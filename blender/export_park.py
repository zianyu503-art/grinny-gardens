"""Turn the hand-made park scene (GRINNY_GARDENS.blend) into the game level.

Reads blender/layout.json, scales the park, spreads its zones apart along the route,
keeps moving parts as separate nodes, and writes:
  public/models/park.glb   all static scenery (one node per zone) + moving parts
  public/park.json         colliders, light sources and named positions (game coordinates)

usage: blender -b --factory-startup --python blender/export_park.py
"""
import json
import os
import re

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CFG = json.load(open(os.path.join(ROOT, "blender", "layout.json")))
S = CFG["scale"]
ZONES = CFG["zones"]
offset, acc = {}, 0.0
for z in ZONES:
    acc += z["gap"]
    offset[z["name"]] = acc

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, CFG["source"]))


def zone_of(y):
    for z in ZONES:
        if z["y0"] <= y < z["y1"]:
            return z["name"]
    return ZONES[-1]["name"] if y >= ZONES[-1]["y0"] else ZONES[0]["name"]


def to_game(v):
    """Blender (x, y, z) -> three.js (x, y, z) with the route running toward -Z."""
    return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


# ------------------------------------------------------------------ lights -> data, then remove
lights = []
for o in list(bpy.data.objects):
    if o.type == "LIGHT" and o.data.type == "POINT":
        lights.append(dict(src=o.matrix_world.translation.copy(), color=list(o.data.color), energy=o.data.energy, name=o.name))
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA") or any(c.name.startswith("07") for c in o.users_collection):
        bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------ materials: flatten procedural colour
for m in bpy.data.materials:
    if not m.node_tree:
        continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if not b:
        continue
    bc = b.inputs["Base Color"]
    if bc.is_linked and bc.links[0].from_node.type == "VALTORGB":
        col = bc.links[0].from_node.color_ramp.evaluate(0.45)
        m.node_tree.links.remove(bc.links[0])
        bc.default_value = col
    nrm = b.inputs["Normal"]
    if nrm.is_linked:
        m.node_tree.links.remove(nrm.links[0])

# ------------------------------------------------------------------ curves / text / modifiers -> meshes
bpy.ops.object.select_all(action="DESELECT")
conv = [o for o in bpy.data.objects if o.type in ("CURVE", "FONT") or (o.type == "MESH" and o.modifiers)]
for o in conv:
    o.select_set(True)
if conv:
    bpy.context.view_layer.objects.active = conv[0]
    bpy.ops.object.convert(target="MESH")
for o in list(bpy.data.objects):
    if o.type != "MESH" or len(o.data.polygons) == 0:
        bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.data.objects:
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw
    if o.data.users > 1:  # instanced meshes must be single-user before transforms can be applied
        o.data = o.data.copy()

# ------------------------------------------------------------------ fun-house maze: keep the gaps at the rear walkable
TRIM_Y = CFG.get("mazeEndY", 42.3)  # maze walls may not reach closer than this to the rear facade (source units)
trimmed_x = []
for o in list(bpy.data.objects):
    if not o.name.startswith("Cutaway interior maze"):
        continue
    mn, mx = bbox(o)
    if mx.y > TRIM_Y and (mx.y - mn.y) > (mx.x - mn.x):
        inv = o.matrix_world.inverted()
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            if w.y > TRIM_Y:
                w.y = TRIM_Y
                v.co = inv @ w
        o.data.update()
        trimmed_x.append((mn.x + mx.x) / 2)
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
    if o.name.startswith("Peeling dark striped wallpaper"):
        mn, mx = bbox(o)
        if mx.y > TRIM_Y + 0.05 and any(abs((mn.x + mx.x) / 2 - x) < 0.35 for x in trimmed_x):
            bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------ assign zones, drop park-long site pieces
DROP_LONG = ("Perimeter", "foundation", "Wet asphalt", "Worn path slab", "Long drag scrape", "Far perimeter")
objs = []
for o in list(bpy.data.objects):
    mn, mx = bbox(o)
    size = mx - mn
    if any(k in o.name for k in DROP_LONG) and max(size.x, size.y) > 18:
        bpy.data.objects.remove(o, do_unlink=True)
        continue
    o["zone"] = zone_of((mn.y + mx.y) / 2)
    objs.append(o)

