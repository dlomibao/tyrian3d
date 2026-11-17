"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a slim silver dart
built the USP Talon's way (assets/blender/usp_talon.py, DECISIONS D50-D53, D74, D90), rebuilt from
the sprite's own pixels (DECISIONS D229).

What the sprite draws (frame 81, x = column - 11, y = row; measured, D229):
- a slim fuselage, 7 px wide inside its ink: a pointed nose with a bright centre ridge (rows 1-4), a
  small dark windshield with a glint (rows 5-8, columns 10-12), then a bright silver deck 5 px wide
  (columns 9-13, rows 9-21: a near-white collar at row 9, palette 10 behind it, brightening to 13
  over rows 16-18, 9 at row 21) with a 1 px flank each side (column 8 lit, 9; column 14 in shade, 3);
- two small swept canards beside the windshield (rows 6-8, palette 5-6);
- a low delta wing each side of the rear (rows 12-21, palette 7 lit / 5 in shade), a short fairing at
  its root (rows 10-13), a rounded rail on its tip (the outer pixel), a dark trailing corner;
- on each wing, tight against the fuselage, an engine 3 px wide (columns 5-7 / 15-17): a bright swept
  lip from row 14 inboard to row 17 outboard, two red glowing slats (rows 18 and 20) between grey
  bars (rows 19 and 21), and a red tail cut on the diagonal (rows 22-25: dark red rim, a bright core);
- three exhaust pipes behind the fuselage (columns 9, 11 and 13, rows 22-25), ink between them.
So the eye reads a 5 px bright bar with grey and red beside it. The model keeps that: the fuselage is
the only tall, bright part; the wings, the engines and the pipes are low and darker.

The sprite is authoritative for the plan outline, the windshield and the colours: the top view
follows frame 81's inner mask (D74: the game's ink outline stands in for the sprite's dark border)
with smooth curves through the middles of its steps, never the steps themselves, and each part takes
the palette index the sprite uses where it covers it, read on the sprite's lit (left) side. The
sprite's ink between the three pipes is inside the inner mask: it is a dark tray under them (as the
saw rotor's plate, D213).

How it is built (as the Talon):
- Every part is a low-poly cage in sprite px (x across from the ship's centre line, the middle of
  sprite column 11; y = sprite row, aft is +y; z up), moved to Blender at the end
  (X = (x - 0.5) / 12, Y = (14 - y) / 12, Z = z / 12).
- Sections between stations are monotone cubic (pchip), so lofts never swell.
- Dark gunmetal cores under separate armour plates that stand 0.1-0.3 px proud with 45-degree
  chamfers, so panel lines are real gaps. Flat faces stay flat (sharp by angle, weighted normals).
- Texture: no concept projection (texture_bake.py skips this model: "bake": "model" in its
  maps.json). This script bakes ambient occlusion with an edge lift (a colour multiplier, TINT)
  and a roughness/metalness map. Base Color = map x palette colour.
- Palette materials (pal_<index>) so palettes, fades and the hit flash apply; the slats' tubes and
  the engines' throats glow in the palette's reds (D126).
