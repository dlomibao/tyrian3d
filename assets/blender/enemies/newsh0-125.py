"""Blue eye pod (newsh0.shp frames 125, 127, 131): a 3D version of its sprite.

A ground emplacement in episode 2 (levels 21 and 22): a blue steel shell in two rounded halves,
split by a groove down the middle, with a red eye set in a dark socket between them. A slim
armour pod hugs each side, joined by two bolts, and two short feet stick out at the bottom. The
frames only open the eye wider and brighter, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newsh0-125.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b104 as lib  # noqa: E402
from lib_b104 import common, px, row  # noqa: E402

NAME = "newsh0-125"
CX = px(12)  # symmetric about column 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(50, metallic=0.4, roughness=0.6),  # 0 dark plinth and socket
        pal(54, metallic=0.55, roughness=0.4),  # 1 shell lower wall
        pal(57, metallic=0.6, roughness=0.35),  # 2 shell
        pal(60, metallic=0.65, roughness=0.3),  # 3 shell crown highlight
        pal(59, metallic=0.6, roughness=0.35),  # 4 side pods
        pal(53, metallic=0.5, roughness=0.45),  # 5 bolts
        pal(58, metallic=0.55, roughness=0.4),  # 6 feet
        pal(116, metallic=0.2, roughness=0.3, emission_strength=2.5),  # 7 red eye
        pal(122, emission_strength=4.0),  # 8 orange pupil
        pal(124, emission_strength=5.0),  # 9 yellow core
    ]
    DARK, LOW, SHELL, CROWN, POD, BOLT, FOOT, EYE, PUPIL, CORE = range(10)
    bm = bmesh.new()

    def mx(x):
        return 2 * CX - x

    # Dark plinth under everything, so the seams between the parts read dark (columns 5-19, rows 7-17).
    lib.stack(bm, CX, row(12), [(0.0, 7.4 / 12, 5.0 / 12, 3.0), (0.06, 7.4 / 12, 5.0 / 12, 3.0)], n=20, mats=DARK)

    # The two shell halves (columns 7-11 and 13-17, rows 7-16): tall rounded lobes meeting in a groove.
    for side in (-1, 1):
        cx = CX + side * 3.3 / 12
        lib.stack(bm, cx, row(11.6), [
            (0.0, 3.0 / 12, 5.2 / 12, 3.2),
            (0.10, 3.0 / 12, 5.2 / 12, 3.2),
            (0.18, 2.8 / 12, 4.9 / 12, 2.8, 0.0, 0.01),
            (0.25, 2.2 / 12, 4.1 / 12, 2.2, 0.0, 0.02),
            (0.29, 1.5 / 12, 3.0 / 12, 2.0, 0.0, 0.03),
            (0.31, 0.0, 0.0, 2.0, 0.0, 0.03),
        ], n=18, mats=[LOW, SHELL, SHELL, CROWN, CROWN])

    # Side pods (columns 5-6 and 18-19, rows 9-16), each a long rounded pad.
    for x in (px(5.6), mx(px(5.6))):
        lib.dome(bm, x, row(12.5), 0.0, 1.35 / 12, 4.0 / 12, 0.1, n=14, steps=3, p=2.4, base=0.1, mats=POD)
        # Bolts joining it to the shell (column 7, rows 11 and 13).
        for r in (11, 13):
            xi = px(7) if x < CX else mx(px(7))
            lib.tube(bm, (xi - 0.7 / 12, row(r), 0.13), (xi + 0.7 / 12, row(r), 0.13), 0.45 / 12, sides=6,
                     mat_index=BOLT)

    # Feet (column 7 / 17, rows 16-18) angled down and out.
    for side in (-1, 1):
        x0, x1 = CX + side * 4.9 / 12, CX + side * 5.1 / 12
        lib.tube(bm, (x0, row(15.4), 0.08), (x1, row(17.9), 0.04), 0.8 / 12, sides=6, mat_index=FOOT, r1=0.6 / 12)

    # The eye: a dark socket between the halves (columns 10-14, rows 9-16) with a red dome in it.
    lib.stack(bm, CX, row(12.5), [(0.05, 2.9 / 12, 3.7 / 12, 2.4), (0.22, 2.9 / 12, 3.7 / 12, 2.4),
                                  (0.24, 2.5 / 12, 3.3 / 12, 2.4)], n=16, mats=DARK)
    lib.dome(bm, CX, row(12.6), 0.2, 2.2 / 12, 2.8 / 12, 0.15, n=16, steps=4, mats=EYE)
    lib.dome(bm, CX, row(12.9), 0.3, 1.2 / 12, 1.5 / 12, 0.06, n=12, steps=3, mats=PUPIL)
    lib.dome(bm, CX, row(13.0), 0.345, 0.6 / 12, 0.7 / 12, 0.03, n=10, steps=2, mats=CORE)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
