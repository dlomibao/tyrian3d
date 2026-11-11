"""assembly-newshd-245, design B: the brown beetle pod under its dark hinge housing (newshd 245 over
281/283, one 24 x 56 px object at both ends of the middle rows of the fortress set, assembly-newshd-127).

Design B leads with the silhouette and the read from the small tilted game camera: three big,
clearly separated masses stepping UP toward the camera (dark drum, low hinge deck, brown pod), each
a pchip-stationed loft of superellipse arches, then machined detail where the camera looks.

Reading the sprite (tools/calibration/rubric.md, "Reading a sprite"; px: x = column edge, y = row
edge down the screen, z up; floor top 0.36 as lib_b073, so the fortress tiles meet):
- Rows 1-10, cols 4-16: a dark polished DRUM lying along the column, rounded rear end (rows 1-2
  narrower). Its lit streak (cols 6-9) and black right half are lighting; the dark col 10 next to
  the bright col 11 is a groove (its left wall away from the light, its right wall toward it): the
  seam between the drum's two half shells. Row 10-11 dark: the drum's front face.
- Rows 10-21, cols 4-17: the dark HINGE DECK (all ink-dark in the sprite: deep shade; steel 2).
  On it a red signal bar (row 12, 67) whose chamfered front shows as the dark-red row 13 (162),
  a grey cross-beam (rows 14-16, 5; the 12 at its top left is sheen) and two yoke cheeks (cols 4-6
  lit / 16-18 shaded, rows 14-19) holding the pod's pivot pin.
- Rows 20-27: the pod's HEAD PLATE (brown 21), a shield narrowing toward the deck (cols 7-13 at
  row 20, 4-16 at rows 23-26), a raised centre strip between two grooves (cols 9 and 12) and a
  transverse groove at row 24 in front of a raised collar (rows 25-27; row 25's lit 24-26 is the
  collar's rising edge catching the light).
- Rows 28-44, cols 1-19: the big round SHELL (brown 19/20): straight sides, round tail. A red
  STRAP (68-71) across its front shoulder (rows 28-31), its ends running down the sides further
  down-screen (rows 30-34 at cols 1-3): the strap leans back. In the strap, centred, a dark LAMP
  HOUSING (163, cols 8-12, rows 30-35) with a brown visor over it (rows 28-29) and two lenses: upper
  rows 30-31, lower rows 33-35 with rounded lower corners, a bar between (row 32). They glow on 281
  (118-124) and are dark pink glass on 283 (70-77). A bead down the shell's centre (col 10, rows
  36-43) between two grooves (cols 9, 11): the suture of the two wing cases.
- The black ring round all of it is the sprite's ink border: the game's ink outline (D74), so the
  plan goes to its inner edge (blueprint INNER spans, the hand trace: the tile is opaque stone).

Colours (trimmed median per region, measured by design B's measure.py): drum 4, deck 2, red bar 67,
beam/cheeks 5, head 21, head ridge 22, shell 20, strap 69, lamp housing 163, visor 21, seam bead 22;
lenses 119 / 72 (upper), 120 / 73 (lower) on 281 / 283 (the lit pair emissive, albedo tinted dark).

Hard surface (D50-D53, D65): lofts with chamfered superellipse sections stationed by pchip,
modelled grooves (cut into the section rings), a separate strap with thickness, a chamfered lamp
housing with proud lenses and a visor, a machined collar ring on the drum, bolted cheeks with pivot
hubs. No bake (no textures folder for this model), outline shell (D51). Underside: every part sits on
the ground, closed, no detail. The floor plate (painted per pixel from the sprite's stone, as
lib_b073) is still built but not exported (D129): the game draws the tile's ground in HD, and the
plate showed as grey pixel cells on it.

Built whole in the pair's coordinates (Blender Y = (28 - y) / 12, so the pair's centre is the origin) and
exported through lib_b073.run_assembly, which cuts it into the pieces newshd-245 and newshd-281: the
machine, the outline shell (D51; re-flagged after the cut) and the two frame parts
(lenses-281, lenses-283).

Run: blender --background --python assets/blender/enemies/assembly-newshd-245.py [-- --preview out.png]
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "assembly-newshd-245"
PIECES = [["newshd-245"], ["newshd-281"]]

W, H = 24, 56
FL = 0.36          # floor top (lib_b073 FLOOR = 0.03 units)
CX = 10.5          # centre column edge of the drum and the pod
X0 = 12.0          # column edge at Blender X = 0


# --- materials ----------------------------------------------------------------------------------
def composite_sprite():
    ref = WT / "reference" / "models"
    a = json.loads((ref / "newshd-245" / "sprite.json").read_text())
    b = json.loads((ref / "newshd-281" / "sprite.json").read_text())
    colors = dict(a["colors"])
    colors.update(b["colors"])
    rows = lambda f: [[int(v) for v in r.split()] for r in f["pixels"]]  # noqa: E731
    top = rows(a["frames"][0])
    frames = {f["index"]: top + rows(f) for f in b["frames"]}
    return {"name": NAME, "colors": colors, "pixels": frames[281], "frames": frames}


class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, frames=None, metallic=0.45, roughness=0.45, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"nshd245B_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


# --- geometry helpers (sprite px; x column edge, y row edge, z up) ------------------------------
def X(x):
    return x - X0


def box(P, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    T.hull(P, T.cbox(X(x0), X(x1), y0, y1, z0, z1, ch, chz), mat)


def arch_ring(cx, y, w, h, z0, p, n, grooves=(), bead=None, flat=0.0):
    """One closed loft ring: a superellipse arch (half width w, height h above z0, exponent p) from
    the right foot over the crown to the left foot, closed by its foot line. `grooves`: [(x offset,
    half width, depth)] cut into the crown as V-bottomed slots; `bead`: (x offset, half width, rise)
    a raised strip. Every ring has the same point count for any w, h, depth (lofts point for point).
    Returns [(x, y, z)], x in Blender-shifted px."""
    feats = []  # (x offset, dz)
    for xo, hw, d in grooves:
        feats += [(xo - hw, 0.0, "e"), (xo - 0.35 * hw, -d, "b"), (xo + 0.35 * hw, -d, "b"), (xo + hw, 0.0, "e")]
    if bead:
        xo, hw, r = bead
        feats += [(xo - hw, 0.0, "e"), (xo - 0.45 * hw, r, "b"), (xo + 0.45 * hw, r, "b"), (xo + hw, 0.0, "e")]
    q = 2.0 / p

    def pt_theta(t):
        c, s = math.cos(t), math.sin(t)
        return w * math.copysign(abs(c) ** q, c), h * abs(s) ** q

    def theta_of(xo):
        u = max(-0.999, min(0.999, xo / max(w, 1e-6)))
        c = math.copysign(abs(u) ** (p / 2.0), u)
        return math.acos(c)

    # base samples on either side of the features (fixed counts), the features between them
    fts = sorted((theta_of(xo), dz) for xo, dz, _ in feats)
    lo = fts[0][0] if fts else 0.5 * math.pi
    hi = fts[-1][0] if fts else 0.5 * math.pi
    n1 = n // 2
    pts = [(lo * k / n1, None) for k in range(n1)]
    pts += fts if fts else [(0.5 * math.pi, None)]
    pts += [(hi + (math.pi - hi) * k / n1, None) for k in range(1, n1 + 1)]
    ring = []
    for t, dz in pts:
        dx, zz = pt_theta(t)
        if t in (0.0, math.pi):
            zz = 0.0
        zz = max(0.0, zz + (dz or 0.0))
        ring.append((X(cx + dx), y, z0 + flat + zz if zz > 0 else z0))
    return ring


def loft(P, rings, mat_of, cap0=True, cap1=True, inner=None):
    """Quads between consecutive rings (same count); caps close the ends. mat_of(i, k) per quad.
    `inner`: a point (or function of ring index) inside the solid for normal hints."""
    vs = [[P.v(p) for p in r] for r in rings]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        a, b = vs[i], vs[i + 1]
        ic = inner(i) if callable(inner) else inner
        for k in range(n):
            j = (k + 1) % n
            P.f([a[k], a[j], b[j], b[k]], mat_of(i, k), away=ic)
    if cap0:
        P.f(vs[0], mat_of(0, 0), out=(0, -1, 0))
    if cap1:
        P.f(vs[-1], mat_of(len(rings) - 2, 0), out=(0, 1, 0))
    return vs


def stations(a, b, step, extra=()):
    ys = set(extra)
    k = 0
    while a + k * step < b - 1e-6:
        ys.add(round(a + k * step, 4))
        k += 1
    ys.add(b)
    return sorted(y for y in ys if a <= y <= b)


# --- parts ---------------------------------------------------------------------------------------
DRUM_W = T.pchip([0.75, 1.1, 1.6, 2.4, 3.3, 4.1, 9.2, 9.9, 10.4], [1.6, 3.6, 4.7, 5.7, 6.35, 6.5, 6.5, 6.35, 5.9])
DRUM_H = T.pchip([0.75, 1.1, 1.6, 2.4, 3.3, 4.1, 9.2, 9.9, 10.4], [3.4, 4.9, 5.9, 6.7, 7.15, 7.3, 7.3, 7.15, 6.7])


def drum(P, M):
    """The dark polished drum along the column (rows 1-10), its seam groove down the crown (col 10),
    a raised machined collar near the front, and a recessed front bulkhead the camera sees."""
    ys = stations(0.75, 10.4, 0.45, extra=(0.95, 1.1, 1.3, 1.6, 2.0, 2.4, 2.9, 3.3))
    rings = []
    for y in ys:
        w, h = DRUM_W(y), DRUM_H(y)
        g = [(0.0, 0.42, min(0.55, 0.12 * h))] if y > 1.2 else [(0.0, 0.42, 0.0)]
        rings.append(arch_ring(CX + 0.05, y, w, h, FL, 2.4, 22, grooves=g))
    loft(P, rings, lambda i, k: M["drum"], inner=lambda i: (X(CX), ys[i], FL + 1.5))
    # machined collar ring round the front (y 8.3-9.1), a hair proud of the drum
    cr = []
    for y, d in ((8.25, 0.0), (8.4, 0.18), (8.95, 0.18), (9.1, 0.0)):
        cr.append(arch_ring(CX + 0.05, y, DRUM_W(y) + d, DRUM_H(y) + d, FL, 2.4, 22,
                            grooves=[(0.0, 0.42, 0.55 + 0.0 * d)]))
    loft(P, cr, lambda i, k: M["drum"], inner=(X(CX), 8.7, FL + 1.5))  # capped: closed (inside the drum)
    # recessed front bulkhead: a slightly smaller arch plate inset on the front face, and a
    # hatch block on it (dark steel)
    fr = [arch_ring(CX + 0.05, 10.25, 4.6, 5.0, FL, 2.4, 22), arch_ring(CX + 0.05, 10.55, 4.6, 5.0, FL, 2.4, 22)]
    loft(P, fr, lambda i, k: M["deck"], inner=(X(CX), 10.3, FL + 1.0))
    # rear foot plinth so the rounded end reads as sitting on the floor
    box(P, CX - 5.6, CX + 5.6, 1.6, 9.8, FL, FL + 0.9, M["deck"], ch=0.3)


def deck(P, M):
    """The low hinge deck between the drum and the pod (rows 10-21) with the red signal bar, the
    grey cross-beam and the yoke cheeks with their pivot hubs."""
    # the deck slab: plan x 4-18, rows 9.6-21.8, chamfered corners (row 22's corner is floor)
    T.hull(P, [(X(x), y, z) for x, y in ((4.4, 9.6), (17.6, 9.6), (18.0, 10.0), (18.0, 21.0), (17.2, 21.8),
                                       (4.9, 21.8), (4.0, 20.9), (4.0, 10.0))
               for z in (FL, 2.3)] + [(X(x), y, 2.6) for x, y in ((4.8, 10.0), (17.2, 10.0), (17.2, 21.0),
                                                                (5.0, 21.0))], M["deck"])
    # red signal bar (row 12) on a dark riser, its front chamfered (row 13's dark red)
    box(P, 6.6, 14.4, 10.2, 13.2, 2.0, 4.0, M["deck"], ch=0.25)
    T.hull(P, [(X(x), y, z) for x in (7.05, 13.95) for y, z in ((11.8, 4.0), (11.8, 4.75), (12.95, 4.75),
                                                               (13.55, 4.1), (13.55, 4.0))]
           + [(X(x), y, 4.75) for x in (7.0, 14.0) for y in (11.95, 12.8)], M["red"])
    # grey cross-beam (rows 14-16): a chamfered beam on the deck, two bolts
    # the bar's dark-red lip (row 13, 162) as its own strip on the front chamfer
    T.hull(P, [(X(x), y, z) for x in (7.05, 13.95) for y, z in ((12.95, 4.75), (13.55, 4.1), (13.75, 4.0),
                                                              (13.75, 4.5), (13.0, 4.8))], M["lip"])
    box(P, 6.9, 14.1, 13.8, 16.9, 2.0, 3.75, M["beam"], ch=0.35)
    for xb in (8.0, 13.0):
        box(P, xb - 0.3, xb + 0.3, 15.0, 15.6, 3.7, 3.95, M["beam"], ch=0.1)
    # yoke cheeks (rows 14-19) either side, bolted, pivot hubs facing out
    for xa, xb, hub in ((4.35, 6.9, 4.0), (15.0, 17.6, 18.0)):
        T.hull(P, [(X(x), y, z) for x in (xa, xb) for y, z in ((13.8, FL), (13.8, 4.2), (14.6, 5.0), (18.4, 5.0),
                                                             (19.9, 3.6), (19.9, FL))], M["cheek"])
        xm = 0.5 * (xa + xb)
        for yb in (14.9, 18.0):
            box(P, xm - 0.28, xm + 0.28, yb - 0.28, yb + 0.28, 4.9, 5.15, M["beam"], ch=0.08)
        # hub cap on the outer face (a short revolved boss along x)
        sgn = -1 if hub < 10 else 1
        xo = xa if sgn < 0 else xb
        rv = []
        for t, r in ((-0.2, 1.35), (0.22, 1.35), (0.35, 1.05)):
            rv.append([(X(xo + sgn * t), 17.0 + r * math.cos(2 * math.pi * k / 14), 2.9 + r * math.sin(2 * math.pi * k / 14))
                       for k in range(14)])
        loft(P, rv, lambda i, k: M["hub"], inner=(X(xo - sgn * 0.5), 17.0, 2.9))
    # the pivot pin between the cheeks (mostly hidden under the head)
    rv = [[(X(x), 17.0 + 1.0 * math.cos(2 * math.pi * k / 12), 2.9 + 1.0 * math.sin(2 * math.pi * k / 12))
           for k in range(12)] for x in (6.8, 15.1)]
    loft(P, rv, lambda i, k: M["hub"], inner=(X(CX), 17.0, 2.9))


HEAD_W = T.pchip([19.6, 20.3, 21.3, 22.3, 23.2, 24.0, 24.7], [2.9, 3.6, 4.55, 5.55, 6.35, 6.5, 6.4])
HEAD_H = T.pchip([19.6, 20.3, 21.5, 23.0, 24.0, 24.7], [3.4, 4.3, 5.0, 5.45, 5.6, 5.3])
COL_W = T.pchip([24.1, 24.6, 25.4, 26.6, 27.2, 27.9], [6.2, 6.5, 6.6, 6.7, 7.2, 7.5])
COL_H = T.pchip([24.1, 24.6, 25.3, 26.5, 27.9], [5.2, 6.0, 6.45, 6.6, 6.6])


def head(P, M):
    """The pod's head plate (rows 20-24) with its centre strip between two grooves, then a raised
    collar (rows 25-27) in front of it: two overlapping armour plates, the gap a panel line."""
    ys = stations(19.6, 24.7, 0.4, extra=(19.8, 20.0, 24.4))
    rings = []
    for y in ys:
        d = 0.42 if 20.0 <= y <= 24.3 else 0.0
        rings.append(arch_ring(CX, y, HEAD_W(y), HEAD_H(y), FL, 2.6, 22,
                               grooves=[(-1.0, 0.42, d), (2.0, 0.42, d)], bead=(0.5, 1.05, 0.0)))
    nr = len(rings[0])
    # the centre strip (between the grooves) in the lighter brown
    ring0 = rings[0]
    strip = {k for k, p in enumerate(ring0) if -0.5 < p[0] - X(CX) - 0.5 < 1.5}

    def mat(i, k):
        return M["ridge"] if k in strip and 0 < k < nr - 1 else M["head"]
    loft(P, rings, mat, inner=lambda i: (X(CX), ys[i], FL + 1.0))
    ys = stations(24.1, 27.9, 0.4, extra=(24.3, 24.6, 25.0, 27.2))
    rings = [arch_ring(CX, y, COL_W(y), COL_H(y), FL, 2.6, 22) for y in ys]
    loft(P, rings, lambda i, k: M["head"], inner=lambda i: (X(CX), ys[i], FL + 1.0))


BODY_W = T.pchip([27.5, 28.0, 28.5, 39.6, 40.6, 41.5, 42.5, 43.5, 44.4, 45.0],
                 [8.9, 9.4, 9.5, 9.5, 9.05, 8.45, 7.4, 6.1, 4.4, 2.2])
BODY_H = T.pchip([27.5, 28.0, 28.8, 31.0, 34.5, 38.5, 41.0, 43.0, 44.4, 45.0],
                 [6.4, 7.2, 7.8, 8.35, 8.5, 8.1, 7.0, 5.2, 3.0, 1.5])
SEAM = T.pchip([34.8, 35.6, 44.2, 45.0], [0.0, 1.0, 1.0, 0.6])
BP = 2.3


def body_pt(y, t, d=0.0):
    """A point on the shell's section at row y, angle t (0 right foot .. pi left foot), pushed d
    outward along the section's normal. (x px Blender-shifted, z.)"""
    w, h = BODY_W(y) + d, BODY_H(y) + d
    q = 2.0 / BP
    c, s = math.cos(t), math.sin(t)
    return X(CX + w * math.copysign(abs(c) ** q, c)), FL + h * abs(s) ** q


