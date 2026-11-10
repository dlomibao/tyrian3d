"""newshd-169: a wooden turret silo with an iris hatch (newshd.shp frames 169, 193-207; 24 x 28 px
full tile with its cobbled slab).

What it is (scout): a FIXED GROUND TURRET-SILO. Type 273 is spawned by ground-layer events with no
motion, so it rides the terrain; turret 144 fires from its pit while a 20-step animation opens and
shuts the iris. Levels (inventory): 1.1, 1.2, 2.4, 3.2. So: a tall stave-built oval vat standing on
a cobbled stone pad, an iris of four steel leaves over a gun pit at its north end, a glowing emitter
in the pit, and a sloped front (south) end with a slot hatch flush in its boards.

Reading of the sprite (tools/calibration/rubric.md "Reading a sprite"), sprite px, (col, row):
- Cobbles fill the whole tile: a stone pad, greys 3-10.
- The object (wood, indices 16 and up) spans rows 1-23: 12/15/17 px wide on rows 1-3, 19 px (cols
  2-20) on rows 4-19, tapering 17/15/13/11 on rows 20-23; ink round it. So its footprint is an
  upright oval / stadium, 19 px wide, rows 1-24 (edges), centred on col edge 11.5 (OUTLINE below).
- North part: a light wood rim ring (21-25) round the pit (pit cols 4-18, rows 2-14, centre
  (11.5, 8.5) in pixel edges).
- Rows 15-23 are the art's oblique view of the tall front wall. Built as a sloped south end (rows
  16-24, staves running down it) so the top-down camera sees it; the pale lintel board (26/23 at
  rows 16-17, cols 9-15), and below it a slot hatch (rows 20-23, cols 8-13, in a dark frame with
  the dark seam at col 14) set flush in those boards. A wooden shutter slides up under the lintel
  panel: its lower edge by frame: 193/195/197 shut, 199 row 23, 201 row 22, 203 row 21, 169/205/207
  fully up. Slot red-lit on 169/207 (115-118), dim on 205 (113-114), a dim 112 on 203, dark otherwise.
- Iris: four grey quarter-dome leaves (3-11, median 7; the 9-11 upper-left pixels are sheen),
  meeting in a 1 px cross seam (193). 195: 3 px gap; 197: only their outer corners left; 199 on:
  gone into four steel pockets on the rim's inner edge at the diagonals (10/11 blocks).
- Pit: dark (1-4), lit inner wall on the left (4). Emitter in its middle: glows on 169 (big, 112 ring
  to 127 centre), 207 (smaller), 205 (smallest, dim); dark on 199-203.
- Two dark-brown pins on the rim (165 at col 14 row 2, 163 at col 8 row 14): iron bolt heads.

Stages (six models, the same split as the game's current newshd-169 script):
  newshd-169     169, 205, 207  open, shutter up, emitter and slot lit (per-frame glow parts)
  newshd-169-f2  193            iris shut, shutter down
  newshd-169-f3  195            iris a little open
  newshd-169-f4  197            iris mostly open
  newshd-169-f5  199            open, dark, shutter one row up
  newshd-169-f6  201, 203       open, dark, shutter two / three rows up (per-frame shutter parts)

Run: blender -b --factory-startup -P newshd-169.py   (writes public/models/enemies/newshd-169{,-f2..-f6}.glb and the spriteModels JSON)
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT

NAME = "newshd-169"
P = 1 / 12  # one sprite pixel


def XE(c):
    """Sprite pixel edge (column) to Blender X."""
    return (c - 12) / 12


def YE(r):
    """Sprite pixel edge (row) to Blender Y (sprite up is +Y)."""
    return (14 - r) / 12


def RW(y):
    """Blender Y back to a sprite row edge."""
    return 14 - y * 12


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys) (copied from usp_talon.pchip)."""
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
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


# --- Layout (pixel edges) ----------------------------------------------------------------------
CX, CY = XE(11.5), YE(8.5)         # pit axis
R_PIT = 6.5 * P                    # pit mouth (coping inner edge), rows 2-15
R_COP = 7.4 * P                    # coping ring outer edge (stays inside row 1)
SX = 7.5 / 6.5                     # the pit is an oval: cols 4-19 (15 px) by rows 2-15 (13 px)
Z_BASE = 0.05                      # top of the stone pad
Z_TOP = 0.95                       # deck
Z_CHIME = Z_TOP + 0.03             # stave ends, proud of the deck
Z_RIM = Z_TOP + 0.06               # top of the coping ring round the pit
Z_PIT = Z_TOP - 0.45               # pit floor
Z_FRONT = 0.36                     # foot of the sloped south end
WALL = 0.9 * P                     # stave thickness
SIDES = 40

