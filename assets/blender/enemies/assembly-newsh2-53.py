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
    ]
    (FLOOR_M, ROCK0, ROCK1, ROCK2, ROCK3, SAND, SAND2, RED, DRED, LRED, DBROWN, BROWN, GOLD,
     PGOLD, LIGHT, METAL, STONE, RECESS) = range(18)
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
    def block(c0, r0, c1, r1, top, mat, bevel=0.5, top_mat=None):
        pts = [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))]
        lib.bevel_prism(bm, pts, FLOOR - 0.03, top, bevel * PX, mat=mat, top_mat=top_mat)

    def pipe(points, r_px, mat, z=None, sides=10):
        h = r_px * PX
        zc = FLOOR + h * 0.9 if z is None else z
        path = [(XE(c), YE(r), zc, h, h) for c, r in points]
        # Round the bends a little by adding points just before and after each corner.
        lib.sweep(bm, path, sides=sides, mat=mat)

    # Red elbow pipe and its housing, top left (columns 3-16, rows 2-16).
    pipe([(5.4, 2.2), (5.4, 6.0), (5.9, 7.6), (7.4, 8.8), (9.0, 9.1), (16.6, 9.1)], 2.6, RED, sides=12)
    block(2.8, 10.2, 11, 16.2, 0.08, RED, bevel=0.8, top_mat=LRED)
    block(11, 11, 13.6, 15.4, 0.03, METAL, bevel=0.4)
    block(11, 15, 16.5, 18, 0.05, RED, bevel=0.5)
    # Two glowing orange lights in dark sockets (columns 14-18, rows 12-14 and 18-20).
    for r0 in (12, 18):
        block(13.4, r0 - 0.6, 19.6, r0 + 3.6, 0.03, RECESS, bevel=0.3)
        block(14, r0, 19, r0 + 3, 0.075, LIGHT, bevel=0.5)

    # Red box (columns 22-27, rows 8-15) and brown posts and a bar along the top.
    block(22, 8, 28, 16, 0.11, RED, bevel=0.8, top_mat=RED)
    block(22.4, 8, 27.6, 9.2, 0.115, LRED, bevel=0.3)
    pipe([(31.5, 3.6), (31.5, 15.2)], 1.0, BROWN)
    pipe([(15.0, 4.5), (28.4, 4.5)], 0.7, GOLD)
    pipe([(41.5, 10.8), (41.5, 13.6)], 0.9, BROWN)

    # Red pipe from the lights across and down the right side, and the thin one across row 27.
    pipe([(18.6, 16.6), (33.2, 16.6), (34.2, 17.2), (34.6, 18.4), (34.6, 33.4)], 1.1, RED)
    pipe([(20.6, 27.5), (35.0, 27.5)], 0.75, LRED)
    pipe([(35.2, 33.6), (31.4, 33.6), (30.4, 34.4), (30.0, 35.6), (30.0, 48.4)], 1.5, RED, sides=12)
    pipe([(30.0, 42.5), (33.6, 42.5), (34.5, 43.4), (34.5, 48.6)], 0.75, DRED)
    pipe([(27.8, 48.5), (35.0, 48.5)], 0.8, DRED)
    # Brown pipe down the right (column 36, rows 17-38) with a stub across at row 17.
    pipe([(36.6, 17.0), (36.6, 38.6)], 0.95, DBROWN)
    pipe([(35.4, 17.6), (39.8, 17.6)], 0.7, BROWN)

    # Grey ribs under the red pipe (row 19) and below (rows 50 and 52).
    for (c0, c1, r) in ((20, 26, 19.5), (30, 34, 19.5), (17.6, 26.4, 50.5), (17.6, 33.6, 52.5)):
        pipe([(c0, r), (c1, r)], 0.6, METAL, sides=6)

    # Brown hatch (columns 23-29, rows 21-26) with grey fins beside it.
    block(23, 21, 30, 27, 0.05, DBROWN, bevel=0.5)
    block(24.2, 22.2, 29.6, 26.6, 0.035, BROWN, bevel=0.3)
    for r in (22.5, 24.5, 26.5):
        pipe([(30.0, r), (33.6, r)], 0.55, ROCK3, sides=6)

    # Brown frame on the left (columns 0-9, rows 17-27) with a red block in it.
    block(-0.5, 17, 10, 28, 0.08, BROWN, bevel=0.6, top_mat=BROWN)
    block(2, 20, 8.5, 26.5, 0.085, RECESS, bevel=0.3)
    block(3, 21, 7, 25.5, 0.13, RED, bevel=0.6, top_mat=LRED)
    pipe([(0.5, 17.4), (0.5, 27.4), (10.2, 27.4)], 0.6, PGOLD, z=0.085)
    pipe([(1.4, 28.0), (1.4, 32.8)], 0.7, GOLD)
    # Red block beside it (columns 9-18, rows 21-26) with a groove, on a dark red stem below.
    block(9, 21, 19, 27, 0.08, DBROWN, bevel=0.5)
    block(10, 21.6, 18.4, 26.4, 0.14, RED, bevel=0.7, top_mat=RED)
    block(14, 21.8, 15, 27, 0.145, DRED, bevel=0.1)
    block(11.5, 26, 17.5, 30, 0.06, DRED, bevel=0.5)
    # Short red pipe below the frame (column 4, rows 29-33).
    pipe([(4.6, 28.6), (4.6, 33.6)], 1.6, RED)

    # Slanted brown panel lower left (columns 6-11, rows 33-47) with a gold rib and a grey rail.
    block(6.6, 33.2, 12, 48, 0.07, DBROWN, bevel=0.6, top_mat=BROWN)
    pipe([(7.2, 35.0), (11.6, 41.6)], 0.8, PGOLD, z=0.07)
    pipe([(6.4, 35.6), (6.4, 41.6)], 0.6, ROCK3, z=0.04)
    # Red block lower middle (columns 13-19, rows 39-47) with a raised top.
    block(13, 39, 20, 48, 0.07, DRED, bevel=0.6)
    block(13.2, 39, 19.4, 42.6, 0.12, RED, bevel=0.6, top_mat=LRED)

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
