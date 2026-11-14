"""assembly-newsh9-197, the armoured hull section of the DREAD-NOT dreadnought (newsh9.shp,
159 161 163 165 over 197 199 201 203; level 4.14, link 14, on screen for the whole boss fight).

What it is (read from the 96x56 sprite): two big glossy sensor domes at the back, each standing on a
low drum and wrapped by a collar of armour scales. Each collar is a folded plate: a lit inner face
under the dome, a crease (the bright diagonal), and a dark outer flange that turns down and sweeps
out to a claw point at the far side. Under it two more scales step down and out, each ending in its
own claw (the middle one at the side, the lowest one at the front corner). A rounded shoulder plate
sits beside each dome's foot, and a broad curved shield closes the front between them, high at its
back edge and falling away to the front. Grey steel throughout; the sprite's bright spots (the dome
glints, the lit plate edges) are sheen and lit chamfers, the black lines under each scale are its
shadowed front wall.

Built once in assembly pixel coordinates (left half, mirrored about the edge x = 48, plus the shield
across the middle), then cut into the eight pieces with common.split_assembly. One frame each.

Each plate is a hard armour plate: its own top-view outline, a crowned top (faired by a
distance-to-edge profile and a slope away from the dome), a crisp chamfer round the top edge, and
vertical walls down to the deck (z = 0). Creases are constrained edges of the triangulation.

Run: blender -b --python assets/blender/enemies/assembly-newsh9-197.py -- [--preview out.png]
Exports the eight pieces to public/models/enemies/newsh9-<n>.glb and their spriteModels JSON.
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, geometry

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402

WT = common.repo_root(__file__)
ROOT = WT

NAME = "assembly-newsh9-197"
PIECES = ["newsh9-197", "newsh9-199", "newsh9-201", "newsh9-203",
          "newsh9-159", "newsh9-161", "newsh9-163", "newsh9-165"]
CX0, CY0 = 168, -4  # assembly centre in screen px (Blender origin)
PX = 1 / 12
AXIS = 48.5  # mirror axis (the sprite is symmetric about the centre of pixel column 48)


def X(c):
    return (c - 48.0) * PX


def Y(r):
    return (28 - r) * PX


# ---------------------------------------------------------------------------------------- 2D maths

def densify(poly, step=0.7, closed=True):
    out = []
    n = len(poly)
    for i in range(n if closed else n - 1):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        k = max(1, int(math.ceil((b - a).length / step)))
        for j in range(k):
            out.append(a.lerp(b, j / k))
    if not closed:
        out.append(Vector(poly[-1]))
    return out


def area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly)))


def seg_dist(p, a, b):
    ab = b - a
    t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length, t


def poly_dist(p, pts, closed=True):
    n = len(pts)
    best = 1e9
    for i in range(n if closed else n - 1):
        d, _ = seg_dist(p, pts[i], pts[(i + 1) % n])
        if d < best:
            best = d
    return best


def inside(p, poly):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) through (xs, ys); returns f(x)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(j for j in range(n - 1) if xs[j] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


class Line:
    """A polyline in pixel coords: projection parameter (0..1 along its length) and signed side."""

    def __init__(self, pts):
        self.p = [Vector(q) for q in pts]
        self.L = [0.0]
        for i in range(1, len(self.p)):
            self.L.append(self.L[-1] + (self.p[i] - self.p[i - 1]).length)

    def project(self, q):
        q = Vector(q)
        best = (1e9, 0.0, 0.0)
        for i in range(len(self.p) - 1):
            d, t = seg_dist(q, self.p[i], self.p[i + 1])
            if d < best[0]:
                a, b = self.p[i], self.p[i + 1]
                cross = (b - a).x * (q - a).y - (b - a).y * (q - a).x
                best = (d, (self.L[i] + t * (self.L[i + 1] - self.L[i])) / self.L[-1], cross)
        d, s, cross = best
        return d, s, (1 if cross > 0 else -1)


# ---------------------------------------------------------------------------------------- plates

RING = 0.9  # edge vertex spacing (px)
# The round opening between the domes (the sprite's transparent hole, rows 4-34 on the axis). Its rim
# is a recess: the plates bevel down into it over LIP_W px (to 1 - LIP_K of their height at the
# edge), the outer LIP_DARK px of that bevel are the sprite's dark rim (pal 2) and the walls down the
# opening are its black shaft (pal 1), so the tilted camera sees a deep black hole, not lit wall tops.
HOLE = {"loop": None, "mats": None}
LIP_W, LIP_K, LIP_DARK = 6.0, 0.88, 1.4


HOLE_BOX = (36.0, 61.0, 4.5, 35.5)  # cols, rows of the notch between the domes (open at the top)


def hole_segments(sil):
    """The silhouette edges that bound the opening: both ends inside HOLE_BOX."""
    c0, c1, r0, r1 = HOLE_BOX
    ok = lambda p: c0 <= p.x <= c1 and r0 <= p.y <= r1  # noqa: E731
    segs = []
    for lp in sil:
        for i in range(len(lp)):
            a, b = Vector(lp[i]), Vector(lp[(i + 1) % len(lp)])
            if ok(a) and ok(b):
                segs.append((a, b))
    return segs


def hole_creases(sil, o):
    """Polylines `o` px inside the opening's edge (constrained edges where the dark lip ends)."""
    c0, c1, r0, r1 = HOLE_BOX
    solid = lambda q: sum(inside(q, lp) for lp in sil) % 2 == 1  # noqa: E731
    lines = []
    for lp in sil:
        n = len(lp)
        cur = []
        for i in range(n + 1):
            a, b, c = Vector(lp[(i - 1) % n]), Vector(lp[i % n]), Vector(lp[(i + 1) % n])
            t = (c - a).normalized()
            nrm = Vector((-t.y, t.x))
            q = b + nrm * o
            if not solid(q):
                q = b - nrm * o
            if c0 <= b.x <= c1 and r0 <= b.y <= r1 and solid(q):
                cur.append(tuple(q))
            elif cur:
                lines.append(cur)
                cur = []
        if len(cur) > 1:
            lines.append(cur)
    return [ln for ln in lines if len(ln) > 3]


