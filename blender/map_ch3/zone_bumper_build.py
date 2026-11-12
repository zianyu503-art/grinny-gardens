"""Chapter 3, zone_bumper: the rusted bumper car arena.

Run headless from /Users/alex/恐怖遊戲2:
    python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py \
        blender/map_ch3/zone_bumper_build.py /private/tmp/claude-504/bumper_out

Interior box x -40..40, y 42..122, ceiling 12 (floor z = 0). Walls 0.3 m thick,
built outward from the interior box. South doorway 3 m wide, 3 m high at x=0,
joined to the Lost & Found hub by a corridor (x -1.5..1.5, y 30..42, 3.4 m high,
built here). A solid wall at y=92 has a 10 m gap closed by an iron shutter that
only the magnet claw opens (magnet_gate_1). A rubber barrier ring (1 m high, with
four gaps) encloses the track. The operator booth (north-west) is reached by a
stair and holds the claw magnet on its desk.
Writes the GLB chunk, the gameplay JSON, the saved .blend and the previews.
"""
import sys, os, math, json, random

import numpy as np

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_bumper"
GLB = f"{ROOT}/public/models/ch3/{NAME}.glb"
JSON_OUT = f"{ROOT}/public/models/ch3/{NAME}.json"
BLEND = f"{ROOT}/blender/bake/map_ch3/{NAME}.blend"
EYE_PNG = f"{ROOT}/renders/ch3_{NAME}_eye.png"
TOP_PNG = f"{ROOT}/renders/ch3_{NAME}_top.png"
CACHE = os.path.expanduser("~/.cache/blender-modeling/ch3_bumper")
PREVIEW_DIR = f"{CACHE}/previews"
SAMPLES = 20
EYE_RES = (640, 360)
TOP_RES = 640
EYE_Z = 1.6

X0, X1 = -40.0, 40.0
Y0, Y1 = 42.0, 122.0
H = 12.0
WT = 0.3
DOOR_W, DOOR_H = 3.0, 3.0
YC = (Y0 + Y1) / 2
GATE_Y = 92.0
GATE_HALF = 5.0
SH_H = 4.5
CORR_W = 3.0
CORR_H = 3.4
CORR_Y0, CORR_Y1 = 30.0, 42.0
# rubber barrier ring around the track
RING_X, RING_Y0, RING_Y1 = 24.0, 62.0, 102.0
RING_H, RING_T, RING_GAP = 1.0, 0.4, 1.5
# operator booth (north-west, raised)
BX, BY = -33.0, 113.0
PLAT_Z = 2.9

# ------------------------------------------------------------------ scene setup
bkit.reset_scene()
SCENE = bpy.context.scene
COLL = SCENE.collection
random.seed(20261109)
rng = np.random.default_rng(3109)
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
    g = (np.arange(256) + 0.5) / 256.0
    xx, yy = np.meshgrid(g, g)
    stripe = ((xx + yy) * 2.0) % 1.0 < 0.5
    haz = np.where(stripe[..., None], np.array([0.62, 0.48, 0.12]), np.array([0.06, 0.05, 0.045]))
    haz = haz * (1 - 0.18 * rng.random((256, 256)))[..., None]
    return (save_png("hazard_faded", haz),)


(haz_png,) = generated_textures()

floor_mat = pbr("B_floor_concrete", "dirty_concrete")
floor2_mat = pbr("B_floor_tiles", "concrete_floor_02", tint=(0.72, 0.70, 0.66))
wall_mat = pbr("B_wall_plaster", "plastered_wall_04", tint=(0.78, 0.80, 0.78))
ceil_mat = pbr("B_ceiling_plaster", "plaster_grey_04", tint=(0.6, 0.6, 0.6))
steel_mat = pbr("B_steel_rust", "rust_coarse_01")
rust_mat = pbr("B_rust_plate", "rusty_metal_04")
iron_mat = pbr("B_iron_crate", "metal_plate_02")
shutter_mat = pbr("B_shutter", "painted_metal_shutter")
rubber_mat = pbr("B_rubber_bumper", "rubberized_track")
hazard_mat = image_mat("B_hazard_paint", haz_png, 0.7)
puddle_mat = flat("B_puddle", (0.012, 0.016, 0.02), 0.03)
oil_mat = flat("B_oil", (0.03, 0.03, 0.035), 0.12)
stain_mat = flat("B_stain", (0.07, 0.05, 0.03), 0.6)
paint_mat = flat("B_lane_paint", (0.66, 0.56, 0.16), 0.7)
sign_mat = flat("B_sign_plate", (0.60, 0.56, 0.44), 0.8)
sign_text_mat = flat("B_sign_text", (0.48, 0.09, 0.07), 0.6)
glass_mat = flat("B_glass", (0.05, 0.07, 0.08), 0.08)
lamp_mat = flat("B_lamp_housing", (0.50, 0.48, 0.40), 0.5)
relic_mat = flat("B_relic_box", (0.36, 0.30, 0.20), 0.8)
cable_mat = flat("B_cable", (0.02, 0.02, 0.02), 0.7)
desk_mat = flat("B_desk_grey", (0.30, 0.31, 0.29), 0.6)


