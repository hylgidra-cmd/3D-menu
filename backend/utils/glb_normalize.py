"""
Bake a consistent real-world size into a .glb by measuring its true
bounding box (from glTF accessor min/max - no buffer decoding needed) and
wrapping the scene's root node(s) in a new parent node carrying a uniform
scale. This is a permanent, file-level fix: every consumer that reads the
GLB directly (model-viewer's web preview, Android Scene Viewer/WebXR, and
any USDZ exporter run against this file) sees the same baked-in size,
instead of relying on a runtime "scale" property that only ever affects
the JS preview and is invisible to native AR viewers.

No third-party 3D library required - a GLB is just a JSON chunk (the
node/mesh/accessor graph) plus an optional binary chunk of raw vertex
data. Since glTF's POSITION accessors are required by spec to carry
min/max, the whole bounding box can be computed from the JSON alone.
"""
from __future__ import annotations

import json
import struct

import numpy as np

TARGET_MAX_DIMENSION = 0.35  # meters

GLB_MAGIC = 0x46546C67  # "glTF"
GLB_VERSION = 2
CHUNK_TYPE_JSON = 0x4E4F534A  # "JSON"
CHUNK_TYPE_BIN = 0x004E4942  # "BIN\0"

# Marks a GLB (in asset.extras) as already baked to TARGET_MAX_DIMENSION,
# so re-running normalization on an already-normalized file is a no-op
# instead of scaling it a second time.
NORMALIZED_MARKER_KEY = "menu3d_normalized_max_dimension_m"
ORIGINAL_DIMENSION_KEY = "menu3d_original_max_dimension_m"


class GLBNormalizeError(ValueError):
    """Raised when a .glb can't be parsed or measured. Callers should treat
    this as non-fatal and fall back to saving the file unmodified."""


def read_glb(data: bytes) -> tuple[dict, bytes | None]:
    if len(data) < 12:
        raise GLBNormalizeError("File too small to be a valid GLB")

    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise GLBNormalizeError("Not a valid GLB file (bad magic header)")
    if version != GLB_VERSION:
        raise GLBNormalizeError(f"Unsupported glTF binary version: {version}")

    json_chunk = None
    bin_chunk = None
    offset = 12
    while offset + 8 <= length and offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        chunk_data = data[offset + 8: offset + 8 + chunk_len]
        if chunk_type == CHUNK_TYPE_JSON:
            json_chunk = chunk_data
        elif chunk_type == CHUNK_TYPE_BIN:
            bin_chunk = chunk_data
        offset += 8 + chunk_len

    if json_chunk is None:
        raise GLBNormalizeError("GLB is missing its JSON chunk")

    try:
        gltf = json.loads(json_chunk.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GLBNormalizeError(f"GLB JSON chunk is not valid JSON: {exc}") from exc

    return gltf, bin_chunk


def write_glb(gltf: dict, bin_chunk: bytes | None) -> bytes:
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)  # glTF pads JSON with spaces

    body = struct.pack("<II", len(json_bytes), CHUNK_TYPE_JSON) + json_bytes
    if bin_chunk is not None:
        padded_bin = bin_chunk + b"\x00" * ((4 - len(bin_chunk) % 4) % 4)  # and BIN with zeros
        body += struct.pack("<II", len(padded_bin), CHUNK_TYPE_BIN) + padded_bin

    header = struct.pack("<III", GLB_MAGIC, GLB_VERSION, 12 + len(body))
    return header + body


def _quat_to_matrix(q) -> np.ndarray:
    x, y, z, w = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y), 0],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x), 0],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y), 0],
            [0, 0, 0, 1],
        ],
        dtype=float,
    )


def _node_local_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        # glTF stores matrices column-major - "F" order reads them into the
        # numpy layout that already means the same thing.
        return np.array(node["matrix"], dtype=float).reshape((4, 4), order="F")

    tx, ty, tz = node.get("translation", [0, 0, 0])
    translation = np.eye(4)
    translation[0, 3], translation[1, 3], translation[2, 3] = tx, ty, tz

    rotation = _quat_to_matrix(node.get("rotation", [0, 0, 0, 1]))

    sx, sy, sz = node.get("scale", [1, 1, 1])
    scale = np.diag([sx, sy, sz, 1.0])

    return translation @ rotation @ scale


