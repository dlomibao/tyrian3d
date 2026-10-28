"""Spinning arch (newsh2.shp frames 191-205): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. A horseshoe-shaped band, bronze over the top and
grey down the two legs, with a bronze barrel pod hung in the middle on two short struts. The band
is a round tube three pixels across seen face on (black edges round a lit centre) and a little
deeper (frame 199 shows it edge on, wider), and the eight
frames turn the whole thing about the screen's vertical axis. So the model is built once and
exported eight times, each turned about Y to the angle its frame shows (read off how far apart the
two legs are drawn: 12, 9, 6, 4, 0 pixels, then back out on the other side): newsh2-191 (frame
191), newsh2-191-f2 (193) ... newsh2-191-f8 (205). It spins about column 11.

Run: blender --background --python assets/blender/enemies/newsh2-191.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-191"
AXIS = 11  # the column the arch spins about
# Leg spacing per frame (px): the angle each frame is turned by is acos(spacing / 12).
SPACING = [12, 9, 6, 4, 0, -4, -6, -9]


def X(c):
    """Sprite column (pixel centre) to X relative to the spin axis."""
    return (c - AXIS) / 12


TUBE_R = 1.5 / 12  # the band is a round tube three pixels across seen face on (its black edges and lit centre)
TUBE_FLAT = 1.3  # ... and a little deeper than wide (3.9 px), as the edge-on frames (199) draw it wider
POD_RX = 3.3 / 12  # the pod is about six and a half pixels across (seven with its black edge)
POD_RZ = 2.6 / 12  # and a little less deep, so it stays inside the band in the edge-on frames


def sprite_index(pixels, c, r, cols, rows):
    """The palette index of the sprite pixel nearest (c, r) among columns/rows `cols`/`rows` that
    isn't the black outline (1) or transparent."""
    best, best_d = None, 1e9
    for rr in rows:
        for cc in cols:
            v = pixels[rr][cc]
            if v in (-1, 1):
                continue
            d = (cc - c) ** 2 + (rr - r) ** 2
            if d < best_d:
                best, best_d = v, d
    return best


