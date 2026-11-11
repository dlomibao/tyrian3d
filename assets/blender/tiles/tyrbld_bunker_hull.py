"""The armoured hull bunker on TYRIAN's ground (map 1-9, layer 0; tiles 322 323 / 332 333, three
copies; every cell under the grey carapace bunker enemy assembly-newsh2-119, so this model shows once
that enemy is shot and stays under ENEMY_MAX 0.38; the tiles stay drawn, keepTiles).

What the art paints (48 x 56 px, read pixel by pixel): a near-black machine bed sunk in the dirt;
on it, at the top, a grey armoured hood with a rounded front, a seam and spine plate on its left, a
dark louvred vent low on its left shoulder and a barred grille window running down its right half;
a brass chevron collar over the hood's front (its apex left of centre at (19, 12), the thick left arm
down to (9.5, 23), the right arm lower, (28, 19) to (35, 25)); two brass pipes leaving each flank
diagonally into the dirt; a brass clamp on the left edge; across the middle a grey horizontal bar,
the brass "7" clamp and a slotted brass bar; below, the machinery: a grey block and a grey column on
the left, a dark slotted slab with a bright end plate and two cross rods in the middle, a dark ribbed
cylinder and a small box on the right, a bronze pipe, a low cap at the bottom left.

Built hard-surface (D65, D141): the hood is a lofted grid (pchip stations along y, a faceted arched
section, recesses and panel grooves cut as stepped vertices, so walls are real), the chevron and
plates are chamfered prisms with planar tilted tops, round parts are lathes, pipes are swept tubes.
AO/roughness bake only (bake_model), no concept projection, no outline shell (tile model, D141).

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_bunker_hull.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_bunker_hull.py -- [--no-bake] [--preview <dir>]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BAKE = "--no-bake" not in argv

PX = lt.PX
# --- Heights (layer 0: z = 0 the HD ground; every cell an enemy cell: tops <= 0.38) -----------------
BED_BOT, BED_TOP, DECK_TOP = -0.04, 0.10, 0.14
HOOD_BASE = 0.08

# --- Palette indices (the art's per-region trimmed medians; measured by measure() below) ----------
P_BED = 2        # the machine bed: the art paints it 32 (the outline/shadow ring, lighting); 2 keeps form
P_FLOOR = 1      # recess floors (vent, grille)
P_HOOD = 6
P_HOOD_R = 4     # the hood's right flank panel (art trimmed median 4)
P_GRILLE = 5     # the grille's bars (art 5)
P_BRASS = 21
P_BRASS_R = 19  # the chevron's right arm: the art paints it a shade darker (trimmed median 19)
P_BRASS_D = 18   # the slots' floor, rods under the chevron
P_BRONZE = 17
P_GREY = 6
P_SLAB = 3
P_SLAB_END = 6
P_COLUMN = 4
P_CAP = 3
P_DARK = 3
P_BOX = 4

GREY = dict(roughness=0.45, metallic=0.35)
BRASS = dict(roughness=0.38, metallic=0.65)
DARK = dict(roughness=0.6, metallic=0.3)


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) through the stations; returns f(x)."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for k in range(1, len(xs) - 1):
        if d[k - 1] * d[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    m[0], m[-1] = d[0], d[-1]

    def f(x):
        if x <= xs[0]:
            return float(ys[0])
        if x >= xs[-1]:
            return float(ys[-1])
        k = int(np.searchsorted(xs, x) - 1)
        t = (x - xs[k]) / h[k]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return float(h00 * ys[k] + h10 * h[k] * m[k] + h01 * ys[k + 1] + h11 * h[k] * m[k + 1])
    return f


# --- Hood: a lofted grid with stepped recesses ------------------------------------------------------
W_OF = pchip([2.1, 2.4, 2.8, 3.3, 3.9, 4.6, 5.4, 6.3, 7.3, 13.0, 21.6], [4.2, 5.6, 6.9, 8.0, 9.0, 9.9, 10.6, 11.1, 11.35, 11.4, 11.55])
H_OF = pchip([2.1, 2.4, 2.8, 3.3, 3.9, 4.6, 5.4, 6.3, 7.3, 12.0, 16.0, 21.6],
             [0.125, 0.19, 0.24, 0.275, 0.30, 0.318, 0.33, 0.338, 0.344, 0.348, 0.344, 0.334])
CX = 20.75
# The arched, faceted section: (u, P) with P the fraction of the hood's height above HOOD_BASE.
PROFILE = [(-1.0, 0.36), (-0.95, 0.56), (-0.88, 0.71), (-0.78, 0.83), (-0.62, 0.93), (-0.40, 0.985),
           (0.05, 1.0), (0.62, 0.95), (0.78, 0.85), (0.89, 0.71), (0.96, 0.55), (1.0, 0.36)]
HOOD_ROWS = [2.1, 2.4, 2.8, 3.3, 3.9, 4.6, 5.4, 6.3, 7.3, 8.5, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 21.6]


def u_of(x):
    return (x - CX) / 11.5


def prof(u):
    us, ps = zip(*PROFILE)
    return float(np.interp(u, us, ps))


def hood_point(u, y, p=None):
    p = prof(u) if p is None else p
    return (CX + u * W_OF(y), y, HOOD_BASE + (H_OF(y) - HOOD_BASE) * p)


class Feature:
    def __init__(self, name, u0, u1, y0, y1, depth, mat):
        self.name, self.u0, self.u1, self.y0, self.y1, self.depth, self.mat = name, u0, u1, y0, y1, depth, mat


def entries(base, spans):
    """Stations along one axis: the base positions and each feature's boundaries; at a boundary two
    entries (the tags just before, then just after), so the recess's wall is a real step."""
    pos = sorted(set([round(v, 5) for v in base] + [round(v, 5) for s in spans for v in (s[1], s[2])]))
    out = []
    for p in pos:
        left = frozenset(n for n, a, b in spans if a < p <= b)
        right = frozenset(n for n, a, b in spans if a <= p < b)
        out.append((p, left))
        if right != left:
            out.append((p, right))
    return out


