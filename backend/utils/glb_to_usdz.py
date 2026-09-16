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

# Blender 3.4 (the version in Debian bookworm, and therefore the Docker
# image) calls this option ``export_textures``.  Blender 4.x renamed it to
# ``export_textures_mode``.  Passing the new name to 3.4 makes the whole
# export fail with "keyword unrecognized", which was the production iOS
# failure.  Inspect the installed operator so either supported Blender
# version writes a self-contained USDZ.
properties = bpy.ops.wm.usd_export.get_rna_type().properties
export_options = {
    "filepath": output_usdz,
    "overwrite_textures": True,
    "generate_preview_surface": True,
}

if "export_textures_mode" in properties:
    export_options["export_textures_mode"] = "NEW"
elif "export_textures" in properties:
    export_options["export_textures"] = True

# This option also changed names between Blender releases.  A USDZ must
# reference bundled textures with relative paths so Quick Look can find them.
if "relative_paths" in properties:
    export_options["relative_paths"] = True
elif "relative_texture_paths" in properties:
    export_options["relative_texture_paths"] = True

bpy.ops.wm.usd_export(**export_options)
