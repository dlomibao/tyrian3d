"""Grey gun-tower craft (newshc.shp frames 191, 193, 195): a 3D version of its sprite.

Seen in episode 3 (levels 3.6 and 3.23). Seen from above: a grey tower at the back with two dark
vent slots, a pair of round grey pods with dark glass canopies either side of it, a blue hull
underneath with green, sloped side panels, and a pink cannon whose dark mouth opens just in front
of the tower. The three frames only light up the green panels (the last frame glows bright
green), so one model covers them all; the glowing strips use the bright green index.

Run: blender --background --python assets/blender/enemies/newshc-191.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "newshc-191"
ROOT = common.repo_root(__file__)
AXIS = 12.0  # the sprite is mirror symmetric about the edge between columns 11 and 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.35),  # 0 grey tower
        pal(2, metallic=0.2, roughness=0.8),  # 1 dark vent slots
        pal(9, metallic=0.6, roughness=0.3),  # 2 light grey ridge
        pal(105, metallic=0.5, roughness=0.35),  # 3 grey-blue pods
        pal(99, metallic=0.7, roughness=0.15),  # 4 dark glass canopies
        pal(108, metallic=0.6, roughness=0.3),  # 5 pale pod rims
        pal(57, metallic=0.4, roughness=0.45),  # 6 blue hull
        pal(59, metallic=0.4, roughness=0.4),  # 7 light blue ribs
        pal(38, metallic=0.3, roughness=0.5),  # 8 green side panels
        pal(202, emission_strength=3.0),  # 9 glowing green strips
        pal(89, metallic=0.4, roughness=0.4),  # 10 pink cannon
        pal(82, metallic=0.2, roughness=0.8),  # 11 cannon mouth
        pal(93, metallic=0.4, roughness=0.3),  # 12 pale pink highlight
        pal(103, metallic=0.5, roughness=0.45),  # 13 grey deck under the pods
    ]
    TOWER, SLOT, RIDGE, POD, GLASS, RIM, HULL, RIB, GREEN, GLOW, PINK, MOUTH, PALE, DECK = range(14)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----
    # Blue hull (rows 17-25), its lower corners cut away, chamfered on top.
    lib.slab(bm, [(1, 17.2), (AXIS, 17.2), (AXIS, 25.0), (4.5, 25.0), (2.6, 24.2), (1.2, 22.8)],
             -3.2, 0.2, mat=HULL, bevel=0.8)
    # Green side panel sloping down the outer edge (columns 1-4, rows 18-24) and its glow strip.
    lib.slab(bm, [(1.0, 17.6), (4.8, 17.6), (4.8, 21.0), (5.2, 24.4), (3.0, 24.6), (1.0, 23.0)],
             -2.6, 0.9, mat=GREEN, bevel=0.9)
    lib.box(bm, 1.9, 20.2, 3.1, 23.8, -1.0, 0.6, mat=GLOW)
    # Light diagonal ribs on the hull (the pale 57-60 streak from column 4, row 20 to column 9, row 24).
    lib.tube(bm, [(4.6, 19.6, 0.55, 0.45, 0.3), (6.6, 22.4, 0.55, 0.45, 0.3), (8.6, 24.4, 0.55, 0.45, 0.2)],
             sides=6, mat=RIB)
    lib.tube(bm, [(6.4, 18.6, 0.5, 0.4, 0.4), (9.0, 22.6, 0.5, 0.4, 0.4)], sides=6, mat=RIB)
    # Grey deck the pods sit on (rows 13-18), behind the hull.
    lib.slab(bm, [(1.6, 13.0), (AXIS, 13.0), (AXIS, 18.0), (1.6, 18.0)], -1.8, 0.4, mat=DECK, bevel=0.5)
    # Round pod (columns 1-8, rows 10-17) with a dark glass canopy on top and a pale rim below it.
    lib.ellipsoid(bm, 4.6, 13.8, 0.6, 3.7, 4.0, 2.6, mat=POD, segments=16, rings=8, lower=0.6)
    lib.ellipsoid(bm, 4.7, 12.4, 2.0, 2.8, 2.4, 1.4, mat=GLASS, segments=14, rings=6, lower=0.4)
    lib.tube(bm, [(1.6, 15.0, 1.0, 0.6, 1.9), (4.6, 15.7, 1.1, 0.6, 2.7), (7.6, 15.0, 1.0, 0.6, 1.9)],
             sides=6, mat=RIM)
    # Dark vent slot in the tower's top (columns 9-10, rows 7-11).
    lib.box(bm, 9.2, 6.9, 10.9, 11.0, 3.0, 4.3, mat=SLOT)
    lib.mirror_x(bm, AXIS)

    # ---- centre ----
    # Grey tower (columns 8-15, rows 4-13): a rounded box, rounded at its back.
    lib.loft_y(bm, AXIS, [(3.9, 0.0, 0.0, 1.8), (4.2, 2.6, 1.8, 1.8), (5.0, 3.8, 2.3, 1.6),
                          (6.5, 4.0, 2.5, 1.5), (13.6, 4.0, 2.5, 1.5), (14.4, 3.2, 2.0, 1.5)],
               sides=12, mat=TOWER, power=0.55)
    # Light ridge down the tower's middle (columns 11-12).
    lib.loft_y(bm, AXIS, [(4.6, 0.0, 0.0, 3.9), (5.4, 1.0, 0.45, 3.9), (12.5, 1.0, 0.45, 3.9),
                          (13.0, 0.0, 0.0, 3.9)], sides=6, mat=RIDGE)
    # Pink cannon (columns 9-14, rows 13-23): a barrel lying down the hull, its flared mouth
    # raised just in front of the tower, with a dark hole and a pale highlight.
    lib.loft_y(bm, AXIS, [(12.9, 2.6, 1.6, 2.8), (13.4, 3.1, 2.0, 2.8), (17.6, 3.0, 2.0, 2.4),
                          (18.4, 2.4, 1.7, 2.0), (22.4, 2.4, 1.6, 1.6), (23.2, 1.6, 1.0, 1.4)],
               sides=12, mat=PINK)
    lib.ellipsoid(bm, AXIS, 15.6, 4.1, 2.0, 2.0, 0.55, mat=MOUTH, segments=12, rings=4)
    lib.loft_y(bm, 11.6, [(18.0, 0.0, 0.0, 3.6), (18.6, 0.5, 0.3, 3.5), (21.8, 0.5, 0.3, 3.1),
                          (22.4, 0.0, 0.0, 3.0)], sides=6, mat=PALE)

    obj = lib.to_object(NAME, bm, mats, coll)
    obj.location.z = -0.4 / 12
    return obj


def main():
    lib.run_single(ROOT, NAME, build)


if __name__ == "__main__":
    main()
