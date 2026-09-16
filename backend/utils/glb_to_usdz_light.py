"""Create a compact Quick Look USDZ from a standard GLB without Blender.

Render's Free instances have 512MB RAM. Blender exceeds that limit while
loading generated food models, so this converter reads the glTF data directly
and writes the supported USD Preview Surface subset that iOS Quick Look needs.
"""
from __future__ import annotations

import base64
import io
import json
import math
import struct
import sys
import zipfile
from pathlib import Path

from PIL import Image


COMPONENTS = {
    5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
    5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4),
}
TYPE_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(data: bytes):
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("not a GLB file")
    _magic, version, total = struct.unpack_from("<III", data, 0)
    if version != 2 or total > len(data):
        raise ValueError("unsupported or truncated GLB")
    offset = 12
    gltf = binary = None
    while offset + 8 <= total:
        size, kind = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8:offset + 8 + size]
        if kind == 0x4E4F534A:
            gltf = json.loads(chunk.decode("utf-8"))
        elif kind == 0x004E4942:
            binary = chunk
        offset += 8 + size
    if not gltf or binary is None:
        raise ValueError("GLB is missing JSON or binary data")
    return gltf, binary


def accessor(gltf, binary, index):
    item = gltf["accessors"][index]
    view = gltf["bufferViews"][item["bufferView"]]
    fmt, byte_size = COMPONENTS[item["componentType"]]
    count = TYPE_SIZE[item["type"]]
    stride = view.get("byteStride", count * byte_size)
    start = view.get("byteOffset", 0) + item.get("byteOffset", 0)
    unpack = struct.Struct("<" + fmt * count).unpack_from
    values = [unpack(binary, start + position * stride) for position in range(item["count"])]
    if item.get("normalized"):
        def normalize(value):
            if fmt in ("b", "h"):
                return max(value / (127 if fmt == "b" else 32767), -1.0)
            if fmt in ("B", "H"):
                return value / (255 if fmt == "B" else 65535)
            return value
        values = [tuple(normalize(value) for value in row) for row in values]
    return values


def number(value):
    if not math.isfinite(float(value)):
        return "0"
    return format(float(value), ".7g")


def tuple_text(values):
    return "(" + ", ".join(number(value) for value in values) + ")"


def matrix_for_node(node):
    if "matrix" in node:
        value = node["matrix"]
        return [[value[column * 4 + row] for column in range(4)] for row in range(4)]

    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    sx, sy, sz = node.get("scale", [1, 1, 1])
    tx, ty, tz = node.get("translation", [0, 0, 0])
    rotation = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)],
    ]
    return [
        [rotation[0][0] * sx, rotation[0][1] * sy, rotation[0][2] * sz, tx],
        [rotation[1][0] * sx, rotation[1][1] * sy, rotation[1][2] * sz, ty],
        [rotation[2][0] * sx, rotation[2][1] * sy, rotation[2][2] * sz, tz],
        [0, 0, 0, 1],
    ]


def matrix_text(matrix):
    return "(" + ", ".join(tuple_text(row) for row in matrix) + ")"


