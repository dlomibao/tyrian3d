"""Clamped red core (newsh5.shp frame 166): a 3D version of its sprite.

Seen in episode 4 (level 4.22). It only fills the top half of its 24x28 block: a dark red, lumpy
mass glowing orange-yellow in places (a hot bar across its middle, spots on its left lobe), held
in a grey frame: a grey block at each top corner, pipes running in from them over the mass and a
dark grey bracket under its middle. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-166.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402
from lib_b030 import PX, ex, ey, px, row  # noqa: E402

NAME = "newsh5-166"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(115, metallic=0.2, roughness=0.45),  # 0 dark red mass
        pal(118, metallic=0.2, roughness=0.35),  # 1 red lobes
        pal(120, emission_strength=3.0),  # 2 orange glow
        pal(123, emission_strength=5.0),  # 3 yellow hot spots
        pal(104, metallic=0.7, roughness=0.35),  # 4 grey blocks
        pal(106, metallic=0.75, roughness=0.3),  # 5 light grey pipes
        pal(102, metallic=0.6, roughness=0.45),  # 6 dark grey bracket
        pal(114, metallic=0.1, roughness=0.6),  # 7 darker red folds
    ]
    MASS, LOBE, GLOW, HOT, BLOCK, PIPE, BRACKET, FOLD = range(8)
    bm = bmesh.new()

    # The red mass (columns 3-20, rows 0-13), rounded.
    before = len(bm.faces)
    common.loft(bm, [(ey(0.2), 0.0, 0.0, 0.0), (ey(0.4), 4.5 * PX, 1.6 * PX, 0.0), (ey(1.2), 8.0 * PX, 2.8 * PX, 0.0),
                     (ey(3.0), 9.2 * PX, 3.2 * PX, 0.0), (ey(9.0), 9.3 * PX, 3.2 * PX, 0.0),
                     (ey(11.8), 8.6 * PX, 2.9 * PX, 0.0), (ey(13.2), 7.4 * PX, 2.2 * PX, 0.0),
                     (ey(13.9), 4.5 * PX, 1.2 * PX, 0.0), (ey(14.0), 0.0, 0.0, 0.0)], sides=16)
    lib.tag_faces(bm, before, MASS, True)

    # Lobes: left (columns 3-9, rows 6-12), centre top (9-14, 0-8), right (14-20, 9-13), upper right.
    lib.ellipsoid(bm, px(6.0), row(8.6), 1.4 * PX, 3.6 * PX, 3.4 * PX, 2.6 * PX, mat=LOBE)
    lib.ellipsoid(bm, px(11.0), row(3.0), 1.6 * PX, 2.6 * PX, 3.2 * PX, 2.4 * PX, mat=LOBE)
    lib.ellipsoid(bm, px(17.6), row(11.0), 1.0 * PX, 3.0 * PX, 2.2 * PX, 2.4 * PX, mat=LOBE)
    lib.ellipsoid(bm, px(16.0), row(2.8), 1.4 * PX, 3.0 * PX, 2.0 * PX, 2.2 * PX, mat=FOLD)
    lib.ellipsoid(bm, px(7.5), row(3.6), 1.4 * PX, 1.6 * PX, 2.2 * PX, 2.2 * PX, mat=FOLD)
    # Glow: the hot bar across the middle (row 5, columns 10-14) and spots.
    lib.sausage(bm, [(px(10.2), row(5.2)), (px(14.0), row(5.2))], 1.0 * PX, 1.0 * PX, mat=GLOW,
                z_of=lambda x, y: 3.0 * PX)
    lib.ellipsoid(bm, px(10.2), row(5.0), 3.6 * PX, 0.9 * PX, 0.9 * PX, 0.6 * PX, mat=HOT, segments=8, rings=4)
    lib.ellipsoid(bm, px(5.3), row(7.6), 3.5 * PX, 1.4 * PX, 1.6 * PX, 0.9 * PX, mat=GLOW, segments=10, rings=5)
    lib.ellipsoid(bm, px(5.0), row(7.2), 4.0 * PX, 0.8 * PX, 0.9 * PX, 0.5 * PX, mat=HOT, segments=8, rings=4)
    lib.ellipsoid(bm, px(10.4), row(1.4), 2.8 * PX, 0.7 * PX, 1.0 * PX, 0.6 * PX, mat=GLOW, segments=8, rings=4)

    # Grey blocks at the top corners, reaching down the sides (columns 0-3 / 20-23, rows 0-8).
    lib.plate(bm, [(ex(0), ey(0)), (ex(4), ey(0)), (ex(4), ey(6)), (ex(3), ey(9)), (ex(1), ey(9)), (ex(0), ey(7))],
              -2.6 * PX, 3.4 * PX, mat=BLOCK)
    lib.plate(bm, [(ex(20), ey(0)), (ex(24), ey(0)), (ex(24), ey(7)), (ex(23), ey(9)), (ex(21), ey(9)),
                   (ex(20), ey(7))], -2.6 * PX, 3.4 * PX, mat=BLOCK)
    lib.plate(bm, [(ex(0.4), ey(0.3)), (ex(3.6), ey(0.3)), (ex(3.6), ey(2.0)), (ex(0.4), ey(2.0))],
              3.4 * PX, 4.0 * PX, mat=PIPE)
    lib.plate(bm, [(ex(20.4), ey(0.3)), (ex(23.6), ey(0.3)), (ex(23.6), ey(2.0)), (ex(20.4), ey(2.0))],
              3.4 * PX, 4.0 * PX, mat=PIPE)

    # Pipes over the mass: left, out of the block along row 5 and up column 6 to row 2, then right.
    flat = lambda z: (lambda x, y: z)  # noqa: E731
    lib.sausage(bm, [(px(3.5), row(5.2)), (px(6.2), row(5.2)), (px(6.4), row(2.4)), (px(8.6), row(2.2))],
                1.0 * PX, 0.9 * PX, mat=PIPE, z_of=flat(3.0 * PX))
    # Right: two pipes in along rows 5 and 7, the lower one bending down to the bracket along row 9.
    lib.sausage(bm, [(px(20.5), row(5.2)), (px(15.6), row(5.2))], 1.0 * PX, 0.9 * PX, mat=PIPE,
                z_of=flat(3.0 * PX))
    lib.sausage(bm, [(px(20.5), row(7.3)), (px(16.4), row(7.4)), (px(15.6), row(9.2)), (px(10.4), row(9.3))],
                1.0 * PX, 0.85 * PX, mat=PIPE, z_of=flat(2.8 * PX))
    # Dark grey bracket under the middle (columns 10-13, rows 9-14).
    lib.plate(bm, [(ex(9.6), ey(9.6)), (ex(14), ey(9.6)), (ex(14), ey(14)), (ex(12.5), ey(15)), (ex(9.6), ey(15))],
              -2.4 * PX, 2.2 * PX, mat=BRACKET)

    return lib.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)
