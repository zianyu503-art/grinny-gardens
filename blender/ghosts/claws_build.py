"""Chapter 3 claw builder.

Every claw keeps the source hand body (HandL from public/models/clawhands.glb, decimated)
and re-colours its enamel. Each claw adds its own attachments to Hand and its own
Jaw0..Jaw2 (origin on the source hinge positions), plus an optional emissive Glow node.

    python3 run.py claws_build.py <out_dir> <claw_id>   claw_id: scissors|magnet|grapple|flash|horn|charge
    python3 run.py claws_build.py <out_dir> lineup      six exported claws side by side
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT, CID = ARGS[0], ARGS[1]
ROOT = "/Users/alex/恐怖遊戲2"
SRC = f"{ROOT}/public/models/clawhands.glb"
GLB = f"{ROOT}/public/models/claw_{CID}.glb"
PREVIEW = f"{ROOT}/renders/ch3_claw_{CID}.png"
Z = Vector((0, 0, 1))

# per claw: enamel colour (linear RGB), metallic, roughness
SPEC = {
    "scissors": dict(enamel=(0.085, 0.05, 0.022), metal=0.55, rough=0.32),
    "magnet": dict(enamel=(0.14, 0.01, 0.012), metal=0.30, rough=0.30),
    "grapple": dict(enamel=(0.155, 0.19, 0.03), metal=0.25, rough=0.38),
    "flash": dict(enamel=(0.79, 0.46, 0.02), metal=0.15, rough=0.34, chips=0.07),
    "horn": dict(enamel=(0.70, 0.62, 0.45), metal=0.10, rough=0.42),
    "charge": dict(enamel=(0.007, 0.10, 0.115), metal=0.35, rough=0.30),
}
# key: (linear colour, metallic, roughness, texture options)
MATS = {
    "alu": ((0.50, 0.57, 0.62), 0.85, 0.27, {}),
    "rubber": ((0.028, 0.035, 0.042), 0.10, 0.55, {}),
    "vent": ((0.008, 0.013, 0.018), 0.0, 0.65, {}),
    "steel": ((0.55, 0.57, 0.60), 1.0, 0.20, {"scratch": 1.0}),
    "chrome": ((0.80, 0.82, 0.84), 1.0, 0.08, {}),
    "brass": ((0.66, 0.48, 0.18), 1.0, 0.33, {"tarnish": 0.35}),
    "copper": ((0.72, 0.33, 0.13), 1.0, 0.30, {"tarnish": 0.2}),
    "ceramic": ((0.78, 0.76, 0.70), 0.0, 0.42, {}),
    "wood": ((0.20, 0.095, 0.045), 0.0, 0.62, {}),
    "thread": ((0.50, 0.02, 0.02), 0.0, 0.50, {}),
    "plate": ((0.74, 0.74, 0.70), 0.0, 0.36, {}),
    "black": ((0.025, 0.025, 0.03), 0.0, 0.42, {}),
    "wire": ((0.55, 0.56, 0.58), 1.0, 0.42, {"scratch": 1.0}),
}
GLOW = {"warm": ((1.0, 0.90, 0.70), 9.0), "cold": ((0.45, 0.80, 1.0), 10.0)}
BODY_MAP = {"Machined aluminium": "alu", "Graphite rubber": "rubber",
            "Cobalt enamel": "enamel", "Vent recess": "vent"}

CACHE = {}
PARTS = {"hand": [], "j0": [], "j1": [], "j2": [], "glow": []}
CUR = "hand"
A = Vector((0, 0, 0))      # hand axis (xy)
HINGE = []                 # source JawL0..2 world positions


def to(kind):
    global CUR
    CUR = kind


# ---------------------------------------------------------------- materials

def _noise(rng, n, cells):
    g = rng.random((cells, cells))
    a = np.kron(g, np.ones((n // cells, n // cells)))
    for _ in range(3):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def _save_png(arr, name, colorspace, path):
    n = arr.shape[0]
    rgba = np.ones((n, n, 4), dtype=np.float32)
    rgba[..., :3] = arr
    im = bpy.data.images.new(name, n, n, alpha=False)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = colorspace
    return im


def make_mat(key):
    if key in CACHE:
        return CACHE[key]
    if key.startswith("glow_"):
        col, strength = GLOW[key[5:]]
        mat = bpy.data.materials.new(f"{CID}_{key}")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
        bsdf.inputs["Emission Color"].default_value = (*col, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
        CACHE[key] = mat
        return mat
    if key == "enamel":
        s = SPEC[CID]
        col, metal, rough = s["enamel"], s["metal"], s["rough"]
        opt = {"chips": s.get("chips", 0)}
    else:
        col, metal, rough, opt = MATS[key]
    rng = np.random.default_rng(sum(map(ord, CID + key)))
    n = 256
    big, fine = _noise(rng, n, 8), _noise(rng, n, 32)
    rgb = np.ones((n, n, 3)) * np.array(col)
    rgb *= (0.90 + 0.12 * big + 0.06 * fine)[..., None]
    if opt.get("tarnish"):
        tar = np.clip((big - (1 - opt["tarnish"])) * 6, 0, 1)
        rgb *= (1 - 0.5 * tar)[..., None]
    if opt.get("chips"):
        rgb[fine > 1 - opt["chips"]] = (0.45, 0.45, 0.45)
    srgb = np.clip(rgb, 0, 1) ** (1 / 2.2)
    rgh = rough * (0.8 + 0.45 * fine + 0.2 * big)
    for _ in range(int(40 * (1 + opt.get("scratch", 0)))):
        y, x = rng.integers(n, size=2)
        rgh[y, x:x + int(rng.integers(12, 60))] += 0.3
    rgh = np.clip(rgh, 0.04, 1)
    os.makedirs(OUT, exist_ok=True)
    ci = _save_png(srgb, f"{CID}_{key}_c", "sRGB", f"{OUT}/tex_{CID}_{key}_color.png")
    ri = _save_png(np.repeat(rgh[..., None], 3, 2), f"{CID}_{key}_r", "Non-Color",
                   f"{OUT}/tex_{CID}_{key}_rough.png")
    mat = bpy.data.materials.new(f"{CID}_{key}")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Metallic"].default_value = metal
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = ci
    tr = nt.nodes.new("ShaderNodeTexImage")
    tr.image = ri
    nt.links.new(uv.outputs["UV"], tc.inputs["Vector"])
    nt.links.new(uv.outputs["UV"], tr.inputs["Vector"])
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    CACHE[key] = mat
    return mat


# ---------------------------------------------------------------- primitives (world coords)

def _link(o, mat):
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    PARTS[CUR].append(o)
    return o


def cyl(p0, p1, r, key, segs=12):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=segs, radius=r, depth=d.length,
                                        location=(p0 + p1) / 2)
    o = bpy.context.active_object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.normalized().to_track_quat("Z", "Y")
    return _link(o, make_mat(key))


def disc(c, axis, r, depth, key, segs=12):
    a = Vector(axis).normalized() * depth / 2
    c = Vector(c)
    return cyl(c - a, c + a, r, key, segs)


def ball(c, r, key, segs=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(3, segs // 2),
                                         radius=r, location=Vector(c))
    return _link(bpy.context.active_object, make_mat(key))


def _bevel(o, w):
    w = min(w, 0.35 * min(o.dimensions))
    if w > 0.0005:
        bkit.harden(o, width=w, segments=1)


def bar(p0, p1, w, t, key, side, bevel=0.003):
    """Box from p0 to p1: width w along side, thickness t across it."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    z = d.normalized()
    s = Vector(side)
    s = (s - s.dot(z) * z).normalized()
    y = z.cross(s)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(p0 + p1) / 2)
    o = bpy.context.active_object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Matrix((s, y, z)).transposed().to_quaternion()
    o.scale = (w, t, d.length)
    _bevel(o, bevel)
    return _link(o, make_mat(key))


