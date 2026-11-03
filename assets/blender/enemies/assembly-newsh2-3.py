"""Long ground pipe (newsh2.shp frames 1, 3 and 5; enemies 21-23): a hard-surface build.

Nine 2x2 enemies in a row make one 216 x 28 px pipe lying on the ground (sprite.json
`assemblyLayout`): newsh2-1 is its left end, newsh2-3 the repeating section (seven of them) and
newsh2-5 the right end. The pipe is built whole in assembly pixels and cut into its pieces with
common.split_assembly (cut faces filled); every section is identical (the build is periodic with a
24 px period), so only the first newsh2-3 (the leftmost) is exported and the game repeats it.

The sprite is authoritative for the plan outline, the parts it shows and their colours:
- Grey cans of radius 6 px on an axis at row edge 13, 8 px up (the big end clamp, radius 8, stands
  on the ground): a long can across each section's left edge (columns 23..12) and a short can
  (15..20). Their dark end columns are rolled rims round dished end faces, each with a ring of
  flange bolts round the coupling.
- A red split clamp (columns 2..8, radius 7) over the long can; its split is the sprite's dark slot
  on the screen-bottom flank (rows 15-17): a dark channel between two clamp lugs, drawn together by
  a draw bolt. The left end has the bigger clamp (columns 18..24, radius 8, split the same way) with
  a bolt ring on its outer face.
- Red coupling sleeves between the cans (columns 12-14, rows 8..14, and 20-22, rows 9..14): smaller
  than the cans and above their axis, so the ground shows under them; below them the sprite's dark
  strip (row 16, row 15) is a tie rod between the can flanges (a turnbuckle in the second gap).
- The left end (newsh2-1) is square in plan: a shallow dished head with a tight knuckle, a girth
  seam and a drain boss. The right end (newsh2-5) is a machined band, a seam groove and a stepped
  shoulder, then an ogive nose cone fitted to the sprite's row widths (a monotone cubic) that ends
  in a small rounded tip at column 21.
- Saddle supports under the cans carry the pipe (hidden under it in plan; seen from the side).
Colours: palette index per part = the median of the sprite pixels the part covers, the darkest
shading (1-3) and the highlights (10+, 77+) left out: cans, head, band and cone 7 (the cone's
own pixels give 4-5, most of them the shading of its tapering flanks; the game's light shades the
cone itself, so it keeps the cans' grey, as the review asked), can ends 4, clamps 72, sleeves 71, slot, tie rods
and saddles 16, bolts steel 8. Satin metal (low metalness, as the ships, D52-D53).

Texture: each piece bakes its own occlusion and edge-lift colour multiplier and a
roughness/metal map (the ships' bake, usp_talon.bake_maps), with its neighbours in the pipe
around it so the joints shade alike; no concept projection (maps.json "bake": "model"). Each piece
is exported with an outline shell (common.outline_shell, D51). The underside is a plain closed
shape, no detail.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-3.py [-- --preview out.png]
[--no-bake] (the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import bisect
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b120 as lib  # noqa: E402

NAME = "assembly-newsh2-3"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-1", "newsh2-3", "newsh2-5"]
W, H = 216, 28  # the assembly grid in pixels; its centre is the Blender origin
PX = 1 / 12
AY, AZ = 13.0, 8.0  # the cans' axis: row edge 13, 8 px up
R = 6.0              # can radius (rims); bodies RB
RB = 5.95

# Material slots -> palette index, and (metallic, roughness): satin, not mirror.
GREY, GREY_DK, RED, NECK, SLOT, STEEL = range(6)
PAL_OF = {GREY: 7, GREY_DK: 4, RED: 72, NECK: 71, SLOT: 16, STEEL: 8}
FINISH = {GREY: (0.3, 0.42), GREY_DK: (0.3, 0.5), RED: (0.15, 0.45), NECK: (0.15, 0.42),
          SLOT: (0.15, 0.72), STEEL: (0.45, 0.36)}
# The baked colour map's tint (linear multipliers): neutral grey stays neutral under three's
# Neutral tone mapping, so the multiplier is untinted.
TINT = (1.0, 1.0, 1.0)


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys) (as usp_talon.pchip)."""
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
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


