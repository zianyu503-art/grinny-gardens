"""The Director - final boss living inside the Ferris wheel. A 5 m mass of fused
plush toys and flesh, studded with doll heads, real eyes and reaching arms."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, Mat, prim, seg, empty, apply_mods, displace, boolean, orient, subsurf, smooth,
                 mat_plush, mat_flesh, mat_teeth, mat_eyeball, mat_simple, mat_stripes, R)

FRAME = dict(height=5.0, center=(0, 0, 2.4))
SHOTS = [
    ("hero", "horror", (-3.2, -7.4, 0.9), (0, 0, 2.7), 28),
    ("studio", "studio", (5.2, -7.0, 2.8), (0, 0, 2.4), 32),
    ("face", "horror", (-1.6, -5.6, 2.2), (0, -1.2, 2.5), 40),
]
CAM = Vector((-3.2, -7.4, 0.9))
CENTER = Vector((0, 0, 2.4))


def mass_material():
    """Flesh bleeding through patches of filthy plush."""
    M = Mat("DirectorMass")
    mask_n = M.noise(0.9, 6, 0.6, distortion=0.8)
    flesh_c = M.ramp(M.noise(5, 10, 0.65, distortion=1.0), [(0.3, "#140305"), (0.5, "#3e0a10"), (0.75, "#6a1c22")])
    plush_c = M.ramp(M.noise(3, 10, 0.65), [(0.3, "#1e1818"), (0.5, "#3e3234"), (0.75, "#5a4a44")])
    mask = M.ramp(mask_n, [(0.52, "#000000"), (0.6, "#ffffff")])
    col = M.mix(mask, flesh_c, plush_c)
    grime = M.ramp(M.noise(2, 6, 0.5), [(0.4, "#ffffff"), (0.8, "#3a2a20")])
    col = M.mix(1.0, col, grime, "MULTIPLY")
    rough = M.ramp(mask_n, [(0.52, "#3a3a3a"), (0.6, "#f0f0f0")])
    sss = M.ramp(mask_n, [(0.52, "#4d4d4d"), (0.6, "#000000")])
    M.set(color=col, rough=rough, sss=sss, sss_radius=(1.0, 0.25, 0.15), sss_scale=0.08, sheen=0.4)
    M.bump(M.math(M.noise(25, 8, 0.7), M.voronoi(6, "DISTANCE_TO_EDGE"), "ADD"), 0.4, 0.03)
    return M.m


def surface(obj, direction):
    d = Vector(direction).normalized()
    ok, loc, n, _ = obj.ray_cast(CENTER + d * 8.0, -d)
    return (loc, n) if ok else (None, None)


def rand_dir(front_bias=0.6, zmin=-0.6, zmax=0.9):
    while True:
        v = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(zmin, zmax)))
        if v.length < 0.2:
            continue
        v.normalize()
        if v.y < 0 or random.random() > front_bias:
            return v


def build():
    random.seed(13)
    mass_m = mass_material()
    flesh = mat_flesh("DirectorFlesh", "#3a080e", "#0a0204", "#6a1a22", vein_scale=14, sss=0.2)
    teeth = mat_teeth()
    eyeball = mat_eyeball()
    pupil = mat_simple("Pupil", "#010101", 0.05, coat=1.0)
    irises = [mat_simple("IrisA", "#6a7a3a", 0.15, coat=1), mat_simple("IrisB", "#3a5a7a", 0.15, coat=1),
              mat_simple("IrisC", "#7a5a2a", 0.15, coat=1), mat_simple("IrisMilk", "#b8b8a8", 0.3, coat=1)]
    plushes = [mat_plush("DollPink", "#8a5a62", "#3a2026", "#b08a8a"),
               mat_plush("DollBlue", "#4a5a7a", "#1e2430", "#7a8aa0"),
               mat_plush("DollYellow", "#9a8a4a", "#3a3218", "#c0b070"),
               mat_plush("DollGreen", "#4a6a4a", "#1a2a1a", "#7a9a7a"),
               mat_plush("DollWhite", "#a8a090", "#4a4438", "#d0c8b8")]
    button = mat_simple("ButtonPlastic", "#0e0806", 0.18, coat=0.8)
    dead_skin = mat_simple("DeadSkinArm", "#6a645a", 0.55, sss=0.15, sss_radius=(0.6, 0.3, 0.2), sss_scale=0.03)
    nail = mat_simple("Nail", "#1a140e", 0.3, coat=0.5)
    hat_m = mat_simple("HatFelt", "#0c0a0c", 0.85, sheen=0.6)
    band_m = mat_stripes("HatBand", "#5a0c10", "#b09a5a", scale=30, direction="Z")
    thread = mat_simple("Thread", "#1c0605", 0.8)

    root = empty("Director")

    # ------------------------------------------------------------ the mass
    mb = bpy.data.metaballs.new("MassMeta")
    mb.resolution = 0.07
    mb.render_resolution = 0.07
    mb.threshold = 0.3
    blobs = [((0, 0.1, 0.9), (1.5, 1.4, 1.0)), ((0, 0.15, 2.2), (1.6, 1.4, 1.1)), ((0.1, 0.0, 3.4), (1.2, 1.1, 0.95)),
             ((0.45, -0.2, 4.3), (0.7, 0.62, 0.62)), ((-1.3, 0.2, 0.5), (0.75, 0.65, 0.55)),
             ((1.2, 0.5, 0.45), (0.7, 0.6, 0.5)), ((-1.2, -0.4, 2.6), (0.65, 0.6, 0.7)),
             ((-0.9, 0.3, 3.7), (0.6, 0.55, 0.55)), ((1.25, -0.35, 2.9), (0.55, 0.55, 0.55)),
             ((1.75, -0.6, 2.35), (0.4, 0.35, 0.4)), ((0.4, -1.0, 0.4), (0.65, 0.55, 0.45)),
             ((-0.6, -0.9, 0.35), (0.55, 0.5, 0.4)), ((0.0, -0.9, 1.5), (0.7, 0.5, 0.6))]
    for (x, y, z), (rx, ry, rz) in blobs:
        el = mb.elements.new(type="ELLIPSOID")
        el.co = (x, y, z)
        el.radius = 1.6
        el.size_x, el.size_y, el.size_z = rx, ry, rz
        el.stiffness = 1.0
    mo = bpy.data.objects.new("Mass", mb)
    bpy.context.collection.objects.link(mo)
    bpy.context.view_layer.update()
    apply_mods(mo)
    mass = bpy.context.active_object
    for o in list(bpy.data.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    mass.name = "Mass"
    mass.parent = root
    mass.data.materials.clear()
    mass.data.materials.append(mass_m)
    smooth(mass)
    displace(mass, 0.32, 1.3)
    apply_mods(mass)
    displace(mass, 0.09, 0.4, depth=3)
    apply_mods(mass)
    displace(mass, 0.04, 0.08, depth=4)
    apply_mods(mass)
    # flesh drips sagging to the floor
    for i in range(9):
        d = rand_dir(0.5, -0.3, 0.3)
        loc, n = surface(mass, d)
        if loc is None or loc.z < 0.6:
            continue
        D = Skel()
        D.chain(None, [(loc - n * 0.1, 0.16), (loc + n * 0.12 + Vector((0, 0, -loc.z * 0.45)), 0.08),
                       (loc + n * 0.18 + Vector((0, 0, -loc.z * 0.85)), 0.05),
                       (Vector((loc.x + n.x * 0.2, loc.y + n.y * 0.2, 0.03)), 0.1)])
        dr = D.build("Drip%d" % i, flesh, subdiv=2, parent=root)
        displace(dr, 0.02, 0.05)

    # the maw: a vertical tear in the front lined with teeth
    maw_c = Vector((0.05, -1.55, 2.3))
    cut = prim("ico", "MawCut", maw_c, (0.45, 0.9, 0.85), subdivisions=4)
    displace(cut, 0.08, 0.2)
    apply_mods(cut)
    boolean(mass, cut)
    gullet = prim("ico", "Gullet", maw_c + Vector((0, 0.55, 0)), (0.5, 0.45, 0.8), m=flesh, parent=root, subdivisions=4)
    displace(gullet, 0.06, 0.12)
    tongue = Skel()
    tongue.chain(None, [(maw_c + Vector((0, 0.35, -0.45)), (0.2, 0.08)), (maw_c + Vector((0.05, -0.2, -0.5)), (0.18, 0.07)),
                        (maw_c + Vector((0.12, -0.55, -0.75)), (0.13, 0.05)), (maw_c + Vector((0.15, -0.7, -1.1)), 0.06)])
    tg = tongue.build("Tongue", flesh, subdiv=2, parent=root)
    displace(tg, 0.02, 0.05)
    for k in range(44):
        a = 2 * math.pi * k / 44
        rim = maw_c + Vector((0.4 * math.cos(a), 0.15, 0.78 * math.sin(a)))
        loc, n = surface(mass, rim - CENTER + Vector((0, -0.6, 0)))
        if loc is None:
            continue
        inward = (maw_c + Vector((0, 0.3, 0)) - rim)
        inward.normalize()
        L = random.uniform(0.08, 0.2) * (1.3 if abs(math.sin(a)) < 0.5 else 1.0)
        base_p = rim + Vector((0, -0.05, 0))
        seg("MawTooth%d" % k, base_p, base_p + inward * L + Vector((0, -0.03, 0)),
            random.uniform(0.025, 0.045), teeth, root, r2=0.004, verts=8)
    for k in range(44):
        a = 2 * math.pi * k / 44
        j = random.uniform(-0.04, 0.04)
        p = maw_c + Vector(((0.46 + j) * math.cos(a), 0.04 + random.uniform(-0.04, 0.04), (0.88 + j) * math.sin(a)))
        sz = random.uniform(0.7, 1.4)
        lb = prim("ico", "Lip%d" % k, p, (0.11 * sz, 0.07 * sz, 0.12 * sz), m=flesh, parent=root, subdivisions=4,
                  rot=(0, -a, 0))
        displace(lb, 0.035, 0.05, depth=3)

    # ------------------------------------------------------------ embedded doll heads
    def doll_head(i, loc, n, r):
        m = random.choice(plushes)
        c = loc - n * r * 0.35
        h = prim("sphere", "DollHead%d" % i, c, (r, r, r * 0.95), m=m, parent=root)
        displace(h, r * 0.06, r * 0.5)
        side = n.cross(Vector((0, 0, 1)))
        if side.length < 0.1:
            side = Vector((1, 0, 0))
        side.normalize()
        upv = side.cross(n).normalized()
        if upv.z < 0:
            upv = -upv
        for s in (-1, 1):
            e = prim("sphere", "DollEar%d_%d" % (i, s), c + side * r * 0.75 * s + upv * r * 0.75,
                     (r * 0.35, r * 0.35, r * 0.35), m=m, parent=root)
            e.scale = (r * 0.35, r * 0.35, r * 0.12)
            orient(e, (0, 0, 0), n)
        prim("sphere", "DollMuzzle%d" % i, c + n * r * 0.8 - upv * r * 0.25, (r * 0.4, r * 0.4, r * 0.4),
             m=random.choice(plushes), parent=root)
        kind = random.random()
        for s in (-1, 1):
            ep = c + n * r * 0.88 + side * r * 0.38 * s + upv * r * 0.22
            if kind < 0.45 or (kind < 0.7 and s > 0):
                b = prim("cyl", "DollButton%d_%d" % (i, s), ep, (r * 0.17, r * 0.17, r * 0.05), m=button, parent=root)
                orient(b, (0, 0, 0), n)
                for sg in (-1, 1):
                    seg("DollThread%d_%d_%d" % (i, s, sg), ep + n * r * 0.04 + (side + upv * sg) * r * 0.07,
                        ep + n * r * 0.04 - (side + upv * sg) * r * 0.07, r * 0.012, thread, root, verts=5)
            elif kind < 0.85:
                add_eye(i * 10 + s, ep, n, r * 0.19)
            # else: empty, stitched shut
            else:
                for k in range(3):
                    seg("Shut%d_%d_%d" % (i, s, k), ep + side * r * (0.1 * (k - 1)) + upv * r * 0.08,
                        ep + side * r * (0.1 * (k - 1)) - upv * r * 0.08, r * 0.015, thread, root, verts=5)

    def add_eye(i, loc, n, r, lid=False):
        c = loc - n * r * 0.25
        prim("sphere", "Eye%d" % i, c, (r, r, r), m=eyeball, parent=root)
        look = (CAM + Vector((random.uniform(-0.6, 0.6), 0, random.uniform(-0.4, 0.4))) - c).normalized()
        ir = prim("cyl", "Iris%d" % i, c + look * r * 0.92, (r * 0.45, r * 0.45, r * 0.08),
                  m=random.choice(irises), parent=root)
        orient(ir, (0, 0, 0), look)
        pu = prim("cyl", "Pupil%d" % i, c + look * r * 0.99, (r * 0.2, r * 0.2, r * 0.05), m=pupil, parent=root)
        orient(pu, (0, 0, 0), look)
        if lid:
            t = prim("torus", "Lid%d" % i, c + n * r * 0.4, (1, 1, 1), m=flesh, parent=root,
                     major_radius=r * 0.95, minor_radius=r * 0.2, major_segments=32, minor_segments=10)
            orient(t, (0, 0, 0), n)
            t.scale = (1, 0.75, 1)
            displace(t, r * 0.18, r * 0.25)

    placed = []

    def free_spot(loc, r):
        for p, pr in placed:
            if (p - loc).length < (r + pr) * 1.1:
                return False
        return True

    maw_keepout = maw_c
    tries = 0
    count = 0
    while count < 48 and tries < 1500:
        tries += 1
        d = rand_dir(0.65)
        loc, n = surface(mass, d)
        if loc is None or (loc - maw_keepout).length < 1.2:
            continue
        r = random.uniform(0.22, 0.5) if count < 30 else random.uniform(0.15, 0.28)
        if not free_spot(loc, r * 0.8):
            continue
        placed.append((loc, r * 0.8))
        doll_head(count, loc, n, r)
        count += 1

    # big real eyes in the flesh
    tries = 0
    count = 0
    while count < 16 and tries < 600:
        tries += 1
        d = rand_dir(0.85, -0.2, 0.9)
        loc, n = surface(mass, d)
        if loc is None or (loc - maw_keepout).length < 1.1:
            continue
        r = random.uniform(0.1, 0.26)
        if not free_spot(loc, r * 1.4):
            continue
        placed.append((loc, r * 1.4))
        add_eye(200 + count, loc, n, r, lid=True)
        count += 1

    # ------------------------------------------------------------ reaching arms
    def arm(i, loc, n, human):
        m = dead_skin if human else random.choice(plushes)
        L = random.uniform(0.9, 1.6)
        down = Vector((0, 0, -1))
        p0 = loc - n * 0.1
        p1 = loc + n * L * 0.45 + down * 0.1
        p2 = p1 + (n * 0.6 + down * 0.8).normalized() * L * 0.5
        rad = 0.1 if human else 0.14
        A = Skel()
        A.chain(None, [(p0, rad * 1.4), (p1, rad), (p1.lerp(p2, 0.5), rad * 0.85), (p2, rad * 0.75)])
        a = A.build("Arm%d" % i, m, subdiv=2, parent=root)
        displace(a, 0.01, 0.08)
        fwd = (p2 - p1).normalized()
        side = fwd.cross(Vector((0, 0, 1)))
        if side.length < 0.1:
            side = Vector((1, 0, 0))
        side.normalize()
        palm = p2 + fwd * rad * 1.1
        prim("sphere", "Palm%d" % i, palm, (rad * 1.1, rad * 1.1, rad * 1.1), m=m, parent=root)
        if human:
            for f in range(4):
                fb = palm + side * (f - 1.5) * rad * 0.55 + fwd * rad * 0.6
                curl = random.uniform(0.2, 0.9)
                F = Skel()
                fl = rad * 1.4
                F.chain(None, [(fb, rad * 0.24), (fb + fwd * fl * 0.5, rad * 0.21),
                               (fb + fwd * fl * (1 - 0.3 * curl) + down * fl * 0.35 * curl, rad * 0.18),
                               (fb + fwd * fl * (1.15 - 0.6 * curl) + down * fl * 0.7 * curl, rad * 0.15)])
                F.build("Finger%d_%d" % (i, f), m, subdiv=2, parent=root)
                tip = fb + fwd * fl * (1.15 - 0.6 * curl) + down * fl * 0.7 * curl
                prim("sphere", "Nail%d_%d" % (i, f), tip + down * rad * 0.06, (rad * 0.13, rad * 0.13, rad * 0.06),
                     m=nail, parent=root)

    tries = 0
    count = 0
    while count < 14 and tries < 600:
        tries += 1
        d = rand_dir(0.6, -0.5, 0.6)
        loc, n = surface(mass, d)
        if loc is None or (loc - maw_keepout).length < 1.2 or not free_spot(loc, 0.25):
            continue
        placed.append((loc, 0.25))
        arm(count, loc, n, human=count % 3 != 0)
        count += 1

    # ------------------------------------------------------------ ringmaster's top hat
    top, tn = surface(mass, (0.35, -0.2, 1.0))
    hat_axis = (tn + Vector((0.2, 0, 1))).normalized()
    hc = top + hat_axis * 0.1
    brim = prim("cyl", "HatBrim", hc, (0.62, 0.62, 0.03), m=hat_m, parent=root)
    orient(brim, (0, 0, 0), hat_axis)
    crown = seg("HatCrown", hc, hc + hat_axis * 0.85, 0.42, hat_m, root, r2=0.45, verts=32)
    dent = prim("ico", "HatDent", hc + hat_axis * 0.85 + Vector((0.3, -0.2, 0)), (0.25, 0.25, 0.2), subdivisions=3)
    boolean(crown, dent)
    band = seg("HatBand", hc + hat_axis * 0.05, hc + hat_axis * 0.2, 0.43, band_m, root, r2=0.435, verts=32)
    return root
