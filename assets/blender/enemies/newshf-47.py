"""newshf-47 (newshf.shp frames 47/49/51, 24x28 px): the horned brown insect fighter.

Reading of the sprite (level frame 49, centred on column edge 13, nose = the point at the bottom,
flying down the screen):
- a brown armoured body (palette 22) from the thorax (row 4) to a pointed snout (row 25), round in
  section so it keeps its width when the craft rolls (rows 18-20 stay 6 px wide on every frame);
- a delta wing (rows 11-17, 18 px inside the ink): a grey metal frame plate (4) whose chamfered
  leading edge shows as the grey band along the lower edges, under a brown armour plate (21) inset
  from that edge, split by a modelled seam; the light line along the plate's edge is sheen on its
  chamfer;
- two grey shoulder pauldrons (5) at rows 5-8 with bolt heads and a seam;
- a dark grey vent housing (3) between the horn roots (rows 4-7) with slats, over a rear nozzle;
- two brown horns (25) from blade ridges (20) at columns 10 and 15, swept back and up to row 1;
- two red eyes (116, emissive) in dark sockets at row 12, columns 10 and 15;
- a dark mouth intake (1) framed by a brown lip at rows 16-18 with one fang (23) at column 12.
Underside: closed plain shapes only.

The frames roll the craft about its long axis: 49 level, 47 right side up, 51 left side up (the
wing narrows a pixel each side, the horns lean a pixel), so each frame gets the level model turned
by ROLL about the line u = 0, z = Z_AXIS.

    blender -b --factory-startup -P assets/blender/enemies/newshf-47.py [-- --roll DEG]

Exports public/models/enemies/newshf-47.glb (frame 47), -f2 (49), -f3 (51), each the model + its
outline shell, and registers them in src/render/spriteModels/.
Build coordinates: u = column edge - 13 (the craft's axis), y = row edge (down the screen), z up,
in sprite px; finish() maps to Blender X = (u + 1) / 12, Y = (14 - y) / 12, Z = z / 12.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parent.parent.parent
sys.path[:0] = [str(WT / "assets" / "blender")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshf-47"
TAG = "nshf47"
PX = 1 / 12
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ROLL = math.radians(float(ARGV[ARGV.index("--roll") + 1]) if "--roll" in ARGV else 16.0)
Z_AXIS = 0.3

# --- body stations (pchip): y, half width, top z, bottom z --------------------------------------
ST = [(3.9, 1.9, 1.5, -0.4), (4.6, 2.3, 1.9, -0.7), (5.6, 2.5, 2.1, -0.9), (7.0, 2.6, 2.3, -1.0),
      (8.5, 2.8, 2.4, -1.0), (9.6, 3.05, 2.55, -1.05), (10.6, 3.3, 2.75, -1.1), (12.5, 3.35, 2.95, -1.2),
      (14.5, 3.3, 2.9, -1.2), (16.5, 3.2, 2.7, -1.1), (18.0, 3.15, 2.5, -1.0), (19.5, 3.05, 2.2, -0.85),
      (20.7, 2.85, 1.95, -0.75), (22.0, 2.15, 1.55, -0.55), (23.5, 1.35, 1.1, -0.3), (24.7, 0.7, 0.75, -0.05),
      (25.45, 0.12, 0.45, 0.2)]
_ys = [s[0] for s in ST]
BW = T.pchip(_ys, [s[1] for s in ST])
BZT = T.pchip(_ys, [s[2] for s in ST])
BZB = T.pchip(_ys, [s[3] for s in ST])

# Section shape, right half from the top centre round to the bottom centre: (fraction of the half
# width, fraction of the height measured from the bottom). Chamfered facets, rounder on top.
SEC = [(0.0, 1.0), (0.42, 0.97), (0.74, 0.86), (0.93, 0.66), (1.0, 0.45), (0.95, 0.25), (0.72, 0.06),
       (0.35, 0.0)]


def body_loop(y, grow=0.0):
    w, zt, zb = BW(y), BZT(y), BZB(y)
    h = zt - zb
    # ring: top centre, round the right side, flat keel, back up the left side
    full = [(w * a, zb + h * b) for a, b in SEC] + [(-w * a, zb + h * b) for a, b in reversed(SEC)][:-1]
    c = (0.0, zb + h * 0.5)
    if grow:
        vn, _ = T.offset_loop(full, c)
        full = [(x + nx * grow, z + nz * grow) for (x, z), (nx, nz) in zip(full, vn)]
    return full, c


def body_top(u, y):
    """Height of the body's upper surface at (u, y) (on the section polyline)."""
    w, zt, zb = BW(y), BZT(y), BZB(y)
    h = zt - zb
    a = min(abs(u) / max(w, 1e-6), 1.0)
    for (a0, b0), (a1, b1) in zip(SEC, SEC[1:]):
        if a0 <= a <= a1 + 1e-9:
            f = (a - a0) / max(a1 - a0, 1e-9)
            return zb + h * (b0 + (b1 - b0) * f)
    return zb + h * 0.45


