"""Chapter 3, zone mirror: a dense walled mirror maze, one route from entry to relic_7.

Run from /Users/alex/恐怖遊戲2 with:
    python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py blender/map_ch3/zone_mirror_build.py <out_dir>

Coordinates follow blender/map_ch3/BRIEF.md: floor z=0, interior box x -40..40, y -112..-42,
ceiling z=5. Walls 0.3 m thick. The only door is north, at x=0 (y=-42), into a 3 m wide,
3.4 m high corridor x -1.5..1.5 running from y -41.85 to y -30.0, where it meets the hub wall.

Maze: 31 x 28 cells, cell pitch 2.58 m (x) and 2.5 m (y), so corridors are about 2.3 m wide.
Perfect maze (recursive backtracker) from the entry cell; the route to the farthest cell is the
only correct route and is checked to have at least 40 turns. Three secret doors are walls on the
route's edge that shortcut dead ends; they are separate objects so the game can reveal them.
"""
import sys, os, json, math, random
from collections import deque

sys.path.insert(0, "/Users/alex/.claude/skills/blender-modeling/scripts")
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import bkit

ROOT = "/Users/alex/恐怖遊戲2"
NAME = "zone_mirror"
OUT_GLB = f"{ROOT}/public/models/ch3/{NAME}.glb"
OUT_JSON = f"{ROOT}/public/models/ch3/{NAME}.json"
OUT_BLEND = f"{ROOT}/blender/bake/map_ch3/{NAME}.blend"
OUT_EYE = f"{ROOT}/renders/ch3_{NAME}_eye.png"
OUT_TOP = f"{ROOT}/renders/ch3_{NAME}_top.png"
SCRATCH = "/private/tmp/claude-504/-Users-alex-----2/df819384-06df-4249-8523-a5c0f94e5679/scratchpad/mz"
PREVIEW_ONLY = "--no-preview" not in sys.argv

# ------------------------------------------------------------------ constants
X_MIN, X_MAX, Y_MIN, Y_MAX, CEIL = -40.0, 40.0, -112.0, -42.0, 5.0
W, H = 31, 28
PX = (X_MAX - X_MIN) / W        # 2.5806 m
PY = (Y_MAX - Y_MIN) / H        # 2.5 m
WALL_T = 0.3
ENTRY = (15, H - 1)              # column at x=0, top row next to the north door


def XL(c):
    return X_MIN + c * PX        # grid line x


def YL(r):
    return Y_MIN + r * PY        # grid line y


def XC(c):
    return X_MIN + (c + 0.5) * PX


def YC(r):
    return Y_MIN + (r + 0.5) * PY


# ------------------------------------------------------------------ maze generation
def gen_maze(seed):
    r = random.Random(seed)
    V = [[True] * H for _ in range(W + 1)]      # V[c][row]: line x=XL(c) between cells c-1 and c
    Hw = [[True] * W for _ in range(H + 1)]     # Hw[row][c]: line y=YL(row) between rows row-1 and row
    visited = [[False] * H for _ in range(W)]
    stack = [ENTRY]
    visited[ENTRY[0]][ENTRY[1]] = True
    while stack:
        c, rr = stack[-1]
        nbrs = []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, rr + dr
            if 0 <= nc < W and 0 <= nr < H and not visited[nc][nr]:
                nbrs.append((nc, nr, dc, dr))
        if not nbrs:
            stack.pop()
            continue
        nc, nr, dc, dr = r.choice(nbrs)
        if dc == 1:
            V[c + 1][rr] = False
        elif dc == -1:
            V[c][rr] = False
        elif dr == 1:
            Hw[rr + 1][c] = False
        else:
            Hw[rr][c] = False
        visited[nc][nr] = True
        stack.append((nc, nr))
    Hw[H][ENTRY[0]] = False                    # the north door opening
    return V, Hw


