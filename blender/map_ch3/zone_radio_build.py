"""Chapter 3, zone radio: broadcast station (lobby, studio, control room, record library,
transmitter hall, three cracked hidden rooms).

Run from /Users/alex/恐怖遊戲2 (scratch out dir is only a runner argument):
    python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py \
        blender/map_ch3/zone_radio_build.py <scratch_dir>

Coordinates follow blender/map_ch3/BRIEF.md: interior box x -102..-42, y -30..30,
ceiling 8. Floor top at z=0. Walls 0.3 m, built outward from the interior box.
East doorway at x=-42, y -1.5..1.5, 3 m high, joined to the hub by a 12 m corridor
(x -42..-30, y +-1.5, 3.4 m high) that ends flush against the hub wall.
"""
import sys, os, math, json, random

import numpy as np

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_radio"
GLB = f"{ROOT}/public/models/ch3/{NAME}.glb"
JSON_OUT = f"{ROOT}/public/models/ch3/{NAME}.json"
BLEND = f"{ROOT}/blender/bake/map_ch3/{NAME}.blend"
EYE_PNG = f"{ROOT}/renders/ch3_{NAME}_eye.png"
TOP_PNG = f"{ROOT}/renders/ch3_{NAME}_top.png"
CACHE = os.path.expanduser("~/.cache/blender-modeling/ch3_radio")
PREVIEW_DIR = f"{CACHE}/previews"
SAMPLES = 20
EYE_RES = (640, 360)
TOP_RES = 800
EYE_Z = 1.6
QUICK = os.environ.get("ZR_QUICK") == "1"

bkit.reset_scene()
SCENE = bpy.context.scene
COLL = SCENE.collection
random.seed(20261108)
rng_np = np.random.default_rng(11)
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
    # acoustic foam: grey-green pyramids
    tri = np.abs(((xx * 12) % 1.0) - 0.5) + np.abs(((yy * 12) % 1.0) - 0.5)
    foam = np.array([0.46, 0.52, 0.42])[None, None, :] * (0.72 + 0.3 * tri[..., None])
    foam *= (1 - 0.10 * rng_np.random((256, 256)))[..., None]
    # cracked plaster: beige with dark hairline cracks that wrap
    base = np.array([0.66, 0.62, 0.54])[None, None, :] * (1 + 0.06 * rng_np.normal(0, 1, (256, 256)))[..., None]
    mask = np.zeros((256, 256), dtype=bool)
    for _ in range(7):
        x, y = rng_np.random() * 256, rng_np.random() * 256
        ang = rng_np.random() * 6.28
        for _s in range(170):
            ang += rng_np.normal(0, 0.28)
            x += math.cos(ang)
            y += math.sin(ang)
            xi, yi = int(x) % 256, int(y) % 256
            mask[yi, xi] = True
            mask[yi, (xi + 1) % 256] = True
    crack = base.copy()
    crack[mask] *= 0.22
    return save_png("foam", foam), save_png("plaster_crack", crack)


foam_png, crack_png = generated_textures()

