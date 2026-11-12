"""Clamshell pod pair (newsha.shp, merged with assembly-newsha-229): silhouette and readability from the small tilted game
camera first, then hard-surface detail. Episode 2 (2.5 SOH JIN, 2.9 MISTAKES) and 4.19.

WHAT IT IS: one half of a split armoured sphere flying free in space, its flat cut face turned to
the screen centre, a glowing plasma core in that face and a plasma slab that slides out of it.
Two of them always spawn as a mirror pair: assembly-newsha-1 rides the right edge (cut face west),
assembly-newsha-229 the left edge (its exact pixel mirror; built here as the X-mirror of the same
geometry). Each is 48 x 56 px of four 24 x 28 pieces:

    right pod   newsha-1 (TL, 4 frames: 1 3 5 7)   newsha-9  (TR, static)
                newsha-39 (BL, 4 frames: 39..45)    newsha-47 (BR, static)
    left pod    newsha-229 (TL, static)             newsha-231 (TR, 4 frames: 231..237)
                newsha-267 (BL, static)             newsha-269 (BR, 4 frames: 269..275)

Animated pieces get one model per frame: <piece>, <piece>-f2, -f3, -f4 (the plasma slab out to
sprite column 13, 16, 19, then retracted so only the red core line shows).

Silhouette first: from the tilted game camera the pod must read as ONE round armoured half-shell
with a hard, ringed cut face and a block of fire standing out of it. So: a clean superellipsoid
lune (loft along X, sections pchip-interpolated from the sprite's traced outline) whose crest is
the cut face's top edge (the sprite's lit band), a bold flange hoop plus a second armour hoop
(rib A) and a short armour strap (rib B) along the crest, three chunky clamps over the face's top
arc (the sprite's grey brackets), a dark sensor bay with two lenses on the north slope, modelled
seams on the dome, and the plasma slab as a chamfered lens-section block with a bright top streak.

Coordinates: sprite px of the right pod's 48 x 56 block, X = c - 24 (east), Y = 28 - r (north),
Z up from the equator; 1 px = 1/12 Blender unit. The cut face is the plane X = 1 (column 25).

Underside: the lower half of the same lune, plain and closed. Palette materials pal_<index>
(glow parts emissive, D126). Outline shell from a sealed pre-cull copy of each whole frame, cut
open per piece (D51, D90, D118).

Exports every piece of both pods (8 pieces, frames -f2..-f4 on the animated ones) with its outline
shell through common.export_sprite_model. This script replaces assembly-newsha-229.py (the pair
is one build, so the mirror is exact).

Run: blender --background --python assets/blender/enemies/assembly-newsha-1.py -- [--review DIR] [--no-export]
"""

import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
PX = 1 / 12
RIGHT = {"pieces": ["newsha-1", "newsha-9", "newsha-39", "newsha-47"], "animated": ["newsha-1", "newsha-39"],
         "origin": (221, 25)}
LEFT = {"pieces": ["newsha-229", "newsha-231", "newsha-267", "newsha-269"], "animated": ["newsha-231", "newsha-269"],
        "origin": (58, 75)}
# West end of the plasma slab per frame (sprite column edge); None = retracted (frame 4).
FIRE_LEFT = [13, 16, 19, None]
# The slab's section (half width Y, height above / depth below the face centre, px) per frame; it
# thins as it withdraws, and the slit in the dark cut face shrinks round it to a thin red line (f4).
SLAB_YE = 18.75
SLAB_EXP = 5.0  # boxy section: the red rim reads as a ~1 px edge from the top
SLAB_Z = [(4.6, 3.6), (3.9, 3.0), (3.2, 2.5), None]
SLIT_YE = 15.5  # the slit's half width in the face (the slab flares to SLAB_YE outside it)
SLIT_LIP = 0.5  # glowing gap round the slab in the slit
SLIT_LINE = (0.7, 0.7)  # frame 4: the closed slit, a thin red core line
SLIT_GLOW = [121, 120, 119, 119]  # the slit's glow index per frame (the sprite's core at c23-24)
FIRE_SHIFT = [0, 1, 1, 0]  # f2/f3 fire one palette step cooler (sprite 121/120 at the slab top)

# ---- the shell's plan: the sprite's outline (traced at pixel edges, symmetric about row 28) -----
# (X east edge, Y) along the north half; the south half is its mirror. The flat west side is the cut
# face at X = 1 (column 25), rounding to the pole tips at rows 6 / 50.
OUTLINE_N = [(1.0, 0.0), (1.0, 17.6), (1.15, 18.9), (1.6, 19.9), (2.4, 20.8), (3.5, 21.45), (5.0, 21.85),
             (6.8, 21.95), (8.4, 21.7), (9.6, 21.25), (11.0, 20.5), (12.75, 19.5), (14.0, 18.5), (15.0, 17.5),
             (16.0, 16.5), (17.0, 15.5), (18.0, 14.5), (18.8, 13.5), (19.4, 12.5), (19.95, 11.5),
             (20.45, 10.5), (20.95, 9.5), (21.4, 8.5), (21.8, 7.5), (22.15, 6.5), (22.45, 5.5),
             (22.7, 4.5), (22.88, 3.5), (22.97, 2.0), (23.0, 0.0)]
