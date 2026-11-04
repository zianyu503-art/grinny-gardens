"""Chapter 2, zone D: packing hall with conveyor lines.

Run headless from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/map_ch2/zone_d_packing_build.py

Writes the level chunk GLB, the gameplay JSON, the saved .blend and the
eye/top previews. Coordinates follow blender/map_ch2/BRIEF.md: floor at z=0,
route along +Y, interior box x -18..18, y 74..114, ceiling 6.0.
"""
import sys, os, math, json, random

import numpy as np

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_d_packing"
GLB = f"{ROOT}/public/models/ch2/{NAME}.glb"
JSON_OUT = f"{ROOT}/public/models/ch2/{NAME}.json"
BLEND = f"{ROOT}/blender/bake/map_ch2/{NAME}.blend"
EYE_PNG = f"{ROOT}/renders/ch2_{NAME}_eye.png"
TOP_PNG = f"{ROOT}/renders/ch2_{NAME}_top.png"
CACHE = os.path.expanduser("~/.cache/blender-modeling/ch2_zone_d")
PREVIEW_DIR = f"{CACHE}/previews"
SAMPLES = 24
EYE_RES = (960, 540)
TOP_RES = 900
EYE_Z = 1.6

# ------------------------------------------------------------------ scene setup
bkit.reset_scene()
SCENE = bpy.context.scene
COLL = SCENE.collection
random.seed(20261102)
os.makedirs(CACHE, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

COLLIDERS = []
LIGHTS = []
MARKERS = {}


def link(obj):
    COLL.objects.link(obj)
    return obj


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
    """arr: HxWx3 floats in 0..1, row 0 at the top of the picture."""
    path = os.path.join(CACHE, name + ".png")
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(arr[..., :3], 0.0, 1.0)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.pixels.foreach_set(np.flipud(rgba).ravel())  # Blender rows run bottom-up
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
    rng = np.random.default_rng(11)
    # cardboard: noisy tan fibre
    n = rng.normal(0, 1, (256, 256))
    for _ in range(3):
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5.0
    n = n / (np.abs(n).max() + 1e-6)
    streak = np.repeat(rng.normal(0, 1, (256, 1)), 256, axis=1)
    base = np.array([0.52, 0.40, 0.27])
    card = base[None, None, :] * (1 + 0.09 * n[..., None] + 0.04 * streak[..., None])

    # faded smiling-toy label: cream card, red border, yellow smiley
    g = (np.arange(256) + 0.5) / 256.0
    xx, yy = np.meshgrid(g, g)
    label = np.ones((256, 256, 3)) * np.array([0.84, 0.78, 0.60])
    border = (xx < 0.06) | (xx > 0.94) | (yy < 0.06) | (yy > 0.94)
    label[border] = (0.60, 0.13, 0.10)
    r = np.hypot(xx - 0.5, yy - 0.5)
    label[r < 0.30] = (0.93, 0.76, 0.20)
    eyes = (np.hypot(xx - 0.40, yy - 0.42) < 0.035) | (np.hypot(xx - 0.60, yy - 0.42) < 0.035)
    label[eyes] = (0.12, 0.09, 0.07)
    smile = (np.abs(r - 0.17) < 0.022) & (yy > 0.50)
    label[smile] = (0.14, 0.05, 0.04)
    label *= (1 - 0.06 * rng.random((256, 256)))[..., None]

    # hazard paint: yellow and black diagonal stripes, tiles seamlessly
    stripe = ((xx + yy) * 2.0) % 1.0 < 0.5
    haz = np.where(stripe[..., None], np.array([0.84, 0.64, 0.10]), np.array([0.07, 0.06, 0.05]))
    haz = haz * (1 - 0.12 * rng.random((256, 256)))[..., None]

    return (save_png("cardboard", card), save_png("toy_label", label), save_png("hazard", haz))


card_png, label_png, haz_png = generated_textures()

floor_mat = pbr("D_floor_concrete", "concrete_floor_worn_001")
wall_mat = pbr("D_wall_paint", "peeling_painted_wall", tint=(0.74, 0.80, 0.78))
ceil_mat = pbr("D_ceiling_plaster", "plaster_grey_04", tint=(0.86, 0.86, 0.84))
steel_mat = pbr("D_steel_rusty", "rusty_metal_02")
corr_mat = pbr("D_corrugated", "corrugated_iron_02")
grate_mat = pbr("D_grate", "metal_grate_rusty")
plate_mat = pbr("D_plate", "metal_plate")
wood_mat = pbr("D_wood_pallet", "wood_planks_grey")
cardboard_mat = image_mat("D_cardboard", card_png, 0.9)
label_mat = image_mat("D_toy_label", label_png, 0.55)
hazard_mat = image_mat("D_hazard_paint", haz_png, 0.7)
sign_mat = flat("D_sign_plate", (0.60, 0.56, 0.44), 0.8)
sign_text_mat = flat("D_sign_text", (0.48, 0.09, 0.07), 0.6)
puddle_mat = flat("D_puddle", (0.012, 0.016, 0.02), 0.03)
stain_mat = flat("D_stain", (0.06, 0.045, 0.03), 0.5)
paper_mat = flat("D_paper", (0.70, 0.67, 0.56), 0.9)
toy_mat = flat("D_toy_plastic", (0.70, 0.16, 0.10), 0.35)
lens_on_mat = flat("D_lens_on", (0.85, 0.90, 0.95), 0.2, emit=(0.9, 0.95, 1.0), emit_strength=6.0)
lens_off_mat = flat("D_lens_off", (0.50, 0.48, 0.40), 0.5)


# ------------------------------------------------------------------ geometry builder
CORNERS = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
           (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def fit_uv(obj, mat_idx):
    """Map each face of the given material slots to a full 0..1 square (labels)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uvl = bm.loops.layers.uv.active
    for f in bm.faces:
        if f.material_index not in mat_idx:
            continue
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a0, a1 = [i for i in range(3) if i != ax]
        v0 = [v.co[a0] for v in f.verts]
        v1 = [v.co[a1] for v in f.verts]
        lo0, lo1 = min(v0), min(v1)
        s0 = (max(v0) - lo0) or 1.0
        s1 = (max(v1) - lo1) or 1.0
        for loop in f.loops:
            loop[uvl].uv = ((loop.vert.co[a0] - lo0) / s0, (loop.vert.co[a1] - lo1) / s1)
    bm.to_mesh(obj.data)
    bm.free()


class Builder:
    """Collects boxes, cylinders and flat polygons into one mesh object."""

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

    def box(self, cx, cy, cz, sx, sy, sz, mat, rz=0.0, rx=0.0):
        R = Matrix.Rotation(rz, 3, "Z") @ Matrix.Rotation(rx, 3, "X")
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

    def cyl(self, p0, p1, r, mat, seg=10):
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

    def finish(self, uv=None, fit=(), bevel=0.0, master=False):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = link(bpy.data.objects.new(self.name, me))
        if uv:
            bkit.box_uv(obj, size=uv)
        if fit:
            fit_uv(obj, [self.mats.index(m) for m in fit])
        if bevel:
            bkit.harden(obj, width=bevel)
        if master:
            bkit.apply_all(obj)
        return obj


# ------------------------------------------------------------------ props (imported and masters)
MASTERS = {}  # key -> (mesh, local lo, local hi)


def local_bounds(me):
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def register(key, obj):
    lo, hi = local_bounds(obj.data)
    MASTERS[key] = (obj.data, lo, hi)
    bpy.data.objects.remove(obj, do_unlink=True)  # the mesh data lives on in instances


def import_prop(key, filename):
    objs = bkit.import_glb(f"{ROOT}/public/models/{filename}")
    o = objs[0]
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    register(key, o)


def inst(key, name, x, y, z=0.0, rz=0.0):
    """Linked-data copy of a master (shares mesh data, so the GLB stays small)."""
    me, _, _ = MASTERS[key]
    o = link(bpy.data.objects.new(name, me))
    o.location = (x, y, z)
    o.rotation_euler = (0.0, 0.0, rz)
    return o


def box_json(cx, cy, cz, sx, sy, sz, rz=0.0):
    return [round(cx, 3), round(cy, 3), round(cz, 3), round(sx, 3), round(sy, 3), round(sz, 3), round(rz, 4)]


def collide_master(key, x, y, z, rz):
    _, lo, hi = MASTERS[key]
    c = (lo + hi) / 2
    w = Matrix.Rotation(rz, 3, "Z") @ c
    COLLIDERS.append(box_json(x + w.x, y + w.y, z + w.z, hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, rz))


def prop(key, name, x, y, rz=0.0, z=0.0, collide=True):
    o = inst(key, name, x, y, z, rz)
    if collide:
        collide_master(key, x, y, z, rz)
    return o


# ------------------------------------------------------------------ build masters
import_prop("conveyor", "conveyor.glb")
import_prop("crate", "crate.glb")
import_prop("plush", "plush_pile.glb")
import_prop("generator", "generator.glb")
import_prop("fusebox", "fusebox.glb")

# carton of smiling toys: cardboard body, faded label on the front (-Y) face
cb = Builder("D_carton_master", [cardboard_mat, label_mat])
cb.box(0, 0, 0.16, 0.50, 0.40, 0.32, cardboard_mat)
cb.quad([(-0.11, -0.2025, 0.05), (0.11, -0.2025, 0.05), (0.11, -0.2025, 0.27), (-0.11, -0.2025, 0.27)],
        label_mat, (0, -1, 0))
register("carton", cb.finish(uv=0.5, fit=[label_mat], master=True))

# wooden pallet, origin bottom centre, 1.2 x 1.0 m
pb = Builder("D_pallet_master", [wood_mat])
for yb in (-0.40, -0.20, 0.0, 0.20, 0.40):
    pb.box(0, yb, 0.13, 1.2, 0.16, 0.02, wood_mat)
for xs in (-0.5, 0.0, 0.5):
    pb.box(xs, 0, 0.06, 0.10, 1.0, 0.12, wood_mat)
for yb in (-0.45, 0.0, 0.45):
    pb.box(0, yb, 0.01, 1.2, 0.10, 0.02, wood_mat)
register("pallet", pb.finish(uv=0.6, bevel=0.004, master=True))

PITCH = MASTERS["conveyor"][2].x - MASTERS["conveyor"][1].x  # 3.124 m per conveyor

# ------------------------------------------------------------------ shell
fl = Builder("D_shell_floor", [floor_mat])
fl.box(0, 94.15, -0.15, 36.6, 40.3, 0.3, floor_mat)
fl.finish(uv=3.0)

wl = Builder("D_shell_walls", [wall_mat])
wl.box(-18.15, 94.0, 3.0, 0.3, 40.0, 6.0, wall_mat)          # west wall
wl.box(18.15, 94.0, 3.0, 0.3, 40.0, 6.0, wall_mat)           # east wall
wl.box(-9.75, 114.15, 3.0, 17.1, 0.3, 6.0, wall_mat)         # far wall, left of doorway
wl.box(9.75, 114.15, 3.0, 17.1, 0.3, 6.0, wall_mat)          # far wall, right of doorway
wl.box(0.0, 114.15, 4.5, 2.4, 0.3, 3.0, wall_mat)            # lintel above the doorway (z 3..6)
wl.finish(uv=2.5)

cl = Builder("D_ceil_slab", [ceil_mat])
cl.box(0, 94.15, 6.15, 36.6, 40.3, 0.3, ceil_mat)
cl.finish(uv=2.5)

COLLIDERS += [
    box_json(-18.15, 94.0, 3.0, 0.3, 40.0, 6.0),
    box_json(18.15, 94.0, 3.0, 0.3, 40.0, 6.0),
    box_json(-9.75, 114.15, 3.0, 17.1, 0.3, 6.0),
    box_json(9.75, 114.15, 3.0, 17.1, 0.3, 6.0),
    box_json(0.0, 114.15, 4.5, 2.4, 0.3, 3.0),
]

# steel door frame in the far doorway, and the leaf hanging open against the wall
df = Builder("D_shell_doorframe", [steel_mat])
df.box(-1.23, 114.14, 1.5, 0.06, 0.44, 3.0, steel_mat)
df.box(1.23, 114.14, 1.5, 0.06, 0.44, 3.0, steel_mat)
df.box(0.0, 114.14, 3.06, 2.52, 0.44, 0.12, steel_mat)
for zk in (0.45, 1.85, 2.6):
    df.box(-1.27, 113.90, zk, 0.05, 0.05, 0.16, steel_mat)  # hinge knuckles on the west jamb
df.finish(uv=0.5, bevel=0.004)

dl = Builder("D_shell_door_leaf", [steel_mat])
dl.box(-1.72, 113.85, 1.50, 0.95, 0.05, 2.95, steel_mat, rz=0.07)
dl.finish(uv=0.5, bevel=0.004)

# ------------------------------------------------------------------ mezzanine (visual only, no stairs)
md = Builder("D_mezz_deck", [grate_mat])
md.box(-16.75, 94.0, 3.45, 2.5, 36.0, 0.10, grate_mat)
md.finish(uv=0.6)

ms = Builder("D_mezz_steel", [steel_mat])
for yj in (77.5, 84.0, 90.5, 97.0, 103.5, 110.0):
    ms.box(-16.75, yj, 3.3, 2.5, 0.12, 0.2, steel_mat)
ms.box(-15.6, 94.0, 3.3, 0.15, 36.0, 0.2, steel_mat)
for yc in (78.0, 88.0, 98.0, 108.0):
    ms.box(-15.6, yc, 1.7, 0.18, 0.18, 3.4, steel_mat)
    COLLIDERS.append(box_json(-15.6, yc, 1.7, 0.18, 0.18, 3.4))
ms.cyl((-15.5, 76.2, 4.4), (-15.5, 111.8, 4.4), 0.03, steel_mat)
ms.cyl((-15.5, 76.2, 3.9), (-15.5, 111.8, 3.9), 0.025, steel_mat)
for yp in (76.2, 84.0, 92.0, 100.0, 108.0, 111.8):
    ms.cyl((-15.5, yp, 3.5), (-15.5, yp, 4.4), 0.03, steel_mat)
ms.finish(uv=0.5, bevel=0.003)

# ------------------------------------------------------------------ ceiling services
cb2 = Builder("D_ceil_beams", [steel_mat])
for yb in (78.0, 82.0, 86.0, 90.0, 94.0, 98.0, 102.0, 106.0, 110.0):
    cb2.box(0, yb, 5.73, 36.0, 0.14, 0.55, steel_mat)
    cb2.box(0, yb, 5.47, 36.0, 0.36, 0.06, steel_mat)
cb2.finish(uv=1.0, bevel=0.005)

du = Builder("D_ceil_ducts", [corr_mat, steel_mat])
for xd in (-14.0, 14.0):
    du.box(xd, 94.0, 5.15, 0.6, 36.0, 0.5, corr_mat)
    for yf in (76.5, 85.0, 93.0, 101.0, 110.0):
        du.box(xd, yf, 5.15, 0.7, 0.12, 0.6, corr_mat)
    for yh in (80.0, 90.0, 100.0, 110.0):
        du.cyl((xd, yh, 5.4), (xd, yh, 6.0), 0.03, steel_mat, seg=6)
du.finish(uv=1.0, bevel=0.004)

tr = Builder("D_ceil_trays", [steel_mat])
for xt in (-5.0, 5.0):
    tr.box(xt, 94.0, 5.05, 0.3, 36.0, 0.05, steel_mat)
    for yt in (86.0, 102.0):
        tr.box(xt, yt, 5.1, 0.04, 0.04, 0.12, steel_mat)
tr.finish(uv=1.0)

pp = Builder("D_ceil_pipes", [steel_mat])
pp.cyl((-18.0, 113.55, 4.6), (18.0, 113.55, 4.6), 0.07, steel_mat, seg=10)
for xb in (-17.0, -10.0, -3.0, 3.0, 10.0, 17.0):
    pp.box(xb, 113.80, 4.66, 0.10, 0.40, 0.10, steel_mat)
pp.cyl((-17.6, 74.5, 0.35), (-17.6, 113.5, 0.35), 0.08, steel_mat, seg=10)  # low wall pipe, west side
pp.cyl((-16.0, 113.6, 0.0), (-16.0, 113.6, 6.0), 0.08, steel_mat, seg=10)   # riser in the far corner
for zc in (1.0, 3.0, 5.0):
    pp.box(-16.0, 113.75, zc, 0.12, 0.10, 0.12, steel_mat)
pp.finish(uv=0.5)

fixtures = [
    (-12.0, 81.0, "on"), (0.0, 81.0, "on"), (12.0, 81.0, "off"),
    (-12.0, 89.0, "on"), (0.0, 89.0, "dead"), (12.0, 89.0, "on"),
    (-12.0, 97.0, "off"), (0.0, 97.0, "on"), (12.0, 97.0, "on"),
    (-12.0, 105.0, "on"), (0.0, 105.0, "flicker"), (12.0, 105.0, "off"),
]
fx = Builder("D_ceil_fixtures", [steel_mat, lens_off_mat])
fl_on = Builder("D_ceil_lens_on", [lens_on_mat])
for x, y, state in fixtures:
    fx.box(x, y, 5.22, 1.2, 0.30, 0.10, steel_mat)
    fx.cyl((x - 0.4, y, 5.27), (x - 0.4, y, 6.0), 0.015, steel_mat, seg=6)
    fx.cyl((x + 0.4, y, 5.27), (x + 0.4, y, 6.0), 0.015, steel_mat, seg=6)
    if state in ("on", "flicker"):
        fl_on.box(x, y, 5.13, 1.1, 0.24, 0.015, lens_on_mat)
    else:
        fx.box(x, y, 5.13, 1.1, 0.24, 0.015, lens_off_mat)
    if state != "dead":
        LIGHTS.append({"pos": [x, y, 5.0], "color": "#d8e4f0", "intensity": 1.0, "range": 9,
                       "flicker": state == "flicker"})
fx.finish(uv=1.0, bevel=0.003)
fl_on.finish()

for pos, color, rng_, flick in [((-16.4, 88.0, 3.0), "#ffb070", 6, False),
                                ((0.0, 112.5, 2.6), "#ff9a50", 6, True),
                                ((-6.5, 107.5, 2.0), "#ffb070", 5, False)]:
    LIGHTS.append({"pos": list(pos), "color": color, "intensity": 0.8, "range": rng_, "flicker": flick})

# ------------------------------------------------------------------ conveyor lines (3 lines, cross aisles at y ~91-94)
def conveyor_run(xline, rz, y0, n, tag):
    for k in range(n):
        yc = y0 + PITCH / 2 + k * PITCH
        prop("conveyor", f"D_prop_conveyor_{tag}{k}", xline, yc, rz)


conveyor_run(-10.5, math.pi / 2, 78.0, 4, "A1")
conveyor_run(-10.5, math.pi / 2, 93.6, 3, "A2")
conveyor_run(-6.5, math.pi / 2, 78.8, 4, "B1")
conveyor_run(-6.5, math.pi / 2, 93.6, 4, "B2")
conveyor_run(9.0, -math.pi / 2, 78.0, 4, "C1")
conveyor_run(9.0, -math.pi / 2, 93.6, 4, "C2")

# sorting chute at the end of line B, discharging into a bin
ch = Builder("D_chute", [corr_mat, steel_mat])
slope = math.atan2(-0.6, 3.1)
L = math.hypot(3.1, 0.6)
ch.box(-6.5, 107.75, 0.65, 0.8, L, 0.03, corr_mat, rx=slope)
for xs in (-6.5 - 0.42, -6.5 + 0.42):
    ch.box(xs, 107.75, 0.71, 0.04, L, 0.12, corr_mat, rx=slope)
ch.box(-6.5 - 0.38, 106.4, 0.47, 0.06, 0.06, 0.94, steel_mat)
ch.box(-6.5 + 0.38, 106.4, 0.47, 0.06, 0.06, 0.94, steel_mat)
ch.box(-6.5 - 0.38, 108.6, 0.22, 0.06, 0.06, 0.44, steel_mat)
ch.box(-6.5 + 0.38, 108.6, 0.22, 0.06, 0.06, 0.44, steel_mat)
ch.box(-6.5, 110.0, 0.02, 1.0, 0.8, 0.04, corr_mat)
ch.box(-6.5 - 0.48, 110.0, 0.45, 0.04, 0.8, 0.9, corr_mat)
ch.box(-6.5 + 0.48, 110.0, 0.45, 0.04, 0.8, 0.9, corr_mat)
ch.box(-6.5, 110.0 - 0.38, 0.45, 1.0, 0.04, 0.9, corr_mat)
ch.box(-6.5, 110.0 + 0.38, 0.45, 1.0, 0.04, 0.9, corr_mat)
ch.finish(uv=1.0, bevel=0.003)
COLLIDERS.append(box_json(-6.5, 110.0, 0.45, 1.0, 0.8, 0.9))

# ------------------------------------------------------------------ packing tables (east side)
TABLE_X, TABLE_Y = 12.2, (81.0, 85.5, 97.0, 101.5)
tt = Builder("D_table_tops", [plate_mat])
tf = Builder("D_table_frames", [steel_mat])
for ty in TABLE_Y:
    tt.box(TABLE_X, ty, 0.875, 0.8, 1.8, 0.05, plate_mat)
    for dx in (-0.36, 0.36):
        for dy in (-0.85, 0.85):
            tf.box(TABLE_X + dx, ty + dy, 0.425, 0.05, 0.05, 0.85, steel_mat)
    tf.box(TABLE_X, ty, 0.25, 0.7, 1.7, 0.03, steel_mat)
    tf.cyl((TABLE_X - 0.1, ty + 0.6, 0.90), (TABLE_X - 0.1, ty + 0.6, 0.98), 0.05, steel_mat, seg=8)
    COLLIDERS.append(box_json(TABLE_X, ty, 0.45, 0.8, 1.8, 0.9))
tt.finish(uv=1.0, bevel=0.005)
tf.finish(uv=0.5, bevel=0.003)
for ty in TABLE_Y:
    prop("carton", f"D_carton_table_{ty}", TABLE_X - 0.05, ty - 0.35, rz=random.uniform(-0.08, 0.08), z=0.9, collide=False)


# ------------------------------------------------------------------ carton stacks on pallets
def stack(px, py, rz, layers, tag, pallet=True):
    base = 0.0
    if pallet:
        inst("pallet", f"D_pallet_{tag}", px, py, 0.0, rz)
        base = 0.14
    c, s = math.cos(rz), math.sin(rz)
    for L_ in range(layers):
        for ox, oy in ((-0.27, -0.2), (0.27, -0.2), (-0.27, 0.2), (0.27, 0.2)):
            jx, jy = random.uniform(-0.012, 0.012), random.uniform(-0.012, 0.012)
            wx = px + (ox + jx) * c - (oy + jy) * s
            wy = py + (ox + jx) * s + (oy + jy) * c
            z = base + L_ * 0.32
            inst("carton", f"D_carton_{tag}_{L_}_{ox:+.1f}_{oy:+.1f}", wx, wy, z,
                 rz + random.uniform(-0.05, 0.05))
    height = base + layers * 0.32
    if pallet:
        COLLIDERS.append(box_json(px, py, height / 2, 1.2, 1.0, height, rz))
    else:
        COLLIDERS.append(box_json(px, py, height / 2, 1.0, 0.8, height, rz))


stack(-14.0, 84.0, 0.0, 3, "P1")
stack(-14.0, 98.0, 0.0, 2, "P2")
stack(15.6, 84.0, 0.10, 4, "P5")
stack(15.6, 96.0, -0.05, 3, "P6")
stack(15.6, 106.0, 0.0, 2, "P7")
stack(9.0, 110.0, 0.0, 2, "P8")
stack(-10.5, 107.5, 0.0, 2, "P9")

# loose cartons and crates
prop("carton", "D_carton_loose_0", -4.8, 79.5, rz=0.3, collide=False)
prop("carton", "D_carton_loose_1", 5.8, 80.2, rz=-0.4, collide=False)
prop("carton", "D_carton_loose_2", -13.0, 91.5, rz=1.1, collide=False)
prop("carton", "D_carton_deck_0", -16.9, 80.5, rz=0.2, z=3.5, collide=False)
prop("carton", "D_carton_deck_1", -16.6, 81.2, rz=-0.5, z=3.5, collide=False)
prop("crate", "D_prop_crate_0", -13.6, 107.0, rz=0.12)
prop("crate", "D_prop_crate_1", -13.6, 107.0, rz=-0.05, z=0.96)
prop("crate", "D_prop_crate_2", 5.5, 112.0, rz=0.6)

# ------------------------------------------------------------------ mezzanine clutter already placed; big machines
prop("generator", "D_prop_generator", 16.4, 78.0, rz=-math.pi / 2)
prop("fusebox", "D_prop_fusebox", 17.72, 102.0, rz=-math.pi / 2)
prop("plush", "D_prop_plush_0", -12.0, 111.0, rz=0.6)
prop("plush", "D_prop_plush_1", 4.8, 99.0, rz=2.1)

# ------------------------------------------------------------------ bin, pallets, floor: puddles, drains, hazard strips, paper, debris
fl_b = Builder("D_floor_puddles", [puddle_mat])
for cx, cy, r in ((1.6, 86.0, 0.9), (-1.0, 100.0, 0.6), (-13.0, 88.5, 1.1), (14.5, 90.0, 0.8),
                  (6.0, 111.0, 0.7), (-12.0, 110.5, 0.9)):
    pts = []
    for k in range(18):
        t = 2 * math.pi * k / 18
        rr = r * (1 + random.uniform(-0.18, 0.18))
        pts.append((cx + rr * math.cos(t), cy + rr * 0.75 * math.sin(t), 0.004))
    fl_b.poly(pts, puddle_mat)
fl_b.finish()

fs = Builder("D_floor_stains", [stain_mat])
for cx, cy, r in ((-3.0, 79.0, 0.8), (8.0, 96.0, 0.9), (-16.0, 102.0, 1.1), (2.0, 108.0, 0.6), (-8.0, 112.0, 0.7)):
    pts = []
    for k in range(14):
        t = 2 * math.pi * k / 14
        rr = r * (1 + random.uniform(-0.25, 0.25))
        pts.append((cx + rr * math.cos(t), cy + rr * 0.6 * math.sin(t), 0.002))
    fs.poly(pts, stain_mat)
fs.finish()

dr = Builder("D_floor_drains", [steel_mat])
for x, y in ((-1.6, 80.0), (5.0, 90.0), (-12.5, 96.0), (10.5, 100.0), (-5.0, 113.0)):
    dr.cyl((x, y, 0.0), (x, y, 0.01), 0.22, steel_mat, seg=12)
dr.finish()

hz = Builder("D_floor_hazard", [hazard_mat])
hz.box(-3.3, 94.0, 0.003, 0.15, 36.0, 0.006, hazard_mat)
hz.box(3.3, 94.0, 0.003, 0.15, 36.0, 0.006, hazard_mat)
hz.finish(uv=0.5)

pa = Builder("D_floor_paper", [paper_mat])
for _ in range(26):
    x, y = random.uniform(-17.0, 17.0), random.uniform(75.5, 112.5)
    pa.box(x, y, 0.003, 0.21, 0.30, 0.004, paper_mat, rz=random.uniform(0, math.pi))
pa.finish()

tiles = Builder("D_floor_tiles", [ceil_mat])
for x, y, rz in ((-7.5, 99.0, 0.3), (6.5, 104.5, -0.2), (-15.0, 93.0, 1.0)):
    tiles.box(x, y, 0.01, 0.6, 0.6, 0.02, ceil_mat, rz=rz)
tiles.finish(uv=2.5)

toys = Builder("D_floor_toy_bits", [toy_mat])
for cx, cy in ((-12.0, 111.0), (4.8, 99.0)):
    for _ in range(5):
        sz = random.uniform(0.05, 0.12)
        toys.box(cx + random.uniform(-0.8, 0.8), cy + random.uniform(-0.9, 0.9), sz / 2, sz, sz * 1.2, sz,
                 toy_mat, rz=random.uniform(0, math.pi))
toys.finish()

# ------------------------------------------------------------------ signs (faded 1990s, with lettering)
sg = Builder("D_signs", [sign_mat])
sg.box(-17.975, 86.0, 2.1, 0.05, 1.5, 0.55, sign_mat)     # west wall
sg.box(17.975, 102.0, 2.2, 0.05, 1.5, 0.55, sign_mat)     # east wall
sg.box(8.5, 113.975, 2.4, 1.6, 0.05, 0.5, sign_mat)       # far wall
sg.box(0.0, 113.975, 3.45, 1.0, 0.05, 0.25, sign_mat)     # exit board over the far doorway
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


text_obj("KEEP SMILING", -17.93, 86.0, 2.1, (math.pi / 2, 0, math.pi / 2), 0.12, "D_text_keep_smiling")
text_obj("PACKING LINE 3", 17.93, 102.0, 2.2, (math.pi / 2, 0, -math.pi / 2), 0.12, "D_text_packing_line")
text_obj("SAFETY FIRST", 8.5, 113.93, 2.4, (math.pi / 2, 0, 0), 0.13, "D_text_safety_first")
text_obj("EXIT", 0.0, 113.93, 3.45, (math.pi / 2, 0, 0), 0.14, "D_text_exit")

# ------------------------------------------------------------------ wall clutter: conduit, junction boxes, drip stains, notice board
cd_ = Builder("D_wall_conduit", [steel_mat])
for zc in (2.15, 2.32):   # two conduit runs down the west wall
    cd_.cyl((-17.80, 74.6, zc), (-17.80, 113.4, zc), 0.035, steel_mat, seg=8)
for yc in range(77, 114, 4):
    cd_.box(-17.86, yc + 0.5, 2.23, 0.12, 0.08, 0.26, steel_mat)  # clamps
for zj in (1.1, 3.2):
    cd_.box(17.84, 91.0, zj, 0.18, 0.5, 0.45, steel_mat)  # junction boxes on the east wall
    cd_.box(17.84, 96.5, zj, 0.18, 0.5, 0.45, steel_mat)
cd_.cyl((17.80, 74.6, 3.9), (17.80, 113.4, 3.9), 0.03, steel_mat, seg=8)
cd_.finish(uv=0.5, bevel=0.003)

dd = Builder("D_wall_drip_stains", [stain_mat])
for yd, hd, wd in ((80.5, 2.6, 0.30), (88.0, 1.9, 0.22), (101.0, 3.1, 0.34), (108.5, 2.2, 0.26)):
    dd.box(17.993, yd, 5.2 - hd / 2, 0.01, wd, hd, stain_mat)  # streaks below the ceiling line
    dd.box(-17.993, yd - 6.0, 4.6 - hd / 2, 0.01, wd, hd, stain_mat)
dd.finish()

nb = Builder("D_notice_board", [sign_mat, paper_mat])
nb.box(-17.955, 100.0, 1.7, 0.05, 1.2, 0.85, sign_mat)       # cork-like board
for yy_, zz_ in ((99.5, 2.0), (100.4, 1.6), (100.1, 1.2), (99.7, 1.85)):
    nb.box(-17.92, yy_, zz_, 0.005, 0.26, 0.32, paper_mat, rz=random.uniform(-0.12, 0.12))
nb.finish()

# ------------------------------------------------------------------ preview-only wall at the near boundary (zone C builds the real one)
pw = Builder("PREVIEW_zone_c_far_wall", [wall_mat])
pw.box(-9.75, 74.15, 3.0, 17.1, 0.3, 6.0, wall_mat)
pw.box(9.75, 74.15, 3.0, 17.1, 0.3, 6.0, wall_mat)
pw.box(0.0, 74.15, 4.5, 2.4, 0.3, 3.0, wall_mat)
pw.finish(uv=2.5)

# ------------------------------------------------------------------ markers (Blender coordinates)
MARKERS = {
    "entry": [0.0, 75.2, 0.0],
    "exit": [0.0, 113.0, 0.0],
    "hide_1": [-16.8, 84.0, 0.0],
    "hide_2": [13.8, 96.0, 0.0],
    "hide_3": [-6.5, 111.4, 0.0],
    "giggler_spawn_1": [10.6, 86.0, 0.0],
    "giggler_spawn_2": [-8.5, 100.0, 0.0],
    "giggler_spawn_3": [2.0, 104.0, 0.0],
    "giggler_spawn_4": [13.0, 110.5, 0.0],
    "patrol_1": [0.0, 78.5, 0.0],
    "patrol_2": [0.0, 92.5, 0.0],
    "patrol_3": [0.0, 106.5, 0.0],
    "patrol_4": [-8.5, 92.5, 0.0],
    "patrol_5": [10.6, 92.5, 0.0],
    "patrol_6": [-12.0, 92.5, 0.0],
}

# ------------------------------------------------------------------ preview lighting (not exported; listed in the JSON)
world = bpy.data.worlds.new("D_preview_world")
SCENE.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.015, 0.017, 0.022, 1.0)
bg.inputs["Strength"].default_value = 1.0


def preview_light(name, pos, watts, color):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = watts
    ld.color = color
    ld.shadow_soft_size = 0.3
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = pos


for i, l in enumerate(LIGHTS):
    x, y, z = l["pos"]
    watts = 260.0 if l["color"] == "#d8e4f0" else 60.0
    preview_light(f"PREVIEW_light_{i}", (x, y, z), watts,
                  (0.80, 0.90, 1.0) if l["color"] == "#d8e4f0" else (1.0, 0.62, 0.32))

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
    # Blender pixel rows run bottom-up, so the bottom row goes first in the array
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
        "far_door": ((0.0, 102.0, EYE_Z), (0.0, 114.0, EYE_Z)),
        "near_door": ((0.0, 110.0, EYE_Z), (0.0, 74.0, EYE_Z)),
        "west_mezz": ((1.5, 86.0, EYE_Z), (-16.0, 90.0, 1.6)),
        "east_tables": ((-1.0, 102.0, EYE_Z), (16.0, 88.0, 1.4)),
    }
    paths = {}
    for key, (pos, tgt) in views.items():
        cam = make_cam(f"cam_{key}", pos, tgt)
        paths[key] = render_to(cam, f"{PREVIEW_DIR}/eye_{key}.png", EYE_RES)
    write_sheet(paths["far_door"], paths["near_door"], paths["west_mezz"], paths["east_tables"], EYE_PNG)

    # top view with ceiling-level objects hidden
    ceil_objs = [o for o in bpy.data.objects if o.name.startswith("D_ceil")]
    for o in ceil_objs:
        o.hide_render = True
    cam = make_cam("cam_top", (0.0, 94.15, 60.0), (0.0, 94.15, 0.0), ortho=42.0)
    render_to(cam, TOP_PNG, (TOP_RES, TOP_RES))
    for o in ceil_objs:
        o.hide_render = False
    return paths


# ------------------------------------------------------------------ export and report
def export_objects():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("PREVIEW_")]


def report():
    objs = export_objects()
    shell_tris = sum(bkit.tri_count(o) for o in objs if not o.name.startswith("D_prop_"))
    prop_tris = sum(bkit.tri_count(o) for o in objs if o.name.startswith("D_prop_"))
    mats = sorted({m.name for o in objs for m in o.data.materials if m})
    print("ZD_REPORT shell_tris", shell_tris, "prop_tris", prop_tris)
    print("ZD_REPORT objects", len(objs), "materials", len(mats), mats)
    print("ZD_REPORT colliders", len(COLLIDERS), "lights", len(LIGHTS), "markers", len(MARKERS))
    return shell_tris, prop_tris, mats


# keep the GLB small: every texture is at most 512 px (embedded once, shared by all materials)
for _im in bpy.data.images:
    if _im.size[0] > 512 or _im.size[1] > 512:
        _im.scale(min(512, _im.size[0]), min(512, _im.size[1]))

# ZD_QUICK=1 renders only the top view and writes no GLB/blend (for layout iteration)
QUICK = os.environ.get("ZD_QUICK") == "1"

if QUICK:
    cam = make_cam("cam_top", (0.0, 94.15, 60.0), (0.0, 94.15, 0.0), ortho=42.0)
    ceil_objs = [o for o in bpy.data.objects if o.name.startswith("D_ceil")]
    for o in ceil_objs:
        o.hide_render = True
    render_to(cam, TOP_PNG, (TOP_RES, TOP_RES))
    report()
    print("ZD_DONE")
else:
    paths = render_previews()
    shell_tris, prop_tris, mats = report()

    objs = export_objects()
    os.makedirs(os.path.dirname(GLB), exist_ok=True)
    bkit.export_glb(GLB, objs, image_format="JPEG")
    print("ZD_REPORT glb_bytes", os.path.getsize(GLB))

    os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
    data = {"zone": "D", "colliders": COLLIDERS, "lights": LIGHTS, "markers": MARKERS}
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    print("ZD_DONE")
