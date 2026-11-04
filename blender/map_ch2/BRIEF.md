# Chapter 2 map brief (for zone-building subagents)

Game: 微笑樂園 (Grinny Gardens), a first-person web horror game (Three.js, browser and iPad).
Chapter 2 is the underground toy factory beneath the park, abandoned since the park closed
overnight in 1996: ~30 years of dust, rust, water damage, peeling paint, mould, debris.
Mood: cold, dim, sad and creepy, never cartoonish. The player walks through on foot (eye height
1.6 m, collision radius 0.35 m, cannot jump or climb). The level is one linear route made of
6 zones; you build exactly one zone.

## How to build (blender-modeling skill)
1. Read `/Users/alex/.claude/skills/blender-modeling/SKILL.md`, then in the same folder
   `references/maps.md`, `references/recipes.md` and `references/realism-checklist.md`.
   Read the docstrings in `scripts/bkit.py` and use it (Poly Haven textures, `pbr_material`,
   `box_uv`, `harden`, `import_glb`, `scatter`, `render_views`, `export_glb`, `report`).
   Do not reimplement those.
2. Headless only: `blender -b --factory-startup -P <script> -- <args>` from
   `/Users/alex/恐怖遊戲2`. Blender 5.2 is on PATH. The Blender MCP is not connected.
3. Use 1k Poly Haven textures only, and don't keep extra copies of renders (disk is limited).

## Shared coordinate system (must match exactly, or the zones won't connect)
- Blender coordinates, meters, Z up. Floor of every zone at z = 0.
- The route runs along +Y. x = 0 is the centre line.
- Zones touch at shared boundary walls (y = const). Every boundary has ONE doorway:
  2.4 m wide (x from -1.2 to 1.2), 3.0 m high, with a steel door frame; the door leaf is
  missing or hanging open (never blocking the opening).
- The boundary wall at the FAR end of a zone (larger y) belongs to that zone. Do not build
  a wall at your near boundary (smaller y), except zone A which also builds its start wall.
  Build your side walls flush with the shared boundary so there are no gaps.
- Walls 0.3 m thick, built outward from the zone box (the box is the walkable interior).
- Where a wider zone follows a narrower one (A→B at y 16, B→C at y 34), the parts of the
  boundary wall outside the narrower zone's width are built by the coordinator in the assembly
  step. Do not build them yourself.

| Zone | Name | Interior box (x range, y range) | Ceiling | Script / output name |
|---|---|---|---|---|
| A | Freight elevator and stairwell landing | x -6..6, y 0..16 | 4.0 | `zone_a_entry` |
| B | Staff locker room and washroom | x -10..10, y 16..34 | 3.5 | `zone_b_lockers` |
| C | Sewing hall | x -18..18, y 34..74 | 7.0 | `zone_c_sewing` |
| D | Packing hall with conveyor lines | x -18..18, y 74..114 | 6.0 | `zone_d_packing` |
| E | Ride-parts warehouse | x -14..14, y 114..144 | 8.0 | `zone_e_warehouse` |
| F | Eternal Joy machine chamber (finale) | x -12..12, y 144..170 | 9.0 | `zone_f_core` |

Zone F has no exit doorway; its far wall is solid.

## Finished props to reuse (import with `bkit.import_glb`, never remodel them)
All in `/Users/alex/恐怖遊戲2/public/models/`, already baked, origin at bottom centre, front -Y:
`conveyor.glb` (3.1 x 0.9 x 0.9 m), `sewing_machine.glb` (1.1 x 0.54 x 1.4 m),
`locker.glb` (0.95 x 0.7 x 1.85 m, 3-door bank), `ferris_cabin.glb` (1.6 x 1.6 x 2.5 m),
`joy_machine.glb` (1.7 x 0.95 x 2.8 m), `joy_jar.glb` (0.3 x 0.23 x 0.5 m),
`name_tag.glb` (tiny), plus Chapter 1 props such as `crate.glb`, `lamp.glb`, `plush_pile.glb`,
`popcorn.glb`, `generator.glb`, `fusebox.glb`, `lever.glb`, `cassette.glb`.
Vary rotation and spacing so repeated props don't look stamped. Instances share mesh data:
duplicate with linked data (`obj.copy()` without copying data) so the GLB stays small.

## What each zone is about (gameplay first)
- A: The player arrives in a caged freight elevator (stuck open, at the near end) and walks past
  a small guard booth with a dead CRT and a sign-in clipboard. Low, cramped, a few pallets.
  Sets the tone. The far doorway leads to B.
- B: Rows of locker banks forming 2-3 aisles (hiding spots), benches, a washroom corner with
  broken sinks and mirrors, a notice board. Place `name_tag.glb` on a bench as a pickup.
  The aisles must be at least 1.2 m wide.
