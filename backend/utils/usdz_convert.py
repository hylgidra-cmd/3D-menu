"""
GLB -> USDZ conversion for iOS AR Quick Look. The converter writes the
standard USD Preview Surface subset directly, avoiding Blender because it
exceeds Render Free's 512MB memory limit while importing a generated GLB.

Always run this against an already-normalized GLB (utils.glb_normalize) -
this module has no opinion on scale, it just converts whatever geometry
it's given.
"""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings

LIGHTWEIGHT_CONVERTER_SCRIPT = Path(settings.BASE_DIR) / "utils" / "glb_to_usdz_light.py"

CONVERSION_TIMEOUT_SECONDS = 120


class USDZConversionError(Exception):
    """
    Raised for any GLB->USDZ conversion failure. `error_type` is a short,
    stable, public-safe code (see apps.eat.models.USDZ_ERROR_MESSAGES);
    `detail` may hold internal subprocess output/exception text and must
    only ever be logged, never serialized to an API response.
    """

    def __init__(self, error_type: str, detail: str = ""):
        self.error_type = error_type
        self.detail = detail
        super().__init__(f"{error_type}: {detail}" if detail else error_type)


def convert_glb_to_usdz(glb_bytes: bytes) -> bytes:
    """
    Returns validated USDZ bytes, or raises USDZConversionError. Callers
    must catch this (and ideally also bare Exception, for genuinely
    unexpected failures) and must never let it interrupt saving the GLB
    itself - USDZ is an iOS-only enhancement, not a requirement for
    Android/web to keep working.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        in_glb = tmp / "model.glb"
        output_usdz = tmp / "model.usdz"
        in_glb.write_bytes(glb_bytes)

        try:
            result = subprocess.run(
                [sys.executable, str(LIGHTWEIGHT_CONVERTER_SCRIPT), str(in_glb), str(output_usdz)],
                capture_output=True, timeout=CONVERSION_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise USDZConversionError("CONVERSION_TIMEOUT", str(exc)) from exc
        except OSError as exc:
            raise USDZConversionError("BLENDER_LAUNCH_FAILED", str(exc)) from exc

        if result.returncode != 0 or not output_usdz.exists():
            raise USDZConversionError(
                "BLENDER_EXPORT_FAILED",
                _tail(result.stderr) or _tail(result.stdout),
            )
        usdz_bytes = output_usdz.read_bytes()

    validate_usdz_bytes(usdz_bytes)
    return usdz_bytes


def validate_usdz_bytes(data: bytes) -> None:
    """
    Structural sanity check before trusting a conversion result. It stays
    lightweight so the final request does not load the large USD Python
    runtime into Render's 512MB instance after conversion succeeds.
    """
    if not data or data[:2] != b"PK":
        raise USDZConversionError("USDZ_INVALID", "output is not a zip/usdz container")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if not names or not names[0].endswith((".usdc", ".usda")):
                raise USDZConversionError("USDZ_INVALID", f"first zip entry is not a usd layer: {names[:1]}")
            root = zf.read(names[0])
            if names[0].endswith(".usda") and not root.lstrip().startswith(b"#usda"):
                raise USDZConversionError("USDZ_INVALID", "root USD layer is not valid USDA text")
            bad_entry = zf.testzip()
            if bad_entry:
                raise USDZConversionError("USDZ_INVALID", f"corrupt zip entry: {bad_entry}")
            for info in zf.infolist():
                data_offset = info.header_offset + 30 + len(info.filename.encode("utf-8")) + len(info.extra)
                if info.compress_type != zipfile.ZIP_STORED or data_offset % 64:
                    raise USDZConversionError("USDZ_INVALID", f"USDZ entry is not aligned: {info.filename}")
    except zipfile.BadZipFile as exc:
        raise USDZConversionError("USDZ_INVALID", "output is not a readable zip/usdz container") from exc


def _tail(output: bytes | None, limit: int = 2000) -> str:
    if not output:
        return ""
    return output.decode("utf-8", "replace")[-limit:]