def body_normal(u, y):
    e = 0.05
    dzdu = (body_top(u + e, y) - body_top(u - e, y)) / (2 * e)
    dzdy = (body_top(u, y + e) - body_top(u, y - e)) / (2 * e)
    return Vector((-dzdu, -dzdy, 1.0)).normalized()


# --- mesh helpers --------------------------------------------------------------------------------

def inset(poly, d):
    """Inset a convex polygon [(u, y)] by d (edges moved inward, adjacent offset lines intersected)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / ln * s, dx / ln * s  # inward normal
        lines.append(((x0 + nx * d, y0 + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p, r), (q, t) = lines[i - 1], lines[i]
        den = r[0] * t[1] - r[1] * t[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        k = ((q[0] - p[0]) * t[1] - (q[1] - p[1]) * t[0]) / den
        out.append((p[0] + r[0] * k, p[1] + r[1] * k))
    return out


def chamfer_slab(P, poly, zb, zt, mat, cht=0.3, chb=0.2, d_top=None, zt_of=None, zb_of=None):
    """A convex chamfered slab: poly [(u, y)] between zb and zt (zt_of/zb_of(u, y) override per
    vertex, for wedges), 45-degree chamfers cht on top and chb underneath."""
    pts = []
    ti, bi = inset(poly, d_top if d_top is not None else cht), inset(poly, chb)
    for (u, y), (ut, yt), (ub, yb) in zip(poly, ti, bi):
        z1 = zt_of(u, y) if zt_of else zt
        z0 = zb_of(u, y) if zb_of else zb
        pts += [(ut, yt, z1), (u, y, z1 - cht), (u, y, z0 + chb), (ub, yb, z0)]
    T.hull(P, pts, mat)


def lathe(P, centre, axis, profile, sides, mats, phase=0.0):
    """Revolve profile [(r, h)] round axis through centre; mats[i] for segment i -> i + 1."""
    axis = Vector(axis).normalized()
    ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    a = (ref - axis * ref.dot(axis)).normalized()
    b = axis.cross(a)
    rows = []
    for r, h in profile:
        c = Vector(centre) + axis * h
        if r < 1e-6:
            rows.append([P.v(c)])
        else:
            rows.append([P.v(c + (a * math.cos(phase + 2 * math.pi * k / sides) +
                                  b * math.sin(phase + 2 * math.pi * k / sides)) * r) for k in range(sides)])
    for j, (r0, r1) in enumerate(zip(rows, rows[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            k = (i + 1) % n
            if len(r0) == 1:
                P.f((r0[0], r1[i], r1[k]), mats[j])
            elif len(r1) == 1:
                P.f((r0[i], r0[k], r1[0]), mats[j])
            else:
                P.f((r0[i], r0[k], r1[k], r1[i]), mats[j])
    if len(rows[0]) > 1:
        P.f(list(reversed(rows[0])), mats[0])
    if len(rows[-1]) > 1:
        P.f(rows[-1], mats[-1])


def sweep(P, pts, radii, sides, mat, flat=1.0, phase=0.5):
    """A tube through pts (Vectors) with per-point radius (0 = a point); `flat` squashes it in z."""
    pts = [Vector(p) for p in pts]
    ts = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        ts.append((b - a).normalized())
    up = Vector((0, 0, 1))
    rows = []
    for p, t, r in zip(pts, ts, radii):
        n = (up - t * up.dot(t)).normalized()
        bn = t.cross(n)
        if r < 1e-6:
            rows.append([P.v(p)])
            continue
        rows.append([P.v(p + (bn * math.cos(2 * math.pi * (k + phase) / sides) * r +
                              n * math.sin(2 * math.pi * (k + phase) / sides) * r * flat))
                     for k in range(sides)])
    for r0, r1 in zip(rows, rows[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            k = (i + 1) % n
            if len(r0) == 1:
                P.f((r0[0], r1[i], r1[k]), mat)
            elif len(r1) == 1:
                P.f((r0[i], r0[k], r1[0]), mat)
            else:
                P.f((r0[i], r0[k], r1[k], r1[i]), mat)
    if len(rows[0]) > 1:
        P.f(list(reversed(rows[0])), mat)
    if len(rows[-1]) > 1:
        P.f(rows[-1], mat)


def surface_block(P, u0, u1, y0, y1, off0, off1, mat, ch=0.12, nu=6, nv=6, ztop=None):
    """A block lying on the body: its footprint the rectangle u0..u1 x y0..y1, its faces following
    the body's upper surface (body_top, or ztop(u, y)) from off0 to off1 above it, the top edges
    chamfered by ch. A closed solid."""
    zs = ztop or body_top

    def rect_grid(a0, a1, b0, b1, off):
        return [[P.v((a0 + (a1 - a0) * i / nu, b0 + (b1 - b0) * j / nv,
                      zs(a0 + (a1 - a0) * i / nu, b0 + (b1 - b0) * j / nv) + off)) for i in range(nu + 1)]
                for j in range(nv + 1)]

    def boundary(g):
        loop = [g[0][i] for i in range(nu + 1)] + [g[j][nu] for j in range(1, nv + 1)]
        loop += [g[nv][i] for i in range(nu - 1, -1, -1)] + [g[j][0] for j in range(nv - 1, 0, -1)]
        return loop

    top = rect_grid(u0 + ch, u1 - ch, y0 + ch, y1 - ch, off1)
    mid = boundary(rect_grid(u0, u1, y0, y1, off1 - ch))
    bot_g = rect_grid(u0, u1, y0, y1, off0)
    bot = boundary(bot_g)
    for j in range(nv):
        for i in range(nu):
            P.f((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), mat)
            P.f((bot_g[j][i], bot_g[j + 1][i], bot_g[j + 1][i + 1], bot_g[j][i + 1]), mat)
    for r0, r1 in ((boundary(top), mid), (mid, bot)):
        n = len(r0)
        for i in range(n):
            k = (i + 1) % n
            P.f((r0[i], r0[k], r1[k], r1[i]), mat)


def mirror(P, start_vert):
    """Mirror everything built since vertex index start_vert about u = 0 (adds the copy)."""
    bm = P.bm
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    ret = bmesh.ops.duplicate(bm, geom=list(verts) + faces)
    for g in ret["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.x = -g.co.x
    bmesh.ops.reverse_faces(bm, faces=[g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)])


# --- parts ---------------------------------------------------------------------------------------

def build_body(P, BODY, NECK):
    grooves = (10.15, 19.25)  # panel seams: thorax / body, body / snout
    stations = [3.9, 4.25, 4.7, 5.3, 6.0, 6.8, 7.6, 8.4, 9.2, 9.8, 10.5, 11.3, 12.2, 13.2, 14.2, 15.2, 16.2,
                17.2, 18.2, 18.9, 19.6, 20.3, 21.0, 21.8, 22.6, 23.4, 24.1, 24.7, 25.1, 25.4]
    allst = [(s, 0.0) for s in stations if all(abs(s - g) > 0.3 for g in grooves)]
    for g in grooves:
        allst += [(g - 0.13, 0.0), (g - 0.1, -0.16), (g + 0.1, -0.16), (g + 0.13, 0.0)]
    allst.sort()
    rings = [(body_loop, y, gr) for y, gr in allst]
    mats = [BODY] * (len(rings) - 1)
    T.loft_rings(P, rings, mats)
    # rear nozzle under the vent housing (dark), pointing up the screen
    lathe(P, (0, 4.15, 0.45), (0, -1, 0),
          [(0.0, -0.2), (0.95, -0.2), (1.25, 0.0), (1.25, 0.28), (1.05, 0.35), (0.7, 0.35), (0.7, 0.1), (0.0, 0.1)],
          12, [NECK] * 7)


def build_neck(P, NECK):
    """Vent housing between the horn roots (the sprite's grey at cols 12-14 -> u -1..2, rows 4-7;
    col 11 is the brown thorax) with four slats."""
    zb = 0.6
    poly = [(-1.05, 4.0), (1.95, 4.0), (2.05, 4.6), (1.9, 7.35), (-0.95, 7.35), (-1.1, 4.6)]
    chamfer_slab(P, poly, zb, 2.35, NECK, cht=0.25, chb=0.1,
                 zt_of=lambda u, y: 2.35 if y < 6 else 2.55)
    for k in range(4):
        y0 = 4.45 + 0.7 * k
        T.hull(P, T.cbox(-0.7, 1.6, y0, y0 + 0.32, 2.2, 2.62 + 0.05 * k, 0.08), NECK)


def build_horns(P, HORN, RIDGE):
    s = len(P.bm.verts)
    u = -2.5
    # blade ridge down the thorax flank (col 10, rows 3-7) with a gusset towards the centre at row 3
    T.hull(P, [(u - 0.5, 3.3, 1.2), (u + 0.5, 3.3, 1.2), (u - 0.5, 3.3, 2.75), (u + 0.5, 3.3, 2.75),
               (u - 0.45, 7.6, 1.8), (u + 0.45, 7.6, 1.8), (u - 0.25, 7.6, 2.55), (u + 0.25, 7.6, 2.55),
               (u - 0.2, 3.05, 2.6), (u + 0.2, 3.05, 2.6), (u - 0.2, 3.05, 1.4), (u + 0.2, 3.05, 1.4)], RIDGE)
    T.hull(P, [(-2.7, 3.12, 1.5), (-0.8, 3.4, 1.5), (-0.8, 3.4, 2.15), (-2.7, 3.12, 2.55),
               (-2.7, 4.4, 1.5), (-0.8, 4.4, 1.5), (-0.8, 4.4, 2.25), (-2.7, 4.4, 2.65)], RIDGE)
    # the horn: a hexagonal spike from the ridge top, swept back (up the screen) and up
    pts = [(u, 4.4, 2.3), (u, 3.4, 2.72), (u, 2.4, 3.2), (u, 1.5, 3.68), (u, 0.9, 3.98), (u - 0.02, 0.5, 4.16)]
    sweep(P, pts, [0.74, 0.7, 0.62, 0.46, 0.3, 0.0], 6, HORN, flat=0.9, phase=0.0)
    # collar where the horn leaves the ridge
    lathe(P, (u, 3.75, 2.55), (0, -0.92, 0.4), [(0.0, -0.18), (0.82, -0.18), (0.9, -0.08), (0.9, 0.1), (0.76, 0.18), (0.0, 0.18)],
          6, [RIDGE] * 5, phase=0.0)
    mirror(P, s)


def build_pads(P, PAD, NECK):
    s = len(P.bm.verts)
    poly = [(-2.6, 4.3), (-4.05, 4.35), (-5.4, 4.95), (-6.02, 5.6), (-6.02, 6.55), (-3.25, 9.35),
            (-2.6, 9.3), (-2.5, 5.0)]
    # crown of the pauldron high on the inboard side, falling away outboard
    def zt(u, y):
        return 2.55 - 0.3 * max(0.0, -u - 3.0) - 0.25 * max(0.0, y - 7.5)
    chamfer_slab(P, poly, -0.75, 3.0, PAD, cht=0.45, chb=0.12, zt_of=zt)
    # seam: a second, smaller lower plate stepping out under the pad edge (the pad overlaps it)
    lower = [(-3.0, 7.2), (-5.0, 7.35), (-3.15, 9.6), (-2.8, 9.62)]
    chamfer_slab(P, lower, -0.6, 1.55, PAD, cht=0.25, chb=0.12)
    # two bolt heads on the pad crown
    for bu, by in ((-4.2, 5.5), (-4.6, 7.0)):
        z = zt(bu, by) - 0.05
        lathe(P, (bu, by, z), (0, 0, 1), [(0.0, 0.0), (0.36, 0.0), (0.36, 0.12), (0.24, 0.2), (0.0, 0.2)], 6,
              [NECK] * 4)
    mirror(P, s)


# Tip and leading edge sit just inside the level frame's pixel edges, so the frames' roll pulls
# them a pixel in at rows 11-14 as the sprite's 47/51 do, while the roll stays small.
LEFT_WING = [(-1.2, 10.25), (-4.4, 10.92), (-8.74, 10.97), (-8.76, 12.36), (-2.82, 18.62), (-1.2, 18.62)]


def build_wing(P, FRAME, WING):
    s = len(P.bm.verts)
    # grey frame plate: thicker at the root, a sharp chamfered leading edge
    def zt(u, y):
        return 0.55 - 0.02 * max(0.0, -u - 3.0)
    def zb(u, y):
        return -0.35 + 0.02 * max(0.0, -u - 3.0)
    chamfer_slab(P, LEFT_WING, 0, 0, FRAME, cht=0.12, chb=0.35, d_top=0.12, zt_of=zt, zb_of=zb)
    # brown armour plate, inset from the leading edge and the lower tip, split by a seam into a
    # root plate and a tip plate (the seam runs chordwise at u = -6.2)
    lead = lambda y: -(19.27 - y)  # noqa: E731  inset leading edge line (parallel to the frame's)
    root = [(-1.2, 10.3), (-4.4, 10.97), (-6.05, 10.99), (-6.05, 13.5), (lead(16.75), 16.75), (-1.2, 16.75)]
    root[4] = (lead(17.0), 17.0)
    root[5] = (-1.2, 17.0)
    tip = [(-6.35, 10.99), (-8.7, 10.99), (-8.72, 11.85), (-7.55, 11.85), (-6.35, 13.05)]
    def ztp(u, y):
        return 1.05 - 0.07 * max(0.0, -u - 3.0)
    chamfer_slab(P, root, 0.3, 0, WING, cht=0.32, chb=0.05, zt_of=ztp)
    chamfer_slab(P, tip, 0.3, 0, WING, cht=0.22, chb=0.05, zt_of=ztp)
    mirror(P, s)


def build_eyes(P, SOCK, EYE, roll=0.0):
    """Two eyes in sockets at row 12.5, seated so that once the frame's roll is applied they land
    on columns 10 and 15 (u = -/+2.5) like the sprite's, on every frame, facing up (towards the
    camera) rather than out along the flank. `roll` is the angle rolled() will turn this frame by."""
    y = 12.5
    ca, sa = math.cos(roll), math.sin(roll)
    up = Vector((-sa, 0.0, ca))  # the direction that ends up straight up after the roll
    for target in (-2.5, 2.5):
        lo, hi = -3.3, 3.3
        if target < 0:
            hi = 0.0
        else:
            lo = 0.0
        for _ in range(40):  # u of the body-top point whose rolled position is the target column
            m = (lo + hi) / 2
            if m * ca + (body_top(m, y) - Z_AXIS) * sa < target:
                lo = m
            else:
                hi = m
        u = (lo + hi) / 2
        z = body_top(u, y)
        n = (body_normal(u, y) * 0.35 + up * 0.65).normalized()
        c = Vector((u, y, z)) - n * 0.15
        lathe(P, c, n, [(0.0, -0.45), (0.95, -0.45), (0.95, 0.22), (0.8, 0.32), (0.62, 0.32), (0.62, 0.18), (0.0, 0.18)],
              10, [SOCK, SOCK, SOCK, SOCK, SOCK, SOCK])
        lathe(P, c + n * 0.18, n, [(0.58, 0.0), (0.56, 0.12), (0.42, 0.3), (0.2, 0.4), (0.0, 0.43)], 10,
              [EYE, EYE, EYE, EYE])


# The maw's outline on the snout (u, y): cols 11-14, rows 16-19, a little irregular like the sprite's
# dark pixels round the fang (wider on the right, a notch at the back by the fang root).
MAW = [(-1.0, 16.0), (-0.3, 16.25), (0.5, 15.95), (1.5, 16.15), (1.95, 16.85), (1.85, 17.9), (1.3, 18.75),
       (0.3, 19.05), (-0.8, 18.85), (-1.6, 18.2), (-1.95, 17.25), (-1.7, 16.35)]


def grow_poly(poly, d):
    cu = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for u, y in poly:
        du, dy = u - cu, y - cy
        ln = math.hypot(du, dy) or 1e-9
        out.append((u + du / ln * d, y + dy / ln * d))
    return out, (cu, cy)


def build_maw_cutter(P, MOUTH):
    """A closed cutter for the maw: wider at the top so the cut leaves a soft chamfered lip, its
    floor following the snout's curve 0.7 px down. Boolean-subtracted from the body."""
    top, c = grow_poly(MAW, 0.32)
    mid = MAW
    low, _ = grow_poly(MAW, -0.3)
    zs = lambda u, y: body_top(u, y)  # noqa: E731
    rings = [[P.v((u, y, zs(u, y) + 2.0)) for u, y in top],
             [P.v((u, y, zs(u, y) + 0.06)) for u, y in top],
             [P.v((u, y, zs(u, y) - 0.25)) for u, y in mid],
             [P.v((u, y, zs(u, y) - 0.62)) for u, y in low]]
    n = len(MAW)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            k = (i + 1) % n
            P.f((r0[i], r0[k], r1[k], r1[i]), MOUTH)
    P.f(rings[0], MOUTH)
    bc = P.v((c[0], c[1], zs(*c) - 0.72))
    for i in range(n):
        P.f((rings[-1][i], rings[-1][(i + 1) % n], bc), MOUTH)


