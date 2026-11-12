"""Chapter 3, zone tower: coaster repair tower hall with a pit crossed only by grappling.

Run from /Users/alex/恐怖遊戲2 with:
    python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py blender/map_ch3/zone_tower_build.py <out_dir>

Coordinates follow blender/map_ch3/BRIEF.md: floor z=0, interior box x 42..112, y -35..35,
ceiling underside z=22. Walls 0.3 m thick, built outward from the interior box.
Doors: west at y=0 (3 m wide, 3 m high) to the hub corridor x 30..41.7 (3.4 m high),
north at x=77 (y=35) to the power plant (the power zone builds that corridor).
"""
import sys, os, json, math, random

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_tower"
MODELS = f"{ROOT}/public/models"
OUT_GLB = f"{ROOT}/public/models/ch3/{NAME}.glb"
OUT_JSON = f"{ROOT}/public/models/ch3/{NAME}.json"
OUT_BLEND = f"{ROOT}/blender/bake/map_ch3/{NAME}.blend"
OUT_EYE = f"{ROOT}/renders/ch3_{NAME}_eye.png"
OUT_TOP = f"{ROOT}/renders/ch3_{NAME}_top.png"
SCRATCH = "/private/tmp/claude-504/-Users-alex-----2/df819384-06df-4249-8523-a5c0f94e5679/scratchpad/tw"
PREVIEW_ONLY = "--no-preview" not in sys.argv

# ------------------------------------------------------------------ constants
X0, X1, Y0, Y1, H = 42.0, 112.0, -35.0, 35.0, 22.0
PIT_X0, PIT_X1 = 88.0, 95.0           # 7 m clear pit cuts the hall in two (west / east)
PIT_BOTTOM = -4.0
NORTH_DOOR_X = 77.0
GANTRY_Y = (-7.0, 7.0)                # gantries, and the rings on them, sit close to the pit_a/pit_b rim

rng = random.Random(31)
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


COLLIDERS = []


def bx(g, x0, x1, y0, y1, z0, z1, mat=0):
    """Axis-aligned box from min/max corners."""
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
          (x1 - x0, y1 - y0, z1 - z0), mat=mat)


def solid(g, x0, x1, y0, y1, z0, z1, mat=0, collide=True):
    """Box plus an axis-aligned collider of the same size."""
    bx(g, x0, x1, y0, y1, z0, z1, mat)
    if collide:
        COLLIDERS.append([round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4), round((z0 + z1) / 2, 4),
                          round(x1 - x0, 4), round(y1 - y0, 4), round(z1 - z0, 4), 0.0])


def rot_xy(cx, cy, rz, lx, ly):
    c, s = math.cos(rz), math.sin(rz)
    return (cx + c * lx - s * ly, cy + s * lx + c * ly)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def pbr(name, tid, tint=None):
    return bkit.pbr_material(name, bkit.polyhaven_texture(tid, res="1k"), tint=tint)


def proc(name, base, **kw):
    return bkit.procedural_material(name, base, **kw)


# ------------------------------------------------------------------ materials (shared)
M_FLOOR = pbr("T_concrete_floor", "concrete_floor_worn_001")
M_WALL = pbr("T_painted_wall", "peeling_painted_wall")
M_CEIL = pbr("T_dirty_concrete", "dirty_concrete")
M_STEEL = pbr("T_rusty_steel", "rusty_painted_metal")
M_GRATE = pbr("T_rust_grate", "metal_grate_rusty")
M_WOOD = pbr("T_bench_wood", "wooden_rough_planks")

# small procedural dressing, baked into one set later
DRESS_MATS = [
    proc("T_paint_yellow", (0.62, 0.48, 0.08), variation=0.12, roughness=0.55, scale=3.0, bump=0.2, grime=0.35),
    proc("T_black_rubber", (0.025, 0.025, 0.025), variation=0.2, roughness=0.8, scale=4.0, bump=0.2, grime=0.3),
    proc("T_oil", (0.035, 0.028, 0.02), variation=0.2, roughness=0.35, scale=3.0, bump=0.0, grime=0.0),
    proc("T_puddle", (0.05, 0.06, 0.07), variation=0.1, roughness=0.04, scale=2.0, bump=0.0, grime=0.0),
    proc("T_paper", (0.58, 0.55, 0.48), variation=0.1, roughness=0.9, scale=8.0, bump=0.05, grime=0.5),
    proc("T_cardboard", (0.36, 0.25, 0.14), variation=0.15, roughness=0.85, scale=6.0, bump=0.25, grime=0.4),
    proc("T_sign_red", (0.45, 0.07, 0.05), variation=0.15, roughness=0.6, scale=4.0, bump=0.1, grime=0.4),
    proc("T_drum_blue", (0.08, 0.18, 0.32), variation=0.15, roughness=0.5, scale=3.0, bump=0.2, grime=0.45),
]
YEL, BLK, OIL, PUD, PAP, CRD, RED, BLU = range(8)

