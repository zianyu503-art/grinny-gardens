"""Shared building blocks for the rebuilt Ticket Man and Child Shadow (bkit.base_body + real shells).

Everything works on the rigged base body: figure scaling / posed rest shapes, clothing shells cut
from the body's own surface (per vertex offset), custom lofted cloth, lathe-like rings, weight
helpers, per-part decimation, and the game join / bake / export steps.
Builds on ch3_human_common (C) for materials, clips and render helpers.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, "/Users/alex/恐怖遊戲2/blender/ghosts")
import ch3_human_common as C  # noqa: E402

bkit, lib = C.bkit, C.lib


def sm01(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- mesh makers
def obj_from(name, verts, faces, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if mat:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return o


def ring_faces(rings, closed=True, cap_first=False, cap_last=False):
    """rings: list of equal-length vertex lists. returns (flat verts, faces)."""
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            if not closed and j == 0:
                continue
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    if cap_first:
        faces.append(tuple(reversed(range(n))))
    if cap_last:
        base = (len(rings) - 1) * n
        faces.append(tuple(range(base, base + n)))
    return verts, faces


def orient_out(o, center=None):
    """Flip all faces if, on average, they point toward `center` (default: the mesh centroid)."""
    me = o.data
    c = Vector(center) if center is not None else sum((v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
    tot = sum(p.normal.dot(p.center - c) * p.area for p in me.polygons)
    if tot < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    return o


def weld(o, d=1e-4):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=d)
    bm.to_mesh(o.data)
    bm.free()
    return o


def ellipse(cx, cy, z, rx, ry, n=24, a0=0.0, a1=math.tau, bulge=None):
    pts = []
    for i in range(n):
        a = a0 + (a1 - a0) * i / n if a1 - a0 >= math.tau - 1e-6 else a0 + (a1 - a0) * i / (n - 1)
        r = 1.0 if bulge is None else bulge(a)
        pts.append(Vector((cx + rx * r * math.sin(a), cy - ry * r * math.cos(a), z)))
    return pts


def finish_mod(o, solid=0.0, offset=1.0, bevel=0.0, smooth_iter=0):
    """Apply Smooth / Solidify / Bevel modifiers right away (rest pose, identity transform)."""
    if smooth_iter:
        m = o.modifiers.new("Sm", "SMOOTH")
        m.factor = 0.6
        m.iterations = smooth_iter
    if solid:
        m = o.modifiers.new("So", "SOLIDIFY")
        m.thickness = solid
        m.offset = offset
        m.use_even_offset = False
    if bevel:
        b = o.modifiers.new("Bv", "BEVEL")
        b.width = bevel
        b.segments = 1
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(35)
    bkit.active(o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def uv(o, size=0.5):
    bkit.box_uv(o, size=size)
    return o


def mat_of(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def rigid(o, bone, m, arm, size=0.5):
    return C.tag(o, bone, m, arm) if size == 0.5 else (mat_of(o, m), uv(o, size), _grp(o, bone, arm))[2]


def _grp(o, bone, arm):
    g = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
    g.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    return C.skin_on(o, arm)


def weighted(o, arm, fn, m=None, size=0.5):
    """fn(co) -> {bone: weight}. Custom per-vertex weights for cloth that follows several bones."""
    if m is not None:
        mat_of(o, m)
    uv(o, size)
    groups = {}
    for v in o.data.vertices:
        for b, w in fn(v.co).items():
            if w <= 1e-4:
                continue
            g = groups.get(b) or o.vertex_groups.get(b) or o.vertex_groups.new(name=b)
            groups[b] = g
            g.add([v.index], w, "REPLACE")
    return C.skin_on(o, arm)


def cyl_along(name, a, b, r, r2=None, verts=12, cap=True, mat=None):
    """Cylinder / cone from a to b, a real mesh (no modifiers)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    z = d / L
    x = z.cross(Vector((0, 0, 1)))
    if x.length < 1e-4:
        x = z.cross(Vector((1, 0, 0)))
    x.normalize()
    y = z.cross(x)
    r2 = r if r2 is None else r2
    rings = []
    for t, rr in ((0, r), (1, r2)):
        rings.append([a + d * t + (x * math.cos(i / verts * math.tau) + y * math.sin(i / verts * math.tau)) * rr
                      for i in range(verts)])
    vs, fs = ring_faces(rings, cap_first=cap, cap_last=cap)
    return obj_from(name, vs, fs, mat)


