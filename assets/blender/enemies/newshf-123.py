"""newshf-123: the grey straight-winged jet (newshf.shp frames 123, 125, 127) as a hard-surface
aircraft, one model per sprite frame: newshf-123 (frame 123), -f2 (125) and -f3 (127).

Seen in episodes 1, 3 and 4 (6 levels). Damaged frames are a runtime effect (D86).

The sprite is authoritative (frame 125 is level, 123 / 127 rock it):
- Plan (inner edge of the ink border, D74), sprite px from the axis at column 12's centre:
  a round fuselage 3 px wide aft (rows 6-10) and along the radome (rows 20-23), 5 px wide from
  the wing root fillet (row 11) to a chamfered shoulder at row 20; a needle probe (rows 24-26);
  a straight wing, trailing edge row 12, tips at 9.2 px, its leading edge at row 16 outboard and
  curving forward inboard (row 17 at 6.5 px, row 18 at 3.5 px) into the intake trunks; a
  swept-leading-edge tailplane (rows 3-5, 5.15 px) and a fin raked back over the tail end to row 1.
- Features: the dark glass bubble canopy at rows 13-17 (3 px wide) with its windscreen bow, the
  fin top over the tail.
- Rock: 123 / 127 roll the whole craft 20 degrees about its axis, which narrows the wing and
  tailplane by a pixel a side and moves the fin top and canopy a pixel over, as the sprite does.
- Colours: the sprite's own index per region (trimmed medians, frame 125, darkest shading and
  sheen left out): fuselage 8 (its light spine 11 is sheen), wing 7, tailplane 6, fin 7, radome
  and probe 5, canopy glass 2 (dark, glossy); satin grey metal (metallic 0.2).

Hard surface: pchip lofts with superellipse sections and modelled panel-line grooves, airfoil
wings and tail with hinge-line grooves for flaps, ailerons, elevators and rudder, intake trunks
with recessed mouths, a jet nozzle with a dark recess, nose guns, a dorsal fairing and antenna,
a fin-top fairing. Underside: the plain closed hull. No concept projection: an AO / roughness bake
(usp_talon.bake_maps) and an outline shell (common.outline_shell, D51) per frame.

Exports public/models/enemies/newshf-123{,-f2,-f3}.glb and their src/render/spriteModels entries.

    blender --background --python assets/blender/enemies/newshf-123.py -- [--no-bake] [--frames 123,125]
            [--out dir]   (--out: export the .glb files there instead, for checks; no JSON entries)
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (pchip, frange, cull_hidden, bake_maps)

REPO = common.repo_root(__file__)
NAME = "newshf-123"
pchip, frange = T.pchip, T.frange

# frame, model, roll (degrees; + moves the top toward -x, the screen's left)
ROLL = 20.0
FRAMES = [(123, "newshf-123", ROLL), (125, "newshf-123-f2", 0.0), (127, "newshf-123-f3", -ROLL)]

# Materials (slots) and their palette index, metallic, roughness.
FUSE, WING, TAIL, FIN, NOSE, GLASS, FRAME, DEEP, DARK = range(9)
MATS = [(FUSE, 8, "fuse", 0.2, 0.42), (WING, 7, "wing", 0.2, 0.44), (TAIL, 6, "tail", 0.2, 0.44),
        (FIN, 7, "fin", 0.2, 0.42), (NOSE, 5, "nose", 0.2, 0.4), (GLASS, 2, "glass", 0.0, 0.07),
        (FRAME, 5, "frame", 0.45, 0.38), (DEEP, 1, "deep", 0.0, 0.85), (DARK, 3, "dark", 0.5, 0.45)]
TEXTURED = (FUSE, WING, TAIL, FIN, NOSE, FRAME, DARK)

# --- coordinates: sprite px, x right from the axis (column 12's centre), y = row (down the screen
# = forward), z up. Blender: X = (x + 0.5) / 12, Y = (14 - y) / 12, Z = z / 12.


def to_blender():
    return Matrix(((1 / 12, 0, 0, 0.5 / 12), (0, -1 / 12, 0, 14 / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))


def spow(v, p):
    return math.copysign(abs(v) ** p, v)


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def loft(self, rings, mats, cap0=None, cap1=None):
        """rings: lists of points (or one point: a pole); mats: int or per band; cap0 / cap1: the
        material of an end cap (None: open)."""
        vs = [[self.v(p) for p in r] for r in rings]
        for b in range(len(vs) - 1):
            r0, r1 = vs[b], vs[b + 1]
            m = mats if isinstance(mats, int) else mats[b]
            n = max(len(r0), len(r1))
            for i in range(n):
                j = (i + 1) % n
                if len(r0) == 1:
                    self.f((r0[0], r1[j], r1[i]), m)
                elif len(r1) == 1:
                    self.f((r0[i], r0[j], r1[0]), m)
                else:
                    self.f((r0[i], r0[j], r1[j], r1[i]), m)
        if cap0 is not None and len(vs[0]) > 2:
            self.f(list(reversed(vs[0])), cap0)
        if cap1 is not None and len(vs[-1]) > 2:
            self.f(vs[-1], cap1)
        return vs


def superellipse(cx, cz, w, ht, hb, n=24, e=2.2, y=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        pts.append((cx + w * spow(c, 2 / e), y, cz + (ht if s >= 0 else hb) * spow(s, 2 / e)))
    return pts


# --- fuselage ----------------------------------------------------------------------------------
FW = pchip([2.25, 2.5, 3.0, 6.0, 10.85, 11.45, 19.5, 20.4, 23.0, 23.7, 24.2, 24.45],
           [0.95, 1.25, 1.42, 1.45, 1.45, 2.48, 2.48, 1.45, 1.42, 1.15, 0.7, 0.3])
FT = pchip([2.25, 3.0, 6.0, 10.8, 11.6, 13.0, 17.5, 19.5, 20.4, 23.0, 23.7, 24.2, 24.45],
           [1.05, 1.3, 1.42, 1.48, 1.62, 1.72, 1.75, 1.7, 1.3, 1.2, 1.0, 0.65, 0.28])
FB = pchip([2.25, 3.0, 6.0, 10.8, 11.6, 13.0, 17.5, 19.5, 20.4, 23.0, 23.7, 24.2, 24.45],
           [0.95, 1.2, 1.35, 1.4, 1.6, 1.7, 1.7, 1.62, 1.2, 1.1, 0.9, 0.6, 0.28])
GROOVES = [5.2, 8.3, 21.6]   # panel joints round the fuselage
RADOME = 19.95               # nose material forward of the shoulder


def build_fuselage(M):
    ys = sorted(set([round(y, 3) for y in frange(2.25, 24.45, 0.95)]
                    + [10.85, 11.0, 11.15, 11.3, 11.45, 19.5, 19.7, 19.95, 20.15, 20.4]
                    + [g + d for g in GROOVES for d in (-0.14, 0.0, 0.14)]))
    rings, mats = [], []
    for y in ys:
        dip = 0.16 if any(abs(y - g) < 1e-6 for g in GROOVES) else 0.0
        rings.append(superellipse(0.0, 0.0, FW(y) - dip, FT(y) - dip, FB(y) - dip, n=20, y=y))
    for a, b in zip(ys, ys[1:]):
        mats.append(NOSE if (a + b) / 2 > RADOME else FUSE)
    # Tail end: a nozzle lip, then a dark recess.
    y0 = ys[0]
    lip = superellipse(0.0, 0.0, FW(y0) * 0.78, FT(y0) * 0.78, FB(y0) * 0.78, n=20, y=y0)
    deep = superellipse(0.0, 0.0, FW(y0) * 0.7, FT(y0) * 0.7, FB(y0) * 0.7, n=20, y=y0 + 0.7)
    M.loft([deep, lip] + rings + [[(0.0, 24.6, 0.0)]], [DEEP, DARK] + mats + [NOSE], cap0=DEEP)
    # Nozzle petals ring (a machined band just in front of the end).
    ring = [superellipse(0.0, 0.0, FW(y0 + d) + g, FT(y0 + d) + g, FB(y0 + d) + g, n=20, y=y0 + d)
            for d, g in ((0.05, 0.0), (0.1, 0.12), (0.55, 0.12), (0.62, 0.0))]
    M.loft(ring, DARK)


def build_probe(M):
    """The needle nose: a pitot / gun probe (rows 24-26)."""
    rs = [(23.6, 0.46), (24.4, 0.46), (24.5, 0.4), (26.2, 0.4), (26.35, 0.32), (26.8, 0.18), (27.0, 0.08)]
    rings = []
    for y, r in rs:
        rings.append([(r * math.cos(2 * math.pi * i / 12), y, r * math.sin(2 * math.pi * i / 12)) for i in range(12)])
    M.loft(rings, NOSE, cap0=NOSE, cap1=NOSE)


def build_guns(M):
    """Two gun barrels out of the fuselage's forward shoulder."""
    for sx in (-1, 1):
        x, z = sx * 1.55, -0.55
        rings = []
        for y, r in ((19.0, 0.22), (21.1, 0.22), (21.1, 0.12), (20.85, 0.12)):
            rings.append([(x + r * math.cos(2 * math.pi * i / 10), y, z + r * math.sin(2 * math.pi * i / 10))
                          for i in range(10)])
        M.loft(rings, [DARK, DARK, DEEP], cap0=DARK, cap1=DEEP)


