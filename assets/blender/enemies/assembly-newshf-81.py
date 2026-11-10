"""Twin cannon bunker (newshf.shp: newshf-43 / newshf-81 / newshf-119 per column, two identical
columns side by side, 48 x 66 px; frame 121 = newshf-119-f2, the muzzle flash). DESIGN A:
cross-sections first, built as a real casemate gun emplacement.

The sprite is authoritative (D52, D74): the plan follows the inner edge of the sprite's ink border
(the column is full width from row 0 to row 65, the toe under the muzzle set back to row 65: the
gun-port notch), every part takes the palette index the sprite uses there (blueprint.json
sprite_regions, luma-trimmed median), lamps sit on the sprite's glow pixels. The blueprint
(blueprint/model.js) gives the heights and cross-sections; this script rebuilds them as hard-surface
parts (chamfered lofts, lathes, bent tubes, modelled panel gaps).

Coordinates (one column) in sprite px: x = column edge 0..24 (screen right), y = row edge 0..66
(0 = top of newshf-43, 28 = top of newshf-81, 56 = top of newshf-119; screen down = FRONT), z up,
ground z = 0. Blender X = (x - 12) / 12, Y = (42 - y) / 12, Z = z / 12 (as the current script: the
origin is newshf-81's centre in the left column). The column is cut into its three pieces
(common.split_assembly); the right column uses the same models.

The machine, back to front:
- Armour hood (rows 0-9.7): a gabled roof (eaves z 6.9, ridge z 9 at cols 12.2-13.8) over the gun
  room, a ridge cap strip, K-brace stiffener ribs where the sprite draws its diagonals, raised
  armour plates in the bays, a drip lip along the front eave, and on the rear face a ventilation
  louvre bank and an access door (seen only from behind).
- Side walls (rows 9.5-50): chamfered parapets, split by real expansion gaps, a coping lip on the
  right wall, inner face stepped where the sprite steps.
- Blue pressure tanks on saddles either side of the housing (rows 7-17), domed ends, a pale band,
  bolted hold-down straps, a lamp on each (sprite glow pixels cols 3 / 21).
- Armoured housing (cols 7-18, rows 9.4-18.6): a flat roof plate and sloped front face with a vision
  slit; blue junction box, blue access hatch (hinges, handle, frame groove), grey machinery box,
  valve block with hand-wheels, and the blue rail pipe across the pit mouth on clamps.
- Gun pit (rows 24-50): dark floor; blue junction pylons and pump housings on the walls; the pipe
  rig (bent pipes with flanges, running into the floor), a valve column, the blue manifold drum
  with its two lamps.
- Cannon on the axis col 11.5: a breech on a trunnion cradle, collar, blue recoil band, neck, an
  armoured mantlet, a muzzle brake with side ports and a bore; deck plates either side (rows
  50-57) with panel gaps and a lit lip.
- Front glacis (rows 57-66): sloped louvred face with ribs, a gun-port recess and frame.
- f2 (frame 121): the muzzle flash, emissive palette 117 / 125, on newshf-119-f2 only.
Underside: closed and flat (z = 0), no detail.

    blender --background --factory-startup --python assembly-newshf-81_A.py -- [--no-bake] [--out x.glb]

Exports public/models/enemies/newshf-43, -81, -119 and -119-f2 (newshf-119 plus the flash, frame 121),
each one piece at its own origin with its outline shell (tyrian_outline) and the baked AO/roughness maps
(D50, "bake": "model"). With --out x.glb it writes only a review glb (both columns at their assembly places).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (Part, hull, cbox, bake_maps)

NAME = "assembly-newshf-81"
HERE = Path(__file__).resolve().parent
PIECES = ["newshf-43", "newshf-81", "newshf-119"]
LAYOUT = [("newshf-43", 0, -28), ("newshf-81", 0, 0), ("newshf-119", 0, 28)]
PX = 1 / 12
OUTLINE_FACES = 1400

# Heights (px), blueprint.json heights_px.
Z = dict(plinth=1.5, pit=1.5, wall=6.4, eave=6.9, ridge=9.0, housing=8.2, deck=5.6, glacisTop=4.9, toe=0.7)

# --- materials: (name, palette index, metallic, roughness, emission) ---------------------------
# Indices: the sprite's per-region medians (blueprint.json sprite_regions / colour_check).
SLOTS = [
    ("floor", 1, 0.1, 0.8, 0),       # pit floor, bores, slots
    ("hood", 7, 0.25, 0.45, 0),      # hood roof
    ("hood_lt", 8, 0.25, 0.42, 0),   # roof plates, ridge cap, housing top
    ("rib", 6, 0.25, 0.45, 0),       # hood ribs, eave, lips, mantlet
    ("wall_l", 5, 0.22, 0.5, 0),     # left wall, housing front, grey block, deck ledge
    ("wall_r", 4, 0.22, 0.5, 0),     # right wall, cradles, breech, muzzle, left deck
    ("dark3", 3, 0.2, 0.55, 0),      # machinery, collars, right deck, glacis ribs
    ("dark2", 2, 0.15, 0.65, 0),     # glacis, neck, panel gaps
    ("blue57", 57, 0.25, 0.4, 0),    # left tank, rig pipes
    ("blue56", 56, 0.25, 0.4, 0),    # right tank, hatch, junction box, left post
    ("blue54", 54, 0.25, 0.42, 0),   # straps, rail, posts, pump blocks, band
    ("pale130", 130, 0.25, 0.38, 0),  # tank bands, post caps
    ("deep100", 100, 0.2, 0.5, 0),   # hinges, clamps, grilles, down pipe
    ("deep99", 99, 0.2, 0.5, 0),     # dark pipe to the right wall
    ("blue58", 58, 0.25, 0.4, 0),    # manifold drum
    ("lamp157", 157, 0.0, 0.4, 4.0),
    ("lamp158", 158, 0.0, 0.4, 4.0),
]
(FLOOR, HOOD, HOOD_LT, RIB, WALL_L, WALL_R, DARK3, DARK2, B57, B56, B54, P130, D100, D99, B58,
 L157, L158) = range(len(SLOTS))
TEXTURED = tuple(i for i, s in enumerate(SLOTS) if not s[4])


# --- 2D helpers ---------------------------------------------------------------------------------

def area2(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def inset(p, d):
    """Miter inset of a simple polygon (d > 0 inward)."""
    n, s, out = len(p), (1 if area2(p) > 0 else -1), []
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        e0 = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        e1 = Vector((c[0] - b[0], c[1] - b[1])).normalized()
        n0 = Vector((-e0.y * s, e0.x * s))
        n1 = Vector((-e1.y * s, e1.x * s))
        P0 = Vector(b) + n0 * d
        P1 = Vector(b) + n1 * d
        den = e0.x * e1.y - e0.y * e1.x
        if abs(den) < 1e-6:
            out.append((P1.x, P1.y))
            continue
        t = ((P1.x - P0.x) * e1.y - (P1.y - P0.y) * e1.x) / den
        out.append((P0.x + e0.x * t, P0.y + e0.y * t))
    return out


def edge_normals(p):
    n, s = len(p), (1 if area2(p) > 0 else -1)
    out = []
    for i in range(n):
        (x0, y0), (x1, y1) = p[i], p[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        out.append((s * (y1 - y0) / ln, -s * (x1 - x0) / ln))
    return out


def clip_y(poly, y0, y1):
    """Clip a polygon (x, y) to y0 <= y <= y1."""
    def clip(P, inside, inter):
        o = []
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            ia, ib = inside(a), inside(b)
            if ia:
                o.append(a)
            if ia != ib:
                o.append(inter(a, b))
        return o

    def ly(Y):
        return lambda a, b: (a[0] + (Y - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), Y)
    P = clip(poly, lambda q: q[1] >= y0, ly(y0))
    if P:
        P = clip(P, lambda q: q[1] <= y1, ly(y1))
    out = []
    for q in P:  # drop duplicates
        if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 1e-6:
            out.append(q)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def circ(n, r, rz=None, phase=0.5):
    rz = r if rz is None else rz
    return [(r * math.cos(2 * math.pi * (k + phase) / n), rz * math.sin(2 * math.pi * (k + phase) / n)) for k in range(n)]


# --- 3D builders (sprite px) ------------------------------------------------------------------

AXES = {
    "x": (lambda u, v, a: (a, u, v), (1, 0, 0)),
    "y": (lambda u, v, a: (u, a, v), (0, 1, 0)),
    "z": (lambda u, v, a: (u, v, a), (0, 0, 1)),
}


def _vec(axis, u, v, a):
    return AXES[axis][0](u, v, a)


def ext(P, sec, axis, a0, a1, mat, ch0=0.3, ch1=0.3, matf=None, cap_mat=None, end_mat=None):
    """Extrude a section (u, v) along `axis` from a0 to a1, each end chamfered (the section inset by
    ch and the end set in by ch). axis 'x': sec (y, z); 'y': (x, z); 'z': (x, y)."""
    rings = []
    if ch0 > 0:
        rings.append((a0, inset(sec, ch0), -1))
    rings.append((a0 + ch0, list(sec), 0))
    rings.append((a1 - ch1, list(sec), 0))
    if ch1 > 0:
        rings.append((a1, inset(sec, ch1), 1))
    nrm = edge_normals(sec)
    vs = [[P.v(_vec(axis, u, v, a)) for u, v in pts] for a, pts, _ in rings]
    n = len(sec)
    for i in range(len(rings) - 1):
        end = rings[i][2] if rings[i][2] else rings[i + 1][2]
        for k in range(n):
            j = (k + 1) % n
            nu, nv = nrm[k]
            out = _vec(axis, nu, nv, 0.0)
            ad = AXES[axis][1]
            out = tuple(out[q] + ad[q] * end * 0.8 for q in range(3))
            m = matf(k) if matf else mat
            if end_mat is not None and end == 1:
                m = end_mat
            P.f((vs[i][k], vs[i][j], vs[i + 1][j], vs[i + 1][k]), m, out=out)
    ad = AXES[axis][1]
    cm = mat if cap_mat is None else cap_mat
    P.f(vs[0], cm, out=tuple(-c for c in ad))
    P.f(vs[-1], cm, out=ad)


def slab(P, poly, z0, zt, ch, mat, top_mat=None):
    """A plan polygon extruded up from z0 to zt, its top edges chamfered by ch (bottom square)."""
    ext(P, poly, "z", z0, zt, mat, ch0=0.0, ch1=ch, cap_mat=None)
    if top_mat is not None:  # a thin top skin in another colour (no z-fight: a hair above)
        ip = inset(poly, ch)
        ext(P, ip, "z", zt - 0.05, zt + 0.02, top_mat, ch0=0.0, ch1=0.0)


def box(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def lathe(P, axis, cu, cv, prof, n=16, inward=()):
    """Solid of revolution along `axis` through (cu, cv) in the cross plane. prof [(a, r, mat)] or
    (a, r, mat, rv) for an elliptic section; mat is the band from this station to the next. Bands
    listed in `inward` (index of their first station) are inner surfaces (a bore or a countersunk
    crown that turns back into the solid): their outward hint points at the axis."""
    rings = []
    for st in prof:
        a, r = st[0], st[1]
        rv = st[3] if len(st) > 3 else r
        if r < 1e-6:
            rings.append([P.v(_vec(axis, cu, cv, a))])
        else:
            rings.append([P.v(_vec(axis, cu + du, cv + dv, a)) for du, dv in circ(n, r, rv)])
    ad = AXES[axis][1]
    for i in range(len(rings) - 1):
        A, B, m = rings[i], rings[i + 1], prof[i][2]
        a0, a1 = prof[i][0], prof[i + 1][0]
        for k in range(n):
            j = (k + 1) % n
            ang = 2 * math.pi * (k + 1) / n
            rad = _vec(axis, math.cos(ang), math.sin(ang), 0.0)
            if i in inward:
                out = tuple(-rad[q] + ad[q] * 0.5 for q in range(3))
            elif abs(a1 - a0) < 1e-6:
                s = 1 if prof[i + 1][1] < prof[i][1] else -1
                out = tuple(c * s for c in ad)
            else:
                dr = (prof[i + 1][1] - prof[i][1]) / (a1 - a0)
                out = tuple(rad[q] - ad[q] * dr * 0.5 for q in range(3))
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                P.f((A[0], B[j], B[k]), m, out=out)
            elif len(B) == 1:
                P.f((A[k], A[j], B[0]), m, out=out)
            else:
                P.f((A[k], A[j], B[j], B[k]), m, out=out)
    if len(rings[0]) > 1:
        P.f(rings[0], prof[0][2], out=tuple(-c for c in ad))
    if len(rings[-1]) > 1:
        P.f(rings[-1], prof[-1][2], out=ad)


def rounded_path(pts, r, seg=4):
    """A polyline with its corners rounded (radius r, seg samples per bend)."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (b - a), (c - b)
        rr = min(r, d0.length * 0.45, d1.length * 0.45)
        p0 = b - d0.normalized() * rr
        p1 = b + d1.normalized() * rr
        for k in range(seg + 1):  # quadratic Bezier through the corner
            t = k / seg
            out.append(p0 * (1 - t) ** 2 + b * 2 * t * (1 - t) + p1 * t * t)
    out.append(pts[-1])
    return out


