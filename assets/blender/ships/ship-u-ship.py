"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275).

What it is: a twin-boom gunship. Two long rail guns (steel) run fore and aft; their breeches plug
into a brass tail hoop, a girder standing on edge that loops round the stern; a small pointed brass
gondola (glazed nose, engine in the tail) hangs between the guns on a two-bar trunnion yoke.

Built in the Talon's way (assets/blender/usp_talon.py, D50-D53): cages in sprite px (x = column -
11.5, y = sprite row, aft is +y, z up), pchip stations, dark cores under proud plates so panel lines
are real gaps, one pal_<index> material per part (the sprite's index for the region the part
covers), an AO / roughness bake only (no concept projection), the outline shell, tyrian_engines.

The PLAN is the blueprint-built model's (the one restored by D240): rails and hoop 1.7 px wide on
the same centre lines, the pod 5 px wide, the same hubs, pylons and saddles (rule IoU 1.0 on frame
271, D74). Nothing is thinned or shrunk to fit top-view pixels (CLAUDE.md art rule 8); what makes the
sprite's thin wire U and small pointed pod is each part's SECTION, under the game's own lights:
- rails: a round barrel (1.7 px: a jacket of lengthwise plates, then four cooling fins on a 1.3 px
  core) between a ported muzzle brake and a bright breech ring (12), a sunk neck (6), a plated
  receiver (10) with a sight rail (11), a rear ring and neck; under it a ladder web and a lower
  chord (5), so the gun is a deep member on edge (2.3 px), and that chord runs on into the hoop's;
- hoop: a band on edge (features.json), 2.2 px deep: a ridge-roofed brass cap (25; two 51 degree
  facets meeting in a 0.3 px land, so one facet is lit and one is in shade: a thin bright line by
  form), a dark recessed web (21) with gussets, a lower chord (22); ferrules where it takes the
  rails, two pale collars (28) either side of a dark blast clamp (21) on the centre line. Its centre
  line is exact (lines and arcs) and its second half is the first one mirrored, so the two sides
  are the same to the vertex; the cap's segments meet in chamfered seams over a dark key;