# --- lifting surfaces --------------------------------------------------------------------------
_AF = [2.969 * math.sqrt(u) - 1.26 * u - 3.516 * u ** 2 + 2.843 * u ** 3 - 1.015 * u ** 4
       for u in [i / 200 for i in range(201)]]
_AFMAX = max(_AF)


def airfoil(u):
    u = min(1.0, max(0.0, u))
    return max(0.06, (2.969 * math.sqrt(u) - 1.26 * u - 3.516 * u ** 2 + 2.843 * u ** 3 - 1.015 * u ** 4) / _AFMAX)


def surface(M, stations, us, mat, groove):
    """A closed airfoil surface. stations: [(le, te, nrm, thickness, upper share)] with le / te 3D
    points and nrm the thickness direction; us: chord fractions from the leading edge (0) to the
    trailing edge (1); groove(i, u) -> depth cut into the upper skin (panel / hinge lines)."""
    top, bot = [], []
    for i, (le, te, n, t, up) in enumerate(stations):
        rt, rb = [], []
        for k, u in enumerate(us):
            p = [le[a] + (te[a] - le[a]) * u for a in range(3)]
            th = t * airfoil(u)
            g = groove(i, u)
            if k == 0:
                v = M.v(tuple(p))
                rt.append(v)
                rb.append(v)
                continue
            rt.append(M.v(tuple(p[a] + n[a] * (th * up - g) for a in range(3))))
            rb.append(M.v(tuple(p[a] - n[a] * th * (1 - up) for a in range(3))))
        top.append(rt)
        bot.append(rb)
    nu = len(us)
    for i in range(len(stations) - 1):
        for k in range(nu - 1):
            M.f((top[i][k], top[i][k + 1], top[i + 1][k + 1], top[i + 1][k]), mat)
            M.f((bot[i][k], bot[i + 1][k], bot[i + 1][k + 1], bot[i][k + 1]), mat)
        M.f((top[i][-1], bot[i][-1], bot[i + 1][-1], top[i + 1][-1]), mat)
    for i in (0, len(stations) - 1):
        ring = top[i] + list(reversed(bot[i][1:]))
        M.f(ring if i else list(reversed(ring)), mat)


