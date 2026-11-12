"""Flicker (閃閃), Chapter 3 ghost: a 1.6 m lamp-wire figure whose head is a cracked light bulb.

Inside the bulb a glowing filament is shaped like a small child curled up asleep. Bare cable arms
end in ceramic sockets; the tattered lower body trails into loose wires, no feet.

Blender coordinates, metres, Z up, front -Y, origin at the bottom (the game sets the float height).

usage: python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py blender/ghosts/flicker_build.py blender/bake/ghosts/flicker [build|game]
  build (default): model, preview -> renders/ch3_flicker_preview.png, save flicker_detail.blend
  game:            per-part rigid skin, decimate, join, bake, rig, animate, export public/models/flicker.glb
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bkit  # noqa: E402
sys.path.insert(0, "/Users/alex/恐怖遊戲2/blender")
import lib  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
STAGE = (sys.argv[sys.argv.index("--") + 2:] or ["build"])[0]
ROOT = "/Users/alex/恐怖遊戲2"
RENDERS = os.path.join(ROOT, "renders")
NAME = "flicker"
BUDGET = 12000
random.seed(1996)


# ---------------------------------------------------------------- helpers
def mesh_obj(name, verts, faces, m=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    if m:
        me.materials.append(m)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return o


def tag(o, bone):
    o["bone"] = bone
    return o


def tube(name, pts, rads, m, segs=12, flat=1.0):
    """Sweep a ring along pts with parallel-transport frames. rads: radius, or (rx, ry) per point."""
    P = [Vector(p) for p in pts]
    n = len(P)
    if not isinstance(rads, list):
        rads = [rads] * n
    R = [tuple(r) if isinstance(r, (tuple, list)) else (r, r * flat) for r in rads]
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    u = T[0].cross(ref).normalized()
    verts, faces = [], []
    for i in range(n):
        t = T[i]
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        rx, ry = R[i]
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append(tuple(P[i] + u * (rx * math.cos(a)) + v * (ry * math.sin(a))))
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((i * segs + k, i * segs + k2, (i + 1) * segs + k2, (i + 1) * segs + k))
    faces.append(tuple(range(segs)))
    faces.append(tuple((n - 1) * segs + k for k in reversed(range(segs))))
    return mesh_obj(name, verts, faces, m)


def lathe_obj(name, profile, m, segs=40, loc=(0, 0, 0)):
    o = bkit.lathe(profile, segments=segs, name=name)
    o.data.materials.append(m)
    o.location = loc
    return o


def ph_mat(name, asset, scale, tint=None, rough_mult=1.0):
    maps = bkit.polyhaven_texture(asset, "1k")
    return bkit.pbr_material(name, maps, scale=scale, tint=tint, roughness_mult=rough_mult)


def mat_rubber(name="CableRubber"):
    M = lib.Mat(name)
    n = M.noise(14, 10, 0.6, distortion=0.4)
    col = M.ramp(n, [(0.3, "#141210"), (0.55, "#2c2824"), (0.8, "#4a423a")])
    grime = M.ramp(M.noise(3, 6, 0.5), [(0.4, "#ffffff"), (0.7, "#4b4032")])
    col = M.mix(1.0, col, grime, "MULTIPLY")
    M.set(color=col, rough=0.7, coat=0.1)
    M.bump(M.noise(60, 6, 0.6), 0.2, 0.005)
    return M.m


def mat_copper(name="WireCopper"):
    M = lib.Mat(name)
    n = M.noise(10, 10, 0.6)
    col = M.ramp(n, [(0.3, "#3a2212"), (0.5, "#8a5a32"), (0.75, "#b07a48")])
    verdi = M.ramp(M.noise(4, 6, 0.6), [(0.55, "#ffffff"), (0.7, "#3c7060")])
    col = M.mix(0.6, col, verdi, "MULTIPLY")
    M.set(color=col, rough=0.45, metal=0.35)
    return M.m


def mat_ceramic(name="Porcelain"):
    M = lib.Mat(name)
    n = M.noise(6, 8, 0.6)
    col = M.ramp(n, [(0.35, "#c9c1a8"), (0.6, "#dcd5bf"), (0.85, "#ece6d2")])
    dirt = M.ramp(M.noise(2.5, 6, 0.5), [(0.5, "#ffffff"), (0.75, "#6a5a40")])
    col = M.mix(1.0, col, dirt, "MULTIPLY")
    M.set(color=col, rough=0.18, coat=0.5, coat_rough=0.06)
    M.bump(M.voronoi(40, "DISTANCE_TO_EDGE"), 0.08, 0.004)
    return M.m


def mat_bulb_glass(name="BulbGlass"):
    M = lib.Mat(name)
    cracks = M.voronoi(7, "DISTANCE_TO_EDGE")
    crack_c = M.ramp(cracks, [(0.0, "#2a2a22"), (0.05, "#e4e2d0")])
    dust = M.ramp(M.noise(3, 8, 0.6), [(0.3, "#ffffff"), (0.7, "#8a8466")])
    col = M.mix(1.0, crack_c, dust, "MULTIPLY")
    M.set(color=col, rough=0.14, coat=0.6, coat_rough=0.05)
    return M.m


def mat_filament(name="FilamentGlow"):
    M = lib.Mat(name)
    M.set(color="#ffb060", rough=0.5, emit="#ffa040", emit_strength=9.0)
    return M.m


def add_lights():
    lib.add_area("Key", (2.2, -3.2, 2.6), (0, 0, 0.85), 900, (0.7, 0.8, 1.0), spot=True)
    lib.add_area("Rim", (-2.0, 2.4, 2.4), (0, 0, 1.0), 500, (1.0, 0.45, 0.3), size=1.5)
    lib.add_area("Fill", (0, -3.5, 0.8), (0, 0, 0.9), 120, (1.0, 0.7, 0.45), size=3)


def shot(path, loc, target, lens=34, samples=28):
    lib.setup_render(samples=samples, res=(800, 600))
    lib.camera(loc, target, lens)
    lib.render(path)


# ---------------------------------------------------------------- bones
PREVIEW = ((1.4, -2.7, 1.0), (0, 0, 0.8))   # full view
CLOSE = ((0.45, -0.95, 1.5), (0, 0, 1.42))  # head close-up
SIDE = ((3.4, 0.0, 0.9), (0, 0, 0.85))


# ---------------------------------------------------------------- shapes (v2)
def catmull(P, n=6):
    """Smooth curve through control points (Catmull-Rom), n samples per span."""
    P = [Vector(p) for p in P]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2 = P[max(i - 1, 0)], P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return [tuple(v) for v in out]


def sweep(name, pts, rads, m, segs=6, mod=None):
    """Tube along pts with parallel-transport frames. mod(i, angle) multiplies the ring radius (pleats)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    if not isinstance(rads, list):
        rads = [rads] * n
    R = [tuple(r) if isinstance(r, (tuple, list)) else (r, r) for r in rads]
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    u = T[0].cross(ref).normalized()
    verts, faces = [], []
    for i in range(n):
        t = T[i]
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        rx, ry = R[i]
        for k in range(segs):
            a = 2 * math.pi * k / segs
            f = mod(i, a) if mod else 1.0
            verts.append(tuple(P[i] + (u * (rx * math.cos(a)) + v * (ry * math.sin(a))) * f))
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((i * segs + k, i * segs + k2, (i + 1) * segs + k2, (i + 1) * segs + k))
    faces.append(tuple(range(segs)))
    faces.append(tuple((n - 1) * segs + k for k in reversed(range(segs))))
    return mesh_obj(name, verts, faces, m)


