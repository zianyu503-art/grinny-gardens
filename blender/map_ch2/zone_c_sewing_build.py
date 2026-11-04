"""Chapter 2 zone C: sewing hall with the Seamstress ceiling rail loop (zone_c_sewing).

Run from /Users/alex/恐怖遊戲2:
    blender -b --factory-startup -P blender/map_ch2/zone_c_sewing_build.py
Verify only (re-import the shipped GLB and render one eye view):
    blender -b --factory-startup -P blender/map_ch2/zone_c_sewing_build.py -- verify

Coordinates follow BRIEF.md: floor z=0, route along +Y, zone box x -18..18, y 34..74,
ceiling 7.0. Far wall (y 74..74.3) belongs to this zone and has the 2.4 m doorway.
No near wall is built (zone B owns y 34..34.3). PREVIEW_ objects exist only in the
render scene and are never exported.
"""
import sys, os, math, json, random, tempfile

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_c_sewing"
OUT_GLB = f"{ROOT}/public/models/ch2/{NAME}.glb"
OUT_JSON = f"{ROOT}/public/models/ch2/{NAME}.json"
OUT_BLEND = f"{ROOT}/blender/bake/map_ch2/{NAME}.blend"
OUT_EYE = f"{ROOT}/renders/ch2_{NAME}_eye.png"
OUT_TOP = f"{ROOT}/renders/ch2_{NAME}_top.png"
PROPS = f"{ROOT}/public/models"
SCRATCH = "/private/tmp/claude-504/-Users-alex-----2/df819384-06df-4249-8523-a5c0f94e5679/scratchpad"
VERIFY_PNG = f"{SCRATCH}/ch2_{NAME}_shipped_check.png"
TMP = tempfile.mkdtemp(prefix="zc_render_")

X0, X1, Y0, Y1, CEIL = -18.0, 18.0, 34.0, 74.0, 7.0
T = 0.3                      # wall thickness, built outward
DOOR_HALF, DOOR_H = 1.2, 3.0
RAIL_Z = 5.2                 # bottom flange of the rail loop
ROWS = [38.0 + 3.0 * i for i in range(11)]          # sewing-table rows along y
BEAM_Y = [37.0, 43.0, 49.0, 55.0, 61.0, 67.0, 73.0]  # ceiling I-beams running along x
FIX_DEAD = {(6.0, 43.0), (-6.0, 55.0), (6.0, 67.0)}
LAMPS = [(-7.0, 44.0), (7.0, 44.0), (-7.0, 64.0), (7.0, 64.0)]
OFFICE = (14.3, 17.7, 52.0, 62.0)                   # x0, x1, y0, y1

# I-beam profile (lateral u, height z above RAIL_Z), 0.40 m tall, bottom flange at RAIL_Z
IBEAM = [(-0.11, 0.00), (0.11, 0.00), (0.11, 0.04), (0.018, 0.04), (0.018, 0.36),
         (0.11, 0.36), (0.11, 0.40), (-0.11, 0.40), (-0.11, 0.36), (-0.018, 0.36),
         (-0.018, 0.04), (-0.11, 0.04)]


def loop_points():
    """Centre line of the rounded-rectangle rail loop (x +-14, y 38..70, corner R 4)."""
    pts = []

    def line(a, b):
        n = max(1, int(math.dist(a, b) / 0.5))
        for i in range(n):
            t = i / n
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))

    def arc(cx, cy, a0, a1, n=24):
        for i in range(n):
            t = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + 4.0 * math.cos(t), cy + 4.0 * math.sin(t)))

    line((14, 42), (14, 66)); arc(10, 66, 0, 90)
    line((10, 70), (-10, 70)); arc(-10, 66, 90, 180)
    line((-14, 66), (-14, 42)); arc(-10, 42, 180, 270)
    line((-10, 38), (10, 38)); arc(10, 42, 270, 360)
    return pts


LOOP = loop_points()


# ---------------------------------------------------------------- geometry helpers

def add_box_m(bm, M, sx, sy, sz):
    """Box of size sx*sy*sz standing on z=0 at its local origin, placed by matrix M."""
    c = [(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0),
         (-sx / 2, -sy / 2, sz), (sx / 2, -sy / 2, sz), (sx / 2, sy / 2, sz), (-sx / 2, sy / 2, sz)]
    v = [bm.verts.new(M @ Vector(p)) for p in c]
    for idx in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]:
        bm.faces.new([v[i] for i in idx])


def add_box(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for idx in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]:
        bm.faces.new([v[i] for i in idx])


def add_cyl(bm, p0, p1, r, seg=10):
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized()
    w = d.cross(u)
    rings = []
    for p in (p0, p1):
        rings.append([bm.verts.new(p + r * (math.cos(t) * u + math.sin(t) * w))
                      for t in [2 * math.pi * i / seg for i in range(seg)]])
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new([rings[0][i], rings[0][j], rings[1][j], rings[1][i]])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])


def add_poly(bm, pts):
    bm.faces.new([bm.verts.new((x, y, z)) for x, y, z in pts])


def add_sweep(bm, pts, closed, prof, z0):
    """Sweep a 2-D profile (u lateral, z up) along a horizontal polyline."""
    n = len(pts)
    rings = []
    for i in range(n):
        if closed:
            a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty)
        tx, ty = tx / L, ty / L
        nx, ny = -ty, tx
        px, py = pts[i]
        rings.append([bm.verts.new((px + nx * u, py + ny * u, z0 + z)) for (u, z) in prof])
    m = len(prof)
    for i in range(n if closed else n - 1):
        A, B = rings[i], rings[(i + 1) % n]
        for k in range(m):
            l = (k + 1) % m
            bm.faces.new([A[k], A[l], B[l], B[k]])
    if not closed:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])


