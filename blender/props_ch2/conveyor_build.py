"""Chapter 2 prop: abandoned factory belt conveyor section (Grinny Gardens toy factory, 1996).

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/conveyor_build.py -- [preview|all]

3.0 m long, 0.5 m rubber belt, belt top at ~0.82 m. Runs along X, front (operator
side with motor and e-stop) faces -Y. Painted steel C-channel frame with rust,
square-tube legs on bolted foot plates, drive/tail rollers, sagging return belt,
gear motor with chain guard, emergency-stop box.
"""
import math
import os
import random
import sys

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bmesh  # noqa: E402
import bpy  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
ASSET = "conveyor"
OUT = os.path.join(ROOT, "blender/bake", ASSET)
GLB = os.path.join(ROOT, "public/models", ASSET + ".glb")
PREVIEW = os.path.join(ROOT, "renders", f"ch2_{ASSET}_preview.png")
BAKED = os.path.join(ROOT, "renders", f"ch2_{ASSET}_baked.png")
BUDGET = 6000  # web budget (large prop, halved)

mode = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else "all"
random.seed(7)
bkit.reset_scene()

L = 3.0          # roller centre-to-centre
W = 0.50         # belt width
RR = 0.055       # roller radius
BT = 0.007       # belt thickness
ZC = 0.82 - RR - BT  # roller axis height
RAIL_Y = W / 2 + 0.035
RAIL_H = 0.14

parts = []