- Exported beside it: an outline shell (common.outline_shell, D51, D90) and `tyrian_engines` (two red
  glows over the engines' tails for the menu backdrop).

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

# Parts and the palette index each takes: the median of the sprite pixels the part covers on the
# sprite's lit side (its left; the right side's darker indices are the same parts in shade, and
# shade is the game's light to give, art rule 2), the ink (1-2) left out; D229's table has each
# region's pixels. Parts of one index share one material (one draw call each in game).
PARTS = {
    "NOSE": 8,       # nose roof, rows 1-4 (left 4-10, mean luma 95; right 5): sloped, so a step up from 7
    "SPINE": 12,     # the nose's centre ridge (column 11: 6, 10, 11, 13), narrow, so a step up
    "FRAME": 9,      # shoulders beside the windshield (left 9; right 4)
    # The deck's plates are level and the game lights a level face brightest (1.12-1.17 times its
    # colour after TINT, measured), so each takes the index one step under its rows' mean tone.
    "COLLAR": 12,    # row 9's bright band (columns 9-12: 12, 12, 15, 12; mean luma 176 with its ends)
    "DECK_A": 9,     # rows 10-12 (mean luma 145, index 10)
    "DECK_B": 10,    # rows 13-15 (160) and 19-20 (172): index 11
    "DECK_C": 12,    # rows 16-18 (199, index 13): the bright middle
    "DECK_E": 8,     # row 21 (124, index 9)
    "FLANK": 9,      # the fuselage's flanks (column 8: 9; column 14: 3, in shade)
    "TAIL": 9,       # the tail cap, rows 21-22
    "CANARD": 6,     # rows 6-8 outboard (left 5, 6, 6, 10; right 3-6)
    "WING": 7,       # the rear wings (left 7; right 5)
    "RAIL": 8,       # the wings' tip rails (column 3: 7, 9, 10, 9; column 19: 6, 7, 7, 6)
    "FAIR": 8,       # the wing-root fairings, rows 10-13 (13, 9, 7, 6)
    "NAC": 9,        # the engines' tops in front of the slats (left 9)
    "LIP": 12,       # their swept front ramps (left 12, 13, 14; right 8, 8, 9)
    "BAR": 10,       # the bar between the slats, row 19 (12, 11, 10; right 8, 9, 9)
    "BAR_LO": 6,     # the bar behind them, row 21, and the pipes' manifold (6)
    "PIPE": 10,      # the outer exhaust pipes (columns 9 and 13: 7-9; a pipe seen whole reads two steps under its crown)
    "PIPE_MID": 8,   # the middle one (column 11: 6-7)
    "GUN": 4,        # cores, the canards' roots
    "DEEP": 2,       # bores, the wings' trailing corners
    "TRAY": 1,       # the sprite's ink between the pipes
    "BELLY": 6,
    "RED_DK": 113,   # the red tails' rims and shrouds
    "RED_SH": 114,   # their walls, the slats' troughs
    "RED": 115,      # the throats' floors
    "TUBE": 117,     # the slats' glowing tubes
    "CORE": 118,     # the throats' cores
}
# Each index's finish: (metallic before METAL, roughness, glow). The reds glow at 1 (D126): the
# palette colour as the sprite shows it, whatever the light.
FINISH = {1: (0.2, 0.85, 0.0), 2: (0.3, 0.8, 0.0), 4: (0.5, 0.46, 0.0), 6: (0.5, 0.45, 0.0), 7: (0.5, 0.42, 0.0),
          8: (0.55, 0.4, 0.0), 9: (0.55, 0.36, 0.0), 10: (0.65, 0.3, 0.0), 12: (0.7, 0.26, 0.0),
          113: (0.0, 0.9, 0.7), 114: (0.0, 0.9, 1.0), 115: (0.0, 0.9, 1.0), 117: (0.0, 0.9, 1.0), 118: (0.0, 0.9, 1.0)}
PALS = sorted(set(PARTS.values()))
# Each part's material slot, in PARTS' order.
(NOSE, SPINE, FRAME, COLLAR, DECK_A, DECK_B, DECK_C, DECK_E, FLANK, TAIL, CANARD, WING, RAIL, FAIR, NAC, LIP, BAR, BAR_LO,
 PIPE, PIPE_MID, GUN, DEEP, TRAY, BELLY, RED_DK, RED_SH, RED, TUBE, CORE) = (PALS.index(i) for i in PARTS.values())
GLASS = len(PALS)  # palette 1 again, glossy and untextured

# Metalness scale (satin, as the Talon's D53).
METAL = 0.22
# The baked colour map's tint (linear multipliers): neutral grey with the blue trimmed, since the
# game's blue sky light leans the ship cool, and 0.88 overall: untinted, the game lights a level
# face to about 1.2 times its palette colour (the deck's index 10 measured 167-171 against 142,
# D229); with this the sloped and shaded parts come out at their sprite tones.
TINT = (0.88, 0.845, 0.72)


def materials(sprite):
    mats = [common.palette_material(sprite, idx, "silver", metallic=FINISH[idx][0] * METAL, roughness=FINISH[idx][1],
                                    emission_strength=FINISH[idx][2]) for idx in PALS]
    mats.append(common.palette_material(sprite, 1, "silver_glass", metallic=0.0, roughness=0.05))
    return mats


# --- the plan (sprite px, x from the centre line, y = row) --------------------------------------
#
# Frame 81's INNER mask (D74, docs/agents/OUTLINE-BORDER.md), half width by row:
#   rows 1-2 1.5 | 3-4 2.5 | 5 3.5 | 6 4.5 | 7 5.5 | 8 6.5 (canard tips) | 9 5.5 | 10-11 4.5 |
#   12 5.5 | 13 6.5 | 14 7.5 | 15-20 8.5 (wing tips) | 21 7.5 | 22 6.5 | 23 6.5 / 5.5 | 24 4.5 | 25 3.5
# Each outboard edge is one smooth line through the middles of those steps (D118): the nose a blunt
# ogive from row 0.95, the canard's leading edge half width y - 2.1 to a tip at row 8, its trailing
# edge one sweep in to the waist, the wing's leading edge half width y - 7 from the waist to the tip
# at 8.5, the rear edge the diagonal x + y = 29, the tray's end at row 26.

PL = 0.25          # the fuselage's armour plates stand this far out of its core
Y_NOSE = 0.95
Y_DECK = 9.05      # the deck's front edge, behind the windshield (the sprite's bright row 9)
Y_FUSE_END = 22.05  # the fuselage's rear face; the pipes and their tray run on to row 26
Y_END = 26.03

_FY = [0.95, 1.15, 1.45, 1.9, 2.4, 2.9, 3.4, 3.9, 4.4, 5.0, 5.8, 7.0, 8.6, Y_DECK, 12.0, 16.0, 20.5, 21.3, 21.7, Y_FUSE_END]
# Plated half width (the outline in front of the canards and at the waist), top and keel.
WO = pchip(_FY, [0.58, 0.9, 1.2, 1.44, 1.64, 1.88, 2.1, 2.26, 2.42, 2.73, 3.2, 3.4, 3.45, 3.45, 3.45, 3.45, 3.45,
                 3.45, 3.4, 3.3])
TO = pchip(_FY, [0.55, 0.7, 0.88, 1.08, 1.26, 1.4, 1.52, 1.62, 1.72, 1.84, 1.95, 2.0, 2.05, 2.3, 2.3, 2.3, 2.3,
                 2.26, 2.05, 1.7])
BO = pchip(_FY, [-0.1, -0.24, -0.4, -0.6, -0.8, -0.95, -1.05, -1.15, -1.22, -1.3, -1.3, -1.3, -1.3, -1.3, -1.3,
                 -1.3, -1.3, -1.25, -1.2, -1.15])
# The top is flat (the nose's ridge, the windshield's sill, the deck) with a chamfer along each edge
# that drops CH out to half width DE; from there the flank falls to the full width at height ZF.
DE = pchip(_FY, [0.2, 0.24, 0.3, 0.38, 0.46, 0.54, 0.57, 0.6, 0.74, 1.38, 1.82, 1.82, 1.9, 2.6, 2.6, 2.6, 2.6,
                 2.6, 2.55, 2.45])
CH = pchip(_FY, [0.06, 0.06, 0.08, 0.08, 0.1, 0.1, 0.1, 0.1, 0.12, 0.16, 0.18, 0.18, 0.2, 0.32, 0.32, 0.32, 0.32,
                 0.32, 0.3, 0.28])
ZF = pchip(_FY, [0.3, 0.36, 0.45, 0.55, 0.64, 0.72, 0.8, 0.86, 0.9, 0.95, 0.95, 0.95, 0.95, 1.0, 1.0, 1.0, 1.0,
                 1.0, 0.95, 0.85])
FLAT = 0.8  # the flat top's share of DE; the chamfer is the rest
CROWN = ((0.4, 0.0), (FLAT, 0.0), (1.0, 1.0))  # (fraction of DE, fraction of CH)
N_LOOP = 14


def fuselage_loop(y):
    """The fuselage core's closed section: s = 0 top centre, 1-2 on the flat top (2 its edge), 3 the chamfer's foot,
    4 the flank's foot (the full width), 5 the wall's foot, 6 the chine, 7 the keel, then back up
    the left side (8-13)."""
    w, t, b = WO(y) - PL, TO(y) - PL, BO(y) + 0.12
    h = t - b
    de = min(DE(y), 0.84 * w)
    c = CH(y)
    zf = min(ZF(y) - 0.08, t - c - 0.08 * h)
    zb = min(b + 0.42 * h, zf - 0.1 * h)
    right = [(0.0, t)] + [(de * fx, t - c * fz) for fx, fz in CROWN]
    right += [(w, zf), (0.92 * w, zb), (0.5 * w, b + 0.07 * h), (0.0, b)]
    pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return pts, (0.0, (t + b) / 2)


def deck_top(y):
    return TO(y)


def hull_top(x, y):
    """The plated fuselage's top at (x, y)."""
    ax = abs(x)
    de, t, c = DE(y), TO(y), CH(y)
    if ax <= de:
        return t - c * max(0.0, (ax / de - FLAT) / (1 - FLAT))
    return t - c - (t - c - ZF(y)) * min(1.0, (ax - de) / max(1e-6, WO(y) - de))


def LS(side, a, b):
    """A plate's loop range on the right (a..b), mirrored for the left."""
    return dict(s0=a, s1=b) if side > 0 else dict(s0=N_LOOP - b, s1=N_LOOP - a)


# --- mesh helpers ----------------------------------------------------------------------------

def inset_polygon(poly, d):
    """Offset a convex polygon inward by d."""
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


def slab(part, side, poly, ztop, zbot, mat, ch=0.08):
    """A convex plan polygon [(x, y)] (right side; mirrored for side -1) from zbot(x, y) up to
    ztop(x, y), its top edge chamfered `ch`: a block, a raised panel or a rail."""
    pts = []
    for x, y in poly:
        pts += [(side * x, y, ztop(x, y) - ch), (side * x, y, zbot(x, y))]
    for x, y in inset_polygon(poly, ch):
        pts.append((side * x, y, ztop(x, y)))
    hull(part, pts, mat)


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


def pipe_y(part, xc, zc, stations, mat, bore_mat, n=12, bore=0.62, depth=0.6):
    """An exhaust pipe along y through stations [(y, radius)] (two at one y make a step), open at
    its aft end: a rim and a dark bore."""
    def ring(y, r):
        return [part.v((xc + r * math.sin(2 * math.pi * (k + 0.5) / n), y, zc + r * math.cos(2 * math.pi * (k + 0.5) / n)))
                for k in range(n)]
    rings = [ring(y, r) for y, r in stations]
    for (y0, ra), (y1, rb), r0, r1 in zip(stations, stations[1:], rings, rings[1:]):
        for k in range(n):
            kk = (k + 1) % n
            if abs(y1 - y0) < 1e-9:
                part.f((r0[k], r0[kk], r1[kk], r1[k]), mat, out=(0, -1 if rb > ra else 1, 0))
            else:
                part.f((r0[k], r0[kk], r1[kk], r1[k]), mat, away=(xc, (y0 + y1) / 2, zc))
    part.f(rings[0], mat, out=(0, -1, 0))
    y1, r1 = stations[-1]
    lip = ring(y1, r1 * bore)
    deep = ring(y1 - depth, r1 * bore)
    c = Vector((xc, y1 - depth / 2, zc))
    for k in range(n):
        kk = (k + 1) % n
        part.f((rings[-1][k], rings[-1][kk], lip[kk], lip[k]), mat, out=(0, 1, 0))
        mid = (Vector(lip[k].co) + Vector(lip[kk].co)) / 2
        part.f((lip[k], lip[kk], deep[kk], deep[k]), bore_mat, out=tuple(c - mid))
    part.f(deep, bore_mat, out=(0, 1, 0))


# --- the fuselage ------------------------------------------------------------------------------

def build_fuselage(P):
    L = fuselage_loop
    ys = [Y_NOSE, 1.1, 1.35, 1.7] + frange(2.1, 8.6, 0.8) + frange(Y_DECK, 21.3, 0.8)[:-1] + [21.3, 21.7, Y_FUSE_END]
    loft(P, L, ys, GUN)
    # Nose cone (rows 1.3-4.75), all round, its back edge chamfered; a tip over its front edge.
    plate(P, L, 1.3, 4.75, NOSE, d=PL, ch0=False, ystep=0.35)
    sec = Section(L, 1.3)
    tip = [sec.at(k, PL) for k in range(sec.n)]
    hull(P, tip + [(0.0, Y_NOSE + 0.03, (TO(Y_NOSE) + BO(Y_NOSE)) / 2)], NOSE)
    for side in (1, -1):
        # The shoulders beside the windshield, a panel break at row 7.
        for y0, y1 in ((4.9, 6.95), (7.1, 8.92)):
            plate(P, L, y0, y1, FRAME, **LS(side, 3.06, 4.94), d=PL, c=0.12)
        # The flanks under the deck, a panel break at row 15 (the deck's own).
        for y0, y1 in ((Y_DECK + 0.02, 15.96), (16.04, 21.24)):
            plate(P, L, y0, y1, FLANK, **LS(side, 3.06, 4.94), d=PL, c=0.1)
        plate(P, L, 21.36, Y_FUSE_END - 0.02, GUN, **LS(side, 3.06, 4.94), d=PL - 0.05, c=0.1, ch1=False)
    # The sill under the windshield.
    plate(P, L, 4.9, 8.92, FRAME, s0=-2.94, s1=2.94, d=PL - 0.05, c=0.1)
    # The collar: one bright band across the deck's front end (the sprite's row 9).
    plate(P, L, Y_DECK + 0.02, 9.96, COLLAR, s0=-2.94, s1=2.94, d=PL, c=0.05, ystep=0.5)
    # The deck: five plates in the sprite's tones by row, brightest over rows 16-18 (the sprite's
    # white there is sheen; a level deck under the game's sun cannot grade itself, so the plates
    # carry the grades, D176, D213).
    for y0, y1, mat in ((10.08, 12.96, DECK_A), (13.04, 15.96, DECK_B), (16.04, 18.96, DECK_C), (19.04, 20.46, DECK_B),
                        (20.54, 21.24, DECK_E)):
        plate(P, L, y0, y1, mat, s0=-2.94, s1=2.94, d=PL, c=0.05, ystep=0.9)
    # The tail cap: the deck's end sloping down to the pipes.
    plate(P, L, 21.36, Y_FUSE_END - 0.02, TAIL, s0=-2.94, s1=2.94, d=PL, c=0.1, ystep=0.25, ch1=False)
    # Belly panels and a keel strake.
    for y0, y1 in ((4.9, 9.6), (9.75, 15.5), (15.65, Y_FUSE_END - 0.1)):
        plate(P, L, y0, y1, BELLY, s0=5.06, s1=8.94, d=0.15, c=0.1, ystep=0.9)
    pts = []
    for y, drop in ((10.5, 0.1), (12.0, 0.4), (19.5, 0.4), (21.5, 0.1)):
        b = BO(y)
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.3, b + 0.3), (0.2, b - drop), (0.08, b - drop - 0.06))]
    hull(P, pts, GUN)


