r"""ASTEROID?'s station kit (map 1-3's ground, shapesz.dat layer 0): the hard-surface parts every
platform of that level is built from, as the base complex (l1bld_base_complex.py, D141's hero) builds
them, so the smaller platforms (bunker, red bar, ring dome, light bridge) match it and the cross pad /
pipe junction round it. One `Kit(b)` per lib_l1bld.Building; every part goes into one bmesh
(`kit.g`), oriented as built; `kit.objects()` makes the mesh object for Building.finish().

    section through a platform's rim, outside -> in (z in units, 1 unit = 12 px, z = 0 the HD ground):

      stones 0.36..0.47 (<= 0.374 on enemy cells)     kerb posts 0.366   bricks 0.345   grating 0.314
        __    __    __                                     ||  ||  ||    ______  ______    _ _
   ____/  \__/  \__/  \_ bed top 0.14 (rubble, pal 2) _____||__||__||___|______||______|__| | |_ deck 0.30
  /  talus chamfer                                                                       (joints, pal 3)
 /_____________________________________________________________ slab bottom -0.04 (closed)

Order (as the base complex): masks -> bed() -> deck() -> rock_layout() -> kerb() -> channels() ->
paving() -> rocks() -> the building's own parts (lens(), pod(), round_hatch(), blasted_hatch(), or
the script's own with kit.g.prism / dome / cyl_y) -> objects(). Pixel coordinates are pattern px at
1x (top-left (0, 0), y down), as lib_l1bld. The art's palette indices for the shared parts are the
base complex's measured medians (PAL_* below); measure a building's own parts from its tiles
(b.grid, lb.Building.m(index)). Rocks, kerb posts and grating are plain (unbaked: their tiny faces
crowd and bleed in the AO atlas), everything else takes the model's own AO bake (bake_model).

The base complex keeps its own copy of the higher-level parts (inline in its build()); the pixel
helpers, Geo, rbox and ell are the same code.
"""

import math

import bmesh
import numpy as np

import lib_l1bld as lb
import lib_sockets as ls
import lib_tiles as lt

TW, TH = lt.TILE_W, lt.TILE_H

# ---- heights (the section above; lib_l1bld.ENEMY_MAX 0.38 caps anything in an enemy's cell) ----
ENEMY_MAX, RIM_MAX = lb.ENEMY_MAX, lb.RIM_MAX
BOTTOM = -0.04
BED_TOP = 0.14
DECK_TOP = 0.300
PLATE_TOP = 0.345  # brick tops
MORTAR_TOP = 0.337  # the mortar plate under the bricks
CH_TOP = 0.314  # grating bars
CH_FILL = 0.303  # the brown fill under them
CH_SQ = 0.307  # the bright squares
CAV_FLOOR = 0.12  # a blasted hatch's cavity floor
KERB_TOP = 0.366
LENS_TOP = 0.350  # a light's housing top (its lens domes 0.026 above)
ROCK_BAND, KERB_W = 13, 4  # px: the rim band (stones) from the outline; the kerb strip inside it
KERB_STEP, KERB_IN, KERB_MIN = 4.0, 2.0, 3.6  # post spacing, post centre in from the deck edge, min gap

# ---- the art's palette indices (the base complex's trimmed medians) ----
PAL_BED, PAL_MORTAR, PAL_KERB, PAL_PAVE = 2, 3, 7, 6
PAL_CHANNEL, PAL_GRATE, PAL_SQUARE = 164, 3, 21
PAL_ROCK, PAL_ROCK_DARK, PAL_ROCK_SHEEN, PAL_ROCK_HI = 5, 4, 6, 7
PAL_LENS, PAL_LENS_FAT, PAL_HOUSING, PAL_POD, PAL_EYE = 113, 114, 8, 8, 113
PAL_RH_DISC, PAL_RH_SPOKE, PAL_RH_CLAMP, PAL_RH_SEAT, PAL_FRAME = 1, 4, 163, 3, 9
PAL_LEAF, PAL_PIT, PAL_EMBER, PAL_SOCKET = 7, 1, 113, 1

# ---- channels (the art's 389 / 379 strips; the base complex and the pipe junction use the same) ----
CH_X, CH_Y = 11.0, 13.5
CH_HX, CH_HY = 7.5, 9.0
ARMS = {389: "ud", 379: "lr", 365: "dr", 367: "dl", 385: "ur", 387: "ul", 366: "lrd", 386: "lru", 376: "udlr",
        375: "udr", 377: "udl", 388: "u", 378: "d", 369: "l", 368: "r"}
