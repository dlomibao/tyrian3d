"""Microcorp Stalker (player ship, tyrian.shp#8 sprite 195 and its banking frames 191-199).

A hard-surface build in the USP Talon's manner (assets/blender/usp_talon.py, DECISIONS D50-D53),
whose geometry helpers it uses. The sprite is authoritative for the plan outline, the windshield and
the colours: the top view follows frame 195 row by row, to the inner edge of its ink border (D74,
docs/agents/OUTLINE-BORDER.md: the game's ink outline stands in for the border), (a straight conical nose widening steadily to
the two forward pods, the narrow neck at rows 14-15, the forward-swept wings with their tips at rows
11-17 and the trailing edge's curve, the rear pods and the tail), the dark glass sits exactly on the
sprite's cockpit pixels (rows 7-11, columns 10-12), and each part takes the palette index the sprite
uses where it covers it. The concept (assets/blender/features/concepts/ship-microcorp-stalker.jpg)
guides the side and front design and the detail where it agrees with the sprite: an ogive nose cone
behind a seam, a framed six-sided canopy with a cross bar, two pods flanking the cockpit whose tails
glow red (the sprite's red neck lights), a narrow neck with vents, a raised mid band, a wide rear
body with long top plates, box wing roots with bright chamfer strakes (the sprite's bright columns
7 and 15) and vent bays, wings with a bright leading-edge strip, an outer rail along the tip and
fore and aft panels with a vent slot, a thin rail along the tips, two engine pods under the wings' trailing edges and a glowing
exhaust plug in a dark nozzle; underneath a keel, a nose gear door, main gear doors under the roots
and intakes under the pods.

How it is built:
- Every part is a low-poly cage in sprite px (x = column - 11.5, the sprite's mirror axis on column
  11; y = sprite row, aft is +y; z up), moved to Blender at the end (X = (x - 0.5) / 12, so column
  11 sits half a pixel left of the 24 px block's centre as in the sprite, Y = (14 - y) / 12, Z = z / 12).
- Sections between stations are monotone cubic (pchip), so lofts never swell. The fuselage and the
  pods are dark cores with a machined section (a chamfered octagon with filleted corners) under
  separate armour plates that stand 0.2-0.35 px proud with 45-degree chamfers, so panel lines are
  real gaps. Wings and wing roots are chamfered slabs; flat faces stay flat (sharp by angle,
  weighted normals). Hidden faces are culled.
- Texture: no concept projection (maps.json says "bake": "model", so tools/build-models.sh and
  texture_bake.py skip it). This script bakes its own ambient occlusion / edge-lift colour map (with
  a slight TINT that keeps the grey neutral under the game's blue sky light and tone mapping) and a
  roughness/metalness map. Base Color = map x palette colour.
- Materials are palette materials; the glows (pod tails red 116, engine plug 120 / 116) are
  emissive palette colours. Satin metal (metallic 0.12-0.18).
- Exported beside it: the outline shell (common.outline_shell, D51) and `tyrian_engines` (the menu
  backdrop's engine glow, at the exhaust plug).

    Blender --background --factory-startup --python ship-microcorp-stalker.py -- [--out path.glb] [--no-bake] [--preview png]

Default: export public/models/ships/ship-microcorp-stalker.glb and its sprite-model entry
(common.export_sprite_model). --out writes only that .glb; --no-bake leaves the model plain.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (hard-surface helpers: pchip, plate, hull, cull_hidden, ...)

NAME = "ship-microcorp-stalker"
MODEL = f"ships/{NAME}"
PX = 1 / 12
pchip, frange, fillet = T.pchip, T.frange, T.fillet

# The baked colour map's tint (linear multipliers on the palette colour), as the Talon's (D53): the
# game's sky light (0x9fb8ff from above) and Neutral tone mapping shift a grey hull; measured in an
# approximation of the game's lighting, this keeps the lit grey as neutral as the sprite's.
TINT = (1.0, 0.985, 0.935)
METAL = 0.3  # metalness scale (satin, D53)

# --- materials ---------------------------------------------------------------------------------

(NOSE, FORE, FRAME, POD, BAND, BODY, SPINE, WBASE, WING, LEAD, RAIL, ROOT, STRIP, RPOD, GUN, DEEP,
 GLASS, RED, GLOW, GLOW_RIM, BELLY, TAIL, RED_DIM) = range(23)

# Palette index per part: the median of the sprite pixels it covers from above, the darkest
# shading (1-3) and the brightest highlights (13-15) left out as lighting (DECISIONS D52; measured
# with a material-id top render): the nose cone 7 (its bright stripe is sheen), the forebody 9, the
# canopy frame 7, the forward pods 9, the neck band and the rear body 6, the wings 6 on a darker
# base 5 with a 10 leading edge (the sprite's bright diagonal) and an 8 tip rail, the roots 5 with
# 11 strakes, the rear pods 6, cores 4, recesses and glass 2, the tail deck 3.
PAL_OF = {NOSE: 7, FORE: 9, FRAME: 7, POD: 9, BAND: 6, BODY: 6, SPINE: 6, WBASE: 5, WING: 6, LEAD: 10,
          RAIL: 8, ROOT: 5, STRIP: 11, RPOD: 6, GUN: 4, DEEP: 2, GLASS: 2, BELLY: 6, TAIL: 3}
SURFACE = {NOSE: (0.6, 0.32), FORE: (0.55, 0.38), FRAME: (0.5, 0.38), POD: (0.6, 0.34), BAND: (0.55, 0.4),
           BODY: (0.55, 0.4), SPINE: (0.6, 0.34), WBASE: (0.5, 0.46), WING: (0.55, 0.4), LEAD: (0.6, 0.3),
           RAIL: (0.55, 0.36), ROOT: (0.55, 0.38), STRIP: (0.6, 0.3), RPOD: (0.6, 0.36), GUN: (0.55, 0.46),
           DEEP: (0.3, 0.8), BELLY: (0.4, 0.55), TAIL: (0.45, 0.6)}


def materials(sprite):
    def pal(slot, tag):
        metallic, rough = SURFACE[slot]
        return common.palette_material(sprite, PAL_OF[slot], f"stalker_{tag}", metallic=metallic * METAL,
                                       roughness=rough)

    def glow(i, tag, strength):
        return common.palette_material(sprite, i, f"stalker_{tag}", metallic=0.0, roughness=0.4,
                                       emission_strength=strength)
    m = [None] * 23
    for slot, tag in ((NOSE, "nose"), (FORE, "fore"), (FRAME, "frame"), (POD, "pod"), (BAND, "band"),
                      (BODY, "body"), (SPINE, "spine"), (WBASE, "wing_base"), (WING, "wing"), (LEAD, "lead"),
                      (RAIL, "rail"), (ROOT, "root"), (STRIP, "strake"), (RPOD, "rear_pod"), (GUN, "gunmetal"),
                      (DEEP, "recess"), (BELLY, "belly"), (TAIL, "tail")):
        m[slot] = pal(slot, tag)
    m[GLASS] = common.palette_material(sprite, 2, "stalker_glass", metallic=0.0, roughness=0.04)
    m[RED] = glow(116, "pod_glow", 3.0)
    m[GLOW] = glow(120, "engine_core", 2.4)
    m[GLOW_RIM] = glow(116, "engine_rim", 2.2)
    m[RED_DIM] = glow(116, "pod_throat", 0.9)  # the rear pods' nozzles: the sprite draws them dark
    return m


TEXTURED = (NOSE, FORE, FRAME, POD, BAND, BODY, SPINE, WBASE, WING, LEAD, RAIL, ROOT, STRIP, RPOD, GUN,
            DEEP, BELLY, TAIL)

# --- sections ----------------------------------------------------------------------------------


def unit_loop(corners, radii, ks):
    """A closed section (half sizes 1 x 1, u right/outboard, v up) from a chamfered polygon given
    clockwise from its top-right corner, its corners filleted; starts at the top centre (s = 0) and
    runs toward +u."""
    return [(0.0, 1.0)] + fillet(corners, radii, ks)


def loop_s(unit, deg):
    """Loop parameter (vertex index + fraction) where the ray at `deg` degrees from straight up,
    toward +u (negative: toward -u), meets the section; negative angles give s below 0."""
    n = len(unit)
    t = math.radians(deg % 360)
    dx, dz = math.sin(t), math.cos(t)
    best = None
    for i in range(n):
        (ax, az), (bx, bz) = unit[i], unit[(i + 1) % n]
        ex, ez = bx - ax, bz - az
        den = dx * ez - dz * ex
        if abs(den) < 1e-12:
            continue
        r = (ax * ez - az * ex) / den
        u = (ax * dz - az * dx) / den
        if r > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or r < best[0]):
            best = (r, i + u)
    return best[1] - (n if deg < 0 and best[1] > n / 2 else 0)


# Fuselage: a flat-topped machined section, wide shoulders and a narrower chined belly.
FUSE_UNIT = unit_loop([(0.32, 1), (1, 0.06), (1, -0.06), (0.32, -1), (-0.32, -1), (-1, -0.06), (-1, 0.06),
                       (-0.32, 1)], (0.25, 0.06, 0.06, 0.25, 0.25, 0.06, 0.06, 0.25), 3)
# Pods: rounder, filleted octagons (the sprite shades them round).
POD_UNIT = unit_loop([(0.5, 1), (1, 0.5), (1, -0.5), (0.5, -1), (-0.5, -1), (-1, -0.5), (-1, 0.5),
                      (-0.5, 1)], (0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42), 3)


# Forward pods: a chined lens (sharp outboard chine at mid height), so that rolled for the banking
# frames they stay as narrow as the sprite's banked forebody (a round pod widens by its height).
QPOD_UNIT = unit_loop([(0.5, 1), (1, 0.04), (1, -0.04), (0.5, -1), (-0.5, -1), (-1, -0.04), (-1, 0.04),
                       (-0.5, 1)], (0.3, 0.05, 0.05, 0.3, 0.3, 0.05, 0.05, 0.3), 3)


def qps(deg):
    return loop_s(QPOD_UNIT, deg)


def fs(deg):
    return loop_s(FUSE_UNIT, deg)


def ps(deg):
    return loop_s(POD_UNIT, deg)


# The plan outline of the nose (half width incl. plates, sprite px): the sprite's straight cone,
# one pixel wider every two rows (0.5 + y / 2), from a point at row 0 to the pods' full width at
# row 7.9. The fuselage follows it to row 4.4; the pods' outboard sides from there.
def cone(y):
    return 0.5 * y - CONE_B


CONE_B = 0.7


# The body (fuselage, pods, roots, engine, canopy) sits Z_BODY px above the wings' plane. The banking
# frames are this model rolled by the game, 17.5 degrees at half bank and 27.5 at full, and moved by
# BANK_SHIFT (BANK_ROLL, D92): the sprite's banks keep the wings' full span and redraw them (the far wing
# foreshortened while its tip stays put), and their opaque columns move right on both hard banks
# though the nose leans into the turn, so bankShift.ts's shift (+1 both ways) is replaced by a fitted
# one. Nothing in the model is shaped for them (no raised body or endplate fins). At that pose they
# measure 0.86-0.88 (half) and 0.78-0.79 (full); the sprite's own level frame, shifted, 0.83 / 0.68-0.70.
Z_BODY = 0.0

NOSE_D = 0.26   # nose cone plate thickness
FORE_D = 0.26
BAND_D = 0.34
BODY_D = 0.3
POD_D = 0.24

# Fuselage stations (row y, core half width, top z, keel z), sprite px.
_FY = [1.0, 1.45, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.4, 6.0, 7.0, 12.0, 13.3, 13.9, 14.3, 15.9, 16.4,
       17.0, 23.4, 24.0, 24.5, 25.0]
FW = pchip(_FY, [0.08, 0.1, 0.24, 0.49, 0.74, 0.99, 1.24, 1.49, 1.72, 1.85, 1.85, 1.85, 1.85, 1.95, 2.12, 2.15,
                 2.15, 3.0, 3.1, 3.1, 3.0, 2.7, 2.2])
_TY = [1.0, 1.5, 2.3, 3.2, 4.0, 4.8, 6.0, 8.0, 12.0, 13.6, 14.3, 16.3, 17.2, 21.5, 23.0, 23.9, 24.5, 25.0]
FT = pchip(_TY, [0.05, 0.12, 0.42, 0.78, 1.1, 1.38, 1.7, 1.95, 1.95, 1.95, 2.15, 2.2, 2.3, 2.3, 2.15, 1.6, 0.95, 0.6])
FB = pchip(_TY, [-0.15, -0.2, -0.45, -0.75, -1.05, -1.3, -1.5, -1.65, -1.65, -1.65, -1.75, -1.8, -1.85, -1.85,
                 -1.75, -1.55, -1.3, -1.1])
FUSE_END = 25.0


def fuse_loop(y, grow=0.0):
    w, t, b = FW(y) + grow, FT(y) + grow, FB(y) - grow
    mid, h = (t + b) / 2, (t - b) / 2
    return [(w * u, mid + h * v) for u, v in FUSE_UNIT], (0.0, mid)


def fuse_top(x, y):
    """Height of the fuselage core's upper surface at (x, y)."""
    pts, _ = fuse_loop(y)
    ax = abs(x)
    best = None
    for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]):
        if min(z0, z1) < (FT(y) + FB(y)) / 2:
            continue
        if min(x0, x1) - 1e-9 <= ax <= max(x0, x1) + 1e-9 and abs(x1 - x0) > 1e-9:
            z = z0 + (z1 - z0) * (ax - x0) / (x1 - x0)
            best = z if best is None else max(best, z)
    return best if best is not None else FT(y) - (FT(y) - FB(y)) * 0.3


