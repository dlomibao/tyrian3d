"""The DREAD-NOT's two armoured fists (newsh9.shp 81/83 over 119/121 right, 77/79 over 115/117 left,
48 x 56 px each; only assembly-newsh9-119 and -115 use this). Built as the right fist; the left is its mirror.

WHAT IT IS: one of the dreadnought's two armoured gauntlets (the left one, assembly-newsh9-115, is its
mirror image across the 96 px structure), riding on the ground2 layer beside the fortress dome. Seen
from above: the wrist cuff / back-of-hand armour (the "hood") over a clenched mechanical hand whose
four knuckles are red armour domes, a light-grey finger plate down the middle, a dark machinery
flank on the outside with rods and a white lamp.

Reading the sprite (right-fist grid, 48 x 56, ink border 100%: model edge at the inner edge, D74;
light from the upper left, so the dark south/east faces and the bright NW shoulders are lighting):
- Hood, rows 6-26: a big rounded armour shell. An upper lobe (rows 6-19, crown at column ~9) steps
  down at the dark curve along row 19 (rising to column 22 at row 15) onto a lower shelf (rows 19-25)
  whose south lip rolls down over the big knuckle; its outer flank slopes to the diagonal right edge.
  A hatch panel (columns 5-11, rows 13-18, bright = sheen on the NW shoulder) with a seam running on
  down column 11 to row 22; a rolled bead down the inner edge (column 6); a rib with a groove beside
  it down the flank (columns 24-25, rows 16-24); a bolt on the lip (column 22, row 25).
- Knuckle domes (palette medians): D1 big (columns 6-18, rows 28-37) 69, D2 (23-30, 26-32) 67,
  D3 outer (35-43, 25-34) 66, D4 lower (16-24, 39-48) 67. D1, D3 and D4 make the silhouette there.
- Finger plate (light grey, median 6) from between D1/D2 down past D4 to the bottom (columns 24-31).
- Outer flank (median 5): a rod down column 31, a diagonal rod (34-37, rows 33-41), slots, and the
  white lamp (palette 14) at column 36, row 47 in a bezel.
Colours (median, ink <= 2 and highlights >= 12 left out): lobe 6, shelf 5, flank 5, body 5, plate 6.

Coordinates: right-fist sprite px (pixel edges) x right, y down; Blender X = (x - 24) / 12,
Y = (28 - y) / 12, Z up from the ground2 plane. Pieces cut with common.split_assembly; the outline
shell is made from the sealed whole (islands="outer", D189) and cut open per piece (no seam ink).

Run through assembly-newsh9-119.py / assembly-newsh9-115.py, each exporting only its own four pieces
(plus each piece's outline shell cut open), via export(name).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]  # the repo, found from this file's location
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh9-119"   # the right fist: the design (and its sprite mask) is built for this one
PX = 1 / 12
SIDES = {  # model name -> (pieces, screen px of the fist's centre = Blender origin, mirrored?)
    "assembly-newsh9-119": (["newsh9-81", "newsh9-83", "newsh9-119", "newsh9-121"], (268, 43), False),
    "assembly-newsh9-115": (["newsh9-77", "newsh9-79", "newsh9-115", "newsh9-117"], (220, 43), True),
}
ALL_PIECES = [p for v in SIDES.values() for p in v[0]]
PAD = 0.08          # px the model edge sits outside the inner mask

# palette slots
(M_LOBE, M_SHELF, M_BODY, M_PLATE, M_ROD, M_SEAM, M_D1, M_D2, M_D3, M_D4, M_LAMP, M_BEZEL,
 M_BOLT) = range(13)
PAL = {M_LOBE: 6, M_SHELF: 5, M_BODY: 5, M_PLATE: 6, M_ROD: 7, M_SEAM: 3, M_D1: 69, M_D2: 67,
       M_D3: 66, M_D4: 67, M_LAMP: 14, M_BEZEL: 4, M_BOLT: 8}

# knuckle domes: (cx, cy, rx, ry, z_equator, rz, mat) in px / units
DOMES = [
    (12.35, 33.0, 6.55, 5.05, 0.30, 0.44, M_D1),
    (26.9, 29.4, 4.05, 3.65, 0.50, 0.24, M_D2),
    (39.3, 29.9, 3.85, 5.0, 0.30, 0.38, M_D3),
    (20.6, 43.9, 4.6, 5.05, 0.28, 0.38, M_D4),
]

HOOD_Z = 0.70   # shelf crown
LOBE_Z = 1.04   # upper lobe crown
BODY_Z = 0.56   # hand body crown


def X(u):
    return (u - 24) * PX


def Y(v):
    return (28 - v) * PX


# --- the sprite ----------------------------------------------------------------------------------

def sprite_masks():
    idx, colors = SM.load(NAME)
    return idx, SM.masks(idx, colors)


def row_spans(mask, rows, pad=PAD, cols=None):
    """{row: (u_left, u_right)} of a bool mask's filled columns per row (pixel edges, padded)."""
    out = {}
    for r in rows:
        cs = [c for c, b in enumerate(mask[r]) if b and (cols is None or cols(r, c))]
        if cs:
            out[r] = (min(cs) - pad, max(cs) + 1 + pad)
    return out


