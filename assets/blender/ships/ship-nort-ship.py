"""Nort ship (player ship, tyrian.shp#8 frame 220, drawn 48 x 28): a hard-surface build in the USP
Talon's manner (assets/blender/usp_talon.py, DECISIONS.md D50-D53).

The sprite is authoritative for the plan outline, the windshield and the colours (D52): the top view
follows frame 220 row by row, its edge on the INNER edge of the sprite's ink border (D74,
docs/agents/OUTLINE-BORDER.md: the game's own outline stands in for the ring; tools/sprite_mask.py
--measure, iou_rule_grid >= 0.95) (a pointed nose cowl with two blue canards, red gun barrels standing
on its shoulders, a wide delta of two swept wings with blue leading-edge bands and two tall body
blocks, two engine nozzles and the V notch between them), the small dark windshield sits exactly
over the sprite's glass pixels (rows 4-6, three columns wide), and each part takes the palette index
the sprite uses where it covers it (the median of those pixels, the darkest shading 1-3 / 48 and the
highlights 14-15 left out as lighting). The concept (assets/blender/features/concepts/ship-nort-ship.jpg)
guides the side and front design and the detail where it agrees with the sprite.

The parts: a lofted, chamfered nose cowl (dark core under separate armour plates with real panel
gaps, Talon style) carrying the framed windshield and, behind it, a machined drum (wall, groove,
rim band and a dome with a ring seam and a cap); a dark machinery chassis under everything, seen in
the channels between the parts; on each side a gun (red barrel with a dark bore, a grey collar and
a mount) with a red light at its foot, a body block (chamfered core with a sloped front bevel and a
wide inner bevel down to the spine, two lengthwise top plates, a two-bay intake grille and a rear
lip), an engine housing and a deep converging nozzle with a glowing throat, a swept wing (a
leading-edge strip, the blue band set between plates, the main plate and a rear plate, a tip rail),
and a pipe run in the channel; the spine between the blocks with a raised centre strip, a vent and
the V tail. Underneath: belly plates, a nose gear door, block gear doors, a keel and wing strakes.
The sprite's bright pixels are sheen (rubric), not modelled bumps.

How it is built (as the Talon): parts are cages in sprite px (x = column - 23.5, the axis, so the
ship is symmetric; y = sprite row, aft +y; z up), moved to Blender at the end (X = (x - 0.5) / 12,
Y = (14 - y) / 12, Z = z / 12: the origin is the middle of the 48 x 28 block). Lofted sections
use monotone cubic (pchip) station curves, so they never swell. Flat faces stay flat (sharp by
angle, weighted normals). No concept projection: texture_bake.py skips this model ("bake": "model"
in its maps.json) and this script bakes its own occlusion/edge colour map (slightly cool: TINT, so
the grey survives the game's tone mapping) and a roughness/metalness map. Materials are palette
materials, satin (metallic <= 0.2). Exported beside it: the outline shell (common.outline_shell)
and `tyrian_engines` (the menu's two engine glows).

    Blender --background --factory-startup --python ship-nort-ship.py -- [--out path.glb] [--no-bake] [--preview png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (the Talon's hard-surface toolkit: Part, plate, hull, pchip, culling)
from usp_talon import Part, cbox, frange, hull, pchip, plate  # noqa: E402

NAME = "ship-nort-ship"
MODEL = f"ships/{NAME}"
PX = 1 / 12

# Material slots.
(HULL9, HULL8, EDGE7, CORE5, NOZ6, DARK3, DECK4, REC2, GLASS, BLUE, CANARD, RED, LIGHT, GLOW, THROAT,
 BELLY, STRIP, FRAME) = range(18)

# Palette index per slot: the median index of the sprite pixels each part covers (DECISIONS D52):
# cowl, block plates and spine 9; wings, drum and nozzle shroud 8 (the drum's panel seams 3-4);
# leading edges, lips, collars and the belly 7; nozzles 6; block bevels, housings and cores 5; the
# machinery deck and the windshield frame 4; recesses and grilles 2; glass 48; the band 57 (55-59),
# the canards 53; gun barrels 69, their lights 68; the spine's centre strip 10.
PAL_OF = {HULL9: 9, HULL8: 8, EDGE7: 7, CORE5: 5, NOZ6: 6, DARK3: 3, DECK4: 4, REC2: 2, GLASS: 48,
          BLUE: 57, CANARD: 53, RED: 69, LIGHT: 68, BELLY: 7, STRIP: 10, FRAME: 4}
# Engine glow colours, palette 5 as the Talon's (orange 121, yellow-orange 123).
GLOW_PAL = {121: (231, 97, 12), 123: (243, 174, 36)}

# Metalness scale (D53): satin, so the reflections do not tint the grey.
METAL = 0.3
# The baked colour map's tint (linear multipliers on the palette colour), as the Talon's TINT (D53),
# set from captures of the game itself: there the sky light and tone mapping turn this grey slightly
# blue (ship pixels blue/red 1.07 with a cool tint, against the sprite greys' 1.00), so unlike the
# Talon's tan the grey needs a hair of warmth to read the sprite's neutral steel.
TINT = (1.0, 0.975, 0.91)


def materials(sprite):
    def pal(slot, tag, metallic, roughness, emission=0.0):
        return common.palette_material(sprite, PAL_OF[slot], f"nort_{tag}", metallic=metallic * METAL,
                                       roughness=roughness, emission_strength=emission)

    def glow(i, tag, strength):
        c = common.srgb(*GLOW_PAL[i])
        return common.material(f"pal_{i}_nort_{tag}", c, metallic=0.0, roughness=0.4, emission=c,
                               emission_strength=strength)
    return [
        pal(HULL9, "hull", 0.6, 0.38),
        pal(HULL8, "hull_dk", 0.6, 0.4),
        pal(EDGE7, "edge", 0.6, 0.36),
        pal(CORE5, "core", 0.5, 0.46),
        pal(NOZ6, "nozzle", 0.65, 0.34),
        pal(DARK3, "seam", 0.4, 0.6),
        pal(DECK4, "deck", 0.45, 0.55),
        pal(REC2, "recess", 0.3, 0.75),
        common.palette_material(sprite, 48, "nort_glass", metallic=0.0, roughness=0.04),
        pal(BLUE, "band", 0.4, 0.3),
        pal(CANARD, "canard", 0.4, 0.34),
        pal(RED, "barrel", 0.35, 0.34),
        pal(LIGHT, "light", 0.0, 0.4, emission=3.0),
        glow(121, "engine_glow", 1.6),
        glow(123, "engine_core", 2.2),
        pal(BELLY, "belly", 0.45, 0.5),
        pal(STRIP, "strip", 0.6, 0.32),
        pal(FRAME, "frame", 0.5, 0.4),
    ]


# --- plan polygons -------------------------------------------------------------------------------

def area(poly):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def offset_poly(poly, ds):
    """Move each edge i (poly[i] -> poly[i + 1]) of a CCW polygon inward by ds[i]; mitred corners."""
    n = len(poly)
    ds = ds if isinstance(ds, (list, tuple)) else [ds] * n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        lines.append(((x0 - uy * ds[i], y0 + ux * ds[i]), (ux, uy)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def clip(poly, a, b, c):
    """Sutherland-Hodgman: the part of poly where a*x + b*y + c <= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    # drop near-duplicate points
    res = []
    for p in out:
        if not res or math.hypot(p[0] - res[-1][0], p[1] - res[-1][1]) > 1e-4:
            res.append(p)
    if len(res) > 1 and math.hypot(res[0][0] - res[-1][0], res[0][1] - res[-1][1]) < 1e-4:
        res.pop()
    return res


