"""newshc-163 (design A): the blue housing of the level 1.19 / 3.23 machine with its cannon removed
(newshc.shp frame 163, 24 x 28 px, one frame), rebuilt hard-surface to the D65 standard.

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"; inner mask, D74):
- Rows 3-9, cols 1-22: the hood, two armoured cowls either side of a dark channel (cols 11-12),
  rounded at the back (row 3 starts at col 4, row 4 at col 2). Each cowl: an outer flank band
  (cols 1-3, 54/55 over 51), a lit crown (57-59, its bright stripe at cols 5-6 is sheen) and a
  short south slope (row 8, 52-54) down to a dark seal gap (row 9, 49-52) over the housing.
- Rows 10-13: the grey housing's flat deck (106; its bright row 11 is sheen on a slightly crowned
  plate), a centre seam (cols 11-12, 101/102). The outer corners of row 10 (cols 1-3) are still
  blue: the cowls' corner gussets.
- Rows 13-17, cols 2-7 / 16-21: two pods whose fronts slope down to the ground at row 18, each
  with a dark round intake (98/99, cols 3-5, rows 14-16) in a grey lip.
- Row 13, cols 8-15: the dark socket where newshc-155's cannon stands, the slide rod's collar
  (5/4) at cols 11-12; row 14 holes at cols 9 and 14 (ground seen between rail and collar).
- Rows 14-22, cols 8 / 15: the cradle's two rails (3-10), dark floor between (1-2), a bright slide
  rod (cols 11-12, 6-11) from the collar to a U-bend (rows 21-23) with a hex boss (9).
- Rows 24-27: a small fitting: dark posts (row 24), a grey crossbar (100) and two blue tines
  (cols 10, 13, 56/59).

Engineering reading (cross-sections first): the cowls are armour shells (vertical outer wall,
chamfered flank, panel seam, superelliptic crown, vertical inner wall onto the channel floor);
the housing a chamfered deck with a crowned top, a modelled panel line at the crease where the
pods' fronts fall away, intake collars proud of the slope with a dark bore, hub and vanes; the
cradle a pair of chamfered beams hinged on a trunnion axle in the socket, tied by ribs, joined by a
bent end plate that carries the rod's boss and the fitting. Underside: closed, plain.

Units while building: sprite px (x = column edge - 12, y = row edge down the screen, z up),
moved to Blender by usp_talon.finish (1/12, y flipped).

Grafts after the design review: pod-wall vent slots (98) and rear-corner cheek plates (51), a gland
ring (7) where the rod meets the collar.

Run: blender --background --python assets/blender/enemies/newshc-163.py [-- --out <review glb>]
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshc-163"
MODEL = f"enemies/{NAME}"


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, metallic=0.45, roughness=0.42):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{NAME}_{part}", metallic=metallic,
                                                     roughness=roughness))
        return self.slots[key]


# --- helpers ------------------------------------------------------------------------------------
def basis(u):
    u = Vector(u).normalized()
    ref = Vector((0, 0, 1)) if abs(u.z) < 0.9 else Vector((1, 0, 0))
    e1 = ref.cross(u).normalized()
    e2 = u.cross(e1).normalized()
    return u, e1, e2


def revolve(P, a, u, stations, mat, n=16, cap0=True, cap1=True, phase=0.5, mats=None):
    """Rings round the axis from a along u: stations [(t, r)]. mats: per-segment material list."""
    a = Vector(a)
    u, e1, e2 = basis(u)
    angs = [2 * math.pi * (k + phase) / n for k in range(n)]
    rings = []
    for t, r in stations:
        c = a + u * t
        rings.append([P.v(tuple(c + (e1 * math.cos(q) + e2 * math.sin(q)) * r)) for q in angs])
    for i in range(len(stations) - 1):
        m = mats[i] if mats else mat
        c = a + u * (0.5 * (stations[i][0] + stations[i + 1][0]))
        for k in range(n):
            j = (k + 1) % n
            P.f([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], m, away=tuple(c))
    if cap0 and stations[0][1] > 1e-6:
        P.f(rings[0], mats[0] if mats else mat, out=tuple(-u))
    if cap1 and stations[-1][1] > 1e-6:
        P.f(rings[-1], mats[-1] if mats else mat, out=tuple(u))
    return rings


def loft_r(P, stations, section, cap0=True, cap1=True, cap_mat=None):
    """Loft along +y (rows). section(s) -> [(x, z, mat)]: a closed ring in the x-z plane; mat is the
    material of the strip from this point to the next."""
    rings = []
    for s in stations:
        pts = section(s)
        rings.append(([P.v((x, s["r"], z)) for x, z, _ in pts], [m for _, _, m in pts],
                      Vector((sum(p[0] for p in pts) / len(pts), s["r"], sum(p[1] for p in pts) / len(pts)))))
    for i in range(len(rings) - 1):
        (a, ma, ca), (b, _, cb) = rings[i], rings[i + 1]
        c = (ca + cb) / 2
        n = len(a)
        for k in range(n):
            j = (k + 1) % n
            P.f([a[k], a[j], b[j], b[k]], ma[k], away=tuple(c))
    if cap0:
        P.f(rings[0][0], cap_mat if cap_mat is not None else rings[0][1][0], out=(0, -1, 0))
    if cap1:
        P.f(rings[-1][0], cap_mat if cap_mat is not None else rings[-1][1][0], out=(0, 1, 0))


def stations(keys, rs):
    """pchip every field of the key stations (dicts with 'r') at rows rs."""
    xs = [k["r"] for k in keys]
    fs = {f: T.pchip(xs, [k[f] for k in keys]) for f in keys[0] if f != "r"}
    return [dict(r=r, **{f: fn(r) for f, fn in fs.items()}) for r in rs]


def cprism(P, poly, z0, z1, ch, top, side):
    """A chamfered prism over a convex plan polygon [(x, y)] (counter-clockwise or not): vertical
    walls z0..z1-ch, a 45-degree chamfer, a flat inset top. Top and chamfer in `top`, walls `side`."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    n = len(poly)
    # inset by offsetting each edge line and intersecting neighbours
    lines = []
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        nx, ny = -(by - ay), bx - ax
        L = math.hypot(nx, ny) or 1
        nx, ny = nx / L, ny / L
        if (cx - (ax + bx) / 2) * nx + (cy - (ay + by) / 2) * ny < 0:
            nx, ny = -nx, -ny
        lines.append((ax + nx * ch, ay + ny * ch, bx - ax, by - ay))
    ins = []
    for i in range(n):
        p1, p2 = lines[i - 1], lines[i]
        den = p1[2] * p2[3] - p1[3] * p2[2]
        if abs(den) < 1e-9:
            ins.append((p2[0], p2[1]))
            continue
        t = ((p2[0] - p1[0]) * p2[3] - (p2[1] - p1[1]) * p2[2]) / den
        ins.append((p1[0] + p1[2] * t, p1[1] + p1[3] * t))
    r0 = [P.v((x, y, z0)) for x, y in poly]
    r1 = [P.v((x, y, z1 - ch)) for x, y in poly]
    r2 = [P.v((x, y, z1)) for x, y in ins]
    c = (cx, cy, (z0 + z1) / 2)
    for i in range(n):
        j = (i + 1) % n
        P.f([r0[i], r0[j], r1[j], r1[i]], side, away=c)
        P.f([r1[i], r1[j], r2[j], r2[i]], top, away=c)
    P.f(r2, top, out=(0, 0, 1))
    P.f(r0, side, out=(0, 0, -1))


