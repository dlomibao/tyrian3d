"""Flying ear, lobe at the bottom right (newsh5.shp frame 284); mirrored, newsh5-245 (the two sprites are pixel-for-pixel mirrors, so one builder makes both).

What it is: a human outer ear (auricle) flying loose, seen from its outer side. EYESPY (4.13).
The sprite reads: a rolled rim (helix) round the top and the back (left), dipping where its crus
dives into the concha on the face side (right, rows 9-12); the tragus on the right edge (rows
13-19, lit); the dark concha bowl inside it (cols 13-16); the Y-shaped antihelix (lit ridge, cols
9-12) rising from the antitragus knob over the lobe and forking into the upper and lower crura under
the top rim; the scapha groove between the helix and the antihelix and the fossa triangularis
between the crura (dark); a fleshy domed lobe at the bottom. Its darker hollows, lit ridges and
ink ring are drawn lighting: in game the relief and the light make them.

Built as one closed, smooth-shaded surface over the sprite's inner outline (the ink ring left to
the game's outline): the front is a height field (rolled rim, a quarter-ellipse side that is
vertical at the outline, rounding over to the crest; inside it a floor with smooth bowls cut in
and the antihelix, lobe, tragus and antitragus as smooth swellings blended in, no seams), the back
rolls under from the outline the same way to a flat-ish back (a plausible closed shape only).
Skin is matte, non-metallic flesh in the sprite's own mid-tans by region (skin / hollow / concha
floor), with a little sheen.

Run: blender --background --python assets/blender/enemies/newsh5-284.py
newsh5-245.py imports build_model() from here and exports the mirror (this script exports only 284).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy  # noqa: F401
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402

ROOT = common.repo_root(__file__)
SRC = "newsh5-284"  # feature positions are this sprite's; the mirror flips the result
NAME = SRC
MIRROR = False

# ---- shape, sprite px (1/12 unit); u right, v down, pixel-corner coordinates of newsh5-284 ----
Z0 = 2.2          # the outline's height; the side is vertical here (front rolls up, back rolls under)
RIM_TOP = 7.4     # helix crest
RIM_AT = 1.9      # the crest's distance in from the outline (more at the top right: RIM_WIDE)
RIM_FALL = 1.7    # the rim's inner shoulder falls to the floor over this
FLOOR = 4.6       # floor of the hollow inside the rim
SEAL_TOP, SEAL_LOBE = 5.6, 4.6  # the shell proxy lens
BACK_IN = 3.2     # the back rolls under over this distance in from the outline
BACK_Z = 0.0      # the back's level
OUTLINE_SIGMA = 0.9  # px: gaussian that rounds the traced outline
OUTLINE_LEVEL = 0.42  # the blurred mask's level the outline follows (< 0.5 pushes it out)
TOP_STEP = 0.62
TOP_RINGS = [0.07, 0.25, 0.5, 0.85, 1.3, 1.85, 2.45, 3.1, 3.8, 4.5]
BACK_RINGS = [0.1, 0.4, 0.9, 1.6, 2.4, 3.2]
BACK_STEP = 1.6


def P(c, r):
    """Sprite pixel centre (column, row) in pixel-corner coordinates."""
    return (c + 0.5, r + 0.5)


# Crest dips, (centre, rx, ry, drop px): the helix crus diving into the concha on the face side,
# and the intertragic notch between the tragus and the lobe.
CREST_DIPS = [
    (P(17.4, 10.8), 2.4, 3.2, 1.9),
    (P(18.9, 20.2), 1.8, 1.6, 2.0),
]
LOBE_ROWS = (17.5, 22.5)   # the crest settles from RIM_TOP to the lobe's height over these rows
LOBE_CREST = 3.6
LOBE = (P(14.5, 21.9), 5.2, 4.8, 6.3)   # (centre, rx, ry, top) the fleshy lobe dome
TRAGUS = (P(18.2, 15.8), 1.9, 3.0, 7.0)  # the flap over the concha on the face side
ANTITRAGUS = (P(14.6, 18.9), 1.7, 1.4, 6.9)
# Bowls cut into the floor (centre, rx, ry, tilt, depth): concha (with the ear canal's pit under
# the tragus), its upper part (cymba), the fossa triangularis between the crura, the scapha groove
# under the top rim and down the back rim.
BASINS = [
    (P(14.9, 13.0), 2.3, 4.8, 0.08, 2.9),
    (P(16.0, 15.4), 1.2, 1.6, 0.0, 1.0),
    (P(15.4, 9.0), 1.4, 1.2, 0.0, 1.4),
    (P(12.6, 7.7), 1.7, 1.1, 0.4, 2.3),
    (P(10.0, 6.2), 3.5, 1.5, 0.06, 2.5),
    (P(6.8, 9.6), 1.05, 3.2, 0.12, 1.5),
]
BASIN_MAX = 3.4
# The antihelix: polylines (column, row, height over the floor, half width px). The stem rises
# from the antitragus over the concha's back wall to the fork; the upper crus runs up under the
# top rim, the lower crus right toward the helix crus.
ANTIHELIX = [
    [(14.0, 18.5, 1.8, 1.5), (12.9, 16.8, 2.3, 1.5), (11.9, 14.5, 2.5, 1.45), (11.2, 12.4, 2.5, 1.4),
     (10.5, 10.5, 2.4, 1.3), (10.1, 8.6, 2.0, 1.1), (9.9, 7.2, 1.2, 0.9), (9.7, 6.4, 0.4, 0.7)],
    [(10.7, 10.4, 2.2, 1.1), (12.2, 9.8, 1.8, 0.95), (13.4, 9.4, 1.2, 0.8), (14.4, 9.1, 0.4, 0.65)],
]
# The helix is broad where it comes down the top right (the sprite's bright band, cols 13-17,
# rows 4-8): the crest's distance in from the outline grows there.
RIM_WIDE = (P(15.6, 5.8), 3.6, 3.4, 1.3)

# Skin: matte flesh by region in the sprite's own indices (region medians, the ink ring and the
# brightest / darkest shading excluded): rim, antihelix, tragus and lobe 25; the scapha / fossa
# floor 23; the concha floor 22.
SHADES = [25, 23, 21, 20]   # skin; scapha and bowl walls; concha and fossa floor; the concha's core
LEVELS = [0.35, 0.95, 1.9]    # the bowls' depth (px, kept off the rim and lobe) where each shade starts
METALLIC, ROUGHNESS = 0.0, 0.62


# ---- maths helpers (copied, not shared) ----
def seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy), t


def ellipse_u(p, c, rx, ry, tilt=0.0):
    dx, dy = p[0] - c[0], p[1] - c[1]
    ct, st = math.cos(tilt), math.sin(tilt)
    ex, ey = dx * ct + dy * st, -dx * st + dy * ct
    return (ex / rx) ** 2 + (ey / ry) ** 2


def smax(a, b, k):
    h = max(0.0, min(1.0, 0.5 + 0.5 * (a - b) / k))
    return b + (a - b) * h + k * h * (1 - h) * 0.5


def smin(a, b, k):
    return -smax(-a, -b, k)


def sstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def inside(poly, p):
    x, y, res = p[0], p[1], False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[i - 1]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            res = not res
    return res


def poly_dist(poly, p):
    return min(seg_dist(p, poly[i], poly[i - 1])[0] for i in range(len(poly)))


def resample(poly, step):
    segs = [(Vector(poly[i]), Vector(poly[(i + 1) % len(poly)])) for i in range(len(poly))]
    total = sum((b - a).length for a, b in segs)
    n = max(8, round(total / step))
    out, i, walked = [], 0, 0.0
    for k in range(n):
        target = total * k / n
        while walked + (segs[i][1] - segs[i][0]).length < target:
            walked += (segs[i][1] - segs[i][0]).length
            i += 1
        a, b = segs[i]
        ln = (b - a).length or 1
        out.append(tuple(a.lerp(b, (target - walked) / ln)))
    return out


def trace(mask):
    """The boundary of a pixel mask (rows of bools) as a closed loop of pixel corners."""
    h, w = len(mask), len(mask[0])
    ins = lambda c, r: 0 <= r < h and 0 <= c < w and mask[r][c]  # noqa: E731
    edges = {}
    for r in range(h):
        for c in range(w):
            if not ins(c, r):
                continue
            if not ins(c, r - 1):
                edges[(c, r)] = (c + 1, r)
            if not ins(c + 1, r):
                edges[(c + 1, r)] = (c + 1, r + 1)
            if not ins(c, r + 1):
                edges[(c + 1, r + 1)] = (c, r + 1)
            if not ins(c - 1, r):
                edges[(c, r + 1)] = (c, r)
    start = min(edges)
    loop, p = [], start
    while True:
        loop.append(p)
        p = edges[p]
        if p == start:
            break
    return loop


def smooth_ring(poly, passes, push):
    pts = [Vector(p) for p in poly]
    n = len(pts)
    for _ in range(passes):
        pts = [(pts[i - 2] + pts[i - 1] + pts[i] + pts[(i + 1) % n] + pts[(i + 2) % n]) / 5 for i in range(n)]
    ring = [tuple(p) for p in pts]
    out = []
    for i, p in enumerate(pts):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        nrm = Vector((-t.y, t.x))
        if inside(ring, tuple(p + nrm * 0.05)):
            nrm = -nrm
        out.append(tuple(p + nrm * push))
    return out


def smooth_outline(mask, loop):
    """The 0.5 level of the mask blurred by a gaussian (OUTLINE_SIGMA px), lowered to OUTLINE_LEVEL so
    the smoothed outline still covers the pixels: a round outline with no pixel stair steps. Found
    by searching along each traced point's normal, then resampled evenly."""
    pix = [(c, r) for r in range(len(mask)) for c in range(len(mask[0])) if mask[r][c]]
    s2 = OUTLINE_SIGMA * math.sqrt(2)
    cdf = lambda x: 0.5 * (1 + math.erf(x / s2))  # noqa: E731

    def field(u, v):
        return sum((cdf(u - c) - cdf(u - c - 1)) * (cdf(v - r) - cdf(v - r - 1))
                   for c, r in pix if abs(u - c - 0.5) < 4 and abs(v - r - 0.5) < 4)

    pts = smooth_ring(resample(loop, 0.5), 4, 0.0)
    n = len(pts)
    out = []
    for i in range(n):
        t = (Vector(pts[(i + 1) % n]) - Vector(pts[i - 1])).normalized()
        nrm = Vector((-t.y, t.x))
        if inside(pts, tuple(Vector(pts[i]) + nrm * 0.05)):
            nrm = -nrm  # outward
        lo, hi = -2.5, 2.5  # along the outward normal: field high at lo, low at hi
        for _ in range(22):
            mid = (lo + hi) / 2
            q = Vector(pts[i]) + nrm * mid
            if field(q.x, q.y) > OUTLINE_LEVEL:
                lo = mid
            else:
                hi = mid
        out.append(tuple(Vector(pts[i]) + nrm * lo))
    return resample(smooth_ring(out, 2, 0.0), 0.42)


