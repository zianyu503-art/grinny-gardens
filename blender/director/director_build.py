"""The Director (園長), redesigned: the Last Ringmaster.

A gaunt ringmaster puppet hung from the Ferris wheel hub on steel cables. Cracked porcelain
mask with a painted grin, dented top hat, faded red tailcoat with the staff badge and a PA
microphone, arms that reach his knees (marionette control bar in one hand, smiley cane in the
other), a brass gramophone horn growing out of his back, and in place of legs a train of 27
plush toys sewn together, each with a small glowing heart.

Blender coordinates, metres, Z up, front -Y. The train skims the floor; the cables run up
out of frame toward the hub.

usage: python3 ~/.claude/skills/blender-modeling/scripts/run.py blender/director/director_build.py <out_dir> [stage]
stage: blockout (default) | detail | game (rig, animate, bake, export public/models/director.glb)
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import lib  # noqa: E402  (shared creature helpers and procedural materials)
from creature_seamstress import mat_porcelain, mat_canvas, mat_blush, overlay_scan  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
STAGE = (sys.argv[sys.argv.index("--") + 2:] or ["blockout"])[0]
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RENDERS = os.path.join(ROOT, "renders")
random.seed(1996)

# key heights (m)
WAIST = 2.35
SHOULDER = 3.7
HEAD = 4.28
HUB = 7.5  # cables are cut here for previews; in game they run on up to the wheel hub


# ---------------------------------------------------------------- helpers
def mat(name, base, rough=0.6, metal=0.0, emit=0.0):
    m = bkit.procedural_material(name, base, variation=0.12, roughness=rough, metallic=metal, bump=0.2, grime=0.3)
    if emit:
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Emission Color"].default_value = (*base, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def assign(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def uv_sphere(name, loc, r, m, scale=(1, 1, 1), segs=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=r, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.shade_smooth()
    return assign(o, m)


def cone(name, loc, r1, r2, depth, m, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return assign(o, m)


def rod(name, a, b, r, m, verts=12):
    """Cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return assign(o, m)


