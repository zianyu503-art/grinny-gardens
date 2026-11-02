"""Chapter 2 prop: joy_machine - the 1990s laughter-extraction machine of the toy factory.

A riveted sheet-steel cabinet on an I-beam skid, a green pressure tank on top crowned with a
big brass gramophone horn (the "laughter collector"), a front control panel with gauges,
buttons and a throw lever, a hand crank on the left, and a pipe run with a valve that drops
to a nozzle over a jar cradle on the right. A cut rubber hose droops to the floor.
Abandoned ~30 years: rust, faded paint, tarnished brass.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/joy_machine_build.py            # full
    blender -b --factory-startup -P blender/props_ch2/joy_machine_build.py -- preview # pre-bake render only

Units: metres. Z up, standing on z=0, front (control panel) faces -Y.
"""
import sys
import math
import random

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import bkit  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
ASSET = "joy_machine"
BAKE_DIR = f"{ROOT}/blender/bake/{ASSET}"
PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_preview.png"
BAKED_PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_baked.png"
GLB = f"{ROOT}/public/models/{ASSET}.glb"
BLEND = f"{BAKE_DIR}/{ASSET}.blend"
TRI_BUDGET = 7300
BAKE_SIZE = 2048

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW_ONLY = "preview" in ARGS

random.seed(1996)
bkit.reset_scene()
PARTS = []


# ---------------------------------------------------------------- materials

def tex(tid):
    return bkit.polyhaven_texture(tid, "1k")


def jitter(base, amt=0.07):
    return tuple(max(0, c * (1 + random.uniform(-amt, amt))) for c in base)


def _n(nt, kind, **inputs):
    node = nt.nodes.new(kind)
    for key, v in inputs.items():
        node.inputs[key].default_value = v
    return node


def _math(nt, op, a, b, clamp=False):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = clamp
    for idx, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            m.inputs[idx].default_value = v
        else:
            nt.links.new(v, m.inputs[idx])
    return m.outputs[0]


def _mixc(nt, fac, a, b):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    for sock, v in (("Factor", fac), ("A", a), ("B", b)):
        if isinstance(v, tuple):
            m.inputs[sock].default_value = v
        elif isinstance(v, (int, float)):
            m.inputs[sock].default_value = v
        else:
            nt.links.new(v, m.inputs[sock])
    return m.outputs["Result"]


def _ramp(nt, src, c0, c1, p0=0.0, p1=1.0):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position, r.color_ramp.elements[0].color = p0, (*c0, 1)
    r.color_ramp.elements[1].position, r.color_ramp.elements[1].color = p1, (*c1, 1)
    nt.links.new(src, r.inputs["Fac"])
    return r.outputs["Color"]