def hole_dist(q):
    if HOLE["loop"] is None:
        return 1e9
    q = Vector(q)
    c0, c1, r0, r1 = HOLE_BOX
    if not (c0 - LIP_W <= q.x <= c1 + LIP_W and r0 - LIP_W <= q.y <= r1 + LIP_W):
        return 1e9
    return min(seg_dist(q, a, b)[0] for a, b in HOLE["loop"])


def lip_scale(q):
    d = hole_dist(q)
    return 1.0 - LIP_K * max(0.0, 1.0 - d / LIP_W) ** 1.25
PARTS = ["none", "low", "mid", "collar", "shoulder", "drum", "dome", "shield", "bolt"]


def plate(bm, outline, height, mat, wall_mat, cw=0.6, drop=0.55, grid=1.5, creases=(), mat_fn=None,
          z0=0.0, extra_pts=(), part=None):
    """A hard armour plate. `outline` is its top-view outline in pixel-edge coords (col, row);
    `height(c, r, d)` the top height in px at a point `d` px inside the edge (before the chamfer);
    the chamfer drops `drop` px over the outer `cw` px. Walls go straight down to z0."""
    poly = [Vector(p) for p in outline]
    if area2(poly) < 0:
        poly.reverse()
    ring = densify(poly, RING)
    n = len(ring)
    pts = list(ring)
    edges = []
    # inset ring (chamfer crease)
    inset = []
    for i in range(n):
        a, b, c = ring[i - 1], ring[i], ring[(i + 1) % n]
        t1 = (b - a).normalized() if (b - a).length > 1e-9 else Vector((1, 0))
        t2 = (c - b).normalized() if (c - b).length > 1e-9 else t1
        nrm = Vector((-(t1 + t2).y, (t1 + t2).x))
        if nrm.length < 1e-6:
            nrm = Vector((-t1.y, t1.x))
        nrm.normalize()
        q = b + nrm * cw  # CCW in (col, row): left normal; checked below
        if not inside(q, poly):
            q = b - nrm * cw
        if inside(q, poly) and poly_dist(q, ring) > 0.75 * cw:
            inset.append(q)
        else:
            inset.append(None)
    start = len(pts)
    idx = []
    for q in inset:
        if q is not None:
            idx.append(len(pts))
            pts.append(q)
        else:
            idx.append(None)
    for i in range(n):
        a, b = idx[i], idx[(i + 1) % n]
        if a is not None and b is not None and (pts[a] - pts[b]).length < 2.5 * RING + 0.5:
            edges.append((a, b))
    for line in list(creases) + HOLE.get("creases", []):
        dl = densify(line, 0.8, closed=False)
        prev = None
        for q in dl:
            if inside(q, poly) and poly_dist(q, ring) > 0.6 * cw:
                pts.append(q)
                if prev is not None:
                    edges.append((prev, len(pts) - 1))
                prev = len(pts) - 1
            else:
                prev = None
    xs = [p.x for p in poly]
    ys = [p.y for p in poly]
    c = math.floor(min(xs))
    while c < max(xs):
        r = math.floor(min(ys))
        while r < max(ys):
            q = Vector((c, r))
            if inside(q, poly) and poly_dist(q, ring) > 1.2 * cw + 0.15:
                pts.append(q)
            r += grid
        c += grid
    for q in extra_pts:
        pts.append(Vector(q))
    res = geometry.delaunay_2d_cdt(pts, edges, [list(range(n))], 1, 1e-5, True)
    vco, _, faces = res[0], res[1], res[2]
    used = sorted({i for f in faces for i in f})
    vmap = {}
    for i in used:
        q = vco[i]
        d = poly_dist(q, ring)
        z = height(q.x, q.y, d) - drop * max(0.0, 1.0 - d / cw)
        z = max(z0 + 0.3, z * lip_scale(q)) if z > z0 + 0.3 else z
        vmap[i] = bm.verts.new((X(q.x), Y(q.y), z * PX))
    top = []
    for f in faces:
        try:
            face = bm.faces.new([vmap[i] for i in f])
        except ValueError:
            continue
        cx = sum(vco[i].x for i in f) / len(f)
        cy = sum(vco[i].y for i in f) / len(f)
        face.material_index = mat_fn(cx, cy) if mat_fn else mat
        if HOLE["mats"] and hole_dist((cx, cy)) < LIP_DARK:
            face.material_index = HOLE["mats"][0]
        if part is not None:  # which part a face belongs to (for the colour check only)
            face[bm.faces.layers.int["part"]] = PARTS.index(part)
        top.append(face)
    # walls + bottom
    bnd = [e for e in {e for f in top for e in f.edges} if len([g for g in e.link_faces if g in top]) == 1]
    ret = bmesh.ops.extrude_edge_only(bm, edges=bnd)
    new_v = [v for v in ret["geom"] if isinstance(v, bmesh.types.BMVert)]
    for v in new_v:
        v.co.z = z0 * PX
    for f in ret["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            f.material_index = wall_mat
            if HOLE["mats"]:
                m = f.calc_center_median()
                if hole_dist((m.x / PX + 48.0, 28 - m.y / PX)) < 0.35:
                    f.material_index = HOLE["mats"][1]
    new_e = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMEdge)
             and all(v in new_v for v in e.verts)]
    fill = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=new_e)
    for f in fill["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            f.material_index = wall_mat
    return top


def offset_line(pts, o):
    """A polyline offset `o` px to its left (in col/row terms)."""
    P = [Vector(p) for p in pts]
    out = []
    for i in range(len(P)):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        n = Vector((-t.y, t.x)).normalized()
        out.append(tuple(P[i] + n * o))
    return out


def radial_fn(outline, centre, bins=180, win=6):
    """R(theta) of a star-shaped outline about `centre` (pixel coords), circularly smoothed over
    +-`win` bins so the cap stays faired where the outline follows pixel steps."""
    C = Vector(centre)
    ring = densify(outline, 0.25)
    raw = [None] * bins
    for p in ring:
        k = int((math.atan2(p.y - C.y, p.x - C.x) + math.pi) / (2 * math.pi) * bins) % bins
        rr = (p - C).length
        raw[k] = rr if raw[k] is None else max(raw[k], rr)
    for k in range(bins):  # fill empty bins
        if raw[k] is None:
            j = 1
            while raw[(k - j) % bins] is None and raw[(k + j) % bins] is None:
                j += 1
            raw[k] = raw[(k - j) % bins] if raw[(k - j) % bins] is not None else raw[(k + j) % bins]
    sm = [sum(raw[(k + j) % bins] for j in range(-win, win + 1)) / (2 * win + 1) for k in range(bins)]

    def R(q):
        f = (math.atan2(q[1] - C.y, q[0] - C.x) + math.pi) / (2 * math.pi) * bins - 0.5
        k0 = math.floor(f)
        t = f - k0
        return sm[k0 % bins] * (1 - t) + sm[(k0 + 1) % bins] * t
    return R


def scale_about(outline, centre, inset):
    C = Vector(centre)
    out = []
    for p in outline:
        v = Vector(p) - C
        out.append(tuple(C + v * max(0.0, 1 - inset / v.length)))
    return out


def stud(bm, c, r, rad, z, h, mat, sides=8):
    """A small machined bolt head: a short faceted cylinder with a chamfered top."""
    ring0, ring1, ring2 = [], [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        ca, sa = math.cos(a), math.sin(a)
        ring0.append(bm.verts.new((X(c + rad * ca), Y(r + rad * sa), (z - 0.4) * PX)))
        ring1.append(bm.verts.new((X(c + rad * ca), Y(r + rad * sa), (z + h * 0.6) * PX)))
        ring2.append(bm.verts.new((X(c + 0.6 * rad * ca), Y(r + 0.6 * rad * sa), (z + h) * PX)))
    for k in range(sides):
        j = (k + 1) % sides
        for a, b in ((ring0, ring1), (ring1, ring2)):
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = mat
    f = bm.faces.new(ring2)
    f.material_index = mat
    f = bm.faces.new(list(reversed(ring0)))
    f.material_index = mat


# ---------------------------------------------------------------------------------------- silhouette

SMOOTH = 10  # Taubin passes on the traced pixel boundary


def silhouette_loops(offset=0.15):
    """The sprite's inner mask (tools/sprite_mask.py: opaque minus the ink ring), traced as closed
    pixel-edge loops, smoothed (Taubin) and pushed `offset` px outward so every inner pixel is more
    than half covered and the ink ring less than half. Each side is traced from its own pixels, so
    the sprite's few asymmetric ink notches are followed (the plates are mirrored, the edge is not)."""
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as sm
    idx = [[-1] * 96 for _ in range(56)]
    colors = {}
    for e, (ox, oy) in zip(PIECES, [(0, 28), (24, 28), (48, 28), (72, 28), (0, 0), (24, 0), (48, 0), (72, 0)]):
        d = common.load_sprite(WT, e)
        colors.update({int(k): tuple(v) for k, v in d["colors"].items()})
        for y, row in enumerate(d["frames"][0]["pixels"]):
            for x, v in enumerate(row.split() if isinstance(row, str) else row):
                idx[oy + y][ox + x] = int(v)
    m = sm.masks(idx, colors)["inner"]
    H, W = len(m), len(m[0])
    on = lambda r, c: 0 <= r < H and 0 <= c < W and m[r][c]  # noqa: E731
    # directed boundary edges, inside on the left in (col, row-down) screen terms
    nxt = {}
    for r in range(H):
        for c in range(W):
            if not m[r][c]:
                continue
            if not on(r - 1, c):
                nxt.setdefault((c + 1, r), []).append((c, r))
            if not on(r + 1, c):
                nxt.setdefault((c, r + 1), []).append((c + 1, r + 1))
            if not on(r, c - 1):
                nxt.setdefault((c, r), []).append((c, r + 1))
            if not on(r, c + 1):
                nxt.setdefault((c + 1, r + 1), []).append((c + 1, r))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        cur = start
        prev_dir = None
        while True:
            outs = nxt[cur]
            if len(outs) > 1 and prev_dir is not None:  # pinch: keep to one side
                outs.sort(key=lambda q: ((q[0] - cur[0]) * prev_dir[1] - (q[1] - cur[1]) * prev_dir[0]))
            q = outs.pop(0)
            if not outs:
                del nxt[cur]
            prev_dir = (q[0] - cur[0], q[1] - cur[1])
            cur = q
            if cur == start and start not in nxt:
                break
            if cur == start:
                break
            loop.append(cur)
        if len(loop) >= 8:
            loops.append(loop)
    out = []
    for loop in loops:
        pts = [Vector(p) for p in loop]
        n = len(pts)
        for lam in (0.5, -0.53) * SMOOTH:
            pts = [pts[i] + lam * ((pts[i - 1] + pts[(i + 1) % n]) * 0.5 - pts[i]) for i in range(n)]
        sgn = 1 if area2(pts) > 0 else -1
        off = []
        for i in range(n):
            t = pts[(i + 1) % n] - pts[i - 1]
            nrm = Vector((t.y, -t.x)).normalized() * sgn  # outward
            off.append(pts[i] + nrm * offset)
        if abs(area2(off)) > 20:
            out.append(off)
    return out


def loops_of(tris, vco):
    """Boundary loops of a set of triangles (index triples into vco)."""
    directed = set()
    for f in tris:
        for i in range(len(f)):
            directed.add((f[i], f[(i + 1) % len(f)]))
    nxt = {}
    for a, b in directed:
        if (b, a) not in directed:
            nxt.setdefault(a, []).append(b)
    loops = []
    while nxt:
        s = next(iter(nxt))
        loop = [s]
        cur = s
        while True:
            b = nxt[cur].pop()
            if not nxt[cur]:
                del nxt[cur]
            if b == s:
                break
            loop.append(b)
            cur = b
            if cur not in nxt:
                break
        if len(loop) >= 3:
            loops.append([Vector(vco[i]) for i in loop])
    return loops


def clip(poly, sil):
    """poly ∩ silhouette, as outline loops (CDT with face membership)."""
    pts, faces = [], []
    for loop in [poly] + sil:
        loop = [Vector(p) for p in loop]
        if area2(loop) < 0:
            loop.reverse()
        faces.append(list(range(len(pts), len(pts) + len(loop))))
        pts.extend(loop)
    vco, _, tris, _, _, forig = geometry.delaunay_2d_cdt(pts, [], faces, 0, 1e-5, True)
    keep = [t for t, o in zip(tris, forig) if 0 in o and any(k > 0 for k in o)]
    loops = loops_of(keep, vco)
    # drop collinear/near-duplicate points
    res = []
    for lp in loops:
        q = [lp[0]]
        for p in lp[1:]:
            if (p - q[-1]).length > 0.08:
                q.append(p)
        if len(q) >= 3 and abs(area2(q)) > 0.6:
            res.append(q)
    return res


# ---------------------------------------------------------------------------------------- shapes

# Left half outlines (pixel edges). Edges that face the outside run past the silhouette and are cut
# to it (clip); edges inside the object are where one plate tucks under the next.
LOW = [(10, 55), (10.4, 50), (11.2, 46), (11.6, 42), (12.4, 40), (16, 38.4), (22, 37.4), (29, 38.5),
       (30.5, 46), (26, 49), (17, 49.4), (14, 51), (12, 54)]
MID = [(3, 50), (3, 45), (3, 41), (3.8, 38), (5, 35.4), (6.4, 33.2), (7.6, 31.2), (9, 29.8), (12, 28.4),
       (16, 27.6), (22, 27.4), (28, 28), (29, 36), (26, 39.5), (20, 38.6), (14, 40.3), (9.2, 40.8),
       (7.6, 42.4), (6.2, 44), (5.2, 46.5), (4.6, 50)]
COLLAR = [(0, 36), (0, 30), (0, 20.5), (1.5, 18.2), (3.2, 16.4), (5.4, 14.2), (9, 11.6), (10.4, 15.6),
          (12.4, 18.8), (16, 19.4), (21, 19.2), (25.6, 19.6), (28.6, 21.6), (30.6, 24.6), (31.6, 27.4),
          (31, 28.4), (22, 28.3), (16, 28.8), (12, 29.4), (9, 30.2), (7, 30.6), (5, 31.2), (3.2, 32.6), (2, 35)]
SHOULDER = [(25, 28.4), (28.5, 27.2), (31.5, 26.0), (35, 25.2), (39, 25.0), (42.2, 26.4), (44.2, 29.2),
            (45.4, 32.4), (45.6, 34.6), (44, 37), (40.4, 39.2), (36, 41.2), (29.5, 41.6), (26.2, 40.2), (25, 37),
            (24.6, 32)]
DOME = [(20, 3), (26.5, 2.8), (33, 3), (36, 4), (38.2, 5.6), (39.8, 7.4), (41, 10), (41.8, 13.5),
        (43, 17.5), (43.6, 21), (42.6, 24.6), (39.5, 26.4), (35.5, 26.2), (31.5, 25), (27.5, 23.4),
        (23, 22.2), (18, 21.8), (13.4, 21.2), (10.4, 19.6), (8.6, 16.2), (8.2, 13), (9.2, 10.6), (11, 8.6),
        (13.2, 6.6), (15.6, 4.8), (17.8, 3.6)]
DOME_C = (26.0, 14.0)
DOME_Z0, DOME_H = 2.2, 13.5  # drum ring height, cap rise (px)
SHIELD_L = [(48.5, 33.0), (44, 33.6), (38, 35.2), (30, 37.5), (25.2, 40.5), (24.6, 45), (24.6, 49), (25.6, 50.6),
            (26.6, 51.6), (28.6, 52.6), (31.6, 53.6), (34.6, 54.6), (37.6, 55.6), (41.5, 57)]
SHIELD = SHIELD_L + [(2 * AXIS - c, r) for c, r in reversed(SHIELD_L[1:])]
# crease of the collar: inner lit face | outer dark flange (the bright diagonal of the sprite)
COLLAR_RIDGE = [(0.6, 36.0), (2.6, 31.6), (12.6, 21.4), (16.5, 18.6)]


def materials(sprite):
    tag = "n9_197a"

    def pal(i, metallic, roughness, spec=None):
        m = common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness)
        if spec is not None:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    spec = [  # key, palette index, metallic, roughness, specular level
        ("dome", 6, 0.55, 0.22, 0.8),
        ("drum", 4, 0.5, 0.45, None),
        ("collar", 5, 0.5, 0.42, 0.6),
        ("flange", 3, 0.45, 0.5, None),
        ("mid", 5, 0.5, 0.42, 0.6),
        ("low", 5, 0.5, 0.44, 0.6),
        ("shoulder", 7, 0.5, 0.38, 0.6),
        ("shield", 5, 0.5, 0.4, 0.6),
        ("wall", 4, 0.45, 0.5, None),
        ("bolt", 7, 0.6, 0.35, None),
        ("lip", 2, 0.45, 0.6, 0.4),
        ("pit", 1, 0.3, 0.7, 0.3),
    ]
    mats, M, seen = [], {}, {}
    for key, i, met, rough, sp in spec:
        sig = (i, met, rough, sp)
        if sig not in seen:
            seen[sig] = len(mats)
            mats.append(pal(i, met, rough, sp))
        M[key] = seen[sig]
    return mats, M


def cplate(bm, sil, poly, height, *a, creases=(), mat_fn=None, **kw):
    for loop in clip(poly, sil):
        plate(bm, loop, height, *a, creases=creases, mat_fn=mat_fn, **kw)


def build_side(bm, M, sil, s, detail):
    """One side: s = +1 left as drawn, -1 mirrored to the right (heights read in left coords)."""
    T = (lambda c: c) if s > 0 else (lambda c: 2 * AXIS - c)  # noqa: E731
    tp = lambda pts: [(T(c), r) for c, r in pts]  # noqa: E731
    L = lambda f: (lambda c, r, d: f(T(c), r, d))  # noqa: E731
    # Lowest scale: low, sloping down to its claw at the front corner.
    A1 = Vector((27, 42))
    cplate(bm, sil, tp(LOW), L(lambda c, r, d: 1.6 + 1.6 * min(1, max(0, 1 - (Vector((c, r)) - A1).length / 18))
                               + 1.1 * (1 - math.exp(-d / 2.2))), M["low"], M["wall"], cw=0.85, drop=0.75, part="low")
    # Middle scale.
    A2 = Vector((25, 32))
    cplate(bm, sil, tp(MID), L(lambda c, r, d: 2.4 + 2.2 * min(1, max(0, 1 - (Vector((c, r)) - A2).length / 22))
                               + 1.2 * (1 - math.exp(-d / 2.4))), M["mid"], M["wall"], cw=0.85, drop=0.75, part="mid")
    # Collar: a folded plate; inner face rises toward the dome, outer flange turns down.
    ridge = Line(COLLAR_RIDGE)
    zr = pchip([0.0, 0.35, 1.0], [3.0, 5.2, 7.6])
    A3 = Vector((36, 25))

    def collar_h(c, r, d):
        dist, sp, side = ridge.project((c, r))
        z_ridge = zr(sp)
        if side < 0:  # outer flange (left/up of the crease), turning down
            return max(1.8, z_ridge - 0.62 * dist)
        k = min(1, max(0, 1 - (Vector((c, r)) - A3).length / 30))
        ramp = min(1.0, dist / 2.5)  # extras fade in from the crease so it stays continuous
        return z_ridge + 0.18 * dist + ramp * (1.0 * k + 0.6 * (1 - math.exp(-d / 2.0)))

    def collar_m(c, r):
        return M["flange"] if ridge.project((T(c), r))[2] < 0 else M["collar"]
    cplate(bm, sil, tp(COLLAR), L(collar_h), M["collar"], M["wall"], cw=0.8, drop=0.7,
           creases=[tp(COLLAR_RIDGE)], mat_fn=collar_m, grid=1.3, part="collar")
    # Shoulder plate beside the dome's foot: a crowned tile with a broad chamfer.
    cplate(bm, sil, tp(SHOULDER), L(lambda c, r, d: 7.4 + 1.4 * (1 - math.exp(-d / 2.6)) - 0.05 * (r - 28)),
           M["shoulder"], M["wall"], cw=0.9, drop=1.0, part="shoulder")
    # Dome: a low drum, then the glossy cap set back 0.8 px (the ledge reads as its base ring).
    drum = clip(tp(DOME), sil)
    for loop in drum:
        plate(bm, loop, lambda c, r, d: DOME_Z0, M["drum"], M["drum"], cw=0.45, drop=0.3, grid=2.5, part="drum")
    C = Vector((T(DOME_C[0]), DOME_C[1]))
    big = max(drum, key=lambda lp: abs(area2(lp)))
    R0 = radial_fn(big, C)
    cap = []
    for k in range(144):  # the cap's edge: the drum's smoothed radius, set in 0.8 px
        a = 2 * math.pi * k / 144
        dvec = Vector((math.cos(a), math.sin(a)))
        cap.append(C + dvec * (R0(C + dvec) - 0.8))
    R = radial_fn(cap, C, win=1)

    def dome_h(c, r, d):
        sr = min(1.0, (Vector((c, r)) - C).length / max(R((c, r)), 1e-6))
        return DOME_Z0 + DOME_H * (1 - sr ** 2.2) ** (1 / 2.2)
    plate(bm, cap, dome_h, M["dome"], M["drum"], cw=0.01, drop=0.0, grid=1.0, part="dome")
    if detail:
        for c, r in ((28.0, 30.4), (33.0, 29.8), (38.0, 30.2), (27.5, 37.6), (33, 39.0)):
            stud(bm, T(c), r, 0.45, 8.6, 0.55, M["bolt"])
        for c, r in ((14, 26.5), (19, 26.2), (24, 26.4)):
            stud(bm, T(c), r, 0.42, collar_h(c, r, 3) - 0.1, 0.5, M["bolt"])


def build(coll, sprite, detail=True, name=NAME, sil=None):
    mats, M = materials(sprite)
    sil = sil or silhouette_loops()
    HOLE["loop"] = hole_segments(sil)
    assert len(HOLE["loop"]) > 20, "hole edge not found"
    HOLE["mats"] = (M["lip"], M["pit"])
    HOLE["creases"] = hole_creases(sil, LIP_DARK)
    bm = bmesh.new()
    bm.faces.layers.int.new("part")
    build_side(bm, M, sil, 1, detail)
    build_side(bm, M, sil, -1, detail)

    # Front shield: high at its back edge, crowned across, falling away to the front.
    # Panel seams (modelled V grooves): one across under the lit back edge, two down to the front.
    arc = [(c, 41.2 + 0.011 * (c - AXIS) ** 2) for c in [27.5 + 1.5 * i for i in range(29)]]
    downs = [[(AXIS - 8.5, 41.2 + 0.011 * 8.5 ** 2), (AXIS - 9.6, 57)],
             [(AXIS + 8.5, 41.2 + 0.011 * 8.5 ** 2), (AXIS + 9.6, 57)]]
    seams = [Line(arc)] + [Line(dn) for dn in downs] if detail else []
    GW, GD = 0.55, 0.45  # groove half width, depth (px)

    def shield_h(c, r, d):
        u = (c - AXIS) / 23.0
        v = max(0.0, (r - 34) / 22.0)
        z = 7.4 - 4.2 * v ** 1.3 - 1.6 * min(1, abs(u)) ** 2 + 0.8 * (1 - math.exp(-d / 2.5))
        for ln in seams:
            g = ln.project((c, r))[0]
            if g < GW:
                z -= GD * (1 - g / GW)
        return z
    creases = []
    if detail:
        for ln in [arc] + downs:
            creases += [ln, offset_line(ln, GW), offset_line(ln, -GW)]
    cplate(bm, sil, SHIELD, shield_h, M["shield"], M["wall"], cw=0.75, drop=0.7, grid=1.6, creases=creases, part="shield")
    if detail:
        for c in (38.5, 43.0, 54.0, 58.5):
            r = 37.6 + 0.02 * (c - AXIS) ** 2
            stud(bm, c, r, 0.42, shield_h(c, r, 3) - 0.1, 0.5, M["bolt"])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only).
    Copied from newshv-10.py (D185)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)),
                                  Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def seam_normals(piece, whole, x0, y0):
    """Give a cut piece the whole object's corner normals (custom normals) on every face it shares
    with it, so the shading runs on across the piece seams instead of each piece's edge normals
    leaning away from the cut.

    The filled cut faces (caps) take the material and normal of the top surface just inside the cut,
    straight above each corner. A piece is normally drawn level with its neighbours and its caps are
    buried, but the renderer raises a later draw over the earlier models it overlaps (D181), along its
    camera ray: newsh9-165 is raised over the right gun works (newsh9-258) and newsh9-159 over the left
    one, which brings their caps in front of the neighbour piece, where a plain wall-coloured cap read
    as a tall dark slab over the dome (E4 QA M1). Shaded as the surface it stands in for, the cap
    reads as that surface."""
    from mathutils.bvhtree import BVHTree
    wm = whole.data
    tree = BVHTree.FromPolygons([v.co for v in wm.vertices], [p.vertices[:] for p in wm.polygons])
    cn = wm.corner_normals
    pm = piece.data
    off = Vector((x0, y0, 0))
    out = [None] * len(pm.loops)

    def blend(idx, pv):
        wf = wm.polygons[idx]
        wl = list(wf.loop_indices)
        if len(wl) == 3:  # blend the corner normals at the point (bisect makes new points on the cut)
            a, b, c3 = (wm.vertices[wm.loops[k].vertex_index].co for k in wl)
            w = geometry.barycentric_transform(pv, a, b, c3, Vector((1, 0, 0)), Vector((0, 1, 0)),
                                               Vector((0, 0, 1)))
            return sum((cn[k].vector * max(0.0, w[j]) for j, k in enumerate(wl)), Vector()).normalized()
        best = min(wl, key=lambda k: (wm.vertices[wm.loops[k].vertex_index].co - pv).length)
        return cn[best].vector.copy()

    def top_hit(pv, n):
        q = pv - Vector((n.x, n.y, 0)).normalized() * 0.02  # just inside the cut
        hit = tree.ray_cast(Vector((q.x, q.y, 5.0)), Vector((0, 0, -1)))
        return (hit[2], hit[0]) if hit[0] is not None else (None, None)

    for f in pm.polygons:
        c = f.center + off
        loc, nrm, idx, dist = tree.find_nearest(c)
        ok = idx is not None and dist < 1e-4 and nrm.dot(f.normal) > 0.98
        cap = not ok and abs(f.normal.z) < 0.6
        if cap:
            hi, _ = top_hit(c, f.normal)
            if hi is not None:
                f.material_index = wm.polygons[hi].material_index
        for li in f.loop_indices:
            pv = pm.vertices[pm.loops[li].vertex_index].co + off
            if cap:
                hi, hp = top_hit(pv, f.normal)
                out[li] = blend(hi, hp) if hi is not None else f.normal.copy()
            elif not ok:
                out[li] = f.normal.copy()
            else:
                out[li] = blend(idx, pv)
    pm.normals_split_custom_set(out)


