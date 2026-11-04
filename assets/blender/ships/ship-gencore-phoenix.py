"""Gencore Phoenix (player ship, tyrian.shp#8 sprite 157 and its banking frames 153-161), built the
way the USP Talon is (assets/blender/usp_talon.py, DECISIONS D50-D53): a hard-surface ship that reads
as a real spaceship from every angle (it turns in the menus and the hangar; the game camera looks
down at a tilt).

The sprite is authoritative for the plan outline, the windshield and the colours (D52):
- Outline: the top view follows frame 157's INNER mask (its ink ring left to the game's outline,
  D74, docs/agents/OUTLINE-BORDER.md) row by row, as smooth curves: an ogive nose widening in steps
  the curve rounds off to the 8 px body at row 9, a narrower waist at rows 17-18, the tail tapering
  over rows 23-24; two crescent blade wings (straight inner edge, convex outer edge, a pointed front
  at row 9 and a tail spike at rows 23-24) clear of the body, joined to it only by the box-section
  booms at rows 20-21. Rule IoU on the grid 0.996 (tools/sprite_mask.py --measure). The banking
  frames are this model rolled by the game, 40 degrees at half bank and 50 at full, and moved 1.5 /
  3.5 px toward the bank (BANK_ROLL, BANK_SHIFT, fitted to sprites 153-161 with tools/bank_roll.py,
  D92): the sprites draw one solid wedge 15-17 px wide (inside the ink), a harder roll than the Talon's 17.5 / 35.
  Nothing in the model is shaped for them; at that pose they measure 0.83-0.84 (half) and 0.85-0.86
  (full).
- Windshield: dark glossy glass in a frame over the sprite's dark cockpit pixels (rows 6-9, columns
  10-13), pointed forward; the bright pixel at row 7 is its glint.
- Colours: each part takes the palette index the sprite uses where it covers it (the median of those
  pixels, the darkest shading 1-3 and the highlights 12-13 left out): nose 7, cockpit surround and
  deck 4, the light plate behind the canopy 9, body sides 5, spine 10, tail 4, wings 7 / 5 / 8
  (outer blade, mid band, inner ridge strip), booms 7 with an 8 top, recesses 2, glass 1. Satin
  metal (metallic ~0.15), and the baked map carries a slight TINT measured against the game's
  lighting (D53).
The concept (assets/blender/features/concepts/ship-gencore-phoenix.jpg) guides the side and front
design and the detail where it agrees with the sprite: layered armour on the blades, the light
chevron plate behind the canopy, the spine, the vent and the rod in its channel down the tail, twin
nozzles; underneath a keel, gear doors, intakes and pipes under the booms.

How it is built (the Talon's toolkit, imported from usp_talon.py): low-poly cages in sprite px
(x = column edge - 12, y = row edge, aft is +y, z up; X = x / 12, Y = (14 - y) / 12, Z = z / 12),
pchip stations so lofts never swell, dark cores under separate armour plates that stand proud with
45-degree chamfers (panel lines are real gaps), hidden faces culled, Cycles-baked occlusion and
roughness maps (no concept projection: maps.json says "bake": "model"), an outline shell
(common.outline_shell, D51) and `tyrian_engines` for the menu's engine glows.

    Blender --background --factory-startup --python ship-gencore-phoenix.py -- [--out path.glb] [--no-bake] [--preview png]
"""