def neighbours(V, Hw, cell):
    c, rr = cell
    out = []
    if c + 1 < W and not V[c + 1][rr]:
        out.append((c + 1, rr))
    if c - 1 >= 0 and not V[c][rr]:
        out.append((c - 1, rr))
    if rr + 1 < H and not Hw[rr + 1][c]:
        out.append((c, rr + 1))
    if rr - 1 >= 0 and not Hw[rr][c]:
        out.append((c, rr - 1))
    return out


def bfs(V, Hw, start):
    dist = {start: 0}
    par = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        for nb in neighbours(V, Hw, cur):
            if nb not in dist:
                dist[nb] = dist[cur] + 1
                par[nb] = cur
                q.append(nb)
    return dist, par


def turns_of(path):
    n = 0
    for a, b, c in zip(path, path[1:], path[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            n += 1
    return n


def find_route():
    for seed in range(1, 400):
        V, Hw = gen_maze(seed)
        dist, par = bfs(V, Hw, ENTRY)
        goal = max(dist, key=lambda k: dist[k])
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = par[cur]
        path.reverse()
        t = turns_of(path)
        if t >= 40 and len(path) >= 150:
            return seed, V, Hw, dist, path
    raise RuntimeError("no maze with 40+ turns found")


SEED, V, Hw, DIST, ROUTE = find_route()
ROUTE_SET = set(ROUTE)
GOAL = ROUTE[-1]
print(f"MAZE seed={SEED} route_cells={len(ROUTE)} turns={turns_of(ROUTE)} goal={GOAL}")

# ------------------------------------------------------------------ secret doors
# present walls between a route cell and an off-route cell: the off-route side is a branch,
# so opening that wall gives a shortcut. Pick three spread along the route.
def secret_candidates():
    out = []
    for idx, cell in enumerate(ROUTE):
        c, rr = cell
        if idx < 10 or idx > len(ROUTE) - 10:
            continue
        for (nc, nr), kind, line, k in (
            ((c + 1, rr), "v", c + 1, rr), ((c - 1, rr), "v", c, rr),
            ((c, rr + 1), "h", rr + 1, c), ((c, rr - 1), "h", rr, c),
        ):
            if not (0 <= nc < W and 0 <= nr < H):
                continue
            if (nc, nr) in ROUTE_SET:
                continue
            wall_present = V[line][k] if kind == "v" else Hw[line][k]
            if wall_present:
                out.append((idx, kind, line, k))
    return out


cands = secret_candidates()
SECRETS = []
for frac in (0.25, 0.5, 0.75):
    target = int(frac * len(ROUTE))
    best = min(cands, key=lambda t: abs(t[0] - target))
    cands = [t for t in cands if abs(t[0] - best[0]) > 12]
    SECRETS.append(best)
SECRET_KEYS = {(kind, line, k) for (_, kind, line, k) in SECRETS}


def wall_centre(kind, line, k):
    if kind == "v":
        return (XL(line), YC(k), 0.0)
    return (XC(k), YL(line), 0.0)


# ------------------------------------------------------------------ helpers
class Group:
    def __init__(self):
        self.items = []

    def box(self, c, s, rot=(0.0, 0.0, 0.0), mat=0):
        R = Euler(rot).to_matrix().to_4x4()
        M = Matrix.Translation(c) @ R @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        self.items.append(("box", mat, M, None))

    def cyl(self, c, r, d, rot=(0.0, 0.0, 0.0), mat=0, segs=14):
        R = Euler(rot).to_matrix().to_4x4()
        self.items.append(("cyl", mat, Matrix.Translation(c) @ R, (r, d, segs)))

    def build(self, name, mats, uv=None):
        bm = bmesh.new()
        for kind, mat, M, extra in self.items:
            before = set(bm.faces)
            if kind == "box":
                bmesh.ops.create_cube(bm, size=1.0, matrix=M)
            else:
                r, d, segs = extra
                bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                      radius1=r, radius2=r, depth=d, matrix=M)
            for f in set(bm.faces) - before:
                f.material_index = mat
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        if uv:
            bkit.box_uv(obj, size=uv)
        return obj


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def pbr(name, tid):
    return bkit.pbr_material(name, bkit.polyhaven_texture(tid, res="1k"))


def proc(name, base, **kw):
    return bkit.procedural_material(name, base, **kw)


# ------------------------------------------------------------------ materials
bpy.context.preferences.filepaths.save_version = 0
bkit.reset_scene()
os.makedirs(SCRATCH, exist_ok=True)

M_FLOOR = pbr("U_concrete_floor", "concrete_floor_worn_001")
M_WALL = pbr("U_painted_wall", "peeling_painted_wall")
M_CEIL = pbr("U_dirty_ceiling", "dirty_concrete")

# mirrors: metallic, dark and tarnished; the cracked ones are rougher and darker
DRESS_MATS = [
    proc("U_mirror_tarnished", (0.82, 0.84, 0.80), variation=0.08, roughness=0.05, metallic=1.0,
         scale=2.0, bump=0.04, grime=0.35),
    proc("U_mirror_cracked", (0.48, 0.50, 0.46), variation=0.15, roughness=0.22, metallic=1.0,
         scale=3.0, bump=0.35, grime=0.6),
    proc("U_pedestal", (0.20, 0.17, 0.14), variation=0.12, roughness=0.7, scale=4.0, bump=0.2, grime=0.4),
    proc("U_fixture", (0.12, 0.12, 0.12), variation=0.1, roughness=0.6, scale=4.0, bump=0.1, grime=0.3),
    proc("U_puddle", (0.05, 0.06, 0.07), variation=0.1, roughness=0.04, scale=2.0, bump=0.0, grime=0.0),
    proc("U_paper", (0.55, 0.52, 0.46), variation=0.1, roughness=0.9, scale=8.0, bump=0.05, grime=0.5),
    proc("U_frame_carnival", (0.45, 0.10, 0.07), variation=0.15, roughness=0.6, scale=4.0, bump=0.2, grime=0.5),
    proc("U_bulb", (0.85, 0.62, 0.30), variation=0.05, roughness=0.3, scale=4.0, bump=0.0, grime=0.0),
]
MIR, CRK, PED, FIX, PUD, PAP, FRAME, BULB = range(8)

# ------------------------------------------------------------------ shell and maze geometry
floor = Group()
ceil_g = Group()
maze = Group()
corr = Group()
secret_objs = []
dr = Group()
COLLIDERS = []

floor.box(((X_MIN + X_MAX) / 2, (Y_MIN + Y_MAX) / 2, -0.15),
          (X_MAX - X_MIN + 2 * WALL_T / 2 + 0.3, Y_MAX - Y_MIN + 0.3, 0.3))
ceil_g.box(((X_MIN + X_MAX) / 2, (Y_MIN + Y_MAX) / 2, CEIL + 0.15),
           (X_MAX - X_MIN + 0.3, Y_MAX - Y_MIN + 0.3, 0.3))


def runs(flags):
    out, a = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and a is None:
            a = i
        if not f and a is not None:
            out.append((a, i - 1))
            a = None
    return out


def wall_box(g, x0, x1, y0, y1, z0, z1, mat=0):
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat=mat)


