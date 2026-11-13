"""Caged gunships of episode 3 (newsh7-51, newsh7-237, newsh7-13), design A: a hard-surface build
of the sprite, shared by the three scripts (the old lib_b007.build_gunship stays for its other users).

What it is: a small drone gunship. newsh7-51 flies hull first (it drifts down the screen, so the
shield hull at the sprite's bottom is its nose and the thruster at the top its tail). Down its
spine, tail to nose:
- a ribbed engine block (rows 3-7): two cheeks either side of a flared exhaust bell, five cooling
  fins along the deck (the sprite's columns 7, 9, 11, 13, 15; the ink columns between are slots);
- the thruster flame out of the bell (one frame-tagged flame per sprite frame, D17: its tip reaches
  rows 2, 1 and 0 and it brightens red -> yellow -> a white-hot core);
- a grey bar cage: a round bar leaves each side of the block at row 4, turns the corner at column 2
  and runs down the side, through a machined ferrule at row 9, into a blue blade;
- a glossy blue spindle pod on a grey yoke (a cross axle with a hub collar);
- 51/237: the blades sweep in and down to a cross wing (row 16, columns 1-21), and the shield hull
  (rows 15-27) is an armoured plate with a raised keel, blue struts, a seam and a raised rim;
- 13: the same engine at both ends, a two-bulb spindle between, short chevron blades on axles.
newsh7-237 is 51 flipped top to bottom and one column right (FLIP, DC). Undersides are plain
closed shapes.

Colours: each part takes the sprite's median palette index for its region (dark shading and bright
sheen left to the game's light): block 6, fins 7/8, bars 9, blades 56, spindle 54, wing 55, yoke 6,
keel 6 (5 past the seam), struts 54, hull plates 6, rim 7. Blue and steel as newsh7-53/-152.

Outline shell (D90/D118): one shell per disjoint part of the sealed pre-cull copy (common.
outline_shell keeps only the largest island); every part here overlaps its neighbours, so the
remesh is one island, and `check_shell` asserts the shell covers the body's whole plan.
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newsh7-51"  # set by each build_* (the materials and objects are named after the model)
PX = 1 / 12
W, H = 24, 28
CU = 11.5  # the centre line (pixel-edge column): the sprite is symmetric about column 11
FLAMES = (51, 89, 127)  # the flame frames, set by each build_*
FLIP = False  # newsh7-237: the whole model mirrored top to bottom
DC = 0  # ... and shifted DC columns right
ZN = 3.25  # the exhaust's axis height: proud of the deck so the tilted camera sees the flame


def P(x, v, z):
    """x px from the centre line (+ = right), sprite pixel-edge row v, height z px -> world
    (FLIP mirrors the row top to bottom, DC shifts columns: newsh7-237)."""
    if FLIP:
        v = H - v
    return Vector(((CU + x + DC - W / 2) * PX, (H / 2 - v) * PX, z * PX))


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


# --- mesh helpers ---------------------------------------------------------------------------------

def loft_rings(bm, rings, mat, cap0=True, cap1=True):
    """Join closed rings of points (equal counts; a 1-point ring is a tip) in order. `mat` is an int
    or a function (face centre Vector in px space) -> material index. Caps are fans to the centroid."""
    def mi(face):
        if callable(mat):
            c = sum((v.co for v in face.verts), Vector()) / len(face.verts)
            return mat(c / PX)
        return mat
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for r0, r1 in zip(vs, vs[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[j], r1[i]))
            elif len(r1) == 1:
                f = bm.faces.new((r0[i], r0[j], r1[0]))
            else:
                f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mi(f)
    for ring, on, rev in ((vs[0], cap0, True), (vs[-1], cap1, False)):
        if not on or len(ring) < 3:
            continue
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ring[j], ring[i], c) if rev else (ring[i], ring[j], c))
            f.material_index = mi(f)
    return vs


def ellipse(cx, v, z, hw, hh, n=12, along="y"):
    """A ring round an axis along Y (in the XZ plane) at row v; or along X (in the YZ plane) at x=cx."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        if along == "y":
            pts.append(P(cx + hw * math.cos(a), v, z + hh * math.sin(a)))
        else:
            pts.append(P(cx, v + hw * math.cos(a), z + hh * math.sin(a)))
    return pts