STUB = {388: ("u", 17), 378: ("d", 6), 369: ("l", 14), 368: ("r", 6)}

# The paving's basket weave (the floor tile 371 and the rest of the paved cells): 2 x 2 units per
# cell, alternating, three bricks each (tile px x0 y0 x1 y1).
WEAVE = ([(x, 0, x + 3, 13) for x in (0, 4, 8)] + [(12, y0, 23, y1) for y0, y1 in ((0, 4), (5, 9), (10, 13))]
         + [(0, y0, 11, y1) for y0, y1 in ((14, 18), (19, 23), (24, 27))] + [(x, 14, x + 3, 27) for x in (12, 16, 20)])


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


def box_mask(shape, x0, y0, x1, y1):
    m = np.zeros(shape, bool)
    m[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)] = True
    return m


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
        """A prism over `outer` (pattern px) with `holes`, z0..z1, its top edge chamfered `chamfer`
        px in and `drop` down; `bottom=False` leaves the underside open (a part standing on a deck)."""
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


def in_poly(px_, py_, poly):
    c_ = False
    for i in range(len(poly)):
        (x1_, y1_), (x2_, y2_) = poly[i], poly[i - 1]
        if (y1_ > py_) != (y2_ > py_) and px_ < (x2_ - x1_) * (py_ - y1_) / (y2_ - y1_) + x1_:
            c_ = not c_
    return c_


# ======================================================================= the kit

