"""Turn a high-detail Blender build into a realtime game asset.

join -> decimate -> UV unwrap -> bake procedural colour to a texture -> (rig + animate) -> GLB

usage: blender -b --factory-startup --python blender/game_export.py -- <creature|props> [name...]
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

os.environ["NO_HAIR"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

OUT = os.path.join(lib.ROOT, "public", "models")
TEX = os.path.join(lib.ROOT, "blender", "bake")


def mesh_objects():
    return [o for o in bpy.data.objects if o.type in ("MESH", "CURVE", "FONT", "META") and not o.hide_render]


def flatten_to_one(name):
    """Apply modifiers/transforms of every mesh and join them into a single object."""
    objs = mesh_objects()
    for o in objs:
        lib.select_only(o)
        if o.type != "MESH" or o.modifiers:
            bpy.ops.object.convert(target="MESH")
    bpy.ops.object.select_all(action="DESELECT")
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
    for o in objs:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in list(bpy.data.objects):
        if o.type == "EMPTY" or (o.type == "MESH" and o.hide_render):
            bpy.data.objects.remove(o, do_unlink=True)
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    return o


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def decimate(o, target):
    n = tri_count(o)
    if n > target:
        d = o.modifiers.new("Dec", "DECIMATE")
        d.ratio = target / n
        d.use_collapse_triangulate = True
        lib.apply_mods(o)
    print("TRIS", o.name, n, "->", tri_count(o))


def unwrap(o):
    lib.select_only(o)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake_color(o, size, name):
    """Bake every material's base colour (procedural or not) into one image."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.cycles.samples = 4
    img = bpy.data.images.new(name + "_col", size, size)
    for slot in o.material_slots:
        m = slot.material
        if not m:
            continue
        nt = m.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
    lib.select_only(o)
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True)
    os.makedirs(TEX, exist_ok=True)
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = "PNG"
    img.save()
    return img


def gloss_map(o):
    """Per-material roughness/emission kept as vertex colour (R=rough, G=metal, B=emit)."""
    me = o.data
    attr = me.color_attributes.new("Surf", "BYTE_COLOR", "CORNER")
    vals = []
    for slot in o.material_slots:
        m = slot.material
        rough, metal, emit = 0.8, 0.0, 0.0
        if m:
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                if not b.inputs["Roughness"].is_linked:
                    rough = b.inputs["Roughness"].default_value
                if not b.inputs["Metallic"].is_linked:
                    metal = b.inputs["Metallic"].default_value
                else:
                    metal = 0.6
                if b.inputs["Emission Strength"].default_value > 0.01:
                    emit = 1.0
                if b.inputs["Coat Weight"].default_value > 0.5:
                    rough = min(rough, 0.25)
        vals.append((rough, metal, emit))
    for poly in me.polygons:
        r, g, b = vals[poly.material_index] if poly.material_index < len(vals) else (0.8, 0, 0)
        for li in poly.loop_indices:
            attr.data[li].color = (r, g, b, 1.0)


def single_material(o, img, name):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    o.data.materials.clear()
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.material_index = 0


# --------------------------------------------------------------------------- rigging
def rig(o, bones, radii):
    """bones: [(name, head, tail, parent)] in Blender space. Weights = nearest bone segments."""
    arm_d = bpy.data.armatures.new(o.name + "Rig")
    arm = lib.link_obj(bpy.data.objects.new(o.name + "Rig", arm_d))
    lib.select_only(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, parent in bones:
        eb = arm_d.edit_bones.new(name)
        eb.head = h
        eb.tail = t
        eb.roll = 0.0
        if parent:
            eb.parent = arm_d.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")

    segs = [(n, Vector(h), Vector(t)) for n, h, t, _ in bones]
    groups = {n: o.vertex_groups.new(name=n) for n, *_ in bones}
    for v in o.data.vertices:
        scores = []
        for n, a, b in segs:
            ab = b - a
            k = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-9)))
            d = (v.co - (a + ab * k)).length / radii[n]
            scores.append((d, n))
        scores.sort()
        (d0, n0), (d1, n1) = scores[0], scores[1]
        w0 = 1.0 / (d0 + 1e-3) ** 6
        w1 = 1.0 / (d1 + 1e-3) ** 6
        s = w0 + w1
        groups[n0].add([v.index], w0 / s, "REPLACE")
        if w1 / s > 0.02:
            groups[n1].add([v.index], w1 / s, "REPLACE")
    o.parent = arm
    mod = o.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return arm