def tube(P, path, r, mat, n=10):
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
    P.f(rings[0], mat, out=tuple(-(pts[1] - pts[0]).normalized()))
    P.f(rings[-1], mat, out=tuple((pts[-1] - pts[-2]).normalized()))


def flange(P, axis, cu, cv, a, r, mat, w=0.35, n=10):
    lathe(P, axis, cu, cv, [(a - w / 2, r * 0.85, mat), (a - w / 2 + 0.08, r, mat), (a + w / 2 - 0.08, r, mat),
                            (a + w / 2, r * 0.85, mat)], n=n)


def bolt(P, x, y, z, r=0.28, h=0.2, mat=WALL_R):
    lathe(P, "z", x, y, [(z - 0.1, r, mat), (z + h * 0.7, r, mat), (z + h, r * 0.7, mat)], n=6)


def strip(P, f, xa, ya, xb, yb, w, h, mat):
    """A raised chamfered strip lying on a planar surface z = f(x, y)."""
    d = Vector((xb - xa, yb - ya))
    L = d.length
    nx, ny = -d.y / L * w / 2, d.x / L * w / 2
    q = [(xa - nx, ya - ny), (xb - nx, yb - ny), (xb + nx, yb + ny), (xa + nx, ya + ny)]
    ins = inset(q, min(w * 0.3, 0.18))
    pts = [(x, y, f(x, y) - 0.15) for x, y in q] + [(x, y, f(x, y) + h * 0.6) for x, y in q] + \
          [(x, y, f(x, y) + h) for x, y in ins]
    T.hull(P, pts, mat)