floor_mat = pbr("R_floor_concrete", "concrete_floor_worn_001")
wall_mat = pbr("R_wall_paint", "peeling_painted_wall", tint=(0.80, 0.76, 0.68))
ceil_mat = pbr("R_ceiling_plaster", "plaster_grey_04", tint=(0.84, 0.84, 0.80))
steel_mat = pbr("R_steel_rusty", "rusty_metal_02")
plate_mat = pbr("R_plate", "metal_plate")
wood_mat = pbr("R_wood", "wood_planks_grey")
foam_mat = image_mat("R_foam", foam_png, 0.95)
crack_mat = image_mat("R_crack_plaster", crack_png, 0.85)
dark_mat = flat("R_black_rubber", (0.03, 0.03, 0.03), 0.7)
rack_mat = flat("R_rack_dark", (0.10, 0.10, 0.09), 0.55)
dial_mat = flat("R_dial_panel", (0.62, 0.58, 0.46), 0.45)
sign_mat = flat("R_onair_sign", (0.40, 0.06, 0.05), 0.5)
reel_mat = flat("R_reel_metal", (0.30, 0.27, 0.24), 0.4)
tape_mat = flat("R_tape_brown", (0.16, 0.10, 0.06), 0.8)
glass_mat = flat("R_tube_glass", (0.55, 0.60, 0.58), 0.12)
puddle_mat = flat("R_puddle", (0.012, 0.016, 0.02), 0.03)
stain_mat = flat("R_stain", (0.06, 0.045, 0.03), 0.5)
sleeves = [flat(f"R_sleeve_{i}", c, 0.7) for i, c in enumerate([
    (0.55, 0.14, 0.10), (0.18, 0.28, 0.42), (0.70, 0.62, 0.36), (0.20, 0.36, 0.22), (0.30, 0.22, 0.34)])]


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
    """Wall lying along x (axis 'x', at y=fixed) or along y (axis 'y', at x=fixed).
    openings: list of (lo, hi) gaps; a lintel fills each gap from `top` up to z1."""
    pieces, pos = [], a0
    for lo, hi in sorted(openings):
        pieces.append((pos, lo, z0, z1))
        pieces.append((lo, hi, top, z1))  # lintel over the opening
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


# ------------------------------------------------------------------ props (imported, shared mesh)
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


def import_prop(key, filename):
    o = bkit.import_glb(f"{ROOT}/public/models/{filename}")[0]
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    register(key, o)


def prop(key, name, x, y, z=0.0, rz=0.0, collide=True):
    me, lo, hi = MASTERS[key]
    o = link(bpy.data.objects.new(name, me))
    o.location = (x, y, z)
    o.rotation_euler = (0.0, 0.0, rz)
    if collide:
        c = (lo + hi) / 2
        w = Matrix.Rotation(rz, 3, "Z") @ c
        COLLIDERS.append(box_json(x + w.x, y + w.y, z + w.z, hi.x - lo.x, hi.y - lo.y, hi.z - lo.z, rz))
    return o


import_prop("receiver", "receiver.glb")
import_prop("cassette", "cassette.glb")

# ------------------------------------------------------------------ shell: floors, outer walls, ceiling
WALL_H = 8.0
fl = Builder("RAD_shell_floor", [floor_mat, puddle_mat, stain_mat])
fl.box(-72.0, 0.0, -0.15, 60.6, 60.6, 0.3, floor_mat)
fl.box(-63.0, 9.0, 0.0, 0.2, 0.2, 0.002, puddle_mat)  # small pool, flattened decal
fl.box(-95.0, -12.0, 0.0, 2.2, 1.6, 0.002, puddle_mat)
fl.box(-53.0, 18.0, 0.0, 1.6, 1.2, 0.002, stain_mat)
fl.box(-86.0, 22.0, 0.0, 1.0, 0.8, 0.002, stain_mat)
fl.finish(uv=3.0)

# corridor to the hub: x -42..-30, 3 m wide, 3.4 m high (floor and walls are this zone's)
cr = Builder("RAD_shell_corridor", [floor_mat, wall_mat])
cr.box(-36.0, 0.0, -0.15, 12.0, 3.0, 0.3, floor_mat)
cr_wall_y = [1.65, -1.65]
for yw in cr_wall_y:
    solid(cr, wall_mat, -36.0, yw, 1.7, 12.0, 0.3, 3.4)
cr.finish(uv=2.0)

wl = Builder("RAD_shell_walls", [wall_mat])
wall(wl, wall_mat, "y", -102.15, -30.3, 30.3, 0.0, WALL_H, 0.3)            # west
wall(wl, wall_mat, "x", 30.15, -102.3, -41.7, 0.0, WALL_H, 0.3)            # north
wall(wl, wall_mat, "x", -30.15, -102.3, -41.7, 0.0, WALL_H, 0.3)           # south
wall(wl, wall_mat, "y", -41.85, -30.3, 30.3, 0.0, WALL_H, 0.3,             # east, with the hub doorway
     openings=[(-1.5, 1.5)], top=3.0)
wl.finish(uv=2.5)

