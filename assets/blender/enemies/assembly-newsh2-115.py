"""Brass dome works (newsh2.shp frames 77, 79, 115 and 117 in a 2x2): a 3D version of its sprites.

Seen in levels 1.28, 1.30 and 3.17. Four 2x2 enemies make one 48 x 56 px structure dug into
brown dirt (sprite.json `assemblyLayout`; the layout also lists newsh2-119, a separate
neighbour): on a dark machinery bed sits a big brass dome (a dark slot on each side, a raised
visor bar over a dark window, a light rod at its lower right), flanked by grey pylons, with two
smaller brass domes below it carrying grey gun blocks, a grey neck between them and a third brass
dome at the bottom with a dark gun port. Grey struts run out from the bed at the bottom.

The whole structure is built once in assembly coordinates and cut into its four pieces with
common.split_assembly. The dirt is a thin floor and the bed a low platform, both made of 2 x 2 px
cells that take the sprite's colour; the domes and blocks take the sprite's colour under each
upward facet (holes in the sprite are dark).

Run: blender --background --python assets/blender/enemies/assembly-newsh2-115.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import math
import sys
from collections import Counter
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b120 as lib  # noqa: E402

NAME = "assembly-newsh2-115"
ROOT = common.repo_root(__file__)
W, H = 48, 56  # the assembly grid in pixels; its centre is the Blender origin
PX = 1 / 12
FLOOR = 0.02  # top of the dirt
BED = 0.1  # top of the machinery bed

# The machinery bed's outline in pixel edges (column, row).
BED_OUTLINE = [(5.5, 8), (9, 3), (13, 1), (24, 1), (28, 3), (32, 6), (37, 8), (37.5, 40), (34, 45),
               (30, 51), (17, 52), (12, 49), (7, 45), (7, 39), (2, 39), (1, 36), (1, 28), (2, 20),
               (2, 13)]


def XE(e):
    """Grid pixel edge (column) to Blender X."""
    return (e - W / 2) / 12


def YE(e):
    """Grid pixel edge (row) to Blender Y."""
    return (H / 2 - e) / 12


def inside(poly, x, y):
    """Point in polygon (pixel edges)."""
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


GREYS = [2, 4, 6, 8, 10]
TANS = [22, 24, 26, 28, 30]
DIRT = [16, 17, 18, 19, 20, 21]


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nsh2a115"
    mats, slot = [], {}
    for i in GREYS:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.4, roughness=0.45))
    for i in TANS:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.55, roughness=0.3))
    for i in DIRT:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.95))
    slot["rod"] = len(mats)
    mats.append(common.palette_material(sprite, 30, tag + "rod", metallic=0.6, roughness=0.25))
    DARK, MID, TAN, ROD = slot[2], slot[4], slot[25 - 1], slot["rod"]

    def nearest(idx, family):
        return slot[min(family, key=lambda g: abs(g - idx))]

    def slot_for(idx):
        """Any sprite colour to the nearest material; holes (-1) are dark."""
        if idx < 0 or idx == 1:
            return DARK
        if idx <= 13:
            return nearest(idx, GREYS)
        if idx == 106:
            return slot[10]
        if 16 <= idx <= 21:
            return slot[20] if idx >= 20 else DARK  # dirt seen past a part's edge
        if 22 <= idx <= 31:
            return nearest(idx, TANS)
        if idx == 169:
            return slot[24]
        if 172 <= idx <= 174:
            return slot[28] if idx == 172 else slot[30]
        return None

    def sample(x, y):
        c = math.floor(x * 12 + W / 2)
        r = math.floor(H / 2 - y * 12)
        if 0 <= r < H and 0 <= c < W:
            return grid[r][c]
        return None

    bm = bmesh.new()

    # ---- dirt floor and machinery bed, in 2 x 2 px cells ----
    verts = {}

    def vert(i, j, z):
        key = (i, j, z)
        if key not in verts:
            verts[key] = bm.verts.new((XE(i), YE(j), z))
        return verts[key]

    for j in range(0, H, 2):
        for i in range(0, W, 2):
            pix = [grid[j + dj][i + di] for dj in (0, 1) for di in (0, 1)]
            on_bed = inside(BED_OUTLINE, i + 1, j + 1)
            z = BED if on_bed else FLOOR
            f = bm.faces.new((vert(i, j + 2, z), vert(i + 2, j + 2, z), vert(i + 2, j, z), vert(i, j, z)))
            f.smooth = False
            if on_bed:
                slots = [slot_for(v) for v in pix if not (16 <= v <= 21)]
                f.material_index = Counter(slots).most_common(1)[0][0] if slots else DARK
            else:
                dirt = [v for v in pix if 16 <= v <= 21] or [18]
                f.material_index = nearest(sum(dirt) / len(dirt), DIRT)
    # The bed's sides, under its cells.
    lib.prism(bm, [(XE(c), YE(r)) for c, r in BED_OUTLINE], 0.0, BED - 0.004, mat=DARK)

    def dome_slot(idx):
        """On the domes the outline (1) and dirt past their edge keep the brass; holes are dark."""
        if idx == 1 or 16 <= idx <= 21:
            return None
        return slot_for(idx)

    def painted(make, base):
        first = len(bm.faces)
        make(base)
        lib.paint(bm, first, sample, dome_slot)

    def grey_of(c0, r0, c1, r1):
        """The commonest grey (not the outline) of the sprite pixels in a box of pixel edges."""
        pix = [grid[r][c] for r in range(math.floor(r0), math.ceil(r1))
               for c in range(math.floor(c0), math.ceil(c1))]
        greys = [nearest(v, GREYS) for v in pix if 2 <= v <= 13]
        return Counter(greys).most_common(1)[0][0] if greys else MID

    def block(c0, r0, c1, r1, z1, mat=None, z0=BED - 0.01):
        mat = grey_of(c0, r0, c1, r1) if mat is None else mat
        lib.bevel_prism(bm, [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))],
                        z0, z1, 0.02, mat=mat)

    # ---- grey works on the bed ----
    block(2.5, 13, 7, 28, 0.36)  # left pylon
    block(2.5, 20.5, 9.5, 25.5, 0.28)  # its foot
    block(31.5, 9, 36.5, 28, 0.36)  # right pylon
    block(29.5, 20.5, 36.5, 25.5, 0.28)  # its foot
    block(13.5, 22, 24.5, 35.5, 0.24, mat=slot[4])  # neck down the middle
    # Struts out from the bottom of the bed.
    lib.bevel_prism(bm, [(XE(c), YE(r)) for c, r in [(7.5, 38.5), (12.5, 38.5), (12.5, 42), (15.5, 45.5),
                                                     (23.5, 46), (23.5, 48), (12.5, 48), (10.5, 46),
                                                     (7.5, 42)]],
                    BED - 0.01, 0.18, 0.02, mat=grey_of(7.5, 38.5, 18, 47))
    block(25.5, 38.5, 32.5, 43, 0.2)

    # ---- brass domes ----
    painted(lambda m: lib.dome(bm, (XE(18.5), YE(11.0), BED - 0.02), (12.6 * PX, 10.6 * PX, 0.46),
                               mat=m, segments=32, rings=9), TAN)
    # Visor bar over the dome's dark window, and the light rod at its lower right.
    block(14, 9.6, 24.5, 12.8, 0.6, mat=TAN, z0=0.42)
    lib.sweep(bm, [(XE(23.2), YE(22.4), 0.2, 0.9 * PX, 0.05), (XE(30.2), YE(16.8), 0.26, 0.9 * PX, 0.05)],
              sides=8, mat=ROD)
    # Dark slots on either side of the big dome, the dark window under the visor and the brass
    # plate below it.
    block(8, 8.5, 11, 14.5, 0.44, mat=DARK, z0=0.1)
    block(25.5, 8.5, 28, 14.5, 0.44, mat=DARK, z0=0.1)
    block(15, 12.6, 23, 15.2, 0.535, mat=DARK, z0=0.3)
    block(16, 15, 22, 18.8, 0.5, mat=slot[24], z0=0.3)
    for cx in (7.0, 30.0):  # the side domes and their grey gun blocks
        painted(lambda m: lib.dome(bm, (XE(cx), YE(31.0), BED - 0.02), (6.0 * PX, 5.2 * PX, 0.32),
                                   mat=m, segments=18, rings=5), TAN)
    block(6, 29.5, 11, 36, 0.42)
    block(29, 29.5, 34, 35.5, 0.42)
    painted(lambda m: lib.dome(bm, (XE(18.5), YE(39.6), BED - 0.02), (5.6 * PX, 4.8 * PX, 0.3),
                               mat=m, segments=18, rings=5), TAN)
    lib.ellipsoid(bm, (XE(19.0), YE(41.0), 0.36), (2.1 * PX, 1.4 * PX, 0.05), mat=DARK, segments=10, rings=4)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-115")
    sprite = common.load_sprite(ROOT, "newsh2-115")
    sprite["colors"] = colors
    obj = build(sprite, grid)
    pieces_layout = [(e["model"], e["cx"] - x0 - W / 2, e["cy"] - y0 - H / 2) for e in layout]
    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_assembly(ROOT, obj, pieces_layout, out, grid, colors, None)


if __name__ == "__main__":
    main()