def plate_on(P, f, poly, h, mat, ch=0.2):
    pts = [(x, y, f(x, y) - 0.1) for x, y in poly] + [(x, y, f(x, y) + h * 0.5) for x, y in poly] + \
          [(x, y, f(x, y) + h) for x, y in inset(poly, ch)]
    T.hull(P, pts, mat)


def lamp(P, x, y, z, r, mat, bezel=WALL_R):
    """A glowing dome lamp in a thin bezel ring."""
    lathe(P, "z", x, y, [(z - 0.3, r + 0.18, bezel), (z + 0.08, r + 0.18, bezel), (z + 0.12, r + 0.05, mat),
                         (z + 0.12 + r * 0.45, r * 0.75, mat), (z + 0.12 + r * 0.7, 0.0, mat)], n=8)


# --- the column ---------------------------------------------------------------------------------

def roof(x, y=0.0):
    if x <= 12.2:
        return Z["eave"] + (x - 0.6) * (Z["ridge"] - Z["eave"]) / (12.2 - 0.6)
    if x >= 13.8:
        return Z["eave"] + (23.4 - x) * (Z["ridge"] - Z["eave"]) / (23.4 - 13.8)
    return Z["ridge"]


def build_hood(P):
    # Gabled hood: section in (x, z) along y, the front end chamfered (the lit eave line, row 9).
    sec = [(0, 0.0), (24, 0.0), (24, Z["wall"]), (23.4, Z["eave"]), (13.8, Z["ridge"]), (12.2, Z["ridge"]),
           (0.6, Z["eave"]), (0, Z["wall"])]
    ext(P, sec, "y", 0.25, 9.7, HOOD, ch0=0.12, ch1=0.55, end_mat=RIB)
    # Ridge cap (pal 8, col 13) and the panel line left of it.
    rz = Z["ridge"]
    ext(P, [(12.5, rz - 0.3), (14.0, rz - 0.3), (14.0, rz + 0.25), (13.7, rz + 0.45), (12.8, rz + 0.45),
            (12.5, rz + 0.25)], "y", 0.3, 9.35, HOOD_LT, ch0=0.1, ch1=0.25)
    ext(P, [(12.0, rz - 0.2), (12.5, rz - 0.2), (12.5, rz + 0.08), (12.0, rz + 0.08)], "y", 0.35, 9.2, RIB, 0.05, 0.1)
    # K-brace stiffener ribs (pal 6) on the roof slopes, traced from the sprite's diagonals.
    for a, b, w, h in (((3.4, 0.45), (7.6, 4.9), 0.9, 0.45), ((7.6, 4.9), (3.6, 9.1), 0.9, 0.45),
                       ((7.6, 4.9), (10.6, 9.1), 0.9, 0.45), ((21.5, 0.45), (17.5, 4.9), 0.9, 0.45),
                       ((17.5, 4.9), (15.4, 9.1), 0.9, 0.45), ((17.5, 4.9), (19.8, 7.0), 0.8, 0.4),
                       ((0.5, 5.5), (6.2, 5.5), 0.8, 0.3)):
        strip(P, roof, a[0], a[1], b[0], b[1], w, h, RIB)
    # Gusset bosses where the K-braces meet.
    for x, y in ((7.6, 4.9), (17.5, 4.9)):
        lathe(P, "z", x, y, [(roof(x) - 0.1, 0.75, RIB), (roof(x) + 0.5, 0.75, RIB), (roof(x) + 0.62, 0.55, RIB)], n=8)
    # Raised armour plates in the bays (pal 8), bolted at the corners.
    for poly in ([(0.7, 0.8), (3.2, 0.8), (6.5, 4.6), (0.7, 4.6)],
                 [(0.7, 6.2), (5.0, 6.2), (3.3, 8.9), (0.7, 8.9)],
                 [(22.0, 1.0), (23.2, 1.0), (23.2, 6.6), (19.6, 6.6), (18.6, 5.6)]):
        plate_on(P, roof, poly, 0.28, HOOD_LT)
    for x, y in ((1.4, 1.5), (1.4, 4.0), (1.4, 6.9), (1.4, 8.3), (22.6, 1.7), (22.6, 6.0)):
        bolt(P, x, y, roof(x) + 0.2, r=0.22, h=0.16, mat=RIB)
    # Front eave drip lip (pal 6), either side of the housing.
    for x0, x1 in ((0.0, 7.0), (18.6, 24.0)):
        ext(P, [(9.25, Z["wall"] - 0.65), (9.95, Z["wall"] - 0.65), (9.95, Z["wall"] - 0.15), (9.25, Z["wall"] + 0.1)],
            "x", x0, x1, RIB, ch0=0.1, ch1=0.1)
    # Rear face (y = 0, seen from behind only): a louvre bank and an access door with a frame.
    for z in (2.2, 3.1, 4.0):
        # (everything stays at y >= 0: the piece cut at row 0 would clip it)
        for x0, x1 in ((2.6, 9.6), (16.4, 22.6)):
            box(P, x0, x1, 0.12, 0.3, z - 0.32, z + 0.32, 0.06, DARK2)  # louvre opening
            ext(P, [(0.02, z - 0.28), (0.3, z - 0.28), (0.3, z + 0.3), (0.12, z + 0.3)], "x", x0 + 0.15, x1 - 0.15,
                DARK3, 0.08, 0.08)
        box(P, 2.3, 9.9, 0.08, 0.3, 1.5, 4.7, 0.08, RIB)  # louvre frames
        box(P, 16.1, 22.9, 0.08, 0.3, 1.5, 4.7, 0.08, RIB)
    box(P, 10.6, 15.4, 0.0, 0.3, 0.3, 5.6, 0.1, RIB)  # door frame
    box(P, 11.2, 14.8, 0.1, 0.3, 0.8, 5.1, 0.08, WALL_R)  # door panel, set in
    box(P, 14.0, 14.4, 0.0, 0.15, 2.6, 3.4, 0.05, DARK3)  # door handle
    for zb in (1.4, 4.5):  # hinges
        box(P, 11.0, 11.5, 0.02, 0.15, zb - 0.3, zb + 0.3, 0.05, DARK3)