def region(poly, *planes):
    for a, b, c in planes:
        poly = clip(poly, a, b, c)
    return poly


def mirror(poly):
    return [(-x, y) for x, y in poly]


def slab(part, poly, z0, z1, mat, ch=0.15, chb=0.1, drop=None, top=None, bot=None, chm=None):
    """A chamfered prism on a plan polygon (any simple polygon, either winding), from z0 to z1
    (plus top(x, y) / bot(x, y) offsets, planar for flat faces): 45-degree chamfers `ch` (a number,
    or a list per edge with a common vertical `drop`) round the top and `chb` round the bottom.
    chm: an optional list of materials per edge for the top chamfers."""
    n = len(poly)
    chs = list(ch) if isinstance(ch, (list, tuple)) else [ch] * n
    chm = list(chm) if chm else [mat] * n
    if area(poly) < 0:  # make it CCW; edge i of the reversed polygon is the old edge n - 2 - i
        poly = poly[::-1]
        chs = [chs[(n - 2 - i) % n] for i in range(n)]
        chm = [chm[(n - 2 - i) % n] for i in range(n)]
    drop = max(chs) if drop is None else drop
    ztop = (lambda x, y: z1 + top(x, y)) if top else (lambda x, y: z1)
    zbot = (lambda x, y: z0 + bot(x, y)) if bot else (lambda x, y: z0)
    rings = []
    if chb > 0:
        rings.append([part.v((x, y, zbot(x, y))) for x, y in offset_poly(poly, chb)])
        rings.append([part.v((x, y, zbot(x, y) + chb)) for x, y in poly])
    else:
        rings.append([part.v((x, y, zbot(x, y))) for x, y in poly])
    if max(chs) > 0:
        rings.append([part.v((x, y, ztop(x, y) - drop)) for x, y in poly])
        rings.append([part.v((x, y, ztop(x, y))) for x, y in offset_poly(poly, chs)])
    else:
        rings.append([part.v((x, y, ztop(x, y))) for x, y in poly])
    part.f(rings[0], mat, out=(0, 0, -1))
    part.f(rings[-1], mat, out=(0, 0, 1))
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        last = k == len(rings) - 2 and max(chs) > 0
        for i in range(n):
            j = (i + 1) % n
            (x0, y0), (x1, y1) = poly[i], poly[j]
            ox, oy = (y1 - y0), -(x1 - x0)  # outward for CCW
            oz = -0.5 if (k == 0 and chb > 0) else (0.5 if last else 0.0)
            part.f((r0[i], r0[j], r1[j], r1[i]), chm[i] if last else mat, out=(ox, oy, oz))


def both(fn):
    """Call fn(side, X) for side 1 and -1, X mapping a right-side x (or polygon) to that side."""
    for side in (1, -1):
        fn(side, (lambda p: p) if side > 0 else mirror)


# --- revolved and ringed bodies -------------------------------------------------------------------

