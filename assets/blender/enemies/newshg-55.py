"""newshg-55, the purple dome bunker (newshg.shp size 2, frame 55, 24 x 28 block, drawing in its
top 20 rows), design A: a hard-surface emplacement that is its sprite in 3D (D65, D120, D130).

WHAT IT IS: a fixed armoured bunker (GYGES terrain-fixed top layer x3, MISTAKES ground layer
moving only at the scroll rate): it stands on the HD ground at z 0 with no floor plate (D130).
Front = down the screen (toward the player and the tilted game camera).

Reading the sprite (pixel col/row; edges in px; palette index = trimmed median of the region):
- Carapace dome (cols 6-16, rows 1-7, pal 88): a ribbed shell, two raised ribs (cols 9 and 13,
  pal 91; the 93 spots are sheen) that splay out to the brow corners (cols 7/15, row 8), a seam
  down the middle (col 11, pal 87).
- Brow (row 7-8): the carapace's front lip; under it the face plate (rows 8-12, pal 83, the
  dome's south slope) with three small red lights in a triangle (row 9 col 11, row 10 cols 10/12,
  pal 67).
- Shoulders (cols 1-4 / 18-21, rows 3-16, pal 87): a curved armour fender each side, pointed at
  the rear (the spike at row 3-4), its lit crest along col 3 / 19, running forward down onto
  the foot.
- Groove between fender and dome (cols 5 / 17, pal 83): the body deck seen low.
- Feet (rows 13-18, pal 82): two heavy front buttresses with a notch between (cols 10-12, rows
  16-19); light cheek ridges (cols 7 / 15, rows 13-15, pal 86) frame the lamp.
- Blue light (rows 13-15, cols 9-13, pal 147): a round lens in a dark socket under the face,
  a small fin (row 13 col 11, pal 87) over its middle.

Built: body hull (battered wall, chamfered deck) from a faired outline fitted to the inner mask
(D74), a carapace dome whose rings meet the brow exactly (the face is recessed behind a lip and a
bead), swept ribs, arch-section fenders with modelled panel lines, raised foot plates, lamp
socket, lens and fin. Outline shell from a sealed pre-cull copy (D51/D90/D118); hidden faces
culled. No textures/newshg-55 folder, so no maps (AO/roughness bake not wired: no "bake").

    blender -b --factory-startup --python assets/blender/enemies/newshg-55.py
"""

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
MODEL = f"enemies/{"newshg-55"}"

NAME = "newshg-55"
PX = 1 / 12
AX = 11.5  # mirror axis (pixel edges)


def bl(x, y, z):
    """Sprite px (column edge, row edge, height) to Blender units (24 x 28 block, centred)."""
    return Vector(((x - 12) * PX, (14 - y) * PX, z * PX))


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# --- curves ------------------------------------------------------------------------------------

