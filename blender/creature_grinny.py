"""Mr. Grinny - 3.6 m stitched teddy-bear mascot of Grinny Gardens."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, prim, seg, empty, apply_mods, displace, boolean, bevel, smooth,
                 add_fur, density_group, mat_plush, mat_fur_hair, mat_flesh, mat_teeth, mat_eyeball,
                 mat_rust, mat_simple, set_mat, R)

FRAME = dict(height=3.6, center=(0, 0, 1.85))
SHOTS = [
    ("hero", "horror", (-1.7, -5.0, 1.1), (0, 0, 2.0), 32),
    ("studio", "studio", (2.7, -5.4, 1.9), (0, 0, 1.85), 35),
    ("face", "horror", (-1.7, -2.5, 2.95), (0.05, -0.5, 2.92), 50),
]


def surface_point(obj, origin, direction):
    ok, loc, normal, _ = obj.ray_cast(Vector(origin), Vector(direction).normalized())
    if not ok:
        raise RuntimeError("ray missed %s" % obj.name)
    return loc, normal


def surface_out(obj, center, direction):
    """Surface point found by casting from outside back toward an interior point."""
    d = Vector(direction).normalized()
    return surface_point(obj, Vector(center) + d * 2.0, -d)


def stitch_line(name, a, b, normal, thread, parent=None, count=6, size=0.05):
    """Cross-stitches along a seam a->b sitting on a surface with given normal."""
    a, b, n = Vector(a), Vector(b), Vector(normal).normalized()
    along = (b - a)
    side = along.cross(n).normalized() * size
    for i in range(count):
        p = a + along * ((i + 0.5) / count) + n * 0.006
        seg("%s%d" % (name, i), p - side, p + side, 0.006, thread, parent, verts=6)


def tear_cutter(loc, scale, seed):
    c = prim("ico", "TearCut", loc, scale, subdivisions=4)
    random.seed(seed)
    displace(c, 0.06, 0.08)
    apply_mods(c)
    return c


def build():
    fur_body = mat_plush("GrinnyPlush", "#5e3440", "#2a141a", "#86606a")
    fur_hair = mat_fur_hair("GrinnyFur", "#5a303a", "#86606a", "#22100f")
    belly_plush = mat_plush("BellyPlush", "#b89482", "#5e4639", "#d9bfae", scale=4)
    belly_hair = mat_fur_hair("BellyFur", "#a8836f", "#d2b8a6", "#4a3a30")
    cavity = mat_simple("Cavity", "#060303", 0.9)
    stuffing = mat_plush("Stuffing", "#d8d0bc", "#8a8270", "#efe9d8", stain="#6b5a3a", scale=6)
    rust = mat_rust()
    thread = mat_simple("Thread", "#1c0605", 0.8)
    gums = mat_flesh("Gums", "#4a0c12", "#120205", "#7a2a30")
    teeth = mat_teeth()
    eyeball = mat_eyeball()
    iris = mat_simple("Iris", "#8a8a3a", 0.15, coat=1.0)
    pupil = mat_simple("Pupil", "#010101", 0.05, coat=1.0)
    button = mat_simple("ButtonPlastic", "#120b08", 0.18, coat=0.8, coat_rough=0.3)
    claw = mat_simple("Claw", "#0d0b09", 0.25, coat=0.6)
    nose = mat_simple("NosePlastic", "#1a0f0c", 0.2, coat=1.0, coat_rough=0.15)

    root = empty("Grinny")

    # ------------------------------------------------------------ body
    S = Skel()
    pelvis = S.chain(None, [((0, 0.03, 1.12), (0.52, 0.44))])
    chest = S.chain(pelvis, [((0, -0.02, 1.48), (0.66, 0.58)), ((0, 0.04, 1.9), (0.62, 0.52))])
    upper = S.chain(chest, [((0, 0.05, 2.25), (0.5, 0.43))])
    S.chain(upper, [((0, -0.12, 2.52), (0.26, 0.24))])
    # arms: left hangs, right is longer and slightly dislocated
    S.chain(upper, [((-0.46, 0.05, 2.28), 0.24), ((-0.7, 0.04, 2.18), 0.2),
                    ((-0.86, -0.04, 1.58), 0.16), ((-0.92, -0.14, 1.0), 0.14),
                    ((-0.93, -0.2, 0.8), (0.2, 0.17))])
    S.chain(upper, [((0.46, 0.05, 2.26), 0.24), ((0.72, 0.06, 2.1), 0.2),
                    ((0.92, -0.1, 1.48), 0.16), ((0.96, -0.28, 0.9), 0.14),
                    ((0.96, -0.36, 0.68), (0.2, 0.17))])
    for s in (-1, 1):
        S.chain(pelvis, [((0.3 * s, 0, 0.95), 0.32), ((0.34 * s, -0.08, 0.52), 0.25),
                         ((0.34 * s, 0.0, 0.2), 0.21), ((0.34 * s, -0.16, 0.13), (0.24, 0.17)),
                         ((0.34 * s, -0.42, 0.13), (0.22, 0.13))])
    body = S.build("Body", fur_body, subdiv=2, parent=root)
    displace(body, 0.035, 0.22)
    apply_mods(body)

    # belly patch sewn on
    patch = prim("sphere", "BellyPatch", (-0.04, -0.47, 1.7), (0.42, 0.14, 0.5), m=belly_plush, parent=root)
    displace(patch, 0.015, 0.2)
    apply_mods(patch)

    # torn belly: cut both body and patch
    tear_at, tear_scale = (0.16, -0.62, 1.55), (0.18, 0.32, 0.28)
    boolean(body, tear_cutter(tear_at, tear_scale, 3))
    boolean(patch, tear_cutter(tear_at, tear_scale, 3))
    prim("sphere", "BellyCavity", (0.14, -0.38, 1.56), (0.25, 0.22, 0.3), m=cavity, parent=root)
    # rusted endoskeleton behind the tear
    for i, z in enumerate((1.5, 1.6, 1.71, 1.8)):
        seg("Rib%d" % i, (-0.04, -0.44, z - 0.07), (0.36, -0.4, z - 0.04), 0.017, rust, root)
    seg("SpinePipe", (0.12, -0.36, 1.25), (0.12, -0.36, 1.85), 0.03, rust, root)
    seg("Wire1", (0.02, -0.5, 1.48), (0.22, -0.68, 1.3), 0.006, mat_simple("Wire", "#6a1a10", 0.4), root)
    random.seed(11)
    stuff_objs = []
    for i in range(16):
        a = random.uniform(0, 2 * math.pi)
        p = Vector(tear_at) + Vector((math.cos(a) * 0.15, -0.02, math.sin(a) * 0.22))
        p += Vector((0, -random.uniform(0.0, 0.06), 0))
        sc = random.uniform(0.05, 0.1)
        st = prim("ico", "Stuffing%d" % i, p, (sc, sc * 0.8, sc), m=stuffing, parent=root,
                  subdivisions=5)
        displace(st, sc * 0.6, 0.03, depth=5)
        apply_mods(st)
        stuff_objs.append(st)
    for i, (p, sc) in enumerate((((0.2, -0.6, 1.4), (0.06, 0.05, 0.08)), ((0.22, -0.62, 1.3), (0.05, 0.045, 0.07)),
                                 ((0.21, -0.6, 1.21), (0.04, 0.04, 0.06)))):
        hang = prim("ico", "StuffingHang%d" % i, p, sc, m=stuffing, parent=root, subdivisions=5)
        displace(hang, 0.03, 0.025, depth=4)
        apply_mods(hang)
        stuff_objs.append(hang)

    # stitches around belly patch
    for i in range(22):
        a = 2 * math.pi * i / 22
        p = Vector((-0.04 + 0.41 * math.cos(a), -0.54, 1.7 + 0.49 * math.sin(a)))
        try:
            loc, n = surface_point(patch, p + Vector((0, -0.4, 0)), (0, 1, 0))
        except RuntimeError:
            continue
        d = Vector((math.cos(a), 0, math.sin(a))) * 0.035
        seg("PatchStitch%d" % i, loc - d + n * 0.005, loc + d + n * 0.005, 0.006, thread, root, verts=6)

    # bolt through the left knee
    seg("KneeBolt", (-0.62, -0.12, 0.55), (-0.08, -0.08, 0.52), 0.03, rust, root)

    # ------------------------------------------------------------ head
    head_pivot = empty("HeadPivot", (0, -0.14, 2.56), root)
    H = Skel()
    H.chain(None, [((0, 0.04, 2.98), (0.56, 0.5)), ((0, -0.16, 2.95), (0.56, 0.5)),
                   ((0, -0.46, 2.82), (0.34, 0.3)), ((0, -0.74, 2.79), (0.28, 0.24))])
    head = H.build("Head", fur_body, subdiv=3, parent=root)
    displace(head, 0.02, 0.18)
    apply_mods(head)

    # stitched grin, far too wide
    pts, normals = [], []
    N = 25
    for k in range(N):
        a = R(-82 + 164 * k / (N - 1))
        z = 2.71 + 0.17 * (1 - math.cos(a)) ** 1.3
        loc, n = surface_point(head, (0, -0.1, z), (math.sin(a), -math.cos(a), 0))
        pts.append(loc)
        normals.append(n)
    C = Skel()
    prev = None
    for k, (p, n) in enumerate(zip(pts, normals)):
        t = abs(k - (N - 1) / 2) / ((N - 1) / 2)
        r = 0.085 * (1 - 0.45 * t)
        idx = C.p(p - n * 0.01, (r * 0.6, r))
        if prev is None:
            C.roots.append(idx)
        else:
            C.e.append((prev, idx))
        prev = idx
    cutter = C.build("MouthCut", None, subdiv=1)
    apply_mods(cutter)
    boolean(head, cutter)
    G = Skel()
    prev = None
    for k, (p, n) in enumerate(zip(pts, normals)):
        t = abs(k - (N - 1) / 2) / ((N - 1) / 2)
        idx = G.p(p - n * 0.045, 0.05 * (1 - 0.5 * t))
        if prev is None:
            G.roots.append(idx)
        else:
            G.e.append((prev, idx))
        prev = idx
    G.build("Gums", gums, subdiv=2, parent=root)
    random.seed(5)
    up = Vector((0, 0, 1))
    for k in range(1, N - 1):
        p, n = pts[k], normals[k]
        t = abs(k - (N - 1) / 2) / ((N - 1) / 2)
        h = 0.085 * (1 - 0.45 * t)
        ln = random.uniform(0.8, 1.25)
        seg("ToothU%d" % k, p - n * 0.025 + up * h * 0.9, p - n * 0.008 - up * h * 0.45 * ln,
            0.02, teeth, root, r2=0.002, verts=8)
        if k % 2 == 0 or random.random() < 0.4:
            seg("ToothL%d" % k, p - n * 0.025 - up * h * 0.9, p - n * 0.008 + up * h * 0.35 * ln,
                0.018, teeth, root, r2=0.002, verts=8)
        if k % 3 == 1:
            seg("MouthStitch%d" % k, p + n * 0.004 + up * (h + 0.025), p + n * 0.004 - up * (h + 0.025),
                0.005, thread, root, verts=6)
    # scar stitches running from the mouth corners toward the ears
    for s, k in ((-1, 0), (1, N - 1)):
        p, n = pts[k], normals[k]
        end, n2 = surface_point(head, (0, -0.05, 2.98), (s * 1, -0.35, 0.25))
        stitch_line("CornerScar%s" % ("L" if s < 0 else "R"), p, end, n, thread, root, count=5, size=0.04)

    # nose
    nloc, nn = surface_point(head, (0, -0.1, 2.88), (0, -1, 0.25))
    prim("sphere", "Nose", nloc + nn * 0.02, (0.1, 0.07, 0.075), m=nose, parent=root)

    # left eye: a big glossy button sewn on
    eloc, en = surface_point(head, (-0.12, -0.1, 3.03), (-0.35, -1, 0.05))
    btn = prim("cyl", "ButtonEye", eloc + en * 0.012, (0.09, 0.09, 0.028), m=button, parent=root,
               vertices=32)
    bpy.context.view_layer.update()
    from lib import orient
    orient(btn, eloc, eloc + en)
    bevel(btn, 0.01, 3)
    apply_mods(btn)
    for i, (dx, dz) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        side = en.cross(up).normalized()
        hp = eloc + side * dx * 0.025 + up * dz * 0.025
        hole = seg("Hole%d" % i, hp - en * 0.05, hp + en * 0.08, 0.011)
        boolean(btn, hole)
    side = en.cross(up).normalized()
    for sgn in (-1, 1):
        a = eloc + en * 0.03 + side * 0.025 + up * 0.025 * sgn
        b = eloc + en * 0.03 - side * 0.025 - up * 0.025 * sgn
        seg("EyeThread%d" % sgn, a, b, 0.005, thread, root, verts=6)

    # right eye: button torn off, a real eye stares out of the socket
    sloc, sn = surface_point(head, (0.12, -0.1, 3.03), (0.35, -1, 0.05))
    sock = prim("ico", "SocketCut", sloc, (0.1, 0.1, 0.1), subdivisions=3)
    displace(sock, 0.03, 0.05)
    apply_mods(sock)
    boolean(head, sock)
    eb = prim("sphere", "Eyeball", sloc - sn * 0.06, (0.078, 0.078, 0.078), m=eyeball, parent=root)
    look = Vector((-0.6, -5.5, 1.6)) - (sloc - sn * 0.06)
    look.normalize()
    ir = prim("cyl", "Iris", sloc - sn * 0.06 + look * 0.072, (0.034, 0.034, 0.01), m=iris, parent=root)
    orient(ir, (0, 0, 0), look)
    pu = prim("cyl", "Pupil", sloc - sn * 0.06 + look * 0.079, (0.012, 0.012, 0.006), m=pupil, parent=root)
    orient(pu, (0, 0, 0), look)
    prim("sphere", "Socket", sloc - sn * 0.11, (0.09, 0.09, 0.09), m=gums, parent=root)
    # the old button dangles on its thread
    hang_p = sloc + Vector((0.05, -0.08, -0.32))
    seg("DangleThread", sloc + Vector((0.0, -0.02, -0.06)), hang_p + Vector((0, 0, 0.05)), 0.004, thread, root, verts=6)
    hb = prim("cyl", "LooseButton", hang_p, (0.085, 0.085, 0.026), m=button, parent=root,
              rot=(R(70), R(20), 0), vertices=32)
    bevel(hb, 0.01, 3)
    random.seed(2)
    for i in range(5):
        a = random.uniform(0, 2 * math.pi)
        p = sloc + (side * math.cos(a) + up * math.sin(a)) * 0.09
        seg("Fray%d" % i, p, p + Vector((random.uniform(-.02, .02), -0.03, -random.uniform(0.04, 0.1))),
            0.003, thread, root, verts=5)

    # ears (right one torn)
    ears = []
    for s in (-1, 1):
        e = prim("sphere", "Ear%s" % ("L" if s < 0 else "R"), (0.41 * s, 0.04, 3.36),
                 (0.21, 0.08, 0.21), m=fur_body, parent=root, rot=(R(-8), R(18 * s), 0))
        displace(e, 0.015, 0.1)
        apply_mods(e)
        inner = prim("sphere", "EarInner%s" % ("L" if s < 0 else "R"), (0.41 * s, -0.025, 3.34),
                     (0.14, 0.03, 0.14), m=belly_plush, parent=root, rot=(R(-8), R(18 * s), 0))
        if s > 0:
            boolean(e, tear_cutter((0.55, 0.0, 3.5), (0.12, 0.2, 0.1), 9))
            boolean(inner, tear_cutter((0.55, 0.0, 3.5), (0.12, 0.2, 0.1), 9))
        ears.append(e)

    # ------------------------------------------------------------ claws
    def claws(base, fwd, count, spread, length, name):
        fwd = Vector(fwd).normalized()
        side = fwd.cross(up).normalized()
        for i in range(count):
            o = side * spread * (i - (count - 1) / 2)
            p0 = Vector(base) + o
            K = Skel()
            K.chain(None, [(p0, 0.024), (p0 + fwd * length * 0.35 - up * length * 0.35, 0.017),
                           (p0 + fwd * length * 0.55 - up * length * 0.75, 0.009),
                           (p0 + fwd * length * 0.45 - up * length * 1.0, 0.0015)])
            K.build("%s%d" % (name, i), claw, subdiv=2, parent=root)

    pl, _ = surface_out(body, (-0.93, -0.2, 0.8), (0, -0.6, -1))
    claws(pl + Vector((0, 0.04, 0.05)), (0, -1, -0.3), 4, 0.075, 0.34, "ClawL")
    pr, _ = surface_out(body, (0.96, -0.36, 0.68), (0, -0.6, -1))
    claws(pr + Vector((0, 0.04, 0.05)), (0, -1, -0.3), 4, 0.075, 0.34, "ClawR")
    for s in (-1, 1):
        tl, _ = surface_out(body, (0.34 * s, -0.3, 0.16), (0, -1, 0))
        claws(tl + Vector((0, 0.03, 0.04)), (0, -1, 0.9), 3, 0.09, 0.13, "Toe%s" % s)

    # ------------------------------------------------------------ fur
    body.data.materials.append(fur_hair)
    dens = density_group(body, [tear_at], 0.3, 0.42)
    add_fur(body, "GrinnyFur", count=9000, length=0.055, children=24, clump=0.7, rough=0.03, seed=1, density=dens)
    head.data.materials.append(fur_hair)
    face_pts = [eloc, sloc, nloc] + list(pts)
    dens = density_group(head, face_pts, 0.1, 0.16)
    add_fur(head, "GrinnyFur", count=6000, length=0.04, children=24, clump=0.6, rough=0.03, seed=2, density=dens)
    for i, e in enumerate(ears):
        e.data.materials.append(fur_hair)
        add_fur(e, "GrinnyFur", count=700, length=0.03, children=20, seed=3 + i)
    patch.data.materials.append(belly_hair)
    add_fur(patch, "BellyFur", count=4000, length=0.028, children=20, clump=0.4, seed=7)
    fiber = mat_fur_hair("StuffingFiber", "#d6cfbd", "#efe9da", "#8f8570")
    for i, st in enumerate(stuff_objs):
        st.data.materials.append(fiber)
        add_fur(st, "StuffingFiber", count=300, length=0.035, children=30, clump=0.0, rough=0.06,
                radius=0.0012, seed=20 + i)

    # tilt the whole head unnaturally to one side
    bpy.context.view_layer.update()
    for o in list(bpy.data.objects):
        if o is head_pivot or o.parent is not root or o.type != "MESH":
            continue
        if o.matrix_world.translation.z > 2.5 or o.name.startswith(("Ear", "Head", "Tooth", "Mouth",
                                                                    "Gums", "Corner", "Nose", "Button",
                                                                    "EyeThread", "Eyeball", "Iris",
                                                                    "Pupil", "Socket", "Dangle",
                                                                    "Loose", "Fray")):
            mw = o.matrix_world.copy()
            o.parent = head_pivot
            o.matrix_world = mw
    head_pivot.rotation_euler = (R(8), R(-16), R(6))
    return root
