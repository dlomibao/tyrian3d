"""Blue eye orb (newsh5.shp frame 270): a 3D version of its sprite.

Seen in episode 4 (level 4.25). A round, glossy, pale blue ball, 21 px across, with a big blue
iris bulging out of its lower half: a dark ring round a near-black pupil, and a white glint at
the iris's upper left. The upper half catches a broad white highlight. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-270.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402
from lib_b030 import PX, px, row  # noqa: E402

NAME = "newsh5-270"
CX, CY = px(12), row(12)  # the ball's centre (columns and rows 2-22)
R = 10.3 * PX  # radius across the screen
RZ = 3.6 * PX  # half height (kept low: a flier at most ~0.6 tall)


def ball_z(x, y):
    d = ((x - CX) ** 2 + (y - CY) ** 2) / (R * R)
    return RZ * math.sqrt(max(0.0, 1 - d))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(62, metallic=0.2, roughness=0.15),  # 0 pale blue ball
        pal(56, metallic=0.3, roughness=0.2),  # 1 blue iris
        pal(53, metallic=0.2, roughness=0.3),  # 2 dark iris ring
        pal(51, metallic=0.1, roughness=0.15),  # 3 pupil
        pal(63, metallic=0.0, roughness=0.1, emission_strength=2.0),  # 4 glint
        pal(59, metallic=0.3, roughness=0.2),  # 5 iris rim
    ]
    BALL, IRIS, RING, PUPIL, GLINT, RIM = range(6)
    bm = bmesh.new()
    lib.ellipsoid(bm, CX, CY, 0.0, R, R, RZ, mat=BALL, segments=32, rings=14)

    # The iris (columns 4-21, rows 10-21), centred low on the ball, and its layers.
    ix, iy = px(12.6), row(15.6)
    lib.surface_cap(bm, ix, iy, 8.0 * PX, 6.2 * PX, ball_z, bulge=0.6 * PX, mat=RIM, rings=3, segments=20)
    iris_z = lambda x, y: ball_z(x, y) + 0.6 * PX * max(0.0, 1 - ((x - ix) / (8.0 * PX)) ** 2  # noqa: E731
                                                       - ((y - iy) / (6.2 * PX)) ** 2)
    lib.surface_cap(bm, ix, iy, 7.0 * PX, 5.4 * PX, iris_z, bulge=0.3 * PX, mat=IRIS, rings=3, segments=20)
    lift_z = lambda x, y: iris_z(x, y) + 0.3 * PX  # noqa: E731
    lib.surface_cap(bm, px(12.8), row(15.8), 4.4 * PX, 3.8 * PX, lift_z, bulge=0.1 * PX, mat=RING, rings=2,
                    segments=16)
    lib.surface_cap(bm, px(13.0), row(15.6), 2.4 * PX, 2.6 * PX, lambda x, y: lift_z(x, y) + 0.12 * PX,
                    bulge=0.1 * PX, mat=PUPIL, rings=2, segments=12)
    lib.surface_cap(bm, px(10.6), row(12.6), 1.4 * PX, 1.1 * PX, lambda x, y: lift_z(x, y) + 0.05 * PX,
                    bulge=0.15 * PX, mat=GLINT, rings=2, segments=10)
    return lib.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)