import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (the Talon's hard-surface toolkit, D50)
from usp_talon import Part, Section, cbox, frange, hull, loft, pchip, plate  # noqa: E402

NAME = "ship-gencore-phoenix"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

# Glow colours from palette 5 (the sprite's): orange engine glow, its yellow core.
GLOW_PAL = {121: (231, 97, 12), 123: (243, 174, 36)}

# Material slots and their palette indices (the sprite's per-region medians, DECISIONS D52).
GUN, DK, MID, HATCH, LT, STRIP, PANEL, SPINE, DEEP, GLASS, GLOW, CORE, BELLY, FRAME = range(14)
PAL_OF = {GUN: 3, DK: 4, MID: 5, HATCH: 6, LT: 7, STRIP: 8, PANEL: 9, SPINE: 10, DEEP: 2, GLASS: 1,
          BELLY: 5, FRAME: 4}
TEXTURED = (GUN, DK, MID, HATCH, LT, STRIP, PANEL, SPINE, DEEP, BELLY, FRAME)

# Satin, not mirror (D52/D53): metallic 0.12-0.2.
METAL = 0.3

# The baked colour map's tint (linear multipliers), as the Talon's (D53): the game's sky light is
# blue and its tone mapping (three's Neutral) takes a small offset off every channel, so the lit
# neutral grey would read cool; a slight warm-neutral tint keeps it the sprite's grey in the game.
TINT = (1.0, 0.97, 0.85)


def materials(sprite):
    def pal(slot, tag, metallic, roughness):
        return common.palette_material(sprite, PAL_OF[slot], f"phoenix_{tag}", metallic=metallic * METAL,
                                       roughness=roughness)

    def glow(i, tag, strength):
        c = common.srgb(*GLOW_PAL[i])
        return common.material(f"pal_{i}_phoenix_{tag}", c, metallic=0.0, roughness=0.4, emission=c,
                               emission_strength=strength)
    return [
        pal(GUN, "core", 0.5, 0.5),
        pal(DK, "dark", 0.55, 0.42),
        pal(MID, "mid", 0.55, 0.4),
        pal(HATCH, "hatch", 0.55, 0.38),
        pal(LT, "armour", 0.6, 0.36),
        pal(STRIP, "strip", 0.65, 0.32),
        pal(PANEL, "panel", 0.6, 0.34),
        pal(SPINE, "spine", 0.65, 0.3),
        pal(DEEP, "recess", 0.3, 0.8),
        common.material(f"pal_{PAL_OF[GLASS]}_phoenix_glass", common.srgb(*sprite["colors"][str(PAL_OF[GLASS])]),
                        metallic=0.0, roughness=0.05),
        glow(121, "engine_glow", 1.6),
        glow(123, "engine_core", 2.2),
        pal(BELLY, "belly", 0.4, 0.55),
        pal(FRAME, "frame", 0.6, 0.32),
    ]


# --- plan and stations (sprite px) -------------------------------------------------------------

# Fuselage half width including the outline ring: pchip through the midpoints of the sprite's steps
# (rows 1 / 2-3 / 4-5 / 6-8 / 9-16 / 17-22 / 23 / 24 / 25 are 1 / 2 / 3 / 4 / 5 / 4 / 4 / 3 / 2 px).
PLAN = pchip([1.9, 2.2, 3.0, 4.0, 5.0, 6.0, 7.5, 8.6, 8.85, 9.15, 9.6, 16.4, 16.8, 17.2, 17.5, 18.5, 18.8,
              19.2, 19.5, 22.6, 23.5, 24.5, 25.0],
             [0.1, 0.6, 0.95, 1.5, 2.0, 2.5, 3.0, 3.3, 3.5, 3.85, 4.0, 4.0, 3.75, 3.1, 3.0, 3.0, 3.25,
              3.9, 4.0, 3.9, 3.0, 2.0, 1.7])
NOSE_Y, TAIL_Y = 1.9, 24.9  # the core's end; the nozzles reach row edge 25
FUSE_PLATE = 0.28
FY = [1.0, 2.0, 3.5, 5.0, 6.5, 9.0, 12.0, 16.0, 19.0, 22.0, 24.0, 25.5, 26.0]
FT = pchip(FY, [0.35, 0.95, 1.55, 2.0, 2.3, 2.55, 2.65, 2.65, 2.5, 2.3, 2.1, 1.8, 1.65])
FB = pchip(FY, [0.05, -0.5, -1.05, -1.5, -1.85, -2.15, -2.3, -2.3, -2.25, -2.15, -1.95, -1.6, -1.45])
# The nose's raised centre ridge (a crisp crease down the faceted nose), gone at the windshield.
RIDGE = pchip([1.9, 4.5, 5.6, 6.3], [0.15, 0.4, 0.3, 0.0])
DECK, SHOULDER, FLANK, CHINE = 0.6, 0.3, 0.42, 0.1


def FW(y):
    return max(0.12, PLAN(y) - FUSE_PLATE)


def ridge(y):
    return RIDGE(y) if y < 6.3 else 0.0


def fuselage_loop(y):
    """Closed section: 0 top centre (ridge), 1 deck edge, 2 shoulder, 3 flank foot, 4 chine, 5 keel,
    then back up the left side (6-9)."""
    w, t, b = FW(y), FT(y), FB(y)
    h = t - b
    right = [(0.0, t + ridge(y)), (DECK * w, t), (w, t - SHOULDER * h), (w, b + FLANK * h),
             (DECK * w, b + CHINE * h), (0.0, b)]
    return right + [(-x, z) for x, z in reversed(right[1:-1])], (0.0, (t + b) / 2)


def hull_top(x, y):
    w, t, b = FW(y), FT(y), FB(y)
    ax = abs(x)
    if ax <= DECK * w:
        return t + ridge(y) * (1 - ax / (DECK * w))
    return t - SHOULDER * (t - b) * min(1.0, (ax - DECK * w) / ((1 - DECK) * w))


# Wings (right wing; the left is its mirror): inner edge XI, outer edge XO (both including the
# outline ring), crest height ZT and keel ZB. Straight inner edge a pixel clear of the body, a
# convex outer edge from the pointed front (row 9) out to column 1, swept in at row 23 to the tail
# spike, which ends at row 25.
WING_Y0, WING_Y1 = 9.5, 24.2
XI = pchip([9.5, 18.7, 19.05, 22.8, 23.1, 23.5, 23.8, 24.2], [7.0, 7.0, 6.45, 6.45, 7.0, 7.15, 7.6, 8.3])
XO = pchip([9.5, 10.0, 10.5, 11.5, 12.5, 13.5, 14.5, 16.0, 19.0, 21.9, 22.25, 22.8, 23.3, 23.8, 24.2],
           [7.3, 7.9, 8.1, 8.3, 8.95, 9.25, 9.9, 10.0, 10.05, 10.0, 9.2, 9.0, 8.9, 8.7, 8.4])
ZT = pchip([9.5, 10.3, 12.0, 15.0, 19.0, 22.0, 23.3, 24.2], [0.3, 0.7, 1.1, 1.3, 1.35, 1.2, 0.8, 0.35])
ZB = pchip([9.5, 10.3, 12.0, 15.0, 19.0, 22.0, 23.3, 24.2], [-0.05, -0.3, -0.58, -0.7, -0.75, -0.68, -0.45, -0.08])
ZE = 0.1  # knife edge height


def wing_loop(y, side=1, grow=0.0):
    """Blade section: 0 crest (near the inner edge), 1 upper mid, 2 outer knife edge, 3 lower mid,
    4 keel, 5 inner foot, 6 inner top (a chamfer up to the crest)."""
    xi, xo, zt, zb = XI(y), XO(y), ZT(y), ZB(y)
    w = max(0.05, xo - xi)
    c = min(0.85, 0.3 * w)
    pts = [(xi + c, zt), (xi + c + 0.5 * (w - c), ZE + 0.57 * (zt - ZE)), (xo, ZE),
           (xi + 0.55 * w, ZE + 0.62 * (zb - ZE)), (xi + 0.5 * c, zb), (xi, zb + 0.3 * (zt - zb) * 0.4),
           (xi, zt - 0.6 * c)]
    cx, cz = xi + 0.4 * w, (zt + zb) / 2
    return [(side * x, z) for x, z in pts], (side * cx, cz)


# Windshield: the glass edge in plan, over the sprite's dark cockpit pixels (rows 6-9, columns 10-13),
# pointed forward and squarer behind.
CAN_Y0, CAN_Y1, CAN_YC, CAN_W = 6.15, 9.95, 8.55, 1.95
CAN_N = 40
GLASS_BASE, GLASS_H = 0.2, 0.75


def canopy_outline(grow=0.0):
    pts = []
    for k in range(CAN_N):
        a = 2 * math.pi * k / CAN_N
        c, s = math.cos(a), math.sin(a)
        n, b = (3.0, CAN_YC - CAN_Y0) if s >= 0 else (4.0, CAN_Y1 - CAN_YC)
        e = 2 / n
        x = CAN_W * math.copysign(abs(c) ** e, c)
        yv = math.copysign(abs(s) ** e, s)
        if s > 0:
            x *= 1 - 0.2 * yv ** 2
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


def deck_top(y):
    return FT(y) + 0.22


# --- the ship ---------------------------------------------------------------------------------

def S2(side, a, b, n=10):
    """Loop range (a, b) on the right side, or its mirror on the left of an n-point symmetric loop."""
    return (a, b) if side > 0 else (n - b, n - a)


def build_fuselage(P, D):
    L = fuselage_loop
    ys = [NOSE_Y, 2.05, 2.25] + frange(2.5, 24.5, 0.5) + [TAIL_Y]
    loft(P, L, ys, GUN, cap0=False)
    # Nose cone: one armour shell all round, folding crisply over the ridge, and a polished tip.
    plate(P, L, 2.2, 5.7, LT, d=FUSE_PLATE, c=0.14, ch0=False, ystep=0.4)
    sec = Section(L, 2.2)
    tip = [sec.at(k, FUSE_PLATE) for k in range(sec.n)]
    hull(P, tip + [(0.0, 1.92, (FT(1.9) + FB(1.9)) / 2 + 0.05)], STRIP)
    for side in (1, -1):
        def S(a, b, side=side):
            return S2(side, a, b)
        # Cockpit section: dark side armour under the frame, a split at the shoulder.
        plate(P, L, 5.85, 10.15, DK, *S(0.1, 0.98), d=0.22, c=0.1)
        plate(P, L, 5.85, 10.15, DK, *S(1.04, 2.95), d=FUSE_PLATE, c=0.12)
        # Body (rows 10-17): dark deck either side of the spine, mid-grey shoulders and flanks with a
        # lighter access hatch (the sprite's light pixels at column 15, rows 12-14).
        for y0, y1 in ((10.3, 13.95), (14.1, 17.85)):
            plate(P, L, y0, y1, DK, *S(0.12, 0.98), d=0.25, c=0.12)
        plate(P, L, 10.3, 16.75, MID, *S(1.04, 2.14), d=FUSE_PLATE, c=0.14)
        plate(P, L, 10.3, 12.75, MID, *S(2.2, 2.95), d=FUSE_PLATE, c=0.12)
        plate(P, L, 16.4, 16.75, MID, *S(2.2, 2.95), d=FUSE_PLATE, c=0.1, ystep=1)
        plate(P, L, 11.9, 14.5, HATCH, *S(1.25, 1.85), d=FUSE_PLATE + 0.14, c=0.08, ystep=0.8)
        # Heat louvres low on the flank: a dark grille with three lengthwise slats.
        plate(P, L, 12.85, 16.3, DEEP, *S(2.2, 2.95), d=0.1, c=0.03, ystep=0.8)
        for k in (2.32, 2.52, 2.72):
            plate(P, L, 13.0, 16.2, GUN, *S(k - 0.05, k + 0.05), d=FUSE_PLATE - 0.03, c=0.02, ystep=0.8)
        # The waist and the rear body (rows 17-22): shoulders and deck either side of the vent.
        plate(P, L, 16.9, 22.85, MID, *S(1.04, 2.95), d=FUSE_PLATE, c=0.14)
        plate(P, L, 18.0, 22.85, MID, *S(0.42, 0.98), d=0.25, c=0.12)
        # Tail housing (rows 23-25): darker plates round the rod's channel.
        plate(P, L, 23.0, 24.8, DK, *S(0.42, 0.98), d=0.25, c=0.12, ystep=0.5)
        plate(P, L, 23.0, 24.8, DK, *S(1.04, 2.95), d=FUSE_PLATE, c=0.14, ystep=0.5)
        # Lower chamfer and belly panels.
        for y0, y1 in ((5.85, 11.9), (12.05, 17.85), (18.0, 24.75)):
            plate(P, L, y0, y1, BELLY, *S(3.05, 3.95), d=0.2, c=0.1)
    for y0, y1 in ((9.4, 13.1), (16.9, 21.5), (21.65, 24.7)):
        plate(P, L, y0, y1, BELLY, s0=4.05, s1=5.95, d=0.2, c=0.1)
    # Nose gear door: proud on the belly, with hinge blocks; a keel strake behind it.
    plate(P, L, 5.85, 9.25, MID, s0=4.1, s1=5.9, d=0.32, c=0.1, ystep=0.6)
    for sx in (-1, 1):
        x4, z4 = fuselage_loop(6.4)[0][4]
        hull(D, [(sx * x, y, z) for x, y, z in cbox(x4 * 0.5, x4 * 0.5 + 0.28, 6.1, 6.7, z4 - 0.6, z4 - 0.05, 0.05)], GUN)
    pts = []
    for y in (13.2, 14.4, 19.5, 22.6):
        b = FB(y) - 0.1
        drop = 0.45 if 14.0 < y < 20.0 else 0.08
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.32, b + 0.4), (0.22, b - drop), (0.1, b - drop - 0.08))]
    hull(D, pts, GUN)
    # Main gear doors under the body, either side of the keel.
    for sx in (-1, 1):
        a, b = (4.25, 4.85) if sx > 0 else (5.15, 5.75)
        plate(P, L, 13.25, 16.6, MID, s0=a, s1=b, d=0.36, c=0.08, ystep=0.8)
    # Intakes under the body's shoulders: a gunmetal scoop with a dark mouth facing forward.
    for sx in (-1, 1):
        sec, _ = fuselage_loop(11.5)
        x3, z3 = sec[3]
        x4, z4 = sec[4]
        cx = sx * (x3 + x4) / 2
        hull(D, [(cx + sx * x, y, z) for x, y, z in cbox(-0.8, 0.7, 10.2, 13.0, z4 - 0.9, z4 + 0.4, 0.18)], GUN)
        hull(D, [(cx + sx * x, y, z) for x, y, z in cbox(-0.6, 0.5, 10.1, 10.35, z4 - 0.72, z4 + 0.1, 0.05)], DEEP)


