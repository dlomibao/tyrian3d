"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a hard-surface
fighter built the USP Talon's way (assets/blender/usp_talon.py, DECISIONS D50-D53).

The sprite is authoritative for the plan outline, the windshield and the colours: the top view
follows frame 81's inner mask (D74: the game's ink outline stands in for the sprite's dark border)
with smooth curves through it, never its pixel steps (a blunt ogive nose, swept wings with a
pointed tip at row 8 and a trailing edge swept in to the waist, two engine pods that swell round
from row 12 to the full width at rows 15-20, and canted red nozzles whose exits make the diagonal
rear edge down to the tail at row 26; DECISIONS D118),
the small dark windshield sits exactly over the sprite's cockpit pixels (rows 5-8, columns 10-12),
and each part takes the palette index the sprite uses where it covers it. The concept
(assets/blender/features/concepts/ship-silver-ship.jpg) guides the side and front design and the
detail where it agrees: a raised bright spine deck with a centre strip, swept wings with panel
lines, rounded armour pods with an intake at the front, a dark bay in each pod's inboard top
holding two glowing red light tubes and a grey strut across them (rows 18-20), red nozzle shrouds
behind the pods, three ribs over a dark tail block; underneath a keel strake, belly panels, a nose
gear door and gear doors under the pods.

How it is built (as the Talon):
- Every part is a low-poly cage in sprite px (x across from the ship's centre line, the middle of
  sprite column 11; y = sprite row, aft is +y; z up), moved to Blender at the end
  (X = (x - 0.5) / 12, Y = (14 - y) / 12, Z = z / 12).
- Sections between stations are monotone cubic (pchip), so lofts never swell.
- Dark gunmetal cores under separate armour plates that stand 0.2-0.5 px proud with 45-degree
  chamfers, so panel lines are real gaps. Flat faces stay flat (sharp by angle, weighted normals).
- Texture: no concept projection (texture_bake.py skips this model: "bake": "model" in its
  maps.json). This script bakes ambient occlusion with an edge lift (a colour multiplier, TINT)
  and a roughness/metalness map. Base Color = map x palette colour.
- Palette materials (pal_<index>) so palettes, fades and the hit flash apply; the light tubes and
  the nozzle throats are emissive palette reds (117, 118).
- Exported beside it: an outline shell (common.outline_shell, D51) and `tyrian_engines` (two red
  glows behind the canted nozzles for the menu backdrop).

    Blender --background --factory-startup --python ship-silver-ship.py -- [--out path.glb] [--no-bake] [--preview png]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
# The Talon's generic hard-surface helpers: pchip curves, parts, sections, lofts, armour plates,
# chamfered hulls, hidden-face culling and the join with weighted normals.
from usp_talon import (Part, Section, cbox, cull_hidden, fillet, frange, hull, join, loft,  # noqa: E402
                       pchip, plate)

NAME = "ship-silver-ship"
MODEL = f"ships/{NAME}"
PX = 1 / 12
AXIS = -0.5  # the ship's centre line in the Talon's frame (column 12's left edge is x = 0)

# Material slots and the palette index each takes: the median index of the sprite pixels the part
# covers, the darkest shading (1-3) and the brightest highlights (13-15) left out as lighting.
(NOSE, WING, DECK, POD, PODF, FRAME, STRUT, RIB, GUN, DEEP, GLASS, RED, RED_DK, TUBE, CORE, SPINE,
 BELLY) = range(17)
PAL_OF = {NOSE: 6, WING: 5, DECK: 11, POD: 7, PODF: 9, FRAME: 9, STRUT: 10, RIB: 8, GUN: 4, DEEP: 2,
          GLASS: 1, RED: 115, RED_DK: 113, TUBE: 117, CORE: 118, SPINE: 10, BELLY: 6}

# Metalness scale (satin, as the Talon's D53): the hull is 0.15-0.25 metallic.
METAL = 0.22
# The baked colour map's tint (linear multipliers). The Talon needed a cool tint to survive three's
# tone mapping; this ship is neutral grey and the game's blue sky light leans it cool, so the map is
# trimmed in blue a touch instead (measured on game-lit top views against the sprite's greys).
TINT = (1.0, 0.96, 0.82)


def materials(sprite):
    def pal(slot, tag, metallic, roughness, emission=0.0):
        return common.palette_material(sprite, PAL_OF[slot], f"silver_{tag}", metallic=metallic * METAL,
                                       roughness=roughness, emission_strength=emission)
    mats = [
        pal(NOSE, "nose", 0.55, 0.4),
        pal(WING, "wing", 0.5, 0.42),
        pal(DECK, "deck", 0.6, 0.34),
        pal(POD, "pod", 0.55, 0.38),
        pal(PODF, "pod_front", 0.55, 0.38),
        pal(FRAME, "frame", 0.55, 0.36),
        pal(STRUT, "strut", 0.6, 0.34),
        pal(RIB, "rib", 0.55, 0.38),
        pal(GUN, "gunmetal", 0.5, 0.46),
        pal(DEEP, "recess", 0.3, 0.8),
        pal(GLASS, "glass", 0.0, 0.04),
        pal(RED, "shroud", 0.45, 0.4),
        pal(RED_DK, "lip", 0.4, 0.5),
        pal(TUBE, "tube", 0.0, 0.4, emission=3.0),
        pal(CORE, "core", 0.0, 0.4, emission=3.5),
        pal(SPINE, "spine", 0.65, 0.3),
        pal(BELLY, "belly", 0.4, 0.55),
    ]
    return mats


