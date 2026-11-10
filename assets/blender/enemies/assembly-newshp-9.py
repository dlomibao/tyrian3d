"""Cable derrick over a grey pad (newshp.shp frames 9, 11 / 1, 3 / 39, 41: six 2x2 pieces, two
across and three down = one 48 x 84 px object; the drill string in newshp-1/3 works up and down
the pit over frames 1|3, 5|7, 81|83, 43|45, 77|79). silhouette and readability from the
small tilted game camera first, then detail.

At game size the sprite reads as five masses, each given its own height band and a clean,
chamfered edge so they separate under the tilted camera:
  1. the brass T-beam crown (top, 8.3 -> 9.6 px), the brightest, flattest mass, its stem riser and
     the sheave housing with a dark sheave slot (the sprite's 16/162 at cols 24-25, rows 5-6);
  2. the dark mast: a plated box leaning back from the pit (row 41, z 2.7) to the crown (row 7,
     z 9.1), lit chords down its edges, battens, girts, braces, a grey fairlead sheave east and the
     grey jib pipe ("hook") curling from the crown's west end down to the working platform;
  3. the legs, the two stiff legs (stays) and the drill string: round tubes with collars, the gaps
     between them kept open as the sprite's (cols 16, 21, 25-26, 31 at rows 24-27);
  4. the pad: a filleted grey slab, its top the sprite's own plates, the brass well collar, two
     brass guide shoes either side of the 4 px drill string, and six brass deadmen with shackle
     eyes, wire guys from the mast to them;
  5. the stone floor: kerb blocks west and east, a drain slot, the cable-trench grate south.

The sprite is authoritative (D52, D74): plan outlines follow the inner edge of its ink
(tools/sprite_mask), each part takes the palette index the sprite uses there (luma-trimmed median,
blueprint region table); lit pixels (the beam's west end, the lit leg, the pad's west edge) are
sheen on round or chamfered edges, not extra parts.

Coordinates in sprite px: x = col - 24 (east), y = 42 - row (north), z up; Blender = px / 12
(assembly centred on the origin, as lib_b073.Grid / run_assembly).

    blender --background --factory-startup --python assets/blender/enemies/assembly-newshp-9.py -- [--no-bake] [--out review.glb]

Exports each piece named as its game model at its assembly place, its
"<piece>_outline" shell (tyrian_outline), and the drill string's lower end per frame pair as
"<piece>-drill-<frame>" parts tagged with tyrian_frames (frame_part), each with its own shell.
Underside: closed and flat, no detail.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402,F401  (bake_maps is copied below with wider island gaps)

NAME = "assembly-newshp-9"
PIECES = [["newshp-9", "newshp-11"], ["newshp-1", "newshp-3"], ["newshp-39", "newshp-41"]]
W, H = 48, 84
# drill frame pairs (newshp-1 frame, newshp-3 frame) and the row of the bit's tip on them
PAIRS = [(1, 3, 39.6), (5, 7, 42.0), (81, 83, 45.3), (43, 45, 46.9), (77, 79, 47.6)]

ZF, ZP, ZR, ZT = 0.36, 1.44, 2.5, 10.9     # floor top, pad top, collar top, crown beam top


def zl(r):
    """The derrick's lean line: row 41.5 (feet) z 2.7 -> row 6.5 z 10.4."""
    return 2.7 + (41.5 - r) * (7.7 / 35.0)


def X(c):
    return c - 24.0


def Y(r):
    return 42.0 - r


def P3(c, r, z):
    return (X(c), Y(r), z)


# --- materials ---------------------------------------------------------------------------------------

FIN = {"metal": (0.45, 0.45), "brass": (0.5, 0.4), "stone": (0.05, 0.85), "dark": (0.3, 0.6),
       "rope": (0.35, 0.55)}


class Mats:
    def __init__(self, sprite, tag):
        self.sprite, self.tag, self.list, self.keys = sprite, tag, [], {}

    def __call__(self, pal, fin="metal"):
        k = (pal, fin)
        if k not in self.keys:
            me, ro = FIN[fin]
            self.keys[k] = len(self.list)
            self.list.append(common.palette_material(self.sprite, pal, f"{self.tag}_{fin}", metallic=me,
                                                     roughness=ro))
        return self.keys[k]


# --- mesh building (px space) ------------------------------------------------------------------------

class Model:
    def __init__(self):
        self.bm = bmesh.new()

    def add(self, b, mat, recalc=True):
        if recalc:
            bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        vmap = {v: self.bm.verts.new(v.co) for v in b.verts}
        for f in b.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mat(f) if callable(mat) else mat
        b.free()

    def quad(self, pts, mat):
        vs = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(vs)
        f.material_index = mat


def mk_loft(rings, cap0=True, cap1=True):
    b = bmesh.new()
    vr = [[b.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for r0, r1 in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            try:
                b.faces.new((r0[i], r0[j], r1[j], r1[i]))
            except ValueError:
                pass
    if cap0:
        b.faces.new(list(reversed(vr[0])))
    if cap1:
        b.faces.new(vr[-1])
    return b


def loft(M, rings, mat, cap0=True, cap1=True):
    M.add(mk_loft(rings, cap0, cap1), mat)


def pchip(xs, ys):
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
        i = 0
        while i < n - 2 and x > xs[i + 1]:
            i += 1
        t = min(1.0, max(0.0, (x - xs[i]) / h[i]))
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1]
                + (t3 - t2) * h[i] * m[i + 1])
    return f