def build_obj(name, bm, mat, uv=None, bevel=0.0, smooth=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = smooth
    if uv:
        bkit.box_uv(obj, size=uv)
    if bevel:
        bkit.harden(obj, width=bevel, segments=2)
    return obj


def flat(name, rgb, rough=0.7, metal=0.0, emit=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit[0], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit[1]
    return mat


def make_materials():
    M = {}
    M["floor"] = bkit.pbr_material("C_floor", bkit.polyhaven_texture("concrete_floor_worn_001"))
    M["wall"] = bkit.pbr_material("C_wall", bkit.polyhaven_texture("peeling_painted_wall"),
                                  tint=(0.93, 0.95, 0.92))
    M["ceiling"] = bkit.pbr_material("C_ceiling", bkit.polyhaven_texture("ceiling_interior"))
    M["beam"] = bkit.pbr_material("C_steel_beam", bkit.polyhaven_texture("rusty_metal_02"))
    M["rail"] = bkit.pbr_material("C_rail_steel", bkit.polyhaven_texture("metal_plate"))
    M["painted"] = bkit.pbr_material("C_painted_metal", bkit.polyhaven_texture("rusty_painted_metal"))
    M["fabric"] = bkit.pbr_material("C_fabric", bkit.polyhaven_texture("hessian_230"))
    M["linen"] = bkit.pbr_material("C_linen", bkit.polyhaven_texture("rough_linen"))
    M["glass"] = flat("C_glass", (0.02, 0.05, 0.06), 0.06)
    M["fixture"] = flat("C_fixture", (0.22, 0.22, 0.21), 0.6, 0.5)
    M["tube_off"] = flat("C_tube_off", (0.4, 0.4, 0.38), 0.4)
    M["tube_on"] = flat("C_tube_on", (0.9, 0.92, 0.9), 0.3, emit=((0.85, 0.9, 1.0), 4.0))
    M["paper"] = flat("C_paper", (0.6, 0.58, 0.5), 0.9)
    M["hazard"] = flat("C_hazard_paint", (0.55, 0.42, 0.08), 0.7)
    M["puddle"] = flat("C_puddle", (0.02, 0.02, 0.02), 0.03)
    M["grime"] = flat("C_grime", (0.12, 0.1, 0.07), 0.95)
    M["black"] = flat("C_black_metal", (0.03, 0.03, 0.03), 0.5, 0.8)
    M["sign_plate"] = flat("C_sign_plate", (0.55, 0.5, 0.4), 0.7)
    M["sign_red"] = flat("C_sign_red", (0.35, 0.04, 0.03), 0.6)
    return M


# ---------------------------------------------------------------- shell

def build_shell(M, ex, shell):
    rng = random.Random(7)

    def keep(o, bucket=shell):
        bucket.append(o)
        return o

    # floor top at z=0, ceiling bottom at z=7.0 (both inside the zone box)
    bm = bmesh.new(); add_box(bm, X0, X1, Y0, Y1, -0.3, 0.0)
    keep(build_obj("C_floor", bm, M["floor"], uv=3.0))
    bm = bmesh.new(); add_box(bm, X0, X1, Y0, Y1, CEIL, CEIL + 0.3)
    keep(build_obj("C_ceiling", bm, M["ceiling"], uv=2.0))

    # side walls, flush with the boundaries, outward
    bm = bmesh.new()
    add_box(bm, X0 - T, X0, Y0, Y1, -0.3, CEIL + 0.3)
    add_box(bm, X1, X1 + T, Y0, Y1, -0.3, CEIL + 0.3)
    keep(build_obj("C_wall_side", bm, M["wall"], uv=2.5, bevel=0.02))

    # far wall with the doorway (y 74..74.3): two piers and a lintel above the opening
    bm = bmesh.new()
    add_box(bm, X0 - T, -DOOR_HALF, Y1, Y1 + T, -0.3, CEIL + 0.3)
    add_box(bm, DOOR_HALF, X1 + T, Y1, Y1 + T, -0.3, CEIL + 0.3)
    add_box(bm, -DOOR_HALF, DOOR_HALF, Y1, Y1 + T, DOOR_H, CEIL + 0.3)
    keep(build_obj("C_wall_far", bm, M["wall"], uv=2.5, bevel=0.02))

    # steel door casing, standing just outside the 2.4 m opening
    bm = bmesh.new()
    add_box(bm, -DOOR_HALF - 0.12, -DOOR_HALF, Y1 - 0.12, Y1 + T, 0.0, DOOR_H + 0.12)
    add_box(bm, DOOR_HALF, DOOR_HALF + 0.12, Y1 - 0.12, Y1 + T, 0.0, DOOR_H + 0.12)
    add_box(bm, -DOOR_HALF - 0.12, DOOR_HALF + 0.12, Y1 - 0.12, Y1 + T, DOOR_H, DOOR_H + 0.12)
    keep(build_obj("C_door_casing", bm, M["painted"], uv=1.0, bevel=0.01))

    # grimy skirting band along both side walls
    bm = bmesh.new()
    add_box(bm, X0, X0 + 0.03, Y0, Y1, 0.0, 0.5)
    add_box(bm, X1 - 0.03, X1, Y0, Y1, 0.0, 0.5)
    keep(build_obj("C_grime_skirting", bm, M["grime"]))

    # ceiling I-beams running along x
    bm = bmesh.new()
    for y in BEAM_Y:
        add_box(bm, X0, X1, y - 0.15, y + 0.15, 6.36, CEIL)
    keep(build_obj("C_ceiling_beams", bm, M["beam"], uv=1.0, bevel=0.02))

    # ducts under the beams, and pipes along the side walls
    bm = bmesh.new()
    add_box(bm, 8.5, 9.5, Y0, Y1, 5.9, 6.3)
    add_box(bm, -9.5, -8.5, Y0, Y1, 5.9, 6.3)
    keep(build_obj("C_ducts", bm, M["painted"], uv=1.0, bevel=0.02))
    bm = bmesh.new()
    for x in (-17.6, 17.6):
        add_cyl(bm, (x, Y0, 6.45), (x, Y1, 6.45), 0.06, 10)
    keep(build_obj("C_pipes_big", bm, M["painted"], uv=1.0, smooth=True))
    bm = bmesh.new()
    for x in (-17.6, 17.6):
        add_cyl(bm, (x, Y0, 6.05), (x, Y1, 6.05), 0.035, 8)
    keep(build_obj("C_cables", bm, M["black"], smooth=True))

    # the 2 m rail loop and cross rail: I-beam sweeps, bottom flange at z = 5.2
    bm = bmesh.new()
    add_sweep(bm, LOOP, True, IBEAM, RAIL_Z)
    add_sweep(bm, [(-13.9, 54.0), (13.9, 54.0)], False, IBEAM, RAIL_Z)
    keep(build_obj("C_rail_loop", bm, M["rail"], uv=0.5))
    # drop rods from the rail top (5.6) up to the ceiling every ~5 m along the loop
    bm = bmesh.new()
    for i in range(0, len(LOOP), 10):
        x, y = LOOP[i]
        add_cyl(bm, (x, y, RAIL_Z + 0.4), (x, y, CEIL), 0.025, 8)
    keep(build_obj("C_rail_rods", bm, M["black"], smooth=True))

    # raised foreman's office on the right wall: steel legs, body, roof, dark window panes
    ox0, ox1, oy0, oy1 = OFFICE
    bm = bmesh.new()
    add_box(bm, ox0, ox1, oy0, oy1, 2.2, 2.4)           # floor slab
    add_box(bm, ox0, ox1, oy0, oy1, 2.4, 4.85)          # body
    add_box(bm, ox0 - 0.1, ox1 + 0.1, oy0 - 0.1, oy1 + 0.1, 4.85, 4.95)  # roof
    for lx in (ox0 + 0.15, ox1 - 0.27):
        for ly in (oy0 + 0.15, oy1 - 0.27):
            add_box(bm, lx, lx + 0.12, ly, ly + 0.12, 0.0, 2.2)
    panes = [(52.5, 54.3), (55.0, 56.8), (57.5, 59.3)]
    for (wy0, wy1) in panes:
        add_box(bm, ox0 - 0.04, ox0 + 0.0, wy0 - 0.05, wy1 + 0.05, 4.3, 4.36)   # top bar
        add_box(bm, ox0 - 0.04, ox0 + 0.0, wy0 - 0.05, wy1 + 0.05, 2.8 - 0.06, 2.8)  # sill
        add_box(bm, ox0 - 0.04, ox0 + 0.0, wy0 - 0.05, wy0, 2.8, 4.3)            # left post
        add_box(bm, ox0 - 0.04, ox0 + 0.0, wy1, wy1 + 0.05, 2.8, 4.3)            # right post
    keep(build_obj("C_office", bm, M["painted"], uv=1.0, bevel=0.02))
    bm = bmesh.new()
    for (wy0, wy1) in panes:
        add_box(bm, ox0 - 0.03, ox0 - 0.01, wy0, wy1, 2.8, 4.3)
    keep(build_obj("C_office_glass", bm, M["glass"]))

    # hazard paint on the floor along the main aisle edges
    bm = bmesh.new()
    add_box(bm, -2.12, -2.02, 36.0, 72.0, 0.0, 0.004)
    add_box(bm, 2.02, 2.12, 36.0, 72.0, 0.0, 0.004)
    keep(build_obj("C_hazard_lines", bm, M["hazard"]))

    # floor drains, puddles, loose paper, cloth and fallen ceiling tiles
    bm = bmesh.new()
    for (x, y) in [(-10.0, 46.0), (10.5, 62.0), (-5.5, 70.5), (7.0, 40.5)]:
        add_box_m(bm, Matrix.Translation((x, y, 0.0)), 0.45, 0.45, 0.006)
    keep(build_obj("C_drains", bm, M["black"]))
    bm = bmesh.new()
    for _ in range(7):
        cx, cy = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        R = rng.uniform(0.5, 1.2)
        n = 14
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            r = R * rng.uniform(0.75, 1.0)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t) * 0.8, 0.002))
        add_poly(bm, pts)
    keep(build_obj("C_puddles", bm, M["puddle"]))
    bm = bmesh.new()
    for _ in range(16):
        cx, cy = rng.uniform(X0 + 1, X1 - 1), rng.uniform(Y0 + 1, Y1 - 1)
        a = rng.uniform(0, math.tau)
        c, s = math.cos(a), math.sin(a)
        hw, hl = 0.11, 0.15
        pts = []
        for (u, v) in [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)]:
            pts.append((cx + u * c - v * s, cy + u * s + v * c, 0.004 + rng.uniform(0, 0.002)))
        add_poly(bm, pts)
    keep(build_obj("C_paper", bm, M["paper"]))
    bm = bmesh.new()
    for _ in range(4):
        cx, cy = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        a = rng.uniform(0, math.tau)
        pts = []
        for k in range(6):
            t = a + math.tau * k / 6
            r = rng.uniform(0.25, 0.4)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t), 0.005))
        add_poly(bm, pts)
    keep(build_obj("C_loose_cloth", bm, M["linen"]))
    bm = bmesh.new()
    for (x, y) in [(-12.0, 60.0), (9.0, 41.5), (-3.0, 65.0), (15.0, 69.0)]:
        M4 = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(rng.uniform(0, math.tau), 4, "Z")
        add_box_m(bm, M4, 0.6, 0.6, 0.02)
    keep(build_obj("C_debris_tiles", bm, M["ceiling"], uv=2.0))

    # signs: plates with raised lettering (text converted to mesh)
    bm = bmesh.new()
    add_box(bm, -0.7, 0.7, Y1 - 0.12, Y1 - 0.10, 3.25, 3.75)          # EXIT plate over door
    add_box(bm, X0, X0 + 0.02, 45.2, 46.8, 1.85, 2.15)                 # left wall plate
    add_box(bm, X1 - 0.02, X1, 59.2, 60.8, 1.85, 2.15)                 # right wall plate
    keep(build_obj("C_sign_plates", bm, M["sign_plate"]))
    texts = [("EXIT", (0.0, Y1 - 0.13, 3.42), (math.radians(90), 0, 0), 0.22),
             ("STAFF ONLY", (X0 + 0.03, 46.0, 2.0), (math.radians(90), 0, math.radians(90)), 0.16),
             ("DANGER", (X1 - 0.03, 60.0, 2.0), (math.radians(90), 0, math.radians(-90)), 0.18)]
    for body, loc, rot, size in texts:
        curve = bpy.data.curves.new("C_sign_text_curve", "FONT")
        curve.body = body
        curve.size = size
        curve.extrude = 0.004
        curve.align_x = "CENTER"
        obj = bpy.data.objects.new("C_sign_text_" + body.replace(" ", "_"), curve)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = rot
        bkit.active(obj)
        bpy.ops.object.convert(target="MESH")
        obj = bpy.context.view_layer.objects.active
        obj.data.materials.clear()
        obj.data.materials.append(M["sign_red"])
        shell.append(obj)

    # work lamps on cords, plus a thread spool on the floor (pickup marker)
    bm = bmesh.new()
    for (x, y) in LAMPS:
        add_cyl(bm, (x, y, CEIL), (x, y, 2.5), 0.008, 6)
    keep(build_obj("C_lamp_cords", bm, M["black"], smooth=True))
    for i, (x, y) in enumerate(LAMPS):
        shade = bkit.lathe([(0.2, 0.0), (0.07, 0.2), (0.0, 0.2)], segments=14,
                           name=f"C_work_lamp_shade_{i}")
        shade.location = (x, y, 2.3)
        shade.data.materials.append(M["black"])
        shell.append(shade)
    SPOOL = (9.8, 57.5, 0.0)
    bm = bmesh.new()
    add_cyl(bm, (SPOOL[0], SPOOL[1], 0.0), (SPOOL[0], SPOOL[1], 0.08), 0.045, 10)
    keep(build_obj("C_spool", bm, M["fabric"], uv=0.5, smooth=True))

    # ceiling light fixtures under the beams (9 slots, 6 working)
    bm_h, bm_on, bm_off = bmesh.new(), bmesh.new(), bmesh.new()
    for y in (43.0, 55.0, 67.0):
        for x in (-6.0, 0.0, 6.0):
            add_box(bm_h, x - 0.6, x + 0.6, y - 0.15, y + 0.15, 6.24, 6.36)
            tube = bm_off if (x, y) in FIX_DEAD else bm_on
            add_box(tube, x - 0.55, x + 0.55, y - 0.05, y + 0.05, 6.22, 6.24)
    keep(build_obj("C_fixture_housing", bm_h, M["fixture"], uv=1.0))
    keep(build_obj("C_tubes_on", bm_on, M["tube_on"]))
    keep(build_obj("C_tubes_off", bm_off, M["tube_off"]))