def catmull(pts, per=10):
    """Closed centripetal-ish Catmull-Rom through pts, `per` samples per span."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = (Vector(pts[(i + k) % n]) for k in (-1, 0, 1, 2))
        for s in range(per):
            t = s / per
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(q)
    return out


def resample(poly, n):
    """Closed polyline resampled to n points evenly by arc length."""
    segs = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    lens = [(b - a).length for a, b in segs]
    total = sum(lens)
    out, acc, j = [], 0.0, 0
    for k in range(n):
        s = total * k / n
        while acc + lens[j] < s:
            acc += lens[j]
            j += 1
        a, b = segs[j]
        t = (s - acc) / max(1e-9, lens[j])
        out.append(a.lerp(b, t))
    return out


def ccw(poly):
    """Make a closed 2D loop counter-clockwise in Blender's frame (y up = image y flipped):
    in image coords (y down) that is clockwise, signed area < 0 with the shoelace on (x, y)."""
    a = sum(p.x * q.y - q.x * p.y for p, q in zip(poly, poly[1:] + poly[:1]))
    return poly if a > 0 else poly[::-1]


def offset(poly, d):
    """Inset a closed loop (image coords) by d px (positive = inward)."""
    n = len(poly)
    a = sum(p.x * q.y - q.x * p.y for p, q in zip(poly, poly[1:] + poly[:1]))
    sgn = 1 if a > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        t = (p2 - p0)
        t.normalize()
        nrm = Vector((-t.y, t.x)) * sgn  # inward for this orientation
        out.append(p1 + nrm * d)
    return out


def mirror_pts(left):
    """Left-half control points (rear centre to front centre) -> full closed loop."""
    right = [(2 * AX - x, y) for x, y in reversed(left)]
    return left + right


# --- the body hull -----------------------------------------------------------------------------

# Left half of the body's footprint (pixel edges): rear centre, round the shoulder, down the side,
# the foot, into the notch between the feet. Fitted to the inner mask (D74).
BODY_L = [(11.5, 4.9), (7.5, 4.9), (5.2, 5.0), (3.5, 5.35), (2.35, 6.3), (1.35, 7.3), (1.0, 8.6), (1.0, 11.2),
          (1.75, 12.45), (1.0, 13.4), (1.0, 15.5), (1.75, 16.95), (2.9, 18.05), (3.8, 18.85), (6.5, 18.95), (9.0, 18.85),
          (9.5, 18.35), (9.6, 17.0), (10.4, 16.15)]
NB = 160


def body_loop():
    pts = catmull(mirror_pts(BODY_L), per=12)
    return resample(pts, NB)


def hscale(y):
    """Body height factor: full behind row 12, falling to 0.8 at the feet's front."""
    return 1.0 - 0.2 * smooth01((y - 12.0) / 7.0)


Z_DECK = 2.1


def build_body(bm, m_wall, m_deck, m_line):
    loop = body_loop()
    prof = [  # inset px, z, material of the band above this ring
        (0.0, 0.0, None), (0.0, 0.3, m_wall), (0.28, 0.85, m_wall), (0.36, 0.9, m_line), (0.42, 1.08, m_line),
        (0.42, 1.12, m_wall), (0.62, 1.6, m_wall), (0.9, 1.95, m_deck), (1.3, Z_DECK, m_deck)]
    rings = []
    for inset, z, _ in prof:
        lp = offset(loop, inset) if inset else loop
        rings.append([bm.verts.new(bl(p.x, p.y, z * hscale(p.y))) for p in lp])
    for i in range(len(rings) - 1):
        for k in range(NB):
            m = (k + 1) % NB
            f = bm.faces.new((rings[i][k], rings[i][m], rings[i + 1][m], rings[i + 1][k]))
            f.material_index = prof[i + 1][2]
    top = bm.faces.new(rings[-1])
    top.material_index = m_deck
    bot = bm.faces.new(list(reversed(rings[0])))
    bot.material_index = m_wall
    bmesh.ops.triangulate(bm, faces=[top, bot])


def deck_z(x, y):
    return Z_DECK * hscale(y)


# --- the carapace dome -------------------------------------------------------------------------

DC = (11.5, 7.15)                    # footprint centre
DRX, DRN, DRS, DN = 5.55, 6.0, 5.9, 2.05  # half-width, north / south half-length, superellipse power
PEAK = (11.5, 5.4)
ZB, HD = 1.5, 5.0                    # dome base height, height above it
NT, NR, NF = 128, 18, 7              # rays, carapace rings, face rings
FACE_DEPTH = 0.42                    # the face plate's recess behind the brow lip


def in_dome(x, y):
    ry = DRN if y < DC[1] else DRS
    return abs((x - DC[0]) / DRX) ** DN + abs((y - DC[1]) / ry) ** DN < 1


def brow_y(x):
    """The brow line: the carapace's front lip (row 7 in the middle, curving down to row ~10 at
    the dome's sides)."""
    return 6.95 + 0.115 * (x - AX) ** 2


def ray_len(inside, src, ang, hi=20.0):
    dx, dy = math.cos(ang), math.sin(ang)
    lo = 0.0
    for _ in range(40):
        m = (lo + hi) / 2
        if inside(src[0] + dx * m, src[1] + dy * m):
            lo = m
        else:
            hi = m
    return lo