def collider(x0, x1, y0, y1, z0, z1):
    COLLIDERS.append([round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4), round((z0 + z1) / 2, 4),
                      round(x1 - x0, 4), round(y1 - y0, 4), round(z1 - z0, 4), 0.0])


# horizontal wall lines (grid rows 0..H): runs of present segments, minus secrets
for rr in range(H + 1):
    flags = [Hw[rr][c] and ("h", rr, c) not in SECRET_KEYS for c in range(W)]
    for a, b in runs(flags):
        x0, x1, y = XL(a), XL(b + 1), YL(rr)
        wall_box(maze, x0, x1, y - WALL_T / 2, y + WALL_T / 2, 0.0, CEIL)
        collider(x0, x1, y - WALL_T / 2, y + WALL_T / 2, 0.0, CEIL)

# vertical wall lines (grid columns 0..W)
for c in range(W + 1):
    flags = [V[c][rr] and ("v", c, rr) not in SECRET_KEYS for rr in range(H)]
    for a, b in runs(flags):
        y0, y1, x = YL(a), YL(b + 1), XL(c)
        wall_box(maze, x - WALL_T / 2, x + WALL_T / 2, y0, y1, 0.0, CEIL)
        collider(x - WALL_T / 2, x + WALL_T / 2, y0, y1, 0.0, CEIL)