def body(P, M):
    """The big round shell (rows 28-44), the seam bead between its two grooves down the back."""
    ys = stations(27.5, 45.0, 0.5, extra=(27.7, 28.0, 28.3, 44.2, 44.6, 44.8))
    rings = []
    for y in ys:
        f = SEAM(y) if y > 34.8 else 0.0
        rings.append(arch_ring(CX, y, BODY_W(y), BODY_H(y), FL, BP, 30,
                               grooves=[(-1.0, 0.5, 0.45 * f), (1.0, 0.5, 0.45 * f)], bead=(0.0, 0.45, 0.2 * f)))
    nr = len(rings[0])
    bead = {k for k, p in enumerate(rings[0]) if abs(p[0] - X(CX)) < 0.42 and 0 < k < nr - 1}

    def mat(i, k):
        return M["bead"] if (k in bead and ys[i] > 35.0) else M["shell"]
    loft(P, rings, mat, inner=lambda i: (X(CX), ys[i], FL + 1.0))


def strap(P, M):
    """The red strap over the shell's front shoulder, leaning back: its ends run down the sides
    further down-screen (rows 30-34 at cols 1-3). Interrupted by the lamp housing at the crown."""
    def yband(z, edge):
        lean = 0.5 * max(0.0, 6.6 - z)
        return (27.9 if edge == 0 else 32.2) + lean

    def pt(t, edge, d):
        y = yband(FL + 8.0, edge)
        for _ in range(4):
            xx, zz = body_pt(y, t)
            y = yband(zz, edge)
        xx, zz = body_pt(y, t, d)
        return (xx, y, zz)
    # angles off the housing (x within cols 8-13 at the crown)
    for t0, t1 in ((0.0, 1.32), (1.82, math.pi)):
        ts = [t0 + (t1 - t0) * k / 14 for k in range(15)]
        rings = []
        for t in ts:
            rings.append([pt(t, 0, -0.15), pt(t, 0, 0.4), pt(t, 1, 0.4), pt(t, 1, -0.15)])
        # rings run along t: quads between them, caps at both ends
        vs = [[P.v(p) for p in r] for r in rings]
        for i in range(len(vs) - 1):
            for k in range(4):
                j = (k + 1) % 4
                cx_, cz_ = body_pt(30.0, 0.5 * (ts[i] + ts[i + 1]), -2.0)
                P.f([vs[i][k], vs[i][j], vs[i + 1][j], vs[i + 1][k]], M["strap"], away=(cx_, 30.0, cz_))
        P.f(vs[0], M["strap"], away=(X(CX), 30, FL + 3))
        P.f(vs[-1], M["strap"], away=(X(CX), 30, FL + 3))
        # a strap buckle plate where it meets the housing side (machined detail at the crown)
    for x0_, x1_ in ((6.9, 8.2), (12.8, 14.1)):
        y0, y1 = 28.3, 31.7
        zt = BODY_H(30.0) + FL + 0.45
        box(P, x0_, x1_, y0, y1, zt - 1.2, zt, M["strap"], ch=0.18)