def build_spine(P):
    # The nose's ridge: a polished strip from row 1.8 to the windshield's sill (the sprite's light
    # centre pixels at rows 2-4 are sheen on it).
    pts = []
    for y in frange(1.8, 4.7, 0.4):
        hw = min(0.5, 0.22 + 0.3 * (y - 1.8))
        top = TO(y) + 0.09
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((hw - 0.08, top), (hw, top - 0.08), (hw, TO(y) - 0.25))]
    hull(P, pts, SPINE)


# Windshield: the sprite's dark cockpit pixels (column 11 at row 5, columns 10-12 at rows 6-8:
# |x| <= 1.5, y 5-9), pointed forward, square behind.
CAN_Y0, CAN_Y1, CAN_YC, CAN_W = 5.0, 8.9, 7.5, 1.5
CAN_N = 40
GLASS_BASE = 0.1
GLASS_H = 0.52


def canopy_outline(grow=0.0):
    pts = []
    for k in range(CAN_N):
        a = 2 * math.pi * k / CAN_N  # 0 = right, pi/2 = forward
        c, s = math.cos(a), math.sin(a)
        if s >= 0:
            n, b = 1.7, CAN_YC - CAN_Y0
        else:
            n, b = 4.0, CAN_Y1 - CAN_YC
        e = 2 / n
        x = CAN_W * math.copysign(abs(c) ** e, c)
        yv = math.copysign(abs(s) ** e, s)
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