def rrect(x0, y0, x1, y1, r=0.25, seg=3):
    r = max(0.01, min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    P = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            P.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return P


def offset_poly(P, dist):
    """Offset a convex CCW polygon inward, edge i by dist(outward normal of edge i)."""
    n = len(P)
    L = []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1.0
        tx, ty = tx / ln, ty / ln
        nx, ny = ty, -tx
        dd = dist(nx, ny)
        L.append(((a[0] - nx * dd, a[1] - ny * dd), (tx, ty)))
    out = []
    for i in range(n):
        (ap, at), (bp, bt) = L[i - 1], L[i]
        den = at[0] * bt[1] - at[1] * bt[0]
        if abs(den) < 1e-6:
            out.append(bp)
            continue
        s = ((bp[0] - ap[0]) * bt[1] - (bp[1] - ap[1]) * bt[0]) / den
        out.append((ap[0] + at[0] * s, ap[1] + at[1] * s))
    return out


SIDES = {"w": (-1, 0), "e": (1, 0), "n": (0, 1), "s": (0, -1)}


def slab(M, mat, poly, z0, z1, ch=0.3, fil=None, slope=None, chb=0.0):
    """Extrude a convex CCW polygon z0..z1; top edges chamfered `ch` (or filleted per side `fil`),
    faces leaning back `slope` px per side over their height; bottom edge chamfer `chb`."""
    fil, slope = fil or {}, slope or {}
    h = z1 - z0
    rmax = max([ch, 0.01] + list(fil.values()))
    ns = 6 if fil else 1
    zs = ([z0, z0 + chb] if chb > 0 else [z0]) + [z1 - rmax * (1 - j / ns) for j in range(ns + 1)]

    def ring(z):
        def dist(nx, ny):
            d = 0.0
            for k, (sx, sy) in SIDES.items():
                w = max(0.0, nx * sx + ny * sy)
                if w <= 0:
                    continue
                r = fil.get(k, ch)
                t = max(0.0, (z - (z1 - r)) / r) if r > 0 else 0.0
                prof = r * (1 - math.sqrt(max(0.0, 1 - t * t))) if k in fil else r * t
                if chb > 0 and z < z0 + chb:
                    prof = max(prof, chb - (z - z0))
                d = max(d, w * (prof + slope.get(k, 0.0) * (z - z0) / h))
            return d
        return [(x, y, z) for x, y in offset_poly(poly, dist)]
    loft(M, [ring(z) for z in zs], mat)


def box(M, mat, c0, r0, c1, r1, z0, z1, ch=0.3, r=0.25, seg=2, fil=None, slope=None, chb=0.0):
    slab(M, mat, rrect(X(c0), Y(r1), X(c1), Y(r0), r, seg), z0, z1, ch=ch, fil=fil, slope=slope, chb=chb)


def plan_loft(M, mat, poly, levels):
    rings = []
    for L in levels:
        def dist(nx, ny, L=L):
            d = 0.0
            for k, (sx, sy) in SIDES.items():
                w = max(0.0, nx * sx + ny * sy)
                if w > 1e-6:
                    d = max(d, w * L.get(k, 0.0))
            return d
        rings.append([(x, y, L["z"]) for x, y in offset_poly(poly, dist)])
    loft(M, rings, mat)


def clip_x(poly, x0, x1):
    """Clip a polygon to x0 <= x <= x1 (Sutherland-Hodgman)."""
    def clip(P, keep, inter):
        out = []
        for i in range(len(P)):
            a, b = P[i - 1], P[i]
            if keep(b):
                if not keep(a):
                    out.append(inter(a, b))
                out.append(b)
            elif keep(a):
                out.append(inter(a, b))
        return out

    def at(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))
    P = clip(poly, lambda p: p[0] >= x0, at(x0))
    return clip(P, lambda p: p[0] <= x1, at(x1)) if P else P


def station_loft(M, mat, st, ch=0.4, n=24):
    """Loft north-south through chamfered rectangular sections st = [(row, col_l, col_r, z_top, z_bot)]."""
    rows = [s[0] for s in st]
    f = [pchip(rows, [s[k] for s in st]) for k in (1, 2, 3, 4)]
    rings = []
    for j in range(n + 1):
        r = rows[0] + (rows[-1] - rows[0]) * j / n
        xl, xr, zt, zb = (g(r) for g in f)
        y = Y(r)
        c = min(ch, (xr - xl) / 3)
        rings.append([(X(xl), y, zb), (X(xr), y, zb), (X(xr), y, zt - c), (X(xr) - c, y, zt), (X(xl) + c, y, zt),
                      (X(xl), y, zt - c)])
    loft(M, rings, mat)


def sweep(M, mat, pts, r, n=12, closed=False, caps=True):
    """Round tube along a 3D polyline, parallel-transport frames; r: number or one per point."""
    P = [Vector(p) for p in pts]
    m = len(P)
    rr = r if isinstance(r, (list, tuple)) else [r] * m
    tans = []
    for i in range(m):
        a = P[(i - 1) % m] if closed else P[max(0, i - 1)]
        b = P[(i + 1) % m] if closed else P[min(m - 1, i + 1)]
        tans.append((b - a).normalized())
    t0 = tans[0]
    up = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    e1 = t0.cross(up).normalized()
    rings = []
    for i in range(m):
        if i:
            q = tans[i - 1].rotation_difference(tans[i])
            e1 = q @ e1
            e1 = (e1 - tans[i] * e1.dot(tans[i])).normalized()
        e2 = tans[i].cross(e1)
        rings.append([tuple(P[i] + rr[i] * (math.cos(2 * math.pi * (k + 0.5) / n) * e1 +
                                            math.sin(2 * math.pi * (k + 0.5) / n) * e2)) for k in range(n)])
    if closed:
        rings.append(rings[0])
        b = mk_loft(rings, False, False)
        bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)
        M.add(b, mat)
    else:
        loft(M, rings, mat, caps, caps)


