"""Flying ear, lobe at the bottom right (newsh5.shp frame 284): a 3D version of its sprite.

Seen in episode 4 (level 20), beside its mirror image newsh5-245. A tan ear: a rolled rim (helix)
all round, standing about 4 px over the hollow inside it; the deep dark concha down the right
side and the fossa under the top rim; the Y-shaped antihelix ridge between them; the tragus bump
on the right rim and a fleshy, domed lobe at the bottom. One frame.

The ear is one closed surface: a height field over the sprite's own outline (outline pixels
included), triangulated with a constrained Delaunay fill, over a flat back on the ground; the
rim's outer side rises from the ground and rounds over to a 7 px crest about 3 px in, the lobe is
a soft dome about 4 px tall that takes over from the rim at the bottom, and the concha and fossa
are smooth merged bowls well below the crest. The antihelix is a pair of round tubes on it whose
ends taper to a point and sink into the surface. The ear is skin: one mid-tone tan (the sprite's average, index 24) on a matte, non-metallic
material, outer side and hollows alike, but for a step darker on the floor of the deepest bowls. The sprite's darker hollows, lit ridges and black outline
are its drawn lighting; in the game the relief, the scene's light and the outline effect make them.

Run: blender --background --python assets/blender/enemies/newsh5-284.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-284"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Heights in sprite px (1/12 unit). The outline sits on the ground (z = 0) and the back is flat
# there; the rim's outer side rises from it in a convex curve to the crest.
RIM_TOP = 7.0     # top of the rolled rim (helix)
LOBE_TOP = 3.4    # the rim's crest where it runs round the lobe
LOBE_ROWS = (17.5, 23.0)  # sprite rows over which the crest drops from RIM_TOP to LOBE_TOP
EQUATOR = 0.0     # the outline's height: on the ground
RIM_AT = 3.4      # distance in from the outline edge of the rim's crest (px)
FOOT_SLOPE = 0.0  # the outer side's slope where it meets the ground (relative to an even ramp)
RIM_HALF = 2.4    # the inner side's fall from the crest to the floor (px)
FLOOR = 2.0       # floor of the hollow inside the rim
MIN_Z = 0.45      # nothing inside the outline goes lower (the back is at 0)
OUT_PUSH = 0.15   # px the smoothed outline is pushed out
SMOOTH_PASSES = 3 # running-average passes over the traced outline
BACK = 0.0        # the back is flat on the ground
TOP_STEP = 0.5    # triangulation spacing of the top (px)
BACK_STEP = 2.0   # and of the back
# Rings of points (px in from the outline, every n-th outline point) that shape the round edge.
TOP_RINGS = [(0.12, 1), (0.4, 1), (0.75, 1), (1.15, 1), (1.6, 1), (2.15, 1), (2.8, 1), (3.3, 1), (3.8, 1), (4.3, 1), (4.85, 1)]
BACK_RINGS = [(1.0, 3)]

# Skin: the sprite's mid-tone tan (its pixels average index 24) everywhere; the light shades it.
# Only the floor of the deep concha and fossa bowls, where the game's light can't reach in the
# way the sprite's darkest browns say, is a step darker skin (a recess, not shading).
SKIN = 24
RECESS = 22
RECESS_Z = FLOOR - 0.4  # faces whose centre lies below this (px) are the recess floor
METALLIC, ROUGHNESS = 0.0, 0.75


def P(c, r):
    """A sprite pixel centre (column, row) in pixel-corner coordinates (u right, v down)."""
    return (c + 0.5, r + 0.5)


# (centre, rx, ry, tilt, depth) basins below the floor: concha (right), its upper end, fossa
# (top), and the scapha groove inside the left rim.
BASINS = [
    (P(15.9, 13.0), 3.2, 5.8, 0.12, 1.4),
    (P(10.6, 6.3), 3.9, 1.7, 0.22, 1.3),
    (P(6.6, 8.6), 1.1, 2.2, 0.25, 0.7),
]
# Antihelix tubes: control points (column, row, centre height px, radius px). The stem runs from
# inside the lobe (its foot is the antitragus) up past the fork into the upper crus; the lower
# crus branches off at the fork toward the concha.
F = FLOOR
ANTIHELIX = [
    [(15.8, 20.6, 3.3, 1.15), (15.2, 19.1, 3.6, 1.3), (14.0, 18.5, F + 1.0, 1.35), (12.9, 17.0, F + 0.9, 1.3),
     (12.2, 14.8, F + 0.9, 1.3), (11.6, 12.6, F + 0.9, 1.25), (11.0, 11.4, F + 0.9, 1.2), (10.2, 9.6, F + 0.8, 1.1),
     (9.6, 8.0, F + 0.5, 0.95), (8.7, 6.6, F + 0.1, 0.75), (7.9, 5.8, F - 0.4, 0.5), (7.3, 5.2, F - 0.9, 0.3)],
    [(11.0, 11.4, F + 0.8, 1.05), (12.4, 10.2, F + 0.8, 1.0), (13.6, 9.3, F + 0.7, 0.9), (14.6, 8.6, F + 1.2, 0.8),
     (15.3, 8.1, F + 2.0, 0.6)],
]
# (start, end) px over which each tube tapers to a point and sinks into the surface it meets, so
# the ridge fades out instead of stopping as a cut pipe.
TAPER = [(2.2, 2.6), (0.0, 2.2)]
FILLET = (0.6, 2.4)  # height and reach (px) of the swell under the antihelix
LOBE = (P(14.3, 20.8), 4.6, 4.2, 4.3)         # centre, rx, ry, height: the floor rising into it
# The lobe is its own soft dome (centre, rx, ry, height) that takes over from the rim below
# LOBE_BLEND (sprite rows), so it rolls down to the outline instead of sitting inside the rim.
LOBE_DOME = (P(14.6, 21.2), 5.6, 5.0, 4.3)
LOBE_BLEND = (17.8, 21.0)
BASIN_MAX = 2.2   # deepest cut below the floor where basins overlap
TRAGUS = (P(18.2, 15.4), 2.4, 2.9, RIM_TOP - 0.3)


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy), t


def line_dist(p, pts):
    """Distance to a polyline and the position along it (0..1)."""
    best, at, total = 1e9, 0.0, len(pts) - 1
    for i in range(total):
        d, t = seg_dist(p, pts[i], pts[i + 1])
        if d < best:
            best, at = d, (i + t) / total
    return best, at


def ellipse_u(p, c, rx, ry, tilt=0.0):
    dx, dy = p[0] - c[0], p[1] - c[1]
    ct, st = math.cos(tilt), math.sin(tilt)
    ex, ey = dx * ct + dy * st, -dx * st + dy * ct
    return (ex / rx) ** 2 + (ey / ry) ** 2


def smax(a, b, k):
    """A smooth maximum of a and b, rounded over about k."""
    t = min(1.0, max(0.0, 0.5 + 0.5 * (a - b) / k))
    return b + (a - b) * t + k * t * (1 - t) * 0.5


def crest(p):
    """The rim's crest height (px) at p: the helix all round, dropping to the lobe's height over
    the bottom of the ear."""
    t = min(1.0, max(0.0, (p[1] - LOBE_ROWS[0]) / (LOBE_ROWS[1] - LOBE_ROWS[0])))
    return RIM_TOP + (LOBE_TOP - RIM_TOP) * t * t * (3 - 2 * t)


def outer(p, d, top):
    """The rim's outer side: from the ground at the outline up to `top` at RIM_AT, rounding over
    to level at the crest. Its foot meets the ground at a low slope (a Hermite curve), so the dark
    outline band painted on the outermost pixel stays a thin strip along the ground."""
    t = min(1.0, d / RIM_AT)
    s = FOOT_SLOPE
    g = s * t + (3 - 2 * s) * t * t + (s - 2) * t ** 3
    return EQUATOR + (top - EQUATOR) * g


def top_height(p, d):
    """Height (px) of the ear's front at pixel-corner point p, d px in from the outline edge."""
    top = crest(p)
    # Inside: the floor with smooth bowls cut into it and a swell under the antihelix, added (not
    # min/max'd) so they blend without creases; the lobe and tragus domes blend in smoothly.
    # The basins add up (capped, softly), so where they overlap they merge into one bowl instead
    # of leaving a saddle and separate pits.
    cut = 0.0
    for c, rx, ry, tilt, depth in BASINS:
        u = ellipse_u(p, c, rx, ry, tilt)
        if u < 1:
            cut += depth * 0.5 * (1 + math.cos(math.pi * math.sqrt(u)))
    cut = BASIN_MAX * math.tanh(cut / BASIN_MAX)
    # A low swell under the antihelix tubes, so they grow out of the floor instead of lying on it.
    swell = 0.0
    for ctrl in ANTIHELIX:
        d_ah, _ = line_dist(p, [(c + 0.5, r + 0.5) for c, r, *_ in ctrl])
        if d_ah < FILLET[1]:
            swell = smax(swell, FILLET[0] * 0.5 * (1 + math.cos(math.pi * d_ah / FILLET[1])), 0.4)
    inner = FLOOR + swell - cut
    lobe_u = ellipse_u(p, LOBE[0], LOBE[1], LOBE[2])
    if lobe_u < 1:
        inner = smax(inner, FLOOR + (LOBE[3] - FLOOR) * math.sqrt(1 - lobe_u), 0.8)
    tu = ellipse_u(p, TRAGUS[0], TRAGUS[1], TRAGUS[2])
    if tu < 1:
        # a soft bump (no vertical edge where it meets the concha)
        inner = smax(inner, FLOOR + (TRAGUS[3] - FLOOR) * 0.5 * (1 + math.cos(math.pi * math.sqrt(tu))), 0.8)
    if d < RIM_AT:
        h = outer(p, d, top)
    else:  # the rim's inner side falls in a round shoulder to whatever is inside it
        k = min(1.0, (d - RIM_AT) / RIM_HALF)
        w = 0.5 * (1 + math.cos(math.pi * k))
        h = smax(inner + (top - inner) * w, inner, 0.9)
    # Whatever stands near the edge falls away with the rim's outer side.
    h = min(h, outer(p, d, max(top, TRAGUS[3])))
    # The lobe: a soft dome rolling down to the outline, taking over from the rim at the bottom.
    w = min(1.0, max(0.0, (p[1] - LOBE_BLEND[0]) / (LOBE_BLEND[1] - LOBE_BLEND[0])))
    if w > 0:
        w = w * w * (3 - 2 * w)
        lu = min(1.0, ellipse_u(p, LOBE_DOME[0], LOBE_DOME[1], LOBE_DOME[2]))
        dome = min(LOBE_DOME[3] * (1 - lu) ** 0.6, outer(p, d, LOBE_DOME[3] * 1.15))
        h = (1 - w) * h + w * dome
    return max(h, min(MIN_Z, outer(p, d, top)))


