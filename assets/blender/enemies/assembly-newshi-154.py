"""assembly-newshi-154, the BOW of the SAVARA blimp (D120): the gas envelope's nose cone, cross-sections first.

newshi.shp frames 154 | 156 | 158 (three 2x2 enemies side by side, 72 x 28 px, one frame each; types
363-365, episode 1 SAVARA levels 1.8 / 1.12 / 1.17 and 3.10). It is drawn right under the last row of
assembly-newshi-115 (the envelope; its col 12, row 112 is this assembly's (0, 0)) and moves with it.

Object (D122 audit fix): every move event for the formation (types 349-365) sets eyc 0, +1 or +2, i.e.
the blimp drifts south, toward the player: this end LEADS. Its nine meridian ribs meeting at a hub are
a blimp's nose battens round the mooring cone, so this is the bow and the ducted propeller at
assembly-newshi-115's north end is the stern (a pusher). The envelope's script still calls its
propeller end the "nose" and this the "tail cap" (its geometry is unaffected). It floats: no base.

Engineering reading:

  plan        the sprite's INNER mask (D74: its dark ring is the game's ink outline), row by row,
              lightly smoothed; a rounded point at the bottom; the envelope continues north beyond
              the cut (a virtual arc to y = -14.5 so the north rays have a rim to aim at)
  upper half  D153: the envelope's own egg carried on past the cut (assembly-newshi-115's sections and
              long profile): each row's section a soft superellipse over the plan's width at that row,
              z = ZE + U0*egg(y)*sqrt(1-q^1.6), q the offset from the row's middle over its half width,
              egg(y) the quarter ellipse from the envelope's crown (115 row 70, here y -42) to the bow
              tip (y 27.45); at the cut the section is the envelope's (crown 26.3 on the axis)
  equator     on the plan's edge, at ZE = 6 px all round: the envelope's level equator
  belly       a round lower half on the same sections, z = ZE - L0*egg(y)*sqrt(1-q^2) (the envelope's
              belly carried on to the tip); plain (a plausible closed shape only)
  stations    the mesh still runs on rays from the pole P = (37.5, 16.5), the hub, where the battens meet
  seams       three latitude panel grooves round the pole (s 0.42, 0.72, 0.93): chamfered grooves
              0.9 px wide, 0.28 px deep, cut along the surface normal, painted one step darker than their panel
  battens     the ribs: chamfered straps (1.2 px wide, 0.7 px high) along the traced meridians,
              standing on the shell normal, bolts every 5.5 px, a bigger bolt at each foot
  hub         chamfered collar ring (r 1.7) with six bolts and the mooring cone (r 0.95, 1.5 px tall, 102)
  rivet       blue-grey domed head (r 0.6) on the north-east rib at (49, 1.5)
  joint       the north cut: a flat mating wall (upper half to belly), no flange of its own: the
              envelope's flange 1.6 px north is the joint, so the fabric runs on across it as in the sprite

Colours (rule 1, per region): the sprite's nose is darker than the envelope and darkens toward the
tip (row medians 6 at rows 0-1, 5 to row 7, 4 to the hub, 3 below it, 1-2 at the tip), and in the
game the light barely darkens the high crest, so that axial ramp is paint, panel by panel (zones
C/F/W/S by the battens, bands by the latitude grooves; ZONE_PAINT): the joint collar 7, the north cap
6, the north flanks 5, the waist 4-3, the tip 3 (in the game the north half reads 0.71 of the
envelope, the south half 0.49; the sprite 0.74 / 0.43). Battens one step lighter than the brighter
panel beside them (8-7 in the north fading to 5-4 at the tip, the sprite's ribs), grooves one darker,
hub collar 6, mooring cone and rivet 102. The ramp is the same east and west: the sprite's
west-bright / east-dark is its light, left to the game's (rule 2).

Units: sprite px; Blender X = (x - 36) / 12, Y = (14 - y) / 12, Z = z / 12 (assembly origin = the
centre of newshi-156, screen (150, -17)). Built whole, the outline shell (D51) built whole from the
smooth envelope surface, belly included (build_outline_shell: no grooves to crack), both cut into the three pieces (split_pieces:
clean inset caps, no holes_fill, the hull's normals on the cut). AO/roughness bake only ("bake": "model"), no concept
projection.

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newshi-154.py -- \
       [--measure DIR] [--views DIR] [--no-bake] [--no-export] [--glb ASSEMBLY.glb]
Exports the three pieces (each with its outline shell, at its own origin) with
common.export_sprite_model to enemies/newshi-154, -156 and -158. Maps: AO/roughness bake of the
model itself (textures/assembly-newshi-154/maps.json says "bake": "model"), no concept projection.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask  # noqa: E402
NAME = "assembly-newshi-154"
PIECES = ["newshi-154", "newshi-156", "newshi-158"]
CX0, CY0 = 150, -17

# The meridian ribs traced from the sprite (assembly px, hub first): the hub is where they meet.
RIBS = [["rib_n", [[37.5, 16.5], [37.5, -1.0]]], ["rib_nw1", [[37.5, 16.5], [36.5, 14.0], [34.5, 11.0], [33.5, 8.5], [32.5, 6.0], [31.5, 4.0], [30.5, 1.0], [30.2, -1.0]]], ["rib_nw2", [[37.5, 16.5], [34.0, 14.5], [31.5, 12.5], [24.5, 5.5], [22.5, 2.5], [21.5, 0.5], [21.0, -1.0]]], ["rib_w", [[37.5, 16.5], [31.0, 15.5], [27.0, 14.3], [24.5, 13.3], [22.0, 12.0], [19.5, 9.5], [16.5, 6.5], [14.5, 4.0], [12.5, 1.0], [11.8, -1.0]]], ["rib_ne1", [[37.5, 16.5], [41.5, 12.5], [43.5, 10.5], [44.5, 8.5], [45.5, 7.0], [46.5, 5.5], [47.5, 3.5], [48.5, 1.0], [49.0, -1.0]]], ["rib_ne2", [[37.5, 16.5], [44.0, 14.0], [48.5, 12.5], [51.5, 10.5], [54.5, 7.5], [56.5, 4.5], [58.5, 1.5], [59.3, -1.0]]], ["rib_s", [[37.5, 16.5], [37.5, 27.2]]], ["rib_sw", [[37.5, 16.5], [34.5, 17.5], [32.5, 18.5], [31.5, 19.5], [28.5, 20.5], [24.5, 21.2], [21.6, 21.7]]], ["rib_se", [[37.5, 16.5], [39.5, 19.5], [41.5, 20.5], [43.5, 21.5], [45.5, 22.5], [48.5, 24.0]]]]

POLE = (37.5, 16.5)
SEAMS = (0.42, 0.72, 0.93)
SEAM_HW = 0.45   # groove half width, px
SEAM_D = 0.28    # groove depth, px
RW, RH, RCH = 0.6, 0.7, 0.18   # rib half width, height, chamfer (px)
# Object fix (D122 audit): a floating envelope's nose, not a flat-based dome. D153: the envelope's egg
# (assembly-newshi-115) carried on to the tip: its level equator ZE, its upper half U0 and belly L0 at the
# crown (115 row 70 = this y -42), scaled by the same quarter-ellipse long profile to the bow tip.
ZE = 6.0
U0 = 25.5
L0 = 11.0
NU = 1.6       # the upper half's section exponent (the envelope's NXS_U)
Y_CROWN = -42.0
Y_TIP = 27.45


def W(x, y, z):
    """Sprite px (x east, y south, z up) to Blender units."""
    return Vector(((x - 36) / 12, (14 - y) / 12, z / 12))


# ---------------------------------------------------------------------------------------------
# The sprite
# ---------------------------------------------------------------------------------------------

def sprite_grid():
    idx = -np.ones((28, 72), dtype=int)
    colours = {}
    for i, n in enumerate(PIECES):
        d = common.load_sprite(ROOT, n)
        colours.update({int(k): tuple(v) for k, v in d["colors"].items()})
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                idx[r, i * 24 + c] = v
    return idx, colours


IDX, COLOURS = sprite_grid()
MASKS = sprite_mask.masks(IDX.tolist(), COLOURS)
INNER = np.array(MASKS["inner"], dtype=bool)
FREE = np.array(MASKS["free"], dtype=bool)


def footprint():
    """The plan (assembly px), counter-clockwise in screen space read y-down... the order only
    matters for the ray test: the inner mask's extent per row, smoothed, a rounded point at the
    bottom and a virtual arc beyond the north cut."""
    L, R = [], []
    rows = [r for r in range(28) if INNER[r].any()]
    for r in rows:
        xs = np.nonzero(INNER[r])[0]
        L.append(float(xs.min()))
        R.append(float(xs.max() + 1))

    def sm(v):
        out = []
        for i in range(len(v)):
            w = v[max(i - 1, 0):i + 2]
            out.append(0.25 * w[0] + 0.5 * v[i] + 0.25 * w[-1] if len(w) == 3 else v[i])
        return out
    L, R = sm(sm(L)), sm(sm(R))
    last = rows[-1]
    pts = [(max(R[0], R[1]) + 1.0, -4.0), (62.0, -10.0), (50.0, -13.5), (36.5, -14.5), (23.0, -13.5), (11.0, -10.0),
           (L[0] - 1.0, -4.0)]
    pts += [(L[i], r + 0.5) for i, r in enumerate(rows)]
    mid = 0.5 * (L[-1] + R[-1])
    pts += [(L[-1] + 1.2, last + 1.15), (mid - 2.0, last + 1.45), (mid + 2.0, last + 1.45), (R[-1] - 1.2, last + 1.15)]
    pts += [(R[i], r + 0.5) for i, r in reversed(list(enumerate(rows)))]
    return pts


OUTLINE = footprint()


def rim_dist_raw(dx, dy):
    best = 1e9
    n = len(OUTLINE)
    for i in range(n):
        p, q = OUTLINE[i], OUTLINE[(i + 1) % n]
        ex, ey = q[0] - p[0], q[1] - p[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        wx, wy = p[0] - POLE[0], p[1] - POLE[1]
        t = (wx * ey - wy * ex) / den
        u = (wx * dy - wy * dx) / den
        if t > 0 and -1e-6 <= u <= 1 + 1e-6:
            best = min(best, t)
    return best


_NA = 1440
_RAW = np.array([rim_dist_raw(math.cos(2 * math.pi * i / _NA), math.sin(2 * math.pi * i / _NA)) for i in range(_NA)])
_K = np.exp(-0.5 * (np.arange(-24, 25) / 8.0) ** 2)  # sigma 2 degrees
_K /= _K.sum()
_RIM = np.convolve(np.concatenate([_RAW[-24:], _RAW, _RAW[:24]]), _K, mode="valid")


def rim_dist(dx, dy):
    """The rim distance along a ray from the pole, smoothed over the ray angle (sigma 2 degrees) so
    the flank is one fair surface instead of following the plan's pixel steps."""
    a = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0 * _NA
    i = int(a)
    f = a - i
    return float(_RIM[i % _NA] * (1 - f) + _RIM[(i + 1) % _NA] * f)


