"""assembly-newshm-45, design A (blueprint geometry first, engineering realism): the armoured dome
emplacement on the stone floor, six 2x2 pieces (newshm-45/47/49 over newshm-83/newshm-7-f2/87).

The object, read from the 72 x 56 px composite (palette 5): a low blue-steel dome (61 x 50 px plan,
centre col 36.5 row 27) standing on the fortress floor. Cross-sections first (sprite px; x = column
edge east, y = row edge south, z up; Blender = px / 12):

- Hull: a polar loft round C = (36.5, 27). The plan R(theta) is the 0.5 iso-line of the sprite's
  object mask (bilinear, holes filled), lightly smoothed, so the dome is round where the sprite is
  round and flat-sided where it has its long straight flanks (rows 22-31). Section: a 1.25 px
  vertical foot wall, a chamfered skirt flange 1.6 px wide, a small lip, then the dome body
  z = 2.35 + 9.9 (1 - t^2.1)^0.55 (t = r / (R - 1.6)): crown 12.25 px, a rounded shoulder.
- Front bay (cols 23-49, rows 34-52): cut into the hull (boolean), two sloped glacis door leaves
  (rows 34.4-45.5) and two apron leaves (the lower hatch, its lit lip at row 45.6, its nose rolling
  down to the floor on the sprite outline), split down the centre seam at col 36.5.
- Red armour (sprite components): the U yoke round the capsule (1.5 px plate over the hull,
  outline = the sprite component's iso-line: its steps as machined 45-degree chamfers), the two
  crescent fenders on the lower rim (+1 px plates rolling over the skirt to the floor; their inner
  edges are the bay's cheeks), two hinge lugs at the top corners of the bay.
- Capsule: a red pill (r 3.75) lying in the yoke, its axis inclined with the dome so it rests in
  the cradle along its length, a steel collar at its tail, a steel neck block behind it (split by
  a groove), the U interior a dark cradle plate.
- Two gun ports (bores cut 1.6 px deep, brown rims) and two louvred vents (wells cut 1.4 px deep,
  steel rim rings, curved brown blades round a hub) on the flanks, all at the sprite's centres.
- Panel seams cut 0.3 px deep: the centre split (col 36.5, rows 27.5-34.3), a shoulder ring at
  t = 0.72 on the north-west and north-east quarters, four radials from it to the skirt.
- Bolts: 14 domed heads at the blueprint's positions, dropped onto the surface by ray cast.
- Floor: the stone plate, painted in the sprite's grey tones (as lib_b073.floor), not under the dome:
  built only as an occluder for the AO bake (the dome's foot darkens where it meets the ground) and
  deleted before export (D130, as D86's dirt): the game draws the tile's ground in HD, and the plate
  showed as grey pixel cells round the dome.

Orange 118-126 streaks and the bright rims are sheen: no geometry. Underside: closed flat base only.
Outline shell (common.outline_shell, D51) from the dome only, cut per piece
without caps.

Texture: the AO/roughness bake (usp_talon.bake_maps, model bake only, no concept projection) is on by
default; -- --no-bake skips it. textures/assembly-newshm-45/maps.json says "bake": "model".

Exports the six pieces (newshm-45, 47, 49, 83, 87 and newshm-7-f2 = frame 85 of newshm-7) with
common.export_sprite_model to public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json,
each piece with its outline shell. -- --review <dir> also writes the placed whole as <dir>/whole.glb.

Run: blender -b --factory-startup -P assets/blender/enemies/assembly-newshm-45.py [-- --no-bake]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402  (base_name, sprites_with)

WT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402  (pchip, bake_maps)

NAME = "assembly-newshm-45"
TAG = "nshm45A"
HERE = Path(__file__).resolve().parent
PIECES = [["newshm-45", "newshm-47", "newshm-49"], ["newshm-83", "newshm-7-f2", "newshm-87"]]
FRAME_OF = {"newshm-7-f2": ("newshm-7", 85)}
W, H = 72, 56
LAYOUT = [(n, ci * 24 + 12 - W / 2, ri * 28 + 14 - H / 2)
          for ri, row in enumerate(PIECES) for ci, n in enumerate(row)]
OUTLINE_FACES = 2200

# --- the blueprint (sprite px) -------------------------------------------------------------------
CX, CY = 36.5, 27.0          # dome centre (object mask: cols 6-66, rows 2-51)
SK = 1.6                     # skirt width (outline -> dome body)
ZBASE, HD = 3.3, 9.0         # dome body: base and height (crown 12.3)
P_T, P_Z = 2.1, 0.55         # body profile exponents
# Foot (graft from design B): a 0.9 px base flange on the outline, a steel band 2 px high set in 0.5 px,
# then the skirt up to the dome body.  (d inward, z)
SKIRT = [(0.0, 0.7), (0.12, 0.85), (0.5, 0.9), (0.52, 2.85), (0.65, 3.0), (1.1, 3.05), (1.35, 3.2), (SK, ZBASE)]
BAND_TOP = 2.8               # fenders end on the band: their outer edge stands here
BODY_T = [0.996, 0.985, 0.965, 0.935, 0.895, 0.845, 0.78, 0.7, 0.6, 0.48, 0.34, 0.18, 0.06]
SECTORS = 80
BAY = (23.0, 49.0)           # bay cheeks (fender inner edges)
SEAM_X = 36.5
GL_TOP, GL_BOT, GL_ZBOT = 34.2, 45.6, 4.9
AP_LIP, AP_Z = 5.25, 4.7
NOSE = 3.0                   # plates roll over the rim in this many px

# --- materials --------------------------------------------------------------------------------------
FIN = {"steel": (0.55, 0.38), "red": (0.35, 0.42), "dark": (0.3, 0.6), "brown": (0.3, 0.55),
       "stone": (0.05, 0.85)}
MATS = []
_slots = {}


def M(idx, fin):
    key = (idx, fin)
    if key not in _slots:
        _slots[key] = len(MATS)
        MATS.append(key)
    return _slots[key]


HULL, SKIRTM, PANEL, APRON, NECK = M(104, "steel"), M(102, "steel"), M(102, "steel"), M(105, "steel"), M(102, "steel")
CRADLE, SEAM, BORE = M(101, "dark"), M(98, "dark"), M(4, "dark")
YOKE, CAPS, FEN_L, FEN_R, LUG = M(69, "red"), M(69, "red"), M(67, "red"), M(68, "red"), M(69, "red")
COLLAR, RIM, VRIM, HUB, BOLT = M(105, "steel"), M(165, "brown"), M(104, "steel"), M(101, "dark"), M(107, "steel")
VENT, VFLOOR = M(166, "brown"), M(165, "brown")
STONE = {i: M(i, "stone") for i in (2, 5, 8, 10)}


# --- sprite -------------------------------------------------------------------------------------

def composite():
    pix = [[-1] * W for _ in range(H)]
    cols = {}
    for ri, row in enumerate(PIECES):
        for ci, n in enumerate(row):
            base, fi = FRAME_OF.get(n, (n, None))
            d = common.load_sprite(WT, base)
            cols.update(d["colors"])
            fr = d["frames"][0] if fi is None else next(f for f in d["frames"] if f["index"] == fi)
            for r, line in enumerate(fr["pixels"]):
                for c, v in enumerate(line):
                    if v >= 0:
                        pix[ri * 28 + r][ci * 24 + c] = v
    return pix, cols


PIX, COLS = composite()


def fill_holes(m):
    h, w = len(m), len(m[0])
    out = [[1] * w for _ in range(h)]
    stack = [(r, c) for r in range(h) for c in (0, w - 1)] + [(r, c) for c in range(w) for r in (0, h - 1)]
    while stack:
        r, c = stack.pop()
        if not (0 <= r < h and 0 <= c < w) or m[r][c] or not out[r][c]:
            continue
        out[r][c] = 0
        stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    return out


OBJ = fill_holes([[1 if v >= 60 else 0 for v in row] for row in PIX])
RED_IDX = set(range(64, 79)) | set(range(118, 127)) | {162, 163, 164}


def sample(m, x, y):
    """Bilinear value of mask m (pixel centres at c + 0.5, r + 0.5) at sprite point (x, y)."""
    fx, fy = x - 0.5, y - 0.5
    c0, r0 = math.floor(fx), math.floor(fy)
    ax, ay = fx - c0, fy - r0

    def g(r, c):
        return m[r][c] if 0 <= r < len(m) and 0 <= c < len(m[0]) else 0
    return ((1 - ax) * (1 - ay) * g(r0, c0) + ax * (1 - ay) * g(r0, c0 + 1)
            + (1 - ax) * ay * g(r0 + 1, c0) + ax * ay * g(r0 + 1, c0 + 1))


def outline_radii():
    rs = []
    for k in range(360):
        th = math.radians(k)
        u = (math.cos(th), math.sin(th))
        r, last = 10.0, 10.0
        while r < 40:
            if sample(OBJ, CX + u[0] * r, CY + u[1] * r) >= 0.5:
                last = r
            r += 0.02
        rs.append(last + 0.01)
    # circular gaussian, sigma 2.5 deg
    ker = [math.exp(-0.5 * (i / 2.5) ** 2) for i in range(-8, 9)]
    s = sum(ker)
    return [sum(ker[j] * rs[(k + j - 8) % 360] for j in range(17)) / s for k in range(360)]


RS = outline_radii()


def Rf(th):
    deg = math.degrees(th) % 360
    i = int(deg)
    f = deg - i
    return RS[i % 360] * (1 - f) + RS[(i + 1) % 360] * f


def polar(x, y):
    return math.atan2(y - CY, x - CX), math.hypot(x - CX, y - CY)


def opt(th, r):
    return CX + r * math.cos(th), CY + r * math.sin(th)


def zbody(t):
    t = min(max(t, 0.0), 1.0)
    return ZBASE + HD * max(0.0, 1 - t ** P_T) ** P_Z


def Zd(x, y):
    """Hull surface height over sprite point (x, y)."""
    th, r = polar(x, y)
    R = Rf(th)
    d = R - r
    if d >= SK:
        return zbody(r / (R - SK))
    if d <= 0:
        return 0.0
    for (d0, z0), (d1, z1) in zip(SKIRT, SKIRT[1:]):
        if d <= d1:
            return z0 + (z1 - z0) * (d - d0) / max(d1 - d0, 1e-6)
    return ZBASE


def wrapz(lift, base=0.5, nose=NOSE):
    """A plate `lift` px over the dome body that rolls over the rim to `base` at the outline."""
    def f(x, y):
        th, r = polar(x, y)
        R = Rf(th)
        d = R - r
        if d >= nose:
            return zbody(r / (R - SK)) + lift
        z3 = zbody((R - nose) / (R - SK)) + lift
        if d <= 0:
            return base
        return base + (z3 - base) * math.sqrt(max(0.0, 1 - (1 - d / nose) ** 2))
    return f


def z_glacis(x, y):
    zt = Zd(x, GL_TOP) - 0.6
    s = min(max((y - GL_TOP) / (GL_BOT - GL_TOP), 0.0), 1.0)
    return zt + (GL_ZBOT - zt) * s


def z_apron(x, y):
    s = min(max((y - 46.15) / 0.45, 0.0), 1.0)
    prof = AP_LIP + (AP_Z - AP_LIP) * (s * s * (3 - 2 * s))
    th, r = polar(x, y)
    d = Rf(th) - r
    nose = 2.5
    if d < nose:
        roll = 0.5 + (AP_Z - 0.5) * math.sqrt(max(0.0, 1 - (1 - max(d, 0.0) / nose) ** 2))
        prof = min(prof, roll)
    return prof


def bay_floor(x, y):
    return z_glacis(x, y) if y <= GL_BOT else z_apron(x, y)


# --- 2D geometry ------------------------------------------------------------------------------------

def area2(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def inset(p, d):
    """Mitred inset of a CCW polygon (d > 0 inward)."""
    n, out = len(p), []
    for i in range(n):
        p0, p1, p2 = Vector(p[i - 1]), Vector(p[i]), Vector(p[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))
        bis = n0 + n1
        if bis.length < 1e-6:
            bis = n0
        bis.normalize()
        cos = max(bis.dot(n0), 0.35)
        q = p1 + bis * (d / cos)
        out.append((q.x, q.y))
    return out


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def poly_dist(x, y, P):
    return min(seg_dist(x, y, *P[i], *P[(i + 1) % len(P)]) for i in range(len(P)))


def dp_simplify(pts, tol):
    """Douglas-Peucker on a closed loop."""
    if len(pts) < 4:
        return pts
    # split at the two farthest points
    a = 0
    b = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)

    def rec(seq):
        if len(seq) < 3:
            return seq
        (ax, ay), (bx, by) = seq[0], seq[-1]
        dmax, im = -1, 0
        for i in range(1, len(seq) - 1):
            d = seg_dist(seq[i][0], seq[i][1], ax, ay, bx, by)
            if d > dmax:
                dmax, im = d, i
        if dmax <= tol:
            return [seq[0], seq[-1]]
        return rec(seq[:im + 1])[:-1] + rec(seq[im:])
    s1 = rec(pts[a:b + 1])
    s2 = rec(pts[b:] + [pts[0]])
    return s1[:-1] + s2[:-1]


def contour(mask):
    """The 0.5 iso-line of a binary pixel mask sampled at pixel centres (marching squares): straight
    along pixel edges, 45-degree cuts at steps. Returns the longest closed loop, sprite coords."""
    h, w = len(mask), len(mask[0])

    def g(r, c):
        return mask[r][c] if 0 <= r < h and 0 <= c < w else 0
    segs = []
    for r in range(-1, h):
        for c in range(-1, w):
            a, b, cc, d = g(r, c), g(r, c + 1), g(r + 1, c + 1), g(r + 1, c)  # tl tr br bl
            k = a * 8 + b * 4 + cc * 2 + d
            if k in (0, 15):
                continue
            x0, y0 = c + 0.5, r + 0.5
            T_, R_, B_, L_ = (x0 + 0.5, y0), (x0 + 1, y0 + 0.5), (x0 + 0.5, y0 + 1), (x0, y0 + 0.5)
            table = {1: [(L_, B_)], 2: [(B_, R_)], 3: [(L_, R_)], 4: [(R_, T_)], 5: [(L_, T_), (R_, B_)],
                     6: [(B_, T_)], 7: [(L_, T_)], 8: [(T_, L_)], 9: [(T_, B_)], 10: [(T_, R_), (B_, L_)],
                     11: [(T_, R_)], 12: [(R_, L_)], 13: [(R_, B_)], 14: [(B_, L_)]}
            segs += table[k]
    key = lambda p: (round(p[0] * 2), round(p[1] * 2))  # noqa: E731
    nxt = {}
    for p, q in segs:
        nxt.setdefault(key(p), []).append(q)
    loops, used = [], set()
    for p, q in segs:
        if (key(p), key(q)) in used:
            continue
        loop = [p]
        cur, prev = q, p
        used.add((key(p), key(q)))
        while key(cur) != key(p):
            loop.append(cur)
            cands = [z for z in nxt.get(key(cur), []) if (key(cur), key(z)) not in used]
            if not cands:
                break
            z = cands[0]
            used.add((key(cur), key(z)))
            prev, cur = cur, z
        loops.append(loop)
    return max(loops, key=lambda lp: abs(area2(lp)))


def comp_mask(pred, rows=None, cols=None):
    m = [[0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if (rows is None or rows[0] <= r <= rows[1]) and (cols is None or cols[0] <= c <= cols[1]) and pred(PIX[r][c], r, c):
                m[r][c] = 1
    return m


def largest_component(m):
    h, w = len(m), len(m[0])
    seen = [[0] * w for _ in range(h)]
    best = []
    for r in range(h):
        for c in range(w):
            if m[r][c] and not seen[r][c]:
                stack, comp = [(r, c)], []
                seen[r][c] = 1
                while stack:
                    a, b = stack.pop()
                    comp.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        y, x = a + da, b + db
                        if 0 <= y < h and 0 <= x < w and m[y][x] and not seen[y][x]:
                            seen[y][x] = 1
                            stack.append((y, x))
                if len(comp) > len(best):
                    best = comp
    out = [[0] * w for _ in range(h)]
    for a, b in best:
        out[a][b] = 1
    return out


# --- mesh building (sprite px; built north-up: (x, -y)) ----------------------------------------------

def to_obj(bm, name, smooth_angle=35.0, recalc=True):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((1 / 12, 0, 0, -W / 2 / 12), (0, 1 / 12, 0, H / 2 / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for idx, fin in MATS:
        me.materials.append(MATERIALS[(idx, fin)])
    obj = bpy.data.objects.new(name, me)
    COLL.objects.link(obj)
    return obj


def clean_poly(P, dmin=0.25, tol=0.06):
    """Drop near-duplicate and near-collinear points (mitred insets spike on them)."""
    if len(P) > 8:
        P = dp_simplify(P, tol)
    out = []
    for p in P:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= dmin:
            out.append(p)
    while len(out) > 3 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < dmin:
        out.pop()
    return out


def frange(a, b, step):
    out, x = [], a
    while x < b - 1e-9:
        out.append(x)
        x += step
    return out


def slab(poly, ztop, zbot, mat, side=None, bot=None, grid=1.5, chamfer=0.0, xcuts=(), ycuts=(), name="slab",
         top_mat=None):
    """A closed solid over a sprite-coords polygon: top z = ztop(x, y) (or a constant), a 45-degree
    chamfer `chamfer` px wide round its top edge, vertical walls, bottom zbot (function or constant).
    Function surfaces are subdivided on a `grid` px lattice (plus extra cut lines)."""
    P = clean_poly([(x, -y) for x, y in poly])
    if area2(P) < 0:
        P.reverse()
    bm = bmesh.new()
    outer = [bm.verts.new((x, y, 0)) for x, y in P]
    n = len(P)
    ring_faces = set()
    if chamfer > 0:
        Pin = inset(P, chamfer)
        inner = [bm.verts.new((x, y, 0)) for x, y in Pin]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
            ring_faces.add(f)
        bm.faces.new(inner)
    else:
        bm.faces.new(outer)
    fun_top, fun_bot = callable(ztop), callable(zbot)
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    lines = []
    if (fun_top or fun_bot or chamfer > 0) and grid:
        lines += [((gx, 0, 0), (1, 0, 0)) for gx in frange(math.floor(min(xs) / grid) * grid + 0.37, max(xs), grid)]
        lines += [((0, gy, 0), (0, 1, 0)) for gy in frange(math.floor(min(ys) / grid) * grid + 0.29, max(ys), grid)]
    lines += [((x, 0, 0), (1, 0, 0)) for x in xcuts] + [((0, -y, 0), (0, 1, 0)) for y in ycuts]
    for co, no in lines:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.verts.ensure_lookup_table()
    verts2 = list(bm.verts)
    vid = {v: i for i, v in enumerate(verts2)}
    xy = [(v.co.x, v.co.y) for v in verts2]
    faces2 = []
    for f in bm.faces:
        f.normal_update()
        loop = [vid[l.vert] for l in f.loops]
        if f.normal.z < 0:
            loop.reverse()
        faces2.append(loop)
    bm.free()
    # The boundary loop: the verts on each outer edge in order (robust to a self-touching inset).
    loop = []
    for k in range(n):
        (ax_, ay_), (bx_, by_) = P[k], P[(k + 1) % n]
        dx, dy = bx_ - ax_, by_ - ay_
        L2 = dx * dx + dy * dy
        on = []
        for i, (x, y) in enumerate(xy):
            t = ((x - ax_) * dx + (y - ay_) * dy) / L2
            if -1e-6 <= t < 1 - 1e-6 and abs((x - ax_) * dy - (y - ay_) * dx) / math.sqrt(L2) < 1e-4:
                on.append((t, i))
        loop += [i for t, i in sorted(on)]
    seen_ = set()
    loop = [i for i in loop if not (i in seen_ or seen_.add(i))]
    def zt(i):
        x, y = xy[i]
        z = ztop(x, -y) if fun_top else ztop
        if chamfer > 0:
            d = poly_dist(x, y, P)
            z = z - chamfer + min(d, chamfer)
        return z

    def zb(i):
        x, y = xy[i]
        return zbot(x, -y) if fun_bot else zbot
    out = bmesh.new()
    top_needed = fun_top or chamfer > 0
    bot_needed = fun_bot
    tv = {}
    bv = {}
    for i in (range(len(xy)) if top_needed else loop):
        tv[i] = out.verts.new((xy[i][0], xy[i][1], zt(i)))
    for i in (range(len(xy)) if bot_needed else loop):
        bv[i] = out.verts.new((xy[i][0], xy[i][1], zb(i)))
    side = mat if side is None else side
    bot = side if bot is None else bot
    tm = mat if top_mat is None else top_mat
    if top_needed:
        for fl in faces2:
            try:
                out.faces.new([tv[i] for i in fl]).material_index = tm
            except ValueError:
                pass
    else:
        out.faces.new([tv[i] for i in loop]).material_index = tm
    if bot_needed:
        for fl in faces2:
            try:
                out.faces.new([bv[i] for i in reversed(fl)]).material_index = bot
            except ValueError:
                pass
    else:
        out.faces.new([bv[i] for i in reversed(loop)]).material_index = bot
    for k in range(len(loop)):
        a, b = loop[k], loop[(k + 1) % len(loop)]
        try:
            out.faces.new((tv[b], tv[a], bv[a], bv[b])).material_index = side
        except ValueError:
            print("slab", name, "wall face skipped")
    return to_obj(out, name)


def ring(cx, cy, r0, r1, ztop, zbot, mat, chamfer=0.2, sides=28, name="ring"):
    """A closed annulus whose top follows ztop(x, y) (+ chamfers both edges), bottom zbot(x, y)."""
    bm = bmesh.new()
    rings = []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        ca, sa = math.cos(a), math.sin(a)
        prof = [(r0, "b"), (r0, "t-"), (r0 + chamfer, "t"), (r1 - chamfer, "t"), (r1, "t-"), (r1, "b")]
        vs = []
        for rr, kind in prof:
            x, y = cx + rr * ca, cy + rr * sa
            z = zbot(x, y) if kind == "b" else ztop(x, y) - (chamfer if kind == "t-" else 0.0)
            vs.append(bm.verts.new((x, -y, z)))
        rings.append(vs)
    for k in range(sides):
        A, B = rings[k], rings[(k + 1) % sides]
        for j in range(6):
            jj = (j + 1) % 6
            f = bm.faces.new((A[j], A[jj], B[jj], B[j]))
            f.material_index = mat
    return to_obj(bm, name)


def disc(cx, cy, r, sides=24):
    return [(cx + r * math.cos(2 * math.pi * k / sides), cy + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)]


def lathe(p0, axis, prof, mat, sides=24, name="lathe"):
    """Closed solid of revolution: prof = [(s, radius)] along the unit `axis` from p0 (sprite x, y, z);
    radius 0 at an end makes a pole."""
    ax = Vector(axis).normalized()
    ref = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 0, 1))
    u = ax.cross(ref).normalized()
    v = ax.cross(u).normalized()
    bm = bmesh.new()
    rings = []
    for s, rad in prof:
        c = Vector(p0) + ax * s
        if rad < 1e-6:
            rings.append([bm.verts.new((c.x, -c.y, c.z))])
            continue
        rv = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            p = c + (u * math.cos(a) + v * math.sin(a)) * rad
            rv.append(bm.verts.new((p.x, -p.y, p.z)))
        rings.append(rv)
    for A, B in zip(rings, rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        for k in range(sides):
            kk = (k + 1) % sides
            if len(A) == 1:
                f = bm.faces.new((A[0], B[k], B[kk]))
            elif len(B) == 1:
                f = bm.faces.new((A[k], A[kk], B[0]))
            else:
                f = bm.faces.new((A[k], A[kk], B[kk], B[k]))
            f.material_index = mat
    for R_ in (rings[0], rings[-1]):
        if len(R_) > 1:
            bm.faces.new(R_).material_index = mat
    return to_obj(bm, name)


# --- parts --------------------------------------------------------------------------------------

def build_hull():
    bm = bmesh.new()
    ths = [2 * math.pi * k / SECTORS for k in range(SECTORS)]
    prof = [("d", d, z) for d, z in [(0.0, 0.0)] + SKIRT] + [("t", t, zbody(t)) for t in BODY_T]
    rings = []
    for kind, val, z in prof:
        rv = []
        for th in ths:
            R = Rf(th)
            r = R - val if kind == "d" else val * (R - SK)
            x, y = opt(th, r)
            rv.append(bm.verts.new((x, -y, z)))
        rings.append(rv)
    pole = bm.verts.new((CX, -CY, zbody(0.0)))
    for j in range(len(rings) - 1):
        A, B = rings[j], rings[j + 1]
        for k in range(SECTORS):
            kk = (k + 1) % SECTORS
            mat = SKIRTM if j < len(SKIRT) else HULL
            bm.faces.new((A[k], A[kk], B[kk], B[k])).material_index = mat
    for k in range(SECTORS):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % SECTORS], pole)).material_index = HULL
    bm.faces.new(list(reversed(rings[0]))).material_index = SKIRTM
    return to_obj(bm, "hull")


def polar_band(th0, th1, rin, rout, step=1.0):
    """Polygon between two radius functions of theta (degrees)."""
    ks = frange(th0, th1, step) + [th1]
    outer = [opt(math.radians(k), rout(math.radians(k))) for k in ks]
    inner = [opt(math.radians(k), rin(math.radians(k))) for k in reversed(ks)]
    return outer + inner


def cutters():
    cs = []
    lo = lambda dz: (lambda x, y: Zd(x, y) - dz)  # noqa: E731
    # Front bay: hull cut down to the door leaves' bed.
    poly = [(BAY[0], GL_TOP), (BAY[1], GL_TOP), (BAY[1], 57.0), (BAY[0], 57.0)]
    cs.append(slab(poly, 30.0, lambda x, y: bay_floor(x, y) - 0.25 if y < y_out(x) - 0.8 else -1.0, SEAM, grid=2.0,
                   ycuts=[GL_BOT, 46.15, 46.6] + [47.5 + 0.5 * i for i in range(10)], name="cut_bay"))
    # Centre seam on the hull from under the yoke to the glacis.
    cs.append(slab([(SEAM_X - 0.22, 27.5), (SEAM_X + 0.22, 27.5), (SEAM_X + 0.22, GL_TOP + 0.3), (SEAM_X - 0.22, GL_TOP + 0.3)],
                   30.0, lo(0.32), SEAM, grid=1.0, name="cut_seam_c"))
    # Shoulder ring (t 0.72), north-west and north-east quarters; radials to the skirt.
    tg = 0.72
    for a0, a1 in ((174.0, 236.0), (-56.0, 6.0)):
        poly = polar_band(a0, a1, lambda th: tg * (Rf(th) - SK) - 0.22, lambda th: tg * (Rf(th) - SK) + 0.22, step=1.5)
        cs.append(slab(poly, 30.0, lo(0.3), SEAM, grid=1.2, name="cut_ring"))
    for a in (174.0, 4.0, -160.0, -20.0):
        th = math.radians(a)
        R = Rf(th)
        r0, r1 = tg * (R - SK), R - SK + 0.15
        nx, ny = -math.sin(th), math.cos(th)
        p0, p1 = opt(th, r0), opt(th, r1)
        poly = [(p0[0] + nx * 0.22, p0[1] + ny * 0.22), (p1[0] + nx * 0.22, p1[1] + ny * 0.22),
                (p1[0] - nx * 0.22, p1[1] - ny * 0.22), (p0[0] - nx * 0.22, p0[1] - ny * 0.22)]
        cs.append(slab(poly, 30.0, lo(0.3), SEAM, grid=1.0, name="cut_radial"))
    # Gun-port bores and vent wells.
    for (x, y) in PORTS:
        cs.append(slab(disc(x, y, 1.7, 20), 30.0, Zd(x, y) - 1.6, BORE, name="cut_port"))
    for (x, y, r) in VENTS:
        cs.append(slab(disc(x, y, r, 28), 30.0, Zd(x, y) - 1.4, CRADLE, name="cut_vent"))
    return cs


def ray_poly_min(th, P, rmin=5.0):
    """Smallest r > rmin where the ray from C at angle th crosses polygon P (sprite coords)."""
    ux, uy = math.cos(th), math.sin(th)
    best = None
    for i in range(len(P)):
        (ax_, ay_), (bx_, by_) = P[i], P[(i + 1) % len(P)]
        ex, ey = bx_ - ax_, by_ - ay_
        den = ux * ey - uy * ex
        if abs(den) < 1e-9:
            continue
        wx, wy = ax_ - CX, ay_ - CY
        r = (wx * ey - wy * ex) / den
        s_ = (wx * uy - wy * ux) / den
        if 0 <= s_ <= 1 and r > rmin and (best is None or r < best):
            best = r
    return best


def fender(th_range, cheek_x, mat, name, exclude):
    """A rim crescent: inner edge = the sprite red component's iso-line (simplified), outer edge just
    outside the hull outline; it rolls over the skirt to the floor."""
    m = largest_component([[1 if (PIX[r][c] in RED_IDX and OBJ[r][c] and r >= 27 and not exclude(r, c)) else 0
                            for c in range(W)] for r in range(H)])
    P = dp_simplify(contour(m), 0.3)
    ks = frange(th_range[0], th_range[1], 1.6) + [th_range[1]]
    seg = []
    for k in ks:
        th = math.radians(k)
        r = ray_poly_min(th, P)
        if r is not None and Rf(th) - r >= 0.6:
            seg.append((k, r))
    # keep the longest run of consecutive angles
    runs, cur = [], [seg[0]]
    for a_, b_ in zip(seg, seg[1:]):
        if b_[0] - a_[0] > 1.9:
            runs.append(cur)
            cur = []
        cur.append(b_)
    runs.append(cur)
    seg = max(runs, key=len)
    # Structured loft: one section per ray (inner foot, chamfered inner edge, the plate over the dome
    # rolling over the rim, outer foot), so the roll is clean quads.
    zf = wrapz(0.85, base=BAND_TOP + 0.2)
    ch, N = 0.28, 9
    secs = []
    for k, r in seg:
        th = math.radians(k)
        ix, iy = opt(th, r)
        if iy > 38.6 and abs(ix - cheek_x) < 0.6:
            ix = cheek_x
        ox, oy = opt(th, Rf(th) - 0.42)  # edge just proud of the band wall (d = 0.5)
        L_ = math.hypot(ox - ix, oy - iy)
        c_ = min(ch, 0.3 * L_)
        lerp = lambda u: (ix + (ox - ix) * u, iy + (oy - iy) * u)  # noqa: E731
        pts = [(ix, iy, 0.2), (ix, iy, zf(ix, iy) - c_)]
        u0 = c_ / L_
        for j in range(N + 1):
            u = u0 + (1 - u0) * (1 - (1 - j / N) ** 1.7)
            x, y = lerp(u)
            pts.append((x, y, zf(x, y)))
        pts.append((ox, oy, BAND_TOP - 0.3))
        secs.append(pts)
    bm = bmesh.new()
    vs = [[bm.verts.new((x, -y, z)) for x, y, z in sec] for sec in secs]
    M_ = len(vs[0])
    for A, B in zip(vs, vs[1:]):
        for j in range(M_):
            jj = (j + 1) % M_
            bm.faces.new((A[j], A[jj], B[jj], B[j])).material_index = mat
    bm.faces.new(vs[0]).material_index = mat
    bm.faces.new(list(reversed(vs[-1]))).material_index = mat
    return to_obj(bm, name)


def y_out(x):
    """The outline's south edge at column x."""
    a, b = 0.0, math.pi
    fa = opt(a, Rf(a))[0] - x
    for _ in range(50):
        m = (a + b) / 2
        fm = opt(m, Rf(m))[0] - x
        if (fm > 0) == (fa > 0):
            a, fa = m, fm
        else:
            b = m
    th = (a + b) / 2
    return opt(th, Rf(th))[1]


