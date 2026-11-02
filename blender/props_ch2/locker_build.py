"""Chapter 2 prop: 員工置物櫃 (3-door staff locker bank), 0.95 x 0.5 x 1.85 m.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/locker_build.py
Everything is built as one bmesh (one object), then harden -> decimate -> bake.
"""
import sys, math, random
sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy, bmesh
from mathutils import Matrix
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
OUT = f"{ROOT}/blender/bake/locker"
PREVIEW = f"{ROOT}/renders/ch2_locker_preview.png"
BAKED = f"{ROOT}/renders/ch2_locker_baked.png"
GLB = f"{ROOT}/public/models/locker.glb"
BLEND = f"{OUT}/locker.blend"
TRI_BUDGET = 4000

random.seed(7)
bkit.reset_scene()
I4 = Matrix.Identity(4)

# ---------------------------------------------------------------- dimensions (m)
BANK_W, DEPTH, Z0, ZTOP = 0.95, 0.50, 0.09, 1.85
LW = BANK_W / 3                 # one locker
FRONT_Y = -DEPTH / 2            # door front plane
BACK_Y = DEPTH / 2
CENTERS = [-LW, 0.0, LW]        # locker centres along X
T_DOOR = 0.012
DW, DH = LW - 0.008, 1.72       # door width/height (4 mm gaps)
DZC = (0.11 + 1.83) / 2         # door centre height
Y_DOOR = FRONT_Y + T_DOOR / 2   # door centre plane

# ---------------------------------------------------------------- materials
TEX = {}
def ph(name):
    TEX[name] = bkit.polyhaven_texture(name, res="1k")
    return TEX[name]