# --- primitives, in assembly px (x = column edge, y = row edge, screen-down +, z up) -------------

class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, mat):
        f = self.bm.faces.new(verts)
        f.material_index = mat
        return f

    def revolve(self, prof, cy=AY, cz=AZ, sides=32, mats=None, mat=GREY, a0=None, a1=None, closed=False,
                phase=0.0):
        """Revolve a profile of (x, r) points about the X axis through (cy, cz). Angle 0 = up,
        positive towards the screen bottom (+y). Full turn by default; with a0/a1 (radians) a
        sector, its ends capped (the profile must then be a closed loop: closed=True). `mats`
        gives a material per profile segment. A point with r = 0 is a single vertex (a pole)."""
        full = a0 is None
        if full:
            angles = [phase + 2 * math.pi * k / sides for k in range(sides)]
        else:
            n = max(2, int(math.ceil((a1 - a0) / (2 * math.pi / sides))))
            angles = [a0 + (a1 - a0) * k / n for k in range(n + 1)]
        rings = []
        for x, r in prof:
            if r <= 1e-6 and full:
                rings.append([self.bm.verts.new((x, cy, cz))] * len(angles))
                continue
            rings.append([self.bm.verts.new((x, cy + r * math.sin(a), cz + r * math.cos(a))) for a in angles])
        segs = list(range(len(prof) - 1)) + ([len(prof) - 1] if closed else [])
        na = len(angles)
        for s in segs:
            r0, r1 = rings[s], rings[(s + 1) % len(prof)]
            m = mats[s] if mats else mat
            for i in range(na if full else na - 1):
                j = (i + 1) % na
                uniq = []
                for v in (r0[i], r0[j], r1[j], r1[i]):
                    if v not in uniq:
                        uniq.append(v)
                if len(uniq) >= 3:
                    self.face(uniq, m)
        if full:
            for ring in (rings[0], rings[-1]):  # open ends (a profile not closed on the axis)
                if len(set(ring)) > 2:
                    self.face(ring, mats[0] if mats else mat)
        else:
            for k in (0, na - 1):
                self.face([ring[k] for ring in rings], mats[0] if mats else mat)

    def extrude_x(self, poly, x0, x1, mat):
        """A prism along X of a (y, z) polygon."""
        a = [self.bm.verts.new((x0, y, z)) for y, z in poly]
        b = [self.bm.verts.new((x1, y, z)) for y, z in poly]
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            self.face([a[i], a[j], b[j], b[i]], mat)
        self.face(a, mat)
        self.face(b[::-1], mat)

    def obox(self, c, u, v, w, hu, hv, hw, mat):
        """An oriented box: centre c, unit axes u, v, w, half sizes."""
        c, u, v, w = Vector(c), Vector(u), Vector(v), Vector(w)
        vs = {}
        for su in (-1, 1):
            for sv in (-1, 1):
                for sw in (-1, 1):
                    vs[su, sv, sw] = self.bm.verts.new(c + u * su * hu + v * sv * hv + w * sw * hw)
        for f in (((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)),
                  ((1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1)),
                  ((-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)),
                  ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)),
                  ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)),
                  ((-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1))):
            self.face([vs[k] for k in f], mat)

    def bolt(self, base, d, r, h, mat=STEEL, sides=6):
        """A hex bolt head standing on `base`, along direction d, height h, its top chamfered."""
        d = Vector(d).normalized()
        u = d.orthogonal().normalized()
        v = d.cross(u)
        base = Vector(base) - d * 0.15  # sunk a little into the surface
        rings = []
        for t, rr in ((0.0, r), (h + 0.15 - 0.1, r), (h + 0.15, r * 0.72)):
            rings.append([self.bm.verts.new(base + d * t + (u * math.cos(a) + v * math.sin(a)) * rr)
                          for a in (2 * math.pi * k / sides + math.pi / sides for k in range(sides))])
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                self.face([r0[i], r0[j], r1[j], r1[i]], mat)
        self.face(rings[0][::-1], mat)
        self.face(rings[-1], mat)

    def tube(self, p0, p1, r, mat, sides=8):
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0).normalized()
        u = d.orthogonal().normalized()
        v = d.cross(u)
        rings = [[self.bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * r)
                  for a in (2 * math.pi * k / sides for k in range(sides))] for p in (p0, p1)]
        for i in range(sides):
            j = (i + 1) % sides
            self.face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]], mat)
        self.face(rings[0][::-1], mat)
        self.face(rings[1], mat)


