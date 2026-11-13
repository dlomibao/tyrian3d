"""TORM / BOTANY end boss (newshj.shp, assembly-newshj-191 merged with assembly-newshj-267).

WHAT IT IS: a hovering biomechanical plant pod, 96 x 112 px, the end boss of TORM (2.1) and BOTANY A/B
(2.10 / 2.11), also in 4.11. Link-64 velocity events move it round the screen, so it flies free: a
closed pod with a round underside, no ground plate. A 4 x 3 block of 24 x 28 pieces (newshj-153 ..
newshj-235) and a centred row of three below (newshj-267 / 269 / 271) are one object, built whole here
and cut into the pieces with common.split_assembly.

The model leads with cross sections (blueprint.json heights, re-fitted to the ground-pass height budget
of D120 / D153: belly -5, crown <= 31.5 px):
- the pod: a loft of soft superellipse sections, one per sprite row, its half width the sprite's inner
  mask row by row (axis at column edge 48.5); the equator at z 4, a shallow elliptic belly to -5;
- the south end splits into two lobes (the 267 row): their own lofts, each ending in a V tip, the
  centre gap open from row 81. Each lobe starts inside the pod's section at row 64 (narrower, lower)
  and swells out of the shell by row 77, while the pod's own south end sinks inside the lobes, so
  the side shows one surface, no end walls; the V edges are smoothed lines, not the pixel staircase;
- the flank half widths are a smoothed curve ([1 2 3 2 1] moving average, twice);
- ribs: the sprite's green columns traced per band of rows and chained down the body, then each run
  straightened to one centreline (least squares) with one constant width; stubs under 6 rows are
  dropped. A half-round strip (4 arc segments) laid along the (smoothed) shell normal, clipped to the
  inner mask and kept off the steep flank (shell normal z >= 0.55 under both edges, sampled every
  half row), its centre and width smoothed along it, ends chamfered; pieces under 6 rows after the
  clip are dropped, so the flank below the pods is bare shell; the seams are the dark shell showing;
- the hull's sections are packed toward the equator (short facets on the steep flank), its lighter
  north cap (rows < 19) is on the top only, and the shoulder step (rows 11-14) is eased;
- the 267 row's light strips: one continuous strip per sprite run (a bar on the left lobe, a U on
  the right), dark pure green 194 / 195 with a low glow, laid on the ribs;
- the sprite's see-through slits (left and right of the eye housing, round the mechanism under it)
  are designed vents: pchip centrelines traced from the hole pixels, a constant 1.4-2.2 px width, the
  rim chamfered, cut (exact boolean) through the hull and the housing parts only; the closed-eye -f3
  models carry a dark plate in them (the sprite's frames 193 / 195 fill them with ink);
- grey machinery: posts on the shoulders, a flat cross band (3.2 px, rows 19-21) arching from them
  over the shoulder lobes into the housing, with bolts, the dark eye housing with brows,
  the glowing two-lobed eye lens under a segmented spine and its block, the mechanism, barrel and a
  square muzzle housing with a ring; grey pods on both flanks, lofted along the row axis on the shell
  (rounded edges, the outer edge a fixed inset from the rim, a strap, a lit sloping south end) on the
  analytic hull surface, with a round bead all round the foot so the seam is one smoothed line.

Run: blender --background --python assets/blender/enemies/assembly-newshj-191.py -- [--out whole.glb]
     [--views DIR]
Always exports the 21 game models (the 15 pieces and the eye / front frame variants) to
public/models/enemies/ and src/render/spriteModels/ (common.export_sprite_model); newshj-267 / 269 / 271
are built here too (the old assembly-newshj-267 script is gone).
--out: the whole boss (all 15 base pieces at their places, with outline shells) as one glb.
--views: review renders (top_flat mask, top, side, front, rear, q1, q2, game, under) into DIR.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = WT
NAME = "assembly-newshj-191"
TAG = "nshj191"
PX = 1 / 12
AXIS = 48.5  # column edge of the symmetry axis
EQ = 4.0  # equator height (px)
BELLY = 9.0  # belly depth below the equator (px): bottom at -5
# glb extra `tyrian_anchor` (D181), model units over the base: the height pinned on the camera ray at the
# sprite's point. The same on all 21 models, so the pieces still meet and the tall domes (crown 2.6) stay
# on screen as long as the sprite's do at the top edge (TORM t7863).
ANCHOR = 2.0

# piece -> (centre col, centre row) in the 96 x 112 grid
BLOCK = [("newshj-153", 142, -16), ("newshj-155", 166, -16), ("newshj-157", 190, -16), ("newshj-159", 214, -16),
         ("newshj-191", 142, 12), ("newshj-161", 166, 12), ("newshj-163", 190, 12), ("newshj-197", 214, 12),
         ("newshj-229", 142, 40), ("newshj-231", 166, 40), ("newshj-233", 190, 40), ("newshj-235", 214, 40)]
CENTRE = {n: (cx - 130, cy + 30) for n, cx, cy in BLOCK}
for i, n in enumerate(["newshj-267", "newshj-269", "newshj-271"]):
    CENTRE[n] = (24 + 24 * i, 98)
PIECES = list(CENTRE)
# Layout for split_assembly: Blender X = (col - AXIS) / 12, Y = (14 - row) / 12 (T.finish).
LAYOUT = {n: (c - AXIS, r - 14) for n, (c, r) in CENTRE.items()}

# Exported models: model -> (piece, frames it covers (None = the piece's own list), variant)
MODELS = {**{p: (p, None, "base") for p in PIECES},
          "newshj-161": ("newshj-161", [165, 203, 237, 275], "base"),
          "newshj-163": ("newshj-163", [167, 205, 239, 277], "base"),
          "newshj-231": ("newshj-231", [241], "base"),
          "newshj-233": ("newshj-233", [243], "base"),
          "newshj-161-f2": ("newshj-161", [161, 199], "dim"),
          "newshj-163-f2": ("newshj-163", [163, 201], "dim"),
          "newshj-161-f3": ("newshj-161", [193], "grey"),
          "newshj-163-f3": ("newshj-163", [195], "grey"),
          "newshj-231-f2": ("newshj-231", [231], "lit"),
          "newshj-233-f2": ("newshj-233", [233], "lit")}
GLOW_STEPS = {"core-small": (165, 167), "core": (203, 205), "flecks-pale": (237, 239), "flecks-yellow": (275, 277)}
DIM_STEPS = ((161, 163), (199, 201))


# --- sprite --------------------------------------------------------------------------------------

def load_all():
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    colors = {}
    for d in sprites.values():
        colors.update(d["colors"])
    want = {"newshj-161": 203, "newshj-163": 205, "newshj-231": 241, "newshj-233": 243}
    grid = [[-1] * 96 for _ in range(112)]
    for n, (cc, cr) in CENTRE.items():
        idx = want.get(n, int(n.split("-")[1]))
        f = next(f for f in sprites[n]["frames"] if f["index"] == idx)
        for r, row in enumerate(f["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[cr - 14 + r][cc - 12 + c] = v
    return sprites, colors, grid


SPR, COLORS, GRID = load_all()
SPRITE = {"name": NAME, "colors": COLORS}
sys.path.insert(0, str(WT / "tools"))
import sprite_mask as SM  # noqa: E402
MASKS = SM.masks(GRID, {int(k): tuple(v) for k, v in COLORS.items()})


def inner_runs(r):
    row = MASKS["inner"][r]
    out, s = [], None
    for c in range(97):
        v = c < 96 and row[c]
        if v and s is None:
            s = c
        if not v and s is not None:
            out.append([s, c - 1])
            s = None
    return out


def luma(i):
    r, g, b = COLORS[str(i)]
    return 0.3 * r + 0.59 * g + 0.11 * b


def median_index(cols, rows, keep):
    vals = [GRID[r][c] for r in rows for c in cols if 0 <= r < 112 and 0 <= c < 96 and GRID[r][c] >= 0 and keep(GRID[r][c])]
    if not vals:
        return None
    vals.sort(key=luma)
    k = int(len(vals) * 0.15)
    core = vals[k:len(vals) - k] or vals
    return core[len(core) // 2]


def runs_of_row(r):
    """Opaque runs of a sprite row, ignoring the ink border pixels at their ends."""
    row = GRID[r]
    out, s = [], None
    for c in range(97):
        v = c < 96 and row[c] >= 0
        if v and s is None:
            s = c
        if not v and s is not None:
            out.append([s, c - 1])
            s = None
    return out


def inner_extent(r):
    """(left edge, right edge) of a row's inner area (the outer ink pixel trimmed), as column edges."""
    rs = runs_of_row(r)
    if not rs:
        return None
    lo, hi = rs[0][0], rs[-1][1]
    if luma(GRID[r][lo]) < 26:
        lo += 1
    if luma(GRID[r][hi]) < 26:
        hi -= 1
    return lo, hi + 1


# --- materials -------------------------------------------------------------------------------------

class Mats:
    def __init__(self):
        self.list, self.slot = [], {}

    def get(self, key, pal, metallic=0.3, roughness=0.5, emission=0.0):
        if key not in self.slot:
            self.slot[key] = len(self.list)
            self.list.append((key, pal, metallic, roughness, emission))
        return self.slot[key]

    def build(self, override=None):
        """Blender materials per slot; `override` {key: (pal, metallic, roughness, emission, frames)}."""
        out = []
        for key, pal, met, rough, em in self.list:
            frames = None
            if override and key in override:
                pal, met, rough, em, frames = override[key]
            tag = TAG + key
            out.append(common.palette_material(SPRITE, pal, tag, metallic=met, roughness=rough,
                                               emission_strength=em, frames=frames))
        return out


