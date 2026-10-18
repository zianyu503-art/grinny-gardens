"""Park props for Grinny Gardens. Each builder makes one prop at the origin, facing -Y.
Empties named Part_<Name> mark moving parts (pivot = empty location)."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, Mat, prim, seg, empty, apply_mods, displace, boolean, orient, link_obj, smooth,
                 mat_painted_wood, mat_rust, mat_brass, mat_simple, mat_plush, mat_stripes, mat_bone, R)


def text(name, body, loc, size, m, parent=None, extrude=0.03):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    o = link_obj(bpy.data.objects.new(name, cu))
    o.data.materials.append(m)
    o.parent = parent
    o.location = loc
    o.rotation_euler = (R(90), 0, 0)
    return o


def box(name, loc, size, m, parent=None, rot=(0, 0, 0)):
    return prim("cube", name, loc, size, m=m, parent=parent, rot=rot, shade_smooth=False)


def mat_wood(name="Wood", base="#5a4430"):
    M = Mat(name)
    grain = M.wave(18, "Y", distortion=4.0)
    col = M.ramp(M.math(grain, M.noise(4, 8, 0.6), "MULTIPLY"),
                 [(0.0, "#1e140c"), (0.3, base), (0.7, "#7a6248")])
    dirt = M.ramp(M.noise(2, 5, 0.5), [(0.4, "#ffffff"), (0.75, "#4a3a2a")])
    M.set(color=M.mix(1.0, col, dirt, "MULTIPLY"), rough=0.85)
    M.bump(grain, 0.3, 0.01)
    return M.m


def mat_metal(name, paint):
    """Painted metal, rust bleeding through."""
    M = Mat(name)
    n = M.noise(5, 12, 0.7, distortion=0.6)
    col = M.ramp(n, [(0.3, "#2a1408"), (0.42, "#6a3418"), (0.5, paint), (0.9, paint)])
    dirt = M.ramp(M.noise(2, 5, 0.5), [(0.4, "#ffffff"), (0.8, "#4a4038")])
    M.set(color=M.mix(1.0, col, dirt, "MULTIPLY"), rough=0.7, metal=0.2)
    M.bump(n, 0.4, 0.01)
    return M.m


def glow(name, color, strength=4.0):
    return mat_simple(name, color, 0.3, emit=color, emit_strength=strength)


# --------------------------------------------------------------------------- props
def booth():
    red = mat_painted_wood("BoothRed", "#8a1c1c")
    cream = mat_painted_wood("BoothCream", "#cdbf9a")
    glass = mat_simple("DirtyGlass", "#0b0f10", 0.15, metal=0.3)
    gold = mat_brass()
    box("Base", (0, 0, 0.55), (2.4, 2.0, 1.1), red)
    box("Back", (0, 0.95, 1.75), (2.4, 0.1, 1.3), cream)
    for s in (-1, 1):
        box("Side%d" % s, (1.15 * s, 0, 1.75), (0.1, 2.0, 1.3), cream)
        box("Pillar%d" % s, (1.12 * s, -0.95, 1.75), (0.16, 0.14, 1.3), red)
    box("Glass", (0, -0.95, 1.75), (2.1, 0.03, 1.1), glass)
    box("Slot", (0, -0.97, 1.22), (0.5, 0.05, 0.12), mat_simple("Black", "#050505", 0.9))
    box("Counter", (0, -1.17, 1.12), (2.5, 0.45, 0.07), cream)
    roof = prim("cone", "Roof", (0, 0, 2.95), (1.95, 1.95, 1.1), m=red, rot=(0, 0, R(45)), vertices=4,
                shade_smooth=False)
    prim("sphere", "Finial", (0, 0, 3.55), (0.12, 0.12, 0.12), m=gold)
    box("SignBoard", (0, -1.04, 2.6), (1.9, 0.08, 0.42), cream)
    text("SignText", "TICKETS", (0, -1.09, 2.6), 0.3, red)


def arch():
    red = mat_painted_wood("ArchRed", "#7a1616")
    cream = mat_painted_wood("ArchCream", "#c9b994")
    purple = mat_painted_wood("ArchPurple", "#3a1a4a")
    gold = mat_brass()
    rust = mat_rust()
    on = glow("BulbOn", "#ffcf80", 6)
    dead = mat_simple("BulbDead", "#2a2620", 0.2)
    plush = mat_painted_wood("BustPaint", "#9a5a66")
    for s in (-1, 1):
        for i in range(10):
            prim("cyl", "Pil%d_%d" % (s, i), (4 * s, 0, 0.3 + 0.6 * i), (0.45, 0.45, 0.6),
                 m=red if i % 2 else cream, vertices=20)
        prim("sphere", "Cap%d" % s, (4 * s, 0, 6.3), (0.55, 0.55, 0.55), m=gold)
    box("Board", (0, 0, 6.7), (9.2, 0.35, 1.5), purple)
    for z in (5.95, 7.45):
        box("FrameH%.1f" % z, (0, -0.18, z), (9.3, 0.08, 0.1), gold)
    text("Title", "GRINNY GARDENS", (0, -0.2, 6.7), 0.78, cream)
    random.seed(3)
    for i in range(26):
        x = -4.4 + 8.8 * i / 25
        for z in (5.95, 7.45):
            prim("sphere", "Bulb%d_%.0f" % (i, z), (x, -0.25, z), (0.07, 0.07, 0.07),
                 m=on if random.random() < 0.3 else dead)
    # Grinny bust on top
    prim("sphere", "BustHead", (0, 0, 8.2), (0.85, 0.75, 0.75), m=plush)
    for s in (-1, 1):
        prim("sphere", "BustEar%d" % s, (0.65 * s, 0.05, 8.85), (0.3, 0.12, 0.3), m=plush)
        prim("sphere", "BustEye%d" % s, (0.3 * s, -0.65, 8.4), (0.13, 0.06, 0.13), m=mat_simple("Black", "#050505", 0.3))
    prim("sphere", "BustMuzzle", (0, -0.65, 8.0), (0.38, 0.25, 0.25), m=cream)
    for k in range(13):
        a = R(-70 + 140 * k / 12)
        p = Vector((0.55 * math.sin(a), -0.72 * math.cos(a) - 0.05, 7.85 + 0.12 * (1 - math.cos(a))))
        box("BustMouth%d" % k, p, (0.1, 0.05, 0.06), mat_simple("Black", "#050505", 0.3))
    for s, nm in ((-1, "Part_DoorL"), (1, "Part_DoorR")):
        d = empty(nm, (3.55 * s, 0, 0))
        for i in range(15):
            x = -s * (0.12 + 0.24 * i)
            seg("Bar%d" % i, (x, 0, 0.05), (x, 0, 3.3), 0.025, rust, d, verts=8)
            prim("cone", "Spike%d" % i, (x, 0, 3.42), (0.05, 0.05, 0.22), m=rust, parent=d, vertices=8)
        for z in (0.3, 1.6, 3.2):
            box("Rail%.1f" % z, (-s * 1.75, 0, z), (3.5, 0.06, 0.08), rust, d)
        t = prim("torus", "Ring", (-s * 1.75, 0, 2.4), (1, 1, 1), m=gold, parent=d, rot=(R(90), 0, 0),
                 major_radius=0.45, minor_radius=0.04, major_segments=32, minor_segments=8)


def carousel():
    floor_m = mat_painted_wood("CarFloor", "#4a3a2a")
    red = mat_painted_wood("CarRed", "#7a1414")
    cream = mat_painted_wood("CarCream", "#c9b994")
    gold = mat_brass()
    mirror = mat_simple("Mirror", "#202428", 0.05, metal=1.0)
    on = glow("BulbOn", "#ffcf80", 5)
    dead = mat_simple("BulbDead", "#2a2620", 0.2)
    prim("cyl", "Base", (0, 0, 0.15), (6.4, 6.4, 0.3), m=mat_metal("CarBase", "#2a2a30"), vertices=48)
    spin = empty("Part_Spin", (0, 0, 0))
    prim("cyl", "Floor", (0, 0, 0.35), (6.1, 6.1, 0.1), m=floor_m, parent=spin, vertices=48)
    prim("cyl", "Column", (0, 0, 2.4), (0.9, 0.9, 4.2), m=cream, parent=spin, vertices=24)
    for i in range(12):
        a = 2 * math.pi * i / 12
        box("MirrorP%d" % i, (0.92 * math.cos(a), 0.92 * math.sin(a), 2.4), (0.05, 0.4, 2.6), mirror,
            spin, rot=(0, 0, a))
    prim("cone", "Canopy", (0, 0, 5.35), (6.8, 6.8, 1.6), m=red, parent=spin, vertices=24)
    prim("cyl", "Ceiling", (0, 0, 4.55), (6.6, 6.6, 0.05), m=cream, parent=spin, vertices=24)
    for i in range(24):
        a = 2 * math.pi * i / 24
        p = (6.7 * math.cos(a), 6.7 * math.sin(a), 4.35)
        v = box("Valance%d" % i, p, (1.7, 0.06, 0.55), red if i % 2 else cream, spin, rot=(0, 0, a + math.pi / 2))
        prim("sphere", "VBulb%d" % i, (6.75 * math.cos(a), 6.75 * math.sin(a), 4.05), (0.07,) * 3,
             m=on if i % 5 == 0 else dead, parent=spin)
    prim("cone", "Cupola", (0, 0, 6.6), (1.2, 1.2, 1.0), m=cream, parent=spin)
    prim("sphere", "TopBall", (0, 0, 7.2), (0.2, 0.2, 0.2), m=gold, parent=spin)
    for ring, n in ((4.6, 16), (3.0, 8)):
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (ring < 4)) / n
            x, y = ring * math.cos(a), ring * math.sin(a)
            seg("Pole%.0f_%d" % (ring, i), (x, y, 0.4), (x, y, 4.5), 0.045, gold, spin, verts=10)


def lamp():
    green = mat_metal("LampGreen", "#1e3a2a")
    prim("cyl", "Foot", (0, 0, 0.15), (0.22, 0.22, 0.3), m=green, vertices=12)
    seg("Post", (0, 0, 0.3), (0, 0, 3.6), 0.07, green, verts=12)
    seg("Arm", (0, 0, 3.4), (0, -0.4, 3.55), 0.03, green, verts=8)
    box("LampGlass", (0, -0.4, 3.75), (0.26, 0.26, 0.34), glow("LampGlass", "#ffd08a", 5))
    for sx in (-1, 1):
        for sy in (-1, 1):
            seg("Frame%d%d" % (sx, sy), (0.14 * sx, -0.4 + 0.14 * sy, 3.57), (0.14 * sx, -0.4 + 0.14 * sy, 3.93),
                0.012, green, verts=6)
    prim("cone", "Cap", (0, -0.4, 4.02), (0.24, 0.24, 0.18), m=green, vertices=4, rot=(0, 0, R(45)))


def bench():
    wood = mat_painted_wood("BenchGreen", "#2a4a32")
    iron = mat_rust()
    for s in (-1, 1):
        box("LegF%d" % s, (0.8 * s, -0.2, 0.22), (0.06, 0.06, 0.44), iron)
        box("LegB%d" % s, (0.8 * s, 0.2, 0.45), (0.06, 0.06, 0.9), iron)
        box("Arm%d" % s, (0.8 * s, 0, 0.62), (0.06, 0.5, 0.05), iron)
    for i in range(4):
        box("Seat%d" % i, (0, -0.22 + 0.13 * i, 0.46), (1.8, 0.1, 0.04), wood)
    for i in range(3):
        box("Back%d" % i, (0, 0.24, 0.6 + 0.12 * i), (1.8, 0.03, 0.09), wood)


def fence():
    rust = mat_rust()
    for s in (-1, 1):
        box("Post%d" % s, (1.5 * s, 0, 1.0), (0.1, 0.1, 2.0), rust)
        prim("sphere", "Knob%d" % s, (1.5 * s, 0, 2.06), (0.08,) * 3, m=rust)
    for z in (0.2, 1.7):
        box("Rail%.1f" % z, (0, 0, z), (3.0, 0.04, 0.06), rust)
    for i in range(13):
        x = -1.32 + 0.22 * i
        seg("Bar%d" % i, (x, 0, 0.05), (x, 0, 1.85), 0.016, rust, verts=4)
        prim("cone", "Tip%d" % i, (x, 0, 1.92), (0.035, 0.035, 0.12), m=rust, vertices=4)


def trash():
    green = mat_metal("BinGreen", "#24402c")
    prim("cyl", "Bin", (0, 0, 0.45), (0.3, 0.3, 0.9), m=green, vertices=20)
    for z in (0.15, 0.75):
        prim("torus", "Hoop%.2f" % z, (0, 0, z), (1, 1, 1), m=green, major_radius=0.31, minor_radius=0.02,
             major_segments=24, minor_segments=6)
    prim("sphere", "Lid", (0.12, 0.05, 0.92), (0.32, 0.32, 0.1), m=green, rot=(R(18), R(10), 0))
    paper = mat_simple("Paper", "#b8b0a0", 0.9)
    for i in range(3):
        p = prim("ico", "Paper%d" % i, (0.35 + 0.1 * i, -0.3 + 0.2 * i, 0.06), (0.07, 0.07, 0.05), m=paper,
                 subdivisions=1, shade_smooth=False)


def crate():
    wood = mat_wood("CrateWood")
    box("Core", (0, 0, 0.5), (0.96, 0.96, 0.96), wood)
    for s in (-1, 1):
        for a in ("x", "y"):
            loc = (0.49 * s, 0, 0.5) if a == "x" else (0, 0.49 * s, 0.5)
            sz = (0.04, 1.0, 0.12) if a == "x" else (1.0, 0.04, 0.12)
            for z in (0.08, 0.92):
                box("Edge%s%d%.2f" % (a, s, z), (loc[0], loc[1], z), sz, wood)
            box("Diag%s%d" % (a, s), loc, (sz[0], sz[1], 0.12), wood,
                rot=(R(45) if a == "x" else 0, R(45) if a == "y" else 0, 0))


def balloon_cart():
    stripe = mat_stripes("CartStripe", "#7a1a1a", "#c9b994", 6, "X")
    iron = mat_rust()
    box("Cart", (0, 0, 0.75), (1.2, 0.7, 0.7), stripe)
    for s in (-1, 1):
        t = prim("torus", "Wheel%d" % s, (0.62 * s, 0, 0.32), (1, 1, 1), m=iron, rot=(0, R(90), 0),
                 major_radius=0.3, minor_radius=0.03, major_segments=24, minor_segments=6)
    seg("Handle", (-0.6, 0, 1.0), (-1.1, 0, 1.1), 0.025, iron, verts=8)
    seg("Pole", (0.3, 0, 1.1), (0.3, 0, 2.4), 0.03, iron, verts=8)
    random.seed(8)
    cols = ["#7a1a1a", "#1a3a7a", "#7a7a1a", "#1a6a3a", "#6a1a6a"]
    for i in range(6):
        p = Vector((0.3 + random.uniform(-0.3, 0.3), random.uniform(-0.2, 0.2), 2.0 - 0.25 * i))
        seg("Str%d" % i, (0.3, 0, 2.4), p, 0.004, iron, verts=4)
        b = prim("sphere", "Deflated%d" % i, p, (0.12, 0.08, 0.16), m=mat_simple("Rubber%d" % i, cols[i % 5], 0.4))
        displace(b, 0.04, 0.05)
    seg("RedString", (0.3, 0, 2.4), (0.6, 0.2, 3.6), 0.004, iron, verts=4)
    prim("sphere", "RedBalloon", (0.6, 0.2, 3.9), (0.28, 0.28, 0.34), m=mat_simple("RedRubber", "#8a0a0a", 0.25))


def popcorn():
    red = mat_painted_wood("PopRed", "#8a1c1c")
    cream = mat_painted_wood("PopCream", "#cdbf9a")
    glass = mat_simple("DirtyGlass", "#2a2a24", 0.1, metal=0.2)
    box("Cabinet", (0, 0, 0.55), (2.0, 1.2, 1.1), red)
    box("Counter", (0, -0.1, 1.12), (2.1, 1.3, 0.06), cream)
    box("Machine", (0.4, 0, 1.55), (0.7, 0.6, 0.8), glass)
    corn = mat_simple("Popcorn", "#d8c89a", 0.9)
    random.seed(2)
    for i in range(40):
        prim("ico", "Corn%d" % i, (0.4 + random.uniform(-0.3, 0.3), random.uniform(-0.25, 0.25), 1.2 + random.uniform(0, 0.15)),
             (0.04,) * 3, m=corn, subdivisions=1, shade_smooth=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            seg("Post%d%d" % (sx, sy), (0.95 * sx, 0.55 * sy, 1.1), (0.95 * sx, 0.55 * sy, 2.5), 0.04, cream, verts=8)
    for i in range(8):
        x = -1.05 + 0.3 * i
        box("Awning%d" % i, (x + 0.15, -0.1, 2.55), (0.3, 1.6, 0.05), red if i % 2 else cream, rot=(R(12), 0, 0))
    box("Sign", (0, -0.62, 2.85), (1.6, 0.06, 0.4), cream)
    text("SignText", "POPCORN", (0, -0.66, 2.85), 0.28, red)


def fuse():
    metal = mat_brass()
    seg("Glass", (-0.11, 0, 0.06), (0.11, 0, 0.06), 0.045, glow("FuseGlow", "#ffd040", 2), verts=16)
    for s in (-1, 1):
        seg("Cap%d" % s, (0.1 * s, 0, 0.06), (0.14 * s, 0, 0.06), 0.052, metal, verts=16)
    seg("Wire", (-0.1, 0, 0.06), (0.1, 0, 0.06), 0.006, mat_simple("Filament", "#aa8844", 0.3), verts=4)


def fusebox():
    grey = mat_metal("BoxGrey", "#4a4e4a")
    box("Box", (0, 0, 1.4), (0.9, 0.25, 1.2), grey)
    box("Post", (0, 0.2, 0.9), (0.15, 0.15, 1.8), grey)
    black = mat_simple("Socket", "#050505", 0.6)
    for i, x in enumerate((-0.25, 0.0, 0.25)):
        box("Slot%d" % i, (x, -0.13, 1.4), (0.08, 0.03, 0.3), black)
    prim("sphere", "Lamp", (0.3, -0.13, 1.88), (0.05,) * 3, m=glow("WarnRed", "#ff2010", 4))
    stripes = mat_stripes("Hazard", "#c9a020", "#151515", 18, "X")
    box("Hazard", (0, -0.13, 0.86), (0.9, 0.02, 0.12), stripes)
    text("Label", "POWER", (0, -0.14, 1.85), 0.12, mat_simple("White", "#c8c8c0", 0.5))


def battery():
    seg("Body", (0, 0, 0), (0, 0, 0.16), 0.05, mat_simple("BatGreen", "#1a5a2a", 0.35), verts=16)
    seg("Band", (0, 0, 0.05), (0, 0, 0.1), 0.051, mat_simple("BatBlack", "#101010", 0.4), verts=16)
    seg("Nub", (0, 0, 0.16), (0, 0, 0.18), 0.015, mat_brass(), verts=8)


def cassette():
    box("Shell", (0, 0, 0.065), (0.2, 0.03, 0.13), mat_simple("CasBlack", "#121212", 0.4))
    box("Label", (0, -0.016, 0.075), (0.17, 0.002, 0.07), mat_simple("Label", "#c8bfa8", 0.8))
    for s in (-1, 1):
        prim("cyl", "Reel%d" % s, (0.045 * s, -0.012, 0.065), (0.022, 0.022, 0.01), m=mat_simple("Reel", "#e0e0e0", 0.3),
             rot=(R(90), 0, 0))


def keycard():
    box("Card", (0, 0, 0.05), (0.16, 0.008, 0.1), mat_simple("CardWhite", "#d0ccc0", 0.4))
    box("Stripe", (0, -0.005, 0.07), (0.16, 0.002, 0.02), mat_simple("CardRed", "#8a1010", 0.4))
    box("Photo", (-0.045, -0.005, 0.035), (0.04, 0.002, 0.045), mat_simple("Photo", "#3a3028", 0.6))


def generator():
    yellow = mat_metal("GenYellow", "#8a6a18")
    box("Base", (0, 0, 0.4), (1.4, 1.0, 0.8), yellow)
    seg("Coil", (0, 0, 0.8), (0, 0, 1.8), 0.25, mat_brass("Copper"), verts=24)
    for i in range(8):
        prim("torus", "Wind%d" % i, (0, 0, 0.9 + 0.11 * i), (1, 1, 1), m=mat_brass("Copper"), major_radius=0.27,
             minor_radius=0.03, major_segments=24, minor_segments=6)
    prim("sphere", "Grab", (0, 0, 2.05), (0.26,) * 3, m=glow("PowerGlow", "#3ab0ff", 4))
    stripes = mat_stripes("Hazard", "#c9a020", "#151515", 18, "X")
    box("Hazard", (0, -0.51, 0.7), (1.4, 0.02, 0.15), stripes)
    text("Danger", "DANGER", (0, -0.52, 0.42), 0.18, mat_simple("White", "#c8c8c0", 0.5))
    rubber = mat_simple("Cable", "#0a0a0a", 0.6)
    for s in (-1, 1):
        seg("Cable%d" % s, (0.6 * s, -0.3, 0.3), (1.1 * s, -0.9, 0.03), 0.03, rubber, verts=8)


def receiver():
    grey = mat_metal("RecGrey", "#3a3e44")
    box("Body", (0, 0, 0.6), (0.5, 0.4, 1.2), grey)
    t = prim("torus", "Dish", (0, -0.21, 1.25), (1, 1, 1), m=mat_brass(), rot=(R(90), 0, 0), major_radius=0.17,
             minor_radius=0.03, major_segments=24, minor_segments=8)
    sock = empty("Part_Socket", (0, -0.22, 1.25))
    prim("sphere", "Socket", (0, 0, 0), (0.14, 0.08, 0.14), m=glow("SocketLight", "#ff3018", 3), parent=sock)
    stripes = mat_stripes("Hazard", "#c9a020", "#151515", 18, "X")
    box("Hazard", (0, -0.205, 0.3), (0.5, 0.02, 0.1), stripes)


def lever():
    grey = mat_metal("LevGrey", "#3a3e44")
    box("Base", (0, 0, 0.35), (0.4, 0.3, 0.7), grey)
    h = empty("Part_Handle", (0, -0.16, 0.55))
    seg("Stick", (0, 0, 0), (0, 0, 0.6), 0.03, mat_rust(), h, verts=8)
    prim("sphere", "Knob", (0, 0, 0.62), (0.07,) * 3, m=mat_simple("KnobRed", "#8a0a0a", 0.3), parent=h)


def gate_handle():
    seg("Post", (0, 0, 0), (0, 0, 1.3), 0.06, mat_metal("HPost", "#2a2a2a"), verts=10)
    prim("torus", "Ring", (0, -0.1, 1.35), (1, 1, 1), m=mat_metal("HYellow", "#a08018"), rot=(R(90), 0, 0),
         major_radius=0.2, minor_radius=0.04, major_segments=24, minor_segments=8)


def coaster_gate():
    rust = mat_rust()
    for s in (-1, 1):
        box("Post%d" % s, (2.3 * s, 0, 1.8), (0.22, 0.22, 3.6), rust)
    box("Top", (0, 0, 3.55), (4.8, 0.25, 0.25), rust)
    g = empty("Part_Grate", (0, 0, 0))
    for i in range(22):
        x = -2.1 + 0.2 * i
        seg("Bar%d" % i, (x, 0, 0.05), (x, 0, 3.1), 0.025, rust, g, verts=6)
    for z in (0.3, 1.5, 2.9):
        box("H%.1f" % z, (0, 0, z), (4.3, 0.05, 0.08), rust, g)
    stripes = mat_stripes("Hazard", "#c9a020", "#151515", 10, "X")
    box("Hazard", (0, -0.14, 3.55), (4.8, 0.02, 0.2), stripes)


def coaster_track():
    rust = mat_rust()
    wood = mat_wood("TrackWood", "#3a2e22")
    for s in (-1, 1):
        seg("Rail%d" % s, (0.55 * s, -2, 0), (0.55 * s, 2, 0), 0.05, rust, verts=8)
    for i in range(8):
        box("Tie%d" % i, (0, -1.75 + 0.5 * i, -0.08), (1.4, 0.12, 0.1), wood)
    box("Spine", (0, 0, -0.25), (0.3, 4.0, 0.3), wood)


def coaster_support():
    wood = mat_wood("TrackWood", "#3a2e22")
    for s in (-1, 1):
        box("Leg%d" % s, (0.6 * s, 0, 2.5), (0.2, 0.2, 5.0), wood)
    for z in (1.0, 2.5, 4.0):
        box("Cross%.1f" % z, (0, 0, z), (1.4, 0.12, 0.12), wood)
        seg("Brace%.1f" % z, (-0.6, 0, z - 0.7), (0.6, 0, z + 0.7), 0.05, wood, verts=6)


def coaster_car():
    red = mat_painted_wood("CarRed", "#7a1414")
    plush = mat_painted_wood("BustPaint", "#9a5a66")
    iron = mat_rust()
    body = box("Body", (0, 0, 0.7), (1.5, 2.0, 0.7), red)
    for s in (-1, 1):
        for y in (-0.7, 0.7):
            seg("Wheel%d%.1f" % (s, y), (0.7 * s, y, 0.3), (0.8 * s, y, 0.3), 0.18, iron, verts=16)
    for y in (-0.4, 0.5):
        box("Seat%.1f" % y, (0, y, 1.0), (1.3, 0.5, 0.15), mat_simple("Leather", "#2a0a0a", 0.6))
        seg("LapBar%.1f" % y, (-0.6, y - 0.3, 1.3), (0.6, y - 0.3, 1.3), 0.03, iron, verts=8)
    prim("sphere", "FaceHead", (0, -1.1, 1.0), (0.5, 0.35, 0.45), m=plush)
    for s in (-1, 1):
        prim("sphere", "FaceEar%d" % s, (0.42 * s, -1.0, 1.4), (0.16, 0.08, 0.16), m=plush)
        prim("sphere", "FaceEye%d" % s, (0.18 * s, -1.42, 1.1), (0.07, 0.04, 0.07), m=mat_simple("Black", "#050505", 0.3))


def ferris():
    rust = mat_metal("FerrisWhite", "#8a8a80")
    for y in (-1.2, 1.2):
        for s in (-1, 1):
            seg("Leg%.1f%d" % (y, s), (4.5 * s, y, 0), (0, y * 0.85, 10), 0.18, rust, verts=10)
        for z in (2.5, 5.0, 7.5):
            w = 4.5 * (1 - z / 10)
            seg("Brace%.1f%.1f" % (y, z), (-w, y, z), (w, y, z), 0.08, rust, verts=8)
    seg("Axle", (0, -1.3, 10), (0, 1.3, 10), 0.3, mat_rust(), verts=16)
    wheel = empty("Part_Wheel", (0, 0, 10))
    on = glow("WheelBulb", "#ffcf80", 5)
    for y in (-0.6, 0.6):
        prim("torus", "Rim%.1f" % y, (0, y, 0), (1, 1, 1), m=rust, parent=wheel, rot=(R(90), 0, 0),
             major_radius=8, minor_radius=0.1, major_segments=96, minor_segments=8)
        prim("torus", "Inner%.1f" % y, (0, y, 0), (1, 1, 1), m=rust, parent=wheel, rot=(R(90), 0, 0),
             major_radius=7.4, minor_radius=0.06, major_segments=96, minor_segments=6)
        for i in range(16):
            a = 2 * math.pi * i / 16
            seg("Spoke%.1f_%d" % (y, i), (0, y, 0), (8 * math.sin(a), y, 8 * math.cos(a)), 0.05, rust, wheel, verts=6)
    for i in range(32):
        a = 2 * math.pi * i / 32
        prim("sphere", "WBulb%d" % i, (8.15 * math.sin(a), -0.65, 8.15 * math.cos(a)), (0.09,) * 3, m=on, parent=wheel)
    cols = ["#7a1414", "#1a3a6a", "#7a6a1a", "#2a5a3a"]
    for i in range(8):
        a = 2 * math.pi * i / 8
        c = empty("Part_Cabin%d" % i, (8 * math.sin(a), 0, 10 + 8 * math.cos(a)))
        pm = mat_painted_wood("Cabin%d" % (i % 4), cols[i % 4])
        seg("Hanger", (0, 0, 0), (0, 0, -0.5), 0.04, rust, c, verts=6)
        box("Cab", (0, 0, -1.15), (1.4, 1.2, 1.1), pm, c)
        box("Win", (0, -0.61, -1.0), (1.1, 0.02, 0.45), mat_simple("Black", "#050505", 0.3), c)
        prim("sphere", "Roof", (0, 0, -0.55), (0.75, 0.65, 0.25), m=pm, parent=c)


def funhouse():
    wall = mat_painted_wood("FHWall", "#3a2050")
    white = mat_painted_wood("FHWhite", "#d0c8b0")
    red = mat_painted_wood("FHRed", "#8a1010")
    blue = mat_painted_wood("FHBlue", "#2a4a8a")
    black = mat_simple("Black", "#050505", 0.3)
    box("WallL", (-6.75, 0, 4.5), (10.5, 0.6, 9.0), wall)
    box("WallR", (6.75, 0, 4.5), (10.5, 0.6, 9.0), wall)
    box("WallTop", (0, 0, 6.25), (3.0, 0.6, 5.5), wall)
    for s in (-1, 1):
        prim("sphere", "Eye%d" % s, (4.2 * s, -0.4, 6.0), (1.4, 0.6, 1.5), m=white)
        prim("sphere", "Pupil%d" % s, (4.0 * s + 0.3, -0.95, 5.7 - 0.2 * s), (0.55, 0.25, 0.55), m=black)
        box("Brow%d" % s, (4.2 * s, -0.5, 7.8), (2.6, 0.3, 0.35), black, rot=(0, R(-15 * s), 0))
        for k in range(4):
            prim("sphere", "Hair%d_%d" % (s, k), (10.0 * s - 1.2 * k * s, -0.3, 8.4 - 0.6 * k), (1.1, 0.7, 1.0), m=blue)
    prim("sphere", "Nose", (0, -0.7, 4.3), (0.9, 0.7, 0.8), m=red)
    for k in range(20):
        a = math.pi * k / 19
        prim("sphere", "Lip%d" % k, (2.0 * math.cos(a), -0.45, 0.2 + 3.4 * math.sin(a) * 0.95), (0.42, 0.35, 0.42), m=red)
    for k in range(6):
        prim("cone", "Tooth%d" % k, (-1.2 + 0.48 * k, -0.45, 3.0), (0.2, 0.15, 0.45), m=white, rot=(R(180), 0, 0))
    box("Sign", (0, -0.4, 8.5), (5.0, 0.15, 0.8), red)
    text("SignText", "FUN HOUSE", (0, -0.5, 8.5), 0.6, white)
    jaw = empty("Part_Jaw", (0, 0, 0))
    box("JawDoor", (0, 0, 1.6), (3.0, 0.25, 3.2), red, jaw)
    for k in range(5):
        prim("cone", "JawTooth%d" % k, (-1.1 + 0.55 * k, -0.15, 3.0), (0.2, 0.12, 0.4), m=white, parent=jaw)


def staff_door():
    grey = mat_metal("DoorGrey", "#3a4440")
    for s in (-1, 1):
        box("Jamb%d" % s, (0.68 * s, 0, 1.15), (0.12, 0.3, 2.3), grey)
    box("Head", (0, 0, 2.35), (1.5, 0.3, 0.12), grey)
    d = empty("Part_Door", (-0.62, 0, 0))
    box("Slab", (0.62, 0, 1.12), (1.22, 0.07, 2.22), grey, d)
    box("Window", (0.62, -0.04, 1.6), (0.35, 0.01, 0.25), mat_simple("DirtyGlass", "#0b0f10", 0.15), d)
    seg("Handle", (1.1, -0.05, 1.05), (1.1, -0.12, 1.05), 0.02, mat_rust(), d, verts=6)
    box("SignPlate", (0.62, -0.045, 1.25), (0.5, 0.01, 0.14), mat_simple("SignRed", "#7a1010", 0.5), d)
    text("Sign", "STAFF ONLY", (0.62, -0.06, 1.25), 0.07, mat_simple("White", "#c8c8c0", 0.5), d)


def jackbox():
    stripe = mat_stripes("JBStripe", "#7a1414", "#c9b994", 10, "X")
    box("Box", (0, 0, 0.3), (0.6, 0.6, 0.6), stripe)
    seg("Crank", (0.3, 0, 0.35), (0.42, 0, 0.35), 0.02, mat_brass(), verts=8)
    seg("CrankArm", (0.42, 0, 0.35), (0.42, 0, 0.48), 0.015, mat_brass(), verts=8)
    lid = empty("Part_Lid", (0, 0.3, 0.6))
    box("LidPlate", (0, -0.3, 0.02), (0.62, 0.62, 0.04), stripe, lid)
    pop = empty("Part_Popper", (0, 0, 0.3))
    for i in range(7):
        prim("torus", "Spring%d" % i, (0, 0, 0.08 * i), (1, 1, 1), m=mat_rust(), parent=pop, major_radius=0.1,
             minor_radius=0.015, major_segments=16, minor_segments=6)
    face = mat_painted_wood("ClownFace", "#d0c8b0")
    prim("sphere", "Head", (0, 0, 0.75), (0.22, 0.2, 0.24), m=face, parent=pop)
    prim("sphere", "Nose", (0, -0.21, 0.75), (0.05,) * 3, m=mat_simple("Red", "#8a0a0a", 0.3), parent=pop)
    for s in (-1, 1):
        prim("sphere", "Eye%d" % s, (0.08 * s, -0.18, 0.83), (0.04, 0.02, 0.05), m=mat_simple("Black", "#050505", 0.3), parent=pop)
        prim("sphere", "Tuft%d" % s, (0.2 * s, 0, 0.85), (0.1, 0.1, 0.1), m=mat_painted_wood("Tuft", "#8a2020"), parent=pop)
    for k in range(9):
        a = R(-60 + 120 * k / 8)
        box("Grin%d" % k, (0.14 * math.sin(a), -0.19 * math.cos(a), 0.66 + 0.04 * (1 - math.cos(a))),
            (0.03, 0.02, 0.02), mat_simple("Black", "#050505", 0.3), pop)


def deadtree():
    M = Mat("Bark")
    n = M.noise(6, 10, 0.7, distortion=2.0)
    M.set(color=M.ramp(n, [(0.3, "#0e0b08"), (0.6, "#2a221a"), (0.8, "#3a3028")]), rough=0.95)
    M.bump(M.wave(4, "Z", distortion=6), 0.6, 0.02)
    bark = M.m
    random.seed(5)
    T = Skel()

    def branch(start_idx, p, d, length, r, depth):
        pts = []
        cur = Vector(p)
        for i in range(3):
            d = (d + Vector((random.uniform(-.3, .3), random.uniform(-.3, .3), random.uniform(-.1, .2)))).normalized()
            cur = cur + d * length / 3
            pts.append((cur.copy(), r * (1 - (i + 1) / 4)))
        end = T.chain(start_idx, pts)
        if depth > 0:
            for k in range(random.randint(2, 3)):
                nd = (d + Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 0.6)))).normalized()
                branch(end, cur, nd, length * 0.6, r * 0.45, depth - 1)

    root = T.chain(None, [((0, 0, 0), 0.35), ((0, 0, 0.5), 0.25)])
    branch(root, (0, 0, 0.5), Vector((0.1, 0, 1)), 4.0, 0.25, 3)
    tree = T.build("Tree", bark, subdiv=1)
    displace(tree, 0.03, 0.1)


def plush_pile():
    random.seed(9)
    mats = [mat_plush("PileA", "#7a4a52", "#2a1418", "#a07078"), mat_plush("PileB", "#4a5a7a", "#1a2030", "#7a8aa0"),
            mat_plush("PileC", "#9a8a4a", "#3a3218", "#c0b070"), mat_plush("PileD", "#a8a090", "#4a4438", "#d0c8b8")]
    black = mat_simple("ButtonPlastic", "#0e0806", 0.18)
    for i in range(10):
        m = random.choice(mats)
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, 0.6)
        base = Vector((r * math.cos(a), r * math.sin(a), 0.15 + random.uniform(0, 0.4) * (1 - r)))
        prim("sphere", "PBody%d" % i, base, (0.16, 0.13, 0.18), m=m, rot=(random.uniform(-1, 1),) * 3)
        if random.random() < 0.8:
            h = base + Vector((0, 0, 0.24))
            prim("sphere", "PHead%d" % i, h, (0.14, 0.13, 0.13), m=m)
            for s in (-1, 1):
                prim("sphere", "PEar%d%d" % (i, s), h + Vector((0.1 * s, 0, 0.1)), (0.05, 0.03, 0.05), m=m)
                prim("sphere", "PEye%d%d" % (i, s), h + Vector((0.05 * s, -0.12, 0.03)), (0.025, 0.012, 0.025), m=black)


def clawpack():
    cloth = mat_plush("Sleeve", "#2a2a30", "#101014", "#44444c", scale=8)
    yellow = mat_metal("PackYellow", "#9a7a18")
    metal = mat_rust()
    for s, side, col in ((-1, "L", "#2a7aff"), (1, "R", "#ff3a2a")):
        seg("Sleeve" + side, (0.22 * s, 0.5, -0.12), (0.22 * s, 0.02, 0.0), 0.075, cloth, verts=16)
        prim("sphere", "Glove" + side, (0.22 * s, -0.06, -0.01), (0.07, 0.09, 0.06), m=mat_simple("GloveBlk", "#141210", 0.6))
        box("Launcher" + side, (0.22 * s, -0.05, 0.09), (0.11, 0.36, 0.1), yellow)
        prim("torus", "Charge" + side, (0.22 * s, -0.2, 0.09), (1, 1, 1), m=glow("Charge" + side, col, 2),
             rot=(R(90), 0, 0), major_radius=0.058, minor_radius=0.014, major_segments=24, minor_segments=8)
        seg("Barrel" + side, (0.22 * s, -0.2, 0.09), (0.22 * s, -0.3, 0.09), 0.045, metal, verts=12)
        prim("cyl", "Spool" + side, (0.22 * s + 0.07 * s, 0.05, 0.09), (0.05, 0.05, 0.04), m=metal, rot=(0, R(90), 0))
        h = empty("Part_Head" + side, (0.22 * s, -0.33, 0.09))
        prim("sphere", "Hub" + side, (0, 0, 0), (0.048,) * 3, m=mat_simple("Hub" + side, col, 0.4), parent=h)
        for k in range(3):
            ang = R(90 + 120 * k)
            dv = Vector((math.cos(ang), 0, math.sin(ang)))
            seg("FingA%s%d" % (side, k), dv * 0.03, dv * 0.07 + Vector((0, -0.07, 0)), 0.012, metal, h, verts=6)
            seg("FingB%s%d" % (side, k), dv * 0.07 + Vector((0, -0.07, 0)), dv * 0.035 + Vector((0, -0.13, 0)), 0.01,
                metal, h, r2=0.003, verts=6)


def bridge():
    wood = mat_wood("BridgeWood", "#3a2e22")
    rope = mat_simple("Rope", "#5a4a30", 0.9)
    b = empty("Part_Bridge", (0, 0, 0))
    random.seed(4)
    for i in range(18):
        y = -3.9 + 0.45 * i
        box("Plank%d" % i, (random.uniform(-0.05, 0.05), y, -0.05), (3.0, 0.38, 0.08), wood, b,
            rot=(0, 0, random.uniform(-0.05, 0.05)))
    for s in (-1, 1):
        seg("Beam%d" % s, (1.3 * s, -4, -0.15), (1.3 * s, 4, -0.15), 0.08, wood, b, verts=8)
        seg("Rope%d" % s, (1.5 * s, -4, 1.0), (1.5 * s, 4, 1.0), 0.025, rope, b, verts=6)
        for y in (-4, 0, 4):
            seg("RPost%d%d" % (s, y), (1.5 * s, y, -0.1), (1.5 * s, y, 1.1), 0.06, wood, b, verts=8)


PROPS = [
    ("booth", booth, 4000, 1024), ("arch", arch, 9000, 1024), ("carousel", carousel, 10000, 1024),
    ("lamp", lamp, 500, 256), ("bench", bench, 800, 256), ("fence", fence, 360, 256), ("trash", trash, 1000, 256),
    ("crate", crate, 600, 256), ("balloon_cart", balloon_cart, 2500, 512), ("popcorn", popcorn, 3000, 512),
    ("fuse", fuse, 400, 128), ("fusebox", fusebox, 1200, 512), ("battery", battery, 300, 128),
    ("cassette", cassette, 300, 128), ("keycard", keycard, 100, 128), ("generator", generator, 3000, 512),
    ("receiver", receiver, 1500, 256), ("lever", lever, 600, 256), ("gate_handle", gate_handle, 500, 128),
    ("coaster_gate", coaster_gate, 2500, 512), ("coaster_track", coaster_track, 300, 256),
    ("coaster_support", coaster_support, 300, 256), ("coaster_car", coaster_car, 2500, 512),
    ("ferris", ferris, 16000, 1024), ("funhouse", funhouse, 8000, 1024), ("staff_door", staff_door, 800, 256),
    ("jackbox", jackbox, 2500, 512), ("deadtree", deadtree, 1400, 512), ("plush_pile", plush_pile, 4000, 512),
    ("clawpack", clawpack, 4000, 512), ("bridge", bridge, 1500, 512),
]

from props_extra import EXTRA  # noqa: E402
PROPS += EXTRA