LAMP = dict(x0=7.9, x1=13.1, y0=29.4, y1=36.0)


def lamp_top(y):
    """The housing's top: tilted 10 deg down toward the camera (+y)."""
    return FL + 9.75 - 0.12 * (y - 29.4)


def lamps(P, M):
    """The lamp housing (cols 8-12, rows 30-35) with its divider bar and a brown visor over it."""
    x0, x1, y0, y1 = LAMP["x0"], LAMP["x1"], LAMP["y0"], LAMP["y1"]
    c = 0.45
    pts = []
    for x, y in ((x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - 1.2), (x1 - 1.2, y1), (x0 + 1.2, y1),
                 (x0, y1 - 1.2), (x0, y0 + c)):
        zt = lamp_top(y)
        pts += [(X(x), y, FL + 4.5), (X(x), y, zt - 0.25)]
        # chamfered top edge: inset ring at the top
        xi = x + (0.25 if x < CX else -0.25)
        yi = y + (0.25 if y < 0.5 * (y0 + y1) else -0.25)
        pts.append((X(xi), yi, lamp_top(yi)))
    T.hull(P, pts, M["housing"])
    # visor (rows 28-29): brown cowl at the housing's back, standing above it, its front sloped
    vs = [(27.9, 2.2, 3.75), (28.2, 2.5, 4.05), (29.45, 2.5, 4.1), (29.8, 2.35, 3.8), (29.95, 2.1, 3.4)]
    rings = [arch_ring(CX, y, w, h, FL + 6.0, 3.2, 16) for y, w, h in vs]
    loft(P, rings, lambda i, k: M["visor"], inner=lambda i: (X(CX), vs[i][0], FL + 7.0))


