"""The glossy rounded wall block of newshm.shp (frames 1, 15, 17, 53): shared by newshm-1, -15,
-17 and -53 so the wall (assembly-newshm-1) reads as one cast product line; newshm-55 and the
chevron block newshm-153 build on it too (the older lib_b078 is gone).

- Plan: a superellipse (rounded rectangle whose corners follow the sprite's 5-3-2-1-1-0 staircase)
  filling the sprite's inner mask (22 x 26 px inside the 1 px ink ring the game draws).
- Section: one enamelled cast shell. Short walls; a chamfered, filleted shoulder on the north, west
  and east (the sprite's lit north-west rim and dark east rim are light on that shoulder); a flat top;
  the long south roll over the sprite's darker lower third. That roll takes the sprite's own darker
  indices by plan row (shell -1 / -2 / -3, e.g. 70 / 69 / 68), cut along straight plan lines and a
  little rougher: under the camera-side sun no slope that deep can fall into shade, and lit in the
  shell colour it read as a bright cushion round a recessed top (demo-compare #13).
- Machined detail, kept fine because the sprite shows none: a parting groove round the base, a dark
  steel foot plate (the shadow gap), recessed lifting sockets in the walls, a barely-there seam
  round the foot of the raised top, two low bolt domes set square to the north shoulder.
- Emblems sit on the flat top: -15 a raised satin-gold S and bar, -17 a raised octagonal bezel
  with a faceted glowing gem, -53 two glowing red strokes and a core.

Colour: the shell takes the sprite's flat-top palette index (71 / 39 / 249 / 87), emblems theirs
(125, 250 + 155, 119 + 120). Satin enamel. Texture: AO/roughness bake only (usp_talon.bake_maps),
no concept projection. Outline shell (D51). Underside: the flat closed foot plate, nothing more.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
PX = 1 / 12

# --- block dimensions (sprite px; x right, y north, z up; origin = sprite centre) ---------------
HX, HY = 11.0, 13.0       # inner mask half extents (22 x 26 px)
NEXP = 3.4                # superellipse exponent: corners follow the sprite staircase
H = 8.4                   # flat top height
FOOT_IN, FOOT_Z = 0.55, 0.9   # dark foot plate: inset and height (shadow gap under the shell)
# Per side section, (inset d from that side's edge, z) px: the wall top P1 and the top edge P2,
# joined by a straight chamfer facet, each corner rounded by a fillet (r1 at P1, r2 at P2).
# N / W / E: a chamfered shoulder (the sprite's lit north-west band, cols 2-4 / rows 1-3, and its
# dark east band, cols 20-21). S: the long front facet (rows 17-26: 70 -> a flat 68 -> 66 at the
# bottom bend), its top edge on row 16.5 where the sprite's flat top ends.
PROF = {
    "n": dict(p1=(0.0, 6.0), p2=(2.5, None), r1=1.1, r2=1.3),
    "w": dict(p1=(0.0, 5.8), p2=(3.1, None), r1=1.2, r2=1.5),
    "e": dict(p1=(0.0, 5.8), p2=(2.7, None), r1=1.2, r2=1.4),
    "s": dict(p1=(0.0, 3.3), p2=(9.0, None), r1=2.4, r2=3.6),
}
SEG = (5, 2, 6)   # samples on the bottom fillet, along the facet (interior), on the top fillet
GROOVE = (1.45, 1.8, 0.38)    # parting groove: z0, z1, depth
SEAM = (0.2, 0.5, 0.012)  # a soft, barely-there seam at the foot of the top plateau: gap from the top edge, width, depth (px)
BOLTS = ((-6.4, 1.9), (6.4, 1.9))   # flush bolts on the north shoulder: x, inset from the north edge (px)
BOLT_R, BOLT_UP = 0.34, 0.04        # bolt head radius and height over the shoulder (px): a flush, soft dot
# The south roll takes the sprite's darker indices, shell -1 / -2 / -3 (71 -> 70 -> 69 -> 68 on
# newshm-1), by plan position: rows 17-18 / 18-19 / 20 on. Under the camera-side sun no section
# with a top-down footprint this deep can fall into shade (the slope would need ~70 deg), so the
# bottom third is darker by its colour, as in the sprite (demo-compare #13).
SOUTH_BANDS = ((-4.0, 1), (-5.0, 2), (-6.0, 3))   # (below plan y px, palette steps darker than the shell)
NPTS = 96                    # points per ring

VARIANTS = {
    #            shell  foot
    "newshm-1": (71, 66),
    "newshm-15": (39, 34),
    "newshm-17": (249, 244),
    "newshm-53": (87, 82),
}


def P(c, r):
    """Sprite pixel centre (col, row) to block px (x, y)."""
    return c + 0.5 - 12, 14 - (r + 0.5)


# --- profile -----------------------------------------------------------------------------------

def _fillet(a, b, c, r, n):
    """n points of a circular fillet of radius r at corner b of the polyline a-b-c."""
    import math as m
    u = (a[0] - b[0], a[1] - b[1]); lu = m.hypot(*u); u = (u[0] / lu, u[1] / lu)
    v = (c[0] - b[0], c[1] - b[1]); lv = m.hypot(*v); v = (v[0] / lv, v[1] / lv)
    ang = m.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))
    t = r / m.tan(ang / 2)
    p0 = (b[0] + u[0] * t, b[1] + u[1] * t)
    p1 = (b[0] + v[0] * t, b[1] + v[1] * t)
    bis = (u[0] + v[0], u[1] + v[1]); lb = m.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
    ctr = (b[0] + bis[0] * r / m.sin(ang / 2), b[1] + bis[1] * r / m.sin(ang / 2))
    a0 = m.atan2(p0[1] - ctr[1], p0[0] - ctr[0]); a1 = m.atan2(p1[1] - ctr[1], p1[0] - ctr[0])
    while a1 - a0 > m.pi: a1 -= 2 * m.pi
    while a0 - a1 > m.pi: a1 += 2 * m.pi
    return [(ctr[0] + r * m.cos(a0 + (a1 - a0) * i / (n - 1)), ctr[1] + r * m.sin(a0 + (a1 - a0) * i / (n - 1)))
            for i in range(n)]


def profile(side):
    """The side's section as a list of (d, z), from the wall top region to the flat top; the same
    count for every side (ring k of every side matches: fillet / facet / fillet)."""
    pr = PROF[side]
    p1 = pr["p1"]; p2 = (pr["p2"][0], H)
    f1 = _fillet((0.0, 0.0), p1, p2, pr["r1"], SEG[0])
    f2 = _fillet(p1, p2, (p2[0] + 5, H), pr["r2"], SEG[2])
    mid = [(f1[-1][0] + (f2[0][0] - f1[-1][0]) * i / (SEG[1] + 1), f1[-1][1] + (f2[0][1] - f1[-1][1]) * i / (SEG[1] + 1))
           for i in range(1, SEG[1] + 1)]
    return f1 + mid + f2


PROFILES = {}


def z_of_inset(side, d):
    pts = PROFILES[side]
    if d <= pts[0][0]:
        return pts[0][1]
    for (d0, z0), (d1, z1) in zip(pts, pts[1:]):
        if d <= d1:
            return z0 + (z1 - z0) * (d - d0) / max(d1 - d0, 1e-9)
    return H


def surface_z(x, y):
    """Approximate shell height above (x, y) (for emblems, which sit on or near the top)."""
    return min(z_of_inset("w", x + HX), z_of_inset("e", HX - x), z_of_inset("n", HY - y), z_of_inset("s", y + HY))


# --- superellipse rings ---------------------------------------------------------------------------

def _se(t, n):
    c, s = math.cos(t), math.sin(t)
    return math.copysign(abs(c) ** (2 / n), c), math.copysign(abs(s) ** (2 / n), s)


def ring_params():
    """Parameters t giving even arc length on the base superellipse (with a point on each axis)."""
    fine = [2 * math.pi * i / 4000 for i in range(4001)]
    pts = [(HX * a, HY * b) for a, b in (_se(t, NEXP) for t in fine)]
    acc = [0.0]
    for p, q in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.dist(p, q))
    L = acc[-1]
    ts, j = [], 0
    for i in range(NPTS):
        target = L * i / NPTS
        while acc[j + 1] < target:
            j += 1
        f = (target - acc[j]) / (acc[j + 1] - acc[j])
        ts.append(fine[j] + (fine[j + 1] - fine[j]) * f)
    return ts


TS = None


def ring(iw, ie, inn, ins, scale=1.0):
    x0, x1 = -HX + iw, HX - ie
    y0, y1 = -HY + ins, HY - inn
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b = (x1 - x0) / 2 * scale, (y1 - y0) / 2 * scale
    return [(cx + a * u, cy + b * v) for u, v in (_se(t, NEXP) for t in TS)]


# --- mesh building ----------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ringv(self, pts, z):
        return [self.bm.verts.new((x, y, z)) for x, y in pts]

    def bridge(self, r0, r1, mat):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat

    def cap(self, r, mat, up=True):
        f = self.bm.faces.new(r if up else list(reversed(r)))
        f.material_index = mat
        return f


def _sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# The front facet wraps round the south corners (the sprite's front band runs the full width, and
# its west edge is dark below row 16): the south section takes over from the side sections already
# 25 deg below east / west, so the corners carry the roll instead of standing up as ears.
S_TURN, S_HALF = 28.0, 26.0


def side_weights(nx, ny):
    th = math.degrees(math.atan2(ny, nx))  # 0 east, 90 north, -90 south
    if th >= 0:  # north half: plain blend at the diagonals
        we = 1 - _sstep(25, 65, th)
        ww = _sstep(115, 155, th)
        return {"e": we, "w": ww, "n": 1 - we - ww, "s": 0.0}
    a = -th  # 0 east .. 180 west, through 90 south
    we = 1 - _sstep(S_TURN - S_HALF, S_TURN + S_HALF, a)
    ww = _sstep(180 - S_TURN - S_HALF, 180 - S_TURN + S_HALF, a)
    return {"e": we, "w": ww, "n": 0.0, "s": 1 - we - ww}


def build_shell(m, SHELL):
    for sd in PROF:
        PROFILES[sd] = profile(sd)
    base = ring(0, 0, 0, 0)
    # outward normals of the base footprint: weights for blending each side's z round the corners
    n = len(base)
    W = []
    for i in range(n):
        a, b = base[i - 1], base[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        lt = math.hypot(tx, ty)
        nx, ny = ty / lt, -tx / lt
        if nx * base[i][0] + ny * base[i][1] < 0:
            nx, ny = -nx, -ny
        W.append(side_weights(nx, ny))
    rings = []
    z_bot = FOOT_Z
    rings.append(m.ringv(ring(0.45, 0.45, 0.45, 0.45), z_bot))          # bottom, chamfered in
    rings.append(m.ringv(ring(0, 0, 0, 0), z_bot + 0.3))
    g0, g1, gd = GROOVE
    rings.append(m.ringv(ring(0, 0, 0, 0), g0))
    rings.append(m.ringv(ring(gd, gd, gd, gd), g0 + 0.07))
    rings.append(m.ringv(ring(gd, gd, gd, gd), g1 - 0.07))
    rings.append(m.ringv(ring(0, 0, 0, 0), g1))
    K = len(PROFILES["n"])
    for k in range(K):
        dd = {sd: PROFILES[sd][k][0] for sd in PROF}
        zz = {sd: PROFILES[sd][k][1] for sd in PROF}
        pts = ring(dd["w"], dd["e"], dd["n"], dd["s"])
        rings.append([m.bm.verts.new((x, y, sum(W[i][sd] * zz[sd] for sd in PROF))) for i, (x, y) in enumerate(pts)])
    for r0, r1 in zip(rings, rings[1:]):
        m.bridge(r0, r1, SHELL)
    # flat top: concentric rings to a centre fan (quads for the bake and the emblems)
    top = rings[-1]
    for v in top:
        v.co.z = H
    iw, ie, inn, ins = (PROFILES[sd][-1][0] for sd in ("w", "e", "n", "s"))
    prev = top
    g = SEAM[0]  # a fine seam round the foot of the raised top: the plateau reads as a separate cast plate
    ra = m.ringv(ring(iw + g, ie + g, inn + g, ins + g), H - SEAM[2])
    m.bridge(prev, ra, SHELL)
    rb = m.ringv(ring(iw + g + SEAM[1], ie + g + SEAM[1], inn + g + SEAM[1], ins + g + SEAM[1]), H)
    m.bridge(ra, rb, SHELL)
    prev = rb
    for sc in (0.72, 0.42):
        r = m.ringv(ring(iw, ie, inn, ins, sc), H)
        m.bridge(prev, r, SHELL)
        prev = r
    cx, cy = ((-HX + iw) + (HX - ie)) / 2, ((-HY + ins) + (HY - inn)) / 2
    c = m.bm.verts.new((cx, cy, H))
    n = len(prev)
    for i in range(n):
        m.bm.faces.new((prev[i], prev[(i + 1) % n], c)).material_index = SHELL
    m.cap(rings[0], SHELL, up=False)


def build_foot(m, FOOT):
    r0 = m.ringv(ring(FOOT_IN, FOOT_IN, FOOT_IN, FOOT_IN), 0.0)
    r1 = m.ringv(ring(FOOT_IN, FOOT_IN, FOOT_IN, FOOT_IN), FOOT_Z + 0.25)
    m.bridge(r0, r1, FOOT)
    m.cap(r0, FOOT, up=False)
    m.cap(r1, FOOT, up=True)


# --- emblems ------------------------------------------------------------------------------------------

def ribbon(m, pts_px, width, raise_, mat, sink=0.35, top_scale=0.55, smooth=True):
    """A raised strip along sprite-pixel points, conformed to the shell surface."""
    pts = [P(c, r) for c, r in pts_px]
    if smooth and len(pts) > 2:  # Chaikin twice: rounder strokes
        for _ in range(2):
            q = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                q += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25),
                      (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
            q.append(pts[-1])
            pts = q
    n = len(pts)
    hw = width / 2
    rows = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        zs = surface_z(x, y)
        row = []
        for off, z in ((hw, zs - sink), (hw * top_scale, zs + raise_), (-hw * top_scale, zs + raise_), (-hw, zs - sink)):
            row.append(m.bm.verts.new((x + nx * off, y + ny * off, z)))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(4):
            j = (k + 1) % 4
            m.bm.faces.new((r0[k], r1[k], r1[j], r0[j])).material_index = mat
    m.bm.faces.new(rows[0]).material_index = mat
    m.bm.faces.new(list(reversed(rows[-1]))).material_index = mat


def bezel(m, cx, cy, r_out, r_in, h, mat, sides=8):
    zs = surface_z(cx, cy)
    def circ(r, z):
        return m.ringv([(cx + r * math.cos(math.pi / sides + 2 * math.pi * i / sides), cy + r * math.sin(math.pi / sides + 2 * math.pi * i / sides))
                        for i in range(sides)], z)
    a = circ(r_out, zs - 0.3)
    b = circ(r_out - 0.35, zs + h)
    c = circ(r_in + 0.3, zs + h)
    d = circ(r_in, zs + h - 0.45)
    m.bridge(a, b, mat)
    m.bridge(b, c, mat)
    m.bridge(c, d, mat)
    return d, zs


def gem(m, cx, cy, r, z, h, mat, sides=8):
    """A brilliant-cut gem: girdle ring, a crown of facets, a flat table."""
    def circ(rr, zz, rot=0.5):  # flat-sided octagon, like the bezel and the sprite's gem
        return m.ringv([(cx + rr * math.cos(2 * math.pi * (i + rot) / sides), cy + rr * math.sin(2 * math.pi * (i + rot) / sides))
                        for i in range(sides)], zz)
    g0 = circ(r, z - 0.3)
    g1 = circ(r, z + 0.15)
    cr = circ(r * 0.78, z + h * 0.62, 1.0)
    tb = circ(r * 0.48, z + h)
    m.bridge(g0, g1, mat)
    # crown: triangles between the girdle and the offset ring
    for i in range(sides):
        j = (i + 1) % sides
        m.bm.faces.new((g1[i], g1[j], cr[i])).material_index = mat
        m.bm.faces.new((cr[i], g1[j], cr[j])).material_index = mat
        m.bm.faces.new((cr[i], cr[j], tb[j])).material_index = mat
        m.bm.faces.new((cr[i], tb[j], tb[i])).material_index = mat
    m.cap(tb, mat, up=True)
    m.cap(g0, mat, up=False)


def bolts(m, mat, hit=None):
    """Two small flush bolts on the north shoulder, outside where the emblems sit: low domes set
    square to the sloping shoulder, so no side of the head stands proud of it as a dark lip."""
    for bx, d in BOLTS:
        by = HY * (1 - (abs(bx) / HX) ** NEXP) ** (1 / NEXP) - d
        zs = surface_z(bx, by)
        e = 0.05
        nrm = Vector((-(surface_z(bx + e, by) - surface_z(bx - e, by)) / (2 * e),
                      -(surface_z(bx, by + e) - surface_z(bx, by - e)) / (2 * e), 1.0)).normalized()
        if hit is not None:  # the built shell's own surface point and smooth normal, when given
            zs, nrm = hit(bx, by)
        t1 = nrm.cross(Vector((0.0, 0.0, 1.0)) if abs(nrm.z) < 0.99 else Vector((1.0, 0.0, 0.0))).normalized()
        if t1.length < 0.5:
            t1 = Vector((1.0, 0.0, 0.0))
        t2 = nrm.cross(t1).normalized()
        o = Vector((bx, by, zs))
        def circ(r, h):
            return [m.bm.verts.new(o + t1 * (r * math.cos(math.pi / 8 + math.pi * i / 4)) + t2 * (r * math.sin(math.pi / 8 + math.pi * i / 4)) + nrm * h)
                    for i in range(8)]
        a, b, c = circ(BOLT_R, -0.35), circ(BOLT_R, 0.0), circ(BOLT_R * 0.6, BOLT_UP)
        m.bridge(a, b, mat)
        m.bridge(b, c, mat)
        m.cap(c, mat, up=True)


def emblem(m, variant, mats):
    if variant == "newshm-15":
        GOLD = mats["emblem"]
        # The S, from its top-right end round to its bottom-left end (sprite pixel centres).
        ribbon(m, [(14.6, 5.0), (11.5, 5.0), (9.0, 5.0), (7.3, 6.2), (6.9, 8.0), (7.3, 9.7), (9.3, 10.4), (12.0, 10.6),
                   (14.2, 11.3), (15.0, 12.6), (15.0, 14.3), (14.1, 15.6), (12.5, 16.0), (10.0, 16.0), (7.8, 16.0)],
               1.6, 0.55, GOLD)
        ribbon(m, [(11.0, 3.0), (11.0, 10.5), (11.0, 18.1)], 1.3, 0.75, GOLD, smooth=False)
    elif variant == "newshm-17":
        cx, cy = P(12.0, 10.0)
        d, zs = bezel(m, cx, cy, 4.9, 3.55, 0.75, mats["bezel"])
        gem(m, cx, cy, 3.55, zs + 0.3, 1.25, mats["gem"])
        m.cap(d, mats["bezel"], up=True)
    elif variant == "newshm-53":
        RED, CORE = mats["emblem"], mats["core"]
        ribbon(m, [(5.7, 6.2), (7.2, 5.0), (8.7, 5.4), (10.3, 7.0), (12.3, 8.8), (13.5, 10.0), (14.7, 11.0), (16.2, 12.0),
                   (17.7, 13.0), (18.8, 12.9), (19.3, 12.0)], 1.5, 0.3, RED, sink=0.25)
        ribbon(m, [(18.2, 4.0), (16.4, 5.7), (14.6, 7.0), (13.2, 8.2), (12.5, 9.3), (11.0, 10.5), (9.0, 11.5), (7.9, 12.6),
                   (7.3, 13.8), (8.2, 15.0), (9.6, 16.0), (11.2, 16.0)], 1.6, 0.32, RED, sink=0.25)
        cx, cy = P(12.5, 9.1)
        zs = surface_z(cx, cy)
        gem(m, cx, cy, 1.25, zs + 0.2, 0.55, CORE, sides=8)


# --- sockets (boolean pockets) ----------------------------------------------------------------------

SOCKETS = [  # (x0, x1, y0, y1, z0, z1): boxes cut into the walls
    (-HX - 1, -HX + 0.55, -2.2, 2.2, 2.6, 4.5),
    (HX - 0.55, HX + 1, -2.2, 2.2, 2.6, 4.5),
    (-4.2, -1.4, HY - 0.55, HY + 1, 2.6, 4.5),
    (1.4, 4.2, HY - 0.55, HY + 1, 2.6, 4.5),
]


def cut_sockets(obj, coll, DARK):
    cutters = []
    for i, (x0, x1, y0, y1, z0, z1) in enumerate(SOCKETS):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x = (x0 + x1) / 2 + v.co.x * (x1 - x0)
            v.co.y = (y0 + y1) / 2 + v.co.y * (y1 - y0)
            v.co.z = (z0 + z1) / 2 + v.co.z * (z1 - z0)
        # chamfer the cutter's vertical edges a little so the pocket mouths are not knife sharp
        me = bpy.data.meshes.new(f"cut{i}")
        bm.to_mesh(me)
        bm.free()
        c = bpy.data.objects.new(f"cut{i}", me)
        coll.objects.link(c)
        cutters.append(c)
        mod = obj.modifiers.new(f"sock{i}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = c
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    me = obj.data  # the boolean appends an empty slot for the cutters (no material): drop it
    nreal = sum(1 for m in me.materials if m is not None)
    for poly in me.polygons:
        if poly.material_index >= nreal:
            poly.material_index = 0
    while len(me.materials) > nreal:
        me.materials.pop(index=len(me.materials) - 1)
    # pocket faces: inside a cutter box (grown a hair) and inside the wall's superellipse
    for poly in obj.data.polygons:
        p = poly.center
        f = ((abs(p.x) / HX) ** NEXP + (abs(p.y) / HY) ** NEXP) ** (1 / NEXP)
        if f > 0.992:
            continue
        for x0, x1, y0, y1, z0, z1 in SOCKETS:
            e = 0.002
            if x0 - e <= p.x <= x1 + e and y0 - e <= p.y <= y1 + e and z0 - e <= p.z <= z1 + e:
                poly.material_index = DARK


# --- assemble -------------------------------------------------------------------------------------------

def build(variant, sprite, coll):
    global TS
    TS = ring_params()
    shell_pal, foot_pal = VARIANTS[variant]
    pal = lambda i, tag, **kw: common.palette_material(sprite, i, f"{variant}_{tag}", **kw)  # noqa: E731
    mats = [pal(shell_pal, "enamel", metallic=0.28, roughness=0.3), pal(foot_pal, "steel", metallic=0.35, roughness=0.55)]
    idx = {"shell": 0, "dark": 1}
    if variant == "newshm-15":
        mats.append(pal(125, "gold", metallic=0.5, roughness=0.36)); idx["emblem"] = 2
    elif variant == "newshm-17":
        mats.append(pal(250, "bezel", metallic=0.45, roughness=0.32)); idx["bezel"] = 2
        mats.append(pal(155, "gem", metallic=0.0, roughness=0.06, emission_strength=0.9)); idx["gem"] = 3
    elif variant == "newshm-53":
        mats.append(pal(119, "glow", metallic=0.0, roughness=0.35, emission_strength=2.2)); idx["emblem"] = 2
        mats.append(pal(120, "core", metallic=0.0, roughness=0.3, emission_strength=3.5)); idx["core"] = 3
    for k in sorted({st for _, st in SOUTH_BANDS}):
        idx[f"south{k}"] = len(mats)
        mats.append(pal(shell_pal - k, f"enamel{k}", metallic=0.12, roughness=0.3 + 0.12 * k))

    m = Mesh()
    build_shell(m, idx["shell"])
    build_foot(m, idx["dark"])
    shell_bm = m.bm
    for y_below, _ in SOUTH_BANDS:  # cut the shell along the bands' plan lines: straight, clean colour edges
        bmesh.ops.bisect_plane(shell_bm, geom=list(shell_bm.verts) + list(shell_bm.edges) + list(shell_bm.faces),
                               plane_co=(0.0, y_below, 0.0), plane_no=(0.0, 1.0, 0.0))
    bmesh.ops.recalc_face_normals(shell_bm, faces=shell_bm.faces)
    S = Matrix.Scale(PX, 4)
    bmesh.ops.transform(shell_bm, matrix=S, verts=shell_bm.verts)
    me = bpy.data.meshes.new(variant)
    shell_bm.to_mesh(me)
    shell_bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(variant, me)
    coll.objects.link(obj)
    global SOCKETS
    SOCKETS = [tuple(v * PX for v in s) for s in SOCKETS]
    global HX, HY
    hx, hy = HX, HY
    HX, HY = hx * PX, hy * PX
    cut_sockets(obj, coll, idx["dark"])
    HX, HY = hx, hy
    for poly in obj.data.polygons:  # the south roll's darker bands (by plan y, like the sprite's rows)
        if poly.material_index != idx["shell"]:
            continue
        y = poly.center.y / PX
        for y_below, k in SOUTH_BANDS:
            if y < y_below:
                poly.material_index = idx[f"south{k}"]

    parts = [obj]
    if True:
        e = Mesh()
        from mathutils.bvhtree import BVHTree
        sv = [v.co / PX for v in obj.data.vertices]
        bvh = BVHTree.FromPolygons(sv, [tuple(p.vertices) for p in obj.data.polygons])

        def hit(x, y):
            loc, _, fi, _ = bvh.ray_cast(Vector((x, y, 30.0)), Vector((0.0, 0.0, -1.0)))
            pol = obj.data.polygons[fi]  # smooth normal: the face's vertex normals, averaged
            nrm = sum((obj.data.vertices[i].normal for i in pol.vertices), Vector()).normalized()
            return loc.z, nrm
        bolts(e, idx["shell"], hit)
        if variant != "newshm-1":
            emblem(e, variant, idx)
        bmesh.ops.recalc_face_normals(e.bm, faces=e.bm.faces)
        bmesh.ops.transform(e.bm, matrix=S, verts=e.bm.verts)
        me2 = bpy.data.meshes.new(variant + "_emblem")
        e.bm.to_mesh(me2)
        e.bm.free()
        for mt in mats:
            me2.materials.append(mt)
        o2 = bpy.data.objects.new(variant + "_emblem", me2)
        coll.objects.link(o2)
        parts.append(o2)
    for o in parts:
        o.data.shade_smooth()
        o.data.set_sharp_from_angle(angle=math.radians(38))
    return parts, mats


def main(variant):
    """Build, bake, add the outline shell and export public/models/enemies/<variant>.glb."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, variant)
    coll = common.reset_collection(variant)
    parts, mats = build(variant, sprite, coll)
    obj = T.join(parts, variant)
    closed = obj.copy()
    closed.data = obj.data.copy()
    closed.modifiers.clear()
    coll.objects.link(closed)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{variant}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(i for i, mt in enumerate(mats) if not any(k in mt.name for k in ("_gem", "_glow", "_core")))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{variant}_bake_"), size=1024, samples=96)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{variant}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, voxel=0.014, faces=1500, smooth=8)
    shell.name = shell.data.name = f"{variant}_outline"
    bpy.data.objects.remove(closed)
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{variant}", sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        out = argv[argv.index("--preview") + 1]
        common.render_preview([obj, shell], out, ROOT / "reference" / "models" / variant / sprite["frames"][0]["image"],
                              size=sprite["frames"][0]["size"])
