"""Golden shield emblem (newshd.shp frames 79, 81, 83, 24 x 28 px, palette 5): a machined gold
shield plate that is its sprite in 3D (D50-D53, D65, D74). Seen in episodes 1-3.

A heraldic shield plate lying on the ground: two pointed shoulders and a pierced lug along the top,
straight sides, and a bowl tapering to a small stepped point. Its top is a shallow crown rising to
a boss: a flat-topped, chamfered bezel ring round a recessed socket holding a blue gem (the only
part the three frames change: dark blue, blue, pale teal; palette_material frames=). Raised ribs
of chamfered trapezoid section run over the crown: an X from the shoulders down to the bezel, a
rib out along each wing's upper edge, one along each wing's lower edge, and two down to the point.
A recessed slot below the lug sits in the V of the X arms. The plate's wall carries a machined
groove all round; the underside is a plain chamfered closed base.

Plan: the sprite's INNER mask (D74, the ink border is the game's outline), fitted per row (Chaikin
smoothed control polygon). Colours: the sprite's palette index per region (trimmed medians).

Units: sprite px (c = column edge right, r = row edge down, z up from the base); Blender
X = (c - 12) / 12, Y = (14 - r) / 12, Z = (z + Z0) / 12.

Run: blender --background --python assets/blender/enemies/newshd-79.py [-- --no-bake] [-- --preview out.png]

Exports public/models/enemies/newshd-79.glb (one model for all three frames; the gem takes each
frame's colour) and src/render/spriteModels/newshd-79.json. The AO/roughness maps are baked here
(D50); there is no concept projection.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (pchip, join, bake_maps)

ROOT = common.repo_root(__file__)
NAME = "newshd-79"
PX = 1 / 12
Z0 = -1.8       # the base sits 1.8 px below the model's origin plane
AX = 12.0       # the sprite's centre line (column edge)
BOSS = (12.0, 17.6)   # the gem's centre (edge coordinates)

# --- materials ------------------------------------------------------------------------------------
# (slot, palette index, metallic, roughness). Indices: each region's trimmed median in the sprite
# (outline 1 dropped, darkest and brightest 15% left out as lighting/sheen). Satin gold, not mirror.
MATS = [
    ("field", 23, 0.45, 0.42),   # the face panel and collar
    ("wall", 23, 0.42, 0.46),    # rim band, rim chamfer and wall
    ("groove", 20, 0.3, 0.6),    # the wall's machined groove, the base
    ("rib_x", 29, 0.55, 0.32),   # the X arms
    ("rib_uw", 27, 0.55, 0.34),  # upper wing ribs
    ("rib_lw", 28, 0.55, 0.33),  # lower wing ribs
    ("rib_lr", 26, 0.55, 0.34),  # the ribs from the lower wing edge down to the point
    ("bezel", 27, 0.55, 0.3),    # the ring round the gem
    ("socket", 23, 0.4, 0.45),   # the gem's seat
    ("lug", 26, 0.55, 0.33),     # the pierced lug
    ("dark", 20, 0.25, 0.7),     # bore and slot floors and walls
    ("gem", 54, 0.0, 0.08),      # frames: 79 dark blue, 81 blue, 83 pale teal
]
M = {name: i for i, (name, *_r) in enumerate(MATS)}
GEM_FRAMES = {81: 58, 83: 134}
UNBAKED = {M["gem"]}


def materials(sprite):
    out = []
    for name, idx, met, rough in MATS:
        if name == "gem":
            out.append(common.palette_material(sprite, idx, f"{NAME}-gem", metallic=met, roughness=rough,
                                               emission_strength=1.6, frames=GEM_FRAMES))
        else:
            out.append(common.palette_material(sprite, idx, f"{NAME}_{name}", metallic=met, roughness=rough))
    return out


# --- plan -----------------------------------------------------------------------------------------

def chaikin(pts, it=2):
    """Chaikin corner cutting on an open polyline (its ends kept)."""
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]),
                    (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        out.append(pts[-1])
        pts = out
    return pts


# The left half of the plate, top centre round to the bottom centre, fitted to the inner mask row by
# row (each row's edge passes the middle of its pixel stair): the lug's neck, the notch, the pointed
# shoulder, the straight side, the bowl, the ledge at row 23 and the small point.
LEFT = [(12, 4.9), (9.6, 4.9), (9.0, 5.3), (8.7, 6.0), (7.4, 6.05), (6.6, 5.2), (4.95, 4.3), (4.4, 3.95), (3.4, 4.0),
        (2.3, 4.9), (1.2, 6.0), (0.95, 7.0), (0.95, 17.3), (1.6, 18.2), (2.6, 18.9), (2.95, 20.0), (3.3, 21.0), (4.1, 21.9),
        (5.0, 22.7), (5.6, 23.0), (7.6, 23.05), (8.3, 23.5), (8.7, 24.3), (9.4, 24.95), (12, 25.0)]


def plan():
    left = chaikin(LEFT, 2)
    right = [(2 * AX - c, r) for c, r in reversed(left[1:-1])]
    return left + right


def signed_area(poly):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def offset(poly, d):
    """Move each vertex of a closed polygon inward by d (miter, limited)."""
    s = 1 if signed_area(poly) > 0 else -1
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        ns = []
        for a, b in ((p0, p1), (p1, p2)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1
            ns.append((-dy / ln * s, dx / ln * s))  # inward normal
        nx, ny = ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        cs = max(0.5, nx * ns[1][0] + ny * ns[1][1])
        out.append((p1[0] + nx * d / cs, p1[1] + ny * d / cs))
    return out


def simplify(poly, tol=0.012):
    """Drop vertices of a closed polygon that sit within tol px of the line through their
    neighbours (Chaikin leaves many on the straight runs), so the bands round the plate stay light."""
    pts = list(poly)
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(pts) and len(pts) > 8:
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            dx, dy = c[0] - a[0], c[1] - a[1]
            ln = math.hypot(dx, dy) or 1
            if abs((b[0] - a[0]) * dy - (b[1] - a[1]) * dx) / ln < tol and ln < 3.0:
                del pts[i]
                changed = True
            else:
                i += 1
    return pts


PLAN = simplify(plan())
_P = np.array(PLAN)
_Q = np.roll(_P, -1, axis=0)


def edge_dist(c, r):
    p = np.array([c, r])
    d = _Q - _P
    t = np.clip(((p - _P) * d).sum(1) / np.maximum((d * d).sum(1), 1e-9), 0, 1)
    proj = _P + d * t[:, None]
    return float(np.sqrt(((proj - p) ** 2).sum(1)).min())


def inside(poly, c, r):
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > r) != (y1 > r) and c < x0 + (r - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


# --- heights --------------------------------------------------------------------------------------

BASE_CH = 0.6     # base chamfer (unseen)
WALL_TOP = 2.6    # top of the vertical wall
RIM_IN = 0.35     # the rim chamfer's width
RIM_Z = 2.95      # the flat rim band round the face panel (and the shoulders)
FACE_STEP = 0.3   # the face panel's chamfered step, plan width
FACE_Z = 3.8      # the face panel's edge
COLLAR_R0, COLLAR_R1, COLLAR_H = 4.0, 5.05, 0.55  # the boss's conical collar on the face

# The face panel: a raised plate inset about a pixel from the outline (the sprite's darker edge band
# is the rim round it), cut straight across under the shoulders and the lug.
# Below the wing it follows the lower rib (RIB_LR) to the point: the rib straddles the step (its
# centre line on the step's middle), so the step is capped by the rib all the way down.
FACE_LEFT = [(12, 6.6), (3.2, 6.6), (2.3, 7.3), (2.1, 8.5), (2.1, 16.9), (2.7, 17.9), (3.6, 18.7)]
# The lower rib (left half), from the lower wing's edge diagonally down to the point (sprite, right
# side: (19,20) 29, (18,21) 28, (15,22) 29, (14,23) 29, (13,24) 27).
RIB_LR = [(4.4, 20.05), (6.2, 21.35), (8.4, 22.55), (10.45, 23.95)]


def face():
    left = chaikin(FACE_LEFT, 2)
    pts = smooth_path(RIB_LR, 0.3)
    for (c, r), (tx, ty, _nx, _ny) in zip(pts, frames_of(pts)):
        h = FACE_STEP / 2  # outward (down-left) of the rib's centre line
        left.append((c - ty * h, r + tx * h))
    left += [(11.3, left[-1][1] + 0.12), (12, left[-1][1] + 0.15)]
    return left + [(2 * AX - c, r) for c, r in reversed(left[1:-1])]




def crown(c, r):
    """The top surface's height: the rim band, the face panel's step, the flat face and the boss's
    conical collar (the rise the sprite's shading shows toward the gem)."""
    if inside(FACE_IN, c, r):
        db = math.hypot(c - BOSS[0], r - BOSS[1])
        return FACE_Z + COLLAR_H * min(1.0, max(0.0, (COLLAR_R1 - db) / (COLLAR_R1 - COLLAR_R0)))
    if inside(FACE, c, r):
        return FACE_Z - 0.5 * (FACE_Z - RIM_Z)
    return RIM_Z


# --- parts ----------------------------------------------------------------------------------------

class Model:
    def __init__(self):
        self.parts = []  # (bmesh, smooth angle)

    def add(self, bm, smooth=30):
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self.parts.append((bm, smooth))
        return bm

    def hull(self, pts, mat, smooth=30):
        bm = bmesh.new()
        verts = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
        for f in bm.faces:
            f.material_index = mat
        return self.add(bm, smooth)


def bridge(bm, a, b, mat):
    """Quads between two closed loops of verts with the same count."""
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((a[i], a[j], b[j], b[i]))
        f.material_index = mat


def cdt_fill(bm, loops, zf, mat, extra=(), holes=()):
    """Fill the region inside loops[0] and outside the other loops (and `holes`, given as 2D
    polygons) with a constrained Delaunay triangulation. loops: lists of existing BMVerts (their
    x, y used); new interior points `extra` get z = zf(c, r). Returns {hole index: [BMVert]}."""
    pts, edges, faces, refs = [], [], [], []
    for loop in loops:
        k0 = len(pts)
        pts += [(v.co.x, v.co.y) for v in loop]
        refs += list(loop)
        edges += [(k0 + i, k0 + (i + 1) % len(loop)) for i in range(len(loop))]
        faces.append(list(range(k0, len(pts))))
    hole_ix = []
    for h in holes:
        k0 = len(pts)
        pts += list(h)
        refs += [None] * len(h)
        edges += [(k0 + i, k0 + (i + 1) % len(h)) for i in range(len(h))]
        faces.append(list(range(k0, len(pts))))
        hole_ix.append(k0)
    pts += list(extra)
    refs += [None] * len(extra)
    vc, _e, fc, vorig, _eo, _fo = delaunay_2d_cdt([Vector(p) for p in pts], edges, faces, 2, 1e-6, True)
    verts = []
    for k, co in enumerate(vc):
        o = vorig[k][0] if vorig[k] else None
        if o is not None and refs[o] is not None:
            verts.append(refs[o])
        else:
            verts.append(bm.verts.new((co.x, co.y, zf(co.x, co.y))))
    hole_verts = {}
    for hi, (h, k0) in enumerate(zip(holes, hole_ix)):
        found = {}
        for k in range(len(vc)):
            o = vorig[k][0] if vorig[k] else None
            if o is not None and k0 <= o < k0 + len(h):
                found[o - k0] = verts[k]
        hole_verts[hi] = [found[i] for i in range(len(h))]
    for f in fc:
        cx = sum(vc[i].x for i in f) / len(f)
        cy = sum(vc[i].y for i in f) / len(f)
        if not inside([(v.co.x, v.co.y) for v in loops[0]], cx, cy):
            continue
        if any(inside([(v.co.x, v.co.y) for v in lp], cx, cy) for lp in loops[1:]) or any(inside(h, cx, cy) for h in holes):
            continue
        bm.faces.new([verts[i] for i in f]).material_index = mat
    return hole_verts


SLOT = [(11.0, 8.9), (13.0, 8.9), (13.0, 11.5), (12.0, 12.5), (11.0, 11.5)]
SLOT_DEPTH = 0.75


def build_plate(m):
    bm = bmesh.new()
    loops = [  # (inset, z, material of the band from the previous loop up to this one)
        (BASE_CH, 0.0, None),
        (0.0, BASE_CH, M["groove"]),
        (0.0, 1.15, M["wall"]),
        (0.22, 1.21, M["groove"]),
        (0.22, 1.55, M["groove"]),
        (0.0, 1.61, M["groove"]),
        (0.0, WALL_TOP, M["wall"]),
        (RIM_IN, RIM_Z, M["wall"]),
    ]
    rings = []
    for d, z, mat in loops:
        ring = [bm.verts.new((c, r, z)) for c, r in (offset(PLAN, d) if d else PLAN)]
        if rings:
            bridge(bm, rings[-1], ring, mat)
        rings.append(ring)
    bm.faces.new(list(reversed(rings[0]))).material_index = M["groove"]
    rim = rings[-1]
    # The rim band (flat) between the chamfer and the face panel.
    face0 = [bm.verts.new((c, r, RIM_Z)) for c, r in FACE]
    cdt_fill(bm, [rim, face0], lambda c, r: RIM_Z, M["wall"])
    # The face panel's chamfered step and its crowned top, with the slot as a hole.
    face1 = [bm.verts.new((c, r, FACE_Z)) for c, r in FACE_IN]
    bridge(bm, face0, face1, M["field"])
    grid = []
    hv = cdt_fill(bm, [face1], crown, M["field"], extra=grid, holes=[SLOT])
    top = hv[0]
    for v in top:
        v.co.z = crown(v.co.x, v.co.y)
    zf = min(v.co.z for v in top) - SLOT_DEPTH
    low = [bm.verts.new((v.co.x, v.co.y, zf)) for v in top]
    bridge(bm, top, low, M["dark"])
    bm.faces.new(low).material_index = M["dark"]
    m.add(bm, smooth=20)


def surface(c, r):
    """The true top surface height under (c, r): the crown, and the rim chamfer near the edge."""
    d = edge_dist(c, r)
    if d < RIM_IN:
        return WALL_TOP + (RIM_Z - WALL_TOP) * d / RIM_IN
    return crown(c, r)


def smooth_path(path, step=0.42):
    """The control polyline as a smooth curve: x(s) and y(s) pchip-interpolated over chord length."""
    s = [0.0]
    for (c0, r0), (c1, r1) in zip(path, path[1:]):
        s.append(s[-1] + math.hypot(c1 - c0, r1 - r0))
    fx = T.pchip(s, [p[0] for p in path])
    fy = T.pchip(s, [p[1] for p in path])
    k = max(2, int(math.ceil(s[-1] / step)))
    return [(fx(s[-1] * i / k), fy(s[-1] * i / k)) for i in range(k + 1)]


def frames_of(path):
    """Unit tangent and normal at each point of a sampled path."""
    out = []
    n = len(path)
    for i in range(n):
        a, b = path[max(0, i - 1)], path[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty)
        out.append((tx / ln, ty / ln, -ty / ln, tx / ln))
    return out


FACE = simplify(face())
FACE_IN = offset(FACE, FACE_STEP)


def rib(m, path, mat, w0=0.62, w1=0.28, h=0.55, sink=0.3, end_ch=0.4, margin=0.12, flat_end=True):
    """A raised rib: one chamfered trapezoid section swept along a pchip-smoothed curve on the top
    surface. Its top rides a smoothed height over the terraces it crosses; its foot goes below the
    lowest surface under it (closed, no gaps where it steps down); its outer end stops inside the
    plate edge and (flat_end) on one terrace, capped flush; both ends' tops are chamfered down. The
    hooks to the point (flat_end=False) step down over the face panel's edge: their foot reaches
    the lower terrace."""
    pts = smooth_path(path)
    fr = frames_of(pts)

    def foot_ok(i):
        c, r = pts[i]
        _tx, _ty, nx, ny = fr[i]
        return all(inside(PLAN, c + nx * o, r + ny * o) and edge_dist(c + nx * o, r + ny * o) >= margin
                   for o in (-w0, 0.0, w0))
    def flat(i):  # the end sits on one terrace (a foot across a step pokes out of the step's chamfer)
        c, r = pts[i]
        _tx, _ty, nx, ny = fr[i]
        zs = [surface(c + nx * o + _tx * t, r + ny * o + _ty * t) for o in (-w0, -w0 / 2, 0.0, w0 / 2, w0)
              for t in (-0.15, 0.0, end_ch, 2 * end_ch)]
        return max(zs) - min(zs) < 0.02
    k0 = 0
    while k0 < len(pts) - 3 and not (foot_ok(k0) and (flat(k0) or not flat_end)):
        k0 += 1
    if k0 > 0:  # slide the new end back toward the trimmed sample as far as it still fits
        keep = pts[k0]
        a, b = pts[k0 - 1], pts[k0]
        for t in (0.8, 0.6, 0.4, 0.2):
            pts[k0] = (b[0] + (a[0] - b[0]) * t, b[1] + (a[1] - b[1]) * t)
            if foot_ok(k0) and (flat(k0) or not flat_end):
                break
        else:
            pts[k0] = keep
    print(f"{NAME}: rib {mat} trimmed {k0} of {len(pts)} samples at the outer end")
    pts, fr = pts[k0:], fr[k0:]
    n = len(pts)
    offs = [-w0 + 2 * w0 * j / 6 for j in range(7)]
    hi, lo = [], []
    for i, (c, r) in enumerate(pts):
        _tx, _ty, nx, ny = fr[i]
        zs = []
        # The footprint between this ring and its neighbours (the bottom faces are straight between).
        for q in (pts[max(0, i - 1)], pts[min(n - 1, i + 1)]):
            for t in (0.0, 0.25, 0.5):
                cc, rr = c + (q[0] - c) * t, r + (q[1] - r) * t
                zs += [surface(cc + nx * o, rr + ny * o) for o in offs]
        hi.append(max(zs))
        lo.append(min(zs))
    # The top: a smoothed ride over the steps, never closer than the shoulder height to the surface.
    win = 4
    top = []
    for i in range(n):
        js = range(max(0, i - win), min(n, i + win + 1))
        wsum = sum(1 + win - abs(j - i) for j in js)
        top.append(sum((1 + win - abs(j - i)) * hi[j] for j in js) / wsum + h)
    for _ in range(2):
        top = [max(t, hz + 0.65 * h + 0.06) for t, hz in zip(top, hi)]
        top = [top[0]] + [(top[i - 1] + 2 * top[i] + top[i + 1]) / 4 for i in range(1, n - 1)] + [top[-1]]
    top = [max(t, hz + 0.65 * h + 0.06) for t, hz in zip(top, hi)]
    sec = [(-w0, None), (-w0, 0.35), (-w1, 1.0), (w1, 1.0), (w0, 0.35), (w0, None)]
    bm = bmesh.new()
    rings = []
    for i, (c, r) in enumerate(pts):
        tx, ty, nx, ny = fr[i]
        ring = []
        for o, f in sec:
            pc, pr = c + nx * o, r + ny * o
            if f is None:
                z = lo[i] - sink
            else:
                z = top[i] - h * (1.0 - f)
            if f == 1.0 and i in (0, n - 1):  # chamfered ends: pull the top back along the rib
                sg = 1 if i == 0 else -1
                pc, pr = pc + tx * end_ch * sg, pr + ty * end_ch * sg
            ring.append(bm.verts.new((pc, pr, z)))
        rings.append(ring)
    for a_, b_ in zip(rings, rings[1:]):
        for k in range(len(sec)):
            j = (k + 1) % len(sec)
            bm.faces.new((a_[k], a_[j], b_[j], b_[k])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat
    m.add(bm, smooth=35)


def to_ring(path, rad):
    """Trim/extend the path's last point onto the bezel's outer radius."""
    (c0, r0), (c1, r1) = path[-2], path[-1]
    bx, by = BOSS
    # Solve |p0 + t (p1 - p0) - B| = rad for the root nearest t = 1.
    dx, dy = c1 - c0, r1 - r0
    fx, fy = c0 - bx, r0 - by
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    cc = fx * fx + fy * fy - rad * rad
    disc = max(0.0, b * b - 4 * a * cc)
    t = (-b - math.sqrt(disc)) / (2 * a)
    return path[:-1] + [(c0 + dx * t, r0 + dy * t)]


def mirror(path):
    return [(2 * AX - c, r) for c, r in path]


RIBS = [  # (left-half path in edge coordinates, ending toward the boss; material)
    ([(5.1, 7.25), (6.4, 8.5), (10.3, 12.7), (11.3, 14.2)], "rib_x"),
    ([(2.75, 13.35), (4.3, 15.0), (5.2, 15.5), (7.4, 15.6), (9.0, 16.4)], "rib_uw"),
    ([(3.9, 18.45), (6.6, 18.35), (8.6, 17.9)], "rib_lw"),
]
BEZEL_OUT = 3.95


def build_ribs(m):
    for path, mat in RIBS:
        p = to_ring(path, BEZEL_OUT - 0.25)
        for side in (p, mirror(p)):
            rib(m, side, M[mat])
    # The lower ribs: from the point (the outer end, trimmed if needed) up to the lower wing's edge,
    # straddling the face panel's step all the way, so their foot reaches the rim band.
    p = RIB_LR[::-1]
    for side in (p, mirror(p)):
        rib(m, side, M["rib_lr"], w0=0.55, w1=0.25, h=0.5, flat_end=False)


def revolve(m, cx, cy, profile, n=40, smooth=40):
    """A closed solid of revolution about the vertical axis at (cx, cy): profile [(radius, z, material
    of the band from this point to the next)], radius 0 = on the axis."""
    bm = bmesh.new()
    rings = []
    for rad, z, _ in profile:
        if rad < 1e-6:
            rings.append([bm.verts.new((cx, cy, z))])
        else:
            rings.append([bm.verts.new((cx + rad * math.cos(2 * math.pi * i / n),
                                        cy + rad * math.sin(2 * math.pi * i / n), z)) for i in range(n)])
    for (_, _, mat), a, b in zip(profile, rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                vs = (a[0], b[i], b[j])
            elif len(b) == 1:
                vs = (a[i], a[j], b[0])
            else:
                vs = (a[i], a[j], b[j], b[i])
            bm.faces.new(vs).material_index = mat
    return m.add(bm, smooth)


def build_boss(m):
    cx, cy = BOSS
    B, S, G = M["bezel"], M["socket"], M["gem"]
    zb = FACE_Z - 0.3
    zs = FACE_Z + COLLAR_H
    # The collar: a chamfered cone rising from the flat face to the bezel, with an engraved ring
    # (a machined seam) part way up.
    F, GR = M["field"], M["groove"]

    def cz(rad):
        return FACE_Z + COLLAR_H * (COLLAR_R1 - rad) / (COLLAR_R1 - COLLAR_R0)
    g0, g1, gd = 4.72, 4.4, 0.16
    revolve(m, cx, cy, [(0.0, zb, F), (COLLAR_R1, zb, F), (COLLAR_R1, FACE_Z, F), (g0, cz(g0), GR),
                        (g0 - 0.06, cz(g0) - gd, GR), (g1 + 0.06, cz(g0) - gd, GR), (g1, cz(g1), F),
                        (COLLAR_R0, zs, F), (0.0, zs, F)], n=40, smooth=25)
    # The bezel: an annulus, flat top with chamfers, seated on the collar.
    revolve(m, cx, cy, [
        (0.0, zs - 0.2, B), (BEZEL_OUT + 0.05, zs - 0.2, B), (BEZEL_OUT + 0.05, zs + 0.15, B), (BEZEL_OUT - 0.25, zs + 0.85, B),
        (BEZEL_OUT - 0.45, zs + 1.0, B), (2.95, zs + 1.0, B), (2.7, zs + 0.8, S), (2.6, zs + 0.3, S),
        (2.35, zs + 0.2, S), (0.0, zs + 0.2, S),
    ], n=40, smooth=40)
    # The gem: a glossy cabochon on the socket floor.
    prof = []
    for k in range(6):
        a = (math.pi / 2) * k / 5
        prof.append((2.05 * math.cos(a), zs + 0.1 + 1.15 * math.sin(a), G))
    prof[-1] = (0.0, prof[-1][1], G)
    revolve(m, cx, cy, [(0.0, zs + 0.05, G), (2.05, zs + 0.05, G)] + prof[:-1] + [prof[-1]], n=28, smooth=70)


LUG_C, LUG_W, LUG_T, LUG_E = (12.0, 6.6), 2.05, 3.95, 3.0
BORE_C, BORE_R = (12.0, 6.85), 0.9


def lug_loop(grow=0.0, n=32):
    pts = []
    hy = LUG_C[1] - LUG_T
    for k in range(n):
        a = 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        x = (LUG_W + grow) * math.copysign(abs(ca) ** (2 / LUG_E), ca)
        y = (hy + grow) * math.copysign(abs(sa) ** (2 / LUG_E), sa)
        pts.append((LUG_C[0] + x, LUG_C[1] + y))
    return pts


def build_lug(m):
    bm = bmesh.new()
    n = 32
    zt = FACE_Z + 0.6
    outer0 = [bm.verts.new((c, r, 1.4)) for c, r in lug_loop(0, n)]
    outer1 = [bm.verts.new((c, r, zt - 0.3)) for c, r in lug_loop(0, n)]
    top_o = [bm.verts.new((c, r, zt)) for c, r in lug_loop(-0.3, n)]

    def bore(rad, z):
        return [bm.verts.new((BORE_C[0] + rad * math.cos(2 * math.pi * k / n),
                              BORE_C[1] + rad * math.sin(2 * math.pi * k / n), z)) for k in range(n)]
    top_i = bore(BORE_R + 0.18, zt)
    bore1 = bore(BORE_R, zt - 0.18)
    bore0 = bore(BORE_R, 1.4)
    L = M["lug"]
    bridge(bm, outer0, outer1, L)
    bridge(bm, outer1, top_o, L)
    bridge(bm, top_o, top_i, L)
    bridge(bm, top_i, bore1, L)
    bridge(bm, bore1, bore0, M["dark"])
    bridge(bm, bore0, outer0, M["dark"])
    m.add(bm, smooth=35)
    # The bore's dark floor: a plug a hair above the crown inside the bore.
    zf = crown(*BORE_C) + 0.08
    revolve(m, BORE_C[0], BORE_C[1], [(0.0, 1.5, M["dark"]), (BORE_R + 0.02, 1.5, M["dark"]),
                                      (BORE_R + 0.02, zf, M["dark"]), (0.0, zf, M["dark"])], n=24)


# --- finishing ------------------------------------------------------------------------------------

def cull_hidden(obj, ndirs=64, k=7):
    """usp_talon.cull_hidden with dense sampling: delete only faces no point of a barycentric grid
    (k per side, out to a hair inside the corners and edges) sees out of along any direction in the face's front
    hemisphere. The plate's large Delaunay triangles run under the ribs and bezel; sampling just
    their centre and a few interior points culled some whose exposed corners then showed as holes."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 2e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        for i in range(1, len(vs) - 1):  # fan triangles, barycentric grid pulled in a hair from the edges
            a, b, d = vs[0], vs[i], vs[i + 1]
            for u in range(k + 1):
                for v in range(k + 1 - u):
                    w = k - u - v
                    p = (a * u + b * v + d * w) / k
                    pts.append(p.lerp(c, 0.004))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    print(f"{NAME}: culled {len(dead)} hidden faces of {len(bm.faces)}")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()


def finish(m, mats, coll):
    mat4 = Matrix(((PX, 0, 0, -AX * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, Z0 * PX), (0, 0, 0, 1)))
    objs = []
    for k, (bm, smooth) in enumerate(m.parts):
        bmesh.ops.transform(bm, matrix=mat4, verts=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{NAME}_p{k}")
        bm.to_mesh(me)
        bm.free()
        for mt in mats:
            me.materials.append(mt)
        obj = bpy.data.objects.new(f"{NAME}_p{k}", me)
        coll.objects.link(obj)
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(smooth))
        objs.append(obj)
    return objs


def build(coll, sprite):
    mats = materials(sprite)
    m = Model()
    build_plate(m)
    build_ribs(m)
    build_boss(m)
    build_lug(m)
    return T.join(finish(m, mats, coll), NAME)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite)
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        T.TEXTURED = tuple(i for i in range(len(MATS)) if i not in UNBAKED)
        T.TINT = (1.0, 1.0, 1.0)
        T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"))
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, faces=1200)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=frame["size"])


if __name__ == "__main__":
    main()
