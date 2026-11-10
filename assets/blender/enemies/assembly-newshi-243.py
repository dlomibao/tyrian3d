"""assembly-newshi-243: the red bomber, blueprint geometry first (cross-sections, then detail).

newshi.shp frames 201 | 203 (top row) and 237 | 239 | 241 | 243 (bottom row): six 2x2 enemies make
one 96 x 56 px twin-engined bomber flying DOWN the screen (front = south = player side). Its nose
is the separate enemy newshi-278, so the fuselage is cut open at row 56 where the nose joins.

Engineering reading (blueprint.json / model.js in ../blueprint, refit to the D74 inner mask):

  fuselage    chamfered superellipse loft (n 3), half-width 6.5 px at the tail joint (row 22)
              opening to 9.5 px from row 26 (the inner edge of the sprite's ink); flat-ish belly;
              two circumferential panel joints (rows 33, 44.5) cut as real grooves
  louvres     three raised cooling ribs across each shoulder (sprite rows 27, 29, 31 bright,
              28, 30, 32 dark) standing on the hull surface
  spine/hump  grey dorsal spine from the tail cone forward into a round bright avionics hump
              (rows 33-40), a dark recessed sensor bay with a lens ahead of it (rows 40-44)
  cockpit     two dark glass ovals on the shoulders (sprite ring cols 40-44 / 52-56, rows 44-51),
              canted outward, in a dark frame ring
  nose ridge  light-red raised ridge running forward into the nose piece
  tail        grey tapered cone (rows 6-22) with two ring joints, exhaust nozzle at the tip, thin
              swept dorsal fin on the axis (rows 4-10, 1 px wide in plan)
  engines     grey core cylinders (c 36, r 3) with a rear exhaust dome and a recessed nozzle
              facing the tail, red cheek cowls each side, a red intake ring facing the player
              (rows 19-22) with a dark intake mouth; dark stub pylons to the cone; a grey
              stabiliser canted outward from each outer cowl (sprite cols 26-29)
  wings       thin chamfered slab (straight trailing edge row 30, round tip cols 3-8, leading
              edge 2:1 diagonal from (16, 41) to the glove), round grey tip pod, vent slots with
              light-red ribs, grey spar cap between two grooves, dark recess with two red lamps,
              grey stiffener bar, red inner panel (ribs, cross bar, panel line, outer rail)
  glove       grey root block, thicker than the wing, running forward as a strake beside the nose
              (cols 35-39 to row 55): two raised rails joined by a crossbar (the H), bolt heads
  underside   closed slabs and the belly loft only (no detail)

Colours: the sprite's own palette index per region (blueprint palette_regions_sprite medians,
darkest shading and brightest highlight left out). Satin metal and satin paint, no mirror finish.

Units: authored in sprite px, assembly coordinates c (0..96, axis 48.5) and r (0..56, toward the
nose), z up. Blender X = (c - 48.5) / 12, Y = (28 - r) / 12, Z = z / 12; that origin is screen
(163.5, 3), the same as the current script, so split_assembly uses the same layout offsets.

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newshi-243.py -- \
       [--measure DIR] [--views DIR] [--no-bake] [--no-export] [--out GLB]
Exports public/models/enemies/<piece>.glb (piece + outline shell) and the spriteModels entries;
--out GLB instead writes one scratch glb with the pieces at their assembly offsets.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = WT
NAME = "assembly-newshi-243"
TAG = "nshi243A"
PIECES = ["newshi-201", "newshi-203", "newshi-237", "newshi-239", "newshi-241", "newshi-243"]
AXIS_SCREEN_X, MID_SCREEN_Y = 163.5, 3
AX = 48.5
W_, H_ = 96, 56
BP = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies/assembly-newshi-243/blueprint")
PC0 = {"newshi-239": (24, 28), "newshi-241": (48, 28), "newshi-243": (72, 28),
       "newshi-203": (48, 0), "newshi-201": (24, 0), "newshi-237": (0, 28)}


def toW(c, r, z):
    return Vector(((c - AX) / 12, (28 - r) / 12, z / 12))


# ---------------------------------------------------------------------------------------------
# Maths
# ---------------------------------------------------------------------------------------------

def pchip(xs, ys):
    """Fritsch-Carlson monotone cubic through (xs, ys); returns f(x) (D52 station interpolation)."""
    n = len(xs)
    if n == 1:
        return lambda x: ys[0]
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
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = 0
        while x > xs[i + 1]:
            i += 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def offset(p, d):
    """Polygon moved inward by d (mitre, clamped)."""
    s = 1 if area(p) > 0 else -1
    n, out = len(p), []
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        e0 = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        e1 = Vector((c[0] - b[0], c[1] - b[1])).normalized()
        n0 = Vector((-e0.y * s, e0.x * s))
        n1 = Vector((-e1.y * s, e1.x * s))
        mm = (n0 + n1)
        mm = mm.normalized() if mm.length > 1e-9 else n0
        k = min(2.5, 1 / max(0.3, mm.dot(n0)))
        out.append((b[0] + mm.x * d * k, b[1] + mm.y * d * k))
    return out


def chaikin(p, it=1):
    """Corner cutting on a closed polygon; vertices with a third element True stay hard."""
    for _ in range(it):
        q = []
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            if len(a) > 2 and a[2]:
                q.append(a)
            else:
                q.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            if not (len(b) > 2 and b[2]):
                q.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        p = q
    return [(v[0], v[1]) for v in p]


def F(v):
    return v if callable(v) else (lambda c, r, _v=v: _v)


# ---------------------------------------------------------------------------------------------
# Model: named parts, each its own bmesh (welded and oriented alone), palette index per face
# ---------------------------------------------------------------------------------------------

class Part:
    def __init__(self, name, mirror):
        self.name, self.mirror = name, mirror
        self.bm = bmesh.new()

    def face(self, pts, idx):
        vs = [self.bm.verts.new(p) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = idx  # palette index for now; remapped to slots on merge
        return f


class Model:
    def __init__(self):
        self.parts = []
        self.cur = None

    def part(self, name, mirror=False):
        self.cur = Part(name, mirror)
        self.parts.append(self.cur)
        return self.cur

    def quad(self, a, b, c, d, idx):
        self.cur.face([a, b, c, d], idx)

    def tri(self, a, b, c, idx):
        self.cur.face([a, b, c], idx)

    # Extruded polygon (c, r) with a chamfered top edge; zb / zt numbers or fn(c, r).
    def prism(self, poly, zb, zt, ch, idx_top, idx_wall, no_bottom=False, idx_bottom=None,
              bottom_ch=0.0, idx_ch=None):
        ZT, ZB = F(zt), F(zb)
        if area(poly) < 0:
            poly = poly[::-1]
        ins = offset(poly, ch) if ch > 0 else poly
        n = len(poly)
        bc = bottom_ch
        for i in range(n):
            j = (i + 1) % n
            (c0, r0), (c1, r1) = poly[i], poly[j]
            (d0, s0), (d1, s1) = ins[i], ins[j]
            self.quad(toW(c0, r0, ZB(c0, r0) + bc), toW(c1, r1, ZB(c1, r1) + bc),
                      toW(c1, r1, ZT(c1, r1) - ch), toW(c0, r0, ZT(c0, r0) - ch), idx_wall)
            if ch > 0:
                self.quad(toW(c0, r0, ZT(c0, r0) - ch), toW(c1, r1, ZT(c1, r1) - ch),
                          toW(d1, s1, ZT(d1, s1)), toW(d0, s0, ZT(d0, s0)), idx_ch if idx_ch is not None else idx_wall)
        self.cur.face([toW(c, r, ZT(c, r)) for c, r in ins], idx_top)
        if not no_bottom:
            ib = idx_bottom if idx_bottom is not None else idx_wall
            bp = offset(poly, bc) if bc > 0 else poly
            if bc > 0:
                for i in range(n):
                    j = (i + 1) % n
                    self.quad(toW(bp[i][0], bp[i][1], ZB(*bp[i])), toW(bp[j][0], bp[j][1], ZB(*bp[j])),
                              toW(poly[j][0], poly[j][1], ZB(*poly[j]) + bc),
                              toW(poly[i][0], poly[i][1], ZB(*poly[i]) + bc), ib)
            self.cur.face([toW(c, r, ZB(c, r)) for c, r in bp[::-1]], ib)

    def box(self, c0, r0, c1, r1, z0, z1, ch, idx_top, idx_wall=None, **kw):
        self.prism([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, ch, idx_top,
                   idx_top if idx_wall is None else idx_wall, **kw)

    # Loft along r: stations {r, c, z, w, h, hb, n}; superellipse sections (exponent n, top
    # half-height h, bottom hb), pchip between stations, sampled every `step` px. grooves:
    # [(r, depth, half_width, idx)] cut as real ring grooves (panel joints).
    def loft(self, st, idx, sides=24, step=0.5, open_start=False, open_end=False,
             start_idx=None, end_idx=None, grooves=()):
        rs = [s["r"] for s in st]

        def FF(k):
            if k == "hb":
                return pchip(rs, [s.get("hb", s["h"]) for s in st])
            return pchip(rs, [s.get(k, st[0].get(k, 2.5)) for s in st])
        fc, fz, fw, fh, fn, fb = FF("c"), FF("z"), FF("w"), FF("h"), FF("n"), FF("hb")
        samples = set(rs)
        r = rs[0]
        while r < rs[-1]:
            samples.add(round(r, 3))
            r += step
        shrink = {}
        for gr, gd, ghw, gidx in grooves:
            for rr in (gr - ghw, gr + ghw):
                samples.add(round(rr, 4))
            for rr in (gr - ghw + 0.02, gr + ghw - 0.02):
                samples.add(round(rr, 4))
                shrink[round(rr, 4)] = gd
            for rr in list(samples):
                if gr - ghw + 0.02 < rr < gr + ghw - 0.02:
                    samples.discard(rr)
        R = sorted(samples)
        I = idx if callable(idx) else (lambda r, a, _i=idx: _i)
        groove_at = lambda rm: next((g[3] for g in grooves if abs(rm - g[0]) < g[2]), None)  # noqa: E731

        def ring(r):
            c, z = fc(r), fz(r)
            d = shrink.get(round(r, 4), 0.0)
            w, h, hb = max(0.0, fw(r) - d), max(0.0, fh(r) - d), max(0.0, fb(r) - d)
            n = fn(r) or 2.5
            pts = []
            for i in range(sides):
                a = i / sides * 2 * math.pi
                ca, sa = math.cos(a), math.sin(a)
                x = math.copysign(abs(ca) ** (2 / n), ca) * w
                y = math.copysign(abs(sa) ** (2 / n), sa) * (h if sa >= 0 else hb)
                pts.append(toW(c + x, r, z + y))
            return pts, c, z
        rings = [ring(r) for r in R]
        for k in range(len(R) - 1):
            A, B = rings[k][0], rings[k + 1][0]
            rm = (R[k] + R[k + 1]) / 2
            g = groove_at(rm)
            for i in range(sides):
                j = (i + 1) % sides
                ang = (i + 0.5) / sides * 360
                ix = g if (g is not None and 0 < ang < 180) else I(rm, ang)
                self.quad(A[i], A[j], B[j], B[i], ix)
        if not open_start:
            A, c, z = rings[0]
            ctr = toW(c, R[0], z)
            for i in range(sides):
                self.tri(ctr, A[(i + 1) % sides], A[i], start_idx if start_idx is not None else I(R[0], 90))
        if not open_end:
            B, c, z = rings[-1]
            ctr = toW(c, R[-1], z)
            for i in range(sides):
                self.tri(ctr, B[i], B[(i + 1) % sides], end_idx if end_idx is not None else I(R[-1], 90))

    def strip(self, axis, a0, a1, u0, u1, zfn, h, ch, idx_top, idx_side, na=10, nu=6, sink=0.3, caps=True):
        """A chamfered rib or plate lying on a surface z = zfn(c, r): it runs along `axis` ('c' or 'r')
        from a0 to a1 and spans u0..u1 across; its top stands h above the surface at every point,
        its walls sink `sink` into it (louvres, fairings, hatch plates that conform to the hull)."""
        def P(a, u, z):
            return toW(a, u, z) if axis == "c" else toW(u, a, z)

        def Z(a, u):
            return zfn(a, u) if axis == "c" else zfn(u, a)
        us = [u0 + ch + (u1 - u0 - 2 * ch) * k / (nu - 1) for k in range(nu)]

        def sec(a):
            pts = [P(a, u0, Z(a, u0) - sink), P(a, u0, Z(a, u0) + h - ch)]
            pts += [P(a, u, Z(a, u) + h) for u in us]
            pts += [P(a, u1, Z(a, u1) + h - ch), P(a, u1, Z(a, u1) - sink)]
            return pts
        As = [a0 + (a1 - a0) * k / (na - 1) for k in range(na)]
        secs = [sec(a) for a in As]
        m = len(secs[0])
        for k in range(na - 1):
            A, B = secs[k], secs[k + 1]
            for i in range(m):
                j = (i + 1) % m
                ix = idx_top if (2 <= i and i < j <= m - 3) else idx_side
                self.quad(A[i], A[j], B[j], B[i], ix)
        if caps:
            self.cur.face(secs[0][::-1], idx_side)
            self.cur.face(secs[-1], idx_side)

    def plate(self, poly, zfn, t, idx, idx_edge=None):
        zf = F(zfn)
        self.prism(poly, lambda c, r: zf(c, r) - t / 2, lambda c, r: zf(c, r) + t / 2, min(0.2, t * 0.3),
                   idx, idx if idx_edge is None else idx_edge)

    def vfin(self, c, prof, tb, tt, idx):
        """Vertical fin in the (r, z) plane at column c; thickness tb at the root, tt at the tip."""
        zs = [p[1] for p in prof]
        zmin, zmax = min(zs), max(zs)
        th = lambda z: tb + (tt - tb) * (z - zmin) / max(1e-6, zmax - zmin)  # noqa: E731
        L = [toW(c - th(z) / 2, r, z) for r, z in prof]
        R = [toW(c + th(z) / 2, r, z) for r, z in prof]
        self.cur.face(L, idx)
        self.cur.face(R[::-1], idx)
        n = len(prof)
        for i in range(n):
            j = (i + 1) % n
            self.quad(L[i], L[j], R[j], R[i], idx)

    def dome(self, c0, r0, z0, rc, rr, hz, idx, seg=16, rings=5, tilt=0.0, base=True):
        def P(u, v):
            a, phi = u * 2 * math.pi, v * math.pi / 2
            cc = math.cos(phi)
            dc, dr = math.cos(a) * rc * cc, math.sin(a) * rr * cc
            return toW(c0 + dc, r0 + dr, z0 + dc * tilt + math.sin(phi) * hz)
        for j in range(rings):
            for i in range(seg):
                a, b = P(i / seg, j / rings), P((i + 1) / seg, j / rings)
                c, d = P((i + 1) / seg, (j + 1) / rings), P(i / seg, (j + 1) / rings)
                if j == rings - 1:
                    self.tri(a, b, c, idx)
                else:
                    self.quad(a, b, c, d, idx)
        if base:
            self.cur.face([P(i / seg, 0) for i in range(seg)][::-1], idx)

    def cyl(self, a, b, rad, idx, sides=12, caps=True, idx_cap=None):
        A, B = toW(*a), toW(*b)
        ax = (B - A)
        u = ax.normalized()
        t = Vector((0, 0, 1)) if abs(u.z) < 0.9 else Vector((1, 0, 0))
        v1 = u.cross(t).normalized()
        v2 = u.cross(v1)
        rad = rad / 12
        ring = lambda C: [C + v1 * math.cos(q) * rad + v2 * math.sin(q) * rad  # noqa: E731
                          for q in (i / sides * 2 * math.pi for i in range(sides))]
        RA, RB = ring(A), ring(B)
        for i in range(sides):
            j = (i + 1) % sides
            self.quad(RA[i], RA[j], RB[j], RB[i], idx)
        if caps:
            ic = idx if idx_cap is None else idx_cap
            self.cur.face(RA[::-1], idx)
            self.cur.face(RB, ic)


# ---------------------------------------------------------------------------------------------
# The bomber
# ---------------------------------------------------------------------------------------------

# palette indices per part (sprite medians from the blueprint's region table; see notes)
C = dict(
    fuselage=70, louvre=72, louvreGroove=67, fuseSide=70, noseRidge=71, seamRed=67,
    spine=6, hump=7, hatch=2, lens=12, glass=1003, glassRim=2,
    cone=4, coneRib=3, fin=7, nozzle=3, dark=1,
    nacelle=7, cowlOut=69, cowlIn=70, lip=69, intakeDark=1, cantFin=6, pylon=3,
    wing=4, wingUnder=3, tipPod=5, spar=6, ventSlot=1, ventRib=73, lampRecess=3, wingLamp=72,
    wingBar=6, panel=69, panelRib=69, panelGroove=66, panelBar=70,
    glove=5, gloveRail=6, gloveRailBright=8, gloveGroove=3, flank=3, seam=2,
)

FZ = 1.2
FUSE = [
    dict(r=22.2, c=AX, z=2.0, w=6.1, h=4.5, hb=3.8, n=2.6),
    dict(r=23.0, c=AX, z=1.9, w=6.4, h=5.0, hb=4.3, n=2.7),
    dict(r=24.0, c=AX, z=1.7, w=7.3, h=5.5, hb=4.8, n=2.8),
    dict(r=25.0, c=AX, z=1.5, w=8.2, h=5.8, hb=5.0, n=2.9),
    dict(r=26.2, c=AX, z=FZ, w=9.3, h=6.0, hb=5.1, n=3.0),
    dict(r=40.5, c=AX, z=FZ, w=9.3, h=6.0, hb=5.1, n=3.0),
    dict(r=44.0, c=AX, z=FZ, w=10.1, h=6.0, hb=5.1, n=3.0),
    dict(r=53.5, c=AX, z=FZ - 0.3, w=10.1, h=5.6, hb=4.9, n=3.0),
    dict(r=55.0, c=AX, z=FZ - 0.4, w=9.9, h=5.5, hb=4.8, n=3.0),
    dict(r=56.0, c=AX, z=FZ - 0.5, w=9.1, h=4.7, hb=4.2, n=3.2),
]
_fr = [s["r"] for s in FUSE]
FW, FH, FZC = (pchip(_fr, [s[k] for s in FUSE]) for k in ("w", "h", "z"))


def fuse_top(c, r):
    w = FW(r)
    x = min(1.0, abs(c - AX) / w)
    return FZC(r) + FH(r) * max(0.0, 1 - x ** 3) ** (1 / 3)


def wing_top(c, r):
    return 0.55 - 0.004 * (36 - c)


def wing_bot(c, r):
    return -0.75 + 0.006 * (36 - c)


def glove_top(c, r):
    return 1.9 + 0.08 * (c - 28)


def build_model():
    M = Model()
    L = lambda n: M.part(n, True)    # noqa: E731  left half, mirrored
    Ctr = lambda n: M.part(n, False)  # noqa: E731

    # ---- FUSELAGE ----
    Ctr("fuselage")
    M.loft(FUSE, lambda r, a: C["wingUnder"] if 200 < a < 340 else C["fuselage"], sides=32, step=1.0,
           end_idx=C["fuselage"], start_idx=C["fuselage"],
           grooves=[(33.0, 0.22, 0.3, C["seamRed"]), (44.6, 0.22, 0.3, C["seamRed"]), (54.9, 0.25, 0.22, C["coneRib"])])

    # shoulder louvres: three raised ribs at sprite rows 27, 29, 31 (grooves 28, 30, 32 between)
    L("louvres")
    for r0 in (26.1, 28.1, 30.1):
        M.strip("c", 39.6, 45.2, r0, r0 + 1.05, fuse_top, 0.4, 0.14, C["louvre"], C["louvreGroove"], na=10, nu=3)

    # grey flank fairing over the wing root, on the fuselage side
    L("flank_fairing")
    M.strip("r", 33.4, 43.4, 39.0, 41.9, fuse_top, 0.3, 0.18, C["flank"], C["seam"], na=12, nu=6, sink=0.5)

    # ---- DORSAL SPINE + HUMP ----
    Ctr("spine")
    M.loft([dict(r=19.5, c=AX, z=5.4, w=2.6, h=0.6, n=3), dict(r=21.0, c=AX, z=5.8, w=3.3, h=1.1, n=3),
            dict(r=25.0, c=AX, z=6.6, w=3.3, h=1.0, n=3), dict(r=33.0, c=AX, z=6.6, w=3.4, h=1.1, n=3)],
           C["spine"], sides=20, step=1.2, grooves=[(26.0, 0.18, 0.25, C["seam"])])
    Ctr("hump")
    M.loft([dict(r=32.2, c=AX, z=6.8, w=0.5, h=0.2, n=2.2), dict(r=33.2, c=AX, z=6.8, w=3.2, h=1.6, n=2.2),
            dict(r=35.5, c=AX, z=6.8, w=3.5, h=2.5, n=2.2), dict(r=38.2, c=AX, z=6.8, w=3.4, h=2.5, n=2.2),
            dict(r=39.7, c=AX, z=6.7, w=3.0, h=2.0, n=2.2), dict(r=40.5, c=AX, z=6.6, w=2.0, h=1.2, n=2.2),
            dict(r=40.9, c=AX, z=6.5, w=0.7, h=0.4, n=2.2)],
           C["hump"], sides=18, step=0.7)
    Ctr("sensor_bay")
    M.strip("c", 45.0, 52.0, 40.8, 43.9, fuse_top, 0.3, 0.15, C["hatch"], C["seam"], na=12, nu=5)
    M.dome(47.6, 41.6, fuse_top(47.6, 41.6) + 0.25, 0.8, 0.7, 0.45, C["lens"], seg=12, rings=3)
    Ctr("nose_ridge")
    M.strip("r", 44.3, 56.0, 45.1, 51.9, fuse_top, 0.55, 0.22, C["noseRidge"], C["seamRed"], na=16, nu=6, caps=True)
    L("cockpit_window")
    zc = fuse_top(42.6, 47.6)
    M.dome(42.6, 47.6, zc - 0.15, 2.5, 3.6, 0.55, C["glassRim"], seg=20, rings=2, tilt=0.55)
    M.dome(42.6, 47.6, zc + 0.1, 2.0, 3.0, 0.7, C["glass"], seg=20, rings=4, tilt=0.55)

    # ---- TAIL CONE + nozzle + fin ----
    Ctr("tail_cone")
    M.loft([dict(r=6.25, c=AX, z=2.6, w=1.2, h=1.6, n=2.4), dict(r=7.1, c=AX, z=2.6, w=3.3, h=3.0, n=2.5),
            dict(r=8.2, c=AX, z=2.5, w=4.4, h=3.8, n=2.6), dict(r=10.0, c=AX, z=2.4, w=5.0, h=4.1, n=2.6),
            dict(r=15.0, c=AX, z=2.2, w=5.4, h=4.4, n=2.6), dict(r=18.6, c=AX, z=2.1, w=6.0, h=4.5, n=2.6),
            dict(r=20.0, c=AX, z=2.0, w=6.3, h=4.6, n=2.6), dict(r=22.9, c=AX, z=2.0, w=6.3, h=4.6, n=2.6)],
           C["cone"], sides=20, open_end=True, step=1.4,
           grooves=[(12.5, 0.2, 0.3, C["coneRib"]), (17.5, 0.2, 0.3, C["coneRib"])])
    Ctr("tail_nozzle")
    M.cyl((AX, 7.6, 2.6), (AX, 6.1, 2.6), 1.1, C["nozzle"], 14, idx_cap=C["dark"])
    Ctr("tail_fin")
    M.vfin(AX, [(10.8, 6.2), (5.6, 6.0), (4.1, 12.0), (5.2, 12.4), (9.0, 7.8)], 0.9, 0.7, C["fin"])

    # ---- ENGINE NACELLES (left; mirrored) ----
    NC, NZ = 36.0, 3.6
    L("nacelle_core")
    M.loft([dict(r=8.0, c=NC, z=NZ, w=1.4, h=1.4, n=2.0), dict(r=8.5, c=NC, z=NZ, w=2.3, h=2.3, n=2.0),
            dict(r=9.4, c=NC, z=NZ, w=2.95, h=2.9, n=2.0), dict(r=10.5, c=NC, z=NZ, w=3.1, h=3.1, n=2.0),
            dict(r=18.6, c=NC, z=NZ, w=3.1, h=3.1, n=2.0)],
           C["nacelle"], sides=14, step=1.4,
           grooves=[(11.2, 0.15, 0.25, C["coneRib"]), (16.4, 0.15, 0.25, C["coneRib"])])
    M.cyl((NC, 8.15, NZ), (NC, 7.8, NZ), 0.9, C["nozzle"], 12, idx_cap=C["dark"])
    L("cowl_outer")
    M.loft([dict(r=10.6, c=31.0, z=2.6, w=0.6, h=0.6, n=2.4), dict(r=11.3, c=31.0, z=2.6, w=1.7, h=2.4, n=2.6),
            dict(r=17.0, c=31.2, z=2.6, w=1.7, h=2.4, n=2.6), dict(r=18.4, c=31.6, z=2.6, w=1.2, h=1.6, n=2.6)],
           C["cowlOut"], sides=16, step=1.0)
    L("cowl_inner")
    M.loft([dict(r=10.8, c=41.0, z=2.6, w=0.7, h=0.6, n=2.4), dict(r=11.4, c=41.0, z=2.6, w=1.85, h=2.4, n=2.6),
            dict(r=17.6, c=41.0, z=2.6, w=1.85, h=2.4, n=2.6), dict(r=19.4, c=40.8, z=2.4, w=1.2, h=1.4, n=2.6)],
           C["cowlIn"], sides=12, step=1.5)
    L("intake_lip")
    M.loft([dict(r=17.8, c=NC - 0.4, z=NZ - 0.6, w=3.6, h=3.0, n=2.2), dict(r=19.5, c=NC - 0.6, z=NZ - 0.8, w=3.4, h=2.7, n=2.2),
            dict(r=21.0, c=NC - 0.8, z=NZ - 0.9, w=3.0, h=2.2, n=2.2), dict(r=21.9, c=NC - 1.2, z=NZ - 0.9, w=2.2, h=1.5, n=2.2)],
           C["lip"], sides=14, step=1.0, end_idx=C["intakeDark"])
    L("pylon")
    M.prism([(42.4, 10.8), (44.8, 10.8), (44.8, 22.0), (42.3, 22.0), (41.2, 21.0), (40.2, 20.0), (40.2, 18.2),
             (42.4, 17.4)], 0.6, 2.8, 0.2, C["pylon"], C["seam"])
    L("canted_fin")
    cant = lambda c, r: 3.4 + (29.6 - c) * 1.1  # noqa: E731
    M.plate([(29.8, 10.6), (28.4, 8.2), (26.2, 8.2), (26.2, 11.2), (27.3, 13.0), (28.3, 15.6), (29.0, 17.6), (29.8, 17.6)],
            cant, 0.7, C["cantFin"], C["seam"])

    # ---- WINGS (left; mirrored) ----
    wing_poly = chaikin([(5.8, 30.0, 1), (35.5, 30.0, 1), (35.5, 50.6, 1), (16.2, 41.0, 1), (8.0, 41.0),
                         (6.6, 40.5), (5.6, 39.5), (4.0, 38.0), (3.0, 36.9), (3.0, 32.0), (4.0, 31.0)], 1)
    L("wing_outer")
    M.prism(wing_poly, wing_bot, wing_top, 0.22, C["wing"], C["wingUnder"], bottom_ch=0.15, idx_bottom=C["wingUnder"])
    L("wing_tip_pod")
    M.loft([dict(r=30.4, c=6.2, z=0.1, w=0.8, h=0.6, n=2.2), dict(r=31.1, c=5.9, z=0.1, w=1.8, h=1.1, n=2.2),
            dict(r=32.6, c=5.6, z=0.1, w=2.5, h=1.5, n=2.2), dict(r=36.4, c=5.6, z=0.1, w=2.5, h=1.5, n=2.2),
            dict(r=38.6, c=6.5, z=0.1, w=1.7, h=1.2, n=2.2), dict(r=40.2, c=7.4, z=0.1, w=0.8, h=0.6, n=2.2)],
           C["tipPod"], sides=16, step=1.0)
    L("wing_vents")
    M.box(8.0, 30.2, 16.2, 34.8, 0.3, 0.62, 0.05, C["ventSlot"], C["seam"], no_bottom=True)
    for c in (9, 11, 13, 15):
        M.box(c + 0.05, 30.3, c + 0.95, 34.7, 0.3, 1.05, 0.12, C["ventRib"], C["louvreGroove"], no_bottom=True)
    L("wing_spar")
    M.box(5.6, 35.25, 17.0, 36.85, 0.4, 1.0, 0.2, C["spar"], C["seam"], no_bottom=True)
    L("wing_lamps")
    M.box(8.6, 37.6, 15.8, 40.6, 0.3, 0.6, 0.05, C["lampRecess"], C["seam"], no_bottom=True)
    M.dome(10.5, 39.1, 0.6, 0.55, 1.15, 0.45, C["wingLamp"], seg=10, rings=3)
    M.dome(14.5, 39.0, 0.6, 0.55, 1.0, 0.45, C["wingLamp"], seg=10, rings=3)
    L("wing_bar")
    M.box(16.2, 30.0, 18.9, 41.8, 0.4, 1.25, 0.25, C["wingBar"], C["seam"], no_bottom=True)
    L("inner_panel")
    M.prism([(18.9, 30.0), (28.4, 30.0), (28.4, 40.0), (29.2, 40.0), (29.2, 46.4), (26.0, 46.4), (18.9, 42.9)], 0.3, 1.1, 0.18,
            C["panel"], C["panelGroove"], no_bottom=True)
    for c in (19.6, 21.6, 23.6):
        M.box(c, 30.2, c + 1.2, 34.8, 1.0, 1.55, 0.15, C["panelRib"], C["panelGroove"], no_bottom=True)
    M.box(19.2, 35.8, 28.2, 36.8, 1.0, 1.5, 0.15, C["panelBar"], C["panelGroove"], no_bottom=True)
    M.box(24.0, 37.2, 24.5, 44.6, 1.05, 1.15, 0.0, C["panelGroove"], C["panelGroove"], no_bottom=True)
    M.box(25.0, 30.2, 27.9, 45.8, 1.0, 1.35, 0.15, C["panel"], C["panelGroove"], no_bottom=True)

    # ---- WING GLOVE / ROOT BLOCK (grey) ----
    L("glove")
    M.prism([(28.3, 30.0), (35.2, 30.0), (36.2, 31.0), (38.6, 31.6), (39.6, 31.6), (39.6, 55.0), (35.2, 55.0),
             (35.2, 51.0), (28.3, 47.4), (28.3, 46.4), (29.2, 46.4), (29.2, 40.0), (28.3, 40.0)], -1.2, glove_top, 0.35, C["glove"], C["flank"], bottom_ch=0.3,
            idx_bottom=C["wingUnder"])
    M.box(29.3, 30.4, 30.8, 46.8, 2.0, glove_top(30, 0) + 0.7, 0.25, C["gloveRail"], C["gloveGroove"], no_bottom=True)
    M.box(32.8, 30.4, 34.2, 49.4, 2.0, glove_top(33.5, 0) + 0.9, 0.25, C["gloveRail"], C["gloveGroove"], no_bottom=True)
    M.box(30.8, 35.6, 32.8, 36.8, 2.0, glove_top(31.8, 0) + 0.55, 0.15, C["gloveRail"], C["gloveGroove"], no_bottom=True)
    M.box(35.7, 45.0, 37.8, 54.8, 2.0, glove_top(36.6, 0) + 0.6, 0.25, C["gloveRail"], C["gloveGroove"], no_bottom=True)
    for r in (32.5, 39.5, 43.0):
        M.dome(36.6, r, glove_top(36.6, r), 0.45, 0.45, 0.25, C["gloveRailBright"], seg=8, rings=2)
    return M


# ---------------------------------------------------------------------------------------------
# Merge parts into one object (each part welded and oriented alone; left halves mirrored)
# ---------------------------------------------------------------------------------------------

def materials(sprite):
    spec = {  # palette index -> (metallic, roughness)
        70: (0.15, 0.42), 72: (0.15, 0.4), 67: (0.15, 0.5), 71: (0.15, 0.4), 69: (0.15, 0.45), 66: (0.15, 0.5),
        6: (0.35, 0.38), 7: (0.38, 0.36), 8: (0.4, 0.34), 4: (0.32, 0.42), 5: (0.32, 0.4), 3: (0.3, 0.48),
        2: (0.3, 0.3), 1: (0.2, 0.6), 12: (0.3, 0.2), 73: (0.15, 0.4),
    }
    mats = {i: common.palette_material(sprite, i, TAG, metallic=m, roughness=r) for i, (m, r) in spec.items()}
    mats[1003] = common.palette_material(sprite, 3, TAG + "-glass", metallic=0.3, roughness=0.08)  # cockpit glass
    return mats


def build(sprite, coll):
    M = build_model()
    mats = materials(sprite)
    used = sorted({f.material_index for p in M.parts for f in p.bm.faces})
    slot = {i: k for k, i in enumerate(used)}
    out = bmesh.new()
    me_tmp = bpy.data.meshes.new("tmp")
    for p in M.parts:
        bm = p.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        if "--parts" in sys.argv:
            print("PART", p.name, sum(len(f.verts) - 2 for f in bm.faces) * (2 if p.mirror else 1))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        copies = [bm]
        if p.mirror:
            m = bm.copy()
            bmesh.ops.scale(m, vec=(-1, 1, 1), verts=m.verts)
            bmesh.ops.reverse_faces(m, faces=m.faces)
            copies.append(m)
        for b in copies:
            for f in b.faces:
                f.material_index = slot[f.material_index]
            b.to_mesh(me_tmp)
            out.from_mesh(me_tmp)
    bpy.data.meshes.remove(me_tmp)
    bmesh.ops.triangulate(out, faces=[f for f in out.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    me = bpy.data.meshes.new(NAME)
    out.to_mesh(me)
    out.free()
    for i in used:
        me.materials.append(mats[i])
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ---------------------------------------------------------------------------------------------
# The sprite and its masks
# ---------------------------------------------------------------------------------------------

IDX_L, COLS = sprite_mask.load(NAME, ref=str(ROOT / "reference" / "models"))
IDX = np.array(IDX_L)
MASKS = sprite_mask.masks(IDX_L, COLS)
INNER = np.array(MASKS["inner"], dtype=bool)
FREE = np.array(MASKS["free"], dtype=bool)


def merged_sprite():
    data = common.load_sprite(ROOT, "newshi-243")
    for n in PIECES:
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


# ---------------------------------------------------------------------------------------------
# Measure and views
# ---------------------------------------------------------------------------------------------

def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [w for w in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split() if w.isupper()]
        scene.render.engine = next(n for n in names if want.split("_")[1] in n)


def render_array(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], img.channels)
    bpy.data.images.remove(img)
    return px[::-1]


REGIONS = {  # blueprint prep.py boxes [c0, c1) x [r0, r1), left half (+ mirror)
    "tip_pod": (3, 31, 8, 40, True), "vent_ribs": ([(9, 30, 10, 35), (11, 30, 12, 35), (13, 30, 14, 35), (15, 30, 16, 35)], 0, 0, 0, True),
    "wing_spar": (6, 35, 17, 37, True), "lamp_recess": (9, 38, 16, 41, True), "wing_lamps": ([(10, 38, 11, 41), (14, 38, 15, 40)], 0, 0, 0, True),
    "wing_bar": (17, 31, 19, 41, True), "panel_ribs": (19, 30, 26, 35, True), "panel_bar": (19, 36, 26, 37, True),
    "panel_plate": (19, 37, 28, 45, True), "glove": ([(28, 31, 33, 47), (34, 31, 38, 45)], 0, 0, 0, True),
    "flank": (39, 34, 42, 44, True), "louvres": (40, 24, 45, 34, True), "fuse_side": ([(39, 45, 41, 55), (42, 34, 45, 43)], 0, 0, 0, True),
    "spine": (45, 21, 52, 33, False), "hump": (45, 33, 52, 40, False), "hatch": (45, 40, 52, 44, False),
    "nose_ridge": (45, 45, 52, 56, False), "windows": (40, 45, 45, 51, True), "tail_cone": ([(43, 8, 47, 23)], 0, 0, 0, True),
    "nacelle_core": (33, 8, 39, 18, True), "cowl_out": (29, 11, 33, 18, True), "cowl_in": (39, 11, 42, 18, True),
    "intake_lip": (33, 19, 38, 22, True), "canted_fin": (26, 8, 29, 16, True),
}


def region_labels():
    """Sprite regions for the colour check: family per pixel from the sprite (red ramp 64-77 vs grey)."""
    fam = np.full(IDX.shape, "", dtype=object)
    fam[(IDX >= 64) & (IDX <= 79)] = "red"
    fam[(IDX >= 2) & (IDX <= 15)] = "grey"
    return fam


def measure(obj, out_dir, ss=8):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o.type == "MESH" and o is not obj and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0, 0, 0)
    cd = bpy.data.cameras.new("measure")
    cd.type = "ORTHO"
    cd.ortho_scale = W_ / 12
    cam = bpy.data.objects.new("measure", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)   # X 0 = axis 48.5 = image centre (96/2 = 48 edge... see below)
    # image centre must be c = 48 (edge) for a 96-wide grid: shift by -0.5 px
    cam.location.x = (48 - AX) / 12
    cam.location.y = 0.0       # r = 28 edge = image centre of a 56-tall grid
    scene.render.resolution_x = W_ * ss
    scene.render.resolution_y = H_ * ss
    scene.render.resolution_percentage = 100
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sil = render_array(scene, cam, out_dir / "top_silhouette.png")[..., 0]
    top = sil > 0.5
    cov = sil.reshape(H_, ss, W_, ss).mean(axis=(1, 3))
    model = cov >= 0.5
    keep = ~FREE
    res = {}

    def iou_grid(rs, cs):
        m, s, k = model[rs, cs], INNER[rs, cs], keep[rs, cs]
        return float(((m & s) & k).sum() / max(1, ((m | s) & k).sum()))
    res["iou_rule_grid"] = round(iou_grid(slice(0, H_), slice(0, W_)), 4)
    res["pieces"] = {}
    for n in PIECES:
        c0, r0 = PC0[n]
        res["pieces"][n] = round(iou_grid(slice(r0, r0 + 28), slice(c0, c0 + 24)), 4)
    big = np.kron(INNER, np.ones((ss, ss), dtype=bool))
    bf = np.kron(FREE, np.ones((ss, ss), dtype=bool))
    res["iou_rule_hires"] = round(float(((big & top) & ~bf).sum() / max(1, ((big | top) & ~bf).sum())), 4)
    diff = np.full((H_, W_), ".")
    diff[INNER] = "-"
    diff[model & INNER] = "#"
    diff[model & ~INNER] = "+"
    diff[FREE & ~model] = "f"
    diff[FREE & model] = "F"
    (out_dir / "diff.txt").write_text("\n".join("".join(r) for r in diff) + "\n")
    res["colours"] = {}
    # colour: flat material colours from above, nearest palette index among the materials
    sh.color_type = "MATERIAL"
    for m in obj.data.materials:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        m.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)
    flat = render_array(scene, cam, out_dir / "top_flat.png")[..., :3]
    centre = flat[ss // 2::ss, ss // 2::ss]
    keys = sorted({int(m.name.split("_")[1]) for m in obj.data.materials})
    keys = [k for k in keys]

    arr = np.array([[v / 255 for v in COLS[k]] for k in keys])
    d = ((centre[..., None, :] - arr[None, None]) ** 2).sum(-1)
    seen = np.array(keys)[d.argmin(-1)]
    seen[~model] = -1
    np.save(out_dir / "seen.npy", seen)
    fam = region_labels()
    mfam = np.full(seen.shape, "", dtype=object)
    mfam[(seen >= 64) & (seen <= 79)] = "red"
    mfam[(seen >= 2) & (seen <= 15)] = "grey"
    mfam[seen == 1] = "dark"
    sel = INNER & model & (fam != "")
    agree = (fam == mfam) & sel
    res["family_agree"] = round(float(agree.sum() / max(1, sel.sum())), 4)
    fdiff = np.full((H_, W_), ".")
    fdiff[sel & (fam == "red")] = "r"
    fdiff[sel & (fam == "grey")] = "g"
    fdiff[sel & ~agree & (fam == "red")] = "R"
    fdiff[sel & ~agree & (fam == "grey")] = "G"
    (out_dir / "family_diff.txt").write_text("\n".join("".join(r) for r in fdiff) + "\n")
    # blueprint regions: median sprite index vs what the model shows there
    bp = json.loads((BP / "blueprint.json").read_text()) if (BP / "blueprint.json").exists() else {"palette_regions_sprite": {}}
    res["features"] = {}
    for name, (c, r) in {"lens": (47, 41), "window_L": (42, 47), "window_R": (54, 47), "lamp_L1": (10, 39),
                         "lamp_L2": (14, 39), "lamp_R1": (86, 39), "lamp_R2": (82, 39), "intake_L": (35, 20),
                         "hump": (47, 36), "fin": (48, 5), "tip_pod": (4, 34)}.items():
        res["features"][name] = {"sprite": int(IDX[r, c]), "model": int(seen[r, c])}
    # per region: sprite median (blueprint table) vs the model's most common index seen from above
    res["regions"] = {}
    med = bp["palette_regions_sprite"]
    for k, (c0, r0, c1, r1, mir) in REGIONS.items():
        sel = np.zeros((H_, W_), dtype=bool)
        for (a0, b0, a1, b1) in c0 if isinstance(c0, list) else [(c0, r0, c1, r1)]:
            sel[b0:b1, a0:a1] = True
            if mir:
                sel[b0:b1, 97 - a1:97 - a0] = True
        v = seen[sel & (seen >= 0)]
        if not len(v):
            continue
        vals, cnt = np.unique(v, return_counts=True)
        res["regions"][k] = {"sprite": med[k]["median"] if k in med else None, "model": int(vals[cnt.argmax()])}
    (out_dir / "metrics.json").write_text(json.dumps(res, indent=1))
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in hidden:
        o.hide_render = False
    print("MEASURE", json.dumps(res))
    return res


def render_views(objs, out_dir, size=900):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o.type == "MESH" and o not in objs and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    set_engine(scene, "BLENDER_EEVEE")
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.21, 0.24, 1)
    bg.inputs["Strength"].default_value = 1.0
    lights = []
    for name, rot, energy in (("key", (math.radians(35), math.radians(-25), math.radians(-20)), 3.6),
                              ("fill", (math.radians(60), math.radians(40), math.radians(160)), 0.9)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(3)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)
        lights.append(lo)
    centre = Vector((0, 0.0, 0.25))
    d = 16.0
    specs = [
        ("top", (0, 0, 10), 8.4),
        ("front_south", (0, -10, 0), 8.4),
        ("side_east", (10, 0, 0), 8.4),
        ("rear_north", (0, 10, 0), 8.4),
        ("high34_sw", (-d * 0.5, -d * 0.55, d * 0.55), None),
        ("high34_ne", (d * 0.55, d * 0.5, d * 0.5), None),
        ("game", (0, -d * 0.53, d * 0.85), None),
        ("low_se", (d * 0.6, -d * 0.7, d * 0.18), None),
        ("under", (d * 0.35, -d * 0.45, -d * 0.6), None),
    ]
    paths = {}
    for name, loc, ortho in specs:
        cd = bpy.data.cameras.new(name)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        else:
            cd.lens = 70
        co = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(co)
        co.location = centre + Vector(loc)
        co.rotation_euler = (centre - co.location).to_track_quat("-Z", "Y").to_euler()
        if name == "top":
            co.rotation_euler = (0, 0, 0)
        scene.camera = co
        p = out_dir / f"{name}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        paths[name] = str(p)
        bpy.data.objects.remove(co, do_unlink=True)
    for lo in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
    for o in hidden:
        o.hide_render = False
    return paths


# ---------------------------------------------------------------------------------------------
# Bake: occlusion and edge lift into a grey colour multiplier and a roughness/metal map
# (no concept projection; maps.json "bake": "model"). Copied from the sibling designs'
# bake (usp_talon.bake_maps pattern) so the images get this model's names.
# ---------------------------------------------------------------------------------------------

def bake_maps(obj, out_dir, size=1024, samples=48):
    scene = bpy.context.scene
    set_engine(scene, "CYCLES")
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{TAG}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def mth(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.2
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            v = mth("MINIMUM", mth("ADD", mth("ADD", 0.5, mth("MULTIPLY", occl, 0.6)), mth("MULTIPLY", edge, 0.15)), 1.0)
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.15)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
        nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
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
    for m in mats:
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


# ---------------------------------------------------------------------------------------------

def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shell)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def islands(obj):
    """Vertex counts of the piece's connected islands (a few small ones are the glove rails, vents
    and lamps standing on the hull; a tiny one hovering off the hull would be a sliver)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, n, pts = [v], 0, []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            n += 1
            pts.append(x.co)
            stack += [e.other_vert(x) for e in x.link_edges]
        if n < 30 and "--islands" in sys.argv:
            c = sum((q for q in pts), Vector()) / n
            print(f"  island {n}: centre ({c.x:.3f}, {c.y:.3f}, {c.z:.3f})")
        out.append(n)
    bm.free()
    return sorted(out, reverse=True)


