"""Stitch Mama (縫線娘娘) - the park's costume seamstress, sewn onto her own dress form
and hung from a ceiling rail in the sewing room. Porcelain doll head skewered on the hanger
rod, tailor's shears for hands, a crinoline cage hung with tattered strips and the little
Grinny costumes she never finished."""
import math
import random
import bpy
from mathutils import Vector
from lib import (Skel, Mat, prim, seg, empty, apply_mods, displace, boolean, orient, bevel, smooth, loft,
                 link_obj, mat_plush, mat_painted_wood, mat_brass, mat_rust, mat_simple, mat_stripes,
                 mat_eyeball, R)

FRAME = dict(height=4.4, center=(0, 0, 2.3))
SHOTS = [
    ("hero", "horror", (-1.9, -5.6, 1.5), (0, -0.2, 2.45), 30),
    ("studio", "studio", (3.6, -6.2, 2.6), (0, 0, 2.3), 34),
    ("face", "horror", (-0.75, -1.9, 3.05), (0, -0.25, 3.02), 45),
]
UP = Vector((0, 0, 1))


# ---------------------------------------------------------------- materials
def mat_canvas(name="DressCanvas"):
    """Old dress-form linen over papier-mache: yellowed, water-stained, hand-soiled."""
    M = Mat(name)
    n = M.noise(3.5, 10, 0.6, distortion=0.3)
    col = M.ramp(n, [(0.25, "#4e4232"), (0.5, "#7e6e56"), (0.75, "#9a8a6c")])
    tide = M.ramp(M.noise(1.2, 4, 0.5, distortion=1.5), [(0.55, "#ffffff"), (0.6, "#8a6a48"), (0.66, "#ffffff")])
    col = M.mix(0.7, col, tide, "MULTIPLY")
    grime = M.ramp(M.noise(1.8, 8, 0.65), [(0.45, "#ffffff"), (0.8, "#4a3424")])
    col = M.mix(1.0, col, grime, "MULTIPLY")
    rust = M.ramp(M.noise(9, 6, 0.6), [(0.72, "#ffffff"), (0.8, "#7a4a28")])
    col = M.mix(1.0, col, rust, "MULTIPLY")
    weave = M.math(M.wave(420, "X"), M.wave(420, "Z"), "ADD")
    M.set(color=col, rough=0.92, sheen=0.35, sheen_rough=0.5)
    M.bump(M.math(weave, M.noise(30, 6, 0.7), "ADD"), 0.18, 0.004)
    return M.m


def mat_porcelain(name="Porcelain"):
    """Bisque doll porcelain: glazed, crazed with fine cracks, dirt settled in the cracks."""
    M = Mat(name)
    n = M.noise(4, 8, 0.55)
    col = M.ramp(n, [(0.3, "#b8ac98"), (0.55, "#cfc5b2"), (0.8, "#ddd4c4")])
    craze = M.voronoi(26, "DISTANCE_TO_EDGE")
    craze_mask = M.ramp(M.noise(2.2, 6, 0.6), [(0.5, "#000000"), (0.62, "#ffffff")])
    lines = M.ramp(craze, [(0.0, "#2a2018"), (0.025, "#ffffff")])
    lines = M.mix(craze_mask, (1, 1, 1), lines)
    col = M.mix(1.0, col, lines, "MULTIPLY")
    grime = M.ramp(M.noise(3, 8, 0.65), [(0.45, "#ffffff"), (0.8, "#5a4434")])
    col = M.mix(1.0, col, grime, "MULTIPLY")
    # decades of dust settled into every crease and around the features
    ao = M.nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.03
    crease = M.ramp(ao.outputs["AO"], [(0.35, "#3a2a1e"), (0.9, "#ffffff")])
    col = M.mix(1.0, col, crease, "MULTIPLY")
    streak = M.ramp(M.noise(1.5, 6, 0.6, distortion=2.0), [(0.55, "#ffffff"), (0.7, "#8a7058")])
    col = M.mix(0.8, col, streak, "MULTIPLY")
    M.set(color=col, rough=0.32, coat=0.6, coat_rough=0.12, sss=0.06, sss_radius=(1, 0.8, 0.6), sss_scale=0.01)
    M.bump(M.math(craze, M.noise(60, 4, 0.6), "ADD"), 0.08, 0.003)
    return M.m


def mat_blush(name="DollBlush"):
    M = Mat(name)
    n = M.noise(6, 6, 0.6)
    col = M.ramp(n, [(0.3, "#b07a72"), (0.7, "#d8a89a")])
    M.set(color=col, rough=0.3, coat=0.8, coat_rough=0.1)
    return M.m


def mat_steel(name="ShearSteel"):
    """Forged tailor-shear steel: polished edge, pitted, rust blooms and old dark stains."""
    M = Mat(name)
    n = M.noise(6, 10, 0.7, distortion=0.6)
    rust_mask = M.ramp(M.noise(3.5, 10, 0.7, distortion=0.8), [(0.55, "#000000"), (0.66, "#ffffff")])
    steel = M.ramp(M.noise(40, 6, 0.6), [(0.3, "#5a5c5e"), (0.7, "#9a9c9e")])
    rust = M.ramp(n, [(0.3, "#2a140a"), (0.6, "#6a3216"), (0.8, "#8a4a22")])
    col = M.mix(rust_mask, steel, rust)
    stain = M.ramp(M.noise(2.5, 6, 0.6), [(0.6, "#ffffff"), (0.7, "#3a0a08")])
    col = M.mix(1.0, col, stain, "MULTIPLY")
    metal = M.ramp(rust_mask, [(0.0, "#ffffff"), (1.0, "#000000")])
    rough = M.ramp(rust_mask, [(0.0, "#4a4a4a"), (1.0, "#e0e0e0")])
    M.set(color=col, metal=metal, rough=rough)
    M.bump(M.math(n, M.noise(120, 4, 0.7), "ADD"), 0.25, 0.004)
    return M.m


def mat_tape(name="MeasureTape"):
    """Cloth measuring tape: faded yellow with black tick marks."""
    M = Mat(name)
    ticks = M.ramp(M.wave(140, "Z"), [(0.0, "#1a1408"), (0.12, "#c8a848")], constant=True)
    dirt = M.ramp(M.noise(3, 6, 0.6), [(0.4, "#ffffff"), (0.8, "#6a5434")])
    M.set(color=M.mix(1.0, ticks, dirt, "MULTIPLY"), rough=0.85, sheen=0.3)
    return M.m


def mat_paper(name="PatternPaper"):
    M = Mat(name)
    n = M.noise(5, 8, 0.6)
    col = M.ramp(n, [(0.3, "#8a7a5a"), (0.6, "#c4b48e"), (0.85, "#d8caa4")])
    M.set(color=col, rough=0.9, sss=0.1, sss_radius=(1, 0.9, 0.7), sss_scale=0.005)
    M.bump(M.noise(14, 6, 0.6), 0.3, 0.005)
    return M.m


def mat_hair(name="DollHair"):
    M = Mat(name)
    combed = M.wave(260, "X", distortion=4.0)
    n = M.math(combed, M.noise(60, 4, 0.6), "ADD")
    col = M.ramp(n, [(0.3, "#120a06"), (0.6, "#2a1a10"), (0.9, "#3e2a1c")])
    grey = M.ramp(M.math(M.wave(300, "X", distortion=6.0), M.noise(4, 4, 0.5), "MULTIPLY"),
                  [(0.55, "#000000"), (0.62, "#ffffff")])
    col = M.mix(grey, col, (0.42, 0.4, 0.37))
    M.set(color=col, rough=0.42, sheen=0.7, sheen_rough=0.3, coat=0.25, coat_rough=0.25)
    M.bump(combed, 0.25, 0.002)
    return M.m


