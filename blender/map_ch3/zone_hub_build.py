"""Chapter 3, zone_hub: the Lost & Found archive (hub of the map).

Run headless from /Users/alex/恐怖遊戲2:
    python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py \
        blender/map_ch3/zone_hub_build.py /private/tmp/claude-504/hub_out

Interior box x -30..30, y -30..30, ceiling 9 (floor z = 0). Walls 0.3 m thick,
built outward from the interior box. Doorways 3 m wide, 3 m high at the centre
of all four sides (north y=+30, south y=-30, east x=+30, west x=-30).

Shelving: a grid of 3.5 m cells (centres at +-6.5, 10, 13.5 ... 24 on both axes).
Even columns hold N-S shelf runs, odd columns hold E-W runs, with random gaps.
The cross lines x=0 and y=0 are always clear (straight paths from every doorway
to the counter) and the counter area is an open 12 x 12 m square.
Writes the GLB chunk, the gameplay JSON, the saved .blend and the previews.
"""
import sys, os, math, json, random

import numpy as np

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_hub"
GLB = f"{ROOT}/public/models/ch3/{NAME}.glb"
JSON_OUT = f"{ROOT}/public/models/ch3/{NAME}.json"
BLEND = f"{ROOT}/blender/bake/map_ch3/{NAME}.blend"
EYE_PNG = f"{ROOT}/renders/ch3_{NAME}_eye.png"
TOP_PNG = f"{ROOT}/renders/ch3_{NAME}_top.png"
CACHE = os.path.expanduser("~/.cache/blender-modeling/ch3_hub")
PREVIEW_DIR = f"{CACHE}/previews"
SAMPLES = 20
EYE_RES = (640, 360)
TOP_RES = 640
EYE_Z = 1.6

H = 9.0
WT = 0.3
HALF = 30.0
DOOR_W = 3.0
DOOR_H = 3.0
CX, CY = 0.0, 11.0                     # counter centre
UNIT_D, UNIT_L, UNIT_H = 0.9, 3.0, 4.5
SHELF_Z = [0.06, 1.0, 1.95, 2.9, 3.85]  # board centres, 5 levels per unit
CELL = 3.5
POS = [6.5 + CELL * i for i in range(6)]  # cell centres, 6 per side per axis