def chamfer_rect(cx, v, hw, zb, zt, c, cb=None):
    """An 8-point chamfered rectangle (XZ plane) at row v: half width hw, bottom zb, top zt."""
    cb = c if cb is None else cb
    pts = [(hw, zb + cb), (hw, zt - c), (hw - c, zt), (-hw + c, zt), (-hw, zt - c), (-hw, zb + cb),
           (-hw + cb, zb), (hw - cb, zb)]
    return [P(cx + x, v, z) for x, z in pts]


def sweep(bm, path, rw, rh, n=10, mat=0, caps=True):
    """A tube along a polyline of px points (x, v, z): rw = half width across the path in plan
    (horizontal), rh = half height; each a number or a list per point. Mitred joints."""
    pts = [P(*p) for p in path]
    rws = rw if isinstance(rw, (list, tuple)) else [rw] * len(pts)
    rhs = rh if isinstance(rh, (list, tuple)) else [rh] * len(pts)
    up = Vector((0, 0, 1))
    rings = []
    for i, c in enumerate(pts):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        t.normalize()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        vert = side.cross(t).normalized()
        # Mitre: stretch the in-plane width by 1/cos of the half turn so widths hold round bends.
        k = 1.0
        if d0 is not None and d1 is not None:
            k = 1.0 / max(0.6, math.cos(0.5 * d0.angle(d1, 0.0)))
        ring = []
        for j in range(n):
            a = 2 * math.pi * (j + 0.5) / n
            ring.append(c + rws[i] * PX * k * math.cos(a) * side + rhs[i] * PX * math.sin(a) * vert)
        rings.append(ring)
    return loft_rings(bm, rings, mat, caps, caps)


def mirror_path(path):
    return [(-x, v, z) for x, v, z in path]




# --- the model -------------------------------------------------------------------------------------

# The hull's plan (half width in px from the centre line, by pixel-edge row), fitted through the
# middles of the inner mask's steps: widest under the wing, stepping in to the waist at rows 20-22,
# then the shield's straight 45 degree sides to a short flat nose at row 27.
HULL_V = [14.7, 15.6, 16.4, 17.1, 18.0, 19.0, 20.0, 20.7, 22.4, 23.0, 26.5, 26.85]
HULL_W = [5.2, 6.4, 7.6, 8.6, 9.0, 8.0, 7.0, 6.55, 6.5, 6.0, 2.5, 2.05]
hull_w = pchip(HULL_V, HULL_W)
# Heights: the plate's crown (z at the centre line) and its edge, by row.
crown = pchip([14.7, 18.0, 21.0, 24.0, 26.85], [2.3, 2.7, 2.6, 2.3, 1.6])
edge = pchip([14.7, 20.0, 26.85], [1.4, 1.3, 1.0])
keel_top = pchip([15.25, 15.9, 18.0, 21.0, 24.0, 25.9, 26.75], [3.0, 4.15, 4.1, 3.85, 3.5, 3.1, 2.35])


def hull_ring(v, dip=0.0, ntop=17, nbot=7):
    hw = hull_w(v)
    zt, ze = crown(v) - dip, edge(v) - dip
    pts = []
    for i in range(ntop):  # top, right edge to left edge
        s = math.cos(math.pi * i / (ntop - 1))
        if i in (0, ntop - 1):
            pts.append(P(hw * s, v, ze - 0.45))  # the rounded lip
            continue
        z = ze + (zt - ze) * (1 - abs(s) ** 3)
        pts.append(P(hw * s * (0.985 if abs(s) > 0.95 else 1.0), v, z))
    for i in range(nbot):  # bottom, left to right: a shallow closed keel underneath
        s = -0.9 + 1.8 * i / (nbot - 1)
        z = (ze - 1.3) - 0.9 * (1 - s * s)
        pts.append(P(hw * s, v, z))
    return pts


