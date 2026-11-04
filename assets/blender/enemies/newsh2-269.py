"""Grey fork ship (newsh2.shp frame 269, 24x28, enemy type 24, flies nose right): a hard-surface
machine that is its sprite in 3D (the treatment of the player ships, PR #84 / D50-D53).

Seen in episode 1 (levels 1.28, 1.30, 1.36) and 3.17. One frame (269), one model.

Built with the usp_talon.py toolkit: chamfered armour plates standing proud of a dark core (panel
lines are real gaps), pchip plan stations, a modelled engine bay, hubs, rails and tail drum.

The sprite is authoritative (D52, the user's rule):
- Plan: a pchip egg for the fuselage (its outline ring included), the drum at columns 0-4 rows
  10-16, the spar at columns 1-3, the housings (columns 0-4, rows 4-7 / 19-22, rear outer corner
  cut), the diagonal struts, the round hubs at columns 7-8 and the rails along rows 2-4 / 22-24 to
  column 15. Mirror plane: row edge 13.5. Top-view IoU vs the sprite mask 0.995 (pixel centres).
- Features: two red grilles (columns 6 and 8, rows 12-14) with orange cores in the bay, the copper
  strap at row 13 columns 12-14, the nose-cone seam at column 20.5.
- Colours: per-region trimmed medians of the sprite (hull 6, nose 5, band 27, band flank 165,
  strut 23, hub 9, rail 6, drum 8, spar / bay 4, grille 119, core 121, copper 26). Satin metal.
- Underside: a plain closed belly (it is rarely seen).

Texture: no concept projection (its maps.json says "bake": "model", D50). Cycles bakes a colour
multiplier (ambient occlusion, edge lift) and a roughness/metalness map (usp_talon.bake_maps) to
assets/blender/textures/newsh2-269/bake/; Base Color = map x palette colour, so pal_<index>, fades
and the hit flash apply; the grilles keep their flat emissive colours. Exported beside it: an
outline shell (common.outline_shell, D51) and `tyrian_engines` (the two red exhausts in the tail
drum's rear face).

Local build frame (sprite px): lx = row edge - 13.5, ly = 24 - column edge (nose at ly 0), z up.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-269.py
     [-- --preview out.png] [--no-bake] [--out x.glb] [--measure m.json] [--renders dir]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, Section, cbox, frange, hull, pchip, plate  # noqa: E402

NAME = "newsh2-269"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

CORE, HULL, NOSE, DEEP, BAND, FLANK, STRUT, HUB, RAIL, DRUM, FRAME, GLOW, GCORE, COPPER, BELLY, RAIL_LT = range(16)
PAL_OF = {CORE: 4, HULL: 6, NOSE: 5, DEEP: 3, BAND: 27, FLANK: 165, STRUT: 23, HUB: 9, RAIL: 6, DRUM: 8,
          FRAME: 5, GLOW: 119, GCORE: 121, COPPER: 26, BELLY: 6, RAIL_LT: 7}
TEXTURED = (CORE, HULL, NOSE, DEEP, BAND, FLANK, STRUT, HUB, RAIL, DRUM, FRAME, COPPER, BELLY, RAIL_LT)
TINT = (1.0, 0.97, 0.88)


def materials(sprite):
    def pal(slot, tag, metallic, roughness, emit=0.0):
        return common.palette_material(sprite, PAL_OF[slot], f"{NAME}_{tag}", metallic=metallic,
                                       roughness=roughness, emission_strength=emit)
    return [
        pal(CORE, "core", 0.25, 0.5),
        pal(HULL, "hull", 0.3, 0.38),
        pal(NOSE, "nose", 0.32, 0.34),
        pal(DEEP, "recess", 0.1, 0.8),
        pal(BAND, "band", 0.2, 0.46),
        pal(FLANK, "flank", 0.25, 0.45),
        pal(STRUT, "strut", 0.3, 0.42),
        pal(HUB, "hub", 0.4, 0.3),
        pal(RAIL, "rail", 0.3, 0.38),
        pal(DRUM, "drum", 0.35, 0.34),
        pal(FRAME, "frame", 0.3, 0.42),
        pal(GLOW, "grille", 0.0, 0.4, emit=1.8),
        pal(GCORE, "grille_core", 0.0, 0.4, emit=2.4),
        pal(COPPER, "copper", 0.4, 0.32),
        pal(BELLY, "belly", 0.2, 0.5),
        pal(RAIL_LT, "rail_strip", 0.35, 0.32),
    ]


def E(e):
    """Column edge -> local ly."""
    return 24.0 - e


# --- the fuselage plan (blueprint pchip, outline ring included) ---------------------------------
# D74: the plan is the sprite's INNER mask (its 1 px ink ring left to the game's outline shell).
_PX = [3.7, 3.9, 4.5, 5.5, 6.5, 7.5, 9, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.5, 23.8, 24.0]
_PW = [0, 2.0, 3.4, 4.6, 5.6, 6.4, 6.5, 6.5, 6.0, 5.3, 4.5, 4.4, 3.9, 3.35, 2.5, 1.5, 0.55, 0.3, 0]
_PLAN = pchip(_PX, _PW)
PL = 0.28          # plate stand-off
TOP, BOT, SE = 0.8, 0.62, 2.4  # top / belly half height over half width, superellipse exponent
ZF = 2.6           # bay floor
BAY = (6.0, 12.0)  # bay columns
N = 24


def plan(e):
    return max(0.0, _PLAN(e))


def hull_loop_f(notched):
    def loop(ly, grow=0.0):
        e = E(ly)
        wp = max(0.35, plan(e))
        W = max(0.08, wp - PL)
        Ht = max(0.06, TOP * wp - PL)
        Hb = max(0.06, BOT * wp - PL)
        bx = min(2.5, 0.42 * W)

        def zs(u):
            u = min(1.0, abs(u))
            return Ht * (1 - u ** SE) ** (1 / SE)
        uc = min(0.66, bx / W + 0.35 / W)
        tc = math.asin(min(1.0, uc ** (SE / 2)))
        right = [(0.0, ZF if notched else zs(0)), (bx, ZF if notched else zs(bx / W))]
        for j in range(6):  # C .. equator (index 2 .. 7)
            t = tc + (math.pi / 2 - tc) * j / 5
            right.append((W * math.sin(t) ** (2 / SE), Ht * max(0.0, math.cos(t)) ** (2 / SE)))
        for j in range(1, 6):  # lower arc to keel (8 .. 12)
            t = math.pi / 2 + (math.pi / 2) * j / 5
            right.append((W * abs(math.sin(t)) ** (2 / SE), -Hb * abs(math.cos(t)) ** (2 / SE)))
        right[-1] = (0.0, -Hb)
        pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
        return pts, (0.0, (Ht - Hb) * 0.3)
    return loop


L = hull_loop_f(False)
LN = hull_loop_f(True)


def build_core(P):
    """The dark core loft, notched for the engine bay between columns 6 and 12."""
    rings = []  # (ly, notched)
    for ly in frange(0.4, E(BAY[1]), 1.0):
        rings.append((ly, False))
    rings.append((E(BAY[1]), True))
    for ly in frange(E(BAY[1]), E(BAY[0]), 0.75)[1:]:
        rings.append((ly, True))
    rings.append((E(BAY[0]), False))
    for ly in frange(E(BAY[0]), E(3.9), 0.4)[1:]:
        rings.append((ly, False))
    built = []
    prev = None
    for ly, notched in rings:
        pts, (cx, cz) = (LN if notched else L)(ly)
        verts = []
        for i, (x, z) in enumerate(pts):
            if prev is not None and abs(prev[0] - ly) < 1e-9:
                pv = prev[1][i]
                if (pv.co - Vector((x, ly, z))).length < 1e-6:
                    verts.append(pv)
                    continue
            verts.append(P.v((x, ly, z)))
        built.append((verts, (cx, ly, cz), ly, notched))
        prev = (ly, verts)
    for (r0, c0, y0, n0), (r1, c1, y1, n1) in zip(built, built[1:]):
        for a in range(N):
            b = (a + 1) % N
            if abs(y1 - y0) < 1e-9:  # step wall at the bay's front (ly 12) or rear (ly 18)
                out = (0, 1, 0) if n1 else (0, -1, 0)
                P.f((r0[a], r0[b], r1[b], r1[a]), CORE, out=out)
                continue
            both = n0 and n1
            if both and a in (0, N - 1):
                P.f((r0[a], r0[b], r1[b], r1[a]), DEEP, out=(0, 0, 1))
            elif both and a == 1:
                P.f((r0[a], r0[b], r1[b], r1[a]), CORE, out=(-1, 0, 0.25))
            elif both and a == N - 2:
                P.f((r0[a], r0[b], r1[b], r1[a]), CORE, out=(1, 0, 0.25))
            else:
                P.f((r0[a], r0[b], r1[b], r1[a]), CORE, away=c0)
    P.f(built[-1][0], CORE, out=(0, 1, 0))


def S2(side, a, b):
    return (a, b) if side > 0 else (N - b, N - a)


def build_plates(P, D):
    for side in (1, -1):
        def S(a, b, side=side):
            return S2(side, a, b)
        # Rear armour collar (columns 4.4-9.2): bronze over the shoulders, dark brown down the flank
        # and round under it, a raised dark rim along its front edge.
        plate(P, L, E(8.05), E(4.45), BAND, *S(2.06, 3.7), d=PL, c=0.12, ystep=1.1)
        plate(P, L, E(8.05), E(4.45), FLANK, *S(3.8, 10.45), d=PL, c=0.12, ystep=1.1)
        plate(P, L, E(9.6), E(8.15), FLANK, *S(2.06, 10.45), d=PL + 0.14, c=0.1, ystep=1)
        # Forward hull: upper plate (centre seam to upper flank), shoulder plate beside the bay,
        # the flank plate across the equator, the ring plate ahead of the lateral seam.
        plate(P, L, E(16.9), E(12.3), HULL, *S(0.05, 1.97), d=PL, c=0.12, ystep=1.1)
        plate(P, L, E(16.9), E(10.25), HULL, *S(2.06, 4.92), d=PL, c=0.12, ystep=1.1)
        plate(P, L, E(12.9), E(10.25), HULL, *S(5.0, 9.5), d=PL, c=0.12, ystep=1.1)
        plate(P, L, E(16.9), E(13.02), HULL, *S(5.0, 9.5), d=PL, c=0.12, ystep=1.1)
        plate(P, L, E(19.85), E(17.05), HULL, *S(0.05, 9.5), d=PL, c=0.12, ystep=1.1)
        # Flank louvres (seen from the side and the game camera).
        plate(P, L, E(15.7), E(12.9), DEEP, *S(5.25, 6.35), d=PL + 0.03, c=0.04, ystep=0.8)
        for k in (5.45, 5.8, 6.15):
            plate(P, L, E(15.55), E(13.05), CORE, *S(k - 0.06, k + 0.06), d=PL + 0.11, c=0.02, ystep=0.8)
        # An access hatch on the forward upper plate.
        plate(P, L, E(16.3), E(14.6), HULL, *S(2.5, 3.9), d=PL + 0.12, c=0.06, ystep=0.8)
    # Rear deck behind the bay, belly plates (plain: the underside is rarely seen).
    plate(P, L, E(5.85), E(4.45), HULL, -1.97, 1.97, d=PL, c=0.12, ystep=0.7)
    plate(P, L, E(9.6), E(4.45), BELLY, 10.55, 13.45, d=PL, c=0.12, ystep=1.1)
    plate(P, L, E(19.85), E(9.75), BELLY, 9.6, 14.4, d=PL, c=0.12, ystep=1.0)
    # Nose cone: two rings and the tip, the seam at column 20.5 (sprite's dark ring).
    plate(P, L, E(22.3), E(20.0), NOSE, d=PL, c=0.12, ystep=1.0)
    plate(P, L, E(23.55), E(22.42), NOSE, d=PL, c=0.1, ch0=False, ystep=0.6)
    sec = Section(L, E(23.55))
    tip = [sec.at(k, PL) for k in range(sec.n)]
    zc = sum(p[2] for p in tip) / len(tip)
    hull(P, tip + [(0.0, E(24.05), zc)], NOSE)
    # Copper strap over the centre seam ahead of the bay (row 13, columns 12-14).
    zt = TOP * plan(13.5)
    hull(D, cbox(-0.55, 0.55, E(15.05), E(12.25), zt - 0.4, zt + 0.2, 0.1), COPPER)
    for e in (12.6, 14.7):
        for x in (-0.3, 0.3):
            hull(D, box8(x - 0.1, x + 0.1, E(e + 0.1), E(e - 0.1), zt + 0.1, zt + 0.28), FRAME)


def box8(x0, x1, y0, y1, z0, z1):
    """Corner points of a plain box (for hull()), for parts too small to chamfer."""
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def tube(D, pts, r, mat, sides=6):
    """A closed tube through 3D points."""
    bm = bmesh.new()
    rings = []
    for i, p in enumerate(pts):
        p = Vector(p)
        a = Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])
        a.normalize()
        u = a.cross(Vector((0, 0, 1)))
        if u.length < 1e-3:
            u = a.cross(Vector((1, 0, 0)))
        u.normalize()
        v = a.cross(u)
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * v))
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            kk = (k + 1) % sides
            bm.faces.new((r0[k], r0[kk], r1[kk], r1[k]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    _copy(D, bm, [mat] * len(bm.faces))


def _copy(D, bm, mats):
    """Copy a closed temp bmesh into a Part with outward normals."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    vmap = {v: D.v(v.co.copy()) for v in bm.verts}
    for f, m in zip(bm.faces, mats):
        D.f([vmap[v] for v in f.verts], m, out=tuple(f.normal))
    bm.free()


