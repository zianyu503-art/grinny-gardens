"""Chapter 2 prop: a Ferris wheel gondola taken off the wheel and left on timber blocks
in the factory repair bay. Red painted steel tub with a cream band, a door hanging open,
two vinyl benches facing each other, four posts, a domed roof with dead bulb sockets and
the hanger yoke with its pivot bushing (sheared bolt). About 1.55 x 1.35 x 2.5 m.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/ferris_cabin_build.py
Z up, standing on z = 0, door on the -Y (front) side. Built as one bmesh, then
harden -> decimate -> bake -> export.
"""
import sys, math, random, os
sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy, bmesh
from mathutils import Matrix, Vector
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
ASSET = "ferris_cabin"
OUT = f"{ROOT}/blender/bake/{ASSET}"
PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_preview.png"
BAKED = f"{ROOT}/renders/ch2_{ASSET}_baked.png"
GLB = f"{ROOT}/public/models/{ASSET}.glb"
BLEND = f"{OUT}/{ASSET}.blend"
TRI_BUDGET = 6000

random.seed(11)
bkit.reset_scene()
I4 = Matrix.Identity(4)

# ---------------------------------------------------------------- dimensions (m)
W, D, R = 1.40, 1.20, 0.26        # tub footprint and corner radius
T_WALL = 0.022
Z_BLOCK = 0.10                    # timber blocks it was set down on
Z_FLOOR = 0.16                    # top of the floor pan
Z_RIM = 0.98                      # top of the tub wall
Z_ROOF = 1.88                     # underside of roof
GATE = 0.30                       # half width of the door opening
DOOR_OPEN = -32.0                 # degrees, swung outward

# ---------------------------------------------------------------- materials
def ph(name):
    return bkit.polyhaven_texture(name, res="1k")