def radial(a, r, cy=AY, cz=AZ):
    """(y, z) of the point at angle a (0 up, + towards screen bottom), radius r about (cy, cz)."""
    return cy + r * math.sin(a), cz + r * math.cos(a)


# --- parts ---------------------------------------------------------------------------------------

NECK1 = (11.0, AZ + 1.0, 2.9)   # first coupling sleeve: centre row edge, height, radius
NECK2 = (11.5, AZ + 1.0, 2.4)   # second (thinner) sleeve
TIE1 = (16.5, 4.2)              # tie rod under the first sleeve: row edge, height (the sprite's row 16)
TIE2 = (15.5, 4.6)              # under the second (row 15)


def can_end(lead, x, gap=None):
    """Profile of a can's rolled rim and dished end face at x (lead: the can starts at x)."""
    s = 1 if lead else -1
    p = [(x + s * 0.5, 0.0), (x + s * 0.5, 3.4), (x + s * 0.12, 4.6), (x, 5.35), (x + s * 0.12, 5.85),
         (x + s * 0.42, R), (x + s * 0.85, R), (x + s * 1.0, RB)]
    m = [GREY_DK, GREY_DK, GREY_DK, GREY, GREY, GREY, GREY]
    if not lead:
        p, m = p[::-1], m[::-1]
    return p, m


def can(B, x0, x1, seams=(), sides=36):
    """A grey can from x0 to x1: rolled rim beads at its ends, the body between, weld beads at `seams`."""
    p, m = can_end(True, x0)
    m.append(GREY)
    for x in seams:
        p += [(x - 0.22, RB), (x - 0.1, RB + 0.08), (x + 0.1, RB + 0.08), (x + 0.22, RB)]
        m += [GREY] * 4
    q, n = can_end(False, x1)
    B.revolve(p + q, sides=sides, mats=m + n)


def flange_bolts(B, x, sgn, neck, tie):
    """A ring of flange bolts on a can's dished end face at x (facing sgn along X) round the
    coupling sleeve; none underneath, none in the sleeve or on the tie rod's nut."""
    ny, nz, nr = neck
    ty, tz = tie
    rr = 4.15
    for k in range(12):
        a = 2 * math.pi * k / 12 + math.pi / 12
        a = math.atan2(math.sin(a), math.cos(a))
        if abs(a) > math.radians(118):
            continue
        y, z = radial(a, rr)
        if math.hypot(y - ny, z - nz) < nr + 0.7 or math.hypot(y - ty, z - tz) < 1.2:
            continue
        B.bolt((x + sgn * 0.3, y, z), (sgn, 0, 0), 0.36, 0.26, STEEL)