# ------------------------------------------------------------------ shell groups
floor = Group()
walls = Group()
ceil_g = Group()
steel = Group()
wood = Group()
dr = Group()

# floor: west slab, east slab, pit bottom (floor top at z=0)
solid(floor, 41.7, PIT_X0, -35.3, 35.3, -0.3, 0.0, collide=False)
solid(floor, PIT_X1, 112.0, -35.3, 35.3, -0.3, 0.0, collide=False)
solid(floor, PIT_X0, PIT_X1, -35.3, 35.3, PIT_BOTTOM - 0.3, PIT_BOTTOM, collide=False)
# hub corridor floor
solid(floor, 30.0, 41.7, -1.5, 1.5, -0.3, 0.0, collide=False)

# walls, 22 m high, with the west doorway (y -1.5..1.5, 3 m high) and north doorway (x 75.5..78.5)
solid(walls, 41.7, 42.0, -35.3, -1.5, 0.0, H)                    # west, south of door
solid(walls, 41.7, 42.0, 1.5, 35.3, 0.0, H)                      # west, north of door
solid(walls, 41.7, 42.0, -1.5, 1.5, 3.0, H)                      # west lintel
solid(walls, 112.0, 112.3, -35.3, 35.3, 0.0, H)                  # east, solid
solid(walls, 42.0, 112.0, -35.3, -35.0, 0.0, H)                  # south, solid
solid(walls, 42.0, NORTH_DOOR_X - 1.5, 35.0, 35.3, 0.0, H)       # north, west of door
solid(walls, NORTH_DOOR_X + 1.5, 112.0, 35.0, 35.3, 0.0, H)      # north, east of door
solid(walls, NORTH_DOOR_X - 1.5, NORTH_DOOR_X + 1.5, 35.0, 35.3, 3.0, H)  # north lintel
# pit edge walls (the pit is 9.7 m wide; the collider blocks the rim)
solid(walls, PIT_X0, PIT_X0 + 0.3, -35.3, 35.3, PIT_BOTTOM, 0.0)
solid(walls, PIT_X1 - 0.3, PIT_X1, -35.3, 35.3, PIT_BOTTOM, 0.0)
# hub corridor, 12 m long, 3 m wide, 3.4 m high, from the hub wall to the tower wall
solid(walls, 30.0, 41.7, -1.8, -1.5, 0.0, 3.4)
solid(walls, 30.0, 41.7, 1.5, 1.8, 0.0, 3.4)
solid(walls, 30.0, 41.7, -1.5, 1.5, 3.4, 3.7, collide=False)  # corridor ceiling

# ceiling slab, underside at z=22
solid(ceil_g, 41.7, 112.3, -35.3, 35.3, H, H + 0.3, collide=False)

# pit: collider blocks the rim so the player can't walk into the hole
COLLIDERS.append([PIT_X0 - 0.05, 0.0, 1.0, 0.7, 70.6, 2.0, 0.0])   # west rim, blocks x 87.65..88.35
COLLIDERS.append([PIT_X1 + 0.05, 0.0, 1.0, 0.7, 70.6, 2.0, 0.0])   # east rim, blocks x 94.65..95.35

# pit rail: posts on the rim, top rail, rusted steel
for rx in (PIT_X0 + 0.05, PIT_X1 - 0.05):
    bx(steel, rx - 0.04, rx + 0.04, -34.0, 34.0, 0.95, 1.05)
    for y in range(-32, 33, 4):
        bx(steel, rx - 0.04, rx + 0.04, y - 0.04, y + 0.04, 0.0, 1.0)

