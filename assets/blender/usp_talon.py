"""USP Talon, the player's starting ship and the game's flagship model (ship sprite 233 in
tyrian.shp#8, banking frames 229-237), shown large and turning in the menus and from the tilted game
camera in play (DECISIONS.md D50).

A hard-surface build from the multi-view blueprint drawn for it (top, side, front, rear and
underside views with dimensions in sprite px) and the top-down concept
(assets/blender/features/concepts/ship-usp-talon-light-fighter.jpg), inside the sprite's outline
(the hitbox read): a faceted chisel nose with a split raised spine, a framed dark canopy with a
cross frame, two big engine nacelles with a machined (chamfered, filleted octagon) section, armour
petals over their front domes and a deep blackened seam, bolted-on outboard armour caps, a banded
rear body with grilles, engine housings with vents and two deep glowing nozzles, a boat-tail
plate; underneath a keel, chin cannons, nacelle intakes, ventral pylons and gear doors.

How it is built:
- Every part is a low-poly cage in sprite px (x = column - 12, y = sprite row, aft is +y, z up),
  moved to Blender at the end (X = x / 12, Y = (14 - y) / 12, Z = z / 12).
- Sections between the blueprint's stations are monotone cubic (pchip), so lofts never swell.
- The fuselage and the nacelles are dark gunmetal cores covered by separate brass armour plates
  that stand 0.15-0.5 px proud with 45-degree chamfered edges, so panel lines are real gaps with
  depth and edges catch the light. Flat faces are flat (sharp edges by angle, weighted normals);
  only fillets, nacelle domes and glass are smooth. No subdivision, no normal map.
- Texture: no concept projection (texture_bake.py skips this model: "bake": "model" in its
  maps.json). This script bakes its own two small maps with Cycles: ambient occlusion at two scales
  times a light edge lift (colour multiplier), and roughness/metalness (crevices rougher, bevelled
  edges polished). Base Color = map x palette colour, so the palette still sets the colour.
- Materials are palette materials (pal_<index>) so palettes, fades and the hit flash apply; the
  glows and navigation lights are emissive palette colours (orange 121/123, red 118, green 204).
- Exported beside it: an outline shell (common.outline_shell, D51), a smooth closed copy the game
  draws only in its outline pass, so the ink outline is one contour, not whiskers along every hard
  edge; and `tyrian_engines` on the object, where the menu backdrop puts its two engine glows.

    Blender --background --factory-startup --python usp_talon.py -- [--out path.glb] [--no-bake] [--preview png]

Default: export public/models/usp_talon.glb and src/render/spriteModels/usp_talon.json
(common.export_sprite_model). --out writes only that .glb (for render checks); --no-bake leaves
the model plain (fast iterations).
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

NAME = "usp_talon"
SPRITES = [{"sheet": "tyrian.shp#8", "size": 2, "frames": [233], "bank": {"step": 2, "max": 2}}]
MODEL = "ship-usp-talon-light-fighter"
PX = 1 / 12

# Palette colours (tyrian.shp#8's ramp 16-31, reference/models/ship-usp-talon-light-fighter/sprite.json).
PAL = {16: (16, 8, 0), 17: (28, 16, 0), 18: (44, 24, 4), 19: (56, 36, 8), 20: (73, 44, 16),
       21: (85, 60, 24), 22: (101, 73, 32), 23: (113, 85, 44), 24: (125, 101, 56), 25: (142, 113, 69),
       26: (154, 130, 85), 27: (170, 146, 101), 28: (182, 162, 121), 29: (207, 195, 158), 30: (231, 223, 199)}

# Glow colours from the same palette (5): orange, yellow-orange, red, green.
GLOW_PAL = {121: (231, 97, 12), 123: (243, 174, 36), 118: (186, 12, 0), 204: (24, 219, 60)}

# Material slots.
BRASS, BRASS_DK, BRASS_LT, GUN, DEEP, GLASS, GLOW, NAV_R, NAV_G, CORE, BRASS_MID, BRASS_POL, FRAME_LT, BELLY = range(14)


def materials():
    """Brass armour a step lighter than the sprite's mid-tone (the game lights it from above and
    the menu from the side), polished nacelles and trim, a darker brass-gunmetal frame; the bake's
    roughness map adds the variation (edges smoother, crevices rougher)."""
    m = common.material

    def glow(i, tag, strength):
        c = common.srgb(*GLOW_PAL[i])
        return m(f"pal_{i}_talon_{tag}", c, metallic=0.0, roughness=0.4, emission=c, emission_strength=strength)
    return [
        m("pal_26_talon_armour", common.srgb(*PAL[26]), metallic=0.8, roughness=0.38),
        m("pal_21_talon_armour_dark", common.srgb(*PAL[21]), metallic=0.75, roughness=0.5),
        m("pal_28_talon_trim", common.srgb(*PAL[28]), metallic=0.95, roughness=0.2),
        m("pal_19_talon_gunmetal", common.srgb(*PAL[19]), metallic=0.7, roughness=0.44),
        m("pal_16_talon_recess", common.srgb(*PAL[16]), metallic=0.3, roughness=0.8),
        m("pal_16_talon_glass", common.srgb(*PAL[16]), metallic=0.0, roughness=0.04),
        glow(121, "engine_glow", 1.6),
        glow(118, "nav_red", 5.0),
        glow(204, "nav_green", 4.0),
        glow(123, "engine_core", 2.2),
        m("pal_24_talon_armour_mid", common.srgb(*PAL[24]), metallic=0.75, roughness=0.45),
        # The nacelles are polished: the sprite's bright pod highlights are sheen on round metal.
        m("pal_26_talon_nacelle", common.srgb(*PAL[26]), metallic=0.9, roughness=0.26),
        # Canopy cross frame and sill lip: mid brass, so it reads against the dark glass.
        m("pal_25_talon_frame", common.srgb(*PAL[25]), metallic=0.6, roughness=0.32),
        # Belly panels: duller (less metallic, rougher) so they take the game's dim ground light
        # instead of mirroring the dark below.
        m("pal_24_talon_belly", common.srgb(*PAL[24]), metallic=0.45, roughness=0.55),
    ]


# --- curves -----------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys): smooth, no overshoot."""
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


