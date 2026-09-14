"""
Pure-logic tests for glb_normalize.py, using small synthetic GLB payloads
(no real 3DAIStudio-generated asset needed, no network, no Django).
Run with: manage.py test utils.test_glb_normalize
"""
import math
import unittest

from utils.glb_normalize import (
    NORMALIZED_MARKER_KEY,
    TARGET_MAX_DIMENSION,
    compute_world_aabb,
    normalize_glb_bytes,
    read_glb,
    write_glb,
)


def make_gltf(*, min_, max_, node_extra=None, wrapper_extra=None):
    """A minimal one-triangle scene whose POSITION accessor bounds are
    exactly min_/max_ - real vertex data is irrelevant, only accessor
    min/max drives the bounding box math."""
    node = {"mesh": 0}
    if node_extra:
        node.update(node_extra)
    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [node],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 4}]}],
        "accessors": [{
            "bufferView": 0,
            "componentType": 5126,
            "count": 3,
            "type": "VEC3",
            "min": list(min_),
            "max": list(max_),
        }],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36}],
        "buffers": [{"byteLength": 36}],
    }
    if wrapper_extra:
        gltf.update(wrapper_extra)
    return gltf


class GLBRoundTripTests(unittest.TestCase):
    def test_write_then_read_preserves_json_and_bin(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(1, 1, 1))
        # A length already a multiple of 4, so there's no zero-padding to
        # account for in the round-trip comparison below.
        bin_chunk = b"some-binary-vertex-data"[:20]

        data = write_glb(gltf, bin_chunk)
        parsed_gltf, parsed_bin = read_glb(data)

        self.assertEqual(parsed_gltf, gltf)
        self.assertEqual(parsed_bin, bin_chunk)

    def test_write_then_read_without_bin_chunk(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(1, 1, 1))

        data = write_glb(gltf, None)
        parsed_gltf, parsed_bin = read_glb(data)

        self.assertEqual(parsed_gltf, gltf)
        self.assertIsNone(parsed_bin)


class BoundingBoxTests(unittest.TestCase):
    def test_axis_aligned_box_no_transform(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(2, 4, 1))
        aabb_min, aabb_max = compute_world_aabb(gltf)
        self.assertTrue((aabb_min == [0, 0, 0]).all())
        self.assertTrue((aabb_max == [2, 4, 1]).all())

    def test_node_translation_shifts_bounding_box(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(1, 1, 1), node_extra={"translation": [10, 0, 0]})
        aabb_min, aabb_max = compute_world_aabb(gltf)
        self.assertTrue((aabb_min == [10, 0, 0]).all())
        self.assertTrue((aabb_max == [11, 1, 1]).all())

    def test_node_scale_grows_bounding_box(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(1, 2, 1), node_extra={"scale": [2, 2, 2]})
        aabb_min, aabb_max = compute_world_aabb(gltf)
        self.assertTrue((aabb_min == [0, 0, 0]).all())
        self.assertTrue((aabb_max == [2, 4, 2]).all())

    def test_nested_parent_child_transform_composes(self):
        # Parent node translates by (5, 0, 0); child (with the mesh) scales by 2.
        gltf = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [
                {"translation": [5, 0, 0], "children": [1]},
                {"mesh": 0, "scale": [2, 2, 2]},
            ],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
            "accessors": [{"min": [0, 0, 0], "max": [1, 1, 1]}],
        }
        aabb_min, aabb_max = compute_world_aabb(gltf)
        self.assertTrue((aabb_min == [5, 0, 0]).all())
        self.assertTrue((aabb_max == [7, 2, 2]).all())


class NormalizeTests(unittest.TestCase):
    def test_large_model_is_scaled_down_to_target(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(2, 4, 1))  # max dimension = 4
        data = write_glb(gltf, None)

        normalized, info = normalize_glb_bytes(data)

        self.assertTrue(info["changed"])
        self.assertAlmostEqual(info["original_max_dimension"], 4.0)
        self.assertAlmostEqual(info["scale_applied"], TARGET_MAX_DIMENSION / 4.0)

        result_gltf, _ = read_glb(normalized)
        new_min, new_max = compute_world_aabb(result_gltf)
        new_max_dimension = float((new_max - new_min).max())
        self.assertAlmostEqual(new_max_dimension, TARGET_MAX_DIMENSION, places=6)

    def test_tiny_model_is_scaled_up_to_target(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(0.01, 0.01, 0.01))  # max dimension = 0.01
        data = write_glb(gltf, None)

        normalized, info = normalize_glb_bytes(data)

        result_gltf, _ = read_glb(normalized)
        new_min, new_max = compute_world_aabb(result_gltf)
        new_max_dimension = float((new_max - new_min).max())
        self.assertAlmostEqual(new_max_dimension, TARGET_MAX_DIMENSION, places=6)

    def test_uniform_scale_never_distorts_proportions(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(1, 2, 4))  # 1:2:4 aspect ratio
        data = write_glb(gltf, None)

        normalized, _ = normalize_glb_bytes(data)
        result_gltf, _ = read_glb(normalized)
        new_min, new_max = compute_world_aabb(result_gltf)
        dims = new_max - new_min

        # Ratios between axes must be unchanged by a uniform scale.
        self.assertAlmostEqual(dims[1] / dims[0], 2.0, places=6)
        self.assertAlmostEqual(dims[2] / dims[0], 4.0, places=6)

    def test_second_normalize_pass_is_a_no_op(self):
        """Never compound scale on repeated processing of the same file."""
        gltf = make_gltf(min_=(0, 0, 0), max_=(2, 4, 1))
        data = write_glb(gltf, None)

        first_pass, first_info = normalize_glb_bytes(data)
        second_pass, second_info = normalize_glb_bytes(first_pass)

        self.assertTrue(first_info["changed"])
        self.assertFalse(second_info["changed"])
        self.assertEqual(second_info["reason"], "already_normalized")
        self.assertEqual(first_pass, second_pass)  # byte-identical, not re-scaled

    def test_already_normalized_marker_is_persisted(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(2, 4, 1))
        data = write_glb(gltf, None)

        normalized, _ = normalize_glb_bytes(data)
        result_gltf, _ = read_glb(normalized)

        self.assertEqual(
            result_gltf["asset"]["extras"][NORMALIZED_MARKER_KEY],
            TARGET_MAX_DIMENSION,
        )

    def test_degenerate_bounding_box_raises_instead_of_silently_scaling(self):
        gltf = make_gltf(min_=(0, 0, 0), max_=(0, 0, 0))  # zero-size box
        data = write_glb(gltf, None)

        with self.assertRaises(Exception):
            normalize_glb_bytes(data)


if __name__ == "__main__":
    unittest.main()