# ------------------------------------------------------------------ steel structure
COL_X = [46.0, 58.0, 70.0, 80.0, 104.0, 110.0]
for cx in COL_X:
    for cy in (-28.0, 28.0):
        solid(steel, cx - 0.3, cx + 0.3, cy - 0.3, cy + 0.3, 0.0, H)

# roof trusses: long beams along y, cross beams along x, all hanging below the ceiling
for tx in [46.0, 53.0, 60.0, 67.0, 74.0, 81.0, 88.0, 95.0, 102.0, 109.0]:
    bx(steel, tx - 0.15, tx + 0.15, -35.0, 35.0, 20.9, 21.6)
for ty in [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0]:
    bx(steel, 42.0, 112.0, ty - 0.15, ty + 0.15, 20.9, 21.6)

# gantries across the pit at z=10: two beams, pillars on each rim
for gy in GANTRY_Y:
    bx(steel, 85.5, 97.5, gy - 0.25, gy + 0.25, 5.2, 5.7)
    solid(steel, 85.5, 86.1, gy - 0.3, gy + 0.3, 0.0, 5.2)
    solid(steel, 96.9, 97.5, gy - 0.3, gy + 0.3, 0.0, 5.2)
    # diagonal brace under the beam, on the west pillar
    bx(steel, 86.1, 88.0, gy - 0.1, gy + 0.1, 4.2, 5.2)

# anchor rings: hung from the gantry beams on each rim, facing the pit (ring plane along x)
ANCHORS = {}
anchor_pos = {   # rings hang over the pit, 4.4 m up, from the gantry beams at 5.2 m
    "anchor_1": (89.5, GANTRY_Y[0], 4.4),
    "anchor_2": (89.5, GANTRY_Y[1], 4.4),
    "anchor_3": (93.5, GANTRY_Y[0], 4.4),
    "anchor_4": (93.5, GANTRY_Y[1], 4.4),
}
for key, (ax, ay, az) in anchor_pos.items():
    bx(steel, ax - 0.05, ax + 0.05, ay - 0.04, ay + 0.04, az + 0.6, 5.2)  # bracket to beam
    ANCHORS[key] = (ax, ay, az)

# lighting fixtures hanging from the trusses
LIGHT_XS = [50.0, 62.0, 74.0, 104.0]
LIGHT_YS = [-24.0, 0.0, 24.0]
for lx in LIGHT_XS:
    for ly in LIGHT_YS:
        bx(steel, lx - 0.8, lx + 0.8, ly - 0.3, ly + 0.3, 19.9, 20.1)
        bx(steel, lx - 0.03, lx + 0.03, ly - 0.03, ly + 0.03, 20.1, 20.9)

# catwalks, decorative, above head height: east rail and west rail
bx(steel, 108.5, 111.7, -33.0, 33.0, 6.0, 6.15)
bx(steel, 108.5, 108.6, -33.0, 33.0, 6.15, 7.1)
bx(steel, 42.3, 44.8, -33.0, 33.0, 6.0, 6.15)
bx(steel, 44.7, 44.8, -33.0, 33.0, 6.15, 7.1)

# shelving units against the walls (also collide)
def shelf_unit(cx, cy, rz, L=2.4, D=0.6, Hh=2.6):
    for lx in (-L / 2 + 0.03, L / 2 - 0.03):
        for ly in (-D / 2 + 0.03, D / 2 - 0.03):
            x, y = rot_xy(cx, cy, rz, lx, ly)
            steel.box((x, y, Hh / 2), (0.05, 0.05, Hh), rot=(0, 0, rz), mat=0)
    for z in (0.05, 0.7, 1.35, 2.0, 2.6):
        steel.box((cx, cy, z), (L, D, 0.03), rot=(0, 0, rz), mat=0)
        for _ in range(rng.randint(1, 3)):
            lx = rng.uniform(-L / 2 + 0.3, L / 2 - 0.3)
            x, y = rot_xy(cx, cy, rz, lx, rng.uniform(-0.12, 0.12))
            dr.box((x, y, z + 0.03 + 0.12), (0.4, 0.3, 0.24), rot=(0, 0, rz + rng.uniform(-0.1, 0.1)), mat=CRD)
    COLLIDERS.append([cx, cy, Hh / 2, L, D, Hh, rz])


shelf_unit(43.4, -12.0, math.pi / 2)
shelf_unit(43.4, 14.0, math.pi / 2)
shelf_unit(101.0, -6.0, math.pi / 2)
shelf_unit(100.6, 15.0, math.pi / 2)


