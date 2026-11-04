"""Long ground pipe (newsh2.shp frames 1, 3 and 5; enemies 21-23): a hard-surface build.

Nine 2x2 enemies in a row make one 216 x 28 px pipe lying on the ground (sprite.json
`assemblyLayout`): newsh2-1 is its left end, newsh2-3 the repeating section (seven of them) and
newsh2-5 the right end. The pipe is built whole in assembly pixels and cut into its pieces with
common.split_assembly (cut faces filled); every section is identical (the build is periodic with a
24 px period), so only the first newsh2-3 (the leftmost) is exported and the game repeats it.

The sprite is authoritative for the plan outline, the parts it shows and their colours. The plan
goes to the INNER edge of the sprite's ink border (D74, docs/agents/OUTLINE-BORDER.md; the game's
ink outline stands in for it): `tools/sprite_mask.py assembly-newsh2-3 --measure` gives
iou_rule_grid 1.0 on every piece.
- Grey cans of radius 5 px on an axis at row edge 13, 8 px up (the big end clamp, radius 7, stands
  on the ground): a long can across each section's left edge (columns 0..10) and a short can
  (16..18), rolled rims round dished end faces.
- A red clamp ring (columns 2..7, radius 6; red over 3..6, its edge rails grey as the sprite's
  columns beside the band) on the long can. The sprite's hole through its screen-bottom flank (rows
  15-17, the ground seen through it) is a real elliptic window cut through the ring; the pipe
  passes through the ring as a thin neck there, so the ground shows. The left end has the bigger
  ring (columns 18..23, radius 7, stepped to 6 at its edge columns) with the same window and a bolt
  ring on its outer face.
- Red coupling sleeves between the cans (columns 12-14, rows 9..12, and 20-22, rows 10..12): smaller
  than the cans and above their axis, so the ground shows under them. The sprite's dark end columns
  either side of each sleeve are pipe flanges round the sleeve's ends (rows 8-13 and 9-13), bolted;
  below them the sprite's dark strip (row 16, rows 15-16) is a tie rod between the can faces, its
  long nuts in the flange columns (a turnbuckle in the second gap).
- The left end (newsh2-1) is square in plan: a shallow dome with a tight knuckle, a girth seam and a
  drain boss (the sprite's one pixel at column 0). The right end (newsh2-5) is a machined band, a
  seam groove and a stepped shoulder, then an ogive nose cone fitted to the inner edge of the
  sprite's row widths (a monotone cubic) that ends in a small rounded tip at column 19.
- Saddle supports under the cans carry the pipe (hidden under it in plan; seen from the side).
Colours: palette index per part = the median of the sprite pixels the part covers, the darkest
shading (1-3) and the highlights (10+, 77+) left out: cans, head, band and cone 7 (the cone's
own pixels give 4-5, most of them the shading of its tapering flanks; the game's light shades the
cone itself, so it keeps the cans' grey, as the review asked), can ends and flanges 4, clamps 72, sleeves 71, slot, tie rods
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
R = 5.0              # can radius (rims); bodies RB: the inner edge of the sprite's ink (D74)
RB = 4.95

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
                phase=0.0, caps=True):
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
            if closed or not caps:
                return
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

# Coupling sleeves (centre row edge, height, radius) and their end flanges' radius: the sprite's
# dark end columns either side of each sleeve are the flanges (inner rows 8-13 round sleeve 1,
# 9-13 round sleeve 2); the cans themselves stop at the columns inside them.
NECK1 = (11.0, AZ + 1.0, 2.0)   # first coupling sleeve (inner rows 9-12)
NECK2 = (11.5, AZ + 1.0, 1.5)   # second (thinner) sleeve (inner rows 10-12)
FL1, FL2 = 3.0, 2.5             # their flanges
TIE1 = (16.5, 4.2)              # tie rod under the first sleeve: row edge, height (the sprite's row 16)
TIE2 = (16.0, 4.4)              # under the second (rows 15-16, the nuts fill them in the flange columns)
# The clamp rings' window: the sprite's hole through the ring's south flank (the ground seen through
# it, rows 15-17), (centre column offset, centre row edge, half width, half height).
WIN = (5.4, 16.5, 2.3, 1.65)
WIN_BIG = (21.45, 17.5, 2.3, 1.8)


def can_end(lead, x, gap=None):
    """Profile of a can's rolled rim and dished end face at x (lead: the can starts at x)."""
    s = 1 if lead else -1
    p = [(x + s * 0.5, 0.0), (x + s * 0.5, 2.8), (x + s * 0.12, 3.85), (x, 4.45), (x + s * 0.1, 4.88),
         (x + s * 0.35, R), (x + s * 0.7, R), (x + s * 0.85, RB)]
    m = [GREY_DK, GREY_DK, GREY_DK, GREY, GREY, GREY, GREY]
    if not lead:
        p, m = p[::-1], m[::-1]
    return p, m