def frange(a, b, step):
    """a..b inclusive, evenly, at most `step` apart."""
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


# Fuselage stations from the blueprint (row y, half width, deck z, keel z), sprite px.
FY = [2.0, 3.0, 4.0, 6.0, 9.0, 12.0, 14.0, 16.0, 17.5, 19.3, 22.6, 24.5, 25.4]
FW = pchip(FY, [0.05, 0.62, 1.25, 2.28, 3.05, 3.75, 3.65, 3.1, 2.75, 2.45, 2.45, 2.3, 2.15])
FT = pchip(FY, [0.32, 0.72, 1.10, 1.58, 1.96, 2.12, 2.10, 2.02, 1.96, 1.88, 1.80, 1.55, 1.35])
FB = pchip(FY, [0.22, -0.30, -0.80, -1.50, -2.05, -2.35, -2.43, -2.45, -2.45, -2.45, -2.45, -2.2, -1.95])
DECK = 0.6     # flat deck half width, fraction of the half width
SHOULDER = 0.3  # shoulder chamfer drop, fraction of the height
FLANK = 0.45    # flank bottom above the keel, fraction of the height
CHINE = 0.1     # lower chamfer foot above the keel


def fuselage_loop(y):
    """Closed section: top centre, right deck edge, shoulder, flank, lower chamfer, keel, and back up
    the left side. s = 0 top centre, 1 deck edge, 2 shoulder, 3 flank foot, 4 chine, 5 keel."""
    w, t, b = FW(y), FT(y), FB(y)
    h = t - b
    right = [(0.0, t), (DECK * w, t), (w, t - SHOULDER * h), (w, b + FLANK * h), (DECK * w, b + CHINE * h), (0.0, b)]
    pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return pts, (0.0, (t + b) / 2)


def hull_top(x, y):
    """Height of the fuselage's upper surface (deck or shoulder) at (x, y), core (no plates)."""
    w, t, b = FW(y), FT(y), FB(y)
    ax = abs(x)
    if ax <= DECK * w:
        return t
    return t - SHOULDER * (t - b) * min(1.0, (ax - DECK * w) / ((1 - DECK) * w))


# Engine nacelles: 5.24 x 4.6 px sections on an axis at z -0.25, x 4.9, the front swept in toward
# the cockpit and narrowed to stay inside the sprite (rows 13-16), the tail drawn down and in to a
# round exhaust housing that ends in the nozzle (x 4.15, z -0.85, row 24.9).
_PY = [12.4, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 21.5, 22.3, 23.0, 23.6, 24.0]
POD_CX = pchip(_PY, [3.9, 4.05, 4.28, 4.47, 4.68, 4.88, 4.9, 4.9, 4.8, 4.6, 4.45, 4.4])
POD_CZ = pchip(_PY, [-0.25] * 8 + [-0.27, -0.31, -0.35, -0.37])
POD_RX = pchip(_PY, [0.66, 1.12, 1.45, 1.72, 2.0, 2.42, 2.62, 2.62, 2.5, 2.12, 1.75, 1.5])
POD_RZ = pchip(_PY, [0.58, 1.04, 1.38, 1.7, 1.98, 2.2, 2.3, 2.3, 2.24, 2.02, 1.72, 1.5])
POD_END = 23.45  # the nacelle's aft bulkhead; the rear shell overhangs it


def fillet(corners, radius, k=3):
    """Round each corner of a closed polygon with an arc of `radius` (k segments); radius and k
    may be lists, one per corner."""
    n = len(corners)
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * n
    ks = k if isinstance(k, (list, tuple)) else [k] * n
    out = []
    for i in range(n):
        p0, p1, p2 = corners[i - 1], corners[i], corners[(i + 1) % n]
        d1 = (p0[0] - p1[0], p0[1] - p1[1])
        d2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*d1), math.hypot(*d2)
        d1 = (d1[0] / l1, d1[1] / l1)
        d2 = (d2[0] / l2, d2[1] / l2)
        ang = math.acos(max(-0.999, min(0.999, d1[0] * d2[0] + d1[1] * d2[1])))
        t = min(radii[i] / math.tan(ang / 2), 0.45 * l1, 0.45 * l2)
        a = (p1[0] + d1[0] * t, p1[1] + d1[1] * t)
        b = (p1[0] + d2[0] * t, p1[1] + d2[1] * t)
        for j in range(ks[i] + 1):  # a quadratic Bezier through the corner: close to the arc
            u = j / ks[i]
            out.append(((1 - u) ** 2 * a[0] + 2 * u * (1 - u) * p1[0] + u * u * b[0],
                        (1 - u) ** 2 * a[1] + 2 * u * (1 - u) * p1[1] + u * u * b[1]))
    return out


def _pod_unit():
    """The nacelle section, normalised to half sizes 1 x 1 (u outboard, v up): a chamfered
    rectangle (octagon) with filleted corners, the outboard-top ones the largest, so the shell has a
    flat top, flanks and belly and reads machined, not inflated. Starts on the top flat's inboard
    end and runs outboard (k = 0 top, then outboard, bottom, inboard)."""
    a, b = 2.6, 2.3
    ca, cb = 0.42 * a, 0.40 * b
    corners = [(-a + ca, b), (a - ca * 1.15, b), (a, b - cb * 1.15), (a, -b + cb), (a - ca, -b),
               (-a + ca, -b), (-a, -b + cb), (-a, b - cb)]
    pts = fillet(corners, (1.15, 1.7, 1.7, 1.35, 1.05, 1.05, 0.9, 1.1), (2, 3, 3, 2, 2, 2, 2, 2))
    return [(u / a, v / b) for u, v in pts]


POD_UNIT = _pod_unit()
POD_N = len(POD_UNIT)


def pod_s(deg):
    """Loop parameter (vertex index + fraction) where the ray at `deg` degrees from straight up,
    toward outboard (negative: inboard), meets the nacelle section."""
    t = math.radians(deg % 360)
    dx, dz = math.sin(t), math.cos(t)
    best = None
    for i in range(POD_N):
        (ax, az), (bx, bz) = POD_UNIT[i], POD_UNIT[(i + 1) % POD_N]
        ex, ez = bx - ax, bz - az
        den = dx * ez - dz * ex
        if abs(den) < 1e-12:
            continue
        r = (ax * ez - az * ex) / den
        u = (ax * dz - az * dx) / den
        if r > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or r < best[0]):
            best = (r, i + u)
    return best[1] - (POD_N if deg < 0 else 0)


