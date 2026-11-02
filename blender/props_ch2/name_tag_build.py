"""name_tag: a 1996 Grinny Gardens staff name badge, dropped and left for 30 years.

Painted steel plate with a raised printed face, a yellow smiley logo, embossed text
("GRINNY GARDENS" / "MEI"), a slight bend, and a brass pin-back on the reverse.

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/props_ch2/name_tag_build.py

Units: metres. Z up, standing on its bottom edge at z=0, printed face toward -Y.
"""
import sys
import math
import os

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix  # noqa: E402
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
ASSET = "name_tag"
BAKE_DIR = f"{ROOT}/blender/bake/{ASSET}"
PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_preview.png"
BAKED_PREVIEW = f"{ROOT}/renders/ch2_{ASSET}_baked.png"
GLB = f"{ROOT}/public/models/{ASSET}.glb"
BLEND = f"{BAKE_DIR}/{ASSET}.blend"
TRI_BUDGET = 1500

W, T, H = 0.076, 0.0025, 0.028      # badge width (X), thickness (Y), height (Z)
FRONT = -T / 2
FACE_X = Matrix.Rotation(math.radians(90), 4, "X")  # +Z axis -> -Y (towards viewer)


def mesh_obj(name, bm, mat, uv=0.05):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bkit.box_uv(obj, size=uv)
    return obj


def box(name, size, loc, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return mesh_obj(name, bm, mat)


def disc(bm, r, depth, seg, x, z, y):
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r,
                                depth=depth)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, z)) @ FACE_X, verts=ret["verts"])


def text_obj(name, body, size, x, z, mat, bold=False):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = 0.00015
    cu.resolution_u = 2
    cu.align_x = "LEFT"
    cu.align_y = "CENTER"
    if bold:
        cu.offset = 0.00012  # thicker strokes for the embossed name
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.location = (x, FRONT - 0.0009, z)
    bkit.active(ob)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bkit.box_uv(ob, size=0.05)
    return ob


