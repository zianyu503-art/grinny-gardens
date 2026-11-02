# Chapter 2 prop brief (for modeling subagents)

Game: 微笑樂園 (Grinny Gardens), a first-person web horror game (Three.js, runs in the browser
and on iPad). Chapter 2 takes place in an underground toy factory beneath an amusement park that
closed overnight in 1996. Everything is abandoned for ~30 years: dust, rust, water damage, peeling
paint, mould, cobwebs-level neglect. Mood: cold, dim, sad and creepy, not cartoonish.

## How to build (blender-modeling skill)
1. Read `/Users/alex/.claude/skills/blender-modeling/SKILL.md`, then
   `references/recipes.md` and `references/realism-checklist.md` in the same folder.
   Read the docstrings in `scripts/bkit.py` and use it for Poly Haven textures, PBR materials,
   bevels (`harden`), UVs, baking, previews and export. Do not reimplement those.
2. Headless only. Blender 5.2 is on PATH as `blender`. Run your script with
   `blender -b --factory-startup -P <script> -- <args>` from `/Users/alex/恐怖遊戲2`.
   The Blender MCP is not connected; do not try to use it.
3. Model real construction (separate parts, gaps, fasteners, bevels on hard edges), real-world
   scale in meters, Z up, the object standing on z = 0, front facing -Y.
4. Prefer real Poly Haven scanned textures (network works). Vary repeated parts. Never a flat colour.
5. Render a preview with `bkit.light_studio()` + `bkit.render_views(path)`, Read the PNG yourself,
   and fix the worst problem against the realism checklist. Do at least 2 render-and-fix rounds.
6. Game-ready step: `bkit.join` into ONE object, decimate to the web budget given for your asset,
   `bkit.origin_to_bottom`, `bkit.uv_unwrap`, `bkit.bake_to_textures(obj, out_dir, size=1024)`,
   `bkit.report()`, `bkit.export_glb(path, [obj], image_format="JPEG")`, then render the
   baked result again with `bkit.render_views` and check that it still looks right.
   Glowing parts: emission is lost by the bake; say so in your report rather than hacking it.

## Where files go (exactly)
- Build script: `/Users/alex/恐怖遊戲2/blender/props_ch2/<asset>_build.py`
- Game model: `/Users/alex/恐怖遊戲2/public/models/<asset>.glb`
- Baked textures and the saved `.blend`: `/Users/alex/恐怖遊戲2/blender/bake/<asset>/`
- Previews: `/Users/alex/恐怖遊戲2/renders/ch2_<asset>_preview.png` (before bake) and
  `/Users/alex/恐怖遊戲2/renders/ch2_<asset>_baked.png` (after bake)

Touch no other files in the project. Do not run git. Do not edit `src/`, `blender/lib.py`
or any existing creature/prop script.

## Report back (short)
For each asset: the paths you wrote, triangle count, size in meters, Poly Haven textures used,
what you checked in the previews, and anything you know still looks wrong.