def pod_loop(y, side=1, grow=0.0):
    cx, cz = side * POD_CX(y), POD_CZ(y)
    rx, rz = POD_RX(y) + grow, POD_RZ(y) + grow
    return [(cx + side * rx * u, cz + rz * v) for u, v in POD_UNIT], (cx, cz)


# --- mesh building ----------------------------------------------------------------------------

class Part:
    """A bmesh in sprite px with an outward hint per face, oriented when finished."""

    def __init__(self, name, smooth_angle=30.0):
        self.name = name
        self.bm = bmesh.new()
        self.hints = []
        self.smooth_angle = smooth_angle

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, verts, mat, out=None, away=None):
        if len({id(v) for v in verts}) < 3:
            return None
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = mat
        self.hints.append((face, out, away))
        return face

    def orient(self):
        for face, out, away in self.hints:
            if not face.is_valid:
                continue
            face.normal_update()
            c = face.calc_center_median()
            d = Vector(out) if out is not None else c - Vector(away)
            if face.normal.dot(d) < 0:
                face.normal_flip()


def offset_loop(pts, centre):
    """Per-vertex outward miter normals (unit length / cos half angle) and per-segment normals."""
    n = len(pts)
    seg = []
    for i in range(n):
        (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % n]
        dx, dz = x1 - x0, z1 - z0
        ln = math.hypot(dx, dz) or 1e-9
        nx, nz = dz / ln, -dx / ln
        mx, mz = (x0 + x1) / 2 - centre[0], (z0 + z1) / 2 - centre[1]
        if nx * mx + nz * mz < 0:
            nx, nz = -nx, -nz
        seg.append((nx, nz, ln))
    vert = []
    for i in range(n):
        ax, az, _ = seg[i - 1]
        bx, bz, _ = seg[i]
        sx, sz = ax + bx, az + bz
        ln = math.hypot(sx, sz) or 1e-9
        ux, uz = sx / ln, sz / ln
        cos_half = max(0.35, ux * bx + uz * bz)
        vert.append((ux / cos_half, uz / cos_half))
    return vert, seg


class Section:
    def __init__(self, loopf, y):
        self.y = y
        self.pts, self.centre = loopf(y)
        self.n = len(self.pts)
        self.vn, self.sn = offset_loop(self.pts, self.centre)

    def at(self, s, off):
        n = self.n
        i = math.floor(s + 1e-9)
        f = s - i
        i %= n
        if f < 1e-6:
            (x, z), (nx, nz) = self.pts[i], self.vn[i]
        else:
            (x0, z0), (x1, z1) = self.pts[i], self.pts[(i + 1) % n]
            x, z = x0 + (x1 - x0) * f, z0 + (z1 - z0) * f
            nx, nz, _ = self.sn[i]
        return (x + nx * off, self.y, z + nz * off)

    def tangent(self, s):
        i = math.floor(s + 1e-9) % self.n
        (x0, z0), (x1, z1) = self.pts[i], self.pts[(i + 1) % self.n]
        ln = math.hypot(x1 - x0, z1 - z0) or 1e-9
        return ((x1 - x0) / ln, 0.0, (z1 - z0) / ln)

    def seglen(self, s):
        return self.sn[math.floor(s + 1e-9) % self.n][2]


def loft(part, loopf, ys, mat, cap0=True, cap1=True):
    """A closed tube through loopf's sections at ys (a core hull)."""
    rings = []
    for y in ys:
        sec = Section(loopf, y)
        rings.append(([part.v((x, y, z)) for x, z in sec.pts], (sec.centre[0], y, sec.centre[1])))
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            part.f((r0[i], r0[j], r1[j], r1[i]), mat, away=c0)
    if cap0:
        part.f(rings[0][0], mat, out=(0, -1, 0))
    if cap1:
        part.f(rings[-1][0], mat, out=(0, 1, 0))


def loft_rings(part, rings, mats, cap0=True, cap1=True):
    """A closed tube through `rings` [(loopf, y, grow)], where loopf(y, grow) gives the section;
    mats[i] is the material between ring i and i + 1. Two rings at the same y make a step (a groove
    wall), oriented toward +y if the later ring is the smaller."""
    built = []
    for loopf, y, grow in rings:
        pts, (cx, cz) = loopf(y, grow)
        built.append(([part.v((x, y, z)) for x, z in pts], (cx, y, cz), y, grow))
    for i, ((r0, c0, y0, g0), (r1, c1, y1, g1)) in enumerate(zip(built, built[1:])):
        n = len(r0)
        for a in range(n):
            b = (a + 1) % n
            if abs(y1 - y0) < 1e-6:
                part.f((r0[a], r0[b], r1[b], r1[a]), mats[i], out=(0, 1 if g1 < g0 else -1, 0))
            else:
                part.f((r0[a], r0[b], r1[b], r1[a]), mats[i], away=c0)
    if cap0:
        part.f(built[0][0], mats[0], out=(0, -1, 0))
    if cap1:
        part.f(built[-1][0], mats[-1], out=(0, 1, 0))