def build_walls(P):
    lw = [(0.3, 9.5), (3.0, 9.5), (3.0, 17.0), (2.6, 17.0), (2.6, 29.0), (1.0, 29.0), (1.0, 36.0), (3.0, 36.0),
          (3.0, 41.0), (1.0, 41.0), (1.0, 47.5), (2.0, 47.5), (2.0, 50.2), (0.3, 50.2)]
    rw = [(23.0, 9.5), (23.7, 9.5), (23.7, 50.2), (22.0, 50.2), (22.0, 47.5), (23.0, 47.5), (23.0, 41.0), (21.0, 41.0),
          (21.0, 36.0), (23.0, 36.0), (23.0, 29.0), (21.0, 29.0), (21.0, 17.2), (23.0, 17.2)]
    # Expansion gaps (real 0.3 px slots down to the plinth): the parapets are cast in sections.
    for poly, mat, cuts in ((lw, WALL_L, (9.5, 22.3, 38.3, 50.2)), (rw, WALL_R, (9.5, 25.3, 38.3, 50.2))):
        for y0, y1 in zip(cuts, cuts[1:]):
            g0 = y0 + (0.15 if y0 > 9.6 else 0)
            g1 = y1 - (0.15 if y1 < 50 else 0)
            part = clip_y(poly, g0, g1)
            if len(part) >= 3:
                slab(P, part, Z["pit"] - 0.1, Z["wall"], 0.3, mat)
    # Coping lip on the right wall (the lit col 23).
    ext(P, rect(23.0, 17.3, 23.75, 49.9), "z", Z["wall"] - 0.1, Z["wall"] + 0.3, RIB, 0.0, 0.15)
    # Outer faces: the parapet stands 0.3 px in from the plinth's edge on a chamfered foot ledge.
    box(P, 0.0, 0.9, 9.6, 50.1, 0.0, 2.4, 0.3, DARK3)
    box(P, 23.1, 24.0, 9.6, 50.1, 0.0, 2.4, 0.3, DARK3)
    # Buttress ribs on the outer faces, between the expansion gaps (within the 0.3 px set-back).
    for y in (13.5, 18.5, 26.5, 32.5, 42.0, 46.5):
        box(P, 0.02, 0.6, y - 0.45, y + 0.45, 2.0, Z["wall"] - 0.5, 0.12, WALL_L)
        box(P, 23.4, 23.98, y - 0.45, y + 0.45, 2.0, Z["wall"] - 0.5, 0.12, WALL_R)