def build_props(M, ex, colliders, markers, shell, rng):
    """Sewing machines in a grid, plush piles and fabric bolts between the rows."""
    machine_src = bkit.import_glb(f"{PROPS}/sewing_machine.glb")[0]
    plush_src = bkit.import_glb(f"{PROPS}/plush_pile.glb")[0]
    for src in (machine_src, plush_src):
        src.rotation_mode = "XYZ"  # glTF imports use quaternions, which ignore rotation_euler
    cols_left = [-16.5 + 2.6 * k for k in range(6)]
    cols_right = [3.5 + 2.6 * k for k in range(6)]
    n_m = 0
    for ri, y in enumerate(ROWS):
        for x in cols_left + cols_right:
            if rng.random() < 0.2:
                continue
            if x > 12.0 and OFFICE[2] - 2 < y < OFFICE[3] + 2:
                continue
            rot = (math.pi if ri % 2 else 0.0) + math.radians(rng.uniform(-4, 4))
            px = x + rng.uniform(-0.05, 0.05)
            py = y + rng.uniform(-0.05, 0.05)
            o = machine_src.copy()
            o.name = f"C_sewing_machine_{n_m:03d}"
            bpy.context.scene.collection.objects.link(o)
            o.location = (px, py, 0.0)
            o.rotation_euler = (0, 0, rot)
            ex.append(o)
            colliders.append([round(px, 3), round(py, 3), 0.7, 1.1, 0.542, 1.403, round(rot, 4)])
            n_m += 1
    print("ZC machines placed:", n_m)

    gap_ys = [r + 1.5 for r in ROWS]
    # fabric bolts lying on the floor in the gaps between rows
    bolts = []
    bm = bmesh.new()
    for _ in range(10):
        side = rng.choice([(-15.5, -3.5), (3.5, 15.5)])
        x = rng.uniform(*side)
        gy = rng.choice(gap_ys)
        add_cyl(bm, (x - 0.5, gy, 0.2), (x + 0.5, gy, 0.2), 0.2, 14)
        colliders.append([round(x, 3), gy, 0.2, 1.0, 0.4, 0.4, 0])
        bolts.append((x, gy))
    shell.append(build_obj("C_fabric_bolts", bm, M["fabric"], uv=0.5, smooth=True))

    # half-sewn plush piles on the floor by the tables
    for k in range(6):
        side = rng.choice([(-15.5, -3.5), (3.5, 15.5)])
        x = rng.uniform(*side)
        gy = rng.choice(gap_ys)
        rot = rng.choice([0.0, math.pi / 2]) + rng.uniform(-0.2, 0.2)
        o = plush_src.copy()
        o.name = f"C_plush_pile_{k}"
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, gy, 0.0)
        o.rotation_euler = (0, 0, rot)
        ex.append(o)
        colliders.append([round(x, 3), gy, 0.38, 0.82, 1.36, 0.76, round(rot, 4)])

    # clean up the import templates: the copies keep the shared mesh data
    bpy.data.objects.remove(machine_src, do_unlink=True)
    bpy.data.objects.remove(plush_src, do_unlink=True)
    return bolts



