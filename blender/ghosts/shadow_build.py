"""Ch3 ghost SHADOW (孩子的影子), rebuilt: one of the 27 missing children, 1.15 m, small, sad, never scary.

bkit.base_body("male_stylized", detail=0) reshaped into a child (head enlarged 1.28x, limbs shortened and
thinned to 0.8), then posed with slumped shoulders and the head down as the rest shape. The body itself is a
near-black matte silhouette (hands and head keep their detail). Clothes are shells cut from the body: a boy's
t-shirt, shorts, socks, sneakers with soles and laces, and a baseball cap whose brim is attached to the
crown, all near black with slight variation. Soft fuzzy edges come from three faint alpha-blended haze
shells just outside the silhouette (separate unbaked meshes). Two small faint warm eye points are a separate
glow mesh. A small plush rabbit hangs by one ear from the right hand (own sway bone).
Clips: Idle, Move, Release (rises, shrinks and dissolves upward).

usage: python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py blender/ghosts/shadow_build.py blender/bake/ghosts/shadow [preview|game]
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, "/Users/alex/恐怖遊戲2/blender/ghosts")
import ch3_body as B  # noqa: E402
import ch3_human_common as C  # noqa: E402
import bkit  # noqa: E402
import lib  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
STAGE = (sys.argv[sys.argv.index("--") + 2:] or ["preview"])[0]
GLB = os.path.join(C.ROOT, "public", "models", "shadow.glb")
HB = float(os.environ.get("HB", "1.20"))
H_TARGET = 1.15
random.seed(1996)

bkit.reset_scene()
glow = lib.Mat("ShadowEye")
glow.set(color="#ffb070", emit="#ffa050", emit_strength=6.0, rough=0.4)


def dark_scan(name, asset, tint, val=0.8, scale=3.0, dirt="#050505", amt=0.5, rough=None):
    return C.scan_mat(name, asset, scale=scale, sat=0.0, val=val, tint=(tint,) * 3, dirt=dirt, dirt_amt=amt, rough=rough)


def haze_mat(name, alpha):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.012, 0.012, 0.014, 1)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Alpha"].default_value = alpha
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    m.use_backface_culling = False
    return m


def skin_mat():
    m = lib.Mat("ShadowSkin")
    col = m.ramp(m.noise(9.0, 4, 0.5, distortion=0.4), [(0.3, "#020203"), (0.7, "#09090b")])
    m.set(color=col, rough=0.92)
    return m.m


M = {
    "skin": skin_mat(),
    "shirt": dark_scan("ShirtCloth", "cotton_jersey", 0.07, val=0.9),
    "shorts": dark_scan("ShortsCloth", "denim_fabric_03", 0.05, val=0.7),
    "sock": dark_scan("SockCloth", "knitted_fleece", 0.09, val=0.9, scale=6.0),
    "shoe": C.scan_mat("Sneaker", "brown_leather", scale=3.0, sat=0.0, val=0.6, tint=(0.07, 0.07, 0.07), dirt="#030303", dirt_amt=0.5, rough=0.5),
    "sole": dark_scan("SneakerSole", "rubberized_track", 0.10, val=1.0, scale=3.0, amt=0.4, rough=0.8),
    "cap": dark_scan("CapCloth", "denim_fabric_03", 0.06, val=0.8),
    "plush": C.scan_mat("Plush", "curly_teddy_natural", scale=5.0, sat=0.0, val=0.6, tint=(0.14, 0.14, 0.14), dirt="#050505", dirt_amt=0.4),
    "glow": glow.m,
    "h1": haze_mat("Haze1", 0.28), "h2": haze_mat("Haze2", 0.14), "h3": haze_mat("Haze3", 0.07),
}

# ---------------------------------------------------------------- body: child proportions
body, ARM = bkit.base_body("male_stylized", HB, detail=0, name="Shadow")
print("BKIT_INFO base tris", bkit.tri_count(body), "dims", tuple(round(v, 3) for v in body.dimensions))
bones0 = {b.name: (Vector(b.head_local), Vector(b.tail_local)) for b in ARM.data.bones}
shoulder = {"L": bones0["upper_arm.L"][0], "R": bones0["upper_arm.R"][0]}
hipj = {"L": bones0["thigh.L"][0], "R": bones0["thigh.R"][0]}
headj = bones0["head"][0]
HEADK, LIMBK = 1.28, 0.80
gnames = [g.name for g in body.vertex_groups]
es = body["eye_start"]
for v in body.data.vertices:
    w = {}
    for g in v.groups:
        w[gnames[g.group]] = g.weight
    p = v.co.copy()
    for sd in ("L", "R"):
        wa = sum(w.get(f"{n}.{sd}", 0.0) for n in ("upper_arm", "forearm", "hand"))
        wl = sum(w.get(f"{n}.{sd}", 0.0) for n in ("thigh", "shin", "foot"))
        if wa > 0:
            p = shoulder[sd] + (p - shoulder[sd]) * (1 - (1 - LIMBK) * min(1.0, wa))
        if wl > 0:
            p = hipj[sd] + (p - hipj[sd]) * (1 - (1 - LIMBK) * min(1.0, wl))
    wh = 1.0 if v.index >= es else min(1.0, w.get("head", 0.0))
    if wh > 0:
        p = headj + (p - headj) * (1 + (HEADK - 1) * wh)
    v.co = p
body.data.update()


def tb(name, p):
    sd = "L" if p.x > 0 or name.endswith(".L") else "R"
    return p


bkit.active(ARM)
bpy.ops.object.mode_set(mode="EDIT")
newb = {}
for eb in ARM.data.edit_bones:
    h, t = Vector(eb.head), Vector(eb.tail)
    sdn = eb.name[-1] if eb.name[-2:] in (".L", ".R") else None
    def f(p):
        if sdn and eb.name.startswith(("upper_arm", "forearm", "hand")):
            return shoulder[sdn] + (p - shoulder[sdn]) * LIMBK
        if sdn and eb.name.startswith(("thigh", "shin", "foot")):
            return hipj[sdn] + (p - hipj[sdn]) * LIMBK
        if eb.name == "head":
            return headj + (p - headj) * HEADK
        return p
    newb[eb.name] = (f(h), f(t))
for eb in ARM.data.edit_bones:
    eb.use_connect = False
for eb in ARM.data.edit_bones:
    eb.head, eb.tail = newb[eb.name]
bpy.ops.object.mode_set(mode="OBJECT")
# feet on the ground (shift everything), thin sole room of 2 cm
zmin = min(v.co.z for v in body.data.vertices if v.index < es)
SOLE = 0.022
B.reshape_figure(body, ARM, lambda z: 1.0, lambda z: 1.0, dz=SOLE - zmin, y0=0.0)

FS = B.best_sign(ARM, "spine", 0, "head", lambda p: p.y)
B.bake_rest_pose(body, ARM, {
    "spine": (FS * 6, 0, 0), "chest": (FS * 9, 0, 0), "neck": (FS * 12, 0, 0), "head": (FS * 4, 0, 0),
    "_aim": {"upper_arm.L": (0.10, 0.02, -1), "upper_arm.R": (-0.10, 0.02, -1),
             "forearm.L": (0.06, -0.12, -1), "forearm.R": (-0.03, -0.32, -1)},
})
bpy.context.view_layer.update()
top = max(v.co.z for v in body.data.vertices if v.index < es)
print("BKIT_INFO child top", round(top, 3), "bbox x", round(body.dimensions.x, 3))

PARTS, GLOW, HAZE = [], [], []


def P(o):
    PARTS.append(o)
    return o


def bone_axis(n):
    b = ARM.data.bones[n]
    return Vector(b.head_local), Vector(b.tail_local)


hh_, ht_ = bone_axis("head")
HF = B.Frame(hh_, ht_ - hh_)
hl = [HF.l(p) for p in B.verts_where(body, lambda co, b: b == "head")]
eyes = [HF.l(v.co) for v in body.data.vertices if v.index >= es]
LU_EYE = sum(e[2] for e in eyes) / len(eyes)
LU_TOP = max(p[2] for p in hl)
# ---------------------------------------------------------------- skin silhouette (head, hands, rest), near-black
SK = {"head": lambda co, b: b in ("head", "neck") and HF.l(co)[2] < LU_EYE + 0.0,
      "HandL": lambda co, b: b == "hand.L", "HandR": lambda co, b: b == "hand.R",
      "Body": lambda co, b: b not in ("head", "neck", "hand.L", "hand.R")}
for nm, fn in SK.items():
    o = B.cut_shell(body, "Skin" + nm, fn, 0.0, 0.0, M["skin"])
    P(o)

# ---------------------------------------------------------------- clothes
hips_h, _ = bone_axis("hips")
kneeL = bone_axis("shin.L")[0]
ankleL = bone_axis("foot.L")[0]
elbowL = bone_axis("forearm.L")[0]
shL = bone_axis("upper_arm.L")[0]
Z_HEM = hips_h.z - 0.02
SLEEVE_Z = lambda co: co.z > elbowL.z + 0.45 * (shL.z - elbowL.z)
shirt = B.cut_shell(body, "Shirt", lambda co, b: (b in ("spine", "chest", "neck") and co.z > Z_HEM) or (b == "hips" and co.z > Z_HEM)
                    or (b.startswith("upper_arm") and SLEEVE_Z(co)) or (b == "neck" and False),
                    0.011, 0.006, M["shirt"], smooth_iter=1)
P(shirt)
shorts = B.cut_shell(body, "Shorts", lambda co, b: (b == "hips" and co.z <= Z_HEM + 0.01) or (b.startswith("thigh") and co.z > kneeL.z + 0.07),
                     0.014, 0.006, M["shorts"], smooth_iter=1)
P(shorts)
for nm in ("L", "R"):
    sock = B.cut_shell(body, f"Sock{nm}", lambda co, b, nm=nm: (b == f"shin.{nm}" and co.z < kneeL.z - 0.015) or (b == f"thigh.{nm}" and co.z <= kneeL.z + 0.07 and co.z > kneeL.z - 0.2 and False),
                       0.007, 0.004, M["sock"])
    P(sock)
    shoe = B.cut_shell(body, f"Shoe{nm}", lambda co, b, nm=nm: b == f"foot.{nm}" or (b == f"shin.{nm}" and co.z < ankleL.z + 0.035),
                       0.015, 0.006, M["shoe"], smooth_iter=1)
    P(shoe)
    hull = B.hull2d([(p.x, p.y) for p in B.verts_where(body, lambda co, b, nm=nm: b == f"foot.{nm}" and co.z < SOLE + 0.06)])
    hull = B.resample_poly(hull, 24)
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)

    def grow(pad, hull=hull, cx=cx, cy=cy):
        out = []
        for p in hull:
            d = Vector((p[0] - cx, p[1] - cy, 0)).normalized()
            out.append((p[0] + d.x * pad, p[1] + d.y * pad))
        return out
    rings = [[Vector((q[0], q[1], z)) for q in grow(pad)] for z, pad in ((0.0, 0.012), (0.004, 0.022), (0.024, 0.022), (0.034, 0.016))]
    vs, fs = B.ring_faces(rings, closed=True, cap_first=True, cap_last=True)
    sole = B.obj_from(f"Sole{nm}", vs, fs, M["sole"])
    B.orient_out(sole, (cx, cy, 0.015))
    B.finish_mod(sole, bevel=0.003)
    B.rigid(sole, f"foot.{nm}", M["sole"], ARM)
    P(sole)
    fh, ft = bone_axis(f"foot.{nm}")
    bt = B.bvh_of_obj(shoe)
    ax = Vector((ft.x - fh.x, ft.y - fh.y, 0)).normalized()
    side = Vector((-ax.y, ax.x, 0))
    for k in range(3):
        pt = fh + (ft - fh) * (0.12 + 0.2 * k)
        hit = bt.ray_cast(Vector((pt.x, pt.y, 1.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        c = hit[0] + Vector((0, 0, 0.003))
        r = B.cyl_along(f"Lace{nm}{k}", c - side * 0.03, c + side * 0.03, 0.0045, verts=5)
        B.rigid(r, f"foot.{nm}", M["sole"], ARM)
        P(r)

# ---------------------------------------------------------------- head frame, cap, eyes
print("BKIT_INFO head eye", round(LU_EYE, 3), "top", round(LU_TOP, 3))


def hslice(lu, tol=0.012):
    pts = [p for p in hl if abs(p[2] - lu) < tol]
    return (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts))


def cap_pt(lu, a, grow, shrink=1.0):
    x0, x1, f0, f1 = hslice(min(lu, LU_TOP - 0.03))
    cx, cf = (x0 + x1) / 2, (f0 + f1) / 2
    rx, rf = ((x1 - x0) / 2 + grow) * shrink, ((f1 - f0) / 2 + grow) * shrink
    return HF.w(cx + rx * math.sin(a), cf + rf * math.cos(a), lu)


LB0 = LU_EYE + 0.062
rings = []
n = 32
levels = [(LB0, 0.010, 1.0), (LB0 + 0.025, 0.012, 1.0), (LB0 + 0.055, 0.013, 0.99)]
topz = LU_TOP + 0.008
for t in (0.25, 0.5, 0.7, 0.85, 0.95):
    ang = t * math.pi / 2 * 0.92
    levels.append((levels[2][0] + (topz - levels[2][0]) * math.sin(ang) ** 1.2, 0.013, math.cos(ang) ** 0.9))
for lu, g, sh in levels:
    ring = []
    for i in range(n):
        a = i / n * math.tau
        low = 0.02 * B.sm01(0.0, 1.0, -math.cos(a)) if lu < LB0 + 0.05 else 0.0
        ring.append(cap_pt(lu - low, a, g, sh))
    rings.append(ring)
vs, fs = B.ring_faces(rings, closed=True, cap_last=True)
crown = B.obj_from("CapCrown", vs, fs, M["cap"])
B.orient_out(crown, HF.w(0, 0, (LB0 + LU_TOP) / 2))
B.finish_mod(crown, solid=0.007, offset=1.0, smooth_iter=1)
B.rigid(crown, "head", M["cap"], ARM)
P(crown)
rows = []
for j in range(4):
    v = j / 3
    row = []
    for i in range(17):
        a = math.radians(-40 + 80 * i / 16)
        base = cap_pt(LB0, a, 0.012)
        L = (0.07 * max(0.0, math.cos(a)) ** 0.5 + 0.004) * v
        d = HF.x * math.sin(a) + HF.f * math.cos(a)
        row.append(base + d * L - HF.u * (0.004 * v + 0.014 * v ** 1.6 * max(0.4, math.cos(a))))
    rows.append(row)
vs, fs = B.ring_faces(rows, closed=False)
brim = B.obj_from("CapBrim", vs, fs, M["cap"])
if sum(p.normal.dot(HF.u) * p.area for p in brim.data.polygons) < 0:
    bm = bmesh.new(); bm.from_mesh(brim.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(brim.data); bm.free()
B.finish_mod(brim, solid=0.008, offset=-1.0, bevel=0.002)
B.rigid(brim, "head", M["cap"], ARM)
P(brim)
btn = B.dome("CapButton", HF.w((hslice(LU_TOP - 0.03)[0] + hslice(LU_TOP - 0.03)[1]) / 2, (hslice(LU_TOP - 0.03)[2] + hslice(LU_TOP - 0.03)[3]) / 2, topz + 0.002), 0.013, (1, 1, 0.7), segs=8)
B.rigid(btn, "head", M["cap"], ARM)
P(btn)
for sd in (-1, 1):
    ey = [e for e in eyes if (e[0] > 0) == (sd > 0)]
    ex = sum(e[0] for e in ey) / len(ey)
    ef = min(e[1] for e in ey)
    g = B.cyl_along(f"EyeGlow{sd}", HF.w(ex, ef + 0.002, LU_EYE), HF.w(ex, ef + 0.008, LU_EYE), 0.011, 0.011, verts=8)
    B.orient_out(g, HF.w(ex, ef - 0.2, LU_EYE))
    B.rigid(g, "head", M["glow"], ARM)
    GLOW.append(g)

# ---------------------------------------------------------------- plush rabbit held by the ear
hd_h, hd_t = bone_axis("hand.R")
HC = (hd_h + hd_t) / 2 + Vector((0, -0.012, 0))
B.add_bone(ARM, "rabbit", HC, HC + Vector((0, 0, -0.2)), "hand.R")
RB = HC + Vector((0, -0.015, -0.16))


def ell(name, c, r, sc, rot=(0, 0, 0), segs=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=r, location=c)
    o = bpy.context.active_object
    o.name = o.data.name = name
    o.scale = sc
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for p in o.data.polygons:
        p.use_smooth = True
    B.rigid(o, "rabbit", M["plush"], ARM)
    return P(o)


ell("RabbitBody", RB + Vector((0, 0, -0.045)), 0.05, (1.0, 0.85, 1.25))
ell("RabbitHead", RB + Vector((0, -0.005, 0.045)), 0.04, (1.0, 1.0, 0.95))
ell("RabbitEarHeld", HC + Vector((0, 0, -0.065)), 0.024, (0.8, 0.5, 4.2), segs=8)
ell("RabbitEarLimp", RB + Vector((0.062, 0.0, -0.005)), 0.024, (0.8, 0.5, 4.6), rot=(0, -0.3, 0), segs=8)
for sd in (-1, 1):
    ell(f"RabbitFoot{sd}", RB + Vector((sd * 0.028, -0.025, -0.1)), 0.02, (0.9, 1.4, 0.75), segs=8)
    ell(f"RabbitArm{sd}", RB + Vector((sd * 0.05, -0.012, -0.015)), 0.014, (0.7, 0.7, 1.7), rot=(0, sd * 0.3, 0), segs=8)
ell("RabbitTail", RB + Vector((0, 0.04, -0.075)), 0.015, (1, 1, 1), segs=8)

# ---------------------------------------------------------------- haze shells: soft fuzzy edge, separate unbaked meshes
for k, (off, mk, tgt) in enumerate(((0.010, "h1", 450), (0.026, "h2", 400), (0.046, "h3", 350))):
    hz = B.cut_shell(body, f"Haze{k + 1}", lambda co, b: not b.startswith(("hand", "foot")), off, 0.0, M[mk], smooth_iter=3)
    B.dec(hz, 900, 60)
    # a little noise so the fringe is ragged, not a clean offset
    random.seed(k + 3)
    for v in hz.data.vertices:
        v.co += Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * off * 0.25
    hz["target"] = tgt
    HAZE.append(hz)


def shots(tag):
    C.reset(ARM)
    pre = os.path.join(C.RENDERS, f"ch3_shadow_{tag}")
    B.studio_shots(pre, (0, -0.05, 0.62), 3.4, tuple(HF.w(0, 0.03, 0.06)), (0.35, -1, -0.05), 0.75)
    if os.environ.get("DEV_DIR"):
        bkit.light_studio()
        B._shot(os.path.join(os.environ["DEV_DIR"], "s_feet.png"), Vector((0.3, -0.8, 0.25)), (0, 0, 0.12), 70)
        B._shot(os.path.join(os.environ["DEV_DIR"], "s_hand.png"), Vector((0.1, -0.9, 0.5)), tuple(HC), 70)
    B.dark_shot(os.path.join(C.RENDERS, f"ch3_shadow_dark_{tag}.png"), (0, 0, 0.62), cam_z=1.55, dist=6.0, energy=4000)


if STAGE in ("preview", "devshots"):
    shots("preview")
    print("BKIT_DONE preview")
    sys.exit(0)

# ================================================================ game
C.reset(ARM)
shots("preview")
for o in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.objects.remove(body, do_unlink=True)
TARGETS = {"SkinhHead": 0, "Skinhead": 950, "SkinHandL": 520, "SkinHandR": 520, "SkinBody": 1100, "Shirt": 1200, "Shorts": 520,
           "Sock": 160, "Shoe": 420, "Sole": 200, "CapCrown": 420, "CapBrim": 160}
for o in PARTS:
    bkit.active(o)
    for m in list(o.modifiers):
        if m.type != "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=m.name)
    for k, t in TARGETS.items():
        if o.name == k or o.name.startswith(k):
            if t:
                B.dec(o, t, 40)
            break
for o in HAZE:
    B.dec(o, o["target"], 60)
BUDGET = 8700
tot = sum(bkit.tri_count(o) for o in PARTS)
gtot = sum(bkit.tri_count(o) for o in GLOW)
htot = sum(bkit.tri_count(o) for o in HAZE)
print("BKIT_TRIS parts", tot, "glow", gtot, "haze", htot)
if tot + gtot + htot > BUDGET:
    big = [o for o in PARTS if bkit.tri_count(o) > 150]
    small = sum(bkit.tri_count(o) for o in PARTS if o not in big)
    r = max(0.3, (BUDGET - gtot - htot - small) / sum(bkit.tri_count(o) for o in big))
    for o in big:
        B.dec(o, bkit.tri_count(o) * r, 60)
    tot = sum(bkit.tri_count(o) for o in PARTS)
print("BKIT_TRIS parts final", tot)
C.fix_metals(list(M.values())) if False else None
obj = bkit.join(PARTS, "Shadow")
C.skin_on(obj, ARM)
obj.parent = ARM
glow_obj = bkit.join(GLOW, "ShadowEyes")
C.skin_on(glow_obj, ARM)
glow_obj.parent = ARM
B.swap_none_slots(obj)
# haze layers: skinned with the body's weights (they keep the groups) and unbaked, own alpha material
haze_objs = []
for k, hz in enumerate(HAZE):
    hz.name = hz.data.name = f"ShadowHaze{k + 1}"
    hz.data.materials.clear()
    hz.data.materials.append(M[("h1", "h2", "h3")[k]])
    bkit.box_uv(hz, size=1.0)
    C.skin_on(hz, ARM)
    hz.parent = ARM
    haze_objs.append(hz)
bkit.bake_to_textures(obj, os.path.join(OUT, "textures"), size=1024, samples=8)
glow_obj.data.materials.clear()
glow_obj.data.materials.append(M["glow"])
ALL = [obj, glow_obj] + haze_objs

AF = {n: B.best_sign(ARM, f"upper_arm.{n}", 0, f"hand.{n}", lambda p: p.y) for n in ("L", "R")}
TF = B.best_sign(ARM, "thigh.L", 0, "foot.L", lambda p: p.y)
SB = -B.best_sign(ARM, "shin.L", 0, "foot.L", lambda p: p.y)
f_ = FS
sn = lambda t, amp, ph=0.0: amp * math.sin(math.tau * (t + ph))

C.loop_clip(ARM, "Idle", 120, lambda t: {
    "spine": (f_ * sn(t, 1.0), 0, sn(t, 0.6, 0.1)),
    "chest": (f_ * sn(t, 1.0, 0.15), 0, 0),
    "neck": (f_ * (2 + sn(t, 1.2, 0.3)), sn(t, 3, 0.2), 0),
    "head": (f_ * sn(t, 1.0, 0.45), sn(t, 5, 0.1), sn(t, 1.5)),
    "upper_arm.L": (AF["L"] * sn(t, 1.2, 0.5), 0, 0),
    "upper_arm.R": (AF["R"] * sn(t, 1.0, 0.2), 0, 0),
    "rabbit": (sn(t, 6, 0.25), 0, sn(t, 4, 0.5)),
}, steps=12)


def move(t):
    s_, c_ = math.sin(math.tau * t), math.cos(math.tau * t)
    return {
        "hips": (0, sn(t, 2.5), sn(t, 1.5, 0.25)),
        "thigh.L": (TF * 18 * s_, 0, 0), "thigh.R": (-TF * 18 * s_, 0, 0),
        "shin.L": (SB * (max(0.0, -c_) * 28 + 3), 0, 0), "shin.R": (SB * (max(0.0, c_) * 28 + 3), 0, 0),
        "spine": (f_ * 3, -sn(t, 3), 0), "chest": (f_ * 2, sn(t, 2.5), 0),
        "neck": (f_ * 4, 0, 0), "head": (f_ * 1, sn(t, 2, 0.3), 0),
        "upper_arm.L": (AF["L"] * 10 * s_, 0, 0), "upper_arm.R": (-AF["R"] * 6 * s_, 0, 0),
        "rabbit": (sn(t, 10, 0.3), 0, sn(t, 6, 0.1)),
    }


C.loop_clip(ARM, "Move", 34, move, steps=8)


def release_clip():
    act = bpy.data.actions.new("Release")
    act.use_fake_user = True
    ARM.animation_data_create()
    ARM.animation_data.action = act
    keys = {
        "hips": [(1, (0, 0, 0), (0, 0, 0), 1.0), (20, (0, 0, 0), (0, 0.10, 0), 1.0), (48, (f_ * -8, 0, 0), (0, 0.75, 0), 0.7), (72, (f_ * -14, 0, 0), (0, 1.5, 0), 0.08)],
        "spine": [(1, (0, 0, 0), None, None), (30, (f_ * -10, 0, 0), None, None), (72, (f_ * -18, 0, 0), None, None)],
        "neck": [(1, (0, 0, 0), None, None), (30, (f_ * -22, 0, 0), None, None), (72, (f_ * -30, 0, 0), None, None)],
        "head": [(1, (0, 0, 0), None, None), (30, (f_ * -18, 0, 0), None, None), (72, (f_ * -24, 0, 0), None, None)],
        "upper_arm.L": [(1, (0, 0, 0), None, None), (40, (0, 0, 40), None, None), (72, (0, 0, 70), None, None)],
        "upper_arm.R": [(1, (0, 0, 0), None, None), (40, (0, 0, -40), None, None), (72, (0, 0, -70), None, None)],
        "thigh.L": [(1, (0, 0, 0), None, None), (48, (TF * 8, 0, 4), None, None), (72, (TF * 4, 0, 8), None, None)],
        "thigh.R": [(1, (0, 0, 0), None, None), (48, (-TF * 6, 0, -4), None, None), (72, (-TF * 4, 0, -8), None, None)],
        "shin.L": [(1, (0, 0, 0), None, None), (48, (SB * 14, 0, 0), None, None), (72, (SB * 24, 0, 0), None, None)],
        "shin.R": [(1, (0, 0, 0), None, None), (48, (SB * 10, 0, 0), None, None), (72, (SB * 20, 0, 0), None, None)],
        "rabbit": [(1, (0, 0, 0), None, None), (30, (14, 0, 6), None, None), (72, (24, 0, 10), None, None)],
    }
    for bone, fr in keys.items():
        pb = ARM.pose.bones[bone]
        pb.rotation_mode = "XYZ"
        for f, rot, loc, scl in fr:
            pb.rotation_euler = tuple(math.radians(a) for a in rot)
            pb.keyframe_insert("rotation_euler", frame=f)
            if loc is not None:
                pb.location = loc
                pb.keyframe_insert("location", frame=f)
            if scl is not None:
                pb.scale = (scl, scl, scl)
                pb.keyframe_insert("scale", frame=f)
    tr = ARM.animation_data.nla_tracks.new()
    tr.name = "Release"
    tr.strips.new("Release", 1, act)
    ARM.animation_data.action = None
    for pb in ARM.pose.bones:
        pb.scale = (1, 1, 1)
    C.reset(ARM)
    print("BKIT_CLIP Release")


release_clip()

bkit.check(ALL, max_tris=9000)
bkit.report(ALL)
C.export_glb(GLB, ARM, ALL)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "shadow.blend"))
for t in ARM.animation_data.nla_tracks:
    t.mute = True
for hz in haze_objs:
    pass
shots("baked")
print("BKIT_DONE game")
