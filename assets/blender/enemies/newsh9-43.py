"""Blue armoured gunship (newsh9.shp size 2 frame 43) (episode 4, lean; D65 hard-surface).

What it is: a mid-sized escort gunship of EYESPY (4.13; type e4:357, armour 40, two spawns that
drop in at (0,+3) and peel off left and right on the top layer, turret 132). The inventory's
boss flag is not borne out by the evidence; it is a plain armoured craft. It flies down the
screen, so the sprite's bottom is its nose.

Read from the 24x28 sprite (palette 5):
  - a wide armoured hull (rows 9-24, 20 px across): a crowned upper deck that breaks along a
    swept crease (the light band from the shoulders, rows 12-13, to the front lip, row 17) into a
    forward glacis that falls toward the nose; straight flanks with a chine seam; a plain belly;
  - a narrower raised engine block at the back (rows 3-8, 12 px across) whose rear top is cut by
    a V notch, and in it a dark grey thruster bell facing aft (the grey wedge, rows 1-4);
  - a raised spine plate down the middle (rows 8-16, between the dark seams at columns 8 and 15);
  - two polished steel ball mounts in sockets on the shoulders (the grey balls, rows 8-12);
  - the main weapon: a big steel ball turret (rows 18-26) set in a socket in the nose, carried by
    a dark grey cradle under its chin (the grey rows 23-25 wider than the ball), with twin short
    barrels low on its face.
Colours (median per part, shading and sheen left to the game's light): armour 153 (the whole
blue; the right half's 147-149 is the shaded side), spine 154, balls and turret 100, thruster
bell 102, sockets and cradle 99, bores 96.

Top view on the inner edge of the sprite's ink ring (D74), iou_rule_grid >= 0.95.
Outline shell from a sealed copy of the whole (common.outline_shell, islands="outer", D189).

Build: tools/build-models.sh -j 2 assets/blender/enemies/newsh9-43.py
Reads the frame from the game data with tools/sprite_data.py (the catalogue's world never draws it).
Writes public/models/enemies/newsh9-43.glb and src/render/spriteModels/newsh9-43.json
(with --out <file.glb> it writes only that glb, for review renders).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


def _find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists() and (p / "package.json").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    # Run from the repo (blender's cwd).
    cwd = Path.cwd()
    if (cwd / "assets" / "blender" / "common.py").exists():
        return cwd
    raise RuntimeError("assets/blender/common.py not found above " + str(here) + " or in the cwd")


ROOT = _find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_data  # noqa: E402

NAME = "newsh9-43"
MODEL = f"enemies/{NAME}"
PX = 1 / 12


def arg(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


# ------------------------------------------------------------------------------------------------
# Coordinates: sprite px, x = column edge - 12 (right +), y = row edge (down the screen = nose +),
# z up. Moved to Blender at the end: X = x / 12, Y = (14 - y) / 12, Z = z / 12.
# ------------------------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation (Fritsch-Carlson); returns f(x), clamped at the ends."""
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
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def se(t, p):
    return math.copysign(abs(t) ** (2 / p), t)


class Part:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat, smooth=True):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        face.smooth = smooth
        return face


def ring_loft(part, rings, mats, cap0=True, cap1=True, smooth=True, cap_mat=None):
    """Rings: lists of 3D points (same count, closed loops). mats[i]: material between ring i, i+1
    (or one int). Caps are fans to the ring centroid (non-planar safe)."""
    vr = [[part.v(p) for p in r] for r in rings]
    n = len(rings[0])
    for k in range(len(vr) - 1):
        mat = mats if isinstance(mats, int) else mats[k]
        a, b = vr[k], vr[k + 1]
        for i in range(n):
            j = (i + 1) % n
            part.f((a[i], a[j], b[j], b[i]), mat, smooth)
    cm = cap_mat if cap_mat is not None else (mats if isinstance(mats, int) else mats[0])
    for ends, flag in ((vr[0], cap0), (vr[-1], cap1)):
        if not flag:
            continue
        c = sum((Vector(v.co) for v in ends), Vector()) / n
        cv = part.v(c)
        for i in range(n):
            part.f((ends[i], ends[(i + 1) % n], cv), cm, False)
    return vr