# lintel over the north door (the opening itself is the removed wall segment)
ex = XC(ENTRY[0])
wall_box(maze, ex - PX / 2, ex + PX / 2, YL(H) - WALL_T / 2, YL(H) + WALL_T / 2, 3.0, CEIL)

# secret doors: each its own object, solid until revealed
for k, (idx, kind, line, kk) in enumerate(SECRETS, start=1):
    g = Group()
    if kind == "v":
        wall_box(g, XL(line) - WALL_T / 2, XL(line) + WALL_T / 2, YL(kk), YL(kk + 1), 0.0, CEIL)
        collider(XL(line) - WALL_T / 2, XL(line) + WALL_T / 2, YL(kk), YL(kk + 1), 0.0, CEIL)
    else:
        wall_box(g, XL(kk), XL(kk + 1), YL(line) - WALL_T / 2, YL(line) + WALL_T / 2, 0.0, CEIL)
        collider(XL(kk), XL(kk + 1), YL(line) - WALL_T / 2, YL(line) + WALL_T / 2, 0.0, CEIL)
    secret_objs.append(g.build(f"U_secret_door_{k}", [M_WALL], uv=2.5))

# north corridor: 3 m wide, 3.4 m high, from the maze wall to the hub wall at y=-30
CY0, CY1 = Y_MAX - 0.15, -30.0
wall_box(corr, -1.8, -1.5, CY0, CY1, 0.0, 3.4)
wall_box(corr, 1.5, 1.8, CY0, CY1, 0.0, 3.4)
collider(-1.8, -1.5, CY0, CY1, 0.0, 3.4)
collider(1.5, 1.8, CY0, CY1, 0.0, 3.4)
wall_box(corr, -1.5, 1.5, CY0, CY1, 3.4, 3.7)           # corridor ceiling
corr_floor = Group()
wall_box(corr_floor, -1.5, 1.5, CY0, CY1, -0.3, 0.0)

# mirror panels on wall faces: tall, one side per wall, some cracked
rng = random.Random(77)
panel_list = []
for rr in range(H + 1):
    for c in range(W):
        if ("h", rr, c) in SECRET_KEYS or not Hw[rr][c]:
            continue
        if rng.random() > 0.38:
            continue
        sides = []
        if rr < H:
            sides.append(+1)
        if rr > 0:
            sides.append(-1)
        if not sides:
            continue
        s = rng.choice(sides)
        panel_list.append(("h", XC(c), YL(rr) + s * (WALL_T / 2 + 0.016), PX * 0.82,
                           CRK if rng.random() < 0.18 else MIR, 0.0))
for c in range(W + 1):
    for rr in range(H):
        if ("v", c, rr) in SECRET_KEYS or not V[c][rr]:
            continue
        if rng.random() > 0.38:
            continue
        sides = []
        if c < W:
            sides.append(+1)
        if c > 0:
            sides.append(-1)
        s = rng.choice(sides)
        panel_list.append(("v", XL(c) + s * (WALL_T / 2 + 0.016), YC(rr), PY * 0.82,
                           CRK if rng.random() < 0.18 else MIR, 0.0))