# --- geometry ------------------------------------------------------------------------------------

def _set(faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def hull(bm, sections, mat, n=18, ql=0.7, qr=0.7, smooth=True, mats=None):
    """Loft rounded-top profiles down the screen. Each section is (v, ul, ur, ua, zb, zt): a half
    superellipse from ul to ur with its crown at ua, closed along zb. q < 1 is boxier."""
    rings = []
    for v, ul, ur, ua, zb, zt in sections:
        ua = min(max(ua, ul + 0.05), ur - 0.05)
        ring = []
        for k in range(n + 1):
            a = math.pi * k / n
            c, s = math.cos(a), max(math.sin(a), 0.0)
            if c >= 0:
                u = ua + (ur - ua) * c ** qr
                z = zb + (zt - zb) * s ** qr
            else:
                u = ua - (ua - ul) * (-c) ** ql
                z = zb + (zt - zb) * s ** ql
            ring.append(bm.verts.new((X(u), Y(v), z)))
        rings.append(ring)
    m = n + 1
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        faces = [bm.faces.new((r0[k], r0[(k + 1) % m], r1[(k + 1) % m], r1[k])) for k in range(m)]
        _set(faces, mats[i] if mats else mat, smooth)
    _set([bm.faces.new(list(reversed(rings[0])))], mat, False)
    _set([bm.faces.new(rings[-1])], mat, False)


def nosed(rows, v0, v1, zt, zb, ua, nose0=1.4, nose1=1.4, shrink=0.8, n_nose=4):
    """Sections for a loft over `rows` [(v, ul, ur)] whose ends roll over (quarter circle) within
    the mask: the ends at v0 and v1 are low and a little narrower. zt, ua: functions of v."""
    rows = sorted(rows)
    secs = []

    def span_at(v):
        best = min(rows, key=lambda t: abs(t[0] - v))
        return best[1], best[2]

    for k in range(n_nose):
        d = nose0 * k / n_nose
        h = math.sqrt(max(0.0, 1 - (1 - d / nose0) ** 2))
        ul, ur = span_at(v0 + d)
        s = (1 - h) * shrink
        v = v0 + d
        secs.append((v, ul + s, ur - s, ua(v), zb, zb + (zt(v) - zb) * max(h, 0.18)))
    for v, ul, ur in rows:
        if v0 + nose0 <= v <= v1 - nose1:
            secs.append((v, ul, ur, ua(v), zb, zt(v)))
    for k in reversed(range(n_nose)):
        d = nose1 * k / n_nose
        h = math.sqrt(max(0.0, 1 - (1 - d / nose1) ** 2))
        ul, ur = span_at(v1 - d)
        s = (1 - h) * shrink
        v = v1 - d
        secs.append((v, ul + s, ur - s, ua(v), zb, zb + (zt(v) - zb) * max(h, 0.18)))
    return secs


def ellipsoid(bm, u, v, z, rx_px, ry_px, rz, mat, segments=28, rings=14, z_cut=0.0, flat_below=None):
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for vert in res["verts"]:
        sz = vert.co.z
        zz = z + sz * (rz if sz >= 0 else (flat_below if flat_below is not None else rz))
        co = Vector((X(u) + vert.co.x * rx_px * PX, Y(v) + vert.co.y * ry_px * PX, zz))
        if co.z < z_cut:
            co.z = z_cut
        vert.co = co
    faces = {f for vert in res["verts"] for f in vert.link_faces}
    _set(faces, mat, True)
    return res["verts"]


def torus(bm, u, v, z, rx_px, ry_px, tube, mat, seg=28, tseg=8, tube_z=None):
    rings = []
    tz = tube if tube_z is None else tube_z
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for j in range(tseg):
            b = 2 * math.pi * j / tseg
            rr = 1 + (tube / (rx_px * PX)) * math.cos(b)
            ring.append(bm.verts.new((X(u) + ca * rx_px * PX * rr, Y(v) - sa * ry_px * PX * rr,
                                      z + tz * math.sin(b))))
        rings.append(ring)
    faces = []
    for i in range(seg):
        r0, r1 = rings[i], rings[(i + 1) % seg]
        for j in range(tseg):
            k = (j + 1) % tseg
            faces.append(bm.faces.new((r0[j], r1[j], r1[k], r0[k])))
    _set(faces, mat, True)


class Surface:
    """Height of the built solids straight down through a point (for detail that sits on them)."""

    def __init__(self, bm):
        self.tree = BVHTree.FromBMesh(bm)

    def z(self, u, v, default=0.0):
        hit = self.tree.ray_cast(Vector((X(u), Y(v), 5.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else default


def sweep(bm, S, path, r_px, mat, sides=10, lift=0.55, squash=1.0, steps=3):
    """A round rod lying on the surface along a polyline of (u, v); ends capped with half domes."""
    pts = []
    for (u0, v0), (u1, v1) in zip(path, path[1:]):
        for k in range(steps):
            t = k / steps
            pts.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
    pts.append(path[-1])
    r = r_px * PX
    P = [Vector((X(u), Y(v), S.z(u, v) + r * lift * squash)) for u, v in pts]
    # end caps: extend with shrinking rings
    up = Vector((0, 0, 1))
    rings = []
    full = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
        t.z = 0
        t.normalize()
        full.append((p, t))
    ext = []
    p0, t0 = full[0]
    for f in (0.0, 0.55, 0.85):
        ext.append((p0 - t0 * r * (1 - f) * 0.9, t0, math.sqrt(max(0.05, 1 - (1 - f) ** 2))))
    body = [(p, t, 1.0) for p, t in full]
    p1, t1 = full[-1]
    tail = [(p1 + t1 * r * (1 - f) * 0.9, t1, math.sqrt(max(0.05, 1 - (1 - f) ** 2))) for f in (0.85, 0.55, 0.0)]
    for p, t, s in ext + body + tail:
        side = t.cross(up)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * (r * s * math.cos(a)) + up * (r * s * squash * math.sin(a))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    _set(faces, mat, True)


def strip(bm, S, path, w_px, mat, h=0.006, depth=0.03, steps=4):
    """A panel-line inlay: a thin closed ribbon hugging the surface along a polyline of (u, v)."""
    pts = []
    for (u0, v0), (u1, v1) in zip(path, path[1:]):
        for k in range(steps):
            t = k / steps
            pts.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
    pts.append(path[-1])
    w = w_px / 2
    tops, bots = [], []
    for i, (u, v) in enumerate(pts):
        a = pts[min(i + 1, len(pts) - 1)]
        b = pts[max(i - 1, 0)]
        du, dv = a[0] - b[0], a[1] - b[1]
        ln = math.hypot(du, dv) or 1
        nu, nv = -dv / ln * w, du / ln * w
        row_t, row_b = [], []
        for su, sv in ((u - nu, v - nv), (u + nu, v + nv)):
            z = S.z(su, sv)
            row_t.append(bm.verts.new((X(su), Y(sv), z + h)))
            row_b.append(bm.verts.new((X(su), Y(sv), z - depth)))
        tops.append(row_t)
        bots.append(row_b)
    faces = []
    for i in range(len(pts) - 1):
        t0, t1, b0, b1 = tops[i], tops[i + 1], bots[i], bots[i + 1]
        faces.append(bm.faces.new((t0[0], t1[0], t1[1], t0[1])))
        faces.append(bm.faces.new((b0[1], b1[1], b1[0], b0[0])))
        faces.append(bm.faces.new((b0[0], b1[0], t1[0], t0[0])))
        faces.append(bm.faces.new((t0[1], t1[1], b1[1], b0[1])))
    faces.append(bm.faces.new((tops[0][1], tops[0][0], bots[0][0], bots[0][1])))
    faces.append(bm.faces.new((tops[-1][0], tops[-1][1], bots[-1][1], bots[-1][0])))
    _set(faces, mat, False)


def raised(bm, S, rows, mat, h=0.045, sink=0.06, n=10, q=0.35, nose=0.6):
    """A plate with rounded-chamfer edges lying on the surface: rows [(v, ul, ur)] at pixel centres
    (the surface height under each section's middle sets its base)."""
    v0, v1 = rows[0][0] - 0.5, rows[-1][0] + 0.5

    def zt(v):
        best = min(rows, key=lambda t: abs(t[0] - v))
        return S.z((best[1] + best[2]) / 2, v) + h

    secs = nosed(rows, v0, v1, zt, 0.0, lambda v: 0.0, nose0=nose, nose1=nose, shrink=0.45, n_nose=3)
    out = []
    for v, ul, ur, _, zb, z in secs:
        base = S.z((ul + ur) / 2, v)
        out.append((v, ul, ur, (ul + ur) / 2, base - sink, max(z, base + 0.01)))
    hull(bm, out, mat, n=n, ql=q, qr=q)


def poly_rows(poly, v0, v1, step=1.0):
    """[(v, ul, ur)] of a polygon [(u, v)] sampled at v0 + k*step (assumes one span per row)."""
    out = []
    v = v0
    while v <= v1 + 1e-6:
        xs = []
        for (a, b), (c, d) in zip(poly, poly[1:] + poly[:1]):
            if (b <= v < d) or (d <= v < b):
                xs.append(a + (v - b) * (c - a) / (d - b))
        if len(xs) >= 2:
            out.append((v, min(xs), max(xs)))
        v += step
    return out


# --- the fist ------------------------------------------------------------------------------------

def build():
    idx, m = sprite_masks()
    inner = m["inner"]
    red = [[v >= 64 for v in row] for row in idx]
    bm = bmesh.new()

    # ---- hood shelf (rows 6-26): crown near column 10, flank sloping to the diagonal edge ----
    hs = row_spans(inner, range(6, 27), cols=lambda r, c: not red[r][c] and (r < 24 or c < 35))
    rows = [(r + 0.5, ul, ur) for r, (ul, ur) in hs.items()]
    rows = [(v, ul, min(ur, 34.4) if v > 23 else ur) for v, ul, ur in rows]

    def shelf_z(v):
        return HOOD_Z - max(0.0, v - 22.5) * 0.035

    def shelf_ua(v):
        return 10.0 + max(0.0, v - 18) * 0.25

    secs = nosed(rows, 5.95, 27.0, shelf_z, 0.0, shelf_ua, nose0=1.3, nose1=2.4, shrink=0.6)
    hull(bm, secs, M_SHELF, n=22, ql=0.55, qr=1.15)

    # ---- upper lobe (rows 6-19.5): the high rounded crown of the cuff ----
    lobe_r = {6: 16.6, 7: 19.0, 8: 20.6, 9: 21.8, 10: 22.6, 11: 23.2, 12: 23.4, 13: 23.2, 14: 22.8,
              15: 22.2, 16: 21.6, 17: 21.0, 18: 20.6, 19: 20.3}
    lrows = []
    for r, ur in lobe_r.items():
        ul = hs[r][0]
        lrows.append((r + 0.5, ul, min(ur, hs[r][1] - 0.4)))

    def lobe_z(v):
        return LOBE_Z

    secs = nosed(lrows, 5.95, 19.6, lobe_z, 0.30, lambda v: 9.0, nose0=1.6, nose1=1.5, shrink=0.5)
    hull(bm, secs, M_LOBE, n=22, ql=0.5, qr=0.95)

    # ---- hand body (rows 24-53) under the knuckles ----
    bs = row_spans(inner, range(23, 54))
    brows = [(r + 0.5, ul, ur) for r, (ul, ur) in bs.items() if r >= 24]
    # under the hood the body is a little narrower (the hood covers it)
    brows = [(v, ul + (1.5 if v < 27 else 0), ur) for v, ul, ur in brows]

    def body_z(v):
        return BODY_Z - max(0.0, v - 46) * 0.035

    secs = nosed(brows, 24.0, 53.05, body_z, 0.0, lambda v: 28.0, nose0=1.0, nose1=2.6, shrink=0.7)
    hull(bm, secs, M_BODY, n=24, ql=0.75, qr=0.75)

    # ---- knuckle domes, each seated in a collar ring on the body (where the body is under it) ----
    S0 = Surface(bm)

    def inside(u, v, margin=0.9):
        for du in (-margin, 0, margin):
            for dv in (-margin, 0, margin):
                c, r = int(math.floor(u + du)), int(math.floor(v + dv))
                if not (0 <= r < len(inner) and 0 <= c < len(inner[0]) and inner[r][c]):
                    return False
        return True

    for cx, cy, rx, ry, ze, rz, mat in DOMES:
        run = []
        runs = []
        N = 48
        for k in range(N + 1):
            a = 2 * math.pi * k / N
            u, v = cx + (rx + 0.35) * math.cos(a), cy + (ry + 0.35) * math.sin(a)
            if inside(u, v) and S0.z(u, v, -1) > ze - 0.05:
                run.append((u, v))
            else:
                if len(run) > 3:
                    runs.append(run)
                run = []
        if len(run) > 3:
            runs.append(run)
        if len(runs) > 1 and runs[0][0] == (cx + rx + 0.35, cy) and runs[-1][-1] == runs[0][0]:
            runs[0] = runs.pop() + runs[0][1:]
        for rr in runs:
            sweep(bm, S0, rr, 0.7, M_SEAM, lift=0.15, sides=8, steps=1)
    for cx, cy, rx, ry, ze, rz, mat in DOMES:
        ellipsoid(bm, cx, cy, ze, rx + PAD, ry + PAD, rz, mat, flat_below=ze)

    S = Surface(bm)

    # ---- hood detail ----
    # hatch panel on the NW shoulder (columns 5-11, rows 13.5-18.5)
    raised(bm, S, [(v + 0.5, 5.6, 10.9) for v in range(14, 18)], M_LOBE, h=0.035, sink=0.08, q=0.3, nose=0.5)
    strip(bm, S, [(7.4, 13.45), (11.3, 13.45)], 0.7, M_SEAM)          # hatch top seam
    strip(bm, S, [(11.35, 13.3), (11.35, 19.0)], 0.6, M_SEAM)          # hatch side seam ...
    strip(bm, S, [(11.35, 19.6), (11.35, 22.6)], 0.6, M_SEAM)          # ... down the shelf
    # rolled bead down the inner edge (column 6)
    sweep(bm, S, [(6.5, 8.0), (6.5, 13.0), (6.4, 18.5)], 0.55, M_ROD, lift=0.2, sides=8)
    # flank rib and its groove (columns 24-25, rows 16-24)
    sweep(bm, S, [(24.4, 15.6), (24.6, 19.5), (24.4, 24.3)], 0.6, M_ROD, lift=0.25, sides=8)
    strip(bm, S, [(25.6, 16.6), (25.6, 24.2)], 0.55, M_SEAM)
    # step seam along the foot of the lobe
    # bolt on the lip
    ellipsoid(bm, 22.4, 25.2, S.z(22.4, 25.2) - 0.01, 0.9, 0.9, 0.05, M_BOLT, segments=10, rings=5)

    # ---- hand detail ----
    # light finger plate from between D1/D2 down past D4 to the foot
    plate_poly = [(19.0, 26.8), (22.6, 26.6), (24.4, 33.2), (29.6, 33.8), (31.2, 37.0), (31.4, 47.5),
                  (30.2, 50.2), (25.2, 50.6), (24.6, 47.0), (25.4, 39.4), (19.6, 39.0), (17.4, 37.9),
                  (18.6, 34.6), (19.4, 31.5)]
    raised(bm, S, poly_rows(plate_poly, 27.3, 50.2), M_PLATE, h=0.11, sink=0.1, q=0.28, nose=0.8)
    # outer armour plate on the flank (columns 38-43, rows 34-45)
    outer_poly = [(37.8, 34.6), (42.4, 34.2), (43.2, 36.5), (43.2, 44.2), (41.6, 45.4), (38.6, 44.0)]
    raised(bm, S, poly_rows(outer_poly, 34.9, 45.0), M_BODY, h=0.06, sink=0.1, q=0.3, nose=0.6)
    # knuckle seam between the finger plate's upper band and its lower blade
    strip(bm, S, [(25.6, 39.2), (31.0, 38.6)], 0.5, M_SEAM)
    strip(bm, S, [(25.2, 45.0), (31.2, 45.0)], 0.45, M_SEAM)
    # rod down column 31 beside the outer knuckle, its groove beside it
    sweep(bm, S, [(31.6, 26.6), (31.8, 32.0), (32.6, 37.4)], 0.7, M_ROD, lift=0.3)
    strip(bm, S, [(33.0, 27.4), (33.6, 37.6)], 0.5, M_SEAM)
    # diagonal rod on the outer flank
    sweep(bm, S, [(34.6, 33.0), (35.6, 36.5), (36.6, 40.6)], 0.6, M_ROD, lift=0.3)
    # slots: dark recesses in the flank
    strip(bm, S, [(33.4, 39.6), (33.8, 43.6)], 0.9, M_SEAM)
    strip(bm, S, [(37.2, 42.5), (40.0, 41.6)], 0.8, M_SEAM)
    strip(bm, S, [(39.6, 35.6), (41.6, 39.2)], 0.7, M_SEAM)
    # outer rim rail (column 43, rows 37-44)
    sweep(bm, S, [(42.6, 36.8), (43.0, 40.0), (42.8, 44.2)], 0.6, M_ROD, lift=0.0)
    # lamp: bezel ring and white lens
    zl = S.z(36.3, 47.0)
    torus(bm, 36.3, 47.0, zl + 0.02, 2.0, 2.0, 0.045, M_BEZEL, tube_z=0.05)
    ellipsoid(bm, 36.3, 47.0, zl - 0.03, 1.55, 1.55, 0.12, M_LAMP, segments=16, rings=8)

    bmesh.ops.scale(bm, vec=(1, 1, 1), verts=bm.verts)
    return bm


# --- materials and objects -----------------------------------------------------------------------

def materials(sprite):
    def pal(slot, metallic, rough, coat=0.0, emission=0.0):
        mt = common.palette_material(sprite, PAL[slot], f"nsh9_b090_{slot}", metallic=metallic, roughness=rough,
                                     emission_strength=emission)
        b = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if coat:
            b.inputs["Coat Weight"].default_value = coat
            b.inputs["Coat Roughness"].default_value = 0.25
        return mt
    return [
        pal(M_LOBE, 0.55, 0.38),        # satin armour
        pal(M_SHELF, 0.55, 0.42),
        pal(M_BODY, 0.5, 0.48),
        pal(M_PLATE, 0.55, 0.36),
        pal(M_ROD, 0.7, 0.3),
        pal(M_SEAM, 0.3, 0.7),
        pal(M_D1, 0.3, 0.42),  # red enamelled knuckle domes, satin
        pal(M_D2, 0.3, 0.42),
        pal(M_D3, 0.3, 0.42),
        pal(M_D4, 0.3, 0.42),
        pal(M_LAMP, 1.0, 1.0, emission=1.6),  # glow: metallic 1 / rough (D126/D173)
        pal(M_BEZEL, 0.6, 0.35),
        pal(M_BOLT, 0.7, 0.3),
    ]


def make_object(bm, name, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(40))
    return obj


def split_open(obj, layout, coll):
    """split_assembly's cut without capping (for the outline shell: no ink line at the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
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


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def merged_sprite(pieces):
    data = common.load_sprite(WT, pieces[0])
    for n in pieces:
        data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


def build_fist(name):
    """Build one fist (the left is the right's mirror image across X) and return
    (whole, shell, pieces, shells, layout, mats, sprite)."""
    pieces_names, (cx0, cy0), mirrored = SIDES[name]
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = merged_sprite(pieces_names)
    coll = common.reset_collection(name)
    mats = materials(sprite)
    bm = build()
    if mirrored:
        for v in bm.verts:
            v.co.x = -v.co.x + PX  # the left sprite is the right one mirrored about column 23.5 (1 px off centre)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    whole = make_object(bm, name, mats, coll)
    bm.free()
    shell = common.outline_shell(whole, coll, voxel=0.02, faces=5000, smooth=6, inside=0.006, islands="outer")
    shell.name = f"{name}_outline"
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in sprite["assemblyLayout"] if e["model"] in pieces_names]
    pieces = common.split_assembly(whole, layout, coll)
    shells = split_open(shell, layout, coll)
    for n in pieces_names:
        pieces[n].data.set_sharp_from_angle(angle=math.radians(40))
    return whole, shell, pieces, shells, layout, mats, sprite


def export(name):
    """Build this fist and export its four pieces (each with its own open outline shell)."""
    whole, shell, pieces, shells, layout, mats, sprite = build_fist(name)
    stats = {}
    for n in SIDES[name][0]:
        data = common.load_sprite(WT, n)
        common.export_sprite_model(WT, [pieces[n], shells[n]], f"enemies/{n}", data["sprites"])
        stats[n] = tris(pieces[n]) + tris(shells[n])
    print("STATS", json.dumps(stats))
