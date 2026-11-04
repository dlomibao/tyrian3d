"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275), built the way the
USP Talon is (assets/blender/usp_talon.py, DECISIONS.md D50-D53): a hard-surface model that reads
as a real machine from every angle, in the menus and from the tilted game camera.

The sprite is authoritative for the plan outline, the windshield and the colours (D52): seen from
above the model covers frame 271's inner mask, the sprite without its ink border (D74,
docs/agents/OUTLINE-BORDER.md: the game's ink outline stands in for it), rule IoU 1.0 on the grid.
Two straight gun arms, 1.7 px wide (the sprite's one colour column, 5 and 17, plus half its ink),
rows 7-21, run back into a U-band that curves under the pod at 45 degrees to a flat bottom (rows
22-24); a bell-shaped pod (columns 9-13, rows 13-19, a blunt nose) hangs between them, joined in
rows 15-17 by a pivot hub on each arm, a one-row pylon (row 16) and a dark saddle on the pod's flank.
The windshield is the sprite's own glass pixels (rows 13-15: column 11, then 9-11, then 9: a slanted
lens left of the centre line), and each part takes the palette index the sprite uses where it covers
it. The banking frames are the same model rolled by the game, 40 degrees at half bank and 55 at full
(BANK_ROLL, fitted to sprites 267-275 with tools/bank_roll.py, D89): the sprite's banks draw a much
harder roll than the Talon's 17.5 / 35 (the arms close to 4 px apart at full bank). Nothing in the
model is shaped for them; at that roll they measure 0.87-0.88 (half) and 0.78 (full).
The concept (assets/blender/features/concepts/ship-u-ship.jpg) guides the rest: guns with a muzzle
brake, a cooling jacket and a boxy receiver between dark collars, pivot hubs and pylons to the pod,
an armoured brass pod with a deep nozzle in its tail, a broad segmented brass band with a dark inner
rim; underneath, magazines, keel, intake and band ribs.