def chord_us(extra=()):
    us = [0.5 - 0.5 * math.cos(math.pi * k / 8) for k in range(9)]
    return sorted(set([round(u, 4) for u in us] + list(extra)))


# Wing: trailing edge row 12, tips at 9.2 px, leading edge at row 16 outboard curving forward
# inboard into the intake trunks (row 17 at 6.5 px, row 18 at 3.5 px).
WS = 9.2
WLE = pchip([0.0, 1.5, 2.5, 3.0, 3.5, 4.2, 5.0, 5.6, 6.0, 6.5, 7.0, 7.6, 9.2],
            [18.6, 18.5, 18.25, 17.95, 17.55, 17.2, 17.0, 16.85, 16.65, 16.38, 16.12, 16.02, 16.0])
WTE = 12.04
WT = pchip([0.0, 2.5, 5.0, 9.2], [1.15, 1.05, 0.82, 0.58])
FLAP_U, AIL_S, FLAP_S0 = 0.73, 5.7, 3.7
SLAT_U, SLAT_S0 = 0.14, 6.9  # outboard leading-edge slat


def build_wing(M):
    ss = sorted(set([round(s, 3) for s in frange(-WS + 0.18, WS - 0.18, 0.95)]
                    + [sx * v for sx in (-1, 1) for v in (AIL_S - 0.1, AIL_S, AIL_S + 0.1, SLAT_S0, FLAP_S0 - 0.1,
                                                         FLAP_S0, FLAP_S0 + 0.1, WS - 0.4)]))
    ss = [-WS] + ss + [WS]
    us = chord_us((SLAT_U - 0.025, SLAT_U, SLAT_U + 0.025, FLAP_U - 0.025, FLAP_U, FLAP_U + 0.025))
    st = []
    for s in ss:
        a = abs(s)
        tip = 0.6 if a >= WS - 1e-6 else 1.0
        zc = -0.45 + 0.03 * a
        st.append(((s, WLE(a), zc), (s, WTE, zc + 0.04 * a / WS), (0, 0, 1), WT(a) * tip, 0.6))

    def groove(i, u):
        a = abs(ss[i])
        if a < FLAP_S0 - 0.15 or a > WS - 0.3:
            return 0.0
        if abs(u - FLAP_U) < 1e-4:
            return 0.17
        if abs(u - SLAT_U) < 1e-4 and a > SLAT_S0:
            return 0.12
        if u > FLAP_U and (abs(a - AIL_S) < 1e-4 or abs(a - FLAP_S0) < 1e-4):
            return 0.17
        return 0.0
    surface(M, st, us, WING, groove)


