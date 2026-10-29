"""TYRIAN's purple carved blocks (map 1-9, layer 2): three structures of the same stone, the 2x2
(tiles 155 157 / 175 177), the 2x3 (155 156 157 / 175 176 177) and the 2x5 (155 156 156 156 157 /
175 176 176 176 177), after the concepts assets/blender/features/concepts/tyr-purple-2x2.jpg,
tyr-purple-2x3.jpg and tyr-purple-2x5.jpg: a low carved slab framed by a raised brick border, with
a ringed round dome (stacked carved tiers, a disc cap) on every cell's corner, and the slab's face
carved with ring bosses and upright bars (2x3, 2x5) or a block of glyph relief (2x2), on the
island's rock.

Every cell of the 2x2 and 2x3 and the first four columns of the 2x5 carry a top enemy, so the
whole block stays under L2_ENEMY_MAX (0.33): the enemies' models cover it until they are shot.
The blocks replace their tiles, so each model also carries the tiles' rock (Structure.rock). They
share tiles with each other and with the purple cross: the plan's minRows 2 tells them apart.
Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_purple_blocks.py
    python tools/concept_maps.py tile:shapesz-tyrbld-purple-2x2 --concept tyr-purple-2x2 --span -0.18,-0.18,1.37,1.26 --px 32
    python tools/concept_maps.py tile:shapesz-tyrbld-purple-2x3 --concept tyr-purple-2x3 --span -0.1,-0.3,1.175,2.3 --px 32
    python tools/concept_maps.py tile:shapesz-tyrbld-purple-2x5 --concept tyr-purple-2x5 --span 0,0,1,4 --px 32
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-purple-2x2
    (and -2x3, -2x5)

Gemini drew the 2x2's and the 2x3's domes closer together than the tiles do (by about a fifth), so
their spans are widened past the pattern's cells to put the concept's domes on the tiles' domes;
the 2x5's concept sits on its tiles as cropped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

TW, TH = 24, 28  # tile px

# The domes' centres inside their tile (px), read off the tile art (each corner tile paints one
# round lump; 156/176 repeat along the long blocks).
DOME_AT = {155: (11.5, 12.0), 156: (11.5, 12.0), 157: (12.5, 12.0),
           175: (11.5, 13.0), 176: (11.0, 13.0), 177: (12.5, 13.0)}
DOME_R = 8.3  # px: the dome's foot

# Heights (layer 2: z = 0 the island's surface).
SLAB_Z = 0.13  # the slab's face
FRAME_Z = 0.17  # the raised brick border round it
DOME_TOP = 0.32  # under L2_ENEMY_MAX
SINK = -0.03

# Each block's slab (x0, y0, x1, y1 px, frame included), its frame's width and the carvings on its
# face, read off the registered concepts (concept_maps.py, the spans in the docstring).
LAYOUT = {
    "purple-2x2": dict(slab=(13.5, 13.5, 34.5, 39.5), frame=2.5, glyph=(15.5, 15.5, 32.5, 37.5)),
    "purple-2x3": dict(slab=(12.0, 11.5, 60.0, 40.5), frame=3.5, face_y=27.0,
                       bosses=(24.0, 48.0), boss_r=3.6, bars=(36.0,), bar=(2.4, 5.0)),
    "purple-2x5": dict(slab=(6.5, 11.5, 113.5, 40.5), frame=4.0, face_y=26.0,
                       bosses=(22.0, 45.8, 69.8, 94.0), boss_r=3.8, bars=(33.8, 57.6, 81.6), bar=(2.0, 6.5)),
}


def dome(s, px, py, mats):
    """A ringed carved dome: a broad bulging foot tier, a narrower second tier and a disc cap,
    each its own smooth band (so the steps stay crisp)."""
    base, mid, top = mats
    r = DOME_R
    # (z0, z1, r_foot, r_shoulder): each tier rises from its foot and rounds over its shoulder.
    tiers = [(SINK, 0.20, r, r * 0.80, base), (0.18, 0.28, r * 0.72, r * 0.56, mid), (0.26, DOME_TOP, r * 0.44, r * 0.34, top)]
    for z0, z1, rf, rs, mat in tiers:
        h = (z1 - z0) * 12.0  # px
        prof = [(0.0, rf), (h * 0.4, rf * 0.98), (h * 0.72, rf * 0.93), (h * 0.92, (rf + rs) / 2), (h, rs), (h, 0.0)]
        s.lathe(prof, px, py, axis="z", z=z0, mat=mat, sides=20)
    # The cap's sunken centre ring (the concept's disc with a ring round it).
    s.lathe([(0.0, r * 0.26), (0.25, r * 0.26), (0.25, 0.0)], px, py, axis="z", z=DOME_TOP - 0.012, mat=base, sides=16)


def boss(s, px, py, r, z, mats):
    """A ring boss on the slab's face: a raised ring with a domed centre."""
    ring, centre = mats
    s.lathe([(0.0, r), (0.4, r), (0.6, r * 0.82), (0.6, r * 0.62), (0.3, r * 0.62), (0.3, 0.0)], px, py, axis="z", z=z, mat=ring, sides=16)
    s.dome(px, py, r * 0.58, r * 0.58, z + 0.02, 0.035, centre, sides=12, rings=3)