def build_tanks(P):
    for xc, y0, y1, lx, lp, mat, nm in ((5.0, 7.8, 17.2, 3.25, L158, B57, "l"), (21.0, 6.8, 17.0, 21.6, L157, B56, "r")):
        zc, r = 5.6, 2.0
        # Saddles on a sill (pal 4): the tank sits in them.
        box(P, xc - 2.0, xc + 2.0, y0 + 1.4, y1 - 1.0, Z["pit"], Z["pit"] + 0.8, 0.2, WALL_R)
        for ys in (y0 + 2.2, y1 - 2.2):
            box(P, xc - 1.9, xc + 1.9, ys - 0.5, ys + 0.5, Z["pit"], zc - 1.1, 0.15, WALL_R)
        # The tank: elliptic domed ends.
        prof = []
        for k in range(6):
            a = k / 5 * math.pi / 2
            prof.append((y0 + 1.4 * (1 - math.cos(a)), 0.35 + (r - 0.35) * math.sin(a), mat))
        for k in range(5, -1, -1):
            a = k / 5 * math.pi / 2
            prof.append((y1 - 1.4 * (1 - math.cos(a)), 0.35 + (r - 0.35) * math.sin(a), mat))
        lathe(P, "y", xc, zc, prof, n=16)
        # Filler valve on the back dome.
        lathe(P, "y", xc, zc, [(y0 - 0.35, 0.3, WALL_R), (y0 + 0.2, 0.3, WALL_R), (y0 + 0.2, 0.42, WALL_R),
                               (y0 + 0.5, 0.42, WALL_R)], n=8)
        # Pale band near the back (rows 8-10) and the bolted hold-down strap (pal 54).
        lathe(P, "y", xc, zc, [(y0 + 1.2, r + 0.03, P130), (y0 + 1.27, r + 0.18, P130), (y0 + 2.3, r + 0.18, P130),
                               (y0 + 2.37, r + 0.03, P130)], n=16)
        lathe(P, "y", xc, zc, [(y1 - 2.6, r + 0.03, B54), (y1 - 2.55, r + 0.15, B54), (y1 - 1.9, r + 0.15, B54),
                               (y1 - 1.85, r + 0.03, B54)], n=16)
        for sx in (-1, 1):
            box(P, xc + sx * (r + 0.05) - 0.3, xc + sx * (r + 0.05) + 0.3, y1 - 2.65, y1 - 1.8, zc - 1.6, zc - 0.6, 0.08, B54)
        a = math.acos(max(-1, min(1, (lx - xc) / r)))
        lamp(P, lx, 12.5, zc + r * math.sin(a) - 0.3, 0.5, lp, bezel=mat)


def build_housing(P):
    # Armoured housing: section (y, z) along x, sloped front.
    sec = [(9.4, Z["pit"]), (18.6, Z["pit"]), (18.6, 4.4), (18.0, 4.6), (13.9, Z["housing"]), (9.4, Z["housing"])]
    ext(P, sec, "x", 7.0, 18.0, HOOD_LT, 0.45, 0.45, matf=lambda k: WALL_L if k in (2, 3) else HOOD_LT)
    # Roof plate: a raised chamfered plate (its edge a real step line).
    box(P, 7.8, 17.2, 10.2, 13.6, Z["housing"] - 0.2, Z["housing"] + 0.25, 0.2, HOOD_LT)
    # The slope's skin (pal 5) and a vision slit across it.
    s0, s1 = Vector((13.9, Z["housing"])), Vector((18.0, 4.6))
    nrm = Vector((s1.y - s0.y, -(s1.x - s0.x))).normalized() * -1  # outward (forward/up)
    if nrm.y < 0:
        nrm = -nrm
    a0, a1 = s0 + (s1 - s0) * 0.05, s1 - (s1 - s0) * 0.02
    skin = [tuple(a0 - nrm * 0.05), tuple(a1 - nrm * 0.05), tuple(a1 + nrm * 0.12), tuple(a0 + nrm * 0.12)]
    ext(P, skin, "x", 7.5, 17.5, WALL_L, 0.1, 0.1)
    m0, m1 = s0 + (s1 - s0) * 0.38, s0 + (s1 - s0) * 0.5
    slit = [tuple(m0 + nrm * 0.0), tuple(m1 + nrm * 0.0), tuple(m1 + nrm * 0.22), tuple(m0 + nrm * 0.3)]
    ext(P, slit, "x", 9.0, 16.5, DARK3, 0.05, 0.05)
    # Step at the foot (row 18).
    slab(P, rect(7.0, 17.8, 15.0, 19.2), Z["pit"], 4.5, 0.2, WALL_R)
    box(P, 15.0, 18.0, 17.6, 19.8, Z["pit"], 5.0, 0.3, B56)  # junction box
    box(P, 15.6, 17.4, 17.9, 19.5, 4.9, 5.3, 0.12, B56)
    # Access hatch (blue, rows 19-24) with a frame groove, a handle and hinge knuckles.
    box(P, 7.0, 13.0, 19.2, 25.0, Z["pit"], 3.6, 0.3, B56)
    box(P, 7.35, 12.65, 19.55, 24.65, 3.4, 4.0, 0.25, B56)
    box(P, 7.6, 12.4, 23.95, 24.25, 3.95, 4.04, 0.05, B54)
    box(P, 9.0, 11.0, 21.0, 21.5, 3.95, 4.3, 0.1, B54)
    for x in (7.8, 11.2):
        lathe(P, "x", 19.6, 4.0, [(x, 0.4, D100), (x + 1.0, 0.4, D100)], n=8)
    for x, y in ((7.9, 24.0), (12.1, 24.0), (12.1, 20.6)):
        bolt(P, x, y, 3.95, r=0.2, h=0.14, mat=B54)
    # Grey machinery box beside the hatch with its top seam.
    box(P, 13.0, 18.0, 19.8, 25.0, Z["pit"], 3.6, 0.3, WALL_L)
    box(P, 13.3, 17.7, 20.0, 20.45, 3.5, 3.66, 0.05, DARK3)
    box(P, 14.2, 16.8, 21.6, 24.0, 3.5, 3.85, 0.15, WALL_L)
    # Rail pipe across the pit mouth (row 26) on clamps, its ends turning down into the floor.
    tube(P, rounded_path([(7.0, 26.4, Z["pit"]), (7.0, 26.4, 2.3), (12.4, 26.4, 2.3), (12.4, 26.4, Z["pit"])], 0.6), 0.68, B54)
    tube(P, rounded_path([(13.1, 26.4, Z["pit"]), (13.1, 26.4, 2.3), (17.9, 26.4, 2.3), (17.9, 26.4, Z["pit"])], 0.6), 0.68, B54)
    for x in (9.6, 15.4):
        box(P, x, x + 0.6, 25.7, 27.1, Z["pit"], 3.15, 0.12, D100)
    # Valve block left of the hatch with three hand-wheel valves.
    box(P, 2.6, 7.0, 17.6, 24.0, Z["pit"], 3.4, 0.25, DARK3)
    for x, y in ((3.7, 19.3), (5.7, 20.8), (3.9, 22.4)):
        lathe(P, "z", x, y, [(3.3, 0.3, WALL_L), (3.9, 0.3, WALL_L), (3.9, 0.55, WALL_L), (4.1, 0.55, WALL_L),
                             (4.15, 0.2, WALL_L), (4.3, 0.2, WALL_L)], n=8)