def lens_parts(coll, Mt, M):
    """Lenses per frame (frame_part): glowing on 281, unlit pink glass on 283."""
    objs = []
    for frame, (mu, ml) in ((281, ("lens_on_u", "lens_on_l")), (283, ("lens_off_u", "lens_off_l"))):
        P = T.Part(f"{NAME}_lenses-{frame}", smooth_angle=40)
        # upper lens rows 30-31.9, lower rows 32.9-35.7 with round lower corners; both the sprite's
        # 5 px (cols 8-12, x 8.0-13.0), leaving only a hair of the housing's rim beside them
        la, lb = 8.0, 13.0
        for (ya, yb, rc, m) in ((29.95, 31.85, 0.3, M[mu]), (32.95, 35.7, 0.9, M[ml])):
            pts = []
            for x, y in ((la + 0.3, ya), (lb - 0.3, ya), (lb, ya + 0.3), (lb, yb - rc), (lb - rc, yb),
                         (la + rc, yb), (la, yb - rc), (la, ya + 0.3)):
                zt = lamp_top(y)
                pts += [(X(x), y, zt - 0.4)]
                xi = x + (0.22 if x < CX else -0.22)
                yi = y + (0.25 if y < 0.5 * (ya + yb) else -0.25)
                pts.append((X(xi), yi, lamp_top(yi) + 0.16))
            T.hull(P, pts, m)
        o = T.finish(P, Mt.list, coll)
        common.frame_part(o, [frame])
        if frame == 281:
            glow_tint(o)
        objs.append(o)
    return objs


