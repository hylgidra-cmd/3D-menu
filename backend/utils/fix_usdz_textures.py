"""Post-process a Blender-exported .usdz: swap WebP textures (unsupported by
iOS Quick Look) for JPEG, patch the USD shader references to match, and
repackage as an ARKit-compliant .usdz.

Usage: python fix_usdz_textures.py <input.usdz> <output.usdz>
"""
import os
import shutil
import sys
import tempfile
import zipfile

from PIL import Image
from pxr import Sdf, Usd, UsdShade

input_usdz, output_usdz = sys.argv[1], sys.argv[2]

workdir = tempfile.mkdtemp()
with zipfile.ZipFile(input_usdz) as z:
    z.extractall(workdir)
    usdc_names = [n for n in z.namelist() if n.endswith((".usdc", ".usda"))]

usdc_path = os.path.join(workdir, usdc_names[0])

textures_dir = os.path.join(workdir, "textures")
renamed = {}
if os.path.isdir(textures_dir):
    for name in os.listdir(textures_dir):
        if name.lower().endswith(".webp"):
            src = os.path.join(textures_dir, name)
            dst = os.path.join(textures_dir, os.path.splitext(name)[0] + ".jpg")
            Image.open(src).convert("RGB").save(dst, "JPEG", quality=90)
            os.remove(src)
            renamed[f"textures/{name}"] = f"textures/{os.path.splitext(name)[0]}.jpg"

def resolve(path):
    key = path.lstrip("./")
    return renamed.get(key)

stage = Usd.Stage.Open(usdc_path)
for prim in stage.Traverse():
    shader = UsdShade.Shader(prim)
    if not shader:
        continue
    file_input = shader.GetInput("file")
    if not file_input:
        continue
    asset = file_input.Get()
    if not asset:
        continue
    new_path = resolve(asset.path)
    print("shader texture:", prim.GetPath(), asset.path, "->", new_path)
    if new_path:
        file_input.Set(Sdf.AssetPath(new_path))
stage.GetRootLayer().Save()


def add_aligned(zf, arcname, data):
    # USDZ requires every file to start on a 64-byte boundary, uncompressed.
    zi = zipfile.ZipInfo(arcname)
    zi.compress_type = zipfile.ZIP_STORED
    header_size = 30 + len(arcname.encode("utf-8"))
    offset = zf.fp.tell()
    pad = (64 - (offset + header_size) % 64) % 64
    zi.extra = b"\0" * pad
    zf.writestr(zi, data)


if os.path.exists(output_usdz):
    os.remove(output_usdz)

usdc_arcname = os.path.basename(usdc_path)
with zipfile.ZipFile(output_usdz, "w") as zf:
    with open(usdc_path, "rb") as f:
        add_aligned(zf, usdc_arcname, f.read())
    for new_rel in sorted(set(renamed.values())):
        with open(os.path.join(workdir, new_rel), "rb") as f:
            add_aligned(zf, new_rel, f.read())

shutil.rmtree(workdir, ignore_errors=True)
print("wrote", output_usdz)