# --- the plan (sprite px, x from the centre line, y = row) --------------------------------------
#
# Frame 81's INNER mask (D74, docs/agents/OUTLINE-BORDER.md: the game's ink outline stands in for
# the sprite's dark border), half width by row; it is the whole sprite's one pixel in at every row:
#   rows 1-2 1.5 | 3-4 2.5 | 5 3.5 | 6 4.5 | 7 5.5 | 8 6.5 (wing tips) | 9 5.5 | 10-11 4.5 |
#   12 5.5 | 13 6.5 | 14 7.5 | 15-20 8.5 (pods) | 21 7.5 | 22 6.5 | 23 6.5 / 5.5 | 24 4.5 | 25 3.5
# Each part's outboard edge is a smooth curve through the middle of those steps, so every inner
# pixel is covered at least half and no other pixel is, with no tiers: the nose is a blunt ogive
# from row 0.95, the wing's leading edge one straight sweep (half width y - 2.1) to a pointed tip,
# its trailing edge one straight sweep in to the waist, the pods' fronts one smooth round, their
# sides straight, the nozzle exits the straight diagonal x + y = 29, the tail's end at row 26.05.
# The parts are the pre-refit ship's (rounded pods, light-tube bays), each pulled in one pixel.

TAIL0, TAIL_OLD, TAIL_NEW = 21.5, 26.9, 26.05


def T(y):
    """The tail block's rows, shortened to the inner mask's length (its end from 26.9 to 26.05)."""
    return y if y <= TAIL0 else TAIL0 + (y - TAIL0) * (TAIL_NEW - TAIL0) / (TAIL_OLD - TAIL0)


FUSE_PLATE = 0.28  # how far the nose plates stand out of the core
POD_PLATE = 0.3

# Fuselage core: half width, top and keel.
# The nose's outline (core + its 0.28 plate) is the old one a pixel in; from row 6 the core is the old one.
_FWY = [0.95, 1.15, 1.45, 1.9, 2.4, 2.9, 3.4, 3.9, 4.4, 5.0, 5.8, 7.0, 9.0, 10.0, 11.0, 12.5, 14.0, 20.0,
        T(22.0), T(24.0), T(25.5), T(26.2), T(26.6), T(26.9)]
FW = pchip(_FWY, [0.3, 0.62, 0.92, 1.16, 1.36, 1.6, 1.82, 1.98, 2.14, 2.45, 2.92, 3.12, 3.08, 3.0, 2.9,
                  2.8, 2.75, 2.75, 2.75, 2.8, 2.95, 3.1, 3.12, 3.0])
_FY = [0.95, 1.35, 2.1, 2.9, 3.7, 4.6, 6.0, 8.0, 9.5, 11.0, 13.0, 16.0, 19.0, 21.5, T(23.0), T(24.5), T(25.8),
       T(26.6), T(26.9)]
FT = pchip(_FY, [0.42, 0.82, 1.22, 1.52, 1.76, 1.94, 2.06, 2.14, 2.2, 2.3, 2.38, 2.4, 2.38, 2.28, 2.05,
                 1.9, 1.78, 1.64, 1.46])
FB = pchip(_FY, [0.18, -0.2, -0.6, -0.9, -1.15, -1.35, -1.6, -1.75, -1.85, -1.95, -2.05, -2.1, -2.1,
                 -2.05, -1.95, -1.8, -1.6, -1.4, -1.2])
DECK_F = 0.6     # flat deck half width, fraction of the half width
SHOULDER = 0.3   # shoulder chamfer drop, fraction of the height
FLANK = 0.45     # flank foot above the keel, fraction of the height
CHINE = 0.1


def fuselage_loop(y):
    """Closed section (the Talon's): s = 0 top centre, 1 deck edge, 2 shoulder, 3 flank foot,
    4 chine, 5 keel, then back up the left side."""
    w, t, b = FW(y), FT(y), FB(y)
    h = t - b
    right = [(0.0, t), (DECK_F * w, t), (w, t - SHOULDER * h), (w, b + FLANK * h), (DECK_F * w, b + CHINE * h),
             (0.0, b)]
    pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return pts, (0.0, (t + b) / 2)


def deck_top(y):
    return FT(y) + 0.2


# Engine pods: outboard edge (the inner mask's, a smooth round at the front, minus the shell plates),
# inboard edge tucked into the fuselage's flank (the sprite's dark seam at columns 8 and 14), centre
# a little below the hull.
_PY = [10.0, 10.4, 11.0, 12.0, 12.5, 13.5, 14.5, 15.0, 15.5, 16.0, 17.0, 18.5, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0]
_PO = [3.95, 4.25, 4.5, 4.88, 5.42, 6.45, 7.45, 7.92, 8.25, 8.42, 8.5, 8.5, 8.48, 8.42, 8.27, 7.95, 7.5, 6.95]
_PI = [3.3, 3.08, 2.95, 2.88, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.88, 2.92, 3.0]
_PXO = [o - POD_PLATE for o in _PO]
POD_CX = pchip(_PY, [(a + b) / 2 for a, b in zip(_PI, _PXO)])
POD_RX = pchip(_PY, [(b - a) / 2 for a, b in zip(_PI, _PXO)])
POD_CZ = pchip(_PY, [-0.2, -0.3, -0.4, -0.45] + [-0.5] * 14)
POD_RZ = pchip(_PY, [0.55, 0.9, 1.2, 1.5, 1.62, 1.85, 2.0, 2.05, 2.1, 2.13, 2.15, 2.15, 2.15, 2.13, 2.1, 2.04, 1.95,
                     1.82])
POD_START, POD_END = _PY[0], _PY[-1]
BAY_Y0, BAY_Y1 = 17.55, 21.35  # the dark bay in the pod's inboard top (sprite rows 18-20)
BAY_Z = 1.38                   # its floor


