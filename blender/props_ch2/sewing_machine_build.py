"""Chapter 2 prop: abandoned industrial sewing machine on its work table (Grinny Gardens toy factory, 1996).

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/sewing_machine_build.py -- [preview|all]

Table 1.10 x 0.52 m, top at 0.76 m; lockstitch head (grey-green painted cast iron)
on the top, handwheel on +X, operator/front side faces -Y. Under the table: steel
legs, clutch motor with V-belt up to the handwheel, treadle pedal, drawer.
A thread stand with two cones at the back, a fabric scrap still under the presser
foot and hanging over the front edge.
"""
import math
import os
import random
import sys

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
ASSET = "sewing_machine"
OUT = os.path.join(ROOT, "blender/bake", ASSET)
GLB = os.path.join(ROOT, "public/models", ASSET + ".glb")
PREVIEW = os.path.join(ROOT, "renders", f"ch2_{ASSET}_preview.png")
BAKED = os.path.join(ROOT, "renders", f"ch2_{ASSET}_baked.png")
BUDGET = 4500  # web budget (medium-large prop, halved)

mode = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else "all"
random.seed(11)
bkit.reset_scene()

TW, TD, TT, TH = 1.10, 0.52, 0.76, 0.035   # table width, depth, top height, top thickness
parts = []


def finish(o, mat, bevel, segs=None):
    bkit.box_uv(o, size=1.0)
    if mat is not None:
        bkit.assign(o, mat)
    if bevel:
        bkit.harden(o, width=bevel, segments=segs or (1 if bevel < 0.004 else 2))
    parts.append(o)
    return o


def box(name, size, loc, rot=(0, 0, 0), mat=None, bevel=0.003, segs=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, mat, bevel, segs)