def tube(M, mat, a, b, r, n=12):
    sweep(M, mat, [a, b], r, n=n)


def disc(M, mat, c, axis, r, h, n=20):
    ax = Vector(axis).normalized()
    c = Vector(c)
    tube(M, mat, tuple(c - ax * h / 2), tuple(c + ax * h / 2), r, n=n)


def fillet(pts, f, seg=6):
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p = Vector(pts[i])
        a = (Vector(pts[i - 1]) - p).normalized()
        b = (Vector(pts[i + 1]) - p).normalized()
        A, B = p + a * f, p + b * f
        for s in range(seg + 1):
            t = s / seg
            out.append(tuple((1 - t) ** 2 * A + 2 * t * (1 - t) * p + t * t * B))
    out.append(pts[-1])
    return out


# --- the floor and the pad ---------------------------------------------------------------------------

PC, PRX, PRY = (23.5, 46.6), 5.2, 4.6       # the well collar's centre (col, row) and radii


def build_floor(M, mt):
    """Stone floor round the pad: one plate in its median grey, kerb blocks west and east with
    modelled joints, a ribbed tread band along the south edge (the sprite's 4 px 7-6-2-2 rhythm
    in rows 80-83) and the cable-trench grate. Plain materials: the sprite's mottling is lighting."""
    box(M, mt(5, "stone"), 0, 28.0, 48, 84, 0, ZF, ch=0.05, r=0.05)
    # west kerb blocks (cols 0-2) and east kerb (cols 44-47), joints between them
    for r0, r1 in ((28.02, 37.8), (38.2, 49.8), (50.2, 59.8), (60.2, 70.0)):
        box(M, mt(6, "stone"), 0.05, r0, 2.95, r1, 0.0, ZF + 0.7, ch=0.25, r=0.2)
    for r0, r1 in ((28.02, 41.8), (42.2, 55.8), (56.2, 70.0)):
        box(M, mt(2, "stone"), 44.1, r0, 47.95, r1, 0.0, ZF + 0.5, ch=0.2, r=0.2)
    # south tread band: raised ribs on a dark bed
    box(M, mt(3, "stone"), 0.0, 79.4, 48.0, 84.0, 0.0, ZF + 0.08, ch=0.04, r=0.04)
    for c in range(0, 48, 4):
        box(M, mt(7, "stone"), c + 0.15, 79.6, c + 1.85, 83.95, 0.0, ZF + 0.32, ch=0.12, r=0.1)
    # cable-trench grate south of the pad (rows 71-78): angle-iron frame and cross bars
    gm = mt(4, "metal")
    box(M, mt(8, "metal"), 11.6, 70.25, 44.0, 71.0, ZF - 0.02, ZF + 0.38, ch=0.12, r=0.1)
    box(M, gm, 11.6, 78.6, 44.0, 79.3, ZF - 0.02, ZF + 0.3, ch=0.1, r=0.1)
    dk = mt(2, "dark")
    box(M, dk, 12.0, 71.0, 44.0, 78.6, ZF - 0.02, ZF + 0.02, ch=0.02, r=0.02)   # dark trench floor
    for c in range(16, 41, 4):
        box(M, gm, c + 0.05, 70.9, c + 0.95, 78.7, ZF - 0.02, ZF + 0.42, ch=0.12, r=0.05)
    for r in (73.2, 75.8):   # cross rails: the cells read as deep recesses
        box(M, gm, 12.0, r, 44.0, r + 0.55, ZF - 0.02, ZF + 0.3, ch=0.08, r=0.05)
    for c in (12, 44):   # frame ends
        box(M, gm, c - 0.45, 70.6, c + 0.0, 79.0, ZF - 0.02, ZF + 0.42, ch=0.1, r=0.05)


# pad plates (col0, row0, col1, row1, fillets on the pad's outer edges); 0.3 px joints between them
PAD_X = (3.1, 11.85, 35.55, 42.9)
PAD_PLATES = [
    (0, [28.02, 39.4, 50.4, 56.4, 60.3, 70.3]),       # west column: joints on the sprite's dark rows
    (1, [28.02, 54.6, 70.3]),                         # centre field round the well; joint at row 55's lit edge
    (2, [28.02, 37.0, 54.4, 70.3]),                   # east column (narrowed by the trench south of row 37)
]
TRENCH = (40.3, 37.0)   # east cable trench: from this col to the pad's edge, south of this row