def mirror_ring(half, y):
    """half: [(x, z)] from the top centre (x = 0) round the +x side to the bottom centre (x = 0).
    Returns the closed ring at station y: right half then the left half back up."""
    right = [(x, y, z) for x, z in half]
    left = [(-x, y, z) for x, z in reversed(half[1:-1])]
    return right + left


# --- the hull -----------------------------------------------------------------------------------
HULL_W = pchip([9.5, 9.9, 10.5, 21.3, 22.4, 23.4, 24.15, 24.6], [8.0, 9.6, 10.0, 10.0, 9.35, 8.2, 6.4, 4.6])
DECK_C = 5.0          # deck height on the centre line
DECK_E = 2.9          # deck height at x = 10
GLACIS = 0.5          # glacis fall, px per px forward of the crease
CREASE_C = 17.4       # crease row across the centre (|x| < CREASE_X)
CREASE_X = 4.5
CREASE_K = 0.7        # crease sweep: rows per px outboard of CREASE_X
WAIST = 0.6
BELLY = -1.9
SHOULDER = 1.3        # shoulder radius
CHINE = (2.05, 1.6)   # chine seam on the flanks (z top, z bottom)


def crease_y(ax):
    return CREASE_C - max(0.0, ax - CREASE_X) * CREASE_K


def deck(ax):
    return DECK_C - (DECK_C - DECK_E) * (0.55 * (ax / 10) ** 2 + 0.45 * (ax / 10) ** 4)


def hull_top(x, y):
    ax = abs(x)
    return max(WAIST + 0.9, deck(ax) - GLACIS * max(0.0, y - crease_y(ax)))


def hull_half(y, lift=0.0, grow=0.0):
    w = HULL_W(y) + grow
    wt = w - SHOULDER
    xc = CREASE_X + (CREASE_C - y) / CREASE_K if y < CREASE_C else CREASE_X
    xc = min(max(xc, 0.4 * wt + 0.25), wt - 0.3)
    xs = [0.0, 0.2 * wt, 0.4 * wt, xc] + [xc + (wt - xc) * k / 3 for k in (1, 2, 3)]
    top = [(x, hull_top(x, y) - lift) for x in xs]
    zt = top[-1][1]
    pts = list(top)
    for k in (1, 2, 3, 4):
        a = math.pi / 2 * k / 4
        pts.append((wt + SHOULDER * math.sin(a), zt - SHOULDER + SHOULDER * math.cos(a)))
    zs = zt - SHOULDER
    c0, c1 = CHINE
    if zs > c0 + 0.2:
        pts += [(w, c0), (w - 0.2, c0 - 0.12), (w - 0.2, c1 + 0.12), (w, c1)]
    else:
        pts += [(w, zs - 0.05 * i) for i in (1, 2, 3, 4)]
    zw = min(WAIST, pts[-1][1] - 0.2)
    pts.append((w, zw))
    for k in (1, 2, 3, 4, 5):
        a = math.pi / 2 * k / 5
        pts.append((w * math.cos(a) ** (2 / 2.6) if k < 5 else 0.0,
                    zw - (zw - BELLY) * math.sin(a) ** (2 / 2.6)))
    return pts


def hull_stations():
    ys = [9.5, 9.9, 10.5, 11.5, 12.5, 13.5, 14.2, 14.9, 15.6, 16.2, 16.8, CREASE_C, 18.2, 19.2, 20.2,
          21.3, 22.0, 22.7, 23.3, 23.8, 24.15, 24.4, 24.6]
    return ys