X0, XE = 1.0, 23.0  # the cut face, the dome's east tip
HT, HB = 16.0, 12.0  # crest height above / keel depth below the equator (px)
EXP = 2.25  # section superellipse exponent (round, a touch fuller than an ellipse)
NSEC = 56  # points per section loop


def outline_y(x):
    """Half width (north = south) of the plan at X = x."""
    pts = OUTLINE_N
    if x <= X0:
        return pts[1][1]
    best = 0.0
    # The outline is a polyline from the cut face round the pole to the east tip: take the largest
    # Y where it crosses X = x (the pole region rises then falls in X).
    for (xa, ya), (xb, yb) in zip(pts[1:], pts[2:]):
        if (xa - x) * (xb - x) <= 0 and xa != xb:
            t = (x - xa) / (xb - xa)
            best = max(best, ya + t * (yb - ya))
    return best


def prof(x, h):
    """Crest height (h = HT) or keel depth (h = HB) of the section at X = x: a quarter superellipse."""
    u = min(1.0, max(0.0, (x - X0) / (XE - X0)))
    return h * (1 - u ** 2.4) ** (1 / 2.4)


def spow(v, p):
    return math.copysign(abs(v) ** p, v)


def section(x, grow=0.0, ye=None, zt=None, zb=None, exp=EXP, n=NSEC, zc=0.0):
    """The shell's YZ section loop at X = x (counter-clockwise seen from +X, starting north at the
    equator), pushed out along its normal by `grow`."""
    ye = outline_y(x) if ye is None else ye
    zt = prof(x, HT) if zt is None else zt
    zb = prof(x, HB) if zb is None else zb
    base = []
    for i in range(n):
        a = 2 * math.pi * i / n
        y = ye * spow(math.cos(a), 2 / exp)
        z = zc + (zt if math.sin(a) >= 0 else zb) * spow(math.sin(a), 2 / exp)
        base.append((y, z))
    if not grow:
        return base
    out = []
    for i, (y, z) in enumerate(base):
        y0, z0 = base[i - 1]
        y1, z1 = base[(i + 1) % n]
        ty, tz = y1 - y0, z1 - z0
        ln = math.hypot(ty, tz) or 1.0
        ny, nz = tz / ln, -ty / ln  # outward for a counter-clockwise loop
        out.append((y + grow * ny, z + grow * nz))
    return out


def shell_height(x, y):
    """Z of the dome's top surface at plan point (x, y), 0 outside it."""
    ye = outline_y(x)
    if ye <= 0 or abs(y) >= ye:
        return 0.0
    return prof(x, HT) * (1 - (abs(y) / ye) ** EXP) ** (1 / EXP)


def shell_normal(x, y):
    e = 0.05
    gx = (shell_height(x + e, y) - shell_height(x - e, y)) / (2 * e)
    gy = (shell_height(x, y + e) - shell_height(x, y - e)) / (2 * e)
    return Vector((-gx, -gy, 1)).normalized()


# ---- geometry builders (Part in sprite px) ------------------------------------------------------

def ring_loft(P, stations, mats, cap0=True, cap1=True, close=True):
    """Loft along X through rings [(x, [(y, z)...])]; mats[i] between ring i and i + 1."""
    rings = []
    for x, loop in stations:
        rings.append(([P.v((x, y, z)) for y, z in loop], x))
    for i, ((r0, x0), (r1, x1)) in enumerate(zip(rings, rings[1:])):
        n = len(r0)
        cy = sum(v.co.y for v in r0) / n
        cz = sum(v.co.z for v in r0) / n
        for a in range(n if close else n - 1):
            b = (a + 1) % n
            P.f((r0[a], r0[b], r1[b], r1[a]), mats[i], away=((x0 + x1) / 2, cy, cz))
    if cap0:
        P.f(rings[0][0], mats[0], out=(-1, 0, 0))
    if cap1:
        P.f(rings[-1][0], mats[-1], out=(1, 0, 0))
    return rings