def helix_pts(z0, z1, n, turns, rfn, phase):
    out = []
    for k in range(n + 1):
        t = k / n
        a = 2 * math.pi * turns * t + phase
        r = rfn(t)
        out.append((r * math.cos(a), 0.6 * r * math.sin(a), z0 + (z1 - z0) * t))
    return out


def split_z(pts, cut):
    """Split a rising path at height cut into a lower and an upper piece sharing one point."""
    k = next((i for i, p in enumerate(pts) if p[2] >= cut), len(pts) - 1)
    k = max(1, min(k, len(pts) - 2))
    return [("hips", pts[:k + 1]), ("spine", pts[k:])]


def sheet(name, cx, cz, y0, w, h, nx, ny, m, rng):
    """Narrow hanging rag strip in the XZ plane: tapers to a torn point, sways, thickened."""
    verts, faces = [], []
    ph = rng.uniform(0, 6)
    for j in range(ny + 1):
        t = j / ny
        wj = w * (1 - 0.62 * t ** 1.6)
        sway = 0.02 * math.sin(j * 0.55 + ph) * t + 0.008 * math.sin(j * 1.7 + ph)
        for i in range(nx + 1):
            x = cx + sway + (i / nx - 0.5) * wj
            fold = 0.010 * math.sin(i * 2.3 + j * 0.8 + ph) * t + 0.004 * math.sin(i * 5.1 + ph)
            z = cz - t * h
            if j >= ny - 1:
                z += rng.uniform(-0.05, 0.03) * (1 if j == ny else 0.4)
            verts.append((x, y0 + fold + 0.01 * t * math.sin(ph + j * 0.3), z))
    idx = lambda i, j: j * (nx + 1) + i
    for j in range(ny):
        for i in range(nx):
            if j == ny - 1 and rng.random() < 0.3:
                continue
            faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
    o = mesh_obj(name, verts, faces, m)
    s = o.modifiers.new("Solid", "SOLIDIFY")
    s.thickness = 0.003
    lib.apply_mods(o)
    return o


