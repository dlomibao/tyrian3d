"""Green beetle with a blue gem (newshv.shp frame 165): a 3D version of its sprite.

What it is: an organic attack craft of the episode-2 hives (level 17), flying down the screen nose
first. The nose (sprite bottom) is a broad oval head shell carrying a big faceted blue gem in a dark
bezel, with a pair of blue-sheathed mandibles curling round its front edge and a dark intake slot
under the gem. Behind it (sprite top) a heart-shaped thorax pod carries a raised diamond boss with a
brown, cross-shaped bud (a long stalk running aft, a four-pointed bulb, a pale knob in a dark crease);
two little exhaust bulbs sit at its rear edge. A pair of curled horns, round tubes in section, sweep
from tips raised high over the stern out round each side and down to the head, segmented by a dark joint
ring near the tips. Belly: a plain closed rounded underside.

Built in sprite pixels (x right, y down the sprite, z up; 12 px = 1 unit), converted at the end.
Colours are the sprite's own palette index per region (body 37, bud 19, knob 22, gem 147, mandible
sheaths and studs 146, recesses 35); shading and highlights come from the game's light.

Run: blender --background --python assets/blender/enemies/newshv-165.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshv-165"
MODEL = f"enemies/{NAME}"

CX = 12.0  # the sprite's mirror line (pixel edge between columns 11 and 12)

# material slots
BODY, RECESS, BUD, BUD_DK, KNOB, GEM, SHEATH, BODY_LT = range(8)


def sgnpow(v, e):
    return math.copysign(abs(v) ** e, v)


def frange(a, b, step):
    n = max(1, round((b - a) / step))
    return [a + (b - a) * i / n for i in range(n + 1)]


def merge_ys(*lists):
    out = sorted(set(round(v, 4) for lst in lists for v in lst))
    return out


# --- sections and lofts ------------------------------------------------------------------------

def section(cx, zc, hw, ht, hb, sides, nt=2.4, nb=2.0):
    """A closed cross-section (x, z): superellipse top (exponent nt) and bottom (nb)."""
    pts = []
    for k in range(sides):
        a = 2 * math.pi * (k + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        n = nt if s >= 0 else nb
        x = cx + hw * sgnpow(c, 2 / n)
        z = zc + (ht * sgnpow(s, 2 / nt) if s >= 0 else abs(hb) * sgnpow(s, 2 / nb))
        pts.append((x, z))
    return pts


def loft(bm, ys, secf, mat):
    """A closed body through sections secf(y) -> [(x, z)] at each y; the ends close with a fan to
    the end section's centre. Returns the new faces."""
    faces = []
    rings = []
    for y in ys:
        pts = secf(y)
        rings.append([bm.verts.new((x, y, z)) for x, z in pts])
    for r0, r1 in zip(rings, rings[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for ring in (rings[0], rings[-1]):
        c = sum((v.co for v in ring), Vector()) / len(ring)
        cv = bm.verts.new(c)
        n = len(ring)
        for i in range(n):
            faces.append(bm.faces.new((ring[i], ring[(i + 1) % n], cv)))
    for f in faces:
        f.material_index = mat
    return faces


def tube(bm, points, half_w, half_h, sides=10, mats=None, mat=0):
    """A tube along 3D points with a horizontal and vertical half-size per point (0 = a tip);
    mats[i] colours the segment from point i to i + 1."""
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts):
        if half_w[i] == 0:
            rings.append([bm.verts.new(p)])
            continue
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * math.cos(a) * half_w[i] + up * math.sin(a) * half_h[i]))
        rings.append(ring)
    faces = []
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        m = mats[i] if mats else mat
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[k], r1[j]))
            elif len(r1) == 1:
                f = bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = m
            faces.append(f)
    for ring, m in ((rings[0], (mats or [mat])[0]), (rings[-1], (mats or [mat])[-1])):
        if len(ring) > 1:
            f = bm.faces.new(ring)
            f.material_index = m
            faces.append(f)
    return faces