def tube(name, pts, r, m, verts=10):
    """Smooth tube through a list of points (a bezier curve with bevel), converted to mesh."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    return assign(o, m)


def droop(a, b, sag, n=12):
    a, b = Vector(a), Vector(b)
    return [tuple(a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))) for t in (i / (n - 1) for i in range(n))]


# ---------------------------------------------------------------- blockout
def blockout():
    M = {
        "coat": mat("Coat", (0.12, 0.012, 0.012), 0.8),
        "trim": mat("GoldTrim", (0.3, 0.2, 0.07), 0.5, 0.8),
        "shirt": mat("Shirt", (0.32, 0.29, 0.22), 0.85),
        "porcelain": mat("Porcelain", (0.7, 0.66, 0.58), 0.3),
        "paint": mat("Paint", (0.08, 0.02, 0.02), 0.4),
        "blush": mat("Blush", (0.7, 0.28, 0.28), 0.4),
        "hat": mat("Hat", (0.04, 0.035, 0.035), 0.6),
        "glove": mat("Glove", (0.4, 0.37, 0.3), 0.85),
        "brass": mat("Brass", (0.16, 0.11, 0.05), 0.6, 0.75),
        "steel": mat("Steel", (0.3, 0.3, 0.32), 0.4, 0.9),
        "wood": mat("Wood", (0.25, 0.15, 0.08), 0.7),
        "heart": mat("Heart", (1.0, 0.55, 0.25), 0.4, emit=4.0),
        "dark": mat("Cavity", (0.01, 0.01, 0.01), 0.9),
    }
    # faded, grimy plush: once-bright toy colours gone grey-brown
    plush_cols = [(0.22, 0.13, 0.1), (0.16, 0.14, 0.19), (0.25, 0.2, 0.12), (0.12, 0.15, 0.16),
                  (0.24, 0.11, 0.13), (0.15, 0.16, 0.1), (0.24, 0.21, 0.17)]
    plush_m = [mat(f"Plush{i}", c, 0.95) for i, c in enumerate(plush_cols)]

    # --- torso: gaunt, long, tapering to a pinched waist; tailcoat over it
    cone("Torso", (0, 0, (WAIST + SHOULDER) / 2), 0.2, 0.3, SHOULDER - WAIST, M["coat"])
    t = bpy.context.active_object
    t.scale = (1.0, 0.62, 1)
    uv_sphere("Shoulders", (0, 0, SHOULDER - 0.04), 0.46, M["coat"], scale=(1, 0.42, 0.22))
    # shirt front and collar
    cone("ShirtFront", (0, -0.12, SHOULDER - 0.35), 0.08, 0.13, 0.7, M["shirt"]).scale = (1, 0.4, 1)
    cone("Collar", (0, -0.02, SHOULDER + 0.05), 0.13, 0.1, 0.12, M["shirt"])
    # tailcoat tails: two long tapering panels hanging behind, split at the centre
    for s in (-1, 1):
        o = cone(f"Tail{s}", (s * 0.12, 0.12, WAIST - 0.55), 0.04, 0.17, 1.4, M["coat"], rot=(0.12, s * -0.06, 0), verts=4)
        o.scale = (1, 0.25, 1)
    # gold frogging and buttons down the front
    for i in range(5):
        z = SHOULDER - 0.25 - i * 0.22
        rod(f"Frog{i}", (-0.2, -0.19, z), (0.2, -0.19, z), 0.012, M["trim"])
        for s in (-1, 1):
            uv_sphere(f"Button{i}{s}", (s * 0.21, -0.2, z), 0.025, M["trim"], segs=10)
    # epaulettes
    for s in (-1, 1):
        uv_sphere(f"Epaulette{s}", (s * 0.42, 0, SHOULDER + 0.02), 0.12, M["trim"], scale=(1, 0.8, 0.35))
    # staff badge and PA microphone on the chest, cable running round to the back
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.17, -0.2, SHOULDER - 0.35))
    assign(bpy.context.active_object, M["porcelain"]).scale = (0.12, 0.01, 0.045)
    rod("MicBody", (0.15, -0.21, SHOULDER - 0.42), (0.15, -0.25, SHOULDER - 0.26), 0.03, M["steel"])
    uv_sphere("MicHead", (0.15, -0.26, SHOULDER - 0.22), 0.05, M["steel"], segs=12)
    tube("MicCable", [(0.15, -0.21, SHOULDER - 0.45), (0.28, -0.12, WAIST + 0.3), (0.3, 0.15, WAIST + 0.4), (0.12, 0.22, SHOULDER - 0.4)], 0.012, M["dark"])

    # --- long neck, porcelain mask head, dented top hat
    rod("Neck", (0, 0, SHOULDER), (0, -0.02, HEAD - 0.12), 0.07, M["shirt"])
    uv_sphere("Head", (0, 0.02, HEAD), 0.24, M["dark"], scale=(0.9, 0.95, 1.12))
    uv_sphere("Mask", (0, -0.045, HEAD), 0.24, M["porcelain"], scale=(0.92, 0.82, 1.15))
    for s in (-1, 1):  # eye holes and rosy cheeks
        uv_sphere(f"EyeHole{s}", (s * 0.09, -0.225, HEAD + 0.06), 0.05, M["dark"], scale=(1.2, 0.5, 0.8), segs=12)
        uv_sphere(f"Cheek{s}", (s * 0.13, -0.205, HEAD - 0.07), 0.05, M["blush"], scale=(1, 0.4, 0.7), segs=12)
    uv_sphere("RealEye", (0.09, -0.245, HEAD + 0.06), 0.02, M["porcelain"], segs=10)
    # painted grin: an arc of small segments from cheek to cheek
    arc = [(math.sin(a) * 0.17, -0.245 + abs(math.sin(a)) * 0.06, HEAD - 0.1 - math.cos(a) * 0.05 + 0.05)
           for a in [i / 12 * 2.4 - 1.2 for i in range(13)]]
    tube("Grin", arc, 0.014, M["paint"])
    # hat: brim, crown, band, with a dent and a tilt
    hat_z = HEAD + 0.25
    cone("HatBrim", (0, 0, hat_z), 0.3, 0.3, 0.025, M["hat"], verts=40)
    cone("HatCrown", (0, 0, hat_z + 0.26), 0.17, 0.19, 0.5, M["hat"], verts=32)
    cone("HatBand", (0, 0, hat_z + 0.06), 0.193, 0.191, 0.08, M["coat"], verts=32)
    for n in ("HatBrim", "HatCrown", "HatBand"):
        o = bpy.data.objects[n]
        o.rotation_euler = (0.08, -0.14, 0)

    # --- arms: far too long, ending past the knees of the train
    arms = {}
    for s, side in ((-1, "R"), (1, "L")):
        sh = Vector((s * 0.44, 0.0, SHOULDER - 0.05))
        el = Vector((s * 0.78, 0.05, SHOULDER - 0.95))
        wr = Vector((s * 0.62, -0.72, SHOULDER - 1.6))
        rod(f"UpperArm{side}", sh, el, 0.075, M["coat"])
        rod(f"Forearm{side}", el, wr, 0.06, M["coat"])
        uv_sphere(f"Elbow{side}", el, 0.07, M["coat"], segs=12)
        cone(f"Cuff{side}", wr + Vector((0, 0.03, 0.06)), 0.07, 0.06, 0.12, M["trim"], verts=16)
        uv_sphere(f"Palm{side}", wr + Vector((0, -0.04, -0.1)), 0.07, M["glove"], scale=(0.7, 0.45, 1.1), segs=14)
        # five long fingers
        for k in range(5):
            a = (k - 2) * 0.22
            base = wr + Vector((s * 0.03 * (k - 2), -0.07, -0.18))
            tip = base + Vector((s * 0.03 * (k - 2) + math.sin(a) * 0.04, -0.1, -0.3 + abs(k - 2) * 0.03))
            rod(f"Finger{side}{k}", base, tip, 0.014, M["glove"], verts=8)
        arms[side] = wr

    # right hand: marionette control bar with strings down to the plush children
    wr = arms["R"]
    bar_c = wr + Vector((0, -0.12, -0.32))
    rod("ControlBar", bar_c - Vector((0.32, 0, 0)), bar_c + Vector((0.32, 0, 0)), 0.02, M["wood"])
    rod("ControlCross", bar_c - Vector((0, 0.22, 0)), bar_c + Vector((0, 0.22, 0)), 0.02, M["wood"])
    # left hand: cane with a smiley knob, tip on the ground
    wl = arms["L"]
    knob = wl + Vector((0.0, -0.1, -0.28))
    rod("Cane", knob, Vector((knob.x + 0.15, knob.y - 0.2, 0.05)), 0.018, M["hat"])
    uv_sphere("CaneKnob", knob + Vector((0, 0, 0.04)), 0.06, M["brass"], segs=14)

    # --- gramophone horn growing out from between the shoulder blades
    horn_pts = [(0.05, 0.18, SHOULDER - 0.35), (0.15, 0.32, SHOULDER - 0.05), (0.32, 0.4, SHOULDER + 0.3), (0.5, 0.42, SHOULDER + 0.62)]
    tube("HornNeck", horn_pts, 0.07, M["brass"])
    cone("HornBell", (0.68, 0.45, SHOULDER + 0.88), 0.08, 0.5, 0.6, M["brass"], rot=(-0.2, 0.75, 0), verts=40)
    cone("HornMouth", (0.88, 0.47, SHOULDER + 1.1), 0.48, 0.48, 0.02, M["dark"], rot=(-0.2, 0.75, 0), verts=40)

    # --- the train: 27 plush toys sewn together, widening toward the floor
    rows = [(WAIST - 0.1, 0.2, 4), (WAIST - 0.5, 0.42, 6), (WAIST - 0.95, 0.66, 8), (WAIST - 1.5, 0.92, 9)]
    plush_tops = []
    i = 0
    for z, ring, n in rows:
        for k in range(n):
            a = (k + 0.5 * (len(plush_tops) % 2)) / n * math.tau + random.uniform(-0.15, 0.15)
            r = random.uniform(0.22, 0.3) * (1 + 0.18 * rows.index((z, ring, n)))
            c = Vector((math.cos(a) * ring, math.sin(a) * ring * 0.85, z + random.uniform(-0.08, 0.08)))
            m = plush_m[i % len(plush_m)]
            uv_sphere(f"Plush{i:02d}", c, r, m, scale=(0.9, 0.85, 1.05), segs=16)
            out = Vector((c.x, c.y, 0)).normalized() if ring else Vector((0, -1, 0))
            hc = c + out * r * 0.55 + Vector((0, 0, r * 0.9))
            uv_sphere(f"PlushHead{i:02d}", hc, r * 0.62, m, segs=14)
            for e in (-1, 1):
                side_v = Vector((-out.y, out.x, 0)) * e
                uv_sphere(f"PlushEar{i:02d}{e}", hc + side_v * r * 0.45 + Vector((0, 0, r * 0.5)), r * 0.2, m, segs=10)
            uv_sphere(f"Heart{i:02d}", c + out * r * 0.86, r * 0.16, M["heart"], segs=10)
            plush_tops.append(hc + Vector((0, 0, r * 0.6)))
            i += 1
    # marionette strings from the control bar to a few of the plush heads
    for k, top in enumerate(plush_tops[::3]):
        end = bar_c + Vector(((k % 3 - 1) * 0.3, (k // 3 % 2 - 0.5) * 0.4, 0))
        rod(f"String{k}", end, top, 0.003, M["shirt"], verts=4)

    # --- suspension cables up toward the hub
    for name, a, top in (("CableL", (-0.3, 0.12, SHOULDER), (-0.6, 0.4, HUB)),
                         ("CableR", (0.3, 0.12, SHOULDER), (0.6, 0.4, HUB)),
                         ("CableHorn", (0, 0.45, SHOULDER + 0.6), (0, 0.9, HUB))):
        rod(name, a, top, 0.018, M["steel"])
    print("BKIT_BLOCKOUT plush", i)


def preview_shots(path):
    """Contact sheet for proportions plus a dark shot from the player's eye height."""
    bkit.light_studio()
    bkit.render_views(path, size=640, samples=24, views=("front", "side", "back", "detail"))
    # player's view in the dark: low camera, one cold key from above, warm hearts
    sc = bpy.context.scene
    for n in sc.world.node_tree.nodes:
        if n.type == "BACKGROUND":
            n.inputs["Strength"].default_value = 0.0
            n.inputs["Color"].default_value = (0, 0, 0, 1)
    bpy.ops.object.light_add(type="SPOT", location=(1.5, -4.0, 8.5))
    key = bpy.context.active_object
    key.data.energy = 9000
    key.data.spot_size = 0.9
    key.data.color = (0.75, 0.82, 1.0)
    key.rotation_euler = (Vector((0, 0, 3.2)) - key.location).to_track_quat("-Z", "Y").to_euler()
    cam_d = bpy.data.cameras.new("Eye")
    cam = bpy.data.objects.new("Eye", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (2.2, -8.5, 1.6)
    cam_d.lens = 28
    cam.rotation_euler = (Vector((0, 0, 3.4)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 960, 640
    sc.cycles.samples = 32
    sc.render.filepath = path.replace(".png", "_eye.png")
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- detail
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def tag(o, bone):
    """Which rig bone a part follows (used when the puppet is joined and skinned)."""
    o["bone"] = bone
    return o


def lat(name, profile, m, loc=(0, 0, 0), rot=None, a=None, b=None, segs=48):
    """Lathed part. Either placed at loc (axis +Z) or aimed from a to b (profile z runs along a->b)."""
    o = lib.lathe(name, profile, segments=segs, m=m)
    if a is not None:
        o.location = a
        lib.orient(o, a, b)
    else:
        o.location = loc
        if rot:
            o.rotation_euler = rot
    return o


def text(name, body, size, m, loc, rot=(math.pi / 2, 0, 0), extrude=0.002, font=FONT):
    cu = bpy.data.curves.new(name, "FONT")
    try:
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    except Exception as ex:  # noqa: BLE001
        print("font fallback:", ex)
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    o = lib.link_obj(bpy.data.objects.new(name, cu))
    o.location = loc
    o.rotation_euler = rot
    lib.select_only(o)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    lib.set_mat(o, m)
    return o


def stitches(name, a, b, n, m, width=0.02, r=0.0035):
    """A row of cross stitches from a to b."""
    a, b = Vector(a), Vector(b)
    d = (b - a)
    side = d.cross(Vector((0, 0, 1)))
    side = (side if side.length > 1e-4 else d.cross(Vector((1, 0, 0)))).normalized() * width
    out = []
    for i in range(n):
        c = a + d * ((i + 0.5) / n)
        out.append(lib.seg(f"{name}{i}a", c - side - d * 0.3 / n, c + side + d * 0.3 / n, r, m, verts=5))
        out.append(lib.seg(f"{name}{i}b", c - side + d * 0.3 / n, c + side - d * 0.3 / n, r, m, verts=5))
    return out


def materials():
    Mt = lib.Mat
    M = {}
    # faded, threadbare ringmaster velvet: bald patches on the folds, dust in the creases
    V = Mt("CoatVelvet")
    n = V.noise(3.0, 10, 0.65, distortion=0.4)
    col = V.ramp(n, [(0.25, "#2a0204"), (0.5, "#560a0e"), (0.72, "#7a1616")])
    bald = V.ramp(V.noise(1.4, 6, 0.6, distortion=1.2), [(0.62, "#ffffff"), (0.72, "#b08070")])
    col = V.mix(0.35, col, bald, "MULTIPLY")
    dust = V.ramp(V.noise(2.2, 8, 0.6), [(0.5, "#ffffff"), (0.85, "#5a4a42")])
    col = V.mix(1.0, col, dust, "MULTIPLY")
    V.set(color=col, rough=0.85, sheen=0.35, sheen_rough=0.4, sheen_tint=(1, 0.35, 0.3))
    V.bump(V.noise(90, 4, 0.7), 0.15, 0.006)
    M["coat"] = V.m
    M["gold"] = lib.mat_brass("GoldBraid")
    M["brass"] = lib.mat_brass("HornBrass", dark=True)
    M["shirt"] = mat_canvas("ShirtLinen")
    M["glove"] = mat_canvas("GloveCotton")
    M["porcelain"] = mat_porcelain("MaskPorcelain")
    M["blush"] = mat_blush("MaskBlush")
    M["lacquer"] = lib.mat_simple("BlackLacquer", "#060404", 0.22, coat=0.6, coat_rough=0.1)
    M["lips"] = lib.mat_simple("RedLacquer", "#4a0608", 0.3, coat=0.5, coat_rough=0.15)
    M["felt"] = lib.mat_simple("HatFelt", "#0c0a0a", 0.9)
    M["band"] = lib.mat_plush("HatBand", "#3a0a0c", "#1a0405", "#5a1a18", scale=6)
    M["fabric"] = lib.mat_plush("HeadFabric", "#2a1e18", "#120c0a", "#3a2c22", scale=5)
    M["thread"] = lib.mat_simple("Thread", "#5a4a38", 0.9)
    M["red_thread"] = lib.mat_simple("RedThread", "#5a1010", 0.85)
    M["wood"] = lib.mat_painted_wood("ControlWood", "#2a1a10")
    M["steel"] = lib.mat_simple("CableSteel", "#2a2a2c", 0.45, metal=0.9)
    M["enamel"] = lib.mat_simple("BadgeEnamel", "#8a8270", 0.35, coat=0.4)
    M["enamel_red"] = lib.mat_simple("BadgeRed", "#4a0a0a", 0.4)
    M["eye"] = lib.mat_eyeball("DirectorEye")
    M["black"] = lib.mat_simple("Void", "#010101", 0.95)
    H = Mt("HeartGlow")
    H.set(color="#ffb070", emit="#ff9a50", emit_strength=6.0, rough=0.4)
    M["heart"] = H.m
    plush = [("#4a3428", "#24160f", "#6a4c3a"), ("#3a3444", "#1a1620", "#544a5a"), ("#504430", "#261e12", "#6e5e42"),
             ("#2c3a3e", "#141c1e", "#425254"), ("#4a2a30", "#221216", "#664048"), ("#3a3e2a", "#1a1c12", "#545a3e"),
             ("#5a5048", "#2a2420", "#766a5e")]
    M["plush"] = [lib.mat_plush(f"Plush{i}", b, d, l, scale=3 + i * 0.4) for i, (b, d, l) in enumerate(plush)]
    # real scans on top of the procedural aging (skipped when offline)
    try:
        velvet = bkit.polyhaven_texture("velour_velvet", "1k")
        linen = bkit.polyhaven_texture("rough_linen", "1k")
        overlay_scan(M["coat"], velvet, 6.0, gain=1.1)
        overlay_scan(M["shirt"], linen, 6.0)
        overlay_scan(M["glove"], linen, 9.0)
        for pm in M["plush"]:
            overlay_scan(pm, linen, 5.0, gain=1.2, normal_strength=0.4)
    except Exception as ex:  # noqa: BLE001
        print("scans skipped:", ex)
    return M


def build_torso(M):
    # body of the coat: a long lofted barrel pinched at the waist, flattened front to back
    path = [(0, 0, WAIST - 0.05), (0, 0.0, WAIST + 0.3), (0, -0.01, 3.0), (0, 0.0, 3.4), (0, 0.02, SHOULDER - 0.02)]
    secs = [(0.2, 0.15, 0), (0.22, 0.15, 0), (0.27, 0.17, 0), (0.31, 0.18, 0), (0.37, 0.17, 0)]
    coat = tag(lib.loft("Coat", path, secs, side=(1, 0, 0), segs=28, m=M["coat"]), "chest")
    lib.subsurf(coat, 1)
    tag(lib.prim("sphere", "ShoulderCap", (0, 0.02, SHOULDER - 0.02), (0.4, 0.19, 0.09), m=M["coat"]), "chest")
    # lapels and shirt front
    for s in (-1, 1):
        lap = tag(lib.prim("cube", f"Lapel{s}", (s * 0.12, -0.19, 3.3), (0.1, 0.012, 0.42), rot=(lib.R(-6), 0, s * lib.R(18)), m=M["coat"]), "chest")
        lib.bevel(lap, 0.01)
        tag(lib.prim("cube", f"LapelEdge{s}", (s * 0.165, -0.2, 3.3), (0.008, 0.008, 0.42), rot=(lib.R(-6), 0, s * lib.R(18)), m=M["gold"]), "chest")
    tag(lib.prim("cube", "ShirtFront", (0, -0.165, 3.35), (0.15, 0.02, 0.4), rot=(lib.R(-6), 0, 0), m=M["shirt"]), "chest")
    for s in (-1, 1):  # bow tie
        tag(lib.prim("cone", f"Bow{s}", (s * 0.05, -0.2, SHOULDER - 0.04), (0.045, 0.03, 0.09), rot=(0, s * lib.R(90), 0), m=M["band"]), "chest")
    tag(lib.prim("sphere", "BowKnot", (0, -0.21, SHOULDER - 0.04), (0.02, 0.015, 0.025), m=M["band"]), "chest")
    # tails: two long panels behind, splitting and twisting a little as they hang
    for s in (-1, 1):
        tpath = [(s * 0.1, 0.12, WAIST + 0.1), (s * 0.14, 0.2, WAIST - 0.35), (s * 0.17, 0.26, WAIST - 0.9), (s * 0.2, 0.3, WAIST - 1.35)]
        tsec = [(0.16, 0.02, 0), (0.17, 0.02, 0), (0.15, 0.018, 0), (0.07, 0.015, 0)]
        tag(lib.loft(f"Tail{s}", tpath, tsec, side=(1, 0, 0), segs=12, m=M["coat"]), "spine")
    # gold frogging: braided cords across the chest with a loop at each end, and buttons
    for i in range(5):
        z = 3.5 - i * 0.2
        w = 0.24 - i * 0.012
        y = -0.18 + i * 0.004
        tag(tube(f"Frog{i}", [(-w, y, z), (-w * 0.5, y - 0.012, z + 0.01), (0, y - 0.016, z), (w * 0.5, y - 0.012, z + 0.01), (w, y, z)], 0.007, M["gold"]), "chest")
        for s in (-1, 1):
            tor = tag(lib.prim("torus", f"FrogLoop{i}{s}", (s * (w + 0.03), y + 0.005, z), (1, 1, 1), rot=(lib.R(90), 0, 0), m=M["gold"],
                               major_radius=0.025, minor_radius=0.005, major_segments=16, minor_segments=6), "chest")
            tag(lib.prim("sphere", f"Button{i}{s}", (s * (w + 0.06), y + 0.004, z), (0.022, 0.012, 0.022), m=M["gold"]), "chest")
    # epaulettes with hanging fringe
    for s in (-1, 1):
        c = Vector((s * 0.38, 0.02, SHOULDER + 0.03))
        tag(lib.prim("sphere", f"Epaulette{s}", c, (0.13, 0.11, 0.035), m=M["gold"]), "chest")
        for k in range(14):
            a = k / 14 * math.tau
            p = c + Vector((math.cos(a) * 0.125, math.sin(a) * 0.105, -0.01))
            if math.cos(a) * s < -0.3:
                continue
            tag(lib.seg(f"Fringe{s}{k}", p, p + Vector((0, 0, -0.1 - random.uniform(0, 0.03))), 0.006, M["gold"], verts=5), "chest")
    # staff badge "園長" and a PA microphone clipped beside it, cable running round to the back
    tag(lib.bevel(lib.prim("cube", "Badge", (-0.17, -0.205, 3.42), (0.13, 0.008, 0.05), m=M["enamel"]), 0.004), "chest")
    tag(lib.prim("cube", "BadgeStripe", (-0.17, -0.211, 3.448), (0.13, 0.003, 0.01), m=M["enamel_red"]), "chest")
    tag(text("BadgeText", "園長", 0.038, M["lacquer"], (-0.17, -0.215, 3.412)), "chest")
    mic = Vector((0.15, -0.23, 3.38))
    tag(lib.seg("MicStem", mic + Vector((0, 0.02, -0.12)), mic, 0.016, M["steel"], verts=10), "chest")
    tag(lib.prim("sphere", "MicGrille", mic + Vector((0, -0.01, 0.04)), (0.045, 0.04, 0.06), m=M["steel"]), "chest")
    tag(lib.prim("torus", "MicRing", mic + Vector((0, -0.01, 0.04)), (1, 1, 1), m=M["gold"], major_radius=0.046, minor_radius=0.006,
                 major_segments=20, minor_segments=6), "chest")
    tag(tube("MicCable", [mic + Vector((0, 0.02, -0.13)), (0.26, -0.16, 2.9), (0.27, 0.05, 2.75), (0.15, 0.2, 2.95), (0.06, 0.2, 3.3)], 0.009, M["black"]), "chest")
    # neck: a thin pole in a starched high collar, with a brass puppet joint ring
    tag(lib.seg("Neck", (0, 0, SHOULDER - 0.05), (0, -0.02, HEAD - 0.15), 0.055, M["fabric"], verts=16), "neck")
    tag(lat("Collar", [(0.085, 0), (0.09, 0.1), (0.1, 0.16)], M["shirt"], loc=(0, -0.01, SHOULDER + 0.02), segs=32), "neck")
    tag(lib.prim("torus", "NeckJoint", (0, -0.015, HEAD - 0.2), (1, 1, 1), m=M["gold"], major_radius=0.06, minor_radius=0.012,
                 major_segments=24, minor_segments=8), "neck")


def build_head(M):
    hc = Vector((0, 0.02, HEAD))
    head = tag(lib.prim("sphere", "HeadSack", hc, (0.21, 0.22, 0.26), m=M["fabric"]), "head")
    # seams of the stitched sack under the mask
    for k, a in enumerate((-0.6, 0.6, math.pi)):
        p0 = hc + Vector((math.sin(a) * 0.2, math.cos(a) * 0.2, 0.18))
        p1 = hc + Vector((math.sin(a) * 0.21, math.cos(a) * 0.21, -0.12))
        tag(lib.seg(f"HeadSeam{k}", p0, p1, 0.004, M["thread"], verts=5), "head")
    # the mask: front half of an egg, porcelain shell 12 mm thick, eye holes, a broken-off chunk
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=1, location=(0, 0, 0))
    mask = bpy.context.active_object
    mask.name = "Mask"
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mask.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.15], context="VERTS")
    for v in bm.verts:  # chin and a slight nose ridge
        v.co.x *= 0.88 + 0.1 * max(0, v.co.z)
        if v.co.z < -0.4:
            v.co.y -= 0.08 * (-0.4 - v.co.z)
        if abs(v.co.x) < 0.18 and -0.25 < v.co.z < 0.2:
            v.co.y -= 0.07 * (1 - abs(v.co.x) / 0.18) * (1 - abs(v.co.z + 0.02) / 0.23)
    bm.to_mesh(mask.data)
    bm.free()
    mask.scale = (0.235, 0.21, 0.29)
    mask.location = (0, -0.035, HEAD)
    lib.set_mat(mask, M["porcelain"])
    lib.smooth(mask)
    sol = mask.modifiers.new("Shell", "SOLIDIFY")
    sol.thickness = 0.012
    sol.offset = 1
    lib.apply_mods(mask)
    for s in (-1, 1):
        cut = lib.prim("sphere", f"EyeCut{s}", (s * 0.085, -0.24, HEAD + 0.07), (0.045, 0.1, 0.03), rot=(0, 0, s * lib.R(-12)))
        lib.boolean(mask, cut)
    chunk = lib.prim("ico", "ChunkCut", (-0.16, -0.2, HEAD + 0.13), (0.08, 0.1, 0.07), subdivisions=2)
    lib.displace(chunk, 0.035, 0.05)
    lib.apply_mods(chunk)
    lib.boolean(mask, chunk)
    tag(mask, "head")
    # painted face: lacquered grin with red lips, rosy cheeks, brows painted high in surprise
    arc = [(math.sin(a) * 0.15, -0.262 + abs(math.sin(a)) * 0.06, HEAD - 0.1 + (1 - math.cos(a)) * 0.065) for a in [i / 14 * 2.5 - 1.25 for i in range(15)]]
    g = tag(tube("Grin", arc, 0.012, M["lacquer"]), "head")
    g.scale.y = 1.0
    arc2 = [(x * 0.92, y - 0.002, z - 0.018) for x, y, z in arc[2:-2]]
    tag(tube("Lips", arc2, 0.008, M["lips"]), "head")
    for k in range(6):  # painted teeth lines across the grin
        x = -0.075 + k * 0.03
        tag(lib.seg(f"Tooth{k}", (x, -0.262, HEAD - 0.1 + 0.02), (x, -0.262, HEAD - 0.1 - 0.012), 0.003, M["lacquer"], verts=4), "head")
    for s in (-1, 1):
        tag(lib.prim("sphere", f"Cheek{s}", (s * 0.13, -0.226, HEAD - 0.06), (0.04, 0.004, 0.03), rot=(0, 0, s * lib.R(-28)), m=M["blush"]), "head")
        tag(tube(f"Brow{s}", [(s * 0.04, -0.252, HEAD + 0.13), (s * 0.09, -0.25, HEAD + 0.155), (s * 0.135, -0.24, HEAD + 0.13)], 0.005, M["lacquer"]), "head")
    # behind the left eye hole, a real eye; the right one is just dark
    tag(lib.prim("sphere", "RealEye", (0.085, -0.2, HEAD + 0.07), (0.02, 0.02, 0.02), m=M["enamel"]), "head")
    tag(lib.prim("sphere", "RealPupil", (0.087, -0.219, HEAD + 0.068), (0.008, 0.004, 0.008), m=M["black"]), "head")
    tag(lib.prim("sphere", "EyeVoid", (-0.085, -0.205, HEAD + 0.07), (0.035, 0.02, 0.025), m=M["black"]), "head")
    # hat: worn felt topper, crown dented and tipped, band reading 微笑樂園 1996
    hz = HEAD + 0.25
    hat = []
    hat.append(lat("HatBrim", [(0.0, 0.0), (0.18, 0.0), (0.27, 0.005), (0.3, 0.025), (0.305, 0.04), (0.29, 0.03), (0.2, 0.012), (0.0, 0.012)], M["felt"], loc=(0, 0, hz)))
    crown = lat("HatCrown", [(0.17, 0.0), (0.168, 0.2), (0.175, 0.42), (0.19, 0.5), (0.18, 0.51), (0.0, 0.51)], M["felt"], loc=(0, 0, hz + 0.01))
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(crown.data)
    for v in bm.verts:  # the dent: top pushed in on one side
        if v.co.z > 0.3 and v.co.x > 0.02:
            v.co.z -= 0.08 * (v.co.x / 0.19) * ((v.co.z - 0.3) / 0.21)
            v.co.x -= 0.015 * (v.co.z - 0.3) / 0.21
    bm.to_mesh(crown.data)
    bm.free()
    hat.append(crown)
    hat.append(lat("HatBand", [(0.172, 0.0), (0.172, 0.075)], M["band"], loc=(0, 0, hz + 0.02)))
    t = text("HatText", "微笑樂園 1996", 0.03, M["gold"], (0, -0.178, hz + 0.058))
    hat.append(t)
    for o in hat:
        p = o.location.copy() - Vector((0, 0, HEAD))
        o.location = Vector((0, 0, HEAD)) + Vector((p.x, p.y * math.cos(0.1) - p.z * math.sin(0.1), p.y * math.sin(0.1) + p.z * math.cos(0.1)))
        o.rotation_euler.x += 0.1
        o.rotation_euler.y += -0.12
        tag(o, "head")