def back_height(d):
    return EQUATOR - BACK


def inside(poly, p):
    x, y, res = p[0], p[1], False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[i - 1]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            res = not res
    return res


def poly_dist(poly, p):
    return min(seg_dist(p, poly[i], poly[i - 1])[0] for i in range(len(poly)))


def resample(poly, step):
    """A closed polyline resampled at about `step` spacing along its length."""
    segs = [(Vector(poly[i]), Vector(poly[(i + 1) % len(poly)])) for i in range(len(poly))]
    total = sum((b - a).length for a, b in segs)
    n = max(8, round(total / step))
    out, i, walked = [], 0, 0.0
    for k in range(n):
        target = total * k / n
        while walked + (segs[i][1] - segs[i][0]).length < target:
            walked += (segs[i][1] - segs[i][0]).length
            i += 1
        a, b = segs[i]
        ln = (b - a).length or 1
        out.append(tuple(a.lerp(b, (target - walked) / ln)))
    return out


def smooth_ring(poly, passes, push):
    """Running-average smoothing of a closed polyline, then each point moved `push` px outward."""
    pts = [Vector(p) for p in poly]
    n = len(pts)
    for _ in range(passes):
        pts = [(pts[i - 2] + pts[i - 1] + pts[i] + pts[(i + 1) % n] + pts[(i + 2) % n]) / 5 for i in range(n)]
    ring = [tuple(p) for p in pts]
    out = []
    for i, p in enumerate(pts):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        nrm = Vector((-t.y, t.x))
        if inside(ring, tuple(p + nrm * 0.05)):
            nrm = -nrm
        out.append(tuple(p + nrm * push))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][0]["pixels"]
    mats = [common.palette_material(sprite, i, NAME, metallic=METALLIC, roughness=ROUGHNESS) for i in (SKIN, RECESS)]

    # The outline: every sprite pixel, black edge included, traced and smoothed (Blender XY),
    # then in pixel-corner coordinates.
    outline_xy = lib.mask_outline(pixels, lambda i: i >= 0, size=2)
    # The traced outline still steps with the pixels, which shows as ribs down a round edge:
    # resample it evenly, smooth it with a running average, and push it back out so the
    # outline pixels stay covered.
    ring = smooth_ring(resample([(x * 12 + 12, 14 - y * 12) for x, y in outline_xy], 0.5),
                       SMOOTH_PASSES, OUT_PUSH)
    ring = resample(ring, TOP_STEP)

    bm = bmesh.new()
    to_xy = lambda u, v: ((u - 12) / 12, (14 - v) / 12)  # noqa: E731
    edge_verts = [bm.verts.new((*to_xy(u, v), EQUATOR / 12)) for u, v in ring]

    # Inward normals of the outline points (averaged over the two neighbouring edges).
    normals = []
    for i, p in enumerate(ring):
        a, b = Vector(ring[i - 1]), Vector(ring[(i + 1) % len(ring)])
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))
        if not inside(ring, tuple(Vector(p) + nrm * 0.1)):
            nrm = -nrm
        normals.append(nrm)

    def offset_ring(d, every):
        """Points d px in from the outline (every `every`-th outline point), kept only where the
        offset point really is about d px in (concave corners drop theirs)."""
        out = []
        for i in range(0, len(ring), every):
            q = Vector(ring[i]) + normals[i] * d
            if inside(ring, tuple(q)) and abs(poly_dist(ring, tuple(q)) - d) < 0.25:
                out.append(tuple(q))
        return out

    def fill(step, height, offset, rings, interior_from):
        pts = []
        for d, every in rings:
            pts += offset_ring(d, every)
        v = step * 0.5 + offset
        while v < 28:
            u = step * 0.5 + offset
            while u < 24:
                if inside(ring, (u, v)) and poly_dist(ring, (u, v)) > interior_from:
                    pts.append((u, v))
                u += step
            v += step
        coords = [Vector(p) for p in ring] + [Vector(p) for p in pts]
        nb = len(ring)
        edges = [(i, (i + 1) % nb) for i in range(nb)]
        out_v, _, out_f, orig_v, _, _ = delaunay_2d_cdt(coords, edges, [], 0, 1e-6)
        verts = []
        for k, co in enumerate(out_v):
            src = orig_v[k][0] if orig_v[k] else None
            if src is not None and src < nb:
                verts.append(edge_verts[src])
            else:
                d = poly_dist(ring, (co.x, co.y))
                verts.append(bm.verts.new((*to_xy(co.x, co.y), height((co.x, co.y), d) / 12)))
                vdist[verts[-1]] = d
        faces = []
        for f in out_f:
            cu = sum(out_v[i].x for i in f) / len(f)
            cv = sum(out_v[i].y for i in f) / len(f)
            if inside(ring, (cu, cv)):
                faces.append(([verts[i] for i in f], (cu, cv)))
        return faces

    vdist = {}  # each inner vertex's distance (px) in from the outline
    for vs, _ in fill(TOP_STEP, top_height, 0.0, TOP_RINGS, TOP_RINGS[-1][0] + 0.45):
        z = sum(v.co.z for v in vs) / len(vs) * 12
        inner = min(vdist.get(v, 0.0) for v in vs) >= RIM_AT  # inside the rim, not its outer side
        bm.faces.new(vs).material_index = 1 if z < RECESS_Z and inner else 0
    for vs, _ in fill(BACK_STEP, lambda p, d: back_height(d), 0.3, BACK_RINGS, BACK_RINGS[-1][0] + 0.8):
        twin = bm.faces.get(vs)
        if twin is not None:  # a sliver of three outline points on both sides: drop both
            bm.faces.remove(twin)
            continue
        f = bm.faces.new(list(reversed(vs)))
        f.material_index = 0
    # The antihelix: round tubes lying on the floor, standing about 2 px over it, the stem
    # climbing onto the lobe at its foot (the antitragus) and the crura dipping into the hollows.
    to_xyz = lambda q, z: (*to_xy(*q), z / 12)  # noqa: E731
    for ctrl, (t0, t1) in zip(ANTIHELIX, TAPER):
        path = lib.chaikin([(c + 0.5, r + 0.5, z, rad) for c, r, z, rad in ctrl], rounds=3, closed=False)
        # Arc length from each end; within the taper length the tube narrows to a point (a
        # rounded, sqrt-shaped tip) and sinks into the surface, so its ends fade out.
        run = [0.0]
        for a, b in zip(path, path[1:]):
            run.append(run[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        pts, radii = [], []
        for (u, v, z, rad), s in zip(path, run):
            f = 1.0
            if t0:
                f = min(f, s / t0)
            if t1:
                f = min(f, (run[-1] - s) / t1)
            f = max(0.0, f)
            pts.append(to_xyz((u, v), z - (1 - f) * rad * 1.6))
            radii.append(rad * f ** 0.7 / 12)
        lib.tube(bm, pts, radii, sides=10, mat_index=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
