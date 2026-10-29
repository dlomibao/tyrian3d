"""The purple carved cross on TYRIAN's islands (map 1-9, layer 2; a 4x4 pattern with its corners cut,
centre tiles 158/159/168/169), after the concept assets/blender/features/concepts/tyr-purple-cross.jpg:
a cross of chamfered purple stone sunk into the island's rock, eight cracked octagonal bosses round
its rim (two at the end of each arm; top enemies sit on them), four big round discs in the arms'
inner corners, a ringed medallion on each arm and a bigger one at the centre, and slotted panels
either side of the centre. The eight outer cells carry enemies (tops 0.22..0.33); the four centre
cells are always visible and stand a little higher.

The structure replaces its tiles, so it carries the rock they paint (Structure.rock) round the stone.
Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_purple_cross.py
    python tools/concept_maps.py tile:shapesz-tyrbld-purple-cross --concept tyr-purple-cross --span 0,0,3,3
    python assets/blender/tiles/tyrbld_purple_cross.py --rock-detail
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-purple-cross
"""

import sys
from pathlib import Path

ROCK_DETAIL = "--rock-detail" in sys.argv
if not ROCK_DETAIL:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import lib_tyrbld as tb  # noqa: E402

CX = 48.0  # the cross's vertical axis (px)
CY = 57.0  # its horizontal axis (px)
# The eight rim bosses (px centre, radius), from the art (tiles 155/157/175/177).
RIM_KNOBS = [(37.0, 14.0, 10.0), (59.5, 14.0, 10.0),
             (12.5, 42.0, 10.0), (83.0, 42.0, 10.0),
             (12.5, 72.0, 10.5), (83.0, 71.5, 10.0),
             (36.5, 97.5, 10.0), (60.0, 97.5, 10.0)]
# The four discs in the arms' inner corners (tiles 158/159/168/169).
INNER_DISCS = [(37.0, 41.5, 8.5), (59.0, 41.5, 8.5), (37.0, 71.0, 8.5), (59.0, 71.0, 8.5)]
# The ringed medallions on the arms (they reach into enemy cells: kept low).
ARM_MEDALS = [(CX, 29.0), (CX, 85.0), (24.5, CY), (71.5, CY)]
# The cross's arms (px boxes): the vertical arm and the horizontal one.
V_ARM = (36, 21, 60, 91)
H_ARM = (12, 45, 84, 70)

BASE_Z = 0.13  # the stone's chamfered base round the arms
ARM_Z = 0.19  # the arms' raised top
PANEL_Z = 0.235  # the slotted panels by the centre (centre cells only)
SLOT_Z = 0.205


# The purple a step lighter than PAL_T's and a little less matte, for the original's mid-lavender.
PURPLE, PURPLE_DARK, PURPLE_LIGHT = 89, 87, 90
STONE_ROUGH = 0.6
# Boulders are kept off the stone shrunk by this much (px), so the rock reaches right up to it and
# matches the per-tile islands round the cross (the stone's base buries their inner sides).
ROCK_INSET = 3