def s_at(x, y):
    """Fraction of the rim distance along the ray from the pole (0 at the hub, 1 at the rim)."""
    vx, vy = x - POLE[0], y - POLE[1]
    t = math.hypot(vx, vy)
    return 0.0 if t < 1e-6 else t / rim_dist(vx / t, vy / t)


def egg(y):
    """The envelope's long profile (assembly-newshi-115's egg_k): a quarter ellipse from its crown to the
    bow tip."""
    t = min(1.0, max(0.0, (y - Y_CROWN) / (Y_TIP - Y_CROWN)))
    return math.sqrt(max(0.0, 1 - t * t))


def _rim_edges(y):
    """The plan's west and east edges at row y (where s = 1 along the row), by bisection."""
    def edge(sign):
        lo, hi = POLE[0], POLE[0] + sign * 40.0
        if s_at(lo, y) >= 1.0:
            return lo
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            if s_at(mid, y) < 1.0:
                lo = mid
            else:
                hi = mid
        return lo
    return edge(-1), edge(1)


_RY0, _RDY = -0.5, 0.025
_RTAB = [_rim_edges(max(0.0, _RY0 + k * _RDY)) for k in range(int((Y_TIP + 1.0 - _RY0) / _RDY) + 2)]


def row_span(y):
    """(middle, half width) of the plan at row y (rows north of the cut take the cut's)."""
    f = (min(max(y, _RY0), Y_TIP + 1.0) - _RY0) / _RDY
    i = min(int(f), len(_RTAB) - 2)
    f -= i
    (a0, b0), (a1, b1) = _RTAB[i], _RTAB[i + 1]
    xl, xr = a0 + (a1 - a0) * f, b0 + (b1 - b0) * f
    return 0.5 * (xl + xr), 0.5 * (xr - xl)


