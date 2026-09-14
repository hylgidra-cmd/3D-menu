"""Blender headless script: import a .glb and export it as .usdz for iOS
AR Quick Look. Run via `blender --background --factory-startup --python
glb_to_usdz.py -- <input.glb> <output.usdz>`.
"""
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb, output_usdz = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=input_glb)

# Blender's USD exporter always re-encodes "NEW"-mode textures as WebP,
# which iOS Quick Look can't read - fix_usdz_textures.py swaps them for
# JPEG afterwards.
bpy.ops.wm.usd_export(
    filepath=output_usdz,
    export_textures_mode="NEW",
    overwrite_textures=True,
    generate_preview_surface=True,
)
