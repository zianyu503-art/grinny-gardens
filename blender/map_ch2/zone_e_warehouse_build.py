"""Chapter 2, zone E: ride-parts warehouse with steel pallet racking.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/map_ch2/zone_e_warehouse_build.py

Coordinates follow blender/map_ch2/BRIEF.md: floor at z=0, route along +Y,
interior box x -14..14, y 114..144, ceiling 8.0. Far wall (y=144) belongs to
this zone and carries the 2.4 m x 3.0 m doorway. The near boundary (y=114) is
zone D's far wall, so this script builds no wall there.
"""
import sys, os, json, math, random, tempfile

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_e_warehouse"
MODELS = f"{ROOT}/public/models"
OUT_GLB = f"{ROOT}/public/models/ch2/{NAME}.glb"
OUT_JSON = f"{ROOT}/public/models/ch2/{NAME}.json"
OUT_BLEND = f"{ROOT}/blender/bake/map_ch2/{NAME}.blend"
OUT_EYE = f"{ROOT}/renders/ch2_{NAME}_eye.png"
OUT_TOP = f"{ROOT}/renders/ch2_{NAME}_top.png"
SCRATCH = "/private/tmp/claude-504/-Users-alex-----2/df819384-06df-4249-8523-a5c0f94e5679/scratchpad/ze"
PREVIEW_ONLY = "--no-preview" not in sys.argv

# ------------------------------------------------------------------ constants
X0, X1, Y0, Y1, H = -14.0, 14.0, 114.0, 144.0, 8.0
DOOR_HALF, DOOR_H = 1.2, 3.0
FRAME_Y = 144.0
ROWS = [-12.0, -6.5, 5.4, 10.9]          # front (aisle-side) x of each rack row
SEGS = [(116.0, 126.0), (130.0, 140.0)]  # rack segments, cross aisle 126..130
BAY = 2.5
BZ = [0.45, 2.05, 3.65, 5.25]            # beam centre heights, 4 levels
UP_H = 6.3
DECK_TOP = [z + 0.09 for z in BZ]

LIGHTS = [  # (pos, colour, intensity, range, flicker)  pos = just under fixture
    ((-4.0, 118.0, 6.6), "#cfe6ff", 1.0, 9.0, False),
    ((4.0, 124.0, 6.6), "#cfe6ff", 0.8, 9.0, True),
    ((-4.0, 130.0, 6.6), "#cfe6ff", 1.0, 9.0, False),
    ((4.0, 136.0, 6.6), "#cfe6ff", 0.7, 9.0, True),
    ((-4.0, 142.0, 6.6), "#cfe6ff", 0.9, 9.0, False),
    ((0.0, 141.2, 2.7), "#ffb070", 0.8, 7.0, False),   # warm bulb over the far doorway
    ((-8.7, 137.0, 2.5), "#ffb070", 0.6, 6.0, True),   # warm bulb in the west aisle
]

rng = random.Random(7)
bpy.context.preferences.filepaths.save_version = 0
bkit.reset_scene()
os.makedirs(SCRATCH, exist_ok=True)


# ------------------------------------------------------------------ helpers
class Group:
    """Collects boxes (and short cylinders) to become one mesh."""

    def __init__(self):
        self.items = []

    def box(self, c, s, rot=(0.0, 0.0, 0.0), mat=0):
        R = Euler(rot).to_matrix().to_4x4()
        M = Matrix.Translation(c) @ R @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        self.items.append(("box", mat, M, None))

    def cyl(self, c, r, d, rot=(0.0, 0.0, 0.0), mat=0, segs=14):
        R = Euler(rot).to_matrix().to_4x4()
        M = Matrix.Translation(c) @ R
        self.items.append(("cyl", mat, M, (r, d, segs)))

    def build(self, name, mats, uv=None):
        bm = bmesh.new()
        for kind, mat, M, extra in self.items:
            before = set(bm.faces)
            if kind == "box":
                bmesh.ops.create_cube(bm, size=1.0, matrix=M)
            else:
                r, d, segs = extra
                bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                                      segments=segs, radius1=r, radius2=r,
                                      depth=d, matrix=M)
            for f in set(bm.faces) - before:
                f.material_index = mat
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        if uv:
            bkit.box_uv(obj, size=uv)
        return obj


def pbr(name, tid, tint=None):
    return bkit.pbr_material(name, bkit.polyhaven_texture(tid, res="1k"), tint=tint)


def proc(name, base, **kw):
    return bkit.procedural_material(name, base, **kw)


