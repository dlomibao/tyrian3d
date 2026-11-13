"""Rib-backed lava beast (newshe.shp, eight 2x2 pieces in two rows of four, 96 x 56 px), final build.

What it is: a crawling armoured creature (spawned on ground2 off the left edge, it crawls across
the screen and leaves on the right; STARGATE). Seen from above, head to the right: a long hunched
back of overlapping carapace segments growing taller towards the head, each with a rolled rear lip
carrying a thin red rib line that bows as a ')' crescent from the crest to the belly, with a lava
hot spot (orange to white) on it in the upper third just south of the crest, the line itself
cooling to dark red by mid-flank and to the body's red at the belly; a bone knob on each lip; a pink bony
tail hooked round under the tail end; a collar of three bone knobs; a skull-like head with two
glowing yellow eyes in a cranium over a lower jaw, both edged with glowing ridges; and a thin limb
that trails along under the belly with bone knuckles, curling up to the jaw.

Sprite reading (rubric "Reading a sprite"): the dark right half of every band is the plate falling
away from the light and tucking under the next lip, so it is shape plus lighting, not paint; the
1 px ink lines between bands are the joints' shadow; the white spots in the eyes are their hot
cores. The crest of the hump runs along the bone knobs (rows 20 -> 12), well north of the plan's
middle, so the long lit south flank is what the sprite shows.

Units: c, r = assembly px edges (0, 0 = top left of newshe-85); X = (c - 48) / 12, Y = (28 - r) / 12,
Z = h / 12 (h in px).

Run: blender --background --python assembly-newshe-123.py -- [--out x.glb] [--pieces DIR] [--review DIR]
Exports public/models/enemies/<piece>.glb and the spriteModels entries.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
WT = common.repo_root(__file__)
sys.path.insert(0, str(WT / "tools"))
import sprite_mask as S  # noqa: E402

ROOT = WT
NAME = "assembly-newshe-123"
PIECES = ["newshe-85", "newshe-87", "newshe-89", "newshe-91",
          "newshe-123", "newshe-125", "newshe-127", "newshe-129"]
W, H = 96, 56
PX = 1 / 12
# Assembly pixel (0, 0) is screen (-20, -32); the assembly centre, screen (28, -4), is the origin.
CX0, CY0 = 28, -4


# Per-column body edges from the sprite's inner mask.
def _masks():
    idx, cols = S.load(NAME, None, str(WT / "reference" / "models"))
    return S.masks(idx, cols), idx, cols


def region(c, r):
    """Which part a sprite pixel belongs to: hook (pink tail), limb, body."""
    # the limb: below the slit that runs from (37, 38) to (41, 41), along the bottom (rows 46+) and,
    # past the jaw, below the diagonal from (70, 38) to (63, 45)
    if 37 <= c <= 41 and r >= 38 + (c - 37) * 0.8:
        return "limb"
    if (41 < c < 50 and r >= 46) or (50 <= c < 67 and r >= 48):
        return "limb"
    if c >= 67 and r > 37 + max(0, 71 - c):
        return "limb"
    return "body"


def body_edges(mk):
    """{col: (north_row, south_row)} of body pixels in the inner mask (whole pixels, inclusive)."""
    out = {}
    for c in range(W):
        rows = [r for r in range(H) if mk["inner"][r][c] and region(c, r) == "body"]
        if rows:
            out[c] = (min(rows), max(rows))
    return out


def P(c, r, h):
    return Vector(((c - 48.0) * PX, (28.0 - r) * PX, h * PX))


# --------------------------------------------------------------------------------------------------
# pchip (monotone cubic) for smooth station curves (D52)
# --------------------------------------------------------------------------------------------------

def pchip(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(xs)
    hs = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / hs[i] for i in range(n - 1)]
    m = [0.0] * n
    if n == 2:
        m = [d[0], d[0]]
    else:
        for i in range(1, n - 1):
            if d[i - 1] * d[i] <= 0:
                m[i] = 0.0
            else:
                w1, w2 = 2 * hs[i] + hs[i - 1], hs[i] + 2 * hs[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        m[0] = d[0]
        m[-1] = d[-1]

    def f(x):
        if x <= xs[0]:
            return ys[0] + m[0] * (x - xs[0]) * 0
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / hs[i]
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1
        h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2
        h11 = t ** 3 - t ** 2
        return h00 * ys[i] + h10 * hs[i] * m[i] + h01 * ys[i + 1] + h11 * hs[i] * m[i + 1]
    return f


# --------------------------------------------------------------------------------------------------
# Materials
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

    def __call__(self, index, metallic=0.2, roughness=0.5, emit=0.0, spec=None):
        key = (index, metallic, roughness, emit, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nshe123a{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            if spec is not None:
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


MAT = Mats()
# Carapace: a satin chitin, the sprite's red ramp (median 114 over the plates, 115 behind the lips).
SHELL = dict(metallic=0.25, roughness=0.42, spec=0.6)
M_SHELL = MAT(114, **SHELL)
M_SHELL_HI = MAT(115, **SHELL)
M_SHELL_DK = MAT(113, **SHELL)  # a plate's front half, falling away under the next lip
M_UNDER = MAT(114, 0.15, 0.6)
M_CORE = MAT(113, 0.1, 0.75)  # the mouth's recess
GLOW = dict(metallic=1.0, roughness=0.85)  # D126/D173 glow surfaces
M_RIB = MAT(121, emit=1.0, **GLOW)  # glowing joints and ridges (sprite median 121)
M_RIB_HOT = MAT(123, emit=1.0, **GLOW)  # the tail end's hotter rim
M_RIB_BEAD = MAT(122, emit=1.0, **GLOW)  # the lip's hottest line
M_RIDGE = MAT(115, **SHELL)  # the growth ridge's lit crest
M_EMBER = MAT(119, emit=0.6, **GLOW)  # the glow fading into the plate behind each lip
M_RIB_DIM = MAT(120, emit=0.8, **GLOW)  # the glow's falling edge
M_LIP = MAT(118, **SHELL)  # the unlit run of each rib lip (sprite 116-119 away from the hot band)
M_LIP_HI = MAT(119, **SHELL)  # its rolled crest
M_MOUTH = MAT(112, 0.1, 0.8)  # the mouth's deep inside
M_EYE = MAT(125, emit=1.5, **GLOW)
M_EYE_CORE = MAT(127, emit=1.4, **GLOW)
BONE = dict(metallic=0.1, roughness=0.24, spec=1.0)  # polished bone: its pink highlights are sheen
M_BONE = MAT(70, **BONE)  # knobs and tail (sprite median 70)
M_BONE_DK = MAT(68, **BONE)  # the belly limb's knuckles (browner, 67-70)
M_LIMB = MAT(116, **SHELL)


# --------------------------------------------------------------------------------------------------
# Mesh helpers (closed lofts, tubes, ellipsoids)
# --------------------------------------------------------------------------------------------------

def bridge(bm, rings, mats, cap_start=True, cap_end=True):
    faces = []
    n = len(rings[0])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mats[i]
            f.smooth = True
            faces.append(f)
    for ring, m, rev in ((rings[0], mats[0], True), (rings[-1], mats[-1], False)):
        if (cap_start if rev else cap_end):
            # fan cap round the centre: no long slivers
            cen = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for k in range(n):
                j = (k + 1) % n
                f = bm.faces.new((ring[j], ring[k], cen) if rev else (ring[k], ring[j], cen))
                f.material_index = m
                f.smooth = True
    return faces


DOME_E = 0.72  # cross-section exponent: steep sides at the ground, full shoulders


def arch(c, n, s, rc, h, npts=22, foot=0.0):
    """Cross-section at column c: from the south edge s over the crest (row rc, height h px) to the
    north edge n (rows are edges, px); `foot` lifts the ends off z = 0 (a closed bottom chord)."""
    pts = []
    for k in range(npts + 1):
        t = math.pi * k / npts  # 0 = south foot, pi = north foot
        ct = math.cos(t)
        r = rc + (s - rc) * ct if ct >= 0 else rc + (rc - n) * ct
        z = foot + (h - foot) * (abs(math.sin(t)) ** DOME_E)
        pts.append(P(c, r, z))
    return pts


class Surf:
    """A loft's height field, for putting ridges and knobs on it."""
    def __init__(self, stations):
        self.st = stations  # (c, n, s, rc, h)

    def z(self, c, r):
        st = self.st
        for a, b in zip(st, st[1:]):
            if a[0] <= c <= b[0]:
                u = (c - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0
                n, s, rc, h = (a[i] + (b[i] - a[i]) * u for i in range(1, 5))
                if r <= n or r >= s:
                    return 0.0
                q = (r - rc) / (s - rc) if r >= rc else (rc - r) / (rc - n)
                return h * (max(0.0, 1 - q * q) ** (DOME_E / 2))
        return 0.0


SURFS = []


def zat(c, r):
    return max([s.z(c, r) for s in SURFS] + [0.0])


def loft(bm, stations, mats, npts=22):
    """stations: (c, n, s, rc, h); mats: one per band or a single index."""
    if isinstance(mats, int):
        mats = [mats] * (len(stations) - 1)
    rings = [[bm.verts.new(p) for p in arch(c, n, s, rc, h, npts)] for c, n, s, rc, h in stations]
    faces = bridge(bm, rings, list(mats) + [mats[-1]])
    SURFS.append(Surf(stations))
    return faces


def tube(bm, path, sides=10, mat=0, cap=True, mats=None):
    """path: (c, r, z_px, half_width_px, half_height_px). Rings stand perpendicular to the path in XY."""
    pts = [P(c, r, z) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, hh) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (hh * PX * math.sin(a))))
        rings.append(ring)
    return bridge(bm, rings, (list(mats) + [mats[-1]]) if mats else [mat] * len(rings), cap, cap)


