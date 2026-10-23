"""Blue organism on a tube wall (newshh.shp 81, 83, 119, 121): a 3D version of its sprites.

Seen in level 2.4. Four 2x2 enemies make one 48 x 56 px block: a wall of ribbed grey tubes with
a glossy blue organism lying on it: a bulb at the top right whose tendril runs left along the
top and curls down the left side, a big oval body in the middle with tendrils wrapping its right
side, a round lobe at the bottom left with smaller lumps beside it, and a dark hollow at the
bottom right where the wall shows through.

The block is built once in assembly coordinates and cut into its four pieces with
common.split_assembly. The wall's tubes are traced from the sprite's texture (lib_b059) and
every part is coloured from the sprite pixel under it, so highlights land where the sprite has
them.

Run: blender --background --python assets/blender/enemies/assembly-newshh-121.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b059 as lib  # noqa: E402

NAME = "assembly-newshh-121"
ROOT = common.repo_root(__file__)
# Each piece's top-left pixel in the 48 x 56 block (from sprite.json assemblyLayout: screen
# centres 125/149, 59/87).
PIECES = [("newshh-81", 0, 0), ("newshh-83", 24, 0), ("newshh-119", 0, 28), ("newshh-121", 24, 28)]

GREY = [97, 100, 103, 106]
BLUE = [49, 51, 53, 56, 59]


def build(grid, sprite):
    coll = common.reset_collection(NAME)
    tag = "nshh121"
    mats, gslot, bslot = [], {}, {}
    for i in GREY:
        gslot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.25, roughness=0.5))
    for i in BLUE:
        bslot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.35, roughness=0.25))
    grey, blue = lib.nearest(gslot), lib.nearest(bslot)
    DARK, BDARK = gslot[97], bslot[49]
    bm = bmesh.new()

    # The wall's backing plate: the whole block, dark (the grooves between the tubes).
    lib.plate(bm, [(0, 0), (48, 0), (48, 56), (0, 56)], -0.25, -0.16, mat=DARK)

    # The organism's skin: a low membrane over every blue pixel, holes and all.
    is_blue = [[48 <= grid[r][c] <= 62 for c in range(lib.W)] for r in range(lib.H)]
    lib.membrane(bm, is_blue, -0.2, -0.07, inset_px=1.0, mat=bslot[51])
    cover = lib.covered(is_blue)

    # The tube wall wherever the organism isn't.
    lib.tube_wall(bm, grid, lambda c, r: not cover[r][c], -0.16, grey, DARK)

    first = len(bm.faces)
    # Bulb at the top right (its top runs off the block).
    lib.ellipsoid(bm, 33.5, 4.0, -0.1, 8.0, 6.5, 0.3, z_bottom=-0.15, segments=20, rings=10)
    # Its tendril along the top, curling down the left side to a knob.
    lib.tendril(bm, [(30, 3.2), (24, 3.0), (19, 3.6), (15.5, 5.5), (12.8, 8.2), (10.6, 11.0),
                     (8.6, 13.8), (7.2, 16.5)], -0.04, 2.4, 2.1, 0.12, 0.11, sides=8)
    lib.ellipsoid(bm, 7.2, 17.5, -0.08, 3.2, 4.2, 0.2, z_bottom=-0.12, segments=12, rings=6)
    # A short tendril off the bulb's right side.
    lib.tendril(bm, [(39.2, 8.5), (39.0, 10.6), (37.5, 12.4), (35.5, 13.4)], -0.05, 1.6, 1.4, 0.08, 0.07,
                sides=6, rounds=1)
    # Fill between the bulb and the body.
    lib.ellipsoid(bm, 29.0, 11.0, -0.08, 8.5, 3.5, 0.13, z_bottom=-0.12, segments=14, rings=6)
    # The big oval body.
    lib.ellipsoid(bm, 21.0, 22.5, -0.1, 13.8, 7.6, 0.34, z_bottom=-0.15, segments=24, rings=12)
    # Tendril wrapping the body's right side, from the edge down and back under it.
    lib.tendril(bm, [(40.5, 22.2), (39.2, 24.6), (37.0, 26.8), (35.0, 28.8), (32.0, 30.4), (27.5, 31.3)],
                -0.03, 1.9, 1.5, 0.1, 0.08, sides=8)
    # Lower mass with its lumps.
    lib.ellipsoid(bm, 23.0, 40.0, -0.08, 10.0, 6.0, 0.11, z_bottom=-0.12, segments=16, rings=6)
    lib.ellipsoid(bm, 21.5, 37.5, -0.06, 3.6, 2.8, 0.15, z_bottom=-0.1, segments=12, rings=6)
    lib.ellipsoid(bm, 28.0, 37.6, -0.06, 3.0, 2.6, 0.13, z_bottom=-0.1, segments=12, rings=6)
    lib.ellipsoid(bm, 32.4, 41.5, -0.06, 2.0, 2.4, 0.1, z_bottom=-0.1, segments=10, rings=5)
    # The round lobe at the bottom left and the smaller one under it.
    lib.ellipsoid(bm, 11.8, 42.8, -0.1, 7.0, 7.0, 0.3, z_bottom=-0.15, segments=20, rings=10)
    lib.ellipsoid(bm, 14.0, 48.2, -0.08, 4.6, 2.6, 0.12, z_bottom=-0.12, segments=12, rings=6)
    lib.paint(bm, first, grid, blue, under=BDARK)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, sprite = lib.load_grid(ROOT, PIECES)
    obj = build(grid, sprite)
    lib.export_assembly(ROOT, obj, PIECES, grid, sprite)


if __name__ == "__main__":
    main()
