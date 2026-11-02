"""Giggler (笑笑兵) - a 75 cm mass-produced Grinny plush off the factory line, stuffed with a
scrap of a child's laughter. Sewing pins for teeth, one safety eye torn out with warm light
leaking from the socket, belly seam split over a tiny music-box movement, pull-string on its back."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, prim, seg, empty, apply_mods, displace, boolean, bevel, orient, add_fur, density_group,
                 mat_plush, mat_fur_hair, mat_brass, mat_simple, R)

FRAME = dict(height=0.75, center=(0, 0, 0.38))
SHOTS = [
    ("hero", "horror", (-0.42, -1.25, 0.3), (0, 0, 0.42), 32),
    ("studio", "studio", (0.7, -1.3, 0.55), (0, 0, 0.37), 35),
    ("face", "horror", (-0.22, -0.72, 0.6), (0, -0.05, 0.56), 45),
]
UP = Vector((0, 0, 1))


def hit(obj, origin, direction):
    """Ray cast in world space (converted to the object's local space and back)."""
    bpy.context.view_layer.update()
    mw = obj.matrix_world
    inv = mw.inverted()
    o_l = inv @ Vector(origin)
    d_l = (inv.to_3x3() @ Vector(direction)).normalized()
    ok, loc, n, _ = obj.ray_cast(o_l, d_l)
    if not ok:
        return None, None
    return mw @ loc, (inv.to_3x3().transposed() @ n).normalized()


def onto(obj, center, direction, dist=1.0):
    d = Vector(direction).normalized()
    return hit(obj, Vector(center) + d * dist, -d)


def stitch_line(name, a, b, n, thread, parent, count=6, size=0.008, r=0.0016):
    a, b, n = Vector(a), Vector(b), Vector(n).normalized()
    along = b - a
    side = along.cross(n).normalized() * size
    for i in range(count):
        p = a + along * ((i + 0.5) / count) + n * 0.0015
        seg("%s%d" % (name, i), p - side, p + side, r, thread, parent, verts=5)


def build():
    random.seed(41)
    plush = mat_plush("GigglerPlush", "#4e3036", "#22141a", "#6e545a", scale=6)
    fur = mat_fur_hair("GigglerFur", "#4a2c32", "#6a5056", "#1e1014")
    muzzle_m = mat_plush("GigglerMuzzle", "#9a8070", "#4a3a30", "#b8a290", scale=8)
    muzzle_fur = mat_fur_hair("GigglerMuzzleFur", "#8e7464", "#b09888", "#4a3a30")
    felt = mat_plush("PawFelt", "#3a2226", "#1a0e10", "#5a3a3e", scale=14)
    thread = mat_simple("Thread", "#1c0605", 0.8)
    thread_w = mat_simple("ThreadWhite", "#cfc6b4", 0.8)
    eye_m = mat_simple("SafetyEye", "#050302", 0.08, coat=1.0, coat_rough=0.05)
    nose_m = mat_simple("NosePlastic", "#1a0f0c", 0.2, coat=1.0, coat_rough=0.15)
    steel = mat_simple("PinSteel", "#8a8c8e", 0.25, metal=1.0)
    pin_heads = [mat_simple("PinHeadR", "#8a0c0c", 0.2, coat=1), mat_simple("PinHeadW", "#d8d0c0", 0.2, coat=1),
                 mat_simple("PinHeadY", "#b8901c", 0.2, coat=1)]
    gums = mat_simple("MouthLining", "#2a0a0e", 0.7, sheen=0.5)
    cavity = mat_simple("Cavity", "#050303", 0.95)
    glow = mat_simple("Laughter", "#ffc070", 0.4, emit="#ffb050", emit_strength=5.0)
    glow_soft = mat_simple("LaughterSoft", "#ffd8a0", 0.6, emit="#ff9a40", emit_strength=2.5)
    stuffing = mat_plush("Stuffing", "#a89c84", "#5e5444", "#c4b89e", stain="#5a4a32", scale=40)
    brass = mat_brass()
    tag_m = mat_plush("TagCloth", "#d8d0c0", "#8a8476", "#ece6da", stain="#7a6a4a", scale=12)
    ring_m = mat_simple("PullRing", "#c8b070", 0.35, coat=0.6)
    cord_m = mat_simple("PullCord", "#d0c8b0", 0.8)

    root = empty("Giggler")

    # ------------------------------------------------------------ body: squat, belly heavy, little legs
    S = Skel()
    pelvis = S.chain(None, [((0, 0.01, 0.2), (0.15, 0.13))])
    belly = S.chain(pelvis, [((0, -0.01, 0.29), (0.17, 0.15)), ((0, 0.01, 0.38), (0.14, 0.12))])
    S.chain(belly, [((0, 0.0, 0.43), (0.08, 0.075))])
    for s in (-1, 1):
        # arms: short, one hanging, one raised a little as if reaching
        if s < 0:
            S.chain(belly, [((0.12 * s, 0, 0.39), 0.055), ((0.19 * s, -0.02, 0.33), 0.048), ((0.22 * s, -0.04, 0.25), 0.05)])
        else:
            S.chain(belly, [((0.12 * s, 0, 0.39), 0.055), ((0.2 * s, -0.06, 0.38), 0.048), ((0.25 * s, -0.13, 0.4), 0.05)])
        S.chain(pelvis, [((0.08 * s, 0, 0.16), 0.07), ((0.1 * s, -0.02, 0.07), 0.062), ((0.1 * s, -0.06, 0.045), (0.065, 0.045)),
                         ((0.1 * s, -0.11, 0.045), (0.058, 0.04))])
    body = S.build("Body", plush, subdiv=2, parent=root)
    displace(body, 0.006, 0.05)
    apply_mods(body)

    # stuffed neck joint: the head is sewn onto a fat ring of plush
    neck = prim("sphere", "NeckRuff", (0, -0.01, 0.45), (0.105, 0.095, 0.055), m=plush, parent=root)
    displace(neck, 0.004, 0.03)
    # belly seam split open: the factory's machine seam down the middle of the front
    seam_top, seam_bot = Vector((0.0, -0.17, 0.36)), Vector((0.0, -0.17, 0.22))
    cut = prim("ico", "BellySplit", (0.0, -0.17, 0.29), (0.032, 0.09, 0.07), subdivisions=4)
    displace(cut, 0.012, 0.02)
    apply_mods(cut)
    boolean(body, cut)
    inside = prim("sphere", "BellyInside", (0.0, -0.06, 0.29), (0.08, 0.08, 0.09), m=cavity, parent=root)
    # a warm light glowing out of the stuffing: the laughter
    prim("sphere", "BellyGlow", (0.0, -0.12, 0.28), (0.028, 0.02, 0.028), m=glow, parent=root)
    # the music-box movement nested in the stuffing: cylinder with pins, steel comb, brass plate
    mb_c = Vector((0.0, -0.135, 0.31))
    prim("cube", "MBPlate", mb_c + Vector((0, 0.012, 0)), (0.05, 0.004, 0.032), m=brass, parent=root)
    cyl = prim("cyl", "MBCylinder", mb_c + Vector((0, -0.004, 0.006)), (0.008, 0.008, 0.034), m=brass, parent=root,
               rot=(0, R(90), 0))
    for k in range(24):
        a = random.uniform(0, 2 * math.pi)
        x = random.uniform(-0.016, 0.016)
        p = mb_c + Vector((x, -0.004 + math.sin(a) * 0.008, 0.006 + math.cos(a) * 0.008))
        seg("MBPin%d" % k, p, p + Vector((0, math.sin(a), math.cos(a))) * 0.0018, 0.0005, steel, root, verts=4)
    for k in range(9):
        x = -0.016 + k * 0.004
        seg("MBTooth%d" % k, mb_c + Vector((x, -0.006, -0.012)), mb_c + Vector((x, -0.012, 0.0)), 0.0012, steel, root,
            r2=0.0006, verts=4)
    seg("MBKey", mb_c + Vector((0.026, 0.0, 0.0)), mb_c + Vector((0.04, 0.0, 0.0)), 0.002, brass, root, verts=6)
    # stuffing spilling out of the split
    stuff = []
    for i in range(7):
        a = random.uniform(0, 2 * math.pi)
        p = Vector((math.cos(a) * 0.026, -0.165 - random.uniform(0, 0.01), 0.29 + math.sin(a) * 0.065))
        sc = random.uniform(0.008, 0.014)
        for c in range(3):
            q = p + Vector((random.uniform(-1, 1), random.uniform(-0.6, 0.2), random.uniform(-1, 1))) * sc * 0.7
            cs = sc * random.uniform(0.45, 0.75)
            st = prim("ico", "Stuffing%d_%d" % (i, c), q, (cs, cs * 0.7, cs * 1.2), m=stuffing, parent=root,
                      subdivisions=3)
            displace(st, cs * 1.2, 0.005, depth=5)
            apply_mods(st)
            stuff.append(st)
    for i, (p, sc) in enumerate((((0.02, -0.18, 0.21), (0.014, 0.012, 0.02)), ((0.024, -0.182, 0.185), (0.01, 0.01, 0.016)))):
        st = prim("ico", "StuffingHang%d" % i, p, sc, m=stuffing, parent=root, subdivisions=4)
        displace(st, 0.008, 0.008, depth=4)
        apply_mods(st)
        stuff.append(st)
    # the broken machine stitches either side of the split, threads pulled loose
    for i in range(9):
        z = 0.23 + i * 0.016
        for s in (-1, 1):
            loc, n = onto(body, (0, 0, z), (0.42 * s, -1, 0), 0.6)
            if loc is None:
                continue
            seg("SplitStitch%d_%d" % (i, s), loc + n * 0.001, loc + n * 0.001 + Vector((0.007 * s, -0.004, -0.004)), 0.0011,
                thread_w, root, verts=4)
            if i % 3 == 1 and s > 0:
                seg("LooseThread%d" % i, loc, loc + Vector((0.004, -0.01, -0.05)), 0.0008, thread_w, root, verts=4)

    # ------------------------------------------------------------ head: too big for the body
    hc = Vector((0.0, -0.02, 0.57))
    head = prim("sphere", "Head", (0, 0, 0), (1, 1, 1), m=plush, parent=root, segments=64, ring_count=32)
    for v in head.data.vertices:
        x, y, z = v.co
        # plush head: wide cheeks, flat-ish face, seams pull it into a slight pear shape
        X = x * 0.158 * (1 + 0.06 * max(0.0, -z))
        Y = y * (0.142 if y < 0 else 0.135)
        Z = z * 0.14
        Y -= 0.012 * max(0.0, -y) * max(0.0, 1 - abs(z) * 1.4)
        v.co = Vector((X, Y, Z)) + Vector((0.0, -0.02, 0.575))
    head.data.update()
    displace(head, 0.004, 0.04)
    apply_mods(head)
    # muzzle
    muz = prim("sphere", "Muzzle", (0.0, -0.17, 0.525), (0.085, 0.055, 0.06), m=muzzle_m, parent=root)
    displace(muz, 0.003, 0.03)
    apply_mods(muz)
    # wide grin cut across the muzzle, lined, set with sewing pins for teeth
    pts, normals = [], []
    N = 17
    for k in range(N):
        a = R(-70 + 140 * k / (N - 1))
        z = 0.505 + 0.035 * (1 - math.cos(a)) ** 1.2
        loc, n = onto(muz, (0, -0.15, z), (math.sin(a), -math.cos(a), 0), 0.4)
        if loc is None:
            continue
        pts.append(loc)
        normals.append(n)
    C = Skel()
    prev = None
    for k, (p, n) in enumerate(zip(pts, normals)):
        t = abs(k - (len(pts) - 1) / 2) / ((len(pts) - 1) / 2)
        r = 0.016 * (1 - 0.5 * t)
        idx = C.p(p - n * 0.003, (r * 0.6, r))
        if prev is None:
            C.roots.append(idx)
        else:
            C.e.append((prev, idx))
        prev = idx
    cutter = C.build("GrinCut", None, subdiv=1)
    apply_mods(cutter)
    boolean(muz, cutter)
    G = Skel()
    G.chain(None, [(p - n * 0.012, 0.012) for p, n in zip(pts, normals)])
    G.build("MouthLining", gums, subdiv=2, parent=root)
    for k in range(1, len(pts) - 1):
        p, n = pts[k], normals[k]
        t = abs(k - (len(pts) - 1) / 2) / ((len(pts) - 1) / 2)
        h = 0.016 * (1 - 0.5 * t)
        for sg, keep in ((1, True), (-1, k % 2 == 0)):
            if not keep:
                continue
            # pin pushed through the felt lip, point toward the gap
            a = p - n * 0.004 + UP * sg * (h + 0.012)
            b = p - n * 0.002 - UP * sg * h * 0.55
            seg("PinTooth%d_%d" % (k, sg), a, b, 0.0009, steel, root, r2=0.0002, verts=5)
            if sg > 0 and k % 3 == 0:
                prim("sphere", "PinToothHead%d" % k, a, (0.0035, 0.0035, 0.0035), m=random.choice(pin_heads),
                     parent=root, segments=10, ring_count=6)
    # stitch lines from the corners of the grin up the cheeks
    for s, k in ((-1, 0), (1, len(pts) - 1)):
        p, n = pts[k], normals[k]
        end, n2 = onto(head, hc, (s * 1, -0.6, 0.35), 0.5)
        if end is not None:
            stitch_line("CheekScar%s" % s, p, end, n, thread, root, count=4, size=0.007)
    # nose
    nl, nn = onto(muz, (0, -0.15, 0.55), (0, -1, 0.5), 0.4)
    prim("sphere", "Nose", nl + nn * 0.004, (0.019, 0.012, 0.012), m=nose_m, parent=root)
    seg("NoseLine", nl - UP * 0.012, nl - UP * 0.034 + nn * 0.002, 0.0015, thread, root, verts=5)

    # left eye: plastic safety eye, slightly scratched
    el, en = onto(head, hc, (-0.38, -1, 0.32), 0.5)
    e = prim("sphere", "SafetyEye", el, (0.025, 0.025, 0.012), m=eye_m, parent=root)
    orient(e, (0, 0, 0), en)
    # right eye: torn out; frayed hole with warm light coming out and the washer left behind
    rl, rn = onto(head, hc, (0.38, -1, 0.32), 0.5)
    sock = prim("ico", "EyeTear", rl, (0.024, 0.024, 0.024), subdivisions=3)
    displace(sock, 0.008, 0.012)
    apply_mods(sock)
    boolean(head, sock)
    prim("sphere", "EyeHollow", rl - rn * 0.035, (0.022, 0.022, 0.022), m=cavity, parent=root)
    prim("sphere", "EyeGlow", rl - rn * 0.016, (0.009, 0.009, 0.009), m=glow, parent=root)
    for i in range(8):
        a = 2 * math.pi * i / 8 + random.uniform(-0.2, 0.2)
        side = rn.cross(UP).normalized()
        upn = side.cross(rn).normalized()
        p = rl + (side * math.cos(a) + upn * math.sin(a)) * 0.022
        seg("EyeFray%d" % i, p, p + rn * 0.006 + (side * math.cos(a) + upn * math.sin(a)) * 0.008 - UP * 0.004,
            0.0009, thread_w, root, verts=4)
    st = prim("ico", "EyeStuffing", rl + rn * 0.002 - UP * 0.012, (0.01, 0.008, 0.01), m=stuffing, parent=root,
              subdivisions=3)
    displace(st, 0.006, 0.006)
    stuff.append(st)
    # the plastic washer that held the eye still dangles on a thread
    hang = rl + Vector((0.012, -0.02, -0.08))
    seg("WasherThread", rl - UP * 0.01, hang + UP * 0.006, 0.0008, thread, root, verts=4)
    w = prim("torus", "Washer", hang, (1, 1, 1), m=mat_simple("WasherPlastic", "#d8d2c4", 0.4), parent=root,
             major_radius=0.008, minor_radius=0.0025, rot=(R(70), R(15), 0))

    # ears, one with the factory tag punched through it
    ears = []
    for s in (-1, 1):
        ep = Vector((0.115 * s, 0.0, 0.685))
        e = prim("sphere", "Ear%s" % s, ep, (0.05, 0.03, 0.048), m=plush, parent=root, rot=(R(-6), R(25 * s), R(-30 * s)))
        displace(e, 0.003, 0.02)
        apply_mods(e)
        prim("sphere", "EarInner%s" % s, ep + Vector((0.004 * s, -0.022, 0.006)), (0.032, 0.012, 0.03), m=muzzle_m,
             parent=root, rot=(R(-6), R(25 * s), R(-30 * s)))
        ears.append(e)
    tag_at = Vector((0.15, -0.01, 0.64))
    seg("TagFastener", tag_at + Vector((-0.01, -0.02, 0.01)), tag_at + Vector((0.004, 0.0, -0.01)), 0.0012,
        mat_simple("TagPlastic", "#e8e2d6", 0.4), root, verts=5)
    tag = prim("cube", "EarTag", tag_at + Vector((0.016, -0.012, -0.045)), (0.024, 0.0015, 0.04), m=tag_m, parent=root,
               rot=(R(8), R(-15), R(-10)))
    displace(tag, 0.002, 0.01)
    # printed lines on the tag
    for k in range(4):
        seg("TagPrint%d" % k, tag_at + Vector((0.008, -0.0145, -0.03 - k * 0.01)), tag_at + Vector((0.026, -0.0145, -0.03 - k * 0.01)),
            0.0008, mat_simple("TagInk", "#6a1414", 0.6), root, verts=4)

    # paws: felt pads with stitched toe lines
    for s in (-1, 1):
        fl, fn = onto(body, (0.1 * s, -0.08, 0.045), (0, -1, 0), 0.4)
        if fl is not None:
            pad = prim("sphere", "FootPad%s" % s, fl + fn * 0.002, (0.04, 0.032, 0.008), m=felt, parent=root)
            orient(pad, (0, 0, 0), fn)
            for k in (-1, 0, 1):
                a = fl + fn * 0.004 + Vector((0.014 * k, 0, 0.022))
                seg("ToeLine%s%d" % (s, k), a, a + Vector((0, -0.002, -0.014)), 0.0011, thread, root, verts=4)
    for s, (hx, hy, hz) in ((-1, (-0.22, -0.04, 0.25)), (1, (0.25, -0.13, 0.4))):
        hl, hn = onto(body, (hx, hy, hz), (0.4 * s, -1, -0.2), 0.3)
        if hl is not None:
            pad = prim("sphere", "HandPad%s" % s, hl + hn * 0.002, (0.03, 0.026, 0.006), m=felt, parent=root)
            orient(pad, (0, 0, 0), hn)

    # pull-string on its back: pull it and it laughs
    bl, bn = onto(body, (0, 0, 0.33), (0, 1, 0.1), 0.5)
    grom = prim("torus", "Grommet", bl + bn * 0.002, (1, 1, 1), m=brass, parent=root, major_radius=0.008,
                minor_radius=0.0025)
    orient(grom, (0, 0, 0), bn)
    ring_c = bl + bn * 0.03 + Vector((0.01, 0, -0.07))
    seg("PullCord", bl, ring_c + Vector((0, 0, 0.022)), 0.0015, cord_m, root, verts=5)
    ring = prim("torus", "PullRing", ring_c, (1, 1, 1), m=ring_m, parent=root, major_radius=0.022, minor_radius=0.005,
                rot=(R(80), R(10), 0))

    # ------------------------------------------------------------ fur
    body.data.materials.append(fur)
    dens = density_group(body, [Vector((0, -0.17, 0.29))], 0.06, 0.09)
    add_fur(body, "GigglerFur", count=7000, length=0.009, children=20, clump=0.8, rough=0.006, radius=0.0012,
            seed=1, density=dens)
    neck.data.materials.append(fur)
    add_fur(neck, "GigglerFur", count=1500, length=0.009, children=20, clump=0.8, rough=0.006, radius=0.0012, seed=9)
    head.data.materials.append(fur)
    dens = density_group(head, [el, rl], 0.03, 0.05)
    add_fur(head, "GigglerFur", count=6000, length=0.008, children=20, clump=0.8, rough=0.006, radius=0.0012,
            seed=2, density=dens)
    muz.data.materials.append(muzzle_fur)
    dens = density_group(muz, pts + [nl], 0.012, 0.022)
    add_fur(muz, "GigglerMuzzleFur", count=2500, length=0.005, children=16, clump=0.3, rough=0.003, radius=0.001,
            seed=3, density=dens)
    for i, e in enumerate(ears):
        e.data.materials.append(fur)
        add_fur(e, "GigglerFur", count=600, length=0.006, children=16, radius=0.001, seed=4 + i)
    fiber = mat_fur_hair("StuffingFiber", "#d6cfbd", "#efe9da", "#8f8570")
    for i, st in enumerate(stuff):
        st.data.materials.append(fiber)
        add_fur(st, "StuffingFiber", count=400, length=0.014, children=30, clump=0.0, rough=0.03, radius=0.0004,
                seed=20 + i)

    # head lolls to one side, the way a stuffed toy's head does when the neck stuffing has gone
    pivot = empty("HeadPivot", (0, 0, 0.45), root)
    bpy.context.view_layer.update()
    for o in list(bpy.data.objects):
        if o.parent is not root or o.type != "MESH":
            continue
        if o.matrix_world.translation.z > 0.46 or o.name.startswith(("Ear", "Tag", "Washer")):
            mw = o.matrix_world.copy()
            o.parent = pivot
            o.matrix_world = mw
    pivot.rotation_euler = (R(10), R(14), R(-8))
    return root