def build_top(P, D):
    """Windshield, its frame, the light chevron plate behind it, the spine, the vent, the rod's
    channel and the tail face with its twin nozzles."""
    C = canopy_outline()
    # Glass: rings scaled toward the peak, height a rounded dome.
    K = 9
    rings = []
    for k in range(K + 1):
        r = 1 - k / K * 0.97
        ring = []
        for x, y in C:
            px, py = x * r, CAN_YC + (y - CAN_YC) * r
            ring.append(P.v((px, py, deck_top(py) + GLASS_BASE + GLASS_H * (1 - r ** 2.6) ** 0.55)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(CAN_N):
            j = (i + 1) % CAN_N
            P.f((r0[i], r0[j], r1[j], r1[i]), GLASS, away=(0, CAN_YC, 0))
    P.f(rings[-1], GLASS, out=(0, 0, 1))
    low = [P.v((x, y, deck_top(y) + GLASS_BASE - 0.3)) for x, y in C]
    for i in range(CAN_N):
        j = (i + 1) % CAN_N
        P.f((low[i], low[j], rings[0][j], rings[0][i]), GLASS, out=(C[i][0], C[i][1] - CAN_YC, 0))
    # Frame: a sill from the glass edge out over the deck, flat top, chamfered outside.
    inner, top_out, ch_out = canopy_outline(-0.06), canopy_outline(0.2), canopy_outline(0.34)
    frame = []
    for k in range(CAN_N):
        (xi, yi), (xo, yo), (xc, yc) = inner[k], top_out[k], ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.16
        frame.append([P.v((xi, yi, deck_top(yi) + GLASS_BASE - 0.3)), P.v((xi, yi, zt)), P.v((xo, yo, zt)),
                      P.v((xc, yc, zt - 0.14)), P.v((xc, yc, hull_top(xc, yc) - 0.4))])
    for k in range(CAN_N):
        j = (k + 1) % CAN_N
        cx, cy = top_out[k]
        outs = [(-cx, -(cy - CAN_YC), 0), (0, 0, 1), (cx * 0.5, (cy - CAN_YC) * 0.5, 1), (cx, cy - CAN_YC, 0)]
        for i in range(4):
            P.f((frame[k][i], frame[j][i], frame[j][i + 1], frame[k][i + 1]), FRAME, out=outs[i])
    # The light chevron plate behind the canopy (the sprite's 3x3 light patch), pointing aft.
    pts = []
    for (x, y) in ((-1.75, 10.35), (1.75, 10.35), (1.75, 12.3), (0.0, 13.6), (-1.75, 12.3)):
        top = deck_top(y) + 0.42
        pts += [(x, y, top - 0.15), (x, y, FT(y) - 0.3)]
    for (x, y) in ((-1.6, 10.5), (1.6, 10.5), (1.6, 12.2), (0.0, 13.4), (-1.6, 12.2)):
        pts.append((x, y, deck_top(y) + 0.42))
    hull(P, pts, PANEL)
    # Spine: a narrow polished ridge from under the chevron's point to the vent.
    pts = []
    for y, h in ((13.0, 0.62), (18.1, 0.45)):
        top = deck_top(y) + h
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.6, top - 0.14), (0.45, top), (0.6, FT(y) - 0.2))]
    hull(P, pts, SPINE)
    # Vent behind the spine: a dark recess between the rear deck plates, two lengthwise slats in it.
    hull(P, cbox(-0.95, 0.95, 18.2, 20.2, FT(19) - 0.6, FT(19) - 0.05, 0.06), DEEP)
    for sx in (-0.42, 0.42):
        hull(P, cbox(sx - 0.07, sx + 0.07, 18.3, 20.1, FT(19) - 0.4, FT(19) + 0.08, 0.03), GUN)
    # A clamp bar, then the channel down the tail with the rod lying in it.
    hull(P, cbox(-1.0, 1.0, 20.3, 20.75, FT(20.5) - 0.3, FT(20.5) + 0.32, 0.08), LT)
    hull(P, cbox(-0.85, 0.85, 20.75, 24.95, FT(23) - 0.75, FT(23) - 0.15, 0.06), DEEP)
    rz, rr = FT(23) - 0.12, 0.34
    n = 12
    rod = []
    for y in (20.6, 24.8):
        rod.append([P.v((rr * math.cos(2 * math.pi * (k + 0.5) / n), y, rz + rr * math.sin(2 * math.pi * (k + 0.5) / n)))
                    for k in range(n)])
    for k in range(n):
        kk = (k + 1) % n
        P.f((rod[0][k], rod[0][kk], rod[1][kk], rod[1][k]), HATCH, away=(0, 23, rz))
    P.f(rod[1], HATCH, out=(0, 1, 0))
    # Tail face: a dark recessed panel in the core's end, the twin nozzles through it.
    zc = (FT(TAIL_Y) + FB(TAIL_Y)) / 2
    hull(D, cbox(-1.5, 1.5, 24.85, 24.98, zc - 1.1, zc + 0.9, 0.05), DEEP)
    for sx in (-1, 1):
        nx, nz = sx * 0.88, zc - 0.15
        y0 = TAIL_Y - 0.1
        prof = [(0.6, y0, GUN), (0.66, y0 + 0.1, GUN), (0.66, y0 + 0.42, GUN), (0.6, y0 + 0.5, GUN),
                (0.47, y0 + 0.5, GUN), (0.42, y0 + 0.3, GLOW), (0.37, y0 + 0.1, CORE), (0.0, y0 + 0.1, CORE)]
        rings = []
        for r, y, mat in prof:
            rings.append([D.v((nx + r * math.cos(2 * math.pi * (k + 0.5) / 16), y, nz + r * math.sin(2 * math.pi * (k + 0.5) / 16)))
                          for k in range(16)] if r > 0 else [D.v((nx, y, nz))])
        for i in range(len(prof) - 1):
            r0, r1 = rings[i], rings[i + 1]
            ya, yb = prof[i][1], prof[i + 1][1]
            for k in range(16):
                kk = (k + 1) % 16
                if len(r1) == 1:
                    D.f((r0[k], r0[kk], r1[0]), prof[i][2], out=(0, 1, 0))
                elif i >= 4:
                    D.f((r0[k], r0[kk], r1[kk], r1[k]), prof[i][2],
                        away=(nx + 50 * (r0[k].co.x - nx), (ya + yb) / 2, nz + 50 * (r0[k].co.z - nz)))
                elif abs(prof[i][0] - prof[i + 1][0]) > 0.05 and abs(ya - yb) < 0.01:
                    D.f((r0[k], r0[kk], r1[kk], r1[k]), prof[i][2], out=(0, 1, 0))
                else:
                    D.f((r0[k], r0[kk], r1[kk], r1[k]), prof[i][2], away=(nx, (ya + yb) / 2, nz))
    return zc - 0.15


