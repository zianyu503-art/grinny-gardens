"""Shared helpers for the Chapter 3 humanoid ghosts (twins, ticket, shadow).

Used only by twins_build.py, ticket_build.py and shadow_build.py. Every helper takes the rig
(`arm`) explicitly. Parts are rigid pieces (one bone each, via a vertex group) or dress shells
(which keep the body's weights), joined into one skinned mesh per ghost. Emissive parts stay as a
separate unbaked mesh skinned to the same rig.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
sys.path.insert(0, "/Users/alex/恐怖遊戲2/blender")
import lib  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
RENDERS = os.path.join(ROOT, "renders")
os.makedirs(RENDERS, exist_ok=True)


# ---------------------------------------------------------------- scene and parts
def skin_on(o, arm):
    if not any(m.type == "ARMATURE" for m in o.modifiers):
        m = o.modifiers.new("Armature", "ARMATURE")
        m.object = arm
    return o


def tag(o, bone, m, arm):
    """Rigid part: every vertex follows one bone. box_uv keeps UVs for the bake."""
    o.data.materials.clear()
    o.data.materials.append(m)
    bkit.box_uv(o, size=0.5)
    g = o.vertex_groups.new(name=bone)
    g.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    return skin_on(o, arm)


def finish(o, scale=(1, 1, 1), rot=(0, 0, 0)):
    o.rotation_euler = rot
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bkit.shade_smooth(o)
    return o


def sphere(name, loc, r, scale, bone, m, arm, segs=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=r, location=loc)
    o = bpy.context.active_object
    o.name = o.data.name = name
    finish(o, scale)
    return tag(o, bone, m, arm)


def cyl(name, loc, r, depth, bone, m, arm, scale=(1, 1, 1), rot=(0, 0, 0), verts=28):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = o.data.name = name
    finish(o, scale, rot)
    return tag(o, bone, m, arm)


def cube(name, loc, scale, bone, m, arm, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = o.data.name = name
    finish(o, scale, rot)
    return tag(o, bone, m, arm)


def rod(name, a, b, r, r2, bone, m, arm):
    o = lib.seg(name, a, b, r, None, None, r2=r2, verts=12)
    return tag(o, bone, m, arm)


def torus(name, loc, major, minor, scale, rot, bone, m, arm):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48,
                                     minor_segments=8, location=loc)
    o = bpy.context.active_object
    o.name = o.data.name = name
    finish(o, scale, rot)
    return tag(o, bone, m, arm)


def hair_cap(name, centre, radii, hairline, bone, m, arm, lift=0.0):
    """UV sphere shaped into a cap: faces below the hairline are removed.

    hairline(x) -> z of the hairline at lateral position x (an arch, so it sits lower at the
    centre of the forehead than at the temples)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=18, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
        v.co += Vector(centre) + Vector((0, 0, lift))
    kill = [f for f in bm.faces if f.calc_center_median().z < hairline(f.calc_center_median().x)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    bkit.shade_smooth(o)
    bkit.box_uv(o, size=0.5)
    return tag(o, bone, m, arm)


# ---------------------------------------------------------------- measurements
def head_frame(arm, body):
    """Front plane, centre and half-size of the head, from the body's vertices above the head bone."""
    hb = arm.data.bones["head"]
    z0, z1 = hb.head_local.z, hb.tail_local.z
    pts = [v.co for v in body.data.vertices if v.co.z > z0]
    ymin = min(p.y for p in pts)
    ymax = max(p.y for p in pts)
    xr = max(abs(p.x) for p in pts)
    cz = (z0 + z1) / 2
    return {"front": ymin, "back": ymax, "cy": (ymin + ymax) / 2, "cz": cz, "top": z1,
            "xr": xr, "yr": (ymax - ymin) / 2, "hh": z1 - z0, "z0": z0}


def front_y(body, zlo, zhi):
    pts = [v.co for v in body.data.vertices if zlo < v.co.z < zhi]
    return min(p.y for p in pts), max(p.y for p in pts)


# ---------------------------------------------------------------- pose
def reset(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def bone_pos(arm, name, end="tail"):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if end == "tail" else pb.head)


def signs(arm):
    """HOLD_Z: the z angle that holds the right arm out to the side; FWD_ARM and FWD_SPINE: the
    sign that swings the right arm or the spine forward (towards -y)."""
    xs = {}
    for z in (70, -70):
        reset(arm)
        bkit.pose(arm, {"upper_arm.R": (0, 0, z)})
        xs[z] = bone_pos(arm, "hand.R").x
    hold = min(xs, key=xs.get)
    reset(arm)
    bkit.pose(arm, {"upper_arm.R": (0, 0, hold)})
    y_rest = bone_pos(arm, "hand.R").y
    bkit.pose(arm, {"upper_arm.R": (60, 0, hold)})
    fwd_arm = 1 if bone_pos(arm, "hand.R").y < y_rest else -1
    reset(arm)
    y_head = bone_pos(arm, "head").y
    bkit.pose(arm, {"spine": (25, 0, 0)})
    fwd_spine = 1 if bone_pos(arm, "head").y < y_head else -1
    reset(arm)
    return hold, fwd_arm, fwd_spine


def set_clip(arm, name, keys):
    """keys: {bone: [(frame, (rx, ry, rz)[, (lx, ly, lz)]), ...]} -> NLA track called `name`."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for bone, frames in keys.items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "XYZ"
        for entry in frames:
            f, rot = entry[0], entry[1]
            pb.rotation_euler = tuple(math.radians(a) for a in rot)
            pb.keyframe_insert("rotation_euler", frame=f)
            if len(entry) > 2:
                pb.location = entry[2]
                pb.keyframe_insert("location", frame=f)
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    arm.animation_data.action = None
    reset(arm)
    print("BKIT_CLIP", name)


def loop_clip(arm, name, period, fn, steps=12):
    """fn(t), t in [0, 1): {bone: (rx, ry, rz)}, the same bones every call."""
    keys = {}
    for i in range(steps + 1):
        for b, r in fn(i / steps).items():
            keys.setdefault(b, []).append((1 + round(period * i / steps), r))
    set_clip(arm, name, keys)


# ---------------------------------------------------------------- materials
def scan_mat(name, asset, scale=2.0, tint=(1, 1, 1), dirt="#3a2e22", dirt_amt=0.35, metal=0.0,
             rough=None, sat=1.0, val=1.0):
    """Real Poly Haven scan (1k) with tint, a dirt and stain layer from noise, and normal map.

    scale: texture repeats per metre (object space). rough: optional float to override the scan's
    roughness (e.g. patent gloss). dirt_amt: how strongly the grime multiplies in."""
    maps = bkit.polyhaven_texture(asset, "1k")
    M = lib.Mat(name)
    N, L = M.nt.nodes, M.nt.links
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(slot, cs):
        n = N.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(maps[slot], check_existing=True)
        n.image.colorspace_settings.name = cs
        L.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    col = img("color", "sRGB")
    src = col.outputs["Color"]
    if sat != 1.0 or val != 1.0:  # optional desaturation / brightness of the scan before tinting
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = sat
        hs.inputs["Value"].default_value = val
        L.new(src, hs.inputs["Color"])
        src = hs.outputs["Color"]
    tinted = M.mix(1.0, src, tint, "MULTIPLY")
    grime = M.ramp(M.noise(0.7, 5, 0.55, distortion=0.6), [(0.35, "#ffffff"), (0.7, dirt)])
    dirty = M.mix(dirt_amt, tinted, grime, "MULTIPLY")
    M.set(color=dirty, metal=metal)
    if rough is None and "roughness" in maps:
        M.set(rough=img("roughness", "Non-Color").outputs["Color"])
    else:
        M.set(rough=0.6 if rough is None else rough)
    if "normal" in maps:
        nm = N.new("ShaderNodeNormalMap")
        L.new(img("normal", "Non-Color").outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs["Normal"], M.bsdf.inputs["Normal"])
    return M.m


def fix_metals(mats):
    """Cycles bakes the colour of fully metallic surfaces as black: lower Metallic before the bake."""
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if not bsdf.inputs["Metallic"].is_linked:
            bsdf.inputs["Metallic"].default_value = min(bsdf.inputs["Metallic"].default_value, 0.35)


# ---------------------------------------------------------------- render and export
def render_views(path, size=400, views=("front", "side", "back", "detail")):
    bkit.light_studio()
    bkit.render_views(path, size=size, samples=24, views=views)


def render_closeup(path, target, direction, dist=0.7, size=520):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = False
    d = Vector(direction).normalized()
    cam = lib.camera(tuple(Vector(target) + d * dist), tuple(target), lens=70)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print("RENDERED", path)


def export_glb(glb, arm, objs):
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in [arm] + objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_apply=False,
                              export_lights=False, export_image_format="JPEG", export_jpeg_quality=85,
                              export_animation_mode="NLA_TRACKS")
    print("BKIT_EXPORT", glb, os.path.getsize(glb) // 1024, "KB")
    print("BKIT_NLA", [t.name for t in arm.animation_data.nla_tracks])


def rest_render(arm, path, size=400):
    """Rest pose for the shipped render: mutes the NLA tracks so the rig shows its bind pose."""
    for t in arm.animation_data.nla_tracks:
        t.mute = True
    reset(arm)
    render_views(path, size=size)
