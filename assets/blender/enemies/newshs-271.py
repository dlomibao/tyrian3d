"""newshs-271 the gun turret riding the grey tank (assembly-newshs-165), AST. CITY 3.2.

The sprite (newshs.shp 271, 24 x 28, ink rows 5-26) read as a machine, in sprite px
(c = column east, r = row south = down the screen, h = up; mirror plane c = 12):
- a round cupola ("head", rows 5-13): a drum with a rounded rim, a groove and a raised flat cap,
  seated on a neck collar that runs into the shoulder block;
- the shoulder block (rows 14-18): a chamfered trapezoid widening to the front, a flat top deck and
  a sloped front glacis (the sprite's dark row 18 is that face in shade); shoulder pads over the arm
  joints (the dark creases at rows 15-17 are the grooves round them);
- two arms reaching out and down from the pads to rounded gauntlets (rows 19-22);
- a thick gun (cols 9-14) out of a mantlet collar under the glacis, a raised collar at row 23, a
  muzzle brake with a top port (the dark pixels at rows 24-25) and a chamfered lip with its bore.
Grey hard surface like the tank (palette_material metallic 0.35 roughness 0.5), AO/roughness bake
only. Each part takes the sprite's palette index for its region; the bright stripe down the barrel,
the rim's bright arc and the lit edges are sheen. The underside is a plain closed shape.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshs-271.py  (flags: --no-bake)
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshs-271"
TAG = "nshs271"
MODEL = f"enemies/{NAME}"
PX = 1 / 12
CX = 12.0  # mirror plane (pixel edges)
SMOOTH = 35.0
SINK_IN = float(next((a.split("=")[1] for a in sys.argv if a.startswith("sinkin=")), "0.012"))

MATS = []
SLOT = {}


def make_materials(sprite):
    def add(idx, metallic=0.35, roughness=0.5):
        SLOT[idx] = len(MATS)
        MATS.append(common.palette_material(sprite, idx, TAG, metallic=metallic, roughness=roughness))
    for i in (2, 4, 5, 7, 8, 9, 10, 11):
        add(i)
    SLOT["gun"] = len(MATS)  # machined gun steel: same index, smoother, so the sheen stripe shows
    MATS.append(common.palette_material(sprite, 8, TAG + "-gun", metallic=0.55, roughness=0.32))


def M(i):
    return SLOT[i]


# ----------------------------------------------------------------------------------------------
# Geometry helpers (sprite px)
# ----------------------------------------------------------------------------------------------

def area2(poly):
    a = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a += p[0] * q[1] - q[0] * p[1]
    return a


def inset(poly, d):
    """Inward miter offset of a simple polygon by d (copied from assembly-newshs-165.py)."""
    if d <= 0:
        return [tuple(p) for p in poly]
    n = len(poly)
    s = 1.0 if area2(poly) > 0 else -1.0
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * s, dx / ln * s
        lines.append((a[0] + nx * d, a[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        l1, l2 = lines[(i - 1) % n], lines[i]
        den = l1[2] * l2[3] - l1[3] * l2[2]
        if abs(den) < 1e-9:
            out.append((l2[0], l2[1]))
            continue
        t = ((l2[0] - l1[0]) * l2[3] - (l2[1] - l1[1]) * l2[2]) / den
        out.append((l1[0] + l1[2] * t, l1[1] + l1[3] * t))
    return out


def mirror(pts):
    return [(2 * CX - c, r) for c, r in pts]


def box(P, c0, c1, r0, r1, h0, h1, mat, ch=0.2):
    ch = min(ch, (c1 - c0) / 2.05, (r1 - r0) / 2.05, (h1 - h0) / 2.05)
    T.hull(P, T.cbox(c0, c1, r0, r1, h0, h1, ch), M(mat))


def cyl(P, p0, p1, rad, mat, n=12, ch=0.0, cap_mat=None):
    """A cylinder from p0 to p1 (the p1 end chamfered by ch)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    e1 = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized()
    e2 = d.cross(e1)

    def ring(p, rr):
        return [P.v(tuple(p + rr * (math.cos(2 * math.pi * k / n) * e1 + math.sin(2 * math.pi * k / n) * e2)))
                for k in range(n)]
    A = ring(p0, rad)
    B = ring(p1 - d * ch, rad) if ch > 0 else None
    Cc = ring(p1, rad - ch) if ch > 0 else ring(p1, rad)
    B = B or Cc
    cen = tuple((p0 + p1) / 2)
    for k in range(n):
        j = (k + 1) % n
        P.f((A[k], A[j], B[j], B[k]), M(mat), away=cen)
        if ch > 0:
            P.f((B[k], B[j], Cc[j], Cc[k]), M(mat), away=cen)
    P.f(A, M(mat), out=tuple(-d))
    P.f(Cc, M(cap_mat if cap_mat is not None else mat), out=tuple(d))