# Forward pods: flanking the cockpit, centred on columns 8 and 14 (x = 3) from row 8; their noses
# start inside the fuselage's flank at row 4.2 and sweep out along the sprite's cone to the full
# width (4.45 incl. plates, the sprite's outline ring) at row 7.9; the shell ends at row 11, a dark
# collar follows and the tail is a red glowing exhaust cone (the sprite's red neck lights, rows 12-13).
_QY = [4.8, 5.2, 5.7, 6.2, 6.7, 7.2, 7.7, 8.1, 8.6, 11.0, 11.9]
_QC = [1.6, 1.7, 1.82, 1.94, 2.04, 2.12, 2.18, 2.2, 2.2, 2.2, 2.2]
Q_CX = pchip(_QY, _QC)
Q_W = 3.1  # the forebody's half width over the pods (incl. plates): the inner mask's columns 8-14
Q_RX = pchip(_QY, [max(0.06, min(Q_W, cone(y)) - POD_D - c) for y, c in zip(_QY[:8], _QC)] + [Q_W - POD_D - c for c in _QC[8:]])
Q_CZ = pchip(_QY, [-0.1] * 11)
Q_RZ = pchip(_QY, [0.1, 0.18, 0.26, 0.33, 0.4, 0.45, 0.5, 0.52, 0.53, 0.53, 0.52])
Q_START, Q_END = 4.8, 11.9