def build_hood(s, feats, mat_of_u):
    fmap = {f.name: f for f in feats}
    us = [u for u, _ in PROFILE]
    cols = entries(us, [(f.name, f.u0, f.u1) for f in feats])
    rows = entries(HOOD_ROWS, [(f.name, f.y0, f.y1) for f in feats])
    bm = bmesh.new()
    cache = {}

    def vert(co):
        key = tuple(round(c, 6) for c in co)
        v = cache.get(key)
        if v is None:
            v = cache[key] = bm.verts.new(co)
        return v

    def world(px, py, z):
        return (s.x(px), s.y(py), z)

    grid = []  # rows of [wall bottom left, profile entries..., wall bottom right]
    for y, rtags in rows:
        line = [vert(world(*hood_point(-1.0, y, 0.0)))]
        for u, ctags in cols:
            x, yy, z = hood_point(u, y)
            inside = ctags & rtags
            if inside:
                z -= max(fmap[n].depth for n in inside)
            line.append(vert(world(x, yy, z)))
        line.append(vert(world(*hood_point(1.0, y, 0.0))))
        grid.append(line)
    ctag_line = [frozenset()] + [t for _, t in cols] + [frozenset()]
    cpos = [-1.0] + [u for u, _ in cols] + [1.0]

    def face(vs, mat):
        uniq = []
        for v in vs:
            if v not in uniq:
                uniq.append(v)
        if len(uniq) < 3:
            return
        try:
            f = bm.faces.new(uniq)
            f.material_index = mat
        except ValueError:
            pass

    for j in range(len(rows) - 1):
        for i in range(len(cpos) - 1):
            vs = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
            tags = ctag_line[i] & rows[j][1] if (cpos[i] != cpos[i + 1] and rows[j][0] != rows[j + 1][0]) else frozenset()
            if tags:
                mat = fmap[max(tags, key=lambda n: fmap[n].depth)].mat
            else:
                mat = mat_of_u(0.5 * (cpos[i] + cpos[i + 1]))
            face(vs, mat)
    # Ends and the bottom.
    face(list(grid[0]), mat_of_u(0.0))
    face(list(reversed(grid[-1])), mat_of_u(0.0))
    face([grid[j][0] for j in range(len(rows))] + [grid[j][-1] for j in reversed(range(len(rows)))], mat_of_u(0.0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def hexa(s, corners, mat):
    """A closed six-faced box from 8 corners (pattern px x, y and z): bottom 4 then top 4, same order."""
    bm = bmesh.new()
    vs = [bm.verts.new((s.x(x), s.y(y), z)) for x, y, z in corners]
    b, t = vs[:4], vs[4:]
    bm.faces.new(b).material_index = mat
    bm.faces.new(t).material_index = mat
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((b[i], b[j], t[j], t[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def bar_on_hood(s, x0, x1, y0, y1, below, top_off, mat, segs=4):
    """A bar standing in a hood recess: from `below` under the hood surface up to `top_off` under it,
    its top following the hood's section (segments along y)."""
    ys = np.linspace(y0, y1, segs + 1)
    for a, b in zip(ys, ys[1:]):
        pts = []
        for zoff in (below, top_off):
            for (x, y) in ((x0, a), (x1, a), (x1, b), (x0, b)):
                hx, hy, hz = hood_point(u_of(x) * 11.5 / W_OF(y), y)
                pts.append((x, y, hz - zoff))
        hexa(s, pts, mat)


def tube(s, path, r_px, mat, sides=10, caps=True):
    """A swept tube along `path` [(px, py, z)], radius r_px."""
    r = r_px * PX
    P = [np.array([s.x(px), s.y(py), z]) for px, py, z in path]
    bm = bmesh.new()
    rings = []
    for k, p in enumerate(P):
        t = (P[min(k + 1, len(P) - 1)] - P[max(k - 1, 0)])
        t /= np.linalg.norm(t)
        ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
        a = np.cross(t, ref)
        a /= np.linalg.norm(a)
        b = np.cross(a, t)
        rings.append([bm.verts.new(tuple(p + r * (math.cos(2 * math.pi * i / sides) * a + math.sin(2 * math.pi * i / sides) * b)))
                      for i in range(sides)])
    for ra, rb in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((ra[i], ra[j], rb[j], rb[i])).material_index = mat
    if caps:
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(list(reversed(rings[-1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=True)


def pipe_path(x0, y0, x1, y1, z0, z1, stub=1.2, n=14):
    """From inside the hood wall (x0, y0) at z0 out along the sprite's diagonal to (x1, y1), falling
    into the dirt to z1: level at first, then curving down."""
    out = []
    for k in range(n + 1):
        t = k / n
        e = t * t * (3 - 2 * t)
        out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * (e ** 1.4)))
    return out


def tilted(s, poly, zf, z0, mat, chamfer=0.8, drop=0.025):
    bm = bmesh.new()
    s._prism(bm, poly, zf, z0, mat, chamfer=chamfer, drop=drop)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def plane(z_at, x_at, y_at, gx, gy):
    return lambda x, y: z_at + gx * (x - x_at) + gy * (y - y_at)


# --- Art masks -------------------------------------------------------------------------------------

def fill_holes(mask):
    outside = np.zeros_like(mask)
    outside[0, :] |= ~mask[0, :]
    outside[-1, :] |= ~mask[-1, :]
    outside[:, 0] |= ~mask[:, 0]
    outside[:, -1] |= ~mask[:, -1]
    while True:
        grown = lb.dilate(outside, 1) & ~mask
        if (grown == outside).all():
            break
        outside = grown
    return ~outside


def art_mask(s):
    g = s.grid
    dark = (g == 32) | ((g >= 0) & (g < 16))
    comps = sorted(lt.components(dark), key=lambda c: -len(c[0]))
    body = np.zeros_like(dark)
    body[comps[0]] = True
    body = fill_holes(body)
    yy, xx = np.mgrid[0:s.H, 0:s.W] + 0.5
    brass = (g >= 20) & (g < 32)
    extra = np.zeros_like(body)
    for (ax, ay), (bx, by) in PIPE_LINES:
        d = np.abs((by - ay) * (xx - ax) - (bx - ax) * (yy - ay)) / math.hypot(bx - ax, by - ay)
        t = ((xx - ax) * (bx - ax) + (yy - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)
        extra |= brass & (d <= 1.3) & (t >= -0.1) & (t <= 1.1)
    clamp = (xx >= 4.5) & (xx <= 10) & (yy >= 24) & (yy <= 30.5) & (brass | (g == 32))
    return body, body | extra | clamp


# The sprite's pipe lines (pattern px), from the bright brass pixels, nudged to the tube's centre.
PIPE_LINES = [((8.8, 8.6), (3.35, 14.1)), ((8.3, 13.55), (3.35, 19.25)),
              ((32.55, 9.6), (37.75, 15.05)), ((32.65, 14.75), (37.85, 20.1))]


# --- The model ---------------------------------------------------------------------------------------

def build():
    lb.clear_scene()
    s = tb.Structure("bunker-hull")
    body, mask = art_mask(s)
    regions = []  # (name, bool px mask of what the top view shows, palette index) for measure()

    m = s.m
    bed, deck = m(P_BED, roughness=0.7, metallic=0.2), m(P_BED, roughness=0.6, metallic=0.3)

    # 1. The machine bed: the art's own outline, a chamfered plinth and an inner deck step.
    smooth = lt.blur(body.astype(np.float32), 0.85) > 0.5  # the art's 1 px staircases as a smooth edge
    for poly in s.outlines(smooth, tol=0.8):
        s.slab(poly, BED_BOT, BED_TOP, bed, chamfer_px=0.5, drop=0.02)
    for poly in s.outlines(lb.open_(lb.erode(smooth, 2), 1), tol=1.0):
        s.slab(poly, BED_TOP - 0.02, DECK_TOP, deck, chamfer_px=0.8, drop=0.02)

    # 2. The hood.
    hood, hood_r, floor = m(P_HOOD, **GREY), m(P_HOOD_R, **GREY), m(P_FLOOR, roughness=0.75, metallic=0.2)
    feats = [
        Feature("grille", u_of(21.3), u_of(27.6), 4.4, 21.0, 0.065, floor),
        Feature("vent", -1.0, u_of(15.0), 8.8, 13.8, 0.05, floor),
        Feature("seam_l", u_of(16.2), u_of(16.7), 3.9, 12.8, 0.012, hood),
        Feature("seam_s", -0.84, -0.80, 14.4, 21.2, 0.012, hood),
        Feature("seam_x", u_of(16.7), u_of(21.3), 12.2, 12.6, 0.012, hood),
        Feature("seam_cap", -0.97, u_of(16.2), 8.2, 8.55, 0.012, hood),
    ]
    build_hood(s, feats, lambda u: hood_r if u > 0.62 else hood)
    # Grille bars (the art's grey bars at x 22, 24, 26) and the vent's louvres.
    for x in (22.0, 24.0, 26.0):
        bar_on_hood(s, x, x + 0.95, 4.7, 20.7, 0.075, 0.012, m(P_GRILLE, **GREY))
    bar_on_hood(s, 21.3, 27.6, 12.0, 12.8, 0.075, 0.02, m(P_GRILLE, **GREY), segs=1)  # cross brace
    for x in (10.3, 11.9, 13.5):
        bar_on_hood(s, x, x + 0.8, 9.0, 13.6, 0.06, 0.012, hood, segs=2)
    # Rivets along the right flank and the spine.
    rivet = m(8, **GREY)
    for x, y in [(30.6, 5.0), (31.1, 9.0), (31.2, 13.0), (31.2, 17.0), (17.6, 4.6), (20.2, 4.6), (17.6, 10.6), (20.2, 10.6)]:
        hx, hy, hz = hood_point(u_of(x) * 11.5 / W_OF(y), y)
        s.bolts([(x, y)], hz - 0.004, r_px=0.45, height=0.012, mat=rivet)

    # 3. The brass chevron collar: two plates with planar tilted tops, an inset panel on each.
    brass = m(P_BRASS, **BRASS)
    LEFT = [(19.2, 11.8), (20.8, 12.6), (23.8, 15.6), (23.8, 22.0), (20.4, 22.0), (19.9, 21.0), (15.6, 21.0),
            (14.0, 23.8), (9.7, 23.8), (9.0, 22.6)]
    RIGHT = [(28.2, 18.8), (30.2, 18.8), (35.2, 24.0), (35.2, 25.6), (34.2, 27.2), (33.0, 27.2), (32.2, 26.2),
             (25.2, 26.2), (25.2, 25.0), (28.2, 21.8)]
    zl = plane(0.376, 19.2, 11.8, 0.0022, -0.0042)
    zr = plane(0.352, 28.2, 18.8, -0.0025, -0.0035)
    tilted(s, LEFT, zl, BED_TOP, brass, chamfer=0.9, drop=0.03)
    brass_r = m(P_BRASS_R, **BRASS)
    tilted(s, RIGHT, zr, BED_TOP, brass_r, chamfer=0.8, drop=0.028)
    # Raised inner panels (a 1 px step reads as the collar's machined edge band).
    LEFT_IN = [(19.2, 14.2), (22.4, 17.0), (22.4, 20.0), (15.2, 20.0), (12.6, 22.6), (11.0, 22.6)]
    tilted(s, LEFT_IN, lambda x, y: zl(x, y) + 0.004, zl(19, 18) - 0.03, brass, chamfer=0.5, drop=0.012)
    RIGHT_IN = [(29.4, 20.4), (33.8, 24.6), (33.4, 25.3), (27.0, 25.3)]
    tilted(s, RIGHT_IN, lambda x, y: zr(x, y) + 0.004, zr(30, 23) - 0.03, brass_r, chamfer=0.4, drop=0.01)
    bolt_b = m(24, **BRASS)
    for x, y, f in [(17.4, 15.0, zl), (12.6, 20.4, zl), (22.6, 15.6, zl), (31.4, 21.6, zr), (34.0, 25.4, zr), (26.6, 25.6, zr)]:
        s.bolts([(x, y)], f(x, y) - 0.004, r_px=0.5, height=0.012, mat=bolt_b)
    regions += [("chevron_l", LEFT, P_BRASS), ("chevron_r", RIGHT, P_BRASS_R)]

    # 4. Rods under the chevron's mouth (the art's dark brass slats) and the left clamp.
    brass_d = m(P_BRASS_D, **BRASS)
    for x in (16.5, 18.5, 20.5, 22.6):
        s.lathe([(0.0, 0.55), (5.0, 0.55)], x, 20.4, axis="y", z=0.19, mat=brass_d, sides=8)
    s.slab(s.rounded_box(5.0, 23.9, 9.1, 30.4, 0.9), BED_TOP - 0.06, 0.23, brass, chamfer_px=0.6, drop=0.02)
    for y0 in (25.7, 28.0):
        s.slab(s.rounded_box(3.9, y0, 9.1, y0 + 1.3, 0.4), 0.18, 0.26, brass, chamfer_px=0.3, drop=0.01)
    s.bolts([(8.2, 27.4)], 0.23, r_px=0.5, height=0.012, mat=bolt_b)

    # 5. Pipes down the flanks: collars at the hood, feet in the dirt.
    for (ax, ay), (bx, by) in PIPE_LINES:
        sgn = -1 if bx < ax else 1
        start = (ax - sgn * 1.6, ay - 1.6)
        path = [(start[0], start[1], 0.20)] + pipe_path(ax, ay, bx, by, 0.20, 0.02)
        ex, ey = bx + sgn * 0.15, by + 0.15
        path.append((ex, ey, -0.05))  # dives into the dirt
        tube(s, path, 0.66, brass)
        cx_, cy_ = ax - sgn * 0.75, ay - 0.75
        tube(s, [(cx_ - sgn * 0.5, cy_ - 0.5, 0.20), (cx_ + sgn * 0.4, cy_ + 0.4, 0.20)], 0.85, brass_d)  # collar at the hood
        mx, my = ax + (bx - ax) * 0.55, ay + (by - ay) * 0.55
        tube(s, [(mx - sgn * 0.35, my - 0.35, 0.155), (mx + sgn * 0.35, my + 0.35, 0.14)], 0.86, brass_d)  # mid band
        sx_, sy_ = ax + (bx - ax) * 0.86, ay + (by - ay) * 0.86
        tube(s, [(sx_ - sgn * 0.3, sy_ - 0.3, 0.06), (sx_ + sgn * 0.3, sy_ + 0.3, 0.035)], 0.86, brass_d)  # sleeve at the dirt

    # 6. The middle: grey bar, the brass "7", the slotted brass bar.
    grey = m(P_GREY, **GREY)
    s.lathe([(0.0, 1.55), (0.35, 1.8), (6.6, 1.8), (6.95, 1.55)], 9.0, 28.0, axis="x", z=0.21, mat=grey, sides=14)
    for t in (1.6, 4.9):
        s.lathe([(t, 1.92), (t + 0.5, 1.92)], 9.0, 28.0, axis="x", z=0.21, mat=grey, sides=14)
    SEVEN = [(13.2, 24.8), (17.0, 24.8), (20.6, 27.0), (20.6, 34.4), (17.6, 34.4), (17.6, 30.2), (15.6, 30.2),
             (15.6, 27.2), (13.2, 27.2)]
    s.slab(SEVEN, BED_TOP, 0.315, brass, chamfer_px=0.6, drop=0.02)
    s.bolts([(19.1, 32.8), (16.3, 26.0)], 0.315, r_px=0.45, height=0.012, mat=bolt_b)
    BAR = [(20.9, 25.6), (27.8, 25.6), (27.8, 30.2), (21.5, 30.2), (20.9, 29.6)]
    s.slab(BAR, BED_TOP, 0.272, brass_d, chamfer_px=0)
    s.rim(BAR, 0.8, 0.26, 0.31, brass, chamfer_px=0)
    s.slab(s.rounded_box(21.6, 27.7, 27.1, 28.3, 0.1), 0.26, 0.31, brass, chamfer_px=0)
    regions += [("seven", SEVEN, P_BRASS), ("bar", BAR, P_BRASS)]

    # 7. The machinery below.
    s.slab(s.rounded_box(9.3, 29.8, 17.2, 33.6, 1.0), BED_TOP, 0.30, grey, chamfer_px=0.8, drop=0.025)
    for x in (11.4, 13.4):
        s.slab(s.rounded_box(x, 30.5, x + 0.5, 32.9, 0.2), 0.27, 0.305, m(P_DARK, **DARK), chamfer_px=0)
    s.bolts([(10.2, 30.6), (16.3, 30.6), (10.2, 32.8), (16.3, 32.8)], 0.30, r_px=0.4, height=0.01, mat=rivet)
    regions.append(("block", s.rounded_box(9.3, 29.8, 17.2, 33.6, 1.0), P_GREY))
    col = m(P_COLUMN, **GREY)
    s.lathe([(0.0, 1.2), (0.3, 1.5), (10.4, 1.5), (10.8, 1.2)], 15.6, 33.4, axis="y", z=0.165, mat=col, sides=14)
    for t in (2.6, 6.4):
        s.lathe([(t, 1.7), (t + 0.6, 1.7)], 15.6, 33.4, axis="y", z=0.165, mat=col, sides=14)
    regions.append(("column", s.rounded_box(14.1, 33.6, 17.1, 44.0, 0.5), P_COLUMN))
    box = m(P_BOX, **GREY)
    s.slab(s.rounded_box(8.6, 39.4, 11.8, 43.8, 0.6), BED_TOP, 0.22, box, chamfer_px=0.6, drop=0.02)
    s.slab(s.rounded_box(12.6, 44.2, 17.6, 47.8, 1.2), BED_TOP, 0.24, m(P_CAP, **GREY), chamfer_px=0.7, drop=0.02)
    regions.append(("cap", s.rounded_box(12.6, 44.2, 17.6, 47.8, 1.2), P_CAP))
    tube(s, [(18.7, 36.8, 0.16), (19.0, 39.0, 0.16), (19.9, 41.5, 0.155), (20.4, 44.6, 0.15)], 0.7, m(P_BRONZE, **BRASS))
    # The slotted slab: floor, three ribs, solid head and a bright end plate; cross rods over its head.
    slab_d = m(P_SLAB, **GREY)
    s.slab(s.rounded_box(21.4, 33.0, 26.8, 47.4, 0.8), BED_TOP, 0.26, m(P_DARK, **DARK), chamfer_px=0.5, drop=0.015)
    for x0, x1 in ((21.4, 22.95), (23.65, 24.95), (25.65, 26.8)):
        s.slab(s.rounded_box(x0, 35.2, x1, 43.4, 0.25), 0.24, 0.305, slab_d, chamfer_px=0.25, drop=0.01)
    s.slab(s.rounded_box(21.4, 33.0, 26.8, 35.2, 0.6), 0.24, 0.30, slab_d, chamfer_px=0.4, drop=0.01)
    s.slab(s.rounded_box(21.6, 43.4, 26.6, 47.2, 0.9), 0.24, 0.315, m(P_SLAB_END, **GREY), chamfer_px=0.7, drop=0.02)
    regions += [("slab", s.rounded_box(21.4, 33.0, 26.8, 43.4, 0.6), P_SLAB), ("slab_end", s.rounded_box(21.6, 43.4, 26.6, 47.2, 0.9), P_SLAB_END)]
    dark = m(P_DARK, **DARK)
    for y in (32.5, 34.5):
        s.lathe([(0.0, 0.62), (10.8, 0.62)], 20.8, y, axis="x", z=0.30, mat=dark, sides=8)
    # Ribbed cylinder on the right, its saddle box above.
    ribs = [(0.0, 1.4), (0.3, 1.95)]
    t = 0.3
    while t < 5.6:
        ribs += [(t + 0.15, 2.05), (t + 0.55, 2.05), (t + 0.7, 1.8)]
        t += 0.8
    ribs += [(6.2, 1.95), (6.5, 1.3)]
    s.lathe(ribs, 29.5, 35.0, axis="y", z=0.15, mat=dark, sides=14)
    regions.append(("cyl", s.rounded_box(27.5, 35.0, 31.5, 41.5, 0.5), P_DARK))
    s.slab(s.rounded_box(27.0, 29.2, 30.6, 32.4, 0.6), BED_TOP, 0.27, dark, chamfer_px=0.5, drop=0.015)
    s.bolts([(28.0, 30.2), (29.6, 31.4)], 0.27, r_px=0.4, height=0.01, mat=rivet)

    objects = s.objects()
    s.finish(objects, mask, bake=BAKE, preview=lt.preview_arg())


build()
