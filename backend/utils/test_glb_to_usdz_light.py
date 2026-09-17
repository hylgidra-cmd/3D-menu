"""Regression test for the low-memory GLB -> USDZ converter."""
import json
import io
import struct
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from glb_to_usdz_light import convert


def write_glb(gltf, binary):
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode()
    json_bytes += b" " * (-len(json_bytes) % 4)
    binary += b"\0" * (-len(binary) % 4)
    body = (
        struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
        + struct.pack("<II", len(binary), 0x004E4942) + binary
    )
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


class LightweightUsdzTests(unittest.TestCase):
    def test_exports_a_64_byte_aligned_usda_package(self):
        positions = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
        indices = struct.pack("<3H", 0, 1, 2)
        binary = positions + indices
        gltf = {
            "asset": {"version": "2.0"}, "scene": 0,
            "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
                {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices)},
            ],
            "buffers": [{"byteLength": len(binary)}],
        }
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "model.glb"
            output_path = Path(directory) / "model.usdz"
            input_path.write_bytes(write_glb(gltf, binary))
            convert(input_path, output_path)

            with zipfile.ZipFile(output_path) as archive:
                self.assertEqual(archive.namelist(), ["model.usda"])
                self.assertIn(b"point3f[] points", archive.read("model.usda"))
                for info in archive.infolist():
                    offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(offset % 64, 0)

    def test_preserves_trellis_webp_base_color_texture(self):
        """TRELLIS puts its source in EXT_texture_webp, not texture.source.

        This is the exact shape that previously generated a white iOS model
        despite a ready USDZ status.
        """
        positions = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
        texcoords = struct.pack("<6f", 0, 0, 1, 0, 0, 1)
        indices = struct.pack("<3H", 0, 1, 2)
        image = io.BytesIO()
        Image.new("RGBA", (2, 2), (230, 60, 80, 255)).save(image, "WEBP", lossless=True)
        image_data = image.getvalue()
        binary = positions + texcoords + indices + image_data
        gltf = {
            "asset": {"version": "2.0"}, "scene": 0,
            "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{
                "attributes": {"POSITION": 0, "TEXCOORD_0": 1}, "indices": 2, "material": 0,
            }]}],
            "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
            "textures": [{"extensions": {"EXT_texture_webp": {"source": 0}}}],
            "images": [{"bufferView": 3, "mimeType": "image/webp"}],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC2"},
                {"bufferView": 2, "componentType": 5123, "count": 3, "type": "SCALAR"},
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
                {"buffer": 0, "byteOffset": len(positions), "byteLength": len(texcoords)},
                {"buffer": 0, "byteOffset": len(positions) + len(texcoords), "byteLength": len(indices)},
                {"buffer": 0, "byteOffset": len(positions) + len(texcoords) + len(indices), "byteLength": len(image_data)},
            ],
            "buffers": [{"byteLength": len(binary)}],
        }
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "model.glb"
            output_path = Path(directory) / "model.usdz"
            input_path.write_bytes(write_glb(gltf, binary))
            convert(input_path, output_path)

            with zipfile.ZipFile(output_path) as archive:
                usda = archive.read("model.usda").decode()
                texture_name = next(name for name in archive.namelist() if name.startswith("textures/image-0."))
                self.assertIn(f"asset inputs:file = @{texture_name}@", usda)
                self.assertIn('token inputs:sourceColorSpace = "sRGB"', usda)
                connection = "color3f inputs:diffuseColor.connect"
                self.assertIn(connection, usda)
                preview_start = usda.index('def Shader "PreviewSurface"')
                preview_end = usda.index("      }", preview_start)
                self.assertLess(preview_start, usda.index(connection), preview_end)


if __name__ == "__main__":
    unittest.main()