def shell(P, mat_top, mat_bot):
    """The half-shell: loft from the cut face east to the tip, closed by a fan at the tip."""
    xs = [X0 + (XE - X0) * math.sin(0.5 * math.pi * k / 30) for k in range(30)]
    rings = []
    for x in xs:
        rings.append([P.v((x, y, z)) for y, z in section(x)])
    n = NSEC
    for r0, r1, xa, xb in zip(rings, rings[1:], xs, xs[1:]):
        for a in range(n):
            b = (a + 1) % n
            m = mat_top if a < n // 2 else mat_bot
            P.f((r0[a], r0[b], r1[b], r1[a]), m, away=((xa + xb) / 2, 0, 0))
    tip = P.v((XE, 0, 0))
    for a in range(n):
        b = (a + 1) % n
        P.f((rings[-1][a], rings[-1][b], tip), mat_top if a < n // 2 else mat_bot, away=(xs[-1] - 1, 0, 0))
    P.f(rings[0], mat_top, out=(-1, 0, 0))  # the cut face (behind the core)


def hoop(P, x0, w, g, mat, a0=0.0, a1=2 * math.pi, ch=0.3, sink=0.5, taper=0.0, base_x=None):
    """An armour band lying on the shell along its section at X = x0, from section angle a0 to a1
    (the full loop when a1 - a0 = 2 pi): chamfered rectangular section w wide, g proud."""
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    bx = x0 if base_x is None else base_x
    m = 72 if full else max(8, int(48 * (a1 - a0) / math.pi))
    xs = (x0 - w / 2, x0 - w / 2 + ch, x0 + w / 2 - ch, x0 + w / 2)
    prof4 = [(xs[0], -sink), (xs[0], g - ch), (xs[1], g), (xs[2], g), (xs[3], g - ch), (xs[3], -sink)]
    rings = []
    for k in range(m if full else m + 1):
        a = a0 + (a1 - a0) * k / m
        ye, zt, zb = outline_y(max(bx, X0)), prof(max(bx, X0), HT), prof(max(bx, X0), HB)
        c, s = math.cos(a), math.sin(a)
        y = ye * spow(c, 2 / EXP)
        z = (zt if s >= 0 else zb) * spow(s, 2 / EXP)
        e = 1e-3
        c2, s2 = math.cos(a + e), math.sin(a + e)
        y2 = ye * spow(c2, 2 / EXP)
        z2 = (zt if s2 >= 0 else zb) * spow(s2, 2 / EXP)
        ty, tz = y2 - y, z2 - z
        ln = math.hypot(ty, tz) or 1.0
        ny, nz = tz / ln, -ty / ln
        gk = 1.0
        if taper and not full:
            d = min(a - a0, a1 - a) / taper
            gk = max(0.0, min(1.0, d))
        ring = []
        for px_, off in prof4:
            o = off if off < 0 else off * gk
            # the shell drops away east of x0: keep the band's foot under it
            ring.append(P.v((px_, y + ny * o, z + nz * o)))
        rings.append(ring)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if full else [])
    for r0, r1 in pairs:
        for i in range(len(prof4) - 1):
            P.f((r0[i], r0[i + 1], r1[i + 1], r1[i]), mat, away=(x0, 0, 0))
        P.f((r0[-1], r0[0], r1[0], r1[-1]), mat, away=(x0, r0[0].co.y * 3, r0[0].co.z * 3))
    if not full:
        c0 = Vector((x0, 0, 0))
        P.f(list(reversed(rings[0])), mat, away=tuple(rings[1][2].co))
        P.f(rings[-1], mat, away=tuple(rings[-2][2].co))


def local_frame(origin, normal, up=(0, 0, 1)):
    n = Vector(normal).normalized()
    u = Vector(up)
    t = u.cross(n)
    if t.length < 1e-6:
        t = Vector((1, 0, 0)).cross(n)
    t.normalize()
    b = n.cross(t)
    return Vector(origin), t, b, n


def block(P, frame, x0, x1, y0, y1, z0, z1, ch, mat):
    """A chamfered box in a local frame (o, ex, ey, ez)."""
    o, ex, ey, ez = frame
    pts = [tuple(o + ex * a + ey * b + ez * c) for a, b, c in T.cbox(x0, x1, y0, y1, z0, z1, ch)]
    T.hull(P, pts, mat)


def dome_on(P, centre, normal, rx, ry, h, mat, seg=14, rings=5, sink=0.6, up=(0, 1, 0)):
    """A domed cap (lens, bolt head, boss) standing on the shell along `normal`."""
    o, ex, ey, ez = local_frame(centre, normal, up)
    o = o - ez * sink
    loops = []
    for j in range(rings + 1):
        t = 0.5 * math.pi * j / rings
        r, z = math.cos(t), math.sin(t)
        if j == rings:
            break
        loops.append([P.v(tuple(o + ex * (rx * r * math.cos(2 * math.pi * i / seg))
                                + ey * (ry * r * math.sin(2 * math.pi * i / seg)) + ez * (sink + h * z)))
                      for i in range(seg)])
    top = P.v(tuple(o + ez * (sink + h)))
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(seg):
            k = (i + 1) % seg
            P.f((l0[i], l0[k], l1[k], l1[i]), mat, away=tuple(o))
    for i in range(seg):
        P.f((loops[-1][i], loops[-1][(i + 1) % seg], top), mat, away=tuple(o))
    P.f(list(reversed(loops[0])), mat, out=tuple(-ez))


def patch(P, outline, lift, mat, wall_mat=None, sink=0.6, rings=4):
    """A plate conforming to the dome over a plan outline [(x, y)], `lift` proud, closed by a wall
    down into the shell."""
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    loops = []
    for j in range(rings, 0, -1):
        s = j / rings
        lp = []
        for x, y in outline:
            px_, py_ = cx + (x - cx) * s, cy + (y - cy) * s
            lp.append(P.v((px_, py_, shell_height(px_, py_) + lift)))
        loops.append(lp)
    centre = P.v((cx, cy, shell_height(cx, cy) + lift))
    for l0, l1 in zip(loops, loops[1:]):
        n = len(l0)
        for i in range(n):
            k = (i + 1) % n
            P.f((l0[i], l0[k], l1[k], l1[i]), mat, out=(0, 0, 1))
    n = len(loops[-1])
    for i in range(n):
        P.f((loops[-1][i], loops[-1][(i + 1) % n], centre), mat, out=(0, 0, 1))
    foot = [P.v((x, y, shell_height(x, y) - sink)) for x, y in outline]
    n = len(outline)
    for i in range(n):
        k = (i + 1) % n
        P.f((loops[0][i], loops[0][k], foot[k], foot[i]), wall_mat if wall_mat is not None else mat,
            away=(cx, cy, shell_height(cx, cy) - 3))
    P.f(list(reversed(foot)), mat, out=(0, 0, -1))