def rot_xy(cx, cy, rz, lx, ly):
    c, s = math.cos(rz), math.sin(rz)
    return (cx + c * lx - s * ly, cy + s * lx + c * ly)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


# ------------------------------------------------------------------ materials
M_FLOOR = pbr("E_concrete_floor", "concrete_floor_worn_001")
M_WALL = pbr("E_painted_wall", "peeling_painted_wall")
M_CEIL = pbr("E_dirty_concrete", "dirty_concrete")
M_STEEL = pbr("E_rack_steel", "rusty_painted_metal")
M_BEAM = M_STEEL  # one shared steel set for racks, beams, frame and pipes
M_GRATE = pbr("E_rack_grate", "metal_grate_rusty")
M_WOOD = pbr("E_pallet_wood", "wooden_rough_planks")
M_TARP = pbr("E_tarp", "rough_linen", tint=(0.30, 0.29, 0.22))

# small detailed dressing, all procedural, baked together later
DRESS_MATS = [
    proc("E_paint_yellow", (0.62, 0.48, 0.08), variation=0.12, roughness=0.55, scale=3.0, bump=0.2, grime=0.35),
    proc("E_black_rubber", (0.025, 0.025, 0.025), variation=0.2, roughness=0.8, scale=4.0, bump=0.2, grime=0.3),
    proc("E_ceiling_tile", (0.55, 0.53, 0.46), variation=0.1, roughness=0.9, scale=5.0, bump=0.1, grime=0.5),
    proc("E_cardboard", (0.36, 0.25, 0.14), variation=0.15, roughness=0.85, scale=6.0, bump=0.25, grime=0.4),
    proc("E_paper", (0.58, 0.55, 0.48), variation=0.1, roughness=0.9, scale=8.0, bump=0.05, grime=0.5),
    proc("E_puddle", (0.05, 0.06, 0.07), variation=0.1, roughness=0.04, scale=2.0, bump=0.0, grime=0.0),
    proc("E_sign_red", (0.45, 0.07, 0.05), variation=0.15, roughness=0.6, scale=4.0, bump=0.1, grime=0.4),
    proc("E_oil", (0.035, 0.028, 0.02), variation=0.2, roughness=0.35, scale=3.0, bump=0.0, grime=0.0),
]
P, K, T, C, PA, PU, SR, OIL = range(8)

# ------------------------------------------------------------------ shell
shell = Group()
# floor slab (top at z=0) and ceiling slab (underside at 8.0)
floor = Group(); floor.box((0.0, 129.15, -0.15), (28.6, 30.3, 0.3))
ceil_g = Group(); ceil_g.box((0.0, 129.15, 8.15), (28.6, 30.3, 0.3))
walls = Group()
walls.box((-14.15, 129.0, 4.0), (0.3, 30.0, 8.0))                       # west
walls.box((14.15, 129.0, 4.0), (0.3, 30.0, 8.0))                        # east
walls.box((-7.75, 144.15, 4.0), (13.1, 0.3, 8.0))                       # far, left of door
walls.box((7.75, 144.15, 4.0), (13.1, 0.3, 8.0))                        # far, right of door
walls.box((0.0, 144.15, 5.5), (2.4, 0.3, 5.0))                          # lintel over door
W_OBJ = walls.build("E_walls", [M_WALL], uv=2.5)
F_OBJ = floor.build("E_floor", [M_FLOOR], uv=2.5)
C_OBJ = ceil_g.build("E_ceiling", [M_CEIL], uv=2.5)

# steel door frame (no leaf: the door is missing), leftover hinge knuckles
frame = Group()
frame.box((-1.14, FRAME_Y, 1.5), (0.12, 0.24, DOOR_H))
frame.box((1.14, FRAME_Y, 1.5), (0.12, 0.24, DOOR_H))
frame.box((0.0, FRAME_Y, 2.94), (2.4, 0.24, 0.12))
frame.box((-1.22, 143.88, 0.6), (0.06, 0.1, 0.22))
frame.box((-1.22, 143.88, 2.4), (0.06, 0.1, 0.22))
FRAME_OBJ = frame.build("E_door_frame", [M_BEAM], uv=1.0)

# ceiling: longitudinal and cross I-beams hung on rods, fixtures, ducts
over = Group()