- pod: a round-section gondola on the old plan, a pointed ogive nose (tip on the axis), a wrap-round
  visor over rows 13-15 (163) in brass sills (21), then lengthwise plates only (it is not a barrel:
  no hoops round the body): a raised dorsal spine (23), one broad smooth port shoulder (24; the
  sprite's pale column 10 is its sheen), the starboard service trench with its conduit (162, the
  sprite's dark column 12), flank plates with an access panel, a boat tail to a closed stern with a
  steel nozzle. No emission (the sprite has no orange pixel; the menus' glow is tyrian_engines).

The banking frames are the same model rolled by the game, 40 degrees at half bank and 55 at full
(BANK_ROLL, tools/bank_roll.py, D93); nothing in the model is shaped for them.

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
(BARREL, BCORE, BRAKE, RING, NECK, RECV, SIGHT, GCORE, DEEP, SPAR, MAG, HUB, PYLON, BRACE, SADDLE,
 HOOP, HOOP_WEB, HOOP_CHORD, HOOP_COLLAR, HOOP_CLAMP,
 POD, POD_SPINE, POD_BELLY, POD_CORE, POD_NOSE, POD_TAIL, FRAME, GLASS, NOZZLE, THROAT) = range(30)
NSLOT = 30

# Palette index per slot: the median index of the sprite pixels each part covers, darkest shading
# and brightest highlights left out (blueprint.json spriteMedians): barrel 9, breech rings 12, necks
# 6, receiver 10 (its lighter pixels 11: the sight rail), hub 4, pylon 7; hoop 25, its collars 28
# and clamp 21; canopy 163; pod body 24, spine 23, groove 162 (measured again on a top render with
# one colour per material: every region's majority index is the sprite's median).
PAL_OF = {BARREL: 9, BCORE: 9, BRAKE: 9, RING: 12, NECK: 6, RECV: 10, SIGHT: 11, GCORE: 3, DEEP: 2, SPAR: 5,
          MAG: 7, HUB: 4, PYLON: 7, BRACE: 6, SADDLE: 3,
          HOOP: 25, HOOP_WEB: 21, HOOP_CHORD: 22, HOOP_COLLAR: 28, HOOP_CLAMP: 21,
          POD: 24, POD_SPINE: 23, POD_BELLY: 22, POD_CORE: 162, POD_NOSE: 22, POD_TAIL: 21, FRAME: 21,
          GLASS: 163, NOZZLE: 3, THROAT: 162}
BRASS_SLOTS = {HOOP, HOOP_WEB, HOOP_CHORD, HOOP_COLLAR, HOOP_CLAMP, POD, POD_SPINE, POD_BELLY, POD_CORE,
               POD_NOSE, POD_TAIL, FRAME, THROAT}

METAL = 0.3  # metalness scale (satin, D53)
# The baked colour map's tint on the brass parts (D53): three's Neutral tone mapping takes most from
# the smallest channel (blue) and pushes the lit tan to saturated bronze; this keeps it sandy khaki.
TINT = (0.76, 0.86, 1.0)
# The steel's map is a touch warm: the game's blue sky light otherwise tints the greys blue.
TINT_STEEL = (1.0, 0.97, 0.92)


def materials(sprite):
    def rgb(i):
        return common.srgb(*sprite["colors"][str(i)])

    def pal(slot, tag, metallic, roughness):
        i = PAL_OF[slot]
        return common.material(f"pal_{i}_uship_{tag}", rgb(i), metallic=metallic * METAL, roughness=roughness)
    return [
        pal(BARREL, "barrel", 0.75, 0.36),
        pal(BCORE, "barrel_core", 0.6, 0.5),
        pal(BRAKE, "muzzle_brake", 0.75, 0.38),
        pal(RING, "breech_ring", 0.8, 0.28),
        pal(NECK, "neck", 0.65, 0.45),
        pal(RECV, "receiver", 0.7, 0.38),
        pal(SIGHT, "sight_rail", 0.75, 0.32),
        pal(GCORE, "gun_core", 0.5, 0.5),
        pal(DEEP, "recess", 0.3, 0.8),
        pal(SPAR, "spar", 0.65, 0.44),
        pal(MAG, "magazine", 0.6, 0.45),
        pal(HUB, "hub", 0.65, 0.4),
        pal(PYLON, "pylon", 0.65, 0.42),
        pal(BRACE, "brace", 0.65, 0.42),
        pal(SADDLE, "saddle", 0.5, 0.5),
        pal(HOOP, "hoop", 0.55, 0.4),
        pal(HOOP_WEB, "hoop_web", 0.5, 0.5),
        pal(HOOP_CHORD, "hoop_chord", 0.5, 0.46),
        pal(HOOP_COLLAR, "hoop_collar", 0.6, 0.34),
        pal(HOOP_CLAMP, "hoop_clamp", 0.5, 0.46),
        pal(POD, "pod", 0.55, 0.36),
        pal(POD_SPINE, "pod_spine", 0.6, 0.36),
        pal(POD_BELLY, "pod_belly", 0.5, 0.44),
        pal(POD_CORE, "pod_core", 0.4, 0.6),
        pal(POD_NOSE, "pod_nose", 0.55, 0.38),
        pal(POD_TAIL, "pod_tail", 0.5, 0.44),
        pal(FRAME, "frame", 0.5, 0.38),
        common.material(f"pal_{PAL_OF[GLASS]}_uship_glass", rgb(PAL_OF[GLASS]), metallic=0.0, roughness=0.04),
        pal(NOZZLE, "nozzle", 0.7, 0.36),
        pal(THROAT, "throat", 0.3, 0.8),
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
    +u (negative: toward -u) meets the unit section; negative angles come back below 0."""
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
    """loopf(y, grow=0) for a section `unit` scaled by rx(y), rz(y) about (cx(y), cz(y))."""
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


def ring_loft(part, rings, mat, cap0=True, cap1=True):
    """A closed convex-section tube through explicit rings of points (same count each), capped."""
    vs = [[part.v(p) for p in r] for r in rings]
    cs = [sum((Vector(p) for p in r), Vector()) / len(r) for r in rings]
    for k in range(len(vs) - 1):
        n = len(vs[k])
        away = tuple((cs[k] + cs[k + 1]) / 2)
        for i in range(n):
            j = (i + 1) % n
            part.f((vs[k][i], vs[k][j], vs[k + 1][j], vs[k + 1][i]), mat, away=away)
    if cap0:
        part.f(vs[0], mat, out=tuple(cs[0] - cs[1]))
    if cap1:
        part.f(vs[-1], mat, out=tuple(cs[-1] - cs[-2]))


def cyl_x(x0, x1, y, z, r, n=12, k0=1.0, k1=1.0, rz=None):
    """Points of a cylinder along x (for hull): radius r in y, rz in z, scaled k0 / k1 at its ends."""
    rz = r if rz is None else rz
    pts = []
    for x, k in ((x0, k0), (x1, k1)):
        pts += [(x, y + r * k * math.cos(2 * math.pi * i / n), z + rz * k * math.sin(2 * math.pi * i / n))
                for i in range(n)]
    return pts


# --- plan (sprite px; x = column - 11.5) ---------------------------------------------------------

GX = 6.0    # rail centre lines (columns 5 and 17)
GW = 0.85   # rail / hoop half width in plan: the old model's 1.7 px (1 colour px + 0.35 px of ink a side, D74 rule 3)
BZ = 0.17   # the barrels' axis height

# The hoop's centre line (the old model's): down each rail, 45 degrees in to a flat bottom, filleted.
HOOP_PATH = [(-GX, 19.9), (-GX, 21.5), (-3.0, 24.5), (3.0, 24.5), (GX, 21.5), (GX, 19.9)]
HOOP_R = [None, 2.0, 2.6, 2.6, 2.0, None]
# Its girder section (u outward, z), u scaled by the local half width / GW.
H_ROOF = [(-0.14, 0.95), (0.14, 0.95), (0.85, 0.06), (0.85, -0.1), (-0.85, -0.1), (-0.85, 0.06)]
H_WEB = [(-0.36, -0.06), (0.36, -0.06), (0.36, -0.95), (-0.36, -0.95)]
H_CHORD = [(-0.5, -0.89), (0.5, -0.89), (0.62, -1.03), (0.46, -1.25), (-0.46, -1.25), (-0.62, -1.03)]
H_GUSSET = [(-0.78, -0.08), (0.78, -0.08), (0.56, -0.95), (-0.56, -0.95)]
H_COLLAR = [(-0.2, 1.03), (0.2, 1.03), (0.93, 0.1), (0.93, -0.16), (-0.93, -0.16), (-0.93, 0.1)]
H_BLOCK = [(-0.26, 1.03), (0.26, 1.03), (0.9, 0.22), (0.9, -0.3), (0.5, -1.29), (-0.5, -1.29), (-0.9, -0.3),
           (-0.9, 0.22)]
# The key under each cap joint: the roof's own section, 0.07 px inside it.
H_KEY = [(-0.1, 0.88), (0.1, 0.88), (0.78, 0.03), (0.78, -0.07), (-0.78, -0.07), (-0.78, 0.03)]
H_FERRULE = 0.78

# The pod: plan half width to the inner edge of the sprite's ink (a pointed ogive nose, tip at row
# 12.45; 3 px on row 13, 5 px on rows 14-19, eased stern corners), and its elevation (free of the
# sprite): tallest at row 16.5, a boat tail to the stern.
PW = pchip([12.45, 12.7, 13.0, 13.5, 14.0, 14.5, 15.2, 19.0, 19.6, 20.0, 20.25],
           [0.0, 0.5, 1.0, 1.62, 2.08, 2.34, 2.48, 2.48, 2.4, 2.26, 2.1])
PZT = pchip([12.45, 13.0, 13.5, 14.0, 14.75, 15.6, 16.5, 17.5, 18.5, 19.4, 20.25],
            [0.0, 0.62, 1.14, 1.6, 2.14, 2.54, 2.7, 2.62, 2.34, 1.95, 1.55])
PZB = pchip([12.45, 13.0, 13.5, 14.0, 14.75, 15.6, 16.5, 18.0, 19.2, 20.25],
            [0.0, -0.44, -0.84, -1.2, -1.66, -2.0, -2.1, -2.02, -1.7, -1.3])
POD_Y0, POD_CAP, POD_Y1 = 12.45, 13.2, 20.25
PLATE = 0.2    # the plates' height over the core
PN, PE = 24, 0.9
PA = [360 * (i + 0.5) / PN for i in range(PN)]


def pzm(y):
    return 0.15 * min(1.0, max(0.0, (y - POD_Y0) / 1.5))


def pod_loop(y, grow=0.0):
    """The pod's core section at row y: a superellipse (exponent 2 / PE), its own half height above
    and below the waist; point i at parameter angle PA[i] from straight up toward +x."""
    y = min(max(y, POD_Y0), POD_Y1)
    zm = pzm(y)
    W = max(PW(y) - PLATE + grow, 0.02)
    ht = max(PZT(y) - zm - PLATE + grow, 0.02)
    hb = max(zm - PZB(y) - PLATE + grow, 0.02)
    pts = []
    for a in PA:
        s, c = math.sin(math.radians(a)), math.cos(math.radians(a))
        pts.append((W * math.copysign(abs(s) ** PE, s), zm + (ht if c >= 0 else hb) * math.copysign(abs(c) ** PE, c)))
    return pts, (0.0, zm)


def PS(a):
    """Loop parameter of parameter angle a (degrees from straight up toward +x; may be negative)."""
    return a / 360 * PN - 0.5


def pod_pt(y, a, off=0.0):
    return Section(pod_loop, y).at(PS(a), off)


# --- the hoop's path ----------------------------------------------------------------------------

def _hoop_half():
    """The filleted centre line's first half as exact pieces, each with its start arc length:
    ('L', t0, len, p0, dir) lines and ('A', t0, len, centre, r, a0, da) arcs. The path is symmetric
    about x = 0, so the second half is this one mirrored (hoop_frame)."""
    P = [Vector(p) for p in HOOP_PATH]
    pieces, cur, t0 = [], P[0], 0.0
    for i in (1, 2):
        p0, p1, p2 = P[i - 1], P[i], P[i + 1]
        d1, d2 = (p0 - p1).normalized(), (p2 - p1).normalized()
        ang = math.acos(max(-1, min(1, d1.dot(d2))))
        r = HOOP_R[i]
        t = r / math.tan(ang / 2)
        a, b = p1 + d1 * t, p1 + d2 * t
        c = p1 + (d1 + d2).normalized() * (r / math.sin(ang / 2))
        a0 = math.atan2(a.y - c.y, a.x - c.x)
        a1 = math.atan2(b.y - c.y, b.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        ln = (a - cur).length
        pieces.append(("L", t0, ln, cur, (a - cur) / ln))
        t0 += ln
        pieces.append(("A", t0, abs(da) * r, c, r, a0, da))
        t0 += abs(da) * r
        cur = b
    ln = -cur.x                                  # the flat bottom, to the centre line
    pieces.append(("L", t0, ln, cur, Vector((1.0, 0.0))))
    return pieces, t0 + ln


HOOP_HALF, _HOOP_MID = _hoop_half()
HOOP_T = 2 * _HOOP_MID
# Arc length at the middle of the port 45-degree run (the cap's corner joint; starboard: HOOP_T - it).
HOOP_TC = HOOP_HALF[2][1] + HOOP_HALF[2][2] / 2


def hoop_frame(t):
    """Centre point, unit tangent and outward normal (away from the U's inside) at arc length t:
    exact on the lines and the arcs, continuous, and the same to the bit on both sides (the second
    half is the first one mirrored in x = 0)."""
    t = max(0.0, min(HOOP_T, t))
    if t > _HOOP_MID:
        (cx, cy), (tx, ty), (nx, ny) = hoop_frame(HOOP_T - t)
        return (-cx, cy), (tx, -ty), (-nx, ny)
    pc = next((q for q in reversed(HOOP_HALF) if t >= q[1]), HOOP_HALF[0])
    u = t - pc[1]
    if pc[0] == "L":
        p, d = pc[3] + pc[4] * u, pc[4]
        tx, ty = d.x, d.y
    else:
        _, _, ln, c, r, a0, da = pc
        th = a0 + da * u / ln
        sg = 1.0 if da > 0 else -1.0
        p = Vector((c.x + r * math.cos(th), c.y + r * math.sin(th)))
        tx, ty = -sg * math.sin(th), sg * math.cos(th)
    return (p.x, p.y), (tx, ty), (-ty, tx)


def _hoop_knots(step=0.45):
    """Arc lengths where the hoop's lofts take a ring: the ends of every line and arc, and the arcs
    cut into spans of `step` or less (a straight run needs none between its ends). Mirrored, so
    both sides' facets are the same, and shared by cap, web and chord, so their facets line up."""
    ks = set()
    for pc in HOOP_HALF:
        n = max(1, math.ceil(pc[2] / step)) if pc[0] == "A" else 1
        for k in range(n + 1):
            t = pc[1] + pc[2] * k / n
            ks.update((round(t, 9), round(HOOP_T - t, 9)))
    return sorted(ks)


HOOP_KNOTS = _hoop_knots()


def hoop_q(t):
    """Width scale: 1 across a row or a column (the rails' width), less on the 45-degree runs (the
    old model's law: the sprite's 1 px steps)."""
    _, (tx, ty), _ = hoop_frame(t)
    return max(abs(tx), abs(ty))


def hoop_warp(co):
    (cx, cy), _, (nx, ny) = hoop_frame(co.y)
    return Vector((cx + nx * co.x, cy + ny * co.x, co.z))


def hoop_t_at_x(x):
    """Arc length where the flat bottom run crosses x."""
    return _HOOP_MID + x


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


# --- rails ------------------------------------------------------------------------------------

MUZ_U = unit_box(0.3, 0.32, 0.3, 1)


def even_circle(unit):
    """A unit circle with one point per point of `unit`, evenly spaced and turned to line up with it
    (the bore of a faceted block: round, with no twist in the face between them)."""
    n = len(unit)
    th = [math.atan2(u, v) for u, v in unit]
    sx = sum(math.sin(t - 2 * math.pi * i / n) for i, t in enumerate(th))
    cx = sum(math.cos(t - 2 * math.pi * i / n) for i, t in enumerate(th))
    t0 = math.atan2(sx, cx)
    return [(math.sin(t0 + 2 * math.pi * i / n), math.cos(t0 + 2 * math.pi * i / n)) for i in range(n)]


MUZ_O = even_circle(MUZ_U)  # the bore: round in the brake's faceted face
C16 = unit_circle(12)   # the barrels' round sections
C14 = unit_circle(14)
REC_U = unit_box(0.5, 0.375, 0.2, 1)
REC_ZC, REC_H, REC_P = -0.1, 1.12, 0.14   # receiver: centre height, half height, plate height
BR_A, BR_B = GW, 0.81                      # muzzle brake half width / half height
RI, RO = 0.64, 0.85                        # barrel core / fin radius: the fins keep the old 1.7 px
FINS = [11.08, 11.53, 11.98, 12.43]
CHORD_Z = -1.1
CHORD_U = [(-0.3, 0.13), (0.3, 0.13), (0.33, 0.0), (0.2, -0.13), (-0.2, -0.13), (-0.33, 0.0)]


def build_rail(P, D, sx):
    cx = sx * GX
    A, B = BR_A, BR_B
    # Muzzle brake (rows 7.4-8.8): a chamfered block, bored, two ports cut round it.
    lathe(P, cx, BZ, MUZ_U, [
        (0.0, 0.0, 7.8, DEEP, "-y"),
        (0.3, 0.3, 7.8, DEEP, "in", MUZ_O),
        (0.3, 0.3, 7.4, BRAKE, "-y", MUZ_O),
        (A - 0.16, B - 0.16, 7.4, BRAKE, "out"),
        (A, B, 7.56, BRAKE, "out"),
        (A, B, 7.82, BRAKE, "+y"),
        (A - 0.22, B - 0.22, 7.82, GCORE, "out"),
        (A - 0.22, B - 0.22, 7.98, BRAKE, "-y"),
        (A, B, 7.98, BRAKE, "out"),
        (A, B, 8.24, BRAKE, "+y"),
        (A - 0.22, B - 0.22, 8.24, GCORE, "out"),
        (A - 0.22, B - 0.22, 8.4, BRAKE, "-y"),
        (A, B, 8.4, BRAKE, "out"),
        (A, B, 8.68, BRAKE, "out"),
        (A - 0.14, B - 0.14, 8.8, BRAKE, "+y"),
        (0.0, 0.0, 8.8, BRAKE, "+y"),
    ], sx=sx)
    # Barrel (rows 8.8-12.9): a round core under eight cooling fins in two groups, a clamp between.
    J = make_loop(C16, const(cx), const(BZ), const(RO - 0.16), const(RO - 0.16), sx)
    T.loft(P, J, [8.7, 9.65, 10.62], BCORE)
    for a, b in ((34, 86), (94, 146), (154, 206), (-146, -94), (-86, -34)):
        plate(P, J, 8.86, 10.5, BARREL, s0=ang_s(C16, a), s1=ang_s(C16, b), d=0.16, c=0.05, ystep=1.0)
    for a, b in ((8.86, 9.62), (9.74, 10.5)):
        plate(P, J, a, b, BARREL, s0=ang_s(C16, -26), s1=ang_s(C16, 26), d=0.16, c=0.05, ystep=1.0)
    prof = [(0.0, 0.0, 10.9, BCORE, "-y"), (RI, RI, 10.9, BCORE, "out")]
    for y0 in FINS:
        prof += [(RI, RI, y0, BARREL, "-y"), (RO, RO, y0 + 0.04, BARREL, "out"), (RO, RO, y0 + 0.2, BARREL, "+y"),
                 (RI, RI, y0 + 0.24, BCORE, "out")]
    prof += [(RI, RI, 12.95, BCORE, "+y"), (0.0, 0.0, 12.95, BCORE, "+y")]
    lathe(P, cx, BZ, C16, prof, sx=sx)
    lathe(P, cx, BZ, MUZ_U, [
        (0.0, 0.0, 10.58, BRAKE, "-y"),
        (A - 0.1, A - 0.1, 10.58, BRAKE, "out"),
        (A - 0.02, A - 0.02, 10.66, BRAKE, "out"),
        (A - 0.02, A - 0.02, 10.88, BRAKE, "out"),
        (A - 0.1, A - 0.1, 10.96, BRAKE, "+y"),
        (0.0, 0.0, 10.96, BRAKE, "+y"),
    ], sx=sx)
    # Breech ring, neck, rear ring, rear neck: round, on the barrel's axis.
    for y0, y1 in ((12.9, 13.95), (17.95, 18.95)):
        ym = (y0 + y1) / 2
        lathe(P, cx, BZ, C16, [
            (0.0, 0.0, y0, RING, "-y"),
            (0.82, 0.82, y0, RING, "out"),
            (0.92, 0.92, y0 + 0.1, RING, "out"),
            (0.92, 0.92, ym - 0.1, RING, "+y"),
            (0.82, 0.82, ym - 0.06, GCORE, "out"),
            (0.82, 0.82, ym + 0.06, RING, "-y"),
            (0.92, 0.92, ym + 0.1, RING, "out"),
            (0.92, 0.92, y1 - 0.1, RING, "out"),
            (0.82, 0.82, y1, RING, "+y"),
            (0.0, 0.0, y1, RING, "+y"),
        ], sx=sx)
    for y0, y1 in ((13.9, 14.95), (18.9, 20.0)):
        lathe(P, cx, BZ, C16, [
            (0.0, 0.0, y0, NECK, "-y"),
            (0.75, 0.75, y0, NECK, "out"),
            (0.75, 0.75, y1, NECK, "+y"),
            (0.0, 0.0, y1, NECK, "+y"),
        ], sx=sx)
    # Receiver (rows 14.9-17.95): a dark core under deck, shoulder, flank and belly plates; vent
    # gaps in the outboard flank; a notched sight rail on the deck.
    R = make_loop(REC_U, const(cx), const(REC_ZC), const(GW - REC_P), const(REC_H - REC_P), sx)
    T.loft(P, R, [14.9, 15.7, 16.4, 17.2, 17.95], GCORE)

    def S(a, b):
        return dict(s0=ang_s(REC_U, a), s1=ang_s(REC_U, b))
    y0, y1 = 14.97, 17.88
    plate(P, R, y0, y1, RECV, **S(-24, 24), d=REC_P, c=0.07, ystep=1.0)
    for a, b in ((29, 55), (-55, -29), (-119, -61)):
        plate(P, R, y0, y1, RECV, **S(a, b), d=REC_P, c=0.07, ystep=1.0)
    for a, b in ((y0, 15.6), (15.72, 16.05), (16.17, 16.5), (16.62, 16.95), (17.07, y1)):
        plate(P, R, a, b, RECV, **S(61, 119), d=REC_P, c=0.06, ystep=1.0)
    plate(P, R, y0, y1, MAG, **S(125, 235), d=0.1, c=0.06, ystep=1.0)
    top = REC_ZC + REC_H
    for a, b in ((15.15, 15.9), (16.0, 16.75), (16.85, 17.7)):
        hull(D, cbox(cx - 0.28, cx + 0.28, a, b, top - 0.08, top + 0.2, 0.07), SIGHT)
    # Raked magazine under the receiver (underside: a plain closed box).
    hull(D, [(cx + dx * k, y - d, z) for z, d, k in ((-1.15, 0.0, 1.0), (-1.72, 0.16, 1.0), (-1.84, 0.2, 0.7))
             for dx in (-0.5, 0.5) for y in (15.45, 17.45)], MAG)
    # Lower chord under the whole gun, rising to the brake, and the ladder web that hangs it from
    # the barrel: the rail is a deep member on edge, and its chord runs on into the hoop's.
    def chord(y, z, k=1.0):
        return [(cx + u * k, y, z + v * k) for u, v in CHORD_U]
    ring_loft(D, [chord(8.6, -0.52, 0.8), chord(9.45, CHORD_Z), chord(19.95, CHORD_Z)], SPAR)
    for a in (9.5, 10.36, 11.22, 12.08, 12.94, 13.8, 18.1, 18.96):
        hull(D, cbox(cx - 0.14, cx + 0.14, a, a + 0.42, CHORD_Z - 0.02, -0.34, 0.04), SPAR)
    hull(D, cbox(cx - 0.24, cx + 0.24, 10.62, 10.92, CHORD_Z - 0.05, -0.4, 0.05), BRAKE)
    # Yoke: a trunnion hub on the inner flank (column 6 / 16, rows 15-17), a lens-section pylon
    # (row 16), a lower brace bar, a dark saddle on the pod's flank (columns 8 / 14).
    hull(D, cyl_x(sx * 4.5, sx * 4.62, 16.5, -0.05, 1.25, 14, 0.86, 1.0) + cyl_x(sx * 4.62, sx * 5.25, 16.5, -0.05, 1.25, 14), HUB)
    hull(D, cyl_x(sx * 4.4, sx * 4.52, 16.5, -0.05, 0.62, 12, 0.85, 1.0), BRACE)
    hull(D, [(sx * x, y, -0.05 + z) for x, y, z in cbox(4.34, 4.46, 16.42, 16.58, -0.5, 0.5, 0.03)], DEEP)
    hull(D, [(sx * x, y, z) for x in (3.3, 4.6) for y, z in ((15.75, 0.05), (16.12, 0.5), (16.88, 0.5), (17.25, 0.05),
                                                             (16.88, -0.42), (16.12, -0.42))], PYLON)
    hull(D, cyl_x(sx * 2.05, sx * 5.25, 16.5, -1.02, 0.2, 8), BRACE)
    hull(D, [(sx * x, y, z) for x, y, z in cbox(2.2, 3.45, 15.15, 17.85, -0.62, 0.72, 0.2)], SADDLE)
    hull(D, [(sx * x, y, z) for x, y, z in cbox(3.38, 3.52, 15.6, 17.4, -0.3, 0.42, 0.04)], BRACE)


# --- hoop (built straight: x = across, outward +; y = arc length t; then bent) -------------------

def hoop_seg(B, t0, t1, poly, mat, cham=0.05):
    """A length of the hoop with section `poly` (u outward, z) from arc length t0 to t1, its ends
    chamfered over `cham` (0: square ends), rings at the path's knots."""
    def ring(t, ku=1.0, kz=1.0):
        q = hoop_q(t)
        zc = sum(z for _, z in poly) / len(poly)
        return [(u * q * ku, t, zc + (z - zc) * kz) for u, z in poly]
    a, b = t0 + cham, t1 - cham
    ts = [a] + [k for k in HOOP_KNOTS if a + 0.04 < k < b - 0.04] + [b]
    rings = [ring(t) for t in ts]
    if cham > 0:
        rings = [ring(t0, 0.9, 0.92)] + rings + [ring(t1, 0.9, 0.92)]
    ring_loft(B, rings, mat)


def build_hoop(B):
    """Everything comes in mirrored pairs (a, b) and (HOOP_T - b, HOOP_T - a), so the two sides are
    the same to the vertex."""
    T_, fer, tc = HOOP_T, H_FERRULE, HOOP_TC
    tL = [hoop_t_at_x(x) for x in (-1.5, -0.5, 0.5, 1.5)]

    def both(a, b, poly, mat, **kw):
        hoop_seg(B, a, b, poly, mat, **kw)
        hoop_seg(B, T_ - b, T_ - a, poly, mat, **kw)
    # The cap: two segments a side, meeting on the middle of the 45-degree run. A joint between two
    # brass parts (ferrule to cap, cap to cap) is a modelled seam: chamfered ends 0.04 px apart over
    # a dark key (the web's metal) that fills the cap's section there, so nothing shows through and
    # the game's ink does not draw it as a break. Where the colour changes (cap to collar, collar to
    # clamp) the chamfered ends butt: a closed V groove.
    gap = 0.02
    both(fer + gap, tc - gap, H_ROOF, HOOP)
    both(tc + gap, tL[0], H_ROOF, HOOP)
    for t in (fer, tc):
        both(t - 0.14, t + 0.14, H_KEY, HOOP_WEB, cham=0)
    hoop_seg(B, fer - 0.1, T_ - fer + 0.1, H_WEB, HOOP_WEB, cham=0.02)
    hoop_seg(B, fer - 0.1, T_ - fer + 0.1, H_CHORD, HOOP_CHORD, cham=0.02)
    # Gussets, placed from the centre line outward.
    d = 1.9
    while T_ / 2 - d > fer + 0.5:
        for t in (T_ / 2 - d, T_ / 2 + d):
            q = hoop_q(t)
            hull(B, [(u * q, t + e, z) for u, z in H_GUSSET for e in (-0.08, 0.08)], HOOP_WEB)
        d += 1.3
    both(0.0, fer, H_BLOCK, HOOP)
    both(tL[0], tL[1], H_COLLAR, HOOP_COLLAR)
    hoop_seg(B, tL[1], tL[2], [(u * 0.97, z - 0.06 if z > 0 else z) for u, z in H_BLOCK], HOOP_CLAMP)


# --- pod ----------------------------------------------------------------------------------------

def build_pod(P, D, G):
    ys = [POD_CAP, 13.5, 13.8, 14.1, 14.5, 14.9, 15.3, 15.7] + frange(16.2, 19.2, 0.6) + [19.6, 19.95, POD_Y1]
    T.loft(P, pod_loop, ys, POD_CORE, cap0=True, cap1=False)

    def PP(y0, y1, a0, a1, mat, d=PLATE, c=0.07, ystep=0.8, part=P, depth=0.12):
        plate(part, pod_loop, y0, y1, mat, s0=PS(a0), s1=PS(a1), d=d, c=c, depth=depth, ystep=ystep)
    # Nose cone: a pointed brass ogive, tip on the axis (rows 12.45-13.2).
    rings = []
    for y, off in ((12.5, 0.08), (12.6, 0.12), (12.75, 0.16), (12.95, 0.19), (POD_CAP + 0.02, 0.2)):
        sec = Section(pod_loop, y)
        rings.append([sec.at(k, off) for k in range(sec.n)])
    sec = Section(pod_loop, POD_CAP + 0.02)
    rings.append([sec.at(k, -0.05) for k in range(sec.n)])
    tip = P.v((0.0, POD_Y0, 0.0))
    vs = [[P.v(p) for p in r] for r in rings]
    for i in range(PN):
        j = (i + 1) % PN
        P.f((tip, vs[0][i], vs[0][j]), POD_NOSE, away=(0, 12.7, 0))
        for k in range(len(vs) - 1):
            P.f((vs[k][i], vs[k][j], vs[k + 1][j], vs[k + 1][i]), POD_NOSE,
                **(dict(out=(0, 1, 0)) if k == len(vs) - 2 else dict(away=(0, rings[k][0][1], pzm(rings[k][0][1])))))
    # Windshield (rows 13.3-15.1): three panes set in under brass sills and mullions, cheeks below
    # them, a sill behind. One faint ring seam (RING) parts the nose from the body.
    GA, MA, FH, RING = 58, 17, 101.0, 15.44
    PP(13.3, 15.1, -MA + 2, MA - 2, GLASS, d=0.09, c=0.04, ystep=0.3, part=G)
    for s in (-1, 1):
        a0, a1 = sorted((s * (MA + 2.5), s * GA))
        PP(13.64, 15.1, a0, a1, GLASS, d=0.09, c=0.04, ystep=0.3, part=G)
        a0, a1 = sorted((s * (MA + 2), s * (GA + 6)))
        PP(13.5, 13.64, a0, a1, FRAME, d=0.2, c=0.05)                       # side pane's front sill
        PP(13.28, 13.48, a0, a1, POD_NOSE, d=0.2, c=0.06)                   # nose shoulder
        a0, a1 = sorted((s * (MA - 1.5), s * (MA + 2)))
        PP(13.3, 15.14, a0, a1, FRAME, d=0.2, c=0.05, ystep=0.3)            # mullion
        a0, a1 = sorted((s * (GA + 0.5), s * (GA + 6)))
        PP(13.3, 15.14, a0, a1, FRAME, d=0.2, c=0.05, ystep=0.3)            # side sill
        a0, a1 = sorted((s * (GA + 8), s * FH))
        PP(13.28, RING - 0.04, a0, a1, POD, ystep=0.3)                      # cheek
    PP(13.16, 13.32, -MA - 2, MA + 2, FRAME, d=0.21, c=0.05)                # front sill
    PP(15.16, RING - 0.04, -GA - 6, GA + 6, FRAME, d=PLATE, c=0.06)         # rear sill
    # Body (rows 15.5-19.9): lengthwise plates only, no hoops round it (it is a gondola, not a keg).
    # The raised dorsal spine; one broad smooth port shoulder from the spine to the flank seam (the
    # sprite's pale column 10 is its sheen); to starboard the service trench between spine and
    # shoulder (the core's dark metal: the sprite's column 12) with a conduit in it; a flank plate
    # each side below a lengthwise seam, with a raised access panel; a plain belly.
    SA, TR0, TR1, FL = 11.5, 13.0, 31.0, 62.0
    y0, y1 = RING + 0.04, 19.9
    PP(y0, y1, -SA, SA, POD_SPINE, d=PLATE + 0.12, c=0.1)
    PP(y0, y1, -FL + 1.5, -SA - 2, POD)
    PP(y0, y1, TR1 + 1, FL - 1.5, POD)
    for s in (-1, 1):
        a0, a1 = sorted((s * (FL + 1.5), s * FH))
        PP(y0, y1, a0, a1, POD)
        # The panel's skirt stops just inside the plate under it (a skirt down to the core would be
        # nearly all hidden, and cull_hidden would take it whole, leaving a see-through slit).
        a0, a1 = sorted((s * (FL + 7), s * (FH - 6)))
        PP(16.5, 18.6, a0, a1, POD, d=PLATE + 0.06, c=0.04, depth=-(PLATE - 0.05))
    PP(13.28, y1, FH + 3, 360 - FH - 3, POD_BELLY, ystep=1.3)
    # The conduit in the trench, three clips: the trench's own dark metal (shape, not paint).
    ca = (TR0 + TR1) / 2
    rings = []
    for y in frange(y0 + 0.2, 19.9, 0.6):
        x, _, z = pod_pt(y, ca, 0.1)
        rings.append([(x + dx, y, z + dz) for dx, dz in ((-0.1, 0.0), (0.0, 0.1), (0.1, 0.0), (0.0, -0.1))])
    ring_loft(D, rings, POD_CORE)
    for y in (16.6, 17.6, 18.6):
        x, _, z = pod_pt(y, ca, 0.1)
        hull(D, cbox(x - 0.17, x + 0.17, y - 0.07, y + 0.07, z - 0.12, z + 0.13, 0.04), POD_CORE)
    # Tail collar: the plates' end ring, no prouder than they are.
    plate(P, pod_loop, 19.98, POD_Y1 + 0.02, POD_TAIL, d=PLATE + 0.02, c=0.07, depth=0.12, ystep=0.3)
    # Stern: a closed bulkhead, a steel nozzle with a centre plug, a vernier each side. Unlit.
    pts, _ = pod_loop(POD_Y1)
    z0 = (max(z for _, z in pts) + min(z for _, z in pts)) / 2
    SU = [(x, z - z0) for x, z in pts]

    def circ(r):
        return [(r * math.sin(math.radians(a)), r * math.cos(math.radians(a))) for a in PA]
    yb = POD_Y1
    lathe(P, 0.0, z0, SU, [
        (1.0, 1.0, yb, POD_BELLY, "+y"),
        (0.93, 0.93, yb + 0.05, POD_BELLY, "+y"),
        (1.0, 1.0, yb + 0.05, NOZZLE, "out", circ(1.1)),
        (1.0, 1.0, yb + 0.1, NOZZLE, "+y", circ(1.1)),
        (1.0, 1.0, yb + 0.1, NOZZLE, "out", circ(0.98)),
        (1.0, 1.0, yb + 0.17, NOZZLE, "+y", circ(0.98)),
        (1.0, 1.0, yb + 0.17, NOZZLE, "in", circ(0.82)),
        (1.0, 1.0, yb - 0.4, THROAT, "+y", circ(0.68)),
        (1.0, 1.0, yb - 0.4, NOZZLE, "out", circ(0.34)),
        (0.0, 0.0, yb + 0.05, NOZZLE, "out"),
    ])
    # Louvre slats on the bulkhead either side of the nozzle.
    for sx in (-1, 1):
        for dz in (-0.3, 0.0, 0.3):
            hull(D, [(sx * x, y, z0 + dz + z) for x, y, z in cbox(1.22, 1.72, yb + 0.02, yb + 0.12, -0.07, 0.07, 0.03)],
                 POD_TAIL)
    return z0


# --- assembly -------------------------------------------------------------------------------------

def build(coll, mats):
    P = Part("uship_rails", smooth_angle=34)
    D = Part("uship_details", smooth_angle=35)
    for sx in (-1, 1):
        build_rail(P, D, sx)
    Q = Part("uship_pod", smooth_angle=34)
    G = Part("uship_glass", smooth_angle=50)
    build_pod(Q, D, G)
    B = Part("uship_hoop", smooth_angle=34)
    build_hoop(B)
    objs = [finish(p, mats, coll) for p in (P, D, Q, G)] + [finish(B, mats, coll, warp=hoop_warp)]
    for o in objs:
        print("u-ship part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = tuple(i for i in range(NSLOT) if i != GLASS)


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



# The game's pose for the banking frames: degrees of roll at half and full bank (D93), fitted to sprites
# 267-275 with tools/bank_roll.py. With the game's own shift (src/render/bankShift.ts) the frames
# measure 0.879 / 0.858 (half) and 0.765 / 0.758 (full) against bars of 0.80 / 0.70 (--fit would take
# 57.5 at full bank with a -3.5 px shift on frame 267 for 0.818 / 0.803; not needed to pass).
BANK_ROLL = [40, 55]
ENGINE_AT = (0.0, 20.65, 0.1)   # sprite px: just behind the nozzle (the menus' engine glow, src/ui/backdrop.ts)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    objs = build(coll, mats)
    obj = T.join(objs, NAME)
    # More directions than the Talon's 48: this ship's seams are narrow (0.06-0.15 px), and a core face
    # seen only through one is missed by a coarse fan and culled, which leaves a see-through slit.
    T.cull_hidden(obj, ndirs=192)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"u-ship: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glow: glTF axes (x, y up, z aft), orange (palette 121).
    ex, ey, ez = ENGINE_AT
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round((ex - 0.5) * PX, 4), round(ez * PX, 4),
                                                         round((ey - 14) * PX, 4)]]}
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
