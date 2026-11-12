# Chapter 3 new claws brief (for a modeling subagent)

Game: 微笑樂園, a first-person web horror game (Three.js). The player has two launchable claw hands
on cables. Chapter 3 adds six swappable claws (story in `blender/ghosts/CHAPTER3.md`). They are the
main thing the player looks at, close to the camera, so they must look like real, well-made,
slightly worn 1990s workshop equipment that belongs to the same family as the existing claws.

## How to build
First invoke the blender-modeling skill with the Skill tool (or read
`/Users/alex/.claude/skills/blender-modeling/SKILL.md`, `references/recipes.md` and
`references/realism-checklist.md` in full). Run builds through its `scripts/run.py`, headless, from
`/Users/alex/恐怖遊戲2`. Script: `blender/ghosts/claws_build.py` (one script, argument = claw id).

## Base model: must stay compatible with the game
`public/models/clawhands.glb` has nodes `HandL`, `HandR`, `JawL0..2`, `JawR0..2`. `src/clawpack.js`
clones the hand body and hinges each jaw at its node position, swinging it outward from the hand's
axis to open. The claw points down in model space (about 1.5 units tall, scaled to 17 cm in game).
- Import `clawhands.glb`, keep `HandL` as the shared body with its size, proportions and machined
  aluminium and graphite rubber, and re-colour its enamel parts per claw.
- Each output has exactly these nodes: `Hand` (body plus attachments), `Jaw0`, `Jaw1`, `Jaw2`, in
  the same positions as HandL/JawL0..2, with each jaw's origin on its hinge exactly as in the source.
  Optional extra node `Glow`, a child-free unbaked emissive mesh. A claw may use two working jaws and
  a small third one, but all three nodes must exist.
- Do not modify `clawhands.glb`, `src/`, or anything else. Do not run git.

## The six claws
| id | Name | Enamel | Jaws and attachments |
|---|---|---|---|
| scissors | 剪刀爪 | deep bronze-black | Two jaws are long tailor's shear blades, sharpened steel with a bright bevel edge; a brass pivot bolt and thread spool on the body, a scrap of red thread. Mei's tool. |
| magnet | 磁力爪 | oxblood red with a silver band | Three short thick pole shoes; copper-wound coils around the body, visible windings, a warning plate. |
| grapple | 鉤索爪 | olive green | Three curved steel hooks with points; a cable drum with wound steel wire on the back of the body. |
| flash | 閃光爪 | yellow, chipped | Jaws frame a chrome parabolic reflector dish with a large flashbulb at its centre (`Glow`, warm white); a capacitor can on the body. |
| horn | 喇叭爪 | cream with a tarnished brass trim | Jaws around a small tarnished brass gramophone horn mouth aimed forward; a perforated speaker grille on the body. |
| charge | 帶電爪 | deep teal | Three copper and ceramic electrode prongs with insulator rings, a Tesla coil on the body with copper windings; thin electrode tips as `Glow` (cold blue). |

Each must be recognisable by colour and silhouette in under a second.

## Rules
- Up to 4,000 tris each, plain glTF PBR materials matching the source's style (metallic and
  roughness on real values, with scratches and worn edges from small roughness or colour textures).
  No procedural-only materials in the GLB; bake if you use them, and remember Cycles bakes fully
  metallic colour as black (set Metallic about 0.35 before baking, or use plain PBR values).
- Bevel every hard edge (`bkit.harden`). Real fasteners, seams and gaps.
- Output: `public/models/claw_<id>.glb` (under 800 KB each), previews
  `renders/ch3_claw_<id>.png` (contact sheet), plus one `renders/ch3_claws_lineup.png` with all six
  side by side at the same scale. Bakes in `blender/bake/claws/<id>/`.
- Previews low quality (samples 24-32, 800x600). Read every PNG and do at least 2 fix rounds.
- Run `bkit.check` and `bkit.report`. After export, verify the GLB's node names and that each jaw
  node's position matches the source jaw.

## Report back (short)
Per claw: path, tris, GLB size, nodes, `bkit.check` result, and what still looks wrong, honestly.
