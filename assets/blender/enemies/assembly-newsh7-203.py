"""Red mortar turret on the ice edge (newsh7-169 over newsh7-203) and the glowing core in the ice
(newsh7-55), design A: balance of sprite fidelity, game-camera readability and engineering detail.

What they are (episode 3, CAMANIS):
- The turret is one 24x56 px emplacement standing on the ice (type 85 newsh7-169 directly above
  type 86 newsh7-203, both terrain-fixed on the ground layer). Top to bottom of the screen:
  - an armoured red housing (rows 1-10): a faired dome, round where the sprite is round, with a
    raised square hatch on its crown (columns 7-14, rows 2-8; a hinge at its back edge and a dark
    louvred vent in its front half, the sprite's 112-114 block) and a modelled seam across its brow;
  - side skirts (columns 2 / 19, rows 9-14) and two claws (columns 4-6 / 15-17) running forward to
    row 19, each a ridged arm sloping down to the ice; between them the gun mantlet (rows 11-12)
    with a front sight blade (columns 10-11, rows 13-14);
  - the barrel cradle in the gun slot (rows 13-21): a dark trough, two bright rails (columns 8 and
    13) on posts, and a strap across the barrel (rows 16-17);
  - the barrel (columns 9-12) through a red collar (rows 22-24) with two low cheeks either side
    (rows 24-26), a flange (rows 26-27), then a grey bell-shaped end knob (rows 28-32);
  - the recoil slide: a red-hot joint (glow, D126) on a rod out of the knob's mouth, and the mortar
    cup, a bowl opening up (rim at z 5.4 px, its dark bore, a hooped and bolted outer wall and a
    firing striker), slid out by 0, 1 and 3 px (frames 203, 205, 207: models newsh7-203,
    newsh7-203-f2, newsh7-203-f3).
  The bright L on the dome's left shoulder, the bright claw tips and the cup's rim streaks are
  sheen (art rule 2), not geometry. The sprite's dark ring and the drop shadow cast right on the
  ice are lighting / the game's ink: nothing models them. The ice is ground (D130): no plate.
- newsh7-55 is a glowing core set in the ice: a low ice mound (at most ~1 px, marked
  `tyrian_ground`: ground, no shadow, outside the outline shell), a bronze socket ring with five
  grey clamps where the sprite has grey spots, a red inner lip lit by the core, and the core dome
  (pal 117, orange 122 on frame 93, white 127 on 131) with a frame-tagged hot spot (126/127 on
  55/131) and a pink highlight (75/79 on frame 93).

Colours: each part takes the median palette index of its sprite region (darkest shading and
brightest sheen trimmed): housing, hatch, claws, mantlet 117, skirts and collar 115, cheeks 114,
rails 11, strap 8, trough 4, barrel 5, knob and flange 6, joint 117 (glowing), cup wall 4 and
rim/hoop 5 (a dark gunmetal ball; its upper-left highlight is sheen), upper bore 4, lower bore 4 / floor 3, striker 12; socket 166, lip 71, clamps 9, mound
ice 58. Greys are satin (metallic 0.3-0.35, F0 raised via Specular IOR Level 1.0, D176).

Output: the game files via common.export_sprite_model (public/models/enemies/<model>.glb and the
spriteModels entries). With --review DIR it also writes review copies to DIR:
  assembly-newsh7-203.glb     every game node: newsh7-169, newsh7-203, newsh7-203-f2,
                              newsh7-203-f3 (each with its _outline) in assembly position, the
                              slide-k variant moved +3k units in X; newsh7-55 (+ frame parts and
                              its _outline) at X -3.
  pieces/<model>.glb          one per game file, at its own origin.
  wholes.glb                  the uncut turret per slide and the 55 core (for review renders).
  build_info.json             triangle and shell face counts.

    blender -b --factory-startup -P assembly-newsh7-203.py -- [--review DIR]
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

NAME = "assembly-newsh7-203"
TOP, GUN, CORE = "newsh7-169", "newsh7-203", "newsh7-55"
PX = 1 / 12
AX = 11.0  # the turret's centre line (pixel-edge column): symmetric about column 10.5
ZB = 4.0  # barrel axis height (px)
SLIDES = (0, 1, 3)  # frames 203, 205, 207
CX0, CY0 = 272, 6  # screen centre of the left turret's 24x56 block (as the shipped script)
SPACING = 3.0


def P(u, v, z):
    """Assembly pixel-edge column u, row v (0-56; 28 is the cut between the pieces), height z px."""
    return Vector(((u - 12) * PX, (28 - v) * PX, z * PX))


def Pc(u, v, z):
    """newsh7-55's own 24x28 grid."""
    return Vector(((u - 12) * PX, (14 - v) * PX, z * PX))


def pchip(xs, ys):
    """Monotone cubic interpolation (copy of usp_talon.pchip)."""
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
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


