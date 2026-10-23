"""Tan bunker (newsh3.shp frames 84 + 86, an assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.2). Two 2x2 ground enemies side by side make one 48 x 22 px bunker
(sprite.json `assemblyLayout`; the newsh3-1 in that layout is a separate enemy parked below it):
the mirror image of the newsh3-122 bunker. A bevelled end cap on the left with two glowing red
vent slits, a long flat tan roof with light ribs and a recessed square hatch with a dark slot, a plain bevelled cap
on the right, and a darker sloped front face along the bottom of the sprite.

The whole bunker is built once in assembly coordinates (pixel edges, cols 0..48 from the left
of newsh3-84, rows 0..28) and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-86.py [-- --preview out.png]
(the preview is the whole bunker; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b115 as lib  # noqa: E402

NAME = "assembly-newsh3-86"
ROOT = common.repo_root(__file__)
PIECES = ["newsh3-84", "newsh3-86"]
CX0, CY0 = 229, -7  # screen position of the assembly centre (between the two pieces)

SPEC = {
    "height": 0.34,
    "front_top": 16.6,
    # (col edge, back row edge, front-bottom row edge, height factor)
    "sections": [(6, 7.0, 22.0, 0.58), (8, 5.5, 24.0, 0.64), (14, 2.5, 24.0, 0.86), (15, 2.0, 23.0, 0.9),
                 (16.5, 2.0, 22.0, 1.0), (22.9, 2.0, 22.0, 1.0), (23.1, 2.0, 24.0, 1.0),
                 (39.0, 2.0, 24.0, 1.0), (40.0, 2.0, 24.0, 0.96), (44.0, 6.0, 24.0, 0.76),
                 (46.0, 8.0, 22.0, 0.66)],
    "bars": [(16, 17, 3, 16.6, 0.03, "rib"),  # light rib between the vent cap and the roof
             (21, 22, 4, 15, 0.015, "rib2"),
             (25, 26, 6, 13, 0.04, "rib2"),  # light line on the hatch plate
             (31, 33, 6, 13, 0.016, "slot"),  # dark slot plate beside it
             (34, 35, 3.5, 14, 0.025, "rib"),  # rib at the right cap
             (17, 39, 14, 15, 0.012, "ledge"),  # light ledge along the roof
             (16, 39, 16, 16.8, 0.006, "edge"),  # front edge of the roof
             (24, 34, 5, 5.6, 0.004, "groove"), (26, 30, 13, 13.6, 0.004, "groove")],
    "panels": [(22, 5, 34, 14, (23, 6, 30, 13))],
    "vents": [(8, 9, 9, 16, "vent"), (9, 10, 9, 16, "vent_hot"),
              (12, 13, 6, 16, "vent"), (13, 14, 6, 16, "vent_hot")],
}


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh3_86"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(168, metallic=0.1, roughness=0.75),  # 0 roof
        pal(163, metallic=0.1, roughness=0.85),  # 1 dark left end cap round the vents
        pal(165, metallic=0.1, roughness=0.85),  # 2 front slope
        pal(171, metallic=0.15, roughness=0.6),  # 3 bright rib
        pal(170, metallic=0.15, roughness=0.65),  # 4 rib
        pal(169, metallic=0.1, roughness=0.7),  # 5 ledge
        pal(162, metallic=0.1, roughness=0.9),  # 6 groove round the hatch
        pal(167, metallic=0.15, roughness=0.7),  # 7 hatch plate
        pal(164, metallic=0.15, roughness=0.75),  # 8 slot plate
        pal(119, emission_strength=4.0),  # 9 hot vent glow
        pal(116, emission_strength=2.0),  # 10 dimmer vent glow
        pal(166, metallic=0.1, roughness=0.8),  # 11 right end cap
    ]
    M = {"roof": 0, "cap": 1, "front": 2, "back": 2, "rib": 3, "rib2": 4, "ledge": 5, "groove": 6,
         "panel": 7, "slot": 8, "vent_hot": 9, "vent": 10, "edge": 11, "cap_r": 11}
    bm = bmesh.new()
    lib.bunker(bm, SPEC, M)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    lib.export_assembly(ROOT, obj, layout, argv, 48, 28)


if __name__ == "__main__":
    main()
