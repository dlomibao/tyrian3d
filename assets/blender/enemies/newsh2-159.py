"""Bronze pod with telescoping arms (newsh2.shp frames 159-167, 24x28 px, enemy type 4): a
hard-surface machine that is its sprite in 3D (the treatment of the player ships, PR #84 / D50-D53).

Seen in episode 1 (levels 25-41, the most common level-1 flyer), episode 2 and episode 3. Over the
five frames the arms slide out of the band one pixel a side at a time (tips at 8, 9, 10, 11 and
12 px from the centre, outline included), red-hot vanes open round them, the frames alternate a
palette step darker and lighter, and frame 159 is drawn one row higher. So each frame gets its own
model: newsh2-159 (159), newsh2-159-f2 (161) ... newsh2-159-f5 (167).

The sprite is authoritative (D52, the user's rule; tools/calibration/rubric.md):
- Plan: the ball's half width by row (PLAN) is a smooth pchip curve fitted to the sprite's mask,
  outline ring included: a squarish ball 16 px wide at rows 12-20, rounding to the rear (rows 8-9,
  where the post stands) and to a blunt front (row 24). Top-view IoU vs the mask 0.95-0.96.
- Features where the sprite has them: the post (rows 7-11, cols 10-13) in a dark channel (cols 9
  and 14, row 11), the steel band (rows 12-15) with its dark frame plate and the bright capsule head
  over it (cols 10-13), the dark bay below the band (cols 9-14, rows 16-20) with the capsule's barrel
  and muzzle ring in it, the dark rim round the bottom, the arm ends at rows 13-14, and the red-hot
  vanes above and below each arm in frames 163-167.
- Colours: each part takes the palette index the sprite uses there (the trimmed median of its
  pixels), +1 in the lighter frames (161, 165, 167) as the sprite alternates; satin metal. Bright
  sprite pixels are sheen, not modelled bumps.
- Underside: the plain closed shell, no detailing.

Hard surface: one smooth superellipsoid shell (pchip plan), its armour plates divided by real
V-grooves cut with exact booleans, a pinched groove the steel band sits in, a deep bay and a channel
cut into it, a socket at each band end the arm heads retract into; machined parts (post with lid and
rear exhaust, capsule with collars and a muzzle, rods, heads, rivets, vanes) are separate closed
solids.

Texture: no concept projection (its maps.json says "bake": "model", D50). Cycles bakes a colour
multiplier (ambient occlusion, edge lift) and a roughness/metalness map per frame model
(usp_talon.bake_maps) to assets/blender/textures/newsh2-159/bake/<model>/; Base Color = map x palette
colour, so pal_<index>, fades and the hit flash apply; the vanes keep their flat emissive colour.
Exported beside each frame model: an outline shell (common.outline_shell, D51). No engine glow: the
sprite shows no exhaust flame.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-159.py
     [-- --preview out.png] [--no-bake] [--frames 159,167] [--out x.glb]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402
import usp_talon as talon  # noqa: E402  (pchip, cbox, cull_hidden, bake_maps)

NAME = "newsh2-159"
ROOT = common.repo_root(__file__)
# The baked colour map's tint: near neutral (the Talon's cool tint turned the steel band blue).
TINT = (0.95, 0.97, 1.0)

# Per frame: sprite frame, model name, arm tip (px from centre, outline included), shade (+1
# palette step in the lighter frames), rows drawn higher, vane opening (0-1), vane palette index
# (the trimmed median of the frame's red pixels).
FRAMES = [
    (159, "newsh2-159", 8, 0, 1, 0.0, None),
    (161, "newsh2-159-f2", 9, 1, 0, 0.0, None),
    (163, "newsh2-159-f3", 10, 0, 0, 0.35, 114),
    (165, "newsh2-159-f4", 11, 1, 0, 0.75, 116),
    (167, "newsh2-159-f5", 12, 1, 0, 1.0, 116),
]

# --- the shell ------------------------------------------------------------------------------------
# Coordinates in sprite px, frame 161: x = column edge - 12 (right +), y = row (down the screen = the
# front, +), z up. Blender: X = x / 12, Y = (14 - y) / 12, Z = z / 12.

# D74: the plan goes to the INNER edge of the sprite's ink border (inner half widths by row, frame 161).
PLAN_Y = [8.02, 8.12, 8.5, 9.5, 10.5, 11.5, 12.5, 13.2, 19.0, 19.8, 20.5, 21.5, 22.5, 22.85, 23.03]
PLAN_W = [0.0, 1.5, 2.6, 3.6, 5.0, 6.0, 6.85, 7.0, 7.0, 6.7, 6.05, 4.7, 3.1, 2.1, 0.0]
BAND_W = 7.0         # the steel band's half width = the ball's widest
W = talon.pchip(PLAN_Y, PLAN_W)
Y0, Y1 = PLAN_Y[0], PLAN_Y[-1]
NEXP = 2.3           # cross-section superellipse exponent (a touch squarer than round)
KT, KB = 0.9, 0.78   # top / belly half height as a fraction of the half width
CY = 16.0            # the ball's centre row
BAND_Y0, BAND_Y1 = 11.95, 16.05  # the steel band (sprite rows 12-15)
PINCH = 1.3          # depth of the groove the band sits in
E_BELT = math.radians(-24)  # the belt seam under the armour (elevation from the centre)
SEAM_X = 4.9         # lower plates: U plate round the bay | flank plates
RIM_K = 0.8          # the rim's inner edge, as a fraction of the top-view outline radius
SIDES = 32
DISSOLVE = 2.0  # degrees: merge boolean slivers flatter than this


def spow(v, p):
    return math.copysign(abs(v) ** p, v)


def heights(w):
    return KT * w, KB * w


def section(w, ht, hb, n=SIDES, phase=0.5):
    e = 2 / NEXP
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + phase) / n
        c, s = math.cos(a), math.sin(a)
        pts.append((w * spow(c, e), (ht if s >= 0 else hb) * spow(s, e)))
    return pts


def DX(y):
    """The crown leans half a pixel left like the sprite's (rows 7-9 span x -4..3)."""
    t = min(1.0, max(0.0, (10.2 - y) / 1.8))
    return -0.45 * t * t * (3 - 2 * t)