def build_pad(M, mt):
    """Grey pad cols 3-43 rows 28-70: a bed in the joint colour carrying chamfered plates in the
    pad's median grey (7 north and middle, 8 south), the joints between them modelled; the
    sprite's L-shaped inlay west of the well and the twin rails of the south channel as raised strips. The light diagonal bands on
    the sprite's pad are sheen and stay lighting."""
    x0, x1, y0, y1 = X(3.1), X(42.9), Y(70.3), Y(28.02)
    slab(M, mt(5, "stone"), rrect(x0, y0, x1, y1, 0.5, 3), 0.0, ZP - 0.3, ch=0.2)
    g = 0.15
    for ci, rows in PAD_PLATES:
        ca, cb = PAD_X[ci] + (g if ci else 0.0), PAD_X[ci + 1] - (g if ci < 2 else 0.0)
        for k, (ra, rb) in enumerate(zip(rows, rows[1:])):
            ra2, rb2 = ra + (g if k else 0.0), rb - (g if k < len(rows) - 2 else 0.0)
            fil = {}
            if ci == 0:
                fil["w"] = 0.9
            if k == len(rows) - 2:
                fil["s"] = 0.5
            if ci == 2 and k:
                cb = TRENCH[0] - g
            # the sprite's pad median: 7 on the north and middle plates, 8 on the south ones
            plate = mt(8 if (ra + rb) / 2 > 56.0 else 7, "stone")
            box(M, plate, ca, ra2, cb, rb2, ZP - 1.1, ZP, ch=0.18, r=0.2 if not fil else 0.5, fil=fil or None)
    # east cable trench (the sprite's dark strip, cols 40-43 rows 37-70): a dark sunk channel
    box(M, mt(2, "stone"), TRENCH[0] + 0.05, TRENCH[1] + g, 42.85, 70.25, ZP - 0.32, ZP - 0.22, ch=0.04, r=0.1)
    lit = mt(11, "stone")
    # L inlay west of the well (sprite rows 51-55, cols 5-8 light 11)
    box(M, lit, 6.9, 50.9, 8.8, 54.2, ZP - 0.05, ZP + 0.12, ch=0.08, r=0.1)
    box(M, lit, 4.9, 54.0, 8.8, 55.9, ZP - 0.05, ZP + 0.12, ch=0.08, r=0.1)
    # south channel: two rails (cols 16 and 20, rows 64-69)
    for c in (16.0, 20.0):
        box(M, mt(10, "stone"), c + 0.05, 63.6, c + 0.95, 70.25, ZP - 0.05, ZP + 0.14, ch=0.1, r=0.1)


def ell(rx, ry, z, n=32, c=PC):
    return [P3(c[0] + rx * math.cos(2 * math.pi * i / n), c[1] + ry * math.sin(2 * math.pi * i / n), z)
            for i in range(n)]


def build_well(M, mt):
    brass, dark = mt(23, "brass"), mt(1, "dark")
    # bore: a dark well floor sunk 0.3 px into the slab top and its throat wall
    loft(M, [ell(PRX - 0.55, PRY - 0.55, ZP + 0.5), ell(PRX - 0.85, PRY - 0.85, ZP + 0.2),
             ell(PRX - 0.85, PRY - 0.85, ZP + 0.03)], dark, cap0=False, cap1=True)
    # cast collar: round-section ring (sheen on its top = the sprite's 26-28)
    sweep(M, brass, ell(PRX, PRY, ZR - 0.55, n=40), 1.15, n=14, closed=True)
    # flange under the collar, bolts on it
    loft(M, [ell(PRX - 0.4, PRY - 0.4, ZP - 0.05), ell(PRX + 1.55, PRY + 1.55, ZP - 0.05),
             ell(PRX + 1.55, PRY + 1.55, ZP + 0.25), ell(PRX + 1.2, PRY + 1.2, ZP + 0.45),
             ell(PRX - 0.4, PRY - 0.4, ZP + 0.45)], mt(22, "brass"), cap0=False, cap1=False)
    for k in range(10):
        a = 2 * math.pi * (k + 0.5) / 10
        disc(M, mt(21, "brass"), P3(PC[0] + (PRX + 0.15) * math.cos(a), PC[1] + (PRY + 0.15) * math.sin(a), ZR + 0.55),
             (0, 0, 1), 0.38, 0.3, n=6)


# deadmen: (col, row) centre, width, height in px: the sprite's brown blobs (rows/cols inclusive:
# nw 33-38 / 12-16, ne 33-37 / 31-34, w 43-49 / 4-10, e 44-48 / 36-42, sw 56-62 / 10-19, se 57-61 / 29-37)
ANCH = {"nw": (14.5, 36.0, 4.8, 5.0), "ne": (33.2, 35.4, 4.2, 4.4), "w": (7.4, 46.6, 6.6, 6.4),
        "e": (39.3, 46.6, 6.2, 5.0), "sw": (15.0, 59.5, 8.8, 6.4), "se": (33.6, 59.5, 8.4, 5.2)}


def build_anchors(M, mt):
    """Cast deadmen: a rounded block with a chamfered top in the sprite's brown (25), a dark socket
    the stay drops into (the dark core of each brown crescent) and a shackle eye over it."""
    blk, eye, pin = mt(25, "brass"), mt(23, "brass"), mt(1, "dark")
    for k, (c, r, w, h) in ANCH.items():
        rad = min(w, h) / 2 - 0.3
        poly = rrect(X(c - w / 2), Y(r + h / 2), X(c + w / 2), Y(r - h / 2), rad, 4)
        plan_loft(M, blk, poly, [{"z": ZP - 0.4}, {"z": ZP + 0.6},
                                 {"z": ZP + 1.0, "w": 0.45, "e": 0.45, "n": 0.45, "s": 0.45}])
        # socket: a dark round recess cap on the block top, its rim a raised lip of the casting
        sr = min(w, h) * 0.22
        sweep(M, blk, ell(sr + 0.2, sr + 0.2, ZP + 1.05, n=20, c=(c, r)), 0.28, n=8, closed=True)
        disc(M, pin, P3(c, r, ZP + 0.98), (0, 0, 1), sr, 0.2, n=16)
        # shackle eye: an arch standing over the socket, its plane facing the derrick
        dx, dy = 23.5 - c, r - 30.0
        ln = math.hypot(dx, dy)
        dx, dy = dx / ln, dy / ln
        E = []
        for i in range(15):
            t = math.pi * i / 14
            s = (sr + 0.1) * math.cos(t)
            E.append(P3(c + dy * s, r + dx * s, ZP + 0.95 + 1.0 * math.sin(t)))
        sweep(M, eye, E, 0.4, n=8)


