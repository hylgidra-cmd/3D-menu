from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator
from decimal import Decimal
from apps.restaurant.models import Restaurant


def extract_provider_model_url(data):
    """
    Extract the generated .glb URL from a 3daistudio job-status payload.
    On success the payload looks like:
        {"status": "FINISHED", "results": [{"asset": "https://.../x.glb",
         "asset_type": "3D_MODEL"}]}
    Note: this URL is a short-lived presigned link (expires in ~1 hour) -
    it must be downloaded and re-hosted (see Eat.model_file), never stored
    or served as-is long-term.
    """
    data = data or {}
    for key in ("model_url", "glb_url", "url", "output_url"):
        value = data.get(key)
        if value:
            return value

    def extract(entry):
        if not isinstance(entry, dict):
            return None
        for key in ("asset", "asset_url", "model_url", "glb_url", "url"):
            value = entry.get(key)
            if value:
                return value
        return None

    for container_key in ("results", "result"):
        container = data.get(container_key)
        entries = container if isinstance(container, list) else [container]
        for entry in entries:
            value = extract(entry)
            if value:
                return value
    return None


MODEL_ERROR_MESSAGES = {
    "AUTH_ERROR": "3D API token noto'g'ri yoki amal qilmayapti.",
    "INSUFFICIENT_CREDITS": "3D API krediti tugagan.",
    "TASK_ACCESS_DENIED": "Bu 3D task boshqa API akkauntiga tegishli.",
    "TASK_NOT_FOUND": "3D task topilmadi. Modelni qayta generatsiya qilish kerak.",
    "RATE_LIMITED": "3D servis limiti vaqtincha tugagan. Keyinroq qayta urinib ko'ring.",
    "NETWORK_ERROR": "3D servisga ulanib bo'lmadi. Keyinroq qayta urinib ko'ring.",
    "PROVIDER_ERROR": "3D servisda xatolik yuz berdi.",
}

# Public-safe messages for GLB->USDZ conversion failures (iOS Quick Look
# only - never affects the GLB itself, which Android/web keep using).
# Full internal detail (subprocess stderr, exceptions) is logged
# server-side only and never stored here or serialized to any client.
USDZ_ERROR_MESSAGES = {
    "BLENDER_NOT_AVAILABLE": "iOS uchun 3D fayl hali tayyor emas.",
    "BLENDER_LAUNCH_FAILED": "iOS uchun 3D faylni tayyorlab bo'lmadi.",
    "CONVERSION_TIMEOUT": "iOS uchun 3D faylni tayyorlashda vaqt tugadi.",
    "BLENDER_EXPORT_FAILED": "iOS uchun 3D faylni tayyorlab bo'lmadi.",
    "TEXTURE_FIX_FAILED": "iOS uchun 3D faylni tayyorlab bo'lmadi.",
    "TEXTURE_FIX_TIMEOUT": "iOS uchun 3D faylni tayyorlashda vaqt tugadi.",
    "USDZ_INVALID": "iOS uchun 3D fayl yaroqsiz chiqdi.",
    "GLB_NOT_NORMALIZED": "3D fayl hali o'lchami bir xillashtirilmagan.",
    "UNKNOWN_ERROR": "iOS uchun 3D faylni tayyorlashda kutilmagan xatolik yuz berdi.",
}


def usdz_error_payload(error_type):
    return {
        "error_type": error_type,
        "error": USDZ_ERROR_MESSAGES.get(error_type, USDZ_ERROR_MESSAGES["UNKNOWN_ERROR"]),
    }


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=16, default="utensils")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.restaurant} - {self.name}"

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "id"]