def polyline(ctrl, rounds=3):
    pts = [Vector(p) for p in ctrl]
    for _ in range(rounds):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        out.append(pts[-1])
        pts = out
    return [tuple(p) for p in pts]


AH = [polyline([(c + 0.5, r + 0.5, hgt, w) for c, r, hgt, w in ctrl]) for ctrl in ANTIHELIX]


def ridge(p):
    """The antihelix's height over the floor at p: along each polyline the nearest point gives a
    height and half width, and the cross-section is a round-topped bell; the stem and the crura
    join with a smooth maximum, so the fork has no crease."""
    vals = []
    for path in AH:
        best, hw = 1e9, None
        for a, b in zip(path, path[1:]):
            d, t = seg_dist(p, a[:2], b[:2])
            if d < best:
                best, hw = d, (a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t)
        hgt, w = hw
        x = best / w
        vals.append(hgt * math.exp(-0.5 * x ** 2.4) if x < 3.5 else 0.0)
    out = vals[0]
    for v in vals[1:]:
        out = smax(out, v, 0.7)
    return out


def crest(p):
    top = RIM_TOP + (LOBE_CREST - RIM_TOP) * sstep((p[1] - LOBE_ROWS[0]) / (LOBE_ROWS[1] - LOBE_ROWS[0]))
    for c, rx, ry, drop in CREST_DIPS:
        u = ellipse_u(p, c, rx, ry)
        if u < 1:
            top -= drop * 0.5 * (1 + math.cos(math.pi * math.sqrt(u)))
    return top


