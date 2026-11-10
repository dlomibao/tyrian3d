"""Big blue rifle (newshc.shp 239 | 241 | 243 plus its muzzle tip 238).

A heavy gun unit that slides across the terrain on its plinth (ev19 moves the four units together),
the mirror twin of assembly-newshc-271 (D121): the same machine with the muzzle at the WEST end.
Geometry follows the blueprint (tyrian-scratch/e1-enemies-3/assembly-newshc-243/blueprint), which
writes the shared machine in the twin's frame (c_twin, muzzle east) and mirrors it, c = 72 - c_twin;
the parts that differ from the twin (the plinth's bevelled side rails, the tip) are written in
assembly columns. Units: sprite px of the whole rifle, c east (-12..72; the tip unit is -12..0),
r down the screen 0-28, h up from the ground (the underside of the purple plinth).

Engineering read, cross-sections first:
- STOCK (newshc-243, c 48-72): pressure tank on axis r 6.5 / h 4.5, radius 3.5, ellipsoidal head
  to the east, weld bead, two straps with closing lugs, spigot into the butt block; the boom (round
  tube r 11.5, radius 1.5, a bulb at the outer end) over the finned radiator; the butt block where
  both plug into the receiver (tallest stock part, h 8 with a clamp band to 8.45).
- RECEIVER (newshc-241, c 24-48): rear body (h 6.4) with a recessed breech step and a breech bolt,
  a raised top cover (7.2); the sight housing (h 9, the gun's crown) with a recessed window and a
  lens tube; the fore bracket and rail rod; the grip lying on the plinth; the purple plinth deck
  (h 1.4) with bevelled side rails, a lower apron toward the player and bolts.
- BARREL (newshc-239, c 0-24): shroud (axis h 4.6, radius 2.5) with groove and lip, two flared
  sleeves either side of a ring collar, the muzzle block (h 7.4, step 6.0), the under-barrel frame
  and the glowing charge emitter under the muzzle.
- TIP (newshc-238, c -12..0): the rounded nose of the muzzle block, its lower step and the blue
  nozzle the emitter fires through. Cut from the same build so it lines up.

Every solid is closed (the unit moves: no open shells, flat closed underside). Colours are each
region's palette index (median of the sprite, lighting left out).

Run: blender --background --python assets/blender/enemies/assembly-newshc-243.py [-- --render <dir>]
Exports the four units (newshc-239/241/243 and the muzzle tip newshc-238, each with its outline
shell) as enemies/<unit> plus their src/render/spriteModels entries; newshc-238.py defers to this.
--render <dir> (scratch only) also writes the review renders via render_A.py found in $TYRIAN_REVIEW_DIR.
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "enemies")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = WT
NAME = "assembly-newshc-243"
PIECES = ["newshc-239", "newshc-241", "newshc-243"]
TIP = "newshc-238"
CX0, CY0 = 218, -18  # screen centre of newshc-241 = the rifle's centre = Blender origin
Z0 = 3.6  # px: as the twin (and assembly-newshc-197), so the pair stands at the same height
TAG = "nshc243"
# newshc-238's 12 x 14 tile: columns -12..-1, rows 0-13 (the old lib_b058 MUZZLE_BOX)
TIP_BOX = ((-6 - 36) / 12, (14 - 7) / 12, 6 / 12, 7 / 12)

SPRITE = None
MATS = []
MAT_IDX = {}
PARTS = []
PART_IDX = {}
FINISH = {
    "metal": dict(metallic=0.55, roughness=0.42),
    "dark": dict(metallic=0.35, roughness=0.55),
    "plate": dict(metallic=0.25, roughness=0.6),  # the purple plinth: painted armour
    "rim": dict(metallic=0.2, roughness=0.5, emission_strength=1.2),
    "glow": dict(metallic=0.0, roughness=0.5, emission_strength=3.0),
    "hot": dict(metallic=0.0, roughness=0.5, emission_strength=6.0),
}


def load_sprite():
    d = common.load_sprite(WT, PIECES[0])
    for p in PIECES[1:] + [TIP]:
        d["colors"].update(common.load_sprite(WT, p)["colors"])
    d["name"] = NAME
    return d


def M(idx, finish=None):
    if finish is None:
        finish = "plate" if 80 <= idx <= 91 else ("dark" if idx in (48, 49, 50, 1, 2, 3, 4) else "metal")
    key = (idx, finish)
    if key not in MAT_IDX:
        MAT_IDX[key] = len(MATS)
        MATS.append(common.palette_material(SPRITE, idx, f"{TAG}-{finish}", **FINISH[finish]))
    return MAT_IDX[key]


MIRROR = True  # True: c is the twin's column (c_twin); the builder writes 72 - c


def mx(c):
    return 72.0 - c if MIRROR else c


class Builder:
    """T.Part plus a per-face part id; c mirrored while MIRROR is on."""

    def __init__(self):
        self.P = T.Part(NAME, smooth_angle=35.0)
        self.layer = self.P.bm.faces.layers.int.new("part")
        self.cur = 0

    def part(self, name):
        if name not in PART_IDX:
            PART_IDX[name] = len(PARTS)
            PARTS.append(name)
        self.cur = PART_IDX[name]

    def v(self, c, r, h):
        return self.P.v((mx(c) - 36.0, r, h))

    def f(self, verts, mat, out=None, away=None):
        if away is not None:
            away = (mx(away[0]) - 36.0, away[1], away[2])
        if out is not None and MIRROR:
            out = (-out[0], out[1], out[2])
        face = self.P.f(verts, mat, out=out, away=away)
        if face is not None:
            face[self.layer] = self.cur
        return face


B = None


# ----------------------------------------------------------------------------------------------
# Geometry primitives (sprite px: c, r, h)
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
        mx_, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx_) * nx + (cy - my) * ny < 0:
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
    """Chamfered prism over a convex plan polygon: vertical sides h0..h1-ch, 45-degree chamfer,
    flat top. `top`, `side`, `cham` are material slots."""
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


def ramp(name, c0, c1, r0, r1, h0, h1, top, side):
    """Closed block over c0..c1 x r0..r1 whose top slopes across c (h0 at c0, h1 at c1)."""
    B.part(name)
    sec = [(c0, 0.0), (c1, 0.0), (c1, h1), (c0, h0)]
    A = [B.v(c, r0, h) for c, h in sec]
    Bv = [B.v(c, r1, h) for c, h in sec]
    cen = ((c0 + c1) / 2, (r0 + r1) / 2, (h0 + h1) / 4)
    for i in range(4):
        j = (i + 1) % 4
        B.f((A[i], A[j], Bv[j], Bv[i]), top if i == 2 else side, away=cen)
    B.f(A, side, away=cen)
    B.f(Bv, side, away=cen)


def section(n, p=2.0):
    out = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        co, si = math.cos(t), math.sin(t)
        out.append((math.copysign(abs(co) ** (2 / p), co), math.copysign(abs(si) ** (2 / p), si)))
    return out


def _loft(name, rings_pts, centres, mats, cap0, cap1, axis):
    """rings_pts[i]: list of (c, r, h) or a single point (tip)."""
    B.part(name)
    rings = [[B.v(*q) for q in pts] for pts in rings_pts]
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        m = mats[i] if isinstance(mats, (list, tuple)) else mats
        cen = tuple((centres[i][k] + centres[i + 1][k]) / 2 for k in range(3))
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for j in range(len(b)):
                B.f((a[0], b[j], b[(j + 1) % len(b)]), m, away=cen)
        elif len(b) == 1:
            for j in range(len(a)):
                B.f((a[j], b[0], a[(j + 1) % len(a)]), m, away=cen)
        else:
            for j in range(len(a)):
                k = (j + 1) % len(a)
                B.f((a[j], a[k], b[k], b[j]), m, away=cen)
    m0 = mats[0] if isinstance(mats, (list, tuple)) else mats
    m1 = mats[-1] if isinstance(mats, (list, tuple)) else mats
    d = [centres[-1][k] - centres[0][k] for k in range(3)]
    s = 1 if d[axis] >= 0 else -1
    o0 = [0, 0, 0]
    o0[axis] = -s
    o1 = [0, 0, 0]
    o1[axis] = s
    if cap0 and len(rings[0]) > 1:
        B.f(rings[0], m0, out=tuple(o0))
    if cap1 and len(rings[-1]) > 1:
        B.f(rings[-1], m1, out=tuple(o1))


def loft_c(name, stations, mats, n=20, p=2.0, cap0=True, cap1=True):
    """A tube along c through stations (c, r, h, a, b): a half width across r, b half height."""
    sec = section(n, p)
    pts, cens = [], []
    for c, r, h, a, b in stations:
        cens.append((c, r, h))
        if a <= 1e-6 and b <= 1e-6:
            pts.append([(c, r, h)])
        else:
            pts.append([(c, r + u * a, h + v * b) for u, v in sec])
    _loft(name, pts, cens, mats, cap0, cap1, 0)


def loft_r(name, stations, mats, n=16, p=4.0, cap0=True, cap1=True):
    """A tube along r through stations (r, c, h, a, b): a half width across c."""
    sec = section(n, p)
    pts, cens = [], []
    for r, c, h, a, b in stations:
        cens.append((c, r, h))
        pts.append([(c + u * a, r, h + v * b) for u, v in sec])
    _loft(name, pts, cens, mats, cap0, cap1, 1)


def hullp(name, pts, mat):
    B.part(name)
    before = len(B.P.hints)
    T.hull(B.P, [(mx(c) - 36.0, r, h) for c, r, h in pts], mat)
    for face, _o, _a in B.P.hints[before:]:
        if face.is_valid:
            face[B.layer] = B.cur


# ----------------------------------------------------------------------------------------------
# STOCK (newshc-243; c_twin 0-24 = c 48-72): pressure tank, boom, radiator, butt block
# ----------------------------------------------------------------------------------------------
TY, TZ, TR = 6.5, 4.5, 3.5


def stock():
    def seg(name, idx, lst, cap0=False, cap1=False, n=36):
        loft_c(name, [(c, TY, TZ, rr, rr) for c, rr in lst], M(idx), n=n, cap0=cap0, cap1=cap1)

    head = [(1.0 + 6.0 * t, TR * math.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2)))
            for t in (0.0, 0.004, 0.02, 0.05, 0.1, 0.17, 0.26, 0.37, 0.5, 0.64, 0.78, 0.9, 1.0)]
    seg("tank/head", 8, head)
    seg("tank/weld", 7, [(7.0, TR), (7.15, TR + 0.12), (7.35, TR + 0.12), (7.5, TR)])
    seg("tank/shell", 8, [(7.5, TR), (15.96, TR)])
    for c0 in (16.0, 18.0):
        seg("tank/strap", 4, [(c0 - 0.04, TR), (c0 + 0.18, TR + 0.22), (c0 + 0.8, TR + 0.22), (c0 + 1.02, TR)])
        seg("tank/shell", 8, [(c0 + 1.02, TR), (c0 + 1.96, TR)])
        for r0, r1 in ((TY + 2.0, TY + 3.3), (TY - 3.3, TY - 2.0)):
            prism("tank/lug", rect(c0 + 0.08, r0, c0 + 0.88, r1), TZ - TR - 0.5, TZ - TR + 1.0, 0.15, M(4))
    seg("tank/spigot", 8, [(19.98, TR), (20.05, TR), (20.35, 2.95), (21.6, 2.95)], cap1=True)
    loft_c("tank/filler", [(c, TY, TZ, rr, rr) for c, rr in ((0.95, 0.0), (1.0, 0.35), (1.1, 0.5), (1.5, 0.55), (1.9, 0.5))],
           M(6), n=12)
    prism("saddle", rect(1.0, 7.7, 5.4, 10.8), 0.7, 4.3, 0.4, M(4))
    prism("saddle", rect(1.6, 3.6, 5.0, 7.8), 0.7, 2.3, 0.35, M(4))
    loft_c("feed", [(5.2, 4.0, 1.7, 0.5, 0.5), (21.4, 4.0, 1.7, 0.5, 0.5)], M(53), n=12)
    for c in (9.0, 14.0):
        prism("feed/clamp", rect(c, 3.3, c + 0.6, 4.7), 1.0, 2.4, 0.12, M(4))

    # BOOM: bulb at the outer end, tube r 11.5 radius 1.5, necking under the butt block
    zc, by, bh = 3.0, 12.55, 2.45
    st = []
    for t in (0.0, 0.03, 0.1, 0.2, 0.33, 0.5, 0.68, 0.85, 1.0):
        s = math.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2))
        st.append((1.0 + 2.6 * t, by, zc, bh * s, 1.05 * bh * s))
    st[0] = (1.0, by, zc, 0.0, 0.0)
    st.append((4.2, by, zc, bh, bh * 1.05))
    loft_c("boom/bulb", st, M(55), n=32, cap1=False)
    loft_c("boom/band", [(4.2, by, zc, bh, bh * 1.05), (4.3, by, zc, bh + 0.14, (bh + 0.14) * 1.05),
                         (4.7, by, zc, bh + 0.14, (bh + 0.14) * 1.05), (4.8, by, zc, bh, bh * 1.05)],
           M(58), n=32, cap0=False, cap1=False)
    cs = [4.8, 7.0, 7.4, 7.8, 8.2, 8.6, 8.9, 12.0, 17.3, 17.9, 18.5, 18.8, 22.75]
    fy = T.pchip([4.8, 7.0, 8.9, 17.3, 18.8, 22.75], [by, by, 11.5, 11.5, 11.0, 11.0])
    fh = T.pchip([4.8, 7.0, 8.9, 17.3, 18.8, 22.75], [bh, bh, 1.5, 1.5, 1.0, 1.0])
    loft_c("boom/tube", [(c, fy(c), zc, fh(c), fh(c) * 1.05) for c in cs], M(56), n=32, cap0=False)
    loft_c("boom/collar", [(c, 11.5, zc, rr, rr * 1.05) for c, rr in ((8.75, 1.45), (8.85, 1.7), (9.45, 1.7), (9.55, 1.45))],
           M(54), n=32)
    loft_c("boom/coupling", [(22.7, 11.0, zc, 0.8, 0.8), (26.8, 11.0, zc, 0.8, 0.8)], M(53), n=16)

    # RADIATOR under the boom
    prism("rad/body", rect(7.7, 12.9, 19.0, 18.95), 0.4, 1.8, 0.2, M(49))
    prism("rad/body", rect(6.9, 12.9, 8.0, 16.0), 0.4, 1.8, 0.2, M(49))
    prism("rad/body", rect(18.9, 12.9, 21.0, 18.0), 0.4, 1.8, 0.2, M(49))
    prism("rad/header", rect(8.0, 12.95, 21.0, 13.95), 1.7, 2.05, 0.1, M(48))

    def rib(name, c0, c1, r0, r1, top, idx):
        c, a, z, b = (c0 + c1) / 2, (c1 - c0) / 2, 1.6, top - 1.6
        loft_r(name, [(r0, c, z, a, b), (r1 - 0.35, c, z, a, b), (r1 - 0.12, c, z - 0.08, a * 0.93, b * 0.9),
                      (r1, c, z - 0.2, a * 0.8, b * 0.72)], M(idx), n=16, p=4.0)
    rib("rad/plate", 8.95, 12.0, 13.9, 18.95, 2.65, 51)
    rib("rad/fin", 13.05, 13.95, 13.9, 19.3, 2.55, 52)
    rib("rad/fin", 15.05, 15.95, 13.9, 18.95, 2.55, 52)
    rib("rad/fin", 17.05, 17.95, 13.9, 18.95, 2.55, 52)
    rib("rad/fin", 19.0, 20.0, 13.9, 18.0, 2.55, 52)
    rib("rad/wall", 20.0, 20.95, 13.9, 18.0, 2.45, 52)
    for c in (12.0, 14.0, 16.0, 18.0):
        prism("rad/slot", rect(c + 0.02, 13.95, c + 1.02, 18.9), 1.75, 1.9, 0.0, M(48))
    for c in (9.4, 16.4):
        prism("rad/hanger", rect(c, 12.3, c + 1.2, 13.7), 1.6, 3.2, 0.2, M(50))
    prism("rad/neck", rect(18.1, 11.4, 21.0, 14.0), 0.6, 3.3, 0.25, M(48))
    prism("rad/neck", rect(20.8, 11.4, 22.0, 13.0), 0.6, 3.0, 0.2, M(48))

    # BUTT BLOCK where the spigot and the boom plug into the receiver
    prism("butt/block", [(20.4, 2.0), (26.2, 2.0), (26.2, 10.0), (20.9, 10.0), (20.4, 9.4)], 0.6, 8.0, 0.5,
          M(57), side=M(56), cham=M(58))
    prism("butt/band", rect(20.6, 6.0, 26.0, 7.0), 7.6, 8.45, 0.25, M(59), side=M(58))
    for r in (3.4, 8.6):
        prism("butt/bolt", rect(22.9, r - 0.3, 23.5, r + 0.3), 7.85, 8.2, 0.1, M(58))
    prism("butt/slot", rect(22.4, 9.6, 24.6, 10.4), 2.4, 5.6, 0.0, M(50))


# ----------------------------------------------------------------------------------------------
# PLINTH (newshc-241): the purple armoured sled the gun is bolted to. Deck in the twin's frame;
# the bevelled side rails in assembly columns (plinth_rails).
# ----------------------------------------------------------------------------------------------

def plinth():
    # The c range stops 0.02 px inside the seams (c 24/48): bisect keeps faces lying on the cut
    # plane, so end walls flush with a seam leak into the next piece (D121).
    prism("plinth/deck", rect(24.02, 1.0, 47.98, 25.0), 0.0, 1.4, 0.3, M(87), side=M(86))
    prism("plinth/ear", rect(24.02, 0.0, 33.0, 1.3), 0.0, 1.4, 0.3, M(87), side=M(86))
    prism("plinth/earW", rect(43.0, 0.0, 47.98, 1.3), 0.0, 1.45, 0.3, M(88))
    prism("plinth/apron", [(24.02, 24.9), (47.98, 24.9), (47.98, 28.0), (25.25, 28.0), (24.02, 26.75)], 0.0, 1.0, 0.25,
          M(83), side=M(82))
    for c, r in ((25.0, 0.7), (31.8, 0.7), (44.4, 0.7), (47.2, 0.7), (25.4, 26.0), (47.2, 26.0)):
        prism("plinth/bolt", rect(c - 0.35, r - 0.3, c + 0.35, r + 0.3), 1.3, 1.75, 0.12, M(89))


def plinth_rails():
    """Assembly columns. Each side of the plinth is a bright edge strip with a bevel sloping from
    it down to the deck (purple 85/87 at the edge, darker 82/83 inward)."""
    prism("plinth/railW", rect(24.02, 14.8, 26.0, 25.0), 0.0, 1.95, 0.3, M(85), side=M(84), cham=M(87))
    ramp("plinth/bevelW", 26.0, 29.2, 14.9, 25.0, 1.85, 1.42, M(83), M(82))
    ramp("plinth/bevelE", 42.9, 46.0, 13.4, 25.0, 1.42, 1.85, M(82), M(81))
    prism("plinth/railE", rect(46.0, 13.0, 47.98, 25.0), 0.0, 1.95, 0.3, M(85), side=M(84), cham=M(87))
    for r in (16.5, 23.0):
        prism("plinth/railbolt", rect(24.65, r - 0.3, 25.35, r + 0.3), 1.85, 2.2, 0.12, M(89))
        prism("plinth/railbolt", rect(46.65, r - 0.3, 47.35, r + 0.3), 1.85, 2.2, 0.12, M(89))


# ----------------------------------------------------------------------------------------------
# RECEIVER, SIGHT, FORE RAIL, GRIP (twin frame)
# ----------------------------------------------------------------------------------------------

def receiver():
    prism("recv/rear", [(26.2, 3.0), (33.4, 3.0), (33.4, 13.0), (26.8, 13.0), (26.2, 12.4)], 1.2, 6.4, 0.55,
          M(52), side=M(51), cham=M(54))
    # breech step: a recessed darker face in the rear body's top, with the breech bolt lying in it
    prism("recv/breech", rect(26.3, 4.9, 29.9, 9.9), 4.9, 6.42, 0.15, M(50))
    loft_c("recv/bolt", [(26.6, 7.4, 6.2, 0.0, 0.0), (26.7, 7.4, 6.2, 0.9, 0.6), (29.4, 7.4, 6.2, 0.9, 0.6),
                         (29.5, 7.4, 6.2, 0.0, 0.0)], M(52), n=12)
    prism("recv/cover", rect(29.95, 3.0, 33.9, 6.95), 6.0, 7.2, 0.35, M(56), side=M(55))
    prism("recv/mid", rect(33.4, 6.9, 39.0, 13.0), 1.2, 6.2, 0.45, M(52), side=M(51))
    prism("recv/seam", rect(33.25, 7.0, 33.55, 12.8), 5.8, 6.25, 0.0, M(50))
    prism("recv/trigger", rect(33.9, 12.8, 38.0, 14.0), 1.2, 4.2, 0.3, M(50))
    for k in range(3):  # cooling louvres on the south face (game camera side)
        h = 2.3 + k * 1.15
        prism("recv/louvre", rect(27.6, 12.85, 32.6, 13.25), h, h + 0.5, 0.1, M(49))
    loft_c("recv/rail", [(26.4, 11.0, 3.6, 1.0, 1.6), (33.2, 11.0, 3.6, 1.0, 1.6)], M(53), n=16, p=3.0)

    # SIGHT: the tallest part
    prism("sight/housing", rect(34.0, 1.0, 42.0, 7.0), 3.0, 9.0, 0.5, M(57), side=M(56), cham=M(58))
    prism("sight/frame", rect(35.6, 3.6, 41.0, 6.2), 8.75, 9.05, 0.1, M(57))
    prism("sight/window", rect(36.0, 3.95, 40.7, 5.95), 8.75, 9.1, 0.0, M(55))
    loft_c("sight/lens", [(41.9, 4.2, 7.0, 1.1, 1.1), (42.6, 4.2, 7.0, 1.1, 1.1), (42.7, 4.2, 7.0, 0.8, 0.8)],
           [M(56), M(48)], n=16)
    hullp("sight/cheek", [(34.0, 7.0, 6.6), (42.0, 7.0, 6.6), (42.0, 9.0, 4.4), (34.0, 9.0, 4.4),
                          (34.0, 7.0, 3.0), (42.0, 7.0, 3.0), (34.0, 9.0, 3.0), (42.0, 9.0, 3.0)], M(53))
    for c in (34.9, 41.1):
        prism("sight/bolt", rect(c - 0.3, 1.6, c + 0.3, 2.2), 8.8, 9.25, 0.1, M(58))

    # FORE BRACKET and rail rod with a round tip
    prism("fore/bracket", [(39.0, 8.0), (45.0, 8.0), (46.0, 9.0), (46.0, 12.0), (39.0, 12.0)], 1.4, 4.6, 0.35,
          M(54), side=M(53))
    st = []
    for c in (38.9, 47.0, 48.0, 48.8, 49.4, 49.85, 50.0):
        k = 1.0 if c <= 48.0 else math.sqrt(max(0.0, 1.0 - ((c - 48.0) / 2.0) ** 2))
        st.append((c, 12.95, 2.4, 0.95 * k, 1.0 * k))
    st[-1] = (50.0, 12.95, 2.4, 0.0, 0.0)
    loft_c("fore/rod", st, M(54), n=16)
    loft_c("fore/band", [(44.0, 12.95, 2.4, 1.05, 1.1), (44.6, 12.95, 2.4, 1.05, 1.1)], M(55), n=16)

    # GRIP lying on the plinth
    prism("grip/mag", rect(30.6, 13.0, 39.0, 21.0), 1.4, 4.4, 0.4, M(50), side=M(49))
    loft_r("grip/back", [(13.6, 31.4, 3.0, 1.45, 1.7), (23.3, 31.4, 3.0, 1.45, 1.7), (23.95, 31.4, 2.9, 1.2, 1.4)],
           M(54), n=16, p=3.0)
    prism("grip/foot", rect(32.4, 20.9, 42.0, 24.0), 1.4, 3.8, 0.35, M(51), side=M(50))
    prism("grip/front", rect(39.9, 14.4, 42.0, 21.0), 1.4, 4.0, 0.3, M(51), side=M(50))
    prism("grip/slot", rect(39.0, 13.4, 39.9, 20.6), 1.4, 2.8, 0.0, M(48))
    for r in (15.5, 17.5):
        prism("grip/rib", rect(33.2, r, 38.2, r + 0.5), 4.2, 4.6, 0.1, M(51))
    for c in (34.0, 40.4):  # foot plate's south face: two screws
        loft_r("grip/screw", [(23.9, c, 2.6, 0.0, 0.0), (24.0, c, 2.6, 0.35, 0.35), (24.25, c, 2.6, 0.35, 0.35)],
               M(52), n=10, p=2.0)


# ----------------------------------------------------------------------------------------------
# BARREL, MUZZLE, UNDER-BARREL FRAME, EMITTER (twin frame: c_twin 42-72 = c 0-30)
# ----------------------------------------------------------------------------------------------
BR, BZ = 5.5, 4.6


def barrel():
    def S(c, a, b=None):
        return (c, BR, BZ, a, a * 1.05 if b is None else b)
    loft_c("barrel/shroud", [S(41.8, 2.5), S(49.6, 2.5)], M(55), n=36, p=2.6, cap1=False)
    loft_c("barrel/groove", [S(49.6, 2.5), S(49.7, 2.2), S(50.5, 2.2), S(50.6, 2.5)], M(52), n=36, p=2.6,
           cap0=False, cap1=False)
    loft_c("barrel/lip", [S(50.6, 2.5), S(52.9, 2.5), S(53.0, 2.0)], M(56), n=36, p=2.6, cap0=False)
    loft_c("barrel/sleeve", [S(52.9, 1.35), S(55.5, 1.45), S(56.9, 1.6)], M(55), n=32, cap0=False, cap1=False)
    loft_c("barrel/ring", [S(56.9, 1.6), S(57.0, 2.45), S(59.9, 2.45), S(60.0, 1.35)], M(55), n=36,
           cap0=False, cap1=False)
    loft_c("barrel/sleeve", [S(60.0, 1.35), S(62.6, 1.45), S(64.6, 1.6)], M(55), n=32, cap0=False, cap1=False)
    loft_c("barrel/sleevelip", [S(64.6, 1.6), S(64.7, 1.75), S(65.9, 1.75), S(66.0, 1.6)], M(58), n=32,
           cap0=False, cap1=False)
    loft_c("barrel/collar", [S(66.0, 1.6), S(66.05, 2.4), S(66.9, 2.4), S(67.0, 1.8)], M(57), n=36, cap0=False)
    for c in (57.7, 59.0):  # machined grooves round the ring collar
        loft_c("barrel/ringgroove", [S(c, 2.45), S(c + 0.05, 2.52), S(c + 0.25, 2.52), S(c + 0.3, 2.45)], M(57), n=36,
               cap0=False, cap1=False)
    for c in (55.4, 62.0):  # clamp straps where the frame shoes grip the sleeves
        loft_c("barrel/strap", [S(c, 1.62), S(c + 0.05, 1.72), S(c + 0.95, 1.72), S(c + 1.0, 1.62)], M(56), n=32,
               cap0=False, cap1=False)
    # MUZZLE block: runs 0.3 px past the tip seam (c 0) so the cut caps it and the nose overlaps it
    prism("muzzle/upper", rect(66.95, 2.0, 72.3, 6.0), 2.2, 7.4, 0.5, M(57), side=M(56), cham=M(58))
    prism("muzzle/lower", rect(67.4, 5.9, 71.98, 8.0), 2.2, 6.0, 0.4, M(51), side=M(50))
    prism("muzzle/groove", rect(67.6, 2.4, 67.95, 7.9), 7.0, 7.45, 0.0, M(52))
    for r in (3.2, 4.8):
        prism("muzzle/bolt", rect(70.3, r - 0.3, 70.9, r + 0.3), 7.2, 7.55, 0.1, M(59))
    # UNDER-BARREL FRAME
    prism("frame/shoe", rect(54.0, 6.6, 58.0, 8.0), 2.2, 3.4, 0.25, M(57), side=M(54))
    prism("frame/post", rect(55.0, 7.9, 58.0, 11.1), 1.4, 3.2, 0.25, M(55), side=M(54))
    prism("frame/shoe", rect(61.0, 6.6, 64.0, 8.0), 2.2, 3.4, 0.25, M(57), side=M(54))
    prism("frame/post", rect(62.0, 7.9, 64.0, 11.1), 1.4, 3.2, 0.25, M(55), side=M(54))
    prism("frame/gusset", rect(61.0, 9.9, 62.2, 11.1), 1.2, 2.8, 0.15, M(52))
    prism("frame/rail", rect(55.0, 11.0, 67.0, 12.0), 1.2, 2.8, 0.2, M(52))
    prism("frame/foot", rect(56.0, 11.9, 58.0, 12.95), 0.6, 2.2, 0.2, M(52))
    prism("frame/foot", rect(62.0, 11.9, 66.0, 12.95), 0.6, 2.2, 0.2, M(52))
    prism("frame/mount", rect(63.9, 6.6, 66.2, 11.0), 1.2, 4.0, 0.3, M(52), side=M(50))
    # EMITTER under the muzzle: a sleeve (rim 117) round a glowing lens (119) with a hot core (125);
    # closed 0.02 px short of the tip seam (a cap ON the cut plane leaks into newshc-238, D121)
    loft_c("emit/rim", [(66.0, 9.45, 2.6, 1.55, 1.3), (71.98, 9.45, 2.6, 1.55, 1.3)], M(117, "rim"), n=20, p=3.0)
    loft_c("emit/lens", [(66.3, 9.35, 3.2, 1.15, 0.85), (71.98, 9.35, 3.2, 1.15, 0.85)], M(119, "glow"), n=16)
    loft_c("emit/core", [(66.6, 9.2, 3.75, 0.0, 0.0), (66.8, 9.2, 3.75, 0.75, 0.5), (68.2, 9.2, 3.75, 0.75, 0.5),
                         (68.6, 9.2, 3.75, 0.0, 0.0)], M(125, "hot"), n=12)


# ----------------------------------------------------------------------------------------------
# TIP (newshc-238, assembly columns -5..0): nose of the muzzle block, its step, the nozzle
# ----------------------------------------------------------------------------------------------

def tip():
    nose = [(0.1, 1.0), (-2.5, 1.0), (-3.2, 0.97), (-3.65, 0.9), (-3.9, 0.78), (-4.02, 0.62)]
    loft_c("tip/nose", [(c, 4.0, 4.8, 2.0 * k, 2.6 * (0.55 + 0.45 * k)) for c, k in nose],
           [M(57)] * (len(nose) - 2) + [M(55)], n=28, p=4.0)
    loft_c("tip/band", [(c, 4.0, 4.8, a * 0.8, a * 1.04) for c, a in ((-2.45, 2.5), (-2.4, 2.62), (-1.9, 2.62), (-1.85, 2.5))],
           M(59), n=28, p=4.0, cap0=False, cap1=False)
    prism("tip/step", [(0.1, 6.9), (0.1, 8.9), (-3.5, 8.9), (-4.0, 8.5), (-4.0, 7.0), (-3.5, 6.45), (-1.0, 6.45)], 2.2, 6.0, 0.4,
          M(54), side=M(53))
    loft_c("tip/neck", [(0.15, 10.5, 2.6, 0.16, 0.3), (-1.25, 10.5, 2.6, 0.16, 0.3)], M(51), n=16)
    nz = [(-1.2, 1.0), (-3.3, 1.0), (-3.7, 0.9), (-3.95, 0.7), (-4.02, 0.5)]
    loft_c("tip/nozzle", [(c, 10.5, 2.6, 1.5 * k, 1.35 * k) for c, k in nz], [M(57)] * (len(nz) - 2) + [M(55)],
           n=20, p=2.4)
    loft_c("tip/bore", [(-3.98, 10.5, 2.6, 0.45, 0.4), (-4.06, 10.5, 2.6, 0.45, 0.4)], M(48), n=12)


# ----------------------------------------------------------------------------------------------
# Build, split, export
# ----------------------------------------------------------------------------------------------

def build():
    global B, MIRROR
    coll = common.reset_collection(NAME)
    B = Builder()
    MIRROR = True
    stock()
    plinth()
    receiver()
    barrel()
    MIRROR = False
    plinth_rails()
    tip()
    obj = T.finish(B.P, MATS, coll)
    obj.data.transform(Matrix.Translation((0, 0, -Z0 / 12)))
    return obj, coll


def cut(obj, name, x0, y0, hw, hh, coll, cap=True):
    """split_assembly's cut for one box of any size (centre x0, y0, half sizes hw, hh, Blender
    units); cap=False leaves the cut open (outline shells: no ink line along the seams)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                   ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                     clear_outer=True)
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if cap and edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in obj.data.materials:
        me.materials.append(mt)
    out = bpy.data.objects.new(name, me)
    coll.objects.link(out)
    return out


