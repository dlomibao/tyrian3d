"""Grey pincer drone (newshd.shp frame 121, 24x28, one frame), design A: a hard-surface claw drone.

Identity (D122 audit, QA2 issue 13): a FLYING drone (spawned on all four layers, moving 2 px/tick down and 4
sideways), so it floats: the prongs reach forward level from the shoulder knuckles (no tips planted on the
ground), there is no stalk or pedestal, and the pod's belly is its round closed underside.

Reading of the sprite (inner mask: the ink ring is the game's own outline, D74):
- Head (rows 1-6, columns 6-15): a domed sensor pod, highest at the back (the bright row 2 is the
  lit crown, the dark row 1 the rear slope falling away), its face sloping forward down to a chin
  lip (row 6, bright). Shell pal 7 on top, pal 6 on the cheeks and lower body, split by modelled
  panel seams; a transverse seam behind the crown.
- Visor (rows 3-5, columns 8-13): a raised dark frame (pal 4) round a recessed red glass slit
  (row 4, pal 119) with the hot orange scanner eye at its left end (column 9, pal 121): satin red metal
  under a constant 0.42-0.5 grey multiplier, no emission, so tone mapping keeps it saturated (fix round 1).
- Neck (row 7): a dark core block (pal 6) between two bright hydraulic rods (columns 9 and 12,
  pal 10).
- Yoke (rows 8-9): a transverse axle housing (pal 5) with a dark centre bearing cap (columns
  10-11, pal 4) and, at its ends, the two shoulder knuckles (rows 9-10, pal 9) the prongs pivot on.
- Prongs (rows 9-24): chamfered octagonal beams (pal 8) that leave the knuckles, flare out into a
  forearm (rows 12-16, armour plate on top) with an inner jaw: an upper jaw block and a lowered
  serrated grip notch (rows 14-15, pal 4), then narrow to a finger that bows out and hooks back
  in, ending in a hardened claw tip (rows 21-24, pal 6) that curls only slightly down. The bright
  pixels down column 5 / 15 are sheen on the beam's chamfer, not geometry.
- Underside: the pod's round closed belly and the prongs' own undersides; nothing below. No detail.

Mirror symmetric about pixel edge 11.

    Blender --background --factory-startup --python assets/blender/enemies/newshd-121.py -- [--views DIR] [--no-bake]

Exports public/models/enemies/newshd-121.glb (model + outline shell, D51) and the spriteModels entry.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/object-minor/newshd-121/final")
NAME = "newshd-121"
FRAME = 121
PX = 1 / 12
AX = 11.0  # mirror axis (pixel edge)

# Material slots -> palette index.
TOP, SIDE, SEAM, FRAME_, GLASS, EYE, CHIN, ROD, CORE, AXLE, KNUCK, PRONG, TIP = range(13)
PAL_OF = {TOP: 7, SIDE: 6, SEAM: 4, FRAME_: 4, GLASS: 119, EYE: 121, CHIN: 9, ROD: 9, CORE: 6,
          AXLE: 5, KNUCK: 9, PRONG: 8, TIP: 6}
GLOWS = {}  # no emission on the visor: any glow tone-maps the red to near-white pink in game (fix round 1)
# The visor glass and eye keep their palette colour (119, 121) but are satin metal (metallic 1,
# roughness 0.7: no white dielectric sheen, the straight-down view no longer mirrors the room light)
# under a constant grey Base Color multiplier, so they stay under the tone-mapping shoulder and read
# saturated red / orange like the sprite instead of washed-out pink. Measured in ?viewer: top
# (238,35,23), game angle (193,16,0) vs the sprite's (211,20,0).
DIM = {GLASS: 0.42, EYE: 0.5}

pchip = T.pchip


def W(p):
    """sprite px (x = column edge, y = row edge, z up) -> Blender units."""
    return Vector(((p[0] - 12) * PX, (14 - p[1]) * PX, p[2] * PX))


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(W(p))

    def f(self, vs, mat):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face


def tube(M, rings, mats, cap0=True, cap1=True):
    """Connect rings (lists of verts, equal length; a 1-vert ring is a point)."""
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        mat = mats(i) if callable(mats) else mats
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                M.f((r0[0], r1[j], r1[k]), mat if not callable(mat) else mat(k))
            elif len(r1) == 1:
                M.f((r0[k], r0[j], r1[0]), mat if not callable(mat) else mat(k))
            else:
                M.f((r0[k], r0[j], r1[j], r1[k]), mat if not callable(mat) else mat(k))
    m0 = mats(0) if callable(mats) else mats
    m1 = mats(len(rings) - 2) if callable(mats) else mats
    if cap0 and len(rings[0]) > 2:
        M.f(list(reversed(rings[0])), m0 if not callable(m0) else m0(0))
    if cap1 and len(rings[-1]) > 2:
        M.f(rings[-1], m1 if not callable(m1) else m1(0))


def hull(M, pts, mat):
    """Convex hull of px points (a chamfered block)."""
    bm = M.bm
    vs = [M.v(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in vs if v.is_valid for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None):
    return T.cbox(x0, x1, y0, y1, z0, z1, ch, chz)


def cyl(M, a, b, r, sides, mat, bevel=0.0, cap_mat=None):
    """A cylinder from px point a to b, radius r, ends chamfered by `bevel`."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    w = d.cross(u).normalized()
    L = (b - a).length
    prof = [(0, r - bevel), (bevel, r), (L - bevel, r), (L, r - bevel)] if bevel else [(0, r), (L, r)]
    rings = []
    for t, rr in prof:
        rings.append([M.v(tuple(a + d * t + (u * math.cos(2 * math.pi * (k + 0.5) / sides)
                                              + w * math.sin(2 * math.pi * (k + 0.5) / sides)) * rr))
                      for k in range(sides)])
    cm = mat if cap_mat is None else cap_mat
    tube(M, rings, mat, cap0=False, cap1=False)
    M.f(list(reversed(rings[0])), cm)
    M.f(rings[-1], cm)