def ellipsoid(bm, c, r, z, rx, ry, rz, mat, seg=14, rings=8, flat_bottom=0.0):
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        zz = v.co.z
        if flat_bottom and zz < -flat_bottom:
            zz = -flat_bottom
        v.co = P(c + v.co.x * rx, r - v.co.y * ry, z + zz * rz)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


# --------------------------------------------------------------------------------------------------
# The plan: per-column body edges from the sprite's inner mask, smoothed
# --------------------------------------------------------------------------------------------------

MK, IDX, _COLS = _masks()
EDGE = body_edges(MK)


def _smooth(vals, sigma=0.6, jump=2.5):
    """Gaussian along the columns, edge-preserving: a neighbour across a step bigger than `jump` px
    (the lobe's end, the jaw) is left out, so steps stay steps."""
    cs = sorted(vals)
    out = {}
    for c in cs:
        wsum = vsum = 0.0
        for d in range(-3, 4):
            if c + d in vals and abs(vals[c + d] - vals[c]) <= jump:
                w = math.exp(-d * d / (2 * sigma * sigma))
                wsum += w
                vsum += w * vals[c + d]
        out[c] = vsum / wsum
    return out


N_ROW = _smooth({c: e[0] for c, e in EDGE.items()})  # top edge of the first row
S_ROW = _smooth({c: e[1] + 1.0 for c, e in EDGE.items()})  # bottom edge of the last row


