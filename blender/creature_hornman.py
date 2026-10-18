"""Mr. Hornman - an emaciated clown whose head is a gramophone horn.
Blind: hunts by sound. Teeth ring the inside of the bell."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, prim, seg, empty, apply_mods, displace, boolean, lathe, orient, smooth, subsurf,
                 mat_brass, mat_stripes, mat_teeth, mat_flesh, mat_simple, mat_plush,
                 mat_painted_wood, mat_rust, mat_bone, Mat, R)

FRAME = dict(height=3.1, center=(0, -0.2, 1.55))
SHOTS = [
    ("hero", "horror", (-1.9, -4.0, 1.0), (0, -0.25, 1.75), 30),
    ("studio", "studio", (3.4, -3.6, 1.8), (0, -0.2, 1.55), 35),
    ("face", "horror", (-0.55, -2.3, 2.1), (0, -0.8, 2.5), 40),
]


def ruff(name, loc, major, minor, pleats, m, parent, tilt=(0, 0, 0), amp=0.6):
    o = prim("torus", name, loc, (1, 1, 1), m=m, parent=parent, rot=tilt, major_radius=major,
             minor_radius=minor, major_segments=pleats * 8, minor_segments=12)
    for v in o.data.vertices:
        th = math.atan2(v.co.y, v.co.x)
        rho = math.hypot(v.co.x, v.co.y)
        off = rho - major
        k = 1 + amp * math.sin(pleats * th)
        rho2 = major + off * (0.6 + 0.4 * k) + minor * 0.5 * abs(math.sin(pleats * th))
        v.co.x = rho2 * math.cos(th)
        v.co.y = rho2 * math.sin(th)
        v.co.z = v.co.z * k
    return o


def build():
    suit = mat_stripes("ClownSuit", "#6a1216", "#bfb08c", scale=9.0, direction="X", distortion=0.25)
    brass_dark = mat_brass("HornBrassInner", dark=True)
    lace = mat_plush("Lace", "#d8d0bc", "#6e6656", "#efe8d6", stain="#4a3a28", scale=5)
    glove = mat_plush("Glove", "#d6d0c2", "#7a7464", "#f0ece0", stain="#3d2e20", scale=4)
    brass = mat_brass("HornBrass")
    inside = mat_simple("HornInside", "#0c0906", 0.6, metal=0.4)
    teeth = mat_teeth()
    flesh = mat_flesh("Throat", "#2e0408", "#080102", "#561218", vein_scale=22, sss=0.12)
    shoe = mat_painted_wood("ShoeLeather", "#8a0f12")
    pompom = mat_plush("Pompom", "#8a1a20", "#3a0808", "#c04048", scale=12)
    dead_skin = mat_simple("DeadFinger", "#6e6a62", 0.6, sss=0.1)
    nail = mat_simple("Nail", "#16120e", 0.3, coat=0.5)
    hat = mat_stripes("PartyHat", "#1c4a6a", "#d8c46a", scale=14, direction="Z")
    rust = mat_rust()
    rib_bone = mat_bone("RibBone", "#a89a80")
    dead_skin_body = mat_simple("DeadSkinBody", "#5e5a52", 0.55, sss=0.15, sss_radius=(0.6, 0.3, 0.2), sss_scale=0.02)

    root = empty("Hornman")
    random.seed(3)
    up = Vector((0, 0, 1))

    # ------------------------------------------------------------ body in a baggy suit
    S = Skel()
    pelvis = S.chain(None, [((0, 0.02, 1.25), (0.18, 0.14))])
    chest = S.chain(pelvis, [((0, 0.05, 1.5), (0.15, 0.12)), ((0, 0.03, 1.78), (0.22, 0.15))])
    upper = S.chain(chest, [((0, -0.05, 2.0), (0.21, 0.14))])
    S.chain(upper, [((0, -0.13, 2.13), 0.055)])
    for s in (-1, 1):
        S.chain(upper, [((0.25 * s, -0.03, 2.03), 0.085), ((0.33 * s, -0.08, 1.75), 0.075),
                        ((0.38 * s, -0.13, 1.48), 0.085), ((0.43 * s, -0.25, 1.2), 0.1),
                        ((0.45 * s, -0.31, 1.05), 0.12)])
        S.chain(pelvis, [((0.11 * s, 0.02, 1.15), 0.12), ((0.13 * s, -0.08, 0.68), 0.1),
                         ((0.14 * s, -0.02, 0.38), 0.11), ((0.14 * s, 0.0, 0.16), 0.13)])
    body = S.build("Suit", suit, subdiv=2, parent=root)
    displace(body, 0.03, 0.25)
    apply_mods(body)
    displace(body, 0.008, 0.05)
    apply_mods(body)

    # tear in the suit over the ribs: grey dead skin and ribs show through
    tear = prim("ico", "SuitTear", (-0.13, -0.12, 1.66), (0.1, 0.12, 0.15), subdivisions=4)
    displace(tear, 0.05, 0.05)
    apply_mods(tear)
    boolean(body, tear)
    sk = prim("sphere", "DeadSkin", (-0.1, 0.0, 1.66), (0.13, 0.1, 0.16), m=dead_skin_body, parent=root)
    displace(sk, 0.02, 0.03)
    for i in range(4):
        z = 1.57 + 0.055 * i
        R_ = Skel()
        R_.chain(None, [((-0.0, -0.11, z + 0.01), 0.013), ((-0.1, -0.135, z), 0.016), ((-0.2, -0.09, z - 0.02), 0.012)])
        R_.build("SuitRib%d" % i, rib_bone, subdiv=2, parent=root)
    for i in range(6):
        a = random.uniform(0, 6.28)
        p = Vector((-0.13 + 0.1 * math.cos(a), -0.16, 1.66 + 0.14 * math.sin(a)))
        seg("TornThread%d" % i, p, p + Vector((random.uniform(-.02, .02), -0.02, -random.uniform(0.03, 0.07))),
            0.003, suit, root, verts=5)

    # pompom buttons
    for i, z in enumerate((1.88, 1.68, 1.48)):
        ok, loc, n, _ = body.ray_cast(Vector((0, -1.0, z)), Vector((0, 1, 0)))
        if ok:
            pp = prim("ico", "Pompom%d" % i, loc + n * 0.03, (0.045, 0.045, 0.045), m=pompom,
                      parent=root, subdivisions=4)
            displace(pp, 0.02, 0.012, depth=4)

    # wind-up crank sticking out of the ribs
    seg("CrankShaft", (0.2, 0.05, 1.7), (0.36, 0.07, 1.72), 0.018, brass, root)
    seg("CrankArm", (0.36, 0.07, 1.72), (0.38, 0.07, 1.86), 0.014, brass, root)
    seg("CrankGrip", (0.38, 0.07, 1.86), (0.48, 0.07, 1.86), 0.025, mat_simple("Bakelite", "#1a0d08", 0.3), root)

    # ruffs: collar, cuffs, ankles
    ruff("Collar", (0, -0.12, 2.09), 0.2, 0.07, 14, lace, root, tilt=(R(-14), 0, 0))
    for s in (-1, 1):
        ruff("Cuff%d" % s, (0.455 * s, -0.33, 1.0), 0.1, 0.04, 10, lace, root, tilt=(R(-30), R(10 * s), 0))
        ruff("Ankle%d" % s, (0.14 * s, -0.01, 0.12), 0.12, 0.035, 10, lace, root)

    # ------------------------------------------------------------ gloves with too-long fingers
    random.seed(3)
    for s in (-1, 1):
        palm_c = Vector((0.46 * s, -0.36, 0.86))
        palm = prim("sphere", "Palm%d" % s, palm_c, (0.075, 0.05, 0.1), m=glove, parent=root)
        displace(palm, 0.008, 0.05)
        fwd = Vector((0, -1, 0))
        side = Vector((1, 0, 0))
        for f in range(4):
            off = side * (f - 1.5) * 0.034 * s
            base = palm_c + off - up * 0.07
            L = [0.13, 0.16, 0.15, 0.12][f] * 1.5
            curl = random.uniform(0.05, 0.12)
            F = Skel()
            F.chain(None, [(base, 0.022), (base - up * L * 0.4 + fwd * curl * 0.3, 0.019),
                           (base - up * L * 0.75 + fwd * curl, 0.017),
                           (base - up * L + fwd * curl * 1.6, 0.014)])
            torn = (s > 0 and f in (1, 2)) or (s < 0 and f == 3)
            fobj = F.build("Finger%d_%d" % (s, f), glove, subdiv=2, parent=root)
            if torn:
                # glove split at the tip: grey dead finger + black nail poking out
                tip = base - up * L + fwd * curl * 1.6
                seg("Bone%d_%d" % (s, f), tip + up * 0.03, tip - up * 0.07 + fwd * 0.02, 0.012, dead_skin,
                    root, r2=0.008, verts=10)
                seg("Nail%d_%d" % (s, f), tip - up * 0.05 + fwd * 0.025, tip - up * 0.1 + fwd * 0.03, 0.008,
                    nail, root, r2=0.001, verts=8)
        tb = palm_c + side * 0.06 * s - fwd * 0.02
        T = Skel()
        T.chain(None, [(tb, 0.022), (tb + side * 0.06 * s - up * 0.05 + fwd * 0.04, 0.018),
                       (tb + side * 0.07 * s - up * 0.12 + fwd * 0.06, 0.015)])
        T.build("Thumb%d" % s, glove, subdiv=2, parent=root)
        for k in range(3):
            a = palm_c + Vector((s * (0.02 * k - 0.02), 0.051, 0.0)) + up * 0.02
            seg("GloveSeam%d_%d" % (s, k), a, a + up * 0.06, 0.003, mat_simple("BlackThread", "#0a0a0a", 0.8),
                root, verts=5)

    # ------------------------------------------------------------ shoes
    for s in (-1, 1):
        SH = Skel()
        SH.chain(None, [((0.14 * s, 0.03, 0.09), (0.11, 0.08)), ((0.15 * s, -0.22, 0.09), (0.13, 0.085)),
                        ((0.16 * s, -0.46, 0.1), (0.12, 0.1)), ((0.16 * s, -0.55, 0.12), (0.08, 0.07))])
        sh = SH.build("Shoe%d" % s, shoe, subdiv=2, parent=root)
        displace(sh, 0.01, 0.1)

    # ------------------------------------------------------------ gramophone horn head
    neck_top = Vector((0, -0.15, 2.17))
    hdir = Vector((0, -0.9, 0.44)).normalized()
    seg("NeckPipe", Vector((0, -0.1, 1.98)), neck_top + hdir * 0.05, 0.04, brass, root)
    for i in range(4):
        p = Vector((0, -0.1, 1.98)).lerp(neck_top, 0.25 + 0.2 * i)
        t = prim("torus", "NeckRing%d" % i, p, (1, 1, 1), m=brass, parent=root, major_radius=0.045,
                 minor_radius=0.01, major_segments=24, minor_segments=8)
        orient(t, Vector((0, -0.1, 1.98)), neck_top)

    LEN = 0.9
    prof = []
    for i in range(41):
        t = i / 40
        r = 0.035 + 0.46 * t ** 3.3
        if t > 0.94:
            r += (t - 0.94) * 1.4  # rolled lip
        prof.append((r, t * LEN))
    horn = lathe("Horn", prof, segments=64, m=brass, parent=root)
    for v in horn.data.vertices:
        th = math.atan2(v.co.y, v.co.x)
        t = v.co.z / LEN
        k = 1 - 0.035 * t * abs(math.cos(4 * th)) ** 0.25  # eight petal panels with raised seams
        v.co.x *= k
        v.co.y *= k
    sol = horn.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = 0.008
    sol.offset = 1.0
    horn.location = neck_top
    orient(horn, (0, 0, 0), hdir)
    horn.data.update()
    # dark inner wall (solidify only fills the rim) -> inner skin slightly smaller
    inner = lathe("HornThroat", [(r * 0.97, z) for r, z in prof[:-2]], segments=64, m=brass_dark, parent=root)
    inner.location = neck_top
    orient(inner, (0, 0, 0), hdir)

    # rivets along the petal seams
    for pnl in range(8):
        th = pnl * math.pi / 4
        for j in range(5):
            t = 0.45 + j * 0.11
            r = (0.035 + 0.46 * t ** 3.3) * (1 - 0.035 * t) + 0.006
            local = Vector((r * math.cos(th), r * math.sin(th), t * LEN))
            world = neck_top + horn.rotation_quaternion @ local
            prim("sphere", "Rivet%d_%d" % (pnl, j), world, (0.007,) * 3, m=brass, parent=root)

    # ring of human teeth just inside the bell
    q = horn.rotation_quaternion
    for k in range(30):
        th = 2 * math.pi * k / 30
        t = 0.8
        r = (0.035 + 0.46 * t ** 3.3) * 0.95
        base = neck_top + q @ Vector((r * math.cos(th), r * math.sin(th), t * LEN))
        axis = neck_top + q @ Vector((0, 0, t * LEN - 0.08))
        tip = base.lerp(axis, random.uniform(0.12, 0.26)) + Vector([random.uniform(-0.01, 0.01) for _ in range(3)])
        kind = random.random()
        if kind < 0.3:   # incisor: flat chisel
            tooth = seg("HornTooth%d" % k, base, tip, random.uniform(0.016, 0.022), teeth, root, r2=0.012, verts=8)
            tooth.scale.x *= 0.45
        elif kind < 0.8:  # canine
            seg("HornTooth%d" % k, base, tip, random.uniform(0.016, 0.02), teeth, root, r2=0.003, verts=10)
        else:            # molar, blunt
            seg("HornTooth%d" % k, base, base.lerp(tip, 0.6), 0.024, teeth, root, r2=0.02, verts=8)
    # flesh lining creeping out of the throat up the inside of the bell
    lining_prof = []
    for i in range(30):
        t = 0.05 + 0.82 * i / 29
        lining_prof.append(((0.035 + 0.46 * t ** 3.3) * 0.955, t * LEN))
    lining = lathe("FleshLining", lining_prof, segments=64, m=flesh, parent=root)
    for v in lining.data.vertices:
        th = math.atan2(v.co.y, v.co.x)
        t = v.co.z / LEN
        # ragged leading edge: tendrils of flesh reaching toward the rim
        reach = 0.6 + 0.27 * (0.5 + 0.5 * math.sin(5 * th) * math.cos(3 * th + 1.3))
        if t > reach:
            k = 1.0 + (t - reach) * 0.6
            v.co.x *= min(k, 1.04)
            v.co.y *= min(k, 1.04)
    lining.location = neck_top
    orient(lining, (0, 0, 0), hdir)
    displace(lining, 0.012, 0.04)
    apply_mods(lining)
    gum = prim("torus", "Gums", neck_top + q @ Vector((0, 0, 0.8 * LEN - 0.01)), (1, 1, 0.8), m=flesh, parent=root,
               major_radius=(0.035 + 0.46 * 0.8 ** 3.3) * 0.975, minor_radius=0.03, major_segments=96,
               minor_segments=14)
    gum.rotation_mode = "QUATERNION"
    gum.rotation_quaternion = q
    subsurf(gum, 1)
    displace(gum, 0.025, 0.03, depth=4)
    # flesh throat and tongue lolling out
    throat = lathe("Gullet", [(0.032, 0.0), (0.06, 0.2), (0.09, 0.35), (0.07, 0.45)], segments=24, m=flesh, parent=root)
    throat.location = neck_top
    orient(throat, (0, 0, 0), hdir)
    tq = Skel()
    a = neck_top + hdir * 0.35
    tq.chain(None, [(a, (0.05, 0.02)), (a + hdir * 0.2 - up * 0.04, (0.06, 0.02)),
                    (a + hdir * 0.42 - up * 0.17, (0.055, 0.018)), (a + hdir * 0.5 - up * 0.32, (0.04, 0.015))])
    tongue = tq.build("Tongue", flesh, subdiv=2, parent=root)
    displace(tongue, 0.006, 0.03)

    # tiny party hat perched on the rim
    rim_top = neck_top + q @ Vector((0, 0.5, LEN * 0.98))
    hat_o = prim("cone", "PartyHat", rim_top + Vector((0.0, 0.02, 0.1)), (0.07, 0.07, 0.2), m=hat, parent=root,
                 rot=(R(20), R(25), 0))
    prim("ico", "HatPompom", rim_top + Vector((0.03, 0.05, 0.21)), (0.03, 0.03, 0.03), m=pompom, parent=root,
         subdivisions=3)
    seg("HatElastic", rim_top + Vector((-0.05, 0.0, 0.01)), rim_top + Vector((0.06, 0.06, -0.02)), 0.002,
        mat_simple("Elastic", "#101010", 0.6), root, verts=5)
    return root
