"""Muzzle cap of the big blue gun (newshc.shp frame 275, a 1x1 sprite): a 3D version of it.

Seen in episode 1 (level 1.19) and 3 (level 3.23), at the right end of the big gun
(assembly-newshc-271). It is the end of the gun's muzzle block: a rounded blue block (columns 0-4,
rows 2-8), lighter on top, with a short nozzle under it (columns 2-4, rows 9-11) and the tail of
the red glow at its left edge. Built at the same height and size as the muzzle in
assembly-newshc-271 so they line up. One frame.

Run: blender --background --python assets/blender/enemies/newshc-275.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "newshc-275"
ROOT = common.repo_root(__file__)
XY = (12, 14)
DZ = -0.5  # as in assembly-newshc-271


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(57, metallic=0.45, roughness=0.4),  # 0 muzzle block
        pal(59, metallic=0.5, roughness=0.3),  # 1 pale top edge
        pal(55, metallic=0.4, roughness=0.45),  # 2 nozzle
        pal(114, emission_strength=3.0),  # 3 red glow
    ]
    BLOCK, PALE, NOZZLE, GLOW = range(4)
    bm = bmesh.new()
    # Muzzle block, rounded off at its end (columns 0-4, rows 2-8).
    lib.loft_x(bm, 5.2, [(0.0, 3.4, 2.4, 1.0 + DZ), (3.6, 3.4, 2.4, 1.0 + DZ), (4.6, 2.9, 2.0, 1.0 + DZ),
                         (5.0, 1.8, 1.2, 1.0 + DZ)], sides=12, mat=BLOCK, power=0.6, cap_start=False, xy=XY)
    lib.loft_x(bm, 3.4, [(0.0, 0.5, 0.35, 3.0 + DZ), (3.4, 0.5, 0.35, 3.0 + DZ), (3.9, 0.0, 0.0, 2.8 + DZ)],
               sides=6, mat=PALE, xy=XY)
    # Nozzle under it (columns 2-4, rows 9-11).
    lib.loft_y(bm, 3.6, [(8.0, 1.4, 1.2, 0.0 + DZ), (11.4, 1.4, 1.2, 0.0 + DZ), (12.0, 0.9, 0.8, 0.0 + DZ)],
               sides=10, mat=NOZZLE, xy=XY)
    # The tail of the red glow (column 0, row 10).
    lib.ellipsoid(bm, 0.6, 10.5, -0.2 + DZ, 1.0, 0.8, 0.9, mat=GLOW, segments=8, rings=4, xy=XY)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run_single(ROOT, NAME, build)


if __name__ == "__main__":
    main()