def yrev(part, cx, cz, prof, n=20, phase=0.5):
    """A body of revolution about the y axis through (cx, cz): prof [(r, y, mat, _)], the material of
    the band from each entry to the next. The profile runs round the solid (out along the front, aft
    along the outside, in at the back or down a bore); r = 0 closes to a point."""
    rings = []
    for r, y, _, _ in prof:
        if r <= 0:
            rings.append([part.v((cx, y, cz))])
        else:
            rings.append([part.v((cx + r * math.cos(2 * math.pi * (k + phase) / n), y,
                                  cz + r * math.sin(2 * math.pi * (k + phase) / n))) for k in range(n)])
    for i in range(len(prof) - 1):
        r0, r1 = rings[i], rings[i + 1]
        (ra, ya, mat, inward), (rb, yb, _, _) = prof[i], prof[i + 1]
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
            a = 2 * math.pi * (k + 0.5) / n
            # The profile runs round the solid with it on one side: its normal in the (r, y) plane is
            # the tangent (dr, dy) turned to (dy, -dr).
            dr, dy = rb - ra, yb - ya
            part.f(vs, mat, out=(math.cos(a) * dy, -dr, math.sin(a) * dy))


def zrings(part, cx, cy, rx, ry, prof, n=40):
    """A stack of ellipses about a vertical axis: prof [(k, z, mat)], k the scale of (rx, ry);
    each band takes the material of its first ring. k = 0 closes to a point; the top ring is capped."""
    rings = []
    for k, z, _ in prof:
        if k <= 0:
            rings.append([part.v((cx, cy, z))])
        else:
            rings.append([part.v((cx + k * rx * math.cos(2 * math.pi * (i + 0.5) / n),
                                  cy + k * ry * math.sin(2 * math.pi * (i + 0.5) / n), z)) for i in range(n)])
    for i in range(len(prof) - 1):
        r0, r1 = rings[i], rings[i + 1]
        (ka, za, mat), (kb, zb, _) = prof[i], prof[i + 1]
        dk, dz = (kb - ka) * max(rx, ry), zb - za
        for j in range(n):
            jj = (j + 1) % n
            vs = (r0[j], r0[jj], r1[jj], r1[j]) if len(r1) > 1 else (r0[j], r0[jj], r1[0])
            a = 2 * math.pi * (j + 1) / n
            part.f(vs, mat, out=(math.cos(a) * dz, math.sin(a) * dz, -dk))
    if len(rings[0]) > 1:
        part.f(rings[0], prof[0][2], out=(0, 0, -1))
    if len(rings[-1]) > 1:
        part.f(rings[-1], prof[-1][2], out=(0, 0, 1))


def tube(part, path, r, mat, n=8):
    """A capped tube of radius r along a polyline [(x, y, z)] (mitred joints)."""
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized()
        w = u.cross(t).normalized()
        scale = 1.0
        if 0 < i < len(pts) - 1:
            a = (pts[i] - pts[i - 1]).normalized()
            b = (pts[i + 1] - pts[i]).normalized()
            scale = 1 / max(0.5, math.cos(a.angle(b) / 2))
        rings.append([part.v(tuple(p + (u * math.cos(2 * math.pi * k / n) * scale + w * math.sin(2 * math.pi * k / n)) * r))
                      for k in range(n)])
    for i in range(len(rings) - 1):
        c = tuple((pts[i] + pts[i + 1]) / 2)
        for k in range(n):
            kk = (k + 1) % n
            part.f((rings[i][k], rings[i][kk], rings[i + 1][kk], rings[i + 1][k]), mat, away=c)
    part.f(rings[0], mat, out=tuple(pts[0] - pts[1]))
    part.f(rings[-1], mat, out=tuple(pts[-1] - pts[-2]))


# --- the nose cowl ---------------------------------------------------------------------------------

COWL_PLATE = 0.3  # how far the cowl's flank plates stand out of its core
# The cowl's plan half width with its plates (sprite px), fitted to the INNER edge of the sprite's
# nose (D74: the game draws the ink ring itself): a blunt point at row 0.7 widening about a pixel a
# row to row 3.5, then 4.4 to row 5.7 (the sprite's nose, canards at 3.5-4.5 beside it), a step out
# to 5.4 at row 6, then on under the guns to the drum.
_CY = [0.7, 0.95, 1.4, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 5.7, 6.2, 6.8, 7.5, 8.5, 9.5, 10.2, 10.9]
_CW = [0.45, 0.95, 1.5, 2.05, 2.5, 3.25, 3.9, 4.25, 4.38, 4.45, 5.3, 5.45, 5.75, 6.15, 6.42, 6.5, 6.45]
PLAN_C = pchip(_CY, _CW)
CW = pchip(_CY, [max(0.25, w - COWL_PLATE) for w in _CW])
_FY = [0.7, 1.4, 2.3, 3.0, 4.0, 5.5, 7.0, 9.0, 10.9]
CT = pchip(_FY, [0.45, 0.95, 1.45, 1.9, 2.25, 2.65, 2.95, 3.2, 3.3])
CB = pchip(_FY, [0.15, -0.25, -0.65, -0.95, -1.2, -1.5, -1.7, -1.85, -1.9])
DECK = 0.55
SHOULDER = 0.32
FLANK = 0.5
CHINE = 0.1
COWL_Y0, COWL_Y1 = 0.7, 10.9


def cowl_loop(y):
    """Closed section (s = 0 top centre, 1 deck edge, 2 shoulder, 3 flank foot, 4 chine, 5 keel,
    then back up the left side), as the Talon's fuselage."""
    w, t, b = CW(y), CT(y), CB(y)
    h = t - b
    right = [(0.0, t), (DECK * w, t), (w, t - SHOULDER * h), (w, b + FLANK * h), (DECK * w, b + CHINE * h), (0.0, b)]
    pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return pts, (0.0, (t + b) / 2)


