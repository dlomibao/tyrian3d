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


def claw(bm, slots):
    GREY, LIGHT, BLADE, CAP, RED, DARKRED, STUD, HIGH, BLADE_TOP, LENS = slots
    P = lambda c, r, z=0.0: (lib.ex(c), lib.ey(r), z * U)  # noqa: E731

    # Outer armour band: along the top (rows 0.5-4) from the head, curving down the left side
    # (columns 5-9) to the blade's root at row 10. Rounded across, about as tall as wide.
    sweep(bm, [(18.0, 2.3), (15.0, 2.25), (12.0, 2.5), (9.4, 3.7), (7.6, 5.6), (6.6, 7.8), (6.1, 10.6)],
          [3.7, 3.7, 3.9, 4.4, 4.4, 4.2, 4.2], [4.0, 4.0, 4.1, 4.3, 4.3, 4.0, 3.4], -1.6, GREY, n=16,
          seams=(0.22, 0.47, 0.72))
    # Inner armour band: a flat-topped plate under it (rows 4.6-8.4, columns 9-18) that runs down
    # into the blade's spine; its left end catches the light (col 13).
    sweep(bm, [(18.0, 6.5), (14.5, 6.5), (11.8, 7.2), (10.0, 8.9), (9.0, 11.0), (8.6, 13.0)],
          [3.6, 3.6, 3.6, 3.4, 3.0, 2.6], [2.7, 2.7, 2.8, 2.7, 2.6, 2.4], -1.2, GREY, n=14,
          seams=(0.3, 0.62), profile=PLATE, smooth=False)

    # Head: a rounded purple hood on the outer band's right end (columns 17-22.6, rows 0.6-4.2),
    # the arm's tallest point, with a small gold plate on its left end.
    sweep(bm, [(16.6, 2.4), (19.0, 2.4), (21.4, 2.5), (22.7, 2.6)], [4.0, 4.0, 3.6, 2.2],
          [4.6, 4.7, 4.3, 3.0], -1.6, CAP, n=8)
    plate(bm, [(16.7, 1.4), (17.9, 1.4), (17.9, 3.4), (16.7, 3.4)], 5.1, 2.0, STUD, chamfer=0.3)

    # Blade: purple wedge from row 10 down to the point (column 3, row 26.4), thin along its outer
    # (left) edge, thicker at the spine.
    rings = []
    for r, right, h in ((9.8, 10.4, 1.6), (12.0, 10.4, 1.7), (15.0, 9.6, 1.6), (18.0, 9.4, 1.4),
                        (21.0, 8.6, 1.2), (22.6, 7.6, 1.0), (24.6, 5.6, 0.8), (25.8, 4.2, 0.5)):
        xl, xr, y = lib.ex(2.5), lib.ex(right), lib.ey(r)
        xm = xl + (xr - xl) * 0.55
        rings.append([(xl, y, -0.4 * U), (xl, y, 0.4 * U), (xm, y, h * U), (xr, y, h * U), (xr, y, -1.0 * U),
                      (xm, y, -1.0 * U)])
    rings.append([(lib.ex(3.0), lib.ey(26.6), 0.0)])
    lib.ring_loft(bm, rings, BLADE)
    # Its upper armour plate: raised purple, ending in a diagonal edge (column 7.5 row 13 to
    # column 3 row 18).
    plate(bm, [(2.6, 9.8), (9.8, 9.8), (9.6, 12.6), (7.8, 13.4), (3.0, 18.2), (2.6, 18.2)], 2.8, -0.6,
          BLADE_TOP, chamfer=0.5)
    # Gold badge on it near the spine (column 8, rows 10-13).
    plate(bm, [(7.4, 10.1), (9.2, 10.1), (9.2, 12.4), (8.2, 13.1), (7.4, 12.6)], 3.5, 1.5, STUD, chamfer=0.4)
    # Grey frame: the spine along the right edge down to the tip, a diagonal brace and a short
    # left rail, standing above the lower purple panels.
    spine = [(9.0, 12.0), (8.9, 15.0), (8.6, 18.0), (8.0, 21.0), (6.8, 23.0), (4.8, 25.2), (3.4, 26.2)]
    sweep(bm, spine, [2.0, 2.0, 1.9, 1.7, 1.5, 1.3, 0.9], [2.7, 2.6, 2.4, 2.2, 1.9, 1.5, 0.9], -1.0, GREY,
          n=12, profile=PLATE, smooth=False)
    plate(bm, [(2.6, 19.6), (7.6, 15.0), (8.6, 16.2), (3.2, 21.2), (2.6, 21.2)], 2.2, -0.4, LIGHT, chamfer=0.4)
    plate(bm, [(2.6, 17.8), (3.8, 17.8), (3.8, 22.8), (2.6, 23.0)], 1.9, -0.4, GREY, chamfer=0.35)

    # Hanger: a purple link from the head down to a grey joint (columns 20.7-23.5, rows 4.8-8),
    # then a thin round rod down to the machine block.
    lib.polyline_tube(bm, [P(19.6, 3.4, 0.6), P(19.7, 6.0, 0.6)], 0.8 * U, sides=8, mat_index=CAP)
    lib.polyline_tube(bm, [P(19.4, 6.5, 0.6), P(21.2, 6.5, 0.6)], 0.8 * U, sides=8, mat_index=GREY)
    plate(bm, [(20.7, 4.8), (23.5, 4.8), (23.5, 8.0), (20.7, 8.0)], 2.4, -1.2, GREY, chamfer=0.6)
    lib.polyline_tube(bm, [P(22.0, 7.4, 0.4), P(22.0, 10.0, 0.4), P(21.8, 12.8, 0.4)], [1.0 * U, 0.9 * U, 0.9 * U],
                      sides=8, mat_index=LIGHT)
    lib.polyline_tube(bm, [P(20.6, 7.6, 0.2), P(20.7, 12.6, 0.2)], 0.4 * U, sides=6, mat_index=GREY)
    # Machine block (columns 18.6-23.4, rows 12.4-17.6), a smaller block stacked on it, and the
    # white lens on its right side (column 22, rows 13-15).
    plate(bm, [(18.6, 12.4), (23.4, 12.4), (23.4, 17.6), (18.6, 17.6)], 2.8, -1.6, LIGHT, chamfer=0.6)
    plate(bm, [(19.2, 13.0), (21.6, 13.0), (21.6, 16.8), (19.2, 16.8)], 3.8, 2.0, GREY, chamfer=0.4)
    lib.ellipsoid(bm, P(22.5, 14.5, 2.4), (1.1 * U, 1.3 * U, 1.0 * U), segments=10, rings=5, mat_index=LENS)
    # Red claw: a dark red collar and a glowing faceted crystal pointing down.
    lib.polyline_tube(bm, [P(21.0, 17.4, 0.4), P(21.0, 19.4, 0.4)], 1.4 * U, sides=8, mat_index=DARKRED,
                      smooth=False)
    crystal(bm, 21.0, 19.2, 21.4, 23.0, 24.4, 1.3, 0.4, RED)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.4),  # 0 grey arm
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
