"""The small red-light platform of map 1-3's ground (shapesz.dat; 3 x 6 tiles at rows 225-227,
cols 4-9: 360 361 361 361 361 362 / 370 347 339 339 347 372 / 380 381 381 381 381 382), after the
concept assets/blender/features/concepts/l1-bld-red-bar.jpg: a riveted machine panel between a
crenellated rock rim (heaps of rock at both ends), struts and vents above and below a light band,
and in the band two glowing square panes in metal frames (347) flanking a carrier plate with six
caged oval red lights (339 339). The game draws red-light enemies (newshs 235 / 195) exactly over
the band's four cells at 0.45, so the band stays under ENEMY_MAX.

Run from the repo root (lib_l1bld.py; DECISIONS.md D34):

    blender --background --factory-startup --python assets/blender/tiles/l1bld_red_bar.py
    python tools/concept_maps.py tile:shapesz-l1bld-red-bar --concept l1-bld-red-bar
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-l1bld-red-bar
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_l1bld as lb  # noqa: E402
import numpy as np  # noqa: E402

OUTER_DECK = 0.24  # the rocky ground round the panel (under the rocks)
PANEL = (22, 14, 122, 63)  # the machine panel's pixel box (concept, registered on the tiles)
PANEL_TOP = 0.31
BAND = (24, 30, 120, 55)  # the light band: a plate across the enemy cells
BAND_TOP = 0.335
CARRIER = (47, 31, 97, 54)  # the plate holding the six oval lights
CARRIER_TOP = 0.36
BAR_X = [52 + 8 * k for k in range(6)]  # oval light centres (the tiles' 8 px bars)
BAR_Y = (32, 52)  # their length in the tiles
SLOT_FLOOR = 0.315
PANES = [(27, 31, 44, 53), (99, 31, 116, 53)]  # the square glowing panes (347)
STRUT_TOP = 0.40  # struts above and below the band (outside the enemy cells)
TOP_STRUTS = [27, 51, 75, 99, 117]
BOTTOM_STRUTS = [40, 64, 88, 112]
TOP_VENTS = [39, 63, 87, 109]
BOTTOM_VENTS = [28, 52, 76, 100]


def stadium(b, cx, ys, r):
    """Pixel mask of an oval slot (a stadium): `r` px either side of column cx, round ends."""
    yy, xx = np.mgrid[0:b.H, 0:b.W] + 0.5
    cy = np.clip(yy, ys[0] + r, ys[1] - r)
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def main():
    b = lb.Building("red-bar")
    b.surface(deck=OUTER_DECK, channel=False, pits=False, red=False)
    x0, y0, x1, y1 = PANEL
    # The panel: a chamfer step round its top, then the top.
    b.raise_box(x0, y0, x1, y1, PANEL_TOP - 0.025, b.m("pave"))
    b.raise_box(x0 + 2, y0 + 2, x1 - 2, y1 - 2, PANEL_TOP, b.m("pave"))
    # Vents: dark slotted recesses between the struts.
    for vx in TOP_VENTS:
        b.raise_box(vx - 3, 18, vx + 3, 24, PANEL_TOP - 0.04, b.m(2))
    for vx in BOTTOM_VENTS:
        b.raise_box(vx - 3, 58, vx + 3, 61, PANEL_TOP - 0.04, b.m(2))
    # The light band: a metal plate with a chamfer step.
    bx0, by0, bx1, by1 = BAND
    b.raise_box(bx0, by0, bx1, by1, BAND_TOP - 0.015, b.m(5))
    b.raise_box(bx0 + 1, by0 + 1, bx1 - 1, by1 - 1, BAND_TOP, b.m(5))
    # The carrier plate, its six oval slots cut in down to a dark red floor.
    b.raise_box(*CARRIER, CARRIER_TOP, b.m(7))
    for cx in BAR_X:
        b.set_region(stadium(b, cx, BAR_Y, 3.0), SLOT_FLOOR,
                     b.m(lb.PAL["red"], emission_strength=0.9, roughness=0.4))
    deck = b.terrace()

    red = b.m("red", emission_strength=2.5, roughness=0.3)
    # The oval lights: low capsules in their slots, each crossed by a cage of thin bars.
    for cx in BAR_X:
        b.capsule(cx, (BAR_Y[0] + BAR_Y[1]) / 2, BAR_Y[1] - BAR_Y[0] - 1, 2.6, axis="y", z=0.35,
                  mat=red, housing=False, sides=10)
        for gx in (cx - 1.3, cx + 1.3):
            b.wall_block(gx - 0.35, BAR_Y[0] + 1, gx + 0.35, BAR_Y[1] - 1, SLOT_FLOOR - 0.01, 0.37,
                         b.m("metal"), bevel=0.2)
    # The square panes: a metal frame round glowing red glass.
    for pane in PANES:
        b.hatch(*pane, z=0.375, frame_px=2, depth_=0.03, mat_frame=b.m("metal"),
                mat_inside=b.m("red", emission_strength=0.9, roughness=0.15))
    # Struts: vertical girders on the panel above and below the band (clear of the enemy cells).
    for sx in TOP_STRUTS:
        b.wall_block(sx - 1.5, y0 + 2, sx + 1.5, 27.5, PANEL_TOP - 0.02, STRUT_TOP, b.m(7), bevel=0.4)
    for sx in BOTTOM_STRUTS:
        b.wall_block(sx - 1.5, 56.5, sx + 1.5, y1 - 2, PANEL_TOP - 0.02, STRUT_TOP, b.m(7), bevel=0.4)
    # A girder along the top and bottom of the band (outside the enemy rows).
    b.wall_block(x0 + 2, 26.5, x1 - 2, 27.8, PANEL_TOP - 0.02, 0.36, b.m(6), bevel=0.3)
    b.wall_block(x0 + 2, 56.2, x1 - 2, 57.5, PANEL_TOP - 0.02, 0.36, b.m(6), bevel=0.3)

    # The rim: big rocks along the top and bottom edges, heaps at both ends; none on the panel.
    def keep(px, py):
        return not (x0 + 3 < px < x1 - 3 and y0 + 4 < py < y1 - 3)

    b.rim_rocks(spacing=10.0, inset=4.0, size=(0.6, 0.85), height=(0.32, 0.48), sink=0.10, keep=keep)
    b.rim_rocks(spacing=7.0, inset=11.0, size=(0.5, 0.7), height=(0.28, 0.40), sink=0.08, keep=keep)
    # Small stones along the very edge, hiding the deck's pixel-stepped outer wall.
    b.rim_rocks(spacing=6.0, inset=1.5, size=(0.5, 0.7), height=(0.20, 0.30), sink=0.20, keep=keep)
    objects = b.objects(deck)
    b.check(objects)
    b.export(objects)


main()