def ibeam_x(g, x_c, y_c, length, axis, zb=7.1):
    """I-beam along axis ('y' or 'x') with bottom flange at zb."""
    if axis == "y":
        g.box((x_c, y_c, zb + 0.015), (0.2, length, 0.03), mat=0)
        g.box((x_c, y_c, zb + 0.2), (0.02, length, 0.37), mat=0)
        g.box((x_c, y_c, zb + 0.385), (0.2, length, 0.03), mat=0)
    else:
        g.box((x_c, y_c, zb + 0.015), (length, 0.2, 0.03), mat=0)
        g.box((x_c, y_c, zb + 0.2), (length, 0.02, 0.37), mat=0)
        g.box((x_c, y_c, zb + 0.385), (length, 0.2, 0.03), mat=0)


for xl in (-8.0, 0.0, 8.0):
    ibeam_x(over, xl, 129.0, 30.0, "y")
for yc in (118.0, 124.0, 130.0, 136.0, 142.0):
    ibeam_x(over, 0.0, yc, 28.6, "x")
    for xl in (-8.0, 0.0, 8.0):
        over.box((xl, yc, 7.75), (0.05, 0.05, 0.5), mat=0)
# fixtures hang from the cross beams, ten positions, all but five are dead
for yc in (118.0, 124.0, 130.0, 136.0, 142.0):
    for xf in (-4.0, 4.0):
        over.box((xf, yc, 6.92), (0.36, 1.2, 0.12), mat=0)
        over.box((xf, yc, 7.04), (0.04, 0.04, 0.12), mat=0)
# two large ducts along the side walls, pipes low on the walls
over.box((-12.6, 129.0, 7.45), (0.9, 30.0, 0.6))
over.box((12.6, 129.0, 7.45), (0.9, 30.0, 0.6))
OVER_OBJ = over.build("E_overhead", [M_BEAM], uv=1.0)

pipes = Group()
pipes.box((-13.75, 129.0, 3.2), (0.12, 30.0, 0.12))
pipes.box((-13.75, 129.0, 3.4), (0.12, 30.0, 0.12))
pipes.box((13.75, 129.0, 2.7), (0.12, 30.0, 0.12))
for yb in (118.0, 129.0, 140.0):  # pipe brackets
    pipes.box((-13.85, yb, 3.0), (0.06, 0.06, 0.6))
PIPE_OBJ = pipes.build("E_pipes", [M_BEAM], uv=1.0)


# ------------------------------------------------------------------ racking
rack_steel = Group()
rack_deck = Group()
RACK_COLLIDERS = []
# a few damaged bays (row x0, segment start, bay index, level)
DAMAGED_DECK = {(-6.5, 116.0, 1, 1), (5.4, 130.0, 2, 2), (10.9, 116.0, 3, 0)}
SAGGED_DECK = {(-12.0, 130.0, 0, 3), (5.4, 116.0, 0, 3), (-6.5, 116.0, 3, 2)}
goods_crate_spots = []   # (x, y, z_deck_top) for crates
goods_card_spots = []    # cardboard stacks, dressing group

for x0 in ROWS:
    x1 = x0 + 1.1
    xm = x0 + 0.55
    for (ys, ye) in SEGS:
        nodes = [ys + i * BAY for i in range(5)]
        n_bays = 4
        for x in (x0, x1):
            for y in nodes:
                rack_steel.box((x, y, UP_H / 2), (0.08, 0.08, UP_H))
            for zb in BZ:
                for i in range(n_bays):
                    rack_steel.box((x, nodes[i] + BAY / 2, zb), (0.07, BAY - 0.1, 0.1))
        for k, zb in enumerate(BZ):
            for y in nodes:
                rack_steel.box((xm, y, zb), (1.1, 0.06, 0.1))
            for i in range(n_bays):
                key = (x0, ys, i, k)
                if key in DAMAGED_DECK:
                    continue  # deck gone: the bay is empty at this level
                if key in SAGGED_DECK:
                    rack_deck.box((xm, nodes[i] + BAY / 2, zb + 0.07), (1.06, BAY - 0.12, 0.04),
                                  rot=(0.12, 0.0, 0.0))
                    continue
                rack_deck.box((xm, nodes[i] + BAY / 2, zb + 0.07), (1.06, BAY - 0.12, 0.04))
        for x in (x0, x1):   # diagonal bracing in the frame plane
            for i in range(n_bays):
                for k in range(3):
                    za, zb2 = BZ[k], BZ[k + 1]
                    dz = zb2 - za
                    ang = math.atan2(dz, BAY)
                    L = math.hypot(BAY, dz)
                    sgn = 1 if (i + k) % 2 == 0 else -1
                    rack_steel.box((x, nodes[i] + BAY / 2, (za + zb2) / 2),
                                   (0.05, L - 0.05, 0.05), rot=(sgn * ang, 0.0, 0.0))
        # goods on the decks
        for i in range(n_bays):
            ym = nodes[i] + BAY / 2
            for k in range(4):
                if (x0, ys, i, k) in DAMAGED_DECK or (x0, ys, i, k) in SAGGED_DECK:
                    continue
                if rng.random() < 0.35:
                    continue
                if rng.random() < 0.6:
                    offs = [0.0] if rng.random() < 0.5 else [-0.6, 0.6]
                    for o in offs:
                        goods_crate_spots.append((xm + rng.uniform(-0.02, 0.02),
                                                  ym + o + rng.uniform(-0.03, 0.03),
                                                  DECK_TOP[k], rng.uniform(-0.04, 0.04)))
                else:
                    goods_card_spots.append((xm, ym, DECK_TOP[k], rng.uniform(0.0, 3.14)))
        RACK_COLLIDERS.append([xm, (ys + ye) / 2, UP_H / 2, 1.1, ye - ys, UP_H, 0.0])