# ------------------------------------------------------------------ scene setup
bkit.reset_scene()
SCENE = bpy.context.scene
COLL = SCENE.collection
random.seed(20261108)
rng = np.random.default_rng(2026)
os.makedirs(CACHE, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

COLLIDERS = []
LIGHTS = []
MARKERS = {}


def link(obj):
    COLL.objects.link(obj)
    return obj


def box_json(cx, cy, cz, sx, sy, sz, rz=0.0):
    return [round(cx, 3), round(cy, 3), round(cz, 3), round(sx, 3), round(sy, 3), round(sz, 3), round(rz, 4)]


# ------------------------------------------------------------------ materials
def pbr(name, asset, tint=None):
    return bkit.pbr_material(name, bkit.polyhaven_texture(asset, res="1k"), tint=tint)


def flat(name, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def save_png(name, arr):
    path = os.path.join(CACHE, name + ".png")
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(arr[..., :3], 0.0, 1.0)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.pixels.foreach_set(np.flipud(rgba).ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return path


def image_mat(name, path, rough):
    m = bkit.pbr_material(name, {"color": path})
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Roughness"].default_value = rough
    return m


def generated_textures():
    n = rng.normal(0, 1, (256, 256))
    for _ in range(3):
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5.0
    n = n / (np.abs(n).max() + 1e-6)
    streak = np.repeat(rng.normal(0, 1, (256, 1)), 256, axis=1)
    base = np.array([0.50, 0.38, 0.25])
    card = base[None, None, :] * (1 + 0.10 * n[..., None] + 0.04 * streak[..., None])
    g = (np.arange(256) + 0.5) / 256.0
    xx, yy = np.meshgrid(g, g)
    label = np.ones((256, 256, 3)) * np.array([0.82, 0.77, 0.62])
    border = (xx < 0.07) | (xx > 0.93) | (yy < 0.10) | (yy > 0.90)
    label[border] = (0.52, 0.14, 0.11)
    stripe = (np.abs(yy - 0.5) < 0.12) & (xx > 0.2) & (xx < 0.8)
    label[stripe] = (0.30, 0.27, 0.22)
    label *= (1 - 0.08 * rng.random((256, 256)))[..., None]
    return save_png("cardboard", card), save_png("label", label)


card_png, label_png = generated_textures()

floor_mat = pbr("H_floor_concrete", "concrete_floor_worn_001")
wall_mat = pbr("H_wall_paint", "peeling_painted_wall", tint=(0.80, 0.82, 0.80))
ceil_mat = pbr("H_ceiling_plaster", "plaster_grey_04", tint=(0.78, 0.78, 0.76))
steel_mat = pbr("H_shelf_steel", "rusty_metal_02")
board_mat = pbr("H_shelf_board", "wood_planks_grey")
wood_mat = pbr("H_counter_wood", "wood_table_worn")
pigeon_mat = pbr("H_pigeon_wood", "old_planks_02")
duct_mat = pbr("H_duct_metal", "corrugated_iron_02")
sack_mat = pbr("H_sack_hessian", "hessian_230")
cardboard_mat = image_mat("H_cardboard", card_png, 0.92)
label_mat = image_mat("H_label", label_png, 0.6)
backpack_mat = flat("H_backpack", (0.10, 0.13, 0.22), 0.85)
teddy_mat = flat("H_teddy", (0.42, 0.29, 0.18), 0.95)
raincoat_mat = flat("H_raincoat", (0.70, 0.60, 0.18), 0.45)
shoe_mat = flat("H_shoe", (0.05, 0.05, 0.05), 0.6)
tag_mat = flat("H_tag", (0.84, 0.83, 0.77), 0.8)
string_mat = flat("H_string", (0.30, 0.28, 0.24), 0.9)
paper_mat = flat("H_paper", (0.70, 0.67, 0.56), 0.9)
ledger_red = flat("H_ledger_red", (0.40, 0.10, 0.09), 0.7)
ledger_green = flat("H_ledger_green", (0.11, 0.25, 0.20), 0.7)
brass_mat = flat("H_brass", (0.62, 0.45, 0.18), 0.35, metal=1.0)
puddle_mat = flat("H_puddle", (0.012, 0.016, 0.02), 0.03)
stain_mat = flat("H_stain", (0.07, 0.05, 0.03), 0.6)
sign_mat = flat("H_sign_plate", (0.60, 0.56, 0.44), 0.8)
sign_text_mat = flat("H_sign_text", (0.48, 0.09, 0.07), 0.6)
lamp_mat = flat("H_lamp_housing", (0.50, 0.48, 0.40), 0.5)
mesh_mat = flat("H_mesh_wire", (0.32, 0.32, 0.30), 0.5, metal=0.6)


# ------------------------------------------------------------------ geometry builder
CORNERS = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
           (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


class Builder:
    """Collects boxes, cylinders, spheres and flat polygons into one mesh object."""

    def __init__(self, name, mats):
        self.name = name
        self.mats = list(mats)
        self.bm = bmesh.new()

    def idx(self, mat):
        return self.mats.index(mat)

    def _face(self, vs, mi, hint):
        n = (vs[1].co - vs[0].co).cross(vs[2].co - vs[0].co)
        if n.dot(hint) < 0:
            vs = list(reversed(vs))
        f = self.bm.faces.new(vs)
        f.material_index = mi
        return f

    def box(self, cx, cy, cz, sx, sy, sz, mat, rz=0.0):
        R = Matrix.Rotation(rz, 3, "Z")
        C = Vector((cx, cy, cz))
        vs = [self.bm.verts.new(R @ Vector((a * sx, b * sy, c * sz)) + C) for a, b, c in CORNERS]
        mi = self.idx(mat)
        for f in FACES:
            fv = [vs[i] for i in f]
            fc = sum((v.co for v in fv), Vector()) / 4
            self._face(fv, mi, fc - C)

    def quad(self, pts, mat, hint):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        self._face(vs, self.idx(mat), Vector(hint))

    def poly(self, pts, mat):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        self._face(vs, self.idx(mat), Vector((0, 0, 1)))

    def sphere(self, c, r, mat, subdiv=1, sc=(1.0, 1.0, 1.0)):
        before_v, before_f = set(self.bm.verts), set(self.bm.faces)
        bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=r)
        new_v = [v for v in self.bm.verts if v not in before_v]
        new_f = [f for f in self.bm.faces if f not in before_f]
        for v in new_v:
            v.co = Vector((v.co.x * sc[0], v.co.y * sc[1], v.co.z * sc[2])) + Vector(c)
        mi = self.idx(mat)
        for f in new_f:
            f.material_index = mi

    def cyl(self, p0, p1, r, mat, seg=6):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        before_v, before_f = set(self.bm.verts), set(self.bm.faces)
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=r, depth=L)
        new_v = [v for v in self.bm.verts if v not in before_v]
        new_f = [f for f in self.bm.faces if f not in before_f]
        M = Matrix.Translation((p0 + p1) / 2) @ Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        for v in new_v:
            v.co = M @ v.co
        mi = self.idx(mat)
        for f in new_f:
            f.material_index = mi

    def finish(self, uv=None, bevel=0.0, master=False):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = link(bpy.data.objects.new(self.name, me))
        if uv:
            bkit.box_uv(obj, size=uv)
        if bevel:
            bkit.harden(obj, width=bevel)
        if master:
            bkit.apply_all(obj)
        return obj


# ------------------------------------------------------------------ linked masters (instanced props)
MASTERS = {}


def local_bounds(me):
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def register(key, obj):
    lo, hi = local_bounds(obj.data)
    MASTERS[key] = (obj.data, lo, hi)
    bpy.data.objects.remove(obj, do_unlink=True)


def inst(key, name, x, y, z=0.0, rz=0.0, rx=0.0, ry=0.0):
    me, _, _ = MASTERS[key]
    o = link(bpy.data.objects.new(name, me))
    o.location = (x, y, z)
    o.rotation_euler = (rx, ry, rz)
    return o


# ------------------------------------------------------------------ shell: floor, ceiling, walls with doorways
fl = Builder("H_shell_floor", [floor_mat])
fl.box(0, 0, -0.15, 2 * HALF + 2 * WT, 2 * HALF + 2 * WT, 0.3, floor_mat)
fl.finish(uv=3.0)

cl = Builder("H_ceil_slab", [ceil_mat])
cl.box(0, 0, H + 0.15, 2 * HALF + 2 * WT, 2 * HALF + 2 * WT, 0.3, ceil_mat)
cl.finish(uv=2.5)

WALL_COLLIDERS = []


def wall_x(B, yc, mat):
    for a, b in ((-HALF - WT, -DOOR_W / 2), (DOOR_W / 2, HALF + WT)):
        B.box((a + b) / 2, yc, H / 2, b - a, WT, H, mat)
        WALL_COLLIDERS.append(box_json((a + b) / 2, yc, H / 2, b - a, WT, H))
    B.box(0, yc, (DOOR_H + H) / 2, DOOR_W, WT, H - DOOR_H, mat)
    WALL_COLLIDERS.append(box_json(0, yc, (DOOR_H + H) / 2, DOOR_W, WT, H - DOOR_H))


def wall_y(B, xc, mat):
    for a, b in ((-HALF - WT, -DOOR_W / 2), (DOOR_W / 2, HALF + WT)):
        B.box(xc, (a + b) / 2, H / 2, WT, b - a, H, mat)
        WALL_COLLIDERS.append(box_json(xc, (a + b) / 2, H / 2, WT, b - a, H))
    B.box(xc, 0, (DOOR_H + H) / 2, WT, DOOR_W, H - DOOR_H, mat)
    WALL_COLLIDERS.append(box_json(xc, 0, (DOOR_H + H) / 2, WT, DOOR_W, H - DOOR_H))


wl = Builder("H_shell_walls", [wall_mat])
wall_x(wl, HALF + WT / 2, wall_mat)
wall_x(wl, -HALF - WT / 2, wall_mat)
wall_y(wl, HALF + WT / 2, wall_mat)
wall_y(wl, -HALF - WT / 2, wall_mat)
wl.finish(uv=2.5)
COLLIDERS += WALL_COLLIDERS

df = Builder("H_shell_doorframes", [steel_mat])
for c, orient in ((HALF + WT / 2, "x"), (-HALF - WT / 2, "x"), (HALF + WT / 2, "y"), (-HALF - WT / 2, "y")):
    if orient == "x":
        for s in (-1, 1):
            df.box(s * (DOOR_W / 2 + 0.03), c, DOOR_H / 2, 0.08, WT + 0.06, DOOR_H, steel_mat)
        df.box(0, c, DOOR_H + 0.05, DOOR_W + 0.14, WT + 0.06, 0.1, steel_mat)
    else:
        for s in (-1, 1):
            df.box(c, s * (DOOR_W / 2 + 0.03), DOOR_H / 2, WT + 0.06, 0.08, DOOR_H, steel_mat)
        df.box(c, 0, DOOR_H + 0.05, WT + 0.06, DOOR_W + 0.14, 0.1, steel_mat)
df.finish(uv=0.5, bevel=0.003)

# ------------------------------------------------------------------ ceiling services
ce = Builder("H_ceil_beams", [steel_mat])
for yb in (-18.0, 0.0, 18.0):
    ce.box(0, yb, 8.6, 2 * HALF, 0.4, 0.6, steel_mat)
for xb in (-18.0, 0.0, 18.0):
    ce.box(xb, 0, 8.6, 0.4, 2 * HALF, 0.6, steel_mat)
ce.finish(uv=1.0, bevel=0.003)

du = Builder("H_ceil_ducts", [duct_mat])
for xd in (-9.0, 9.0):
    du.box(xd, 0, 7.9, 0.8, 2 * HALF - 1.0, 0.8, duct_mat)
du.finish(uv=1.0, bevel=0.004)

LAMPS = [(x, y) for x in (-18.0, 0.0, 18.0) for y in (-18.0, 0.0, 18.0)]
la = Builder("H_ceil_lamps", [lamp_mat, steel_mat])
for x, y in LAMPS:
    la.box(x, y, 8.12, 1.2, 0.35, 0.10, lamp_mat)
    la.cyl((x, y, 8.17), (x, y, 8.3), 0.01, steel_mat, seg=5)
la.finish(uv=0.5)

tag_master = Builder("H_tag_master", [tag_mat])
tag_master.box(0, 0, 0.0, 0.10, 0.005, 0.14, tag_mat)
register("tag", tag_master.finish(uv=None, master=True))

stg = Builder("H_ceil_strings", [string_mat])
TAG_SPOTS = []
while len(TAG_SPOTS) < 26:
    tx = random.uniform(-27, 27)
    ty = random.uniform(-27, 27)
    if abs(tx) < 7.5 and 3 < ty < 19:          # keep the counter area open
        continue
    if abs(tx) < 2.5 or abs(ty) < 2.5:          # keep the straight doorway paths open
        continue
    TAG_SPOTS.append((tx, ty))
for tx, ty in TAG_SPOTS:
    stg.cyl((tx, ty, 8.3), (tx, ty, 6.95), 0.004, string_mat, seg=4)
stg.finish(uv=None)
for k, (tx, ty) in enumerate(TAG_SPOTS):
    inst("tag", f"H_ceil_tag_{k}", tx, ty, 6.91, random.uniform(-0.4, 0.4))

# ------------------------------------------------------------------ shelf units: grid of cells
# A cell is (x, y) with x, y = +-POS[i]. Even column index -> N-S run, odd -> E-W run.
RELIC_1 = (-13.5, -13.5)
RELIC_2 = (20.5, 17.0)
cells = {}
for sx in (-1, 1):
    for i in range(6):
        for sy in (-1, 1):
            for j in range(6):
                xc, yc = sx * POS[i], sy * POS[j]
                if i % 2 == 0:
                    kind, p = "NS", 0.8
                else:
                    kind, p = "EW", 0.6
                occ = random.random() < p
                if i == 0 and sy > 0 and 5.0 < yc < 17.0:   # counter zone
                    occ = False
                cells[(xc, yc)] = kind if occ else None
cells[RELIC_1] = "NS"
cells[RELIC_2] = "NS"


def in_counter_zone(x, y):
    return abs(x) <= POS[0] and 5.0 < y < 17.0


def cross_line(x, y):
    return abs(x) < 2.6 or abs(y) < 2.6


free_cells = [c for c, k in cells.items() if k is None and not in_counter_zone(*c)]
random.shuffle(free_cells)

ub = Builder("H_shelf_unit_master", [steel_mat, board_mat])
for sx_ in (-0.42, 0.42):
    for sy_ in (-1.45, 1.45):
        ub.box(sx_, sy_, UNIT_H / 2, 0.05, 0.05, UNIT_H, steel_mat)
ub.box(-0.44, 0, UNIT_H / 2, 0.02, UNIT_L, UNIT_H, steel_mat)
for zl in SHELF_Z:
    ub.box(0, 0, zl, UNIT_D, UNIT_L, 0.03, board_mat)
    ub.box(0, -1.48, zl - 0.02, UNIT_D, 0.02, 0.04, steel_mat)
    ub.box(0, 1.48, zl - 0.02, UNIT_D, 0.02, 0.04, steel_mat)
register("unit", ub.finish(uv=1.0, bevel=0.003, master=True))

shoebox_master = Builder("H_item_shoebox", [cardboard_mat, label_mat])
shoebox_master.box(0, 0, 0.06, 0.30, 0.19, 0.12, cardboard_mat)
shoebox_master.quad([(-0.15, -0.0955, 0.03), (0.15, -0.0955, 0.03), (0.15, -0.0955, 0.10), (-0.15, -0.0955, 0.10)],
                    label_mat, (0, -1, 0))
register("shoebox", shoebox_master.finish(uv=0.5, master=True))

sh = Builder("H_item_shoe", [shoe_mat])
sh.box(0, 0, 0.035, 0.26, 0.10, 0.05, shoe_mat)
sh.box(0.04, 0, 0.09, 0.14, 0.09, 0.07, shoe_mat)
register("shoe", sh.finish(uv=None, master=True))

bp = Builder("H_item_backpack", [backpack_mat])
bp.box(0, 0, 0.17, 0.30, 0.20, 0.34, backpack_mat)
bp.box(0, -0.02, 0.36, 0.28, 0.22, 0.06, backpack_mat)
bp.cyl((-0.16, 0.0, 0.1), (-0.16, 0.0, 0.3), 0.012, backpack_mat, seg=4)
register("backpack", bp.finish(uv=None, master=True))

tb = Builder("H_item_teddy", [teddy_mat])
tb.sphere((0, 0, 0.13), 0.13, teddy_mat, subdiv=2)
tb.sphere((0, 0, 0.30), 0.09, teddy_mat, subdiv=2)
tb.sphere((-0.07, 0, 0.385), 0.034, teddy_mat, subdiv=1)
tb.sphere((0.07, 0, 0.385), 0.034, teddy_mat, subdiv=1)
register("teddy", tb.finish(uv=None, master=True))

rc = Builder("H_item_raincoat", [raincoat_mat])
rc.box(0, 0, 0.04, 0.36, 0.26, 0.08, raincoat_mat)
rc.box(0, 0.09, 0.10, 0.12, 0.10, 0.04, raincoat_mat)
register("raincoat", rc.finish(uv=None, master=True))

sack = Builder("H_sack_master", [sack_mat])
sack.sphere((0, 0, 0.154), 0.28, sack_mat, subdiv=2, sc=(1.0, 0.8, 0.55))
sack.cyl((0, 0, 0.27), (0, 0, 0.34), 0.05, sack_mat, seg=6)
register("sack", sack.finish(uv=0.5, master=True))

cage = Builder("H_cage_master", [mesh_mat, steel_mat])
for sx_ in (-1.0, 1.0):
    for sy_ in (-0.6, 0.6):
        cage.box(sx_, sy_, 1.2, 0.05, 0.05, 2.4, steel_mat)
cage.box(0, -0.6, 2.42, 2.0, 0.05, 0.05, steel_mat)
cage.box(0, 0.6, 2.42, 2.0, 0.05, 0.05, steel_mat)
cage.box(-1.0, 0, 2.42, 0.05, 1.2, 0.05, steel_mat)
cage.box(1.0, 0, 2.42, 0.05, 1.2, 0.05, steel_mat)
for k in range(8):
    cage.box(-0.9 + k * 0.26, -0.6, 1.2, 0.02, 0.02, 2.4, mesh_mat)     # mesh door bars
for z in (0.3, 0.9, 1.5, 2.1):
    cage.box(0, -0.6, z, 2.0, 0.02, 0.02, mesh_mat)
cage.box(0.9, -0.62, 1.2, 0.05, 0.03, 0.2, steel_mat)                    # latch
register("cage", cage.finish(uv=1.0, bevel=0.002, master=True))

lad = Builder("H_ladder_master", [steel_mat])
lad.box(-0.22, 0, 1.3, 0.05, 0.05, 2.6, steel_mat)
lad.box(0.22, 0, 1.3, 0.05, 0.05, 2.6, steel_mat)
for k in range(8):
    lad.box(0, 0, 0.35 + k * 0.3, 0.44, 0.03, 0.03, steel_mat)
lad.cyl((-0.25, -0.12, 0.06), (0.25, -0.12, 0.06), 0.06, steel_mat, seg=6)
lad.cyl((-0.25, 0.12, 0.06), (0.25, 0.12, 0.06), 0.06, steel_mat, seg=6)
register("ladder", lad.finish(uv=1.0, bevel=0.002, master=True))

# shelf items: shoe boxes, lost shoes, backpacks, teddy bears, tiny raincoats
ITEM_KEYS = ["shoebox"] * 4 + ["shoe"] * 2 + ["backpack"] * 3 + ["teddy"] * 2 + ["raincoat"] * 3
ITEM_Y = [-1.05, -0.35, 0.35, 1.05]
RELIC_CELLS = {RELIC_1, RELIC_2}
TILT_CAND = []
shelf_items = 0
unit_n = 0
collider_units = 0
tipped = []
leaned = []
for (xc, yc), kind in sorted(cells.items()):
    if kind is None:
        continue
    unit_n += 1
    name = f"H_unit_{unit_n}"
    outer = abs(xc) in (POS[2], POS[4]) and kind == "NS" and (xc, yc) not in RELIC_CELLS
    if outer and len(tipped) < 4 and random.random() < 0.22:
        s = 1 if xc > 0 else -1
        nb = (xc + s * CELL, yc)
        if cells.get(nb) is None and nb not in RELIC_CELLS:
            inst("unit", name, xc, yc, 0.45, 0.0, ry=s * math.pi / 2)
            COLLIDERS.append(box_json(xc + s * 2.25, yc, 0.45, UNIT_H, UNIT_L, UNIT_D, 0.0))
            tipped.append((xc, yc))
            continue
    if outer and len(leaned) < 4 and random.random() < 0.22:
        s = 1 if xc > 0 else -1
        inst("unit", name, xc, yc, 0.0, 0.0, ry=s * 0.2)
        COLLIDERS.append(box_json(xc + s * 0.45, yc, UNIT_H / 2, UNIT_D + 0.2, UNIT_L, UNIT_H, 0.0))
        leaned.append((xc, yc))
        continue
    rz = math.pi / 2 if kind == "EW" else 0.0
    inst("unit", name, xc, yc, 0.0, rz)
    if kind == "EW":
        COLLIDERS.append(box_json(xc, yc, UNIT_H / 2, UNIT_L, UNIT_D, UNIT_H))
    else:
        COLLIDERS.append(box_json(xc, yc, UNIT_H / 2, UNIT_D, UNIT_L, UNIT_H))
    for zl in SHELF_Z:
        for yo in ITEM_Y:
            if random.random() < 0.12:
                continue
            key = random.choice(ITEM_KEYS)
            ox = random.uniform(-0.06, 0.06)
            oy = yo + random.uniform(-0.05, 0.05)
            if kind == "EW":        # local +y maps to world -x for a 90-degree turn
                wx, wy = xc - oy, yc + ox
                irz = random.uniform(-0.25, 0.25) + math.pi / 2
            else:
                wx, wy = xc + ox, yc + oy
                irz = random.uniform(-0.25, 0.25)
            inst(key, f"H_item_{shelf_items}", wx, wy, zl + 0.015, irz)
            shelf_items += 1

# relic markers sit on the level-1 board of their units
MARKERS = {
    "spawn": [0.0, -22.0, 0.0],
    "claw_scissors": [CX - 4.0, CY, 1.08],
    "save": [CX, CY, 1.08],
    "relic_1": [RELIC_1[0], RELIC_1[1], SHELF_Z[1] + 0.015],
    "relic_2": [RELIC_2[0], RELIC_2[1], SHELF_Z[1] + 0.015],
}

# cages, rolling ladders, sacks, spilled boxes and piles on the free floor cells
for k in range(4):
    x, y = free_cells.pop()
    rz = random.choice([0.0, math.pi / 2])
    inst("cage", f"H_cage_{k}", x, y, 0.0, rz)
    if rz == 0.0:
        COLLIDERS.append(box_json(x, y, 1.2, 2.0, 1.2, 2.4, 0.0))
    else:
        COLLIDERS.append(box_json(x, y, 1.2, 1.2, 2.0, 2.4, 0.0))
for k in range(3):
    x, y = free_cells.pop()
    rz = random.uniform(0, math.pi)
    inst("ladder", f"H_ladder_{k}", x, y, 0.0, rz)
    COLLIDERS.append(box_json(x, y, 1.3, 0.5, 0.15, 2.6, rz))

for k in range(8):
    cx_, cy_ = random.choice(free_cells)
    x, y = cx_ + random.uniform(-0.8, 0.8), cy_ + random.uniform(-0.8, 0.8)
    rz = random.uniform(0, 6.28)
    inst("sack", f"H_sack_{k}", x, y, 0.0, rz)
    COLLIDERS.append(box_json(x, y, 0.15, 0.6, 0.5, 0.3, rz))

for k in range(14):
    cx_, cy_ = random.choice(free_cells)
    x, y = cx_ + random.uniform(-0.9, 0.9), cy_ + random.uniform(-0.9, 0.9)
    rz = random.uniform(0, 6.28)
    inst("shoebox", f"H_spill_{k}", x, y, 0.0, rz)
    COLLIDERS.append(box_json(x, y, 0.06, 0.3, 0.19, 0.12, rz))

pile_n = 0
for k in range(6):
    cx_, cy_ = random.choice(free_cells)
    for m in range(random.randint(2, 3)):
        key = random.choice(["backpack", "teddy", "raincoat"])
        x, y = cx_ + random.uniform(-0.7, 0.7), cy_ + random.uniform(-0.7, 0.7)
        inst(key, f"H_pile_{pile_n}", x, y, 0.0, random.uniform(0, 6.28))
        pile_n += 1
    COLLIDERS.append(box_json(cx_, cy_, 0.2, 0.8, 0.8, 0.4, 0.0))

# ------------------------------------------------------------------ central counter, bell, ledgers, pigeon-hole wall
ct = Builder("H_counter", [wood_mat, brass_mat, ledger_red, ledger_green, paper_mat])
ct.box(CX, CY, 0.50, 9.0, 1.0, 1.0, wood_mat)
ct.box(CX, CY, 1.04, 9.4, 1.2, 0.08, wood_mat)
ct.box(CX, CY - 0.62, 1.00, 9.4, 0.04, 0.06, wood_mat)
ct.box(-2.8, CY + 0.10, 1.12, 0.30, 0.22, 0.05, ledger_red, rz=0.04)
ct.box(-2.8, CY + 0.05, 1.17, 0.28, 0.21, 0.05, ledger_green, rz=-0.05)
ct.box(-1.9, CY - 0.10, 1.10, 0.36, 0.28, 0.02, paper_mat, rz=0.10)
ct.cyl((3.0, CY, 1.08), (3.0, CY, 1.12), 0.09, brass_mat, seg=10)
ct.sphere((3.0, CY, 1.16), 0.10, brass_mat, subdiv=2)
ct.finish(uv=1.0, bevel=0.004)
COLLIDERS.append(box_json(CX, CY, 0.54, 9.0, 1.2, 1.08))

pg = Builder("H_pigeonhole", [pigeon_mat, paper_mat])
for xc in (-9.0, 9.0):
    pg.box(xc, 29.80, 2.3, 10.0, 0.10, 4.6, pigeon_mat)
    for i in range(11):
        pg.box(xc - 5.0 + i, 29.70, 2.3, 0.03, 0.12, 4.6, pigeon_mat)
    for j in range(7):
        pg.box(xc, 29.70, j * 4.6 / 6, 10.0, 0.12, 0.03, pigeon_mat)
    for i in range(10):
        for j in range(6):
            if random.random() < 0.40:
                pg.box(xc - 4.5 + i, 29.72, 0.38 + j * 4.6 / 6, 0.34, 0.02, 0.22, paper_mat,
                       rz=random.uniform(-0.1, 0.1))
pg.finish(uv=1.0)
COLLIDERS.append(box_json(-9.0, 29.8, 2.3, 10.0, 0.4, 4.6))
COLLIDERS.append(box_json(9.0, 29.8, 2.3, 10.0, 0.4, 4.6))

# ------------------------------------------------------------------ floor: puddles, debris, wall stains
pu = Builder("H_puddles", [puddle_mat])
PUDDLES = [(-7.0, -15.0, 1.8), (6.5, -8.0, 1.4), (-12.0, 4.0, 1.2), (10.0, 21.0, 2.0),
           (-6.0, 22.0, 1.6), (3.5, -22.0, 1.3), (-22.0, 2.5, 1.1), (23.0, -3.0, 1.5),
           (-16.0, -26.0, 1.5), (14.0, 26.0, 1.4), (-24.0, 9.0, 1.3)]
for cx, cy, r in PUDDLES:
    pts = []
    for k in range(10):
        t = 2 * math.pi * k / 10
        rr = r * random.uniform(0.6, 1.0)
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t), 0.004))
    pu.poly(pts, puddle_mat)