def make_mats(sprite):

    def pal(i, metallic=0.6, roughness=0.4, spec=None, tag=None, **kw):
        if str(i) not in sprite["colors"]:  # newsh7-13 has no 3: the nearest index it does use
            i = min((int(k) for k in sprite["colors"]), key=lambda k: abs(k - i))
        m = common.palette_material(sprite, i, tag or NAME, metallic=metallic, roughness=roughness, **kw)
        if spec is not None:
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            b.inputs["Specular IOR Level"].default_value = spec
        return m

    mats = [
        pal(6, 0.6, 0.42),                 # 0 block body, yoke, hull plates
        pal(7, 0.65, 0.36, tag=f"{NAME}-fin"),   # 1 fins, hull rim
        pal(8, 0.65, 0.34, tag=f"{NAME}-nz"),    # 2 outer fins, nozzle bell, ferrules
        pal(9, 0.7, 0.3),                  # 3 cage bars
        pal(56, 0.1, 0.32, spec=0.9),       # 4 blades
        pal(54, 0.1, 0.22, spec=1.0),      # 5 spindle, struts
        pal(55, 0.1, 0.32, spec=0.9),       # 6 wing
        pal(5, 0.6, 0.45),                 # 7 keel past the seam, dark slots
        pal(3, 0.5, 0.6),                  # 8 nozzle throat walls (scorched)
        pal(112, 1.0, 0.9, emission_strength=1.0, frames={FLAMES[1]: 115, FLAMES[2]: 117}),  # 9 throat glow
    ]
    return mats


BODY, FIN, NOZ, BAR, BLADE, BLUE, WING, DARK, THROAT, GLOW = range(10)


GUN_BLADE = ([(-8.85, 8.9, 2.75), (-8.6, 10.2, 2.7), (-8.15, 11.35, 2.65), (-7.3, 12.35, 2.6),
              (-6.55, 13.35, 2.55), (-6.0, 14.4, 2.5), (-5.75, 15.4, 2.45), (-5.9, 16.5, 2.4)],
             [0.6, 0.8, 1.15, 1.3, 1.15, 1.0, 0.95, 0.9], [0.55, 0.55, 0.55, 0.55, 0.52, 0.5, 0.5, 0.5])