def hull(bm, points, mat):
    verts = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context="VERTS")
    faces = list({f for v in verts if v.is_valid for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=[v for v in verts if v.is_valid],
                             edges=list({e for f in faces for e in f.edges}))
    faces = list({f for v in verts if v.is_valid for f in v.link_faces})
    for f in faces:
        f.material_index = mat
    return faces


def mirror(bm, faces):
    """Mirror faces about x = CX."""
    vmap = {}
    out = []
    for f in faces:
        if not f.is_valid:
            continue
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm.verts.new((2 * CX - v.co.x, v.co.y, v.co.z))
            vs.append(vmap[v])
        nf = bm.faces.new(list(reversed(vs)))
        nf.material_index = f.material_index
        out.append(nf)
    return out


# --- the parts' plan and height profiles (sprite px) ---------------------------------------------

# Pod (thorax): heart-shaped plan, widest over rows 9-10, narrowing in a V to the waist at row 13.
POD_HW = T.pchip([2.95, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.4],
                 [3.1, 4.0, 4.05, 4.9, 5.3, 5.5, 5.7, 5.95, 6.0, 5.0, 4.0, 3.0, 2.6])
POD_ZT = T.pchip([2.95, 3.5, 5.0, 7.0, 9.0, 11.0, 12.5, 14.4], [2.2, 3.9, 5.2, 6.0, 6.2, 5.8, 4.9, 3.9])
POD_ZB = T.pchip([2.95, 4.0, 8.0, 12.0, 14.4], [1.0, 1.9, 2.2, 2.0, 1.7])
POD_Y0, POD_Y1 = 2.95, 14.4
POD_NT = 2.3

# Head shell: an ellipse in plan, centred on row 20.
SH_YC, SH_B0, SH_B1, SH_A = 20.0, 6.75, 6.3, 8.05
SH_Y0, SH_Y1 = SH_YC - SH_B0, SH_YC + SH_B1
SH_NT = 2.2


def shell_hw(y):
    b = SH_B0 if y < SH_YC else SH_B1
    t = min(1.0, abs(y - SH_YC) / b)
    return SH_A * math.sqrt(max(0.0, 1 - t * t))


SH_ZT = T.pchip([SH_Y0, 14.5, 16.0, 18.5, 21.0, 23.5, 25.0, SH_Y1], [2.6, 4.2, 5.1, 5.5, 5.3, 4.4, 3.2, 1.5])
SH_ZB = T.pchip([SH_Y0, 15.0, 20.0, 24.5, SH_Y1], [1.0, 1.9, 2.2, 1.8, 0.9])


def surf_z(x, y, hwf, ztf, nt):
    hw = hwf(y)
    if hw <= 1e-6:
        return 0.0
    t = min(1.0, abs(x - CX) / hw)
    return ztf(y) * (1 - t ** nt) ** (1 / nt)


def pod_z(x, y):
    return surf_z(x, y, POD_HW, POD_ZT, POD_NT)


def shell_z(x, y):
    return surf_z(x, y, shell_hw, lambda yy: SH_ZT(yy) * (max(shell_hw(yy), 0.05) / SH_A) ** 0.3, SH_NT)


# Left horn (columns 1-6): per-row edges, a round tube whose plan follows the sprite's crescent.
HORN_Y = [0.85, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.0]
HORN_XL = T.pchip(HORN_Y, [5.85, 5.0, 4.0, 3.0, 2.05, 1.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.05, 1.95, 2.95, 3.5])
HORN_XR = T.pchip(HORN_Y, [6.35, 6.95, 7.0, 7.0, 6.9, 6.05, 6.8, 7.0, 7.0, 6.9, 5.4, 5.0, 5.0, 5.0, 5.0, 4.5])
HORN_HH = T.pchip([0.85, 2.0, 3.5, 5.5, 8.0, 10.5, 12.5, 14.0, 15.0], [0.35, 1.05, 1.5, 1.8, 2.05, 1.9, 1.7, 1.25, 0.5])
HORN_ZC = T.pchip([0.85, 2.0, 3.5, 6.0, 9.0, 12.0, 15.0], [5.6, 5.0, 4.2, 3.2, 2.5, 1.9, 1.3])
# The joint groove near the horn tip: a ring across the tube's axis, centred (4.45, 4.75).
GROOVE_C = Vector((4.45, 4.75))
GROOVE_D = Vector((-0.48, 0.88)).normalized()


def horn_axis(y):
    return 0.5 * (HORN_XL(y) + HORN_XR(y)), HORN_ZC(y)


def build(bm):
    parts = {}
    # Pod.
    ys = merge_ys(frange(POD_Y0, 3.9, 0.3), frange(3.6, 13.0, 0.65), frange(13.0, POD_Y1, 0.45))
    parts["pod"] = loft(bm, ys, lambda y: section(CX, 0.0, POD_HW(y), POD_ZT(y), -POD_ZB(y), 24, nt=POD_NT,
                                                   nb=2.0), BODY)
    # Head shell.
    ys = merge_ys(frange(SH_Y0, SH_Y0 + 1.0, 0.25), frange(SH_Y0 + 1.0, SH_Y1 - 1.2, 0.65),
                  frange(SH_Y1 - 1.2, SH_Y1, 0.2))
    def shell_sec(y):
        hw = shell_hw(y)
        k = (max(hw, 0.05) / SH_A) ** 0.3
        return section(CX, 0.0, max(hw, 0.05), SH_ZT(y) * k, -SH_ZB(y) * k, 24, nt=SH_NT, nb=2.0)

    parts["shell"] = loft(bm, ys, shell_sec, BODY)

    # Left horn, with its joint ring, then mirrored.
    ys = merge_ys(frange(0.85, 3.0, 0.36), frange(3.0, 6.6, 0.24), frange(6.6, 13.6, 0.7), frange(13.6, 15.0, 0.35))

    def horn_sec(y):
        cx, zc = horn_axis(y)
        hw = 0.5 * (HORN_XR(y) - HORN_XL(y))
        return section(cx, zc, hw, HORN_HH(y), -HORN_HH(y), 12, nt=2.15, nb=2.0)

    horn = loft(bm, ys, horn_sec, BODY)
    # The joint near the tip: a dark band ring round the tube, square to its axis, half sunk.
    gy = GROOVE_C.y
    x0, z0 = horn_axis(gy - 0.2)
    x1, z1 = horn_axis(gy + 0.2)
    t = Vector((x1 - x0, 0.4, z1 - z0)).normalized()
    side = t.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(t).normalized()
    ax, az = horn_axis(gy)
    centre = Vector((ax, gy, az))
    cos_th = abs(Vector((t.x, t.y)).normalized().y)
    ra = 0.5 * (HORN_XR(gy) - HORN_XL(gy)) * cos_th - 0.02
    rb = HORN_HH(gy) - 0.02
    M, S, rm = 22, 6, 0.26
    rings = []
    for i in range(M):
        a_ = 2 * math.pi * i / M
        p = centre + side * math.cos(a_) * ra + up * math.sin(a_) * rb
        radial = (side * math.cos(a_) * rb + up * math.sin(a_) * ra).normalized()
        rings.append([bm.verts.new(p + radial * math.cos(2 * math.pi * k / S) * rm + t * math.sin(2 * math.pi * k / S) * rm)
                      for k in range(S)])
    for i in range(M):
        r0, r1 = rings[i], rings[(i + 1) % M]
        for k in range(S):
            j = (k + 1) % S
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = RECESS
            horn.append(f)
    parts["horn"] = horn + mirror(bm, horn)

    # Raised diamond boss on the pod, carrying the bud.
    BY0, BYM, BY1, BHW = 3.3, 8.7, 13.0, 4.1

    def boss_hw(y):
        if y <= BYM:
            t = (BYM - y) / (BYM - BY0)
        else:
            t = (y - BYM) / (BY1 - BYM)
        t = min(1.0, t)
        return BHW * max(0.0, 1 - t ** 1.35) ** (1 / 1.35)

    def boss_sec(y):
        hw = max(boss_hw(y), 0.12)
        top = []
        K = 8
        inner = max(hw - 0.45, hw * 0.3)
        for i in range(K + 1):
            x = CX - inner + 2 * inner * i / K
            top.append((x, pod_z(x, y) + 0.55))
        edge_r = (CX + hw, pod_z(CX + hw, y) + 0.08)
        edge_l = (CX - hw, pod_z(CX - hw, y) + 0.08)
        bot_r = (CX + hw * 0.7, pod_z(CX + hw * 0.7, y) - 0.7)
        bot_l = (CX - hw * 0.7, pod_z(CX - hw * 0.7, y) - 0.7)
        # counter-clockwise seen from +y: right-bottom, right edge, top right to left, left edge, left bottom
        return [bot_r, edge_r] + list(reversed(top)) + [edge_l, bot_l]

    parts["boss"] = loft(bm, merge_ys(frange(BY0, BY1, 0.45)), boss_sec, BODY)

    def boss_top(x, y):
        return pod_z(x, y) + 0.55

    # Bud: the stalk running aft, the four-pointed bulb, a dark crease and the pale knob.
    def stalk_sec(y):
        hw = 0.55 + 0.4 * (y - 3.4) / 4.0
        z0 = boss_top(CX, y)
        return section(CX, z0, hw, 0.85 + 0.25 * (y - 3.4) / 4.0, -0.5, 10, nt=2.2)

    bud = loft(bm, merge_ys(frange(3.4, 7.8, 0.45)), stalk_sec, BUD)
    BUD_YC, BUD_L0, BUD_L1, BUD_HW, BUD_H = 9.35, 2.6, 2.55, 3.0, 1.55

    def bulb_sec(y):
        b = BUD_L0 if y < BUD_YC else BUD_L1
        t = min(1.0, abs(y - BUD_YC) / b)
        hw = max(0.06, BUD_HW * max(0.0, 1 - t ** 1.3) ** (1 / 1.3))
        h = BUD_H * math.sqrt(max(0.0, 1 - t ** 2.2)) + 0.05
        return section(CX, boss_top(CX, BUD_YC), hw, h, -0.7, 16, nt=2.0)

    bud += loft(bm, merge_ys(frange(BUD_YC - BUD_L0, BUD_YC + BUD_L1, 0.4)), bulb_sec, BUD)
    top_z = boss_top(CX, BUD_YC) + BUD_H
    # dark crease round the knob, then the knob
    crease = loft(bm, merge_ys(frange(BUD_YC - 1.55, BUD_YC + 1.55, 0.31)),
                  lambda y: section(CX, top_z - 0.35, 1.55 * math.sqrt(max(0.0, 1 - ((y - BUD_YC) / 1.55) ** 2)) + 0.03,
                                    0.22, -0.3, 12), BUD_DK)
    knob = loft(bm, merge_ys(frange(BUD_YC - 1.05, BUD_YC + 1.05, 0.26)),
                lambda y: section(CX, top_z - 0.25, 1.05 * math.sqrt(max(0.0, 1 - ((y - BUD_YC) / 1.05) ** 2)) + 0.02,
                                  0.55, -0.3, 12), KNOB)
    parts["bud"] = bud + crease + knob

    # Two exhaust bulbs at the pod's stern (sprite row 2): short tubes with a dark recessed nozzle.
    noz = []
    for nx in (10.0,):
        zc = 2.3
        pts = [(nx, 5.0, zc), (nx, 3.4, zc), (nx, 2.35, zc), (nx, 2.03, zc), (nx, 2.15, zc), (nx, 2.8, zc)]
        hw = [0.98, 1.0, 0.94, 0.74, 0.55, 0.0]
        hh = [1.05, 1.08, 1.0, 0.78, 0.58, 0.0]
        noz += tube(bm, pts, hw, hh, sides=12, mats=[BODY, BODY, BODY, RECESS, RECESS])
    parts["nozzle"] = noz + mirror(bm, noz)

    # Gem: a faceted cabochon in a dark bezel (rows 14-21, columns 8-15).
    girdle = [(11.0, 14.05), (13.0, 14.05), (14.9, 15.0), (15.2, 16.2), (15.95, 17.0), (15.95, 19.0), (15.0, 19.9),
              (14.0, 20.95), (13.0, 21.95), (11.0, 21.95), (10.0, 20.95), (9.0, 19.9), (8.05, 19.0), (8.05, 17.0),
              (8.8, 16.2), (9.1, 15.0)]
    gx = sum(p[0] for p in girdle) / len(girdle)
    gy = sum(p[1] for p in girdle) / len(girdle)
    gz = shell_z(gx, gy)

    def scaled(s, dz):
        return [(gx + (x - gx) * s, gy + (y - gy) * s, dz) for x, y in girdle]

    gem_pts = (scaled(1.0, gz + 0.2) + scaled(0.9, gz + 1.15) + scaled(0.7, gz + 1.95) + scaled(0.42, gz + 2.35)
               + scaled(0.75, gz - 1.6))
    parts["gem"] = hull(bm, gem_pts, GEM)
    # bezel: a flat ring, sitting on the shell round the gem
    bez = []
    n = len(girdle)
    outer, inner = [], []
    for (x, y) in girdle:
        dx, dy = x - gx, y - gy
        ln = math.hypot(dx, dy)
        ox, oy = x + dx / ln * 0.75, y + dy / ln * 0.75
        ix, iy = x - dx / ln * 0.25, y - dy / ln * 0.25
        zt = max(shell_z(ox, oy), shell_z(x, y)) + 0.35
        outer.append((bm.verts.new((ox, oy, zt - 0.1)), bm.verts.new((x + dx / ln * 0.95, y + dy / ln * 0.95,
                                                                          shell_z(x + dx / ln * 0.95, y + dy / ln * 0.95) - 0.5))))
        inner.append((bm.verts.new((ix, iy, zt)), bm.verts.new((ix, iy, gz - 0.8))))
    for i in range(n):
        j = (i + 1) % n
        (ot0, ob0), (ot1, ob1) = outer[i], outer[j]
        (it0, ib0), (it1, ib1) = inner[i], inner[j]
        for q in ((it0, it1, ot1, ot0), (ot0, ot1, ob1, ob0), (ob0, ob1, ib1, ib0), (ib0, ib1, it1, it0)):
            f = bm.faces.new(q)
            f.material_index = RECESS
            bez.append(f)
    parts["bezel"] = bez

    # Mandibles: blue-sheathed pincers curling round the head's front edge, green tips (row 26).
    path = [(6.45, 20.9), (6.6, 22.3), (7.3, 23.6), (8.4, 24.75), (9.55, 25.7), (10.2, 26.35), (10.45, 26.85)]
    hws = [0.75, 1.05, 1.15, 1.1, 0.95, 0.7, 0.0]
    hhs = [0.5, 0.6, 0.62, 0.6, 0.55, 0.45, 0.0]
    pts3 = []
    for (x, y), h in zip(path, hhs):
        z = max(shell_z(x, y), 0.25) + 0.1 + (0.25 if y > 25.5 else 0.0)
        pts3.append((x, y, z))
    mand = tube(bm, pts3, hws, hhs, sides=10, mats=[SHEATH, SHEATH, SHEATH, SHEATH, BODY, BODY])
    # the knuckle at the mandible's root, with a blue stud, and the shoulder stud (row 16)
    kx, ky = 6.55, 21.05
    kz = shell_z(kx, ky)
    mand += loft(bm, merge_ys(frange(ky - 1.25, ky + 1.25, 0.31)),
                 lambda y: section(kx, kz - 0.2, 1.25 * math.sqrt(max(0.0, 1 - ((y - ky) / 1.25) ** 2)) + 0.03, 0.85,
                                   -0.6, 12, nt=2.0), BODY_LT)
    mand += loft(bm, merge_ys(frange(ky - 0.6, ky + 0.6, 0.2)),
                 lambda y: section(kx, kz + 0.45, 0.6 * math.sqrt(max(0.0, 1 - ((y - ky) / 0.6) ** 2)) + 0.02, 0.35,
                                   -0.3, 10, nt=2.0), SHEATH)
    sx, sy = 6.55, 16.5
    sz = shell_z(sx, sy)
    mand += loft(bm, merge_ys(frange(sy - 0.62, sy + 0.62, 0.2)),
                 lambda y: section(sx, sz - 0.05, 0.62 * math.sqrt(max(0.0, 1 - ((y - sy) / 0.62) ** 2)) + 0.02, 0.4,
                                   -0.4, 10, nt=2.0), SHEATH)
    parts["mandible"] = mand + mirror(bm, mand)

    # Intake slot under the gem (row 22): a dark louvred plate set into the shell.
    slot = []
    zs = shell_z(CX, 22.55)
    slot += hull(bm, T.cbox(10.25, 13.75, 22.1, 23.0, zs - 1.2, zs + 0.12, 0.18), RECESS)
    # a keel ridge from the slot down the head's front to the tip
    kpts = [(CX, y, shell_z(CX, y) - 0.15) for y in (22.95, 23.8, 24.7, 25.5, 26.05)]
    slot += tube(bm, kpts, [0.45, 0.48, 0.45, 0.38, 0.0], [0.42, 0.45, 0.42, 0.35, 0.0], sides=8, mat=BODY)
    parts["slot"] = slot
    return parts


def to_blender(bm):
    m = Matrix(((1 / 12, 0, 0, -CX / 12), (0, -1 / 12, 0, 14 / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(37, metallic=0.15, roughness=0.42),  # BODY: green chitin, satin
        pal(35, metallic=0.05, roughness=0.75),  # RECESS: dark green grooves, bezel, nozzles
        pal(19, metallic=0.1, roughness=0.5),  # BUD: brown
        pal(17, metallic=0.0, roughness=0.8),  # BUD_DK: the crease round the knob
        pal(22, metallic=0.15, roughness=0.4),  # KNOB: pale brown
        pal(147, metallic=0.2, roughness=0.1, emission_strength=0.35),  # GEM: deep glossy blue
        pal(146, metallic=0.35, roughness=0.3),  # SHEATH: blue mandible plates and studs
        pal(38, metallic=0.15, roughness=0.42),  # BODY_LT: the mandible knuckles
    ]
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    to_blender(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=3000)
    if '--no-cull' not in sys.argv:
        T.cull_hidden(obj, grid=3, ndirs=32)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    print("tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))


if __name__ == "__main__":
    main()
