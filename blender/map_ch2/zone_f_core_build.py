"""Chapter 2, zone F: Eternal Joy machine chamber (finale).

Run headless from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/map_ch2/zone_f_core_build.py

Coordinates follow blender/map_ch2/BRIEF.md: floor at z=0, route along +Y,
interior box x -12..12, y 144..170, ceiling 9.0. The near boundary (y=144) is
built by zone E, so this zone builds only its side walls, far wall, ceiling and
floor. The walkable room is an octagon inside the box (3 m chamfers).
"""
import sys
import os
import math
import json
import random
import tempfile

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")

import numpy as np
import bpy
import bmesh
from mathutils import Vector
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_f_core"
OUT_GLB = f"{ROOT}/public/models/ch2/{NAME}.glb"
OUT_JSON = f"{ROOT}/public/models/ch2/{NAME}.json"
OUT_BLEND = f"{ROOT}/blender/bake/map_ch2/{NAME}.blend"
OUT_EYE = f"{ROOT}/renders/ch2_{NAME}_eye.png"
OUT_TOP = f"{ROOT}/renders/ch2_{NAME}_top.png"
TMP = os.path.join(tempfile.gettempdir(), f"{NAME}_tex")
os.makedirs(TMP, exist_ok=True)

# ---- zone geometry (BRIEF) ----
X0, X1, Y0, Y1, CEIL = -12.0, 12.0, 144.0, 170.0, 9.0
WT = 0.3          # wall thickness
CHAMFER = 3.0     # octagon corner cut
CX_ROOM, CY_ROOM = 0.0, 157.0
MACH_X, MACH_Y, MACH_S = 0.0, 158.0, 2.5
MACH_HALF_X, MACH_HALF_Y = 0.869 * MACH_S, 0.477 * MACH_S   # joy_machine.glb bounds x 1.738, y 0.954
MACH_TOP = 2.799 * MACH_S

random.seed(7)
rng = np.random.default_rng(7)
scene = bpy.context.scene


def link(ob):
    scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- mesh helpers

