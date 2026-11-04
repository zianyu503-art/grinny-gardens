"""Shrink a Chapter 2 zone GLB for the web: resize every texture to at most MAX px,
merge byte-identical images, and re-export with JPEG textures.

usage: blender -b --factory-startup -P blender/map_ch2/shrink_glb.py -- <in.glb> [out.glb] [max_px]
"""
import hashlib
import os
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
src = args[0]
dst = args[1] if len(args) > 1 else src
MAX = int(args[2]) if len(args) > 2 else 512

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

# resize, then merge duplicates by pixel hash
seen = {}
for img in list(bpy.data.images):
    if not img.has_data and img.size[0] == 0:
        continue
    w, h = img.size
    if max(w, h) > MAX:
        k = MAX / max(w, h)
        img.scale(max(1, int(w * k)), max(1, int(h * k)))
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    key = hashlib.md5(str(img.size[:]).encode() + (px * 255).astype(np.uint8).tobytes()).hexdigest()
    if key in seen:
        img.user_remap(seen[key])
        bpy.data.images.remove(img)
    else:
        seen[key] = img
        img.pack()

print("SHRINK images", len(seen))
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_image_format="JPEG",
                          export_jpeg_quality=80, export_apply=False)
print("SHRINK_DONE", dst, os.path.getsize(dst), "bytes")
