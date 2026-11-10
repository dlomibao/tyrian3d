"""Small grey-blue asteroid (newshd.shp frame 152, 12x14 px): a 3D version of its sprite.

A round, fractured boulder floating in space, traced to the sprite's inner mask (inside its ink
ring, D74). The sprite draws three lit facets, the upper-left one, a strip down the upper right
and the lower-left one, with a darker crease down the middle between the two upper ones and a dark
pit below the strip; the lower right is in shadow. So its top carries three lumps where the lit
facets are, each cut flat by a fracture face turned to the light (on rock a highlight is a lit
face, not sheen), a shallow crease groove between them, the pit cut in, and the top falling away
to the lower right. Its underside is a plain closed dome with a few broad planes. One matte
material, the sprite's blue-grey mid-tone pal_104 (the trimmed median of its rock pixels; its ink
ring, dark limb and near-white glints are lighting). AO/roughness bake only, D90 outline shell.

    blender -b --factory-startup -P assets/blender/enemies/newshd-152.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-152.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshd-152"

# Sprite coordinates are pixel edges: pixel (c, r) spans c..c+1, r..r+1.
SPEC = {
    "metallic": 0.0,
    "roughness": 0.9,       # matte stone: its lit faces read by their angle, no glint
    "mid": 104,
    "h_top": 0.44,
    "h_bot": 0.36,
    "fall": 0.8,            # a rounder underside: the bottom dome closes without a flat base
    "rise": 0.7,            # a rounder dome than the default
    "summit": (6.3, 5.8),
    "summit_gain": 0.04,
    "ridges": [],
    # the three lit facets stand up as lumps: upper-left patch, upper-right strip, lower-left patch
    "bumps": [((4.6, 3.4), 0.45, 1.5), ((4.8, 9.0), 0.42, 1.6),
              ((8.6, 10.6), -0.21, 1.8)],   # the shadowed lower right sinks
    "crests": [((8.0, 3.4), (8.1, 6.8), 0.45, 1.0),
               # the crease down the middle between the upper facets
               ((6.4, 1.6), (6.5, 7.0), -0.24, 0.7)],
    "tilt": 0.10,
    "lumps": 0.04,
    "grow": 0.15,
    "waist": 0.08,
    "seed": 152,
    "fine": 16,
    "rim_spalls": 10,
    "cuts": [
        # the lit facets, each a face turned to the light (left / upper-left / lower-left)
        (150, 46, 0.10), (205, 44, 0.10), (178, 56, 0.07),
        # the strip's top and the shadowed right and lower-right flanks
        (95, 58, 0.07), (15, 44, 0.12), (335, 46, 0.12), (290, 60, 0.07),
        (245, 62, 0.06), (55, 60, 0.07),
        # shoulder spalls round the rim (shallow, so the outline holds)
        (140, 22, 0.035), (230, 24, 0.035), (320, 22, 0.035), (45, 24, 0.035),
        # underside: a few planes so it reads as stone, nothing more, and no flat base
        (30, -55, 0.06), (150, -50, 0.06), (260, -58, 0.06), (100, -64, 0.05),
        (200, -28, 0.04), (320, -26, 0.04), (80, -30, 0.04),
    ],
    # a fine crack along the crease
    "cracks": [([(6.4, 1.8), (6.5, 3.6), (6.3, 5.4), (6.6, 6.8)], 0.03, 0.03)],
    # the dark pit below the strip
    "pits": [((7.6, 8.6), 0.07)],
    "pit_lift": 0.6,
}


if __name__ == "__main__":
    lib.main(NAME, SPEC)