def dome_h(d):
    """Height profile over normalised distance d from the peak to the footprint edge."""
    return ZB + HD * max(0.0, 1 - d ** 2.1) ** 0.55


def ray_brow(ang, de):
    """Distance along the ray from PEAK to the brow (or de if the ray never crosses it)."""
    dx, dy = math.cos(ang), math.sin(ang)
    f = lambda t: (PEAK[1] + dy * t) - brow_y(PEAK[0] + dx * t)  # noqa: E731
    if f(de) <= 0:
        return de
    lo, hi = 0.0, de
    for _ in range(40):
        m = (lo + hi) / 2
        if f(m) > 0:
            hi = m
        else:
            lo = m
    return lo


_RAYS = {}


def rays():
    if not _RAYS:
        for k in range(NT):
            a = 2 * math.pi * k / NT
            de = ray_len(in_dome, PEAK, a)
            db = ray_brow(a, de)
            _RAYS[k] = (a, de, db)
    return _RAYS


def dome_z(x, y):
    """Height of the carapace (not the recessed face) over (x, y); None outside the footprint."""
    if not in_dome(x, y):
        return None
    a = math.atan2(y - PEAK[1], x - PEAK[0])
    de = ray_len(in_dome, PEAK, a)
    return dome_h(math.hypot(x - PEAK[0], y - PEAK[1]) / de)


def face_z(x, y):
    z = dome_z(x, y)
    return None if z is None else z - FACE_DEPTH


def build_dome(bm, m_shell, m_seam, m_face, m_skirt):
    R = rays()
    vr = []  # rings of verts: carapace rings, then face rings, then the skirt to z 0
    mats_band = []
    lip_w = 0.14
    for j in range(1, NR + 1):
        t = j / NR
        ring = []
        for k in range(NT):
            a, de, db = R[k]
            real = de - db > 0.05
            dbx = db if real else de
            r = dbx * t
            x, y = PEAK[0] + r * math.cos(a), PEAK[1] + r * math.sin(a)
            z = dome_h(r / de)
            # the seam down the middle (col 11): a modelled V groove on the rays at +-90 deg
            if abs(x - AX) < 0.05 and y < brow_y(x) - 0.3:
                z -= 0.16 * smooth01(min(r, dbx - r) / 0.6)
            ring.append((x, y, z))
        vr.append(ring)
        mats_band.append(None)
    # face rings: first the lip drop (just past the brow), then down the face to the edge
    for j in range(NF + 1):
        ring = []
        for k in range(NT):
            a, de, db = R[k]
            real = de - db > 0.05
            depth = FACE_DEPTH * smooth01((de - db) / 0.8) if real else 0.0
            if j == 0:
                r = min(db + lip_w, de) if real else de
            else:
                r = db + lip_w + (de - db - lip_w) * j / NF if real and de - db > lip_w else de
            x, y = PEAK[0] + r * math.cos(a), PEAK[1] + r * math.sin(a)
            z = dome_h(min(1.0, r / de)) - depth
            ring.append((x, y, z))
        vr.append(ring)
    # skirt: straight down from the edge into the deck
    vr.append([(x, y, 0.4) for x, y, _ in vr[-1]])
    nring = len(vr)
    verts = [[bm.verts.new(bl(*p)) for p in r] for r in vr]
    pole = bm.verts.new(bl(PEAK[0], PEAK[1], dome_h(0)))

    def is_face(k, j):
        a, de, db = R[k]
        return de - db > 0.05 and j >= NR

    seam_k = {k for k in range(NT) if abs(math.cos(R[k][0])) < 0.03}
    for k in range(NT):
        m = (k + 1) % NT
        f = bm.faces.new((pole, verts[0][k], verts[0][m]))
        f.material_index = m_shell
    for i in range(nring - 1):
        for k in range(NT):
            m = (k + 1) % NT
            f = bm.faces.new((verts[i][k], verts[i + 1][k], verts[i + 1][m], verts[i][m]))
            if i == nring - 2:
                f.material_index = m_skirt
            elif is_face(k, i + 1) and is_face(m, i + 1) and i + 1 > NR:
                f.material_index = m_face
            elif i + 1 == NR and is_face(k, i + 1) and is_face(m, i + 1):
                f.material_index = m_face  # the lip's drop face, in shadow under the brow
            elif (k in seam_k or m in seam_k) and i < NR - 1:
                f.material_index = m_seam
            else:
                f.material_index = m_shell
    bot = bm.faces.new([verts[-1][k] for k in range(NT)][::-1])
    bot.material_index = m_skirt
    bmesh.ops.triangulate(bm, faces=[bot])