def _q(x, y):
    c, hw = row_span(y)
    return 1.0 if hw < 1e-3 else min(1.0, abs(x - c) / hw)


def z_at(x, y):
    """The envelope's upper half: a true ellipse across the row from the equator (ZE, on the plan's edge)."""
    q = _q(x, y)
    return ZE + U0 * egg(y) * math.sqrt(max(0.0, 1 - q ** NU))


def zl_at(x, y):
    """The envelope's lower half: a round belly from the equator (ZE on the plan's edge) down."""
    q = _q(x, y)
    return ZE - L0 * egg(y) * math.sqrt(max(0.0, 1 - q * q))


def nl_at(x, y, e=0.05):
    """Outward (downward) normal of the lower half."""
    zx = (zl_at(x + e, y) - zl_at(x - e, y)) / (2 * e)
    zy = (zl_at(x, y + e) - zl_at(x, y - e)) / (2 * e)
    return Vector((zx, zy, -1.0)).normalized()


def n_at(x, y, e=0.05):
    zx = (z_at(x + e, y) - z_at(x - e, y)) / (2 * e)
    zy = (z_at(x, y + e) - z_at(x, y - e)) / (2 * e)
    v = Vector((-zx, -zy, 1.0))
    return v.normalized()


def frame_at(x, y):
    """Local frame on the shell at (x, y): origin, tangent t (east-ish), b, normal n, in px."""
    n = n_at(x, y)
    t = Vector((0, 1, 0)).cross(n).normalized()
    b = n.cross(t)
    return Vector((x, y, z_at(x, y))), t, b, n


def P(p):
    """A px-space Vector to Blender."""
    return W(p.x, p.y, p.z)


# ---------------------------------------------------------------------------------------------
# Mesh building
# ---------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(P(p))

    def f(self, vs, mat):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face


SHELL, RIB, BOLT, CAP, GROOVE = range(5)


# Paint (rule 1: the sprite's index per region). The sprite's nose is no envelope-pale cap: its rows 0-2
# carry on from the envelope's last rows (6-8 at the centre), then it darkens toward the tip (row
# medians 5 to row 7, 4 to the hub, 3 below it, 1-2 at the tip). In the game the light barely darkens
# the high crest, so that axial ramp is paint, laid panel by panel: every change of paint sits under a
# batten or in a latitude groove, never on open fabric. The ramp runs only along the axis and is the
# same east and west; the sprite's west-bright / east-dark is its light (rule 2), left to the game's.
# Sectors are named by the battens that bound them; bands are the latitude grooves (0 inside SEAMS[0]).
SECTOR_ZONE = {("rib_nw2", "rib_nw1"): "C", ("rib_nw1", "rib_n"): "C", ("rib_n", "rib_ne1"): "C",
               ("rib_w", "rib_nw2"): "F", ("rib_ne1", "rib_ne2"): "F",
               ("rib_ne2", "rib_se"): "W", ("rib_sw", "rib_w"): "W",
               ("rib_se", "rib_s"): "S", ("rib_s", "rib_sw"): "S"}
# per band 0..3: C the north centre (the joint collar is its bands 1+, rows 0-3), F the north flanks,
# W the waist either side of the hub, S the tip
ZONE_PAINT = {"C": (6, 7, 7, 7), "F": (5, 5, 5, 5), "W": (4, 3, 3, 3), "S": (3, 3, 3, 3)}
HUB_PAINT = 6        # the hub collar and its bolts
CAP_PAINT = 102      # the mooring cone and the rivet


def rib_tracks():
    """Each batten's centre line as built (build_ribs), carried on to the rim: name -> (distance from
    the pole, polar angle about the pole) arrays, sorted by distance, for the sector test."""
    out = {}
    for name, pl in RIBS:
        pts = [p for p in resample(chaikin(pl), 0.5) if math.hypot(p[0] - POLE[0], p[1] - POLE[1]) >= 1.0]
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        L = math.hypot(bx - ax, by - ay)
        while s_at(*pts[-1]) < 1.05 and pts[-1][1] > -2.0:
            pts.append((pts[-1][0] + 0.5 * (bx - ax) / L, pts[-1][1] + 0.5 * (by - ay) / L))
        d = np.array([math.hypot(x - POLE[0], y - POLE[1]) for x, y in pts])
        a = np.unwrap(np.array([math.atan2(y - POLE[1], x - POLE[0]) for x, y in pts]))
        o = np.argsort(d)
        out[name] = (d[o], a[o])
    return out


TRACKS = None


