"""SAVARA red fortress centre (newshf.shp, four 2x2 pieces: newshf-157 / -159 top, newshf-195 / -197
bottom, 48x56 px), built cross-section first, as a real armoured machine.

Seen in 6 levels across all four episodes. It is the middle of a wide red flying fortress (the left
part is assembly-newshf-191, the right part assembly-newshf-199). Built whole and cut into the four
pieces (common.split_assembly), each piece one frame and one model.

What it is (D120/D122 identify the object first; DECISIONS D166): the red FLYING gun fortress at the end of
SAVARA, in three sections that separate, not a ground building. In 1.8 and 1.12 SAVARA it holds at
the top of the screen over open sea; event 20 then pushes the two wing
sections (assembly-newshf-191 with newshf-230 on the left, assembly-newshf-199 with newshf-238 on the
right) out sideways at +-6 px/tick and back, while the centre gun module (assembly-newshf-195) roams
on its own; in 1.17 SAVARA V the same pieces spawn on the sky layer. The model already reads as that
from the game camera: armoured hull plating, barrels and turrets over a closed flat underside, with no
foundations, legs or walls down to a ground. So it was not rebuilt, and its pieces and pivots are
unchanged so the split still works.

The sprite is authoritative (D52, D74): the plan follows the inner edge of the sprite's ink border
row by row, every part takes the palette index the sprite uses there (median of its pixels without
the darkest shading and the brightest sheen; blueprint/region_colours.json) and the blueprint
(blueprint/model.js) gives the cross-sections and heights. Coordinates in sprite px: x = column edge
(0..48), y = row edge (0..56, the screen bottom is +y), z up; the mirror plane is x = 24.5 (the
middle of the seam column 24). Blender X = (x - 24) / 12, Y = (28 - y) / 12, Z = z / 12.

The machine:
- Tower (cols 13-35, rows 6-42): a clamshell armoured hull. Cross-section: vertical side walls
  3 px high under a superellipse crown (exponent 2.6) 9.15 px high, split down the middle by a
  real slot (the black seam, col 24, 1.3 px deep). Plan: a rounded nose cap (rows 6-12), a shoulder
  collar at row 13, straight to the rear. On the crown each half carries four bolted armour plates
  standing proud with 45-degree chamfers, the panel lines between them real gaps: the cap plate
  (to the cap groove, rows 14-21), the middle plate (to the chevron), and below the chevron a
  diamond plate (inside the lower V) and the flank plate (outside it). The chevron is a step up
  (the lower plates are thicker), so its edge catches the light: the sprite's lit chevron ridge.
  Door-edge rails either side of the seam from the nose to the chevron (the lit col 22), with a row
  of bolt heads along each.
  The rear (south) end slopes down to an apron ledge over the gun (row 42).
- Wings (cols 1-11 / 37-47, rows 14-42): a box girder deck. Outside, an open trough with two
  coolant pipes of one diameter (cols 1-2 and 5-6 / 42-43 and 46-47, the dark col 3-4 / 44-45 is
  the trough floor in the pipe's shadow) bending down into the deck at both ends, with clamp
  straps at the bars and a slotted clamp block near the top end. Inside, a machined strip: a hatch lid (rows 14-17), a raised cross bar
  (18-21), a groove (22), a raised armour panel (23-38, the dark col 7 a gap at its edge) and a
  raised lower bar (39-42).
- Cooling decks (rows 43-55) in front of each wing: a sloped louvre bank (vanes rows 43-46 and
  48-49, dark gaps 47 and 50-51), a stiffening rib across the vanes, a lit front rail (row 52) and a
  low plinth (53-55).
- Gun bay under the tower's rear (cols 12-36, rows 42-55): a dark floor, an octagonal mantlet under
  the apron, twin barrels (cols 20-23 and 25-28) with collars and muzzle brakes (rows 52-55,
  a recessed bore), dark grey breech housings (cols 14-18 / 30-34) with breech caps, red side
  struts (cols 19 / 35) and a red cheek plate (cols 12-13).
The underside is only closed (every part has its base at z = 0: a flat closed belly), no detail.

Texture: no concept projection; usp_talon.bake_maps (AO and edge colour multiplier, roughness /
metalness map), tint neutral. Outline shell as common.outline_shell (D51; D90's 0.03 voxels held
0.004 inside, 2000 faces), cut into the pieces open.

    blender --background --factory-startup --python assets/blender/enemies/assembly-newshf-195.py --
        [--no-bake] [--out review.glb]

Writes public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json for each piece;
--out also writes the whole block (each piece at its assembly place) to one glb for review.
"""

import bisect
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (Part, hull, cbox, pchip, bake_maps)

WT = common.repo_root(__file__)