def can(B, x0, x1, seams=(), sides=36):
    """A grey can from x0 to x1: rolled rim beads at its ends, the body between, weld beads at `seams`."""
    p, m = can_end(True, x0)
    m.append(GREY)
    for x in seams:
        p += [(x - 0.22, RB), (x - 0.1, RB + 0.05), (x + 0.1, RB + 0.05), (x + 0.22, RB)]
        m += [GREY] * 4
    q, n = can_end(False, x1)
    B.revolve(p + q, sides=sides, mats=m + n)


def flange(B, x0, x1, neck, rf, sgn):
    """A dark pipe flange plate from x0 to x1 round a sleeve's end (centred on the sleeve), chamfered,
    with a ring of bolt heads on its face towards the sleeve (sgn: that face's direction)."""
    cy, cz, r = neck
    c = 0.15
    prof = [(x0, 0.0), (x0, rf - c), (x0 + c, rf), (x1 - c, rf), (x1, rf - c), (x1, 0.0)]
    B.revolve(prof, cy=cy, cz=cz, sides=24, mat=GREY_DK)
    rr = (r + rf) / 2 + 0.05
    xf = x1 if sgn > 0 else x0
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        a = math.atan2(math.sin(a), math.cos(a))
        if abs(a) > math.radians(115):
            continue  # none underneath (never seen)
        y, z = radial(a, rr, cy, cz)
        B.bolt((xf, y, z), (sgn, 0, 0), 0.27, 0.2, STEEL)


def sleeve(B, x0, x1, neck):
    """A red coupling sleeve between two flanges (x0..x1 visible), above and behind the cans' axis,
    a raised band in the middle; its ends buried in the flanges."""
    cy, cz, r = neck
    xa, xb = x0 - 0.6, x1 + 0.6
    xm = (x0 + x1) / 2
    prof = [(xa, 0.0), (xa, r), (xm - 0.42, r), (xm - 0.3, r + 0.1), (xm + 0.3, r + 0.1), (xm + 0.42, r),
            (xb, r), (xb, 0.0)]
    B.revolve(prof, cy=cy, cz=cz, sides=20, mat=NECK)


def coupling(B, x0, x1, neck, rf, tie, turnbuckle=False):
    """Flange (column x0-1..x0), sleeve (x0..x1), flange (x1..x1+1), and the tie rod under them from
    can face to can face (x0-1 and x1+1)."""
    flange(B, x0 - 1.0, x0, neck, rf, 1)
    flange(B, x1, x1 + 1.0, neck, rf, -1)
    sleeve(B, x0, x1, neck)
    tie_rod(B, x0 - 1.0, x1 + 1.0, tie, turnbuckle)


def tie_rod(B, x0, x1, tie, turnbuckle=False):
    """A dark tie rod low on the south flank between two can end faces, with long nuts on the faces
    (in the flange columns, as the sprite's dark pixels there)."""
    y, z = tie
    B.revolve([(x0 - 0.4, 0.0), (x0 - 0.4, 0.36), (x1 + 0.4, 0.36), (x1 + 0.4, 0.0)], cy=y, cz=z, sides=10,
              mat=SLOT)
    for x, s in ((x0, 1), (x1, -1)):
        B.bolt((x, y, z), (s, 0, 0), 0.68, 0.62, SLOT)
    if turnbuckle:
        a, b = (x0 + x1) / 2 - 0.8, (x0 + x1) / 2 + 0.8
        B.revolve([(a, 0.0), (a, 0.6), (a + 0.25, 0.75), (b - 0.25, 0.75), (b, 0.6), (b, 0.0)], cy=y, cz=z,
                  sides=8, mat=SLOT, phase=math.pi / 8)


