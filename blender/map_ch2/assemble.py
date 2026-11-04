"""Assemble the Chapter 2 map from the six zone chunks.

Builds the seam walls where neighbouring zones differ in width or height (no zone owns those),
exports them as public/models/ch2/zone_seams.glb, writes public/models/ch2/manifest.json and
renders a top-down overview of the whole map with the ceilings clipped away.

usage: blender -b --factory-startup -P blender/map_ch2/assemble.py
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "public", "models", "ch2")
T = 0.3  # wall thickness

# name, half width of the walkable box, y range (route runs along +Y)
ZONES = [
    ("zone_a_entry", 6, 0, 16),
    ("zone_b_lockers", 10, 16, 34),
    ("zone_c_sewing", 18, 34, 74),
    ("zone_d_packing", 18, 74, 114),
    ("zone_e_warehouse", 14, 114, 144),
    ("zone_f_core", 12, 144, 170),
]

bkit.reset_scene()

# import every chunk and measure how tall it is (top of its ceiling slab)
tops = {}
for name, hw, y0, y1 in ZONES:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    zs = []
    for o in new:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            if -hw - 1 < p.x < hw + 1 and y0 - 1 < p.y < y1 + 1:
                zs.append(p.z)
    tops[name] = round(max(zs), 2)
print("ASSEMBLE tops", tops)

# seam walls at each boundary
wall_mat = bkit.pbr_material("CH2_seam_wall", bkit.polyhaven_texture("peeling_painted_wall", "1k"),
                             scale=1.0, tint=(0.75, 0.72, 0.7))
seams = []


def box(name, x0, x1, y0, y1, z0, z1):
    bpy.ops.mesh.primitive_cube_add(location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.name = name
    o.scale = ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(wall_mat)
    bkit.box_uv(o, size=1.0)
    seams.append(o)
    return [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3), round((z0 + z1) / 2, 3),
            round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3), 0.0]


colliders = []
for (pa, wa, _, yb), (pb, wb, _, _) in zip(ZONES, ZONES[1:]):
    ta, tb = tops[pa], tops[pb]
    if wb > wa:  # next zone is wider: close the wall either side of the narrower zone
        for s in (-1, 1):
            xs = sorted((s * (wa + T), s * (wb + T)))
            colliders.append(box(f"S_side_{pb}_{'w' if s < 0 else 'e'}", *xs, yb, yb + T, 0.0, tb))
    if tb > ta:  # next zone is taller: close the band above the far wall of the previous zone
        w = min(wa, wb) + T
        colliders.append(box(f"S_top_{pb}", -w, w, yb, yb + T, ta, tb))
print("ASSEMBLE seams", [o.name for o in seams])

bkit.export_glb(os.path.join(OUT, "zone_seams.glb"), seams, image_format="JPEG")

manifest = {
    "note": "Blender coordinates (metres, Z up, route along +Y). Three.js: (x, z, -y).",
    "zones": [{"name": n, "glb": n + ".glb", "data": n + ".json", "x": [-w, w], "y": [y0, y1],
               "top": tops[n]} for n, w, y0, y1 in ZONES],
    "seams": {"glb": "zone_seams.glb", "colliders": colliders},
}
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)

# overview: top-down orthographic, ceilings clipped, Workbench so lighting ignores the roof
cut = 3.2
cam_z = 60.0
bpy.ops.object.camera_add(location=(0, 85, cam_z), rotation=(0, 0, math.radians(90)))
cam = bpy.context.active_object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 176
cam.data.clip_start = cam_z - cut
cam.data.clip_end = cam_z + 5
sc = bpy.context.scene
sc.camera = cam
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.display.shading.show_cavity = True
sc.display.shading.show_shadows = False
sc.render.resolution_x, sc.render.resolution_y = 3520, 840
sc.render.film_transparent = False
sc.world = sc.world or bpy.data.worlds.new("W")
sc.display_settings.display_device = "sRGB"

# mark lights and markers from each zone's JSON as small coloured discs
def dot_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)  # Workbench draws untextured materials in this colour
    return m


DOTS = {"light": dot_mat("CH2_dot_light", (1.0, 0.85, 0.3)),
        "route": dot_mat("CH2_dot_route", (0.2, 1.0, 0.4)),
        "marker": dot_mat("CH2_dot_marker", (1.0, 0.25, 0.25))}


def dot(x, y, z, r, kind):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.02, location=(x, y, z))
    bpy.context.active_object.data.materials.append(DOTS[kind])


for name, *_ in ZONES:
    data = json.load(open(os.path.join(OUT, name + ".json")))
    for li in data.get("lights", []):
        dot(li["pos"][0], li["pos"][1], cut - 0.1, 0.35, "light")
    for mk, (x, y, _z) in data.get("markers", {}).items():
        dot(x, y, cut - 0.05, 0.3, "route" if "patrol" in mk or "rail" in mk else "marker")
path = os.path.join(ROOT, "renders", "ch2_map_overview.png")
sc.render.filepath = path
bpy.ops.render.render(write_still=True)
print("ASSEMBLE_DONE", path)