RACK_OBJ = rack_steel.build("E_racks_steel", [M_STEEL], uv=1.0)
DECK_OBJ = rack_deck.build("E_racks_decks", [M_GRATE], uv=1.0)

# ------------------------------------------------------------------ dressing (procedural, baked)
dr = Group()

# hazard lines along the aisle sides of each rack row
for x0 in ROWS:
    for xl in (x0 - 0.25, x0 + 1.1 + 0.25):
        for (ys, ye) in SEGS:
            dr.box((xl, (ys + ye) / 2, 0.002), (0.1, ye - ys, 0.004), mat=PA)

# oil stains and dark patches so the floor is not a bare flat surface
for _ in range(16):
    x = rng.uniform(-12.5, 12.5)
    y = rng.uniform(115.0, 143.5)
    if abs(x) < 1.8 and y < 143:
        continue
    dr.cyl((x, y, 0.0), rng.uniform(0.35, 1.0), 0.003, mat=OIL, segs=rng.choice([9, 11, 13]))

# wall signs
dr.box((-13.99, 119.0, 2.3), (0.02, 0.9, 0.6), mat=SR)
dr.box((13.99, 137.0, 2.3), (0.02, 0.9, 0.6), mat=PA)
dr.box((-4.0, 143.99, 2.4), (1.0, 0.02, 0.6), mat=PA)
dr.box((6.0, 143.99, 2.4), (0.8, 0.02, 0.6), mat=SR)

# puddles and drains
for (x, y, r) in [(-9.6, 121.8, 0.6), (-7.2, 137.0, 0.8), (6.2, 118.5, 0.7),
                  (9.4, 130.0, 0.9), (0.5, 142.4, 0.6), (1.6, 137.5, 0.5)]:
    dr.cyl((x, y, 0.0), r * rng.uniform(0.9, 1.05), 0.004, mat=PU, segs=16)
for (x, y) in [(-8.7, 128.0), (6.5, 121.0), (-11.2, 143.0)]:
    dr.box((x, y, 0.001), (0.5, 0.5, 0.004), mat=K if False else 1)

# fallen ceiling tiles
for _ in range(6):
    x = rng.uniform(-13.0, 13.0)
    y = rng.uniform(116.5, 142.5)
    if abs(x) < 2.6:
        x += 3.2 * (1 if x >= 0 else -1)
    dr.box((x, y, 0.05), (0.6, 0.6, 0.02),
           rot=(rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, 3.14)), mat=T)

# paper litter
for _ in range(14):
    x = rng.uniform(-13.0, 13.0)
    y = rng.uniform(116.0, 143.0)
    if abs(x) < 2.0:
        continue
    dr.box((x, y, 0.002), (0.21, 0.297, 0.002), rot=(0, 0, rng.uniform(0, 3.14)), mat=PA_IDX if False else 4)

# loose cardboard stacks against the walls and in the far end
for (x, y, rz) in [(-13.1, 135.6, 0.1), (10.1, 139.5, -0.2), (-10.0, 141.2, 0.3)]:
    dr.box((x, y, 0.2), (0.6, 0.45, 0.4), rot=(0, 0, rz), mat=C)
    dr.box((x + 0.02, y, 0.6), (0.55, 0.42, 0.36), rot=(0, 0, rz + 0.05), mat=C)