# Tailplane: trailing edge row 3, tips 5.15 px, leading edge swept forward inboard to the root.
TS = 5.15
TLE = pchip([0.0, 1.5, 2.5, 3.5, 4.0, 4.5, 5.15], [6.9, 6.35, 5.65, 4.95, 4.6, 4.3, 4.1])
TTE = 3.02
TT = pchip([0.0, 2.0, 5.15], [0.75, 0.62, 0.42])
ELEV_U = 0.62


def build_tail(M):
    ss = [-TS] + sorted(set([round(s, 3) for s in frange(-TS + 0.15, TS - 0.15, 1.0)] + [-1.6, -1.5, 1.5, 1.6])) + [TS]
    us = chord_us((ELEV_U - 0.03, ELEV_U, ELEV_U + 0.03))
    st = []
    for s in ss:
        a = abs(s)
        tip = 0.6 if a >= TS - 1e-6 else 1.0
        st.append(((s, TLE(a), 0.05), (s, TTE, 0.05), (0, 0, 1), TT(a) * tip, 0.55))

    def groove(i, u):
        a = abs(ss[i])
        if 1.5 < a < TS - 0.2 and abs(u - ELEV_U) < 1e-4:
            return 0.12
        return 0.0
    surface(M, st, us, TAIL, groove)


# Fin: root inside the fuselage, leading edge swept back, the top raked back over the tail end.
FIN_TOP = 3.75
RUD_U = 0.66