def blob(c, size, key, bevel=0.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=Vector(c))
    o = bpy.context.active_object
    o.scale = size
    _bevel(o, bevel)
    return _link(o, make_mat(key))


def lathe_at(profile, c, direction, key, segs=16):
    o = bkit.lathe(profile, segments=segs, name=f"{CID}_lathe")
    o.matrix_world = (Matrix.Translation(Vector(c))
                      @ Vector(direction).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4())
    return _link(o, make_mat(key))


def P(r, th, z):
    """Point on the hand's cylinder: radius r from the axis, angle th, height z."""
    return Vector((A.x + r * math.cos(th), A.y + r * math.sin(th), z))


def RAD(th):
    return Vector((math.cos(th), math.sin(th), 0.0))


def TAN(th):
    return Vector((-math.sin(th), math.cos(th), 0.0))


def jaw_frame(k):
    H = HINGE[k]
    th = math.atan2(H.y - A.y, H.x - A.x)
    return H, th, RAD(th), TAN(th)


# ---------------------------------------------------------------- the six claws

def build_scissors():
    th = math.pi / 2
    to("hand")
    cyl((A.x, A.y, 1.80), (A.x, A.y, 1.88), 0.042, "brass", 12)           # pivot bolt
    cyl((A.x, A.y, 1.88), (A.x, A.y, 1.90), 0.06, "brass", 12)            # bolt head
    cyl(P(0.30, th, 1.36), P(0.41, th, 1.36), 0.034, "wood", 10)          # thread spool
    disc(P(0.37, th, 1.36), RAD(th), 0.058, 0.012, "wood", 12)
    disc(P(0.405, th, 1.36), RAD(th), 0.058, 0.012, "wood", 12)
    cyl(P(0.37, th, 1.36), P(0.40, th, 1.36), 0.0365, "thread", 10)      # red thread on spool
    bar(P(0.40, th, 1.33), P(0.40, th, 1.12), 0.012, 0.004, "thread", TAN(th), bevel=0.0)
    for k in range(3):
        to(f"j{k}")
        H, th_k, ru, tg = jaw_frame(k)
        if k < 2:  # long tailor's shear blades
            tip = H + Vector((0, 0, -0.84)) - ru * 0.16
            mid = H + Vector((0, 0, -0.45)) - ru * 0.08
            bar(H + Vector((0, 0, -0.10)), mid, 0.05, 0.012, "steel", tg, bevel=0.0015)  # wide heel
            bar(mid, tip, 0.024, 0.010, "steel", tg, bevel=0.0012)                        # tapered edge
            bar(H + Vector((0, 0, 0.03)), H + Vector((0, 0, -0.14)), 0.07, 0.05, "steel", tg,
                bevel=0.004)                                              # shoulder block
            disc(H, tg, 0.024, 0.03, "brass", 10)
        else:      # small third jaw
            bar(H, H + Vector((0, 0, -0.24)) - ru * 0.03, 0.03, 0.02, "steel", tg)
            disc(H, tg, 0.02, 0.02, "brass", 10)


