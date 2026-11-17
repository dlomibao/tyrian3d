"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275), built the way the
USP Talon is (assets/blender/usp_talon.py, DECISIONS.md D50-D53): a hard-surface model that reads
as a real machine from every angle, in the menus, the viewer and from the tilted game camera.

What it is: two slim guns joined behind by a brass yoke bent into a U, a small pointed brass pod
with a dark glass nose slung between them on one strut a side.

The sprite is authoritative for the plan outline, the feature placement and the colours (D52): seen
from above the model covers frame 271's inner mask, the sprite without its ink border (D74,
docs/agents/OUTLINE-BORDER.md: the game's ink outline stands in for it). Each part takes the palette
index the sprite uses where it covers it; the sprite's light and dark sides are its lighting and are
left to the game's lights on the model's own form (art rule 2): nothing here is painted in tone
bands (DECISIONS.md D237, which takes back D228's).

- Guns (columns 5 and 17, rows 8-19; the sprite's one colour pixel between its ink): 1.5 px wide
  (D74's rule 3: a thin part keeps half its 3 px; the old model's were 1.7) and 2 px deep, as a gun
  is: the banking frames, the only ones that show their depth, draw them 2 and 3 px wide. The
  section has a narrow flat on top and steep shoulders, so the bright line seen from above is about
  1 px. A muzzle brake, a barrel jacket under six cooling fins (index 9), a polished breech ring
  (11, the sprite's bright row 13), a dark neck (5, row 14), a receiver (10, rows 15-17) with a
  sight rail and vented flank, a second ring (row 18) and the dark socket the yoke runs into (row 19).
- Yoke (rows 20-24): a brass rail as slim as the guns (1.5 px; the old tube was 1.7), in sleeves
  (25) on a dark core, its broad bevel turned outward so the limb that faces the sun is the lighter
  one, as the sprite draws it; a dark clamp (21) between two polished flanges (28) in the middle
  of the bottom run (the sprite's 28 21 28), thin clamps on the corners.
- Pod (columns 9-13, rows 13-19): a low shell with an ogive nose, 2.9 px tall (the old barrel was
  4.4), its nose down and its tail drawn in: dark glass over the nose (163, rows 13-15) in a brass
  hoop, tan plates (24) on a dark core with real seams, a polished cream spine panel (28) flush
  with them, louvres on the shoulders, a brown tail collar (22) round a dark, unlit exhaust. The sprite has no orange pixel,
  so nothing glows; `tyrian_engines` places the menus' glow.
- Struts (row 16): a pivot hub on each gun's inner flank (4), a pylon (6), a dark saddle on the
  pod's flank (the sprite's ink blocks, columns 6, 8, 14 and 16, which the inner mask keeps).
- Underneath: a magazine under each receiver and the pod's keel, plain.

The banking frames are the same model rolled and shifted by the game (BANK_ROLL, BANK_SHIFT,
fitted to sprites 267-275 with tools/bank_roll.py --fit, D93). Nothing is shaped for them.

How it is built (as the Talon; its helpers are imported from usp_talon.py):
- Every part is a low-poly cage in sprite px (x = column - 11.5, the ship's centre line; y = sprite
  row, aft is +y; z up), moved to Blender at the end (X = (x - 0.5) / 12, Y = (14 - y) / 12,
  Z = z / 12: the sprite block's centre is column 12).
- Sections between stations are monotone cubic (pchip), so lofts never swell.
- Dark cores under separate plates that stand 0.2-0.3 px proud with 45-degree chamfers, so panel
  lines are real gaps. The yoke is built straight and bent along its centre line.
- Texture: no concept projection (maps.json says "bake": "model"). This script bakes its own two
  maps with Cycles: ambient occlusion with an edge lift (a colour multiplier, a touch cool on the
  brass and warm on the steel, D53) and roughness/metalness.
- Palette materials (pal_<index>) so palettes, fades and the hit flash apply.
- Exported beside it: the outline shell (common.outline_shell, D51, D90) and `tyrian_engines`.

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

# Material slots.
(GUN_F, GUN_R, GUN_HI, COLLAR, HUB, STRUT, GCORE, DEEP, BAND, BAND_HI, BAND_DK, BAND_CORE, POD, POD_HI, POD_DK,
 POD_CORE, FRAME, NOSE, GLASS, MAG) = range(20)

# Palette index per slot (palette 5, reference/models/ship-u-ship/sprite.json): the index of the
# sprite pixels each part covers, the ink ring left out. Guns: barrel 9, receiver 10, the two bright
# rings 11, necks 5, hubs 4, pylons 6. Yoke: 25 (the median of its 15 pixels, 20-28), its flanges 28
# and clamps 21 (row 24: 28 21 28). Pod: 24 (the median of rows 16-19 without the bright and the dark
# column: 22-26), the
# spine 28 (column 10: 28, 29), the tail collar and lower plates 22, its seams 162 (column 12), the
# glass 163 (rows 13-15) in a 21 hoop, the nose cap 23 (row 13).
PAL_OF = {GUN_F: 9, GUN_R: 10, GUN_HI: 11, COLLAR: 5, HUB: 4, STRUT: 6, GCORE: 3, DEEP: 2, BAND: 25,
          BAND_HI: 28, BAND_DK: 21, BAND_CORE: 20, POD: 24, POD_HI: 28, POD_DK: 22, POD_CORE: 162, FRAME: 21,
          NOSE: 23, GLASS: 163, MAG: 7}
BRASS_SLOTS = {BAND, BAND_HI, BAND_DK, BAND_CORE, POD, POD_HI, POD_DK, POD_CORE, FRAME, NOSE}

METAL = 0.3  # metalness scale (satin, D53)
# The baked colour map's tint (D53). Brass: three's Neutral tone mapping takes most from the smallest
# channel (blue) and pushes lit tan toward saturated bronze; a slightly cool map keeps it the
# sprite's sandy tan (milder than the 0.76 / 0.86 / 1.0 before D228: measured in game, DECISIONS.md
# D237). Steel: a touch warm against the game's blue sky light.
TINT = (0.9, 0.94, 1.0)
TINT_STEEL = (1.0, 0.97, 0.92)


def materials(sprite):
    def rgb(i):
        return common.srgb(*sprite["colors"][str(i)])

    def pal(slot, tag, metallic, roughness):
        i = PAL_OF[slot]
        return common.material(f"pal_{i}_uship_{tag}", rgb(i), metallic=metallic * METAL, roughness=roughness)
    return [
        pal(GUN_F, "barrel", 0.75, 0.38),
        pal(GUN_R, "receiver", 0.7, 0.38),
        pal(GUN_HI, "ring", 0.75, 0.34),
        pal(COLLAR, "neck", 0.65, 0.44),
        pal(HUB, "hub", 0.65, 0.4),
        pal(STRUT, "pylon", 0.65, 0.42),
        pal(GCORE, "gun_core", 0.5, 0.5),
        pal(DEEP, "recess", 0.3, 0.8),
        pal(BAND, "yoke", 0.6, 0.36),
        pal(BAND_HI, "yoke_flange", 0.8, 0.26),
        pal(BAND_DK, "yoke_clamp", 0.5, 0.46),
        pal(BAND_CORE, "yoke_core", 0.4, 0.6),
        pal(POD, "pod", 0.6, 0.34),
        pal(POD_HI, "pod_spine", 0.8, 0.2),
        pal(POD_DK, "pod_collar", 0.5, 0.44),
        pal(POD_CORE, "pod_core", 0.4, 0.6),
        pal(FRAME, "frame", 0.5, 0.38),
        pal(NOSE, "nose", 0.6, 0.34),
        common.material(f"pal_{PAL_OF[GLASS]}_uship_glass", rgb(PAL_OF[GLASS]), metallic=0.0, roughness=0.04),
        pal(MAG, "magazine", 0.6, 0.45),
    ]


# --- sections ---------------------------------------------------------------------------------

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

GX = 6.0    # the guns' centre lines (columns 5 and 17)
# Their half width in plan (D74's rule 3): the sprite draws each gun one colour px wide inside its
# ink, 3 px in all, and a thin part keeps half of that: 1.5 px, a quarter of a pixel into the ink
# each side. The old model's 1.7 px tubes read fat (D228's diagnosis).
GW = 0.75
# Their half height: deeper than wide, as a gun is. The banking frames, the only ones that show the
# guns' depth, draw them 2 and 3 px wide (D228 read 2.5-3 px of depth from them; 2 px keeps the gun
# a gun in the side view and passes D93's bars).
GZ = 1.0
G_PLATE = 0.18  # the receiver's plates stand this far off its core
FIN = 0.25  # the barrel's cooling fins stand this far off its jacket

# The pod's plan half width (outer, plates included), to the inner edge of the sprite's ink (D74):
# a pointed nose (an ogive: three columns in row 13, columns 10-12) widening into the five-column
# body of rows 14-19 (columns 9-13, half width 2.5); the tail stops 0.25 px into row 20, the sprite's ink. Rows
# 15-17's columns 8 and 14 are the strut saddles on its flanks (build_pod).
_PWY = [12.6, 12.8, 13.0, 13.25, 13.5, 13.75, 14.0, 14.3, 14.7, 19.6, 20.0, 20.25]
_PWV = [0.0, 0.42, 0.8, 1.12, 1.5, 1.92, 2.26, 2.44, 2.48, 2.48, 2.44, 2.38]
PW = pchip(_PWY, _PWV)
# Its elevation is free of the sprite: low and pointed (2.9 px tall on a 5 px plan; the old barrel
# was 4.4), the nose down on the roll axis, the crown over rows 16-17, the top drawn down to a
# short stern so no tall face turns to the game's camera.
_PHY = [12.6, 12.65, 12.75, 13.0, 13.4, 13.8, 14.2, 14.8, 15.6, 16.6, 18.0, 19.0, 19.8, 20.25]
PH = pchip(_PHY, [0.0, 0.26, 0.42, 0.62, 0.86, 1.02, 1.14, 1.27, 1.39, 1.45, 1.4, 1.26, 1.02, 0.84])
PZ = pchip([12.6, 13.4, 14.4, 15.6, 18.6, 20.25], [0.0, 0.07, 0.19, 0.3, 0.3, 0.2])  # its centre line's height
P_PLATE = 0.26
POD_Y0, POD_Y1 = 12.6, 20.25
# Its section: a rounded octagon, a little flatter underneath.
POD_U = fillet([(-0.5, 1), (0.5, 1), (1, 0.45), (1, -0.4), (0.55, -1), (-0.55, -1), (-1, -0.4), (-1, 0.45)],
               (0.42, 0.42, 0.5, 0.5, 0.45, 0.45, 0.5, 0.5), 3)
GLASS_Y0, GLASS_Y1 = 13.18, 15.55   # the glass nose: the sprite's dark rows 13-15

# The yoke's centre line: down each gun, 45 degrees in to a flat bottom (the sprite's diagonal
# steps, rows 21-24), filleted.
BAND_PATH = [(-GX, 19.35), (-GX, 21.5), (-3.0, 24.5), (3.0, 24.5), (GX, 21.5), (GX, 19.35)]
BAND_R = [None, 2.0, 2.6, 2.6, 2.0, None]
BAND_ZC, BAND_RZ, B_PLATE = 0.0, 0.6, 0.18
# Its section (u outward from the U, v up): a narrow top flat, a broad bevel on the outer shoulder,
# a small one inside. The outer bevel is most of what the game's camera sees of it, and it looks
# left on the left limb and right on the right one: the sun (from the left) lights the two limbs
# differently, as the sprite does, with no paint.
BAND_U = fillet([(-0.56, 1), (0.1, 1), (1, 0.2), (1, -0.5), (0.5, -1), (-0.5, -1), (-1, -0.5), (-1, 0.56)],
                (0.2, 0.2, 0.3, 0.3, 0.3, 0.3, 0.3, 0.25), 2)
BAND_DIAG = 0.82  # the yoke's width on its 45 degree runs, as a share of GW (it covers one pixel a row there)


# --- the yoke's path --------------------------------------------------------------------------

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
    nx, ny = -ty, tx  # outward (the left gun, going down: -x; the bottom: +y)
    return (cx, cy), (tx, ty), (nx, ny)


def band_w(t):
    """Half width: GW across a row or a column (the guns' width), BAND_DIAG of it on the 45-degree runs."""
    _, (tx, ty), _ = band_frame(t)
    m = max(abs(tx), abs(ty))
    return GW * (BAND_DIAG + (1 - BAND_DIAG) * (m - 0.7071) / 0.2929)


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

# The guns' section: a narrow flat on top (the sprite's one colour pixel), steep shoulders down to the
# full width, plumb flanks, a tapered belly. Under the game's sun the flat is the bright line and
# the shoulders fall away darker either side of it: the slim read comes from the form.
GUN_BOX = fillet([(-0.62, 1), (0.62, 1), (1, 0.42), (1, -0.5), (0.7, -1), (-0.7, -1), (-1, -0.5), (-1, 0.42)], 0.12, 2)
MUZ_O = [(u / math.hypot(u, v), v / math.hypot(u, v)) for u, v in GUN_BOX]  # a circle, vertex for vertex

# Stations along a gun (sprite rows): the muzzle brake's face (half way into the ink of row 7), the
# barrel, the breech ring (row 13), the neck (row 14), the receiver (rows 15-17), the rear ring
# (row 18), the socket (row 19).
MUZ_Y0, MUZ_Y1 = 7.5, 8.42
FIN_Y0, FIN_Y1, FIN_N, FIN_GAP = 8.56, 12.62, 6, 0.2
RING1, NECK1, RECV, RING2, NECK2 = (12.82, 13.86), (13.96, 14.96), (15.06, 17.96), (18.06, 18.92), (19.02, 20.05)


def build_gun(P, D, sx):
    cx = sx * GX
    A, B = GW, GZ
    # Muzzle brake: a chamfered block with a bored face and one port all round.
    lathe(P, cx, 0.0, GUN_BOX, [
        (0.0, 0.0, MUZ_Y0 + 0.55, DEEP, "-y"),
        (0.3, 0.3, MUZ_Y0 + 0.55, DEEP, "in", MUZ_O),
        (0.3, 0.3, MUZ_Y0, GUN_F, "-y", MUZ_O),
        (A - 0.17, B - 0.17, MUZ_Y0, GUN_F, "out"),
        (A, B, MUZ_Y0 + 0.2, GUN_F, "out"),
        (A, B, MUZ_Y0 + 0.4, GUN_F, "+y"),
        (A - 0.2, B - 0.2, MUZ_Y0 + 0.4, GCORE, "out"),
        (A - 0.2, B - 0.2, MUZ_Y0 + 0.56, GUN_F, "-y"),
        (A, B, MUZ_Y0 + 0.56, GUN_F, "out"),
        (A, B, MUZ_Y1 - 0.12, GUN_F, "out"),
        (A - 0.14, B - 0.14, MUZ_Y1, GUN_F, "+y"),
        (0.0, 0.0, MUZ_Y1, GUN_F, "+y"),
    ], sx=sx)
    # Barrel (rows 8-12): a dark jacket under six cooling fins, real rings with real gaps.
    J = make_loop(GUN_BOX, const(cx), const(0.0), const(GW - FIN), const(GZ - FIN), sx)
    T.loft(P, J, [MUZ_Y1 - 0.2, FIN_Y1 + 0.3], COLLAR)
    pitch = (FIN_Y1 - FIN_Y0 + FIN_GAP) / FIN_N
    for k in range(FIN_N):
        y0 = FIN_Y0 + pitch * k
        plate(P, J, y0, y0 + pitch - FIN_GAP, GUN_F, d=FIN, c=0.07, depth=0.1, ystep=1)
    # Breech and receiver (rows 13-19): one core; over it a polished ring, a dark neck sunk between
    # (the sprite's bright row, then its dark one: a turned shoulder beside a groove), the receiver's
    # deck, flank and belly plates, the rear ring and the socket the yoke runs into.
    R = make_loop(GUN_BOX, const(cx), const(0.0), const(GW - G_PLATE), const(GZ - G_PLATE), sx)
    T.loft(P, R, frange(RING1[0] - 0.2, NECK2[1] + 0.25, 1.0), GCORE)

    def S(a, b, gap=0.0):
        return dict(s0=ang_s(GUN_BOX, a) + gap, s1=ang_s(GUN_BOX, b) - gap)
    for y0, y1 in (RING1, RING2):
        plate(P, R, y0, y1, GUN_HI, d=G_PLATE + 0.03, c=0.1, ystep=0.6)
    for y0, y1 in (NECK1, NECK2):
        plate(P, R, y0, y1, COLLAR, d=0.05, c=0.04, ystep=0.6)
    y0, y1 = RECV
    plate(P, R, y0, y1, GUN_R, **S(-58, 58), d=G_PLATE, c=0.09, ystep=0.6)                    # deck
    for a, b in ((y0, y0 + 0.86), (y0 + 1.02, y0 + 1.42), (y0 + 1.58, y0 + 1.98), (y0 + 2.14, y1)):  # outboard, vented
        plate(P, R, a, b, GUN_R, **S(62, 128), d=G_PLATE, c=0.07, ystep=0.6)
    plate(P, R, y0, y1, GUN_R, **S(232, 298), d=G_PLATE, c=0.09, ystep=0.6)                   # inboard
    plate(P, R, y0, y1, MAG, **S(132, 228), d=0.14, c=0.07, ystep=0.8)                        # belly
    # A sight rail on the deck, notched twice.
    top = GZ
    for a, b in ((y0 + 0.24, y0 + 0.98), (y0 + 1.1, y0 + 1.84), (y0 + 1.96, y1 - 0.24)):
        hull(D, cbox(cx - 0.27, cx + 0.27, a, b, top - 0.1, top + 0.2, 0.08), GUN_R)
    # The magazine under the receiver (plain: undersides are not looked at).
    hull(D, cbox(cx - 0.5, cx + 0.5, y0 + 0.4, y1 - 0.4, -GZ - 0.55, -GZ + 0.1, 0.14), MAG)
    # Pivot hub on the inner flank (rows 15-17, column 6 of the sprite's inner mask): an oval disc,
    # a round boss on it, and the pylon to the pod, one px wide in plan (row 16).
    xi = cx - sx * GW  # inner face
    zc = 0.05
    ring = [(math.cos(2 * math.pi * k / 16), math.sin(2 * math.pi * k / 16)) for k in range(16)]
    pts = []
    for dx, ry, rz in ((0.3, 1.3, 0.62), (0.12, 1.4, 0.7), (-0.42, 1.4, 0.7), (-0.55, 1.26, 0.58)):
        pts += [(xi + sx * dx, 16.5 + ry * c, zc + rz * s) for c, s in ring]
    hull(D, pts, HUB)
    pts = []
    for dx, r in ((-0.5, 0.42), (-0.68, 0.42), (-0.74, 0.34)):
        pts += [(xi + sx * dx, 16.5 + r * c, zc + r * s) for c, s in ring]
    hull(D, pts, STRUT)
    pts = []
    for x in (xi - sx * 0.6, 2.9 * sx):
        pts += [(x, y, z) for y, z in ((16.03, zc - 0.2), (16.03, zc + 0.14), (16.2, zc + 0.3), (16.8, zc + 0.3),
                                       (16.97, zc + 0.14), (16.97, zc - 0.2), (16.8, zc - 0.36), (16.2, zc - 0.36))]
    hull(D, pts, STRUT)


# --- pod ----------------------------------------------------------------------------------------

def pod_loop(y, grow=0.0):
    return make_loop(POD_U, const(0.0), PZ, lambda y: max(0.02, PW(y) - P_PLATE),
                     lambda y: max(0.02, PH(y) - P_PLATE))(y, grow)


def build_pod(P, D):
    ys = [POD_Y0, 12.65, 12.72, 12.8, 12.9, 13.05, 13.25, 13.5, 13.8, 14.2, 14.6] + frange(15.0, POD_Y1, 0.7)
    T.loft(P, pod_loop, ys, POD_CORE, cap1=False)

    def S(a, b, gap=0.0):
        return dict(s0=ang_s(POD_U, a) + gap, s1=ang_s(POD_U, b) - gap)
    # Nose cap: a solid tip over the plates' front edges.
    pts = [(0.0, POD_Y0 - 0.01, PZ(POD_Y0))]
    for y, off in ((12.65, 0.06), (12.72, 0.1), (12.8, 0.14), (12.9, 0.18), (13.05, 0.22), (13.16, 0.24)):
        sec = Section(pod_loop, y)
        pts += [sec.at(k, off) for k in range(sec.n)]
    hull(P, pts, NOSE)
    # The glass nose (the sprite's dark rows 13-15): one blown panel over the top, a hair proud of
    # the shell, in a brass hoop behind it; cheek plates below it either side.
    plate(P, pod_loop, GLASS_Y0, GLASS_Y1, GLASS, **S(-54, 54), d=P_PLATE + 0.05, c=0.12, ystep=0.3)
    plate(P, pod_loop, GLASS_Y1 + 0.07, GLASS_Y1 + 0.4, FRAME, **S(-57, 57), d=P_PLATE + 0.1, c=0.07, ystep=0.4)
    for a, b, mat in ((58, 118, POD), (122, 160, POD_DK)):
        plate(P, pod_loop, GLASS_Y0, GLASS_Y1 + 0.4, mat, **S(a, b), d=P_PLATE, c=0.1, ystep=0.3)
        plate(P, pod_loop, GLASS_Y0, GLASS_Y1 + 0.4, mat, **S(-b, -a), d=P_PLATE, c=0.1, ystep=0.3)
    # Body (rows 16-19): a polished cream spine panel down the top, all but flush with the shell (the
    # sprite's bright column is sheen on the crown, not a hump: the panel is its colour and its
    # polish, not a ridge), between two real seams (the dark core shows in them: the sprite's dark
    # column beside its bright one), shoulder and flank plates, brown lower plates.
    b0, b1 = GLASS_Y1 + 0.5, 19.58
    plate(P, pod_loop, b0, b1, POD_HI, **S(-12.5, 12.5), d=P_PLATE + 0.04, c=0.1, ystep=0.7)
    for a, b, mat in ((17.5, 62, POD), (66, 118, POD), (122, 160, POD_DK)):
        plate(P, pod_loop, b0, b1, mat, **S(a, b), d=P_PLATE, c=0.11, ystep=0.7)
        plate(P, pod_loop, b0, b1, mat, **S(-b, -a), d=P_PLATE, c=0.11, ystep=0.7)
    plate(P, pod_loop, GLASS_Y0, b1, POD_DK, **S(164, 196), d=0.22, c=0.1, ystep=0.8)
    # Louvres across each shoulder plate: three raised ribs.
    for a, b in ((27, 57), (-57, -27)):
        for y in (17.0, 17.62, 18.24):
            plate(P, pod_loop, y, y + 0.36, POD, **S(a, b), d=P_PLATE + 0.1, c=0.07, ystep=0.4)
    # Tail collar, a ring all round, and the stern: a chamfered bulkhead round a wide, dark, unlit
    # exhaust sunk into it (row 20 is the sprite's ink; the sprite has no orange).
    plate(P, pod_loop, 19.7, POD_Y1 + 0.03, POD_DK, d=0.3, c=0.12, ystep=0.4)
    rx, rz = PW(POD_Y1) - P_PLATE, PH(POD_Y1) - P_PLATE
    zc = PZ(POD_Y1)
    hole = [(u / math.hypot(u, v), v / math.hypot(u, v)) for u, v in POD_U]
    lathe(P, 0.0, zc, POD_U, [
        (rx, rz, POD_Y1 - 0.02, POD_DK, "+y"),
        (rx * 0.93, rz * 0.9, POD_Y1 + 0.03, POD_DK, "+y"),
        (1.42, 0.36, POD_Y1 + 0.03, GCORE, "in", hole),
        (1.3, 0.3, POD_Y1 - 0.5, DEEP, "+y", hole),
        (0.0, 0.0, POD_Y1 - 0.5, DEEP, "+y"),
    ])
    # Strut saddles on the flanks (rows 15-17, the sprite's columns 8 and 14): dark clamps the
    # pylons run into, chamfered, the pod's top left clear.
    zs = PZ(16.5)
    for sx in (-1, 1):
        hull(D, [(sx * x, y, z) for x, y, z in cbox(2.05, 3.25, 15.1, 17.9, zs - 0.8, zs + 0.5, 0.2)], GCORE)
        hull(D, [(sx * x, y, z) for x, y, z in cbox(3.15, 3.3, 15.6, 17.4, zs - 0.45, zs + 0.2, 0.04)], COLLAR)
    # Underneath: a plain keel.
    pts = []
    for y in (13.6, 14.6, 18.6, 19.7):
        b = PZ(y) - PH(y) + 0.1
        drop = 0.3 if 14.0 < y < 19.0 else 0.04
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.45, b + 0.3), (0.3, b - drop), (0.12, b - drop - 0.06))]
    hull(D, pts, GCORE)


# --- yoke (built straight: x = across, outward +; y = arc length t; then bent) -------------------

def band_loop(t, grow=0.0):
    w = band_w(t) - B_PLATE
    return [(w * u + grow * u, BAND_ZC + (BAND_RZ + grow) * v) for u, v in BAND_U], (0.0, BAND_ZC)


def build_band(B):
    T.loft(B, band_loop, frange(0.0, BAND_T, 0.45), BAND_CORE)
    tm = BAND_T / 2
    # The diagonal runs' middles: the sleeves are split there and at the bottom centre (the sprite's
    # dark pixel between two bright ones, row 24 columns 10-12).
    td = [BAND_L[i] for i, (x, y) in enumerate(BAND_PTS) if abs(abs(x) - 4.5) < 0.6 and 22.5 < y < 23.6]
    t1 = sum(t for t in td if t < tm) / max(1, len([t for t in td if t < tm]))
    # Sleeves all the way round the core, between the clamps.
    for a, b in ((0.15, t1 - 0.3), (t1 + 0.3, tm - 1.12), (tm + 1.12, BAND_T - t1 - 0.3), (BAND_T - t1 + 0.3, BAND_T - 0.15)):
        plate(B, band_loop, a, b, BAND, d=B_PLATE, c=0.09, depth=0.12, ystep=0.42)
    # The middle joint: a dark clamp between two polished flanges that stand proud.
    plate(B, band_loop, tm - 0.44, tm + 0.44, BAND_DK, d=B_PLATE - 0.04, c=0.07, depth=0.1, ystep=0.3)
    for a, b in ((tm - 1.02, tm - 0.54), (tm + 0.54, tm + 1.02)):
        plate(B, band_loop, a, b, BAND_HI, d=B_PLATE + 0.1, c=0.1, depth=0.2, ystep=0.3)
    for t in (t1, BAND_T - t1):  # thin clamps on the corners
        plate(B, band_loop, t - 0.2, t + 0.2, BAND_DK, d=B_PLATE + 0.05, c=0.07, depth=0.12, ystep=0.4)


# --- assembly -------------------------------------------------------------------------------------

def build(coll, mats):
    P = Part("uship_guns", smooth_angle=34)
    D = Part("uship_details", smooth_angle=35)
    for sx in (-1, 1):
        build_gun(P, D, sx)
    Q = Part("uship_pod", smooth_angle=34)
    build_pod(Q, D)
    B = Part("uship_yoke", smooth_angle=34)
    build_band(B)
    objs = [finish(p, mats, coll) for p in (P, D, Q)] + [finish(B, mats, coll, warp=band_warp)]
    for o in objs:
        print("u-ship part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = tuple(i for i in range(20) if i != GLASS)


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


# The game's roll at bank steps 1 and 2, degrees (spriteModels bank.roll, D93).
BANK_ROLL = [40, 52.5]
# ... and its sideways shift per frame, game px, hardest left bank to hardest right (bank.shift);
# None leaves it to src/render/bankShift.ts.
BANK_SHIFT = None


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    objs = build(coll, mats)
    obj = T.join(objs, NAME)
    # The outline shell is made from a closed copy, taken before hidden faces are culled (remeshing
    # the culled, open model wraps both sides of every open plate, D118) and kept out of the bake.
    closed = obj.copy()
    closed.data = obj.data.copy()
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"u-ship: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glow (src/ui/backdrop.ts): just behind the exhaust, glTF axes
    # (x, y up, z aft), orange (palette 121). The model itself carries no glow: the sprite has none.
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round(-0.5 * PX, 4), round(PZ(POD_Y1) * PX, 4),
                                                         round((POD_Y1 + 0.4 - 14) * PX, 4)]]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="uship_bake_"))
        fmt = "WEBP"
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, voxel=0.03, faces=3000, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"u-ship: outline shell {len(shell.data.polygons)} faces")
    sprites = common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT)
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, sprites, image_format=fmt)
    if "--preview" in argv:
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
