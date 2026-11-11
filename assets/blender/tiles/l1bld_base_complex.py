r"""The ASTEROID? (map 1-3) base complex (shapesz.dat, 39 x 13 tiles), hard-surface (D65, D141), after
the blueprint: cross-sections first, then the parts.

Engineering read of the tile art (312 x 1092 px, 13 x 39 cells; the art wins on outline, feature
placement and colours):

  section through the rim, outside -> in (z in units, 1 unit = 12 px, z = 0 the HD ground):

      stones 0.36..0.47 (<= 0.374 on enemy cells)     kerb posts 0.366   plates 0.345   grating 0.314
        __    __    __                                     ||  ||  ||    ______  ______    _ _
   ____/  \__/  \__/  \_ bed top 0.14 (rubble, pal 2) _____||__||__||___|______||______|__| | |_ deck 0.30
  /  talus chamfer                                                                       (joints, pal 3)
 /_____________________________________________________________ slab bottom -0.04 (plain, closed)

- foundation bed: the painted footprint (pits, the yard, the fork's slots are holes) as one closed
  prism, its outer edge a talus chamfer, top in the rubble colour the rocks stand in;
- rim rocks: one chain of craggy, angular stones (8-11 px across) with small stones in its gaps,
  flat-shaded (an irregular 5-8 sided foot, a tilted shoulder ring, an off-centre peak), sunk into
  the dark bed, which shows in the crevices round each stone as the art's near-black gaps; crown
  facets pal 5 (the band's median with the bed's 0-2 left out), sides pal 4, a few facets pal 6-7
  (sheen); kept under the enemies on enemy cells;
- kerb: the art's dashed comb of light stubs inside the rocks, as separate closed posts every 4 px,
  deduplicated across all outlines (none closer than 3.6 px) and kept clear of the stones;
- paving: the art's basket weave (2 x 2 alternating units of three bricks per cell, WEAVE) as low
  chamfered bricks on a deck at the mortar colour, which shows in the 1 px seams;
- channels: a recessed grating: dark bars (pal 3) on a 4 px lattice over a brown fill (pal 164),
  the art's bright brown squares (pal 21) in alternate cells;
- the lights (338/339/347: domed dark-red lenses, faintly lit), the sensor pods (384), the round hatch (305-316), the two blasted
  hatches (318-329) and the turret block (298-309) as machined parts, each region in the art's
  own palette index (trimmed median of its pixels; table in blueprint.json "regions").

Only AO/roughness from the model's own bake (Building.bake_model, ground=0.0 occluder, D86); no
concept projection ("bake": "model" in textures/shapesz-l1bld-base-complex/maps.json). No D51 outline shell
(tile models draw no ink outline: structureInstances.ts, D8, D141). Exported through Building.export (the
tile contract: model l1bld-base-complex, layer 0, the pattern, default keepTiles / minRows).

    tools/build-models.sh -j 2 assets/blender/tiles/l1bld_base_complex.py
    blender --background --factory-startup --python assets/blender/tiles/l1bld_base_complex.py -- [--no-bake] [--preview dir]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402

TW, TH = lt.TILE_W, lt.TILE_H

# ---- heights (section above) ----
ENEMY_MAX, RIM_MAX = lb.ENEMY_MAX, lb.RIM_MAX
BOTTOM = -0.04
BED_TOP = 0.14  # low, so the boulders show a real dome above it (the deck's walls hide behind the kerb)
DECK_TOP = 0.300
PLATE_TOP = 0.345  # brick tops
MORTAR_TOP = 0.337  # the mortar bed plate under the bricks (relief 0.008, as the art's shallow seams)
CH_TOP = 0.314  # grating bars
CH_FILL = 0.303  # the brown fill under them
CH_SQ = 0.307  # the bright squares
CAV_FLOOR = 0.12  # the blasted hatches' cavity floor
KERB_TOP = 0.366
ROCK_BAND, KERB_W = 13, 4
KERB_STEP, KERB_IN = 4.0, 2.0  # post spacing along the edge, post centre in from it (px)
OPEN = [(120, 0, 192, 14), (300, 31 * 28, 312, 39 * 28)]  # platform runs on past the pattern: no rim

# ---- the art's palette index per region (trimmed medians, blueprint.json "regions") ----
PAL_BED, PAL_MORTAR, PAL_KERB, PAL_PAVE = 2, 3, 7, 6  # bricks: trimmed median of the weave's brick px 6, its seams 3
PAL_CHANNEL, PAL_RIB, PAL_GRATE, PAL_SQUARE = 164, 163, 3, 21
# the rim rocks: over the 12 px band with the bed / gap pixels (pal 0-2) left out the counts are 3:10481
# 4:8133 5:7007 6:5642 7:4674 8:3749, median 5 (the 3s are the darkest shading): bodies 5, the under-edge
# 4, a few stones' upper faces 6 / 7 (sheen)
PAL_ROCK, PAL_ROCK_DARK, PAL_ROCK_SHEEN, PAL_ROCK_HI = 5, 4, 6, 7
PAL_LENS, PAL_LENS_FAT, PAL_HOUSING, PAL_POD, PAL_EYE = 113, 114, 8, 8, 113  # lens medians: capsules 113, big lights 114
PAL_RH_DISC, PAL_RH_SPOKE, PAL_RH_CLAMP, PAL_FRAME = 1, 4, 163, 9
PAL_RH_SEAT = 3  # the round hatch is dark all through in the art (annulus medians 1 / 1 / 3 / 5 from the centre out)
PAL_LEAF, PAL_PIT, PAL_EMBER = 7, 1, 113
PAL_TURRET, PAL_SOCKET, PAL_VENT, PAL_TURRET_HI = 163, 1, 113, 165
PAL_TUR_BAR, PAL_TUR_FRAME = 161, 9  # the left bar near-black brown, striped pal 1; the socket's light grey frame

# ---- features (pattern px, from the tiles) ----
CAPS = [((194, 114, 211, 120), 'x'), ((194, 123, 211, 129), 'x'), ((194, 132, 211, 138), 'x'),
        ((98, 142, 115, 148), 'x'), ((98, 151, 115, 157), 'x'), ((98, 160, 115, 166), 'x'),
        ((145, 173, 150, 190), 'y'), ((153, 173, 158, 190), 'y'), ((161, 173, 166, 190), 'y')]
FAT = [(100, 564, 114, 583), (124, 564, 138, 583), (196, 564, 210, 583), (220, 564, 234, 583)]
PODS = [(155.5, 569.5), (179.5, 569.5)]
RHATCH = (165.5, 475.0, 20.0, 24.5)
HATCH = [(124, 840, 166, 890), (196, 840, 238, 890)]
TURRET = (246, 588, 288, 642)

# The paving's basket weave (every floor cell is the same tile; seams at x = 3, 7, 11, 15, 19, 23 and
# y = 13, 27 between the units): 2 x 2 units per cell, alternating, three bricks each (tile px, x0 y0 x1 y1)
WEAVE = ([(x, 0, x + 3, 13) for x in (0, 4, 8)] + [(12, y0, 23, y1) for y0, y1 in ((0, 4), (5, 9), (10, 13))]
         + [(0, y0, 11, y1) for y0, y1 in ((14, 18), (19, 23), (24, 27))] + [(x, 14, x + 3, 27) for x in (12, 16, 20)])

ARMS = {389: "ud", 379: "lr", 365: "dr", 367: "dl", 385: "ur", 387: "ul", 366: "lrd", 386: "lru", 376: "udlr",
        375: "udr", 377: "udl", 388: "u", 378: "d", 369: "l", 368: "r"}
STUB = {388: ("u", 17), 378: ("d", 6), 369: ("l", 14), 368: ("r", 6)}
CH_X, CH_Y, CH_HALF = 11.0, 13.5, 4.5


# ======================================================================= pixel-mask helpers (numpy)

def shift(m, dy, dx):
    o = np.zeros_like(m)
    h, w = m.shape
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    o[yd, xd] = m[ys, xs]
    return o


def disk_offsets(r):
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dy * dy + dx * dx <= (r + 0.3) ** 2]


def dil_disk(m, r):
    out = np.zeros_like(m)
    for dy, dx in disk_offsets(r):
        out |= shift(m, dy, dx)
    return out


def ero_disk(m, r):
    return ~dil_disk(~m, r)


def dil4(m, n=1):
    for _ in range(n):
        m = m | shift(m, 1, 0) | shift(m, -1, 0) | shift(m, 0, 1) | shift(m, 0, -1)
    return m


def gauss(img, sigma):
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(img, r, mode="constant")
    a = np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 1, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "valid"), 0, a)


def maxf(img, size):
    r = size // 2
    out = np.full_like(img, -np.inf)
    p = np.pad(img, r, mode="constant", constant_values=-np.inf)
    h, w = img.shape
    for dy in range(size):
        for dx in range(size):
            out = np.maximum(out, p[dy:dy + h, dx:dx + w])
    return out


def regions(mask, tol=0.8, min_px=8):
    """[(outer, [holes])] per 4-connected part: pixel-corner outlines, simplified (Douglas-Peucker)."""
    out = []
    lab, n = ls.label(mask)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) < min_px:
            continue
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        part = lab[y0:y1, x0:x1] == i
        pad = np.pad(part, 1)
        outer = [(x + x0 - 1, y + y0 - 1) for x, y in ls.simplify(ls.trace(pad), tol)]
        hl, hn = ls.label(~pad)
        holes = []
        for j in range(1, hn + 1):
            hm = hl == j
            if hm[0, :].any() or hm[-1, :].any() or hm[:, 0].any() or hm[:, -1].any() or hm.sum() < min_px:
                continue
            holes.append([(x + x0 - 1, y + y0 - 1) for x, y in ls.simplify(ls.trace(hm), tol)])
        out.append((outer, holes))
    return out


# ======================================================================= geometry (pattern px in, world out)

class Geo:
    """One bmesh for the whole model; every piece is oriented as built (outward normals)."""

    def __init__(self, s):
        self.s = s
        self.bm = bmesh.new()

    def v(self, x, y, z):
        return self.bm.verts.new((self.s.x(x), self.s.y(y), z))

    @staticmethod
    def clean(poly):
        out = []
        for p in poly:
            p = (float(p[0]), float(p[1]))
            if not out or math.dist(p, out[-1]) > 1e-4:
                out.append(p)
        while len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-4:
            out.pop()
        return out

    @staticmethod
    def outer(poly):  # world CCW == pattern-px area < 0 (y down)
        poly = Geo.clean(poly)
        return poly if ls.area(poly) < 0 else poly[::-1]

    @staticmethod
    def hole(poly):
        poly = Geo.clean(poly)
        return poly if ls.area(poly) > 0 else poly[::-1]

    def face(self, vs, mat, smooth=False):
        if len(set(vs)) < 3:
            return None
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f

    def walls(self, lo, hi, z0, z1, mat):
        a = [self.v(x, y, z0) for x, y in lo]
        b = [self.v(x, y, z1) for x, y in hi]
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            self.face((a[i], a[j], b[j], b[i]), mat)

    def cap(self, loops, z, mat, up=True):
        """A flat face over loops (first outer, then holes), all oriented (outer/hole)."""
        if len(loops) == 1:
            vs = [self.v(x, y, z) for x, y in loops[0]]
            self.face(vs if up else vs[::-1], mat)
            return
        edges = []
        for loop in loops:
            vs = [self.v(x, y, z) for x, y in loop]
            edges += [self.bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
        res = bmesh.ops.triangle_fill(self.bm, use_beauty=True, use_dissolve=False, edges=edges)
        for f in [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]:
            f.material_index = mat
            f.normal_update()
            if (f.normal.z > 0) != up:
                f.normal_flip()

    def prism(self, outer, holes, z0, z1, mat, chamfer=0.0, drop=0.0, bottom=True, side_mat=None, top_mat=None):
        side_mat = mat if side_mat is None else side_mat
        top_mat = mat if top_mat is None else top_mat
        o = self.outer(outer)
        if len(o) < 3:
            return
        hs = [h for h in (self.hole(h) for h in holes) if len(h) >= 3]
        if chamfer and drop:
            oi = [tuple(p) for p in ls.inset(o, chamfer)]
            if abs(ls.area(oi)) < 0.3 * abs(ls.area(o)) or (ls.area(oi) < 0) != (ls.area(o) < 0):
                chamfer = 0
        if chamfer and drop:
            his = [[tuple(p) for p in ls.inset(h, -chamfer)] for h in hs]
            self.walls(o, o, z0, z1 - drop, side_mat)
            self.walls(o, oi, z1 - drop, z1, mat)
            for h, h2 in zip(hs, his):
                self.walls(h, h, z0, z1 - drop, side_mat)
                self.walls(h, h2, z1 - drop, z1, mat)
            self.cap([oi] + his, z1, top_mat)
        else:
            self.walls(o, o, z0, z1, side_mat)
            for h in hs:
                self.walls(h, h, z0, z1, side_mat)
            self.cap([o] + hs, z1, top_mat)
        if bottom:
            self.cap([o] + hs, z0, side_mat, up=False)

    def frustum(self, poly, z0, z1, top_inset, mat, bottom=False):
        """A plate: walls sloping in `top_inset` px from z0 to z1 (a full-height chamfer)."""
        o = self.outer(poly)
        if len(o) < 3:
            return
        t = [tuple(p) for p in ls.inset(o, top_inset)]
        if abs(ls.area(t)) < 0.3 * abs(ls.area(o)):
            t = [tuple(p) for p in ls.inset(o, 0.3)]
        self.walls(o, t, z0, z1, mat)
        self.cap([t], z1, mat)
        if bottom:
            self.cap([o], z0, mat, up=False)

    def dome(self, cx, cy, rx, ry, z0, h, mat, n=12, rings=3):
        ringv = []
        for k in range(rings):
            t = k / rings * (math.pi / 2)
            ringv.append([self.v(cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a), z0 + h * math.sin(t))
                          for a in (2 * math.pi * i / n for i in range(n))])
        # px y down: angles increasing are clockwise in world; reverse to CCW
        ringv = [r[::-1] for r in ringv]
        top = self.v(cx, cy, z0 + h)
        for lo, hi in zip(ringv, ringv[1:]):
            for i in range(n):
                j = (i + 1) % n
                self.face((lo[i], lo[j], hi[j], hi[i]), mat, smooth=True)
        last = ringv[-1]
        for i in range(n):
            self.face((last[i], last[(i + 1) % n], top), mat, smooth=True)

    def cyl_y(self, cx, y0, y1, r, zc, mat, n=12, stripe=None, stripes=()):
        """A pipe along the screen's y (r in px); facets listed in `stripes` in `stripe` (lengthwise stripes)."""
        rz = r * lt.PX
        ring = lambda y: [self.v(cx + r * math.cos(2 * math.pi * i / n), y, zc + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]
        a, b = ring(y0), ring(y1)
        for i in range(n):
            j = (i + 1) % n
            self.face((a[i], b[i], b[j], a[j]), stripe if i in stripes and stripe is not None else mat, smooth=True)
        self.face(a, mat)
        self.face(b[::-1], mat)


def rbox(x0, y0, x1, y1, c=1.5, seg=2):
    c = max(0.0, min(c, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    if c <= 0:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pts = []
    for qx, qy, a0 in ((x1 - c, y0 + c, -90), (x1 - c, y1 - c, 0), (x0 + c, y1 - c, 90), (x0 + c, y0 + c, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((qx + c * math.cos(a), qy + c * math.sin(a)))
    return pts


def ell(cx, cy, rx, ry, n=24, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * i / n), cy + ry * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


# ======================================================================= build

def build(bake=True):
    s = lb.Building("base-complex")
    H, W = s.H, s.W
    grid, fp = s.grid, s.footprint
    red = s.masks()["red"]
    dep = lb.depth(fp)
    enemy = s.enemy_mask
    g = Geo(s)
    M = lambda i, **kw: s.m(i, **kw)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5

    def box(x0, y0, x1, y1):
        m = np.zeros((H, W), bool)
        m[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)] = True
        return m

    openm = np.zeros((H, W), bool)
    for b in OPEN:
        openm |= box(*b)

    feat = np.zeros((H, W), bool)
    for (x0, y0, x1, y1), _ in CAPS:
        feat |= box(x0 - 3, y0 - 3, x1 + 4, y1 + 4)
    for (x0, y0, x1, y1) in FAT:
        feat |= box(x0 - 3, y0 - 3, x1 + 4, y1 + 4)
    for (px, py) in PODS:
        feat |= box(px - 9, py - 10, px + 9, py + 10)
    cx, cy, rx, ry = RHATCH
    feat |= ((xx - cx) / (rx + 2.5)) ** 2 + ((yy - cy) / (ry + 2.5)) ** 2 <= 1
    for b in HATCH:
        feat |= box(b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)
    feat |= box(*TURRET)

    # materials (surface finish per part: satin metal, rough rubble and stone)
    m_bed = M(PAL_BED, roughness=0.95)
    m_mortar = M(PAL_MORTAR, roughness=0.9)
    m_mortar_plate = M(PAL_MORTAR, roughness=0.85, metallic=0.05)
    m_kerb = M(PAL_KERB, roughness=0.6, metallic=0.25, plain=True)  # plain: 1345 tiny posts would crowd the bake atlas
    m_pave = M(PAL_PAVE, roughness=0.7, metallic=0.1)
    m_chan = M(PAL_CHANNEL, roughness=0.55, metallic=0.35)
    m_rock = M(PAL_ROCK, roughness=0.9, plain=True)  # plain (unbaked) like the island rock: the bake's tiny islands on 1k stones bled glossy texels
    m_house = M(PAL_HOUSING, roughness=0.4, metallic=0.55)
    m_lens = M(PAL_LENS, roughness=0.22, metallic=0.1, emission_strength=0.45)  # a dark red glass that glows a little
    m_lens_fat = M(PAL_LENS_FAT, roughness=0.22, metallic=0.1, emission_strength=0.45)
    m_pod = M(PAL_POD, roughness=0.4, metallic=0.55)
    m_sock = M(PAL_SOCKET, roughness=0.8)
    m_eye = M(PAL_EYE, roughness=0.3, emission_strength=1.0)
    m_frame = M(PAL_FRAME, roughness=0.4, metallic=0.5)
    m_disc = M(PAL_RH_DISC, roughness=0.6, metallic=0.3)
    m_spoke = M(PAL_RH_SPOKE, roughness=0.45, metallic=0.5)
    m_clamp = M(PAL_RH_CLAMP, roughness=0.5, metallic=0.4)
    m_leaf = M(PAL_LEAF, roughness=0.5, metallic=0.45)
    m_pit = M(PAL_PIT, roughness=0.95)
    m_ember = M(PAL_EMBER, roughness=0.4, emission_strength=1.5)
    m_tur = M(PAL_TURRET, roughness=0.5, metallic=0.4)
    m_vent = M(PAL_VENT, roughness=0.4, emission_strength=1.8)

    # 1. Foundation bed: the painted footprint, holes cut; talus chamfer at the outer edge.
    # the blasted hatches' cavities go down through the bed and the deck (the frames line them)
    cav = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in HATCH:
        cav |= box(x0 + 3, y0 + 4.5, x1 - 3, y1 - 3)
    for outer, holes in regions(fp & ~cav, tol=1.9):
        g.prism(outer, holes, BOTTOM, BED_TOP, m_bed, chamfer=1.5, drop=0.10)

    # 2. Deck (the joint colour) inside the rock band.
    deck_mask = fp & (dep > ROCK_BAND - 1)
    deck_mask = dil_disk(ero_disk(deck_mask, 4), 4)
    deck_mask = ero_disk(dil_disk(deck_mask, 4), 4) & fp & ~cav
    deck_loops = regions(deck_mask, tol=1.6, min_px=30)
    for outer, holes in deck_loops:
        o = g.outer(outer)
        hs = [g.hole(h) for h in holes]
        g.walls(o, o, BED_TOP - 0.02, DECK_TOP, m_mortar)
        for h in hs:
            g.walls(h, h, BED_TOP - 0.02, DECK_TOP, m_mortar)
        g.cap([o] + hs, DECK_TOP, m_mortar)

    # Rim-rock layout (placed now, built in step 6, so the kerb can keep clear of the stones): as the
    #    art paints them, one chain of angular stones (about 9-10 px across) down the middle of the
    #    13 px band, small stones in the chain's gaps, each sized to leave a crevice of the dark bed
    #    (pal 2) round it, as the art's near-black gaps between its stones.
    bandm = fp & (dep <= ROCK_BAND) & ~dil4(openm, 4)
    rng = np.random.default_rng(13)
    taken = []  # (x, y, rad, kind)
    block = np.zeros((H, W), bool)
    cover = np.zeros((H, W), bool)

    def stamp(mask, x, y, r):
        ri = int(math.ceil(r))
        ya, yb, xa, xb = max(0, int(y) - ri), min(H, int(y) + ri + 1), max(0, int(x) - ri), min(W, int(x) + ri + 1)
        mask[ya:yb, xa:xb] |= (yy[ya:yb, xa:xb] - y) ** 2 + (xx[ya:yb, xa:xb] - x) ** 2 <= r * r

    # the chain: centres 5-7 px in, about 9-10 px apart
    ys, xs = np.nonzero(bandm & (dep >= 5) & (dep <= 7))
    for k in rng.permutation(len(ys)):
        if block[ys[k], xs[k]]:
            continue
        x, y = xs[k] + 0.5, ys[k] + 0.5
        taken.append([x, y, 0.0, 0])
        stamp(block, x, y, 9.0)
    ta = np.array([(t[0], t[1]) for t in taken])
    for t in taken:
        d = np.sort(np.hypot(ta[:, 0] - t[0], ta[:, 1] - t[1]))[1:3]
        t[2] = float(np.clip(0.45 * d.mean() * (0.92 + 0.16 * rng.random()), 3.8, 5.8))  # < half the spacing: a crevice between
        stamp(cover, t[0], t[1], t[2] * 1.05)
    # the small stones: wherever the band still shows bed 2-11 px in, clear of the chain
    block = dil_disk(cover, 1)
    ys, xs = np.nonzero(bandm & (dep >= 2) & (dep <= 11) & ~dil_disk(cover, 2))
    for k in rng.permutation(len(ys)):
        if block[ys[k], xs[k]]:
            continue
        x, y = xs[k] + 0.5, ys[k] + 0.5
        rad = 2.0 + 1.1 * rng.random()
        taken.append([x, y, rad, 1])
        stamp(block, x, y, rad + 2.4)
    print(f"rocks: {sum(1 for t in taken if t[3] == 0)} chain, {sum(1 for t in taken if t[3] == 1)} small")

    def inside(m, x, y):
        xi, yi = int(math.floor(x)), int(math.floor(y))
        return 0 <= xi < W and 0 <= yi < H and bool(m[yi, xi])

    # each stone's foot: an irregular 5-8 sided polygon (pattern px), every corner pulled in until it
    #    lies on the footprint and off the deck, so no stone reaches past the art's outline or into the
    #    kerb's row of posts
    feet = []
    for (x, y, rad, kind) in taken:
        big = kind == 0
        n = int(rng.integers(6, 9)) if big else int(rng.integers(5, 7))
        rot = rng.random() * math.tau
        angs = [rot + math.tau * (i + 0.55 * (rng.random() - 0.5)) / n for i in range(n)]
        fr = 0.82 + 0.36 * rng.random(n)  # uneven, not smoothed: angular corners
        ex, ey = 0.88 + 0.24 * rng.random(), 0.88 + 0.24 * rng.random()
        pts = []
        for a, f in zip(angs, fr):
            ca, sa = math.cos(a), math.sin(a)
            r = rad * f * (ex * abs(ca) + ey * abs(sa))
            while r > 0.35 * rad and (not inside(fp, x + r * ca, y + r * sa) or inside(deck_mask, x + r * ca, y + r * sa)):
                r *= 0.9
            pts.append((a, r))
        feet.append(pts)

    def in_poly(px_, py_, poly):
        c_ = False
        for i in range(len(poly)):
            (x1_, y1_), (x2_, y2_) = poly[i], poly[i - 1]
            if (y1_ > py_) != (y2_ > py_) and px_ < (x2_ - x1_) * (py_ - y1_) / (y2_ - y1_) + x1_:
                c_ = not c_
        return c_

    foot_polys = [[(t[0] + r * math.cos(a), t[1] + r * math.sin(a)) for a, r in pts] for t, pts in zip(taken, feet)]

    # 3. Kerb: the art's dashed comb of short light stubs along the paving's edge, as separate closed
    #    posts every KERB_STEP px round every deck outline (the dark mortar deck shows between them);
    #    none where the platform runs on past the pattern, nor at the hatch frames. Candidates from all
    #    outlines are deduplicated together (no two posts closer than KERB_MIN px, so none meet where
    #    outlines turn or touch), and a post a rim stone would reach is dropped.
    cav_near = dil4(cav, 3)
    no_post = dil4(openm, 3) | cav_near | feat
    nposts = 0
    KERB_MIN = 3.6  # > the post's diagonal (1.7 x 3.2 px): posts this far apart never overlap

    cands = []  # (cx, cy, tx, ty, nx, ny)
    for outer, holes in regions(deck_mask, tol=1.2, min_px=30):
        for loop in [outer] + holes:
            loop = Geo.clean(loop)
            n_ = len(loop)
            segs = [(loop[i], loop[(i + 1) % n_]) for i in range(n_)]
            per = sum(math.dist(p, q) for p, q in segs)
            if per < 3 * KERB_STEP:
                continue
            npost = max(1, int(round(per / KERB_STEP)))
            step = per / npost
            t_next, acc = step / 2, 0.0
            for p, q in segs:
                L = math.dist(p, q)
                if L < 1e-6:
                    continue
                tx, ty = (q[0] - p[0]) / L, (q[1] - p[1]) / L
                nx, ny = -ty, tx
                mx_, my_ = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                if not inside(deck_mask, mx_ + nx * 2.5, my_ + ny * 2.5):
                    nx, ny = -nx, -ny
                while t_next <= acc + L:
                    u = t_next - acc
                    t_next += step
                    ex_, ey_ = p[0] + tx * u, p[1] + ty * u
                    cx_, cy_ = ex_ + nx * KERB_IN, ey_ + ny * KERB_IN
                    if not inside(deck_mask, cx_, cy_) or not inside(deck_mask, ex_ + nx * 3.4, ey_ + ny * 3.4) or inside(no_post, cx_, cy_):
                        continue
                    cands.append((cx_, cy_, tx, ty, nx, ny))
                acc += L
    rock_xy = np.array([(t[0], t[1]) for t in taken]) if taken else np.zeros((0, 2))
    kept = []
    nrock_skip = 0
    for (cx_, cy_, tx, ty, nx, ny) in cands:
        if any(math.hypot(cx_ - kx, cy_ - ky) < KERB_MIN for kx, ky in kept):
            continue
        hw, hl = 0.85, 1.6  # 1.7 px along the edge, 3.2 px deep, as the art's stubs
        corners = [(cx_ + tx * a_ * hw + nx * b_ * hl, cy_ + ty * a_ * hw + ny * b_ * hl) for a_, b_ in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        near = np.nonzero(np.hypot(rock_xy[:, 0] - cx_, rock_xy[:, 1] - cy_) < 12)[0] if len(rock_xy) else []
        if any(in_poly(px_, py_, foot_polys[k]) for k in near for px_, py_ in corners + [(cx_, cy_)]):
            nrock_skip += 1
            continue  # a stone covers it
        kept.append((cx_, cy_))
        quad = Geo.outer(corners)
        # the post: a closed box (an open back showed its side walls as thin bright slivers from the
        #    rim side); tops staggered a hair so no two neighbours are coplanar
        ztop = KERB_TOP + 0.004 * ((len(kept) % 3) - 1)
        lo_ = [g.v(px_, py_, DECK_TOP - 0.005) for px_, py_ in quad]
        hi_ = [g.v(px_, py_, ztop) for px_, py_ in quad]
        g.face(hi_, m_kerb)
        for i in range(4):
            j = (i + 1) % 4
            g.face((lo_[i], lo_[j], hi_[j], hi_[i]), m_kerb)
        nposts += 1
    print(f"kerb: {len(cands)} candidates, {nposts} posts, {nrock_skip} under stones")

    # 4. Channels: the clean conduit strips from the channel tiles' arms.
    chan = np.zeros((H, W), bool)
    for r, row in enumerate(s.pattern):
        for c, t in enumerate(row):
            arms = ARMS.get(t)
            if not arms:
                continue
            x0, y0 = c * TW, r * TH
            ccx, ccy = x0 + CH_X, y0 + CH_Y
            st = STUB.get(t)
            for a in arms:
                if a == "u":
                    b = (ccx - CH_HALF, y0, ccx + CH_HALF, (y0 + st[1]) if st else ccy + CH_HALF)
                elif a == "d":
                    b = (ccx - CH_HALF, (y0 + st[1]) if st else ccy - CH_HALF, ccx + CH_HALF, y0 + TH)
                elif a == "l":
                    b = (x0, ccy - CH_HALF, (x0 + st[1]) if st else ccx + CH_HALF, ccy + CH_HALF)
                else:
                    b = ((x0 + st[1]) if st else ccx - CH_HALF, ccy - CH_HALF, x0 + TW, ccy + CH_HALF)
                chan[int(round(b[1])):int(round(b[3])), int(round(b[0])):int(round(b[2]))] = True
    chan &= fp
    # the conduit as a recessed grating per box (the arms meeting at a centre square, edge to edge, each
    #    clipped to the footprint's rows / columns): a brown fill (pal 164), dark bars (pal 3) on a 4 px
    #    lattice centred on the channel's axis (cross bars, and one bar down the middle), and the art's
    #    bright brown squares (pal 21) in alternate cells
    # plain (left out of the AO bake): its texel islands on these 1-2 px faces bled black / glossy
    m_grate = M(PAL_GRATE, roughness=0.8, metallic=0.15, plain=True)
    m_sq = M(PAL_SQUARE, roughness=0.8, metallic=0.1, plain=True)
    ngrate = 0

    def bar(x0_, y0_, x1_, y1_, z0_, z1_, mat):
        """A grating bar: its top and its two long sides (its ends butt into the trough's walls)."""
        if x1_ - x0_ < 0.2 or y1_ - y0_ < 0.2:
            return
        a_ = [g.v(x0_, y0_, z1_), g.v(x1_, y0_, z1_), g.v(x1_, y1_, z1_), g.v(x0_, y1_, z1_)]
        g.face(a_[::-1], mat)
        b_ = [g.v(x0_, y0_, z0_), g.v(x1_, y0_, z0_), g.v(x1_, y1_, z0_), g.v(x0_, y1_, z0_)]
        sides = ((0, 1), (2, 3)) if (x1_ - x0_) > (y1_ - y0_) else ((1, 2), (3, 0))
        for i, j in sides:
            g.face((b_[j], b_[i], a_[i], a_[j]), mat)

    def lattice(lo, hi, c):
        k0, k1 = math.ceil((lo - c - 0.5) / 4), math.floor((hi - c + 0.5) / 4)
        return [c + 4 * k for k in range(k0, k1 + 1) if lo - 0.5 <= c + 4 * k <= hi + 0.5]

    def grating(X0, Y0, X1, Y1, ax, ay, along):
        g.prism(rbox(X0, Y0, X1, Y1, 0), [], DECK_TOP - 0.01, CH_FILL, m_chan, bottom=False)
        xs_l = lattice(X0, X1, ax) if along in ("x", "xy") else [ax] if X0 <= ax <= X1 else []
        ys_l = lattice(Y0, Y1, ay) if along in ("y", "xy") else [ay] if Y0 <= ay <= Y1 else []
        for xb in xs_l:  # bars across x (constant x)
            bar(max(X0, xb - 0.5), Y0, min(X1, xb + 0.5), Y1, CH_FILL - 0.002, CH_TOP, m_grate)
        for yb in ys_l:
            bar(X0, max(Y0, yb - 0.5), X1, min(Y1, yb + 0.5), CH_FILL - 0.002, CH_TOP - 0.001, m_grate)
        # squares in the cells, checkerwise on the global lattice
        for cxq in [ax + 2 + 4 * k for k in range(-8, 8)]:
            for cyq in [ay + 2 + 4 * k for k in range(-8, 8)]:
                if not (X0 + 1.2 <= cxq <= X1 - 1.2 and Y0 + 1.2 <= cyq <= Y1 - 1.2):
                    continue
                kx, ky = round((cxq - ax - 2) / 4), round((cyq - ay - 2) / 4)
                if (kx + ky) % 2:
                    continue
                hx = 0.9
                g.face([g.v(cxq - hx, cyq + hx, CH_SQ), g.v(cxq + hx, cyq + hx, CH_SQ), g.v(cxq + hx, cyq - hx, CH_SQ), g.v(cxq - hx, cyq - hx, CH_SQ)], m_sq)

    for r, row in enumerate(s.pattern):
        for c, t in enumerate(row):
            arms = ARMS.get(t)
            if not arms:
                continue
            x0, y0 = c * TW, r * TH
            ccx, ccy = x0 + CH_X, y0 + CH_Y
            st = STUB.get(t)
            bx0, bx1, by0, by1 = ccx - CH_HALF, ccx + CH_HALF, ccy - CH_HALF, ccy + CH_HALF
            boxes = []
            if st:
                a = arms[0]
                boxes.append(({"u": (bx0, y0, bx1, y0 + st[1]), "d": (bx0, y0 + st[1], bx1, y0 + TH),
                               "l": (x0, by0, x0 + st[1], by1), "r": (x0 + st[1], by0, x0 + TW, by1)}[a], "y" if a in "ud" else "x"))
            else:
                boxes.append(((bx0, by0, bx1, by1), "xy"))
                for a in arms:
                    boxes.append(({"u": (bx0, y0, bx1, by0), "d": (bx0, by1, bx1, y0 + TH),
                                   "l": (x0, by0, bx0, by1), "r": (bx1, by0, x0 + TW, by1)}[a], "y" if a in "ud" else "x"))
            for (X0, Y0, X1, Y1), along in boxes:
                X0, Y0, X1, Y1 = round(X0), round(Y0), round(X1), round(Y1)
                m = fp[Y0:Y1, X0:X1]
                if X1 - X0 < 1 or Y1 - Y0 < 1 or not m.any():
                    continue
                ys_, xs_ = np.nonzero(m)
                X0, X1, Y0, Y1 = X0 + xs_.min(), X0 + xs_.max() + 1, Y0 + ys_.min(), Y0 + ys_.max() + 1
                grating(X0, Y0, X1, Y1, x0 + CH_X, y0 + CH_Y, along)
                ngrate += 1

    # 5. Paving: the art's basket weave as modelled bricks standing on the mortar deck (its 1 px seams
    #    are the gaps between them), each a brick face 0.008 proud of the mortar plate in the paving's index; bricks the kerb,
    #    a channel or a feature cuts are trimmed along their length, slivers dropped.
    zone = ero_disk(deck_mask, KERB_W) & ~chan & ~feat
    nplates = 0
    # the mortar plate: one chamfered slab per cell over the zone (its edges fall in the weave's seams)
    for r in range(H // TH):
        for c in range(W // TW):
            x0, y0 = c * TW, r * TH
            m = zone[y0:y0 + TH, x0:x0 + TW]
            if m.sum() < 6:
                continue
            if m.all():
                polys = [rbox(x0, y0, x0 + TW, y0 + TH, 0)]
            else:
                sub = np.zeros((H, W), bool)
                sub[y0:y0 + TH, x0:x0 + TW] = m
                polys = [o for o, _ in regions(sub, tol=1.0, min_px=6)]
            for poly in polys:
                g.frustum(poly, DECK_TOP - 0.002, MORTAR_TOP, 0.3, m_mortar_plate)
    for r in range(H // TH):
        for c in range(W // TW):
            x0, y0 = c * TW, r * TH
            if not zone[y0:y0 + TH, x0:x0 + TW].any():
                continue
            for bx0, by0, bx1, by1 in WEAVE:
                X0, Y0, X1, Y1 = x0 + bx0, y0 + by0, x0 + bx1, y0 + by1
                m = zone[Y0:Y1, X0:X1]
                horiz = (X1 - X0) > (Y1 - Y0)
                full = list(m.all(axis=0) if horiz else m.all(axis=1)) + [False]
                start = None
                for k, ok in enumerate(full):  # every run of the brick inside the zone, slivers dropped
                    if ok and start is None:
                        start = k
                    elif not ok and start is not None:
                        a_, b_ = start, k
                        start = None
                        if b_ - a_ < 2:
                            continue
                        e0 = 0.05 if a_ == 0 else 0.5  # a cut end keeps a joint off the channel or feature
                        e1 = 0.05 if b_ == len(full) - 1 else 0.5
                        rect = (X0 + a_ + e0, Y0 + 0.05, X0 + b_ - e1, Y1 - 0.05) if horiz else (X0 + 0.05, Y0 + a_ + e0, X1 - 0.05, Y0 + b_ - e1)
                        x_a, y_a, x_b, y_b = rect
                        g.face([g.v(x_a, y_b, PLATE_TOP), g.v(x_b, y_b, PLATE_TOP), g.v(x_b, y_a, PLATE_TOP), g.v(x_a, y_a, PLATE_TOP)], m_pave)
                        nplates += 1

    # Where the platform runs on past the pattern (OPEN), every edge is cut square at the pattern's
    #    border: no chamfer or frustum slope there to catch the light where the next piece joins.
    def snap_open():
        ux = s.x(1) - s.x(0)
        uy = s.y(1) - s.y(0)
        for v in g.bm.verts:
            px, py = (v.co.x - s.x(0)) / ux, (v.co.y - s.y(0)) / uy
            if 118 <= px <= 194 and py < 2.0:
                v.co.y = s.y(0)
            if px > W - 2.0 and OPEN[1][1] - 2 <= py <= H:
                v.co.x = s.x(W)

    snap_open()

    coll = common.reset_collection("shapesz-l1bld-base-complex")

    # 6. Rim rocks (the layout above): craggy, angular stones as the art's, never smooth domes. Each a
    #    flat-shaded faceted lump: an irregular 5-8 sided foot sunk just under the bed's top, a
    #    shoulder ring at uneven heights (the crown tilted), and an off-centre peak, so its top is 5-8
    #    flat facets that catch the light one by one; the dark bed (pal 2) shows in the crevices
    #    round it. Sides pal 4 (the art's dark under-edge; pal 3 on the darkest stones), crown facets
    #    pal 5 (the band's median), one or two facets pal 6 on most stones and pal 7 on a few (sheen).
    m_rock_dark = M(PAL_ROCK_DARK, roughness=0.92, plain=True)
    m_rock_sheen = M(PAL_ROCK_SHEEN, roughness=0.8, plain=True)
    m_rock_hi = M(PAL_ROCK_HI, roughness=0.75, plain=True)
    m_rock_deep = M(PAL_ROCK_DARK - 1, roughness=0.95, plain=True)  # the sides of the darkest stones
    for (x, y, rad, kind), pts in zip(taken, feet):
        big = kind == 0
        if big:
            top = 0.36 + 0.008 * rad + 0.07 * rng.random()
        else:
            top = 0.23 + 0.016 * rad + 0.035 * rng.random()  # small stones low and blunt, no spikes
        top = min(RIM_MAX, top)
        rr = int(math.ceil(1.25 * rad))
        if enemy[max(0, int(y) - rr):int(y) + rr + 1, max(0, int(x) - rr):int(x) + rr + 1].any():
            top = min(top, ENEMY_MAX - 0.006 - 0.02 * rng.random())
        n = len(pts)
        zs = BED_TOP - 0.03  # the foot, just under the bed's top
        hgt = top - zs
        ta_ = rng.random() * math.tau  # the crown's tilt: the shoulder rises on one side, falls on the other
        tilt = 0.18 + 0.14 * rng.random()
        shs = 0.72 + 0.12 * rng.random()  # the shoulder ring's scale: the crown fills most of the top view
        foot, shoulder = [], []
        for a, r in pts:
            ca, sa = math.cos(a), math.sin(a)
            foot.append(g.v(x + r * ca, y + r * sa, zs))
            zsh = zs + hgt * (0.58 + 0.16 * rng.random() + tilt * math.cos(a - ta_))  # a blunt crown
            g_ = shs * (0.85 + 0.3 * rng.random())
            shoulder.append(g.v(x + r * g_ * ca, y + r * g_ * sa, min(zsh, top - 0.02)))
        foot, shoulder = foot[::-1], shoulder[::-1]  # px y down: reverse to world CCW
        rs_min = min(r for _, r in pts) * shs * 0.85
        po = min(0.32 * rad * rng.random(), 0.45 * rs_min)  # the peak stays well inside the shoulder ring: no folded facets
        pa = ta_ + (rng.random() - 0.5) * 1.2  # the peak toward the high side
        apex = g.v(x + po * math.cos(pa), y + po * math.sin(pa), top)
        u = rng.random()  # crowns spread round the band's median 5, as the art's stones vary
        crown = m_rock_dark if u < 0.1 else m_rock
        side = m_rock_deep if crown == m_rock_dark else m_rock_dark
        k0 = int(rng.integers(n))  # sheen: one or two neighbouring crown facets lighter (pal 6, a few 7)
        lit = ({k0} if u > 0.3 else set()) | ({(k0 + 1) % n} if u > 0.6 else set())
        for i in range(n):
            j = (i + 1) % n
            g.face((foot[i], foot[j], shoulder[j]), side)
            g.face((foot[i], shoulder[j], shoulder[i]), side)
            mat = crown
            if i in lit:
                mat = m_rock_hi if (u > 0.85 and i == k0) else m_rock_sheen
            g.face((shoulder[i], shoulder[j], apex), mat)

    # 7. Red light capsules (338 x2, 339) and the big lights (347): a machined housing, a dark seat and
    #    a domed dark-red lens over a rounded rectangle (the art paints rounded capsules), faintly lit, under the enemies drawn over.
    m_dark = M(PAL_SOCKET, roughness=0.8)

    def pillow(poly, z0, h, mat, corner):
        """A domed lens over a rounded rectangle: rings stepping in and up (a quarter-ellipse profile), smooth."""
        o = g.outer(poly)
        prof = [(0.0, 0.0), (0.35, 0.45), (0.9, 0.78), (1.7, 0.95), (2.6, 1.0)]
        mn = min(max(p[0] for p in o) - min(p[0] for p in o), max(p[1] for p in o) - min(p[1] for p in o))
        k = min(1.0, (mn / 2 - 0.5) / 2.6, 0.9 * corner / 2.6)
        rings = [[g.v(x, y, z0 + h * t) for x, y in ([tuple(q) for q in ls.inset(o, d * k)] if d else o)] for d, t in prof]
        n = len(o)
        for lo, hi in zip(rings, rings[1:]):
            if len(hi) != n:
                break
            for i in range(n):
                j = (i + 1) % n
                g.face((lo[i], lo[j], hi[j], hi[i]), mat, smooth=True)
        g.face(rings[-1], mat, smooth=True)

    def lens_unit(x0, y0, x1, y1, fat):
        hx0, hy0, hx1, hy1 = x0 - 1.2, y0 - 1.2, x1 + 2.2, y1 + 2.2
        ztop = 0.350
        g.prism(rbox(hx0, hy0, hx1, hy1, 3.0 if fat else 2.0, 2), [], DECK_TOP - 0.005, ztop, m_house, chamfer=0.7, drop=0.012, bottom=False)
        w, h = x1 - x0 + 1, y1 - y0 + 1
        corner = 3.0 if fat else min(2.2, min(w, h) / 2 - 0.1)
        g.prism(rbox(x0 - 0.4, y0 - 0.4, x1 + 1.4, y1 + 1.4, corner + 0.4, 2), [], ztop - 0.02, ztop + 0.002, m_dark, bottom=False)
        pillow(rbox(x0, y0, x1 + 1, y1 + 1, corner, 2), ztop - 0.004, 0.030, m_lens_fat if fat else m_lens, corner)

    for (x0, y0, x1, y1), ax in CAPS:
        lens_unit(x0, y0, x1, y1, False)
    for (x0, y0, x1, y1) in FAT:
        lens_unit(x0, y0, x1, y1, True)
        cy_ = (y0 + y1 + 1) / 2
        for xs_ in (x0 - 1.0, x1 + 2.0):  # bolts on the housing's flanks
            g.prism(ell(xs_, cy_, 0.8, 0.8, 6), [], 0.345, 0.358, m_house, bottom=False)

    # 8. Sensor pods (384): a dark socket ring, a shell dome, the red eye slits as the art's.
    for (px, py) in PODS:
        g.prism(ell(px, py, 8.0, 9.0, 18), [], DECK_TOP - 0.005, 0.318, m_sock, chamfer=0.6, drop=0.006, bottom=False)
        g.dome(px - 0.5, py, 6.5, 7.5, 0.312, 0.058, m_pod, n=16, rings=4)
        g.prism(rbox(px - 2.5, py - 7, px + 2.5, py - 4.5, 0.5, 1), [], 0.345, 0.369, m_eye, bottom=False)
        g.prism(rbox(px - 5.5, py - 1, px - 3.5, py + 5, 0.5, 1), [], 0.345, 0.368, m_eye, bottom=False)

    # 9. Round hatch in the yard: seat ring, dark recessed disc, six spokes, hub, brown clamps.
    cx, cy, rx, ry = RHATCH
    g.prism(ell(cx, cy, rx + 1.5, ry + 1.5, 32), [ell(cx, cy, rx - 2.5, ry - 2.5, 32)], DECK_TOP - 0.01, 0.348, M(PAL_RH_SEAT, roughness=0.45, metallic=0.5),
            chamfer=0.7, drop=0.012, bottom=False)
    g.prism(ell(cx, cy, rx - 2.4, ry - 2.4, 32), [], DECK_TOP - 0.01, 0.322, m_disc, bottom=False)
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        p0, p1 = (cx + 5 * dx * rx / ry, cy + 5 * dy), (cx + (rx - 3.5) * dx, cy + (ry - 3.5) * dy)
        w = 1.1
        poly = [(p0[0] + nx * w, p0[1] + ny * w), (p1[0] + nx * w, p1[1] + ny * w), (p1[0] - nx * w, p1[1] - ny * w), (p0[0] - nx * w, p0[1] - ny * w)]
        g.prism(poly, [], 0.318, 0.338, m_spoke, chamfer=0.3, drop=0.006, bottom=False)
    g.prism(ell(cx, cy, 5.0, 5.5, 16), [], 0.318, 0.352, m_spoke, chamfer=0.8, drop=0.01, bottom=False)
    g.prism(ell(cx, cy, 2.2, 2.4, 10), [], 0.350, 0.360, m_disc, bottom=False)
    for sx in (-1, 1):
        x_ = cx + sx * (rx + 0.5)
        for y_ in ((cy - 6, cy - 0.4), (cy + 0.4, cy + 6)):  # split clamp blocks
            g.prism(rbox(x_ - 3, y_[0], x_ + 3, y_[1], 0.8, 1), [], DECK_TOP, 0.372, m_clamp, chamfer=0.6, drop=0.012, bottom=False)

    # 10. Blasted hatches: heavy frame, dark cavity, torn leaves bent down into it, embers.
    for (x0, y0, x1, y1) in HATCH:
        o = rbox(x0, y0, x1, y1, 1.5, 2)
        i_ = rbox(x0 + 3.5, y0 + 5, x1 - 3.5, y1 - 3.5, 1.0, 1)
        g.prism(o, [i_], CAV_FLOOR, 0.370, m_frame, chamfer=0.8, drop=0.012, bottom=False)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        g.prism(rbox(mx - 0.5, y0 + 0.6, mx + 0.5, y0 + 4.4, 0.2, 1), [], 0.362, 0.372, m_pit, bottom=False)  # top joint
        for bx_, by_ in ((x0 + 1.8, y0 + 2.5), (x1 - 1.8, y0 + 2.5), (x0 + 1.8, y1 - 1.8), (x1 - 1.8, y1 - 1.8)):
            g.prism(ell(bx_, by_, 0.7, 0.7, 6), [], 0.364, 0.378, m_frame, bottom=False)
        g.cap([g.outer(i_)], CAV_FLOOR + 0.002, m_pit)  # the cavity's floor
        # blasted leaves: each side's leaf is broken into three jagged wedge shards hinged under the
        # frame's lip, bent down into the cavity at different angles, tips torn at random lengths,
        # a few loose ones on the floor (pal 7); dark cracks between them
        ix0, iy0, ix1, iy1 = x0 + 3.5, y0 + 5, x1 - 3.5, y1 - 3.5
        sides = [((ix0 + 1, iy0 + 0.5), (ix1 - 1, iy0 + 0.5)), ((ix1 - 1, iy1 - 0.5), (ix0 + 1, iy1 - 0.5)),
                 ((ix0 + 0.5, iy1 - 1), (ix0 + 0.5, iy0 + 1)), ((ix1 - 0.5, iy0 + 1), (ix1 - 0.5, iy1 - 1))]

        def shard(P, Q, T, zh, zt, th=0.016):
            top = [g.v(P[0], P[1], zh), g.v(Q[0], Q[1], zh), g.v(T[0], T[1], zt)]
            bot = [g.v(P[0], P[1], zh - th), g.v(Q[0], Q[1], zh - th), g.v(T[0], T[1], zt - th)]
            for f in (top, bot[::-1], (top[0], bot[0], bot[1], top[1]), (top[1], bot[1], bot[2], top[2]), (top[2], bot[2], bot[0], top[0])):
                g.face(tuple(f), m_leaf)

        for si, (a, b) in enumerate(sides):
            ln = math.dist(a, b)
            ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
            inx, iny = mx - (a[0] + b[0]) / 2, my - (a[1] + b[1]) / 2
            il = math.hypot(inx, iny)
            inx, iny = inx / il, iny / il
            n3 = 3
            for k in range(n3):
                t0, t1 = k / n3 + 0.02, (k + 1) / n3 - 0.02
                P = (a[0] + ux * ln * t0, a[1] + uy * ln * t0)
                Q = (a[0] + ux * ln * t1, a[1] + uy * ln * t1)
                reach = 4.0 + 7.0 * rng.random()
                lat = (rng.random() - 0.5) * 0.5 * ln / n3
                mid = ((P[0] + Q[0]) / 2 + inx * reach + ux * lat, (P[1] + Q[1]) / 2 + iny * reach + uy * lat)
                zt = 0.31 - 0.08 * rng.random() - 0.04 * (k == 1)
                shard(P, Q, mid, 0.352, zt)
            # a lone small splinter on the floor
            fx, fy = mx + (rng.random() - 0.5) * 18, my + (rng.random() - 0.5) * 20
            ang = rng.random() * math.tau
            T3 = [(fx + r_ * math.cos(ang + k_), fy + r_ * math.sin(ang + k_)) for r_, k_ in ((3.2, 0), (2.4, 2.2), (1.8, 4.0))]
            top = [g.v(p[0], p[1], CAV_FLOOR + 0.03) for p in T3]
            bot = [g.v(p[0], p[1], CAV_FLOOR + 0.004) for p in T3]
            g.face(tuple(top), m_leaf)
            g.face(tuple(bot[::-1]), m_leaf)
            for i in range(3):
                j = (i + 1) % 3
                g.face((top[i], bot[i], bot[j], top[j]), m_leaf)
        # embers where the art paints the red in the hatch, glowing on the cavity floor
        hm = box(x0 + 4, y0 + 5, x1 - 4, y1 - 4) & red
        for outer, holes in regions(dil4(hm, 1), tol=0.7, min_px=4):
            g.prism(outer, [], CAV_FLOOR, CAV_FLOOR + 0.05, m_ember, bottom=False)

    # 11. Turret block (no enemy: stands taller): dark socket, cruciform pump housing, a pipe, vents.
    x0, y0, x1, y1 = TURRET
    # the socket: a light grey frame (pal 9, the art's) round a dark well
    m_tframe = M(PAL_TUR_FRAME, roughness=0.45, metallic=0.5)
    g.prism(rbox(x0 + 1, y0, x1 - 1, y1, 2.0, 2), [rbox(x0 + 3.5, y0 + 2.5, x1 - 3.5, y1 - 2.5, 1.0, 2)], DECK_TOP - 0.01, 0.332, m_tframe,
            chamfer=0.6, drop=0.01, bottom=False)
    g.prism(rbox(x0 + 3.4, y0 + 2.4, x1 - 3.4, y1 - 2.4, 1.0, 2), [], DECK_TOP - 0.01, 0.318, m_sock, bottom=False)
    g.prism(rbox(250, 606, 286, 626, 3.0, 2), [], 0.32, 0.50, m_tur, chamfer=1.2, drop=0.03, bottom=False)
    g.prism(rbox(260, 590, 280, 640, 3.0, 2), [], 0.32, 0.56, m_tur, chamfer=1.2, drop=0.03, bottom=False)
    m_tur_hi = M(PAL_TURRET_HI, roughness=0.45, metallic=0.4)
    g.prism(ell(270, 615, 8.5, 9.5, 20), [], 0.55, 0.61, m_tur_hi, chamfer=1.0, drop=0.02, bottom=False)
    g.prism(ell(270, 615, 5.5, 6.2, 16), [], 0.60, 0.65, m_tur, chamfer=0.8, drop=0.015, bottom=False)
    g.prism(ell(270, 615, 2.0, 2.2, 10), [], 0.64, 0.665, m_house, bottom=False)
    # the long left bar: near-black brown (pal 161) with dark lengthwise stripes (pal 1), as the art
    m_tbar = M(PAL_TUR_BAR, roughness=0.5, metallic=0.4)
    g.cyl_y(254.5, 588.5, 640.5, 3.6, 0.43, m_tbar, n=12, stripe=m_sock, stripes=(2, 4))
    for yb in (594, 634):
        g.prism(rbox(250, yb - 2, 259, yb + 2, 0.8, 1), [], 0.32, 0.43, m_tur, chamfer=0.5, drop=0.01, bottom=False)
    for yb in (606, 626):  # panel joints on the spine: a dark recessed strip
        g.prism(rbox(261, yb - 0.5, 279, yb + 0.5, 0.2, 1), [], 0.55, 0.562, m_sock, bottom=False)
    for vx0, vy0, vx1, vy1 in ((267, 598, 274, 604), (263, 628, 266, 633), (274, 628, 277, 633)):
        g.prism(rbox(vx0, vy0, vx1, vy1, 0.6, 1), [], 0.52, 0.565, m_vent, bottom=False)
    g.prism(rbox(252.0, 622, 257.0, 634, 0.6, 1), [], 0.40, 0.473, m_vent, bottom=False)

    # orient the shards (closed pieces): recalc only those faces' normals
    bm = g.bm
    leaf_faces = [f for f in bm.faces if f.material_index == m_leaf]
    bmesh.ops.recalc_face_normals(bm, faces=leaf_faces)
    bm.normal_update()

    # No needles: drop any degenerate face, and any upright face thinner than 0.2 px across that
    #    stands taller than it is wide (a sliver spike from a snapped edge or a tiny outline step).
    pxu = lt.PX
    drop_f = []
    for f in bm.faces:
        a = f.calc_area()
        L = max(e.calc_length() for e in f.edges)
        if L <= 1e-9 or a <= 1e-10:
            drop_f.append(f)
            continue
        if abs(f.normal.z) > 0.7:
            continue
        zs_ = [v.co.z for v in f.verts]
        xy = max(math.hypot(v.co.x - w.co.x, v.co.y - w.co.y) for v in f.verts for w in f.verts)
        if xy < 0.2 * pxu and (max(zs_) - min(zs_)) > xy:
            drop_f.append(f)
    bmesh.ops.delete(bm, geom=drop_f, context="FACES_ONLY")
    print(f"slivers removed: {len(drop_f)}")

    return s, g, coll, nposts, nplates, len(taken), fp, openm


def main(bake=True, preview=None):
    s, g, coll, nposts, nplates, nrocks, fp, openm = build()
    obj = lb.mesh_object("shapesz-l1bld-base-complex-parts", g.bm, s.pal.materials, coll)
    objects = [obj]
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"plates {nplates} kerb parts {nposts} rocks {nrocks} triangles {tris}")
    per = {}
    for p_ in obj.data.polygons:
        k_ = obj.data.materials[p_.material_index].name
        per[k_] = per.get(k_, 0) + len(p_.vertices) - 2
    print("triangles per material:", sorted(per.items(), key=lambda kv: -kv[1])[:14])
    s.check(objects)
    iou = s.top_iou(objects, fp, scale=1)
    if bake:
        objects = s.bake_model(objects, size=2048, ground=0.0)
    hard = objects[0]
    hard_tris = sum(len(p.vertices) - 2 for p in hard.data.polygons)
    print(f"base-complex: {hard_tris} triangles (hard), IoU {iou:.4f}")
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / "shapesz-l1bld-base-complex.png", view_px=480)
    s.export(objects, baked=bake)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
main(bake="--no-bake" not in argv, preview=lt.preview_arg())