def deck_top(y):
    return CT(y) + 0.28


def build_cowl(P):
    L = cowl_loop
    T.loft(P, L, [COWL_Y0, 0.85, 1.05] + frange(1.3, COWL_Y1, 0.8), DARK3, cap0=False)
    # Nose cap all round, its back edge chamfered, and a polished point.
    plate(P, L, 0.85, 2.05, HULL9, d=0.28, ch0=False, ystep=0.3)
    sec = T.Section(L, 0.85)
    hull(P, [sec.at(k, 0.28) for k in range(sec.n)] + [(0.0, 0.66, (CT(0.7) + CB(0.7)) / 2)], EDGE7)
    # Top centre plate round the windshield, and on under the drum.
    plate(P, L, 2.2, 7.4, HULL9, s0=-0.9, s1=0.9, d=0.28, c=0.12)
    plate(P, L, 7.55, 10.75, HULL9, s0=-0.9, s1=0.9, d=0.28, c=0.12)

    def side(sd, _):
        def S(a, b):
            return (a, b) if sd > 0 else (10 - b, 10 - a)
        # Shoulder and flank plates, thick, with a panel break at row 6 under the gun's muzzle.
        for y0, y1 in ((2.2, 5.95), (6.1, 10.75)):
            plate(P, L, y0, y1, HULL9, *S(0.95, 2.55), d=COWL_PLATE, c=0.14)
            plate(P, L, y0, y1, HULL8, *S(2.6, 4.25), d=COWL_PLATE, c=0.12)
        # Reaction-control ports on the nose flanks: dark recessed blocks.
        for y0 in (3.3, 4.15):
            y1 = y0 + 0.55
            pts, _c = cowl_loop(y0 + 0.3)
            zc = (pts[2][1] + pts[3][1]) / 2
            w = CW(y0 + 0.3) + COWL_PLATE
            hull(P, [(sd * x, y, z) for x, y, z in cbox(w - 0.45, w + 0.04, y0, y1, zc - 0.22, zc + 0.22, 0.06)], REC2)
    both(side)
    # Belly plates fore and aft of the nose gear door, and the door itself, proud.
    for y0, y1 in ((2.2, 2.95), (8.55, 10.75)):
        plate(P, L, y0, y1, BELLY, s0=4.3, s1=5.7, d=0.2, c=0.1)
    plate(P, L, 3.1, 8.4, BELLY, s0=4.35, s1=5.65, d=0.34, c=0.12)


def build_canards(D):
    """Small blue canards on the nose flanks (sprite rows 2-3, |x| 3.5-4.5), swept, with a little
    dihedral."""
    def side(sd, X):
        poly = X([(3.0, 2.95), (3.55, 2.0), (4.45, 2.05), (4.45, 3.6), (3.3, 4.0)])
        slab(D, poly, 0.45, 0.78, CANARD, ch=0.08, chb=0.06, top=lambda x, y: (abs(x) - 3.0) * 0.28,
             bot=lambda x, y: (abs(x) - 3.0) * 0.28)
    both(side)


# --- windshield ------------------------------------------------------------------------------------

# Glass edge in plan (sprite px): exactly over the sprite's glass pixels (rows 4-6, three columns,
# |x| <= 1.5), its front a little narrower than its square back.
CAN_Y0, CAN_Y1, CAN_YC, CAN_W = 4.0, 7.0, 5.65, 1.5
CAN_N = 36
GLASS_BASE = 0.12
GLASS_H = 0.62