def fade(mat):
    """Cloth burn gradient along height: lighter scorched brown near the top, black at the torn tips."""
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].position = 0.40
    rp.color_ramp.elements[0].color = (0.01, 0.008, 0.007, 1)
    rp.color_ramp.elements[1].position = 1.02
    rp.color_ramp.elements[1].color = (8.5, 6.0, 3.8, 1)
    nt.links.new(sep.outputs["Z"], rp.inputs["Fac"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.inputs["Factor"].default_value = 1.0
    nt.links.new(src, mx.inputs["A"])
    nt.links.new(rp.outputs["Color"], mx.inputs["B"])
    nt.links.new(mx.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


# ---------------------------------------------------------------- bones
PREVIEW = ((1.4, -2.7, 1.0), (0, 0, 0.8))   # full view
CLOSE = ((0.45, -0.95, 1.5), (0, 0, 1.42))  # head close-up
SIDE = ((3.4, 0.0, 0.9), (0, 0, 0.85))


# ---------------------------------------------------------------- shapes (v2)
def catmull(P, n=6):
    """Smooth curve through control points (Catmull-Rom), n samples per span."""
    P = [Vector(p) for p in P]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2 = P[max(i - 1, 0)], P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return [tuple(v) for v in out]


def sweep(name, pts, rads, m, segs=6, mod=None):
    """Tube along pts with parallel-transport frames. mod(i, angle) multiplies the ring radius (pleats)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    if not isinstance(rads, list):
        rads = [rads] * n
    R = [tuple(r) if isinstance(r, (tuple, list)) else (r, r) for r in rads]
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    u = T[0].cross(ref).normalized()
    verts, faces = [], []
    for i in range(n):
        t = T[i]
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        rx, ry = R[i]
        for k in range(segs):
            a = 2 * math.pi * k / segs
            f = mod(i, a) if mod else 1.0
            verts.append(tuple(P[i] + (u * (rx * math.cos(a)) + v * (ry * math.sin(a))) * f))
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((i * segs + k, i * segs + k2, (i + 1) * segs + k2, (i + 1) * segs + k))
    faces.append(tuple(range(segs)))
    faces.append(tuple((n - 1) * segs + k for k in reversed(range(segs))))
    return mesh_obj(name, verts, faces, m)


def helix_pts(z0, z1, n, turns, rfn, phase):
    out = []
    for k in range(n + 1):
        t = k / n
        a = 2 * math.pi * turns * t + phase
        r = rfn(t)
        out.append((r * math.cos(a), 0.6 * r * math.sin(a), z0 + (z1 - z0) * t))
    return out


def split_z(pts, cut):
    """Split a rising path at height cut into a lower and an upper piece sharing one point."""
    k = next((i for i, p in enumerate(pts) if p[2] >= cut), len(pts) - 1)
    k = max(1, min(k, len(pts) - 2))
    return [("hips", pts[:k + 1]), ("spine", pts[k:])]


def sheet(name, cx, cz, y0, w, h, nx, ny, m, rng):
    """Hanging rag in the XZ plane: a grid with a torn, uneven bottom and a few holes, given thickness."""
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = cx + (i / nx - 0.5) * w
            fold = 0.012 * math.sin(i * 2.3 + j * 0.8) * (j / ny) + 0.004 * math.sin(i * 5.1)
            z = cz - (j / ny) * h
            if j == ny:
                z += rng.uniform(-0.05, 0.02)
            verts.append((x, y0 + fold, z))
    idx = lambda i, j: j * (nx + 1) + i
    for j in range(ny):
        for i in range(nx):
            if rng.random() < 0.10 and 0 < j < ny - 1:
                continue
            if j == ny - 1 and rng.random() < 0.35:
                continue
            faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
    o = mesh_obj(name, verts, faces, m)
    s = o.modifiers.new("Solid", "SOLIDIFY")
    s.thickness = 0.0025
    lib.apply_mods(o)
    return o


# ---------------------------------------------------------------- bones
def rig_bones():
    bones = [
        ("root", (0, 0, 0), (0, 0, 0.5), None),
        ("hips", (0, 0, 0.62), (0, 0, 0.9), "root"),
        ("spine", (0, 0, 0.9), (0, 0, 1.1), "hips"),
        ("neck", (0, 0, 1.1), (0, 0, 1.21), "spine"),
        ("head", (0, 0, 1.21), (0, 0, 1.6), "neck"),
        ("wire_L", (-0.08, 0, 0.62), (-0.2, 0, 0.1), "hips"),
        ("wire_M", (0, 0, 0.6), (0.0, 0, 0.03), "hips"),
        ("wire_R", (0.08, 0, 0.62), (0.2, 0, 0.1), "hips"),
        ("wire_B", (0, 0.05, 0.62), (0.0, 0.2, 0.1), "hips"),
    ]
    for side, s in (("L", 1), ("R", -1)):
        bones += [
            (f"arm_up.{side}", (0.12 * s, 0, 1.05), (0.27 * s, 0, 0.85), "spine"),
            (f"arm_lo.{side}", (0.27 * s, 0, 0.85), (0.36 * s, 0, 0.68), f"arm_up.{side}"),
            (f"hand.{side}", (0.36 * s, 0, 0.68), (0.38 * s, 0, 0.58), f"arm_lo.{side}"),
        ]
    return bones


# ---------------------------------------------------------------- v3 helpers
BULB_PROF = [(0.030, 1.20), (0.031, 1.24), (0.042, 1.265), (0.080, 1.30), (0.115, 1.35), (0.130, 1.41),
             (0.131, 1.46), (0.124, 1.52), (0.100, 1.57), (0.060, 1.605), (0.025, 1.622), (0.0, 1.627)]
HOLE_POLY = [(0.085, 0.010), (0.040, 0.020), (0.052, 0.062), (0.012, 0.035), (-0.010, 0.070), (-0.030, 0.030), (-0.085, 0.045), (-0.050, 0.000), (-0.088, -0.030), (-0.035, -0.025), (-0.028, -0.075), (0.002, -0.030), (0.040, -0.070), (0.038, -0.020)]
HOLE_C = (0.0, 1.50)


def r_at(z):
    for (r0, z0), (r1, z1) in zip(BULB_PROF, BULB_PROF[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0 + 1e-9)
    return 0.0


def surf_y(x, z):
    return -math.sqrt(max(r_at(z) ** 2 - x * x, 1e-6))


def inside(px, pz, poly):
    c, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > pz) != (zj > pz) and px < (xj - xi) * (pz - zi) / (zj - zi + 1e-12) + xi:
            c = not c
        j = i
    return c


def crack(name, start, d, length, steps, rng, m):
    """A thin crack running outward over the glass surface from a hole rim."""
    x, z = start
    dx, dz = d
    pts = []
    for _ in range(steps + 1):
        pts.append((x, surf_y(x, z) * 0.995, z))
        a = rng.uniform(-0.2, 0.2)
        c, s = math.cos(a), math.sin(a)
        dx, dz = dx * c - dz * s, dx * s + dz * c
        x += dx * length / steps
        z += dz * length / steps
    return sweep(name, catmull(pts, 2), 0.0018, m, segs=4)


def mat_smoke_glass(name="BulbSmokeGlass"):
    """Clear smoky glass, unbaked: dust tint comes from vertex colour 'Dust' (darker near the base)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Dust"
    nt.links.new(vc.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.06
    b.inputs["Alpha"].default_value = 0.2
    return m


def mat_glass_solid(name="GlassShard"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.75, 0.82, 0.8, 1)
    b.inputs["Roughness"].default_value = 0.06
    b.inputs["Alpha"].default_value = 0.25
    return m


def mat_crack_solid(name="GlassCrack"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.04, 0.04, 0.035, 1)
    b.inputs["Roughness"].default_value = 0.5
    return m


def scorch(mat):
    """Burn gradient over a scanned cloth: noise darkens the scan toward black-brown in patches."""
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    for lk in list(bsdf.inputs["Base Color"].links):
        nt.links.remove(lk)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.5
    nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (0.03, 0.02, 0.014, 1)
    rp.color_ramp.elements[1].color = (0.2, 0.13, 0.085, 1)
    nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.inputs["Factor"].default_value = 1.0
    nt.links.new(src, mx.inputs["A"])
    nt.links.new(rp.outputs["Color"], mx.inputs["B"])
    nt.links.new(mx.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


# ---------------------------------------------------------------- build
def build():
    M = {
        "rubber": mat_rubber(), "copper": mat_copper(), "ceramic": mat_ceramic(),
        "glass": mat_smoke_glass(), "glassS": mat_glass_solid(), "crack": mat_crack_solid(), "filament": mat_filament(),
        "bone": lib.mat_bone("BoneBlade"),
        "cloth": fade(scorch(ph_mat("ScorchedCloth", "rough_linen", 1.5, tint=(0.22, 0.15, 0.1)))),
        "screw": ph_mat("ScrewMetal", "rusty_metal_02", 1.0),
    }
    parts, glow = [], []

    # --- bulb: smooth clear smoky glass (unbaked), one large jagged hole at the upper front,
    # bevelled rim, thin cracks running out of the hole, a few shards stuck around it
    bulb = lathe_obj("FlickerGlowBulb", BULB_PROF, M["glass"], segs=40)
    me = bulb.data
    bm = bmesh.new()
    bm.from_mesh(me)
    hole = [(HOLE_C[0] + px, HOLE_C[1] + pz) for px, pz in HOLE_POLY]
    dust = me.color_attributes.new("Dust", "BYTE_COLOR", "POINT")
    dark, clear = (0.16, 0.14, 0.11), (0.52, 0.5, 0.45)
    for i, v in enumerate(me.vertices):
        t = max(0.0, min(1.0, (v.co.z - 1.20) / 0.30))
        dust.data[i].color = tuple(dark[k] + (clear[k] - dark[k]) * t for k in range(3)) + (1.0,)
    sol = bulb.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.004
    bkit.active(bulb)
    bpy.ops.object.modifier_apply(modifier=sol.name)
    # one irregular jagged hole: a prism of the outline, cut through the front wall only
    cb = bmesh.new()
    top = [cb.verts.new((x, -0.40, z)) for x, z in hole]
    bot = [cb.verts.new((x, -0.03, z)) for x, z in hole]
    n_ = len(hole)
    for i in range(n_):
        j = (i + 1) % n_
        cb.faces.new((top[i], top[j], bot[j], bot[i]))
    cb.faces.new(top)
    cb.faces.new(list(reversed(bot)))
    bmesh.ops.triangulate(cb, faces=[f for f in cb.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(cb, faces=cb.faces)
    cm = bpy.data.meshes.new("HoleCutter")
    cb.to_mesh(cm)
    cb.free()
    cutter = bpy.data.objects.new("HoleCutter", cm)
    bpy.context.scene.collection.objects.link(cutter)
    bm_ = bulb.modifiers.new("Hole", "BOOLEAN")
    bm_.object = cutter
    bm_.operation = "DIFFERENCE"
    bm_.solver = "EXACT"
    bkit.active(bulb)
    n0 = len(bulb.data.polygons)
    bpy.ops.object.modifier_apply(modifier=bm_.name)
    print("BKIT_HOLE polys", n0, "->", len(bulb.data.polygons), "cutter faces", len(cutter.data.polygons))
    bpy.data.objects.remove(cutter, do_unlink=True)
    bkit.harden(bulb, width=0.0028, segments=2, angle=40)
    glow.append(tag(bulb, "head"))
    rng_c = random.Random(21)
    for k, idx in enumerate([2, 6, 8, 12]):
        px, pz = hole[idx]
        dx, dz = px - HOLE_C[0], pz - HOLE_C[1]
        L = math.hypot(dx, dz)
        glow.append(tag(crack(f"FlickerGlowCrack{k}", (px, pz), (dx / L, dz / L),
                              0.055 + 0.01 * (k % 2), 6, rng_c, M["crack"]), "head"))
    for k, idx in enumerate([0, 4, 10, 13]):
        px, pz = hole[idx]
        dx, dz = px - HOLE_C[0], pz - HOLE_C[1]
        L = math.hypot(dx, dz)
        x, z = px + dx / L * 0.012, pz + dz / L * 0.012
        shard = lib.prim("ico", f"FlickerGlowShard{k}", (x, surf_y(x, z) * 0.99, z),
                         scale=(0.007, 0.0012, 0.01), rot=(rng_c.uniform(0, 3), rng_c.uniform(0, 3), rng_c.uniform(0, 3)),
                         m=M["glassS"], subdivisions=1)
        glow.append(tag(shard, "head"))


    sprof = [(0.0, 1.10), (0.028, 1.10), (0.030, 1.11), (0.024, 1.115), (0.030, 1.12),
             (0.024, 1.125), (0.030, 1.13), (0.024, 1.135), (0.030, 1.14), (0.024, 1.145),
             (0.030, 1.15), (0.022, 1.16), (0.020, 1.19), (0.020, 1.21), (0.0, 1.21)]
    parts.append(tag(lathe_obj("FlickerScrew", sprof, M["screw"], segs=24), "neck"))

    # the child: a tiny curled figure of glowing wire, ~0.22 m, on two support wires from the base
    def P(pts):
        return [(x * 0.86, y * 0.86, 1.40 + (z - 1.40) * 0.86) for x, y, z in pts]
    head = [(0.024 * math.cos(math.radians(a)), 0.0, 1.50 + 0.024 * math.sin(math.radians(a)))
            for a in range(0, 361, 30)]
    spine = catmull([(0.0, 0, 1.476), (-0.02, 0, 1.44), (-0.035, 0, 1.39), (-0.03, 0, 1.335), (-0.005, 0, 1.30)], 4)
    thigh = catmull([(-0.005, 0, 1.30), (0.03, -0.006, 1.31), (0.055, -0.012, 1.335), (0.04, -0.006, 1.30),
                     (0.015, 0, 1.27)], 3)
    arm_a = catmull([(-0.01, 0, 1.455), (0.02, -0.012, 1.44), (0.052, -0.02, 1.39), (0.06, -0.014, 1.355)], 3)
    arm_b = [(x - 0.004, y + 0.01, z) for x, y, z in arm_a]
    for name, pts in (("FlickerGlowHead", head), ("FlickerGlowSpine", spine), ("FlickerGlowLegs", thigh),
                      ("FlickerGlowArmA", arm_a), ("FlickerGlowArmB", arm_b)):
        glow.append(tag(sweep(name, P(pts) if name != "FlickerGlowHead" else P(pts), 0.0045, M["filament"], segs=6),
                        "head"))
    wl = catmull([(0.014, 0, 1.215), (0.01, 0, 1.25), (-0.005, 0, 1.30)], 3)
    wr = [(-x, y, z) for x, y, z in wl]
    for name, pts in (("FlickerChildWireL", wl), ("FlickerChildWireR", wr)):
        parts.append(tag(sweep(name, P(pts), 0.0012, M["copper"], segs=4), "head"))


    # --- gaunt frame: eight wound lamp-wire strands forming the body, ribs, sternum, shoulder blades
    for j in range(8):
        ph = j * 2 * math.pi / 8
        rf = (lambda t: 0.085 - 0.025 * math.sin(math.pi * t) + 0.012 * t)
        pts = helix_pts(0.55, 1.14, 40, 3.5, rf, ph)
        for bone, seg in split_z(pts, 0.9):
            parts.append(tag(sweep(f"FlickerFrame{j}{bone}", seg, 0.0028, M["copper"], segs=5), bone))
    for k in range(6):
        z = 0.92 + k * 0.03
        r = 0.088 - k * 0.004
        arc_r = [(r * math.cos(math.pi * (0.15 + 0.7 * i / 8)), -0.8 * r * math.sin(math.pi * (0.15 + 0.7 * i / 8)), z)
                 for i in range(9)]
        parts.append(tag(sweep(f"FlickerRib{k}", arc_r, 0.0017, M["copper"], segs=4), "spine"))
    parts.append(tag(sweep("FlickerSternum", [(0, -0.088, 0.92), (0, -0.092, 1.0), (0, -0.088, 1.08)],
                           0.0018, M["copper"], segs=4), "spine"))
    for s in (1, -1):
        parts.append(tag(lib.prim("ico", f"FlickerBlade{s:+d}", (0.06 * s, 0.05, 1.03),
                                  scale=(0.045, 0.01, 0.065), rot=(0.2, 0, 0.25 * s), m=M["bone"]), "spine"))

    # scorched rags: six narrow strips hung from the shoulders and ribs with gaps between them, so the
    # wire ribs show through; torn to points below
    rng3 = random.Random(3)
    for k, (cx, cz, w, h, y0) in enumerate([(-0.115, 1.06, 0.055, 0.52, -0.058), (-0.015, 1.04, 0.05, 0.62, -0.075),
                                            (0.09, 1.06, 0.055, 0.5, -0.06), (-0.075, 1.0, 0.05, 0.46, 0.078),
                                            (0.015, 1.02, 0.055, 0.58, 0.09), (0.095, 1.0, 0.05, 0.44, 0.075)]):
        o = sheet(f"FlickerRag{k}", cx, cz, y0, w, h, 3, 16, M["cloth"], rng3)
        parts.append(tag(o, "spine" if k < 3 else "hips"))


    # --- arms: three strands of wire each, curving, with ceramic socket hands
    rng4 = random.Random(5)
    for side, s in (("L", 1), ("R", -1)):
        base = catmull([(0.11 * s, 0, 1.05), (0.22 * s, -0.03, 0.88), (0.3 * s, -0.02, 0.74),
                        (0.36 * s, 0, 0.62)], 4)
        mid = len(base) // 2
        for j in range(3):
            ox, oy = 0.008 * math.cos(j * 2.1), 0.008 * math.sin(j * 2.1)
            nb = len(base)
            pts = [(x + ox * (1 - 0.3 * (i / (nb - 1))) + 0.01 * math.sin((i / (nb - 1)) * 9 + j), y + oy, z)
                   for i, (x, y, z) in enumerate(base)]
            for bone, seg in ((f"arm_up.{side}", pts[:mid + 1]), (f"arm_lo.{side}", pts[mid:])):
                parts.append(tag(sweep(f"FlickerArm{side}{j}{bone[-1]}", seg, 0.0048, M["copper"], segs=5), bone))
        sock = lathe_obj(f"FlickerSocket{side}", [(0.0, 0.0), (0.022, 0.0), (0.024, 0.01), (0.02, 0.03),
                                                  (0.026, 0.04), (0.030, 0.045), (0.026, 0.05), (0.0, 0.05)],
                         M["ceramic"], segs=20, loc=(0.36 * s, 0, 0.60))
        parts.append(tag(sock, f"hand.{side}"))
        for f in range(5):
            dx = (f - 2) * 0.012
            fing = catmull([(0.36 * s + dx * 0.5 * s, 0.0, 0.58), (0.36 * s + dx * 1.2 * s, 0.0, 0.5),
                            (0.36 * s + dx * 2.0 * s, 0.004 * f, 0.43 - 0.01 * f),
                            (0.36 * s + (dx * 2.6 + 0.02 * rng4.uniform(-1, 1)) * s, 0.01 * f, 0.36 - 0.02 * f)], 3)
            parts.append(tag(sweep(f"FlickerFinger{side}{f}", fing, 0.0021, M["copper"], segs=4), f"hand.{side}"))
        for q in range(2):
            loose = catmull([(0.36 * s, 0.01 * q, 0.56), (0.4 * s + 0.02 * q, 0.02, 0.4),
                             (0.44 * s, -0.02 * q, 0.22 + 0.05 * q), (0.46 * s, 0.0, 0.004)], 3)
            loose = [(x, y, max(z, 0.0021)) for x, y, z in loose]
            parts.append(tag(sweep(f"FlickerLoose{side}{q}", loose, 0.0021, M["copper"], segs=4), f"hand.{side}"))

    # --- lower body: dozens of wires splaying out from the hips, tapering to the floor
    rng2 = random.Random(11)
    for j in range(36):
        x0 = rng2.uniform(-0.1, 0.1)
        y0 = rng2.uniform(-0.05, 0.05)
        ang = rng2.uniform(0, 2 * math.pi)
        spread = rng2.uniform(0.2, 0.46)
        x1 = x0 + spread * math.cos(ang)
        y1 = y0 + spread * math.sin(ang) * 0.7
        pts = catmull([(x0, y0, 0.64),
                       (x0 + (x1 - x0) * 0.3, y0 + (y1 - y0) * 0.3, 0.42 + rng2.uniform(-0.03, 0.03)),
                       (x0 + (x1 - x0) * 0.7, y0 + (y1 - y0) * 0.7, 0.2 + rng2.uniform(-0.04, 0.04)),
                       (x1, y1, 0.0012)], 3)
        pts = [(x, y, max(z, 0.0012)) for x, y, z in pts]
        n = len(pts)
        rads = [0.0042 * (1 - 0.7 * i / (n - 1)) + 0.0012 for i in range(n)]
        bone = "wire_L" if x0 < -0.035 else ("wire_R" if x0 > 0.035 else ("wire_B" if y0 > 0.02 else "wire_M"))
        parts.append(tag(sweep(f"FlickerWire{j}", pts, rads, M["copper"], segs=5), bone))

    for o in parts + glow:
        bkit.box_uv(o, size=1.0)
    return parts, glow


def build_stage():
    bkit.reset_scene()
    parts, glow = build()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + "_detail.blend"))
    lib.stage("horror")
    add_lights()
    shot(os.path.join(RENDERS, f"ch3_{NAME}_preview.png"), *PREVIEW)
    shot(os.path.join(OUT, "checks", f"{NAME}_close.png"), *CLOSE, lens=55, samples=24)
    shot(os.path.join(OUT, "checks", f"{NAME}_front.png"), (0.55, -1.0, 1.52), (0, 0, 1.43), lens=55, samples=24)
    shot(os.path.join(OUT, "checks", f"{NAME}_side.png"), *SIDE, lens=40, samples=16)
    print("BKIT_BUILD parts", len(parts), "glow", len(glow))


# ---------------------------------------------------------------- game stage
def sway(length, amp, ph=0.0, axes=(1, 0, 0), base=(0, 0, 0)):
    """Looping sine over one clip: amp degrees along axes, offset by base."""
    out = []
    for i in range(9):
        s = math.sin(2 * math.pi * (i / 8 + ph))
        rot = tuple(base[k] + amp * axes[k] * s for k in range(3))
        out.append((1 + (length - 1) * i / 8, rot, None))
    return out


def bob(length, amp, rot=(0, 0, 0)):
    out = []
    for i in range(9):
        z = amp * math.sin(2 * math.pi * i / 8)
        out.append((1 + (length - 1) * i / 8, rot, (0, 0, z)))
    return out


def key(frames):
    return [(f, r, None) for f, r in frames]


def animate(arm, name, length, keys):
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
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)


def clips():
    """Clip name -> (length in frames, {bone: keys})."""
    W = ("wire_L", "wire_M", "wire_R", "wire_B")
    idle = {"root": bob(96, 0.035), "head": sway(96, 5, 0.0, (0.4, 0, 1)),
            "hips": sway(96, 2.5, 0.1, (1, 0, 0)), "spine": sway(96, 2, 0.2, (1, 0, 0.3))}
    for side, ph in (("L", 0.0), ("R", 0.5)):
        idle[f"arm_up.{side}"] = sway(96, 7, 0.25 + ph, (1, 0, 0))
        idle[f"arm_lo.{side}"] = sway(96, 5, 0.35 + ph, (1, 0, 0))
    for j, b in enumerate(W):
        idle[b] = sway(96, 9, 0.15 * j, (1, 0, 0.4))

    move = {"root": bob(48, 0.05, rot=(-6, 0, 0)), "head": sway(48, 6, 0.0, (1, 0, 0.5), base=(-8, 0, 0)),
            "spine": sway(48, 3, 0.1, (1, 0, 0), base=(-8, 0, 0)),
            "hips": sway(48, 4, 0.2, (1, 0, 0), base=(-4, 0, 0))}
    for side, s in (("L", 1), ("R", -1)):
        move[f"arm_up.{side}"] = sway(48, 10, 0.5 * (s < 0), (1, 0, 0), base=(-30, 0, 0))
        move[f"arm_lo.{side}"] = sway(48, 8, 0.5 * (s < 0), (1, 0, 0), base=(-20, 0, 0))
    for j, b in enumerate(W):
        move[b] = sway(48, 18, 0.2 * j, (1, 0, 0.4), base=(-10, 0, 0))

    attack = {"arm_up.L": key([(1, (0, 0, 0)), (8, (-88, 0, 12)), (14, (-80, 0, 8)), (30, (0, 0, 0))]),
              "arm_up.R": key([(1, (0, 0, 0)), (8, (-88, 0, -12)), (14, (-80, 0, -8)), (30, (0, 0, 0))]),
              "arm_lo.L": key([(1, (0, 0, 0)), (8, (-10, 0, 0)), (14, (-5, 0, 0)), (30, (0, 0, 0))]),
              "arm_lo.R": key([(1, (0, 0, 0)), (8, (-10, 0, 0)), (14, (-5, 0, 0)), (30, (0, 0, 0))]),
              "head": key([(1, (0, 0, 0)), (7, (-28, 0, 6)), (13, (-22, 0, 0)), (30, (0, 0, 0))]),
              "spine": key([(1, (0, 0, 0)), (7, (-10, 0, 0)), (30, (0, 0, 0))])}
    for b in W:
        attack[b] = sway(30, 14, 0.0, (1, 0, 0.3))

    flash = {"head": key([(1, (0, 0, 0)), (3, (0, 0, 7)), (5, (0, 0, -9)), (7, (2, 0, 0)),
                          (9, (0, 0, 8)), (12, (0, 0, -5)), (16, (0, 0, 0))]),
             "arm_lo.L": key([(1, (0, 0, 0)), (4, (-25, 0, 0)), (8, (0, 0, 0)), (12, (-18, 0, 0)), (16, (0, 0, 0))]),
             "arm_lo.R": key([(1, (0, 0, 0)), (6, (-20, 0, 0)), (10, (0, 0, 0)), (16, (0, 0, 0))])}

    death = {"head": key([(1, (0, 0, 0)), (20, (-30, 0, 14)), (72, (-58, 0, 22))]),
             "spine": key([(1, (0, 0, 0)), (30, (-12, 0, 0)), (72, (-20, 0, 0))]),
             "arm_up.L": key([(1, (0, 0, 0)), (30, (18, 0, 25)), (72, (28, 0, 30))]),
             "arm_up.R": key([(1, (0, 0, 0)), (30, (18, 0, -25)), (72, (28, 0, -30))]),
             "arm_lo.L": key([(1, (0, 0, 0)), (40, (-30, 0, 0)), (72, (-40, 0, 0))]),
             "arm_lo.R": key([(1, (0, 0, 0)), (40, (-30, 0, 0)), (72, (-40, 0, 0))])}
    for b in W:
        death[b] = key([(1, (0, 0, 0)), (40, (-16, 0, 0)), (72, (-26, 0, 0))])
    stun = {"head": key([(1, (0, 0, 0)), (6, (-30, 0, 0)), (14, (-22, 0, 8)), (22, (-26, 0, -8)),
                         (30, (-20, 0, 0)), (40, (-24, 0, 0))]),
            "spine": key([(1, (0, 0, 0)), (6, (-12, 0, 0)), (40, (-12, 0, 0))]),
            "arm_lo.L": key([(1, (0, 0, 0)), (4, (-30, 0, 0)), (12, (5, 0, 0)), (40, (-10, 0, 0))]),
            "arm_lo.R": key([(1, (0, 0, 0)), (4, (-26, 0, 0)), (12, (4, 0, 0)), (40, (-8, 0, 0))]),
            "arm_up.L": key([(1, (0, 0, 0)), (8, (-20, 0, 25)), (40, (-15, 0, 20))]),
            "arm_up.R": key([(1, (0, 0, 0)), (8, (-20, 0, -25)), (40, (-15, 0, -20))])}
    for b_ in W:
        stun[b_] = sway(40, 10, 0.0, (1, 0, 0.4))
    return {"Idle": (96, idle), "Move": (48, move), "Attack": (30, attack),
            "Flash": (16, flash), "Death": (72, death), "Stun": (40, stun)}


def game_stage():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, NAME + "_detail.blend"))
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH" or o.name == "Floor"]:
        bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    glow = [o for o in meshes if o.name.startswith("FlickerGlow")]
    body = [o for o in meshes if o not in glow]
    for o in meshes:
        lib.apply_mods(o)
        vg = o.vertex_groups.new(name=o["bone"])
        vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    bulb = next(o for o in glow if o.name.startswith("FlickerGlowBulb"))
    tb = bkit.tri_count(bulb)
    print("BKIT_BULB tris", tb)
    if tb > 2600:  # the glass is dense from the bevel; keep its silhouette, drop the rest, protect the hole rim
        rim = bulb.vertex_groups.new(name="rim")
        hole_ = [(HOLE_C[0] + px, HOLE_C[1] + pz) for px, pz in HOLE_POLY]
        rim.add([v.index for v in bulb.data.vertices if v.co.y < 0 and any(math.hypot(v.co.x - hx, v.co.z - hz) < 0.03 for hx, hz in hole_ + [HOLE_C])], 1.0, "REPLACE")
        dm = bulb.modifiers.new("Dec", "DECIMATE")
        dm.ratio = 2600 / tb
        dm.vertex_group = "rim"
        dm.vertex_group_factor = 12.0
        lib.apply_mods(bulb)
    total = sum(bkit.tri_count(o) for o in body)
    print("BKIT_TRIS before decimate", total)
    if total > 7800:
        ratio = 7800 / total
        for o in body:
            # thin cables and cloth shells keep a floor so they don't collapse
            t = bkit.tri_count(o)
            keep = max(int(t * ratio), min(t, 24))
            if keep < t:
                m = o.modifiers.new("Dec", "DECIMATE")
                m.ratio = keep / t
                lib.apply_mods(o)
    obj = bkit.join(body, NAME.capitalize())
    gobj = bkit.join(glow, "FlickerGlow")
    first = next(m for m in obj.data.materials if m)
    for i, m in enumerate(obj.data.materials):
        if m is None:
            obj.data.materials[i] = first
    for m in obj.data.materials:
        if m and m.name.split(".")[0] == "ScrewMetal":
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            met = bsdf.inputs["Metallic"]
            for lk in list(met.links):
                m.node_tree.links.remove(lk)
            met.default_value = 0.35
    bkit.bake_to_textures(obj, os.path.join(OUT, "textures"), size=1024, samples=8)

    # rig: armature with the same bones; rigid parts follow one bone each
    arm_d = bpy.data.armatures.new("FlickerRig")
    arm = lib.link_obj(bpy.data.objects.new("FlickerRig", arm_d))
    lib.select_only(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, parent in rig_bones():
        eb = arm_d.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = Vector(h), Vector(t), 0.0
        if parent:
            eb.parent = arm_d.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in (obj, gobj):
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm

    for cname, (length, keys) in clips().items():
        animate(arm, cname, length, keys)

    bkit.check([obj, gobj], max_tris=BUDGET)
    bkit.report([obj, gobj])
    path = os.path.join(ROOT, "public", "models", NAME + ".glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in (arm, obj, gobj):
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=False,
                              export_lights=False, export_image_format="JPEG", export_jpeg_quality=85,
                              export_animation_mode="NLA_TRACKS")
    print("BKIT_EXPORT", path, os.path.getsize(path) // 1024, "KB")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + "_game.blend"))

    for o in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
        bpy.data.objects.remove(o, do_unlink=True)
    lib.stage("horror")
    add_lights()
    shot(os.path.join(RENDERS, f"ch3_{NAME}_baked.png"), *PREVIEW)
    shot(os.path.join(RENDERS, f"ch3_{NAME}_baked_close.png"), *CLOSE, lens=55, samples=24)
    shot(os.path.join(RENDERS, f"ch3_{NAME}_baked_front.png"), (0.55, -1.0, 1.52), (0, 0, 1.43), lens=55, samples=24)
    print("BKIT_DONE", STAGE)


if __name__ == "__main__":
    if STAGE == "build":
        build_stage()
    else:
        game_stage()