def build_mouth(P, LIP, MOUTH, FANG):
    """Inside the maw: one fang (column 12) hanging forward from the back lip down into it, and a
    ridged throat plate low in the cavity."""
    y0 = 16.0
    zr = lambda y: body_top(-0.5, y)  # noqa: E731
    u = -0.5
    pts = [(u, y0 - 0.35, zr(y0 - 0.35) + 0.12), (u, 16.3, zr(16.3) + 0.12), (u, 17.1, zr(17.1) - 0.12),
           (u, 17.9, zr(17.9) - 0.32), (u, 18.5, zr(18.5) - 0.48)]
    sweep(P, pts, [0.5, 0.48, 0.38, 0.2, 0.0], 6, FANG, flat=0.75, phase=0.0)
    # throat: two dark gill ribs across the floor either side of the fang
    for a, b in ((-1.45, -1.0), (0.3, 1.35)):
        surface_block(P, a, b, 16.9, 18.1, -0.85, -0.5, MOUTH, ch=0.06, nu=2, nv=3)


def build_spine(P, BODY):
    """Dorsal armour strip on the crown (the light pixels at columns 12-13, rows 7-10) running
    forward between the eyes, and a chin plate on the snout (rows 19.5-22)."""
    surface_block(P, -0.95, 0.95, 6.9, 15.2, -0.25, 0.2, BODY, ch=0.14, nu=4, nv=10)
    surface_block(P, -1.05, 1.05, 19.6, 22.6, -0.25, 0.14, BODY, ch=0.1, nu=4, nv=5)