def build_hull(part, M, seal=False):
    ys = hull_stations()
    rings = []
    for y in ys:
        lift = 0.7 if y == ys[0] else (0.25 if y == ys[1] else 0.0)
        lift += {24.4: 0.35, 24.6: 0.9}.get(y, 0.0)
        rings.append(mirror_ring(hull_half(y, lift), y))
    ring_loft(part, rings, M["armour"])


# --- the rear engine block ----------------------------------------------------------------------
BLK_W = pchip([3.0, 3.35, 3.8, 11.5], [5.45, 5.85, 6.0, 6.0])
BLK_TOP = pchip([3.0, 3.6, 8.4, 10.0, 11.6], [5.25, 5.6, 5.6, 5.05, 4.3])
BLK_R = 1.5
BLK_BELLY = pchip([3.0, 5.0, 8.5, 10.5], [1.2, 0.2, -1.0, -1.6])
NOTCH_Y0, NOTCH_Y1 = 3.0, 5.6


def notch(y):
    t = min(1.0, max(0.0, (y - NOTCH_Y0) / (NOTCH_Y1 - NOTCH_Y0)))
    return 3.1 * (1 - t) + 0.25 * t, 2.3 * (1 - t) ** 1.2


def block_half(y, seal=False):
    w = BLK_W(y)
    top = BLK_TOP(y)
    wt = w - BLK_R

    def crown(x):
        return top - 0.7 * (x / 6) ** 2
    g, d = notch(y)
    if seal:
        d = 0.0
    xs = [g + (wt - g) * k / 4 for k in range(5)]
    pts = [(0.0, crown(0) - d)] + [(x, crown(x)) for x in xs]
    zt = pts[-1][1]
    for k in (1, 2, 3, 4):
        a = math.pi / 2 * k / 4
        pts.append((wt + BLK_R * math.sin(a), zt - BLK_R + BLK_R * math.cos(a)))
    zs = zt - BLK_R
    # a louvre seam band on the flank
    pts += [(w, zs - 0.6), (w - 0.18, zs - 0.72), (w - 0.18, zs - 1.0), (w, zs - 1.12)]
    zw = min(0.9, zs - 1.3)
    zb = min(BLK_BELLY(y), zw - 0.5)
    pts.append((w, zw))
    for k in (1, 2, 3, 4, 5):
        a = math.pi / 2 * k / 5
        pts.append((w * math.cos(a) ** (2 / 2.6) if k < 5 else 0.0,
                    zw - (zw - zb) * math.sin(a) ** (2 / 2.6)))
    return pts


def build_block(part, M, seal=False):
    ys = [3.0, 3.2, 3.5, 3.9, 4.4, 5.0, 5.6, 6.4, 7.4, 8.4, 9.2, 10.0, 10.8, 11.6]
    rings = []
    for y in ys:
        half = block_half(y, seal)
        if y == ys[0]:
            half = [(x * 0.92, z - 0.35 if z > 1 else z) for x, z in half]
        rings.append(mirror_ring(half, y))
    ring_loft(part, rings, M["armour"])


# --- the thruster bell in the notch ---------------------------------------------------------------
BELL_Z = 3.75


def ellipse_ring(y, hr, vr, zc, n=24):
    return [(hr * math.sin(2 * math.pi * i / n), y, zc + vr * math.cos(2 * math.pi * i / n)) for i in range(n)]


