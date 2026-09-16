"""
Tests for usdz_convert.py. No 3DAIStudio calls are made. The happy/failure
conversion paths mock the external converter, while validation is tested
against a real, valid USDZ built with pxr (the same USD
  library ARKit's Quick Look is built on), not a fake stand-in.

Run with: manage.py test utils.test_usdz_convert
"""
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pxr import Usd, UsdGeom, UsdUtils

from utils.usdz_convert import (
    USDZConversionError,
    convert_glb_to_usdz,
    validate_usdz_bytes,
)


def build_minimal_usdz_bytes(tmp_dir: Path) -> bytes:
    """A real, valid USDZ (one triangle), packaged with pxr's own official
    USDZ packaging helper - genuine content, not a hand-rolled fake."""
    usdc_path = tmp_dir / "model.usdc"
    stage = Usd.Stage.CreateNew(str(usdc_path))
    UsdGeom.Xform.Define(stage, "/Model")
    mesh = UsdGeom.Mesh.Define(stage, "/Model/Mesh")
    mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    mesh.CreateFaceVertexCountsAttr([3])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
    stage.GetRootLayer().Save()

    usdz_path = tmp_dir / "model.usdz"
    assert UsdUtils.CreateNewUsdzPackage(str(usdc_path), str(usdz_path))
    return usdz_path.read_bytes()


class ValidateUsdzBytesTests(unittest.TestCase):
    def test_accepts_a_real_valid_usdz(self):
        with TemporaryDirectory() as tmp:
            data = build_minimal_usdz_bytes(Path(tmp))
            validate_usdz_bytes(data)  # must not raise

    def test_rejects_non_zip_garbage(self):
        with self.assertRaises(USDZConversionError) as ctx:
            validate_usdz_bytes(b"not a zip file at all")
        self.assertEqual(ctx.exception.error_type, "USDZ_INVALID")

    def test_rejects_zip_without_a_usd_layer_as_first_entry(self):
        with TemporaryDirectory() as tmp:
            bad_zip_path = Path(tmp) / "bad.usdz"
            with zipfile.ZipFile(bad_zip_path, "w") as zf:
                zf.writestr("readme.txt", "not a usd layer")
            with self.assertRaises(USDZConversionError) as ctx:
                validate_usdz_bytes(bad_zip_path.read_bytes())
            self.assertEqual(ctx.exception.error_type, "USDZ_INVALID")

    def test_rejects_empty_bytes(self):
        with self.assertRaises(USDZConversionError):
            validate_usdz_bytes(b"")


class ConvertGlbToUsdzTests(unittest.TestCase):
    def test_happy_path_with_mocked_converter(self):
        """The external converter is mocked in this test, but
        it writes a REAL, valid USDZ that then goes through this module's
        actual (unmocked) validation step."""
        with TemporaryDirectory() as tmp:
            real_usdz_bytes = build_minimal_usdz_bytes(Path(tmp))

            def fake_run(args, capture_output, timeout):
                # Both calls end with an output path as the last argument -
                # write real USDZ bytes there regardless of which stage.
                Path(args[-1]).write_bytes(real_usdz_bytes)
                return subprocess.CompletedProcess(args, returncode=0, stdout=b"", stderr=b"")

            with patch("utils.usdz_convert.subprocess.run", side_effect=fake_run):
                result = convert_glb_to_usdz(b"fake glb bytes")

            self.assertEqual(result, real_usdz_bytes)

    def test_blender_export_failure_is_reported(self):
        def fake_run(args, capture_output, timeout):
            return subprocess.CompletedProcess(args, returncode=1, stdout=b"", stderr=b"boom: out of memory")

        with patch("utils.usdz_convert.subprocess.run", side_effect=fake_run):
            with self.assertRaises(USDZConversionError) as ctx:
                convert_glb_to_usdz(b"fake glb bytes")
        self.assertEqual(ctx.exception.error_type, "BLENDER_EXPORT_FAILED")

    def test_blender_timeout_is_reported(self):
        def fake_run(args, capture_output, timeout):
            raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)

        with patch("utils.usdz_convert.subprocess.run", side_effect=fake_run):
            with self.assertRaises(USDZConversionError) as ctx:
                convert_glb_to_usdz(b"fake glb bytes")
        self.assertEqual(ctx.exception.error_type, "CONVERSION_TIMEOUT")

    def test_invalid_output_is_reported_as_usdz_invalid(self):
        """A converter can report success while outputting garbage;
        validation must still catch it."""
        def fake_run(args, capture_output, timeout):
            Path(args[-1]).write_bytes(b"not actually a usdz")
            return subprocess.CompletedProcess(args, returncode=0, stdout=b"", stderr=b"")

        with patch("utils.usdz_convert.subprocess.run", side_effect=fake_run):
            with self.assertRaises(USDZConversionError) as ctx:
                convert_glb_to_usdz(b"fake glb bytes")
        self.assertEqual(ctx.exception.error_type, "USDZ_INVALID")


if __name__ == "__main__":
    unittest.main()