def _pod_unit():
    """The pod section, normalised to half sizes 1 x 1 (u outboard, v up): a chamfered rectangle
    with large fillets, rounder than the Talon's nacelles (the concept's armour shells). Starts on
    the top flat's inboard end and runs outboard."""
    a, b = 2.6, 2.3
    ca, cb = 0.45 * a, 0.42 * b
    corners = [(-a + ca, b), (a - ca * 1.1, b), (a, b - cb * 1.1), (a, -b + cb), (a - ca, -b),
               (-a + ca, -b), (-a, -b + cb), (-a, b - cb)]
    pts = fillet(corners, (1.3, 1.9, 1.9, 1.5, 1.2, 1.2, 1.0, 1.2), (2, 3, 3, 2, 2, 2, 2, 2))
    return [(u / a, v / b) for u, v in pts]


POD_UNIT = _pod_unit()
POD_N = len(POD_UNIT)


def pod_s(deg):
    """Loop parameter where the ray at `deg` degrees from straight up (toward outboard; negative:
    inboard) meets the pod section."""
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
    return best[1] - (POD_N if deg < 0 and best[1] > POD_N / 2 else 0)


def pod_loop(y, side=1, grow=0.0, cut=False):
    cx, cz = side * POD_CX(y), POD_CZ(y)
    rx, rz = POD_RX(y) + grow, POD_RZ(y) + grow
    pts = []
    for u, v in POD_UNIT:
        x, z = cx + side * rx * u, cz + rz * v
        if cut and u < 0.3 and z > BAY_Z:
            z = BAY_Z
        pts.append((x, z))
    return pts, (cx, cz)


# Canted nozzles: each exit lies on the plan diagonal x + y = 29 (the inner mask's rear edge, rows
# 21-25), facing aft and outboard at 45 degrees; the shroud runs back into the pod and the body.
NOZ_E = (5.3, 23.7, -0.55)  # exit centre (right side)
NOZ_U = (1 / math.sqrt(2), 1 / math.sqrt(2))   # axis, outboard-aft
NOZ_V = (-1 / math.sqrt(2), 1 / math.sqrt(2))  # across the exit, inboard-aft


def rrect(a, b, r, n=4):
    """A rounded rectangle (half sizes a, b, corner radius r), counter-clockwise from +u."""
    r = min(r, a * 0.95, b * 0.95)
    pts = []
    for cx, cy, a0 in ((a - r, b - r, 0), (-a + r, b - r, 90), (-a + r, -b + r, 180), (a - r, -b + r, 270)):
        for k in range(n + 1):
            t = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


# --- mesh helpers ----------------------------------------------------------------------------

def ring_loft(part, rings, mat_of, cap0=None, cap1=None):
    """Loft through rings [(y, pts, centre, tag)], pts [(x, z)] all the same length. Two rings at the
    same y make a step wall (vertices that do not move are shared). mat_of(i, a, b) gives the
    material of the band from ring i to i + 1 between vertices a and b."""
    built = []
    prev = None
    for y, pts, (cx, cz), tag in rings:
        if prev is not None and abs(prev[0] - y) < 1e-9:
            vs = [pv if abs(pv.co.x - x) < 1e-9 and abs(pv.co.z - z) < 1e-9 else part.v((x, y, z))
                  for pv, (x, z) in zip(prev[1], pts)]
        else:
            vs = [part.v((x, y, z)) for x, z in pts]
        built.append((y, vs, (cx, y, cz)))
        prev = (y, vs)
    for i in range(len(built) - 1):
        y0, r0, c0 = built[i]
        y1, r1, c1 = built[i + 1]
        n = len(r0)
        for a in range(n):
            b = (a + 1) % n
            quad = [r0[a], r0[b], r1[b], r1[a]]
            uniq = []
            for v in quad:
                if all(v is not u for u in uniq):
                    uniq.append(v)
            if len(uniq) < 3:
                continue
            if abs(y1 - y0) < 1e-9:
                # Step wall: faces toward the side the step drops to.
                part.f(uniq, mat_of(i, a, b), out=(0, 1 if rings[i + 1][3] == "in" else -1, 0))
            else:
                part.f(uniq, mat_of(i, a, b), away=c0)
    if cap0 is not None:
        part.f(built[0][1], cap0, out=(0, -1, 0))
    if cap1 is not None:
        part.f(built[-1][1], cap1, out=(0, 1, 0))
    return built


def tube_x(part, x0, x1, y, z, r, mat, n=10):
    """A capped cylinder along x."""
    rings = []
    for x in (x0, x1):
        rings.append([part.v((x, y + r * math.cos(2 * math.pi * (k + 0.5) / n), z + r * math.sin(2 * math.pi * (k + 0.5) / n)))
                      for k in range(n)])
    for k in range(n):
        kk = (k + 1) % n
        part.f((rings[0][k], rings[0][kk], rings[1][kk], rings[1][k]), mat, away=((x0 + x1) / 2, y, z))
    part.f(rings[0], mat, out=(-1 if x0 < x1 else 1, 0, 0))
    part.f(rings[1], mat, out=(1 if x0 < x1 else -1, 0, 0))


# --- the ship ---------------------------------------------------------------------------------