def sector_of(x, y):
    """The pair of battens (west/clockwise first, in the y-down screen sense of SECTOR_ZONE) the point
    lies between, by the battens' polar angles at the point's own distance from the hub."""
    global TRACKS
    if TRACKS is None:
        TRACKS = rib_tracks()
    t = math.hypot(x - POLE[0], y - POLE[1])
    th = math.atan2(y - POLE[1], x - POLE[0]) % (2 * math.pi)
    angs = sorted((float(np.interp(t, d, a)) % (2 * math.pi), n) for n, (d, a) in TRACKS.items())
    for i, (a0, n0) in enumerate(angs):
        a1, n1 = angs[(i + 1) % len(angs)]
        span = (a1 - a0) % (2 * math.pi)
        if (th - a0) % (2 * math.pi) < span:
            return n0, n1
    return angs[-1][1], angs[0][1]


def band_of(x, y):
    s = s_at(x, y)
    return sum(s >= b for b in SEAMS)


def shell_paint(x, y):
    return ZONE_PAINT[SECTOR_ZONE[sector_of(x, y)]][band_of(x, y)]


def nearest_rib(x, y):
    global TRACKS
    if TRACKS is None:
        TRACKS = rib_tracks()
    t = math.hypot(x - POLE[0], y - POLE[1])
    th = math.atan2(y - POLE[1], x - POLE[0])
    best = None
    for n, (d, a) in TRACKS.items():
        da = abs((float(np.interp(t, d, a)) - th + math.pi) % (2 * math.pi) - math.pi)
        if best is None or da < best[0]:
            best = (da, n)
    return best[1]


def rib_paint(x, y):
    """A batten one step lighter than the brighter of the two panels it divides (the sprite's ribs:
    6-7 in the north, fading to 4-5 on the dark tip), at most 8."""
    r = nearest_rib(x, y)
    b = band_of(x, y)
    sides = [ZONE_PAINT[z][b] for pair, z in SECTOR_ZONE.items() if r in pair]
    return min(8, max(sides) + 1)


def paint_faces(bm):
    """Tag (SHELL, RIB, BOLT, CAP, GROOVE) to palette index, by where the face's centre lies."""
    out = []
    for f in bm.faces:
        c = f.calc_center_median()
        x, y = c.x * 12 + 36, 14 - c.y * 12
        tag = f.material_index
        if tag == CAP:
            out.append(CAP_PAINT)
        elif tag in (RIB, BOLT):
            out.append(HUB_PAINT if math.hypot(x - POLE[0], y - POLE[1]) < 2.3 else rib_paint(x, y))
        elif tag == GROOVE:
            out.append(max(3, shell_paint(x, y) - 1))
        else:
            out.append(shell_paint(x, y))
    return out


def materials(sprite, used):
    """One palette material per index used (pal_<index>): fabric and battens satin, the mooring cone
    and rivet blue-grey metal."""
    tag = "nshi154C"
    mats = []
    for k in used:
        if k == CAP_PAINT:
            mats.append(common.palette_material(sprite, k, tag, metallic=0.25, roughness=0.32))
        else:
            # doped fabric and its battens: a broad satin sheen (the 0.34 gloss of the pale envelope read
            # as black chrome on the darker panels)
            mats.append(common.palette_material(sprite, k, tag, metallic=0.12, roughness=0.46))
    return mats


def build_shell(M, NT=112):
    """The nose: rays from the pole, latitude grooves cut along the normal (painted one step darker
    than their panel), the equator on the plan's edge and a round belly under it (no detail)."""
    grid, lows, gflags = [], [], []
    for i in range(NT):
        a = 2 * math.pi * i / NT
        dx, dy = math.cos(a), math.sin(a)
        Rr = rim_dist(dx, dy)
        st = []
        e = [(s0 - SEAM_HW / Rr, s0 + SEAM_HW / Rr) for s0 in SEAMS]
        a0 = e[0][0]
        st += [(a0 * (1 - (1 - k / 10) ** 1.25), 0.0, False) for k in range(1, 11)]
        st += [(v, 0.0, False) for v in np.linspace(e[0][1], e[1][0], 7)]
        st += [(v, 0.0, False) for v in np.linspace(e[1][1], e[2][0], 5)]
        st += [(e[2][1], 0.0, False)] + [(v, 0.0, False) for v in (0.978, 0.99, 0.997, 1.0)]
        for s0, (lo, hi) in zip(SEAMS, e):
            ds = hi - s0
            st += [(s0 - 0.45 * ds, SEAM_D, True), (s0 + 0.45 * ds, SEAM_D, True)]
        st.sort()
        ring, low, flags = [], [], []
        for s, d, _ in st:
            if s == 0.0:
                continue
            x, y = POLE[0] + dx * s * Rr, POLE[1] + dy * s * Rr
            z = ZE if s >= 1.0 else z_at(x, y)
            p = Vector((x, y, z))
            if d:
                p -= n_at(x, y) * d
            ring.append(p)
            flags.append(bool(d))
            if s < 1.0:  # the belly: the same stations (so the cut pairs them), no grooves (D: plain)
                low.append(Vector((x, y, zl_at(x, y))))
        grid.append(ring)
        lows.append(low)
        gflags = flags
    nst = len(grid[0])
    assert all(len(r) == nst for r in grid)
    pole = M.v(Vector((POLE[0], POLE[1], z_at(*POLE))))
    vg = [[M.v(p) for p in ring] for ring in grid]
    # the lower half shares the equator (the rim, last upper station) and closes under the pole
    vl = [[M.v(p) for p in low] + [vg[i][-1]] for i, low in enumerate(lows)]
    keel = M.v(Vector((POLE[0], POLE[1], zl_at(*POLE))))
    for i in range(NT):
        j = (i + 1) % NT
        M.f((pole, vg[i][0], vg[j][0]), SHELL)
        for k in range(nst - 1):
            mat = GROOVE if gflags[k] and gflags[k + 1] else SHELL
            M.f((vg[i][k], vg[i][k + 1], vg[j][k + 1], vg[j][k]), mat)
        M.f((keel, vl[j][0], vl[i][0]), SHELL)
        for k in range(len(vl[i]) - 1):
            M.f((vl[i][k], vl[j][k], vl[j][k + 1], vl[i][k + 1]), SHELL)


