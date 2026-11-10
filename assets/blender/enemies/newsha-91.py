"""Sand pod newsha-91 (newsha.shp 91/129, 24x28 px): the sand pod, a sealed tan dome with a red vent.

Reading of the sprite (the tile is painted sand edge to edge; the sand is the HD ground's job, D103):
newsha-91 is pixel-identical to newshf-39 (the bell turret, D116) except in two places, so the dome,
the sensor ball on its arm and the barrel are newshf-39's accepted shapes, copied here (no shared lib):
- A tan metal dome, footprint ellipse centre (10.5, 11.6) px (pixel-edge coords), 8.5 x 6.6 px radii,
  lit from the upper left (the white patch is sheen). One pchip profile from the crown to a low foot
  lip; eight flush armour panels with engraved seams; bolt heads round the foot.
- Where the turret has its eye, the pod has a CLOSED HATCH (centre (9.5, 11.5), 2.5 px; region median
  21): the dome's low chamfered lip, a dark seam gap, a slightly domed lid with a two-leaf split, a
  hinge block, six bolt heads and a small grab boss.
- A glowing VENT (rows 13-18, cols 3-8) curving down the lower-left flank along the dome's rim and
  spilling over the foot: a chamfered cowl (113) round a sunken grille (115 rim, 117 glow, a 121
  hot core, three slats). Frame 129 brightens it (116 / 121 / 123, palette_material frames=).
- Sensor ball upper right (17, 5.2) on an arm; barrel out of a collar on the lower right, round the
  foot and straight down the screen (the light stripe and the dark spike below the dome).
Underside: a flat closed disc, no detail.

    blender --background --python assets/blender/enemies/newsha-91.py
Exports public/models/enemies/newsha-91.glb + src/render/spriteModels/newsha-91.json (object + outline shell).
Coordinates while building: x = col_edge - 12, y = row_edge - 14 (down the screen), z up, all in
sprite px; finish() maps to Blender X = x/12, Y = -y/12, Z = z/12.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newsha-91"
PX = 1 / 12
TAG = NAME

# --- the reading, in build coordinates ----------------------------------------------------------
DCX, DCY, DRX, DRY = 10.5 - 12, 11.6 - 14, 8.5, 6.6  # dome footprint
T_CAP = 1.0           # the cap runs all the way to the footprint's edge (one continuous curve)
Z_COLLAR = 0.55       # height of the low foot lip at the rim
Z_APEX = 8.6          # crown height (px): a full, bulbous dome
EYE = (9.5 - 12, 11.5 - 14)  # the hatch sits where the turret has its eye
VENT = [(3.95, 13.95), (4.3, 14.6), (4.75, 15.3), (5.75, 16.5), (6.95, 17.45), (8.15, 18.3)]  # centreline, edge coords
VENT_HW = 1.25
BALL = (17.0 - 12, 5.2 - 14, 2.7, 1.35)
BARREL = [(16.9 - 12, 13.6 - 14, 2.3), (16.4 - 12, 15.3 - 14, 2.0), (15.1 - 12, 16.8 - 14, 1.75),
          (13.0 - 12, 18.1 - 14, 1.55), (11.1 - 12, 19.1 - 14, 1.45), (10.6 - 12, 20.4 - 14, 1.4),
          (10.5 - 12, 22.0 - 14, 1.4), (10.5 - 12, 25.0 - 14, 1.4)]
BR = 1.15


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) interpolant through (xs, ys)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        i = max(0, min(n - 2, next((k for k in range(n - 1) if x <= xs[k + 1]), n - 2)))
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


# Cap profile stations (normalised radius -> height), one pchip curve from the crown to the rim: a
# full glossy bulb whose shoulders roll steeply down into a low foot lip (no terraces or steps).
_cap = pchip([0.0, 0.3, 0.55, 0.75, 0.86, 0.94, 1.0],
             [Z_APEX, Z_APEX - 0.35, Z_APEX - 1.5, Z_APEX - 3.3, Z_APEX - 4.8, Z_APEX - 6.4, Z_COLLAR])


def cap_z(t):
    return _cap(min(max(t, 0.0), T_CAP))


def S(th, t):
    """A point of the dome surface at angle th, normalised radius t (t <= T_CAP)."""
    return Vector((DCX + DRX * t * math.cos(th), DCY + DRY * t * math.sin(th), cap_z(t)))


def S_normal(th, t):
    e = 1e-3
    p = S(th, t)
    if t < 0.02:
        return Vector((0, 0, 1))
    a = S(th + e, t) - p
    b = S(th, min(t + e, T_CAP)) - S(th, max(t - e, 0))
    n = b.cross(a)
    if n.z < 0:
        n = -n
    return n.normalized()


def r_at(th, t):
    """Approximate px distance of S(th, t) from the dome axis (to turn px gaps into angles)."""
    return max(1e-3, t * math.hypot(DRX * math.cos(th), DRY * math.sin(th)))


def dome_height_at(x, y):
    t = math.hypot((x - DCX) / DRX, (y - DCY) / DRY)
    return cap_z(t) if t <= 1 else 0.0


# --- mesh building --------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(Vector(p))

    def f(self, vs, mat):
        if len({id(x) for x in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def grid(self, rows, mat, closed=True, mats=None):
        """Quads between consecutive rings (lists of verts, single-vert rings collapse to fans)."""
        for j, (r0, r1) in enumerate(zip(rows, rows[1:])):
            m = mats[j] if mats else mat
            if len(r0) == 1 and len(r1) == 1:
                continue
            n = max(len(r0), len(r1))
            for i in range(n if closed else n - 1):
                k = (i + 1) % n
                if len(r0) == 1:
                    self.f((r0[0], r1[i], r1[k]), m)
                elif len(r1) == 1:
                    self.f((r0[i], r0[k], r1[0]), m)
                else:
                    self.f((r0[i], r0[k], r1[k], r1[i]), m)


def lathe(M, centre, axis, profile, sides, mats, phase=0.0):
    """Revolve profile [(r, h)] around `axis` through `centre`; mats[i] is the segment i->i+1."""
    axis = Vector(axis).normalized()
    ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    u = (ref - axis * ref.dot(axis)).normalized()
    w = axis.cross(u)
    rows = []
    for r, h in profile:
        c = Vector(centre) + axis * h
        if r < 1e-6:
            rows.append([M.v(c)])
        else:
            rows.append([M.v(c + (u * math.cos(phase + 2 * math.pi * k / sides) +
                                  w * math.sin(phase + 2 * math.pi * k / sides)) * r) for k in range(sides)])
    M.grid(rows, 0, mats=mats)
    if len(rows[0]) > 1:
        M.f(list(reversed(rows[0])), mats[0])
    if len(rows[-1]) > 1:
        M.f(rows[-1], mats[-1])


def frames_along(pts):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline."""
    ts = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        ts.append((b - a).normalized())
    n = Vector((0, 0, 1))
    n = (n - ts[0] * n.dot(ts[0])).normalized()
    out = []
    for t in ts:
        n = (n - t * n.dot(t)).normalized()
        out.append((t, n, t.cross(n)))
    return out


