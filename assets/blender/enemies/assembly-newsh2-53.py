"""Red machinery block (newsh2.shp frames 15, 17, 53, 55 in a 2x2): a 3D version of its sprites.

Seen in levels 1.30 and 3.17. Four 2x2 enemies make one 48x56 px block of machinery set into
grey rock (sprite.json `assemblyLayout`): on a dark floor sit a red elbow pipe and housing
(top left), two glowing orange lights, a red box, brown posts, a run of red pipes bending down the
right side, a brown hatch with grey fins, a brown frame with a red block in it (left), red blocks
lower down, a slanted brown panel and grey vent ribs, all ringed by boulders and sand.

The whole block is built once in assembly coordinates and cut into the four pieces with
common.split_assembly. It hangs centred on z = 0 like other flying objects. The floor and the
boulders are flat-shaded and take the sprite's colour under each facet; the machinery parts are
modelled as boxes and pipes in the colours of their pixels.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-53.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import math
import random
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b053 as lib  # noqa: E402

NAME = "assembly-newsh2-53"
ROOT = common.repo_root(__file__)
W, H = 48, 56  # the assembly grid in pixels; its centre is the Blender origin
PX = 1 / 12
FLOOR = -0.07  # top of the floor


def XE(e):
    """Grid pixel edge (column) to Blender X."""
    return (e - W / 2) / 12


def YE(e):
    """Grid pixel edge (row) to Blender Y."""
    return (H / 2 - e) / 12


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nsh2a53"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.2, roughness=0.8),  # 0 dark floor
        pal(4, metallic=0.05, roughness=0.9),  # 1 dark rock
        pal(7, metallic=0.05, roughness=0.85),  # 2 mid rock
        pal(9, metallic=0.05, roughness=0.8),  # 3 light rock
        pal(11, metallic=0.05, roughness=0.75),  # 4 pale rock, bright rails
        pal(169, metallic=0.0, roughness=0.9),  # 5 sand
        pal(171, metallic=0.0, roughness=0.85),  # 6 pale sand
        pal(71, metallic=0.4, roughness=0.4),  # 7 red
        pal(68, metallic=0.35, roughness=0.5),  # 8 dark red
        pal(74, metallic=0.4, roughness=0.35),  # 9 light red
        pal(163, metallic=0.3, roughness=0.6),  # 10 dark brown
        pal(165, metallic=0.3, roughness=0.55),  # 11 brown
        pal(24, metallic=0.4, roughness=0.45),  # 12 golden brown
        pal(27, metallic=0.4, roughness=0.4),  # 13 pale gold
        pal(123, emission_strength=4.0),  # 14 orange lights
        pal(7, metallic=0.6, roughness=0.35),  # 15 grey metal
        pal(104, metallic=0.2, roughness=0.6),  # 16 blue-grey stones
        pal(16, metallic=0.2, roughness=0.8),  # 17 near-black recess
        common.palette_material(sprite, 71, tag + "lens", metallic=0.1, roughness=0.12),  # 18 lens
    ]
    (FLOOR_M, ROCK0, ROCK1, ROCK2, ROCK3, SAND, SAND2, RED, DRED, LRED, DBROWN, BROWN, GOLD,
     PGOLD, LIGHT, METAL, STONE, RECESS, LENS) = range(19)
    bm = bmesh.new()
    rng = random.Random(53)

    def sample(x, y):
        c, r = math.floor(x * 12 + W / 2), math.floor(H / 2 - y * 12)
        if 0 <= r < H and 0 <= c < W:
            return grid[r][c]
        return None

    def ground_slot(i):
        if i <= 3:
            return FLOOR_M
        if i <= 15:
            return ROCK0 if i <= 5 else ROCK1 if i <= 8 else ROCK2 if i <= 9 else ROCK3
        if 16 <= i <= 28:
            return GOLD if i >= 22 else RECESS
        if 65 <= i <= 78:
            return DRED
        if 80 <= i <= 106:
            return STONE
        if 116 <= i <= 125:
            return LIGHT
        if 160 <= i <= 166:
            return DBROWN
        if 167 <= i <= 169:
            return SAND
        if 170 <= i <= 173:
            return SAND2
        return None

    # ---- the floor: a slab with a lightly broken top, painted from the sprite ----
    first = len(bm.faces)
    nx, ny = 24, 28
    verts = [[bm.verts.new((XE(-0.6 + (W + 1.2) * i / nx), YE(-0.6 + (H + 1.2) * j / ny),
                            FLOOR)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((verts[j + 1][i], verts[j + 1][i + 1], verts[j][i + 1], verts[j][i]))
    def floor_slot(i, x, y):
        c, r = x * 12 + W / 2, H / 2 - y * 12
        if 4 <= c <= 40 and 4 <= r <= 49 and i <= 8:
            return FLOOR_M  # the dark machinery floor; its grey specks are shading, not rock
        return ground_slot(i)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        m = f.calc_center_median()
        i = sample(m.x, m.y)
        if i is not None and i >= 0:
            slot = floor_slot(i, m.x, m.y)
            if slot is not None:
                f.material_index = slot
    # Its underside and sides.
    lib.box(bm, XE(-0.6), YE(H + 0.6), XE(W + 0.6), YE(-0.6), -0.16, FLOOR - 0.02, mat=FLOOR_M)

    # ---- boulders and sand round the edges, painted from the sprite ----
    first = len(bm.faces)
    boulders = [  # (column, row, rx px, ry px, rz)
        (2.5, 1.2, 4.6, 3.0, 0.1), (1.5, 7.5, 2.8, 4.0, 0.12), (1.5, 13.0, 2.6, 3.0, 0.1),
        (3.0, 16.0, 4.0, 1.8, 0.08), (1.8, 38.0, 3.0, 5.0, 0.12), (3.0, 48.0, 4.6, 5.0, 0.15),
        (6.0, 54.6, 5.5, 2.2, 0.1), (12.0, 1.4, 4.2, 3.0, 0.12), (19.0, 1.5, 4.0, 3.2, 0.12),
        (26.6, 1.0, 3.0, 2.2, 0.09), (33.0, 1.5, 4.0, 3.0, 0.12), (23.0, 5.5, 3.6, 1.8, 0.07),
        (10.5, 4.6, 3.0, 1.8, 0.07), (44.5, 1.5, 3.6, 3.0, 0.12), (44.5, 7.5, 3.6, 3.6, 0.14),
        (44.0, 13.6, 3.2, 3.0, 0.1), (44.5, 20.0, 3.6, 4.6, 0.15), (44.5, 28.0, 3.6, 4.0, 0.13),
        (44.5, 37.0, 3.6, 5.0, 0.14), (44.5, 46.5, 3.6, 5.0, 0.15), (44.0, 53.0, 4.0, 3.0, 0.12),
        (40.4, 46.0, 1.8, 2.6, 0.08), (11.5, 51.6, 4.2, 3.0, 0.1), (20.0, 55.2, 4.0, 1.4, 0.06),
        (30.5, 54.9, 5.0, 1.8, 0.08), (37.6, 51.0, 3.0, 3.0, 0.1), (39.6, 5.0, 2.2, 3.0, 0.08),
    ]
    for c, r, rx, ry, rz in boulders:
        seeds = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.08, 0.16))
                 for _ in range(4)]
        def bump(d, seeds=seeds):
            return 1.0 + sum(a * max(0.0, d.x * u + d.y * v + d.z * w) for u, v, w, a in seeds)
        lib.ellipsoid(bm, (XE(c + 0.5), YE(r + 0.5), FLOOR - rz * 0.3), (rx * PX, ry * PX, rz), mat=ROCK1,
                      segments=10, rings=6, smooth=False, bump=bump)
    lib.paint(bm, first, sample, lambda i: ROCK1 if i <= 3 else ground_slot(i), up_only=True)

    # ---- machinery ----
    # Heights follow the concept's reading: a dark central housing framed by red trim, boxes
    # and housings stacked a few px above the black floor, round parts as tall as they are wide.
    def block(c0, r0, c1, r1, top, mat, bevel=0.5, top_mat=None, base=None):
        pts = [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))]
        lib.bevel_prism(bm, pts, FLOOR - 0.03 if base is None else base, top, bevel * PX, mat=mat,
                        top_mat=top_mat)

    def pipe(points, r_px, mat, z=None, sides=10):
        h = r_px * PX
        zc = FLOOR + h * 0.9 if z is None else z
        path = [(XE(c), YE(r), zc, h, h) for c, r in points]
        lib.sweep(bm, path, sides=sides, mat=mat)

    def canister(c0, c1, r, r_px, z, mat, sides=12):
        """A cylinder lying along x (sprite columns c0-c1) at row r."""
        h = r_px * PX
        lib.sweep(bm, [(XE(c0), YE(r), z, h, h), (XE(c1), YE(r), z, h, h)], sides=sides, mat=mat)

    # Chrome fittings and the gold pipe across the top (rows 1-5).
    canister(6.4, 12.6, 2.6, 1.1, FLOOR + 0.1, METAL)
    for c in (7.2, 9.6, 11.8):
        canister(c - 0.4, c + 0.4, 2.6, 1.45, FLOOR + 0.1, ROCK3)
    canister(27.6, 33.0, 2.6, 1.1, FLOOR + 0.1, METAL)
    for c in (28.4, 30.6, 32.4):
        canister(c - 0.4, c + 0.4, 2.6, 1.45, FLOOR + 0.1, ROCK3)
    pipe([(12.6, 4.5), (27.6, 4.5)], 0.8, GOLD)

    # Red pump housing (columns 3-11, rows 10-16) under the elbow pipe, and the step to its right.
    block(2.8, 9.6, 11, 16.2, 0.24, RED, bevel=0.9, top_mat=LRED)
    block(11, 11, 13.6, 15.4, 0.12, METAL, bevel=0.4)
    block(11, 15, 18.6, 18, 0.14, RED, bevel=0.5)
    # The elbow pipe, round and resting on the housing (columns 3-16, rows 2-9).
    pipe([(5.4, 2.2), (5.4, 6.0), (5.9, 7.6), (7.4, 8.8), (9.0, 9.1), (16.6, 9.1)], 2.6, RED,
         z=0.2, sides=14)
    pipe([(5.4, 1.4), (5.4, 2.6)], 3.0, DRED, z=0.2, sides=14)  # flange where it leaves the rock
    pipe([(15.8, 9.1), (16.9, 9.1)], 2.9, DRED, z=0.2, sides=14)  # flange at its end

    # Two glowing canister lights in dark sockets (columns 14-18, rows 12-14 and 18-20).
    for r0 in (12, 18):
        block(13.2, r0 - 0.7, 19.8, r0 + 3.7, 0.08, RECESS, bevel=0.3)
        canister(14.0, 19.0, r0 + 1.5, 1.6, 0.08 + 1.2 * PX, LIGHT, sides=12)
        for c in (13.4, 19.0):
            canister(c, c + 0.6, r0 + 1.5, 1.9, 0.08 + 1.2 * PX, METAL, sides=12)

    # Red box (columns 22-27, rows 8-15): a lid on a body, with a seam between them.
    block(22, 11.2, 28, 16, 0.30, RED, bevel=0.7, top_mat=RED)
    block(22.2, 8, 27.8, 11.4, 0.38, RED, bevel=0.7, top_mat=LRED, base=0.2)
    block(21.8, 10.9, 28.2, 11.7, 0.31, DRED, bevel=0.2, base=0.2)
    # Brown posts.
    pipe([(31.5, 3.6), (31.5, 15.2)], 1.0, BROWN, z=FLOOR + 0.12)
    pipe([(41.5, 10.8), (41.5, 13.6)], 0.9, BROWN)

    # Dark central housing (columns 19-34, rows 17-27, and down the right to row 33), built round
    # the hatch opening (columns 23-30, rows 20-27) so the hatch sits recessed in it.
    HT = 0.17
    block(18.6, 17.6, 34.6, 20.4, HT, FLOOR_M, bevel=0.4)
    block(18.6, 20.0, 23.2, 27.6, HT, FLOOR_M, bevel=0.4)
    block(33.4, 20.0, 34.6, 27.6, HT, FLOOR_M, bevel=0.2)
    block(28.0, 27.2, 34.6, 33.2, HT - 0.02, FLOOR_M, bevel=0.4)
    # The hatch: a brown panel set down in the opening.
    block(23, 20.2, 30, 27.2, 0.06, DBROWN, bevel=0.3)
    block(24.2, 21.4, 29.2, 26.4, 0.085, BROWN, bevel=0.4)
    # Louvres: grey ribs in the housing top beside the hatch (rows 22-26) and along row 19.
    block(29.8, 20.0, 33.6, 27.6, HT - 0.06, RECESS, bevel=0.2)
    for r in (22.4, 24.2, 26.0):
        block(30.0, r - 0.5, 33.4, r + 0.5, HT - 0.02, ROCK3, bevel=0.25, base=HT - 0.08)
    for (c0, c1) in ((20, 26), (30, 34)):
        block(c0, 19.0, c1, 20.0, HT + 0.02, ROCK3, bevel=0.3, base=HT - 0.02)
    # Angular red trim: along the top (rows 16-18), down the right (col 34) and along row 27.
    block(18.6, 16.0, 35.4, 18.0, HT + 0.05, RED, bevel=0.5, top_mat=LRED)
    block(33.8, 17.6, 35.4, 33.6, HT + 0.05, RED, bevel=0.4)
    block(20.6, 27.0, 35.2, 28.2, HT + 0.03, LRED, bevel=0.4)

    # Red pipe turning down the right side, its thin branch and the bar across row 48.
    pipe([(35.2, 33.6), (31.4, 33.6), (30.4, 34.4), (30.0, 35.6), (30.0, 48.4)], 1.5, RED,
         z=FLOOR + 0.16, sides=12)
    pipe([(30.0, 42.5), (33.6, 42.5), (34.5, 43.4), (34.5, 48.6)], 0.8, DRED, z=FLOOR + 0.08)
    pipe([(27.8, 48.5), (35.0, 48.5)], 0.8, DRED, z=FLOOR + 0.08)
    # Brown pipe down the right (column 36, rows 17-38) with a stub across at row 17.
    pipe([(36.6, 17.0), (36.6, 38.6)], 1.0, DBROWN)
    pipe([(35.4, 17.6), (39.8, 17.6)], 0.7, BROWN)

    # Grey ribs low down (rows 50 and 52).
    for (c0, c1, r) in ((17.6, 26.4, 50.5), (17.6, 33.6, 52.5)):
        pipe([(c0, r), (c1, r)], 0.6, METAL, sides=6)

    # Brass box on the left (columns 0-10, rows 17-28) with a round red lens in a dark socket.
    block(-0.5, 17, 10, 28, 0.19, BROWN, bevel=0.8, top_mat=BROWN)
    block(1.8, 19.6, 8.4, 26.4, 0.215, RECESS, bevel=0.4, base=0.1)
    lib.dome(bm, (XE(5.0), YE(23.0), 0.2), (2.6 * PX, 2.6 * PX, 2.2 * PX), mat=LENS,
             segments=16, rings=5)
    pipe([(0.5, 17.4), (0.5, 27.4), (10.2, 27.4)], 0.7, PGOLD, z=0.17)
    pipe([(1.4, 28.0), (1.4, 32.8)], 0.7, GOLD)
    # Twin red panels beside it (columns 11-18, rows 22-26) over a vented dark red skirt.
    block(9, 21, 19, 27, 0.12, DBROWN, bevel=0.5)
    block(10.2, 21.6, 14.4, 26.4, 0.22, RED, bevel=0.8, top_mat=RED)
    block(14.8, 21.6, 18.8, 26.4, 0.22, RED, bevel=0.8, top_mat=RED)
    block(11.0, 26.0, 18.2, 30.0, 0.12, DRED, bevel=0.5)
    for c in (12.0, 13.4, 15.6, 17.0):
        block(c - 0.3, 26.8, c + 0.3, 29.4, 0.125, RECESS, bevel=0.05, base=0.08)
    # Short red pipe below the brass box (column 4, rows 29-33).
    pipe([(4.6, 28.6), (4.6, 33.6)], 1.6, RED)

    # Slanted brass panel lower left (columns 6-11, rows 33-47): raised, with a gold rib and a rail.
    block(6.6, 33.2, 12, 48, 0.17, DBROWN, bevel=0.9, top_mat=BROWN)
    pipe([(7.4, 35.2), (11.4, 41.4)], 0.8, PGOLD, z=0.17)
    pipe([(6.2, 35.6), (6.2, 41.6)], 0.7, ROCK3, z=0.08)
    # Red block lower middle (columns 13-19, rows 39-47) with a raised top plate.
    block(13, 39, 20, 48, 0.14, DRED, bevel=0.6)
    block(13.2, 39, 19.4, 42.6, 0.23, RED, bevel=0.7, top_mat=LRED, base=0.1)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-53")
    sprite = common.load_sprite(ROOT, "newsh2-53")
    sprite["colors"] = colors
    obj = build(sprite, grid)
    cx0, cy0 = x0 + W // 2, y0 + H // 2
    pieces = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in layout]
    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_assembly(ROOT, obj, pieces, out, grid, colors, size=W / 12)


if __name__ == "__main__":
    main()