def canopy_outline(grow=0.0):
    pts = []
    for k in range(CAN_N):
        a = 2 * math.pi * k / CAN_N
        c, s = math.cos(a), math.sin(a)
        if s >= 0:   # front half
            n, b = 2.8, CAN_YC - CAN_Y0
        else:
            n, b = 3.6, CAN_Y1 - CAN_YC
        e = 2 / n
        x = CAN_W * math.copysign(abs(c) ** e, c)
        yv = math.copysign(abs(s) ** e, s)
        if s > 0:
            x *= 1 - 0.12 * yv ** 2
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
            z = deck_top(py) + GLASS_BASE + GLASS_H * (1 - r ** 2.4) ** 0.55
            ring.append(G.v((px, py, z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(CAN_N):
            j = (i + 1) % CAN_N
            G.f((r0[i], r0[j], r1[j], r1[i]), GLASS, away=(0, CAN_YC, 0))
    G.f(rings[-1], GLASS, out=(0, 0, 1))
    low = [G.v((x, y, deck_top(y) - 0.3)) for x, y in C]
    for i in range(CAN_N):
        j = (i + 1) % CAN_N
        G.f((low[i], low[j], rings[0][j], rings[0][i]), GLASS, out=(C[i][0], C[i][1] - CAN_YC, 0))
    # Frame: a sill from the glass edge out over the deck, flat top, chamfered outer edge.
    inner = canopy_outline(-0.05)
    top_out = canopy_outline(0.2)
    ch_out = canopy_outline(0.34)
    fr = []
    for k in range(CAN_N):
        (xi, yi), (xo, yo), (xc, yc) = inner[k], top_out[k], ch_out[k]
        zt = deck_top(yo) + GLASS_BASE + 0.14
        fr.append([F.v((xi, yi, deck_top(yi) - 0.3)), F.v((xi, yi, zt)), F.v((xo, yo, zt)),
                   F.v((xc, yc, zt - 0.14)), F.v((xc, yc, deck_top(yc) - 0.4))])
    for k in range(CAN_N):
        j = (k + 1) % CAN_N
        cx, cy = top_out[k]
        for i in range(4):
            out = ((-cx, -(cy - CAN_YC), 0), (0, 0, 1), (cx * 0.5, (cy - CAN_YC) * 0.5, 1), (cx, cy - CAN_YC, 0))[i]
            F.f((fr[k][i], fr[j][i], fr[j][i + 1], fr[k][i + 1]), FRAME, out=out)


# --- the drum behind the cockpit -------------------------------------------------------------------

DRUM_C, DRUM_RX, DRUM_RY = 10.45, 4.6, 3.2
DRUM_WALL = 4.3


def build_drum(D):
    """A machined drum: an elliptic wall rising out of the cowl, a dark groove and a proud rim band
    at its top, then a dome with a ring seam part-way up and a raised oval cap."""
    zw = DRUM_WALL
    prof = [(1.0, 1.0, HULL8), (1.0, zw, DARK3), (0.965, zw, DARK3), (0.965, zw + 0.23, DARK3),
            (1.015, zw + 0.23, EDGE7), (1.015, zw + 0.57, EDGE7), (0.975, zw + 0.57, HULL8)]
    zd = zw + 0.57
    for a in (12, 24, 36):
        t = math.radians(a)
        prof.append((0.975 * math.cos(t), zd + 1.25 * math.sin(t), HULL8))
    # ring seam: a step in
    k_s, z_s = prof[-1][0], prof[-1][1]
    prof[-1] = (k_s, z_s, DARK3)
    prof += [(k_s - 0.04, z_s, DARK3), (k_s - 0.04, z_s + 0.1, HULL8)]
    for a in (52, 62, 72):
        t = math.radians(a)
        prof.append((0.975 * math.cos(t) - 0.03, zd + 1.25 * math.sin(t) + 0.06, HULL8))
    k_c, z_c = prof[-1][0], prof[-1][1]
    # the cap: a step up and a flat top
    prof[-1] = (k_c, z_c, HULL9)
    prof += [(k_c, z_c + 0.14, HULL9), (k_c - 0.05, z_c + 0.22, HULL9), (0.0, z_c + 0.24, HULL9)]
    zrings(D, 0.0, DRUM_C, DRUM_RX, DRUM_RY, prof, n=44)


# --- chassis, blocks, spine, engines ---------------------------------------------------------------

# The machinery deck under everything (right half and its mirror), seen in the channels between the
# cowl, guns, wings and blocks. Its front stays behind row 6.95 beside the cowl (the sprite's nose is
# alone at rows 5-6), x 8.4 beside the guns (the inner edge), a notch at row 23 (the gap between block
# and wing), its rear ends in the V between the nozzles (x = y - 21, as the spine).
CHASSIS_R = [(0.0, 5.8), (5.0, 5.8), (5.3, 6.95), (8.4, 6.95), (8.4, 10.0), (9.25, 10.0), (9.25, 10.75), (10.4, 10.95),
             (12.95, 17.9), (12.95, 23.0), (11.45, 23.0), (11.45, 24.2), (3.2, 24.2), (0.0, 21.0)]
CHASSIS = CHASSIS_R + mirror(CHASSIS_R[1:-1])[::-1]
DECK_Z = 0.6

# Body block (right): front edge at row 12, a 45-degree front (x = y - 6, the sprite's bevel and
# highlight lines), the outer side at x 12.4, a step in at the rear lip, the inner side at x 2.9 (a
# wide bevel down to the spine).
BLOCK = [(2.9, 12.0), (6.0, 12.0), (12.4, 18.4), (12.4, 20.75), (11.45, 21.7), (11.45, 23.65), (2.9, 23.65)]
BLOCK_INSET = [0.25, 1.0, 0.3, 0.3, 0.3, 0.3, 1.6]
BLOCK_Z0, BLOCK_Z1 = -2.1, 4.6
PLATE_TOP = 4.95
SEAM_X = 7.3   # the lengthwise seam on the block's top
BAY_Y0, BAY_Y1 = 20.65, 22.95

# Wing (right), on the inner edge of the sprite's ink border (D74, docs/agents/OUTLINE-BORDER.md):
# leading edge x = y from the front tip (row 10.75) to the outer corner (row 17.45), outer edge
# x 17.45, trailing edge x = 38 - y, a step out at rows 22.5-23.6 and the tip (x 13.5-14.45) to row
# 25; inboard the edge runs x = 9.4 then x = y - 5 (parallel to the leading edge, the sprite's
# channel) and x 12.55, stepping out to 13.5 behind row 24 (the sprite's gap beside the nozzle).
WING = [(9.4, 10.75), (10.75, 10.75), (17.45, 17.45), (17.45, 20.5), (15.45, 22.5), (15.45, 23.6), (14.45, 24.6),
        (14.45, 25.0), (13.5, 25.0), (13.5, 24.0), (12.55, 24.0), (12.55, 17.55), (9.4, 14.4)]


def wing_top(x, y):
    """Height of the wing's top plates: thickest at the root, thinning outboard."""
    return 2.15 - 0.085 * (abs(x) - 9.5)


def wing_bot(x, y):
    return -0.75 + 0.05 * (abs(x) - 9.5)


def build_chassis(P):
    slab(P, CHASSIS, -1.2, DECK_Z, DECK4, ch=0.2, chb=0.75)


def build_block(P, D):
    def side(sd, X):
        core = X(BLOCK)
        chm = [CORE5, EDGE7, CORE5, CORE5, CORE5, CORE5, CORE5]
        slab(P, core, BLOCK_Z0, BLOCK_Z1, CORE5, ch=BLOCK_INSET, drop=0.7, chb=0.25, chm=chm)
        topp = offset_poly(BLOCK, BLOCK_INSET)   # the core's top face (right side)
        g = 0.08
        # Top plates: inner and outer either side of the lengthwise seam, ending before the intake.
        inner = region(topp, (1, 0, -(SEAM_X - g)), (0, 1, -(BAY_Y0 - 2 * g)), (0, -1, 12.0 + 0.45))
        outer = region(topp, (-1, 0, SEAM_X + g), (0, 1, -(BAY_Y0 - 2 * g)))
        for poly, mat in ((inner, HULL9), (outer, HULL9)):
            slab(P, X(offset_poly(poly, 0.12)), BLOCK_Z1 - 0.3, PLATE_TOP, mat, ch=0.12, chb=0.0)
        # A small raised hatch on the outer plate, and a fairing strip along the front of the inner one.
        slab(P, X([(8.0, 16.4), (8.6, 16.4), (10.4, 18.2), (10.4, 19.6), (8.0, 19.6)]), PLATE_TOP - 0.2, PLATE_TOP + 0.16, HULL8, ch=0.08, chb=0.0)
        # Intake bays: a dark recess either side of a post, louvres across it.
        post = (SEAM_X - 0.42, SEAM_X + 0.42)
        bays = ((4.62, post[0] - 0.1), (post[1] + 0.1, 11.1))
        slab(P, X([(post[0], BAY_Y0), (post[1], BAY_Y0), (post[1], BAY_Y1), (post[0], BAY_Y1)]),
             BLOCK_Z1 - 0.3, PLATE_TOP, HULL9, ch=0.1, chb=0.0)
        for x0, x1 in bays:
            slab(P, X([(x0, BAY_Y0), (x1, BAY_Y0), (x1, BAY_Y1), (x0, BAY_Y1)]), BLOCK_Z1 - 0.5, BLOCK_Z1 - 0.05, REC2, ch=0.04, chb=0.0)
            for yy in frange(BAY_Y0 + 0.42, BAY_Y1 - 0.42, 0.5):
                hull(D, [(sd * x, y, z) for x, y, z in cbox(x0 + 0.05, x1 - 0.05, yy - 0.08, yy + 0.08, BLOCK_Z1 - 0.4, BLOCK_Z1 + 0.12, 0.03)], DARK3)
        # Rear lip behind the intake, sloping down aft.
        slab(P, X([(3.0, BAY_Y1 + 0.12), (11.47, BAY_Y1 + 0.12), (11.47, 23.68), (3.0, 23.68)]), BLOCK_Z1 - 0.4, PLATE_TOP - 0.1,
             EDGE7, ch=0.12, chb=0.0, top=lambda x, y: -0.45 * (y - BAY_Y1))
        # Wide inner bevel plate (the dark wall the sprite shows beside the spine).
        x_in, x_top = BLOCK[0][0], BLOCK[0][0] + BLOCK_INSET[6]
        bev = [(x_in + 0.1, 13.0), (x_top - 0.1, 13.0), (x_top - 0.1, BAY_Y0 - 0.1), (x_in + 0.1, BAY_Y0 - 0.1)]
        z_at = lambda x, y: BLOCK_Z1 - 0.7 * (x_top - abs(x)) / (x_top - x_in)  # noqa: E731
        slab(P, X(bev), -0.5, 0.0, CORE5, ch=0.06, chb=0.0, top=lambda x, y: z_at(x, y) + 0.18)
        # Underside: two gear-door plates under the block, hinge blocks between them.
        under = offset_poly(BLOCK, 0.45)
        for y0, y1 in ((12.6, 17.9), (18.1, 23.1)):
            poly = region(under, (0, -1, y0), (0, 1, -y1))
            slab(P, X(poly), BLOCK_Z0 - 0.28, BLOCK_Z0 + 0.25, BELLY, ch=0.0, chb=0.12)
        for yy in (17.65, 18.35):
            hull(D, [(sd * x, y, z) for x, y, z in cbox(6.0, 9.0, yy - 0.22, yy + 0.22, BLOCK_Z0 - 0.5, BLOCK_Z0 + 0.1, 0.06)], CORE5)
    both(side)


def build_spine(P):
    """The spine between the blocks: a core, a top plate with a V tail, a raised centre strip and
    a dark vent at its rear, a keel underneath."""
    spine = [(-2.75, 13.3), (2.75, 13.3), (2.75, 23.75), (0.0, 21.0), (-2.75, 23.75)]
    slab(P, spine, -1.6, 3.2, CORE5, ch=0.2, chb=0.2)
    top = [(-2.5, 13.55), (2.5, 13.55), (2.5, 23.15), (0.0, 20.65)]
    top = top + [(-2.5, 23.15)]
    slab(P, top, 2.9, 3.55, HULL9, ch=0.14, chb=0.0)
    slab(P, [(-0.95, 13.9), (0.95, 13.9), (0.95, 19.4), (0.0, 20.05), (-0.95, 19.4)], 3.3, 3.9, STRIP, ch=0.14, chb=0.0)
    slab(P, [(-1.5, 20.0), (1.5, 20.0), (1.5, 21.3), (0.0, 20.55), (-1.5, 21.3)], 3.05, 3.43, REC2, ch=0.05, chb=0.0)
    for xx in (-0.75, 0.0, 0.75):
        hull(P, cbox(xx - 0.12, xx + 0.12, 20.15, 20.45 + abs(xx) * 0.8, 3.25, 3.53, 0.03), DARK3)
    # Keel strake under the spine.
    pts = []
    for y, drop in ((12.5, 0.0), (14.0, 0.75), (19.2, 0.75), (20.8, 0.1)):
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.45, -1.3), (0.32, -1.6 - drop), (0.15, -1.7 - drop))]
    hull(P, pts, CORE5)