def window(bm_part, cx, cy, ax, ay, mat=RED, n=40):
    """Cut a vertical elliptic window (plan centre (cx, cy), half axes ax, ay, px) through a closed
    part with an exact boolean; returns the cut part as a new bmesh. Its walls take `mat`."""
    me = bpy.data.meshes.new("nsh2a3_part")
    bm_part.to_mesh(me)
    bm_part.free()
    obj = bpy.data.objects.new("nsh2a3_part", me)
    bpy.context.scene.collection.objects.link(obj)
    cb = bmesh.new()
    lo = [cb.verts.new((cx + ax * math.cos(2 * math.pi * k / n), cy + ay * math.sin(2 * math.pi * k / n), -2.0))
          for k in range(n)]
    hi = [cb.verts.new((v.co.x, v.co.y, 30.0)) for v in lo]
    for k in range(n):
        j = (k + 1) % n
        cb.faces.new([lo[k], lo[j], hi[j], hi[k]]).material_index = mat
    cb.faces.new(lo[::-1]).material_index = mat
    cb.faces.new(hi).material_index = mat
    cme = bpy.data.meshes.new("nsh2a3_cut")
    cb.to_mesh(cme)
    cb.free()
    cut = bpy.data.objects.new("nsh2a3_cut", cme)
    bpy.context.scene.collection.objects.link(cut)
    mod = obj.modifiers.new("window", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.material_mode = "INDEX"
    mod.object = cut
    dg = bpy.context.evaluated_depsgraph_get()
    res = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    out = bmesh.new()
    out.from_mesh(res)
    for o in (obj, cut):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in (me, cme, res):
        bpy.data.meshes.remove(m)
    return out


def clamp(B, x0, x1, r, win, red, sides=44, step=None, bolts_out=None):
    """A red clamp ring from x0 to x1 of radius r (inner radius 4.8, on the can ends), chamfered;
    `step` = (w, r2): its edges w wide at the smaller radius r2. A window `win` (plan) through its
    south flank shows the ground, as the sprite's hole: the pipe passes through the ring as a thin
    neck there. The band is red over `red` = (xa, xb), its edge rails beyond grey (the sprite's grey
    columns either side of the red band). `bolts_out` = (x, sign) of a face that gets a ring of bolt heads."""
    c = 0.3
    ri = 4.8
    if step:
        w, r2 = step
        prof = [(x0, ri), (x0, r2 - 0.15), (x0 + 0.15, r2), (x0 + w - 0.12, r2), (x0 + w, r - 0.25),
                (x0 + w + 0.25, r), (x1 - w - 0.25, r), (x1 - w, r - 0.25), (x1 - w + 0.12, r2), (x1 - 0.15, r2),
                (x1, r2 - 0.15), (x1, ri)]
    else:
        prof = [(x0, ri), (x0, r - c), (x0 + c, r), (red[0], r), (red[1], r), (x1 - c, r), (x1, r - c), (x1, ri),
                (red[1], ri), (red[0], ri)]
    P = Builder()
    P.revolve(prof, sides=sides, mat=RED, closed=True)
    bmesh.ops.remove_doubles(P.bm, verts=P.bm.verts, dist=1e-5)
    cut = window(P.bm, *win)
    for f in cut.faces:  # (a mesh without material slots loses the indices: set them here)
        f.material_index = RED if red[0] <= f.calc_center_median().x <= red[1] else GREY
    tmp = bpy.data.meshes.new("nsh2a3_tmp")
    cut.to_mesh(tmp)
    cut.free()
    B.bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)
    if bolts_out is not None:
        xf, sgn = bolts_out
        rr = (ri + (step[1] if step else r)) / 2 + 0.1
        for k in range(14):
            a = 2 * math.pi * k / 14 + math.pi / 14
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > math.radians(118) or a > math.radians(12):
                continue  # none underneath (never seen) or at the window
            y, z = radial(a, rr)
            B.bolt((xf, y, z), (sgn, 0, 0), 0.38, 0.28, STEEL)


def neck(B, x0, x1):
    """The thin pipe through a clamp ring, between the can ends (seen only through the window's
    edges and from the side)."""
    B.revolve([(x0, 0.0), (x0, 2.6), (x1, 2.6), (x1, 0.0)], cy=NECK1[0], cz=NECK1[1], sides=20, mat=NECK)


def saddle(B, x0, x1):
    """A ground support under a can: a base plate, a web and a cradle the can rests in (hidden under
    the pipe in plan, seen from the side)."""
    ac = 0.62
    cr = R + 0.3
    poly = [(AY - 4.3, 0.0), (AY + 4.3, 0.0), (AY + 4.3, 0.45), (AY + 3.0, 0.6)]
    yo, zo = radial(math.pi - ac, cr)
    poly.append((yo, zo))
    for k in range(9):  # the cradle's seat, a little inside the can
        a = math.pi - ac + 2 * ac * k / 8
        poly.append(radial(a, RB - 0.2))
    yo, zo = radial(math.pi + ac, cr)
    poly += [(yo, zo), (AY - 3.0, 0.6), (AY - 4.3, 0.45)]
    B.extrude_x(poly, x0, x1, SLOT)
    # Anchor bolts on the base plate's feet.
    for y in (AY - 3.7, AY + 3.7):
        B.bolt(((x0 + x1) / 2, y, 0.45), (0, 0, 1), 0.28, 0.2, STEEL)