def build_arm(M, side, s, sh, el, wr, grip_axis):
    """Long puppet arm: velvet sleeve segments joined by brass hinge pins, gloved hand."""
    tag(lib.seg(f"UpperSleeve{side}", sh, el, 0.085, M["coat"], r2=0.07, verts=16), f"arm_up.{side}")
    tag(lib.seg(f"LowerSleeve{side}", el, wr, 0.068, M["coat"], r2=0.055, verts=16), f"arm_lo.{side}")
    for name, p, bone in ((f"ShoulderPin{side}", sh, f"arm_up.{side}"), (f"ElbowPin{side}", el, f"arm_lo.{side}")):
        tag(lib.prim("sphere", name + "Ball", p, (0.075, 0.075, 0.075), m=M["coat"]), bone)
        tag(lib.seg(name, p - Vector((s * 0.09, 0, 0)), p + Vector((s * 0.09, 0, 0)), 0.014, M["gold"], verts=8), bone)
    d = (wr - el).normalized()
    cuff = tag(lib.seg(f"Cuff{side}", wr - d * 0.1, wr + d * 0.01, 0.07, M["gold"], verts=16), f"hand.{side}")
    # gloved hand: palm and five long three-jointed fingers curled around grip_axis
    up = Vector((0, 0, 1))
    across = d.cross(up).normalized()
    palm_c = wr + d * 0.1
    tag(lib.prim("sphere", f"Palm{side}", palm_c, (0.06, 0.035, 0.09), m=M["glove"]), f"hand.{side}")
    lib.orient(bpy.data.objects[f"Palm{side}"], wr, wr + d)
    for k in range(5):
        thumb = k == 0
        base = palm_c + d * (0.04 if thumb else 0.08) + across * (s * (0.05 if thumb else (k - 2.5) * 0.024))
        dirv = (d + across * s * (0.6 if thumb else 0.05)).normalized()
        curl = grip_axis
        p = base
        L = 0.08 if thumb else 0.11 - abs(k - 2.5) * 0.008
        for j in range(3):
            ang = (0.55 if not thumb else 0.35) * (j + 1)
            q = dirv * math.cos(ang) + curl * math.sin(ang)
            n = p + q.normalized() * L * (1 - j * 0.18)
            tag(lib.seg(f"Finger{side}{k}{j}", p, n, 0.014 - j * 0.002, M["glove"], verts=8), f"hand.{side}")
            tag(lib.prim("sphere", f"Knuckle{side}{k}{j}", n, (0.013, 0.013, 0.013), m=M["glove"]), f"hand.{side}")
            p = n
    return palm_c, d


