"""Shared helpers for procedural creature modelling in Blender (bpy).

Conventions: Z is up, creatures face -Y (Blender "front" view).
"""
import bpy
import math
import os
import random
from mathutils import Vector

R = math.radians
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))


# ---------------------------------------------------------------- scene utils
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link_obj(o):
    bpy.context.collection.objects.link(o)
    return o


def select_only(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply_mods(o):
    """Bake the modifier stack into real geometry."""
    select_only(o)
    bpy.ops.object.convert(target="MESH")
    return o


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    e = link_obj(bpy.data.objects.new(name, None))
    e.parent = parent
    e.location = loc
    return e


def set_mat(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def setattrs(obj, **kw):
    for k, v in kw.items():
        try:
            setattr(obj, k, v)
        except Exception as ex:  # API drift between Blender versions
            print("setattr skipped", k, ex)


# ---------------------------------------------------------------- primitives
def prim(kind, name, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), m=None,
         parent=None, shade_smooth=True, **kw):
    ops = {
        "cube": (bpy.ops.mesh.primitive_cube_add, dict(size=1)),
        "sphere": (bpy.ops.mesh.primitive_uv_sphere_add, dict(segments=32, ring_count=16, radius=1)),
        "ico": (bpy.ops.mesh.primitive_ico_sphere_add, dict(subdivisions=3, radius=1)),
        "cyl": (bpy.ops.mesh.primitive_cylinder_add, dict(vertices=24, radius=1, depth=1)),
        "cone": (bpy.ops.mesh.primitive_cone_add, dict(vertices=24, radius1=1, radius2=0, depth=1)),
        "torus": (bpy.ops.mesh.primitive_torus_add, dict()),
    }
    fn, defaults = ops[kind]
    defaults = {**defaults, **kw}
    fn(location=(0, 0, 0), **defaults)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = rot
    o.parent = parent
    o.location = loc
    if m:
        set_mat(o, m)
    if shade_smooth:
        smooth(o)
    return o


def orient(o, a, b):
    d = Vector(b) - Vector(a)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    return o


def seg(name, a, b, r, m=None, parent=None, r2=None, verts=16):
    """Cylinder (or tapered cone when r2 is given) spanning a -> b."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    if r2 is None:
        o = prim("cyl", name, (a + b) / 2, (r, r, L), m=m, parent=parent, vertices=verts)
    else:
        o = prim("cone", name, (a + b) / 2, (1, 1, L), m=m, parent=parent,
                 vertices=verts, radius1=r, radius2=r2)
    return orient(o, a, b)


def bevel(o, width=0.01, segments=2):
    b = o.modifiers.new("Bevel", "BEVEL")
    b.width = width
    b.segments = segments
    return o


def subsurf(o, levels=2):
    s = o.modifiers.new("Sub", "SUBSURF")
    s.levels = levels
    s.render_levels = levels
    return o


def displace(o, strength=0.05, size=0.3, kind="CLOUDS", depth=2):
    tex = bpy.data.textures.new(o.name + "_tex", kind)
    try:
        tex.noise_scale = size
        tex.noise_depth = depth
    except Exception:
        pass
    d = o.modifiers.new("Disp", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.texture_coords = "OBJECT" if False else "LOCAL"
    return o


def boolean(o, cutter, op="DIFFERENCE"):
    mod = o.modifiers.new("Bool", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    apply_mods(o)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return o


# ---------------------------------------------------------------- skin bodies
class Skel:
    """Builds organic tube bodies with the Skin + Subdivision modifiers."""

    def __init__(self):
        self.v, self.e, self.r, self.roots = [], [], [], []

    def p(self, co, r):
        self.v.append(tuple(co))
        self.r.append(tuple(r) if isinstance(r, (tuple, list)) else (r, r))
        return len(self.v) - 1

    def chain(self, start, pts):
        """pts: [(co, radius), ...]. start: vertex index to attach to, or None."""
        prev = start
        for co, r in pts:
            i = self.p(co, r)
            if prev is None:
                self.roots.append(i)
            else:
                self.e.append((prev, i))
            prev = i
        return prev

    def build(self, name, m=None, subdiv=2, parent=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, self.e, [])
        me.update()
        o = link_obj(bpy.data.objects.new(name, me))
        o.parent = parent
        sk = o.modifiers.new("Skin", "SKIN")
        sk.use_smooth_shade = True
        layer = me.skin_vertices[0].data
        for i, r in enumerate(self.r):
            layer[i].radius = r
            layer[i].use_root = False
        for i in self.roots:
            layer[i].use_root = True
        if subdiv:
            subsurf(o, subdiv)
        if m:
            me.materials.append(m)
        return o


def lathe(name, profile, segments=48, m=None, parent=None):
    """Revolve [(radius, z), ...] around Z into an open tube (no caps)."""
    verts, faces = [], []
    n = len(profile)
    for i in range(segments):
        a = 2 * math.pi * i / segments
        for r, z in profile:
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(segments):
        j = (i + 1) % segments
        for k in range(n - 1):
            faces.append((i * n + k, j * n + k, j * n + k + 1, i * n + k + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = link_obj(bpy.data.objects.new(name, me))
    o.parent = parent
    if m:
        me.materials.append(m)
    return smooth(o)


# ---------------------------------------------------------------- hair
NO_HAIR = os.environ.get("NO_HAIR") == "1"


def density_group(o, points, inner, outer):
    """Vertex group that fades hair out near the given points (eyes, mouth...)."""
    g = o.vertex_groups.new(name="Density")
    pts = [Vector(p) for p in points]
    for v in o.data.vertices:
        d = min((v.co - p).length for p in pts) if pts else 99
        w = max(0.0, min(1.0, (d - inner) / max(1e-6, outer - inner)))
        g.add([v.index], w, "REPLACE")
    return g.name


def add_fur(o, mat_slot_name, count=6000, length=0.05, children=40, clump=0.6,
            rough=0.02, radius=0.0035, seed=1, density=None):
    if NO_HAIR:
        return None
    mod = o.modifiers.new("Fur", "PARTICLE_SYSTEM")
    ps = o.particle_systems[-1]
    ps.seed = seed
    if density:
        ps.vertex_group_density = density
    s = ps.settings
    s.type = "HAIR"
    s.count = count
    s.hair_length = length
    if mat_slot_name not in [m.name for m in o.data.materials if m]:
        raise RuntimeError("append hair material %s before add_fur" % mat_slot_name)
    setattrs(s, child_type="INTERPOLATED", rendered_child_count=children,
             child_percent=4, clump_factor=clump, clump_shape=0.3,
             roughness_1=rough, roughness_1_size=0.5, roughness_2=rough * 0.6,
             roughness_endpoint=rough * 0.5, root_radius=1.0, tip_radius=0.15,
             radius_scale=radius, display_step=3, render_step=4,
             use_hair_bspline=True, material_slot=mat_slot_name, child_length=0.85,
             child_length_threshold=0.2)
    return ps


# ---------------------------------------------------------------- materials
def _fac(node):
    for o in node.outputs:
        if o.type == "VALUE":
            return o
    return node.outputs[0]


def _col(node):
    for o in node.outputs:
        if o.type == "RGBA":
            return o
    return node.outputs[0]


class Mat:
    """Tiny node-graph builder around a Principled BSDF material."""

    def __init__(self, name):
        self.m = bpy.data.materials.new(name)
        self.nt = self.m.node_tree
        self.bsdf = self.nt.nodes["Principled BSDF"]
        self._tc = None

    def link(self, a, b):
        self.nt.links.new(a, b)

    def coord(self, kind="Object"):
        if not self._tc:
            self._tc = self.nt.nodes.new("ShaderNodeTexCoord")
        return self._tc.outputs[kind]

    def noise(self, scale, detail=8.0, rough=0.6, distortion=0.0, coord="Object"):
        n = self.nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        try:
            n.inputs["Distortion"].default_value = distortion
        except KeyError:
            pass
        self.link(self.coord(coord), n.inputs["Vector"])
        return _fac(n)

    def voronoi(self, scale, feature="DISTANCE_TO_EDGE", coord="Object"):
        v = self.nt.nodes.new("ShaderNodeTexVoronoi")
        v.feature = feature
        v.inputs["Scale"].default_value = scale
        self.link(self.coord(coord), v.inputs["Vector"])
        return v.outputs[0]

    def wave(self, scale, direction="Z", distortion=0.0, coord="Object"):
        w = self.nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.bands_direction = direction
        w.inputs["Scale"].default_value = scale
        w.inputs["Distortion"].default_value = distortion
        w.inputs["Detail"].default_value = 0.0
        self.link(self.coord(coord), w.inputs["Vector"])
        return _fac(w)

    def ramp(self, fac, stops, constant=False):
        r = self.nt.nodes.new("ShaderNodeValToRGB")
        cr = r.color_ramp
        if constant:
            cr.interpolation = "CONSTANT"
        els = cr.elements
        els[0].position = stops[0][0]
        els[0].color = (*_c(stops[0][1]), 1)
        els[1].position = stops[-1][0]
        els[1].color = (*_c(stops[-1][1]), 1)
        for pos, c in stops[1:-1]:
            e = els.new(pos)
            e.color = (*_c(c), 1)
        self.link(fac, r.inputs[0])
        return _col(r)

    def math(self, a, b, op="MULTIPLY"):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                self.link(v, n.inputs[i])
        return n.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = blend
        f = [i for i in n.inputs if i.name == "Factor" and i.type == "VALUE"][0]
        A = [i for i in n.inputs if i.name == "A" and i.type == "RGBA"][0]
        B = [i for i in n.inputs if i.name == "B" and i.type == "RGBA"][0]
        for sock, v in ((f, fac), (A, a), (B, b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*_c(v), 1)
            else:
                self.link(v, sock)
        return [o for o in n.outputs if o.type == "RGBA"][0]

    def bump(self, height, strength=0.3, distance=0.02):
        b = self.nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = distance
        self.link(height, b.inputs["Height"])
        self.link(b.outputs["Normal"], self.bsdf.inputs["Normal"])
        return b

    def set(self, **kw):
        names = {"color": "Base Color", "rough": "Roughness", "metal": "Metallic",
                 "sss": "Subsurface Weight", "sss_radius": "Subsurface Radius",
                 "sss_scale": "Subsurface Scale", "sheen": "Sheen Weight",
                 "sheen_tint": "Sheen Tint", "sheen_rough": "Sheen Roughness",
                 "coat": "Coat Weight", "coat_rough": "Coat Roughness",
                 "emit": "Emission Color", "emit_strength": "Emission Strength",
                 "spec": "Specular IOR Level"}
        for k, v in kw.items():
            sock = self.bsdf.inputs[names[k]]
            if hasattr(v, "is_linked") or hasattr(v, "node"):
                self.link(v, sock)
            elif isinstance(v, str):
                sock.default_value = (*_c(v), 1)
            elif isinstance(v, tuple) and len(v) == 3 and k in ("color", "emit", "sheen_tint"):
                sock.default_value = (*_c(v), 1)
            else:
                sock.default_value = v
        return self


def _c(v):
    """Accept '#rrggbb' (sRGB) or linear tuples."""
    if isinstance(v, str):
        h = v.lstrip("#")
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return tuple(((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb)
    return tuple(v)


# ---- material library -------------------------------------------------------
def mat_plush(name, base, dark, light, stain="#2a1a12", scale=2.5):
    """Old, dirty plush fabric."""
    M = Mat(name)
    n = M.noise(scale, 10, 0.65, distortion=0.4)
    col = M.ramp(n, [(0.25, dark), (0.5, base), (0.72, light)])
    grime = M.noise(scale * 0.6, 6, 0.5)
    grime_c = M.ramp(grime, [(0.55, "#ffffff"), (0.75, stain)])
    col = M.mix(0.85, col, grime_c, "MULTIPLY")
    M.set(color=col, rough=0.95, sheen=0.9, sheen_rough=0.4, sheen_tint=(1, 1, 1))
    M.bump(M.noise(180, 4, 0.7), 0.25, 0.01)
    return M.m


def mat_fur_hair(name, base, tip, variation):
    """Principled Hair BSDF for particle fur, varied per strand."""
    M = Mat(name)
    nt = M.nt
    out = nt.nodes["Material Output"]
    try:
        hair = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
        hair.parametrization = "COLOR"
        info = nt.nodes.new("ShaderNodeHairInfo")
        rnd = [o for o in info.outputs if o.name == "Random"][0]
        col = M.ramp(rnd, [(0.0, variation), (0.5, base), (1.0, tip)])
        stain = M.ramp(M.noise(1.8, 6, 0.6), [(0.55, "#ffffff"), (0.72, "#3a1c14")])
        col = M.mix(1.0, col, stain, "MULTIPLY")
        nt.links.new(col, hair.inputs["Color"])
        hair.inputs["Roughness"].default_value = 0.55
        hair.inputs["Radial Roughness"].default_value = 0.7
        hair.inputs["Coat"].default_value = 0.1
        nt.links.new(hair.outputs[0], out.inputs["Surface"])
    except Exception as ex:
        print("hair bsdf fallback", ex)
        M.set(color=_c(base), rough=0.8)
    return M.m


def mat_bone(name="Bone", tint="#c9bc98"):
    M = Mat(name)
    n = M.noise(9, 12, 0.7, distortion=0.3)
    col = M.ramp(n, [(0.2, "#2a2017"), (0.4, "#7a6a4c"), (0.58, tint), (0.85, "#ddd2b4")])
    grime = M.ramp(M.noise(3, 8, 0.6), [(0.35, "#ffffff"), (0.7, "#5a4632")])
    col = M.mix(1.0, col, grime, "MULTIPLY")
    M.set(color=col, rough=0.55, sss=0.08, sss_radius=(0.6, 0.4, 0.2), sss_scale=0.02)
    pits = M.voronoi(60, "F1")
    M.bump(M.math(M.noise(40, 8, 0.8), pits, "ADD"), 0.35, 0.01)
    return M.m


def mat_painted_wood(name, paint, trim="#7a1a14"):
    """Carousel paint, cracked and chipped down to grey wood."""
    M = Mat(name)
    chips = M.noise(5, 12, 0.7, distortion=0.6)
    cracks = M.voronoi(38, "DISTANCE_TO_EDGE")
    crack_mask = M.ramp(M.math(cracks, M.noise(9, 4, 0.6), "ADD"), [(0.42, "#1a1410"), (0.46, "#ffffff")])
    base = M.ramp(chips, [(0.0, "#2a2018"), (0.26, "#5d4a36"), (0.29, "#8c7a63"),
                          (0.31, paint), (0.85, paint)])
    dirt = M.ramp(M.noise(2, 5, 0.5), [(0.3, "#ffffff"), (0.75, "#4a3a2a")])
    streak = M.ramp(M.noise(1.5, 6, 0.6, coord="Object"), [(0.5, "#ffffff"), (0.7, "#6e5a44")])
    col = M.mix(1.0, base, dirt, "MULTIPLY")
    col = M.mix(1.0, col, streak, "MULTIPLY")
    col = M.mix(1.0, col, crack_mask, "MULTIPLY")
    M.set(color=col, rough=0.6, coat=0.25, coat_rough=0.35)
    M.bump(M.math(chips, cracks, "ADD"), 0.5, 0.01)
    return M.m


def mat_brass(name="AgedBrass", dark=False):
    M = Mat(name)
    n = M.noise(4, 12, 0.7, distortion=0.5)
    if dark:
        col = M.ramp(n, [(0.25, "#10180f"), (0.4, "#2a1f0e"), (0.6, "#5a4318"), (0.8, "#7a5a26")])
    else:
        col = M.ramp(n, [(0.25, "#2d4a3a"), (0.38, "#4a3a1c"), (0.5, "#9a7430"), (0.75, "#c79b48")])
    metal = M.ramp(n, [(0.32, "#000000"), (0.45, "#ffffff")])
    rough = M.ramp(M.noise(25, 6, 0.6), [(0.3, "#4d4d4d"), (0.7, "#a6a6a6")])
    M.set(color=col, metal=metal, rough=rough)
    M.bump(M.noise(60, 8, 0.7), 0.2, 0.01)
    return M.m


def mat_rust(name="RustIron"):
    M = Mat(name)
    n = M.noise(7, 12, 0.75, distortion=0.8)
    col = M.ramp(n, [(0.3, "#1c1410"), (0.45, "#5a2e15"), (0.6, "#8a4a22"), (0.75, "#3d3a38")])
    metal = M.ramp(n, [(0.6, "#000000"), (0.75, "#ffffff")])
    M.set(color=col, metal=metal, rough=0.8)
    M.bump(n, 0.6, 0.01)
    return M.m


def mat_flesh(name="Flesh", base="#5a1414", deep="#1e0508", hi="#9a4040", vein_scale=9, sss=0.35):
    M = Mat(name)
    n = M.noise(6, 10, 0.65, distortion=1.2)
    col = M.ramp(n, [(0.25, deep), (0.5, base), (0.75, hi)])
    veins = M.math(M.voronoi(vein_scale, "DISTANCE_TO_EDGE"), M.noise(14, 4, 0.5), "ADD")
    vmask = M.ramp(veins, [(0.4, "#2a0010"), (0.44, "#ffffff")])
    col = M.mix(1.0, col, vmask, "MULTIPLY")
    M.set(color=col, rough=0.35, sss=sss, sss_radius=(1.0, 0.25, 0.15), sss_scale=0.05,
          coat=0.4, coat_rough=0.15)
    M.bump(M.math(n, veins, "ADD"), 0.4, 0.02)
    return M.m


def mat_teeth(name="Teeth"):
    M = Mat(name)
    n = M.noise(14, 8, 0.6)
    col = M.ramp(n, [(0.3, "#6b5636"), (0.5, "#cbb98d"), (0.8, "#e8dfc4")])
    M.set(color=col, rough=0.3, sss=0.15, sss_radius=(0.8, 0.6, 0.4), sss_scale=0.01, coat=0.3)
    return M.m


def mat_eyeball(name="Eyeball"):
    M = Mat(name)
    veins = M.voronoi(18, "DISTANCE_TO_EDGE")
    v = M.ramp(veins, [(0.0, "#7a0a0a"), (0.05, "#e9e0d2")])
    blotch = M.ramp(M.noise(5, 6, 0.5), [(0.4, "#ffffff"), (0.8, "#e0a090")])
    M.set(color=M.mix(1.0, v, blotch, "MULTIPLY"), rough=0.08, sss=0.2,
          sss_radius=(1, 0.4, 0.3), sss_scale=0.01, coat=1.0, coat_rough=0.02)
    return M.m


def mat_simple(name, color, rough=0.5, metal=0.0, **kw):
    M = Mat(name)
    M.set(color=color, rough=rough, metal=metal, **kw)
    return M.m


def mat_stripes(name, a, b, scale=10.0, direction="Z", distortion=1.5):
    """Faded, dirty striped cloth (clown suits)."""
    M = Mat(name)
    w = M.wave(scale, direction, distortion=distortion)
    stripes = M.ramp(w, [(0.0, a), (0.5, b)], constant=True)
    dirt = M.ramp(M.noise(3, 8, 0.6), [(0.35, "#ffffff"), (0.7, "#5c4a3a")])
    col = M.mix(1.0, stripes, dirt, "MULTIPLY")
    M.set(color=col, rough=0.9, sheen=0.5, sheen_rough=0.5)
    M.bump(M.noise(90, 4, 0.7), 0.2, 0.01)
    return M.m


# ---------------------------------------------------------------- render stage
def setup_render(samples=128, res=(1600, 900)):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("GPU setup failed", ex)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass


def add_area(name, loc, target, energy, color=(1, 1, 1), size=2.0, spot=False):
    if spot:
        d = bpy.data.lights.new(name, "SPOT")
        d.spot_size = R(35)
        d.spot_blend = 0.6
        d.shadow_soft_size = 0.08
    else:
        d = bpy.data.lights.new(name, "AREA")
        d.size = size
    d.energy = energy
    d.color = color
    o = link_obj(bpy.data.objects.new(name, d))
    o.location = loc
    orient_to(o, target)
    return o


def orient_to(o, target):
    d = Vector(target) - Vector(o.location)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("-Z", "Y")


def stage(mood="horror"):
    """Concrete floor, dark world and light rig."""
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    bg = world.node_tree.nodes["Background"]
    if mood == "horror":
        bg.inputs["Color"].default_value = (0.004, 0.005, 0.009, 1)
        bg.inputs["Strength"].default_value = 1.0
    else:
        bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1)
        bg.inputs["Strength"].default_value = 1.0
    M = Mat("Concrete")
    n = M.noise(1.2, 12, 0.7)
    col = M.ramp(n, [(0.3, "#141210"), (0.55, "#3a3632"), (0.75, "#57524b")])
    puddle = M.ramp(M.noise(0.6, 3, 0.5), [(0.55, "#d0d0d0"), (0.62, "#1a1a1a")])
    M.set(color=col, rough=puddle)
    M.bump(M.voronoi(3, "DISTANCE_TO_EDGE"), 0.25, 0.02)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    set_mat(floor, M.m)
    return floor


def camera(loc, target, lens=40):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.dof.use_dof = False
    c = link_obj(bpy.data.objects.new("Cam", cd))
    c.location = loc
    orient_to(c, target)
    bpy.context.scene.camera = c
    return c


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


def save_blend(name):
    p = os.path.join(ROOT, "blender", "creatures", name + ".blend")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=p)
    print("SAVED", p)


def export_glb(name):
    p = os.path.join(ROOT, "public", "models", name + ".glb")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    hidden = []
    for o in bpy.data.objects:
        if o.type in ("LIGHT", "CAMERA") or o.name == "Floor":
            o.select_set(False)
            hidden.append(o)
    bpy.ops.object.select_all(action="SELECT")
    for o in hidden:
        o.select_set(False)
    bpy.ops.export_scene.gltf(filepath=p, export_format="GLB", export_apply=True,
                              use_selection=True, export_lights=False)
    print("EXPORTED", p)


def loft(name, path, sections, side=(1, 0, 0), segs=16, m=None, parent=None, cap=True):
    """Sweep elliptical cross-sections along a path.

    path: list of points; sections: list of (half_width_along_side, half_height, up_offset).
    The section plane is spanned by `side` and up = tangent x side.
    """
    side = Vector(side).normalized()
    pts = [Vector(p) for p in path]
    verts, faces = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        upv = t.cross(side).normalized()
        sd = upv.cross(t).normalized()
        w, h, off = sections[i]
        c = p + upv * off
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append(tuple(c + sd * (w * math.cos(a)) + upv * (h * math.sin(a))))
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((i * segs + k, i * segs + k2, (i + 1) * segs + k2, (i + 1) * segs + k))
    if cap:
        faces.append(tuple(reversed(range(segs))))
        faces.append(tuple((n - 1) * segs + k for k in range(segs)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.validate()
    o = link_obj(bpy.data.objects.new(name, me))
    o.parent = parent
    if m:
        me.materials.append(m)
    return smooth(o)