def apron_leaf(x0, x1, y0, ch=0.2):
    """The lower hatch leaf as a structured grid: columns across, rows from its back edge (the lip) to
    the outline, the nose rolling down to the floor; chamfered side and back edges; closed."""
    nx = max(4, int(round((x1 - x0) / 0.8)))
    us = [0.0, 0.25 * ch / (y_out(36.5) - y0), ch / (y_out(36.5) - y0)]
    us += [0.12, 0.2, 0.32, 0.45, 0.58, 0.68, 0.76, 0.83, 0.89, 0.935, 0.97, 0.99, 1.0]
    us = sorted(set(round(u, 4) for u in us))
    xs = [x0, x0 + 0.25 * ch, x0 + ch] + [x0 + ch + (x1 - x0 - 2 * ch) * i / nx for i in range(1, nx)] + [x1 - ch, x1 - 0.25 * ch, x1]
    bm = bmesh.new()
    grid = []
    for i, x in enumerate(xs):
        yo = y_out(x) + 0.1
        row = []
        for j, u in enumerate(us):
            y = y0 + (yo - y0) * u
            z = z_apron(x, y)
            ed = min(x - x0, x1 - x, (y - y0) if True else 9)
            if ed < ch:
                z -= ch - ed if ed > 0.25 * ch else ch * 0.9
            row.append(bm.verts.new((x, -y, z)))
        grid.append(row)
    nX, nY = len(xs), len(us)
    for i in range(nX - 1):
        for j in range(nY - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])).material_index = APRON
    base = 0.0
    bot = [[bm.verts.new((v.co.x, v.co.y, base)) for v in (grid[i][0], grid[i][-1])] for i in range(nX)]
    for i in range(nX - 1):  # back and front walls
        bm.faces.new((grid[i][0], bot[i][0], bot[i + 1][0], grid[i + 1][0])).material_index = APRON
        bm.faces.new((grid[i][-1], grid[i + 1][-1], bot[i + 1][1], bot[i][1])).material_index = APRON
    for i, rng in ((0, range(nY)), (nX - 1, range(nY))):  # side walls (ngons)
        vs = [grid[i][j] for j in rng] + [bot[i][1], bot[i][0]]
        bm.faces.new(vs).material_index = APRON
    bm.faces.new([bot[i][0] for i in range(nX)] + [bot[i][1] for i in reversed(range(nX))]).material_index = APRON
    return to_obj(bm, "apron")