# The game camera (D61 tilted, 16:9) in assembly coordinates (col, row, height in px). DREAD-NOT's
# hull holds still on screen for the whole fight (assembly origin, col 48 row 28, at game_screen
# (231, 127)); the camera is at world (0, 19.47, 5.96) (tyrianHarness.view.camera), i.e. over game
# pixel (156, 163.5) and 233.6 px up. A piece model is placed as a scaled copy about the camera
# (D6, D181), so in its own coordinates the camera is always here, raised or not.
CAM = (-27.0, 64.5, 233.6)


def cut_planes(x0, y0):
    """A piece's four cut planes (co, outward normal) in Blender units. The cuts inside the assembly
    are slanted to contain the game camera: from it the cap of a cut is seen edge on, so a piece the
    renderer raises over its neighbours (D181: newsh9-165 over the right gun works, newsh9-159 over
    the left) shows no cap wall where its neighbour's surface should be (E4 QA M1: the "tall dark
    slab" over the right dome was newsh9-165's cap). The assembly's outer edges stay vertical."""
    hw, hh = 12 / 12, 14 / 12
    C = Vector((X(CAM[0]), Y(CAM[1]), CAM[2] * PX))
    xa, xb, ya, yb = X(0), X(96), Y(56), Y(0)
    out = []
    for xe, sgn in ((x0 - hw, -1), (x0 + hw, 1)):
        if xa + 1e-4 < xe < xb - 1e-4:
            out.append(((xe, 0, 0), Vector((C.z, 0, -(C.x - xe))).normalized() * sgn))
        else:
            out.append(((xe, 0, 0), Vector((sgn, 0, 0))))
    for ye, sgn in ((y0 - hh, -1), (y0 + hh, 1)):
        if ya + 1e-4 < ye < yb - 1e-4:
            out.append(((0, ye, 0), Vector((0, C.z, -(C.y - ye))).normalized() * sgn))
        else:
            out.append(((0, ye, 0), Vector((0, sgn, 0))))
    return out, C