def qpod_loop(y, side=1, grow=0.0):
    cx, cz = side * Q_CX(y), Q_CZ(y)
    rx, rz = Q_RX(y) + grow, Q_RZ(y) + grow
    return [(cx + side * rx * u, cz + rz * v) for u, v in QPOD_UNIT], (cx, cz)


# Rear pods: under the wings' trailing edges beside the rear body (rows 20.4-25.9, x 4.4): the
# sprite's lit pods at columns 5-7 and 15-17, rows 21-24, and its row 25 out to column 6.
_RY = [20.4, 20.9, 21.5, 23.9, 24.35, 24.6]
R_CX = pchip(_RY, [4.35] * 6)
R_RX = pchip(_RY, [0.65, 0.86, 0.9, 0.9, 0.84, 0.7])
R_CZ = pchip(_RY, [-0.55] * 6)
R_RZ = pchip(_RY, [0.6, 0.78, 0.84, 0.84, 0.77, 0.62])
R_START, R_END = 20.4, 24.6


def rpod_loop(y, side=1, grow=0.0):
    cx, cz = side * R_CX(y), R_CZ(y)
    rx, rz = R_RX(y) + grow, R_RZ(y) + grow
    return [(cx + side * rx * u, cz + rz * v) for u, v in POD_UNIT], (cx, cz)


# --- small geometry helpers --------------------------------------------------------------------

def clip(poly, a, b, c):
    """The part of polygon `poly` [(x, y)] where a*x + b*y <= c."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def clips(poly, *planes):
    for pl in planes:
        poly = clip(poly, *pl)
    return poly


def area(poly):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def tidy(poly, eps=1e-4):
    """Drop repeated points and points where the outline runs straight on or doubles back (clip()
    leaves them where a cut runs along an edge): they would fold the slab's inset rings."""
    pts = list(poly)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if math.hypot(b[0] - a[0], b[1] - a[1]) < eps or abs(cross) < eps:
                del pts[i]
                changed = True
                break
    return pts