def build_pit(P):
    # Floor plates (dark, pal 2 seams) in the pit.
    for y in (30.5, 37.2):
        box(P, 3.4, 20.6, y, y + 0.3, Z["pit"] - 0.05, Z["pit"] + 0.06, 0.03, DARK2)
    # Blue junction pylons on the walls (rows 29-35), rounded tops, pale cap band.
    for x0, x1, mat in ((1.0, 4.0, B56), (20.0, 23.0, B54)):
        xc, hw = (x0 + x1) / 2, (x1 - x0) / 2
        sec = [(x0, Z["pit"]), (x1, Z["pit"]), (x1, 6.0)]
        for k in range(1, 8):
            a = k / 8 * math.pi
            sec.append((xc + hw * math.cos(a), 6.0 + 1.2 * math.sin(a)))
        sec.append((x0, 6.0))
        ext(P, sec, "y", 29.0, 35.6, mat, 0.35, 0.35)
        lathe(P, "y", xc, 6.0, [(29.8, hw * 0.9, P130, 1.1), (29.85, hw + 0.1, P130, 1.3), (30.7, hw + 0.1, P130, 1.3),
                                (30.75, hw * 0.9, P130, 1.1)], n=10)
        # Cable gland on the pylon's pit-side face.
        lathe(P, "x", 32.6, 4.0, [((x1 if x0 < 10 else x0) - 0.1 * (1 if x0 < 10 else -1), 0.45, D100),
                                  ((x1 + 0.35) if x0 < 10 else (x0 - 0.35), 0.45, D100)], n=8)
    lamp(P, 20.6, 29.6, 6.75, 0.45, L158, bezel=B54)
    # Blue pump housings on the walls (rows 41-46) with grille fins.
    for x0, x1 in ((1.0, 5.0), (19.8, 23.2)):
        box(P, x0, x1, 41.0, 47.2, Z["pit"], 5.0, 0.4, B54)
        for y in (42.6, 44.0, 45.4):  # grille fins (thin: the housing's blue reads, as in the sprite)
            box(P, x0 + 0.6, x1 - 0.6, y, y + 0.35, 4.8, 5.25, 0.08, D100)
    # The pipe rig: pipes with flanges, running into the floor at their ends.
    tube(P, rounded_path([(10.0, 36.6, Z["pit"]), (10.0, 36.6, 3.0), (10.0, 41.6, 3.0)], 0.7), 0.8, B57, n=8)
    tube(P, rounded_path([(6.5, 39.8, Z["pit"]), (6.5, 39.8, 3.0), (10.0, 39.8, 3.0)], 0.6), 0.7, B57, n=8)
    tube(P, rounded_path([(14.5, 37.4, Z["pit"]), (14.5, 37.4, 2.8), (14.5, 44.6, 2.8)], 0.6), 0.55, B57, n=8)
    tube(P, rounded_path([(16.5, 37.4, Z["pit"]), (16.5, 37.4, 2.8), (16.5, 44.2, 2.8)], 0.6), 0.55, B54, n=8)
    tube(P, rounded_path([(16.5, 38.7, 2.8), (20.8, 38.7, 2.8), (20.8, 38.7, Z["pit"] + 0.2)], 0.6), 0.65, D99, n=8)
    flange(P, "y", 10.0, 3.0, 40.2, 1.0, B57, n=8)
    flange(P, "y", 14.5, 2.8, 41.0, 0.75, B57, n=8)
    flange(P, "y", 16.5, 2.8, 41.6, 0.75, B54, n=8)
    flange(P, "x", 38.7, 2.8, 19.0, 0.85, D99, n=8)
    # Valve column (grey, cols 12-13) with a cap.
    box(P, 12.0, 14.0, 36.4, 42.0, Z["pit"], 4.4, 0.25, WALL_R)
    lathe(P, "z", 13.0, 37.6, [(4.3, 0.55, WALL_R), (4.75, 0.55, WALL_R), (4.85, 0.35, WALL_R)], n=8)
    # Manifold drum across the breech (rows 42-43), with domed ends, and its arm to the right.
    lathe(P, "x", 43.0, 3.2, [(7.7, 0.6, B58), (7.85, 1.05, B58), (8.1, 1.25, B58), (12.7, 1.25, B58),
                              (12.95, 1.05, B58), (13.1, 0.6, B58)], n=12)
    lathe(P, "x", 43.0, 3.0, [(13.0, 0.8, B57), (17.6, 0.8, B57)], n=10)
    flange(P, "x", 43.0, 3.0, 15.2, 1.0, B57, n=8)
    for x in (8.6, 11.6):
        lamp(P, x, 43.8, 4.0, 0.5, L157, bezel=B58)
    tube(P, rounded_path([(8.5, 43.8, 2.6), (8.5, 47.6, 2.6), (8.5, 47.6, Z["pit"])], 0.5), 0.5, D100, n=8)
    tube(P, rounded_path([(14.0, 43.8, 2.6), (14.0, 48.0, 2.6), (14.0, 48.0, Z["pit"])], 0.5), 0.5, B54, n=8)


CX, CZ = 11.5, 3.7