def bar(s, x0, y0, x1, y1, z, mats):
    """An upright carved bar on its plinth (the concept's panel between the bosses): the plinth is
    a deck step, the bar a chamfered step on it (terrace() after)."""
    plinth, body = mats
    s.set_region(s.box_mask(x0 - 2.0, y0 - 2.0, x1 + 2.0, y1 + 2.0), z + 0.025, plinth)
    s.carved(s.box_mask(x0, y0, x1, y1), z + 0.085, body, chamfer_px=1, chamfer_drop=0.03)


def build(name):
    s = tb.Structure(name)
    rows, cols = len(s.pattern), len(s.pattern[0])
    purple, dark, light = s.m("purple"), s.m("purple_dark"), s.m("purple_light")
    deep = s.m(84, roughness=0.7)

    domes = []
    for r in range(rows):
        for c in range(cols):
            dx, dy = DOME_AT[s.pattern[r][c]]
            domes.append((c * TW + dx, r * TH + dy))

    lay = LAYOUT[name]
    lx, ty, rx, by = lay["slab"]
    frame_w = lay["frame"]
    slab = s.box_mask(lx, ty, rx, by)
    inner = s.box_mask(lx + frame_w, ty + frame_w, rx - frame_w, by - frame_w)
    s.carved(slab, FRAME_Z, dark, chamfer_px=1, chamfer_drop=0.03)
    s.set_region(inner, SLAB_Z, purple)
    if "glyph" in lay:
        # The 2x2's glyph block: a raised cross of carved blocks over the slab, a sunk square in
        # the middle and a few sunk glyph strokes (the concept's runes; the bake adds the rest).
        gx0, gy0, gx1, gy1 = lay["glyph"]
        cx, cy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
        s.set_region(s.box_mask(cx - 5.5, gy0, cx + 5.5, gy1), 0.19, purple)
        s.set_region(s.box_mask(gx0, cy - 4.5, gx1, cy + 4.5), 0.19, purple)
        s.set_region(s.box_mask(cx - 3.0, cy - 3.0, cx + 3.0, cy + 3.0), 0.155, deep)
        for x0, y0, x1, y1 in ((cx - 4, gy0 + 2, cx - 2.8, gy0 + 6), (cx + 1, gy0 + 2, cx + 2.2, gy0 + 6),
                               (gx0 + 2, cy - 1, gx0 + 5, cy + 0.2), (gx1 - 5, cy - 1, gx1 - 2, cy + 0.2),
                               (cx - 1.5, gy1 - 6, cx - 0.3, gy1 - 2), (cx + 2, gy1 - 6, cx + 3.2, gy1 - 2)):
            s.set_region(s.box_mask(x0, y0, x1, y1), 0.165, deep)
    # Brick joints in the frame: narrow sunk notches every few px.
    for x in np.arange(lx + 4.0, rx - 3, 5.5):
        s.set_region(s.box_mask(x, ty, x + 0.8, ty + frame_w) | s.box_mask(x, by - frame_w, x + 0.8, by), FRAME_Z - 0.05, deep)
    for y in np.arange(ty + 4.5, by - 3, 5.5):
        s.set_region(s.box_mask(lx, y, lx + frame_w, y + 0.8) | s.box_mask(rx - frame_w, y, rx, y + 0.8), FRAME_Z - 0.05, deep)

    # Ring bosses and upright bars on the long blocks' face, where the concept carves them.
    cy = lay.get("face_y", (ty + by) / 2)
    for bx in lay.get("bosses", ()):
        boss(s, bx, cy, lay["boss_r"], SLAB_Z, (dark, light))
    for bx in lay.get("bars", ()):
        hw, hh = lay["bar"]
        bar(s, bx - hw, cy - hh, bx + hw, cy + hh, SLAB_Z, (dark, light))

    for px, py in domes:
        dome(s, px, py, (dark, purple, light))

    # The rock round it: the tiles' own stones, none under the domes or the slab.
    keep_out = s.box_mask(lx - 1, ty - 1, rx + 1, by + 1)
    for px, py in domes:
        keep_out |= s.ellipse_mask(px, py, DOME_R + 1, DOME_R + 1)
    # The slab under the stone is cut out (its dark would take the purple's shadows) and the
    # block's ground is the islands' dark rock instead, a deck plane just over the slab's top.
    under = lb.dilate(s.purple_mask(), 1) & s.footprint
    s.set_region(under & np.isnan(s.height), 0.0, s.m("rock_dark"))
    s.rock(exclude=keep_out | under, cut=under)

    objects = s.objects()
    s.check(objects)
    s.export(objects)


for name in ("purple-2x2", "purple-2x3", "purple-2x5"):
    build(name)