def sleeve(B, x0, x1, neck):
    """A red coupling sleeve between two cans (x0..x1 visible), above and behind the cans' axis:
    a plain sleeve with a ferrule at each end and a raised band in the middle, its ends buried in
    the cans' dished faces."""
    cy, cz, r = neck
    xa, xb = x0 - 0.6, x1 + 0.6
    xm = (x0 + x1) / 2
    prof = [(xa, 0.0), (xa, r + 0.2), (x0 + 0.45, r + 0.2), (x0 + 0.6, r), (xm - 0.42, r), (xm - 0.3, r + 0.1),
            (xm + 0.3, r + 0.1), (xm + 0.42, r), (x1 - 0.6, r), (x1 - 0.45, r + 0.2), (xb, r + 0.2), (xb, 0.0)]
    B.revolve(prof, cy=cy, cz=cz, sides=20, mat=NECK)


def tie_rod(B, x0, x1, tie, turnbuckle=False):
    """A dark tie rod low on the south flank between two can end faces, with nuts on the faces."""
    y, z = tie
    B.revolve([(x0 - 0.4, 0.0), (x0 - 0.4, 0.42), (x1 + 0.4, 0.42), (x1 + 0.4, 0.0)], cy=y, cz=z, sides=10,
              mat=SLOT)
    for x, s in ((x0, 1), (x1, -1)):
        B.bolt((x, y, z), (s, 0, 0), 0.6, 0.3, SLOT)
    if turnbuckle:
        a, b = x0 + 0.6, x1 - 0.6
        B.revolve([(a, 0.0), (a, 0.62), (a + 0.25, 0.8), (b - 0.25, 0.8), (b, 0.62), (b, 0.0)], cy=y, cz=z,
                  sides=8, mat=SLOT, phase=math.pi / 8)


def clamp(B, x0, x1, r, gap, sides=44, bolts_out=None):
    """A red split clamp from x0 to x1 of radius r round a can (inner radius 5.5), chamfered edges;
    split by `gap` = (a0, a1) radians on its south flank: a dark channel between two clamp lugs
    standing out of the band, drawn together by a draw bolt with a nut on each lug. `bolts_out` =
    (x, sign) of a face that gets a ring of bolt heads."""
    c = 0.45
    xm = (x0 + x1) / 2
    a0, a1 = gap
    prof = [(x0, 5.5), (x0, r - c), (x0 + c, r), (x1 - c, r), (x1, r - c), (x1, 5.5)]
    B.revolve(prof, sides=sides, mat=RED, a0=a1, a1=a0 + 2 * math.pi, closed=True)
    # The split: a dark channel below the band's surface.
    B.revolve([(x0 + 0.3, 5.4), (x0 + 0.3, r - 1.0), (x1 - 0.3, r - 1.0), (x1 - 0.3, 5.4)],
              sides=sides, mat=SLOT, a0=a0 - 0.02, a1=a1 + 0.02, closed=True)
    # Clamp lugs: thick ears standing out radially either side of the channel.
    lw = (x1 - x0) / 2 - 0.5
    ends = []
    for a, s in ((a0, -1), (a1, 1)):
        ac = a - s * math.radians(4.5)  # the lug sits on the band, beside the channel
        u = Vector((0, math.sin(ac), math.cos(ac)))
        t = Vector((0, math.cos(ac), -math.sin(ac)))
        centre = Vector((xm, AY, AZ)) + u * (r + 0.05)
        B.obox(centre, (1, 0, 0), t, u, lw, 0.36, 0.42, RED)
        ends.append(Vector((xm, AY, AZ)) + u * (r + 0.2))
    # The draw bolt across the split, through both lugs, a hex nut on the outside of each.
    pa, pb = ends
    d = (pb - pa).normalized()
    B.tube(pa - d * 0.4, pb + d * 0.4, 0.26, STEEL, sides=8)
    B.bolt(pa - d * 0.36, -d, 0.44, 0.3, STEEL)
    B.bolt(pb + d * 0.36, d, 0.44, 0.3, STEEL)
    if bolts_out is not None:
        xf, sgn = bolts_out
        rr = (5.95 + r - c) / 2
        for k in range(14):
            a = 2 * math.pi * k / 14 + math.pi / 14
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > math.radians(118) or a0 - 0.2 < a < a1 + 0.2:
                continue  # none underneath (never seen) or at the split
            y, z = radial(a, rr)
            B.bolt((xf, y, z), (sgn, 0, 0), 0.42, 0.3, STEEL)


