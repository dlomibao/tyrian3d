"""Brass dome works (newsh2.shp frames 77, 79, 115 and 117 in a 2x2): a 3D version of its sprites.

Seen in levels 1.28, 1.30 and 3.17. Four 2x2 enemies make one 48 x 56 px structure dug into
brown dirt (sprite.json `assemblyLayout`; the layout also lists newsh2-119, a separate
neighbour): on a dark machinery bed sits a big brass dome (a dark slot on each side, a raised
visor bar over a dark window, a light rod at its lower right), flanked by grey pylons, with two
smaller brass domes below it carrying grey gun blocks, a grey neck between them and a third brass
dome at the bottom with a dark gun port. Grey struts run out from the bed at the bottom.

The whole structure is built once in assembly coordinates and cut into its four pieces with
common.split_assembly. The dirt is a thin floor and the bed a low platform, both made of 2 x 2 px
cells that take the sprite's colour. The domes are round, polished brass balls in one mid tone
(the sprite's bright spots are sheen, its dark rims shadow) with their markings modelled: a
hatch band on the big dome conforming to its curve, framed slots, a gun port bored into the bottom
dome, brass feed pipes to the side domes and a pipe down the neck.

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
    slot[25] = len(mats)  # the domes' mid brass
    mats.append(common.palette_material(sprite, 25, tag, metallic=0.55, roughness=0.3))
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
    # Round, polished brass balls (the concept's reading): each about half its width tall or more,
    # one mid brass tone; the sprite's bright spots are sheen and its dark lower-right rims shadow,
    # left to the lighting. Markings are modelled, not painted.
    BASE = BED - 0.02
    BRASS = slot[25]  # the domes' mid tone
    BIG = (18.5, 11.0, 12.6, 10.6, 0.88)  # centre column, row, radii in px, height in units

    def surf(d, c, r):
        """Height of dome d = (col, row, rx px, ry px, rz) over the pixel point (c, r)."""
        dc, dr, rx, ry, rz = d
        q = 1 - ((c - dc) / rx) ** 2 - ((r - dr) / ry) ** 2
        return BASE + rz * math.sqrt(max(q, 0.0))

    def shell(d, c0, r0, c1, r1, t, mat, n=6, sink=0.04):
        """A plate on dome d over the pixel box, its top following the curve t above the surface
        and its sides dropping below it: crisp edges, curved face."""
        first = len(bm.faces)
        cs = [c0 + (c1 - c0) * i / n for i in range(n + 1)]
        rs = [r0 + (r1 - r0) * j / n for j in range(n + 1)]
        top = [[bm.verts.new((XE(c), YE(r), surf(d, c, r) + t)) for c in cs] for r in rs]
        bot = [[bm.verts.new((XE(c), YE(r), surf(d, c, r) - sink)) for c in cs] for r in rs]
        for j in range(n):
            for i in range(n):
                bm.faces.new((top[j + 1][i], top[j + 1][i + 1], top[j][i + 1], top[j][i]))
        ring = ([(0, i) for i in range(n)] + [(j, n) for j in range(n)] +
                [(n, i) for i in range(n, 0, -1)] + [(j, 0) for j in range(n, 0, -1)])
        for (j0, i0), (j1, i1) in zip(ring, ring[1:] + ring[:1]):
            bm.faces.new((top[j0][i0], top[j1][i1], bot[j1][i1], bot[j0][i0]))
        for f in bm.faces[first:]:
            f.material_index = mat
            f.smooth = False
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[first:])

    def framed_slot(d, c0, r0, c1, r1, w=0.6):
        """A dark slot cut into dome d: a dark floor just over the surface inside a raised brass
        frame."""
        shell(d, c0, r0, c1, r1, 0.006, DARK, n=3)
        shell(d, c0 - w, r0 - w, c1 + w, r0, 0.04, BRASS, n=3)
        shell(d, c0 - w, r1, c1 + w, r1 + w, 0.04, BRASS, n=3)
        shell(d, c0 - w, r0, c0, r1, 0.04, BRASS, n=3)
        shell(d, c1, r0, c1 + w, r1, 0.04, BRASS, n=3)

    lib.dome(bm, (XE(BIG[0]), YE(BIG[1]), BASE), (BIG[2] * PX, BIG[3] * PX, BIG[4]),
             mat=BRASS, segments=32, rings=10)
    # The hatch band down the dome's middle (lit left edge at col 13), its upper hatch plate, the
    # visor bar (the bright row 11), the dark window under it and the darker lower plate.
    shell(BIG, 13.0, 5.5, 24.0, 20.0, 0.035, BRASS, n=8)
    shell(BIG, 15.0, 6.6, 23.0, 10.4, 0.07, slot[24])
    shell(BIG, 13.4, 10.4, 23.6, 12.5, 0.1, slot[28], n=6)
    shell(BIG, 15.0, 12.7, 23.0, 15.0, 0.04, DARK, n=4)
    shell(BIG, 15.6, 15.1, 22.4, 19.4, 0.075, slot[22], n=5)
    # The vertical slots on the dome's flanks.
    framed_slot(BIG, 10.0, 9.0, 11.6, 14.6)
    framed_slot(BIG, 25.0, 9.0, 26.6, 14.6)
    # The light rod at the dome's lower right.
    lib.sweep(bm, [(XE(23.2), YE(22.4), 0.2, 0.9 * PX, 0.9 * PX), (XE(30.2), YE(16.8), 0.3, 0.9 * PX, 0.9 * PX)],
              sides=8, mat=ROD)

    SIDE = 0.58 # side domes' height
    for cx in (7.0, 30.0):  # the side domes
        lib.dome(bm, (XE(cx), YE(31.0), BASE), (6.0 * PX, 5.2 * PX, SIDE), mat=BRASS, segments=20, rings=7)
    # Their grey gun blocks, standing proud of the dome's front.
    block(6, 29.5, 11, 36, 0.66)
    block(29, 29.5, 34, 35.5, 0.66)
    # Brass feed pipes from under the main dome down into each side dome.
    rp = 1.3 * PX
    lib.sweep(bm, [(XE(10.4), YE(17.5), 0.36, rp, rp), (XE(8.6), YE(20.5), 0.3, rp, rp),
                   (XE(8.2), YE(23.0), 0.28, rp, rp), (XE(8.0), YE(27.5), 0.3, rp, rp)],
              sides=10, mat=BRASS)
    lib.sweep(bm, [(XE(27.0), YE(18.0), 0.36, rp, rp), (XE(29.4), YE(20.8), 0.3, rp, rp),
                   (XE(29.9), YE(23.0), 0.28, rp, rp), (XE(30.0), YE(27.5), 0.3, rp, rp)],
              sides=10, mat=BRASS)
    # A pipe down the neck (its lighter column 20), from under the main dome to the bottom dome.
    lib.sweep(bm, [(XE(20.5), YE(20.0), 0.31, 0.9 * PX, 0.9 * PX), (XE(20.5), YE(36.5), 0.31, 0.9 * PX, 0.9 * PX)],
              sides=8, mat=slot[6])

    BOT = (18.5, 39.6, 5.6, 4.8, 0.5)
    lib.dome(bm, (XE(BOT[0]), YE(BOT[1]), BASE), (BOT[2] * PX, BOT[3] * PX, BOT[4]), mat=BRASS, segments=20, rings=7)
    # Its gun port: a dark bore in a raised brass rim.
    pc, pr = 19.0, 41.3
    pz = surf(BOT, pc, pr)
    up = (0, 1, 0)
    lib.sweep(bm, [(XE(pc), YE(pr), pz - 0.08, 2.7 * PX, 2.2 * PX), (XE(pc), YE(pr), pz + 0.035, 2.7 * PX, 2.2 * PX)],
              sides=14, mat=BRASS, up=up, smooth=False)
    lib.sweep(bm, [(XE(pc), YE(pr), pz - 0.05, 1.9 * PX, 1.5 * PX), (XE(pc), YE(pr), pz + 0.04, 1.9 * PX, 1.5 * PX)],
              sides=12, mat=slot[2], up=up, smooth=False)

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
