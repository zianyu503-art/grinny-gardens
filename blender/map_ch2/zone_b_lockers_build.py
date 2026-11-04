"""Zone B (zone_b_lockers): staff locker room and washroom, Chapter 2.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/map_ch2/zone_b_lockers_build.py

Writes the level chunk GLB, the gameplay JSON, the saved .blend and two previews.
Coordinates follow blender/map_ch2/BRIEF.md: floor at z=0, interior x -10..10,
y 16..34, ceiling 3.5. Walls are 0.3 m thick and built outward. The far wall
(y 34..34.3) belongs to this zone and has one 2.4 x 3.0 m doorway.
"""
import sys
import os
import json
import math
import random

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_b_lockers"
SCRATCH = "/private/tmp/claude-504/-Users-alex-----2/df819384-06df-4249-8523-a5c0f94e5679/scratchpad/zb"
GLB_PATH = f"{ROOT}/public/models/ch2/{NAME}.glb"
JSON_PATH = f"{ROOT}/public/models/ch2/{NAME}.json"
BLEND_PATH = f"{ROOT}/blender/bake/map_ch2/{NAME}.blend"
EYE_PNG = f"{ROOT}/renders/ch2_{NAME}_eye.png"
TOP_PNG = f"{ROOT}/renders/ch2_{NAME}_top.png"
MODELS = f"{ROOT}/public/models"
PREVIEW_SAMPLES = 24

bkit.reset_scene()  # empty scene, metric, Cycles; must run before anything is built

rng = random.Random(20260)
COLLIDERS = []
MARKERS = {}
LIGHTS = []        # exported to JSON
PREVIEW_LIGHTS = []  # Blender-only lights for previews
SHELL = []         # objects built here (for triangle report)
PROPS = []         # imported prop instances


# ---------------------------------------------------------------- materials

def ph(name, asset, tint=None, rough=1.0):
    maps = bkit.polyhaven_texture(asset, "1k")
    return bkit.pbr_material(name, maps, scale=1.0, tint=tint, roughness_mult=rough)


def flat(name, color, rough=0.8, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1.0)
        b.inputs["Emission Strength"].default_value = emit
    return m


M = {
    "floor": ph("B_concrete_floor", "concrete_floor_02"),
    "tile": ph("B_washroom_tile", "floor_tiles_02", tint=(0.8, 0.82, 0.78), rough=1.2),
    "wall": ph("B_plaster_wall", "plastered_wall_04"),
    "ceiling": ph("B_ceiling_concrete", "rough_concrete"),
    "steel": ph("B_painted_steel", "rusty_painted_metal"),
    "rust": ph("B_rusty_metal", "rusty_metal_04"),
    "ceramic": ph("B_ceramic", "plastered_wall_04", tint=(0.86, 0.87, 0.84), rough=0.25),
    "hazard": ph("B_hazard_paint", "concrete_floor_02", tint=(1.0, 0.72, 0.14), rough=1.1),
    "board": ph("B_notice_board", "hessian_230"),
    "mirror": flat("B_mirror_glass", (0.72, 0.78, 0.78), rough=0.03, metal=1.0),
    "paper": flat("B_paper", (0.78, 0.75, 0.64), rough=0.85),
    "sign": flat("B_sign_red", (0.5, 0.07, 0.05), rough=0.5),
    "housing": flat("B_fixture_housing", (0.5, 0.5, 0.47), rough=0.45, metal=0.6),
    "tube_on": flat("B_tube_lit", (0.85, 0.93, 1.0), rough=0.4, emit=6.0),
    "tube_off": flat("B_tube_dead", (0.33, 0.34, 0.32), rough=0.5),
    "puddle": flat("B_puddle", (0.02, 0.025, 0.03), rough=0.03),
}


# ---------------------------------------------------------------- mesh bags