def build_magnet():
    to("hand")
    disc((A.x, A.y, 1.44), Z, 0.323, 0.034, "alu", 16)                    # silver band
    for i in range(6):
        disc((A.x, A.y, 1.27 + 0.018 * i), Z, 0.324, 0.008, "copper", 10)  # coil windings
    for i in range(3):
        disc((A.x, A.y, 1.56 + 0.018 * i), Z, 0.324, 0.008, "copper", 10)
    blob(P(0.327, -math.pi / 2, 1.50), (0.09, 0.006, 0.07), "plate")     # warning plate
    for k in range(3):
        to(f"j{k}")
        H, th_k, ru, tg = jaw_frame(k)
        disc(H + Vector((0, 0, -0.14)), Z, 0.042, 0.05, "copper", 10)     # jaw coil
        cyl(H, H + Vector((0, 0, -0.22)), 0.016, "steel", 8)
        bar(H + Vector((0, 0, -0.22)), H + Vector((0, 0, -0.37)) - ru * 0.03,
            0.10, 0.11, "steel", tg, bevel=0.004)                          # pole shoe


def build_grapple():
    th = math.pi / 2
    to("hand")
    bar(P(0.30, th, 1.46), P(0.345, th, 1.46), 0.04, 0.04, "steel", TAN(th), bevel=0.0)
    disc(P(0.345, th, 1.46), RAD(th), 0.10, 0.014, "enamel", 14)          # drum flanges
    disc(P(0.425, th, 1.46), RAD(th), 0.10, 0.014, "enamel", 14)
    disc(P(0.385, th, 1.46), RAD(th), 0.085, 0.07, "wire", 14)            # wound steel wire
    for k in range(3):
        to(f"j{k}")
        H, th_k, ru, tg = jaw_frame(k)
        pts = [H,
               H + Vector((0, 0, -0.30)) - ru * 0.02,
               H + Vector((0, 0, -0.40)) - ru * 0.10,
               H + Vector((0, 0, -0.33)) - ru * 0.24]                     # curls inward to a point
        ball(H, 0.03, "steel", 8)
        for a, b in zip(pts, pts[1:]):
            cyl(a, b, 0.014, "steel", 8)
            ball(b, 0.015, "steel", 6)