def build_canopy(G, F):
    C = canopy_outline()
    K = 8
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
    # Frame: a thin sill from the glass edge out over the deck, flat top, chamfered outer edge.
    inner = canopy_outline(-0.05)
    top_out = canopy_outline(0.13)
    ch_out = canopy_outline(0.22)
    fr = []
    for k in range(CAN_N):
        xi, yi = inner[k]
        xo, yo = top_out[k]
        xc, yc = ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.1
        fr.append([F.v((xi, yi, deck_top(yi) + GLASS_BASE - 0.3)), F.v((xi, yi, zt)), F.v((xo, yo, zt)),
                   F.v((xc, yc, zt - 0.1)), F.v((xc, yc, hull_top(xc, yc) - 0.3))])
    for k in range(CAN_N):
        j = (k + 1) % CAN_N
        cx, cy = top_out[k]
        for i in range(4):
            out = (cx, cy - CAN_YC, 0) if i >= 2 else ((-cx, -(cy - CAN_YC), 0) if i == 0 else (0, 0, 1))
            if i == 2:
                out = (cx * 0.5, (cy - CAN_YC) * 0.5, 1)
            F.f((fr[k][i], fr[j][i], fr[j][i + 1], fr[k][i + 1]), FRAME, out=out)


# --- canards -----------------------------------------------------------------------------------