def cut_north(bm):
    """Cut the hull flat at the sprite's top edge (y = 0), where the envelope (assembly-newshi-115)
    joins, and close it with a flat joint wall from the upper half's cut line to the belly's (welded
    to the shell)."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    yc = 14 / 12
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, yc, 0), plane_no=(0, 1, 0), clear_outer=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # the cut's boundary loop (the upper half's grooves fold it back on itself in x near the flanks,
    # so it is filled as a polygon, not zipped by x): one planar fill, beauty triangulated
    edges = [e for e in bm.edges if e.is_boundary and all(abs(v.co.y - yc) < 1e-4 for v in e.verts)]
    res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges, normal=(0, 1, 0))
    faces = [f for f in res["geom"] if isinstance(f, bmesh.types.BMFace)]
    for f in faces:
        f.material_index = SHELL
        for e in f.edges:
            e.smooth = False
    return faces


def bolt(M, x, y, r, h, lift, mat, sides=6, frame=None):
    o, t, b, n = frame or frame_at(x, y)
    lo, mid, hi = [], [], []
    for k in range(sides):
        a = 2 * math.pi * (k + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        lo.append(M.v(o + t * (r * c) + b * (r * s) + n * (lift - 0.12)))
        mid.append(M.v(o + t * (r * c) + b * (r * s) + n * (lift + 0.6 * h)))
        hi.append(M.v(o + t * (0.72 * r * c) + b * (0.72 * r * s) + n * (lift + h)))
    for k in range(sides):
        j = (k + 1) % sides
        M.f((lo[k], lo[j], mid[j], mid[k]), mat)
        M.f((mid[k], mid[j], hi[j], hi[k]), mat)
    M.f(hi, mat)
    M.f(list(reversed(lo)), mat)


def lathe(M, o, t, b, n, prof, mat, sides=24):
    """Revolve a (radius, height) profile round normal n at o; radius 0 collapses to a centre point."""
    rings = []
    for r, h in prof:
        if r == 0:
            rings.append([M.v(o + n * h)])
            continue
        rings.append([M.v(o + t * (r * math.cos(2 * math.pi * k / sides)) + b * (r * math.sin(2 * math.pi * k / sides)) + n * h)
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                M.f((r0[0], r1[k], r1[j]), mat)
            elif len(r1) == 1:
                M.f((r0[k], r1[0], r0[j]), mat)
            else:
                M.f((r0[k], r1[k], r1[j], r0[j]), mat)


def dome(M, x, y, r, h, lift, mat, sides=16, nr=5):
    o, t, b, n = frame_at(x, y)
    prof = [(0, lift - 0.2), (r, lift - 0.2)]
    prof += [(r * math.cos(0.5 * math.pi * i / nr), lift + h * math.sin(0.5 * math.pi * i / nr)) for i in range(nr)]
    prof += [(0, lift + h)]
    lathe(M, o, t, b, n, prof, mat, sides)


def resample(pl, step):
    out = []
    for a, b in zip(pl, pl[1:]):
        n = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        for k in range(n):
            out.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    out.append(tuple(pl[-1]))
    return out


def chaikin(pl, n=3):
    pts = [tuple(p) for p in pl]
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        out.append(pts[-1])
        pts = out
    return pts


RIB_END_S = 0.952   # the battens run down to just above the equator


def build_ribs(M):
    ribs = [(n, chaikin(pl)) for n, pl in RIBS]
    prof = [(-RW, -0.12), (RW, -0.12), (RW, RH - RCH), (RW - RCH, RH), (-RW + RCH, RH), (-RW, RH - RCH)]
    for name, pl in ribs:
        pts = [p for p in resample(pl, 0.5) if math.hypot(p[0] - POLE[0], p[1] - POLE[1]) >= 1.5]
        # a rib traced short of the rim carries on in its last direction down toward the equator
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        L = math.hypot(bx - ax, by - ay)
        while pts[-1][1] > 0.95 and s_at(*pts[-1]) < RIB_END_S:
            pts.append((pts[-1][0] + 0.5 * (bx - ax) / L, pts[-1][1] + 0.5 * (by - ay) / L))
        pts = [p for p in pts if p[1] >= 0.95 and s_at(*p) <= RIB_END_S]
        if len(pts) < 2:
            continue
        rings = []
        for i, p in enumerate(pts):
            q, o = pts[min(i + 1, len(pts) - 1)], pts[max(i - 1, 0)]
            n = n_at(*p)
            base = Vector((p[0], p[1], z_at(*p)))
            nxt = Vector((q[0], q[1], z_at(*q)))
            prv = Vector((o[0], o[1], z_at(*o)))
            tg = (nxt - prv).normalized()
            side = tg.cross(n).normalized()
            rings.append([M.v(base + side * u + n * h) for u, h in prof])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(len(prof)):
                j = (k + 1) % len(prof)
                M.f((r0[k], r0[j], r1[j], r1[k]), RIB)
        M.f(list(reversed(rings[0])), RIB)
        M.f(rings[-1], RIB)
        acc = 0.0
        for i in range(1, len(pts) - 4):
            acc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            if acc >= 5.5:
                acc = 0.0
                bolt(M, pts[i][0], pts[i][1], 0.2, 0.15, RH, RIB)
        if pts[-1][1] > 1.5:  # the foot: a bigger bolt through the rib's end
            q = pts[-2]
            bolt(M, q[0], q[1], 0.32, 0.18, RH, BOLT)


def build_hub(M):
    o, t, b, n = frame_at(*POLE)
    lathe(M, o, t, b, n, [(0, -0.3), (1.7, -0.3), (1.7, 0.55), (1.52, 0.75), (0, 0.75)], RIB, sides=28)
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        c = o + t * (1.27 * math.cos(a)) + b * (1.27 * math.sin(a))
        bolt(M, c.x, c.y, 0.17, 0.13, 0.0, RIB, frame=(o + (c - o) + n * 0.75 - n * 0.0, t, b, n))
    # the mooring cone on the nose tip (the battens' hub): a short blunt cone
    lathe(M, o, t, b, n, [(0, 0.55), (0.95, 0.55), (0.95, 0.8), (0.78, 1.2), (0.55, 1.6), (0.3, 1.9), (0.12, 2.02), (0, 2.05)],
          CAP, sides=20)
    # the rivet on the north-east rib
    dome(M, 49.0, 1.5, 0.6, 0.35, RH + 0.02, CAP, sides=14, nr=4)


def rim_x(y):
    """The plan's west and east edges at row y (where the equator is)."""
    def edge(sign):
        lo, hi = POLE[0], POLE[0] + sign * 40.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if s_at(mid, y) < 1.0:
                lo = mid
            else:
                hi = mid
        return lo
    return edge(-1), edge(1)