SHELL_FACES = 1500


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa: E731
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    print(f"model: {len(obj.data.polygons)} faces, {tris(obj)} triangles")
    if arg("--measure"):
        measure(obj, arg("--measure"))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_maps(obj, tempfile.mkdtemp(prefix="nshi243_bake_"))
        fmt = "WEBP"
    if arg("--views"):
        render_views([obj], arg("--views"))
    if "--no-export" in argv:
        return
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(obj, coll, voxel=0.016, faces=SHELL_FACES, smooth=6)
    layout = [(e["model"], e["cx"] - AXIS_SCREEN_X, e["cy"] - MID_SCREEN_Y) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    parts = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll, "_outline")
    shell.hide_render = True
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for name, cx, cy in layout:
        p, sh = parts[name], shells[name]
        sh.data.shade_smooth()
        sh["tyrian_outline"] = True
        sh.data.materials.clear()
        sh.data.materials.append(outline_mat)
        sh.hide_render = True
        data = common.load_sprite(ROOT, name)
        if arg("--out"):
            continue
        common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", data["sprites"], image_format=fmt)
        print(f"piece {name}: {tris(p)} triangles, outline {tris(sh)} triangles")
        print(f"piece {name}: loose islands (verts) {islands(p)}")
    if arg("--out"):
        out_objs = []
        for name, cx, cy in layout:
            for o in (parts[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
                out_objs.append(o)
        common.export_glb(out_objs, Path(arg("--out")), image_format=fmt)
        print(f"exported {arg('--out')}")


if __name__ == "__main__":
    main()