NOZ_X, NOZ_Z, NOZ_END = 5.5, 0.7, 27.4


def build_engines(P, D):
    def side(sd, X):
        # Housing behind the block, its outboard rear corner cut back (the sprite's tapering rows 24-26).
        slab(P, X([(3.1, 23.45), (11.45, 23.45), (11.45, 23.7), (10.3, 23.7), (8.0, 26.0), (3.1, 26.0)]), -1.85, 3.35, CORE5, ch=0.22, chb=0.22)
        # A dark band and a bright collar where the nozzle leaves the housing.
        # Sized to the inner edge of the sprite's nozzle (rows 25-27, x 3.5-7.5; D74): NR scales the radii.
        cx, cz = sd * NOZ_X, NOZ_Z
        NR = 0.74
        prof = [
            (2.55 * NR, 25.4, NOZ6, False), (2.78 * NR, 25.62, NOZ6, False), (2.78 * NR, 26.3, DARK3, False),
            (2.64 * NR, 26.3, DARK3, False), (2.64 * NR, 26.45, NOZ6, False), (2.69 * NR, 26.45, NOZ6, False),
            (2.32 * NR, NOZ_END, DARK3, False),   # converging petals to the lip
            (1.98 * NR, NOZ_END, DARK3, True),    # lip face, then the bore
            (1.86 * NR, 26.95, REC2, True), (1.5 * NR, 26.5, GLOW, True), (1.0 * NR, 26.3, THROAT, True), (0.0, 26.3, THROAT, True),
        ]
        yrev(D, cx, cz, prof, n=24)
        # A bright trim ring round the nozzle on the housing's rear face.
        yrev(D, cx, cz, [(2.62 * NR, 25.82, EDGE7, 0), (3.0 * NR, 25.95, EDGE7, 0), (3.0 * NR, 26.15, EDGE7, 0),
                         (2.8 * NR, 26.27, EDGE7, 0), (2.6 * NR, 26.27, EDGE7, 0)], n=24)
        # Petal seams: thin dark strips along the converging section.
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            p0 = (cx + 2.71 * NR * math.cos(a), 26.52, cz + 2.71 * NR * math.sin(a))
            p1 = (cx + 2.36 * NR * math.cos(a), NOZ_END - 0.1, cz + 2.36 * NR * math.sin(a))
            tube(D, [p0, p1], 0.07, DARK3, n=4)
    both(side)