def build_fin(M):
    hs = frange(0.6, FIN_TOP, 0.45)
    le = pchip([0.6, 1.4, 2.4, FIN_TOP], [8.2, 7.2, 5.3, 3.75])
    te = pchip([0.6, 1.4, FIN_TOP], [2.75, 2.35, 1.15])
    th = pchip([0.6, FIN_TOP], [0.85, 0.5])
    us = chord_us((RUD_U - 0.03, RUD_U, RUD_U + 0.03))
    st = [((0.0, le(h), h), (0.0, te(h), h), (1, 0, 0), th(h), 0.5) for h in hs]

    def groove(i, u):
        return 0.1 if hs[i] > 1.6 and abs(u - RUD_U) < 1e-4 else 0.0
    surface(M, st, us, FIN, groove)
    # Fin-top fairing (an antenna pod) along the top, overhanging the tail end.
    pod = pchip([0.88, 1.0, 1.2, 3.2, 3.8, 4.2], [0.05, 0.3, 0.37, 0.37, 0.25, 0.05])
    rings = []
    for y in [0.88, 0.94, 1.0, 1.1, 1.2, 2.2, 3.2, 3.5, 3.8, 4.05, 4.2]:
        r = pod(y)
        rings.append([(r * math.cos(2 * math.pi * i / 12), y, FIN_TOP + 0.02 + r * math.sin(2 * math.pi * i / 12))
                      for i in range(12)])
    M.loft(rings, FIN, cap0=FIN, cap1=FIN)


# --- canopy, fairings --------------------------------------------------------------------------
CW = pchip([12.85, 13.2, 13.9, 15.4, 16.5, 17.1, 17.45], [0.3, 1.0, 1.4, 1.45, 1.32, 0.85, 0.15])
CT = pchip([12.85, 13.3, 14.4, 15.6, 16.5, 17.1, 17.45], [1.95, 2.55, 2.95, 2.98, 2.7, 2.25, 1.9])
CB = 0.9
BOW = (16.35, 16.6)


def can_ring(y, grow=0.0, n=14):
    w, t = CW(y) + grow, CT(y) + grow
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((w * math.cos(a), y, CB + (t - CB) * math.sin(a) ** 0.85))
    return pts


def build_canopy(M):
    ys = sorted(set([round(y, 3) for y in frange(12.85, 17.45, 0.4)] + list(BOW)))
    M.loft([[(0.0, 12.75, 2.0)]] + [can_ring(y) for y in ys] + [[(0.0, 17.55, 1.9)]], GLASS)
    # Windscreen bow and the rear frame: bands standing a hair proud of the glass.
    for y0, y1 in (BOW, (13.15, 13.35)):
        rings = [can_ring(y, g) for y, g in ((y0, 0.0), (y0 + 0.03, 0.08), (y1 - 0.03, 0.08), (y1, 0.0))]
        M.loft(rings, FRAME)


def build_dorsal(M):
    """A dorsal fairing behind the canopy down the spine, an antenna blade on it."""
    w = pchip([8.2, 9.2, 11.0, 13.2], [0.1, 0.6, 0.85, 0.95])
    t = pchip([8.2, 9.2, 11.0, 13.2], [1.45, 1.75, 1.95, 2.05])
    rings = [[(0.0, 8.05, 1.4)]]
    for y in frange(8.2, 13.2, 0.4):
        rings.append(superellipse(0.0, 0.9, w(y), t(y) - 0.9, 0.3, n=16, y=y))
    M.loft(rings, FUSE, cap1=FUSE)
    # antenna blade
    pts = [(-0.1, 9.6, 1.6), (0.1, 9.6, 1.6), (-0.1, 10.5, 1.8), (0.1, 10.5, 1.8),
           (-0.07, 9.75, 2.55), (0.07, 9.75, 2.55), (-0.07, 9.95, 2.55), (0.07, 9.95, 2.55)]
    hull(M, pts, DARK)