def edge_at(tab, x):
    """Edge at continuous column x (pixel c spans [c, c+1]; its value sits at c + 0.5)."""
    u = x - 0.5
    c0 = math.floor(u)
    c0 = max(min(tab), min(max(tab) - 1, c0))
    t = min(1.0, max(0.0, u - c0))
    return tab[c0] * (1 - t) + tab[c0 + 1] * t


def north(x):
    return edge_at(N_ROW, x)


def south(x):
    return edge_at(S_ROW, x)


# The crest follows the bone knobs (rows 20 -> 12), well north of the plan's middle.
CREST = pchip([(c + 0.5, r + 0.5) for c, r in ((10, 23.0), (19.7, 20.6), (25.3, 18.9), (32.8, 16.8),
                                               (41.4, 15.0), (50.9, 14.2), (58.0, 14.6), (63.0, 17.0),
                                               (68.0, 18.5))])

# Segments, tail to neck: (rear lip column, front end column, height px behind the lip). The lips
# sit at the north edge's steps (cols 18, 25, 33, 42, 51), so their crests and front faces cover the
# sprite's rib lines (cols 19, 25, 34, 43, 53).
SEGS = [(18.5, 26.1, 9.0), (25.4, 33.9, 10.6), (33.2, 42.9, 12.3), (42.2, 51.6, 13.8),
        (51.2, 62.0, 15.2)]


# Each rib runs straight down from its north foot over the crest (the sprite's hot lips hold their
# column, 19, 25, 33, 42, 52, from row 6 to row 30) and then bows forward, towards the head, down
# the south flank to the belly: +1 px at row 31, +3 at row 34, +5 at rows 37-43 (ribs 19, 42, 52
# traced in the sprite). Column offset (px, + = towards the head) at arc parameter cos(t): -1 north
# foot, 0 crest, +1 south foot.
RIB_OFF = pchip([(-1.0, -1.8), (-0.5, -0.8), (0.0, 0.0), (0.3, 1.1), (0.5, 2.2), (0.7, 3.3),
                 (0.85, 4.0), (1.0, 4.3)])


def bow_of(ct, scale=1.0):
    """Column offset (towards the tail, px) of a rib at arc parameter cos(t); `scale` = the segment's
    share of the full sweep."""
    return -scale * RIB_OFF(ct)


SEG_NPTS = 40  # fine arc steps: the glow is graded face by face along each lip


def bowed_ring(x, dn, hk, npts=SEG_NPTS, bow=1.0):
    """A plate cross-section at column x whose vertices follow the rib's crescent: each vertex is
    moved along the columns by the rib offset at its arc parameter and placed on the plan edges at
    the column it ends up at."""
    pts = []
    for k in range(npts + 1):
        t = math.pi * k / npts
        ct = math.cos(t)
        xx = x - bow_of(ct, bow)
        n, s, rc = north(xx) - dn, south(xx) + dn, CREST(xx)
        r = rc + (s - rc) * ct if ct >= 0 else rc + (rc - n) * ct
        z = hk * (abs(math.sin(t)) ** DOME_E)
        pts.append(P(xx, r, z))
    return pts


class BowSurf(Surf):
    """A segment's height field: the stations' surface sheared along the rib's crescent."""
    def __init__(self, stations, bow):
        super().__init__(stations)
        self.bow = bow

    def z(self, c, r):
        cc = c
        for _ in range(3):
            n, s, rc = north(cc), south(cc), CREST(cc)
            ct = (r - rc) / max(0.5, s - rc) if r >= rc else (r - rc) / max(0.5, rc - n)
            cc = c + bow_of(max(-1.0, min(1.0, ct)), self.bow)
        return Surf.z(self, cc, r)




def glow_mat(index):
    """A palette material of the lip at `index`: >= 119 glows (D126/D173 glow surface, emission
    rising with the index), 116-118 is the lit red lip, below that the plate's own red."""
    if index >= 119:
        return MAT(min(index, 127), emit=round(0.55 + 0.1 * (index - 119), 2), **GLOW)
    if index >= 116:
        return MAT(index, **SHELL)
    return M_SHELL_HI


def paint_lip(faces, rings, peak, lo=115):
    """The lip itself is shell, not glow: the sprite's body is dark maroon round every rib and the
    rib is a thin red line (rib_line), its hot spots beads on it (hot_bead). Only the rolled crest
    warms a step towards the belly-side red where the line runs."""
    n = len(rings[0])
    npts = n - 1
    for i, m in enumerate((M_SHELL_DK, M_SHELL_HI, M_SHELL_HI, M_SHELL, M_SHELL)):
        for k in range(npts):
            faces[i * n + k].material_index = m


# The rib line's colour along its arc (cos t: -1 north foot, 0 crest, +1 belly): red (119-121)
# over the crest and the upper flank, dark red (119-120) by mid-flank, near the body's own red at
# the belly (sprite trace of the six ribs, rows 4 -> 45).
def rib_index(ct):
    if ct < -0.55:
        return 118
    if ct < -0.1:
        return 119
    if ct < 0.45:
        return 120
    if ct < 0.62:
        return 119
    if ct < 0.78:
        return 118
    if ct < 0.9:
        return 117
    return 116


def rib_line(bm, x, dn, h, bow):
    """The rib's thin red line along the lip's rolled crest (the ring at column x), following the
    crescent, sunk into the lip so only its top stands proud; tapered at both feet."""
    pts = bowed_ring(x, dn, h, bow=bow)
    npts = len(pts) - 1
    path, mats = [], []
    for k, p in enumerate(pts):
        t = math.pi * k / npts
        if math.sin(t) < 0.12:
            continue
        c, r = p.x * 12 + 48, 28 - p.y * 12
        taper = min(1.0, 0.45 + 2.2 * math.sin(t))
        path.append((c, r, p.z * 12 - 0.05, 0.55 * taper, 0.5 * taper))
        mats.append(glow_mat(rib_index(math.cos(t))))
    tube(bm, path, sides=8, mats=mats[:-1])