def saddle(B, x0, x1):
    """A ground support under a can: a base plate, a web and a cradle the can rests in (hidden under
    the pipe in plan, seen from the side)."""
    ac = 0.62
    cr = 6.35
    poly = [(AY - 4.9, 0.0), (AY + 4.9, 0.0), (AY + 4.9, 0.45), (AY + 3.5, 0.6)]
    yo, zo = radial(math.pi - ac, cr)
    poly.append((yo, zo))
    for k in range(9):  # the cradle's seat, a little inside the can
        a = math.pi - ac + 2 * ac * k / 8
        poly.append(radial(a, RB - 0.2))
    yo, zo = radial(math.pi + ac, cr)
    poly += [(yo, zo), (AY - 3.5, 0.6), (AY - 4.9, 0.45)]
    B.extrude_x(poly, x0, x1, SLOT)
    # Anchor bolts on the base plate's feet.
    for y in (AY - 4.3, AY + 4.3):
        B.bolt(((x0 + x1) / 2, y, 0.45), (0, 0, 1), 0.3, 0.2, STEEL)


def section(B, o):
    """One repeating section (newsh2-3) with its left edge at column o."""
    can(B, o - 1.0, o + 12.0, seams=(o + 9.9,))
    clamp(B, o + 2.2, o + 7.8, 7.0, (math.radians(20), math.radians(44)))
    for xf, sgn in ((o + 2.2, -1), (o + 7.8, 1)):  # bolts on both faces of the clamp
        for k in range(10):
            a = 2 * math.pi * k / 10
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > math.radians(112) or math.radians(5) < a < math.radians(60):
                continue
            y, z = radial(a, 6.22)
            B.bolt((xf, y, z), (sgn, 0, 0), 0.3, 0.24, STEEL)
    sleeve(B, o + 12.0, o + 15.0, NECK1)
    flange_bolts(B, o + 12.0, 1, NECK1, TIE1)
    flange_bolts(B, o + 15.0, -1, NECK1, TIE1)
    tie_rod(B, o + 12.0, o + 15.0, TIE1)
    can(B, o + 15.0, o + 20.0)
    sleeve(B, o + 20.0, o + 23.0, NECK2)
    flange_bolts(B, o + 20.0, 1, NECK2, TIE2)
    flange_bolts(B, o + 23.0, -1, NECK2, TIE2)
    tie_rod(B, o + 20.0, o + 23.0, TIE2, turnbuckle=True)
    saddle(B, o + 8.7, o + 10.7)
    saddle(B, o + 16.6, o + 18.4)