# --- guns, wings, channel --------------------------------------------------------------------------

GUN_X, GUN_Z = 8.0, 2.1


def build_guns(D):
    def side(sd, X):
        cx = sd * GUN_X
        prof = [
            (0.0, 5.75, REC2, True), (0.4, 5.25, REC2, True), (0.6, 5.15, RED, False),
            (0.78, 5.5, RED, False), (0.9, 5.9, RED, False), (0.9, 7.35, DARK3, False), (0.84, 7.35, DARK3, False),
            (0.84, 7.5, RED, False), (0.9, 7.5, RED, False), (0.9, 9.15, EDGE7, False), (1.0, 9.27, EDGE7, False),
            (1.0, 10.15, EDGE7, False), (0.85, 10.35, DECK4, False), (0.75, 11.4, DECK4, False), (0.0, 11.5, DECK4, False),
        ]
        yrev(D, cx, GUN_Z, prof, n=18)
        # Mount under the barrel, down to the deck.
        hull(D, [(sd * x, y, z) for x, y, z in cbox(GUN_X - 0.65, GUN_X + 0.65, 7.6, 11.5, DECK_Z - 0.2, GUN_Z - 0.3, 0.15)], DECK4)
        # The red light at its foot (sprite row 12).
        hull(D, [(sd * x, y, z) for x, y, z in cbox(GUN_X - 0.45, GUN_X + 0.45, 11.95, 12.75, DECK_Z - 0.1, DECK_Z + 0.55, 0.15)], LIGHT)
    both(side)