# --- mesh helpers (copied in; lib_b108 / lib_b007 stay untouched) ----------------------------------

def loft(bm, rings, mat, cap0=True, cap1=True, smooth=True, conv=None):
    """Join rings of world points (equal counts; a 1-point ring is a tip) in order. `mat` is an int,
    a list (one per band) or a function (face centre in px space via `conv`) -> material index."""
    def mi(face, band):
        if callable(mat):
            c = sum((v.co for v in face.verts), Vector()) / len(face.verts)
            return mat(conv(c) if conv else c / PX)
        if isinstance(mat, list):
            return mat[min(band, len(mat) - 1)]
        return mat
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for b, (r0, r1) in enumerate(zip(vs, vs[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[j], r1[i]))
            elif len(r1) == 1:
                f = bm.faces.new((r0[i], r0[j], r1[0]))
            else:
                f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mi(f, b)
            f.smooth = smooth
    for ring, on, rev, band in ((vs[0], cap0, True, 0), (vs[-1], cap1, False, len(vs) - 2)):
        if not on or len(ring) < 3:
            continue
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ring[j], ring[i], c) if rev else (ring[i], ring[j], c))
            f.material_index = mi(f, band)
            f.smooth = False
    return vs


def yring(v, r, uc=AX, zc=ZB, n=16, rz=None, F=P):
    """A ring round an axis along the rows (barrel direction) at row v."""
    rz = r if rz is None else rz
    return [F(uc + r * math.cos(2 * math.pi * (k + 0.5) / n), v, zc + rz * math.sin(2 * math.pi * (k + 0.5) / n))
            for k in range(n)]


def vring(uc, vc, z, rx, ry, n=16, F=P):
    """A horizontal ellipse ring (vertical axis) at height z."""
    return [F(uc + rx * math.cos(2 * math.pi * (k + 0.5) / n), vc + ry * math.sin(2 * math.pi * (k + 0.5) / n), z)
            for k in range(n)]


def sering(uc, vc, z, rx, ry, n=16, p=2.4, F=P):
    """A horizontal superellipse ring (|x/rx|^p + |y/ry|^p = 1) at height z."""
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        out.append(F(uc + rx * math.copysign(abs(c) ** (2 / p), c), vc + ry * math.copysign(abs(s) ** (2 / p), s), z))
    return out


# The cup's plan (half width by pixel-edge row of the frame-203 drawing, rows 35-49): flat-backed
# where it meets the joint, round at its front (inner mask rows 7-21 of the frame).
CUP_V = [35.0, 35.5, 36.5, 37.5, 38.5, 40.0, 42.0, 44.0, 45.0, 46.0, 47.0, 48.0, 48.7, 49.0]
CUP_HW = [1.6, 3.0, 4.45, 5.45, 5.95, 6.05, 6.05, 6.0, 5.6, 4.75, 3.7, 2.55, 1.5, 0.0]
cup_hw = pchip(CUP_V, CUP_HW)
CUP_C = 42.0


def cup_outline(n=18):
    """Closed plan outline of the cup (du, dv from (AX, CUP_C)), clockwise from the back."""
    vs = [35.0 + 14.0 * (1 - math.cos(math.pi * i / (n - 1))) / 2 for i in range(n)]
    right = [(cup_hw(v), v - CUP_C) for v in vs]
    left = [(-cup_hw(v), v - CUP_C) for v in reversed(vs[1:-1])]
    return [(0.0, vs[0] - CUP_C)] + right[1:-1] + [(0.0, vs[-1] - CUP_C)] + left


CUP_PLAN = cup_outline()


def cup_ring(vc, z, s):
    return [P(AX + du * s, vc + dv * s, z) for du, dv in CUP_PLAN]


def catmull_closed(pts, per=4):
    """A closed Catmull-Rom spline through (u, v) points, `per` samples per span."""
    out, n = [], len(pts)
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return out


# newsh7-55's socket plan, traced round the sprite's non-ice pixels (rows 7-14, columns 6-16),
# clockwise from the top; its rings are this outline scaled about SOCK_C.
SOCK_C = (11.9, 11.0)
SOCK_PLAN = catmull_closed([(9.0, 7.05), (11.5, 6.95), (14.2, 7.1), (15.45, 7.85), (16.4, 8.9), (17.0, 10.1),
                            (17.0, 11.6), (16.75, 12.8), (16.2, 14.0), (15.2, 14.9), (12.0, 15.05),
                            (8.8, 14.9), (7.5, 14.0), (6.25, 12.5), (6.8, 11.1), (7.0, 9.6), (7.4, 8.3),
                            (8.0, 7.45)], per=3)


def sock_ring(z, s):
    cu, cv = SOCK_C
    return [Pc(cu + (u - cu) * s, cv + (v - cv) * s, z) for u, v in SOCK_PLAN]