# scale + spread
for o in objs:
    T = Matrix.Translation((0, offset[o["zone"]], 0)) @ Matrix.Scale(S, 4)
    o.matrix_world = T @ o.matrix_world


def src_y(y, zone):
    return y * S + offset[zone]


# ------------------------------------------------------------------ moving parts
def group(name_test):
    return [o for o in objs if o.name in bpy.data.objects and name_test(o.name)]


SPECIAL = {}


def special(name, members, pivot_fn):
    if not members:
        print("WARN no members for", name)
        return
    pts = [p for o in members for p in (o.matrix_world @ Vector(c) for c in o.bound_box)]
    mn = Vector([min(p[i] for p in pts) for i in range(3)])
    mx = Vector([max(p[i] for p in pts) for i in range(3)])
    SPECIAL[name] = dict(members=members, pivot=pivot_fn(mn, mx), min=mn, max=mx)


gate_parts = group(lambda n: n.startswith("Entrance iron gate"))
special("GateL", [o for o in gate_parts if bbox(o)[1].x <= 0.05 * S], lambda a, b: Vector((a.x, (a.y + b.y) / 2, 0)))
special("GateR", [o for o in gate_parts if bbox(o)[1].x > 0.05 * S], lambda a, b: Vector((b.x, (a.y + b.y) / 2, 0)))
for n in (1, 2, 3):
    special("Gate%d" % n, group(lambda s, n=n: s.startswith("Gate %d" % n)), lambda a, b: Vector(((a.x + b.x) / 2, (a.y + b.y) / 2, 0)))
special("Bridge", group(lambda s: any(k in s for k in ("Suspended bridge", "Bridge rope", "Bridge lower rope", "Bridge sagging"))),
        lambda a, b: Vector(((a.x + b.x) / 2, (a.y + b.y) / 2, 0)))
mast = group(lambda s: s.startswith("Carousel central mast"))[0]
mast_c = sum((mast.matrix_world @ Vector(c) for c in mast.bound_box), Vector()) / 8
special("CarouselTop", group(lambda s: s.startswith("Carousel") and not any(k in s for k in ("raised deck", "deck gold rim"))),
        lambda a, b: Vector((mast_c.x, mast_c.y, 0)))
special("Orb", group(lambda s: s.startswith("Blue electric orb") or s.startswith("Static electrical arc")),
        lambda a, b: (a + b) / 2)
special_members = {o.name for g in SPECIAL.values() for o in g["members"]}

# ------------------------------------------------------------------ colliders
SKIP = ("cable", "rope", "scrape", "puddle", "bulb", "glow", "stain", "lettering", "Haunted house floor", "floor",
        "passage", "slab", "service path", "open-mouth mask", "wallpaper", "pit", "Pit", "darkness", "lip", "Bridge",
        "bridge", "drawing", "Crayon", "pennant", "flag", "arc", "Discarded", "candy stick", "Stale popcorn", "spark",
        "pupil", "Dead pinpoint", "stitch", "grin", "nose", "decal", "Drip", "leaf", "Leaf", "debris", "Debris",
        "Shard", "shard", "litter", "Litter", "paper", "Paper", "boarding", "Bottle", "bottle", "tooth", "Tooth",
        "teeth", "cheek", "hair", "eye socket", "Clown")
colliders = []
for o in objs:
    if o.name not in bpy.data.objects:
        continue
    mn, mx = bbox(o)
    if mx.z < 0.7 or mn.z > 2.2:
        continue
    if any(k in o.name for k in SKIP):
        continue
    if (mx.x - mn.x) * (mx.y - mn.y) < 0.004:
        continue
    tag = ""
    for g, info in SPECIAL.items():
        if o in info["members"]:
            tag = g
    colliders.append([round(mn.x, 2), round(mx.x, 2), round(-mx.y, 2), round(-mn.y, 2), tag])