def plate(part, loopf, y0, y1, mat, s0=None, s1=None, d=0.2, c=0.12, depth=0.3, ystep=0.7,
          ch0=True, ch1=True):
    """An armour plate standing `d` proud of loopf's surface, from row y0 to y1 and (open plates)
    from loop parameter s0 to s1 (s = vertex index + fraction; may run below 0 to wrap), with 45-degree
    chamfered edges `c` wide and a skirt down to `depth` under the surface. Without s0/s1 the plate
    wraps all the way round (its ends chamfered if ch0/ch1)."""
    closed = s0 is None
    c = min(c, (y1 - y0) / 3)
    ys = [y0]
    if ch0:
        ys.append(y0 + c)
    a, b = (y0 + c if ch0 else y0), (y1 - c if ch1 else y1)
    mids = frange(a, b, ystep)
    ys += mids[1:-1]
    if ch1:
        ys.append(y1 - c)
    ys.append(y1)
    secs = [Section(loopf, y) for y in ys]
    n = secs[0].n
    grid = []
    for ri, sec in enumerate(secs):
        border_r = (ri == 0 and ch0) or (ri == len(secs) - 1 and ch1)
        if closed:
            cols = [(float(k), False) for k in range(n)]
        else:
            ca = min(c / sec.seglen(s0), 0.45 * (math.floor(s0 + 1) - s0))
            cb = min(c / sec.seglen(s1 - 1e-6), 0.45 * (s1 - math.ceil(s1 - 1)))
            inner = [float(k) for k in range(math.floor(s0 + ca) + 1, math.ceil(s1 - cb))]
            cols = [(s0, True), (s0 + ca, False)] + [(k, False) for k in inner] + [(s1 - cb, False), (s1, True)]
        row = []
        for s, border_c in cols:
            off = d - c if (border_r or border_c) else d
            row.append((part.v(sec.at(s, off)), s))
        grid.append(row)
    # Columns must match from row to row (open plates: the same integers inside every row).
    lens = {len(r) for r in grid}
    if len(lens) != 1:
        raise ValueError(f"plate {y0}-{y1} {s0}-{s1}: uneven columns {lens}")
    k = len(grid[0])
    for ri in range(len(grid) - 1):
        sec = secs[ri]
        away = (sec.centre[0], sec.y, sec.centre[1])
        for ci in range(k if closed else k - 1):
            cj = (ci + 1) % k
            part.f((grid[ri][ci][0], grid[ri][cj][0], grid[ri + 1][cj][0], grid[ri + 1][ci][0]), mat, away=away)
    # Skirts.
    def skirt(chain, outs):
        low = []
        for (vert, s), sec in chain:
            low.append(part.v(sec.at(s, -depth)))
        for i in range(len(chain) - 1):
            part.f((chain[i][0][0], chain[i + 1][0][0], low[i + 1], low[i]), mat, out=outs[i])
    if closed:
        for ri, o in ((0, (0, -1, 0)), (len(grid) - 1, (0, 1, 0))):
            if (ri == 0 and not ch0) or (ri and not ch1):
                pass
            chain = [(grid[ri][ci], secs[ri]) for ci in range(k)] + [(grid[ri][0], secs[ri])]
            skirt(chain, [o] * k)
    else:
        top = [(grid[0][ci], secs[0]) for ci in range(k)]
        bot = [(grid[-1][ci], secs[-1]) for ci in range(k)]
        left = [(grid[ri][0], secs[ri]) for ri in range(len(grid))]
        right = [(grid[ri][-1], secs[ri]) for ri in range(len(grid))]
        skirt(top, [(0, -1, 0)] * k)
        skirt(bot, [(0, 1, 0)] * k)
        skirt(left, [tuple(-t for t in secs[ri].tangent(s0)) for ri in range(len(grid))])
        skirt(right, [secs[ri].tangent(s1 - 1e-6) for ri in range(len(grid))])
    return grid


def hull(part, points, mat, merge_angle=1.0):
    """The convex hull of points (a chamfered block), coplanar triangles merged."""
    bm = part.bm
    verts = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(merge_angle), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    centre = sum((Vector(p) for p in points), Vector()) / len(points)
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat
        part.hints.append((f, None, tuple(centre)))


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None):
    """Corner points of a box with chamfered edges (for hull())."""
    chz = ch if chz is None else chz
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(x + sx * ch, y, z + sz * chz), (x, y + sy * ch, z + sz * chz), (x + sx * ch, y + sy * ch, z)]
    return pts


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Sprite px to Blender: X = x / 12, Y = (14 - y) / 12, Z = z / 12 (a reflection in y).
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


# --- the ship ---------------------------------------------------------------------------------

def build_fuselage(P):
    ys = [2.0, 2.3, 2.7] + frange(3.2, 25.4, 0.9)
    loft(P, fuselage_loop, ys, GUN, cap0=False)
    L = fuselage_loop
    # Nose cone, all round, its back edge chamfered.
    plate(P, L, 2.3, 4.15, BRASS, d=0.2, ch0=False, ystep=0.35)
    # Its tip: a polished point over the plate's front edge.
    sec = Section(L, 2.3)
    tip = [sec.at(k, 0.2) for k in range(sec.n)]
    hull(P, tip + [(0.0, 2.02, (FT(2.0) + FB(2.0)) / 2)], BRASS_LT)
    # Deck, shoulders, flanks, belly: plates with gaps between them (panel lines). The concept's
    # nose panels (inner either side of the spine, outer split at row 8.5) are thick, set into the
    # hull, so the dark substructure shows in the gaps.
    for y0, y1 in ((9.5, 17.35), (17.5, 19.15)):
        plate(P, L, y0, y1, BRASS, s0=-0.9, s1=0.9)
    for side in (1, -1):
        def S(a, b):
            return (a, b) if side > 0 else (10 - b, 10 - a)
        plate(P, L, 4.3, 9.35, BRASS, *S(0.13, 0.9), d=0.34, c=0.15)
        for y0, y1, mat in ((4.3, 8.4, BRASS), (8.55, 12.2, BRASS_MID), (12.35, 16.0, BRASS_MID)):
            plate(P, L, y0, y1, mat, *S(0.95, 2.55), d=0.3, c=0.15)
        for y0, y1 in ((4.4, 8.9, ), (9.05, 12.25), (12.4, 16.5)):
            plate(P, L, y0, y1, BRASS_DK, *S(2.6, 4.25))
        # Rear shoulders behind the canopy, partly inside the nacelles.
        plate(P, L, 16.15, 19.15, BRASS, *S(0.95, 2.6))
        plate(P, L, 22.65, 25.25, BRASS, *S(0.95, 2.6))
    # Reaction-control ports on the nose flanks: dark recessed blocks, two a side.
    for side in (1, -1):
        for y0 in (5.6, 6.5):
            y1 = y0 + 0.55
            w = FW(y0 + 0.3)
            sec, _ = fuselage_loop(y0 + 0.3)
            zc = (sec[2][1] + sec[3][1]) / 2
            hull(P, [(side * x, y, z) for x, y, z in cbox(w - 0.2, w + 0.3, y0, y1, zc - 0.22, zc + 0.22, 0.06)], DEEP)
    # Ventral keel strake: a low gunmetal fin along the centre line aft of the nose gear door.
    pts = []
    for y in (16.8, 18.0, 21.0, 23.6):
        b = FB(y) - 0.12
        drop = 0.45 if 17.0 < y < 22.0 else 0.1
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.32, b + 0.4), (0.22, b - drop), (0.1, b - drop - 0.08))]
    hull(P, pts, GUN)
    # Belly: brass panels along the keel (lighter than the flanks, so the belly reads under the
    # game's dark ground light), and the nose gear door on the V keel, proud, with hinge blocks.
    for y0, y1 in ((4.6, 8.7), (8.85, 12.6), (16.75, 21.0), (21.15, 25.0)):
        plate(P, L, y0, y1, BELLY, s0=4.3, s1=5.7, d=0.15)
    plate(P, L, 12.75, 16.6, BRASS, s0=4.35, s1=5.65, d=0.3, c=0.12, ystep=0.6)
    for sx in (-1, 1):
        sec, _ = fuselage_loop(13.4)
        x4, z4 = sec[4]
        hull(P, [(sx * x, y, z) for x, y, z in cbox(x4 * 0.55, x4 * 0.55 + 0.32, 13.0, 13.7, z4 - 0.75, z4 - 0.1, 0.06)], GUN)
        hull(P, [(sx * x, y, z) for x, y, z in cbox(x4 * 0.55, x4 * 0.55 + 0.32, 15.6, 16.3, z4 - 0.75, z4 - 0.1, 0.06)], GUN)
    # Belts between the nacelles (thick polished straps) with a grille between them.
    for y0, y1 in ((19.3, 20.15), (21.6, 22.45)):
        plate(P, L, y0, y1, BRASS_LT, s0=-2.7, s1=2.7, d=0.36, c=0.1, ystep=1)
    for yc in (20.45, 20.85, 21.25):
        plate(P, L, yc - 0.09, yc + 0.09, BRASS_DK, s0=-2.4, s1=2.4, d=0.16, c=0.04, ystep=1)
    # Rear hatch.
    plate(P, L, 22.65, 25.25, BRASS, s0=-0.9, s1=0.9)