def build_fuselage(P):
    L = fuselage_loop
    ys = [0.95, 1.1, 1.35, 1.7] + frange(2.1, TAIL_NEW, 0.85)
    loft(P, L, ys, GUN)
    # Nose cone, all round, its back edge chamfered; a polished tip over its front edge.
    plate(P, L, 1.3, 3.95, NOSE, d=FUSE_PLATE, ch0=False, ystep=0.35)
    sec = Section(L, 1.3)
    tip = [sec.at(k, FUSE_PLATE) for k in range(sec.n)]
    hull(P, tip + [(0.0, 0.98, (FT(0.95) + FB(0.95)) / 2 + 0.05)], NOSE)
    for side in (1, -1):
        def S(a, b):
            return (a, b) if side > 0 else (10 - b, 10 - a)
        # Round the canopy: the shoulders (the sprite's lighter grey beside the glass) and the
        # flanks under the wings, a panel break at row 7.
        for y0, y1 in ((4.1, 6.9), (7.05, 9.55)):
            plate(P, L, y0, y1, FRAME, *S(0.95, 2.55), d=FUSE_PLATE, c=0.14)
            plate(P, L, y0, y1, NOSE, *S(2.6, 4.25), d=FUSE_PLATE)
        # Behind the wings: the shoulders either side of the spine deck run to the tail block,
        # flank plates under them (mostly inside the pods).
        plate(P, L, 9.7, 15.4, DECK, *S(0.95, 2.55), d=0.3, c=0.14)
        plate(P, L, 15.55, 21.5, DECK, *S(0.95, 2.55), d=0.3, c=0.14)
        plate(P, L, 9.7, 21.5, GUN, *S(2.6, 4.25), d=0.2)
        # Tail block: shoulders either side of the dark top, and the sides.
        plate(P, L, 21.65, T(26.35), RIB, *S(0.95, 2.55), d=0.3, c=0.12)
        plate(P, L, 21.65, T(26.35), GUN, *S(2.6, 4.25), d=0.2)
    # Deck in front of the canopy (under the frame) and the spine deck behind it, rows 9.7-21.5,
    # split lengthwise either side of a raised centre strip (the sprite's seams run lengthwise).
    plate(P, L, 3.95, 9.55, FRAME, s0=-0.9, s1=0.9, d=0.2)
    for s0, s1 in ((-0.9, -0.3), (0.3, 0.9)):
        plate(P, L, 9.7, 21.5, DECK, s0=s0, s1=s1, d=0.34, c=0.12, ystep=0.8)
    # Belly: panels along the keel, a proud nose gear door, a keel strake behind it.
    for y0, y1 in ((1.7, 5.2), (5.35, 9.6), (15.65, 20.6), (20.75, T(26.1))):
        plate(P, L, y0, y1, BELLY, s0=4.3, s1=5.7, d=0.15)
    plate(P, L, 9.75, 15.5, BELLY, s0=4.35, s1=5.65, d=0.3, c=0.12, ystep=0.6)
    for sx in (-1, 1):
        sec, _ = fuselage_loop(10.4)
        x4, z4 = sec[4]
        for y0 in (10.2, 14.3):
            hull(P, [(sx * x, y, z) for x, y, z in cbox(x4 * 0.55, x4 * 0.55 + 0.3, y0, y0 + 0.7, z4 - 0.7, z4 - 0.1, 0.06)], GUN)
    pts = []
    for y in (16.0, 17.2, 22.0, T(25.4)):
        b = FB(y) - 0.12
        drop = 0.5 if 17.0 < y < 23.0 else 0.1
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.32, b + 0.4), (0.22, b - drop), (0.1, b - drop - 0.08))]
    hull(P, pts, GUN)
    # The tail's end: a dark ring round the last row, its back edge chamfered, and a recessed vent
    # face with three slats behind the ribs.
    plate(P, L, T(26.4), TAIL_NEW, GUN, d=0.22, c=0.14, ystep=1)
    zc = (FT(T(26.8)) + FB(T(26.8))) / 2
    hull(P, cbox(-2.2, 2.2, T(26.7), T(26.84), zc - 0.95, zc + 0.85, 0.05), DEEP)
    for dz in (-0.5, 0.0, 0.5):
        hull(P, cbox(-2.0, 2.0, T(26.7), TAIL_NEW + 0.03, zc + dz - 0.1, zc + dz + 0.1, 0.04), GUN)


def build_spine(P):
    # Nose spine: two polished strips from row 1.9 to the canopy frame, split by a dark groove (the
    # sprite's light centre pixels at rows 2-4 are sheen on it).
    for sx in (-1, 1):
        pts = []
        for y in frange(1.9, 4.6, 0.45):
            hw = 0.2 + 0.2 * min(1.0, (y - 1.9) / 2.0)
            rise = 0.25 * min(1.0, (y - 1.9) / 1.0)
            top = FT(y) + FUSE_PLATE + rise
            ch = 0.1
            pts += [(sx * 0.07, y, top), (sx * (hw - ch), y, top), (sx * hw, y, top - ch), (sx * hw, y, FT(y) - 0.2),
                    (sx * 0.07, y, FT(y) - 0.2)]
        hull(P, pts, SPINE)

    def ridge(y0, y1, h0, h1, hw, mat, base=-0.3, ch=0.12):
        pts = []
        for y, h in ((y0, h0), (y1, h1)):
            top = FT(y) + h
            pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((hw, top - ch), (hw - ch, top), (hw, FT(y) + base))]
        hull(P, pts, mat)
    # Centre strip of the spine deck behind the canopy (the sprite's column 11, rows 9-21): a raised
    # deck-grey ridge with a polished top, a panel break at row 15.5.
    ridge(9.75, 15.4, 0.62, 0.66, 0.5, DECK)
    ridge(9.9, 15.3, 0.78, 0.8, 0.36, DECK, base=0.2, ch=0.1)
    ridge(15.55, 21.45, 0.66, 0.6, 0.5, DECK)
    ridge(15.65, 21.3, 0.8, 0.74, 0.36, DECK, base=0.2, ch=0.1)
    # A raised access hatch on each side of the deck (rows 12-14.5) and vents further aft.
    for sx in (-1, 1):
        hull(P, [(sx * x, y, z) for x, y, z in cbox(0.75, 1.55, 12.0, 14.4, FT(13) + 0.3, FT(13) + 0.46, 0.08)], DECK)
        for y0 in (17.0, 17.7, 18.4):
            hull(P, [(sx * x, y, z) for x, y, z in cbox(0.8, 1.5, y0, y0 + 0.4, FT(18) + 0.25, FT(18) + 0.38, 0.05)], DEEP)
    # Tail block (rows 21.65-25.65): dark top, three box ribs along it (columns 9, 11 and 13).
    pts = []
    for y in (21.6, T(26.4)):
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((2.05, FT(y) + 0.15), (2.05, FT(y) - 0.6))]
    hull(P, pts, DEEP)
    for xc in (-2.0, 0.0, 2.0):
        pts = []
        for y, h in ((21.55, 0.78), (T(25.6), 0.55), (T(26.45), 0.3)):
            top = FT(y) + h
            pts += [(xc + sx * x, y, z) for sx in (-1, 1) for x, z in ((0.46, top - 0.1), (0.34, top), (0.46, FT(y) - 0.2))]
        hull(P, pts, RIB)