def animate(arm, name, length, keys):
    """keys: {bone: [(frame, (rx, ry, rz) degrees, loc or None)]}"""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for bone, frames in keys.items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "XYZ"
        for f, rot, loc in frames:
            pb.rotation_euler = tuple(math.radians(a) for a in rot)
            pb.keyframe_insert("rotation_euler", frame=f)
            if loc is not None:
                pb.location = loc
                pb.keyframe_insert("location", frame=f)
    # push to NLA so every action gets exported
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)


def cyc(period, fn, steps=8):
    """Sample a periodic function into keyframes over one cycle."""
    return [(1 + period * i / steps, *fn(i / steps)) for i in range(steps + 1)]


def S(t, amp, phase=0.0):
    return amp * math.sin(2 * math.pi * (t + phase))


# --------------------------------------------------------------------------- per-asset rigs
def rig_grinny(o):
    bones = [
        ("Hips", (0, 0, 1.05), (0, 0, 1.5), None),
        ("Spine", (0, 0, 1.5), (0, 0.03, 2.3), "Hips"),
        ("Head", (0, -0.12, 2.5), (0, -0.35, 3.3), "Spine"),
        ("ArmL", (-0.46, 0.05, 2.28), (-0.86, -0.04, 1.58), "Spine"),
        ("ForeL", (-0.86, -0.04, 1.58), (-0.93, -0.3, 0.45), "ArmL"),
        ("ArmR", (0.46, 0.05, 2.26), (0.92, -0.1, 1.48), "Spine"),
        ("ForeR", (0.92, -0.1, 1.48), (0.96, -0.45, 0.35), "ArmR"),
        ("LegL", (-0.3, 0, 1.0), (-0.34, -0.08, 0.52), "Hips"),
        ("ShinL", (-0.34, -0.08, 0.52), (-0.34, -0.45, 0.06), "LegL"),
        ("LegR", (0.3, 0, 1.0), (0.34, -0.08, 0.52), "Hips"),
        ("ShinR", (0.34, -0.08, 0.52), (0.34, -0.45, 0.06), "LegR"),
    ]
    radii = {"Hips": 0.5, "Spine": 0.62, "Head": 0.55, "ArmL": 0.24, "ForeL": 0.22, "ArmR": 0.24,
             "ForeR": 0.22, "LegL": 0.32, "ShinL": 0.26, "LegR": 0.32, "ShinR": 0.26}
    arm = rig(o, bones, radii)
    # Run: 20 frame lumbering gallop, arms dragging and flailing
    run = {
        "Hips": cyc(20, lambda t: ((-12, S(t, 6), 0), (0, abs(S(t, 0.12, 0.25)), 0)), 8),
        "Spine": cyc(20, lambda t: ((-14 + S(t, 4, 0.1), 0, S(t, 7)), None)),
        "Head": cyc(20, lambda t: ((10 + S(t, 8, 0.3), S(t, 10), -12 + S(t, 6)), None)),
        "LegL": cyc(20, lambda t: ((S(t, 38), 0, 0), None)),
        "ShinL": cyc(20, lambda t: ((max(0, S(t, -55, 0.15)), 0, 0), None)),
        "LegR": cyc(20, lambda t: ((S(t, -38), 0, 0), None)),
        "ShinR": cyc(20, lambda t: ((max(0, S(t, 55, 0.15)), 0, 0), None)),
        "ArmL": cyc(20, lambda t: ((S(t, -45) - 25, 0, -10), None)),
        "ForeL": cyc(20, lambda t: ((S(t, -25, 0.2) - 30, 0, 0), None)),
        "ArmR": cyc(20, lambda t: ((S(t, 45) - 25, 0, 10), None)),
        "ForeR": cyc(20, lambda t: ((S(t, 25, 0.2) - 30, 0, 0), None)),
    }
    animate(arm, "Run", 20, run)
    idle = {
        "Spine": cyc(80, lambda t: ((S(t, 2), 0, 0), None)),
        "Head": cyc(80, lambda t: ((S(t, 4), S(t, 6, 0.2), S(t, 12, 0.1)), None), 12),
        "ArmL": cyc(80, lambda t: ((S(t, 3), 0, S(t, 2)), None)),
        "ArmR": cyc(80, lambda t: ((S(t, -3), 0, S(t, -2)), None)),
    }
    animate(arm, "Idle", 80, idle)
    lunge = {
        "Spine": [(1, (0, 0, 0), None), (8, (-35, 0, 0), None), (24, (-35, 0, 0), None)],
        "Head": [(1, (0, 0, 0), None), (8, (25, 0, -20), None), (24, (30, 5, -25), None)],
        "ArmL": [(1, (0, 0, 0), None), (8, (-110, 0, -30), None), (24, (-105, 0, -25), None)],
        "ArmR": [(1, (0, 0, 0), None), (8, (-110, 0, 30), None), (24, (-115, 0, 35), None)],
        "ForeL": [(1, (0, 0, 0), None), (8, (-20, 0, 0), None)],
        "ForeR": [(1, (0, 0, 0), None), (8, (-20, 0, 0), None)],
    }
    animate(arm, "Attack", 24, lunge)
    return arm