def build_spine(P):
    # Raised spine on the nose: two chamfered polished strips from row 4.4 into the canopy frame,
    # split down the middle by a dark groove (the core shows between them).
    for sx in (-1, 1):
        pts = []
        for y in frange(4.5, 10.2, 0.6):
            hw = 0.3 + 0.24 * min(1.0, (y - 4.5) / 3.0)
            rise = 0.42 * min(1.0, (y - 4.5) / 1.3)
            top = FT(y) + 0.4 + rise
            ch = 0.12
            pts += [(sx * 0.07, y, top), (sx * (hw - ch), y, top), (sx * hw, y, top - ch), (sx * hw, y, FT(y) - 0.3),
                    (sx * 0.07, y, FT(y) - 0.3)]
        hull(P, pts, BRASS_LT)
    # Dorsal conduit behind the canopy: gunmetal box with a polished ridge on top.
    pts = []
    for y in (16.6, 19.25):
        top = FT(y) + 0.5
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.7, top - 0.12), (0.58, top), (0.7, FT(y) - 0.3))]
    hull(P, pts, GUN)
    pts = []
    for y in (16.8, 19.0):
        top = FT(y) + 0.68
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.26, top - 0.08), (0.18, top), (0.26, FT(y) + 0.3))]
    hull(P, pts, BRASS_LT)
    # Blade antenna on the conduit, swept back.
    pts = []
    for y, z0, z1 in ((18.05, FT(18.05) + 0.6, FT(18.05) + 0.62), (18.75, FT(18.75) + 0.6, FT(18.75) + 1.35)):
        pts += [(sx * 0.06, y, z) for sx in (-1, 1) for z in (z0, z1)]
    pts += [(sx * 0.06, 19.05, FT(19.05) + 1.35) for sx in (-1, 1)] + [(sx * 0.06, 19.1, FT(19.1) + 0.6) for sx in (-1, 1)]
    hull(P, pts, GUN)


# Canopy: glass edge outline in plan (sprite px), peak behind the middle.
CAN_Y0, CAN_Y1, CAN_YC, CAN_W = 10.0, 16.45, 13.75, 2.02
CAN_N = 40