# workbenches (wood tops, steel legs)
def bench(cx, cy, rz, L=2.0, W=0.8, Hh=0.94):
    x, y = rot_xy(cx, cy, rz, 0.0, 0.0)
    wood.box((cx, cy, Hh - 0.03), (L, W, 0.06), rot=(0, 0, rz), mat=0)
    for lx in (-L / 2 + 0.08, L / 2 - 0.08):
        for ly in (-W / 2 + 0.08, W / 2 - 0.08):
            px, py = rot_xy(cx, cy, rz, lx, ly)
            steel.box((px, py, (Hh - 0.06) / 2), (0.06, 0.06, Hh - 0.06), rot=(0, 0, rz), mat=0)
    COLLIDERS.append([cx, cy, Hh / 2, L, W, Hh, rz])


bench(79.5, -26.0, 0.0)
bench(104.0, -22.0, 0.2)
bench(107.5, 24.0, -0.1)
bench(62.0, 26.0, 0.0)
bench(56.0, -10.0, math.pi / 2)

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


load_template("car", "coaster_car.glb")
load_template("crate", "crate.glb")


def place(key, x, y, rz, tip=0.0, zbase=0.0, name=None):
    """Linked copy: origin at (x, y), yawed by rz; lowest point lands on zbase.
    Returns the object and its oriented box [cx, cy, cz, sx, sy, sz, rz]."""
    t = TPL[key]
    R = Euler((tip, 0.0, 0.0)).to_matrix()
    pts = [R @ p for p in t["corners"]]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    obj_copy = t["obj"].copy()
    bpy.context.scene.collection.objects.link(obj_copy)
    obj_copy.name = name or f"T_{key}"
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


# stripped coaster car on jacks, centre-west of the hall
car_obj, car_box = place("car", 66.0, 4.0, 0.1, zbase=1.3, name="T_car_on_jacks")
cwx, cwy, cwz, csx, csy, csz, crz = car_box
top = cwz + csz / 2
COLLIDERS.append([cwx, cwy, top / 2, csx, csy, top, crz])  # full-height footprint, no walking under
for fx in (-0.3, 0.3):
    for fy in (-0.3, 0.3):
        px, py = rot_xy(cwx, cwy, crz, fx * csx, fy * csy)
        steel.box((px, py, 0.65), (0.3, 0.3, 1.3), rot=(0, 0, crz), mat=0)
        steel.box((px, py, 1.33), (0.5, 0.5, 0.06), rot=(0, 0, crz), mat=0)

# crates on the floor, and a stack by the west wall
for idx, (x, y, rz) in enumerate([(50.0, -20.0, 0.0), (50.6, -19.4, 0.3), (48.5, 26.0, 0.1)]):
    _, b = place("crate", x, y, rz, zbase=0.0, name=f"T_crate_{idx}")
    COLLIDERS.append(b[:6] + [rz])
    if idx == 0:
        _, b2 = place("crate", x, y, rz, zbase=b[5], name="T_crate_top")
        COLLIDERS.append([b2[0], b2[1], b2[2], b2[3], b2[4], b2[5], rz])

# ------------------------------------------------------------------ scaffolding, parts rack, rigging, track, cover
def scaffold(x0, x1, y, height=6.0, bay=2.0):
    """Tube scaffold against a wall: posts, ledgers and two plank decks. Collides."""
    n = max(1, int(round((x1 - x0) / bay)))
    for i in range(n + 1):
        x = x0 + i * (x1 - x0) / n
        for yy in (y - 0.6, y + 0.6):
            steel.box((x, yy, height / 2), (0.08, 0.08, height), mat=0)
    for z in (1.0, 2.0, 4.0, height - 0.1):
        for yy in (y - 0.6, y + 0.6):
            steel.box(((x0 + x1) / 2, yy, z), (x1 - x0, 0.06, 0.06), mat=0)
    for z in (2.0, 4.0):
        wood.box(((x0 + x1) / 2, y, z + 0.04), (x1 - x0, 1.1, 0.06), mat=0)
    COLLIDERS.append([(x0 + x1) / 2, y, height / 2, x1 - x0, 1.2, height, 0.0])