# goods on the racks: cardboard stacks
for (x, y, zt, rz) in goods_card_spots:
    if rng.random() < 0.5:
        dr.box((x, y, zt + 0.2), (0.7, 0.5, 0.4), rot=(0, 0, rz), mat=C)
    else:
        dr.box((x, y, zt + 0.2), (0.6, 0.45, 0.4), rot=(0, 0, rz), mat=C)
        dr.box((x, y, zt + 0.6), (0.5, 0.4, 0.35), rot=(0, 0, rz + 0.1), mat=C)

# yellow hazard paint on the forklift's floor line near the centre aisle (decor)
dr.box((-5.15, 136.0, 0.002), (0.12, 3.0, 0.004), mat=PA)


def pallet(g, cx, cy, rz):
    for lx in (-0.42, 0.0, 0.42):
        x, y = rot_xy(cx, cy, rz, lx, 0.0)
        g.box((x, y, 0.05), (0.09, 1.0, 0.1), rot=(0, 0, rz), mat=0)
    for ly in (-0.42, -0.21, 0.0, 0.21, 0.42):
        x, y = rot_xy(cx, cy, rz, 0.0, ly)
        g.box((x, y, 0.11), (1.2, 0.1, 0.02), rot=(0, 0, rz), mat=0)


# forklift (local frame: forks toward -Y, origin at floor centre)
FORK = (3.3, 119.8, 0.5)


def forklift(g, cx, cy, rz):
    def p(lx, ly, lz):
        x, y = rot_xy(cx, cy, rz, lx, ly)
        return (x, y, lz)
    R = (0, 0, rz)
    g.box(p(0, 0.15, 0.45), (1.0, 1.4, 0.3), rot=R, mat=PA)
    g.box(p(0, 0.72, 0.6), (1.0, 0.36, 0.6), rot=R, mat=PA)
    g.box(p(0, 0.35, 0.82), (0.9, 0.6, 0.22), rot=R, mat=PA)
    g.box(p(0, 0.2, 1.0), (0.42, 0.42, 0.12), rot=R, mat=K)
    for lx in (-0.42, 0.42):
        for ly in (0.55, -0.02):
            g.box(p(lx, ly, 1.4), (0.06, 0.06, 1.1), rot=R, mat=K)
    g.box(p(0, 0.27, 2.0), (1.0, 0.9, 0.06), rot=R, mat=PA)
    for lx in (-0.38, 0.38):
        g.box(p(lx, -0.8, 1.25), (0.07, 0.1, 2.5), rot=R, mat=K)
    g.box(p(0, -0.8, 2.45), (0.9, 0.1, 0.08), rot=R, mat=K)
    g.box(p(0, -0.8, 0.8), (0.95, 0.12, 0.6), rot=R, mat=K)
    for lx in (-0.3, 0.3):
        g.box(p(lx, -1.3, 0.15), (0.1, 1.1, 0.05), rot=R, mat=K)
    for lx in (-0.5, 0.5):
        x, y = rot_xy(cx, cy, rz, lx, 0.55)
        g.cyl((x, y, 0.28), 0.28, 0.22, rot=(0, math.pi / 2, rz), mat=K, segs=12)
        x, y = rot_xy(cx, cy, rz, lx * 0.9, -0.5)
        g.cyl((x, y, 0.2), 0.2, 0.18, rot=(0, math.pi / 2, rz), mat=K, segs=12)


forklift(dr, FORK[0], FORK[1], FORK[2])
FORK_COLLIDER = [*rot_xy(FORK[0], FORK[1], FORK[2], 0.0, 0.05), 1.0, 1.05, 1.9, 2.0, FORK[2]]
FORK_COLLIDER = [FORK_COLLIDER[0], FORK_COLLIDER[1], 1.0, 1.05, 1.9, 2.0, FORK[2]]

# wooden pallets on the floor with stacks
PALLETS = [
    (-8.7, 118.4, 0.0, "crate"),
    (-8.7, 131.0, 1.5708, "card"),
    (-8.0, 142.0, 0.2, "crate"),
    (8.7, 117.8, 0.1, "crate"),
    (8.7, 124.5, 0.0, "card"),
    (9.0, 141.4, 1.2, "none"),
]
PALLET_COLLIDERS = []
for (px, py, prz, kind) in PALLETS:
    pallet(dr if False else dr, px, py, prz)
    if kind == "crate":
        goods_crate_spots.append((px, py, 0.12, prz))
    elif kind == "card":
        for (lx, ly, lz) in [(-0.3, 0, 0.12), (0.3, 0, 0.12), (-0.3, 0, 0.54), (0.3, 0, 0.54)]:
            x, y = rot_xy(px, py, prz, lx, ly)
            dr.box((x, y, lz + 0.2), (0.55, 0.5, 0.4), rot=(0, 0, prz), mat=C)
        PALLET_COLLIDERS.append([px, py, 0.6, 1.2, 1.0, 1.2, prz])
    else:
        PALLET_COLLIDERS.append([px, py, 0.06, 1.2, 1.0, 0.12, prz])

