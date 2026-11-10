"""Large grey asteroid (newshd.shp frame 43, a 24 x 23 px rock in its 24x28 block): a 3D version of
its sprite.

A big three-lobed rock floating in space, round all over, traced to the sprite's inner mask
(inside its ink ring, D74): a lobe reaching up to the upper right, a broad one on the left and one
below, with a notch in its right side between the upper and lower lobes. The sprite draws a bright
ridge running down the upper lobe from its upper right towards the middle, a bright cluster low in
the middle, a lit left lobe, and dark creases between the lobes: one from the left under the upper
lobe across to the notch, one between the left and lower lobes. So the top rises to the cluster
low in the middle and carries the upper lobe's ridge and the other lobes as lumps, all cut by
fracture faces turned to the light (on rock a highlight is a lit face, not sheen), with the creases
(a fine crack in the long one) and two pits cut in. Its underside is a plain closed dome with a few
planes. One matte material, the sprite's grey mid-tone pal_7 (the trimmed median of its rock greys;
its ink ring, dark limb and near-white glints are lighting). AO/roughness bake only, D90 outline
shell.

    blender -b --factory-startup -P assets/blender/enemies/newshd-43.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-43.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshd-43"

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
    "smooth": 1,               # keep the notch in the right side
    "summit": (11.4, 13.6),    # the bright cluster low in the middle
    "summit_gain": 0.10,
    "summit_r": 2.8,
    "ridges": [],
    "bumps": [((6.4, 11.2), 0.30, 2.4),     # the lit left lobe
              ((14.6, 18.4), 0.24, 2.4),    # the lower lobe
              ((13.4, 5.4), 0.21, 2.2)],    # the upper lobe's crown
    # the bright ridge down the upper lobe
    "crests": [((14.8, 6.0), (11.6, 9.4), 0.42, 1.2)],
    # the crease from the left under the upper lobe across to the notch, and the one between the
    # left and lower lobes
    "valleys": [([(7.4, 8.4), (9.6, 10.4), (13.0, 11.2), (17.6, 10.6)], -0.18, 1.0),
                ([(3.6, 15.8), (6.4, 14.6), (8.4, 13.4)], -0.12, 1.0)],
    "tilt": 0.05,
    "lumps": 0.04,
    "grow": 0.3,
    "steps": 144,           # a finer outline trace for the big rock
    "waist": 0.12,
    "seed": 43,
    "fine": 48,
    "fine_depth": (0.02, 0.04),
    "rim_spalls": 18,
    "rim_depth": (0.015, 0.025),
    "cuts": [
        # the crown, broken into a few near-level faces so it never closes to a point
        (160, 78, 0.035), (20, 80, 0.03), (260, 82, 0.03), (100, 76, 0.035),
        # the lit faces of the ridge, the cluster and the lobes, turned to the light
        (150, 46, 0.07), (205, 44, 0.07), (178, 62, 0.045), (125, 56, 0.05), (232, 52, 0.05),
        # the shadowed flanks
        (10, 46, 0.07), (45, 58, 0.05), (80, 50, 0.06), (330, 46, 0.07), (300, 60, 0.05),
        (265, 50, 0.05), (350, 64, 0.04),
        # shoulder spalls
        (140, 22, 0.02), (195, 24, 0.02), (240, 22, 0.02), (290, 24, 0.02), (340, 22, 0.02),
        (30, 24, 0.02), (85, 22, 0.02),
        # underside: a few planes so it reads as stone, nothing more, and no flat base
        (30, -55, 0.05), (150, -50, 0.05), (260, -58, 0.05), (100, -64, 0.04),
        (200, -28, 0.03), (320, -26, 0.03), (80, -30, 0.03),
    ],
    "cracks": [([(10.2, 10.6), (12.0, 11.0), (13.8, 11.1), (15.6, 10.8)], 0.03, 0.035)],
    "pits": [((14.6, 3.6), 0.07), ((5.6, 8.8), 0.06), ((15.8, 15.4), 0.06), ((9.6, 18.6), 0.05)],
    "pit_lift": 0.55,
}


if __name__ == "__main__":
    lib.main(NAME, SPEC)