ce = Builder("RAD_ceil_slab", [ceil_mat])
ce.box(-72.0, 0.0, WALL_H + 0.15, 60.6, 60.6, 0.3, ceil_mat)
ce.box(-36.0, 0.0, 3.55, 12.0, 3.6, 0.3, ceil_mat)
ce.finish(uv=2.5)

# ceiling beams, ducts and dead fixtures (ceiling objects are hidden in the top view)
cbm = Builder("RAD_ceil_beams", [steel_mat])
for xb in range(-100, -40, 8):
    cbm.box(xb + 0.5, 0.0, 7.6, 0.3, 60.0, 0.5, steel_mat)
cbm.finish(uv=1.0, bevel=0.004)

dct = Builder("RAD_ceil_ducts", [steel_mat])
dct.box(-91.0, -4.0, 7.1, 1.0, 50.0, 0.6, steel_mat)
dct.box(-57.0, 0.0, 7.1, 0.8, 58.0, 0.5, steel_mat)
dct.finish(uv=1.0, bevel=0.004)

fix = Builder("RAD_ceil_fixtures", [plate_mat])
for xf, yf in [(-98, -20), (-98, 4), (-86, 12), (-74, -4), (-62, 18), (-46, -10), (-52, 25), (-95, 22)]:
    fix.box(xf, yf, 7.9, 1.2, 0.3, 0.12, plate_mat)
fix.finish(uv=1.0)

# ------------------------------------------------------------------ interior partitions (0.2 m)
pt = Builder("RAD_partitions", [wall_mat])
wall(pt, wall_mat, "y", -80.0, -30.0, 30.0, 0.0, WALL_H, 0.2, openings=[(6.0, 8.0)])       # P1 hall | library
wall(pt, wall_mat, "x", 0.0, -80.0, -58.0, 0.0, WALL_H, 0.2, openings=[(-72.0, -68.0)])    # P2 control | library
wall(pt, wall_mat, "y", -62.0, -30.0, 0.0, 0.0, WALL_H, 0.2, openings=[(-12.0, -10.0)])    # P3 control | studio
wall(pt, wall_mat, "x", -14.0, -62.0, -42.0, 0.0, WALL_H, 0.2, openings=[(-56.0, -53.0)])  # P4 studio | lobby
pt.finish(uv=2.0)

# hidden rooms. Each is closed except a cracked wall that only the horn claw breaks.
hr = Builder("RAD_hidden_rooms", [wall_mat])
# H1 tape vault, north-west hall corner (x -102..-93, y 14..28); crack_1 on its east wall
wall(hr, wall_mat, "x", 14.0, -102.3, -92.9, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "x", 28.0, -102.3, -92.9, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "y", -93.0, 14.0, 18.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "y", -93.0, 22.0, 28.0, 0.0, WALL_H, 0.2)
# H2 relic cache, studio south-east corner (x -51..-42, y -28..-21); crack_2 on its west wall
wall(hr, wall_mat, "x", -21.0, -51.1, -42.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "x", -28.0, -51.1, -42.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "y", -51.0, -28.0, -26.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "y", -51.0, -23.0, -21.0, 0.0, WALL_H, 0.2)
# H3 store room, library north-east corner (x -49..-42, y 20..27); crack_3 on its west wall
wall(hr, wall_mat, "x", 20.0, -49.1, -42.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "x", 27.0, -49.1, -42.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "y", -49.0, 20.0, 22.0, 0.0, WALL_H, 0.2)
wall(hr, wall_mat, "y", -49.0, 25.0, 27.0, 0.0, WALL_H, 0.2)
hr.finish(uv=2.0)

# cracked walls: separate objects so the game can remove them when the horn breaks them
for key, x, y0, y1, axis in [
        ("crack_1", -93.0, 18.0, 22.0, "y"),
        ("crack_2", -51.0, -26.0, -23.0, "y"),
        ("crack_3", -49.0, 22.0, 25.0, "y")]:
    cb = Builder(f"RAD_{key}", [crack_mat])
    wall(cb, crack_mat, axis, x, y0, y1, 0.0, WALL_H, 0.2)
    cb.finish(uv=1.5)