def sweep(M, pts, radii, sides, mats, cap0=True, cap1=True):
    """A tube through pts with per-point radius; mats per segment."""
    fr = frames_along(pts)
    rows = []
    for p, (t, n, b), r in zip(pts, fr, radii):
        if r < 1e-6:
            rows.append([M.v(p)])
        else:
            rows.append([M.v(p + (n * math.cos(2 * math.pi * (k + 0.5) / sides) +
                                  b * math.sin(2 * math.pi * (k + 0.5) / sides)) * r) for k in range(sides)])
    M.grid(rows, 0, mats=mats)
    if cap0 and len(rows[0]) > 1:
        M.f(list(reversed(rows[0])), mats[0])
    if cap1 and len(rows[-1]) > 1:
        M.f(rows[-1], mats[-1])
    return rows


def catmull(points, step):
    """Resample a polyline of Vectors as a Catmull-Rom curve, about `step` apart."""
    P = [points[0] * 2 - points[1]] + list(points) + [points[-1] * 2 - points[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(1, int(round((p2 - p1).length / step)))
        for k in range(n):
            s = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(P[-2])
    return out


# --- parts ---------------------------------------------------------------------------------------

def build_shell(M, SHELL, DARK):
    """The dome shell: one continuous cap surface from crown to rim, a low foot lip, a flat bottom."""
    seg = 56
    ths = [2 * math.pi * k / seg for k in range(seg)]
    ts = [0.06, 0.13, 0.2, 0.27, 0.34, 0.41, 0.48, 0.55, 0.61, 0.67, 0.72, 0.77, 0.81, 0.85, 0.885,
          0.915, 0.94, 0.96, 0.975, 0.988]
    rows = [[M.v(S(0, 0))]]
    for t in ts:
        rows.append([M.v(S(th, t)) for th in ths])
    # Foot: the cap rolls onto a short chamfered lip standing on the ground.
    ring = lambda t, z: [M.v((DCX + DRX * t * math.cos(th), DCY + DRY * t * math.sin(th), z)) for th in ths]  # noqa: E731
    rows += [ring(0.997, Z_COLLAR), ring(1.0, Z_COLLAR - 0.12), ring(1.0, 0.0)]
    mats = [SHELL] * (len(ts)) + [SHELL, SHELL, SHELL]
    M.grid(rows, SHELL, mats=mats)
    M.f(list(reversed(rows[-1])), SHELL)  # flat underside


def petal(M, th0, th1, t0, t1, mat, h=0.1, c=0.08, gap=0.24, nu=7, nv=6):
    """An armour petal on the cap between angles th0..th1 and radii t0..t1, standing h proud, with
    c chamfered edges and a constant px gap to its neighbours (the panel line)."""
    def region(shrink):
        rows = []
        for j in range(nv):
            t = t0 + (t1 - t0) * j / (nv - 1)
            t = min(max(t, t0 + shrink / 7.5 + gap / 15), t1 - shrink / 7.5 - gap / 15)
            r = r_at((th0 + th1) / 2, t)
            g = (gap / 2 + shrink) / r
            a, b = th0 + g, th1 - g
            rows.append([(a + (b - a) * i / (nu - 1), t) for i in range(nu)])
        return rows

    def loop(grid):
        top = grid[0]
        right = [row[-1] for row in grid[1:]]
        bot = list(reversed(grid[-1][:-1]))
        left = [row[0] for row in reversed(grid[1:-1])]
        return top + right + bot + left

    def place(th, t, off):
        return S(th, t) + S_normal(th, t) * off

    top = [[M.v(place(th, t, h)) for th, t in row] for row in region(c)]
    mid_uv = loop(region(0))
    bot = [[M.v(place(th, t, -0.15)) for th, t in row] for row in region(0)]
    # top grid
    for j in range(nv - 1):
        for i in range(nu - 1):
            M.f((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), mat)
            M.f((bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1], bot[j][i]), mat)
    tl, bl = loop(top), loop(bot)
    ml = [M.v(place(th, t, h - c)) for th, t in mid_uv]
    n = len(tl)
    for i in range(n):
        k = (i + 1) % n
        M.f((tl[i], tl[k], ml[k], ml[i]), mat)
        M.f((ml[i], ml[k], bl[k], bl[i]), mat)


def build_cap_panels(M, SHELL):
    """Eight armour panels over the dome's flanks, flush with the shell (they stand 0.1 px proud of
    it, so the gaps read as engraved seams, not terraces); the crown round the eye stays smooth."""
    off2 = math.radians(-8)
    for k in range(8):
        a = off2 + 2 * math.pi * k / 8
        petal(M, a, a + 2 * math.pi / 8, 0.46, 0.93, SHELL, nu=7, nv=9)


def build_bolts(M, SHELL):
    """Hex bolt heads round the collar band."""
    n = 18
    for k in range(n):
        th = 2 * math.pi * (k + 0.5) / n
        if math.radians(100) < th < math.radians(182):
            continue  # under the vent cowl
        t = 0.965
        p = S(th, t)
        nrm = S_normal(th, t)
        lathe(M, p, nrm, [(0.3, -0.25), (0.3, 0.12), (0.2, 0.22), (0, 0.22)], 6, [SHELL] * 3)


def dome_height_ext(x, y):
    """The dome's surface height, carried on past the footprint as a short fall to the ground."""
    t = math.hypot((x - DCX) / DRX, (y - DCY) / DRY)
    return cap_z(t) if t <= 1 else max(0.0, Z_COLLAR - (t - 1) * 5.0)


def smax(a, b, k=0.6):
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k * 0.25


def build_hatch(M, SHELL, SEAM, LID, BOLT):
    """A closed hatch in the crown, where the turret has its eye: every ring follows the dome's own
    surface (offset along z). The dome's low chamfered lip, a dark seam gap, a slightly domed lid split
    into two leaves, a hinge block on the upper left, six bolt heads and a grab boss in the middle."""
    x, y = EYE
    sides = 28
    # (radius px, height above the dome surface, material of the band from this ring inwards)
    prof = [(3.0, -0.9, SHELL), (3.0, -0.05, SHELL), (2.85, 0.22, SHELL), (2.6, 0.32, SHELL),
            (2.42, 0.26, SHELL), (2.3, -0.08, SEAM), (2.12, -0.12, SEAM), (2.02, 0.02, LID),
            (1.9, 0.14, LID), (1.5, 0.2, LID), (0.9, 0.26, LID), (0.0, 0.29, LID)]
    rows = []
    for r, off, _m in prof:
        if r < 1e-6:
            rows.append([M.v((x, y, dome_height_at(x, y) + off))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            ring.append(M.v((px, py, dome_height_at(px, py) + off)))
        rows.append(ring)
    bot = M.v((x, y, dome_height_at(x, y) - 0.9))
    M.grid(rows, SHELL, mats=[m for _r, _o, m in prof[:-1]])
    for k in range(sides):
        j = (k + 1) % sides
        M.f((rows[0][j], rows[0][k], bot), SHELL)
    # the split between the two leaves: a thin dark strip lying on the lid, across it (upper right to lower left)
    a = math.radians(-35)
    u = Vector((math.cos(a), math.sin(a), 0))
    w = Vector((-u.y, u.x, 0))
    pts = []
    for k in range(9):
        s = -1.95 + 3.9 * k / 8
        p = Vector((x, y, 0)) + u * s
        r = abs(s)
        pts.append(p + Vector((0, 0, dome_height_at(p.x, p.y) + (0.29 - 0.15 * (r / 1.9) ** 2) + 0.015)))
    for k in range(8):
        p0, p1 = pts[k], pts[k + 1]
        q = [p0 + w * 0.09, p1 + w * 0.09, p1 - w * 0.09, p0 - w * 0.09]
        M.f([M.v(v) for v in q], SEAM)
    # grab boss: a short turned knob in the middle, a ring of six bolt heads on the lid's rim
    c = Vector((x, y, dome_height_at(x, y) + 0.29))
    lathe(M, c - Vector((0, 0, 0.2)), (0, 0, 1), [(0.62, 0.0), (0.62, 0.32), (0.5, 0.45), (0.0, 0.45)], 12,
          [LID, LID, LID])
    for k in range(6):
        th = 2 * math.pi * (k + 0.25) / 6
        px, py = x + 1.62 * math.cos(th), y + 1.62 * math.sin(th)
        p = Vector((px, py, dome_height_at(px, py) + 0.2))
        lathe(M, p, (0, 0, 1), [(0.22, -0.2), (0.22, 0.1), (0.14, 0.18), (0, 0.18)], 6, [BOLT] * 3)
    # hinge block on the upper-left edge of the lid: a barrel between two lugs
    th = math.radians(215)
    hp = Vector((x + 2.15 * math.cos(th), y + 2.15 * math.sin(th), 0))
    hp.z = dome_height_at(hp.x, hp.y) + 0.28
    tang = Vector((-math.sin(th), math.cos(th), 0))
    sweep(M, [hp - tang * 0.85, hp + tang * 0.85], [0.26, 0.26], 8, [SEAM])
    for sgn in (-1, 1):
        lp = hp + tang * (0.55 * sgn)
        lathe(M, lp, tang, [(0.34, -0.14), (0.34, 0.14)], 8, [SHELL])


def build_vent(M, LIP, RIM, GLOW, HOT):
    """The glowing vent curving down the lower-left flank along the rim and over the foot: a chamfered
    cowl ring (113) that stands on the dome (or, past the foot, on a floor 1 px up), round a sunken
    grille: a rim (115), the glow (117) and a hot core (121), crossed by three slats."""
    cl = catmull([Vector((cx - 12, cy - 14, 0)) for cx, cy in VENT], 0.6)
    n = len(cl)
    tans = [(cl[min(i + 1, n - 1)] - cl[max(i - 1, 0)]).normalized() for i in range(n)]
    nrms = [Vector((-t.y, t.x, 0)) for t in tans]

    def loop(w):
        pts = [cl[i] + nrms[i] * w for i in range(n)]
        cap = 7
        t, nn = tans[-1], nrms[-1]
        for k in range(1, cap):
            a = math.pi * k / cap
            pts.append(cl[-1] + (nn * math.cos(a) + t * math.sin(a)) * w)
        pts += [cl[i] - nrms[i] * w for i in range(n - 1, -1, -1)]
        t, nn = tans[0], nrms[0]
        for k in range(1, cap):
            a = math.pi * k / cap
            pts.append(cl[0] + (-nn * math.cos(a) - t * math.sin(a)) * w)
        return pts

    def hz(p):
        return smax(dome_height_ext(p.x, p.y), 1.0)

    # (inset px, height above hz, material of the band from this ring inwards)
    prof = [(0.0, None, LIP), (0.0, 0.25, LIP), (0.08, 0.62, LIP), (0.2, 0.72, LIP), (0.3, 0.64, LIP),
            (0.36, 0.42, LIP), (0.8, 0.36, RIM), (0.93, 0.32, GLOW), (VENT_HW - 0.12, 0.3, GLOW)]
    rows = []
    for d, off, _m in prof:
        ring = []
        for p in loop(VENT_HW - d):
            z = max(0.0, hz(p) - 1.3) if off is None else hz(p) + off
            ring.append(M.v((p.x, p.y, z)))
        rows.append(ring)
    M.grid(rows, LIP, mats=[m for _d, _o, m in prof[:-1]])
    M.f(list(reversed(rows[0])), LIP)
    M.f(rows[-1], GLOW)
    # hot core: a long lozenge sunk in the middle of the slot (the sprite's brightest pixels, rows 15-17)
    a, b = 0.32, 0.72
    i0, i1 = int(a * (n - 1)), int(b * (n - 1))
    pts = [cl[i] + Vector((0, 0, hz(cl[i]) + 0.22)) for i in range(i0, i1 + 1)]
    m = len(pts)
    radii = [0.4 * math.sin(math.pi * (0.15 + 0.7 * k / (m - 1))) for k in range(m)]
    rows2 = sweep(M, pts, radii, 8, [HOT] * (m - 1))
    # three slats across the slot, standing level with the grille rim
    for f in (0.22, 0.5, 0.78):
        i = int(f * (n - 1))
        p, nn = cl[i], nrms[i]
        h = hz(p) + 0.5
        ends = [p + nn * (VENT_HW - 0.35), p - nn * (VENT_HW - 0.35)]
        sweep(M, [Vector((e.x, e.y, h)) for e in ends], [0.13, 0.13], 6, [LIP])


def build_ball(M, SHELL, BALLM, DARK):
    bx, by, bz, br = BALL
    c = Vector((bx, by, bz))
    # sphere as a lathe with an equator band standing proud
    prof = [(0, -br)]
    for k in range(1, 6):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((br * math.cos(a), br * math.sin(a)))
    prof += [(br * 1.0, -0.12), (br + 0.14, -0.12), (br + 0.14, 0.12), (br * 1.0, 0.12)]
    for k in range(7, 12):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((br * math.cos(a), br * math.sin(a)))
    prof.append((0, br))
    mats = [BALLM] * 5 + [DARK, DARK, DARK, DARK] + [BALLM] * 6
    lathe(M, c, (0.25, -0.3, 1.0), prof, 14, mats[:len(prof) - 1])
    # arm from the dome's foot to the ball, with a clamp collar at its root, and a post under it
    root = Vector((2.9, -7.0, Z_COLLAR + 0.2))
    sweep(M, [root, root.lerp(c, 0.5), c], [0.52, 0.5, 0.48], 8, [SHELL, SHELL])
    rc = root.lerp(c, 0.18)
    d = (c - root).normalized()
    lathe(M, rc, d, [(0.72, -0.3), (0.72, 0.3)], 8, [DARK])
    sweep(M, [Vector((bx, by, -0.1)), Vector((bx, by, bz - 0.6))], [0.42, 0.42], 8, [DARK])


def build_barrel(M, BARRELM, DARK, BORE):
    pts = catmull([Vector(p) for p in BARREL], 0.5)
    n = len(pts)
    sweep(M, pts, [BR] * n, 12, [BARRELM] * (n - 1))
    fr = frames_along(pts)
    # length along the barrel
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + (b - a).length)
    L = s[-1]

    def at(d):
        for i in range(n - 1):
            if s[i + 1] >= d:
                f = (d - s[i]) / (s[i + 1] - s[i])
                return pts[i].lerp(pts[i + 1], f), fr[i][0]
        return pts[-1], fr[-1][0]

    # mount collar where it leaves the dome (two steps, chamfered)
    p, t = at(1.0)
    lathe(M, p, t, [(BR + 0.2, -1.6), (BR + 0.55, -1.2), (BR + 0.55, 0.15), (BR + 0.3, 0.45),
                    (BR + 0.3, 0.75), (BR + 0.08, 0.9)], 12, [DARK, DARK, DARK, DARK, DARK])
    # a clamp band on the bend
    p, t = at(L * 0.5)
    lathe(M, p, t, [(BR + 0.05, -0.4), (BR + 0.22, -0.28), (BR + 0.22, 0.28), (BR + 0.05, 0.4)], 12,
          [DARK, DARK, DARK])
    # muzzle sleeve with a chamfered lip and a dark bore
    p, t = at(L - 1.25)
    lathe(M, p, t, [(BR - 0.05, -0.2), (BR + 0.18, 0.0), (BR + 0.18, 1.05), (BR + 0.02, 1.27),
                    (0.62, 1.27), (0.62, 0.9), (0, 0.9)], 12,
          [DARK, DARK, DARK, DARK, BORE, BORE])


def finish(M, mats, coll, name):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 0), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the y reflection flips winding
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj


def build(sprite, coll):
    pal = lambda i, tag="", **kw: common.palette_material(sprite, i, TAG + tag, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.2, roughness=0.32),                        # 0 dome shell (region median 24), glossy
        pal(17, metallic=0.4, roughness=0.5),                         # 1 dark collars, clamps, hatch seam
        pal(21, metallic=0.25, roughness=0.42),                       # 2 hatch lid (region median 21)
        pal(25, metallic=0.2, roughness=0.4),                         # 3 sensor ball, bolt heads (median 25)
        pal(22, metallic=0.35, roughness=0.36),                       # 4 barrel (as newshf-39)
        pal(16, metallic=0.2, roughness=0.7),                         # 5 bore
        common.palette_material(sprite, 113, TAG + "-cowl", metallic=0.3, roughness=0.45,
                                emission_strength=0.3),               # 6 vent cowl (region median 113)
        common.palette_material(sprite, 115, TAG + "-rim", emission_strength=0.6, frames={129: 116}),  # 7
        common.palette_material(sprite, 117, TAG + "-glow", emission_strength=1.6, frames={129: 121}),  # 8
        common.palette_material(sprite, 121, TAG + "-hot", emission_strength=3.0, frames={129: 123}),  # 9
    ]
    SHELL, DARK, LID, BALLM, BARRELM, BORE, COWL, RIM, GLOW, HOT = range(10)
    M = Mesh()
    build_shell(M, SHELL, DARK)
    build_cap_panels(M, SHELL)
    build_bolts(M, SHELL)
    build_hatch(M, SHELL, DARK, LID, BALLM)
    build_vent(M, COWL, RIM, GLOW, HOT)
    build_ball(M, SHELL, BALLM, DARK)
    build_barrel(M, BARRELM, DARK, BORE)
    return finish(M, mats, coll, NAME)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = common.outline_shell(obj, coll)
    obj.data.calc_loop_triangles()
    print("triangles", len(obj.data.loop_triangles), "shell", len(shell.data.polygons))
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