# The sprite's hot spots on the ribs (pixel centres): (lip column a, row of the hot centre, half
# length along the rib px, peak index). All in the upper third, just south of the crest; the two
# tallest plates also show a small one at their north tip.
HOT = {11.9: [(22.6, 4.6, 127)], 18.5: [(25.5, 3.4, 124)], 25.4: [(24.0, 3.6, 125)],
       33.2: [(23.8, 4.4, 124)], 42.2: [(24.0, 3.0, 127), (7.2, 1.8, 125)],
       51.2: [(27.0, 2.8, 127), (5.4, 1.6, 125)]}


def hot_bead(bm, a, dn, h, bow, row, half, peak):
    """A hot spot on the rib line: nested elongated beads along the rib (red-orange rim, orange,
    yellow, a white-hot core for the hottest), each a step smaller and standing a hair prouder, so
    the heat rises smoothly to the centre instead of in painted blocks."""
    pts = bowed_ring(a, dn, h, bow=bow)
    # the ring point nearest the row: its column and height, and the rib's direction there
    best = min(range(len(pts)), key=lambda k: abs((28 - pts[k].y * 12) - row))
    k0, k1 = max(0, best - 1), min(len(pts) - 1, best + 1)
    p = pts[best]
    d = pts[k1] - pts[k0]
    ang = math.atan2(-d.x, d.y)  # lean of the rib off the row direction
    c, r, z = p.x * 12 + 48, 28 - p.y * 12, p.z * 12
    layers = [(1.0, 1.25, 120), (0.85, 1.15, 121), (0.7, 1.0, 122), (0.55, 0.85, 123), (0.42, 0.7, 124),
              (0.3, 0.55, 125)]
    if peak >= 127:
        layers.append((0.18, 0.4, 127))
    for i, (s, w, idx) in enumerate(layers):
        if idx > peak:
            break
        ellipsoid_rot(bm, c, r, z + 0.05 + 0.08 * i, w, half * s, 0.6 + 0.04 * i, ang,
                      glow_mat(idx), seg=14, rings=8)


