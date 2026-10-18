"""Second batch of park props: side attractions, clutter, signage and collectibles."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, Mat, prim, seg, empty, apply_mods, displace, boolean, orient, link_obj, smooth, lathe,
                 mat_painted_wood, mat_rust, mat_brass, mat_simple, mat_plush, mat_stripes, R)
from props import text, box, mat_wood, mat_metal, glow


def fan_slices(name, r_base, z_base, z_apex, n, mats, parent=None, r_top=0.0, open_base=True):
    """Cone/frustum split into n slices with alternating materials (circus stripes)."""
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        verts, faces = [], []
        steps = 4
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            verts.append((r_base * math.cos(a), r_base * math.sin(a), z_base))
            verts.append((r_top * math.cos(a), r_top * math.sin(a), z_apex))
        for i in range(steps):
            b = i * 2
            faces.append((b, b + 2, b + 3, b + 1))
        me = bpy.data.meshes.new("%s%d" % (name, k))
        me.from_pydata(verts, [], faces)
        me.update()
        o = link_obj(bpy.data.objects.new("%s%d" % (name, k), me))
        o.parent = parent
        me.materials.append(mats[k % len(mats)])
        smooth(o)


def circus_tent():
    red = mat_painted_wood("TentRed", "#7a1414")
    cream = mat_painted_wood("TentCream", "#c9b994")
    wood = mat_wood("PoleWood", "#4a3828")
    # walls (front gap for the entrance is cut in the game by leaving out colliders)
    fan_slices("Wall", 9, 0, 3.6, 20, [red, cream], r_top=9)
    fan_slices("Roof", 9.6, 3.4, 9.5, 20, [red, cream], r_top=0.4)
    seg("Pole", (0, 0, 0), (0, 0, 10.6), 0.25, wood, verts=12)
    seg("Flagpole", (0, 0, 10.6), (0, 0, 11.6), 0.04, wood, verts=6)
    box("Flag", (0.35, 0, 11.35), (0.7, 0.02, 0.4), red)
    for k in range(20):
        a = 2 * math.pi * k / 20
        prim("cone", "Scallop%d" % k, (9.65 * math.cos(a), 9.65 * math.sin(a), 3.15), (0.7, 0.7, 0.55),
             m=cream if k % 2 else red, rot=(math.pi, 0, 0), vertices=6, shade_smooth=False)
    # entrance flaps pulled aside
    for s in (-1, 1):
        box("Flap%d" % s, (1.9 * s, -9.15, 1.8), (1.4, 0.06, 3.6), red, rot=(0, 0, R(28 * s)))
    box("EntrySign", (0, -9.3, 4.0), (3.6, 0.1, 0.8), cream)
    text("EntryText", "BIG TOP", (0, -9.37, 4.0), 0.55, red)
    # ring, bleachers, trapeze
    lathe("Ring", [(3.2, 0), (3.2, 0.45), (3.0, 0.45), (3.0, 0)], segments=40, m=red)
    prim("cyl", "Sawdust", (0, 0, 0.02), (3.0, 3.0, 0.04), m=mat_simple("Sawdust", "#6a5232", 0.95), vertices=40)
    for row in range(3):
        for k in range(9):
            a = math.pi * 0.25 + math.pi * 0.5 * k / 8 + math.pi * 0.5
            r = 5.6 + row * 0.9
            box("Bench%d_%d" % (row, k), (r * math.cos(a), r * math.sin(a), 0.3 + row * 0.45),
                (1.4, 0.6, 0.12 + row * 0.9), wood, rot=(0, 0, a + math.pi / 2))
    seg("TrapL", (-1.2, 0, 8.8), (-1.2, 0, 4.5), 0.012, mat_simple("Rope", "#5a4a30", 0.9), verts=4)
    seg("TrapR", (1.2, 0, 8.8), (1.2, 0, 4.5), 0.012, mat_simple("Rope", "#5a4a30", 0.9), verts=4)
    seg("TrapBar", (-1.2, 0, 4.5), (1.2, 0, 4.5), 0.03, mat_brass(), verts=8)
    # tears in the canvas
    for i, (x, y, z) in enumerate(((6, 6.5, 2.2), (-7.5, 4.5, 6), (2, 8.6, 1.4))):
        prim("ico", "Tear%d" % i, (x, y, z), (0.6, 0.6, 0.9), m=mat_simple("Black", "#020202", 1.0), subdivisions=2)


def bumper_arena():
    steel = mat_metal("ArenaSteel", "#3a3a40")
    yellow = mat_metal("ArenaYellow", "#9a7a18")
    rubber = mat_simple("Rubber", "#101010", 0.8)
    box("Floor", (0, 0, 0.03), (14, 10, 0.06), mat_metal("FloorPlate", "#2a2a2c"))
    for x in (-7, 0, 7):
        for y in (-5, 5):
            seg("Post%d%d" % (x, y), (x, y, 0), (x, y, 4.2), 0.12, yellow, verts=10)
    box("Roof", (0, 0, 4.35), (14.8, 10.8, 0.3), steel)
    for i in range(15):
        seg("Grid%d" % i, (-7 + i, -5, 4.15), (-7 + i, 5, 4.15), 0.015, steel, verts=4)
    for i in range(11):
        seg("GridB%d" % i, (-7, -5 + i, 4.12), (7, -5 + i, 4.12), 0.015, steel, verts=4)
    stripes = mat_stripes("ArenaStripe", "#7a1414", "#c9b994", 4, "X")
    for side, (cx, cy, w, d) in {"N": (0, 5.4, 14.8, 0.1), "E": (7.4, 0, 0.1, 10.8), "W": (-7.4, 0, 0.1, 10.8)}.items():
        box("Valance" + side, (cx, cy, 4.0), (w, d, 0.6), stripes)
    box("ValanceS1", (-4.6, -5.4, 4.0), (5.6, 0.1, 0.6), stripes)
    box("ValanceS2", (4.6, -5.4, 4.0), (5.6, 0.1, 0.6), stripes)
    box("Sign", (0, -5.5, 4.9), (6, 0.15, 1.0), mat_painted_wood("SignBlue", "#1a3a6a"))
    text("SignText", "BUMPER CARS", (0, -5.6, 4.9), 0.6, mat_simple("White", "#d0c8b0", 0.5))
    # rubber barrier with an entrance gap at the front
    for name, (cx, cy, w, d) in {"BN": (0, 4.85, 14, 0.3), "BE": (6.85, 0, 0.3, 10), "BW": (-6.85, 0, 0.3, 10),
                                 "BS1": (-4.5, -4.85, 5, 0.3), "BS2": (4.5, -4.85, 5, 0.3)}.items():
        box(name, (cx, cy, 0.3), (w, d, 0.6), rubber)


def bumper_car():
    paint = mat_painted_wood("CarPaint", "#c8c0b0")
    rubber = mat_simple("Rubber", "#101010", 0.8)
    b = box("Body", (0, 0, 0.45), (1.3, 1.9, 0.5), paint)
    b.modifiers.new("Sub", "SUBSURF").levels = 2
    prim("torus", "Bumper", (0, 0, 0.3), (0.72, 1.02, 1.0), m=rubber, major_radius=1.0, minor_radius=0.12,
         major_segments=32, minor_segments=8)
    box("Seat", (0, 0.35, 0.8), (1.0, 0.5, 0.5), mat_simple("Leather", "#2a0a0a", 0.6))
    seg("Column", (0, -0.4, 0.6), (0, -0.25, 1.0), 0.03, mat_rust(), verts=6)
    prim("torus", "Wheel", (0, -0.25, 1.0), (1, 1, 1), m=rubber, rot=(R(60), 0, 0), major_radius=0.17,
         minor_radius=0.025, major_segments=16, minor_segments=6)
    seg("Pole", (0, 0.7, 0.7), (0, 0.7, 4.0), 0.025, mat_rust(), verts=6)
    prim("cone", "Brush", (0, 0.7, 4.05), (0.08, 0.08, 0.12), m=mat_brass(), vertices=8)


def teacups():
    pink = mat_painted_wood("CupPink", "#b07888")
    blue = mat_painted_wood("CupBlue", "#5a7aa8")
    yellow = mat_painted_wood("CupYellow", "#b8a058")
    prim("cyl", "Base", (0, 0, 0.15), (5.2, 5.2, 0.3), m=mat_metal("CupBase", "#4a3a5a"), vertices=40)
    spin = empty("Part_Spin", (0, 0, 0))
    prim("cyl", "Turntable", (0, 0, 0.35), (4.8, 4.8, 0.1), m=mat_painted_wood("Turn", "#6a5a7a"), parent=spin, vertices=40)
    prof = [(0.0, 0.0), (0.55, 0.0), (0.95, 0.25), (1.15, 0.65), (1.2, 1.05), (1.12, 1.05), (1.06, 0.68), (0.88, 0.32), (0.0, 0.08)]
    for i, m in enumerate((pink, blue, yellow)):
        a = 2 * math.pi * i / 3
        cx, cy = 2.9 * math.cos(a), 2.9 * math.sin(a)
        cup = lathe("Cup%d" % i, prof, segments=32, m=m, parent=spin)
        cup.location = (cx, cy, 0.4)
        t = prim("torus", "Handle%d" % i, (cx + 1.25 * math.cos(a), cy + 1.25 * math.sin(a), 1.0), (1, 1, 1), m=m,
                 parent=spin, rot=(R(90), 0, a + math.pi / 2), major_radius=0.3, minor_radius=0.07,
                 major_segments=16, minor_segments=8)
        prim("cyl", "Wheel%d" % i, (cx, cy, 0.95), (0.25, 0.25, 0.06), m=mat_brass(), parent=spin)
        seg("Stem%d" % i, (cx, cy, 0.5), (cx, cy, 0.95), 0.04, mat_brass(), spin, verts=6)


def cotton_candy():
    pink = mat_painted_wood("CandyPink", "#c08098")
    glass = mat_simple("DirtyGlass", "#2a2a24", 0.1, metal=0.2)
    box("Cart", (0, 0, 0.6), (1.5, 0.8, 0.8), pink)
    for s in (-1, 1):
        prim("torus", "Wheel%d" % s, (0.7 * s, 0, 0.3), (1, 1, 1), m=mat_rust(), rot=(0, R(90), 0),
             major_radius=0.28, minor_radius=0.03, major_segments=20, minor_segments=6)
    prim("sphere", "Dome", (0, 0, 1.2), (0.5, 0.5, 0.35), m=glass)
    fluff = mat_plush("Candy", "#d0a0b8", "#7a4a5a", "#f0d0e0", stain="#4a2a3a", scale=10)
    random.seed(4)
    for i in range(5):
        p = Vector((-0.55 + 0.27 * i, -0.3, 1.25))
        seg("Cone%d" % i, p - Vector((0, 0, 0.25)), p, 0.02, mat_simple("Paper", "#c8c0a8", 0.9), r2=0.006, verts=6)
        f = prim("ico", "Floss%d" % i, p + Vector((0, 0, 0.12)), (0.13, 0.13, 0.16), m=fluff, subdivisions=3)
        displace(f, 0.05, 0.05)
    seg("UmbPole", (0, 0.3, 0.9), (0, 0.3, 2.6), 0.03, mat_rust(), verts=6)
    fan_slices("Umb", 1.4, 2.4, 2.9, 8, [pink, mat_painted_wood("CandyCream", "#d8d0c0")])


def striker():
    red = mat_painted_wood("StrikerRed", "#8a1414")
    cream = mat_painted_wood("StrikerCream", "#c9b994")
    box("Pad", (0, 0, 0.15), (0.8, 0.8, 0.3), mat_rust())
    box("Tower", (0, 0.1, 3.0), (0.4, 0.15, 6.0), cream)
    for i in range(10):
        box("Mark%d" % i, (0, -0.0, 0.8 + i * 0.5), (0.42, 0.02, 0.06), red)
    prim("sphere", "Bell", (0, 0.05, 6.2), (0.3, 0.3, 0.25), m=mat_brass())
    box("Sign", (0, 0.0, 6.7), (1.6, 0.1, 0.5), red)
    text("SignText", "TEST YOUR STRENGTH", (0, -0.06, 6.7), 0.14, cream)
    seg("Mallet", (0.6, -0.4, 0.0), (0.7, -0.2, 1.2), 0.03, mat_wood("Handle"), verts=6)
    seg("MalletHead", (0.55, -0.25, 1.2), (0.85, -0.15, 1.2), 0.12, mat_wood("Head", "#3a2a1a"), verts=10)


def billboard():
    plush = mat_painted_wood("BillPink", "#9a5a66")
    cream = mat_painted_wood("BillCream", "#c9b994")
    black = mat_simple("Black", "#050505", 0.4)
    for s in (-1, 1):
        seg("Leg%d" % s, (2.2 * s, 0.3, 0), (2.2 * s, 0.3, 6.5), 0.15, mat_rust(), verts=8)
    prim("cyl", "Head", (0, 0, 7.5), (3.0, 3.0, 0.25), m=plush, rot=(R(90), 0, 0), vertices=40)
    for s in (-1, 1):
        prim("cyl", "Ear%d" % s, (2.4 * s, 0, 10.0), (1.0, 1.0, 0.24), m=plush, rot=(R(90), 0, 0), vertices=24)
        prim("cyl", "Eye%d" % s, (1.0 * s, -0.15, 8.2), (0.35, 0.35, 0.06), m=black, rot=(R(90), 0, 0), vertices=20)
    prim("cyl", "Muzzle", (0, -0.14, 6.9), (1.2, 1.2, 0.05), m=cream, rot=(R(90), 0, 0), vertices=24)
    for k in range(17):
        a = R(-75 + 150 * k / 16)
        box("Smile%d" % k, (1.6 * math.sin(a), -0.2, 6.7 + 0.5 * (1 - math.cos(a))), (0.22, 0.05, 0.12), black)
    box("Banner", (0, -0.15, 4.0), (4.6, 0.08, 0.9), cream)
    text("BannerText", "SMILE!", (0, -0.21, 4.0), 0.7, mat_painted_wood("BillRed", "#8a1414"))
    # rusty bullet holes / tear
    prim("ico", "Hole", (-1.4, -0.15, 7.0), (0.5, 0.2, 0.6), m=black, subdivisions=2)


def signpost():
    wood = mat_wood("SignWood", "#4a3828")
    paint = mat_painted_wood("ArrowPaint", "#c9b994")
    red = mat_simple("SignRedTxt", "#6a1010", 0.6)
    seg("Post", (0, 0, 0), (0, 0, 3.0), 0.07, wood, verts=8)
    for i, (label, ang) in enumerate((("CAROUSEL", 20), ("FUN HOUSE", -15), ("EXIT", 160))):
        z = 2.6 - 0.45 * i
        piv = empty("Arrow%d" % i, (0, 0, z))
        piv.rotation_euler = (0, 0, R(ang))
        box("Board%d" % i, (0.75, 0, 0), (1.3, 0.05, 0.3), paint, piv)
        prim("cone", "Tip%d" % i, (1.5, 0, 0), (0.22, 0.03, 0.2), m=paint, parent=piv, rot=(0, R(90), 0),
             vertices=3, shade_smooth=False)
        t = text("Txt%d" % i, label, (0.7, -0.03, 0), 0.16, red, piv)


def mapboard():
    wood = mat_wood("MapWood", "#3a2a1a")
    red = mat_painted_wood("MapRed", "#7a1414")
    for s in (-1, 1):
        seg("Leg%d" % s, (1.4 * s, 0, 0), (1.4 * s, 0, 2.6), 0.08, wood, verts=8)
    box("Frame", (0, 0.05, 1.7), (2.8, 0.1, 1.9), wood)
    for sgn in (-1, 1):
        box("Roof%d" % sgn, (0, 0.05 + 0.22 * sgn, 2.98), (3.2, 0.5, 0.05), red, rot=(R(-30 * sgn), 0, 0))
    box("Plate", (0, -0.02, 2.75), (1.4, 0.05, 0.25), red)
    text("PlateText", "PARK MAP", (0, -0.05, 2.75), 0.15, mat_simple("White", "#d0c8b0", 0.5))
    scr = empty("Part_Screen", (0, -0.02, 1.68))
    prim("cube", "ScreenQuad", (0, 0, 0), (2.5, 0.02, 1.6), m=mat_simple("Paper", "#c8bfa8", 0.9), parent=scr,
         shade_smooth=False)


def photo():
    box("Frame", (0, 0, 0.055), (0.09, 0.006, 0.11), mat_simple("PolaWhite", "#d8d2c4", 0.7))
    ph = empty("Part_Photo", (0, -0.004, 0.062))
    box("Image", (0, 0, 0), (0.075, 0.002, 0.075), mat_simple("PhotoDark", "#2a2420", 0.6), ph)


def trashbags():
    bag = mat_simple("Bag", "#0c0c0e", 0.25, coat=0.6)
    random.seed(6)
    for i in range(7):
        p = Vector((random.uniform(-0.8, 0.8), random.uniform(-0.6, 0.6), 0.3 + (0.35 if i > 4 else 0)))
        b = prim("sphere", "Bag%d" % i, p, (0.4, 0.35, 0.32), m=bag)
        displace(b, 0.08, 0.15)
        prim("cone", "Knot%d" % i, p + Vector((0, 0, 0.35)), (0.08, 0.08, 0.15), m=bag, vertices=6)
    cardboard = mat_simple("Cardboard", "#6a5232", 0.95)
    box("Box1", (1.1, 0.3, 0.25), (0.6, 0.5, 0.5), cardboard, rot=(0, 0, 0.3))
    box("Box2", (1.0, -0.5, 0.15), (0.5, 0.4, 0.3), cardboard, rot=(0, R(10), 0.8))


def turnstile():
    steel = mat_metal("TurnSteel", "#4a4e50")
    box("Body", (0, 0, 0.5), (0.3, 0.9, 1.0), steel)
    for k in range(3):
        a = 2 * math.pi * k / 3
        seg("Arm%d" % k, (0.2, 0, 0.85), (0.2 + 0.6 * math.cos(a) * 0.3, 0.6 * math.sin(a), 0.85 + 0.5 * math.cos(a)),
            0.025, mat_rust(), verts=6)
    box("Rail", (0.8, 0, 0.9), (1.4, 0.05, 0.05), steel)


def circus_wagon():
    red = mat_painted_wood("WagonRed", "#7a1414")
    gold = mat_brass()
    box("Floor", (0, 0, 0.9), (3.6, 1.8, 0.2), red)
    box("Roof", (0, 0, 3.0), (3.8, 2.0, 0.2), red)
    box("Back", (0, 0.85, 1.95), (3.6, 0.1, 1.9), red)
    for s in (-1, 1):
        box("Side%d" % s, (1.75 * s, 0, 1.95), (0.1, 1.8, 1.9), red)
        for y in (-0.6, 0.6):
            prim("torus", "Wheel%d%.1f" % (s, y), (1.3 * y / 0.6, -0.95 * s, 0.6), (1, 1, 1), m=gold,
                 rot=(R(90), 0, 0), major_radius=0.5, minor_radius=0.05, major_segments=24, minor_segments=6)
    for i in range(17):
        x = -1.6 + 0.2 * i
        if i == 9:
            seg("BentBar", (x, -0.85, 1.0), (x + 0.3, -1.1, 2.0), 0.025, mat_rust(), verts=6)
            continue
        seg("Bar%d" % i, (x, -0.85, 1.0), (x, -0.85, 2.9), 0.025, mat_rust(), verts=6)
    box("Sign", (0, -0.95, 3.25), (2.6, 0.08, 0.4), gold)
    text("SignText", "WILD BEASTS", (0, -1.0, 3.25), 0.24, red)
    # something left inside: a stained, torn plush lion
    lion = mat_plush("Lion", "#9a7a3a", "#3a2a10", "#c8a860")
    prim("sphere", "LionBody", (0.4, 0.2, 1.3), (0.6, 0.4, 0.35), m=lion)
    prim("sphere", "LionMane", (-0.3, 0.2, 1.45), (0.4, 0.4, 0.4), m=mat_plush("Mane", "#6a3a14", "#2a1408", "#8a5a2a"))


def stall_tent():
    red = mat_painted_wood("StallRed", "#7a1414")
    cream = mat_painted_wood("StallCream", "#c9b994")
    wood = mat_wood("StallWood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            seg("Post%d%d" % (sx, sy), (1.4 * sx, 1.0 * sy, 0), (1.4 * sx, 1.0 * sy, 2.4), 0.05, wood, verts=8)
    fan_slices("Canopy", 2.2, 2.3, 3.4, 8, [red, cream])
    box("Counter", (0, -0.9, 0.55), (2.8, 0.4, 1.1), red)
    box("Shelf", (0, 0.9, 1.2), (2.6, 0.3, 0.05), wood)
    random.seed(2)
    prize = [mat_plush("PrizeA", "#7a4a52", "#2a1418", "#a07078"), mat_plush("PrizeB", "#4a5a7a", "#1a2030", "#7a8aa0")]
    for i in range(6):
        x = -1.1 + 0.44 * i
        m = prize[i % 2]
        prim("sphere", "PBody%d" % i, (x, 0.9, 1.4), (0.14, 0.12, 0.16), m=m)
        if i != 3:
            prim("sphere", "PHead%d" % i, (x, 0.88, 1.65), (0.12, 0.11, 0.11), m=m)


def coaster_hill():
    """Huge skeletal coaster lift hill, used as skyline scenery outside the fences."""
    wood = mat_wood("HillWood", "#2e241a")
    rust = mat_rust()
    pts = []
    for i in range(25):
        t = i / 24
        y = -15 + 30 * t
        z = 2 + 18 * math.sin(math.pi * min(1, t * 1.3)) ** 1.2 if t < 0.77 else 2 + 18 * math.sin(math.pi * 0.999) + (1 - t) * 40
        z = max(2, z)
        pts.append(Vector((0, y, z)))
    for i in range(24):
        for s in (-1, 1):
            seg("Rail%d_%d" % (i, s), pts[i] + Vector((0.6 * s, 0, 0)), pts[i + 1] + Vector((0.6 * s, 0, 0)), 0.08, rust, verts=6)
    for i in range(0, 25, 2):
        p = pts[i]
        for s in (-1, 1):
            seg("Leg%d_%d" % (i, s), (1.2 * s, p.y, 0), (0.6 * s, p.y, p.z), 0.12, wood, verts=6)
        for h in range(1, int(p.z // 3) + 1):
            seg("X%d_%d" % (i, h), (-1.0, p.y, (h - 1) * 3), (1.0, p.y, h * 3), 0.05, wood, verts=4)


EXTRA = [
    ("circus_tent", circus_tent, 9000, 1024), ("bumper_arena", bumper_arena, 6000, 1024),
    ("bumper_car", bumper_car, 1800, 256), ("teacups", teacups, 6000, 1024), ("cotton_candy", cotton_candy, 2500, 512),
    ("striker", striker, 1500, 512), ("billboard", billboard, 2500, 512), ("signpost", signpost, 1200, 256),
    ("mapboard", mapboard, 600, 256), ("photo", photo, 60, 64), ("trashbags", trashbags, 2500, 256),
    ("turnstile", turnstile, 600, 128), ("circus_wagon", circus_wagon, 3000, 512), ("stall_tent", stall_tent, 3000, 512),
    ("coaster_hill", coaster_hill, 2500, 512),
]