# --- swept parts -------------------------------------------------------------------------------

def loft(bm, rings, mat, cap=True):
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in rings]
    faces = []
    for r0, r1 in zip(vr, vr[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    if cap:
        for r, flip in ((vr[0], True), (vr[-1], False)):
            c = bm.verts.new(sum((v.co for v in r), Vector()) / len(r))
            n = len(r)
            for i in range(n):
                j = (i + 1) % n
                faces.append(bm.faces.new((r[j], r[i], c) if flip else (r[i], r[j], c)))
    for f in faces:
        f.material_index = mat
    return faces


def sweep(bm, mat, path, sides=8, n=3.0):
    """A tube through path [(x, y, z, half_w, half_h)] px, sections upright."""
    pts = [Vector(p[:3]) for p in path]
    N = len(path)
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-6:
            t = Vector((0, 1, 0))
        t.normalize()
        side = Vector((-t.y, t.x, 0))
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            q = Vector((x, y, z)) + side * (w * spow(math.cos(a), 2 / n)) + Vector((0, 0, h * spow(math.sin(a), 2 / n)))
            ring.append(tuple(q))
        rings.append(ring)
    return loft(bm, rings, mat)


def pchip_path(stations, step):
    """Interpolate station tuples (first value = parameter) with pchip per column."""
    ys = [s[0] for s in stations]
    cols = list(zip(*stations))
    fs = [T.pchip(ys, list(c)) for c in cols[1:]]
    out = []
    y = ys[0]
    while y < ys[-1] - 1e-6:
        out.append((y, *[f(y) for f in fs]))
        y += step
    out.append((ys[-1], *[f(ys[-1]) for f in fs]))
    return out


def surf_z(x, y):
    zs = [deck_z(x, y)]
    d = dome_z(x, y)
    if d is not None:
        zs.append(d if y < brow_y(x) else d - FACE_DEPTH)
    return max(zs)


def build_ribs(bm, m_rib, m_bead):
    """The carapace's two ribs (cols 9 / 13) from the crown to the brow corners, and the brow bead
    along the lip."""
    for side in (-1, 1):
        st = [(1.9, 1.1, 0.0, 0.16), (2.8, 1.85, 0.22, 0.2), (4.2, 2.05, 0.36, 0.26), (5.6, 2.1, 0.4, 0.28),
              (6.8, 2.55, 0.38, 0.26), (7.75, 3.45, 0.3, 0.2)]
        path = []
        for y, dx, w, h in pchip_path(st, 0.18):
            x = AX - side * dx if side < 0 else AX + dx
            x = AX + side * dx
            z = dome_z(x, y) or ZB
            path.append((x, y, z - 0.05, max(w, 0.05), max(h, 0.05)))
        sweep(bm, m_rib, path, sides=8, n=2.4)
    # brow bead: along the lip from one side to the other
    path = []
    xs = [AX - 4.9 + 0.1 * i for i in range(99)]
    for x in xs:
        y = brow_y(x)
        z = dome_z(x, y - 0.02)
        if z is None:
            continue
        taper = smooth01((4.9 - abs(x - AX)) / 0.9)
        path.append((x, y - 0.05, z - 0.02, 0.27 * taper + 0.03, 0.22 * taper + 0.03))
    sweep(bm, m_bead, path, sides=8, n=2.2)


def build_lights(bm, m_red, m_bezel):
    """Three small red lights in a triangle on the face plate (row 9 col 11, row 10 cols 10, 12)."""
    seg = 12
    for cx, cy in ((11.5, 9.45), (10.45, 10.5), (12.55, 10.5)):
        z0 = face_z(cx, cy)
        # bezel ring
        rings = []
        for r, dz in ((0.55, -0.15), (0.55, 0.12), (0.44, 0.16), (0.38, 0.06)):
            rings.append([(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg),
                           z0 + dz) for k in range(seg)])
        loft(bm, rings, m_bezel)
        # lens: a low dome
        rings = []
        for i in range(4):
            th = (math.pi / 2) * i / 4
            r = 0.38 * math.cos(th)
            rings.append([(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg),
                           z0 + 0.02 + 0.2 * math.sin(th)) for k in range(seg)])
        rings.append([(cx + 0.02 * math.cos(2 * math.pi * k / seg), cy + 0.02 * math.sin(2 * math.pi * k / seg),
                       z0 + 0.22) for k in range(seg)])
        loft(bm, rings, m_red)