class Bag:
    """Collects boxes and cylinders in world space into one mesh object.

    One bag per material keeps the shell to a few objects. UVs are world-scale
    box projections (1 UV unit = uv metres), so Poly Haven tiles keep real scale.
    """

    def __init__(self, name, mat, uv=1.0, bevel=0.01):
        self.name, self.mat, self.uv, self.bevel = name, mat, uv, bevel
        self.bm = bmesh.new()

    def box(self, c, s, rot=0.0):
        cx, cy, cz = c
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        cr, sr = math.cos(rot), math.sin(rot)
        corners = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
                   (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        vs = [self.bm.verts.new((cx + x * cr - y * sr, cy + x * sr + y * cr, cz + z))
              for x, y, z in corners]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)):
            self.bm.faces.new([vs[i] for i in f])
        return self

    def cyl(self, c, r, h, axis="z", seg=12):
        m = Matrix.Translation(c)
        if axis == "y":
            m = m @ Matrix.Rotation(math.pi / 2, 4, "X")
        elif axis == "x":
            m = m @ Matrix.Rotation(math.pi / 2, 4, "Y")
        r0, r1 = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            x, y = r * math.cos(a), r * math.sin(a)
            r0.append(self.bm.verts.new(m @ Vector((x, y, -h / 2))))
            r1.append(self.bm.verts.new(m @ Vector((x, y, h / 2))))
        for i in range(seg):
            j = (i + 1) % seg
            self.bm.faces.new([r0[i], r0[j], r1[j], r1[i]])
        self.bm.faces.new(list(reversed(r0)))
        self.bm.faces.new(r1)
        return self

    def finish(self):
        bm = self.bm
        if self.bevel:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=self.bevel,
                            offset_type="OFFSET", segments=1, affect="EDGES",
                            clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            o = [i for i in range(3) if i != ax]
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (co[o[0]] / self.uv, co[o[1]] / self.uv)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(self.mat)
        obj = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(obj)
        SHELL.append(obj)
        return obj


# ---------------------------------------------------------------- props

TEMPLATES = {}


def template(path, key):
    objs = bkit.import_glb(path)
    for o in objs:
        bkit.apply_all(o)
    TEMPLATES[key] = objs
    return objs


def local_bounds(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def inst(tmpl, name, cx, cy, z0=0.0, rot=0.0, collide=False):
    """Linked copy of tmpl with its bounding-box centre at (cx, cy) and its
    bottom at z0. Copies share mesh data, so the GLB stores each mesh once."""
    lo, hi = local_bounds(tmpl)
    lc = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0))
    c, s = math.cos(rot), math.sin(rot)
    rc = Vector((lc.x * c - lc.y * s, lc.x * s + lc.y * c, 0))
    o = bpy.data.objects.new(name, tmpl.data)
    o.location = (cx - rc.x, cy - rc.y, z0 - lo.z)
    o.rotation_euler = (0, 0, rot)
    bpy.context.scene.collection.objects.link(o)
    PROPS.append(o)
    if collide:
        sx, sy, sz = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
        add_collider(cx, cy, z0 + sz / 2, sx, sy, sz, rot)
    return o


def add_collider(cx, cy, cz, sx, sy, sz, rot=0.0):
    COLLIDERS.append([round(v, 3) for v in (cx, cy, cz, sx, sy, sz, rot)])


def lathe_obj(profile, loc, mat, name, rot=(0, 0, 0)):
    o = bkit.lathe(profile, segments=20, name=name)
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(mat)
    SHELL.append(o)
    return o


# ---------------------------------------------------------------- shell

X0, X1 = -10.0, 10.0
Y0, Y1 = 16.0, 34.0
CEIL = 3.5

# floor slab: top surface at z=0 (zone floor)
Bag("B_floor", M["floor"], uv=3.0).box((0, 25.15, -0.15), (20.6, 18.3, 0.3)).finish()

# washroom floor tile laid over the slab
Bag("B_washroom_tile", M["tile"], uv=1.2, bevel=0).box(
    (7.0, 30.0, 0.004), (6.0, 8.0, 0.008)).finish()

# walls: 0.3 m thick, outward from the box. Near wall (y=16) belongs to zone A.
walls = Bag("B_walls", M["wall"], uv=2.5)
walls.box((-10.15, 25.0, 1.75), (0.3, 18.0, 3.5))          # west
walls.box((10.15, 25.0, 1.75), (0.3, 18.0, 3.5))           # east
walls.box((-5.75, 34.15, 1.75), (9.1, 0.3, 3.5))           # far wall, left of door
walls.box((5.75, 34.15, 1.75), (9.1, 0.3, 3.5))            # far wall, right of door
walls.box((0.0, 34.15, 3.25), (2.4, 0.3, 0.5))             # lintel over doorway
walls.box((4.0, 27.2, 1.75), (0.15, 2.4, 3.5))             # washroom wall, south of door
walls.box((4.0, 31.95, 1.75), (0.15, 4.1, 3.5))            # washroom wall, north of door
walls.box((4.0, 29.15, 2.975), (0.15, 1.5, 1.05))          # washroom door lintel
walls.box((6.9625, 26.0, 1.75), (6.075, 0.15, 3.5))        # washroom south partition
walls.finish()