for kind, a, b, length, mat, _ in panel_list:
    if kind == "h":
        dr.box((a, b, 2.45), (length, 0.03, 4.0), mat=mat)
    else:
        dr.box((a, b, 2.45), (0.03, length, 4.0), mat=mat)
    # dusty carnival frame on most panels: top and bottom bars, two stiles
    if rng.random() < 0.6:
        if kind == "h":
            dr.box((a, b, 4.48), (length + 0.24, 0.05, 0.14), mat=FRAME)
            dr.box((a, b, 0.42), (length + 0.24, 0.05, 0.14), mat=FRAME)
            dr.box((a - length / 2 - 0.07, b, 2.45), (0.14, 0.05, 4.0), mat=FRAME)
            dr.box((a + length / 2 + 0.07, b, 2.45), (0.14, 0.05, 4.0), mat=FRAME)
        else:
            dr.box((a, b, 4.48), (0.05, length + 0.24, 0.14), mat=FRAME)
            dr.box((a, b, 0.42), (0.05, length + 0.24, 0.14), mat=FRAME)
            dr.box((a, b - length / 2 - 0.07, 2.45), (0.05, 0.14, 4.0), mat=FRAME)
            dr.box((a, b + length / 2 + 0.07, 2.45), (0.05, 0.14, 4.0), mat=FRAME)

# dim bulbs in cages on the walls, one per few corridors
for f in (1 / 9, 3 / 9, 5 / 9, 7 / 9):
    cell = ROUTE[int(f * (len(ROUTE) - 1))]
    x, y = XC(cell[0]), YC(cell[1])
    dr.box((x + PX * 0.42, y, 1.2), (0.06, 0.14, 0.14), mat=BULB)

# route markers: pedestals for relic_7 and claw_flash, lamps, patrols
def route_cell(frac):
    return ROUTE[min(len(ROUTE) - 1, max(0, int(frac * (len(ROUTE) - 1))))]


CLAW_CELL = route_cell(0.30)
LAMP_CELLS = [route_cell(f) for f in (1 / 9, 2 / 9, 3 / 9, 4 / 9, 5 / 9, 6 / 9, 7 / 9, 8 / 9)]
PATROL_CELLS = [route_cell(f) for f in (0.2, 0.4, 0.6, 0.8)]
off_route = [c for c in DIST if c not in ROUTE_SET]
FLICKER_CELL = max(off_route, key=lambda k: DIST[k])


def pedestal(cell, pedestal_mat=PED):
    x, y = XC(cell[0]), YC(cell[1])
    dr.box((x, y, 0.45), (0.5, 0.5, 0.9), mat=pedestal_mat)
    collider(x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0.0, 0.9)


pedestal(GOAL)                 # relic_7 on top
pedestal(CLAW_CELL)            # claw_flash on top
for cell in LAMP_CELLS:        # ceiling fixture under each lamp point
    x, y = XC(cell[0]), YC(cell[1])
    dr.box((x, y, 4.88), (0.6, 0.3, 0.12), mat=FIX)

# floor dressing: puddles, paper and a few mirror shards
for _ in range(14):
    c = rng.randrange(W)
    rr = rng.randrange(H)
    x, y = XC(c) + rng.uniform(-0.6, 0.6), YC(rr) + rng.uniform(-0.6, 0.6)
    dr.cyl((x, y, 0.0), rng.uniform(0.3, 0.7), 0.004, mat=PUD, segs=14)
for _ in range(20):
    c = rng.randrange(W)
    rr = rng.randrange(H)
    x, y = XC(c) + rng.uniform(-0.8, 0.8), YC(rr) + rng.uniform(-0.8, 0.8)
    dr.box((x, y, 0.002), (0.21, 0.297, 0.002), rot=(0, 0, rng.uniform(0, 3.14)), mat=PAP)
for _ in range(16):
    c = rng.randrange(W)
    rr = rng.randrange(H)
    x, y = XC(c) + rng.uniform(-0.7, 0.7), YC(rr) + rng.uniform(-0.7, 0.7)
    dr.box((x, y, 0.01), (rng.uniform(0.12, 0.3), rng.uniform(0.08, 0.2), 0.02),
           rot=(0, 0, rng.uniform(0, 3.14)), mat=MIR if rng.random() < 0.5 else CRK)