def image_bytes(gltf, binary, image):
    if "bufferView" in image:
        view = gltf["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        return binary[start:start + view["byteLength"]]
    uri = image.get("uri", "")
    if uri.startswith("data:") and "," in uri:
        return base64.b64decode(uri.split(",", 1)[1])
    raise ValueError("external texture URL is not supported")


def export_textures(gltf, binary):
    exported = {}
    files = {}
    for index, image in enumerate(gltf.get("images", [])):
        try:
            raw = image_bytes(gltf, binary, image)
            loaded = Image.open(io.BytesIO(raw))
            loaded.load()
            has_alpha = loaded.mode in ("RGBA", "LA") or "transparency" in loaded.info
            extension = "png" if has_alpha else "jpg"
            output = io.BytesIO()
            if has_alpha:
                loaded.convert("RGBA").save(output, "PNG")
            else:
                loaded.convert("RGB").save(output, "JPEG", quality=90)
            loaded.close()
        except Exception:
            continue
        name = f"textures/image-{index}.{extension}"
        exported[index] = name
        files[name] = output.getvalue()
    return exported, files


def texture_for_material(gltf, material, images):
    texture = (material.get("pbrMetallicRoughness") or {}).get("baseColorTexture")
    if not texture:
        return None
    source = (gltf.get("textures") or [])[texture["index"]].get("source")
    return images.get(source)


def material_usda(gltf, images):
    lines = ["  def Scope \"Materials\"\n  {"]
    materials = gltf.get("materials") or [{}]
    for index, material in enumerate(materials):
        pbr = material.get("pbrMetallicRoughness") or {}
        color = pbr.get("baseColorFactor", [1, 1, 1, 1])
        texture = texture_for_material(gltf, material, images)
        base = f"/Model/Materials/Material_{index}"
        lines += [
            f"    def Material \"Material_{index}\"",
            "    {",
            f"      token outputs:surface.connect = <{base}/PreviewSurface.outputs:surface>",
            "      def Shader \"PreviewSurface\"",
            "      {",
            "        uniform token info:id = \"UsdPreviewSurface\"",
            f"        color3f inputs:diffuseColor = {tuple_text(color[:3])}",
            f"        float inputs:metallic = {number(pbr.get('metallicFactor', 1))}",
            f"        float inputs:roughness = {number(pbr.get('roughnessFactor', 1))}",
            "        token outputs:surface",
            "      }",
        ]
        if texture:
            lines += [
                "      def Shader \"PrimvarReader_st\"",
                "      {",
                "        uniform token info:id = \"UsdPrimvarReader_float2\"",
                "        token inputs:varname = \"st\"",
                "        float2 outputs:result",
                "      }",
                "      def Shader \"BaseColorTexture\"",
                "      {",
                "        uniform token info:id = \"UsdUVTexture\"",
                f"        asset inputs:file = @{texture}@",
                f"        float2 inputs:st.connect = <{base}/PrimvarReader_st.outputs:result>",
                "        float3 outputs:rgb",
                "        float outputs:a",
                "      }",
                f"      color3f inputs:diffuseColor.connect = <{base}/BaseColorTexture.outputs:rgb>",
            ]
        lines += ["    }"]
    lines += ["  }"]
    return lines


def primitive_usda(gltf, binary, primitive, primitive_index):
    attributes = primitive.get("attributes", {})
    if "POSITION" not in attributes:
        return []
    points = accessor(gltf, binary, attributes["POSITION"])
    if "indices" in primitive:
        indices = [row[0] for row in accessor(gltf, binary, primitive["indices"])]
    else:
        indices = list(range(len(points)))
    mode = primitive.get("mode", 4)
    if mode != 4:
        raise ValueError(f"unsupported primitive mode: {mode}")
    indices = indices[:len(indices) - len(indices) % 3]
    material = primitive.get("material", 0)
    lines = [
        f"      def Mesh \"Primitive_{primitive_index}\"",
        "      {",
        "        uniform token subdivisionScheme = \"none\"",
        "        point3f[] points = [" + ", ".join(tuple_text(row[:3]) for row in points) + "]",
        "        int[] faceVertexCounts = [" + ", ".join("3" for _ in range(len(indices) // 3)) + "]",
        "        int[] faceVertexIndices = [" + ", ".join(str(value) for value in indices) + "]",
        f"        rel material:binding = </Model/Materials/Material_{material}>",
    ]
    if "NORMAL" in attributes:
        normals = accessor(gltf, binary, attributes["NORMAL"])
        lines += [
            "        normal3f[] normals = [" + ", ".join(tuple_text(row[:3]) for row in normals) + "]",
            "        uniform token normalsInterpolation = \"vertex\"",
        ]
    if "TEXCOORD_0" in attributes:
        texcoords = accessor(gltf, binary, attributes["TEXCOORD_0"])
        lines += [
            "        texCoord2f[] primvars:st = [" + ", ".join(tuple_text((row[0], 1 - row[1])) for row in texcoords) + "] (interpolation = \"vertex\")",
        ]
    lines += ["      }"]
    return lines


def build_usda(gltf, binary, image_paths):
    scene = (gltf.get("scenes") or [{}])[gltf.get("scene", 0)]
    nodes = gltf.get("nodes") or []
    meshes = gltf.get("meshes") or []
    lines = [
        "#usda 1.0", "(", "    defaultPrim = \"Model\"", "    metersPerUnit = 1", "    upAxis = \"Y\"", ")",
        "def Xform \"Model\" (kind = \"component\")", "{",
    ]
    lines += material_usda(gltf, image_paths)

    visited = set()
    def node_lines(index, indent="  "):
        if index in visited:
            return []
        visited.add(index)
        node = nodes[index]
        output = [f'{indent}def Xform "Node_{index}"', indent + "{"]
        output += [indent + "  matrix4d xformOp:transform = " + matrix_text(matrix_for_node(node))]
        output += [indent + '  uniform token[] xformOpOrder = ["xformOp:transform"]']
        if "mesh" in node:
            for primitive_index, primitive in enumerate(meshes[node["mesh"]].get("primitives", [])):
                output += [indent + line for line in primitive_usda(gltf, binary, primitive, primitive_index)]
        for child in node.get("children", []):
            output += node_lines(child, indent + "  ")
        output += [indent + "}"]
        return output

    for node in scene.get("nodes", []):
        lines += node_lines(node)
    lines += ["}", ""]
    return "\n".join(lines).encode("utf-8")


def add_aligned(archive, name, data):
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_STORED
    header_size = 30 + len(name.encode("utf-8"))
    padding = (64 - (archive.fp.tell() + header_size) % 64) % 64
    info.extra = b"\0" * padding
    archive.writestr(info, data)


def convert(input_path, output_path):
    gltf, binary = read_glb(Path(input_path).read_bytes())
    image_paths, textures = export_textures(gltf, binary)
    usda = build_usda(gltf, binary, image_paths)
    with zipfile.ZipFile(output_path, "w") as archive:
        add_aligned(archive, "model.usda", usda)
        for name, data in textures.items():
            add_aligned(archive, name, data)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