def inset(poly, d):
    """Offset a simple polygon inward by d (miter joins)."""
    n = len(poly)
    sgn = 1 if area(poly) > 0 else -1
    normals = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        normals.append((-(y1 - y0) / ln * sgn, (x1 - x0) / ln * sgn))  # inward
    out = []
    for i in range(n):
        n1, n2 = normals[i - 1], normals[i]
        k = d / max(0.3, 1 + n1[0] * n2[0] + n1[1] * n2[1])
        out.append((poly[i][0] + (n1[0] + n2[0]) * k, poly[i][1] + (n1[1] + n2[1]) * k))
    return out


def slab(part, poly, ztop, zbot, mat, cht=0.12, chb=0.1, side=-1):
    """A chamfered slab over plan polygon `poly` (left side, x < 0, as given; side=1 mirrors it),
    top at ztop(x, y), bottom at zbot(x, y) (planes), the top edge chamfered cht, the bottom chb."""
    pts = tidy([(-x, y) for x, y in poly] if side > 0 else poly)
    if area(pts) < 0:
        pts.reverse()
    rings = [
        [(x, y, zbot(x, y)) for x, y in inset(pts, chb)],
        [(x, y, zbot(x, y) + chb) for x, y in pts],
        [(x, y, ztop(x, y) - cht) for x, y in pts],
        [(x, y, ztop(x, y)) for x, y in inset(pts, cht)],
    ]
    vs = [[part.v(p) for p in r] for r in rings]
    n = len(pts)
    part.f(vs[0], mat, out=(0, 0, -1))
    part.f(vs[3], mat, out=(0, 0, 1))
    for i in range(n):
        j = (i + 1) % n
        (x0, y0), (x1, y1) = pts[i], pts[j]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        nx, ny = (y1 - y0) / ln, -(x1 - x0) / ln  # outward for a CCW polygon (area > 0)
        for k, nz in ((0, -1.0), (1, 0.0), (2, 1.0)):
            part.f((vs[k][i], vs[k][j], vs[k + 1][j], vs[k + 1][i]), mat, out=(nx, ny, nz))


def revolve(part, cx, cz, prof, mats, n=20, outward=True):
    """A body of revolution about the row axis at (cx, cz): prof [(r, y)], mats[i] between i, i+1.
    r = 0 makes a point (a cone tip or a closed end)."""
    rings = []
    for r, y in prof:
        if r <= 1e-6:
            rings.append([part.v((cx, y, cz))])
        else:
            rings.append([part.v((cx + r * math.cos(2 * math.pi * (k + 0.5) / n), y,
                                  cz + r * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)])
    for i in range(len(prof) - 1):
        r0, r1 = rings[i], rings[i + 1]
        (ra, ya), (rb, yb) = prof[i], prof[i + 1]
        ym = (ya + yb) / 2
        for k in range(n):
            kk = (k + 1) % n
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                vs = (r0[0], r1[kk], r1[k])
            elif len(r1) == 1:
                vs = (r0[k], r0[kk], r1[0])
            else:
                vs = (r0[k], r0[kk], r1[kk], r1[k])
            ang = 2 * math.pi * (k + 1) / n
            radial = (math.cos(ang), 0.0, math.sin(ang))
            if abs(ra - rb) > 1e-6 and abs(ya - yb) < 1e-6:  # a flat annulus
                out = (0, 1 if rb < ra else -1, 0) if outward else (0, -1 if rb < ra else 1, 0)
                part.f(vs, mats[i], out=out)
            else:
                sgn = 1 if outward else -1
                if isinstance(outward, (list, tuple)):
                    sgn = 1 if outward[i] else -1
                part.f(vs, mats[i], out=tuple(sgn * c for c in radial))


# --- the ship ----------------------------------------------------------------------------------

def build_fuselage(P):
    L = fuse_loop
    ys = [1.35, 1.6, 1.9] + frange(2.4, FUSE_END, 0.6)  # the tip is the nose cap's
    T.loft(P, L, ys, GUN)
    # Nose cone: one plate all round from just behind the point to the seam at row 4.45; a
    # polished tip over its front edge.
    T.plate(P, L, 1.35, 4.42, NOSE, d=NOSE_D, ch0=False, ystep=0.3, c=0.12)
    sec = T.Section(L, 1.35)
    tip = [sec.at(k, NOSE_D) for k in range(sec.n)]
    hull_pts = tip + [(0.0, 0.95, (FT(1.0) + FB(1.0)) / 2)]
    T.hull(P, hull_pts, NOSE)
    # Forebody: a top deck plate (the canopy's frame sits on it), shoulder and flank plates split
    # at row 8.6, a chin plate; the dark core shows in the seams.
    T.plate(P, L, 4.62, 11.95, FORE, s0=fs(-36), s1=fs(36), d=FORE_D, c=0.12)
    for side in (1, -1):
        def S(a, b, side=side):
            return (fs(a), fs(b)) if side > 0 else (fs(-b), fs(-a))
        T.plate(P, L, 4.62, 8.5, FORE, *S(39, 92), d=FORE_D, c=0.12)
        T.plate(P, L, 8.65, 13.75, FORE, *S(39, 92), d=FORE_D, c=0.12)
        T.plate(P, L, 4.62, 13.75, FORE, *S(95, 150), d=0.22, c=0.1)
    T.plate(P, L, 4.62, 10.0, BELLY, s0=fs(153), s1=fs(207), d=0.22)
    T.plate(P, L, 10.15, 13.75, BELLY, s0=fs(153), s1=fs(207), d=0.22)
    # Behind the canopy (rows 12.1-13.75): the neck deck, lighter (the sprite's rows 12-13).
    T.plate(P, L, 12.12, 13.75, SPINE, s0=fs(-36), s1=fs(36), d=FORE_D, c=0.1)
    # Mid band round the neck (rows 13.95-16.45), proud, chamfered both ends.
    T.plate(P, L, 13.95, 16.45, BAND, d=BAND_D, c=0.14, ystep=0.5)
    # Rear body: long top plates either side of a centre seam, flank plates in two, belly plates.
    for s0, s1 in ((fs(-40), fs(-2.5)), (fs(2.5), fs(40))):
        T.plate(P, L, 16.65, 24.1, SPINE, s0=s0, s1=s1, d=BODY_D, c=0.13)
    for side in (1, -1):
        def S(a, b, side=side):
            return (fs(a), fs(b)) if side > 0 else (fs(-b), fs(-a))
        T.plate(P, L, 16.65, 20.3, BODY, *S(43, 100), d=BODY_D, c=0.12)
        T.plate(P, L, 20.45, 24.1, BODY, *S(43, 100), d=BODY_D, c=0.12)
        T.plate(P, L, 16.65, 24.1, BELLY, *S(103, 150), d=0.24, c=0.1)
    T.plate(P, L, 16.65, 20.3, BELLY, s0=fs(153), s1=fs(207), d=0.24)
    T.plate(P, L, 20.45, 24.1, BELLY, s0=fs(153), s1=fs(207), d=0.24)
    # Tail deck: a dark ring over the boat tail between the rear pods, back edge chamfered.
    T.plate(P, L, 24.22, FUSE_END, TAIL, d=0.22, c=0.12, ystep=0.5)


def build_details(P):
    # Neck vents behind the canopy: dark grilles either side of the deck's centre, three slats each.
    for sx in (-1, 1):
        y0, y1 = 12.35, 13.55
        x0, x1 = 0.55, 1.45
        z = FT(13.0) + FORE_D
        T.hull(P, [(sx * x, y, zz) for x, y, zz in T.cbox(x0, x1, y0, y1, z - 0.4, z + 0.06, 0.05)], DEEP)
        for k in range(3):
            yy = y0 + 0.2 + k * 0.38
            T.hull(P, [(sx * x, y, zz) for x, y, zz in T.cbox(x0 + 0.05, x1 - 0.05, yy, yy + 0.14, z - 0.2, z + 0.16, 0.03)], FRAME)
    # Mid band: three short vent slits on top (the concept's mark).
    for k in range(3):
        y = 14.75 + k * 0.4
        z = FT(y) + BAND_D
        T.hull(P, T.cbox(-0.55, 0.55, y, y + 0.18, z - 0.25, z + 0.04, 0.04), DEEP)
    # Keel strake under the rear body, deepest in the middle; chin fairing under the nose with a
    # nose gear door.
    pts = []
    for y, drop in ((15.0, 0.1), (16.5, 0.45), (21.5, 0.45), (24.0, 0.1)):
        b = FB(y) - 0.2
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.34, b + 0.4), (0.24, b - drop), (0.1, b - drop - 0.08))]
    T.hull(P, pts, GUN)
    for sx in (-1, 1):
        T.hull(P, [(sx * x, y, z) for x, y, z in T.cbox(0.08, 0.75, 5.4, 9.6, FB(7.5) - 0.25, FB(7.5) + 0.2, 0.08)], BELLY)
        for y0 in (5.6, 8.9):
            T.hull(P, [(sx * x, y, z) for x, y, z in T.cbox(0.82, 1.05, y0, y0 + 0.5, FB(7.5) - 0.3, FB(7.5) + 0.2, 0.04)], GUN)