def build_props(M, r_palm, r_dir, l_palm, l_dir):
    # marionette control: a wooden cross with brass eyelets, hanging from the right hand
    bar = r_palm + r_dir * 0.16
    tag(lib.bevel(lib.prim("cube", "ControlBar", bar, (0.7, 0.04, 0.03), m=M["wood"]), 0.005), "hand.R")
    tag(lib.bevel(lib.prim("cube", "ControlCross", bar + Vector((0, 0, -0.01)), (0.04, 0.46, 0.03), m=M["wood"]), 0.005), "hand.R")
    eyelets = [bar + Vector((x, y, -0.02)) for x, y in ((-0.33, 0), (0.33, 0), (0, -0.22), (0, 0.22), (-0.16, 0), (0.16, 0))]
    for i, e in enumerate(eyelets):
        tag(lib.prim("torus", f"Eyelet{i}", e, (1, 1, 1), m=M["gold"], major_radius=0.012, minor_radius=0.003,
                     major_segments=10, minor_segments=4), "hand.R")
    # cane in the left hand, tip on the floor, a smiling brass knob
    knob = l_palm + l_dir * 0.08 + Vector((0, 0, 0.08))
    tip = Vector((knob.x + 0.18, knob.y - 0.25, 0.04))
    tag(lib.seg("Cane", knob, tip, 0.018, M["lacquer"], verts=12), "hand.L")
    tag(lib.seg("CaneFerrule", tip + (knob - tip).normalized() * 0.06, tip, 0.02, M["gold"], verts=12), "hand.L")
    tag(lib.prim("sphere", "CaneKnob", knob + Vector((0, 0, 0.05)), (0.06, 0.06, 0.06), m=M["gold"]), "hand.L")
    for s in (-1, 1):
        tag(lib.prim("sphere", f"KnobEye{s}", knob + Vector((s * 0.02, -0.055, 0.07)), (0.008, 0.005, 0.01), m=M["black"]), "hand.L")
    tag(tube("KnobSmile", [knob + Vector((x, -0.056 + abs(x) * 0.3, 0.035 - (0.025 - abs(x)) * 0.5)) for x in (-0.025, -0.012, 0, 0.012, 0.025)],
             0.003, M["black"]), "hand.L")
    return eyelets