def add_text(body, loc, rot, size, mat, shell):
    curve = bpy.data.curves.new("C_text_curve", "FONT")
    curve.body = body
    curve.size = size
    curve.extrude = 0.004
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new("C_text_" + body.replace(" ", "_"), curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    bkit.active(obj)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    shell.append(obj)


def blob(bm, cx, cy, z, R, rng, sx=1.0):
    pts = []
    for i in range(12):
        t = 2 * math.pi * i / 12
        r = R * rng.uniform(0.75, 1.0)
        pts.append((cx + r * sx * math.cos(t), cy + r * math.sin(t), z))
    add_poly(bm, pts)


def build_dressing(M, ex, shell, colliders, rng):
    """Rail trolley, wall dressing, floor dressing, bins, bolt stacks and overturned chairs."""
    # rail trolley parked on the cross rail: wheels on the bottom flange, body hung below it
    bm = bmesh.new()
    add_box(bm, -0.35, 0.35, 53.7, 54.3, 4.55, RAIL_Z)
    for x in (-0.25, 0.25):
        add_cyl(bm, (x, 53.8, RAIL_Z + 0.02), (x, 54.2, RAIL_Z + 0.02), 0.06, 10)
    add_cyl(bm, (0.0, 54.0, 4.55), (0.0, 54.0, 4.3), 0.03, 8)
    shell.append(build_obj("C_trolley", bm, M["painted"], smooth=True))

    # shelving on the side walls, outside the rail footprint
    sh, bolts_bm = bmesh.new(), bmesh.new()
    units = [(X0 + 0.08, X0 + 0.63, 40.0, 42.2), (X0 + 0.08, X0 + 0.63, 61.0, 63.2),
             (X1 - 0.63, X1 - 0.08, 36.0, 38.2), (X1 - 0.63, X1 - 0.08, 69.0, 71.2)]
    for (ux0, ux1, uy0, uy1) in units:
        add_box(sh, ux0, ux0 + 0.02, uy0, uy1, 0.0, 2.2)
        add_box(sh, ux0, ux1, uy0, uy0 + 0.03, 0.0, 2.2)
        add_box(sh, ux0, ux1, uy1 - 0.03, uy1, 0.0, 2.2)
        for zs in (0.02, 0.62, 1.22, 1.82):
            add_box(sh, ux0, ux1, uy0, uy1, zs, zs + 0.03)
            for bx in (ux0 + 0.17, ux1 - 0.17):
                add_cyl(bolts_bm, (bx, uy0 + 0.3, zs + 0.14), (bx, uy1 - 0.3, zs + 0.14), 0.11, 10)
        colliders.append([round((ux0 + ux1) / 2, 3), round((uy0 + uy1) / 2, 3), 1.1,
                          round(ux1 - ux0, 3), round(uy1 - uy0, 3), 2.2, 0])
    shell.append(build_obj("C_shelving", sh, M["painted"], uv=1.0))
    shell.append(build_obj("C_shelf_bolts", bolts_bm, M["fabric"], uv=0.5, smooth=True))

    # vertical pipes and conduit brackets on both side walls
    pb = bmesh.new()
    for (x, y) in [(-17.6, 37.2), (-17.6, 54.0), (-17.6, 71.0), (17.6, 47.0), (17.6, 66.0)]:
        add_cyl(pb, (x, y, 0.0), (x, y, 6.3), 0.05, 10)
        for zb in (1.2, 4.0):
            add_box(pb, x - 0.07, x + 0.07, y - 0.07, y + 0.07, zb, zb + 0.1)
    shell.append(build_obj("C_pipes_vertical", pb, M["painted"], uv=1.0, smooth=True))

    # fuse boxes
    fb = bmesh.new()
    for (y, z) in [(45.0, 1.3), (58.0, 1.4)]:
        add_box(fb, X0, X0 + 0.09, y, y + 0.35, z, z + 0.3)
    for (y, z) in [(42.5, 1.3), (58.5, 1.4)]:
        add_box(fb, X1 - 0.09, X1, y, y + 0.35, z, z + 0.3)
    shell.append(build_obj("C_fuse_boxes", fb, M["fixture"], uv=1.0, bevel=0.01))

    # wall fans (housing and grille)
    fan, grille = bmesh.new(), bmesh.new()
    for (wx, fy, side) in [(X0, 56.0, 1), (X1, 49.5, -1)]:
        fz = 2.4
        add_cyl(fan, (wx + side * 0.01, fy, fz), (wx + side * 0.3, fy, fz), 0.28, 16)
        add_cyl(grille, (wx + side * 0.3, fy, fz), (wx + side * 0.32, fy, fz), 0.22, 16)
    shell.append(build_obj("C_wall_fans", fan, M["black"], smooth=True))
    shell.append(build_obj("C_fan_grilles", grille, M["fixture"], smooth=True))

    # water streaks running down the walls
    ws = bmesh.new()
    for _ in range(26):
        side = rng.choice("LRF")
        top = rng.uniform(4.5, 6.9)
        z0 = max(0.0, top - rng.uniform(1.5, 4.0))
        if side == "L":
            y = rng.uniform(Y0 + 1, Y1 - 1)
            add_box(ws, X0, X0 + 0.02, y, y + 0.05, z0, top)
        elif side == "R":
            y = rng.uniform(Y0 + 1, Y1 - 1)
            add_box(ws, X1 - 0.02, X1, y, y + 0.05, z0, top)
        else:
            x = rng.uniform(X0 + 1, X1 - 1)
            add_box(ws, x, x + 0.05, Y1 - 0.02, Y1, z0, top)
    shell.append(build_obj("C_water_streaks", ws, M["grime"]))

    # posters and quota boards
    pb = bmesh.new()
    add_box(pb, -10.2, -7.8, Y1 - 0.08, Y1 - 0.06, 1.9, 2.9)
    add_box(pb, 6.2, 6.8, Y1 - 0.07, Y1 - 0.05, 1.6, 2.3)
    add_box(pb, 10.0, 10.6, Y1 - 0.07, Y1 - 0.05, 1.6, 2.3)
    add_box(pb, X0 + 0.005, X0 + 0.025, 58.6, 59.2, 1.9, 2.6)
    shell.append(build_obj("C_posters", pb, M["paper"]))
    add_text("QUOTA 800", (-9.0, Y1 - 0.1, 2.55), (math.radians(90), 0, 0), 0.16, M["sign_red"], shell)
    add_text("SMILE!", (6.5, Y1 - 0.09, 2.0), (math.radians(90), 0, 0), 0.12, M["sign_red"], shell)
    add_text("NO TALKING", (X0 + 0.03, 58.9, 2.25), (math.radians(90), 0, math.radians(90)), 0.1,
             M["sign_red"], shell)

    # floor: thread spools, fabric scraps, oil marks, stains
    th = bmesh.new()
    for _ in range(14):
        x, y = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        add_cyl(th, (x, y, 0.0), (x, y, 0.045), rng.uniform(0.025, 0.035), 8)
    shell.append(build_obj("C_thread_spools", th, M["fabric"], uv=0.5, smooth=True))
    sc = bmesh.new()
    for _ in range(14):
        cx, cy = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        a = rng.uniform(0, math.tau)
        c, s = math.cos(a), math.sin(a)
        pts = []
        for (u, v) in [(-0.15, -0.1), (0.15, -0.09), (0.12, 0.11), (-0.13, 0.1)]:
            pts.append((cx + u * c - v * s, cy + u * s + v * c, 0.004))
        add_poly(sc, pts)
    shell.append(build_obj("C_fabric_scraps", sc, M["linen"]))
    oil = bmesh.new()
    for _ in range(9):
        blob(oil, rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2), 0.003,
             rng.uniform(0.3, 0.6), rng, sx=rng.uniform(0.7, 1.4))
    shell.append(build_obj("C_oil_marks", oil, M["puddle"]))
    stains = bmesh.new()
    for _ in range(8):
        blob(stains, rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2), 0.002,
             rng.uniform(0.6, 1.5), rng, sx=rng.uniform(0.6, 1.2))
    shell.append(build_obj("C_floor_stains", stains, M["grime"]))

    # bins of half-sewn plush in the gaps between table rows
    bin_bm, lump_bm = bmesh.new(), bmesh.new()
    bins = [(-10.0, 39.5, 0.0), (10.0, 45.5, 0.4), (-10.0, 63.5, 0.0), (-10.0, 66.5, 0.3)]
    for (x, y, rot) in bins:
        Mb = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(rot, 4, "Z")
        tb, tl = bmesh.new(), bmesh.new()
        add_box(tb, -0.35, 0.35, -0.25, 0.25, 0.0, 0.03)
        add_box(tb, -0.35, 0.35, -0.25, -0.22, 0.0, 0.4)
        add_box(tb, -0.35, 0.35, 0.22, 0.25, 0.0, 0.4)
        add_box(tb, -0.35, -0.32, -0.25, 0.25, 0.0, 0.4)
        add_box(tb, 0.32, 0.35, -0.25, 0.25, 0.0, 0.4)
        for _ in range(3):
            lx, ly, lz = rng.uniform(-0.2, 0.2), rng.uniform(-0.15, 0.15), rng.uniform(0.12, 0.22)
            ret = bmesh.ops.create_icosphere(tl, subdivisions=1, radius=0.5)
            Ms = Matrix.Translation((lx, ly, lz)) @ Matrix.Diagonal((0.16, 0.14, 0.12, 1.0))
            bmesh.ops.transform(tl, matrix=Ms, verts=ret["verts"])
        bmesh.ops.transform(tb, matrix=Mb, verts=tb.verts)
        bmesh.ops.transform(tl, matrix=Mb, verts=tl.verts)
        for src, dst in ((tb, bin_bm), (tl, lump_bm)):
            vmap = {v: dst.verts.new(v.co) for v in src.verts}
            dst.verts.ensure_lookup_table()
            for f in src.faces:
                dst.faces.new([vmap[v] for v in f.verts])
            src.free()
        colliders.append([x, y, 0.2, 0.7, 0.5, 0.4, rot])
    shell.append(build_obj("C_plush_bins", bin_bm, M["painted"], uv=1.0))
    shell.append(build_obj("C_plush_bin_lumps", lump_bm, M["linen"], uv=0.5, smooth=True))

    # stacks of fabric bolts in the aisle gaps
    st = bmesh.new()
    for (x, y) in [(-12.6, 42.5), (4.8, 60.5), (12.6, 48.5)]:
        add_cyl(st, (x - 0.22, y - 0.5, 0.2), (x - 0.22, y + 0.5, 0.2), 0.2, 12)
        add_cyl(st, (x + 0.22, y - 0.5, 0.2), (x + 0.22, y + 0.5, 0.2), 0.2, 12)
        add_cyl(st, (x, y - 0.5, 0.55), (x, y + 0.5, 0.55), 0.2, 12)
        colliders.append([x, y, 0.4, 0.5, 1.0, 0.6, 0])
    shell.append(build_obj("C_bolt_stacks", st, M["fabric"], uv=0.5, smooth=True))

    # overturned chairs lying on their sides
    for k, (x, y, th) in enumerate([(-9.0, 47.5, 1.1), (4.5, 62.0, -0.5), (11.0, 40.3, 2.0)]):
        cb = bmesh.new()
        add_box(cb, -0.21, 0.21, -0.21, 0.21, 0.42, 0.46)
        add_box(cb, -0.21, 0.21, -0.23, -0.19, 0.46, 0.92)
        for lx in (-0.19, 0.19):
            for ly in (-0.19, 0.19):
                add_cyl(cb, (lx, ly, 0.0), (lx, ly, 0.42), 0.016, 6)
        Mc = Matrix.Translation((x, y, 0.24)) @ Matrix.Rotation(th, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
        bmesh.ops.transform(cb, matrix=Mc, verts=cb.verts)
        shell.append(build_obj(f"C_chair_{k}", cb, M["black"], smooth=True))

def build_lights_preview(col_lights):
    """Dim cold tubes and warm lamps for previews only; lights are not exported."""
    for (x, y) in [(xx, yy) for yy in (43.0, 55.0, 67.0) for xx in (-6.0, 0.0, 6.0)]:
        if (x, y) in FIX_DEAD:
            continue
        L = bpy.data.lights.new("PREVIEW_tube", "AREA")
        L.shape = "RECTANGLE"
        L.size, L.size_y = 1.1, 0.1
        L.energy = 170.0
        L.color = (0.82, 0.9, 1.0)
        o = bpy.data.objects.new("PREVIEW_tube", L)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, y, 6.15)
    for (x, y) in [(-10.0, 54.0), (10.0, 54.0)]:
        L = bpy.data.lights.new("PREVIEW_rail", "POINT")
        L.energy = 60.0
        L.color = (0.8, 0.86, 1.0)
        o = bpy.data.objects.new("PREVIEW_rail", L)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, y, 5.9)
    for (x, y) in LAMPS:
        L = bpy.data.lights.new("PREVIEW_lamp", "POINT")
        L.energy = 110.0
        L.color = (1.0, 0.68, 0.38)
        L.shadow_soft_size = 0.05
        o = bpy.data.objects.new("PREVIEW_lamp", L)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, y, 2.15)
    w = bpy.data.worlds.new("PREVIEW_world")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0, 0.0, 0.0, 1)
    bpy.context.scene.world = w