How it is built (as the Talon; its helpers are imported from usp_talon.py):
- Every part is a low-poly cage in sprite px (x = column - 11.5, the ship's centre line; y = sprite
  row, aft is +y; z up), moved to Blender at the end (X = (x - 0.5) / 12, Y = (14 - y) / 12,
  Z = z / 12: the sprite block's centre is column 12).
- Sections between stations are monotone cubic (pchip), so lofts never swell.
- Dark cores under separate armour plates that stand 0.2-0.3 px proud with 45-degree chamfers, so
  panel lines are real gaps. The U-band is built straight and bent along its centre line.
- Texture: no concept projection (there is no assets/blender/textures/ship-u-ship/maps.json, so
  texture_bake.py never touches it). This script bakes its own two maps with Cycles: ambient
  occlusion with an edge lift (a colour multiplier; on the brass parts slightly cool, TINT, so the
  game's tone mapping does not push them to saturated bronze, D53) and roughness/metalness.
- Palette materials (pal_<index>) so palettes, fades and the hit flash apply; the nozzle glows in
  orange 121/123.
- Exported beside it: the outline shell (common.outline_shell, D51) and `tyrian_engines` (the menu's
  engine glow behind the nozzle).

    Blender --background --factory-startup --python ship-u-ship.py -- [--out path.glb] [--no-bake] [--preview png]
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
import usp_talon as T  # noqa: E402  (shared hard-surface helpers: pchip, fillet, Part, Section, plate, hull, ...)

NAME = "ship-u-ship"
MODEL = f"ships/{NAME}"
PX = 1 / 12
pchip, frange, fillet, Part, Section, plate, hull, cbox = (T.pchip, T.frange, T.fillet, T.Part, T.Section,
                                                         T.plate, T.hull, T.cbox)

# Palette 5 colours used here (reference/models/ship-u-ship/sprite.json), plus the glows.
GLOW_PAL = {121: (231, 97, 12), 123: (243, 174, 36)}

# Material slots.
(GUN_F, GUN_R, GUN_HI, COLLAR, HUB, STRUT, GCORE, DEEP, BAND, BAND_DK, BAND_RIM, POD, POD_SPINE, POD_DK,
 POD_CORE, FRAME, GLASS, GLOW, CORE, MAG) = range(20)

# Palette index per slot: the median index of the sprite pixels each part covers (the outline ring,
# the darkest shading (16-18, the 160s ramp) and the brightest highlights left out; measured on a
# top render with one colour per material): gun barrels 9, receivers 10 (their top rail and row 13's
# sloped front 11), collars 5, pivot hubs 4, pylons 6, the U-band 25 (its centre seam 21), the pod
# 24 with its spine 23 and tail collar 21, the windshield 163 in a 21 frame, the pod's seams 162.
PAL_OF = {GUN_F: 9, GUN_R: 10, GUN_HI: 11, COLLAR: 5, HUB: 4, STRUT: 6, GCORE: 3, DEEP: 2, BAND: 25,
          BAND_DK: 21, BAND_RIM: 6, POD: 24, POD_SPINE: 23, POD_DK: 21, POD_CORE: 162, FRAME: 21,
          GLASS: 163, MAG: 7}
BRASS_SLOTS = {BAND, BAND_DK, POD, POD_SPINE, POD_DK, POD_CORE, FRAME}

METAL = 0.3  # metalness scale (satin, D53)
# The baked colour map's tint on the brass parts (D53): three's Neutral tone mapping takes most from
# the smallest channel (blue) and pushes the lit tan to saturated bronze; this keeps it sandy khaki.
# The steel parts keep a neutral map.
TINT = (0.76, 0.86, 1.0)
# The steel's map is a touch warm: the game's blue sky light otherwise tints the greys blue.
TINT_STEEL = (1.0, 0.97, 0.92)


def materials(sprite):
    def rgb(i):
        return common.srgb(*sprite["colors"][str(i)])

    def pal(slot, tag, metallic, roughness):
        i = PAL_OF[slot]
        return common.material(f"pal_{i}_uship_{tag}", rgb(i), metallic=metallic * METAL, roughness=roughness)

    def glow(i, tag, strength):
        c = common.srgb(*GLOW_PAL[i])
        return common.material(f"pal_{i}_uship_{tag}", c, metallic=0.0, roughness=0.4, emission=c,
                               emission_strength=strength)
    return [
        pal(GUN_F, "barrel", 0.75, 0.36),
        pal(GUN_R, "receiver", 0.7, 0.38),
        pal(GUN_HI, "glacis", 0.75, 0.32),
        pal(COLLAR, "collar", 0.65, 0.42),
        pal(HUB, "hub", 0.65, 0.4),
        pal(STRUT, "pylon", 0.65, 0.42),
        pal(GCORE, "gun_core", 0.5, 0.5),
        pal(DEEP, "recess", 0.3, 0.8),
        pal(BAND, "band", 0.55, 0.4),
        pal(BAND_DK, "band_dark", 0.5, 0.46),
        pal(BAND_RIM, "band_rim", 0.6, 0.44),
        pal(POD, "pod", 0.55, 0.38),
        pal(POD_SPINE, "pod_spine", 0.6, 0.34),
        pal(POD_DK, "pod_collar", 0.5, 0.44),
        pal(POD_CORE, "pod_core", 0.4, 0.6),
        pal(FRAME, "frame", 0.5, 0.38),
        common.material(f"pal_{PAL_OF[GLASS]}_uship_glass", rgb(PAL_OF[GLASS]), metallic=0.0, roughness=0.04),
        glow(121, "engine_glow", 1.6),
        glow(123, "engine_core", 2.2),
        pal(MAG, "magazine", 0.6, 0.45),
    ]


# --- sections ---------------------------------------------------------------------------------

def unit_box(ca, cb, radii, k):
    """A chamfered square (octagon) of half size 1 with filleted corners, from the top flat's left
    end clockwise (seen from behind: +u right, +v up), so angle 0 (straight up) is on the top flat."""
    corners = [(-1 + ca, 1), (1 - ca, 1), (1, 1 - cb), (1, -1 + cb), (1 - ca, -1), (-1 + ca, -1), (-1, -1 + cb),
               (-1, 1 - cb)]
    return fillet(corners, radii, k)


def unit_circle(n=24):
    return [(math.sin(2 * math.pi * (i + 0.5) / n), math.cos(2 * math.pi * (i + 0.5) / n)) for i in range(n)]


def ang_s(unit, deg):
    """Loop parameter (vertex index + fraction) where the ray at `deg` degrees from straight up toward
    +u (negative: toward -u) meets the unit section; negative angles come back below 0 (a plate may
    run across the loop's start)."""
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


def make_loop(unit, cx, cz, rx, rz, sx=1):
    """loopf(y, grow=0) for a section `unit` scaled by rx(y), rz(y) about (cx(y), cz(y)); sx = -1
    mirrors it (u toward -x)."""
    def f(y, grow=0.0):
        X, Z, A, B = cx(y), cz(y), rx(y) + grow, rz(y) + grow
        return [(X + sx * A * u, Z + B * v) for u, v in unit], (X, Z)
    return f


def const(v):
    return lambda y: v


def lathe(part, cx, cz, unit, prof, sx=1):
    """Rings of `unit` scaled (ru, rv) about (cx, cz) at rows y, joined in order; prof = [(ru, rv,
    y, mat, hint)], hint the facing of the band to the next ring: 'out' / 'in' (away from / toward
    the axis), '-y' / '+y'. ru = 0 is a point (a cap)."""
    rings = []
    for ru, rv, y, mat, hint, *own in prof:
        if ru <= 0:
            rings.append([part.v((cx, y, cz))])
        else:
            rings.append([part.v((cx + sx * ru * u, y, cz + rv * v)) for u, v in (own[0] if own else unit)])
    for i in range(len(prof) - 1):
        r0, r1 = rings[i], rings[i + 1]
        mat, hint = prof[i][3], prof[i][4]
        n = max(len(r0), len(r1))
        for k in range(n):
            kk = (k + 1) % n
            if len(r0) == 1:
                vs = (r0[0], r1[k], r1[kk])
            elif len(r1) == 1:
                vs = (r0[k], r0[kk], r1[0])
            else:
                vs = (r0[k], r0[kk], r1[kk], r1[k])
            mx = sum(v.co.x for v in vs) / len(vs)
            mz = sum(v.co.z for v in vs) / len(vs)
            if hint == "out":
                out = (mx - cx, 0.0, mz - cz)
            elif hint == "in":
                out = (cx - mx, 0.0, cz - mz)
            else:
                out = (0.0, -1.0 if hint == "-y" else 1.0, 0.0)
            part.f(vs, mat, out=out)


# --- plan (sprite px; x = column - 11.5) ---------------------------------------------------------

GX = 6.0    # gun arms' centre lines (columns 5 and 17)
# Their half width in plan (D74): the sprite draws each arm one colour px wide inside its ink, so the
# arm keeps 1.7 px (over half its 3 px); beside the pod (rows 14-18) the ink is not free and must stay
# under half covered, so the edge sits 0.35 px into it.
GW = 0.85
G_PLATE = 0.2   # gun plates' height over the core
GA = GW - G_PLATE  # gun core half width
GZ = 0.95   # the arms' half height (a slim square-ish section, not the old 3 px tall box)

# The pod's plan half width (outer, plates included), to the inner edge of the sprite's ink (D74):
# the bell's blunt nose (row 13: columns 10-12) widening into the five-column body of rows 14-19
# (columns 9-13, half width 2.5); the tail stops 0.25 px into row 20, the sprite's ink. Rows 15-17's
# columns 8 and 14 are the pylon saddles on its flanks (build_pod).
_PWY = [12.6, 12.65, 12.75, 13.0, 13.4, 13.8, 14.2, 14.6, 15.0, 19.6, 20.0, 20.25]
_PWV = [0.0, 0.42, 0.72, 1.08, 1.5, 1.92, 2.25, 2.42, 2.48, 2.48, 2.44, 2.38]
PW = pchip(_PWY, _PWV)
# Its half height and centre (elevation, free of the sprite): an egg, tallest at the middle.
_PHY = [12.6, 12.65, 12.75, 13.0, 13.4, 13.8, 14.2, 14.8, 15.6, 19.0, 19.8, 20.25]
PH = pchip(_PHY, [0.0, 0.45, 0.8, 1.2, 1.58, 1.84, 2.0, 2.14, 2.2, 2.2, 2.12, 2.02])
PZ = 0.15
P_PLATE = 0.3
POD_Y0, POD_Y1 = 12.6, 20.25
# Its section: a machined octagon, a broad flat-ish deck on top (so it takes the light as the
# sprite's lit pod does), rounder below.
POD_U = fillet([(-0.7, 1), (0.7, 1), (1, 0.64), (1, -0.55), (0.55, -1), (-0.55, -1), (-1, -0.55), (-1, 0.64)],
               (0.4, 0.4, 0.5, 0.55, 0.5, 0.5, 0.55, 0.5), 3)

# Windshield: the sprite's own glass pixels (rows 13-15: column 11 on row 13, columns 9-11 on row
# 14, column 9 on row 15; 163 and the dark 16), traced as a slanted, swept lens: their stepped
# outline with only its corners eased (Chaikin, three tight passes), the glass pulled 0.12 px in and
# its frame filling those 0.12 px, so glass and frame together are the five pixels (plan area 4.94
# px, IoU 0.95 with them) and nothing reaches past them.
WS_X, WS_Y = -1.0, 14.5
WS_PIX = [(-0.5, 13.0), (0.5, 13.0), (0.5, 15.0), (-1.5, 15.0), (-1.5, 16.0), (-2.5, 16.0), (-2.5, 14.0),
          (-0.5, 14.0)]
WS_OFF = -0.12
WS_FRAME = 0.12  # the frame's plan width, out to the glass pixels' edge


def _chaikin(p, n, r=0.25):
    for _ in range(n):
        q = []
        for i in range(len(p)):
            (ax, ay), (bx, by) = p[i], p[(i + 1) % len(p)]
            q += [(ax + (bx - ax) * r, ay + (by - ay) * r), (ax + (bx - ax) * (1 - r), ay + (by - ay) * (1 - r))]
        p = q
    return p


WS_BASE = _chaikin(WS_PIX, 3, 0.1)
WS_N = len(WS_BASE)

# The U-band's centre line: down each arm, 45 degrees in to a flat bottom (the sprite's diagonal
# steps, rows 21-24), filleted; its half width keeps the sprite's 3 px across rows and columns.
BAND_PATH = [(-GX, 19.35), (-GX, 21.5), (-3.0, 24.5), (3.0, 24.5), (GX, 21.5), (GX, 19.35)]
BAND_R = [None, 2.0, 2.6, 2.6, 2.0, None]
BAND_ZC, BAND_RZ, B_PLATE = -0.15, 0.68, 0.2
BAND_U = unit_box(0.3, 0.36, 0.32, 2)


# --- the U-band's path ------------------------------------------------------------------------

def _band_centre():
    """Dense polyline of the filleted centre line (circular arcs), with arc length."""
    P = BAND_PATH
    pts = [P[0]]
    for i in range(1, len(P) - 1):
        p0, p1, p2 = Vector(P[i - 1]), Vector(P[i]), Vector(P[i + 1])
        d1, d2 = (p0 - p1).normalized(), (p2 - p1).normalized()
        ang = math.acos(max(-1, min(1, d1.dot(d2))))
        r = BAND_R[i]
        t = r / math.tan(ang / 2)
        a, b = p1 + d1 * t, p1 + d2 * t
        bis = (d1 + d2).normalized()
        c = p1 + bis * (r / math.sin(ang / 2))
        a0 = math.atan2(a.y - c.y, a.x - c.x)
        a1 = math.atan2(b.y - c.y, b.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        prev = Vector(pts[-1])
        for k in range(1, 7):  # straight run to the arc's start
            pts.append(tuple(prev.lerp(a, k / 6)))
        for k in range(1, 13):
            th = a0 + da * k / 12
            pts.append((c.x + r * math.cos(th), c.y + r * math.sin(th)))
    prev, end = Vector(pts[-1]), Vector(P[-1])
    for k in range(1, 7):
        pts.append(tuple(prev.lerp(end, k / 6)))
    L = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L.append(L[-1] + math.hypot(x1 - x0, y1 - y0))
    return pts, L


BAND_PTS, BAND_L = _band_centre()
BAND_T = BAND_L[-1]


def band_frame(t):
    """Centre point, unit tangent and outward normal (away from the U's inside) at arc length t."""
    import bisect
    t = max(0.0, min(BAND_T, t))
    i = min(len(BAND_L) - 2, max(0, bisect.bisect_right(BAND_L, t) - 1))
    f = (t - BAND_L[i]) / max(1e-9, BAND_L[i + 1] - BAND_L[i])
    (x0, y0), (x1, y1) = BAND_PTS[i], BAND_PTS[i + 1]
    cx, cy = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
    # Smoothed tangent: average the neighbouring segments.
    j0, j1 = max(0, i - 1), min(len(BAND_PTS) - 1, i + 2)
    tx, ty = BAND_PTS[j1][0] - BAND_PTS[j0][0], BAND_PTS[j1][1] - BAND_PTS[j0][1]
    ln = math.hypot(tx, ty)
    tx, ty = tx / ln, ty / ln
    nx, ny = -ty, tx  # outward (the left arm, going down: -x; the bottom: +y)
    return (cx, cy), (tx, ty), (nx, ny)


def band_w(t):
    """Half width: GW across a row or a column (the arms' width), less on the 45-degree runs."""
    _, (tx, ty), _ = band_frame(t)
    return GW * max(abs(tx), abs(ty))


def band_warp(co):
    (cx, cy), _, (nx, ny) = band_frame(co.y)
    return Vector((cx + nx * co.x, cy + ny * co.x, co.z))


# --- mesh building ----------------------------------------------------------------------------

def finish(part, mats, coll, warp=None):
    part.orient()
    bm = part.bm
    if warp is not None:  # built straight, bent along a path (an orientation-reversing map)
        for v in bm.verts:
            v.co = warp(v.co)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
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


# --- guns -------------------------------------------------------------------------------------

GUN_BOX = unit_box(0.26, 0.3, 0.22, 2)
GUN_RND = unit_circle(20)
MUZ_U = unit_box(0.3, 0.32, 0.3, 2)
MUZ_O = [(u / math.hypot(u, v), v / math.hypot(u, v)) for u, v in MUZ_U]  # a circle, vertex for vertex

# Receiver core: top rises over its sloped front (row 13, the sprite's bright glacis) to a flat deck.
_RTY = [12.3, 12.6, 13.0, 13.5, 13.9, 20.3]
R_TOP = pchip(_RTY, [GZ * f for f in (0.73, 0.75, 0.82, 0.92, 0.96, 0.96)])
R_BOT = -0.94 * GZ


def build_gun(P, D, sx):
    cx = sx * GX
    # Muzzle brake (rows 7-8): a rounded block with a bored front and one port (a gap round the
    # barrel), its front edge chamfered.
    A, B = GW, GZ
    lathe(P, cx, 0.0, MUZ_U, [
        (0.0, 0.0, 7.8, DEEP, "-y"),
        (0.32, 0.32, 7.8, DEEP, "in", MUZ_O),
        (0.32, 0.32, 7.0, GUN_F, "-y", MUZ_O),
        (A - 0.2, B - 0.2, 7.0, GUN_F, "out"),
        (A, B, 7.25, GUN_F, "out"),
        (A, B, 7.45, GUN_F, "+y"),
        (A - 0.24, B - 0.24, 7.45, GCORE, "out"),
        (A - 0.24, B - 0.24, 7.66, GUN_F, "-y"),
        (A, B, 7.66, GUN_F, "out"),
        (A, B, 8.1, GUN_F, "+y"),
        (0.0, 0.0, 8.1, GUN_F, "+y"),
    ], sx=sx)
    # Cooling jacket (rows 8-12): a dark round core under four lengthwise plates (gaps on the
    # diagonals) in two lengths, a raised band between them.
    J = make_loop(GUN_RND, const(cx), const(0.0), const(GW - 0.19), const(GZ - 0.19), sx)
    T.loft(P, J, frange(8.0, 12.9, 0.7), GCORE)
    for y0, y1 in ((8.12, 10.05), (10.6, 12.62)):
        for a, b in ((48, 132), (138, 222), (228, 312)):
            plate(P, J, y0, y1, GUN_F, s0=ang_s(GUN_RND, a), s1=ang_s(GUN_RND, b), d=0.17, c=0.06, ystep=0.7)
        # The top plate in three, two short vent slots across it.
        n = 3
        for k in range(n):
            a = y0 + (y1 - y0) * k / n + (0.08 if k else 0)
            b = y0 + (y1 - y0) * (k + 1) / n - (0.08 if k < n - 1 else 0)
            plate(P, J, a, b, GUN_F, s0=ang_s(GUN_RND, -42), s1=ang_s(GUN_RND, 42), d=0.17, c=0.06, ystep=0.7)
    plate(P, J, 10.15, 10.5, GUN_F, d=0.19, c=0.06, ystep=1)  # band ring
    # Receiver (rows 12.6-20): core with a sloped front, a dark collar each end (rows 14 and 19),
    # deck, flank and belly plates between; vent gaps in the outboard flank plates.
    R = make_loop(GUN_BOX, const(cx), lambda y: (R_TOP(y) + R_BOT) / 2, const(GA), lambda y: (R_TOP(y) - R_BOT) / 2, sx)
    T.loft(P, R, [12.45] + frange(12.6, 14.0, 0.35)[1:] + frange(14.0, 20.4, 0.8)[1:], GCORE)

    def S(a, b, gap=0.0):
        return dict(s0=ang_s(GUN_BOX, a) + gap, s1=ang_s(GUN_BOX, b) - gap)
    plate(P, R, 12.66, 13.8, GUN_HI, **S(-58, 58), d=G_PLATE, c=0.08, ystep=0.35)  # glacis
    for a, b in ((62, 128), (232, 298)):
        plate(P, R, 12.66, 13.8, GUN_R, **S(a, b), d=G_PLATE, c=0.1, ystep=0.5)
    for y0, y1 in ((13.92, 14.95), (19.0, 20.05)):
        plate(P, R, y0, y1, COLLAR, d=0.23, c=0.09, ystep=0.5)
    plate(P, R, 15.08, 18.87, GUN_R, **S(-58, 58), d=G_PLATE, c=0.1, ystep=0.6)
    for y0, y1 in ((15.08, 16.0), (16.18, 16.62), (16.8, 17.24), (17.42, 18.87)):
        plate(P, R, y0, y1, GUN_R, **S(62, 128), d=G_PLATE, c=0.08, ystep=0.6)
    plate(P, R, 15.08, 18.87, GUN_R, **S(232, 298), d=G_PLATE, c=0.1, ystep=0.6)
    plate(P, R, 15.08, 18.87, MAG, **S(132, 228), d=0.16, c=0.08, ystep=0.8)
    # Top rail on the deck, with three cross notches.
    top = R_TOP(16) + G_PLATE
    for y0, y1 in ((15.35, 16.2), (16.35, 17.2), (17.35, 18.6)):
        hull(D, cbox(cx - 0.36, cx + 0.36, y0, y1, top - 0.1, top + 0.24, 0.1), GUN_HI)
    # Magazine under the receiver.
    hull(D, cbox(cx - 0.6, cx + 0.6, 15.5, 18.2, R_BOT - 0.75, R_BOT + 0.1, 0.16), MAG)
    hull(D, cbox(cx - 0.42, cx + 0.42, 15.8, 17.9, R_BOT - 0.86, R_BOT - 0.68, 0.06), GUN_R)
    # Pivot hub on the inner flank (rows 15-17, column 6 of the sprite's inner mask), an oval slotted
    # disc, and the pylon to the pod: one px wide in plan (row 16; column 7's rows 15 and 17 are ink).
    xi = cx - sx * GW  # inner face
    zc = 0.1
    ring = [(math.cos(2 * math.pi * k / 16), math.sin(2 * math.pi * k / 16)) for k in range(16)]
    pts = []
    for dx, ry, rz in ((0.36, 1.3, 0.9), (0.2, 1.4, 1.0), (-0.3, 1.4, 1.0), (-0.42, 1.25, 0.86)):
        pts += [(xi + sx * dx, 16.5 + ry * c, zc + rz * s) for c, s in ring]
    hull(D, pts, HUB)
    hull(D, [(xi + sx * x, y, z) for x, y, z in cbox(0.3, 0.42, 16.42, 16.58, zc - 0.62, zc + 0.62, 0.03)], DEEP)
    pts = []
    for x in (xi + sx * 0.2, 2.9 * sx):
        pts += [(x, y, z) for y, z in ((15.8, zc - 0.25), (15.8, zc + 0.15), (15.95, zc + 0.35), (17.05, zc + 0.35),
                                       (17.2, zc + 0.15), (17.2, zc - 0.25), (17.05, zc - 0.45), (15.95, zc - 0.45))]
    hull(D, pts, STRUT)
    # A lower brace under it to the pod's belly.
    pts = []
    for x, y, z in ((xi + sx * 0.1, 16.5, zc - 0.55), (2.3 * sx, 16.5, zc - 1.45)):
        pts += [(x, y + dy, z + dz) for dy in (-0.3, 0.3) for dz in (-0.24, 0.24)]
    hull(D, pts, STRUT)


# --- pod ----------------------------------------------------------------------------------------

def pod_loop(y, grow=0.0):
    return make_loop(POD_U, const(0.0), const(PZ), lambda y: max(0.02, PW(y) - P_PLATE),
                     lambda y: max(0.02, PH(y) - P_PLATE))(y, grow)


def pod_top(x, y, off=P_PLATE):
    """Height of the pod's plated upper surface at plan point (x, y)."""
    sec = Section(pod_loop, y)
    pts = [(px + nx * off, pz + nz * off) for (px, pz), (nx, nz) in zip(sec.pts, sec.vn)]
    best = None
    for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]):
        if (x0 - x) * (x1 - x) <= 0 and abs(x1 - x0) > 1e-9:
            z = z0 + (z1 - z0) * (x - x0) / (x1 - x0)
            best = z if best is None else max(best, z)
    return best if best is not None else PZ


def build_pod(P, D):
    ys = [POD_Y0, 12.65, 12.72, 12.8, 12.9, 13.05, 13.25, 13.5, 13.8, 14.2, 14.6] + frange(15.0, POD_Y1, 0.7)
    T.loft(P, pod_loop, ys, POD_CORE, cap1=False)

    def S(a, b, gap=0.0):
        return dict(s0=ang_s(POD_U, a) + gap, s1=ang_s(POD_U, b) - gap)
    # Nose cowl: four armour petals over the blunt nose, gaps on the diagonals.
    for a, b in ((-43, 43), (47, 133), (137, 223), (227, 313)):
        plate(P, pod_loop, 13.05, 14.6, POD, **S(a, b), d=0.26, c=0.1, ystep=0.3)
    # Their tip: a nose cap over the petals' front edges.
    pts = [(0.0, POD_Y0 - 0.01, PZ)]
    for y, off in ((12.65, 0.06), (12.72, 0.1), (12.8, 0.13), (12.9, 0.16), (13.05, 0.2)):
        sec = Section(pod_loop, y)
        pts += [sec.at(k, off) for k in range(sec.n)]
    hull(P, pts, POD_SPINE)
    # Body: a raised spine strip down the top (the sprite's centre columns), plates either side with
    # lengthwise seams (the dark one right of the spine is the sprite's column 12), flanks, belly.
    plate(P, pod_loop, 14.75, 19.62, POD_SPINE, **S(-21, 21), d=0.42, c=0.14, ystep=0.7)
    for a, b, mat in ((25, 64, POD), (68, 118, POD), (122, 160, POD_DK)):
        plate(P, pod_loop, 14.75, 19.62, mat, **S(a, b), d=P_PLATE, c=0.12, ystep=0.7)
        plate(P, pod_loop, 14.75, 19.62, mat, **S(-b, -a), d=P_PLATE, c=0.12, ystep=0.7)
    plate(P, pod_loop, 14.75, 19.62, POD_DK, **S(164, 196), d=0.24, c=0.1, ystep=0.8)
    # Raised access hatches on the top plates, behind the windshield.
    for a, b in ((31, 58), (-58, -31)):
        plate(P, pod_loop, 16.6, 18.9, POD, **S(a, b), d=P_PLATE + 0.14, c=0.08, ystep=0.8)
    # Tail collar, a ring all round.
    plate(P, pod_loop, 19.76, POD_Y1 + 0.03, POD_DK, d=0.3, c=0.12, ystep=0.4)
    # Aft bulkhead: a chamfered ring from the core's end in to the nozzle's collar.
    rx, rz = PW(POD_Y1) - P_PLATE, PH(POD_Y1) - P_PLATE
    hole = [(u / math.hypot(u, v), v / math.hypot(u, v)) for u, v in POD_U]
    lathe(P, 0.0, PZ, POD_U, [
        (rx, rz, POD_Y1 - 0.02, POD_DK, "+y"),
        (rx * 0.9, rz * 0.9, POD_Y1 + 0.02, POD_DK, "+y"),
        (rx * 0.86, rz * 0.86, POD_Y1 + 0.02, POD_DK, "+y"),
        (1.5, 1.5, POD_Y1 + 0.02, POD_DK, "in", hole),
        (1.5, 1.5, POD_Y1 - 0.5, POD_DK, "in", hole),
    ])
    # Nozzle: collar, bell, a deep glowing throat, sunk into the tail (row 20 is the sprite's ink).
    NZ = PZ
    C = unit_circle(20)
    lathe(D, 0.0, NZ, C, [
        (1.45, 1.45, POD_Y1 - 0.5, GCORE, "out"),
        (1.45, 1.45, POD_Y1 + 0.04, GCORE, "+y"),
        (1.12, 1.12, POD_Y1 + 0.04, GCORE, "in"),
        (0.95, 0.95, POD_Y1 - 0.35, GLOW, "in"),
        (0.72, 0.72, POD_Y1 - 0.75, CORE, "+y"),
        (0.0, 0.0, POD_Y1 - 0.75, CORE, "+y"),
    ])
    # Pylon saddles on the flanks (rows 15-17, the sprite's columns 8 and 14): dark clamps the
    # pylons run into, chamfered, the pod's top left clear.
    for sx in (-1, 1):
        hull(D, [(sx * x, y, z) for x, y, z in cbox(2.05, 3.25, 15.1, 17.9, PZ - 1.15, PZ + 0.85, 0.22)], GCORE)
        hull(D, [(sx * x, y, z) for x, y, z in cbox(3.15, 3.3, 15.6, 17.4, PZ - 0.65, PZ + 0.45, 0.04)], COLLAR)
    # Underneath: a keel, an intake under the nose, a gear door.
    pts = []
    for y in (13.4, 14.4, 18.6, 19.8):
        b = PZ - PH(y) + 0.1
        drop = 0.4 if 14.0 < y < 19.0 else 0.05
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.45, b + 0.3), (0.32, b - drop), (0.14, b - drop - 0.08))]
    hull(D, pts, GCORE)
    for sx in (-1, 1):
        hull(D, cbox(sx * 1.0 - 0.55, sx * 1.0 + 0.55, 13.6, 15.4, PZ - PH(14.5) - 0.1, PZ - PH(14.5) + 0.7, 0.18), POD_DK)
        hull(D, cbox(sx * 1.0 - 0.38, sx * 1.0 + 0.38, 13.55, 13.75, PZ - PH(14.5) + 0.0, PZ - PH(14.5) + 0.55, 0.04), DEEP)
    # Small orange thruster ports in the tail collar's flanks (the concept's glows).
    for sx in (-1, 1):
        x = sx * (PW(19.8) + 0.02)
        hull(D, [(x - sx * dx, y, z) for dx, y, z in cbox(0.0, 0.2, 19.55, 20.05, PZ - 0.25, PZ + 0.25, 0.05)], GLOW)