def build_wings(P, D):
    for side in (1, -1):
        def G(y, grow=0.0, side=side):
            return wing_loop(y, side, grow)

        def L(y, side=side):
            return wing_loop(y, side)

        def S(a, b):
            return (a, b)  # the left wing's loop is the right's mirror image, same indices
        ys = [WING_Y0, 9.6, 9.8, 10.1] + frange(10.5, 23.5, 0.5) + [23.75, 23.95, 24.1, WING_Y1]
        loft(P, L, ys, GUN)
        # The front point and the tail spike: one armour shell each, all round.
        plate(P, L, 9.62, 10.65, LT, d=0.16, c=0.08, ch0=False, ystep=0.3)
        plate(P, L, 22.75, 24.1, HATCH, d=0.18, c=0.1, ch1=False, ystep=0.4)
        # Top armour in three bands along the blade (the sprite's light inner ridge, darker middle
        # and light outer blade): an inner strip over the crest and the inner chamfer, a mid plate,
        # the outer blade plate down to the knife edge.
        plate(P, L, 10.8, 22.6, STRIP, *S(-0.75, 0.32), d=0.17, c=0.08)
        plate(P, L, 11.0, 22.4, MID, *S(0.4, 1.0), d=0.12, c=0.06)
        plate(P, L, 10.8, 22.6, LT, *S(1.06, 1.94), d=0.17, c=0.08)
        # A raised inset on the outer blade (the concept's layered armour), and the inner face's
        # panel below the strip.
        plate(P, L, 13.2, 18.6, STRIP, *S(1.2, 1.7), d=0.26, c=0.06, ystep=0.8)
        plate(P, L, 11.0, 22.4, DK, *S(5.05, 5.9), d=0.18, c=0.08)
        # Underneath: two panels and a gear door.
        plate(P, L, 11.0, 22.4, BELLY, *S(2.08, 2.95), d=0.18, c=0.08)
        plate(P, L, 11.0, 15.8, BELLY, *S(3.05, 3.95), d=0.18, c=0.08)
        plate(P, L, 15.95, 22.4, MID, *S(3.05, 3.95), d=0.3, c=0.08, ystep=0.8)
        # Boom: a box-section beam from the body's flank into the blade's inner face, its top a
        # light plate; two pipes under it.
        hull(D, [(side * x, y, z) for x, y, z in cbox(3.2, 7.3, 20.0, 22.0, -0.8, 1.0, 0.25)], LT)
        hull(D, [(side * x, y, z) for x, y, z in cbox(3.6, 6.9, 20.2, 21.45, 0.8, 1.25, 0.14)], STRIP)
        hull(D, [(side * x, y, z) for x, y, z in cbox(3.6, 6.9, 21.5, 21.95, 0.5, 1.15, 0.1)], DK)
        for y, r in ((20.35, 0.2), (21.65, 0.2)):
            n = 8
            ring = []
            for x in (3.6, 6.9):
                ring.append([D.v((side * x, y + r * math.cos(2 * math.pi * k / n), -1.0 + r * math.sin(2 * math.pi * k / n)))
                             for k in range(n)])
            for k in range(n):
                kk = (k + 1) % n
                D.f((ring[0][k], ring[0][kk], ring[1][kk], ring[1][k]), GUN, away=(side * 5.0, y, -1.0))
        # A hinge fairing under the blade where the boom meets it.
        hull(D, [(side * x, y, z) for x, y, z in cbox(6.6, 8.0, 19.2, 22.6, ZB(21) - 0.35, ZB(21) + 0.3, 0.18)], GUN)


