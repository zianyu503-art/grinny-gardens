# Chapter 3 map brief (for zone-building subagents)

Game: 微笑樂園, a first-person web horror game (Three.js, browser and iPad). Story and claws:
`blender/ghosts/CHAPTER3.md`. Abandoned since 1996: dust, rust, water damage, peeling paint. Cold,
sad, creepy, never cartoonish. The player walks (eye height 1.6 m, radius 0.35 m, cannot jump).
Each zone is built by one agent.

## How to build
Invoke the blender-modeling skill with the Skill tool (or read
`/Users/alex/.claude/skills/blender-modeling/SKILL.md`, `references/maps.md`, `references/recipes.md`
and `references/realism-checklist.md`). Run builds through its `scripts/run.py`, headless, from
`/Users/alex/恐怖遊戲2`. Worked examples to copy from: `blender/map_ch2/zone_d_packing_build.py`
and `zone_e_warehouse_build.py`. Other agents run Blender at the same time and this machine has
killed jobs for memory before, so keep previews small (samples 16-24, 640x480), keep scenes lean,
and retry if a job dies with exit 137.

## Coordinates (must match exactly, or zones won't connect)
Blender metres, Z up, floor z = 0, single level. Game maps (x, y, z) to Three.js (x, z, -y).
Walls 0.3 m thick, built outward from the interior box.

| Zone | File name | Interior box (x, y) | Ceiling | Connects by |
|---|---|---|---|---|
| Lost & Found hub | `zone_hub` | x -30..30, y -30..30 | 9 | door on all four sides at the side's centre |
| Bumper car arena | `zone_bumper` | x -40..40, y 42..122 | 12 | south door to hub via corridor |
| Coaster repair tower | `zone_tower` | x 42..112, y -35..35 | 22 | west door to hub via corridor; north door to power plant |
| Mirror maze | `zone_mirror` | x -40..40, y -112..-42 | 5 | north door to hub via corridor |
| Broadcast station | `zone_radio` | x -102..-42, y -30..30 | 8 | east door to hub via corridor |
| Power plant and cable maze | `zone_power` | x 42..122, y 45..125 | 10 | south door from tower via corridor |

Corridors: each outer zone builds its own corridor, 12 m long, 3 m wide, 3.4 m high, centred on the
door line, running from its own wall to the neighbouring zone's wall so that it ends flush against
it (bumper y 30..42 at x=0; tower x 30..42 at y=0; mirror y -42..-30 at x=0; radio x -42..-30 at y=0;
power y 35..45 at x=77). The hub builds a 3 m wide, 3 m high doorway at each side centre. The tower
builds its north doorway at x=77 (y=35).

## Zones
- **hub**: an enormous dusty archive. Tall steel shelves in aisles (2.5 m+ wide) holding thousands of
  labelled shoe boxes, tagged lost shoes, backpacks, teddy bears, tiny raincoats, numbered tags on
  string. A central counter with an old bell, ledgers and a pigeon-hole wall. Markers: `spawn`,
  `claw_scissors` (on the counter), `save` (counter), `relic_1`, `relic_2`.
- **bumper**: a big rusted arena with a sagging ceiling grid, dead cars pushed into piles, a raised
  operator booth. Heavy iron shutter blocks the way on, opened only by magnet. Markers:
  `claw_magnet`, `magnet_gate_1`, `magnet_crate_1..3` (heavy iron crates in the way),
  `relic_3`, `relic_4`, `ticket_patrol_1..6`.
- **tower**: a huge steel service tower hall holding a stripped coaster car on jacks. Deep repair
  pit that cuts the room in two, crossed only by grappling: anchors are large steel rings on beams.
  Markers: `claw_grapple`, `anchor_1..4`, `pit_a`, `pit_b` (each side of the pit), `relic_5`,
  `relic_6`, `ticket_patrol_1..6`. Colliders must block the pit edges.
- **mirror**: a dense walled maze (corridors 1.5-2.5 m wide) with tall tarnished mirrors, some
  cracked, dark, low ceiling. Build a real maze, at least 40 turns, one correct route. Secret doors
  shown only by flash. Markers: `claw_flash`, `secret_1..3`, `flicker_spawn`, `lamp_1..8`,
  `relic_7`, `ticket_patrol_1..4`.
- **radio**: a two-room radio station: studio with mixing desk, reel-to-reel recorders, foam walls,
  on-air sign, record shelves, and a transmitter hall. Cracked walls that only the horn claw breaks.
  Markers: `claw_horn`, `crack_1..3` (with hidden rooms behind), `tape_reveal`, `relic_8`,
  `ticket_patrol_1..4`.
- **power**: transformer hall with giant ceramic insulators, then a large electric maze of
  caged corridors (1.8 m wide) lined with cable trays, breaker panels and warning signs. Three
  circuits to connect. Markers: `claw_charge`, `node_1..6`, `breaker_1..3`, `flicker_arena`,
  `finale_door`, `relic_9`, `ticket_patrol_1..6`.

All zones: concrete with stains and puddles, peeling walls, ceilings with beams, ducts and cable
trays, mostly dead lights, debris, 1990s signs. No large bare surfaces.

## Outputs (exactly)
- Script: `blender/map_ch3/<name>_build.py`
- Chunk: `public/models/ch3/<name>.glb` (under 5 MB, JPEG 512 textures, shared materials, linked
  instances for repeats; `blender/map_ch2/shrink_glb.py` can shrink it)
- Data: `public/models/ch3/<name>.json` with `{"zone", "colliders": [[cx, cy, cz, sx, sy, sz, rotZ]...],
  "lights": [{"pos", "color", "intensity", "range", "flicker"}], "markers": {"name": [x, y, z]}}`
- Saved scene: `blender/bake/map_ch3/<name>.blend`
- Previews: `renders/ch3_<name>_eye.png` (2-4 eye-height views incl. each doorway),
  `renders/ch3_<name>_top.png` (top view, ceiling hidden)

Lessons: glTF imports use quaternions (set `rotation_mode = "XYZ"` before `rotation_euler`); do not
bake big shell surfaces, use tiling Poly Haven textures with `box_uv`; tris up to 60k per zone
excluding instanced props. Touch no other files. Do not run git or edit `src/`.

## Report back (short)
Paths, tris, GLB size, door positions, markers, what you checked, what still looks wrong.