# ------------------------------------------------------------------ studio foam and sound booth
fo = Builder("RAD_studio_foam", [foam_mat])
solid(fo, foam_mat, -52.0, -29.85, 1.3, 18.0, 0.12, 2.2)                  # south wall
solid(fo, foam_mat, -61.85, -21.6, 1.3, 0.12, 15.0, 2.2)                  # west wall (P3 side)
solid(fo, foam_mat, -56.0, -18.0, 1.3, 0.12, 6.0, 2.2)                    # baffle beside P4 door
solid(fo, foam_mat, -47.0, -15.85, 1.3, 9.0, 0.12, 2.2)                   # north wall of studio
fo.finish(uv=1.0)

# ------------------------------------------------------------------ library shelving (aisles between rows)
SHELF_LIB = Builder("RAD_shelves", [steel_mat, wood_mat] + sleeves)
def shelf_unit(cx, y0, y1):
    L, cy = y1 - y0, (y0 + y1) / 2
    SHELF_LIB.box(cx, cy, 1.15, 0.03, L, 2.3, steel_mat)               # back panel
    for zb in (0.05, 0.75, 1.45):
        SHELF_LIB.box(cx + 0.2, cy, zb, 0.42, L, 0.04, steel_mat)       # boards
    for zb in (0.75, 1.45):
        y = y0 + 0.15
        while y < y1 - 0.1:
            if random.random() < 0.7:
                w = random.uniform(0.11, 0.14)
                SHELF_LIB.box(cx + 0.25 + random.uniform(-0.03, 0.02), y + w / 2, zb + 0.16,
                              0.03, w, 0.3, random.choice(sleeves))
                y += w + random.uniform(0.01, 0.03)
            else:
                y += 0.2
    COLLIDERS.append(box_json(cx + 0.2, cy, 1.15, 0.42, L, 2.3))

for cx_, spans in [(-68.0, [(3.0, 8.5), (11.0, 16.5), (19.0, 24.5)]),
                   (-56.0, [(3.0, 8.5), (11.0, 16.5)])]:
    for y0, y1 in spans:
        shelf_unit(cx_, y0, y1)
# record crates on the floor between rows (cover)
for xc, yc in [(-62.0, 26.0), (-74.0, 26.0), (-44.0, 12.0)]:
    solid(SHELF_LIB, wood_mat, xc, yc, 0.4, 1.2, 0.9, 0.8, rz=random.uniform(-0.2, 0.2))
SHELF_LIB.finish(uv=1.0)

# ------------------------------------------------------------------ studio furniture
fu = Builder("RAD_studio_furniture", [wood_mat, steel_mat, dark_mat])
solid(fu, wood_mat, -47.0, -18.5, 0.72, 1.6, 0.8, 0.06)                   # table top
for xl, yl in [(-47.7, -18.1), (-46.3, -18.1), (-47.7, -18.9), (-46.3, -18.9)]:
    fu.box(xl, yl, 0.35, 0.05, 0.05, 0.7, steel_mat)
for xs, ys in [(-54.0, -22.0), (-57.0, -18.0)]:                           # two mic stands
    fu.cyl((xs, ys, 0.0), (xs, ys, 1.3), 0.02, steel_mat, seg=6)
    fu.box(xs, ys, 1.35, 0.14, 0.09, 0.2, dark_mat)                       # mic capsule
    fu.box(xs, ys, 0.02, 0.3, 0.3, 0.03, steel_mat)
for xc, yc in [(-58.5, -25.0), (-55.0, -27.0)]:                            # chairs (outside H2)
    solid(fu, wood_mat, xc, yc, 0.45, 0.5, 0.5, 0.05, collide=False)
    fu.box(xc, yc - 0.22, 0.9, 0.5, 0.05, 0.5, wood_mat)
fu.finish(uv=1.0, bevel=0.003)