def canopy_outline(grow=0.0):
    pts = []
    for k in range(CAN_N):
        a = 2 * math.pi * k / CAN_N  # 0 = right, pi/2 = forward
        c, s = math.cos(a), math.sin(a)
        if s >= 0:   # front half: long, narrowing to a rounded point
            n = 2.1
            b = CAN_YC - CAN_Y0
        else:        # rear half: short and squarer
            n = 3.2
            b = CAN_Y1 - CAN_YC
        e = 2 / n
        x = CAN_W * math.copysign(abs(c) ** e, c)
        yv = math.copysign(abs(s) ** e, s)
        if s > 0:
            x *= 1 - 0.28 * yv ** 2
        y = CAN_YC - b * yv
        pts.append([x, y])
    if grow:
        out = []
        for i in range(CAN_N):
            (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[(i + 1) % CAN_N]
            tx, ty = x2 - x0, y2 - y0
            ln = math.hypot(tx, ty)
            nx, ny = ty / ln, -tx / ln
            if nx * x1 + ny * (y1 - CAN_YC) < 0:
                nx, ny = -nx, -ny
            out.append([x1 + nx * grow, y1 + ny * grow])
        pts = out
    return pts


def deck_top(y):
    return FT(y) + 0.2


GLASS_BASE = 0.32
GLASS_H = 1.25


def build_canopy(P):
    C = canopy_outline()
    # Glass: rings scaled toward the peak, height a rounded dome.
    K = 9
    rings = []
    for k in range(K + 1):
        r = 1 - k / K * 0.97
        ring = []
        for x, y in C:
            px, py = x * r, CAN_YC + (y - CAN_YC) * r
            z = deck_top(py) + GLASS_BASE + GLASS_H * (1 - r ** 2.6) ** 0.55
            ring.append(P.v((px, py, z)))
        rings.append(ring)
    apex = (0.0, CAN_YC, deck_top(CAN_YC) + GLASS_BASE + GLASS_H)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(CAN_N):
            j = (i + 1) % CAN_N
            P.f((r0[i], r0[j], r1[j], r1[i]), GLASS, away=(0, CAN_YC, 0))
    P.f(rings[-1], GLASS, out=(0, 0, 1))
    # The glass's edge goes down under the frame.
    low = [P.v((x, y, deck_top(y) + GLASS_BASE - 0.3)) for x, y in C]
    for i in range(CAN_N):
        j = (i + 1) % CAN_N
        P.f((low[i], low[j], rings[0][j], rings[0][i]), GLASS, out=(C[i][0], C[i][1] - CAN_YC, 0))
    return apex


def glass_z(x, y):
    """Height of the glass at plan point (x, y): find the ring scale r by ray casting the outline."""
    C = canopy_outline()
    dx, dy = x, y - CAN_YC
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        r = 0.0
    else:
        ux, uy = dx / dist, dy / dist
        R = None
        for i in range(CAN_N):
            (ax, ay), (bx, by) = C[i], C[(i + 1) % CAN_N]
            ay -= CAN_YC
            by -= CAN_YC
            ex, ey = bx - ax, by - ay
            den = ux * ey - uy * ex
            if abs(den) < 1e-12:
                continue
            t = (ax * ey - ay * ex) / den
            u = (ax * uy - ay * ux) / den
            if t > 0 and -1e-6 <= u <= 1 + 1e-6:
                R = t if R is None else min(R, t)
        r = min(1.0, dist / R) if R else 1.0
    return deck_top(y) + GLASS_BASE + GLASS_H * max(0.0, 1 - r ** 2.6) ** 0.55


def build_canopy_frame(P):
    # Sill: a ring from the glass edge out over the deck, flat top, chamfered outer edge.
    inner = canopy_outline(-0.06)
    top_out = canopy_outline(0.3)
    ch_out = canopy_outline(0.46)
    rings = []
    for k in range(CAN_N):
        xi, yi = inner[k]
        xo, yo = top_out[k]
        xc, yc = ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.16
        rings.append([
            P.v((xi, yi, deck_top(yi) + GLASS_BASE - 0.3)),
            P.v((xi, yi, zt)),
            P.v((xo, yo, zt)),
            P.v((xc, yc, zt - 0.16)),
            P.v((xc, yc, hull_top(xc, yc) - 0.4)),
        ])
    for k in range(CAN_N):
        j = (k + 1) % CAN_N
        cx, cy = top_out[k]
        for i in range(4):
            out = (cx, cy - CAN_YC, 0) if i >= 2 else ((-cx, -(cy - CAN_YC), 0) if i == 0 else (0, 0, 1))
            if i == 2:
                out = (cx * 0.5, (cy - CAN_YC) * 0.5, 1)
            P.f((rings[k][i], rings[j][i], rings[j][i + 1], rings[k][i + 1]), GUN, out=out)
    # Cross frame between windscreen and canopy (blueprint rows 12.0-12.4): a mid-brass bar
    # standing proud of the glass with chamfered edges, so it reads against the dark glass.
    ya, yb, ch = 11.98, 12.46, 0.08
    n = 16
    xs = [-CAN_W * 1.06 + 2 * CAN_W * 1.06 * i / n for i in range(n + 1)]
    rows = []
    for y, dz in ((ya, -0.18), (ya, 0.1), (ya + ch, 0.18), (yb - ch, 0.18), (yb, 0.1), (yb, -0.18)):
        rows.append([P.v((x, y, glass_z(x, y) + dz)) for x in xs])
    outs = [(0, -1, 0), (0, -1, 1), (0, 0, 1), (0, 1, 1), (0, 1, 0)]
    for r in range(5):
        for i in range(n):
            P.f((rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]), FRAME_LT, out=outs[r])