GLOW_ATTR = "lens_glow"


def glow_tint(o, v=0.1):
    """Darken the lit lenses' albedo (not their emission) with a vertex colour exported as COLOR_0.
    The game copies the palette colour into the emissive at full strength, so a lens that also took
    the scene's light summed to well over 1 and Neutral tone mapping washed the red to salmon (the
    reviewer's (244,107,103)). three.js multiplies base colour, and so a metal's specular, by
    COLOR_0 but never the emissive: the lens then shows its palette colour with a faint sheen."""
    a = o.data.color_attributes.new(GLOW_ATTR, "FLOAT_COLOR", "POINT")
    for d in a.data:
        d.color = (v, v, v, 1.0)


def export_glb(objects, path, image_format="AUTO"):
    """common.export_glb plus the lens tint attribute (export_vertex_color NAME: only meshes that
    carry GLOW_ATTR get COLOR_0). Copied here, not shared; candidate for common.py."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_cameras=False, export_lights=False, export_extras=True, export_image_format=image_format,
        export_image_quality=85, export_vertex_color="NAME", export_vertex_color_name=GLOW_ATTR,
        export_all_vertex_colors=False, export_active_vertex_color_when_no_material=False,
    )
    return path


common.export_glb = export_glb


def floor(sprite, Mt, coll):
    """Stone floor plate 0..FL under the whole pair, its top painted per pixel in four grey tones
    (as lib_b073 / newshd-275), a separate object marked tyrian_ground."""
    pix = sprite["pixels"]
    colors = sprite["colors"]
    tones = ((1, 3), (4, 6), (7, 9), (10, 15))
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        mid = (lo + hi) / 2
        slots.append(Mt(min(have, key=lambda i: abs(i - mid)), f"stone{lo}", metallic=0.05, roughness=0.85)
                     if have else None)

    def slot_of(i):
        for (lo, hi), s in zip(tones, slots):
            if lo <= i <= hi:
                return s
        return slots[1]
    P = T.Part(f"{NAME}_floor", smooth_angle=5)
    T.hull(P, [(x, y, z) for x in (-12.0, 12.0) for y in (0.0, float(H)) for z in (0.0, FL - 0.01)], slot_of(4))
    for r in range(H):
        c = 0
        while c < W:
            s = slot_of(pix[r][c])
            e = c + 1
            while e < W and slot_of(pix[r][e]) == s:
                e += 1
            vs = [P.v((xx, yy, FL)) for xx, yy in ((c - 12, r), (e - 12, r), (e - 12, r + 1), (c - 12, r + 1))]
            P.f(vs, s, out=(0, 0, 1))
            c = e
    o = T.finish(P, Mt.list, coll)
    o.data.shade_flat()
    o["tyrian_ground"] = True
    return o


def recentre(obj):
    """usp_talon.finish puts row 14 at Y = 0; the pair's centre is row 28."""
    for v in obj.data.vertices:
        v.co.y += 14.0 / 12.0
    obj.data.update()