def hull(M, pts, mat):
    tmp = bmesh.new()
    vs = [tmp.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(tmp, input=vs)
    m = {}
    for v in tmp.verts:
        m[v] = M.v(v.co)
    for f in tmp.faces:
        M.f([m[v] for v in f.verts], mat)
    tmp.free()


def chamfer_rect(x0, x1, z0, z1, c, y):
    return [(x0 + c, y, z0), (x1 - c, y, z0), (x1, y, z0 + c), (x1, y, z1 - c),
            (x1 - c, y, z1), (x0 + c, y, z1), (x0, y, z1 - c), (x0, y, z0 + c)]


def build_intakes(M):
    """Intake trunks along the fuselage sides over the wing roots, the mouths at row 18."""
    for sx in (-1, 1):
        x0, x1 = 2.0, 3.52
        z0, z1 = -0.75, 0.95
        y_back, y_front = 12.6, 18.05

        def r(y, ins=0.0, top=z1):
            pts = chamfer_rect(x0 + ins, x1 - ins, z0 + ins, top - ins, 0.32, y)
            return [(sx * p[0], p[1], p[2]) for p in pts]
        rings = [r(y_back, 0.0, 0.5), r(y_back + 1.2, 0.0), r(y_front - 0.25, 0.0), r(y_front, 0.06),
                 r(y_front, 0.2), r(y_front - 0.7, 0.24)]
        if sx > 0:
            rings = [list(reversed(rr)) for rr in rings]
        M.loft(rings, [FUSE, FUSE, FUSE, DARK, DEEP], cap0=FUSE, cap1=DEEP)


# --- frame model -------------------------------------------------------------------------------

def materials(sprite, model):
    out = []
    for slot, idx, tag, met, rough in MATS:
        out.append(common.palette_material(sprite, idx, f"{model}_{tag}", metallic=met, roughness=rough))
    return out


def build_model(sprite, coll, model, roll):
    M = Mesh()
    build_fuselage(M)
    build_probe(M)
    build_guns(M)
    build_wing(M)
    build_tail(M)
    build_fin(M)
    build_canopy(M)
    build_dorsal(M)
    build_intakes(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    th = math.radians(roll)
    rot = Matrix(((math.cos(th), 0, -math.sin(th), 0), (0, 1, 0, 0), (math.sin(th), 0, math.cos(th), 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=to_blender() @ rot, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(model)
    bm.to_mesh(me)
    bm.free()
    for m in materials(sprite, model):
        me.materials.append(m)
    obj = bpy.data.objects.new(model, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    for p in me.polygons:
        if p.material_index in (DEEP,):
            p.use_smooth = False
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = None
    if "--frames" in argv:
        want = {int(v) for v in argv[argv.index("--frames") + 1].split(",")}
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    bake = "--no-bake" not in argv
    fmt = "WEBP" if bake else "AUTO"
    sprite = common.load_sprite(REPO, NAME)
    coll = common.reset_collection(NAME)
    for frame, model, roll in FRAMES:
        if want and frame not in want:
            continue
        obj = build_model(sprite, coll, model, roll)
        T.cull_hidden(obj, grid=3, ndirs=40)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"{NAME}: {model} {len(obj.data.polygons)} faces, {tris} triangles")
        if bake:
            tint, textured = T.TINT, T.TEXTURED
            T.TEXTURED = TEXTURED
            T.TINT = (1.0, 1.0, 1.0)  # neutral grey (Talon's blue lift is for its tan brass)
            try:
                T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{model}_bake_"), size=512, samples=64)
            finally:
                T.TINT, T.TEXTURED = tint, textured
            for img in bpy.data.images:
                if img.name in ("talon_colour", "talon_rm"):
                    img.name = img.name.replace("talon", model)
        shell = common.outline_shell(obj, coll, faces=1200)
        shell.name = shell.data.name = f"{model}_outline"
        if out_dir:
            common.export_glb([obj, shell], out_dir / f"{model}.glb", image_format=fmt)
        else:
            sprites = [{**s, "frames": [frame]} for s in sprite["sprites"] if frame in s["frames"]]
            common.export_sprite_model(REPO, [obj, shell], f"enemies/{model}", sprites, image_format=fmt)


if __name__ == "__main__":
    main()