def units():
    """[(unit, x0, y0, hw, hh)] in Blender units relative to the origin."""
    data0 = common.load_sprite(ROOT, PIECES[0])
    out = [(e["model"], (e["cx"] - CX0) / 12, -(e["cy"] - CY0) / 12, 1.0, 14 / 12)
           for e in data0["assemblyLayout"] if e["model"] in PIECES]
    out.append((TIP, *TIP_BOX))
    return out


def finish_piece(pc):
    pc.data.shade_smooth()
    pc.data.set_sharp_from_angle(angle=math.radians(35.0))
    wn = pc.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(pc)


def main():
    global SPRITE
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    SPRITE = load_sprite()
    obj, coll = build()
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=7000, smooth=6, inside=0.01)
    T.cull_hidden(obj)
    finish_piece(obj)
    out_objs, placed = [], {}
    total = 0
    for name, x0, y0, hw, hh in units():
        pc = cut(obj, name, x0, y0, hw, hh, coll)
        sh = cut(shell, f"{name}_outline", x0, y0, hw, hh, coll, cap=False)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        finish_piece(pc)
        common.export_sprite_model(ROOT, [pc, sh], f"enemies/{name}", common.load_sprite(ROOT, name)["sprites"])
        pc.data.calc_loop_triangles()
        n = len(pc.data.loop_triangles)
        total += n
        print(f"piece {name}: {n} triangles, outline {len(sh.data.polygons)} faces")
        for o in (pc, sh):
            o.location = (x0, y0, 0)
        out_objs += [pc, sh]
        placed[name] = pc
    print(f"total triangles {total}")
    if "--render" in argv:
        sys.path.insert(0, os.environ.get("TYRIAN_REVIEW_DIR", str(HERE)))
        import render_A
        render_A.render_all(list(placed.values()), Path(argv[argv.index("--render") + 1]), SPRITE, PARTS,
                            [sh for sh in out_objs if sh.get("tyrian_outline")])


if __name__ == "__main__":
    main()