def apron_poly(x0, x1, y0):
    def theta_for(xt, lo_, hi_):
        a, b = math.radians(lo_), math.radians(hi_)
        fa = opt(a, Rf(a))[0] - xt
        for _ in range(50):
            m = (a + b) / 2
            fm = opt(m, Rf(m))[0] - xt
            if (fm > 0) == (fa > 0):
                a, fa = m, fm
            else:
                b = m
        return (a + b) / 2
    t1, t0 = theta_for(x1, 0, 90), theta_for(x0, 90, 180)
    pts = [(x0, y0), (x1, y0)]
    n = 24
    for i in range(n + 1):
        th = t1 + (t0 - t1) * i / n
        pts.append(opt(th, Rf(th) + 0.1))
    return pts


def terraced(lift, step=2.2, y0=2.0, y1=18.0):
    """wrapz, but the yoke arms (rows < 18) step down toward the rear in risers 0.5 px long (graft from B):
    each tread holds the height of its upper edge, so it never dips into the dome."""
    base = wrapz(lift)

    def f(x, y):
        if y >= y1:
            return base(x, y)
        s_ = max(y - y0, 0.0) / step
        k = math.floor(s_)
        u = min((s_ - k) / 0.22, 1.0)
        yq = y0 + step * (k + u * u * (3 - 2 * u))
        w = min(1.0, (y1 - y) / 2.0)
        return base(x, y * (1 - w) + yq * w)
    return f