def rig_hornman(o):
    bones = [
        ("Hips", (0, 0.02, 1.15), (0, 0.03, 1.5), None),
        ("Spine", (0, 0.03, 1.5), (0, -0.05, 2.0), "Hips"),
        ("Head", (0, -0.13, 2.1), (0, -0.9, 2.55), "Spine"),
        ("ArmL", (-0.25, -0.03, 2.03), (-0.38, -0.13, 1.48), "Spine"),
        ("ForeL", (-0.38, -0.13, 1.48), (-0.46, -0.4, 0.55), "ArmL"),
        ("ArmR", (0.25, -0.03, 2.03), (0.38, -0.13, 1.48), "Spine"),
        ("ForeR", (0.38, -0.13, 1.48), (0.46, -0.4, 0.55), "ArmR"),
        ("LegL", (-0.11, 0.02, 1.15), (-0.13, -0.08, 0.68), "Hips"),
        ("ShinL", (-0.13, -0.08, 0.68), (-0.14, -0.4, 0.05), "LegL"),
        ("LegR", (0.11, 0.02, 1.15), (0.13, -0.08, 0.68), "Hips"),
        ("ShinR", (0.13, -0.08, 0.68), (0.14, -0.4, 0.05), "LegR"),
    ]
    radii = {"Hips": 0.2, "Spine": 0.25, "Head": 0.45, "ArmL": 0.13, "ForeL": 0.13, "ArmR": 0.13,
             "ForeR": 0.13, "LegL": 0.13, "ShinL": 0.14, "LegR": 0.13, "ShinR": 0.14}
    arm = rig(o, bones, radii)
    walk = {
        "Hips": cyc(48, lambda t: ((0, S(t, 4), 0), (0, abs(S(t, 0.05)), 0))),
        "Spine": cyc(48, lambda t: ((-8, 0, S(t, 6)), None)),
        "Head": cyc(48, lambda t: ((S(t, 6, 0.25), 0, S(t, 14, 0.1)), None), 12),
        "LegL": cyc(48, lambda t: ((S(t, 28), 0, 0), None)),
        "ShinL": cyc(48, lambda t: ((max(0, S(t, -40, 0.15)), 0, 0), None)),
        "LegR": cyc(48, lambda t: ((S(t, -28), 0, 0), None)),
        "ShinR": cyc(48, lambda t: ((max(0, S(t, 40, 0.15)), 0, 0), None)),
        "ArmL": cyc(48, lambda t: ((S(t, -12), 0, -4), None)),
        "ForeL": cyc(48, lambda t: ((-10 + S(t, -8, 0.2), 0, 0), None)),
        "ArmR": cyc(48, lambda t: ((S(t, 12), 0, 4), None)),
        "ForeR": cyc(48, lambda t: ((-10 + S(t, 8, 0.2), 0, 0), None)),
    }
    animate(arm, "Walk", 48, walk)
    listen = {
        "Spine": cyc(90, lambda t: ((-12 + S(t, 3), 0, 0), None)),
        "Head": [(1, (0, 0, 0), None), (15, (10, 0, 35), None), (40, (12, 5, 38), None), (55, (5, 0, -30), None),
                 (80, (8, -5, -34), None), (91, (0, 0, 0), None)],
        "ArmL": cyc(90, lambda t: ((-20 + S(t, 5), 0, 0), None)),
        "ForeL": cyc(90, lambda t: ((-40 + S(t, 8, 0.3), 0, 0), None)),
        "ArmR": cyc(90, lambda t: ((-20 + S(t, -5), 0, 0), None)),
        "ForeR": cyc(90, lambda t: ((-40 + S(t, -8, 0.3), 0, 0), None)),
    }
    animate(arm, "Listen", 90, listen)
    lunge = {
        "Spine": [(1, (0, 0, 0), None), (6, (-40, 0, 0), None), (20, (-40, 0, 0), None)],
        "Head": [(1, (0, 0, 0), None), (6, (-30, 0, 0), None), (20, (-25, 0, 8), None)],
        "ArmL": [(1, (0, 0, 0), None), (6, (-100, 0, -20), None)],
        "ArmR": [(1, (0, 0, 0), None), (6, (-100, 0, 20), None)],
    }
    animate(arm, "Attack", 20, lunge)
    return arm