# on-air sign above the studio door (dead; a flickering lamp is the only power left)
oa = Builder("RAD_onair_sign", [sign_mat, dark_mat])
oa.box(-54.5, -13.85, 2.9, 2.2, 0.08, 0.6, sign_mat)
oa.box(-54.5, -13.8, 2.9, 1.6, 0.02, 0.2, dark_mat)
oa.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ control room: mixing desk and tape gear
cr_ = Builder("RAD_control", [wood_mat, rack_mat, dial_mat, reel_mat, dark_mat, tape_mat, sleeves[1], sleeves[2]])
solid(cr_, wood_mat, -72.0, -20.0, 0.9, 4.0, 0.9, 0.9)                    # desk body (top at 1.35)
cr_.box(-72.0, -19.4, 1.4, 3.8, 0.4, 0.04, dial_mat)                       # fader panel
for i in range(12):
    cr_.box(-73.9 + i * 0.32, -19.4, 1.47, 0.04, 0.06, 0.12, dark_mat)     # faders
for xr, yr in [(-78.7, -14.0), (-78.7, -24.5)]:                             # rack units against P1
    solid(cr_, rack_mat, xr, yr, 1.0, 0.5, 2.0, 2.0)
    for zb in (0.7, 1.3, 1.9):
        cr_.box(xr + 0.27, yr, zb, 0.05, 1.8, 0.04, dark_mat)
# reel-to-reel recorders on a low bench
solid(cr_, rack_mat, -67.0, -26.0, 0.45, 1.5, 0.7, 0.9)
for xr in (-68.0, -66.0):
    cr_.box(xr, -25.6, 1.0, 0.5, 0.45, 0.4, rack_mat)
    cr_.cyl((xr, -25.36, 1.05), (xr, -25.33, 1.05), 0.2, reel_mat, seg=12)
    cr_.cyl((xr, -25.36, 1.05), (xr, -25.33, 1.05), 0.12, tape_mat, seg=12)
    cr_.cyl((xr, -25.36, 0.97), (xr, -25.33, 0.97), 0.02, dark_mat, seg=6)
# bare tape stacks on the floor and tape rack corner
for xs_, ys_ in [(-77.0, -6.0), (-75.8, -6.2), (-76.6, -4.5)]:
    solid(cr_, sleeves[2], xs_, ys_, 0.1, 0.4, 0.4, 0.2, rz=random.uniform(-0.3, 0.3))
cr_.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ transmitter hall: cabinets, tubes, cables
tx = Builder("RAD_transmitter", [rack_mat, dial_mat, glass_mat, dark_mat, steel_mat])
for xc in (-98.0, -88.0):
    for yc in (-24.0, -17.0, -10.0, -3.0):
        solid(tx, rack_mat, xc, yc, 1.3, 1.2, 0.8, 2.6)
        tx.box(xc + 0.61, yc, 1.8, 0.02, 0.6, 0.8, dial_mat)                # dial panel face
        tx.box(xc + 0.61, yc, 0.6, 0.02, 0.5, 0.3, dark_mat)
# tube bench in the middle of the hall, with glass tubes
solid(tx, steel_mat, -84.0, 0.0, 0.85, 0.8, 4.0, 0.9)
for i in range(8):
    tx.cyl((-84.0 - 0.1, -1.8 + i * 0.5, 1.4), (-84.0 - 0.1, -1.8 + i * 0.5, 1.9), 0.06, glass_mat, seg=8)
# cables from ceiling down to the cabinets
for xc, yc in [(-98.0, -17.0), (-88.0, -10.0), (-84.0, 0.0), (-98.0, -3.0), (-88.0, -24.0)]:
    tx.cyl((xc, yc, 7.2), (xc, yc, 2.2 + random.uniform(0.0, 0.8)), 0.04, dark_mat, seg=6)
tx.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ hidden room contents
hc = Builder("RAD_hidden_contents", [wood_mat, rack_mat, reel_mat, tape_mat, sleeves[3]])
# H1: table with reels and a stack of tape boxes
solid(hc, wood_mat, -97.0, 21.0, 0.75, 1.2, 0.7, 0.05)
for xr in (-97.5, -96.5):
    hc.cyl((xr, 21.0, 0.8), (xr, 21.0, 0.85), 0.16, reel_mat, seg=10)
    hc.cyl((xr, 21.0, 0.85), (xr, 21.0, 0.9), 0.07, tape_mat, seg=8)