# --- the derrick -------------------------------------------------------------------------------------

FW, FE = (19.9, 41.6), (28.6, 41.6)          # leg feet (on the collar's north side)
TS = [(7.0, 17.2, 27.8), (8.0, 18.0, 27.3), (9.0, 18.9, 27.6), (10.5, 18.9, 28.6), (11.5, 18.2, 29.6),
      (12.5, 18.1, 30.1), (15.9, 18.0, 30.2), (16.2, 16.9, 31.1), (17.6, 16.9, 31.1), (18.2, 16.9, 32.0),
      (19.0, 16.4, 32.0), (19.5, 16.2, 31.9)]


def drill_z(r):
    """The drill string's axis height at a row (straight line from the tool joint into the pit)."""
    return 4.67 - 0.1496 * (r - 28.0)


def build_derrick(M, mt):
    steel, lit, mid, grey = mt(1, "metal"), mt(9, "metal"), mt(5, "metal"), mt(3, "metal")
    # ---- feet and legs
    for c, r in (FW, FE):
        box(M, grey, c - 1.4, r - 1.0, c + 1.4, r + 1.3, ZR - 0.5, ZR + 0.5, ch=0.2)
        disc(M, mt(2, "metal"), P3(c, r + 0.15, ZR + 0.55), (1, 0, 0), 0.55, 3.2, n=8)   # foot pin
    sweep(M, lit, [P3(FW[0], FW[1], ZR + 0.6), P3(19.5, 27.6, zl(27.6) - 0.3), P3(18.9, 25.5, zl(25.5) - 0.25),
                   P3(18.9, 24.0, zl(24) - 0.2), P3(18.8, 21.8, zl(21.8) - 0.9)],
          [1.05, 1.2, 0.95, 1.0, 1.0], n=16)
    sweep(M, mid, [P3(FE[0], FE[1], ZR + 0.6), P3(29.6, 28.0, zl(28) - 0.3), P3(29.3, 25.5, zl(25.5) - 0.35),
                   P3(29.0, 24.4, zl(24.4) - 0.4), P3(29.0, 21.0, zl(21) - 0.6)],
          [1.0, 0.95, 0.95, 0.95, 0.95], n=16)
    for c, r, z in ((19.2, 30.0, zl(30.0) - 0.3), (29.4, 30.5, zl(30.5) - 0.3)):   # leg sleeve collars
        disc(M, mt(4, "metal"), P3(c, r, z), (0, 1, 0.18), 1.35, 0.9, n=12)
    # (no cross struts between the legs: the sprite shows the pad between them, rows 29-40)
    # stiff legs (back stays) from the mast to the NW / NE deadmen
    sweep(M, mid, [P3(14.8, 22.0, zl(22) - 0.9), P3(15.0, 24.0, zl(24) - 1.2), P3(14.8, 25.3, zl(25.3) - 1.4),
                   P3(14.4, 26.5, zl(26.5) - 1.55), P3(14.6, 27.4, zl(27.4) - 1.65), P3(14.2, 34.4, ZP + 1.4)],
          [0.9, 0.9, 0.9, 1.0, 1.15, 0.9], n=10)
    sweep(M, grey, [P3(31.6, 23.2, zl(23.2) - 0.9), P3(33.4, 25.0, zl(25) - 1.2), P3(33.6, 26.2, zl(26.2) - 1.4),
                    P3(33.8, 27.4, zl(27.4) - 1.5), P3(33.3, 34.0, ZP + 1.4)], [0.8, 0.85, 0.7, 0.9, 0.85], n=10)

    # ---- the mast: plated box, chords, battens, girts, braces
    station_loft(M, steel, [(r, a, b, zl(r), zl(r) - 2.6) for r, a, b in TS], ch=0.5)
    sweep(M, mt(4, "metal"), [P3(a + 0.8, r, zl(r) + 0.15) for r, a, b in TS], 0.7, n=10)
    sweep(M, steel, [P3(b - 0.8, r, zl(r) + 0.1) for r, a, b in TS], 0.65, n=10)
    for c in (19.6, 21.6, 23.6):
        tube(M, steel, P3(c, 13.5, zl(13.5) + 0.25), P3(c, 18.6, zl(18.6) + 0.25), 0.32, n=6)
    for r in (13.0, 18.4):
        tube(M, steel, P3(18.8, r, zl(r) + 0.3), P3(28.8 if r < 15 else 30.4, r, zl(r) + 0.3), 0.3, n=6)
    for a, b in (((19.6, 18.4), (25.6, 13.2)), ((25.6, 18.4), (29.4, 13.2))):
        tube(M, steel, P3(a[0], a[1], zl(a[1]) + 0.3), P3(b[0], b[1], zl(b[1]) + 0.3), 0.24, n=6)
    # fairlead sheave on the mast's east face (grey wheel rows 9-13), rim, spokes, hub
    nl = Vector((0, -6.4 / 35.0, 1)).normalized()
    sc = Vector(P3(27.3, 12.0, zl(12) + 0.5))
    disc(M, grey, tuple(sc), nl, 2.0, 0.9, n=22)
    e1 = Vector((1, 0, 0))
    e2 = nl.cross(e1)
    sweep(M, mt(4, "metal"), [tuple(sc + nl * 0.5 + 1.75 * (math.cos(a) * e1 + math.sin(a) * e2))
                              for a in [2 * math.pi * i / 20 for i in range(20)]], 0.22, n=6, closed=True)
    disc(M, mt(5, "metal"), tuple(sc + nl * 0.55), nl, 0.8, 0.5, n=12)

    # ---- drill string, upper part (crown to the tool joint); its lower end is per frame (drill_part)
    sweep(M, mt(4, "metal"), [P3(24.0, 17.5, zl(17.5) - 1.3), P3(24.6, 20.3, zl(20.3) - 0.5), P3(23.6, 24.0, zl(24) - 0.4),
                              P3(24.0, 28.0, drill_z(28)), P3(24.0, 32.0, drill_z(32))],
          [1.0, 1.15, 1.3, 1.2, 1.85], n=12)
    tube(M, mt(6, "metal"), P3(24.0, 30.4, drill_z(30.4)), P3(24.0, 32.2, drill_z(32.2)), 2.05, n=12)   # tool joint
    # guide shoes: two cast brass blocks either side of the string at the pad's north edge
    # (sprite cols 20-21 rows 32-34, 25/24, clamped over the lit west leg; cols 26-27 rows 31-34,
    # 22/27): standing on the pad up to the string's top, a cap plate and a bolt on each
    shoe = mt(25, "brass")
    zs = drill_z(33.0) + 1.95
    for c0, r0, c1, r1, cap in ((19.95, 31.95, 22.0, 35.0, 24), (26.0, 30.95, 28.05, 35.0, 22)):
        box(M, shoe, c0, r0, c1, r1, ZP - 0.2, zs, ch=0.3, r=0.3, slope={"s": 0.4})
        box(M, mt(cap, "brass"), c0 + 0.45, r0 + 0.45, c1 - 0.45, r1 - 0.8, zs - 0.05, zs + 0.2, ch=0.08, r=0.15)
        disc(M, mt(23, "brass"), P3((c0 + c1) / 2, (r0 + r1) / 2 - 0.2, zs + 0.25), (0, 0, 1), 0.36, 0.2, n=6)

    # kelly bushing: dark guide block where the string leaves the mast (rows 19-20)
    box(M, steel, 22.5, 18.8, 25.7, 21.0, zl(20) - 1.8, zl(20) + 0.55, ch=0.3, r=0.4, slope={"s": 0.5})
    # ---- monkey board (platform), its rail, gussets, winch house and drum
    box(M, steel, 12.8, 21.55, 24.9, 23.9, zl(22) - 1.7, zl(22) - 0.6, ch=0.25, slope={"s": 0.4})
    for c in (14.5, 16.5, 18.5, 20.5, 22.5):     # tread bars across the board
        box(M, mt(2, "metal"), c - 0.25, 21.8, c + 0.25, 23.6, zl(22) - 0.75, zl(22) - 0.5, ch=0.08, r=0.05)
    tube(M, mt(7, "metal"), P3(13.4, 22.1, zl(22) - 0.1), P3(16.8, 22.1, zl(22) - 0.1), 0.45, n=8)
    slab(M, mt(2, "metal"), [(X(c), Y(r)) for c, r in ((15.2, 21.7), (20.4, 21.7), (20.4, 19.15), (16.1, 19.15), (15.2, 20.1))],
         zl(20) - 1.9, zl(20) - 0.5, ch=0.2)
    box(M, mt(2, "metal"), 16.9, 23.7, 20.9, 24.8, zl(24) - 1.6, zl(24) + 0.6, ch=0.3, r=0.5)
    house = [(X(c), Y(r)) for c, r in ((28.0, 24.5), (30.9, 24.5), (32.7, 23.3), (32.7, 21.0), (32.1, 20.3), (31.6, 19.4), (27.3, 19.4))]
    slab(M, steel, house, zl(22) - 2.2, zl(22) - 0.1, ch=0.35, slope={"s": 0.6})
    tube(M, mt(2, "metal"), P3(31.2, 20.3, zl(22) - 0.5), P3(31.2, 23.4, zl(22) - 0.5), 1.0, n=16)   # drum
    for rr in (20.3, 23.4):
        disc(M, mt(4, "metal"), P3(31.2, rr, zl(22) - 0.5), (0, 1, 0), 1.15, 0.3, n=16)

    # ---- the jib pipe ("hook") from the crown's west end down the west side into the platform
    HK = fillet([P3(12.5, 5.6, zl(5.6) - 0.6), P3(12.5, 8.6, zl(8.6) - 0.7), P3(12.0, 10.4, zl(10.4) - 0.7),
                 P3(12.2, 22.1, zl(22.1) - 0.8), P3(19.6, 22.7, zl(22.7) - 0.6)], 1.2, 6)
    sweep(M, mid, HK, [0.6 if 42 - p[1] < 9.2 else (0.8 if p[0] > X(13.5) else 0.95) for p in HK], n=12)
    # cast elbow where the pipe turns east into the platform
    slab(M, mid, rrect(X(11.0), Y(22.6), X(13.9), Y(19.6), 1.1, 3), zl(21.3) - 1.75, zl(21.3) + 0.2, ch=0.35)
    for r in (12.0, 16.0):      # pipe clamps
        c = 12.1 if r < 21 else 12.2
        disc(M, mt(3, "metal"), P3(c, r, zl(r) - 0.75), (0, 1, 0.18), 1.12, 0.45, n=12)

    # ---- the crown: stem riser, sheave housing (two cheeks with the sheave slot), T-beam
    brass = mt(23, "brass")
    station_loft(M, mt(22, "brass"), [(4.6, 19.7, 24.3, ZT - 0.4, zl(5) - 2.0), (8.0, 19.8, 24.1, zl(8) + 0.9, zl(8) - 1.8),
                                      (11.7, 20.0, 24.0, zl(11.7) + 0.45, zl(11.7) - 1.5)], ch=0.4, n=8)
    housing = [(X(17.2), Y(7.7)), (X(31.0), Y(7.7)), (X(31.0), Y(4.75)), (X(16.4), Y(4.75))]
    for poly, xa, xb in ((housing, 16.0, 23.9), (housing, 25.7, 28.0),
                         ([(X(27.9), Y(7.0)), (X(31.0), Y(7.0)), (X(31.0), Y(4.75)), (X(27.9), Y(4.75))], 27.9, 31.5)):
        plan_loft(M, mt(21, "brass"), clip_x(poly, X(xa), X(xb)), [{"z": 7.2}, {"z": ZT - 0.4, "s": 1.7}])
    plan_loft(M, mt(162, "dark"), clip_x(housing, X(23.7), X(25.9)), [{"z": 7.0}, {"z": ZT - 0.9, "s": 1.5}])
    disc(M, mt(4, "metal"), P3(24.8, 5.9, ZT - 1.5), (1, 0, 0), 1.0, 1.6, n=14)   # crown sheave in its slot
    beam = [(X(11.0), Y(5.35)), (X(31.0), Y(5.35)), (X(31.0), Y(4.85)), (X(29.4), Y(4.05)), (X(25.4), Y(2.05)),
            (X(11.0), Y(2.05))]
    plan_loft(M, mt(20, "brass"), beam, [{"z": ZT - 1.35}, {"z": ZT - 0.5, "w": 0.15, "e": 0.15, "n": 0.15, "s": 0.15}])
    seams = [11.0, 15.4, 20.0, 25.0, 31.0]       # plate seams cut down to the beam's core
    for xa, xb in zip(seams, seams[1:]):
        part = clip_x(beam, X(xa + (0.07 if xa > 11 else 0)), X(xb - (0.07 if xb < 31 else 0)))
        plan_loft(M, brass, part, [{"z": ZT - 1.3}, {"z": ZT - 0.35},
                                   {"z": ZT, "w": 0.35, "e": 0.35, "n": 0.35, "s": 0.35}])
    box(M, mt(21, "brass"), 11.0, 5.0, 13.4, 6.6, ZT - 2.4, ZT - 0.8, ch=0.25, slope={"s": 0.4})   # hook lug

    # ---- wire stays, 1.5 px wire rope in the sprite's near-black (1), each along the sprite's dark
    # line into its deadman's socket: the legs -> SW / SE (cols 16-17 and 31-32, rows 36-56), the
    # mast's west and east flanks -> W / E (cols 12 -> 9 and 36 -> 39), and the ground tie W -> SW
    # along rows 47-48 and col 14.
    rope = mt(1, "rope")
    RR = 0.75

    def sock(k, dc=0.0, dr=0.0):
        return (ANCH[k][0] + dc, ANCH[k][1] + dr, ZP + 1.05)

    def stay(pts):
        """pts: (col, row) plan points between a start (col, row, z) and an end (col, row, z);
        heights run linearly by plan length (a taut wire)."""
        (c0, r0, z0), mids, (c1, r1, z1) = pts[0], pts[1:-1], pts[-1]
        plan = [(c0, r0)] + list(mids) + [(c1, r1)]
        L = [0.0]
        for a, b in zip(plan, plan[1:]):
            L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        P = [P3(c, r, z0 + (z1 - z0) * l / L[-1]) for (c, r), l in zip(plan, L)]
        sweep(M, rope, fillet(P, 0.9, 4), RR, n=10)
    stay([(18.9, 31.0, zl(31.0) - 0.6), (17.0, 37.0), (16.0, 43.0), (16.1, 48.0), (16.5, 52.0), (16.0, 55.8),
          sock("sw", 0.6, -0.4)])
    stay([(29.4, 31.0, zl(31.0) - 0.6), (31.0, 37.0), (31.6, 43.0), (31.5, 48.0), (31.8, 52.5), (32.6, 56.0),
          sock("se", -0.2, -0.3)])
    stay([(13.6, 24.6, zl(24.6) - 1.6), (13.4, 29.0), (12.3, 34.5), (11.2, 38.2), (10.1, 40.8), (9.0, 43.4),
          sock("w", 0.3, -0.2)])
    stay([(33.4, 25.2, zl(25.2) - 1.6), (35.8, 30.0), (36.6, 35.5), (37.6, 40.5), (38.6, 43.5), sock("e", -0.1, -0.2)])
    stay([sock("w", 0.4, 0.1), (10.6, 47.3), (13.3, 48.3), (14.2, 50.2), (14.3, 55.6), sock("sw", -0.4, -0.3)])