NAME = "assembly-newshf-195"
PIECES = ["newshf-157", "newshf-159", "newshf-195", "newshf-197"]
CX0, CY0 = 154, -4  # the block's centre in screen px (the current script's origin)
PX = 1 / 12
# Triangle budget (boss, about 8-20k with the outline shells): the shell's face target (2000 for D90's
# 0.03-voxel shell held inside; at 1000 an ink streak stayed on the dome), the pipes'
# tube sides and the station spacing of the seam rails and chevron bead are where it is trimmed; the
# silhouette and the tower lofts are not touched.
OUTLINE_FACES = 2000
PIPE_SIDES = 10
AX = 24.5  # mirror plane / seam axis (x)

# --- materials: (name, palette index, metallic, roughness) ------------------------------------
SLOTS = [
    ("tower", 71, 0.32, 0.42),
    ("seam", 65, 0.2, 0.7),
    ("rail", 74, 0.35, 0.36),
    ("apron", 67, 0.3, 0.5),
    ("slot", 64, 0.2, 0.75),
    ("wing", 70, 0.3, 0.48),
    ("trench", 65, 0.2, 0.7),
    ("pipe", 74, 0.4, 0.3),
    ("clamp", 72, 0.35, 0.38),
    ("hatch", 68, 0.3, 0.5),
    ("bar_upper", 69, 0.3, 0.45),
    ("groove", 64, 0.2, 0.75),
    ("panel", 70, 0.32, 0.44),
    ("bar_lower", 74, 0.32, 0.42),
    ("deck", 66, 0.25, 0.6),
    ("vane", 68, 0.3, 0.48),
    ("rib", 68, 0.3, 0.48),
    ("lip", 71, 0.32, 0.42),
    ("step", 69, 0.3, 0.5),
    ("bay", 2, 0.4, 0.6),
    ("cheek", 65, 0.25, 0.6),
    ("housing", 4, 0.55, 0.4),
    ("fitting", 5, 0.6, 0.35),
    ("strut", 66, 0.3, 0.5),
    ("barrel", 7, 0.65, 0.3),
    ("muzzle", 8, 0.65, 0.32),
]
(TOWER, SEAM, RAIL, APRON, SLOT, WING, TRENCH, PIPE, CLAMP, HATCH, BARU, GROOVE, PANEL, BARL, DECK, VANE,
 RIB, LIP, STEP, BAY, CHEEK, HOUSING, FITTING, STRUT, BARREL, MUZZLE) = range(len(SLOTS))

pchip = T.pchip


def mirror_x(x):
    return 2 * AX - x


# --- generic builders (sprite px) -------------------------------------------------------------