def section(B, o):
    """One repeating section (newsh2-3) with its left edge at column o: the long can (columns
    o..o+10) through the clamp ring (o+2..o+7), sleeve 1 (o+12..o+14) between its flanges (o+11,
    o+15), the short can (o+16..o+18), sleeve 2 (o+20..o+22) between its flanges (o+19, o+23)."""
    can(B, o, o + 3.1)
    neck(B, o + 2.6, o + 8.2)
    can(B, o + 7.75, o + 11.0, seams=(o + 9.9,))
    cx, cy, ax, ay = WIN
    clamp(B, o + 2.0, o + 8.4, 6.0, (o + cx, cy, ax, ay), (o + 3.0, o + 7.0))
    for xf, sgn in ((o + 2.0, -1), (o + 8.4, 1)):  # bolts on both faces of the clamp
        for k in range(10):
            a = 2 * math.pi * k / 10
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > math.radians(112) or a > math.radians(12):
                continue
            y, z = radial(a, 5.45)
            B.bolt((xf, y, z), (sgn, 0, 0), 0.28, 0.22, STEEL)
    coupling(B, o + 12.0, o + 15.0, NECK1, FL1, TIE1)
    can(B, o + 16.0, o + 19.0)
    coupling(B, o + 20.0, o + 23.0, NECK2, FL2, TIE2, turnbuckle=True)
    saddle(B, o + 8.6, o + 10.4)
    saddle(B, o + 16.6, o + 18.4)


def left_end(B):
    """newsh2-1, columns 0..24: a domed head with a tight knuckle (square in plan, as the sprite's
    first columns), a girth seam, a coupling, and a can under the big end clamp ring."""
    x0 = 0.8
    hx = [0.0, 0.02, 0.06, 0.12, 0.2, 0.32, 0.5, 0.8, 1.3]
    hr = [0.0, 2.0, 3.25, 4.0, 4.42, 4.67, 4.85, 4.95, R]
    prof = [(x0 + x, r) for x, r in zip(hx, hr)] + [(3.15, R), (3.3, RB - 0.2), (3.6, RB - 0.2), (3.75, R),
                                                    (6.98, RB), (7.1, RB + 0.05), (7.3, RB + 0.05), (7.42, RB)]
    mats = [GREY] * (len(prof) - 1)
    q, n = can_end(False, 10.0)
    mats += [GREY] + n
    B.revolve(prof + q, sides=40, mats=mats)
    # The drain boss on the dome (the sprite's one pixel at column 0) and a ring of stud bolts.
    B.revolve([(0.0, 0.0), (0.0, 0.42), (0.1, 0.55), (0.75, 0.55), (0.75, 0.0)], cy=11.5, cz=AZ, sides=6,
              mat=STEEL, phase=math.pi / 6)
    for k in range(10):
        a = 2 * math.pi * k / 10 + math.pi / 10
        a = math.atan2(math.sin(a), math.cos(a))
        if abs(a) > math.radians(120):
            continue
        y, z = radial(a, 3.4)
        B.bolt((x0 + 0.12, y, z), (-1, 0, 0), 0.34, 0.2, STEEL)
    coupling(B, 11.0, 14.0, NECK1, FL1, TIE1)
    can(B, 15.0, 19.0)
    neck(B, 18.6, 24.2)
    cx, cy, ax, ay = WIN_BIG
    clamp(B, 18.0, 23.95, 7.0, (cx, cy, ax, ay), (19.0, 23.0), step=(1.0, 6.0), bolts_out=(18.0, -1))
    saddle(B, 4.4, 6.4)
    saddle(B, 15.6, 17.4)


# The nose cone's radius (px) at column edges (newsh2-5's own columns), a monotone cubic fitted to
# the inner edge of the sprite's row widths (8 rows at columns 6-9, 6 at 10-13, 4 at 14-16, 2 at
# 17-18; D74).
CONE_X = [6.0, 10.0, 14.0, 17.0, 19.0]
CONE_R = [4.5, 3.5, 2.5, 1.5, 0.6]
TIP = 0.5  # the rounded tip's length beyond CONE_X[-1]


def right_end(B):
    """newsh2-5, columns 192..216: the last can as a machined band with a seam groove, a stepped
    shoulder, then the nose cone with a panel seam and a rounded tip."""
    o = 192.0
    p, m = can_end(True, o)
    m.append(GREY)
    p += [(o + 1.9, RB), (o + 2.05, RB - 0.22), (o + 2.35, RB - 0.22), (o + 2.5, RB),  # seam groove
          (o + 5.2, RB), (o + 5.3, R), (o + 5.7, R), (o + 5.9, 4.75), (o + 6.0, CONE_R[0] + 0.05)]
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