def build_bell(part, M, seal=False):
    outer = [(1.95, 3.0, 1.85), (2.15, 3.0, 1.85), (2.5, 2.85, 1.78), (3.4, 2.35, 1.5), (4.4, 1.55, 1.05),
             (5.4, 0.85, 0.62), (6.0, 0.4, 0.3)]
    rings = [ellipse_ring(y, h, v, BELL_Z) for y, h, v in outer]
    if seal:
        ring_loft(part, rings, M["bell"])
        return
    vr = ring_loft(part, rings, M["bell"], cap0=False)
    # the mouth: a lip and a deep bore
    inner = [(1.95, 2.45, 1.4), (2.3, 2.1, 1.15), (3.0, 1.4, 0.75)]
    irings = [ellipse_ring(y, h, v, BELL_Z) for y, h, v in inner]
    iv = [[part.v(p) for p in r] for r in irings]
    n = len(irings[0])
    for i in range(n):
        j = (i + 1) % n
        part.f((vr[0][j], vr[0][i], iv[0][i], iv[0][j]), M["bell"], False)
        part.f((iv[0][j], iv[0][i], iv[1][i], iv[1][j]), M["bore"])
        part.f((iv[1][j], iv[1][i], iv[2][i], iv[2][j]), M["bore"])
    c = part.v((0, 3.0, BELL_Z))
    for i in range(n):
        part.f((iv[2][(i + 1) % n], iv[2][i], c), M["bore"], False)
    # three stiffener rings round the bell
    for y, h, v in ((2.75, 2.92, 1.83), (3.7, 2.18, 1.42)):
        rs = [ellipse_ring(y - 0.12, h - 0.02, v - 0.02, BELL_Z), ellipse_ring(y - 0.08, h + 0.14, v + 0.14, BELL_Z),
              ellipse_ring(y + 0.08, h + 0.14, v + 0.14, BELL_Z), ellipse_ring(y + 0.12, h - 0.05, v - 0.05, BELL_Z)]
        ring_loft(part, rs, M["bell"], smooth=True)


# --- the spine plate ----------------------------------------------------------------------------
SPINE_W = 3.0
SPINE_TOP = pchip([7.6, 8.3, 13.0, 15.6, 17.25], [5.75, 6.35, 6.3, 5.75, 5.15])


def spine_half(y):
    zt = SPINE_TOP(y)
    zb = min(hull_top(SPINE_W, y), BLK_TOP(y) if y < 11.6 else 99) - 0.9
    w = SPINE_W if y > 7.9 else SPINE_W - 0.3
    return [(0.0, zt + 0.08), (1.3, zt + 0.04), (w - 0.5, zt), (w, zt - 0.5), (w, zb), (0.0, zb)]


def build_spine(part, M):
    ys = [7.6, 7.9, 8.3, 9.5, 11.0, 12.5, 13.6, 14.6, 15.6, 16.5, 17.25]
    rings = []
    for y in ys:
        half = spine_half(y)
        rings.append(mirror_ring(half, y))
    ring_loft(part, rings, M["spine"], smooth=False)
    # a transverse seam across the spine at row 12 (the sprite's darker band): a shallow groove plate
    # is not needed; the spine is two plates with a gap
    return rings


def build_rib(part, M):
    """A rolled armour lip along the deck/glacis crease (the sprite's light chevron, rows 13-17)."""
    xs = [-9.0 + 0.5 * i for i in range(37)]
    pts = []
    for x in xs:
        y = crease_y(abs(x))
        pts.append(Vector((x, y, hull_top(x, y) - 0.02)))
    r, n = 0.34, 8
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = (b - a).normalized()
        up = Vector((0, 0, 1))
        side = t.cross(up).normalized()
        up = side.cross(t).normalized()
        rings.append([tuple(p + (side * math.cos(2 * math.pi * k / n) + up * math.sin(2 * math.pi * k / n) * 0.8) * r)
                      for k in range(n)])
    ring_loft(part, rings, M["armour"])