class Eat(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="eat_restaurant")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="eats")
    name = models.CharField(max_length=200)
    description = models.TextField(validators=[MinLengthValidator(5), MaxLengthValidator(500)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    image = models.ImageField(upload_to="eat/")
    task_json = models.JSONField(default=dict)
    model_json = models.JSONField(default=dict)
    # The provider's own .glb URL (model_json's "results[].asset") is a
    # presigned link that expires in ~1 hour - it gets downloaded once into
    # our own storage here so customers always have a working, permanent URL.
    model_file = models.FileField(upload_to="models/", blank=True, null=True)
    # iOS AR Quick Look can't render .glb - it only accepts Apple's USDZ
    # format, so this is converted from model_file once it's downloaded.
    model_file_usdz = models.FileField(upload_to="models_usdz/", blank=True, null=True)
    # Records why the GLB->USDZ conversion failed, if it did - separate
    # from model_json/task_json since it's about a local format
    # conversion, not the provider's 3D generation itself.
    usdz_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Eat {self.name}"

    @property
    def model_url(self):
        """
        Only ever the permanent, re-hosted file - never the provider's raw
        presigned link (it expires in ~1 hour, so exposing it here would
        just hand out a URL that goes dead shortly after being read).
        """
        return self.model_file.url if self.model_file else None

    @property
    def model_url_usdz(self):
        if not self.model_file_usdz:
            return None
        # Quick Look can retain a previously downloaded USDZ for the same
        # URL.  Regeneration replaces the R2 object in place, so expose a
        # version tied to the saved record and make iPhone fetch the new file.
        url = self.model_file_usdz.url
        separator = "&" if "?" in url else "?"
        version = int(self.updated_at.timestamp()) if self.updated_at else 0
        return f"{url}{separator}v={version}"

    @property
    def model_status(self):
        if self.model_file:
            return "finished"
        task_error = (self.task_json or {}).get("error")
        if task_error:
            return "failed"
        data = self.model_json or {}
        if data.get("error_type") or data.get("error"):
            return "failed"
        status = data.get("status") or data.get("state")
        status = status.lower() if isinstance(status, str) else status
        # The provider says it's finished, but we haven't re-hosted the file
        # yet (or a previous download attempt failed) - one more "Tekshirish"
        # will retry the download.
        if status in ("finished", "success", "succeeded", "completed") and not self.model_file:
            return "downloading"
        if status:
            return status
        return "pending" if not data else "unknown"

    @property
    def model_progress(self):
        data = self.model_json or {}
        progress = data.get("progress")
        return progress if isinstance(progress, (int, float)) else None

    @property
    def model_error(self):
        error_type = self.model_error_type
        if error_type in MODEL_ERROR_MESSAGES:
            return MODEL_ERROR_MESSAGES[error_type]

        data = self.model_json or {}
        task = self.task_json or {}
        for payload in (data, task, data.get("provider_json") or {}, task.get("provider_json") or {}):
            if not isinstance(payload, dict):
                continue
            message = (
                payload.get("error")
                or payload.get("detail")
                or payload.get("message")
                or payload.get("failure_reason")
            )
            if message:
                return message
        return (
            None
        )

    @property
    def model_error_type(self):
        data = self.model_json or {}
        task = self.task_json or {}
        existing = data.get("error_type") or task.get("error_type") or data.get("error_code") or task.get("error_code")
        if existing:
            return existing

        payloads = (data, task, data.get("provider_json") or {}, task.get("provider_json") or {})
        text = " ".join(
            str(payload.get(key) or "")
            for payload in payloads
            if isinstance(payload, dict)
            for key in ("error", "detail", "message", "failure_reason")
        ).lower()
        if "winerror" in text or "connect" in text or "network" in text or "timeout" in text:
            return "NETWORK_ERROR"
        if "insufficient credits" in text or "quota" in text or "credits" in text:
            return "INSUFFICIENT_CREDITS"
        if "not found" in text or "no publicapigenerationrequest" in text:
            return "TASK_NOT_FOUND"
        if "unauthorized" in text or "invalid token" in text:
            return "AUTH_ERROR"
        if "forbidden" in text or "access denied" in text:
            return "TASK_ACCESS_DENIED"
        return None

    @property
    def usdz_status(self):
        """For admin: distinguishes GLB-ready-but-no-USDZ-yet states so
        iOS readiness can be shown separately from the GLB/Android/web
        status above."""
        if self.model_file_usdz:
            return "ready"
        if (self.usdz_json or {}).get("error_type"):
            return "failed"
        if self.model_file:
            return "pending"
        return ""

    @property
    def usdz_error(self):
        return (self.usdz_json or {}).get("error")

    @property
    def usdz_error_type(self):
        return (self.usdz_json or {}).get("error_type")

    class Meta:
        verbose_name = "Eat"
        verbose_name_plural = "Eats"
        ordering = ["-created_at"]