# Windshield: the sprite's dark cockpit pixels (rows 7-11, columns 10-12): a six-sided pane 2.9 px
# wide from row 7.05 to 11.95, its front corners cut more than its rear, raised in a frame.
CAN_Y0, CAN_Y1, CAN_W = 7.04, 11.96, 1.49
CAN_YC = 9.6


def _canopy_base():
    cf, cr = 0.5, 0.36
    corners = [(CAN_W - cf, CAN_Y0), (CAN_W, CAN_Y0 + cf), (CAN_W, CAN_Y1 - cr), (CAN_W - cr, CAN_Y1),
               (-CAN_W + cr, CAN_Y1), (-CAN_W, CAN_Y1 - cr), (-CAN_W, CAN_Y0 + cf), (-CAN_W + cf, CAN_Y0)]
    return fillet(corners, 0.16, 2)


CAN_BASE = _canopy_base()
CAN_N = len(CAN_BASE)


def canopy_outline(grow=0.0):
    pts = [list(p) for p in CAN_BASE]
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
    return FT(y) + FORE_D


GLASS_BASE, GLASS_H = 0.18, 0.95


def glass_z(r, y):
    return deck_top(y) + GLASS_BASE + GLASS_H * max(0.0, 1 - r ** 2.4) ** 0.5