def engine(bm, blade=None):
    """The engine block with its fins and exhaust bell at the top (rows 2-8) and the cage bars round
    its sides, to row 9.5. `blade` = (path, half widths, half heights) of the blue blade each bar
    runs into."""

    # Engine block: the deck between the cheeks, rows 4.4-7.3, its front corners chamfered in to
    # the spindle's neck (inner mask: hw 5.5 to row 6, 4.5 on row 6, 2.5 on row 7).
    blk = [(4.35, 5.45), (5.9, 5.45), (6.6, 4.7), (7.2, 3.2), (7.8, 2.45)]
    loft_rings(bm, [chamfer_rect(0, v, hw, 0.9, 4.2, 0.5) for v, hw in blk], BODY)
    # Cheeks either side of the bell, out to row 3 (columns 6-8 / 14-16).
    for sx in (-1, 1):
        rings = [chamfer_rect(sx * 3.95, v, 1.45, 0.9, 4.2, 0.45) for v in (3.05, 4.6)]
        loft_rings(bm, rings, BODY)
    # Cooling fins along the deck: the outer pair from row 3 on the cheeks, the inner three behind
    # the bell; chamfered tops, standing 0.5 px proud, their ends sloped into the deck.
    for x, v0, m in ((-4.0, 3.15, NOZ), (4.0, 3.15, NOZ), (-2.0, 4.85, FIN), (2.0, 4.85, FIN), (0.0, 5.15, FIN)):
        v1 = 6.75 if abs(x) > 3 else 6.95
        rings = [chamfer_rect(x, v, 0.42, 3.6, 4.7, 0.2) for v in (v0, v0 + 0.3, v1 - 0.45, v1)]
        rings[0] = chamfer_rect(x, v0, 0.42, 3.6, 4.35, 0.15)
        rings[-1] = chamfer_rect(x, v1, 0.42, 3.6, 4.25, 0.15)
        loft_rings(bm, rings, m)
    # Exhaust port in the deck's back face (row 4.3): a raised collar with a flared lip, a scorched
    # throat and a glowing core; the flame pours out between the cheeks (rows 2-4, as the sprite).
    bell = [(5.05, 1.75, 1.1), (4.7, 2.05, 1.3), (4.4, 2.2, 1.38), (4.28, 2.22, 1.4)]
    loft_rings(bm, [ellipse(0, v, ZN, hw, hh, 16) for v, hw, hh in bell], NOZ, cap0=True, cap1=False)
    lip = [ellipse(0, 4.28, ZN, 2.22, 1.4, 16), ellipse(0, 4.3, ZN, 1.85, 1.08, 16),
           ellipse(0, 4.75, ZN, 1.55, 0.9, 16)]
    loft_rings(bm, lip, THROAT, cap0=False, cap1=False)
    loft_rings(bm, [ellipse(0, 4.75, ZN, 1.55, 0.9, 16), ellipse(0, 4.95, ZN, 1.0, 0.55, 16)], GLOW,
               cap0=False, cap1=True)

    # The cage: a round bar from each side of the block, round the corner and down the side,
    # through a ferrule into the blue blade that sweeps in and down to the wing.
    bar = [(-4.9, 4.5, 3.0), (-7.3, 4.5, 3.0), (-8.25, 4.85, 2.95), (-8.75, 5.6, 2.9), (-8.95, 6.6, 2.85),
           (-8.95, 8.0, 2.8), (-8.85, 9.35, 2.75)]
    for sx in (-1, 1):
        f = (lambda p: p) if sx < 0 else (lambda p: mirror_path(p))
        sweep(bm, f(bar), 0.6, 0.6, n=10, mat=BAR)
        if blade:
            sweep(bm, f(blade[0]), blade[1], blade[2], n=10, mat=BLADE)
        # Ferrule where bar meets blade (row 9) and a collar where the bar meets the block (row 4.5).
        sweep(bm, f([(-8.9, 8.55, 2.78), (-8.82, 9.55, 2.74)]), 0.85, 0.8, n=12, mat=NOZ)
        sweep(bm, f([(-5.2, 4.5, 3.0), (-5.85, 4.5, 3.0)]), 0.8, 0.8, n=12, mat=NOZ)