def inside(x, y, z):
    if not (Y0 < y < Y1):
        return False
    x -= DX(y)
    w = W(y)
    if w <= 1e-4:
        return False
    ht, hb = heights(w)
    h = ht if z >= 0 else hb
    return abs(x / w) ** NEXP + abs(z / h) ** NEXP <= 1.0


def top(x, y):
    """Height of the (unpinched) shell over top-view point (x, y)."""
    x -= DX(y)
    w = W(y)
    if w <= 1e-4 or abs(x) >= w:
        return 0.0
    return KT * w * (1 - abs(x / w) ** NEXP) ** (1 / NEXP)


def top_normal(x, y):
    e = 0.02
    fx = (top(x + e, y) - top(x - e, y)) / (2 * e)
    fy = (top(x, y + e) - top(x, y - e)) / (2 * e)
    return Vector((-fx, -fy, 1.0)).normalized()


def on_dir(theta, elev, cz=0.0):
    """Shell point along a direction from the centre (0, CY, cz): theta round the top view (0 = +x,
    90 = +y, the front), elevation up from the horizontal. Returns (point, normal)."""
    d = Vector((math.cos(elev) * math.cos(theta), math.cos(elev) * math.sin(theta), math.sin(elev)))
    c = Vector((0.0, CY, cz))
    lo, hi = 0.0, 20.0
    for _ in range(40):
        m = 0.5 * (lo + hi)
        p = c + d * m
        if inside(p.x, p.y, p.z):
            lo = m
        else:
            hi = m
    p = c + d * lo
    return p, shell_normal(p)


def shell_normal(p):
    def f(x, y, z):
        x -= DX(y)
        w = max(W(y), 1e-3)
        ht, hb = heights(w)
        h = ht if z >= 0 else hb
        return abs(x / w) ** NEXP + abs(z / h) ** NEXP
    e = 0.01
    g = Vector(((f(p.x + e, p.y, p.z) - f(p.x - e, p.y, p.z)),
                (f(p.x, p.y + e, p.z) - f(p.x, p.y - e, p.z)),
                (f(p.x, p.y, p.z + e) - f(p.x, p.y, p.z - e))))
    return g.normalized() if g.length > 1e-9 else Vector((0, 0, 1))


def outline_r(theta):
    """Top-view distance from (0, CY) to the plan outline at angle theta."""
    lo, hi = 0.0, 12.0
    for _ in range(36):
        m = 0.5 * (lo + hi)
        x, y = m * math.cos(theta), CY + m * math.sin(theta)
        if Y0 < y < Y1 and abs(x) < W(y):
            lo = m
        else:
            hi = m
    return lo


def k_of(x, y):
    th = math.atan2(y - CY, x)
    return math.hypot(x, y - CY) / max(outline_r(th), 1e-6)