def arch_ring(xc, y, h, wo, wi, side, nseg=14, n=2.6, scale=1.0):
    """An arch section across x at row y: from the outer foot over the crest to the inner foot.
    side -1 = left fender (outer is -x)."""
    pts = []
    for i in range(nseg + 1):
        a = math.pi * i / nseg  # 0 outer foot, pi inner foot
        c, s = math.cos(a), math.sin(a)
        w = wo if c > 0 else wi
        x = xc + side * spow(c, 2 / n) * w * scale
        z = h * scale * spow(s, 2 / n)
        pts.append((x, y, z))
    return pts


def build_fenders(bm, m_fender, m_line):
    """The curved shoulder armour each side (cols 1-4), pointed at the rear, crest along col 3,
    running forward onto the foot. Panel lines are modelled as narrow waists in the loft."""
    st = [  # y, crest x (left), crest height, outer half-width, inner half-width
        (3.85, 3.5, 1.6, 0.12, 0.12), (4.5, 3.5, 2.6, 0.4, 0.7), (5.5, 3.45, 3.5, 0.6, 1.25),
        (6.8, 3.4, 4.1, 1.95, 1.6), (8.5, 3.4, 4.3, 2.35, 1.65), (10.5, 3.5, 4.05, 2.4, 1.5),
        (12.2, 3.75, 3.4, 1.95, 1.35), (13.8, 3.9, 2.85, 2.0, 1.1), (15.6, 4.0, 2.45, 1.2, 0.85),
        (16.9, 4.05, 2.0, 0.35, 0.35)]
    lines = (7.6, 11.4, 14.6)
    for side in (-1, 1):
        rings, bands = [], []
        path = pchip_path(st, 0.2)
        ys = sorted({p[0] for p in path} | {l + d for l in lines for d in (-0.09, -0.03, 0.03, 0.09)})
        fs = [T.pchip([s[0] for s in st], [s[i] for s in st]) for i in range(1, 5)]
        for y in ys:
            xc, h, wo, wi = (f(y) for f in fs)
            if side > 0:
                xc = 2 * AX - xc
            sc = 1.0
            for l in lines:
                if abs(y - l) < 0.06:
                    sc = 0.93
            rings.append(arch_ring(xc, y, h, max(wo, 0.05), max(wi, 0.05), side, scale=sc))
        # close each section along its bottom: arch ring is open (feet at z 0); make a closed ring
        closed = [r + [(r[-1][0], r[-1][1], -0.02), (r[0][0], r[0][1], -0.02)] for r in rings]
        faces = loft(bm, closed, m_fender)
        # panel line waists get the line material
        nper = len(closed[0])
        for idx, y in enumerate(ys[:-1]):
            if any(abs(y - l) < 0.1 and abs(ys[idx + 1] - l) < 0.1 for l in lines):
                for q in range(nper):
                    faces[idx * nper + q].material_index = m_line