def lathe(P, origin, axis, e1, e2, prof, n=32, shape=None, close0=True, close1=True):
    """A surface of revolution round `axis` through `origin`. prof: [(radius, axial, mat)], the
    mat of station k colours the band from k-1 to k. shape(t) -> (sx, sy) multiplies the radius
    along e1/e2 (a superellipse plan). Ends with zero radius are poles; others are capped."""
    o, a, u, w = Vector(origin), Vector(axis).normalized(), Vector(e1), Vector(e2)
    rings = []
    for rad, ax, _m in prof:
        ring = []
        for k in range(n):
            t = 2 * math.pi * k / n
            sx, sy = shape(t) if shape else (math.cos(t), math.sin(t))
            ring.append(P.v(tuple(o + a * ax + u * (rad * sx) + w * (rad * sy))))
        rings.append(ring)
    for i in range(1, len(prof)):
        r0, a0, _ = prof[i - 1]
        r1, a1, m = prof[i]
        nax, nrad = -(r1 - r0), (a1 - a0)
        for k in range(n):
            j = (k + 1) % n
            t = 2 * math.pi * (k + 0.5) / n
            sx, sy = shape(t) if shape else (math.cos(t), math.sin(t))
            radial = (u * sx + w * sy).normalized()
            out = tuple(a * nax + radial * nrad)
            P.f((rings[i - 1][k], rings[i - 1][j], rings[i][j], rings[i][k]), M(m), out=out)
    if close0 and prof[0][0] > 1e-6:
        P.f(rings[0], M(prof[0][2]), out=tuple(-a))
    if close1 and prof[-1][0] > 1e-6:
        P.f(rings[-1], M(prof[-1][2]), out=tuple(a))


def superellipse(n_north, n_south, rx, ry_n, ry_s):
    """Plan shape in (c, r): north (r < centre) rounder than south."""
    def f(t):
        c, s = math.cos(t), math.sin(t)
        ex = 2.0 / (n_north if s < 0 else n_south)
        x = math.copysign(abs(c) ** ex, c) * rx
        y = math.copysign(abs(s) ** ex, s) * (ry_n if s < 0 else ry_s)
        return x, y
    return f


def sector_extrude(P, axis_pt, r0, r1, rad_out, rad_in, gap_deg, mat, inner_mat, n=28, ch=0.15):
    """A tube along +r (barrel axis at axis_pt=(c, h)) with a slot gap_deg wide cut out of its top:
    the muzzle brake's cheeks. Outer edges chamfered by ch at both ends."""
    c0, h0 = axis_pt
    g = math.radians(gap_deg) / 2
    angs = [math.pi / 2 + g + (2 * math.pi - 2 * g) * k / (n - 1) for k in range(n)]

    def pt(rr, ang, r):
        return P.v((c0 + rr * math.cos(ang), r, h0 + rr * math.sin(ang)))
    st = [(r0, rad_out - ch), (r0 + ch, rad_out), (r1 - ch, rad_out), (r1, rad_out - ch)]
    outer = [[pt(rr, a, r) for a in angs] for r, rr in st]
    inner0 = [pt(rad_in, a, r0) for a in angs]
    inner1 = [pt(rad_in, a, r1) for a in angs]
    for i in range(3):
        for k in range(n - 1):
            am = (angs[k] + angs[k + 1]) / 2
            rv = (math.cos(am), 0, math.sin(am))
            ax = -1 if i == 0 else (1 if i == 2 else 0)
            P.f((outer[i][k], outer[i][k + 1], outer[i + 1][k + 1], outer[i + 1][k]), M(mat),
                out=(rv[0], ax, rv[2]))
    for k in range(n - 1):
        am = (angs[k] + angs[k + 1]) / 2
        rv = (-math.cos(am), 0, -math.sin(am))
        P.f((inner0[k], inner0[k + 1], inner1[k + 1], inner1[k]), M(inner_mat), out=rv)
        P.f((inner0[k], inner0[k + 1], outer[0][k + 1], outer[0][k]), M(mat), out=(0, -1, 0))
        P.f((inner1[k], inner1[k + 1], outer[3][k + 1], outer[3][k]), M(mat), out=(0, 1, 0))
    # slot walls
    for k, sgn in ((0, 1), (n - 1, -1)):
        a = angs[k]
        tang = (-math.sin(a) * sgn * -1, 0, math.cos(a) * sgn * -1)
        P.f((inner0[k], inner1[k], outer[3][k], outer[2][k], outer[1][k], outer[0][k]), M(mat), out=tang)