def brass_material(name, verd_bias=0.0, worn=0.0):
    """Decades-old brass: brown-black tarnish (rough, weak sheen), pale-green verdigris pooled
    where AO says crevice/joint (plus noise breakup, verd_bias pushes coverage), and optionally
    small bright worn spots (worn=1, horn rim only)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = _n(nt, "ShaderNodeTexNoise", Scale=7.0, Detail=8.0)
    n2 = _n(nt, "ShaderNodeTexNoise", Scale=28.0, Detail=10.0, Roughness=0.65)
    n3 = _n(nt, "ShaderNodeTexNoise", Scale=45.0, Detail=4.0)
    for nn in (n1, n2, n3):
        L.new(tc.outputs["Object"], nn.inputs["Vector"])
    ao = _n(nt, "ShaderNodeAmbientOcclusion", Distance=0.06)
    tarnish = _ramp(nt, n1.outputs["Fac"], (0.035, 0.024, 0.012), (0.10, 0.068, 0.03), 0.3, 0.7)
    verd_col = _ramp(nt, n2.outputs["Fac"], (0.07, 0.16, 0.11), (0.20, 0.33, 0.25), 0.35, 0.65)
    # verdigris mask: crevice (1-AO) + mottling noise + bias
    crev = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, ao.outputs["AO"]), 2.2)
    mott = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", n2.outputs["Fac"], 0.5), 1.6)
    vm = _math(nt, "ADD", _math(nt, "ADD", crev, mott), verd_bias - 0.1)
    vm = _math(nt, "MULTIPLY", vm, 2.5, clamp=True)
    col = _mixc(nt, vm, tarnish, verd_col)
    metal = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, vm), 0.7)
    rough = _math(nt, "ADD", _math(nt, "MULTIPLY", vm, 0.3), 0.58)
    if worn:
        wm = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", n3.outputs["Fac"], 0.6), 12.0, clamp=True)
        wm = _math(nt, "MULTIPLY", wm, worn)
        col = _mixc(nt, wm, col, (0.45, 0.32, 0.13, 1))
        metal = _math(nt, "ADD", _math(nt, "MULTIPLY", metal, _math(nt, "SUBTRACT", 1.0, wm)), wm)
        rough = _math(nt, "SUBTRACT", rough, _math(nt, "MULTIPLY", wm, 0.25))
    L.new(col, bsdf.inputs["Base Color"])
    L.new(metal, bsdf.inputs["Metallic"])
    L.new(rough, bsdf.inputs["Roughness"])
    bump = _n(nt, "ShaderNodeBump", Strength=0.25, Distance=0.01)
    L.new(n2.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def paint_material(tint):
    """Painted sheet steel. rusty_painted_metal on its own has a strong vertical corrugation in
    its normal map and streaky colour, which read as planks. Here its colour only shows through
    a broken noise mask over a flat, mottled faded-oxide paint, its normal map is replaced by
    green_metal_rust's (flat sheet with pitting), so rust runs remain but as patches."""
    pm = tex("rusty_painted_metal")
    sm = tex("green_metal_rust")
    m = bpy.data.materials.new("paint")
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.9, 0.9, 0.9)
    L.new(uv.outputs["UV"], mp.inputs["Vector"])
    mp2 = nt.nodes.new("ShaderNodeMapping")
    mp2.inputs["Scale"].default_value = (0.7, 0.7, 0.7)
    mp2.inputs["Rotation"].default_value = (0, 0, 0.6)
    L.new(uv.outputs["UV"], mp2.inputs["Vector"])

    def img(path, vec, noncolor):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        if noncolor:
            t.image.colorspace_settings.name = "Non-Color"
        L.new(vec, t.inputs["Vector"])
        return t.outputs["Color"]

    pcol = img(pm["color"], mp.outputs["Vector"], False)
    prough = img(pm["roughness"], mp.outputs["Vector"], True)
    snorm = img(sm["normal"], mp2.outputs["Vector"], True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nb = _n(nt, "ShaderNodeTexNoise", Scale=2.5, Detail=6.0)
    nd = _n(nt, "ShaderNodeTexNoise", Scale=14.0, Detail=8.0)
    for nn in (nb, nd):
        L.new(tc.outputs["Object"], nn.inputs["Vector"])
    flat = _ramp(nt, nd.outputs["Fac"], tuple(c * t for c, t in zip((0.13, 0.05, 0.032), tint)),
                 tuple(c * t for c, t in zip((0.19, 0.075, 0.048), tint)), 0.35, 0.65)
    mask = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", nb.outputs["Fac"], 0.42), 4.0, clamp=True)
    mask = _math(nt, "ADD", _math(nt, "MULTIPLY", mask, 0.6), 0.25)     # texture shows 25..85 %
    col = _mixc(nt, mask, flat, pcol)
    # cavity grime
    ao = _n(nt, "ShaderNodeAmbientOcclusion", Distance=0.08)
    g = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, ao.outputs["AO"]), 0.5)
    col = _mixc(nt, g, col, (0.03, 0.025, 0.02, 1))
    L.new(col, bsdf.inputs["Base Color"])
    L.new(_math(nt, "MULTIPLY", prough, 1.0), bsdf.inputs["Roughness"])
    nmap = _n(nt, "ShaderNodeNormalMap", Strength=0.7)
    nmap.uv_map = "UVMap"
    L.new(snorm, nmap.inputs["Color"])
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return m


MAT_CACHE = {}