def build_flash():
    to("hand")
    cyl(P(0.30, 0.0, 1.30), P(0.43, 0.0, 1.30), 0.05, "black", 14)        # capacitor can
    disc(P(0.43, 0.0, 1.30), RAD(0.0), 0.05, 0.006, "steel", 14)
    refl = [(0.17 * s, -0.12 * s * s) for s in np.linspace(0.1, 1.0, 9)]   # parabolic reflector
    profile = ([(0.0, 0.0)] + [(float(r), float(z)) for r, z in refl]
               + [(0.165, -0.13), (0.0, -0.02)])
    lathe_at(profile, (A.x, A.y, 0.62), Z, "chrome", segs=24)
    cyl((A.x, A.y, 0.57), (A.x, A.y, 0.80), 0.01, "steel", 8)             # bulb stem
    to("glow")
    ball((A.x, A.y, 0.57), 0.032, "glow_warm", 10)                       # flashbulb
    for k in range(3):
        to(f"j{k}")
        H, th_k, ru, tg = jaw_frame(k)
        E = P(0.23, th_k, 0.84)
        Q = P(0.178, th_k, 0.50)                                           # clamps the dish rim
        cyl(H, E, 0.016, "steel", 8)
        cyl(E, Q, 0.016, "steel", 8)
        ball(E, 0.02, "steel", 6)
        ball(Q, 0.022, "steel", 6)


def build_horn():
    to("hand")
    disc((A.x, A.y, 1.25), Z, 0.320, 0.012, "brass", 16)
    disc((A.x, A.y, 1.655), Z, 0.320, 0.012, "brass", 16)
    th = math.pi / 2
    for z in (1.36, 1.44):                                                 # speaker grille
        for dt in (-0.04, 0.0, 0.04):
            disc(P(0.318, th, z) + TAN(th) * dt, RAD(th), 0.011, 0.01, "vent", 8)
    L = 0.33
    ss = np.linspace(0, L, 8)
    rr = [0.034 + 0.10 * (s / L) ** 2.4 for s in ss]
    outer = [(float(r), float(s)) for r, s in zip(rr, ss)]
    inner = [(float(r - 0.007), float(s)) for r, s in reversed(list(zip(rr, ss)))]
    profile = [(0.0, 0.0)] + outer + inner[:-1] + [(0.0, 0.0)]
    T0 = Vector((A.x, A.y - 0.28, 1.36))
    DH = Vector((0, -1, 0))
    lathe_at(profile, T0, DH, "brass", segs=16)                           # gramophone horn
    M = T0 + DH * L                                                       # horn mouth centre
    for k in range(3):
        to(f"j{k}")
        H, th_k, ru, tg = jaw_frame(k)
        phi = [-math.pi / 2, math.radians(30), math.radians(150)][k]
        tip = M + Vector((0.15 * math.cos(phi), 0, 0.15 * math.sin(phi)))
        E = (H + tip) / 2 + Vector((0, -0.06, 0.04))
        cyl(H, E, 0.017, "enamel", 8)
        cyl(E, tip, 0.015, "enamel", 8)
        ball(E, 0.019, "enamel", 6)
        ball(tip, 0.024, "brass", 8)