def build_one(sprite, name, angle):
    coll = common.reset_collection(name)
    pixels = [[int(v) for v in (line.split() if isinstance(line, str) else line)] for line in sprite["frames"][0]["pixels"]]
    mats, slot = [], {}

    def mat(i):
        """Material slot of palette index i (bronze and greys alike are polished metal; the dark
        collars and the top seam a little less polished). The sprite's highlights and dark sides are
        its drawn light: the game's lights make them on these metal surfaces."""
        if i not in slot:
            dark = i in (4, 5, 21)
            slot[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, metallic=0.7 if dark else 0.8,
                                                roughness=0.4 if dark else 0.3))
        return slot[i]

    def col_of(x):
        return AXIS + x * 12

    def row_of(y):
        return 13.5 - y * 12

    bm = bmesh.new()

    # The band: one round tube along the centreline through the pixel centres, from the bottom of
    # the left leg (row 19, its rounded end) up, over the top (row 2) and down the right leg. Each
    # stretch takes the colour of the sprite pixels under it, so the arch keeps its alternating
    # bronze segments, the lit left corners, the dark right corners and the dark collar rows.
    half = [(5, 19.45), (5, 19.0), (5, 18.55), (5, 12.0), (5, 7.0), (5.15, 5.4), (6.0, 4.0), (7.0, 3.0),
            (8.2, 2.15), (9.6, 2.0)]
    half = [(X(c), lib.row(r)) for c, r in half]
    path = half + [(0.0, lib.row(2.0))] + [(-x, y) for x, y in reversed(half)]
    radii = [0.45 / 12, 0.85 / 12] + [TUBE_R] * (len(path) - 4) + [0.85 / 12, 0.45 / 12]
    # One point per pixel or so, then a material per stretch from the sprite.
    pts, rads = [], []
    for (p0, r0), (p1, r1) in zip(zip(path, radii), zip(path[1:], radii[1:])):
        n = max(1, math.ceil(math.dist(p0, p1) * 12 / 1.0))
        for k in range(n):
            t = k / n
            pts.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t))
            rads.append(r0 + (r1 - r0) * t)
    pts.append(path[-1])
    rads.append(radii[-1])
    band_pal = []
    for a, b in zip(pts, pts[1:]):
        c, r = col_of((a[0] + b[0]) / 2), row_of((a[1] + b[1]) / 2)
        band_pal.append(sprite_index(pixels, c, min(r, 18.0), range(round(c) - 1, round(c) + 2),
                                     range(max(0, round(r) - 1), min(19, round(r) + 2))))
    # On the legs, the stretches under the collars take their neighbour's colour, and the lighter
    # greys of the leg's middle (10-12) are one: the tube's own lighting gives the highlight. The
    # bronze is one mid-tone (25) all round: the sprite's lit left corners and dark right corners
    # are its drawn light, not paint. Only the dark seam at the top centre (21) is kept.
    for k in range(len(band_pal)):
        i = band_pal[k]
        mx, my = (pts[k][0] + pts[k + 1][0]) / 2, (pts[k][1] + pts[k + 1][1]) / 2
        r = row_of(my)
        if i >= 16:
            band_pal[k] = 21 if abs(col_of(mx) - AXIS) < 0.6 and r < 2.6 else 25
            continue
        if r > 6.5:
            if min(abs(r - 7), abs(r - 12)) < 0.6 and k > 0:
                i = band_pal[k - 1] if r > 9.5 else 10
            band_pal[k] = 10 if i in (11, 12) else i
    # Drop points inside straight runs of one colour (the legs).
    keep = [0, 1]
    for i in range(2, len(pts) - 2):
        a, b, c = pts[keep[-1]], pts[i], pts[i + 1]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if band_pal[i - 1] == band_pal[i] and abs(cross) < 1e-6 and rads[i] == rads[keep[-1]] == rads[i + 1]:
            continue
        keep.append(i)
    keep += [len(pts) - 2, len(pts) - 1]
    # Each stretch is one colour all round: the sprite's dark band edges are its outline and
    # shading, which the game draws itself.
    band_mats = [[mat(band_pal[k0])] * 8 for k0 in keep[:-1]]
    lib.polyline_tube(bm, [(pts[i][0], pts[i][1], 0.0) for i in keep], [rads[i] for i in keep], sides=8,
                      mat_index=band_mats, flat=TUBE_FLAT)

    # Raised dark collars round both legs at rows 7 and 12.
    for c in (5, 17):
        for r in (7, 12):
            y0 = lib.row(r)
            rings = [lib.ellipse_ring(X(c), 0, 0, TUBE_R * 1.12, TUBE_R * TUBE_FLAT * 1.12, n=8, phase=0.5)
                     for _ in range(2)]
            rings = [[(x, y0 + dy, z) for x, z, _ in ring] for ring, dy in zip(rings, (-0.55 / 12, 0.55 / 12))]
            lib.ring_loft(bm, rings, mat(4), cap_start=False, cap_end=False)

    # Round struts about two pixels thick from the legs to the pod (row 10).
    for s in (-1, 1):
        lib.tube(bm, (s * 4.8 / 12, lib.row(10), 0), (s * 2.6 / 12, lib.row(10), 0), 1.1 / 12, sides=8,
                 mat_index=mat(6), caps=False)

    # The pod: a round barrel about six pixels across, rows 6-14, rounded at the bottom, polished
    # bronze in the band's mid-tone (25). The sprite's pale stripe left of centre, dark column right of it,
    # dark lower end and black edge are a lit metal cylinder drawn by hand: the game's lights and
    # outline make them.
    sections = [(5.6, 2.4), (6.2, 2.95), (6.9, 3.3), (12.0, 3.3), (12.8, 2.85), (13.6, 2.2), (14.3, 1.4),
                (14.75, 0.6)]
    rings = []
    for sr, rx in sections:
        ring = lib.ellipse_ring(0, 0, 0, rx / 12, rx / 12 * POD_RZ / POD_RX, n=12, phase=0.0)
        rings.append([(x, lib.row(sr), z) for x, z, _ in ring])
    rings = [[(0.0, lib.row(5.5), 0.0)]] + rings + [[(0.0, lib.row(14.9), 0.0)]]
    lib.ring_loft(bm, rings, mat(25), smooth=True)

    # Turn it about the spin axis and put the axis on column 11.
    bmesh.ops.transform(bm, matrix=Matrix.Translation((lib.px(AXIS), 0, 0)) @ lib.rot_y(angle), verts=bm.verts)
    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build_one(sprite, name, math.acos(SPACING[k] / 12))
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