def mat(kind, vary=False):
    """Named material kinds; vary=True gives a new tinted copy for repeated parts."""
    if kind in MAT_CACHE and not vary:
        return MAT_CACHE[kind]
    if kind == "paint":        # faded factory paint over rust (cabinet panels)
        m = paint_material(jitter((1.0, 1.0, 1.0), 0.08))
    elif kind == "tank":
        m = bkit.pbr_material("tank", tex("green_metal_rust"), scale=0.8, tint=(0.85, 0.9, 0.85))
    elif kind == "frame":      # skid, posts, brackets
        m = bkit.pbr_material("frame", tex("rust_coarse_01"), scale=1.2, tint=jitter((0.8, 0.78, 0.76), 0.05))
    elif kind == "pipe":
        m = bkit.pbr_material("pipe", tex("rusty_metal_02"), scale=1.5, tint=(0.36, 0.31, 0.25),
                              roughness_mult=1.15)
    elif kind == "steel":      # dark worn steel: crank, lever, bolts
        m = bkit.pbr_material("steel", tex("rusty_metal_04"), scale=2.0, tint=(0.7, 0.7, 0.7))
    elif kind == "brass":      # dark tarnished brass, verdigris in crevices and joints
        m = brass_material("brass", verd_bias=-0.05)
    elif kind == "brass_rim":  # horn rim: tarnish with small worn bright spots
        m = brass_material("brass_rim", verd_bias=-0.25, worn=1.0)
    elif kind == "brass_inner":  # inside the horn bell: verdigris pooled
        m = brass_material("brass_inner", verd_bias=0.45)
    elif kind == "face":       # yellowed gauge dial
        m = bkit.procedural_material("face", (0.62, 0.56, 0.42), variation=0.18, roughness=0.55,
                                     scale=30, bump=0.05, grime=0.5)
    elif kind == "black":
        m = bkit.procedural_material("black", (0.03, 0.03, 0.03), roughness=0.6, scale=20, bump=0.05)
    elif kind == "rubber":
        m = bkit.procedural_material("rubber", (0.045, 0.043, 0.04), variation=0.3, roughness=0.85,
                                     scale=8, bump=0.25, grime=0.0)
    elif kind == "glass":      # dark murky porthole / lamp glass
        m = bkit.procedural_material("glass", (0.05, 0.075, 0.05), variation=0.4, roughness=0.12,
                                     scale=6, bump=0.02, grime=0.0)
    elif kind == "red":
        m = bkit.procedural_material("red", (0.38, 0.06, 0.045), variation=0.2, roughness=0.5, scale=12, bump=0.1)
    elif kind == "lamp":
        m = bkit.procedural_material("lamp", (0.35, 0.05, 0.03), variation=0.2, roughness=0.15, scale=8, bump=0.0)
    elif kind == "yellow":
        m = bkit.procedural_material("yellow", (0.55, 0.42, 0.08), variation=0.2, roughness=0.5, scale=12, bump=0.1)
    elif kind == "green":
        m = bkit.procedural_material("green", (0.08, 0.25, 0.1), variation=0.2, roughness=0.5, scale=12, bump=0.1)
    elif kind == "wood":       # crank handle grip
        m = bkit.procedural_material("wood", (0.22, 0.13, 0.07), variation=0.25, roughness=0.6, scale=25, bump=0.2)
    else:
        raise KeyError(kind)
    if not vary:
        MAT_CACHE[kind] = m
    return m


# ---------------------------------------------------------------- part helpers

def finish(ob, material, uv=1.0, hard=None):
    bpy.context.view_layer.update()
    if hard:
        bkit.harden(ob, width=hard, segments=1, angle=35)
    bkit.box_uv(ob, size=uv)
    ob.data.materials.append(material)
    PARTS.append(ob)
    return ob


def new_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def orient(direction):
    return Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized()).to_euler()


def box(name, c, s, m, rot=(0, 0, 0), hard=0.004, jit=0.0):
    if jit:
        rot = tuple(r + math.radians(random.uniform(-jit, jit)) for r in rot)
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = s
    bkit.apply_all(ob)
    return finish(ob, m, hard=hard)


def cyl(name, c, r, h, m, rot=(0, 0, 0), seg=20, r2=None, hard=0.003):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=seg, radius=r, depth=h, location=c, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=seg, radius1=r, radius2=r2, depth=h, location=c, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    bkit.apply_all(ob)
    bkit.shade_smooth(ob)
    return finish(ob, m, hard=hard)


def torus(name, c, R, r, m, rot=(0, 0, 0), seg=24, mseg=8):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg,
                                     minor_segments=mseg, location=c, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    bkit.apply_all(ob)
    bkit.shade_smooth(ob)
    return finish(ob, m)


def sphere(name, c, r, m, scale=(1, 1, 1), seg=12, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=r, location=c)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    bkit.apply_all(ob)
    bkit.shade_smooth(ob)
    return finish(ob, m)


def lathe(name, profile, m, loc, seg=32, cap_top=False, cap_bottom=False):
    """Revolve [(r, z)] around Z."""
    verts, faces = [], []
    n = len(profile)
    for i in range(seg):
        a = math.tau * i / seg
        for r, z in profile:
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(seg):
        j = (i + 1) % seg
        for k in range(n - 1):
            faces.append((i * n + k, j * n + k, j * n + k + 1, i * n + k + 1))
    if cap_bottom:
        faces.append(tuple(i * n for i in reversed(range(seg))))
    if cap_top:
        faces.append(tuple(i * n + n - 1 for i in range(seg)))
    ob = new_obj(name, verts, faces)
    ob.location = loc
    bkit.shade_smooth(ob)
    return finish(ob, m)