# Footprint: half width (px) about col edge 11.5 per row edge (from the sprite's wood spans).
_HW = pchip([1.0, 1.5, 2.5, 3.5, 4.5, 5.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.5, 24.0],
            [4.4, 6.0, 7.5, 8.55, 9.3, 9.5, 9.5, 9.35, 8.5, 7.5, 6.5, 5.5, 4.9])
R_TOP, R_BOT = 1.05, 24.0          # its north and south edges

# Sloped south end: from the crest at row 16 to the foot at row 24.
R_HI, R_LO = 16.0, R_BOT
Z_HI, Z_LO = Z_TOP, Z_FRONT


def ztop(y):
    """Deck height at Blender y: flat north of the crest, sloping down to the front."""
    r = RW(y)
    if r <= R_HI:
        return Z_TOP
    return Z_HI + (min(r, R_LO) - R_HI) / (R_LO - R_HI) * (Z_LO - Z_HI)


def slope_point(x, r, h):
    """A point on the sloped face at sprite row edge r, h out along the face normal."""
    y = YE(r)
    t = (r - R_HI) / (R_LO - R_HI)
    z = Z_HI + t * (Z_LO - Z_HI)
    dy, dz = YE(R_LO) - YE(R_HI), Z_LO - Z_HI  # down-slope direction (in y, z)
    ln = math.hypot(dy, dz)
    ny, nz = dz / ln, -dy / ln   # outward normal: (0, ny, nz) points south and up
    if nz < 0:
        ny, nz = -ny, -nz
    return (x, y + h * ny, z + h * nz)


# --- 2D polygon helpers -------------------------------------------------------------------------

def area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def outline(step=0.25):
    """The footprint (CCW seen from above), resampled evenly by arc length later."""
    rows = [R_TOP + k * step for k in range(int((R_BOT - R_TOP) / step) + 1)]
    if rows[-1] < R_BOT:
        rows.append(R_BOT)
    right = [(XE(11.5) + _HW(r) * P, YE(r)) for r in rows]
    left = [(XE(11.5) - _HW(r) * P, YE(r)) for r in reversed(rows)]
    poly = right + left
    if area(poly) < 0:
        poly.reverse()
    return poly


def resample(poly, n):
    seg = [math.dist(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    total = sum(seg)
    out, acc, i = [], 0.0, 0
    for k in range(n):
        s = total * k / n
        while acc + seg[i] < s:
            acc += seg[i]
            i += 1
        t = (s - acc) / seg[i]
        a, b = poly[i], poly[(i + 1) % len(poly)]
        out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def normals(poly):
    """Outward unit vertex normals of a CCW polygon."""
    n = len(poly)
    out = []
    for i in range(n):
        a, b = poly[i - 1], poly[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty)
        out.append((ty / ln, -tx / ln))
    return out


def offset(poly, d):
    return [(x + nx * d, y + ny * d) for (x, y), (nx, ny) in zip(poly, normals(poly))]


def clip(poly, keep):
    """Sutherland-Hodgman against one half plane: keep(p) -> signed value, kept where >= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        fa, fb = keep(a), keep(b)
        if fa >= 0:
            out.append(a)
        if (fa >= 0) != (fb >= 0):
            t = fa / (fa - fb)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def ray_hit(poly, c, d):
    """Distance from c along unit d to the polygon's boundary (c inside)."""
    best = 1e9
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        wx, wy = a[0] - c[0], a[1] - c[1]
        t = (wx * ey - wy * ex) / den
        u = (wx * d[1] - wy * d[0]) / den
        if t > 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            best = min(best, t)
    return best


def inside(poly, p):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


OUTER = resample(outline(), 120)
INNER = offset(OUTER, -WALL)
# --- bmesh helpers ------------------------------------------------------------------------------

def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def hexa(bm, pts, mat, smooth=False):
    """A closed six-faced solid from 8 points: bottom quad 0-3, top quad 4-7 (same winding)."""
    before = set(bm.faces)
    v = [bm.verts.new(p) for p in pts]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in q])
    _tag(bm, before, mat, smooth)


