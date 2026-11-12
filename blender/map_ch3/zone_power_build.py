"""Chapter 3, zone power: transformer hall with giant ceramic insulators, a caged electric
maze (1.8 m corridors, cell pitch 1.9 m, seeded perfect maze), a breaker service room,
and the flicker arena behind the finale door.

Run from /Users/alex/恐怖遊戲2 (scratch out dir is only a runner argument):
    python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py \
        blender/map_ch3/zone_power_build.py <scratch_dir>

Coordinates follow blender/map_ch3/BRIEF.md: interior box x 42..122, y 45..125,
ceiling 10. Floor top at z=0. South doorway at x=77, y=45, 3 m wide and 3 m high,
joined to the tower by a corridor (x 75.5..78.5, y 35..45, 3.4 m high).
"""
import sys, os, math, json, random

import numpy as np

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_power"
GLB = f"{ROOT}/public/models/ch3/{NAME}.glb"
JSON_OUT = f"{ROOT}/public/models/ch3/{NAME}.json"
BLEND = f"{ROOT}/blender/bake/map_ch3/{NAME}.blend"
EYE_PNG = f"{ROOT}/renders/ch3_{NAME}_eye.png"
TOP_PNG = f"{ROOT}/renders/ch3_{NAME}_top.png"
CACHE = os.path.expanduser("~/.cache/blender-modeling/ch3_power")
PREVIEW_DIR = f"{CACHE}/previews"
SAMPLES = 20
EYE_RES = (640, 360)
TOP_RES = 800
EYE_Z = 1.6

bkit.reset_scene()
SCENE = bpy.context.scene
COLL = SCENE.collection
random.seed(20261108)
MAZE_RNG = random.Random(20261112)
rng_np = np.random.default_rng(23)
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