def tilt_to_surface(objs, x, y, k=0.4):
    """Tilt vent parts (built upright on the sprite's x, y) so their bores run along the dome normal."""
    e = 0.4
    nx = -(Zd(x + e, y) - Zd(x - e, y)) / (2 * e)
    ny = -(Zd(x, y + e) - Zd(x, y - e)) / (2 * e)
    n = (Vector((0, 0, 1)) * (1 - k) + Vector((nx, -ny, 1.0)).normalized() * k).normalized()
    q = Vector((0, 0, 1)).rotation_difference(n)
    P = Vector(((x - W / 2) / 12, (H / 2 - y) / 12, (Zd(x, y) - 1.0) / 12))  # about the well floor
    mat = Matrix.Translation(P) @ q.to_matrix().to_4x4() @ Matrix.Translation(-P)
    for o in objs:
        o.data.transform(mat)
        o.data.update()


def build_parts():
    parts = []
    # Yoke: the red U (sprite component), outline as machined chamfers.
    yoke_m = largest_component(comp_mask(lambda v, r, c: v in RED_IDX, rows=(2, 29), cols=(22, 50)))
    capsule_px = [[1 if (PIX[r][c] in RED_IDX and not yoke_m[r][c] and 3 <= r <= 16 and 32 <= c <= 41) else 0
                   for c in range(W)] for r in range(H)]
    ypoly = dp_simplify(contour(yoke_m), 0.3)
    parts.append(slab(ypoly, terraced(1.5), 1.0, YOKE, chamfer=0.3, grid=1.7,
                      ycuts=[2.6 + 0.5 * i for i in range(6)] + [2.0 + 2.2 * k + d for k in range(7) for d in (0.0, 0.48)],
                      name="yoke"))
    # U interior: cradle plate (rows 2-24), neck block behind the capsule.
    inter = [[0] * W for _ in range(H)]
    for r in range(2, 25):
        rc = [c for c in range(W) if yoke_m[r][c]]
        lo_, hi_ = (min(rc), max(rc)) if rc else (29, 44)
        if r < 3:
            lo_, hi_ = 28, 45
        for c in range(lo_ + 1, hi_):
            if OBJ[r][c] and not yoke_m[r][c]:
                inter[r][c] = 1
    for r in range(0, 4):
        inter[r] = [0] * W
    inter = largest_component(inter)
    cpoly = dp_simplify(contour(inter), 0.3)
    parts.append(slab(cpoly, wrapz(0.45), 1.0, CRADLE, grid=2.0, name="cradle"))
    neck_lo = [[inter[r][c] if 15 <= r <= 17 else 0 for c in range(W)] for r in range(H)]
    neck_hi = [[inter[r][c] if 18 <= r <= 24 else 0 for c in range(W)] for r in range(H)]
    crown = lambda x, y: Zd(x, y) + 1.25 + 0.55 * max(0.0, 1 - ((x - 36.5) / 5.0) ** 2)  # noqa: E731
    for nm, m_, y0, y1 in (("neck_a", neck_lo, 15.5, 17.8), ("neck_b", neck_hi, 18.2, 25.0)):
        p = dp_simplify(contour(m_), 0.3)
        p = [(x, min(max(y, y0), y1)) for x, y in p]
        q = inset([(x, -y) for x, y in (p if area2([(x, -y) for x, y in p]) > 0 else p[::-1])], 0.35)
        parts.append(slab([(x, -y) for x, y in q], crown, 2.0, NECK, chamfer=0.3, grid=1.0, name=nm))
    # Capsule: a pill resting in the cradle, axis inclined with the dome; steel collar at its tail.
    cs = [(c + 0.5, r + 0.5) for r in range(H) for c in range(W) if capsule_px[r][c]]
    ccx = sum(p[0] for p in cs) / len(cs)
    cz = wrapz(0.45)
    rad = 3.75
    yN, yT = 3.7, 16.0
    z15, z6 = cz(ccx, 15.0) + 0.6, cz(ccx, 6.3) + 0.9 - 1.6  # nose tipped down more (graft from B)
    slope = (z15 - z6) / (15.0 - 6.3)  # z rises per px south
    tail = Vector((ccx, yT, z15 + slope * (yT - 15.0)))
    ax = Vector((0, -1, -slope)).normalized()  # toward the nose (north, down)
    Lp = (yT - yN) / abs(ax.y)  # 3D length whose plan projection spans rows yN..yT
    capL = 2.7 / abs(ax.y)
    prof = [(0.0, 3.35), (0.35, rad)]
    for i in range(0, 9):
        s = Lp - capL + capL * i / 8 * 0.999
        u = (s - (Lp - capL)) / capL
        prof.append((s, rad * math.sqrt(max(0.0, 1 - u * u))))
    prof.append((Lp, 0.0))
    prof = [prof[0], prof[1]] + [(s, r) for s, r in prof[2:] if s > 0.36]
    parts.append(lathe(tail, ax, prof, CAPS, sides=28, name="capsule"))
    back = 1.8 / abs(ax.y)
    parts.append(lathe(tail - ax * back, ax, [(0.0, 0.0), (0.0001, 3.6), (0.25, 4.1), (back - 0.2, 4.4),
                                              (back + 0.25, 4.4), (back + 0.45, 3.9), (back + 0.4501, 0.0)],
                       COLLAR, sides=28, name="collar"))
    # A steel band round the capsule's waist breaks the plain cylinder (graft from B's collared pod).
    sb = Lp - capL - 2.6
    parts.append(lathe(tail, ax, [(sb, 0.0), (sb + 0.0001, rad + 0.1), (sb + 0.2, rad + 0.28), (sb + 0.75, rad + 0.28),
                                  (sb + 0.95, rad + 0.1), (sb + 0.9501, 0.0)], COLLAR, sides=28, name="band"))
    # Fenders: rim crescents from the sprite's red, their inner edges the bay cheeks.
    lugL = lambda r, c: 33 <= r <= 38 and 20 <= c <= 22  # noqa: E731
    lugR = lambda r, c: 33 <= r <= 39 and 49 <= c <= 52  # noqa: E731
    parts.append(fender((95.0, 178.0), BAY[0], FEN_L, "fender_l", lambda r, c: lugL(r, c) or c >= 36))
    parts.append(fender((2.0, 85.0), BAY[1], FEN_R, "fender_r", lambda r, c: lugR(r, c) or c < 36))
    # Hinge lugs at the bay's top corners.
    parts.append(slab([(21.0, 34.0), (23.0, 34.0), (23.0, 39.0), (21.0, 39.0)], wrapz(0.9), 2.0, LUG, chamfer=0.25,
                      grid=1.0, name="lug_l"))
    parts.append(slab([(49.0, 34.0), (52.0, 34.0), (52.0, 39.6), (49.0, 39.6)], wrapz(0.9), 2.0, LUG, chamfer=0.25,
                      grid=1.0, name="lug_r"))
    # Hinge knuckles along the bay's outer edges (hinge axis fore-aft), two per side.
    for hx in (22.0, 50.5):
        for ya, yb in ((34.6, 36.4), (36.9, 38.7)):
            ln = yb - ya
            parts.append(lathe((hx, ya, Zd(hx, ya + 1.0) + 1.15), (0, 1, 0),
                               [(0.0, 0.0), (0.0001, 0.6), (0.2, 0.92), (ln - 0.2, 0.92), (ln - 0.0001, 0.6), (ln, 0.0)],
                               LUG, sides=12, name="knuckle"))
    # Door leaves: glacis (sloped) and apron (lower hatch), split down the centre seam.
    g = 0.22
    for x0, x1 in ((BAY[0] + 0.25, SEAM_X - g), (SEAM_X + g, BAY[1] - 0.25)):
        parts.append(slab([(x0, GL_TOP + 0.25), (x1, GL_TOP + 0.25), (x1, GL_BOT - 0.15), (x0, GL_BOT - 0.15)],
                          z_glacis, 3.0, PANEL, chamfer=0.22, grid=2.0, name="glacis"))
        parts.append(apron_leaf(x0, x1, GL_BOT + 0.15))
    # Gun ports (brown rims) and vents (steel rims, brown louvres round a hub).
    for (x, y) in PORTS:
        parts.append(ring(x, y, 1.6, 2.75, lambda a, b: Zd(a, b) + 0.45, lambda a, b: Zd(a, b) - 1.0, RIM,
                          chamfer=0.18, sides=20, name="port_rim"))
    for (x, y, r) in VENTS:
        n0 = len(parts)
        zf = Zd(x, y) - 1.4
        parts.append(ring(x, y, r - 0.1, r + 0.9, lambda a, b: Zd(a, b) + 0.4, lambda a, b: Zd(a, b) - 1.2, VRIM,
                          chamfer=0.22, sides=22, name="vent_rim"))
        parts.append(slab(disc(x, y, r + 0.05, 28), zf + 0.12, zf - 0.6, VFLOOR, name="vent_floor"))
        parts.append(slab(disc(x, y, 1.1, 16), zf + 1.0, zf - 0.5, HUB, chamfer=0.2, grid=0, name="vent_hub"))
        for b in range(6):
            a0 = 2 * math.pi * b / 6 + 0.3
            pts_a, pts_b = [], []
            for i in range(5):
                rr = 1.0 + (r - 1.15) * i / 4
                a = a0 + 0.55 * i / 4
                nx, ny = -math.sin(a), math.cos(a)
                px, py = x + rr * math.cos(a), y + rr * math.sin(a)
                pts_a.append((px + nx * 0.17, py + ny * 0.17))
                pts_b.append((px - nx * 0.17, py - ny * 0.17))
            parts.append(slab(pts_a + pts_b[::-1], zf + 0.95, zf - 0.2, VENT, grid=0, name="blade"))
        tilt_to_surface(parts[n0:], x, y)  # bores along the dome normal (the sprite's narrowed ellipses)
    return parts