# Windshield: the sprite's dark cockpit pixels (rows 5-8, columns 10-12: |x| <= 1.5, y 5-9),
# a rounded front and a squarer rear edge.
CAN_Y0, CAN_Y1, CAN_YC, CAN_W = 5.0, 9.0, 7.35, 1.5
CAN_N = 40
GLASS_BASE = 0.22
GLASS_H = 0.72


def canopy_outline(grow=0.0):
    pts = []
    for k in range(CAN_N):
        a = 2 * math.pi * k / CAN_N  # 0 = right, pi/2 = forward
        c, s = math.cos(a), math.sin(a)
        if s >= 0:
            n, b = 3.4, CAN_YC - CAN_Y0
        else:
            n, b = 4.0, CAN_Y1 - CAN_YC
        e = 2 / n
        x = CAN_W * math.copysign(abs(c) ** e, c)
        yv = math.copysign(abs(s) ** e, s)
        if s > 0:
            x *= 1 - 0.06 * yv ** 2
        pts.append([x, CAN_YC - b * yv])
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


def hull_top(x, y):
    w, t, b = FW(y), FT(y), FB(y)
    ax = abs(x)
    if ax <= DECK_F * w:
        return t
    return t - SHOULDER * (t - b) * min(1.0, (ax - DECK_F * w) / ((1 - DECK_F) * w))