def compute_world_aabb(gltf: dict) -> tuple[np.ndarray, np.ndarray]:
    """World-space (min, max) corners across every mesh in the default
    scene, accounting for each node's own transform."""
    nodes = gltf.get("nodes") or []
    meshes = gltf.get("meshes") or []
    accessors = gltf.get("accessors") or []
    scenes = gltf.get("scenes") or []
    if not scenes:
        raise GLBNormalizeError("GLB has no scenes to measure")

    scene = scenes[gltf.get("scene", 0)]
    global_min = np.full(3, np.inf)
    global_max = np.full(3, -np.inf)
    found_any = False

    def visit(node_index: int, parent_matrix: np.ndarray):
        nonlocal global_min, global_max, found_any
        node = nodes[node_index]
        world_matrix = parent_matrix @ _node_local_matrix(node)

        if "mesh" in node:
            for primitive in meshes[node["mesh"]].get("primitives", []):
                position_index = primitive.get("attributes", {}).get("POSITION")
                if position_index is None:
                    continue
                accessor = accessors[position_index]
                amin, amax = accessor.get("min"), accessor.get("max")
                if amin is None or amax is None:
                    raise GLBNormalizeError(
                        "A POSITION accessor is missing min/max - cannot measure bounding box"
                    )
                corners = np.array(
                    [[x, y, z, 1.0] for x in (amin[0], amax[0]) for y in (amin[1], amax[1]) for z in (amin[2], amax[2])]
                )
                world_corners = (world_matrix @ corners.T).T[:, :3]
                global_min = np.minimum(global_min, world_corners.min(axis=0))
                global_max = np.maximum(global_max, world_corners.max(axis=0))
                found_any = True

        for child_index in node.get("children", []):
            visit(child_index, world_matrix)

    for root_index in scene.get("nodes", []):
        visit(root_index, np.eye(4))

    if not found_any:
        raise GLBNormalizeError("No mesh geometry with POSITION bounds found in the default scene")

    return global_min, global_max


def normalize_glb_bytes(data: bytes, target_max_dimension: float = TARGET_MAX_DIMENSION) -> tuple[bytes, dict]:
    """
    Returns (bytes_to_store, info). `info` always has a "changed" bool;
    when True it also carries "original_max_dimension" and "scale_applied"
    for logging. Raises GLBNormalizeError on structurally invalid input -
    callers should catch this and fall back to storing the original bytes
    rather than lose the model entirely.
    """
    gltf, bin_chunk = read_glb(data)

    asset = gltf.setdefault("asset", {"version": "2.0"})
    extras = asset.setdefault("extras", {})
    if extras.get(NORMALIZED_MARKER_KEY):
        return data, {"changed": False, "reason": "already_normalized"}

    aabb_min, aabb_max = compute_world_aabb(gltf)
    dimensions = aabb_max - aabb_min
    max_dimension = float(np.max(dimensions))
    if not np.isfinite(max_dimension) or max_dimension <= 0:
        raise GLBNormalizeError(f"Degenerate bounding box: {dimensions.tolist()}")

    scale = target_max_dimension / max_dimension

    nodes = gltf.setdefault("nodes", [])
    scenes = gltf["scenes"]
    scene = scenes[gltf.get("scene", 0)]
    original_roots = list(scene.get("nodes", []))

    wrapper_index = len(nodes)
    nodes.append({
        "name": "menu3d_normalize_root",
        "scale": [scale, scale, scale],
        "children": original_roots,
    })
    scene["nodes"] = [wrapper_index]

    extras[NORMALIZED_MARKER_KEY] = target_max_dimension
    extras[ORIGINAL_DIMENSION_KEY] = max_dimension

    return write_glb(gltf, bin_chunk), {
        "changed": True,
        "original_max_dimension": max_dimension,
        "scale_applied": scale,
    }