def build_charge():
    to("hand")
    cyl((A.x, A.y, 1.81), (A.x, A.y, 1.84), 0.10, "ceramic", 16)           # tesla coil base
    for i in range(9):
        disc((A.x, A.y, 1.845 + 0.012 * i), Z, 0.072, 0.006, "copper", 12)  # copper windings
    ball((A.x, A.y, 1.99), 0.04, "copper", 8)
    disc((A.x, A.y, 1.30), Z, 0.327, 0.03, "ceramic", 16)
    disc((A.x, A.y, 1.60), Z, 0.327, 0.03, "ceramic", 16)
    for k in range(3):
        to(f"j{k}")
        H, th_k, ru, tg = jaw_frame(k)
        E = H + Vector((0, 0, -0.42)) - ru * 0.05
        tip = H + Vector((0, 0, -0.80)) - ru * 0.10
        cyl(H, E, 0.014, "steel", 8)
        disc(H + (E - H) * 0.4, E - H, 0.026, 0.035, "ceramic", 12)
        cyl(E, tip, 0.011, "copper", 8)
        disc(E + (tip - E) * 0.5, tip - E, 0.02, 0.03, "ceramic", 12)
        to("glow")
        ball(tip, 0.014, "glow_cold", 6)


BUILDERS = {"scissors": build_scissors, "magnet": build_magnet, "grapple": build_grapple,
            "flash": build_flash, "horn": build_horn, "charge": build_charge}


# ---------------------------------------------------------------- build and export

def build_claw():
    global A, HINGE
    bkit.reset_scene()
    bpy.ops.import_scene.gltf(filepath=SRC)
    body = bpy.data.objects["HandL"]
    HINGE = [bpy.data.objects[f"JawL{k}"].matrix_world.translation.copy() for k in range(3)]
    corners = [body.matrix_world @ Vector(c) for c in body.bound_box]
    A = Vector(((min(p.x for p in corners) + max(p.x for p in corners)) / 2,
                (min(p.y for p in corners) + max(p.y for p in corners)) / 2, 0.0))
    for o in list(bpy.data.objects):
        if o is not body:
            bpy.data.objects.remove(o, do_unlink=True)
    bkit.decimate(body, 1600)
    for i, slot in enumerate(body.data.materials):
        body.data.materials[i] = make_mat(BODY_MAP[slot.name])

    BUILDERS[CID]()
    for kind, parts in PARTS.items():
        if kind == "glow":
            continue
        for o in parts:
            bkit.apply_all(o)
            bkit.box_uv(o, size=0.25)

    hand = bkit.join([body] + PARTS["hand"], "Hand")
    jaws = []
    for k in range(3):
        o = bkit.join(PARTS[f"j{k}"], f"Jaw{k}")
        bkit.active(o)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        o.data.transform(Matrix.Translation(-HINGE[k]))
        o.location = HINGE[k]
        jaws.append(o)
    objs = [hand] + jaws
    if PARTS["glow"]:
        objs.append(bkit.join(PARTS["glow"], "Glow"))

    bkit.check(objs, max_tris=4000, ground=False)
    bkit.report(objs)
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/claw_{CID}.blend")
    bkit.export_glb(GLB, objs=objs, image_format="JPEG")
    bkit.light_studio()
    bkit.render_views(PREVIEW, size=400, samples=24)


def lineup():
    bkit.reset_scene()
    scene = bpy.context.scene
    for i, cid in enumerate(SPEC):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=f"{ROOT}/public/models/claw_{cid}.glb")
        for o in bpy.data.objects:
            if o not in before and o.parent is None:
                o.location.x += i * 1.15
    bkit.light_studio()
    objs = [o for o in scene.objects if o.type == "MESH"]
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 620
    scene.render.film_transparent = False
    cam = bkit._frame_camera(objs, (0, -1, 0.12), ortho=True, margin=1.08)
    span = 1.15 * (len(SPEC) - 1)
    cam.location.x = -2.236 + span / 2
    cam.data.ortho_scale = span + 1.9
    scene.render.filepath = f"{ROOT}/renders/ch3_claws_lineup.png"
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print("BKIT_LINEUP", [o.name for o in objs])


if CID == "lineup":
    lineup()
else:
    build_claw()