M = Mats()
SHELL = M.get("shell", 35, 0.15, 0.55)
SHELL_HI = M.get("shell_hi", 37, 0.15, 0.5)
SEAM = M.get("seam", 1, 0.0, 0.9)
SOCKET = M.get("socket", 5, 0.25, 0.45)
BROW = M.get("brow", 5, 0.25, 0.45)
BAR = M.get("bar", 4, 0.25, 0.4)
POST = M.get("post", 6, 0.25, 0.35)
POD = M.get("pod", 7, 0.25, 0.4)
POD_LIT = M.get("pod_lit", 9, 0.25, 0.35)
MECH = M.get("mech", 5, 0.25, 0.4)
MECH_LT = M.get("mech_lt", 8, 0.25, 0.35)
BARREL = M.get("barrel", 4, 0.25, 0.35)
HOUSING = M.get("housing", 2, 0.4, 0.5)
RING = M.get("ring", 4, 0.25, 0.3)
BORE = M.get("bore", 1, 0.0, 0.9)
BOLT = M.get("bolt", 12, 0.6, 0.25)
SPINE = M.get("spine", 7, 0.25, 0.35)
SPINE_LT = M.get("spine_lt", 11, 0.25, 0.3)
EYE = M.get("eye", 204, 0.1, 0.15, 1.6)


# --- profiles ---------------------------------------------------------------------------------------

def hw_row(r):
    rs = inner_runs(r)
    if not rs:
        return 0.0
    lo, hi = rs[0][0], rs[-1][1] + 1
    return ((AXIS - lo) + (hi - AXIS)) / 2


HW = {r: hw_row(r) for r in range(3, 81)}
# The shoulder step (row 13 is the ear tips; the sprite's half width jumps 30.5 -> 39.5 over rows
# 11-13): eased over rows 11-14, so the ear's north face is a sloped, rounded shoulder (a 6-9 px jump
# between two stations made a flat wall facing north that read as a strip in the side view).
HW[11], HW[12], HW[13], HW[14] = 31.0, 33.4, 36.8, 39.8
# The flanks (rows 15-79) as a smooth curve, not the pixel staircase: a [1 2 3 2 1] / 9 moving
# average, run six times (the sprite's edge there is one curve; raw half widths step by whole pixels,
# and fewer passes left waves down the steep flank; ~23 px more off the mask edge, IoU -0.003).
for _pass in range(6):
    _raw = dict(HW)
    for _r in range(15, 80):
        _w = [(_raw.get(_r + d, _raw[min(max(_r + d, 3), 80)]), k) for d, k in ((-2, 1), (-1, 2), (0, 3), (1, 2), (2, 1))]
        HW[_r] = sum(v * k for v, k in _w) / 9
CROWN = T.pchip([2.6, 5, 10, 16, 30, 45, 60, 72, 82, 94, 102.5], [2.5, 8.5, 13.5, 17, 19, 19, 17.5, 15, 12, 7, 2])
BELLYF = T.pchip([2.6, 6, 14, 26, 70, 82, 94, 102.5], [2.0, 5.5, 8.0, 9.0, 9.0, 7.5, 5, 2])


def hw_at(y):
    """Half width of the main pod at row coordinate y (row r spans y r..r+1, sampled at r + 0.5)."""
    r = y - 0.5
    r0 = int(math.floor(r))
    r0 = max(3, min(r0, 80))
    r1 = max(3, min(r0 + 1, 80))
    t = max(0.0, min(1.0, r - r0))
    return HW[r0] * (1 - t) + HW[r1] * t


def lobe_edges():
    """Rows 81-101: (outer, inner) edge x of the left lobe, the left run averaged with the mirrored
    right run (column edges), then smoothed ([1 2 1] / 4, twice) so the V's edges are straight lines
    rather than the pixel staircase."""
    raw = {}
    for r in range(81, 102):
        rs = inner_runs(r)
        lo, hi = rs[0][0], rs[0][1] + 1
        ro, ri = rs[-1][1] + 1, rs[-1][0]
        raw[r] = [((lo - AXIS) + (AXIS - ro)) / 2, ((hi - AXIS) + (AXIS - ri)) / 2 if len(rs) > 1 else -0.7]
    for _ in range(2):
        prev = {r: list(v) for r, v in raw.items()}
        for r in range(82, 101):
            for k in (0, 1):
                raw[r][k] = (prev[r - 1][k] + 2 * prev[r][k] + prev[r + 1][k]) / 4
    return {r: tuple(v) for r, v in raw.items()}


LOBE_EDGES = lobe_edges()


def section(hw, crown, belly, n=36, pt=2.3, pb=2.0, xc=0.0, dense=0.0):
    """Closed section points (x, z): a soft superellipse top (2/3 of the points), an elliptic belly,
    equator at EQ. `dense` (0..0.8) packs the points toward the equator, where the superellipse turns
    fastest (short facets on the steep flank, so things sitting on it meet a smooth surface)."""
    pts = []
    nt = (2 * n) // 3
    nb = n - nt

    def g(u):
        return u - dense * math.sin(2 * math.pi * u) / (2 * math.pi)
    for i in range(n):
        t = math.pi * g(i / nt) if i <= nt else math.pi + math.pi * g((i - nt) / nb)
        c, s = math.cos(t), math.sin(t)
        if s >= 0:
            x = hw * math.copysign(abs(c) ** (2 / pt), c)
            z = EQ + crown * abs(s) ** (2 / pt)
        else:
            x = hw * math.copysign(abs(c) ** (2 / pb), c)
            z = EQ - belly * abs(s) ** (2 / pb)
        pts.append((xc + x, z))
    return pts, (xc, EQ)


# --- geometry helpers (sprite px: x = col - AXIS, y = row, z up) -------------------------------------

def loft_stations(P, stations, mat_of_y, n=40, mat_of_yi=None):
    """stations: [(y, pts)] all with n points; closed tube, capped. `mat_of_yi(y, i)` (optional)
    picks the material per face (i = the section segment)."""
    rings = []
    for y, pts, centre in stations:
        rings.append(([P.v((x, y, z)) for x, z in pts], (centre[0], y, centre[1])))
    for (r0, c0), (r1, c1), (y0, *_), (y1, *_) in zip(rings, rings[1:], stations, stations[1:]):
        m = mat_of_y((y0 + y1) / 2)
        for i in range(n):
            j = (i + 1) % n
            mi = mat_of_yi((y0 + y1) / 2, i) if mat_of_yi else m
            P.f((r0[i], r0[j], r1[j], r1[i]), mi, away=c0)
    P.f(rings[0][0], mat_of_y(stations[0][0]), out=(0, -1, 0))
    P.f(rings[-1][0], mat_of_y(stations[-1][0]), out=(0, 1, 0))