def box(name, c, s, mat, rot=0.0, uv=1.0):
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    loc = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
           (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    cs, sn = math.cos(rot), math.sin(rot)
    verts = [(c[0] + x * cs - y * sn, c[1] + x * sn + y * cs, c[2] + z) for x, y, z in loc]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    bkit.box_uv(ob, size=uv)
    return ob


def _catmull(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


def tube(name, pts, r, mat, sides=10, step=5, uv_m=1.0):
    """Swept tube along a smooth polyline (cables, pipes, rods, discs with 2 points)."""
    P = [Vector(p) for p in pts]
    D = []
    if len(P) == 2:
        for k in range(step + 1):
            D.append(P[0].lerp(P[1], k / step))
    else:
        n = len(P)
        for i in range(n - 1):
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
            for k in range(step):
                D.append(_catmull(p0, p1, p2, p3, k / step))
        D.append(P[-1])
    m = len(D)
    S = sides
    S_len = [0.0]
    for i in range(1, m):
        S_len.append(S_len[-1] + (D[i] - D[i - 1]).length)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for i in range(m):
        t = (D[min(i + 1, m - 1)] - D[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        nrm = t.cross(ref).normalized()
        bi = t.cross(nrm).normalized()
        ring = []
        for j in range(S):
            a = 2 * math.pi * j / S
            ring.append(bm.verts.new(D[i] + (nrm * math.cos(a) + bi * math.sin(a)) * r))
        rings.append(ring)
    circ = 2 * math.pi * r * uv_m
    for i in range(m - 1):
        u0, u1 = S_len[i] * uv_m, S_len[i + 1] * uv_m
        for j in range(S):
            a = rings[i][j]
            b = rings[i][(j + 1) % S]
            c = rings[i + 1][(j + 1) % S]
            d = rings[i + 1][j]
            f = bm.faces.new((a, b, c, d))
            v0, v1 = j / S * circ, (j + 1) / S * circ
            for loop, uv in zip(f.loops, [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]):
                loop[uvl].uv = uv
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        vs = list(reversed(ring)) if rev else ring
        f = bm.faces.new(vs)
        for loop in f.loops:
            loop[uvl].uv = (loop.vert.co.x * uv_m, loop.vert.co.y * uv_m)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def plane(name, c, u, v, w, h, mat):
    """Flat decal. Its normal is u x v, so pick u and v to face the room."""
    u = Vector(u).normalized()
    v = Vector(v).normalized()
    cc = Vector(c)
    corners = [(cc - u * w / 2 - v * h / 2, (0, 0)), (cc + u * w / 2 - v * h / 2, (1, 0)),
               (cc + u * w / 2 + v * h / 2, (1, 1)), (cc - u * w / 2 + v * h / 2, (0, 1))]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p) for p, _ in corners]
    f = bm.faces.new(vs)
    for loop, (_, uv) in zip(f.loops, corners):
        loop[uvl].uv = uv
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def flat(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def join_group(objs, name):
    return bkit.join(objs, name)


def save_img(path, rgb):
    h, w = rgb.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb[..., :3], 0, 1)
    im = bpy.data.images.new("tmp_" + os.path.basename(path), w, h, alpha=False)
    im.pixels.foreach_set(rgba[::-1].ravel())   # Blender images are bottom-up
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return path


# ---------------------------------------------------------------- painted textures

def make_mural(path):
    """Unsettling painted smiley on the far wall: faded, drips, too-wide grin."""
    W, H = 1024, 683
    yy, xx = np.mgrid[0:H, 0:W]
    v = (H - 1 - yy) / H           # height units from the bottom
    x = xx / H                     # height units from the left
    img = np.zeros((H, W, 3))
    img[:] = [0.42, 0.48, 0.40]
    img += rng.normal(0, 0.025, (H, W, 1))
    col = rng.random(W) ** 5
    img -= col[None, :, None] * 0.25 * (1 - v)[:, :, None]     # paint runs from the top
    X = x - W / (2 * H)
    Y = v - 0.48
    d = np.sqrt(X ** 2 + Y ** 2)
    face = d < 0.36
    img[face] = (np.array([0.80, 0.70, 0.40])[None, None, :]
                 + rng.normal(0, 0.03, (H, W, 1)))[face]
    img[(d >= 0.348) & (d < 0.36)] = [0.22, 0.10, 0.07]
    eyeL = ((X + 0.17) / 0.065) ** 2 + ((Y - 0.14) / 0.11) ** 2 < 1
    eyeR = ((X - 0.14) / 0.05) ** 2 + ((Y - 0.16) / 0.13) ** 2 < 1
    rim = (((X + 0.17) / 0.08) ** 2 + ((Y - 0.14) / 0.13) ** 2 < 1) & ~eyeL
    img[rim] = [0.45, 0.12, 0.08]
    img[eyeL | eyeR] = [0.04, 0.03, 0.03]
    t = np.clip(X / 0.27, -1.0, 1.0)
    vc = -0.16 + 0.10 * t ** 2
    th = 0.035 + 0.025 * (1 - t ** 2)
    mouth = (np.abs(X) < 0.27) & (np.abs(Y - vc) < th)
    img[mouth] = [0.30, 0.04, 0.05]
    teeth = mouth & ((Y - vc) > 0.0) & (np.floor(X / 0.035) % 2 == 0)
    img[teeth] = [0.93, 0.90, 0.84]
    cheek = (((X + 0.27) / 0.09) ** 2 + ((Y + 0.05) / 0.06) ** 2 < 1) | \
            (((X - 0.27) / 0.09) ** 2 + ((Y + 0.05) / 0.06) ** 2 < 1)
    img[cheek & face] = img[cheek & face] * 0.6 + np.array([0.5, 0.12, 0.12]) * 0.4
    return save_img(path, img)


def make_hazard(path):
    N = 256
    yy, xx = np.mgrid[0:N, 0:N]
    s = ((xx + yy) // 64) % 2
    base = np.where(s[..., None] == 0, np.array([0.92, 0.72, 0.06]), np.array([0.05, 0.05, 0.045]))
    base = base + rng.normal(0, 0.04, (N, N, 1))
    base = base * (0.8 + 0.2 * rng.random((N, N, 1)))   # dirt
    return save_img(path, base)


def make_sign(path):
    N = 512
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    img = np.zeros((N, N, 3))
    img[:] = [0.84, 0.82, 0.70]
    img += rng.normal(0, 0.02, (N, N, 1))

    def in_tri(P, A, B, C):
        def sgn(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = sgn(P, A, B), sgn(P, B, C), sgn(P, C, A)
        neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
        pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        return ~(neg & pos)
    A, B, C = (256, 60), (60, 430), (452, 430)
    G = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
    inner = [(G[0] + 0.8 * (p[0] - G[0]), G[1] + 0.8 * (p[1] - G[1])) for p in (A, B, C)]
    P = (xx, yy)
    out = in_tri(P, A, B, C)
    ins = in_tri(P, *inner)
    img[out] = [0.72, 0.12, 0.09]
    img[ins] = [0.92, 0.90, 0.84]
    bar = (xx > 236) & (xx < 276) & (yy > 170) & (yy < 330)
    dot = (xx > 236) & (xx < 276) & (yy > 350) & (yy < 384)
    img[(bar | dot) & ins] = [0.05, 0.05, 0.05]
    return save_img(path, img)


# ---------------------------------------------------------------- materials

def build_materials():
    ph = {k: bkit.polyhaven_texture(k) for k in
          ["concrete_floor_worn_001", "peeling_painted_wall", "concrete_wall_006",
           "rusty_metal_02", "metal_plate"]}
    M = {}
    M["floor"] = bkit.pbr_material("F_concrete_floor", ph["concrete_floor_worn_001"])
    M["wall"] = bkit.pbr_material("F_painted_wall", ph["peeling_painted_wall"], scale=0.7, tint=(0.82, 0.9, 0.95))
    M["wall2"] = bkit.pbr_material("F_painted_wall_b", ph["peeling_painted_wall"], scale=0.55, tint=(0.95, 0.96, 0.98))
    M["ceil"] = bkit.pbr_material("F_ceiling_concrete", ph["concrete_wall_006"], tint=(0.85, 0.87, 0.9))
    M["grime"] = flat("F_grime_dark", (0.06, 0.055, 0.045), 0.9)
    M["rust"] = bkit.pbr_material("F_rust", ph["rusty_metal_02"])
    M["metal"] = bkit.pbr_material("F_metal_plate", ph["metal_plate"])
    M["cable"] = flat("F_cable_rubber", (0.015, 0.015, 0.014), 0.55)
    M["puddle"] = flat("F_puddle_water", (0.010, 0.014, 0.018), 0.03)
    M["drain"] = flat("F_drain_grate", (0.09, 0.09, 0.085), 0.5, 0.8)
    M["tile"] = flat("F_ceiling_tile", (0.52, 0.47, 0.36), 0.95)
    M["fix"] = flat("F_fixture_plastic", (0.62, 0.60, 0.52), 0.45)
    M["paper"] = flat("F_paper_sheet", (0.66, 0.63, 0.52), 0.9)
    M["mural"] = bkit.pbr_material("F_mural_paint", {"color": make_mural(f"{TMP}/mural.png")})
    M["hazard"] = bkit.pbr_material("F_hazard_paint", {"color": make_hazard(f"{TMP}/hazard.png")})
    M["sign"] = bkit.pbr_material("F_sign_plate", {"color": make_sign(f"{TMP}/sign.png")})
    return M


# ---------------------------------------------------------------- scene build

def build_shell(M):
    parts = {}
    # walls: three flat walls plus four chamfer walls (octagon inside the box)
    walls = [box("F_wall_w", (X0 - WT / 2, 157.0, 4.5), (WT, 20.0, CEIL), M["wall"], uv=2.5),
             box("F_wall_e", (X1 + WT / 2, 157.0, 4.5), (WT, 20.0, CEIL), M["wall2"], uv=2.5),
             box("F_wall_far", (0.0, Y1 + WT / 2, 4.5), (18.0, WT, CEIL), M["wall"], uv=2.5),
             # dirty skirting along the flat walls (proud of the wall face)
             box("F_skirt_e", (11.99, 157.0, 0.25), (0.04, 20.0, 0.5), M["grime"], uv=1.0),
             box("F_skirt_w", (-11.99, 157.0, 0.25), (0.04, 20.0, 0.5), M["grime"], uv=1.0),
             box("F_skirt_far", (0.0, 169.99, 0.25), (18.0, 0.04, 0.5), M["grime"], uv=1.0)]
    corners = [((X0, Y0 + CHAMFER), (X0 + CHAMFER, Y0)),
               ((X1 - CHAMFER, Y0), (X1, Y0 + CHAMFER)),
               ((X1, Y1 - CHAMFER), (X1 - CHAMFER, Y1)),
               ((X0 + CHAMFER, Y1), (X0, Y1 - CHAMFER))]
    colliders_diag = []
    for k, (A, B) in enumerate(corners):
        A, B = Vector(A), Vector(B)
        seg = B - A
        L = seg.length
        d = seg / L
        n = Vector((-d.y, d.x))
        M_ = (A + B) / 2
        if n.dot(M_ - Vector((CX_ROOM, CY_ROOM))) < 0:
            n = -n
        cen = M_ + n * (WT / 2)
        rot = math.atan2(d.y, d.x)
        Lb = L + 0.2
        walls.append(box(f"F_wall_chamfer{k}", (cen.x, cen.y, 4.5), (Lb, WT, CEIL), M["wall2"],
                         rot=rot, uv=2.5))
        colliders_diag.append([round(cen.x, 3), round(cen.y, 3), 4.5, round(Lb, 3), WT, CEIL, round(rot, 5)])
    parts["walls"] = join_group(walls, "F_walls")
    parts["ceiling"] = box("F_ceiling", (0.0, 157.15, CEIL + WT / 2), (24.6, 26.3, WT), M["ceil"], uv=2.5)
    parts["floor"] = box("F_floor", (0.0, 157.15, -WT / 2), (24.6, 26.3, WT), M["floor"], uv=3.0)
    colliders = [[-12.15, 157.0, 4.5, WT, 20.0, CEIL, 0.0],
                 [12.15, 157.0, 4.5, WT, 20.0, CEIL, 0.0],
                 [0.0, 170.15, 4.5, 18.0, WT, CEIL, 0.0]] + colliders_diag
    return parts, colliders


def build_ceiling(M):
    objs = {"beam": [], "duct": [], "tray": [], "fix": [], "rods": [], "cables": [], "pipes": [],
            "gantry": [], "rails": [], "shelf": []}
    # I-beams across the room (bottom at 8.4)
    for y in (147.5, 152.5, 157.5, 162.5, 167.5):
        b = box(f"F_beam_{y}", (0.0, y, 8.7), (24.6, 0.25, 0.6), M["ceil"], uv=2.5)
        bkit.harden(b, width=0.01)
        objs["beam"].append(b)
    # rust duct along the east side, tray on the west side
    d = box("F_duct", (9.0, 158.0, 7.9), (0.8, 22.4, 0.8), M["rust"], uv=1.0)
    bkit.harden(d, width=0.012)
    objs["duct"].append(d)
    objs["tray"].append(box("F_tray_bottom", (-8.8, 157.9, 7.95), (0.5, 22.0, 0.02), M["metal"], uv=1.0))
    objs["tray"].append(box("F_tray_w", (-8.55, 157.9, 8.02), (0.02, 22.0, 0.12), M["metal"], uv=1.0))
    objs["tray"].append(box("F_tray_e", (-9.05, 157.9, 8.02), (0.02, 22.0, 0.12), M["metal"], uv=1.0))
    # four light fixtures; (-6,152.5) and (6,162.5) are the working ones
    for x, y in ((-6.0, 152.5), (6.0, 152.5), (-6.0, 162.5), (6.0, 162.5)):
        objs["fix"].append(box(f"F_fixture_{x}_{y}", (x, y, 7.6), (1.2, 0.28, 0.1), M["fix"], uv=1.0))
        for dx in (-0.35, 0.35):
            objs["rods"].append(tube(f"F_fixrod_{x}_{y}_{dx}", [(x + dx, y, 8.42), (x + dx, y, 7.65)],
                                     0.012, M["metal"], sides=6))
    return objs


def build_machine_area(M):
    objs = {"rods": [], "gantry": [], "cables": [], "pipes": []}
    # gantry deck at 3.0 m, visual only, hung from the ceiling (no floor posts, so the 3 m ring stays clear)
    gx_o, gy_o, gx_i, gy_i = 3.6, 2.8, 2.6, 1.8
    gy = MACH_Y
    objs["gantry"].append(box("F_deck_l", (-3.1, gy, 3.0), (1.0, 2 * gy_o, 0.15), M["metal"], uv=0.8))
    objs["gantry"].append(box("F_deck_r", (3.1, gy, 3.0), (1.0, 2 * gy_o, 0.15), M["metal"], uv=0.8))
    objs["gantry"].append(box("F_deck_f", (0.0, gy - gy_o + 0.5, 3.0), (2 * gx_i, 1.0, 0.15), M["metal"], uv=0.8))
    objs["gantry"].append(box("F_deck_b", (0.0, gy + gy_o - 0.5, 3.0), (2 * gx_i, 1.0, 0.15), M["metal"], uv=0.8))
    for sx in (-1, 1):
        objs["gantry"].append(box(f"F_rail_side{sx}", (sx * gx_o, gy, 4.0), (0.05, 2 * gy_o, 0.05), M["metal"], uv=1.0))
        for sy in (-1, 1):
            objs["gantry"].append(box(f"F_post_{sx}_{sy}", (sx * gx_o, gy + sy * gy_o, 3.55), (0.05, 0.05, 0.95), M["metal"], uv=1.0))
    for sy in (-1, 1):
        objs["gantry"].append(box(f"F_rail_end{sy}", (0.0, gy + sy * gy_o, 4.0), (2 * gx_o, 0.05, 0.05), M["metal"], uv=1.0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs["rods"].append(tube(f"F_hangrod_{sx}_{sy}", [(sx * gx_o, gy + sy * gy_o, 3.1),
                                                              (sx * gx_o, gy + sy * gy_o, 9.0)],
                                     0.025, M["metal"], sides=8))
    # cables from the machine to the walls and ceiling
    cable_paths = [
        [(0.8, 159.2, 6.6), (1.6, 161.0, 7.6), (3.2, 163.6, 7.9), (5.6, 166.6, 7.6), (7.8, 169.2, 6.9), (8.4, 169.95, 6.4)],
        [(-0.7, 159.2, 6.3), (-1.4, 161.8, 7.0), (-2.8, 164.6, 7.7), (-4.6, 167.4, 8.1), (-6.8, 169.8, 7.6), (-7.2, 170.05, 7.2)],
        [(1.2, 156.6, 6.8), (2.6, 154.0, 6.4), (4.5, 151.8, 5.6), (7.0, 150.0, 4.6), (10.4, 148.5, 3.0), (12.1, 148.0, 2.0)],
        [(12.1, 152.0, 6.0), (8.6, 152.8, 6.3), (5.0, 154.4, 5.6), (2.4, 155.6, 5.2)],
        [(-12.1, 163.0, 5.9), (-8.5, 162.8, 6.2), (-5.0, 161.5, 5.6), (-2.4, 159.8, 5.2)],
        [(-0.2, 158.0, 7.0), (-0.6, 157.5, 7.9), (-0.2, 157.8, 8.4)],
    ]
    for i, p in enumerate(cable_paths):
        objs["cables"].append(tube(f"F_cable_{i}", p, 0.05 if i < 5 else 0.06, M["cable"], sides=8, step=6))
    # pipes: along the east wall under the beams, a vertical stack in the north-west corner, a low pipe on the far wall
    objs["pipes"].append(tube("F_pipe_east", [(11.75, 148.0, 8.0), (11.75, 169.6, 8.0)], 0.1, M["rust"], sides=10, step=2, uv_m=0.7))
    for yy_ in (150.0, 156.0, 162.0, 168.0):
        objs["pipes"].append(box(f"F_pipe_bracket_{yy_}", (11.9, yy_, 8.0), (0.2, 0.14, 0.14), M["metal"], uv=1.0))
    objs["pipes"].append(tube("F_pipe_vert", [(-11.8, 165.0, 0.2), (-11.8, 165.0, 8.7)], 0.12, M["rust"], sides=10, step=2, uv_m=0.7))
    for zz in (1.2, 4.0, 6.8):
        objs["pipes"].append(box(f"F_pipe_vbracket_{zz}", (-11.9, 165.0, zz), (0.2, 0.2, 0.2), M["metal"], uv=1.0))
    objs["pipes"].append(tube("F_pipe_low", [(-8.9, 169.6, 0.4), (-3.4, 169.6, 0.4)], 0.09, M["rust"], sides=10, step=2, uv_m=0.7))
    return objs


def build_shelves(M, jar_src):
    shelf_objs, jars = [], []
    for side in (1, -1):
        for yc in (150.5, 162.0):
            xc = side * 11.75
            for dx in (-0.22, 0.22):
                for dy in (-1.18, 1.18):
                    shelf_objs.append(box(f"F_shelfpost", (xc + dx, yc + dy, 1.275), (0.04, 0.04, 2.55), M["metal"], uv=0.6))
            for L in (0.15, 0.95, 1.75, 2.5):
                shelf_objs.append(box("F_shelfboard", (xc, yc, L - 0.015), (0.5, 2.4, 0.03), M["metal"], uv=0.6))
            for L in (0.15, 0.95, 1.75):
                for dy in (-0.9, -0.3, 0.3, 0.9):
                    if rng.random() < 0.1:
                        continue
                    rot = (-math.pi / 2 if side > 0 else math.pi / 2) + rng.uniform(-0.12, 0.12)
                    ob = bpy.data.objects.new("F_jar", jar_src.data)
                    ob.location = (xc + rng.uniform(-0.03, 0.03), yc + dy + rng.uniform(-0.03, 0.03), L + 0.001)
                    ob.rotation_euler = (0, 0, rot)
                    jars.append(link(ob))
    shelves = join_group(shelf_objs, "F_shelves")
    return shelves, jars


def build_decals(M):
    out = {"paper": [], "puddle": [], "drain": [], "tile": []}
    # puddles (outside the 3 m ring) and drains
    for x, y, r in ((8.2, 150.6, 1.0), (-7.6, 166.2, 0.9), (6.6, 166.4, 0.7), (-7.2, 149.8, 0.6)):
        out["puddle"].append(tube(f"F_puddle_{x}_{y}", [(x, y, 0.001), (x, y, 0.006)], r, M["puddle"], sides=16, step=1))
    for x, y in ((-6.5, 156.5), (7.0, 155.0), (2.8, 167.8)):
        out["drain"].append(box(f"F_drain_{x}_{y}", (x, y, 0.005), (0.5, 0.5, 0.01), M["drain"], uv=0.5))
    out["tile"].append(box("F_tile_a", (-8.2, 160.8, 0.01), (0.6, 0.6, 0.02), M["tile"], rot=0.4, uv=1.0))
    out["tile"].append(box("F_tile_b", (6.2, 147.9, 0.01), (0.6, 0.6, 0.02), M["tile"], rot=-0.3, uv=1.0))
    # scattered paper sheets, kept outside the chase ring
    placed = 0
    while placed < 11:
        x = rng.uniform(-10.0, 10.0)
        y = rng.uniform(146.6, 168.5)
        if abs(x) < 6.0 and 152.4 < y < 163.6:
            continue
        a = rng.uniform(0, math.tau)
        u = (math.cos(a), math.sin(a), 0.0)
        v = (-math.sin(a), math.cos(a), 0.0)
        out["paper"].append(plane(f"F_paper_{placed}", (x, y, 0.004), u, v, 0.21, 0.297, M["paper"]))
        placed += 1
    return out


def build_fixed_decals(M):
    out = {}
    out["mural"] = plane("F_mural", (0.0, 169.97, 5.6), (1, 0, 0), (0, 0, 1), 5.4, 3.6, M["mural"])
    out["hazard"] = plane("F_hazard", (0.0, 146.35, 0.003), (1, 0, 0), (0, 1, 0), 8.0, 0.4, M["hazard"])
    out["sign"] = plane("F_sign", (11.97, 154.5, 1.8), (0, -1, 0), (0, 0, 1), 0.5, 0.5, M["sign"])
    return out


def build_cage(M):
    parts = [box("F_cage_bracket", (-11.9, 149.0, 4.6), (0.2, 0.25, 0.25), M["metal"], uv=1.0),
             box("F_junction_e", (11.88, 158.0, 1.3), (0.24, 0.32, 0.24), M["metal"], uv=1.0),
             box("F_junction_w", (-11.88, 156.0, 1.5), (0.24, 0.28, 0.2), M["metal"], uv=1.0),
             tube("F_cage_bulb", [(-11.8, 149.0, 4.6), (-11.55, 149.0, 4.6)], 0.08, M["fix"], sides=10, step=1)]
    return join_group(parts, "F_cage")


def preview_boundary(M):
    """Preview only: zone E's boundary with its doorway, so the eye views can look at it.
    Not exported."""
    y_c = Y0 + WT / 2   # 144.0..144.3 (built by zone E)
    parts = [box("PREVIEW_E_left", (-6.75, y_c, 4.65), (11.1, WT, 9.3), M["wall"], uv=2.5),
             box("PREVIEW_E_right", (6.75, y_c, 4.65), (11.1, WT, 9.3), M["wall"], uv=2.5),
             box("PREVIEW_E_lintel", (0.0, y_c, 6.15), (2.4, WT, 6.3), M["wall"], uv=2.5)]
    for p in parts:
        p.hide_select = True
    return parts


def build_lights():
    fixtures = [
        {"pos": [-6.0, 152.5, 7.45], "color": "#d6ecff", "intensity": 1.0, "range": 9.0, "flicker": False},
        {"pos": [6.0, 162.5, 7.45], "color": "#c8dcff", "intensity": 0.8, "range": 9.0, "flicker": True},
        {"pos": [0.0, 154.3, 5.0], "color": "#ffb070", "intensity": 1.2, "range": 10.0, "flicker": False},
        {"pos": [-11.4, 149.0, 4.6], "color": "#ffb070", "intensity": 0.7, "range": 6.0, "flicker": True},
    ]
    return fixtures


def add_preview_lights(lights):
    for i, L in enumerate(lights):
        ld = bpy.data.lights.new(f"prev_light_{i}", "POINT")
        hx = L["color"].lstrip("#")
        rgb = tuple(int(hx[k:k + 2], 16) / 255 for k in (0, 2, 4))
        ld.color = rgb
        ld.energy = (1100.0 if L["color"] != "#ffb070" else 700.0) * L["intensity"]
        ld.shadow_soft_size = 0.25
        ob = bpy.data.objects.new(f"prev_light_{i}", ld)
        ob.location = L["pos"]
        link(ob)
    w = bpy.data.worlds.new("F_dark")
    scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.012, 0.012, 0.014, 1)
    bg.inputs["Strength"].default_value = 1.0


def setup_render(res, samples):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"


def eye_cam(loc, target, lens=28.0):
    cd = bpy.data.cameras.new("EyeCam")
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 80.0
    cam = bpy.data.objects.new("EyeCam", cd)
    link(cam)
    cam.location = Vector(loc)
    d = (Vector(target) - Vector(loc)).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def render_still(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def load_rgba(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    arr = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    return arr


def write_sheet(tiles_paths, out_path):
    tiles = [load_rgba(p) for p in tiles_paths]
    sheet = np.vstack([np.hstack(tiles[2:4]), np.hstack(tiles[0:2])])   # bottom-up
    h, w = sheet.shape[:2]
    im = bpy.data.images.new("eye_sheet", w, h, alpha=False)
    im.pixels.foreach_set(sheet.ravel())
    im.filepath_raw = out_path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out_path


EYE_VIEWS = [
    ("entry", (0.0, 146.8, 1.6), (0.0, 158.0, 2.4)),
    ("doorway", (0.0, 154.0, 1.6), (0.0, 144.0, 1.9)),
    ("shelves", (-5.5, 150.0, 1.6), (11.5, 156.0, 1.5)),
    ("mural", (-6.0, 163.5, 1.6), (-1.0, 170.0, 5.4)),
]


def main():
    global scene
    bkit.reset_scene()
    scene = bpy.context.scene   # reset_scene replaces the scene datablock
    M = build_materials()
    shell, shell_colliders = build_shell(M)
    ceil = build_ceiling(M)
    mach = build_machine_area(M)

    # imported finished props
    mach_objs = bkit.import_glb(f"{ROOT}/public/models/joy_machine.glb")
    machine = mach_objs[0]
    machine.name = "F_joy_machine"
    machine.scale = (MACH_S, MACH_S, MACH_S)
    machine.location = (MACH_X, MACH_Y, 0.0)
    jar_objs = bkit.import_glb(f"{ROOT}/public/models/joy_jar.glb")
    jar_src = jar_objs[0]
    plush_objs = bkit.import_glb(f"{ROOT}/public/models/plush_pile.glb")
    plush = plush_objs[0]
    plush.name = "F_plush_pile"
    plush.location = (-9.3, 148.6, 0.0)
    plush.rotation_euler = (0, 0, 0.6)

    shelves, jars = build_shelves(M, jar_src)
    decals = build_decals(M)
    fixed = build_fixed_decals(M)
    cage = build_cage(M)
    preview = preview_boundary(M)

    # joins by group (keeps the scene at a few dozen mesh objects plus instanced jars)
    join_group(ceil["beam"], "F_beams")
    join_group(ceil["duct"], "F_duct")
    join_group(ceil["tray"], "F_tray")
    join_group(ceil["fix"], "F_fixtures")
    join_group(ceil["rods"] + mach["rods"], "F_hangrods")
    join_group(mach["cables"], "F_cables")
    join_group(mach["pipes"], "F_pipes")
    join_group(mach["gantry"], "F_gantry")
    join_group(decals["puddle"], "F_puddles")
    join_group(decals["drain"], "F_drains")
    join_group(decals["tile"], "F_tiles")
    join_group(decals["paper"], "F_paper")

    # remove the template jar and plush sources (copies keep the mesh data)
    for src in (jar_src,):
        bpy.data.objects.remove(src, do_unlink=True)
    for o in list(scene.objects):
        if o.type == "MESH" and o.name.startswith("joy_"):
            bpy.data.objects.remove(o, do_unlink=True)

    ship = [o for o in scene.objects if o.type == "MESH" and not o.name.startswith("PREVIEW_")]
    props_names = {"F_joy_machine", "F_plush_pile", "F_jar"}
    jar_objs_ship = [o for o in ship if o.name.startswith("F_jar")]
    print("ZONE_F shipping meshes:", len(ship), " jars:", len(jar_objs_ship))

    # lights for previews only
    lights = build_lights()
    add_preview_lights(lights)

    # ---- previews
    os.makedirs(f"{ROOT}/renders", exist_ok=True)
    # top view with the ceiling-level dressing hidden
    hide_top = [o for o in scene.objects if o.name.startswith(
        ("F_beam", "F_duct", "F_tray", "F_fixture", "F_ceiling", "F_hangrods"))]
    for o in hide_top:
        o.hide_render = True
    setup_render((1000, 1000), 16)
    cd = bpy.data.cameras.new("TopCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 28.0
    cd.clip_end = 120.0
    cam = bpy.data.objects.new("TopCam", cd)
    link(cam)
    cam.location = (0.0, 157.15, 60.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = cam
    render_still(OUT_TOP)
    for o in hide_top:
        o.hide_render = False
    bpy.data.objects.remove(cam)

    # eye views in a 2x2 contact sheet
    setup_render((800, 450), 24)
    tiles = []
    for name, loc, tgt in EYE_VIEWS:
        cam = eye_cam(loc, tgt)
        p = f"{TMP}/eye_{name}.png"
        render_still(p)
        tiles.append(p)
        bpy.data.objects.remove(cam)
    write_sheet(tiles, OUT_EYE)

    # ---- save the scene and export the shipping objects
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

    # ship 512 px textures (each image datablock is embedded once; materials and jars are shared)
    for im in bpy.data.images:
        if im.size[0] > 512 or im.size[1] > 512:
            im.scale(512, 512)
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    bkit.export_glb(OUT_GLB, ship, image_format="JPEG")

    # ---- gameplay data
    colliders = list(shell_colliders)
    colliders.append([MACH_X, MACH_Y, MACH_TOP / 2, round(2 * MACH_HALF_X, 3), round(2 * MACH_HALF_Y, 3), round(MACH_TOP, 3), 0.0])
    for xc, yc in ((11.75, 150.5), (11.75, 162.0), (-11.75, 150.5), (-11.75, 162.0)):
        colliders.append([xc, yc, 1.275, 0.5, 2.4, 2.55, 0.0])
    colliders.append([-9.3, 148.6, 0.42, 0.9, 1.4, 0.8, 0.6])

    markers = {
        "entry": [0.0, 146.2, 0.0],
        "machine": [MACH_X, MACH_Y, 0.0],
        "hide_east": [10.2, 156.3, 0.0],
        "hide_west": [-10.2, 156.3, 0.0],
        "spawn_1": [-9.0, 167.0, 0.0],
        "spawn_2": [9.0, 167.0, 0.0],
        "patrol_1": [-5.6, 153.0, 0.0],
        "patrol_2": [5.6, 153.0, 0.0],
        "patrol_3": [5.6, 163.0, 0.0],
        "patrol_4": [-5.6, 163.0, 0.0],
    }
    data = {
        "zone": "F",
        "colliders": colliders,
        "lights": lights,
        "markers": markers,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # ---- report
    shell_names = [o for o in ship if not (o.name in props_names or o.name.startswith("F_jar")
                                           or o.name.startswith("F_plush"))]
    prop_objs = [o for o in ship if o not in shell_names]
    shell_tris = sum(bkit.tri_count(o) for o in shell_names)
    prop_tris = sum(bkit.tri_count(o) for o in prop_objs)
    print("ZONE_F shell_tris", shell_tris, "prop_tris(imported+instances, counted per instance)", prop_tris)
    print("ZONE_F glb_bytes", os.path.getsize(OUT_GLB))
    print("ZONE_F materials", sorted({m.name for m in bpy.data.materials if m.users > 0}))
    print("ZONE_F collider_count", len(colliders), "lights", len(lights))


main()