def build_canopy(G, F):
    C = canopy_outline()
    K = 9
    rings = []
    for k in range(K + 1):
        r = 1 - k / K * 0.97
        rings.append([G.v((x * r, CAN_YC + (y - CAN_YC) * r, glass_z(r, CAN_YC + (y - CAN_YC) * r))) for x, y in C])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(CAN_N):
            j = (i + 1) % CAN_N
            G.f((r0[i], r0[j], r1[j], r1[i]), GLASS, away=(0, CAN_YC, 0))
    G.f(rings[-1], GLASS, out=(0, 0, 1))
    low = [G.v((x, y, deck_top(y) + GLASS_BASE - 0.3)) for x, y in C]
    for i in range(CAN_N):
        j = (i + 1) % CAN_N
        G.f((low[i], low[j], rings[0][j], rings[0][i]), GLASS, out=(C[i][0], C[i][1] - CAN_YC, 0))
    # Frame sill: a ring from the glass's edge out over the deck, flat top, chamfered outer edge.
    inner = canopy_outline(-0.06)
    top_out = canopy_outline(0.2)
    ch_out = canopy_outline(0.34)
    fr = []
    for k in range(CAN_N):
        (xi, yi), (xo, yo), (xc, yc) = inner[k], top_out[k], ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.14
        fr.append([F.v((xi, yi, deck_top(yi) + GLASS_BASE - 0.3)), F.v((xi, yi, zt)), F.v((xo, yo, zt)),
                   F.v((xc, yc, zt - 0.14)), F.v((xc, yc, fuse_top(xc, yc) - 0.3))])
    for k in range(CAN_N):
        j = (k + 1) % CAN_N
        cx, cy = top_out[k]
        for i in range(4):
            out = (cx, cy - CAN_YC, 0) if i >= 2 else ((-cx, -(cy - CAN_YC), 0) if i == 0 else (0, 0, 1))
            if i == 2:
                out = (cx * 0.5, (cy - CAN_YC) * 0.5, 1)
            F.f((fr[k][i], fr[j][i], fr[j][i + 1], fr[k][i + 1]), FRAME, out=out)
    # Cross bar between the front pane and the long rear pane (row 8.3), and a short spine bar
    # behind it, proud of the glass.
    yb = 8.3
    pts = []
    for k in range(9):
        x = -CAN_W + 2 * CAN_W * k / 8
        r = min(1.0, abs(x) / CAN_W)
        z = glass_z(r, yb) + 0.07
        pts += [(x, yb - 0.12, z), (x, yb + 0.12, z), (x, yb - 0.12, deck_top(yb)), (x, yb + 0.12, deck_top(yb))]
    T.hull(F, pts, FRAME)


def build_qpods(P, D):
    for side in (1, -1):
        def L(y, side=side):
            return qpod_loop(y, side)

        def G(y, grow, side=side):
            return qpod_loop(y, side, grow)
        rings = [(G, y, 0.0) for y in frange(Q_START, Q_END, 0.45)]
        T.loft_rings(P, rings, [GUN] * len(rings))
        # Front cowl (an ogive over the nose, its tip polished) and the rear shell in two (a seam
        # along the upper outboard side); a dark collar behind the shell.
        T.plate(P, L, 4.95, 8.05, POD, d=POD_D, ch0=False, c=0.1, ystep=0.35)
        sec = T.Section(L, 4.95)
        T.hull(P, [sec.at(k, POD_D) for k in range(sec.n)] + [(side * Q_CX(4.8), 4.72, Q_CZ(4.8))], POD)

        def A(a, b, gap=0.0):
            return dict(s0=qps(a) + gap, s1=qps(b) - gap)
        T.plate(P, L, 8.2, 10.95, POD, **A(-150, 52), d=POD_D, c=0.12, ystep=0.6)
        T.plate(P, L, 8.2, 10.95, POD, **A(55, 205), d=POD_D, c=0.12, ystep=0.6)
        T.plate(P, L, 11.08, 11.9, TAIL, d=0.16, c=0.08, ystep=1)
        # Intake under the pod's front: a gunmetal lip round a dark mouth.
        cx = side * Q_CX(8.4)
        zb = Q_CZ(8.4) - Q_RZ(8.4)
        T.hull(D, [(cx + side * x, y, z) for x, y, z in T.cbox(-0.6, 0.2, 7.6, 10.2, zb - 0.22, zb + 0.4, 0.1)], GUN)
        T.hull(D, [(cx + side * x, y, z) for x, y, z in T.cbox(-0.48, 0.08, 7.52, 7.7, zb - 0.14, zb + 0.15, 0.04)], DEEP)
        # The tail: a dark nozzle lip and the red glowing exhaust cone in it (rows 11.9-13.95).
        cx, cz = side * Q_CX(11.9), Q_CZ(11.9)
        k = (Q_W - Q_CX(11.9)) / 0.95  # the nozzle's radius to the forebody's half width
        revolve(D, cx, cz, [(0.8 * k, 11.75), (0.95 * k, 11.85), (0.95 * k, 12.3), (0.87 * k, 12.42), (0.0, 12.42)],
                [GUN, GUN, GUN, GUN], n=20)
        revolve(D, cx, cz, [(0.0, 12.2), (0.84 * k, 12.2), (0.91 * k, 12.6), (0.9 * k, 13.3), (0.75 * k, 13.75),
                            (0.4 * k, 13.98), (0.0, 14.02)], [RED] * 6, n=20)


def build_rpods(P, D):
    for side in (1, -1):
        def L(y, side=side):
            return rpod_loop(y, side)

        def G(y, grow, side=side):
            return rpod_loop(y, side, grow)
        rings = [(G, y, 0.0) for y in frange(R_START, R_END, 0.5)]
        T.loft_rings(P, rings, [GUN] * len(rings))

        def A(a, b, gap=0.0):
            return dict(s0=ps(a) + gap, s1=ps(b) - gap)
        T.plate(P, L, 20.95, 23.95, RPOD, **A(-130, 50), d=POD_D, c=0.12, ystep=0.6)
        T.plate(P, L, 20.95, 23.95, RPOD, **A(53, 227), d=POD_D, c=0.12, ystep=0.6)
        T.plate(P, L, 24.08, R_END, TAIL, d=0.2, c=0.12, ystep=0.5)
        # Intake ring at the front (under the wing), dark mouth.
        cx, cz = side * R_CX(20.4), R_CZ(20.4)
        revolve(D, cx, cz, [(0.0, 20.5), (0.52, 20.5), (0.52, 20.28), (0.7, 20.2), (0.8, 20.42), (0.8, 20.9)],
                [DEEP, GUN, GUN, GUN, GUN], n=18)
        # Deep nozzle out of the tail: collar, bell, dim red throat.
        y0 = R_END - 0.15
        revolve(D, cx, cz, [(0.6, y0), (0.66, y0 + 0.1), (0.66, y0 + 0.4), (0.53, y0 + 0.5), (0.46, y0 + 0.1),
                            (0.36, y0 - 0.25), (0.0, y0 - 0.25)], [GUN, GUN, GUN, DEEP, DEEP, RED_DIM],
                n=18, outward=[True, True, True, False, False, True])