def build_cannon(P):
    box(P, 9.4, 13.6, 46.2, 50.0, Z["pit"], CZ - 0.6, 0.2, DARK3)  # trunnion cradle
    for sx in (-1, 1):  # trunnion pins
        lathe(P, "x", 48.0, CZ - 0.3, [(CX + sx * 1.5, 0.45, DARK3), (CX + sx * 2.3, 0.45, DARK3)], n=8)
    # Breech, collar, blue recoil band, neck and the barrel (rows 53.5-62): one closed lathe. The barrel
    # is a round tube, slim where the sprite draws it 3 px wide (row 54), then a slightly flared round
    # muzzle sleeve (4 px, rows 55-61) with a raised band, a rounded lip and a countersunk crown
    # turning into the dark bore at row 62.
    ring = WALL_R
    lathe(P, "y", CX, CZ, [
        (45.8, 0.9, WALL_R), (45.9, 1.3, WALL_R), (46.2, 1.5, WALL_R), (46.5, 1.6, WALL_R), (49.6, 1.6, WALL_R),
        (50.0, 1.4, DARK3), (50.0, 1.2, DARK3), (51.0, 1.2, B54), (51.0, 1.5, B54), (51.2, 1.75, B54),
        (52.8, 1.75, B54), (53.0, 1.5, DARK2), (53.0, 1.2, DARK2),
        (53.5, 1.2, RIB), (53.6, 1.6, RIB), (54.7, 1.65, RIB), (55.3, 1.95, RIB), (57.7, 2.0, ring),
        (57.75, 2.12, ring), (58.35, 2.12, ring), (58.4, 2.0, RIB), (61.3, 2.0, ring), (61.6, 2.12, ring),
        (61.9, 2.05, ring), (62.05, 1.85, ring), (62.05, 1.45, FLOOR), (61.2, 0.95, FLOOR),
        (61.2, 0.0, FLOOR)], n=18, inward=(25,))
    # Breech block cap (screw plug) on the back.
    lathe(P, "y", CX, CZ, [(45.5, 0.0, DARK3), (45.5, 0.6, DARK3), (45.9, 0.6, DARK3)], n=10)


def build_deck(P):
    for x0, x1, mat in ((0.0, 9.0, WALL_R), (14.0, 24.0, DARK3)):
        sec = [(49.8, Z["pit"]), (57.3, Z["pit"]), (57.3, Z["deck"] - 0.25), (57.05, Z["deck"]), (51.0, Z["deck"]),
               (49.8, Z["deck"] - 1.0)]
        # Three plates per side, split by real panel gaps (rows 53 and 55.6).
        dk, pit = Z["deck"], Z["pit"]
        c0, c1 = (0.0, 0.3) if x0 == 0 else (0.3, 0.0)
        ext(P, [(49.8, pit), (53.0, pit), (53.0, dk - 0.12), (52.88, dk), (51.0, dk), (49.8, dk - 1.0)], "x", x0, x1, mat, c0, c1)
        ext(P, [(53.3, pit), (55.6, pit), (55.6, dk - 0.12), (55.48, dk), (53.42, dk), (53.3, dk - 0.12)], "x", x0, x1, mat, c0, c1)
        ext(P, [(55.9, pit), (57.3, pit), (57.3, dk - 0.25), (57.05, dk), (56.02, dk), (55.9, dk - 0.12)], "x", x0, x1, mat, c0, c1)
        box(P, x0 + 0.2, x1 - 0.2, 52.9, 55.95, Z["pit"], Z["deck"] - 0.6, 0.05, DARK2)  # gap floors (end off the 119 seam at row 56)
        for xb in ((2.0, 7.0) if x0 == 0 else (16.0, 22.0)):
            for yb in (54.45,):
                bolt(P, xb, yb, Z["deck"] - 0.05, r=0.24, h=0.14, mat=mat)
    for x0, x1 in ((0.3, 8.6), (18.5, 23.7)):  # lit lip on the deck's back edge (row 51)
        ext(P, [(50.6, Z["deck"] - 0.35), (51.4, Z["deck"]), (51.4, Z["deck"] + 0.12), (50.6, Z["deck"] - 0.2)],
            "x", x0, x1, RIB, 0.1, 0.1)
    box(P, 3.0, 9.0, 49.6, 50.9, Z["pit"], Z["deck"] - 0.2, 0.25, WALL_L)  # raised ledge (row 50)


def gz(y):
    return Z["glacisTop"] + (y - 57.3) * (Z["toe"] - Z["glacisTop"]) / (66.0 - 57.3)


def build_glacis(P):
    for x0, x1, toe, nm in ((0, 7.0, 66.0, "l"), (7.0, 16.0, 65.0, "c"), (16.0, 24, 66.0, "r")):
        zt = Z["glacisTop"] - (0.15 if nm == "c" else 0)
        ext(P, [(57.3, 0), (toe, 0), (toe, Z["toe"]), (toe - 0.4, Z["toe"] + 0.35), (57.3, zt)], "x", x0, x1, DARK2,
            0.0, 0.0)
    f = lambda x, y: gz(y)  # noqa: E731
    for a, b, h in (((0.2, 58.4), (9.0, 58.4), 0.35), ((14.0, 58.4), (23.8, 58.4), 0.35),
                    ((0.2, 65.2), (6.8, 65.2), 0.3), ((16.2, 65.2), (23.8, 65.2), 0.3)):
        strip(P, f, a[0], a[1], b[0], b[1], 0.9, h, DARK3)
    # Louvre slats (the dark gaps cols 1, 3, 20, 22): vertical vanes standing on the slope.
    for x in (1.1, 3.1, 20.1, 22.1):
        strip(P, f, x + 0.45, 59.4, x + 0.45, 64.4, 0.6, 0.2, FLOOR)
    for x in (2.1, 4.1, 21.1, 23.1):
        strip(P, f, x + 0.45, 59.4, x + 0.45, 64.4, 0.55, 0.3, DARK3)
    lathe(P, "y", 5.6, gz(58.4) + 0.3, [(58.0, 0.6, WALL_R), (58.9, 0.6, WALL_R), (58.9, 0.35, WALL_R),
                                        (59.1, 0.35, WALL_R)], n=10)  # inspection boss
    strip(P, f, 9.0, 61.6, 6.6, 64.6, 0.6, 0.35, DARK3)  # gun-port frame
    strip(P, f, 14.0, 61.6, 15.6, 64.6, 0.6, 0.35, DARK3)