def box(name, size, loc, rot=(0, 0, 0), mat=None, bevel=0.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(o, mat, bevel)
    return o


def cyl(name, r, depth, loc, rot=(0, 0, 0), mat=None, verts=16, bevel=0.002):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    finish(o, mat, bevel)
    return o


def finish(o, mat, bevel):
    bkit.box_uv(o, size=1.0)
    if mat is not None:
        bkit.assign(o, mat)
    if bevel:
        bkit.harden(o, width=bevel, segments=1 if bevel < 0.004 else 2)
    parts.append(o)


def jitter(o, deg=0.6):
    o.rotation_euler = [a + math.radians(random.uniform(-deg, deg)) for a in o.rotation_euler]


# ------------------------------------------------------------- materials
def tex(aid):
    return bkit.polyhaven_texture(aid, "1k")


paint = tex("rusty_painted_metal")
rust = tex("rusty_metal_02")
plate = tex("metal_plate")
rubber = tex("rubberized_track")
green = tex("green_metal_rust")
blue = tex("blue_metal_plate")

M_FRAME = bkit.pbr_material("frame", green, scale=0.8, tint=(0.85, 0.9, 0.88))
M_FRAME2 = bkit.pbr_material("frame2", green, scale=0.65, tint=(0.75, 0.8, 0.8))
M_RUST = bkit.pbr_material("rust", rust, scale=1.2, metallic=0.6)
M_STEEL = bkit.pbr_material("steel", plate, scale=2.0, tint=(0.55, 0.53, 0.50), metallic=1.0, roughness_mult=1.1)
M_BELT = bkit.pbr_material("belt", rubber, scale=2.5, tint=(0.24, 0.23, 0.22), roughness_mult=1.25)
M_MOTOR = bkit.pbr_material("motor", blue, scale=1.5, tint=(0.8, 0.85, 0.9))
M_ORANGE = bkit.pbr_material("guard", paint, scale=1.4, tint=(1.0, 0.55, 0.18))
M_RED = bkit.pbr_material("estop", paint, scale=3.0, tint=(1.0, 0.18, 0.12))
M_YELLOW = bkit.pbr_material("estopbox", paint, scale=3.0, tint=(1.0, 0.82, 0.25))


# ------------------------------------------------------------- belt (stadium loop)
def build_belt():
    R = RR + BT / 2
    pts = []
    n_arc = 14
    n_run = 10
    # top run, left -> right
    for i in range(n_run + 1):
        x = -L / 2 + L * i / n_run
        pts.append((x, ZC + R))
    # right end arc (top -> bottom, clockwise)
    for i in range(1, n_arc):
        a = math.pi / 2 - math.pi * i / n_arc
        pts.append((L / 2 + R * math.cos(a), ZC + R * math.sin(a)))
    # bottom return run with sag between idlers, right -> left
    for i in range(n_run + 1):
        x = L / 2 - L * i / n_run
        t = (x + L / 2) / L
        sag = 0.035 * math.sin(math.pi * t) ** 2 + 0.008 * math.sin(3 * math.pi * t) ** 2
        pts.append((x, ZC - R - sag))
    for i in range(1, n_arc):
        a = -math.pi / 2 - math.pi * i / n_arc
        pts.append((-L / 2 + R * math.cos(a), ZC + R * math.sin(a)))

    me = bpy.data.meshes.new("belt")
    bm = bmesh.new()
    a = [bm.verts.new((x, -W / 2, z)) for x, z in pts]
    b = [bm.verts.new((x, W / 2, z)) for x, z in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("belt", me)
    bpy.context.scene.collection.objects.link(o)
    s = o.modifiers.new("Solid", "SOLIDIFY")
    s.thickness = BT
    s.offset = 0
    bkit.active(o)
    bpy.ops.object.modifier_apply(modifier="Solid")
    finish(o, M_BELT, 0.0015)
    return o


build_belt()

# ------------------------------------------------------------- rollers + shafts + bearings
for sx, nm in ((-1, "tail"), (1, "drive")):
    x = sx * L / 2
    cyl(f"roller_{nm}", RR, W + 0.02, (x, 0, ZC), (math.pi / 2, 0, 0), M_STEEL, verts=20)
    cyl(f"shaft_{nm}", 0.015, 2 * RAIL_Y + 0.12, (x, 0, ZC), (math.pi / 2, 0, 0), M_STEEL, verts=10, bevel=0.001)
    for sy in (-1, 1):
        y = sy * (RAIL_Y + 0.035)
        # pillow-block bearing: base + housing
        box(f"brg_base_{nm}{sy}", (0.11, 0.035, 0.03), (x, y, ZC - 0.035), mat=M_RUST, bevel=0.004)
        cyl(f"brg_house_{nm}{sy}", 0.032, 0.035, (x, y, ZC), (math.pi / 2, 0, 0), M_RUST, verts=14, bevel=0.003)
        for bx in (-0.04, 0.04):
            cyl(f"brg_bolt", 0.006, 0.012, (x + bx, y, ZC - 0.018), mat=M_STEEL, verts=6, bevel=0)

# return idlers under the bottom run
for i, x in enumerate((-0.75, 0.0, 0.75)):
    cyl(f"idler{i}", 0.03, W + 0.01, (x, 0, ZC - RR - 0.06), (math.pi / 2, 0, 0), M_STEEL, verts=14)

# ------------------------------------------------------------- side frame (C-channel rails)
rail_len = L + 0.08
rail_z = ZC + 0.015
for sy in (-1, 1):
    y = sy * RAIL_Y
    m = M_FRAME if sy < 0 else M_FRAME2
    web = box(f"rail_web{sy}", (rail_len, 0.006, RAIL_H), (0, y, rail_z), mat=m, bevel=0.002)
    for fz in (rail_z + RAIL_H / 2 - 0.003, rail_z - RAIL_H / 2 + 0.003):
        box(f"rail_flange{sy}", (rail_len, 0.05, 0.006), (0, y + sy * 0.022, fz), mat=m, bevel=0.002)
    # bolt heads along the web
    for i in range(9):
        bx = -rail_len / 2 + 0.17 + i * (rail_len - 0.34) / 8
        cyl("bolt", 0.008, 0.01, (bx, y - sy * 0.007, rail_z + 0.035 * (1 if i % 2 else -1)),
            (math.pi / 2, 0, 0), M_RUST, verts=6, bevel=0)
    # top belt guide (thin angle strip riding over the belt edge)
    g = box(f"guide{sy}", (L - 0.1, 0.03, 0.004), (0, sy * (W / 2 - 0.005), ZC + RR + 0.06), mat=M_STEEL, bevel=0.0015)
    jitter(g, 0.3)
    for i in range(5):
        gx = -L / 2 + 0.2 + i * (L - 0.4) / 4
        box("guide_post", (0.025, 0.006, 0.075), (gx, y - sy * 0.004, ZC + RR + 0.03), mat=M_STEEL, bevel=0.0015)

# slider bed under the top run
box("bed", (L - 0.05, W - 0.02, 0.004), (0, 0, ZC + RR - 0.006), mat=M_STEEL, bevel=0)
# cross members between rails
for x in (-1.1, -0.35, 0.35, 1.1):
    box("cross", (0.04, 2 * RAIL_Y, 0.04), (x, 0, rail_z - 0.03), mat=M_FRAME2, bevel=0.003)

# ------------------------------------------------------------- legs
leg_top = rail_z - RAIL_H / 2
for i, x in enumerate((-1.3, 0.0, 1.3)):
    for sy in (-1, 1):
        y = sy * RAIL_Y
        h = leg_top - 0.008
        lg = box(f"leg{i}{sy}", (0.05, 0.05, h), (x, y, 0.008 + h / 2), mat=M_FRAME if (i + sy) % 2 else M_FRAME2, bevel=0.004)
        jitter(lg, 0.4)
        box(f"foot{i}{sy}", (0.13, 0.13, 0.008), (x, y, 0.004), mat=M_RUST, bevel=0.002)
        for fx in (-0.045, 0.045):
            for fy in (-0.045, 0.045):
                cyl("anchor", 0.007, 0.014, (x + fx, y + fy, 0.012), mat=M_STEEL, verts=6, bevel=0)
    # lower Y brace
    box(f"ybrace{i}", (0.035, 2 * RAIL_Y - 0.05, 0.035), (x, 0, 0.22), mat=M_FRAME2, bevel=0.003)
# lower longitudinal braces, one slightly bent from an old impact
for sy in (-1, 1):
    b = box(f"xbrace{sy}", (2.6, 0.03, 0.03), (0, sy * RAIL_Y, 0.30), mat=M_FRAME, bevel=0.003)
    if sy < 0:
        b.rotation_euler = (math.radians(1.2), 0, math.radians(0.5))

# ------------------------------------------------------------- drive: gear motor + chain guard (front, drive end)
mx, my, mz = L / 2 - 0.25, -RAIL_Y - 0.17, 0.42
box("motor_plate", (0.36, 0.26, 0.012), (mx, my + 0.03, mz - 0.11), mat=M_RUST, bevel=0.003)
box("motor_bracket", (0.04, 0.2, 0.04), (mx, -RAIL_Y - 0.06, mz - 0.11), mat=M_FRAME, bevel=0.003)
cyl("motor_body", 0.085, 0.24, (mx - 0.05, my, mz), (0, math.pi / 2, 0), M_MOTOR, verts=20, bevel=0.004)
for k in range(10):  # cooling fins
    a = 2 * math.pi * k / 10
    box("fin", (0.2, 0.006, 0.018), (mx - 0.06, my + 0.09 * math.cos(a), mz + 0.09 * math.sin(a)),
        (a, 0, 0), M_MOTOR, bevel=0)
cyl("fan_cover", 0.09, 0.05, (mx - 0.19, my, mz), (0, math.pi / 2, 0), M_MOTOR, verts=20, bevel=0.005)
box("gearbox", (0.12, 0.16, 0.18), (mx + 0.12, my, mz), mat=M_MOTOR, bevel=0.008)
box("terminal_box", (0.08, 0.07, 0.05), (mx - 0.05, my, mz + 0.105), mat=M_MOTOR, bevel=0.004)
cz0, cz1 = mz + 0.13, rail_z - 0.05
cyl("conduit_v", 0.011, cz1 - cz0, (mx - 0.05, my, (cz0 + cz1) / 2), mat=M_RUST, verts=8, bevel=0)
cyl("conduit_h", 0.011, abs(my) - RAIL_Y, (mx - 0.05, (my - RAIL_Y) / 2, cz1), (math.pi / 2, 0, 0), M_RUST, verts=8, bevel=0)
# chain guard: vertical sheet box from gearbox output up to the drive shaft
gz0, gz1 = mz - 0.06, ZC + 0.06
box("chain_guard", (0.2, 0.06, gz1 - gz0), (L / 2 - 0.06, -RAIL_Y - 0.1, (gz0 + gz1) / 2), (0, math.radians(-6), 0), M_ORANGE, bevel=0.006)

# ------------------------------------------------------------- e-stop box on the front rail
ex = -L / 2 + 0.45
box("estop_box", (0.09, 0.07, 0.09), (ex, -RAIL_Y - 0.045, rail_z + 0.02), mat=M_YELLOW, bevel=0.006)
cyl("estop_collar", 0.022, 0.012, (ex, -RAIL_Y - 0.085, rail_z + 0.02), (math.pi / 2, 0, 0), M_STEEL, verts=14, bevel=0.001)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.028, segments=14, ring_count=7, location=(ex, -RAIL_Y - 0.09, rail_z + 0.02))
btn = bpy.context.active_object
btn.name = "estop_button"
btn.scale = (1, 0.45, 1)
bpy.ops.object.transform_apply(scale=True)
finish(btn, M_RED, 0)
bkit.shade_smooth(btn)

# ------------------------------------------------------------- render / bake / export
bkit.light_studio()
bkit.render_views(PREVIEW)
print("preview:", PREVIEW)
if mode == "preview":
    sys.exit(0)

obj = bkit.join(parts, ASSET)
bkit.decimate(obj, BUDGET)
bkit.origin_to_bottom(obj)
# (bake_to_textures makes its own BakeUV; re-unwrapping "UVMap" here would wreck the box-UV texture scale)
os.makedirs(OUT, exist_ok=True)
bkit.bake_to_textures(obj, OUT, size=1024)
bkit.report([obj])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, ASSET + ".blend"))
bkit.export_glb(GLB, [obj], image_format="JPEG")
bkit.render_views(BAKED)
print("done:", GLB)