scaffold(60.0, 74.0, -31.5)
scaffold(54.0, 68.0, 31.5)
shelf_unit(48.0, -31.5, 0.0, L=6.0, D=0.8, Hh=4.0)   # parts rack, south wall


def chain(x, y, z_top, z_bot):
    """Hanging chain of alternating links, one box per link."""
    z, k = z_top, 0
    while z > z_bot:
        steel.box((x, y, z), (0.035, 0.09, 0.14), rot=(0, 0, (k % 2) * math.pi / 2), mat=0)
        z -= 0.1
        k += 1


def hoist(x, y, z_hook=14.3):
    """Electric hoist on a cross beam: trolley, motor, chain and hook."""
    steel.box((x, y, 20.45), (0.6, 0.5, 0.4), mat=0)
    steel.box((x, y, 20.1), (0.4, 0.3, 0.3), mat=0)
    chain(x, y, 20.2, z_hook + 0.2)
    steel.box((x, y, z_hook), (0.16, 0.16, 0.3), mat=0)


hoist(66.0, -20.0)
hoist(76.0, 10.0)
hoist(100.0, -10.0)


def track(x0, x1, y, rz=0.0):
    """Straight coaster track section on the floor: two rails on ties."""
    L, cx = x1 - x0, (x0 + x1) / 2
    for gy in (-0.7, 0.7):
        x, yy = rot_xy(cx, y, rz, 0.0, gy)
        steel.box((x, yy, 0.09), (L, 0.07, 0.12), rot=(0, 0, rz), mat=0)
    for k in range(int(L / 0.6) + 1):
        x, yy = rot_xy(cx, y, rz, -L / 2 + k * 0.6, 0.0)
        wood.box((x, yy, 0.02), (0.22, 1.6, 0.06), rot=(0, 0, rz), mat=0)


track(72.0, 80.0, -14.0)
track(56.0, 64.0, 16.0, rz=math.pi / 2)

# wheels on the floor (flat) and one standing upright against the shelves
for (x, y) in [(63.0, -3.0), (59.5, -4.0), (46.5, 20.0), (46.0, 20.8)]:
    dr.cyl((x, y, 0.06), 0.42, 0.12, mat=BLK, segs=18)
dr.cyl((51.0, -12.0, 0.42), 0.42, 0.12, rot=(math.pi / 2, 0, 0), mat=BLK, segs=18)

# chase cover: crate blocks in the middle of the hall, colliding
for idx, (x, y, rz) in enumerate([(72.0, -8.0, 0.0), (72.9, -8.1, 0.2), (74.4, -6.6, 0.0),
                                  (71.0, 11.0, 0.3), (71.8, 11.7, 0.0), (81.0, 16.0, 1.2)]):
    _, b = place("crate", x, y, rz, zbase=0.0, name=f"T_cover_{idx}")
    COLLIDERS.append(b[:6] + [rz])

# ------------------------------------------------------------------ dressing (procedural, baked)
# hazard stripes on the pit rim
dr.box((PIT_X0 - 0.25, 0.0, 0.002), (0.12, 70.0, 0.004), mat=YEL)
dr.box((PIT_X1 + 0.25, 0.0, 0.002), (0.12, 70.0, 0.004), mat=YEL)
# yellow paint on the floor under the north door and the benches
dr.box((NORTH_DOOR_X, 31.5, 0.002), (3.0, 0.12, 0.004), mat=YEL)
# tyre stacks and upright blue drums
for (x, y) in [(58.0, 20.0), (100.0, -20.0), (92.0, 0.0 + 0.0)]:
    if PIT_X0 - 0.5 < x < PIT_X1 + 0.5:
        continue
    for k in range(4):
        dr.cyl((x, y, 0.125 + k * 0.25), 0.36, 0.25, mat=BLK, segs=16)
    COLLIDERS.append([x, y, 0.5, 0.72, 0.72, 1.0, 0.0])
for (x, y) in [(62.0, -27.0), (63.1, -26.2), (99.0, 12.0)]:
    dr.cyl((x, y, 0.44), 0.29, 0.88, mat=BLU, segs=16)
    COLLIDERS.append([x, y, 0.44, 0.58, 0.58, 0.88, 0.0])
