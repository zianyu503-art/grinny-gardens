"""Build one creature, save .blend, export GLB and render preview shots.

usage: blender -b --factory-startup --python blender/make_creature.py -- <name> [samples]
"""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
name = args[0]
samples = int(args[1]) if len(args) > 1 else 96

mod = importlib.import_module("creature_" + name)
lib.reset()
mod.build()
lib.export_glb(name)

h = mod.FRAME["height"]
cx, cy, cz = mod.FRAME["center"]
floor = lib.stage("horror")

# horror rig: flashlight from the viewer, cold rim light, faint red bounce
fl = lib.add_area("Flashlight", (0.9 * h * 0.35, -h * 1.5, cz * 0.85), (cx, cy, cz), 2600 * h / 3.6,
                  (1.0, 0.86, 0.68), spot=True)
rim = lib.add_area("Rim", (h * 0.5, h * 1.0, h * 1.2), (cx, cy, cz), 900 * h / 3.6, (0.45, 0.6, 1.0), size=h)
red = lib.add_area("RedBounce", (-h * 0.4, -h * 0.5, 0.2), (cx, cy, cz), 90 * h / 3.6, (1.0, 0.1, 0.05), size=1)
horror = [fl, rim, red]
# studio rig: soft neutral light so the forms can be judged
key = lib.add_area("Key", (-h * 0.9, -h * 1.1, h * 1.2), (cx, cy, cz), 1500 * h / 3.6, size=h * 1.2)
fill = lib.add_area("Fill", (h * 1.1, -h * 0.8, h * 0.6), (cx, cy, cz), 500 * h / 3.6, size=h)
back = lib.add_area("Back", (0, h * 1.2, h * 1.2), (cx, cy, cz), 900 * h / 3.6, size=h)
studio = [key, fill, back]

lib.setup_render(samples=samples, res=(1440, 810))
lib.save_blend(name)

shots = getattr(mod, "SHOTS", None) or [
    ("hero", "horror", (-h * 0.45, -h * 1.45, cz * 0.55), (cx, cy, cz * 1.05), 32),
    ("studio", "studio", (h * 0.75, -h * 1.5, cz * 1.0), (cx, cy, cz), 35),
    ("face", "horror", (-h * 0.12, -h * 0.75, cz * 1.55), (cx, cy, cz * 1.55), 45),
]
world = bpy_world = None
import bpy  # noqa: E402

for shot, mood, cam_loc, target, lens in shots:
    for o in horror:
        o.hide_render = mood != "horror"
    for o in studio:
        o.hide_render = mood != "studio"
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.004, 0.005, 0.009, 1) if mood == "horror" else (0.05, 0.05, 0.055, 1)
    if mood == "horror":
        fl.location = (cam_loc[0] + 0.35 * h, cam_loc[1] + 0.2 * h, cam_loc[2] + 0.28 * h)
        lib.orient_to(fl, target)
    lib.camera(cam_loc, target, lens)
    lib.render(os.path.join(lib.ROOT, "renders", "%s_%s.png" % (name, shot)))