def build(name):
    import lib_l1bld as lb

    s = tb.Structure(name)
    purple = s.m(PURPLE, roughness=STONE_ROUGH)
    dark = s.m(PURPLE_DARK, roughness=STONE_ROUGH)
    light = s.m(PURPLE_LIGHT, roughness=STONE_ROUGH)
    stone = s.purple_mask()

    # The stone: a chamfered base over every purple pixel, the arms raised on it.
    s.carved(stone, BASE_Z, mat=dark, chamfer_px=2, chamfer_drop=0.04)
    arms = (s.box_mask(*V_ARM) | s.box_mask(*H_ARM)) & stone
    s.carved(arms, ARM_Z, mat=purple, chamfer_px=2, chamfer_drop=0.03, edge_mat=dark)
    # Slotted panels either side of the centre (two slots each), and the short panels above and
    # below it, in the centre cells.
    for x0, x1 in ((30, 43), (53, 66)):
        s.raise_box(x0, 50, x1, 64, PANEL_Z, light)
        w = (x1 - x0 - 3) / 2
        for k in range(2):
            sx = x0 + 1 + k * (w + 1)
            s.raise_box(sx + 0.5, 52, sx + w + 0.5, 62, SLOT_Z, dark)
    for y0, y1 in ((37, 47), (67, 77)):
        s.raise_box(43, y0, 53, y1, PANEL_Z, light)
        s.raise_box(45, y0 + 2, 51, y1 - 2, SLOT_Z, dark)
    deck = s.terrace(bottom=-0.04, wall_mat=dark)

    # The rim bosses: two-tier cracked octagons under the enemies.
    for px, py, r in RIM_KNOBS:
        s.knob(px, py, r, BASE_Z - 0.05, 0.25, mat=dark, sides=8, bevel=0.2)
        s.knob(px, py, r * 0.72, 0.24, 0.31, mat=purple, sides=8, bevel=0.3, angle=0.0)
    # The inner-corner discs (always visible): a round slab with a raised cap.
    for px, py, r in INNER_DISCS:
        s.knob(px, py, r, ARM_Z - 0.03, 0.30, mat=purple, sides=12, bevel=0.2)
        s.knob(px, py, r * 0.62, 0.29, 0.35, mat=light, sides=12, bevel=0.35)
    # Arm medallions: a ring with a low dome (they reach into enemy cells: under 0.33).
    for px, py in ARM_MEDALS:
        s.knob(px, py, 5.0, ARM_Z - 0.02, 0.26, mat=dark, sides=12, bevel=0.25)
        s.dome(px, py, 3.2, 3.2, 0.25, 0.06, light, sides=12, rings=3)
    # The centre medallion, the highest point.
    s.knob(CX, CY, 6.5, ARM_Z - 0.02, 0.31, mat=dark, sides=12, bevel=0.25)
    s.knob(CX, CY, 5.0, 0.30, 0.33, mat=purple, sides=12, bevel=0.1)
    s.dome(CX, CY, 3.6, 3.6, 0.32, 0.08, light, sides=12, rings=3)

    # The island's rock round it, boulders kept off the stone.
    s.rock(exclude=lb.erode(stone, ROCK_INSET))

    objects = s.objects(deck_bm=deck)
    s.check(objects)
    s.export(objects)


def rock_detail():
    """After tools/concept_maps.py: the concept paints the rock round the cross as dark rubble, which
    the bake would lay over the real boulders and make a dark square against the per-tile islands
    (they carry no concept texture). Outside the purple stone (the concept's purple, grown a little),
    bring the detail map to about the palette colour and flatten the relief."""
    import numpy as np
    from PIL import Image, ImageFilter

    root = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
    d = root / "assets/blender/textures/shapesz-tyrbld-purple-cross"
    c = np.asarray(Image.open(d / "concept.png").convert("RGB")).astype(int)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    purple = Image.fromarray((((b > g + 12) & (r > g + 4)) * 255).astype(np.uint8))
    purple = purple.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(5))
    w = np.asarray(purple.filter(ImageFilter.GaussianBlur(4))) / 255.0  # 1 on the stone
    det = np.asarray(Image.open(d / "detail.png").convert("L")) / 255.0
    rock = np.clip(0.97 + 0.2 * (det - 0.85), 0.9, 1.0)
    out = w * det + (1 - w) * rock
    Image.fromarray((out * 255).round().astype(np.uint8)).save(d / "detail.png")
    hi = Image.open(d / "height.png").convert("L")
    h, hb = np.asarray(hi) / 255.0, np.asarray(hi.filter(ImageFilter.GaussianBlur(12))) / 255.0
    out = w * h + (1 - w) * (hb + 0.2 * (h - hb))
    Image.fromarray((out * 255).round().astype(np.uint8)).save(d / "height.png")
    print("rock detail: stone", round(float(w.mean()), 3), "of the map")


if ROCK_DETAIL:
    rock_detail()
else:
    build("purple-cross")
