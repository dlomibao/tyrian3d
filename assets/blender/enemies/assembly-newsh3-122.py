"""Tan bunker (newsh3.shp frames 122 + 124, an assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.2). Two 2x2 ground enemies side by side make one 48 x 22 px bunker
(sprite.json `assemblyLayout`): a long flat tan roof with a recessed square hatch, a light rib at
each end of the roof, a bevelled end cap on the left, another on the right with two glowing red
vent slits, and a darker sloped front face along the bottom of the sprite.

The whole bunker is built once in assembly coordinates (pixel edges, cols 0..48 from the left
of newsh3-122, rows 0..28) and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-122.py [-- --preview out.png]
(the preview is the whole bunker; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b115 as lib  # noqa: E402

NAME = "assembly-newsh3-122"
ROOT = common.repo_root(__file__)
PIECES = ["newsh3-122", "newsh3-124"]
CX0, CY0 = 51, -18  # screen position of the assembly centre (between the two pieces)

SPEC = {
    "height": 0.34,
    "front_top": 16.6,
    # (col edge, back row edge, front-bottom row edge, height factor)
    "sections": [(3, 8.0, 22.0, 0.55), (5, 6.0, 24.0, 0.66), (9, 2.0, 24.0, 0.93), (10.5, 2.0, 24.0, 1.0),
                 (25.9, 2.0, 24.0, 1.0), (26.1, 2.0, 22.0, 1.0), (33.0, 2.0, 22.0, 1.0),
                 (33.9, 2.0, 22.0, 0.97), (34.1, 2.1, 24.0, 0.96), (41.0, 6.0, 24.0, 0.68),
                 (43.0, 7.5, 22.0, 0.58)],
    "bars": [(10, 11, 3, 16.6, 0.03, "rib"),  # light rib between the left cap and the roof
             (14, 15, 4, 14, 0.02, "rib2"),  # frame of the hatch
             (32, 33, 3, 16.6, 0.02, "rib2"),  # rib at the right cap
             (14, 28, 14, 15, 0.012, "ledge"),  # light ledge under the hatch
             (11, 33, 16, 16.8, 0.006, "edge")],  # front edge of the roof
    "panels": [(15, 5, 24, 14, (16, 6, 23, 13))],
    "vents": [(35, 36, 6, 16, "vent_hot"), (36, 37, 6, 16, "vent"),
              (39, 40, 9, 16, "vent_hot"), (40, 41, 9, 16, "vent")],
}


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh3_122"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(168, metallic=0.1, roughness=0.75),  # 0 roof
        pal(166, metallic=0.1, roughness=0.8),  # 1 end caps
        pal(165, metallic=0.1, roughness=0.85),  # 2 front slope
        pal(171, metallic=0.15, roughness=0.6),  # 3 bright rib
        pal(170, metallic=0.15, roughness=0.65),  # 4 rib
        pal(169, metallic=0.1, roughness=0.7),  # 5 ledge
        pal(162, metallic=0.1, roughness=0.9),  # 6 groove round the hatch
        pal(167, metallic=0.15, roughness=0.7),  # 7 hatch plate
        pal(119, emission_strength=4.0),  # 8 hot vent glow
        pal(116, emission_strength=2.0),  # 9 dimmer vent glow
        pal(163, metallic=0.1, roughness=0.85),  # 10 dark right end cap round the vents
    ]
    M = {"roof": 0, "cap": 1, "front": 2, "back": 2, "rib": 3, "rib2": 4, "ledge": 5, "groove": 6,
         "panel": 7, "vent_hot": 8, "vent": 9, "edge": 1, "cap_r": 10}
    bm = bmesh.new()
    lib.bunker(bm, SPEC, M)
    # The light slot down the middle of the hatch (column 18).
    X = lambda c: lib.ex(c, 48)  # noqa: E731
    Y = lambda r: lib.ey(r, 28)  # noqa: E731
    lib.box(bm, X(18), Y(12.5), X(19), Y(6.5), SPEC["height"], SPEC["height"] + 0.035, mat=3)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    lib.export_assembly(ROOT, obj, layout, argv, 48, 28)


if __name__ == "__main__":
    main()