def build_wings(P, D):
    g = 0.08

    def side(sd, X):
        slab(P, X(offset_poly(WING, 0.12)), -0.6, 1.45, DARK3, ch=0.1, chb=0.1,
             top=lambda x, y: wing_top(x, y) - 2.15, bot=lambda x, y: wing_bot(x, y) + 0.6)
        # Plates: the front tip; a leading-edge strip; the blue band between them and the main plate
        # (the sprite's band, x - y in -3..-1, rows 12.7-19); a rear outer plate behind the band; the
        # main plate inboard.
        tip = region(WING, (0, 1, -(12.55 - g)))
        lead = region(WING, (-1, 1, -0.925), (0, -1, 12.55 + g), (0, 1, -(19.05 - g)))
        band = region(WING, (-1, 1, -2.925), (1, -1, 1.075), (0, -1, 12.55 + g), (0, 1, -(19.05 - g)))
        rear = region(WING, (-1, 1, -2.925), (0, -1, 19.05 + g))
        main = region(WING, (1, -1, 3.075), (0, -1, 12.55 + g))
        for poly, mat, lift in ((tip, EDGE7, 0.0), (lead, EDGE7, 0.0), (band, BLUE, -0.12), (rear, HULL8, 0.0),
                                (main, HULL8, 0.0)):
            if len(poly) < 3:
                continue
            slab(P, X(poly), 0.0, 0.0, mat, ch=0.12, chb=0.0,
                 top=lambda x, y, lift=lift: wing_top(x, y) + lift, bot=lambda x, y: wing_top(x, y) - 0.85)
        # Tip rail along the outer edge (the concept's tip prong).
        slab(P, X([(16.5, 17.75), (17.47, 17.75), (17.47, 20.48), (16.5, 20.98)]), 0.0, 0.0, EDGE7, ch=0.15, chb=0.1,
             top=lambda x, y: wing_top(x, y) + 0.45, bot=lambda x, y: wing_bot(x, y) - 0.1)
        # Ventral strake under the wing.
        pts = []
        for y, drop in ((18.0, 0.0), (19.0, 0.8), (23.0, 0.8), (24.3, 0.0)):
            z = wing_bot(14.5, y)
            pts += [(sd * x, y, zz) for x, zz in ((14.0, z + 0.3), (14.0, z - drop), (14.3, z - drop - 0.1),
                                                  (14.6, z - drop), (14.6, z + 0.3))]
        hull(D, pts, CORE5)
    both(side)


def build_channel(D):
    """The machinery in the channel between each wing and block: a pipe run on the deck with
    clamps."""
    def side(sd, X):
        path = [(8.6, 10.6), (8.95, 12.4), (12.45, 17.6), (12.6, 18.2), (12.62, 23.9)]
        z = DECK_Z + 0.28
        tube(D, [(sd * x, y, z) for x, y in path], 0.26, DECK4, n=8)
        for y in (13.6, 15.4, 17.0, 19.5, 21.2, 22.9):
            x = 9.4 + (y - 13.0) * (12.45 - 8.95) / (17.6 - 12.4) if y < 17.6 else 12.6
            hull(D, [(sd * xx, yy, zz) for xx, yy, zz in cbox(x - 0.42, x + 0.42, y - 0.17, y + 0.17, DECK_Z - 0.1, z + 0.36, 0.05)], NOZ6)
        # A second, thinner line along the rear channel where it widens.
        tube(D, [(sd * x, y, z - 0.08) for x, y in ((11.95, 21.2), (11.95, 22.8))], 0.2, NOZ6, n=6)
    both(side)


# --- assembly --------------------------------------------------------------------------------------

def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Sprite px to Blender: X = (x - 0.5) / 12, Y = (14 - y) / 12, Z = z / 12 (a reflection in y).
    m = Matrix(((PX, 0, 0, -0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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
    hullp = Part("nort_hull", smooth_angle=30)
    build_cowl(hullp)
    build_chassis(hullp)
    build_spine(hullp)
    blocks = Part("nort_blocks", smooth_angle=30)
    det = Part("nort_details", smooth_angle=35)
    build_block(blocks, det)
    build_engines(blocks, det)
    wings = Part("nort_wings", smooth_angle=30)
    build_wings(wings, det)
    build_canards(det)
    build_guns(det)
    build_channel(det)
    drum = Part("nort_drum", smooth_angle=40)
    build_drum(drum)
    glass = Part("nort_canopy", smooth_angle=50)
    frame = Part("nort_frame", smooth_angle=30)
    build_canopy(glass, frame)
    objs = [finish(p, mats, coll) for p in (hullp, blocks, wings, det, drum, glass, frame)]
    for o in objs:
        print("nort part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# Materials that get the baked maps (the glass and the glows keep their flat colours).
TEXTURED = (HULL9, HULL8, EDGE7, CORE5, NOZ6, DARK3, DECK4, REC2, BLUE, CANARD, RED, BELLY, STRIP, FRAME)


def bake_maps(obj, out_dir, size=1024, samples=96):
    """As the Talon's (usp_talon.bake_maps): UV the model and bake a grey colour multiplier
    (ambient occlusion at two scales plus a light lift on bevelled edges, tinted by TINT) and a
    roughness/metalness map with Cycles; then Base Color = map x palette colour."""
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
        print("nort: no GPU bake", err)
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
    col_img = bpy.data.images.new("nort_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nort_rm", size // 2, size // 2, alpha=False)
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
    sprite = common.load_sprite(root, NAME)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    # The outline shell is made from a closed copy, taken before hidden faces are culled (remeshing the
    # culled, open hull wraps both sides of every open plate) and kept out of the scene during the bake.
    closed = obj.copy()
    closed.data = obj.data.copy()
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"nort: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glows (src/ui/backdrop.ts) just behind the two nozzles, glTF axes.
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round((sx * NOZ_X - 0.5) * PX, 4), round(NOZ_Z * PX, 4),
                                                          round((NOZ_END + 0.6 - 14) * PX, 4)] for sx in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = out.parent if out else root / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir)
        fmt = "WEBP"
    # The outline shell (D51), as the Talon's (D90): from coarser voxels (0.03) so it bridges the
    # plates' seams, and held just inside the hull. From 0.012 it followed the seams between the white
    # nose and cockpit plates in, and its back faces drew ink cracks across them.
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, voxel=0.03, faces=3000, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"nort: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=(frame["width"], frame["height"]))


if __name__ == "__main__":
    main()