# ------------------------------------------------------------------ geometry builder
CORNERS = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
           (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


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


def place(key, name, x, y, z=0.0, rz=0.0, rx=0.0, ry=0.0):
    me, _, _ = MASTERS[key]
    o = link(bpy.data.objects.new(name, me))
    o.location = (x, y, z)
    o.rotation_euler = (rx, ry, rz)
    return o


def import_car(filename):
    """Import the existing bumper car GLB as a body-only master (the 4 m mast removed)."""
    objs = bkit.import_glb(f"{ROOT}/public/models/{filename}")
    meshes = [o for o in objs if o.type == "MESH"]
    car = bkit.join(meshes, "B_car_master") if len(meshes) > 1 else meshes[0]
    for o in objs:
        if o is not car and o.name in bpy.data.objects and o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    car.data.transform(car.matrix_world)
    car.matrix_world = Matrix.Identity(4)
    bm = bmesh.new()
    bm.from_mesh(car.data)
    faces = [f for f in bm.faces if min(v.co.z for v in f.verts) > 1.25]
    bmesh.ops.delete(bm, geom=faces, context="FACES")
    loose = [v for v in bm.verts if v.co.z > 1.25 and not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    zmin = min(v.co.z for v in bm.verts)
    bmesh.ops.translate(bm, verts=list(bm.verts), vec=(0.0, 0.0, -zmin))
    bm.to_mesh(car.data)
    bm.free()
    register("car", car)


import_car("bumper_car.glb")

# ------------------------------------------------------------------ shell: floor, ceiling, walls, south doorway, corridor
fl = Builder("B_shell_floor", [floor_mat])
fl.box(0, YC, -0.15, (X1 - X0) + 2 * WT, (Y1 - Y0) + 2 * WT, 0.3, floor_mat)
fl.finish(uv=3.0)

WALL_COLLIDERS = []


def wall_x(B, yc, mat, gate=None):
    x_lo, x_hi = X0 - WT, X1 + WT
    if gate is None:
        B.box((x_lo + x_hi) / 2, yc, H / 2, x_hi - x_lo, WT, H, mat)
        WALL_COLLIDERS.append(box_json((x_lo + x_hi) / 2, yc, H / 2, x_hi - x_lo, WT, H))
        return
    hw, gh = gate
    for a, b in ((x_lo, -hw), (hw, x_hi)):
        B.box((a + b) / 2, yc, H / 2, b - a, WT, H, mat)
        WALL_COLLIDERS.append(box_json((a + b) / 2, yc, H / 2, b - a, WT, H))
    B.box(0, yc, (gh + H) / 2, 2 * hw, WT, H - gh, mat)
    WALL_COLLIDERS.append(box_json(0, yc, (gh + H) / 2, 2 * hw, WT, H - gh))


def wall_y(B, xc, mat):
    y_lo, y_hi = Y0 - WT, Y1 + WT
    B.box(xc, (y_lo + y_hi) / 2, H / 2, WT, y_hi - y_lo, H, mat)
    WALL_COLLIDERS.append(box_json(xc, (y_lo + y_hi) / 2, H / 2, WT, y_hi - y_lo, H))


wl = Builder("B_shell_walls", [wall_mat])
wall_x(wl, Y0 - WT / 2, wall_mat, gate=(DOOR_W / 2, DOOR_H))
wall_x(wl, Y1 + WT / 2, wall_mat)
wall_y(wl, X0 - WT / 2, wall_mat)
wall_y(wl, X1 + WT / 2, wall_mat)
wl.finish(uv=2.5)
COLLIDERS += WALL_COLLIDERS

cl = Builder("B_ceil_slab", [ceil_mat])
cl.box(0, YC, H + 0.15, (X1 - X0) + 2 * WT, (Y1 - Y0) + 2 * WT, 0.3, ceil_mat)
cl.finish(uv=2.5)

gw = Builder("B_gate_wall", [wall_mat])
for a, b in ((X0 - WT, -GATE_HALF), (GATE_HALF, X1 + WT)):
    gw.box((a + b) / 2, GATE_Y, H / 2, b - a, WT, H, wall_mat)
    COLLIDERS.append(box_json((a + b) / 2, GATE_Y, H / 2, b - a, WT, H))
gw.box(0, GATE_Y, (SH_H + H) / 2, 2 * GATE_HALF, WT, H - SH_H, wall_mat)
COLLIDERS.append(box_json(0, GATE_Y, (SH_H + H) / 2, 2 * GATE_HALF, WT, H - SH_H))
gw.finish(uv=2.5)

df = Builder("B_doorframe", [steel_mat])
for s in (-1, 1):
    df.box(s * (DOOR_W / 2 + 0.03), Y0 - WT / 2, DOOR_H / 2, 0.08, WT + 0.06, DOOR_H, steel_mat)
df.box(0, Y0 - WT / 2, DOOR_H + 0.05, DOOR_W + 0.14, WT + 0.06, 0.1, steel_mat)
df.finish(uv=0.5, bevel=0.003)

cor = Builder("B_corridor", [floor_mat, wall_mat, steel_mat])
cor.box(0, (CORR_Y0 + CORR_Y1) / 2, -0.15, CORR_W + 2 * 0.3, CORR_Y1 - CORR_Y0, 0.3, floor_mat)
cor.box(0, (CORR_Y0 + CORR_Y1) / 2, CORR_H + 0.15, CORR_W + 2 * 0.3, CORR_Y1 - CORR_Y0, 0.3, steel_mat)
for s in (-1, 1):
    cor.box(s * (CORR_W / 2 + 0.15), (CORR_Y0 + CORR_Y1) / 2, CORR_H / 2, 0.3, CORR_Y1 - CORR_Y0, CORR_H, wall_mat)
cor.finish(uv=2.0)
for s in (-1, 1):
    COLLIDERS.append(box_json(s * (CORR_W / 2 + 0.15), (CORR_Y0 + CORR_Y1) / 2, CORR_H / 2, 0.3,
                              CORR_Y1 - CORR_Y0, CORR_H))

# rubber wall rails (cosmetic, no collider)
rb = Builder("B_bumper_rails", [rubber_mat])
rb.box(X0 + 0.2, YC, 0.12, 0.4, Y1 - Y0 - 2.0, 0.24, rubber_mat)
rb.box(X1 - 0.2, YC, 0.12, 0.4, Y1 - Y0 - 2.0, 0.24, rubber_mat)
rb.box(0, Y1 - 0.2, 0.12, X1 - X0 - 2.0, 0.4, 0.24, rubber_mat)
rb.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ rubber barrier ring with four gaps
rr = Builder("B_barrier_ring", [rubber_mat])


def ring_run_x(y, gap_x=0.0):
    for a, b in ((-RING_X, gap_x - RING_GAP), (gap_x + RING_GAP, RING_X)):
        rr.box((a + b) / 2, y, RING_H / 2, b - a, RING_T, RING_H, rubber_mat)
        COLLIDERS.append(box_json((a + b) / 2, y, RING_H / 2, b - a, RING_T, RING_H))


def ring_run_y(x, y0=RING_Y0, y1=RING_Y1, gap_y=82.0):
    for a, b in ((y0, gap_y - RING_GAP), (gap_y + RING_GAP, y1)):
        rr.box(x, (a + b) / 2, RING_H / 2, RING_T, b - a, RING_H, rubber_mat)
        COLLIDERS.append(box_json(x, (a + b) / 2, RING_H / 2, RING_T, b - a, RING_H))


ring_run_x(RING_Y0)
ring_run_x(RING_Y1)
ring_run_y(-RING_X)
ring_run_y(RING_X)
rr.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ painted lane markings and floor patches
lane = Builder("B_lane_paint", [paint_mat])


def strip_x(x0, x1, y, w=0.15):
    lane.quad([(x0, y - w / 2, 0.004), (x1, y - w / 2, 0.004), (x1, y + w / 2, 0.004), (x0, y + w / 2, 0.004)],
              paint_mat, (0, 0, 1))


def strip_y(x, y0, y1, w=0.15):
    lane.quad([(x - w / 2, y0, 0.004), (x + w / 2, y0, 0.004), (x + w / 2, y1, 0.004), (x - w / 2, y1, 0.004)],
              paint_mat, (0, 0, 1))


strip_x(-20.0, 20.0, 66.0)
strip_x(-20.0, 20.0, 88.0)
strip_y(-20.0, 66.0, 88.0)
strip_y(20.0, 66.0, 88.0)
for x in (-12.0, 12.0):                      # dashed lane lines
    for k in range(6):
        y0 = 67.0 + k * 4.0
        strip_y(x, y0, y0 + 2.0)
lane.finish(uv=None)

fp = Builder("B_floor_patches", [floor2_mat])
fp.box(-28.0, 50.0, 0.003, 22.0, 14.0, 0.006, floor2_mat)
fp.box(29.0, 112.0, 0.003, 18.0, 14.0, 0.006, floor2_mat)
fp.finish(uv=3.0)

# ------------------------------------------------------------------ sagging ceiling grid and hanging cables
SAG = 1.3


def sag_z(d, half):
    t = max(0.0, min(1.0, abs(d) / half))
    return H - 0.6 - SAG * (1 - t * t)


ceil_beams = Builder("B_ceil_beams", [steel_mat])
N_SEG = 8
for yb in range(50, 121, 10):
    for k in range(N_SEG):
        x0 = X0 + k * (X1 - X0) / N_SEG
        x1 = x0 + (X1 - X0) / N_SEG
        xc = (x0 + x1) / 2
        ceil_beams.box(xc, yb, sag_z(xc, (X1 - X0) / 2), (X1 - X0) / N_SEG + 0.05, 0.3, 0.5, steel_mat)
for xb in range(-30, 31, 10):
    for k in range(N_SEG):
        y0 = Y0 + k * (Y1 - Y0) / N_SEG
        y1 = y0 + (Y1 - Y0) / N_SEG
        yc_ = (y0 + y1) / 2
        ceil_beams.box(xb, yc_, sag_z(yc_ - YC, (Y1 - Y0) / 2) - 0.3, 0.3, (Y1 - Y0) / N_SEG + 0.05, 0.4, steel_mat)
ceil_beams.finish(uv=1.0, bevel=0.003)

LAMPS = [(x, y) for x in (-20.0, 0.0, 20.0) for y in (62.0, 82.0, 102.0)]
la = Builder("B_ceil_lamps", [lamp_mat, steel_mat])
for x, y in LAMPS:
    zl = sag_z(y - YC, (Y1 - Y0) / 2) - 0.7
    la.box(x, y, zl, 1.2, 0.35, 0.12, lamp_mat)
    la.cyl((x, y, zl + 0.06), (x, y, H - 0.3), 0.012, steel_mat, seg=5)
la.finish(uv=0.5)

cab = Builder("B_cables", [cable_mat])
CABLE_N = 18
for k in range(CABLE_N):
    x = random.uniform(-36, 36)
    y = random.uniform(46, 118)
    if abs(x - BX) < 3.0 and y > 104:          # keep the stair and the booth clear
        continue
    ztop = sag_z(y - YC, (Y1 - Y0) / 2) - 0.2
    zend = random.uniform(2.5, 6.0)
    p0 = (x, y, ztop)
    p1 = (x + random.uniform(-0.5, 0.5), y + random.uniform(-0.3, 0.3), (ztop + zend) / 2 - 0.4)
    p2 = (x + random.uniform(-0.8, 0.8), y + random.uniform(-0.6, 0.6), zend)
    cab.cyl(p0, p1, 0.025, cable_mat, seg=5)
    cab.cyl(p1, p2, 0.025, cable_mat, seg=5)
cab.finish(uv=None)

# ------------------------------------------------------------------ dead bumper cars: single cars on the floor
CAR_HALF_W, CAR_HALF_L, CAR_H = 0.81, 1.14, 1.02
car_spots = []
attempts = 0
while len(car_spots) < 14 and attempts < 4000:
    attempts += 1
    x = random.uniform(-36, 36)
    y = random.uniform(45, 119)
    if abs(x) < 5.0 and y < 56:                      # clear the south doorway
        continue
    if abs(x) < 7.5 and abs(y - GATE_Y) < 3.0:      # clear the shutter
        continue
    if x < -26.0 and y > 100.0:                      # stair and booth
        continue
    if x > 22.0 and 60.0 < y < 104.0 and random.random() < 0.5:
        continue
    if any((x - a) ** 2 + (y - b) ** 2 < 2.8 ** 2 for a, b in car_spots):
        continue
    car_spots.append((x, y))

CAR_LOG = []
for k, (x, y) in enumerate(car_spots):
    rz = random.uniform(0, 2 * math.pi)
    mode = "upright"
    if k % 4 == 1:
        mode = "side"
    elif k % 7 == 3:
        mode = "upside"
    if mode == "upright":
        place("car", f"B_car_{k}", x, y, 0.0, rz)
        COLLIDERS.append(box_json(x, y, CAR_H / 2, 2 * CAR_HALF_W, 2 * CAR_HALF_L, CAR_H, rz))
    elif mode == "side":          # lying on its side: height runs along x, width along z
        place("car", f"B_car_{k}", x, y, CAR_HALF_W, rz, ry=math.pi / 2)
        COLLIDERS.append(box_json(x, y, CAR_HALF_W, CAR_H, 2 * CAR_HALF_L, 2 * CAR_HALF_W, rz))
    else:                         # upside down
        place("car", f"B_car_{k}", x, y, CAR_H, rz, rx=math.pi)
        COLLIDERS.append(box_json(x, y, CAR_H / 2, 2 * CAR_HALF_W, 2 * CAR_HALF_L, CAR_H, rz))
    CAR_LOG.append(mode)

# ------------------------------------------------------------------ operator booth, raised, with stair and door
bo = Builder("B_booth", [steel_mat, wall_mat, glass_mat, rust_mat, desk_mat])
for dx in (-2.7, 2.7):
    for dy in (-2.7, 2.7):
        bo.box(BX + dx, BY + dy, PLAT_Z / 2, 0.22, 0.22, PLAT_Z, steel_mat)
        COLLIDERS.append(box_json(BX + dx, BY + dy, PLAT_Z / 2, 0.22, 0.22, PLAT_Z))
bo.box(BX, BY, PLAT_Z - 0.15, 6.2, 6.2, 0.3, rust_mat)                  # platform, top at PLAT_Z
bo.box(BX, BY + 0.7, 5.7, 6.2, 4.6, 0.25, rust_mat)                      # cabin roof
bo.box(BX - 2.9, BY + 0.7, 4.225, 0.2, 4.4, 2.65, wall_mat)              # west wall
bo.box(BX + 2.9, BY + 0.7, 4.225, 0.2, 4.4, 2.65, wall_mat)              # east wall
bo.box(BX, BY + 2.9, 4.225, 6.0, 0.2, 2.65, wall_mat)                    # north wall
bo.box(BX - 1.95, BY - 1.5, 4.225, 1.9, 0.2, 2.65, wall_mat)             # south wall, left of door
bo.box(BX + 1.95, BY - 1.5, 4.225, 1.9, 0.2, 2.65, wall_mat)             # south wall, right of door
bo.box(BX, BY - 1.5, 5.275, 2.0, 0.2, 0.55, wall_mat)                    # lintel over the door
bo.box(BX + 1.95, BY - 1.62, 4.3, 0.8, 0.04, 1.2, glass_mat)             # window, right of door
bo.box(BX + 0.6, BY + 0.9, PLAT_Z + 0.4, 1.2, 0.6, 0.8, desk_mat)        # desk
bo.box(BX + 0.6, BY + 0.9, PLAT_Z + 0.85, 0.9, 0.5, 0.05, desk_mat)       # desk top
bo.finish(uv=1.0, bevel=0.003)
COLLIDERS.append(box_json(BX + 0.6, BY + 0.9, PLAT_Z + 0.4, 1.2, 0.6, 0.8))
COLLIDERS.append(box_json(BX - 2.9, BY + 0.7, 4.225, 0.2, 4.4, 2.65))
COLLIDERS.append(box_json(BX + 2.9, BY + 0.7, 4.225, 0.2, 4.4, 2.65))
COLLIDERS.append(box_json(BX, BY + 2.9, 4.225, 6.0, 0.2, 2.65))
COLLIDERS.append(box_json(BX - 1.95, BY - 1.5, 4.225, 1.9, 0.2, 2.65))
COLLIDERS.append(box_json(BX + 1.95, BY - 1.5, 4.225, 1.9, 0.2, 2.65))

# claw magnet on the desk
mg = Builder("B_claw_magnet", [steel_mat, rust_mat])
mg.cyl((BX + 0.6, BY + 0.9, PLAT_Z + 0.9), (BX + 0.6, BY + 0.9, PLAT_Z + 1.08), 0.11, steel_mat, seg=10)
mg.box(BX + 0.6, BY + 0.9, PLAT_Z + 1.2, 0.3, 0.1, 0.22, rust_mat)
mg.finish(uv=1.0)

# stair from the arena floor up to the platform edge at y=110, centred on x=-33
ST_X, ST_Y0, ST_STEPS, ST_RUN = BX, 104.0, 12, 0.5
rise = PLAT_Z / ST_STEPS
sb = Builder("B_stair", [steel_mat, rust_mat])
for k in range(ST_STEPS):
    h = (k + 1) * rise
    y_c = ST_Y0 + (k + 0.5) * ST_RUN
    sb.box(ST_X, y_c, h / 2, 1.2, ST_RUN, h, steel_mat if k % 2 == 0 else rust_mat)
sb.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ iron shutter across the gap at y=92 and the crates
shl = Builder("B_shutter", [shutter_mat, hazard_mat, steel_mat])
shl.box(0, GATE_Y, SH_H / 2, 2 * GATE_HALF, 0.1, SH_H, shutter_mat)
for k in range(14):
    shl.box(0, GATE_Y - 0.07, 0.15 + k * 0.3, 2 * GATE_HALF, 0.05, 0.08, shutter_mat)
for s in (-1, 1):
    shl.box(s * (GATE_HALF + 0.12), GATE_Y, SH_H / 2, 0.22, 0.3, SH_H, steel_mat)
shl.box(0, GATE_Y - 0.10, SH_H - 0.1, 2 * GATE_HALF, 0.02, 0.3, hazard_mat)
shl.finish(uv=1.0, bevel=0.003)
COLLIDERS.append(box_json(0, GATE_Y, SH_H / 2, 2 * GATE_HALF, 0.1, SH_H))

crate_pos = [(-3.0, 84.0, 0.1), (3.5, 86.2, 0.3), (0.5, 88.8, 0.1)]
for i, (x, y, rz) in enumerate(crate_pos):
    cr = Builder(f"B_magnet_crate_{i + 1}", [iron_mat, rust_mat])
    cr.box(0, 0, 0.5, 1.2, 1.0, 1.0, iron_mat)
    for sx in (-0.56, 0.56):
        for sy in (-0.46, 0.46):
            cr.box(sx, sy, 0.5, 0.08, 0.08, 1.02, rust_mat)
    cr.box(0, -0.52, 0.5, 1.12, 0.05, 0.12, rust_mat)
    cr.box(0, 0.52, 0.5, 1.12, 0.05, 0.12, rust_mat)
    obj = cr.finish(uv=1.0, bevel=0.004)
    obj.location = (x, y, 0.0)
    obj.rotation_euler = (0.0, 0.0, rz)
    COLLIDERS.append(box_json(x, y, 0.5, 1.2, 1.0, 1.0, rz))
    MARKERS[f"magnet_crate_{i + 1}"] = [x, y, 0.0]

# ------------------------------------------------------------------ floor: puddles, oil stains, debris
pu = Builder("B_puddles", [puddle_mat, oil_mat, stain_mat])
PUDDLES = [(-22.0, 46.0, 2.0), (16.0, 50.0, 1.8), (-6.0, 58.0, 1.4), (10.0, 72.0, 2.2),
           (-18.0, 84.0, 1.6), (22.0, 88.0, 1.5), (-10.0, 104.0, 2.0), (18.0, 116.0, 1.7),
           (-24.0, 118.0, 1.4), (6.0, 110.0, 1.3), (-30.0, 74.0, 1.6), (30.0, 70.0, 1.2)]
STAINS = [(rng.uniform(-36, 36), rng.uniform(46, 120), rng.uniform(0.8, 2.4)) for _ in range(32)]
for cx, cy, r in PUDDLES + STAINS:
    pts = []
    for k in range(10):
        t = 2 * math.pi * k / 10
        rr_ = r * random.uniform(0.6, 1.0)
        pts.append((cx + rr_ * math.cos(t), cy + rr_ * math.sin(t), 0.004))
    if (cx, cy, r) in PUDDLES:
        pu.poly(pts, puddle_mat if rng.random() < 0.7 else oil_mat)
    else:
        pu.poly(pts, stain_mat if rng.random() < 0.6 else oil_mat)
pu.finish(uv=None)

db = Builder("B_debris", [steel_mat, rust_mat])
for k in range(10):
    x = random.uniform(-32, 32)
    y = random.uniform(48, 120)
    if abs(y - GATE_Y) < 3 or (abs(x) < 3.5 and y < 60):
        continue
    db.box(x, y, 0.07, random.uniform(0.3, 0.8), random.uniform(0.3, 0.8), 0.14, rust_mat,
           rz=random.uniform(0, 1.5))
db.finish(uv=1.0, bevel=0.003)

st = Builder("B_wall_stains", [stain_mat])
for k in range(10):
    side = k % 4
    w = random.uniform(0.6, 1.5)
    top = random.uniform(7.0, 11.4)
    h = random.uniform(2.0, 4.5)
    if side == 0:
        c = random.uniform(50, 118)
        st.quad([(X0 + 0.01, c - w / 2, top), (X0 + 0.01, c + w / 2, top),
                 (X0 + 0.01, c + w / 2, top - h), (X0 + 0.01, c - w / 2, top - h)], stain_mat, (1, 0, 0))
    elif side == 1:
        c = random.uniform(50, 118)
        st.quad([(X1 - 0.01, c - w / 2, top), (X1 - 0.01, c + w / 2, top),
                 (X1 - 0.01, c + w / 2, top - h), (X1 - 0.01, c - w / 2, top - h)], stain_mat, (-1, 0, 0))
    elif side == 2:
        c = random.uniform(-30, 30)
        st.quad([(c - w / 2, Y1 - 0.01, top), (c + w / 2, Y1 - 0.01, top),
                 (c + w / 2, Y1 - 0.01, top - h), (c - w / 2, Y1 - 0.01, top - h)], stain_mat, (0, -1, 0))
    else:
        c = random.uniform(-30, 30)
        st.quad([(c - w / 2, GATE_Y - WT / 2 - 0.01, top), (c + w / 2, GATE_Y - WT / 2 - 0.01, top),
                 (c + w / 2, GATE_Y - WT / 2 - 0.01, top - h), (c - w / 2, GATE_Y - WT / 2 - 0.01, top - h)],
                stain_mat, (0, -1, 0))
st.finish(uv=None)

# relic boxes on the floor
RELIC_POS = {"relic_3": (-26.0, 62.0), "relic_4": (-12.0, 108.0)}
for key, (x, y) in RELIC_POS.items():
    rb_obj = Builder(f"B_{key}_box", [relic_mat])
    rb_obj.box(0, 0, 0.12, 0.4, 0.3, 0.24, relic_mat)
    o = rb_obj.finish(uv=None, master=True)
    o.location = (x, y, 0.0)

# ------------------------------------------------------------------ signs
sg = Builder("B_signs", [sign_mat])
sg.box(X0 + 0.04, 70.0, 2.3, 0.05, 6.0, 1.2, sign_mat)
sg.box(0.0, GATE_Y - WT / 2 - 0.03, 5.6, 4.0, 0.05, 0.7, sign_mat)
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


text_obj("BUMPER CARS 1996", X0 + 0.1, 70.0, 2.3, (math.pi / 2, 0, math.pi / 2), 0.2, "B_text_bumper_cars")
text_obj("KEEP OUT", 0.0, GATE_Y - WT / 2 - 0.06, 5.6, (math.pi / 2, 0, 0), 0.25, "B_text_keep_out")

# ------------------------------------------------------------------ markers (Blender coordinates)
MARKERS.update({
    "claw_magnet": [BX + 0.6, BY + 0.9, PLAT_Z + 0.9],
    "magnet_gate_1": [0.0, GATE_Y, SH_H / 2],
    "relic_3": [RELIC_POS["relic_3"][0], RELIC_POS["relic_3"][1], 0.0],
    "relic_4": [RELIC_POS["relic_4"][0], RELIC_POS["relic_4"][1], 0.0],
    "ticket_patrol_1": [-22.0, 50.0, 0.0],
    "ticket_patrol_2": [22.0, 52.0, 0.0],
    "ticket_patrol_3": [-34.0, 78.0, 0.0],
    "ticket_patrol_4": [34.0, 80.0, 0.0],
    "ticket_patrol_5": [-12.0, 102.0, 0.0],
    "ticket_patrol_6": [14.0, 108.0, 0.0],
})

# ------------------------------------------------------------------ lights (exported): mostly dead, a few alive
ALIVE = {(-20.0, 62.0): ("#ffb070", True), (20.0, 102.0): ("#d8e4f0", False),
         (0.0, 82.0): ("#d8e4f0", True), (-20.0, 102.0): ("#ffb070", False)}
for (x, y), (color, flick) in ALIVE.items():
    zl = sag_z(y - YC, (Y1 - Y0) / 2) - 0.8
    LIGHTS.append({"pos": [x, y, round(zl, 3)], "color": color, "intensity": 0.8, "range": 12,
                   "flicker": flick})

# ------------------------------------------------------------------ preview lighting (not exported)
world = bpy.data.worlds.new("B_preview_world")
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
    zl = sag_z(y - YC, (Y1 - Y0) / 2) - 0.8
    if (x, y) in ALIVE:
        color = ALIVE[(x, y)][0]
        preview_light(f"PREVIEW_light_{i}", (x, y, zl), 1100.0,
                      (0.80, 0.90, 1.0) if color == "#d8e4f0" else (1.0, 0.62, 0.32))
    else:
        preview_light(f"PREVIEW_light_{i}", (x, y, zl), 60.0, (0.9, 0.9, 1.0))
preview_light("PREVIEW_booth", (BX, BY, PLAT_Z + 2.0), 300.0, (0.9, 0.9, 1.0))

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
        if o.name.startswith("B_ceil"):
            o.hide_render = flag


def render_previews():
    os.makedirs(os.path.dirname(EYE_PNG), exist_ok=True)
    views = {
        "south_door": ((0.0, 50.0, EYE_Z), (0.0, CORR_Y0, EYE_Z)),
        "shutter": ((0.0, 78.0, EYE_Z), (0.0, GATE_Y, 2.0)),
        "booth": ((-33.0, 99.0, EYE_Z), (BX, BY, 3.2)),
        "ring": ((-18.0, 58.0, EYE_Z), (-6.0, 74.0, 0.5)),
    }
    paths = {}
    for key, (pos, tgt) in views.items():
        cam = make_cam(f"cam_{key}", pos, tgt)
        paths[key] = render_to(cam, f"{PREVIEW_DIR}/eye_{key}.png", EYE_RES)
    write_sheet(paths["south_door"], paths["shutter"], paths["booth"], paths["ring"], EYE_PNG)

    hide_ceiling(True)
    cam = make_cam("cam_top", (0.0, YC, 60.0), (0.0, YC, 0.0), ortho=92.0)
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
    print("ZB_REPORT shell_tris", shell, "instanced_master_tris", shared_tris,
          "instances", sum(1 for o in objs if o.data.users > 1))
    print("ZB_REPORT objects", len(objs), "materials", len(mats))
    print("ZB_REPORT colliders", len(COLLIDERS), "lights", len(LIGHTS), "markers", len(MARKERS),
          "cars", CAR_LOG)


for _im in bpy.data.images:
    if _im.size[0] > 512 or _im.size[1] > 512:
        _im.scale(min(512, _im.size[0]), min(512, _im.size[1]))

render_previews()
objs = export_objects()
report(objs)

os.makedirs(os.path.dirname(GLB), exist_ok=True)
bkit.export_glb(GLB, objs, image_format="JPEG")
print("ZB_REPORT glb_bytes", os.path.getsize(GLB))

data = {"zone": "bumper", "colliders": COLLIDERS, "lights": LIGHTS, "markers": MARKERS}
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
print("ZB_DONE")