def left_end(B):
    """newsh2-1, columns 0..24: a shallow dished head with a tight knuckle (square in plan, as the
    sprite's first column), a girth seam, a sleeve, and a can under the big end clamp."""
    hx = [0.0, 0.02, 0.06, 0.12, 0.2, 0.32, 0.5, 0.8, 1.3]
    hr = [0.0, 2.4, 3.9, 4.8, 5.3, 5.6, 5.82, 5.94, R]
    prof = list(zip(hx, hr)) + [(3.15, R), (3.3, RB - 0.2), (3.6, RB - 0.2), (3.75, R), (6.98, RB),
                                (7.1, RB + 0.06), (7.3, RB + 0.06), (7.42, RB)]
    mats = [GREY] * (len(prof) - 1)
    q, n = can_end(False, 11.0)
    mats += [GREY] + n
    B.revolve(prof + q, sides=40, mats=mats)
    # The drain boss in the middle of the dish and a ring of stud bolts round the knuckle.
    B.bolt((0.02, AY, AZ), (-1, 0, 0), 1.05, 0.4, STEEL)
    for k in range(10):
        a = 2 * math.pi * k / 10 + math.pi / 10
        a = math.atan2(math.sin(a), math.cos(a))
        if abs(a) > math.radians(120):
            continue
        y, z = radial(a, 3.4)
        B.bolt((0.08, y, z), (-1, 0, 0), 0.38, 0.22, STEEL)
    sleeve(B, 11.0, 14.0, NECK1)
    flange_bolts(B, 11.0, 1, NECK1, TIE1)
    flange_bolts(B, 14.0, -1, NECK1, TIE1)
    tie_rod(B, 11.0, 14.0, TIE1)
    # The end can runs under the big clamp to the piece's edge (the first section's can overlaps it).
    p, m = can_end(True, 14.0)
    B.revolve(p + [(24.2, RB), (24.2, 0.0)], sides=40, mats=m + [GREY, GREY])
    clamp(B, 18.2, 23.85, 8.0, (math.radians(24), math.radians(46)), bolts_out=(18.2, -1))
    saddle(B, 4.4, 6.4)
    saddle(B, 15.4, 17.4)


# The nose cone's radius (px) at column edges (newsh2-5's own columns), a monotone cubic fitted to
# the sprite's row widths (10 rows at columns 6-9, 8 at 10-13, 6 at 14-16, 4 at 17-18, 2 at 19-20).
CONE_X = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 17.5, 19.0, 20.3]
CONE_R = [5.0, 4.95, 4.5, 4.0, 3.55, 3.0, 2.4, 1.6, 1.0]
TIP = 0.9  # the rounded tip's length beyond CONE_X[-1]


def right_end(B):
    """newsh2-5, columns 192..216: the last can (from the last section's column 23) as a machined
    band with a seam groove, a stepped shoulder, then the nose cone with a panel seam and a rounded
    tip."""
    o = 192.0
    p, m = can_end(True, o - 1.0)
    m.append(GREY)
    p += [(o + 1.9, RB), (o + 2.05, RB - 0.22), (o + 2.35, RB - 0.22), (o + 2.5, RB),  # seam groove
          (o + 5.2, RB), (o + 5.35, R), (o + 5.75, R), (o + 5.95, 5.6), (o + 6.0, CONE_R[0] + 0.15)]
    m += [GREY] * 8
    cone = pchip([o + x for x in CONE_X], CONE_R)
    n = 26
    xs = [o + CONE_X[0] + (CONE_X[-1] - CONE_X[0]) * k / n for k in range(n + 1)]
    pts = [(x, cone(x)) for x in xs if abs(x - (o + 12.0)) > 0.25]
    rs = cone(o + 12.0)  # a panel seam round the cone
    pts += [(o + 11.85, rs), (o + 11.93, rs - 0.18), (o + 12.07, rs - 0.18), (o + 12.15, rs)]
    x0, r0 = o + CONE_X[-1], CONE_R[-1]  # the rounded tip
    pts += [(x0 + TIP * math.sin(k / 6 * math.pi / 2), r0 * math.cos(k / 6 * math.pi / 2)) for k in range(1, 6)]
    pts.sort()
    pts.append((x0 + TIP, 0.0))
    p += pts
    m += [GREY] * len(pts)
    B.revolve(p, sides=40, mats=m)
    saddle(B, o + 0.8, o + 2.6)


def build(sprite, coll):
    B = Builder()
    left_end(B)
    for t in range(1, 8):
        section(B, 24 * t)
    right_end(B)
    bm = B.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # px (y screen-down) to Blender units: X = (x - 108) / 12, Y = (14 - y) / 12, Z = z / 12.
    mtx = Matrix(((PX, 0, 0, -W / 2 * PX), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite):
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    smooth(obj)
    return obj


def smooth(obj, angle=38):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))