class Kit:
    """The base complex's parts for one building `b` (lib_l1bld.Building). `b.footprint` is the
    painted platform; `b.enemy_mask` the cells ground enemies stand on (tops there <= ENEMY_MAX)."""

    def __init__(self, b, seed=13):
        self.b = b
        self.g = Geo(b)
        self.H, self.W = b.H, b.W
        self.rng = np.random.default_rng(seed)
        M = b.m
        self.mat = dict(
            bed=M(PAL_BED, roughness=0.95),
            mortar=M(PAL_MORTAR, roughness=0.9),
            mortar_plate=M(PAL_MORTAR, roughness=0.85, metallic=0.05),
            kerb=M(PAL_KERB, roughness=0.6, metallic=0.25, plain=True),
            pave=M(PAL_PAVE, roughness=0.7, metallic=0.1),
            chan=M(PAL_CHANNEL, roughness=0.55, metallic=0.35),
            grate=M(PAL_GRATE, roughness=0.8, metallic=0.15, plain=True),
            square=M(PAL_SQUARE, roughness=0.8, metallic=0.1, plain=True),
            rock=M(PAL_ROCK, roughness=0.9, plain=True),
            rock_dark=M(PAL_ROCK_DARK, roughness=0.92, plain=True),
            rock_sheen=M(PAL_ROCK_SHEEN, roughness=0.8, plain=True),
            rock_hi=M(PAL_ROCK_HI, roughness=0.75, plain=True),
            rock_deep=M(PAL_ROCK_DARK - 1, roughness=0.95, plain=True),
            house=M(PAL_HOUSING, roughness=0.4, metallic=0.55),
            lens=M(PAL_LENS, roughness=0.22, metallic=0.1, emission_strength=0.45),
            lens_fat=M(PAL_LENS_FAT, roughness=0.22, metallic=0.1, emission_strength=0.45),
            pod=M(PAL_POD, roughness=0.4, metallic=0.55),
            sock=M(PAL_SOCKET, roughness=0.8),
            eye=M(PAL_EYE, roughness=0.3, emission_strength=1.0),
            frame=M(PAL_FRAME, roughness=0.4, metallic=0.5),
            disc=M(PAL_RH_DISC, roughness=0.6, metallic=0.3),
            spoke=M(PAL_RH_SPOKE, roughness=0.45, metallic=0.5),
            clamp=M(PAL_RH_CLAMP, roughness=0.5, metallic=0.4),
            seat=M(PAL_RH_SEAT, roughness=0.45, metallic=0.5),
            leaf=M(PAL_LEAF, roughness=0.5, metallic=0.45),
            pit=M(PAL_PIT, roughness=0.95),
            ember=M(PAL_EMBER, roughness=0.4, emission_strength=1.5),
        )
        self.stones = []  # rock_layout(): [x, y, rad, kind, foot polygon (pattern px)]

    def box(self, x0, y0, x1, y1):
        return box_mask((self.H, self.W), x0, y0, x1, y1)

    # ---- the platform ---------------------------------------------------------------------------

    def bed(self, mask, chamfer=1.5, drop=0.10):
        """The foundation bed: `mask` (the footprint, holes cut: pits, cavities) as closed prisms
        from BOTTOM to BED_TOP in the rubble colour, a talus chamfer round the outside."""
        for outer, holes in regions(mask, tol=1.9):
            self.g.prism(outer, holes, BOTTOM, BED_TOP, self.mat["bed"], chamfer=chamfer, drop=drop)

    def deck_mask(self, fp, cut=None):
        """The deck inside the rock band: footprint px deeper than ROCK_BAND - 1, opened / closed by
        4 px (smooth outline), minus `cut`."""
        dep = lb.depth(fp)
        d = fp & (dep > ROCK_BAND - 1)
        d = dil_disk(ero_disk(d, 4), 4)
        d = ero_disk(dil_disk(d, 4), 4) & fp
        return d & ~cut if cut is not None else d

    def deck(self, deck_mask):
        """The mortar deck (the joint colour) at DECK_TOP over `deck_mask`, walls down into the bed."""
        g = self.g
        for outer, holes in regions(deck_mask, tol=1.6, min_px=30):
            o = g.outer(outer)
            hs = [g.hole(h) for h in holes]
            g.walls(o, o, BED_TOP - 0.02, DECK_TOP, self.mat["mortar"])
            for h in hs:
                g.walls(h, h, BED_TOP - 0.02, DECK_TOP, self.mat["mortar"])
            g.cap([o] + hs, DECK_TOP, self.mat["mortar"])

    # ---- the rim rocks and the kerb -------------------------------------------------------------

    def rock_layout(self, fp, deck_mask, exclude=None):
        """Where the rim stones go (built later by rocks(), so the kerb keeps clear of them): one
        chain of angular stones (about 9-10 px across) down the middle of the ROCK_BAND, small stones
        in its gaps, each leaving a crevice of the dark bed round it, as the art's near-black gaps.
        `exclude` (bool px) keeps stones away (an open edge, a part of the building's own)."""
        H, W, rng = self.H, self.W, self.rng
        yy, xx = np.mgrid[0:H, 0:W] + 0.5
        dep = lb.depth(fp)
        bandm = fp & (dep <= ROCK_BAND)
        if exclude is not None:
            bandm &= ~exclude
        taken = []
        block = np.zeros((H, W), bool)
        cover = np.zeros((H, W), bool)

        def stamp(mask, x, y, r):
            ri = int(math.ceil(r))
            ya, yb, xa, xb = max(0, int(y) - ri), min(H, int(y) + ri + 1), max(0, int(x) - ri), min(W, int(x) + ri + 1)
            mask[ya:yb, xa:xb] |= (yy[ya:yb, xa:xb] - y) ** 2 + (xx[ya:yb, xa:xb] - x) ** 2 <= r * r

        ys, xs = np.nonzero(bandm & (dep >= 5) & (dep <= 7))
        for k in rng.permutation(len(ys)):
            if block[ys[k], xs[k]]:
                continue
            x, y = xs[k] + 0.5, ys[k] + 0.5
            taken.append([x, y, 0.0, 0])
            stamp(block, x, y, 9.0)
        if taken:
            ta = np.array([(t[0], t[1]) for t in taken])
            for t in taken:
                d = np.sort(np.hypot(ta[:, 0] - t[0], ta[:, 1] - t[1]))[1:3]
                d = d if len(d) else np.array([10.0])
                t[2] = float(np.clip(0.45 * d.mean() * (0.92 + 0.16 * rng.random()), 3.8, 5.8))
                stamp(cover, t[0], t[1], t[2] * 1.05)
        block = dil_disk(cover, 1)
        ys, xs = np.nonzero(bandm & (dep >= 2) & (dep <= 11) & ~dil_disk(cover, 2))
        for k in rng.permutation(len(ys)):
            if block[ys[k], xs[k]]:
                continue
            x, y = xs[k] + 0.5, ys[k] + 0.5
            rad = 2.0 + 1.1 * rng.random()
            taken.append([x, y, rad, 1])
            stamp(block, x, y, rad + 2.4)

        def inside(m, x, y):
            xi, yi = int(math.floor(x)), int(math.floor(y))
            return 0 <= xi < W and 0 <= yi < H and bool(m[yi, xi])

        # each foot: an irregular 5-8 sided polygon, corners pulled in onto the footprint, off the deck
        stones = []
        for (x, y, rad, kind) in taken:
            n = int(rng.integers(6, 9)) if kind == 0 else int(rng.integers(5, 7))
            rot = rng.random() * math.tau
            angs = [rot + math.tau * (i + 0.55 * (rng.random() - 0.5)) / n for i in range(n)]
            fr = 0.82 + 0.36 * rng.random(n)
            ex, ey = 0.88 + 0.24 * rng.random(), 0.88 + 0.24 * rng.random()
            pts = []
            for a, f in zip(angs, fr):
                ca, sa = math.cos(a), math.sin(a)
                r = rad * f * (ex * abs(ca) + ey * abs(sa))
                while r > 0.35 * rad and (not inside(fp, x + r * ca, y + r * sa) or inside(deck_mask, x + r * ca, y + r * sa)):
                    r *= 0.9
                pts.append((a, r))
            stones.append([x, y, rad, kind, pts])
        self.stones = stones
        print(f"kit rocks: {sum(1 for t in stones if t[3] == 0)} chain, {sum(1 for t in stones if t[3] == 1)} small")
        return stones

    def kerb(self, deck_mask, no_post=None):
        """The art's dashed comb of short light stubs along the deck's edge: closed posts every
        KERB_STEP px round every deck outline (the dark mortar shows between them), none in `no_post`
        (open edges, hatch frames, parts), none a rim stone (rock_layout) covers. Returns the count."""
        g, H, W = self.g, self.H, self.W

        def inside(m, x, y):
            xi, yi = int(math.floor(x)), int(math.floor(y))
            return 0 <= xi < W and 0 <= yi < H and bool(m[yi, xi])

        no_post = np.zeros((H, W), bool) if no_post is None else no_post
        cands = []
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
        feet = [[(t[0] + r * math.cos(a), t[1] + r * math.sin(a)) for a, r in t[4]] for t in self.stones]
        rock_xy = np.array([(t[0], t[1]) for t in self.stones]) if self.stones else np.zeros((0, 2))
        kept = []
        for (cx_, cy_, tx, ty, nx, ny) in cands:
            if any(math.hypot(cx_ - kx, cy_ - ky) < KERB_MIN for kx, ky in kept):
                continue
            hw, hl = 0.85, 1.6
            corners = [(cx_ + tx * a_ * hw + nx * b_ * hl, cy_ + ty * a_ * hw + ny * b_ * hl) for a_, b_ in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            near = np.nonzero(np.hypot(rock_xy[:, 0] - cx_, rock_xy[:, 1] - cy_) < 12)[0] if len(rock_xy) else []
            if any(in_poly(px_, py_, feet[k]) for k in near for px_, py_ in corners + [(cx_, cy_)]):
                continue
            kept.append((cx_, cy_))
            quad = Geo.outer(corners)
            ztop = KERB_TOP + 0.004 * ((len(kept) % 3) - 1)
            lo_ = [g.v(px_, py_, DECK_TOP - 0.005) for px_, py_ in quad]
            hi_ = [g.v(px_, py_, ztop) for px_, py_ in quad]
            g.face(hi_, self.mat["kerb"])
            for i in range(4):
                j = (i + 1) % 4
                g.face((lo_[i], lo_[j], hi_[j], hi_[i]), self.mat["kerb"])
        print(f"kit kerb: {len(cands)} candidates, {len(kept)} posts")
        return len(kept)

    def rocks(self):
        """The rim stones of rock_layout(): craggy, flat-shaded faceted lumps (an irregular foot sunk
        just under the bed's top, a tilted shoulder ring, an off-centre peak), crowns pal 5, sides 4,
        a facet or two pal 6/7 (sheen); under ENEMY_MAX on an enemy's cell, under RIM_MAX elsewhere."""
        g, rng, m = self.g, self.rng, self.mat
        enemy = self.b.enemy_mask
        for (x, y, rad, kind, pts) in self.stones:
            if kind == 0:
                top = 0.36 + 0.008 * rad + 0.07 * rng.random()
            else:
                top = 0.23 + 0.016 * rad + 0.035 * rng.random()
            top = min(RIM_MAX, top)
            rr = int(math.ceil(1.25 * rad))
            if enemy[max(0, int(y) - rr):int(y) + rr + 1, max(0, int(x) - rr):int(x) + rr + 1].any():
                top = min(top, ENEMY_MAX - 0.006 - 0.02 * rng.random())
            n = len(pts)
            zs = BED_TOP - 0.03
            hgt = top - zs
            ta_ = rng.random() * math.tau
            tilt = 0.18 + 0.14 * rng.random()
            shs = 0.72 + 0.12 * rng.random()
            foot, shoulder = [], []
            for a, r in pts:
                ca, sa = math.cos(a), math.sin(a)
                foot.append(g.v(x + r * ca, y + r * sa, zs))
                zsh = zs + hgt * (0.58 + 0.16 * rng.random() + tilt * math.cos(a - ta_))
                g_ = shs * (0.85 + 0.3 * rng.random())
                shoulder.append(g.v(x + r * g_ * ca, y + r * g_ * sa, min(zsh, top - 0.02)))
            foot, shoulder = foot[::-1], shoulder[::-1]
            rs_min = min(r for _, r in pts) * shs * 0.85
            po = min(0.32 * rad * rng.random(), 0.45 * rs_min)
            pa = ta_ + (rng.random() - 0.5) * 1.2
            apex = g.v(x + po * math.cos(pa), y + po * math.sin(pa), top)
            u = rng.random()
            crown = m["rock_dark"] if u < 0.1 else m["rock"]
            side = m["rock_deep"] if crown == m["rock_dark"] else m["rock_dark"]
            k0 = int(rng.integers(n))
            lit = ({k0} if u > 0.3 else set()) | ({(k0 + 1) % n} if u > 0.6 else set())
            for i in range(n):
                j = (i + 1) % n
                g.face((foot[i], foot[j], shoulder[j]), side)
                g.face((foot[i], shoulder[j], shoulder[i]), side)
                mat = crown
                if i in lit:
                    mat = m["rock_hi"] if (u > 0.85 and i == k0) else m["rock_sheen"]
                g.face((shoulder[i], shoulder[j], apex), mat)

    # ---- channels and paving --------------------------------------------------------------------

    def channels(self, fp):
        """The channel tiles' (ARMS) conduits as recessed gratings: a brown fill, dark bars on a 4 px
        lattice centred on the channel's axis, bright squares in alternate cells. Returns the
        channel mask (keep the paving off it)."""
        b, g, H, W = self.b, self.g, self.H, self.W
        chan = np.zeros((H, W), bool)
        boxes = []
        for r, row in enumerate(b.pattern):
            for c, t in enumerate(row):
                arms = ARMS.get(t)
                if not arms:
                    continue
                x0, y0 = c * TW, r * TH
                ccx, ccy = x0 + CH_X, y0 + CH_Y
                st = STUB.get(t)
                bx0, bx1, by0, by1 = ccx - CH_HX, ccx + CH_HX, ccy - CH_HY, ccy + CH_HY
                cell = []
                if st:
                    a = arms[0]
                    cell.append(({"u": (bx0, y0, bx1, y0 + st[1]), "d": (bx0, y0 + st[1], bx1, y0 + TH),
                                  "l": (x0, by0, x0 + st[1], by1), "r": (x0 + st[1], by0, x0 + TW, by1)}[a], "y" if a in "ud" else "x"))
                else:
                    cell.append(((bx0, by0, bx1, by1), "xy"))
                    for a in arms:
                        cell.append(({"u": (bx0, y0, bx1, by0), "d": (bx0, by1, bx1, y0 + TH),
                                      "l": (x0, by0, bx0, by1), "r": (bx1, by0, x0 + TW, by1)}[a], "y" if a in "ud" else "x"))
                for bb, along in cell:
                    boxes.append((bb, along, ccx, ccy))
                    chan[int(round(bb[1])):int(round(bb[3])), int(round(bb[0])):int(round(bb[2]))] = True
        chan &= fp

        def bar(x0_, y0_, x1_, y1_, z0_, z1_, mat):
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

        for (X0, Y0, X1, Y1), along, ax, ay in boxes:
            X0, Y0, X1, Y1 = round(X0), round(Y0), round(X1), round(Y1)
            m = fp[Y0:Y1, X0:X1]
            if X1 - X0 < 1 or Y1 - Y0 < 1 or not m.any():
                continue
            ys_, xs_ = np.nonzero(m)
            X0, X1, Y0, Y1 = X0 + xs_.min(), X0 + xs_.max() + 1, Y0 + ys_.min(), Y0 + ys_.max() + 1
            g.prism(rbox(X0, Y0, X1, Y1, 0), [], DECK_TOP - 0.01, CH_FILL, self.mat["chan"], bottom=False)
            xs_l = lattice(X0, X1, ax) if along in ("x", "xy") else [ax] if X0 <= ax <= X1 else []
            ys_l = lattice(Y0, Y1, ay) if along in ("y", "xy") else [ay] if Y0 <= ay <= Y1 else []
            for xb in xs_l:
                bar(max(X0, xb - 0.5), Y0, min(X1, xb + 0.5), Y1, CH_FILL - 0.002, CH_TOP, self.mat["grate"])
            for yb in ys_l:
                bar(X0, max(Y0, yb - 0.5), X1, min(Y1, yb + 0.5), CH_FILL - 0.002, CH_TOP - 0.001, self.mat["grate"])
            for cxq in [ax + 2 + 4 * k for k in range(-8, 8)]:
                for cyq in [ay + 2 + 4 * k for k in range(-8, 8)]:
                    if not (X0 + 1.2 <= cxq <= X1 - 1.2 and Y0 + 1.2 <= cyq <= Y1 - 1.2):
                        continue
                    kx, ky = round((cxq - ax - 2) / 4), round((cyq - ay - 2) / 4)
                    if (kx + ky) % 2:
                        continue
                    hx = 0.9
                    g.face([g.v(cxq - hx, cyq + hx, CH_SQ), g.v(cxq + hx, cyq + hx, CH_SQ), g.v(cxq + hx, cyq - hx, CH_SQ),
                            g.v(cxq - hx, cyq - hx, CH_SQ)], self.mat["square"])
        return chan

    def paving(self, zone):
        """The art's basket weave over `zone` (bool px; e.g. ero_disk(deck_mask, KERB_W) & ~chan &
        ~parts): a chamfered mortar plate per cell, low bricks (WEAVE) on it, trimmed where the zone
        ends, slivers dropped. Returns the brick count."""
        g, H, W = self.g, self.H, self.W
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
                    g.frustum(poly, DECK_TOP - 0.002, MORTAR_TOP, 0.3, self.mat["mortar_plate"])
        n = 0
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
                    for k, ok in enumerate(full):
                        if ok and start is None:
                            start = k
                        elif not ok and start is not None:
                            a_, b_ = start, k
                            start = None
                            if b_ - a_ < 2:
                                continue
                            e0 = 0.05 if a_ == 0 else 0.5
                            e1 = 0.05 if b_ == len(full) - 1 else 0.5
                            rect = (X0 + a_ + e0, Y0 + 0.05, X0 + b_ - e1, Y1 - 0.05) if horiz else (X0 + 0.05, Y0 + a_ + e0, X1 - 0.05, Y0 + b_ - e1)
                            x_a, y_a, x_b, y_b = rect
                            g.face([g.v(x_a, y_b, PLATE_TOP), g.v(x_b, y_b, PLATE_TOP), g.v(x_b, y_a, PLATE_TOP), g.v(x_a, y_a, PLATE_TOP)], self.mat["pave"])
                            n += 1
        return n

    # ---- machined parts -------------------------------------------------------------------------

    def pillow(self, poly, z0, h, mat, corner):
        """A domed lens over a rounded rectangle: rings stepping in and up, smooth."""
        g = self.g
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

    def lens(self, x0, y0, x1, y1, fat=False, ztop=LENS_TOP, mat=None):
        """A red light (the 338/339 capsules: fat=False; the 347 big lights: fat=True) over the
        art's lens box (x0, y0)-(x1, y1) (inclusive px): a machined housing, a dark seat, a domed
        dark-red lens, faintly lit. Top ztop + 0.026 (0.376 by default: under ENEMY_MAX)."""
        g, m = self.g, self.mat
        hx0, hy0, hx1, hy1 = x0 - 1.2, y0 - 1.2, x1 + 2.2, y1 + 2.2
        g.prism(rbox(hx0, hy0, hx1, hy1, 3.0 if fat else 2.0, 2), [], DECK_TOP - 0.005, ztop, m["house"], chamfer=0.7, drop=0.012, bottom=False)
        w, h = x1 - x0 + 1, y1 - y0 + 1
        corner = 3.0 if fat else min(2.2, min(w, h) / 2 - 0.1)
        g.prism(rbox(x0 - 0.4, y0 - 0.4, x1 + 1.4, y1 + 1.4, corner + 0.4, 2), [], ztop - 0.02, ztop + 0.002, m["sock"], bottom=False)
        self.pillow(rbox(x0, y0, x1 + 1, y1 + 1, corner, 2), ztop - 0.004, 0.030,
                    mat if mat is not None else (m["lens_fat"] if fat else m["lens"]), corner)
        if fat:
            cy_ = (y0 + y1 + 1) / 2
            for xs_ in (x0 - 1.0, x1 + 2.0):
                g.prism(ell(xs_, cy_, 0.8, 0.8, 6), [], ztop - 0.005, ztop + 0.008, m["house"], bottom=False)

    def pod(self, px, py):
        """A sensor pod (384): a dark socket ring, a shell dome, red eye slits."""
        g, m = self.g, self.mat
        g.prism(ell(px, py, 8.0, 9.0, 18), [], DECK_TOP - 0.005, 0.318, m["sock"], chamfer=0.6, drop=0.006, bottom=False)
        g.dome(px - 0.5, py, 6.5, 7.5, 0.312, 0.058, m["pod"], n=16, rings=4)
        g.prism(rbox(px - 2.5, py - 7, px + 2.5, py - 4.5, 0.5, 1), [], 0.345, 0.369, m["eye"], bottom=False)
        g.prism(rbox(px - 5.5, py - 1, px - 3.5, py + 5, 0.5, 1), [], 0.345, 0.368, m["eye"], bottom=False)

    def round_hatch(self, cx, cy, rx, ry):
        """The round hatch (305/306/315/316): seat ring, dark recessed disc, six spokes, hub, brown
        split clamps either side (top 0.372)."""
        g, m = self.g, self.mat
        g.prism(ell(cx, cy, rx + 1.5, ry + 1.5, 32), [ell(cx, cy, rx - 2.5, ry - 2.5, 32)], DECK_TOP - 0.01, 0.348, m["seat"],
                chamfer=0.7, drop=0.012, bottom=False)
        g.prism(ell(cx, cy, rx - 2.4, ry - 2.4, 32), [], DECK_TOP - 0.01, 0.322, m["disc"], bottom=False)
        for k in range(6):
            a = math.pi / 6 + k * math.pi / 3
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            p0, p1 = (cx + 5 * dx * rx / ry, cy + 5 * dy), (cx + (rx - 3.5) * dx, cy + (ry - 3.5) * dy)
            w = 1.1
            poly = [(p0[0] + nx * w, p0[1] + ny * w), (p1[0] + nx * w, p1[1] + ny * w), (p1[0] - nx * w, p1[1] - ny * w), (p0[0] - nx * w, p0[1] - ny * w)]
            g.prism(poly, [], 0.318, 0.338, m["spoke"], chamfer=0.3, drop=0.006, bottom=False)
        g.prism(ell(cx, cy, 5.0, 5.5, 16), [], 0.318, 0.352, m["spoke"], chamfer=0.8, drop=0.01, bottom=False)
        g.prism(ell(cx, cy, 2.2, 2.4, 10), [], 0.350, 0.360, m["disc"], bottom=False)
        for sx in (-1, 1):
            x_ = cx + sx * (rx + 0.5)
            for y_ in ((cy - 6, cy - 0.4), (cy + 0.4, cy + 6)):
                g.prism(rbox(x_ - 3, y_[0], x_ + 3, y_[1], 0.8, 1), [], DECK_TOP, 0.372, m["clamp"], chamfer=0.6, drop=0.012, bottom=False)

    def cavity(self, x0, y0, x1, y1):
        """The px a blasted hatch (x0, y0, x1, y1) cuts through the bed and the deck: cut it from
        both (bed(mask & ~cavity), deck_mask(..., cut=cavity))."""
        return self.box(x0 + 3, y0 + 4.5, x1 - 3, y1 - 3)

    def blasted_hatch(self, x0, y0, x1, y1, red=None):
        """A blasted hatch (318/319/328/329): heavy frame round a dark cavity down to CAV_FLOOR,
        torn leaves bent down into it, a splinter on the floor, embers where `red` (bool px, the
        art's red) is inside. Top 0.378: under ENEMY_MAX (an enemy stands on it)."""
        g, m, rng = self.g, self.mat, self.rng
        o = rbox(x0, y0, x1, y1, 1.5, 2)
        i_ = rbox(x0 + 3.5, y0 + 5, x1 - 3.5, y1 - 3.5, 1.0, 1)
        g.prism(o, [i_], CAV_FLOOR, 0.370, m["frame"], chamfer=0.8, drop=0.012, bottom=False)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        g.prism(rbox(mx - 0.5, y0 + 0.6, mx + 0.5, y0 + 4.4, 0.2, 1), [], 0.362, 0.372, m["pit"], bottom=False)
        for bx_, by_ in ((x0 + 1.8, y0 + 2.5), (x1 - 1.8, y0 + 2.5), (x0 + 1.8, y1 - 1.8), (x1 - 1.8, y1 - 1.8)):
            g.prism(ell(bx_, by_, 0.7, 0.7, 6), [], 0.364, 0.378, m["frame"], bottom=False)
        g.cap([g.outer(i_)], CAV_FLOOR + 0.002, m["pit"])
        ix0, iy0, ix1, iy1 = x0 + 3.5, y0 + 5, x1 - 3.5, y1 - 3.5
        sides = [((ix0 + 1, iy0 + 0.5), (ix1 - 1, iy0 + 0.5)), ((ix1 - 1, iy1 - 0.5), (ix0 + 1, iy1 - 0.5)),
                 ((ix0 + 0.5, iy1 - 1), (ix0 + 0.5, iy0 + 1)), ((ix1 - 0.5, iy0 + 1), (ix1 - 0.5, iy1 - 1))]
        leaf = m["leaf"]

        def shard(P, Q, T, zh, zt, th=0.016):
            top = [g.v(P[0], P[1], zh), g.v(Q[0], Q[1], zh), g.v(T[0], T[1], zt)]
            bot = [g.v(P[0], P[1], zh - th), g.v(Q[0], Q[1], zh - th), g.v(T[0], T[1], zt - th)]
            for f in (top, bot[::-1], (top[0], bot[0], bot[1], top[1]), (top[1], bot[1], bot[2], top[2]), (top[2], bot[2], bot[0], top[0])):
                g.face(tuple(f), leaf)

        for si, (a, b_) in enumerate(sides):
            ln = math.dist(a, b_)
            ux, uy = (b_[0] - a[0]) / ln, (b_[1] - a[1]) / ln
            inx, iny = mx - (a[0] + b_[0]) / 2, my - (a[1] + b_[1]) / 2
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
            fx, fy = mx + (rng.random() - 0.5) * 18, my + (rng.random() - 0.5) * 20
            ang = rng.random() * math.tau
            T3 = [(fx + r_ * math.cos(ang + k_), fy + r_ * math.sin(ang + k_)) for r_, k_ in ((3.2, 0), (2.4, 2.2), (1.8, 4.0))]
            top = [g.v(p[0], p[1], CAV_FLOOR + 0.03) for p in T3]
            bot = [g.v(p[0], p[1], CAV_FLOOR + 0.004) for p in T3]
            g.face(tuple(top), leaf)
            g.face(tuple(bot[::-1]), leaf)
            for i in range(3):
                j = (i + 1) % 3
                g.face((top[i], bot[i], bot[j], top[j]), leaf)
        if red is not None:
            hm = self.box(x0 + 4, y0 + 5, x1 - 4, y1 - 4) & red
            for outer, holes in regions(dil4(hm, 1), tol=0.7, min_px=4):
                g.prism(outer, [], CAV_FLOOR, CAV_FLOOR + 0.05, m["ember"], bottom=False)

    # ---- finish ---------------------------------------------------------------------------------

    def no_needles(self):
        """Orient the closed shards (blasted leaves), then drop degenerate faces and upright faces
        thinner than 0.2 px that stand taller than they are wide (spikes from tiny outline steps)."""
        bm = self.g.bm
        leaf_faces = [f for f in bm.faces if f.material_index == self.mat["leaf"]]
        if leaf_faces:
            bmesh.ops.recalc_face_normals(bm, faces=leaf_faces)
        bm.normal_update()
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
        return len(drop_f)

    def objects(self, coll=None):
        """The kit's bmesh as the building's mesh object (after no_needles()); returns [obj]. Add
        cover-part objects (D139, tagged tyrian_cell / tyrian_when) to the list yourself."""
        import common
        b = self.b
        coll = coll or common.reset_collection(f"{lb.SHAPES}-{b.prefix}-{b.name}")
        obj = lb.mesh_object(f"{lb.SHAPES}-{b.prefix}-{b.name}-parts", self.g.bm, b.pal.materials, coll)
        self.g.bm = bmesh.new()
        return [obj]