def lathe(D, origin, axis, profile, sides=20, mats=None, phase=0.5):
    """A closed solid of revolution. profile: [(t along axis, r)], r 0 allowed at the ends;
    mats[i] for the band between profile points i and i + 1."""
    o, a = Vector(origin), Vector(axis).normalized()
    u = a.cross(Vector((0, 0, 1)))
    if u.length < 1e-3:
        u = a.cross(Vector((1, 0, 0)))
    u.normalize()
    v = a.cross(u)
    bm = bmesh.new()
    rings = []
    for t, r in profile:
        c = o + a * t
        if r < 1e-6:
            rings.append([bm.verts.new(c)])
        else:
            rings.append([bm.verts.new(c + r * (math.cos(2 * math.pi * (k + phase) / sides) * u
                                                + math.sin(2 * math.pi * (k + phase) / sides) * v))
                          for k in range(sides)])
    fm = []
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        m = mats[i] if mats else 0
        for k in range(sides):
            kk = (k + 1) % sides
            q = [r0[k % len(r0)], r0[kk % len(r0)], r1[kk % len(r1)], r1[k % len(r1)]]
            q = list(dict.fromkeys(q))
            if len(q) >= 3:
                bm.faces.new(q)
                fm.append(m)
    if len(rings[0]) > 1:
        bm.faces.new(rings[0])
        fm.append(mats[0] if mats else 0)
    if len(rings[-1]) > 1:
        bm.faces.new(list(reversed(rings[-1])))
        fm.append(mats[-1] if mats else 0)
    _copy(D, bm, fm)