DRESS_OBJ = dr.build("E_dressing", DRESS_MATS)

# ------------------------------------------------------------------ prop templates
TPL = {}


def load_template(key, fname):
    before = set(bpy.data.objects)
    meshes = bkit.import_glb(f"{MODELS}/{fname}")
    new = [o for o in bpy.data.objects if o not in before]
    m = meshes[0]
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = mw
    bkit.apply_all(m)
    for o in new:
        if o is not m and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    m.name = f"TPL_{key}"
    TPL[key] = {"obj": m, "corners": [Vector(c) for c in m.bound_box]}
    return m


load_template("cabin", "ferris_cabin.glb")
load_template("car", "coaster_car.glb")
load_template("crate", "crate.glb")
load_template("plush", "plush_pile.glb")


def place(key, x, y, rz, tip=0.0, zbase=0.0, name=None):
    """Place a linked copy: origin at (x, y), yawed by rz after tipping by tip (about X).
    The lowest point of the tipped prop lands on zbase. Returns the object and its
    oriented collider box [cx, cy, cz, sx, sy, sz, rz]."""
    t = TPL[key]
    R = Euler((tip, 0.0, 0.0)).to_matrix()
    pts = [R @ p for p in t["corners"]]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = obj_copy = t["obj"].copy()
    bpy.context.scene.collection.objects.link(obj_copy)
    obj_copy.name = name or f"E_{key}"
    obj_copy.rotation_mode = "XYZ"  # glTF imports use quaternions, which ignore rotation_euler
    obj_copy.rotation_euler = (tip, 0.0, rz)
    obj_copy.location = (x, y, zbase - lo.z)
    cen = (lo + hi) / 2
    size = hi - lo
    cs, sn = math.cos(rz), math.sin(rz)
    wx = x + cs * cen.x - sn * cen.y
    wy = y + sn * cen.x + cs * cen.y
    wz = zbase - lo.z + cen.z
    return obj_copy, [wx, wy, wz, size.x, size.y, size.z, rz]


# ------------------------------------------------------------------ placed props
COLLIDERS = []
COLLIDERS += RACK_COLLIDERS
COLLIDERS += PALLET_COLLIDERS
COLLIDERS.append(FORK_COLLIDER)
COLLIDERS.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # placeholder removed below
COLLIDERS.pop()

# standing cabins (ferris gondolas parked on the floor)
_, cab_a = place("cabin", -3.4, 118.5, 0.35, zbase=0.0, name="E_cabin_a")
_, cab_b = place("cabin", 3.6, 126.0, -0.5, zbase=0.0, name="E_cabin_b")
# one cabin tipped over on its side near the far end
_, cab_c = place("cabin", -3.2, 138.5, 0.3, tip=math.pi / 2, zbase=0.0, name="E_cabin_c_tipped")
COLLIDERS += [cab_a, cab_b, cab_c]

# coaster cars under tarps
car_a_obj, car_a = place("car", -3.9, 124.8, 0.08, zbase=0.0, name="E_car_a")
car_b_obj, car_b = place("car", 3.9, 133.5, -0.12, zbase=0.0, name="E_car_b")
COLLIDERS += [car_a, car_b]

# plush piles: broken toys on the floor
_, pl_a = place("plush", -9.1, 121.2, 0.4, zbase=0.0, name="E_plush_a")
_, pl_b = place("plush", 7.9, 117.4, -1.0, zbase=0.0, name="E_plush_b")

# goods on the racks and on pallets: crates
for idx, (x, y, zt, rz) in enumerate(goods_crate_spots):
    place("crate", x, y, rz, zbase=zt, name=f"E_crate_{idx:03d}")

# a few loose crates on the floor in the central aisle edges
for idx, (x, y, rz) in enumerate([(-6.5, 115.6, 0.0), (5.6, 143.0, 0.2)]):
    place("crate", x, y, rz, zbase=0.0, name=f"E_floor_crate_{idx}")
    COLLIDERS.append([x, y, 0.48, 1.02, 1.02, 0.96, rz])