# Plan (right side): the root buried in the fuselage's flank, the leading edge on the inner mask's
# sweep (half width y - 2.1), a short tip at x 6.5 (row 8), the trailing edge swept in through row
# 9's step to the waist at row 10 (D118's, unchanged).
CANARD_PLAN = [(2.2, 4.3), (6.4, 8.5), (6.5, 9.05), (4.45, 10.05), (2.6, 10.05)]
CANARD_FILLET = ((0.0, 0.3, 0.22, 0.3, 0.0), (1, 3, 2, 2, 1))
CANARD_Z = 0.05


def canard_points(outline, ztop, zbot):
    pts = []
    for x, y in outline:
        tz = (0.5 - 0.24 * (x - 2.6) / 3.9)  # thickness falls toward the tip
        zc = CANARD_Z - 0.06 * (x - 2.6) / 3.9
        pts.append((x, y, zc + tz * ztop, zc + tz * zbot))
    return pts


def build_canards(P):
    outline = fillet(CANARD_PLAN, *CANARD_FILLET)
    for side in (1, -1):
        def m(x):
            return side * x
        # The blade: a slab whose edges are chamfered top and bottom to a blunt edge.
        pts = []
        for x, y, zt, zb in canard_points(outline, 0.5, -0.5):
            zc = (zt + zb) / 2
            pts += [(m(x), y, zc + 0.04), (m(x), y, zc - 0.04)]
        for x, y, zt, zb in canard_points(fillet(inset_polygon(CANARD_PLAN, 0.28), (0.0, 0.18, 0.12, 0.18, 0.0), (1, 3, 2, 2, 1)), 0.5, -0.5):
            pts += [(m(x), y, zt), (m(x), y, zb)]
        hull(P, pts, GUN)
        # One top armour panel from the root seam (the sprite's dark column beside the fuselage)
        # to the tip, a belly panel.
        top = [(4.3, 6.75), (6.02, 8.47), (6.1, 8.95), (4.45, 9.76), (4.3, 9.76)]
        pp = []
        for x, y, zt, zb in canard_points(top, 0.5, -0.5):
            pp += [(m(x), y, zt - 0.08), (m(x), y, zt + 0.07)]
        for x, y, zt, zb in canard_points(inset_polygon(top, 0.1), 0.5, -0.5):
            pp += [(m(x), y, zt + 0.15)]
        hull(P, pp, CANARD)
        under = [(2.5, 5.1), (6.0, 8.6), (6.0, 9.15), (4.45, 9.85), (2.5, 9.85)]
        pp = []
        for x, y, zt, zb in canard_points(under, 0.5, -0.5):
            pp += [(m(x), y, zb + 0.1), (m(x), y, zb - 0.06)]
        for x, y, zt, zb in canard_points(inset_polygon(under, 0.1), 0.5, -0.5):
            pp += [(m(x), y, zb - 0.12)]
        hull(P, pp, BELLY)


# --- rear wings, engines, pipes ----------------------------------------------------------------