def section(y, n=72):
    """The envelope's closed cross-section at row y as (x, z) points: the upper half west to east,
    then the belly back (cosine spaced, dense at the equator)."""
    xl, xr = rim_x(y)
    xl, xr = xl + 0.01, xr - 0.01
    xs = [0.5 * (xl + xr) - 0.5 * (xr - xl) * math.cos(math.pi * k / n) for k in range(n + 1)]
    up = [(x, z_at(x, y)) for x in xs]
    lo = [(x, zl_at(x, y)) for x in reversed(xs[1:-1])]
    return up + lo


def build(sprite, coll):
    M = Mesh()
    build_shell(M)
    cut_north(M.bm)
    build_ribs(M)
    build_hub(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:  # the joint wall faces north
        if abs(f.calc_center_median().y - 14 / 12) < 1e-4 and abs(f.normal.y) > 0.9 and f.normal.y < 0:
            f.normal_flip()
    paints = paint_faces(bm)
    used = sorted(set(paints), key=lambda k: (k == CAP_PAINT, k))
    slot = {k: i for i, k in enumerate(used)}
    for f, k in zip(bm.faces, paints):
        f.material_index = slot[k]
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in materials(sprite, used):
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    sharp = [not e.use_edge_sharp for e in me.edges]
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    for e, keep in zip(me.edges, sharp):
        if not keep:
            e.use_edge_sharp = True
    return obj


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ---------------------------------------------------------------------------------------------
# Measure and views
# ---------------------------------------------------------------------------------------------

def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [w for w in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split() if w.isupper()]
        scene.render.engine = next(n for n in names if want.split("_")[1] in n)


def render_array(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], img.channels)
    bpy.data.images.remove(img)
    return px[::-1]