def build(coll, sprite):
    mats = materials(sprite)
    hullp = Part("phoenix_hull", smooth_angle=30)
    det = Part("phoenix_details", smooth_angle=35)
    build_fuselage(hullp, det)
    top = Part("phoenix_top", smooth_angle=40)
    nz = build_top(top, det)
    wings = Part("phoenix_wings", smooth_angle=30)
    build_wings(wings, det)
    objs = [T.finish(p, mats, coll) for p in (hullp, wings, det, top)]
    return objs, nz


def bake_maps(obj, out_dir, size=1024, samples=96):
    """The Talon's bake (usp_talon.bake_maps, D50/D53) with this ship's tint and textured slots:
    a grey colour multiplier (ambient occlusion at two scales and an edge lift, tinted) and a
    metallic-roughness map, wired in as Base Color = map x palette colour."""
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "phoenix")


# The game's roll at bank steps 1 and 2, degrees, and shift per frame (hard left .. hard right), game px
# (spriteModels bank.roll and bank.shift, D92; bankShift.ts would give -2.5, -1, 0, 1, 3.5).
BANK_ROLL = [40, 50]
BANK_SHIFT = [-3.5, -1.5, 0, 1.5, 3.5]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs, nz = build(coll, sprite)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"phoenix: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glows (src/ui/backdrop.ts): just behind the twin nozzles, glTF axes.
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round(sx * 0.88 * PX, 4), round(nz * PX, 4),
                                                          round((TAIL_Y + 0.7 - 14) * PX, 4)] for sx in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = out.parent if out else ROOT / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.016, faces=1500, smooth=16)
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT),
                                   image_format=fmt)
    if "--preview" in argv:
        level = next(f for f in sprite["frames"] if f["index"] == sprite["sprites"][0]["frames"][0])
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