def drill_part(M, mt, tip):
    """The drill string from the tool joint (row 31) to its bit at row `tip`: kelly pipe and a
    4 px bit with a cutting head."""
    top = (24.0, 31.0)
    zt = max(drill_z(tip), ZP + 1.6)
    sweep(M, mt(4, "metal"), [P3(top[0], top[1], drill_z(top[1])), P3(24.0, tip - 1.6, max(drill_z(tip - 1.6), ZP + 1.9))],
          1.85, n=12)
    a = Vector(P3(24.0, tip - 2.6, max(drill_z(tip - 2.6), zt + 0.35)))
    b = Vector(P3(24.0, tip - 0.4, zt))
    rings = []
    for t, rad in ((0.0, 1.05), (0.12, 1.75), (0.55, 1.9), (0.82, 1.55), (1.0, 0.5)):
        c = a.lerp(b, t)
        rings.append(c)
    sweep(M, mt(6, "metal"), [tuple(c) for c in rings], [1.85, 2.0, 2.1, 1.75, 0.6], n=12)


# --- object, bake, export ----------------------------------------------------------------------------

def to_object(M, name, mats, coll, smooth_angle=40.0, flat_up=False):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.transform(bm, matrix=Matrix.Scale(1 / 12, 4), verts=bm.verts)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