# --- the head pod ----------------------------------------------------------------------------------

PY = [0.95, 1.3, 2.0, 2.6, 3.5, 4.5, 5.5, 6.3, 7.0, 7.3]
POD_W = pchip(PY, [1.3, 2.3, 3.55, 4.2, 4.85, 5.0, 4.85, 4.3, 3.4, 2.6])
POD_ZT = pchip(PY, [5.6, 6.9, 8.3, 8.85, 8.8, 8.3, 7.4, 6.5, 5.6, 5.1])
POD_ZB = pchip(PY, [3.7, 2.6, 1.7, 1.4, 1.3, 1.3, 1.45, 2.0, 2.9, 3.4])
POD_ZC = 4.6
NT, NB = 2.4, 2.1  # superellipse exponents, top and bottom halves (a round belly: it flies)
SEAM_PHI = math.degrees(math.acos(0.8 ** (NT / 2)))  # top-half angle where |x| = 0.8 w
SEAM_D = 0.45
SEAM_Y = (1.45, 6.85)   # side seams run along the pod between these rows
RING_Y = 2.05           # transverse seam behind the crown


def pod_point(y, phi_deg):
    w, zt, zb = POD_W(y), POD_ZT(y), POD_ZB(y)
    ph = math.radians(phi_deg)
    c, s = math.cos(ph), math.sin(ph)
    n = NT if s >= 0 else NB
    h = (zt - POD_ZC) if s >= 0 else (POD_ZC - zb)
    x = AX + w * math.copysign(abs(c) ** (2 / n), c)
    z = POD_ZC + h * math.copysign(abs(s) ** (2 / n), s)
    return x, z


def pod_normal2(y, phi_deg):
    x0, z0 = pod_point(y, phi_deg - 0.5)
    x1, z1 = pod_point(y, phi_deg + 0.5)
    dx, dz = x1 - x0, z1 - z0
    ln = math.hypot(dx, dz) or 1e-9
    return dz / ln, -dx / ln  # outward for counter-clockwise phi


def pod_top_z(x, y):
    w = POD_W(y)
    t = min(abs(x - AX) / w, 0.999)
    return POD_ZC + (POD_ZT(y) - POD_ZC) * (1 - t ** NT) ** (1 / NT)