def split_pieces(obj, layout):
    """common.split_assembly with cut_planes, each cut closed by strips hung from the cut's top edges
    down to the deck (z = 0) along the camera's rays instead of one filled n-gon per plate (no fan of
    long thin triangles; seam_normals shades them as the surface above)."""
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        planes, C = cut_planes(x0, y0)
        for co, no in planes:
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        eps = 1e-5

        def ground(v):  # where the camera ray through v meets the deck
            return v + (v - C) * (v.z / (C.z - v.z))
        for e in [e for e in bm.edges if len(e.link_faces) == 1]:
            a, b = e.verts
            if a.co.z < eps or b.co.z < eps:
                continue
            nrm = None
            for co, no in planes:
                if abs(no.dot(a.co - Vector(co))) < 1e-4 and abs(no.dot(b.co - Vector(co))) < 1e-4:
                    nrm = no
            if nrm is None:
                continue
            a0 = bm.verts.new(ground(a.co))
            b0 = bm.verts.new(ground(b.co))
            f = bm.faces.new((a, b, b0, a0))
            f.material_index = e.link_faces[0].material_index
            f.normal_update()
            if f.normal.dot(nrm) < 0:
                f.normal_flip()
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def split_open(obj, layout, coll):
    """Cut an outline shell into the pieces without filling the cuts (no outline along the seams).
    Copied from assembly-newsh2-123.py; here each piece also keeps the whole shell's vertex normals
    (custom normals), so the game's inverted hull, pushed along them, closes across the seams instead
    of opening a black crack where a cut piece's own normals would lean."""
    from mathutils.kdtree import KDTree
    mw = obj.matrix_world
    kd = KDTree(len(obj.data.vertices))
    for v in obj.data.vertices:
        kd.insert(mw @ v.co, v.index)
    kd.balance()
    wn = [(mw.to_3x3() @ v.normal).normalized() for v in obj.data.vertices]
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in cut_planes(x0, y0)[0]:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        for k in obj.keys():  # tyrian_outline and any other node extras
            sh[k] = obj[k]
        for poly in me.polygons:
            poly.use_smooth = True
        nrm = []
        for v in me.vertices:
            near = kd.find_n(Vector((v.co.x + x0, v.co.y + y0, v.co.z)), 2)
            n = sum((wn[i] * (1 / (d + 1e-5)) for _, i, d in near), Vector())
            nrm.append(n.normalized())
        me.normals_split_custom_set_from_vertices(nrm)
        out[name] = sh
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    obj = build(coll, sprite)
    pieces = split_pieces(obj, layout)
    for name, cx, cy in layout:
        p = pieces[name]
        for poly in p.data.polygons:
            poly.use_smooth = True
        p.data.set_sharp_from_angle(angle=math.radians(32))
        seam_normals(p, obj, cx / 12, -cy / 12)
    # Outline shell (D51) from a sealed copy without the bolts and seams, made once for the whole
    # object and cut into the pieces without filling the cuts, so no ink runs along the piece seams;
    # every outer island is kept (D189) and the shell is held under the top surface (D90/D118).
    plain = build(coll, sprite, detail=False, name=NAME + "_plain")
    bpy.context.view_layer.update()
    shell = common.outline_shell(plain, coll, voxel=0.02, faces=9000, inside=0.012, islands="outer")
    sink_shell(shell, plain, margin=0.03, reach=0.09)
    shells = split_open(shell, layout, coll)
    for name, sh in shells.items():
        print("SHELL", name, len(sh.data.vertices), "verts")
        assert len(sh.data.polygons) > 0, f"{name}_outline has no mesh"
    bpy.data.objects.remove(plain, do_unlink=True)
    bpy.data.objects.remove(shell, do_unlink=True)
    for name, _, _ in layout:  # piece-local: each piece's centre at the origin
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    for name, cx, cy in layout:
        pieces[name].location = shells[name].location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    tris = sum(sum(len(p.vertices) - 2 for p in pieces[n].data.polygons) for n, _, _ in layout)
    print("TRIS", tris)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        common.render_preview([pieces[n] for n, _, _ in layout] + [shells[n] for n, _, _ in layout],
                              str(out), None, size=(96, 56), view_px=640)


if __name__ == "__main__":
    main()