def flat(name, color, rough=0.6, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_strength
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
    g = (np.arange(256) + 0.5) / 256.0
    xx, yy = np.meshgrid(g, g)
    # glazed porcelain: off-white with brown grime streaks
    glaze = np.array([0.74, 0.70, 0.62])[None, None, :] * (1 + 0.04 * rng_np.normal(0, 1, (256, 256)))[..., None]
    streak = np.repeat(rng_np.normal(0, 1, (256, 1)), 256, axis=1)
    grime = np.clip(0.5 + 0.5 * np.sin(yy * 30 + streak * 0.8), 0, 1)
    glaze = glaze * (1 - 0.25 * grime[..., None] * (yy < 0.5)[..., None])
    # hazard paint: yellow and black diagonal stripes, tiles seamlessly
    stripe = ((xx + yy) * 2.0) % 1.0 < 0.5
    haz = np.where(stripe[..., None], np.array([0.84, 0.64, 0.10]), np.array([0.07, 0.06, 0.05]))
    haz = haz * (1 - 0.12 * rng_np.random((256, 256)))[..., None]
    return save_png("glaze", glaze), save_png("hazard", haz)


glaze_png, haz_png = generated_textures()

floor_mat = pbr("P_floor_concrete", "concrete_floor_worn_001")
wall_mat = pbr("P_wall_paint", "peeling_painted_wall", tint=(0.72, 0.76, 0.74))
ceil_mat = pbr("P_ceiling_plaster", "plaster_grey_04", tint=(0.80, 0.80, 0.78))
steel_mat = pbr("P_steel_rusty", "rusty_metal_02")
grate_mat = pbr("P_grate", "metal_grate_rusty")
plate_mat = pbr("P_plate", "metal_plate")
glaze_mat = image_mat("P_ceramic_glaze", glaze_png, 0.35)
hazard_mat = image_mat("P_hazard_sign", haz_png, 0.7)
tank_mat = flat("P_tank_paint", (0.22, 0.24, 0.23), 0.55)
dark_mat = flat("P_black_cable", (0.03, 0.03, 0.03), 0.7)
panel_mat = flat("P_breaker_panel", (0.45, 0.44, 0.40), 0.5)
switch_mat = flat("P_switch_red", (0.52, 0.07, 0.05), 0.45)
sign_mat = flat("P_sign_yellow", (0.80, 0.66, 0.12), 0.6)
puddle_mat = flat("P_puddle", (0.012, 0.016, 0.02), 0.03)
stain_mat = flat("P_stain", (0.06, 0.045, 0.03), 0.5)
wood_mat = pbr("P_wood_planks", "wood_planks_grey")


# ------------------------------------------------------------------ geometry builder
CORNERS = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
           (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


class Builder:
    """Collects boxes and cylinders into one mesh object (one object per material group)."""

    def __init__(self, name, mats):
        self.name = name
        self.mats = list(mats)
        self.bm = bmesh.new()

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
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
        mi = self._mi(mat)
        for f in FACES:
            fv = [vs[i] for i in f]
            fc = sum((v.co for v in fv), Vector()) / 4
            self._face(fv, mi, fc - C)

    def cyl(self, p0, p1, r, mat, seg=8):
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
        mi = self._mi(mat)
        for f in new_f:
            f.material_index = mi

    def finish(self, uv=2.0, bevel=0.0):
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
        return obj


def solid(b, mat, cx, cy, cz, sx, sy, sz, rz=0.0, collide=True):
    b.box(cx, cy, cz, sx, sy, sz, mat, rz=rz)
    if collide:
        COLLIDERS.append(box_json(cx, cy, cz, sx, sy, sz, rz))


def wall(b, mat, axis, fixed, a0, a1, z0, z1, t, openings=(), top=2.6):
    """Wall along x (axis 'x', at y=fixed) or along y (axis 'y', at x=fixed).
    openings: list of (lo, hi) gaps; a lintel fills each gap from `top` up to z1."""
    pieces, pos = [], a0
    for lo, hi in sorted(openings):
        pieces.append((pos, lo, z0, z1))
        pieces.append((lo, hi, top, z1))
        pos = hi
    pieces.append((pos, a1, z0, z1))
    for lo, hi, zl, zh in pieces:
        if hi - lo < 1e-3 or zh - zl < 1e-3:
            continue
        c, s = (lo + hi) / 2, hi - lo
        zc, zs = (zl + zh) / 2, zh - zl
        if axis == "x":
            solid(b, mat, c, fixed, zc, s, t, zs)
        else:
            solid(b, mat, fixed, c, zc, t, s, zs)


# ------------------------------------------------------------------ shell
WALL_H = 10.0
fl = Builder("PWR_shell_floor", [floor_mat, puddle_mat, stain_mat])
fl.box(82.0, 85.0, -0.15, 80.6, 80.6, 0.3, floor_mat)
for xp, yp, sx, sy in [(60.0, 52.0, 3.0, 1.6), (92.0, 74.0, 2.2, 1.2), (114.0, 100.0, 3.0, 2.0),
                       (50.0, 100.0, 2.0, 1.6), (98.0, 112.0, 2.4, 1.4)]:
    fl.box(xp, yp, 0.001, sx, sy, 0.002, puddle_mat)
fl.box(70.0, 60.0, 0.001, 1.6, 1.0, 0.002, stain_mat)
fl.box(108.0, 88.0, 0.001, 1.8, 1.2, 0.002, stain_mat)
fl.finish(uv=3.0)

# corridor to the tower: x 75.5..78.5, y 35..45, 3.4 m high (this zone builds it)
cr = Builder("PWR_shell_corridor", [floor_mat, wall_mat])
cr.box(77.0, 40.0, -0.15, 3.0, 10.0, 0.3, floor_mat)
for xw in (75.35, 78.65):
    wall(cr, wall_mat, "y", xw, 35.0, 45.0, 0.0, 3.4, 0.3)
cr.box(77.0, 40.0, 3.55, 3.6, 10.0, 0.3, wall_mat)
cr.finish(uv=2.0)

shell = Builder("PWR_shell_walls", [wall_mat])
wall(shell, wall_mat, "y", 41.85, 44.7, 125.3, 0.0, WALL_H, 0.3)           # west
wall(shell, wall_mat, "y", 122.15, 44.7, 125.3, 0.0, WALL_H, 0.3)          # east
wall(shell, wall_mat, "x", 125.15, 41.7, 122.3, 0.0, WALL_H, 0.3)          # north
wall(shell, wall_mat, "x", 44.85, 41.7, 122.3, 0.0, WALL_H, 0.3,           # south, with the tower doorway
     openings=[(75.5, 78.5)], top=3.0)
shell.finish(uv=2.5)

ce = Builder("PWR_ceil_slab", [ceil_mat])
ce.box(82.0, 85.0, WALL_H + 0.15, 80.6, 80.6, 0.3, ceil_mat)
ce.finish(uv=2.5)

ctr = Builder("PWR_ceil_trays", [steel_mat, dark_mat])
for yt in (49.0, 56.0, 63.0):                       # cable trays across the transformer hall
    ctr.box(82.0, yt, 8.8, 80.0, 0.45, 0.08, steel_mat)
    for xc in range(44, 122, 10):
        ctr.cyl((xc + 0.5, yt, 8.8), (xc + 0.5, yt, 9.9), 0.04, steel_mat, seg=6)
for xt in (46.0, 60.0, 84.0, 100.0, 116.0):     # cable bundles drooping from the trays
    ctr.cyl((xt, 52.0, 8.7), (xt + 0.1, 52.0, 6.2), 0.05, dark_mat, seg=6)
ctr.finish(uv=1.0)

# ------------------------------------------------------------------ transformer hall (y 45..66)
fence = Builder("PWR_fence", [grate_mat])
wall(fence, grate_mat, "x", 66.0, 41.8, 122.2, 0.0, 3.0, 0.2,
     openings=[(74.0, 80.0), (112.0, 116.0)], top=3.0)     # maze entrance, service room entrance
fence.finish(uv=1.0)

tr = Builder("PWR_transformers", [tank_mat, steel_mat, glaze_mat, dark_mat])
def transformer(x, y):
    tr.box(x, y, 1.2, 3.0, 2.0, 2.4, tank_mat)
    COLLIDERS.append(box_json(x, y, 1.2, 3.0, 2.0, 2.4))
    for k in range(-3, 4):
        tr.box(x + k * 0.4, y + 1.15, 1.2, 0.12, 0.3, 2.2, tank_mat)      # radiator fins
    for bx in (-0.8, 0.0, 0.8):
        tr.cyl((x + bx, y, 2.4), (x + bx, y, 3.0), 0.12, steel_mat, seg=8)  # bushings
    tr.cyl((x, y - 1.2, 0.0), (x, y - 1.2, 0.5), 0.08, dark_mat, seg=6)
for xt, yt in [(50.0, 50.0), (62.0, 50.0), (104.0, 50.0), (116.0, 50.0)]:
    transformer(xt, yt)
tr.finish(uv=1.5, bevel=0.003)

ins = Builder("PWR_insulators", [steel_mat, glaze_mat])
def insulator(x, y):
    ins.cyl((x, y, 0.0), (x, y, 0.6), 0.35, steel_mat, seg=10)
    z = 0.6
    for k in range(9):
        r = 0.72 if k % 2 == 0 else 0.55
        ins.cyl((x, y, z), (x, y, z + 0.2), r, glaze_mat, seg=14)
        z += 0.42
    ins.cyl((x, y, z), (x, y, z + 0.5), 0.12, steel_mat, seg=8)
    COLLIDERS.append(box_json(x, y, 2.6, 1.44, 1.44, 5.2))
for xi in (46.5, 54.5, 92.5, 100.5, 108.5, 116.5):
    insulator(xi, 61.0)
ins.finish(uv=1.0)

# benches and crates in the hall (cover; the bench holds the claw_charge marker)
hb = Builder("PWR_hall_props", [wood_mat, steel_mat, dark_mat, sign_mat])
solid(hb, wood_mat, 56.0, 47.5, 0.95, 1.4, 0.8, 0.08)               # bench top
for xl, yl in [(55.4, 47.2), (56.6, 47.2), (55.4, 47.8), (56.6, 47.8)]:
    hb.box(xl, yl, 0.45, 0.06, 0.06, 0.9, steel_mat)
solid(hb, dark_mat, 56.0, 47.5, 1.05, 0.5, 0.4, 0.04, collide=False)  # tool case lid
for xc, yc, s in [(70.0, 47.0, 1.0), (72.0, 47.5, 0.8), (88.0, 48.0, 1.0), (122 - 4.0, 60.0, 1.1)]:
    solid(hb, wood_mat, xc, yc, s / 2, s, s, s, rz=random.uniform(-0.2, 0.2))
solid(hb, steel_mat, 100.0, 46.8, 0.7, 1.2, 0.8, 1.4)               # tool cabinet
for xw in (44.0, 120.0):
    solid(hb, sign_mat, xw, 45.2, 1.3, 1.0, 0.04, 0.6, collide=False)  # yellow warning placards
hb.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ maze (electric caged corridors)
C_N, R_N = 35, 22
X0, Y0, P = 42.6, 66.1, 1.9             # cell pitch 1.9 m, corridor 1.8 m clear
ENTRY_COL, EXIT_COL = 17, 20            # entrance under the fence gap, exit under the finale door
vopen, hopen = set(), set()             # carved walls: vertical line (i, r), horizontal line (c, j)
visited = {(ENTRY_COL, 0)}
stack = [(ENTRY_COL, 0)]
while stack:
    c, r = stack[-1]
    nbrs = [(c + dc, r + dr, dc, dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= c + dc < C_N and 0 <= r + dr < R_N and (c + dc, r + dr) not in visited]
    if nbrs:
        nc, nr, dc, dr = MAZE_RNG.choice(nbrs)
        if dc == 1:
            vopen.add((c + 1, r))
        elif dc == -1:
            vopen.add((c, r))
        elif dr == 1:
            hopen.add((c, r + 1))
        else:
            hopen.add((c, r))
        visited.add((nc, nr))
        stack.append((nc, nr))
    else:
        stack.pop()
assert len(visited) == C_N * R_N

def cell_xy(c, r):
    return X0 + (c + 0.5) * P, Y0 + (r + 0.5) * P

def neighbours_open(c, r):
    out = []
    if (c + 1, r) in vopen: out.append((c + 1, r))
    if (c, r) in vopen: out.append((c - 1, r))
    if (c, r + 1) in hopen: out.append((c, r + 1))
    if (c, r) in hopen: out.append((c, r - 1))
    if r == 0 and c == ENTRY_COL: out.append("entrance")
    return out

# BFS from the entrance for distances, dead ends for the node markers
dist = {(ENTRY_COL, 0): 0}
queue = [(ENTRY_COL, 0)]
while queue:
    cur = queue.pop(0)
    for nb in neighbours_open(*cur):
        if nb == "entrance" or nb in dist:
            continue
        dist[nb] = dist[cur] + 1
        queue.append(nb)
assert len(dist) == C_N * R_N

dead_ends = [cell for cell in dist if cell != (ENTRY_COL, 0)
             and len([n for n in neighbours_open(*cell) if n != "entrance"]) == 1]
dead_ends.sort(key=lambda cell: -dist[cell])
chosen = []
for cell in dead_ends:
    if all(abs(cell[0] - o[0]) + abs(cell[1] - o[1]) >= 9 for o in chosen):
        chosen.append(cell)
    if len(chosen) == 6:
        break
assert len(chosen) == 6, f"only {len(chosen)} spaced dead ends"

mz = Builder("PWR_maze_walls", [grate_mat])
solid_v = []
for i in range(C_N + 1):
    for r in range(R_N):
        if (i, r) in vopen:
            continue
        x, y = X0 + i * P, Y0 + (r + 0.5) * P
        mz.box(x, y, 1.5, 0.1, P + 0.1, 3.0, grate_mat)
        COLLIDERS.append(box_json(x, y, 1.5, 0.1, P + 0.1, 3.0))
        solid_v.append((x, y))
for j in range(R_N + 1):
    for c in range(C_N):
        if (c, j) in hopen:
            continue
        if (j == 0 and c == ENTRY_COL) or (j == R_N and c == EXIT_COL):
            continue
        x, y = X0 + (c + 0.5) * P, Y0 + j * P
        mz.box(x, y, 1.5, P + 0.1, 0.1, 3.0, grate_mat)
        COLLIDERS.append(box_json(x, y, 1.5, P + 0.1, 0.1, 3.0))
mz.finish(uv=1.0)

# hazard placards on random maze walls (decor, no collision)
hz = Builder("PWR_maze_signs", [hazard_mat])
for x, y in solid_v:
    if MAZE_RNG.random() < 0.05:
        hz.box(x + 0.06, y, 1.9, 0.02, 0.5, 0.4, hazard_mat)
hz.finish(uv=1.0)

# finale door: a grate gate across the top opening of the maze
fd = Builder("PWR_finale_door", [steel_mat, grate_mat, switch_mat])
FDX, FDY = cell_xy(EXIT_COL, R_N - 1)[0], Y0 + R_N * P
fd.box(FDX - 0.95, FDY, 1.5, 0.12, 0.12, 3.0, steel_mat)
fd.box(FDX + 0.95, FDY, 1.5, 0.12, 0.12, 3.0, steel_mat)
fd.box(FDX, FDY, 2.95, 2.0, 0.12, 0.12, steel_mat)
fd.box(FDX, FDY, 1.4, 1.8, 0.05, 2.8, grate_mat)
fd.box(FDX + 0.7, FDY - 0.1, 1.2, 0.12, 0.1, 0.2, switch_mat)
fd.finish(uv=1.0, bevel=0.003)
COLLIDERS.append(box_json(FDX, FDY, 1.4, 1.8, 0.12, 2.8))

# ------------------------------------------------------------------ arena (flicker arena) and cover
ar = Builder("PWR_arena_cover", [tank_mat, steel_mat, glaze_mat, dark_mat])
for xt, yt in [(60.0, 118.0), (100.0, 116.0)]:
    ar.box(xt, yt, 1.2, 3.0, 2.0, 2.4, tank_mat)
    COLLIDERS.append(box_json(xt, yt, 1.2, 3.0, 2.0, 2.4))
for xi, yi in [(70.0, 112.5), (94.0, 112.5), (74.0, 122.0), (90.0, 123.0)]:
    insulator_pos = (xi, yi)
    ar.cyl((xi, yi, 0.0), (xi, yi, 0.6), 0.35, steel_mat, seg=10)
    z = 0.6
    for k in range(9):
        r = 0.72 if k % 2 == 0 else 0.55
        ar.cyl((xi, yi, z), (xi, yi, z + 0.2), r, glaze_mat, seg=14)
        z += 0.42
    COLLIDERS.append(box_json(xi, yi, 2.6, 1.44, 1.44, 5.2))
ar.finish(uv=1.0)

# ------------------------------------------------------------------ service room (x 109..122, y 66..108)
sv = Builder("PWR_service", [panel_mat, switch_mat, dark_mat, sign_mat, steel_mat])
wall(sv, steel_mat, "x", 107.95, 109.0, 122.2, 0.0, WALL_H, 0.3)     # north wall to the arena
for yb in (74.0, 86.0, 98.0):
    solid(sv, panel_mat, 121.55, yb, 1.5, 0.3, 1.0, 1.8)               # breaker cabinet
    for k in range(3):
        sv.box(121.36, yb - 0.25 + k * 0.25, 1.9 - k * 0.2, 0.04, 0.16, 0.1, switch_mat)
    sv.box(121.36, yb, 0.85, 0.04, 0.5, 0.25, dark_mat)                # reset plate
    sv.box(121.36, yb, 2.7, 0.04, 0.6, 0.25, sign_mat)                 # warning plate above
for yc in (80.0, 92.0):
    solid(sv, steel_mat, 113.0, yc, 0.5, 0.8, 1.2, 1.0)                # spare parts crates
sv.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ the claw_charge marker bench is in hb above
# ------------------------------------------------------------------ lights (dead ones have no entry)
LIGHTS = [
    {"pos": [52.0, 56.0, 9.3], "color": "#d8e4f0", "intensity": 0.5, "range": 16, "flicker": False},
    {"pos": [72.0, 56.0, 9.3], "color": "#d8e4f0", "intensity": 0.4, "range": 14, "flicker": True},
    {"pos": [96.0, 56.0, 9.3], "color": "#ffb070", "intensity": 0.4, "range": 14, "flicker": True},
    {"pos": [116.0, 56.0, 9.3], "color": "#d8e4f0", "intensity": 0.3, "range": 12, "flicker": False},
    {"pos": [60.0, 80.0, 2.7], "color": "#d8e4f0", "intensity": 0.3, "range": 8, "flicker": True},
    {"pos": [88.0, 92.0, 2.7], "color": "#ffb070", "intensity": 0.3, "range": 8, "flicker": True},
    {"pos": [50.0, 102.0, 2.7], "color": "#d8e4f0", "intensity": 0.25, "range": 8, "flicker": False},
    {"pos": [100.0, 76.0, 2.7], "color": "#d8e4f0", "intensity": 0.3, "range": 8, "flicker": True},
    {"pos": [119.0, 80.0, 6.0], "color": "#ffb070", "intensity": 0.4, "range": 10, "flicker": True},
    {"pos": [118.0, 98.0, 6.0], "color": "#d8e4f0", "intensity": 0.3, "range": 10, "flicker": False},
    {"pos": [82.0, 117.0, 9.5], "color": "#ff5050", "intensity": 0.5, "range": 18, "flicker": True},
    {"pos": [60.0, 122.0, 9.5], "color": "#d8e4f0", "intensity": 0.2, "range": 14, "flicker": False},
    {"pos": [106.0, 121.0, 9.5], "color": "#d8e4f0", "intensity": 0.2, "range": 14, "flicker": True},
]

# ------------------------------------------------------------------ markers (Blender coordinates, ground level)
MARKERS = {
    "entry": [77.0, 40.0, 0.0],
    "claw_charge": [56.0, 47.5, 1.0],
    "breaker_1": [119.0, 74.0, 0.0],
    "breaker_2": [119.0, 86.0, 0.0],
    "breaker_3": [119.0, 98.0, 0.0],
    "flicker_arena": [82.0, 117.0, 0.0],
    "finale_door": [FDX, FDY, 0.0],
    "relic_9": [46.0, 121.0, 0.0],
}
for k, cell in enumerate(sorted(chosen, key=lambda cell: dist[cell])):
    x, y = cell_xy(*cell)
    MARKERS[f"node_{k + 1}"] = [round(x, 3), round(y, 3), 0.0]
for k, cell in enumerate([(5, 5), (28, 8), (8, 15), (30, 17), (14, 4), (24, 20)]):
    x, y = cell_xy(*cell)
    MARKERS[f"ticket_patrol_{k + 1}"] = [round(x, 3), round(y, 3), 0.0]

# ------------------------------------------------------------------ preview lighting (not exported)
world = bpy.data.worlds.new("P_preview_world")
SCENE.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.015, 0.017, 0.022, 1.0)
bg.inputs["Strength"].default_value = 1.0


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


for i, l in enumerate(LIGHTS):
    ld = bpy.data.lights.new(f"PREVIEW_light_{i}", "POINT")
    ld.energy = 2400.0 * l["intensity"]
    ld.color = hex_rgb(l["color"])
    ld.shadow_soft_size = 0.3
    ob = link(bpy.data.objects.new(f"PREVIEW_light_{i}", ld))
    ob.location = tuple(l["pos"])


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


def render_previews():
    os.makedirs(os.path.dirname(EYE_PNG), exist_ok=True)
    views = {
        "south_door": ((77.0, 40.0, EYE_Z), (77.0, 56.0, 1.4)),
        "maze_entry": ((75.85, 69.0, EYE_Z), (75.85, 80.0, EYE_Z)),
        "finale_door": ((81.55, 105.0, EYE_Z), (81.55, 112.0, EYE_Z)),
        "breakers": ((114.0, 72.0, EYE_Z), (121.5, 80.0, 1.5)),
    }
    paths = {}
    for key, (pos, tgt) in views.items():
        cam = make_cam(f"cam_{key}", pos, tgt)
        paths[key] = render_to(cam, f"{PREVIEW_DIR}/eye_{key}.png", EYE_RES)
    write_sheet(paths["south_door"], paths["maze_entry"], paths["finale_door"], paths["breakers"], EYE_PNG)
    ceil_objs = [o for o in bpy.data.objects if o.name.startswith("PWR_ceil")]
    for o in ceil_objs:
        o.hide_render = True
    cam = make_cam("cam_top", (82.0, 85.0, 90.0), (82.0, 85.0, 0.0), ortho=84.0)
    render_to(cam, TOP_PNG, (TOP_RES, TOP_RES))
    for o in ceil_objs:
        o.hide_render = False
    return paths


def export_objects():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("PREVIEW_")]


def report():
    objs = export_objects()
    tris = sum(bkit.tri_count(o) for o in objs)
    print("PZ_REPORT objects", len(objs), "tris", tris)
    print("PZ_REPORT colliders", len(COLLIDERS), "lights", len(LIGHTS), "markers", len(MARKERS))
    return tris


for _im in bpy.data.images:
    if _im.size[0] > 512 or _im.size[1] > 512:
        _im.scale(min(512, _im.size[0]), min(512, _im.size[1]))

paths = render_previews()
tris = report()
objs = export_objects()
bkit.check(objs, max_tris=60000)
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bkit.export_glb(GLB, objs, image_format="JPEG")
print("PZ_REPORT glb_bytes", os.path.getsize(GLB))
os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
data = {"zone": NAME, "colliders": COLLIDERS, "lights": LIGHTS, "markers": MARKERS}
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
print("PZ_DONE")
