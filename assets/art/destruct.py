"""Picture 11: the screen of Destruct, the hidden artillery game (destruct.c: JE_loadPic 11).

Black, with a status bar for each player across the top: a red lamp and a long red gauge in a
bronze housing, as the original. Everything below the bars is left transparent, so the game's
terrain can be drawn under them. Writes public/art/destruct.webp.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
import panels as p  # noqa: E402

NAME = "destruct"

scene = c.new_scene(samples=96)
scene.render.film_transparent = True

metal = p.bronze("bronze", color=(150, 96, 60))
dark = p.bronze("dark_bronze", color=(90, 50, 32), roughness=0.45)
gauge = c.material("gauge", c.srgb(90, 8, 6), roughness=0.7, emission=c.srgb(120, 10, 6), emission_strength=0.6)

for name, x0, x1 in (("left", 2, 145), ("right", 172, 316)):
    p.box(f"{name}_housing", x0, 0.5, x1, 12, 0.0, 0.6, metal, bevel=0.1, segments=3)
    p.box(f"{name}_cup", x0 + 2, 2.5, x0 + 11, 10, 0.5, 0.8, dark, bevel=0.06)
    p.lamp(f"{name}_lamp", x0 + 3.5, 3.5, x0 + 9.5, 9)
    p.bezel(f"{name}_gauge", x0 + 15, 3, x1 - 3, 9.5, metal, gauge, rim=1.2)
    p.rivets(f"{name}_rivet", [(x0 + 13, 2.2), (x0 + 13, 10.3), (x1 - 1.3, 6)], dark, radius=0.7)

p.key_lights()
p.screen_camera()
c.save(NAME)
