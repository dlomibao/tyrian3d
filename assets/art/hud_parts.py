"""The pieces the one- and two-player in-game frames (pictures 3 and 6) share, in the original's
pixel layout: materials, the side panel and the power bar under the playfield, and a shield and
armour block."""

import common as c
import panels as p


def materials():
    """(bronze, dark bronze, readout glass, label green, LED red)."""
    return (p.bronze(), p.bronze("dark_bronze", color=(96, 78, 58), roughness=0.45), p.glass(),
            c.emission("green", c.srgb(10, 200, 30), 1.1), c.emission("red", c.srgb(200, 20, 10), 2.0))


def frame(metal, dark, glass):
    """The side panel (x 262-320), the bar under the playfield (y 183-200) and its ribbed power
    gauge, with a ribbed pipe along each."""
    p.box("side", 262, 0, 320, 200, 0.0, 0.6, metal, bevel=0.1)
    p.box("bottom", 0, 183, 262, 200, 0.0, 0.6, metal, bevel=0.1)
    p.box("edge", 259, 0, 263, 186, 0.0, 0.85, dark, bevel=0.12, segments=3)
    p.bezel("power", 7, 187, 250, 196, metal, glass, rim=2)
    for i in range(9, 249, 3):
        p.box(f"rib{i}", i, 188.5, i + 1.4, 194.5, 0.45, 0.7, dark, bevel=0.02)
    p.box("cap_l", 0, 185, 6, 198, 0.4, 0.95, dark, bevel=0.12, segments=3)
    p.box("cap_r", 252, 185, 260, 198, 0.4, 0.95, dark, bevel=0.12, segments=3)
    p.pipe("side_pipe", [(264.8, 1), (264.8, 199)], 0.13, dark, ribs=5)
    p.pipe("bar_pipe", [(1, 184.3), (258, 184.3)], 0.1, dark, ribs=5)


def shield_block(name, y0, y1, label_y1, metal, dark, glass, green):
    """Shield and armour: a bar on each side (y0-y1), the vertical labels between (y0-label_y1),
    a little arch under them."""
    p.bezel(f"{name}_shield_bar", 269, y0, 279, y1, metal, glass)
    p.bezel(f"{name}_armor_bar", 306, y0, 316, y1, metal, glass)
    p.bezel(f"{name}_shield_lbl", 283, y0 + 1, 292, label_y1, metal, glass, rim=1.5)
    p.bezel(f"{name}_armor_lbl", 294, y0 + 1, 303, label_y1, metal, glass, rim=1.5)
    p.label(f"{name}_shield_text", "SHIELD", 287.5, y0 + 2, 6.0, green, vertical=True)
    p.label(f"{name}_armor_text", "ARMOR", 298.5, y0 + 2, 6.0, green, vertical=True)
    p.greebles(f"{name}_g", 282, label_y1 + 3, 304, y1 - 3, dark, 6, seed=int(y0))
    arch = c.primitive("cylinder", f"{name}_arch", dark, vertices=32, radius=0.55, depth=0.3)
    arch.location = p.px(292.5, y1 + 4, 0.55)