def ellipsoid_rot(bm, c, r, z, rx, ry, rz, ang, mat, seg=14, rings=8):
    """ellipsoid() with its long (row) axis leaned by `ang` radians towards the columns."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    ca, sa = math.cos(ang), math.sin(ang)
    for v in res["verts"]:
        x, y = v.co.x * rx, v.co.y * ry
        v.co = P(c + x * ca - y * sa, r - (x * sa + y * ca), z + v.co.z * rz)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


def segment(bm, a, b, hk, bow=1.0, peak=124):
    """One carapace plate: a rolled rear lip at column a (the joint, its lava glow graded along it),
    the plate holding its height over its rear half, then falling away over its front half to tuck
    under the next lip, so the trailing half reads darker by its shape (turned from the light)."""
    spec = [(a - 0.7, -1.0, hk - 2.2), (a - 0.35, 0.15, hk - 0.4), (a + 0.2, 0.3, hk + 0.45),
            (a + 0.9, 0.2, hk + 0.3), (a + 1.6, 0.0, hk), (a + 2.6, 0.0, hk * 0.99)]
    mats = [M_LIP, M_LIP_HI, M_LIP, M_SHELL_HI, M_SHELL_HI]

    def fall(f):  # share of hk the plate has dropped at fraction f from lip to front end
        u = min(1.0, max(0.0, (f - 0.3) / 0.7))
        return 0.04 * f + 0.42 * (u * u * (3 - 2 * u))

    # a growth ridge across the middle of the longer plates (the sprite's second, fainter arc)
    xm = a + 0.45 * (b - a) if b - a >= 7 else None
    xs = []
    x = a + 3.6
    while x < b - 0.3:
        if xm is None or abs(x - xm) > 0.7:
            xs.append((x, 0.0))
        x += 0.9
    if xm is not None:
        xs += [(xm - 0.5, 0.0), (xm - 0.15, 0.4), (xm + 0.25, 0.4), (xm + 0.6, 0.0)]
        xs.sort()
    for x, bump in xs:
        f = (x - a) / (b - a)
        spec.append((x, 0.08 * (bump > 0), hk * (1.0 - fall(f)) + bump))
        mats.append(M_RIDGE if bump > 0 else (M_SHELL_HI if f < 0.3 else M_SHELL if f < 0.55 else M_SHELL_DK))
    spec.append((b, -0.3, hk * (1.0 - fall(1.0))))
    mats.append(M_SHELL_DK)  # the tuck under the next lip
    spec.append((b + 0.5, -1.2, hk * (1.0 - fall(1.0)) - 1.5))
    rings = [[bm.verts.new(p) for p in bowed_ring(x, dn, h, bow=bow)] for x, dn, h in spec]
    faces = bridge(bm, rings, mats + [mats[-1]])
    paint_lip(faces, rings, peak)
    lx, ldn, lh = spec[2]
    rib_line(bm, lx, ldn, lh, bow)
    for row, half, pk in HOT.get(a, []):
        hot_bead(bm, lx, ldn, lh, bow, row, half, pk)
    SURFS.append(BowSurf([(x, north(x) - dn, south(x) + dn, CREST(x), h) for x, dn, h in spec], bow))


def tail_end(bm):
    """The tail: a low rounded cap (cols 4-12) that carries the bony hook, under the tail-end plate
    (cols 12-18) with its hot glowing rim."""
    hs = pchip([(3.9, 1.2), (4.6, 3.0), (6.0, 4.2), (9.0, 5.0), (12.6, 5.4)])
    st = []
    for x in (3.9, 4.3, 4.9, 5.8, 7.0, 8.2, 9.4, 10.6, 11.8, 12.6):
        n, s = north(x), south(x)
        if x < 11.5:  # the hook's own arc closes the cap's south side; the slit inside it stays open
            s = min(s, 25.2 + max(0.0, x - 8.4) * 2.4)
        st.append((x, n, s, (n + s) / 2 - 1.5, hs(x)))
    loft(bm, st, M_UNDER)
    segment(bm, 11.9, 20.0, 7.6, bow=0.5, peak=125)


def neck(bm):
    """The neck between the last plate and the head: a lower collar under the three bone knobs."""
    hs = pchip([(54.0, 11.0), (59.5, 12.5), (63.0, 12.0), (66.5, 11.0), (68.5, 9.5)])
    stations = []
    x = 54.0
    while x <= 68.6:
        n, s = north(x), south(x)
        stations.append((x, n, s, CREST(x) + 1.0, hs(x)))
        x += 1.0
    loft(bm, stations, M_SHELL)


HEAD_H = pchip([(65.5, 10.5), (70.0, 11.2), (75.0, 10.6), (80.0, 9.0), (84.0, 6.6), (86.6, 4.0),
                (88.0, 1.4)])
JAW_H = pchip([(65.5, 6.5), (70.0, 7.0), (76.0, 6.8), (81.0, 6.0), (85.0, 4.4), (87.2, 2.4),
               (88.0, 1.0)])
# The mouth: the sprite's dark slot rows 24-30 (cols 66-80) between the cranium's lower edge (the ink
# line at row 25) and the jaw's rim, closing at the cheek (cols 82-86).
CRANIUM_S = pchip([(65.5, 24.8), (72.0, 24.6), (78.0, 24.9), (82.0, 25.8), (85.0, 27.2), (88.0, 28.4)])
JAW_N = pchip([(65.5, 29.6), (72.0, 30.0), (78.0, 30.0), (82.0, 29.2), (85.0, 28.3), (88.0, 27.2)])


def darken_mouth(faces, inside):
    """The walls of the mouth slot (faces whose centre `inside(c, r, h)` says is in it) go dark."""
    for f in faces:
        cen = f.calc_center_median()
        if inside(cen.x * 12 + 48, 28 - cen.y * 12, cen.z * 12):
            f.material_index = M_CORE


def head(bm):
    # Cranium: rows north .. 25.5, crest between the eyes.
    st = []
    x = 65.5
    while x <= 88.01:
        xx = min(x, 87.5)
        n = north(xx) if x < 87.6 else 20.5
        s = CRANIUM_S(x)
        st.append((x, n, s, (n + s) / 2 - 0.5, HEAD_H(x)))
        x += 1.1 if x < 84 else 0.9
    darken_mouth(loft(bm, st, M_SHELL),
                 lambda c, r, h: c < 83.5 and r > CRANIUM_S(c) - 1.4 and h < HEAD_H(c) * 0.62)
    # Jaw: rows 26 .. south, crest at row 31.
    st = []
    x = 65.5
    while x <= 88.01:
        n = JAW_N(x)
        s = south(min(x, 87.5))
        if x > 87.0:
            s = s - (x - 87.0) * 4
        st.append((x, n, s, (n + s) / 2 - 0.3, JAW_H(x)))
        x += 1.1 if x < 84 else 0.8
    darken_mouth(loft(bm, st, M_SHELL),
                 lambda c, r, h: c < 83.5 and r < JAW_N(c) + 0.9 and h < JAW_H(c) * 0.55)
    # The mouth's floor, deep in the slot between them (the throat).
    st = [(65.0, 23.0, 31.0, 27.2, 1.6), (75.0, 23.0, 31.0, 27.4, 1.6), (83.0, 23.5, 30.5, 27.4, 1.4),
          (86.5, 24.5, 29.5, 27.2, 1.0)]
    loft(bm, st, M_MOUTH, npts=12)


def ridge(bm, pts, w=0.7, hh=0.55, mat=None, lift=-0.1, sides=8, px=True):
    """A glowing ridge lying on the surfaces along pts (c, r: pixel indices, or edge coords with
    px=False); tapered at both ends."""
    mat = M_RIB if mat is None else mat
    if px:
        pts = [(c + 0.5, r + 0.5) for c, r in pts]
    n = len(pts)
    path = []
    for i, (c, r) in enumerate(pts):
        taper = 1.0 if 0 < i < n - 1 else 0.45
        path.append((c, r, zat(c, r) + lift, w * taper, hh * taper))
    tube(bm, path, sides=sides, mat=mat)


def rolled_edge(bm, pts, glow=None, w=1.0, hh=1.05, crest=None):
    """A raised rolled edge of shell along pts (pixel indices) standing ~1 px proud of the surface,
    with a glowing bead along its crest (the sprite's hot ridge lines); tapered at both ends."""
    pts = [(c + 0.5, r + 0.5) for c, r in pts]
    n = len(pts)
    roll, bead = [], []
    for i, (c, r) in enumerate(pts):
        taper = 1.0 if 0 < i < n - 1 else 0.4
        z = zat(c, r)
        roll.append((c, r, z + 0.15, w * taper, hh * taper))
        bead.append((c, r, z + 0.15 + hh * taper * 0.82, w * 0.55 * taper, 0.42 * taper))
    tube(bm, roll, sides=10, mat=M_RIDGE)
    if glow is not None:
        cm = [glow] * (len(bead) - 1) if crest is None else crest  # per span: the glow fades along it
        tube(bm, bead, sides=8, mats=cm)


def eyes(bm):
    """Each eye: a glowing orb (yellow, white-hot core, its orange fringe trailing to the right as in
    the sprite) set in a raised socket rim of shell."""
    for c, r, rx, ry, cc, cr in ((73.9, 14.9, 3.9, 2.3, 72.5, 14.5), (73.1, 21.4, 4.4, 2.3, 72.0, 21.0)):
        z = zat(c, r)
        ring = [(c + 0.3 + rx * 1.2 * math.cos(a) - 0.5, r + ry * 1.32 * math.sin(a) - 0.5)
                for a in [2 * math.pi * k / 20 for k in range(21)]]
        path = [(pc + 0.5, pr + 0.5, zat(pc + 0.5, pr + 0.5) + 0.1, 0.75, 0.95) for pc, pr in ring]
        tube(bm, path, sides=8, mat=M_SHELL_HI)
        ellipsoid(bm, c + 0.6, r, z - 0.6, rx * 1.02, ry * 0.98, 1.5, M_RIB_BEAD, seg=18, rings=8)
        ellipsoid(bm, c - 0.3, r, z - 0.35, rx * 0.86, ry * 0.86, 1.55, M_EYE, seg=16, rings=8)
        ellipsoid(bm, cc, cr, z - 0.1, 1.7, 1.3, 1.45, M_EYE_CORE, seg=12, rings=6)


def head_ridges(bm):
    """The skull's raised rolled edges with their glowing beads (sprite pixel coordinates)."""
    # the cranium's right rim, from the brow down the cheek to the jaw's hinge
    rolled_edge(bm, [(79.5, 12.0), (82.4, 13.6), (84.8, 16.0), (86.2, 19.5), (86.7, 23.0), (86.2, 26.5),
                     (85.2, 29.0)], M_RIB, w=1.0)
    # the jaw's upper mandible (the mouth's lower lip), joining the rim at the hinge
    rolled_edge(bm, [(71.5, 31.2), (74.0, 32.0), (77.0, 32.2), (80.0, 31.9), (82.6, 31.0), (84.3, 29.8),
                     (85.0, 28.6)], M_RIB, w=0.95,
                crest=[M_RIB_DIM, M_RIB, M_RIB, M_RIB_BEAD, M_RIB_HOT, M_RIB])
    # the jaw's lower edge, running down from the chin
    rolled_edge(bm, [(64.0, 29.3), (66.5, 30.0), (68.8, 31.3), (70.8, 32.8), (72.8, 34.2), (75.0, 35.4),
                     (77.5, 36.0), (80.0, 35.9)], M_RIB, w=0.9,
                crest=[M_LIP_HI, M_RIB_DIM, M_RIB_BEAD, M_RIB, M_RIB, M_RIB_DIM, M_RIB_DIM])
    # the lower eye's trail back along the cheek: a low rolled edge, only warm
    rolled_edge(bm, [(75.6, 21.4), (78.0, 21.6), (80.3, 21.5), (82.0, 22.4), (83.4, 23.8)], M_EMBER,
                w=0.75, hh=0.8)


def knobs(bm):
    # bone knobs on the crest at each lip (cluster centres of the sprite's pinks), and the collar
    for c, r, rx, ry, rz in ((19.9, 20.1, 1.5, 2.0, 1.5), (25.6, 18.4, 1.7, 1.8, 1.6),
                             (33.0, 16.2, 2.6, 1.8, 1.8), (41.6, 14.3, 2.7, 1.8, 1.9),
                             (51.2, 13.4, 3.4, 1.8, 2.0),
                             (64.3, 11.9, 3.2, 2.6, 2.2), (63.0, 18.3, 3.0, 2.3, 2.1),
                             (65.3, 24.0, 2.7, 1.5, 1.8)):
        c, r = c + 0.5, r + 0.5
        z = zat(c, r)
        ellipsoid(bm, c, r, z - rz * 0.25, rx * 0.88, ry * 0.88, rz * 1.15, M_BONE)


def tail_hook(bm):
    """The pink bony tail hooked round under the tail end: vertebrae along a tapering curve."""
    ctrl = [(12.5, 20.0, 1.5), (10.5, 20.6, 2.4), (8.4, 22.0, 2.9), (6.6, 23.8, 2.4), (5.8, 25.4, 1.8),
            (5.3, 26.8, 1.2), (5.4, 28.0, 1.0), (6.1, 29.2, 1.2), (7.2, 30.4, 1.4), (8.6, 31.6, 1.5),
            (10.4, 32.9, 1.4), (13.0, 33.6, 1.3), (16.0, 33.8, 0.9), (17.2, 33.8, 0.5)]
    # resample along the curve
    pts = []
    for (c0, r0, w0), (c1, r1, w1) in zip(ctrl, ctrl[1:]):
        for k in range(2):
            t = k / 2
            pts.append((c0 + (c1 - c0) * t, r0 + (r1 - r0) * t, w0 + (w1 - w0) * t))
    pts.append(ctrl[-1])
    path = []
    for i, (c, r, w) in enumerate(pts):
        bead = 1.0 + 0.1 * math.cos(i * 2 * math.pi / 3)  # vertebrae
        hh = w * 0.85 * bead
        path.append((c, r, zat(c, r) + hh * 0.35, w * bead, hh))
    tube(bm, path, sides=12, mat=M_BONE)


LIMB = [(c + 0.5, r + 0.5, w) for c, r, w in (
    (37.6, 43.6, 1.5), (38.8, 46.0, 1.3), (41.5, 47.4, 1.3), (45.5, 48.0, 1.2), (50.0, 48.0, 0.9),
    (54.0, 48.1, 1.0), (58.0, 48.5, 1.2), (62.0, 49.0, 1.5), (66.0, 49.4, 1.7), (70.0, 49.2, 1.6),
    (73.5, 48.8, 1.3), (76.5, 47.8, 1.0), (79.0, 46.7, 0.9), (81.3, 45.3, 0.8), (83.0, 43.8, 0.7),
    (84.5, 42.3, 0.65), (85.6, 41.0, 0.55), (86.4, 40.0, 0.45))]


def limb(bm):
    path = [(c, r, 1.5, w, 1.3) for c, r, w in LIMB]
    path[0] = (path[0][0], path[0][1], 2.5, path[0][3], 1.6)
    tube(bm, path, sides=10, mat=M_LIMB)
    # the glowing seam on its lower (south) side
    seam = [(c + 0.0, r + w * 0.55, 1.3, w * 0.45, 0.65) for c, r, w in LIMB[1:-2]]
    tube(bm, seam, sides=8, mat=M_RIB)
    for c, r, rx, ry, rz in ((37.9, 43.9, 1.8, 2.0, 2.0), (58.3, 48.3, 2.4, 1.6, 1.9), (67.8, 49.7, 2.2, 1.4, 1.8)):
        ellipsoid(bm, c, r, 1.6, rx, ry, rz, M_BONE_DK)


def build(coll):
    bm = bmesh.new()
    tail_end(bm)
    for (a, b, hk), bow, peak in zip(SEGS, (0.85, 0.85, 0.9, 1.0, 1.0), (123, 123, 123, 122, 122)):
        segment(bm, a, b, hk, bow, peak)
    neck(bm)
    head(bm)
    eyes(bm)
    head_ridges(bm)
    knobs(bm)
    tail_hook(bm)
    limb(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


# --------------------------------------------------------------------------------------------------
# Outline shell (D51/D90), keeping every island
# --------------------------------------------------------------------------------------------------

def shell_all_islands(obj, collection, voxel=0.02, faces=3000, smooth=4, inside=0.006, min_extent=0.004):
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    seen, dead = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        xs = [q.co.x for q in isl]
        ys = [q.co.y for q in isl]
        if (max(xs) - min(xs)) * (max(ys) - min(ys)) < min_extent:
            dead.extend(isl)
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -inside
        common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def flat_seam_caps(piece, eps=1e-4):
    """The cut faces split_assembly fills at the piece's box are flat-shaded, so the smooth hull's
    normals along the seam don't bend towards them (a dark line across the joined assembly)."""
    me = piece.data
    for f in me.polygons:
        vs = [me.vertices[i].co for i in f.vertices]
        if (all(abs(abs(v.x) - 1.0) < eps for v in vs) and abs(abs(vs[0].x) - 1.0) < eps) or \
           all(abs(abs(v.y) - 14 / 12) < eps for v in vs):
            f.use_smooth = False


def sink_shell(shell, model, margin=0.6 * PX, reach=1.4 * PX, floor=0.8 * PX):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only;
    newshv-10's sink, D185). The voxel copy bridges the creases between plates, round the knobs and
    where the limb runs beside the belly, and stood above the surface there: its back faces drew as
    black fins on the south flank. Every shell vertex is dropped to `margin` under the lowest model
    top within `reach` of it seen from straight above (a vertex just off the plan, in a notch between
    two plates' feet or in the slot beside the limb, takes its neighbours' lowest top). x and y are
    untouched, so the silhouette, and the ink round it, is the same."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    mm = model.matrix_world
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        tops, centre, ring = [], None, []
        misses = 0
        for rad, ks in ((0.0, 1), (0.35 * reach, 12), (0.7 * reach, 12), (reach, 12)):
            for k in range(ks):
                a = 2 * math.pi * k / ks
                h = tree.ray_cast(mm.inverted() @ Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)),
                                  Vector((0, 0, -1)))
                if h[0] is None:
                    misses += 1
                if h[0] is not None:
                    tops.append((mm @ h[0]).z)
                    if rad == 0.0:
                        centre = tops[-1]
                    elif rad == reach:
                        ring.append(tops[-1])
        if not tops:
            continue
        # in a groove (the V between a plate's fallen front and the next lip) the game's inflated
        # hull would rise out of the groove's floor: sink deeper there, by how far the surface round
        # the vertex stands above it (0 on the convex rims, so the silhouette's ink is untouched)
        groove = 0.0
        if centre is not None and len(ring) >= 8:
            groove = min(3.5 * PX, 1.3 * max(0.0, sum(ring) / len(ring) - centre))
        z = min(w.z, max(0.0, min(tops) - margin - groove))
        # well inside the plan (model under every probe out to `reach`) the shell has no silhouette
        # to ink: it goes down flat under the body, so the game's inflated hull cannot rise out of
        # the creases between plates, round the beads or at the limb's join as black fins
        if misses == 0:
            z = min(z, floor)
        # under an overhang (a plate's front tucked under the next lip) the lowest top seen from
        # above is still the lip: a vertex left in the slot between them is outside the body, so it
        # goes on down to the tucked plate under it
        mi = mm.inverted()
        for _ in range(4):
            q = mi @ Vector((w.x, w.y, z))
            up = tree.ray_cast(q, Vector((0, 0, 1)))  # the first face above: an underside = outside
            if up[0] is None or up[1].z >= 0:
                break
            h = tree.ray_cast(q, Vector((0, 0, -1)))
            if h[0] is None:
                break
            z = max(0.0, (mm @ h[0]).z - margin)
        if z < w.z - 1e-6:
            v.co = inv @ Vector((w.x, w.y, z))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def split_shell(shell, layout, coll):
    """The whole outline shell cut into the pieces' 24 x 28 px boxes like split_assembly, but left
    open at the cuts (no seam walls: the neighbour's shell carries on there)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(shell.data)
        bmesh.ops.transform(bm, matrix=shell.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in shell.data.materials:
            me.materials.append(m)
        me.shade_smooth()
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        o["tyrian_outline"] = True
        out[name] = o
    return out


def layout():
    data = common.load_sprite(ROOT, "newshe-123")
    return [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in data["assemblyLayout"] if e["model"] in PIECES]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    lay = layout()
    pieces = common.split_assembly(obj, lay, coll)
    for p in pieces.values():
        flat_seam_caps(p)
    # D90/D118: one outline shell from the whole, sealed model (before the cut), sunk under it
    # against the whole model, then cut along the pieces' boxes without caps. Shells made per piece
    # carried a wall at every seam; under the tallest lip (col 48, the 87/89 seam) it stood up out
    # of the groove in front of the lip and drew an ink stripe down the flank.
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    whole = shell_all_islands(sealed, coll, voxel=0.02, faces=14000, smooth=8, inside=0.006)
    sink_shell(whole, sealed)
    bpy.data.objects.remove(sealed, do_unlink=True)
    cut = split_shell(whole, lay, coll)
    bpy.data.objects.remove(whole, do_unlink=True)
    shells, total, exports = [], 0, {}
    for name, dx, dy in lay:
        p = pieces[name]
        sh = cut[name]
        sh.name = sh.data.name = f"{name}_outline"
        shells.append(sh)
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: {tris} tris")
        exports[name] = (p, sh)
    print("total tris", total)
    if "--pieces" in argv:  # piece-local glbs, for judging in the game's renderer (scratch only)
        pdir = Path(argv[argv.index("--pieces") + 1])
        for name, (p, sh) in exports.items():
            common.export_glb([p] if "--noshell" in argv else [p, sh], pdir / f"{name}.glb")
    for name, dx, dy in lay:
        common.export_sprite_model(ROOT, list(exports[name]), f"enemies/{name}",
                                   common.load_sprite(ROOT, name)["sprites"])
    for name, dx, dy in lay:
        for o in exports[name]:
            o.location = (dx / 12, -dy / 12, 0)
    bpy.context.view_layer.update()
    obj.hide_render = True
    obj.hide_set(True)
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + shells, out)
        print("exported", out)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        (rv / "stats.json").write_text(json.dumps({"tris": total, "pal": sorted({k[0] for k in MAT.slots})}))
        review(list(pieces.values()), shells, rv)


# --------------------------------------------------------------------------------------------------
# Review renders
# --------------------------------------------------------------------------------------------------

def review(pieces, shells, out):
    scene = bpy.context.scene

    def cam(location, look_at, ortho=None, fov=None, top=False):
        data = bpy.data.cameras.new("cam")
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.sensor_fit = "VERTICAL"
            data.angle_y = math.radians(fov)
        c = bpy.data.objects.new("cam", data)
        scene.collection.objects.link(c)
        c.location = location
        c.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
        return c

    def render(c, path, rx, ry):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(c, do_unlink=True)

    for s in shells:
        s.hide_render = True
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    k = 8
    render(cam((0, 0, 20), (0, 0, 0), ortho=W / 12, top=True), out / "top_flat.png", W * k, H * k)
    # the same top view with every material's grey = its palette index (sRGB byte), for measuring
    scene.display_settings.display_device = "sRGB"
    scene.render.dither_intensity = 0
    keep = {}
    for m in MAT.list:
        keep[m.name] = tuple(m.diffuse_color)
        v = int(m.name.split("_")[1]) / 255.0
        lin = v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        m.diffuse_color = (lin, lin, lin, 1)
    render(cam((0, 0, 20), (0, 0, 0), ortho=W / 12, top=True), out / "top_index.png", W * k, H * k)
    for m in MAT.list:
        m.diffuse_color = keep[m.name]
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sun_data = bpy.data.lights.new("game_sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, -8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    ink = bpy.data.materials.new("ink")
    ink.use_nodes = True
    bs = next(n for n in ink.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bs.inputs["Roughness"].default_value = 1.0
    ink.use_backface_culling = True
    for s in shells:
        h = s.copy()
        h.data = s.data.copy()
        h.data.materials.clear()
        h.data.materials.append(ink)
        scene.collection.objects.link(h)
        bm = bmesh.new()
        bm.from_mesh(h.data)
        bm.normal_update()
        for v in bm.verts:
            v.co += v.normal * 0.045
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(h.data)
        bm.free()
        h.hide_render = False
    render(cam((0, 0, 20), (0, 0, 0), ortho=W / 12, top=True), out / "top_game.png", W * 8, H * 8)
    zc = 0.6
    span = 9.0
    render(cam((30, 0, zc), (0, 0, zc), ortho=6.0), out / "side.png", 600, 300)
    render(cam((0, -30, zc), (0, 0, zc), ortho=span), out / "front.png", 800, 300)
    render(cam((0, 30, zc), (0, 0, zc), ortho=span), out / "rear.png", 800, 300)
    render(cam((-30, 0, zc), (0, 0, zc), ortho=6.0), out / "tailend.png", 600, 300)
    d = 18
    render(cam((d * 0.55, -d * 0.6, d * 0.5), (0, 0, 0.4), fov=33), out / "q1.png", 800, 600)
    render(cam((-d * 0.6, d * 0.5, d * 0.55), (0, 0, 0.4), fov=33), out / "q2.png", 800, 600)
    tilt = math.radians(32)
    render(cam((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0.5), fov=28), out / "game.png", 800, 600)
    render(cam((0, -d * 0.3, -d * 0.9), (0, 0, 0), fov=35), out / "under.png", 500, 400)


if __name__ == "__main__":
    main()