# ---------------------------------------------------------------- scanned textures (Poly Haven, CC0)
def _scans():
    """Real scanned texture sets; None when offline (the procedural materials stay)."""
    try:
        import sys
        sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
        import bkit
        return bkit
    except Exception as ex:  # noqa: BLE001
        print("no scanned textures:", ex)
        return None


def overlay_scan(mat, maps, scale, gain=1.6, normal_strength=0.6):
    """Multiply a scanned colour map over a procedural material and feed its normal map
    into the material's bump node, so the aging/stains stay and the weave becomes real."""
    nt = mat.node_tree
    N, Lk = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    Lk.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(path, non_color):
        t = N.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        if non_color:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"
        t.projection_blend = 0.3
        Lk.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t

    base_in = bsdf.inputs["Base Color"]
    src = base_in.links[0].from_socket if base_in.is_linked else None
    gn = N.new("ShaderNodeMath")
    gn.operation = "MULTIPLY"
    gn.inputs[1].default_value = gain
    col = img(maps["color"], False)
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if src is not None:
        Lk.new(src, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = base_in.default_value
    # brighten the scan around 1.0 so it adds texture without darkening the stains twice
    bw = N.new("ShaderNodeRGBToBW")
    Lk.new(col.outputs["Color"], bw.inputs["Color"])
    Lk.new(bw.outputs["Val"], gn.inputs[0])
    Lk.new(gn.outputs[0], mix.inputs["B"])
    Lk.new(mix.outputs["Result"], base_in)
    if "normal" in maps:
        nm = N.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal_strength
        nm.space = "OBJECT" if False else "TANGENT"
        Lk.new(img(maps["normal"], True).outputs["Color"], nm.inputs["Color"])
        bumps = [n for n in N if n.type == "BUMP"]
        if bumps:
            Lk.new(nm.outputs["Normal"], bumps[0].inputs["Normal"])
        else:
            Lk.new(nm.outputs["Normal"], bsdf.inputs["Normal"])


def apply_scans(root):
    bk = _scans()
    if not bk:
        return
    try:
        rust_maps = bk.polyhaven_texture("rusty_metal_02", "2k")
        linen_maps = bk.polyhaven_texture("rough_linen", "2k")
        velvet_maps = bk.polyhaven_texture("velour_velvet", "2k")
        leather_maps = bk.polyhaven_texture("brown_leather", "1k")
    except Exception as ex:  # noqa: BLE001
        print("scan download failed:", ex)
        return
    rust = bk.pbr_material("RustScan", rust_maps, scale=1.2, coords="BOX")
    leather = bk.pbr_material("LeatherScan", leather_maps, scale=6, tint=(0.35, 0.25, 0.2), coords="BOX")
    overlay_scan(bpy.data.materials["DressCanvas"], linen_maps, 4.0)
    overlay_scan(bpy.data.materials["SeamTape"], linen_maps, 8.0)
    overlay_scan(bpy.data.materials["OldVelvet"], velvet_maps, 5.0, gain=1.4)
    overlay_scan(bpy.data.materials["FadedRose"], linen_maps, 6.0)
    overlay_scan(bpy.data.materials["DustyBlue"], linen_maps, 6.0)
    bpy.context.view_layer.update()
    for o in list(bpy.data.objects):
        if o.type != "MESH" or not o.data.materials:
            continue
        names = [m.name if m else "" for m in o.data.materials]
        if "RustIron" in names or "Leather" in names:
            # object-space projection needs real-world scale baked into the mesh
            mw = o.matrix_world.copy()
            par = o.parent
            o.parent = None
            o.matrix_world = mw
            o.data = o.data.copy() if o.data.users > 1 else o.data
            o.data.transform(o.matrix_basis)
            o.matrix_basis.identity()
            o.parent = par
            o.matrix_parent_inverse = par.matrix_world.inverted() if par else o.matrix_parent_inverse
            for i, nm in enumerate(names):
                if nm == "RustIron":
                    o.data.materials[i] = rust
                elif nm == "Leather":
                    o.data.materials[i] = leather


# ---------------------------------------------------------------- helpers
def ell_lathe(name, profile, sy, segs=64, m=None, parent=None):
    """Revolve [(r, z), ...] around Z, squashed to sy along Y; closed at both ends."""
    verts, faces = [], []
    n = len(profile)
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for r, z in profile:
            verts.append((r * math.cos(a), r * math.sin(a) * sy, z))
    for i in range(segs):
        j = (i + 1) % segs
        for k in range(n - 1):
            faces.append((i * n + k, i * n + k + 1, j * n + k + 1, j * n + k))
    bot = len(verts)
    verts.append((0, 0, profile[0][1]))
    top = len(verts)
    verts.append((0, 0, profile[-1][1]))
    for i in range(segs):
        j = (i + 1) % segs
        faces.append((bot, j * n, i * n))
        faces.append((top, i * n + n - 1, j * n + n - 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.validate()
    o = link_obj(bpy.data.objects.new(name, me))
    o.parent = parent
    if m:
        me.materials.append(m)
    return smooth(o)


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


def onto(obj, center, direction, dist=2.0):
    d = Vector(direction).normalized()
    return hit(obj, Vector(center) + d * dist, -d)


def ribbon(name, path, width, thick, m, parent, twist_side=(1, 0, 0)):
    """Flat strip (tape, cloth strip) along a path."""
    return loft(name, path, [(width, thick, 0)] * len(path), side=twist_side, segs=6, m=m, parent=parent)


def cord(name, pts, r, m, parent):
    S = Skel()
    S.chain(None, [(p, r) for p in pts])
    return S.build(name, m, subdiv=1, parent=parent)


def droop(a, b, sag, n=10):
    """Points of a hanging thread from a to b."""
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, t) - UP * sag * 4 * t * (1 - t) for t in (i / (n - 1) for i in range(n))]


def pin(name, at, normal, m_head, m_steel, parent, length=0.045, head=0.007):
    d = (Vector(normal) + Vector((random.uniform(-.4, .4), random.uniform(-.4, .4), random.uniform(-.2, .4)))).normalized()
    tip = Vector(at) - d * length * 0.55
    end = Vector(at) + d * length * 0.45
    seg(name + "Shaft", tip, end, 0.0011, m_steel, parent, verts=6)
    prim("sphere", name + "Head", end, (head, head, head), m=m_head, parent=parent, segments=12, ring_count=8)


# ---------------------------------------------------------------- build
def build():
    random.seed(23)
    canvas = mat_canvas()
    porcelain = mat_porcelain()
    blush = mat_blush()
    steel = mat_steel()
    rust = mat_rust()
    brass = mat_brass()
    wood = mat_painted_wood("JointWood", "#b8a688", trim="#5a4a38")
    spool_wood = mat_painted_wood("SpoolWood", "#8a6a44", trim="#4a3020")
    thread_red = mat_simple("RedThread", "#6a080c", 0.65, sheen=0.6, sheen_rough=0.3)
    thread_blk = mat_simple("BlackThread", "#0e0806", 0.7, sheen=0.4)
    tape = mat_tape()
    paper = mat_paper()
    hair = mat_hair()
    cavity = mat_simple("DressCavity", "#070404", 0.95)
    stuffing = mat_plush("HorseHair", "#3a2c20", "#1a120c", "#5a4632", stain="#120c08", scale=14)
    eyeball = mat_eyeball("DollEyeGlass")
    iris = mat_simple("DollIris", "#3a4a5a", 0.08, coat=1)
    pupil = mat_simple("DollPupil", "#020202", 0.05, coat=1)
    lens = mat_simple("LoupeLens", "#ffb860", 0.05, coat=1, emit="#ffa040", emit_strength=4.0)
    lips = mat_simple("PaintedLips", "#6a1e1e", 0.35, coat=0.8, coat_rough=0.2)
    pin_heads = [mat_simple("PinRed", "#8a0c0c", 0.2, coat=1), mat_simple("PinWhite", "#d8d0c0", 0.2, coat=1),
                 mat_simple("PinBlack", "#0a0a0a", 0.2, coat=1), mat_simple("PinYellow", "#b8901c", 0.2, coat=1)]
    cloths = [mat_plush("FadedRose", "#6a3a3a", "#2a1414", "#8a5a54", scale=3),
              mat_plush("DustyBlue", "#3e4a5a", "#181e26", "#5e6a78", scale=3),
              mat_plush("OldVelvet", "#3a0c12", "#140406", "#5a1a20", scale=5),
              canvas,
              mat_stripes("CircusStripe", "#6a1010", "#b8a888", scale=14, direction="X", distortion=0.6)]
    grinny_plush = mat_plush("MiniGrinny", "#5e3440", "#2a141a", "#86606a")

    root = empty("Seamstress")

    # ------------------------------------------------------------ ceiling rail and trolley
    rail_z = 4.42
    L = 3.4
    prim("cube", "RailTopFlange", (0, 0, rail_z + 0.13), (L, 0.16, 0.022), m=rust, parent=root)
    prim("cube", "RailWeb", (0, 0, rail_z + 0.06), (L, 0.016, 0.14), m=rust, parent=root)
    prim("cube", "RailBotFlange", (0, 0, rail_z - 0.01), (L, 0.16, 0.022), m=rust, parent=root)
    for x in (-1.3, 1.3):
        prim("cube", "RailHanger%d" % x, (x, 0, rail_z + 0.5), (0.05, 0.05, 0.75), m=rust, parent=root)
        for dy in (-0.05, 0.05):
            prim("cyl", "RailBolt%d_%d" % (x, dy * 100), (x + 0.04, dy, rail_z + 0.15), (0.012, 0.012, 0.05),
                 m=rust, parent=root, rot=(0, R(90), 0), vertices=6)
    # trolley: four flanged wheels riding the bottom flange, side plates, cross bolt
    tz = rail_z + 0.045
    for sx in (-0.11, 0.11):
        for sy in (-1, 1):
            w = prim("cyl", "TrolleyWheel", (sx, sy * 0.046, tz), (0.042, 0.042, 0.026), m=rust, parent=root,
                     rot=(R(90), 0, 0), vertices=24)
            bevel(w, 0.006, 2)
            prim("cyl", "WheelFlange", (sx, sy * 0.064, tz), (0.052, 0.052, 0.008), m=rust, parent=root,
                 rot=(R(90), 0, 0), vertices=24)
    for sy in (-1, 1):
        sp = prim("cube", "TrolleyPlate", (0, sy * 0.082, rail_z - 0.04), (0.34, 0.012, 0.2), m=rust, parent=root)
        bevel(sp, 0.01, 2)
    seg("TrolleyAxleBolt", (0, -0.1, rail_z - 0.11), (0, 0.1, rail_z - 0.11), 0.016, rust, root)
    # chain
    cz = rail_z - 0.13
    for i in range(7):
        t = prim("torus", "ChainLink%d" % i, (0, 0, cz - i * 0.058), (1, 0.62, 1), m=rust, parent=root,
                 major_radius=0.036, minor_radius=0.009, major_segments=20, minor_segments=8,
                 rot=(R(90), 0, R(90 * (i % 2))))
    hook_top = cz - 7 * 0.058
    # the hanger rod skewers down through her pincushion bun into the skull
    head_c = Vector((0.03, -0.06, 3.12))
    rod_bot = head_c + Vector((0, 0.02, 0.05))
    seg("HangerRod", (0, 0, hook_top + 0.02), rod_bot, 0.013, steel, root)
    prim("torus", "RodEye", (0, 0, hook_top + 0.02), (1, 1, 1), m=steel, parent=root, major_radius=0.026,
         minor_radius=0.007, rot=(R(90), 0, 0))
    prim("cyl", "RodCollar", (0.0, 0, 3.47), (0.03, 0.03, 0.04), m=brass, parent=root)

    # ------------------------------------------------------------ dress form
    prof = [(0.0, 1.84), (0.17, 1.845), (0.235, 1.87), (0.27, 1.95), (0.275, 2.03), (0.258, 2.12), (0.222, 2.2),
            (0.2, 2.27), (0.205, 2.34), (0.226, 2.44), (0.252, 2.55), (0.262, 2.62), (0.255, 2.69), (0.25, 2.75),
            (0.245, 2.8), (0.215, 2.85), (0.15, 2.885), (0.085, 2.91), (0.062, 2.94), (0.058, 2.99), (0.0, 3.0)]
    form = ell_lathe("DressForm", prof, 0.74, m=canvas, parent=root)
    # the bust and shoulder blades pushed out a little
    for v in form.data.vertices:
        x, y, z = v.co
        bust = math.exp(-((z - 2.6) / 0.07) ** 2) * math.exp(-((abs(x) - 0.11) / 0.08) ** 2) * (1 if y < 0 else 0)
        blade = math.exp(-((z - 2.72) / 0.08) ** 2) * math.exp(-((abs(x) - 0.12) / 0.08) ** 2) * (1 if y > 0 else 0)
        sh = math.exp(-((z - 2.82) / 0.05) ** 2)
        v.co.y += -bust * 0.045 + blade * 0.02
        v.co.x *= 1 + sh * 0.12
    form.data.update()
    displace(form, 0.006, 0.12)
    apply_mods(form)
    # tear in the left flank: canvas peeled open over horsehair padding and a dark hollow
    tear_c = Vector((-0.22, -0.1, 2.12))
    cut = prim("ico", "FormTear", tear_c, (0.09, 0.09, 0.16), subdivisions=4)
    displace(cut, 0.035, 0.05)
    apply_mods(cut)
    boolean(form, cut)
    prim("sphere", "FormHollow", tear_c + Vector((0.08, 0.0, 0)), (0.07, 0.075, 0.14), m=cavity, parent=root)
    for i in range(14):
        a = random.uniform(0, 2 * math.pi)
        p = tear_c + Vector((0.02, math.cos(a) * 0.06, math.sin(a) * 0.11))
        s = random.uniform(0.018, 0.035)
        h = prim("ico", "HorseHair%d" % i, p, (s, s, s * 1.4), m=stuffing, parent=root, subdivisions=3)
        displace(h, s * 0.5, 0.02, depth=4)
    for i in range(4):
        z0 = tear_c.z - 0.08 + i * 0.05
        seg("FormWire%d" % i, tear_c + Vector((0.05, -0.08, z0 - tear_c.z)), tear_c + Vector((0.05, 0.08, z0 - tear_c.z + 0.01)),
            0.0035, rust, root, verts=6)
    seam_tape = mat_plush("SeamTape", "#6a5a44", "#3a2e22", "#8a7a5e", scale=8)
    # princess-seam piping running over the canvas
    for a in (R(-62), R(-118), R(62), R(118), R(90)):
        pts = []
        for k in range(16):
            z = 1.9 + k * (2.84 - 1.9) / 15
            loc, n = onto(form, (0, 0, z), (math.cos(a), -math.sin(a), 0), 1.0)
            if loc is not None and (loc - tear_c).length > 0.15:
                pts.append(loc + n * 0.0035)
            elif len(pts) > 1:
                ribbon("Piping", pts, 0.006, 0.0018, seam_tape, root, twist_side=(-math.sin(a), -math.cos(a), 0))
                pts = []
        if len(pts) > 1:
            ribbon("Piping", pts, 0.006, 0.0018, seam_tape, root, twist_side=(-math.sin(a), -math.cos(a), 0))
    # waist tape and the wooden base plate
    ring = []
    for k in range(49):
        a = 2 * math.pi * k / 48
        loc, n = onto(form, (0, 0, 2.27), (math.cos(a), math.sin(a), 0), 1.0)
        if loc is not None:
            ring.append(loc + n * 0.003)
    cord("WaistTape", ring, 0.006, thread_blk, root)
    base = prim("cyl", "FormBase", (0, 0, 1.83), (0.24, 0.24 * 0.74, 0.03), m=spool_wood, parent=root, vertices=48)
    bevel(base, 0.008, 2)
    # neck cap
    cap = prim("cyl", "NeckCap", (0, 0, 3.005), (0.07, 0.07, 0.018), m=spool_wood, parent=root, vertices=32)
    bevel(cap, 0.006, 2)

    # paper sewing pattern pinned to the chest
    GX, GZ = 14, 18
    pv, pf = [], []
    for j in range(GZ):
        for i in range(GX):
            x = -0.02 + 0.16 * i / (GX - 1) + 0.006 * math.sin(j * 0.9)
            z = 2.32 + 0.2 * j / (GZ - 1)
            # tissue paper slightly lifted and crumpled, curling away at the lower corner
            loc, n = onto(form, (0, 0, z), (x, -1, 0), 1.0)
            curl = max(0.0, (0.03 - x) * 0.4) * max(0.0, (2.38 - z)) * 60
            pv.append(tuple(loc + n * (0.004 + 0.002 * random.random() + curl * 0.02)))
    for j in range(GZ - 1):
        for i in range(GX - 1):
            pf.append((j * GX + i, j * GX + i + 1, (j + 1) * GX + i + 1, (j + 1) * GX + i))
    pme = bpy.data.meshes.new("PatternPiece")
    pme.from_pydata(pv, [], pf)
    pme.update()
    pp = link_obj(bpy.data.objects.new("PatternPiece", pme))
    pp.parent = root
    pme.materials.append(paper)
    smooth(pp)
    so = pp.modifiers.new("Sol", "SOLIDIFY")
    so.thickness = 0.0008
    for i, (dx, dz) in enumerate(((-0.075, 0.09), (0.075, 0.085), (-0.07, -0.085), (0.075, -0.09))):
        loc, n = onto(form, (0, 0, 2.42 + dz), (0.06 + dx, -1, 0), 1.0)
        if loc is not None:
            pin("PatternPin%d" % i, loc + n * 0.005, n, random.choice(pin_heads), steel, root)
    # loose pins all over
    for i in range(22):
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 0.4), 0)).normalized()
        loc, n = onto(form, (0, 0, random.uniform(1.95, 2.8)), d, 1.0)
        if loc is not None and (loc - tear_c).length > 0.14:
            pin("Pin%d" % i, loc, n, random.choice(pin_heads), steel, root)

    # ------------------------------------------------------------ neck and porcelain head
    neck_pts = [(0, 0, 2.99), (0.01, -0.01, 3.03), (0.025, -0.03, 3.0), head_c + Vector((0.0, 0.01, -0.13))]
    N = Skel()
    N.chain(None, [(neck_pts[0], 0.05), (neck_pts[1], 0.045), (neck_pts[3], 0.048)])
    nk = N.build("Neck", porcelain, subdiv=2, parent=root)
    # thread wound round the neck where it was sewn on
    for i in range(7):
        z = 3.0 + i * 0.012
        prim("torus", "NeckWrap%d" % i, (0.005, -0.012, z), (1, 1, 1), m=thread_red, parent=root,
             major_radius=0.052, minor_radius=0.0028, rot=(R(random.uniform(-8, 8)), R(random.uniform(-8, 8)), 0))

    head_pivot = empty("HeadPivot", head_c + Vector((0, 0, -0.12)), root)
    hc = head_c
    head = prim("sphere", "Head", (0, 0, 0), (1, 1, 1), m=porcelain, parent=root, segments=96, ring_count=48)
    for v in head.data.vertices:
        x, y, z = v.co
        # egg-shaped skull, flatter at the back, narrowing to a small doll chin
        sx, sy, sz = 0.152, 0.162, 0.188
        low = max(0.0, -z)                       # 0 at the equator, 1 at the chin
        taper = 1 - 0.32 * low ** 1.6
        X, Y, Z = x * sx * taper, y * sy, z * sz
        if y < 0:                                # face plane pushed forward, chin forward
            Y *= 1 + 0.08 * low
            Y -= 0.012 * math.exp(-((z + 0.25) / 0.25) ** 2)
        else:
            Y *= 0.94
        # plump doll cheeks
        for s in (-1, 1):
            d = (x - 0.45 * s) ** 2 + (y + 0.8) ** 2 + (z + 0.3) ** 2
            g = math.exp(-d / 0.08)
            X += 0.01 * g * s
            Y -= 0.012 * g
        # brow ridge and eye hollows
        for s in (-1, 1):
            d = (x - 0.34 * s) ** 2 + (y + 0.9) ** 2 + (z - 0.02) ** 2
            Y += 0.012 * math.exp(-d / 0.03)
        # nose bump
        d = x ** 2 + (y + 1) ** 2 + (z + 0.12) ** 2
        Y -= 0.016 * math.exp(-d / 0.012)
        v.co = Vector((X, Y, Z)) + hc
    head.data.update()
    eye_y = hc.y - 0.155
    eyes = {}
    for s in (-1, 1):
        loc, n = onto(head, hc + Vector((0.052 * s, 0, 0.0)), (0.25 * s, -1, 0.05), 0.6)
        eyes[s] = (loc, n)
        sock = prim("sphere", "EyeSocketCut", loc - n * 0.004, (0.031, 0.02, 0.021))
        orient(sock, (0, 0, 0), n)
        sock.scale = (0.031, 0.021, 0.02)
        boolean(head, sock)
    # chipped forehead: a piece has broken away, showing the hollow inside
    chip_at, _ = onto(head, hc + Vector((-0.03, 0, 0.09)), (-0.4, -1, 0.7), 0.6)
    chip = prim("ico", "ForeheadChip", chip_at, (0.045, 0.03, 0.035), subdivisions=2)
    displace(chip, 0.01, 0.02)
    apply_mods(chip)
    boolean(head, chip)
    # a shard of the left cheek has broken off: under the porcelain there is a real face, grey and old
    shard_at, shard_n = onto(head, hc + Vector((-0.06, 0, -0.055)), (-0.55, -1, -0.15), 0.6)
    shard = prim("ico", "CheekShard", shard_at, (0.036, 0.03, 0.03), subdivisions=1)
    orient(shard, (0, 0, 0), shard_n)
    shard.scale = (0.04, 0.03, 0.022)
    bpy.context.view_layer.update()
    apply_mods(shard)
    boolean(head, shard)
    skin = mat_simple("UnderSkin", "#5a4234", 0.55, sss=0.2, sss_radius=(1, 0.4, 0.3), sss_scale=0.01)
    under = prim("sphere", "UnderFace", shard_at - shard_n * 0.012, (0.045, 0.035, 0.04), m=skin, parent=root)
    orient(under, (0, 0, 0), shard_n)
    under.scale = (0.045, 0.035, 0.012)
    displace(under, 0.002, 0.006, depth=4)
    # porcelain edge of the break, thick and bright
    for k in range(10):
        a = 2 * math.pi * k / 10
        side = shard_n.cross(UP).normalized()
        upn = side.cross(shard_n).normalized()
        e = shard_at + (side * math.cos(a) * 0.036 + upn * math.sin(a) * 0.026) - shard_n * 0.003
        prim("ico", "ShardChip%d" % k, e, (0.003, 0.003, 0.003), m=porcelain, parent=root, subdivisions=1)
    prim("sphere", "HeadHollow", hc + Vector((0, 0, 0.02)), (0.13, 0.12, 0.14), m=cavity, parent=root)
    # right eye: glass doll eye under a jeweller's loupe (the only thing she sees with)
    loc, n = eyes[1]
    ec = loc - n * 0.016
    prim("sphere", "GlassEye", ec, (0.022, 0.022, 0.022), m=eyeball, parent=root)
    look = (Vector((-0.75, -1.9, 3.05)) - ec).normalized()
    ir = prim("cyl", "Iris", ec + look * 0.0205, (0.011, 0.011, 0.002), m=iris, parent=root)
    orient(ir, (0, 0, 0), look)
    pu = prim("cyl", "Pupil", ec + look * 0.0215, (0.0048, 0.0048, 0.002), m=pupil, parent=root)
    orient(pu, (0, 0, 0), look)
    lb = loc + n * 0.004
    lt = loc + n * 0.05
    tube = seg("LoupeTube", lb, lt, 0.024, brass, root, r2=0.02, verts=32)
    seg("LoupeRim", lt - n * 0.004, lt + n * 0.004, 0.022, brass, root, verts=32)
    lz = prim("sphere", "LoupeLens", lt, (0.019, 0.019, 0.006), m=lens, parent=root)
    orient(lz, (0, 0, 0), n)
    # its leather strap around the head
    strap = []
    for k in range(33):
        a = 2 * math.pi * k / 32
        l2, n2 = onto(head, hc, (math.sin(a), -math.cos(a), 0.68 + 0.2 * (1 - math.cos(a)) / 2), 0.6)
        if l2 is not None:
            strap.append(l2 + n2 * 0.004)
    leather = mat_simple("Leather", "#1e120a", 0.6, coat=0.2)
    cord("LoupeStrap", strap, 0.005, leather, root)
    band_at, band_n = onto(head, hc, (0.33, -1, 0.68), 0.6)
    seg("LoupeArm", band_at + band_n * 0.008, lt - n * 0.01 + UP * 0.012, 0.0035, brass, root, verts=8)
    prim("sphere", "LoupeHinge", band_at + band_n * 0.008, (0.007, 0.007, 0.007), m=brass, parent=root)
    # left eye: socket empty, stitched shut with an X of black thread
    loc, n = eyes[-1]
    prim("sphere", "EmptySocket", loc - n * 0.03, (0.03, 0.03, 0.03), m=cavity, parent=root)
    side = n.cross(UP).normalized()
    for sg in (-1, 1):
        a = loc + side * 0.03 + UP * 0.022 * sg + n * 0.003
        b = loc - side * 0.03 - UP * 0.022 * sg + n * 0.003
        seg("EyeX%d" % sg, a, b, 0.0024, thread_red, root, verts=6)
    # thin painted eyebrows, high and surprised like an antique bisque doll
    brow_m = mat_simple("BrowPaint", "#1e120a", 0.4, coat=0.6)
    for s in (-1, 1):
        P = []
        for k in range(7):
            u = k / 6
            x = s * (0.025 + 0.055 * u)
            z = 0.052 + 0.014 * math.sin(u * math.pi) - 0.006 * u
            l2, n2 = onto(head, hc + Vector((x, 0, z)), (x * 3, -1, 0.15), 0.6)
            if l2 is not None:
                P.append(l2 + n2 * 0.0006)
        if len(P) > 2:
            cord("BrowL" if s < 0 else "BrowR", P, 0.0019, brow_m, root)
    # painted cheeks and lips, mouth stitched shut
    for s in (-1, 1):
        loc, n = onto(head, hc + Vector((0.06 * s, 0, -0.05)), (0.35 * s, -1, -0.1), 0.6)
        bl = prim("sphere", "Blush", loc - n * 0.004, (0.026, 0.026, 0.006), m=blush, parent=root)
        orient(bl, (0, 0, 0), n)
    mloc, mn = onto(head, hc + Vector((0, 0, -0.09)), (0, -1, -0.05), 0.6)
    lp = prim("sphere", "Lips", mloc - mn * 0.002, (0.03, 0.006, 0.011), m=lips, parent=root)
    msl = seg("MouthSlit", mloc + Vector((-0.05, 0, 0)), mloc + Vector((0.05, 0, 0)), 0.0025)
    boolean(head, msl)
    for k in range(7):
        x = -0.042 + k * 0.014
        p = mloc + Vector((x, -0.004, 0))
        seg("LipStitch%d" % k, p + UP * 0.013, p - UP * 0.013, 0.0016, thread_blk, root, verts=5)
    # cracks running out of the mouth corners and down from the socket
    for i, (a, b) in enumerate((((-0.03, -0.1), (-0.07, -0.13)), ((0.03, -0.1), (0.075, -0.14)),
                                ((-0.06, -0.02), (-0.075, -0.07)))):
        prev = None
        P = []
        for t in range(6):
            u = t / 5
            x = a[0] + (b[0] - a[0]) * u + random.uniform(-0.004, 0.004)
            z = a[1] + (b[1] - a[1]) * u
            l2, n2 = onto(head, hc + Vector((x, 0, z)), (x * 4, -1, 0), 0.6)
            if l2 is not None:
                P.append(l2 - n2 * 0.0005)
        if len(P) > 1:
            cord("Crack%d" % i, P, 0.0012, cavity, root)

    # hair: a combed-back shell over the skull, real strands lying on top, and the bun (her pincushion)
    bun_c = hc + Vector((0, 0.135, 0.085))
    bun = prim("sphere", "Bun", bun_c, (0.072, 0.062, 0.064), m=hair, parent=root)
    displace(bun, 0.008, 0.025)

    def hairline(rel):
        # inside the hairline: top/back of the skull, clear of the face and below the ears at the sides
        if rel.y < -0.05 and rel.z < 0.075 + 0.25 * max(0.0, abs(rel.x) - 0.08):
            return False
        if rel.z < -0.07 and rel.y < 0.06:
            return False
        return rel.z > -0.13

    shell = head.copy()
    shell.data = head.data.copy()
    shell.name = "HairShell"
    bpy.context.collection.objects.link(shell)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.normal_update()
    kill = []
    for v in bm.verts:
        rel = v.co - hc
        if hairline(rel):
            v.co += v.normal * 0.005
        else:
            kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    shell.data.materials.clear()
    shell.data.materials.append(hair)
    so = shell.modifiers.new("Sol", "SOLIDIFY")
    so.thickness = 0.004
    displace(shell, 0.0025, 0.02)
    cu = bpy.data.curves.new("HairStrands", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0011
    cu.bevel_resolution = 1
    made = 0
    tries = 0
    while made < 900 and tries < 6000:
        tries += 1
        d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.6, 1))).normalized()
        l0, n0 = onto(head, hc, d, 0.6)
        if l0 is None or not hairline(l0 - hc):
            continue
        stray = random.random() < 0.06
        P = []
        for t in range(12):
            u = t / 11
            if stray:  # loose strands that escaped the bun and hang down
                p = l0 + n0 * 0.007 + Vector((random.uniform(-.004, .004), 0.01 * u, -0.26 * u ** 1.6))
            else:
                target = bun_c + (l0 - bun_c).normalized() * 0.055
                q = l0.lerp(target, u)
                lq, nq = onto(head, hc, q - hc, 0.6)
                if lq is None:
                    break
                lift = 0.0075 + 0.003 * math.sin(u * math.pi) + 0.0012 * random.random()
                p = lq + nq * lift if (q - bun_c).length > 0.075 else q
            P.append(p)
        if len(P) < 4:
            continue
        sp = cu.splines.new("POLY")
        sp.points.add(len(P) - 1)
        for k, p in enumerate(P):
            sp.points[k].co = (p.x, p.y, p.z, 1)
        made += 1
    hs = link_obj(bpy.data.objects.new("HairStrands", cu))
    hs.parent = root
    cu.materials.append(hair)
    # pins and needles stuck in the bun
    for i in range(18):
        d = Vector((random.uniform(-1, 1), random.uniform(0, 1), random.uniform(-0.3, 1))).normalized()
        l2, n2 = onto(bun, bun_c, d, 0.4)
        if l2 is None:
            continue
        if i % 4 == 0:  # sewing needle
            dd = (n2 + Vector((random.uniform(-.3, .3), 0, random.uniform(0, .4)))).normalized()
            seg("BunNeedle%d" % i, l2 - dd * 0.02, l2 + dd * 0.05, 0.0016, steel, root, verts=6)
            seg("BunNeedleThread%d" % i, l2 + dd * 0.048, l2 + dd * 0.05 + Vector((0.01, 0.02, -0.12)), 0.0011,
                thread_red, root, verts=5)
        else:
            pin("BunPin%d" % i, l2, n2, random.choice(pin_heads), steel, root, length=0.05, head=0.0075)

    # tilt the head on its sewn neck
    bpy.context.view_layer.update()
    for o in list(bpy.data.objects):
        if o.parent is not root or o.type not in ("MESH", "CURVE"):
            continue
        if o.name.startswith(("Head", "Glass", "Iris", "Pupil", "Loupe", "Empty", "EyeX", "Blush", "Lips", "Brow", "UnderFace", "ShardChip",
                              "LipStitch", "Crack", "Bun", "HairStrands", "HairShell")):
            mw = o.matrix_world.copy()
            o.parent = head_pivot
            o.matrix_world = mw
    head_pivot.rotation_euler = (R(14), R(-12), R(9))

    # dried blood that ran down from where the head was sewn on
    blood = mat_simple("DriedBlood", "#2a0604", 0.35, coat=0.5, coat_rough=0.2)
    for i, (x0, length) in enumerate(((-0.035, 0.3), (0.012, 0.46), (0.05, 0.2))):
        P, R2 = [], []
        x = x0
        for k in range(14):
            u = k / 13
            z = 2.9 - u * length
            x += random.uniform(-0.006, 0.006)
            l2, n2 = onto(form, (0, 0, z), (x, -1, 0), 1.0)
            if l2 is None:
                break
            P.append((l2 + n2 * 0.0015, 0.0035 * (1 - 0.5 * u) * random.uniform(0.7, 1.3) + 0.0012 + (0.0035 if k == 13 else 0)))
        if len(P) > 2:
            S = Skel()
            S.chain(None, [(p, (r, r * 0.6)) for p, r in P])
            S.build("BloodDrip%d" % i, blood, subdiv=1, parent=root)
    # measuring tape around the neck, hanging down the front
    tp_l = [Vector((-0.06, 0.03, 2.95)), Vector((-0.09, -0.04, 2.9)), Vector((-0.12, -0.13, 2.82)),
            Vector((-0.14, -0.2, 2.65)), Vector((-0.15, -0.2, 2.45)), Vector((-0.155, -0.19, 2.25)),
            Vector((-0.15, -0.21, 2.1))]
    tp_r = [Vector((0.06, 0.03, 2.95)), Vector((0.09, -0.05, 2.9)), Vector((0.11, -0.15, 2.8)),
            Vector((0.13, -0.235, 2.62)), Vector((0.14, -0.24, 2.45)), Vector((0.15, -0.23, 2.32))]
    tp_b = [Vector((-0.06, 0.03, 2.95)), Vector((0, 0.07, 2.96)), Vector((0.06, 0.03, 2.95))]
    for nm, P in (("TapeL", tp_l), ("TapeR", tp_r), ("TapeBack", tp_b)):
        dense = []
        for k in range(len(P) - 1):
            for t in range(6):
                dense.append(P[k].lerp(P[k + 1], t / 6))
        dense.append(P[-1])
        Q = []
        for p in dense:
            l2, n2 = onto(form, (0, 0, p.z), (p.x, p.y, 0), 1.0)
            Q.append(l2 + n2 * 0.003 if l2 is not None and p.z < 2.88 else p)
        ribbon(nm, Q, 0.009, 0.0012, tape, root)
    brass_end = prim("cube", "TapeEnd", tp_l[-1] + Vector((0, -0.005, -0.01)), (0.02, 0.004, 0.014), m=brass, parent=root)

    # ------------------------------------------------------------ the shear arms (wooden mannequin limbs)
    def ball(name, at, r):
        b = prim("sphere", name, at, (r, r, r), m=wood, parent=root)
        return b

    def limb(name, a, b, r0, r1):
        o = seg(name, a, b, r0, wood, root, r2=r1, verts=24)
        bevel(o, 0.004, 2)
        return o

    def shears(name, wrist, fwd, upv, openness, length=0.78):
        """Tailor's shears bolted onto the wrist in place of a hand."""
        fwd, upv = Vector(fwd).normalized(), Vector(upv).normalized()
        side = fwd.cross(upv).normalized()
        upv = side.cross(fwd).normalized()
        pivot = Vector(wrist) + fwd * 0.2
        # bracket clamping the bow handles to the forearm
        br = seg(name + "Bracket", Vector(wrist) - fwd * 0.04, Vector(wrist) + fwd * 0.08, 0.034, rust, root, verts=8)
        for k in range(3):
            seg(name + "Lash%d" % k, Vector(wrist) + fwd * (k * 0.04 - 0.02) - side * 0.04,
                Vector(wrist) + fwd * (k * 0.04 - 0.02) + side * 0.04, 0.005, thread_red, root, verts=6)
        for sg, ang in ((1, openness), (-1, -openness)):
            d = (fwd * math.cos(ang) + upv * math.sin(ang)).normalized()
            # blade: flat, spine thick, edge thin, tapering to a point and curving slightly
            path, secs = [], []
            for k in range(14):
                u = k / 13
                path.append(pivot + d * (length * u) + upv * sg * (-0.012 * math.sin(u * math.pi)))
                w = 0.05 * (1 - u ** 1.35) + 0.003
                secs.append((0.006 * (1 - 0.6 * u) + 0.0012, w, -w * sg * 0.45))
            bl = loft(name + "Blade%s" % sg, path, secs, side=side, segs=12, m=steel, parent=root)
            # shank and bow running back into the bracket
            back = pivot - d * 0.03
            seg(name + "Shank%s" % sg, pivot, Vector(wrist) + fwd * 0.05 + upv * sg * 0.025, 0.012, steel, root,
                r2=0.009, verts=10)
            bow = prim("torus", name + "Bow%s" % sg, Vector(wrist) + upv * sg * 0.06 - fwd * 0.02, (1, 1, 1),
                       m=steel, parent=root, major_radius=0.04 if sg > 0 else 0.03, minor_radius=0.008,
                       major_segments=28, minor_segments=8)
            orient(bow, (0, 0, 0), side)
        scr = seg(name + "Screw", pivot - side * 0.012, pivot + side * 0.012, 0.012, brass, root, verts=16)
        # strands of thread snagged on the blades
        for k in range(3):
            u = random.uniform(0.25, 0.7)
            d = (fwd * math.cos(openness) + upv * math.sin(openness)).normalized()
            a = pivot + d * length * u
            cord(name + "Snag%d" % k, droop(a, a + Vector((random.uniform(-.05, .05), random.uniform(-.05, .05), -0.25)), 0.02, 5),
                 0.0012, thread_red, root)
        return pivot

    sh_l = Vector((-0.29, -0.01, 2.82))
    sh_r = Vector((0.29, -0.01, 2.82))
    for s, sh, elbow, wrist, fwd, upv, op in (
            (-1, sh_l, Vector((-0.5, -0.22, 2.55)), Vector((-0.62, -0.62, 2.62)), (-0.15, -1, 0.35), (0, 0.2, 1), R(22)),
            (1, sh_r, Vector((0.55, -0.12, 2.42)), Vector((0.66, -0.55, 2.25)), (0.12, -1, -0.15), (0, -0.1, 1), R(8))):
        ball("Shoulder%d" % s, sh, 0.055)
        limb("UpperArm%d" % s, sh, elbow, 0.045, 0.036)
        ball("Elbow%d" % s, elbow, 0.042)
        limb("Forearm%d" % s, elbow, wrist, 0.036, 0.028)
        ball("Wrist%d" % s, wrist, 0.03)
        shears("Shears%d" % s, wrist, fwd, upv, op)
    # shoulder plates screwing the limbs onto the canvas
    for s, sh in ((-1, sh_l), (1, sh_r)):
        pl = prim("cyl", "ShoulderPlate%d" % s, sh + Vector((-0.025 * s, 0, 0)), (0.06, 0.06, 0.012), m=brass,
                  parent=root, rot=(0, R(90), 0), vertices=24)

    # ------------------------------------------------------------ the lower sewing arms (wire wrapped in thread)
    wrap = mat_stripes("ThreadWrap", "#2a0406", "#4e0a0e", scale=160, direction="Z", distortion=0.3)

    def wire_arm(name, a, el, wr, r=0.017):
        A = Skel()
        A.chain(None, [(a, r * 1.3), (el, r), (wr, r * 0.85)])
        o = A.build(name, wrap, subdiv=2, parent=root)
        displace(o, 0.003, 0.02)
        return o

    def doll_hand(name, wr, fwd, curl=0.6):
        fwd = Vector(fwd).normalized()
        side = fwd.cross(UP).normalized()
        dn = side.cross(fwd).normalized() * -1
        palm = Vector(wr) + fwd * 0.03
        prim("sphere", name + "Palm", palm, (0.026, 0.03, 0.02), m=porcelain, parent=root)
        tips = []
        for f in range(4):
            b = palm + side * (f - 1.5) * 0.012 + fwd * 0.022
            P = [(b, 0.0065), (b + fwd * 0.022 + dn * 0.008 * curl, 0.0058), (b + fwd * 0.036 + dn * 0.022 * curl, 0.005)]
            S = Skel()
            S.chain(None, P)
            S.build(name + "Finger%d" % f, porcelain, subdiv=2, parent=root)
            tips.append(P[-1][0])
        S = Skel()
        S.chain(None, [(palm - side * 0.02, 0.007), (palm - side * 0.03 + fwd * 0.02 + dn * 0.01, 0.006)])
        S.build(name + "Thumb", porcelain, subdiv=2, parent=root)
        return palm, tips

    # left lower arm holds a long sewing needle, its red thread trailing down into the skirt
    la0, la1, la2 = Vector((-0.18, -0.06, 2.36)), Vector((-0.38, -0.25, 2.22)), Vector((-0.34, -0.48, 2.3))
    wire_arm("LowerArmL", la0, la1, la2)
    palm, _ = doll_hand("HandL", la2, (0.1, -1, 0.3), 0.9)
    nd = Vector((0.25, -0.3, 1)).normalized()
    n0, n1 = palm - nd * 0.18, palm + nd * 0.42
    seg("BigNeedle", n0, n1, 0.006, steel, root, r2=0.0008, verts=12)
    eye = prim("torus", "NeedleEye", n0 + nd * 0.02, (1, 1, 1), m=steel, parent=root, major_radius=0.009,
               minor_radius=0.003)
    orient(eye, (0, 0, 0), Vector((1, 0, 0)))
    cord("NeedleThread", droop(n0 + nd * 0.02, Vector((-0.3, -0.42, 1.35)), 0.1, 14), 0.0018, thread_red, root)
    # right lower arm: thimble on the finger, holding a half-sewn sleeve of a child's costume
    ra0, ra1, ra2 = Vector((0.18, -0.06, 2.36)), Vector((0.36, -0.2, 2.15)), Vector((0.3, -0.42, 2.05))
    wire_arm("LowerArmR", ra0, ra1, ra2)
    palm, tips = doll_hand("HandR", ra2, (-0.2, -1, -0.2), 0.7)
    th = prim("cyl", "Thimble", tips[0] + Vector((0, -0.004, 0)), (0.0075, 0.0075, 0.011), m=brass, parent=root)
    orient(th, (0, 0, 0), Vector((-0.2, -1, -0.2)))
    sleeve = Skel()
    sleeve.chain(None, [(palm + Vector((0.0, -0.04, -0.02)), 0.032), (palm + Vector((0.02, -0.08, -0.12)), 0.03),
                        (palm + Vector((0.03, -0.07, -0.22)), 0.026)])
    sl = sleeve.build("CostumeSleeve", grinny_plush, subdiv=2, parent=root)
    displace(sl, 0.006, 0.03)
    cord("SleeveThread", droop(palm + Vector((0.03, -0.07, -0.24)), Vector((0.2, -0.3, 1.2)), 0.05, 10), 0.0014,
         thread_red, root)

    # ------------------------------------------------------------ spools on her back
    for i, (x, z) in enumerate(((-0.1, 2.72), (0.1, 2.72), (0, 2.52))):
        c = Vector((x, 0.215 if z > 2.6 else 0.19, z))
        prim("cyl", "SpoolPeg%d" % i, c + Vector((0, -0.02, 0)), (0.008, 0.008, 0.08), m=rust, parent=root,
             rot=(R(90), 0, 0))
        sp = prim("cyl", "Spool%d" % i, c + Vector((0, 0.03, 0)), (0.036, 0.036, 0.07), m=thread_red if i != 1 else thread_blk,
                  parent=root, rot=(R(90), 0, 0))
        for dy in (-0.004, 0.064):
            f = prim("cyl", "SpoolFlange%d" % i, c + Vector((0, dy, 0)), (0.046, 0.046, 0.008), m=spool_wood,
                     parent=root, rot=(R(90), 0, 0))
            bevel(f, 0.003, 2)
    cord("SpoolThread", droop(Vector((-0.1, 0.25, 2.72)), Vector((-0.27, 0.0, 2.8)), 0.06, 8), 0.0014, thread_red, root)

    # ------------------------------------------------------------ crinoline cage and the skirt of rags
    hoops = [(1.8, 0.27), (1.55, 0.36), (1.3, 0.45), (1.05, 0.52), (0.82, 0.58)]
    for i, (z, r) in enumerate(hoops):
        t = prim("torus", "Hoop%d" % i, (0, 0, z), (1, 0.82, 1), m=rust, parent=root, major_radius=r,
                 minor_radius=0.0065, major_segments=64, minor_segments=8)
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.15
        P = [Vector((math.cos(a) * r, math.sin(a) * r * 0.82, z)) for z, r in hoops]
        P = [Vector((math.cos(a) * 0.22, math.sin(a) * 0.17, 1.84))] + P
        ribbon("CageTape%d" % k, P, 0.012, 0.0015, canvas, root, twist_side=(-math.sin(a), math.cos(a), 0))
    # the skirt: heavy old velvet hanging over the cage in deep folds, rotted through, hem torn to rags
    velvet = cloths[2]
    A, Z = 160, 26
    hem = [random.uniform(0.62, 1.05) for _ in range(A)]
    for _ in range(3):  # smooth the hem a little, then cut a few long rips into it
        hem = [(hem[i - 1] + hem[i] * 2 + hem[(i + 1) % A]) / 4 for i in range(A)]
    for _ in range(9):
        c = random.randrange(A)
        for k in range(-2, 3):
            hem[(c + k) % A] += random.uniform(0.25, 0.55) * (1 - abs(k) / 3)
    verts, faces = [], []
    for i in range(A):
        a = 2 * math.pi * i / A
        for j in range(Z):
            t = j / (Z - 1)
            z = 1.86 - t * (1.86 - hem[i])
            depth = (1.86 - z)
            r = 0.27 + depth * 0.33
            fold = 0.035 * min(1.0, depth / 0.4) * (math.sin(a * 11 + 0.6 * math.sin(a * 3)) + 0.4 * math.sin(a * 23 + 1))
            r += fold + 0.012
            verts.append((math.cos(a) * r, math.sin(a) * r * 0.82, z))
    for i in range(A):
        i2 = (i + 1) % A
        for j in range(Z - 1):
            faces.append((i * Z + j, i * Z + j + 1, i2 * Z + j + 1, i2 * Z + j))
    # moth-eaten holes and a long gash at the front showing the cage: drop the faces inside them
    holes = []
    for k in range(8):
        a = random.uniform(0, 2 * math.pi) if k else -math.pi / 2 + 0.25
        z = random.uniform(0.95, 1.6) if k else 1.15
        r = 0.27 + (1.86 - z) * 0.33
        sc = (0.07, 0.07, 0.11) if k else (0.1, 0.1, 0.4)
        holes.append((Vector((math.cos(a) * r, math.sin(a) * r * 0.82, z)), Vector(sc), random.uniform(0, 9)))

    def in_hole(c):
        for hcn, sc, ph in holes:
            d = c - hcn
            q = (d.x / sc.x) ** 2 + (d.y / sc.y) ** 2 + (d.z / sc.z) ** 2
            wob = 1 + 0.35 * math.sin(c.z * 60 + ph) * math.sin(math.atan2(c.y, c.x) * 40 + ph)
            if q < wob:
                return True
        return False

    keep = []
    for f in faces:
        c = sum((Vector(verts[i]) for i in f), Vector()) / 4
        if not in_hole(c):
            keep.append(f)
    me = bpy.data.meshes.new("Skirt")
    me.from_pydata(verts, [], keep)
    me.update()
    skirt = link_obj(bpy.data.objects.new("Skirt", me))
    skirt.parent = root
    me.materials.append(velvet)
    smooth(skirt)
    displace(skirt, 0.015, 0.12)
    so = skirt.modifiers.new("Sol", "SOLIDIFY")
    so.thickness = 0.005
    # loose strips torn from the hem and still hanging
    for k in range(26):
        a = random.uniform(0, 2 * math.pi)
        i = int(a / (2 * math.pi) * A) % A
        top_z = hem[i] + 0.05
        bottom = top_z - random.uniform(0.15, 0.55)
        P = []
        for zi in range(8):
            z = top_z - zi * (top_z - bottom) / 7
            r = 0.27 + (1.86 - z) * 0.33 + 0.025 + 0.015 * math.sin(zi + k)
            P.append(Vector((math.cos(a) * r, math.sin(a) * r * 0.82, z)))
        w = random.uniform(0.02, 0.05)
        o = ribbon("Rag%d" % k, P, w, 0.002, random.choice(cloths), root, twist_side=(-math.sin(a), math.cos(a), 0))
        displace(o, 0.01, 0.06)
        for f in range(2):
            e = P[-1] + Vector((random.uniform(-w, w) * 0.6, 0, 0))
            seg("Fray%d_%d" % (k, f), e, e + Vector((random.uniform(-.02, .02), random.uniform(-.02, .02), -random.uniform(0.04, 0.12))),
                0.0012, thread_blk, root, verts=5)
    # a hem of lace, rotten and grey, along the waist
    lace = mat_simple("Lace", "#8a8272", 0.8, sheen=0.5)
    for k in range(60):
        a = 2 * math.pi * k / 60
        r = 0.29
        p = Vector((math.cos(a) * r, math.sin(a) * r * 0.82, 1.84))
        prim("sphere", "Lace%d" % k, p, (0.022, 0.022, 0.03), m=lace, parent=root, segments=10, ring_count=6)

    # the little Grinny costumes she never finished, hung from the hoops on thread
    def mini_costume(i, at, rot):
        g = empty("MiniCostume%d" % i, at, root)
        g.rotation_euler = (R(random.uniform(-10, 10)), R(random.uniform(-10, 10)), rot)
        S = Skel()
        S.chain(None, [((0, 0, -0.2), (0.07, 0.06)), ((0, 0, -0.08), (0.08, 0.07)), ((0, 0, 0.0), (0.06, 0.05))])
        for s in (-1, 1):
            S.chain(1, [((0.08 * s, 0, -0.05), 0.025), ((0.11 * s, -0.01, -0.16), 0.02)])
            S.chain(0, [((0.04 * s, 0, -0.24), 0.028), ((0.045 * s, -0.01, -0.34), 0.024)])
        b = S.build("CostumeBody%d" % i, grinny_plush, subdiv=2, parent=g)
        displace(b, 0.006, 0.03)
        hd = prim("sphere", "CostumeHood%d" % i, (0, 0, 0.08), (0.085, 0.08, 0.08), m=grinny_plush, parent=g)
        displace(hd, 0.005, 0.03)
        # empty face opening of the hood: no one inside
        fo = prim("sphere", "HoodHole%d" % i, (0, -0.07, 0.07), (0.05, 0.04, 0.055), m=cavity, parent=g)
        for s in (-1, 1):
            prim("sphere", "CostumeEar%d" % i, (0.07 * s, 0, 0.15), (0.035, 0.012, 0.035), m=grinny_plush, parent=g)
        # unfinished seam with the needle still in it
        seg("CostumePin%d" % i, (0.05, -0.06, -0.12), (0.09, -0.08, -0.04), 0.0012, steel, g, verts=6)
        cord("CostumeSeam%d" % i, [Vector((-0.04, -0.07, -0.18)), Vector((0.0, -0.075, -0.12)), Vector((0.03, -0.072, -0.06))],
             0.0015, thread_red, g)
        return g

    for i, (a, z_hoop, drop) in enumerate(((R(-120), 3, 0.32), (R(-40), 4, 0.22), (R(160), 2, 0.4), (R(60), 4, 0.28))):
        z, r = hoops[z_hoop]
        top = Vector((math.cos(a) * r, math.sin(a) * r * 0.82, z))
        bot = top + Vector((0, 0, -drop))
        seg("CostumeString%d" % i, top, bot + Vector((0, 0, 0.12)), 0.0012, thread_red, root, verts=5)
        mini_costume(i, bot - Vector((0, 0, 0.04)), a + math.pi / 2)

    apply_scans(root)
    return root