def gunship_body(bm):
    """Blades, yoke, spindle, wing and shield hull of newsh7-51 / newsh7-237 (rows 8-27)."""
    # The yoke: a cross axle between the blades (row 14) and a hub collar under the spindle's tip.
    sweep(bm, [(-6.4, 13.75, 2.3), (-5.2, 13.75, 2.3), (5.2, 13.75, 2.3), (6.4, 13.75, 2.3)],
          [0.9, 1.35, 1.35, 0.9], [0.55, 0.75, 0.75, 0.55], n=14, mat=DARK)
    hub = [(13.75, 1.5, 1.15), (14.0, 2.05, 1.6), (15.2, 2.05, 1.6), (15.45, 1.6, 1.25)]
    loft_rings(bm, [ellipse(0, v, 2.6, hw, hh, 14) for v, hw, hh in hub], NOZ)

    # Spindle: a glossy blue pod, diamond in plan, from the block's chin to its tip in the hub.
    spin = [(7.1, 1.1, 0.9), (8.0, 1.4, 1.2), (9.2, 1.6, 1.45), (10.3, 2.55, 1.95), (11.4, 3.35, 2.3),
            (12.4, 2.75, 2.1), (13.4, 1.75, 1.6), (14.3, 0.85, 1.0)]
    rings = [ellipse(0, v, 3.05, hw, hh, 18) for v, hw, hh in spin] + [[P(0, 14.85, 2.9)]]
    loft_rings(bm, rings, BLUE, cap0=True, cap1=False)
    # A machined neck ring where it leaves the block.
    loft_rings(bm, [ellipse(0, v, 3.0, 1.55, 1.3, 14) for v in (7.35, 7.85)], NOZ)

    # Cross wing along row 16: a thin airfoil spar, tips at columns 1 and 21, under the keel.
    wing = []
    for x in (-10.45, -10.1, -9.0, -7.0, -4.0, 0.0, 4.0, 7.0, 9.0, 10.1, 10.45):
        a = abs(x)
        c = 1.05 if a > 10.3 else (1.5 if a > 9.5 else pchip([0, 4, 7, 9], [2.8, 2.7, 2.5, 2.05])(a))
        t = 0.5 if a > 10.3 else (0.7 if a > 9.5 else pchip([0, 4, 7, 9], [1.2, 1.1, 0.95, 0.8])(a))
        vc = pchip([0, 6, 9, 10.1, 10.5], [16.55, 16.6, 16.9, 16.95, 16.75])(a)
        wing.append(ellipse(x, vc, pchip([0, 10.5], [2.95, 2.75])(a), c / 2, t / 2, 12, along="x"))
    loft_rings(bm, wing, WING)

    # Shield hull: the plate (with the transverse seam at row 21), the keel, the struts and rim.
    vs = [14.7, 15.0, 15.4, 16.0, 16.6, 17.1, 17.6, 18.2, 18.8, 19.4, 20.0, 20.5, 20.9, 21.05, 21.3, 21.45,
          22.0, 22.4, 22.75, 23.2, 24.0, 25.0, 25.8, 26.4, 26.85]
    dips = {21.05: 0.45, 21.3: 0.45}
    loft_rings(bm, [hull_ring(v, dips.get(v, 0.0)) for v in vs], BODY)
    kv = [15.25, 15.5, 15.9, 17.0, 19.0, 20.95, 21.05, 21.3, 21.4, 23.0, 24.5, 25.9, 26.4, 26.75]

    def keel_mat(c):
        return BODY if c.y > (H / 2 - 21.2) * 1 else DARK
    rings = []
    for v in kv:
        hw = 1.5 if v < 26.0 else (1.4 if v < 26.5 else 1.15)
        zt = keel_top(v) - (0.25 if v in (21.05, 21.3) else 0.0)
        rings.append(chamfer_rect(0, v, hw, 1.2, zt, 0.45))
    loft_rings(bm, rings, lambda c: BODY if c.y > H / 2 - 21.2 else DARK)
    for sx in (-1, 1):
        # Blue strut: a chamfered rail riding in the upper hull (rows 16.5-20.6), its ends sloped down.
        st = []
        for v, k in ((16.45, 0.0), (16.85, 1.0), (20.15, 1.0), (20.6, 0.0)):
            z0 = crown(v) - (crown(v) - edge(v)) * (3.9 / hull_w(v)) ** 3 - 0.4
            st.append(chamfer_rect(sx * 3.9, v, 1.1 if k else 0.8, z0, z0 + 0.5 + 0.9 * k, 0.35 if k else 0.15))
        loft_rings(bm, st, BLUE)
        # Raised rim round the hull's edge, row 17.3 to the nose.
        rim = []
        for v in (17.3, 18.0, 19.0, 20.0, 20.7, 22.0, 22.6, 23.2, 24.5, 25.8, 26.45):
            rim.append((sx * (hull_w(v) - 0.7), v, edge(v) + 0.15))
        sweep(bm, rim, 0.55, 0.42, n=8, mat=FIN)



