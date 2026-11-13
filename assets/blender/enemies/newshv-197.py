"""Red-eyed beetle pod (newshv.shp frames 197, 199, 201): a 3D version of its sprite.

What it is: a steel-blue armoured beetle pod of the episode-2 hives (level 17), MARKERS' craft that
drops the newshv-190 mines. It flies down the screen (sky drift with small swoops). Its head, at the
sprite's top, is a rounded octagonal blue housing with a raised bezel ring round one big glowing red
eye (a dark red rim, a dark pupil up and right of centre, a hot glint lower left); a pair of purple
horns, round tubes in section, curl from the housing's front corners out and back round it. Behind
the head a narrower neck carries a pale chest dome and a green ribbed pipe down each shoulder; a dark
waist collar joins it to the rear shell, two rounded lobes split by a groove, each with a slanted
red vent near its stern. A second pair of shorter purple horns curls round the shell's front corners.
Belly: a plain closed rounded underside (it flies free).

The three frames only change the glows: the eye's glint and the vents brighten, and on the last
frame the pupil fills with red. One model covers them all, with those colours stepping per frame
(palette_material frames=, D17). Glows are emission strength 1 (the palette colour unlit, D126) on
metallic 1 / roughness 0.9 surfaces, so no lit reflection washes them out (D173).

Built in sprite pixels (x right, y down the sprite, z up; 12 px = 1 unit; x and y are pixel
edges, so column c spans x c..c+1), converted at the end. The sprite's mirror line is x = 12.5 (the
centre of column 12). Colours are the sprite's own palette index per region (hull 58, bezel 57, rear
shell 59, chest 61, horns 86 front / 88 side, ribs 40, eye 115, rim 112, pupil 82, glint 121, vents 115/121/112);
shading and highlights come from the game's light.

Run: blender --background --python assets/blender/enemies/newshv-197.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshv-197"
MODEL = f"enemies/{NAME}"

CX = 12.5  # the sprite's mirror line (centre of column 12)

# material slots
(HULL, BEZEL, DARK, SHELL, CHEST, HORN, RIB, RIM, EYE, GLINT, PUPIL, VENT, VENT_GLOW, VENT_RIM, KEEL,
 RIB_DK, HORN_S) = range(17)


def sgnpow(v, e):
    return math.copysign(abs(v) ** e, v)


def frange(a, b, step):
    n = max(1, round((b - a) / step))
    return [a + (b - a) * i / n for i in range(n + 1)]


def merge_ys(*lists):
    return sorted(set(round(v, 4) for lst in lists for v in lst))


# --- sections, lofts, tubes (as newshv-165) -----------------------------------------------------

def section(cx, zc, hw, ht, hb, sides, nt=2.4, nb=2.0):
    """A closed cross-section (x, z): superellipse top (exponent nt) and bottom (nb)."""
    pts = []
    for k in range(sides):
        a = 2 * math.pi * (k + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        n = nt if s >= 0 else nb
        x = cx + hw * sgnpow(c, 2 / n)
        z = zc + (ht * sgnpow(s, 2 / nt) if s >= 0 else abs(hb) * sgnpow(s, 2 / nb))
        pts.append((x, z))
    return pts


def loft(bm, ys, secf, mat):
    """A closed body through sections secf(y) -> [(x, z)]; the ends close with a fan to the end
    section's centre. Returns the new faces."""
    faces = []
    rings = []
    for y in ys:
        rings.append([bm.verts.new((x, y, z)) for x, z in secf(y)])
    for r0, r1 in zip(rings, rings[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for ring in (rings[0], rings[-1]):
        c = sum((v.co for v in ring), Vector()) / len(ring)
        cv = bm.verts.new(c)
        n = len(ring)
        for i in range(n):
            faces.append(bm.faces.new((ring[i], ring[(i + 1) % n], cv)))
    for f in faces:
        f.material_index = mat
    return faces


def tube(bm, points, half_w, half_h, sides=10, mats=None, mat=0, closed=False):
    """A tube along 3D points with a horizontal and vertical half-size per point (0 = a tip);
    mats[i] colours the segment from point i to i + 1. closed: a loop (no tips, no caps)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        if half_w[i] == 0 and not closed:
            rings.append([bm.verts.new(p)])
            continue
        if closed:
            t = (pts[(i + 1) % n] - p).normalized() + (p - pts[i - 1]).normalized()
        elif i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * math.cos(a) * half_w[i] + up * math.sin(a) * half_h[i]))
        rings.append(ring)
    faces = []
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for i, (r0, r1) in enumerate(pairs):
        m = mats[i] if mats else mat
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[k], r1[j]))
            elif len(r1) == 1:
                f = bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = m
            faces.append(f)
    if not closed:
        for ring, m in ((rings[0], (mats or [mat])[0]), (rings[-1], (mats or [mat])[-1])):
            if len(ring) > 1:
                f = bm.faces.new(ring)
                f.material_index = m
                faces.append(f)
    return faces


def mirror(bm, faces):
    """Mirror faces about x = CX."""
    vmap = {}
    out = []
    for f in faces:
        if not f.is_valid:
            continue
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm.verts.new((2 * CX - v.co.x, v.co.y, v.co.z))
            vs.append(vmap[v])
        nf = bm.faces.new(list(reversed(vs)))
        nf.material_index = f.material_index
        out.append(nf)
    return out


def smooth_path(pts, n=4):
    """Catmull-Rom through points, n samples per span (keeps the ends)."""
    P = [Vector(p) for p in pts]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


def resample(vals, n=4):
    out = []
    for a, b in zip(vals, vals[1:]):
        out += [a + (b - a) * k / n for k in range(n)]
    return out + [vals[-1]]


# --- plan and height profiles (sprite px) -------------------------------------------------------

# Head and neck hull: rows 2-15. The head is the eye housing (widest over rows 5-9), the neck
# (rows 10-15) is 13 px wide.
HULL_Y0, HULL_Y1 = 2.0, 15.45
HULL_HW = T.pchip([2.0, 2.4, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.4, 10.2, 11.0, 13.0, 14.5, 15.45],
                  [2.7, 3.45, 4.45, 5.4, 6.2, 6.75, 7.2, 7.35, 7.2, 6.55, 6.42, 6.42, 6.42, 6.2])
HULL_ZT = T.pchip([2.0, 2.6, 4.0, 6.0, 8.0, 10.5, 12.5, 14.3, 15.0, 15.45], [1.6, 2.6, 3.6, 4.1, 4.2, 4.05, 3.85, 3.5,
                                                                           2.9, 2.2])
HULL_ZB = T.pchip([2.0, 3.0, 7.0, 12.0, 15.45], [0.8, 1.6, 2.0, 1.85, 1.5])
HULL_NT = 2.4


def surf_z(x, y, cx, hw, zt, nt):
    if hw <= 1e-6:
        return 0.0
    t = min(1.0, abs(x - cx) / hw)
    return zt * (1 - t ** nt) ** (1 / nt)


def hull_z(x, y):
    return surf_z(x, y, CX, HULL_HW(y), HULL_ZT(y), HULL_NT)


# Eye: an ellipse over columns 8-16, rows 3-10 (its 112 rim included), centre (12.5, 7.0).
EYE_C = (12.5, 7.0)
EYE_A, EYE_B = 4.45, 3.95
EYE_H = 1.55  # how far its crown stands above the bezel's foot
# Bezel ring round it (the 53/57 band): centreline ellipse, top at row 2, sides at columns 6-7.
BEZ_A, BEZ_BT, BEZ_BB = 5.35, 4.4, 4.2

# Rear shell: two lobes, rows 15-24. The left lobe's outer and inner edges per y.
LOBE_Y0, LOBE_Y1 = 15.3, 25.0
LOBE_XL = T.pchip([15.3, 15.7, 16.2, 17.0, 19.5, 20.4, 21.0, 22.0, 23.0, 23.8, 24.4, 24.8, 25.0],
                  [6.2, 5.45, 5.05, 4.98, 4.98, 5.15, 5.6, 6.02, 6.6, 7.4, 8.4, 9.4, 10.4])
LOBE_XR = T.pchip([15.3, 23.6, 23.95, 24.25, 24.6, 25.0], [12.75, 12.75, 12.4, 12.05, 11.85, 11.4])
LOBE_ZT = T.pchip([15.3, 15.8, 16.6, 18.0, 20.5, 22.5, 23.8, 24.4, 24.8, 25.0], [1.6, 2.9, 3.85, 4.15, 4.05, 3.6,
                                                                               2.75, 1.95, 1.1, 0.35])
LOBE_ZC = 1.0
LOBE_NT = 2.2


def lobe_hb(y):
    """The lobe's depth below LOBE_ZC: rounds up with the crest at both ends."""
    return min(1.9, 0.25 + 0.5 * LOBE_ZT(y))


def base_hw(y):
    """The shell base under the lobes ends before the lobes' rear notch."""
    return max(0.05, (CX - LOBE_XL(y) - 0.25) * min(1.0, max(0.0, (24.3 - y) / 1.3)) ** 0.5)


def lobe_z(x, y):
    xl, xr = LOBE_XL(y), LOBE_XR(y)
    return LOBE_ZC + surf_z(x, y, 0.5 * (xl + xr), 0.5 * (xr - xl), LOBE_ZT(y), LOBE_NT)


def build(bm):
    parts = {}

    # Head and neck hull.
    ys = merge_ys(frange(HULL_Y0, 3.0, 0.2), frange(3.0, 14.4, 0.5), frange(14.4, HULL_Y1, 0.25))
    parts["hull"] = loft(bm, ys, lambda y: section(CX, 0.0, HULL_HW(y), HULL_ZT(y), -HULL_ZB(y), 32, nt=HULL_NT,
                                                   nb=2.0), HULL)

    # The eye: a lens dome over the ellipse, base sunk into the hull. Painted flush by plan position:
    # dark rim ring, pupil (up right), glint (lower left); no bumps.
    ex, ey = EYE_C
    base = max(hull_z(ex + EYE_A * c, ey + EYE_B * s) for c, s in
               ((math.cos(a), math.sin(a)) for a in [i * math.pi / 12 for i in range(24)]))

    def eye_z(x, y):
        r = min(1.0, math.hypot((x - ex) / EYE_A, (y - ey) / EYE_B))
        return base + 0.35 + EYE_H * math.sqrt(max(0.0, 1 - r ** 2.2))

    # A polar dome: rings of constant r, so the rim (r > 0.8) is a clean ring; a skirt down into
    # the hull closes it.
    NS = 56
    radii = [0.0, 0.12, 0.25, 0.38, 0.5, 0.6, 0.68, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    rings = []
    for r in radii[1:]:
        rings.append([bm.verts.new((ex + EYE_A * r * math.cos(2 * math.pi * i / NS),
                                    ey + EYE_B * r * math.sin(2 * math.pi * i / NS),
                                    eye_z(ex + EYE_A * r * math.cos(2 * math.pi * i / NS),
                                          ey + EYE_B * r * math.sin(2 * math.pi * i / NS)))) for i in range(NS)])
    skirt = [bm.verts.new((v.co.x, v.co.y, base - 1.6)) for v in rings[-1]]
    apex = bm.verts.new((ex, ey, eye_z(ex, ey)))
    bottom = bm.verts.new((ex, ey, base - 1.6))
    eye = []
    for i in range(NS):
        j = (i + 1) % NS
        f = bm.faces.new((apex, rings[0][i], rings[0][j]))
        f.material_index = EYE
        eye.append(f)
        for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
            f = bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
            f.material_index = RIM if radii[k + 1] >= 0.8 else EYE
            eye.append(f)
        for q in ((rings[-1][i], skirt[i], skirt[j], rings[-1][j]), (skirt[i], bottom, skirt[j])):
            f = bm.faces.new(q)
            f.material_index = RIM
            eye.append(f)

    def patch(cx, cy, ra, rb, r_in, mat, lift=0.06):
        """A flush elliptical disc (or ring, r_in > 0) lying on the eye: paint, not a bump."""
        rs = [r_in + (1 - r_in) * k / 4 for k in range(5)] if r_in > 0 else [0.2, 0.4, 0.6, 0.8, 1.0]
        N = 32
        rr = [[bm.verts.new((cx + ra * r * math.cos(2 * math.pi * i / N), cy + rb * r * math.sin(2 * math.pi * i / N),
                             eye_z(cx + ra * r * math.cos(2 * math.pi * i / N),
                                   cy + rb * r * math.sin(2 * math.pi * i / N)) + lift)) for i in range(N)] for r in rs]
        out = []
        if r_in == 0:
            c = bm.verts.new((cx, cy, eye_z(cx, cy) + lift))
            out += [bm.faces.new((c, rr[0][i], rr[0][(i + 1) % N])) for i in range(N)]
        for r0, r1 in zip(rr, rr[1:]):
            out += [bm.faces.new((r0[i], r1[i], r1[(i + 1) % N], r0[(i + 1) % N])) for i in range(N)]
        for f in out:
            f.material_index = mat
        return out

    # The pupil: a dark ring up and right of centre (82 round a red centre on columns 12-14, rows 5-7).
    eye += patch(13.5, 6.55, 1.35, 1.3, 0.38, PUPIL)
    # The glint: a crescent round the lower left of the iris (columns 10-13, rows 5-8).
    A0, A1, R0, NA = math.radians(238), math.radians(84), 1.95, 24
    left, right = [], []
    for i in range(NA + 1):
        u = i / NA
        a = A0 + (A1 - A0) * u
        w = 0.08 + 0.62 * math.sin(math.pi * u) ** 0.7
        for rad, lst in ((R0 + w, left), (R0 - w, right)):
            x, y = ex + rad * math.cos(a), ey + rad * math.sin(a) * (EYE_B / EYE_A) * 1.05
            lst.append(bm.verts.new((x, y, eye_z(x, y) + 0.06)))
    for i in range(NA):
        f = bm.faces.new((left[i], left[i + 1], right[i + 1], right[i]))
        f.material_index = GLINT
        eye.append(f)
    parts["eye"] = eye

    # The bezel ring: a closed tube round the eye on the housing's top.
    loop = []
    M = 48
    for i in range(M):
        a = 2 * math.pi * i / M
        c, s = math.cos(a), math.sin(a)
        b = BEZ_BT if s < 0 else BEZ_BB
        # a rounded octagon: superellipse exponent 2.6
        x = ex + BEZ_A * sgnpow(c, 2 / 2.6)
        y = ey + b * sgnpow(s, 2 / 2.6)
        loop.append((x, y, max(hull_z(x, y), base) + 0.15))
    hw = [0.95 if abs(math.sin(2 * math.pi * i / M)) < 0.7 else 0.75 for i in range(M)]
    hw = [0.5 * (hw[i - 1] + hw[i]) for i in range(M)]
    parts["bezel"] = tube(bm, loop, hw, [0.62] * M, sides=10, mat=BEZEL, closed=True)

    # Front horns: round tubes from the housing's front corners, curling out and back round it.
    path = [(9.4, 2.85, 2.4), (8.1, 2.62, 2.75), (6.95, 3.0, 3.0), (5.95, 3.78, 3.15), (4.95, 4.8, 3.2),
            (4.4, 5.9, 3.15), (4.15, 7.0, 3.0), (4.3, 8.05, 2.6), (4.65, 8.85, 2.1)]
    hws = [0.6, 0.72, 0.95, 1.07, 1.25, 1.32, 1.15, 0.82, 0.0]
    pts = smooth_path(path, 4)
    hw_s = resample(hws, 4)
    horn = tube(bm, pts, hw_s, [0.92 * h for h in hw_s], sides=12, mat=HORN)
    # Side horns: shorter crescents round the rear shell's front corners (rows 13-19).
    path = [(4.65, 13.2, 2.4), (4.45, 13.85, 2.7), (4.42, 14.6, 2.85), (4.3, 15.45, 2.85), (3.98, 16.45, 2.75),
            (3.95, 17.5, 2.6), (4.12, 18.6, 2.3), (4.45, 19.45, 1.95), (4.85, 20.05, 1.6)]
    hws = [0.0, 0.62, 1.5, 1.45, 1.02, 0.96, 0.85, 0.55, 0.0]
    pts = smooth_path(path, 4)
    hw_s = resample(hws, 4)
    horn += tube(bm, pts, hw_s, [min(0.95, 0.85 * h) for h in hw_s], sides=12, mat=HORN_S)
    parts["horn"] = horn + mirror(bm, horn)

    # Green ribbed pipe down each shoulder of the neck (columns 6-7, rows 8-15).
    path2 = [(6.3, 7.75), (6.6, 8.5), (7.0, 9.5), (7.45, 10.6), (7.55, 12.0), (7.55, 13.6), (7.55, 15.2), (7.6, 16.1)]
    rhw = [0.0, 0.72, 0.85, 0.7, 0.66, 0.66, 0.72, 0.0]
    pts = []
    for x, y in path2:
        z = hull_z(x, y) + 0.1 if y < 14.9 else 2.55
        pts.append((x, y, z))
    pts = smooth_path(pts, 3)
    hws = resample(rhw, 3)
    rib = tube(bm, pts, hws, [0.62 * h for h in hws], sides=10, mat=RIB)
    # the ribs: rings round the pipe
    for ry in (10.0, 11.6, 13.2, 14.6):
        x = 7.5
        z = hull_z(x, ry) + 0.1
        rib += tube(bm, [(x, ry - 0.3, z), (x, ry - 0.18, z), (x, ry + 0.18, z), (x, ry + 0.3, z)],
                    [0.0, 0.82, 0.82, 0.0], [0.0, 0.56, 0.56, 0.0], sides=10, mat=RIB_DK)
    parts["rib"] = rib + mirror(bm, rib)

    # Pale chest dome on the neck (columns 10-14, rows 11-14).
    cy0, ca, cb = 13.25, 2.55, 1.9
    cz = hull_z(CX, cy0) - 0.4
    parts["chest"] = loft(bm, merge_ys(frange(cy0 - cb, cy0 + cb, 0.25)),
                          lambda y: section(CX, cz, max(0.04, ca * math.sqrt(max(0.0, 1 - ((y - cy0) / cb) ** 2))),
                                            0.4 + 0.75 * math.sqrt(max(0.0, 1 - ((y - cy0) / cb) ** 2)), -0.5, 20,
                                            nt=2.2), CHEST)

    # Dark waist collar between the neck and the rear shell (row 15).
    parts["collar"] = loft(bm, merge_ys(frange(14.6, 16.4, 0.3)),
                           lambda y: section(CX, 0.0, 6.35, 2.95, -1.9, 28, nt=2.6), DARK)

    # Rear shell: a low base under two raised lobes; the groove between them is the base's top.
    def base_sec(y):
        zt = LOBE_ZT(y)
        k = min(1.0, (y - 15.0) / 1.2) ** 0.5  # the front hides in the waist collar
        e = min(1.0, max(0.0, (24.3 - y) / 3.0)) ** 0.55  # the stern rounds up from below
        return section(CX, 0.0, min(base_hw(y), 6.1 + 1.0 * k), max(0.3, min(2.6 + 0.2 * k, zt + LOBE_ZC - 0.9)),
                       -max(0.25, min(1.6 + 0.2 * k, 0.3 + 0.7 * zt) * e), 28, nt=2.2)

    shell = loft(bm, merge_ys(frange(15.2, 16.6, 0.25), frange(16.6, 23.0, 0.45), frange(23.0, 24.25, 0.2)),
                 base_sec, SHELL)
    ys = merge_ys(frange(LOBE_Y0, 16.6, 0.25), frange(16.6, 23.4, 0.45), frange(23.4, LOBE_Y1, 0.16))

    def lobe_sec(y):
        xl, xr = LOBE_XL(y), LOBE_XR(y)
        return section(0.5 * (xl + xr), LOBE_ZC, max(0.04, 0.5 * (xr - xl)), LOBE_ZT(y), -lobe_hb(y), 28,
                       nt=LOBE_NT)

    lobe = loft(bm, ys, lobe_sec, SHELL)

    # Vent on the lobe (columns 9-10, rows 20-23): a slanted oval, dark red lip, glowing core with
    # its hot forward end.
    vc = Vector((9.95, 21.95))
    vd = Vector((0.3, 1.0)).normalized()
    vn = Vector((vd.y, -vd.x))
    va, vb = 1.95, 0.95
    lip = []
    M = 24
    for i in range(M):
        a = 2 * math.pi * i / M
        p = vc + vd * math.cos(a) * va + vn * math.sin(a) * vb
        lip.append((p.x, p.y, lobe_z(p.x, p.y) + 0.05))
    vent = tube(bm, lip, [0.3] * M, [0.28] * M, sides=8, mat=VENT_RIM, closed=True)
    core = []
    K = 10
    for j in range(K):  # a shallow cushion inside the lip, conforming to the lobe
        s = 1.0 - j / K
        ring = []
        for i in range(M):
            a = 2 * math.pi * i / M
            p = vc + vd * math.cos(a) * va * s + vn * math.sin(a) * vb * s
            ring.append(bm.verts.new((p.x, p.y, lobe_z(p.x, p.y) + 0.05 + 0.12 * (1 - s * s))))
        core.append(ring)
    top = bm.verts.new((vc.x, vc.y, lobe_z(vc.x, vc.y) + 0.17))
    under = [bm.verts.new((v.co.x, v.co.y, v.co.z - 0.5)) for v in core[0]]
    vf = []
    for r0, r1 in zip(core, core[1:]):
        for i in range(M):
            j = (i + 1) % M
            vf.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(M):
        j = (i + 1) % M
        vf.append(bm.faces.new((core[-1][i], core[-1][j], top)))
        vf.append(bm.faces.new((under[j], under[i], core[0][i], core[0][j])))
    vf.append(bm.faces.new(list(reversed(under))))
    for f in vf:
        c = f.calc_center_median()
        d = Vector((c.x, c.y)) - vc
        f.material_index = VENT_GLOW if d.dot(vd) < -0.15 and c.z > lobe_z(c.x, c.y) - 0.1 else VENT
    vent += vf
    lobe += vent
    parts["lobe"] = lobe + mirror(bm, lobe)
    parts["shell"] = shell

    # Keel strip in the groove between the lobes (column 12, rows 16-24).
    kp = [(CX, y, lobe_z(LOBE_XR(y), y) + 0.25) for y in (16.0, 17.2, 19.5, 21.8, 23.2, 23.9)]
    kp = [(x, y, min(z, 2.9)) for x, y, z in kp]
    kpts = smooth_path(kp, 3)
    nk = len(kpts)
    parts["keel"] = tube(bm, kpts, [0.0 if i in (0, nk - 1) else 0.42 for i in range(nk)],
                         [0.0 if i in (0, nk - 1) else 0.35 for i in range(nk)], sides=8, mat=KEEL)
    return parts


def to_blender(bm):
    m = Matrix(((1 / 12, 0, 0, -12 / 12), (0, -1 / 12, 0, 14 / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)


def glow(sprite, index, part, frames=None):
    """A glow (D126 strength 1 = the palette colour unlit) on a metallic 1 / rough 0.9 surface (D173)."""
    return common.palette_material(sprite, index, f"{NAME}-{part}", metallic=1.0, roughness=0.9,
                                   emission_strength=1.0, frames=frames)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    f1, f2 = (f["index"] for f in sprite["frames"][1:3])  # 199, 201
    mats = [
        pal(58, metallic=0.45, roughness=0.38),  # HULL: steel-blue head and neck
        pal(57, metallic=0.45, roughness=0.36),  # BEZEL: the eye's housing ring
        pal(52, metallic=0.3, roughness=0.6),  # DARK: the waist collar
        pal(59, metallic=0.5, roughness=0.33),  # SHELL: the pale steel rear lobes
        pal(61, metallic=0.5, roughness=0.3),  # CHEST: pale chest dome
        pal(86, metallic=0.3, roughness=0.42),  # HORN: purple front horns
        pal(40, metallic=0.2, roughness=0.45),  # RIB: green pipes
        glow(sprite, 112, "rim"),  # RIM: the eye's dark red rim
        glow(sprite, 115, "eye"),  # EYE: the red eye
        glow(sprite, 121, "glint", {f1: 124, f2: 126}),  # GLINT: the eye's hot spot, brightening
        glow(sprite, 82, "pupil", {f2: 114}),  # PUPIL: dark, red on the last frame
        glow(sprite, 115, "vent", {f1: 117, f2: 119}),  # VENT: vent core
        glow(sprite, 121, "ventglow", {f1: 123, f2: 125}),  # VENT_GLOW: its hot forward end
        glow(sprite, 112, "ventrim", {f1: 113, f2: 115}),  # VENT_RIM: the vent's lip
        pal(55, metallic=0.4, roughness=0.45),  # KEEL: strip in the lobes' groove
        pal(37, metallic=0.2, roughness=0.5),  # RIB_DK: the rings on the green pipes
        pal(88, metallic=0.3, roughness=0.42),  # HORN_S: purple side horns
    ]
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    to_blender(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    # D90/D118: the outline shell from the sealed copy, before the hidden faces are culled.
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=3000)
    if "--no-cull" not in sys.argv:
        T.cull_hidden(obj, grid=3, ndirs=32)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    print("tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))


if __name__ == "__main__":
    main()