def build_struts(bm, m_strut, m_boss):
    """Tie rods across the groove from each fender's inner flank to the dome's skirt (rows 6.2 and
    11.0): the fender is a separate armour plate held off the dome (the sprite's gap at row 9)."""
    for side in (-1, 1):
        for y, z in ((6.3, 2.9), (11.1, 2.7)):
            x0, x1 = 4.4, 6.9
            if side > 0:
                x0, x1 = 2 * AX - x0, 2 * AX - x1
            path = [(x0 + (x1 - x0) * i / 6, y, z, 0.2, 0.2) for i in range(7)]
            sweep(bm, m_strut, path, sides=8, n=2.0)
            for x in (x0, x1):
                sweep(bm, m_boss, [(x - 0.01, y - 0.3, z, 0.36, 0.36), (x + 0.01, y + 0.3, z, 0.36, 0.36)][::1],
                      sides=10, n=2.0)


def build_feet(bm, m_plate, m_cheek, m_line):
    """Raised armour plates on the two feet (rows 13-18) and the cheek ridges (cols 7 / 15) that
    frame the lamp socket."""
    plate_l = [(2.1, 12.9), (5.0, 12.75), (7.7, 12.9), (8.25, 13.7), (8.35, 15.9), (9.2, 17.3), (9.15, 18.2),
               (6.5, 18.35), (4.0, 18.25), (2.7, 17.4), (1.9, 16.0), (1.75, 14.0)]
    for side in (-1, 1):
        pts = plate_l if side < 0 else [(2 * AX - x, y) for x, y in plate_l]
        loop = resample(catmull(pts, per=10), 72)
        rings = []
        for inset, dz in ((0.0, -0.3), (0.0, 0.18), (0.18, 0.36), (0.32, 0.4)):
            lp = offset(loop, inset) if inset else loop
            rings.append([(p.x, p.y, deck_z(p.x, p.y) + dz) for p in lp])
        faces = loft(bm, rings, m_plate)
        # cheek ridge: the plate's inner edge raised as a rounded bead (col 7 / 15, rows 12.8-16.2)
        cx = 7.95 if side < 0 else 2 * AX - 7.95
        path = []
        for y in [12.7 + 0.25 * i for i in range(15)]:
            taper = smooth01((y - 12.6) / 0.6) * smooth01((16.3 - y) / 0.7)
            path.append((cx, y, deck_z(cx, y) + 0.38, 0.12 + 0.4 * taper, 0.05 + 0.32 * taper))
        sweep(bm, m_cheek, path, sides=8, n=2.6)
        # two transverse panel lines across the plate (rows 15.2, 17.0): shallow raised strips
        for y, x0, x1 in ((15.0, 2.3, 7.7), (16.9, 3.0, 8.6)):
            if side > 0:
                x0, x1 = 2 * AX - x1, 2 * AX - x0
            path = [(x0 + (x1 - x0) * i / 8, y, deck_z(0, y) + 0.4, 0.07, 0.04) for i in range(9)]
            sweep(bm, m_line, path, sides=6, n=2.0)


def build_lamp(bm, m_lens, m_sock, m_fin):
    """The blue light: a round lens (centre col 11.5, row 14.5) in a dark socket ring, a fin over
    its middle hanging from under the face plate."""
    cx, cy = 11.5, 14.55
    seg = 32
    zd = deck_z(cx, cy)
    # socket collar (dark), a ring proud of the deck round the lens
    def ell(rx, ry, z):
        return [(cx + rx * math.cos(2 * math.pi * k / seg), cy + ry * math.sin(2 * math.pi * k / seg), z)
                for k in range(seg)]
    loft(bm, [ell(3.05, 1.95, zd - 0.3), ell(3.05, 1.95, zd + 0.25), ell(2.85, 1.8, zd + 0.42),
              ell(2.6, 1.62, zd + 0.38), ell(2.5, 1.55, zd - 0.1)], m_sock)
    # lens: an ellipsoid cap
    rings = []
    for i in range(7):
        th = (math.pi / 2) * i / 7
        rings.append(ell(2.48 * math.cos(th), 1.55 * math.cos(th), zd + 0.1 + 1.15 * math.sin(th)))
    rings.append(ell(0.03, 0.03, zd + 1.25))
    loft(bm, rings, m_lens)
    # the fin over the lens's middle (row 13 col 11): a thin blade sloping down from the face
    y0 = 12.5
    fz0 = surf_z(cx, y0)
    blade = []
    for i in range(6):
        t = i / 5
        y = y0 + 1.45 * t
        ztop = fz0 * (1 - t) + (zd + 1.15) * t
        blade.append((cx, y, ztop - 0.25, 0.2, 0.3))
    sweep(bm, m_fin, blade, sides=6, n=2.4)


