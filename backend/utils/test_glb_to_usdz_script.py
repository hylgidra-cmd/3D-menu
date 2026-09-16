"""Regression tests for the Blender-version compatibility in glb_to_usdz.py.

These tests use a tiny fake bpy module, so they prove the options passed to
Blender without requiring Blender or a graphics-capable test runner.
"""
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("glb_to_usdz.py")


class FakeUsdExport:
    def __init__(self, properties):
        self.properties = properties
        self.options = None

    def get_rna_type(self):
        return types.SimpleNamespace(properties=self.properties)

    def __call__(self, **options):
        self.options = options


def run_export_script(properties):
    usd_export = FakeUsdExport(properties)
    fake_bpy = types.SimpleNamespace(
        ops=types.SimpleNamespace(
            wm=types.SimpleNamespace(
                read_factory_settings=lambda **_kwargs: None,
                usd_export=usd_export,
            ),
            import_scene=types.SimpleNamespace(gltf=lambda **_kwargs: None),
        )
    )
    with patch.dict(sys.modules, {"bpy": fake_bpy}), patch.object(
        sys, "argv", ["blender", "--", "input.glb", "output.usdz"]
    ):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    return usd_export.options


class BlenderUsdExportCompatibilityTests(unittest.TestCase):
    def test_debian_blender_34_uses_its_boolean_texture_option(self):
        options = run_export_script({"export_textures", "relative_texture_paths"})

        self.assertTrue(options["export_textures"])
        self.assertTrue(options["relative_texture_paths"])
        self.assertNotIn("export_textures_mode", options)

    def test_newer_blender_uses_the_renamed_texture_option(self):
        options = run_export_script({"export_textures_mode", "relative_paths"})

        self.assertEqual(options["export_textures_mode"], "NEW")
        self.assertTrue(options["relative_paths"])
        self.assertNotIn("export_textures", options)


if __name__ == "__main__":
    unittest.main()
