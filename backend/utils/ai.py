from decouple import config
import httpx
from httpx import AsyncClient, Client, Timeout, stream
from pathlib import Path
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image
import base64
import logging

logger = logging.getLogger(__name__)

API_TOKEN = config("AISTUDIO_TOKEN", None)
if API_TOKEN is None:
    raise ValueError("API_TOKEN environment variable not set")

burl = "https://api.3daistudio.com"

models = {
    "tencent_rapid": {
        "url": "/v1/3d-models/tencent/generate/rapid/",
    },
    "hunyuan": {
        "url": "/v1/3d-models/tencent/generate/pro/",
        "example": {
            "model": "3.0",
            "prompt": "a medieval sword with ornate handle",
            "enable_pbr": True,
            "face_count": 500000,
            "generate_type": "Normal"
        }
    },
    "trellis": {
        "url": "/v1/3d-models/trellis2/generate/",
        "example": {
            "image_url": "https://example.com/my-object.png",
            "resolution": "1024",
            "textures": True,
            "texture_size": 2048
        }
    },
    "tripo": {
        "url": "/v1/3d-models/tripo/text-to-3d/",
        "example": {
            "prompt": "a medieval sword with ornate handle",
            "texture": True,
            "pbr": True,
            "texture_quality": "standard"
        }
    }
}

ERROR_MESSAGES = {
    "AUTH_ERROR": "3D API token noto'g'ri yoki amal qilmayapti.",
    "INSUFFICIENT_CREDITS": "3D API krediti tugagan.",
    "TASK_ACCESS_DENIED": "Bu 3D task boshqa API akkauntiga tegishli.",
    "TASK_NOT_FOUND": "3D task topilmadi. Modelni qayta generatsiya qilish kerak.",
    "RATE_LIMITED": "3D servis limiti vaqtincha tugagan. Keyinroq qayta urinib ko'ring.",
    "NETWORK_ERROR": "3D servisga ulanib bo'lmadi. Keyinroq qayta urinib ko'ring.",
    "PROVIDER_ERROR": "3D servisda xatolik yuz berdi.",
}


def public_error_payload(error_type, *, provider_http_status=None, provider_json=None, detail=None):
    payload = {
        "error_type": error_type,
        "error_code": error_type,
        "error": ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["PROVIDER_ERROR"]),
    }
    if provider_http_status is not None:
        payload["provider_http_status"] = provider_http_status
    if detail:
        payload["detail"] = detail
    if provider_json is not None:
        payload["provider_json"] = provider_json
    return payload


def extract_task_id(data):
    if not isinstance(data, dict):
        return None

    for key in ("task_id", "id", "request_id", "generation_request_id"):
        value = data.get(key)
        if value:
            return value

    for container_key in ("data", "result", "results"):
        container = data.get(container_key)
        entries = container if isinstance(container, list) else [container]
        for entry in entries:
            if isinstance(entry, dict):
                value = extract_task_id(entry)
                if value:
                    return value
    return None


def classify_provider_error(data=None, http_status=None, network_error=None):
    if network_error:
        return public_error_payload("NETWORK_ERROR", detail=str(network_error))

    data = data if isinstance(data, dict) else {}
    raw_code = str(data.get("error_code") or data.get("code") or "").upper()
    text = " ".join(
        str(data.get(key) or "")
        for key in ("error", "detail", "message", "failure_reason")
    ).lower()

    error_type = None
    if http_status in (401,):
        error_type = "AUTH_ERROR"
    elif http_status in (403,):
        error_type = "TASK_ACCESS_DENIED"
    elif http_status in (404,) or "not found" in text or "no publicapigenerationrequest" in text:
        error_type = "TASK_NOT_FOUND"
    elif http_status in (402,) or raw_code == "INSUFFICIENT_CREDITS" or "insufficient credits" in text or "quota" in text or "credits" in text:
        error_type = "INSUFFICIENT_CREDITS"
    elif http_status in (429,) or "rate limit" in text or "limit reached" in text:
        error_type = "RATE_LIMITED"
    elif http_status and http_status >= 400:
        error_type = "PROVIDER_ERROR"

    if not error_type:
        return data

    return public_error_payload(
        error_type,
        provider_http_status=http_status,
        provider_json=data,
    )


def is_successful_generation_response(data):
    return bool(extract_task_id(data)) and not (data or {}).get("error_type")


