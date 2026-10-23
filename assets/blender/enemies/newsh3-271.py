"""Ringed turret (newsh3.shp frame 271): a 3D version of its sprite.

Seen in episode 4 (levels 4.10, 4.18 and 4.22), on the ground. A grey ring stands open in the
middle with a glossy blue dome hung in its upper half and the ground showing through below it;
a ribbed grey-and-blue barrel points up the screen from the top of the ring, two grey arms
reach out to the sides with short blue pins pointing forward, a light grey bar crosses the
bottom, and under it sits a blue block between grey cheeks with small blue pods at its corners.

Run: blender --background --python assets/blender/enemies/newsh3-271.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b076 as lib  # noqa: E402

NAME = "newsh3-271"
ROOT = common.repo_root(__file__)
F = lib.Frame(24, 28)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.7, roughness=0.35),  # 0 grey ring
        pal(6, metallic=0.7, roughness=0.4),  # 1 left arm (lit grey)
        pal(4, metallic=0.7, roughness=0.4),  # 2 right arm (shaded grey)
        pal(10, metallic=0.75, roughness=0.3),  # 3 light grey bar and rims
        pal(55, metallic=0.4, roughness=0.15),  # 4 blue dome
        pal(56, metallic=0.4, roughness=0.3),  # 5 blue block
        pal(53, metallic=0.4, roughness=0.35),  # 6 blue pods and pins
        pal(59, metallic=0.4, roughness=0.3),  # 7 light blue barrel ribs
        pal(61, metallic=0.3, roughness=0.2),  # 8 bright blue edge
        pal(5, metallic=0.7, roughness=0.4),  # 9 dark grey barrel ribs and cheeks
        pal(13, metallic=0.8, roughness=0.25),  # 10 bright grey highlights
        pal(62, metallic=0.3, roughness=0.1),  # 11 highlight on the dome
    ]
    RING, LARM, RARM, BAR, DOME, BLOCK, POD, RIB, EDGE, DARK, HI, SHINE = range(12)
    bm = bmesh.new()

    # The ring: outer edge columns 5-19, rows 6-19; the hole inside reaches row 17 at the bottom.
    prof = [(0, 0.0), (0, 0.17), (0.3, 0.25), (0.7, 0.25), (1, 0.15), (1, 0.0)]
    lib.annulus(bm, F, (12.5, 13.1, 7.4, 7.0), (12.5, 13.2, 5.3, 4.3), prof, 28, RING)

    # The dome hung in the ring's upper half (columns 9-15, rows 7-13).
    lib.ellipsoid(bm, (F.ex(12.5), F.ey(10.6), 0.12), (3.6 * U, 3.7 * U, 0.3), DOME, segments=18, rings=9,
                  z_min=0.0)
    lib.ellipsoid(bm, (F.ex(11.4), F.ey(9.8), 0.36), (0.8 * U, 1.4 * U, 0.04), SHINE, segments=8, rings=4)

    # Barrel pointing up the screen (columns 10-14, rows 1-6): five ribs, the middle one highest.
    lib.loft_y(bm, F, 12.5, [(1.3, 2.0, 0.06, 0.24), (2.0, 2.5, 0.08, 0.24), (6.5, 2.5, 0.08, 0.24)],
               sides=10, mat=DARK)
    for col in (11.5, 13.5):
        lib.loft_y(bm, F, col, [(1.5, 0.5, 0.06, 0.255), (2.1, 0.55, 0.07, 0.255), (6.5, 0.55, 0.07, 0.255)],
                   sides=6, mat=RIB)
    # Its collar on the ring (row 5) with a pin each side (columns 8 and 16, row 2).
    lib.prism(bm, F, [(9, 4.6), (16, 4.6), (16, 7), (9, 7)], 0.0, 0.3, BAR, bevel=0.03)
    for col in (8.5, 16.5):
        lib.loft_y(bm, F, col, [(1.8, 0.0, 0.0, 0.2), (2.3, 0.5, 0.04, 0.2), (5.0, 0.5, 0.04, 0.2)],
                   sides=6, mat=POD)

    # Arms out to the sides, joining the bar at the bottom.
    lib.prism(bm, F, [(1, 7), (2, 7), (6.2, 9), (6.2, 18), (4, 18), (4, 13.5), (1, 11)], 0.0, 0.22, LARM,
              bevel=0.04)
    lib.prism(bm, F, [(18, 9), (23, 7), (24, 7), (24, 11), (21, 13.5), (21, 18), (18.6, 18)], 0.0, 0.22,
              RARM, bevel=0.04)
    lib.loft_y(bm, F, 5.5, [(8.5, 0.0, 0.0, 0.2), (9.5, 0.5, 0.03, 0.2), (17.5, 0.5, 0.03, 0.2)],
               sides=6, mat=BAR)  # light edge down the inside of the left arm
    # Blue pins pointing up the screen from the arms (columns 3 and 21, rows 3-8).
    for col in (3.5, 21.5):
        lib.loft_y(bm, F, col, [(3.0, 0.0, 0.0, 0.2), (3.6, 0.65, 0.055, 0.2), (8.0, 0.7, 0.06, 0.2),
                                (9.5, 0.7, 0.06, 0.18)], sides=8, mat=POD)

    # The light grey bar across the bottom (rows 17-19, columns 2-22).
    lib.loft_x(bm, F, 18.9, [(2.4, 0.0, 0.0, 0.13), (3.0, 1.3, 0.11, 0.13), (21.0, 1.3, 0.11, 0.13),
                             (21.8, 0.0, 0.0, 0.13)], sides=10, mat=BAR)
    lib.loft_x(bm, F, 18.6, [(10.5, 0.0, 0.0, 0.22), (11.0, 0.5, 0.03, 0.22), (15.5, 0.5, 0.03, 0.22),
                             (16.0, 0.0, 0.0, 0.22)], sides=6, mat=HI)

    # Blue block under the bar (columns 9-15, rows 20-25) between grey cheeks, with a bright top edge.
    lib.prism(bm, F, [(9, 19.5), (16, 19.5), (16, 25.6), (15, 26), (10, 26), (9, 25.6)], 0.0, 0.24, BLOCK,
              bevel=0.04)
    lib.prism(bm, F, [(9.3, 20.4), (15.7, 20.4), (15.7, 21.6), (9.3, 21.6)], 0.2, 0.248, EDGE)
    lib.prism(bm, F, [(6.5, 19.5), (9, 19.5), (9, 25.5), (7.5, 25.5), (6.5, 24)], 0.0, 0.18, DARK, bevel=0.03)
    lib.prism(bm, F, [(16, 19.5), (18.2, 19.5), (18.2, 23.5), (17, 25.5), (16, 25.5)], 0.0, 0.18, RARM,
              bevel=0.03)
    # Pods at its corners.
    lib.ellipsoid(bm, (F.ex(5.6), F.ey(21.7), 0.06), (1.5 * U, 1.9 * U, 0.12), POD, segments=10, rings=5,
                  z_min=0.0)
    lib.ellipsoid(bm, (F.ex(19.5), F.ey(21.2), 0.06), (1.5 * U, 1.7 * U, 0.11), POD, segments=10, rings=5,
                  z_min=0.0)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run(ROOT, NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)


if __name__ == "__main__":
    main()