# ceiling slab and concrete beams under it
ceil = Bag("B_ceiling", M["ceiling"], uv=3.0)
ceil.box((0, 25.15, 3.65), (20.6, 18.3, 0.3))
for by in (18.0, 22.0, 30.0):
    ceil.box((0, by, 3.3), (20.0, 0.3, 0.4))
ceil.finish()

# steel: far door frame, hanging-open leaf, stall panels, notice board frame, grate, faucets
steel = Bag("B_steel", M["steel"], uv=1.0)
steel.box((-1.25, 33.95, 1.5), (0.1, 0.1, 3.0))            # jamb left (inside zone face)
steel.box((1.25, 33.95, 1.5), (0.1, 0.1, 3.0))             # jamb right
steel.box((0.0, 33.95, 3.0), (2.6, 0.1, 0.12))             # head casing
steel.box((-1.675, 33.975, 1.1), (0.95, 0.05, 2.2))        # fire door leaf, hung open flat on the wall
steel.box((6.2, 32.0, 1.15), (0.05, 4.0, 1.7))             # washroom stall panel
steel.box((8.6, 32.0, 1.15), (0.05, 4.0, 1.7))             # washroom stall panel
steel.box((-5.5, 33.975, 2.72), (2.72, 0.05, 0.06))       # notice board frame top
steel.box((-5.5, 33.975, 1.38), (2.72, 0.05, 0.06))       # notice board frame bottom
steel.box((-6.84, 33.975, 2.05), (0.06, 0.05, 1.4))        # frame left
steel.box((-4.16, 33.975, 2.05), (0.06, 0.05, 1.4))        # frame right
steel.box((7.6, 27.4, 0.004), (0.3, 0.3, 0.008))           # floor drain grate
steel.cyl((9.2, 27.2, 1.0), 0.02, 0.25)                    # faucets
steel.cyl((9.2, 28.4, 1.0), 0.02, 0.25)
steel.finish()
add_collider(-1.675, 33.975, 1.1, 0.95, 0.05, 2.2, 0)      # leaf stands proud of the wall
add_collider(6.2, 32.0, 1.15, 0.05, 4.0, 1.7, 0)
add_collider(8.6, 32.0, 1.15, 0.05, 4.0, 1.7, 0)

# rust: ducts, pipes, cable tray
rust = Bag("B_rust", M["rust"], uv=0.8)
rust.box((-7.6, 25.0, 3.1), (0.7, 17.6, 0.5))
rust.box((7.6, 21.35, 3.1), (0.7, 10.3, 0.5))
rust.cyl((-9.85, 25.0, 2.7), 0.05, 17.0, axis="y")
rust.cyl((-3.0, 33.3, 3.25), 0.06, 14.0, axis="x")
rust.box((1.5, 25.0, 3.2), (0.35, 17.0, 0.06))
rust.finish()

# ceramic: sink counter, toilet tanks
Bag("B_ceramic", M["ceramic"], uv=0.6).box((9.5, 27.8, 0.425), (0.8, 2.4, 0.85))\
    .box((5.1, 33.82, 0.62), (0.42, 0.2, 0.36))\
    .box((7.4, 33.82, 0.62), (0.42, 0.2, 0.36)).finish()
add_collider(9.5, 27.8, 0.425, 0.8, 2.4, 0.85, 0)

# mirror above the sinks
Bag("B_mirror", M["mirror"], bevel=0).box((9.94, 27.8, 1.5), (0.04, 2.2, 0.9)).finish()

# hazard walkway lines (painted, flush with the floor)
Bag("B_hazard", M["hazard"], uv=3.0, bevel=0)\
    .box((-2.9, 24.9, 0.002), (0.1, 17.2, 0.004))\
    .box((2.9, 24.9, 0.002), (0.1, 17.2, 0.004)).finish()

# wet floor: puddles
wet = Bag("B_puddles", M["puddle"], uv=1.0, bevel=0)
wet.cyl((-7.9, 23.0, 0.002), 0.6, 0.004, seg=14)
wet.cyl((2.0, 30.0, 0.002), 0.45, 0.004, seg=14)
wet.cyl((8.0, 29.0, 0.002), 0.5, 0.004, seg=14)
wet.finish()