# tarps draped over the two coaster cars
def tarp(name, box, seed):
    """Tarp over a box = [cx, cy, cz, sx, sy, sz, rz] (the car's oriented box)."""
    cx, cy, cz, sx, sy, sz, rz = box
    r = random.Random(seed)
    W, L = sx + 2.2, sy + 2.2
    peak = cz + sz / 2 + 0.06
    nx, ny = 26, 30
    bm = bmesh.new()
    verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = (i / nx - 0.5) * W
            v = (j / ny - 0.5) * L
            dx = max(0.0, abs(u) - sx / 2)
            dy = max(0.0, abs(v) - sy / 2)
            d = math.hypot(dx, dy)
            if d <= 0.0:
                z = peak + r.uniform(-0.04, 0.04)
            else:
                k = max(0.0, 1.0 - d / 1.0)
                z = 0.03 + (peak - 0.03) * (k ** 1.3) + r.uniform(-0.05, 0.05)
            row.append(bm.verts.new((u, v, max(0.02, z))))
        verts.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M_TARP)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (cx, cy, 0.0)
    obj.rotation_euler = (0.0, 0.0, rz)
    bkit.box_uv(obj, size=1.0)
    return obj


TARPS = [tarp("E_tarp_a", car_a, 11), tarp("E_tarp_b", car_b, 12)]

# ------------------------------------------------------------------ lights (for previews and the JSON)
JSON_LIGHTS = []
for pos, color, inten, rng_, flick in LIGHTS:
    JSON_LIGHTS.append({"pos": list(pos), "color": color, "intensity": inten,
                        "range": rng_, "flicker": flick})

# ------------------------------------------------------------------ dressing bake (one 1024 set)
DRESS_OBJ.name = "E_dressing"
bkit.bake_to_textures(DRESS_OBJ, SCRATCH, size=512, samples=16)
for im in bpy.data.images:
    if im.name.startswith("E_dressing") and im.filepath:
        try:
            im.pack()
        except Exception:
            pass

# ------------------------------------------------------------------ colliders (shell + racks + props)
WALL_COLLIDERS = [
    [-14.15, 129.0, 4.0, 0.3, 30.0, 8.0, 0.0],
    [14.15, 129.0, 4.0, 0.3, 30.0, 8.0, 0.0],
    [-7.75, 144.15, 4.0, 13.1, 0.3, 8.0, 0.0],
    [7.75, 144.15, 4.0, 13.1, 0.3, 8.0, 0.0],
    [-1.14, 144.0, 1.5, 0.12, 0.24, 3.0, 0.0],
    [1.14, 144.0, 1.5, 0.12, 0.24, 3.0, 0.0],
]
ALL_COLLIDERS = WALL_COLLIDERS + COLLIDERS

# ------------------------------------------------------------------ markers
MARKERS = {
    "entry": [0.0, 115.8, 0.0],
    "exit": [0.0, 143.0, 0.0],
    "hide_tarp_a": [-3.9, 122.9, 0.0],
    "hide_tarp_b": [3.9, 131.6, 0.0],
    "hide_cabin_c": [-3.2, 136.8, 0.0],
    "hide_west_aisle": [-8.7, 124.6, 0.0],
    "spawn_1": [-8.7, 136.0, 0.0],
    "spawn_2": [8.7, 118.0, 0.0],
    "spawn_3": [7.5, 141.0, 0.0],
    "patrol_1": [-8.7, 118.5, 0.0],
    "patrol_2": [-8.7, 134.0, 0.0],
    "patrol_3": [8.7, 134.0, 0.0],
    "patrol_4": [8.7, 118.0, 0.0],
}

# ------------------------------------------------------------------ export
# web size budget: every embedded texture at 512 px (exported as JPEG below)
for im in bpy.data.images:
    if im.name in ("Render Result", "Viewer Node"):
        continue
    if im.size[0] > 512 or im.size[1] > 512:
        im.scale(512, 512)
zone_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in zone_meshes:
    if o.name.startswith("TPL_"):
        bpy.data.objects.remove(o, do_unlink=True)
zone_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
shell_tris = sum(bkit.tri_count(o) for o in zone_meshes if not o.name.startswith(("E_crate", "E_floor_crate", "E_plush", "E_cabin", "E_car_")))
prop_tris = sum(bkit.tri_count(o) for o in zone_meshes if o.name.startswith(("E_crate", "E_floor_crate", "E_plush", "E_cabin", "E_car_")))
print(f"ZE_TRIS shell+dressing={shell_tris} props_instanced_per_copy_sum={prop_tris}")

