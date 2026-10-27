"""Blue armoured core pod (newshc.shp frames 49, 51, 53): a 3D version of its sprite.

Seen in episode 1 (level 1.19), 3 (level 3.23) and 4 (level 4.12). A dark blue hull with a
thick, curved light-blue shell wrapping its left side and top, a glowing orange core in a socket
under the shell, a light rib and a darker wall down its right side, and banded plates and vents
across its lower part. The three frames only brighten the core (dim red to white-hot), so one
model covers them all: the core and its hot centre change palette colour on each frame
(palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshc-49.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "newshc-49"
ROOT = common.repo_root(__file__)
DZ = -0.4


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(53, metallic=0.4, roughness=0.5),  # 0 dark blue hull
        pal(57, metallic=0.45, roughness=0.4),  # 1 light blue shell
        pal(61, metallic=0.5, roughness=0.3),  # 2 pale shell crest
        pal(56, metallic=0.45, roughness=0.4),  # 3 right rib, plates
        pal(54, metallic=0.4, roughness=0.45),  # 4 right wall, struts
        # 5 glowing core and 6 hot centre: dim red-orange on 49, orange on 51, yellow-white on 53
        common.palette_material(sprite, 121, f"{NAME}-core", emission_strength=4.0, frames={49: 116, 53: 124}),
        common.palette_material(sprite, 125, f"{NAME}-hot", emission_strength=6.0, frames={49: 122, 53: 127}),
        pal(58, metallic=0.45, roughness=0.35),  # 7 light lip and bands
        pal(50, metallic=0.3, roughness=0.6),  # 8 dark socket and vents
    ]
    HULL, SHELL, CREST, RIB, WALL, CORE, HOT, LIP, DARK = range(9)
    bm = bmesh.new()

    # Hull: the whole silhouette, chamfered.
    lib.slab(bm, [(11, 1), (19, 1), (19, 4), (23, 4), (23, 24), (20, 24), (20, 28), (3, 28), (3, 25),
                  (1, 25), (1, 12), (2, 9.5), (9, 2)], -2.6 + DZ, 0.0 + DZ, mat=HULL, bevel=0.6)
    # Dark socket the core sits in (columns 9-16, rows 3-17).
    lib.ellipsoid(bm, 12.6, 10.5, 0.0 + DZ, 4.2, 7.0, 0.7, mat=DARK, segments=14, rings=4, lower=0.0)
    # The curved shell: across the top (rows 1-3), then down the left side to row 20.
    lib.tube(bm, [(19.0, 2.5, 1.5, 1.6, 0.9 + DZ), (14.0, 2.5, 1.6, 1.7, 1.0 + DZ), (10.4, 3.7, 2.3, 1.9, 1.1 + DZ),
                  (7.6, 6.3, 2.9, 2.0, 1.2 + DZ), (5.6, 9.6, 3.3, 2.0, 1.2 + DZ), (4.8, 13.0, 3.5, 2.0, 1.2 + DZ),
                  (4.6, 17.0, 3.5, 1.9, 1.1 + DZ), (4.4, 19.6, 3.2, 1.6, 0.9 + DZ)],
             sides=12, mat=SHELL, power=0.7)
    # Pale crest along the shell (the 60-62 streak from column 9, row 4 to column 5, row 15).
    lib.tube(bm, [(10.6, 4.0, 0.0, 0.0, 2.8 + DZ), (9.6, 4.8, 0.6, 0.35, 3.0 + DZ), (7.8, 6.8, 0.65, 0.35, 3.1 + DZ),
                  (6.2, 9.6, 0.65, 0.35, 3.1 + DZ), (5.6, 13.0, 0.6, 0.35, 3.1 + DZ), (5.5, 15.4, 0.0, 0.0, 3.0 + DZ)],
             sides=6, mat=CREST)
    # Light rib (columns 16-18, rows 5-16) and the darker wall right of it (columns 19-22).
    lib.box(bm, 15.8, 4.4, 19.0, 16.4, -0.5 + DZ, 1.7 + DZ, mat=RIB, bevel=0.4)
    lib.box(bm, 19.4, 4.4, 23.0, 19.4, -0.5 + DZ, 1.0 + DZ, mat=WALL, bevel=0.4)
    # The glowing core (columns 9-15, rows 10-16) with its hot centre, and the light lip below it.
    lib.ellipsoid(bm, 12.5, 13.4, 0.6 + DZ, 3.5, 3.5, 2.3, mat=CORE, segments=16, rings=8)
    lib.ellipsoid(bm, 12.6, 13.0, 1.6 + DZ, 1.7, 1.6, 1.5, mat=HOT, segments=12, rings=6)
    lib.loft_x(bm, 17.5, [(8.8, 0.0, 0.0, 0.6 + DZ), (9.4, 0.6, 0.5, 0.6 + DZ), (15.0, 0.6, 0.5, 0.6 + DZ),
                          (15.6, 0.0, 0.0, 0.6 + DZ)], sides=6, mat=LIP)
    # Lower bands across the hull (rows 20 and 22-23), a strut on the left (column 5) and the
    # vented block at the bottom (rows 25-27).
    lib.loft_x(bm, 20.5, [(8.6, 0.6, 0.5, 0.4 + DZ), (23.0, 0.6, 0.5, 0.4 + DZ)], sides=6, mat=LIP)
    lib.box(bm, 6.6, 21.8, 23.0, 24.0, -0.6 + DZ, 0.9 + DZ, mat=RIB, bevel=0.35)
    lib.box(bm, 4.6, 18.6, 5.8, 25.0, -0.6 + DZ, 1.0 + DZ, mat=WALL, bevel=0.2)
    for c in (9.6, 11.6, 13.6, 15.6):
        lib.box(bm, c, 26.4, c + 1.0, 28.0, -1.6 + DZ, 0.5 + DZ, mat=WALL)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run_single(ROOT, NAME, build)


if __name__ == "__main__":
    main()
