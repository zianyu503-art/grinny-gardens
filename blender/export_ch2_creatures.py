"""Game-ready export of the chapter 2 creatures with the blender-modeling kit (bkit):
one mesh, decimated to a web budget, every material baked into one texture set
(plus an emission map for the glowing parts), exported to public/models/<name>.glb.

usage: blender -b --factory-startup --python blender/export_ch2_creatures.py -- seamstress giggler
"""
import os
import sys

import bpy

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUDGET = {"seamstress": 16000, "giggler": 12000}
TEX = 1024


# ---------------------------------------------------------------- rigs and animation (same tools as chapter 1)
sys.path.insert(0, HERE)
import game_export as ge  # noqa: E402
from mathutils import Vector  # noqa: E402
import math  # noqa: E402

cyc, S = ge.cyc, ge.S


def shear_blades(wrist, fwd, upv, op, length=0.78):
    """The two blade lines of a pair of shears as built in creature_seamstress.shears()."""
    fwd, upv = Vector(fwd).normalized(), Vector(upv).normalized()
    side = fwd.cross(upv).normalized()
    upv = side.cross(fwd).normalized()
    pivot = Vector(wrist) + fwd * 0.2
    out = []
    for ang in (op, -op):
        d = (fwd * math.cos(ang) + upv * math.sin(ang)).normalized()
        out.append((pivot, pivot + d * length))
    return out, side