def build():
    sprite = composite_sprite()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    Mt = Mats(sprite)
    paint = dict(metallic=0.45, roughness=0.42)      # the fortress's painted metal (newshd-275)
    steel = dict(metallic=0.75, roughness=0.32)
    M = {
        "drum": Mt(4, "drum", metallic=0.8, roughness=0.28),
        "deck": Mt(1, "deck", metallic=0.6, roughness=0.5),
        "red": Mt(67, "red", **paint),
        "lip": Mt(162, "lip", **paint),
        "beam": Mt(5, "beam", **steel),
        "cheek": Mt(4, "cheek", **steel),
        "hub": Mt(4, "hub", **steel),
        "head": Mt(20, "head", **paint),
        "ridge": Mt(23, "ridge", **paint),
        "shell": Mt(19, "shell", metallic=0.4, roughness=0.5),
        "bead": Mt(22, "bead", **paint),
        "slot": Mt(1, "slot", metallic=0.6, roughness=0.5),
        "strap": Mt(68, "strap", metallic=0.3, roughness=0.5),
        "housing": Mt(163, "housing", metallic=0.6, roughness=0.4),
        "visor": Mt(21, "visor", **paint),
        # lit lenses glow in their own palette colour (the sprite's lit medians 119 / 120), their
        # albedo darkened by glow_tint so the game's light doesn't wash them to salmon
        "lens_on_u": Mt(119, "lens_on_u", metallic=1.0, roughness=0.5, emission=1.0),
        "lens_on_l": Mt(120, "lens_on_l", metallic=1.0, roughness=0.5, emission=1.0),
        "lens_off_u": Mt(72, "lens_off_u", metallic=0.0, roughness=0.15),
        "lens_off_l": Mt(73, "lens_off_l", metallic=0.0, roughness=0.15),
    }
    P = T.Part(NAME, smooth_angle=34)
    drum(P, M)
    deck(P, M)
    head(P, M)
    body(P, M)
    strap(P, M)
    lamps(P, M)
    obj = T.finish(P, Mt.list, coll)
    lenses = lens_parts(coll, Mt, M)
    fl = floor(sprite, Mt, coll)
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=3000, smooth=6, inside=0.01)
    shell.name = f"{NAME}_outline"
    objs = [obj, fl, shell] + lenses
    for o in objs:
        recentre(o)
    return sprite, objs


_cut_parts = L.cut_parts


def cut_parts(part, layout):
    """lib_b073.cut_parts, then the outline shell's pieces get their flag and material back."""
    out = _cut_parts(part, layout)
    if part.get("tyrian_outline"):
        mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
        for piece in out.values():
            piece["tyrian_outline"] = True
            piece.data.materials.clear()
            piece.data.materials.append(mat)
    return out


L.cut_parts = cut_parts


def build_asm(sprite_, g):
    sprite, objs = build()
    obj, fl, shell = objs[0], objs[1], objs[2]
    bpy.data.objects.remove(fl, do_unlink=True)  # the floor plate stays out of the pieces (D129)
    return obj, [], [shell] + objs[3:]


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build_asm, __file__, 1, 2)