# ------------------------------------------------------------------ build meshes
F_OBJ = floor.build("U_floor", [M_FLOOR], uv=2.5)
C_OBJ = ceil_g.build("U_ceiling", [M_CEIL], uv=2.5)
MAZE_OBJ = maze.build("U_maze_walls", [M_WALL], uv=2.5)
CORR_OBJ = corr.build("U_corridor", [M_WALL], uv=2.5)
CFLOOR_OBJ = corr_floor.build("U_corridor_floor", [M_FLOOR], uv=2.5)
DRESS_OBJ = dr.build("U_dressing", DRESS_MATS)

# bake the procedural dressing (mirrors, pedestals, puddles) to one 512 set
bkit.bake_to_textures(DRESS_OBJ, SCRATCH, size=512, samples=16)
for im in bpy.data.images:
    if im.name.startswith("U_dressing") and im.filepath:
        try:
            im.pack()
        except Exception:
            pass

# ------------------------------------------------------------------ markers and lights
def cell_xyz(cell, z=0.0):
    return [round(XC(cell[0]), 4), round(YC(cell[1]), 4), z]


MARKERS = {
    "claw_flash": cell_xyz(CLAW_CELL, 0.95),
    "flicker_spawn": cell_xyz(FLICKER_CELL, 0.0),
    "relic_7": cell_xyz(GOAL, 0.95),
}
for k, (idx, kind, line, kk) in enumerate(SECRETS, start=1):
    x, y, z = wall_centre(kind, line, kk)
    MARKERS[f"secret_{k}"] = [round(x, 4), round(y, 4), z]
for k, cell in enumerate(LAMP_CELLS, start=1):
    MARKERS[f"lamp_{k}"] = cell_xyz(cell, 4.6)
for k, cell in enumerate(PATROL_CELLS, start=1):
    MARKERS[f"ticket_patrol_{k}"] = cell_xyz(cell, 0.0)

LIGHTS = []
for k, cell in enumerate(LAMP_CELLS):
    flick = k % 3 == 1
    LIGHTS.append(((XC(cell[0]), YC(cell[1]), 4.6), "#c9d6d0", 0.55 if flick else 0.8, 9.0, flick))
LIGHTS.append(((0.0, -36.0, 3.0), "#ffb070", 0.6, 6.0, True))   # warm bulb in the north corridor
JSON_LIGHTS = [{"pos": list(p), "color": c, "intensity": i, "range": r, "flicker": f}
               for p, c, i, r, f in LIGHTS]

# ------------------------------------------------------------------ export
for im in bpy.data.images:
    if im.name in ("Render Result", "Viewer Node"):
        continue
    if im.size[0] > 512 or im.size[1] > 512:
        im.scale(512, 512)
zone_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
tris_total = sum(bkit.tri_count(o) for o in zone_meshes)
print(f"MIRROR_TRIS total={tris_total} objects={len(zone_meshes)} panels={len(panel_list)}")

os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
bkit.export_glb(OUT_GLB, objs=zone_meshes, image_format="JPEG")
print("MIRROR_GLB", OUT_GLB, os.path.getsize(OUT_GLB))

data = {
    "zone": "mirror",
    "colliders": [[round(v, 4) for v in c] for c in COLLIDERS],
    "lights": JSON_LIGHTS,
    "markers": MARKERS,
}
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
print("MIRROR_JSON", OUT_JSON, len(COLLIDERS), "colliders")

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