def align_rolls(arm, axes):
    bkit.active(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, vec in axes.items():
        arm.data.edit_bones[name].align_roll(vec)
    bpy.ops.object.mode_set(mode="OBJECT")


def rig_seamstress(o, off):
    P = lambda *v: tuple(Vector(v) - off)  # noqa: E731
    (l1, l2), side_l = shear_blades((-0.62, -0.62, 2.62), (-0.15, -1, 0.35), (0, 0.2, 1), math.radians(22))
    (r1, r2), side_r = shear_blades((0.66, -0.55, 2.25), (0.12, -1, -0.15), (0, -0.1, 1), math.radians(8))
    bones = [
        ("Root", P(0, 0, 3.6), P(0, 0, 4.5), None),
        ("Body", P(0, 0, 3.55), P(0, 0, 1.0), "Root"),
        ("Skirt", P(0, 0, 1.85), P(0, 0, 0.5), "Body"),
        ("Head", P(0.03, -0.06, 3.0), P(0.03, -0.12, 3.3), "Body"),
        ("ArmL", P(-0.29, -0.01, 2.82), P(-0.5, -0.22, 2.55), "Body"),
        ("ForeL", P(-0.5, -0.22, 2.55), P(-0.62, -0.62, 2.62), "ArmL"),
        ("BladeL1", P(*l1[0]), P(*l1[1]), "ForeL"),
        ("BladeL2", P(*l2[0]), P(*l2[1]), "ForeL"),
        ("ArmR", P(0.29, -0.01, 2.82), P(0.55, -0.12, 2.42), "Body"),
        ("ForeR", P(0.55, -0.12, 2.42), P(0.66, -0.55, 2.25), "ArmR"),
        ("BladeR1", P(*r1[0]), P(*r1[1]), "ForeR"),
        ("BladeR2", P(*r2[0]), P(*r2[1]), "ForeR"),
        ("LowL", P(-0.18, -0.06, 2.36), P(-0.34, -0.48, 2.3), "Body"),
        ("LowR", P(0.18, -0.06, 2.36), P(0.3, -0.42, 2.05), "Body"),
    ]
    radii = {"Root": 0.5, "Body": 0.32, "Skirt": 0.55, "Head": 0.2, "ArmL": 0.07, "ForeL": 0.07,
             "BladeL1": 0.05, "BladeL2": 0.05, "ArmR": 0.07, "ForeR": 0.07, "BladeR1": 0.05, "BladeR2": 0.05,
             "LowL": 0.06, "LowR": 0.06}
    arm = ge.rig(o, bones, radii)
    align_rolls(arm, {"BladeL1": side_l, "BladeL2": side_l, "BladeR1": side_r, "BladeR2": side_r})

    def snap(open_, a_l=22, a_r=8):
        """Blade rotations about the screw: open_=0 closed, 1 as modelled, >1 wider."""
        return {"BladeL1": (0, 0, a_l * (open_ - 1)), "BladeL2": (0, 0, -a_l * (open_ - 1)),
                "BladeR1": (0, 0, a_r * (open_ - 1) * 2.5), "BladeR2": (0, 0, -a_r * (open_ - 1) * 2.5)}

    def blades(period, fn, steps=8):
        keys = {b: [] for b in ("BladeL1", "BladeL2", "BladeR1", "BladeR2")}
        for i in range(steps + 1):
            t = i / steps
            for b, rot in snap(fn(t)).items():
                keys[b].append((1 + period * t, rot, None))
        return keys

    # Idle: hangs and turns slowly on the hook, head twitching, blades idly working
    idle = {
        "Body": cyc(96, lambda t: ((S(t, 3), S(t, 6, 0.2), S(t, 2.5, 0.1)), None), 12),
        "Skirt": cyc(96, lambda t: ((S(t, 4, 0.15), 0, S(t, 3, 0.3)), None), 12),
        "Head": [(1, (0, 0, 0), None), (30, (0, 0, 0), None), (33, (8, 0, -14), None), (60, (8, 0, -14), None),
                 (63, (-4, 0, 10), None), (97, (0, 0, 0), None)],
        "ArmL": cyc(96, lambda t: ((S(t, 4), 0, S(t, 3, 0.3)), None)),
        "ArmR": cyc(96, lambda t: ((S(t, -4), 0, S(t, -3, 0.3)), None)),
        "LowL": cyc(96, lambda t: ((S(t, 6), 0, 0), None)),
        "LowR": cyc(96, lambda t: ((S(t, -6), 0, 0), None)),
        **blades(96, lambda t: 1 + 0.25 * math.sin(2 * math.pi * t * 3)),
    }
    ge.animate(arm, "Idle", 96, idle)
    # Glide: sliding along the rail, the body trailing behind the trolley, skirt swinging
    glide = {
        "Body": cyc(32, lambda t: ((-9 + S(t, 2), S(t, 3), 0), None)),
        "Skirt": cyc(32, lambda t: ((-12 + S(t, 5, 0.2), 0, S(t, 4)), None)),
        "Head": cyc(32, lambda t: ((6 + S(t, 3), S(t, 4), S(t, 6, 0.25)), None)),
        "ArmL": cyc(32, lambda t: ((-20 + S(t, 6), 0, -10), None)),
        "ArmR": cyc(32, lambda t: ((-20 + S(t, -6), 0, 10), None)),
        **blades(32, lambda t: 0.5 + 0.7 * abs(math.sin(math.pi * t * 2))),
    }
    ge.animate(arm, "Glide", 32, glide)
    # Search: stops, the loupe eye sweeping left and right for a light
    search = {
        "Body": cyc(72, lambda t: ((0, S(t, 25), 0), None), 12),
        "Head": [(1, (0, 0, 0), None), (14, (10, 0, 40), None), (30, (12, 0, 42), None), (44, (10, 0, -40), None),
                 (60, (12, 0, -42), None), (73, (0, 0, 0), None)],
        "ArmL": cyc(72, lambda t: ((-10, 0, 0), None)),
        "ArmR": cyc(72, lambda t: ((-10, 0, 0), None)),
        **blades(72, lambda t: 1.2),
    }
    ge.animate(arm, "Search", 72, search)
    # Attack: swings in, both shears thrust forward and slam shut
    attack = {
        "Body": [(1, (0, 0, 0), None), (6, (14, 0, 0), None), (20, (16, 0, 0), None)],
        "Head": [(1, (0, 0, 0), None), (6, (-15, 0, 0), None), (20, (-18, 0, 6), None)],
        "ArmL": [(1, (0, 0, 0), None), (6, (-50, 0, -20), None), (20, (-55, 0, -18), None)],
        "ArmR": [(1, (0, 0, 0), None), (6, (-50, 0, 20), None), (20, (-55, 0, 18), None)],
        "ForeL": [(1, (0, 0, 0), None), (6, (-25, 0, 0), None)],
        "ForeR": [(1, (0, 0, 0), None), (6, (-25, 0, 0), None)],
        "BladeL1": [(1, (0, 0, 0), None), (5, (0, 0, 18), None), (8, (0, 0, -22), None), (20, (0, 0, -22), None)],
        "BladeL2": [(1, (0, 0, 0), None), (5, (0, 0, -18), None), (8, (0, 0, 22), None), (20, (0, 0, 22), None)],
        "BladeR1": [(1, (0, 0, 0), None), (5, (0, 0, 25), None), (8, (0, 0, -8), None), (20, (0, 0, -8), None)],
        "BladeR2": [(1, (0, 0, 0), None), (5, (0, 0, -25), None), (8, (0, 0, 8), None), (20, (0, 0, 8), None)],
    }
    ge.animate(arm, "Attack", 20, attack)
    return arm


def rig_giggler(o, off):
    P = lambda *v: tuple(Vector(v) - off)  # noqa: E731
    bones = [
        ("Hips", P(0, 0.01, 0.17), P(0, 0, 0.3), None),
        ("Spine", P(0, 0, 0.3), P(0, -0.01, 0.44), "Hips"),
        ("Head", P(0, -0.01, 0.45), P(0, -0.05, 0.72), "Spine"),
        ("ArmL", P(-0.12, 0, 0.39), P(-0.22, -0.04, 0.25), "Spine"),
        ("ArmR", P(0.12, 0, 0.39), P(0.25, -0.13, 0.4), "Spine"),
        ("LegL", P(-0.08, 0, 0.17), P(-0.1, -0.08, 0.04), "Hips"),
        ("LegR", P(0.08, 0, 0.17), P(0.1, -0.08, 0.04), "Hips"),
    ]
    radii = {"Hips": 0.15, "Spine": 0.16, "Head": 0.17, "ArmL": 0.055, "ArmR": 0.055, "LegL": 0.07, "LegR": 0.07}
    arm = ge.rig(o, bones, radii)
    # Walk: a toddling waddle, rocking from foot to foot, the heavy head lolling a beat behind
    walk = {
        "Hips": cyc(16, lambda t: ((0, S(t, 9), S(t, 4)), (0, 0, abs(S(t, 0.02, 0.25))))),
        "Spine": cyc(16, lambda t: ((-6, S(t, -5, 0.1), 0), None)),
        "Head": cyc(16, lambda t: ((S(t, 5, 0.3), S(t, 12, 0.35), S(t, 6, 0.3)), None)),
        "LegL": cyc(16, lambda t: ((S(t, 32), 0, 0), None)),
        "LegR": cyc(16, lambda t: ((S(t, -32), 0, 0), None)),
        "ArmL": cyc(16, lambda t: ((S(t, -25), 0, -8), None)),
        "ArmR": cyc(16, lambda t: ((S(t, 25), 0, 8), None)),
    }
    ge.animate(arm, "Walk", 16, walk)
    run = {
        "Hips": cyc(10, lambda t: ((-14, S(t, 10), 0), (0, 0, abs(S(t, 0.04, 0.25))))),
        "Spine": cyc(10, lambda t: ((-12, 0, S(t, 6)), None)),
        "Head": cyc(10, lambda t: ((10 + S(t, 8, 0.3), S(t, 14, 0.35), 0), None)),
        "LegL": cyc(10, lambda t: ((S(t, 50), 0, 0), None)),
        "LegR": cyc(10, lambda t: ((S(t, -50), 0, 0), None)),
        "ArmL": cyc(10, lambda t: ((-60 + S(t, 30), 0, -20), None)),
        "ArmR": cyc(10, lambda t: ((-60 + S(t, -30), 0, 20), None)),
    }
    ge.animate(arm, "Run", 10, run)
    # Idle: shaking with silent giggles, the head tipping over and snapping back
    idle = {
        "Spine": cyc(48, lambda t: ((S(t * 6, 2), 0, S(t * 6, 1.5, 0.2)), None), 24),
        "Head": [(1, (0, 0, 0), None), (20, (6, 0, 28), None), (26, (6, 0, 30), None), (29, (0, 0, -6), None),
                 (49, (0, 0, 0), None)],
        "ArmL": cyc(48, lambda t: ((S(t * 6, 4), 0, 0), None), 24),
        "ArmR": cyc(48, lambda t: ((S(t * 6, -4), 0, 0), None), 24),
    }
    ge.animate(arm, "Idle", 48, idle)
    # Attack: crouch, then spring at the face arms first
    attack = {
        "Hips": [(1, (0, 0, 0), (0, 0, 0)), (6, (10, 0, 0), (0, 0, -0.06)), (12, (-35, 0, 0), (0, 0, 0.12)),
                 (20, (-40, 0, 0), (0, 0, 0.1))],
        "Head": [(1, (0, 0, 0), None), (6, (-10, 0, 0), None), (12, (20, 0, 0), None)],
        "ArmL": [(1, (0, 0, 0), None), (6, (20, 0, 0), None), (12, (-150, 0, -20), None), (20, (-150, 0, -25), None)],
        "ArmR": [(1, (0, 0, 0), None), (6, (20, 0, 0), None), (12, (-150, 0, 20), None), (20, (-150, 0, 25), None)],
        "LegL": [(1, (0, 0, 0), None), (6, (-30, 0, 0), None), (12, (40, 0, 0), None)],
        "LegR": [(1, (0, 0, 0), None), (6, (-30, 0, 0), None), (12, (40, 0, 0), None)],
    }
    ge.animate(arm, "Attack", 20, attack)
    return arm


RIGS = {"seamstress": rig_seamstress, "giggler": rig_giggler}


def prepare():
    """Strip the preview stage, freeze everything into plain meshes in world space."""
    for o in list(bpy.data.objects):
        if o.type in ("LIGHT", "CAMERA") or o.name == "Floor":
            bpy.data.objects.remove(o, do_unlink=True)
    # hair curves are sub-pixel in game; the hair shell carries the look
    for o in list(bpy.data.objects):
        if o.type == "CURVE" and o.name.startswith("HairStrands"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    meshes = []
    for o in list(bpy.data.objects):
        if o.type == "CURVE":
            bkit.active(o)
            bpy.ops.object.convert(target="MESH")
            o = bpy.context.active_object
        if o.type != "MESH":
            continue
        # particle fur can't be baked onto the surface; the plush material underneath stays
        for m in list(o.modifiers):
            if m.type == "PARTICLE_SYSTEM":
                o.modifiers.remove(m)
        meshes.append(o)
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        if o.data.users > 1:
            o.data = o.data.copy()
        bkit.apply_all(o)
    for o in list(bpy.data.objects):
        if o.type == "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)
    return [o for o in meshes if len(o.data.polygons)]


def emissive(mat):
    if not mat or not mat.use_nodes:
        return False
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    return bool(bsdf and bsdf.inputs["Emission Strength"].default_value > 0.01)


def bake_emission(src, dst, out_dir):
    """Bake src's emission onto dst's final UVMap (same topology) and wire it into dst's material."""
    src.data.uv_layers.new(name="FinalUV")
    for a, b in zip(src.data.uv_layers["FinalUV"].data, dst.data.uv_layers["UVMap"].data):
        a.uv = b.uv
    src.data.uv_layers.active = src.data.uv_layers["FinalUV"]
    im = bpy.data.images.new(dst.name + "_emission", TEX, TEX, alpha=False)
    for mat in src.data.materials:
        nt = mat.node_tree
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = im
        nt.nodes.active = t
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "FinalUV"
        nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
    src.hide_render = False
    dst.hide_render = True
    bkit.active(src)
    bpy.ops.object.bake(type="EMIT")
    dst.hide_render = False
    im.filepath_raw = os.path.join(out_dir, dst.name + "_emission.png")
    im.file_format = "PNG"
    im.save()
    mat = dst.data.materials[0]
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = im
    nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    bpy.data.objects.remove(src, do_unlink=True)


def export(name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "creatures", name + ".blend"))
    out_dir = os.path.join(HERE, "bake", name)
    parts = prepare()
    # spend the triangle budget on the big surfaces; small parts (pins, threads, eyes) stay intact
    tris = {o.name: bkit.tri_count(o) for o in parts}
    keep = ("Pin", "Tooth", "Thread", "Stitch", "Eye", "Iris", "Pupil", "Nose", "Washer", "MB", "Loupe",
            "Lips", "Brow", "Fray", "Snag", "Lash", "Screw", "Seam", "Toe")
    detail = [o for o in parts if o.name.startswith(keep) or any(k in o.name for k in ("Pin", "Stitch", "Thread"))]
    small = sum(tris[o.name] for o in detail)
    big = [o for o in parts if o not in detail]
    room = max(BUDGET[name] - small, BUDGET[name] // 3)
    total_big = sum(tris[o.name] for o in big)
    # when the small parts alone eat most of the budget, decimating them separately starves the big
    # surfaces; then one even pass over the joined mesh holds up better
    even = small > BUDGET[name] * 0.5
    for o in big:
        if total_big > room and not even:
            bkit.decimate(o, int(tris[o.name] * room / total_big))
    print("TRIS small", small, "big", total_big, "->", room)
    obj = bkit.join(parts, name)
    fallback = None
    for i, m in enumerate(obj.data.materials):
        if m is None or not m.use_nodes:
            if fallback is None:
                fallback = bpy.data.materials.new("Fallback")
                fallback.use_nodes = True
            obj.data.materials[i] = fallback
    if bkit.tri_count(obj) > BUDGET[name] * 1.15:
        bkit.decimate(obj, BUDGET[name])
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    bkit.origin_to_bottom(obj)
    glow = any(emissive(m) for m in obj.data.materials)
    ghost = None
    if glow:
        ghost = obj.copy()
        ghost.data = obj.data.copy()
        ghost.name = name + "_emit_src"
        bpy.context.collection.objects.link(ghost)
        ghost.hide_render = True
    bkit.uv_unwrap(obj, "UVMap")
    bkit.bake_to_textures(obj, out_dir, size=TEX, samples=16)
    if ghost:
        bake_emission(ghost, obj, out_dir)
    bkit.report([obj])
    arm = RIGS[name](obj, off) if name in RIGS else None
    path = os.path.join(ROOT, "public", "models", name + ".glb")
    ge.export(path, [obj] + ([arm] if arm else []))
    # look at what ships: the baked model under studio light
    bkit.light_studio()
    bkit.render_views(os.path.join(ROOT, "renders", name + "_baked.png"), size=768, samples=32)
    blend = os.path.join(out_dir, name + "_game.blend")
    for f in (blend, blend + "1", blend + "@"):
        if os.path.exists(f):
            os.remove(f)
    bpy.ops.wm.save_as_mainfile(filepath=blend)


names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["seamstress", "giggler"]
for n in names:
    export(n)
