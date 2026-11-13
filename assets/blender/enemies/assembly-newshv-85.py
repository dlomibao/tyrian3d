"""Grey gunship (newshv.shp 85 + 87, a two-piece assembly, 48 x 28 px; assembly-newshv-44 is its
exact mirror), design B: silhouette and readability at the small tilted game camera first, then
detail.

What it is: a gunship that flies WEST (-3, +1 px/tick, custom event 50 in GRYPHON 2.6 / MISTAKES
2.9) with its two halves rigid side by side. Nose west, big red glowing engine pod at the east
stern. Built as one flying object, then cut into the two pieces at column 24.

Read at the game camera as four masses, each a separate closed solid so the shadows between them
read:
  * the dorsal fairing: a long swept wedge, its north edge sweeping up from the nose tip (c 2,
    r 15) to the hump (r 5) and its lit crown ridge north of centre (rows 9-10); a modelled panel
    groove at c 23.5 where the forward fairing meets the body; louvre ribs over the aft crown;
  * the chin gun block under the nose (rows 13-20, c 2-20): a rounded hard block with a dark gun
    slot (row 15) holding four red gun lights and a grille strip behind them;
  * the aft deck and keel sponson (rows 14-24, c 23-46) with a red nav light at its west tip;
  * the engine pod at the stern (c 39-46, rows 7-16): a fat red glowing nacelle on a dark collar,
    a hot core window on its top (the sprite's orange/yellow), a dark nozzle ring and a glowing
    exhaust facing east (rear).

Units: c, r = assembly px edges; Blender X = (c - 24) / 12, Y = (14 - r) / 12; h px above the
lowest point, Z = (h - 4) / 12 (hull centred on the sprite plane). Pieces: newshv-85 columns 0-24, newshv-87 columns 24-48.

Exports both pieces (with outline shells) to public/models/enemies/<piece>.glb and the
spriteModels JSON entries; --out x.glb also writes a whole scratch GLB, --review DIR renders review views.
Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshv-85.py
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
# assembly-newshv-44 (newshv-44 / newshv-46) is the exact mirror and reuses this builder (MIRROR).
import os  # noqa: E402
MIRROR = os.environ.get("NSHV_MIRROR") == "1"  # set by assembly-newshv-44.py
NAME = "assembly-newshv-44" if MIRROR else "assembly-newshv-85"
PIECES = ["newshv-44", "newshv-46"] if MIRROR else ["newshv-85", "newshv-87"]
W, H = 48, 28


def P(c, r, h):
    return Vector(((c - 24.0) / 12, (14.0 - r) / 12, (h - 4.0) / 12))  # mid-height at the sprite plane


# --------------------------------------------------------------------------------------------------
# Materials (sprite region medians; satin grey, glow surfaces metallic 1 / rough, D126/D173)
# --------------------------------------------------------------------------------------------------

def merged_colors():
    cols = {}
    for n in PIECES:
        cols.update(common.load_sprite(ROOT, n)["colors"])
    return cols


class Mats:
    def __init__(self):
        self.sprite = {"name": NAME, "colors": merged_colors()}
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.35, roughness=0.42, emit=0.0, spec=None):
        key = (index, metallic, roughness, emit, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nshv85b{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            if spec is not None:  # D176: polished grey needs F0 (exported as KHR_materials_specular)
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


MAT = Mats()
GREY = dict(metallic=0.35, roughness=0.42, spec=0.65)
M_FWD_CROWN = MAT(106, **GREY)
M_FWD_N = MAT(103, **GREY)
M_FWD_S = MAT(105, **GREY)
M_BODY_CROWN = MAT(105, **GREY)
M_BODY_N = MAT(105, **GREY)
M_BODY_S = MAT(103, **GREY)
M_UNDER = MAT(101, 0.3, 0.55)
M_SEAM = MAT(102, 0.3, 0.6)
M_FWD_LINE = MAT(104, **GREY)
M_RIB = MAT(108, 0.4, 0.3, spec=0.8)
M_LOUVRE_WELL = MAT(107, **GREY)
M_CHIN = MAT(103, **GREY)
M_CHIN_EDGE = MAT(104, **GREY)
M_CHIN_SIDE = MAT(102, 0.3, 0.5)
M_SLOT = MAT(100, 0.3, 0.65)
M_GRILLE = MAT(106, **GREY)
M_NOSEPLATE = MAT(104, **GREY)
M_DECK = MAT(103, **GREY)
M_SPONSON = MAT(105, **GREY)
M_SPONSON_SIDE = MAT(104, **GREY)
M_STRAKE = MAT(106, **GREY)
M_COLLAR = MAT(99, 0.4, 0.5)
M_PYLON = MAT(100, 0.3, 0.6)
GLOW = dict(metallic=1.0, roughness=0.9)
M_POD = MAT(116, emit=1.25, **GLOW)  # north (lit) half: the sprite's 116
M_POD_S = MAT(114, emit=1.25, **GLOW)  # south half: 114
M_POD_BAND = MAT(114, emit=1.0, **GLOW)
M_POD_RIM = MAT(113, emit=0.8, **GLOW)
M_CORE = MAT(120, emit=1.3, **GLOW)
M_HOT = MAT(124, emit=1.15, **GLOW)
M_EXHAUST = MAT(121, emit=1.4, **GLOW)
M_GUN = [MAT(115, emit=1.6, **GLOW), MAT(116, emit=1.6, **GLOW), MAT(114, emit=1.6, **GLOW)]
M_NAV = MAT(118, emit=1.5, **GLOW)


# --------------------------------------------------------------------------------------------------
# Curves
# --------------------------------------------------------------------------------------------------

def _slopes(xs, ys):
    n = len(xs)
    if n < 2:
        return [0.0] * n
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
    return m


class Pchip:
    """Monotone cubic through knots (x, y) (D52 station interpolation)."""

    def __init__(self, knots):
        self.x = [k[0] for k in knots]
        self.y = [k[1] for k in knots]
        self.m = _slopes(self.x, self.y)

    def __call__(self, x):
        xs, ys, m = self.x, self.y, self.m
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
        hh = xs[i + 1] - xs[i]
        t = (x - xs[i]) / hh
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * hh * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * hh * m[i + 1])


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


# --------------------------------------------------------------------------------------------------
# Dorsal fairing (one loft along c)
# --------------------------------------------------------------------------------------------------

C0, C1 = 1.7, 39.6
YN = Pchip([(1.7, 15.0), (2.6, 14.0), (3.5, 12.8), (4.5, 11.8), (5.5, 10.85), (7, 9.85), (9.5, 8.85), (14.5, 7.85),
            (21, 6.95), (23.9, 6.3), (25.2, 5.9), (26.3, 5.05), (33.6, 5.05), (34.2, 5.95), (38.6, 6.05),
            (39.6, 6.7)])
YS = 15.0
YR = Pchip([(1.7, 15.0), (4, 13.4), (7, 11.6), (11, 10.6), (20, 10.2), (28, 9.4), (35, 9.2), (39.6, 9.6)])
HT = Pchip([(1.7, 3.3), (3, 4.4), (5, 5.6), (8, 6.6), (12, 7.2), (18, 7.4), (26, 7.7), (34, 7.7), (38.5, 7.4),
            (39.6, 7.0)])
HE = 3.3
HB = Pchip([(1.7, 2.9), (5, 1.4), (10, 0.9), (39.6, 0.9)])
P_TOP, P_BOT = 2.3, 2.0
JOINT = (23.2, 23.75)  # panel groove between the forward fairing and the body


def hull_params(c):
    yn, yr = YN(c), YR(c)
    an = max(0.12, yr - yn)
    as_ = max(0.12, YS - yr)
    return yr, an, as_, max(0.15, HT(c) - HE), max(0.15, HE - HB(c))


def hull_top(c, r):
    """Height of the fairing's top surface over (c, r), or None off it."""
    yr, an, as_, ht, _ = hull_params(c)
    t = (yr - r) / an if r < yr else (r - yr) / as_
    if t >= 1:
        return None
    return HE + ht * (1 - t ** P_TOP) ** (1 / P_TOP)


