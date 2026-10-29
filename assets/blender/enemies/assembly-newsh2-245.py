"""Purple eye fortress (newsh2.shp frames 245, 169, 207 side by side): a 3D version of its sprites.

Seen in levels 1.30 and 3.17. Three 2x2 enemies in a row make one 72x28 px block set into grey
rock (sprite.json `assemblyLayout`): a purple plated structure with a dark blue glass eye in a
round collar in the middle (newsh2-169), two blue capsules and a grille under the eye, a raised
octagonal pad on each side (newsh2-245 and newsh2-207), vertical beams between them and a band
of panels along the top and bottom edges, with boulders and sand at both ends.

The whole block is built once in assembly coordinates and cut into the three pieces with
common.split_assembly. It hangs centred on z = 0 like other flying objects; the rocks are lumpy,
flat-shaded boulders whose facets take the sprite's colour under them.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-245.py [-- --preview out.png]
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

NAME = "assembly-newsh2-245"
ROOT = common.repo_root(__file__)
W, H = 72, 28  # the assembly grid in pixels; its centre is the Blender origin
PX = 1 / 12


def XE(e):
    """Grid pixel edge (column) to Blender X."""
    return (e - W / 2) / 12


def YE(e):
    """Grid pixel edge (row) to Blender Y."""
    return (H / 2 - e) / 12


def rect(bm, c0, r0, c1, r1, z0, z1, mat):
    """A box over pixel edges c0..c1, r0..r1."""
    lib.box(bm, XE(c0), YE(r1), XE(c1), YE(r0), z0, z1, mat=mat)


def brect(bm, c0, r0, c1, r1, z0, z1, bevel, mat):
    """A box over pixel edges c0..c1, r0..r1 with its top edge chamfered by `bevel` px."""
    lib.bevel_prism(bm, [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))],
                    z0, z1, bevel * PX, mat=mat)


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nsh2a245"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(88, metallic=0.25, roughness=0.55),  # 0 purple plating
        pal(89, metallic=0.25, roughness=0.5),  # 1 lighter purple panels, collar
        pal(90, metallic=0.3, roughness=0.45),  # 2 pale purple beams
        pal(85, metallic=0.2, roughness=0.7),  # 3 dark purple seams, grille recess
        pal(93, metallic=0.35, roughness=0.4),  # 4 pale grille bars
        pal(52, metallic=0.6, roughness=0.12),  # 5 dark blue glass eye
        pal(102, metallic=0.6, roughness=0.35),  # 6 blue-grey eye rim
        pal(55, metallic=0.5, roughness=0.2),  # 7 blue capsules
        pal(4, metallic=0.05, roughness=0.9),  # 8 dark rock
        pal(7, metallic=0.05, roughness=0.85),  # 9 mid rock
        pal(9, metallic=0.05, roughness=0.8),  # 10 light rock
        pal(10, metallic=0.05, roughness=0.75),  # 11 pale rock
        pal(167, metallic=0.0, roughness=0.9),  # 12 dark sand
        pal(169, metallic=0.0, roughness=0.9),  # 13 sand
        pal(171, metallic=0.0, roughness=0.85),  # 14 pale sand
        pal(91, metallic=0.3, roughness=0.45),  # 15 pale purple rims
    ]
    (PLATE, PANEL, BEAM, SEAM, BAR, GLASS, RIM, CAPSULE, ROCK0, ROCK1, ROCK2, ROCK3,
     SAND0, SAND1, SAND2, PALE) = range(16)
    bm = bmesh.new()

    # Base block under the plating (purple columns 13-60, the full height).
    rect(bm, 13, -0.5, 61, 28.5, -0.16, 0.0, SEAM)
    rect(bm, 13.3, -0.5, 60.7, 28.5, -0.15, 0.01, PLATE)

    # Vertical beams between the pads and the middle (columns 21-26 and 45-50).
    for c in (21, 45):
        brect(bm, c, -0.5, c + 6, 28.5, -0.02, 0.13, 0.7, BEAM)
    # Panels in the bands along the top and bottom edges (they repeat every 24 px).
    for c0, c1, mat in ((13, 19, PANEL), (29, 36, BEAM), (37, 43, PANEL), (53, 60, BEAM)):
        brect(bm, c0 + 0.2, -0.5, c1 - 0.2, 3.8, -0.02, 0.09, 0.6, mat)
        brect(bm, c0 + 0.2, 23.2 if c0 not in (13, 53) else 20.2, c1 - 0.2, 28.5, -0.02, 0.09, 0.6, mat)

    # Octagonal pads on both sides (columns 3-20 and 51-68, rows 4-19), raised and chamfered.
    octagon = [(8, 4), (16, 4), (21, 9), (21, 15), (16, 20), (8, 20), (3, 15), (3, 9)]
    for flip in (False, True):
        pts = [((72 - c) if flip else c, r) for c, r in octagon]
        lib.bevel_prism(bm, [(XE(c), YE(r)) for c, r in pts], -0.1, 0.32, 1.3 * PX, mat=PLATE,
                        bevel_h=1.0 * PX)

    # Round collar round the eye (centre column 36, row 10.5) and the eye's blue-grey rim.
    ex, ey = XE(36.5), YE(11.0)
    def ellipse(rx, ry, n=20):
        return [(ex + rx * PX * math.cos(2 * math.pi * k / n), ey + ry * PX * math.sin(2 * math.pi * k / n))
                for k in range(n)]
    lib.bevel_prism(bm, ellipse(9.8, 9.6, 24), -0.02, 0.24, 1.6 * PX, mat=PANEL, bevel_h=1.3 * PX)
    lib.bevel_prism(bm, ellipse(7.6, 6.6, 24), 0.24, 0.29, 0.6 * PX, mat=RIM)
    # The dark glass eye (columns 30-42, rows 6-16), a big glossy ball standing in the collar.
    lib.dome(bm, (ex, ey, 0.26), (6.9 * PX, 5.9 * PX, 0.48), mat=GLASS, segments=24, rings=8)

    # Two blue capsules below the eye, slanting outwards.
    for (c0, r0), (c1, r1) in (((25.2, 16.4), (31.0, 22.4)), ((47.2, 17.0), (41.6, 22.6))):
        x0, y0, x1, y1 = XE(c0), YE(r0), XE(c1), YE(r1)
        n = 6
        path = []
        for k in range(n + 1):
            t = k / n
            s = math.sin(math.pi * t) ** 0.35
            path.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0.13, 1.65 * PX * s, 1.6 * PX * s))
        lib.sweep(bm, path, sides=10, mat=CAPSULE)
        # A dark socket under each capsule.
        lib.sweep(bm, [(x0, y0, 0.02, 2.4 * PX, 0.05), (x1, y1, 0.02, 2.4 * PX, 0.05)], sides=8, mat=SEAM)

    # Grille under the eye: a dark recess with four pale bars (columns 33-39, rows 20-23) and a
    # pale bar across its top (row 18).
    # The grille sits in a raised frame, so the recess is cut in below the frame's top.
    for c0, r0, c1, r1 in ((31.6, 18.9, 32.4, 24.9), (40.6, 18.9, 41.4, 24.9), (31.6, 24.1, 41.4, 24.9)):
        brect(bm, c0, r0, c1, r1, -0.02, 0.16, 0.25, PANEL)
    rect(bm, 32.3, 19.3, 40.7, 24.2, -0.02, 0.03, SEAM)
    for c in (33, 35, 37, 39):
        rect(bm, c + 0.1, 19.6, c + 0.9, 23.8, 0.0, 0.11, BAR)
    brect(bm, 31.6, 17.4, 41.4, 19.1, -0.02, 0.19, 0.4, PALE)

    # ---- rocks at both ends, painted from the sprite ----
    rng = random.Random(245)
    first_face = len(bm.faces)
    boulders = [  # (column, row, rx px, ry px, z, rz)
        (5.0, 1.0, 6.5, 4.2, -0.06, 0.13), (6.0, 27.6, 5.5, 3.0, -0.06, 0.11),
        (1.5, 10.5, 3.2, 6.8, -0.08, 0.12), (5.3, 20.2, 6.6, 5.0, -0.05, 0.16),
        (0.8, 25.5, 2.4, 2.8, -0.08, 0.09), (10.3, 23.5, 3.0, 3.0, -0.07, 0.1),
        (66.0, 1.5, 6.4, 4.4, -0.06, 0.14), (70.0, 7.6, 2.8, 3.6, -0.07, 0.11),
        (70.6, 13.0, 2.2, 3.0, -0.08, 0.1), (68.2, 21.6, 5.2, 5.4, -0.05, 0.16),
        (62.6, 18.0, 2.0, 3.6, -0.09, 0.08), (64.2, 26.8, 3.4, 2.4, -0.08, 0.09),
    ]
    # A bed of rubble under the boulders so the ends are filled like the sprite's.
    for c0, c1 in ((-0.5, 13.5), (60.5, 72.5)):
        first_bed = len(bm.faces)
        bed = bmesh.ops.create_grid(bm, x_segments=6, y_segments=10, size=0.5)
        for v in bed["verts"]:
            u, w = v.co.x + 0.5, v.co.y + 0.5
            v.co = (XE(c0 + (c1 - c0) * u), YE(-0.5 + 29 * w), -0.04 + rng.uniform(-0.02, 0.03))
        bm.faces.ensure_lookup_table()
        for f in bm.faces[first_bed:]:
            f.material_index = ROCK0
            f.smooth = False
    for c, r, rx, ry, z, rz in boulders:
        seeds = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.08, 0.16))
                 for _ in range(4)]
        def bump(d, seeds=seeds):
            return 1.0 + sum(a * max(0.0, d.x * u + d.y * v + d.z * w) for u, v, w, a in seeds)
        lib.ellipsoid(bm, (XE(c + 0.5), YE(r + 0.5), z), (rx * PX, ry * PX, 2.0 * rz), mat=ROCK1,
                      segments=10, rings=6, smooth=False, bump=bump)

    def sample(x, y):
        c, r = math.floor(x * 12 + W / 2), math.floor(H / 2 - y * 12)
        if 0 <= r < H and 0 <= c < W:
            return grid[r][c]
        return None

    def slot(i):
        if 2 <= i <= 15:
            return ROCK0 if i <= 4 else ROCK1 if i <= 7 else ROCK2 if i <= 9 else ROCK3
        if 160 <= i <= 167:
            return SAND0
        if 168 <= i <= 169:
            return SAND1
        if 170 <= i <= 173:
            return SAND2
        return None
    lib.paint(bm, first_face, sample, slot, up_only=True)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-245")
    sprite = common.load_sprite(ROOT, "newsh2-245")
    sprite["colors"] = colors
    obj = build(sprite, grid)
    cx0, cy0 = x0 + W // 2, y0 + H // 2
    pieces = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in layout]
    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_assembly(ROOT, obj, pieces, out, grid, colors, size=W / 12)


if __name__ == "__main__":
    main()