def roll(d, reach):
    """Quarter ellipse 0..1 over 0..reach: vertical at the outline, level at reach."""
    t = min(1.0, max(0.0, d / reach))
    return math.sqrt(max(0.0, 1 - (1 - t) ** 2))


def dome(p, spec, power=0.5):
    c, rx, ry, top = spec
    u = ellipse_u(p, c, rx, ry)
    return None if u >= 1 else top * (1 - u) ** power


def rim_at(p):
    c, rx, ry, more = RIM_WIDE
    u = ellipse_u(p, c, rx, ry)
    return RIM_AT + (more * 0.5 * (1 + math.cos(math.pi * math.sqrt(u))) if u < 1 else 0.0)


def front(p, d):
    """Height (px) of the front at p, d px in from the outline. Returns (height, inner) where inner
    says the point lies in the hollow, not on the rim or a swelling."""
    top = crest(p)
    ra = rim_at(p)
    cut = 0.0
    for c, rx, ry, tilt, depth in BASINS:
        u = ellipse_u(p, c, rx, ry, tilt)
        if u < 1:
            cut += depth * 0.5 * (1 + math.cos(math.pi * math.sqrt(u)))
    cut = BASIN_MAX * math.tanh(cut / BASIN_MAX)
    rg = ridge(p)
    inner = FLOOR - cut + rg
    tu = ellipse_u(p, TRAGUS[0], TRAGUS[1] * 1.3, TRAGUS[2] * 1.2)
    for spec, k in ((TRAGUS, 0.8), (ANTITRAGUS, 0.7)):
        h = dome(p, spec, 0.7)
        if h is not None:
            inner = smax(inner, FLOOR - 0.6 + (spec[3] - FLOOR + 0.6) * (h / spec[3]), k)
    # rim: rolled outer side up to the crest, a round shoulder falling to the inside
    if d < ra:
        rim = Z0 + (top - Z0) * roll(d, ra)
    else:
        k = min(1.0, (d - ra) / RIM_FALL)
        rim = inner + (top - inner) * 0.5 * (1 + math.cos(math.pi * k))
    h = smax(rim, inner, 0.9)
    # nothing stands outside the rolled side
    h = min(h, Z0 + (max(top, TRAGUS[3]) - Z0 + 0.3) * roll(d, ra * 0.95))
    # the lobe: a soft dome taking over at the bottom, rolling down to the outline
    # (a smooth union, so it swells out of the rim and the antitragus without a crease)
    w = sstep((p[1] - 19.0) / 3.5)
    lh = dome(p, LOBE, 0.42)
    if lh is not None:
        h = smax(h, min(lh, Z0 + (LOBE[3] - Z0) * roll(d, 3.6)), 2.0)
    # the material field: the bowls' depth, kept off the rim and the lobe
    # (and the floor between the rim and the antihelix a shade down too)
    floor = 0.5 * max(0.0, 1 - rg / 1.3)
    if tu < 1:
        floor *= min(1.0, tu)
    return h, (cut + floor) * sstep((d - ra + 0.2) / 1.0) * (1 - w)