def pod_surface(x, y, off=0.0):
    """Point on the pod's top at plan (x, y), pushed `off` along the surface normal."""
    z = pod_top_z(x, y)
    e = 0.02
    gx = (pod_top_z(x + e, y) - pod_top_z(x - e, y)) / (2 * e)
    gy = (pod_top_z(x, y + e) - pod_top_z(x, y - e)) / (2 * e)
    n = Vector((-gx, -gy, 1.0)).normalized()
    return Vector((x, y, z)) + n * off


def ramp(y, a, b, k=0.25):
    """1 inside [a, b], ramping to 0 over k outside it."""
    if y < a - k or y > b + k:
        return 0.0
    if y < a:
        return (y - (a - k)) / k
    if y > b:
        return ((b + k) - y) / k
    return 1.0


def pod(M):
    # Columns round the section: (phi, kind) kind 0 plain, 1 seam floor.
    cols = []
    base = [i * 360 / 36 for i in range(36)]
    seams = [SEAM_PHI, 180 - SEAM_PHI]
    for p in base:
        if all(abs(p - s) > 5.5 for s in seams):
            cols.append((p, 0))
    for s in seams:
        cols += [(s - 4.2, 0), (s - 1.9, 1), (s + 1.9, 1), (s + 4.2, 0)]
    cols.sort()
    # Stations along the pod.
    ys = set(T.frange(PY[0], PY[-1], 0.32))
    ys |= {RING_Y - 0.24, RING_Y - 0.09, RING_Y + 0.09, RING_Y + 0.24}
    ys |= {SEAM_Y[0] - 0.25, SEAM_Y[0], SEAM_Y[1], SEAM_Y[1] + 0.25}
    ys = sorted(y for y in ys if PY[0] <= y <= PY[-1])
    ys = [y for i, y in enumerate(ys) if i == 0 or y - ys[i - 1] > 0.02]
    ring_floor = {y for y in ys if abs(y - RING_Y) < 0.1}

    def in_top(p):
        return SEAM_PHI - 0.01 <= p <= 180 - SEAM_PHI + 0.01

    rings = []
    for y in ys:
        ring = []
        for p, kind in cols:
            x, z = pod_point(y, p)
            d = 0.0
            if kind == 1:
                d = SEAM_D * ramp(y, SEAM_Y[0] + 0.25, SEAM_Y[1] - 0.25, 0.25)
            if y in ring_floor and in_top(p):
                d = max(d, SEAM_D)
            nx, nz = pod_normal2(y, p)
            ring.append(M.v((x - nx * d, y, z - nz * d)))
        rings.append(ring)
    n = len(cols)
    for i in range(len(rings) - 1):
        y0, y1 = ys[i], ys[i + 1]
        for a in range(n):
            b = (a + 1) % n
            pa, pb = cols[a][0], cols[b][0] if b else cols[b][0] + 360
            pm = (pa + pb) / 2
            floor = cols[a][1] == 1 and cols[b][1] == 1 and SEAM_Y[0] < (y0 + y1) / 2 < SEAM_Y[1]
            ringf = y0 in ring_floor and y1 in ring_floor and in_top(pm)
            if floor or ringf:
                mat = SEAM
            elif in_top(pm):
                mat = TOP
            else:
                mat = SIDE
            M.f((rings[i][a], rings[i][b], rings[i + 1][b], rings[i + 1][a]), mat)
    M.f(list(reversed(rings[0])), SIDE)
    M.f(rings[-1], SIDE)


def rrect(x0, x1, y0, y1, r, k=4):
    """Rounded-rectangle loop in plan (px), counter-clockwise in screen terms, 4*(k+1) points."""
    pts = []
    corners = [(x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)]
    for cx, cy, a0 in corners:
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def scale_loop(loop, s, grow=0.0):
    cx = sum(p[0] for p in loop) / len(loop)
    cy = sum(p[1] for p in loop) / len(loop)
    out = []
    for x, y in loop:
        dx, dy = x - cx, y - cy
        ln = math.hypot(dx, dy) or 1e-9
        out.append((cx + dx * s + dx / ln * grow, cy + dy * s + dy / ln * grow))
    return out