# ------------------------------------------------------------------ named positions (before joining)
def center_of(prefix, exact=False):
    g = group(lambda s: s == prefix or (not exact and s.startswith(prefix)))
    if not g:
        print("WARN missing", prefix)
        return None
    pts = [p for o in g for p in (o.matrix_world @ Vector(c) for c in o.bound_box)]
    mn = Vector([min(p[i] for p in pts) for i in range(3)])
    mx = Vector([max(p[i] for p in pts) for i in range(3)])
    return dict(c=to_game((mn + mx) / 2), min=to_game(mn), max=to_game(mx))


names = {
    "booth": "Ticket booth shell", "generator": "Old diesel generator", "orb": "Blue electric orb",
    "gatePier": "Gate pier foot", "carouselDeck": "Carousel raised deck", "bumperSlab": "Bumper car slab",
    "tentWall": "Circus striped wall", "tentPlacard": "Circus entry placard board", "teacups": "Teacup ride platform",
    "popcorn": "Old popcorn stand body", "cottonCandy": "Cotton candy cart body", "striker": "Strength-test striking base",
    "billboard": "Mascot billboard", "clownMask": "Giant clown face", "funhouseFloor": "Haunted house floor",
    "rearLintel": "Rear exit lintel", "staffPassage": "Staff concrete passage", "locker": "Maintenance steel locker",
    "coasterPath": "Narrow coaster service path", "pit": "Bottomless black pit", "pitLip": "Pit rough retaining lip",
    "ferrisAxle": "Ferris central axle", "ferrisPlatform": "Ferris boarding platform", "wagon": "Beast wagon chassis",
    "finalStall": "Final fair stall counter", "staffEastWall": "Staff east cutaway wall", "barrels": "Rusted maintenance barrel",
}
points = {k: center_of(v) for k, v in names.items()}
for n in (1, 2, 3):
    points["gate%d" % n] = center_of("Gate %d / leaf stile" % n)
points["mainGate"] = center_of("Entrance iron gate")

zones_out = {}
for z in ZONES:
    y0 = max(z["y0"], -6)
    y1 = min(z["y1"], 84)
    zones_out[z["name"]] = dict(zFront=round(-(y0 * S + offset[z["name"]]), 2), zBack=round(-(y1 * S + offset[z["name"]]), 2))

light_out = []
for l in lights:
    y = l["src"].y
    zn = zone_of(y)
    p = Vector((l["src"].x * S, y * S + offset[zn], l["src"].z * S))
    light_out.append(dict(pos=to_game(p), color=[round(c, 3) for c in l["color"]], energy=l["energy"], name=l["name"]))

# ------------------------------------------------------------------ join: static per zone, specials with pivots
def join(members, name, pivot):
    bpy.ops.object.select_all(action="DESELECT")
    for o in members:
        o.select_set(True)
    bpy.context.view_layer.objects.active = members[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(members) > 1:
        bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = name
    for v in j.data.vertices:
        v.co -= pivot
    j.location = pivot
    return j


final = []
for name, info in SPECIAL.items():
    members = [o for o in info["members"] if o.name in bpy.data.objects]
    final.append(join(members, name, info["pivot"]))
    info["pivot_game"] = to_game(info["pivot"])
for z in ZONES:
    members = [o for o in bpy.data.objects if o.get("zone") == z["name"] and o.name not in special_members and o not in final]
    members = [o for o in members if o.type == "MESH"]
    if members:
        final.append(join(members, "Static_" + z["name"], Vector((0, 0, 0))))

tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in final)
print("TRIS total", tris, {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in final})

out_glb = os.path.join(ROOT, "public", "models", "park.glb")
bpy.ops.object.select_all(action="DESELECT")
for o in final:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", use_selection=True, export_apply=True,
                          export_lights=False, export_cameras=False)

data = dict(scale=S, halfWidth=round(16.1 * S, 2), zones=zones_out, colliders=colliders, lights=light_out, points=points,
            pivots={k: v["pivot_game"] for k, v in SPECIAL.items()},
            specialBounds={k: dict(min=to_game(v["min"]), max=to_game(v["max"])) for k, v in SPECIAL.items()})
json.dump(data, open(os.path.join(ROOT, "public", "park.json"), "w"), ensure_ascii=False)
print("EXPORTED", out_glb, os.path.getsize(out_glb) // 1024, "KB;", len(colliders), "colliders;", len(light_out), "lights")
