"""Ch3 ghost TICKET (剪票人), rebuilt: Old Zhou, 2.6 m, the unkillable pursuer.

bkit.base_body("male_realistic", detail=0) widened ~1.35x through torso and shoulders, stooped with
the head thrust forward, then dressed in real shells cut from its own surface: a knee length double
breasted railway coat (collar, lapels, belt, pocket flaps, brass buttons, folded hem), trousers,
laced boots with soles, a gloved left hand (the base mesh hand under a leather shell), a peaked
conductor's cap with badge, and a dented steel face plate with two punched holes (glow = separate
unbaked mesh). The right hand is a huge steel ticket punch strapped to the forearm. Riveted steel
booth plates on chest and both shoulders (own bones), a turnstile arm across the back, big paper
tickets in bundles at the belt (own sway bones).

usage: python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py blender/ghosts/ticket_build.py blender/bake/ghosts/ticket [preview|game]
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
GLB = os.path.join(C.ROOT, "public", "models", "ticket.glb")
DEV = os.environ.get("DEV_DIR")  # dev renders go here when set
random.seed(1963)
HB = float(os.environ.get("HB", "2.47"))   # base body height before widening and stoop
SOLE = 0.06

bkit.reset_scene()
glow = lib.Mat("TicketGlow")
glow.set(color="#ffb040", emit="#ffb040", emit_strength=9.0, rough=0.4)


def scan(name, asset, **kw):
    return C.scan_mat(name, asset, **kw)


M = {
    "coat": scan("CoatWool", "caban", scale=2.5, sat=0.15, val=0.6, tint=(0.13, 0.14, 0.16), dirt="#0c0a08", dirt_amt=0.8),
    "trousers": scan("Trousers", "poly_wool_herringbone", scale=3.0, sat=0.15, val=0.7, tint=(0.16, 0.16, 0.17), dirt="#0c0a08", dirt_amt=0.75),
    "cloth": scan("DarkCloth", "denim_fabric_03", scale=3.0, sat=0.1, val=0.6, tint=(0.12, 0.12, 0.13), dirt="#080706", dirt_amt=0.6),
    "leather": scan("Leather", "brown_leather", scale=2.0, sat=0.6, val=0.7, tint=(0.38, 0.32, 0.28), dirt="#120c08", dirt_amt=0.8, rough=0.55),
    "glove": scan("Glove", "brown_leather", scale=3.0, sat=0.5, val=0.6, tint=(0.28, 0.24, 0.22), dirt="#0c0806", dirt_amt=0.75, rough=0.6),
    "sole": scan("Sole", "rubberized_track", scale=2.0, tint=(0.25, 0.24, 0.23), dirt="#0e0e0c", dirt_amt=0.5, rough=0.8),
    "steel": scan("SteelPlate", "green_metal_rust", scale=1.8, val=0.7, tint=(0.45, 0.52, 0.46), dirt="#0c0a06", dirt_amt=0.7, metal=0.35),
    "dark": scan("PunchSteel", "blue_metal_plate", scale=2.0, sat=0.5, val=0.8, tint=(0.55, 0.5, 0.5), dirt="#5a2a10", dirt_amt=0.9, metal=0.35, rough=0.6),
    "rust": scan("TurnstileRust", "rusty_metal_02", scale=2.0, val=0.7, tint=(0.4, 0.3, 0.25), dirt="#1a0e08", dirt_amt=0.7, metal=0.35),
    "brass": lib.mat_simple("Brass", "#8a6a2c", 0.4, metal=1.0),
    "paper": scan("Ticket", "rough_linen", scale=4.0, sat=0.8, val=0.8, tint=(1.0, 0.82, 0.5), dirt="#4a3a22", dirt_amt=0.6),
    "paper2": scan("Ticket2", "rough_linen", scale=4.0, sat=0.8, val=0.7, tint=(0.85, 0.72, 0.5), dirt="#3a2a1a", dirt_amt=0.7),
    "peak": scan("Peak", "brown_leather", scale=3.0, sat=0.5, tint=(0.14, 0.12, 0.11), dirt="#0a0806", dirt_amt=0.6, rough=0.3),
    "cap": scan("CapCloth", "caban", scale=3.0, sat=0.15, val=0.7, tint=(0.11, 0.12, 0.15), dirt="#0a0908", dirt_amt=0.75),
    "plate": scan("FacePlateSteel", "blue_metal_plate", scale=3.0, sat=0.3, val=0.9, tint=(0.75, 0.75, 0.78), dirt="#3a200e", dirt_amt=0.65, metal=0.35, rough=0.5),
    "ink": lib.mat_simple("TicketInk", "#5a2a20", 0.7),
    "paint": lib.mat_simple("StencilPaint", "#b9a24a", 0.8),
    "glow": glow.m,
}
M["paint"].name = "StencilPaint"

# ---------------------------------------------------------------- body: widen, shift up, stoop
body, ARM = bkit.base_body("male_realistic", HB, detail=0, name="Ticket")
print("BKIT_INFO base tris", bkit.tri_count(body), "dims", tuple(round(v, 3) for v in body.dimensions))
S = HB / 2.4
y0 = -0.06 * S


def fx(z):
    return 1.12 + 0.23 * (1 - B.sm01(0.80 * HB, 0.90 * HB, z))


B.reshape_figure(body, ARM, fx, fx, dz=SOLE, y0=y0)
FS = B.best_sign(ARM, "spine", 0, "head", lambda p: p.y)     # forward (-y) pitch sign
IN_L = B.best_sign(ARM, "upper_arm.L", 2, "hand.L", lambda p: abs(p.x))
IN_R = B.best_sign(ARM, "upper_arm.R", 2, "hand.R", lambda p: abs(p.x))
FB_L = B.best_sign(ARM, "forearm.L", 0, "hand.L", lambda p: p.y)
FB_R = B.best_sign(ARM, "forearm.R", 0, "hand.R", lambda p: p.y)
print("BKIT_SIGNS", FS, IN_L, IN_R, FB_L, FB_R)
B.bake_rest_pose(body, ARM, {
    "spine": (FS * 9, 0, 0), "chest": (FS * 10, 0, 0), "neck": (FS * 14, 0, 0), "head": (FS * -16, 0, 0),
    "_aim": {"upper_arm.L": (0.17, -0.06, -1), "upper_arm.R": (-0.17, -0.06, -1),
             "forearm.L": (0.10, -0.40, -1), "forearm.R": (-0.06, -0.80, -1)},
})
bpy.context.view_layer.update()

bpts = [v.co for v in body.data.vertices if v.index < body["eye_start"]]
print("BKIT_INFO stooped top", round(max(p.z for p in bpts), 3), "xrange", round(min(p.x for p in bpts), 3), round(max(p.x for p in bpts), 3))
for n in ("hips", "spine", "chest", "neck", "head", "upper_arm.L", "forearm.L", "hand.L", "forearm.R", "hand.R", "thigh.L", "shin.L", "foot.L"):
    b = ARM.data.bones[n]
    print("BKIT_BONE", n, tuple(round(c, 3) for c in b.head_local), tuple(round(c, 3) for c in b.tail_local))


def dev_render(name):
    if DEV:
        bkit.light_studio()
        bkit.render_views(os.path.join(DEV, name), size=500, samples=12, views=("front", "side", "back", "detail"))


if os.environ.get("STOP") == "body":
    dev_render("t_body.png")
    sys.exit(0)

PARTS, GLOW = [], []


def P(o):
    PARTS.append(o)
    return o


def bone_axis(name):
    b = ARM.data.bones[name]
    return Vector(b.head_local), Vector(b.tail_local)


# ================================================================ coat
UPPER = {"spine", "chest", "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R", "hips"}


def sel_bod(co, b):
    if b in ("hips", "spine"):
        return co.z > 1.46
    return b in UPPER


bodice = B.cut_shell(body, "CoatBodice", sel_bod,
                     lambda co: 0.04 if (abs(co.x) > 0.40 and co.z < 2.05) else 0.055, 0.02, M["coat"], smooth_iter=2)
P(B.rigid_keep(bodice) if hasattr(B, "rigid_keep") else bodice)
BODICE = bodice

# body slices for the skirt and belt
LEGB = {"hips", "thigh.L", "thigh.R", "shin.L", "shin.R", "spine"}
Z_BELT, Z_HEM = 1.50, 0.62
SL = []
for z in (1.52, 1.30, 1.10, 0.90, 0.70, 0.60):
    bx = B.slice_box(body, z - 0.03, z + 0.03, bones=LEGB, xmax=0.75)
    SL.append((z, (bx[0] + bx[1]) / 2, (bx[1] - bx[0]) / 2, (bx[2] + bx[3]) / 2, (bx[3] - bx[2]) / 2))
print("BKIT_SLICES", [tuple(round(c, 3) for c in r) for r in SL])


def prof(z):
    z = max(SL[-1][0], min(SL[0][0], z))
    for a, b in zip(SL, SL[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0])
            return [a[i] + (b[i] - a[i]) * t for i in range(1, 5)]
    return SL[-1][1:]


def skirt_pt(z, a, extra=0.0, fold=1.0):
    cx, rx, cy, ry = prof(z)
    t = max(0.0, (Z_BELT + 0.02 - z) / (Z_BELT - Z_HEM))
    pad = 0.07 + 0.13 * t ** 0.85 + extra
    amp = 0.05 * B.sm01(0.0, 0.5, t) * fold
    f = 1 + amp * (0.6 * math.sin(7 * a + 0.9 + 3 * t) + 0.4 * math.sin(13 * a + 2.0 * z * 5))
    return Vector((cx + (rx + pad) * f * math.sin(a), cy - (ry + pad * 0.8) * f * math.cos(a), z))


def skirt_mesh(name, a_front0, a_front1, extra, K=16, n=44, thick=0.018, slit=True, mat=None, top=Z_BELT + 0.02, hem=Z_HEM):
    rings = []
    for k in range(K):
        tk = k / (K - 1)
        pts = []
        for i in range(n):
            u = i / (n - 1)
            a0, a1 = a_front0, a_front1
            if slit:
                zk = top + (hem - top) * tk
                g = 0.20 * B.sm01(0.98, 0.64, zk)
                a0, a1 = math.pi + g, 3 * math.pi - g
            a = a0 + (a1 - a0) * u
            hz = hem + 0.035 * math.sin(5 * a + 1.0) + 0.02 * math.sin(11 * a + 0.3) + (0.03 if slit and abs(math.sin(a)) < 0.12 else 0)
            z = top + (hz - top) * tk
            pts.append(skirt_pt(z, a, extra, 1.0 if slit else 0.6))
        rings.append(pts)
    vs, fs = B.ring_faces(rings, closed=False)
    fs = [tuple(reversed(f)) for f in fs]
    o = B.obj_from(name, vs, fs, mat)
    B.weld(o)
    B.finish_mod(o, solid=thick, offset=1.0)
    return o


skirt = skirt_mesh("CoatSkirt", 0, 0, 0.0, mat=M["coat"])
B.orient_out(skirt)


def skirt_w(co):
    t = B.sm01(1.40, 0.80, co.z)
    side = B.sm01(-0.12, 0.12, co.x)
    w = 0.85 * t
    return {"hips": 1 - w, "thigh.L": w * side, "thigh.R": w * (1 - side)}


B.weighted(skirt, ARM, skirt_w, M["coat"], 0.5)
P(skirt)

# double breasted front panel (right flap over left), slightly proud of the skirt
flap = skirt_mesh("CoatFlap", -0.50, 0.20, 0.016, K=12, n=9, thick=0.016, slit=False, mat=M["coat"], top=Z_BELT + 0.0, hem=Z_HEM + 0.02)
B.orient_out(flap)
B.weighted(flap, ARM, skirt_w, M["coat"], 0.5)
P(flap)

# belt: leather band with brass buckle and keeper
bx = prof(Z_BELT)
belt_rings = []
for z, e in ((Z_BELT - 0.05, 0.015), (Z_BELT - 0.05, 0.095), (Z_BELT + 0.05, 0.095), (Z_BELT + 0.05, 0.015)):
    belt_rings.append([skirt_pt(z, i / 40 * math.tau, e - 0.0, 0.0) for i in range(40)])
vs, fs = B.ring_faces(belt_rings, closed=True)
belt = B.obj_from("Belt", vs, fs, M["leather"])
B.orient_out(belt, (0, bx[2], Z_BELT))
B.finish_mod(belt, bevel=0.006)
B.rigid(belt, "hips", M["leather"], ARM)
P(belt)
fp = skirt_pt(Z_BELT, 0, 0.115, 0.0)
buckle = B.box("Buckle", (fp.x, fp.y - 0.01, Z_BELT), (0.11, 0.022, 0.085), mat=M["brass"], bevel=0.008)
B.rigid(buckle, "hips", M["brass"], ARM)
P(buckle)
tongue = B.box("BuckleBar", (fp.x, fp.y - 0.024, Z_BELT), (0.075, 0.012, 0.02), mat=M["dark"], bevel=0.004)
B.rigid(tongue, "hips", M["dark"], ARM)
P(tongue)

# ---- collar (tall, flared, open at the front), lapels
nh, nt = bone_axis("neck")
NC = (nh + nt) / 2
nb = B.slice_box(body, nh.z - 0.02, nt.z + 0.02, bones={"neck"})
NRX, NRY = (nb[1] - nb[0]) / 2, (nb[3] - nb[2]) / 2
print("BKIT_INFO neck", round(NRX, 3), round(NRY, 3), tuple(round(c, 3) for c in NC))
dxy = (nt - nh)
lean = dxy.y / dxy.z


def collar_pt(z, a, flare):
    cy = NC.y + (z - NC.z) * lean
    rx = NRX + 0.075 + flare
    ry = NRY + 0.07 + flare
    wob = 1 + 0.05 * math.sin(5 * a + 1.0)
    return Vector((rx * wob * math.sin(a), cy - ry * wob * math.cos(a) * 0.9, z))


rings = []
for z, fl in ((nh.z - 0.10, 0.03), (nh.z + 0.0, 0.0), (nh.z + 0.07, 0.02), (nh.z + 0.125, 0.07), (nh.z + 0.14, 0.075)):
    pts = []
    for i in range(28):
        a = math.radians(34) + (math.tau - math.radians(68)) * i / 27
        pts.append(collar_pt(z, a, fl))
    rings.append(pts)
vs, fs = B.ring_faces(rings, closed=False)
collar = B.obj_from("Collar", vs, fs, M["coat"])
B.orient_out(collar, (0, NC.y, NC.z))
B.finish_mod(collar, solid=0.022, offset=1.0, smooth_iter=1)
B.rigid(collar, "chest", M["coat"], ARM)
P(collar)

# lapels, projected onto the bodice surface
bv = B.bvh_of_obj(BODICE)


def project(p, extra=0.0):
    hit = bv.ray_cast(Vector((p.x, -1.2, p.z)), Vector((0, 1, 0)))
    if hit[0] is None:
        return p
    return Vector((p.x, hit[0].y - extra, p.z))


def lapel(s):
    c00, c10 = Vector((0.07 * s, 0, nh.z - 0.02)), Vector((0.30 * s, 0, nh.z - 0.10))
    c01, c11 = Vector((0.02 * s, 0, 1.62)), Vector((0.22 * s, 0, 1.80))
    rows = []
    for j in range(9):
        v = j / 8
        row = []
        for i in range(7):
            u = i / 6
            p = c00.lerp(c10, u).lerp(c01.lerp(c11, u), v)
            row.append(project(p, -0.012 - 0.03 * u * (1 - v * 0.7)))
        rows.append(row)
    vs, fs = B.ring_faces(rows, closed=False)
    return B.obj_from("Lapel" + ("L" if s > 0 else "R"), vs, fs, M["coat"])


for sd in (1, -1):
    lp = lapel(sd)
    if sum(p.normal.y * p.area for p in lp.data.polygons) > 0:
        bm = bmesh.new(); bm.from_mesh(lp.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(lp.data); bm.free()
    B.finish_mod(lp, solid=0.02, offset=1.0, bevel=0.004)
    B.rigid(lp, "chest", M["coat"], ARM)
    P(lp)

# ---- buttons (double breasted, brass), sleeve cuffs, pocket flaps
for r in range(3):
    for sd in (-1, 1):
        p = skirt_pt(1.40 - r * 0.20, sd * 0.20, 0.035, 0.6)
        b = B.dome(f"BtnS{r}{sd}", (p.x, p.y - 0.004, p.z), 0.028, (1, 1, 0.5), rot=(math.pi / 2, 0, 0), segs=8)
        B.weighted(b, ARM, skirt_w, M["brass"], 0.5)
        P(b)
for r in range(3):
    for sd in (-1, 1):
        q = project(Vector((sd * (0.13 - 0.01 * r), 0, 1.60 + r * 0.12)), -0.03)
        b = B.dome(f"BtnU{r}{sd}", (q.x, q.y - 0.002, q.z), 0.026, (1, 1, 0.5), rot=(math.pi / 2, 0, 0), segs=8)
        B.rigid(b, "chest", M["brass"], ARM)
        P(b)

for nm in ("L", "R"):
    fa, fb = bone_axis(f"forearm.{nm}")
    d = (fb - fa).normalized()
    c0 = fb - d * 0.11
    cuff = B.cyl_along(f"Cuff{nm}", c0, fb + d * 0.03, 0.115, 0.108, verts=20, cap=False)
    B.finish_mod(cuff, solid=0.014, offset=1.0, bevel=0.004)
    B.orient_out(cuff, (fa + fb) / 2)
    B.rigid(cuff, f"forearm.{nm}", M["coat"], ARM)
    P(cuff)
    for k in range(2):
        bt = B.dome(f"CuffBtn{nm}{k}", c0 + d * (0.03 + 0.05 * k) + Vector((0, -0.112, 0)), 0.016, (1, 1, 0.5), rot=(math.pi / 2, 0, 0), segs=8)
        B.rigid(bt, f"forearm.{nm}", M["brass"], ARM)
        P(bt)

for sd in (1, -1):  # pocket flaps on the skirt, slanted
    a = sd * 0.62
    p = skirt_pt(1.17, a, 0.028, 0.5)
    fl = B.box(f"Pocket{sd}", (p.x, p.y, p.z), (0.21, 0.016, 0.085), rot=(0.12, 0, -a * 0.9 + sd * 0.12), mat=M["coat"], bevel=0.004)
    B.weighted(fl, ARM, skirt_w, M["coat"], 0.5)
    P(fl)

if os.environ.get("STOP") == "coat":
    dev_render("t_coat.png")
    sys.exit(0)

# ================================================================ trousers, boots, gloved left hand
LEGSET = {"hips", "thigh.L", "thigh.R", "shin.L", "shin.R"}
trou = B.cut_shell(body, "Trousers", lambda co, b: b in LEGSET and 0.24 < co.z < 1.5, 0.045, 0.014, M["trousers"], smooth_iter=2)
B.dec(trou, 1100)
P(trou)

for nm in ("L", "R"):
    boot = B.cut_shell(body, f"Boot{nm}", lambda co, b, nm=nm: (b == f"foot.{nm}") or (b == f"shin.{nm}" and co.z < 0.30),
                       0.04, 0.012, M["leather"], smooth_iter=1)
    P(boot)
    hull = B.hull2d([(p.x, p.y) for p in B.verts_where(body, lambda co, b, nm=nm: b == f"foot.{nm}" and co.z < 0.17)])
    hull = B.resample_poly(hull, 28)
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)

    def grow(pad):
        out = []
        for p in hull:
            d = Vector((p[0] - cx, p[1] - cy, 0))
            d.normalize()
            out.append((p[0] + d.x * pad, p[1] + d.y * pad))
        return out
    rings = []
    for z, pad in ((0.0, 0.026), (0.008, 0.052), (0.052, 0.054), (0.068, 0.04)):
        rings.append([Vector((q[0], q[1], z)) for q in grow(pad)])
    vs, fs = B.ring_faces(rings, closed=True, cap_first=True, cap_last=True)
    sole = B.obj_from(f"Sole{nm}", vs, fs, M["sole"])
    B.orient_out(sole, (cx, cy, 0.03))
    B.finish_mod(sole, bevel=0.004)
    B.rigid(sole, f"foot.{nm}", M["sole"], ARM)
    P(sole)
    # laces: short cross bars along the instep
    fh, ft = bone_axis(f"foot.{nm}")
    bt = B.bvh_of_obj(boot)
    ax = Vector((ft.x - fh.x, ft.y - fh.y, 0)).normalized()
    side = Vector((-ax.y, ax.x, 0))
    for k in range(5):
        pt = fh + (ft - fh) * (0.08 + 0.17 * k)
        pt.z = 0
        hit = bt.ray_cast(Vector((pt.x, pt.y, 1.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        c = hit[0] + Vector((0, 0, 0.006))
        r = B.cyl_along(f"Lace{nm}{k}", c - side * 0.055, c + side * 0.055, 0.0085, verts=6)
        B.rigid(r, f"foot.{nm}", M["cloth"], ARM)
        P(r)

glove = B.cut_shell(body, "GloveL", lambda co, b: b == "hand.L", 0.012, 0.006, M["glove"], smooth_iter=0)
B.dec(glove, 1900)
P(glove)

# head wrap: dark cloth over skull and neck so no skin shows anywhere
hw = B.cut_shell(body, "HeadWrap", lambda co, b: b in ("head", "neck"), lambda co: 0.032 if co.z < 2.17 else 0.012, 0.012,
                 M["cloth"], smooth_iter=2)
B.dec(hw, 800)
P(hw)

if os.environ.get("STOP") == "lower":
    dev_render("t_lower.png")
    sys.exit(0)

# ================================================================ head: cap, badge, steel face plate, glow
hh_, ht_ = bone_axis("head")
HF = B.Frame(hh_, ht_ - hh_)
hv = B.verts_where(body, lambda co, b: b == "head")
hl = [HF.l(p) for p in hv]
eyes = [HF.l(v.co) for v in body.data.vertices if v.index >= body["eye_start"]]
LU_EYE = sum(e[2] for e in eyes) / len(eyes)
LU_TOP = max(p[2] for p in hl)
LU_CHIN = min(p[2] for p in hl)
print("BKIT_INFO head frame eye", round(LU_EYE, 3), "top", round(LU_TOP, 3), "chin", round(LU_CHIN, 3))


def hslice(lu, tol=0.02):
    pts = [p for p in hl if abs(p[2] - lu) < tol]
    return (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts))


def cap_pt(lu, a, grow, cx_cf=None):
    x0, x1, f0, f1 = hslice(min(lu, LU_TOP - 0.045))
    cx, cf = (x0 + x1) / 2, (f0 + f1) / 2
    rx, rf = (x1 - x0) / 2 + grow, (f1 - f0) / 2 + grow
    return HF.w(cx + rx * math.sin(a), cf + rf * math.cos(a), lu)


LU_B0 = LU_EYE + 0.075
LU_B1 = LU_B0 + 0.08
CH = LU_TOP + 0.05 - LU_B1
CAPG = 0.038   # distance of the cap above the cloth wrap


def cap_rings():
    spec = [(LU_B0 - 0.012, 0.0 + CAPG, 0.0), (LU_B1 - 0.01, CAPG + 0.002, 0.0), (LU_B1 + 0.0, CAPG + 0.006, 0.0),
            (LU_B1 + 0.22 * CH, CAPG + 0.036, 0.0), (LU_B1 + 0.55 * CH, CAPG + 0.055, 0.0), (LU_B1 + 0.9 * CH, CAPG + 0.045, 0.0),
            (LU_B1 + CH, CAPG + 0.030, 0.0)]
    rings = []
    n = 36
    for lu, g, _ in spec:
        ring = []
        for i in range(n):
            a = i / n * math.tau
            back = 0.03 * B.sm01(0.0, 1.0, -math.cos(a)) if lu < LU_B1 else 0.0  # rim sits lower at the back
            ring.append(cap_pt(lu - back, a, g))
        rings.append(ring)
    return rings


cr = cap_rings()
vs, fs = B.ring_faces(cr, closed=True, cap_last=True)
# sagging soft top: pull the top centre down a touch by adding a centre vertex fan
cap = B.obj_from("CapCrown", vs, fs, M["cloth"])
B.orient_out(cap, HF.w(0, 0, (LU_B0 + LU_TOP) / 2))
B.finish_mod(cap, solid=0.012, offset=1.0, bevel=0.005, smooth_iter=1)
B.rigid(cap, "head", M["cap"], ARM)
P(cap)

# peak (visor): a curved, drooping leather shield glued to the front of the band
rows = []
for j in range(5):
    v = j / 4
    row = []
    for i in range(21):
        a = math.radians(-74 + 148 * i / 20)
        base = cap_pt(LU_B0 + 0.0, a, CAPG - 0.002)
        L = (0.115 * max(0.0, math.cos(a)) ** 0.7 + 0.012) * v
        d = HF.x * math.sin(a) + HF.f * math.cos(a)
        p = base + d * L - HF.u * (0.01 + 0.03 * v ** 1.5 * max(0.3, math.cos(a)))
        row.append(p)
    rows.append(row)
vs, fs = B.ring_faces(rows, closed=False)
peak = B.obj_from("CapPeak", vs, fs, M["peak"])
if sum(p.normal.dot(HF.u) * p.area for p in peak.data.polygons) < 0:
    bm = bmesh.new(); bm.from_mesh(peak.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(peak.data); bm.free()
B.finish_mod(peak, solid=0.014, offset=-1.0, bevel=0.004)
B.rigid(peak, "head", M["peak"], ARM)
P(peak)
# gold-braid band over the peak and a badge on the front of the band
fr = cap_pt(LU_B0 + 0.045, 0.0, CAPG + 0.004)
for k, (r_, m_, dz_) in enumerate(((0.040, "brass", 0.0), (0.025, "leather", 0.006))):
    badge = B.cyl_along(f"Badge{k}", fr - HF.f * 0.0 + HF.f * (0.004 + dz_), fr + HF.f * (0.014 + dz_), r_, r_ * 0.9, verts=14)
    B.rigid(badge, "head", M[m_], ARM)
    P(badge)
star = []
for i in range(10):
    rr = 0.052 if i % 2 == 0 else 0.03
    a = i / 10 * math.tau
    star.append(fr + HF.f * 0.003 + HF.x * rr * math.sin(a) + HF.u * rr * math.cos(a))
bm = bmesh.new()
vv = [bm.verts.new(p) for p in star]
bm.faces.new(vv)
sm = bpy.data.meshes.new("BadgeStar")
bm.to_mesh(sm)
bm.free()
bst = bpy.data.objects.new("BadgeStar", sm)
bpy.context.collection.objects.link(bst)
B.finish_mod(bst, solid=0.008, offset=1.0, bevel=0.002)
B.orient_out(bst, fr - HF.f * 0.2)
B.rigid(bst, "head", M["brass"], ARM)
P(bst)
for sd in (-1, 1):
    bt = B.dome(f"CapBtn{sd}", cap_pt(LU_B0 + 0.04, sd * math.radians(78), CAPG + 0.006), 0.014, (1, 1, 0.7), rot=(0, sd * math.pi / 2, 0), segs=8)
    B.rigid(bt, "head", M["brass"], ARM)
    P(bt)

# ---- steel face plate: dented, riveted, two punched holes
headbv = B.bvh_of(body, lambda co, b: b in ("head",))
NC_, NR_ = 28, 13
LU0, LU1 = LU_CHIN + 0.025, LU_B0 - 0.004
TH = math.radians(78)


def radial(lu, th):
    x0, x1, f0, f1 = hslice(lu, 0.03)
    c = HF.w((x0 + x1) / 2, (f0 + f1) / 2, lu)
    d = HF.x * math.sin(th) + HF.f * math.cos(th)
    hit = headbv.ray_cast(c + d * 0.6, -d)
    return c, d, (hit[0] - c).dot(d) if hit[0] is not None else 0.1


grid = [[radial(LU0 + (LU1 - LU0) * j / (NR_ - 1), -TH + 2 * TH * i / (NC_ - 1)) for i in range(NC_)] for j in range(NR_)]
rad = [[g[2] for g in row] for row in grid]
for _ in range(5):  # soften nose and brow detail so it reads as a stamped plate, not a mask
    new = [r[:] for r in rad]
    for j in range(NR_):
        for i in range(NC_):
            nb_ = [rad[jj][ii] for jj in (j - 1, j, j + 1) for ii in (i - 1, i, i + 1) if 0 <= jj < NR_ and 0 <= ii < NC_]
            new[j][i] = max(rad[j][i] * 0.5 + 0.5 * sum(nb_) / len(nb_), rad[j][i] - 0.012)
    rad = new
HOLE = [(-0.042, LU_EYE - 0.012), (0.042, LU_EYE - 0.012)]
pg = []
for j in range(NR_):
    row = []
    for i in range(NC_):
        c, d, _ = grid[j][i]
        th = -TH + 2 * TH * i / (NC_ - 1)
        dent = 0.006 * math.sin(i * 1.7 + j * 0.9) * math.sin(j * 2.3 - i * 0.6) + 0.004 * math.sin(i * 0.8 + 1.3)
        edge = B.sm01(0, 2, min(i, NC_ - 1 - i, j, NR_ - 1 - j))  # rolled edges stay close to the head
        row.append(c + d * (rad[j][i] + 0.046 + dent * edge))
    pg.append(row)
vs, fs = B.ring_faces(pg, closed=False)
plate = B.obj_from("FacePlate", vs, fs, M["plate"])
B.weld(plate)
if sum(p.normal.dot(HF.f) * p.area for p in plate.data.polygons) < 0:
    bm = bmesh.new(); bm.from_mesh(plate.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(plate.data); bm.free()
B.finish_mod(plate, solid=0.012, offset=-1.0, bevel=0.003)
for hx, hz in HOLE:  # round punched holes: boolean cut
    ctr_ = HF.w(hx, 0.0, hz)
    cut = B.cyl_along("HoleCut", ctr_ + HF.f * 0.3, ctr_ - HF.f * 0.05, 0.0245, verts=18)
    bm_ = plate.modifiers.new("Hole", "BOOLEAN")
    bm_.object = cut
    bm_.operation = "DIFFERENCE"
    bm_.solver = "EXACT"
    bkit.active(plate)
    bpy.ops.object.modifier_apply(modifier=bm_.name)
    bpy.data.objects.remove(cut, do_unlink=True)
B.rigid(plate, "head", M["plate"], ARM)
P(plate)
PLATE_BV = B.bvh_of_obj(plate)
for k in range(5):  # rivets round the edge
    th = -TH * 0.92 + 2 * TH * 0.92 * k / 4
    for lu in (LU0 + 0.012, LU1 - 0.012):
        j = 0 if lu < (LU0 + LU1) / 2 else NR_ - 1
        i = int(round((th + TH) / (2 * TH) * (NC_ - 1)))
        p = pg[j][i] + (HF.u * (0.012 if j == 0 else -0.012))
        rv = B.dome(f"PlateRivet{k}{j}", p, 0.0075, (1, 1, 1), segs=6)
        B.rigid(rv, "head", M["brass"], ARM)
        P(rv)
# strap round the back of the head holding the plate on
rings = []
for lu, g in ((LU_CHIN + 0.075, 0.034), (LU_CHIN + 0.075, 0.046), (LU_CHIN + 0.105, 0.046), (LU_CHIN + 0.105, 0.034)):
    rings.append([cap_pt(lu, math.radians(70) + (math.tau - math.radians(140)) * i / 19, g) for i in range(20)])
vs, fs = B.ring_faces(rings, closed=False)
strap = B.obj_from("HeadStrap", vs, fs, M["leather"])
B.orient_out(strap, HF.w(0, 0, LU_CHIN + 0.09))
B.finish_mod(strap, bevel=0.003)
B.rigid(strap, "head", M["leather"], ARM)
P(strap)
# glow: two discs just behind the holes (separate unbaked emissive mesh)
for k, (hx, hz) in enumerate(HOLE):
    best = min(((HF.l(pg[j][i])[0] - hx) ** 2 + (HF.l(pg[j][i])[2] - hz) ** 2, j, i) for j in range(NR_) for i in range(NC_))
    ctr = pg[best[1]][best[2]]
    g = B.cyl_along(f"PunchGlow{k}", ctr + HF.f * -0.020, ctr + HF.f * -0.008, 0.034, 0.034, verts=14)
    B.orient_out(g, ctr - HF.f * 0.3)
    B.rigid(g, "head", M["glow"], ARM)
    GLOW.append(g)

if os.environ.get("STOP") == "head":
    bkit.light_studio()
    C.render_closeup(os.path.join(DEV, "t_face.png"), tuple(HF.w(0, 0.03, 0.07)), (0.3, -1, -0.3), dist=0.9)
    sys.exit(0)

# ================================================================ armour: booth plates, straps, turnstile arm, tickets
add_chest = bone_axis("chest")
_jh, _jt = bone_axis("hand.R")
B.add_bone(ARM, "plate_chest", (0, -0.34, 1.80), (0, -0.34, 2.02), "chest")
for sd, nm in ((1, "L"), (-1, "R")):
    jh, jt = bone_axis(f"upper_arm.{nm}")
    B.add_bone(ARM, f"plate_shoulder.{nm}", jh + Vector((0.02 * sd, 0, 0.05)), jh + Vector((0.02 * sd, 0, 0.17)), f"upper_arm.{nm}")


def smooth_grid(g, n=5, keep=0.0):
    R, Cn = len(g), len(g[0])
    for _ in range(n):
        new = [r[:] for r in g]
        for j in range(R):
            for i in range(Cn):
                nb_ = [g[jj][ii] for jj in (j - 1, j, j + 1) for ii in (i - 1, i, i + 1) if 0 <= jj < R and 0 <= ii < Cn]
                new[j][i] = g[j][i] * keep + (1 - keep) * sum(nb_) / len(nb_)
        g = new
    return g


def plate_from_grid(name, pts, kill_fn, thick, mat, bone, bev=0.004):
    vs, fs = B.ring_faces(pts, closed=False)
    keep = []
    for f in fs:
        cen = sum((Vector(vs[i]) for i in f), Vector()) / 4
        if not kill_fn(cen):
            keep.append(f)
    o = B.obj_from(name, vs, keep, mat)
    return o


# chest plate: projected on the bodice front, smoothed flat, corners chamfered
CP_Z0, CP_Z1, CP_HW = 1.58, 2.02, 0.31
NU, NV = 17, 13
ys = []
for j in range(NV):
    row = []
    for i in range(NU):
        x = -CP_HW + 2 * CP_HW * i / (NU - 1) * (1 - 0.10 * j / (NV - 1))
        z = CP_Z0 + (CP_Z1 - CP_Z0) * j / (NV - 1)
        h = bv.ray_cast(Vector((x, -1.2, z)), Vector((0, 1, 0)))
        row.append(h[0].y if h[0] is not None else -0.4)
    ys.append(row)
ys = smooth_grid(ys, 6, 0.1)
cp = []
for j in range(NV):
    row = []
    for i in range(NU):
        x = -CP_HW + 2 * CP_HW * i / (NU - 1) * (1 - 0.10 * j / (NV - 1)) * 1.0
        z = CP_Z0 + (CP_Z1 - CP_Z0) * j / (NV - 1)
        dent = 0.006 * math.sin(i * 1.3 + j * 0.7) * math.sin(j * 1.9 - i * 0.5) + 0.004 * math.sin(i * 0.6 + 2 * j * 0.3)
        row.append(Vector((x, ys[j][i] - 0.034 - dent, z)))
    cp.append(row)


def chamfer(c):
    u = (c.x / CP_HW)
    v = (c.z - CP_Z0) / (CP_Z1 - CP_Z0)
    return (abs(u) > 0.74 and v > 0.78 + (1 - abs(u)) * 0.0 and abs(u) + v > 1.64) or (abs(u) > 0.80 and v < 0.12 and abs(u) - v > 0.72)


cpo = plate_from_grid("ChestPlate", cp, chamfer, 0.02, M["steel"], "plate_chest")
B.weld(cpo)
if sum(p.normal.y * p.area for p in cpo.data.polygons) > 0:
    bm = bmesh.new(); bm.from_mesh(cpo.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(cpo.data); bm.free()
B.finish_mod(cpo, solid=0.024, offset=1.0, bevel=0.004)
B.rigid(cpo, "plate_chest", M["steel"], ARM, 0.5)
P(cpo)
CPBV = B.bvh_of_obj(cpo)


def on_plate(x, z, lift=0.0):
    h = CPBV.ray_cast(Vector((x, -1.5, z)), Vector((0, 1, 0)))
    return Vector((x, (h[0].y if h[0] is not None else -0.4) - lift, z))


for k in range(14):  # rivets round the border and across the middle
    if k < 10:
        a = k / 10 * math.tau
        x, z = 0.255 * math.cos(a), 1.80 + 0.185 * math.sin(a)
    else:
        x, z = (-0.11, 0.11, -0.11, 0.11)[k - 10], (1.64, 1.64, 1.96, 1.96)[k - 10]
    if chamfer(Vector((x, 0, z))):
        continue
    p = on_plate(x, z, 0.0)
    rv = B.dome(f"ChestRivet{k}", p + Vector((0, -0.003, 0)), 0.014, (1, 1, 0.55), rot=(math.pi / 2, 0, 0), segs=8)
    B.rigid(rv, "plate_chest", M["dark"], ARM)
    P(rv)

# stencil paint remains: a big character and a number, plus faded hazard stripes
fnt = bpy.data.fonts.load("/System/Library/Fonts/STHeiti Medium.ttc")
for txt, size, zc, xc in (("止", 0.25, 1.86, 0.0), ("07", 0.10, 1.68, 0.0)):
    bpy.ops.object.text_add(location=(0, 0, 0))
    tobj = bpy.context.active_object
    tobj.data.body = txt
    tobj.data.font = fnt
    tobj.data.size = size
    tobj.data.align_x = "CENTER"
    tobj.data.align_y = "CENTER"
    tobj.data.resolution_u = 2
    tobj.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.convert(target="MESH")
    tm = bpy.context.active_object
    tm.name = "Stencil_" + txt
    bkit.active(tm)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for v in tm.data.vertices:
        v.co = Vector((v.co.x + xc, 0, v.co.z + zc))
    bm = bmesh.new(); bm.from_mesh(tm.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(tm.data); bm.free()
    for v in tm.data.vertices:
        v.co = on_plate(v.co.x, v.co.z, 0.0) + Vector((0, -0.0305, 0))
    # plate surface is at the solidified front: ray hit is on the front face already
    for v in tm.data.vertices:
        v.co.y += 0.0305 - 0.0035
    if sum(p.normal.y * p.area for p in tm.data.polygons) > 0:
        bm = bmesh.new(); bm.from_mesh(tm.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(tm.data); bm.free()
    tm.data.materials.clear()
    B.rigid(tm, "plate_chest", M["paint"], ARM)
    P(tm)
for k in range(5):  # hazard stripes along the lower edge
    x0 = -0.22 + k * 0.095
    quad = []
    for (xx, zz) in ((x0, 1.605), (x0 + 0.045, 1.605), (x0 + 0.045 + 0.05, 1.655), (x0 + 0.05, 1.655)):
        quad.append((xx, zz))
    rows = []
    for jj in range(3):
        row = []
        for ii in range(3):
            a_ = Vector(quad[0]).lerp(Vector(quad[3]), jj / 2)
            b_ = Vector(quad[1]).lerp(Vector(quad[2]), jj / 2)
            q = a_.lerp(b_, ii / 2)
            row.append(on_plate(q.x, q.y, 0.0) + Vector((0, 0.0305 - 0.0032, 0)) * 0 + Vector((0, -0.0032 + 0.0, 0)))
        rows.append(row)
    vs, fs = B.ring_faces(rows, closed=False)
    st = B.obj_from(f"Hazard{k}", vs, fs, M["paint"])
    if sum(p.normal.y * p.area for p in st.data.polygons) > 0:
        bm = bmesh.new(); bm.from_mesh(st.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(st.data); bm.free()
    B.rigid(st, "plate_chest", M["paint"], ARM)
    P(st)

# straps round the chest, behind the plate
for z in (1.62, 1.96):
    bx_ = B.slice_box(body, z - 0.03, z + 0.03, bones={"spine", "chest", "hips"}, xmax=0.42)
    cxs, rxs, cys, rys = (bx_[0] + bx_[1]) / 2, (bx_[1] - bx_[0]) / 2, (bx_[2] + bx_[3]) / 2, (bx_[3] - bx_[2]) / 2
    rings = []
    for dz, pad in ((-0.035, 0.083), (-0.035, 0.093), (0.035, 0.093), (0.035, 0.083)):
        rings.append([Vector((cxs + (rxs + pad) * math.sin(i / 40 * math.tau), cys - (rys + pad) * math.cos(i / 40 * math.tau), z + dz)) for i in range(40)])
    vs, fs = B.ring_faces(rings, closed=True)
    sr = B.obj_from(f"ChestStrap{z}", vs, fs, M["leather"])
    B.orient_out(sr, (cxs, cys, z))
    B.finish_mod(sr, bevel=0.003)
    B.rigid(sr, "chest", M["leather"], ARM)
    P(sr)

# shoulder plates: curved pauldron-like booth plates over the deltoid, own bones
for sd, nm in ((1, "L"), (-1, "R")):
    jh, jt = bone_axis(f"upper_arm.{nm}")
    NU2, NV2 = 11, 9
    U0, U1 = 0.16, 0.66
    V0, V1 = -0.34, 0.02
    zs = []
    for j in range(NV2):
        row = []
        for i in range(NU2):
            x = sd * (U0 + (U1 - U0) * i / (NU2 - 1))
            y = V0 + (V1 - V0) * j / (NV2 - 1)
            h = bv.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)))
            row.append(h[0].z if h[0] is not None else jh.z - 0.1)
        zs.append(row)
    zs = smooth_grid(zs, 5, 0.1)
    pts = []
    for j in range(NV2):
        row = []
        for i in range(NU2):
            u = i / (NU2 - 1)
            x = sd * (U0 + (U1 - U0) * u)
            y = V0 + (V1 - V0) * j / (NV2 - 1)
            drop = 0.16 * max(0.0, u - 0.55) ** 1.4 / 0.45 ** 0.4
            dent = 0.005 * math.sin(i * 1.5 + j * 0.8)
            row.append(Vector((x + sd * 0.02 * u, y, zs[j][i] + 0.03 - drop + dent)))
        pts.append(row)

    def kill_sh(c, sd=sd):
        u = (abs(c.x) - U0) / (U1 - U0)
        v = (c.y - V0) / (V1 - V0)
        return (u > 0.8 and (v < 0.14 or v > 0.86)) or (u < 0.12 and (v < 0.1 or v > 0.9))
    sp = plate_from_grid(f"ShoulderPlate{nm}", pts, kill_sh, 0.02, M["steel"], f"plate_shoulder.{nm}")
    B.weld(sp)
    if sum(p.normal.z * p.area for p in sp.data.polygons) < 0:
        bm = bmesh.new(); bm.from_mesh(sp.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(sp.data); bm.free()
    B.finish_mod(sp, solid=0.024, offset=1.0, bevel=0.004)
    B.rigid(sp, f"plate_shoulder.{nm}", M["steel"], ARM)
    P(sp)
    spb = B.bvh_of_obj(sp)
    for k in range(6):
        u = (0.22, 0.5, 0.78)[k % 3]
        v = (0.2, 0.8)[k // 3]
        x = sd * (U0 + (U1 - U0) * u)
        y = V0 + (V1 - V0) * v
        h = spb.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)))
        if h[0] is None:
            continue
        rv = B.dome(f"ShRivet{nm}{k}", h[0] + Vector((0, 0, 0.003)), 0.014, (1, 1, 0.55), segs=8)
        B.rigid(rv, f"plate_shoulder.{nm}", M["dark"], ARM)
        P(rv)
    # leather strap round the upper arm below the plate
    pa = jh + (jt - jh) * 0.55
    d = (jt - jh).normalized()
    sr = B.cyl_along(f"ArmStrap{nm}", pa - d * 0.04, pa + d * 0.04, 0.165, 0.165, verts=20, cap=False)
    B.finish_mod(sr, solid=0.012, offset=1.0, bevel=0.003)
    B.orient_out(sr, pa)
    B.rigid(sr, f"upper_arm.{nm}", M["leather"], ARM)
    P(sr)

# turnstile arm across the back: steel tube on two bracket plates, flanged ends, faded paint bands
bvb = B.bvh_of_obj(BODICE)


def back_y(x, z):
    h = bvb.ray_cast(Vector((x, 1.5, z)), Vector((0, -1, 0)))
    return h[0].y if h[0] is not None else 0.2


pA = Vector((-0.86, 0, 1.40))
pB = Vector((0.90, 0, 2.28))
pA.y = back_y(pA.x * 0.7, pA.z) + 0.115
pB.y = back_y(pB.x * 0.7, pB.z) + 0.115
tube = B.cyl_along("TurnstileArm", pA, pB, 0.042, verts=14)
B.finish_mod(tube, bevel=0.004)
B.rigid(tube, "chest", M["rust"], ARM)
P(tube)
dtu = (pB - pA).normalized()
for t_, r_ in ((0.0, 0.07), (1.0, 0.07)):
    c = pA + (pB - pA) * t_
    fl = B.cyl_along(f"TFlange{t_}", c - dtu * 0.02, c + dtu * 0.02, r_, r_, verts=14)
    B.finish_mod(fl, bevel=0.004)
    B.rigid(fl, "chest", M["rust"], ARM)
    P(fl)
for t_ in (0.12, 0.2, 0.82, 0.9):  # chipped paint bands
    c = pA + (pB - pA) * t_
    bnd = B.cyl_along(f"TBand{t_}", c - dtu * 0.018, c + dtu * 0.018, 0.0455, 0.0455, verts=14, cap=False)
    B.rigid(bnd, "chest", M["paint"], ARM)
    P(bnd)
for t_ in (0.32, 0.68):  # bracket plates bolted to the back, with U-clamps
    c = pA + (pB - pA) * t_
    cx_, cz_ = c.x, c.z
    by_ = back_y(cx_, cz_)
    br = B.box(f"TBracket{t_}", (cx_, by_ + 0.06, cz_), (0.2, 0.025, 0.2), mat=M["steel"], bevel=0.006)
    B.rigid(br, "chest", M["steel"], ARM)
    P(br)
    for dx, dz in ((-0.07, -0.07), (0.07, -0.07), (-0.07, 0.07), (0.07, 0.07)):
        rv = B.dome(f"TBolt{t_}{dx}{dz}", (cx_ + dx, by_ + 0.075, cz_ + dz), 0.014, (1, 1, 0.6), rot=(-math.pi / 2, 0, 0), segs=8)
        B.rigid(rv, "chest", M["dark"], ARM)
        P(rv)
    cl = B.cyl_along(f"TClamp{t_}", c - dtu * 0.03, c + dtu * 0.03, 0.058, 0.058, verts=14, cap=False)
    B.finish_mod(cl, solid=0.01, bevel=0.003)
    B.orient_out(cl, c)
    B.rigid(cl, "chest", M["dark"], ARM)
    P(cl)

# paper tickets in bundles at the belt, each bundle on its own sway bone
random.seed(7)
for sd, nm in ((1, "L"), (-1, "R")):
    a = sd * 0.80
    pv = skirt_pt(Z_BELT - 0.05, a, 0.115, 0.0)
    B.add_bone(ARM, f"ticket.{nm}", pv, pv + Vector((0, 0, -0.22)), "hips")
    nrm = Vector((math.sin(a), -math.cos(a), 0))
    tang = Vector((math.cos(a), math.sin(a), 0))
    for k in range(8):
        w, h = 0.16, 0.30 + 0.03 * random.random()
        fan = (k - 3.5) * math.radians(8) * sd
        rows = []
        for j in range(4):
            v = j / 3
            row = []
            for i in range(3):
                u = (i / 2 - 0.5) * w
                curl = 0.035 * v * v + 0.01 * math.sin(v * 4 + k)
                row.append((u, -h * v, curl))
            rows.append(row)
        pts = []
        for row in rows:
            r2 = []
            for (u, v_, c_) in row:
                # rotate about the hang point: fan around the outward normal, then place
                ca, sa = math.cos(fan), math.sin(fan)
                uu, vv = u * ca - v_ * sa, u * sa + v_ * ca
                r2.append(pv + tang * uu + Vector((0, 0, 1)) * vv + nrm * (c_ + 0.012 * k))
            pts.append(r2)
        vs, fs = B.ring_faces(pts, closed=False)
        tk = B.obj_from(f"Ticket{nm}{k}", vs, fs, M["paper"] if k % 2 else M["paper2"])
        B.finish_mod(tk, solid=0.003, offset=0.0)
        B.rigid(tk, f"ticket.{nm}", M["paper"] if k % 2 else M["paper2"], ARM)
        P(tk)
        ink = B.box(f"Ink{nm}{k}", tuple(pv + tang * (math.sin(fan) * 0.0) + Vector((0, 0, -h * 0.35)) + nrm * (0.035 + 0.012 * k + 0.003)), (0.13, 0.0015, 0.04), mat=M["ink"])
        ink.rotation_euler = (0, 0, 0)
        B.rigid(ink, f"ticket.{nm}", M["ink"], ARM)
        P(ink)
    ring = B.dome(f"TicketRing{nm}", pv + nrm * 0.02, 0.028, (1, 1, 0.5), segs=10)
    B.rigid(ring, f"ticket.{nm}", M["brass"], ARM)
    P(ring)

if os.environ.get("STOP") == "armour":
    allp = [v.co for o in PARTS for v in o.data.vertices]
    print("BKIT_INFO parts bounds", [round(min(p[i] for p in allp), 2) for i in range(3)], [round(max(p[i] for p in allp), 2) for i in range(3)], "tris", sum(bkit.tri_count(o) for o in PARTS))
    for o in PARTS:
        zs_ = [(o.matrix_world @ v.co).z for v in o.data.vertices]
        ys_ = [(o.matrix_world @ v.co).y for v in o.data.vertices]
        print("BKIT_PART", o.name, bkit.tri_count(o), round(min(zs_), 2), round(min(ys_), 2), round(max(ys_), 2))
    sys.exit(0)

# ================================================================ right hand: the huge steel ticket punch
fa_, fb_ = bone_axis("forearm.R")
PU = (fb_ - fa_).normalized()
E1 = (Vector((1, 0, 0)) - PU * PU.x).normalized()
E2 = PU.cross(E1).normalized()
W0 = fb_.copy()


def pw(a, b, c):
    return W0 + PU * a + E1 * b + E2 * c


B.add_bone(ARM, "punch_jaw", pw(0.32, 0, 0), pw(0.52, 0, 0), "hand.R", roll_axis=E2)


def rot_ab(a, b, ang, ha=0.32, hb=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    da, db = a - ha, b - hb
    return ha + da * ca - db * sa, hb + da * sa + db * ca


def lbox(name, c, size, ang=0.0, pivot=(0.32, 0.0), pre=0.0, mat=None, bevel=0.006):
    """Box in punch-local coordinates (a along the forearm, b lateral, c hinge axis).
    pre: rotation of the box about its own centre; ang: rotation about the hinge pivot."""
    hs = [s_ / 2 for s_ in size]
    verts = []
    for sa in (-1, 1):
        for sb in (-1, 1):
            for sc in (-1, 1):
                da, db = sa * hs[0], sb * hs[1]
                cp, sp = math.cos(pre), math.sin(pre)
                a, b = c[0] + da * cp - db * sp, c[1] + da * sp + db * cp
                a, b = rot_ab(a, b, ang, *pivot)
                verts.append(pw(a, b, c[2] + sc * hs[2]))
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    o = B.obj_from(name, verts, faces, mat)
    B.orient_out(o)
    B.finish_mod(o, bevel=bevel)
    return o


OPEN = math.radians(8)
parts_fixed, parts_jaw = [], []
# gauntlet over the sleeve cuff, two leather straps up the forearm
gt = B.cyl_along("Gauntlet", pw(-0.10, 0, 0), pw(0.12, 0, 0), 0.126, 0.116, verts=22, cap=False)
B.orient_out(gt, W0)
B.finish_mod(gt, solid=0.018, offset=1.0, bevel=0.004)
parts_fixed.append(gt)
for a_ in (-0.10, 0.12):
    fl = B.cyl_along(f"GFlange{a_}", pw(a_ - 0.012, 0, 0), pw(a_ + 0.012, 0, 0), 0.138, 0.138, verts=22, cap=False)
    B.orient_out(fl, W0)
    B.finish_mod(fl, solid=0.016, offset=1.0, bevel=0.003)
    parts_fixed.append(fl)
for k, a_ in enumerate((-0.22, -0.34)):
    sr = B.cyl_along(f"PStrap{k}", pw(a_ - 0.03, 0, 0), pw(a_ + 0.03, 0, 0), 0.128, 0.128, verts=20, cap=False)
    B.orient_out(sr, W0)
    B.finish_mod(sr, solid=0.012, offset=1.0, bevel=0.003)
    B.rigid(sr, "forearm.R", M["leather"], ARM)
    P(sr)
    bk = lbox(f"PBuckle{k}", (a_, 0, 0.145), (0.05, 0.045, 0.015), mat=M["brass"], bevel=0.003)
    B.rigid(bk, "forearm.R", M["brass"], ARM)
    P(bk)
# housing and rails
parts_fixed.append(lbox("PunchHousing", (0.17, 0, 0), (0.12, 0.16, 0.13), mat=M["dark"], bevel=0.012))
for sd in (-1, 1):
    parts_fixed.append(lbox(f"PunchRail{sd}", (0.0, sd * 0.07, 0.0), (0.34, 0.03, 0.2), mat=M["dark"], bevel=0.005))
# jaws: root + body + heavy head on each side, rotated open about the hinge
for sd in (1, -1):
    ang = sd * OPEN
    b0 = sd * 0.046
    target = parts_jaw if sd == 1 else parts_fixed
    target.append(lbox(f"JawRoot{sd}", (0.25, b0, 0), (0.17, 0.075, 0.1), ang=ang, mat=M["dark"], bevel=0.008))
    target.append(lbox(f"JawBody{sd}", (0.43, b0, 0), (0.22, 0.07, 0.1), ang=ang, mat=M["dark"], bevel=0.008))
    target.append(lbox(f"JawHead{sd}", (0.565, b0 - sd * 0.006, 0), (0.11, 0.1, 0.12), ang=ang, mat=M["dark"], bevel=0.01))
    target.append(lbox(f"JawEdge{sd}", (0.585, b0 - sd * 0.034, 0), (0.05, 0.03, 0.085), ang=ang, pre=-sd * 0.5, mat=M["dark"], bevel=0.005))


def jaw_pt(a, b, c, sd):
    a2, b2 = rot_ab(a, b, sd * OPEN)
    return pw(a2, b2, c)


# punch pin on the + jaw, die ring on the - jaw
pin_a = 0.57
pin = B.cyl_along("PunchPin", jaw_pt(pin_a, 0.0, 0, 1), jaw_pt(pin_a, -0.032, 0, 1), 0.024, 0.017, verts=10)
B.finish_mod(pin, bevel=0.002)
tipc = B.cyl_along("PunchPinTip", jaw_pt(pin_a, -0.032, 0, 1), jaw_pt(pin_a, -0.046, 0, 1), 0.017, 0.006, verts=10)
parts_jaw += [pin, tipc]
rings = []
for rr, tt in ((0.036, 0.0), (0.036, 0.012), (0.019, 0.012), (0.019, 0.0)):
    rings.append([jaw_pt(pin_a + rr * math.cos(i / 14 * math.tau), 0.0025 + tt, rr * math.sin(i / 14 * math.tau), -1) for i in range(14)])
vs, fs = B.ring_faces(rings, closed=True)
die = B.obj_from("PunchDie", vs, fs, M["dark"])
B.orient_out(die, jaw_pt(pin_a, 0.0025, 0, -1))
B.finish_mod(die, bevel=0.002)
parts_fixed.append(die)
# hinge bolt, nut and washers
H_ = (0.32, 0.0)
bolt = B.cyl_along("HingeBolt", pw(H_[0], 0, -0.085), pw(H_[0], 0, 0.085), 0.022, verts=12)
hexh = B.cyl_along("BoltHead", pw(H_[0], 0, 0.052), pw(H_[0], 0, 0.078), 0.05, 0.05, verts=6)
B.finish_mod(hexh, bevel=0.004)
nut = B.cyl_along("BoltNut", pw(H_[0], 0, -0.078), pw(H_[0], 0, -0.052), 0.05, 0.05, verts=6)
B.finish_mod(nut, bevel=0.004)
wsh = B.cyl_along("BoltWasher", pw(H_[0], 0, 0.046), pw(H_[0], 0, 0.054), 0.06, 0.06, verts=16)
parts_fixed += [bolt, hexh, nut, wsh]
for o in parts_fixed:
    B.rigid(o, "hand.R", M["dark"] if o.name not in ("BoltHead", "BoltNut") else M["steel"], ARM)
    P(o)
for o in parts_jaw:
    B.rigid(o, "punch_jaw", M["dark"], ARM)
    P(o)
# rivets on the housing
for k in range(4):
    sd = (-1, 1)[k % 2]
    rv = B.dome(f"PunchRivet{k}", pw(0.15 + 0.05 * (k // 2), sd * 0.04, 0.07), 0.013, (1, 1, 0.6), segs=8)
    B.rigid(rv, "hand.R", M["steel"], ARM)
    P(rv)

if os.environ.get("STOP") == "punch":
    bkit.light_studio()
    C.render_closeup(os.path.join(DEV, "t_punch.png"), tuple(pw(0.25, 0, 0)), (-0.9, -0.8, 0.1), dist=1.6)
    sys.exit(0)

# ================================================================ previews
def shots(tag):
    C.reset(ARM)
    pre = os.path.join(C.RENDERS, f"ch3_ticket_{tag}")
    B.studio_shots(pre, (0, -0.05, 1.32), 5.9, tuple(HF.w(0, 0.03, 0.07)), (0.3, -1, -0.12), 1.15)
    B.dark_shot(os.path.join(C.RENDERS, f"ch3_ticket_dark_{tag}.png"), (0, 0, 1.3), cam_z=1.55, dist=6.0, energy=2200)


if STAGE == "preview":
    shots("preview")
    print("BKIT_DONE preview")
    sys.exit(0)
if STAGE == "devshots":
    shots("preview")
    sys.exit(0)

# ================================================================ game: decimate, join, bake, rig clips, export
C.reset(ARM)
shots("preview")
for o in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.objects.remove(body, do_unlink=True)
TARGETS = {"CoatBodice": 2000, "Boot": 520, "FacePlate": 1100, "CoatSkirt": 1400, "CapCrown": 450, "GloveL": 1300,
           "ChestPlate": 700, "Trousers": 650, "ShoulderPlate": 330, "CapPeak": 200, "HeadWrap": 300, "Sole": 200,
           "ChestStrap": 120, "Belt": 220, "Collar": 300, "Lapel": 150, "Cuff": 130, "ArmStrap": 100, "CoatFlap": 260,
           "TClamp": 80, "HeadStrap": 100, "BadgeStar": 60}
for o in PARTS:
    bkit.active(o)
    for m in list(o.modifiers):
        if m.type != "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=m.name)
    for k, t in TARGETS.items():
        if o.name.startswith(k):
            B.dec(o, t, 40)
            break
tot = sum(bkit.tri_count(o) for o in PARTS)
gtot = sum(bkit.tri_count(o) for o in GLOW)
print("BKIT_TRIS parts after targets", tot, "glow", gtot)
BUDGET = 14700
if tot + gtot > BUDGET:
    big = [o for o in PARTS if bkit.tri_count(o) > 150]
    small = sum(bkit.tri_count(o) for o in PARTS if o not in big)
    r = max(0.2, (BUDGET - gtot - small) / sum(bkit.tri_count(o) for o in big))
    for o in big:
        B.dec(o, bkit.tri_count(o) * r, 60)
    tot = sum(bkit.tri_count(o) for o in PARTS)
print("BKIT_TRIS parts", tot, "glow", gtot)
C.fix_metals(list(M.values()))
obj = bkit.join(PARTS, "Ticket")
C.skin_on(obj, ARM)
obj.parent = ARM
glow_obj = bkit.join(GLOW, "TicketGlow")
C.skin_on(glow_obj, ARM)
glow_obj.parent = ARM
B.swap_none_slots(obj)
print("BKIT_TRIS joined", bkit.tri_count(obj), "glow", bkit.tri_count(glow_obj))
bkit.bake_to_textures(obj, os.path.join(OUT, "textures"), size=1024, samples=8)
glow_obj.data.materials.clear()
glow_obj.data.materials.append(M["glow"])

AF = {n: B.best_sign(ARM, f"upper_arm.{n}", 0, f"hand.{n}", lambda p: p.y) for n in ("L", "R")}
TF = B.best_sign(ARM, "thigh.L", 0, "foot.L", lambda p: p.y)
SB = -B.best_sign(ARM, "shin.L", 0, "foot.L", lambda p: p.y)  # knee bends the foot backwards
JS = B.best_sign(ARM, "punch_jaw", 2, "punch_jaw", lambda p: p.x)
print("BKIT_SIGNS clips", AF, TF, SB, JS, FS)
sn = lambda t, amp, ph=0.0: amp * math.sin(math.tau * (t + ph))
f_ = FS

C.loop_clip(ARM, "Idle", 96, lambda t: {
    "spine": (f_ * (1.5 + sn(t, 1.2)), 0, sn(t, 0.8, 0.1)),
    "chest": (f_ * sn(t, 1.0, 0.15), sn(t, 1.5, 0.3), 0),
    "neck": (f_ * sn(t, 1.2, 0.3), sn(t, 3, 0.2), 0),
    "head": (f_ * sn(t, 1.0, 0.45), sn(t, 4, 0.1), 0),
    "upper_arm.L": (AF["L"] * sn(t, 1.5, 0.5), 0, sn(t, 0.8)),
    "upper_arm.R": (AF["R"] * sn(t, 1.2, 0.2), 0, 0),
    "punch_jaw": (0, 0, JS * (4 + sn(t, 4, 0.1))),
    "ticket.L": (sn(t, 4, 0.2), 0, sn(t, 3, 0.5)), "ticket.R": (sn(t, 4, 0.5), 0, sn(t, 3, 0.1)),
}, steps=12)


def move(t):
    s_, c_ = math.sin(math.tau * t), math.cos(math.tau * t)
    return {
        "hips": (0, sn(t, 4), sn(t, 2.5, 0.25)),
        "thigh.L": (TF * 20 * s_, 0, 0), "thigh.R": (-TF * 20 * s_, 0, 0),
        "shin.L": (SB * (max(0.0, -c_) * 32 + 4), 0, 0), "shin.R": (SB * (max(0.0, c_) * 32 + 4), 0, 0),
        "spine": (f_ * (3 + 2 * abs(s_)), -sn(t, 5), 0), "chest": (f_ * 2, sn(t, 4), sn(t, 2, 0.25)),
        "neck": (f_ * 3, sn(t, 3, 0.2), 0), "head": (f_ * (-1 + 2 * abs(c_)), sn(t, 3, 0.3), 0),
        "upper_arm.L": (AF["L"] * 14 * s_, 0, 0), "upper_arm.R": (-AF["R"] * 10 * s_, 0, 0),
        "forearm.R": (AF["R"] * 4, 0, 0),
        "punch_jaw": (0, 0, JS * (6 + sn(t, 5, 0.1))),
        "ticket.L": (sn(t, 8, 0.3), 0, sn(t, 6, 0.1)), "ticket.R": (sn(t, 8, 0.6), 0, sn(t, 6, 0.4)),
    }


C.loop_clip(ARM, "Move", 44, move, steps=8)


def charge(t):
    s_, c_ = math.sin(math.tau * t), math.cos(math.tau * t)
    return {
        "hips": (f_ * 6, sn(t, 6), 0),
        "thigh.L": (TF * 42 * s_, 0, 0), "thigh.R": (-TF * 42 * s_, 0, 0),
        "shin.L": (SB * (max(0.0, -c_) * 70 + 8), 0, 0), "shin.R": (SB * (max(0.0, c_) * 70 + 8), 0, 0),
        "spine": (f_ * 20, -sn(t, 7), 0), "chest": (f_ * 12, sn(t, 6), 0),
        "neck": (f_ * 10, 0, 0), "head": (f_ * 16, sn(t, 2), 0),
        "upper_arm.L": (AF["L"] * 45 * -s_, 0, 0), "upper_arm.R": (AF["R"] * (35 - 14 * s_), 0, 0),
        "forearm.R": (AF["R"] * 10, 0, 0),
        "punch_jaw": (0, 0, JS * (14 + sn(t, 8))),
        "ticket.L": (sn(t, 14, 0.4), 0, sn(t, 8)), "ticket.R": (sn(t, 14, 0.7), 0, sn(t, 8, 0.3)),
    }


C.loop_clip(ARM, "Charge", 22, charge, steps=8)
C.set_clip(ARM, "Attack", {
    "upper_arm.R": [(1, (0, 0, 0)), (12, (AF["R"] * -55, 0, -14)), (17, (AF["R"] * 75, 0, 8)), (22, (AF["R"] * 80, 0, 8)), (36, (0, 0, 0))],
    "forearm.R": [(1, (0, 0, 0)), (12, (AF["R"] * -20, 0, 0)), (17, (AF["R"] * 30, 0, 0)), (36, (0, 0, 0))],
    "punch_jaw": [(1, (0, 0, JS * 5)), (12, (0, 0, JS * 26)), (17, (0, 0, JS * 22)), (19, (0, 0, JS * -6)), (22, (0, 0, JS * -8)), (36, (0, 0, JS * 5))],
    "spine": [(1, (0, 0, 0)), (12, (f_ * -6, 14, 0)), (17, (f_ * 22, -16, 0)), (24, (f_ * 18, -10, 0)), (36, (0, 0, 0))],
    "chest": [(1, (0, 0, 0)), (12, (0, 12, 0)), (17, (f_ * 8, -14, 0)), (36, (0, 0, 0))],
    "head": [(1, (0, 0, 0)), (12, (f_ * -4, 0, 0)), (17, (f_ * 10, 0, 0)), (36, (0, 0, 0))],
    "thigh.L": [(1, (0, 0, 0)), (17, (TF * 14, 0, 0)), (36, (0, 0, 0))],
    "thigh.R": [(1, (0, 0, 0)), (17, (-TF * 8, 0, 0)), (36, (0, 0, 0))],
    "ticket.L": [(1, (0, 0, 0)), (17, (-12, 0, 6)), (28, (6, 0, -4)), (36, (0, 0, 0))],
    "ticket.R": [(1, (0, 0, 0)), (17, (-12, 0, -6)), (28, (6, 0, 4)), (36, (0, 0, 0))],
})
C.set_clip(ARM, "Stagger", {  # unkillable: he stumbles, catches himself, rises and carries on
    "spine": [(1, (0, 0, 0)), (12, (f_ * 28, 6, 0)), (22, (f_ * -8, -6, 0)), (34, (f_ * 8, 0, 0)), (56, (0, 0, 0))],
    "chest": [(1, (0, 0, 0)), (12, (f_ * 12, 0, 0)), (34, (f_ * 4, 0, 0)), (56, (0, 0, 0))],
    "neck": [(1, (0, 0, 0)), (12, (f_ * 12, 0, 0)), (56, (0, 0, 0))],
    "head": [(1, (0, 0, 0)), (12, (f_ * 18, 8, 0)), (22, (f_ * -8, -8, 0)), (56, (0, 0, 0))],
    "thigh.L": [(1, (0, 0, 0)), (12, (TF * 34, 0, 0)), (22, (TF * -10, 0, 0)), (34, (TF * 6, 0, 0)), (56, (0, 0, 0))],
    "thigh.R": [(1, (0, 0, 0)), (12, (-TF * 16, 0, 0)), (22, (-TF * 22, 0, 0)), (34, (-TF * 4, 0, 0)), (56, (0, 0, 0))],
    "shin.L": [(1, (0, 0, 0)), (12, (SB * 8, 0, 0)), (22, (SB * 46, 0, 0)), (34, (SB * 12, 0, 0)), (56, (0, 0, 0))],
    "upper_arm.R": [(1, (0, 0, 0)), (12, (AF["R"] * 35, 0, -10)), (22, (AF["R"] * -12, 0, 0)), (56, (0, 0, 0))],
    "upper_arm.L": [(1, (0, 0, 0)), (12, (AF["L"] * -30, 0, 14)), (34, (AF["L"] * 8, 0, 4)), (56, (0, 0, 0))],
    "punch_jaw": [(1, (0, 0, JS * 5)), (12, (0, 0, JS * 20)), (30, (0, 0, JS * 8)), (56, (0, 0, JS * 5))],
    "ticket.L": [(1, (0, 0, 0)), (12, (-16, 0, 8)), (30, (8, 0, -6)), (56, (0, 0, 0))],
    "ticket.R": [(1, (0, 0, 0)), (12, (-16, 0, -8)), (30, (8, 0, 6)), (56, (0, 0, 0))],
})
C.set_clip(ARM, "ArmorOff", {  # a magnet claw rips plating loose: a short recoil
    "spine": [(1, (0, 0, 0)), (4, (f_ * -14, 6, 0)), (10, (f_ * -4, 0, 0)), (16, (0, 0, 0))],
    "chest": [(1, (0, 0, 0)), (4, (f_ * -9, -8, 0)), (16, (0, 0, 0))],
    "head": [(1, (0, 0, 0)), (4, (f_ * -10, 10, 0)), (16, (0, 0, 0))],
    "upper_arm.R": [(1, (0, 0, 0)), (4, (AF["R"] * -26, 0, -16)), (16, (0, 0, 0))],
    "plate_chest": [(1, (0, 0, 0)), (4, (f_ * -6, 0, 0)), (8, (f_ * 3, 0, 0)), (16, (0, 0, 0))],
    "ticket.L": [(1, (0, 0, 0)), (4, (-14, 0, 5)), (16, (0, 0, 0))],
    "ticket.R": [(1, (0, 0, 0)), (4, (-14, 0, -5)), (16, (0, 0, 0))],
})

bkit.check([obj, glow_obj], max_tris=15000)
bkit.report([obj, glow_obj])
C.export_glb(GLB, ARM, [obj, glow_obj])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ticket.blend"))
for t in ARM.animation_data.nla_tracks:
    t.mute = True
shots("baked")
print("BKIT_DONE game")