solid(hc, sleeves[3], -97.4, 20.2, 0.9, 0.3, 0.2, 0.25, rz=0.2)
for xs_ in (-99.0, -94.8):
    solid(hc, rack_mat, xs_, 15.5, 1.1, 0.4, 1.5, 2.2)
# H2: relic cabinet
solid(hc, rack_mat, -45.5, -24.5, 0.95, 0.6, 1.0, 1.9)
hc.box(-45.2, -24.5, 1.95, 0.02, 0.6, 0.4, dark_mat)
# H3: crates and a tipped tape rack
for xc, yc in [(-46.0, 23.0), (-44.0, 25.5)]:
    solid(hc, wood_mat, xc, yc, 0.4, 1.0, 0.8, 0.8, rz=random.uniform(-0.2, 0.2))
solid(hc, rack_mat, -47.5, 21.4, 0.25, 1.4, 0.4, 0.5, rz=0.3)
hc.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ lobby and library scatter (cover, junk)
lb = Builder("RAD_lobby", [wood_mat, rack_mat, sleeves[4]])
solid(lb, wood_mat, -50.5, -6.0, 0.45, 1.4, 0.7, 0.9)                     # reception counter
solid(lb, rack_mat, -44.0, 4.0, 0.9, 0.5, 1.6, 1.8)                       # tall rack by the entrance
solid(lb, sleeves[4], -60.0, 9.5, 0.2, 0.6, 0.6, 0.4)                     # tape crates
solid(lb, sleeves[4], -60.0, 10.3, 0.2, 0.6, 0.6, 0.4, rz=0.2)
lb.finish(uv=1.0, bevel=0.003)

# ------------------------------------------------------------------ props (imported)
prop("receiver", "RAD_prop_receiver_1", -95.5, -6.3, rz=0.0)
prop("receiver", "RAD_prop_receiver_2", -93.3, -6.3, rz=0.0)
prop("receiver", "RAD_prop_receiver_3", -95.0, 7.0, rz=math.pi / 2)
for i, (x, y) in enumerate([(-74.6, -19.4), (-73.0, -19.2), (-71.0, -19.6)]):
    prop("cassette", f"RAD_prop_cassette_{i}", x, y, z=1.35, rz=random.uniform(-0.3, 0.3), collide=False)

# ------------------------------------------------------------------ markers (Blender coordinates, ground level)
MARKERS = {
    "spawn": [-40.0, 0.0, 0.0],
    "claw_horn": [-72.0, -20.0, 1.35],
    "crack_1": [-91.0, 20.0, 0.0],
    "crack_2": [-53.0, -24.5, 0.0],
    "crack_3": [-51.0, 23.5, 0.0],
    "tape_reveal": [-97.0, 21.0, 0.85],
    "relic_8": [-45.0, -24.5, 0.0],
    "ticket_patrol_1": [-62.0, 12.0, 0.0],
    "ticket_patrol_2": [-93.0, -20.0, 0.0],
    "ticket_patrol_3": [-56.0, -6.0, 0.0],
    "ticket_patrol_4": [-66.0, -20.0, 0.0],
}