def bezel(P, outline, w, lift, mat, sink=0.6):
    """A raised frame round a plan outline, w px wide outward."""
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    n = len(outline)
    inner, outer = [], []
    for i, (x, y) in enumerate(outline):
        x0, y0 = outline[i - 1]
        x1, y1 = outline[(i + 1) % n]
        tx, ty = x1 - x0, y1 - y0
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = ty / ln, -tx / ln
        if nx * (x - cx) + ny * (y - cy) < 0:
            nx, ny = -nx, -ny
        inner.append((x, y))
        outer.append((x + nx * w, y + ny * w))
    def lv(pts, dz):
        return [P.v((x, y, shell_height(x, y) + dz)) for x, y in pts]
    ib, it, ot, ob = lv(inner, -sink), lv(inner, lift), lv(outer, lift * 0.7), lv(outer, -sink)
    for i in range(n):
        k = (i + 1) % n
        P.f((it[i], it[k], ot[k], ot[i]), mat, out=(0, 0, 1))
        P.f((ot[i], ot[k], ob[k], ob[i]), mat, away=(cx, cy, shell_height(cx, cy) - 2))
        P.f((ib[i], ib[k], it[k], it[i]), mat, out=None, away=(cx, cy, shell_height(cx, cy) + 6))
        P.f((ob[i], ob[k], ib[k], ib[i]), mat, out=(0, 0, -1))


def surface_strip(P, pts, w, lift, mat, sink=0.4):
    """A thin strip lying on the dome along plan points (a modelled seam), tapered at the ends."""
    dense = [pts[0]]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        m = max(1, int(math.hypot(xb - xa, yb - ya) / 0.5))
        dense += [(xa + (xb - xa) * k / m, ya + (yb - ya) * k / m) for k in range(1, m + 1)]
    pts = dense
    n = len(pts)
    tops, feetL, feetR = [], [], []
    left_pts, right_pts = [], []
    for i, (x, y) in enumerate(pts):
        xa, ya = pts[max(0, i - 1)]
        xb, yb = pts[min(n - 1, i + 1)]
        tx, ty = xb - xa, yb - ya
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        k = 0.25 if i in (0, n - 1) else 1.0
        hw = w / 2 * k
        left_pts.append((x + nx * hw, y + ny * hw))
        right_pts.append((x - nx * hw, y - ny * hw))
    L = [P.v((x, y, shell_height(x, y) + lift)) for x, y in left_pts]
    R = [P.v((x, y, shell_height(x, y) + lift)) for x, y in right_pts]
    Lf = [P.v((x, y, shell_height(x, y) - sink)) for x, y in left_pts]
    Rf = [P.v((x, y, shell_height(x, y) - sink)) for x, y in right_pts]
    for i in range(n - 1):
        x, y = pts[i]
        c = (x, y, shell_height(x, y) - 3)
        P.f((L[i], L[i + 1], R[i + 1], R[i]), mat, out=(0, 0, 1))
        P.f((Lf[i], Lf[i + 1], L[i + 1], L[i]), mat, away=c)
        P.f((R[i], R[i + 1], Rf[i + 1], Rf[i]), mat, away=c)
        P.f((Rf[i], Rf[i + 1], Lf[i + 1], Lf[i]), mat, out=(0, 0, -1))
    P.f((L[0], R[0], Rf[0], Lf[0]), mat, away=(pts[1][0], pts[1][1], shell_height(*pts[1])))
    P.f((L[-1], Lf[-1], Rf[-1], R[-1]), mat, away=(pts[-2][0], pts[-2][1], shell_height(*pts[-2])))


# ---- materials -----------------------------------------------------------------------------------

def make_materials(sprite):
    tag = "nshaB"
    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    M = {}
    M["dome"] = pal(103, metallic=0.4, roughness=0.4)
    M["keel"] = M["dome"]  # one satin shell; the underside needs no colour break
    M["flange"] = pal(104, metallic=0.6, roughness=0.3)
    M["rib"] = pal(107, metallic=0.6, roughness=0.3)
    M["face"] = pal(100, metallic=0.5, roughness=0.45)
    M["bay"] = pal(100, metallic=0.45, roughness=0.5)
    M["bezel"] = pal(102, metallic=0.6, roughness=0.32)
    M["lens"] = pal(96, metallic=0.7, roughness=0.12)
    M["seam"] = pal(99, metallic=0.45, roughness=0.5)
    M["bolt"] = pal(108, metallic=0.65, roughness=0.28)
    M["clamp"] = pal(8, metallic=0.6, roughness=0.35)
    M["clampdk"] = pal(6, metallic=0.6, roughness=0.4)
    M["core"] = pal(119, emission_strength=1.0)
    M["fireside"] = pal(118, emission_strength=1.0)
    M["firetop"] = pal(122, emission_strength=1.0)
    M["fireend"] = pal(123, emission_strength=1.0)
    M["fire119"] = pal(119, emission_strength=1.0)
    M["fire123"] = pal(123, emission_strength=1.0)
    M["fire125"] = pal(125, emission_strength=1.05)
    M["ribB"] = pal(108, metallic=0.6, roughness=0.3)
    M["firehot"] = pal(126, emission_strength=1.15)
    for i in range(114, 128):
        M[f"f{i}"] = pal(i, emission_strength={125: 1.05, 126: 1.15, 127: 1.25}.get(i, 1.0))
    M["firewhite"] = pal(127, emission_strength=1.25)
    mats, slot = [], {}
    for k, m in M.items():
        if m not in mats:
            mats.append(m)
        slot[k] = mats.index(m)
    return mats, slot


