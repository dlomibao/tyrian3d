"""Fireball (newsh3.shp frames 267, 269): a 3D version of its sprite.

Seen in episode 4 (levels 6, 22 and 31). A teardrop of fire, tip up the screen and a round hot
belly below: one smooth ball, about 9-10 px tall over the belly and tapering to the tip, its
surface painted pixel by pixel in the sprite's own palette shades (dark red rim, orange and yellow
tongues, a white-hot heart). The two frames only flicker the flame: each gets its own ball from
its own pixels, shown on that frame (common.frame_part). Everything glows.

Run: blender --background --python assets/blender/enemies/newsh3-267.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, ex, ey  # noqa: E402

NAME = "newsh3-267"


def smooth(values, n=1):
    out = list(values)
    for _ in range(n):
        out = [out[0]] + [(out[i - 1] + 2 * out[i] + out[i + 1]) / 4 for i in range(1, len(out) - 1)] + [out[-1]]
    return out


# Palette index of each sprite pixel -> the material it gets: pairs of the dark reds share one,
# the bright yellows and white keep their own so the hot core reads as it does in the sprite.
MAT_OF = {112: 113, 113: 113, 114: 115, 115: 115, 116: 117, 117: 117, 118: 119, 119: 119,
          120: 121, 121: 121, 122: 123, 123: 123, 124: 124, 125: 125, 126: 126, 127: 127}
MAT_INDICES = sorted(set(MAT_OF.values()))

PX = 1 / 12
H_MAX = 9.6     # px, the ball's height over its belly
ROUND = 1.2     # height per px of half width: the cross-section is a little taller than a half circle
RIM = 1.0       # px, the outline's height (a short wall round the edge, the ball's steep side)
TIP_MIN = 3.2   # px, the tip still stands this tall
SMOOTH_PASSES = 2
OUTLINE_PASSES = 3
EDGE_OFFSET = 0.5  # px: the ball's round side starts this far outside the pixel outline
BLUR = [(0.55, 0.55), (-0.55, 0.55), (0.55, -0.55), (-0.55, -0.55), (0.7, 0.0), (-0.7, 0.0), (0.0, 0.7), (0.0, -0.7)]


def height_field(frames):
    """f(col, row) -> height in px of a smooth round ball over the sprite's pixels: a round
    cross-section whose height at a point follows its distance d from the pixel outline,
    h = H * sqrt(1 - (1 - d / R)^2), with R the (smoothed) half width of the body at that row and
    H = ROUND * R capped at H_MAX, so the belly stands about 9-10 px and the tip tapers. The
    outline itself sits at RIM (a short wall). One field serves every frame (over the union of
    their pixels), so the frames' surfaces agree where they overlap."""
    h, w = len(frames[0]), len(frames[0][0])
    on = lambda c, r: 0 <= r < h and 0 <= c < w and any(p[r][c] >= 0 for p in frames)  # noqa: E731
    rows = [r for r in range(h) if any(on(c, r) for c in range(w))]
    hws = smooth([(max(c for c in range(w) if on(c, r)) + 1 - min(c for c in range(w) if on(c, r))) / 2
                  for r in rows], 1)
    segs = []
    for r in range(h):
        for c in range(w):
            if not on(c, r):
                continue
            if not on(c, r - 1):
                segs.append((c, r, c + 1, r))
            if not on(c, r + 1):
                segs.append((c, r + 1, c + 1, r + 1))
            if not on(c - 1, r):
                segs.append((c, r, c, r + 1))
            if not on(c + 1, r):
                segs.append((c + 1, r, c + 1, r + 1))

    def dist(x, y):
        best = 1e9
        for x0, y0, x1, y1 in segs:
            px_ = min(max(x, min(x0, x1)), max(x0, x1))
            py_ = min(max(y, min(y0, y1)), max(y0, y1))
            best = min(best, (x - px_) ** 2 + (y - py_) ** 2)
        return math.sqrt(best)

    def half_width(y):
        t = y - (rows[0] + 0.5)
        i = max(0, min(len(rows) - 2, int(math.floor(t))))
        f = max(0.0, min(1.0, t - i))
        return hws[i] * (1 - f) + hws[i + 1] * f

    def signed(x, y):
        d = dist(x, y)
        return d if on(int(math.floor(x)), int(math.floor(y))) else -d

    def f(c, y):
        # signed distance blurred over about a pixel, so the outline's stair steps round off: the
        # outer corners of a step stay at the rim and the inner ones rise with the ball's side
        d = max(0.0, sum(signed(c + dx, y + dy) for dx, dy in BLUR) / len(BLUR) + EDGE_OFFSET)
        rad = max(1.0, half_width(y))
        top = max(min(H_MAX, ROUND * rad), TIP_MIN)
        k = min(1.0, d / rad)
        return RIM + (top - RIM) * math.sqrt(1.0 - (1.0 - k) ** 2)

    def rim(y):
        """The height where the round side meets the wall (at d = EDGE_OFFSET)."""
        rad = max(1.0, half_width(y))
        top = max(min(H_MAX, ROUND * rad), TIP_MIN)
        k = min(1.0, EDGE_OFFSET / rad)
        return RIM + (top - RIM) * math.sqrt(1.0 - (1.0 - k) ** 2)
    f.rim = rim
    return f