# loose debris, paper and cardboard around the floor
for _ in range(16):
    x = rng.uniform(45.0, 83.0) if rng.random() < 0.6 else rng.uniform(99.0, 110.0)
    y = rng.uniform(-32.0, 32.0)
    if abs(x - 66.0) < 4.0 and abs(y - 4.0) < 3.0:
        continue
    dr.box((x, y, 0.002), (0.21, 0.297, 0.002), rot=(0, 0, rng.uniform(0, 3.14)), mat=PAP)
for (x, y, rz) in [(44.0, 30.0, 0.2), (109.0, -30.0, -0.3), (73.0, -31.0, 0.1)]:
    dr.box((x, y, 0.2), (0.6, 0.45, 0.4), rot=(0, 0, rz), mat=CRD)
    dr.box((x + 0.02, y, 0.6), (0.55, 0.42, 0.36), rot=(0, 0, rz + 0.05), mat=CRD)
# oil stains and puddles (none over the pit)
for _ in range(14):
    x = rng.uniform(45.0, 83.0) if rng.random() < 0.6 else rng.uniform(99.0, 110.0)
    y = rng.uniform(-32.0, 32.0)
    dr.cyl((x, y, 0.0), rng.uniform(0.35, 1.0), 0.003, mat=OIL, segs=rng.choice([9, 11, 13]))
for _ in range(10):
    x = rng.uniform(45.0, 83.0) if rng.random() < 0.6 else rng.uniform(99.0, 110.0)
    y = rng.uniform(-32.0, 32.0)
    if abs(x - 66.0) < 4.0 and abs(y - 4.0) < 3.0:
        continue
    dr.cyl((x, y, 0.0), rng.uniform(0.4, 0.9) * rng.uniform(0.9, 1.05), 0.004, mat=PUD, segs=16)
# red warning signs on the walls and over the north door
dr.box((42.03, -6.0, 2.0), (0.02, 1.0, 0.55), mat=RED)
dr.box((111.97, 6.0, 2.0), (0.02, 1.0, 0.55), mat=RED)
dr.box((NORTH_DOOR_X, 34.97, 3.5), (1.6, 0.02, 0.4), mat=RED)
dr.box((42.03, 6.0, 2.4), (0.02, 1.0, 0.45), mat=YEL)

# ------------------------------------------------------------------ marker and light data
# lights: (pos, colour, intensity, range, flicker). pos sits just under the fixture
LIGHTS = []
for i, lx in enumerate(LIGHT_XS):
    for j, ly in enumerate(LIGHT_YS):
        flick = (i + j) % 3 == 1
        LIGHTS.append(((lx, ly, 19.7), "#cfe6ff", 0.9 if not flick else 0.6, 14.0, flick))
LIGHTS.append(((NORTH_DOOR_X, 33.0, 2.7), "#ffb070", 0.7, 7.0, False))   # warm bulb over north door
LIGHTS.append(((91.0, -30.0, 3.0), "#ff3b2a", 0.35, 8.0, True))          # dim red over the pit rim
LIGHTS.append(((50.0, 0.0, 2.5), "#ffb070", 0.5, 6.0, True))             # warm bulb near west door

JSON_LIGHTS = [{"pos": list(p), "color": c, "intensity": i, "range": r, "flicker": f}
               for p, c, i, r, f in LIGHTS]

MARKERS = {
    "claw_grapple": [79.5, -26.0, 0.95],
    "anchor_1": list(ANCHORS["anchor_1"]),
    "anchor_2": list(ANCHORS["anchor_2"]),
    "anchor_3": list(ANCHORS["anchor_3"]),
    "anchor_4": list(ANCHORS["anchor_4"]),
    "pit_a": [87.0, 0.0, 0.0],
    "pit_b": [96.2, 0.0, 0.0],
    "relic_5": [104.0, -22.0, 0.95],
    "relic_6": [107.5, 24.0, 0.95],
    "ticket_patrol_1": [48.0, -26.0, 0.0],
    "ticket_patrol_2": [48.0, 26.0, 0.0],
    "ticket_patrol_3": [60.0, -26.0, 0.0],
    "ticket_patrol_4": [60.0, 26.0, 0.0],
    "ticket_patrol_5": [106.0, -28.0, 0.0],
    "ticket_patrol_6": [106.0, 28.0, 0.0],
}