ASSETS = {
    # name: (module builder, target tris, texture size, rig fn)
    "grinny": ("creature_grinny", 26000, 2048, rig_grinny),
    "hornman": ("creature_hornman", 22000, 2048, rig_hornman),
    "horse": ("creature_horse", 18000, 2048, None),
    "director": ("creature_director", 40000, 2048, None),
}


def export(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_apply=False, export_lights=False, export_image_format="JPEG",
                              export_jpeg_quality=88, export_animation_mode="NLA_TRACKS",
                              export_attributes=True)
    print("EXPORTED", path, os.path.getsize(path) // 1024, "KB")


def export_creature(name):
    mod_name, tris, size, rig_fn = ASSETS[name]
    lib.reset()
    importlib.import_module(mod_name).build()
    o = flatten_to_one(name)
    decimate(o, tris)
    unwrap(o)
    gloss_map(o)
    img = bake_color(o, size, name)
    single_material(o, img, name + "_mat")
    objs = [o]
    if rig_fn:
        objs.append(rig_fn(o))
    export(os.path.join(OUT, name + ".glb"), objs)


def export_props(only=None):
    import props
    for pname, builder, tris, size in props.PROPS:
        if only and pname not in only:
            continue
        lib.reset()
        builder()
        o = flatten_parts(pname)
        objs = []
        for part in o:
            decimate(part, tris)
            unwrap(part)
            gloss_map(part)
            img = bake_color(part, size, "%s_%s" % (pname, part.name))
            single_material(part, img, part.name + "_mat")
            objs.append(part)
        export(os.path.join(OUT, pname + ".glb"), objs)


def flatten_parts(pname):
    """Props may contain named parts (empties whose name starts with 'Part_'): each becomes its own mesh."""
    part_roots = [o for o in bpy.data.objects if o.type == "EMPTY" and o.name.startswith("Part_")]
    groups = {}
    for o in [o for o in bpy.data.objects if o.type in ("MESH", "CURVE", "FONT") and not o.hide_render]:
        p, owner = o, "Part_Main"
        while p is not None:
            if p in part_roots:
                owner = p.name
                break
            p = p.parent
        groups.setdefault(owner, []).append(o)
    pivots = {r.name: r.matrix_world.translation.copy() for r in part_roots}
    pivots["Part_Main"] = Vector((0, 0, 0))
    results = []
    for owner, members in groups.items():
        for o in members:
            lib.select_only(o)
            if o.type != "MESH" or o.modifiers:
                bpy.ops.object.convert(target="MESH")
        members = [bpy.data.objects[m.name] if m.name in bpy.data.objects else m for m in members]
        bpy.ops.object.select_all(action="DESELECT")
        for o in members:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
            o.select_set(True)
        bpy.context.view_layer.objects.active = members[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if len(members) > 1:
            bpy.ops.object.join()
        j = bpy.context.active_object
        j.name = owner[5:]
        # move origin to the part pivot so the game can rotate it
        piv = pivots[owner]
        for v in j.data.vertices:
            v.co -= piv
        j.location = piv
        results.append(j)
    for o in list(bpy.data.objects):
        if o.type == "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)
    return results


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    kind, names = args[0], args[1:]
    if kind == "props":
        export_props(names or None)
    else:
        for n in ([kind] + names):
            export_creature(n)
