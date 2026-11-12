"""GEM WAR gem-launcher gunship (newshv.shp 89, 91/129, 93), DESIGN B: silhouette and readability
from the small tilted game camera first, then hard-surface detail (D50-D53, D65).

WHAT IT IS: a free-flying gunship, 72 x 28 px, three 24x28 pieces side by side: newshv-89 (left
hull), newshv-91 (centre launcher; frame 129 = firing, model newshv-91-f2), newshv-93 (right hull,
the exact mirror of 89). Types 796/797/798 drift down the screen and fire aimed shots; the centre
launches gem pods. It flies, so it has a round, closed belly and stands on nothing.

Reading of the sprite (light from the upper left; white spots are sheen, the dark ring is ink):
- each side hull: an armoured nacelle. A louvred vent block on its outboard rear deck (three white
  fins, cols 9/11/13), a bright spine rib down col 15, a raised armour block inboard (cols 16-23,
  rows 5-13) with a rail at its front foot (row 14), a plain mid deck (rows 15-18), a sloped nose
  glacis (rows 19-23) with a rail along its top (row 19), and a red marker lamp on the inboard
  front corner (col 24, rows 19-20). On the outer flank a big glossy red gem pod (cols 2-8, rows
  8-15) on a low dark shelf (rows 15-18). A 1 px rear fairing bump (row 5, cols 14-21).
- centre: a horizontal launcher drum (axis east-west, cols 29-42, rows 8-14; its bright middle is
  sheen) held between two ribbed trunnion collars (cols 24-29) into the hulls; under/in front of it
  a gun chin (rows 15-17) with the launcher muzzle (cols 34-37) and two red port lenses (cols 32,
  39) on its top, and two short STRAIGHT barrels forward (cols 31-32 and 39-40, row 18).
- frame 129: the muzzle glows (118/122), the port lenses brighten (68), and a wide flat muzzle
  flare spreads in front of the chin (rows 18-21; row 19 spans lamp to lamp).

Silhouette plan (game camera, 32 deg from south): three height bands. Skyline: the drum crown (7.4
px) and the two red pods (6.2); the armour blocks, spines and vent fins (5.6-6.3); the decks (4.5);
the nose glacis ramps down to 1.9 at the front, so from the camera the hulls read as two armoured
wedges with a drum slung between them and the chin's guns under it.

Plan: every part lies inside the sprite's INNER mask (D74, tools/sprite_mask.py): edges are the
inner-mask edges per row through pchip stations.

Final script: exports public/models/enemies/newshv-{89,91,91-f2,93}.glb (each with its outline shell)
and src/render/spriteModels/*.json; bakes AO/roughness (D65) unless --no-bake.

Coordinates: x = assembly column (0..72), y = row (0..28, south = FRONT), z up, in sprite px.
Blender X = (x - 36) / 12, Y = (14 - y) / 12, Z = z / 12 (the centre piece at the origin).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshv-91.py
(extra: -- [--no-bake] [--out x.glb] [--pieces DIR] [--review DIR] [--no-export])
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "assembly-newshv-91"
TAG = "nv91b"
PIECES = ["newshv-89", "newshv-91", "newshv-93"]
LAYOUT = [("newshv-89", -24, 0), ("newshv-91", 0, 0), ("newshv-93", 24, 0)]
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def X(x):
    return (x - 36) / 12


def Y(y):
    return (14 - y) / 12


def Z(z):
    return z / 12


def P(x, y, z):
    return (X(x), Y(y), Z(z))


# --------------------------------------------------------------------------------------------------
# pchip (copied from usp_talon.pchip semantics: monotone cubic through stations)
# --------------------------------------------------------------------------------------------------
def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(0, min(n - 2, next(k for k in range(n - 1) if x <= xs[k + 1])))
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def lin(knots):
    def f(x):
        if x <= knots[0][0]:
            return knots[0][1]
        for (a, va), (b, vb) in zip(knots, knots[1:]):
            if x <= b:
                return va + (vb - va) * (x - a) / (b - a)
        return knots[-1][1]
    return f


# --------------------------------------------------------------------------------------------------
# Materials (pal_<index>): satin blue metal, glossy red gem pods, glows per D126
# --------------------------------------------------------------------------------------------------
def merged_colors():
    cols = {}
    for n in PIECES:
        d = json.loads((ROOT / "reference" / "models" / n / "sprite.json").read_text())
        cols.update(d["colors"])
    return cols


class Mats:
    def __init__(self):
        self.sprite = {"name": NAME, "colors": merged_colors()}
        self.list, self.slots = [], {}

    def __call__(self, key):
        """key: palette index, or (index, variant) with variant 'glow<strength>' / 'gloss'."""
        if key in self.slots:
            return self.slots[key]
        idx, var = (key, "") if isinstance(key, int) else key
        kw = dict(metallic=0.3, roughness=0.42)  # satin blue steel
        if 52 <= idx <= 54:
            kw = dict(metallic=0.3, roughness=0.55)  # darker, rougher steel (sockets, bores)
        if 64 <= idx <= 76:
            kw = dict(metallic=0.15, roughness=0.28)  # glossy red gem / lens
        if var.startswith("glow"):
            kw = dict(metallic=0.0, roughness=0.5, emission_strength=float(var[4:]))
        tag = TAG if not var else f"{TAG}_{var.replace('.', 'p')}"
        self.slots[key] = len(self.list)
        self.list.append(common.palette_material(self.sprite, idx, tag, **kw))
        return self.slots[key]


# --------------------------------------------------------------------------------------------------
# Mesh builder in sprite px
# --------------------------------------------------------------------------------------------------
def poly_area(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def inset(poly, d):
    """Miter inset of a closed (x, y) polygon by d (inward)."""
    if d == 0:
        return list(poly)
    s = 1 if poly_area(poly) > 0 else -1
    n, out = len(poly), []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1 = math.hypot(*e1) or 1
        l2 = math.hypot(*e2) or 1
        n1 = (-e1[1] / l1 * s, e1[0] / l1 * s)
        n2 = (-e2[1] / l2 * s, e2[0] / l2 * s)
        m = (n1[0] + n2[0], n1[1] + n2[1])
        ml = math.hypot(*m) or 1
        m = (m[0] / ml, m[1] / ml)
        k = d / max(0.35, m[0] * n1[0] + m[1] * n1[1])
        out.append((p1[0] + m[0] * k, p1[1] + m[1] * k))
    return out


def rounded_rect(x0, y0, x1, y1, r, seg=3):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


class B:
    def __init__(self, mats):
        self.bm = bmesh.new()
        self.mats = mats
        self.smooth_faces = set()

    def ring_loft(self, rings, mat, cap0=True, cap1=True, smooth=False, mats=None):
        """rings: list of equal-length lists of (x, y, z) px points. mats: per band material."""
        bm = self.bm
        vs = [[bm.verts.new(P(*p)) for p in r] for r in rings]
        faces = []
        for j in range(len(vs) - 1):
            A, Bv = vs[j], vs[j + 1]
            n = len(A)
            mi = self.mats(mats[j] if mats else mat)
            for i in range(n):
                k = (i + 1) % n
                try:
                    f = bm.faces.new((A[i], A[k], Bv[k], Bv[i]))
                except ValueError:
                    continue
                f.material_index = mi
                f.smooth = smooth
                faces.append(f)
        mi = self.mats(mat)
        for cap, rv in ((cap0, vs[0]), (cap1, vs[-1])):
            if cap:
                try:
                    f = bm.faces.new(rv if rv is vs[0] else list(reversed(rv)))
                    f.material_index = mi
                    faces.append(f)
                except ValueError:
                    pass
        return faces

    def prism(self, poly, z0, z1, mat, ch=0.3, chb=None, top=None, side=None):
        """Plan polygon (x, y) extruded z0..z1, chamfer ch on top, chb on the bottom."""
        chb = ch if chb is None else chb
        if poly_area(poly) > 0:   # px y is down: make it clockwise in px = ccw in Blender
            poly = list(reversed(poly))
        rings = [[(x, y, z0) for x, y in inset(poly, chb)], [(x, y, z0 + chb) for x, y in poly],
                 [(x, y, z1 - ch) for x, y in poly], [(x, y, z1) for x, y in inset(poly, ch)]]
        s = side if side is not None else mat
        t = top if top is not None else mat
        return self.ring_loft(rings, t, mats=[s, s, t])

    def box(self, x0, x1, y0, y1, z0, z1, mat, ch=0.3, **kw):
        return self.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, ch=ch, **kw)

    def cyl_x(self, x0, x1, yc, zc, ry, rz, mat, n=20, smooth=True, stations=None, p=2.0):
        """Round section in the (y, z) plane swept along x. stations: [(x, scale)]."""
        st = stations or [(x0, 1.0), (x1, 1.0)]
        rings = []
        for x, s in st:
            r = []
            for i in range(n):
                a = 2 * math.pi * i / n
                c, si = math.cos(a), math.sin(a)
                r.append((x, yc + ry * s * math.copysign(abs(c) ** (2 / p), c),
                          zc + rz * s * math.copysign(abs(si) ** (2 / p), si)))
            rings.append(r)
        return self.ring_loft(rings, mat, smooth=smooth)

    def cyl_y(self, y0, y1, xc, zc, r, mat, n=12, smooth=True, stations=None):
        st = stations or [(y0, r), (y1, r)]
        rings = []
        for y, rr in st:
            rings.append([(xc + rr * math.cos(2 * math.pi * i / n), y, zc + rr * math.sin(2 * math.pi * i / n))
                          for i in range(n)])
        rings = rings[::-1]
        return self.ring_loft(rings, mat, smooth=smooth)

    def finish(self, name, coll):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats.list:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


def superell_rings(c, r, p, n=24, m=12):
    """Closed superellipsoid (exponent p in both angles) as rings from pole to pole."""
    e = 2.0 / p
    sp = lambda v: math.copysign(abs(v) ** e, v)  # noqa: E731
    rings = []
    for j in range(0, m + 1):
        t = -math.pi / 2 + math.pi * j / m
        ct = max(sp(math.cos(t)), 0.002)
        rings.append([(c[0] + r[0] * ct * sp(math.cos(2 * math.pi * i / n)),
                       c[1] + r[1] * ct * sp(math.sin(2 * math.pi * i / n)),
                       c[2] + r[2] * sp(math.sin(t))) for i in range(n)])
    return rings


def ell_rings(c, r, n=16, m=8, rot=None):
    """Closed ellipsoid as rings from pole to pole (poles as tiny rings)."""
    rings = []
    for j in range(0, m + 1):
        t = -math.pi / 2 + math.pi * j / m
        ct = max(math.cos(t), 0.002)
        rings.append([(c[0] + r[0] * ct * math.cos(2 * math.pi * i / n),
                       c[1] + r[1] * ct * math.sin(2 * math.pi * i / n),
                       c[2] + r[2] * math.sin(t)) for i in range(n)])
    return rings


# --------------------------------------------------------------------------------------------------
# The craft
# --------------------------------------------------------------------------------------------------
# Left hull body plan per row (inner-mask edges): row -> (left, right)
BODY_L = {6: 9.0, 7: 8.15, 8: 8.1, 9: 8.1, 10: 8.1, 11: 8.1, 12: 8.1, 13: 8.1, 14: 8.1, 15: 8.1, 16: 8.1,
          17: 8.1, 18: 8.0, 19: 7.0, 20: 8.95, 21: 10.95, 22: 12.95, 23: 14.95}
BODY_R = {6: 24.3, 7: 24.4, 8: 24.4, 9: 24.4, 10: 24.4, 11: 24.4, 12: 24.4, 13: 24.4, 14: 24.6, 15: 25.4,
          16: 24.3, 17: 24.3, 18: 24.4, 19: 24.4, 20: 24.4, 21: 23.05, 22: 22.05, 23: 21.05}
DECK = 4.5
TOP = lin([(5.85, 2.9), (6.3, 3.9), (6.9, DECK), (19.2, DECK), (19.8, 4.3), (24.0, 1.9)])
BELLY = pchip([5.85, 6.6, 8.5, 17.5, 20.5, 22.5, 24.0], [-0.6, -1.7, -2.4, -2.4, -1.6, -0.6, 0.4])


def body_edges():
    ys = sorted(BODY_L)
    yy = [5.9] + [r + 0.5 for r in ys] + [24.0]
    ll = [9.6] + [BODY_L[r] for r in ys] + [15.6]
    rr = [23.6] + [BODY_R[r] for r in ys] + [20.4]
    return lin(list(zip(yy, ll))), lin(list(zip(yy, rr)))


def hull_section(y, L, R):
    T, Bz = TOP(y), BELLY(y)
    c = min(0.8, (R - L) / 4)
    # top chamfers, slight tumblehome outboard, rounded bilge
    pts = [(L + c, T), (R - c, T), (R, T - c), (R, Bz + 1.6), (R - 0.5, Bz + 0.55), (R - 1.6, Bz),
           (L + 1.6, Bz), (L + 0.5, Bz + 0.55), (L, Bz + 1.6), (L, T - c)]
    return [(x, y, z) for x, z in pts]


def build_left_hull(b, firing):
    fl, fr = body_edges()
    ys = [5.9, 6.2, 6.6, 7.0, 7.5, 8.5, 10.5, 12.5, 14.5, 16.5, 18.0, 18.5, 19.2, 19.5, 19.8, 20.5, 21.5,
          22.5, 23.5, 24.0]
    rings = [hull_section(y, fl(y), fr(y)) for y in ys]
    b.ring_loft(rings, 55)

    # Rear fairing bump (row 5, cols 14-21): the drive housing behind the armour block, with two
    # exhaust nozzles let into its rear face.
    b.prism(rounded_rect(14.1, 5.05, 21.8, 8.0, 0.6), -0.9, 4.2, 57, ch=0.45)
    for x in (16.2, 19.9):
        b.cyl_y(4.9, 5.4, x, 1.7, 1.15, 53, n=12)
        b.cyl_y(4.75, 4.95, x, 1.7, 0.75, 52, n=12)

    # Vent block, outboard rear deck (cols 8.6-15, rows 6-11.6), and three louvre fins at cols 9,
    # 11, 13 standing proud (the white ribs are lit fin tops).
    vb = [(9.1, 6.05), (15.0, 6.05), (15.0, 11.7), (8.4, 11.7), (8.4, 6.8)]
    b.prism(vb, 3.6, 5.0, 59, ch=0.3)
    for c in (9, 11, 13):
        b.prism(rounded_rect(c + 0.08, 6.2, c + 0.92, 11.1, 0.2, 1), 4.6, 5.9, 61, ch=0.18)
    # Louvre slots between the fins (dark, recessed reads come from the fin walls).
    # Spine rib down col 15, following the deck and the glacis.
    sp = []
    for y in (5.1, 5.6, 6.5, 9.0, 13.0, 14.4, 15.0, 17.0, 19.2, 19.8, 21.5, 23.0, 23.9):
        top = (6.25 if y < 14.4 else TOP(y) + 0.9)
        if y < 6.0:
            top = 5.6 + (y - 5.1) * 1.2
        sp.append([(14.95, y, top - 3.0), (16.05, y, top - 3.0), (16.05, y, top - 0.25), (15.8, y, top),
                   (15.2, y, top), (14.95, y, top - 0.25)])
    b.ring_loft(sp, 60)

    # Armour block, inboard upper deck (cols 16-24, rows 5-14): a convex top, high at the spine.
    ab = [(16.0, 5.05), (21.6, 5.05), (23.3, 5.95), (24.45, 6.4), (24.45, 14.25), (16.0, 14.25)]
    abr = list(reversed(ab))
    rings = [[(x, y, 2.5) for x, y in inset(abr, 0.0)]]
    hz = lambda x: 5.75 - 0.55 * ((x - 16.0) / 8.45) ** 1.6  # noqa: E731
    rings.append([(x, y, hz(x) - 0.45) for x, y in abr])
    rings.append([(x, y, hz(x)) for x, y in inset(abr, 0.45)])
    b.ring_loft(rings, 57, mats=[57, 57])
    # its seams: a transverse panel line (row 9.5) and a hatch outline near the front
    for (x0, x1, y0, y1) in ((16.6, 24.4, 9.35, 9.7), (19.9, 20.2, 5.6, 9.35)):
        b.box(x0, x1, y0, y1, 4.0, hz((x0 + x1) / 2) + 0.04, 53, ch=0.04)
    # a bolted inspection hatch on the block's front half (rows 10.4-13.4, cols 17-23)
    hh = rounded_rect(17.1, 10.4, 23.4, 13.4, 0.4, 2)
    b.prism(hh, 4.0, hz(20.2) + 0.12, 57, ch=0.1)
    for x in (17.7, 22.8):
        for y in (11.0, 12.8):
            b.ring_loft(ell_rings((x, y, hz(x) + 0.12), (0.22, 0.22, 0.12), n=8, m=4), 54, smooth=True)
    # Riveted panel heads along the seams and the block's rear edge (graft from design A; modelled
    # detail only, inside the outline).
    for (x, y) in ((17.1, 6.6), (17.1, 8.7), (22.6, 6.9), (22.6, 8.7), (19.0, 9.0), (21.2, 9.0),
                   (23.7, 10.2), (23.7, 13.6), (17.1, 9.95)):
        b.ring_loft(ell_rings((x, y, hz(x) + 0.02), (0.2, 0.2, 0.1), n=8, m=3), 54, smooth=True)
    b.box(16.6, 24.4, 12.95, 13.2, 4.0, hz(20.5) + 0.03, 53, ch=0.03)
    # Rail at its front foot (row 14, cols 17-24): a round bar on stand-offs.
    b.cyl_x(16.9, 24.7, 14.55, 4.85, 0.5, 0.5, 58, n=10)
    for x in (18.0, 22.5):
        b.box(x - 0.3, x + 0.3, 14.2, 14.9, DECK - 0.2, 4.7, 54, ch=0.08)
    # Mid deck panel lines (rows 15-18) and a raised access panel
    b.box(16.4, 24.4, 16.85, 17.15, DECK - 0.2, DECK + 0.08, 53, ch=0.03)
    b.box(11.85, 12.15, 11.8, 19.3, DECK - 0.2, DECK + 0.08, 53, ch=0.03)
    b.prism(rounded_rect(17.0, 15.25, 23.6, 16.6, 0.3, 2), DECK - 0.2, DECK + 0.22, 56, ch=0.12)

    # Nose glacis plate (rows 19.6-24) raised over the slope, and the rail along its top (row 19).
    gp = []
    for y in (19.75, 20.5, 21.5, 22.5, 23.4, 23.85):
        L, R = fl(y) + 0.75, fr(y) - 0.55
        T = TOP(y) + 0.02
        gp.append([(L, y, T - 0.3), (R, y, T - 0.3), (R, y, T + 0.12), (R - 0.15, y, T + 0.25),
                   (L + 0.15, y, T + 0.25), (L, y, T + 0.12)])
    b.ring_loft(gp, 58)
    b.cyl_x(18.9, 24.6, 19.5, 4.55, 0.42, 0.42, 59, n=10)

    # Under-collar bracket filling the hull's inboard corner at row 15 (col 24).
    b.prism(rounded_rect(23.0, 14.6, 25.35, 16.05, 0.3, 2), -1.2, 3.6, 55, ch=0.3)
    # Corner lamp housing (cols 23-25.3, rows 17.7-21) and its red lamp (col 24, rows 19-20).
    b.prism(rounded_rect(22.8, 18.05, 25.3, 21.0, 0.5, 2), -0.9, 3.9, 55, ch=0.35)
    b.ring_loft(ell_rings((24.45, 19.75, 3.85), (0.7, 1.05, 0.55), n=12, m=6), (68, "glow0.6"), smooth=True)

    # Gem pod: a big glossy red gem ball on the outer flank (cols 2-8.6, rows 8-16): a soft
    # superellipsoid (round where the sprite is round, a touch fuller than a sphere so its plan
    # fills the sprite's rounded square), half buried in the hull side and held by a dark socket
    # ring; the white spot on it is sheen.
    b.ring_loft(superell_rings((5.55, 12.0, 2.5), (3.55, 4.0, 3.7), 2.7, n=28, m=14), 68, smooth=True)
    b.cyl_x(7.9, 9.0, 12.0, 2.5, 3.55, 3.3, 54, n=24)
    b.cyl_x(7.75, 7.95, 12.0, 2.5, 3.75, 3.5, 53, n=24)

    # Low shelf under / in front of the pod (cols 2-9, rows 15-19).
    sh = [(2.0, 14.6), (9.0, 14.6), (9.0, 19.1), (3.6, 19.1), (2.85, 18.4), (2.85, 17.3), (2.0, 16.6)]
    b.prism(sh, -1.8, 1.0, 54, ch=0.35)


def build_centre(b, firing):
    # Trunnion collars (cols 24-29.8): ribbed rings round the drum axis, into the hulls.
    ZC, YCOL = 3.0, 11.0
    for s in (1, -1):
        X_ = (lambda u: u) if s > 0 else (lambda u: 72 - u)
        st = [(23.5, 0.93), (24.0, 1.0), (24.9, 1.0), (24.95, 0.955), (25.35, 0.955), (25.4, 1.0),
              (26.6, 1.0), (26.65, 1.045), (27.75, 1.045), (27.8, 1.0),
              (28.2, 1.0), (28.25, 0.955), (28.6, 0.955), (28.65, 1.0),
              (29.0, 1.0), (29.1, 0.9), (29.9, 0.9)]
        st = [(X_(u), k) for u, k in st]
        if s < 0:
            st = st[::-1]
        b.cyl_x(None, None, YCOL, ZC, 4.0, 4.0, 56, n=24, stations=st, p=2.0)
    # The launcher drum (cols 29.6-42.4, rows 8-15): a slightly barrelled cylinder, its axis half
    # a pixel forward of the collars' (the sprite's drum sits on rows 8-14, the collars 7-14).
    yc = 11.5
    st = [(29.5, 0.94), (30.3, 0.985), (33.0, 1.0), (36.0, 1.0), (39.0, 1.0), (41.7, 0.985), (42.5, 0.94)]
    b.cyl_x(None, None, yc, ZC, 3.5, 4.4, 58, n=28, stations=st, p=2.0)
    for u in (31.1, 40.5):  # machined seam bands
        b.cyl_x(u, u + 0.4, yc, ZC, 3.52, 4.42, 55, n=28)
    # Feed hatch on the drum's crown (reads as a machined panel from the camera)
    b.cyl_x(34.6, 37.4, yc, ZC, 3.3, 4.47, 58, n=28, p=2.0)

    # Gun chin under and in front of the drum (rows 13.5-18, cols 28-44).
    chin = [(28.05, 13.0), (43.95, 13.0), (43.95, 15.55), (42.0, 17.95), (30.0, 17.95), (28.05, 15.55)]
    b.prism(chin, -1.6, 2.1, 55, ch=0.5, chb=0.6)
    # Muzzle housing on the chin (cols 31-41, rows 14.3-16.6) with the muzzle and port lenses.
    b.prism(rounded_rect(31.0, 14.2, 41.0, 16.7, 0.5, 2), 1.2, 2.8, 56, ch=0.3)
    if firing:
        b.prism(rounded_rect(33.9, 14.75, 38.1, 16.15, 0.35, 2), 2.0, 2.92, (120, "glow1.0"), ch=0.1)
        b.prism(rounded_rect(34.8, 15.0, 37.2, 15.9, 0.25, 2), 2.0, 2.98, (122, "glow1.0"), ch=0.08)
    else:
        b.prism(rounded_rect(33.9, 14.75, 38.1, 16.15, 0.35, 2), 2.0, 2.9, 67, ch=0.1)
        b.prism(rounded_rect(34.6, 15.05, 37.4, 15.85, 0.2, 2), 2.4, 2.95, 66, ch=0.05)
    lens = (68, "glow0.8") if firing else (66, "glow0.4")
    for x in (32.45, 39.55):
        b.ring_loft(ell_rings((x, 15.45, 2.75), (0.5, 0.55, 0.32), n=10, m=5), lens, smooth=True)
    # Two short straight barrels forward (cols 31-32 / 39-40, row 18), muzzle rings at the tips.
    for x in (32.0, 40.0):
        b.cyl_y(None, None, x, 0.7, 0.8, 56, n=14,
                stations=[(16.5, 0.8), (18.15, 0.8), (18.2, 0.92), (18.95, 0.92)])
        b.cyl_y(18.9, 19.0, x, 0.7, 0.55, 52, n=14)

    if firing:
        build_flare(b)


def build_flare(b):
    """Frame 129's muzzle flare: a flat lens of glowing layers in front of the chin, hottest in
    the middle and on top; row 19 a thin beam from lamp to lamp."""
    outer = [(24.4, 19.15), (27.0, 18.95), (28.75, 18.5), (29.3, 17.9), (36.0, 17.55), (42.7, 17.9),
             (43.25, 18.5), (45.0, 18.95), (47.6, 19.15), (47.6, 19.9), (45.0, 20.0), (41.3, 20.05),
             (40.8, 20.9), (38.3, 21.1), (37.8, 21.9), (34.2, 21.9), (33.7, 21.1), (31.2, 20.9),
             (30.7, 20.05), (27.0, 20.0), (24.4, 19.9)]
    cx, cy = 36.0, 19.5
    layers = [(1.0, 114, 0.55, 1.05), (0.75, 117, 0.6, 1.25), (0.52, 120, 0.65, 1.45),
              (0.34, 123, 0.7, 1.65), (0.18, 125, 0.75, 1.85)]
    for k, pal, z0, z1 in layers:
        pts = [(cx + (x - cx) * k, cy + (y - cy) * max(k, 0.45)) for x, y in outer]
        b.prism(pts, z0, z1, (pal, "glow1.0"), ch=0.12)


def build(coll, mats, firing):
    b = B(mats)
    start = len(b.bm.verts)
    build_left_hull(b, firing)
    # mirror the left hull into the right hull (newshv-93 = exact mirror of newshv-89)
    bm = b.bm
    bm.verts.ensure_lookup_table()
    left_faces = list(bm.faces)
    vmap = {}
    for v in bm.verts[start:]:
        vmap[v] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
    for f in left_faces:
        nf = bm.faces.new([vmap[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index
        nf.smooth = f.smooth
    build_centre(b, firing)
    return b.finish(NAME + ("-fire" if firing else ""), coll)


# --------------------------------------------------------------------------------------------------
# Hidden-face cull (copied from assembly-newshu-15_B / assembly-newsh2-9.py)
# --------------------------------------------------------------------------------------------------
def cull_hidden(obj, grid=3, ndirs=40):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 1.5e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs[:12]:
                for t in (0.4, 0.9):
                    pts.append(c.lerp(vco, t))
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
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


import bpy

def bake_maps(obj, tag, size=1024, samples=48):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
        nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.pack()

    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])




def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    mats = Mats()
    whole = build(coll, mats, firing=False)
    hot = build(coll, mats, firing=True)
    pieces = common.split_assembly(whole, LAYOUT, coll)
    pieces["newshv-91-f2"] = common.split_assembly(hot, [("newshv-91-f2", 0, 0)], coll)["newshv-91-f2"]
    offs = {"newshv-89": -2.0, "newshv-91": 0.0, "newshv-91-f2": 0.0, "newshv-93": 2.0}
    shells = {}
    total = 0
    bpy.context.view_layer.update()
    for name, p in pieces.items():
        # outline shell from the sealed piece before the cull (D90/D118)
        sh = common.outline_shell(p, coll, voxel=0.018, faces=1500, inside=0.012)
        sh.name = sh.data.name = f"{name}_outline"
        shells[name] = sh
        n = cull_hidden(p)
        p.data.set_sharp_from_angle(angle=math.radians(35))
        t = tris(p)
        total += t if name != "newshv-91-f2" else 0
        print(f"{name}: culled {n}; {t} tris; shell {tris(sh)}")
    print("total tris (idle craft)", total)
    for name in pieces:
        pieces[name].location.x = offs[name]
        shells[name].location.x = offs[name]
    bpy.data.objects.remove(whole, do_unlink=True)
    bpy.data.objects.remove(hot, do_unlink=True)

    if "--no-bake" not in ARGV:
        # the shells and the other frame's centre piece stay out of the scene during the bake (D118)
        for sh in shells.values():
            coll.objects.unlink(sh)
        for name, p in pieces.items():
            tag = name.replace("-", "_")
            for i, m in enumerate(list(p.data.materials)):
                c = m.copy()
                c.name = m.name.replace(f"_{TAG}", f"_{tag}")
                p.data.materials[i] = c
            others = [q for n2, q in pieces.items() if n2 != name and {name, n2} == {"newshv-91", "newshv-91-f2"}]
            for q in others:
                coll.objects.unlink(q)
            bake_maps(p, tag)
            for q in others:
                coll.objects.link(q)
        for sh in shells.values():
            coll.objects.link(sh)
    fmt = "AUTO" if "--no-bake" in ARGV else "WEBP"

    sprites = {n: common.load_sprite(ROOT, n)["sprites"] for n in ("newshv-89", "newshv-91", "newshv-93")}

    def frames(keep):
        return [dict(s, frames=[f for f in s["frames"] if f in keep]) for s in sprites["newshv-91"]]

    spr = {"newshv-89": sprites["newshv-89"], "newshv-91": frames({91}),
           "newshv-91-f2": frames({129}), "newshv-93": sprites["newshv-93"]}
    for name in pieces:
        loc = pieces[name].location.x
        pieces[name].location.x = 0
        shells[name].location.x = 0
        if "--no-export" not in ARGV:
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", spr[name],
                                       image_format=fmt)
        if "--pieces" in ARGV:
            pd = Path(ARGV[ARGV.index("--pieces") + 1])
            common.export_glb([pieces[name], shells[name]], pd / f"{name}.glb", image_format=fmt)
        pieces[name].location.x = loc
        shells[name].location.x = loc
    if "--out" in ARGV:
        out = ARGV[ARGV.index("--out") + 1]
        objs = [pieces[n] for n in ("newshv-89", "newshv-91", "newshv-91-f2", "newshv-93")]
        objs += [shells[n] for n in ("newshv-89", "newshv-91", "newshv-91-f2", "newshv-93")]
        common.export_glb(objs, out, image_format=fmt)
    if "--review" in ARGV:
        import os
        sys.path.insert(0, os.environ.get("REVIEW_PY", str(HERE)))
        import review_b
        review_b.review(pieces, shells, Path(ARGV[ARGV.index("--review") + 1]))
    if "--blend" in ARGV:
        bpy.ops.wm.save_as_mainfile(filepath=ARGV[ARGV.index("--blend") + 1])


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