def box(part, x0, x1, y0, y1, z0, z1, mat, smooth=False):
    vs = [part.v((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        part.f([vs[i] for i in q], mat, smooth)


def build_vents(part, M):
    """A louvred intake grille on each flank of the engine block, under its seam band."""
    for s in (-1, 1):
        x = s * BLK_W(6.0)
        box(part, min(x - s * 0.1, x + s * 0.06), max(x - s * 0.1, x + s * 0.06), 4.6, 8.3, 1.2, 2.35, M["socket"])
        for k in range(5):
            y = 4.85 + k * 0.78
            box(part, min(x, x + s * 0.2), max(x, x + s * 0.2), y, y + 0.3, 1.25, 2.3, M["armour"])


# --- shoulder balls, sockets, nose turret, cradle -----------------------------------------------
BALL = (5.85, 10.35, 4.7, 2.2)
TURRET = (0.0, 21.8, 1.45, 4.2)


def uv_sphere(part, c, r, mat, seg=20, rings=12, scale=(1, 1, 1)):
    cx, cy, cz = c
    sx, sy, sz = scale
    top = part.v((cx, cy, cz + r * sz))
    bot = part.v((cx, cy, cz - r * sz))
    layers = []
    for k in range(1, rings):
        t = math.pi * k / rings
        layers.append([part.v((cx + r * sx * math.sin(t) * math.cos(2 * math.pi * i / seg),
                               cy + r * sy * math.sin(t) * math.sin(2 * math.pi * i / seg),
                               cz + r * sz * math.cos(t))) for i in range(seg)])
    for i in range(seg):
        j = (i + 1) % seg
        part.f((top, layers[0][i], layers[0][j]), mat)
        part.f((bot, layers[-1][j], layers[-1][i]), mat)
    for a, b in zip(layers, layers[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            part.f((a[i], b[i], b[j], a[j]), mat)


def cylinder(part, c, axis, r, z0, z1, mat, n=24, r1=None, cap=True, smooth=True):
    """A (tapered) cylinder along unit `axis` through point c, from c + z0*axis to c + z1*axis."""
    a = Vector(axis).normalized()
    u = a.orthogonal().normalized()
    w = a.cross(u)
    r1 = r if r1 is None else r1
    rings = []
    for z, rr in ((z0, r), (z1, r1)):
        base = Vector(c) + a * z
        rings.append([tuple(base + (u * math.cos(2 * math.pi * i / n) + w * math.sin(2 * math.pi * i / n)) * rr)
                      for i in range(n)])
    return ring_loft(part, rings, mat, cap0=cap, cap1=cap, smooth=smooth)


def build_balls(part, M, seal=False):
    bx, by, bz, br = BALL
    for s in (-1, 1):
        c = (s * bx, by, bz)
        uv_sphere(part, c, br, M["ball"], seg=18, rings=10)
        # socket: a cup ring round the ball's lower half, sunk into the deck
        if not seal:
            rings = [[(c[0] + r * math.cos(2 * math.pi * i / 28), by + r * math.sin(2 * math.pi * i / 28), z)
                      for i in range(28)]
                     for r, z in ((2.42, bz - 2.6), (2.42, bz - 0.5), (2.15, bz - 0.28), (1.92, bz - 0.8))]
            ring_loft(part, rings, M["socket"], cap0=True, cap1=False)


def build_turret(part, M, seal=False):
    tx, ty, tz, tr = TURRET
    uv_sphere(part, (tx, ty, tz), tr, M["turret"], seg=28, rings=16, scale=(1.1, 1.0, 1.0))
    if seal:
        return
    # twin barrels low on the face, angled down 32 degrees
    d = Vector((0, math.cos(math.radians(48)), -math.sin(math.radians(48))))
    for s in (-1, 1):
        base = Vector((s * 1.15, ty, tz))
        cylinder(part, tuple(base), tuple(d), 0.6, 3.2, 4.6, M["socket"], n=16)
        cylinder(part, tuple(base), tuple(d), 0.3, 4.4, 4.605, M["bore"], n=12, smooth=False)
    # a seam ring round the ball's equator, tilted with the barrels (a split turret shell)
    ax = Vector((0, math.sin(math.radians(32)), math.cos(math.radians(32))))
    cylinder(part, (tx, ty, tz), tuple(ax), tr + 0.06, -0.12, 0.12, M["socket"], n=40, cap=False)


CRADLE = (21.8, 6.0, 4.2, 2.6)   # centre row, half width, front reach, superellipse power


def cradle_outline(n=28):
    cy, ax, ay, p = CRADLE
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n          # 0 .. pi, front half
        pts.append((ax * se(math.cos(a), p), cy + ay * se(math.sin(a), p)))
    pts += [(-ax, cy - 2.0), (ax, cy - 2.0)]
    return pts


def build_cradle(part, M):
    outline = cradle_outline()
    cy = CRADLE[0]

    def inset(pts, d):
        out = []
        for x, y in pts:
            dx, dy = x, y - (cy - 1.0)
            n = math.hypot(dx, dy) or 1
            out.append((x - d * dx / n, y - d * dy / n))
        return out
    levels = [(inset(outline, 0.9), -1.85), (inset(outline, 0.35), -1.75), (outline, -1.2), (outline, 0.55),
              (inset(outline, 0.3), 0.95), (inset(outline, 1.2), 1.05)]
    rings = [[(x, y, z) for x, y in o] for o, z in levels]
    ring_loft(part, rings, M["cradle"], smooth=False)


# ------------------------------------------------------------------------------------------------

def to_object(part, name, mats, coll, smooth_angle=24, round_mats=()):
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    lim = math.radians(smooth_angle)
    for e in bm.edges:
        fs = e.link_faces
        if len(fs) != 2:
            e.smooth = False
            continue
        if fs[0].material_index != fs[1].material_index:
            e.smooth = False
        elif fs[0].material_index in round_mats and fs[0].smooth and fs[1].smooth:
            e.smooth = True
        else:
            e.smooth = fs[0].normal.angle(fs[1].normal, 0.0) < lim and fs[0].smooth and fs[1].smooth
    for f in bm.faces:
        f.smooth = True
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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


def spec(mat, level=0.5):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def build():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    # The catalogue has no reference/models folder for it: read the frame from the game data.
    sprite = sprite_data.load(ROOT, NAME, "newsh9.shp", [43])
    coll = common.reset_collection(NAME)
    defs = [  # key, palette index, metallic, roughness, specular
        ("armour", 153, 0.6, 0.36, 0.5),
        ("spine", 154, 0.6, 0.32, 0.5),
        ("ball", 100, 0.45, 0.5, 0.5),
        ("turret", 100, 0.45, 0.5, 0.5),
        ("bell", 102, 0.75, 0.38, 0.5),
        ("socket", 99, 0.6, 0.5, 0.45),
        ("cradle", 99, 0.65, 0.45, 0.45),
        ("bore", 96, 0.3, 0.85, 0.3),
    ]
    mats, M = [], {}
    for i, (key, idx, met, rough, sp) in enumerate(defs):
        mats.append(spec(common.palette_material(sprite, idx, f"{NAME}-{key}", metallic=met, roughness=rough), sp))
        M[key] = i
        if key in ("ball", "turret"):  # satin steel under a clear coat: the sprite's sheen spot
            bsdf = next(n for n in mats[-1].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Coat Weight"].default_value = 0.6
            bsdf.inputs["Coat Roughness"].default_value = 0.12

    part = Part()
    build_hull(part, M)
    build_block(part, M)
    build_bell(part, M)
    build_spine(part, M)
    build_balls(part, M)
    build_vents(part, M)
    build_rib(part, M)
    build_turret(part, M)
    obj = to_object(part, NAME, mats, coll, round_mats=(M["ball"], M["turret"], M["bell"]))

    # Sealed copy for the outline shell: the closed volumes only (no bores, sockets or seams).
    seal = Part()
    build_hull(seal, M)
    build_block(seal, M, seal=True)
    build_bell(seal, M, seal=True)
    build_spine(seal, M)
    build_balls(seal, M, seal=True)
    build_turret(seal, M, seal=True)
    sobj = to_object(seal, NAME + "_seal", [], coll)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sobj, coll, voxel=0.008, faces=2400, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(sobj, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"

    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    out = arg("--out")
    if out:
        common.export_glb([obj, shell], Path(out))
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    print(f"{NAME}: {tris} tris, outline shell {len(shell.data.polygons)} faces")


if __name__ == "__main__":
    build()
