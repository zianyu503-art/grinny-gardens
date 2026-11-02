"""joy_jar: thick glass laughter jar with a dented brass screw lid, a terminal with two
cloth-insulated wires, murky liquid, a glowing orb with stuffing fibres and a faded label.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/joy_jar_build.py

Units: metres. Z up, base on z=0, label on the -Y (front) side.
"""
import sys
import math
import os
import random

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import bkit  # noqa: E402


# ---------------------------------------------------------------- wear helpers (shader masks)

def sock(node, name, out=False):
    coll = node.outputs if out else node.inputs
    return next(s for s in coll if s.name == name and getattr(s, "enabled", True))


def math_n(nt, op, a, b=None, clamp=False):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            nt.links.new(v, m.inputs[i])
    return m.outputs[0]


def obj_xyz(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    return tc.outputs["Object"], sep.outputs


def remap(nt, v, a, b, c=0.0, d=1.0):
    m = nt.nodes.new("ShaderNodeMapRange")
    m.clamp = True
    nt.links.new(v, sock(m, "Value"))
    sock(m, "From Min").default_value = a
    sock(m, "From Max").default_value = b
    sock(m, "To Min").default_value = c
    sock(m, "To Max").default_value = d
    return sock(m, "Result", out=True)


def noise_mask(nt, vec, scale, lo, hi, stretch=None):
    N, L = nt.nodes, nt.links
    if stretch:
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = stretch
        L.new(vec, mp.inputs["Vector"])
        vec = mp.outputs["Vector"]
    n = N.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 6.0
    L.new(vec, n.inputs["Vector"])
    r = N.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = lo
    r.color_ramp.elements[1].position = hi
    L.new(n.outputs["Fac"], r.inputs["Fac"])
    return r.outputs["Color"]


def overlay(mat, fac, color=None, color_socket=None, roughness=None):
    """Mix a colour (and optionally a roughness) over the material where fac is 1."""
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    bc = bsdf.inputs["Base Color"]
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    L.new(fac, sock(mix, "Factor"))
    if bc.links:
        L.new(bc.links[0].from_socket, sock(mix, "A"))
    else:
        sock(mix, "A").default_value = bc.default_value
    if color_socket is not None:
        L.new(color_socket, sock(mix, "B"))
    else:
        sock(mix, "B").default_value = (*color, 1)
    L.new(sock(mix, "Result", out=True), bc)
    if roughness is not None:
        rs = bsdf.inputs["Roughness"]
        rm = N.new("ShaderNodeMix")
        rm.data_type = "FLOAT"
        L.new(fac, sock(rm, "Factor"))
        if rs.links:
            L.new(rs.links[0].from_socket, sock(rm, "A"))
        else:
            sock(rm, "A").default_value = rs.default_value
        sock(rm, "B").default_value = roughness
        L.new(sock(rm, "Result", out=True), rs)
    return mat

ROOT = "/Users/alex/恐怖遊戲2"
ASSET = "joy_jar"
BAKE_DIR = f"{ROOT}/blender/bake/{ASSET}"
PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_preview.png"
BAKED_PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_baked.png"
GLB = f"{ROOT}/public/models/{ASSET}.glb"
BLEND = f"{BAKE_DIR}/{ASSET}.blend"
TRI_BUDGET = 2500
TAU = math.tau

random.seed(1996)


# ---------------------------------------------------------------- bmesh helpers

def add_cone(bm, r, h, seg, matrix=None, r2=None):
    """Append a capped cylinder (or cone when r2 given) centred on origin along Z."""
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                radius1=r, radius2=r if r2 is None else r2, depth=h)
    if matrix is not None:
        bmesh.ops.transform(bm, matrix=matrix, verts=ret["verts"])
    return bm


def lathe_bm(profile, steps=18):
    """Revolve an (r, z) profile around Z. Open chains give open surfaces."""
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    es = [bm.edges.new((a, b)) for a, b in zip(vs, vs[1:])]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=TAU,
                   steps=steps, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    return bm


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def part(name, bm, mat, uv_size=0.1):
    obj = mesh_obj(name, bm)
    obj.data.materials.append(mat)
    bkit.box_uv(obj, size=uv_size)
    return obj


# ---------------------------------------------------------------- materials