def log_provider_response(action, response, data, task_id=None):
    logger.info(
        "3DAIStudio %s response: status=%s task_id=%s json=%s",
        action,
        getattr(response, "status_code", None),
        task_id,
        data,
    )
def image_to_base64_data_uri(image_path: str) -> dict:
    # Re-encode through Pillow instead of trusting the file extension / OS
    # mimetypes db (e.g. .webp resolves to '' rather than None on some
    # Windows installs, silently producing an invalid "data:;base64,..."
    # URI that the provider rejects with VALIDATION_FAILED).
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
    except FileNotFoundError:
        return {"status": False, "error": "File not found"}
    except Exception as e:
        return {"status": False, "error": str(e)}

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return {"status": True, "result": f"data:image/jpeg;base64,{encoded}"}

class API:
    def __init__(self):
        timeout=Timeout(
            connect=10.0,
            read=60.0,
            write=60.0,  # <-- именно это падало (WriteTimeout)
            pool=10.0,
        )
        self.aclient = AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )
        self.client = Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )

    def show_balance(self):
        res = self.client.get(
            url=f"{burl}/account/user/wallet/",
        )
        return res.json()

    def send_prompt(self, prompt):
        try:
            res = self.client.post(
                url=burl + str(models["tencent_rapid"]["url"]),
                json={
                    "prompt": prompt,
                    "enable_pbr": True,
                }
            )
            data = res.json()
            log_provider_response("generate", res, data, extract_task_id(data))
        except httpx.HTTPError as exc:
            return classify_provider_error(network_error=exc)
        except ValueError as exc:
            return classify_provider_error({"detail": str(exc)}, http_status=getattr(locals().get("res", None), "status_code", None))

        if res.status_code >= 400:
            return classify_provider_error(data, http_status=res.status_code)
        return data

    def send_image(self, *, image_path=None, image_url=None):
        """
        Image-to-3D generation via TRELLIS.2 (confirmed against
        https://3daistudio.com/Platform/API/Documentation/3d-generation/trellis2):
        the request takes exactly one of `image` (a base64 data URI, for a
        locally-stored file the provider can't reach over HTTP) or
        `image_url` (a publicly reachable URL, e.g. the R2-backed file in
        production).
        """
        if image_path:
            encoded = image_to_base64_data_uri(image_path)
            if not encoded.get("status"):
                return public_error_payload("PROVIDER_ERROR", detail=encoded.get("error"))
            payload = {"image": encoded["result"], "textures": True}
        elif image_url:
            payload = {"image_url": image_url, "textures": True}
        else:
            raise ValueError("send_image requires image_path or image_url")

        try:
            res = self.client.post(
                url=burl + str(models["trellis"]["url"]),
                json=payload,
            )
            data = res.json()
            log_provider_response("generate", res, data, extract_task_id(data))
        except httpx.HTTPError as exc:
            return classify_provider_error(network_error=exc)
        except ValueError as exc:
            return classify_provider_error({"detail": str(exc)}, http_status=getattr(locals().get("res", None), "status_code", None))

        if res.status_code >= 400:
            return classify_provider_error(data, http_status=res.status_code)
        return data

    def show_model(self, task_id):
        try:
            res = self.client.get(
                url=f"{burl}/v1/generation-request/{task_id}/status/",
            )
            data = res.json()
            log_provider_response("status", res, data, task_id)
        except httpx.HTTPError as exc:
            return classify_provider_error(network_error=exc)
        except ValueError as exc:
            return classify_provider_error({"detail": str(exc)}, http_status=getattr(locals().get("res", None), "status_code", None))

        if res.status_code >= 400:
            return classify_provider_error(data, http_status=res.status_code)
        return data

    def download_model(self, url: str, save_dir: str = "media/models/") -> str:
        parsed = urlparse(url)
        filename = Path(parsed.path).name  # trellis2_1024_1014963766.glb

        Path(save_dir).mkdir(parents=True, exist_ok=True)
        save_path = Path(save_dir) / filename

        # Стримим скачивание, чтобы не грузить весь файл в память разом
        # (не передаём auth-заголовки — presigned URL уже содержит подпись доступа)
        with stream("GET", url, timeout=Timeout(60.0)) as response:
            response.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        return str(save_path)

api = API()