def miter(poly):
    """Outward unit-ish miter normals of a closed 2D polygon (either winding)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) / 2
    sgn = 1 if area > 0 else -1
    segs = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        segs.append((sgn * dy / ln, -sgn * dx / ln))
    out = []
    for i in range(n):
        ax, ay = segs[i - 1]
        bx, by = segs[i]
        sx, sy = ax + bx, ay + by
        ln = math.hypot(sx, sy) or 1e-9
        ux, uy = sx / ln, sy / ln
        cos_half = max(0.4, ux * bx + uy * by)
        out.append((ux / cos_half, uy / cos_half))
    return out


def pillow(P, poly, zbot, ztop, bevel, mat, nb=3, mat_of_face=None):
    """A slab on polygon `poly` from zbot up to ztop(x, y) with a rounded top edge of radius `bevel`."""
    nrm = miter(poly)
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    rings = [[P.v((x, y, zbot)) for x, y in poly]]
    rings.append([P.v((x, y, ztop(x, y) - bevel)) for x, y in poly])
    for k in range(1, nb + 1):
        a = k / nb * math.pi / 2
        d = bevel * (1 - math.cos(a))
        ring = []
        for (x, y), (nx, ny) in zip(poly, nrm):
            xi, yi = x - nx * d, y - ny * d
            ring.append(P.v((xi, yi, ztop(x, y) - bevel + bevel * math.sin(a))))
        rings.append(ring)
    n = len(poly)
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            nx, ny = (nrm[i][0] + nrm[j][0]) / 2, (nrm[i][1] + nrm[j][1]) / 2
            up = 0.0 if k == 0 else math.sin((k - 0.5) / nb * math.pi / 2) * 2
            m = mat
            if mat_of_face:
                m = mat_of_face((poly[i][0] + poly[j][0]) / 2, (poly[i][1] + poly[j][1]) / 2, nx, ny, up)
            P.f((a[i], a[j], b[j], b[i]), m, out=(nx, ny, up))
    m = mat_of_face(cx, cy, 0, 0, 9) if mat_of_face else mat
    P.f(rings[-1], m, out=(0, 0, 1))
    P.f(list(reversed(rings[0])), mat, out=(0, 0, -1))


def tube(P, pts, sides, mat, cap=True):
    """A tube through [(x, y, z, r)] (r may be 0 for a point end)."""
    rings = []
    for i, (x, y, z, r) in enumerate(pts):
        p = Vector((x, y, z))
        a = Vector(pts[max(i - 1, 0)][:3])
        b = Vector(pts[min(i + 1, len(pts) - 1)][:3])
        t = (b - a).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized()
        w = u.cross(t).normalized()
        ring = [P.v(tuple(p + (u * math.cos(2 * math.pi * k / sides) + w * math.sin(2 * math.pi * k / sides)) * r))
                for k in range(sides)]
        rings.append((ring, tuple(p)))
    for (r0, c0), (r1, _) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            P.f((r0[k], r0[j], r1[j], r1[k]), mat, away=c0)
    if cap:
        t0 = Vector(pts[0][:3]) - Vector(pts[1][:3])
        t1 = Vector(pts[-1][:3]) - Vector(pts[-2][:3])
        P.f(rings[0][0], mat, out=tuple(t0))
        P.f(rings[-1][0], mat, out=tuple(t1))


def dome(P, cx, cy, rx, ry, z0, h, mat, seg=24, rings=5, p=2.0, zf=None, bottom=True):
    """An elliptic cap on footprint (cx, cy, rx, ry) rising h above z0 (or above zf(x, y))."""
    base = (lambda x, y: z0) if zf is None else zf
    rr = []
    for k in range(rings):
        t = k / rings
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            x = cx + rx * math.copysign(abs(ca) ** (2 / p), ca) * math.cos(t * math.pi / 2)
            y = cy + ry * math.copysign(abs(sa) ** (2 / p), sa) * math.cos(t * math.pi / 2)
            ring.append(P.v((x, y, base(x, y) + h * math.sin(t * math.pi / 2))))
        rr.append(ring)
    top = P.v((cx, cy, base(cx, cy) + h))
    c = (cx, cy, base(cx, cy))
    for a, b in zip(rr, rr[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            P.f((a[i], a[j], b[j], b[i]), mat, away=c)
    last = rr[-1]
    for i in range(seg):
        P.f((last[i], last[(i + 1) % seg], top), mat, away=c)
    if bottom:
        bot = [P.v((v.co.x, v.co.y, v.co.z - 1.5)) for v in rr[0]]
        for i in range(seg):
            j = (i + 1) % seg
            P.f((bot[i], bot[j], rr[0][j], rr[0][i]), mat, away=(cx, cy, base(cx, cy) + h / 2))
        P.f(list(reversed(bot)), mat, out=(0, 0, -1))


def ring_at(P, cx, cy, z, r_out, r_in, h, tilt, mat, sides=24):
    """A flat ring (collar) of height h, centred at (cx, cy, z), its axis tilted `tilt` rad toward +y."""
    ax = Vector((0, math.sin(tilt), math.cos(tilt)))
    u = Vector((1, 0, 0))
    w = ax.cross(u)
    c = Vector((cx, cy, z))
    loops = []
    for r, dz in ((r_out, 0), (r_out, h), (r_in, h), (r_in, 0)):
        loops.append([P.v(tuple(c + ax * dz + (u * math.cos(2 * math.pi * k / sides) + w * math.sin(2 * math.pi * k / sides)) * r))
                      for k in range(sides)])
    for li in range(4):
        a, b = loops[li], loops[(li + 1) % 4]
        for k in range(sides):
            j = (k + 1) % sides
            mid = (Vector(a[k].co) + Vector(b[j].co)) / 2
            radial = mid - c - ax * (mid - c).dot(ax)
            if li == 0:
                o = radial
            elif li == 1:
                o = ax
            elif li == 2:
                o = -radial
            else:
                o = -ax
            P.f((a[k], a[j], b[j], b[k]), mat, out=tuple(o))


# --- the build ---------------------------------------------------------------------------------------

HULL_N = 36  # hull section points
HULL_DENSE = 0.45  # their packing toward the equator
SHOULDER_DP = 0.45  # the superellipse power taken off at the shoulder step (a rounder, thinner rim)

def build_body():
    """Pod hull, the two south lobes and the shoulder pads (one Part, sprite px)."""
    P = T.Part("body", smooth_angle=40)
    # Main hull: a station per row, rows 3..80, closing at row 82.
    # a station per row through the shoulder step (rows 4-16), every 1.5 rows down the smoothed flanks
    ys = [2.7, 3.0, 3.5] + [r + 0.5 for r in range(4, 17)] + T.frange(17.5, 76.5, 1.5) + [77.5, 78.5, 79.4, 80.2, 80.7]
    st = []
    for y in ys:
        if y <= 3.0:
            hw = 8.0 + (y - 2.7) / 0.3 * 4.0
        elif y >= 77.5:
            hw = hw_at(77.0) * (1 - ((y - 77.0) / 5.4) ** 2) + 2.0
        else:
            hw = hw_at(y)
        crown = CROWN(y) if y < 77.5 else CROWN(y) * (1 - 0.6 * ((y - 77.0) / 5.0) ** 2)
        belly = BELLYF(y) if y < 77.5 else BELLYF(y) * (1 - 0.5 * ((y - 77.0) / 5.0) ** 2)
        # rows 72+: the pod's south end sinks inside the two lobes, which carry the side profile from
        # row 77 (no end wall of the pod showing between them in the side view)
        k = min(1.0, max(0.0, (y - 72.0) / 8.7))
        k = k * k * (3 - 2 * k)
        hw *= 1 - 0.3 * k
        crown *= 1 - 0.45 * k
        belly *= 1 - 0.45 * k
        # the shoulder step (rows 11-14, the ear tips): there the half width grows 9 px in four rows, so
        # the rim is a little thinner (a lower superellipse power), easing back by row 18
        sw = shoulder_thin(y)
        pts, c = section(hw, crown, belly, n=HULL_N, dense=HULL_DENSE, pt=2.3 - SHOULDER_DP * sw,
                         pb=2.0 - SHOULDER_DP * 0.6 * sw)
        st.append((y, pts, c))
    # The lighter north cap (rows < 19) only on the top, the flanks one colour all the way along (a
    # colour change down the steep side read as a wall in the side view).
    nt = (2 * HULL_N) // 3
    top = {i for i in range(nt) if math.pi / 6 < math.pi * ((i + 0.5) / nt - HULL_DENSE * math.sin(
        2 * math.pi * (i + 0.5) / nt) / (2 * math.pi)) < 5 * math.pi / 6}
    loft_stations(P, st, lambda y: SHELL, n=HULL_N,
                  mat_of_yi=lambda y, i: SHELL_HI if y < 19 and i in top else SHELL)
    H = P
    P = T.Part("lobes", smooth_angle=40)

    # South lobes (the 267 row), mirrored: from row 64 to the V tips at row 102.
    for side in (-1, 1):
        st = []
        ys = T.frange(64.0, 80.5, 1.5) + [r + 0.5 for r in range(81, 102)] + [102.2]
        for y in ys:
            r = int(math.floor(y))
            # Junction rows 64-77: the lobe starts inside the pod's section (narrower, lower crown and
            # belly) and swells out of the shell, so it grows out of the pod instead of a flat end wall.
            t = min(1.0, max(0.0, (y - 64.0) / 13.0))
            t = t * t * (3 - 2 * t)
            if y < 81:
                xo, xi = -hw_at(y) * (0.70 + 0.30 * t), -0.7 - 6.0 * (1 - t)
            else:
                xo, xi = LOBE_EDGES[min(r, 101)]
                if y > 101.5:
                    xo, xi = -11.6, -8.6
            w = (xi - xo) / 2
            xc = (xo + xi) / 2
            crown = CROWN(y) * (0.97 if y < 81 else 1.0) * (0.55 + 0.45 * t)
            belly = BELLYF(y) * (1 - 0.5 * min(1.0, max(0.0, (y - 72) / 14))) * (0.45 + 0.55 * t)
            pts, c = section(w, crown, belly, n=24, pt=2.2, xc=xc)
            if side > 0:
                pts = [(-x, z) for x, z in reversed(pts)]
                c = (-c[0], c[1])
            st.append((y, pts, c))
        loft_stations(P, st, lambda y: SHELL, n=24)
    L = P
    P = T.Part("pads", smooth_angle=40)

    # Shoulder pads under the posts (rows 16-34): raised humps, kept >= 2.5 px inside the rim (a pad
    # reaching the rim hung its base and skirt down the steep flank as a light vertical sliver).
    for side in (-1, 1):
        dome(P, side * 37.4, 25.0, 4.6, 9.0, 0, 3.0, SHELL, seg=20, rings=4, p=2.4,
             zf=lambda x, y: surface_guess(x, y) - 1.0)
    return H, L, P


def shoulder_thin(y):
    """0..1: how much the hull's rim is thinned at the shoulder step (rows 11-18)."""
    sw = min(1.0, max(0.0, (y - 11.0) / 2.5)) if y < 13.5 else (1.0 if y <= 14.5 else max(0.0, 1 - (y - 14.5) / 3.5))
    return sw * sw * (3 - 2 * sw)


def surface_guess(x, y):
    """Analytic top of the main hull (before the BVH exists)."""
    hw = hw_at(max(3.0, min(y, 77.0)))
    u = min(abs(x) / max(hw, 1e-3), 1.0)
    pt = 2.3 - SHOULDER_DP * shoulder_thin(y)
    return EQ + CROWN(y) * max(0.0, 1 - u ** pt) ** (1 / pt)


class Surface:
    def __init__(self, parts):
        bm = bmesh.new()
        for P in parts:
            tmp = bmesh.new()
            me = bpy.data.meshes.new("tmp")
            P.bm.to_mesh(me)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
            tmp.free()
        self.tree = BVHTree.FromBMesh(bm)
        bm.free()

    def hit(self, x, y):
        h = self.tree.ray_cast(Vector((x, y, 200.0)), Vector((0, 0, -1)), 400.0)
        if h[0] is None:
            return None
        nrm = h[1] if h[1].z > 0 else -h[1]
        return h[0], nrm.normalized()

    def z(self, x, y, default=None):
        hit = self.tree.ray_cast(Vector((x, y, 200.0)), Vector((0, 0, -1)), 400.0)
        if hit[0] is None:
            return default if default is not None else EQ
        return hit[0].z


