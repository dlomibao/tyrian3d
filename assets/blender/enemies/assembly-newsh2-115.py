"""Brass dome works (newsh2.shp frames 77, 79, 115 and 117 in a 2x2): a 3D version of its sprites.

Seen in levels 1.28, 1.30 and 3.17. Four 2x2 enemies make one 48 x 56 px structure dug into
brown dirt (sprite.json `assemblyLayout`; the layout also lists newsh2-119, a separate
neighbour): on a dark machinery bed sits a big brass dome, flanked by grey pylons, with two
smaller brass domes below it carrying grey gun blocks, a bundle of pipes down the middle and a
third brass dome at the bottom with a dark gun port, all inside a raised octagonal frame.

Remodelled on the concept (assets/blender/features/concepts/): each part sits where the
registered concept (assets/blender/textures/<name>/concept.png) draws it, within the sprite's
outline, so the concept detail texture_bake.py projects onto it lands on the right part. The big
dome carries an H-shaped hatch band (an upper hatch with a plate and a vent grille, a crossbar, a
lower hatch with notched tabs over a dark slot and a second grille), a framed vertical slot on each
flank and a collar round its foot; elbow pipes with flanges drop from it into the side domes; each
side dome has an end cap on each side and a grey gun block (two studs on top, a handle, two
nozzles, the inner one glowing, and a lit indicator slit); three pipes run down the neck, the
outer two bending into the side domes, the middle one into the bottom dome's collar; two thin
brass pipes run from the big dome's lower right.

The whole structure is built once in assembly coordinates and cut into its four pieces with
common.split_assembly. The dirt is a thin floor of 2 x 2 px cells that take the sprite's colour;
the bed is one chamfered slab in the sprite's outline with chamfered plates on it. The domes are
round, polished brass balls in one mid tone (the sprite's bright spots are sheen, its dark rims
shadow) with their markings modelled, not painted.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-115.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import math
import sys
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

# The machinery bed's outline in pixel edges (column, row), from the sprite.
BED_OUTLINE = [(5.5, 8), (9, 3), (13, 1), (24, 1), (28, 3), (32, 6), (37, 8), (37.5, 40), (34, 45),
               (30, 51), (17, 52), (12, 49), (7, 45), (7, 39), (2, 39), (1, 36), (1, 28), (2, 20),
               (2, 13)]


def XE(e):
    """Grid pixel edge (column) to Blender X."""
    return (e - W / 2) / 12


def YE(e):
    """Grid pixel edge (row) to Blender Y."""
    return (H / 2 - e) / 12


def P(pts):
    return [(XE(c), YE(r)) for c, r in pts]


GREYS = [2, 3, 4, 5, 6, 8, 10]
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
    mats.append(common.palette_material(sprite, 28, tag + "rod", metallic=0.6, roughness=0.25))
    slot["glow"] = len(mats)  # nozzle glow and indicator slits
    mats.append(common.palette_material(sprite, 30, tag + "glow", metallic=0.0, roughness=0.2,
                                        emission_strength=2.5))
    slot["bore"] = len(mats)  # the gun port's dark bore: matte, so it reads as a hole
    mats.append(common.palette_material(sprite, 1, tag + "bore", metallic=0.0, roughness=0.8))
    DARK, BEDM, PLATE, MID, LIGHT = slot[2], slot[3], slot[4], slot[5], slot[8]
    BRASS, BRASS_D, ROD, GLOW = slot[25], slot[24], slot["rod"], slot["glow"]

    def nearest(idx, family):
        return slot[min(family, key=lambda g: abs(g - idx))]

    bm = bmesh.new()

    # ---- dirt floor in 2 x 2 px cells (hidden under the bed) ----
    verts = {}

    def vert(i, j, z):
        key = (i, j, z)
        if key not in verts:
            verts[key] = bm.verts.new((XE(i), YE(j), z))
        return verts[key]

    bed_in = list(BED_OUTLINE)

    def inside(x, y):
        hit = False
        for (x0, y0), (x1, y1) in zip(bed_in, bed_in[1:] + bed_in[:1]):
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                hit = not hit
        return hit

    for j in range(0, H, 2):
        for i in range(0, W, 2):
            if all(inside(i + a, j + b) for a in (-0.3, 2.3) for b in (-0.3, 2.3)):
                continue  # hidden under the bed
            pix = [grid[j + dj][i + di] for dj in (0, 1) for di in (0, 1)]
            f = bm.faces.new((vert(i, j + 2, FLOOR), vert(i + 2, j + 2, FLOOR), vert(i + 2, j, FLOOR),
                              vert(i, j, FLOOR)))
            f.smooth = False
            dirt = [v for v in pix if 16 <= v <= 21] or [18]
            f.material_index = nearest(sum(dirt) / len(dirt), DIRT)

    # ---- the machinery bed: one chamfered slab ----
    lib.bevel_prism(bm, P(BED_OUTLINE), 0.0, BED, 0.012, mat=BEDM)

    def plate(pts, z1, mat, bevel=0.02, z0=BED - 0.01):
        lib.bevel_prism(bm, P(pts), z0, z1, bevel, mat=mat)

    def rect(c0, r0, c1, r1, z1, mat, bevel=0.02, z0=BED - 0.01, cut=0.0):
        """A chamfered block over a pixel box; `cut` clips its corners (px)."""
        if cut:
            pts = [(c0 + cut, r0), (c1 - cut, r0), (c1, r0 + cut), (c1, r1 - cut), (c1 - cut, r1),
                   (c0 + cut, r1), (c0, r1 - cut), (c0, r0 + cut)]
        else:
            pts = [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]
        plate(pts, z1, mat, bevel, z0)

    def frame(outline, width, z1, mat):
        """A raised rim along a closed outline (px), `width` px wide inside it."""
        inner = lib.inset(P(outline), width * PX)
        outer = P(outline)
        n = len(outer)
        for i in range(n):
            j = (i + 1) % n
            lib.bevel_prism(bm, [outer[i], outer[j], inner[j], inner[i]], BED - 0.01, z1, 0.012, mat=mat)

    # Pylons either side of the main dome: tall grey panels with a clipped outer top corner, split
    # into an upper and a lower plate by a seam.
    plate([(3.6, 12.2), (6.4, 12.2), (6.4, 19.0), (2.0, 19.0), (2.0, 13.8)], 0.3, PLATE)
    plate([(2.0, 19.3), (6.4, 19.3), (6.4, 37.4), (1.6, 37.4), (1.6, 28.0)], 0.27, PLATE)
    plate([(31.4, 11.8), (35.2, 11.8), (36.8, 13.4), (36.8, 19.0), (31.4, 19.0)], 0.3, PLATE)
    plate([(31.4, 19.3), (36.8, 19.3), (37.0, 37.4), (31.4, 37.4)], 0.27, PLATE)
    # The lower octagon: an inner plate inside a raised rim (the sprite's grey struts).
    LOW = [(7.2, 37.4), (32.2, 37.4), (32.2, 43.0), (27.4, 49.8), (12.2, 49.8), (7.2, 45.0)]
    plate(LOW, BED + 0.035, BEDM, bevel=0.01)
    frame(LOW, 1.5, 0.2, MID)
    # Brackets under the side domes' gun blocks.
    rect(5.4, 36.4, 9.6, 40.0, 0.24, PLATE, cut=0.6)
    rect(28.0, 36.4, 32.0, 41.0, 0.24, PLATE, cut=0.6)
    # The neck: a dark machinery plate behind the pipe bundle.
    rect(12.6, 21.0, 24.4, 34.6, 0.15, PLATE, cut=1.2)

    # ---- brass domes ----
    BASE = BED - 0.02

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

    def framed_slot(d, c0, r0, c1, r1, w=0.6, n=3):
        """A dark slot cut into dome d: a dark floor just over the surface inside a raised brass
        frame."""
        shell(d, c0, r0, c1, r1, 0.006, DARK, n=n)
        shell(d, c0 - w, r0 - w, c1 + w, r0, 0.045, BRASS, n=n)
        shell(d, c0 - w, r1, c1 + w, r1 + w, 0.045, BRASS, n=n)
        shell(d, c0 - w, r0, c0, r1, 0.045, BRASS, n=n)
        shell(d, c1, r0, c1 + w, r1, 0.045, BRASS, n=n)

    def grille(d, c0, r0, c1, r1, slats, t):
        """A vent: a dark recess crossed by horizontal slats."""
        shell(d, c0, r0, c1, r1, t - 0.035, DARK, n=3)
        step = (r1 - r0) / slats
        for k in range(slats):
            a = r0 + step * (k + 0.2)
            shell(d, c0 + 0.15, a, c1 - 0.15, a + step * 0.5, t, BRASS_D, n=2, sink=0.03)

    def collar(c, r, z0, z1, rad, mat, sides=12):
        """A short vertical cylinder (a flange or socket) at pixel (c, r)."""
        lib.sweep(bm, [(XE(c), YE(r), z0, rad * PX, rad * PX), (XE(c), YE(r), z1, rad * PX, rad * PX)],
                  sides=sides, mat=mat, up=(0, 1, 0), smooth=False)

    def pipe(pts, rad, mat, sides=10):
        lib.sweep(bm, [(XE(c), YE(r), z, rad * PX, rad * PX) for c, r, z in pts], sides=sides, mat=mat)

    # The big dome: concept and sprite agree on a ball about 26 x 21 px, 11 px tall.
    BIG = (18.4, 10.9, 12.9, 10.6, 0.95)
    lib.dome(bm, (XE(BIG[0]), YE(BIG[1]), BASE), (BIG[2] * PX, BIG[3] * PX, BIG[4]),
             mat=BRASS, segments=32, rings=10)
    # A collar round its foot.
    ring = [(XE(BIG[0] + (BIG[2] + 0.1) * math.cos(a)), YE(BIG[1] + (BIG[3] + 0.1) * math.sin(a)))
            for a in (2 * math.pi * k / 28 for k in range(29))]
    lib.sweep(bm, [(x, y, BASE + 0.05, 0.9 * PX, 0.9 * PX) for x, y in ring], sides=6, mat=BRASS_D,
              cap_start=False, cap_end=False)
    # The H-shaped hatch band down its middle (cols 13.8-22.8 in the concept).
    shell(BIG, 13.8, 0.4, 22.8, 19.4, 0.03, BRASS, n=8)
    # Upper hatch: a raised plate (with a strip at its right) beside a vent grille, over a lower-left
    # plate.
    shell(BIG, 14.5, 0.9, 20.6, 4.5, 0.075, BRASS, n=4)
    shell(BIG, 21.0, 1.0, 21.9, 4.5, 0.06, BRASS, n=2)
    shell(BIG, 14.4, 5.0, 18.2, 9.4, 0.075, BRASS, n=4)
    grille(BIG, 18.6, 5.1, 21.8, 8.6, 5, 0.075)
    # The crossbar under it (the sprite's bright row 11 is its lit edge).
    shell(BIG, 13.8, 9.8, 22.8, 11.6, 0.1, BRASS, n=5)
    # Lower hatch: two notched tabs over a dark slot (the sprite's dark window), the plate below and
    # its grille on the right.
    shell(BIG, 15.6, 12.0, 21.2, 13.4, 0.01, DARK, n=4)
    shell(BIG, 14.4, 11.9, 16.0, 13.6, 0.085, BRASS, n=2)
    shell(BIG, 20.0, 11.9, 21.6, 13.6, 0.085, BRASS, n=2)
    shell(BIG, 14.2, 13.6, 22.2, 19.0, 0.07, BRASS, n=5)
    grille(BIG, 20.1, 14.2, 21.9, 18.2, 5, 0.09)
    # The vertical slots on its flanks.
    framed_slot(BIG, 9.4, 6.9, 11.0, 14.1)
    framed_slot(BIG, 25.2, 6.9, 26.8, 14.1)

    # Side domes, each with an end cap at both sides and a gun block on its front.
    SIDE_R = 30.2
    for dc in (6.8, 29.5):
        dx = dc - 6.8  # the right unit is the left one moved across (the concept draws both alike)
        dome = (dc, SIDE_R, 6.1, 6.0, 0.62)
        lib.dome(bm, (XE(dc), YE(SIDE_R), BASE), (6.1 * PX, 6.0 * PX, 0.62), mat=BRASS, segments=20, rings=7)
        # The pipe socket on top.
        collar(6.6 + dx, 24.6, surf(dome, 6.6 + dx, 25.2) - 0.05, surf(dome, 6.6 + dx, 25.2) + 0.08, 1.7, BRASS_D)
        # End caps: a grey boss on the outer side, a brass ring on the inner one.
        lib.sweep(bm, [(XE(dc - 5.4), YE(29.8), 0.34, 1.9 * PX, 1.9 * PX), (XE(dc - 6.6), YE(29.8), 0.34, 1.9 * PX, 1.9 * PX),
                       (XE(dc - 6.6), YE(29.8), 0.34, 1.0 * PX, 1.0 * PX), (XE(dc - 7.0), YE(29.8), 0.34, 1.0 * PX, 1.0 * PX)],
                  sides=10, mat=LIGHT, smooth=False) if dc < 20 else \
            lib.sweep(bm, [(XE(dc + 5.4), YE(29.8), 0.34, 1.9 * PX, 1.9 * PX), (XE(dc + 6.6), YE(29.8), 0.34, 1.9 * PX, 1.9 * PX),
                           (XE(dc + 6.6), YE(29.8), 0.34, 1.0 * PX, 1.0 * PX), (XE(dc + 7.4), YE(29.8), 0.34, 1.0 * PX, 1.0 * PX)],
                      sides=10, mat=LIGHT, smooth=False)
        inner = dc + 5.6 if dc < 20 else dc - 5.6
        sgn = 1 if dc < 20 else -1
        lib.sweep(bm, [(XE(inner), YE(29.8), 0.34, 1.6 * PX, 1.6 * PX), (XE(inner + sgn * 1.0), YE(29.8), 0.34, 1.6 * PX, 1.6 * PX)],
                  sides=10, mat=BRASS_D, smooth=False)
        # The gun block: a dark grey housing standing proud of the dome, a lighter face plate, two
        # studs on top, a handle at its right, two nozzles below (the inner one glowing) and a lit
        # indicator slit.
        g0, g1 = 3.9 + dx, 9.7 + dx
        rect(g0, 28.6, g1, 35.0, 0.78, MID, z0=0.2, cut=0.4)
        rect(g0 + 2.0, 29.2, g1 - 0.4, 34.4, 0.81, slot[6], z0=0.6, bevel=0.012)
        rect(g0 + 0.5, 29.6, g0 + 1.6, 33.6, 0.8, DARK, z0=0.6, bevel=0.008)  # vent at its left
        rect(g0 + 2.7, 28.0, g0 + 3.5, 28.8, 0.84, MID, z0=0.6, bevel=0.01)
        rect(g0 + 4.0, 28.0, g0 + 4.8, 28.8, 0.84, MID, z0=0.6, bevel=0.01)
        rect(g0 + 4.3, 30.4, g0 + 4.6, 31.8, 0.83, GLOW, z0=0.75, bevel=0.0)
        rect(g1, 30.3, g1 + 1.7, 30.9, 0.6, LIGHT, z0=0.48, bevel=0.01)
        rect(g1, 31.7, g1 + 1.7, 32.3, 0.6, LIGHT, z0=0.48, bevel=0.01)
        rect(g1 + 1.1, 30.3, g1 + 1.7, 32.3, 0.6, LIGHT, z0=0.48, bevel=0.01)
        for nc, glow in ((g0 + 1.0, False), (g0 + 3.6, True)):
            pipe([(nc, 34.6, 0.42), (nc, 36.2, 0.42)], 0.75, LIGHT, sides=10)
            pipe([(nc, 36.2, 0.42), (nc, 36.9, 0.42)], 0.55, GLOW if glow else MID, sides=10)

    # Elbow pipes from the big dome's foot into the side domes, with flanges at both ends.
    for sgn, c0 in ((1, 8.1), (-1, 28.4)):
        cx = lambda d: c0 - sgn * d  # noqa: E731  (outwards from the dome)
        collar(cx(0.1), 18.6, surf(BIG, cx(0.1), 18.6) - 0.06, surf(BIG, cx(0.1), 18.6) + 0.06, 1.7, slot[6])
        pipe([(cx(0.1), 18.4, surf(BIG, cx(0.1), 18.4) + 0.02), (cx(0.6), 19.6, 0.5), (cx(1.0), 20.8, 0.5),
              (cx(1.4), 22.4, 0.5), (cx(1.5), 24.6, 0.42)], 1.1, BRASS, sides=10)
    # The grey pipes down the neck (grey as in the sprite): the outer two bend into the side domes, the middle one runs into the
    # bottom dome's collar; grey clamps where they leave the big dome.
    pipe([(17.05, 21.0, 0.24), (17.05, 29.2, 0.24), (16.6, 30.4, 0.26), (15.4, 30.6, 0.3), (12.6, 30.6, 0.34)],
         0.6, slot[6], sides=8)
    pipe([(20.6, 21.0, 0.24), (20.6, 29.0, 0.24), (21.1, 30.2, 0.26), (22.2, 30.4, 0.3), (24.0, 30.4, 0.34)],
         0.6, slot[6], sides=8)
    pipe([(18.95, 20.8, 0.27), (18.95, 34.0, 0.27)], 0.75, slot[6], sides=10)
    for c, rad in ((17.05, 1.0), (18.95, 1.15), (20.6, 1.0)):
        lib.sweep(bm, [(XE(c), YE(21.8), 0.25, rad * PX, rad * PX), (XE(c), YE(22.8), 0.25, rad * PX, rad * PX)],
                  sides=10, mat=slot[6], smooth=False)
    # Two thin brass pipes from the big dome's lower right (the sprite's bright rod there).
    for off in (0.0, 1.0):
        pipe([(23.6 + off, 20.4 - off * 0.4, 0.42), (24.6 + off, 21.6 - off * 0.4, 0.36),
              (25.4 + off, 23.4 - off * 0.4, 0.34)], 0.45, ROD, sides=6)

    # The bottom dome and its gun port.
    BOT = (18.1, 40.0, 5.95, 5.95, 0.6)
    lib.dome(bm, (XE(BOT[0]), YE(BOT[1]), BASE), (BOT[2] * PX, BOT[3] * PX, BOT[4]), mat=BRASS, segments=20, rings=7)
    collar(18.6, 34.3, BASE + 0.12, BASE + 0.38, 1.8, BRASS_D)
    pc, pr = 18.1, 40.9
    pz = surf(BOT, pc, pr)
    up = (0, 1, 0)
    lib.sweep(bm, [(XE(pc), YE(pr), pz - 0.1, 3.1 * PX, 3.1 * PX), (XE(pc), YE(pr), pz + 0.04, 3.1 * PX, 3.1 * PX),
                   (XE(pc), YE(pr), pz + 0.06, 2.6 * PX, 2.6 * PX)],
              sides=16, mat=BRASS_D, up=up, smooth=False, cap_end=False)
    lib.sweep(bm, [(XE(pc), YE(pr), pz + 0.06, 2.6 * PX, 2.6 * PX), (XE(pc), YE(pr), pz + 0.055, 1.9 * PX, 1.9 * PX),
                   (XE(pc), YE(pr), pz - 0.08, 1.9 * PX, 1.9 * PX)],
              sides=16, mat=slot["bore"], up=up, smooth=False, cap_start=False)

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