def conform_ring(M, outer, inner, mat, top=0.45, lip=0.3, inner_floor=0.05, bottom=-0.45, ch=0.18):
    """A raised frame on the pod top between two plan loops, its top chamfered."""
    layers = [(outer, bottom), (outer, lip), (scale_loop(outer, 1.0, -ch), top),
              (scale_loop(inner, 1.0, ch), top), (inner, inner_floor), (inner, bottom)]
    rings = [[M.v(tuple(pod_surface(x, y, off))) for x, y in loop] for loop, off in layers]
    tube(M, rings + [rings[0]], mat, cap0=False, cap1=False)


def conform_plate(M, loop, mat, top, bottom=-0.45, ch=0.15, steps=3):
    """A plate following the pod top inside a plan loop, chamfered top edge, closed below."""
    layers = [(loop, bottom), (loop, top - ch), (scale_loop(loop, 1.0, -ch), top)]
    for i in range(1, steps):
        layers.append((scale_loop(scale_loop(loop, 1.0, -ch), 1 - i / steps), top))
    rings = [[M.v(tuple(pod_surface(x, y, off))) for x, y in lp] for lp, off in layers]
    cx = sum(p[0] for p in loop) / len(loop)
    cy = sum(p[1] for p in loop) / len(loop)
    rings.append([M.v(tuple(pod_surface(cx, cy, top)))])
    tube(M, rings, mat, cap0=True, cap1=False)