# ------------------------------------------------------------------ build meshes
W_OBJ = walls.build("T_walls", [M_WALL], uv=2.5)
F_OBJ = floor.build("T_floor", [M_FLOOR], uv=2.5)
C_OBJ = ceil_g.build("T_ceiling", [M_CEIL], uv=2.5)
S_OBJ = steel.build("T_steel", [M_STEEL], uv=1.0)
WD_OBJ = wood.build("T_benches", [M_WOOD], uv=1.0)
DRESS_OBJ = dr.build("T_dressing", DRESS_MATS)

# anchor rings: real tori, built with the operator (needs no edit mode)
for key, (ax, ay, az) in ANCHORS.items():
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.07,
                                     location=(ax, ay, az), rotation=(0.0, math.pi / 2, 0.0))
    ring = bpy.context.active_object
    ring.name = f"T_{key}_ring"
    ring.data.materials.append(M_STEEL)
    bkit.box_uv(ring, size=1.0)

# dressing: one 512 set for the procedural materials
bkit.bake_to_textures(DRESS_OBJ, SCRATCH, size=512, samples=16)
for im in bpy.data.images:
    if im.name.startswith("T_dressing") and im.filepath:
        try:
            im.pack()
        except Exception:
            pass

# ------------------------------------------------------------------ export
for im in bpy.data.images:
    if im.name in ("Render Result", "Viewer Node"):
        continue
    if im.size[0] > 512 or im.size[1] > 512:
        im.scale(512, 512)
zone_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("TPL_")]
for o in list(bpy.context.scene.objects):
    if o.name.startswith("TPL_"):
        bpy.data.objects.remove(o, do_unlink=True)
tris_total = sum(bkit.tri_count(o) for o in zone_meshes)
print(f"TOWER_TRIS total={tris_total} objects={len(zone_meshes)}")

os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
bkit.export_glb(OUT_GLB, objs=zone_meshes, image_format="JPEG")
print("TOWER_GLB", OUT_GLB, os.path.getsize(OUT_GLB))

data = {
    "zone": "tower",
    "colliders": [[round(v, 4) for v in c] for c in COLLIDERS],
    "lights": JSON_LIGHTS,
    "markers": MARKERS,
}
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
print("TOWER_JSON", OUT_JSON, len(COLLIDERS), "colliders")

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

# ------------------------------------------------------------------ preview lights (not exported)
world = bpy.data.worlds.new("T_preview_world")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.032, 0.035, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

for i, (pos, color, inten, rng_, flick) in enumerate(LIGHTS):
    if pos[2] > 6.0:
        ld = bpy.data.lights.new(f"T_prev_area_{i}", type="AREA")
        ld.size = 1.5
        ld.size_y = 0.3
        ld.energy = 260.0 * inten
    else:
        ld = bpy.data.lights.new(f"T_prev_point_{i}", type="POINT")
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
    tiles = []
    for i, (label, pos, target) in enumerate(views):
        cam = eye_camera(f"T_eye_{i}", pos, target)
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
    out = bpy.data.images.new("tw_sheet", size * 2, size * 2, alpha=False)
    out.pixels = sheet.ravel()
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def render_top(path, size=900, samples=16):
    hide = [o for o in bpy.context.scene.objects if o.name == "T_ceiling"]
    for o in hide:
        o.hide_render = True
    cd = bpy.data.cameras.new("T_top")
    cd.type = "ORTHO"
    cd.ortho_scale = 78.0
    cd.clip_end = 100
    co = bpy.data.objects.new("T_top", cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = (77.0, 0.0, 60.0)
    co.rotation_euler = (0.0, 0.0, 0.0)
    still(path, co, size, size, samples)
    bpy.data.objects.remove(co)
    for o in hide:
        o.hide_render = False


if PREVIEW_ONLY:
    views = [
        ("west doorway", (50.0, 0.0, 1.6), (40.0, 0.0, 1.6)),
        ("north doorway", (77.0, 22.0, 1.6), (77.0, 35.0, 1.6)),
        ("pit rim and anchors", (87.0, 0.0, 1.6), (92.0, -4.0, 4.0)),
        ("car on jacks", (58.0, -8.0, 1.6), (67.0, 4.0, 1.4)),
    ]
    render_eye_sheet(OUT_EYE, views)
    print("TOWER_EYE", OUT_EYE)
    render_top(OUT_TOP)
    print("TOWER_TOP", OUT_TOP)

bkit.check(objs=zone_meshes, max_tris=60000, ground=False)
bkit.report(zone_meshes)