def build():
    bkit.reset_scene()
    bkit.light_studio()

    # Poly Haven scan for the pin-back and the steel plate edge
    metal_maps = bkit.polyhaven_texture("rusty_metal_02", res="1k")
    brass = bkit.pbr_material("brass_pin", metal_maps, scale=20.0, tint=(0.42, 0.32, 0.17),
                              metallic=1.0, roughness_mult=1.4)
    pvec, _ = obj_xyz(brass.node_tree)
    overlay(brass, noise_mask(brass.node_tree, pvec, 300, 0.4, 0.7), color=(0.06, 0.05, 0.03),
            roughness=0.8)
    plate_mat = bkit.pbr_material("plate_paint", metal_maps, scale=12.0, tint=(0.40, 0.11, 0.09),
                                  metallic=0.0)
    face = bkit.procedural_material("face_print", base=(0.60, 0.50, 0.31), variation=0.3,
                                    roughness=0.6, scale=40, bump=0.06, grime=0.9)
    logo = bkit.procedural_material("logo_yellow", base=(0.64, 0.54, 0.28), variation=0.4,
                                    roughness=0.55, scale=50, bump=0.05, grime=0.8)
    ink = bkit.procedural_material("ink", base=(0.07, 0.06, 0.07), variation=0.3,
                                   roughness=0.6, scale=80, bump=0, grime=0)

    # paint chipped to bare steel along the edges, plus rub scratches
    nt = plate_mat.node_tree
    vec, xyz = obj_xyz(nt)
    dx = math_n(nt, "SUBTRACT", W / 2, math_n(nt, "ABSOLUTE", xyz[0]))
    dz = math_n(nt, "SUBTRACT", H / 2, math_n(nt, "ABSOLUTE", math_n(nt, "SUBTRACT", xyz[2], H / 2)))
    edge = remap(nt, math_n(nt, "MINIMUM", dx, dz), 0.0, 0.0018, 1.0, 0.0)
    chips = math_n(nt, "MULTIPLY", edge, noise_mask(nt, vec, 260, 0.48, 0.58), clamp=True)
    scratches = noise_mask(nt, vec, 6, 0.70, 0.715, stretch=(3.0, 3.0, 140.0))
    overlay(plate_mat, math_n(nt, "MAXIMUM", chips, scratches), color=(0.30, 0.29, 0.28),
            roughness=0.42)
    overlay(plate_mat, math_n(nt, "MULTIPLY", chips, noise_mask(nt, vec, 500, 0.5, 0.7)),
            color=(0.25, 0.11, 0.04), roughness=0.9)  # rust blooming in the chips

    # card: coffee/water stains and dirt worked into the edges
    nt = face.node_tree
    vec, xyz = obj_xyz(nt)
    overlay(face, noise_mask(nt, vec, 70, 0.52, 0.68), color=(0.40, 0.29, 0.14))
    cdx = math_n(nt, "SUBTRACT", (W - 0.006) / 2, math_n(nt, "ABSOLUTE", xyz[0]))
    cdz = math_n(nt, "SUBTRACT", (H - 0.006) / 2,
                 math_n(nt, "ABSOLUTE", math_n(nt, "SUBTRACT", xyz[2], H / 2)))
    overlay(face, remap(nt, math_n(nt, "MINIMUM", cdx, cdz), 0.0, 0.003, 0.85, 0.0),
            color=(0.24, 0.19, 0.11))

    # sun-faded smiley and rubbed-off ink
    nt = logo.node_tree
    vec, _ = obj_xyz(nt)
    overlay(logo, noise_mask(nt, vec, 150, 0.5, 0.8), color=(0.70, 0.62, 0.42), roughness=0.75)
    nt = ink.node_tree
    vec, _ = obj_xyz(nt)
    overlay(ink, noise_mask(nt, vec, 200, 0.5, 0.65), color=(0.36, 0.33, 0.29), roughness=0.8)

    objs = []
    # painted steel plate, slightly bent where it was stepped on
    plate = box("plate", (W, T, H), (0, 0, H / 2), plate_mat)
    sub = plate.modifiers.new("Cuts", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 2
    bkit.apply_all(plate)
    for v in plate.data.vertices:
        v.co.y += 0.7 * (v.co.x ** 2) - 0.03 * max(0.0, v.co.x - 0.02) * (v.co.z / H)
    bkit.harden(plate, width=0.0006, segments=2, angle=30)
    objs.append(plate)

    # raised printed face (a separate laminated card), corner lifting off
    card = box("card", (W - 0.006, 0.0006, H - 0.006), (0, FRONT - 0.0003, H / 2), face)
    sub = card.modifiers.new("Cuts", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 2
    bkit.apply_all(card)
    for v in card.data.vertices:
        v.co.y += 0.7 * (v.co.x ** 2)
        if v.co.x > 0.025 and v.co.z > H - 0.010:   # peeling top-right corner
            v.co.y -= 0.0012 * (v.co.x - 0.025) / 0.010
    objs.append(card)

    # smiley logo: yellow disc, two eyes and a grin
    lbm = bmesh.new()
    disc(lbm, 0.0085, 0.0004, 20, -0.0255, H / 2, FRONT - 0.0008 + 0.7 * 0.0255 ** 2)
    objs.append(mesh_obj("logo", lbm, logo))
    ibm = bmesh.new()
    y_ink = FRONT - 0.0011 + 0.7 * 0.0255 ** 2
    for ex in (-0.0285, -0.0225):
        disc(ibm, 0.0011, 0.0003, 8, ex, H / 2 + 0.0025, y_ink)
    # grin: an arc of quads
    rs, rl = 0.0042, 0.0055
    arc = []
    for k in range(9):
        a = math.radians(200 + 140 * k / 8)
        c, s = math.cos(a), math.sin(a)
        arc.append((ibm.verts.new((-0.0255 + rs * c, y_ink, H / 2 + 0.0005 + rs * s)),
                    ibm.verts.new((-0.0255 + rl * c, y_ink, H / 2 + 0.0005 + rl * s))))
    for (a0, a1), (b0, b1) in zip(arc, arc[1:]):
        ibm.faces.new((a0, b0, b1, a1))
    objs.append(mesh_obj("logo_ink", ibm, ink))

    objs.append(text_obj("brand", "GRINNY GARDENS", 0.0042, -0.0140, H / 2 + 0.0065, ink))
    objs.append(text_obj("name", "MEI", 0.0105, -0.0130, H / 2 - 0.0030, ink, bold=True))

    # pin-back on the reverse: base strip, hinge, pin and catch
    back = T / 2
    objs.append(box("pin_base", (0.050, 0.0006, 0.0050), (0, back + 0.0003, H * 0.62), brass))
    pbm = bmesh.new()
    rot_x = Matrix.Rotation(math.radians(90), 4, "Y")
    ret = bmesh.ops.create_cone(pbm, cap_ends=True, segments=6, radius1=0.0005,
                                radius2=0.0004, depth=0.044)
    bmesh.ops.transform(pbm, matrix=Matrix.Translation((0.001, back + 0.0018, H * 0.62)) @ rot_x,
                        verts=ret["verts"])
    for x in (-0.023, 0.023):  # hinge and catch
        r2 = bmesh.ops.create_cone(pbm, cap_ends=True, segments=8, radius1=0.0016,
                                   radius2=0.0016, depth=0.0028)
        bmesh.ops.transform(pbm, matrix=Matrix.Translation((x, back + 0.0014, H * 0.62)) @ rot_x,
                            verts=r2["verts"])
    objs.append(mesh_obj("pin", pbm, brass, uv=0.02))

    for o in objs:
        print("PART", o.name, bkit.tri_count(o))
    joined = bkit.join(objs, ASSET)
    bkit.decimate(joined, TRI_BUDGET)
    bkit.origin_to_bottom(joined)
    return joined


def main():
    os.makedirs(BAKE_DIR, exist_ok=True)
    obj = build()
    bkit.render_views(PREVIEW)

    me = obj.data
    names = {i: m.name for i, m in enumerate(me.materials) if m}
    metal_faces = {p.index for p in me.polygons if names.get(p.material_index) == "brass_pin"}
    # DIFFUSE colour bakes black for metallic=1, so bake the brass as a dielectric and
    # put metal back on those faces afterwards
    for m in me.materials:
        if m.name == "brass_pin":
            bkit._nodes(m)[1].inputs["Metallic"].default_value = 0.0

    bkit.bake_to_textures(obj, BAKE_DIR, size=1024)

    mat = bpy.data.materials.new("brass_metal")
    nt, bsdf = bkit._nodes(mat)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    for slot, sock in (("color", "Base Color"), ("roughness", "Roughness")):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images[f"{obj.name}_{slot}"]
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
        nt.links.new(t.outputs["Color"], bsdf.inputs[sock])
    bsdf.inputs["Metallic"].default_value = 1.0
    bkit.assign(obj, mat, faces=metal_faces)

    bkit.report([obj])
    bkit.render_views(BAKED_PREVIEW)
    bkit.export_glb(GLB, [obj], image_format="JPEG")
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BKIT_DONE", GLB)


main()