def ws_outline(grow=0.0):
    """The windshield's edge in plan: the glass pixels' rounded outline (WS_BASE) moved out by
    WS_OFF + grow along its vertex normals."""
    p, n, d = WS_BASE, WS_N, WS_OFF + grow
    area = sum(p[i][0] * p[(i + 1) % n][1] - p[(i + 1) % n][0] * p[i][1] for i in range(n))
    sg = 1 if area > 0 else -1
    out = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = p[i - 1], p[i], p[(i + 1) % n]
        n1 = (sg * (by - ay), -sg * (bx - ax))
        n2 = (sg * (cy - by), -sg * (cx - bx))
        l1, l2 = math.hypot(*n1), math.hypot(*n2)
        n1, n2 = (n1[0] / l1, n1[1] / l1), (n2[0] / l2, n2[1] / l2)
        nx, ny = n1[0] + n2[0], n1[1] + n2[1]
        ln = math.hypot(nx, ny)
        cs = max(0.35, (n1[0] * n2[0] + n1[1] * n2[1] + 1) / 2) ** 0.5
        out.append((bx + nx / ln * d / cs, by + ny / ln * d / cs))
    return out


def build_windshield(G, F):
    C = ws_outline()
    cx, cy = WS_X, WS_Y
    base, h = 0.16, 0.32
    K = 7
    rings = []
    for k in range(K + 1):
        r = 1 - k / K * 0.96
        ring = []
        for x, y in C:
            px, py = cx + (x - cx) * r, cy + (y - cy) * r
            ring.append(G.v((px, py, pod_top(px, py) + base + h * (1 - r ** 2.4) ** 0.5)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(WS_N):
            j = (i + 1) % WS_N
            G.f((r0[i], r0[j], r1[j], r1[i]), GLASS, out=(0, 0, 1))
    G.f(rings[-1], GLASS, out=(0, 0, 1))
    low = [G.v((x, y, pod_top(x, y) - 0.25)) for x, y in C]
    for i in range(WS_N):
        j = (i + 1) % WS_N
        G.f((low[i], low[j], rings[0][j], rings[0][i]), GLASS, out=(C[i][0] - cx, C[i][1] - cy, 0))
    # Frame: a sill from the glass edge out over the plates, flat top, chamfered outer edge.
    inner, top_out, ch_out = ws_outline(0.0), ws_outline(WS_FRAME * 0.6), ws_outline(WS_FRAME)
    rings = []
    for k in range(WS_N):
        (xi, yi), (xo, yo), (xc, yc) = inner[k], top_out[k], ch_out[k]
        zt = max(pod_top(xi, yi), pod_top(xo, yo)) + base + 0.1
        rings.append([F.v((xi, yi, pod_top(xi, yi) - 0.2)), F.v((xi, yi, zt)), F.v((xo, yo, zt)),
                      F.v((xc, yc, zt - 0.12)), F.v((xc, yc, pod_top(xc, yc) - 0.3))])
    for k in range(WS_N):
        j = (k + 1) % WS_N
        ox, oy = top_out[k][0] - cx, top_out[k][1] - cy
        for i in range(4):
            out = [(-ox, -oy, 0), (0, 0, 1), (ox * 0.5, oy * 0.5, 1), (ox, oy, 0)][i]
            F.f((rings[k][i], rings[j][i], rings[j][i + 1], rings[k][i + 1]), FRAME, out=out)


# --- U-band (built straight: x = across, outward +; y = arc length t; then bent) -----------------

def band_loop(t, grow=0.0):
    w = band_w(t) - B_PLATE
    return [(w * u + grow * u, BAND_ZC + (BAND_RZ + grow) * v) for u, v in BAND_U], (0.0, BAND_ZC)


def build_band(B):
    T.loft(B, band_loop, frange(0.0, BAND_T, 0.45), BAND_RIM)
    tm = BAND_T / 2
    # The diagonal runs' middles: the plates are split there and at the bottom centre (the sprite's
    # dark seam pixel, row 24 column 11).
    td = [BAND_L[i] for i, (x, y) in enumerate(BAND_PTS) if abs(abs(x) - 4.5) < 0.6 and 22.5 < y < 23.6]
    t1 = sum(t for t in td if t < tm) / max(1, len([t for t in td if t < tm]))
    cuts = [0.15, t1, tm, BAND_T - t1, BAND_T - 0.15]

    def S(a, b):
        return dict(s0=ang_s(BAND_U, a), s1=ang_s(BAND_U, b))
    for k in range(4):
        y0 = cuts[k] + (0.0 if k == 0 else 0.09)
        y1 = cuts[k + 1] - (0.0 if k == 3 else 0.09)
        plate(B, band_loop, y0, y1, BAND, **S(-62, 62), d=B_PLATE, c=0.12, ystep=0.42, ch0=k > 0, ch1=k < 3)
        plate(B, band_loop, y0, y1, BAND, **S(66, 128), d=B_PLATE, c=0.1, ystep=0.42, ch0=k > 0, ch1=k < 3)
    # The seam plate at the bottom centre: a darker clamp across the band.
    plate(B, band_loop, tm - 0.3, tm + 0.3, BAND_DK, **S(-66, 128), d=B_PLATE + 0.06, c=0.08, ystep=0.3)
    for t in (t1, BAND_T - t1):  # and thinner clamps over the other two seams
        plate(B, band_loop, t - 0.2, t + 0.2, BAND_DK, **S(-66, 128), d=B_PLATE + 0.04, c=0.07, ystep=0.4)
    # Belly and the dark inner rim, continuous.
    plate(B, band_loop, 0.2, BAND_T - 0.2, BAND_DK, **S(132, 228), d=0.18, c=0.08, ystep=0.5)
    plate(B, band_loop, 0.2, BAND_T - 0.2, BAND_RIM, **S(232, 296), d=0.16, c=0.06, ystep=0.5)
    # Ribs under the band.
    for t in frange(1.4, BAND_T - 1.4, 1.25):
        w = band_w(t) - 0.35
        hull(B, cbox(-w, w, t - 0.16, t + 0.16, BAND_ZC - BAND_RZ - 0.45, BAND_ZC - BAND_RZ + 0.1, 0.06), GCORE)


# --- assembly -------------------------------------------------------------------------------------

def build(coll, mats):
    P = Part("uship_guns", smooth_angle=34)
    D = Part("uship_details", smooth_angle=35)
    for sx in (-1, 1):
        build_gun(P, D, sx)
    Q = Part("uship_pod", smooth_angle=34)
    build_pod(Q, D)
    G = Part("uship_glass", smooth_angle=60)
    F = Part("uship_frame", smooth_angle=30)
    build_windshield(G, F)
    B = Part("uship_band", smooth_angle=34)
    build_band(B)
    objs = [finish(p, mats, coll) for p in (P, D, Q, G, F)] + [finish(B, mats, coll, warp=band_warp)]
    for o in objs:
        print("u-ship part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = tuple(i for i in range(20) if i not in (GLASS, GLOW, CORE))


def bake_maps(obj, out_dir, size=1024, samples=96):
    """As usp_talon.bake_maps: UV (Smart UV Project) and bake a grey colour multiplier (occlusion at
    two scales plus a lift on bevelled edges; tinted on the brass parts) and a roughness/metalness
    map, then wire them in: Base Color = map x palette colour."""
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
        print("u-ship: no GPU bake", err)
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

    col_img = bpy.data.images.new("uship_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("uship_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(slot, m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
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
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
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
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = TINT if slot in BRASS_SLOTS else TINT_STEEL
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, tint[k]), comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
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
        tmps = {m.name: bake_shader(i, m, mode) for i, m in enumerate(mats)}
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


# The game's roll at bank steps 1 and 2, degrees (spriteModels bank.roll, D89).
BANK_ROLL = [40, 55]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    objs = build(coll, mats)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"u-ship: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glow (src/ui/backdrop.ts): just behind the nozzle, glTF axes
    # (x, y up, z aft), orange (palette 121).
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round(-0.5 * PX, 4), round((PZ - 0.1) * PX, 4),
                                                         round((POD_Y1 + 0.4 - 14) * PX, 4)]]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="uship_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, faces=1500)
    print(f"u-ship: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, common.with_bank_roll(sprite["sprites"], BANK_ROLL),
                                   image_format=fmt)
    if "--preview" in argv:
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
