"""Small grey-blue stone (newshd.shp frame 133, 12x14 px block, an 11 x 12 px rock): a 3D version of
its sprite.

A round, chipped boulder floating in space, traced to the sprite's inner mask (inside its ink ring,
D74), its upper right cut in. The sprite draws one lit streak from just right of the middle down to
the lower left, a softer lit patch upper left, the upper right in shadow and the right side
darker. So the summit stands right of the middle with a ridge running from it down-left, cut by
fracture faces turned to the light (on rock a highlight is a lit face, not sheen), a smaller lump
upper left, and the upper right and right falling away. Its underside is a plain closed dome with
a few planes. One matte material, the sprite's blue-grey mid-tone pal_103 (the trimmed median of
its rock pixels; its ink ring, dark limb and pale glints are lighting). AO/roughness bake only, D90
outline shell.

    blender -b --factory-startup -P assets/blender/enemies/newshd-133.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-133.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshd-133"

# Sprite coordinates are pixel edges: pixel (c, r) spans c..c+1, r..r+1.
SPEC = {
    "metallic": 0.0,
    "roughness": 0.9,       # matte stone: its lit faces read by their angle, no glint
    "mid": 103,
    "h_top": 0.44,
    "h_bot": 0.36,
    "rise": 0.7,
    "fall": 0.8,
    "summit": (5.4, 5.6),
    "summit_gain": 0.12,
    # the lit streak from the summit down to the lower left
    "ridges": [((3.4, 8.7), 0.30, 1.2)],
    # the softer lit patch upper left; the shadowed upper right sinks
    "bumps": [((3.0, 4.4), 0.21, 1.3), ((6.8, 3.4), -0.21, 1.5)],
    "crests": [],
    "tilt": 0.12,
    "lumps": 0.04,
    "grow": 0.15,
    "waist": 0.08,
    "seed": 133,
    "fine": 14,
    "rim_spalls": 10,
    "cuts": [
        # the streak's two faces: the lit one to the lower left, the other falling right
        (200, 46, 0.12), (20, 42, 0.14),
        # the lit upper-left patch, and the summit's other flanks
        (140, 50, 0.08), (90, 58, 0.08), (320, 52, 0.10), (270, 60, 0.07), (60, 50, 0.08),
        # shoulder spalls
        (150, 22, 0.035), (235, 24, 0.035), (320, 22, 0.035), (45, 24, 0.035),
        # underside: a few planes so it reads as stone, nothing more, and no flat base
        (30, -55, 0.06), (150, -50, 0.06), (260, -58, 0.06), (100, -64, 0.05),
        (200, -28, 0.04), (320, -26, 0.04), (80, -30, 0.04),
    ],
    "cracks": [],
    "pits": [((7.0, 8.2), 0.06)],
    "pit_lift": 0.6,
}


if __name__ == "__main__":
    lib.main(NAME, SPEC)