def conform_grid(M, x0, x1, y0, y1, mat, top, bottom=-0.45, nx=6, ny=3):
    """A rectangular patch following the pod top (the visor glass), closed box below."""
    def P(i, j, off):
        return M.v(tuple(pod_surface(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, off)))
    topg = [[P(i, j, top) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            M.f((topg[j][i], topg[j][i + 1], topg[j + 1][i + 1], topg[j + 1][i]), mat)
    # skirt
    border = [topg[0][i] for i in range(nx + 1)] + [topg[j][nx] for j in range(1, ny + 1)] + \
             [topg[ny][i] for i in range(nx - 1, -1, -1)] + [topg[j][0] for j in range(ny - 1, 0, -1)]
    bpts = [(x0 + (x1 - x0) * i / nx, y0) for i in range(nx + 1)] + \
           [(x1, y0 + (y1 - y0) * j / ny) for j in range(1, ny + 1)] + \
           [(x0 + (x1 - x0) * i / nx, y1) for i in range(nx - 1, -1, -1)] + \
           [(x0, y0 + (y1 - y0) * j / ny) for j in range(ny - 1, 0, -1)]
    low = [M.v(tuple(pod_surface(x, y, bottom))) for x, y in bpts]
    for k in range(len(border)):
        j = (k + 1) % len(border)
        M.f((border[k], border[j], low[j], low[k]), mat)
    M.f(list(reversed(low)), mat)


def head(M):
    pod(M)
    # Visor: raised dark frame, recessed red glass with the orange scanner eye at its left end.
    outer = rrect(8.05, 13.95, 3.05, 6.0, 0.95)
    inner = rrect(9.0, 13.0, 3.95, 5.08, 0.42)
    conform_ring(M, outer, inner, FRAME_)
    conform_grid(M, 9.85, 13.15, 3.85, 5.18, GLASS, top=0.14, nx=6, ny=2)
    conform_grid(M, 8.85, 9.95, 3.85, 5.18, EYE, top=0.17, nx=2, ny=2)
    # Chin lip under the visor (row 6, bright).
    conform_plate(M, rrect(8.25, 13.75, 6.05, 6.95, 0.4), CHIN, top=0.32)


def neck(M):
    hull(M, cbox(8.3, 13.7, 6.3, 8.6, 2.8, 5.2, 0.45), CORE)
    for x in (9.05, 12.95):
        cyl(M, (x, 6.2, 5.1), (x, 8.4, 5.1), 0.62, 10, ROD, bevel=0.12)
        cyl(M, (x, 6.6, 5.1), (x, 7.1, 5.1), 0.78, 10, KNUCK, bevel=0.12)  # gland collar


def yoke(M):
    # Axle housing across the shoulders, banded at the knuckles.
    cyl(M, (7.0, 9.0, 4.4), (10.15, 9.0, 4.4), 1.2, 16, AXLE, bevel=0.2)
    cyl(M, (11.85, 9.0, 4.4), (15.0, 9.0, 4.4), 1.2, 16, AXLE, bevel=0.2)
    cyl(M, (9.9, 9.0, 4.4), (12.1, 9.0, 4.4), 1.0, 16, SEAM, bevel=0.1)  # recessed centre bearing
    for x0, x1 in ((9.65, 10.05), (11.95, 12.35)):
        cyl(M, (x0, 9.0, 4.4), (x1, 9.0, 4.4), 1.36, 16, AXLE, bevel=0.1)
    # Centre bearing cap facing forward (the dark pixels at columns 10-11, row 9).
    cyl(M, (11.0, 8.6, 4.2), (11.0, 9.98, 4.2), 0.78, 12, SEAM, bevel=0.18)


# --- the prongs (left; mirrored) -------------------------------------------------------------------

PRY = [9.6, 10.5, 11.5, 12.4, 13.5, 15.0, 16.5, 17.8, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 24.8]
XO = pchip(PRY, [6.2, 6.0, 5.15, 4.15, 3.97, 3.95, 3.95, 3.95, 3.98, 4.15, 4.6, 5.15, 5.6, 6.0, 6.3])
XI = pchip(PRY, [8.9, 8.8, 8.4, 7.7, 7.35, 7.2, 7.1, 7.05, 7.0, 7.0, 7.0, 7.0, 7.0, 6.95, 6.9])
# Level prongs (a flying drone): the beam stays at shoulder height, the claw tip curls down a little.
ZC = pchip(PRY, [4.6, 4.6, 4.58, 4.55, 4.52, 4.5, 4.48, 4.45, 4.4, 4.33, 4.25, 4.15, 4.03, 3.9, 3.8])
HZ = pchip(PRY, [1.3, 1.3, 1.35, 1.4, 1.45, 1.4, 1.3, 1.15, 1.0, 0.9, 0.78, 0.65, 0.52, 0.4, 0.3])
TIP_PT = (6.65, 25.25, 3.7)
NECK_Y = 17.45   # groove between forearm and finger
TIP_Y = 20.85    # seam where the hardened claw tip starts
PLATE_Y = (11.75, 17.05)


def oct_section(y, grow=0.0):
    xo, xi = XO(y) - grow, XI(y) + grow
    zc, hz = ZC(y), HZ(y) + grow
    hw = (xi - xo) / 2
    cx = (xi + xo) / 2
    c = 0.38 * min(hw, hz)
    return [(cx + hw, zc - hz + c), (cx + hw, zc + hz - c), (cx + hw - c, zc + hz), (cx - hw + c, zc + hz),
            (cx - hw, zc + hz - c), (cx - hw, zc - hz + c), (cx - hw + c, zc - hz), (cx + hw - c, zc - hz)]


def prong(M):
    ys = set(T.frange(PRY[0], PRY[-1], 0.5))
    grooves = [(NECK_Y, 0.28), (TIP_Y, 0.2)]
    for gy, _ in grooves:
        ys |= {gy - 0.22, gy - 0.08, gy + 0.08, gy + 0.22}
    ys = sorted(ys)
    rings, kinds = [], []
    for y in ys:
        g = 0.0
        for gy, gd in grooves:
            if abs(y - gy) < 0.1:
                g = -gd
        rings.append([M.v((x, y, z)) for x, z in oct_section(y, g)])
        kinds.append(g < 0)
    rings.append([M.v(TIP_PT)])

    def mat(i):
        if i < len(kinds) - 1 and kinds[i] and kinds[i + 1]:
            return SEAM
        y = ys[i] if i < len(ys) else 99
        return TIP if y >= TIP_Y else PRONG
    tube(M, rings, mat, cap0=True, cap1=False)

    # Armour plate over the forearm's top: proud, chamfered ends.
    py = T.frange(PLATE_Y[0], PLATE_Y[1], 0.45)
    prings = []
    for i, y in enumerate(py):
        s = oct_section(y)
        g = 0.3 if 0 < i < len(py) - 1 else 0.05
        xo, xi, zc, hz = XO(y), XI(y), ZC(y), HZ(y)
        c = 0.38 * min((xi - xo) / 2, hz)
        top = zc + hz + g
        pts = [(xi + 0.12, zc + 0.2), (xi + 0.12, zc + hz - c + g * 0.3), (xi - c + 0.05, top),
               (xo + c - 0.05, top), (xo - 0.12, zc + hz - c + g * 0.3), (xo - 0.12, zc + 0.2)]
        if g < 0.1:
            pts = [(xi - 0.05, zc + 0.2), (xi - 0.05, zc + hz - c), (xi - c, zc + hz - 0.02),
                   (xo + c, zc + hz - 0.02), (xo + 0.05, zc + hz - c), (xo + 0.05, zc + 0.2)]
        prings.append([M.v((x, y, z)) for x, z in pts])
    tube(M, prings, PRONG)

    # Inner jaw: upper jaw block, then the lowered grip notch with three serration teeth.
    hull(M, cbox(6.9, 8.85, 11.55, 13.95, ZC(12.7) - 1.1, ZC(12.7) + 1.05, 0.3), PRONG)
    nz0, nz1 = ZC(15.2) - 1.2, ZC(15.2) + 0.15
    hull(M, cbox(6.9, 8.7, 13.8, 16.6, nz0, nz1, 0.22), SEAM)
    for ty in (14.35, 15.15, 15.95):
        hull(M, [(7.05, ty - 0.32, nz1 - 0.05), (7.05, ty + 0.32, nz1 - 0.05), (8.6, ty - 0.32, nz1 - 0.05),
                 (8.6, ty + 0.32, nz1 - 0.05), (7.05, ty, nz1 + 0.42), (8.45, ty, nz1 + 0.42)], SEAM)

    # Shoulder knuckle on the axle end: a hinge drum, an outer hub and pin.
    cyl(M, (6.05, 9.9, 4.6), (9.7, 9.9, 4.6), 1.35, 16, KNUCK, bevel=0.28)
    cyl(M, (5.85, 9.9, 4.6), (6.3, 9.9, 4.6), 0.72, 12, AXLE, bevel=0.12)
    cyl(M, (5.7, 9.9, 4.6), (6.0, 9.9, 4.6), 0.32, 8, KNUCK, bevel=0.06)


def rear(M):
    """Back of the pod (seen only from behind); nothing below it: the drone flies."""
    # Two exhaust ports low on the pod's back (seen only from behind).
    for x in (9.6, 12.4):
        cyl(M, (x, 2.2, 3.6), (x, 1.05, 3.6), 0.55, 10, AXLE, bevel=0.1, cap_mat=SEAM)
    # A louvred cooling grille between them.
    hull(M, cbox(10.15, 11.85, 1.3, 2.4, 2.9, 4.5, 0.15), SEAM)
    for z in (3.15, 3.65, 4.15):
        hull(M, cbox(10.25, 11.75, 1.12, 1.6, z - 0.14, z + 0.14, 0.06), AXLE)


def mirror(M, start_vert):
    bm = M.bm
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start_vert:]
    faces = {f for v in verts for f in v.link_faces}
    edges = {e for v in verts for e in v.link_edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + list(faces))["geom"]
    ax = W((AX, 0, 0)).x
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x


def materials(sprite):
    out = []
    spec = {TOP: (0.4, 0.42), SIDE: (0.38, 0.46), SEAM: (0.15, 0.7), FRAME_: (0.3, 0.5), GLASS: (1.0, 0.7),
            EYE: (1.0, 0.7), CHIN: (0.42, 0.4), ROD: (0.6, 0.28), CORE: (0.35, 0.5), AXLE: (0.4, 0.45),
            KNUCK: (0.42, 0.4), PRONG: (0.42, 0.4), TIP: (0.45, 0.38)}
    names = ["top", "side", "seam", "frame", "glass", "eye", "chin", "rod", "core", "axle", "knuck", "prong", "tip"]
    for slot in range(13):
        met, rough = spec[slot]
        out.append(common.palette_material(sprite, PAL_OF[slot], f"{NAME}_A_{names[slot]}", metallic=met,
                                           roughness=rough, emission_strength=GLOWS.get(slot, 0.0)))
    return out


def build(sprite, coll):
    M = Mesh()
    head(M)
    neck(M)
    yoke(M)
    rear(M)
    M.bm.verts.ensure_lookup_table()
    start = len(M.bm.verts)
    prong(M)
    mirror(M, start)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in materials(sprite):
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (0.97, 0.98, 1.0), tuple(s for s in range(13) if s not in GLOWS and s not in DIM)
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


def dim_visor(obj, out_dir):
    """Multiply the visor materials' palette colour by a constant grey (a 4x4 image, so it survives
    the glTF export as a baseColorTexture; in game the palette colour still comes from pal_<index>)."""
    for slot, k in DIM.items():
        img = bpy.data.images.new(f"{NAME}_dim_{slot}", 4, 4, alpha=False)
        v = k * 12.92 if k <= 0.0031308 else 1.055 * k ** (1 / 2.4) - 0.055  # sRGB image, like the bake
        img.pixels[:] = [v, v, v, 1.0] * 16
        img.filepath_raw = str(out_dir / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
        m = obj.data.materials[slot]
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])