def box(name, center, size, rot=(0, 0, 0), mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.active_object
    o.name = o.data.name = name
    o.scale = size
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        finish_mod(o, bevel=bevel)
    if mat:
        o.data.materials.append(mat)
    return o


def dome(name, center, r, scale=(1, 1, 1), rot=(0, 0, 0), segs=8, mat=None):
    """Rivet / button: upper half of a small UV sphere (the back sits against the surface)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(3, segs // 2), radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-5], context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.location = center
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.select_all(action="DESELECT")
    bkit.active(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for p in me.polygons:
        p.use_smooth = True
    if mat:
        me.materials.append(mat)
    return o


def dec(o, target, floor=20):
    """Decimate one part to about `target` tris (never below `floor`)."""
    t = bkit.tri_count(o)
    keep = max(int(target), floor)
    if keep < t:
        bkit.active(o)
        m = o.modifiers.new("Dec", "DECIMATE")
        m.ratio = keep / t
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


# ---------------------------------------------------------------- body shells
def dominant(v, dl, names):
    items = v[dl].items()
    if not items:
        return ""
    gi, _ = max(items, key=lambda kv: kv[1])
    return names[gi]


def cut_shell(body, name, sel, off, thick, mat, smooth_iter=0, bevel=0.0, size=0.5):
    names = [g.name for g in body.vertex_groups]
    me = body.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    dl = bm.verts.layers.deform.active
    es = body["eye_start"]
    ok = [v.index < es and sel(v.co, dominant(v, dl, names)) for v in bm.verts]
    nrm = [v.normal.copy() for v in bm.verts]
    for v in bm.verts:
        d = off(v.co) if callable(off) else off
        v.co += nrm[v.index] * d
    kill = [f for f in bm.faces if not all(ok[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    for g in body.vertex_groups:
        o.vertex_groups.new(name=g.name)
    me.materials.clear()
    me.materials.append(mat)
    finish_mod(o, solid=thick, bevel=bevel, smooth_iter=smooth_iter)
    uv(o, size)
    return o


# ---------------------------------------------------------------- figure scaling and rest pose
def reshape_figure(body, arm, fx, fy, dz=0.0, y0=0.0):
    """Remap vertices and bones: x *= fx(z), y = y0 + (y - y0) * fy(z), z += dz."""
    me = body.data
    for v in me.vertices:
        c = v.co
        v.co = Vector((c.x * fx(c.z), y0 + (c.y - y0) * fy(c.z), c.z + dz))
    me.update()

    def f(p):
        return Vector((p.x * fx(p.z), y0 + (p.y - y0) * fy(p.z), p.z + dz))
    bkit.active(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    new = {eb.name: (f(eb.head), f(eb.tail)) for eb in arm.data.edit_bones}  # connected bones drag each other
    for eb in arm.data.edit_bones:
        eb.use_connect = False
    for eb in arm.data.edit_bones:
        eb.head, eb.tail = new[eb.name]
    bpy.ops.object.mode_set(mode="OBJECT")


def best_sign(arm, bone, axis, probe, fn, deg=18):
    """+1 or -1: the sign of a rotation on `axis` (0..2) of `bone` that makes fn(probe position) smaller."""
    vals = {}
    for s in (1, -1):
        C.reset(arm)
        r = [0, 0, 0]
        r[axis] = s * deg
        bkit.pose(arm, {bone: tuple(r)})
        vals[s] = fn(C.bone_pos(arm, probe))
    C.reset(arm)
    return 1 if vals[1] < vals[-1] else -1


def bake_rest_pose(body, arm, rots):
    """Make a pose the new rest shape (mesh and armature)."""
    C.reset(arm)
    bkit.pose(arm, rots)
    bpy.context.view_layer.update()
    bkit.active(body)
    for m in list(body.modifiers):
        if m.type == "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=m.name)
    bkit.active(arm)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode="OBJECT")
    C.reset(arm)
    C.skin_on(body, arm)


def add_bone(arm, name, head, tail, parent, roll_axis=None):
    bkit.active(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones.new(name)
    eb.head, eb.tail = Vector(head), Vector(tail)
    eb.parent = arm.data.edit_bones[parent]
    if roll_axis is not None:
        eb.align_roll(Vector(roll_axis))
    bpy.ops.object.mode_set(mode="OBJECT")


def slice_box(body, zlo, zhi, bones=None, xmax=None):
    """min/max x and y over body vertices in a z band (optionally only some dominant bones)."""
    names = [g.name for g in body.vertex_groups]
    xs, ys = [], []
    for v in body.data.vertices:
        if v.index >= body["eye_start"] or not (zlo <= v.co.z <= zhi):
            continue
        if bones is not None:
            if not v.groups:
                continue
            gi = max(v.groups, key=lambda g: g.weight).group
            if names[gi] not in bones:
                continue
        if xmax is not None and abs(v.co.x) > xmax:
            continue
        xs.append(v.co.x)
        ys.append(v.co.y)
    return (min(xs), max(xs), min(ys), max(ys)) if xs else None


def bvh_of_obj(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def bvh_of(body, sel):
    names = [g.name for g in body.vertex_groups]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    dl = bm.verts.layers.deform.active
    es = body["eye_start"]
    ok = [v.index < es and sel(v.co, dominant(v, dl, names)) for v in bm.verts]
    kill = [f for f in bm.faces if not all(ok[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


# ---------------------------------------------------------------- game stage
def swap_none_slots(obj):
    first = next(m for m in obj.data.materials if m)
    for i, m in enumerate(obj.data.materials):
        if m is None:
            obj.data.materials[i] = first


def decimate_parts(parts, glow_parts, budget_total, floor=24):
    """Per-part decimation with one shared ratio and a minimum per part."""
    for o in parts + glow_parts:
        bkit.active(o)
        for m in list(o.modifiers):
            if m.type != "ARMATURE":
                bpy.ops.object.modifier_apply(modifier=m.name)
    tot = sum(bkit.tri_count(o) for o in parts)
    gt = sum(bkit.tri_count(o) for o in glow_parts)
    ratio = min(1.0, (budget_total - gt) / tot)
    print("BKIT_TRIS before", tot, "glow", gt, "ratio", round(ratio, 3))
    for o in parts:
        t = bkit.tri_count(o)
        if o.get("nodec"):
            continue
        dec(o, t * ratio, floor)
    return ratio


# ---------------------------------------------------------------- geometry helpers
def verts_where(body, pred):
    names = [g.name for g in body.vertex_groups]
    out = []
    for v in body.data.vertices:
        if v.index >= body["eye_start"] or not v.groups:
            continue
        b = names[max(v.groups, key=lambda g: g.weight).group]
        if pred(v.co, b):
            out.append(v.co.copy())
    return out


def hull2d(pts):
    p = sorted(set((round(q[0], 4), round(q[1], 4)) for q in pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def resample_poly(poly, n):
    """Evenly spaced n points along a closed polygon."""
    pts = list(poly) + [poly[0]]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(poly))]
    L = sum(seg)
    out, acc, i = [], 0.0, 0
    for k in range(n):
        d = L * k / n
        while acc + seg[i] < d:
            acc += seg[i]
            i += 1
        t = (d - acc) / seg[i]
        out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
    return out


class Frame:
    """Local frame: origin, lateral X, forward f, up u (all world vectors)."""

    def __init__(self, origin, up):
        self.o = Vector(origin)
        self.u = Vector(up).normalized()
        self.x = Vector((1, 0, 0))
        self.f = self.x.cross(self.u).normalized()

    def w(self, lx, lf, lu):
        return self.o + self.x * lx + self.f * lf + self.u * lu

    def l(self, p):
        d = Vector(p) - self.o
        return d.dot(self.x), d.dot(self.f), d.dot(self.u)


# ---------------------------------------------------------------- previews
def _shot(path, loc, target, lens=50, res=(800, 600), samples=24):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    cam = lib.camera(tuple(loc), tuple(target), lens=lens)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print("RENDERED", path)


def studio_shots(prefix, center, dist, face_target, face_dir, face_dist, samples=24):
    """prefix: renders/ch3_<ghost>_<tag> ; writes <prefix>.png (front | 3/4 side by side) and <prefix>_face.png."""
    import numpy as np
    bkit.light_studio()
    tiles = []
    tmp = prefix + "_tmp.png"
    for d in ((0, -1, 0.08), (0.72, -1, 0.14)):
        d = Vector(d).normalized()
        _shot(tmp, Vector(center) + d * dist, center, 50, (800, 600), samples)
        im = bpy.data.images.load(tmp)
        tiles.append(np.array(im.pixels[:]).reshape(600, 800, 4))
        bpy.data.images.remove(im)
    sheet = np.hstack(tiles)
    out = bpy.data.images.new("sheet", 1600, 600)
    out.pixels = sheet.ravel()
    out.filepath_raw = prefix + ".png"
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    os.remove(tmp)
    fd = Vector(face_dir).normalized()
    _shot(prefix + "_face.png", Vector(face_target) + fd * face_dist, face_target, 70, (800, 600), samples)


def dark_shot(path, target, cam_z=1.55, dist=6.0, energy=1800, samples=28, lens=35):
    """First-person view from `dist` metres away in the dark, lit only by one spot (a flashlight)."""
    for o in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
        bpy.data.objects.remove(o, do_unlink=True)
    lib.setup_render(samples=samples, res=(800, 600))
    floor = lib.stage("horror")
    cam_loc = Vector((0.0, target[1] - dist, cam_z))
    lib.add_area("Torch", (cam_loc.x + 0.25, cam_loc.y + 0.1, cam_z - 0.25), tuple(target), energy, (1.0, 0.86, 0.66), spot=True)
    cam = lib.camera(tuple(cam_loc), tuple(target), lens)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    for o in [o for o in bpy.context.scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.objects.remove(floor, do_unlink=True)
    print("RENDERED", path)