# ------------------------------------------------------------------ preview lights (not exported)
world = bpy.data.worlds.new("U_preview_world")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.16, 0.17, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
for i, (pos, color, inten, rng_, flick) in enumerate(LIGHTS):
    ld = bpy.data.lights.new(f"U_prev_point_{i}", type="POINT")
    ld.energy = 240.0 * inten
    ld.shadow_soft_size = 0.2
    ld.color = hex_rgb(color)
    lo = bpy.data.objects.new(ld.name, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = pos
# preview-only fill: the maze is closed, so the world light cannot reach inside.
# Four soft panels just under the ceiling stand in for the room's general glow.
for i, (fx, fy) in enumerate([(a, b) for a in (-26.0, 0.0, 26.0) for b in (-101.0, -77.0, -53.0)]):
    fd = bpy.data.lights.new(f"U_prev_fill_{i}", type="AREA")
    fd.size = 9.0
    fd.size_y = 9.0
    fd.energy = 900.0
    fd.color = (0.9, 0.85, 0.8)
    fo = bpy.data.objects.new(fd.name, fd)
    bpy.context.scene.collection.objects.link(fo)
    fo.location = (fx, fy, 4.9)


# ------------------------------------------------------------------ previews
def eye_camera(name, pos, target):
    cd = bpy.data.cameras.new(name)
    cd.lens = 26
    cd.sensor_width = 36
    cd.clip_end = 200
    co = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = pos
    d = Vector(target) - Vector(pos)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return co


def still(path, cam, w, h, samples):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_eye_sheet(path, views, size=512, samples=16):
    tiles = []
    for i, (label, pos, target) in enumerate(views):
        cam = eye_camera(f"U_eye_{i}", pos, target)
        tmp = os.path.join(SCRATCH, f"eye_{i}.png")
        still(tmp, cam, size, size, samples)
        im = bpy.data.images.load(tmp, check_existing=False)
        tiles.append(np.array(im.pixels[:]).reshape(size, size, 4))
        bpy.data.images.remove(im)
        os.remove(tmp)
        bpy.data.objects.remove(cam)
    while len(tiles) < 4:
        tiles.append(np.ones((size, size, 4)))
    sheet = np.vstack([np.hstack(tiles[2:4]), np.hstack(tiles[0:2])])
    out = bpy.data.images.new("mz_sheet", size * 2, size * 2, alpha=False)
    out.pixels = sheet.ravel()
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def render_top(path, size=720, samples=12):
    ceil_obj = bpy.data.objects.get("U_ceiling")
    ceil_obj.hide_render = True
    cd = bpy.data.cameras.new("U_top")
    cd.type = "ORTHO"
    cd.ortho_scale = 84.0
    cd.clip_end = 100
    co = bpy.data.objects.new("U_top", cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = (0.0, -77.0, 60.0)
    co.rotation_euler = (0.0, 0.0, 0.0)
    still(path, co, size, size, samples)
    bpy.data.objects.remove(co)
    ceil_obj.hide_render = False


if PREVIEW_ONLY:
    # a cell two steps before the route midpoint, looking down the route
    mid = ROUTE[len(ROUTE) // 2]
    nxt = ROUTE[len(ROUTE) // 2 + 2]
    prev_cell = ROUTE[max(0, len(ROUTE) // 2 - 2)]
    sec_idx, sk, sl, sn = SECRETS[0]
    sx, sy, sz = wall_centre(sk, sl, sn)
    sec_route = ROUTE[sec_idx]
    views = [
        ("north door", (0.0, -43.6, 1.6), (0.0, -38.0, 1.6)),
        ("route corridor", (XC(prev_cell[0]), YC(prev_cell[1]), 1.6),
         (XC(nxt[0]), YC(nxt[1]), 1.6)),
        ("secret door", (XC(sec_route[0]), YC(sec_route[1]), 1.6), (sx, sy, 1.6)),
        ("goal pedestal", (XC(ROUTE[-2][0]), YC(ROUTE[-2][1]), 1.6),
         (XC(GOAL[0]), YC(GOAL[1]), 1.0)),
    ]
    for label, pos, target in views:
        print("BKIT_VIEW", label, [round(v, 3) for v in pos], [round(v, 3) for v in target])
    # preview only: with the ceiling off, the world light reaches inside the closed maze
    bpy.data.objects.get("U_ceiling").hide_render = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.3, 0.3, 0.31, 1)
    render_eye_sheet(OUT_EYE, views)
    print("MIRROR_EYE", OUT_EYE)
    render_top(OUT_TOP)
    print("MIRROR_TOP", OUT_TOP)

bkit.check(objs=zone_meshes, max_tris=60000, ground=False)
bkit.report(zone_meshes)
