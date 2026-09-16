"""Post-process a Blender-exported .usdz: replace WebP textures (unsupported
by iOS Quick Look), patch the USD shader references, and repackage every
original resource as an ARKit-compliant .usdz.

Usage: python fix_usdz_textures.py <input.usdz> <output.usdz>
"""
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image
from pxr import Sdf, Usd, UsdShade

input_usdz, output_usdz = sys.argv[1], sys.argv[2]


def add_aligned(zf, arcname, data):
    # USDZ requires every file to start on a 64-byte boundary, uncompressed.
    zi = zipfile.ZipInfo(arcname)
    zi.compress_type = zipfile.ZIP_STORED
    header_size = 30 + len(arcname.encode("utf-8"))
    offset = zf.fp.tell()
    pad = (64 - (offset + header_size) % 64) % 64
    zi.extra = b"\0" * pad
    zf.writestr(zi, data)


workdir = Path(tempfile.mkdtemp())
try:
    with zipfile.ZipFile(input_usdz) as z:
        source_names = [name for name in z.namelist() if not name.endswith("/")]
        z.extractall(workdir)

    usd_names = [name for name in source_names if name.endswith((".usdc", ".usda"))]
    if not usd_names:
        raise RuntimeError("USDZ has no USD layer")

    def archive_name(path):
        return path.relative_to(workdir).as_posix()

    # Keep the archive self-contained.  The former implementation wrote only
    # converted WebP textures and accidentally dropped original JPG/PNG assets.
    # Apple Quick Look then received a structurally valid package with missing
    # material resources.
    renamed = {}
    for source in workdir.rglob("*"):
        if not source.is_file() or source.suffix.lower() != ".webp":
            continue

        image = Image.open(source)
        has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
        suffix = ".png" if has_alpha else ".jpg"
        destination = source.with_suffix(suffix)
        if destination.exists():
            destination = source.with_name(f"{source.stem}-quicklook{suffix}")
        if has_alpha:
            image.convert("RGBA").save(destination, "PNG")
        else:
            image.convert("RGB").save(destination, "JPEG", quality=90)
        image.close()
        renamed[archive_name(source)] = archive_name(destination)
        source.unlink()

    def resolve(asset_path):
        return renamed.get(asset_path.replace("\\", "/").lstrip("./"))

    # Blender puts material references in the root layer.  Update every USD
    # layer anyway so packaged sublayers work on both old and new exporters.
    for name in usd_names:
        stage = Usd.Stage.Open(str(workdir / name))
        if stage is None:
            raise RuntimeError(f"could not open USD layer: {name}")
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
            if new_path:
                print("shader texture:", prim.GetPath(), asset.path, "->", new_path)
                file_input.Set(Sdf.AssetPath(new_path))
        stage.GetRootLayer().Save()
        stage = None

    if os.path.exists(output_usdz):
        os.remove(output_usdz)

    # USDZ requires its root USD layer to be the first uncompressed,
    # 64-byte-aligned entry.  Keep every remaining source asset after it.
    root_layer = usd_names[0]
    output_names = [root_layer] + [
        name for name in source_names if name != root_layer and name not in renamed
    ] + sorted(set(renamed.values()))
    output_names = list(dict.fromkeys(output_names))
    with zipfile.ZipFile(output_usdz, "w") as zf:
        for name in output_names:
            source = workdir / name
            if not source.is_file():
                raise RuntimeError(f"USDZ resource missing after conversion: {name}")
            add_aligned(zf, name, source.read_bytes())

    print("wrote", output_usdz)
finally:
    shutil.rmtree(workdir, ignore_errors=True)