def flames(sprite, coll, both=False):
    """One frame-tagged flame per sprite frame (D17), lofted out of the bell along +Y: the tip reaches
    rows 2, 1 and 0 (51, 89, 127), red outside, a yellow core, a white-hot core on 127. Glows at
    strength 1 (D126/D176), metallic 1 and rough (D173)."""
    def glow(i):
        return common.palette_material(sprite, i, NAME, metallic=1.0, roughness=0.9, emission_strength=1.0)
    mats = [glow(118), glow(119), glow(120), glow(122), glow(124), glow(125), glow(127)]
    R118, R119, R120, Y122, Y124, Y125, W127 = range(7)
    # Per frame: layers of (material, [(row, half width, half height, z)]).
    # The outer red is a flat sheet of flame, the hotter cores stand taller, so from above (as the
    # sprite) the yellow and white cores show down the middle.
    shapes = [
        [(R118, [(4.4, 1.9, 0.9), (3.6, 2.15, 1.0), (3.0, 1.95, 0.95), (2.45, 1.4, 0.75), (1.95, 0.0, 0.0)]),
         (Y122, [(4.4, 1.0, 1.2), (3.4, 1.1, 1.25), (2.8, 0.8, 1.0), (2.4, 0.0, 0.0)])],
        [(R119, [(4.4, 1.9, 0.9), (3.4, 2.2, 1.0), (2.5, 2.15, 0.95), (1.6, 1.5, 0.7), (1.2, 0.9, 0.45),
                 (0.9, 0.0, 0.0)]),
         (Y124, [(4.4, 1.1, 1.25), (3.2, 1.25, 1.3), (2.4, 1.0, 1.1), (1.8, 0.0, 0.0)])],
        [(R120, [(4.4, 1.9, 0.9), (3.4, 2.3, 1.0), (1.6, 2.35, 1.0), (0.9, 1.8, 0.8), (0.45, 1.3, 0.55),
                 (0.02, 0.0, 0.0)]),
         (Y125, [(4.4, 1.4, 1.2), (3.0, 1.6, 1.25), (1.6, 1.3, 1.1), (0.9, 0.8, 0.8), (0.5, 0.0, 0.0)]),
         (W127, [(4.4, 0.8, 1.4), (3.2, 0.85, 1.45), (2.4, 0.6, 1.2), (1.9, 0.0, 0.0)])],
    ]
    out = []
    for frame, layers in zip(FLAMES, shapes):
        bm = bmesh.new()
        for li, (mat, secs) in enumerate(layers):
            for vv in ((lambda v: v), (lambda v: H - v)) if both else ((lambda v: v),):
                rings = [ellipse(0, vv(v), ZN, hw, hh, 14) if hw else [P(0, vv(v), ZN)]
                         for v, hw, hh in secs]
                loft_rings(bm, rings, mat, cap0=True, cap1=False)
        obj = common.mesh_object(f"{NAME}-flame-{frame}", bm, mats, coll, smooth=True)
        out.append(common.frame_part(obj, [frame]))
    return out