def build_pods(P, D):
    for side in (1, -1):
        def L(y, side=side):
            return pod_loop(y, side)

        def G(y, grow, side=side):
            return pod_loop(y, side, grow)
        # The core, with a deep blackened groove at the blueprint's seam (rows 17.62-18.0)
        # between the front cowl and the rear shell.
        SEAM0, SEAM1 = 17.62, 17.98
        rings = [(G, y, 0.0) for y in frange(12.4, SEAM0, 0.8)]
        rings += [(G, SEAM0, -0.32), (G, SEAM1, -0.32), (G, SEAM1, 0.0)]
        rings += [(G, y, 0.0) for y in frange(SEAM1, POD_END, 0.8)[1:]]
        mats = [GUN] * len(rings)
        for i, (_, y, g) in enumerate(rings[:-1]):
            if y >= SEAM0 - 1e-6 and rings[i + 1][1] <= SEAM1 + 1e-6:
                mats[i] = DEEP
        loft_rings(P, rings, mats)
        # Exhaust housing: a round gunmetal can from the bulkhead to the nozzle.
        def can(y, side=side):
            r = 1.02
            return [(side * 4.15 + side * r * math.cos(math.pi / 2 - 2 * math.pi * k / 16), -0.85 + r * math.sin(math.pi / 2 - 2 * math.pi * k / 16)) for k in range(16)], (side * 4.15, -0.85)
        loft(P, can, [23.2, 24.75], GUN, cap0=False, cap1=False)
        # Aft bulkhead: a dark brass end plate, chamfered, inside the shell's rim.
        pts = []
        for y, k in ((POD_END - 0.05, 0.8), (POD_END + 0.06, 0.8), (POD_END + 0.14, 0.72)):
            ring, (cx, cz) = pod_loop(y, side)
            pts += [(cx + (x - cx) * k, y, cz + (z - cz) * k) for x, z in ring]
        hull(P, pts, BRASS_DK)
        # A raised gunmetal boss on the bulkhead's upper half (above the exhaust can), a panel line
        # round it.
        pts = []
        for y, k in ((POD_END + 0.1, 0.62), (POD_END + 0.24, 0.62), (POD_END + 0.3, 0.55)):
            ring, (cx, cz) = pod_loop(y, side)
            pts += [(cx + (x - cx) * k, y, max(cz + (z - cz) * k, cz + 0.1)) for x, z in ring]
        hull(P, pts, GUN)
        plate(P, can, 23.95, 24.3, BRASS_DK, d=0.12, c=0.05, ystep=1)
        # Front cowl: polished armour petals over the dome (gaps along the section's chamfers and
        # across the dome at row 14.6), the dark core's nose showing as a cap at the tip. Then the
        # thicker rear shell in two panels (a seam along the upper outboard side) with a thick
        # chamfered top plate; the gunmetal core shows in the seams and as the exhaust housing
        # behind the shell, ringed by two bands.
        def A(a, b, gap=0.0):
            return dict(s0=pod_s(a) + gap, s1=pod_s(b) - gap)
        for a, b in ((-48, 57), (57, 133), (133, 224), (224, 312)):
            plate(P, L, 13.2, 14.5, BRASS_POL, **A(a, b, 0.12), d=0.22, c=0.1, ystep=0.4)
        plate(P, L, 14.66, 17.5, BRASS_POL, **A(-136, 57), d=0.22, c=0.12, ystep=0.6)
        plate(P, L, 14.66, 17.5, BRASS_POL, **A(59, 221), d=0.22, c=0.12, ystep=0.6)
        plate(P, L, 18.06, 22.42, BRASS_POL, **A(-121, 56), d=0.3, c=0.12, ystep=0.7)
        plate(P, L, 18.06, 22.42, BRASS_POL, **A(59, 236), d=0.3, c=0.12, ystep=0.7)
        # Aft end cap: a thicker dark brass ring round the shell's tail, behind a panel break, so
        # the tapering rear is not one big smooth surface.
        plate(P, L, 22.56, POD_END + 0.12, BRASS_DK, d=0.38, c=0.12, ystep=0.5)
        plate(P, L, 18.75, 22.3, BRASS, **A(-34, 70), d=0.5, c=0.16, ystep=0.9)
        # Heat louvres at the panel's aft end: a dark grille with three slats across it.
        plate(P, L, 20.85, 21.95, DEEP, **A(-13.5, 46.5), d=0.54, c=0.03, ystep=2)
        for yc in (21.12, 21.4, 21.68):
            plate(P, L, yc - 0.07, yc + 0.07, BRASS_DK, **A(-12.7, 45.7), d=0.62, c=0.03, ystep=2)
        # Gear door under the nacelle (blueprint callout 19): a proud panel on the shell's belly.
        plate(P, L, 18.9, 22.4, BELLY, **A(152, 206), d=0.44, c=0.1, ystep=0.9)
        # Outboard armour cap: a chamfered block on the nacelle's side.
        x0, x1 = 6.75, 8.95
        hull(D, [(side * x, y, z) for x, y, z in cbox(x0, x1, 19.1, 21.97, -1.35, 0.85, 0.42)], BRASS_DK)
        # Its raised face plate.
        hull(D, [(side * x, y, z) for x, y, z in cbox(8.6, 9.0, 19.55, 21.6, -0.95, 0.45, 0.14)], BRASS)
        # Navigation light at the cap's front corner.
        hull(D, [(side * x, y, z) for x, y, z in cbox(8.25, 8.75, 19.02, 19.3, 0.2, 0.55, 0.06)],
             NAV_G if side > 0 else NAV_R)
        # Vent block between the nacelle tail and the body, a grille on top.
        hull(D, [(side * x, y, z) for x, y, z in cbox(1.9, 3.85, 22.3, 24.95, -1.7, 0.95, 0.3)], BRASS_DK)
        hull(D, [(side * x, y, z) for x, y, z in cbox(2.3, 3.45, 22.75, 24.55, 0.7, 1.0, 0.05)], DEEP)
        for yc in (23.0, 23.42, 23.84, 24.26):
            hull(D, [(side * x, y, z) for x, y, z in cbox(2.33, 3.42, yc - 0.09, yc + 0.09, 0.75, 1.12, 0.04)], BRASS_DK)
        # Nozzle: collar, bell, deep glowing throat.
        nx, nz = side * 4.15, -0.85
        prof = [
            (0.85, 24.7, GUN), (0.95, 24.85, GUN), (0.95, 25.2, GUN), (0.85, 25.3, GUN), (0.84, 26.0, GUN),
            (0.7, 26.0, GUN), (0.62, 25.7, GLOW), (0.56, 25.35, CORE), (0.0, 25.35, CORE),
        ]
        rings = []
        for r, y, mat in prof:
            rings.append([D.v((nx + r * math.cos(2 * math.pi * (k + 0.5) / 18), y, nz + r * math.sin(2 * math.pi * (k + 0.5) / 18)))
                          for k in range(18)] if r > 0 else [D.v((nx, y, nz))])
        for i in range(len(prof) - 1):
            r0, r1 = rings[i], rings[i + 1]
            ya, yb = prof[i][1], prof[i + 1][1]
            inside = i >= 5
            for k in range(18):
                kk = (k + 1) % 18
                vs = (r0[k], r0[kk], r1[0]) if len(r1) == 1 else (r0[k], r0[kk], r1[kk], r1[k])
                if len(r1) == 1:
                    D.f(vs, prof[i][2], out=(0, 1, 0))
                elif inside:
                    D.f(vs, prof[i][2], away=(nx + 50 * (r0[k].co.x - nx), (ya + yb) / 2, nz + 50 * (r0[k].co.z - nz)))
                elif abs(prof[i][0] - prof[i + 1][0]) > 0.05 and abs(ya - yb) < 0.01:
                    D.f(vs, prof[i][2], out=(0, 1, 0))
                else:
                    D.f(vs, prof[i][2], away=(nx, (ya + yb) / 2, nz))
        # Intake scoop under the nacelle's front: gunmetal lip, dark mouth.
        cx = side * POD_CX(15.5)
        hull(D, [(cx + side * x, y, z) for x, y, z in cbox(-0.85, 0.85, 14.6, 17.4, -2.55, -1.3, 0.22)], GUN)
        hull(D, [(cx + side * x, y, z) for x, y, z in cbox(-0.62, 0.62, 14.5, 14.75, -2.33, -1.55, 0.05)], DEEP)
        # Ventral pylon under the nacelle-body joint (callout 18): a gunmetal beam, deepest in the
        # middle, its ends and lower edges chamfered.
        pts = []
        for y, bot in ((17.0, -2.45), (17.9, -3.0), (22.2, -3.0), (23.1, -2.45)):
            pts += [(side * x, y, z) for x, z in ((1.75, -1.75), (2.95, -1.75), (2.95, bot + 0.2), (2.75, bot),
                                                   (1.95, bot), (1.75, bot + 0.2))]
        hull(D, pts, GUN)