def build_horn(M):
    """Gramophone horn grown out of his back: brass throat tube into an exponential flared bell."""
    throat = Vector((0.12, 0.3, SHOULDER - 0.05))
    neck_pts = [(0.03, 0.17, SHOULDER - 0.4), (0.06, 0.26, SHOULDER - 0.25), throat, (0.3, 0.38, SHOULDER + 0.28), (0.46, 0.42, SHOULDER + 0.55)]
    tag(tube("HornNeck", neck_pts, 0.045, M["brass"]), "horn")
    mouth_dir = Vector((0.55, 0.15, 0.82)).normalized()
    a = Vector(neck_pts[-1])
    L = 0.85
    prof = [(0.045 * math.exp(2.6 * (z / L) ** 1.6), z) for z in [i / 20 * L for i in range(21)]]
    prof[-1] = (0.52, L)
    prof += [(0.54, L - 0.01), (0.545, L - 0.03)]  # rolled lip
    bell = tag(lat("HornBell", prof, M["brass"], a=a, b=a + mouth_dir), "horn")
    sol = bell.modifiers.new("Wall", "SOLIDIFY")
    sol.thickness = 0.006
    lib.apply_mods(bell)
    # soldered seams running up the bell
    for k in range(6):
        ang = k / 6 * math.tau
        pts = []
        for z, r in [(p[1], p[0]) for p in prof[2:21:3]]:
            q = mouth_dir.to_track_quat("Z", "Y")
            loc = Vector((math.cos(ang) * (r + 0.004), math.sin(ang) * (r + 0.004), z))
            pts.append(tuple(a + q @ loc))
        tag(tube(f"HornSeam{k}", pts, 0.005, M["brass"]), "horn")
    # the strap that holds it to his back
    tag(lib.prim("torus", "HornStrap", (0.06, 0.2, SHOULDER - 0.3), (1, 1.2, 1), rot=(lib.R(80), 0, 0), m=M["band"],
                 major_radius=0.22, minor_radius=0.015, major_segments=32, minor_segments=6), "chest")