def arch(v, hw, h, zs, uc=AX, n=16, p=2.4, F=P):
    """A section standing on the ground across the rows: vertical sides to zs, a superellipse crown
    to h; closed along the ground."""
    pts = [F(uc + hw, v, 0.0)]
    for i in range(n + 1):
        a = math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        x = hw * math.copysign(abs(c) ** (2 / p), c)
        z = zs + (h - zs) * abs(s) ** (2 / p)
        pts.append(F(uc + x, v, z))
    pts.append(F(uc - hw, v, 0.0))
    return pts


def crect(uc, v, hw, z0, z1, c, F=P):
    """A chamfered rectangle across the rows at row v (8 points)."""
    pts = [(hw, z0), (hw, z1 - c), (hw - c, z1), (-hw + c, z1), (-hw, z1 - c), (-hw, z0 + 0.0)]
    pts = [(hw, z0), (hw, z1 - c), (hw - c, z1), (-hw + c, z1), (-hw, z1 - c), (-hw, z0)]
    return [F(uc + x, v, z) for x, z in pts]


def ridge(uc, v, hw, zc, F=P):
    """A ridged arm section: vertical flanks, chamfered shoulders, a crest along the middle."""
    pts = [(hw, 0.0), (hw, zc - 1.0), (hw - 0.45, zc - 0.4), (0.0, zc), (-hw + 0.45, zc - 0.4), (-hw, zc - 1.0),
           (-hw, 0.0)]
    return [F(uc + x, v, max(0.0, z)) for x, z in pts]


