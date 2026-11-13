"""newsh3-52, the copper shield pod (newsh3.shp 52 in episode 4, newshd.shp 117 in episode 2; 24 x 28
px, one picture on both sheets), rebuilt as what it is (D65, D120, D122, D166, D167).

WHAT IT IS: a flying armoured pod (type 826, armour 2, three turrets 68): it drifts straight down the
screen on the sky layer (0,+3 / +4 px per tick), so it flies free with a closed, round underside, its
point leading. A domed copper carapace shaped like a heraldic shield: three lobes along the top edge
(two rounded shoulders and, in the middle, a ring lug: a towing / launch eye), the point at the
bottom; pale machined ribs run over the dome from the rim to a bezel round the glowing orange core.

Reading the sprite (pixel edges, col x right, row y down):
- Outline (inner mask, the game draws its own ink): full width x 1..23 over rows 6-17, shoulders
  x 2..7 / 17..22 at row 5 with tops at y 4, notches (ink) at x 7..9 and 15..17 on row 5, the lug a
  disc round (12, 7.2) reaching y 4, then the shield's sides narrowing to a blunt point (x 9..15 on
  row 24, bottom y 25). Mirror-symmetric about x 12.
- Colours: carapace 72 (copper median; 67-70 on the right and edges and 76-79 near the core are
  lighting), ribs 77 (pale, on lit and unlit sides alike, so a material, not sheen), lug 74, lug hole
  65-68 (dark), the slot down from the lug 67-69 (dark), core 121 with a 125 hot heart up-left, 122 /
  120 flanks and 116-119 red in its lower half, underside (unseen) 68.
- Ribs, from the sprite's pale lines: upper left and right straight at 45 degrees, x = y - 2 and
  x = 26 - y (pixel centres (3.5,5.5)->(10.5,12.5) and mirrored), left (2.5,13.5)->(9.5,16.5), lower left (3.5,18.5)->(9.5,17.5), lower right
  (20.5,18.5)->(14.5,17.5), down to the point (14.5,19.5)->(13.5,24.2), and a right one mirrored from
  the left (the sprite's light falls from the left, so it only darkens there).
- Bezel: the bright arc round the core (cols 9-14, rows 15-21): a raised collar, r ~3 px about (12, 18).

Build: the carapace is one loft of rings scaled from the fitted outline toward a centre (12, 15.5); the
inner rings relax to a smooth oval (no notches inside the dome), the outer ones carry the lobes. The
outline is faired: the lobes are interpolated, the taper from the straight sides to the point is one
convex B-spline fitted to the staircase (no pixel waves). Its section has a raised rim bead with a panel
groove inside it, a chamfered edge band and a shallow round underside; from the sides down the rim rings
are inset along the outline's normal, so the band keeps a constant section. Ribs are chamfered
trapezoid sweeps laid on the dome (raycast) with chamfered end caps and a low round bolt on the top of
each outer end; the lug a chamfered ring with a dark socket, the core a lens whose facets take the
sprite's own glow index under them.
Outline shell from a sealed pre-cull copy (D51/D90/D118); hidden faces culled. No textures folder.

    tools/build-models.sh -j 2 assets/blender/enemies/newsh3-52.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
WT = None
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newsh3-52"
PX = 1 / 12


def bl(x, y, z):
    """Sprite px (column edge, row edge, height px) to Blender units (24 x 28 block, centred)."""
    return Vector(((x - 12) * PX, (14 - y) * PX, z * PX))


# --- outline -------------------------------------------------------------------------------------

# Right half of the carapace outline (no lug), on the inner mask's edge (each point between an inner
# and an outer pixel centre). TOP runs from the top centre over the shoulder lobe and down the straight
# side; it is interpolated (the lobes are drawn shapes). Below the side the sprite's edge is a pixel
# staircase (rows 18-24), so the taper to the blunt point is NOT interpolated through it: LOW is the
# control polygon of a uniform cubic B-spline, convex (so the curve is convex: no waves), fitted by
# least squares to the staircase's row widths (row 23's ink step taken at its midpoint). The three
# collinear points at its head join the straight side with zero curvature; the two at its tail meet the
# mirror image level at the point.
HALF_TOP = [
    (12.0, 6.05), (14.0, 6.05), (15.6, 6.08), (16.6, 5.8), (17.4, 5.25), (18.3, 4.62), (19.2, 4.18),
    (20.0, 4.02), (20.8, 4.18), (21.5, 4.75), (22.1, 5.5), (22.65, 6.3), (22.95, 7.3), (23.02, 9.0),
    (23.02, 12.0), (23.02, 16.59),
]
LOW = [
    (23.02, 12.59), (23.02, 14.59), (23.02, 16.59), (22.849, 17.857), (21.604, 19.586), (20.302, 21.215),
    (19.239, 22.402), (18.202, 23.081), (13.672, 25.05), (12.0, 25.05), (10.328, 25.05),
]
C = (12.0, 15.5)  # loft centre (and the dome's crown)
N_HALF = 60       # outline samples per half (N = 2 * N_HALF)


def catmull(pts, step=0.05, post=None):
    """Centripetal Catmull-Rom through an open list; the head phantom mirrors pts[1] about x 12, the
    tail phantom is `post` (default: pts[-2] mirrored)."""
    def mir(p):
        return (24.0 - p[0], p[1])
    ext = [mir(pts[1])] + pts + [post if post else mir(pts[-2])]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = [Vector(p) for p in ext[i - 1:i + 3]]
        def tj(ti, a, b):
            return ti + max((b - a).length, 1e-6) ** 0.5
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        n = max(2, int((p2 - p1).length / step))
        for k in range(n):
            t = t1 + (t2 - t1) * k / n
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(Vector(pts[-1]))
    return out


def bspline(ctrl, n=40):
    """Uniform cubic B-spline through the control polygon (approximating), n samples per span."""
    q = [Vector(p) for p in ctrl]
    out = []
    for i in range(len(q) - 3):
        for k in range(n):
            t = k / n
            w = ((1 - t) ** 3 / 6, (3 * t ** 3 - 6 * t * t + 4) / 6, (-3 * t ** 3 + 3 * t * t + 3 * t + 1) / 6,
                 t ** 3 / 6)
            out.append(sum((wi * qi for wi, qi in zip(w, q[i:i + 4])), Vector((0.0, 0.0))))
    out.append((q[-3] + 4 * q[-2] + q[-1]) / 6)
    return out


def resample(poly, n):
    """n + 1 points evenly by arc length along an open polyline."""
    d = [0.0]
    for a, b in zip(poly, poly[1:]):
        d.append(d[-1] + (b - a).length)
    out = []
    j = 0
    for k in range(n + 1):
        s = d[-1] * k / n
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        t = (s - d[j]) / max(d[j + 1] - d[j], 1e-9)
        out.append(poly[j].lerp(poly[j + 1], t))
    return out


def outline_loop():
    """The closed outline, N points clockwise (image coords) from the top centre, mirror-exact."""
    top = catmull(HALF_TOP, post=(23.02, 19.0))[:-1]
    right = resample(top + bspline(LOW), N_HALF)  # top centre .. bottom centre
    left = [Vector((24.0 - p.x, p.y)) for p in reversed(right[1:-1])]
    return right + left


LOOP = None


def relax(loop, iters):
    pts = [p.copy() for p in loop]
    n = len(pts)
    for _ in range(iters):
        pts = [(pts[i - 1] + pts[i] * 2 + pts[(i + 1) % n]) / 4 for i in range(n)]
    return pts


# --- carapace ------------------------------------------------------------------------------------

Z_EDGE_TOP, Z_EDGE_BOT = 0.9, -0.5
DOME_T = [0.0, 0.25, 0.45, 0.62, 0.76, 0.88, 1.0]
DOME_Z = [6.3, 6.05, 5.45, 4.6, 3.65, 2.65, 1.75]
dome_z = T.pchip(DOME_T, DOME_Z)
UNDER_T = [0.0, 0.4, 0.7, 0.9, 1.0]
UNDER_Z = [-3.4, -3.1, -2.3, -1.35, -0.9]
under_z = T.pchip(UNDER_T, UNDER_Z)


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def build_carapace(bm, m_shell, m_rim, m_under, m_groove):
    global LOOP
    loop = outline_loop()
    LOOP = loop
    soft = relax(loop, 60)
    # scale the relaxed oval back up to the outline's mean radius, so inner rings don't shrink
    c = Vector(C)
    k = sum((p - c).length for p in loop) / sum((p - c).length for p in soft)
    soft = [c + (p - c) * k for p in soft]
    n = len(loop)

    # inset directions: along the radius on the lobed top (offsetting the lobes along their normals
    # would fold them), along the outline's inward normal from the straight sides down to the point,
    # so the rim band there keeps a constant section
    dirs = []
    for i, o in enumerate(loop):
        tn = (loop[(i + 1) % n] - loop[i - 1]).normalized()
        nin = Vector((tn.y, -tn.x))
        if nin.dot(c - o) < 0:
            nin = -nin
        rad = (c - o).normalized()
        w = smoothstep(8.5, 12.0, o.y)
        dirs.append(rad.lerp(nin, w).normalized())

    def ring_pts(t, d):
        """Ring at radial fraction t (0 centre, 1 outline) pulled in a further d px."""
        b = smoothstep(0.55, 0.97, t)
        pts = []
        for o, s, u in zip(loop, soft, dirs):
            q = s.lerp(o, b)
            v = q - c
            L = v.length
            p = c + v * t
            if d:
                p = p + u * d
            pts.append((p, (p - c).length / L))
        return pts

    # (t, d, z or None, material of the band above it, top?)  z None = from the dome / underside
    prof = []
    for t in (0.1, 0.22, 0.34, 0.46, 0.57, 0.66):
        prof.append((t, 0.0, "dome", m_shell))
    # near the edge, absolute insets (px): dome, groove, raised rim bead, chamfer, band, chamfer
    prof += [
        (1.0, 2.55, "dome", m_shell),
        (1.0, 2.05, "dome", m_shell),
        (1.0, 1.85, ("drop", -0.4), m_shell),
        (1.0, 1.6, ("drop", -0.42), m_groove),
        (1.0, 1.42, ("drop", 0.02), m_groove),
        (1.0, 0.9, ("drop", 0.05), m_rim),
        (1.0, 0.35, ("drop", -0.3), m_rim),
        (1.0, 0.0, Z_EDGE_TOP, m_rim),
        (1.0, 0.0, Z_EDGE_BOT, m_rim),
        (1.0, 0.45, -0.95, m_under),
        (1.0, 1.4, "under", m_under),
    ]
    for t in (0.78, 0.6, 0.4, 0.2):
        prof.append((t, 0.0, "under", m_under))

    rings, mats = [], []
    for t, d, z, m in prof:
        pts = ring_pts(t, d)
        ring = []
        for (p, tf) in pts:
            if z == "dome":
                zz = dome_z(tf)
            elif z == "under":
                zz = under_z(tf)
            elif isinstance(z, tuple) and z[0] == "drop":
                zz = dome_z(tf) + z[1]
            else:
                zz = z
            ring.append(bm.verts.new(bl(p.x, p.y, zz)))
        rings.append(ring)
        mats.append(m)
    top = bm.verts.new(bl(c.x, c.y, dome_z(0.0)))
    bot = bm.verts.new(bl(c.x, c.y, under_z(0.0)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((top, rings[0][i], rings[0][j])).material_index = m_shell
    for r in range(len(rings) - 1):
        a, b = rings[r], rings[r + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], b[i], b[j], a[j])).material_index = mats[r + 1]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot, rings[-1][j], rings[-1][i])).material_index = m_under


# --- surface queries -----------------------------------------------------------------------------

class Surface:
    def __init__(self, bm):
        self.tree = BVHTree.FromBMesh(bm)

    def hit(self, x, y):
        """(z px, normal) of the carapace top over sprite (x, y)."""
        o = bl(x, y, 40)
        loc, nor, _, _ = self.tree.ray_cast(o, Vector((0, 0, -1)), 10.0)
        if loc is None:
            return 0.0, Vector((0, 0, 1))
        return loc.z / PX, (nor if nor.z >= 0 else -nor)  # the face's winding may point it down

    def plane(self, x, y, r=2.5, k=0.5):
        """(z px, normal) of a plane fitted to the carapace round (x, y) (central differences over
        r px), its tilt scaled by k (k < 1 keeps a fitting more level than the dome under it)."""
        z0 = self.hit(x, y)[0]
        gx = (self.hit(x + r, y)[0] - self.hit(x - r, y)[0]) / (2 * r) * k
        gy = (self.hit(x, y + r)[0] - self.hit(x, y - r)[0]) / (2 * r) * k  # per image px, y down
        # Blender y = -image y, so dz/dY = -gy
        return z0, Vector((-gx, gy, 1.0)).normalized()


def polyline(pts, step=0.3):
    """Smooth open path through pts (pchip on arc length per coordinate), sampled every `step` px."""
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.dist(a, b))
    fx = T.pchip(d, [p[0] for p in pts])
    fy = T.pchip(d, [p[1] for p in pts])
    n = max(3, int(d[-1] / step))
    return [(fx(d[-1] * k / n), fy(d[-1] * k / n)) for k in range(n + 1)]


def inset(x, y):
    """Distance (px) from (x, y) to the carapace outline (positive inside)."""
    best = 1e9
    for a, b in zip(LOOP, LOOP[1:] + LOOP[:1]):
        ab = b - a
        t = max(0.0, min(1.0, ((x - a.x) * ab.x + (y - a.y) * ab.y) / max(ab.length_squared, 1e-9)))
        best = min(best, math.hypot(x - (a.x + ab.x * t), y - (a.y + ab.y * t)))
    return best


def sweep_rib(bm, surf, pts, mat, w=1.3, h=0.55, sink=0.9, keep_in=2.15, cap=0.9, step=0.4, bridge=0.0):
    """A chamfered trapezoid rib laid on the carapace along pts (sprite px): heights and normals are
    smoothed along the path so it reads as one machined bar; clipped where it reaches the rim groove
    (keep_in px from the outline). Each end is a chamfered cap: over the last `cap` px the top drops to
    a fifth of its height and narrows, then a flat end face closes it below the dome. Returns the
    path and, per sample, its frame (base, side, up, tangent, top height). `bridge` (px): heights never
    drop below the chord between the carapace `bridge` px either side along the path, so a rib crossing
    the rim groove spans it instead of dipping in (its sunk base still reaches the groove floor)."""
    path = [p for p in polyline(pts, step) if inset(*p) >= keep_in]
    n = len(path)
    if n < 3:
        return path, []
    dist = [0.0]
    for p0, p1 in zip(path, path[1:]):
        dist.append(dist[-1] + math.dist(p0, p1))
    total = dist[-1]
    # heights from the carapace, normals from its height field (central differences): a raycast's
    # face normal tilts to one side on the dome's facets (and along the centre line, where it lands on
    # an edge)
    zs = [surf.hit(x, y)[0] for x, y in path]
    if bridge > 0:  # span dips narrower than 2 * bridge: never below the chord across them
        def at(d):
            j = min(range(n), key=lambda j: abs(dist[j] - d))
            return zs0[j]
        zs0 = zs
        zs = [max(zs0[i], 0.5 * (at(dist[i] - bridge) + at(dist[i] + bridge))) for i in range(n)]
    ns = [surf.plane(x, y, r=0.8, k=1.0)[1] for x, y in path]
    for _ in range(1):
        zs = [zs[0]] + [(zs[i - 1] + 2 * zs[i] + zs[i + 1]) / 4 for i in range(1, n - 1)] + [zs[-1]]
        ns = [ns[0]] + [(ns[i - 1] + ns[i] * 2 + ns[i + 1]).normalized() for i in range(1, n - 1)] + [ns[-1]]
    rings, frames = [], []
    for k, (x, y) in enumerate(path):
        nor = ns[k]  # follow the dome so both edges seat
        a = path[max(k - 1, 0)]
        b = path[min(k + 1, n - 1)]
        tng = (bl(b[0], b[1], 0) - bl(a[0], a[1], 0)).normalized()
        side = tng.cross(nor).normalized()
        up = side.cross(tng).normalized()
        e = min(dist[k], total - dist[k]) / cap  # 0 at an end, 1 a cap length in
        f = math.sin(min(e, 1.0) * math.pi / 2)
        hh = h * (0.2 + 0.8 * f)
        base = bl(x, y, zs[k])
        hw = w * 0.5 * (0.85 + 0.15 * f) * PX
        tw = w * 0.22 * (0.6 + 0.4 * f) * PX
        ring = [
            base + side * hw - up * sink * PX,
            base + side * hw + up * 0.02 * PX,
            base + side * tw + up * hh * PX,
            base - side * tw + up * hh * PX,
            base - side * hw + up * 0.02 * PX,
            base - side * hw - up * sink * PX,
        ]
        rings.append([bm.verts.new(v) for v in ring])
        frames.append((base, side, up, tng, hh))
    for a, b in zip(rings, rings[1:]):
        for i in range(5):
            bm.faces.new((a[i], b[i], b[i + 1], a[i + 1])).material_index = mat
        bm.faces.new((a[5], b[5], b[0], a[0])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat
    return path, frames


def rib_bolt(bm, frame, mat, r=0.36, h=0.17, seg=12):
    """A low round-headed bolt seated on a rib's top (in the rib's own frame, so it sits flush with the
    rib whatever the dome's slope)."""
    base, side, up, tng, hh = frame
    o = base + up * (hh - 0.09) * PX  # seated a touch into the top so its edge never hovers over the chamfers
    rings = []
    for rr, dz in ((r, 0.0), (r, 0.07), (r * 0.7, h * 0.8), (r * 0.3, h)):
        rings.append([bm.verts.new(o + (side * math.cos(2 * math.pi * k / seg) + tng * math.sin(2 * math.pi * k / seg))
                                   * rr * PX + up * dz * PX) for k in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            m = (k + 1) % seg
            bm.faces.new((a[k], a[m], b[m], b[k])).material_index = mat  # side x tng = up: outward
    bm.faces.new(rings[-1]).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat


def collar(bm, surf, cx, cy, prof, mat_of, seg=40):
    """A ring loft round (cx, cy): prof = [(r px, dz px over the local carapace), ...] from the inside
    out; each band takes mat_of[i]. Heights follow the carapace under the ring's centre plane."""
    z0, nor = surf.plane(cx, cy)
    # local plane through the centre with the carapace's normal there
    nz = max(nor.z, 0.3)
    rings = []
    for r, dz in prof:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            # plane height: z0 + slope * offset
            p = bl(x, y, 0) - bl(cx, cy, 0)
            zp = z0 - (nor.x * p.x + nor.y * p.y) / nz / PX
            ring.append(bm.verts.new(bl(x, y, zp + dz)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(seg):
            m = (k + 1) % seg
            bm.faces.new((a[k], a[m], b[m], b[k])).material_index = mat_of[i]
    return rings


# --- parts ---------------------------------------------------------------------------------------

UPPER_KEEP = 1.2
KEEL_KEEP = 1.0
RIBS = [  # (pale rib line of the sprite in pixel centres, clip px from the outline, groove bridge px);
    # the upper pair are its straight 45-degree lines (the sprite's big X), run out over the shoulder
    # lobes' groove to the rim bead, bridging the groove level
    ([(3.4, 5.4), (6.85, 8.85), (10.3, 12.3)], UPPER_KEEP, 0.9),        # upper left: x = y - 2
    ([(20.6, 5.4), (17.15, 8.85), (13.7, 12.3)], UPPER_KEEP, 0.9),      # upper right: x = 26 - y
    ([(2.2, 13.0), (4.0, 14.8), (6.2, 15.9), (8.6, 16.4)], 2.15, 0.0),       # left
    ([(21.8, 13.0), (20.0, 14.8), (17.8, 15.9), (15.4, 16.4)], 2.15, 0.0),   # right
    ([(2.6, 18.4), (4.6, 18.6), (6.8, 18.2), (8.8, 18.0)], 2.15, 0.0),       # lower left
    ([(21.4, 18.4), (19.4, 18.6), (17.2, 18.2), (15.2, 18.0)], 2.15, 0.0),   # lower right
    # keel: the sprite's pale line under the core, cols 13-14 ((14.5,19.5) -> (13.5,24.2)), from under
    # the bezel's skirt down to about 1.5 px from the point
    ([(14.55, 19.7), (14.2, 21.6), (13.75, 23.2), (13.45, 24.4)], KEEL_KEEP, 0.0),
]
LUG = (12.0, 7.25)
GEM = (12.0, 18.0)


LUG_TILT = math.radians(22)  # the eye pitches up toward the crown with the dome under it


def build_lug(bm, surf, m_lug, m_hole):
    """The towing eye: a chamfered ring (outer r 3.15 px, hole r 1.15) on the top edge, pitched with
    the dome so its inner half seats into the carapace and its outer half overhangs the rim; a dark
    socket inside; a chamfered root block ties it back into the dome."""
    cx, cy = LUG
    seg = 32
    z0, _ = surf.hit(cx, cy + 1.2)
    tz = math.tan(LUG_TILT)

    def P3(x, y, z):  # pitch about the ring's centre line (y = cy): rises toward +y (the crown)
        return bl(x, y, z + (y - cy) * tz)
    zt = z0 + 0.55
    prof = [  # (r, z) round the ring section, closed
        (1.15, zt - 1.6), (1.15, zt - 0.3), (1.5, zt), (2.7, zt), (3.15, zt - 0.4),
        (3.15, zt - 1.25), (2.75, zt - 1.6),
    ]
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new(P3(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg), z))
                      for k in range(seg)])
    for i in range(len(rings)):
        a, b = rings[i], rings[(i + 1) % len(rings)]
        for k in range(seg):
            m = (k + 1) % seg
            bm.faces.new((a[k], a[m], b[m], b[k])).material_index = m_lug
    ring = [bm.verts.new(P3(cx + 1.2 * math.cos(2 * math.pi * k / seg), cy + 1.2 * math.sin(2 * math.pi * k / seg),
                            zt - 1.1)) for k in range(seg)]
    f = bm.faces.new(ring)
    f.material_index = m_hole
    if f.normal.z < 0:
        f.normal_flip()
    # root block: from under the ring down into the dome, chamfered top. It stays under the ring's
    # (pitched) top everywhere: its head used to poke 0.3 px through the ring's flat top, a level tile
    # that caught the sun as a white quad in 3/4 rear views. Its exposed end ramps just below the dome,
    # meeting the dome and the slot strip at an angle (no coplanar faces)
    def ring_top(y):
        return zt + (y - cy) * tz
    z1, _ = surf.hit(cx, 10.6)
    sec = []
    for y, zz, hw in ((8.6, ring_top(8.6) - 0.6, 1.9), (9.9, ring_top(9.9) - 0.55, 1.6), (10.6, z1 - 0.15, 1.2)):
        sec.append([bl(cx - hw, y, zz - 2.4), bl(cx - hw, y, zz - 0.35), bl(cx - hw + 0.35, y, zz),
                    bl(cx + hw - 0.35, y, zz), bl(cx + hw, y, zz - 0.35), bl(cx + hw, y, zz - 2.4)])
    vs = [[bm.verts.new(v) for v in r] for r in sec]
    for a, b in zip(vs, vs[1:]):
        for i in range(6):
            j = (i + 1) % 6
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = m_lug
    bm.faces.new(list(reversed(vs[0]))).material_index = m_lug
    bm.faces.new(vs[-1]).material_index = m_lug


def build_slot(bm, surf, m_dark):
    """The dark slot from the lug's root down the dome between the upper ribs (cols 11-12, rows
    9-13): a recessed channel, shown as a dark strip just proud of the dome."""
    sweep_rib(bm, surf, [(12.0, 10.2), (12.0, 11.6), (12.0, 13.0)], m_dark, w=1.9, h=0.08, sink=0.3, keep_in=0, cap=0.01)


def build_core(bm, surf, mats, m_bezel, m_bezel_in, sprite_px):
    """Bezel collar round the core and the glowing lens inside it."""
    cx, cy = GEM
    collar(bm, surf, cx, cy,
           [(1.95, -0.2), (1.95, 0.5), (2.25, 0.85), (2.75, 0.85), (3.1, 0.35), (3.3, -1.0)],
           [m_bezel_in, m_bezel, m_bezel, m_bezel, m_bezel], seg=32)
    # lens: a dome on the local plane, r 2.0, 1.25 px high above the plane
    z0, nor = surf.plane(cx, cy)
    nz = max(nor.z, 0.3)
    seg, rings_n = 24, 5
    centre = None
    rings = []
    for i in range(rings_n + 1):
        u = i / rings_n
        r = 2.0 * math.sin(u * math.pi / 2)
        h = 0.2 + 1.15 * math.cos(u * math.pi / 2)
        if i == 0:
            centre = (cx, cy, h)
            continue
        ring = []
        for k in range(seg):
            a = 2 * math.pi * (k + 0.5 * (i % 2)) / seg
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            p = bl(x, y, 0) - bl(cx, cy, 0)
            zp = z0 - (nor.x * p.x + nor.y * p.y) / nz / PX
            ring.append(bm.verts.new(bl(x, y, zp + h - 0.4)))
        rings.append(ring)
    cv = bm.verts.new(bl(cx, cy, z0 + 1.35 - 0.4))

    def glow_mat(x, y):
        c, r = int(math.floor(x)), int(math.floor(y))
        best = None
        for dr in (0, -1, 1):
            for dc in (0, -1, 1):
                v = sprite_px[r + dr][c + dc] if 0 <= r + dr < len(sprite_px) and 0 <= c + dc < 24 else -1
                if v in mats:
                    best = v
                    break
            if best is not None:
                break
        return mats.get(best, mats[121])

    faces = []
    for k in range(seg):
        m = (k + 1) % seg
        faces.append(bm.faces.new((cv, rings[0][k], rings[0][m])))
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(seg):
            m = (k + 1) % seg
            faces.append(bm.faces.new((a[k], b[k], b[m], a[m])))
    for f in faces:
        p = f.calc_center_median()
        f.material_index = glow_mat(p.x / PX + 12, 14 - p.y / PX)
    # close the lens bottom
    fb = bm.faces.new(list(reversed(rings[-1])))
    fb.material_index = mats[121]


# --- assemble ------------------------------------------------------------------------------------

MATS = {  # name: (palette index, kwargs)
    "shell": (72, dict(metallic=0.4, roughness=0.45)),  # satin copper (metallic 0.55 read redder)
    "rim": (72, dict(metallic=0.4, roughness=0.45)),
    "groove": (69, dict(metallic=0.35, roughness=0.55)),
    "under": (68, dict(metallic=0.35, roughness=0.55)),
    "rib": (77, dict(metallic=0.2, roughness=0.55)),  # diffuse: the palette's pale shows over the shell's sheen
    "lug": (74, dict(metallic=0.4, roughness=0.42)),
    "hole": (65, dict(metallic=0.2, roughness=0.8)),
    "slot": (67, dict(metallic=0.3, roughness=0.65)),
    "bezel": (74, dict(metallic=0.45, roughness=0.38)),
    "bezel_in": (68, dict(metallic=0.4, roughness=0.5)),
}
GLOW = {  # sprite index -> (material index, emission strength); metallic 1 / rough (D126, D173)
    125: (125, 1.15),
    122: (122, 1.0),
    121: (121, 1.0),
    120: (120, 1.0),
    119: (119, 1.0),
    117: (117, 1.0),
    116: (117, 1.0),
}


def make_mats(sprite):
    names = list(MATS)
    mats = [common.palette_material(sprite, MATS[n][0], NAME + ("-rim" if n == "rim" else ""), **MATS[n][1])
            for n in names]
    I = {n: i for i, n in enumerate(names)}
    glow = {}
    made = {}
    for src, (idx, em) in GLOW.items():
        if idx not in made:
            mats.append(common.palette_material(sprite, idx, f"{NAME}-glow", metallic=1.0, roughness=0.9,
                                                emission_strength=em))
            made[idx] = len(mats) - 1
        glow[src] = made[idx]
    return mats, I, glow


def build(sprite, coll):
    mats, I, glow = make_mats(sprite)
    px = sprite["frames"][0]["pixels"]
    bm = bmesh.new()
    build_carapace(bm, I["shell"], I["rim"], I["under"], I["groove"])
    bm.normal_update()
    surf = Surface(bm)
    for pts, keep, bridge in RIBS:
        path, frames = sweep_rib(bm, surf, pts, I["rib"], keep_in=keep, bridge=bridge)
        # a low bolt on the rib's top just inside its outer (rim) end
        out_end = inset(*path[0]) > inset(*path[-1])
        k = len(frames) - 3 if out_end else 2
        rib_bolt(bm, frames[k], I["lug"])
    build_lug(bm, surf, I["lug"], I["hole"])
    build_slot(bm, surf, I["slot"])
    build_core(bm, surf, glow, I["bezel"], I["bezel_in"], px)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(38))
    return obj


def main():
    global WT
    WT = common.repo_root(__file__)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    seal = bpy.data.objects.new(f"{NAME}_seal", obj.data.copy())
    coll.objects.link(seal)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.01, faces=1500, smooth=5, inside=0.003)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(seal, do_unlink=True)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print("built", NAME, "triangles", tris, "shell faces", len(shell.data.polygons))
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