PLUSH_KINDS = ("bear", "bunny", "cat", "dog")


def build_plush(M, i, c, out, r, row):
    """One faded plush toy sewn into the train: body, head, ears by kind, stubby limbs,
    button eyes, a heart lamp in its chest. Faces outward, head lolling."""
    kind = PLUSH_KINDS[i % 4]
    m = M["plush"][i % len(M["plush"])]
    bone = f"train_{row}"
    side = Vector((-out.y, out.x, 0)).normalized()
    up = Vector((0, 0, 1))
    body = tag(lib.prim("sphere", f"PlushBody{i:02d}", c, (r * 0.85, r * 0.8, r), m=m), bone)
    body.rotation_euler = (0, 0, math.atan2(out.y, out.x) + math.pi / 2)
    tilt = random.uniform(-0.5, 0.5)
    hd = (out * 0.35 + up + side * tilt * 0.4).normalized()
    hc = c + hd * r * 1.25
    hr = r * 0.68
    tag(lib.prim("sphere", f"PlushHead{i:02d}", hc, (hr, hr * 0.92, hr * 0.9), m=m), bone)
    tag(lib.prim("sphere", f"PlushMuzzle{i:02d}", hc + out * hr * 0.8 - up * hr * 0.2, (hr * 0.38, hr * 0.32, hr * 0.28), m=m), bone)
    for e in (-1, 1):
        base = hc + side * e * hr * 0.55 + up * hr * 0.6
        if kind == "bear":
            tag(lib.prim("sphere", f"PlushEar{i:02d}{e}", base, (hr * 0.28, hr * 0.12, hr * 0.28), m=m), bone)
        elif kind == "bunny":
            tip = base + (up + side * e * 0.35 + out * 0.1).normalized() * hr * 1.5
            if e > 0 and i % 3 == 0:  # one ear flopped over
                tip = base + (side * e + out * 0.4 - up * 0.3).normalized() * hr * 1.2
            tag(lib.seg(f"PlushEar{i:02d}{e}", base, tip, hr * 0.17, m, r2=hr * 0.1, verts=10), bone)
        elif kind == "cat":
            tag(lib.seg(f"PlushEar{i:02d}{e}", base, base + (up + side * e * 0.3).normalized() * hr * 0.5, hr * 0.22, m, r2=0.002, verts=8), bone)
        else:
            tip = base + (side * e * 0.6 - up + out * 0.2).normalized() * hr * 0.9
            tag(lib.seg(f"PlushEar{i:02d}{e}", base, tip, hr * 0.2, m, r2=hr * 0.14, verts=10), bone)
        # button eyes, one hanging loose on a thread now and then
        ey = hc + out * hr * 0.86 + side * e * hr * 0.32 + up * hr * 0.12
        if e > 0 and i % 5 == 2:
            loose = ey - up * hr * 0.5 + out * 0.02
            tag(lib.seg(f"PlushThread{i:02d}", ey, loose, 0.0015, M["thread"], verts=4), bone)
            ey = loose
        tag(lib.prim("cyl", f"PlushEye{i:02d}{e}", ey, (hr * 0.13, hr * 0.13, 0.012), m=M["lacquer"]), bone)
        lib.orient(bpy.data.objects[f"PlushEye{i:02d}{e}"], ey - out, ey + out)
        # stubby arms reaching round to the neighbours, feet dangling
        sh = c + side * e * r * 0.75 + up * r * 0.3
        tag(lib.seg(f"PlushArm{i:02d}{e}", sh, sh + (side * e * 0.8 + out * 0.4 - up * 0.3).normalized() * r * 0.9, r * 0.22, m, r2=r * 0.18, verts=10), bone)
        hip = c + side * e * r * 0.4 - up * r * 0.8
        tag(lib.seg(f"PlushLeg{i:02d}{e}", hip, hip + (out * 0.5 - up).normalized() * r * 0.7, r * 0.25, m, r2=r * 0.22, verts=10), bone)
    # stitched mouth and the heart lamp sewn into the chest
    tag(tube(f"PlushMouth{i:02d}", [tuple(hc + out * hr * 0.98 + side * x * hr * 0.25 - up * hr * (0.32 - abs(x) * 0.1)) for x in (-1, -0.5, 0, 0.5, 1)],
             0.003, M["thread"]), bone)
    hp = c + out * r * 0.8 + up * r * 0.15
    tag(lib.prim("sphere", f"Heart{i:02d}", hp, (r * 0.16, r * 0.08, r * 0.15), m=M["heart"]), bone)
    tag(lib.prim("torus", f"HeartRim{i:02d}", hp, (1, 1, 1), m=M["red_thread"], major_radius=r * 0.18, minor_radius=r * 0.025,
                 major_segments=16, minor_segments=5), bone)
    lib.orient(bpy.data.objects[f"HeartRim{i:02d}"], hp - out, hp + out)
    return hc + up * hr