os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
bkit.export_glb(OUT_GLB, objs=zone_meshes, image_format="JPEG")
print("ZE_GLB", OUT_GLB, os.path.getsize(OUT_GLB))

data = {
    "zone": "E",
    "colliders": [[round(v, 4) for v in c] for c in ALL_COLLIDERS],
    "lights": JSON_LIGHTS,
    "markers": MARKERS,
}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
print("ZE_JSON", OUT_JSON, len(ALL_COLLIDERS), "colliders")

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

# ------------------------------------------------------------------ preview lights
world = bpy.data.worlds.new("E_preview_world")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.036, 0.04, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

for i, (pos, color, inten, rng_, flick) in enumerate(LIGHTS):
    if pos[2] > 6.0:
        ld = bpy.data.lights.new(f"E_prev_area_{i}", type="AREA")
        ld.size = 1.2
        ld.size_y = 0.2
        ld.energy = 320.0 * inten
    else:
        ld = bpy.data.lights.new(f"E_prev_point_{i}", type="POINT")
        ld.energy = 150.0 * inten
        ld.shadow_soft_size = 0.2
    ld.color = hex_rgb(color)
    lo = bpy.data.objects.new(ld.name, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = pos

# ------------------------------------------------------------------ previews
def eye_camera(name, pos, target):
    cd = bpy.data.cameras.new(name)
    cd.lens = 26
    cd.sensor_width = 36
    cd.clip_end = 200
    co = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = pos
    d = Vector(target) - Vector(pos)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return co


def still(path, cam, w, h, samples):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_eye_sheet(path, views, size=640, samples=24):
    sc = bpy.context.scene
    tiles = []
    for i, (label, pos, target) in enumerate(views):
        cam = eye_camera(f"E_eye_{i}", pos, target)
        tmp = os.path.join(SCRATCH, f"eye_{i}.png")
        still(tmp, cam, size, size, samples)
        im = bpy.data.images.load(tmp, check_existing=False)
        tiles.append(np.array(im.pixels[:]).reshape(size, size, 4))
        bpy.data.images.remove(im)
        os.remove(tmp)
        bpy.data.objects.remove(cam)
    while len(tiles) < 4:
        tiles.append(np.ones((size, size, 4)))
    # pixels are bottom-up: first memory rows are the bottom of the image
    sheet = np.vstack([np.hstack(tiles[2:4]), np.hstack(tiles[0:2])])
    out = bpy.data.images.new("ze_sheet", size * 2, size * 2, alpha=False)
    out.pixels = sheet.ravel()
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def render_top(path, size=900, samples=16):
    for o in bpy.context.scene.objects:
        if o.name in ("E_overhead", "E_ceiling"):
            o.hide_render = True
    cd = bpy.data.cameras.new("E_top")
    cd.type = "ORTHO"
    cd.ortho_scale = 33.0
    cd.clip_end = 100
    co = bpy.data.objects.new("E_top", cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = (0.0, 129.15, 40.0)
    co.rotation_euler = (0.0, 0.0, 0.0)
    still(path, co, size, size, samples)
    bpy.data.objects.remove(co)
    for o in bpy.context.scene.objects:
        if o.name in ("E_overhead", "E_ceiling"):
            o.hide_render = False


if PREVIEW_ONLY:
    # stand-in for zone D's far wall with its doorway, for preview only (never exported)
    d_wall = bpy.data.meshes.new("PREVIEW_D_wall")
    dg = Group()
    dg.box((-7.75, 113.85, 4.0), (13.1, 0.3, 8.0))
    dg.box((7.75, 113.85, 4.0), (13.1, 0.3, 8.0))
    dg.box((0.0, 113.85, 5.5), (2.4, 0.3, 5.0))
    prev_wall = dg.build("PREVIEW_D_wall", [M_WALL], uv=2.5)

    views = [
        ("far doorway", (0.0, 116.5, 1.6), (0.0, 144.0, 1.6)),
        ("entry doorway", (0.6, 142.0, 1.6), (0.0, 114.0, 1.6)),
        ("tarps and cabins", (1.0, 121.0, 1.6), (-4.0, 126.0, 1.0)),
        ("forklift and east racks", (8.7, 128.0, 1.6), (2.5, 116.5, 1.2)),
    ]
    render_eye_sheet(OUT_EYE, views)
    print("ZE_EYE", OUT_EYE)
    render_top(OUT_TOP)
    print("ZE_TOP", OUT_TOP)
    bpy.data.objects.remove(prev_wall)
