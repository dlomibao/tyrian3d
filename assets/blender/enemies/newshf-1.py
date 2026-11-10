"""Green fighter (newshf.shp frames 1, 3, 5), design A: a hard-surface 3D version of the sprite in
the player ships' / level-1 enemies' style (D50-D53, D65), plan to the inner edge of the ink (D74).

Reading of the sprite (24x28, light from the upper left). It flies nose DOWN the screen, so row 25
is its nose and the top of the picture its tail.
- Frame 3 is the level frame: a shield-shaped body (straight V sides from the wing roots, row 11,
  to the nose at row 25, half width 7.5 -> 0 inside the ink), two swept-back wing blades whose tips
  trail to row 7 (outer edge straight at column 6/20, inner edge a 45-degree line down to the roots
  at row 10-11), a narrow tail block on the centre line (columns 11-15, waisted to 12-14 at rows
  8-9) carrying a pale rear probe (column 13, rows 1-4) and two brown horns canted outward (columns
  10 and 16, rows 3-5) on brown cheek plates (columns 11 and 15, rows 5-7).
- A pale inverted-U frame (row 14 across, columns 11 and 15 down to row 19) round a dark oval with
  a pale glint (columns 12-14, rows 17-20) = a raised cockpit cowl with dark glass (the glint is
  sheen). Two yellow eyes either side of the spine at rows 11-12 (columns 12 and 14) = sensor
  lamps in dark sockets. Brown strips along each wing's root (columns 8-9 / 18, rows 9-11) = the
  wing-root knuckles; orange lamps at both wing roots (rows 10-11); frame 3 also lights a horn lamp
  (row 5, column 10) and a right-wing lamp (row 8, column 19).
- Frames 1 and 5: the ship rolls (its cowl, eyes, probe and horns slide a pixel left on 1, right on
  5: they stand high above the roll axis) while its wing blades and shoulders flex a pixel in
  (both blades a pixel shorter, the body a pixel narrower at rows 11-17, as drawn). Each frame is
  the same parametric build with that frame's plan from its own inner mask, widened by 1/cos(roll)
  and rolled, so the top view lands on the frame's mask. Each frame is its own mesh, bake and
  outline shell, shown on its frame only (common.frame_part, D17).
Colours: each part's median palette index with the darkest shading and brightest highlights left
out: hull 39, spine/deck plates 40, cowl 42, glass 33, probe 44, horns 24, cheeks 23, knuckles 26,
wingtip fences 43, dark intakes/sockets 32, eyes 125, lamps 122.

Coordinates while building: sprite px, x = column edge - 13.5 (the ship's centre line, column 13),
y = row edge (down), z up; shifted by CX to the block's frame, then usp_talon.finish
(X = x / 12, Y = (14 - y) / 12, Z = z / 12).

    blender --background --python newshf-1.py -- [--no-bake] [--views DIR]

Exports public/models/enemies/newshf-1.glb and src/render/spriteModels/newshf-1.json.
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
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, hull, pchip, plate, loft  # noqa: E402

NAME = "newshf-1"
HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies/newshf-1/final")  # bake and view scratch
MODEL = f"enemies/{NAME}"
REPO = WT
PX = 1 / 12
CX = 1.5  # the ship's centre line (column edge 13.5) from the block's centre (12)

# Material slots and their palette indices.
(HULL, DECK, SPINE, COWL, GLASS, EYE, LAMP, HORN, CHEEK, STRIP, PROBE, DARK, FENCE, BELLY) = range(14)
# Medians of the sprite pixels under each part from straight above (frames 1/3/5, darkest and
# brightest fifth left out): hull 38-39, deck and spine plates 38-40, cowl 41.5-42, fence 43,
# horns 23.5-24, cheeks 23-24, knuckles 26, glass 33, probe 44.
PAL_OF = {HULL: 39, DECK: 40, SPINE: 40, COWL: 42, GLASS: 33, EYE: 125, LAMP: 122, HORN: 24,
          CHEEK: 23, STRIP: 26, PROBE: 44, DARK: 32, FENCE: 43, BELLY: 38}
TEXTURED = (HULL, DECK, SPINE, COWL, HORN, CHEEK, STRIP, PROBE, DARK, FENCE, BELLY)
TINT = (0.97, 0.98, 1.0)

# --- per-frame plan --------------------------------------------------------------------------------
# Hull half widths left and right (knots at the middle of each run of equal width in the frame's
# inner mask, the run's half width; the nose is common), the wing blades' outer edge, the horn tips'
# |x| and the roll (degrees, + = top to the left).
_NOSE = [(21.0, 2.5), (23.0, 1.5), (24.3, 0.82), (24.9, 0.45), (25.35, 0.06)]
_F3 = [(11.0, 7.5), (11.5, 7.28), (13.0, 6.5), (15.0, 5.5), (17.0, 4.5), (19.0, 3.5)] + _NOSE
# Frames 1/5: knots at row centres, each a quarter pixel or more inside the row's run (rows 11 | 12-13
# | 14-16 | 17-19 | 20-21 on the left, 11 | 12-14 | 15-17 | 18-19 | 20-21 on the right).
_TAIL = [(22.5, 1.75), (23.5, 1.25), (24.3, 0.82), (24.9, 0.45), (25.35, 0.06)]
_RL = [(11.0, 6.7), (11.5, 6.4), (12.5, 5.75), (13.5, 5.25), (14.5, 4.85), (15.5, 4.5), (16.5, 4.15),
       (17.5, 3.8), (18.5, 3.5), (19.5, 3.15), (20.5, 2.75), (21.5, 2.25)] + _TAIL
_RR = [(11.0, 6.7), (11.5, 6.4), (12.5, 5.8), (13.5, 5.45), (14.5, 5.1), (15.5, 4.8), (16.5, 4.5),
       (17.5, 4.15), (18.5, 3.75), (19.5, 3.25), (20.5, 2.75), (21.5, 2.25)] + _TAIL
FRAMES = {
    3: dict(roll=0.0, L=_F3, R=_F3, wing_out=7.5, wing_in=0.0, horn=(3.1, 3.1), probe=0.0),
    1: dict(roll=20.0, L=_RL, R=_RR, wing_out=6.4, wing_in=0.65, horn=(1.3, 2.8), probe=-0.45),
    5: dict(roll=-20.0, L=_RL, R=_RR, wing_out=6.4, wing_in=0.65, horn=(2.8, 1.3), probe=0.45),
}
F = dict(FRAMES[3])
PIVOT_Z = 0.5
DOWN_TRIM = 0.35


def plan_curve(knots):
    k = knots
    return pchip([a for a, _ in k], [b for _, b in k])


def set_frame(frame):
    F.clear()
    F.update(FRAMES[frame])
    hl, hr = plan_curve(F["L"]), plan_curve(F["R"])
    # The side that rolls down shows its low edge and belly a little further out: trim it.
    F["trim"] = (DOWN_TRIM if F["roll"] < 0 else 0.0, DOWN_TRIM if F["roll"] > 0 else 0.0)
    F["hl"] = lambda y: max(0.04, hl(y) - F["trim"][0] * min(1.0, hl(y) / 1.5))
    F["hr"] = lambda y: max(0.04, hr(y) - F["trim"][1] * min(1.0, hr(y) / 1.5))


def materials(sprite, frame):
    def pal(slot, tag, metallic, roughness, emission=0.0):
        return common.palette_material(sprite, PAL_OF[slot], f"{NAME}A_f{frame}_{tag}", metallic=metallic,
                                       roughness=roughness, emission_strength=emission)
    return [
        pal(HULL, "hull", 0.3, 0.42),
        pal(DECK, "deck", 0.3, 0.38),
        pal(SPINE, "spine", 0.32, 0.36),
        pal(COWL, "cowl", 0.3, 0.36),
        pal(GLASS, "glass", 0.0, 0.07),
        pal(EYE, "eye", 0.0, 0.4, 2.0),
        pal(LAMP, "lamp", 0.0, 0.4, 1.2),
        pal(HORN, "horn", 0.25, 0.42),
        pal(CHEEK, "cheek", 0.25, 0.45),
        pal(STRIP, "strip", 0.25, 0.4),
        pal(PROBE, "probe", 0.35, 0.32),
        pal(DARK, "dark", 0.05, 0.8),
        pal(FENCE, "fence", 0.3, 0.36),
        pal(BELLY, "belly", 0.2, 0.55),
    ]


# --- curves ---------------------------------------------------------------------------------------

HS = pchip([11.0, 13.0, 16.0, 19.0, 22.0, 24.0, 25.35], [2.6, 2.8, 2.75, 2.45, 1.75, 1.05, 0.38])
HB = pchip([11.0, 14.0, 18.0, 22.0, 25.35], [1.35, 1.45, 1.2, 0.75, 0.2])
EDGE = 0.28


def hull_loop(y, grow=0.0):
    """16 points: 0 top centre, 1-7 down the right side, 8 keel, 9-15 up the left side. A chamfered
    lens: a narrow spine flat, a chamfer, the deck, the shoulder chamfer, a thin edge, the belly."""
    wl, wr, hs, hb = F["hl"](y), F["hr"](y), HS(y), HB(y)

    def side(w):
        return [(0.18 * w, hs), (0.31 * w, hs * 0.86), (0.62 * w, hs * 0.6), (0.87 * w, EDGE + hs * 0.22),
                (w, EDGE), (w, -EDGE), (0.6 * w, -hb * 0.78)]
    right = side(wr)
    left = [(-x, z) for x, z in reversed(side(wl))]
    return [(0.0, hs)] + right + [(0.0, -hb)] + left, (0.0, (hs - hb) * 0.3)


def hull_top(x, y):
    pts, _ = hull_loop(y)
    top = pts[0:6] if x >= 0 else [pts[0]] + [(-a, b) for a, b in reversed(pts[11:16])]
    ax = abs(x)
    for (x0, z0), (x1, z1) in zip(top, top[1:]):
        if x0 <= ax <= x1 + 1e-9:
            return z0 + (z1 - z0) * (ax - x0) / max(x1 - x0, 1e-9)
    return EDGE


# Tail block: columns 11-15 at rows 5-7, waisted to 12-14 at rows 8-9, widening into the hull.
NW = pchip([3.9, 4.3, 4.9, 5.4, 7.55, 8.15, 9.85, 10.45, 11.8], [1.15, 1.45, 2.15, 2.45, 2.45, 1.55, 1.55, 2.45, 2.9])
NT = pchip([3.9, 5.0, 8.0, 11.8], [1.7, 2.3, 2.4, 2.65])
NB = pchip([3.9, 5.0, 11.8], [0.6, 1.0, 1.3])


def neck_loop(y, grow=0.0):
    """12 points: 0 top centre, 1-5 right, 6 keel, 7-11 left."""
    w, t, b = NW(y), NT(y), NB(y)
    right = [(0.42 * w, t), (0.8 * w, t * 0.86), (w, t * 0.5), (w, -0.15), (0.6 * w, -b)]
    pts = [(0.0, t)] + right + [(0.0, -b)] + [(-x, z) for x, z in reversed(right)]
    return pts, (0.0, (t - b) * 0.3)


# Cockpit cowl: the pale frame columns 11-15, rows 14-21; glass columns 12-14, rows 17-20.
CW = pchip([13.9, 14.4, 15.3, 19.0, 20.4, 21.3, 21.8], [0.8, 1.55, 2.05, 2.1, 1.7, 0.9, 0.3])
GW = pchip([16.85, 17.25, 18.3, 19.6, 20.4, 20.85], [0.35, 1.2, 1.45, 1.25, 0.6, 0.12])
COWL_UP = 0.55


def cowl_loop(y, grow=0.0):
    w = CW(y)
    base = HS(y)
    top = base + COWL_UP
    right = [(0.5 * w, top), (0.82 * w, top - 0.16), (w, top - 0.45), (w, base - 0.7)]
    pts = [(0.0, top)] + right + [(0.0, base - 0.9)] + [(-x, z) for x, z in reversed(right)]
    return pts, (0.0, base - 0.2)


# --- generic shapes -------------------------------------------------------------------------------

def tube(P, stations, mat, n=10, cap0=True, cap1=True, mats=None):
    """stations: [(centre (x,y,z), tangent, rx, rz)]; rings of n points in the plane normal to the
    tangent, rx across (horizontal) and rz up."""
    rings = []
    for c, t, rx, rz in stations:
        t = Vector(t).normalized()
        side = Vector((0, 0, 1)).cross(t)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        up = t.cross(side).normalized()
        if up.z < 0:
            up = -up
        ring = [P.v(tuple(Vector(c) + side * (rx * math.cos(2 * math.pi * (k + 0.5) / n))
                          + up * (rz * math.sin(2 * math.pi * (k + 0.5) / n)))) for k in range(n)]
        rings.append((ring, Vector(c)))
    for i, ((r0, c0), (r1, c1)) in enumerate(zip(rings, rings[1:])):
        m = mats[i] if mats else mat
        for a in range(n):
            b = (a + 1) % n
            P.f((r0[a], r0[b], r1[b], r1[a]), m, away=tuple((c0 + c1) / 2))
    if cap0:
        P.f(list(rings[0][0]), mats[0] if mats else mat, out=tuple(-(rings[1][1] - rings[0][1])))
    if cap1:
        P.f(list(rings[-1][0]), mats[-1] if mats else mat, out=tuple(rings[-1][1] - rings[-2][1]))
    return rings


def oval_dome(P, cx, cy, z, hw, hl, h, mat, n=10, sink=0.35):
    """An oblong dome (lamp lens / eye) over (cx, cy), its base sunk `sink` under z."""
    pts = [(cx + hw * math.cos(2 * math.pi * k / n), cy + hl * math.sin(2 * math.pi * k / n), z - sink)
           for k in range(n)]
    for f, s in ((0.85, 0.5), (0.55, 0.85), (0.2, 1.0)):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (s > 0.6)) / n
            pts.append((cx + f * hw * math.cos(a), cy + f * hl * math.sin(a), z + h * s))
    hull(P, pts, mat)


# --- parts ----------------------------------------------------------------------------------------

def build_hull(P, D):
    ys = [11.0, 11.4, 12.2] + T.frange(13.0, 24.3, 0.8) + [24.7, 25.0, 25.2, 25.35]
    loft(P, hull_loop, ys, HULL)
    # Raised deck armour either side of the spine, split at row 17 (a panel line): 45-degree
    # chamfers, skirts into the core (modelled gaps).
    for (y0, y1) in ((11.25, 16.85), (17.1, 22.8)):
        plate(D, hull_loop, y0, y1, DECK, 2.2, 3.85, d=0.2, c=0.14, depth=0.35, ystep=0.8)
        plate(D, hull_loop, y0, y1, DECK, 12.15, 13.8, d=0.2, c=0.14, depth=0.35, ystep=0.8)
    # Chine strips along the V edges (between the shoulder chamfer and the edge).
    for (y0, y1) in ((12.4, 18.2), (18.5, 23.6)):
        plate(D, hull_loop, y0, y1, HULL, 4.1, 4.85, d=0.12, c=0.08, depth=0.25, ystep=0.9)
        plate(D, hull_loop, y0, y1, HULL, 11.15, 11.9, d=0.12, c=0.08, depth=0.25, ystep=0.9)
    # Spine plate from the tail block to the cowl; nose spine strip in front of it.
    plate(D, hull_loop, 11.0, 14.3, SPINE, -0.85, 0.85, d=0.22, c=0.12, depth=0.35, ystep=0.8)
    plate(D, hull_loop, 21.9, 24.6, SPINE, -0.8, 0.8, d=0.16, c=0.1, depth=0.3, ystep=0.7)
    # Dark intakes in the hull's rear face either side of the tail block (the ink notches at
    # columns 10 and 16, rows 6-10): mouths facing aft, with lips.
    for s in (-1, 1):
        x0, x1 = sorted((s * 2.55, s * 3.45))
        hull(D, T.cbox(x0, x1, 10.85, 11.35, 0.15, 1.15, 0.08), DARK)
        xa, xb = sorted((s * 2.4, s * 3.6))
        hull(D, T.cbox(xa, xb, 11.0, 11.5, 0.05, 1.3, 0.1), HULL)


def build_neck(P, D):
    ys = [3.9, 4.15, 4.5, 4.9, 5.4, 6.4, 7.55, 7.85, 8.15, 9.0, 9.85, 10.15, 10.45, 11.0, 11.8]
    loft(P, neck_loop, ys, HULL)
    # Spine plate along the top, brown cheek plates on the flanks (columns 11 and 15, rows 5-7).
    plate(D, neck_loop, 4.6, 11.2, SPINE, -0.75, 0.75, d=0.2, c=0.12, depth=0.35, ystep=0.6)
    plate(D, neck_loop, 4.95, 7.65, CHEEK, 1.25, 3.4, d=0.18, c=0.1, depth=0.3, ystep=0.6)
    plate(D, neck_loop, 4.95, 7.65, CHEEK, 8.6, 10.75, d=0.18, c=0.1, depth=0.3, ystep=0.6)
    # Machined collars either side of the waist.
    for y0, y1 in ((8.35, 8.7), (9.3, 9.65)):
        plate(D, neck_loop, y0, y1, HULL, 1.2, 4.6, d=0.14, c=0.06, depth=0.3, ystep=1.0)
        plate(D, neck_loop, y0, y1, HULL, 7.4, 10.8, d=0.14, c=0.06, depth=0.3, ystep=1.0)
    # Rear face: a dark exhaust ring round the probe's root.
    tube(D, [((0, 4.0, 0.75), (0, -1, 0), 1.05, 0.95), ((0, 3.78, 0.75), (0, -1, 0), 1.0, 0.9)], DARK, n=12)


def build_probe(P, D):
    """The pale rear probe (column 13, rows 1-4): it rises aft like a sting (about 30 degrees), from
    a machined collar, a tapered shaft to a fine tip."""
    z0, rise = 1.15, 0.55
    st = [(4.3, 0.78), (3.95, 0.78), (3.6, 0.78), (3.55, 0.58), (3.0, 0.56), (2.4, 0.5), (1.95, 0.36),
          (1.65, 0.16), (1.45, 0.04)]
    dx = F["probe"]  # the sting swivels: lateral offset at the tip (frames 1 and 5)
    stations = [((dx * ((4.3 - y) / 2.85) ** 1.5, y, z0 + rise * (4.3 - y)), (dx * 0.5, -1, rise), r, r)
                for y, r in st]
    tube(D, stations, PROBE, n=12, mats=[HULL, HULL, DARK, PROBE, PROBE, PROBE, PROBE, PROBE])


def build_horn(D, s):
    """A brown horn canted outward from its cheek plate (column 10 / 16, rows 3-5): a curved,
    chamfered-diamond blade thinning to a point, on a collar."""
    tip = F["horn"][0 if s < 0 else 1]
    p0, p1, p2 = (Vector((s * 2.0, 7.3, 1.6)), Vector((s * (tip - 0.1), 5.2, 2.1)),
                  Vector((s * tip, 3.3, 2.65)))
    stations = []
    k = 8
    for i in range(k):
        t = i / (k - 1)
        c = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2
        d = 2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1)
        stations.append((tuple(c), tuple(d), 0.5 * (1 - t) ** 0.7 + 0.2, 0.7 * (1 - t) ** 0.8 + 0.08))
    tube(D, stations, HORN, n=6)
    tube(D, [((s * 2.0, 7.45, 1.5), (s * 0.35, -1, 0.25), 0.78, 0.78),
             ((s * 2.15, 6.85, 1.68), (s * 0.35, -1, 0.25), 0.74, 0.74)], CHEEK, n=8)


def wing_outlines(s):
    """Wing blade plan (convex pieces): tip at row 7, outer edge straight at the frame's inner edge,
    inner edge on the 45-degree line |x| = 14 - y down to the root, the root buried in the hull's
    shoulder. The flexed blade of frames 1/5 is a pixel wide at rows 7-8 and widens to the root as
    drawn: two pieces split at row 9.5, so its inner edge can bend."""
    wo = F["wing_out"] - F["trim"][0 if s < 0 else 1]
    root = [(wo, 11.6), (wo - 0.55, 12.3), (3.0, 12.3), (3.0, 11.0)]
    if not F["wing_in"]:
        pieces = [[(wo - 0.38, 6.92), (wo, 7.45)] + root + [(3.42, 10.58), (6.72, 7.28)]]
    else:
        wi = F["wing_in"]
        pieces = [[(wo, 9.4)] + root + [(3.42 + wi * 0.3, 10.58), (4.3 + wi * 0.5, 9.4)],
                  [(wo - 0.38, 6.92), (wo, 7.45), (wo, 9.6), (4.3 + wi * 0.5, 9.6), (wo - 0.8, 7.28)]]
    return [[(s * x, y) for x, y in p] for p in pieces]


def wing_top(x, y):
    t = (abs(x) - 3.0) / 4.5
    return 1.55 - 0.95 * t - 0.03 * (12 - y)


def build_wing(P, D, s):
    for outline in wing_outlines(s):
        cx = sum(p[0] for p in outline) / len(outline)
        cy = sum(p[1] for p in outline) / len(outline)
        pts = []
        for x, y in outline:
            zt = wing_top(x, y)
            zb = -0.32 - 0.3 * max(0.0, 1 - (abs(x) - 3) / 4.5)
            ix, iy = x + (cx - x) * 0.06, y + (cy - y) * 0.06
            pts += [(x, y, zt - 0.22), (x, y, zb + 0.1), (ix, iy, zt), (ix, iy, zb)]
        hull(P, pts, HULL)
    # Wingtip fence: a thin blade on the outer edge, leaning inboard (the sprite's lit column 6/20).
    wo = F["wing_out"] - F["trim"][0 if s < 0 else 1]
    fp = []
    lean = 0.45 if not F["wing_in"] else 0.12  # the flexed blade (frames 1/5) is a pixel wide
    for y, h in ((7.25, 1.1), (8.0, 1.15), (11.2, 0.85)):
        for x in (wo, wo - 0.3 - lean / 3):
            fp += [(s * x, y, 0.1), (s * (x - lean), y + 0.1, h)]
    fp += [(s * (wo - 0.15), 11.6, 0.2), (s * (wo - 0.35), 7.0, 0.6)]
    hull(D, fp, FENCE)
    # The brown knuckle at the root (columns 8-9 / 18, rows 9-11): a chamfered barrel with
    # collars, from inside the shoulder up to where the blade's inner edge leaves it.
    ko = 0.5 * F["wing_in"]
    a = Vector((s * (3.9 + ko), 12.1, 1.3))
    b = Vector((s * (4.75 + ko * 0.6), 9.45 + ko, 1.3))
    d = b - a
    tube(D, [(tuple(a), tuple(d), 0.4, 0.4), (tuple(a + d * 0.08), tuple(d), 0.55, 0.55),
             (tuple(a + d * 0.92), tuple(d), 0.55, 0.55), (tuple(b), tuple(d), 0.4, 0.4)], STRIP, n=8)
    # A spar ridge from root to tip on the wing's top (panel break).
    rp = []
    tipx = wo - 0.95
    for (x, y) in ((4.9, 11.4), (tipx, 8.3)):
        for dx in (-0.22, 0.22):
            rp += [(s * (x + dx), y, wing_top(x, y) - 0.1), (s * (x + dx * 0.5), y, wing_top(x, y) + 0.12)]
    hull(D, rp, DECK)


def build_cowl(P, D):
    ys = [13.9, 14.2, 14.6, 15.3, 16.2, 17.2, 18.2, 19.0, 19.8, 20.4, 20.9, 21.3, 21.6, 21.8]
    loft(D, cowl_loop, ys, COWL)
    # Glass: a low dome set in the cowl's top, oval (columns 12-14, rows 17-20).
    n = 12
    rings = []
    for y in [16.85, 17.05, 17.4, 18.0, 18.6, 19.2, 19.8, 20.3, 20.6, 20.85]:
        w = GW(y)
        top = HS(y) + COWL_UP
        rings.append([D.v((w * math.cos(math.pi * k / n), y,
                           top - 0.12 + 0.42 * math.sin(math.pi * k / n) * min(1.0, w / 1.2) ** 0.5))
                      for k in range(n + 1)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            D.f((r0[k], r0[k + 1], r1[k + 1], r1[k]), GLASS, away=(0, 18.6, -5))
        D.f((r0[0], r0[n], r1[n], r1[0]), GLASS, out=(0, 0, -1))
    D.f(rings[0], GLASS, out=(0, -1, 0))
    D.f(rings[-1], GLASS, out=(0, 1, 0))


def build_eyes(P, D):
    for s in (-1, 1):
        x, y = s * 1.0, 12.15
        z = hull_top(x, y) + 0.22
        hull(D, T.cbox(x - 0.6, x + 0.6, y - 1.0, y + 1.0, z - 0.6, z + 0.1, 0.12), DARK)
        oval_dome(D, x, y, z + 0.1, 0.45, 0.82, 0.3, EYE, sink=0.3)


# Where the sprite draws them: right root (10, 17), left root (11, 10), left horn (5, 10), right wing (8, 19).
LAMPS = {"root_r": (3.95, 10.6), "root_l": (-3.2, 11.3), "horn": (-2.75, 5.35), "wing_r": (5.5, 8.5)}
FRAME_LAMPS = {1: ["root_r"], 3: ["root_r", "root_l", "horn", "wing_r"], 5: ["root_r", "root_l"]}


def build_lamp(P, key):
    x, y = LAMPS[key]
    # The lamps stay where the sprite draws them on every frame: undo the roll's sideways slide.
    x += 0.45 * math.sin(math.radians(F["roll"])) / math.sin(math.radians(20.0)) if F["roll"] else 0.0
    if key.startswith("root"):
        oval_dome(P, x, y, 1.6, 0.42, 0.42, 0.28, LAMP, sink=0.4)
    elif key == "horn":
        oval_dome(P, x, y, 2.1, 0.34, 0.4, 0.3, LAMP, sink=0.35)
    else:
        oval_dome(P, x, y, wing_top(x, y) + 0.02, 0.4, 0.45, 0.25, LAMP, sink=0.35)


def shifted(part):
    for v in part.bm.verts:
        v.co.x += CX
    return part


def frame_matrix(frame):
    """Blender-space matrix of a frame: widened 1/cos(roll) across, then rolled about the long axis
    (the centre line at PIVOT_Z), + roll = top to the left."""
    a = math.radians(FRAMES[frame]["roll"])
    piv = Vector((CX * PX, 0, PIVOT_Z * PX))
    sc = Matrix.Diagonal((1 / math.cos(a), 1, 1, 1))
    return Matrix.Translation(piv) @ Matrix.Rotation(-a, 4, "Y") @ sc @ Matrix.Translation(-piv)


def build_frame(coll, sprite, frame):
    set_frame(frame)
    mats = materials(sprite, frame)
    P = Part(f"{NAME}A_f{frame}_core", smooth_angle=32)
    D = Part(f"{NAME}A_f{frame}_detail", smooth_angle=32)
    build_hull(P, D)
    build_neck(P, D)
    build_probe(P, D)
    build_cowl(P, D)
    build_eyes(P, D)
    for s in (-1, 1):
        build_wing(P, D, s)
        build_horn(D, s)
    objs = [T.finish(shifted(p), mats, coll) for p in (P, D)]
    obj = T.join(objs, f"{NAME}-f{frame}")
    obj.data.transform(frame_matrix(frame))
    # Make every face point out of its own piece. Some faces came out of usp_talon.finish facing
    # inward (measured from straight above: 92 / 170 / 297 of the first hits on frames 1 / 3 / 5
    # were down-facing faces: the left horn and wing pieces, probe collar, an eye); cull_hidden then
    # deleted them as hidden, leaving holes the game saw through as black blotches.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    # The outline shell is remeshed from the closed parts before cull_hidden opens them up: a voxel
    # remesh of the culled, open surface fills unevenly (holes over the hull, the horns cut off).
    src = obj.copy()
    src.data = obj.data.copy()
    src.name = f"{NAME}-f{frame}_shellsrc"
    coll.objects.link(src)
    T.cull_hidden(obj)
    lamps = []
    for key in FRAME_LAMPS[frame]:
        L = Part(f"{NAME}-f{frame}-lamp-{key}", smooth_angle=60)
        build_lamp(L, key)
        lo = T.finish(shifted(L), mats, coll)
        lo.data.transform(frame_matrix(frame))
        lamps.append(lo)
    return obj, lamps, src


# --- measurement ----------------------------------------------------------------------------------

def pal_grid(obj):
    rows = []
    for r in range(28):
        row = []
        for c in range(24):
            X, Y = (c + 0.5 - 12) * PX, (14 - (r + 0.5)) * PX
            hit, loc, nrm, fi = obj.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            m = obj.data.materials[obj.data.polygons[fi].material_index]
            row.append(int(m.name.split("_")[1]))
        rows.append(row)
    return rows


# --- views ----------------------------------------------------------------------------------------

def setup_cam(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def render_views(frames_objs, out):
    """frames_objs: {frame: [visible objects (model, lamps)]}; outline shells hidden."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene

    def show(frame):
        for o in scene.objects:
            if o.type == "MESH":
                o.hide_render = o not in frames_objs[frame]

    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 10
    scene.render.resolution_x, scene.render.resolution_y = 24 * K, 28 * K
    scene.render.resolution_percentage = 100
    top = setup_cam(scene, "topmask", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    for f in frames_objs:
        show(f)
        scene.render.filepath = str(out / f"top_mask_f{f}.png")
        bpy.ops.render.render(write_still=True)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.17, 0.2, 1)
    bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(20))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
    scene.render.resolution_x, scene.render.resolution_y = 24 * 12, 28 * 12
    for f in frames_objs:
        show(f)
        scene.render.filepath = str(out / f"top_lit_f{f}.png")
        bpy.ops.render.render(write_still=True)
    show(3)
    V = 420
    scene.render.resolution_x = scene.render.resolution_y = V
    c0 = Vector((CX * PX, 0, 0.05))
    d = 3.4
    t = math.radians(32)
    views = {
        "side": ((d, 0, 0), 2.6),
        "front": ((0, -d, 0), 2.6),
        "rear": ((0, d, 0), 2.6),
        "q34": ((d * 0.6, -d * 0.55, d * 0.6), None),
        "q34r": ((-d * 0.6, d * 0.5, d * 0.6), None),
        "game": ((0, -d * math.sin(t), d * math.cos(t)), None),
        "under": ((d * 0.5, -d * 0.6, -d * 0.9), None),
    }
    for name, (loc, ortho) in views.items():
        c = setup_cam(scene, name, tuple(c0 + Vector(loc)), tuple(c0), ortho=ortho, lens=58)
        scene.camera = c
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    for f in (1, 5):
        show(f)
        scene.camera = bpy.data.objects["game"]
        scene.render.filepath = str(out / f"game_f{f}.png")
        bpy.ops.render.render(write_still=True)