def frange(a, b, step):
    n = max(1, int(math.ceil(abs(b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


# --- mesh helpers -------------------------------------------------------------------------------

def loft(bm, rings, mats, closed=False):
    """Join rings of 3D points (or single points for poles) in order; mats[i] between ring i and
    i + 1 (an int for all). closed joins the last ring back to the first."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    pairs = list(zip(vs, vs[1:])) + ([(vs[-1], vs[0])] if closed else [])
    for b, (r0, r1) in enumerate(pairs):
        m = mats if isinstance(mats, int) else mats[b]
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                vv = (r0[0], r1[i], r1[j])
            elif len(r1) == 1:
                vv = (r0[i], r1[0], r0[j])
            else:
                vv = (r0[i], r1[i], r1[j], r0[j])
            f = bm.faces.new(vv)
            f.material_index = m
    return vs


def cap(bm, ring, mat):
    f = bm.faces.new(ring)
    f.material_index = mat
    return f


def hull(bm, pts, mat):
    tmp = bmesh.new()
    vs = [tmp.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(tmp, input=vs)
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(1.0), verts=tmp.verts[:], edges=tmp.edges[:])
    add_bm(bm, tmp, mat)
    tmp.free()


def add_bm(bm, src, mat=None):
    m = {}
    for v in src.verts:
        m[v] = bm.verts.new(v.co)
    for f in src.faces:
        try:
            nf = bm.faces.new([m[v] for v in f.verts])
        except ValueError:
            continue
        nf.material_index = f.material_index if mat is None else mat


def to_object(name, bm, mats, coll, up=0.0):
    """px bmesh -> Blender object (X = x/12, Y = (14 - y + up)/12, Z = z/12), normals outward."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((1 / 12, 0, 0, 0), (0, -1 / 12, 0, (14 + up) / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def prism(bm, poly, z0, z1, mat):
    """A vertical prism on a convex top-view polygon (px)."""
    b = [bm.verts.new((x, y, z0)) for x, y in poly]
    t = [bm.verts.new((x, y, z1)) for x, y in poly]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((b[i], b[j], t[j], t[i])).material_index = mat
    bm.faces.new(b).material_index = mat
    bm.faces.new(t).material_index = mat


def groove(bm, pts, nrms, mat, half=0.24, depth=0.38, h=0.7, closed=False, ext=0.35):
    """A V-groove cutter along a surface polyline: a closed tube whose section is a trapezoid,
    `half` px half-wide at the surface, narrowing to a 0.05 px floor `depth` below it, opening to
    well above it (so the cut has 45-ish degree chamfered walls)."""
    pts = [Vector(p) for p in pts]
    nrms = [Vector(n) for n in nrms]
    if not closed and ext:
        t0 = (pts[0] - pts[1]).normalized()
        t1 = (pts[-1] - pts[-2]).normalized()
        pts = [pts[0] + t0 * ext] + pts + [pts[-1] + t1 * ext]
        nrms = [nrms[0]] + nrms + [nrms[-1]]
    n = len(pts)
    bfl = 0.05
    a = bfl + (half - bfl) * (h + depth) / depth
    rings = []
    for i in range(n):
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        else:
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nn = (nrms[i] - t * nrms[i].dot(t)).normalized()
        s = t.cross(nn).normalized()
        p = pts[i]
        rings.append([tuple(p + nn * h - s * a), tuple(p + nn * h + s * a),
                      tuple(p - nn * depth + s * bfl), tuple(p - nn * depth - s * bfl)])
    vs = loft(bm, rings, mat, closed=closed)
    if not closed:
        cap(bm, vs[0], mat)
        cap(bm, vs[-1][::-1], mat)


def resample(pts, step=0.35):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        k = max(1, int(math.ceil(d / step)))
        for i in range(1, k + 1):
            out.append(tuple(a[j] + (b[j] - a[j]) * i / k for j in range(len(a))))
    return out


def xy_seam(poly, step=0.5):
    """Surface points and normals over a top-view polyline."""
    pts, nrms = [], []
    for x, y in resample(poly, step):
        pts.append((x, y, top(x, y)))
        nrms.append(top_normal(x, y))
    return pts, nrms


def dir_seam(dirs):
    pts, nrms = [], []
    for th, el in dirs:
        p, n = on_dir(th, el)
        pts.append(tuple(p))
        nrms.append(n)
    return pts, nrms


def elev_at_k(theta, k):
    """Elevation (from the centre) whose shell point lies at fraction k of the top-view outline."""
    lo, hi = 0.0, math.radians(89)
    for _ in range(30):
        m = 0.5 * (lo + hi)
        p, _ = on_dir(theta, m)
        if k_of(p.x, p.y) > k:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


# --- materials ------------------------------------------------------------------------------------

(SHOULDER, UPLATE, FLANK, RIM, BELLY, CHANNEL, POST, LID, BAND, FRAME, CAPSULE, BARREL, BAYWALL, DEEP,
 ARM, HEAD, GROOVE, VANE) = range(18)
EMISSIVE = {VANE}


def materials(sprite, model, s, vane_pal):
    """Palette materials (pal_<index>): the sprite's own index per region (trimmed median of the
    region's pixels in frame 159; +s in the lighter frames). Satin metal: bronze metallic ~0.2,
    steel ~0.4."""
    def pal(i, tag, metallic, roughness, **kw):
        return common.palette_material(sprite, i, f"{model}_{tag}", metallic=metallic, roughness=roughness, **kw)
    mats = [
        pal(23 + s, "shoulder", 0.22, 0.42),
        pal(21 + s, "uplate", 0.22, 0.44),
        pal(20 + s, "flank", 0.22, 0.44),
        pal(20 + s, "rim", 0.2, 0.55),
        pal(20 + s, "belly", 0.15, 0.6),
        pal(2 + s, "channel", 0.3, 0.6),
        pal(164 + s, "post", 0.3, 0.42),
        pal(165 + s, "lid", 0.35, 0.38),
        pal(4 + s, "band", 0.2, 0.36),
        pal(2 + s, "frame", 0.25, 0.42),
        pal(5 + s, "capsule", 0.3, 0.28),
        pal(3 + s, "barrel", 0.3, 0.4),
        pal(2 + s, "baywall", 0.2, 0.7),
        pal(1, "deep", 0.0, 0.9),
        pal(4 + s, "arm", 0.5, 0.3),
        pal(5 + s, "head", 0.45, 0.32),
        pal(17 + s, "groove", 0.15, 0.7),
    ]
    if vane_pal is not None:
        mats.append(pal(vane_pal, "vane", 0.0, 0.5, emission_strength=2.2))
    else:
        mats.append(pal(4 + s, "vane", 0.4, 0.4))
    return mats


def region(x, y, z):
    """Shell material by position (after the grooves split the faces)."""
    el = math.atan2(z, math.hypot(x, y - CY))
    if el < E_BELT - math.radians(0.5):
        return BELLY
    if BAND_Y0 - 0.02 < y < BAND_Y1 + 0.02:
        return CHANNEL
    if y < BAND_Y0:
        return SHOULDER
    if k_of(x, y) >= RIM_K:
        return RIM
    return FLANK if abs(x) >= SEAM_X else UPLATE


# --- parts ----------------------------------------------------------------------------------------

def build_shell():
    """The ball: superellipse sections along y, poles at both ends, pinched under the band."""
    ys = sorted(set([round(v, 4) for v in frange(8.3, 11.95, 0.6) + frange(16.05, Y1, 0.65)
                     + [8.1, 8.22, 8.45, Y1 - 0.02, Y1 - 0.12, Y1 - 0.3, Y1 - 0.6] if Y0 < v < Y1]))
    ys += [BAND_Y0, BAND_Y1] + frange(BAND_Y0, BAND_Y1, 0.7)[1:-1]
    rings = [[(DX(Y0), Y0, 0.0)]]
    for y in sorted(set(ys)):
        w = W(y)
        ht, hb = heights(w)
        if BAND_Y0 - 1e-6 <= y <= BAND_Y1 + 1e-6:
            if abs(y - BAND_Y0) < 1e-6 or abs(y - BAND_Y1) < 1e-6:
                full = [(x, y, z) for x, z in section(w, ht, hb)]
                pin = [(x, y, z) for x, z in section(w - PINCH, ht - PINCH, hb - PINCH)]
                rings += [full, pin] if abs(y - BAND_Y0) < 1e-6 else [pin, full]
            else:
                rings.append([(x, y, z) for x, z in section(w - PINCH, ht - PINCH, hb - PINCH)])
        else:
            rings.append([(x + DX(y), y, z) for x, z in section(w, ht, hb)])
    rings.append([(0.0, Y1, 0.0)])
    bm = bmesh.new()
    loft(bm, rings, BELLY)
    return bm


def shell_cutters(tip):
    """Everything cut out of the shell: the plate grooves, the bay, the post channel and the arm
    sockets."""
    bm = bmesh.new()
    # The belt seam under the armour, all round.
    ring = [(math.radians(a), E_BELT) for a in frange(0, 360, 6)[:-1]]
    p, n = dir_seam(ring)
    groove(bm, p, n, GROOVE, closed=True)
    for sd in (-1, 1):
        # Shoulder seams: outer | inner shoulder plate, curving in to the post channel.
        p, n = xy_seam([(sd * 5.15, 12.4), (sd * 4.55, 10.5), (sd * 3.95, 9.35), (sd * 2.7, 8.85)])
        groove(bm, p, n, GROOVE)
        # Below the band: U plate round the bay | flank plate, down to the rim.
        yr = BAND_Y1
        while k_of(SEAM_X, yr) < RIM_K and yr < 24:
            yr += 0.05
        p, n = xy_seam([(sd * SEAM_X, 15.7), (sd * SEAM_X, yr + 0.1)])
        groove(bm, p, n, GROOVE)
    # The rim's inner edge, round the front from band to band.
    pts = []
    for a in frange(1.0, 179.0, 3.0):
        th = math.radians(a)
        r = RIM_K * outline_r(th)
        pts.append((r * math.cos(th), CY + r * math.sin(th)))
    p, n = xy_seam(pts, 0.4)
    groove(bm, p, n, GROOVE, ext=0.6)
    # The rim's segment joints, from its inner edge down to the belt.
    for a in (52.0, 128.0):
        th = math.radians(a)
        e0 = elev_at_k(th, RIM_K)
        p, n = dir_seam([(th, e) for e in frange(e0 + 0.03, E_BELT - 0.05, 0.06)])
        groove(bm, p, n, GROOVE, ext=0.15)
    # The bay under the band (sprite cols 9-14, rows 16-20): straight walls into the ball, a lip at
    # the front.
    bay = [(-2.95, 15.6), (2.95, 15.6), (2.95, 19.55), (2.3, 20.3), (-2.3, 20.3), (-2.95, 19.55)]
    prism(bm, bay, 3.1, 12.0, BAYWALL)
    # The channel round the post (sprite cols 9 and 14, row 11).
    prism(bm, [(POST_X - 3.0, 6.0), (POST_X + 3.0, 6.0), (POST_X + 3.0, 12.1), (POST_X - 3.0, 12.1)], 2.2, 12.0, CHANNEL)
    for sd in (-1, 1):
        prism(bm, socket_poly(sd), -1.35, 1.75, BAYWALL)
    vane_slots(bm)
    return bm


def socket_poly(sd):
    x0, x1 = 6.25, 11.0
    return [(sd * x0, 12.45), (sd * x1, 12.45), (sd * x1, 15.55), (sd * x0, 15.55)][::sd]


BAND_C = 0.32


def band_loop(y_unused, grow):
    w = BAND_W + grow
    return section(w, KT * BAND_W + 0.45 + grow, KB * BAND_W + 0.15 + grow, n=40)


def band_top(x):
    w, h = BAND_W, KT * BAND_W + 0.45
    if abs(x) >= w:
        return 0.0
    return h * (1 - abs(x / w) ** NEXP) ** (1 / NEXP)


def build_band():
    """The steel band round the ball in its groove: a flat strap with chamfered edges."""
    c = BAND_C
    inner_w = BAND_W - PINCH - 0.25
    def ring(y, grow, inner=False):
        if inner:
            w = inner_w
            return [(x, y, z) for x, z in section(w, KT * BAND_W - PINCH - 0.25, KB * BAND_W - PINCH - 0.25, n=40)]
        return [(x, y, z) for x, z in band_loop(y, grow)]
    y0, y1 = 12.0, 16.0
    rings = [ring(y0, 0, True), ring(y0, -c), ring(y0 + c, 0), ring(y1 - c, 0), ring(y1, -c), ring(y1, 0, True)]
    bm = bmesh.new()
    loft(bm, rings, BAND, closed=True)
    return bm


def band_cutters():
    bm = bmesh.new()
    for sd in (-1, 1):
        for xs in (4.6, 6.4):
            pts, nrms = [], []
            for y in frange(11.6, 16.4, 0.4):
                pts.append((sd * xs, y, band_top(sd * xs)))
                e = 0.02
                fx = (band_top(sd * xs + e) - band_top(sd * xs - e)) / (2 * e)
                nrms.append(Vector((-fx, 0, 1)).normalized())
            groove(bm, pts, nrms, GROOVE, half=0.16, depth=0.28)
        prism(bm, socket_poly(sd), -1.35, 1.75, BAYWALL)
    vane_slots(bm)
    return bm


def build_frame(bm):
    """The dark steel frame plate on the band's middle (sprite cols 9-14, rows 12-16): an octagonal
    plate following the band's curve, chamfered."""
    c, lift, thick = 0.22, 0.38, 1.0
    x0, x1 = -3.35, 3.35
    xs = [x0, x0 + c] + frange(x0 + c, x1 - c, 0.45)[1:-1] + [x1 - c, x1]

    def ylo(x):
        return 11.55 + max(0.0, abs(x) - 2.45)

    def yhi(x):
        return 16.45 - max(0.0, abs(x) - 2.45)
    nrow = 10
    grid = []
    for i, x in enumerate(xs):
        a, b = ylo(x), yhi(x)
        edge_c = i in (0, len(xs) - 1)
        ys = [a, a + c] + [a + c + (b - a - 2 * c) * k / (nrow - 3) for k in range(1, nrow - 3)] + [b - c, b]
        col = []
        for j, y in enumerate(ys):
            edge = edge_c or j in (0, len(ys) - 1)
            xx = x if not (i == 1 or i == len(xs) - 2) else x
            col.append(bm.verts.new((xx, y, band_top(x) + lift - (c if edge else 0.0))))
        grid.append(col)
    for i in range(len(grid) - 1):
        for j in range(nrow - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])).material_index = FRAME
    loop = [grid[i][0] for i in range(len(grid))] + [grid[-1][j] for j in range(1, nrow)]
    loop += [grid[i][-1] for i in range(len(grid) - 2, -1, -1)] + [grid[0][j] for j in range(nrow - 2, 0, -1)]
    zb = band_top(x1) + lift - thick
    low = [bm.verts.new((v.co.x, v.co.y, zb)) for v in loop]
    n = len(loop)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((loop[i], loop[j], low[j], low[i])).material_index = FRAME
    bm.faces.new(low).material_index = FRAME


POST_X = -0.45  # the sprite's post and its outline sit half a pixel left of the centre line


def build_post(bm):
    """The post on the crown (sprite cols 10-13, rows 7-11): an armoured housing standing in its
    dark channel, a bevelled lid on top and a deep exhaust in its rear face."""
    px = POST_X
    hull(bm, talon.cbox(px - 2.55, px + 2.55, 8.35, 11.25, 2.0, 7.0, 0.45), POST)
    hull(bm, talon.cbox(px - 1.95, px + 1.95, 8.9, 10.6, 6.6, 7.45, 0.28), LID)
    # Rear exhaust: a short collar, a lip and a bore into the dark.
    zc, r = 4.2, 1.2

    def circ(y, rr, n=16):
        return [(px + rr * math.cos(2 * math.pi * (i + 0.5) / n), y, zc + rr * math.sin(2 * math.pi * (i + 0.5) / n))
                for i in range(n)]
    loft(bm, [circ(8.4, r), circ(8.05, r), circ(8.05, r - 0.32), circ(9.2, r - 0.45), [(px, 9.2, zc)]],
         [ARM, ARM, DEEP, DEEP])
    # Two vent slots each side of the housing (dark, set in).
    for sd in (-1, 1):
        for zz in (3.6, 5.0):
            xx = px + sd * 2.57
            hull(bm, talon.cbox(xx - 0.12, xx + 0.12, 8.6, 10.4, zz, zz + 0.5, 0.05), DEEP)


def cap_axis(y):
    return 7.75 - 0.31 * (y - 11.75)


def build_capsule(bm):
    """The steel capsule (cannon) lying along the ball's front: its dome over the frame plate (the
    sprite's bright head, cols 10-13, rows 12-15), a collar at the band's edge, then a narrower
    barrel down into the bay ending in a muzzle ring with a dark bore (the sprite's ring, rows 16-19)."""
    n = 16

    def ring(y, r):
        zc = cap_axis(y)
        return [(r * math.cos(2 * math.pi * (i + 0.5) / n), y, zc + r * math.sin(2 * math.pi * (i + 0.5) / n))
                for i in range(n)]
    R = 1.95
    secs = [((11.72, 0.0), None)]
    dome = 1.9
    for t in (0.2, 0.4, 0.6, 0.8, 1.0):
        a = t * math.pi / 2
        secs.append(((11.72 + dome * (1 - math.cos(a)), R * math.sin(a)), CAPSULE))
    secs += [((14.3, R), CAPSULE), ((14.3, R + 0.12), CAPSULE), ((14.75, R + 0.12), ARM), ((14.75, R), ARM),
             ((15.55, R), CAPSULE), ((15.55, R + 0.14), CAPSULE), ((16.05, R + 0.14), ARM),
             ((16.25, 1.55), ARM), ((16.6, 1.38), BARREL), ((18.75, 1.38), BARREL), ((18.75, 1.62), ARM),
             ((19.75, 1.62), ARM), ((19.75, 0.78), DEEP), ((18.4, 0.78), DEEP)]
    rings = []
    mats = []
    for (y, r), m in secs:
        rings.append([(0.0, y, cap_axis(y))] if r == 0 else ring(y, r))
        if m is not None:
            mats.append(m)
    rings.append([(0.0, 18.4, cap_axis(18.4))])
    mats.append(DEEP)
    loft(bm, rings, mats)
    # A cradle under the barrel, from the bay floor.
    hull(bm, talon.cbox(-0.85, 0.85, 16.7, 17.8, 2.9, cap_axis(17.2) - 0.9, 0.2), BARREL)
    # A dark sighting slot on the capsule's top.
    hull(bm, talon.cbox(-0.32, 0.32, 13.65, 14.15, cap_axis(13.9) + R - 0.25, cap_axis(13.9) + R + 0.04, 0.08), DEEP)


def build_arms(bm, tip, o):
    """The telescoping arms: a head that retracts flush into the band's socket (tip 8) and slides out
    on two rod stages (frames 161-167); its outer end flares (jaws open) with the vanes."""
    yc, zc = 14.0, 0.2
    for sd in (-1, 1):
        hx1 = tip - 1.02  # the inner edge of the sprite's ink
        hx0 = hx1 - 2.3
        # rods: stage 1 out of the socket, stage 2 out of stage 1
        ext = hx0 - 6.4
        if ext > 0.05:
            s1 = 6.4 + ext * 0.55
            lib.polyline_tube(bm, [(sd * 6.3, yc, zc), (sd * s1, yc, zc)], 1.0, sides=12, mat_index=ARM)
            lib.polyline_tube(bm, [(sd * (s1 - 0.25), yc, zc), (sd * s1, yc, zc)], 1.12, sides=12, mat_index=HEAD)
            lib.polyline_tube(bm, [(sd * (s1 - 0.4), yc, zc), (sd * (hx0 + 0.2), yc, zc)], 0.85, sides=12,
                              mat_index=ARM)
        # head: a chamfered block, flaring at its outer end, with a dark slot in its outer face
        # its rear side flares further than its front as the jaws open; the tip tapers (sprite 167: the
        # head is rows 12-15 wide behind a 2-row tip)
        fl = min(1.0, o / 0.35)
        rear, front = 1.0 + 0.3 * fl, 1.0 + 0.2 * fl
        pts = []
        for x, yr, yf, c in ((hx0, rear, front, 0.0), (hx0 + 0.3, rear, front, 0.3), (hx1 - 1.15, rear, front, 0.3),
                             (hx1 - 0.2, 1.0, 1.0, 0.25), (hx1, 0.85, 0.85, 0.0)):
            for yy in (yc - yr + (0.3 - c), yc + yf - (0.3 - c)):
                for zz in (zc - 1.25 + (0.3 - c), zc + 1.45 - (0.3 - c)):
                    pts.append((sd * x, yy, zz))
        hull(bm, pts, HEAD)
        xs = sorted((sd * (hx1 - 0.2), sd * (hx1 + 0.015)))
        hull(bm, talon.cbox(xs[0], xs[1], 13.6, 14.4, zc - 0.65, zc + 0.85, 0.04), DEEP)
        # and a ridge along its top
        xr = sorted((sd * (hx0 + 0.3), sd * (hx1 - 0.35)))
        hull(bm, talon.cbox(xr[0], xr[1], 13.5, 14.5, zc + 1.35, zc + 1.68, 0.1), HEAD)


# The vanes, open (sprite px, right side; frame 167's red lobes, to the inner edge of the ink): a front lobe
# below each arm (rows 15-18.5) and a smaller rear lobe above it (rows 10-12.5), each a stack of thin
# blades sliding out of slots in the ball's side. Opening o scales them out from the root line x = 7.
VANE_FRONT = [(6.2, 15.0), (10.0, 15.0), (10.0, 16.6), (9.0, 17.5), (8.0, 19.0), (6.2, 19.0)]
VANE_REAR = [(6.2, 11.0), (9.0, 11.0), (9.0, 12.0), (10.0, 12.0), (10.0, 13.0), (6.2, 13.0)]
VANE_Z = ((VANE_FRONT, (1.25, 0.3, -0.65)), (VANE_REAR, (1.0, -0.05)))
VANE_T = 0.22
VANE_ROOT = 7.0


def blade(bm, poly, z0, z1, mat):
    """An extruded (possibly concave) top-view polygon, its caps triangulated."""
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) < 0:
        poly = poly[::-1]
    lo = [bm.verts.new((x, y, z0)) for x, y in poly]
    hi = [bm.verts.new((x, y, z1)) for x, y in poly]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat
    caps = [bm.faces.new(lo[::-1]), bm.faces.new(hi)]
    for f in caps:
        f.material_index = mat
    bmesh.ops.triangulate(bm, faces=caps, quad_method="BEAUTY", ngon_method="EAR_CLIP")


def build_vanes(bm, o):
    """Red-hot vanes sliding out of the ball's side round each arm root (frames 163-167): the front
    lobe first, the rear lobe from frame 165 (163's sprite shows red only below the arm)."""
    if o <= 0:
        return
    for sd in (-1, 1):
        for k, (poly, zs) in enumerate(VANE_Z):
            oo = max(o, min(0.48, 1.4 * o)) if k == 0 else max(0.0, (o - 0.35) / 0.65)
            if oo <= 0:
                continue
            for z in zs:
                pp = [(sd * (VANE_ROOT + (x - VANE_ROOT) * oo if x > VANE_ROOT else x), y) for x, y in poly]
                blade(bm, pp, z - VANE_T / 2, z + VANE_T / 2, VANE)


def vane_slots(bm):
    """Slots in the ball's side the vanes slide out of (all frames: shut, they read as vents)."""
    for sd in (-1, 1):
        for poly, zs in VANE_Z:
            y0 = min(y for x, y in poly) + 0.15
            y1 = max(y for x, y in poly if x <= VANE_ROOT + 1.2) - 0.15
            for z in zs:
                box = [(sd * 5.6, y0), (sd * 10.0, y0), (sd * 10.0, y1), (sd * 5.6, y1)][::sd]
                prism(bm, box, z - 0.24, z + 0.24, GROOVE)


def rivet(bm, p, n, mat, r=0.24, h=0.2):
    n = Vector(n).normalized()
    p = Vector(p)
    t = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    u = n.cross(t).normalized()
    v = n.cross(u)
    pts = []
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = u * math.cos(a) + v * math.sin(a)
        pts.append(tuple(p - n * 0.15 + d * r))
        pts.append(tuple(p + n * h + d * r * 0.62))
    hull(bm, pts, mat)


def build_rivets(bm):
    xy = [(6.2, 11.0), (3.7, 11.25), (3.85, 19.6), (6.2, 17.1)]
    for x, y in xy:
        for sd in (-1, 1):
            rivet(bm, (sd * x, y, top(sd * x, y)), top_normal(sd * x, y), POST)
    for a in (16.0, 34.0, 70.0, 90.0, 110.0, 146.0, 164.0):
        th = math.radians(a)
        rr = 0.9 * outline_r(th)
        x, y = rr * math.cos(th), CY + rr * math.sin(th)
        rivet(bm, (x, y, top(x, y)), top_normal(x, y), RIM, r=0.22)
    for sd in (-1, 1):
        for y in (12.55, 15.45):
            x = sd * 3.9
            rivet(bm, (x, y, band_top(x)), Vector((-(band_top(x + 0.02) - band_top(x - 0.02)) / 0.04, 0, 1)), ARM,
                  r=0.22)


# --- assembly -------------------------------------------------------------------------------------

def boolean(obj, cutter):
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    mod.material_mode = "INDEX"
    mod.use_self = True
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    # The exact boolean leaves fans of slivers; merge near-coplanar pieces and retriangulate.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(DISSOLVE), verts=bm.verts[:], edges=bm.edges[:],
                             delimit={"MATERIAL"})
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                          ngon_method="BEAUTY")
    bm.to_mesh(obj.data)
    bm.free()


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def build_frame_model(sprite, coll, spec):
    frame, model, tip, s, up, o, vane_pal = spec
    mats = materials(sprite, model, s, vane_pal)
    shell = to_object(model + "-shell", build_shell(), mats, coll, up)
    boolean(shell, to_object(model + "-cut", shell_cutters(tip), mats, coll, up))
    # Shell faces take their plate's colour (the grooves split them along the seams).
    inv = 12.0
    for p in shell.data.polygons:
        if p.material_index == BELLY:
            c = p.center
            x, y, z = c.x * inv, 14 + up - c.y * inv, c.z * inv
            p.material_index = region(x, y, z)
    band = to_object(model + "-band", build_band(), mats, coll, up)
    boolean(band, to_object(model + "-bandcut", band_cutters(), mats, coll, up))
    bm = bmesh.new()
    build_frame(bm)
    build_post(bm)
    build_capsule(bm)
    build_arms(bm, tip, o)
    build_vanes(bm, o)
    build_rivets(bm)
    parts = to_object(model + "-parts", bm, mats, coll, up)
    for o in (shell, band, parts):
        print(f"{NAME}: part", o.name, sum(len(p.vertices) - 2 for p in o.data.polygons), "tris")
    obj = join([shell, band, parts], model)
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(32))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj, mats


