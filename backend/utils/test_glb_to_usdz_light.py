"""Regression test for the low-memory GLB -> USDZ converter."""
import json
import struct
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

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


if __name__ == "__main__":
    unittest.main()