# --- outline shell --------------------------------------------------------------------------------

def outline_shell_parts(obj, coll, voxel=0.01, faces=1500, smooth=4, inside=0.004, min_verts=120, target=None):
    """common.outline_shell (D51) keeping every outer island, not only the largest: the horns, the
    probe sting, the knuckles and the glass stand off the hull (after cull_hidden they only touch it),
    so the voxel remesh leaves them as islands of their own and the stock helper dropped them (no ink
    on them in game). Islands inside another island (the inner side of a thin plate's remesh) and
    voxel crumbs go; the rest are smoothed, thinned and held `inside` the model (Shrinkwrap, D88) so
    the shell's back faces never poke through the thin hull and wings as black cracks.
    Candidate for common.outline_shell(keep="outer")."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{(target or obj).name}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
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
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    islands = [i for i in islands if len(i) >= min_verts]
    trees = []
    for isl in islands:
        ids = {v.index for v in isl}
        fs = {f for v in isl for f in v.link_faces}
        verts = [v.co.copy() for v in isl]
        remap = {v.index: k for k, v in enumerate(isl)}
        polys = [[remap[v.index] for v in f.verts] for f in fs if all(v.index in ids for v in f.verts)]
        trees.append(BVHTree.FromPolygons(verts, polys))

    def inside_of(p, tree):
        hits, o, d = 0, p.copy(), Vector((0.137, 0.291, 0.947)).normalized()
        for _ in range(64):
            loc, _n, _i, _dist = tree.ray_cast(o, d)
            if loc is None:
                break
            hits += 1
            o = loc + d * 1e-5
        return hits % 2 == 1

    keep = set()
    for k, isl in enumerate(islands):
        sample = isl[:: max(1, len(isl) // 24)]
        buried = any(sum(inside_of(v.co, trees[j]) for v in sample) > 0.6 * len(sample)
                     for j in range(k))
        if not buried:
            keep.update(v.index for v in isl)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = target or obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        # INSIDE mode pulls a vertex that far *inside* for a positive offset; a negative one (as in
        # common.outline_shell) leaves the shell where it was (measured: same 1048/2883 pokes).
        sw.offset = inside
        common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(REPO, NAME)
    coll = common.reset_collection(NAME)
    export, frames_objs, tris = [], {}, {}
    fmt = "AUTO" if "--no-bake" in argv else "WEBP"
    for f in (1, 3, 5):
        body, lamps, src = build_frame(coll, sprite, f)
        tris[f] = sum(len(p.vertices) - 2 for p in body.data.polygons)
        if "--no-bake" not in argv:
            bake_dir = HERE / "bake" / f"f{f}"
            bake_dir.mkdir(parents=True, exist_ok=True)
            tint, textured = T.TINT, T.TEXTURED
            T.TINT, T.TEXTURED = TINT, TEXTURED
            try:
                T.bake_maps(body, bake_dir, size=512, samples=48)
            finally:
                T.TINT, T.TEXTURED = tint, textured
            for img in bpy.data.images:
                if img.name in ("talon_colour", "talon_rm"):
                    img.name = img.name.replace("talon", f"{NAME}_f{f}")
        shell = outline_shell_parts(src, coll, voxel=0.01, faces=1500, smooth=4, inside=0.006, target=body)
        bpy.data.objects.remove(src)
        shell.name = f"{NAME}-f{f}_outline"
        for o in [body, shell] + lamps:
            common.frame_part(o, [f])
        export += [body, shell] + lamps
        frames_objs[f] = [body] + lamps
    print(f"{NAME}: triangles per frame {tris} (shells excluded)")
    common.export_sprite_model(REPO, export, MODEL, sprite["sprites"], image_format=fmt)
    if "--views" in argv:
        out = Path(argv[argv.index("--views") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "pal_grid.json").write_text(json.dumps({f: pal_grid(frames_objs[f][0]) for f in (1, 3, 5)}))
        (out / "fit.json").write_text(json.dumps({"frames": {f: {k: v for k, v in FRAMES[f].items()}
                                                             for f in FRAMES}, "tris": tris}))
        render_views(frames_objs, out)


if __name__ == "__main__":
    main()
