"""Small grey-blue asteroid (newshd.shp frame 114, 12x14 px): a 3D version of its sprite.

A round, fractured boulder floating in space, traced to the sprite's inner mask (inside its ink
ring, D74): an egg leaning from the upper right down to the lower left. The sprite draws two lit
facet clusters, a strip from the upper middle down to the right and a broad patch lower left, with
a dark crack running between them from the left edge across to the right, and its lower right in
shadow. So its top carries a crest and a lump where the lit clusters are, each cut flat by fracture
faces turned to the light (on rock a highlight is a lit face, not sheen), a crease with a fine crack
in it between them, and falls away to the lower right. Its underside is a plain closed dome with a
few planes. One matte material, the sprite's blue-grey mid-tone pal_104 (the trimmed median of its
rock pixels; its ink ring, dark limb and pale glints are lighting). AO/roughness bake only, D90
outline shell.

    blender -b --factory-startup -P assets/blender/enemies/newshd-114.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-114.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshd-114"

# Sprite coordinates are pixel edges: pixel (c, r) spans c..c+1, r..r+1.
SPEC = {
    "metallic": 0.0,
    "roughness": 0.9,       # matte stone: its lit faces read by their angle, no glint
    "mid": 104,
    "h_top": 0.44,
    "h_bot": 0.36,
    "rise": 0.7,
    "fall": 0.8,
    "summit": (7.6, 5.2),
    "summit_gain": 0.04,
    "ridges": [],
    # the lower-left lit patch, and the shadowed lower right sinking
    "bumps": [((5.2, 8.9), 0.42, 1.6), ((8.6, 10.4), -0.21, 1.7)],
    "crests": [((6.6, 4.4), (8.5, 7.3), 0.42, 1.0),          # the upper lit strip
               # the crease between the clusters, left edge to right edge
               ((3.8, 6.6), (9.8, 8.6), -0.17, 1.0)],
    "tilt": 0.10,
    "lumps": 0.04,
    "grow": 0.15,
    "waist": 0.08,
    "seed": 114,
    "fine": 16,
    "rim_spalls": 10,
    "cuts": [
        # the lit faces, turned to the light (left / upper-left / lower-left)
        (160, 46, 0.10), (210, 44, 0.10), (130, 56, 0.07),
        # the strip's top and the shadowed right and lower-right flanks
        (70, 56, 0.07), (10, 44, 0.12), (330, 46, 0.12), (285, 60, 0.07), (245, 62, 0.06),
        # shoulder spalls
        (140, 22, 0.035), (225, 24, 0.035), (315, 22, 0.035), (40, 24, 0.035),
        # underside: a few planes so it reads as stone, nothing more, and no flat base
        (30, -55, 0.06), (150, -50, 0.06), (260, -58, 0.06), (100, -64, 0.05),
        (200, -28, 0.04), (320, -26, 0.04), (80, -30, 0.04),
    ],
    # a fine crack along the crease
    "cracks": [([(4.0, 6.7), (5.0, 7.0), (6.0, 7.3)], 0.03, 0.03)],
    "pits": [],
}


if __name__ == "__main__":
    lib.main(NAME, SPEC)