def build_engine(D):
    # The main exhaust at the tail: a dark nozzle lip round a glowing plug (the sprite's glow at
    # row 25, columns 10-12).
    cz = 0.15
    revolve(D, 0.0, cz, [(1.15, 24.3), (1.42, 24.45), (1.42, 24.85), (1.3, 24.97), (1.22, 24.8)], [GUN] * 4, n=24,
            outward=[True, True, True, False])
    # The glowing plug out of the lip (the sprite's 116-120-116 at row 25; its dark row 26 is ink).
    revolve(D, 0.0, cz, [(1.22, 24.75), (1.3, 25.2), (1.22, 25.62), (1.04, 25.9)], [GLOW_RIM, GLOW, GLOW_RIM], n=24)
    revolve(D, 0.0, cz, [(1.04, 25.9), (0.0, 25.9)], [GLOW], n=24)


# Wings (left; the right is their mirror): plan outline in sprite px. The leading edge is the
# sprite's diagonal (x = y - 20, row 11 to 16), the tip's front edge row 11, its outer edge column
# 1 to row 17, then the trailing edge's curve (steep near the tip, flatter toward the pods) to the
# rear pod at row 25.1.
WING_PLAN = [(-3.0, 16.5), (-4.5, 16.5), (-9.0, 12.0), (-9.25, 12.0), (-9.5, 12.25), (-9.5, 17.6),
             (-8.5, 18.6), (-7.5, 20.1), (-6.4, 22.4), (-5.6, 23.4), (-4.3, 23.4), (-3.0, 23.4)]
FIN_PLAN = [(-9.5, 12.3), (-9.5, 17.6), (-8.5, 18.6), (-7.5, 20.1), (-7.05, 21.1), (-6.72, 20.95),
            (-7.2, 19.9), (-8.2, 18.4), (-9.12, 17.45), (-9.12, 12.6)]
FIN_UP, FIN_DN = 0.45, 0.3
FIN_Y0 = 16.4  # the rail's aft part; forward of it the tip strip
PRONG_X = 9.05
PRONG_PLAN = [(-9.5, 12.25), (-9.5, FIN_Y0 + 0.4), (-PRONG_X, FIN_Y0 + 0.4), (-PRONG_X, 12.7)]
PRONGS = [(-0.3, 0.45)]  # the tip strip forward of the rail (z0, z1)
WZ0, WK = -0.4, 0.085  # wing mid plane: z = WZ0 + WK * (|x| - 3)


def wing_mid(x):
    return WZ0 + WK * (abs(x) - 3)


def wing_t(x):
    return max(0.55, 1.0 - 0.062 * (abs(x) - 3))


def wtop(x, y):
    return wing_mid(x) + wing_t(x) / 2


def wbot(x, y):
    return wing_mid(x) - wing_t(x) / 2


def build_wings(W, FN):
    lead_c = 22.45  # -x + y <= 22.45: the leading-edge strip, 1 px deep from the edge (x - y = -21)
    gap = 0.12
    for side in (-1, 1):
        slab(W, WING_PLAN, wtop, wbot, WBASE, cht=0.16, chb=0.12, side=side)

        def panel(poly, d, mat, ch=0.1, side=side):
            if len(poly) < 3 or abs(area(poly)) < 0.05:
                return
            slab(W, poly, lambda x, y: wtop(x, y) + d, lambda x, y: wtop(x, y) - 0.2, mat, cht=ch, chb=0.02,
                 side=side)
        outer = WING_PLAN
        # Leading-edge strip along the diagonal and the tip's front edge (bright, the sprite's 8s).
        panel(clips(outer, (-1, 1, lead_c), (-1, 0, 8.55 - gap), (0, 1, 16.5), (1, 0, -4.5)), 0.2, LEAD, ch=0.12)
        # Outer rail along the tip.
        panel(clips(outer, (1, 0, -8.67), (0, 1, 17.5)), 0.24, RAIL, ch=0.12)
        # Fore panel: between the strip and a chordwise seam at row 18.3, with a vent slot cut in
        # it (a dark grille in a gap, parallel to the leading edge).
        fore = clips(outer, (1, -1, -(lead_c + gap)), (-1, 0, 8.67 - gap), (0, 1, 18.25), (1, 0, -4.82))
        s0, s1 = 23.9, 24.55  # the slot band: -x + y between these
        panel(clips(fore, (-1, 1, s0 - gap / 2)), 0.16, WING)
        panel(clips(fore, (1, -1, -(s1 + gap / 2))), 0.16, WING)
        panel(clips(fore, (1, -1, -s0), (-1, 1, s1), (1, 0, -7.7)), 0.16, WING)
        panel(clips(fore, (1, -1, -s0), (-1, 1, s1), (-1, 0, 5.6)), 0.16, WING)
        slot = clips(fore, (1, -1, -s0 + 0.02), (-1, 1, s1 - 0.02), (-1, 0, 7.7 - 0.02), (1, 0, -5.6 + 0.02))
        panel(slot, 0.02, DEEP, ch=0.02)
        # Aft panel to the trailing edge, and a narrow flap strip along it.
        aft = clips(outer, (0, -1, -(18.25 + gap)), (1, 0, -4.82))
        panel(aft, 0.16, WING)
        # A rail along the tip and the trailing edge's outer corner, FIN_UP above and FIN_DN below
        # the wing's plane.
        slab(FN, clips(FIN_PLAN, (0, -1, -FIN_Y0)), lambda x, y: FIN_UP, lambda x, y: -FIN_DN, RAIL, cht=0.12,
             chb=0.12, side=side)
        # Forward of the rail, a strip along the tip.
        for z0, z1 in PRONGS:
            slab(FN, PRONG_PLAN, lambda x, y, z1=z1: z1, lambda x, y, z0=z0: z0, RAIL, cht=0.08, chb=0.08, side=side)