def build_train(M, eyelets):
    # a stuffed canvas core so the toys read as one sewn mass, not loose balloons
    core = tag(lat("TrainCore", [(0.22, WAIST + 0.05), (0.3, WAIST - 0.4), (0.55, WAIST - 1.0), (0.82, WAIST - 1.6), (0.9, WAIST - 1.95), (0.7, WAIST - 2.08), (0.0, WAIST - 2.1)],
                   M["fabric"], loc=(0, 0, 0)), "train_4")
    lib.displace(core, 0.05, 0.25)
    rows = [(WAIST - 0.1, 0.24, 4), (WAIST - 0.55, 0.45, 6), (WAIST - 1.02, 0.7, 8), (WAIST - 1.55, 0.94, 9)]
    tops, centres = [], []
    i = 0
    for ri, (z, ring, n) in enumerate(rows):
        for k in range(n):
            a = (k + 0.5 * (ri % 2)) / n * math.tau + random.uniform(-0.12, 0.12)
            r = random.uniform(0.21, 0.27) * (1 + 0.16 * ri)
            c = Vector((math.cos(a) * ring, math.sin(a) * ring * 0.85, z + random.uniform(-0.06, 0.06)))
            out = Vector((c.x, c.y, 0)).normalized()
            tops.append(build_plush(M, i, c, out, r, ri + 1))
            centres.append((c, r, ri + 1))
            i += 1
    # coarse red stitches sewing neighbours together
    for j, (c, r, row) in enumerate(centres):
        for c2, r2, row2 in centres[j + 1:]:
            d = (c2 - c).length
            if d < (r + r2) * 1.05 and random.random() < 0.6:
                a = c + (c2 - c) * (r / (r + r2))
                stitches(f"Sew{j}_{int(c2.x * 100)}", a - Vector((0, 0, 0.08)), a + Vector((0, 0, 0.08)), 3, M["red_thread"], width=0.025)
                for o in [ob for ob in bpy.context.scene.objects if ob.name.startswith(f"Sew{j}_{int(c2.x * 100)}")]:
                    tag(o, f"train_{max(row, row2)}")
    # marionette strings from the control bar down to every third toy's head
    for k, top in enumerate(tops[::3]):
        tag(lib.seg(f"String{k}", eyelets[k % len(eyelets)], top, 0.0018, M["thread"], verts=4), "hand.R")
    print("BKIT_TRAIN plush", i)


def build_cables(M):
    for name, a, top, bone in (("CableL", (-0.28, 0.16, SHOULDER + 0.02), (-0.5, 0.45, HUB), "chest"),
                               ("CableR", (0.28, 0.16, SHOULDER + 0.02), (0.5, 0.45, HUB), "chest"),
                               ("CableHead", (0, 0.06, HEAD + 0.3), (0, 0.2, HUB), "head")):
        a = Vector(a)
        tag(lib.prim("torus", name + "Eye", a, (1, 1, 1), rot=(0, lib.R(90), 0), m=M["steel"], major_radius=0.03, minor_radius=0.008,
                     major_segments=12, minor_segments=5), bone)
        tag(lib.seg(name, a + Vector((0, 0, 0.03)), top, 0.011, M["steel"], verts=8), "root")


def detail():
    M = materials()
    build_torso(M)
    build_head(M)
    up = Vector((0, 0, 1))
    r_palm, r_dir = build_arm(M, "R", -1, Vector((-0.44, 0.0, SHOULDER - 0.05)), Vector((-0.78, 0.05, SHOULDER - 0.95)),
                              Vector((-0.62, -0.72, SHOULDER - 1.6)), Vector((0, -1, 0)))
    l_palm, l_dir = build_arm(M, "L", 1, Vector((0.44, 0.0, SHOULDER - 0.05)), Vector((0.78, 0.05, SHOULDER - 0.95)),
                              Vector((0.62, -0.72, SHOULDER - 1.6)), Vector((0, -1, 0)))
    eyelets = build_props(M, r_palm, r_dir, l_palm, l_dir)
    build_horn(M)
    build_train(M, eyelets)
    build_cables(M)
    untagged = [o.name for o in bpy.context.scene.objects if o.type == "MESH" and "bone" not in o]
    print("BKIT_DETAIL parts", len([o for o in bpy.context.scene.objects if o.type == "MESH"]), "untagged", untagged[:10])


def detail_shots():
    """Hero (player's view, dark), face close-up, and a neutral studio shot for materials."""
    lib.setup_render(samples=32, res=(960, 600))
    shots = [
        ("hero", "horror", (2.4, -8.0, 1.5), (0, 0, 3.0), 30),
        ("face", "horror", (-0.55, -1.75, HEAD + 0.05), (0, -0.1, HEAD + 0.05), 50),
        ("studio", "studio", (5.5, -7.5, 3.4), (0, 0, 2.9), 34),
    ]
    for name, mood, cam, target, lens in shots:
        for o in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA") or o.name == "Floor"]:
            bpy.data.objects.remove(o, do_unlink=True)
        lib.stage(mood)
        if mood == "horror":
            lib.add_area("Key", (2.5, -3.5, 7.5), (0, 0, 3.4), 2500, (0.7, 0.8, 1.0), spot=True)
            lib.add_area("Rim", (-2.5, 3.0, 5.0), (0, 0, 3.5), 900, (1.0, 0.45, 0.3), size=1.5)
            lib.add_area("Fill", (0.0, -4.0, 0.6), (0, 0, 2.0), 120, (1.0, 0.7, 0.45), size=3)
            if name == "face":
                lib.add_area("FaceKey", (0.9, -1.6, HEAD + 0.6), (0, -0.2, HEAD), 60, (0.85, 0.9, 1.0), size=0.6)
        else:
            lib.add_area("Key", (4, -5, 7), (0, 0, 3), 3000, size=4)
            lib.add_area("Fill", (-5, -3, 3), (0, 0, 2.5), 900, size=4)
            lib.add_area("Back", (0, 5, 6), (0, 0, 3), 1200, size=3)
        lib.camera(cam, target, lens)
        lib.render(os.path.join(RENDERS, f"director2_{name}.png"))


# ---------------------------------------------------------------- game export
BUDGET = 26000


def rig_bones():
    sh = {"R": Vector((-0.44, 0.0, SHOULDER - 0.05)), "L": Vector((0.44, 0.0, SHOULDER - 0.05))}
    el = {"R": Vector((-0.78, 0.05, SHOULDER - 0.95)), "L": Vector((0.78, 0.05, SHOULDER - 0.95))}
    wr = {"R": Vector((-0.62, -0.72, SHOULDER - 1.6)), "L": Vector((0.62, -0.72, SHOULDER - 1.6))}
    bones = [
        ("root", (0, 0, 0), (0, 0, 0.5), None),
        ("spine", (0, 0, WAIST), (0, 0, 3.0), "root"),
        ("chest", (0, 0, 3.0), (0, 0, SHOULDER), "spine"),
        ("neck", (0, 0, SHOULDER), (0, -0.02, HEAD - 0.15), "chest"),
        ("head", (0, -0.02, HEAD - 0.15), (0, -0.02, HEAD + 0.35), "neck"),
        ("horn", (0.03, 0.17, SHOULDER - 0.4), (0.46, 0.42, SHOULDER + 0.55), "chest"),
        ("train_1", (0, 0, WAIST), (0, 0, WAIST - 0.45), "spine"),
        ("train_2", (0, 0, WAIST - 0.45), (0, 0, WAIST - 0.95), "train_1"),
        ("train_3", (0, 0, WAIST - 0.95), (0, 0, WAIST - 1.45), "train_2"),
        ("train_4", (0, 0, WAIST - 1.45), (0, 0, WAIST - 2.1), "train_3"),
    ]
    for side in ("R", "L"):
        d = (wr[side] - el[side]).normalized()
        bones += [(f"arm_up.{side}", sh[side], el[side], "chest"), (f"arm_lo.{side}", el[side], wr[side], f"arm_up.{side}"),
                  (f"hand.{side}", wr[side], wr[side] + d * 0.3, f"arm_lo.{side}")]
    return bones


