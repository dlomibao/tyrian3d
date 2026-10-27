"""Picture 3: the in-game frame for one player (JE_main, tyrian2.c: JE_loadPic(twoPlayerMode ? 6 : 3)).

The playfield (the left 262x183 pixels) is left transparent, so the frame can lie over the 3D
game. The bronze side panel keeps the original's readouts in place: the generator gauge down the
left, FRONT GUN, REAR GUN and MODE, two sidekick windows, the score slot, and the shield and
armour bars either side of their labels; the weapon power bar runs along the bottom.
Writes public/art/hud.webp.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
import hud_parts as h  # noqa: E402
import panels as p  # noqa: E402

NAME = "hud"

scene = c.new_scene(samples=96)
scene.render.film_transparent = True

metal, dark, glass, green, red = h.materials()
h.frame(metal, dark, glass)

# Top: the warning lamp, the generator gauge, the weapon readouts.
p.box("lamp_cup", 266, 2, 279, 9, 0.5, 0.8, dark, bevel=0.06)
p.lamp("lamp", 268, 3, 277, 8)
p.bezel("generator", 268, 11, 279, 107, metal, glass)
p.bezel("front", 284, 3, 313, 21, metal, glass)
p.label("front_text", "FRONT", 286, 4, 5.8, green)
p.label("front_text2", "GUN", 286, 10.5, 5.8, green)
p.box("front_led", 285, 17, 289, 20, 0.6, 0.66, red, bevel=0)
p.bezel("rear", 284, 25, 313, 42, metal, glass)
p.label("rear_text", "REAR", 286, 26, 5.8, green)
p.label("rear_text2", "GUN", 286, 32.5, 5.8, green)
p.box("rear_led", 285, 38, 289, 41, 0.6, 0.66, red, bevel=0)
p.bezel("mode_a", 286, 45, 295, 50, metal, glass, rim=1.5)
p.bezel("mode_b", 302, 45, 311, 50, metal, glass, rim=1.5)
p.bezel("mode", 284, 53, 313, 60, metal, glass, rim=1.5)
p.label("mode_text", "MODE", 286, 54, 5.0, green)
p.bezel("sidekick_l", 284, 63, 313, 80, metal, glass)
p.bezel("sidekick_r", 284, 82, 313, 99, metal, glass)
p.greebles("g_top", 282, 101, 318, 110, dark, 14, seed=3)
p.greebles("g_mid", 263, 108, 282, 113, dark, 6, size=(1.5, 3), seed=9)

# The score slot.
p.bezel("score", 267, 114, 317, 127, metal, glass)
p.pipe("rail", [(263, 130.5), (319, 130.5)], 0.12, dark, ribs=4)

# Shield and armour.
h.shield_block("p1", 134, 195, 178, metal, dark, glass, green)
p.rivets("rivet", [(282, 1.5), (315, 1.5), (282, 22.5), (315, 22.5), (282, 61), (315, 61), (282, 100.5),
                   (315, 100.5), (265.5, 112), (318.5, 112), (265.5, 132), (318.5, 132)], dark)

p.key_lights()
p.screen_camera()
c.save(NAME)