def painted(name, maps, sat, val, tint, scale=1.0, hue=0.5, rust=None, rust_amt=0.0):
    """Box-projected scanned paint, faded (sat/val), tinted, darker grime toward the floor."""
    mat = bpy.data.materials.new(name)
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale,) * 3
    L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(slot, noncolor):
        t = N.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(maps[slot], check_existing=True)
        if noncolor:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"
        t.projection_blend = 0.2
        L.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t

    col = img("color", False).outputs["Color"]
    hs = N.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = sat
    hs.inputs["Value"].default_value = val
    hs.inputs["Hue"].default_value = hue
    L.new(col, hs.inputs["Color"])
    tm = N.new("ShaderNodeMix"); tm.data_type = "RGBA"; tm.blend_type = "MULTIPLY"
    tm.inputs["Factor"].default_value = 1.0
    tm.inputs["B"].default_value = (*tint, 1)
    L.new(hs.outputs["Color"], tm.inputs["A"])
    paint = tm.outputs["Result"]
    if rust:
        # rust bleeding down in vertical streaks, heavier low down
        ms = N.new("ShaderNodeMapping")
        ms.inputs["Scale"].default_value = (22.0, 22.0, 1.6)
        L.new(tc.outputs["Object"], ms.inputs["Vector"])
        rn = N.new("ShaderNodeTexNoise")
        rn.inputs["Scale"].default_value = 1.0
        rn.inputs["Detail"].default_value = 6.0
        L.new(ms.outputs["Vector"], rn.inputs["Vector"])
        rr = N.new("ShaderNodeValToRGB")
        rr.color_ramp.elements[0].position = 0.52
        rr.color_ramp.elements[1].position = 0.66
        L.new(rn.outputs["Fac"], rr.inputs["Fac"])
        sz = N.new("ShaderNodeSeparateXYZ")
        L.new(tc.outputs["Object"], sz.inputs["Vector"])
        hr = N.new("ShaderNodeMapRange")
        hr.inputs["From Min"].default_value = 0.1
        hr.inputs["From Max"].default_value = 2.4
        hr.inputs["To Min"].default_value = rust_amt
        hr.inputs["To Max"].default_value = rust_amt * 0.3
        L.new(sz.outputs["Z"], hr.inputs["Value"])
        rm = N.new("ShaderNodeMath"); rm.operation = "MULTIPLY"
        L.new(rr.outputs["Color"], rm.inputs[0]); L.new(hr.outputs["Result"], rm.inputs[1])
        rimg = img_any(N, L, rust["color"], mp)
        rmix = N.new("ShaderNodeMix"); rmix.data_type = "RGBA"
        L.new(rm.outputs["Value"], rmix.inputs["Factor"])
        L.new(paint, rmix.inputs["A"]); L.new(rimg.outputs["Color"], rmix.inputs["B"])
        paint = rmix.outputs["Result"]
    # grime: multiply darker near the floor, broken up by noise
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.1
    mr.inputs["From Max"].default_value = 0.8
    mr.inputs["To Min"].default_value = 0.55
    mr.inputs["To Max"].default_value = 1.0
    L.new(sep.outputs["Z"], mr.inputs["Value"])
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 6.0
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = N.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"
    mx.inputs[2].default_value = 0.8
    L.new(nz.outputs["Fac"], mx.inputs[0]); mx.inputs[1].default_value = 0.35
    g = N.new("ShaderNodeMath"); g.operation = "MULTIPLY"
    L.new(mr.outputs["Result"], g.inputs[0]); L.new(mx.outputs["Value"], g.inputs[1])
    gm = N.new("ShaderNodeMix"); gm.data_type = "RGBA"; gm.blend_type = "MULTIPLY"
    L.new(paint, gm.inputs["A"])
    gm.inputs["Factor"].default_value = 1.0
    cr = N.new("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        L.new(g.outputs["Value"], cr.inputs[k])
    L.new(cr.outputs["Color"], gm.inputs["B"])
    L.new(gm.outputs["Result"], bsdf.inputs["Base Color"])
    if "roughness" in maps:
        L.new(img("roughness", True).outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    if "normal" in maps:
        nm = N.new("ShaderNodeNormalMap")
        L.new(img("normal", True).outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat

def img_any(N, L, path, mp):
    t = N.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    t.projection = "BOX"
    t.projection_blend = 0.2
    L.new(mp.outputs["Vector"], t.inputs["Vector"])
    return t

def solid(name, color, rough, metal=0.0):
    mat = bpy.data.materials.new(name)
    _, bsdf = bkit._nodes(mat)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return mat

TX_PAINT = ph("green_metal_rust")
TX_RUST = ph("rust_coarse_01")
TX_STEEL = ph("rusty_metal_02")
TX_VINYL = ph("brown_leather")
TX_WOOD = ph("old_planks_02")
TX_FLOOR = ph("metal_plate")

# green scanned paint hue-shifted to a faded fairground red; cream from the same scan
# red: the scan fully desaturated, then tinted, so no hue-shifted specks can turn purple
M_RED = painted("cabin_red", TX_PAINT, sat=0.0, val=2.0, tint=(0.52, 0.13, 0.10),
                scale=0.8, rust=TX_RUST, rust_amt=0.85)
M_CREAM = painted("cabin_cream", TX_PAINT, sat=0.12, val=2.2, tint=(0.95, 0.88, 0.72),
                  scale=0.8, rust=TX_RUST, rust_amt=0.6)
def chipped_steel(name):
    """Steel painted the same cream as the trim, faded and chipped; brown rust and dark
    steel show through the chips, which get denser toward the post bases (z ~ 1.0)."""
    mat = painted(name, TX_PAINT, sat=0.12, val=2.2, tint=(0.95, 0.88, 0.72), scale=0.8,
                  rust=TX_RUST, rust_amt=0.45)
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    paint = bsdf.inputs["Base Color"].links[0].from_socket
    tc = next(n for n in N if n.type == "TEX_COORD")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0,) * 3
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    steel = img_any(N, L, TX_STEEL["color"], mp)
    hs = N.new("ShaderNodeHueSaturation")          # orange rust -> dull brown
    hs.inputs["Saturation"].default_value = 0.55
    hs.inputs["Value"].default_value = 0.55
    L.new(steel.outputs["Color"], hs.inputs["Color"])
    tm = N.new("ShaderNodeMix"); tm.data_type = "RGBA"; tm.blend_type = "MULTIPLY"
    tm.inputs["Factor"].default_value = 1.0
    tm.inputs["B"].default_value = (0.62, 0.48, 0.40, 1)
    L.new(hs.outputs["Color"], tm.inputs["A"])
    # chip mask: sharp-edged noise, plus extra exposure near the post bases
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 16.0
    nz.inputs["Detail"].default_value = 10.0
    nz.inputs["Roughness"].default_value = 0.65
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    sz = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sz.inputs["Vector"])
    base = N.new("ShaderNodeMapRange")
    base.inputs["From Min"].default_value = 1.0
    base.inputs["From Max"].default_value = 1.25
    base.inputs["To Min"].default_value = 0.14
    base.inputs["To Max"].default_value = 0.0
    L.new(sz.outputs["Z"], base.inputs["Value"])
    add = N.new("ShaderNodeMath"); add.operation = "ADD"
    L.new(nz.outputs["Fac"], add.inputs[0]); L.new(base.outputs["Result"], add.inputs[1])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.56
    ramp.color_ramp.elements[1].position = 0.59
    L.new(add.outputs["Value"], ramp.inputs["Fac"])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
    L.new(ramp.outputs["Color"], mx.inputs["Factor"])
    L.new(paint, mx.inputs["A"]); L.new(tm.outputs["Result"], mx.inputs["B"])
    L.new(mx.outputs["Result"], bsdf.inputs["Base Color"])
    return mat

M_STEEL = chipped_steel("painted_steel")
M_RUST = bkit.pbr_material("rusted_steel", TX_STEEL, scale=2.0, coords="BOX",
                           tint=(0.30, 0.23, 0.19), roughness_mult=1.1)
M_VINYL = bkit.pbr_material("bench_vinyl", TX_VINYL, scale=2.5, coords="BOX",
                            tint=(1.0, 0.55, 0.5), roughness_mult=1.3)
M_WOOD = bkit.pbr_material("dunnage_wood", TX_WOOD, scale=1.5, coords="BOX", tint=(0.8, 0.75, 0.7))
M_FLOOR = bkit.pbr_material("floor_plate", TX_FLOOR, scale=1.5, coords="BOX", tint=(0.6, 0.58, 0.55))
M_GLASS = solid("dead_bulb", (0.32, 0.30, 0.26), 0.25)
M_DARK = solid("dark_steel", (0.07, 0.07, 0.075), 0.55, metal=0.7)
MATS = [M_RED, M_CREAM, M_STEEL, M_VINYL, M_WOOD, M_FLOOR, M_GLASS, M_DARK, M_RUST]
RED, CREAM, STEEL, VINYL, WOOD, FLOOR, GLASS, DARK, RUST = range(len(MATS))

# ---------------------------------------------------------------- geometry helpers
bm = bmesh.new()

def emit(src, M, mat):
    vmap = {v: bm.verts.new(M @ v.co) for v in src.verts}
    for f in src.faces:
        bm.faces.new([vmap[v] for v in f.verts]).material_index = mat
    src.free()

def T(x, y, z):
    return Matrix.Translation((x, y, z))

def rz(d):
    return Matrix.Rotation(math.radians(d), 4, "Z")

def ry(d):
    return Matrix.Rotation(math.radians(d), 4, "Y")

def rx(d):
    return Matrix.Rotation(math.radians(d), 4, "X")

def box(c, s, mat, G=I4, rot=I4):
    src = bmesh.new()
    bmesh.ops.create_cube(src, size=1.0)
    emit(src, G @ T(*c) @ rot @ Matrix.Diagonal((*s, 1.0)), mat)

def cyl(c, r, h, mat, G=I4, rot=I4, seg=8, r2=None):
    src = bmesh.new()
    bmesh.ops.create_cone(src, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    emit(src, G @ T(*c) @ rot, mat)

def bar(a, b, w, t, mat, roll_up=Vector((1, 0, 0))):
    """Flat bar from point a to b, w wide (along roll_up-ish) and t thick."""
    a, b = Vector(a), Vector(b)
    d = b - a
    z = d.normalized()
    x = roll_up - roll_up.dot(z) * z
    x.normalize()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = (a + b) / 2
    box((0, 0, 0), (w, t, d.length), mat, G=M)

def rrect(w, d, r, n=5, gap=None):
    """Rounded rectangle path, CCW from above. With gap, an open path that starts at
    (gap, -d/2) on the front edge and ends at (-gap, -d/2)."""
    hx, hy = w / 2 - r, d / 2 - r
    pts = []
    if gap is not None:
        pts.append((gap, -d / 2))
    for cx, cy, a0 in ((hx, -hy, -90), (hx, hy, 0), (-hx, hy, 90), (-hx, -hy, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if gap is not None:
        pts.append((-gap, -d / 2))
    return pts

def offsets(path, closed):
    """Outward unit normal at each path point (CCW path)."""
    n = len(path)
    out = []
    for i in range(n):
        p0 = Vector(path[i - 1] if (closed or i > 0) else path[i])
        p1 = Vector(path[(i + 1) % n] if (closed or i < n - 1) else path[i])
        d = (p1 - p0).normalized()
        out.append(Vector((d.y, -d.x)))
    return out

def strip(path, z0, z1, t, mat, closed=False, out=0.0):
    """Wall of thickness t along path (outer face pushed out by `out`)."""
    src = bmesh.new()
    nrm = offsets(path, closed)
    rings = []
    for (x, y), nv in zip(path, nrm):
        o = Vector((x, y)) + nv * out
        i = o - nv * t
        rings.append([src.verts.new((o.x, o.y, z0)), src.verts.new((o.x, o.y, z1)),
                      src.verts.new((i.x, i.y, z1)), src.verts.new((i.x, i.y, z0))])
    n = len(rings)
    for k in range(n if closed else n - 1):
        a, b = rings[k], rings[(k + 1) % n]
        for j in range(4):
            src.faces.new([a[j], b[j], b[(j + 1) % 4], a[(j + 1) % 4]])
    if not closed:
        src.faces.new(rings[0][::-1])
        src.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(src, faces=src.faces[:])
    emit(src, I4, mat)

def slab(path, z0, z1, mat, s0=1.0, s1=1.0):
    """Prism over a closed path, bottom loop scaled s0, top loop scaled s1."""
    src = bmesh.new()
    lo = [src.verts.new((x * s0, y * s0, z0)) for x, y in path]
    hi = [src.verts.new((x * s1, y * s1, z1)) for x, y in path]
    n = len(path)
    for k in range(n):
        src.faces.new([lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]])
    src.faces.new(lo[::-1])
    src.faces.new(hi)
    bmesh.ops.recalc_face_normals(src, faces=src.faces[:])
    emit(src, I4, mat)

# ---------------------------------------------------------------- dunnage blocks
for x in (-0.42, 0.44):
    box((x, random.uniform(-0.03, 0.03), Z_BLOCK / 2), (0.10, 1.18, Z_BLOCK), WOOD,
        rot=rz(random.uniform(-4, 4)))

# ---------------------------------------------------------------- tub
loop = rrect(W, D, R)
slab(loop, Z_BLOCK, Z_FLOOR - 0.01, RED, s0=0.9)            # tapered belly pan
slab(rrect(W - 0.03, D - 0.03, R - 0.015), Z_FLOOR - 0.01, Z_FLOOR, RED)
slab(rrect(W - 2 * T_WALL - 0.01, D - 2 * T_WALL - 0.01, R - T_WALL), Z_FLOOR, Z_FLOOR + 0.006, FLOOR)
wall = rrect(W, D, R, gap=GATE)
strip(wall, Z_FLOOR - 0.01, Z_RIM, T_WALL, RED)
strip(wall, Z_RIM, Z_RIM + 0.035, T_WALL + 0.02, CREAM, out=0.012)       # rolled top rail
strip(wall, 0.52, 0.60, 0.006, CREAM, out=0.004)                         # cream trim band
strip(wall, Z_FLOOR + 0.02, Z_FLOOR + 0.06, 0.006, DARK, out=0.004)       # rubbing strip
# door jamb posts at the opening
for sx in (-1, 1):
    box((sx * (GATE + 0.012), -D / 2 + T_WALL / 2, (Z_FLOOR + Z_RIM) / 2),
        (0.024, T_WALL + 0.02, Z_RIM - Z_FLOOR), STEEL)
# number plate on the back
box((0.0, D / 2 + 0.008, 0.78), (0.20, 0.006, 0.15), CREAM)
box((0.0, D / 2 + 0.012, 0.78), (0.05, 0.004, 0.11), DARK)                  # stencilled "1"

# ---------------------------------------------------------------- door (hinged at -GATE)
G = T(-GATE + 0.004, -D / 2 + 0.002, 0) @ rz(DOOR_OPEN)
DW = 2 * GATE - 0.012
dz0, dz1 = Z_FLOOR + 0.01, Z_RIM - 0.01
box((DW / 2, 0, (dz0 + dz1) / 2), (DW, T_WALL, dz1 - dz0), RED, G)
box((DW / 2, -0.012, 0.56), (DW, 0.006, 0.08), CREAM, G)
box((DW / 2, 0, dz1 + 0.015), (DW, T_WALL + 0.02, 0.03), CREAM, G)
box((DW - 0.04, -0.03, 0.80), (0.05, 0.03, 0.03), STEEL, G)                # latch
box((DW - 0.015, -0.02, 0.80), (0.012, 0.025, 0.07), DARK, G)
for z in (0.32, 0.82):                                                     # hinges
    cyl((0.0, -0.016, z), 0.012, 0.08, STEEL, G)
    box((0.04, -0.013, z), (0.08, 0.004, 0.06), STEEL, G)

# ---------------------------------------------------------------- benches
for sx in (-1, 1):
    xin = W / 2 - T_WALL
    box((sx * (xin - 0.17), 0, (Z_FLOOR + 0.42) / 2), (0.30, 0.70, 0.42 - Z_FLOOR), RED)
    box((sx * (xin - 0.19), 0, 0.44), (0.38, 0.78, 0.04), STEEL)
    # cushions, a little uneven
    sq = random.uniform(-0.01, 0.01)
    box((sx * (xin - 0.19), 0.0, 0.495 + sq), (0.36, 0.74, 0.07), VINYL,
        rot=ry(sx * random.uniform(0.5, 2.0)))
    box((sx * (xin - 0.035), 0.0, 0.73), (0.05, 0.72, 0.36), VINYL,
        rot=ry(-sx * random.uniform(2, 5)))
# a torn flap of vinyl peeling off the left cushion
box((-(W / 2 - T_WALL - 0.03), -0.30, 0.53), (0.12, 0.14, 0.008), VINYL, rot=rx(35) @ ry(-25))

# grab bar across the inside of the door opening
cyl((0.0, -D / 2 + 0.06, 0.86), 0.014, 0.90, STEEL, rot=ry(90))
for sx in (-1, 1):
    cyl((sx * 0.44, -D / 2 + 0.04, 0.86), 0.012, 0.05, STEEL, rot=rx(90))

# ---------------------------------------------------------------- posts and roof
hx, hy = W / 2 - R, D / 2 - R
post_pts = []
for cx, cy in ((hx, -hy), (hx, hy), (-hx, hy), (-hx, -hy)):
    d = Vector((cx, cy)).normalized()
    p = Vector((cx, cy)) + d * (R - T_WALL - 0.03)
    post_pts.append(p)
    lean = random.uniform(-0.6, 0.6)
    cyl((p.x, p.y, (Z_RIM + Z_ROOF) / 2), 0.022, Z_ROOF - Z_RIM + 0.03, STEEL,
        rot=rx(lean), seg=8)
    cyl((p.x, p.y, Z_RIM + 0.05), 0.032, 0.05, RUST)                        # base collar
roofl = rrect(W + 0.14, D + 0.14, R + 0.07, n=6)
slab(roofl, Z_ROOF, Z_ROOF + 0.06, CREAM, s0=0.985)
slab(roofl, Z_ROOF + 0.06, Z_ROOF + 0.14, RED, s0=1.0, s1=0.82)
slab(roofl, Z_ROOF + 0.14, Z_ROOF + 0.20, RED, s0=0.82, s1=0.45)
ZTOPR = Z_ROOF + 0.20

# bulb sockets around the roof edge; some bulbs missing or broken
for k, (x, y) in enumerate(rrect(W + 0.14, D + 0.14, R + 0.07, n=2)[::1]):
    if k % 2:
        continue
    p = Vector((x, y)) * 0.99
    cyl((p.x, p.y, Z_ROOF - 0.018), 0.017, 0.03, DARK, seg=6)
    if random.random() < 0.65:
        cyl((p.x, p.y, Z_ROOF - 0.05), 0.02, 0.04, GLASS, seg=6, r2=0.012)

# ---------------------------------------------------------------- hanger yoke + pivot
ZPIV = ZTOPR + 0.34
for sy in (-1, 1):
    bar((0, sy * 0.30, ZTOPR - 0.02), (0, sy * 0.075, ZPIV), 0.07, 0.014, STEEL)
    box((0, sy * 0.30, ZTOPR - 0.005), (0.14, 0.10, 0.012), STEEL)           # foot plate
    for bx in (-0.045, 0.045):
        cyl((bx, sy * 0.30, ZTOPR + 0.006), 0.008, 0.014, DARK, seg=6)       # bolt heads
box((0, 0, ZTOPR + 0.11), (0.05, 0.52, 0.03), STEEL)                          # tie bar
cyl((0, 0, ZPIV), 0.055, 0.17, RUST, rot=rx(90), seg=12)                    # pivot bushing
cyl((0, 0, ZPIV), 0.028, 0.24, DARK, rot=rx(90), seg=8)                      # sheared axle stub
cyl((0, 0, ZPIV + 0.09), 0.012, 0.05, DARK, seg=6)                           # grease nipple

# ---------------------------------------------------------------- build object
me = bpy.data.meshes.new(ASSET)
bm.normal_update()
bm.to_mesh(me)
bm.free()
obj = bpy.data.objects.new(ASSET, me)
bpy.context.scene.collection.objects.link(obj)
for m in MATS:
    me.materials.append(m)

bkit.harden(obj, width=0.004, segments=1, angle=35)
bkit.decimate(obj, TRI_BUDGET)
bkit.origin_to_bottom(obj)

os.makedirs(OUT, exist_ok=True)
bkit.light_studio()
bkit.render_views(PREVIEW)
print("preview", PREVIEW)
if "--preview" in sys.argv:
    bkit.report([obj])
    raise SystemExit

# ---------------------------------------------------------------- game-ready: bake + export
bkit.uv_unwrap(obj)
bkit.bake_to_textures(obj, OUT, size=1024)
bkit.report([obj])
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bkit.export_glb(GLB, [obj], image_format="JPEG")
bkit.render_views(BAKED)
print("baked", BAKED)