def prism_pts(poly, z0, z1, ch):
    """Points of a chamfered prism over a convex polygon [(lx, ly)] (for hull())."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    pts = []
    for x, y in poly:
        dx, dy = x - cx, y - cy
        ln = math.hypot(dx, dy) or 1
        ix, iy = x - dx / ln * ch * 1.2, y - dy / ln * ch * 1.2
        pts += [(x, y, z0 + ch), (x, y, z1 - ch), (ix, iy, z0), (ix, iy, z1)]
    return pts


def build_bay(D):
    # Grille housings, the glowing grilles (sprite columns 6 and 8, rows 12-14) and their cores.
    hull(D, cbox(-1.95, 1.95, E(9.4), E(5.9), ZF - 0.2, ZF + 0.55, 0.12), FRAME)
    for e0, e1 in ((6.0, 7.05), (7.95, 9.0)):
        hull(D, cbox(-1.68, 1.68, E(e1 + 0.15), E(e0 - 0.15), ZF, 3.95, 0.1), FRAME)
        hull(D, cbox(-1.5, 1.5, E(e1), E(e0), 3.7, 4.12, 0.06), GLOW)
        hull(D, cbox(-0.55, 0.55, E(e1 - 0.22), E(e0 + 0.22), 4.0, 4.2, 0.05), GCORE)
        for x in (-0.66, 0.66):  # grille bars across the glow
            hull(D, box8(x - 0.07, x + 0.07, E(e1), E(e0), 3.9, 4.17), DEEP)
    # Machinery block behind them with a junction box, and two pipes into the bay's front wall.
    hull(D, cbox(-2.05, 2.05, E(11.85), E(9.55), ZF - 0.2, 3.55, 0.18), CORE)
    hull(D, cbox(-0.8, 0.8, E(11.3), E(9.9), 3.4, 3.95, 0.12), FRAME)
    for x in (-1.45, 1.45):
        tube(D, [(x, E(9.3), 3.4), (x, E(9.8), 3.85), (x, E(12.3), 3.85)], 0.3, FRAME)
    # Pipes over the shoulder in the gap between the collar and the forward plates.
    for side in (1, -1):
        for e, k0 in ((9.8, 2.25), (10.08, 2.35)):
            sec = Section(L, E(e))
            pts = [sec.at(s, 0.1) for s in frange(k0, 7.6, 0.9)]
            pts = [(side * x if side > 0 else -abs(x), y, z) for x, y, z in pts]
            tube(D, pts, 0.15, FRAME, sides=5)


def build_tail(D):
    # The drum: rear ring, waist, front ring, its axis along the ship; a dished rear face with two
    # red exhausts.
    prof = [(0.38, 0.0), (0.38, 2.45), (0.05, 2.75), (0.05, 3.1), (0.28, 3.41), (1.42, 3.41), (1.65, 3.12),
            (1.65, 2.6), (2.65, 2.6), (2.65, 3.12), (2.88, 3.41), (4.42, 3.41), (4.65, 3.12), (4.65, 0.0)]
    DR = 0.84  # D74: drum radius scale (inner mask)
    prof = [(t, r * DR) for t, r in prof]
    mats = [DEEP, CORE, DRUM, DRUM, DRUM, DRUM, CORE, CORE, CORE, DRUM, DRUM, DRUM, DRUM]
    lathe(D, (0.0, E(0.0), 0.0), (0, -1, 0), prof, sides=16, mats=mats)
    # Raised bands on the rings and bolt heads round the rear ring.
    lathe(D, (0.0, E(0.0), 0.0), (0, -1, 0), [(0.6, 3.3 * DR), (0.6, 3.52 * DR), (1.05, 3.52 * DR), (1.05, 3.3 * DR)],
          sides=16, mats=[DRUM, DRUM, DRUM])
    lathe(D, (0.0, E(0.0), 0.0), (0, -1, 0), [(3.4, 3.3 * DR), (3.4, 3.52 * DR), (3.85, 3.52 * DR), (3.85, 3.3 * DR)],
          sides=16, mats=[DRUM, DRUM, DRUM])
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        lathe(D, (2.9 * DR * math.cos(a), E(0.0), 2.9 * DR * math.sin(a)), (0, -1, 0),
              [(-0.08, 0.0), (-0.08, 0.17), (0.12, 0.17)], sides=5, mats=[FRAME, FRAME])
    for x in (-1.25, 1.25):
        lathe(D, (x, E(0.0), 0.25), (0, -1, 0),
              [(0.45, 0.0), (0.45, 0.95), (0.0, 0.95), (0.0, 0.72), (0.18, 0.72), (0.18, 0.0)],
              sides=12, mats=[DEEP, DEEP, DEEP, DEEP, GLOW])
    # The spar: a chamfered beam across the ship through the drum, into the housings.
    # Cross beam inside the drum's width, and a diagonal brace each side up to the housing.
    hull(D, cbox(-3.4, 3.4, E(4.0), E(1.0), -1.0, 1.0, 0.25), CORE)
    for sx in (-1, 1):
        hull(D, cbox(sx * 4.2 - 0.5, sx * 4.2 + 0.5, E(3.0), E(2.0), -0.9, 0.9, 0.2), CORE)
        pts = cbox(sx * 5.9 - 0.45, sx * 5.9 + 0.45, E(2.6), E(1.9), -1.0, 1.0, 0.2) + \
            cbox(sx * 3.9 - 0.45, sx * 3.9 + 0.45, E(3.8), E(3.1), -1.0, 1.0, 0.2)
        hull(D, pts, CORE)


def build_arms(D):
    for sx in (-1, 1):
        def X(a, b, sx=sx):
            return (min(sx * a, sx * b), max(sx * a, sx * b))
        # Housing (columns 0-4, rows 4-7): rear outer corner cut, inner front corner cut.
        poly = [(8.5, 0.7), (8.5, 4.9), (7.0, 4.0), (5.9, 3.0), (5.9, 1.0), (6.5, 0.7)]
        hull(D, prism_pts([(sx * x, E(e)) for x, e in poly], -1.6, 1.7, 0.3), STRUT)
        cap = [(6.8, 1.2), (8.2, 0.9), (8.2, 3.6), (7.4, 4.0), (6.8, 3.0)]
        hull(D, prism_pts([(sx * x, E(e)) for x, e in cap], 1.5, 1.95, 0.12), STRUT)
        # Strut: a diagonal beam from the housing's front to the hub.
        pts = cbox(*X(7.2, 8.7), E(4.9), E(3.0), -0.85, 1.45, 0.25) + cbox(*X(9.45, 10.8), E(6.8), E(5.2), -0.85, 1.45, 0.25)
        hull(D, pts, STRUT)
        pts = cbox(*X(7.7, 8.5), E(4.6), E(3.6), 1.3, 1.62, 0.1) + cbox(*X(9.4, 10.6), E(6.4), E(5.6), 1.3, 1.62, 0.1)
        hull(D, pts, STRUT)
        # Hydraulic ram along the strut's outer side.
        tube(D, [(sx * 9.9, E(4.3), -0.15), (sx * 10.1, E(5.9), -0.15)], 0.25, RAIL_LT, sides=8)
        # Rail: main bar, top strip, collar groove, tip block, blade.
        hull(D, cbox(*X(9.15, 10.85), E(12.85), E(5.0), -0.8, 1.0, 0.3), RAIL)
        hull(D, cbox(*X(9.4, 10.6), E(12.55), E(9.6), 0.85, 1.18, 0.1), RAIL)
        hull(D, box8(*X(9.15, 10.85), E(13.32), E(12.83), -0.6, 0.72), DEEP)
        hull(D, cbox(*X(9.1, 10.9), E(14.3), E(13.3), -0.95, 1.35, 0.3), RAIL)
        for e in (13.75, 14.55):
            lathe(D, (sx * 10.0, E(e), 1.3), (0, 0, 1), [(-0.05, 0.0), (-0.05, 0.2), (0.12, 0.2), (0.12, 0.0)],
                  sides=6, mats=[FRAME, FRAME, FRAME])
        blade = []
        for x0, x1, e, z0, z1 in ((9.15, 10.85, 14.3, -0.55, 1.1), (9.1, 10.9, 14.98, -0.3, 0.2)):
            blade += [(sx * x0, E(e), z0), (sx * x1, E(e), z0), (sx * x0, E(e), z1), (sx * x1, E(e), z1)]
        blade += [(sx * 9.08, E(14.75), 0.55), (sx * 10.92, E(14.75), 0.55)]
        hull(D, blade, HUB)
        # Hub: a round boss at columns 6-9 with a slotted bolt cap.
        lathe(D, (sx * 10.0, E(8.0), 0.0), (0, 0, 1),
              [(-1.1, 0.0), (-1.1, 0.85), (-0.88, 1.0), (1.32, 1.0), (1.55, 0.85), (1.55, 0.0)],
              sides=14, mats=[HUB] * 5)
        lathe(D, (sx * 10.0, E(8.0), 0.0), (0, 0, 1), [(1.45, 0.0), (1.45, 0.3), (1.88, 0.3), (1.98, 0.25), (1.98, 0.0)],
              sides=10, mats=[CORE] * 4)
        hull(D, box8(sx * 10.0 - 0.3, sx * 10.0 + 0.3, E(8.06), E(7.94), 1.9, 2.02), DEEP)


def build(coll, sprite):
    mats = materials(sprite)
    core = Part("fork_core", smooth_angle=35)
    build_core(core)
    plates = Part("fork_plates", smooth_angle=35)
    det = Part("fork_details", smooth_angle=35)
    build_plates(plates, det)
    build_bay(det)
    build_tail(det)
    arms = Part("fork_arms", smooth_angle=35)
    build_arms(arms)
    return [T.finish(p, mats, coll) for p in (core, plates, det, arms)]


def to_sprite_frame(obj):
    """finish() maps (lx, ly) to (lx / 12, (14 - ly) / 12); turn that into the sprite's frame:
    X = (column edge - 12) / 12, Y = (14 - row edge) / 12."""
    m = Matrix(((0, 1, 0, -2 * PX), (-1, 0, 0, 0.5 * PX), (0, 0, 1, 0), (0, 0, 0, 1)))
    obj.data.transform(m)
    obj.data.update()


def bake_maps(obj, out_dir, size=1024, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", NAME)


# --- measuring ----------------------------------------------------------------------------------

def measure(obj, sprite, out):
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, deps)
    me = obj.data
    mat_pal = [int(m.name.split("_")[1]) for m in me.materials]
    fr = sprite["frames"][0]
    grid = fr["pixels"]
    h, w = len(grid), len(grid[0])

    def hit(c, r):
        x, y = (c - w / 2) / 12, (h / 2 - r) / 12
        loc, nrm, idx, dist = tree.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)), 20.0)
        if loc is None:
            return None
        return mat_pal[me.polygons[idx].material_index]
    centre = [[hit(c + 0.5, r + 0.5) for c in range(w)] for r in range(h)]
    sub = 6
    cov = [[sum(hit(c + (i + 0.5) / sub, r + (j + 0.5) / sub) is not None for i in range(sub) for j in range(sub)) / sub ** 2
            for c in range(w)] for r in range(h)]
    m_s = [[grid[r][c] >= 0 for c in range(w)] for r in range(h)]
    m_m = [[centre[r][c] is not None for c in range(w)] for r in range(h)]
    inter = sum(m_s[r][c] and m_m[r][c] for r in range(h) for c in range(w))
    union = sum(m_s[r][c] or m_m[r][c] for r in range(h) for c in range(w))
    ai = sum(min(cov[r][c], float(m_s[r][c])) for r in range(h) for c in range(w))
    au = sum(max(cov[r][c], float(m_s[r][c])) for r in range(h) for c in range(w))
    # Anything outside the grid?
    rows = []
    for r in range(h):
        sc = [c for c in range(w) if m_s[r][c]]
        mc = [c for c in range(w) if m_m[r][c]]
        rows.append({"r": r, "sprite": len(sc), "model": len(mc), "sl": min(sc, default=-1), "sr": max(sc, default=-1),
                     "ml": min(mc, default=-1), "mr": max(mc, default=-1)})
    missed = [[c, r] for r in range(h) for c in range(w) if m_s[r][c] and not m_m[r][c]]
    extra = [[c, r] for r in range(h) for c in range(w) if m_m[r][c] and not m_s[r][c]]
    # Region colours (the blueprint's prep.py classes).
    col = {int(k): v for k, v in sprite["colors"].items()}
    lum = lambda i: sum(col.get(i, (0, 0, 0))) / 3  # noqa: E731
    BROWN, DB, RED = set(range(16, 32)), set(range(160, 168)), {118, 119, 120, 121}

    def region(c, r, v):
        if v < 0 or v == 2:
            return None
        if v in RED:
            return "core" if v == 121 else "grille"
        yy = min(r, 26 - r)
        if c <= 6 and yy <= 6 and v in BROWN:
            return "strut"
        if yy <= 4 and 7 <= c <= 8:
            return "hub"
        if yy <= 4 and c >= 5:
            return "strut" if v in BROWN else "rail"
        if c <= 4 and yy >= 3 and v not in BROWN | DB:
            return "drum" if 10 <= r <= 16 else "spar"
        if v in DB:
            return "band_flank"
        if v in BROWN and c <= 9:
            return "band"
        if r == 13 and 12 <= c <= 14:
            return "copper"
        if 6 <= c <= 11 and 11 <= r <= 15:
            return "bay"
        if c >= 20:
            return "nose"
        return "hull"

    def tmed(vals):
        s = sorted(vals, key=lum)
        n = len(s)
        t = n // 6 if n >= 6 else 0
        core = s[t:n - t] or s
        return core[len(core) // 2]
    regions = {}
    for r in range(h):
        for c in range(w):
            k = region(c, r, grid[r][c])
            if k:
                regions.setdefault(k, ([], []))
                regions[k][0].append(grid[r][c])
                if centre[r][c] is not None:
                    regions[k][1].append(centre[r][c])
    reg = {}
    for k, (sv, mv) in regions.items():
        reg[k] = {"sprite": tmed(sv), "model": tmed(mv) if mv else None, "n": len(sv),
                  "model_counts": {str(i): mv.count(i) for i in sorted(set(mv))}}
    per = {}
    for p in me.polygons:
        k = me.materials[p.material_index].name
        per[k] = per.get(k, 0) + len(p.vertices) - 2
    print("tris per material", sorted(per.items(), key=lambda kv: -kv[1]))
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    res = {"iou_pixel_centres": inter / union, "iou_area": ai / au, "missed": missed, "extra": extra, "rows": rows,
           "regions": reg, "model_grid": centre, "coverage": cov,
           "bounds_px": [[min(xs) * 12, max(xs) * 12], [min(ys) * 12, max(ys) * 12], [min(zs) * 12, max(zs) * 12]],
           "faces": len(me.polygons), "tris": sum(len(p.vertices) - 2 for p in me.polygons)}
    Path(out).write_text(json.dumps(res))
    print(f"IoU centres {res['iou_pixel_centres']:.3f} area {res['iou_area']:.3f} tris {res['tris']}")
    for k, v in reg.items():
        print(f"  {k:11s} sprite {v['sprite']:4d} model {v['model']}  {v['model_counts']}")


# --- renders ------------------------------------------------------------------------------------

def renders(objs, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o not in objs:
            o.hide_render = True
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs[1].default_value = 1.0
    # Key light from the top left of the screen (the sprites' light), a fill and a rim.
    for name, rot, energy in (("key", (math.radians(40), math.radians(-25), math.radians(-30)), 4.0),
                              ("fill", (math.radians(60), math.radians(40), math.radians(140)), 0.9),
                              ("rim", (math.radians(110), 0, math.radians(90)), 1.0)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(8)
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.rotation_euler = rot

    def cam(name, loc, ortho=None, look=(0, 0, 0), lens=60, up="Y"):
        cd = bpy.data.cameras.new(name)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        else:
            cd.lens = lens
        co = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(co)
        co.location = loc
        co.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", up).to_euler()
        scene.camera = co
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    s = 2.6
    cam("top", (0, 0, 8), ortho=28 / 12 * 1.0)
    cam("side", (0, -8, 0), ortho=s, up="Z")
    cam("front", (8, 0, 0), ortho=s, up="Z")
    cam("rear", (-8, 0, 0), ortho=s, up="Z")
    cam("under", (0, 0, -8), ortho=s)
    d = 6.0
    cam("q34_front", (d * 0.62, -d * 0.6, d * 0.5), lens=70, up="Z")
    cam("q34_rear", (-d * 0.62, d * 0.6, d * 0.5), lens=70, up="Z")
    cam("game", (0, -d * 0.55, d * 0.85), lens=70, up="Z")
    cam("low_side", (d * 0.2, -d * 0.9, d * 0.12), lens=70, up="Z")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    to_sprite_frame(obj)
    T.cull_hidden(obj)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    if "--measure" in argv:
        measure(obj, sprite, argv[argv.index("--measure") + 1])
    # Engine glows (src/ui/backdrop.ts): the two red exhausts in the drum's rear face (rows 12.25 and
    # 14.75, column edge 0.2, z 0.25 px), in glTF axes (x, y up, z = -Blender Y).
    obj["tyrian_engines"] = {"color": "#ff3a1c", "at": [
        [round((0.2 - 12) * PX, 4), round(0.25 * PX, 4), round(-(14 - r) * PX, 4)] for r in (12.25, 14.75)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir, size=1024, samples=64)
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(obj, coll, voxel=0.016, faces=1500, smooth=16)
    shell.name = shell.data.name = f"{NAME}_outline"
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    shell.hide_render = True
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])
    if "--renders" in argv:
        renders([obj], argv[argv.index("--renders") + 1])


if __name__ == "__main__":
    main()