def measure(objs, out_dir, ss=8):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o.type == "MESH" and o not in objs and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0, 0, 0)
    cd = bpy.data.cameras.new("measure")
    cd.type = "ORTHO"
    cd.ortho_scale = 72 / 12
    cam = bpy.data.objects.new("measure", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    scene.render.resolution_x = 72 * ss
    scene.render.resolution_y = 28 * ss
    scene.render.resolution_percentage = 100
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sil = render_array(scene, cam, out_dir / "top_silhouette.png")[..., 0]
    cov = sil.reshape(28, ss, 72, ss).mean(axis=(1, 3))
    model = cov >= 0.5
    keep = ~FREE
    res = {}

    def iou(cols):
        m, s, k = model[:, cols], INNER[:, cols], keep[:, cols]
        return float(((m & s) & k).sum() / max(1, ((m | s) & k).sum()))
    res["iou_rule_grid"] = round(iou(slice(0, 72)), 4)
    res["pieces"] = {n: round(iou(slice(24 * i, 24 * i + 24)), 4) for i, n in enumerate(PIECES)}
    # render-resolution IoU against the inner mask
    big = np.kron(INNER, np.ones((ss, ss), dtype=bool))
    top = sil > 0.5
    res["iou_rule_hires"] = round(float((big & top).sum() / max(1, (big | top).sum())), 4)
    diff = np.full((28, 72), ".")
    diff[INNER] = "-"
    diff[model & INNER] = "#"
    diff[model & ~INNER] = "+"
    (out_dir / "diff.txt").write_text("\n".join("".join(r) for r in diff) + "\n")
    # colour: flat material colours from above, nearest palette index of the materials
    sh.color_type = "MATERIAL"
    for o in objs:
        for m in o.data.materials:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            m.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)
    flat = render_array(scene, cam, out_dir / "top_flat.png")[..., :3]
    centre = flat[ss // 2::ss, ss // 2::ss]
    keys = [3, 4, 5, 6, 7, 8, 9, 102]
    arr = np.array([[c / 255 for c in COLOURS[k]] for k in keys])
    d = ((centre[..., None, :] - arr[None, None]) ** 2).sum(-1)
    seen = np.array(keys)[d.argmin(-1)]
    seen[~model] = -1
    ribs = RIBS
    lab = np.full((28, 72), "shell", dtype=object)

    def dseg(p, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
        return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)
    for r in range(28):
        for c in range(72):
            p = (c + 0.5, r + 0.5)
            if IDX[r, c] == 102:
                lab[r, c] = "hub_rivet"
                continue
            for _n, pl in ribs:
                if min(dseg(p, a, b) for a, b in zip(pl, pl[1:])) < 0.75 and math.hypot(p[0] - 37.5, p[1] - 16.5) > 1.2:
                    lab[r, c] = "ribs"
    # per region: the sprite's mean and median index there against the paint the model shows there,
    # regions = the panel zones (C north centre, F north flanks, W waist, S tip) x the latitude bands
    col = {}
    for r in range(28):
        for c in range(72):
            if not (INNER[r, c] and model[r, c]) or IDX[r, c] > 9:
                continue
            x, y = c + 0.5, r + 0.5
            z = SECTOR_ZONE[sector_of(x, y)]
            b = band_of(x, y)
            key = f"{lab[r, c]}:{z}{0 if b == 0 else 1 if b == 1 else 2}"
            col.setdefault(key, {"sprite": [], "model": []})
            col[key]["sprite"].append(int(IDX[r, c]))
            col[key]["model"].append(int(seen[r, c]))
    res["colours"] = {k: {"n": len(v["sprite"]), "sprite_mean": round(float(np.mean(v["sprite"])), 2),
                          "sprite_median": float(np.median(v["sprite"])),
                          "model_median": float(np.median(v["model"])),
                          "model_seen": {int(a): int(b) for a, b in zip(*np.unique(v["model"], return_counts=True))}}
                      for k, v in sorted(col.items())}
    rows = []
    for r in range(28):
        sv = [int(IDX[r, c]) for c in range(72) if INNER[r, c] and IDX[r, c] <= 9]
        mv = [int(seen[r, c]) for c in range(72) if INNER[r, c] and model[r, c] and 0 <= seen[r, c] <= 9]
        if sv and mv:
            rows.append((r, float(np.median(sv)), float(np.median(mv))))
    res["row_medians_sprite_model"] = rows
    # feature check: what the model shows at the sprite's 102 pixels
    res["features102"] = {f"{c},{r}": int(seen[r, c]) for r, c in zip(*np.nonzero(IDX == 102))}
    (out_dir / "metrics.json").write_text(json.dumps(res, indent=1))
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in hidden:
        o.hide_render = False
    print("MEASURE", json.dumps(res))
    return res


def render_views(objs, out_dir, size=900):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o.type == "MESH" and o not in objs and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    # Cycles: EEVEE's screen-space reflections paint blocky ghosts on the satin dome
    set_engine(scene, "CYCLES")
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.21, 0.24, 1)
    bg.inputs["Strength"].default_value = 1.0
    lights = []
    for name, rot, energy in (("key", (math.radians(35), math.radians(-25), math.radians(-20)), 3.6),
                              ("fill", (math.radians(60), math.radians(40), math.radians(160)), 0.9)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(3)
        ld.use_shadow = "--no-shadow" not in sys.argv
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)
        lights.append(lo)
    centre = Vector((0, 0, 0.45))
    d = 14.0
    specs = [
        ("top", (0, 0, 10), 6.6),
        ("front_south", (0, -10, 0), 6.6),
        ("side_west", (-10, 0, 0), 6.6),
        ("side_east", (10, 0, 0), 6.6),
        ("rear_north", (0, 10, 0), 6.6),
        ("high34_sw", (-d * 0.5, -d * 0.55, d * 0.55), None),
        ("high34_ne", (d * 0.55, d * 0.5, d * 0.5), None),
        ("game", (0, -d * 0.53, d * 0.85), None),
        ("under", (d * 0.35, -d * 0.45, -d * 0.6), None),
    ]
    paths = {}
    for name, loc, ortho in specs:
        cd = bpy.data.cameras.new(name)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        else:
            cd.lens = 70
        co = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(co)
        co.location = centre + Vector(loc)
        co.rotation_euler = (centre - co.location).to_track_quat("-Z", "Y").to_euler()
        if name == "top":
            co.rotation_euler = (0, 0, 0)
        scene.camera = co
        p = out_dir / f"{name}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        paths[name] = str(p)
        bpy.data.objects.remove(co, do_unlink=True)
    for lo in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
    for o in hidden:
        o.hide_render = False
    return paths


# ---------------------------------------------------------------------------------------------
# Bake: occlusion and edge wear into a grey colour multiplier and a roughness/metal map
# (no concept projection; maps.json "bake": "model")
# ---------------------------------------------------------------------------------------------

def bake_maps(obj, out_dir, size=1024, samples=48):
    scene = bpy.context.scene
    set_engine(scene, "CYCLES")
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
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
    col_img = bpy.data.images.new("nshi154A_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nshi154A_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
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

        def mth(op, a, b=None):
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
        ao_s.only_local = True  # this hull alone (main also drops the factory scene's cube)
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.only_local = True
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.2
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            v = mth("MINIMUM", mth("ADD", mth("ADD", 0.5, mth("MULTIPLY", occl, 0.6)), mth("MULTIPLY", edge, 0.18)), 1.0)
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.15)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
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
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
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


# ---------------------------------------------------------------------------------------------