def revolve(bm, profile, mat, sides=SIDES, a0=0.0, a1=2 * math.pi, cx=CX, cy=CY, smooth=True, closed_profile=True):
    """Revolve a closed (r, z) profile round the tub axis. Full turn: a closed torus-like solid;
    partial turn: capped ends. Profile points with r == 0 collapse onto the axis."""
    before = set(bm.faces)
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    n = sides if full else sides + 1
    rings = []
    for i in range(n):
        a = a0 + (a1 - a0) * i / sides
        ring = [bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)) for r, z in profile]
        rings.append(ring)
    m = len(profile)
    pairs = range(n) if full else range(n - 1)
    for i in pairs:
        j = (i + 1) % n
        for k in range(m if closed_profile else m - 1):
            l = (k + 1) % m
            quad = [rings[i][k], rings[j][k], rings[j][l], rings[i][l]]
            uniq = []
            for vv in quad:
                if vv not in uniq:
                    uniq.append(vv)
            if len(uniq) >= 3:
                try:
                    bm.faces.new(uniq)
                except ValueError:
                    pass
    if not full and closed_profile:
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
    _tag(bm, before, mat, smooth)
    bmesh.ops.remove_doubles(bm, verts=[v for r in rings for v in r], dist=1e-6)


def disc_profile(r, z0, z1, ch=0.0):
    """Profile of a solid disc (axis to r) with a chamfered top edge."""
    return [(0.0, z0), (r, z0), (r, z1 - ch), (r - ch, z1), (0.0, z1)]


def ring_profile(r0, r1, z0, z1, ch=0.0, ch_in=None):
    ci = ch if ch_in is None else ch_in
    return [(r0, z0), (r1, z0), (r1, z1 - ch), (r1 - ch, z1), (r0 + ci, z1), (r0, z1 - ci)]


def to_object(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def bevel_block(bm, x0, y0, x1, y1, z0, z1, ch, mat, smooth=False):
    """A box with chamfered top edges (cobbles, pockets, bolts)."""
    pts_lo = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pts_hi = [(x0 + ch, y0 + ch), (x1 - ch, y0 + ch), (x1 - ch, y1 - ch), (x0 + ch, y1 - ch)]
    before = set(bm.faces)
    vb = [bm.verts.new((x, y, z0)) for x, y in pts_lo]
    vm = [bm.verts.new((x, y, z1 - ch)) for x, y in pts_lo]
    vt = [bm.verts.new((x, y, z1)) for x, y in pts_hi]
    bm.faces.new(list(reversed(vb)))
    bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vb[i], vb[j], vm[j], vm[i]))
        bm.faces.new((vm[i], vm[j], vt[j], vt[i]))
    _tag(bm, before, mat, smooth)


def slope_box(bm, x0, x1, r0, r1, h0, h1, mat, ch=0.0):
    """A board lying on the hatch's sloped face: columns x0..x1 (Blender x), rows r0..r1 (edges),
    from h0 to h1 out along the face normal. ch chamfers its outer face's edges."""
    if ch <= 0:
        hexa(bm, [slope_point(x0, r1, h0), slope_point(x1, r1, h0), slope_point(x1, r0, h0), slope_point(x0, r0, h0),
                  slope_point(x0, r1, h1), slope_point(x1, r1, h1), slope_point(x1, r0, h1), slope_point(x0, r0, h1)], mat)
        return
    dr = ch / P  # chamfer in rows
    before = set(bm.faces)
    lo = [slope_point(x0, r1, h0), slope_point(x1, r1, h0), slope_point(x1, r0, h0), slope_point(x0, r0, h0)]
    mid = [slope_point(x0, r1, h1 - ch), slope_point(x1, r1, h1 - ch), slope_point(x1, r0, h1 - ch), slope_point(x0, r0, h1 - ch)]
    hi = [slope_point(x0 + ch, r1 - dr, h1), slope_point(x1 - ch, r1 - dr, h1), slope_point(x1 - ch, r0 + dr, h1),
          slope_point(x0 + ch, r0 + dr, h1)]
    vb = [bm.verts.new(p) for p in lo]
    vm = [bm.verts.new(p) for p in mid]
    vt = [bm.verts.new(p) for p in hi]
    bm.faces.new(list(reversed(vb)))
    bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vb[i], vb[j], vm[j], vm[i]))
        bm.faces.new((vm[i], vm[j], vt[j], vt[i]))
    _tag(bm, before, mat, False)