pu.finish(uv=None)

db = Builder("H_debris", [board_mat, steel_mat])
for k in range(6):
    cx_, cy_ = random.choice(free_cells)
    db.box(cx_, cy_, 0.02, 1.2, 0.14, 0.03, board_mat, rz=random.uniform(0, math.pi))
for k in range(3):
    cx_, cy_ = random.choice(free_cells)
    db.box(cx_, cy_ + 0.5, 0.07, 0.5, 0.5, 0.14, steel_mat, rz=random.uniform(0, 1.5))
db.finish(uv=1.0, bevel=0.003)

st = Builder("H_wall_stains", [stain_mat])
for k in range(12):
    side = k % 4
    w = random.uniform(0.5, 1.2)
    top = random.uniform(5.0, 8.4)
    h = random.uniform(1.5, 3.0)
    c = random.uniform(-26, 26)
    if abs(c) < 4.0:
        c = 8.0 if c >= 0 else -8.0
    if side == 0:
        st.quad([(c - w / 2, HALF - 0.01, top), (c + w / 2, HALF - 0.01, top),
                 (c + w / 2, HALF - 0.01, top - h), (c - w / 2, HALF - 0.01, top - h)], stain_mat, (0, -1, 0))
    elif side == 1:
        st.quad([(c - w / 2, -HALF + 0.01, top), (c + w / 2, -HALF + 0.01, top),
                 (c + w / 2, -HALF + 0.01, top - h), (c - w / 2, -HALF + 0.01, top - h)], stain_mat, (0, 1, 0))
    elif side == 2:
        st.quad([(HALF - 0.01, c - w / 2, top), (HALF - 0.01, c + w / 2, top),
                 (HALF - 0.01, c + w / 2, top - h), (HALF - 0.01, c - w / 2, top - h)], stain_mat, (-1, 0, 0))
    else:
        st.quad([(-HALF + 0.01, c - w / 2, top), (-HALF + 0.01, c + w / 2, top),
                 (-HALF + 0.01, c + w / 2, top - h), (-HALF + 0.01, c - w / 2, top - h)], stain_mat, (1, 0, 0))
