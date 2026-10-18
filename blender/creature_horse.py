"""Bone horse - a carousel prancer whose painted wooden shell has split open,
revealing a real horse skeleton (and a music-box drum) inside."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, prim, seg, empty, apply_mods, displace, boolean, lathe, orient, loft, subsurf,
                 mat_bone, mat_painted_wood, mat_brass, mat_teeth, mat_simple, mat_rust, R)

FRAME = dict(height=2.6, center=(0, 0.1, 1.3))
SHOTS = [
    ("hero", "horror", (-2.6, -3.4, 0.9), (0, -0.2, 1.35), 30),
    ("studio", "studio", (4.6, -1.6, 1.6), (0, 0.1, 1.25), 35),
    ("face", "horror", (-1.2, -2.5, 2.0), (0, -1.25, 1.85), 45),
]


def jagged(loc, scale, strength=0.25, sub=4):
    c = prim("ico", "Cut", loc, scale, subdivisions=sub)
    displace(c, strength, 0.25)
    apply_mods(c)
    return c


def bone_chain(name, pts, m, parent, knob=1.35):
    """pts: joint positions with radii. Adds knobbly epiphyses at each end of each bone."""
    S = Skel()
    prev = None
    for i in range(len(pts) - 1):
        (a, ra), (b, rb) = pts[i], pts[i + 1]
        a, b = Vector(a), Vector(b)
        mid_r = min(ra, rb) * 0.62
        if prev is None:
            prev = S.chain(None, [(a, ra * knob)])
        prev = S.chain(prev, [(a.lerp(b, 0.18), mid_r * 1.05), (a.lerp(b, 0.5), mid_r * 0.92),
                              (a.lerp(b, 0.82), mid_r * 1.05), (b, rb * knob)])
    return S.build(name, m, subdiv=2, parent=parent)


def build():
    bone = mat_bone()
    paint = mat_painted_wood("CarouselPaint", "#d9ccb0")
    mane_paint = mat_painted_wood("ManePaint", "#8c1a1a")
    saddle_paint = mat_painted_wood("SaddlePaint", "#4a1f5c")
    gold = mat_brass("Gilt")
    teeth = mat_teeth()
    dark = mat_simple("Hollow", "#000000", 1.0, spec=0.0)
    ember = mat_simple("SocketGlow", "#200000", 0.4, emit="#ff2208", emit_strength=6.0)
    rust = mat_rust()

    root = empty("Horse")
    random.seed(4)

    # ------------------------------------------------------------ spine
    def spine_at(t):
        y = -0.55 + 1.4 * t
        z = 1.62 - 0.08 * math.sin(math.pi * t) + 0.02 * t
        return Vector((0, y, z))

    for i in range(16):
        t = i / 15
        p = spine_at(t)
        q = spine_at(min(1, t + 0.04))
        seg("Vert%d" % i, p - (q - p).normalized() * 0.035, p + (q - p).normalized() * 0.035,
            0.045, bone, root, verts=12)
        h = 0.2 * (1 - t) + 0.06
        seg("Process%d" % i, p, p + Vector((0, 0.03 + 0.05 * (1 - t), h)), 0.022, bone, root,
            r2=0.008, verts=8)
        for s in (-1, 1):
            seg("Trans%d_%d" % (i, s), p, p + Vector((0.08 * s, 0.0, -0.01)), 0.014, bone, root, r2=0.008, verts=6)
    # tail vertebrae
    for i in range(9):
        a = spine_at(1) + Vector((0, 0.06 * i + 0.05, -0.05 * i - 0.04 * i * i * 0.1))
        prim("sphere", "Tail%d" % i, a, (0.03 - i * 0.002,) * 3, m=bone, parent=root)

    # neck
    neck_pts = []
    for i in range(8):
        t = i / 7
        p = Vector((0, -0.55 - 0.5 * t - 0.05 * math.sin(math.pi * t), 1.62 + 0.55 * t + 0.08 * math.sin(math.pi * t)))
        neck_pts.append(p)
    for i in range(7):
        a, b = neck_pts[i], neck_pts[i + 1]
        seg("NeckV%d" % i, a.lerp(b, 0.12), a.lerp(b, 0.88), 0.058, bone, root, verts=12)
        prim("sphere", "NeckJ%d" % i, b, (0.07, 0.07, 0.06), m=bone, parent=root)

    # ------------------------------------------------------------ ribs
    for i in range(10):
        t = i / 9
        sp = spine_at(0.04 + 0.5 * t)
        depth = 0.78 - 0.35 * t ** 1.5
        width = 0.3 + 0.06 * math.sin(math.pi * (0.3 + 0.7 * t))
        for s in (-1, 1):
            bone_chain("Rib%d_%d" % (i, s), [
                (sp + Vector((0.04 * s, 0, -0.03)), 0.022),
                (sp + Vector((width * 0.75 * s, 0.03, -0.12)), 0.02),
                (sp + Vector((width * s, 0.06, -depth * 0.45)), 0.018),
                (sp + Vector((width * 0.8 * s, 0.05, -depth * 0.8)), 0.016),
                (sp + Vector((0.12 * s * (1 + t), 0.02, -depth)), 0.014),
            ], bone, root, knob=1.1)
    bone_chain("Sternum", [((0, -0.62, 0.88), 0.04), ((0, -0.35, 0.82), 0.045), ((0, -0.05, 0.86), 0.035)],
               bone, root, knob=1.0)

    # scapulae and pelvis
    for s in (-1, 1):
        sc = prim("ico", "Scapula%d" % s, (0.27 * s, -0.5, 1.42), (0.035, 0.15, 0.24), m=bone,
                  parent=root, rot=(R(-25), R(6 * s), 0), subdivisions=3)
        displace(sc, 0.015, 0.1)
        il = prim("ico", "Ilium%d" % s, (0.19 * s, 0.68, 1.56), (0.17, 0.045, 0.09), m=bone, parent=root,
                  rot=(R(20), R(-25 * s), R(25 * s)), subdivisions=3)
        displace(il, 0.02, 0.1)
        bone_chain("Ischium%d" % s, [((0.16 * s, 0.7, 1.5), 0.05), ((0.2 * s, 0.8, 1.32), 0.05),
                                     ((0.12 * s, 0.98, 1.3), 0.045)], bone, root)

    # ------------------------------------------------------------ legs (carousel prance)
    legs = {
        "FL": [((-0.25, -0.6, 1.3), 0.06), ((-0.24, -0.74, 0.98), 0.05), ((-0.22, -1.1, 0.98), 0.042),
               ((-0.22, -1.02, 0.68), 0.035), ((-0.22, -0.95, 0.58), 0.04)],
        "FR": [((0.25, -0.6, 1.3), 0.06), ((0.24, -0.72, 0.94), 0.05), ((0.22, -1.0, 0.8), 0.042),
               ((0.22, -0.86, 0.52), 0.035), ((0.22, -0.8, 0.42), 0.04)],
        "HL": [((-0.21, 0.8, 1.27), 0.065), ((-0.23, 0.62, 0.9), 0.055), ((-0.22, 1.05, 0.64), 0.045),
               ((-0.22, 1.36, 0.42), 0.035), ((-0.22, 1.48, 0.35), 0.04)],
        "HR": [((0.21, 0.8, 1.27), 0.065), ((0.23, 0.6, 0.92), 0.055), ((0.22, 0.98, 0.6), 0.045),
               ((0.22, 1.25, 0.34), 0.035), ((0.22, 1.36, 0.25), 0.04)],
    }
    for name, pts in legs.items():
        bone_chain("Leg" + name, pts, bone, root)
        a, b = Vector(pts[-2][0]), Vector(pts[-1][0])
        d = (b - a).normalized()
        seg("Hoof" + name, b - d * 0.02, b + d * 0.12, 0.07, gold, root, r2=0.058)

    # ------------------------------------------------------------ skull (lofted, anatomical)
    poll = neck_pts[-1] + Vector((0, -0.03, 0.04))
    d = Vector((0, -0.72, -0.69)).normalized()
    up = Vector((0, -0.69, 0.72)).normalized()
    X = Vector((1, 0, 0))
    L = 0.72
    prof = [(0.0, 0.07, 0.075, 0.02), (0.08, 0.11, 0.1, 0.02), (0.2, 0.13, 0.11, 0.0),
            (0.32, 0.1, 0.1, -0.01), (0.5, 0.08, 0.088, -0.02), (0.7, 0.064, 0.072, -0.025),
            (0.88, 0.054, 0.056, -0.03), (1.0, 0.04, 0.034, -0.035)]
    skull = loft("Skull", [poll + d * (t * L) for t, *_ in prof], [(w, h, o) for _, w, h, o in prof],
                 side=X, segs=20, m=bone, parent=root)
    subsurf(skull, 2)
    displace(skull, 0.008, 0.05)
    apply_mods(skull)
    displace(skull, 0.004, 0.012, depth=4)
    apply_mods(skull)
    eye_c = []
    for s in (-1, 1):
        c = poll + d * 0.17 + up * 0.01 + X * (0.124 * s)
        eye_c.append(c)
        boolean(skull, jagged(c, (0.062, 0.062, 0.058), 0.01, 3))
        seg("Zygomatic%d" % s, c - up * 0.05 - X * (0.012 * s), poll + d * 0.03 - up * 0.04 + X * (0.085 * s),
            0.013, bone, root, verts=10)
    # nasal opening and temporal pits
    boolean(skull, jagged(poll + d * 0.64 + up * 0.035, (0.03, 0.03, 0.03), 0.01, 3))
    for s in (-1, 1):
        boolean(skull, jagged(poll + d * 0.36 + up * 0.0 + X * (0.1 * s), (0.03, 0.08, 0.035), 0.01, 3))
    for i, c in enumerate(eye_c):
        sgn = 1 if i else -1
        prim("sphere", "SocketDark%d" % i, c - X * (0.075 * sgn), (0.045, 0.045, 0.045), m=dark, parent=root)
        prim("sphere", "Glint%d" % i, c - X * (0.035 * sgn) - up * 0.01, (0.008, 0.008, 0.008), m=ember, parent=root)

    # mandibles, jaw hanging slightly open
    def jaw_pt(dist, drop):
        open_ = 0.06 * max(0.0, dist - 0.17) / 0.5
        return poll + d * dist - up * (drop + open_)
    jaw_path = [(0.17, 0.06, 0.03), (0.13, 0.15, 0.045), (0.18, 0.23, 0.05), (0.32, 0.215, 0.03),
                (0.5, 0.185, 0.025), (0.7, 0.15, 0.02)]
    for s in (-1, 1):
        pts = []
        for i, (dist, drop, h) in enumerate(jaw_path):
            x = 0.09 - 0.07 * (i / (len(jaw_path) - 1)) ** 1.5
            pts.append(jaw_pt(dist, drop) + X * (x * s))
        jaw = loft("Mandible%d" % s, pts, [(0.016, h, 0.0) for _, _, h in jaw_path], side=X, segs=12,
                   m=bone, parent=root)
        subsurf(jaw, 2)
        displace(jaw, 0.005, 0.04)
    prim("sphere", "Symphysis", jaw_pt(0.69, 0.15), (0.025, 0.025, 0.02), m=bone, parent=root)

    # cheek teeth (tall, worn horse molars) and incisors
    for s in (-1, 1):
        for k in range(6):
            dist = 0.3 + 0.045 * k
            top = poll + d * dist - up * 0.1 + X * (0.05 * s)
            seg("Molar%d_%d" % (s, k), top, top - up * 0.04, 0.023, teeth, root, verts=6)
            jt = jaw_pt(dist, 0.19) + up * 0.022 + X * (0.05 * s * (1 - 0.2 * k / 5))
            seg("MolarL%d_%d" % (s, k), jt, jt + up * 0.035, 0.022, teeth, root, verts=6)
    for k in range(6):
        x = (k - 2.5) * 0.015
        tip = poll + d * 0.69 - up * 0.055 + X * x
        seg("IncU%d" % k, tip, tip + d * 0.025 - up * 0.05, 0.009, teeth, root, r2=0.006, verts=8)
        tl = jaw_pt(0.68, 0.14) + X * (x * 0.8)
        seg("IncL%d" % k, tl, tl + d * 0.025 + up * 0.04, 0.008, teeth, root, r2=0.005, verts=8)

    # gilded bridle remnant across the muzzle
    br = prim("torus", "Bridle", poll + d * 0.5 - up * 0.02, (1, 1, 1), m=gold, parent=root,
              major_radius=0.098, minor_radius=0.012, major_segments=32, minor_segments=8)
    orient(br, (0, 0, 0), d)
    prim("ico", "Jewel", poll + d * 0.5 - up * 0.02 + Vector((-0.1, 0, 0)), (0.025, 0.025, 0.025),
         m=mat_simple("RedJewel", "#6a0010", 0.05, coat=1.0), parent=root, subdivisions=2)

    # ------------------------------------------------------------ painted wooden shell (mostly broken)
    W = Skel()
    chest = W.chain(None, [((0, -0.62, 1.28), (0.34, 0.42)), ((0, -0.05, 1.25), (0.39, 0.42)),
                           ((0, 0.72, 1.33), (0.37, 0.4))])
    W.chain(0, [((0, -0.82, 1.65), (0.2, 0.24)), ((0, -1.0, 2.0), (0.16, 0.2))])
    shell = W.build("Shell", paint, subdiv=2, parent=root)
    sol = shell.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = 0.03
    apply_mods(shell)
    # break it apart: keep only the left chest / shoulder / lower neck
    for loc, sc in (((0.45, 0.0, 1.3), (0.42, 1.2, 0.7)), ((0.0, 0.75, 1.4), (0.6, 0.45, 0.55)),
                    ((0.0, 0.0, 1.75), (0.6, 0.85, 0.25)), ((0.0, 0.25, 0.8), (0.6, 0.6, 0.35)),
                    ((-0.45, 0.45, 1.2), (0.3, 0.45, 0.35)), ((0.0, -1.05, 2.1), (0.3, 0.25, 0.3)),
                    ((0.15, -0.75, 1.5), (0.22, 0.25, 0.3)), ((-0.42, -0.1, 1.05), (0.2, 0.22, 0.16))):
        boolean(shell, jagged(loc, sc, 0.22))
    # carved mane on the remaining neck
    for i in range(7):
        t = i / 6
        b = Vector((-0.02, -0.7 - 0.28 * t, 1.75 + 0.33 * t))
        M = Skel()
        M.chain(None, [(b, (0.05, 0.03)), (b + Vector((-0.1, 0.06, -0.06)), (0.06, 0.025)),
                       (b + Vector((-0.17, 0.12, -0.18)), (0.045, 0.02)), (b + Vector((-0.13, 0.15, -0.28)), 0.012)])
        M.build("Mane%d" % i, mane_paint, subdiv=2, parent=root)

    # broken saddle and tassels
    sd = prim("cube", "Saddle", (0, -0.02, 1.7), (0.42, 0.42, 0.07), m=saddle_paint, parent=root,
              rot=(R(-4), 0, 0))
    sd.modifiers.new("Bend", "SUBSURF").levels = 2
    boolean(sd, jagged((0.25, 0.15, 1.7), (0.2, 0.2, 0.2), 0.1))
    seg("SaddleTrim", (-0.22, -0.22, 1.72), (0.12, -0.22, 1.72), 0.02, gold, root)
    for i in range(3):
        p = Vector((-0.22, -0.1 + 0.1 * i, 1.66))
        seg("TasselCord%d" % i, p, p + Vector((0, 0, -0.18 - 0.05 * i)), 0.005, gold, root, verts=6)
        prim("cone", "Tassel%d" % i, p + Vector((0, 0, -0.24 - 0.05 * i)), (0.03, 0.03, 0.08),
             m=mane_paint, parent=root)

    # music-box drum inside the ribcage
    drum = seg("MusicDrum", (-0.12, -0.15, 1.18), (0.12, -0.15, 1.18), 0.09, gold, root, verts=24)
    for i in range(40):
        a = random.uniform(0, 2 * math.pi)
        x = random.uniform(-0.11, 0.11)
        p = Vector((x, -0.15 + 0.09 * math.cos(a), 1.18 + 0.09 * math.sin(a)))
        seg("Pin%d" % i, p, p + (p - Vector((x, -0.15, 1.18))).normalized() * 0.015, 0.003, gold, root, verts=5)
    for i in range(12):
        x = -0.1 + i * 0.018
        seg("Comb%d" % i, (x, -0.05, 1.16), (x, -0.13, 1.2), 0.004, rust, root, verts=5)
    seg("Wire", (0.0, -0.15, 1.28), (0.1, -0.3, 1.6), 0.005, rust, root, verts=5)

    # ------------------------------------------------------------ twisted brass pole
    prof = [(0.042, z / 40 * 2.7) for z in range(41)]
    pole = lathe("Pole", prof, segments=16, m=gold, parent=root)
    for v in pole.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        k = 1 + 0.18 * math.cos(6 * a)
        v.co.x *= k
        v.co.y *= k
    tw = pole.modifiers.new("Twist", "SIMPLE_DEFORM")
    tw.deform_method = "TWIST"
    tw.angle = R(900)
    tw.deform_axis = "Z"
    apply_mods(pole)
    pole.location = (0, -0.08, 0.0)
    prim("cyl", "PoleFoot", (0, -0.08, 0.02), (0.14, 0.14, 0.04), m=rust, parent=root)
    prim("sphere", "PoleKnob", (0, -0.08, 2.72), (0.07, 0.07, 0.07), m=gold, parent=root)
    return root