def fireball(bm, pixels, slot, f, drop=0.0):
    """One smooth closed ball over the sprite's pixels: a top surface with a vertex at every pixel
    corner and centre (four triangles a pixel, each pixel in its own palette colour), a short wall
    round the pixel outline and a flat base at z = 0. f is height_field(...); `drop` (px) lowers
    the surface off the outline."""
    h, w = len(pixels), len(pixels[0])
    on = lambda c, r: 0 <= r < h and 0 <= c < w and pixels[r][c] >= 0  # noqa: E731
    corner, base = {}, {}

    def edge(c, r):
        return not all(on(c - dc, r - dr) for dc in (0, 1) for dr in (0, 1))

    def cv(c, r):
        if (c, r) not in corner:
            z = f(c, r) if edge(c, r) else f(c, r) - drop
            corner[(c, r)] = bm.verts.new((ex(c, w), ey(r, h), z * PX))
        return corner[(c, r)]

    def bv(c, r):
        if (c, r) not in base:
            base[(c, r)] = bm.verts.new((ex(c, w), ey(r, h), 0.0))
        return base[(c, r)]
    top_faces, flat_faces, inner, links = [], [], [], {}
    for r in range(h):
        for c in range(w):
            if not on(c, r):
                continue
            m = slot[MAT_OF[pixels[r][c]]]
            mid = bm.verts.new((ex(c + 0.5, w), ey(r + 0.5, h), (f(c + 0.5, r + 0.5) - drop) * PX))
            inner.append(mid)
            a, b, d, e = cv(c, r), cv(c + 1, r), cv(c + 1, r + 1), cv(c, r + 1)
            for p, q in ((a, e), (e, d), (d, b), (b, a)):
                face = bm.faces.new((p, q, mid))
                face.material_index = m
                top_faces.append(face)
            face = bm.faces.new((bv(c, r), bv(c + 1, r), bv(c + 1, r + 1), bv(c, r + 1)))
            face.material_index = slot[113]
            flat_faces.append(face)
            # walls on the outline edges
            for (c0, r0), (c1, r1), (nc, nr) in (((c, r), (c + 1, r), (c, r - 1)),
                                                 ((c + 1, r), (c + 1, r + 1), (c + 1, r)),
                                                 ((c + 1, r + 1), (c, r + 1), (c, r + 1)),
                                                 ((c, r + 1), (c, r), (c - 1, r))):
                if on(nc, nr):
                    continue
                face = bm.faces.new((cv(c0, r0), cv(c1, r1), bv(c1, r1), bv(c0, r0)))
                face.material_index = m
                flat_faces.append(face)
                links.setdefault((c0, r0), set()).add((c1, r1))
                links.setdefault((c1, r1), set()).add((c0, r0))
    # Round the outline's stair steps off: smooth the outline corners along the outline (top and
    # base together), so the wall's top runs level instead of rising and falling at every step.
    pos = {k: (float(k[0]), float(k[1])) for k in links}
    for _ in range(OUTLINE_PASSES):
        pos = {k: (0.5 * pos[k][0] + 0.5 * sum(pos[n][0] for n in links[k]) / len(links[k]),
                   0.5 * pos[k][1] + 0.5 * sum(pos[n][1] for n in links[k]) / len(links[k]))
               for k in links}
    for k, (x, y) in pos.items():
        for v in (corner[k], base[k]):
            v.co.x, v.co.y = ex(x, w), ey(y, h)
        corner[k].co.z = f.rim(y) * PX
    # Soften the top: a few smoothing passes over the vertices off the outline (the distance field
    # has creases along the body's middle and at the outline's steps).
    walls = set(flat_faces)
    rim = {v for v in corner.values() if any(f_ in walls for f_ in v.link_faces)}
    free = [v for v in list(corner.values()) + inner if v not in rim]
    for _ in range(SMOOTH_PASSES):
        new = {}
        for v in free:
            nb = [e.other_vert(v) for e in v.link_edges if e.other_vert(v).co.z > 0]
            new[v] = 0.5 * v.co.z + 0.5 * sum(n.co.z for n in nb) / len(nb)
        for v, z in new.items():
            v.co.z = z
    for face in top_faces:
        face.smooth = True
    for face in flat_faces:
        face.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, slot = [], {}
    for i in MAT_INDICES:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, NAME, roughness=0.5,
                                            emission_strength=1.5 + 0.25 * (i - 112)))
    field = height_field([fr["pixels"] for fr in sprite["frames"]])
    parts = []
    for k, frame in enumerate(sprite["frames"]):
        bm = bmesh.new()
        # The flickered frame stands a hair lower so where both are drawn at once (previews, the
        # review sheet) the first frame's surface is the one seen; in game only one shows.
        fireball(bm, frame["pixels"], slot, field, drop=0.0 if k == 0 else 0.25)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        obj = lib.mesh_object_mixed(f"{NAME}-{frame['index']}", bm, mats, coll)
        parts.append(common.frame_part(obj, [frame["index"]]))
    return [(NAME, parts, sprite["sprites"])]

if __name__ == "__main__":
    lib.run(NAME, build, __file__)