def set_render(samples, w, h):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    return sc


def eye_cam(loc, target, lens=24):
    cd = bpy.data.cameras.new("EyeCam")
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.05, 120
    cam = bpy.data.objects.new("EyeCam", cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render_to(path, cam, w, h, samples):
    sc = set_render(samples, w, h)
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


EYE_VIEWS = [
    ("near_doorway", (0.0, 47.0, 1.6), (0.0, 34.0, 1.6)),
    ("far_doorway", (0.0, 60.0, 1.6), (0.0, 74.0, 1.6)),
    ("rail_loop", (-6.0, 46.0, 1.6), (0.0, 54.0, 5.0)),
    ("foreman_office", (5.0, 56.0, 1.6), (16.0, 57.0, 2.8)),
    ("hall_overview", (-16.0, 37.5, 1.6), (14.0, 72.0, 1.8)),
    ("sewing_rows", (-1.0, 41.0, 1.6), (-12.0, 47.0, 1.0)),
    ("rail_up", (-9.0, 50.0, 1.6), (-14.0, 56.0, 5.3)),
    ("trolley_up", (-3.0, 49.5, 1.6), (0.0, 54.0, 4.8)),
    ("floor_bins", (5.0, 46.0, 1.4), (9.0, 50.0, 0.4)),
    ("walls_detail", (-16.0, 66.0, 1.6), (-18.0, 58.0, 2.2)),
]


def contact_sheet(paths, cols, w, h, out_path):
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p, check_existing=False)
        imgs.append(np.array(im.pixels[:]).reshape(h, w, 4))
        bpy.data.images.remove(im)
    rows = math.ceil(len(imgs) / cols)
    while len(imgs) < rows * cols:
        imgs.append(np.zeros((h, w, 4)))
    row_arrays = [np.hstack(imgs[r * cols:(r + 1) * cols]) for r in range(rows)]
    full = np.vstack(row_arrays[::-1])   # pixel rows are bottom-up
    out = bpy.data.images.new("sheet", w * cols, h * rows, alpha=True)
    out.pixels = full.ravel()
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def render_previews():
    # render-only proxy for zone B's far wall (x -10.3..10.3, y 34..34.3, doorway in the middle)
    bm = bmesh.new()
    add_box(bm, -10.3, -DOOR_HALF, Y0, Y0 + T, -0.3, CEIL + 0.3)
    add_box(bm, DOOR_HALF, 10.3, Y0, Y0 + T, -0.3, CEIL + 0.3)
    add_box(bm, -DOOR_HALF, DOOR_HALF, Y0, Y0 + T, DOOR_H, CEIL + 0.3)
    build_obj("PREVIEW_B_far_wall", bm, bpy.data.materials["C_wall"], uv=2.5)
    paths = []
    for i, (label, loc, tgt) in enumerate(EYE_VIEWS):
        p = os.path.join(TMP, f"eye_{i}.png")
        render_to(p, eye_cam(loc, tgt), 640, 360, 24)
        paths.append(p)
        print("ZC rendered", label)
    contact_sheet(paths, 4, 640, 360, OUT_EYE)

    # top view with the ceiling and high items hidden (the office and rails stay visible)
    hide_keys = ("ceiling", "beams", "fixture", "tubes", "lamp", "cords", "shade", "ducts",
                 "pipes", "cables", "sign_", "rods")
    hidden = [o for o in bpy.context.scene.objects
              if o.type == "MESH" and o.name.startswith("C_") and any(k in o.name for k in hide_keys)]
    for o in hidden:
        o.hide_render = True
    cd = bpy.data.cameras.new("TopCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 46.0
    cam = bpy.data.objects.new("TopCam", cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0.0, 54.0, 40.0)
    cam.rotation_euler = (0, 0, 0)
    sc = set_render(16, 1024, 1024)
    sc.camera = cam
    sc.render.filepath = OUT_TOP
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    for o in hidden:
        o.hide_render = False
    bpy.data.objects.remove(bpy.data.objects["PREVIEW_B_far_wall"], do_unlink=True)


def main_build():
    bkit.reset_scene()
    M = make_materials()
    ex, shell, colliders, markers = [], [], [], {}
    rng = random.Random(20260)
    build_shell(M, ex, shell)
    ex.extend(shell)

    # colliders for the shell (walls and office block the player)
    colliders += [
        [X0 - T / 2, 54.0, 3.65, T, Y1 - Y0, 7.3, 0],
        [X1 + T / 2, 54.0, 3.65, T, Y1 - Y0, 7.3, 0],
        [(-18.3 - 1.2) / 2, Y1 + T / 2, 3.65, 17.1, T, 7.3, 0],
        [(1.2 + 18.3) / 2, Y1 + T / 2, 3.65, 17.1, T, 7.3, 0],
        [0.0, Y1 + T / 2, (DOOR_H + CEIL + 0.3) / 2, 2 * DOOR_HALF, T, CEIL + 0.3 - DOOR_H, 0],
    ]
    ox0, ox1, oy0, oy1 = OFFICE
    colliders.append([(ox0 + ox1) / 2, (oy0 + oy1) / 2, 2.475, ox1 - ox0, oy1 - oy0, 4.95, 0])

    bolts = build_props(M, ex, colliders, markers, shell, rng)
    build_dressing(M, ex, shell, colliders, rng)
    n_props = sum(1 for o in ex if o.name.startswith(("C_sewing", "C_plush")))

    # preview-only lights (never exported; the GLB carries no lights)
    build_lights_preview(None)

    # markers
    markers["entry"] = [0.0, 35.0, 0.0]
    markers["exit"] = [0.0, 72.5, 0.0]
    markers["seamstress_spawn"] = [0.0, 54.0, RAIL_Z]
    markers["pickup_spool"] = [9.8, 57.5, 0.0]
    for k, (bx, by) in enumerate(bolts[:4]):
        markers[f"hide_{k + 1:02d}"] = [round(bx, 3), round(by + 0.6, 3), 0.0]
    for k in range(16):
        x, y = LOOP[int(k * len(LOOP) / 16)]
        markers[f"rail_{k:02d}"] = [round(x, 3), round(y, 3), RAIL_Z]

    lights = []
    for (x, y) in [(xx, yy) for yy in (43.0, 55.0, 67.0) for xx in (-6.0, 0.0, 6.0)]:
        if (x, y) in FIX_DEAD:
            continue
        lights.append({"pos": [x, y, 6.15], "color": "#dfe9ff", "intensity": 1.0, "range": 9,
                       "flicker": (x, y) in {(0.0, 55.0), (6.0, 55.0)}})
    for (x, y) in LAMPS:
        lights.append({"pos": [x, y, 2.15], "color": "#ffb46b", "intensity": 1.0, "range": 6,
                       "flicker": False})

    render_previews()

    # blend file (no backups), then the shipped GLB and JSON
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

    export_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("C_")]
    # shrink every texture to 512 px so the chunk stays small for the web (one image per map, shared)
    for im in bpy.data.images:
        if im.type == "IMAGE" and im.name not in ("Render Result", "Viewer Node") and max(im.size) > 512:
            w, h = im.size
            s = 512 / max(w, h)
            im.scale(max(1, int(w * s)), max(1, int(h * s)))
    bkit.export_glb(OUT_GLB, export_objs, image_format="JPEG")
    shell_tris = sum(bkit.tri_count(o) for o in export_objs if not o.name.startswith(("C_sewing", "C_plush")))
    prop_tris = sum(bkit.tri_count(o) for o in export_objs if o.name.startswith(("C_sewing", "C_plush")))
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump({"zone": "C", "colliders": colliders, "lights": lights, "markers": markers},
                  f, indent=1)
    print("ZC_REPORT shell_tris", shell_tris, "prop_instance_tris", prop_tris,
          "prop_instances", n_props, "glb_bytes", os.path.getsize(OUT_GLB),
          "colliders", len(colliders), "lights", len(lights), "markers", len(markers))


def main_verify():
    bkit.reset_scene()
    bpy.ops.import_scene.gltf(filepath=OUT_GLB)
    build_lights_preview(None)
    cam = eye_cam((0.0, 60.0, 1.6), (0.0, 74.0, 1.6))
    render_to(VERIFY_PNG, cam, 960, 540, 24)
    print("ZC_VERIFY ok", VERIFY_PNG)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "verify" in argv:
    main_verify()
else:
    main_build()
