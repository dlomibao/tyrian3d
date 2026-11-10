"""Small grey-blue asteroid (newshd.shp frame 95, 12x14 px): a 3D version of its sprite.

A weathered, fractured boulder: a round body traced to the sprite's inner mask (inside its ink ring,
D74), its top raised into the summit and the two lit ridges the sprite draws (the bright streak from
the upper-left down to the centre, and the softer one running down the lower-left), then broken by
planar fracture faces (crisp, chamfered edges, the faces the sprite's highlights are on: on rock a
highlight is a lit face, not sheen), one fracture crack across the shadowed right flank and a few
small impact pits. One matte material, the sprite's blue-grey mid-tone pal_104 (the median of its
rock pixels; the dark grey limb, black ring and white streak are its lighting). AO/roughness bake
only (no concept projection), outline shell (D51). Underside: a closed, plainer shape.

The rock is built by lib_newshd_rock from this spec (summit, ridges, heights, cuts, cracks, pits), as
the rest of the newshd asteroid family (newshd-152/-114/-133/-5/-18/-43) is from its own sprite.

    blender -b --factory-startup -P assets/blender/enemies/newshd-95.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-95.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshd-95"

SPEC = {
    "mid": 104,             # rock mid-tone: median of the sprite's blue-grey rock pixels
    "h_top": 0.44,          # summit height above the rim (units; 12 px = 1 unit)
    "h_bot": 0.27,          # depth of the underside below the rim
    "summit": (5.4, 6.3),   # sprite px (column, row), the brightest pixel (110) and its peak
    # Ridges from the summit (sprite px end point, height gain, width px): the lit streak up to the
    # upper-left and the softer lit spur down the lower-left.
    "ridges": [((2.6, 2.6), 0.20, 1.5), ((3.4, 9.8), 0.12, 1.4)],
    "summit_gain": 0.16,
    "tilt": 0.10,           # how far the shadowed right side falls away (fraction of h_top)
    "lumps": 0.06,
    "grow": 0.15,           # px the body is grown past the inner mask, for the rim spalls to cut back
    "waist": 0.09,          # how far the widest line wanders in height (units)
    "seed": 95,
    "fine": 14,             # extra small fracture faces (fine_cuts)
    # Fracture faces: (azimuth deg, elevation deg, depth fraction). Azimuth 0 = +X (screen right),
    # 90 = +Y (screen up).
    "cuts": [
        # the crest: two faces meeting along the sprite's lit streak (summit -> upper-left); the
        # one below-left of it turns to the game's sun (left, screen bottom), the other falls away
        (215, 44, 0.22), (35, 40, 0.22),
        # the lower-left spur's two faces, then the summit's other flanks
        (150, 50, 0.14), (330, 48, 0.14),
        (250, 52, 0.12), (95, 46, 0.12), (125, 60, 0.10), (60, 64, 0.10),
        (185, 66, 0.08), (275, 70, 0.08), (10, 55, 0.10), (300, 40, 0.12),
        # shoulder spalls round the rim (shallow, so the outline holds)
        (140, 24, 0.035), (230, 22, 0.035), (320, 24, 0.035), (50, 22, 0.035),
        # underside: a few broad planes so it reads as stone, nothing more
        (30, -68, 0.10), (150, -62, 0.10), (260, -70, 0.09), (95, -82, 0.05),
        (200, -24, 0.04), (320, -22, 0.04), (80, -26, 0.04),
    ],
    # Crack: polyline in sprite px, groove width / depth in units.
    "cracks": [([(7.0, 2.3), (7.6, 4.6), (7.2, 6.6), (8.3, 8.9), (8.0, 10.6)], 0.022, 0.03)],
    # Pits: sprite px centre, radius units.
    "pits": [],
    # its shell and bake as built in D121 (0.012 voxels from the closed rock, which stays in the
    # scene during the bake), kept so its glb is unchanged; the rest of the family uses D90's shell
    # from a copy kept out of the bake (D118)
    "shell": {"voxel": 0.012, "faces": 1200, "smooth": 8},
    "bake_with_copy": True,
}


if __name__ == "__main__":
    lib.main(NAME, SPEC)