# paper litter on the floor, and sheets pinned to the notice board
paper = Bag("B_paper", M["paper"], uv=1.0, bevel=0)
for _ in range(14):
    px = rng.uniform(-2.3, 2.3) if rng.random() < 0.5 else rng.uniform(-9.0, 9.0)
    py = rng.uniform(16.8, 33.4)
    paper.box((px, py, 0.002), (0.21, 0.297, 0.002), rot=rng.uniform(0, math.tau))
for _ in range(9):
    px = rng.uniform(-6.5, -4.5)
    pz = rng.uniform(1.5, 2.55)
    paper.box((px, 33.945, pz), (0.21, 0.004, 0.297), rot=rng.uniform(-0.12, 0.12))
paper.finish()

# sign boards: exit over the far door, WC sign on the washroom partition
Bag("B_sign", M["sign"], bevel=0)\
    .box((0.0, 33.975, 3.22), (1.1, 0.03, 0.26))\
    .box((4.09, 27.9, 2.2), (0.02, 0.3, 0.2)).finish()

# notice board face (hessian, flush inside the far wall)
Bag("B_notice_board", M["board"], uv=0.6, bevel=0)\
    .box((-5.5, 33.975, 2.05), (2.6, 0.04, 1.3)).finish()

# ceiling light fixtures: working (emissive tubes plus light sources) and dead
FIXTURES = [
    # x, y, working, colour, flicker, intensity
    (-6.0, 20.0, True, "#d6eeff", True, 1.0),
    (0.0, 20.0, True, "#d6eeff", False, 1.0),
    (6.0, 20.0, False, None, False, 0.0),
    (0.0, 27.5, True, "#d6eeff", False, 0.8),
    (-6.0, 27.5, False, None, False, 0.0),
    (-6.0, 32.0, True, "#d6eeff", True, 0.9),
    (7.0, 31.0, True, "#ffb27a", True, 0.7),
    (2.0, 33.0, False, None, False, 0.0),
]
fx_house = Bag("B_fixture_housings", M["housing"], uv=1.0, bevel=0.005)
tube_on = Bag("B_fixture_tubes_lit", M["tube_on"], uv=1.0, bevel=0)
tube_off = Bag("B_fixture_tubes_dead", M["tube_off"], uv=1.0, bevel=0)
for fx, fy, working, col, flicker, inten in FIXTURES:
    fx_house.box((fx, fy, 3.465), (1.2, 0.3, 0.07))
    if working:
        tube_on.box((fx, fy, 3.42), (1.1, 0.1, 0.03))
        LIGHTS.append({"pos": [fx, fy, 3.3], "color": col, "intensity": inten,
                       "range": 8, "flicker": flicker})
        PREVIEW_LIGHTS.append((fx, fy, 3.3, col, inten))
    else:
        tube_off.box((fx, fy, 3.42), (1.1, 0.1, 0.03))
fx_house.finish()
tube_on.finish()
tube_off.finish()


# lathe pieces: sinks and toilets
basin_profile = [(0.0, 0.0), (0.2, 0.0), (0.22, 0.02), (0.22, 0.035),
                 (0.18, 0.05), (0.12, 0.05), (0.0, 0.05)]
toilet_profile = [(0.0, 0.0), (0.19, 0.0), (0.21, 0.06), (0.22, 0.2),
                  (0.2, 0.36), (0.19, 0.44), (0.0, 0.44)]
lathe_obj(basin_profile, (9.5, 27.2, 0.85), M["ceramic"], "B_basin_1")
lathe_obj(basin_profile, (9.5, 28.4, 0.85), M["ceramic"], "B_basin_2")
lathe_obj(toilet_profile, (5.1, 33.5, 0.0), M["ceramic"], "B_toilet_1")
lathe_obj(toilet_profile, (7.4, 33.5, 0.0), M["ceramic"], "B_toilet_2")
lathe_obj(toilet_profile, (9.3, 31.0, 0.22), M["ceramic"], "B_toilet_tipped",
          rot=(math.pi / 2, 0, 0.4))
add_collider(5.1, 33.5, 0.22, 0.44, 0.44, 0.44, 0)
add_collider(7.4, 33.5, 0.22, 0.44, 0.44, 0.44, 0)
add_collider(9.3, 31.0, 0.22, 0.44, 0.44, 0.44, 0)


# ---------------------------------------------------------------- imported props

