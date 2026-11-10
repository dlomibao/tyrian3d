"""Large grey asteroid (newshd.shp frame 5, a 22 x 20 px rock in its 24x28 block): a 3D version of
its sprite.

A big, round, fractured rock floating in space, traced to the sprite's inner mask (inside its ink
ring, D74). The sprite draws a bright mass in the upper middle with a small dark pit at its upper
left, a second bright lobe on the right, a lit patch on the left and a smaller lit lobe low in the
middle; a dark crack runs in from the left edge under the big mass, another down between the big
mass and the right lobe, and the lower left and lower right are in shadow. So the top rises to
the big mass and carries the lobes as lumps, all cut by fracture faces turned to the light (on
rock a highlight is a lit face, not sheen), with the two creases and their fine cracks and two
impact pits cut in, and falls away into the shadowed lower flanks. Its underside is a plain
closed dome with a few planes. One matte material, the sprite's grey mid-tone pal_7 (the trimmed
median of its rock greys; its ink ring, dark limb and near-white glints are lighting). AO/roughness
bake only, D90 outline shell. newshd-18 is this rock with a glowing vent and builds from this SPEC.

    blender -b --factory-startup -P assets/blender/enemies/newshd-5.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-5.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshd-5"

# Sprite coordinates are pixel edges: pixel (c, r) spans c..c+1, r..r+1 (24x28 block).
SPEC = {
    "metallic": 0.0,
    "roughness": 0.9,       # matte stone: its lit faces read by their angle, no glint
    "mid": 7,
    "h_top": 0.7,
    "h_bot": 0.52,
    "rise": 0.7,
    "fall": 0.8,
    "sectors": 96,
    "rings_top": 20,
    "rings_bot": 10,
    "summit": (11.4, 8.4),     # the bright upper-middle mass
    "summit_gain": 0.10,
    "summit_r": 3.2,
    "ridges": [],
    "bumps": [((18.4, 8.6), 0.42, 2.4),     # the bright right lobe
              ((7.2, 10.0), 0.27, 2.0),     # the lit patch on the left
              ((12.6, 13.6), 0.27, 2.2),    # the lit lobe low in the middle
              ((5.6, 6.4), 0.15, 1.8),      # the lit upper-left corner
              ((17.6, 15.6), -0.24, 3.0),   # the shadowed lower right
              ((8.0, 15.2), -0.18, 2.6)],   # and lower left
    "crests": [],
    # the crack in from the left edge under the big mass, and the one down between it and the
    # right lobe
    "valleys": [([(3.6, 13.4), (7.0, 12.2), (10.4, 11.4), (13.6, 10.8)], -0.15, 1.0),
                ([(14.4, 3.6), (14.6, 6.6), (15.2, 9.8)], -0.14, 0.9)],
    "tilt": 0.05,
    "lumps": 0.04,
    "grow": 0.3,
    "smooth": 1,
    "steps": 144,           # a finer outline trace for the big rock
    "waist": 0.12,
    "seed": 5,
    "fine": 48,
    "fine_depth": (0.02, 0.04),
    "rim_spalls": 18,
    "rim_depth": (0.015, 0.025),
    "cuts": [
        # the crown, broken into a few near-level faces so it never closes to a point
        (160, 78, 0.035), (20, 80, 0.03), (260, 82, 0.03), (100, 76, 0.035),
        # the lit faces of the big mass and the lobes, turned to the light (left / upper-left /
        # lower-left)
        (150, 46, 0.07), (205, 44, 0.07), (178, 62, 0.045), (125, 56, 0.05), (232, 52, 0.05),
        # the shadowed right, upper-right and lower-right flanks
        (10, 46, 0.07), (40, 58, 0.05), (75, 50, 0.06), (330, 46, 0.07), (300, 60, 0.05),
        (265, 50, 0.05), (350, 64, 0.04),
        # shoulder spalls
        (140, 22, 0.02), (195, 24, 0.02), (240, 22, 0.02), (290, 24, 0.02), (340, 22, 0.02),
        (30, 24, 0.02), (85, 22, 0.02),
        # underside: a few planes so it reads as stone, nothing more, and no flat base
        (30, -55, 0.05), (150, -50, 0.05), (260, -58, 0.05), (100, -64, 0.04),
        (200, -28, 0.03), (320, -26, 0.03), (80, -30, 0.03),
    ],
    "cracks": [([(4.4, 13.2), (6.2, 12.5), (8.2, 11.9), (10.0, 11.5)], 0.03, 0.035),
               ([(14.5, 4.4), (14.6, 6.4), (15.0, 8.6)], 0.03, 0.03)],
    # the dark pit at the big mass's upper left and the smaller dark spots
    "pits": [((9.0, 4.8), 0.10), ((15.0, 16.4), 0.07), ((20.4, 6.0), 0.06), ((7.6, 13.6), 0.06),
             ((15.6, 12.2), 0.05)],
    "pit_lift": 0.55,
}


if __name__ == "__main__":
    lib.main(NAME, SPEC)