def glass_dirty(name):
    """Green transmission glass with grime blotches and fingerprint roughness."""
    mat = bpy.data.materials.new(name)
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")

    dirt = N.new("ShaderNodeTexNoise")
    dirt.inputs["Scale"].default_value = 9.0
    dirt.inputs["Detail"].default_value = 8.0
    L.new(tc.outputs["Object"], dirt.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.62, 0.78, 0.66, 1)
    ramp.color_ramp.elements[1].position = 0.68
    ramp.color_ramp.elements[1].color = (0.30, 0.31, 0.22, 1)
    L.new(dirt.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    prints = N.new("ShaderNodeTexNoise")
    prints.inputs["Scale"].default_value = 30.0
    prints.inputs["Detail"].default_value = 4.0
    L.new(tc.outputs["Object"], prints.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.04
    mr.inputs["To Max"].default_value = 0.30
    L.new(prints.outputs["Fac"], mr.inputs["Value"])
    L.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

    bsdf.inputs["IOR"].default_value = 1.5
    vec, xyz = obj_xyz(nt)
    z = xyz[2]
    base = remap(nt, z, 0.0, 0.07, 1.0, 0.0)
    shoulder = remap(nt, math_n(nt, "ABSOLUTE", math_n(nt, "SUBTRACT", z, 0.372)), 0.0, 0.04, 1.0, 0.0)
    zone = math_n(nt, "MAXIMUM", base, shoulder)
    dust = math_n(nt, "MULTIPLY", zone, noise_mask(nt, vec, 14, 0.2, 0.55), clamp=True)
    overlay(mat, dust, color=(0.40, 0.36, 0.29), roughness=0.88)
    L.new(math_n(nt, "SUBTRACT", 1.0, math_n(nt, "MULTIPLY", dust, 0.85)),
          bsdf.inputs["Transmission Weight"])
    return mat


def paper_label(name):
    """Yellowed paper with mottling and a few faint horizontal ink strokes."""
    mat = bpy.data.materials.new(name)
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")

    mott_map = N.new("ShaderNodeMapping")
    mott_map.inputs["Scale"].default_value = (6, 6, 6)
    L.new(tc.outputs["Object"], mott_map.inputs["Vector"])
    mott = N.new("ShaderNodeTexNoise")
    mott.inputs["Scale"].default_value = 4.0
    mott.inputs["Detail"].default_value = 6.0
    L.new(mott_map.outputs["Vector"], mott.inputs["Vector"])
    paper = N.new("ShaderNodeValToRGB")
    paper.color_ramp.elements[0].color = (0.60, 0.50, 0.28, 1)
    paper.color_ramp.elements[1].color = (0.86, 0.79, 0.58, 1)
    L.new(mott.outputs["Fac"], paper.inputs["Fac"])

    stroke_map = N.new("ShaderNodeMapping")
    stroke_map.inputs["Scale"].default_value = (3.0, 3.0, 40.0)
    L.new(tc.outputs["Object"], stroke_map.inputs["Vector"])
    stroke = N.new("ShaderNodeTexNoise")
    stroke.inputs["Scale"].default_value = 1.0
    stroke.inputs["Detail"].default_value = 3.0
    L.new(stroke_map.outputs["Vector"], stroke.inputs["Vector"])
    ink = N.new("ShaderNodeValToRGB")
    ink.color_ramp.elements[0].position = 0.50
    ink.color_ramp.elements[0].color = (0, 0, 0, 1)
    ink.color_ramp.elements[1].position = 0.56
    ink.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(stroke.outputs["Fac"], ink.inputs["Fac"])

    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    L.new(ink.outputs["Color"], mix.inputs["Factor"])
    L.new(paper.outputs["Color"], mix.inputs["A"])
    mix.inputs["B"].default_value = (0.20, 0.15, 0.20, 1)
    L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.75
    overlay(mat, noise_mask(nt, mott_map.outputs["Vector"], 2.5, 0.48, 0.66),
            color=(0.36, 0.25, 0.11), roughness=0.6)
    vec, xyz = obj_xyz(nt)
    damp = math_n(nt, "MULTIPLY", remap(nt, xyz[2], 0.14, 0.19, 0.8, 0.0),
                  noise_mask(nt, vec, 25, 0.3, 0.6), clamp=True)
    overlay(mat, damp, color=(0.22, 0.17, 0.09))
    return mat


def brass_material():
    maps = bkit.polyhaven_texture("rusty_metal_02", res="1k")
    mat = bkit.pbr_material("brass", maps, scale=2.5, tint=(0.34, 0.25, 0.15),
                            metallic=1.0, roughness_mult=1.25)
    nt, bsdf = bkit._nodes(mat)
    N, L = nt.nodes, nt.links
    next(n for n in N if n.type == "MAPPING").inputs["Rotation"].default_value = (0.3, 0.2, 0.61)
    raw = next(n for n in N if n.type == "TEX_IMAGE"
               and os.path.basename(n.image.filepath).startswith("color"))
    vec, xyz = obj_xyz(nt)
    # large tarnish blotches break up the texture repeat
    overlay(mat, noise_mask(nt, vec, 5, 0.35, 0.75), color=(0.045, 0.035, 0.025), roughness=0.75)
    # rust packed into the thread bands
    band = math_n(nt, "LESS_THAN", xyz[2], 0.4235)
    overlay(mat, math_n(nt, "MULTIPLY", band, noise_mask(nt, vec, 45, 0.25, 0.5)),
            color_socket=raw.outputs["Color"], roughness=0.92)
    # thumb-worn bright spots on the top rim
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(xyz[0], comb.inputs[0])
    L.new(xyz[1], comb.inputs[1])
    ln = N.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    L.new(comb.outputs[0], ln.inputs[0])
    rim = math_n(nt, "MULTIPLY", math_n(nt, "GREATER_THAN", xyz[2], 0.443),
                 math_n(nt, "GREATER_THAN", sock(ln, "Value", out=True), 0.089))
    overlay(mat, math_n(nt, "MULTIPLY", rim, noise_mask(nt, vec, 70, 0.5, 0.6)),
            color=(0.62, 0.47, 0.23), roughness=0.3)
    return mat


def cloth_material():
    maps = bkit.polyhaven_texture("hessian_230", res="1k")
    return bkit.pbr_material("cloth_red", maps, scale=12.0, tint=(0.78, 0.14, 0.10))


# ---------------------------------------------------------------- parts

def make_glass():
    profile = [(0.0, 0.0), (0.095, 0.0), (0.104, 0.004), (0.110, 0.016), (0.110, 0.330),
               (0.104, 0.362), (0.092, 0.390), (0.088, 0.398), (0.088, 0.408)]
    bm = lathe_bm(profile, steps=24)
    obj = part("glass", bm, glass_dirty("glass_dirty"), uv_size=0.2)
    solid = obj.modifiers.new("Thickness", "SOLIDIFY")
    solid.thickness = 0.007
    solid.offset = 0.0
    bkit.harden(obj, width=0.0015, segments=1, angle=35)
    return obj


def make_lid(brass):
    profile = [(0.0, 0.405), (0.096, 0.405), (0.096, 0.418), (0.0945, 0.419),
               (0.0945, 0.421), (0.096, 0.422), (0.096, 0.447), (0.094, 0.451), (0.0, 0.451)]
    bm = lathe_bm(profile, steps=18)
    # hand-dent: a soft dip near the top, plus fine random roughness
    for v in bm.verts:
        if v.co.z > 0.43:
            d = math.hypot(v.co.x - 0.035, v.co.y + 0.03)
            if d < 0.035:
                v.co.z -= 0.0055 * (1 - d / 0.035)
            v.co.z += random.uniform(-0.0003, 0.0003)
        elif v.co.z > 0.424 and v.co.length > 0:
            a = abs(math.atan2(v.co.y, v.co.x) - 2.2)
            if a < 0.45:
                k = 1 - 0.035 * (1 - a / 0.45)
                v.co.x *= k
                v.co.y *= k
    obj = mesh_obj("lid", bm)
    obj.data.materials.append(brass)
    bkit.box_uv(obj, size=0.1)
    bkit.harden(obj, width=0.0010, segments=1, angle=40)
    return obj


def make_terminal(brass):
    bm = bmesh.new()
    add_cone(bm, 0.018, 0.006, 14, Matrix.Translation((0, 0, 0.454)))
    add_cone(bm, 0.008, 0.022, 10, Matrix.Translation((0, 0, 0.468)))
    add_cone(bm, 0.012, 0.004, 10, Matrix.Translation((0, 0, 0.480)))
    obj = part("terminal", bm, brass, uv_size=0.05)
    return obj


def wire_path(s):
    p0 = Vector((s * 0.004, 0.0, 0.476))
    p1 = Vector((s * 0.070, -0.020, 0.500))
    p2 = Vector((s * 0.130, -0.050, 0.500))
    p3 = Vector((s * 0.150, -0.060, 0.340))
    n = 22
    pts = []
    for k in range(n):
        t = k / (n - 1)
        pts.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
                   + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    return pts


def make_wire(name, s, cloth, stubs):
    pts = wire_path(s)
    cu = bpy.data.curves.new(name + "_curve", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0035
    cu.bevel_resolution = 1
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for k, p in enumerate(pts):
        sp.points[k].co = (p.x, p.y, p.z, 1.0)
    ob = bpy.data.objects.new(name + "_curve", cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = name
    obj.data.materials.append(cloth)
    bkit.box_uv(obj, size=0.05)
    bkit.shade_smooth(obj)
    # bare copper core poking out of the cut end
    tangent = (pts[-1] - pts[-2]).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(tangent).to_matrix().to_4x4()
    centre = pts[-1] + tangent * 0.002
    add_cone(stubs, 0.0022, 0.008, 8, Matrix.Translation(centre) @ rot)
    return obj


def make_fibres():
    bm = bmesh.new()
    for _ in range(5):
        ang = random.uniform(0, TAU)
        rad = random.uniform(0.045, 0.080)
        z = random.uniform(0.10, 0.20)
        rot = Matrix.Rotation(random.uniform(0, TAU), 4, "X") @ Matrix.Rotation(random.uniform(0, TAU), 4, "Y")
        loc = Matrix.Translation((rad * math.cos(ang), rad * math.sin(ang), z))
        add_cone(bm, 0.0011, random.uniform(0.03, 0.06), 5, loc @ rot)
    return bm


def make_orb(mat):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.04,
                               matrix=Matrix.Translation((0, 0, 0.15)))
    return part("orb", bm, mat, uv_size=0.1)


def make_label(mat, r=0.1150, phi_max=0.46, cols=9, z0=0.135, z1=0.265):
    bm = bmesh.new()
    rows = 2
    grid = []
    for j in range(rows):
        z = z0 + (z1 - z0) * j
        row = []
        for i in range(cols):
            phi = -phi_max + 2 * phi_max * i / (cols - 1)
            rr = r
            # peeling corners lift off the glass
            if (i == 0 and j == 0) or (i == cols - 1 and j == rows - 1):
                rr += 0.0025
            row.append(bm.verts.new((rr * math.sin(phi), -rr * math.cos(phi), z)))
        grid.append(row)
    for j in range(rows - 1):
        for i in range(cols - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return part("label", bm, mat, uv_size=0.1)


# ---------------------------------------------------------------- build

def build():
    bkit.reset_scene()
    bkit.light_studio()

    brass = brass_material()
    cloth = cloth_material()
    copper = bkit.procedural_material("copper", base=(0.80, 0.45, 0.25), variation=0.12,
                                      roughness=0.35, metallic=1.0, scale=8, bump=0, grime=0.1)
    liquid_mat = bkit.procedural_material("liquid", base=(0.30, 0.32, 0.15), variation=0.25,
                                          roughness=0.18, metallic=0.0, scale=3, bump=0,
                                          grime=0.2)
    orb_mat = bkit.procedural_material("orb", base=(1.0, 0.86, 0.55), variation=0.08,
                                       roughness=0.3, metallic=0.0, scale=5, bump=0, grime=0)
    fibre_mat = bkit.procedural_material("fibre", base=(0.80, 0.74, 0.56), variation=0.15,
                                         roughness=0.9, metallic=0.0, scale=20, bump=0, grime=0.25)

    objs = []
    objs.append(make_glass())
    objs.append(make_lid(brass))
    objs.append(make_terminal(brass))

    stubs = bmesh.new()
    for name, s in (("wire_left", -1), ("wire_right", 1)):
        objs.append(make_wire(name, s, cloth, stubs))
    # build copper stubs as one part
    copper_obj = mesh_obj("copper_tips", stubs)
    copper_obj.data.materials.append(copper)
    bkit.box_uv(copper_obj, size=0.02)
    objs.append(copper_obj)

    liquid = bmesh.new()
    add_cone(liquid, 0.100, 0.26, 20, Matrix.Translation((0, 0, 0.15)))
    liquid_obj = part("liquid", liquid, liquid_mat, uv_size=0.2)
    objs.append(liquid_obj)

    lnt, lb = bkit._nodes(liquid_mat)
    lb.inputs["Transmission Weight"].default_value = 0.9
    lvec, _ = obj_xyz(lnt)
    dist = lnt.nodes.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    lnt.links.new(lvec, dist.inputs[0])
    dist.inputs[1].default_value = (0, 0, 0.15)
    overlay(liquid_mat, remap(lnt, sock(dist, "Value", out=True), 0.035, 0.10, 1.0, 0.0),
            color=(0.70, 0.64, 0.32))
    ob = bkit._nodes(orb_mat)[1]
    ob.inputs["Emission Color"].default_value = (1.0, 0.75, 0.35, 1)
    ob.inputs["Emission Strength"].default_value = 4.0
    objs.append(make_orb(orb_mat))
    fibres_obj = part("fibres", make_fibres(), fibre_mat, uv_size=0.05)
    objs.append(fibres_obj)
    objs.append(make_label(paper_label("label_paper")))

    for o in objs:
        print("PART", o.name, bkit.tri_count(o))

    joined = bkit.join(objs, ASSET)
    bkit.decimate(joined, TRI_BUDGET)
    bkit.origin_to_bottom(joined)
    return joined


def main():
    import os
    os.makedirs(BAKE_DIR, exist_ok=True)
    obj = build()

    # 1. live preview, before baking
    bkit.render_views(PREVIEW)

    # 2. remember which faces need transmissive materials after the bake
    me = obj.data
    names = {i: m.name for i, m in enumerate(me.materials) if m}
    glass_faces = {p.index for p in me.polygons if names.get(p.material_index) == "glass_dirty"}
    liquid_faces = {p.index for p in me.polygons if names.get(p.material_index) == "liquid"}
    orb_faces = {p.index for p in me.polygons if names.get(p.material_index) == "orb"}
    print("BKIT faces glass", len(glass_faces), "liquid", len(liquid_faces))

    metal_faces = {p.index for p in me.polygons if names.get(p.material_index) in ("brass", "copper")}
    # the DIFFUSE colour pass returns black for metallic or transmissive surfaces, so
    # bake them as plain dielectrics; metal and transmission go back on afterwards
    for m in me.materials:
        b = bkit._nodes(m)[1]
        tw = b.inputs["Transmission Weight"]
        for lk in list(tw.links):
            m.node_tree.links.remove(lk)
        tw.default_value = 0.0
        if m.name in ("brass", "copper"):
            b.inputs["Metallic"].default_value = 0.0

    # 3. bake everything to one texture set
    bkit.bake_to_textures(obj, BAKE_DIR, size=1024)

    # 4. the bake drops transmission, so restore it on the glass and liquid faces only,
    #    sampling the baked colour so grime and tint survive
    color_img = bpy.data.images[f"{obj.name}_color"]

    def transmissive(name, roughness, transmission=1.0, metallic=0.0, dusty=False):
        mat = bpy.data.materials.new(name)
        nt, bsdf = bkit._nodes(mat)
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = color_img
        nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Transmission Weight"].default_value = transmission
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["IOR"].default_value = 1.5
        if dusty:
            rt = nt.nodes.new("ShaderNodeTexImage")
            rt.image = bpy.data.images[f"{obj.name}_roughness"]
            nt.links.new(uv.outputs["UV"], rt.inputs["Vector"])
            nt.links.new(rt.outputs["Color"], bsdf.inputs["Roughness"])
            nt.links.new(remap(nt, rt.outputs["Color"], 0.35, 0.8, 1.0, 0.15),
                         bsdf.inputs["Transmission Weight"])
        if metallic:
            rt = nt.nodes.new("ShaderNodeTexImage")
            rt.image = bpy.data.images[f"{obj.name}_roughness"]
            nt.links.new(uv.outputs["UV"], rt.inputs["Vector"])
            nt.links.new(rt.outputs["Color"], bsdf.inputs["Roughness"])
            nm_t = nt.nodes.new("ShaderNodeTexImage")
            nm_t.image = bpy.data.images[f"{obj.name}_normal"]
            nt.links.new(uv.outputs["UV"], nm_t.inputs["Vector"])
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.uv_map = "UVMap"
            nt.links.new(nm_t.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        return mat

    bkit.assign(obj, transmissive("brass_metal", 0.4, transmission=0.0, metallic=0.85),
                faces=metal_faces)
    bkit.assign(obj, transmissive("glass_transmission", 0.05, dusty=True), faces=glass_faces)
    bkit.assign(obj, transmissive("liquid_transmission", 0.12, transmission=0.92), faces=liquid_faces)

    glow = bpy.data.materials.new("orb_glow")
    gb = bkit._nodes(glow)[1]
    gb.inputs["Base Color"].default_value = (1.0, 0.78, 0.40, 1)
    gb.inputs["Emission Color"].default_value = (1.0, 0.74, 0.35, 1)
    gb.inputs["Emission Strength"].default_value = 2.5
    gb.inputs["Roughness"].default_value = 0.35
    bkit.assign(obj, glow, faces=orb_faces)

    report = bkit.report([obj])
    print("BLENDER_VERTS", len(obj.data.vertices))

    # 5. preview after baking, so what is checked is what ships
    bkit.render_views(BAKED_PREVIEW)

    bkit.export_glb(GLB, [obj], image_format="JPEG")
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BKIT_DONE", GLB)


main()