LOCKER = template(f"{MODELS}/locker.glb", "locker")[0]
BENCH = template(f"{MODELS}/bench.glb", "bench")[0]
NAMETAG = template(f"{MODELS}/name_tag.glb", "name_tag")[0]
TRASHBAGS = template(f"{MODELS}/trashbags.glb", "trashbags")[0]
TRASH = template(f"{MODELS}/trash.glb", "trash")[0]
CRATE = template(f"{MODELS}/crate.glb", "crate")[0]
FUSEBOX = template(f"{MODELS}/fusebox.glb", "fusebox")[0]
PLUSH = template(f"{MODELS}/plush_pile.glb", "plush")[0]
CASSETTE = template(f"{MODELS}/cassette.glb", "cassette")[0]
KEYCARD = template(f"{MODELS}/keycard.glb", "keycard")[0]
STAFF_DOOR = template(f"{MODELS}/staff_door.glb", "staff_door")

# locker banks: rows run along y, backs against the walls or back to back.
# (centre x, facing: +1 doors face +x, -1 doors face -x, slots to leave empty)
LOCKER_ROWS = [
    ("W1", -9.63, +1, {3, 7}),
    ("W2a", -6.65, -1, {5}),
    ("W2b", -5.95, +1, {2}),
    ("W3", -3.85, +1, {4, 8}),
    ("E1", 9.63, -1, {6}),
    ("E2a", 6.65, +1, {1}),
    ("E2b", 5.95, -1, {3}),
    ("E3", 3.85, -1, {0, 7}),
]
for label, cx, facing, skips in LOCKER_ROWS:
    base = facing * math.pi / 2
    for k in range(9):
        if k in skips:
            continue
        cy = 17.0 + 0.475 + 0.95 * k
        jx = cx + rng.uniform(-0.01, 0.01)
        rot = base + rng.uniform(-0.015, 0.015)
        inst(LOCKER, f"B_locker_{label}_{k}", jx, cy, 0.0, rot, collide=True)

# benches, one with a name tag for the pickup
inst(BENCH, "B_bench_corridor", -2.4, 21.0, 0.0, math.pi / 2, collide=True)
inst(BENCH, "B_bench_board", -5.0, 32.3, 0.0, 0.0, collide=True)
inst(NAMETAG, "B_name_tag", -2.4, 21.0, 0.48, 0.3)

# washroom door: frame in the partition, leaf hanging open into the room
frame_obj = next(o for o in STAFF_DOOR if o.name.startswith("Main"))
leaf_obj = next(o for o in STAFF_DOOR if o.name.startswith("Door"))
frame_obj.name = "B_washroom_frame"
frame_obj.location = (4.0, 29.15, 0.0)
frame_obj.rotation_euler = (0, 0, math.pi / 2)
for v in leaf_obj.data.vertices:  # move the hinge (left edge) to the origin
    v.co.x += 0.61
leaf_obj.name = "B_washroom_leaf"
leaf_obj.location = (4.0, 28.54, 0.0)
leaf_obj.rotation_euler = (0, 0, 0)
PROPS += [frame_obj, leaf_obj]
add_collider(4.61, 28.5, 1.11, 1.22, 0.16, 2.22, 0)

# clutter and storage
inst(TRASHBAGS, "B_trashbags", -8.0, 31.0, 0.0, 0.1, collide=True)
inst(CRATE, "B_crate_low", -8.9, 33.2, 0.0, 0.05, collide=False)
inst(CRATE, "B_crate_top", -8.85, 33.25, 0.96, -0.08, collide=False)
add_collider(-8.9, 33.2, 0.96, 1.02, 1.02, 1.92, 0)
inst(TRASH, "B_trash_bin", 2.7, 32.6, 0.0, 0.4, collide=True)
inst(FUSEBOX, "B_fusebox", 2.6, 33.775, 0.8, 0.0, collide=True)
inst(PLUSH, "B_plush_pile", -3.0, 29.0, 0.0, 0.2)
inst(CASSETTE, "B_cassette", -4.9, 24.9, 0.0, 0.7)
inst(KEYCARD, "B_keycard", -8.2, 27.5, 0.0, 1.1)

# pickup and marker positions
MARKERS.update({
    "entry": [0.0, 17.0, 0.0],
    "exit": [0.0, 33.0, 0.0],
    "door_near": [0.0, 16.0, 0.0],
    "door_far": [0.0, 34.0, 0.0],
    "pickup_name_tag": [-2.4, 21.0, 0.48],
    "hide_w_aisle": [-8.14, 21.0, 0.0],
    "hide_e_aisle": [8.14, 21.0, 0.0],
    "hide_w_narrow": [-4.9, 21.0, 0.0],
    "hide_e_narrow": [4.9, 21.0, 0.0],
    "hide_washroom_stall": [7.4, 31.5, 0.0],
    "notice_board": [-5.5, 33.9, 1.6],
    "washroom_sinks": [9.5, 27.8, 0.85],
})

