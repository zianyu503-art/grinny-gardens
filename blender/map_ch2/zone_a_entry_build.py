"""Chapter 2, zone A (zone_a_entry): freight elevator and stairwell landing.

Interior box x -6..6, y 0..16, ceiling z 4.0. This zone builds the start wall (y = 0)
and the far wall (y = 16). Doorways are 2.4 m wide (x -1.2..1.2), 3.0 m high.
Start wall: the steel trim sits on the zone side, the leaf hangs open flat against the
wall beside the opening. Far wall: frame and hinge stubs, the leaf is missing.

Headless runs, from /Users/alex/恐怖遊戲2:
  blender -b --factory-startup -P blender/map_ch2/zone_a_entry_build.py -- build
  blender -b --factory-startup -P blender/map_ch2/zone_a_entry_build.py -- verify
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_a_entry"
GLB = f"{ROOT}/public/models/ch2/{NAME}.glb"
JSON_OUT = f"{ROOT}/public/models/ch2/{NAME}.json"
BLEND = f"{ROOT}/blender/bake/map_ch2/{NAME}.blend"
RENDER_DIR = f"{ROOT}/renders"
SCRATCH = "/private/tmp/claude-504/-Users-alex-----2/df819384-06df-4249-8523-a5c0f94e5679/scratchpad/zA"
SAMPLES = 24
PREVIEW = 768

rng = random.Random(11)
MATS = {}
GROUPS = {}


# ------------------------------------------------------------------ materials

TEX_DIR = f"{SCRATCH}/tex512"
TEX_CACHE = {}


def small_maps(tex):
    """Poly Haven 1k set resized to 512 px JPEG (q 80) with sips; cached per set."""
    if tex in TEX_CACHE:
        return TEX_CACHE[tex]
    import subprocess
    src = bkit.polyhaven_texture(tex, "1k")
    os.makedirs(TEX_DIR, exist_ok=True)
    out = {}
    for slot in ("color", "normal", "roughness"):
        if slot not in src:
            continue
        dst = f"{TEX_DIR}/{tex}_{slot}.jpg"
        subprocess.run(["sips", "-Z", "512", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        src[slot], "--out", dst], check=True, capture_output=True)
        out[slot] = dst
    TEX_CACHE[tex] = out
    return out


def make_materials():
    """One material per texture set (no tints, so each image is written once in the GLB).
    Small coloured parts use plain colour materials with no image."""
    def pm(key, tex, **kw):
        MATS[key] = bkit.pbr_material(f"A_{key}", small_maps(tex), **kw)

    def plain(key, color, rough=0.6, metal=0.0):
        mat = bpy.data.materials.new(f"A_{key}")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        MATS[key] = mat

    pm("floor", "brushed_concrete_2")
    pm("wall", "blue_plaster_weathered")
    pm("ceil", "concrete")
    pm("rust", "rusty_metal_02")
    pm("painted", "rusty_painted_metal")
    pm("wood", "wood_planks")
    pm("rubber", "rubberized_track")
    pm("paper", "rough_linen", metallic=0.0)
    plain("cardboard", (0.45, 0.34, 0.22), 0.9)
    plain("cork", (0.5, 0.36, 0.22), 0.9)
    plain("puddle", (0.02, 0.025, 0.03), 0.05)
    plain("drain", (0.2, 0.2, 0.21), 0.5, 1.0)
    plain("glass", (0.05, 0.09, 0.09), 0.1)
    plain("hz_y", (0.95, 0.68, 0.04), 0.6)
    plain("hz_k", (0.04, 0.04, 0.04), 0.6)
    plain("sign_y", (0.9, 0.66, 0.1), 0.6)
    plain("sign_r", (0.55, 0.06, 0.04), 0.6)
    plain("sign_fade", (0.5, 0.34, 0.28), 0.8)
    plain("stain", (0.18, 0.15, 0.1), 0.9)
    plain("conduit", (0.3, 0.3, 0.29), 0.5, 1.0)


# ------------------------------------------------------------------ geometry helpers

def recalc(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()


def _finish(name, me, key, uv, grp):
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    bkit.box_uv(obj, size=uv)
    bkit.assign(obj, MATS[key])
    GROUPS.setdefault(grp or key, []).append(obj)
    return obj


def rbox(name, c, s, key, uv=1.0, rz=0.0, rx=0.0, grp=None):
    """Box with centre c and size s, rotated about X (rx) then Z (rz). World-space UVs."""
    rot = Euler((rx, 0.0, rz)).to_matrix()
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    local = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
             (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    cv = Vector(c)
    verts = [tuple(cv + rot @ Vector(p)) for p in local]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    recalc(me)
    return _finish(name, me, key, uv, grp)


def flat(name, pts, z, key, uv=1.0, grp=None):
    """Single flat polygon at height z (points in XY), facing up."""
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if area < 0:
        pts = pts[::-1]
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new((p[0], p[1], z)) for p in pts]
    bm.faces.new(vs)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    return _finish(name, me, key, uv, grp)


def pipe(name, p0, p1, r, key, grp=None, segs=8):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    m4 = Matrix.Translation((p0 + p1) / 2) @ rot
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=r, radius2=r, depth=d.length, matrix=m4)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _finish(name, me, key, 0.5, grp)


def disc(name, cx, cy, r, z, key):
    n = 18
    pts = []
    for i in range(n):
        a = math.tau * i / n
        rr = r * rng.uniform(0.82, 1.08)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return flat(name, pts, z, key)


def rect_pts(cx, cy, w, h, rz):
    c, s = math.cos(rz), math.sin(rz)
    out = []
    for lx, ly in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        out.append((cx + c * lx - s * ly, cy + s * lx + c * ly))
    return out


def clip(poly, a, b, c):
    """Keep the part of poly where a*x + b*y <= c (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = a * p[0] + b * p[1] - c
        fq = a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def hazard(prefix, x0, x1, y0, y1, period=0.32, width=0.15):
    """Diagonal yellow/black hazard stripes clipped to a floor rectangle."""
    rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    umin, umax = x0 + y0, x1 + y1
    u = umin - period
    k = 0
    while u < umax:
        for lo, hi, key in ((u, u + width, "hz_y"), (u + width, u + period, "hz_k")):
            poly = clip(rect, -1, -1, -lo)
            poly = clip(poly, 1, 1, hi)
            if len(poly) >= 3:
                flat(f"{prefix}_{k}", poly, 0.004, key)
            k += 1
        u += period


def pallet(name, cx, cy, rz):
    """Euro-style pallet, 1.2 x 1.0 x 0.14 m, origin at its floor centre."""
    c, s = math.cos(rz), math.sin(rz)

    def w(lx, ly, lz):
        return (cx + c * lx - s * ly, cy + s * lx + c * ly, lz)

    for ly in (-0.46, 0.0, 0.46):
        rbox(f"{name}_bot", w(0, ly, 0.01), (1.2, 0.1, 0.02), "wood", uv=0.8, rz=rz)
    for lx in (-0.5, 0.0, 0.5):
        rbox(f"{name}_str", w(lx, 0, 0.07), (0.12, 1.0, 0.1), "wood", uv=0.8, rz=rz)
    for ly in (-0.4, -0.2, 0.0, 0.2, 0.4):
        rbox(f"{name}_deck", w(0, ly, 0.13), (1.2, 0.12, 0.02), "wood", uv=0.8, rz=rz)


def import_src(fname, name):
    objs = bkit.import_glb(f"{ROOT}/public/models/{fname}")
    src = objs[0]
    bkit.active(src)
    if src.parent:
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bkit.origin_to_bottom(src)  # origin bottom-centre, base on z = 0
    src.name = name
    return src


def place(src, name, x, y, z, rz=0.0):
    o = bpy.data.objects.new(name, src.data)
    bpy.context.scene.collection.objects.link(o)
    o.location = (x, y, z)
    o.rotation_euler = (0.0, 0.0, rz)
    return o


# ------------------------------------------------------------------ the zone

COLLIDERS = []   # [cx, cy, cz, sx, sy, sz, rotZ]
MARKERS = {}
PROP_OBJS = []


def collider(c, s, rz=0.0):
    COLLIDERS.append([round(c[0], 3), round(c[1], 3), round(c[2], 3),
                      round(s[0], 3), round(s[1], 3), round(s[2], 3), round(rz, 4)])


def build_shell():
    # floor and ceiling slabs (outside the box, so the walkable top is z = 0 and z = 4.0)
    rbox("A_floor_slab", (0, 8, -0.15), (12.6, 16.6, 0.3), "floor", uv=3.0)
    rbox("A_ceil_slab", (0, 8, 4.15), (12.6, 16.6, 0.3), "ceil", uv=3.0, grp="overhead")

    # side walls, flush with the start and far walls
    rbox("A_wall_w", (-6.15, 8.0, 2.0), (0.3, 16.0, 4.0), "wall", uv=2.5)
    rbox("A_wall_e", (6.15, 8.0, 2.0), (0.3, 16.0, 4.0), "wall", uv=2.5)

    # start wall (y -0.3..0): piers and lintel around the doorway
    rbox("A_start_pier_l", (-3.75, -0.15, 2.0), (5.1, 0.3, 4.0), "wall", uv=2.5)
    rbox("A_start_pier_r", (3.75, -0.15, 2.0), (5.1, 0.3, 4.0), "wall", uv=2.5)
    rbox("A_start_lintel", (0.0, -0.15, 3.5), (2.4, 0.3, 1.0), "wall", uv=2.5)
    # far wall (y 16..16.3)
    rbox("A_far_pier_l", (-3.75, 16.15, 2.0), (5.1, 0.3, 4.0), "wall", uv=2.5)
    rbox("A_far_pier_r", (3.75, 16.15, 2.0), (5.1, 0.3, 4.0), "wall", uv=2.5)
    rbox("A_far_lintel", (0.0, 16.15, 3.5), (2.4, 0.3, 1.0), "wall", uv=2.5)

    # steel door trim on the zone side of each doorway (4 cm proud of the wall)
    for y in (0.02, 15.98):
        rbox(f"A_trim_jl_{y}", (-1.26, y, 1.5), (0.12, 0.04, 3.0), "rust", uv=0.6)
        rbox(f"A_trim_jr_{y}", (1.26, y, 1.5), (0.12, 0.04, 3.0), "rust", uv=0.6)
        rbox(f"A_trim_lt_{y}", (0.0, y, 3.06), (2.64, 0.04, 0.12), "rust", uv=0.6)

    # start door leaf: hinged on the right jamb, hanging open flat against the wall
    rbox("A_start_leaf", (1.92, 0.07, 1.3), (1.2, 0.04, 2.6), "rust", uv=0.8)
    rbox("A_start_hinge_b", (1.33, 0.08, 0.35), (0.06, 0.06, 0.4), "rust", uv=0.4)
    rbox("A_start_hinge_t", (1.33, 0.08, 2.3), (0.06, 0.06, 0.4), "rust", uv=0.4)
    # far door: leaf missing, hinge knuckles and a broken latch left on the jambs
    rbox("A_far_hinge_b", (-1.33, 15.9, 0.35), (0.06, 0.06, 0.4), "rust", uv=0.4)
    rbox("A_far_hinge_t", (-1.33, 15.9, 2.3), (0.06, 0.06, 0.4), "rust", uv=0.4)
    rbox("A_far_latch", (1.3, 15.9, 1.4), (0.1, 0.05, 0.22), "rust", uv=0.4)

    # signs above the doorways
    rbox("A_sign_start", (0.0, 0.02, 3.35), (1.0, 0.02, 0.3), "sign_y", uv=0.5)
    rbox("A_sign_far", (0.0, 15.97, 3.35), (1.0, 0.02, 0.3), "sign_r", uv=0.5)

    # ceiling beams, pipes and duct (overhead group, hidden from the top view)
    rbox("A_beam_4", (0.0, 4.0, 3.8), (12.0, 0.3, 0.4), "painted", uv=1.0, grp="overhead")
    rbox("A_beam_12", (0.0, 12.0, 3.8), (12.0, 0.3, 0.4), "painted", uv=1.0, grp="overhead")
    rbox("A_duct", (2.75, 5.95, 3.475), (6.5, 0.7, 0.55), "painted", uv=1.0, grp="overhead")
    rbox("A_duct_flange", (2.75, 5.95, 3.2), (6.5, 0.8, 0.05), "rust", uv=1.0, grp="overhead")
    rbox("A_tray", (0.0, 9.0, 3.3), (11.8, 0.3, 0.04), "rubber", uv=1.0, grp="overhead")
    pipe("A_pipe_ceil", (-6.0, 8.0, 3.7), (6.0, 8.0, 3.7), 0.07, "rust", grp="overhead")
    pipe("A_pipe_w", (-5.9, 4.0, 3.2), (-5.9, 15.9, 3.2), 0.06, "rust", grp="overhead")
    pipe("A_pipe_drop", (5.78, 9.0, 0.0), (5.78, 9.0, 3.9), 0.06, "rust")
    for y in (4.0, 9.0, 14.0):
        rbox(f"A_pipe_brk_{y}", (5.78, y, 2.0), (0.1, 0.1, 0.05), "rust", uv=0.3)

    # ceiling fluorescent fixtures (6 along the walls; the one at (3, 8) is dead)
    for x, y in ((-3.0, 2.0), (3.0, 2.0), (-3.0, 8.0), (3.0, 8.0), (-3.0, 14.0), (3.0, 14.0)):
        rbox(f"A_fix_{x}_{y}", (x, y, 3.95), (1.2, 0.22, 0.06), "painted", uv=0.5, grp="overhead")
        rbox(f"A_diff_{x}_{y}", (x, y, 3.915), (1.15, 0.18, 0.01), "paper", uv=0.5, grp="overhead")


def build_cage():
    x0, x1, y0, y1 = -5.8, -2.7, 0.3, 3.4
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    h = 3.5
    # car floor plate, a few cm above the landing
    rbox("A_car_floor", (cx, cy, 0.015), (x1 - x0, y1 - y0, 0.03), "rust", uv=1.0)
    # posts
    for x in (x0, x1):
        for y in (y0, y1):
            rbox("A_car_post", (x, y, h / 2), (0.08, 0.08, h), "rust", uv=0.5)
    # mesh bars on back and both sides, horizontal rails
    n = 21
    for i in range(n):
        t = i / (n - 1)
        rbox("A_car_bar_b", (x0, y0 + t * (y1 - y0), h / 2), (0.025, 0.025, h), "rust", uv=0.5)
        rbox("A_car_bar_s0", (x0 + t * (x1 - x0), y0, h / 2), (0.025, 0.025, h), "rust", uv=0.5)
        rbox("A_car_bar_s1", (x0 + t * (x1 - x0), y1, h / 2), (0.025, 0.025, h), "rust", uv=0.5)
    for z in (0.8, 2.2, 3.4):
        rbox("A_car_rail_b", (x0, cy, z), (0.03, y1 - y0, 0.03), "rust", uv=0.5)
        rbox("A_car_rail_s0", (cx, y0, z), (x1 - x0, 0.03, 0.03), "rust", uv=0.5)
        rbox("A_car_rail_s1", (cx, y1, z), (x1 - x0, 0.03, 0.03), "rust", uv=0.5)
    # crosshead over the cage (overhead)
    rbox("A_car_crosshead", (cx, cy, 3.62), (x1 - x0 + 0.4, 0.2, 0.1), "rust", uv=1.0, grp="overhead")
    # folding gate jammed half open: the extended leaf runs y 0.3..1.9 across the front,
    # the folded part is bunched against the side at y 2.9..3.4 (the gap between is open)
    n_ext = 12
    for i in range(n_ext):
        y = y0 + i * (1.6 / (n_ext - 1))
        rbox("A_gate_slat", (x1, y, h / 2), (0.02, 0.02, h - 0.1), "rust", uv=0.3)
    for z in (0.15, h - 0.15):
        rbox("A_gate_rail", (x1, (y0 + 1.9) / 2, z), (0.03, 1.6, 0.03), "rust", uv=0.3)
    for i in range(10):
        y = 2.9 + i * 0.05
        rbox("A_gate_fold", (x1, y, h / 2), (0.02, 0.02, h - 0.1), "rust", uv=0.3)
    rbox("A_gate_fold_top", (x1, 3.15, h - 0.15), (0.03, 0.6, 0.04), "rust", uv=0.3)
    collider((x1, 1.1, h / 2), (0.1, 1.6, h))
    # control box on the back of the car, lit by the warm bulb in the roof
    rbox("A_car_ctrl", (-5.55, 2.9, 1.2), (0.22, 0.3, 0.42), "painted", uv=0.3)
    rbox("A_car_ctrl_lamp", (-5.43, 2.9, 1.45), (0.02, 0.1, 0.06), "sign_r", uv=0.2)
    collider((x0 + 0.06, cy, h / 2), (0.12, y1 - y0, h))
    collider((cx, y0 + 0.02, h / 2), (x1 - x0, 0.12, h))
    collider((cx, y1 - 0.02, h / 2), (x1 - x0, 0.12, h))


def build_booth():
    # guard booth, x 3.4..5.2, y 2.0..3.6, height 2.4; window faces the aisle (-x)
    rbox("A_booth_back", (5.16, 2.8, 1.2), (0.08, 1.6, 2.4), "painted", uv=1.0)
    rbox("A_booth_sy0", (4.3, 2.04, 1.2), (1.8, 0.08, 2.4), "painted", uv=1.0)
    rbox("A_booth_sy1", (4.3, 3.56, 1.2), (1.8, 0.08, 2.4), "painted", uv=1.0)
    rbox("A_booth_front_lo", (3.44, 2.8, 0.5), (0.08, 1.6, 1.0), "painted", uv=1.0)
    rbox("A_booth_front_hi", (3.44, 2.8, 2.2), (0.08, 1.6, 0.4), "painted", uv=1.0)
    rbox("A_booth_pil_0", (3.44, 2.15, 1.5), (0.08, 0.3, 1.0), "painted", uv=1.0)
    rbox("A_booth_pil_1", (3.44, 3.45, 1.5), (0.08, 0.3, 1.0), "painted", uv=1.0)
    rbox("A_booth_roof", (4.3, 2.8, 2.44), (1.8, 1.6, 0.08), "painted", uv=1.0, grp="overhead")
    rbox("A_booth_glass", (3.44, 2.8, 1.5), (0.02, 1.0, 1.0), "glass", uv=1.0)
    # inside: counter and dead CRT (visible through the window)
    rbox("A_counter", (3.7, 2.8, 0.5), (0.45, 1.4, 1.0), "wood", uv=0.8)
    rbox("A_crt_body", (3.72, 2.8, 1.2), (0.36, 0.42, 0.36), "rubber", uv=0.5)
    rbox("A_crt_screen", (3.52, 2.8, 1.2), (0.03, 0.3, 0.27), "glass", uv=0.3)
    rbox("A_crt_base", (3.8, 2.8, 1.0), (0.28, 0.3, 0.03), "rubber", uv=0.5)
    rbox("A_booth_paper_in", (3.8, 3.1, 1.03), (0.2, 0.15, 0.01), "paper", uv=0.3)
    # sign-in clipboard hung outside the window
    rbox("A_clipboard", (3.355, 2.45, 1.45), (0.03, 0.26, 0.34), "wood", uv=0.4)
    rbox("A_clip_sheet", (3.33, 2.46, 1.42), (0.01, 0.21, 0.28), "paper", uv=0.3)
    collider((4.3, 2.8, 1.2), (1.8, 1.6, 2.4))


def build_stairs():
    # stairwell at the far east corner: stepped run rising along +y, gated at the bottom
    x0, x1 = 4.0, 5.4
    run, rise, n = 0.28, 0.18, 15
    total_rise = rise * n
    total_run = run * n
    theta = math.atan2(total_rise, total_run)
    slope_len = math.hypot(total_rise, total_run)
    for i in range(n):
        top = rise * (i + 1)
        yc = 11.0 + run * i + run / 2
        rbox(f"A_tread_{i}", ((x0 + x1) / 2, yc, top - 0.02), (x1 - x0, run - 0.02, 0.04),
             "painted", uv=0.8)
    ymid = 11.0 + total_run / 2
    for x in (x0 + 0.04, x1 - 0.04):
        rbox("A_stringer", (x, ymid, total_rise / 2), (0.08, slope_len, 0.12), "painted",
             uv=0.8, rx=theta)
        s, c = math.sin(theta), math.cos(theta)
        rbox("A_handrail", (x, ymid - s * 0.9, total_rise / 2 + c * 0.9), (0.05, slope_len, 0.05),
             "rust", uv=0.5, rx=theta)
    rbox("A_landing_top", ((x0 + x1) / 2, 15.55, 2.65), (x1 - x0, 0.7, 0.1), "painted", uv=0.8)
    # the top landing is carried on four posts down to the floor
    for x in (x0 + 0.1, x1 - 0.1):
        for y in (15.3, 15.85):
            rbox("A_landing_post", (x, y, 1.3), (0.1, 0.1, 2.6), "rust", uv=0.4)
    rbox("A_landing_brace", ((x0 + x1) / 2, 15.3, 1.1), (x1 - x0, 0.06, 0.06), "rust", uv=0.4)
    # service hatch on the landing wall, chained shut
    rbox("A_hatch", ((x0 + x1) / 2, 15.955, 3.3), (1.1, 0.05, 1.05), "rust", uv=0.6)
    rbox("A_hatch_bar", ((x0 + x1) / 2, 15.92, 3.3), (1.1, 0.03, 0.05), "rust", uv=0.4)
    for x in (4.25, 5.15):
        rbox("A_hatch_chain", (x, 15.9, 3.3), (0.03, 0.03, 1.05), "rust", uv=0.2)
    rbox("A_hatch_lock", (4.7, 15.9, 3.3), (0.12, 0.06, 0.12), "rubber", uv=0.2)
    collider(((x0 + x1) / 2, 13.45, total_rise / 2), (x1 - x0, 4.9, total_rise))
    # chain-link style gate across the bottom step, closed
    yg = 10.9
    rbox("A_gate_post_0", (x0, yg, 0.9), (0.05, 0.05, 1.8), "rust", uv=0.4)
    rbox("A_gate_post_1", (x1, yg, 0.9), (0.05, 0.05, 1.8), "rust", uv=0.4)
    rbox("A_gate_top", ((x0 + x1) / 2, yg, 1.8), (x1 - x0, 0.03, 0.03), "rust", uv=0.4)
    rbox("A_gate_bot", ((x0 + x1) / 2, yg, 0.05), (x1 - x0, 0.03, 0.03), "rust", uv=0.4)
    for k in range(15):
        x = x0 + k * (x1 - x0) / 14
        rbox("A_gate_bar", (x, yg, 0.9), (0.02, 0.02, 1.8), "rust", uv=0.4)
    rbox("A_gate_sign", ((x0 + x1) / 2, yg - 0.05, 1.35), (0.5, 0.01, 0.3), "sign_r", uv=0.4)
    collider(((x0 + x1) / 2, yg, 0.9), (x1 - x0, 0.06, 1.8))
    hazard("A_hz_gate", x0, x1, 10.25, 10.78, period=0.3, width=0.13)


def build_pallets_and_props():
    crate = import_src("crate.glb", "A_crate_src")
    plush = import_src("plush_pile.glb", "A_plush_src")
    fuse = import_src("fusebox.glb", "A_fusebox_src")

    # pallet 1: two crates stacked
    pallet("A_pal1", -4.4, 9.4, 0.05)
    PROP_OBJS.append(place(crate, "A_crate_1a", -4.42, 9.42, 0.14, 0.05))
    PROP_OBJS.append(place(crate, "A_crate_1b", -4.38, 9.38, 1.10, -0.06))
    collider((-4.4, 9.4, 1.03), (1.1, 1.05, 2.06), 0.05)

    # pallet 2: cardboard, 2 layers of 2x2 boxes
    rz2 = -0.1
    pallet("A_pal2", -4.2, 11.8, rz2)
    c2, s2 = math.cos(rz2), math.sin(rz2)
    for layer in range(2):
        for ix in (-0.3, 0.3):
            for iy in (-0.26, 0.26):
                lx, ly = ix, iy
                wx = -4.2 + c2 * lx - s2 * ly
                wy = 11.8 + s2 * lx + c2 * ly
                z0 = 0.14 + layer * 0.4
                rbox("A_carton", (wx, wy, z0 + 0.2), (0.58, 0.48, 0.4), "cardboard",
                     uv=0.6, rz=rz2 + rng.uniform(-0.05, 0.05))
    collider((-4.2, 11.8, 0.54), (1.25, 1.05, 0.8), rz2)

    # pallet 3: one loose crate on it, plush heap on the floor beside it
    pallet("A_pal3", -4.8, 4.5, -0.02)
    PROP_OBJS.append(place(crate, "A_crate_3", -4.8, 4.5, 0.14, -0.02))
    collider((-4.8, 4.5, 0.55), (1.1, 1.05, 1.1), -0.02)
    PROP_OBJS.append(place(plush, "A_plush_heap", -4.6, 6.6, 0.0, 0.6))
    collider((-4.6, 6.6, 0.38), (0.8, 1.36, 0.76), 0.6)

    # fusebox mounted on the west wall, front facing +x (rz +90 deg)
    PROP_OBJS.append(place(fuse, "A_fusebox", -5.7725, 9.5, 0.9, math.pi / 2))
    collider((-5.545, 9.5, 1.9), (0.455, 0.9, 2.0))

    for s in (crate, plush, fuse):
        bpy.data.objects.remove(s, do_unlink=True)


def build_debris():
    # puddles, drains, paper, fallen ceiling tiles, broken toys, concrete chunks
    for i, (x, y, r) in enumerate(((1.0, 4.6, 0.5), (-2.6, 10.8, 0.55), (3.0, 12.6, 0.42),
                                   (-0.8, 14.6, 0.35), (4.6, 6.2, 0.4))):
        disc(f"A_puddle_{i}", x, y, r, 0.002, "puddle")
    for i, (x, y) in enumerate(((-0.6, 2.6), (2.2, 11.6), (-2.3, 6.1))):
        disc(f"A_drain_{i}", x, y, 0.12, 0.003, "drain")

    def in_cage(x, y):
        return -5.9 < x < -2.6 and 0.2 < y < 3.5

    def in_booth(x, y):
        return 3.3 < x < 5.3 and 1.9 < y < 3.7

    def in_stairs(x, y):
        return 3.9 < x < 5.5 and 10.8 < y < 16

    n = 0
    while n < 30:
        x, y = rng.uniform(-5.4, 5.4), rng.uniform(0.6, 15.4)
        if in_cage(x, y) or in_booth(x, y) or in_stairs(x, y):
            continue
        flat(f"A_paper_{n}", rect_pts(x, y, 0.21, 0.297, rng.uniform(0, math.tau)), 0.003, "paper")
        n += 1

    for i, (x, y, rz) in enumerate(((-2.4, 14.9, 0.4), (2.4, 14.4, 2.1))):
        rbox(f"A_ceiltile_{i}", (x, y, 0.1), (0.6, 0.6, 0.02), "paper", uv=0.5, rz=rz, rx=0.22)
    for i, (x, y) in enumerate(((-0.6, 15.1), (2.9, 15.3), (-3.4, 14.5))):
        s = rng.uniform(0.22, 0.34)
        rbox(f"A_chunk_{i}", (x, y, s * 0.3), (s, s * 0.8, s * 0.6), "floor", uv=1.0,
             rz=rng.uniform(0, math.tau), rx=rng.uniform(-0.2, 0.2))
    for i, (x, y, key) in enumerate(((-1.5, 6.9, "sign_r"), (-0.9, 7.5, "sign_y"),
                                     (1.6, 4.2, "sign_y"), (-2.0, 13.4, "sign_r"))):
        rbox(f"A_toy_{i}", (x, y, 0.03), (0.12, 0.08, 0.05), key, uv=0.2,
             rz=rng.uniform(0, math.tau))

    # hazard stripes at the cage door, and the notice board with pinned notes
    hazard("A_hz_cage", -2.62, -2.2, 0.3, 3.4, period=0.32, width=0.15)
    rbox("A_notice", (5.97, 7.2, 1.7), (0.04, 1.2, 1.0), "cork", uv=0.6)
    for i, (y, z) in enumerate(((6.85, 1.95), (7.3, 1.45), (7.5, 2.0))):
        rbox(f"A_note_{i}", (5.935, y, z), (0.01, 0.2, 0.26), "paper", uv=0.2)
    rbox("A_sign_wall", (-5.97, 13.6, 1.7), (0.03, 0.6, 0.45), "sign_y", uv=0.5)


def vquad(name, pts, key, normal):
    """Planar polygon on a wall; pts are 3D, normal says which way the face must point."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    if f.normal.dot(Vector(normal)) < 0:
        f.normal_flip()
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    return _finish(name, me, key, 0.5, None)


def build_clutter():
    """Pallets and cartons, conduit and cable trays, a fire hose cabinet, faded signs, stains."""
    # two more pallets with cartons
    for name, cx, cy, rz, layers in (("A_pal4", 4.4, 7.4, 0.12, 2), ("A_pal5", -4.4, 14.6, -0.15, 1)):
        pallet(name, cx, cy, rz)
        c, s = math.cos(rz), math.sin(rz)
        for layer in range(layers):
            for ix in (-0.3, 0.3):
                for iy in (-0.26, 0.26):
                    wx = cx + c * ix - s * iy
                    wy = cy + s * ix + c * iy
                    rbox(f"{name}_carton", (wx, wy, 0.14 + layer * 0.4 + 0.2), (0.58, 0.48, 0.4),
                         "cardboard", uv=0.6, rz=rz + rng.uniform(-0.05, 0.05))
        collider((cx, cy, 0.14 + layers * 0.2), (1.1, 1.05, 0.14 + layers * 0.4), rz)
    # loose cartons on the floor by the booth wall
    for i, (x, y, rz) in enumerate(((2.9, 0.9, 0.3), (3.3, 0.7, -0.2), (2.6, 14.9, 0.5))):
        rbox(f"A_loose_carton_{i}", (x, y, 0.2), (0.5, 0.4, 0.4), "cardboard", uv=0.6, rz=rz)

    # conduit runs along the walls, with brackets
    pipe("A_conduit_e", (5.84, 4.5, 2.4), (5.84, 10.4, 2.4), 0.035, "conduit")
    pipe("A_conduit_w", (-5.9, 4.2, 2.4), (-5.9, 8.8, 2.4), 0.035, "conduit")
    for y in (5.0, 7.5, 10.0):
        rbox(f"A_conduit_brk_e_{y}", (5.9, y, 2.4), (0.12, 0.06, 0.12), "conduit", uv=0.2)
    for y in (5.0, 7.5):
        rbox(f"A_conduit_brk_w_{y}", (-5.93, y, 2.4), (0.12, 0.06, 0.12), "conduit", uv=0.2)
    # cable trays and a second duct at the ceiling
    rbox("A_tray_2", (-2.0, 8.0, 3.45), (0.4, 15.0, 0.04), "rubber", uv=1.0, grp="overhead")
    rbox("A_duct_2", (-2.75, 13.0, 3.45), (3.5, 0.6, 0.5), "painted", uv=1.0, grp="overhead")

    # fire hose cabinet on the east wall near the start (red box, white door)
    rbox("A_hose_box", (5.87, 0.9, 1.0), (0.22, 0.6, 0.8), "sign_r", uv=0.3)
    rbox("A_hose_door", (5.745, 0.9, 1.0), (0.02, 0.56, 0.76), "paper", uv=0.3)
    rbox("A_hose_reel", (5.78, 0.9, 0.5), (0.08, 0.3, 0.12), "rubber", uv=0.2)
    collider((5.87, 0.9, 0.4), (0.22, 0.6, 0.8))

    # faded 1990s safety signs and a stencilled notice
    rbox("A_sign_fade_w", (-5.97, 6.5, 1.7), (0.03, 0.5, 0.4), "sign_fade", uv=0.3)
    rbox("A_sign_fade_e", (5.97, 9.6, 1.9), (0.03, 0.5, 0.25), "sign_fade", uv=0.3)
    rbox("A_sign_fade_k", (-2.0, 15.97, 2.2), (0.6, 0.02, 0.3), "sign_fade", uv=0.3)

    # water stains running down the walls from the ceiling
    vquad("A_stain_w1", [(-5.995, 5.0, 3.9), (-5.995, 5.6, 3.9), (-5.995, 5.5, 2.0),
                         (-5.995, 5.25, 1.2), (-5.995, 5.0, 2.2)], "stain", (1, 0, 0))
    vquad("A_stain_w2", [(-5.995, 11.2, 3.9), (-5.995, 12.0, 3.9), (-5.995, 11.8, 1.4),
                         (-5.995, 11.4, 0.6), (-5.995, 11.2, 1.8)], "stain", (1, 0, 0))
    vquad("A_stain_e1", [(5.995, 3.0, 3.9), (5.995, 3.9, 3.9), (5.995, 3.7, 2.5),
                         (5.995, 3.4, 1.6)], "stain", (-1, 0, 0))
    vquad("A_stain_f1", [(-4.2, 15.995, 3.9), (-3.4, 15.995, 3.9), (-3.6, 15.995, 2.6),
                         (-3.9, 15.995, 1.5)], "stain", (0, -1, 0))
    vquad("A_stain_s1", [(3.2, 0.005, 3.9), (4.0, 0.005, 3.9), (3.8, 0.005, 2.2)],
          "stain", (0, 1, 0))


def build_markers_colliders():
    collider((-6.15, 8.0, 2.0), (0.3, 16.0, 4.0))
    collider((6.15, 8.0, 2.0), (0.3, 16.0, 4.0))
    collider((-3.75, -0.15, 2.0), (5.1, 0.3, 4.0))
    collider((3.75, -0.15, 2.0), (5.1, 0.3, 4.0))
    collider((-3.75, 16.15, 2.0), (5.1, 0.3, 4.0))
    collider((3.75, 16.15, 2.0), (5.1, 0.3, 4.0))
    collider((4.7, 10.92, 0.9), (1.4, 0.06, 1.8))
    MARKERS.update({
        "entry": [-4.25, 1.85, 0.0],
        "exit": [0.0, 15.2, 0.0],
        "start_door": [0.0, 0.8, 0.0],
        "clipboard": [3.2, 2.55, 1.4],
        "hide_pallets": [-3.0, 11.8, 0.0],
        "stair_gate": [4.7, 10.3, 0.0],
    })


LIGHTS = [
    {"pos": [-3.0, 2.0, 3.8], "color": "#cfe4ff", "intensity": 1.0, "range": 9, "flicker": False},
    {"pos": [3.0, 2.0, 3.8], "color": "#cfe4ff", "intensity": 1.0, "range": 9, "flicker": True},
    {"pos": [-3.0, 8.0, 3.8], "color": "#cfe4ff", "intensity": 1.0, "range": 9, "flicker": False},
    {"pos": [-3.0, 14.0, 3.8], "color": "#cfe4ff", "intensity": 1.0, "range": 9, "flicker": True},
    {"pos": [3.0, 14.0, 3.8], "color": "#cfe4ff", "intensity": 1.0, "range": 9, "flicker": False},
    {"pos": [4.3, 2.8, 1.9], "color": "#ffb060", "intensity": 0.6, "range": 4, "flicker": False},
    {"pos": [-4.25, 1.85, 3.2], "color": "#ffb060", "intensity": 0.5, "range": 5, "flicker": True},
    {"pos": [4.7, 14.0, 2.9], "color": "#ff9a50", "intensity": 0.5, "range": 5, "flicker": False},
]


def hex_lin(h):
    h = h.lstrip("#")
    return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4))


def preview_lights():
    """Dim, cold preview lighting. Lights are not exported; the JSON lists them."""
    world = bpy.data.worlds.new("A_dark")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.004, 0.004, 0.005, 1)
    bg.inputs["Strength"].default_value = 1.0
    for i, L in enumerate(LIGHTS):
        if L["range"] >= 8:  # fluorescent tube
            ld = bpy.data.lights.new(f"prev_tube_{i}", "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = 1.2, 0.2
            ld.energy = 22.0 * L["intensity"]
        else:
            ld = bpy.data.lights.new(f"prev_warm_{i}", "POINT")
            ld.energy = 5.0 * L["intensity"]
            ld.shadow_soft_size = 0.05
        ld.color = hex_lin(L["color"])
        o = bpy.data.objects.new(ld.name, ld)
        bpy.context.scene.collection.objects.link(o)
        o.location = L["pos"]


def set_render(res, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"


def render_eye(path, pos, target):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("A_eye_cam")
    cd.lens = 24
    cd.clip_start, cd.clip_end = 0.05, 40.0
    cam = bpy.data.objects.new("A_eye_cam", cd)
    sc.collection.objects.link(cam)
    cam.location = pos
    d = Vector(target) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.cameras.remove(cd)
    return path


def render_top(path):
    sc = bpy.context.scene
    for o in GROUPS_OVERHEAD:
        o.hide_render = True
    cd = bpy.data.cameras.new("A_top_cam")
    cd.type = "ORTHO"
    cd.ortho_scale = 18.0
    cd.clip_start, cd.clip_end = 0.1, 50.0
    cam = bpy.data.objects.new("A_top_cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (0.0, 8.0, 30.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.cameras.remove(cd)
    return path


def compose_sheet(paths, out, tile):
    """2x2 contact sheet; pixel rows are bottom-up, so the top row is written last."""
    import numpy as np
    tiles = []
    for p in paths:
        im = bpy.data.images.load(p, check_existing=False)
        tiles.append(np.array(im.pixels[:]).reshape(tile, tile, 4))
        bpy.data.images.remove(im)
    arr = np.vstack([np.hstack(tiles[2:4]), np.hstack(tiles[0:2])])
    img = bpy.data.images.new("A_sheet", tile * 2, tile * 2)
    img.pixels = arr.ravel()
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return out


GROUPS_OVERHEAD = []
EYE_VIEWS = [
    ((0.0, 6.0, 1.6), (0.0, 16.0, 1.4)),    # far doorway
    ((0.0, 3.0, 1.6), (0.0, -0.5, 1.5)),    # start doorway, leaf hanging open on the right
    ((0.6, 1.9, 1.6), (-4.4, 1.9, 1.3)),    # freight car, half-open gate and control box
    ((0.6, 9.0, 1.6), (4.6, 13.0, 1.3)),    # stairwell and gate
]


def build():
    bkit.reset_scene()
    make_materials()
    build_shell()
    build_cage()
    build_booth()
    build_stairs()
    build_pallets_and_props()
    build_debris()
    build_clutter()
    build_markers_colliders()

    # join each static material group into one mesh (the overhead group is kept apart)
    shell_objs = []
    for key, objs in GROUPS.items():
        if len(objs) == 1:
            joined = objs[0]
            joined.name = f"A_{key}"
        else:
            joined = bkit.join(objs, f"A_{key}")
        shell_objs.append(joined)
        if key == "overhead":
            GROUPS_OVERHEAD.append(joined)  # ceiling slab, beams, pipes, fixtures, duct

    shell_tris = sum(bkit.tri_count(o) for o in shell_objs)
    prop_tris = sum(bkit.tri_count(o) for o in PROP_OBJS)
    print(f"A_REPORT shell_tris={shell_tris} prop_copies_tris={prop_tris} "
          f"shell_objects={len(shell_objs)} materials={len(MATS)}")
    return shell_tris, prop_tris


def export_all():
    os.makedirs(os.path.dirname(GLB), exist_ok=True)
    bkit.export_glb(GLB, image_format="JPEG")
    data = {"zone": "A", "colliders": COLLIDERS, "lights": LIGHTS, "markers": MARKERS}
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("A_EXPORT glb_bytes", os.path.getsize(GLB), "json", JSON_OUT)


def save_blend():
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build"]
    mode = args[0]
    os.makedirs(SCRATCH, exist_ok=True)

    if mode == "build":
        build()
        export_all()
        preview_lights()
        save_blend()
        set_render(PREVIEW, SAMPLES)
        eye_paths = []
        for i, (pos, tgt) in enumerate(EYE_VIEWS):
            eye_paths.append(render_eye(f"{SCRATCH}/eye_{i}.png", pos, tgt))
        os.makedirs(RENDER_DIR, exist_ok=True)
        compose_sheet(eye_paths, f"{RENDER_DIR}/ch2_{NAME}_eye.png", PREVIEW)
        set_render(900, SAMPLES)
        render_top(f"{RENDER_DIR}/ch2_{NAME}_top.png")
        print("A_RENDERS done")

    elif mode == "verify":
        # fresh scene: import only the shipped GLB and light it from the JSON
        bkit.reset_scene()
        objs = bkit.import_glb(GLB)
        print("A_VERIFY imported mesh objects:", len(objs))
        preview_lights()
        set_render(PREVIEW, SAMPLES)
        render_eye(f"{SCRATCH}/verify_eye.png", (-4.25, 1.85, 1.6), (-0.5, 4.0, 1.4))
        render_eye(f"{SCRATCH}/verify_eye_stairs.png", (0.6, 9.0, 1.6), (4.6, 13.0, 1.3))
        print("A_VERIFY done")


main()