def game_export():
    import game_export as ge  # shared animate() helper (NLA tracks per clip)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "director_detail.blend"))
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    parts = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    # rigid puppet: every part follows exactly one bone
    for o in parts:
        lib.apply_mods(o)
        vg = o.vertex_groups.new(name=o["bone"])
        vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    hearts = [o for o in parts if o.name.startswith("Heart") and not o.name.startswith("HeartRim")]
    body = [o for o in parts if o not in hearts]
    total = sum(bkit.tri_count(o) for o in body)
    ratio = (BUDGET - 1500) / total
    for o in body:  # thin cords keep a few more triangles so they don't collapse
        if o.name.startswith("Horn"):  # the horn is his silhouette; a thin flared shell falls apart when decimated
            continue
        t = bkit.tri_count(o)
        keep = max(int(t * ratio), min(t, 24))
        if keep < t:
            m = o.modifiers.new("Dec", "DECIMATE")
            m.ratio = keep / t
            lib.apply_mods(o)
    for o in hearts:  # tiny lamps: a few dozen triangles each is plenty
        m = o.modifiers.new("Dec", "DECIMATE")
        m.ratio = 60 / max(bkit.tri_count(o), 60)
        lib.apply_mods(o)
    obj = bkit.join(body, "Director")
    glow = bkit.join(hearts, "DirectorHearts")
    # parts converted from curves/text can carry empty material slots; point them at a real one
    first = next(m for m in obj.data.materials if m)
    for i, m in enumerate(obj.data.materials):
        if m is None:
            obj.data.materials[i] = first
    print("BKIT_TRIS body", bkit.tri_count(obj), "hearts", bkit.tri_count(glow), "from", total)
    # Cycles bakes the diffuse colour of fully metallic surfaces as black: tone the metals down
    # to partly metallic so the brass horn and gold braid keep their colour in the bake
    for m in obj.data.materials:
        if m and m.name.split(".")[0] in ("HornBrass", "GoldBraid", "CableSteel"):
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            met = bsdf.inputs["Metallic"]
            for lk in list(met.links):
                m.node_tree.links.remove(lk)
            met.default_value = 0.35
    bake_dir = os.path.join(OUT, "textures")
    bkit.bake_to_textures(obj, bake_dir, size=1024, samples=8)
    hm = bpy.data.materials.new("HeartGlow")
    hm.use_nodes = True
    b = next(n for n in hm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (1.0, 0.6, 0.35, 1)
    b.inputs["Emission Color"].default_value = (1.0, 0.55, 0.25, 1)
    b.inputs["Emission Strength"].default_value = 4.0
    glow.data.materials.clear()
    glow.data.materials.append(hm)

    # armature with rigid weights already in place
    bones = rig_bones()
    arm_d = bpy.data.armatures.new("DirectorRig")
    arm = lib.link_obj(bpy.data.objects.new("DirectorRig", arm_d))
    lib.select_only(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, parent in bones:
        eb = arm_d.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = h, t, 0.0
        if parent:
            eb.parent = arm_d.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in (obj, glow):
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm

    cyc, S = ge.cyc, ge.S
    sway = lambda amp, ph=0.0: cyc(96, lambda t: ((S(t, amp * 0.5, ph), 0, S(t, amp, ph)), None))
    ge.animate(arm, "Idle", 96, {
        "spine": sway(3), "chest": sway(2, 0.1), "neck": sway(4, 0.2),
        "head": cyc(96, lambda t: ((S(t, 4, 0.3), 0, S(t, 9, 0.25)), None)),
        "arm_up.R": sway(5, 0.3), "arm_up.L": sway(5, 0.55), "horn": sway(3, 0.4),
        "train_1": sway(3, 0.3), "train_2": sway(4, 0.4), "train_3": sway(5, 0.5), "train_4": sway(6, 0.6),
    })
    # Throw: wind the right arm up and back, then hurl it forward and down; head snaps with it
    ge.animate(arm, "Throw", 48, {
        "arm_up.R": [(1, (0, 0, 0), None), (14, (95, 0, -25), None), (22, (-60, 0, 10), None), (34, (-40, 0, 5), None), (48, (0, 0, 0), None)],
        "arm_lo.R": [(1, (0, 0, 0), None), (14, (40, 0, 0), None), (22, (-10, 0, 0), None), (48, (0, 0, 0), None)],
        "chest": [(1, (0, 0, 0), None), (14, (10, 0, 12), None), (22, (-14, 0, -10), None), (48, (0, 0, 0), None)],
        "head": [(1, (0, 0, 0), None), (14, (12, 0, 10), None), (22, (-18, 0, -14), None), (30, (8, 0, 20), None), (48, (0, 0, 0), None)],
    })
    # Reach: both long arms swing forward to grab, head tilts down at you
    ge.animate(arm, "Reach", 36, {
        "arm_up.R": [(1, (0, 0, 0), None), (18, (-75, 0, 10), None), (36, (-70, 0, 8), None)],
        "arm_up.L": [(1, (0, 0, 0), None), (18, (-75, 0, -10), None), (36, (-70, 0, -8), None)],
        "arm_lo.R": [(1, (0, 0, 0), None), (18, (-25, 0, 0), None), (36, (-20, 0, 0), None)],
        "arm_lo.L": [(1, (0, 0, 0), None), (18, (-25, 0, 0), None), (36, (-20, 0, 0), None)],
        "neck": [(1, (0, 0, 0), None), (18, (-15, 0, 0), None), (36, (-15, 0, 0), None)],
        "head": [(1, (0, 0, 0), None), (18, (-12, 0, 18), None), (36, (-12, 0, 22), None)],
    })
    # sanity check: where the right hand goes at the top of the throw wind-up
    tr = arm.animation_data.nla_tracks["Throw"]
    arm.animation_data.action = tr.strips[0].action
    for f in (1, 14, 22):
        bpy.context.scene.frame_set(f)
        hb = arm.pose.bones["hand.R"]
        print("BKIT_THROW frame", f, "hand", tuple(round(v, 2) for v in (arm.matrix_world @ hb.head)))
    arm.animation_data.action = None
    bpy.context.scene.frame_set(1)

    path = os.path.join(ROOT, "public", "models", "director.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in (arm, obj, glow):
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=False,
                              export_lights=False, export_image_format="JPEG", export_jpeg_quality=85,
                              export_animation_mode="NLA_TRACKS")
    print("BKIT_EXPORT", path, os.path.getsize(path) // 1024, "KB")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "director_game.blend"))
    # check what ships: the baked model in the dark player's-eye shot
    for o in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
        bpy.data.objects.remove(o, do_unlink=True)
    lib.setup_render(samples=24, res=(800, 500))
    lib.stage("horror")
    lib.add_area("Key", (2.5, -3.5, 7.5), (0, 0, 3.4), 2500, (0.7, 0.8, 1.0), spot=True)
    lib.add_area("Rim", (-2.5, 3.0, 5.0), (0, 0, 3.5), 900, (1.0, 0.45, 0.3), size=1.5)
    lib.add_area("Fill", (0.0, -4.0, 0.6), (0, 0, 2.0), 160, (1.0, 0.7, 0.45), size=3)
    lib.camera((2.4, -8.0, 1.5), (0, 0, 3.0), 30)
    lib.render(os.path.join(RENDERS, "director2_baked.png"))


bkit.reset_scene()
if STAGE == "blockout":
    blockout()
    preview_shots(os.path.join(RENDERS, "director2_blockout.png"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "director_blockout.blend"))
elif STAGE == "detail":
    detail()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "director_detail.blend"))
    detail_shots()
elif STAGE == "game":
    game_export()
print("BKIT_DONE", STAGE)