def build_canopy(G, F):
    C = canopy_outline()
    K = 9
    rings = []
    for k in range(K + 1):
        r = 1 - k / K * 0.97
        ring = []
        for x, y in C:
            px, py = x * r, CAN_YC + (y - CAN_YC) * r
            z = deck_top(py) + GLASS_BASE + GLASS_H * (1 - r ** 2.6) ** 0.55
            ring.append(G.v((px, py, z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(CAN_N):
            j = (i + 1) % CAN_N
            G.f((r0[i], r0[j], r1[j], r1[i]), GLASS, away=(0, CAN_YC, 0))
    G.f(rings[-1], GLASS, out=(0, 0, 1))
    low = [G.v((x, y, deck_top(y) + GLASS_BASE - 0.3)) for x, y in C]
    for i in range(CAN_N):
        j = (i + 1) % CAN_N
        G.f((low[i], low[j], rings[0][j], rings[0][i]), GLASS, out=(C[i][0], C[i][1] - CAN_YC, 0))
    # Frame: a sill from the glass edge out over the deck, flat top, chamfered outer edge.
    inner = canopy_outline(-0.06)
    top_out = canopy_outline(0.2)
    ch_out = canopy_outline(0.32)
    fr = []
    for k in range(CAN_N):
        xi, yi = inner[k]
        xo, yo = top_out[k]
        xc, yc = ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.14
        fr.append([F.v((xi, yi, deck_top(yi) + GLASS_BASE - 0.3)), F.v((xi, yi, zt)), F.v((xo, yo, zt)),
                   F.v((xc, yc, zt - 0.14)), F.v((xc, yc, hull_top(xc, yc) - 0.4))])
    for k in range(CAN_N):
        j = (k + 1) % CAN_N
        cx, cy = top_out[k]
        for i in range(4):
            out = (cx, cy - CAN_YC, 0) if i >= 2 else ((-cx, -(cy - CAN_YC), 0) if i == 0 else (0, 0, 1))
            if i == 2:
                out = (cx * 0.5, (cy - CAN_YC) * 0.5, 1)
            F.f((fr[k][i], fr[j][i], fr[j][i + 1], fr[k][i + 1]), FRAME, out=out)


# Wing plan (right side): root leading edge buried in the nose's flank, the leading edge on the
# inner mask's sweep (half width y - 2.1), a short tip at x 6.5 (row 8), the trailing edge swept in
# through row 9's step to the waist at row 10.
WING_PLAN = [(2.2, 4.3), (6.4, 8.5), (6.5, 9.05), (4.45, 10.05), (2.6, 10.05)]
WING_FILLET = ((0.0, 0.3, 0.22, 0.3, 0.0), (1, 3, 2, 2, 1))
WING_Z = 0.15


def wing_points(outline, inset, ztop, zbot):
    pts = []
    for x, y in outline:
        tz = (0.62 - 0.32 * (x - 2.6) / 4.85)  # thickness falls toward the tip
        zc = WING_Z + 0.12 * (x - 2.6) / 4.85  # slight dihedral
        pts.append((x, y, zc + tz * ztop, zc + tz * zbot))
    return pts


def inset_polygon(poly, d):
    """Offset a convex counter-clockwise or clockwise polygon inward by d."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln, dx / ln
        if nx * (cx - x0) + ny * (cy - y0) < 0:
            nx, ny = -nx, -ny
        lines.append((x0 + nx * d, y0 + ny * d, dx, dy))
    out = []
    for i in range(n):
        ax, ay, adx, ady = lines[i - 1]
        bx, by, bdx, bdy = lines[i]
        den = adx * bdy - ady * bdx
        t = ((bx - ax) * bdy - (by - ay) * bdx) / den
        out.append((ax + adx * t, ay + ady * t))
    return out


def build_wings(P):
    outline = fillet(WING_PLAN, *WING_FILLET)
    for side in (1, -1):
        def m(x):
            return side * x
        # The wing: a slab whose edges are chamfered top and bottom to a blunt edge.
        pts = []
        for x, y, zt, zb in wing_points(outline, 0, 0.5, -0.5):
            zc = (zt + zb) / 2
            pts += [(m(x), y, zc + 0.04), (m(x), y, zc - 0.04)]
        for x, y, zt, zb in wing_points(fillet(inset_polygon(WING_PLAN, 0.28), (0.0, 0.18, 0.12, 0.18, 0.0), (1, 3, 2, 2, 1)), 0, 0.5, -0.5):
            pts += [(m(x), y, zt), (m(x), y, zb)]
        hull(P, pts, GUN)
        # Two top armour panels, proud, a seam along the sweep between them; a belly panel.
        front = [(2.5, 5.0), (6.0, 8.45), (6.1, 8.85), (2.5, 7.35)]
        back = [(2.5, 7.6), (6.1, 9.08), (4.45, 9.82), (2.5, 9.82)]
        for poly in (front, back):
            pp = []
            for x, y, zt, zb in wing_points(poly, 0, 0.5, -0.5):
                pp += [(m(x), y, zt - 0.1), (m(x), y, zt + 0.1)]
            for x, y, zt, zb in wing_points(inset_polygon(poly, 0.1), 0, 0.5, -0.5):
                pp += [(m(x), y, zt + 0.2)]
            hull(P, pp, WING)
        under = [(2.5, 5.1), (6.0, 8.6), (6.0, 9.15), (4.45, 9.85), (2.5, 9.85)]
        pp = []
        for x, y, zt, zb in wing_points(under, 0, 0.5, -0.5):
            pp += [(m(x), y, zb + 0.1), (m(x), y, zb - 0.08)]
        for x, y, zt, zb in wing_points(inset_polygon(under, 0.1), 0, 0.5, -0.5):
            pp += [(m(x), y, zb - 0.16)]
        hull(P, pp, BELLY)
        # Wing-tip cap: a darker block on the tip, chamfered.
        pp = []
        for x, y, zt, zb in wing_points([(6.1, 8.3), (6.45, 8.6), (6.47, 9.03), (6.1, 9.22)], 0, 0.5, -0.5):
            pp += [(m(x), y, zt + 0.12), (m(x), y, zb - 0.06)]
        hull(P, pp, GUN)


def build_pods(P, D):
    for side in (1, -1):
        def L(y, side=side):
            return pod_loop(y, side)

        # The core: plain, then the bay rows with the inboard top cut down to the bay floor.
        rings = [(y, *pod_loop(y, side), "") for y in frange(POD_START, BAY_Y0, 0.7)]
        rings.append((BAY_Y0, *pod_loop(BAY_Y0, side, cut=True), "in"))
        rings += [(y, *pod_loop(y, side, cut=True), "") for y in frange(BAY_Y0, BAY_Y1, 0.8)[1:]]
        rings.append((BAY_Y1, *pod_loop(BAY_Y1, side), "out"))
        rings += [(y, *pod_loop(y, side), "") for y in frange(BAY_Y1, POD_END, 0.4)[1:]]

        def mat_of(i, a, b, rings=rings):
            ya, yb = rings[i][0], rings[i + 1][0]
            if BAY_Y0 - 1e-6 <= ya and yb <= BAY_Y1 + 1e-6:
                pa = rings[i + 1][1]
                if abs(pa[a][1] - BAY_Z) < 1e-6 and abs(pa[b][1] - BAY_Z) < 1e-6:
                    return DEEP
            return GUN
        ring_loft(P, rings, mat_of, cap0=DEEP, cap1=GUN)

        def A(a, b, gap=0.0):
            return dict(s0=pod_s(a) + gap, s1=pod_s(b) - gap)
        # Front cowl: armour petals over the intake fairing (rows 10.25-12.0).
        for a, b in ((-48, 57), (57, 133), (133, 224), (224, 312)):
            plate(P, L, 10.25, 12.0, PODF, **A(a, b, 0.12), d=0.24, c=0.1, ystep=0.4)
        # Shell: the inboard top in front of the bay, the outboard top along the whole pod (a
        # lengthwise seam at the top between them), the outboard flank with a raised hatch, the
        # belly with a gear door.
        plate(P, L, 12.15, 17.4, POD, **A(-120, -4), d=POD_PLATE, c=0.12, ystep=0.6)
        plate(P, L, 12.15, 21.55, POD, **A(-1, 58), d=POD_PLATE, c=0.12, ystep=0.6)
        plate(P, L, 12.15, 21.55, POD, **A(61, 132), d=POD_PLATE, c=0.12, ystep=0.6)
        plate(P, L, 12.15, 21.55, POD, **A(135, 236), d=POD_PLATE, c=0.12, ystep=0.6)
        plate(P, L, 14.2, 17.0, POD, **A(70, 118), d=POD_PLATE + 0.14, c=0.08, ystep=0.7)
        plate(P, L, 13.6, 20.2, BELLY, **A(152, 206), d=POD_PLATE + 0.14, c=0.1, ystep=0.9)
        # Rear rim: a dark band round the pod's end, behind a panel break.
        for a, b in ((-118, 57), (57, 133), (133, 236)):
            plate(P, L, 21.7, POD_END + 0.02, GUN, **A(a, b, 0.08), d=0.22, c=0.08, ystep=0.4)
        # The bay: two glowing red light tubes across it (rows 18 and 20) and a grey strut between
        # (row 19), all from the fuselage flank to the outboard plate's edge.
        xi, xo = 2.7, POD_CX(19.5) + 0.25
        for y in (18.5, 20.45):
            tube_x(D, side * xi, side * xo, y, BAY_Z + 0.32, 0.3, TUBE)
            for x in (xi + 0.25, xo - 0.3):  # clamps
                hull(D, [(side * xx, yy, zz) for xx, yy, zz in cbox(x - 0.12, x + 0.12, y - 0.4, y + 0.4, BAY_Z, BAY_Z + 0.5, 0.04)], GUN)
        hull(D, [(side * x, y, z) for x, y, z in cbox(xi, xo, 19.12, 19.88, BAY_Z, BAY_Z + 0.5, 0.1)], STRUT)
        # Intake mouth at the pod's nose.
        cxf = side * POD_CX(10.5)
        hull(D, [(cxf + side * x, y, z) for x, y, z in cbox(-0.28, 0.28, 9.92, 10.15, POD_CZ(10.5) - 0.6, POD_CZ(10.5) + 0.6, 0.05)], DEEP)
        # Ventral strake under the pod: a gunmetal fin, deepest in the middle, chamfered.
        pts = []
        cx = POD_CX(18.0)
        for y, bot in ((14.5, -2.6), (15.6, -3.1), (20.0, -3.1), (21.2, -2.6)):
            pts += [(side * x, y, z) for x, z in ((cx - 0.25, -2.3), (cx + 0.25, -2.3), (cx + 0.18, bot), (cx - 0.18, bot))]
        hull(D, pts, GUN)


def build_nozzles(D):
    """Canted nozzles behind the pods: a red shroud of rounded-rectangle section along the axis
    (outboard-aft at 45 degrees), its exit on the plan diagonal x + y = 29, a dark lip, then a deep
    throat glowing red and a bright core."""
    ex, ey, ez = NOZ_E
    for side in (1, -1):
        def at(t, v, z):
            x = ex + t * NOZ_U[0] + v * NOZ_V[0]
            y = ey + t * NOZ_U[1] + v * NOZ_V[1]
            return (side * x, y, ez + z)
        # (t along the axis, half width a, half height b, corner radius r, material of the band to
        # the next ring, "out"/"in" for a step).
        prof = [
            (-3.6, 2.2, 1.55, 0.9, RED), (-2.2, 2.35, 1.5, 0.9, RED), (-1.6, 2.42, 1.45, 0.9, RED_DK),
            (-1.6, 2.32, 1.35, 0.85, RED_DK), (-1.45, 2.32, 1.35, 0.85, RED_DK), (-1.45, 2.44, 1.44, 0.9, RED),
            (-0.2, 2.55, 1.32, 0.9, RED), (-0.02, 2.5, 1.25, 0.85, RED_DK), (-0.02, 2.22, 0.98, 0.7, RED_DK),
            (-0.35, 2.12, 0.9, 0.65, TUBE), (-1.0, 1.85, 0.7, 0.5, CORE),
        ]
        rings = []
        for t, a, b, r, mat in prof:
            rings.append(([D.v(at(t, v, z)) for v, z in rrect(a, b, r)], t, mat))
        for i in range(len(rings) - 1):
            r0, t0, m0 = rings[i]
            r1, t1, _ = rings[i + 1]
            n = len(r0)
            inside = i >= 8
            c = at((t0 + t1) / 2, 0, 0)
            for k in range(n):
                kk = (k + 1) % n
                quad = (r0[k], r0[kk], r1[kk], r1[k])
                if inside:
                    D.f(quad, m0, out=tuple(-(q - cc) for q, cc in zip(Vector(r0[k].co), c)))
                elif abs(t1 - t0) < 1e-6:
                    # Step: faces aft along the axis when the next ring is smaller.
                    grow = prof[i + 1][1] < prof[i][1]
                    D.f(quad, m0, out=(side * NOZ_U[0] * (1 if grow else -1), NOZ_U[1] * (1 if grow else -1), 0))
                else:
                    D.f(quad, m0, away=c)
        D.f(rings[0][0], RED, out=(-side * NOZ_U[0], -NOZ_U[1], 0))
        D.f(rings[-1][0], CORE, out=(side * NOZ_U[0], NOZ_U[1], 0))


def outline_fill():
    """Blocks for the outline shell only (never drawn) that fill the deep places and ease the tall
    steps seen from above: the pods' bays, ramps from the spine deck's edges down to the pods' tops,
    the tail's slots between the ribs and the nozzles' throats. The ink outline is the shell's back
    faces pushed out on screen, so a deep trench or a tall wall facing away from the camera draws
    an ink line across the hull."""
    Q = Part("silver_fill")
    for side in (1, -1):
        pts = []
        for y in (BAY_Y0 - 0.6, BAY_Y1 + 0.2):
            xo = POD_CX(y) + 0.6
            top = POD_CZ(y) + POD_RZ(y) + POD_PLATE
            pts += [(side * x, y, z) for x in (2.2, xo) for z in (0.0, top)]
        hull(Q, pts, 0)
        pts = []
        for y in (11.5, 14.0, 18.0, 21.4):
            top = POD_CZ(y) + POD_RZ(y) + POD_PLATE
            pts += [(side * 1.55, y, deck_top(y) + 0.1), (side * 1.55, y, 0.0),
                    (side * (POD_CX(y) + 0.3), y, top - 0.05), (side * (POD_CX(y) + 0.3), y, 0.0)]
        hull(Q, pts, 0)
        ex, ey, ez = NOZ_E
        pts = []
        for t in (-1.2, -0.05):
            for v, z in rrect(2.3, 1.1, 0.8):
                pts.append((side * (ex + t * NOZ_U[0] + v * NOZ_V[0]), ey + t * NOZ_U[1] + v * NOZ_V[1], ez + z))
        hull(Q, pts, 0)
        # The pod's rear down onto the nozzle shroud.
        pts = []
        for y in (20.6, 21.9):
            top = POD_CZ(y) + POD_RZ(y) + POD_PLATE
            pts += [(side * x, y, z) for x in (3.0, POD_CX(y) + POD_RX(y)) for z in (-0.5, top)]
        for v, z in rrect(2.0, 1.0, 0.8):
            pts.append((side * (ex - 0.6 * NOZ_U[0] + v * NOZ_V[0]), ey - 0.6 * NOZ_U[1] + v * NOZ_V[1], ez + z))
        hull(Q, pts, 0)
        # The slot between the nozzle shroud and the tail block.
        pts = []
        for y, xo in ((21.6, 4.1), (T(25.2), 3.2), (T(26.2), 2.7)):
            pts += [(side * x, y, z) for x, z in ((2.2, FT(y) + 0.5), (2.2, -1.2), (xo, -1.2), (xo, 0.6))]
        hull(Q, pts, 0)
    # The spine: ramps from the centre ridge's top down to the deck plates' edges, from the canopy's
    # top to the tail block, and the tail's slots filled to the ribs' tops.
    pts = []
    for y in (7.4, 9.4, 15.5, 21.3):
        ridge = FT(y) + (0.8 if y > 9 else GLASS_BASE + GLASS_H + 0.2)
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.3, ridge), (1.6, FT(y) + 0.3), (1.6, FT(y) - 0.5))]
    hull(Q, pts, 0)
    pts = []
    for y, h in ((21.0, 0.8), (21.6, 0.78), (T(25.7), 0.5)):
        pts += [(sx * 2.3, y, z) for sx in (-1, 1) for z in (FT(y) + h, FT(y) - 0.5)]
    hull(Q, pts, 0)
    return Q


# The banking frames' pose (D93, fitted to sprites 77-85 with tools/bank_roll.py --fit): the game's
# roll (17.5 / 35 degrees), but moved sideways only 0 / 0.5 px, not bankShift.ts's 1 / 2. Rolled about
# its axis the ship's high fuselage and low pods already move its top view toward the bank; the
# sprite's banks move it about that much, so bankShift's slide on top overshot (full bank 0.72-0.75
# at bankShift's shift, 0.87 at this one).
BANK_ROLL = [17.5, 35.0]
BANK_SHIFT = [0.5, 0, 0, 0, -0.5]


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Sprite px to Blender: X = (x + AXIS) / 12, Y = (14 - y) / 12, Z = z / 12 (a reflection in y).
    m = Matrix(((PX, 0, 0, AXIS * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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


def build(coll, sprite):
    mats = materials(sprite)
    P = Part("silver_hull", smooth_angle=30)
    build_fuselage(P)
    S = Part("silver_spine", smooth_angle=30)
    build_spine(S)
    G = Part("silver_canopy", smooth_angle=50)
    F = Part("silver_frame", smooth_angle=30)
    build_canopy(G, F)
    W = Part("silver_wings", smooth_angle=30)
    build_wings(W)
    pods = Part("silver_pods", smooth_angle=34)
    det = Part("silver_details", smooth_angle=35)
    build_pods(pods, det)
    N = Part("silver_nozzles", smooth_angle=40)
    build_nozzles(N)
    objs = [finish(p, mats, coll) for p in (P, pods, det, S, G, F, W, N)]
    return objs


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = (NOSE, WING, DECK, POD, PODF, FRAME, STRUT, RIB, GUN, DEEP, RED, RED_DK, SPINE, BELLY)


def bake_maps(obj, out_dir, size=1024, samples=96):
    """The Talon's bake (usp_talon.bake_maps) with this ship's tint and slots: a grey colour
    multiplier (ambient occlusion at two scales plus a light lift on bevelled edges) and a
    metallic-roughness map (G roughness, B metallic), wired in as Base Color = map x palette colour."""
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
        print("silver: no GPU bake", err)
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

    col_img = bpy.data.images.new("silver_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("silver_rm", size // 2, size // 2, alpha=False)
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
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
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
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    obj = join(build(coll, sprite), NAME)
    # The outline shell is made from the closed parts, before hidden faces are culled: remeshing the
    # culled (open) hull wraps both sides of every open plate, and the inner walls drew ink lines
    # along the panel gaps.
    # The bays are filled in it (outline_fill), so their deep walls draw no ink lines either.
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    fill = finish(outline_fill(), [], coll)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (closed, fill))
    bpy.context.view_layer.objects.active = closed
    bpy.ops.object.join()
    cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"silver: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glows (src/ui/backdrop.ts): just outside the two nozzle exits, in
    # glTF axes (x, y up, z aft), red (palette 118's hue).
    ex, ey, ez = NOZ_E
    gx, gy = ex + 0.9 * NOZ_U[0], ey + 0.9 * NOZ_U[1]
    obj["tyrian_engines"] = {"color": "#ff3a1c", "at": [[round((sx * gx + AXIS) * PX, 4), round(ez * PX, 4),
                                                          round((gy - 14) * PX, 4)] for sx in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="silver_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it. As the Talon's
    # (D90): from coarser voxels (0.03) so it bridges the hull's seams and vents, and held just inside
    # the hull; from 0.012 it followed them in and drew ink wedges across the hull.
    shell = common.outline_shell(closed, coll, voxel=0.03, faces=3000, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"silver: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT),
                                   image_format=fmt)
    if "--preview" in argv:
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