def sweep(name, pts, radius, m, seg=12, caps=True, open_end=False):
    """Tube along a polyline. radius: float or f(t) with t in 0..1. Parallel-transport frames."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rf = radius if callable(radius) else (lambda t, r=radius: r)
    tans = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tans.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = (up - tans[0] * up.dot(tans[0])).normalized()
    verts, faces = [], []
    for i, (p, t) in enumerate(zip(pts, tans)):
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bin_ = t.cross(nrm)
        r = rf(i / (n - 1))
        for k in range(seg):
            a = math.tau * k / seg
            verts.append(p + (nrm * math.cos(a) + bin_ * math.sin(a)) * r)
    for i in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k2, (i + 1) * seg + k2, (i + 1) * seg + k))
    if caps:
        faces.append(tuple(reversed(range(seg))))
        if not open_end:
            faces.append(tuple((n - 1) * seg + k for k in range(seg)))
    ob = new_obj(name, verts, faces)
    bkit.shade_smooth(ob)
    return finish(ob, m)


def rounded_path(corners, rr=0.08, steps=6):
    """Polyline through corners with each interior corner rounded by a quadratic arc."""
    c = [Vector(p) for p in corners]
    out = [c[0]]
    for i in range(1, len(c) - 1):
        A, P, B = c[i - 1], c[i], c[i + 1]
        r = min(rr, (A - P).length * 0.45, (B - P).length * 0.45)
        pin = P + (A - P).normalized() * r
        pout = P + (B - P).normalized() * r
        for s in range(steps + 1):
            t = s / steps
            out.append(pin * (1 - t) ** 2 + P * 2 * (1 - t) * t + pout * t * t)
    out.append(c[-1])
    # densify straight runs a little so the UVs/normals behave
    dense = [out[0]]
    for p in out[1:]:
        d = (p - dense[-1]).length
        k = max(1, int(d / 0.25))
        for s in range(1, k + 1):
            dense.append(dense[-1].lerp(p, s / k) if s < k else p)
    return dense


def bezier(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = map(Vector, (p0, p1, p2, p3))
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / (n - 1) for i in range(n))]


RIVETS = []   # (position, outward normal, radius)


def rivet(p, n, r=0.007):
    RIVETS.append((Vector(p), Vector(n), r))


def build_rivets():
    bm = bmesh.new()
    for p, n, r in RIVETS:
        ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        M = (Matrix.Translation(p) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4()
             @ Matrix.Diagonal((r, r, r * 0.55, 1)))
        bmesh.ops.transform(bm, matrix=M, verts=ret["verts"])
    me = bpy.data.meshes.new("rivets")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("rivets", me)
    bpy.context.scene.collection.objects.link(ob)
    bkit.shade_smooth(ob)
    finish(ob, mat("steel"), uv=0.2)


# ---------------------------------------------------------------- layout (metres)
CX = -0.05                       # cabinet centre x
X0, X1 = CX - 0.5, CX + 0.5      # cabinet sides
Y0, Y1 = -0.35, 0.35             # front / back
ZB, ZT = 0.16, 1.25              # cabinet bottom / top (skid below)
TX, TY = CX - 0.12, 0.06         # tank centre
TR = 0.27                        # tank radius
TZ0, TZ1 = 1.30, 1.88

# ---------------------------------------------------------------- skid base (I-beams)
for yi, y in enumerate((-0.31, 0.31)):
    box(f"rail_tf{yi}", (CX + 0.03, y, 0.1525), (1.5, 0.1, 0.015), mat("frame"), hard=0.002)
    box(f"rail_bf{yi}", (CX + 0.03, y, 0.0275), (1.5, 0.1, 0.015), mat("frame"), hard=0.002)
    box(f"rail_web{yi}", (CX + 0.03, y, 0.09), (1.5, 0.012, 0.11), mat("frame"), hard=0.0)
for xi, x in enumerate((CX - 0.6, CX + 0.0, CX + 0.66)):
    box(f"cross{xi}", (x, 0, 0.09), (0.08, 0.52, 0.1), mat("frame"), hard=0.003)
for fx in (CX - 0.66, CX + 0.72):
    for fy in (-0.31, 0.31):
        box("foot", (fx, fy, 0.01), (0.17, 0.17, 0.02), mat("steel"), hard=0.003, jit=1.5)
        for bx in (-0.055, 0.055):
            cyl("foot_bolt", (fx + bx, fy, 0.026), 0.013, 0.014, mat("steel"), seg=6, hard=0.0015)

# ---------------------------------------------------------------- cabinet
box("sill", (CX, 0, ZB + 0.015), (1.0, 0.7, 0.03), mat("frame"))
for px in (X0 + 0.025, X1 - 0.025):
    for py in (Y0 + 0.025, Y1 - 0.025):
        box("post", (px, py, (ZB + ZT) / 2), (0.05, 0.05, ZT - ZB), mat("frame"), hard=0.004)
        for z in [ZB + 0.08 + i * 0.105 for i in range(10)]:
            rivet((px, Y0 if py < 0 else Y1, z), (0, -1 if py < 0 else 1, 0))
            rivet((X0 if px < CX else X1, py, z), (-1 if px < CX else 1, 0, 0))

PW = X1 - X0 - 0.11      # panel width between posts, with 5 mm gaps
# front lower access door
DZ0, DZ1 = ZB + 0.04, 0.78
box("door", (CX, Y0 + 0.006, (DZ0 + DZ1) / 2), (PW, 0.012, DZ1 - DZ0), mat("paint", True), jit=0.3)
for z in (DZ0 + 0.08, DZ1 - 0.08):
    cyl("hinge", (X0 + 0.055, Y0 - 0.006, z), 0.012, 0.07, mat("steel"), seg=10)
box("handle", (X1 - 0.12, Y0 - 0.03, 0.5), (0.025, 0.018, 0.16), mat("steel"))
for z in (0.44, 0.56):
    box("handle_post", (X1 - 0.12, Y0 - 0.012, z), (0.02, 0.03, 0.02), mat("steel"))
# louvre vent in the door
box("vent_frame", (CX - 0.1, Y0 - 0.002, 0.34), (0.42, 0.01, 0.17), mat("black"), hard=0.002)
for i in range(6):
    box("louvre", (CX - 0.1, Y0 - 0.012, 0.275 + i * 0.026), (0.4, 0.004, 0.03),
        mat("paint"), rot=(math.radians(-40), 0, 0), hard=0.0, jit=1.5)
# divider band
box("band", (CX, Y0 - 0.004, 0.8), (1.0, 0.02, 0.04), mat("frame"))
# upper control panel (proud by 1 cm)
CPY = Y0 - 0.012                     # control panel front face
box("ctrl_panel", (CX, Y0 - 0.006, 1.02), (PW, 0.012, 0.4), mat("paint", True))
for x in (X0 + 0.07, X1 - 0.07):
    for z in (0.85, 1.19):
        rivet((x, CPY, z), (0, -1, 0), 0.006)
# sides and back
box("side_L", (X0 + 0.006, 0, (ZB + ZT) / 2), (0.012, 0.6, ZT - ZB - 0.04), mat("paint", True), jit=0.3)
box("side_R", (X1 - 0.006, 0, (ZB + ZT) / 2), (0.012, 0.6, ZT - ZB - 0.04), mat("paint", True), jit=0.3)
box("back", (CX, Y1 - 0.006, (ZB + ZT) / 2), (PW, 0.012, ZT - ZB - 0.04), mat("paint", True))
# side vents (right)
for i in range(5):
    box("side_louvre", (X1 + 0.004, 0.12, 0.35 + i * 0.03), (0.004, 0.25, 0.032),
        mat("paint"), rot=(0, math.radians(40), 0), hard=0.0, jit=1.5)
# lid
box("lid", (CX, 0, ZT + 0.0175), (1.06, 0.76, 0.035), mat("frame"), hard=0.005)
for i in range(9):
    x = X0 + 0.04 + i * (X1 - X0 - 0.08) / 8
    rivet((x, -0.38, ZT + 0.0175), (0, -1, 0), 0.006)

# ---------------------------------------------------------------- control panel hardware
gauges = [(CX - 0.30, 1.1, 0.068), (CX - 0.08, 1.1, 0.068), (CX + 0.12, 1.13, 0.046)]
for gi, (gx, gz, gr) in enumerate(gauges):
    cyl("gauge_case", (gx, CPY - 0.02, gz), gr, 0.04, mat("steel"), rot=(math.pi / 2, 0, 0), seg=24)
    torus("gauge_bezel", (gx, CPY - 0.04, gz), gr, 0.008, mat("brass"), rot=(math.pi / 2, 0, 0))
    cyl("gauge_face", (gx, CPY - 0.041, gz), gr * 0.93, 0.002, mat("face"), rot=(math.pi / 2, 0, 0),
        seg=24, hard=0.0)
    # tick ring: 9 small marks around the dial
    for k in range(9):
        a = math.radians(-135 + k * 270 / 8)
        d = Vector((math.sin(a), 0, math.cos(a)))
        c = Vector((gx, CPY - 0.0425, gz)) + d * gr * 0.78
        box("tick", c, (0.003, 0.001, gr * 0.14), mat("black"), rot=(0, a, 0), hard=0.0)
    ang = math.radians(random.uniform(-150, -120) if gi != 1 else 100)   # needles dead / one stuck high
    d = Vector((math.sin(ang), 0, math.cos(ang)))
    L = gr * 0.75
    box("needle", Vector((gx, CPY - 0.044, gz)) + d * L * 0.4, (0.004, 0.002, L), mat("black"),
        rot=(0, ang, 0), hard=0.0)
    cyl("pivot", (gx, CPY - 0.045, gz), 0.006, 0.004, mat("brass"), rot=(math.pi / 2, 0, 0), seg=8, hard=0.0)

# nameplate + buttons + warning lamp
box("nameplate", (CX - 0.19, CPY - 0.003, 0.96), (0.32, 0.006, 0.07), mat("brass"), hard=0.002, jit=0.8)
for x in (CX - 0.34, CX - 0.04):
    rivet((x, CPY - 0.006, 0.96), (0, -1, 0), 0.005)
for i, col in enumerate(("red", "green", "yellow", "black")):
    x = CX - 0.32 + i * 0.1
    cyl("btn_collar", (x, CPY - 0.006, 0.865), 0.026, 0.012, mat("steel"), rot=(math.pi / 2, 0, 0), seg=16)
    depth = 0.03 if i != 2 else 0.015      # one button stuck in
    cyl("btn", (x, CPY - 0.012 - depth / 2, 0.865), 0.018, depth, mat(col), rot=(math.pi / 2, 0, 0), seg=16)
cyl("lamp_base", (CX + 0.12, CPY - 0.01, 0.97), 0.03, 0.02, mat("steel"), rot=(math.pi / 2, 0, 0), seg=16)
sphere("lamp", (CX + 0.12, CPY - 0.022, 0.97), 0.025, mat("lamp"), scale=(1, 0.8, 1))
# throw lever
LX = CX + 0.34
box("lever_plate", (LX, CPY - 0.008, 1.0), (0.1, 0.016, 0.24), mat("steel"))
box("lever_slot", (LX, CPY - 0.0165, 1.0), (0.02, 0.002, 0.17), mat("black"), hard=0.0)
for z in (0.9, 1.1):
    for x in (LX - 0.035, LX + 0.035):
        rivet((x, CPY - 0.016, z), (0, -1, 0), 0.006)
pivot = Vector((LX, CPY - 0.03, 0.95))
cyl("lever_pivot", pivot, 0.022, 0.05, mat("steel"), rot=(0, math.pi / 2, 0), seg=12)
ldir = Vector((0, -math.sin(math.radians(30)), math.cos(math.radians(30))))
cyl("lever_arm", pivot + ldir * 0.13, 0.011, 0.26, mat("steel"), rot=orient(ldir), seg=10)
sphere("lever_knob", pivot + ldir * 0.27, 0.032, mat("red"))

# ---------------------------------------------------------------- tank on the lid
cyl("tank_base", (TX, TY, ZT + 0.055), TR + 0.04, 0.04, mat("frame"), seg=32)
lathe("tank", [(TR, ZT + 0.07), (TR, TZ1), (TR * 0.97, TZ1 + 0.04), (TR * 0.86, TZ1 + 0.085),
               (TR * 0.66, TZ1 + 0.12), (TR * 0.4, TZ1 + 0.14), (0.06, TZ1 + 0.15)],
      mat("tank"), (TX, TY, 0), seg=32, cap_top=True)
for z in (1.47, 1.74):
    cyl("tank_hoop", (TX, TY, z), TR + 0.008, 0.035, mat("frame"), seg=32)
cyl("tank_flange", (TX, TY, TZ1), TR + 0.016, 0.025, mat("frame"), seg=32)
for k in range(24):
    a = math.tau * k / 24
    n = Vector((math.cos(a), math.sin(a), 0))
    rivet(Vector((TX, TY, TZ1)) + n * (TR + 0.016), n, 0.006)
    rivet(Vector((TX, TY, ZT + 0.055)) + n * (TR + 0.04), n, 0.007)
# vertical seam with rivets
seam = Vector((math.cos(math.radians(-50)), math.sin(math.radians(-50)), 0))
box("tank_seam", Vector((TX, TY, (TZ0 + TZ1) / 2 + 0.03)) + seam * (TR + 0.002), (0.04, 0.006, TZ1 - TZ0 - 0.08),
    mat("tank"), rot=(0, 0, math.radians(-50 + 90)), hard=0.002)
for i in range(8):
    rivet(Vector((TX, TY, TZ0 + 0.06 + i * 0.07)) + seam * (TR + 0.005), seam, 0.005)
# porthole facing front
PH = Vector((TX, TY - TR, 1.6))
torus("port_bezel", PH + Vector((0, -0.01, 0)), 0.075, 0.016, mat("brass"), rot=(math.pi / 2, 0, 0))
cyl("port_glass", PH + Vector((0, 0.0, 0)), 0.075, 0.03, mat("glass"), rot=(math.pi / 2, 0, 0), seg=24, hard=0.0)
for k in range(6):
    a = math.tau * k / 6
    rivet(PH + Vector((math.cos(a) * 0.1, -0.012, math.sin(a) * 0.1)), (0, -1, 0), 0.007)

# ---------------------------------------------------------------- brass horn (laughter collector)
HTOP = TZ1 + 0.15
horn_path = bezier((TX, TY, HTOP - 0.03), (TX, TY, HTOP + 0.25), (TX, TY - 0.08, HTOP + 0.36),
                   (TX, TY - 0.47, HTOP + 0.48), 18)
MOUTH = 0.29


def horn_r(t):
    if t < 0.3:
        return 0.045
    u = (t - 0.3) / 0.7
    return 0.045 + (MOUTH - 0.045) * u ** 2.8


horn = sweep("horn", horn_path, horn_r, mat("brass"), seg=16, caps=False)
sol = horn.modifiers.new("Solidify", "SOLIDIFY")
sol.thickness = 0.004
sol.offset = -1
bkit.apply_all(horn)
# faces whose normal points toward the horn axis are the inside of the bell -> verdigris material
horn.data.materials.append(mat("brass_inner"))
for poly in horn.data.polygons:
    c = poly.center
    near = min(horn_path, key=lambda q: (q - c).length)
    if poly.normal.dot(c - near) < 0:
        poly.material_index = 1
end_dir = (horn_path[-1] - horn_path[-2]).normalized()
torus("horn_rim", horn_path[-1], MOUTH + 0.002, 0.009, mat("brass_rim"), rot=orient(end_dir), seg=24, mseg=6)
cyl("horn_collar", (TX, TY, HTOP + 0.02), 0.06, 0.05, mat("brass"), seg=16)
# a support stay from the tank dome to the horn bell
stay_top = horn_path[13] + Vector((0, 0.02, -horn_r(13 / 17) + 0.01))
stay_bot = Vector((TX, TY - 0.17, TZ1 + 0.09))
sweep("horn_stay", [stay_bot, stay_bot.lerp(stay_top, 0.5), stay_top], 0.008, mat("steel"), seg=8)

# ---------------------------------------------------------------- pipe run to the dispenser (right)
DX, DY = X1 + 0.19, -0.14           # nozzle above the jar cradle
pipe_pts = rounded_path([(TX + TR - 0.01, TY, 1.56), (DX, TY, 1.56), (DX, TY, 1.2),
                         (DX, DY, 1.12), (DX, DY, 0.96)], rr=0.09)
sweep("pipe_main", pipe_pts, 0.026, mat("pipe"), seg=14)
cyl("pipe_flange_tank", (TX + TR + 0.01, TY, 1.56), 0.045, 0.02, mat("frame"), rot=(0, math.pi / 2, 0), seg=16)
for z in (1.38,):
    cyl("pipe_coupling", (DX, TY, z), 0.036, 0.05, mat("steel"), seg=14)
# valve with handwheel on the vertical drop
VZ = 1.3
cyl("valve_body", (DX, TY, VZ), 0.045, 0.09, mat("brass"), seg=14)
cyl("valve_stem", (DX + 0.06, TY, VZ), 0.008, 0.08, mat("steel"), rot=(0, math.pi / 2, 0), seg=8)
torus("valve_wheel", (DX + 0.1, TY, VZ), 0.06, 0.008, mat("red"), rot=(0, math.pi / 2, 0), seg=20, mseg=6)
for k in range(3):
    a = math.tau * k / 3 + 0.4
    d = Vector((0, math.cos(a), math.sin(a)))
    cyl("valve_spoke", Vector((DX + 0.1, TY, VZ)) + d * 0.03, 0.005, 0.06, mat("red"), rot=orient(d), seg=6, hard=0.0)
# wall bracket holding the pipe to the cabinet side
box("pipe_bracket", ((X1 + DX) / 2, TY, 1.1), (DX - X1, 0.04, 0.012), mat("frame"))
torus("pipe_clamp", (DX, TY + 0.0, 1.1), 0.03, 0.006, mat("frame"), seg=14, mseg=6)
# nozzle
cyl("nozzle", (DX, DY, 0.92), 0.028, 0.08, mat("brass"), r2=0.012, rot=(math.pi, 0, 0), seg=14)
# jar cradle shelf with brackets
SZ = 0.6
box("shelf", (DX - 0.02, DY + 0.02, SZ), (0.34, 0.32, 0.015), mat("frame"), jit=0.6)
for y in (DY - 0.1, DY + 0.12):
    box("shelf_brace", (X1 + 0.09, y, SZ - 0.09), (0.012, 0.03, 0.24), mat("frame"),
        rot=(0, math.radians(-42), 0))
torus("cradle_ring", (DX, DY, SZ + 0.05), 0.075, 0.007, mat("steel"), seg=20, mseg=6)
for k in range(3):
    a = math.tau * k / 3
    cyl("cradle_post", (DX + math.cos(a) * 0.075, DY + math.sin(a) * 0.075, SZ + 0.025), 0.006, 0.05,
        mat("steel"), seg=6, hard=0.0)
# drip tray grime: a dark ring where jars stood
cyl("drip_stain", (DX, DY, SZ + 0.008), 0.065, 0.002, mat("black"), seg=20, hard=0.0)

# return pipe from the tank into the lid (left)
sweep("pipe_return", rounded_path([(TX - TR + 0.01, TY, 1.44), (X0 + 0.1, TY, 1.44), (X0 + 0.1, TY, ZT + 0.03)],
                                  rr=0.07), 0.022, mat("pipe"), seg=12)
cyl("pipe_return_flange", (X0 + 0.1, TY, ZT + 0.045), 0.04, 0.02, mat("frame"), seg=14)

# electrical conduit from control panel to tank
sweep("conduit", rounded_path([(CX + 0.3, Y0 + 0.08, ZT + 0.03), (CX + 0.3, Y0 + 0.08, 1.36),
                               (TX + 0.12, TY - 0.23, 1.36)], rr=0.05), 0.011, mat("steel"), seg=8)
box("junction_box", (TX + 0.12, TY - 0.24, 1.36), (0.08, 0.04, 0.08), mat("paint"), rot=(0, 0, math.radians(-25)))

# ---------------------------------------------------------------- hand crank (left side)
CC = Vector((X0 - 0.01, 0.02, 0.72))
cyl("crank_hub_plate", CC + Vector((-0.005, 0, 0)), 0.07, 0.012, mat("steel"), rot=(0, math.pi / 2, 0), seg=16)
cyl("crank_shaft", CC + Vector((-0.045, 0, 0)), 0.02, 0.08, mat("steel"), rot=(0, math.pi / 2, 0), seg=12)
WC = CC + Vector((-0.08, 0, 0))
torus("crank_rim", WC, 0.2, 0.013, mat("steel"), rot=(0, math.pi / 2, 0), seg=20, mseg=6)
cyl("crank_hub", WC, 0.035, 0.04, mat("steel"), rot=(0, math.pi / 2, 0), seg=12)
for k in range(5):
    a = math.tau * k / 5 + 0.3
    d = Vector((0, math.cos(a), math.sin(a)))
    box("crank_spoke", WC + d * 0.11, (0.012, 0.016, 0.17), mat("steel"),
        rot=orient(d), hard=0.002)
hp = WC + Vector((0, math.cos(1.0) * 0.2, math.sin(1.0) * 0.2))
cyl("crank_handle_pin", hp + Vector((-0.03, 0, 0)), 0.008, 0.06, mat("steel"), rot=(0, math.pi / 2, 0), seg=8)
cyl("crank_handle", hp + Vector((-0.09, 0, 0)), 0.018, 0.1, mat("wood"), rot=(0, math.pi / 2, 0), seg=12)

# ---------------------------------------------------------------- cut rubber hose drooping to the floor
hose = rounded_path([(X0 + 0.0, 0.22, 0.46), (X0 - 0.14, 0.24, 0.42), (X0 - 0.24, 0.27, 0.04),
                     (X0 - 0.3, 0.1, 0.022), (X0 - 0.38, -0.12, 0.022)], rr=0.12, steps=5)
sweep("hose", hose, 0.022, mat("rubber"), seg=8)
cyl("hose_fitting", (X0 - 0.01, 0.22, 0.46), 0.032, 0.04, mat("brass"), rot=(0, math.pi / 2, 0), seg=12)

build_rivets()

# ---------------------------------------------------------------- preview (pre-bake)
bkit.light_studio()
bkit.render_views(PREVIEW, size=640, samples=40)
if PREVIEW_ONLY:
    bkit.report()
    sys.exit(0)

# ---------------------------------------------------------------- game-ready
obj = bkit.join(PARTS, ASSET)
print("pre-decimate tris", bkit.tri_count(obj))
# hard-surface: planar decimation first keeps flat panels clean, then collapse to budget
dm = obj.modifiers.new("Planar", "DECIMATE")
dm.decimate_type = "DISSOLVE"
dm.angle_limit = math.radians(2)
dm.delimit = {"MATERIAL", "UV"}
bkit.apply_all(obj)
print("after planar", bkit.tri_count(obj))
bkit.decimate(obj, TRI_BUDGET)
bkit.origin_to_bottom(obj)


# Cycles' DIFFUSE colour pass is black on metallic=1 surfaces, which turned the brass horn black
# in the baked texture. Without touching bkit, wrap its bake call so the DIFFUSE pass runs with
# metallic temporarily forced to 0 (the metallic map is still baked from the real values).
class _Proxy:
    def __init__(self, real, over):
        self._real, self._over = real, over

    def __getattr__(self, n):
        return self._over[n] if n in self._over else getattr(self._real, n)


def _bake(type, **kw):
    if type != "DIFFUSE":
        return bpy.ops.object.bake(type=type, **kw)
    saved = []
    for m in obj.data.materials:
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        sock = b.inputs["Metallic"]
        src = sock.links[0].from_socket if sock.links else None
        if src:
            m.node_tree.links.remove(sock.links[0])
        saved.append((m, sock, src, sock.default_value))
        sock.default_value = 0.0
    try:
        return bpy.ops.object.bake(type=type, **kw)
    finally:
        for m, sock, src, dv in saved:
            sock.default_value = dv
            if src:
                m.node_tree.links.new(src, sock)


bkit.bpy = _Proxy(bpy, {"ops": _Proxy(bpy.ops, {"object": _Proxy(bpy.ops.object, {"bake": _bake})})})
try:
    bkit.bake_to_textures(obj, BAKE_DIR, size=BAKE_SIZE)
finally:
    bkit.bpy = bpy
bkit.report([obj])
bkit.export_glb(GLB, [obj], image_format="JPEG")
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bkit.render_views(BAKED_PREVIEW, size=640, samples=40)
print("DONE", GLB)