# ---- the pod -------------------------------------------------------------------------------------

CLAMPS = [(16.0, 5.0), (1.0, 7.0), (-14.0, 5.0)]  # (Y of the clamp centre, width) on the top arc


def cut_loop_point(y, grow=0.0):
    """The top-arc point of the cut face's boundary at plan Y = y, and its outward YZ normal."""
    ye, zt = outline_y(X0), prof(X0, HT)
    c = max(-1.0, min(1.0, spow(y / ye, EXP / 2)))
    a = math.acos(c)
    z = zt * spow(math.sin(a), 2 / EXP)
    yy = ye * spow(math.cos(a), 2 / EXP)
    e = 1e-3
    y2 = ye * spow(math.cos(a + e), 2 / EXP)
    z2 = zt * spow(math.sin(a + e), 2 / EXP)
    ty, tz = y2 - yy, z2 - z
    ln = math.hypot(ty, tz)
    ny, nz = tz / ln, -ty / ln
    return Vector((X0, yy + ny * grow, z + nz * grow)), Vector((0, ny, nz)), Vector((0, ty / ln, tz / ln))


def build(frame, M, mats, coll, name, data):
    P = T.Part(name, smooth_angle=34.0)
    shell(P, M["dome"], M["keel"])
    # Flange hoop round the cut face (columns 25-26) and armour hoop rib A beside it (27-28).
    hoop(P, 2.0, 2.1, 0.8, M["flange"], ch=0.35, sink=1.4, base_x=X0)
    hoop(P, 4.05, 1.6, 0.5, M["rib"], ch=0.3, sink=0.8)
    # Rib B: an armour strap from the north equator over the crest, ending at row 24 (Y 4) on bolts.
    ye7 = outline_y(7.0)
    a_end = math.acos(spow(4.0 / ye7, EXP / 2))
    hoop(P, 7.0, 2.0, 0.45, M["ribB"], a0=-0.12, a1=a_end, ch=0.3, sink=0.8, taper=0.12)
    for bx, by in ((7.0, 5.6),):
        dome_on(P, (bx, by, shell_height(bx, by) + 0.35), shell_normal(bx, by), 0.85, 0.85, 0.55, M["bolt"],
                seg=10, rings=3)
    # Crest boss below the sensor bay (bright knob, column 34 row 19).
    dome_on(P, (10.2, 9.0, shell_height(10.2, 9.0)), shell_normal(10.2, 9.0), 1.15, 1.15, 0.7, M["rib"],
            seg=12, rings=3)
    # Sensor bay on the north slope (columns 33-38, rows 10-17): dark plate in a raised bezel, two lenses.
    bay = []
    cxb, cyb, hx, hy = 11.9, 14.2, 2.7, 3.9
    for i in range(20):
        a = 2 * math.pi * i / 20
        bay.append((cxb + hx * spow(math.cos(a), 0.55), cyb + hy * spow(math.sin(a), 0.55)))
    patch(P, bay, 0.1, M["bay"])
    bezel(P, bay, 0.7, 0.55, M["bezel"])
    for lx, ly in ((11.9, 16.3), (12.3, 12.3)):
        dome_on(P, (lx, ly, shell_height(lx, ly) + 0.1), shell_normal(lx, ly), 1.55, 1.55, 0.8, M["lens"],
                seg=14, rings=4)
    # Modelled plating seams (the sprite's dark arcs on the south half).
    # Long swirl arcs: the sprite's dark line down column 42 (rows 16-24) curving south-west along
    # row 29-30 to the rib, and two lower arcs sweeping up to the east (D-A arcs).
    surface_strip(P, [(18.6, 12.2), (18.7, 9.5), (18.4, 6.5), (17.4, 3.6), (15.6, 1.0), (13.4, -1.2), (10.8, -2.4),
                      (8.0, -3.0), (5.4, -3.4)], 0.7, 0.06, M["seam"])
    surface_strip(P, [(4.6, -7.2), (8.0, -6.6), (11.5, -5.8), (14.5, -4.6), (17.0, -2.8), (19.2, -0.4),
                      (20.6, 2.4)], 0.7, 0.06, M["seam"])
    surface_strip(P, [(5.2, -15.0), (9.0, -13.6), (12.8, -11.4), (15.8, -8.6), (18.2, -5.6), (19.8, -2.6)],
                  0.6, 0.05, M["seam"])

    # Core disc in the cut face (columns 23-24): its glowing face stands 2 px west of the flange.
    cut = lambda g: section(X0, grow=g)  # noqa: E731
    ring_loft(P, [(0.7, cut(-0.35)), (-0.5, cut(-0.35)), (-1.0, cut(-0.9))], [M["core"], M["core"]],
              cap0=False, cap1=False)
    # The cut face itself is dark satin metal; only a horizontal slit in it glows (D126). The slit
    # fits the slab with a thin glowing lip in frames 1-3 and closes to a thin red line in frame 4.
    inner = cut(-0.9)
    slab_z = SLAB_Z[frame]
    sz = SLIT_LINE if slab_z is None else (slab_z[0] + SLIT_LIP, slab_z[1] + SLIT_LIP)
    slit = section(X0, ye=SLIT_YE, zt=sz[0], zb=sz[1], exp=SLAB_EXP, n=NSEC)
    o_ring = [P.v((-1.0, y, z)) for y, z in inner]
    s_ring = [P.v((-1.0, y, z)) for y, z in slit]
    for a in range(NSEC):
        b = (a + 1) % NSEC
        P.f((o_ring[a], o_ring[b], s_ring[b], s_ring[a]), M["face"], out=(-1, 0, 0))
    glow = M[f"f{SLIT_GLOW[frame]}"]
    back = [P.v((-0.45, y, z)) for y, z in slit]
    for a in range(NSEC):  # the recess walls face into the slit, its back faces out of it
        b = (a + 1) % NSEC
        my, mz = (slit[a][0] + slit[b][0]) / 2, (slit[a][1] + slit[b][1]) / 2
        P.f((s_ring[a], s_ring[b], back[b], back[a]), glow, away=(-0.7, 3 * my, 3 * mz))
    P.f(back, glow, out=(-1, 0, 0))

    # Three clamps over the face's top arc (the sprite's grey brackets, columns 22-24).
    for y, w in CLAMPS:
        o, nrm, tan = cut_loop_point(y)
        fr = (o, Vector((1, 0, 0)), tan, nrm)
        block(P, fr, -3.1, -0.2, -w / 2, w / 2, -3.4, 2.3, 0.45, M["clamp"])
        block(P, fr, -1.0, 1.5, -w / 2 + 0.5, w / 2 - 0.5, 0.2, 2.0, 0.35, M["clamp"])
        block(P, fr, -3.25, -2.9, -w / 2 + 0.9, w / 2 - 0.9, -2.6, 1.4, 0.12, M["clampdk"])
        # bolt head on its west face
        bo = o + nrm * (0.6)
        P2 = Vector((-3.1, 0, 0))
        dome_on(P, tuple(bo + P2), (-1, 0, 0), 0.75, 0.75, 0.45, M["clampdk"], seg=8, rings=2, sink=0.3,
                up=(0, 0, 1))

    # The plasma slab (frames 1-3): a chamfered lens-section block out of the core.
    left = FIRE_LEFT[frame]
    if left is not None:
        xl = left - 24.0
        zt_s, zb_s = slab_z
        sh_ = FIRE_SHIFT[frame]

        def F(i):
            return M[f"f{max(114, i - sh_)}"]

        def sec(g, ye=SLAB_YE):
            return section(X0, grow=g, ye=ye, zt=zt_s, zb=zb_s, exp=SLAB_EXP, n=48)
        # out of the slit (Y 15) it fans to its full width by X -1.6, then runs straight to its end
        stations = [(-0.6, sec(0, SLIT_YE - 0.2)), (-1.6, sec(0)), (xl + 0.6, sec(0)), (xl + 0.2, sec(-0.35)),
                    (xl, sec(-0.75))]
        rings = ring_loft(P, stations, [M["fireside"]] * 4, cap0=True, cap1=False)
        end = rings[-1][0]
        P.f(list(reversed(end)), F(123), out=(-1, 0, 0))
        hot = section(X0, ye=12.5, zt=zt_s * 0.55, zb=zb_s * 0.55, exp=2.4, n=32)
        ring_loft(P, [(xl + 0.4, hot), (xl - 0.2, [(y * 0.92, z * 0.88) for y, z in hot])],
                  [F(126)], cap0=False, cap1=True)
        # Molten top: overlapping flattened flame lobes along the slab, hotter toward its north half
        # and along the white-hot streak of row 19 (sprite frame 1: rows 13-14, 18-20, 33-34).
        L = -0.2 - xl

        def on_fire(y):
            return zt_s * max(0.0, 1 - (abs(y) / SLAB_YE) ** SLAB_EXP) ** (1 / SLAB_EXP)

        def ribbon(y0, w, h, mat, phase):
            """A flattened plasma ribbon lying along X on the slab's top, swelling and drifting a
            little like a flame tongue, tapered into the slab at both ends."""
            xa, xb = xl + 0.7, -1.6
            n = max(6, int((xb - xa) / 0.8))
            seg = 10
            loops = []
            for k in range(n + 1):
                t = k / n
                x = xa + (xb - xa) * t
                env = math.sin(math.pi * t) ** 0.45
                yy = y0 + 0.3 * math.sin(0.9 * x + phase)
                ww = w * env * (0.88 + 0.12 * math.sin(1.3 * x + 2 * phase))
                hh = h * env * (0.8 + 0.2 * math.sin(1.1 * x + phase))
                base = on_fire(yy) - 0.45
                loop = []
                for i in range(seg):
                    a_ = math.pi * i / (seg - 1)
                    loop.append(P.v((x, yy + ww * math.cos(a_), base + (0.45 + hh) * math.sin(a_) ** 0.8)))
                loops.append(loop)
            for l0, l1 in zip(loops, loops[1:]):
                for i in range(seg - 1):
                    P.f((l0[i], l0[i + 1], l1[i + 1], l1[i]), mat, out=(0, 0, 1))
                P.f((l0[-1], l0[0], l1[0], l1[-1]), mat, out=(0, 0, -1))
            P.f(loops[0], mat, out=(1, 0, 0))
            P.f(loops[-1], mat, out=(-1, 0, 0))
        ribbon(14.3, 1.7, 0.45, F(125), 0.3 + frame)
        ribbon(9.0, 1.5, 0.7, F(126), 1.1 + frame)       # the white-hot streak (row 19)
        ribbon(3.0, 2.2, 0.4, F(121), 2.0 + frame)
        ribbon(-5.5, 2.0, 0.55, F(125), 0.7 + frame)
        ribbon(-11.8, 1.8, 0.35, F(122), 1.6 + frame)
        spots = [(xl + 0.55 * L, -5.5, min(1.8, 0.3 * L), 1.6)]
        if frame == 0:
            spots.append((xl + 0.62 * L, 14.4, 1.7, 1.1))
        for sx, sy, rx, ry in spots:
            dome_on(P, (sx, sy, on_fire(sy) + 0.15), (0, 0, 1), rx, ry, 0.5, F(127), seg=12, rings=3,
                    sink=0.6)

    obj = finish(P, mats, coll)
    if left is not None:
        recolour_fire(obj, M, left - 24.0, fire_grid(data, frame), FIRE_SHIFT[frame])
    return obj