st.finish(uv=None)

# ------------------------------------------------------------------ signs (faded 1990s, with lettering)
sg = Builder("H_signs", [sign_mat])
sg.box(0.0, HALF - 0.04, 4.8, 4.2, 0.05, 0.9, sign_mat)
sg.box(HALF - 0.04, 16.0, 2.2, 0.05, 1.6, 0.55, sign_mat)
sg.box(-HALF + 0.04, -14.0, 2.2, 0.05, 1.6, 0.55, sign_mat)
sg.box(0.0, -HALF + 0.04, 2.4, 2.4, 0.05, 0.5, sign_mat)
sg.finish(uv=None, bevel=0.003)


def text_obj(body, x, y, z, rot, size, name):
    cu = bpy.data.curves.new(name + "_cu", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = 0.004
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = link(bpy.data.objects.new(name, cu))
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    ob.data.materials.clear()
    ob.data.materials.append(sign_text_mat)
    return ob


text_obj("LOST & FOUND", 0.0, HALF - 0.1, 4.8, (math.pi / 2, 0, 0), 0.42, "H_text_lost_found")
text_obj("CLAIM YOUR SHOE", HALF - 0.1, 16.0, 2.2, (math.pi / 2, 0, -math.pi / 2), 0.13, "H_text_claim")
text_obj("KEEP YOUR TICKET", -HALF + 0.1, -14.0, 2.2, (math.pi / 2, 0, math.pi / 2), 0.13, "H_text_ticket")
text_obj("NOTHING LEAVES", 0.0, -HALF + 0.1, 2.4, (math.pi / 2, 0, math.pi), 0.16, "H_text_nothing")

# ------------------------------------------------------------------ lights (exported): mostly dead, a few alive
ALIVE = {(0.0, 0.0): ("#d8e4f0", False), (-18.0, -18.0): ("#ffb070", True),
         (18.0, 18.0): ("#d8e4f0", False), (-18.0, 18.0): ("#d8e4f0", True),
         (18.0, -18.0): ("#ffb070", False)}
for (x, y), (color, flick) in ALIVE.items():
    LIGHTS.append({"pos": [x, y, 8.0], "color": color, "intensity": 0.8, "range": 10,
                   "flicker": flick})

# ------------------------------------------------------------------ preview lighting (not exported)
world = bpy.data.worlds.new("H_preview_world")
SCENE.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.02, 0.022, 0.026, 1.0)
bg.inputs["Strength"].default_value = 1.0