- C: Big hall, rows of sewing tables (`sewing_machine.glb`) in a grid with 1.5 m+ aisles,
  bolts of fabric, half-sewn plush toys, hanging work lamps. The Seamstress enemy hangs from a
  ceiling trolley: build a ceiling I-beam rail LOOP (a rounded rectangle around the hall, inset
  about 4 m from the walls, plus one cross rail down the middle) with its BOTTOM flange at
  z = 5.2 m, hung from the ceiling on drop rods. Keep z 0..5.2 under the rails clear of tall
  objects. Add a raised foreman's office with windows on one side (not enterable).
- D: Several conveyor lines (`conveyor.glb` placed end to end into 2-3 long lines) with packing
  tables, stacks of boxes of smiling toys, a sorting chute, and a mezzanine catwalk along one
  side wall (visual only, not walkable: give it no stairs). Leave a clear main path down the
  middle and cross gaps between lines. The small Giggler enemies roam here.
- E: Tall warehouse with steel pallet racking (3-4 levels), crates, tarps, spare ride parts:
  `ferris_cabin.glb` (2-3 of them, one tipped over), carousel horses or coaster cars under
  tarps, a forklift. Racks form aisles at least 2 m wide.
- F: Round-feeling chamber (an octagon inside the box is fine). `joy_machine.glb` scaled up
  x2.5 as a huge centrepiece in the middle, thick cables and pipes running from it into the
  walls and ceiling, shelves of `joy_jar.glb` along the walls (30+ jars), a gantry walkway
  around the machine at about 3 m (visual), an unsettling painted smiley mural. Keep a 3 m clear
  ring around the machine at floor level for the final chase.

Everywhere: concrete floors with stains, puddles and drains; painted block or concrete walls
with peeling paint and water streaks; ceiling with beams, ducts, pipes and cable trays; light
fixtures (mostly dead, a few working); debris (paper, broken toys, fallen ceiling tiles); hazard
paint and faded 1990s safety signs. Do not leave large bare flat surfaces.

## Technical rules
- Budget: up to 60k tris per zone for the shell and dressing you model, not counting the
  imported props.
- Walls, floors and ceilings: real tiling Poly Haven textures with world-scale `box_uv`
  (concrete floor 2-4 m tile, walls 2-3 m), exported as tiling textures. Do NOT bake the big
  shell surfaces into one texture (it would be blurry). Small detailed dressing you model may
  be joined and baked (1024) per group.
- Keep material count reasonable (under ~20 per zone); reuse the same materials across objects.
- Lighting for previews only: dim and moody, cold fluorescent plus a few warm sources. Lights
  are not exported; you list them in the JSON instead (below).
- Object naming: prefix every object with your zone letter, e.g. `C_wall_n`, `C_rail_loop`.

## Outputs (exactly these paths)
- Build script: `/Users/alex/恐怖遊戲2/blender/map_ch2/<name>_build.py`
- Level chunk: `/Users/alex/恐怖遊戲2/public/models/ch2/<name>.glb` (JPEG textures)
- Gameplay data: `/Users/alex/恐怖遊戲2/public/models/ch2/<name>.json`, in Blender coordinates:
  ```json
  {"zone": "C",
   "colliders": [[cx, cy, cz, sx, sy, sz, rotZ_radians], ...],
   "lights": [{"pos": [x,y,z], "color": "#ffe0b0", "intensity": 1.0, "range": 8, "flicker": false}],
   "markers": {"name": [x, y, z]}}
  ```
  Colliders are boxes (centre and full size) for walls, large props and anything the player must
  not walk through. Markers name useful spots: `entry`, `exit`, pickups, hiding spots, enemy
  spawn points and patrol waypoints (for C: points along the rail loop).
- Saved scene: `/Users/alex/恐怖遊戲2/blender/bake/map_ch2/<name>.blend` (no .blend1 backups)
- Previews (overwrite, don't keep old copies):
  `/Users/alex/恐怖遊戲2/renders/ch2_<name>_eye.png`: 2-4 views from eye height (1.6 m)
  inside the zone, including one looking at each doorway.
  `/Users/alex/恐怖遊戲2/renders/ch2_<name>_top.png`: top-down render with the ceiling hidden,
  to check the layout.

## Process
1. Blockout at true scale, render the top view, and check aisles, doorways and the zone box.
2. Build real construction and dressing, then render the eye-level views.
3. Do at least 2 render-and-fix rounds against the realism checklist. Read every PNG yourself.
4. Export, then re-import your GLB into a fresh scene and render one eye view to confirm what
   ships looks right.

Touch no other files in the project. Do not run git. Do not edit `src/`, other zones' files,
or existing prop scripts and models.

## Report back (short)
Paths written, triangle count (shell vs imported props), GLB size, materials and Poly Haven
textures used, how the doorways sit (x/z ranges at each boundary), what you checked in the
renders, and anything that still looks wrong.