def fire_grid(data, frame):
    """The sprite's own fire indices (right pod, frame k): {(col, row): palette index}, columns
    10-24 of the 48 x 56 block (newsha-1 on top, newsha-39 below)."""
    g = {}
    for name, r0 in (("newsha-1", 0), ("newsha-39", 28)):
        fr = data[name]["frames"][frame]
        for r, row in enumerate(fr["pixels"]):
            for c, v in enumerate(row.split() if isinstance(row, str) else row):
                if int(v) >= 100:
                    g[(c, r0 + r)] = int(v)
    return g


def recolour_fire(obj, M, xl, grid, shift=0):
    """Plasma slab body: every face of the top and upper flanks takes the median of the sprite's
    fire indices under it (a +-1 row window over the face's columns), so the slab reads yellow-orange
    with the white-hot band low on it and only a thin dark-red edge, as the sprite does. Faces
    turned to the side stay a deep red (the slab's rim)."""
    me = obj.data
    side = M["fireside"]
    slot = {i: M[f"f{i}"] for i in range(114, 128)}
    for p in me.polygons:
        if p.material_index != side:
            continue
        c = p.center / PX
        if c.x > -0.5 or c.x < xl + 0.55:
            continue
        if p.normal.z < 0.25:
            p.material_index = slot[116]
            continue
        xs = [v.co.x / PX for v in (me.vertices[i] for i in p.vertices)]
        ys = [v.co.y / PX for v in (me.vertices[i] for i in p.vertices)]
        c0, c1 = int(math.floor(min(xs) + 24)), int(math.floor(max(xs) + 24))
        r0, r1 = int(math.floor(28 - max(ys))), int(math.floor(28 - min(ys)))
        vals = sorted(grid[(cc, rr)] for cc in range(c0, c1 + 1) for rr in range(r0, r1 + 1)
                      if (cc, rr) in grid and grid[(cc, rr)] >= 118)
        if not vals:
            continue
        v = max(118, vals[len(vals) // 2] - shift)
        if p.normal.z < 0.55:
            v = max(118, v - 1)
        p.material_index = slot[v]


def finish(P, mats, coll):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.scale(bm, vec=(PX, PX, PX), verts=bm.verts)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(P.smooth_angle))
    return obj


def mirror_copy(obj, name, coll):
    me = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.scale(bm, vec=(-1, 1, 1), verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    out = bpy.data.objects.new(name, me)
    coll.objects.link(out)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34.0))
    return out