def build_rear(bm, m_vent, m_line):
    """A louvre on the carapace's back skirt and studs on the deck behind the dome (rear detail)."""
    for k in range(5):
        x = AX - 1.6 + 0.8 * k
        y = 5.3 - 0.0
        zt = (dome_z(x, 2.6) or ZB) - 0.1
        loft(bm, [[(x - 0.22, yy, z) for yy, z in ((2.2, zt - 0.6), (2.2, zt), (2.9, zt), (2.9, zt - 0.6))],
                  [(x + 0.22, yy, z) for yy, z in ((2.2, zt - 0.6), (2.2, zt), (2.9, zt), (2.9, zt - 0.6))]], m_vent)


# --- assemble ----------------------------------------------------------------------------------

MATS = {  # name: (palette index, kwargs)
    "shell": (88, dict(metallic=0.15, roughness=0.34)),
    "seam": (87, dict(metallic=0.15, roughness=0.42)),
    "rib": (91, dict(metallic=0.2, roughness=0.3)),
    "bead": (89, dict(metallic=0.2, roughness=0.32)),
    "face": (83, dict(metallic=0.2, roughness=0.45)),
    "fender": (87, dict(metallic=0.15, roughness=0.34)),
    "fline": (84, dict(metallic=0.2, roughness=0.5)),
    "deck": (83, dict(metallic=0.1, roughness=0.75)),
    "wall": (82, dict(metallic=0.1, roughness=0.75)),
    "line": (81, dict(metallic=0.2, roughness=0.65)),
    "plate": (82, dict(metallic=0.1, roughness=0.8)),
    "cheek": (86, dict(metallic=0.45, roughness=0.38)),
    "sock": (81, dict(metallic=0.3, roughness=0.6)),
    "fin": (87, dict(metallic=0.45, roughness=0.38)),
    "bezel": (82, dict(metallic=0.4, roughness=0.45)),
    "skirt": (84, dict(metallic=0.4, roughness=0.5)),
}
GLOW = {"red": 67, "lens": 147}  # emission 1: the palette colour unlit (D126); metallic 1 rough 0.9 (D173)


def make_mats(sprite):
    names = list(MATS)
    mats = [common.palette_material(sprite, MATS[n][0], NAME, **MATS[n][1]) for n in names]
    for n, idx in GLOW.items():
        mats.append(common.palette_material(sprite, idx, f"{NAME}-{n}", metallic=1.0, roughness=0.9,
                                            emission_strength=1.0))
        names.append(n)
    return mats, {n: i for i, n in enumerate(names)}


def build(sprite, coll):
    mats, I = make_mats(sprite)
    bm = bmesh.new()
    build_body(bm, I["wall"], I["deck"], I["line"])
    build_dome(bm, I["shell"], I["seam"], I["face"], I["skirt"])
    build_ribs(bm, I["rib"], I["bead"])
    build_lights(bm, I["red"], I["bezel"])
    build_fenders(bm, I["fender"], I["fline"])
    build_feet(bm, I["plate"], I["cheek"], I["line"])
    build_struts(bm, I["cheek"], I["fline"])
    build_lamp(bm, I["lens"], I["sock"], I["fin"])
    build_rear(bm, I["seam"], I["line"])
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(40))
    return obj


def main():
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
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])


if __name__ == "__main__":
    main()