# The wing's plan (right side): leading edge on half width y - 7 from the waist (4.55 at row 11.55) to
# the tip (8.5 at row 15.5), the tip straight to row 20.5, the rear edge the diagonal x + y = 29,
# which the engine's red tail carries on in to the tray at row 25.5. Low and thin, with a little
# anhedral.
WING_PLAN = [(3.2, 11.45), (4.55, 11.55), (8.5, 15.5), (8.5, 20.5), (6.45, 22.55), (3.2, 22.55)]
WING_FILLET = ((0.0, 0.25, 0.75, 0.6, 0.0, 0.0), (1, 2, 4, 4, 1, 1))
WING_ROOT_Z, WING_DROP = 0.4, 0.13  # the top at x = 3.5, and its fall per px outboard
WING_BOT = -0.55
RAIL_PLAN = [(7.3, 14.6), (8.47, 15.77), (8.47, 19.55), (7.3, 20.35)]


def wing_top(x, y=0.0):
    return WING_ROOT_Z - WING_DROP * (x - 3.5)


def lip_y(x):
    """The engine lip's centre line: through the sprite's bright pixels (7, 14), (6, 16), (5, 17)."""
    return 13.75 + 1.5 * (x - 3.5)


NAC_X0, NAC_X1 = 3.3, 6.52  # the engine's inboard side (in the fuselage's flank) and its outboard wall
SLAT_Y0, SLAT_Y1 = 18.0, 22.0
NAC_PLATE = 0.12
LIP_HALF = 0.46  # half the lip's depth along y
TROUGH = 0.36


def nac_top(x, y=0.0):
    return 1.04 - 0.1 * (x - 3.5)


def build_wings(P):
    outline = fillet(WING_PLAN, *WING_FILLET)
    inner = fillet(inset_polygon(WING_PLAN, 0.3), (0.0, 0.15, 0.5, 0.4, 0.0, 0.0), (1, 2, 4, 4, 1, 1))
    for side in (1, -1):
        pts = []
        for x, y in outline:
            zc = (wing_top(x) + WING_BOT) / 2
            pts += [(side * x, y, zc + 0.05), (side * x, y, zc - 0.05)]
        for x, y in inner:
            pts += [(side * x, y, wing_top(x)), (side * x, y, WING_BOT)]
        hull(P, pts, GUN)
        # Top armour: the panel between the leading edge and the engine's lip (the wing's first row
        # stays dark, as the sprite's row 12), and a strip outboard of the engine to row 20.
        lead = [(5.3, 12.6), (6.62, 13.92), (6.62, lip_y(6.62) - LIP_HALF - 0.3), (3.75, lip_y(3.75) - LIP_HALF - 0.3), (3.75, 12.6)]
        slab(P, side, lead, lambda x, y: wing_top(x) + 0.1, lambda x, y: wing_top(x) - 0.1, WING, ch=0.07)
        strip = [(6.74, 14.04), (7.14, 14.44), (7.14, 20.1), (6.74, 20.1)]
        slab(P, side, strip, lambda x, y: wing_top(x) + 0.1, lambda x, y: wing_top(x) - 0.1, WING, ch=0.06)
        # The tip rail: the wing's rounded outer pixel (the sprite's column 3 is lighter than column 4
        # over rows 16-18), ending at row 20; behind it the wing's dark trailing corner (the sprite's
        # 4, 2 and ink at rows 20-21).
        rail = fillet(RAIL_PLAN, (0.1, 0.5, 0.45, 0.25), (1, 3, 3, 2))
        mid = fillet(inset_polygon(RAIL_PLAN, 0.14), (0.1, 0.4, 0.35, 0.2), (1, 3, 3, 2))
        crown = fillet(inset_polygon(RAIL_PLAN, 0.4), 0.15, 2)
        pts = [(side * x, y, wing_top(x) - 0.12) for x, y in rail]
        pts += [(side * x, y, wing_top(x) + 0.22) for x, y in mid]
        pts += [(side * x, y, wing_top(x) + 0.38) for x, y in crown]
        hull(P, pts, RAIL)
        flap = [(6.74, 20.42), (8.3, 20.52), (6.74, 22.08)]
        slab(P, side, flap, lambda x, y: wing_top(x) + 0.06, lambda x, y: wing_top(x) - 0.1, DEEP, ch=0.05)
        # The root fairing along the fuselage's flank (rows 10-13.3): a bullet, its nose at the waist.
        pts = []
        for y, x1, zt in ((10.08, 3.9, 0.5), (10.45, 4.3, 0.78), (11.0, 4.43, 0.9), (13.3, 4.43, 0.94)):
            pts += [(side * x, y, z) for x, z in ((3.2, zt), (x1 - 0.22, zt), (x1, zt - 0.22), (x1, -0.45), (3.2, -0.45))]
        hull(P, pts, FAIR)