def build_outline_shell(coll, NT=96):
    """The outline shell (D51) built from the dome's own smooth surface: the cap without its grooves,
    ribs, flange and bolts, closed by the round belly and the flat north wall, smooth shaded. A voxel shell
    held inside the hull with a shrinkwrap folded over the 0.8 px grooves and the rib edges, and its
    flipped faces drew as black scribbles in the outline pass; this one has no folds and lies on or
    under the hull everywhere, so only its silhouette draws."""
    M = Mesh()
    stations = [k / 10 for k in range(1, 9)] + [0.86, 0.91, 0.95, 0.975, 0.99, 1.0]
    grid, lows = [], []
    for i in range(NT):
        a = 2 * math.pi * i / NT
        dx, dy = math.cos(a), math.sin(a)
        Rr = rim_dist(dx, dy)
        ring, low = [], []
        for st in stations:
            x, y = POLE[0] + dx * st * Rr, POLE[1] + dy * st * Rr
            ring.append(M.v(Vector((x, y, ZE if st >= 1.0 else z_at(x, y)))))
            if st < 1.0:
                low.append(M.v(Vector((x, y, zl_at(x, y)))))
        grid.append(ring)
        lows.append(low + [ring[-1]])
    pole = M.v(Vector((POLE[0], POLE[1], z_at(*POLE))))
    keel = M.v(Vector((POLE[0], POLE[1], zl_at(*POLE))))
    for i in range(NT):
        j = (i + 1) % NT
        M.f((pole, grid[i][0], grid[j][0]), 0)
        for k in range(len(stations) - 1):
            M.f((grid[i][k], grid[i][k + 1], grid[j][k + 1], grid[j][k]), 0)
        M.f((keel, lows[j][0], lows[i][0]), 0)
        for k in range(len(stations) - 1):
            M.f((lows[i][k], lows[j][k], lows[j][k + 1], lows[i][k + 1]), 0)
    bm = M.bm
    cut_north(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = 0
    for e in bm.edges:
        e.smooth = True
    me = bpy.data.meshes.new(f"{NAME}_outline")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell = bpy.data.objects.new(f"{NAME}_outline", me)
    coll.objects.link(shell)
    me.shade_smooth()
    shell["tyrian_outline"] = True
    return shell


def cut_cap(bm, xs, side, eps=0.04, depth=0.4):
    """A clean flat cap for a piece's cut at sprite x = xs: the nose's cross-section there (upper half
    and belly), pulled `depth` px in (under the grooves, flange and ribs) and `eps` px back into
    the piece (`side` -1: the piece lies west of the cut), so it never shows from outside or meets
    the neighbour's cap. One face, its own vertices: flat, split normals."""
    x = xs + side * eps
    top, low = [], []
    for k in range(0, 400):
        y = 0.12 + k * 0.1
        if s_at(x, y) >= 1.0:
            break
        zu, zl = z_at(x, y) - depth, zl_at(x, y) + depth
        if zu - zl < 0.12:
            break
        top.append((y, zu))
        low.append((y, zl))
    if len(top) < 3:
        return []
    loop = top + list(reversed(low))
    vs = [bm.verts.new(W(x, y, z)) for y, z in loop]
    f = bm.faces.new(vs)
    f.material_index = SHELL
    f.normal_update()
    if (f.normal.x > 0) != (side < 0):
        f.normal_flip()
    f.smooth = False
    return vs


# Each piece closes its cuts with an inset cap (cut_cap), so it stays a closed shape when its
# neighbour is gone; with the neighbour there the cap is out of sight.
CAP_CUTS = True


def split_pieces(obj, layout, coll, cap=True, transfer_normals=True):
    """common.split_assembly without its holes_fill caps (on this layered hull they overlapped and
    left jagged, non-planar caps and smoothed normals along the cut): bisect each piece's box and
    add one clean inset cap per cut that has a neighbour (cut_cap; `cap`), welded to nothing so its
    normals are flat; the vertices on the cut take the whole hull's normals. The outline shells
    are left open at the cuts (a capped shell drew its cap as an ink line across the dome)."""
    result = {}
    centres = {(round(cx), round(cy)) for _, cx, cy in layout}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        caps = []
        if cap:
            xs = cx + 36  # sprite x of the piece's centre (assembly origin = sprite x 36)
            for side in (-1, 1):
                if (round(cx + side * 24), round(cy)) in centres:
                    caps += cut_cap(bm, xs + side * 12, -side)
        bm.verts.index_update()
        cap_ids = {v.index for v in caps}
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        if transfer_normals:
            # The vertices on a cut take the whole hull's normals (not ones averaged over one side of
            # the cut only), so neighbouring pieces shade as one surface across the cut.
            vg = piece.vertex_groups.new(name="hull")
            on_cut = [v.index for v in mesh.vertices if v.index not in cap_ids
                      and min(abs(v.co.x - x0 - hw), abs(v.co.x - x0 + hw)) < 1e-5]
            vg.add(on_cut, 1.0, "REPLACE")
            dt = piece.modifiers.new("normals", "DATA_TRANSFER")
            dt.object = obj
            dt.use_loop_data = True
            dt.data_types_loops = {"CUSTOM_NORMAL"}
            dt.loop_mapping = "POLYINTERP_NEAREST"
            dt.vertex_group = "hull"
            common._apply_modifiers(piece)
            piece.vertex_groups.clear()
        mesh.transform(Matrix.Translation((-x0, -y0, 0)))
        result[name] = piece
    return result


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for n in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa: E731
    sprite = merged_sprite()
    # --factory-startup's default cube (2 units = 24 px wide, at the origin) sat inside the hull from
    # sprite x 24 to 48, exactly the middle piece: the AO bake drew its walls as two dark bands down
    # the dome that read as seams at the piece cuts.
    for o in bpy.context.view_layer.objects:
        o.select_set(o.type == "MESH")
    if bpy.context.selected_objects:
        bpy.ops.object.delete()
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    print(f"model: {len(obj.data.polygons)} faces, {tris(obj)} triangles")
    if arg("--measure"):
        measure([obj], arg("--measure"))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bdir = Path(tempfile.mkdtemp())  # the PNGs are only a stop on the way into the glb
        bake_maps(obj, bdir)
        fmt = "WEBP"
    if arg("--views"):
        render_views([obj], arg("--views"))
    if "--no-export" in argv:
        return
    # The outline shell from the smooth dome itself (build_outline_shell): common.outline_shell's voxel
    # shell, even held inside with inside=0.02, folded over the grooves and rib edges (the D88 crack:
    # black scribbles along them in the game's outline pass).
    shell = build_outline_shell(coll)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]]
    parts = split_pieces(obj, layout, coll, cap=CAP_CUTS)
    shells = split_pieces(shell, layout, coll, cap=False, transfer_normals=False)
    out_objs = []
    for name, cx, cy in layout:
        p, sh = parts[name], shells[name]
        sh.name = f"{name}_outline"
        sh["tyrian_outline"] = True
        print(f"piece {name}: {tris(p)} triangles, outline {len(sh.data.polygons)} faces")
        out_objs += [p, sh]
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [parts[name], shells[name]], f"enemies/{name}", data["sprites"], image_format=fmt)
    if arg("--glb"):  # the whole assembly (each piece at its place) for the measure and view scripts
        for name, cx, cy in layout:
            for o in (parts[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
        common.export_glb(out_objs, Path(arg("--glb")), image_format=fmt)


if __name__ == "__main__":
    main()
