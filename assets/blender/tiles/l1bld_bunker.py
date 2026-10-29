"""The square bunker of map 1-3's ground (shapesz.dat; 6 x 6 tiles, five of them on the map), after
the concept assets/blender/features/concepts/l1-bld-bunker.jpg: a paved platform ringed by a rocky,
crenellated rim, a raised square block in the middle (the tiles' bevelled 415-419 ring, its front
drawn as the dark band of 399), and on it the bunker's hatch (318 319 / 328 329), over which the
game draws a ground enemy (newshp 153/155/199/201) at 0.45: the hatch stays under ENEMY_MAX.

The worked example for lib_l1bld.py (DECISIONS.md D34). Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/l1bld_bunker.py
    python tools/concept_maps.py tile:shapesz-l1bld-bunker --concept l1-bld-bunker
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-l1bld-bunker
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_l1bld as lb  # noqa: E402

OUTER_DECK = 0.20  # the paving between the rim and the block
BLOCK = (28, 36, 116, 116)  # the raised block's pixel box (from the tiles' bevel)
BLOCK_TOP = 0.32
CHAMFER_PX = 2
HATCH = (48, 56, 96, 112)  # the 2 x 2 hatch cells
HATCH_TOP = 0.37  # under ENEMY_MAX: the enemy drawn over the hatch sits on it


def main():
    b = lb.Building("bunker")
    b.surface(deck=OUTER_DECK, channel=False, pits=False, red=False)
    x0, y0, x1, y1 = BLOCK
    # The block: a chamfer step round its top, then the top.
    b.raise_box(x0, y0, x1, y1, BLOCK_TOP - 0.03, b.m("pave"))
    b.raise_box(x0 + CHAMFER_PX, y0 + CHAMFER_PX, x1 - CHAMFER_PX, y1 - CHAMFER_PX, BLOCK_TOP, b.m(7))
    deck = b.terrace()
    # The hatch: a light metal frame round a dark red interior with a faint glow (the concept's
    # broken hatch shows red mesh inside).
    b.hatch(*HATCH, z=HATCH_TOP, frame_px=3, depth_=0.04,
            mat_inside=b.m(lb.PAL["red_dark"], emission_strength=0.6, roughness=0.6))
    # Corner bolts of the block, as in the concept's raised square.
    for px, py in ((x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6)):
        b.dome(px, py, 2.2, 2.2, BLOCK_TOP - 0.01, 0.04, b.m("metal"), sides=10, rings=3)
    # The rim: big and small rocks in two rows, the outer ones taller (crenellations).
    b.rim_rocks(spacing=9.0, inset=4.0, size=(0.55, 0.85), height=(0.30, 0.46), sink=0.10)
    b.rim_rocks(spacing=7.0, inset=10.0, size=(0.45, 0.65), height=(0.22, 0.30), sink=0.06)
    objects = b.objects(deck)
    b.check(objects)
    b.export(objects)


main()