def build_column(P):
    ext(P, rect(0, 0.3, 24, 57.5), "z", 0.0, Z["pit"], FLOOR, 0.0, 0.0)  # plinth: its top is the pit floor
    build_hood(P)
    build_walls(P)
    build_tanks(P)
    build_housing(P)
    build_pit(P)
    build_cannon(P)
    build_deck(P)
    build_glacis(P)


def build_flash(P):
    """Frame 121's muzzle flash: an outer bloom (palette 117) with a hot core (125) and a tail leaning to
    column 11 as the sprite's flash does."""
    st = [(57.2, 0.0), (57.6, 1.2), (58.6, 2.35), (60.5, 2.55), (62.5, 2.35), (64.0, 2.0), (65.0, 1.4), (65.8, 0.0)]
    lathe(P, "y", CX, CZ + 0.4, [(y, r, 0, r * 0.75) for y, r in st], n=14)
    tail = [(63.0, 0.0), (63.6, 1.7), (64.8, 2.1), (65.6, 1.8), (66.5, 1.2), (67.4, 0.7), (68.0, 0.0)]
    lathe(P, "y", 11.05, CZ + 0.3, [(y, r, 0, r * 0.65) for y, r in tail], n=12)
    s2 = [(57.8, 0.0), (58.3, 0.9), (59.5, 1.2), (61.5, 1.15), (63.3, 0.8), (64.4, 0.0)]
    lathe(P, "y", CX - 0.2, CZ + 1.3, [(y, r, 1, r * 0.7) for y, r in s2], n=12)


# --- assembly ------------------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(WT, "newshf-81")
    for name in PIECES:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


def materials(sprite):
    return [common.palette_material(sprite, pal, f"nshf81A_{nm}", metallic=met, roughness=rough,
                                    emission_strength=em)
            for nm, pal, met, rough, em in SLOTS]


def finish(P, mats, coll, smooth=True):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 42 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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


def bake_maps(obj, out_dir, size=1024, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (1.0, 1.0, 1.0)
    T.TEXTURED = TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured


def split_open(obj, layout, coll):
    """Cut an outline shell into the pieces without filling the cuts (no ink along the seams)."""
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
        sh.data.shade_smooth()
        out[name] = sh
    return out


def close_seams(obj):
    """Check each piece is closed after split_assembly (a part face lying on a cut plane leaves its
    cap unfilled: the deck gap floors once ended on row 56, the 119 seam); fill any loop left open."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        new = bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]
        if new:
            bmesh.ops.triangulate(bm, faces=new)
        bm.to_mesh(obj.data)
    left = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    print(f"{NAME}: {obj.name}: open boundary edges {len(edges)} -> {left}")


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    P = T.Part(NAME, smooth_angle=32.0)
    build_column(P)
    obj = finish(P, mats, coll)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    print(f"{NAME}_A: column {tris(obj)} triangles")

    # The flash (f2 only), emissive palette 117 / 125 from frame 121.
    d119 = common.load_sprite(WT, "newshf-119")
    fmats = [common.palette_material(d119, 117, "nshf81A_flash", metallic=0.0, roughness=0.5, emission_strength=3.0),
             common.palette_material(d119, 125, "nshf81A_flash", metallic=0.0, roughness=0.5, emission_strength=5.0)]
    F = T.Part("newshf-119-f2_flash", smooth_angle=80.0)
    build_flash(F)
    flash = finish(F, fmats, coll)
    common.frame_part(flash, [121])

    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nshf81A_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, faces=OUTLINE_FACES)
    shell.hide_render = True
    pieces = common.split_assembly(obj, LAYOUT, coll)
    shells = split_open(shell, LAYOUT, coll)
    flash.location = (0, 0, 0)
    # newshf-119 piece centre is at Y = -28/12: the flash is built in column coordinates, move it to piece space.
    bm = bmesh.new()
    bm.from_mesh(flash.data)
    bmesh.ops.translate(bm, vec=(0, 28 / 12, 0), verts=bm.verts)
    bm.to_mesh(flash.data)
    bm.free()

    total = 0
    groups = {}
    for name, cx, cy in LAYOUT:
        p, sh = pieces[name], shells[name]
        p.name = name
        close_seams(p)
        # The cut edges (filled caps at the piece borders) are new: mark them sharp like the rest, or the
        # smoothing bends the faces they split toward the caps (a shaded band along every seam).
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(32.0))
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        common._apply_modifiers(p)
        t, ts = tris(p), tris(sh)
        total += t + ts
        print(f"{NAME}: piece {name}: {t} triangles, outline {ts}")
        p.location = sh.location = (0, 0, 0)
        groups[name] = [p, sh]
    print(f"{NAME}: per column {total} triangles (shells included), flash {tris(flash)}")
    if "--out" in argv:  # review copy: both columns at their assembly places
        export = []
        for name, cx, cy in LAYOUT:
            for dx, suffix in ((0.0, ""), (2.0, "_R")):
                for o in groups[name] + ([flash] if name == "newshf-119" else []):
                    c = o if not suffix else o.copy()
                    if suffix:
                        c.name = o.name + suffix
                        coll.objects.link(c)
                    c.location = (cx / 12 + dx, -cy / 12, 0)
                    export.append(c)
        common.export_glb(export, out, image_format=fmt)
        print(f"{NAME}: exported review {out}")
        return
    for name in ("newshf-43", "newshf-81"):
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, groups[name], f"enemies/{name}", data["sprites"], image_format=fmt)
    s119 = common.load_sprite(WT, "newshf-119")["sprites"][0]
    common.export_sprite_model(WT, groups["newshf-119"], "enemies/newshf-119", [{**s119, "frames": [119]}],
                               image_format=fmt)
    common.export_sprite_model(WT, groups["newshf-119"] + [flash], "enemies/newshf-119-f2",
                               [{**s119, "frames": [121]}], image_format=fmt)


if __name__ == "__main__":
    main()
