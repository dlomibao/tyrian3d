"""Gold beetle fighter (newshf.shp frames 85, 87, 89): a 3D version of its sprite.

Seen in episodes 1 and 3. It flies tail point down the screen: a broad gold-brown body on a
narrow neck, a pale stinger at the back flanked by two small grey horns, two claws sweeping
back from the body's shoulders with grey blades on their inner edges, two pale blue-grey lights
on the back and a dark mouth with a pale fang. The frames rock it side to side (85 rolled with its
right side up, 87 level, 89 left side up: the claws close in a pixel and the stinger leans a
pixel), so each frame gets the level model turned about its long axis (newshf-85, -f2, -f3).

Run: blender --background --python assets/blender/enemies/newshf-85.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402
from lib_b023 import common, ey, px  # noqa: E402

NAME = "newshf-85"
P = 1 / 12
X0 = px(13)  # the level frame is symmetric about column 13
ROLL = math.radians(26)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lib.palette(sprite, NAME)
    mats = [
        pal(25, metallic=0.35, roughness=0.4),  # 0 gold-brown body
        pal(28, metallic=0.35, roughness=0.35),  # 1 pale ridge and stinger
        pal(27, metallic=0.35, roughness=0.4),  # 2 claws
        pal(10, metallic=0.6, roughness=0.35),  # 3 grey blades and horns
        pal(8, metallic=0.6, roughness=0.4),  # 4 grey neck sides
        pal(109, metallic=0.3, roughness=0.2, emission_strength=2.0),  # 5 pale lights
        pal(16, metallic=0.3, roughness=0.15),  # 6 dark mouth
        pal(30, metallic=0.2, roughness=0.4),  # 7 pale fang
    ]
    BODY, RIDGE, CLAW, BLADE, NECK, LIGHT, MOUTH, FANG = range(8)
    bm = bmesh.new()

    # Body: narrow neck (rows 5-10), broad back (rows 12-16), tapering to the tail point (row 25).
    body = [(4.6, 0.0, 0.0), (5.0, 1.6, 1.0), (5.6, 2.4, 1.5), (7.6, 2.4, 1.6), (8.2, 1.6, 1.5),
            (9.6, 1.7, 1.6), (10.4, 2.5, 1.9), (11.5, 3.6, 2.2), (13.0, 5.0, 2.5), (14.5, 5.5, 2.6),
            (16.0, 5.0, 2.5), (17.5, 4.4, 2.3), (18.5, 3.6, 2.1), (20.0, 2.8, 1.8), (21.6, 2.4, 1.5),
            (22.4, 1.6, 1.2), (23.8, 1.4, 1.0), (24.6, 0.6, 0.5), (25.0, 0.0, 0.0)]
    lib.ellipse_loft(bm, X0, [(ey(r), w * P, h * P, 0.0) for r, w, h in body], sides=12, mats=BODY)
    # Pale ridge down the back (rows 8-16).
    lib.ellipse_loft(bm, X0, [(ey(r), w * P, 0.35 * P, z) for r, w, z in
                              ((8.0, 0.0, 0.12), (8.6, 0.7, 0.13), (14.5, 0.9, 0.215), (16.2, 0.0, 0.2))],
                     sides=6, mats=RIDGE)
    # Stinger at the back (column 13, rows 1-5).
    lib.polyline_tube(bm, [(X0, ey(6.0), 0.08), (X0, ey(3.5), 0.13), (X0, ey(1.2), 0.17)],
                      [0.8 * P, 0.6 * P, 0.0], sides=6, mat_index=RIDGE)
    # Dark mouth with a pale fang (rows 17-20).
    lib.dome(bm, X0, ey(18.7), 0.12, 1.5 * P, 1.9 * P, 0.07, mat_index=MOUTH, segs=10, rings=3)
    lib.polyline_tube(bm, [(X0, ey(17.6), 0.19), (X0, ey(18.6), 0.185), (X0, ey(19.6), 0.16)],
                      [0.5 * P, 0.45 * P, 0.0], sides=6, mat_index=FANG)

    # Left claw, its grey blade, horn, neck side and light; then mirrored about column 13.
    start = len(bm.verts)
    lib.polyline_tube(bm, [(px(10.0), ey(13.4), 0.02), (px(8.0), ey(12.0), 0.04), (px(6.8), ey(10.0), 0.06),
                           (px(6.4), ey(8.2), 0.07), (px(6.5), ey(6.6), 0.08)],
                      [1.8 * P, 1.5 * P, 1.1 * P, 0.7 * P, 0.0], sides=8, mat_index=CLAW, flat=0.7)
    lib.polyline_tube(bm, [(px(10.6), ey(11.6), 0.1), (px(9.0), ey(10.4), 0.09), (px(8.1), ey(8.8), 0.08)],
                      [0.7 * P, 0.6 * P, 0.0], sides=6, mat_index=BLADE)
    lib.polyline_tube(bm, [(px(11.4), ey(6.2), 0.06), (px(10.6), ey(4.8), 0.08), (px(10.0), ey(3.4), 0.1)],
                      [0.7 * P, 0.55 * P, 0.0], sides=6, mat_index=BLADE)
    lib.polyline_tube(bm, [(px(11.1), ey(5.4), 0.05), (px(11.2), ey(7.8), 0.06)], 0.65 * P, sides=6,
                      mat_index=NECK)
    lib.dome(bm, px(12), ey(12.0), 0.15, 0.65 * P, 1.0 * P, 0.06, mat_index=LIGHT, segs=8, rings=3, full=True)
    lib.mirror_x(bm, X0, start)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return lib.rocking_models(NAME, sprite, [obj], X0, [-ROLL, 0.0, ROLL], coll)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
