# Chapter 3 ghost brief (for modeling subagents)

Game: 微笑樂園 (Grinny Gardens), a first-person web horror game (Three.js, browser and iPad). The
park closed overnight in 1996; everything is ~30 years old: dust, rust, water damage, faded
paint. Mood: cold, sad, creepy, never cartoonish. These are ghosts born from the park's dead
electricity and its 27 missing children. Original designs only; do not imitate characters from
other games.

## How to build (blender-modeling skill)
1. Read `/Users/alex/.claude/skills/blender-modeling/SKILL.md`, then `references/recipes.md` and
   `references/realism-checklist.md` beside it, and the docstrings in `scripts/bkit.py`.
2. Headless only. Run with
   `python3 /Users/alex/.claude/skills/blender-modeling/scripts/run.py <script> blender/bake/ghosts/<ghost> [args]`
   from `/Users/alex/恐怖遊戲2`. The Blender MCP is not connected.
3. Humanoids: start from `bkit.base_body(kind, height, detail=0)` and `bkit.dress(...)`, rigid
   pieces parented to bones. Non-humanoids: real construction, parts tagged per bone.
4. Reuse `blender/lib.py` (`Mat`, `mat_plush`, `mat_brass`, `mat_rust`, `mat_simple`, `lathe`,
   `loft`, `seg`, `prim`, `Skel`, ...) and `blender/game_export.py` (`animate`, `cyc`, `S`).
   `blender/director/director_build.py` is a complete worked example: read `game_export()` there
   and copy that pipeline (build, per-part vertex group, decimate, join, bake, armature, clips,
   glTF export). Use Poly Haven scans at 1k (`bkit.polyhaven_texture`).
5. At least 2 render-and-fix rounds. Read every PNG yourself. Previews at low quality
   (samples 24-32, 800x600): the user wants this fast.

## Lessons already paid for (do not repeat these)
- Cycles bakes the colour of fully metallic surfaces as BLACK. Before baking, unlink Metallic on
  metal materials and set it to about 0.35.
- Glowing parts: emission is lost by the bake. Keep them as a separate unbaked mesh with its own
  emissive material, skinned to the same armature (see `DirectorHearts`).
- Decimating thin shells (horn bells, cloth) destroys them. Skip those parts, or keep them high.
- Decimate per part, keeping a minimum, not one ratio over the joined mesh.
- Replace any `None` material slots on the joined mesh before baking.
- glTF-imported objects use quaternions; set `rotation_mode = "XYZ"` before using `rotation_euler`.
- Apply modifiers one at a time only once; hundreds of parts make this slow, so keep part counts
  reasonable (under ~250).
- Blender's default font has no Chinese; use `/System/Library/Fonts/STHeiti Medium.ttc`.
- Check after export: the GLB's clip names, and that the baked render matches the live one.

## Game-ready targets
- Up to 12,000 tris each (skinned body + glow mesh), 1024 baked textures, JPEG, GLB under 2.5 MB.
- Real-world metres, Z up, front faces -Y, lowest point on z = 0, origin at bottom centre (floating
  ghosts: origin at the bottom of the model, the game sets the height).
- Export with `export_animation_mode="NLA_TRACKS"`, `export_apply=False`.
- Every ghost needs clips named exactly `Idle`, `Move`, `Attack`, `Death` plus any listed below.

## Files (exactly)
- Script: `blender/ghosts/<ghost>_build.py`
- Game model: `public/models/<ghost>.glb`
- Bakes and .blend: `blender/bake/ghosts/<ghost>/`
- Previews: `renders/ch3_<ghost>_preview.png` (before bake), `renders/ch3_<ghost>_baked.png` (after)

Touch no other files. Do not run git. Do not edit `src/` or existing scripts or models.

## The ghosts

**flicker (閃閃)**, 1.6 m, floats. Lives inside lamps and teleports between them. A gaunt child-sized
figure made of old lamp wire and scorched cloth; its head is a large cracked glass light bulb with
a glowing filament shaped like a small curled-up child (emissive). Bare cable arms with ceramic
sockets for hands. Tattered lower body trailing off into loose wires, no feet. Extra clip: `Flash`.
Death: the bulb bursts, wires go limp.

**tangle (纏纏)**, about 2.4 m long, 0.9 m high, crawls. A knot of old rubber and cloth-braided
cables shaped into a low body, dragging itself on many cable limbs ending in plugs. Its "head" is a
Bakelite wall socket faceplate whose two slots and ground hole read as a terrified face, sparking
(emissive inner glow). Fuse clips and porcelain insulators caught in the knot. Extra clip: `Lunge`.
Death: cables whip apart and burn out.

**balloon (飄飄)**, 3.2 m total, floats. A hollow clown costume with nothing inside: limp, faded
striped suit and ruffled collar hanging from a bunch of about nine wrinkled, half-deflated balloons,
one of which, largest, wears the painted clown face. Long empty sleeves ending in gloves; a noose
of balloon string hangs from one glove. Extra clip: `Drop` (lowers the rope). Death: balloons burst,
the costume collapses.

**twins (雙生子)**, 1.25 m, walks. One model, used twice in game. A girl in a 1996 park children's
choir uniform (faded pinafore, white knee socks, patent shoes, ribboned pigtails). Her face is a flat
shard of mirror set into the head (a bright, glossy, slightly blue material), cracked down the
middle. Holding one hand out to the side as if to a sister. Stiff, doll-like. Extra clip: `Freeze`
(a held, tilted-head pose). Death: the mirror shatters, the body folds down.

**ticket (剪票人)**, 2.6 m, walks, heavy. A hulking ride conductor: an oversized 1960s-style railway
coat with brass buttons, peaked cap, face hidden in shadow under the peak with two ticket-punch
holes of light (emissive). Riveted steel plates from a turnstile and ticket booth strapped over chest
and shoulders as armour. One hand is a giant steel ticket punch. A rack of old paper tickets flutters
at the belt. Extra clip: `Charge` (head-down sprint). Death: falls forward, plates clatter off.

**shadow (孩子的影子)**, 1.15 m, walks. One of the 27 missing children, reduced to a soft black
silhouette in 1996 clothes (a boy in shorts and a cap works well; keep it readable from a distance).
Near-black, slightly fuzzy edges from a noise-driven dark material, two faint warm points for eyes
(emissive). Holds a small toy by the hand. Never threatening: sad and small. It does not attack, so
it needs `Idle`, `Move` and `Release` (rises, dissolves upward) instead of `Attack` and `Death`.

## Report back (short)
For each ghost: paths, tris, GLB size, clip names, textures used, what you checked, what still looks
wrong.
