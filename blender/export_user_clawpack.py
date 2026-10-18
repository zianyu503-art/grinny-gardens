"""Export the hand-made ClawPack.blend for the game.

  public/models/clawpack_full.glb   whole backpack (the pickup at the entrance)
  public/models/clawhands.glb       HandL / HandR claw heads, each jaw finger a separate part (JawL0..2, JawR0..2)

Materials are plain Principled BSDF in the source file, so they are exported as-is (no baking).

usage: blender -b --factory-startup --python blender/export_user_clawpack.py -- [path/to/ClawPack.blend]
"""
import os
import re
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = args[0] if args else os.path.join(lib.ROOT, "blender", "source", "ClawPack.blend")
OUT = os.path.join(lib.ROOT, "public", "models")

# hand parts: everything named LEFT BLUE / RIGHT RED except the cable that stays on the pack
HAND = {"L": "LEFT BLUE", "R": "RIGHT RED"}
PACK_ONLY = ("extendable main cable", "side cable socket")


def load():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for o in list(bpy.data.objects):
        if o.type in ("LIGHT", "CAMERA") or o.name == "Studio floor":
            bpy.data.objects.remove(o, do_unlink=True)
    # bake curves / text / modifiers into plain meshes
    for o in list(bpy.data.objects):
        if o.type in ("CURVE", "FONT") or (o.type == "MESH" and o.modifiers):
            lib.select_only(o)
            bpy.ops.object.convert(target="MESH")
    for o in bpy.data.objects:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw


def join(objs, name, pivot=Vector((0, 0, 0))):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(objs) > 1:
        bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = name
    j.data.name = name
    for v in j.data.vertices:
        v.co -= pivot
    j.location = pivot
    return j


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def decimate(o, target):
    n = tris(o)
    if n > target:
        d = o.modifiers.new("Dec", "DECIMATE")
        d.ratio = target / n
        lib.apply_mods(o)
    print("TRIS", o.name, n, "->", tris(o))


def export(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_lights=False, export_cameras=False)
    print("EXPORTED", path, os.path.getsize(path) // 1024, "KB")


def bbox_center(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector([(min(p[i] for p in pts) + max(p[i] for p in pts)) / 2 for i in range(3)])


# ------------------------------------------------------------------ 1. whole backpack (pickup)
load()
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
full = join(meshes, "ClawPack", Vector((0, 0, 0)))
decimate(full, 40000)
export(os.path.join(OUT, "clawpack_full.glb"), [full])

# ------------------------------------------------------------------ 2. claw hands with movable jaws
load()
parts = []
for side, prefix in HAND.items():
    objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(prefix)
            and not any(k in o.name for k in PACK_ONLY)]
    jaws = {}
    body = []
    for o in objs:
        m = re.search(r"jaw (\d) ", o.name + " ")
        if m and "actuator" not in o.name:
            jaws.setdefault(int(m.group(1)), []).append(o)
        else:
            body.append(o)
    # the hand pivots at the top of the strain relief, where the cable attaches
    top = max((o.matrix_world @ Vector(c)).z for o in body for c in o.bound_box)
    c = bbox_center(body)
    hand = join(body, "Hand" + side, Vector((c.x, c.y, top)))
    decimate(hand, 9000)
    parts.append(hand)
    for k, jobjs in sorted(jaws.items()):
        hinge = [o for o in jobjs if "hinge 0" in o.name and "inset" not in o.name and "pin" not in o.name]
        piv = bbox_center(hinge or jobjs)
        jaw = join(jobjs, "Jaw%s%d" % (side, k), piv)
        decimate(jaw, 2500)
        parts.append(jaw)
export(os.path.join(OUT, "clawhands.glb"), parts)