def split_open(obj, layout, coll):
    """split_assembly's cut without capping (for the outline shell: no ink line at the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
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


def model_name(piece, frame):
    return piece if frame == 0 else f"{piece}-f{frame + 1}"


def load_sprites():
    data = {}
    merged = None
    for name in RIGHT["pieces"] + LEFT["pieces"]:
        d = common.load_sprite(ROOT, name)
        data[name] = d
        if merged is None:
            merged = {"name": "assembly-newsha-1", "colors": dict(d["colors"])}
        merged["colors"].update(d["colors"])
    return data, merged


def layout_of(side, data):
    first = data[side["pieces"][0]]
    ox, oy = side["origin"]
    return [(e["model"], e["cx"] - ox, e["cy"] - oy) for e in first["assemblyLayout"] if e["model"] in side["pieces"]]


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    review = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    data, sprite = load_sprites()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection("newshaB")
    mats, M = make_materials(sprite)
    lay_r = layout_of(RIGHT, data)
    lay_l = layout_of(LEFT, data)
    export, wholes, stats = [], [], {}
    for frame in range(4):
        whole = build(frame, M, mats, coll, f"pod-f{frame + 1}", data)
        shell_src = whole  # sealed, pre-cull
        sh = common.outline_shell(shell_src, coll, voxel=0.016, faces=4000, smooth=6, inside=0.008)
        T.cull_hidden(whole)
        wholes.append(whole)
        stats[f"whole_f{frame + 1}"] = tris(whole)
        left_whole = mirror_copy(whole, f"podL-f{frame + 1}", coll)
        left_sh = mirror_copy(sh, f"podL-f{frame + 1}_sh", coll)
        for side, lay, w, s in ((RIGHT, lay_r, whole, sh), (LEFT, lay_l, left_whole, left_sh)):
            names = [n for n in side["pieces"] if n in side["animated"] or frame == 0]
            sub = [e for e in lay if e[0] in names]
            pieces = common.split_assembly(w, sub, coll)
            shells = split_open(s, sub, coll)
            for name, cx, cy in sub:
                mdl = model_name(name, frame) if name in side["animated"] else name
                pc, ps = pieces[name], shells[name]
                pc.name, ps.name = mdl, f"{mdl}_outline"
                for o in (pc, ps):
                    o.location = (0, 0, 0)
                pc.data.shade_smooth()
                pc.data.set_sharp_from_angle(angle=math.radians(34.0))
                stats[mdl] = tris(pc)
                export.append((name, mdl, frame, pc, ps))
    if "--no-export" not in argv:
        for name, mdl, frame, pc, ps in export:
            sprites = data[name]["sprites"]
            if name in RIGHT["animated"] + LEFT["animated"]:
                sprites = [{**sp, "frames": [sp["frames"][frame]]} for sp in sprites]
            common.export_sprite_model(ROOT, [pc, ps], f"enemies/{mdl}", sprites)
    print("STATS", json.dumps(stats))
    if review:
        review_views(wholes, mats, sprite, review)


# ---- review renders --------------------------------------------------------------------------------

def srgb_lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def setup_wb(flat):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_object_outline = False
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def setup_game():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("game_sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sd)
    bpy.context.scene.collection.objects.link(sun)
    d = Vector((-6, -8.4, 20)).normalized()
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    return sun


def camera(location, look_at, ortho=None, fov=None, top=False):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov)
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, path, rx, ry):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def only(objs):
    keep = {o.name for o in objs}
    for o in bpy.context.scene.objects:
        if o.type in ("MESH",):
            o.hide_render = o.name not in keep
    bpy.context.view_layer.update()


def review_views(wholes, mats, sprite, out):
    out.mkdir(parents=True, exist_ok=True)
    for m in mats:
        g = re.match(r"pal_(\d+)", m.name)
        rgb = sprite["colors"].get(g.group(1)) if g else None
        if rgb:
            m.diffuse_color = (*[srgb_lin(c) for c in rgb], 1.0)
    K, W, H = 8, 48, 56
    for k, w in enumerate(wholes):
        only([w])
        setup_wb(True)
        render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / f"top_flat_f{k + 1}.png", W * K, H * K)
    # shaded views of frames 1 and 4 (game-lit, Eevee)
    sun = setup_game()
    P = 320
    for k in (1, 2):
        only([wholes[k]])
        render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / f"top_game_f{k + 1}.png", W * K, H * K)
    for k in (0, 3):
        w = wholes[k]
        only([w])
        f = f"f{k + 1}"
        render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / f"top_game_{f}.png", W * K, H * K)
        d = 9.0
        tilt = math.radians(32)
        render(camera((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), out / f"game_{f}.png", P, P)
        render(camera((0, -30, 0.2), (0, 0, 0.2), ortho=5.4), out / f"front_{f}.png", P, P)   # from the south
        render(camera((0, 30, 0.2), (0, 0, 0.2), ortho=5.4), out / f"rear_{f}.png", P, P)     # from the north
        render(camera((-30, 0, 0.2), (0, 0, 0.2), ortho=5.4), out / f"west_{f}.png", P, P)    # the cut face
        render(camera((30, 0, 0.2), (0, 0, 0.2), ortho=5.4), out / f"east_{f}.png", P, P)
        render(camera((-5.5, -5.0, 5.0), (0, 0, 0), fov=35), out / f"q_sw_{f}.png", P, P)
        render(camera((6.0, 5.0, 4.6), (0, 0, 0), fov=35), out / f"q_ne_{f}.png", P, P)
        render(camera((-4.0, -5.0, -5.0), (0, 0, 0), fov=35), out / f"under_{f}.png", P, P)
    # the mirror pair at the game camera (gap shortened)
    pairs = []
    for k in (0, 2):
        L = mirror_copy(wholes[k], f"pairL{k}", wholes[k].users_collection[0])
        L.location = (-6.0, 0, 0)
        R = wholes[k]
        R.location = (0.0, 0, 0)
        only([L, R])
        tilt = math.radians(32)
        d = 15.0
        render(camera((-3.0, -d * math.sin(tilt), d * math.cos(tilt)), (-3.0, 0, 0), fov=35),
               out / f"pair_f{k + 1}.png", 2 * P, P)
        bpy.data.objects.remove(L, do_unlink=True)
    bpy.data.objects.remove(sun, do_unlink=True)


if __name__ == "__main__":
    main()