def finish(P, mats, coll, name):
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    return [
        pal(22, metallic=0.18, roughness=0.5),   # 0 body (region median 22)
        pal(21, metallic=0.18, roughness=0.52),   # 1 wing armour (21)
        pal(4, metallic=0.6, roughness=0.38),     # 2 wing frame / leading edge (4)
        pal(5, metallic=0.6, roughness=0.36),     # 3 shoulder pauldrons (5)
        pal(3, metallic=0.5, roughness=0.5),      # 4 vent housing, nozzle, bolts (3)
        pal(25, metallic=0.2, roughness=0.45),   # 5 horns (25)
        pal(20, metallic=0.2, roughness=0.5),   # 6 horn ridges (20)
        pal(116, emission_strength=3.0),          # 7 eyes
        pal(17, metallic=0.4, roughness=0.4),     # 8 eye sockets
        pal(1, metallic=0.2, roughness=0.6),      # 9 maw (1)
        pal(23, metallic=0.25, roughness=0.35),     # 10 fang (23)
    ]


BODY, WING, FRAME, PAD, NECK, HORN, RIDGE, EYE, SOCK, MOUTH, FANG = range(11)


def join_objs(objs, name, coll):
    """One mesh object from several (same material list, in order)."""
    bm = bmesh.new()
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in objs[0].data.materials:
        me.materials.append(mat)
    for o in objs:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(data)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def build(sprite, coll, name, roll=0.0):
    """The level model, with the eyes seated for a frame rolled by `roll` afterwards."""
    mats = materials(sprite)
    B = T.Part(name + "_body")
    build_body(B, BODY, NECK)
    body = finish(B, mats, coll, name + "_body")
    C = T.Part(name + "_cut")
    build_maw_cutter(C, MOUTH)
    cutter = finish(C, mats, coll, name + "_cut")
    mod = body.modifiers.new("maw", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.material_mode = "TRANSFER"
    dg = bpy.context.evaluated_depsgraph_get()
    cut = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    old = body.data
    body.modifiers.clear()
    body.data = cut
    bpy.data.meshes.remove(old)
    cdata = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(cdata)
    P = T.Part(name)
    build_neck(P, NECK)
    build_horns(P, HORN, RIDGE)
    build_pads(P, PAD, NECK)
    build_wing(P, FRAME, WING)
    build_eyes(P, SOCK, EYE, roll)
    build_mouth(P, BODY, MOUTH, FANG)
    build_spine(P, BODY)
    rest = finish(P, mats, coll, name + "_rest")
    return join_objs([body, rest], name, coll)


def rolled(obj, angle, suffix, coll):
    """A copy of obj turned about the long axis (X = 1/12, Z = Z_AXIS/12); positive lifts the left."""
    x0, z0 = PX, Z_AXIS * PX
    m = Matrix.Translation((x0, 0, z0)) @ Matrix.Rotation(angle, 4, "Y") @ Matrix.Translation((-x0, 0, -z0))
    c = obj.copy()
    c.data = obj.data.copy()
    c.data.transform(m)
    c.name = obj.name + suffix
    coll.objects.link(c)
    return c


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    frames = [f["index"] for f in sprite["frames"]]
    for k, angle in enumerate((-ROLL, 0.0, ROLL)):
        model = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build(sprite, coll, NAME if k == 1 else f"{NAME}_r{k + 1}", angle)
        shell = common.outline_shell(obj, coll)
        obj.data.calc_loop_triangles()
        print("frame", frames[k], "triangles", len(obj.data.loop_triangles), "shell", len(shell.data.polygons))
        if angle == 0:
            objs = [obj, shell]
        else:  # the rolled copies keep the names the single-build script gave them
            objs = [rolled(obj, angle, "", coll), rolled(shell, angle, "", coll)]
            for o in (obj, shell):
                data = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                bpy.data.meshes.remove(data)
            objs[0].name, objs[1].name = f"{NAME}_f{k + 1}", f"{NAME}_outline_f{k + 1}"
        common.export_sprite_model(WT, objs, f"enemies/{model}", frame_sprites(sprite, [frames[k]]))


def frame_sprites(sprite, indices):
    out = []
    for s in sprite["sprites"]:
        fr = [f for f in s["frames"] if f in indices]
        if fr:
            out.append({**s, "frames": fr})
    return out


if __name__ == "__main__":
    main()