def x_prism(bm, x0, x1, yz, mat, smooth=False):
    """Extrude a closed (y, z) polygon along X from x0 to x1."""
    before = set(bm.faces)
    a = [bm.verts.new((x0, y, z)) for y, z in yz]
    b = [bm.verts.new((x1, y, z)) for y, z in yz]
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    n = len(yz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    _tag(bm, before, mat, smooth)

def squash(bm, before):
    """Stretch the geometry added since `before` across X about the pit axis: the round pit parts
    become the sprite's oval pit."""
    for v in set(bm.verts) - before:
        v.co.x = CX + (v.co.x - CX) * SX


def prism_var(bm, poly, z0, zfn, mat, smooth=False):
    """Extrude a CCW polygon from z0 up to a top that follows zfn(x, y) (the sloped deck)."""
    before = set(bm.faces)
    b = [bm.verts.new((x, y, z0)) for x, y in poly]
    t = [bm.verts.new((x, y, zfn(x, y))) for x, y in poly]
    bm.faces.new(list(reversed(b)))
    bm.faces.new(t)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((b[i], b[j], t[j], t[i]))
    _tag(bm, before, mat, smooth)


# --- Parts --------------------------------------------------------------------------------------

def stone_pad(bm, M):
    """The cobbled pad filling the tile: a mortar bed and rounded setts in staggered courses."""
    bevel_block(bm, XE(0), YE(28), XE(24), YE(0), 0.0, Z_BASE - 0.015, 0.01, M["MORTAR"])
    hidden = offset(OUTER, -1.6 * P)
    course_h = 3.5  # px per course
    rows = int(28 / course_h)
    shade = [M["SETT_A"], M["SETT_B"], M["SETT_C"]]
    k = 0
    for i in range(rows):
        r0 = i * course_h
        r1 = r0 + course_h
        off = 0.0 if i % 2 == 0 else 1.75
        c = -off
        while c < 24:
            w = (3.9, 2.8, 3.4, 4.2, 3.0)[(k * 3 + i) % 5]
            c0, c1 = max(c, 0.0), min(c + w, 24.0)
            c += w
            k += 1
            if c1 - c0 < 0.9:
                continue
            corners = [(XE(a), YE(b)) for a in (c0, c1) for b in (r0, r1)]
            if all(inside(hidden, p) for p in corners):
                continue  # under the vat
            g = 0.22 * P
            x0, x1 = XE(c0) + (g if c0 > 0 else 0), XE(c1) - (g if c1 < 24 else 0)
            y1, y0 = YE(r0) - (g if r0 > 0 else 0), YE(r1) + (g if r1 < 28 else 0)
            h = Z_BASE + 0.006 * ((k * 7) % 5) - 0.008
            g2 = 0.12 * P * ((k * 11) % 3)
            y1 -= g2 if r0 > 0 else 0
            bevel_block(bm, x0, y0, x1, y1, Z_BASE - 0.02, h, 0.022, shade[(k * 5 + i) % 3])


def vat(bm, M):
    """The oval stave vat: staves (V-grooved boards standing on the pad, their ends proud of the
    deck as a chime), two iron hoops, the flat north deck round the pit with its coping ring, the
    pit liner and floor, and the sloped south end planked down to the front."""
    n = len(OUTER)
    nrm = normals(OUTER)
    per = 3                       # outline segments per stave: 40 staves
    g, c = 0.09 * P, 0.28 * P     # gap and chamfer at each stave edge: the groove between boards

    def chime(x, y):
        return ztop(y) + (Z_CHIME - Z_TOP)

    for s in range(n // per):
        idx = [(s * per + k) % n for k in range(per + 1)]
        po = [OUTER[i] for i in idx]
        pi = [INNER[i] for i in idx]
        tx, ty = po[-1][0] - po[0][0], po[-1][1] - po[0][1]
        ln = math.hypot(tx, ty)
        tx, ty = tx / ln, ty / ln
        n0, n1 = nrm[idx[0]], nrm[idx[-1]]
        a, b = po[0], po[-1]
        poly = [(a[0] - n0[0] * c + tx * g, a[1] - n0[1] * c + ty * g), (a[0] + tx * (g + c), a[1] + ty * (g + c))]
        poly += po[1:-1]
        poly += [(b[0] - tx * (g + c), b[1] - ty * (g + c)), (b[0] - n1[0] * c - tx * g, b[1] - n1[1] * c - ty * g)]
        poly += [(pi[-1][0] - tx * g, pi[-1][1] - ty * g)] + list(reversed(pi[1:-1])) + [(pi[0][0] + tx * g, pi[0][1] + ty * g)]
        prism_var(bm, poly, Z_BASE - 0.01, chime, M["STAVE"])
    # A dark core behind the staves (what the grooves show) up to the pit floor and the slope.
    core = offset(INNER, 0.15 * P)
    prism_var(bm, core, Z_BASE - 0.01, lambda x, y: min(Z_PIT - 0.03, ztop(y) - 0.04), M["CORE"])
    # Iron hoops proud of the staves; the upper one follows the slope down the south end.
    hi_o, hi_i = offset(OUTER, 0.32 * P)[::2], offset(OUTER, -0.2 * P)[::2]
    n = len(hi_o)
    for zh, dip in ((0.17, None), (0.80, 0.085)):
        before = set(bm.faces)
        ring = []
        for (xo, yo), (xi, yi) in zip(hi_o, hi_i):
            zc = zh if dip is None else min(zh, ztop((yo + yi) / 2) - dip)
            ring.append([bm.verts.new((xi, yi, zc - 0.028)), bm.verts.new((xo, yo, zc - 0.022)),
                         bm.verts.new((xo, yo, zc + 0.022)), bm.verts.new((xi, yi, zc + 0.028))])
        for i in range(n):
            j = (i + 1) % n
            for k in range(4):
                l = (k + 1) % 4
                bm.faces.new((ring[i][k], ring[j][k], ring[j][l], ring[i][l]))
        _tag(bm, before, M["HOOP"], False)
    # North deck: the ring from the pit mouth out to the staves, north of the crest; a solid from the
    # pit floor up to the deck, built radially from the pit axis.
    north = clip(offset(INNER, 0.1 * P), lambda p: p[1] - YE(R_HI))
    north = [(CX + (x - CX) / SX, y) for x, y in north]  # into pit space (round), squashed back below
    v_pit = set(bm.verts)
    na = 64
    before = set(bm.faces)
    rings = []
    for i in range(na):
        a = 2 * math.pi * i / na
        d = (math.cos(a), math.sin(a))
        ro = ray_hit(north, (CX, CY), d)
        rings.append([bm.verts.new((CX + R_PIT * d[0], CY + R_PIT * d[1], Z_PIT - 0.03)),
                      bm.verts.new((CX + ro * d[0], CY + ro * d[1], Z_PIT - 0.03)),
                      bm.verts.new((CX + ro * d[0], CY + ro * d[1], Z_TOP)),
                      bm.verts.new((CX + R_PIT * d[0], CY + R_PIT * d[1], Z_TOP))])
    for i in range(na):
        j = (i + 1) % na
        for k in range(4):
            l = (k + 1) % 4
            bm.faces.new((rings[i][k], rings[j][k], rings[j][l], rings[i][l]))
    _tag(bm, before, M["DECK"], False)
    # Coping ring round the pit: twelve wooden segments, chamfered both edges, joints as gaps.
    nb = 12
    gap = 0.12 * P / R_COP
    for i in range(nb):
        a0 = 2 * math.pi * i / nb + 0.2
        a1 = a0 + 2 * math.pi / nb - gap
        revolve(bm, [(R_PIT, Z_TOP - 0.04), (R_COP, Z_TOP - 0.04), (R_COP, Z_RIM - 0.022), (R_COP - 0.022, Z_RIM),
                     (R_PIT + 0.022, Z_RIM), (R_PIT, Z_RIM - 0.022)], M["RIM"], sides=6, a0=a0, a1=a1, smooth=False)
    # Pit liner (dark steel) from the rim down to the floor, and the floor.
    revolve(bm, [(R_PIT - 0.5 * P, Z_PIT - 0.02), (R_PIT + 0.4 * P, Z_PIT - 0.02), (R_PIT + 0.4 * P, Z_TOP - 0.03),
                 (R_PIT - 0.5 * P, Z_TOP - 0.03)], M["LINER"], smooth=True)
    revolve(bm, [(R_PIT - 0.5 * P, Z_TOP - 0.10), (R_PIT, Z_TOP - 0.10), (R_PIT, Z_TOP - 0.03), (R_PIT - 0.5 * P, Z_TOP - 0.03)],
            M["LINER"], smooth=False)
    revolve(bm, disc_profile(R_PIT, Z_PIT - 0.04, Z_PIT), M["FLOOR"], smooth=False)
    # Leaf tracks along the diagonals on the floor, and the emitter's collar in the middle.
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        r0, r1, w = 2.6 * P, R_PIT - 0.2 * P, 0.45 * P
        pts = []
        for rr, ww in ((r0, -w), (r1, -w), (r1, w), (r0, w)):
            pts.append((CX + rr * ca - ww * sa, CY + rr * sa + ww * ca))
        before = set(bm.faces)
        common.slab(bm, pts, 0.03, z=Z_PIT + 0.015, mat_index=M["TRACK"])
        _tag(bm, before, M["TRACK"], False)
    revolve(bm, ring_profile(1.6 * P, 3.0 * P, Z_PIT - 0.01, Z_PIT + 0.07, ch=0.02), M["COLLAR"], sides=24)
    # Pockets: steel housings over the slots the leaves slide into, on the rim's inner edge.
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        rc = R_PIT + 0.55 * P
        hw, hl = 1.25 * P, 1.0 * P  # half width (across), half length (radial)
        corners = []
        for rr, ww in ((rc - hl, -hw), (rc + hl, -hw), (rc + hl, hw), (rc - hl, hw)):
            corners.append((CX + rr * ca - ww * sa, CY + rr * sa + ww * ca))
        lo = [(x, y, Z_TOP - 0.06) for x, y in corners]
        top_in = 0.02 / max(hw, hl)
        hi = [(x + (sum(p[0] for p in corners) / 4 - x) * top_in * 2,
               y + (sum(p[1] for p in corners) / 4 - y) * top_in * 2, Z_RIM + 0.035)
              for x, y in corners]
        hexa(bm, lo + hi, M["POCKET"])
    squash(bm, v_pit)
    # Iron bolt heads on the rim (165 north-east, 163 south-west in the sprite).
    for (cc, r), m in (((14.5, 2.5), M["PIN_N"]), ((8.5, 14.5), M["PIN_S"])):
        revolve(bm, disc_profile(0.55 * P, Z_RIM - 0.01, Z_RIM + 0.022, ch=0.012), m, sides=10,
                cx=XE(cc), cy=YE(r), smooth=False)
    # South end: planks running down the slope from the crest to the foot, over a dark bed.
    south = clip(offset(INNER, 0.1 * P), lambda p: YE(R_HI) - p[1])
    prism_var(bm, south, Z_FRONT - 0.12, lambda x, y: ztop(y) - 0.004, M["CORE"])
    xs = [p[0] for p in south]
    x0, x1 = min(xs), max(xs)
    nplank = 11
    w = (x1 - x0) / nplank
    for k in range(nplank):
        xa, xb = x0 + k * w + 0.06 * P, x0 + (k + 1) * w - 0.06 * P
        strip = clip(clip(south, lambda p, xa=xa: p[0] - xa), lambda p, xb=xb: xb - p[0])
        if len(strip) < 3 or abs(area(strip)) < 1e-6:
            continue
        prism_var(bm, strip, Z_FRONT - 0.06, lambda x, y: ztop(y) + 0.014, M["PLANK"])


# The slot hatch on the slope (rows and cols in sprite pixel edges).
H_C0, H_C1 = 8.0, 14.0           # slot between the jambs
H_R0, H_R1 = 20.0, 23.55         # slot rows (sill below)
PL = 0.011                       # plank face, out along the slope normal


def hatch(bm, M):
    """The hatch set into the planks: pale lintel board at the crest, the fixed panel the shutter
    slides up behind, dark iron jambs either side of the slot and a sill at its foot."""
    slope_box(bm, XE(8.3), XE(15.7), 16.05, 17.3, PL - 0.01, PL + 0.03, M["LINTEL"], ch=0.01)
    slope_box(bm, XE(H_C0), XE(H_C1), 17.3, H_R0, PL - 0.01, PL + 0.018, M["PANEL"], ch=0.006)
    for c0, c1 in ((H_C0 - 0.45, H_C0), (H_C1, H_C1 + 0.7)):
        slope_box(bm, XE(c0), XE(c1), 17.3, R_LO - 0.05, PL - 0.01, PL + 0.022, M["JAMB"], ch=0.005)
    slope_box(bm, XE(H_C0), XE(H_C1), H_R1, R_LO - 0.05, PL - 0.01, PL + 0.016, M["JAMB"], ch=0.005)


def window_glass(bm, mat, bar):
    """The slot: one glass plate flush in the planks, between the jambs."""
    slope_box(bm, XE(H_C0), XE(H_C1), H_R0, H_R1, PL - 0.01, PL + 0.002, mat)
    del bar


def door(bm, M, bottom):
    """The shutter over the slot: three boards and a batten, lower edge at row `bottom`. Its top
    runs up behind the fixed panel when raised."""
    xi0, xi1 = XE(H_C0 + 0.05), XE(H_C1 - 0.05)
    top = max(17.4, bottom - 4.2)
    w = (xi1 - xi0) / 3
    for k in range(3):
        slope_box(bm, xi0 + k * w + 0.05 * P, xi0 + (k + 1) * w - 0.05 * P, top, bottom, PL + 0.004, PL + 0.013,
                  M["DOOR"], ch=0.003)
    if bottom - 0.95 > H_R0:  # the batten shows only below the fixed panel
        slope_box(bm, xi0 + 0.1 * P, xi1 - 0.1 * P, bottom - 1.0, bottom - 0.45, PL + 0.012, PL + 0.017, M["BATTEN"])
def leaf(bm, sx, sy, off, mat, zb=Z_RIM - 0.045, hd=0.075, gap=0.3 * P, nr=5, na=8):
    """One iris leaf (a quarter of a shallow dome) in quadrant (sx, sy), slid out diagonally so its
    inner corner sits `off` from the axis in x and y; the part past the pit mouth is in the pocket
    (not built). Returns nothing if fully retracted."""
    o = gap + off
    R = R_PIT - 0.05 * P
    if o >= R / math.sqrt(2) - 0.15 * P:
        return
    phi0 = math.asin(o / R)
    phi1 = math.pi / 2 - phi0
    lead = gap  # the leaf's own corner (dome crest) relative to the visible corner

    def height(lx, ly):
        # Dome crest at the leaf's own corner, which is at (o, o) here.
        rho = math.hypot(lx - o, ly - o)
        return zb + hd * max(0.0, 1 - (rho / (R + 0.0)) ** 2)

    before = set(bm.faces)
    corner_top = bm.verts.new((CX + sx * o, CY + sy * o, height(o, o)))
    grid = []
    for i in range(1, nr + 1):
        s = i / nr
        row = []
        for j in range(na + 1):
            ph = phi0 + (phi1 - phi0) * j / na
            lx = o + s * (R * math.cos(ph) - o)
            ly = o + s * (R * math.sin(ph) - o)
            row.append(bm.verts.new((CX + sx * lx, CY + sy * ly, height(lx, ly))))
        grid.append(row)
    for j in range(na):
        bm.faces.new((corner_top, grid[0][j], grid[0][j + 1]))
    for i in range(nr - 1):
        for j in range(na):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    loop = [corner_top] + [grid[i][0] for i in range(nr)] + [grid[nr - 1][j] for j in range(1, na + 1)] \
        + [grid[i][na] for i in range(nr - 2, -1, -1)]
    low = [bm.verts.new((v.co.x, v.co.y, zb - 0.035)) for v in loop]
    n = len(loop)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((loop[i], low[i], low[j], loop[j]))
    bm.faces.new(list(reversed(low)))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True
    # A raised rib along the leaf's straight edges (the machined lip that seals the seam).
    del lead


def emitter(bm, M, r_core, r_hot, core_mat, hot_mat, glow_mat=None, r_glow=0.0):
    """The gun's emitter in the pit: a glass dome in the collar, a hot centre; a glow disc round it."""
    if glow_mat is not None and r_glow > 0:
        revolve(bm, ring_profile(3.0 * P, r_glow, Z_PIT + 0.002, Z_PIT + 0.012), glow_mat, sides=28, smooth=False)
    k = r_core / (3.2 * P)
    revolve(bm, [(0, Z_PIT + 0.02)] + [(r_core * math.cos(t), Z_PIT + 0.05 + 0.16 * k * math.sin(t))
                                        for t in [i * math.pi / 2 / 7 for i in range(8)]],
            core_mat, sides=24, closed_profile=False)
    revolve(bm, [(0, Z_PIT + 0.05 + 0.16 * k - 0.02)] + [(r_hot * math.cos(t), Z_PIT + 0.05 + 0.16 * k - 0.02 + 0.07 * k * math.sin(t))
                                                         for t in [i * math.pi / 2 / 5 for i in range(6)]],
            hot_mat, sides=16, closed_profile=False)


# --- Stages -------------------------------------------------------------------------------------

# (suffix, frames, leaf offset px (None = gone), shutter lower-edge row per frame (None = up), lit)
STAGES = [
    ("", [169, 205, 207], None, None, True),
    ("-f2", [193], 0.2, {193: H_R1}, False),
    ("-f3", [195], 1.4, {195: H_R1}, False),
    ("-f4", [197], 2.4, {197: H_R1}, False),
    ("-f5", [199], None, {199: 23.0}, False),
    ("-f6", [201, 203], None, {201: 22.0, 203: 21.0}, False),
]
# Lit emitter per frame on the main model: (glow ring, core, hot centre palette; radii in px).
CORES = {169: (112, 118, 124, 4.6, 3.3, 1.5), 207: (113, 116, 122, 3.8, 2.7, 1.2), 205: (112, 114, 118, 3.2, 2.1, 0.9)}
WINDOW = {169: 116, 207: 116, 205: 113}


def build(sprite, name, frames, leaf_off, doors, lit):
    coll = common.reset_collection(name)

    def pal(i, tag=NAME, **kw):
        return common.palette_material(sprite, i, tag, **kw)

    mats = []
    M = {}

    def add(key, m):
        M[key] = len(mats)
        mats.append(m)

    add("MORTAR", pal(2, metallic=0.0, roughness=0.95))
    add("SETT_A", pal(5, metallic=0.0, roughness=0.85))
    add("SETT_B", pal(6, metallic=0.0, roughness=0.85))
    add("SETT_C", pal(4, metallic=0.0, roughness=0.9))
    add("STAVE", pal(20, metallic=0.0, roughness=0.75))
    add("CORE", pal(16, metallic=0.0, roughness=0.9))
    add("HOOP", pal(18, metallic=0.5, roughness=0.5))
    add("DECK", pal(21, metallic=0.0, roughness=0.7))
    add("PLANK", pal(19, metallic=0.0, roughness=0.75))
    add("JAMB", pal(16, metallic=0.4, roughness=0.55))
    add("RIM", pal(22, metallic=0.0, roughness=0.65))
    add("LINER", pal(3, metallic=0.3, roughness=0.7))
    add("FLOOR", pal(2, metallic=0.3, roughness=0.7))
    add("TRACK", pal(4, metallic=0.6, roughness=0.45))
    add("COLLAR", pal(4, metallic=0.6, roughness=0.4))
    add("POCKET", pal(10, metallic=0.65, roughness=0.35))
    add("PIN_N", pal(165, metallic=0.4, roughness=0.5))
    add("PIN_S", pal(163, metallic=0.4, roughness=0.5))
    add("PANEL", pal(19, metallic=0.0, roughness=0.85))
    add("LINTEL", pal(23, metallic=0.0, roughness=0.6))
    add("DOOR", pal(18, metallic=0.0, roughness=0.85))
    add("BATTEN", pal(18, metallic=0.0, roughness=0.75))
    add("LEAF", pal(7, metallic=0.5, roughness=0.5))
    add("DARKCORE", pal(3, metallic=0.2, roughness=0.3))
    add("DARKHOT", pal(4, metallic=0.2, roughness=0.3))
    if lit:
        add("GLASS", pal(116, tag=NAME + "-window", emission_strength=1.2, frames={f: WINDOW[f] for f in frames}))
    elif 203 in frames:
        add("GLASS", pal(2, tag=NAME + "-window-dim", metallic=0.0, roughness=0.4, frames={203: 112}))
    else:
        add("GLASS", pal(2, metallic=0.0, roughness=0.4))

    bm = bmesh.new()
    stone_pad(bm, M)
    vat(bm, M)
    hatch(bm, M)
    window_glass(bm, M["GLASS"], M["BATTEN"])
    v_pit = set(bm.verts)
    if leaf_off is not None:
        for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            leaf(bm, sx, sy, leaf_off * P, M["LEAF"])
    if not lit:
        emitter(bm, M, 2.6 * P, 1.0 * P, M["DARKCORE"], M["DARKHOT"])
    squash(bm, v_pit)
    parts = []
    if doors:
        rows = set(doors.values())
        if len(rows) == 1:
            door(bm, M, rows.pop())
        else:
            for f, row in doors.items():
                dbm = bmesh.new()
                door(dbm, M, row)
                parts.append(common.frame_part(to_object(f"{name}-door-{f}", dbm, mats, coll), [f]))
    if lit:
        for f, (pg, pc, ph, rg, rc, rh) in CORES.items():
            cm = list(mats)
            gi, ci, hi = len(cm), len(cm) + 1, len(cm) + 2
            cm += [pal(pg, tag=f"{NAME}-glow{f}", emission_strength=1.5),
                   pal(pc, tag=f"{NAME}-core{f}", emission_strength=3.0),
                   pal(ph, tag=f"{NAME}-hot{f}", emission_strength=4.0)]
            cbm = bmesh.new()
            emitter(cbm, M, rc * P, rh * P, ci, hi, gi, rg * P)
            squash(cbm, set())
            parts.append(common.frame_part(to_object(f"{name}-core-{f}", cbm, cm, coll), [f]))
    body = to_object(name, bm, mats, coll)
    shell = common.outline_shell(body, coll, faces=2500)
    return [body] + parts + [shell]


def main():
    sprite = common.load_sprite(WT, NAME)
    for suffix, frames, leaf_off, doors, lit in STAGES:
        name = NAME + suffix
        objs = build(sprite, name, frames, leaf_off, doors, lit)
        sub = [{**s, "frames": [f for f in s["frames"] if f in frames]} for s in sprite["sprites"]]
        sub = [s for s in sub if s["frames"]]
        out = common.export_sprite_model(ROOT, objs, f"enemies/{name}", sub)
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if "outline" not in o.name)
        print(f"built {out.name}: {tris} tris (+ shell {sum(len(p.vertices) - 2 for p in objs[-1].data.polygons)})")
        for o in objs:
            o.hide_render = True


if __name__ == "__main__":
    main()
