"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a hard-surface
fighter built the USP Talon's way (assets/blender/usp_talon.py, DECISIONS D50-D53, D74, D90), a
sculpted fuselage between two low armour shells (DECISIONS D238, which replaces D229's painted
deck and thin wings and keeps D229's reading of the sprite).

What the sprite draws (frame 81, x = column - 11, y = row; measured in D229):
- a slim fuselage, 7 px wide inside its ink: a pointed nose with a bright centre ridge (rows 1-4), a
  small dark windshield (rows 5-8, columns 10-12), a near-white collar behind it (row 9), then a
  bright deck 5 px wide (columns 9-13, rows 9-21) between a lit flank (column 8) and a flank in
  shade (column 14);
- two small swept canards beside the windshield (rows 6-8);
- a low grey shell each side of the rear (rows 12-21): a swept front, a lighter outer rail, a dark
  trailing corner, a short fairing at its root (rows 10-13);
- on each shell, tight against the fuselage, an engine 3 px wide (columns 5-7 / 15-17): a bright
  swept lip (row 14 inboard to row 17 outboard), two red glowing grooves (rows 18 and 20) between
  grey bands (rows 19 and 21), and a red tail cut on the diagonal (rows 22-25) with a bright core;
- three exhaust pipes behind the fuselage (columns 9, 11 and 13, rows 22-25), ink between them.
The eye reads a 5 px bright bar with grey and red beside it. The model gets that from its shape
(art rule 2: the sprite's shading is lighting, never paint): the fuselage is the one tall part, its
deck a shallow crown (a flat middle, a shoulder each side tilted 24 degrees, then a steep flank)
under a raised, polished spine, so the game's sun (17 degrees left of up) lights the left shoulder
most, the deck next, and leaves the right flank dark, as the sprite; the shells, the engines and
the pipes stand 1-1.5 px lower and take the sprite's darker indices.

The sprite is authoritative for the plan outline, the windshield and the colours: the top view
follows frame 81's inner mask (D74: the game's ink outline stands in for the sprite's dark border)
with smooth curves through the middles of its steps (D118), and each part takes the palette index
of the sprite pixels it covers, read on the sprite's lit (left) side, one index per part. The
sprite's ink between the three pipes is inside the inner mask: it is a dark heat shield under
them (D213, D229).

How it is built (as the Talon):
- Every part is a low-poly cage in sprite px (x across from the ship's centre line, the middle of
  sprite column 11; y = sprite row, aft is +y; z up), moved to Blender at the end
  (X = (x - 0.5) / 12, Y = (14 - y) / 12, Z = z / 12).
- Sections between stations are monotone cubic (pchip), so lofts never swell.
- Dark gunmetal cores under separate armour plates that stand 0.2-0.36 px proud with 45-degree
  chamfers, so panel lines are real gaps. Flat faces stay flat (sharp by angle, weighted normals).
- Texture: no concept projection (texture_bake.py skips this model: "bake": "model" in its
  maps.json). This script bakes ambient occlusion with an edge lift (a colour multiplier, TINT)
  and a roughness/metalness map. Base Color = map x palette colour.
- Palette materials (pal_<index>) so palettes, fades and the hit flash apply; the engines' grooves
  and throats glow in the palette's reds at strength 1 (D126).
- Exported beside it: an outline shell (common.outline_shell, D51, D90) and `tyrian_engines` (two red
  glows over the engines' throats for the menu backdrop).

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

# Finishes: (metallic, roughness, glow). Satin hull metal as the Talon's (D53); the spine, the collar
# and the engines' lips are polished, so they carry the sheen the sprite draws on them. The reds
# glow at 1 (the rims at 0.7): the palette colour as the sprite shows it, whatever the light; past
# that a red runs pink (D126).
FINISHES = {
    "satin": (0.12, 0.38, 0.0),
    "bright": (0.15, 0.3, 0.0),
    "polish": (0.3, 0.16, 0.0),
    "dull": (0.11, 0.46, 0.0),
    "matte": (0.06, 0.8, 0.0),
    "glass": (0.0, 0.05, 0.0),
    "warm": (0.0, 0.7, 0.35),
    "ember": (0.0, 0.9, 0.7),
    "glow": (0.0, 0.9, 1.0),
}
# Parts: the palette index each takes (the median of the sprite pixels it covers on the sprite's
# lit, left side; the right side's darker indices are the same parts in shade, which is the game's
# light to give, art rule 2; the ink, 1-2, left out) and its finish. Parts of one index and finish
# share a material.
PARTS = {
    "NOSE": (7, "satin"),      # nose roof, rows 1-4 (left 4, 6, 5, 9, 8, 10)
    "SPINE": (11, "polish"),   # the nose's ridge (column 11: 6, 10, 11, 13) and the deck's spine (column 11, rows 10-20: median 11)
    "COLLAR": (12, "polish"),  # row 9's band behind the windshield (12, 12, 15, 12)
    "LIP": (12, "polish"),     # the engines' swept lips (left 12, 13, 14)
    "FRAME": (9, "satin"),     # shoulders beside the windshield and its sill (left 9)
    "DECK": (11, "bright"),    # the deck and its shoulders (columns 9-13, rows 10-21: median 11)
    "FLANK": (9, "satin"),     # the fuselage's flanks (column 8: 9; column 14 is the same in shade)
    "TAIL": (9, "satin"),      # the tail cap, rows 21-22, and the pipes' collars
    "CANARD": (6, "satin"),    # rows 7-8 outboard of the dark root (left 6, 5 and 10, 6, 5)
    "SHELL": (7, "satin"),     # the side shells (left 7)
    "RAIL": (9, "satin"),      # their outer rails (column 3, rows 15-19: 7, 9, 10, 9, 6)
    "FAIR": (9, "satin"),      # the root fairings, rows 10-13 (13, 9, 7, 6)
    "NAC": (9, "satin"),       # the engines' cowls in front of the grooves (left 9)
    "BAR": (11, "bright"),     # the band between the grooves, row 19 (12, 11, 10)
    "BAR_LO": (6, "satin"),    # the band behind them, row 21, and the pipes' manifold (6)
    "PIPE": (9, "satin"),      # the outer exhaust pipes (column 9: 9, 9, 8, 8)
    "PIPE_MID": (7, "satin"),  # the middle one (column 11: 6, 6, 7)
    "BELLY": (6, "satin"),
    "GUN": (4, "dull"),        # cores, seams, the shells' trailing corners (4, 2)
    "DEEP": (2, "matte"),      # bores, intakes
    "TRAY": (1, "matte"),      # the sprite's ink between the pipes
    "GLASS": (1, "glass"),
    "SHROUD": (113, "warm"),   # the nozzles' shrouds: red metal, lit, a little of its own glow
    "RED_DK": (113, "ember"),  # their rims
    "RED_SH": (114, "glow"),   # their walls, the grooves' floors
    "RED": (115, "glow"),      # the throats' floors
    "TUBE": (117, "glow"),     # the grooves' tubes, the throats' inner walls
    "CORE": (118, "glow"),     # the throats' cores
}
MATS = sorted(set(PARTS.values()))
(NOSE, SPINE, COLLAR, LIP, FRAME, DECK, FLANK, TAIL, CANARD, SHELL, RAIL, FAIR, NAC, BAR, BAR_LO, PIPE, PIPE_MID,
 BELLY, GUN, DEEP, TRAY, GLASS, SHROUD, RED_DK, RED_SH, RED, TUBE, CORE) = (MATS.index(v) for v in PARTS.values())

# The baked colour map's tint (linear multipliers): neutral grey with the blue trimmed, since the
# game's blue sky light leans the ship cool (measured on game-lit top views, D118).
TINT = (1.0, 0.96, 0.82)


def materials(sprite):
    return [common.palette_material(sprite, idx, f"silver_{fin}", metallic=FINISHES[fin][0], roughness=FINISHES[fin][1],
                                    emission_strength=FINISHES[fin][2]) for idx, fin in MATS]


# --- the plan (sprite px, x from the centre line, y = row) --------------------------------------
#
# Frame 81's INNER mask (D74, docs/agents/OUTLINE-BORDER.md), half width by row:
#   rows 1-2 1.5 | 3-4 2.5 | 5 3.5 | 6 4.5 | 7 5.5 | 8 6.5 (canard tips) | 9 5.5 | 10-11 4.5 |
#   12 5.5 | 13 6.5 | 14 7.5 | 15-20 8.5 (the shells) | 21 7.5 | 22 6.5 | 23 6.5 / 5.5 | 24 4.5 | 25 3.5
# Each outboard edge is one smooth line through the middles of those steps (D118): the nose a blunt
# ogive from row 0.95, the canard's leading edge half width y - 2.1 to a tip at row 8, its trailing
# edge one sweep in to the waist, the shell's front one sweep (half width y - 7) rounding into its
# straight side at 8.5, the rear edge the diagonal x + y = 29, the heat shield's end at row 26.

PL = 0.25           # the fuselage's armour plates stand this far out of its core
Y_NOSE = 0.95
Y_DECK = 9.05       # the deck's front edge, behind the windshield (the sprite's bright row 9)
Y_SEAM = 15.5       # the deck's panel break
Y_DECK_END = 21.3
Y_FUSE_END = 22.05  # the fuselage's rear face; the pipes and their heat shield run on to row 26
Y_END = 26.03

_FY = [0.95, 1.15, 1.45, 1.9, 2.4, 2.9, 3.4, 3.9, 4.4, 5.0, 5.8, 7.0, 8.6, Y_DECK, 12.0, 16.0, 20.5, Y_DECK_END, 21.7,
       Y_FUSE_END]
# Plated half width (the outline in front of the canards and at the waist), deck top and keel.
WO = pchip(_FY, [0.58, 0.9, 1.2, 1.44, 1.64, 1.88, 2.1, 2.26, 2.42, 2.73, 3.2, 3.4, 3.45, 3.45, 3.45, 3.45, 3.45,
                 3.45, 3.4, 3.3])
TO = pchip(_FY, [0.55, 0.72, 0.92, 1.14, 1.34, 1.5, 1.64, 1.76, 1.86, 1.98, 2.1, 2.22, 2.36, 2.42, 2.55, 2.58, 2.5,
                 2.42, 2.05, 1.55])
BO = pchip(_FY, [-0.1, -0.26, -0.45, -0.68, -0.9, -1.08, -1.2, -1.3, -1.38, -1.45, -1.5, -1.55, -1.6, -1.6, -1.6,
                 -1.6, -1.55, -1.5, -1.42, -1.3])
# The crown: flat out to half width DE (the nose's ridge, the windshield's sill, the deck), a
# shoulder that drops CH out to half width SH, then the flank down to the full width at height ZF.
DE = pchip(_FY, [0.16, 0.2, 0.25, 0.3, 0.36, 0.42, 0.47, 0.52, 0.6, 0.85, 1.2, 1.4, 1.45, 1.45, 1.45, 1.45, 1.45,
                 1.45, 1.42, 1.35])
SH = pchip(_FY, [0.4, 0.62, 0.84, 1.02, 1.18, 1.36, 1.54, 1.68, 1.82, 2.08, 2.4, 2.52, 2.55, 2.55, 2.55, 2.55, 2.55,
                 2.55, 2.5, 2.4])
CH = pchip(_FY, [0.12, 0.16, 0.2, 0.26, 0.3, 0.34, 0.38, 0.4, 0.42, 0.45, 0.48, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                 0.48, 0.45])
ZF = pchip(_FY, [0.2, 0.26, 0.34, 0.44, 0.54, 0.62, 0.7, 0.76, 0.82, 0.9, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.95,
                 0.9, 0.8])
N_LOOP = 12


def fuselage_loop(y):
    """The fuselage core's closed section: s = 0 top centre, 1 the flat's edge, 2 the shoulder's foot,
    3 the flank's foot (the full width), 4 the wall's foot, 5 the chine, 6 the keel, then back up the
    left side (7-11)."""
    w, t, b = WO(y) - PL, TO(y) - PL, BO(y) + 0.12
    h = t - b
    sh = min(SH(y) - 0.5 * PL, 0.9 * w)
    de = min(DE(y), 0.75 * sh)
    c = CH(y)
    zf = min(ZF(y) - 0.1, t - c - 0.1 * h)
    zb = min(b + 0.4 * h, zf - 0.1 * h)
    right = [(0.0, t), (de, t), (sh, t - c), (w, zf), (0.94 * w, zb), (0.5 * w, b + 0.07 * h), (0.0, b)]
    pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return pts, (0.0, (t + b) / 2)


def deck_top(y):
    return TO(y)


def hull_top(x, y):
    """The plated fuselage's top at (x, y)."""
    ax = abs(x)
    de, sh, t, c = DE(y), SH(y), TO(y), CH(y)
    if ax <= de:
        return t
    if ax <= sh:
        return t - c * (ax - de) / (sh - de)
    return t - c - (t - c - ZF(y)) * min(1.0, (ax - sh) / max(1e-6, WO(y) - sh))


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
    ztop(x, y), its top edge chamfered `ch`: a block or a raised panel."""
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


def pipe_y(part, xc, zc, stations, mat, bore_mat, n=12, bore=0.66, depth=0.7):
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
    ys = ([Y_NOSE, 1.1, 1.35, 1.7] + frange(2.1, 8.6, 0.8) + frange(Y_DECK, Y_DECK_END, 0.8)[:-1]
          + [Y_DECK_END, 21.7, Y_FUSE_END])
    loft(P, L, ys, GUN)
    # Nose cone (rows 1.3-4.75), all round, its back edge chamfered; a tip over its front edge.
    plate(P, L, 1.3, 4.75, NOSE, d=PL, ch0=False, ystep=0.35)
    sec = Section(L, 1.3)
    tip = [sec.at(k, PL) for k in range(sec.n)]
    hull(P, tip + [(0.0, Y_NOSE + 0.03, (TO(Y_NOSE) + BO(Y_NOSE)) / 2)], NOSE)
    for side in (1, -1):
        # Beside the windshield: the shoulders (the sprite's lighter grey beside the glass) and the
        # flanks down to the canards, a panel break at row 7.
        for y0, y1 in ((4.9, 6.95), (7.1, 8.92)):
            plate(P, L, y0, y1, FRAME, **LS(side, 1.06, 1.94), d=PL, c=0.12)
            plate(P, L, y0, y1, NOSE, **LS(side, 2.06, 3.94), d=PL, c=0.12)
        # Behind it: the deck and its shoulder in one plate (the knee between them is a crease, not a
        # seam) and the flank, a panel break at row 15.5.
        for y0, y1 in ((10.05, Y_SEAM - 0.08), (Y_SEAM + 0.08, Y_DECK_END - 0.04)):
            plate(P, L, y0, y1, DECK, **LS(side, 0.38, 1.94), d=PL, c=0.1, ystep=0.9)
            plate(P, L, y0, y1, FLANK, **LS(side, 2.06, 3.94), d=PL, c=0.12, ystep=0.9)
        plate(P, L, Y_DECK_END + 0.06, Y_FUSE_END - 0.02, GUN, **LS(side, 2.06, 3.94), d=PL - 0.05, c=0.1, ch1=False)
    # The sill under the windshield.
    plate(P, L, 4.9, 8.92, FRAME, s0=-0.94, s1=0.94, d=PL - 0.05, c=0.1)
    # The collar: one polished band over the deck and both shoulders behind the windshield (the
    # sprite's near-white row 9).
    plate(P, L, Y_DECK + 0.02, 9.92, COLLAR, s0=-1.94, s1=1.94, d=PL + 0.1, c=0.09, ystep=0.5)
    # The tail cap: the deck's end falling to the pipes.
    plate(P, L, Y_DECK_END + 0.06, Y_FUSE_END - 0.02, TAIL, s0=-1.94, s1=1.94, d=PL, c=0.1, ystep=0.25, ch1=False)
    # Belly panels and a keel strake.
    for y0, y1 in ((4.9, 9.6), (9.75, 15.5), (15.65, Y_FUSE_END - 0.1)):
        plate(P, L, y0, y1, BELLY, s0=4.06, s1=7.94, d=0.15, c=0.1, ystep=0.9)
    pts = []
    for y, drop in ((10.5, 0.1), (12.0, 0.4), (19.5, 0.4), (21.5, 0.1)):
        b = BO(y)
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.3, b + 0.3), (0.2, b - drop), (0.08, b - drop - 0.06))]
    hull(P, pts, GUN)


def build_spine(P):
    # The nose's ridge: a polished strip from row 1.8 to the windshield's sill (the sprite's light
    # centre pixels at rows 2-4 are sheen on it).
    pts = []
    for y in frange(1.8, 4.72, 0.4):
        hw = min(0.42, 0.2 + 0.3 * (y - 1.8))
        top = TO(y) + 0.13
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((hw - 0.1, top), (hw, top - 0.1), (hw, TO(y) - 0.25))]
    hull(P, pts, SPINE)
    # The deck's spine (the sprite's column 11, rows 10-21): a raised strip in two steps, both
    # polished, a break at the deck's seam; it follows the deck's own gentle arc.
    for y0, y1 in ((10.05, Y_SEAM - 0.08), (Y_SEAM + 0.08, Y_DECK_END - 0.04)):
        for hw, rise, base, ch in ((0.52, 0.2, -0.3, 0.1), (0.33, 0.36, 0.1, 0.09)):
            pts = []
            ys = frange(y0, y1, 1.4)
            for k, y in enumerate(ys):
                end = k in (0, len(ys) - 1)
                top = TO(y) + rise
                pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((hw, top - ch), (hw, TO(y) + base))]
                yy = y + (ch if k == 0 else -ch if k == len(ys) - 1 else 0.0)
                pts += [(sx * (hw - ch), yy, top) for sx in (-1, 1)]
                if end:
                    pts += [(sx * hw, y, top - ch) for sx in (-1, 1)]
            hull(P, pts, SPINE)
    # A raised access hatch each side of the fore deck and two louvres in front of it.
    for sx in (-1, 1):
        t = TO(13.6)
        hull(P, [(sx * x, y, z) for x, y, z in cbox(0.72, 1.26, 12.7, 14.6, t - 0.05, t + 0.1, 0.06)], DECK)
        for y0 in (10.75, 11.4):
            t = TO(y0)
            hull(P, [(sx * x, y, z) for x, y, z in cbox(0.76, 1.22, y0, y0 + 0.3, t - 0.05, t + 0.06, 0.04)], GUN)
        # Two fasteners' bosses on the aft shoulder.
        for y0 in (17.0, 19.6):
            hull(P, [(sx * x, y, z) for x, y, z in cbox(1.78, 2.14, y0, y0 + 0.36, hull_top(1.96, y0) - 0.1,
                                                         hull_top(1.96, y0) + 0.07, 0.05)], DECK)


# Windshield: the sprite's dark cockpit pixels (column 11 at row 5, columns 10-12 at rows 6-8:
# |x| <= 1.5, y 5-9), pointed forward, square behind.
CAN_Y0, CAN_Y1, CAN_YC, CAN_W = 5.0, 8.9, 7.5, 1.5
CAN_N = 40
GLASS_BASE = 0.12
GLASS_H = 0.62


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
    # Frame: a sill from the glass edge out over the deck, flat top, chamfered outer edge.
    inner = canopy_outline(-0.05)
    top_out = canopy_outline(0.16)
    ch_out = canopy_outline(0.27)
    fr = []
    for k in range(CAN_N):
        xi, yi = inner[k]
        xo, yo = top_out[k]
        xc, yc = ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.12
        fr.append([F.v((xi, yi, deck_top(yi) + GLASS_BASE - 0.3)), F.v((xi, yi, zt)), F.v((xo, yo, zt)),
                   F.v((xc, yc, zt - 0.11)), F.v((xc, yc, hull_top(xc, yc) - 0.3))])
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
# 9's step to the waist at row 10 (D118's).
CANARD_PLAN = [(2.2, 4.3), (6.4, 8.5), (6.5, 9.05), (4.45, 10.05), (2.6, 10.05)]
CANARD_FILLET = ((0.0, 0.3, 0.22, 0.3, 0.0), (1, 3, 2, 2, 1))
CANARD_Z = 0.12


def canard_points(outline, ztop, zbot):
    pts = []
    for x, y in outline:
        tz = (0.58 - 0.3 * (x - 2.6) / 3.9)  # thickness falls toward the tip
        zc = CANARD_Z + 0.08 * (x - 2.6) / 3.9  # a little dihedral
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
        # Two top armour panels, proud, a seam along the sweep between them; a belly panel.
        front = [(3.3, 5.8), (6.0, 8.45), (6.1, 8.85), (3.3, 7.72)]
        back = [(3.3, 7.98), (6.1, 9.08), (4.45, 9.82), (3.3, 9.82)]
        for poly in (front, back):
            pp = []
            for x, y, zt, zb in canard_points(poly, 0.5, -0.5):
                pp += [(m(x), y, zt - 0.1), (m(x), y, zt + 0.08)]
            for x, y, zt, zb in canard_points(inset_polygon(poly, 0.1), 0.5, -0.5):
                pp += [(m(x), y, zt + 0.17)]
            hull(P, pp, CANARD)
        under = [(2.5, 5.1), (6.0, 8.6), (6.0, 9.15), (4.45, 9.85), (2.5, 9.85)]
        pp = []
        for x, y, zt, zb in canard_points(under, 0.5, -0.5):
            pp += [(m(x), y, zb + 0.1), (m(x), y, zb - 0.06)]
        for x, y, zt, zb in canard_points(inset_polygon(under, 0.1), 0.5, -0.5):
            pp += [(m(x), y, zb - 0.12)]
        hull(P, pp, BELLY)
        # Tip cap: a darker block on the tip, chamfered.
        pp = []
        for x, y, zt, zb in canard_points([(6.1, 8.3), (6.45, 8.6), (6.47, 9.03), (6.1, 9.22)], 0.5, -0.5):
            pp += [(m(x), y, zt + 0.1), (m(x), y, zb - 0.05)]
        hull(P, pp, GUN)


# --- the side shells ---------------------------------------------------------------------------

# One low armour shell each side of the rear fuselage (the sprite's rows 10-21): its outboard edge is
# the inner mask's (D118's line: a short fairing along the flank at rows 10-11.5, one sweep out to
# the full width at row 15.5, straight to row 20.5, then the rear diagonal), its inboard edge is
# tucked into the fuselage's flank. It is 2.5 px thick where D118's round pod was 4.9, and its top
# stands 1.4 px under the deck: a flat crown that falls a little outboard, a sloped shoulder, a
# blunt edge, a flat belly.
SHELL_PLATE = 0.22
RAIL_PLATE = 0.36
_PY = [10.0, 10.4, 11.0, 12.0, 12.5, 13.5, 14.5, 15.0, 15.5, 16.0, 17.0, 18.5, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0]
_PO = [3.95, 4.25, 4.5, 4.88, 5.42, 6.45, 7.45, 7.92, 8.25, 8.42, 8.5, 8.5, 8.48, 8.42, 8.27, 7.95, 7.5, 6.95]
_PI = [3.3, 3.08, 2.95, 2.88, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.85, 2.88, 2.92, 3.0]
_PXO = [o - RAIL_PLATE + 0.04 for o in _PO]
POD_CX = pchip(_PY, [(a + b) / 2 for a, b in zip(_PI, _PXO)])
POD_RX = pchip(_PY, [(b - a) / 2 for a, b in zip(_PI, _PXO)])
POD_CZ = pchip(_PY, [0.1, 0.05, 0.0, -0.06] + [-0.1] * 14)
POD_RZ = pchip(_PY, [0.4, 0.55, 0.68, 0.82, 0.88, 0.96, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.98, 0.95, 0.9])
POD_START, POD_END = _PY[0], _PY[-1]


def _pod_unit():
    """The shell's section, normalised to half sizes 1 x 1 (u outboard, v up). Starts on the inboard
    wall's top and runs outboard over the crown."""
    a, b = 2.7, 1.0
    corners = [(-0.75 * a, b), (0.3 * a, 0.86 * b), (0.86 * a, 0.3 * b), (a, -0.15 * b), (0.8 * a, -0.8 * b),
               (0.35 * a, -b), (-0.75 * a, -b), (-a, -0.6 * b), (-a, 0.7 * b)]
    pts = fillet(corners, (0.25, 0.45, 0.4, 0.16, 0.3, 0.3, 0.25, 0.25, 0.25), (2, 3, 3, 2, 2, 2, 2, 2, 2))
    return [(u / a, v / b) for u, v in pts]


POD_UNIT = _pod_unit()
POD_N = len(POD_UNIT)


def pod_s(deg):
    """Loop parameter where the ray at `deg` degrees from straight up (toward outboard; negative:
    inboard) meets the shell's section (in its normalised frame)."""
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


def pod_loop(y, side=1):
    cx, cz = side * POD_CX(y), POD_CZ(y)
    rx, rz = POD_RX(y), POD_RZ(y)
    return [(cx + side * rx * u, cz + rz * v) for u, v in POD_UNIT], (cx, cz)


def pod_top(x, y):
    """The shell core's top at (x, y), right side."""
    pts, _ = pod_loop(y)
    best = None
    for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]):
        if abs(x1 - x0) > 1e-9 and min(x0, x1) - 1e-9 <= x <= max(x0, x1) + 1e-9:
            z = z0 + (z1 - z0) * (x - x0) / (x1 - x0)
            best = z if best is None else max(best, z)
    return best if best is not None else POD_CZ(y)


# The engine on each shell (the sprite's columns 5-7 / 15-17): a low arched cowl from a swept,
# polished lip back to the nozzle, with two glowing grooves between raised bands.
NAC_X0, NAC_X1 = 3.3, 6.52
_AX = [NAC_X0, 3.5, 3.8, 4.3, 5.0, 5.7, 6.2, 6.4, NAC_X1]
ARCH = pchip(_AX, [0.92, 1.18, 1.4, 1.55, 1.6, 1.53, 1.36, 1.2, 0.95])
GROOVE = 0.3            # the grooves' depth under the cowl
SLAT_Y0, SLAT_Y1 = 18.0, 22.0   # the grooves and bands, rows 18-21
LIP_END = 17.42         # the lip's line stops sweeping here, so the lip ends in front of the first groove
LIP_KINK = 3.5 + (LIP_END - 13.75) / 1.5


def lip_y(x):
    """The engine lip's line: through the sprite's bright pixels (7, 14), (6, 16), (5, 17), then
    straight across to the engine's outboard side."""
    return min(13.75 + 1.5 * (x - 3.5), LIP_END)


def lip_spans(x0=NAC_X0, x1=NAC_X1):
    """The x stations across the engine in two runs, split where the lip's line turns (a block with a
    swept edge is a convex hull, and the turn is not convex)."""
    xs = sorted({x0, x1, LIP_KINK} | {a for a in _AX if x0 < a < x1})
    return [[x for x in xs if x <= LIP_KINK + 1e-9], [x for x in xs if x >= LIP_KINK - 1e-9]]


def arch_block(part, side, y0, y1, mat, off=0.0, zbot=0.3, ch=0.07, x0=NAC_X0, x1=NAC_X1):
    """A piece of the engine's arch between rows y0 and y1 (either may be a function of x: a swept edge),
    its top `off` above the cowl's, its front and rear edges chamfered."""
    f0 = y0 if callable(y0) else (lambda x: y0)
    f1 = y1 if callable(y1) else (lambda x: y1)
    swept = callable(y0) or callable(y1)
    for xs in (lip_spans(x0, x1) if swept else [sorted({x0, x1} | {a for a in _AX if x0 < a < x1})]):
        pts = []
        for x in xs:
            z = ARCH(x) + off
            ya, yb = f0(x), max(f1(x), f0(x) + 0.02)
            pts += [(side * x, ya, z - ch), (side * x, ya + ch, z), (side * x, yb - ch, z), (side * x, yb, z - ch),
                    (side * x, ya, zbot), (side * x, yb, zbot)]
        if len(xs) > 1:
            hull(part, pts, mat)


def build_shells(P, D):
    for side in (1, -1):
        def L(y, side=side):
            return pod_loop(y, side)

        def A(a, b, gap=0.0):
            return dict(s0=pod_s(a) + gap, s1=pod_s(b) - gap)
        loft(P, L, frange(POD_START, 12.5, 0.5) + frange(12.5, POD_END, 0.7)[1:], GUN)
        # The root fairing (rows 10.25-12): one cowl over the shell's nose, an intake mouth in it.
        plate(P, L, 10.25, 12.0, FAIR, **A(-37, 133, 0.1), d=SHELL_PLATE, c=0.1, ystep=0.4)
        cxf = side * POD_CX(10.3)
        hull(D, [(cxf + side * x, y, z) for x, y, z in cbox(-0.24, 0.3, 9.9, 10.12, POD_CZ(10.3) - 0.3, POD_CZ(10.3) + 0.34, 0.05)], DEEP)
        # The shoulder: one armour plate along the whole shell (a break at row 16.2), a raised hatch
        # on it; the trailing corner behind row 20.5 is dark (the sprite's 4 and 2 there).
        plate(P, L, 12.15, 16.1, SHELL, **A(22, 68), d=SHELL_PLATE, c=0.1, ystep=0.6)
        plate(P, L, 16.25, 20.42, SHELL, **A(22, 68), d=SHELL_PLATE, c=0.1, ystep=0.7)
        plate(P, L, 17.0, 19.4, SHELL, **A(33, 57), d=SHELL_PLATE + 0.1, c=0.07, ystep=0.8)
        plate(P, L, 20.56, POD_END + 0.02, GUN, **A(22, 132), d=SHELL_PLATE, c=0.1, ystep=0.4)
        # The edge: armour in front of row 14.6, then the rail, a prouder rounded strake along the
        # shell's outer pixel to row 20.4 (the sprite's column 3 is lighter than column 4).
        plate(P, L, 12.15, 14.5, SHELL, **A(72, 132), d=SHELL_PLATE, c=0.1, ystep=0.6)
        plate(P, L, 14.62, 20.42, RAIL, **A(72, 132), d=RAIL_PLATE, c=0.14, ystep=0.6)
        # The belly.
        plate(P, L, 12.15, 21.55, BELLY, **A(138, 214), d=SHELL_PLATE, c=0.1, ystep=0.9)
        # The crown in front of the engine: one panel between the shell's swept front and the
        # engine's intake.
        lead = [(3.6, 12.2), (4.3, 12.45), (6.28, 15.5), (6.28, LIP_END - 0.56), (LIP_KINK, LIP_END - 0.56),
                (3.6, lip_y(3.6) - 0.56)]
        slab(P, side, lead, lambda x, y: pod_top(x, max(y, 13.6)) + 0.16, lambda x, y: pod_top(x, max(y, 13.6)) - 0.15, SHELL, ch=0.08)
        # Outboard of the engine: a narrow strip of crown armour beside the grooves.
        strip = [(6.62, LIP_END + 0.3), (6.62, 20.42), (6.3, 20.42), (6.3, LIP_END + 0.3)]
        slab(P, side, strip, lambda x, y: pod_top(x, 18.0) + 0.16, lambda x, y: pod_top(x, 18.0) - 0.15, SHELL, ch=0.06)


def build_engines(P, D):
    for side in (1, -1):
        # Core: the arch from behind the lip to the nozzle, its top at the grooves' floor.
        arch_block(P, side, lambda x: lip_y(x) + 0.4, SLAT_Y1, GUN, off=-GROOVE - 0.04, ch=0.03)
        # The cowl in front of the grooves (the sprite's 9s between the lip and the first groove).
        arch_block(P, side, lambda x: lip_y(x) + 0.42, SLAT_Y0 - 0.04, NAC, zbot=0.6, ch=0.06)
        arch_block(P, side, lambda x: lip_y(x) + 0.4, SLAT_Y0 - 0.04, GUN, off=-0.1, zbot=0.6, ch=0.03)
        # The intake: the cowl's swept front is open (a dark mouth set back under the lip), and the
        # strip of the shell's crown in front of it is its bare floor (the sprite's darker pixels
        # just ahead of the bright diagonal).
        arch_block(P, side, lambda x: lip_y(x) - 0.06, lambda x: lip_y(x) + 0.4, DEEP, off=-0.16, ch=0.0)
        for xs in lip_spans(NAC_X0 + 0.25, NAC_X1 - 0.3):
            pts = []
            for x in (xs[0], xs[-1]):
                z = pod_top(x, 17.0)
                pts += [(side * x, lip_y(x) + dy, z + dz) for dy in (-0.62, 0.3) for dz in (0.03, -0.25)]
            hull(P, pts, GUN)
        # The lip: a polished ring over the mouth, following the arch; its front is a bevel facing up
        # and forward (the sprite's bright diagonal, 1 px deep).
        # (One hull per pair of stations: a hull of the whole ring would fill the mouth under the arch.)
        for xs in lip_spans(NAC_X0 + 0.04, NAC_X1 - 0.03):
            for xa, xb in zip(xs, xs[1:]):
                pts = []
                for x in (xa, xb):
                    yl, z = lip_y(x), ARCH(x)
                    pts += [(side * x, yl - 0.2, z - 0.15), (side * x, yl + 0.2, z + 0.06), (side * x, yl + 0.4, z + 0.06),
                            (side * x, yl + 0.5, z - 0.03), (side * x, yl - 0.2, z - 0.34), (side * x, yl + 0.5, z - 0.34)]
                hull(P, pts, LIP)
        # Two bands over the arch (rows 19 and 21: raised rings) and two red grooves (rows 18 and 20),
        # each with a glowing tube across it held by two clamps.
        for y0, y1, mat in ((19.04, 19.96, BAR), (21.04, 21.96, BAR_LO)):
            arch_block(P, side, y0, y1, mat, off=0.05, zbot=0.6, ch=0.09)
        for y0, y1 in ((18.0, 19.04), (19.96, 21.04)):
            arch_block(D, side, y0, y1, RED_SH, off=-GROOVE, zbot=0.6, ch=0.0)
            yc = (y0 + y1) / 2
            zc = ARCH(5.0) - GROOVE + 0.1
            tube_x(D, side * 3.95, side * 6.0, yc, zc, 0.18, TUBE)
            for x in (3.82, 6.12):
                hull(D, [(side * xx, yy, zz) for xx, yy, zz in cbox(x - 0.1, x + 0.1, yc - 0.3, yc + 0.3,
                                                                       ARCH(x) - GROOVE - 0.05, ARCH(x) - 0.06, 0.04)], GUN)


# The red nozzles: each engine ends in a trough cut on the shell's rear diagonal, its opening
# tilted 29 degrees to face up, aft and outboard, so the game's camera (overhead, from behind) looks
# into the glowing throat: a dark red rim, red walls, a brighter floor, a bright core in a pit, as
# the sprite's rows 22-25. The shroud round it is red metal, lit, so it shades as a solid.
NOZ_RIM = [(3.42, 22.02), (6.5, 22.02), (6.5, 22.47), (3.56, 25.41), (3.42, 25.41)]
NOZ_C = (4.72, 23.25)
NOZ_K = 0.55          # the rim's fall per px toward the diagonal
NOZ_BOT = -1.25
_NN = math.hypot(NOZ_K, 1.0)
NOZ_IN = (-NOZ_K / _NN / math.sqrt(2), -NOZ_K / _NN / math.sqrt(2), -1.0 / _NN)  # into the throat


def noz_z(x, y):
    return 0.95 - NOZ_K * (x + y - 25.44) / math.sqrt(2)


def noz_ring(k, depth=0.0):
    """The rim's polygon scaled k about its centre and sunk `depth` into the throat: [(x, y, z)], right side."""
    out = []
    for x, y in NOZ_RIM:
        px, py = NOZ_C[0] + (x - NOZ_C[0]) * k, NOZ_C[1] + (y - NOZ_C[1]) * k
        out.append((px + NOZ_IN[0] * depth, py + NOZ_IN[1] * depth, noz_z(px, py) + NOZ_IN[2] * depth))
    return out


def build_nozzles(P, D):
    n = len(NOZ_RIM)
    for side in (1, -1):
        def ring(part, pts):
            return [part.v((side * x, y, z)) for x, y, z in pts]
        c = (side * NOZ_C[0], NOZ_C[1], -0.3)
        up = (side * -NOZ_IN[0], -NOZ_IN[1], -NOZ_IN[2])
        # The shroud: red metal, lit (its rim's top glows a little, an ember), a chamfered foot.
        rim = ring(P, [(x, y, z - 0.07) for x, y, z in noz_ring(1.0)])
        rim_in = ring(P, noz_ring(0.95))
        lip = ring(P, noz_ring(0.87))
        low = ring(P, [(x, y, NOZ_BOT + 0.15) for x, y, _ in noz_ring(1.0)])
        bot = ring(P, [(x, y, NOZ_BOT) for x, y, _ in noz_ring(0.9)])
        # The throat: walls, a floor ring, a pit with the bright core at its bottom.
        lip_d = ring(D, noz_ring(0.87))
        floor = ring(D, noz_ring(0.74, 0.55))
        core = ring(D, noz_ring(0.46, 0.62))
        pit = ring(D, noz_ring(0.4, 0.8))
        for i in range(n):
            j = (i + 1) % n
            mx, my = (NOZ_RIM[i][0] + NOZ_RIM[j][0]) / 2, (NOZ_RIM[i][1] + NOZ_RIM[j][1]) / 2
            inward = (side * (NOZ_C[0] - mx), NOZ_C[1] - my, 0.5)
            P.f((rim[i], rim[j], low[j], low[i]), SHROUD, away=c)
            P.f((low[i], low[j], bot[j], bot[i]), SHROUD, away=c)
            P.f((rim[i], rim[j], rim_in[j], rim_in[i]), SHROUD, out=up)
            P.f((rim_in[i], rim_in[j], lip[j], lip[i]), RED_DK, out=up)
            D.f((lip_d[i], lip_d[j], floor[j], floor[i]), RED_SH, out=inward)
            D.f((floor[i], floor[j], core[j], core[i]), RED, out=up)
            D.f((core[i], core[j], pit[j], pit[i]), TUBE, out=inward)
        D.f(pit, CORE, out=up)
        P.f(bot, SHROUD, out=(0, 0, -1))


# The three exhaust pipes (the sprite's columns 9, 11 and 13, rows 22-25) leave the tail through a
# collar each, over a dark heat shield that is the sprite's ink between and beside them.
PIPES = ((-2.0, PIPE, 0.5, 0.14), (0.0, PIPE_MID, 0.47, 0.06), (2.0, PIPE, 0.5, 0.14))
TRAY_Z0, TRAY_Z1 = -0.95, -0.42


def build_tail(P, D):
    hull(P, cbox(-3.44, 3.44, Y_FUSE_END - 0.3, Y_END, TRAY_Z0, TRAY_Z1, 0.08), TRAY)
    # The manifold the pipes leave (row 22: 9, 6, 11, 6, 8).
    hull(P, cbox(-2.7, 2.7, Y_FUSE_END - 0.2, 22.95, TRAY_Z1 - 0.05, 0.44, 0.1), BAR_LO)
    for xc, mat, r, zc in PIPES:
        pipe_y(D, xc, zc, [(Y_FUSE_END - 0.3, r), (25.45, r), (25.45, r + 0.08), (Y_END - 0.06, r + 0.08)], mat, DEEP)
        # The collar where the pipe leaves the tail, and a saddle under it further aft.
        pipe_y(D, xc, zc, [(Y_FUSE_END - 0.1, r + 0.16), (22.8, r + 0.16), (22.8, r + 0.06), (22.95, r + 0.06)], TAIL, GUN,
               bore=0.9, depth=0.02)
        hull(D, cbox(xc - 0.3, xc + 0.3, 24.0, 24.55, TRAY_Z1 - 0.05, zc - r + 0.12, 0.05), GUN)


def outline_fill():
    """Blocks for the outline shell only (never drawn).
    - The engines' grooves and throats are filled: the ink outline is the shell's back faces pushed
      out on screen, so a trench draws an ink line across the red. The gaps between the pipes are
      left open: the sprite inks them.
    - The canards are thinner at their edges than the shell's voxels (0.36 px), which wore the shell
      back from the silhouette there; each gets a prism of its own plan, thick enough to survive
      the remesh, so the ink stands on the model's edge."""
    Q = Part("silver_fill")
    for side in (1, -1):
        arch_block(Q, side, SLAT_Y0 - 0.3, SLAT_Y1 + 0.1, 0, off=0.0, zbot=0.3, ch=0.02)
        pts = []
        for x, y, z in noz_ring(0.96):
            pts += [(side * x, y, z - 0.03), (side * x, y, NOZ_BOT + 0.2)]
        hull(Q, pts, 0)
        pts = []
        for x, y, zt, zb in canard_points(fillet(CANARD_PLAN, *CANARD_FILLET), 0.5, -0.5):
            pts += [(side * x, y, max(zt - 0.12, 0.05)), (side * x, y, zb - 0.45)]
        hull(Q, pts, 0)
    return Q


# The banking frames' pose (D93, fitted to sprites 77-85 with tools/bank_roll.py --fit).
BANK_ROLL = [15.0, 30.0]
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
    P = Part("silver_hull", smooth_angle=22)
    build_fuselage(P)
    S = Part("silver_spine", smooth_angle=30)
    build_spine(S)
    G = Part("silver_canopy", smooth_angle=50)
    F = Part("silver_frame", smooth_angle=30)
    build_canopy(G, F)
    C = Part("silver_canards", smooth_angle=30)
    build_canards(C)
    W = Part("silver_shells", smooth_angle=34)
    det = Part("silver_details", smooth_angle=40)
    build_shells(W, det)
    E = Part("silver_engines", smooth_angle=34)
    build_engines(E, det)
    N = Part("silver_nozzles", smooth_angle=30)
    build_nozzles(N, det)
    T = Part("silver_tail", smooth_angle=30)
    build_tail(T, det)
    return [finish(p, mats, coll) for p in (P, S, G, F, C, W, E, det, N, T)]


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = tuple(i for i, (idx, fin) in enumerate(MATS) if FINISHES[fin][2] == 0.0 and fin != "glass")


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