def preview_light(name, pos, watts, color):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = watts
    ld.color = color
    ld.shadow_soft_size = 0.5
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = pos


for i, (x, y) in enumerate(LAMPS):
    if (x, y) in ALIVE:
        color = ALIVE[(x, y)][0]
        preview_light(f"PREVIEW_light_{i}", (x, y, 8.0), 900.0,
                      (0.80, 0.90, 1.0) if color == "#d8e4f0" else (1.0, 0.62, 0.32))
    else:
        preview_light(f"PREVIEW_light_{i}", (x, y, 8.0), 60.0, (0.9, 0.9, 1.0))

# ------------------------------------------------------------------ render helpers
SCENE.render.engine = "CYCLES"
SCENE.cycles.samples = SAMPLES
SCENE.cycles.use_denoising = True
SCENE.render.film_transparent = False
SCENE.render.image_settings.file_format = "PNG"


def make_cam(name, pos, target=None, lens=24.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_end = 300.0
    co = link(bpy.data.objects.new(name, cd))
    co.location = pos
    d = Vector(target) - Vector(pos)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return co


def render_to(cam, path, res):
    SCENE.camera = cam
    SCENE.render.resolution_x, SCENE.render.resolution_y = res
    SCENE.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    return path


def load_rgba(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    arr = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    return arr


def write_sheet(tl, tr_, bl, br, out):
    top = np.hstack([load_rgba(tl), load_rgba(tr_)])
    bot = np.hstack([load_rgba(bl), load_rgba(br)])
    sheet = np.vstack([bot, top])
    sheet[..., 3] = 1.0
    im = bpy.data.images.new("eye_sheet", sheet.shape[1], sheet.shape[0], alpha=False)
    im.pixels.foreach_set(sheet.ravel())
    im.filepath_raw = out
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def hide_ceiling(flag):
    for o in bpy.data.objects:
        if o.name.startswith("H_ceil"):
            o.hide_render = flag


def render_previews():
    os.makedirs(os.path.dirname(EYE_PNG), exist_ok=True)
    views = {
        "north_door": ((0.0, -18.0, EYE_Z), (0.0, HALF, EYE_Z)),
        "east_door": ((-14.0, 0.0, EYE_Z), (HALF, 0.0, EYE_Z)),
        "south_door": ((0.0, 20.0, EYE_Z), (0.0, -HALF, EYE_Z)),
        "west_door": ((14.0, 0.0, EYE_Z), (-HALF, 0.0, EYE_Z)),
    }
    paths = {}
    for key, (pos, tgt) in views.items():
        cam = make_cam(f"cam_{key}", pos, tgt)
        paths[key] = render_to(cam, f"{PREVIEW_DIR}/eye_{key}.png", EYE_RES)
    write_sheet(paths["north_door"], paths["east_door"], paths["south_door"], paths["west_door"], EYE_PNG)

    hide_ceiling(True)
    cam = make_cam("cam_top", (0.0, 0.0, 60.0), (0.0, 0.0, 0.0), ortho=64.0)
    render_to(cam, TOP_PNG, (TOP_RES, TOP_RES))
    hide_ceiling(False)
    return paths


# ------------------------------------------------------------------ export and report
def export_objects():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("PREVIEW_")]


def report(objs):
    shell = sum(bkit.tri_count(o) for o in objs if o.data.users == 1)
    shared = {o.data.name: o for o in objs if o.data.users > 1}
    shared_tris = sum(bkit.tri_count(o) for o in shared.values())
    mats = sorted({m.name for o in objs for m in o.data.materials if m})
    print("ZH_REPORT shell_tris", shell, "instanced_master_tris", shared_tris,
          "instances", sum(1 for o in objs if o.data.users > 1))
    print("ZH_REPORT objects", len(objs), "materials", len(mats))
    print("ZH_REPORT colliders", len(COLLIDERS), "lights", len(LIGHTS), "markers", len(MARKERS),
          "units", unit_n, "tipped", len(tipped), "leaned", len(leaned))


for _im in bpy.data.images:
    if _im.size[0] > 512 or _im.size[1] > 512:
        _im.scale(min(512, _im.size[0]), min(512, _im.size[1]))

render_previews()
objs = export_objects()
report(objs)

os.makedirs(os.path.dirname(GLB), exist_ok=True)
bkit.export_glb(GLB, objs, image_format="JPEG")
print("ZH_REPORT glb_bytes", os.path.getsize(GLB))

data = {"zone": "hub", "colliders": COLLIDERS, "lights": LIGHTS, "markers": MARKERS}
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
print("ZH_DONE")
