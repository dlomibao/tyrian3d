"""Red machinery block (newsh2.shp frames 15, 17, 53, 55 in a 2x2): a 3D version of its sprites.

Seen in levels 1.30 and 3.17. Four 2x2 enemies make one 48x56 px block of machinery set into
grey rock (sprite.json `assemblyLayout`): on a dark floor sit a red elbow pipe and housing
(top left), two glowing orange lights, a red box, brown posts, a run of red pipes bending down the
right side, a brown hatch with grey fins, a brown frame with a red block in it (left), red blocks
lower down, a slanted brown panel and grey vent ribs, all ringed by boulders and sand.

The whole block is built once in assembly coordinates and cut into the four pieces with
common.split_assembly. It hangs centred on z = 0 like other flying objects. The floor and the
boulders are flat-shaded and take the sprite's colour under each facet. The machinery is traced
from the concept (assets/blender/features/concepts/assembly-newsh2-53.jpg, registered to the
sprite by tools/concept_maps.py) so the baked texture (assets/blender/texture_bake.py) lands on
the matching parts: two red elbow pipes and a chrome-coupled top pipe, two striped canister lights,
a chamfered red tower, a brass lens box, twin vented red panels, a gunmetal housing with a sunken
hatch and louvres framed by flat red trim bars, a drum with a stepped red block, a louvred box and
a brass chevron block.

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
        pal(122, emission_strength=4.0),  # 14 orange lights (the concept glows orange)
        pal(7, metallic=0.6, roughness=0.35),  # 15 grey metal
        pal(104, metallic=0.2, roughness=0.6),  # 16 blue-grey stones
        pal(16, metallic=0.2, roughness=0.8),  # 17 near-black recess
        common.palette_material(sprite, 71, tag + "lens", metallic=0.1, roughness=0.12),  # 18 lens
        pal(4, metallic=0.55, roughness=0.4),  # 19 dark gunmetal housing
        pal(164, metallic=0.35, roughness=0.55),  # 20 brown hatch, brass block faces
        pal(22, metallic=0.5, roughness=0.4),  # 21 brass
    ]
    (FLOOR_M, ROCK0, ROCK1, ROCK2, ROCK3, SAND, SAND2, RED, DRED, LRED, DBROWN, BROWN, GOLD,
     PGOLD, LIGHT, METAL, STONE, RECESS, LENS, HOUSING, HATCH, BRASS) = range(22)
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
        (14.5, 51.2, 3.0, 2.0, 0.06), (22.5, 51.6, 4.6, 2.2, 0.07), (30.0, 51.4, 3.4, 2.0, 0.06),
    ]
    for c, r, rx, ry, rz in boulders:
        seeds = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.08, 0.16))
                 for _ in range(4)]
        def bump(d, seeds=seeds):
            return 1.0 + sum(a * max(0.0, d.x * u + d.y * v + d.z * w) for u, v, w, a in seeds)
        lib.ellipsoid(bm, (XE(c + 0.5), YE(r + 0.5), FLOOR - rz * 0.3), (rx * PX, ry * PX, rz), mat=ROCK1,
                      segments=10, rings=6, smooth=False, bump=bump)
    lib.paint(bm, first, sample, lambda i: ROCK1 if i <= 3 else ground_slot(i), up_only=True)

    # ---- machinery, traced from the concept (assets/blender/features/concepts/) ----
    # Coordinates are sprite columns/rows of the 48x56 grid; heights in px above the floor.
    # Hard-surface machinery: bevelled plates stacked in height, round only for the pipes, the
    # canister lights, the lens and the drum the concept draws round.
    recalc_from = len(bm.faces)

    def hz(px):
        return FLOOR + px * PX

    def blk(c0, r0, c1, r1, top, mat, bevel=0.4, top_mat=None, base=None):
        pts = [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))]
        lib.bevel_prism(bm, pts, FLOOR - 0.03 if base is None else hz(base), hz(top), bevel * PX,
                        mat=mat, top_mat=top_mat)

    def poly(cr, top, mat, bevel=0.4, top_mat=None, base=None):
        pts = [(XE(c), YE(r)) for c, r in cr]
        lib.bevel_prism(bm, pts, FLOOR - 0.03 if base is None else hz(base), hz(top), bevel * PX,
                        mat=mat, top_mat=top_mat)

    def bar(p0, p1, w, top, mat, base=None, bevel=0.25):
        """A flat bar (crisp, not round) of width w px from p0 to p1 (column, row)."""
        x0, y0, x1, y1 = XE(p0[0]), YE(p0[1]), XE(p1[0]), YE(p1[1])
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        nx, ny = -dy / n * w * PX / 2, dx / n * w * PX / 2
        pts = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
        lib.bevel_prism(bm, pts, FLOOR - 0.03 if base is None else hz(base), hz(top), bevel * PX, mat=mat)

    def tube(points, r_px, z, mat, sides=12):
        """A round pipe through (column, row[, radius px]) points, centred z px above the floor."""
        path = []
        for p in points:
            rr = (p[2] if len(p) > 2 else r_px) * PX
            path.append((XE(p[0]), YE(p[1]), hz(z), rr, rr))
        lib.sweep(bm, path, sides=sides, mat=mat)

    def rings_x(row, z, segs, mat, sides=12):
        """A pipe along x built from (c0, c1, radius px) sections: couplings, collars, grooves."""
        pts = []
        for c0, c1, rad in segs:
            pts += [(c0, row, rad), (c1, row, rad)]
        tube(pts, 1, z, mat, sides)

    def half_cyl_y(c0, c1, r0, r1, height, mat, seg=14):
        """A drum lying along the rows: a half-ellipse profile across the columns, extruded."""
        first = len(bm.faces)
        cx, rx, b = (XE(c0) + XE(c1)) / 2, (c1 - c0) / 2 * PX, FLOOR - 0.03
        prof = [(cx - rx * math.cos(math.pi * k / seg), b + (height * PX + 0.03) * math.sin(math.pi * k / seg))
                for k in range(seg + 1)]
        ends = []
        for y in (YE(r1), YE(r0)):
            ends.append([bm.verts.new((x, y, z)) for x, z in prof])
        for k in range(seg):
            bm.faces.new((ends[0][k], ends[0][k + 1], ends[1][k + 1], ends[1][k]))
        bm.faces.new(ends[0])
        bm.faces.new(list(reversed(ends[1])))
        lib._faces_done(bm, first, mat, True)

    def circle(c, r, rad, n=16):
        return [(c + rad * math.cos(2 * math.pi * k / n), r + rad * math.sin(2 * math.pi * k / n)) for k in range(n)]

    # -- The top pipe (rows 1-6): chrome couplings at both ends, a red flange, a rod, a spring.
    TZ = 2.4
    rings_x(3.6, TZ, [(6.6, 7.0, 1.6), (7.1, 8.4, 2.1), (8.45, 10.0, 1.6), (10.05, 12.0, 2.1),
                      (12.05, 12.5, 1.5)], METAL)
    rings_x(3.6, TZ, [(12.5, 13.0, 1.6), (13.05, 14.6, 1.9), (14.65, 15.0, 1.4)], RED)
    rings_x(3.6, TZ, [(14.8, 26.2, 0.8)], GOLD, sides=10)
    rings_x(3.6, TZ, [(26.0 + 0.5 * i, 26.25 + 0.5 * i, 1.15 if i % 2 else 0.8) for i in range(5)], METAL, sides=10)
    rings_x(3.6, TZ, [(28.4, 29.6, 1.6), (29.65, 31.4, 2.0), (31.45, 32.0, 1.5), (32.05, 33.4, 2.0),
                      (33.45, 34.9, 1.0)], METAL)
    # The thin red elbow pipe: out of the left coupling, bending down column 5 to the lens box.
    TP = 1.25
    tube([(6.8, 3.6), (5.9, 3.75), (5.3, 4.4), (5.1, 5.4), (5.1, 15.2)], TP, TZ, RED)
    tube([(5.1, 6.4, 1.55), (5.1, 7.6, 1.55)], 1, TZ, METAL)  # coupling
    tube([(5.1, 14.4, 1.8), (5.1, 16.2, 1.8)], 1, TZ, METAL)  # flange into the box
    # The big red elbow pipe: up column 8, along row 8.7, down column 20.7 behind the lights.
    BP, BZ = 1.65, 3.4
    tube([(8.1, 15.6), (8.1, 11.0), (8.3, 9.9), (9.0, 9.0), (10.2, 8.7), (19.0, 8.7), (20.0, 9.0),
          (20.6, 9.8), (20.8, 11.0), (20.8, 16.0)], BP, BZ, RED, sides=14)
    tube([(8.1, 11.0, 1.95), (8.1, 12.0, 1.95)], 1, BZ, RED, sides=14)  # band on the left leg
    tube([(12.3, 8.7, 1.95), (13.2, 8.7, 1.95)], 1, BZ, RED, sides=14)  # band on the run
    tube([(16.2, 8.7, 2.0), (16.8, 8.7, 2.0), (16.85, 8.7, 1.75), (17.3, 8.7, 1.75), (17.35, 8.7, 2.0),
          (18.0, 8.7, 2.0)], 1, BZ, METAL, sides=14)  # chrome coupling
    tube([(20.8, 12.6, 1.95), (20.8, 13.6, 1.95)], 1, BZ, RED, sides=14)
    tube([(8.1, 14.6, 2.3), (8.1, 16.2, 2.3)], 1, BZ, METAL, sides=14)  # base flange

    # -- Two canister lights stacked between the pipes (columns 12-19, rows 11.5-15 and 17.5-21),
    # joined by a collar, on a dark socket, with a thin red feed pipe on their left.
    blk(11.8, 10.8, 20.0, 21.8, 1.2, RECESS, bevel=0.3)
    LZ = 3.0
    for rc in (13.25, 19.25):
        rings_x(rc, LZ, [(12.2, 12.6, 1.5), (12.65, 13.4, 1.9)], METAL)
        rings_x(rc, LZ, [(13.4, 18.4, 1.65)], LIGHT)
        for c in (14.1, 15.6, 17.1):  # dark hazard bands round the glass
            rings_x(rc, LZ, [(c, c + 0.55, 1.72)], RECESS, sides=12)
        rings_x(rc, LZ, [(18.4, 19.15, 1.9), (19.2, 19.6, 1.5)], METAL)
    tube([(16.8, 14.6, 1.45), (16.8, 15.4, 1.45), (16.8, 15.45, 1.7), (16.8, 16.3, 1.7), (16.8, 16.35, 1.45),
          (16.8, 17.7, 1.45)], 1, LZ, METAL)
    tube([(16.8, 10.0, 1.2), (16.8, 11.5, 1.2)], 1, LZ, BROWN)
    tube([(12.4, 12.9), (11.6, 12.9), (11.3, 13.5), (11.3, 19.6), (11.6, 20.2), (12.4, 20.2)], 0.6, 1.8, RED, sides=8)
    blk(11.0, 15.4, 15.4, 17.6, 2.6, RED, bevel=0.4, top_mat=LRED)  # the red tee between them

    # -- Red tower (columns 22-28.5, rows 7.5-15.5): a chamfered lid on a body, a seam between.
    blk(22.0, 11.4, 28.6, 15.8, 5.0, RED, bevel=0.6)
    blk(21.8, 11.0, 28.8, 11.9, 5.2, DRED, bevel=0.2, base=3.0)
    poly([(22.9, 7.4), (27.7, 7.4), (28.5, 8.2), (28.5, 11.4), (22.1, 11.4), (22.1, 8.2)], 6.6, RED,
         bevel=0.9, top_mat=LRED, base=3.0)
    # The housing's nub behind it and the brass bracket on it (columns 28-33, rows 13-16).
    blk(28.4, 13.0, 31.4, 16.2, 4.0, HOUSING, bevel=0.4)
    blk(31.4, 13.4, 33.0, 15.8, 4.4, BRASS, bevel=0.3)
    tube([(31.8, 6.8), (31.8, 13.2)], 0.8, 1.2, BROWN, sides=8)  # brown post above it

    # -- The lens box (columns 0-10.5, rows 16.5-33.5): a brass frame round a dark panel with a
    # glossy red lens in a chrome bezel, and a lower bay holding a red block.
    LB = 4.6
    blk(0.0, 16.4, 1.2, 27.4, LB, PGOLD, bevel=0.3)
    blk(1.2, 16.4, 10.6, 18.2, LB, BROWN, bevel=0.4)
    blk(9.2, 18.2, 10.6, 27.4, LB, BROWN, bevel=0.3)
    blk(1.2, 18.2, 2.0, 26.2, LB - 0.3, BROWN, bevel=0.2)
    blk(1.2, 26.2, 10.6, 27.6, LB, GOLD, bevel=0.4)
    blk(1.6, 17.8, 9.6, 26.6, 3.4, DBROWN, bevel=0.3)  # the recessed panel
    lib.prism(bm, [(XE(c), YE(r)) for c, r in circle(5.3, 22.5, 3.1)], hz(2.5), hz(4.6), mat=METAL)
    lib.prism(bm, [(XE(c), YE(r)) for c, r in circle(5.3, 22.5, 2.6)], hz(4.0), hz(4.75), mat=RECESS)
    lib.dome(bm, (XE(5.3), YE(22.5), hz(4.6)), (2.45 * PX, 2.45 * PX, 1.9 * PX), mat=LENS, segments=16, rings=5)
    # Lower bay (rows 27.6-33.6): frame, dark floor, red block.
    blk(0.0, 27.4, 1.8, 33.6, 3.8, GOLD, bevel=0.3)
    blk(1.8, 27.6, 10.6, 29.0, 3.8, HATCH, bevel=0.3)
    blk(9.2, 29.0, 10.6, 33.6, 3.6, DBROWN, bevel=0.3)
    blk(1.8, 32.8, 9.2, 33.6, 3.0, DBROWN, bevel=0.2)
    blk(1.8, 29.0, 9.2, 32.8, 1.4, RECESS, bevel=0.1)
    poly([(2.8, 29.4), (5.8, 29.4), (5.8, 30.6), (6.8, 30.6), (6.8, 33.2), (2.8, 33.2)], 3.4, RED,
         bevel=0.5, top_mat=RED)

    # -- Twin red panels (columns 11-19, rows 21.5-31): a plate on top, a vented skirt below.
    for a in (11.0, 15.0):
        blk(a, 21.2, a + 3.9, 31.0, 2.0, DRED, bevel=0.2)
        poly([(a + 0.7, 21.3), (a + 3.8, 21.3), (a + 3.8, 25.6), (a, 25.6), (a, 22.0)], 4.6, RED,
             bevel=0.6, top_mat=RED)
        blk(a, 25.4, a + 0.8, 30.8, 4.0, RED, bevel=0.3)
        blk(a + 3.1, 25.4, a + 3.9, 30.8, 4.0, RED, bevel=0.3)
        blk(a + 0.8, 25.6, a + 3.1, 26.2, 3.8, RED, bevel=0.2)
        for r in (26.9, 27.9, 28.9, 29.9):
            blk(a + 0.8, r - 0.3, a + 3.1, r + 0.3, 3.2, DRED, bevel=0.15, base=1.5)

    # -- Dark central housing (columns 19-37, rows 16-40): one slab with the hatch and the vents
    # set into it, framed by flat red trim bars.
    HB, HT = 2.0, 3.6  # recess floor and housing top
    poly([(19.0, 16.2), (35.6, 16.2), (35.6, 40.0), (29.0, 40.0), (29.0, 37.2), (25.6, 37.2),
          (19.4, 31.4), (19.0, 31.4)], HB, HOUSING, bevel=0.2)
    blk(19.0, 17.4, 34.2, 20.4, HT, HOUSING, bevel=0.4, base=HB - 0.1)
    blk(19.0, 20.4, 19.6, 26.8, HT, HOUSING, bevel=0.15, base=HB - 0.1)
    blk(19.6, 20.4, 22.6, 21.6, HT, HOUSING, bevel=0.2, base=HB - 0.1)
    blk(19.6, 25.8, 22.6, 26.8, HT, HOUSING, bevel=0.2, base=HB - 0.1)
    blk(22.1, 21.6, 22.6, 25.8, HT, HOUSING, bevel=0.1, base=HB - 0.1)
    blk(29.6, 20.4, 30.2, 26.8, HT, HOUSING, bevel=0.1, base=HB - 0.1)
    # The hatch (columns 22.6-29.6, rows 20.4-26.6): brown planks set down in the opening.
    blk(22.6, 20.4, 29.6, 26.8, 2.4, HATCH, bevel=0.3, base=HB - 0.1)
    for c in (24.4, 26.1, 27.8):
        blk(c - 0.12, 20.7, c + 0.12, 26.4, 2.45, DBROWN, bevel=0.0, base=2.0)
    # Louvres: slats over a dark recess, left of the hatch (rows 21.6-25.8) and right (20.4-26.6).
    blk(19.6, 21.6, 22.1, 25.8, HB + 0.2, RECESS, bevel=0.0, base=HB - 0.1)
    for r in (22.2, 23.0, 23.8, 24.6, 25.4):
        blk(19.8, r - 0.22, 21.9, r + 0.22, HT - 0.5, METAL, bevel=0.1, base=HB)
    blk(30.2, 20.4, 34.2, 26.8, HB + 0.2, RECESS, bevel=0.0, base=HB - 0.1)
    for r in (21.0, 21.85, 22.7, 23.55, 24.4, 25.25, 26.1):
        blk(30.5, r - 0.25, 33.8, r + 0.25, HT - 0.4, METAL, bevel=0.1, base=HB)
    # Below the middle trim (rows 28-37): a plate with the slanted lower edge, and vertical slots.
    poly([(19.0, 28.0), (29.4, 28.0), (29.4, 32.6), (28.8, 32.6), (28.8, 37.0), (25.7, 37.0),
          (19.6, 31.0), (19.0, 31.0)], HT - 0.4, HOUSING, bevel=0.5, base=HB - 0.1)
    blk(29.4, 28.0, 34.2, 32.6, HB + 0.3, RECESS, bevel=0.0, base=HB - 0.1)
    for c in (30.0, 31.6, 33.2):
        blk(c - 0.45, 28.2, c + 0.45, 32.4, HT - 0.6, HOUSING, bevel=0.2, base=HB)
    # The outer rim down the right (columns 35.6-37), slanting in at the bottom, and its brass plate.
    poly([(35.4, 16.0), (36.4, 16.0), (37.0, 16.8), (37.0, 38.6), (36.0, 46.6), (35.4, 46.6)], HT + 0.6,
         HOUSING, bevel=0.6)
    blk(37.0, 22.6, 38.2, 34.6, 2.6, BRASS, bevel=0.3)
    # Red trim, flat bars with crisp edges: the top (rows 16-17.6), down the right (columns 34-35.6),
    # across row 27, and the "P" below: across row 33, down columns 29-31, and the box round the switch.
    TR = HT + 0.8
    blk(19.0, 16.0, 35.6, 17.6, TR, RED, bevel=0.4, top_mat=LRED)
    blk(34.0, 17.6, 35.6, 34.4, TR, RED, bevel=0.4)
    blk(20.8, 26.6, 34.0, 28.0, TR - 0.2, RED, bevel=0.4, top_mat=LRED)
    blk(28.8, 32.6, 34.0, 34.4, TR, RED, bevel=0.4)
    blk(28.8, 34.4, 31.2, 48.8, TR, RED, bevel=0.4)
    blk(31.2, 40.2, 35.4, 41.8, TR - 0.4, DRED, bevel=0.3)
    blk(34.2, 41.8, 35.4, 48.8, TR - 0.4, DRED, bevel=0.3)
    blk(31.2, 47.6, 34.2, 48.8, TR - 0.4, DRED, bevel=0.3)
    blk(31.2, 41.8, 34.2, 47.6, 1.4, RECESS, bevel=0.1)
    blk(31.4, 42.8, 32.9, 47.3, 2.8, BRASS, bevel=0.3, top_mat=GOLD)  # the brass switch
    blk(31.9, 43.4, 32.5, 45.2, 3.4, PGOLD, bevel=0.15, base=2.6)

    # -- Lower middle: a dark drum lying along the rows (columns 12.6-23.6, rows 32.8-48), a stepped
    # red block on it, gear ribs down its right side, a louvred box and a thin rod with a red cap.
    half_cyl_y(12.6, 23.6, 32.8, 48.2, 4.4, HOUSING)
    blk(18.4, 33.2, 19.8, 37.6, 4.6, METAL, bevel=0.3)  # strap across the drum's top
    poly([(13.0, 38.8), (18.8, 38.8), (18.8, 41.4), (16.4, 41.4), (16.4, 42.4), (13.0, 42.4)], 5.6, RED,
         bevel=0.5, top_mat=LRED, base=2.0)
    poly([(13.0, 42.4), (16.4, 42.4), (16.4, 43.2), (19.0, 43.2), (19.0, 47.4), (13.0, 47.4)], 5.2, DRED,
         bevel=0.5, base=2.0)
    for i in range(6):
        r = 36.8 + 1.6 * i
        blk(23.0, r, 24.8, r + 0.9, 2.8, METAL, bevel=0.2)
    blk(24.6, 37.4, 28.8, 43.6, HT - 0.2, HOUSING, bevel=0.4)
    blk(25.2, 38.2, 28.4, 42.8, HT - 0.15, RECESS, bevel=0.0, base=2.0)
    for r in (38.8, 39.8, 40.8, 41.8):
        blk(25.3, r - 0.25, 28.3, r + 0.25, HT, HOUSING, bevel=0.1, base=2.4)
    tube([(22.0, 45.0), (28.8, 45.0)], 0.65, 1.6, BROWN, sides=8)
    tube([(20.8, 45.0, 1.1), (22.0, 45.0, 1.1)], 1, 1.6, RED, sides=10)

    # -- Brass armour block lower left (columns 7-13, rows 33-48): two plates meeting at a chevron,
    # gold edge ribs, and a chrome rail down its left side.
    poly([(7.4, 33.0), (12.9, 33.0), (12.9, 48.2), (7.4, 48.2)], 3.4, HATCH, bevel=0.6)
    poly([(7.8, 33.4), (12.6, 33.4), (12.6, 39.4), (10.4, 39.4), (7.8, 35.6)], 4.6, BRASS, bevel=0.6,
         top_mat=HATCH, base=3.0)
    poly([(7.8, 46.2), (10.4, 41.4), (12.6, 41.4), (12.6, 47.8), (7.8, 47.8)], 4.6, BRASS, bevel=0.6,
         top_mat=HATCH, base=3.0)
    bar((7.6, 35.0), (10.4, 40.4), 0.9, 4.2, PGOLD)
    bar((10.4, 40.4), (7.6, 45.8), 0.9, 4.2, PGOLD)
    bar((10.4, 40.4), (12.8, 40.4), 0.9, 4.0, GOLD)
    tube([(6.8, 34.0), (6.8, 46.8)], 0.75, 2.2, METAL, sides=10)

    bm.normal_update()
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[recalc_from:])

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