def ring_normals(pts):
    """Outward 2D normals of a closed loop's edges (any winding)."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    s = 1 if area > 0 else -1  # CCW: outward normal of edge (dx, dz) is (dz, -dx)
    out = []
    for i in range(n):
        (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % n]
        dx, dz = x1 - x0, z1 - z0
        ln = math.hypot(dx, dz) or 1e-9
        out.append((s * dz / ln, -s * dx / ln))
    return out


def loft_y(P, secs, matf, cap0=True, cap1=True, cap_mat=None):
    """Loft closed (x, z) loops along y. secs: [(y, pts)], same point count; matf(k, i) is the
    material of loop edge k between section i and i + 1."""
    rings = []
    for y, pts in secs:
        rings.append([P.v((x, y, z)) for x, z in pts])
    nrm = ring_normals(secs[0][1])
    n = len(rings[0])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        nn = ring_normals(secs[i][1])
        for k in range(n):
            j = (k + 1) % n
            P.f((r0[k], r0[j], r1[j], r1[k]), matf(k, i), out=(nn[k][0], 0, nn[k][1]))
    cm = cap_mat if cap_mat is not None else matf(0, 0)
    if cap0:
        P.f(rings[0], cm, out=(0, -1, 0))
    if cap1:
        P.f(rings[-1], cm, out=(0, 1, 0))
    del nrm


def lathe_y(P, cx, cz, prof, n=16):
    """A solid of revolution about the y axis through (cx, cz): prof [(y, r, mat)], mat for the
    band from this station to the next. Ends closed (r 0 stations allowed)."""
    rings = []
    for y, r, _m in prof:
        if r < 1e-6:
            rings.append([P.v((cx, y, cz))])
        else:
            rings.append([P.v((cx + r * math.cos(2 * math.pi * (k + 0.5) / n), y,
                               cz + r * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)])
    for i in range(len(rings) - 1):
        a, b, m = rings[i], rings[i + 1], prof[i][2]
        y0, y1 = prof[i][0], prof[i + 1][0]
        for k in range(n):
            j = (k + 1) % n
            ang = 2 * math.pi * (k + 1) / n
            radial = (math.cos(ang), 0, math.sin(ang))
            if len(a) == 1 and len(b) == 1:
                continue
            if abs(y1 - y0) < 1e-6:  # a flat annulus (step)
                out = (0, 1 if prof[i + 1][1] < prof[i][1] else -1, 0)
            else:
                dr = prof[i + 1][1] - prof[i][1]
                out = (radial[0], -dr / (y1 - y0) * 0.5, radial[2])
            if len(a) == 1:
                P.f((a[0], b[j], b[k]), m, out=out)
            elif len(b) == 1:
                P.f((a[k], a[j], b[0]), m, out=out)
            else:
                P.f((a[k], a[j], b[j], b[k]), m, out=out)
    if len(rings[0]) > 1:
        P.f(rings[0], prof[0][2], out=(0, -1, 0))
    if len(rings[-1]) > 1:
        P.f(rings[-1], prof[-1][2], out=(0, 1, 0))


def tube(P, path, r, mat, n=12):
    """A closed tube along a 3D polyline (parallel-transport frames)."""
    pts = [Vector(p) for p in path]
    rings = []
    prev_s = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_s is None:
            up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            s = t.cross(up).normalized()
        else:
            s = (prev_s - t * prev_s.dot(t)).normalized()
        u = s.cross(t).normalized()
        prev_s = s
        rings.append([P.v(tuple(p + r * (math.cos(2 * math.pi * (k + 0.5) / n) * s
                                         + math.sin(2 * math.pi * (k + 0.5) / n) * u))) for k in range(n)])
    for i in range(len(rings) - 1):
        c = (pts[i] + pts[i + 1]) / 2
        for k in range(n):
            j = (k + 1) % n
            P.f((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), mat, away=tuple(c))
    t0 = (pts[1] - pts[0]).normalized()
    t1 = (pts[-1] - pts[-2]).normalized()
    P.f(rings[0], mat, out=tuple(-t0))
    P.f(rings[-1], mat, out=tuple(t1))


def box(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def prof_box(P, x0, x1, y0, y1, z0, ztop, ch, mat, step=1.5, chy=None):
    """A box from x0 to x1 whose top follows ztop(y), top edges chamfered all round."""
    chy = ch if chy is None else chy
    ys = [y0, y0 + chy] + [y0 + chy + (y1 - y0 - 2 * chy) * i / max(1, round((y1 - y0 - 2 * chy) / step))
                           for i in range(1, max(1, round((y1 - y0 - 2 * chy) / step)))] + [y1 - chy, y1]
    secs = []
    for i, y in enumerate(ys):
        end = i in (0, len(ys) - 1)
        zt = ztop(y) - (ch if end else 0)
        a, b = (x0 + ch, x1 - ch) if end else (x0, x1)
        secs.append((y, [(a, z0), (b, z0), (b, zt - ch), (b - ch, zt), (a + ch, zt), (a, zt - ch)]))
    loft_y(P, secs, lambda k, i: mat)


# --- the tower: plan, crown and armour plates --------------------------------------------------

HW = pchip([5.65, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.6, 12.6, 13.0, 13.35, 42.5],
           [3.0, 4.5, 5.6, 6.7, 7.6, 8.6, 9.45, 10.1, 10.5, 10.55, 11.05, 11.5, 11.5])
HC = pchip([5.65, 6.5, 7.5, 8.5, 10.0, 13.0, 40.9, 41.5, 42.0, 42.5],
           [3.8, 5.6, 7.0, 8.0, 8.8, 9.15, 9.15, 8.55, 6.9, 5.4])
PEXP = 2.6
NOTCH = 1.3  # seam slot depth below the crown
SEAM_HW = 0.45


def zbase(y):
    return min(3.0, 0.45 * HC(y))


def tz(u, y):
    """Crown height at distance u from the axis."""
    w, h = HW(y), HC(y)
    zb = zbase(y)
    q = min(abs(u) / w, 1.0)
    return zb + (h - zb) * (1 - q ** PEXP) ** (1 / PEXP)


def hull_section(y):
    w = HW(y)
    fr = [1.0, 0.995, 0.98, 0.955, 0.92, 0.87, 0.8, 0.7, 0.58, 0.44, 0.3, 0.16]
    us = [SEAM_HW + (w - SEAM_HW) * f for f in fr] + [SEAM_HW]
    pts = [(AX - w, 0.0)]
    for u in us:
        pts.append((AX - u, tz(u, y)))
    zn = tz(SEAM_HW, y) - NOTCH
    pts += [(AX - SEAM_HW, zn), (AX + SEAM_HW, zn)]
    for u in reversed(us):
        pts.append((AX + u, tz(u, y)))
    pts.append((AX + w, 0.0))
    return pts, len(us)


def build_tower(P):
    ys = TOWER_YS
    secs = []
    for y in ys:
        pts, nu = hull_section(y)
        secs.append((y, pts))
    n = len(secs[0][1])
    nu = hull_section(20)[1]
    # loop edges: 0 left wall, 1..nu crown left, nu+1 notch wall, nu+2 notch floor, nu+3 notch wall,
    # then the crown right, right wall, bottom.
    notch = {nu, nu + 1, nu + 2}

    def matf(k, i):
        if k in notch:
            return SEAM
        if (secs[i][0] + secs[i + 1][0]) / 2 > 41.0 and k not in (0, n - 2, n - 1):
            return APRON
        return TOWER
    loft_y(P, secs, matf, cap_mat=TOWER)

    # Armour plates on each half: regions in (u, y), u = distance from the axis.
    def hp(p, q, inside):
        dx, dy = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(dx, dy)

        def f(u, y):
            return ((u - p[0]) * dy - (y - p[1]) * dx) / ln
        s = 1 if f(*inside) > 0 else -1
        return lambda u, y: s * f(u, y)

    def outline(u, y):
        w = HW(y)
        dw = (HW(y + 0.05) - HW(y - 0.05)) / 0.1
        return min(u - (SEAM_HW + 0.12), (w - 0.8 - u) / math.sqrt(1 + dw * dw), y - 6.35, 40.75 - y)

    g1d = hp((3.8, 14.4), (11.6, 20.8), (11, 25))  # cap groove, diagonal (positive south)

    def s_g1(u, y):
        return min(y - 14.4, g1d(u, y))

    def n_g1(u, y):
        return max(14.4 - y, -g1d(u, y))
    g2 = hp((0, 23.2), (11.6, 32.0), (0, 30))  # chevron (positive south)
    g3 = hp((0, 38.5), (8.7, 29.8), (1, 30))  # lower V (positive inside the V)
    GAP, STEP = 0.36, 0.06
    plates = [  # (region, centre, thickness, material)
        (lambda u, y: min(outline(u, y), n_g1(u, y) - GAP), (4.2, 10.2), 0.45, TOWER),
        (lambda u, y: min(outline(u, y), s_g1(u, y) - GAP, -g2(u, y) - STEP), (5.0, 21.0), 0.4, TOWER),
        (lambda u, y: min(outline(u, y), g2(u, y) - STEP, g3(u, y) - GAP), (2.4, 30.0), 0.9, TOWER),
        (lambda u, y: min(outline(u, y), g2(u, y) - STEP, -g3(u, y) - GAP), (7.6, 36.0), 0.9, TOWER),
    ]
    ue = lambda y: HW(y) - 0.8  # noqa: E731
    for side in (-1, 1):
        for region, centre, d, mat in plates:
            surf_plate(P, region, centre, d, 0.3, 0.7, mat, side)
        # Dark gaskets in the panel lines (the sprite's dark cap groove and lower V).
        groove_strip(P, side, (SEAM_HW + 0.1, 14.4), (3.8, 14.4), GAP)
        groove_strip(P, side, (3.6, 14.4 - 0.16), (11.6, 20.8), GAP, clip=ue)
        groove_strip(P, side, (SEAM_HW + 0.1, 38.5 - SEAM_HW - 0.1), (8.9, 29.6), GAP)
        # The chevron: a raised bead along the lower plates' upper edge (the sprite's lit ridge).
        ridge_strip(P, side, (SEAM_HW + 0.15, 23.2 + 0.76 * (SEAM_HW + 0.15)), (11.6, 32.0), 0.5, 0.95, RAIL, clip=ue)
        # Door-edge rails either side of the seam, nose to chevron, and bolt heads along them.
        rail(P, side, 1.35, 2.65, 6.95, 22.7)
        for y in (8.6, 11.6, 17.4, 20.6):
            bolt(P, AX + side * 2.0, y, max(tz(1.35, y), tz(2.65, y)) + 0.36 + 0.45)


def bolt(P, x, y, z, r=0.36, h=0.26):
    """A hex bolt head sitting on a surface at height z (skirt buried 0.2), top edge chamfered."""
    pts = []
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        c, s_ = math.cos(a), math.sin(a)
        pts += [(x + r * c, y + r * s_, z - 0.2), (x + r * c, y + r * s_, z + h - 0.08),
                (x + (r - 0.1) * c, y + (r - 0.1) * s_, z + h)]
    T.hull(P, pts, CLAMP)


TOWER_YS = [5.65, 5.8, 6.0, 6.25, 6.5, 6.75, 7.0, 7.3, 7.6, 8.0, 8.5, 9.0, 9.6, 10.5, 11.7, 12.6, 12.85, 13.1,
            13.35, 14.5] + [16 + 2 * i for i in range(13)] + [40.4, 40.9, 41.2, 41.5, 41.8, 42.1, 42.5]
_PLATE_CACHE = {}


def _interval(region, y, level, u_max=13.0, du=0.1):
    """The longest run of u (>= 0) on row y where region >= level, ends refined; None if empty."""
    runs, start = [], None
    n = int(u_max / du) + 1
    for i in range(n + 1):
        u = i * du
        ok = i < n and region(u, y) >= level
        if ok and start is None:
            start = u
        elif not ok and start is not None:
            runs.append((start, u - du))
            start = None
    if not runs:
        return None
    a, b = max(runs, key=lambda r: r[1] - r[0])

    def refine(inside, outside):
        for _ in range(16):
            mid = (inside + outside) / 2
            if region(mid, y) >= level:
                inside = mid
            else:
                outside = mid
        return inside
    return refine(a, max(0.0, a - du)), refine(b, b + du)


def _plate_grid(region, c, ncol, ystep):
    """The plate's top as rows of u samples on y stations that follow the tower loft (densified):
    [(y, [u...])], a row of one u where the plate ends in a point."""
    def width(y):
        iv = _interval(region, y, c)
        return -1.0 if iv is None else iv[1] - iv[0]
    ys = [5.0 + 0.1 * i for i in range(381)]
    good = [y for y in ys if width(y) > 0.02]
    y0, y1 = good[0], good[-1]

    def edge(inside, outside):
        for _ in range(16):
            mid = (inside + outside) / 2
            if width(mid) > 0.02:
                inside = mid
            else:
                outside = mid
        return inside
    y0, y1 = edge(y0, y0 - 0.1), edge(y1, y1 + 0.1)
    st = [y0] + [y for y in TOWER_YS if y0 + 0.12 < y < y1 - 0.12] + [y1]
    rows_y = [st[0]]
    for a, b in zip(st, st[1:]):
        lim = ystep(0.5 * (a + b))
        m = max(1, math.ceil((b - a) / lim))
        rows_y += [a + (b - a) * k / m for k in range(1, m + 1)]
    rows = []
    for y in rows_y:
        ua, ub = _interval(region, y, c)
        if ub - ua < 0.25 and y in (rows_y[0], rows_y[-1]):
            rows.append((y, [0.5 * (ua + ub)]))
        else:
            rows.append((y, [ua + (ub - ua) * (0.5 - 0.5 * math.cos(math.pi * k / ncol)) for k in range(ncol + 1)]))
    return rows


def surf_plate(P, region, centre, d, c, depth, mat, side, ncol=10):
    """An armour plate over the crown: region(u, y) >= 0 is the plate (one u interval per row),
    standing d proud of the crown with a 45-degree chamfer c and a skirt `depth` into the hull.
    The top is a (u, y) grid on the tower loft's stations (densified, closer at the nose where the
    plan narrows fast), so it samples the crown evenly and stays a smooth hard shell."""
    key = (id(region), c)
    if key not in _PLATE_CACHE:
        _PLATE_CACHE[key] = _plate_grid(region, c, ncol, lambda y: 0.32 if y < 14.5 else 0.9)
    rows = _PLATE_CACHE[key]
    sx = -1 if side < 0 else 1

    def X(u):
        return AX + sx * u
    top = [[P.v((X(u), y, tz(u, y) + d)) for u in us] for y, us in rows]
    uv = [[(u, y) for u in us] for y, us in rows]
    for r0, r1 in zip(top, top[1:]):
        if len(r0) == 1:
            for k in range(len(r1) - 1):
                P.f((r0[0], r1[k], r1[k + 1]), mat, out=(0, 0, 1))
        elif len(r1) == 1:
            for k in range(len(r0) - 1):
                P.f((r0[k], r0[k + 1], r1[0]), mat, out=(0, 0, 1))
        else:
            for k in range(len(r0) - 1):
                P.f((r0[k], r0[k + 1], r1[k + 1], r1[k]), mat, out=(0, 0, 1))
    # The top's boundary loop: first row, the rows' far ends, last row back, the near ends back.
    loop = [(top[0][k], uv[0][k]) for k in range(len(top[0]))]
    loop += [(top[i][-1], uv[i][-1]) for i in range(1, len(top) - 1)]
    loop += [(top[-1][k], uv[-1][k]) for k in reversed(range(len(top[-1])))]
    loop += [(top[i][0], uv[i][0]) for i in reversed(range(1, len(top) - 1))]
    pts = [q for _v, q in loop]
    nrm = ring_normals(pts)
    n = len(loop)
    ring = []
    for i in range(n):
        a, b = nrm[i - 1], nrm[i]
        nu, ny = a[0] + b[0], a[1] + b[1]
        ln = math.hypot(nu, ny) or 1e-9
        nu, ny = nu / ln, ny / ln
        u0, y0 = pts[i]
        lo, hi = 0.0, 3.0 * c
        for _ in range(18):
            mid = (lo + hi) / 2
            if region(u0 + nu * mid, y0 + ny * mid) >= 0.0:
                lo = mid
            else:
                hi = mid
        u, y = u0 + nu * lo, y0 + ny * lo
        ring.append((P.v((X(u), y, tz(u, y) + d - c)), P.v((X(u), y, tz(u, y) - depth))))
    ucs, ycs = centre
    away = (X(ucs), ycs, tz(ucs, ycs) - 2.0)
    for i in range(n):
        j = (i + 1) % n
        P.f((loop[i][0], loop[j][0], ring[j][0], ring[i][0]), mat, away=away)  # chamfer
        P.f((ring[i][0], ring[j][0], ring[j][1], ring[i][1]), mat, away=away)  # skirt


def groove_strip(P, side, p, q, hw, clip=None, step=0.25, lift=0.1):
    """A dark gasket ribbon lying on the crown along the panel line p -> q (u, y), hw wide each side."""
    sx = -1 if side < 0 else 1
    ln = math.hypot(q[0] - p[0], q[1] - p[1])
    du, dy = (q[0] - p[0]) / ln, (q[1] - p[1]) / ln
    nu, ny = -dy, du
    n = max(1, int(ln / step))
    rows = []
    for i in range(n + 1):
        u, y = p[0] + du * ln * i / n, p[1] + dy * ln * i / n
        if clip and u > clip(y):
            break
        row = []
        for s in (-hw, 0.0, hw):
            uu, yy = u + nu * s, y + ny * s
            row.append(P.v((AX + sx * uu, yy, tz(uu, yy) + lift)))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        P.f((a[0], a[1], b[1], b[0]), SEAM, out=(0, 0, 1))
        P.f((a[1], a[2], b[2], b[1]), SEAM, out=(0, 0, 1))


def ridge_strip(P, side, p, q, hw, h, mat, clip=None, step=0.6, ch=0.22):
    """A chamfered bead standing h above the crown along p -> q (u, y), 2 hw wide, skirts buried."""
    sx = -1 if side < 0 else 1
    ln = math.hypot(q[0] - p[0], q[1] - p[1])
    du, dy = (q[0] - p[0]) / ln, (q[1] - p[1]) / ln
    nu, ny = -dy, du
    n = max(1, int(ln / step))
    prof = [(-hw, -0.6), (-hw, h - ch), (-hw + ch, h), (hw - ch, h), (hw, h - ch), (hw, -0.6)]
    rows = []
    for i in range(n + 1):
        u, y = p[0] + du * ln * i / n, p[1] + dy * ln * i / n
        if clip and u > clip(y):
            break
        zc = tz(u, y)
        row = []
        for s, z in prof:
            uu, yy = u + nu * s, y + ny * s
            row.append(P.v((AX + sx * uu, yy, zc + z)))
        rows.append((row, (AX + sx * u, y, zc - 1.0)))
    for (a, ca), (b, _cb) in zip(rows, rows[1:]):
        for k in range(len(prof) - 1):
            P.f((a[k], a[k + 1], b[k + 1], b[k]), mat, away=ca)
    P.f(list(reversed(rows[0][0])), mat, out=(-sx * du, -dy, 0))
    P.f(rows[-1][0], mat, out=(sx * du, dy, 0))


def rail(P, side, u0, u1, y0, y1, h=0.45, ch=0.2, d=0.36):
    sx = -1 if side < 0 else 1
    xa, xb = sorted((AX + sx * u0, AX + sx * u1))
    ys = [y0, y0 + 0.3] + [y0 + 0.3 + i * 1.0 for i in range(1, int((y1 - y0 - 0.6) / 1.0))] + [y1 - 0.3, y1]
    secs = []
    for i, y in enumerate(ys):
        end = i in (0, len(ys) - 1)
        top = max(tz(u0, y), tz(u1, y)) + d + h - (0.3 if end else 0)
        bot = min(tz(u0, y), tz(u1, y)) - 0.4
        a, b = (xa + ch, xb - ch) if end else (xa, xb)
        secs.append((y, [(a, bot), (b, bot), (b, top - ch), (b - ch, top), (a + ch, top), (a, top - ch)]))
    loft_y(P, secs, lambda k, i: RAIL)


# --- wings, decks, gun bay ----------------------------------------------------------------------

WZ = pchip([14, 22, 34, 43], [4.3, 4.5, 4.9, 4.6])
TROUGH = 1.3  # trough floor below the wing top
PIPE_R = 0.98
DZ = pchip([43, 52], [4.0, 2.8])


def build_wing(P, side):
    m = (lambda x: x) if side < 0 else mirror_x

    def xs(a, b):
        return sorted((m(a), m(b)))
    # Wing body: section across x (left wing; mirrored for the right).
    ys = [14.0, 14.3] + [16 + 2 * i for i in range(13)] + [42.0, 43.0]
    secs = []
    for i, y in enumerate(ys):
        w = WZ(y) - (0.3 if i == 0 else 0)
        zs, zf = w - 0.6, WZ(y) - TROUGH - (0.3 if i == 0 else 0)
        pts = [(1.0, 0.0), (12.0, 0.0), (12.0, zs - 0.2), (11.8, zs), (7.0, zs), (7.0, zf), (1.0, zf)]
        secs.append((y, [(m(x), z) for x, z in pts]))
    mats = [WING, WING, WING, GROOVE, TRENCH, TRENCH, WING]
    loft_y(P, secs, lambda k, i: mats[k], cap_mat=WING)

    # Coolant pipes in the trough, elbows down into the deck at both ends; clamp straps.
    for xc in (2.0, 6.0):
        x = m(xc)
        zc = lambda y: WZ(y) - TROUGH + PIPE_R  # noqa: E731
        R = 1.4
        path = []
        y_n = 14.0 + PIPE_R
        for k in range(7):  # north elbow: from inside the deck up and over
            a = math.pi - (math.pi / 2) * k / 6
            path.append((x, y_n + R + R * math.cos(a), zc(14.5) - R + R * math.sin(a)))
        path.insert(0, (x, y_n, zc(14.5) - R - 1.5))
        for y in [18, 22, 26, 30, 34, 38]:
            path.append((x, y, zc(y)))
        y_s = 43.0 - PIPE_R
        for k in range(7):  # south elbow, down into the deck
            a = (math.pi / 2) * (1 - k / 6)
            path.append((x, y_s - R + R * math.cos(a), zc(42) - R + R * math.sin(a)))
        path.append((x, y_s, zc(42) - R - 1.5))
        tube(P, path, PIPE_R, PIPE, n=PIPE_SIDES)
        for yc in (20.0, 40.8):
            tube(P, [(x, yc - 0.4, zc(yc)), (x, yc + 0.4, zc(yc))], PIPE_R + 0.17, CLAMP, n=PIPE_SIDES)
        # A clamp block near the top end: a base round the pipe's lower half and two jaws over it with
        # a slot between them (the pipe shows through the slot).
        y0, y1 = 16.5, 17.7
        zf, z = WZ(17.1) - TROUGH, zc(17.1)
        a, b = xs(max(1.05, xc - 1.15), min(6.95, xc + 1.15))  # inside the trough (cols 1-6)
        box(P, a, b, y0, y1, zf - 0.1, z + 0.1, 0.12, CLAMP)
        box(P, a, x - 0.14, y0, y1, z, z + PIPE_R + 0.24, 0.12, CLAMP)
        box(P, x + 0.14, b, y0, y1, z, z + PIPE_R + 0.24, 0.12, CLAMP)

    # The machined strip inside the pipes.
    a, b = xs(7.35, 11.65)
    box(P, a, b, 14.35, 17.7, WZ(16) - 1.2, WZ(16) - 0.42, 0.15, HATCH)
    a, b = xs(7.0, 12.0)
    box(P, a, b, 18.0, 22.0, WZ(20) - 1.2, WZ(20) + 0.7, 0.35, BARU)
    a, b = xs(8.0, 12.0)
    prof_box(P, a, b, 23.0, 39.0, WZ(30) - 1.5, lambda y: WZ(y) + 0.25, 0.3, PANEL, step=2.0)
    a, b = xs(7.0, 12.0)
    box(P, a, b, 39.0, 43.0, WZ(41) - 1.2, WZ(41) + 0.8, 0.4, BARL)

    # Cooling deck: louvre bank, rib, lit front rail, plinth.
    lo, hi = xs(1.0, 12.0)
    prof_box(P, lo, hi, 43.0, 52.0, 0.0, lambda y: DZ(y) - 0.35, 0.12, DECK, step=3.0)
    for y0, y1 in ((43.05, 44.0), (44.15, 46.9), (47.9, 49.95)):
        prof_box(P, lo + 0.15, hi - 0.15, y0, y1, DZ(y1) - 1.0, lambda y: DZ(y) + 0.38, 0.2, VANE, step=9)
    a, b = xs(8.5, 10.0)
    prof_box(P, a, b, 43.0, 52.0, DZ(52) - 1.0, lambda y: DZ(y) + 0.62, 0.25, RIB, step=9)
    box(P, lo, hi, 52.0, 53.0, 0.0, 3.1, 0.3, LIP)
    box(P, lo, hi, 53.0, 56.0, 0.0, 2.0, 0.3, STEP)


def build_bay(P):
    # Slots between the wings and the tower.
    box(P, 11.9, 13.3, 13.9, 43.0, 0.0, 2.0, 0.1, SLOT)
    box(P, 35.7, 37.1, 13.9, 43.0, 0.0, 2.0, 0.1, SLOT)
    # Apron ledge over the gun and the mantlet under it.
    box(P, 14.0, 35.0, 41.8, 43.0, 3.0, 5.0, 0.3, APRON)
    box(P, 19.4, 29.6, 41.0, 44.0, 0.6, 3.6, 0.8, APRON)
    # Bay floor, cheek, housings, breech caps, struts, gap floor.
    box(P, 12.0, 37.0, 42.5, 55.0, 0.0, 0.8, 0.1, BAY)
    box(P, 12.0, 14.0, 43.0, 53.0, 0.0, 3.2, 0.25, CHEEK)
    for a, b in ((14.0, 19.0), (29.6, 35.0)):
        box(P, a, b, 43.0, 53.0, 0.0, 3.9, 0.45, HOUSING)
    box(P, 16.0, 19.0, 53.0, 55.0, 0.0, 1.8, 0.3, HOUSING)
    box(P, 29.6, 32.6, 53.0, 55.0, 0.0, 1.8, 0.3, HOUSING)
    box(P, 16.6, 18.6, 47.6, 49.6, 3.5, 4.4, 0.2, FITTING)
    box(P, 30.4, 32.4, 47.6, 49.6, 3.5, 4.4, 0.2, FITTING)
    for a in (19.0, 35.0):
        box(P, a, a + 1.0, 43.0, 52.0, 0.0, 4.2, 0.25, STRUT)
    box(P, 36.0, 37.0, 43.0, 55.0, 0.0, 1.6, 0.1, SLOT)
    # Twin barrels: barrel, collar, muzzle brake with a groove, recessed bore.
    for xc in (22.0, 27.0):
        lathe_y(P, xc, 2.6, [
            (42.0, 1.7, BARREL), (52.0, 1.7, BARREL), (52.0, 1.95, MUZZLE), (52.8, 1.95, MUZZLE),
            (52.8, 1.85, MUZZLE), (54.0, 1.85, MUZZLE), (54.0, 1.62, MUZZLE), (54.35, 1.62, MUZZLE),
            (54.35, 1.85, MUZZLE), (55.75, 1.85, MUZZLE), (55.98, 1.62, MUZZLE), (55.98, 1.0, BAY),
            (55.2, 1.0, BAY), (55.2, 0.0, BAY)], n=16)


# --- assembly ------------------------------------------------------------------------------------

def materials(sprite):
    return [common.palette_material(sprite, pal, f"nshf195_{nm}", metallic=met, roughness=rough)
            for nm, pal, met, rough in SLOTS]


def finish(P, mats, coll):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -24 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(P.smooth_angle))
    return obj


def build(sprite, coll):
    P = T.Part(NAME, smooth_angle=34.0)
    build_tower(P)
    for side in (-1, 1):
        build_wing(P, side)
    build_bay(P)
    obj = finish(P, materials(sprite), coll)
    sharpen_nose_cap(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    return obj


def sharpen_nose_cap(obj):
    """The tower loft's nose is closed by one flat n-gon (y 5.65): mark its rim sharp so the smoothed
    ring next to it doesn't shade the nose's front edge unevenly (the front end stays hard)."""
    me = obj.data
    yb = (28 - TOWER_YS[0]) * PX
    sharp = me.attributes.get("sharp_edge") or me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    ek = {tuple(sorted(e.vertices)): e.index for e in me.edges}
    n = 0
    for poly in me.polygons:
        if poly.loop_total > 8 and poly.normal.y > 0.99 and abs(poly.center.y - yb) < 1e-3:
            vs = list(poly.vertices)
            for i in range(len(vs)):
                sharp.data[ek[tuple(sorted((vs[i], vs[(i + 1) % len(vs)])))]].value = True
            n += 1
    print(f"{NAME}: nose cap rims marked sharp: {n}")


def bake_maps(obj, out_dir, size=1024, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (1.0, 1.0, 1.0)
    T.TEXTURED = tuple(range(len(SLOTS)))
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured


def split_open(obj, layout, coll):
    """Cut an outline shell into the pieces without filling the cuts (no outline along the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def merged_sprite():
    data = common.load_sprite(WT, "newshf-195")
    for name in PIECES:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: body {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nshf195_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it. D90's shell:
    # 0.03 voxels bridge the dome's panel seams, held 0.004 inside the model (at 0.012 its back faces
    # stood out of the seams and drew ink wedges across the dome).
    shell = common.outline_shell(obj, coll, voxel=0.03, faces=OUTLINE_FACES, inside=0.004)
    shell.hide_render = True
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    parts = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    per_piece = {}
    total = 0
    for name, _cx, _cy in layout:
        p, sh = parts[name], shells[name]
        p.name = name
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        sh.name = f"{name}_outline"
        sh.data.shade_smooth()
        sh.hide_render = True
        per_piece[name] = [p, sh]
        t = sum(len(q.vertices) - 2 for q in p.data.polygons)
        ts = sum(len(q.vertices) - 2 for q in sh.data.polygons)
        total += t + ts
        print(f"{NAME}: piece {name}: {t} triangles, outline {ts}")
    print(f"{NAME}: total {total} triangles (outline shells included)")
    # The game export: one model per piece, at its centre (split_assembly), with every frame it covers.
    for name in PIECES:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, per_piece[name], f"enemies/{name}", data["sprites"], image_format=fmt)
    if "--out" in argv:  # the whole block in one glb, each piece at its place, for review
        out = Path(argv[argv.index("--out") + 1])
        export = []
        for name, cx, cy in layout:
            for o in per_piece[name]:
                o.location = (cx / 12, -cy / 12, 0)
                export.append(o)
        common.export_glb(export, out, image_format=fmt)
        for o in export:
            o.location = (0.0, 0.0, 0.0)
        print(f"{NAME}: exported {out}")


if __name__ == "__main__":
    main()
