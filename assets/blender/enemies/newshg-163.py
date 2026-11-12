"""Blue manta skimmer (newshg.shp frame 163, 24x28, one frame), design A: a hard-surface hover craft.

Identity: type 809 rises 2 px/tick UP the screen against the scroll (spawned on groundBottom in GEM
WAR and MARKERS, swung sideways by link ev20), aimed fire from tur131. So it is a VEHICLE facing
up-screen, its pointed head leading. Read as a low ground-effect skimmer: a manta wing riding about
one pixel over the ground on a round closed belly (no skirt detail, no wheels).

Reading of the sprite (inner mask: the ink ring is the game's own outline, D74):
- Head (rows 5-13): a pointed domed cockpit pod, pal 55, its snout narrower (rows 5-7) than the
  canopy section behind it. A dark brow (row 7, pal 51) over a cyan wraparound visor (row 8, its
  ends wrapping down the sides to row 9, pal 135), split by a dark centre post (columns 11-12).
  Two raised cheek strakes (the bright diagonal 57-59 from column 10 row 9 to column 7 row 12),
  each with a dark seam behind it (the 50-51 diagonal one pixel further back).
- Behind the head (rows 14-16): a dark centre intake (columns 10-13) and, either side, a dark
  slanted socket with a red eye lens at its inner end (columns 8-9, pal 116, glowing).
- Wing (rows 14-26, pal 53): a manta wing with a rounded leading edge, swept back to two lobes.
- Haunches: two raised swept ridges in a V from the apex at row 18 out to the pale end caps at
  row 23 (crest pal 57, outer slope pal 54, a modelled panel step (pal 52) along the dark line three
  pixels outboard of the crest; end caps pal 58). Between the arms a raised tail deck (pal 55)
  whose rear face carries two thruster nozzles.
- Lobes (rows 24-26): a small fairing pod on each lobe (lit crest row 24, pal 55) and the red tail
  lamp at each outer rear corner (pal 117, glowing).
- Underside: the wing's and the head's round closed bellies; nothing else.

Mirror symmetric about pixel edge 12.

    Blender --background --python assets/blender/enemies/newshg-163.py -- [--views DIR] [--no-bake]

Exports public/models/enemies/newshg-163.glb (model + outline shell, D51) and its spriteModels entry.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

HERE = Path(__file__).resolve().parent
NAME = "newshg-163"
PX = 1 / 12
AX = 12.0  # mirror axis (pixel edge)

# Material slots -> palette index.
(WING, SLOPE, CREST, DECK, GROOVE, HEAD, BROW, VISOR, STRAKE, SEAM, SOCKET, EYE, LAMP, TIP, POD,
 NOZZLE, INTAKE) = range(17)
PAL_OF = {WING: 53, SLOPE: 54, CREST: 57, DECK: 55, GROOVE: 52, HEAD: 55, BROW: 51, VISOR: 137,
          STRAKE: 57, SEAM: 51, SOCKET: 50, EYE: 116, LAMP: 117, TIP: 58, POD: 55, NOZZLE: 50, INTAKE: 53}
NAMES = ["wing", "slope", "crest", "deck", "groove", "head", "brow", "visor", "strake", "seam", "socket",
         "eye", "lamp", "tip", "pod", "nozzle", "intake"]
GLOWS = {VISOR: 1.0, EYE: 1.0, LAMP: 1.0}  # D126: 1 = the palette colour, unlit
SPEC = {WING: (0.45, 0.42), SLOPE: (0.45, 0.42), CREST: (0.5, 0.36), DECK: (0.45, 0.4), GROOVE: (0.25, 0.65),
        HEAD: (0.45, 0.38), BROW: (0.3, 0.55), VISOR: (0.1, 0.2), STRAKE: (0.5, 0.36), SEAM: (0.2, 0.65),
        SOCKET: (0.2, 0.7), EYE: (0.1, 0.25), LAMP: (0.1, 0.25), TIP: (0.55, 0.32), POD: (0.45, 0.4),
        NOZZLE: (0.3, 0.6), INTAKE: (0.45, 0.42)}

pchip = T.pchip


def W(p):
    """sprite px (x = column edge, y = row edge, z up) -> Blender units."""
    return Vector(((p[0] - 12) * PX, (14 - p[1]) * PX, p[2] * PX))


def lerp_table(u, us, vs):
    if u <= us[0]:
        return vs[0]
    for i in range(len(us) - 1):
        if u <= us[i + 1]:
            t = (u - us[i]) / (us[i + 1] - us[i])
            return vs[i] + (vs[i + 1] - vs[i]) * t
    return vs[-1]


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


def tube(M, rings, mats, cap0=True, cap1=True, closed=True):
    """Connect rings (equal-length vert lists; a 1-vert ring is a point). mats: int or f(i, k)."""
    def mat(i, k):
        return mats(i, k) if callable(mats) else mats
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        n = max(len(r0), len(r1))
        for k in range(n if closed else n - 1):
            j = (k + 1) % n
            if len(r0) == 1:
                M.f((r0[0], r1[j], r1[k]), mat(i, k))
            elif len(r1) == 1:
                M.f((r0[k], r0[j], r1[0]), mat(i, k))
            else:
                M.f((r0[k], r0[j], r1[j], r1[k]), mat(i, k))
    if cap0 and len(rings[0]) > 2:
        M.f(list(reversed(rings[0])), mat(0, 0))
    if cap1 and len(rings[-1]) > 2:
        M.f(rings[-1], mat(len(rings) - 2, 0))


def hull(M, pts, mat):
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


def cyl(M, a, b, r, sides, mat, bevel=0.0, cap_mat=None):
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    w = d.cross(u).normalized()
    L = (b - a).length
    prof = [(0, r - bevel), (bevel, r), (L - bevel, r), (L, r - bevel)] if bevel else [(0, r), (L, r)]
    rings = [[M.v(tuple(a + d * t + (u * math.cos(2 * math.pi * (k + 0.5) / sides)
                                     + w * math.sin(2 * math.pi * (k + 0.5) / sides)) * rr))
              for k in range(sides)] for t, rr in prof]
    tube(M, rings, mat, cap0=False, cap1=False)
    cm = mat if cap_mat is None else cap_mat
    M.f(list(reversed(rings[0])), cm)
    M.f(rings[-1], cm)


# --- the wing ----------------------------------------------------------------------------------------
# Plan: leading edge LE(dx) and trailing edge TE(dx) (sprite rows), dx = distance from the axis.
LE = pchip([0.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 11.6, 12.0], [13.2, 13.2, 13.55, 14.5, 15.5, 16.5, 17.45, 17.95, 18.6])
TE = pchip([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 10.8, 11.4, 12.0],
           [22.0, 22.65, 23.35, 23.95, 24.5, 25.0, 25.5, 25.9, 26.25, 26.65, 26.95, 26.95, 26.6, 25.9])
ZB = pchip([0.0, 6.0, 12.0], [1.0, 1.15, 1.55])     # belly line
TH = pchip([0.0, 4.0, 8.0, 12.0], [3.6, 3.35, 2.55, 1.6])  # thickness
# Chordwise section (u = 0 leading edge .. 1 trailing edge), fraction of thickness above ZB.
TOPU = [0.0, 0.025, 0.07, 0.15, 0.32, 0.62, 0.86, 0.96, 1.0]
TOPF = [0.5, 0.75, 0.89, 0.97, 1.0, 1.0, 0.9, 0.74, 0.62]
BOTU = [1.0, 0.94, 0.72, 0.3, 0.09, 0.025]
BOTF = [0.36, 0.2, 0.03, 0.0, 0.1, 0.27]
DXMAX = 11.9


def wing_top(x, y):
    dx = min(abs(x - AX), DXMAX)
    le, te = LE(dx), TE(dx)
    u = min(max((y - le) / (te - le), 0.0), 1.0)
    return ZB(dx) + TH(dx) * lerp_table(u, TOPU, TOPF)


def surf_point(fz, x, y, off):
    z = fz(x, y)
    e = 0.03
    gx = (fz(x + e, y) - fz(x - e, y)) / (2 * e)
    gy = (fz(x, y + e) - fz(x, y - e)) / (2 * e)
    n = Vector((-gx, -gy, 1.0)).normalized()
    return tuple(Vector((x, y, z)) + n * off)


def wing(M):
    ds = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5,
          10.0, 10.5, 11.0, 11.4, 11.7]
    stations = [(-d) for d in reversed(ds[1:])] + ds
    rings = []

    def section(dx, shrink=0.0):
        le, te = LE(min(dx, DXMAX)), TE(min(dx, DXMAX))
        zb, th = ZB(dx), TH(dx)
        pts = [(le + (te - le) * u, zb + th * f) for u, f in zip(TOPU, TOPF)]
        pts += [(le + (te - le) * u, zb + th * f) for u, f in zip(BOTU, BOTF)]
        if shrink:
            cy = (le + te) / 2
            cz = zb + th * 0.5
            pts = [(cy + (y - cy) * (1 - shrink / ((te - le) / 2)), cz + (z - cz) * (1 - 2.2 * shrink / th))
                   for y, z in pts]
        return pts

    xs = []
    for s in stations:
        xs.append((AX + s, section(abs(s))))
    # chamfered tips
    tip = [(AX - DXMAX - 0.2, section(DXMAX, 0.3))] + xs + [(AX + DXMAX + 0.2, section(DXMAX, 0.3))]
    for x, sec in tip:
        rings.append([M.v((x, y, z)) for y, z in sec])
    tube(M, rings, WING, cap0=True, cap1=True)


# --- haunches, deck, lobes ------------------------------------------------------------------------
# Crest line y = 18 + dx; panel step 2.1 px outboard (the dark line y = 15 + dx).
ARM0, ARM1 = -0.35, 5.25   # dx along the crest
ARM_PROF = [  # (s outboard, h above the wing top, material of the face that follows)
    (-1.05, -0.5, DECK), (-1.05, 0.95, DECK), (-0.55, 1.45, SLOPE), (-0.18, 1.68, CREST), (0.22, 1.68, CREST),
    (0.55, 1.42, SLOPE), (1.95, 0.42, SLOPE), (2.05, 0.4, GROOVE), (2.15, 0.02, WING), (2.15, -0.5, WING)]


def arm_point(side, dxc, s, h):
    """Crest station at dx = dxc, offset s outboard (perpendicular, plan), h above the wing top."""
    c = (AX + side * dxc, 18.0 + dxc)
    nrm = (side / math.sqrt(2), -1 / math.sqrt(2))  # outboard and forward
    x, y = c[0] + nrm[0] * s, c[1] + nrm[1] * s
    return (x, y, wing_top(x, y) + h)


def arms(M):
    for side in (-1, 1):
        ts = [ARM0 + (ARM1 - ARM0) * i / 16 for i in range(17)]
        rings = [[M.v(arm_point(side, t, s, h)) for s, h, _ in ARM_PROF] for t in ts]
        if side > 0:
            rings = [list(reversed(r)) for r in rings]
        mats = [m for _, _, m in ARM_PROF]
        n = len(ARM_PROF)

        def mat(i, k, side=side, mats=mats, n=n):
            if side > 0:
                k = n - 2 - k
            return mats[k] if k < n - 1 else WING
        tube(M, rings, mat, cap0=True, cap1=True)
        # Pale end cap on the haunch tip (row 23, columns 5-6): a chamfered knuckle.
        cx, cy = AX + side * 5.75, 23.55
        z0 = wing_top(cx, cy)
        hull(M, [(cx + side * dxx, cy + dyy, z0 + dz)
                 for dxx, dyy, dz in ((-1.0, -1.2, -0.4), (1.0, -0.9, -0.4), (1.1, 0.75, -0.4), (-0.9, 0.85, -0.4),
                                      (-0.8, -0.95, 1.45), (0.75, -0.7, 1.45), (0.85, 0.5, 1.2), (-0.7, 0.6, 1.2),
                                      (-0.45, -0.55, 1.75), (0.4, -0.35, 1.75), (0.45, 0.15, 1.6), (-0.35, 0.25, 1.6))],
             TIP)


def deck(M):
    """Raised tail deck between the arms, its rear face along the trailing edge, two nozzles."""
    nx, ny = 14, 6
    H, CH = 1.0, 0.22
    grid = []
    for i in range(nx + 1):
        dxs = -5.4 + 10.8 * i / nx
        y0 = 18.0 + abs(dxs) - 0.6
        y1 = TE(abs(dxs)) - 0.08
        col = []
        for j in range(ny + 1):
            y = y0 + (y1 - y0) * j / ny
            x = AX + dxs
            col.append((x, y))
        grid.append(col)
    top = [[M.v((x, y, wing_top(x, y) + (H if j < ny else H - CH))) for j, (x, y) in enumerate(col)]
           for col in grid]
    # chamfer the rear edge: last row pulled in
    for i in range(nx):
        for j in range(ny):
            M.f((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]), DECK)
    # rear face: from the chamfer down into the wing
    low = []
    for i, col in enumerate(grid):
        x, y = col[-1]
        low.append(M.v((x, y + 0.08, wing_top(x, y - 0.3) - 0.9)))
    rear = [top[i][ny] for i in range(nx + 1)]
    for i in range(nx):
        M.f((rear[i], low[i], low[i + 1], rear[i + 1]), DECK)
    # seal the sides and front under the arms (hidden)
    front = [top[i][0] for i in range(nx + 1)]
    frontlow = [M.v((v.co.x / PX + 12, 14 - v.co.y / PX, v.co.z / PX - 1.6)) for v in front]
    for i in range(nx):
        M.f((front[i + 1], front[i], frontlow[i], frontlow[i + 1]), DECK)
    left = [top[0][j] for j in range(ny + 1)]
    right = [top[nx][j] for j in range(ny + 1)]
    M.f(list(reversed(left)) + [frontlow[0], low[0]], DECK)
    M.f(right + [low[nx], frontlow[nx]], DECK)
    M.f(frontlow + list(reversed(low)), DECK)
    # Thruster nozzles in the rear face (pointing back along the face normal).
    for side in (-1, 1):
        dxn = 2.2
        x = AX + side * dxn
        te = TE(dxn)
        z = wing_top(x, te - 1.0) + 0.15
        tdir = Vector((side * 0.5, 1.0, 0.0)).normalized()  # back and a little outboard, normal to the TE sweep
        base = Vector((x, te - 0.85, z))
        cyl(M, tuple(base), tuple(base + tdir * 0.95), 0.75, 12, DECK, bevel=0.12, cap_mat=NOZZLE)
        cyl(M, tuple(base + tdir * 0.5), tuple(base + tdir * 1.02), 0.5, 12, NOZZLE, bevel=0.0, cap_mat=NOZZLE)


def lobes(M):
    for side in (-1, 1):
        # Fairing pod along each lobe (lit crest row 24, columns 1-3 / 20-22).
        a = (6.6, 25.35)
        b = (10.6, 24.55)
        ts = [i / 8 for i in range(9)]
        rad = [0.35, 0.7, 0.85, 0.9, 0.9, 0.88, 0.8, 0.6, 0.25]
        rings = []
        for t, r in zip(ts, rad):
            dx = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            x = AX + side * dx
            zb = wing_top(x, y) - 0.4
            rr = r
            sec = []
            for k in range(8):
                ang = 2 * math.pi * (k + 0.5) / 8
                # plan perpendicular to the pod axis
                px, py = -(b[1] - a[1]), (b[0] - a[0])
                ln = math.hypot(px, py)
                px, py = px / ln, py / ln
                sx = math.cos(ang) * rr
                sec.append((x + side * px * sx, y + py * sx, zb + 0.55 + math.sin(ang) * rr * 0.95))
            rings.append([M.v(p) for p in sec])
        tube(M, rings, POD, cap0=True, cap1=True)
        # Red tail lamp bar wrapping the outer rear corner (row 25 column 0, row 26 columns 1-2), in a
        # dark housing.
        a = Vector((AX + side * 11.75, 25.15))
        b = Vector((AX + side * 9.75, 26.75))
        za = wing_top(a.x, a.y - 0.3) - 0.45
        zb = wing_top(b.x, b.y - 0.3) - 0.45
        cyl(M, (a.x, a.y, za - 0.15), (b.x, b.y, zb - 0.15), 0.6, 10, SOCKET, bevel=0.15)
        mid = (a + b) / 2
        d = (b - a).normalized()
        o = Vector((d.y, -d.x)) * side * -0.25   # pushed out over the rear-outer edge
        cyl(M, (a.x + d.x * 0.2 + o.x, a.y + d.y * 0.2 + o.y, za + 0.1),
            (b.x - d.x * 0.2 + o.x, b.y - d.y * 0.2 + o.y, zb + 0.1), 0.85, 12, LAMP, bevel=0.3)


# --- the front deck: intake, eye sockets -------------------------------------------------------------

def plate(M, fz, loop, mat, h, depth=0.6, ch=0.12, side_mat=None):
    """A plate following the surface fz inside a plan loop (px), top h above it, chamfered rim."""
    cx = sum(p[0] for p in loop) / len(loop)
    cy = sum(p[1] for p in loop) / len(loop)

    def inset(p, d):
        dx, dy = p[0] - cx, p[1] - cy
        ln = math.hypot(dx, dy) or 1e-9
        return (p[0] - dx / ln * d, p[1] - dy / ln * d)
    layers = [([p for p in loop], -depth), ([p for p in loop], h - ch), ([inset(p, ch) for p in loop], h)]
    rings = [[M.v(surf_point(fz, x, y, off)) for x, y in lp] for lp, off in layers]
    sm = mat if side_mat is None else side_mat
    tube(M, rings, lambda i, k: sm if i == 0 else mat, cap0=True, cap1=True)


def wing_panels(M):
    """A raised outer-wing access panel each side: its chamfered rim reads as modelled panel lines."""
    for side in (-1, 1):
        loop = []
        for dx, y in ((7.6, 15.3), (10.6, 18.2), (10.9, 22.6), (9.6, 24.6), (7.9, 23.3), (7.3, 19.0)):
            loop.append((AX + side * dx, y))
        if side > 0:
            loop = list(reversed(loop))
        plate(M, wing_top, loop, WING, 0.16, ch=0.14)


def front_deck(M):
    # Centre intake (columns 10-13, rows 14-16): a raised scoop, dark grille, a splitter vane.
    pts = []
    for x0, x1, y0, y1, z0, z1, ch in ((10.05, 13.95, 13.5, 17.1, 2.9, 5.25, 0.3),):
        pts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0,)]
        top = [(x0 + ch, y0 + ch, z1), (x1 - ch, y0 + ch, z1), (x0 + ch, y1 - ch, z1), (x1 - ch, y1 - ch, z1),
               (x0, y0, z1 - ch), (x1, y0, z1 - ch), (x0, y1, z1 - ch), (x1, y1, z1 - ch)]
        hull(M, pts + top, INTAKE)
    hull(M, [(x, y, z) for x in (10.45, 13.55) for y in (13.9, 16.7) for z in (4.6, 5.33)], SOCKET)
    for x in (11.15, 12.85):
        hull(M, [(x + dx, y, z) for dx in (-0.2, 0.2) for y in (14.0, 16.6) for z in (4.6, 5.25)], INTAKE)
    hull(M, [(x, y, z) for x in (11.8, 12.2) for y in (13.95, 16.65) for z in (4.6, 5.42)], DECK)
    for side in (-1, 1):
        def P(dx, y):
            return (AX + side * dx, y)
        sock = [P(2.0, 13.9), P(7.7, 13.9), P(7.5, 14.6), P(5.0, 15.35), P(4.1, 16.0), P(3.6, 17.0), P(2.0, 17.0)]
        if side > 0:
            sock = list(reversed(sock))
        plate(M, wing_top, sock, SOCKET, 0.14, ch=0.08)
        # Eye lens: a slanted oval (columns 8-9, rows 14-16).
        c = Vector((AX + side * 3.0, 15.55))
        ax = Vector((side * -0.45, 1.0)).normalized()
        pr = Vector((ax.y, -ax.x))
        loop = []
        for k in range(12):
            a = 2 * math.pi * k / 12
            p = c + ax * math.cos(a) * 1.25 + pr * math.sin(a) * 0.62
            loop.append((p.x, p.y))
        if side > 0:
            loop = list(reversed(loop))
        plate(M, wing_top, loop, EYE, 0.42, ch=0.18, side_mat=SOCKET)


# --- the head -------------------------------------------------------------------------------------

HY = [4.85, 5.5, 6.5, 7.5, 8.2, 8.7, 9.5, 10.5, 11.5, 12.5, 13.2, 13.65, 14.0]
HWf = pchip(HY, [0.3, 1.05, 2.05, 3.05, 4.55, 5.2, 5.95, 6.3, 7.0, 7.9, 7.55, 6.8, 5.2])
# Fix 1: a low prow pod, not a tall helmet. The ridge line climbs straight from a low beak to a
# nearly flat canopy deck (rows 8-11, where the visor faces up at the game camera), then falls to
# the intake; the equator sits low and the flanks slope out to the belly, so no brim overhangs.
HZT = pchip(HY, [3.0, 4.0, 5.1, 5.85, 6.1, 6.15, 6.12, 6.05, 5.95, 5.8, 5.6, 5.4, 5.15])
HZB = pchip(HY, [2.3, 2.0, 1.7, 1.5, 1.4, 1.35, 1.3, 1.3, 1.3, 1.35, 1.4, 1.5, 1.7])
HZC = pchip(HY, [2.55, 2.5, 2.45, 2.4, 2.4, 2.4, 2.4, 2.45, 2.5, 2.55, 2.6, 2.7, 2.8])
# Section exponent: a ridged roof at the prow (the sprite's dark centre line), rounding out behind.
NTf = pchip([4.85, 6.0, 7.5, 9.0, 10.5, 14.0], [1.25, 1.3, 1.6, 2.2, 2.5, 2.5])
NB = 1.7


def head_top(x, y):
    y = min(max(y, HY[0]), HY[-1])
    w = HWf(y)
    t = min(abs(x - AX) / w, 0.999)
    zc = HZC(y)
    nt = NTf(y)
    return zc + (HZT(y) - zc) * (1 - t ** nt) ** (1 / nt)


def head_point(y, phi):
    w, zt, zb, zc = HWf(y), HZT(y), HZB(y), HZC(y)
    ph = math.radians(phi)
    c, s = math.cos(ph), math.sin(ph)
    n = NTf(y) if s >= 0 else NB
    h = (zt - zc) if s >= 0 else (zc - zb)
    return AX + w * math.copysign(abs(c) ** (2 / n), c), zc + h * math.copysign(abs(s) ** (2 / n), s)


def head(M):
    ys = sorted(set(T.frange(HY[0], HY[-1], 0.4)) | {HY[-1], 13.8, 13.9})
    ys = [y for i, y in enumerate(ys) if i == 0 or y - ys[i - 1] > 0.04]
    rings = []
    N = 28
    for y in ys:
        rings.append([M.v((x, y, z)) for x, z in (head_point(y, 360 * k / N) for k in range(N))])
    tip = [M.v((AX, HY[0] - 0.12, HZC(HY[0]) + 0.3))]
    tube(M, [tip] + rings, HEAD, cap0=False, cap1=True)
    hs = lambda x, y, off: surf_point(head_top, x, y, off)  # noqa: E731

    # Brow (row 7, dark) and centre post (columns 11-12, row 8): one dark T frame.
    def grid_patch(x0f, x1f, y0f, y1f, mat, h, nx=10, ny=3, depth=0.5):
        """A patch on the head between x0f(y)..x1f(y) (abs x) and y0f(x)..y1f(x)."""
        topg, low = [], []
        for j in range(ny + 1):
            row, lrow = [], []
            for i in range(nx + 1):
                u, v = i / nx, j / ny
                # param over x at the patch's mid y, then y between the bounds at that x
                x = x0f + (x1f - x0f) * u
                y = y0f(x) + (y1f(x) - y0f(x)) * v
                d = abs(x - AX)
                x = AX + math.copysign(min(d, HWf(y) * 0.985), x - AX)
                row.append(M.v(hs(x, y, h)))
                lrow.append((x, y))
            topg.append(row)
            low.append(lrow)
        for j in range(ny):
            for i in range(nx):
                M.f((topg[j][i], topg[j][i + 1], topg[j + 1][i + 1], topg[j + 1][i]), mat)
        border = [topg[0][i] for i in range(nx + 1)] + [topg[j][nx] for j in range(1, ny + 1)] + \
                 [topg[ny][i] for i in range(nx - 1, -1, -1)] + [topg[j][0] for j in range(ny - 1, 0, -1)]
        bpts = [low[0][i] for i in range(nx + 1)] + [low[j][nx] for j in range(1, ny + 1)] + \
               [low[ny][i] for i in range(nx - 1, -1, -1)] + [low[j][0] for j in range(ny - 1, 0, -1)]
        lv = [M.v(hs(x, y, -depth)) for x, y in bpts]
        for k in range(len(border)):
            j = (k + 1) % len(border)
            M.f((border[k], border[j], lv[j], lv[k]), mat)
        M.f(list(reversed(lv)), mat)

    # Visor (fix 1): two separate glass panes either side of the dark centre post (row 8, columns
    # 7-10 / 13-16, pal 137), each a chamfered slab whose top faces mostly up (a slight fall to the
    # front and outboard), seated in a dark frame. On the dome's slope they read only as a thin arc
    # at the game camera.
    zref = HZT(8.6) + 0.24

    def vtop(dx, y):
        return zref - 0.06 * (dx - 0.95) - 0.3 * max(0.0, dx - 2.6) - 0.2 * (y - 7.95)
    foot = [(0.95, 7.95), (4.0, 7.95), (4.85, 8.65), (5.0, 9.35), (0.95, 9.35)]
    breaks = [(2.6, 7.95), (2.6, 9.35)]
    for side in (-1, 1):
        for mat, grow, dz in ((BROW, 0.2, -0.13), (VISOR, 0.0, 0.0)):
            cx, cy = 2.9, 8.65
            pts = []
            for dx, y in foot + breaks:
                ex, ey = dx - cx, y - cy
                ln = math.hypot(ex, ey) or 1.0
                gx, gy = dx + ex / ln * grow, y + ey / ln * grow
                gx = max(gx, 0.95 - (0.25 if grow else 0.0)) if dx < 1.0 else gx
                zt = vtop(dx, y) + dz
                ch = 0.12
                ix, iy = dx - ex / ln * ch, y - ey / ln * ch
                pts.append((AX + side * gx, gy, zt - ch))
                pts.append((AX + side * (ix if not grow else gx - ex / ln * ch), iy if not grow else gy - ey / ln * ch, zt))
                pts.append((AX + side * gx, gy, head_top(AX + side * min(gx, HWf(gy) * 0.98), gy) - 0.6))
            hull(M, pts, mat)
    # Brow bar over the visor and the centre post.
    def by0(x):
        return 6.95 + 0.0 * x

    def by1(x):
        return 8.02
    grid_patch(AX - 3.6, AX + 3.6, by0, by1, BROW, 0.24, nx=12, ny=2)
    grid_patch(AX - 0.9, AX + 0.9, lambda x: 7.9, lambda x: 9.15, BROW, 0.24, nx=3, ny=3)
    # Centre keel (fix 1): the sprite's dark centre line (columns 11-12, rows 7-13, pal 50-53) as a
    # chamfered rib along the prow's ridge, from the beak back to the intake.
    rings = []
    for i in range(22):
        y = 6.75 + (13.7 - 6.75) * i / 21
        taper = min(1.0, (i + 1) / 3)
        rings.append([M.v(hs(AX + s_, y, h * taper if h > 0 else h)) for s_, h in
                      ((-0.5, -0.35), (-0.5, 0.08), (-0.3, 0.2), (0.3, 0.2), (0.5, 0.08), (0.5, -0.35))])
    tube(M, rings, GROOVE)
    # Cheek strakes (the bright diagonal, y = 8.2 + dx from column 10 row 9 to column 7 row 12)
    # with a seam rail behind each (the dark diagonal one pixel further back).
    for side in (-1, 1):
        t0, t1 = 1.25, 4.9
        nrm = (side / math.sqrt(2), -1 / math.sqrt(2))
        prof = [(-0.55, -0.4), (-0.55, 0.12), (-0.25, 0.48), (0.2, 0.48), (0.5, 0.12), (0.5, -0.4)]
        mats = [HEAD, HEAD, STRAKE, STRAKE, HEAD, HEAD]
        rings = []
        for i in range(13):
            d = t0 + (t1 - t0) * i / 12
            cx, cy = AX + side * d, 8.35 + d
            taper = min(1.0, (i + 1) / 3, (13 - i) / 3)
            rings.append([M.v(hs(cx + nrm[0] * s, cy + nrm[1] * s, h * taper if h > 0 else h)) for s, h in prof])
        if side > 0:
            rings = [list(reversed(r)) for r in rings]
            mats = list(reversed(mats[:-1])) + [mats[-1]]
        tube(M, rings, lambda i, k, mats=mats: mats[k])
        rings = []
        for i in range(11):
            d = 0.7 + (3.5 - 0.7) * i / 10
            cx, cy = AX + side * d, 10.05 + d
            rings.append([M.v(hs(cx + nrm[0] * s, cy + nrm[1] * s, h)) for s, h in
                          ((-0.32, -0.3), (-0.32, 0.07), (0.32, 0.07), (0.32, -0.3))])
        if side > 0:
            rings = [list(reversed(r)) for r in rings]
        tube(M, rings, SEAM)


def mirror_check():
    pass


def materials(sprite):
    out = []
    for slot in range(len(PAL_OF)):
        met, rough = SPEC[slot]
        out.append(common.palette_material(sprite, PAL_OF[slot], f"{NAME}_{NAMES[slot]}", metallic=met,
                                           roughness=rough, emission_strength=GLOWS.get(slot, 0.0)))
    return out


def build(sprite, coll):
    M = Mesh()
    wing(M)
    arms(M)
    deck(M)
    lobes(M)
    front_deck(M)
    wing_panels(M)
    head(M)
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
    T.TINT, T.TEXTURED = (0.97, 0.98, 1.0), tuple(s for s in range(len(PAL_OF)) if s not in GLOWS)
    try:
        T.bake_maps(obj, out_dir, size=512, samples=96)
    finally:
        T.TINT, T.TEXTURED = tint, textured


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


def top_mask(obj, out):
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
        "front": ((0, d, zc), 2.6, (0, 0, zc)),
        "rear": ((0, -d, zc), 2.6, (0, 0, zc)),
        "q34": ((d * 0.6, d * 0.6, d * 0.65), None, (0, 0, zc)),
        "q34b": ((-d * 0.65, -d * 0.45, d * 0.55), None, (0, 0, zc)),
        "game": ((0, -d * math.sin(tilt), d * math.cos(tilt)), None, (0, 0, zc)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, 0, zc)),
    }
    for name, (loc, ortho, look) in views.items():
        g.hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    obj = build(sprite, coll)
    # D90/D118: the outline shell from the sealed model before culling.
    sh = common.outline_shell(obj, coll, voxel=0.012, faces=1500, smooth=8)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask(obj, views)
        (views / "pal.json").write_text(json.dumps(pal_grid(obj)))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        # Fix 1: the outline shell must not be in the bake. Its hull sits a hair outside the
        # model, so the AO rays hit it and left foil-like blotches; hide it from Cycles while baking.
        sh.hide_render = True
        try:
            bake(obj, Path(tempfile.mkdtemp(prefix="nshg163_bake_")))
        finally:
            sh.hide_render = False
        fmt = "WEBP"
    common.export_sprite_model(WT, [obj, sh], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views)


if __name__ == "__main__":
    main()