def materials(sprite):
    return [common.palette_material(sprite, PAL_OF[s], "nsh2a3", metallic=FINISH[s][0], roughness=FINISH[s][1])
            for s in range(len(PAL_OF))]


# --- texture: baked occlusion and edge lift (no concept projection) -----------------------------

def bake_piece(obj, tag, size=512, samples=64):
    """The ships' bake (usp_talon.bake_maps) for one piece, in its place in the pipe with its
    neighbours visible (the caller sets that up): a grey colour multiplier (occlusion at two scales
    and a light lift on bevelled edges, TINT) and a metallic-roughness map (G roughness, B
    metallic), wired in as Base Color = map x palette colour on copies of the palette materials
    (pal_<index>_..._<tag>; each piece has its own maps)."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("newsh2: no GPU bake", err)
    me = obj.data
    mats = [m.copy() for m in me.materials]
    for i, m in enumerate(mats):
        m.name = f"{me.materials[i].name}_{tag}"
        me.materials[i] = m
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

    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
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

        def math_(op, a, b=None):
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
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.62, math_("MULTIPLY", occl, 0.5)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
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
        img.pack()

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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-3")
    sprite = common.load_sprite(ROOT, "newsh2-3")
    sprite["colors"] = colors
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    # Every layout position (assembly coordinates, centre origin); newsh2-3 repeats and its first
    # copy (left of the row) is the one exported.
    lay = [(e["model"], e["cx"] - x0 - W / 2, e["cy"] - y0 - H / 2) for e in layout]
    first_cx = min(cx for n, cx, _ in lay if n == "newsh2-3")
    pieces_layout = [e for e in lay if e[0] != "newsh2-3" or e[1] == first_cx]
    pieces_layout = sorted(pieces_layout, key=lambda e: PIECES.index(e[0]))
    pieces = common.split_assembly(obj, pieces_layout)
    for n, p in pieces.items():
        smooth(p)
        print(f"newsh2: {n} {sum(len(q.vertices) - 2 for q in p.data.polygons)} triangles")
    # Closed copies for the outline shells, before the bake adds its maps (and so its rays never
    # hit a shell).
    closed = {}
    for n, p in pieces.items():
        c = p.copy()
        c.data = p.data.copy()
        coll.objects.link(c)
        c.hide_render = True
        closed[n] = c
    fmt = "AUTO"
    obj.hide_render = True
    if "--no-bake" not in argv:
        # Each exported piece baked in its place, every other layout position as an occluder.
        occ = []
        for name, cx, cy in lay:
            o = pieces[name].copy()
            o.data = pieces[name].data.copy()
            coll.objects.link(o)
            o.location = (cx * PX, -cy * PX, 0)
            o.hide_render = True
            occ.append((o, cx))
        for name, cx, cy in pieces_layout:
            for o, ocx in occ:
                o.hide_render = ocx == cx
            p = pieces[name]
            saved = p.location.copy()
            p.location = (cx * PX, -cy * PX, 0)
            p.hide_render = False
            bake_piece(p, name.replace("newsh2-", "p"))
            p.location = saved
        for o, _ in occ:
            bpy.data.objects.remove(o, do_unlink=True)
        fmt = "WEBP"
    for name, _, _ in pieces_layout:
        shell = common.outline_shell(closed[name], coll, faces=1500)
        shell.name = shell.data.name = f"{name}_outline"
        bpy.data.objects.remove(closed[name])
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], shell], f"enemies/{name}", data["sprites"],
                                   image_format=fmt)
        shell.hide_render = True
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        w, h = len(grid[0]), len(grid)
        Wp = max(w, round(h * 24 / 28))
        Hp = round(Wp * 28 / 24)
        ref = lib.composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(Wp, Hp))
        obj.hide_render = False
        common.render_preview([obj], str(out), str(ref), size=Wp / 12, view_px=640)
        for name, _, _ in pieces_layout:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