def back(d):
    return Z0 + (BACK_Z - Z0) * roll(d, BACK_IN)


def sealed(p, d):
    """The outline-shell proxy's front: a plain lens over the outline (rolled side, then level,
    lower toward the lobe, no valleys) that stays inside the model. The shell's ink then rings the
    silhouette only; built from the real front, its smoothed copy stood proud in the concha and
    the scapha and drew black lines there."""
    top = SEAL_TOP + (SEAL_LOBE - SEAL_TOP) * sstep((p[1] - 17.0) / 7.0)
    return Z0 + (top - Z0) * roll(d, 2.2), 0.0


def build(sprite, coll, proxy=False):
    pixels = [[int(x) for x in r.split()] if isinstance(r, str) else r for r in sprite["frames"][0]["pixels"]]
    h, w = len(pixels), len(pixels[0])
    # The inner mask: opaque pixels minus the ink ring (dark pixels 4-adjacent to the outside); the
    # game draws its own ink there.
    INK = {1, 16, 17}
    opaque = lambda c, r: 0 <= r < h and 0 <= c < w and pixels[r][c] >= 0  # noqa: E731
    mask = [[opaque(c, r) and not (pixels[r][c] in INK and not all(opaque(c + dc, r + dr) for dc, dr in
             ((1, 0), (-1, 0), (0, 1), (0, -1)))) for c in range(w)] for r in range(h)]
    ring = smooth_outline(mask, trace(mask))
    n = len(ring)
    normals = []
    for i in range(n):
        t = (Vector(ring[(i + 1) % n]) - Vector(ring[i - 1])).normalized()
        nrm = Vector((-t.y, t.x))
        if not inside(ring, tuple(Vector(ring[i]) + nrm * 0.05)):
            nrm = -nrm
        normals.append(nrm)

    mats = [common.palette_material(sprite, i, NAME, metallic=METALLIC, roughness=ROUGHNESS) for i in SHADES]
    bm = bmesh.new()
    sx = -1 if MIRROR else 1
    to3 = lambda u, v, z: (sx * (u - 12) / 12, (14 - v) / 12, z / 12)  # noqa: E731
    edge_verts = [bm.verts.new(to3(u, v, Z0)) for u, v in ring]

    def offset_ring(dd, every):
        out = []
        for i in range(0, n, every):
            q = Vector(ring[i]) + normals[i] * dd
            if inside(ring, tuple(q)) and abs(poly_dist(ring, tuple(q)) - dd) < 0.22:
                out.append(tuple(q))
        return out

    def fill(step, rings, interior_from, height):
        """Triangles (as lists of (vert, uv, g)) of a constrained Delaunay fill of the outline,
        lifted by height(uv, d) -> (z, g); g is the material field."""
        pts = []
        for dd in rings:
            pts += offset_ring(dd, 1 if dd < 2.0 else 2)
        v = step * 0.5
        while v < h:
            u = step * 0.5 + (step * 0.5 if int(v / step) % 2 else 0)
            while u < w:
                if inside(ring, (u, v)) and poly_dist(ring, (u, v)) > interior_from:
                    pts.append((u, v))
                u += step
            v += step
        coords = [Vector(p) for p in ring] + [Vector(p) for p in pts]
        out_v, _, out_f, orig_v, _, _ = delaunay_2d_cdt(coords, [(i, (i + 1) % n) for i in range(n)], [], 0, 1e-6)
        items = []
        for k, co in enumerate(out_v):
            src = orig_v[k][0] if orig_v[k] else None
            if src is not None and src < n:
                items.append((edge_verts[src], (co.x, co.y), 0.0))
            else:
                z, g = height((co.x, co.y), poly_dist(ring, (co.x, co.y)))
                items.append((bm.verts.new(to3(co.x, co.y, z)), (co.x, co.y), g))
        tris = []
        for f in out_f:
            cu = sum(out_v[i].x for i in f) / 3
            cv = sum(out_v[i].y for i in f) / 3
            if inside(ring, (cu, cv)):
                tris.append([items[i] for i in f])
        return tris

    cuts = {}

    def split(poly, level):
        """Clip a convex polygon of (vert, uv, g) by the material field's level: (below, above).
        Crossing points are new vertices on the real surface, shared between neighbours, so the
        colour boundary is a smooth curve, not a stair of whole triangles."""
        lo, hi = [], []
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            (lo if a[2] < level else hi).append(a)
            if (a[2] < level) != (b[2] < level):
                key = (min(id(a[0]), id(b[0])), max(id(a[0]), id(b[0])), level)
                if key not in cuts:
                    t = (level - a[2]) / (b[2] - a[2])
                    uv = (a[1][0] + (b[1][0] - a[1][0]) * t, a[1][1] + (b[1][1] - a[1][1]) * t)
                    z, _ = front(uv, poly_dist(ring, uv))
                    cuts[key] = (bm.verts.new(to3(uv[0], uv[1], z)), uv, level)
                lo.append(cuts[key])
                hi.append(cuts[key])
        return lo, hi

    def add(poly, slot, flip):
        vs = [p[0] for p in poly]
        if len(vs) < 3 or len(set(vs)) < len(vs):
            return
        f = bm.faces.new(list(reversed(vs)) if flip else vs)
        f.material_index = slot

    for tri in fill(TOP_STEP, TOP_RINGS, TOP_RINGS[-1] + 0.4, sealed if proxy else front):
        polys, rest = [], tri
        for slot, level in enumerate(LEVELS):
            below, rest = split(rest, level) if len(rest) >= 3 else ([], [])
            polys.append((below, slot))
        polys.append((rest, len(LEVELS)))
        for poly, slot in polys:
            add(poly, slot, MIRROR)
    for tri in fill(BACK_STEP, BACK_RINGS, BACK_RINGS[-1] + 0.6, lambda p, dd: (back(dd), 0.0)):
        add(tri, 0, not MIRROR)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return obj


def build_model(name, mirror):
    """Build the ear as `name` (mirrored for newsh5-245); returns [model, outline shell]."""
    global NAME, MIRROR
    NAME, MIRROR = name, mirror
    sprite = common.load_sprite(ROOT, SRC)
    coll = common.reset_collection(NAME)
    proxy = build(sprite, coll, proxy=True)
    shell = common.outline_shell(proxy, coll, voxel=0.008, faces=1400, smooth=3, inside=0.002)
    pmesh = proxy.data
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.data.meshes.remove(pmesh)
    obj = build(sprite, coll)
    assert obj.name == NAME and shell.name == f"{NAME}_outline", (obj.name, shell.name)
    assert shell.data.polygons, "outline shell has no mesh"
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    print(f"tris {tris} open_edges {open_edges} shell_faces {len(shell.data.polygons)}")
    return [obj, shell]


def main():
    objs = build_model("newsh5-284", False)
    common.export_sprite_model(ROOT, objs, "enemies/newsh5-284", common.load_sprite(ROOT, "newsh5-284")["sprites"])


if __name__ == "__main__":
    main()