def drone_body(bm):
    """newsh7-13's middle: a two-bulb blue spindle on a cross axle, short chevron blades."""
    half = [(7.1, 1.1, 0.9), (8.0, 1.4, 1.2), (9.2, 1.6, 1.45), (10.3, 2.55, 1.95), (11.4, 3.35, 2.3),
            (12.4, 2.2, 1.8), (13.3, 1.35, 1.35), (14.0, 1.2, 1.25)]
    spin = half + [(H - v, hw, hh) for v, hw, hh in reversed(half[:-1])]
    loft_rings(bm, [ellipse(0, v, 3.05, hw, hh, 18) for v, hw, hh in spin], BLUE, cap0=True, cap1=True)
    # machined neck rings where it leaves each block
    for v0 in (7.35, H - 7.85):
        loft_rings(bm, [ellipse(0, v, 3.0, 1.55, 1.3, 14) for v in (v0, v0 + 0.5)], NOZ)
    # The cross axle through the waist (rows 13-15): a grey bar either side, with a hub collar.
    for sx in (-1, 1):
        sweep(bm, [(sx * 1.0, 14.0, 2.6), (sx * 3.0, 14.0, 2.6), (sx * 6.3, 14.0, 2.6)], [1.0, 0.9, 0.9],
              [0.9, 0.8, 0.8], n=12, mat=BAR)
        # the short blue chevron blade: out of the cage bar at the ferrule, in to the axle, and back
        pts = [(-8.85, 8.9, 2.75), (-8.55, 10.4, 2.7), (-7.7, 12.0, 2.65), (-6.7, 13.2, 2.6), (-6.4, 14.0, 2.6),
               (-6.7, 14.8, 2.6), (-7.7, 16.0, 2.65), (-8.55, 17.6, 2.7), (-8.85, 19.1, 2.75)]
        pts = [(x if sx < 0 else -x, v, z) for x, v, z in pts]
        w = [0.6, 0.85, 1.1, 1.0, 0.9, 1.0, 1.1, 0.85, 0.6]
        sweep(bm, pts, w, [0.55] * 9, n=10, mat=BLADE)
    # the bottom engine block, fins, bell and cage bars: the upper one mirrored about the middle
    lower_engine(bm)


def lower_engine(bm):
    """The engine block, fins and bell of the bottom end: engine() built on the mirrored rows."""
    global FLIP
    saved = FLIP
    FLIP = not saved
    try:
        engine(bm, None)
    finally:
        FLIP = saved


def finish(name, body_fn, flip, dc, flames_frames, both=False, tag="gunship"):
    """Build the whole model: the body, the shell and the frame-tagged flames. Returns
    (collection, [objects], body)."""
    global NAME, FLIP, DC, FLAMES
    NAME, FLIP, DC, FLAMES = name, flip, dc, tuple(flames_frames)
    coll = common.reset_collection(name)
    mats = make_mats(SPRITE)
    bm = bmesh.new()
    engine(bm, GUN_BLADE if body_fn is gunship_body else None)
    body_fn(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = common.mesh_object(name, bm, mats, coll, smooth=True)
    es = body.modifiers.new("hard", "EDGE_SPLIT")  # chamfered blocks stay crisp, round parts smooth
    es.split_angle = math.radians(42)
    fl = flames(SPRITE, coll, both=both)
    # D90/D118: the shell from a sealed copy of the body (nothing is culled)
    sealed = body.copy()
    sealed.data = body.data.copy()
    for m in list(sealed.modifiers):
        sealed.modifiers.remove(m)
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=3000, inside=0.004)
    shell.name = f"{name}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    bb = [body.matrix_world @ Vector(c) for c in body.bound_box]
    sb = [shell.matrix_world @ Vector(c) for c in shell.bound_box]
    lo = [round(min(p[i] for p in sb) - min(p[i] for p in bb), 3) for i in range(2)]
    hi = [round(max(p[i] for p in sb) - max(p[i] for p in bb), 3) for i in range(2)]
    assert len(shell.data.polygons) > 100 and max(map(abs, lo + hi)) < 0.06, ("shell lost a part", lo, hi)
    print(f"{name}: shell faces {len(shell.data.polygons)}, bbox slack {lo} {hi}")
    return coll, [body, shell] + fl


SPRITE = None


def build_gunship(sprite, name, flip=False, dc=0, flames=(51, 89, 127)):
    """newsh7-51 (flip=False) or newsh7-237 (flip=True, dc=1). Returns the objects to export."""
    global SPRITE
    SPRITE = sprite
    return finish(name, gunship_body, flip, dc, flames)[1]


def build_drone(sprite, name, flames=(13, 15, 17)):
    """newsh7-13: the engine at both ends, the spindle between."""
    global SPRITE
    SPRITE = sprite
    return finish(name, drone_body, False, 0, flames, both=True)[1]