# remove the import templates: their mesh data stays with the linked copies
for key, objs in TEMPLATES.items():
    if key == "staff_door":  # frame and leaf are used directly
        continue
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


# ---------------------------------------------------------------- preview lights

def build_preview_lights():
    world = bpy.data.worlds.new("ZB_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.013, 0.015, 1)
    for i, (x, y, z, col, inten) in enumerate(PREVIEW_LIGHTS):
        ld = bpy.data.lights.new(f"ZB_light_{i}", "POINT")
        ld.energy = 55.0 * inten if col == "#d6eeff" else 40.0
        ld.shadow_soft_size = 0.15
        ld.color = tuple(int(col[j:j + 2], 16) / 255 for j in (1, 3, 5))
        lo = bpy.data.objects.new(f"ZB_light_{i}", ld)
        lo.location = (x, y, z)
        bpy.context.scene.collection.objects.link(lo)


def make_cam(loc, tgt, lens=32):
    cd = bpy.data.cameras.new("ZB_cam")
    cd.lens = lens
    cd.clip_end = 80
    co = bpy.data.objects.new("ZB_cam", cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = loc
    d = Vector(tgt) - Vector(loc)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return co


def render_previews():
    os.makedirs(SCRATCH, exist_ok=True)
    os.makedirs(os.path.dirname(EYE_PNG), exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = PREVIEW_SAMPLES
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    size = 640
    scene.render.resolution_x = scene.render.resolution_y = size

    eye_views = [
        ((0.0, 17.2, 1.6), (0.0, 34.0, 1.3)),     # far doorway
        ((0.0, 32.6, 1.6), (0.0, 16.0, 1.3)),     # near doorway
        ((2.6, 29.2, 1.6), (9.0, 29.6, 1.1)),     # washroom through the door
        ((-8.14, 18.0, 1.6), (-8.14, 27.0, 1.2)),  # locker aisle
    ]
    tiles = []
    for i, (loc, tgt) in enumerate(eye_views):
        cam = make_cam(loc, tgt)
        scene.camera = cam
        path = os.path.join(SCRATCH, f"eye_{i}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path)
        tiles.append(np.array(im.pixels[:]).reshape(size, size, 4))
        bpy.data.images.remove(im)
        bpy.data.objects.remove(cam)
        os.remove(path)
    sheet = np.vstack([np.hstack(tiles[2:4]), np.hstack(tiles[0:2])])
    out = bpy.data.images.new("eye_sheet", size * 2, size * 2)
    out.pixels = sheet.ravel()
    out.filepath_raw = EYE_PNG
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)

    # top view, ceiling and overhead clutter hidden
    hide = [o for o in bpy.data.objects if o.name.startswith(("B_ceiling", "B_rust",
            "B_fixture", "B_tube"))]
    for o in hide:
        o.hide_render = True
    cd = bpy.data.cameras.new("ZB_top")
    cd.type = "ORTHO"
    cd.ortho_scale = 21.0
    cd.clip_end = 80
    cam = bpy.data.objects.new("ZB_top", cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0.0, 25.15, 40.0)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.filepath = TOP_PNG
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    for o in hide:
        o.hide_render = False


# ---------------------------------------------------------------- report and export

def write_outputs():
    shell_tris = sum(bkit.tri_count(o) for o in SHELL)
    prop_meshes = {}
    for o in PROPS:
        if o.data and o.data.name not in prop_meshes:
            prop_meshes[o.data.name] = bkit.tri_count(o)
    prop_tris = sum(prop_meshes.values())
    print("ZB_TRIS shell", shell_tris, "unique_prop_meshes", len(prop_meshes), "prop_tris_unique", prop_tris)

    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    data = {
        "zone": "B",
        "colliders": COLLIDERS,
        "lights": LIGHTS,
        "markers": MARKERS,
    }
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=1)

    export_objs = [o for o in bpy.data.objects if o.name.startswith("B_")]
    bkit.export_glb(GLB_PATH, export_objs, image_format="JPEG")
    print("ZB_GLB", GLB_PATH, os.path.getsize(GLB_PATH), "bytes", "objects", len(export_objs))

    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(os.path.dirname(BLEND_PATH), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


# ---------------------------------------------------------------- main

build_preview_lights()
render_previews()
write_outputs()
print("ZB_DONE")