def sweep(bm, path, rw, rh, n=8, mat=0, caps=True, F=P):
    """A tube along a polyline of px points (u, v, z): rw half width across the path in plan, rh
    half height. Mitred joints."""
    pts = [F(*p) for p in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, c in enumerate(pts):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        t.normalize()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((0, 1, 0))
        side.normalize()
        vert = side.cross(t).normalized()
        if vert.z < 0:
            vert = -vert
        k = 1.0
        if d0 is not None and d1 is not None:
            k = 1.0 / max(0.6, math.cos(0.5 * d0.angle(d1, 0.0)))
        rings.append([c + rw * PX * math.cos(2 * math.pi * (j + 0.5) / n) * side
                      + rh * PX * k * math.sin(2 * math.pi * (j + 0.5) / n) * vert for j in range(n)])
    return loft(bm, rings, mat, caps, caps)


def cyl_z(bm, uc, vc, z0, z1, r, n=8, mat=0, F=P, chamfer=0.0):
    """A vertical post/boss (optionally chamfered top)."""
    rings = [vring(uc, vc, z0, r, r, n, F)]
    if chamfer:
        rings += [vring(uc, vc, z1 - chamfer, r, r, n, F), vring(uc, vc, z1, r - chamfer, r - chamfer, n, F)]
    else:
        rings.append(vring(uc, vc, z1, r, r, n, F))
    loft(bm, rings, mat, smooth=False)


# --- the turret ------------------------------------------------------------------------------------

# Housing plan (half width from the centre line) and heights by pixel-edge row: fitted to the inner
# mask (D74): rows 1: 6, 2: 7, 3-4: 8, 5-14: 9, with a rounded back.
DOME_V = [0.85, 1.25, 2.0, 3.0, 4.0, 5.2, 7.0, 9.0, 10.5, 10.95]
DOME_HW = [5.0, 5.95, 6.95, 7.85, 8.35, 8.9, 9.0, 9.0, 9.0, 8.8]
DOME_H = [1.3, 2.9, 4.4, 5.5, 6.25, 6.75, 7.0, 6.9, 6.5, 5.6]
DOME_ZS = [0.4, 0.8, 1.0, 1.1, 1.2, 1.25, 1.3, 1.3, 1.3, 1.3]
dome_hw, dome_h, dome_zs = pchip(DOME_V, DOME_HW), pchip(DOME_V, DOME_H), pchip(DOME_V, DOME_ZS)
DP = 2.4


def dome_z(u, v):
    hw, h, zs = dome_hw(v), dome_h(v), dome_zs(v)
    s = min(1.0, abs(u - AX) / hw)
    return zs + (h - zs) * max(0.0, 1 - s ** DP) ** (1 / DP)


def build_turret(sprite, coll, d):
    tag = "n7_203"

    def pal(i, metallic=0.45, roughness=0.4, spec=None, tag=tag, **kw):
        m = common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness, **kw)
        if spec is not None:
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            b.inputs["Specular IOR Level"].default_value = spec
        return m

    mats = [
        pal(117, 0.4, 0.38),   # 0 housing, hatch, claws, mantlet (satin red armour)
        pal(115, 0.4, 0.42),   # 1 skirts, collar, hinge
        pal(114, 0.35, 0.5),   # 2 cheeks
        pal(113, 0.3, 0.6),    # 3 vent recess
        pal(4, 0.4, 0.55),     # 4 trough, bore wall
        pal(11, 0.35, 0.3, spec=1.0),    # 5 rails
        pal(8, 0.35, 0.35, spec=1.0),     # 6 strap, rod
        pal(5, 0.35, 0.4, spec=1.0),      # 7 barrel
        pal(6, 0.3, 0.32, spec=1.0),     # 8 knob, flange, cup wall
        pal(9, 0.35, 0.3, spec=1.0),    # 9 posts, hoop, bolts, knob band
        pal(10, 0.3, 0.3, spec=1.0),    # 10 cup rim
        pal(3, 0.3, 0.6),      # 11 cup floor, knob mouth
        pal(12, 0.35, 0.28, spec=1.0),    # 12 striker
        common.palette_material(sprite, 117, f"{tag}-hot", metallic=1.0, roughness=0.9, emission_strength=0.85),  # 13 joint
        pal(4, 0.35, 0.4, spec=1.0, tag=f"{tag}-cup"),  # 14 cup wall: dark gunmetal ball (sprite median 3-4)
    ]
    RED, RED2, RED3, VENT, TROUGH, RAIL, STRAP, BARREL, KNOB, STEEL, RIM, FLOOR, PIN, HOT, CUPW = range(15)
    RIM = BARREL  # the cup rim is pal_5 satin gunmetal: the sun's sheen makes the sprite's upper-left highlight
    bm = bmesh.new()

    # Housing: a faired dome, with a modelled seam across the brow (rows 9.2-9.7).
    vs = []
    for v in DOME_V[:-2] + [9.15, 9.3, 9.55, 9.7, 10.5, 10.95]:
        vs.append(v)
    vs = sorted(set([0.85, 1.05, 1.25, 1.6, 2.0, 2.5, 3.0, 3.5, 4.0, 4.6, 5.2, 6.0, 7.0, 8.0, 9.15, 9.3, 9.55,
                     9.7, 10.5, 10.95]))
    rings = []
    for v in vs:
        dip = 0.18 if v in (9.3, 9.55) else 0.0
        rings.append(arch(v, dome_hw(v) - dip, dome_h(v) - dip * 1.6, dome_zs(v), n=20, p=DP))
    loft(bm, rings, RED)

    # Hatch on the crown (columns 7-14, rows 2-8): a plate standing 0.5 px proud, following the
    # dome, chamfered all round; hinge along its back edge; a louvred vent in its front half.
    def hatch_ring(v, hw, lift, sink=0.5, n=9):
        top = []
        for i in range(n):
            s = -1 + 2 * i / (n - 1)
            u = AX + s * hw
            top.append(P(u, v, dome_z(u, v) + lift))
        ends = [P(AX + hw + 0.35, v, dome_z(AX + hw + 0.35, v) - sink), P(AX - hw - 0.35, v, dome_z(AX - hw - 0.35, v) - sink)]
        return [ends[1]] + top + [ends[0]]
    hv = [(2.15, 3.35, 0.15), (2.45, 3.75, 0.5), (8.25, 3.75, 0.5), (8.6, 3.35, 0.15)]
    loft(bm, [hatch_ring(v, hw, lift) for v, hw, lift in hv], RED, smooth=False)
    sweep(bm, [(AX - 3.2, 2.55, dome_z(AX - 3.2, 2.55) + 0.55), (AX + 3.2, 2.55, dome_z(AX + 3.2, 2.55) + 0.55)],
          0.42, 0.42, n=10, mat=RED2)
    # Vent: a dark recess panel with three slats across it (the sprite's dark block, rows 6-8).
    vv = [(5.85, 2.1, 0.5), (6.0, 2.1, 0.56), (8.0, 2.1, 0.56), (8.15, 2.1, 0.5)]
    loft(bm, [hatch_ring(v, hw, lift, sink=0.0, n=7) for v, hw, lift in vv], VENT, smooth=False)
    for v in (6.45, 7.05, 7.65):
        sweep(bm, [(AX - 2.0, v, dome_z(AX - 2.0, v) + 0.62), (AX + 2.0, v, dome_z(AX + 2.0, v) + 0.62)],
              0.2, 0.16, n=6, mat=RED)

    # Side skirts (columns 2 / 19, rows 9-14), sloping down from the dome's flank.
    for sx in (-1, 1):
        uc = AX + sx * 8.15
        top0 = dome_z(uc, 10.0) - 0.1
        secs = [(9.4, uc, 0.85, top0), (12.0, uc, 0.85, top0 - 0.9), (15.0, uc, 0.85, 1.9),
                (15.9, uc - sx * 0.75, 0.5, 1.2)]
        loft(bm, [crect(c, v, hw, 0.0, z, 0.4) for v, c, hw, z in secs], RED2, smooth=False)

    # Claws (columns 4-6 / 15-17, rows 10-19): ridged arms sloping down to the ice.
    claw_v = [9.6, 12.0, 14.5, 16.5, 18.3, 19.4, 20.05]
    claw_z = [6.0, 5.45, 4.6, 3.8, 2.8, 1.95, 1.05]
    claw_w = [1.8, 1.8, 1.8, 1.75, 1.65, 1.45, 1.1]
    for sx in (-1, 1):
        uc = AX + sx * 5.25
        loft(bm, [ridge(uc, v, w, z) for v, w, z in zip(claw_v, claw_w, claw_z)], RED, smooth=False)

    # Mantlet (rows 10-13, columns 7-14) with the sight blade (columns 10-11, rows 13-14).
    secs = [(10.2, 3.6, 5.7), (12.6, 3.6, 5.7), (13.15, 3.5, 4.9), (13.4, 3.3, 4.1)]
    loft(bm, [crect(AX, v, hw, 0.0, z, 0.45) for v, hw, z in secs], RED, smooth=False)
    secs = [(12.4, 0.95, 6.35), (14.6, 0.95, 6.15), (15.15, 0.7, 5.6)]
    loft(bm, [crect(AX, v, hw, 4.6, z, 0.3) for v, hw, z in secs], RED, smooth=False)

    # Barrel cradle: dark trough, rails on posts, strap over the barrel.
    secs = [(12.6, 3.45, 1.6), (12.9, 3.75, 2.0), (22.1, 3.75, 2.0), (22.4, 3.45, 1.6)]
    loft(bm, [crect(AX, v, hw, 0.0, z, 0.4) for v, hw, z in secs], TROUGH, smooth=False)
    for sx in (-1, 1):
        uc = AX + sx * 2.5
        sweep(bm, [(uc, 12.9, ZB), (uc, 22.0, ZB)], 0.62, 0.62, n=10, mat=RAIL)
        for v in (13.7, 21.3):
            cyl_z(bm, uc, v, 1.8, ZB - 0.3, 0.45, n=8, mat=STEEL)
    sweep(bm, [(AX - 2.5, 17.05, ZB + 0.2), (AX - 2.05, 17.05, ZB + 1.95), (AX + 2.05, 17.05, ZB + 1.95),
               (AX + 2.5, 17.05, ZB + 0.2)], 0.66, 0.32, n=8, mat=STRAP)

    # Barrel (columns 9-12) from inside the mantlet to the knob, a band where it leaves the collar,
    # and the flange (rows 26-27).
    loft(bm, [yring(v, r) for v, r in ((11.0, 1.6), (24.7, 1.6), (24.85, 1.78), (25.35, 1.78), (25.5, 1.6),
                                       (26.0, 1.6))], [BARREL, BARREL, STEEL, STEEL, BARREL])
    loft(bm, [yring(v, r) for v, r in ((25.9, 2.05), (26.15, 2.85), (27.8, 2.85), (28.1, 2.15))], KNOB)

    # Collar (rows 22-24): a red arch round the barrel, a seam groove across it; the cheeks beside the
    # barrel (rows 24-26).
    cs = [(21.8, 3.95, 5.9), (22.15, 4.4, 6.45), (23.0, 4.4, 6.45), (23.1, 4.25, 6.3), (23.3, 4.25, 6.3),
          (23.4, 4.4, 6.45), (24.3, 4.4, 6.45), (24.65, 3.95, 5.9)]
    loft(bm, [arch(v, hw, h, 1.2, n=16, p=2.2) for v, hw, h in cs], RED2)
    for sx in (-1, 1):
        uc = AX + sx * 3.35
        secs = [(24.2, 1.3, 4.0), (25.9, 1.3, 3.8), (26.75, 1.05, 2.9), (27.05, 0.7, 2.1)]
        loft(bm, [crect(uc, v, hw, 0.0, z, 0.45) for v, hw, z in secs], RED3, smooth=False)

    # End knob (rows 28-32): a bell with a dark mouth, a machined band.
    kn = [(27.8, 1.7), (28.3, 2.2), (29.0, 2.9), (29.9, 3.6), (30.7, 3.95), (31.05, 3.95), (31.1, 4.05),
          (31.5, 4.05), (31.55, 3.95), (32.4, 3.95), (33.1, 3.65), (33.45, 3.2), (33.5, 2.55), (33.2, 2.1), (32.7, 1.95)]

    def knob_mat(c):
        v = 28 - c.y
        r = math.hypot(c.x - (AX - 12), c.z - ZB)
        if v > 33.2 and r < 3.3 or v > 32.75 and r < 2.6:
            return FLOOR
        return STEEL if 31.05 < v < 31.55 else KNOB
    loft(bm, [yring(v, r, n=20) for v, r in kn], knob_mat)

    # The recoil slide: rod, red-hot joint, lug, cup.
    loft(bm, [yring(v, 0.85, n=10) for v in (32.4, 34.0 + d)], STRAP)
    jt = [(31.9, 1.0), (32.15, 1.6), (32.4, 1.88), (34.6, 1.88), (34.85, 1.6), (35.1, 1.1)]
    loft(bm, [yring(v + d, r, n=14) for v, r in jt], HOT)
    loft(bm, [yring(v + d, r, n=14) for v, r in ((34.6, 1.0), (34.9, 1.35), (36.6, 1.35))], KNOB)

    vc = 42.0 + d
    RX, RY = 6.0, 7.0
    # One closed loft: wall with its hoop (z 2.35-3.2) raised in the same surface, rim, bore, floor.
    prof = [(0.0, 0.66), (0.35, 0.8), (1.3, 0.92), (2.35, 0.965), (2.45, 0.995), (3.1, 0.995), (3.2, 0.965),
            (4.3, 0.965), (5.1, 0.95), (5.45, 0.915), (5.35, 0.86), (4.6, 0.82), (3.2, 0.70), (2.1, 0.52),
            (1.55, 0.30)]
    HOOP = BARREL
    bands = [CUPW, CUPW, CUPW, HOOP, HOOP, HOOP, CUPW, CUPW, RIM, RIM, RIM, TROUGH, TROUGH, FLOOR, FLOOR]
    rings = [cup_ring(vc, z, s) for z, s in prof] + [[P(AX, vc, 1.5)]]
    loft(bm, rings, bands, cap0=True, cap1=False)
    # Bolt heads on the hoop, none under the lug.
    npl = len(CUP_PLAN)
    for k in range(2, npl - 1, 3):
        du, dv = CUP_PLAN[k]
        if dv < -4.5:  # none at the back, under the lug
            continue
        a, b = CUP_PLAN[k - 1], CUP_PLAN[(k + 1) % npl]
        nrm = Vector((b[1] - a[1], -(b[0] - a[0]), 0)).normalized()
        if nrm.x * du + nrm.y * dv < 0:
            nrm = -nrm
        u0, v0 = AX + 0.99 * du, vc + 0.99 * dv
        sweep(bm, [(u0, v0, 2.78), (u0 + 0.38 * nrm.x, v0 + 0.38 * nrm.y, 2.78)], 0.3, 0.3, n=6, mat=STEEL)
    # Firing striker standing in the bore (column 10, rows 14-17 of the frame).
    cyl_z(bm, AX - 0.4, vc + 0.6, 1.4, 2.0, 1.0, n=10, mat=KNOB, chamfer=0.25)
    sweep(bm, [(AX - 0.4, vc + 0.6, 1.8), (AX - 0.4, vc + 3.0, 3.7)], 0.5, 0.5, n=8, mat=PIN)
    sweep(bm, [(AX - 0.4, vc + 2.9, 3.62), (AX - 0.4, vc + 3.3, 3.95)], 0.72, 0.72, n=10, mat=PIN)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = common.mesh_object(f"turret-{d}", bm, mats, coll, smooth=None)
    es = obj.modifiers.new("hard", "EDGE_SPLIT")
    es.split_angle = math.radians(40)
    es.use_edge_sharp = False
    return obj