def layered_metal(name, metal, rust, tint):
    """Painted sheet metal with rust bleeding from the bottom of the seams.

    Rust mask = vertical streaks (noise stretched along Z) times a height ramp,
    so it runs down from the lower seams. Object-space box projection, so it
    bakes without needing UVs.
    """
    mat = bpy.data.materials.new(name)
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")

    def img(path, noncolor):
        t = N.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        if noncolor:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"
        t.projection_blend = 0.2
        L.new(tc.outputs["Object"], t.inputs["Vector"])
        return t

    # paint colour, tinted blue-grey
    col = img(metal["color"], False).outputs["Color"]
    tm = N.new("ShaderNodeMix"); tm.data_type = "RGBA"; tm.blend_type = "MULTIPLY"
    tm.inputs["Factor"].default_value = 1.0
    tm.inputs["B"].default_value = (*tint, 1)
    L.new(col, tm.inputs["A"]); col = tm.outputs["Result"]
    hs = N.new("ShaderNodeHueSaturation")          # 30 years of fading
    hs.inputs["Saturation"].default_value = 0.55
    hs.inputs["Value"].default_value = 0.9
    L.new(col, hs.inputs["Color"]); col = hs.outputs["Color"]

    # rust mask: vertical streaks x height ramp
    m_streak = N.new("ShaderNodeMapping")
    m_streak.inputs["Scale"].default_value = (25.0, 25.0, 1.5)
    L.new(tc.outputs["Object"], m_streak.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0
    noise.inputs["Detail"].default_value = 6.0
    L.new(m_streak.outputs["Vector"], noise.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.50
    ramp.color_ramp.elements[1].position = 0.64
    L.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    hramp = N.new("ShaderNodeMapRange")
    hramp.inputs["From Min"].default_value = 0.0
    hramp.inputs["From Max"].default_value = ZTOP
    hramp.inputs["To Min"].default_value = 1.0
    hramp.inputs["To Max"].default_value = 0.1
    L.new(sep.outputs["Z"], hramp.inputs["Value"])
    mm = N.new("ShaderNodeMath"); mm.operation = "MULTIPLY"
    L.new(ramp.outputs["Color"], mm.inputs[0])
    L.new(hramp.outputs["Result"], mm.inputs[1])
    # a little uneven coverage so it is not a clean stripe
    mm2 = N.new("ShaderNodeMath"); mm2.operation = "MULTIPLY"
    mm2.inputs[1].default_value = 0.9
    L.new(mm.outputs["Value"], mm2.inputs[0])

    rc = img(rust["color"], False).outputs["Color"]
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MIX"
    L.new(mm2.outputs["Value"], mx.inputs["Factor"])
    L.new(col, mx.inputs["A"])
    L.new(rc, mx.inputs["B"])
    L.new(mx.outputs["Result"], bsdf.inputs["Base Color"])

    L.new(img(metal["roughness"], True).outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.1
    nm = N.new("ShaderNodeNormalMap")
    L.new(img(metal["normal"], True).outputs["Color"], nm.inputs["Color"])
    L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat

def solid(name, color, rough, metal=0.0):
    mat = bpy.data.materials.new(name)
    _, bsdf = bkit._nodes(mat)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return mat

metal_tex = ph("green_metal_rust")
rust_tex = ph("rust_coarse_01")
fabric_tex = ph("denim_fabric_03")

M_METAL = layered_metal("locker_paint", metal_tex, rust_tex, tint=(0.85, 0.95, 1.0))
M_INNER = bkit.procedural_material("locker_inner", (0.15, 0.17, 0.19), roughness=0.75,
                                   metallic=0.0, scale=3.0, bump=0.2, grime=0.5)
M_CHROME = solid("hardware_steel", (0.55, 0.57, 0.6), 0.42, metal=1.0)
M_PAPER = solid("name_card", (0.72, 0.68, 0.58), 0.9)
M_WOOD = bkit.procedural_material("shelf_wood", (0.30, 0.19, 0.11), roughness=0.7,
                                  metallic=0.0, scale=5.0, bump=0.3, grime=0.3)
M_FABRIC = bkit.pbr_material("costume_fabric", fabric_tex, scale=2.0,
                             tint=(0.85, 0.3, 0.32), coords="BOX")
M_DARK = solid("padlock_steel", (0.09, 0.09, 0.1), 0.5, metal=0.6)
M_VOID = solid("vent_shadow", (0.012, 0.012, 0.013), 0.95)   # seen through the louvres
MATS = [M_METAL, M_INNER, M_CHROME, M_PAPER, M_WOOD, M_FABRIC, M_DARK, M_VOID]
MI_METAL, MI_INNER, MI_CHROME, MI_PAPER, MI_WOOD, MI_FABRIC, MI_DARK, MI_VOID = range(8)

# ---------------------------------------------------------------- geometry helpers
bm = bmesh.new()

def emit(src, M, mat):
    """Copy a small bmesh src into bm with transform M and material index mat."""
    vmap = {v: bm.verts.new(M @ v.co) for v in src.verts}
    bm.verts.ensure_lookup_table()
    for f in src.faces:
        nf = bm.faces.new([vmap[v] for v in f.verts])
        nf.material_index = mat
    src.free()

def T(x, y, z):
    return Matrix.Translation((x, y, z))

def box(c, s, mat, G=I4):
    src = bmesh.new()
    bmesh.ops.create_cube(src, size=1.0)
    emit(src, G @ T(*c) @ Matrix.Diagonal((*s, 1.0)), mat)

def emit_cube(M, s, mat):
    src = bmesh.new()
    bmesh.ops.create_cube(src, size=1.0)
    emit(src, M @ Matrix.Diagonal((*s, 1.0)), mat)

def cyl(c, r, h, mat, G=I4, rot=I4, seg=8):
    """Cylinder centred at c, axis Z before rot."""
    src = bmesh.new()
    bmesh.ops.create_cone(src, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r, depth=h)
    emit(src, G @ T(*c) @ rot, mat)

def rx(d):
    return Matrix.Rotation(math.radians(d), 4, "X")

def rz(d):
    return Matrix.Rotation(math.radians(d), 4, "Z")

def door_slab(W, H, t, nx, nz, dent=None):
    """Sheet door: nx*nz front grid (so a dent can be pushed in), back as one n-gon."""
    src = bmesh.new()
    F = [[None] * (nx + 1) for _ in range(nz + 1)]
    for j in range(nz + 1):
        for i in range(nx + 1):
            x = W * i / nx
            z = -H / 2 + H * j / nz
            dy = dent(x, z) if dent else 0.0
            F[j][i] = src.verts.new((x, -t / 2 + dy, z))
    for j in range(nz):
        for i in range(nx):
            src.faces.new([F[j][i], F[j][i + 1], F[j + 1][i + 1], F[j + 1][i]])
    # perimeter, counter-clockwise in the XZ plane
    per = ([(0, i) for i in range(nx)] + [(j, nx) for j in range(nz)]
           + [(nz, i) for i in range(nx, 0, -1)] + [(j, 0) for j in range(nz, 0, -1)])
    B = {}
    for (j, i) in per:
        B[(j, i)] = src.verts.new((F[j][i].co.x, t / 2, F[j][i].co.z))
    for k in range(len(per)):
        a, b = per[k], per[(k + 1) % len(per)]
        src.faces.new([F[a[0]][a[1]], F[b[0]][b[1]], B[b], B[a]])
    src.faces.new([B[p] for p in per])
    bmesh.ops.recalc_face_normals(src, faces=src.faces[:])
    return src

def emit_slab(src, M, mat):
    emit(src, M, mat)

# ---------------------------------------------------------------- carcass
for cx in CENTERS:

    hgt = ZTOP - Z0
    box((cx - LW / 2 + 0.006, 0, Z0 + hgt / 2), (0.012, DEPTH, hgt), MI_METAL)   # left side
    box((cx + LW / 2 - 0.006, 0, Z0 + hgt / 2), (0.012, DEPTH, hgt), MI_METAL)   # right side
    box((cx, 0, ZTOP - 0.006), (LW, DEPTH, 0.012), MI_METAL)                     # roof
    box((cx, 0, Z0 + 0.006), (LW, DEPTH, 0.012), MI_METAL)                       # floor
    box((cx, BACK_Y - 0.006, Z0 + hgt / 2), (LW, 0.012, hgt), MI_METAL)          # back
    box((cx, BACK_Y - 0.012, Z0 + hgt / 2), (LW - 0.024, 0.004, hgt - 0.05), MI_INNER)  # dark inner back
    # a stiffening lip along the top and bottom front edges
    box((cx, FRONT_Y + 0.006, ZTOP - 0.02), (LW, 0.012, 0.02), MI_METAL)

# plinth (recessed toe kick)
box((0, 0.03, Z0 / 2), (BANK_W, DEPTH - 0.06, Z0), MI_METAL)

# ---------------------------------------------------------------- interior of middle locker
c = CENTERS[1]
# hanging shelf on two rods from the roof
box((c, BACK_Y - 0.14, 1.18), (LW - 0.03, 0.2, 0.02), MI_WOOD)
for sx in (-0.11, 0.11):
    cyl((c + sx, BACK_Y - 0.14, 1.52), 0.003, 0.66, MI_CHROME)
# coat hook on the back panel
box((c, BACK_Y - 0.012 - 0.003, 1.52), (0.03, 0.006, 0.03), MI_CHROME)
cyl((c, BACK_Y - 0.04, 1.52), 0.004, 0.07, MI_CHROME, rot=rx(90))
cyl((c, BACK_Y - 0.076, 1.49), 0.004, 0.025, MI_CHROME, rot=rx(0))

# crumpled performer's costume bag on the floor
src = bmesh.new()
bmesh.ops.create_icosphere(src, subdivisions=2, radius=1.0)
for v in src.verts:
    v.co += v.co.normalized() * random.uniform(-0.18, 0.18)
    v.co.x *= 0.12 ; v.co.y *= 0.09 ; v.co.z *= 0.11  # squashed, crumpled blob
src.verts.ensure_lookup_table()
emit(src, T(c + 0.01, 0.04, Z0 + 0.012 + 0.07), MI_FABRIC)
# (note: radius 1.0 * per-axis scale above gives ~0.12 x 0.09 x 0.11 m half-extents)

# ---------------------------------------------------------------- doors
# door geometry is built in a frame whose origin is the hinge (left edge, front plane)
DOOR_SPECS = [
    # (locker index, open angle in degrees, has dent)
    (0, 0.0, True),
    (1, -40.0, False),   # middle door open 40 degrees, swinging outward (-Y)
    (2, 0.0, False),
]

for idx, angle, dented in DOOR_SPECS:
    cx = CENTERS[idx]
    hinge = (cx - DW / 2, Y_DOOR, DZC)
    G = T(*hinge) @ rz(angle)

    dent = None
    if dented:
        du, dz, R, depth = 0.13, -0.42, 0.13, 0.008
        def dent(x, z, du=du, dz=dz, R=R, depth=depth):
            d = math.hypot(x - du, z - dz)
            return depth * (1 - d / R) ** 2 if d < R else 0.0
        nx, nz = 10, 16
    else:
        nx, nz = 6, 10
    slab = door_slab(DW, DH, T_DOOR, nx, nz, dent=dent)
    # slab is in a frame with x from 0 (hinge) to DW, z centred on 0
    emit_slab(slab, G, MI_METAL)

    # local helpers: put things in door-frame coordinates, then move with the door
    u_c = DW / 2
    front = -T_DOOR / 2
    # two louvre vents, top and bottom
    for zv in (0.56, -0.60):
        box((u_c, front - 0.0015, zv), (0.20, 0.003, 0.26), MI_VOID, G)
        for k in range(6):
            zs = zv - 0.11 + k * 0.044
            # each slat tilted about its own centre: G @ T(centre) @ rx @ scale
            emit_cube(G @ T(u_c, front - 0.009, zs) @ rx(-28), (0.19, 0.003, 0.036), MI_METAL)
    # handle, hasp, padlock
    hx = DW - 0.035
    box((hx, front - 0.0045, 0.0), (0.03, 0.006, 0.09), MI_CHROME, G)
    box((hx, front - 0.0125, 0.0), (0.014, 0.018, 0.10), MI_CHROME, G)
    box((hx, front - 0.0045, -0.15), (0.05, 0.006, 0.075), MI_CHROME, G)
    box((hx, front - 0.012, -0.20), (0.036, 0.022, 0.042), MI_DARK, G)
    for dx in (-0.012, 0.012):
        box((hx + dx, front - 0.012, -0.135), (0.005, 0.006, 0.03), MI_DARK, G)
    box((hx, front - 0.012, -0.12), (0.03, 0.006, 0.006), MI_DARK, G)
    # name-card holder
    box((u_c, front - 0.0045, 0.76), (0.074, 0.006, 0.036), MI_CHROME, G)
    box((u_c, front - 0.0085, 0.76), (0.060, 0.004, 0.024), MI_PAPER, G)
    # three visible hinge knuckles on the hinge edge
    for z in (-0.66, 0.0, 0.66):
        cyl((0.0, 0.0, z), 0.0065, 0.09, MI_CHROME, G=G)
        box((0.012, 0.0, z), (0.024, 0.004, 0.10), MI_CHROME, G)

# ---------------------------------------------------------------- build the object
me = bpy.data.meshes.new("locker")
bm.normal_update()
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(me)
bm.free()
obj = bpy.data.objects.new("locker", me)
bpy.context.scene.collection.objects.link(obj)
for m in MATS:
    me.materials.append(m)
for p in me.polygons:
    p.use_smooth = False

bkit.harden(obj, width=0.003, segments=1, angle=35)
bkit.decimate(obj, TRI_BUDGET)
bkit.origin_to_bottom(obj)

import os
os.makedirs(OUT, exist_ok=True)
bkit.light_studio()
bkit.render_views(PREVIEW)
print("preview", PREVIEW)

# ---------------------------------------------------------------- game-ready: bake + export
bkit.uv_unwrap(obj)
bkit.bake_to_textures(obj, OUT, size=1024)
bkit.report([obj])
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bkit.export_glb(GLB, [obj], image_format="JPEG")
bkit.render_views(BAKED)
print("baked", BAKED)