def weighted(o):
    o.data.set_sharp_from_angle(angle=math.radians(40.0))
    wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(o)


def bake_maps(obj, out_dir, n_slots, size=1024, samples=64):
    """A copy of usp_talon.bake_maps (AO + edge-lift colour multiplier, roughness/metal map) with
    white tint and every slot textured, and two fixes for thin round parts: the occlusion rays leave
    about the face's true normal (with the smooth normal, rays from the 12-sided tubes and the
    beam's chamfers went into the part itself and baked ragged black patches along the facets), and
    wider island gaps (0.008 / 0.006 of the atlas) with a 2 px bake margin, so no island's margin
    spills onto a neighbour (the shared one packs islands 2 px apart and bleeds 6 px)."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:  # Metal GPU when there is one
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("talon: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.008, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")

    col_img = bpy.data.images.new("talon_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("talon_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"

    mats = list(me.materials)
    saved = {}
    for i, m in enumerate(mats):
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        N = nt.nodes.new
        L = nt.links.new
        tmp = []

        def node(kind):
            n = N(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            n.use_clamp = op in ("MULTIPLY_ADD",)
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        for ao in (ao_s, ao_l):   # occlusion about the flat face normal: no terminator self-shadowing
            L(geo.outputs["True Normal"], ao.inputs["Normal"])
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, 1.0), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=2, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i in range(n_slots):
        m = mats[i]
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def split_open(obj, layout, coll, suffix="_outline"):
    """Cut a shell into the pieces without filling the cuts (no ink along the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}{suffix}")
        bm.to_mesh(me)
        bm.free()
        sh = bpy.data.objects.new(f"{name}{suffix}", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def composite():
    pix = [[-1] * W for _ in range(H)]
    colors = {}
    for ri, row in enumerate(PIECES):
        for ci, n in enumerate(row):
            d = common.load_sprite(WT, n)
            colors.update(d["colors"])
            for r, line in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(line):
                    if v >= 0:
                        pix[ri * 28 + r][ci * 24 + c] = v
    return pix, colors


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pix, colors = composite()
    sprite = {"name": NAME, "colors": colors}
    coll = common.reset_collection(NAME)
    mt = Mats(sprite, "nshp9B")
    mt_drill = Mats(sprite, "nshp9B_drill")

    S = Model()
    for fn in (build_derrick, build_anchors, build_well):
        fn(S, mt)
    body = to_object(S, f"{NAME}_body", mt.list, coll)
    F = Model()
    build_pad(F, mt)
    build_floor(F, mt)
    floor = to_object(F, f"{NAME}_floor", mt.list, coll, smooth_angle=10.0)
    for o in (body, floor):
        while len(o.data.materials) < len(mt.list):
            o.data.materials.append(mt.list[len(o.data.materials)])
    print(f"{NAME}: body {tris(body)} floor {tris(floor)} triangles")

    shell = common.outline_shell(body, coll, faces=4000)
    shell.hide_render = True

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    body.select_set(True)
    floor.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    obj = body
    obj.name = NAME
    weighted(obj)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nshp9B_bake_"), len(mt.list))
        fmt = "WEBP"
    layout = [(n, ci * 24 + 12 - W / 2, ri * 28 + 14 - H / 2) for ri, row in enumerate(PIECES) for ci, n in enumerate(row)]
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)

    def as_shell(sh):
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        sh.data.materials.clear()
        sh.data.materials.append(outline_mat)
        return sh
    per_piece, total = {}, 0
    for name, cx, cy in layout:
        p, sh = pieces[name], as_shell(shells[name])
        p.name = name
        weighted(p)
        total += tris(p) + tris(sh)
        print(f"{NAME}: piece {name}: {tris(p)} triangles, outline {tris(sh)}")
        per_piece[name] = [o for o in (p, sh) if len(o.data.polygons)]
    # the drill string's lower end, one part per frame pair, cut into newshp-1 / newshp-3
    mid = [entry for entry in layout if entry[0] in ("newshp-1", "newshp-3")]
    for a, b, tip in PAIRS:
        D = Model()
        drill_part(D, mt_drill, tip)
        d = to_object(D, f"drill-{a}", mt_drill.list, coll)
        dshell = common.outline_shell(d, coll, faces=300)
        cut = common.split_assembly(d, mid, coll)
        cut_sh = split_open(dshell, mid, coll, suffix=f"-drill-{a}_outline")
        for name, cx, cy in mid:
            for o, nm in ((cut[name], f"{name}-drill-{a}"), (as_shell(cut_sh[name]), f"{name}-drill-{a}_outline")):
                if not len(o.data.polygons):
                    continue
                o.name = nm
                common.frame_part(o, [a, b])
                total += tris(o)
                per_piece[name].append(o)
        d.hide_render = dshell.hide_render = True
    print(f"{NAME}: total {total} triangles (shells and drill frames included)")
    for name, cx, cy in layout:
        common.export_sprite_model(WT, per_piece[name], f"enemies/{name}", common.load_sprite(WT, name)["sprites"],
                                   image_format=fmt)
    if "--out" in argv:
        for name, cx, cy in layout:
            for o in per_piece[name]:
                o.location = (cx / 12, -cy / 12, 0)
        common.export_glb([o for v in per_piece.values() for o in v], Path(argv[argv.index("--out") + 1]),
                          image_format=fmt)


if __name__ == "__main__":
    main()