def build_engines(P, D):
    for side in (1, -1):
        # Core: the front block behind the swept lip, then the slat section, its top at the troughs' floor.
        front = [(NAC_X0, lip_y(NAC_X0) + 0.2), (NAC_X1, min(SLAT_Y0 - 0.02, lip_y(NAC_X1) + 0.2)), (NAC_X1, SLAT_Y0), (NAC_X0, SLAT_Y0)]
        slab(P, side, front, lambda x, y: nac_top(x) - NAC_PLATE, lambda x, y: -0.4, GUN, ch=0.1)
        slats = [(NAC_X0, SLAT_Y0), (NAC_X1, SLAT_Y0), (NAC_X1, SLAT_Y1), (NAC_X0, SLAT_Y1)]
        slab(P, side, slats, lambda x, y: nac_top(x) - TROUGH, lambda x, y: -0.4, GUN, ch=0.03)
        # Side rails along the slats, thin (the sprite's red runs the engine's full 3 px).
        for x0, x1 in ((NAC_X0, 3.62), (6.36, NAC_X1)):
            rail = [(x0, SLAT_Y0 - 0.05), (x1, SLAT_Y0 - 0.05), (x1, SLAT_Y1), (x0, SLAT_Y1)]
            slab(P, side, rail, lambda x, y: nac_top(x) - 0.02, lambda x, y: nac_top(x) - TROUGH - 0.1, GUN, ch=0.05)
        # The top plate in front of the slats (the sprite's 9s between the lip and the first slat).
        top = [(3.66, lip_y(3.66) + LIP_HALF + 0.12), (5.82, lip_y(5.82) + LIP_HALF + 0.12), (5.82, SLAT_Y0 - 0.04), (3.66, SLAT_Y0 - 0.04)]
        slab(P, side, top, nac_top, lambda x, y: nac_top(x) - NAC_PLATE - 0.1, NAC, ch=0.07)
        # The lip: a polished ramp on the swept front edge, from the wing up to the engine's top
        # (the sprite's bright diagonal, 1 px deep).
        pts = []
        for x in (NAC_X0 + 0.05, NAC_X1 - 0.03):
            yf, yr = lip_y(x) - LIP_HALF, lip_y(x) + LIP_HALF
            pts += [(side * x, yf, wing_top(x) + 0.2), (side * x, yf, wing_top(x) - 0.1),
                    (side * x, yr - 0.12, nac_top(x) + 0.05), (side * x, yr, nac_top(x) - 0.04),
                    (side * x, yr, nac_top(x) - NAC_PLATE - 0.1)]
        hull(P, pts, LIP)
        # Two red troughs (rows 18 and 20), each with a glowing tube, and the bars behind them
        # (row 19 bright, row 21 darker).
        for y0, y1, mat in ((19.04, 19.96, BAR), (21.04, 21.94, BAR_LO)):
            bar = [(3.64, y0), (6.34, y0), (6.34, y1), (3.64, y1)]
            slab(P, side, bar, nac_top, lambda x, y: nac_top(x) - TROUGH - 0.1, mat, ch=0.08)
        for y0, y1 in ((18.06, 19.02), (19.98, 21.02)):
            floor = [(3.64, y0), (6.34, y0), (6.34, y1), (3.64, y1)]
            slab(D, side, floor, lambda x, y: nac_top(x) - TROUGH + 0.05, lambda x, y: nac_top(x) - TROUGH - 0.1,
                 RED_SH, ch=0.02)
            yc = (y0 + y1) / 2
            zc = nac_top(5.0) - TROUGH + 0.24
            tube_x(D, side * 4.0, side * 6.0, yc, zc, 0.2, TUBE)
            for x in (3.86, 6.14):  # clamps
                hull(D, [(side * xx, yy, zz) for xx, yy, zz in cbox(x - 0.1, x + 0.1, yc - 0.28, yc + 0.28,
                                                                       nac_top(x) - TROUGH, nac_top(x) - 0.08, 0.04)], GUN)


# The red tails: each engine ends in a nozzle cut on the wing's rear diagonal, its opening facing up
# and aft, so the game's camera (overhead, 15 degrees from behind) looks into the glowing throat:
# a dark red rim, lit red walls, a bright core, as the sprite's rows 22-25.
NOZ_RIM = [(3.42, 22.02), (6.5, 22.02), (6.5, 22.47), (3.56, 25.41), (3.42, 25.41)]
NOZ_C = (4.85, 23.35)


def noz_z(y):
    return 0.86 - 0.22 * (y - 22.0)


def noz_scaled(k):
    return [(NOZ_C[0] + (x - NOZ_C[0]) * k, NOZ_C[1] + (y - NOZ_C[1]) * k) for x, y in NOZ_RIM]


def build_nozzles(D):
    n = len(NOZ_RIM)
    for side in (1, -1):
        def ring(poly, dz):
            return [D.v((side * x, y, noz_z(y) + dz)) for x, y in poly]
        rim = ring(NOZ_RIM, -0.06)
        rim_in = ring(noz_scaled(0.94), 0.0)
        lip = ring(noz_scaled(0.8), 0.0)
        floor = ring(noz_scaled(0.72), -0.22)
        core = ring(noz_scaled(0.36), -0.22)
        bot = [D.v((side * x, y, -0.5)) for x, y in NOZ_RIM]
        c = (side * NOZ_C[0], NOZ_C[1], 0.2)
        for i in range(n):
            j = (i + 1) % n
            mx, my = (NOZ_RIM[i][0] + NOZ_RIM[j][0]) / 2, (NOZ_RIM[i][1] + NOZ_RIM[j][1]) / 2
            inward = (side * (NOZ_C[0] - mx), NOZ_C[1] - my, 0.4)
            D.f((rim[i], rim[j], bot[j], bot[i]), RED_DK, away=c)
            D.f((rim[i], rim[j], rim_in[j], rim_in[i]), RED_DK, out=(0, 0, 1))
            D.f((rim_in[i], rim_in[j], lip[j], lip[i]), RED_DK, out=(0, 0, 1))
            D.f((lip[i], lip[j], floor[j], floor[i]), RED_SH, out=inward)
            D.f((floor[i], floor[j], core[j], core[i]), RED, out=(0, 0, 1))
        D.f(core, CORE, out=(0, 0, 1))
        D.f(bot, RED_DK, out=(0, 0, -1))