def box(P, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def tagged_hull(P, points, top_mat, side_mat, cos_top=0.55):
    """hull(); faces whose normal points up (z > cos_top) get top_mat, the rest side_mat."""
    before = set(P.bm.faces)
    T.hull(P, points, side_mat)
    c = sum((Vector(p) for p in points), Vector()) / len(points)
    for f in P.bm.faces:
        if f in before or not f.is_valid:
            continue
        f.normal_update()
        nrm = f.normal if f.normal.dot(f.calc_center_median() - c) >= 0 else -f.normal
        f.material_index = top_mat if nrm.z > cos_top else side_mat


def frange(a, b, step):
    return T.frange(a, b, step)


SIDES = (-1, 1)   # west, east


def X(c, s):
    return (c - 12.0) if s < 0 else (12.0 - c)


# --- hood ---------------------------------------------------------------------------------------
LOBE_KEYS = [
    # r: row edge; cL outer edge col; cR inner (channel) edge; hw outer wall top; hc crown; hi inner wall top
    dict(r=3.0, cL=4.7, cR=10.4, hw=0.6, hc=1.6, hi=0.9),
    dict(r=3.35, cL=3.4, cR=10.85, hw=1.5, hc=3.6, hi=2.2),
    dict(r=3.9, cL=2.25, cR=11.0, hw=2.0, hc=4.55, hi=3.1),
    dict(r=4.6, cL=1.45, cR=11.0, hw=2.3, hc=5.1, hi=3.5),
    dict(r=5.4, cL=1.05, cR=11.0, hw=2.4, hc=5.38, hi=3.6),
    dict(r=6.6, cL=1.0, cR=11.0, hw=2.45, hc=5.45, hi=3.6),
    dict(r=7.6, cL=1.0, cR=11.0, hw=2.45, hc=5.35, hi=3.6),
    dict(r=8.3, cL=1.0, cR=11.0, hw=2.4, hc=5.05, hi=3.5),
    dict(r=8.75, cL=1.0, cR=11.0, hw=2.3, hc=4.6, hi=3.35),
    dict(r=9.05, cL=1.0, cR=11.0, hw=2.2, hc=4.1, hi=3.15),
]
FLANK_W = 2.35   # px: the outer flank band (sprite cols 1-3)
Q = 2.4          # crown superellipse exponent


def lobe(P, M, s):
    st = stations(LOBE_KEYS, [3.0, 3.12, 3.25] + frange(3.4, 8.7, 0.22) + [8.85, 8.95, 9.05])

    def section(t):
        cL, cR, hw, hc, hi = t["cL"], t["cR"], t["hw"], t["hc"], t["hi"]
        w = cR - cL
        fw = min(FLANK_W, 0.3 * w)
        xs_ = cL + fw                      # seam position
        hs = hw + 0.72 * (hc - hw)          # seam height
        pts = [(cL, 0.0, M["wall"]), (cL, hw, M["flank"])]
        # flank: a convex fillet from the wall top to the seam (quarter superellipse)
        for k in range(1, 5):
            a = k / 5 * math.pi / 2
            pts.append((cL + fw * (1 - math.cos(a)) ** 1.0 * 0.98, hw + (hs - hw) * math.sin(a), M["flank"]))
        # panel seam: a modelled groove
        g = 0.22
        pts += [(xs_ - 0.02, hs, M["seam"]), (xs_ + 0.08, hs - g, M["seam"]), (xs_ + 0.3, hs - g + 0.02, M["seam"]),
                (xs_ + 0.4, hs + 0.02, M["crown"])]
        # crown: superellipse from the seam to the inner shoulder
        x0, x1 = xs_ + 0.4, cR - 0.35
        xc = x0 + 0.45 * (x1 - x0)
        for k in range(1, 13):
            x = x0 + (x1 - x0) * k / 12
            u = (x - xc) / ((xc - x0) if x < xc else (x1 - xc))
            base = hs + 0.02 if x < xc else hi + 0.35
            z = base + (hc - base) * max(0.0, 1 - abs(u) ** Q) ** (1 / Q)
            pts.append((x, z, M["crown"]))
        pts += [(cR - 0.12, hi + 0.12, M["inner"]), (cR, hi - 0.05, M["inner"]), (cR, 0.0, M["under"])]
        return [(X(c, s), z, m) for c, z, m in pts]

    loft_r(P, st, section, cap_mat=M["cap"])
    # bolt row along the flank band, on the wall top
    for r in (4.9, 6.3, 7.7):
        t = stations(LOBE_KEYS, [r])[0]
        revolve(P, (X(t["cL"] + 0.55, s), r, t["hw"] + 0.55), (-s * 0.6, 0, 0.8), [(0, 0.26), (0.18, 0.26), (0.26, 0.15)],
                M["lbolt"], n=6, phase=0.0)
    # seal gap under the hood's south edge (sprite row 9, dark): a recessed dark strip
    a, b = sorted((X(1.15, s), X(11.0, s)))
    box(P, a, b, 8.9, 10.1, 0.0, 2.85, M["skirt"], ch=0.08)
    # cheek plate: the cowl's flank wrapping the housing's rear corner (row 10, cols 1-3)
    xo, xi = X(1.0, s), X(3.5, s)
    pts = []
    for r, zo, zi in ((8.8, 2.4, 2.4), (9.25, 3.45, 3.3), (10.6, 3.6, 3.45), (11.05, 3.2, 3.1)):
        pts += [(xo, r, 0.0), (xi, r, 0.0), (xo, r, zo), (xi, r, zi)]
    T.hull(P, pts, M["cheek"])
    for r in (9.6, 10.3):
        a, b = sorted((X(1.9, s), X(3.1, s)))
        box(P, a, b, r, r + 0.12, 3.3, 3.62, M["seam"], ch=0.0)
    # rear hinge lugs (seen from behind): a plate and two knuckles low on the cowl's back
    a, b = sorted((X(5.4, s), X(9.9, s)))
    box(P, a, b, 3.05, 3.55, 0.25, 0.85, M["hinge_plate"], ch=0.1)
    for c in (5.8, 8.3):
        x0 = X(c, s)
        x1 = X(c + 1.3, s)
        revolve(P, (min(x0, x1), 3.1, 0.95), (1, 0, 0), [(0, 0.42), (abs(x1 - x0), 0.42)], M["hinge"], n=10)


def channel(P, M):
    """The channel between the cowls (cols 11-12): its floor, the cannon's track."""
    box(P, -1.05, 1.05, 3.85, 10.0, 0.0, 2.55, M["channel"], ch=0.0)
    # guide strips on the channel floor's edges
    for x in (-0.75, 0.75):
        box(P, x - 0.18, x + 0.18, 4.2, 9.6, 2.4, 2.75, M["channel_hi"], ch=0.06)


# --- housing ------------------------------------------------------------------------------------
POD_KEYS = [
    dict(r=9.95, cL=1.0, h=3.0),
    dict(r=10.3, cL=1.0, h=3.28),
    dict(r=11.2, cL=1.0, h=3.42),
    dict(r=12.4, cL=1.0, h=3.32),
    dict(r=13.0, cL=1.05, h=3.12),
    dict(r=13.6, cL=1.3, h=2.92),
    dict(r=14.3, cL=1.95, h=2.66),
    dict(r=16.7, cL=2.0, h=1.78),
    dict(r=17.4, cL=2.6, h=1.45),
    dict(r=18.0, cL=3.4, h=1.12),
]
CREASE = 13.0


def pod_h(r):
    """Deck height with the crease panel line at r = CREASE."""
    return POD_SEC["h"](r) - (0.16 if abs(r - CREASE) < 0.07 else 0.0)


POD_SEC = {}


def pod(P, M, s):
    rs = sorted(set(frange(9.95, 18.0, 0.2) + [CREASE - 0.12, CREASE - 0.06, CREASE + 0.06, CREASE + 0.12]))
    xs = [k["r"] for k in POD_KEYS]
    POD_SEC["h"] = T.pchip(xs, [k["h"] for k in POD_KEYS])
    POD_SEC["cL"] = T.pchip(xs, [k["cL"] for k in POD_KEYS])
    st = [dict(r=r, cL=POD_SEC["cL"](r), h=pod_h(r)) for r in rs]
    CH = 0.32
    cR = 8.0

    def section(t):
        h = t["h"]
        top = M["deck"] if t["r"] < CREASE - 0.07 else (M["crease"] if t["r"] < CREASE + 0.07 else M["slope"])
        cham = M["deck_edge"] if t["r"] < CREASE else M["slope_side"]
        pts = [(t["cL"], 0.0, M["pod_side"]), (t["cL"], h - CH, cham), (t["cL"] + CH, h, top),
               (cR - CH, h, cham), (cR, h - CH, M["pod_side"]), (cR, 0.0, M["under"])]
        return [(X(c, s), z, m) for c, z, m in pts]

    loft_r(P, st, section, cap_mat=M["pod_side"])
    intake(P, M, s)
    # access panel on the outer wall (side views): a chamfered plate standing proud
    xo = X(1.0, s)
    a, b = sorted((xo, xo - s * 0.14))
    box(P, a, b, 10.7, 13.3, 0.55, 2.45, M["panel"], ch=0.06)
    # vent slots in the access panel
    for k in range(3):
        y = 10.95 + k * 0.8
        a, b = sorted((xo - s * 0.12, xo - s * 0.18))
        box(P, a, b, y, y + 0.42, 0.95, 2.2, M["vent"], ch=0.0)
    # front foot: the pod's inner toe bolted to the ground beside the rail (row 18, col 7)
    a, b = sorted((X(6.5, s), X(8.0, s)))
    box(P, a, b, 17.6, 18.75, 0.0, 0.75, M["foot"], ch=0.15)
    # bolt heads along the deck's rear edge
    for c in (2.6, 5.2):
        revolve(P, (X(c, s), 10.25, 3.2), (0, 0, 1), [(0, 0.3), (0.2, 0.3), (0.3, 0.18)], M["bolt"], n=6, phase=0.0)


def intake(P, M, s):
    """The round intake on the pod's slope: a machined collar proud of the slope, a dark bore, a hub
    with three vanes."""
    c0, r0 = 4.55, 15.35
    dh = (POD_SEC["h"](r0 + 0.3) - POD_SEC["h"](r0 - 0.3)) / 0.6
    n = Vector((0.0, -dh, 1.0)).normalized()
    O = Vector((X(c0, s), r0, POD_SEC["h"](r0)))
    _, e1, e2 = basis(n)
    # collar: outer wall from below the slope, chamfered top, inner lip down to the bore floor
    revolve(P, O - n * 0.5, n, [(0.0, 1.72), (0.72, 1.72), (0.86, 1.58), (0.86, 1.3), (0.62, 1.22)], M["lip"],
            n=20, cap0=True, cap1=False, mats=[M["lip_side"], M["lip_side"], M["lip"], M["lip_in"]])
    # bore floor: a dark disc inside the collar
    revolve(P, O + n * 0.05, n, [(0.0, 1.24), (0.08, 1.24)], M["bore"], n=20)
    # hub and vanes
    revolve(P, O + n * 0.13, n, [(0.0, 0.48), (0.28, 0.48), (0.38, 0.28)], M["hub"], n=10)
    for k in range(3):
        q = 2 * math.pi * k / 3 + 0.4
        d = e1 * math.cos(q) + e2 * math.sin(q)
        side = n.cross(d).normalized()
        pts = []
        for t in (0.4, 1.2):
            for w in (-0.1, 0.1):
                for hgt in (0.13, 0.4):
                    pts.append(tuple(O + d * t + side * w + n * hgt))
        T.hull(P, pts, M["vane"])


def centre_block(P, M):
    """The housing's middle (cols 8-15, rows 10-12): a crowned deck, cut back at row 13 for the socket."""
    xs = [9.95, 10.3, 11.2, 12.4, 13.0]
    hz = T.pchip(xs, [3.0, 3.28, 3.42, 3.32, 3.12])
    pts = []
    for r in frange(9.95, 13.0, 0.3):
        h = hz(r)
        for x in (-4.0, 4.0):
            pts += [(x, r, 0.0), (x, r, h - 0.25), (x - 0.2 * (1 if x > 0 else -1), r, h)]
    tagged_hull(P, pts, M["centre_top"], M["centre_side"], cos_top=0.8)
    # centre seam (cols 11-12): a modelled panel line, a dark strip sunk into the deck
    box(P, -0.32, 0.32, 10.1, 12.9, 2.6, 3.3, M["seam_c"], ch=0.0)
    # bolt rows either side of the seam
    for x in (-2.6, -1.3, 1.3, 2.6):
        revolve(P, (x, 12.35, hz(12.35) - 0.05), (0, 0, 1), [(0, 0.27), (0.18, 0.27), (0.26, 0.16)], M["bolt"],
                n=6, phase=0.0)


# --- socket and cradle -------------------------------------------------------------------------
AXZ = 1.15   # trunnion axle height
RZ = 1.75    # slide rod axis height


def socket(P, M):
    # the dark pit in the deck's front face where the cannon stands
    box(P, -4.0, 4.0, 12.95, 13.95, 0.0, 0.55, M["pit"], ch=0.0)
    box(P, -4.0, 4.0, 12.6, 13.0, 0.0, 2.6, M["pit"], ch=0.0)
    revolve(P, (-4.0, 13.45, AXZ), (1, 0, 0), [(0, 0.42), (8.0, 0.42)], M["axle"], n=10)


def cradle(P, M):
    for s in SIDES:
        a, b = sorted((X(7.95, s), X(9.05, s)))
        # beam: a chamfered bar, its rear end round the trunnion
        cprism(P, [(a, 13.95), (b, 13.95), (b, 21.6), (a, 21.6)], 0.0, 1.8, 0.22, M["rail_top"], M["rail_side"])
        revolve(P, (a - 0.02, 13.95, AXZ), (1, 0, 0), [(0, 0.82), (b - a + 0.04, 0.82)], M["rail_side"], n=12)
        # lightening slot on the outer face (side view)
        xo = a if s < 0 else b
        box(P, xo - 0.08, xo + 0.08, 15.4, 19.6, 0.55, 1.25, M["slot"], ch=0.0)
        # tie ribs from the rail to the rod (rows 15 and 20)
        c0, c1 = sorted((X(9.0, s), X(10.4, s)))
        for r0 in (15.0, 19.9):
            box(P, c0, c1, r0, r0 + 0.75, 0.0, 0.85, M["rib"], ch=0.12)
    # U-bend end plate (rows 21-23, narrowing to cols 10-13)
    W = [(8.0, 20.6), (8.0, 22.55), (8.45, 23.25), (9.2, 23.75), (10.0, 24.05)]
    poly = [(c - 12.0, r) for c, r in W] + [(12.0 - c, r) for c, r in reversed(W)]
    cprism(P, poly, 0.0, 1.85, 0.3, M["bend_top"], M["bend_side"])
    # floor plate between the rails
    box(P, -3.0, 3.0, 15.0, 20.7, 0.0, 0.35, M["floor"], ch=0.0)
    # slide rod: collar at the socket, polished rod, end block and hex boss on the bend
    revolve(P, (0.0, 13.25, RZ), (0, 1, 0), [(0, 1.55), (0.15, 1.75), (1.4, 1.75), (1.55, 1.55)], M["collar"], n=16, phase=0.0)
    revolve(P, (0.0, 14.7, RZ), (0, 1, 0), [(0, 0.98), (6.4, 0.98)], M["rod"], n=16, cap0=False, cap1=False)
    revolve(P, (0.0, 14.55, RZ), (0, 1, 0), [(0, 1.3), (0.5, 1.3)], M["gland"], n=16)
    for t in (2.2, 4.4):   # wiper rings
        revolve(P, (0.0, 14.7 + t, RZ), (0, 1, 0), [(0, 1.06), (0.22, 1.06)], M["rod_ring"], n=16)
    revolve(P, (0.0, 20.9, RZ), (0, 1, 0), [(0, 1.15), (0.6, 1.15)], M["rod"], n=16)
    revolve(P, (0.0, 22.0, 1.85), (0, 0, 1), [(0, 1.3), (0.38, 1.3), (0.52, 1.05)], M["boss"], n=6, phase=0.0)


def fitting(P, M):
    # dark posts (row 24) hanging the fitting from the bend
    for c in (10.2, 13.8):
        revolve(P, (c - 12.0, 23.8, 0.6), (0, 1, 0), [(0, 0.38), (0.9, 0.38)], M["post"], n=8)
    box(P, -1.25, 1.25, 24.45, 25.95, 0.08, 0.85, M["crossbar"], ch=0.15)
    for s in SIDES:
        c0, c1 = 9.95, 11.1
        keys = [dict(r=24.3, a=c0 + 0.1, b=c1 - 0.05, h=1.0), dict(r=24.9, a=c0, b=c1, h=1.08),
                dict(r=26.3, a=c0, b=c1, h=0.95), dict(r=26.85, a=c0 + 0.12, b=c1 - 0.05, h=0.72),
                dict(r=27.1, a=c0 + 0.35, b=c1 - 0.2, h=0.45)]
        st = stations(keys, frange(24.3, 27.1, 0.2))

        def section(t, s=s):
            a, b, h = t["a"], t["b"], t["h"]
            ch = min(0.16, 0.3 * (b - a))
            pts = [(a, 0.0, M["tine_side"]), (a, h - ch, M["tine_side"]), (a + ch, h, M["tine_top"]),
                   (b - ch, h, M["tine_side"]), (b, h - ch, M["tine_side"]), (b, 0.0, M["under_t"])]
            return [(X(c, s), z, m) for c, z, m in pts]

        loft_r(P, st, section, cap_mat=M["tine_side"])


# --- outline proxy ------------------------------------------------------------------------------
def build():
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    Mt = Mats(sprite)
    paint = dict(metallic=0.45, roughness=0.42)    # satin blue armour paint
    steel = dict(metallic=0.7, roughness=0.34)     # satin machined steel
    dark = dict(metallic=0.3, roughness=0.75)
    M = {
        # hood
        "crown": Mt(57, "crown", **paint), "flank": Mt(54, "flank", **paint), "seam": Mt(52, "seam", **paint),
        "wall": Mt(53, "wall", **paint), "inner": Mt(55, "inner", **paint), "cap": Mt(55, "cap", **paint),
        "under": Mt(51, "under", **dark), "skirt": Mt(51, "skirt", **dark), "cheek": Mt(51, "cheek", **paint), "vent": Mt(98, "vent", **dark), "gland": Mt(5, "gland", **steel), "lbolt": Mt(55, "lbolt", **paint),
        "hinge_plate": Mt(3, "hinge_plate", **steel), "hinge": Mt(4, "hinge", **steel),
        "channel": Mt(52, "channel", **dark), "channel_hi": Mt(54, "channel_hi", **paint),
        # housing
        "deck": Mt(106, "deck", **steel), "deck_edge": Mt(107, "deck_edge", **steel),
        "crease": Mt(101, "crease", **steel), "slope": Mt(102, "slope", **steel),
        "slope_side": Mt(102, "slope_side", **steel), "pod_side": Mt(102, "pod_side", **steel),
        "centre_top": Mt(105, "centre_top", **steel), "centre_side": Mt(104, "centre_side", **steel),
        "seam_c": Mt(101, "seam_c", **steel), "bolt": Mt(107, "bolt", **steel), "foot": Mt(101, "foot", **steel), "panel": Mt(103, "panel", **steel),
        "lip": Mt(104, "lip", **steel), "lip_side": Mt(103, "lip_side", **steel), "lip_in": Mt(100, "lip_in", **steel),
        "bore": Mt(98, "bore", **dark), "hub": Mt(100, "hub", **steel), "vane": Mt(99, "vane", **steel),
        # socket and cradle
        "pit": Mt(96, "pit", **dark), "axle": Mt(3, "axle", **steel),
        "rail_top": Mt(6, "rail_top", **steel), "rail_side": Mt(4, "rail_side", **steel),
        "slot": Mt(2, "slot", **dark), "rib": Mt(4, "rib", **steel),
        "bend_top": Mt(6, "bend_top", **steel), "bend_side": Mt(4, "bend_side", **steel),
        "floor": Mt(2, "floor", **dark), "collar": Mt(6, "collar", **steel), "rod": Mt(7, "rod", metallic=0.8, roughness=0.25),
        "rod_ring": Mt(5, "rod_ring", **steel), "boss": Mt(8, "boss", **steel),
        # fitting
        "post": Mt(3, "post", **steel), "crossbar": Mt(100, "crossbar", **steel),
        "tine_top": Mt(58, "tine_top", **paint), "tine_side": Mt(56, "tine_side", **paint),
        "under_t": Mt(53, "under_t", **dark),
    }
    P = T.Part(NAME, smooth_angle=34)
    for s in SIDES:
        lobe(P, M, s)
        pod(P, M, s)
    channel(P, M)
    centre_block(P, M)
    socket(P, M)
    cradle(P, M)
    fitting(P, M)
    obj = T.finish(P, Mt.list, coll)
    shell = common.outline_shell(obj, coll, faces=3000)
    shell.name = f"{NAME}_outline"
    return sprite, [obj, shell]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, objs = build()
    if "--out" in argv:
        common.export_glb(objs, Path(argv[argv.index("--out") + 1]))
    else:
        common.export_sprite_model(WT, objs, MODEL, sprite["sprites"])
    for o in objs:
        o.data.calc_loop_triangles()
    print(f"built {NAME}: {len(objs[0].data.loop_triangles)} triangles, shell {len(objs[1].data.loop_triangles)}")


if __name__ == "__main__":
    main()
