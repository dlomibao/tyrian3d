"""Claw, left-hand (newsh2.shp frame 49): a 3D version of its sprite.

Seen in episode 1 (levels 28-36) and episode 3, usually beside newsh2-51, its mirror image. A
thick armoured arm of two stacked grey bands (the outer one rounded, the inner one a flat-topped
plate, both with panel seams) hooks from a rounded purple head at the top right over to the left
and down into a purple blade: a raised purple armour plate with a gold badge, then a grey frame
(spine, diagonal brace, left rail) over lower purple panels down to the point. From the head a
purple link and a joint drop a thin rod to a grey machine block with a white lens, ending in a
glowing red faceted crystal with a dark red collar. One frame. Feature list:
assets/blender/features/newsh2-49.json.

Run: blender --background --python assets/blender/enemies/newsh2-49.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-49"
MIRROR = False
U = 1 / 12  # one sprite px


def E(c, r):
    """A point at sprite edge coordinates (column c, row r) in the XY plane."""
    return Vector((lib.ex(c), lib.ey(r)))


# Armour cross-section across a band: (across -1..1, up 0..1), chamfered rounded top, flat bottom.
BAND = [(-1.0, 0.0), (-1.0, 0.45), (-0.8, 0.82), (-0.42, 0.98), (0.0, 1.0), (0.42, 0.98), (0.8, 0.82),
        (1.0, 0.45), (1.0, 0.0)]
PLATE = [(-1.0, 0.0), (-1.0, 0.7), (-0.75, 1.0), (0.75, 1.0), (1.0, 0.7), (1.0, 0.0)]


def catmull(points, n):
    """n samples of a Catmull-Rom curve through `points` (2D Vectors), with their parameter 0..1."""
    pts = [points[0]] + list(points) + [points[-1]]
    segs = len(points) - 1
    out = []
    for k in range(n):
        t = k / (n - 1) * segs
        i = min(int(t), segs - 1)
        u = t - i
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return out


def lerp_list(vals, t):
    """Linear interpolation in a list of values spaced evenly over 0..1."""
    x = t * (len(vals) - 1)
    i = min(int(x), len(vals) - 2)
    return vals[i] + (vals[i + 1] - vals[i]) * (x - i)


def sweep(bm, ctrl, widths, tops, bottom, mat, n=14, seams=(), profile=BAND, smooth=True):
    """An armour band along a curve through `ctrl` (sprite edge coords): `widths` and `tops` (in px,
    spaced evenly along it) give its width and top height, `bottom` its underside (px). Each seam
    (a parameter 0..1) is a narrow groove across it, the joint between two armour segments."""
    ts = sorted([k / (n - 1) for k in range(n)] + [s + d for s in seams for d in (-0.025, 0.0, 0.025)])
    curve = catmull([E(*p) for p in ctrl], 200)
    rings = []
    for t in ts:
        i = min(int(t * 199), 198)
        f = t * 199 - i
        p = curve[i].lerp(curve[i + 1], f)
        d = (curve[i + 1] - curve[i]).normalized()
        nrm = Vector((-d.y, d.x))
        w = lerp_list(widths, t) / 2 * U
        top = lerp_list(tops, t) * U
        bot = bottom * U
        groove = any(abs(t - s) < 1e-6 for s in seams)
        if groove:
            w *= 0.9
            top = bot + (top - bot) * 0.86
        rings.append([(p.x + nrm.x * a * w, p.y + nrm.y * a * w, bot + (top - bot) * b) for a, b in profile])
    lib.ring_loft(bm, rings, mat, smooth=smooth)


def offset_polygon(pts, d):
    """Offset a counter-clockwise 2D polygon inwards by d (mitred corners)."""
    n = len(pts)
    out = []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (b - a).normalized()
        e1 = (c - b).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        m = (n0 + n1).normalized()
        out.append(b + m * (d / max(0.35, m.dot(n0))))
    return out


def plate(bm, poly, top, bottom, mat, chamfer=0.6, side_mat=None):
    """A hard plate: the polygon (sprite edge coords) extruded from `bottom` to `top` (px), its top
    edge chamfered by `chamfer` px. Flat shaded."""
    pts = [E(*p) for p in poly]
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    inner = offset_polygon(pts, chamfer * U)
    ch = min(chamfer, (top - bottom) * 0.5)
    rings = [[(p.x, p.y, bottom * U) for p in pts], [(p.x, p.y, (top - ch) * U) for p in pts],
             [(p.x, p.y, top * U) for p in inner]]
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(pts)
    sm = mat if side_mat is None else side_mat
    for r0, r1, m in ((vs[0], vs[1], sm), (vs[1], vs[2], mat)):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = m
            f.smooth = False
    f = bm.faces.new(vs[2])
    f.material_index = mat
    f = bm.faces.new(list(reversed(vs[0])))
    f.material_index = sm


def crystal(bm, c, r0, r1, r2, tip, radius, z, mat):
    """A faceted crystal pointing down the sprite (rows r0 -> tip) around column edge c."""
    rings = []
    for r, k in ((r0, 0.85), (r1, 1.0), (r2, 0.7)):
        ring = []
        for i in range(6):
            a = 2 * math.pi * i / 6
            ring.append((lib.ex(c) + math.cos(a) * radius * k * U, lib.ey(r), z * U + math.sin(a) * radius * k * U))
        rings.append(ring)
    rings.append([(lib.ex(c), lib.ey(tip), z * U)])
    lib.ring_loft(bm, rings, mat, smooth=False)


def resample(points, n):
    """n points spaced evenly by arc length along a Catmull-Rom curve through `points` (edge coords)."""
    dense = catmull([E(*p) for p in points], 400)
    acc = [0.0]
    for a, b in zip(dense, dense[1:]):
        acc.append(acc[-1] + (b - a).length)
    out, j = [], 0
    for k in range(n):
        s = acc[-1] * k / (n - 1)
        while j < len(acc) - 2 and acc[j + 1] < s:
            j += 1
        f = (s - acc[j]) / max(1e-9, acc[j + 1] - acc[j])
        out.append(dense[j].lerp(dense[j + 1], min(1.0, max(0.0, f))))
    return out


def band(bm, outer, inner, profile, tops, bottom, mats, n=16, seams=(), smooth=False):
    """Armour between two edge curves traced from the concept: `outer` and `inner` (edge coords, in
    the same direction) are its two long edges. `profile` = (across 0 outer..1 inner, up 0..1),
    `tops` (px, spaced evenly along it) its top height, `bottom` its underside (px). Seams (0..1)
    are narrow grooves across it. `mats` is one material or a function t -> material."""
    ts = sorted([k / (n - 1) for k in range(n)] + [s + d for s in seams for d in (-0.02, 0.0, 0.02)])
    o = resample(outer, 300)
    i_ = resample(inner, 300)
    rings, bands = [], []
    for t in ts:
        k = min(int(t * 299), 298)
        f = t * 299 - k
        po = o[k].lerp(o[k + 1], f)
        pi = i_[k].lerp(i_[k + 1], f)
        top = lerp_list(tops, t) * U
        bot = bottom * U
        if any(abs(t - s) < 1e-6 for s in seams):
            mid = (po + pi) / 2
            po, pi = mid.lerp(po, 0.9), mid.lerp(pi, 0.9)
            top = bot + (top - bot) * 0.84
        rings.append([(po.x + (pi.x - po.x) * a, po.y + (pi.y - po.y) * a, bot + (top - bot) * b)
                      for a, b in profile])
    for t0, t1 in zip(ts, ts[1:]):
        bands.append(mats((t0 + t1) / 2) if callable(mats) else mats)
    lib.ring_loft(bm, rings, bands, smooth=smooth)


def plate_z(bm, poly, top, bottom, mat, chamfer=0.5, side_mat=None):
    """Like plate(), but the top height is a function top(c, r) of the edge coords (a sloped plate)."""
    pts = [E(*p) for p in poly]
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    inner = offset_polygon(pts, chamfer * U)
    to_cr = lambda p: (p.x * 12 + 12, 14 - p.y * 12)  # noqa: E731
    rings = [[(p.x, p.y, bottom * U) for p in pts],
             [(p.x, p.y, (top(*to_cr(p)) - chamfer * 0.7) * U) for p in pts],
             [(p.x, p.y, top(*to_cr(p)) * U) for p in inner]]
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(pts)
    sm = mat if side_mat is None else side_mat
    for r0, r1, m in ((vs[0], vs[1], sm), (vs[1], vs[2], mat)):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = m
            f.smooth = False
    f = bm.faces.new(vs[2])
    f.material_index = mat
    f.smooth = False
    f = bm.faces.new(list(reversed(vs[0])))
    f.material_index = sm


def bar(bm, a, b, w, top, bottom, mat, chamfer=0.25):
    """A straight hard-edged frame bar from edge coords a to b, w px wide."""
    pa, pb = E(*a), E(*b)
    d = (pb - pa).normalized()
    nrm = Vector((-d.y, d.x)) * (w / 2 * U)
    poly = [pa + nrm, pb + nrm, pb - nrm, pa - nrm]
    plate(bm, [(p.x * 12 + 12, 14 - p.y * 12) for p in poly], top, bottom, mat, chamfer=chamfer)


# Edge curves traced from textures/newsh2-49/concept.png (sprite edge coords: column, row), kept
# inside the sprite's outline and covering its dark ring.
OUTER_EDGE = [(17.6, 0.08), (14.0, 0.3), (11.0, 1.0), (8.3, 2.3), (6.3, 4.0), (4.9, 6.1), (3.6, 8.6)]
SEAM = [(18.6, 3.75), (15.0, 3.95), (12.0, 4.75), (10.0, 5.8), (8.4, 7.1), (7.2, 8.6)]
INNER_EDGE = [(18.9, 8.3), (16.0, 8.9), (14.2, 10.3), (12.6, 12.1), (11.1, 13.7), (10.1, 15.4), (9.9, 18.0),
              (9.85, 20.7)]
RAIL = [(18.6, 3.75), (15.0, 3.95), (12.0, 4.75), (10.0, 5.8), (8.4, 7.1), (7.2, 8.6), (9.0, 9.6),
        (9.3, 11.0), (9.1, 13.4), (8.8, 16.0), (8.75, 20.6)]


def claw(bm, slots):
    GREY, LIGHT, BLADE, CAP, RED, DARKRED, STUD, HIGH, BLADE_TOP, LENS = slots
    P = lambda c, r, z=0.0: (lib.ex(c), lib.ey(r), z * U)  # noqa: E731
    ROUND = [(0.0, 0.0), (0.0, 0.5), (0.08, 0.82), (0.25, 0.97), (0.5, 1.0), (0.75, 0.97), (0.92, 0.82),
             (1.0, 0.5), (1.0, 0.0)]
    FLAT = [(0.0, 0.0), (0.0, 0.72), (0.12, 1.0), (0.88, 1.0), (1.0, 0.72), (1.0, 0.0)]

    # Outer armour band: the top of the arm from the head over to the left, ending where the purple
    # blade plate starts (row 9). Rounded across, segment seams where the concept draws them.
    band(bm, OUTER_EDGE, SEAM, ROUND, [4.3, 4.4, 4.4, 4.2, 4.0], -1.6, GREY, n=18,
         seams=(0.29, 0.49, 0.7))
    # Inner armour band: lower, flat-topped, under the outer one from the hanger round to the badge,
    # then on down the blade as its right-hand rail to row 20.7.
    band(bm, RAIL, INNER_EDGE, FLAT, [3.1, 3.1, 3.0, 2.9, 2.8, 2.6, 2.4, 2.2], -1.2, GREY, n=20,
         seams=(0.2, 0.42, 0.62))

    # Head: a rounded purple hood on the outer band's right end (columns 17.2-22.8, rows 0-4.2), the
    # arm's tallest point, with the gold plate on its left end.
    sweep(bm, [(17.0, 2.05), (19.0, 2.05), (21.3, 2.15), (22.85, 2.4)], [4.1, 4.1, 3.8, 2.0],
          [4.9, 5.0, 4.6, 3.0], -1.6, CAP, n=10)
    plate(bm, [(17.3, 0.4), (18.5, 0.4), (18.5, 2.9), (17.3, 2.9)], 5.4, 2.0, STUD, chamfer=0.3)
    # A dark port on the hood's lower front (concept: a round socket at column 20, row 3).
    lib.ellipsoid(bm, P(20.2, 3.1, 3.3), (0.55 * U, 0.55 * U, 0.4 * U), segments=8, rings=4, mat_index=GREY)

    # Purple blade plate: continues the outer band down the left side to the diagonal edge running
    # from column 2 row 20.3 up to column 8.8 row 14.2; highest along the arm, sloping to the outer edge.
    blade_poly = [(3.6, 8.6), (2.9, 10.6), (2.4, 12.8), (2.15, 15.5), (2.1, 18.0), (2.1, 20.3), (8.8, 14.2),
                  (9.1, 13.4), (9.3, 11.0), (9.0, 9.6), (7.2, 8.6)]
    plate_z(bm, blade_poly, lambda c, r: 2.2 + 1.5 * min(1.0, max(0.0, (c - 2.1) / 5.5)) - 0.04 * max(0.0, r - 9),
            -1.4, BLADE_TOP, chamfer=0.55)
    # Gold badge set in a grey octagonal frame near the spine (columns 7-9.7, rows 9.4-13.2).
    plate(bm, [(7.0, 9.9), (7.6, 9.3), (9.4, 9.3), (9.8, 9.9), (9.8, 12.7), (9.1, 13.3), (7.6, 13.3), (7.0, 12.7)],
          3.9, 1.0, GREY, chamfer=0.3)
    plate(bm, [(7.4, 10.1), (7.9, 9.7), (9.1, 9.7), (9.4, 10.1), (9.4, 12.2), (8.8, 12.8), (7.9, 12.8),
               (7.4, 12.4)], 4.4, 2.0, STUD, chamfer=0.35)

    # Lower blade: a low purple base from the diagonal down to the point (column 3, row 27) with a
    # grey frame standing on it: a rail along the diagonal, the left rail, the lower right edge and a
    # brace, leaving recessed purple panels between the bars.
    plate(bm, [(2.1, 20.3), (8.8, 14.2), (8.8, 20.8), (9.85, 20.9), (4.0, 26.85), (2.15, 26.85)], 1.0, -1.0,
          BLADE, chamfer=0.3)
    bar(bm, (2.3, 20.4), (9.0, 14.3), 1.0, 2.0, 0.2, GREY)
    plate(bm, [(2.15, 20.0), (3.6, 19.0), (3.6, 25.9), (3.2, 26.85), (2.15, 26.85)], 1.9, 0.2, GREY, chamfer=0.3)
    bar(bm, (3.0, 26.5), (9.6, 20.6), 1.1, 1.9, 0.2, GREY)
    bar(bm, (3.4, 19.8), (8.9, 21.0), 0.8, 1.8, 0.2, GREY)
    bar(bm, (3.4, 23.2), (6.6, 21.4), 0.6, 1.5, 0.2, GREY)

    # Hanger, as the concept draws it: a pipe from under the hood to a cross joint (columns 21.6-23.8,
    # rows 4.3-6.5), a side pipe back to the arm, and rods down to the machine block.
    lib.polyline_tube(bm, [P(20.6, 3.6, 1.0), P(21.6, 4.4, 1.0), P(22.6, 5.3, 1.0)], 0.55 * U, sides=8,
                      mat_index=LIGHT)
    plate(bm, [(21.6, 4.3), (23.8, 4.3), (23.8, 6.5), (21.6, 6.5)], 2.4, -1.0, GREY, chamfer=0.5)
    lib.ellipsoid(bm, P(22.7, 5.4, 2.4), (0.6 * U, 0.6 * U, 0.4 * U), segments=8, rings=4, mat_index=LIGHT)
    lib.polyline_tube(bm, [P(18.8, 5.7, 0.4), P(21.8, 5.7, 0.4)], 0.55 * U, sides=8, mat_index=LIGHT)
    lib.polyline_tube(bm, [P(18.8, 6.7, 0.0), P(21.8, 6.7, 0.0)], 0.45 * U, sides=6, mat_index=GREY)
    lib.polyline_tube(bm, [P(22.7, 6.4, 0.6), P(22.8, 9.5, 0.6), P(22.6, 12.7, 0.6)], 0.6 * U, sides=8,
                      mat_index=LIGHT)
    lib.polyline_tube(bm, [P(21.3, 6.6, 0.3), P(21.2, 9.5, 0.3), P(21.0, 12.7, 0.3)], 0.5 * U, sides=8,
                      mat_index=GREY)
    lib.polyline_tube(bm, [P(20.3, 6.8, -0.2), P(20.0, 9.6, -0.2), P(20.4, 12.7, -0.2)], 0.4 * U, sides=6,
                      mat_index=GREY)
    lib.polyline_tube(bm, [P(23.3, 6.5, 0.0), P(23.4, 10.5, 0.0)], 0.35 * U, sides=6, mat_index=GREY)

    # Machine block (columns 18.8-23.8, rows 12.5-17.3): an upper housing with the white lens on its
    # right, a lower housing, stacked chamfered boxes.
    plate(bm, [(18.8, 12.5), (23.8, 12.5), (23.8, 15.0), (18.8, 15.0)], 3.0, -1.6, LIGHT, chamfer=0.5)
    plate(bm, [(19.0, 15.0), (23.5, 15.0), (23.5, 17.3), (19.0, 17.3)], 2.5, -1.4, GREY, chamfer=0.5)
    plate(bm, [(19.3, 12.9), (21.3, 12.9), (21.3, 14.7), (19.3, 14.7)], 3.6, 2.0, GREY, chamfer=0.3)
    lib.polyline_tube(bm, [P(22.6, 14.3, 2.6), P(22.6, 14.3, 3.4)], 1.25 * U, sides=10, mat_index=GREY,
                      smooth=False)
    lib.ellipsoid(bm, P(22.6, 14.3, 3.3), (0.95 * U, 0.95 * U, 0.6 * U), segments=10, rings=5, mat_index=LENS)
    # Claw prongs and dark red collar under the block, then the glowing faceted crystal.
    lib.polyline_tube(bm, [P(20.0, 17.0, 0.4), P(19.7, 18.4, 0.4), P(20.2, 19.4, 0.4)], 0.4 * U, sides=6,
                      mat_index=GREY, smooth=False)
    lib.polyline_tube(bm, [P(22.4, 17.0, 0.4), P(22.7, 18.4, 0.4), P(22.2, 19.4, 0.4)], 0.4 * U, sides=6,
                      mat_index=GREY, smooth=False)
    lib.polyline_tube(bm, [P(21.2, 17.2, 0.4), P(21.2, 18.9, 0.4)], 1.3 * U, sides=8, mat_index=DARKRED,
                      smooth=False)
    crystal(bm, 21.1, 18.7, 20.6, 23.0, 24.85, 1.6, 0.4, RED)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.5, roughness=0.4),  # 0 grey arm
        pal(9, metallic=0.65, roughness=0.3),  # 1 light grey
        pal(90, metallic=0.35, roughness=0.4),  # 2 purple blade
        pal(87, metallic=0.35, roughness=0.45),  # 3 purple cap
        pal(119, emission_strength=3.5),  # 4 red claw tip
        pal(67, emission_strength=1.5),  # 5 dark red collar
        pal(171, metallic=0.4, roughness=0.35),  # 6 beige studs
        pal(109, metallic=0.6, roughness=0.25),  # 7 pale highlights
        pal(91, metallic=0.3, roughness=0.45),  # 8 purple armour plate
        pal(15, emission_strength=2.5),  # 9 white lens
    ]
    bm = bmesh.new()
    claw(bm, range(10))
    if MIRROR:
        lib.mirror_all_x(bm)
    return [(NAME, [lib.finish(NAME, bm, mats, coll)], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
