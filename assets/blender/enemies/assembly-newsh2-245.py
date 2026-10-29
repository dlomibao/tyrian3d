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


def lib_inset(pts, d):
    """lib.inset for an outline in pixel coordinates."""
    return lib.inset(pts, d)


def sector(cx, cy, r0, r1, a0, a1, n=4, sq=1.0):
    """Outline of an annulus sector (radii in px, angles in degrees, y squashed by `sq`)."""
    outer = [(cx + r1 * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
              cy + sq * r1 * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
    inner = [(cx + r0 * math.cos(math.radians(a1 - (a1 - a0) * k / n)),
              cy + sq * r0 * math.sin(math.radians(a1 - (a1 - a0) * k / n))) for k in range(n + 1)]
    return outer + inner


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nsh2a245"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(88, metallic=0.25, roughness=0.55),  # 0 purple plating, octagon plates
        pal(89, metallic=0.25, roughness=0.5),  # 1 lighter purple panels, collar body
        pal(90, metallic=0.3, roughness=0.45),  # 2 pale purple beam panels, collar ring
        pal(85, metallic=0.2, roughness=0.7),  # 3 dark purple seams, recess floors
        pal(93, metallic=0.5, roughness=0.35),  # 4 pale grille bars
        pal(53, metallic=0.1, roughness=0.05),  # 5 dark blue glass eye
        pal(103, metallic=0.45, roughness=0.35),  # 6 blue-grey steel: eye ring, clamps, capsule caps
        pal(57, metallic=0.0, roughness=0.15, emission_strength=1.6),  # 7 glowing blue capsules
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

    def poly(pts, z0, z1, bevel, mat, bevel_h=None, flip=False):
        """A chamfered plate over an outline in pixel coordinates (flip mirrors it about col 36)."""
        pts = [((W - c) if flip else c, r) for c, r in pts]
        lib.bevel_prism(bm, [(XE(c), YE(r)) for c, r in pts], z0, z1, bevel * PX, mat=mat,
                        bevel_h=None if bevel_h is None else bevel_h * PX)

    # Base block under the plating (purple columns 12-60, the full height); dark, so the gaps
    # between the plates on it read as seams.
    rect(bm, 12, -0.5, 60, 28.5, -0.16, 0.0, SEAM)
    rect(bm, 12.6, -0.5, 59.4, 28.5, -0.15, 0.005, PLATE)

    # Traced from the concept (assets/blender/textures/<name>/concept.png, warped onto the sprite's
    # parts): every plate below is a chamfered armour panel; the left half is mirrored about col 36.
    for f in (False, True):
        # Octagonal armour plate (cols 3-21, rows 4-20): a thick backing plate and a raised face
        # inset about 1.3 px, both with crisp chamfers.
        octagon = [(8, 4), (16, 4), (21, 9), (21, 15), (16, 20), (8, 20), (3, 15), (3, 9)]
        poly(octagon, -0.1, 0.22, 0.5, PLATE, flip=f)
        poly(lib_inset(octagon, 1.3), 0.15, 0.36, 1.0, PLATE, bevel_h=0.8, flip=f)
        # Top band: a panel over cols 12.5-19.6, then the shoulder (cols 19.8-29) with a dark vent
        # slot in it (the concept's grey vent under the arc).
        poly([(12.8, -0.5), (19.4, -0.5), (19.4, 3.8), (13.4, 3.8), (12.8, 3.2)], -0.02, 0.09, 0.5, PANEL, flip=f)
        poly([(19.8, -0.5), (29.2, -0.5), (29.2, 0.9), (19.8, 0.9)], -0.02, 0.15, 0.35, PLATE, flip=f)
        poly([(19.8, 3.0), (29.2, 3.0), (29.2, 4.2), (19.8, 4.2)], -0.02, 0.15, 0.35, PLATE, flip=f)
        poly([(19.8, 0.9), (21.2, 0.9), (21.2, 3.0), (19.8, 3.0)], -0.02, 0.15, 0.2, PLATE, flip=f)
        poly([(21.2, 0.9), (29.2, 0.9), (29.2, 3.0), (21.2, 3.0)], -0.02, 0.04, 0.1, SEAM, flip=f)
        for r in (1.45, 2.2):
            poly([(21.4, r), (28.8, r), (28.8, r + 0.35), (21.4, r + 0.35)], 0.0, 0.1, 0.08, RIM, flip=f)
        # Beam column between the plate and the eye (cols 21-28.6): an upper panel (pale) and a lower
        # one, split by a seam at row 11.9.
        poly([(21.2, 4.6), (27.8, 4.6), (28.8, 5.6), (28.8, 11.6), (21.2, 11.6)], -0.02, 0.16, 0.6, BEAM, flip=f)
        poly([(21.2, 12.2), (28.8, 12.2), (28.8, 21.4), (23.0, 21.4), (21.2, 19.6)], -0.02, 0.16, 0.6, PANEL, flip=f)
        # Bottom band: a block under the plate (cols 12.2-19.6, chamfered top-right) and one under
        # the beam (cols 20.4-28.6, chamfered top corners).
        poly([(12.4, 20.5), (18.2, 20.5), (19.6, 21.9), (19.6, 28.5), (12.6, 28.5), (12.4, 28.0)], -0.02, 0.12, 0.6, PANEL, flip=f)
        poly([(20.4, 23.6), (21.6, 22.2), (27.4, 22.2), (28.8, 23.6), (28.8, 28.5), (20.4, 28.5)], -0.02, 0.12, 0.6, PLATE, flip=f)

    # Top centre panel above the collar (cols 29-43) and bottom centre one under the chin.
    poly([(29.4, -0.5), (42.6, -0.5), (42.6, 3.6), (29.4, 3.6)], -0.02, 0.1, 0.5, BEAM)
    poly([(29.2, 25.8), (42.8, 25.8), (42.8, 28.5), (29.2, 28.5)], -0.02, 0.1, 0.5, BEAM)

    # The round body the eye sits in (centre col 36, row 11.5), and a ring of eight segmented
    # armour plates round the eye on it.
    cx, cy = 36.0, 11.5
    body = [(cx + 9.3 * math.cos(2 * math.pi * k / 28), cy + 9.1 * math.sin(2 * math.pi * k / 28)) for k in range(28)]
    poly(body, -0.02, 0.2, 0.9, PANEL, bevel_h=0.8)
    for k in range(8):
        a0 = 22.5 + 45 * k + 2.2
        a1 = 22.5 + 45 * (k + 1) - 2.2
        poly(sector(cx, cy, 6.6, 8.7, a0, a1, n=3), 0.1, 0.31, 0.45, BEAM, bevel_h=0.4)
    # Chin plate holding the grille (cols 29.4-42.6, rows 17.6-26).
    chin = [(31.2, 17.6), (40.8, 17.6), (42.6, 19.4), (42.6, 25.0), (41.6, 26.0), (30.4, 26.0), (29.4, 25.0), (29.4, 19.4)]
    poly(chin, -0.02, 0.24, 0.6, PANEL, bevel_h=0.5)
    # Grille: a pale frame round a dark recess (cols 32.8-39.2, rows 20.6-24.6) with thin bars.
    gx0, gx1, gy0, gy1 = 32.6, 39.4, 20.5, 24.7
    for pts in (
        [(31.8, 19.6), (40.2, 19.6), (40.2, gy0), (31.8, gy0)],
        [(31.8, gy1), (40.2, gy1), (40.2, 25.5), (31.8, 25.5)],
        [(31.8, gy0), (gx0, gy0), (gx0, gy1), (31.8, gy1)],
        [(gx1, gy0), (40.2, gy0), (40.2, gy1), (gx1, gy1)],
    ):
        poly(pts, 0.2, 0.3, 0.2, PANEL)
    poly([(gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)], 0.2, 0.21, 0.0, SEAM)
    nb = 9
    for i in range(nb):
        c = gx0 + (gx1 - gx0) * (i + 0.5) / nb
        rect(bm, c - 0.17, gy0, c + 0.17, gy1, 0.2, 0.27, BAR)

    # The steel ring the eye is set in, with a clamp on top, and the dark glass ball.
    for a in (0, 180):
        poly(sector(cx, cy, 5.5, 6.7, a, a + 180, n=12), 0.2, 0.36, 0.25, RIM, bevel_h=0.25)
    poly([(34.6, 4.0), (37.4, 4.0), (37.4, 5.3), (34.6, 5.3)], 0.2, 0.4, 0.3, RIM)
    lib.dome(bm, (XE(cx), YE(cy), 0.27), (5.8 * PX, 5.7 * PX, 0.44), mat=GLASS, segments=24, rings=7)

    # Two capsule lights slanting outwards below the eye: a dark socket, a steel cap at the outer
    # top end and a glowing blue pill.
    for f in (False, True):
        (c0, r0), (c1, r1) = (26.0, 16.4), (30.8, 21.6)
        if f:
            c0, c1 = W - c0, W - c1
        x0, y0, x1, y1 = XE(c0), YE(r0), XE(c1), YE(r1)
        d = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / d, (y1 - y0) / d
        ext = 0.7 * PX
        lib.sweep(bm, [(x0 - ux * ext, y0 - uy * ext, 0.02, 2.1 * PX, 0.05),
                       (x1 + ux * ext, y1 + uy * ext, 0.02, 2.1 * PX, 0.05)], sides=8, mat=SEAM, smooth=False)
        def pill(t0, t1, mat, w):
            n = 5
            path = []
            for k in range(n + 1):
                t = t0 + (t1 - t0) * k / n
                end = min(t, 1 - t)
                s = min(1.0, (end / 0.18)) ** 0.5 if end < 0.18 else 1.0
                path.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0.17, w * PX * s, w * PX * s))
            lib.sweep(bm, path, sides=10, mat=mat)
        pill(0.0, 1.0, CAPSULE, 1.35)
        lib.sweep(bm, [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0.17, 1.55 * PX * s, 1.55 * PX * s)
                       for t, s in ((-0.02, 0.6), (0.06, 1.0), (0.3, 1.0), (0.32, 0.85))], sides=10, mat=RIM)

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