def build_hull(bm):
    n = 32
    cs = []
    c = C0
    while c < C1:
        cs.append(c)
        c += 0.55
    cs.append(C1)
    for j in JOINT:  # the groove stations
        cs += [j - 0.06, j + 0.06]
    cs = sorted(set(round(x, 3) for x in cs))
    rings, groove = [], []
    for c in cs:
        yr, an, as_, ht, hb = hull_params(c)
        ins = 0.22 if JOINT[0] + 0.01 < c < JOINT[1] - 0.01 else 0.0
        if c < 2.0:  # the nose tip: a short vertical blade edge
            an = as_ = 0.06
        ring = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            u, v = math.cos(a), math.sin(a)
            if v >= 0:
                pv = spow(v, 2 / P_TOP) * (ht - ins)
                pu = spow(u, 2 / P_TOP)
            else:
                pv = spow(v, 2 / P_BOT) * (hb - ins)
                pu = spow(u, 2 / P_BOT)
            rr = yr - pu * (an - ins) if u >= 0 else yr - pu * (as_ - ins)
            tag = "B" if v < 0 else ("N" if u > 0.5 else ("S" if u < -0.5 else "C"))
            ring.append((P(c, rr, HE + pv), tag))
        rings.append((c, ring))
    vr = [[bm.verts.new(p) for p, _ in ring] for _, ring in rings]
    for i in range(len(vr) - 1):
        cm = (rings[i][0] + rings[i + 1][0]) / 2
        zone = "J" if JOINT[0] < cm < JOINT[1] else ("F" if cm < JOINT[0] else "A")
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((vr[i][k], vr[i][j], vr[i + 1][j], vr[i + 1][k]))
            tg = rings[i][1][k][1] if rings[i][1][k][1] == rings[i][1][j][1] else rings[i][1][j][1]
            if zone == "J":
                m = M_SEAM
            elif tg == "B":
                m = M_UNDER
            elif zone == "F":
                m = {"N": M_FWD_N, "C": M_FWD_CROWN, "S": M_FWD_S}[tg]
            else:
                m = {"N": M_BODY_N, "C": M_BODY_CROWN, "S": M_BODY_S}[tg]
            f.material_index = m
            f.smooth = True
    f = bm.faces.new(list(reversed(vr[0])))
    f.material_index = M_FWD_S
    f = bm.faces.new(vr[-1])
    f.material_index = M_UNDER