def cyl(name, r, depth, loc, rot=(0, 0, 0), mat=None, verts=16, bevel=0.002, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    return finish(o, mat, bevel)


AX = (0, math.pi / 2, 0)   # cylinder along X
AY = (math.pi / 2, 0, 0)   # cylinder along Y


# ------------------------------------------------------------- materials (Poly Haven, 1k)
def tex(aid):
    return bkit.polyhaven_texture(aid, "1k")


green = tex("green_metal_rust")
wood = tex("wood_table_worn")
rust = tex("rusty_metal_02")
plate = tex("metal_plate")
linen = tex("rough_linen")
rubber = tex("rubberized_track")
blue = tex("blue_metal_plate")

M_HEAD = bkit.pbr_material("head", green, scale=2.0, tint=(0.95, 1.05, 0.98))
M_WOOD = bkit.pbr_material("top", wood, scale=0.8, tint=(0.85, 0.82, 0.78))
M_LEGS = bkit.pbr_material("legs", rust, scale=1.2, tint=(0.42, 0.4, 0.38), metallic=0.5)
M_STEEL = bkit.pbr_material("steel", plate, scale=3.0, tint=(0.6, 0.58, 0.55), metallic=1.0)
M_MOTOR = bkit.pbr_material("motor", blue, scale=1.5, tint=(0.55, 0.58, 0.6))
M_BELT = bkit.pbr_material("vbelt", rubber, scale=4.0, tint=(0.2, 0.19, 0.18), roughness_mult=1.2)
M_CLOTH = bkit.pbr_material("cloth", linen, scale=5.0, tint=(0.72, 0.52, 0.48), metallic=0.0, roughness_mult=1.3)


def desaturate(mat, sat=0.0, value=1.05):
    """Insert Hue/Saturation after the colour image so the tint sets the hue (linen scan is blue)."""
    nt = mat.node_tree
    img = next(n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image and "color" in n.image.filepath)
    links = list(img.outputs["Color"].links)
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = sat
    hs.inputs["Value"].default_value = value
    nt.links.new(img.outputs["Color"], hs.inputs["Color"])
    for lk in links:
        nt.links.new(hs.outputs["Color"], lk.to_socket)



M_THREAD_R = bkit.pbr_material("thread_r", linen, scale=12.0, tint=(0.6, 0.12, 0.1), metallic=0.0)
M_THREAD_W = bkit.pbr_material("thread_w", linen, scale=12.0, tint=(0.85, 0.8, 0.7), metallic=0.0)
desaturate(M_CLOTH)
desaturate(M_THREAD_R, sat=0.0, value=1.0)
desaturate(M_THREAD_W, sat=0.0, value=1.1)

# ------------------------------------------------------------- table
box("tabletop", (TW, TD, TH), (0, 0, TT - TH / 2), mat=M_WOOD, bevel=0.004)
box("table_edge_front", (TW, 0.012, 0.05), (0, -TD / 2 + 0.03, TT - TH - 0.025), mat=M_WOOD, bevel=0.002)
# drawer under the left front
box("drawer", (0.36, 0.38, 0.08), (-0.3, -0.04, TT - TH - 0.045), mat=M_WOOD, bevel=0.003)
box("drawer_front", (0.38, 0.015, 0.09), (-0.3, -0.237, TT - TH - 0.045), mat=M_WOOD, bevel=0.003)
cyl("drawer_knob", 0.012, 0.02, (-0.3, -0.25, TT - TH - 0.045), AY, M_STEEL, verts=10, bevel=0)

# steel leg frames (two end frames + stretchers)
LZ = TT - TH
for sx in (-1, 1):
    x = sx * (TW / 2 - 0.08)
    for sy in (-1, 1):
        y = sy * (TD / 2 - 0.05)
        lg = box("leg", (0.035, 0.035, LZ - 0.01), (x, y, (LZ - 0.01) / 2 + 0.01), mat=M_LEGS, bevel=0.003)
        lg.rotation_euler = (math.radians(random.uniform(-0.4, 0.4)), math.radians(random.uniform(-0.4, 0.4)), 0)
        box("foot", (0.06, 0.06, 0.012), (x, y, 0.006), mat=M_STEEL, bevel=0.002)   # levelling pad
    box("end_rail_top", (0.03, TD - 0.06, 0.035), (x, 0, LZ - 0.02), mat=M_LEGS, bevel=0.003)
    box("end_rail_low", (0.03, TD - 0.06, 0.03), (x, 0, 0.12), mat=M_LEGS, bevel=0.003)
box("stretcher", (TW - 0.16, 0.03, 0.03), (0, TD / 2 - 0.05, 0.12), mat=M_LEGS, bevel=0.003)

# ------------------------------------------------------------- clutch motor + pedal (under right side)
mx, my, mz = 0.05 + 0.25 + 0.035 - 0.19, 0.05, LZ - 0.14
box("motor_hanger", (0.2, 0.16, 0.02), (mx, my, LZ - 0.01), mat=M_LEGS, bevel=0.003)
for dx in (-0.07, 0.07):
    box("hanger_strap", (0.02, 0.1, 0.07), (mx + dx, my, LZ - 0.055), mat=M_LEGS, bevel=0.002)
cyl("motor_body", 0.09, 0.24, (mx, my, mz), AX, M_MOTOR, verts=20, bevel=0.004)
cyl("motor_endcap", 0.075, 0.05, (mx - 0.14, my, mz), AX, M_MOTOR, verts=20, bevel=0.004)
cyl("clutch_housing", 0.08, 0.06, (mx + 0.145, my, mz), AX, M_MOTOR, verts=20, bevel=0.004)
cyl("motor_pulley", 0.035, 0.025, (mx + 0.19, my, mz), AX, M_STEEL, verts=16, bevel=0.002)
cyl("clutch_lever", 0.007, 0.6, (mx - 0.13, my - 0.08, mz - 0.33), (math.radians(8), 0, 0), M_LEGS, verts=8, bevel=0)
box("pedal", (0.12, 0.25, 0.02), (mx - 0.13, my - 0.14, 0.08), (math.radians(-12), 0, 0), mat=M_LEGS, bevel=0.003)
box("pedal_base", (0.1, 0.06, 0.04), (mx - 0.13, my - 0.02, 0.02), mat=M_LEGS, bevel=0.003)

# ------------------------------------------------------------- machine head
BZ = TT                     # bed sits on the table top
hx = 0.05                   # head centred a bit right of table centre
box("bed", (0.48, 0.18, 0.05), (hx, 0.0, BZ + 0.025), mat=M_HEAD, bevel=0.012, segs=3)
box("needle_plate", (0.07, 0.05, 0.003), (hx - 0.17, -0.02, BZ + 0.051), mat=M_STEEL, bevel=0.001)
box("slide_plate", (0.07, 0.05, 0.002), (hx - 0.1, -0.02, BZ + 0.0505), mat=M_STEEL, bevel=0.001)
box("pillar", (0.11, 0.13, 0.27), (hx + 0.17, 0.0, BZ + 0.05 + 0.135), mat=M_HEAD, bevel=0.02, segs=3)
AZ = BZ + 0.27              # arm centre height
box("arm", (0.42, 0.11, 0.1), (hx + 0.0, 0.0, AZ), mat=M_HEAD, bevel=0.03, segs=3)
box("head_end", (0.09, 0.12, 0.17), (hx - 0.2, 0.0, AZ - 0.035), mat=M_HEAD, bevel=0.018, segs=3)
box("face_plate", (0.004, 0.1, 0.13), (hx - 0.247, 0.0, AZ - 0.04), mat=M_STEEL, bevel=0.002)
# needle bar, presser bar, foot, needle
nx = hx - 0.17
cyl("needle_bar", 0.0055, 0.07, (nx, -0.02, AZ - 0.15), mat=M_STEEL, verts=8, bevel=0)
cyl("needle_clamp", 0.009, 0.015, (nx, -0.02, AZ - 0.19), mat=M_STEEL, verts=8, bevel=0)
cyl("needle", 0.0012, 0.04, (nx, -0.02, BZ + 0.075), mat=M_STEEL, verts=6, bevel=0)
cyl("presser_bar", 0.005, 0.08, (nx + 0.015, -0.005, AZ - 0.16), mat=M_STEEL, verts=8, bevel=0)
box("presser_foot", (0.03, 0.025, 0.006), (nx + 0.005, -0.02, BZ + 0.062), mat=M_STEEL, bevel=0.001)
box("presser_shank", (0.008, 0.01, 0.06), (nx + 0.015, -0.01, BZ + 0.09), mat=M_STEEL, bevel=0.001)
# thread tension, take-up lever, guides (front of head)
for dz in (0.0, 0.03):
    cyl("tension_disc", 0.012, 0.012, (hx - 0.185, -0.066, AZ - 0.02 - dz), AY, M_STEEL, verts=12, bevel=0.001)
box("takeup_lever", (0.012, 0.012, 0.05), (hx - 0.215, -0.066, AZ + 0.01), (0, math.radians(20), 0), mat=M_STEEL, bevel=0.001)
for gx in (-0.1, 0.0, 0.1):
    cyl("thread_guide", 0.004, 0.012, (hx + gx, -0.01, AZ + 0.055), mat=M_STEEL, verts=6, bevel=0)
# handwheel + belt cover
wx = hx + 0.25
cyl("handwheel", 0.065, 0.03, (wx, 0.0, AZ), AX, M_HEAD, verts=24, bevel=0.004)
cyl("handwheel_hub", 0.02, 0.06, (wx + 0.015, 0.0, AZ), AX, M_STEEL, verts=12, bevel=0.002)
cyl("pulley", 0.04, 0.02, (wx + 0.035, 0.0, AZ), AX, M_STEEL, verts=16, bevel=0.002)
# stitch-length dial and reverse lever on the pillar front
cyl("stitch_dial", 0.025, 0.015, (hx + 0.17, -0.07, BZ + 0.15), AY, M_STEEL, verts=16, bevel=0.002)
box("reverse_lever", (0.014, 0.012, 0.09), (hx + 0.12, -0.07, BZ + 0.11), (0, math.radians(-25), 0), mat=M_STEEL, bevel=0.002)
# bobbin winder on the table top right of the bed
box("winder_base", (0.07, 0.05, 0.02), (hx + 0.32, 0.12, TT + 0.01), mat=M_HEAD, bevel=0.004)
cyl("winder_spindle", 0.008, 0.05, (hx + 0.32, 0.12, TT + 0.035), AX, M_STEEL, verts=8, bevel=0)

# V-belt from handwheel pulley down through the table to the motor pulley
bx = wx + 0.035
top = (bx, 0.0, AZ)
bot = (mx + 0.19, my, mz)
for side in (-1, 1):
    zt, zb = top[2] + side * 0.0, bot[2]
    dz = zt - zb
    dy = top[1] - bot[1]
    length = math.hypot(dz, dy)
    ang = math.atan2(dy, dz)
    off = side * 0.035
    box("vbelt", (0.012, 0.01, length), (bx, (top[1] + bot[1]) / 2 + off, (zt + zb) / 2), (-ang, 0, 0), mat=M_BELT, bevel=0)
box("belt_hole", (0.04, 0.1, TH + 0.002), (bx, 0.02, TT - TH / 2), mat=M_STEEL, bevel=0)  # worn metal grommet in the slot

# ------------------------------------------------------------- head paint wear: oil/grime + chipped edges
def add_wear(mat, spots, bed_z):
    """Darken with oil/grime around given (centre, radius) spots, low on the bed and in cavities;
    chip paint off sharp edges to bare dark metal. World position is stable through the bake
    (origin_to_bottom only shifts by a few mm in X/Y)."""
    nt = mat.node_tree
    N, Lk = nt.nodes, nt.links
    bsdf = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    col = bsdf.inputs["Base Color"].links[0].from_socket
    rgh = bsdf.inputs["Roughness"].links[0].from_socket
    geo = N.new("ShaderNodeNewGeometry")

    def node(t, **kw):
        n = N.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def maprange(src, a, b, c=0.0, d=1.0):
        m = node("ShaderNodeMapRange", clamp=True)
        m.inputs["From Min"].default_value, m.inputs["From Max"].default_value = a, b
        m.inputs["To Min"].default_value, m.inputs["To Max"].default_value = c, d
        Lk.new(src, m.inputs["Value"])
        return m.outputs["Result"]

    def math_(op, a, b):
        m = node("ShaderNodeMath", operation=op, use_clamp=True)
        for i, x in enumerate((a, b)):
            if isinstance(x, float):
                m.inputs[i].default_value = x
            else:
                Lk.new(x, m.inputs[i])
        return m.outputs[0]

    mask = None
    for (c, r) in spots:
        d = node("ShaderNodeVectorMath", operation="DISTANCE")
        Lk.new(geo.outputs["Position"], d.inputs[0])
        d.inputs[1].default_value = c
        m = maprange(d.outputs["Value"], r * 0.3, r, 1.0, 0.0)
        mask = m if mask is None else math_("MAXIMUM", mask, m)
    sep = node("ShaderNodeSeparateXYZ")
    Lk.new(geo.outputs["Position"], sep.inputs[0])
    low = maprange(sep.outputs["Z"], bed_z + 0.03, bed_z + 0.12, 0.6, 0.0)
    mask = math_("MAXIMUM", mask, low)
    nz = node("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 18
    nz.inputs["Detail"].default_value = 8
    Lk.new(geo.outputs["Position"], nz.inputs["Vector"])
    blot = maprange(nz.outputs["Fac"], 0.3, 0.6, 0.35, 1.0)
    ao = node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.04
    cav = maprange(ao.outputs["AO"], 0.95, 0.5)
    grime = math_("ADD", math_("MULTIPLY", mask, blot), math_("MULTIPLY", cav, 0.8))
    grime = math_("MULTIPLY", grime, 0.92)

    # chipped edges: bevel normal vs true normal
    bev = node("ShaderNodeBevel")
    bev.inputs["Radius"].default_value = 0.012
    dot = node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    Lk.new(bev.outputs["Normal"], dot.inputs[0])
    Lk.new(geo.outputs["Normal"], dot.inputs[1])
    edge = maprange(dot.outputs["Value"], 0.999, 0.96)
    nz2 = node("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 45
    nz2.inputs["Detail"].default_value = 10
    Lk.new(geo.outputs["Position"], nz2.inputs["Vector"])
    chip = math_("MULTIPLY", edge, maprange(nz2.outputs["Fac"], 0.4, 0.55))
    chip = math_("GREATER_THAN", chip, 0.3)

    def mixc(fac, a, b_col):
        m = node("ShaderNodeMix", data_type="RGBA")
        Lk.new(fac, m.inputs["Factor"])
        Lk.new(a, m.inputs["A"])
        m.inputs["B"].default_value = (*b_col, 1)
        return m.outputs["Result"]

    def mixf(fac, a, b_val):
        m = node("ShaderNodeMix", data_type="FLOAT")
        Lk.new(fac, m.inputs["Factor"])
        Lk.new(a, m.inputs["A"])
        m.inputs["B"].default_value = b_val
        return m.outputs["Result"]

    c1 = mixc(chip, col, (0.42, 0.40, 0.37))          # worn-through bare metal
    c2 = mixc(grime, c1, (0.045, 0.035, 0.022))       # oil and grime
    Lk.new(c2, bsdf.inputs["Base Color"])
    r1 = mixf(chip, rgh, 0.5)
    r2 = mixf(math_("MULTIPLY", mask, blot), r1, 0.28)  # fresh-looking oil stays glossier
    Lk.new(r2, bsdf.inputs["Roughness"])


add_wear(M_HEAD, [((nx, -0.02, BZ + 0.06), 0.18), ((wx, 0.0, AZ), 0.15), ((hx - 0.2, 0.0, AZ - 0.1), 0.12)], BZ)

# knee lifter under the front edge
cyl("knee_rod", 0.006, 0.18, (hx - 0.05, -TD / 2 + 0.1, LZ - 0.09), (math.radians(30), 0, 0), M_STEEL, verts=8, bevel=0)
box("knee_pad", (0.1, 0.02, 0.06), (hx - 0.05, -TD / 2 + 0.06, LZ - 0.16), mat=M_LEGS, bevel=0.005)

# ------------------------------------------------------------- thread stand (back right)
sx_, sy_ = hx + 0.22, TD / 2 - 0.07
box("stand_base", (0.2, 0.08, 0.012), (sx_, sy_, TT + 0.006), mat=M_STEEL, bevel=0.002)
cyl("stand_rod", 0.006, 0.6, (sx_, sy_, TT + 0.3), mat=M_STEEL, verts=8, bevel=0)
cyl("stand_bar", 0.004, 0.22, (sx_, sy_, TT + 0.59), AX, M_STEEL, verts=6, bevel=0)
for i, (dx, m) in enumerate(((-0.06, M_THREAD_R), (0.06, M_THREAD_W))):
    cyl("spool_pin", 0.003, 0.12, (sx_ + dx, sy_, TT + 0.07), mat=M_STEEL, verts=6, bevel=0)
    h = 0.11 - 0.025 * i     # the white cone is half used up
    cyl("cone", 0.032 - 0.008 * i, h, (sx_ + dx, sy_, TT + 0.012 + h / 2), mat=m, verts=18, bevel=0.003, r2=0.016)
    cyl("cone_guide", 0.006, 0.01, (sx_ + dx, sy_, TT + 0.59), mat=M_STEEL, verts=6, bevel=0)

# ------------------------------------------------------------- fabric scrap under the foot, draping over the front
me = bpy.data.meshes.new("cloth")
bm = bmesh.new()
nu, nv = 14, 18
x0, x1 = nx - 0.15, nx + 0.12
y0, y1 = -TD / 2 - 0.16, -0.0          # beyond the front edge it falls
grid = []
for j in range(nv + 1):
    row = []
    for i in range(nu + 1):
        x = x0 + (x1 - x0) * i / nu
        yy = y1 + (y0 - y1) * j / nv
        z = TT + 0.002
        if yy > -0.09:   # lies over the bed near the foot
            z = BZ + 0.052 if abs(x - nx) < 0.24 and yy > -0.09 else z
        y = yy
        edge = -TD / 2
        if yy < edge:
            drop = edge - yy
            y = edge - 0.004 - drop * 0.08
            z = TT - drop
        z += 0.004 + 0.002 * math.sin(i * 1.3 + j * 0.7) + 0.0015 * math.sin(i * 0.5 - j * 1.1)
        x += 0.006 * math.sin(j * 0.6)
        row.append(bm.verts.new((x, y, z)))
    grid.append(row)
for j in range(nv):
    for i in range(nu):
        border = i in (0, nu - 1) or j in (0, nv - 1)
        if border and random.random() < 0.35:   # frayed, torn-off edge
            continue
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
# ragged outline: jitter the vertices on the edge, drop the loose ones
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
for v in bm.verts:
    if any(e.is_boundary for e in v.link_edges):
        v.co.x += random.uniform(-0.006, 0.006)
        v.co.y += random.uniform(-0.006, 0.006)
# a few loose threads hanging from the bottom edge
bot_edge = [v for v in bm.verts if v.co.z < TT - 0.12 and any(e.is_boundary for e in v.link_edges)]
random.shuffle(bot_edge)
for v in bot_edge[:5]:
    ln = random.uniform(0.02, 0.05)
    a = bm.verts.new(v.co + Vector((0.0015, 0, 0)))
    b = bm.verts.new(v.co + Vector((random.uniform(-0.01, 0.01), -0.002, -ln)))
    bm.faces.new((v, a, b))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me)
bm.free()
cloth = bpy.data.objects.new("cloth", me)
bpy.context.scene.collection.objects.link(cloth)
sol = cloth.modifiers.new("Solid", "SOLIDIFY")
sol.thickness = 0.002
bkit.active(cloth)
bpy.ops.object.modifier_apply(modifier="Solid")
finish(cloth, M_CLOTH, 0)
bkit.shade_smooth(cloth)

# ------------------------------------------------------------- render / bake / export
bkit.light_studio()
if mode == "head":  # debug close-up of the machine head only (not kept)
    for o in list(parts):
        if not o.data.materials or o.data.materials[0] != M_HEAD and o.name not in ("cloth", "tabletop"):
            bpy.data.objects.remove(o)
    bkit.render_views(sys.argv[-1], size=512, samples=24)
    sys.exit(0)
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
if os.path.exists(os.path.join(OUT, ASSET + ".blend1")):
    os.remove(os.path.join(OUT, ASSET + ".blend1"))
bkit.export_glb(GLB, [obj], image_format="JPEG")
bkit.render_views(BAKED)
print("done:", GLB)