# --- newsh7-55 -------------------------------------------------------------------------------------

def build_core(sprite, coll):
    def pal(i, metallic=0.5, roughness=0.4, tag=CORE, **kw):
        return common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness, **kw)

    mats = [
        pal(166, 0.6, 0.4),   # 0 socket ring (bronze)
        pal(71, 0.6, 0.45, tag=f"{CORE}-lip", emission_strength=0.35),  # 1 inner lip lit by the core
        pal(9, 0.35, 0.3),   # 2 clamps
        common.palette_material(sprite, 117, f"{CORE}-core", metallic=1.0, roughness=0.9, emission_strength=1.0,
                                frames={93: 122, 131: 127}),  # 3 core
        pal(58, 0.1, 0.32),    # 4 ice mound
        common.palette_material(sprite, 126, f"{CORE}-hot", metallic=1.0, roughness=0.9, emission_strength=1.0,
                                frames={131: 127}),  # 5 hot spot
        common.palette_material(sprite, 75, f"{CORE}-pink", metallic=1.0, roughness=0.9, emission_strength=1.0),  # 6
        common.palette_material(sprite, 79, f"{CORE}-pinkhi", metallic=1.0, roughness=0.9, emission_strength=1.0),  # 7
    ]
    RING, LIP, CLAMP, GLOW, ICEM, HOT, PINK, PINKHI = range(8)
    UC, VC = 11.75, 11.0
    bm = bmesh.new()
    # Socket: outer foot, chamfered top, inner lip down to the core.
    prof = [(0.0, 1.0), (1.45, 1.0), (2.0, 0.955), (2.15, 0.89), (2.0, 0.815), (1.55, 0.76), (1.0, 0.73),
            (0.6, 0.69)]
    loft(bm, [sock_ring(z, s) for z, s in prof], [RING, RING, RING, RING, LIP, LIP, LIP],
         cap0=True, cap1=True)
    # Clamps where the sprite has grey spots (NW, NE, E, W, SW), straddling the ring.
    for u, v in ((7.6, 8.3), (15.0, 7.7), (16.7, 11.0), (6.6, 12.6), (8.8, 14.6)):
        cu, cv = SOCK_C
        i = min(range(len(SOCK_PLAN)), key=lambda j: (SOCK_PLAN[j][0] - u) ** 2 + (SOCK_PLAN[j][1] - v) ** 2)
        pu, pv = SOCK_PLAN[i]
        p1 = (cu + (pu - cu) * 0.995, cv + (pv - cv) * 0.995, 0.0)
        p0 = (cu + (pu - cu) * 0.8, cv + (pv - cv) * 0.8, 0.0)
        qa, qb = SOCK_PLAN[i - 1], SOCK_PLAN[(i + 1) % len(SOCK_PLAN)]
        tang = Vector((qb[0] - qa[0], qb[1] - qa[1], 0)).normalized()
        rings = []
        for (pu, pv, _), zt in ((p0, 2.45), (p1, 1.9)):
            rings.append([Pc(pu + tang.x * s * 0.6, pv + tang.y * s * 0.6, z)
                          for s, z in ((1, 0.0), (1, zt - 0.25), (0.6, zt), (-0.6, zt), (-1, zt - 0.25), (-1, 0.0))])
        loft(bm, rings, CLAMP, smooth=False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ring = common.mesh_object(f"{CORE}-socket", bm, mats, coll, smooth=None)
    es = ring.modifiers.new("hard", "EDGE_SPLIT")
    es.split_angle = math.radians(40)

    # Core dome.
    bm = bmesh.new()
    cu, cv = 11.6, 10.9
    dome = [(0.6, 3.75, 2.95), (1.1, 3.74, 2.93), (1.6, 3.7, 2.9), (2.0, 3.5, 2.75), (2.4, 3.2, 2.5),
            (2.7, 2.8, 2.2), (2.95, 2.3, 1.8), (3.12, 1.8, 1.4), (3.25, 1.2, 0.95), (3.32, 0.6, 0.48)]
    loft(bm, [vring(cu, cv, z, rx, ry, 48, Pc) for z, rx, ry in dome] + [[Pc(cu, cv, 3.35)]], GLOW,
         cap0=True, cap1=False)
    core = common.mesh_object(f"{CORE}-core", bm, mats, coll, smooth=True)

    def blob(name, u, v, rx, ry, mat, frames, z=3.0, h=0.42):
        b = bmesh.new()
        rs = [vring(u, v, z - 0.25, rx, ry, 16, Pc), vring(u, v, z + h * 0.6, rx * 0.8, ry * 0.8, 16, Pc),
              vring(u, v, z + h, rx * 0.4, ry * 0.4, 16, Pc)]
        loft(b, rs + [[Pc(u, v, z + h + 0.05)]], mat, cap0=True, cap1=False)
        o = common.mesh_object(name, b, mats, coll, smooth=True)
        return common.frame_part(o, frames)

    def surf(u, v):  # the dome's height there
        e = math.hypot((u - cu) / 3.7, (v - cv) / 2.9)
        return 0.6 + 2.75 * max(0.0, 1 - e * e) ** 0.5
    hot = blob(f"{CORE}-hot", 10.6, 10.5, 1.6, 1.4, HOT, [55, 131], z=surf(10.6, 10.5) - 0.1)
    pink = blob(f"{CORE}-pink", 10.2, 10.1, 2.1, 1.9, PINK, [93], z=surf(10.2, 10.1) - 0.12, h=0.3)
    pinkhi = blob(f"{CORE}-pinkhi", 9.9, 9.9, 1.0, 0.9, PINKHI, [93], z=surf(9.9, 9.9) + 0.1, h=0.22)

    # The ice mound (ground, D130/D66: tyrian_ground, no shadow, outside the outline shell).
    bm = bmesh.new()
    md = [(0.0, 8.0, 6.8), (0.25, 7.2, 6.1), (0.6, 6.3, 5.3), (0.85, 5.6, 4.7)]
    loft(bm, [vring(11.6, 11.2, z, rx, ry, 28, Pc) for z, rx, ry in md], ICEM, cap0=True, cap1=True)
    mound = common.mesh_object(f"{CORE}-mound", bm, mats, coll, smooth=True)
    mound["tyrian_ground"] = True
    return ring, core, [hot, pink, pinkhi], mound


# --- outline shells, split, export ------------------------------------------------------------------

def shell_of(objs, coll, name):
    """D90/D118: the outline shell from a sealed copy of the joined parts, held inside."""
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        for m in list(c.modifiers):
            c.modifiers.remove(m)
        coll.objects.link(c)
        copies.append(c)
    bpy.context.view_layer.update()
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    if len(copies) > 1:
        bpy.ops.object.join()
    sealed = copies[0]
    shell = common.outline_shell(sealed, coll, voxel=0.010, faces=6000, smooth=4, inside=0.003)
    shell.name = f"{name}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    return shell


def split_open(obj, layout, coll, suffix=""):
    """Cut a shell per piece without capping the cuts (no ink along the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}{suffix}_outline")
        bm.to_mesh(me)
        bm.free()
        for mm in obj.data.materials:
            me.materials.append(mm)
        s = bpy.data.objects.new(f"{name}{suffix}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


def apply_mods(obj):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main(only=None):
    """only: "turret" (newsh7-169, newsh7-203, -f2, -f3; the default when this script is run), "core"
    (newsh7-55; what newsh7-55.py runs) or "all". Each entry script builds only its own models, so a
    full tools/build-models.sh run never has two Blender processes writing the same glb."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    review = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    only = only or (argv[argv.index("--only") + 1] if "--only" in argv else "turret")
    assert only in ("turret", "core", "all"), only
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    gun = common.load_sprite(WT, GUN)
    top = common.load_sprite(WT, TOP)
    sprite = json.loads(json.dumps(gun))
    sprite["colors"].update(top["colors"])
    core_sprite = common.load_sprite(WT, CORE)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in gun["assemblyLayout"] if e["cx"] == CX0]

    objs, per_file, shells, wholes, info = [], {}, [], [], {}
    core_objs = []
    for k, d in enumerate(SLIDES if only in ("turret", "all") else ()):
        whole = build_turret(sprite, coll, d)
        apply_mods(whole)
        shell = shell_of([whole], coll, f"turret-{d}")
        pieces = common.split_assembly(whole, layout)
        sh = split_open(shell, layout, coll)
        bpy.data.objects.remove(shell, do_unlink=True)
        model = GUN if k == 0 else f"{GUN}-f{k + 1}"
        names = {GUN: model, TOP: TOP}
        for n, cx, cy in layout:
            if n == TOP and k > 0:  # the top piece is the same on every slide
                bpy.data.objects.remove(pieces[n], do_unlink=True)
                bpy.data.objects.remove(sh[n], do_unlink=True)
                continue
            pc, s = pieces[n], sh[n]
            pc.name, s.name = names[n], f"{names[n]}_outline"
            shells.append(s)
            for o in (pc, s):
                o.location = (cx / 12 + SPACING * k, -cy / 12, 0)
                objs.append(o)
            per_file[names[n]] = [pc, s]
            info[names[n]] = {"tris": tris(pc), "shell_faces": len(s.data.polygons)}
        whole.location = (SPACING * k, 0, 0)
        whole["slide"] = d
        wholes.append(whole)
        info[f"whole-{d}"] = tris(whole)

    if only in ("core", "all"):
        ring, core, parts, mound = build_core(core_sprite, coll)
        apply_mods(ring)
        cshell = shell_of([ring, core], coll, CORE)
        shells.append(cshell)
        core_objs = [ring, core] + parts + [mound, cshell]
        # one node per model: join ring + core into the model node, keep frame parts separate
        bpy.context.view_layer.update()
        for o in bpy.context.view_layer.objects:
            if o is not None:
                o.select_set(False)
        ring.select_set(True)
        core.select_set(True)
        bpy.context.view_layer.objects.active = ring
        bpy.ops.object.join()
        ring.name = CORE
        core_objs = [ring] + parts + [mound, cshell]
        per_file[CORE] = core_objs
        info[CORE] = {"tris": sum(tris(o) for o in [ring] + parts + [mound]), "shell_faces": len(cshell.data.polygons)}
        for o in core_objs:
            o.location = (-SPACING, 0, 0)
            objs.append(o)

    bad = [s.name for s in shells if len(s.data.polygons) == 0]
    if bad:
        raise SystemExit(f"empty outline shells: {bad}")
    bpy.context.view_layer.update()
    if review:
        pdir = review / "pieces"
        pdir.mkdir(parents=True, exist_ok=True)
        common.export_glb(objs, review / f"{NAME}.glb")
        common.export_glb(wholes + core_objs, review / "wholes.glb")
    gframes = gun["sprites"][0]["frames"]
    for fname, group in per_file.items():
        saved = [tuple(o.location) for o in group]
        for o in group:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        if review:
            common.export_glb(group, pdir / f"{fname}.glb")
        if fname == TOP:
            sprites = top["sprites"]
        elif fname == CORE:
            sprites = core_sprite["sprites"]
        else:
            k = 0 if fname == GUN else int(fname.rsplit("-f", 1)[1]) - 1
            sprites = [dict(gun["sprites"][0], frames=[gframes[k]])]
        common.export_sprite_model(WT, group, f"enemies/{fname}", sprites)
        for o, loc in zip(group, saved):
            o.location = loc
    bpy.context.view_layer.update()
    if review:
        (review / "build_info.json").write_text(json.dumps(info, indent=1))
    print("BUILD_INFO", json.dumps(info))


if __name__ == "__main__":
    main()