def build_aft(D):
    # Tail plate: a dark brass boat-tail that closes the rear body, its top sloping down from the
    # hatch to a thin trailing edge between the nozzles, rear corners cut: a tail plate, not a
    # shelf.
    pts = []
    for y, hw, top, bot in ((24.4, 2.5, 1.2, -0.95), (25.15, 2.25, 1.2, -0.85), (26.0, 2.2, 0.3, -0.72),
                            (26.85, 1.45, -0.3, -0.52)):
        ch = min(0.16, (top - bot) / 3)
        for sx in (-1, 1):
            pts += [(sx * hw, y, top - ch), (sx * (hw - ch), y, top), (sx * hw, y, bot + ch * 0.5), (sx * (hw - ch * 0.5), y, bot)]
    hull(D, pts, BRASS_DK)
    # Chevron on the rear hatch.
    for sx in (-1, 1):
        pts = []
        for (x, y) in ((0.0, 23.35), (0.8, 24.2)):
            for dy in (0.0, 0.3):
                for z in (FT(y + dy) + 0.2, FT(y + dy) + 0.38):
                    pts.append((sx * x, y + dy, z))
        hull(D, pts, GUN)
    # Chin fairing and twin cannons under the nose.
    pts = []
    for y in (7.6, 9.5, 12.4):
        b = FB(y)
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.8, b + 0.35), (0.8, b - 0.3), (0.55, b - 0.55))]
    hull(D, pts, GUN)
    for sx in (-1, 1):
        x, z = sx * 0.42, FB(7.6) - 0.28
        prof = [(0.0, 4.75, GUN), (0.22, 4.75, GUN), (0.22, 5.2, GUN), (0.16, 5.3, GUN), (0.16, 8.0, GUN), (0.0, 8.0, GUN)]
        rings = []
        for r, y, mat in prof:
            rings.append([D.v((x + r * math.cos(2 * math.pi * (k + 0.5) / 8), y, z + r * math.sin(2 * math.pi * (k + 0.5) / 8)))
                          for k in range(8)] if r > 0 else [D.v((x, y, z))])
        for i in range(len(prof) - 1):
            r0, r1 = rings[i], rings[i + 1]
            for k in range(8):
                kk = (k + 1) % 8
                if len(r0) == 1:
                    D.f((r0[0], r1[kk], r1[k]), GUN, out=(0, -1, 0))
                elif len(r1) == 1:
                    D.f((r0[k], r0[kk], r1[0]), GUN, out=(0, 1, 0))
                else:
                    D.f((r0[k], r0[kk], r1[kk], r1[k]), GUN, away=(x, (prof[i][1] + prof[i + 1][1]) / 2, z))


def build(coll):
    mats = materials()
    P = Part("talon_hull", smooth_angle=30)
    build_fuselage(P)
    S = Part("talon_spine", smooth_angle=30)
    build_spine(S)
    G = Part("talon_canopy", smooth_angle=50)
    build_canopy(G)
    F = Part("talon_frame", smooth_angle=30)
    build_canopy_frame(F)
    pods2 = Part("talon_pods", smooth_angle=34)
    det = Part("talon_details", smooth_angle=35)
    build_pods(pods2, det)
    build_aft(det)
    objs = [finish(p, mats, coll) for p in (P, pods2, det, S, G, F)]
    for o in objs:
        print("talon part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


def cull_hidden(obj, grid=6, ndirs=48):
    """Delete faces no ray from outside can reach: the cores under the armour plates, buried
    skirts and block faces inside other parts. Keeps the model light and, where the game draws the
    ship translucent (invulnerable), stops hidden layers darkening it. A face stays if any of a grid
    of points on it sees out along any direction in its front hemisphere."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
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
                for t in (0.35, 0.7, 0.92):
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
    print(f"talon: culled {len(dead)} hidden faces of {len(bm.faces)}")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()


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
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

# Materials that get the baked maps, with their roughness (the roughness map holds it, so each
# keeps its own: bare edges a little smoother, crevices rougher).
TEXTURED = (BRASS, BRASS_DK, BRASS_LT, GUN, DEEP, BRASS_MID, BRASS_POL, FRAME_LT, BELLY)


def bake_maps(obj, out_dir, size=1024, samples=96):
    """UV the model (Smart UV Project) and bake two maps with Cycles: a grey colour multiplier
    (ambient occlusion at two scales, so panel gaps and the nacelle roots darken, plus a light
    lift on bevelled edges) and a metallic-roughness map (G roughness, B metallic). Wire them into
    the palette materials: Base Color = map x palette colour, as texture_bake.py does."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:  # Metal GPU when there is one
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("talon: no GPU bake", err)
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

    col_img = bpy.data.images.new("talon_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("talon_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"

    mats = list(me.materials)
    saved = {}
    for i, m in enumerate(mats):
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        N = nt.nodes.new
        L = nt.links.new
        tmp = []

        def node(kind):
            n = N(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            n.use_clamp = op in ("MULTIPLY_ADD",)
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
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
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.36, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            L(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
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

    for i in TEXTURED:
        m = mats[i]
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
    root = common.repo_root(__file__)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    objs = build(coll)
    obj = join(objs, NAME)
    cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"talon: {len(obj.data.polygons)} faces, {tris} triangles")
    # Where the menu backdrop puts its engine glows (src/ui/backdrop.ts): just behind the two
    # nozzles, in glTF axes (x, y up, z aft), with the glow colour (orange, palette 121).
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round(sx * 4.15 * PX, 4), round(-0.85 * PX, 4), round((26.15 - 14) * PX, 4)]
                                                         for sx in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = out.parent if out else root / "assets" / "blender" / "textures" / MODEL / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir)
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(obj, coll, faces=1500)
    print(f"talon: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], NAME, SPRITES, image_format=fmt)
    if "--preview" in argv:
        ref = root / "reference" / "models" / MODEL / "frame-tyrian8-233.png"
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=2)


if __name__ == "__main__":
    main()