# --- views and measurements (scratch only) ---------------------------------------------------------

def pal_grid(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    rows = []
    for r in range(28):
        row = []
        for c in range(24):
            X, Y = (c + 0.5 - 12) * PX, (14 - (r + 0.5)) * PX
            hit, loc, nrm, fi = ev.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            m = obj.data.materials[obj.data.polygons[fi].material_index]
            row.append(int(m.name.split("_")[1]))
        rows.append(row)
    return rows


def cam(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def top_renders(obj, out):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o is not obj
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 10
    scene.render.resolution_x, scene.render.resolution_y = 24 * K, 28 * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(out / "top_mask.png")
    bpy.ops.render.render(write_still=True)


def lit_views(obj, out):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.2, 0.16, 1)
    bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(-30), math.radians(20))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.001))
    g = bpy.context.active_object
    g.name = "ground"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.09, 0.11, 0.08, 1)
    g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    zc = 4.0 * PX
    tilt = math.radians(32)
    views = {
        "top": ((0, 0, d), 2.6, (0, 0, 0)),
        "side": ((d, 0, zc), 2.6, (0, 0, zc)),
        "front": ((0, -d, zc), 2.6, (0, 0, zc)),
        "rear": ((0, d, zc), 2.6, (0, 0, zc)),
        "q34": ((d * 0.6, -d * 0.6, d * 0.65), None, (0, 0, zc)),
        "q34l": ((-d * 0.65, d * 0.35, d * 0.55), None, (0, 0, zc)),
        "game": ((0, -d * math.sin(tilt), d * math.cos(tilt)), None, (0, 0, zc)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, 0, zc)),
    }
    for name, (loc, ortho, look) in views.items():
        g.hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()  # Blender 5.2 leaves None entries in the view layer otherwise
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    obj = build(sprite, coll)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_renders(obj, views)
        (views / "pal.json").write_text(json.dumps(pal_grid(obj)))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bd = HERE / "bake"
        bd.mkdir(parents=True, exist_ok=True)
        bake(obj, bd)
        fmt = "WEBP"
    bd = HERE / "bake"
    bd.mkdir(parents=True, exist_ok=True)
    dim_visor(obj, bd)
    sh = common.outline_shell(obj, coll, voxel=0.012, faces=1500, smooth=8)
    common.export_sprite_model(WT, [obj, sh], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views)
    (HERE / "stats.json").write_text(json.dumps({"tris": tris}))


if __name__ == "__main__":
    main()