def build_roots(W):
    """Box wing roots beside the rear body (rows 16-22.2, |x| 2.7-4.62): a flat top inboard and a
    bright strake (the sprite's columns 7 and 15) sloping down to the outer edge, a vent bay in the
    outer face above the wing, and a main gear door underneath."""
    for sx in (-1, 1):
        # bottom (at the wing's underside: the body stands Z_BODY above the wings), inner top, the
        # strake's outer edge
        zb, zt, zo = -0.55 - Z_BODY, 1.75, 1.15

        def box(x0, x1, y0, y1, z0, z1, ch, mat):
            T.hull(W, [(sx * x, y, z) for x, y, z in T.cbox(x0, x1, y0, y1, z0, z1, ch)], mat)
        box(2.7, 3.62, 16.02, 23.2, zb, zt, 0.12, ROOT)
        box(3.4, 4.62, 16.9, 23.2, zb, zo - 0.05, 0.1, ROOT)
        # The strake: a polished plate on the sloping top, chamfered at its ends.
        pts = []
        for y, e in ((16.96, 0.12), (17.13, 0.0), (22.97, 0.0), (23.14, 0.12)):
            pts += [(sx * x, y, z) for x, z in ((3.56 + e, zt + 0.04 - e), (4.6 - e, zo - e), (4.6 - e, zo - 0.4),
                                                (3.56 + e, zo - 0.4))]
        T.hull(W, pts, STRIP)
        # Vent bay in the outer face: a dark recess with four slats across it.
        zw = wtop(4.6, 18) + 0.15 - Z_BODY
        box(4.5, 4.66, 17.1, 20.0, zw, zo - 0.3, 0.03, DEEP)
        for k in range(4):
            y = 17.3 + k * 0.66
            box(4.55, 4.74, y, y + 0.2, zw + 0.05, zo - 0.35, 0.03, FRAME)
        # Main gear door under the root: a proud panel with hinge blocks.
        box(2.9, 4.4, 17.2, 21.5, zb - 0.16, zb + 0.1, 0.06, BELLY)
        for y0 in (17.5, 20.7):
            box(3.0, 3.25, y0, y0 + 0.45, zb - 0.3, zb + 0.05, 0.03, GUN)


def finish(part, mats, coll, dz=0.0):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Sprite px to Blender: X = (x - 0.5) / 12, Y = (14 - y) / 12, Z = (z + dz) / 12 (a reflection in y).
    m = Matrix(((PX, 0, 0, -0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, dz * PX), (0, 0, 0, 1)))
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
    hullp = T.Part("stalker_hull", smooth_angle=30)
    build_fuselage(hullp)
    det = T.Part("stalker_details", smooth_angle=35)
    build_details(det)
    glass = T.Part("stalker_glass", smooth_angle=50)
    frame = T.Part("stalker_frame", smooth_angle=30)
    build_canopy(glass, frame)
    pods = T.Part("stalker_pods", smooth_angle=34)
    build_qpods(pods, det)
    build_rpods(pods, det)
    eng = T.Part("stalker_engine", smooth_angle=40)
    build_engine(eng)
    wings = T.Part("stalker_wings", smooth_angle=30)
    fins = T.Part("stalker_fins", smooth_angle=30)
    build_wings(wings, fins)
    roots = T.Part("stalker_roots", smooth_angle=30)
    build_roots(roots)
    objs = [finish(p, mats, coll, dz=0.0 if p in (wings, fins) else Z_BODY)
            for p in (hullp, pods, det, wings, fins, roots, eng, glass, frame)]
    for o in objs:
        print("stalker part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


def bake_maps(obj, out_dir, size=1024, samples=96):
    """As the Talon's (usp_talon.bake_maps): UV the model and bake a grey colour multiplier
    (ambient occlusion at two scales and an edge lift, times TINT) and a roughness/metalness map,
    then Base Color = map x palette colour."""
    saved_t, saved_tint = T.TEXTURED, T.TINT
    T.TEXTURED, T.TINT = TEXTURED, TINT
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TEXTURED, T.TINT = saved_t, saved_tint
    for img in list(bpy.data.images):  # name the images (and their files) after this model
        if img.name.startswith("talon_"):
            old = Path(out_dir) / f"{img.name}.png"
            img.name = "stalker_" + img.name[len("talon_"):]
            new = Path(out_dir) / f"{img.name}.png"
            if old.exists():
                old.replace(new)
            img.filepath_raw = str(new)


# The game's roll at bank steps 1 and 2, degrees, and shift per frame (hard left .. hard right), game px
# (spriteModels bank.roll and bank.shift, D92; bankShift.ts would give 1, 0, 0, 0, 1).
BANK_ROLL = [17.5, 27.5]
BANK_SHIFT = [-0.5, -0.5, 0, 0.5, 2.5]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj, grid=10)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"stalker: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glow (src/ui/backdrop.ts), glTF axes (x, y up, z aft): just
    # behind the exhaust plug, orange (palette 120's hue).
    obj["tyrian_engines"] = {"color": "#ff5a1e", "at": [[round(-0.5 * PX, 4), round((0.15 + Z_BODY) * PX, 4), round((26.4 - 14) * PX, 4)]]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = out.parent if out else root / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, faces=1500)
    print(f"stalker: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT),
                                   image_format=fmt)
    if "--preview" in argv:
        level = next(f for f in sprite["frames"] if f["index"] == sprite["sprites"][0]["frames"][0])
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
