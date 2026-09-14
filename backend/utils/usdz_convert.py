"""
GLB -> USDZ conversion for iOS AR Quick Look, using the existing
Blender-headless pipeline (glb_to_usdz.py + fix_usdz_textures.py) plus a
genuine structural validation pass with pxr (the reference USD library -
the same technology ARKit's own USD-based Quick Look renderer is built
on), so a broken export is caught here rather than shipped to a phone.

Always run this against an already-normalized GLB (utils.glb_normalize) -
this module has no opinion on scale, it just converts whatever geometry
it's given.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from decouple import config
from django.conf import settings

BLENDER_SCRIPT = Path(settings.BASE_DIR) / "utils" / "glb_to_usdz.py"
FIX_TEXTURES_SCRIPT = Path(settings.BASE_DIR) / "utils" / "fix_usdz_textures.py"

BLENDER_TIMEOUT_SECONDS = 90
FIX_TEXTURES_TIMEOUT_SECONDS = 60


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


def find_blender_binary() -> str | None:
    """BLENDER_BINARY env var takes priority (set by the Docker image in
    production); falls back to whatever `blender` resolves to on PATH for
    environments where it's just apt-installed."""
    return config("BLENDER_BINARY", default=None) or shutil.which("blender")


def convert_glb_to_usdz(glb_bytes: bytes) -> bytes:
    """
    Returns validated USDZ bytes, or raises USDZConversionError. Callers
    must catch this (and ideally also bare Exception, for genuinely
    unexpected failures) and must never let it interrupt saving the GLB
    itself - USDZ is an iOS-only enhancement, not a requirement for
    Android/web to keep working.
    """
    blender_bin = find_blender_binary()
    if not blender_bin:
        raise USDZConversionError("BLENDER_NOT_AVAILABLE", "no Blender binary configured (BLENDER_BINARY) or found on PATH")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        in_glb = tmp / "model.glb"
        raw_usdz = tmp / "model.usdz"
        fixed_usdz = tmp / "model_fixed.usdz"
        in_glb.write_bytes(glb_bytes)

        try:
            result = subprocess.run(
                [blender_bin, "--background", "--factory-startup", "--python", str(BLENDER_SCRIPT),
                 "--", str(in_glb), str(raw_usdz)],
                capture_output=True, timeout=BLENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise USDZConversionError("CONVERSION_TIMEOUT", str(exc)) from exc
        except OSError as exc:
            raise USDZConversionError("BLENDER_LAUNCH_FAILED", str(exc)) from exc

        if result.returncode != 0 or not raw_usdz.exists():
            raise USDZConversionError(
                "BLENDER_EXPORT_FAILED",
                _tail(result.stderr) or _tail(result.stdout),
            )

        try:
            fix_result = subprocess.run(
                [sys.executable, str(FIX_TEXTURES_SCRIPT), str(raw_usdz), str(fixed_usdz)],
                capture_output=True, timeout=FIX_TEXTURES_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise USDZConversionError("TEXTURE_FIX_TIMEOUT", str(exc)) from exc

        if fix_result.returncode != 0 or not fixed_usdz.exists():
            raise USDZConversionError(
                "TEXTURE_FIX_FAILED",
                _tail(fix_result.stderr) or _tail(fix_result.stdout),
            )

        usdz_bytes = fixed_usdz.read_bytes()

    validate_usdz_bytes(usdz_bytes)
    return usdz_bytes


def validate_usdz_bytes(data: bytes) -> None:
    """
    Structural sanity check before trusting a conversion result: a real
    zip container whose first entry is an uncompressed USD layer (per the
    USDZ spec), which pxr (the same USD implementation ARKit is built on)
    can actually open and that contains real content. Raises
    USDZConversionError("USDZ_INVALID", ...) otherwise.
    """
    if not data or data[:2] != b"PK":
        raise USDZConversionError("USDZ_INVALID", "output is not a zip/usdz container")

    with tempfile.NamedTemporaryFile(suffix=".usdz", delete=False) as f:
        f.write(data)
        tmp_path = f.name

    try:
        with zipfile.ZipFile(tmp_path) as zf:
            names = zf.namelist()
            if not names or not names[0].endswith((".usdc", ".usda")):
                raise USDZConversionError("USDZ_INVALID", f"first zip entry is not a usd layer: {names[:1]}")
            bad_entry = zf.testzip()
            if bad_entry:
                raise USDZConversionError("USDZ_INVALID", f"corrupt zip entry: {bad_entry}")

        from pxr import Usd  # imported lazily - only needed for this validation step

        stage = Usd.Stage.Open(tmp_path)
        if stage is None or not list(stage.Traverse()):
            raise USDZConversionError("USDZ_INVALID", "USD stage has no content")
        stage = None  # drop our reference before cleanup below
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            # USD caches opened layers process-wide (by design, for reuse),
            # which can keep a file handle open on Windows past the point
            # our Python reference is dropped - harmless to leave the temp
            # file behind (the OS temp dir cleans up eventually); must
            # never mask a validation result that already succeeded.
            pass


def _tail(output: bytes | None, limit: int = 2000) -> str:
    if not output:
        return ""
    return output.decode("utf-8", "replace")[-limit:]