def crown_strip(bm, c0, c1, r0, r1, lift, mat, n=10, bevel=0.12):
    """A strip lying on the fairing's top surface between (c0..c1, r0..r1), raised `lift` px:
    a closed block whose underside follows the surface 0.2 px under it."""
    rows = [r0 + (r1 - r0) * i / n for i in range(n + 1)]
    cols = [c0, c0 + bevel, c1 - bevel, c1]
    top = []
    bot = []
    for r in rows:
        tr, br = [], []
        for ci, c in enumerate(cols):
            h = hull_top(c, r)
            h = HE if h is None else h
            edge = ci in (0, 3)
            tr.append(bm.verts.new(P(c, r, h + (lift * 0.55 if edge else lift))))
            br.append(bm.verts.new(P(c, r, h - 0.25)))
        top.append(tr)
        bot.append(br)
    faces = []
    for i in range(n):
        for k in range(3):
            faces.append(bm.faces.new((top[i][k], top[i][k + 1], top[i + 1][k + 1], top[i + 1][k])))
            faces.append(bm.faces.new((bot[i][k + 1], bot[i][k], bot[i + 1][k], bot[i + 1][k + 1])))
    for i in range(n):
        faces.append(bm.faces.new((top[i][0], top[i + 1][0], bot[i + 1][0], bot[i][0])))
        faces.append(bm.faces.new((top[i + 1][3], top[i][3], bot[i][3], bot[i + 1][3])))
    faces.append(bm.faces.new(top[0][::-1] + bot[0]))
    faces.append(bm.faces.new(top[-1] + bot[-1][::-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def build_louvres(bm):
    crown_strip(bm, 31.4, 39.0, 6.4, 11.6, 0.12, M_LOUVRE_WELL, n=12, bevel=0.2)  # recessed louvre bed
    for c0 in (31.9, 33.9, 35.9, 37.85):
        crown_strip(bm, c0, c0 + 0.95, 5.9, 11.3, 0.55, M_RIB, n=12, bevel=0.22)
    crown_strip(bm, 8.0, 8.45, 9.1, 14.6, 0.04, M_FWD_LINE, n=8, bevel=0.1)  # forward panel line (c 8)
    crown_strip(bm, 24.0, 30.6, 12.75, 13.35, 0.05, M_SEAM, n=2, bevel=0.1)  # body side seam (row 13)


# --------------------------------------------------------------------------------------------------
# Rounded slabs (chin, deck, sponson): closed, round top and bottom edges
# --------------------------------------------------------------------------------------------------

def inset(poly, d):
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sg = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        nx, ny = -sg * dy / ln, sg * dx / ln  # inward normal
        lines.append((a[0] + nx * d, a[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        l1, l2 = lines[i - 1], lines[i]
        den = l1[2] * l2[3] - l1[3] * l2[2]
        if abs(den) < 1e-9:
            out.append((l2[0], l2[1]))
            continue
        t = ((l2[0] - l1[0]) * l2[3] - (l2[1] - l1[1]) * l2[2]) / den
        out.append((l1[0] + l1[2] * t, l1[1] + l1[3] * t))
    return out


def rslab(bm, poly, h0, h1, top, side, under, edge=None, rt=0.45, rb=0.6, segs=3):
    """poly in (c, r) px. Walls from h0 + rb to h1 - rt, quarter-round edges of those radii."""
    rings = []
    for k in range(segs, 0, -1):
        t = k / segs * math.pi / 2
        rings.append(([(c, r, h0 + rb - rb * math.sin(t)) for c, r in inset(poly, rb * (1 - math.cos(t)))], "u"))
    rings.append(([(c, r, h0 + rb) for c, r in poly], "s"))
    rings.append(([(c, r, h1 - rt) for c, r in poly], "s"))
    for k in range(1, segs + 1):
        t = k / segs * math.pi / 2
        rings.append(([(c, r, h1 - rt + rt * math.sin(t)) for c, r in inset(poly, rt * (1 - math.cos(t)))],
                      "e" if k < segs else "t"))
    vr = [[bm.verts.new(P(*p)) for p in ring] for ring, _ in rings]
    n = len(poly)
    faces = []
    for i in range(len(vr) - 1):
        m = under if i < segs else (side if i == segs else (edge if edge is not None else top))
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((vr[i][k], vr[i][j], vr[i + 1][j], vr[i + 1][k]))
            f.material_index = m
            faces.append(f)
    f = bm.faces.new(vr[-1])
    f.material_index = top
    faces.append(f)
    f = bm.faces.new(list(reversed(vr[0])))
    f.material_index = under
    faces.append(f)
    # Outward winding: fix the whole slab's normals consistently.
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.smooth = False
    return faces


def lens(bm, c, r, h, a, b, d, mat, seg=12, rings=5):
    """A half-ellipsoid dome (closed by a flat base) centred at (c, r, h): a, b px in c, r; d up."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings * 2, radius=1.0)
    verts = res["verts"]
    for v in verts:
        z = max(v.co.z, 0.0)
        v.co = P(c + v.co.x * a, r - v.co.y * b, h + z * d)
    bmesh.ops.remove_doubles(bm, verts=verts, dist=1e-6)
    fs = {f for v in verts if v.is_valid for f in v.link_faces}
    for f in fs:
        f.material_index = mat
        f.smooth = True


def build_chin(bm):
    poly = [(3, 13), (19.4, 13), (20.1, 14), (20.1, 16), (19, 16.6), (18, 17), (17.4, 17.6), (17.1, 18.4), (17.0, 19),
            (15, 19), (15, 18.2), (14.6, 18), (9.4, 18), (9.0, 18.4), (9.0, 19), (8.4, 19.25), (8, 19.6), (7.6, 20),
            (2.4, 20), (1.9, 19.6), (1.9, 15.4)]
    rslab(bm, poly, 0.8, 3.7, M_CHIN, M_CHIN_SIDE, M_UNDER, edge=M_CHIN_EDGE, rt=0.45, rb=0.8)
    # gun slot (row 15) sunk into the block's top, four red gun lights in it
    rslab(bm, [(9.05, 14.6), (16.95, 14.6), (16.95, 16.05), (9.05, 16.05)], 3.0, 3.82, M_SLOT, M_SLOT, M_SLOT,
          rt=0.12, rb=0.1, segs=1)
    for c, m in ((10.5, M_GUN[0]), (12.5, M_GUN[1]), (13.5, M_GUN[2]), (15.5, M_GUN[2])):  # square gun lights
        rslab(bm, [(c - 0.5, 15.0), (c + 0.5, 15.0), (c + 0.5, 15.95), (c - 0.5, 15.95)], 3.2, 4.05, m, m, m,
              rt=0.2, rb=0.1, segs=2)
    # grille strip behind the slot (row 16): six bright ribs
    for c0 in (9.1, 10.1, 12.1, 13.1, 15.1, 16.1):
        rslab(bm, [(c0, 16.1), (c0 + 0.72, 16.1), (c0 + 0.72, 16.95), (c0, 16.95)], 3.3, 3.98, M_GRILLE, M_CHIN_EDGE,
              M_CHIN_EDGE, rt=0.15, rb=0.1, segs=1)
    # nose armour plate over the block's front lobe
    rslab(bm, [(2.3, 15.3), (6.4, 15.3), (6.4, 19.5), (2.6, 19.5)], 3.2, 3.9, M_NOSEPLATE, M_CHIN, M_CHIN,
          rt=0.2, rb=0.1, segs=2)


def build_aft(bm):
    deck = [(23.2, 14.6), (45.2, 14.6), (45.9, 15.4), (45.9, 16.6), (45.1, 17.4), (44.8, 18.4), (24, 18.4), (24, 16),
            (23.2, 16)]
    rslab(bm, deck, 1.0, 4.5, M_DECK, M_CHIN_SIDE, M_UNDER, edge=M_CHIN_EDGE, rt=0.45, rb=0.8)
    spon = [(24, 17.2), (44.9, 17.2), (45.0, 18.6), (43.5, 19.05), (41.4, 19.3), (40, 20), (38.2, 20.95), (36.2, 21.9),
            (34.3, 22.9), (33, 23.6), (31.5, 24), (28.4, 24), (27, 23.6), (26.3, 23), (25.5, 22), (24.6, 21.05),
            (23.0, 20.9), (23.0, 18.1)]
    rslab(bm, spon, 0.9, 3.9, M_SPONSON, M_SPONSON_SIDE, M_UNDER, edge=M_SPONSON, rt=1.0, rb=1.0, segs=4)
    rslab(bm, [(24.6, 19.1), (38.0, 19.1), (38.0, 19.65), (24.6, 19.65)], 3.6, 4.08, M_STRAKE, M_SPONSON, M_SPONSON,
          rt=0.15, rb=0.1, segs=1)
    # red nav light on the sponson's west tip (c 23, rows 19-20)
    lens(bm, 23.6, 19.9, 2.8, 0.75, 0.85, 1.0, M_NAV)
    # pylon carrying the pod
    rslab(bm, [(39.4, 13.4), (45.0, 13.4), (45.0, 15.4), (39.4, 15.4)], 1.2, 3.6, M_PYLON, M_PYLON, M_PYLON,
          rt=0.2, rb=0.3, segs=2)


# --------------------------------------------------------------------------------------------------
# Engine pod
# --------------------------------------------------------------------------------------------------

POD_R, POD_H = 11.95, 4.7


def loft_c(bm, stations, mats, n=28, cap0=None, cap1=None, rc=POD_R, hc=POD_H):
    """Ellipse sections along c: stations (c, a px in r, b px in h); mats per span."""
    vr = []
    for c, a, b in stations:
        ring = []
        for k in range(n):
            t = 2 * math.pi * (k + 0.5) / n
            ring.append(bm.verts.new(P(c, rc - a * math.cos(t), hc + b * math.sin(t))))
        vr.append(ring)
    faces = []
    for i in range(len(vr) - 1):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((vr[i][k], vr[i][j], vr[i + 1][j], vr[i + 1][k]))
            tm = 2 * math.pi * (k + 1) / n
            f.material_index = M_POD_S if (mats[i] == M_POD and math.cos(tm) < 0) else mats[i]
            f.smooth = True
            faces.append(f)
    if cap0 is not None:
        f = bm.faces.new(list(reversed(vr[0])))
        f.material_index = cap0
        faces.append(f)
    if cap1 is not None:
        f = bm.faces.new(vr[-1])
        f.material_index = cap1
        faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def build_pod(bm):
    # dark collar where the pod meets the fairing
    loft_c(bm, [(38.8, 3.5, 3.1), (39.0, 4.15, 3.7), (39.85, 4.15, 3.7), (40.05, 3.8, 3.4)],
           [M_COLLAR] * 3, cap0=M_COLLAR, cap1=M_COLLAR)
    # the nacelle: a fat glowing red can, band ring at c 43, tapering into the nozzle
    st = [(39.95, 3.8, 3.42), (40.3, 3.92, 3.53), (41.2, 4.0, 3.6), (42.95, 4.0, 3.6), (43.0, 4.09, 3.69),
          (43.5, 4.09, 3.69), (43.55, 4.0, 3.6), (44.6, 3.8, 3.42), (45.3, 3.35, 3.0), (45.75, 2.7, 2.45)]
    mats = [M_POD, M_POD, M_POD, M_POD_BAND, M_POD_BAND, M_POD_BAND, M_POD, M_POD, M_POD]
    loft_c(bm, st, mats, cap0=M_POD)
    # nozzle: a dark rim ring and a recessed glowing exhaust face east (the stern)
    loft_c(bm, [(45.75, 2.7, 2.45), (45.95, 2.45, 2.2), (45.95, 1.95, 1.75), (45.6, 1.85, 1.65)],
           [M_POD_RIM, M_POD_RIM, M_EXHAUST], cap1=M_EXHAUST)
    # hot core window on the pod's top (the sprite's orange / yellow, rows 9-11, c 41-44)
    lens(bm, 42.4, 10.3, 7.35, 1.55, 1.25, 0.75, M_CORE, seg=16, rings=5)
    lens(bm, 42.9, 10.45, 7.95, 0.62, 0.5, 0.3, M_HOT, seg=10, rings=3)


# --------------------------------------------------------------------------------------------------
# Build, pieces, shells, export
# --------------------------------------------------------------------------------------------------

def build(coll):
    bm = bmesh.new()
    build_hull(bm)
    build_louvres(bm)
    build_chin(bm)
    build_aft(bm)
    build_pod(bm)
    if MIRROR:  # c -> 48 - c, winding reversed
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


def layout():
    lay = common.load_sprite(ROOT, PIECES[0])["assemblyLayout"]
    ents = [e for e in lay if e["model"] in PIECES]
    cx0 = sum(e["cx"] for e in ents) / len(ents)
    cy0 = sum(e["cy"] for e in ents) / len(ents)
    return [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in ents]


def cull_hidden(obj, ndirs=32):
    """Delete faces no ray from outside can reach."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    dead = []
    for f in bm.faces:
        n = f.normal
        c = f.calc_center_median()
        pts = [c] + [c.lerp(v.co, 0.85) for v in f.verts]
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * 1e-3
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    print("whole tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))
    lay = layout()
    pieces = common.split_assembly(obj, lay, coll)
    shells, total, exports = [], 0, {}
    for name, dx, dy in lay:
        p = pieces[name]
        sealed = p.copy()  # D90/D118: the outline shell from a sealed copy taken before culling
        sealed.data = p.data.copy()
        coll.objects.link(sealed)
        bpy.context.view_layer.update()
        sh = common.outline_shell(sealed, coll, voxel=0.012, faces=2000, inside=0.006)
        sh.name = sh.data.name = f"{name}_outline"
        bpy.data.objects.remove(sealed, do_unlink=True)
        shells.append(sh)
        n = cull_hidden(p) if "--nocull" not in argv else 0
        p.data.set_sharp_from_angle(angle=math.radians(40))
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: culled {n}, {tris} tris")
        exports[name] = (p, sh)
    print("total tris", total)
    for name, (p, sh) in exports.items():  # game contract: piece-local, export path + spriteModels entry
        common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", common.load_sprite(ROOT, name)["sprites"])
    for name, dx, dy in lay:  # scratch / review: pieces back at their assembly offsets
        for o in exports[name]:
            o.location = (dx / 12, -dy / 12, 0)
    bpy.context.view_layer.update()
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + shells, out)
        print("exported", out)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        (rv / "stats.json").write_text(json.dumps({"tris": total, "pal": sorted({k[0] for k in MAT.slots})}))
        review(obj, list(pieces.values()), shells, rv)


def review(whole, pieces, shells, out):
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    sh = scene.display.shading
    for s in shells:
        s.hide_render = True
    eng = None
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            eng = e
            break
        except TypeError:
            pass
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.0
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(15))
    scene.world.use_nodes = True
    bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.06, 0.065, 0.075, 1)
    bgn.inputs[1].default_value = 3.0

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600, rot=None):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot if rot else (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    def shot(path, flat=False, transparent=False):
        if not flat and eng:
            scene.render.engine = eng
            scene.render.film_transparent = transparent
        else:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh.light = "FLAT"
            sh.color_type = "MATERIAL"
            sh.show_cavity = False
            sh.show_object_outline = False
            sh.show_specular_highlight = False
            scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    k = 12
    whole.hide_render = True
    for p in pieces:
        p.hide_render = False
    cam("top", (0, 0, 40), (0, 0, 0), ortho=W / 12, rx=W * k, ry=H * k, rot=(0, 0, 0))
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_lit.png")
    zc = 0.0
    for nm, loc, look, orth, rx, ry in (("side_s", (0, -60, zc), (0, 0, zc), 4.3, 1000, 360),
                                        ("side_n", (0, 60, zc), (0, 0, zc), 4.3, 1000, 360),
                                        ("front", (-60, 0, zc), (0, 0, zc), 2.0, 600, 400),
                                        ("rear", (60, 0, zc), (0, 0, zc), 2.0, 600, 400)):
        cam(nm, loc, look, ortho=orth, rx=rx, ry=ry)
        shot(out / f"{nm}.png")
    d = 7.0
    ctr = Vector((0, 0, zc))
    for nm, az, el in (("q_nose", -55, 30), ("q_stern", 145, 30), ("q_high", 30, 50)):
        a, e = math.radians(az), math.radians(el)
        cam(nm, ctr + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), ctr,
            lens=50, rx=1000, ry=700)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam("game", ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=50, rx=1000, ry=700)
    shot(out / "game.png")
    cam("game_small", ctr + Vector((0, -d * 2.2 * math.sin(t), d * 2.2 * math.cos(t))), ctr, lens=50, rx=300, ry=210)
    shot(out / "game_small.png")
    cam("under", (0, 0, -40), (0, 0, 0), ortho=W / 12 * 1.05, rx=W * 10, ry=H * 10, rot=(math.pi, 0, 0))
    shot(out / "under.png")


if __name__ == "__main__":
    main()