def finish(P, coll):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for mat in MATS:
        me.materials.append(mat)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    return obj


def weighted(o):
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(SMOOTH))
    wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(o)


def sink_shell(shell, model, margin, reach):
    """newshv-10.py's sink_shell (copied): drop every outline-shell vertex to `margin` under the
    lowest top surface within `reach` (seen from above), so the ink stays on the silhouette (D90/D118)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


# ----------------------------------------------------------------------------------------------
# The turret
# ----------------------------------------------------------------------------------------------
HEAD_C = (12.0, 9.35)
CAP_R = 8.6
HEAD = superellipse(2.5, 4.0, 5.0, 4.6, 3.75)
SH_TOP = 8.0       # shoulder deck height
LIFT = 3.0         # head raised onto the deck
GLACIS = (17.3, 6.6)  # glacis: from r 17.3 down to h 6.6 at the front edge (over the mantlet)
GUN_H = 3.3        # gun axis height
GUN_R = 2.9


def head(P):
    c, r = HEAD_C
    # (scale, h, mat): drum, rounded rim, groove, raised cap
    # the lower body under the cupola runs down to the turret ring (a drum, a seam lip at the joint)
    prof = [(0.0, -1.8, 4), (0.8, -1.8, 4), (0.94, -1.3, 8), (0.975, -0.8, 8), (0.975, 3.2, 8), (1.0, 3.4, 8),
            (1.0, 3.9, 8), (0.965, 4.05, 8), (0.965, 4.7, 8), (1.0, 4.95, 9), (1.0, 5.5, 9), (1.0, 6.75, 9), (0.985, 7.2, 10),
            (0.95, 7.5, 10), (0.88, 7.62, 10), (0.80, 7.45, 10), (0.76, 7.25, 7), (0.0, 7.25, 7)]
    lathe(P, (c, r, LIFT), (0, 0, 1), (1, 0, 0), (0, 1, 0),
          [(s, h, m) for s, h, m in prof], n=32, shape=HEAD)
    # the round cap in the rim (the sprite's ring of 10s round the 9s, rows 6-10)
    cap = [(3.3, 7.1, 9), (3.3, 7.55, 9), (3.2, 7.95, 9), (2.95, 8.15, 9), (2.3, 8.22, 9), (0.0, 8.25, 9)]
    lathe(P, (c, CAP_R, LIFT), (0, 0, 1), (1, 0, 0), (0, 1, 0), cap, n=28)
    r = CAP_R
    # the cap is a hatch: a hinge block at its rear, a grab handle at its front, a bolt ring
    box(P, c - 1.3, c + 1.3, r - 3.35, r - 2.55, LIFT + 7.7, LIFT + 8.6, 8, ch=0.2)
    cyl(P, (c - 1.5, r - 2.95, LIFT + 8.2), (c + 1.5, r - 2.95, LIFT + 8.2), 0.32, 8, n=10, ch=0.08)
    for x in (-0.9, 0.9):
        box(P, c + x - 0.18, c + x + 0.18, r + 1.6, r + 1.95, LIFT + 8.1, LIFT + 8.6, 8, ch=0.06)
    box(P, c - 1.05, c + 1.05, r + 1.6, r + 1.95, LIFT + 8.45, LIFT + 8.7, 8, ch=0.08)
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        bc, br = c + 2.75 * math.cos(a), r + 2.75 * math.sin(a)
        cyl(P, (bc, br, LIFT + 8.0), (bc, br, LIFT + 8.28), 0.2, 8, n=6, ch=0.06)
    # neck collar under the head, running into the shoulder deck
    neck = [(7.1, 11.0), (16.9, 11.0), (16.9, 14.4), (7.1, 14.4)]
    prism_hull(P, neck, SH_TOP - 0.5, LIFT + 5.55, 0.35, 8)
    # stowage box with a louvred vent on the body's rear
    box(P, 9.4, 14.6, 5.0, 6.2, 2.4, 5.6, 8, ch=0.2)
    for k in range(3):
        box(P, 9.9, 14.1, 4.85, 5.15, 3.0 + 0.8 * k, 3.35 + 0.8 * k, 5, ch=0.05)


def prism_hull(P, poly, h0, h1, ch, mat):
    """A convex chamfered prism (top edges chamfered by ch) as a hull."""
    pts = [(c, r, h0) for c, r in poly] + [(c, r, h1 - ch) for c, r in poly]
    pts += [(c, r, h1) for c, r in inset(poly, ch)]
    T.hull(P, pts, M(mat))


SH_PLAN = [(6.3, 13.6), (17.7, 13.6), (18.7, 14.9), (19.6, 16.8), (20.6, 18.25), (20.3, 18.95),
           (3.7, 18.95), (3.4, 18.25), (4.4, 16.8), (5.3, 14.9)]


def sh_top(c, r):
    r0, h1 = GLACIS
    if r <= r0:
        return SH_TOP
    return SH_TOP - (r - r0) * (SH_TOP - h1) / (18.95 - r0)


def shoulder(P):
    poly = SH_PLAN
    ch = 0.45
    pts = [(c, r, 1.2) for c, r in inset(poly, 0.7)]
    pts += [(c, r, sh_top(c, r) - ch) for c, r in poly]
    ip = inset(poly, ch)
    pts += [(c, r, sh_top(c, r)) for c, r in ip]
    # the crease where the deck meets the glacis
    for c in (4.75, 19.25):
        pts.append((c, GLACIS[0], SH_TOP))
    T.hull(P, pts, M(10))
    # raised centre deck plate (between the pads), with a seam either side and bolts
    plate = [(8.0, 14.3), (16.0, 14.3), (16.4, 16.2), (7.6, 16.2)]
    prism_hull(P, plate, SH_TOP - 0.3, SH_TOP + 0.22, 0.12, 10)
    for c in (8.6, 15.4):
        cyl(P, (c, 15.6, SH_TOP), (c, 15.6, SH_TOP + 0.4), 0.26, 8, n=8, ch=0.08)
    # glacis: two vent louvres either side of the gun
    for c0 in (6.0, 15.0):
        for k in range(3):
            r = 17.05 + 0.6 * k
            h = sh_top(c0, r)
            box(P, c0, c0 + 3.0, r, r + 0.32, h - 0.25, h + 0.12, 5, ch=0.05)
    # rear face: an access hatch with hinges, and two stiffener ribs
    box(P, 9.2, 14.8, 13.35, 13.75, 3.0, 6.9, 9, ch=0.15)
    for c in (9.9, 14.1):
        cyl(P, (c - 0.45, 13.4, 6.4), (c + 0.45, 13.4, 6.4), 0.28, 8, n=8)
    for c in (6.9, 17.1):
        box(P, c - 0.4, c + 0.4, 13.3, 13.8, 1.8, 7.4, 8, ch=0.12)
    # shoulder pads over the arm joints
    for s in (1, -1):
        cx = CX + s * 6.6
        cyl(P, (cx - 1.6 * s, 16.7, SH_TOP - 0.6), (cx + 0.9 * s, 17.5, SH_TOP - 1.2), 1.75, 9, n=20, ch=0.35)
        cyl(P, (cx - 1.9 * s, 16.6, SH_TOP - 0.55), (cx - 1.6 * s, 16.7, SH_TOP - 0.6), 1.35, 7, n=20)


ARM = [((6.4, 17.2, 6.4), (3.2, 20.8, 2.2))]


def arms(P):
    for s in (1, -1):
        def m(p):
            return (CX + s * (p[0] - CX), p[1], p[2])
        (a, b), = ARM
        a, b = Vector(m(a)), Vector(m(b))
        d = (b - a).normalized()
        # upper arm: a tapered square-ish tube with chamfers (hull), and a hydraulic rod under it
        e1 = d.cross(Vector((0, 0, 1))).normalized()
        e2 = e1.cross(d).normalized()
        pts = []
        for p, hw, hh in ((a, 1.75, 1.15), (b - d * 0.4, 1.5, 1.0)):
            for u in (-1, 1):
                for v in (-1, 1):
                    for cu, cv in ((1.0, 0.72), (0.72, 1.0)):
                        q = p + e1 * (u * hw * cu) + e2 * (v * hh * cv)
                        pts.append(tuple(q))
        T.hull(P, pts, M(9))
        # armour strip along the arm top
        pts = []
        for p, hw in ((a + d * 0.6, 0.75), (b - d * 0.9, 0.6)):
            for u in (-1, 1):
                for v, k in ((0.0, 1.0), (0.3, 0.7)):
                    pts.append(tuple(p + e1 * (u * hw * k) + e2 * (1.0 + v)))
        T.hull(P, pts, M(10))
        # gauntlet: a rounded pod at the arm's end, pointing out and down, with a seam and a port
        g = b + d * 0.35
        ax = Vector((s * -0.75, 0.6, -0.3)).normalized()
        f1 = ax.cross(Vector((0, 0, 1))).normalized()
        f2 = f1.cross(ax).normalized()
        prof = [(0.0, -1.55, 9), (1.05, -1.4, 9), (1.6, -0.9, 9), (1.85, -0.2, 9), (1.85, 0.25, 9),
                (1.95, 0.3, 8), (1.95, 0.6, 8), (1.8, 0.65, 8), (1.6, 1.15, 9), (1.25, 1.45, 9),
                (0.75, 1.5, 9), (0.65, 1.3, 2), (0.0, 1.25, 2)]
        lathe(P, tuple(g), tuple(ax), tuple(f1), tuple(f2), prof, n=20)


def gun(P):
    c, h = CX, GUN_H
    axis = (0, 1, 0)
    e1, e2 = (1, 0, 0), (0, 0, 1)
    # mantlet collar under the glacis, the barrel, the raised collar
    prof = [(0.0, 15.2, 8), (GUN_R, 15.2, 8), (GUN_R, 18.3, 8), (3.7, 18.5, 8), (3.95, 18.75, 8),
            (3.95, 19.7, 8), (3.6, 20.0, 8), (GUN_R - 0.12, 20.0, 7), (GUN_R - 0.12, 22.75, "gun"),
            (GUN_R + 0.1, 22.9, 8), (GUN_R + 0.1, 23.55, 8), (GUN_R - 0.2, 23.7, 8),
            (2.0, 23.7, 2), (2.0, 26.0, 2), (0.0, 26.0, 2)]
    lathe(P, (c, 0, h), axis, e1, e2, prof, n=32)
    # muzzle brake cheeks with the top port, and the chamfered lip with its bore
    sector_extrude(P, (c, h), 23.65, 25.95, GUN_R - 0.05, 2.0, 70, 8, 4, ch=0.12)
    lip = [(1.15, 25.9, 4), (GUN_R - 0.05, 25.9, 8), (GUN_R - 0.05, 26.25, 8), (2.25, 26.75, 8),
           (1.15, 26.75, 8), (1.15, 26.55, 2), (0.0, 26.55, 2)]
    lathe(P, (c, 0, h), axis, e1, e2, lip, n=32, close0=False)
    # breech housing at the back (under the shoulder, closes the gun's root) - underside only
    box(P, c - 3.4, c + 3.4, 14.0, 16.0, 0.6, 3.6, 5, ch=0.3)


def base(P):
    """Turret ring and a plain closed underside."""
    lathe(P, (CX, 12.6, 0), (0, 0, 1), (1, 0, 0), (0, 1, 0),
          [(0.0, 0.3, 4), (4.6, 0.3, 4), (5.0, 0.7, 5), (5.0, 1.6, 5), (4.6, 1.8, 5)], n=32, close1=True)


def build(coll, sprite):
    make_materials(sprite)
    P = T.Part(NAME, smooth_angle=SMOOTH)
    base(P)
    shoulder(P)
    head(P)
    arms(P)
    gun(P)
    return finish(P, coll)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite)
    weighted(obj)
    t = tris(obj)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {t} triangles")
    sealed = obj.copy()  # D90/D118: the outline shell from a sealed pre-cull copy
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=3000, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    if "--no-sink" not in argv:
        sink_shell(shell, sealed, 0.5 * PX, 1.2 * PX)
        # sinking drops the shell's side rings under overhangs (the cupola over its body, the pads over
        # the arms) outside the narrower part below; pull every vertex back inside the model again
        sw = shell.modifiers.new("inside2", "SHRINKWRAP")
        sw.target = sealed
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -SINK_IN
        common._apply_modifiers(shell)
    bpy.data.objects.remove(sealed, do_unlink=True)
    bpy.context.view_layer.update()
    assert len(shell.data.polygons) > 0, "empty outline shell"
    shell.hide_render = True
    fmt = "AUTO"
    if "--no-bake" not in argv:
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(range(len(MATS)))
        T.bake_maps(obj, tempfile.mkdtemp(prefix="nshs271_bake_"), size=512, samples=64)
        fmt = "WEBP"
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
