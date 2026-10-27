"""Picture 6: the in-game frame for two players (JE_main, tyrian2.c: JE_loadPic(twoPlayerMode ? 6 : 3)).

As picture 3 (hud.py), with the side panel split between the players: player 1's lamp, weapon
slot and shield/armour block on top, the shared score slot, then player 2's lamp and weapon slot,
the power and sidekick readouts, and player 2's shield/armour block. The playfield is left
transparent. Writes public/art/hud_two_player.webp.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
import hud_parts as h  # noqa: E402
import panels as p  # noqa: E402

NAME = "hud_two_player"

scene = c.new_scene(samples=96)
scene.render.film_transparent = True

metal, dark, glass, green, red = h.materials()
h.frame(metal, dark, glass)

# Player 1: lamp, weapon slot, shield and armour.
p.box("p1_lamp_cup", 266, 2, 279, 9, 0.5, 0.8, dark, bevel=0.06)
p.lamp("p1_lamp", 268, 3, 277, 8)
p.bezel("p1_weapon", 284, 3, 313, 10, metal, glass, rim=1.5)
p.box("p1_led", 285, 5, 289, 8, 0.6, 0.66, red, bevel=0)
h.shield_block("p1", 14, 63, 55, metal, dark, glass, green)

# The shared score slot, and a band of machinery.
p.bezel("score", 267, 71, 317, 83, metal, glass)
p.greebles("g_band", 264, 86, 319, 95, dark, 16, seed=11)
p.pipe("rail", [(263, 95.5), (319, 95.5)], 0.12, dark, ribs=4)

# Player 2: lamp, weapon slot, power and sidekick readouts, shield and armour.
p.box("p2_lamp_cup", 266, 97, 279, 104, 0.5, 0.8, dark, bevel=0.06)
p.lamp("p2_lamp", 268, 98, 277, 103)
p.bezel("p2_weapon", 284, 98, 313, 104, metal, glass, rim=1.5)
p.box("p2_led", 285, 99.5, 289, 102.5, 0.6, 0.66, red, bevel=0)
p.bezel("p2_power", 268, 106, 278, 122, metal, glass, rim=1.5)
for i in range(5):
    p.box(f"p2_power_seg{i}", 270, 108 + i * 3, 276, 109.6 + i * 3, 0.6, 0.64, green, bevel=0)
p.bezel("p2_sidekicks", 268, 125, 278, 143, metal, glass, rim=1.5)
p.bezel("p2_sidekick_l", 284, 107, 313, 124, metal, glass)
p.bezel("p2_sidekick_r", 284, 126, 313, 143, metal, glass)
h.shield_block("p2", 148, 196, 190, metal, dark, glass, green)

p.rivets("rivet", [(265.5, 67), (318.5, 67), (265.5, 87), (318.5, 87), (282, 105), (315, 105),
                   (282, 144.5), (315, 144.5)], dark)

p.key_lights()
p.screen_camera()
c.save(NAME)