# Ribs: the sprite's green runs between dark seams, traced into columns (per band of rows, the columns
# that are mostly green, chained down the body by overlap) and laid on the dome as constant half-round
# strips with chamfered ends.
W = 96
RIB_BANDS = [(3, 13), (13, 21), (21, 28), (28, 37), (37, 46), (46, 57), (57, 64), (64, 70), (70, 77),
             (77, 84), (84, 90), (90, 96), (96, 102)]
GLOW_RIB_COLS = ((31, 37), (59, 66))  # the stripe ribs (lit on the newshj-231 / 233 -f2 frame)
RIB_NZ = 0.55  # ribs stay where the shell's normal z under both their edges is at least this


def in_eye(c, r):
    return 27 <= r <= 47 and 31 <= c <= 65


def rib_green(v):
    return 35 <= v <= 47 or 192 <= v <= 207


def band_runs(r0, r1):
    frac = []
    for c in range(W):
        vs = [GRID[r][c] for r in range(r0, r1) if GRID[r][c] >= 0 and not in_eye(c, r)]
        frac.append(sum(rib_green(v) for v in vs) / len(vs) if len(vs) >= max(2, (r1 - r0) // 2) else 0)
    runs, s = [], None
    for c in range(W + 1):
        ok = c < W and frac[c] >= 0.5
        if ok and s is None:
            s = c
        elif not ok and s is not None:
            if c - s >= 2:
                runs.append((s, c))
            s = None
    return runs


def split_wide(runs, w=4.6):
    out = []
    for a_, b_ in runs:
        n = max(1, int(round((b_ - a_) / w)))
        out += [(a_ + (b_ - a_) * i / n, a_ + (b_ - a_) * (i + 1) / n) for i in range(n)]
    return out


def row_clip(r, a_, b_):
    """Clip a rib's (a, b) column edges at pixel row r to the sprite's inner mask there."""
    best = None
    for s, e in inner_runs(r):
        aa, bb = max(a_, s + 0.35), min(b_, e + 1 - 0.35)
        if bb - aa > 0.8 and (best is None or bb - aa > best[1] - best[0]):
            best = (aa, bb)
    return best


def rib_chains():
    chains, prev = [], []
    for r0, r1 in RIB_BANDS:
        cur = []
        for a_, b_ in split_wide(band_runs(r0, r1)):
            best, ov = None, 0
            for ch in prev:
                _, _, pa, pb = ch[-1]
                o = min(b_, pb) - max(a_, pa)
                if o > ov and o >= 0.5 * min(b_ - a_, pb - pa):
                    best, ov = ch, o
            if best is not None and best not in cur:
                best.append((r0, r1, a_, b_))
                cur.append(best)
            else:
                ch = [(r0, r1, a_, b_)]
                chains.append(ch)
                cur.append(ch)
        prev = cur
    return chains


def rib_rows(ch):
    rows = []
    for r0, r1, a_, b_ in ch:
        for r in range(r0, r1):
            mid = int((a_ + b_) / 2)
            if any(rib_green(GRID[r][c]) for c in range(int(a_), int(math.ceil(b_)))) and not in_eye(mid, r):
                cl = row_clip(r, a_, b_)
                if cl:
                    rows.append((r, *cl))
    return rows


def rib_columns():
    """The traced chains as straight columns: each run of rows (split where the sprite's column breaks
    for more than 4 rows) becomes one straight centreline (least squares over its rows) with one
    constant width (the median); runs shorter than 6 rows are dropped (stubs read as dribbles)."""
    cols = []
    for ch in rib_chains():
        rows = rib_rows(ch)
        if not rows:
            continue
        groups, cur = [], [rows[0]]
        for row in rows[1:]:
            if row[0] - cur[-1][0] > 4:
                groups.append(cur)
                cur = [row]
            else:
                cur.append(row)
        groups.append(cur)
        for grp in groups:
            if grp[-1][0] - grp[0][0] + 1 < 6 or len(grp) < 5:
                continue
            ys = [r + 0.5 for r, _, _ in grp]
            cs = [(a_ + b_) / 2 for _, a_, b_ in grp]
            ws = sorted(b_ - a_ for _, a_, b_ in grp)
            ym, cm = sum(ys) / len(ys), sum(cs) / len(cs)
            sxx = sum((y - ym) ** 2 for y in ys) or 1e-9
            k = sum((y - ym) * (c - cm) for y, c in zip(ys, cs)) / sxx
            k = max(-0.06, min(0.06, k))
            w = min(max(ws[len(ws) // 2], 1.8), 4.6)
            v = sorted(GRID[r][c] for r, a_, bb in grp for c in range(int(a_), int(math.ceil(bb))) if 35 <= GRID[r][c] <= 47)
            if not v:
                continue
            q = int(len(v) * 0.15)
            t = v[q:len(v) - q] or v
            idx = min(max(t[len(t) // 2], 36), 40)
            cols.append((grp[0][0] + 0.2, grp[-1][0] + 0.8, cm, k, ym, w / 2 - 0.25, idx))
    return cols


def build_ribs(S):
    """Ribs: straight columns of a constant half-round section (4 arc segments) laid on the shell
    along its normal, the ends chamfered; clipped to the inner mask where the body narrows."""
    P = T.Part("ribs", smooth_angle=50)
    n = 0
    ARC = 4
    for y0, y1, cm, k, ym, hw0, idx in rib_columns():
        base = M.get(f"rib{idx}", idx, 0.15, 0.45)
        mid = cm + k * ((y0 + y1) / 2 - ym)
        glow = any(lo <= mid <= hi for lo, hi in GLOW_RIB_COLS) and y1 >= 60
        # Sample every half row: the rib stands where it fits the inner mask, both its edges are on
        # the shell and the shell there is not the steep flank (both edges' normal z >= RIB_NZ), so it
        # ends at a smooth normal-z contour, not at a raggedly clipped station.
        samples = []
        for y in T.frange(y0, y1, 0.5):
            c = cm + k * (y - ym)
            cl = row_clip(min(int(y), 111), c - hw0, c + hw0)
            ok = cl is not None and cl[1] - cl[0] >= 1.2
            if ok:
                hs = [S.hit(x - AXIS, y) for x in (cl[0] + 0.15, (cl[0] + cl[1]) / 2, cl[1] - 0.15)]
                ok = all(h is not None and h[1].z >= RIB_NZ for h in hs)
            samples.append((y, ((cl[0] + cl[1]) / 2 - AXIS, (cl[1] - cl[0]) / 2) if ok else None))
        segs, cur = [], []
        for y, v in samples + [(None, None)]:
            if v is None:
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append((y, *v))
        for st in segs:
            # fragments shorter than 6 rows after the clip read as dribbles: dropped
            if st[-1][0] - st[0][0] < 6.0:
                continue
            # centre and half width smoothed along the run (no per-row steps from the mask clip)
            cs, hs_ = [s[1] for s in st], [s[2] for s in st]
            for _ in range(4):
                cs = [sum(cs[max(0, i - 4):i + 5]) / len(cs[max(0, i - 4):i + 5]) for i in range(len(cs))]
                hs_ = [sum(hs_[max(0, i - 4):i + 5]) / len(hs_[max(0, i - 4):i + 5]) for i in range(len(hs_))]
            ya, yb = st[0][0], st[-1][0]
            fc = T.pchip([s[0] for s in st], cs)
            fh = T.pchip([s[0] for s in st], hs_)
            nmid = max(2, int(round((yb - ya - 1.2) / 1.2)))
            mids = [ya + 0.6 + (yb - ya - 1.2) * i / nmid for i in range(nmid + 1)]
            # chamfered caps: a low narrow station at each end, inside the run (on valid shell)
            seq = [(ya, fc(ya), fh(ya) * 0.8, 0.3)] + [(y, fc(y), fh(y), 1.0) for y in mids] \
                + [(yb, fc(yb), fh(yb) * 0.8, 0.3)]
            # the offset direction: the shell normal averaged across the rib and along it (the
            # faceted shell's face normals would make the strip wobble)
            nr = []
            for y, cc, hw, e in seq:
                acc = Vector((0, 0, 0))
                for x in (cc - hw, cc, cc + hw):
                    h = S.hit(x, y)
                    if h:
                        acc += h[1]
                nr.append(acc.normalized() if acc.length > 0 else Vector((0, 0, 1)))
            nr = [(nr[max(0, i - 1)] + 2 * nr[i] + nr[min(len(nr) - 1, i + 1)]).normalized() for i in range(len(nr))]
            rings = []
            for (y, cc, hw, e), nrm in zip(seq, nr):
                bump = min(max(0.45 * hw, 0.7), 1.2) * e
                ring = []
                for i in range(ARC + 1):
                    ang = math.pi * i / ARC
                    x = cc + hw * math.cos(ang)
                    h = S.hit(x, y)
                    p0 = h[0] if h else Vector((x, y, EQ))
                    ring.append(P.v(tuple(p0 + nrm * (bump * math.sin(ang) ** 0.8 - 0.05))))
                for sgn in (1, -1):
                    x = cc + sgn * hw * 0.8
                    h = S.hit(x, y)
                    p0 = h[0] if h else Vector((x, y, EQ))
                    ring.append(P.v(tuple(p0 - nrm * 0.9)))
                rings.append(ring)
            mats = []
            for kk in range(len(seq) - 1):
                rr = (seq[kk][0] + seq[kk + 1][0]) / 2
                if glow and rr >= 56:
                    mats.append(M.get("stripe", idx, 0.15, 0.45))
                else:
                    mats.append(base)
            m_ = len(rings[0])
            for kk, (a_, b_) in enumerate(zip(rings, rings[1:])):
                cen = Vector((0, 0, 0))
                for vv in a_ + b_:
                    cen += vv.co
                cen /= len(a_ + b_)
                for i in range(m_):
                    j = (i + 1) % m_
                    P.f((a_[i], a_[j], b_[j], b_[i]), mats[kk], away=tuple(cen))
            P.f(rings[0], mats[0], out=(0, -1, 0))
            P.f(rings[-1], mats[-1], out=(0, 1, 0))
            n += 1
    print(f"{NAME}: {n} ribs")
    return P


def lens_z(x, y):
    """Height of the eye lens surface."""
    u = ((x - LENS[0]) / LENS[2]) ** 2 + ((y - LENS[1]) / LENS[3]) ** 2
    return LENS[4] + LENS[5] * math.sqrt(max(1 - u, 0))


LENS = (-1.0, 37.4, 14.6, 9.4, 24.4, 4.0)  # cx, cy, rx, ry, base z, height


BAR_PATH = [(36.4, 23.2), (33.2, 21.2), (28.5, 20.3), (22.5, 20.1), (18.2, 20.6), (15.0, 22.6)]


def band(P, path, hw, th, mat_top, mat_side, zs, step=0.6):
    """A flat band (chamfered rectangle section, half width hw, thickness th) along a pchip curve
    through `path` (x, y), lying on the surface zs (smoothed along the path, bottom sunk 0.8).
    Returns a z-of-top lookup by nearest sample."""
    d = [0.0]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        d.append(d[-1] + math.hypot(x1 - x0, y1 - y0))
    fx, fy = T.pchip(d, [p[0] for p in path]), T.pchip(d, [p[1] for p in path])
    ts = T.frange(0, d[-1], step)
    pts = [(fx(t), fy(t)) for t in ts]
    nrm = []
    for i in range(len(pts)):
        (xa, ya), (xb, yb) = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        ln = math.hypot(xb - xa, yb - ya) or 1e-9
        nrm.append((-(yb - ya) / ln, (xb - xa) / ln))
    zr = [max(zs(x + nx * u, y + ny * u) for u in (-hw, 0, hw)) for (x, y), (nx, ny) in zip(pts, nrm)]
    zb = [sum(zr[max(0, i - 3):i + 4]) / len(zr[max(0, i - 3):i + 4]) for i in range(len(zr))]
    zb = [max(a_, b_ - 0.3) for a_, b_ in zip(zb, zr)]
    ch = 0.45
    sec = [(-hw, -0.8, mat_side), (-hw, th - ch, mat_top), (-hw + ch, th, mat_top), (hw - ch, th, mat_top),
           (hw, th - ch, mat_side), (hw, -0.8, mat_side)]
    rings = []
    for (x, y), (nx, ny), z in zip(pts, nrm, zb):
        rings.append([P.v((x + nx * u, y + ny * u, z + v)) for u, v, _ in sec])
    m = len(sec)
    for i in range(len(rings) - 1):
        a_, b_ = rings[i], rings[i + 1]
        cx, cy = pts[i]
        for j in range(m):
            k = (j + 1) % m
            mt = sec[j][2] if j != m - 1 else mat_side
            if j in (1, 2):
                mt = mat_top
            P.f((a_[j], a_[k], b_[k], b_[j]), mt, away=(cx, cy, zb[i] + th / 2))
    (x0, y0), (x1, y1) = pts[0], pts[1]
    P.f(rings[0], mat_side, out=(x0 - x1, y0 - y1, 0))
    (x0, y0), (x1, y1) = pts[-1], pts[-2]
    P.f(rings[-1], mat_side, out=(x0 - x1, y0 - y1, 0))

    def ztop(x, y):
        i = min(range(len(pts)), key=lambda i: (pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2)
        return zb[i] + th
    return ztop


def poly_span(poly, y):
    """(x min, x max) where the horizontal line at y crosses a y-monotone polygon."""
    xs = []
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
            xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return (min(xs), max(xs)) if xs else None


POD_INSET = T.pchip([36.0, 45.0, 53.0, 58.0, 62.0, 66.0], [3.3, 3.0, 2.2, 1.6, 1.3, 1.2])


def pod_loft(P, pod, side, S, H=3.0, R=1.5):
    """A flank pod as a loft along y that lies on the hull: each section spans the footprint's width,
    its top H above the shell with rounded (radius R) long edges, a short wall into the shell; the
    ends ease down, the south part (rows 53.5+, the sprite's lit chamfer) slopes down, and a raised
    strap crosses it at rows 43.6-45. One clean surface on the shell instead of a flat-topped slab
    standing out of the flank."""
    y0 = min(p[1] for p in pod) + 0.05
    y1 = max(p[1] for p in pod) - 0.05
    ys = sorted(set(T.frange(y0, y1, 1.5) + [y0 + 0.4, y0 + 0.9, y1 - 0.4, y1 - 0.9, 43.4, 43.6, 45.0, 45.2, 53.5]))
    ys = [y for y in ys if y0 <= y <= y1]
    us = [0.0, 0.04, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.96, 1.0]
    # The analytic hull surface, not ray casts on the faceted loft: near the rim a facet's z changes
    # fast with x, so ray-cast heights made the pod's walls (and its seam on the shell) jagged.
    zs = surface_guess
    st, spans = [], []
    for y in ys:
        sp = poly_span(pod, y)
        if sp is None:
            continue
        a_, b_ = sp
        # the outer edge a constant inset from the hull's (smoothed) rim, not the traced polygon's
        # steps, so its line down the steep flank is one clean curve
        a_ = max(a_, -(hw_at(y) - POD_INSET(y)))
        if b_ - a_ < 0.6:
            mid = (a_ + b_) / 2
            a_, b_ = mid - 0.3, mid + 0.3
        e = min(y - y0, y1 - y)
        hf = 0.45 + 0.55 * math.sqrt(min(1.0, e / 1.6))
        # the lit south part slopes down to 0.65 of the height at the end (a straight 0.12 / row
        # slope sank the end below the shell, leaving a ragged sliver at the south seam)
        h = H * hf * (1 - 0.35 * min(1.0, max(0.0, (y - 53.5) / 12.0)))
        if 43.6 <= y <= 45.0:
            h += 0.45
        w = b_ - a_
        top = []
        for u in us:
            x = a_ + w * u
            d = min(u, 1 - u) * w
            q = min(d / R, 1.0)
            f = 0.35 + 0.65 * math.sqrt(max(0.0, 1 - (1 - q) ** 2))
            top.append((x, zs(x, y) + h * f))
        pts = [(a_, zs(a_, y) - 1.0)] + top + [(b_, zs(b_, y) - 1.0)]
        bot = [(a_ + w * u, zs(a_ + w * u, y) - 1.6) for u in (0.66, 0.33)]
        spans.append((y, a_, b_))
        pts = pts + bot
        if side > 0:
            pts = [(-x, z) for x, z in reversed(pts)]
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        st.append((y, pts, (cx, cz)))

    def mat(y):
        if 43.6 <= y <= 45.0:
            return POD_LIT
        return POD_LIT if y > 53.5 else POD
    loft_stations(P, st, mat, n=len(st[0][1]))
    pod_bead(P, spans, side)


def pod_bead(P, spans, side, r=0.55):
    """A round bead (a weld / gasket) all round the pod's foot on the shell: the seam between the pod
    and the hull is one clean smoothed line, not the raw intersection of two surfaces meeting at a
    shallow angle on the steep flank. `spans`: [(y, outer x, inner x)] of the pod's sections (left
    side); the loop runs down the outer edge, across the south end, up the inner edge and across the
    north end, then is smoothed (closed moving average) and laid on the analytic shell."""
    ys = [s[0] for s in spans]
    y0, y1 = ys[0], ys[-1]
    loop = [(a_ + r * 0.9, y) for y, a_, _ in spans]
    a1, b1 = spans[-1][1] + r * 0.9, spans[-1][2] - r * 0.9
    loop += [(a1 + (b1 - a1) * k / 4, y1 - r * 0.6) for k in range(1, 4)]
    loop += [(b_ - r * 0.9, y) for y, _, b_ in reversed(spans)]
    a0, b0 = spans[0][1] + r * 0.9, spans[0][2] - r * 0.9
    loop += [(b0 + (a0 - b0) * k / 4, y0 + r * 0.6) for k in range(1, 4)]
    # resample by arc length (0.5 px), then smooth (closed [1 2 3 2 1] / 9, three passes)
    d = [0.0]
    for (xa, ya), (xb, yb) in zip(loop, loop[1:] + loop[:1]):
        d.append(d[-1] + math.hypot(xb - xa, yb - ya))
    n = max(24, int(d[-1] / 0.5))
    pts = []
    j = 0
    for k in range(n):
        t = d[-1] * k / n
        while d[j + 1] < t:
            j += 1
        (xa, ya), (xb, yb) = loop[j], loop[(j + 1) % len(loop)]
        f = (t - d[j]) / max(d[j + 1] - d[j], 1e-9)
        pts.append((xa + (xb - xa) * f, ya + (yb - ya) * f))
    for _ in range(3):
        pts = [tuple(sum(pts[(i + o) % n][c] * w for o, w in ((-2, 1), (-1, 2), (0, 3), (1, 2), (2, 1))) / 9
                     for c in (0, 1)) for i in range(n)]
    path = [(x if side < 0 else -x, y, surface_guess(x, y) + 0.1, r) for x, y in pts]
    path.append(path[0])
    tube(P, path, 8, BAR, cap=False)


# The 267 row's light strips (sprite rows 84-91, indices 193-197 in a dark pure green): one continuous
# strip per sprite run, laid on the ribs: a short bar on the left lobe, a U on the right one.
GLOW_STRIPS = [([(-16.2, 84.5), (-14.6, 84.5), (-12.9, 84.5)], 194, 0.25),
               ([(13.0, 84.4), (13.0, 87.5), (13.1, 90.2), (14.5, 91.4), (15.9, 90.2), (16.0, 87.5), (16.0, 84.4)],
                195, 0.35)]


def build_glow(S2):
    P = T.Part("glow", smooth_angle=40)
    for path, pal, em in GLOW_STRIPS:
        m = M.get(f"glow{pal}", pal, 0.1, 0.35, em)
        band(P, path, 0.5, 0.3, m, m, S2.z, step=0.4)
    return P


def build_machinery(S):
    P = T.Part("machinery", smooth_angle=32)
    H = T.Part("housing", smooth_angle=32)  # the parts the slits cut through
    zs = S.z

    # Posts on the shoulders: grey pipes running north-south, a bright collar, a foot on the bar.
    for side in (-1, 1):
        x = side * 35.5
        zp = max(zs(x, y) for y in (14.0, 18.0, 22.0, 26.0)) + 1.2
        pts = []
        for y in (12.9, 13.6, 16.0, 20.0, 24.0, 26.6, 27.3):
            r = 2.0 if 13.4 < y < 26.8 else 1.3
            pts.append((x, y, zp, r))
        tube(P, pts, 10, POST)
        tube(P, [(x, 15.0, zp, 0.0), (x, 15.2, zp, 2.6), (x, 18.2, zp, 2.6), (x, 18.4, zp, 0.0)], 12, BOLT, cap=False)
        # struts down to the shell under the pipe
        for y in (15.0, 24.0):
            T.hull(P, T.cbox(x - 1.2, x + 1.2, y, y + 1.6, zs(x, y + 0.8) - 1.0, zp, 0.3), BAR)
        # Cross bar: a flat grey band 3.2 px wide (sprite rows 19-21) arching from the post up over the
        # shoulder lobe and down round the housing's top lobe into the housing.
        path = [(side * x, y) for x, y in BAR_PATH]
        bar_z = band(P, path, 1.6, 1.5, POST, BAR, zs)
        # Bolts on the bar (the sprite's bright pixels at cols 18 and 32).
        for bx, by in ((30.0, 20.4), (16.4, 20.2)):
            dome(P, side * bx, by, 1.3, 1.3, bar_z(side * bx, by) - 0.3, 0.8, BOLT, seg=12, rings=3)

    # Eye housing: a dark rounded slab on a traced footprint (the slits are cut later).
    sock = [(-18.3, 20.0), (-12.0, 18.5), (0.5, 18.0), (12.0, 18.5), (15.0, 20.5), (15.6, 27.0), (16.3, 33.0),
            (16.8, 39.0), (16.2, 44.0), (13.5, 47.2), (6.0, 47.0), (0.5, 46.6), (-6.0, 47.0), (-14.0, 47.4),
            (-18.2, 45.5), (-18.3, 38.0), (-18.3, 27.0)]
    ztop_s = 25.0
    pillow(H, sock, 6.0, lambda x, y: ztop_s + 0.6 * math.exp(-((y - 22) / 6) ** 2), 2.2, SOCKET, nb=3)
    # Brows over the housing's top corners.
    for cx, rx in ((-13.6, 6.0), (9.4, 5.8)):
        dome(H, cx, 24.0, rx, 4.6, ztop_s - 0.8, 2.2, BROW, seg=20, rings=4, p=2.4)
    # The eye lens in a bezel.
    cx, cy, rx, ry, z0, h = LENS
    bez = []
    for i in range(32):
        a = 2 * math.pi * i / 32
        bez.append((cx + (rx + 1.2) * math.cos(a), cy + (ry + 1.1) * math.sin(a)))
    pillow(H, bez, z0 - 1.0, lambda x, y: z0 + 0.9, 0.6, RING, nb=2)
    dome(H, cx, cy, rx, ry, z0, h, EYE, seg=36, rings=6, p=2.2)

    # Spine: segmented vertebrae down the eye from the top rim to the block.
    sx = 0.5
    y = 16.6
    while y < 38.0:
        z = max(lens_z(sx, y + 0.8), ztop_s + 0.4) + 0.7
        hwid = 1.5 if y < 27 else 2.3
        T.hull(P, T.cbox(sx - hwid, sx + hwid, y, y + 1.7, z - 2.5, z + 1.0, 0.35), SPINE)
        T.hull(P, T.cbox(sx - hwid * 0.55, sx + hwid * 0.55, y + 0.25, y + 1.45, z + 0.8, z + 1.5, 0.2), SPINE_LT)
        y += 2.0
    # The block at the bottom of the eye and its side tabs.
    T.hull(P, T.cbox(-5.4, 5.0, 38.3, 46.4, ztop_s - 2, lens_z(0, 40) + 2.6, 0.7), SPINE)
    T.hull(P, T.cbox(-3.6, 3.2, 39.0, 41.6, lens_z(0, 40) + 2.2, lens_z(0, 40) + 3.2, 0.35), SPINE_LT)
    for tx in (-7.4, 4.6):
        T.hull(P, T.cbox(tx, tx + 2.8, 41.5, 46.6, ztop_s - 2, ztop_s + 1.4, 0.4), SPINE)

    # Mechanism under the eye: a dark bracket with two light shoulders in a V.
    mech = [(-8.2, 47.3), (5.4, 47.3), (7.6, 49.6), (6.8, 55.8), (-7.8, 55.8), (-9.8, 49.6)]
    zm = lambda x, y: zs(x, y, EQ) + 2.2  # noqa: E731
    zm_top = max(zm(-8, 48), zm(6, 48), zm(0, 52))
    pillow(H, mech, 6.0, lambda x, y: zm_top, 1.0, MECH, nb=2)
    T.hull(H, [(-7.6, 48.6, zm_top - 1), (-2.4, 50.0, zm_top - 1), (-2.4, 55.0, zm_top - 1), (-6.6, 55.0, zm_top - 1),
               (-7.2, 48.9, zm_top + 1.6), (-2.9, 50.4, zm_top + 2.2), (-2.9, 54.4, zm_top + 2.0), (-6.2, 54.4, zm_top + 1.4)],
           MECH_LT)
    T.hull(H, [(6.2, 48.6, zm_top - 1), (1.0, 50.0, zm_top - 1), (1.0, 55.0, zm_top - 1), (5.4, 55.0, zm_top - 1),
               (5.8, 48.9, zm_top + 1.6), (1.5, 50.4, zm_top + 2.2), (1.5, 54.4, zm_top + 2.0), (5.0, 54.4, zm_top + 1.4)],
           MECH_LT)

    # Barrel down to the muzzle housing.
    bx = -1.0
    zb = zm_top - 0.3
    tube(P, [(bx, 54.0, zb, 2.2), (bx, 57.0, zb - 0.3, 2.3), (bx, 57.6, zb - 0.35, 2.6), (bx, 59.0, zb - 0.5, 2.6),
             (bx, 59.6, zb - 0.55, 2.2), (bx, 68.5, zb - 1.6, 2.2)], 12, BARREL)

    # Muzzle housing: a square block with a tilted ring and bore facing forward and up.
    hz = max(zs(-11, 70, EQ), zs(10, 70, EQ), zs(0, 82, EQ)) + 2.0
    house = [(-11.4, 67.0), (10.4, 67.0), (11.4, 68.2), (11.4, 82.0), (10.0, 83.6), (-10.0, 83.6), (-11.4, 82.2),
             (-12.0, 68.2)]
    pillow(P, house, 6.0, lambda x, y: hz - 0.08 * (y - 67), 1.4, HOUSING, nb=3)
    rz = hz - 0.08 * (75.6 - 67)
    MUZZLE_Z[0] = rz
    ring_at(P, -0.6, 75.6, rz - 0.5, 6.9, 4.6, 2.0, 0.35, RING, sides=28)
    dome(P, -0.6, 75.6, 4.7, 4.5, rz - 0.4, 0.15, BORE, seg=20, rings=2)
    # Panel bolts at the housing corners.
    for x, y in ((-9.0, 69.4), (8.0, 69.4), (-9.0, 81.2), (8.0, 81.2)):
        dome(P, x, y, 0.9, 0.9, hz - 0.08 * (y - 67) - 0.2, 0.5, BOLT, seg=8, rings=2)

    # Flank pods: grey pods lying on the flanks, a lit sloping south end.
    pod = [(-41.5, 37.0), (-39.5, 35.6), (-32.5, 35.6), (-30.0, 37.4), (-29.1, 40.0), (-29.1, 54.0), (-27.4, 59.5),
           (-30.0, 65.3), (-35.0, 65.8), (-36.4, 63.6), (-36.6, 60.0), (-37.6, 58.0), (-39.9, 55.4), (-41.6, 53.4), (-42.4, 39.2)]
    for side in (-1, 1):
        pod_loft(P, pod, side, S)
    return P, H


def build_eye_parts():
    """Per-frame eye pieces in assembly coordinates: {name: Part}."""
    out = {}
    for name, scale in (("core", 1.0), ("core-small", 0.7)):
        P = T.Part(name, smooth_angle=60)
        for cx in (-8.6, 7.0):
            dome(P, cx, 35.2, 5.2 * scale, 5.6 * scale, 0, 0.35, 0, seg=20, rings=4, p=2.2,
                 zf=lambda x, y: lens_z(x, y) - 0.08, bottom=False)
        out[name] = P
    return out


def eye_pixels(step, indices, region):
    """[(assembly col, row, index)] of these palette indices on a step (161 frame, 163 frame)."""
    out = []
    for piece, frame in zip(("newshj-161", "newshj-163"), step):
        fr = next(f for f in SPR[piece]["frames"] if f["index"] == frame)
        c0, c1, r0, r1 = region[piece]
        oc, orow = CENTRE[piece][0] - 12, CENTRE[piece][1] - 14
        out += [(oc + c, orow + r, fr["pixels"][r][c]) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                if fr["pixels"][r][c] in indices]
    return out


def flecks(P, pixels, mat_of):
    for c, r, i in pixels:
        x, y = c + 0.5 - AXIS, r + 0.5
        dome(P, x, y, 0.55, 0.55, 0, 0.12, mat_of(i), seg=6, rings=1, p=4.0,
             zf=lambda x, y: lens_z(x, y) - 0.03, bottom=False)


# --- assembly, variants, export ------------------------------------------------------------------------

# The sprite's see-through slits as designed vents: smooth centrelines (sprite pixel col, row centres,
# traced from the sprite's hole pixels: inside the outline, neither inner nor free) with a constant width, so the cut has clean pchip edges instead of the
# pixel staircase. (col, row) points; width in px.
SLITS = [
    # left of the eye housing, the full height of it
    ([(29.3, 27.3), (29.5, 30.0), (29.4, 34.0), (29.7, 38.0), (30.4, 41.0), (30.5, 45.0), (30.5, 50.0),
      (30.5, 55.6)], 2.2),
    # under the housing: a U from the left slit round the mechanism's shoulder to the right
    ([(31.6, 47.8), (33.0, 49.0), (35.0, 50.5), (37.5, 51.2), (40.0, 51.0), (41.4, 49.8), (42.6, 47.6),
      (44.0, 46.7), (50.0, 46.5), (54.0, 46.6), (56.5, 47.6)], 2.2),
    # right of the housing: down its shoulder, then down its side and in under it
    ([(58.5, 29.0), (61.0, 31.0), (63.0, 33.0), (64.6, 34.8), (65.8, 37.0), (66.1, 40.0), (66.0, 43.0),
      (65.5, 45.5), (65.0, 48.0), (64.2, 50.5), (63.5, 52.0)], 2.2),
    # the gaps either side of the mechanism's two shoulder blocks
    ([(57.0, 49.2), (56.4, 51.5), (56.2, 56.2)], 1.4),
    ([(59.5, 51.0), (59.6, 56.0)], 1.5),
    ([(36.2, 52.0), (36.3, 55.5)], 1.4),
    ([(40.2, 52.0), (40.3, 55.5)], 1.4),
]


def slit_ribbons(step=0.9):
    """[(points [(x, y)], normals, half widths)] of each slit centreline, pchip by chord length, the
    ends rounded off."""
    out = []
    for ctrl, w in SLITS:
        path = [(c - 48.0, r + 0.5) for c, r in ctrl]
        d = [0.0]
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            d.append(d[-1] + math.hypot(x1 - x0, y1 - y0))
        fx, fy = T.pchip(d, [p[0] for p in path]), T.pchip(d, [p[1] for p in path])
        ts = T.frange(0, d[-1], step)
        pts = [(fx(t), fy(t)) for t in ts]
        nrm, hws = [], []
        for i, t in enumerate(ts):
            (xa, ya), (xb, yb) = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            ln = math.hypot(xb - xa, yb - ya) or 1e-9
            nrm.append((-(yb - ya) / ln, (xb - xa) / ln))
            e = min(t, d[-1] - t) / (w / 2)
            hws.append(w / 2 * math.sqrt(max(0.0, min(1.0, 0.25 + 0.75 * e))))
        out.append((pts, nrm, hws))
    return out


def ribbon_solid(P, pts, nrm, hws, levels, mat):
    """A closed solid along a ribbon: `levels` [(z(x, y), extra half width)] from the bottom up."""
    rings = []
    for (x, y), (nx, ny), hw in zip(pts, nrm, hws):
        left = [P.v((x - nx * (hw + e), y - ny * (hw + e), zf(x, y))) for zf, e in levels]
        right = [P.v((x + nx * (hw + e), y + ny * (hw + e), zf(x, y))) for zf, e in levels]
        rings.append(left + list(reversed(right)))
    m = len(rings[0])
    for i in range(len(rings) - 1):
        cx, cy = pts[i]
        zc = (levels[0][0](cx, cy) + levels[-1][0](cx, cy)) / 2
        for j in range(m):
            k = (j + 1) % m
            P.f((rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]), mat, away=(cx, cy, zc))
    (x0, y0), (x1, y1) = pts[0], pts[1]
    P.f(rings[0], mat, out=(x0 - x1, y0 - y1, 0))
    (x0, y0), (x1, y1) = pts[-1], pts[-2]
    P.f(rings[-1], mat, out=(x0 - x1, y0 - y1, 0))


def cutter_object(coll, S):
    """Ribbons through the pod along the slit centrelines; the top widens by 0.6 px either side from
    just under the shell, so the cut rim is chamfered."""
    P = T.Part("slits", smooth_angle=10)
    rib = slit_ribbons()
    for pts, nrm, hws in rib:
        levels = [(lambda x, y: -30.0, 0.0), (lambda x, y: S.z(x, y, EQ) - 1.1, 0.0),
                  (lambda x, y: S.z(x, y, EQ) + 0.2, 0.6), (lambda x, y: 60.0, 0.6)]
        ribbon_solid(P, pts, nrm, hws, levels, 0)
    P.bm.normal_update()
    bmesh.ops.recalc_face_normals(P.bm, faces=P.bm.faces)
    P.hints = []
    obj = T.finish(P, [], coll)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    print(f"slit cutter: {len(rib)} ribbons")
    return obj


def slit_fill(S):
    """The closed-eye frames (193 / 195) draw the slits filled with dark ink: a thin dark plate in each
    slit just under the shell, for the -f3 models."""
    P = T.Part("slit-fill", smooth_angle=10)
    for pts, nrm, hws in slit_ribbons():
        levels = [(lambda x, y: S.z(x, y, EQ) - 1.6, 0.25), (lambda x, y: S.z(x, y, EQ) - 0.7, 0.25)]
        ribbon_solid(P, pts, nrm, hws, levels, 0)
    return P


def apply_boolean(obj, cutter):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new("slits", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.use_self = True
    mod.use_hole_tolerant = True
    bpy.ops.object.modifier_apply(modifier=mod.name)


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def seam_faces(obj, mats_before):
    """Faces the cutter made (material index outside the model's slots) -> SEAM."""
    for p in obj.data.polygons:
        if p.material_index >= mats_before:
            p.material_index = SEAM


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def split_open(obj, layout, coll):
    """split_assembly's cut without capping (the outline shell: no ink line at the seams)."""
    out = {}
    for name, (cx, cy) in layout.items():
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def cull_hidden(obj, grid=6, ndirs=96):
    """usp_talon.cull_hidden with denser sampling (a copy; candidate for usp_talon): every face gets a
    grid of points (quads) or points out to its corners (others), and the directions include straight
    up and the tilted game camera's, so a face that shows only through a narrow gap between ribs, or at
    a rib's end, stays."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    # planar faces only: a sample on a twisted quad (a rib on the steep flank) can start inside the mesh
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4 and abs(
        (f.verts[1].co - f.verts[0].co).cross(f.verts[2].co - f.verts[0].co).normalized().dot(f.normal)) < 0.999])
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = [Vector((0, 0, 1))]
    for tilt in (15, 30, 45):
        for yaw in range(0, 360, 45):
            t, y_ = math.radians(tilt), math.radians(yaw)
            dirs.append(Vector((math.sin(t) * math.sin(y_), -math.sin(t) * math.cos(y_), math.cos(t))))
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 2e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    a = vs[0].lerp(vs[1], u)
                    b = vs[3].lerp(vs[2], u)
                    pts.append(a.lerp(b, v))
        else:
            for vco in vs:
                for t in (0.35, 0.7, 0.92, 0.98):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    print(f"{NAME}: culled {len(dead)} hidden faces of {len(bm.faces)}")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


def finish_piece(pc):
    pc.data.shade_smooth()
    pc.data.set_sharp_from_angle(angle=math.radians(35.0))
    wn = pc.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50


def variant_mats(kind):
    if kind == "dim":
        return M.build({"eye": (42, 0.2, 0.15, 0.0, None)})
    if kind == "grey":
        return M.build({"eye": (8, 0.45, 0.25, 0.0, None)})
    if kind == "lit":
        return M.build({"stripe": (196, 0.1, 0.3, 1.2, None), "housing": (4, 0.4, 0.45, 0.0, None)})
    return M.build()


def part_object(P, mats, coll):
    obj = T.finish(P, mats, coll)
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    coll = common.reset_collection(NAME)

    hull, lobes, pads = build_body()
    S = Surface((hull, lobes, pads))
    ribs = build_ribs(S)
    mach, housing = build_machinery(S)
    glow = build_glow(Surface((hull, lobes, pads, ribs)))
    base_mats = M.build()
    nslots = len(base_mats)
    objs = [part_object(P, base_mats, coll) for P in (hull, lobes, pads, ribs, mach, housing, glow)]
    for o in objs:
        print(f"  part {o.name}: {tris(o)} triangles")
    cutter = cutter_object(coll, S)
    cut_mat = common.palette_material(SPRITE, 1, TAG + "cut", metallic=0.0, roughness=0.9)
    cutter.data.materials.append(cut_mat)
    for o in (objs[0], objs[5]):
        before = tris(o)
        apply_boolean(o, cutter)
        print(f"  boolean {o.name}: {before} -> {tris(o)} triangles")
        seam_faces(o, nslots)
        while len(o.data.materials) > nslots:
            o.data.materials.pop()
    bpy.data.objects.remove(cutter, do_unlink=True)
    whole = join(objs, NAME)
    print(f"whole before cull: {tris(whole)} triangles")

    # Outline shell from a sealed pre-cull copy (D90 / D118).
    sealed = whole.copy()
    sealed.data = whole.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.03, faces=4000, smooth=6, inside=0.004)
    cull_hidden(whole)
    bpy.data.objects.remove(sealed, do_unlink=True)
    print(f"whole after cull: {tris(whole)} triangles; shell {len(shell.data.polygons)} faces")

    layout = [(n, cx, cy) for n, (cx, cy) in LAYOUT.items()]
    pieces = common.split_assembly(whole, layout, coll)
    shells = split_open(shell, LAYOUT, coll)
    for pc in pieces.values():
        finish_piece(pc)

    # Per-frame eye parts (glow models) and variant extras.
    eye_objs = {}
    core_mat = common.palette_material(SPRITE, 47, TAG, roughness=0.25, emission_strength=0.6)
    for name, P in build_eye_parts().items():
        eye_objs[name] = T.finish(P, [core_mat], coll)
    region = {"newshj-161": (10, 22, 0, 18), "newshj-163": (0, 16, 0, 18)}
    for name in ("flecks-pale", "flecks-yellow"):
        px = eye_pixels(GLOW_STEPS[name], {14, 31, 45, 94, 95, 110, 126}, region)
        idx = sorted({i for *_, i in px})
        P = T.Part(name, smooth_angle=60)
        flecks(P, px, lambda i: idx.index(i))
        eye_objs[name] = T.finish(P, [common.palette_material(SPRITE, i, TAG + "fleck", roughness=0.3, emission_strength=1.5)
                                      for i in idx], coll)
    # dim: a reflection up on the left and the grey glyph; grey: a reflection only
    extras = {}
    P = T.Part("dim-extra", smooth_angle=60)
    dome(P, -10.5, 32.6, 3.2, 2.6, 0, 0.2, 0, seg=14, rings=3, zf=lambda x, y: lens_z(x, y) - 0.05, bottom=False)
    flecks(P, eye_pixels(DIM_STEPS[0], set(range(10, 14)), {"newshj-161": (13, 20, 2, 10), "newshj-163": (3, 10, 2, 11)}),
           lambda i: 1)
    extras["dim"] = T.finish(P, [common.palette_material(SPRITE, 141, TAG + "refl", metallic=0.2, roughness=0.1,
                                                          frames={199: 139}),
                                 common.palette_material(SPRITE, 10, TAG + "glyph", metallic=0.3, roughness=0.3,
                                                         frames={199: 12, 201: 12})], coll)
    P = T.Part("grey-extra", smooth_angle=60)
    dome(P, -9.5, 32.4, 3.4, 2.8, 0, 0.2, 0, seg=14, rings=3, zf=lambda x, y: lens_z(x, y) - 0.05, bottom=False)
    extras["grey"] = T.finish(P, [common.palette_material(SPRITE, 14, TAG + "greyrefl", metallic=0.4, roughness=0.2)],
                              coll)
    extras["grey-fill"] = T.finish(slit_fill(S), [common.palette_material(SPRITE, 1, TAG + "slitfill", metallic=0.0,
                                                                          roughness=0.9)], coll)
    P = T.Part("lit-extra", smooth_angle=60)
    dome(P, -0.6, 75.6, 3.6, 3.6, 0, 2.2, 0, seg=16, rings=4, zf=lambda x, y: MUZZLE_Z[0] - 0.4, bottom=True)
    extras["lit"] = T.finish(P, [common.palette_material(SPRITE, 204, TAG + "muz", roughness=0.2, emission_strength=2.0)],
                             coll)

    eye_layout = [(n, *LAYOUT[n]) for n in ("newshj-161", "newshj-163")]
    front_layout = [(n, *LAYOUT[n]) for n in ("newshj-231", "newshj-233")]
    per_model_extra = {m: [] for m in MODELS}
    for name, obj in eye_objs.items():
        cut = common.split_assembly(obj, eye_layout, coll)
        for model, frame in (("newshj-161", GLOW_STEPS[name][0]), ("newshj-163", GLOW_STEPS[name][1])):
            part = cut[model]
            part.name = f"{model}-{name}"
            per_model_extra[model].append(common.frame_part(part, [frame]))
    for kind, obj in extras.items():
        lay = front_layout if kind == "lit" else eye_layout
        cut = common.split_assembly(obj, lay, coll)
        for model, (piece, frames, k) in MODELS.items():
            if k == kind.split("-")[0] and piece in cut:
                cp = cut[piece].copy()
                cp.data = cut[piece].data.copy()
                coll.objects.link(cp)
                cp.name = f"{model}-{kind}"
                per_model_extra[model].append(cp)

    # Models: base pieces and their material variants.
    models = {}
    for model, (piece, frames, kind) in MODELS.items():
        if kind == "base":
            obj = pieces[piece]
        else:
            obj = pieces[piece].copy()
            obj.data = pieces[piece].data.copy()
            coll.objects.link(obj)
            obj.name = model
            mats = variant_mats(kind)
            for i, mt in enumerate(mats):
                obj.data.materials[i] = mt
        models[model] = [obj, shells[piece]] + per_model_extra[model]

    total = sum(tris(pieces[p]) for p in PIECES)
    print(f"base pieces: {total} triangles in all")
    for p in PIECES:
        print(f"  {p}: {tris(pieces[p])}")

    for model, objects in models.items():
        piece, frames, kind = MODELS[model]
        for o in objects:  # the one shared camera-ray anchor on every piece (D181): no seams
            o["tyrian_anchor"] = ANCHOR
        sprites = SPR[piece]["sprites"] if frames is None else [{**SPR[piece]["sprites"][0], "frames": frames}]
        common.export_sprite_model(ROOT, objects, f"enemies/{model}", sprites)
    if out or views:
        # The assembled boss (base pieces placed back at their layout positions).
        placed = []
        for p in PIECES:
            cx, cy = LAYOUT[p]
            for o in (pieces[p], shells[p]):
                o.location = (cx / 12, -cy / 12, 0)
                placed.append(o)
        for model in ("newshj-161", "newshj-163"):
            for o in per_model_extra[model]:
                if "tyrian_frames" in o and list(o["tyrian_frames"]) == [GLOW_STEPS["core"][0 if model.endswith("161") else 1]]:
                    cx, cy = LAYOUT[model]
                    o.location = (cx / 12, -cy / 12, 0)
                    placed.append(o)
        if out:
            common.export_glb(placed, out)
            print(f"exported {out}")
        if views:
            render_views([o for o in placed if not o.get("tyrian_outline")], views)


MUZZLE_Z = [0.0]


def render_views(objs, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in list(scene.objects):
        if o not in objs:
            o.hide_render = True
    for o in objs:
        o.hide_render = False
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.35, 0.35, 0.38, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(-30))
    scene.collection.objects.link(sun)
    # centre of the boss: col 48.5 (x 0), row 56 -> Y = (14 - 56) / 12
    cy = (14 - 56) / 12
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam

    def shot(name, loc, rot, ortho=None, res=(900, 900)):
        scene.render.resolution_x, scene.render.resolution_y = res
        cam.location = loc
        cam.rotation_euler = rot
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = "PERSP"
            cam.data.lens = 50
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    # top (ortho, exactly the 96 x 112 grid at 8 px per sprite px)
    W, H = 96 / 12, 112 / 12
    scene.render.resolution_x, scene.render.resolution_y = 768, 896
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = H
    cam.location = (-0.5 / 12, (14 - 56) / 12, 20)
    cam.rotation_euler = (0, 0, 0)
    scene.render.filepath = str(out_dir / "top.png")
    bpy.ops.render.render(write_still=True)
    # flat mask: emission-white override
    flat = bpy.data.materials.new("flatmask")
    flat.use_nodes = True
    nt = flat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (1, 1, 1, 1)
    o_ = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], o_.inputs[0])
    vl = scene.view_layers[0]
    vl.material_override = flat
    scene.render.filepath = str(out_dir / "top_flat.png")
    bpy.ops.render.render(write_still=True)
    vl.material_override = None
    d = 26
    shot("side", (d, cy, 1.0), (math.radians(88), 0, math.radians(90)), ortho=11, res=(1000, 500))
    shot("front", (0, cy - d, 1.0), (math.radians(88), 0, 0), ortho=11, res=(1000, 500))
    shot("rear", (0, cy + d, 1.0), (math.radians(88), 0, math.radians(180)), ortho=11, res=(1000, 500))
    shot("under", (0, cy, -20), (math.radians(180), 0, 0), ortho=10, res=(700, 800))

    def look(name, yaw, tilt, dist=22, res=(1000, 800)):
        # camera on a sphere round the centre: yaw 0 = from the south (-Y), tilt from horizontal
        t, y_ = math.radians(tilt), math.radians(yaw)
        loc = Vector((dist * math.cos(t) * math.sin(y_), cy - dist * math.cos(t) * math.cos(y_), 1.0 + dist * math.sin(t)))
        direction = Vector((0, cy, 1.0)) - loc
        rot = direction.to_track_quat("-Z", "Y").to_euler()
        shot(name, tuple(loc), tuple(rot), res=res)
    look("q1", -35, 50)
    look("q2", 145, 55)
    look("game", 0, 58, dist=30)


if __name__ == "__main__":
    main()