def bake(obj, mats, model):
    tint, textured = talon.TINT, talon.TEXTURED
    talon.TINT = TINT
    talon.TEXTURED = tuple(i for i in range(len(mats)) if i not in EMISSIVE)
    bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake" / model
    bake_dir.mkdir(parents=True, exist_ok=True)
    try:
        talon.bake_maps(obj, bake_dir, size=512, samples=64)
    finally:
        talon.TINT, talon.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name.startswith("talon_"):
            img.name = img.name.replace("talon_", f"{model}_")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    want = None
    if "--frames" in argv:
        want = {int(v) for v in argv[argv.index("--frames") + 1].split(",")}
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    baked = "--no-bake" not in argv
    fmt = "WEBP" if baked else "AUTO"
    sprite = common.load_sprite(ROOT, NAME)
    by_index = {f["index"]: f for f in sprite["frames"]}
    coll = common.reset_collection(NAME)
    exported, previews = [], []
    for spec in FRAMES:
        frame, model = spec[0], spec[1]
        if want and frame not in want:
            continue
        obj, mats = build_frame_model(sprite, coll, spec)
        # The outline shell is made from the whole closed model; cull_hidden opens the mesh and the
        # voxel remesh of the open mesh kept only a middle band.
        full_me = obj.data.copy()
        talon.cull_hidden(obj, grid=3, ndirs=40)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"{NAME}: {model} {len(obj.data.polygons)} faces, {tris} triangles")
        if baked:
            bake(obj, mats, model)
        # The outline shell (D51), made after the bake so its occlusion rays never hit it.
        full = obj.copy()
        full.data = full_me
        coll.objects.link(full)
        shell = common.outline_shell(full, coll, faces=1200)
        bpy.data.objects.remove(full, do_unlink=True)
        shell.name = shell.data.name = f"{model}_outline"
        print(f"{NAME}: {model} outline shell {len(shell.data.polygons)} faces")
        if out:
            exported += [obj, shell]
        else:
            common.export_sprite_model(ROOT, [obj, shell], f"enemies/{model}", lib.frames_subset(sprite, [frame]),
                                       image_format=fmt)
        obj.hide_render = shell.hide_render = True
        previews.append((frame, model, obj))
    if out:
        common.export_glb(exported, out, image_format=fmt)
        print(f"{NAME}: exported {out}")
    if "--preview" in argv:
        png = Path(argv[argv.index("--preview") + 1])
        for i, (frame, model, obj) in enumerate(previews):
            obj.hide_render = False
            f = by_index[frame]
            path = png if i == 0 else png.with_name(f"{png.stem}{model[len(NAME):]}.png")
            common.render_preview([obj], str(path), ROOT / "reference" / "models" / NAME / f["image"], size=f["size"])
            obj.hide_render = True


if __name__ == "__main__":
    main()