def vent_and_ports():
    """Centres from the sprite: vents = brown + dark well pixels on the lower flanks; ports = the
    dark bores on the upper flanks."""
    vents = []
    for c0, c1 in ((11, 21), (51, 61)):
        pts = [(c + 0.5, r + 0.5) for r in range(30, 40) for c in range(c0, c1 + 1)
               if (162 <= PIX[r][c] <= 167 or PIX[r][c] in (3, 4)) and OBJ[r][c]]
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        vents.append((x, y, math.sqrt(len(pts) / math.pi) - 0.35))
    ports = []
    for c0, c1 in ((14, 20), (53, 59)):
        pts = [(c + 0.5, r + 0.5) for r in range(11, 17) for c in range(c0, c1 + 1)
               if PIX[r][c] in (3, 4) and OBJ[r][c]]
        ports.append((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    return vents, ports


VENTS, PORTS = vent_and_ports()

BOLTS = [(27.3, 6), (27.3, 13), (45.7, 6), (45.7, 13), (31, 26.6), (42.5, 26.6), (24.8, 35.6), (48.2, 35.6),
         (24.8, 44.0), (48.2, 44.0), (9.5, 37), (13.5, 45), (63.3, 33), (59.8, 43)]


def fender_bolts():
    """Machined bolt heads along each red crescent (graft from B), 3 px in from the rim, on the sprite's red."""
    out = []
    for lo, hi in ((108, 170), (10, 72)):
        for k in range(5):
            th = math.radians(lo + (hi - lo) * k / 4)
            x, y = opt(th, Rf(th) - 3.4)
            c, r = int(x), int(y)
            if PIX[r][c] in RED_IDX and all(math.hypot(x - bx, y - by) > 3 for bx, by in BOLTS + out):
                out.append((x, y))
    return out


BOLTS += fender_bolts()


def add_bolts(body):
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(body, dg)
    bm = bmesh.new()
    for x, y in BOLTS:
        X, Y = (x - W / 2) / 12, (H / 2 - y) / 12
        hit = bvh.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        z = hit[0].z * 12 - 0.06
        nrm = hit[1]
        c = Vector((x, -y, z))
        n = Vector((nrm.x, nrm.y, nrm.z)).normalized()
        ref = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
        u = n.cross(ref).normalized()
        v = n.cross(u)
        rings = []
        for rr, hh in ((0.55, 0.0), (0.52, 0.16), (0.38, 0.3), (0.0, 0.38)):
            if rr == 0:
                rings.append([bm.verts.new(c + n * hh)])
                continue
            rings.append([bm.verts.new(c + n * hh + (u * math.cos(2 * math.pi * k / 8) + v * math.sin(2 * math.pi * k / 8)) * rr)
                          for k in range(8)])
        for A, B in zip(rings, rings[1:]):
            for k in range(8):
                kk = (k + 1) % 8
                f = bm.faces.new((A[k], A[kk], B[0]) if len(B) == 1 else (A[k], A[kk], B[kk], B[k]))
                f.material_index = BOLT
        bm.faces.new(list(reversed(rings[0]))).material_index = BOLT
    return to_obj(bm, "bolts")


def build_floor():
    """The stone plate, top painted in four grey tones from the sprite; skipped well under the dome."""
    tone = lambda i: 2 if i <= 3 else 5 if i <= 6 else 8 if i <= 9 else 10  # noqa: E731
    # distance (px) inside the object mask
    inside = [[0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if OBJ[r][c]:
                d = 0
                while d < 4 and all(0 <= r + a < H and 0 <= c + b < W and OBJ[r + a][c + b]
                                    for a in range(-d - 1, d + 2) for b in range(-d - 1, d + 2)):
                    d += 1
                inside[r][c] = d + 1
    bm = bmesh.new()
    top = 0.36
    for r in range(H):
        c = 0
        while c < W:
            if inside[r][c] > 2:
                c += 1
                continue
            t = tone(PIX[r][c]) if not OBJ[r][c] else 5
            e = c + 1
            while e < W and inside[r][e] <= 2 and (tone(PIX[r][e]) if not OBJ[r][e] else 5) == t:
                e += 1
            vs = [bm.verts.new((x, -y, top)) for x, y in ((c, r + 1), (e, r + 1), (e, r), (c, r))]
            bm.faces.new(vs).material_index = STONE[t]
            c = e
    # base block under it (top just below the paint)
    vs = [bm.verts.new((x, -y, z)) for z in (0.0, top - 0.004) for x, y in ((0, H), (W, H), (W, 0), (0, 0))]
    for a, b, cc, d in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new((vs[a], vs[b], vs[cc], vs[d])).material_index = STONE[5]
    bm.normal_update()
    ctr = Vector((W / 2, -H / 2, top / 2))
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median() - ctr) < 0:
            f.normal_flip()
    return to_obj(bm, "floor", recalc=False)


# --- assembly ------------------------------------------------------------------------------------

def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


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


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def smooth(o, angle=35.0):
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(angle))
    wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(o)


def main():
    global COLL, MATERIALS
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    COLL = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": COLS}
    MATERIALS = {}
    for idx, fin in MATS:
        met, rough = FIN[fin]
        MATERIALS[(idx, fin)] = common.palette_material(sprite, idx, f"{TAG}_{fin}", metallic=met, roughness=rough)

    hull = build_hull()
    cs = cutters()
    cc = bpy.data.collections.new(f"{NAME}_cutters")
    for c in cs:
        COLL.objects.unlink(c)
        cc.objects.link(c)
    bpy.context.scene.collection.children.link(cc)
    mod = hull.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.operand_type = "COLLECTION"
    mod.collection = cc
    mod.material_mode = "INDEX"
    common._apply_modifiers(hull)
    for c in cs:
        bpy.data.objects.remove(c, do_unlink=True)
    print(f"{NAME}: hull {tris(hull)} triangles after cuts")
    parts = build_parts()
    from collections import Counter
    cnt = Counter()
    for o in parts:
        cnt[o.name.split(".")[0]] += tris(o)
    print(f"{NAME}: parts", dict(cnt))
    body = join([hull] + parts, "body")
    bolts = add_bolts(body)
    body = join([body, bolts], "body")
    print(f"{NAME}: body {tris(body)} triangles; vents {VENTS}; ports {PORTS}")
    floor = build_floor()
    print(f"{NAME}: floor {tris(floor)} triangles")

    fmt = "AUTO"
    whole = join([body, floor], "whole")
    if "--no-bake" not in argv:
        T.TINT, tex = (1.0, 1.0, 1.0), T.TEXTURED
        T.TEXTURED = tuple(range(len(MATS)))
        try:
            T.bake_maps(whole, tempfile.mkdtemp(prefix="nshm45A_bake_"), size=2048, samples=64)
        finally:
            T.TEXTURED = tex
        fmt = "WEBP"
    # outline shell from the dome only (the floor plate is not inked)
    dome_only = whole.copy()
    dome_only.data = whole.data.copy()
    COLL.objects.link(dome_only)
    bm = bmesh.new()
    bm.from_mesh(dome_only.data)
    stone_slots = set(STONE.values())
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in stone_slots], context="FACES")
    bm.to_mesh(dome_only.data)
    bm.free()
    shell = common.outline_shell(dome_only, COLL, voxel=0.016, faces=OUTLINE_FACES)
    shell.hide_render = True
    bpy.data.objects.remove(dome_only, do_unlink=True)
    # the floor plate was the bake's occluder only: it is not exported (D130)
    bm = bmesh.new()
    bm.from_mesh(whole.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in stone_slots], context="FACES")
    bm.to_mesh(whole.data)
    bm.free()

    pieces = common.split_assembly(whole, LAYOUT, COLL)
    shells = split_open(shell, LAYOUT, COLL)
    whole.hide_render = True
    total = 0
    placed = []
    for name, cx, cy in LAYOUT:
        p, sh = pieces[name], shells[name]
        p.name = name
        smooth(p)
        sh.data.materials.clear()
        sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
        t, ts = tris(p), tris(sh)
        total += t
        print(f"{NAME}: piece {name}: {t} triangles, outline {ts}")
        base = L.base_name(name)
        sprites = common.load_sprite(WT, name)["sprites"] if name not in FRAME_OF else \
            L.sprites_with(WT, base, [FRAME_OF[name][1]])
        # in piece space (the piece centre is the origin and the pivot), as run_assembly exports them
        common.export_sprite_model(WT, [p, sh], f"enemies/{name}", sprites, image_format=fmt)
        placed.append((p, sh, cx, cy))
    print(f"{NAME}: total {total} triangles (shells excluded), shell {tris(shell)}")
    if "--review" in argv:  # review only: the six pieces placed side by side, one glb
        out = Path(argv[argv.index("--review") + 1])
        export = []
        for p, sh, cx, cy in placed:
            for o in (p, sh):
                o.location = (cx / 12, -cy / 12, 0)
                export.append(o)
        common.export_glb(export, out / "whole.glb", image_format=fmt)
        print(f"{NAME}: review glb {out / 'whole.glb'}")


if __name__ == "__main__":
    main()
