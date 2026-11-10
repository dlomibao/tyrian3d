"""Muzzle cap of the big blue gun (newshc.shp frame 275, 1x1 sprite, 12x14 tile): final.

The firing end of the boss gun assembly-newshc-271 (D121): it is bolted on where newshc-273 ends
(gun c 72), rides with the gun (global ev19 velocities) and carries turret 46, the gun's shots.
So it is built as the gun's own hardware carried on, cross-sections first, in the gun's units:

  c   east, cap column (c 0 = gun c 72, the joint face; the tile spans c 0-12, the cap c 0-5)
  r   south, sprite row (the cap's rows are the gun's rows 0-14)
  h   up, in the gun's height units (the gun's Blender build shifts everything by -Z0 = -3.6 px)

- MUZZLE BRAKE: the gun's muzzle/upper prism section exactly (r 2-6, h 2.2-7.4, 0.5 px top
  chamfer; top 57, sides 56, chamfers 59 as the gun) carried 3.6 px, then a bullnose to c 4.88: the
  side walls sink, the chamfers grow, the top drops to 6.55 and the bottom rolls in (pchip in c).
  Three vent ports through each side wall (framed, dark), a joint seam over the top at c 0 and a
  seam where the nose starts, two flush bolts by it. On the nose face: a real bored muzzle (rim,
  dark bore wall 0.7 px deep, red charge 114 at its bottom).
- LOWER HOUSING: the gun's muzzle/lower step (top 51) carried on as a housing round the emitter
  feed, its NE corner chamfered (sprite row 6 col 4 ink), a lit south bevel (54, sprite row 8),
  a sill along r 8-9 that bridges the sprite's waist at c 0-1 rows 6-7 (dark there: a recessed
  joint, open below), a clamp strap (53) with a hex bolt (56) along row 7.
- EMITTER NOZZLE: the gun's emitter ends open at c 72; a thin dark plate closes it and a feed pipe
  runs under the sill (row 8), since col 0 rows 9-11 are the sprite's ink. The nozzle starts at c 1
  with a red charge ring (114, the sprite's red at row 10), a dark neck (49) into the collar, then
  on r 10.45 / h 2.6, r 8.9-12.0: collar 55, body 57, band 56, crown 55 with two side slots, and a
  real bore with the red charge glowing at its bottom.
- Top-view fit (fix round 1): the nose face at c 4.88, the housing's NE corner chamfered steeply to
  open the row 6 col 4 notch, shallow port frames, a 54 strip on the brake top (sprite row 5).

Underside: closed flat bottoms only. The outline shell (D51) is left open on the joint face so
no ink line is drawn across the seam with the gun (as the gun's split_open shells).

Run: blender --background --python newshc-275.py [-- --render <dir>]
Exports public/models/enemies/newshc-275.glb and its spriteModels entry (frame 275).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

WT = Path(os.environ.get("TYRIAN_WT") or "/Users/dlomibao/projects/tyrian-worktrees/e1-enemies-3")
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "enemies")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
SPRITE_DIR = None
NAME = "newshc-275"
TAG = "nshc275"
Z0 = 3.6  # px, as assembly-newshc-271

SPRITE = None
MATS = []
MAT_IDX = {}
PARTS = []
PART_IDX = {}
# The gun's finishes (assembly-newshc-271.py FINISH), so the cap is the same metal.
FINISH = {
    "metal": dict(metallic=0.55, roughness=0.42),
    "dark": dict(metallic=0.35, roughness=0.55),
    "glow": dict(metallic=0.0, roughness=0.5, emission_strength=3.0),
}


def load_sprite():
    d = common.load_sprite(WT, NAME)
    g = common.load_sprite(WT, "newshc-273")  # same palette (5); the gun's darks 48-50
    for k, v in g["colors"].items():
        d["colors"].setdefault(k, v)
    return d


def M(idx, finish=None):
    if finish is None:
        finish = "glow" if idx == 114 else ("dark" if idx in (48, 49, 50, 1) else "metal")
    key = (idx, finish)
    if key not in MAT_IDX:
        MAT_IDX[key] = len(MATS)
        MATS.append(common.palette_material(SPRITE, idx, f"{TAG}-{finish}", **FINISH[finish]))
    return MAT_IDX[key]


class Builder:
    """T.Part plus a per-face part id (for the per-region colour check)."""

    def __init__(self):
        self.P = T.Part(NAME, smooth_angle=35.0)
        self.layer = self.P.bm.faces.layers.int.new("part")
        self.cur = 0

    def part(self, name):
        if name not in PART_IDX:
            PART_IDX[name] = len(PARTS)
            PARTS.append(name)
        self.cur = PART_IDX[name]

    @staticmethod
    def _p(c, r, h):
        # T.finish maps (x, y, z) -> (x/12, (14-y)/12, z/12): tile centre (c 6, r 7) at the origin.
        return (c - 6.0, r + 7.0, h - Z0)

    def v(self, c, r, h):
        return self.P.v(self._p(c, r, h))

    def f(self, verts, mat, out=None, away=None):
        if away is not None:
            away = self._p(*away)
        face = self.P.f(verts, mat, out=out, away=away)
        if face is not None:
            face[self.layer] = self.cur
        return face


B = None


# ----------------------------------------------------------------------------------------------
# Primitives (c, r, h)
# ----------------------------------------------------------------------------------------------

def inset(poly, d):
    if d <= 0:
        return [tuple(p) for p in poly]
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        ln = math.hypot(nx, ny)
        nx, ny = nx / ln, ny / ln
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx) * nx + (cy - my) * ny < 0:
            nx, ny = -nx, -ny
        lines.append((a[0] + nx * d, a[1] + ny * d, b[0] - a[0], b[1] - a[1]))
    out = []
    for i in range(n):
        L1, L2 = lines[(i - 1) % n], lines[i]
        den = L1[2] * L2[3] - L1[3] * L2[2]
        if abs(den) < 1e-9:
            out.append((L2[0], L2[1]))
            continue
        t = ((L2[0] - L1[0]) * L2[3] - (L2[1] - L1[1]) * L2[2]) / den
        out.append((L1[0] + L1[2] * t, L1[1] + L1[3] * t))
    return out


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def prism(name, poly, h0, h1, ch, top, side=None, cham=None, bottom=True):
    """Chamfered prism over a convex plan polygon (c, r): sides h0..h1-ch, 45-degree chamfer, top."""
    B.part(name)
    side = top if side is None else side
    cham = side if cham is None else cham
    ch = min(ch, (h1 - h0) * 0.6)
    n = len(poly)
    cen = (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n, (h0 + h1) / 2)
    r0 = [B.v(p[0], p[1], h0) for p in poly]
    r1 = [B.v(p[0], p[1], h1 - ch) for p in poly] if ch > 0 else None
    r2 = [B.v(p[0], p[1], h1) for p in inset(poly, ch)]
    mid = r1 if ch > 0 else r2
    for i in range(n):
        j = (i + 1) % n
        B.f((r0[i], r0[j], mid[j], mid[i]), side, away=cen)
        if ch > 0:
            B.f((r1[i], r1[j], r2[j], r2[i]), cham, away=cen)
    B.f(r2, top, out=(0, 0, 1))
    if bottom:
        B.f(r0, side, out=(0, 0, -1))


def wall_prism(name, c0, c1, h0, h1, r_face, depth, out_sign, mat):
    """A box on a side wall (r = r_face), standing `depth` proud toward out_sign (+1 south, -1 north)."""
    B.part(name)
    ra, rb = r_face - out_sign * 0.05, r_face + out_sign * depth
    pts = [(c0, ra, h0), (c1, ra, h0), (c1, ra, h1), (c0, ra, h1), (c0, rb, h0), (c1, rb, h0), (c1, rb, h1), (c0, rb, h1)]
    v = [B.v(*p) for p in pts]
    cen = ((c0 + c1) / 2, (ra + rb) / 2, (h0 + h1) / 2)
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        B.f([v[i] for i in q], mat, away=cen)


def section(n, p=2.0):
    out = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        co, si = math.cos(t), math.sin(t)
        out.append((math.copysign(abs(co) ** (2 / p), co), math.copysign(abs(si) ** (2 / p), si)))
    return out


def ring_c(c, r, h, a, b, n, p=2.0):
    return [B.v(c, r + u * a, h + w * b) for u, w in section(n, p)]


def bridge(ra, rb, mat, cen):
    n = len(ra)
    for j in range(n):
        k = (j + 1) % n
        B.f((ra[j], ra[k], rb[k], rb[j]), mat, away=cen)


def loft_c(name, stations, mats, n=20, p=2.0, cap0=True, cap1=True):
    """A tube along c through stations (c, r, h, a, b); returns the rings."""
    B.part(name)
    rings = [ring_c(c, r, h, a, b, n, p) for c, r, h, a, b in stations]
    for i in range(len(rings) - 1):
        m = mats[i] if isinstance(mats, (list, tuple)) else mats
        c0, r0, h0 = stations[i][:3]
        c1, r1, h1 = stations[i + 1][:3]
        bridge(rings[i], rings[i + 1], m, ((c0 + c1) / 2, (r0 + r1) / 2, (h0 + h1) / 2))
    m0 = mats[0] if isinstance(mats, (list, tuple)) else mats
    m1 = mats[-1] if isinstance(mats, (list, tuple)) else mats
    if cap0:
        B.f(rings[0], m0, out=(-1, 0, 0))
    if cap1:
        B.f(rings[-1], m1, out=(1, 0, 0))
    return rings


def loft_sec(name, stations, mats, cap0=None, cap1=None):
    """Loft along c through stations (c, [(r, h), ...]) (same vertex count, convex); edge e (vertex
    e to e+1) gets mats[e]. cap0/cap1: material of the flat end caps, None = open. Returns rings."""
    B.part(name)
    rings = [[B.v(c, r, h) for r, h in sec] for c, sec in stations]
    n = len(stations[0][1])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        ca, cb = stations[i], stations[i + 1]
        cen = ((ca[0] + cb[0]) / 2, sum(q[0] for q in ca[1]) / n, sum(q[1] for q in ca[1]) / n)
        for e in range(n):
            f = (e + 1) % n
            B.f((a[e], a[f], b[f], b[e]), mats[e], away=cen)
    if cap0 is not None:
        B.f(rings[0], cap0, out=(-1, 0, 0))
    if cap1 is not None:
        B.f(rings[-1], cap1, out=(1, 0, 0))
    return rings


def annulus(outer, inner, centre, mat, out):
    """Fill the flat ring between two closed loops of any vertex counts (same plane, c const)."""
    def ang(v):
        q = Builder._p(*centre)
        return math.atan2(v.co.z - q[2], v.co.y - q[1])

    def ordered(loop):
        lst = sorted(loop, key=ang)
        return lst, [ang(v) for v in lst]

    A, aa = ordered(outer)
    Bq, bb = ordered(inner)
    i = j = 0
    na, nb = len(A), len(Bq)
    while i < na or j < nb:
        a0, a1 = A[i % na], A[(i + 1) % na]
        b0, b1 = Bq[j % nb], Bq[(j + 1) % nb]
        ta = aa[(i + 1) % na] + (2 * math.pi if i + 1 >= na else 0)
        tb = bb[(j + 1) % nb] + (2 * math.pi if j + 1 >= nb else 0)
        if j >= nb or (i < na and ta <= tb):
            B.f((a0, a1, b0), mat, out=out)
            i += 1
        else:
            B.f((a0, b1, b0), mat, out=out)
            j += 1


def hexbolt(name, c, r, h0, h1, rad, mat):
    """A hex head standing on a top face."""
    B.part(name)
    lo = [B.v(c + rad * math.cos(math.pi / 3 * k), r + rad * math.sin(math.pi / 3 * k), h0) for k in range(6)]
    hi = [B.v(c + rad * math.cos(math.pi / 3 * k), r + rad * math.sin(math.pi / 3 * k), h1 - 0.04) for k in range(6)]
    tp = [B.v(c + rad * 0.82 * math.cos(math.pi / 3 * k), r + rad * 0.82 * math.sin(math.pi / 3 * k), h1) for k in range(6)]
    cen = (c, r, (h0 + h1) / 2)
    bridge(lo, hi, mat, cen)
    bridge(hi, tp, mat, cen)
    B.f(tp, mat, out=(0, 0, 1))
    B.f(lo, mat, out=(0, 0, -1))


# ----------------------------------------------------------------------------------------------
# The cap
# ----------------------------------------------------------------------------------------------

def nose_section(k):
    """The muzzle block's section (r, h) at nose progress k (0 = the gun's muzzle/upper prism)."""
    si = 0.3 * k * k
    ch = 0.5 + 1.25 * k
    cb = 0.9 * k
    top = 7.4 - 0.85 * k * k
    bot = 2.2 + 0.15 * k
    lo, hi = 2 + si + ch, 6 - si - ch
    split = lo + (hi - lo) * 0.833  # r 5.0 on the flat section: the sprite's darker 54 band (row 5)
    return [(2 + si, bot + cb), (2 + si + cb, bot), (6 - si - cb, bot), (6 - si, bot + cb),
            (6 - si, top - ch), (hi, top), (split, top), (lo, top), (2 + si, top - ch)]


NOSE = 4.88  # the nose face, inside the sprite's col 5 ink


def brake():
    # stations: flat to c 3.6, then a pchip bullnose to c 5
    sc = (NOSE - 3.6) / 1.4
    kc = [3.6 + (c - 3.6) * sc for c in (3.6, 3.9, 4.2, 4.45, 4.65, 4.82, 4.94, 5.0)]
    kk = [0.0, 0.12, 0.28, 0.45, 0.62, 0.8, 0.93, 1.0]
    f = T.pchip(kc, kk)
    cs = [0.0, 3.6] + [3.6 + (NOSE - 3.6) * t / 9 for t in range(1, 10)]
    st = [(c, nose_section(0.0 if c <= 3.6 else min(1.0, max(0.0, f(c))))) for c in cs]
    edge = [M(56), M(56), M(56), M(56), M(59), M(54), M(57), M(59), M(56)]
    #        bottomN bottom bottomS south chamferS topS top  chamferN north
    rings = loft_sec("brake/block", st, edge, cap0=M(56), cap1=None)
    # nose face with a bored muzzle (bore on r 4.0, h 4.45)
    B.part("brake/face")
    bc = (NOSE, 4.0, 4.45)
    rim_o = ring_c(NOSE, 4.0, 4.45, 1.15, 1.0, 24)
    annulus(rings[-1], rim_o, bc, M(55), (1, 0, 0))
    B.part("brake/bore_rim")
    rim_f = ring_c(NOSE + 0.06, 4.0, 4.45, 1.12, 0.97, 24)
    rim_i = ring_c(NOSE + 0.06, 4.0, 4.45, 0.85, 0.72, 24)
    bridge(rim_o, rim_f, M(57), (NOSE - 0.1, 4.0, 4.45))
    bridge(rim_f, rim_i, M(57), (NOSE - 0.1, 4.0, 4.45))
    B.part("brake/bore")
    cd = NOSE - 0.65
    deep = ring_c(cd, 4.0, 4.45, 0.85, 0.72, 24)
    bridge(rim_i, deep, M(48), (cd + 0.35, 4.0, 4.45 + 5.0))  # faces point in (toward the axis)
    glow = ring_c(cd + 0.001, 4.0, 4.45, 0.42, 0.35, 16)
    B.part("brake/bore_glow")
    annulus(deep, glow, (cd, 4.0, 4.45), M(48), (1, 0, 0))
    B.f(glow, M(114), out=(1, 0, 0))
    # seams over the top: the joint with the gun and where the nose starts
    prism("brake/joint_line", rect(0.0, 2.45, 0.16, 5.55), 7.3, 7.43, 0, M(53))
    prism("brake/nose_line", rect(3.58, 2.5, 3.7, 5.5), 7.3, 7.43, 0, M(55))
    # two flush bolts by the nose seam (as the gun's muzzle bolts)
    for r in (3.2, 4.8):
        hexbolt("brake/bolt", 3.05, r, 7.3, 7.52, 0.28, M(59))
    # vent ports: three through each side wall, a dark slot in a machined frame
    for c in (0.7, 1.75, 2.8):
        wall_prism("brake/port_N", c, c + 0.7, 3.4, 6.45, 2.0, 0.012, -1, M(48))
        wall_prism("brake/port_frame", c - 0.1, c + 0.8, 6.45, 6.6, 2.0, 0.03, -1, M(55))
        wall_prism("brake/port_frame", c - 0.1, c + 0.8, 3.25, 3.4, 2.0, 0.03, -1, M(55))
        wall_prism("brake/port_frame", c - 0.1, c, 3.4, 6.45, 2.0, 0.03, -1, M(55))
        wall_prism("brake/port_frame", c + 0.7, c + 0.8, 3.4, 6.45, 2.0, 0.03, -1, M(55))
        wall_prism("brake/port_S", c, c + 0.7, 6.15, 6.72, 6.0, 0.012, 1, M(48))
        wall_prism("brake/port_frame", c - 0.1, c + 0.8, 6.72, 6.84, 6.0, 0.03, 1, M(55))


def housing():
    def low(r0):
        return [(r0, 2.2), (9.0, 2.2), (9.0, 5.0), (8.0, 6.0), (r0 + 0.35, 6.0), (r0, 5.65)]
    #          bottom     south      bevel      top        chamferN       north
    edge = [M(50), M(50), M(54), M(51), M(50), M(50)]
    # NE corner: a steep chamfer to r 6.95 by c 4.05, so the sprite's row 6 col 4 notch stays open
    loft_sec("housing/body", [(1.0, low(6.0)), (3.85, low(6.0)), (4.05, low(6.95)), (4.95, low(7.05))], edge,
             cap0=M(50), cap1=M(52))
    sill = [(8.0, 3.35), (9.0, 3.35), (9.0, 4.7), (8.35, 5.35), (8.0, 5.35)]
    loft_sec("housing/sill", [(0.0, sill), (1.05, sill)], [M(50), M(50), M(52), M(51), M(50)], cap0=M(50), cap1=M(50))
    # clamp strap along row 7 with a hex bolt (sprite row 7: 56 at col 1, 53 at cols 2-3)
    prism("housing/clamp_band", rect(1.25, 7.1, 3.9, 7.9), 5.9, 6.3, 0.1, M(53))
    hexbolt("housing/clamp_bolt", 1.62, 7.5, 6.3, 6.62, 0.36, M(56))
    # an access plate on the south wall, in the strip the nozzle leaves visible (h 3.9-5.0)
    wall_prism("housing/access_plate", 1.35, 4.5, 4.05, 4.85, 9.0, 0.06, 1, M(53))
    for c in (1.6, 4.25):
        wall_prism("housing/plate_screw", c - 0.1, c + 0.1, 4.35, 4.55, 9.0, 0.1, 1, M(56))
    prism("housing/clamp_knuckle", rect(3.2, 7.2, 3.7, 7.8), 6.3, 6.46, 0.08, M(53))


def nozzle():
    # a thin gasket closes the gun's open emitter at the joint (col 0 rows 9-10 are the sprite's ink,
    # so nothing else of the nozzle stands west of c 1 there); a feed pipe runs under the sill (row 8)
    loft_c("nozzle/end_plate", [(0.0, 9.45, 2.6, 1.55, 1.3), (0.05, 9.45, 2.6, 1.55, 1.3)], M(49), n=20, p=3.0,
           cap0=True, cap1=True)
    loft_c("nozzle/feed", [(0.05, 8.6, 2.55, 0.38, 0.5), (1.1, 8.6, 2.55, 0.38, 0.5)], M(49), n=12,
           cap0=False, cap1=True)
    # the nozzle's tail: a red charge ring (the sprite's 114 at row 10) and a dark neck into the collar
    Y = 10.45
    loft_c("nozzle/tail_ring", [(1.0, 10.0, 2.55, 0.97, 1.05), (1.14, 10.0, 2.55, 0.97, 1.05)], M(114), n=20, p=3.0,
           cap0=True, cap1=False)
    loft_c("nozzle/neck", [(1.14, 10.0, 2.55, 0.92, 1.0), (1.75, 10.1, 2.57, 0.98, 1.05),
                           (2.0, Y, 2.6, 1.3, 1.12)], M(49), n=20, p=3.0, cap0=True, cap1=False)

    def NZ(c, a, b):
        return (c, Y, 2.6, a, b)
    A = 1.55  # nozzle half-width: r 8.9-12.0, the sprite's rows 9-11 to their inner edge
    loft_c("nozzle/collar", [NZ(2.0, 1.3, 1.12), NZ(2.05, A + 0.03, 1.32), NZ(2.35, A + 0.03, 1.32)], M(55), n=24,
           p=2.6, cap0=True, cap1=False)
    loft_c("nozzle/body", [NZ(2.35, A, 1.28), NZ(3.2, A, 1.28)], M(57), n=24, p=2.6, cap0=False, cap1=False)
    loft_c("nozzle/band", [NZ(3.2, A, 1.28), NZ(3.25, A + 0.05, 1.34), NZ(3.55, A + 0.05, 1.34), NZ(3.6, A, 1.28)],
           M(56), n=24, p=2.6, cap0=False, cap1=False)
    loft_c("nozzle/body", [NZ(3.6, A, 1.28), NZ(4.5, A, 1.28)], M(57), n=24, p=2.6, cap0=False, cap1=False)
    rings = loft_c("nozzle/crown", [NZ(4.5, A, 1.28), NZ(4.55, A - 0.05, 1.22), NZ(4.9, A - 0.05, 1.22),
                                    NZ(4.95, A - 0.2, 1.08)], M(55), n=24, p=2.6, cap0=False, cap1=False)
    # bored tip: lip, dark bore wall, red charge at the bottom
    B.part("nozzle/crown")
    lip = ring_c(4.95, Y, 2.6, 0.85, 0.68, 24, 2.6)
    bridge(rings[-1], lip, M(55), (4.0, Y, 2.6))
    B.part("nozzle/bore")
    deep = ring_c(4.35, Y, 2.6, 0.85, 0.68, 24, 2.6)
    bridge(lip, deep, M(48), (4.65, Y, 2.6 + 5.0))
    B.part("nozzle/bore_glow")
    B.f(deep, M(114), out=(1, 0, 0))
    # side slots in the crown
    for r, s in ((Y + A - 0.07, 1), (Y - A + 0.07, -1)):
        prism("nozzle/slot", rect(4.62, min(r, r + 0.06 * s), 4.88, max(r, r + 0.06 * s)), 2.1, 3.1, 0, M(48))


def build():
    global B
    coll = common.reset_collection(NAME)
    B = Builder()
    brake()
    housing()
    nozzle()
    # bore walls face their bore's axis (inside a tube): re-point their hints at the axis
    P = B.P
    hints = []
    for face, out, away in P.hints:
        if not face.is_valid:
            continue
        pid = PARTS[face[B.layer]]
        if pid in ("brake/bore", "nozzle/bore") and len(face.verts) == 4:
            c = face.calc_center_median()
            axis = (4.0, 4.45) if pid == "brake/bore" else (10.45, 2.6)
            q = Builder._p(0.0, *axis)
            out, away = (0.0, q[1] - c.y, q[2] - c.z), None
        hints.append((face, out, away))
    P.hints = hints
    obj = T.finish(P, MATS, coll)
    return obj, coll


def open_shell_west(shell):
    """Drop the shell's faces on the joint face (no ink across the seam with the gun)."""
    xw = (0.0 - 6.0) / 12
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.normal_update()
    dead = [f for f in bm.faces if f.calc_center_median().x < xw + 0.02 and f.normal.x < -0.5]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()
    return len(dead)


def main():
    global SPRITE
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    SPRITE = load_sprite()
    obj, coll = build()
    shell = common.outline_shell(obj, coll, voxel=0.006, faces=1500, smooth=4, inside=0.006)
    n_open = open_shell_west(shell)
    T.cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    obj.data.calc_loop_triangles()
    print(f"newshc-275: {len(obj.data.loop_triangles)} triangles, outline {len(shell.data.polygons)} faces "
          f"({n_open} opened at the joint)")
    common.export_sprite_model(WT, [obj, shell], "enemies/" + NAME, SPRITE["sprites"])
    if "--render" in argv:
        sys.path.insert(0, str(HERE))
        import render_A
        render_A.render_all(obj, shell, Path(argv[argv.index("--render") + 1]), SPRITE, PARTS)


if __name__ == "__main__":
    main()