PIPES = ((-2.0, PIPE, 0.5, 0.12), (0.0, PIPE_MID, 0.47, 0.06), (2.0, PIPE, 0.5, 0.12))
TRAY_Z0, TRAY_Z1 = -0.95, -0.42


def build_tail(P, D):
    # The tray: the sprite's ink between and beside the pipes (columns 8, 10, 12 and 14, rows 22-25),
    # a dark heat shield under them out to the engines' tails.
    hull(P, cbox(-3.44, 3.44, Y_FUSE_END - 0.3, Y_END, TRAY_Z0, TRAY_Z1, 0.08), TRAY)
    # The manifold the pipes leave (row 22: 9, 6, 11, 6, 8).
    hull(P, cbox(-2.62, 2.62, Y_FUSE_END - 0.2, 22.95, TRAY_Z1 - 0.05, 0.42, 0.1), BAR_LO)
    for xc, mat, r, zc in PIPES:
        pipe_y(D, xc, zc, [(Y_FUSE_END - 0.3, r), (25.5, r), (25.5, r + 0.07), (Y_END - 0.06, r + 0.07)], mat, DEEP)
        # A saddle under each pipe.
        hull(D, cbox(xc - 0.3, xc + 0.3, 23.9, 24.5, TRAY_Z1 - 0.05, zc - r + 0.12, 0.05), GUN)


def outline_fill():
    """Blocks for the outline shell only (never drawn).
    - The engines' troughs and throats are filled: the ink outline is the shell's back faces pushed
      out on screen, so a trench draws an ink line across the red. The gaps between the pipes are
      left open: the sprite inks them.
    - The wings and the canards are thinner at their edges than the shell's voxels (0.36 px), which
      wore the shell back from the silhouette there; each gets a prism of its own plan, thick enough
      to survive the remesh, so the ink stands on the model's edge."""
    Q = Part("silver_fill")
    for side in (1, -1):
        pts = []
        for x in (NAC_X0, NAC_X1):
            pts += [(side * x, y, z) for y in (SLAT_Y0 - 0.2, SLAT_Y1 + 0.1) for z in (nac_top(x) - 0.04, 0.0)]
        hull(Q, pts, 0)
        pts = []
        for x, y in noz_scaled(0.95):
            pts += [(side * x, y, noz_z(y) - 0.03), (side * x, y, -0.3)]
        hull(Q, pts, 0)
        pts = []
        for x, y in fillet(WING_PLAN, *WING_FILLET):
            pts += [(side * x, y, min(wing_top(x), -0.1)), (side * x, y, WING_BOT - 0.45)]
        hull(Q, pts, 0)
        pts = []
        for x, y, zt, zb in canard_points(fillet(CANARD_PLAN, *CANARD_FILLET), 0.5, -0.5):
            pts += [(side * x, y, max(zt - 0.12, 0.05)), (side * x, y, zb - 0.45)]
        hull(Q, pts, 0)
    return Q


# The banking frames' pose (D93, fitted to sprites 77-85 with tools/bank_roll.py --fit).
BANK_ROLL = [17.5, 30.0]
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
    C = Part("silver_canards", smooth_angle=30)
    build_canards(C)
    W = Part("silver_wings", smooth_angle=34)
    build_wings(W)
    E = Part("silver_engines", smooth_angle=30)
    det = Part("silver_details", smooth_angle=40)
    build_engines(E, det)
    N = Part("silver_nozzles", smooth_angle=30)
    build_nozzles(N)
    T = Part("silver_tail", smooth_angle=30)
    build_tail(T, det)
    return [finish(p, mats, coll) for p in (P, S, G, F, C, W, E, det, N, T)]


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = tuple(i for i, idx in enumerate(PALS) if FINISH[idx][2] == 0.0)


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
    # along the panel gaps (D118). The engines' troughs and throats are filled in it (outline_fill).
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
    # The menu backdrop's engine glows (src/ui/backdrop.ts): over the two red throats, in glTF axes
    # (x, y up, z aft), red (palette 118's hue).
    gx, gy, gz = NOZ_C[0], NOZ_C[1] + 0.5, 0.45
    obj["tyrian_engines"] = {"color": "#ff3a1c", "at": [[round((sx * gx + AXIS) * PX, 4), round(gz * PX, 4),
                                                          round((gy - 14) * PX, 4)] for sx in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="silver_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it. As the Talon's
    # (D90): from coarse voxels (0.03) so it bridges the hull's seams, and held just inside the hull.
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
