import logging
from pathlib import Path
from urllib.parse import urlparse
import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count
from rest_framework import generics, permissions, parsers
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.restaurant.models import RestaurantStaff
from apps.restaurant.permissions import is_restaurant_role
from .models import Eat, Category, extract_provider_model_url, usdz_error_payload
from .serializers import EatSerializer, CreateEatSerializer, UpdateEatSerializer, CategorySerializer
from .permissions import IsMineEat
from utils.ai import api, extract_task_id, is_successful_generation_response, public_error_payload
from utils.glb_normalize import GLBNormalizeError, TARGET_MAX_DIMENSION, normalize_glb_bytes
from utils.usdz_convert import USDZConversionError, convert_glb_to_usdz

logger = logging.getLogger(__name__)


def request_food_model(eat):
    """
    Image-to-3D generation from the food's own uploaded photo (TRELLIS.2).
    In DEBUG, media is served from this dev machine, which the external
    provider can never reach - the image is base64-encoded and sent inline
    instead. In production, media lives on public S3/R2 storage, so the
    provider fetches the URL itself.
    """
    if settings.DEBUG:
        return api.send_image(image_path=eat.image.path)
    return api.send_image(image_url=eat.image.url)


def save_provider_model_file(eat, model_json, force_replace=False):
    provider_url = extract_provider_model_url(model_json)
    if not provider_url:
        return []

    if eat.model_file and not force_replace:
        return []

    try:
        resp = httpx.get(provider_url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    filename = Path(urlparse(provider_url).path).name or f"eat-{eat.id}.glb"

    # Bake a consistent real-world size into the file itself, so every
    # consumer (web preview, Android Scene Viewer/WebXR, and any USDZ
    # exported from this GLB) renders it at the same physical scale - a
    # runtime model-viewer `scale` property can't reach native AR viewers.
    content = resp.content
    is_normalized = False
    try:
        content, info = normalize_glb_bytes(content)
        is_normalized = True
        if info["changed"]:
            logger.info(
                "Normalized eat=%s GLB: %.4fm -> %.2fm (scale=%.4f)",
                eat.id, info["original_max_dimension"], TARGET_MAX_DIMENSION, info["scale_applied"],
            )
    except GLBNormalizeError as exc:
        # Never lose a working model over a scaling bug - store it
        # unnormalized rather than fail the whole check-model request.
        logger.warning("Could not normalize eat=%s GLB, storing as-is: %s", eat.id, exc)

    eat.model_file.save(filename, ContentFile(content), save=False)
    updated_fields = ["model_file"]

    # GLB/Android/web are already done above and must stay usable no
    # matter what happens next - USDZ is an iOS-only enhancement layered
    # on top, generated from the SAME (normalized) bytes just saved.
    updated_fields += generate_usdz_for_eat(eat, content, is_normalized)
    return updated_fields


def generate_usdz_for_eat(eat, glb_content, is_normalized):
    if not is_normalized:
        # Building a USDZ from an unnormalized GLB would just reproduce
        # the same iOS size-inconsistency bug - skip and record why,
        # rather than convert something we know is the wrong scale.
        eat.usdz_json = usdz_error_payload("GLB_NOT_NORMALIZED")
        return ["usdz_json"]

    try:
        usdz_bytes = convert_glb_to_usdz(glb_content)
    except USDZConversionError as exc:
        logger.warning("USDZ conversion failed for eat=%s: %s (%s)", eat.id, exc.error_type, exc.detail)
        eat.usdz_json = usdz_error_payload(exc.error_type)
        return ["usdz_json"]
    except Exception:
        # Never let an unexpected bug in the conversion path break the
        # GLB save that already succeeded above.
        logger.exception("Unexpected error converting USDZ for eat=%s", eat.id)
        eat.usdz_json = usdz_error_payload("UNKNOWN_ERROR")
        return ["usdz_json"]

    # New filename, never the existing one - a working USDZ is never
    # overwritten in storage until this new one has already validated
    # successfully above (convert_glb_to_usdz raises on a bad result).
    eat.model_file_usdz.save(f"eat-{eat.id}.usdz", ContentFile(usdz_bytes), save=False)
    eat.usdz_json = {}
    return ["model_file_usdz", "usdz_json"]


class EatListCreateAPIView(generics.ListCreateAPIView):
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    queryset = Eat.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return EatSerializer
        return CreateEatSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMineEat()]

    def get_queryset(self):
        queryset = Eat.objects.all()
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = serializer.validated_data["restaurant"]
        if not is_restaurant_role(request.user, restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)
        serializer.save()

        try:
            task_json = request_food_model(serializer.instance)
        except Exception as exc:
            # Saving the menu item must not fail just because the external 3D
            # provider is unavailable, rate-limited, or out of credits.
            task_json = public_error_payload("NETWORK_ERROR", detail=str(exc))
        serializer.instance.task_json = task_json
        serializer.instance.save(update_fields=["task_json"])

        return Response(EatSerializer(serializer.instance).data, status=201)


class EatDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    queryset = Eat.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UpdateEatSerializer
        return EatSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMineEat()]


class CheckTaskAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, pk):
        eat = Eat.objects.filter(id=pk).first()
        if not eat:
            return Response({"detail": "eat not found"}, status=404)

        if not is_restaurant_role(request.user, eat.restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)

        if eat.model_file and not (eat.task_json or {}).get("replace_model_when_finished"):
            return Response(EatSerializer(eat).data, status=200)

        task_id = extract_task_id(eat.task_json)
        if not task_id:
            if not eat.model_error_type:
                eat.model_json = public_error_payload("TASK_NOT_FOUND")
                eat.save(update_fields=["model_json", "updated_at"])
            return Response(EatSerializer(eat).data, status=200)

        model_json = api.show_model(task_id)
        eat.model_json = model_json
        update_fields = ["model_json"]

        # The provider's URL is a presigned link that expires in ~1 hour, so
        # it can't be served to customers long-term - download it once into
        # our own storage the moment generation finishes.
        force_replace = bool((eat.task_json or {}).get("replace_model_when_finished"))
        if not model_json.get("error_type"):
            saved_fields = save_provider_model_file(eat, model_json, force_replace=force_replace)
            update_fields.extend(saved_fields)
        else:
            saved_fields = []

        if saved_fields and force_replace:
            eat.task_json = {k: v for k, v in (eat.task_json or {}).items() if k != "replace_model_when_finished"}
            update_fields.append("task_json")

        eat.save(update_fields=update_fields)
        return Response(EatSerializer(eat).data, status=200)


class RegenerateModelAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        eat = Eat.objects.filter(id=pk).first()
        if not eat:
            return Response({"detail": "eat not found"}, status=404)

        if not is_restaurant_role(request.user, eat.restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)

        task_json = request_food_model(eat)
        if not is_successful_generation_response(task_json):
            if not eat.model_file:
                eat.model_json = task_json
                eat.save(update_fields=["model_json", "updated_at"])
            return Response(EatSerializer(eat).data, status=200)

        eat.task_json = dict(task_json)
        if eat.model_file:
            eat.task_json["replace_model_when_finished"] = True
        eat.model_json = {}
        eat.save(update_fields=["task_json", "model_json", "updated_at"])
        return Response(EatSerializer(eat).data, status=200)


class RegenerateUSDZAPIView(APIView):
    """Retry only the local iOS conversion for an existing 3D model.

    This deliberately does not call the paid image-to-3D provider again.
    It lets an owner repair models which reached the old Docker image before
    its Blender-export compatibility fix was deployed.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        eat = Eat.objects.filter(id=pk).first()
        if not eat:
            return Response({"detail": "eat not found"}, status=404)

        if not is_restaurant_role(request.user, eat.restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)

        if not eat.model_file:
            return Response({"detail": "Avval taom uchun 3D model tayyor bo'lishi kerak."}, status=400)

        try:
            with eat.model_file.open("rb") as model_file:
                glb_content = model_file.read()
        except (FileNotFoundError, OSError):
            logger.exception("Could not read GLB while retrying USDZ for eat=%s", eat.id)
            return Response({"detail": "3D model faylini o'qib bo'lmadi."}, status=400)

        try:
            normalized_content, info = normalize_glb_bytes(glb_content)
        except GLBNormalizeError as exc:
            logger.warning("Could not normalize GLB while retrying USDZ for eat=%s: %s", eat.id, exc)
            eat.usdz_json = usdz_error_payload("GLB_NOT_NORMALIZED")
            eat.save(update_fields=["usdz_json", "updated_at"])
            return Response(EatSerializer(eat).data, status=200)

        update_fields = []
        if info["changed"]:
            # Keep the previous provider download in storage and only point
            # the record at the normalized copy, matching normalize_models.
            eat.model_file.save(f"eat-{eat.id}-normalized.glb", ContentFile(normalized_content), save=False)
            update_fields.append("model_file")

        update_fields += generate_usdz_for_eat(eat, normalized_content, is_normalized=True)
        eat.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
        return Response(EatSerializer(eat).data, status=200)


class CategoryListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMineEat()]

    def get_queryset(self):
        queryset = Category.objects.all()
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset.annotate(eats_count=Count("eats")).order_by("order", "id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = serializer.validated_data["restaurant"]
        if not is_restaurant_role(request.user, restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)
        serializer.save()
        category = Category.objects.annotate(eats_count=Count("eats")).get(pk=serializer.instance.pk)
        return Response(CategorySerializer(category).data, status=201)


class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.annotate(eats_count=Count("eats"))
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMineEat()]