# ------------------------------------------------------------------ lights (dead ones have no entry)
LIGHTS = [
    {"pos": [-36.0, 0.0, 2.8], "color": "#d8e4f0", "intensity": 0.3, "range": 6, "flicker": True},
    {"pos": [-50.0, -7.0, 7.2], "color": "#d8e4f0", "intensity": 0.8, "range": 14, "flicker": False},
    {"pos": [-54.5, -15.5, 6.6], "color": "#ff5050", "intensity": 0.6, "range": 6, "flicker": True},
    {"pos": [-50.0, -22.0, 7.2], "color": "#d8e4f0", "intensity": 0.2, "range": 9, "flicker": True},
    {"pos": [-71.0, -14.0, 7.0], "color": "#ffb070", "intensity": 0.7, "range": 9, "flicker": True},
    {"pos": [-62.0, 14.0, 7.2], "color": "#d8e4f0", "intensity": 0.5, "range": 12, "flicker": False},
    {"pos": [-46.0, 20.0, 7.2], "color": "#ffb070", "intensity": 0.3, "range": 8, "flicker": True},
    {"pos": [-92.0, -14.0, 7.2], "color": "#d8e4f0", "intensity": 0.4, "range": 14, "flicker": True},
    {"pos": [-90.0, 16.0, 7.2], "color": "#ffb070", "intensity": 0.4, "range": 12, "flicker": False},
    {"pos": [-97.0, 21.0, 7.0], "color": "#ffb070", "intensity": 0.5, "range": 7, "flicker": True},
    {"pos": [-46.0, -24.0, 7.0], "color": "#ff8a50", "intensity": 0.2, "range": 6, "flicker": True},
]


# ------------------------------------------------------------------ preview lighting (not exported)
world = bpy.data.worlds.new("R_preview_world")
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
    ld.energy = 900.0 * l["intensity"]
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
        "east_door": ((-36.0, 0.0, EYE_Z), (-48.0, -1.0, EYE_Z)),
        "hall_door": ((-76.0, 7.0, EYE_Z), (-88.0, 7.0, EYE_Z)),
        "crack_1": ((-89.5, 20.0, EYE_Z), (-95.0, 20.0, EYE_Z)),
        "studio": ((-59.0, -10.0, EYE_Z), (-48.0, -22.0, 1.4)),
    }
    paths = {}
    for key, (pos, tgt) in views.items():
        cam = make_cam(f"cam_{key}", pos, tgt)
        paths[key] = render_to(cam, f"{PREVIEW_DIR}/eye_{key}.png", EYE_RES)
    write_sheet(paths["east_door"], paths["hall_door"], paths["crack_1"], paths["studio"], EYE_PNG)
    ceil_objs = [o for o in bpy.data.objects if o.name.startswith("RAD_ceil")]
    for o in ceil_objs:
        o.hide_render = True
    cam = make_cam("cam_top", (-72.0, 0.0, 70.0), (-72.0, 0.0, 0.0), ortho=66.0)
    render_to(cam, TOP_PNG, (TOP_RES, TOP_RES))
    for o in ceil_objs:
        o.hide_render = False
    return paths


def export_objects():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("PREVIEW_")]


def report():
    objs = export_objects()
    tris = sum(bkit.tri_count(o) for o in objs)
    mats = sorted({m.name for o in objs for m in o.data.materials if m})
    print("ZR_REPORT objects", len(objs), "tris", tris, "materials", len(mats))
    print("ZR_REPORT colliders", len(COLLIDERS), "lights", len(LIGHTS), "markers", len(MARKERS))
    return tris


# keep the GLB small: every texture at most 512 px
for _im in bpy.data.images:
    if _im.size[0] > 512 or _im.size[1] > 512:
        _im.scale(min(512, _im.size[0]), min(512, _im.size[1]))

if QUICK:
    ceil_objs = [o for o in bpy.data.objects if o.name.startswith("RAD_ceil")]
    for o in ceil_objs:
        o.hide_render = True
    cam = make_cam("cam_top", (-72.0, 0.0, 70.0), (-72.0, 0.0, 0.0), ortho=66.0)
    render_to(cam, TOP_PNG, (TOP_RES, TOP_RES))
    report()
    print("ZR_DONE")
else:
    paths = render_previews()
    tris = report()
    objs = export_objects()
    bkit.check(objs, max_tris=60000)
    os.makedirs(os.path.dirname(GLB), exist_ok=True)
    bkit.export_glb(GLB, objs, image_format="JPEG")
    print("ZR_REPORT glb_bytes", os.path.getsize(GLB))
    os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
    data = {"zone": NAME, "colliders": COLLIDERS, "lights": LIGHTS, "markers": MARKERS}
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    print("ZR_DONE")
