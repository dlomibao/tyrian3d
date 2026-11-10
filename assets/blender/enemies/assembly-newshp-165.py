"""Grey corrugated cargo container "218" docked in a steel cradle, design A
(newshp.shp 165|167 / 203|205 / 241|243: six 2x2 pieces, two across and three down, 48 x 84 px).
Seen in episodes 2 and 3 (levels 2.8 and 3.15, from the sprite data).

Led by the blueprint (scratch blueprint/blueprint.json, model_body.js): one point model in sprite
px, cross-sections first, fitted to the sprite's INNER mask (D74). Built here hard-surface:

- the floor (rows 28-84): a dark base plate (pal 2: it is what shows in the joints, the drain
  trench and the grating pit) with dressed kerb blocks down both sides (6 west, 3 east), separate
  paving slabs with real joints, a drain grating south of the cradle (angle-iron frame, seven flat
  bars over a pit, a spine);
- the steel cradle (rows 28-70): a dark deck (pal 3) with a rounded west edge, a sloped front
  apron with three gussets and a round bump rail, two louvred vent grilles and a tread plate in
  its deck, chocks along the container's feet; a service pipe down the west side on three clamped
  feet, its end bending down into the floor;
- the container (rows 15-55, cols 7-41): a corrugated roof (crests on the even columns), sloped
  corrugated shoulders (the sprite's lighter west 9 / shaded east 6), roof edge rails, a north
  header with its corners cut on the diagonal as the sprite's rows 15-17, a south door header
  whose face leans back (the 7 band at rows 53-54) with door leaves, four locking rods and
  handles, ISO corner castings, vertical ribs on the side walls and the north end, and the
  stencilled 218 painted on the corrugated roof (smooth glyph outlines traced from the sprite's
  12/13 pixels, as faces just over the roof, not geometry).

Every part takes the sprite's palette index for its region (trimmed median; blueprint.json
region_medians). Undersides are plain closed shapes.

Texture: AO/roughness bake only (usp_talon.bake_maps, "bake": "model", D50/D65), no concept
projection. Built whole, baked, cut into the six pieces with common.split_assembly.

Run: blender -b --factory-startup -P assets/blender/enemies/assembly-newshp-165.py [-- --out all.glb] [--no-bake]
Writes public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json for each piece;
--out also writes all pieces in place (each with its outline shell) to one glb to look at.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

HERE = Path(__file__).resolve().parent
NAME = "assembly-newshp-165"
TAG = "nshp165A"
PIECES = [["newshp-165", "newshp-167"], ["newshp-203", "newshp-205"], ["newshp-241", "newshp-243"]]
W, H = 48, 84

# Heights (sprite px): base plate, floor top, cradle deck, shoulder edge, roof, end headers.
ZB, ZF, ZP, ZS, ZT = 0.15, 0.36, 2.2, 6.0, 8.4
ZTF = ZT + 0.45


def X(c):
    return c - 24.0


def Y(r):
    return 42.0 - r


# ----------------------------------------------------------------------------------------------
# Sprite, materials
# ----------------------------------------------------------------------------------------------

def load_composite():
    colors, G = {}, [[-1] * W for _ in range(H)]
    for ri, row in enumerate(PIECES):
        for ci, n in enumerate(row):
            d = common.load_sprite(WT, n)
            colors.update(d["colors"])
            for r, line in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(line):
                    if v >= 0:
                        G[ri * 28 + r][ci * 24 + c] = v
    return colors, G


SLOTS, MATS = {}, []
FINISH = {"metal": (0.5, 0.42), "steel": (0.45, 0.55), "stone": (0.05, 0.85), "paint": (0.15, 0.6),
          "dark": (0.2, 0.7)}


def mat(pal, finish="metal"):
    key = (pal, finish)
    if key not in SLOTS:
        m, r = FINISH[finish]
        SLOTS[key] = len(MATS)
        MATS.append(common.palette_material(SPRITE, pal, f"{TAG}_{finish}", metallic=m, roughness=r))
    return SLOTS[key]


# ----------------------------------------------------------------------------------------------
# Geometry (sprite px: x = c - 24 right, y = 42 - r north, z up; scaled by 1/12 at the end)
# ----------------------------------------------------------------------------------------------
BM = bmesh.new()


def V(p):
    return BM.verts.new(p)


def face(vs, m):
    try:
        f = BM.faces.new(vs)
    except ValueError:
        return None
    f.material_index = m
    return f


def loft(rings, m, cap0=True, cap1=True, closed=True):
    """Quads between rings of points (same count); n-gon caps."""
    vr = [[V(p) for p in R] for R in rings]
    n = len(rings[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            face([a[i], a[j], b[j], b[i]], m)
    if cap0:
        face(vr[0][::-1], m)
    if cap1:
        face(vr[-1], m)
    return vr


def norm2(x, y):
    ln = math.hypot(x, y) or 1.0
    return x / ln, y / ln


def offset_poly(P, dist):
    """Offset a convex CCW polygon inward; edge i moves by dist(outward normal of edge i)."""
    n, L = len(P), []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        tx, ty = norm2(b[0] - a[0], b[1] - a[1])
        nx, ny = ty, -tx
        d = dist(nx, ny)
        L.append(((a[0] - nx * d, a[1] - ny * d), (tx, ty)))
    out = []
    for i in range(n):
        (ap, at), (bp, bt) = L[i - 1], L[i]
        den = at[0] * bt[1] - at[1] * bt[0]
        if abs(den) < 1e-6:
            out.append(bp)
            continue
        s = ((bp[0] - ap[0]) * bt[1] - (bp[1] - ap[1]) * bt[0]) / den
        out.append((ap[0] + at[0] * s, ap[1] + at[1] * s))
    return out


def rrect(x0, y0, x1, y1, r=0.25, seg=2):
    r = max(0.01, min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    P = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            P.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return P


SIDES = {"w": (-1, 0), "e": (1, 0), "n": (0, 1), "s": (0, -1)}


def slab(m, poly, z0, z1, ch=0.3, fil=None, slope=None):
    """Extrude a convex CCW plan polygon from z0 to z1 with a chamfer (or per-side round fillets)
    round the top edge; slope = {side: px that face leans back over its height}."""
    fil, slope = fil or {}, slope or {}
    h = z1 - z0
    rmax = max([ch] + list(fil.values()) + [0.01])
    rmax = min(rmax, h * 0.95)
    ns = 4 if fil else 1
    zs = [z0] + [z1 - rmax * (1 - j / ns) for j in range(ns + 1)]
    rings = []
    for z in zs:
        def dist(nx, ny, z=z):
            d = 0.0
            for k, (sx, sy) in SIDES.items():
                w = max(0.0, nx * sx + ny * sy)
                if w <= 0:
                    continue
                r = min(fil.get(k, ch), rmax)
                t = max(0.0, (z - (z1 - r)) / r) if r > 0 else 0.0
                prof = r * (1 - math.sqrt(max(0.0, 1 - t * t))) if k in fil else r * t
                d = max(d, w * (prof + slope.get(k, 0.0) * (z - z0) / h))
            return d
        rings.append([(x, y, z) for x, y in offset_poly(poly, dist)])
    loft(rings, m)


def box(m, c0, r0, c1, r1, z0, z1, ch=0.25, r=0.25, seg=2, **kw):
    """A block over columns c0..c1, rows r0..r1 (pixel edges)."""
    slab(m, rrect(X(c0), Y(r1), X(c1), Y(r0), r, seg), z0, z1, ch=ch, **kw)


def extrude(m, poly_uz, v0, v1, axis="y"):
    """Extrude a closed (u, z) polygon from v0 to v1; axis 'y': u = x, v = y; 'x': u = y, v = x."""
    P = (lambda u, v, z: (u, v, z)) if axis == "y" else (lambda u, v, z: (v, u, z))
    loft([[P(u, v0, z) for u, z in poly_uz], [P(u, v1, z) for u, z in poly_uz]], m)


def plan_loft(m, poly, levels):
    rings = []
    for L in levels:
        def dist(nx, ny, L=L):
            d = 0.0
            for k, (sx, sy) in SIDES.items():
                w = max(0.0, nx * sx + ny * sy)
                if w > 1e-6:
                    d = max(d, w * L.get(k, 0.0))
            return d
        rings.append([(x, y, L["z"]) for x, y in offset_poly(poly, dist)])
    loft(rings, m)


def tube(m, path, r, n=12, cap0=True, cap1=True):
    """A round tube along a polyline (parallel-transported, mitred rings)."""
    pts = [Vector(p) for p in path]
    rings = []
    t0 = (pts[1] - pts[0]).normalized()
    up = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    e1 = t0.cross(up).normalized()
    prev_t = t0
    for i, p in enumerate(pts):
        if i == 0:
            t = t0
        elif i == len(pts) - 1:
            t = (pts[i] - pts[i - 1]).normalized()
        else:
            t = ((pts[i] - pts[i - 1]).normalized() + (pts[i + 1] - pts[i]).normalized()).normalized()
        # transport e1
        e1 = (e1 - t * e1.dot(t)).normalized()
        e2 = t.cross(e1)
        R = []
        for k in range(n):
            th = 2 * math.pi * (k + 0.5) / n
            R.append(tuple(p + e1 * (math.cos(th) * r) + e2 * (math.sin(th) * r)))
        rings.append(R)
        prev_t = t
    loft(rings, m, cap0, cap1)


def corr(x, c0, pitch, amp):
    """Trapezoid corrugation 0..amp, crest centred on x = c0 + k * pitch."""
    t = math.cos(2 * math.pi * (x - c0) / pitch)
    return amp * (max(-1.0, min(1.0, 1.7 * t)) + 1) / 2


def frange(a, b, s):
    out, x = [], a
    while x <= b + 1e-9:
        out.append(round(x, 4))
        x += s
    if out[-1] < b - 1e-6:
        out.append(b)
    return out


# ----------------------------------------------------------------------------------------------
# The floor
# ----------------------------------------------------------------------------------------------

def build_floor():
    dark = mat(2, "stone")
    box(dark, 0, 28, 48, 84, 0.0, ZB, ch=0.02, r=0.02, seg=1)
    # kerb blocks down the west side (col 3 = joint shadow) and the east side, beyond the trench
    for r0, r1 in ((28.1, 36.8), (37.2, 47.8), (48.2, 58.8), (59.2, 69.8), (70.2, 76.8), (77.2, 83.9)):
        box(mat(6, "stone"), 0.1, r0, 3.4, r1, ZB, ZF + 0.8, ch=0.25)
    for r0, r1 in ((28.1, 41.8), (42.2, 55.8), (56.2, 69.8)):
        box(mat(3, "stone"), 45.15, r0, 47.9, r1, ZB, ZF + 0.6, ch=0.2)
    # under the cradle and the pipe: plain floor slabs (mostly hidden)
    box(mat(5, "stone"), 3.6, 28.1, 42.0, 69.6, ZB, ZF, ch=0.06, r=0.1)
    # paving south of everything (rows 79-84: joints every 4 cols, staggered at row 81)
    sl = mat(5, "stone")
    for c in range(0, 48, 4):
        box(sl, c + 0.12, 79.15, c + 3.88, 80.92, ZB, ZF, ch=0.08, r=0.1)
    for c in range(-2, 48, 4):
        box(sl, max(0.1, c + 0.12), 81.08, min(47.95, c + 3.88), 83.95, ZB, ZF, ch=0.08, r=0.1)
    # west of the grating (cols 0-10, rows 70-79)
    for c0, c1 in ((3.6, 6.9), (7.1, 9.0)):
        for r0, r1 in ((70.2, 74.4), (74.6, 78.95)):
            box(sl, c0, r0, c1, r1, ZB, ZF, ch=0.08, r=0.1)
    # the pit east of the grating (cols 41-47): a shallow sump, its rim a slab (pal 3)
    box(mat(3, "stone"), 44.0, 70.2, 47.9, 78.95, ZB, ZF - 0.05, ch=0.06, r=0.1)
    # drain grating: angle-iron frame, flat bars every 4 px on a spine, over the dark pit
    box(mat(8, "steel"), 9.0, 69.9, 41.0, 70.9, ZB, ZF + 0.45, ch=0.15)
    box(mat(6, "steel"), 9.0, 78.2, 41.0, 79.0, ZB, ZF + 0.35, ch=0.12)
    box(mat(6, "steel"), 9.0, 70.8, 9.9, 78.3, ZB, ZF + 0.35, ch=0.12)
    box(mat(6, "steel"), 40.1, 70.8, 41.0, 78.3, ZB, ZF + 0.35, ch=0.12)
    box(mat(3, "steel"), 9.9, 74.2, 40.1, 74.8, ZB, ZF + 0.12, ch=0.06)
    for c in range(12, 37, 4):
        box(mat(4, "steel"), c, 70.8, c + 1, 78.3, ZB, ZF + 0.3, ch=0.12, r=0.15)
    # trench east of the cradle (cols 42-45): just the dark base plate, a lip on each side
    box(mat(3, "stone"), 42.0, 28.05, 42.45, 69.9, ZB, ZF + 0.1, ch=0.06, r=0.1)


# ----------------------------------------------------------------------------------------------
# The cradle and the pipe
# ----------------------------------------------------------------------------------------------

def build_cradle():
    box(mat(3, "steel"), 5.5, 28.05, 42.0, 65.7, ZB, ZP, ch=0.25, fil={"w": 0.8}, r=0.4, seg=3)
    # sloped front apron (rows 65.7-69.25) and its round bump rail (row 69)
    extrude(mat(5, "steel"), [(Y(69.25), ZB), (Y(65.6), ZB), (Y(65.6), ZP), (Y(69.25), 1.05)], X(5.5), X(42.0), "x")
    tube(mat(9, "metal"), [(X(5.5), Y(69.35), 0.95), (X(42.0), Y(69.35), 0.95)], 0.62, n=16)
    for c in (17.6, 27.6, 34.4):
        extrude(mat(6, "steel"), [(Y(69.1), ZB), (Y(65.5), ZB), (Y(65.5), ZP + 0.35), (Y(65.9), ZP + 0.35),
                                  (Y(69.1), 1.45)], X(c - 0.35), X(c + 0.35), "x")
    # a seam where the apron meets the deck (a shallow modelled groove = a strip of the darker steel)
    box(mat(2, "steel"), 5.8, 65.55, 41.7, 65.85, ZP - 0.1, ZP + 0.02, ch=0.02, r=0.05, seg=1)
    # two louvred vent grilles (cols 14-21, 24-31, rows 59-64): frame ring, dark well, one bar
    for c0, c1 in ((13.6, 22.4), (23.6, 32.4)):
        fr = mat(4, "steel")
        box(fr, c0, 58.6, c1, 59.2, ZP - 0.1, ZP + 0.3, ch=0.1, r=0.1)
        box(fr, c0, 64.7, c1, 65.3, ZP - 0.1, ZP + 0.3, ch=0.1, r=0.1)
        box(fr, c0, 59.1, c0 + 0.6, 64.8, ZP - 0.1, ZP + 0.3, ch=0.1, r=0.1)
        box(fr, c1 - 0.6, 59.1, c1, 64.8, ZP - 0.1, ZP + 0.3, ch=0.1, r=0.1)
        box(mat(2, "dark"), c0 + 0.5, 59.1, c1 - 0.5, 64.8, ZP - 0.1, ZP + 0.02, ch=0.02, r=0.05, seg=1)
        box(mat(6, "steel"), c0 + 0.6, 60.6, c1 - 0.6, 61.6, ZP, ZP + 0.45, ch=0.02, fil={"n": 0.3, "s": 0.3}, r=0.1)
        box(mat(3, "steel"), c0 + 0.6, 63.0, c1 - 0.6, 63.6, ZP, ZP + 0.25, ch=0.08, r=0.1)
        for bx in (c0 + 0.3, c1 - 0.3):  # corner bolts
            for by in (58.9, 65.0):
                slab(mat(6, "metal"), rrect(X(bx) - 0.2, Y(by) - 0.2, X(bx) + 0.2, Y(by) + 0.2, 0.18, 2),
                     ZP + 0.3, ZP + 0.42, ch=0.05)
    # tread plate (cols 33-39) with raised lozenges
    box(mat(4, "steel"), 32.8, 59.2, 39.2, 65.3, ZP - 0.1, ZP + 0.2, ch=0.08, r=0.15)
    for i, r in enumerate(frange(60.0, 64.5, 1.1)):
        for c in frange(33.6 + (0.6 if i % 2 else 0.0), 38.4, 1.2):
            cx, cy = X(c), Y(r)
            slab(mat(5, "steel"), [(cx, cy - 0.38), (cx + 0.22, cy), (cx, cy + 0.38), (cx - 0.22, cy)],
                 ZP + 0.2, ZP + 0.3, ch=0.03)
    # west deck strip beside the container: a riveted access plate with corner bolts, and the dark
    # kick plate where the container meets the deck
    box(mat(3, "steel"), 7.3, 56.4, 12.6, 64.6, ZP - 0.1, ZP + 0.3, ch=0.12, r=0.15)
    box(mat(4, "steel"), 7.9, 57.0, 12.0, 64.0, ZP + 0.2, ZP + 0.36, ch=0.06, r=0.12)
    box(mat(2, "steel"), 9.4, 57.4, 10.5, 63.6, ZP + 0.34, ZP + 0.46, ch=0.04, r=0.1)  # handle recess
    for bx in (8.4, 11.5):
        for by in (57.6, 63.4):
            slab(mat(6, "metal"), rrect(X(bx) - 0.22, Y(by) - 0.22, X(bx) + 0.22, Y(by) + 0.22, 0.2, 2),
                 ZP + 0.3, ZP + 0.5, ch=0.06)
    box(mat(2, "steel"), 13.0, 55.0, 40.8, 55.9, ZP - 0.1, ZP + 0.35, ch=0.1, r=0.1)
    # chocks along the container's feet (mostly hidden under the shoulders)
    for r in (31, 40, 49):
        box(mat(4, "steel"), 5.8, r, 7.3, r + 3, ZP - 0.1, ZP + 1.4, ch=0.2, slope={"w": 0.8})
        box(mat(4, "steel"), 40.7, r, 41.9, r + 3, ZP - 0.1, ZP + 1.4, ch=0.2, slope={"e": 0.6})


def build_pipe():
    pz, px = 1.35, X(5.0)
    pm = mat(10, "metal")
    path = [(px, Y(28.25), pz), (px, Y(65.0), pz)]
    # the bend down into the floor (radius 1.4 px)
    rb = 1.4
    for k in range(1, 7):
        a = math.radians(90 * k / 6)
        path.append((px, Y(65.0) - rb * math.sin(a), pz - rb * (1 - math.cos(a))))
    path.append((px, Y(65.0) - rb, ZB))
    tube(pm, path, 0.92, n=16)
    # flange at the north end (it continues into the next tile)
    tube(mat(7, "metal"), [(px, Y(28.05), pz), (px, Y(28.6), pz)], 1.12, n=16)
    for r in (34, 46, 58):
        tube(mat(7, "metal"), [(px, Y(r - 0.45), pz), (px, Y(r + 0.45), pz)], 1.1, n=16)
        box(mat(6, "steel"), 3.9, r - 0.55, 6.1, r + 0.55, ZF, pz - 0.5, ch=0.1, r=0.1)
    # collar where it enters the floor
    tube(mat(7, "metal"), [(px, Y(65.0) - rb, ZF - 0.05), (px, Y(65.0) - rb, ZF + 0.35)], 1.15, n=16)


# ----------------------------------------------------------------------------------------------
# The container
# ----------------------------------------------------------------------------------------------

def sh(z):
    return max(0.0, (z - ZS) / (ZTF - ZS))


def sl(z):
    return 2.25 * z / ZTF


def roof_z(x):
    return ZT + corr(x, 14.5, 2, 0.26)


def build_container(G):
    hdr = mat(10, "metal")
    # north header (rows 15-19.6): plan corners cut on the diagonal as the sprite's rows 15-17
    frame_n = [(X(7), Y(19.6)), (X(41), Y(19.6)), (X(41), Y(17.6)), (X(34), Y(15)), (X(13), Y(15)), (X(7), Y(17.1))]
    plan_loft(hdr, frame_n, [
        {"z": 0}, {"z": ZS}, {"z": ZTF - 0.55, "w": 6 * sh(ZTF - 0.55), "e": 8 * sh(ZTF - 0.55)},
        {"z": ZTF - 0.18, "w": 6, "e": 8, "n": 0.18}, {"z": ZTF, "w": 6.15, "e": 8.15, "n": 0.55, "s": 0.12}])
    # south header (rows 47.6-55.2), its south face leaning back over rows 53-55
    frame_s = [(X(7), Y(55.2)), (X(41), Y(55.2)), (X(41), Y(47.6)), (X(7), Y(47.6))]
    plan_loft(hdr, frame_s, [
        {"z": 0, "s": sl(0)}, {"z": ZS, "s": sl(ZS)},
        {"z": ZTF - 0.5, "w": 6 * sh(ZTF - 0.5), "e": 8 * sh(ZTF - 0.5), "s": sl(ZTF - 0.5)},
        {"z": ZTF - 0.15, "w": 6, "e": 8, "s": sl(ZTF - 0.15) + 0.12, "n": 0.0},
        {"z": ZTF, "w": 6.15, "e": 8.15, "s": sl(ZTF) + 0.35, "n": 0.12}])

    # door leaves on the south face (the 7 band): two plates on the slope, a gap between them
    def face_y(z):
        return Y(55.2) + sl(z)
    dm = mat(7, "metal")
    for c0, c1 in ((12.5, 23.1), (23.4, 34.0)):
        plan_loft(dm, [(X(c0), Y(55.45)), (X(c1), Y(55.45)), (X(c1), Y(54.75)), (X(c0), Y(54.75))],
                  [{"z": 0.4, "s": sl(0.4)}, {"z": ZS + 1.6, "s": sl(ZS + 1.6)}])
    # locking rods with cams top and bottom, handles
    lm = mat(8, "metal")
    for c in (15.5, 20.5, 26.0, 31.0):
        a = (X(c), face_y(0.7) - 0.42, 0.7)
        b = (X(c), face_y(ZS + 1.3) - 0.42, ZS + 1.3)
        tube(lm, [a, b], 0.26, n=8)
        for z in (0.9, ZS + 1.1):
            yy = face_y(z) - 0.42
            slab(lm, rrect(X(c) - 0.42, yy - 0.3, X(c) + 0.42, yy + 0.3, 0.12, 2), z - 0.3, z + 0.3, ch=0.08)
        tube(lm, [(X(c), face_y(3.2) - 0.5, 3.2), (X(c) + 0.9, face_y(3.2) - 0.75, 3.2),
                  (X(c) + 1.8, face_y(3.2) - 0.6, 3.2)], 0.19, n=6)

    # mid body (rows 19.6-47.6): sloped corrugated shoulders, corrugated roof, edge rails
    y0, y1 = Y(47.6), Y(19.6)
    west = [(X(x), ZS + (ZT - ZS) * (x - 7.25) / 5.75 + corr(x, 8.5, 2, 0.28)) for x in frange(7.25, 13.0, 0.25)]
    extrude(mat(9, "metal"), [(X(7.25), 0.0)] + west + [(X(13.0), 0.0)], y0, y1)
    roof = [(X(x), roof_z(x)) for x in frange(13.0, 33.0, 0.25)]
    extrude(mat(10, "metal"), [(X(13.0), 0.0)] + roof + [(X(33.0), 0.0)], y0, y1)
    east = [(X(x), ZT - (ZT - ZS) * (x - 33) / 7.75 + corr(x, 35.5, 2, 0.28)) for x in frange(33.0, 40.75, 0.25)]
    extrude(mat(6, "metal"), [(X(33.0), 0.0)] + east + [(X(40.75), 0.0)], y0, y1)
    # vertical ribs on the side walls (below the shoulder edge) and down the north end
    rib = mat(9, "metal")
    for r in frange(21.0, 46.0, 2.0):
        box(rib, 6.95, r, 7.35, r + 0.9, 0.3, ZS - 0.15, ch=0.12, r=0.15)
        box(mat(6, "metal"), 40.65, r, 41.05, r + 0.9, 0.3, ZS - 0.15, ch=0.12, r=0.15)
    for c in frange(14.6, 32.6, 2.0):  # north end wall ribs
        box(mat(10, "metal"), c, 14.95, c + 0.9, 15.35, 0.3, ZS - 0.15, ch=0.12, r=0.15)
    # door hinges down both outer edges of the door leaves, and the rubber seal between them
    for c0, c1 in ((11.7, 12.6), (33.9, 34.8)):
        for z in (1.2, 3.6, 6.0):
            yy = face_y(z) - 0.3
            slab(lm, rrect(X(c0), yy - 0.35, X(c1), yy + 0.25, 0.15, 2), z - 0.45, z + 0.45, ch=0.1)
    plan_loft(mat(2, "dark"), [(X(23.1), Y(55.5)), (X(23.4), Y(55.5)), (X(23.4), Y(54.9)), (X(23.1), Y(54.9))],
              [{"z": 0.4, "s": sl(0.4)}, {"z": ZS + 1.6, "s": sl(ZS + 1.6)}])
    for rr in ((12.85, 13.75), (32.3, 33.2)):
        box(mat(11, "metal"), rr[0], 19.4, rr[1], 47.8, ZT - 0.3, ZT + 0.42, ch=0.02, fil={"w": 0.3, "e": 0.3}, r=0.1)
    # transverse seams where the roof meets the headers: a dark strip in a groove
    for r0 in (19.45, 47.45):
        box(mat(9, "metal"), 13.6, r0, 32.4, r0 + 0.3, ZT - 0.2, ZT + 0.15, ch=0.02, r=0.05, seg=1)

    # ISO corner castings (plain tops, as the sprite), each with a twist-lock aperture on its faces
    cm9, cm7 = mat(9, "metal"), mat(7, "metal")
    box(cm9, 7.0, 17.2, 10.4, 20.4, 0.0, ZS + 1.25, ch=0.3)
    box(cm7, 37.2, 17.7, 41.0, 20.6, 0.0, ZS + 1.05, ch=0.3)
    box(cm9, 7.0, 50.2, 10.6, 55.3, 0.0, ZS + 1.25, ch=0.3, slope={"s": 1.2})
    box(cm7, 37.0, 50.2, 41.0, 55.3, 0.0, ZS + 1.05, ch=0.3, slope={"s": 1.2})
    ap = mat(2, "dark")
    for c, z in ((8.7, ZS - 0.6), (39.1, ZS - 0.8)):  # oval apertures on the south faces (seen from the camera)
        zz = z
        yy = Y(55.3) + 1.2 * zz / (ZS + 1.15) - 0.02
        slab(ap, rrect(X(c) - 0.7, yy - 0.12, X(c) + 0.7, yy + 0.05, 0.05, 1), zz - 0.4, zz + 0.4, ch=0.01)

    # the stencilled 218: smooth outlines traced from the sprite's 12/13 pixels, painted as strips
    # just over the corrugated roof (each roof facet split along y where a glyph edge crosses it)
    stencil(G)


def stencil(G):
    sten = np.zeros((H, W), float)
    for r in range(20, 48):
        for c in range(14, 33):
            if G[r][c] in (12, 13):
                sten[r, c] = 1.0
    K = 16  # samples per px
    # bilinear field at pixel centres, then a small blur: rounded stroke ends, straight strokes kept
    ys = (np.arange(H * K) + 0.5) / K - 0.5
    xs = (np.arange(W * K) + 0.5) / K - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 2)
    x0 = np.clip(np.floor(xs).astype(int), 0, W - 2)
    fy = np.clip(ys - y0, 0, 1)[:, None]
    fx = np.clip(xs - x0, 0, 1)[None, :]
    a = sten[y0][:, x0]
    b = sten[y0][:, x0 + 1]
    c = sten[y0 + 1][:, x0]
    d = sten[y0 + 1][:, x0 + 1]
    f = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    k = np.exp(-0.5 * (np.arange(-8, 9) / (0.28 * K)) ** 2)
    k /= k.sum()
    f = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, f)
    f = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, f)
    on = f >= 0.42
    sm = mat(12, "paint")
    step = 0.125
    for x in frange(13.75, 32.25 - step, step):
        cx = int((x + step / 2) * K)
        col = on[:, cx]
        r = 20 * K
        while r < 48 * K:
            if not col[r]:
                r += 1
                continue
            s = r
            while r < 48 * K and col[r]:
                r += 1
            ra, rb = s / K, r / K
            if rb - ra < 0.3:
                continue
            za, zb = roof_z(x) + 0.04, roof_z(x + step) + 0.04
            vs = [V((X(x), Y(rb), za)), V((X(x + step), Y(rb), zb)), V((X(x + step), Y(ra), zb)), V((X(x), Y(ra), za))]
            face(vs, sm)


# ----------------------------------------------------------------------------------------------
# Assembly, outline shell, export
# ----------------------------------------------------------------------------------------------

def to_object(coll, name):
    global BM
    bmesh.ops.remove_doubles(BM, verts=BM.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(BM, faces=[f for f in BM.faces if f.material_index != SLOTS.get((12, "paint"))])
    for f in BM.faces:  # the stencil paint always faces up
        if f.material_index == SLOTS.get((12, "paint")) and f.normal.z < 0:
            f.normal_flip()
    bmesh.ops.transform(BM, matrix=Matrix.Scale(1 / 12, 4), verts=BM.verts)
    me = bpy.data.meshes.new(name)
    BM.to_mesh(me)
    BM.free()
    BM = bmesh.new()
    for m in MATS:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35.0))
    return obj


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells: no seams outlined)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


SPRITE = None


def main():
    global SPRITE
    colors, G = load_composite()
    SPRITE = {"name": NAME, "colors": colors}
    coll = common.reset_collection(NAME + "_A")
    build_floor()
    floor = to_object(coll, NAME + "_floor")
    build_cradle()
    build_pipe()
    build_container(G)
    struct = to_object(coll, NAME + "_struct")
    # The outline shell (D51) is made from the machinery only: the floor runs to the tile edges
    # (the sprite draws colour to its edge there, no ink border), so it gets no ink round it.
    shell = common.outline_shell(struct, coll, voxel=0.014, faces=4000, smooth=6, inside=0.01)
    shell.hide_render = True
    # join floor + machinery into the model
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    floor.select_set(True)
    struct.select_set(True)
    bpy.context.view_layer.objects.active = struct
    bpy.ops.object.join()
    obj = struct
    obj.name = NAME
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    fmt = "AUTO"
    if "--no-bake" not in argv:
        # AO/roughness only (D50/D65): every palette material except the crisp stencil paint
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(SLOTS[k] for k in SLOTS if k[1] != "paint")
        import tempfile
        T.bake_maps(obj, tempfile.mkdtemp(prefix="nshp165_bake_"), size=1024, samples=64)
        fmt = "WEBP"
    layout = [(n, ci * 24 + 12 - W / 2, ri * 28 + 14 - H / 2)
              for ri, row in enumerate(PIECES) for ci, n in enumerate(row)]
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    out_objs, tris = [], 0
    for name, cx, cy in layout:
        p, s = pieces[name], shells[name]
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(35.0))
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        objs = [p] + ([s] if s.data.polygons else [])
        common.export_sprite_model(WT, objs, f"enemies/{name}", common.load_sprite(WT, name)["sprites"],
                                   image_format=fmt)
        for o in objs:
            o.location = (cx / 12, -cy / 12, 0)
        out_objs += objs
        p.data.calc_loop_triangles()
        tris += len(p.data.loop_triangles)
        print(f"piece {name}: {len(p.data.loop_triangles)} tris, shell {len(s.data.polygons)} faces")
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.objects.remove(shell, do_unlink=True)
    if "--out" in argv:
        common.export_glb(out_objs, Path(argv[argv.index("--out") + 1]), image_format=fmt)
    print(f"built {NAME}: {tris} triangles, {len(MATS)} materials")


if __name__ == "__main__":
    main()
