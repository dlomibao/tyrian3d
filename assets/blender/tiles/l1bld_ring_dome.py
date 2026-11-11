r"""l1bld-ring-dome: ASTEROID?'s ring dome (map 1-3 rows 154-160, 7 x 10 tiles), hard
surface on lib_l1kit (the base complex's station kit, D141), silhouette first.

What it is (the tiles and the game): a paved U of station deck in a rocky rim. Its top bar carries a
light band: two framed big red panes (347), two racks of three red capsule lights (339) and two
brass gun turrets (358) in the middle, each a round brass cage with steel windows, red side lamps
and a short barrel pointing down the screen at the player. Each arm carries two orb sockets (357):
a dark well ringed by bright lugs, a dark sensor dome with two red eyes. Inside the U a separate
paved pad carries the big low dome (415 417 / 409 383): its plating is the deck's basket weave
carried over the dome (the art paints the weave over it, lit top-left, shadowed bottom-right).

Read from the tilted game camera: the dome is the only thing that stands up (top 0.72, everything
else under the rim's 0.50), so it is a clear ellipsoid with a collar, its plates modelled as
inlaid strips alternating along / across like the weave; the band reads as one bright red row with
two brass knobs; the orbs as four eyes in bezels on the arms.

Ground enemies stand at 0.45 on the six band cells and the four orb cells: every top there stays
<= 0.376. D139: each band cell's light ("open": lights + the paving round them) and its lid
("covered": the plain basket-weave paving, flush with the deck round it) are their own objects,
tagged tyrian_cell [1, col] / tyrian_when; bake_model keeps them separate and tagged.

Dome plating: the art's basket weave (lib_l1kit.WEAVE bricks) draped over the ellipsoid, plain
mortar showing between the plates.

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/l1bld_ring_dome.py
    blender --background --factory-startup --python assets/blender/tiles/l1bld_ring_dome.py -- [--no-bake] [--preview <dir>]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_l1kit as kit  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
from lib_l1kit import DECK_TOP, ell, rbox  # noqa: E402

PX = lt.PX
TW, TH = lt.TILE_W, lt.TILE_H

BAND_ROW, BAND_COLS = 1, [2, 3, 4, 5, 6, 7]
TURRET_COLS = (4, 5)
TURRET_R = (9.0, 10.0)  # brass cage radii (px) round the cell's brass centroid
TOP_E = 0.376  # highest top on an enemy cell
DOME_C, DOME_R = (120.0, 140.0), 21.0
DOME_Z0, DOME_H = 0.34, 0.415  # ellipsoid from its collar to 0.755 (+ boss 0.775)

# The art's palette indices (trimmed medians of each region's pixels; measure() prints them).
PAL_BRASS, PAL_WINDOW, PAL_LAMP = 164, 101, 115
PAL_ORB_BEZEL, PAL_ORB_WELL, PAL_ORB_LUG, PAL_ORB_EYE = 5, 1, 9, 112
PAL_DOME, PAL_DOME_SEAM, PAL_COLLAR = 5, 3, 5


# ---------------------------------------------------------------- small local helpers (follow-ups)

def face_out(bm, vs, mat, out_vec, smooth=False):
    """A face whose normal points along out_vec (world)."""
    if len(set(vs)) < 3:
        return None
    try:
        f = bm.faces.new(vs)
    except ValueError:
        return None
    f.normal_update()
    if f.normal.dot(Vector(out_vec)) < 0:
        f.normal_flip()
    f.material_index = mat
    f.smooth = smooth
    return f


def lens_unit(k, x0, y0, x1, y1, corner, fat=False, ztop=kit.LENS_TOP, mat=None, house_pad=(1.2, 2.2)):
    """lib_l1kit.Kit.lens with the lens corner as a parameter (a stadium for the 339 capsules:
    corner = half the width), housing, dark seat and domed lens."""
    g, m = k.g, k.mat
    a, b_ = house_pad
    g.prism(rbox(x0 - a, y0 - a, x1 + b_, y1 + b_, corner + 1.2, 3), [], DECK_TOP - 0.005, ztop, m["house"],
            chamfer=0.7, drop=0.012, bottom=False)
    g.prism(rbox(x0 - 0.4, y0 - 0.4, x1 + 1.4, y1 + 1.4, corner + 0.4, 3), [], ztop - 0.02, ztop + 0.002, m["sock"], bottom=False)
    k.pillow(rbox(x0, y0, x1 + 1, y1 + 1, corner, 3), ztop - 0.004, 0.024 if fat else 0.022,
             mat if mat is not None else (m["lens_fat"] if fat else m["lens"]), corner)


def flat_cyl_y(g, cx, y0, y1, rx, rz, zc, mat, n=12, cap0=None, cap1=None):
    """A squashed pipe along the screen's y (rx in px, rz in units), its ends capped (cap1: the far
    end's own material, e.g. a red bore)."""
    bm = g.bm
    ring = lambda y: [g.v(cx + rx * math.cos(2 * math.pi * i / n), y, zc + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]
    a, b_ = ring(y0), ring(y1)
    for i in range(n):
        j = (i + 1) % n
        ca = math.cos(2 * math.pi * (i + 0.5) / n)
        sa = math.sin(2 * math.pi * (i + 0.5) / n)
        face_out(bm, (a[i], a[j], b_[j], b_[i]), mat, (ca, 0, sa), smooth=True)
    face_out(bm, a, mat if cap0 is None else cap0, (0, 1 if y0 < y1 else -1, 0))
    face_out(bm, b_, mat if cap1 is None else cap1, (0, -1 if y0 < y1 else 1, 0))


def dome_z(cx, cy, rx, ry, z0, h, x, y):
    t = 1 - ((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2
    return z0 + h * math.sqrt(max(0.0, t))


def conform_patch(g, poly, f, lift, mat):
    """A flat-shaded ngon over `poly` (pattern px), each corner lifted `lift` over the surface f(x, y)."""
    vs = [g.v(x, y, f(x, y) + lift) for x, y in g.outer(poly)]
    face_out(g.bm, vs, mat, (0, 0, 1))


def comps(mask, min_px=1):
    lab, n = ls.label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) >= min_px:
            out.append((xs.min(), ys.min(), xs.max(), ys.max(), xs.mean() + 0.5, ys.mean() + 0.5, len(ys)))
    return out


def trimmed_median(grid, mask, ts):
    """The region's palette index: median by luminance with the darkest / brightest eighth left
    out (lighting), as the rubric's 'reading a sprite'."""
    v = grid[mask & (grid >= 0)]
    if not len(v):
        return None
    lum = np.array([sum(c * w for c, w in zip(ts.rgb(int(i)), (0.299, 0.587, 0.114))) for i in v])
    o = np.argsort(lum)
    n = len(o)
    keep = v[o[n // 8: n - n // 8]] if n >= 8 else v[o]
    return int(keep[len(keep) // 2])


def clip_convex(poly, clip):
    """Sutherland-Hodgman: `poly` clipped by the convex CCW (in px, y down: any consistent) `clip`."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def inter(p, q, a, b):
        x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    out = list(poly)
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        inp, out = out, []
        if not inp:
            break
        for j in range(len(inp)):
            p, q = inp[j - 1], inp[j]
            if inside(q, a, b):
                if not inside(p, a, b):
                    out.append(inter(p, q, a, b))
                out.append(q)
            elif inside(p, a, b):
                out.append(inter(p, q, a, b))
    return out


# ---------------------------------------------------------------- the parts

def turret(k, cx, cy, grid, b):
    """358: dark seat, brass cage dome with steel windows (the art's blue-steel pixels), red side
    lamps, a short barrel down the screen with a red bore. Top 0.376."""
    g, M = k.g, b.m
    brass = M(PAL_BRASS, roughness=0.38, metallic=0.75)
    brass_dk = M(PAL_BRASS - 2, roughness=0.45, metallic=0.65)
    steel = M(PAL_WINDOW, roughness=0.25, metallic=0.6)
    lamp = M(PAL_LAMP, roughness=0.25, emission_strength=1.2)
    seat = M(1, roughness=0.6, metallic=0.3)
    rx, ry = TURRET_R
    g.prism(ell(cx, cy, rx + 1.6, ry + 1.2, 28), [], DECK_TOP - 0.005, 0.318, seat, chamfer=0.6, drop=0.008, bottom=False)
    z0, h = 0.312, TOP_E - 0.004 - 0.312
    g.dome(cx, cy, rx, ry, z0, h, brass, n=24, rings=6)
    # windows: the art's blue-steel pixels inside the cage, as inset panes on the dome
    yy0, xx0 = int(cy - ry), int(cx - rx)
    wm = np.zeros(grid.shape, bool)
    sub = grid[yy0:int(cy + ry) + 1, xx0:int(cx + rx) + 1]
    wm[yy0:int(cy + ry) + 1, xx0:int(cx + rx) + 1] = (sub >= 96) & (sub <= 111)
    yy, xx = np.mgrid[0:grid.shape[0], 0:grid.shape[1]] + 0.5
    wm &= ((xx - cx) / (rx - 0.8)) ** 2 + ((yy - cy) / (ry - 0.8)) ** 2 <= 1
    f = lambda x, y: dome_z(cx, cy, rx, ry, z0, h, x, y)
    nwin = 0
    for x0, y0, x1, y1, mx, my, n in comps(wm, 2):
        conform_patch(g, rbox(x0 + 0.15, y0 + 0.15, x1 + 0.85, y1 + 0.85, 0.6, 1), f, 0.003, steel)
        nwin += 1
    # cage ribs: a brass ring round the crown and four meridian ribs (the cage the windows sit in)
    for a0 in (0.25, 0.75, 1.25, 1.75):
        a = a0 * math.pi
        pts = []
        for t in np.linspace(0.18, 0.92, 5):
            pts.append((cx + rx * t * math.cos(a), cy + ry * t * math.sin(a)))
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            nx, ny = -(yb - ya), xb - xa
            L = math.hypot(nx, ny)
            nx, ny = 0.55 * nx / L, 0.55 * ny / L
            conform_patch(g, [(xa + nx, ya + ny), (xb + nx, yb + ny), (xb - nx, yb - ny), (xa - nx, ya - ny)], f, 0.0035, brass_dk)
    # side lamps (the art's red at the cage's flanks)
    for sx in (-1, 1):
        lx = cx + sx * (rx + 0.6)
        g.prism(rbox(lx - 1.3, cy - 3.6, lx + 1.3, cy + 3.6, 1.2, 2), [], DECK_TOP, 0.34, brass_dk, chamfer=0.4, drop=0.008, bottom=False)
        g.dome(lx, cy, 1.1, 3.0, 0.338, 0.026, lamp, n=10, rings=2)
    # barrel: from the cage's front down the screen, a red bore at its muzzle
    bore = M(113, roughness=0.3, emission_strength=1.5)
    my = cy + ry + 3.0  # the muzzle seen from above: a brass ring round a red bore (art y 48-54)
    flat_cyl_y(g, cx, cy + ry - 3.5, my, 2.6, 0.028, 0.336, brass, n=14)
    g.prism(ell(cx, my, 3.6, 3.2, 18), [ell(cx, my, 1.7, 1.4, 12)], DECK_TOP - 0.005, 0.372, brass, chamfer=0.6, drop=0.012, bottom=False)
    g.prism(ell(cx, my, 1.75, 1.45, 12), [], DECK_TOP - 0.005, 0.345, bore, bottom=False)
    return nwin


def orb_socket(k, cx, cy, lugs, eyes, b):
    """357: a dark bezel ring with bright lugs (the art's bright knobs), a dark well, a dark sensor
    dome with two red eyes. Top <= 0.376 (an enemy cell)."""
    g, M = k.g, b.m
    bezel = M(PAL_ORB_BEZEL, roughness=0.5, metallic=0.45)
    well = M(PAL_ORB_WELL, roughness=0.8)
    lug = M(PAL_ORB_LUG, roughness=0.35, metallic=0.6)
    sens = M(3, roughness=0.3, metallic=0.55)
    eye = M(PAL_ORB_EYE, roughness=0.25, emission_strength=2.2)
    g.prism(ell(cx, cy, 11.0, 11.0, 32), [ell(cx, cy, 7.0, 7.0, 32)], DECK_TOP - 0.005, 0.338, bezel, chamfer=0.9, drop=0.014, bottom=False)
    g.prism(ell(cx, cy, 7.05, 7.05, 32), [], DECK_TOP - 0.005, 0.306, well, bottom=False)
    for lx, ly in lugs:
        a = math.atan2(ly - cy, lx - cx)
        r = min(9.0, max(8.0, math.hypot(lx - cx, ly - cy)))
        px_, py_ = cx + r * math.cos(a), cy + r * math.sin(a)
        ca, sa = math.cos(a), math.sin(a)
        hw, hl = 1.5, 2.0
        poly = [(px_ + ca * u * hl - sa * v * hw, py_ + sa * u * hl + ca * v * hw) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        g.prism(poly, [], 0.33, 0.362, lug, chamfer=0.4, drop=0.01, bottom=False)
    ry = 6.2
    z0, h = 0.305, 0.058
    g.dome(cx, cy, 5.2, ry, z0, h, sens, n=18, rings=4)
    f = lambda x, y: dome_z(cx, cy, 5.2, ry, z0, h, x, y)
    for ex, ey in eyes:
        conform_patch(g, ell(ex, ey, 2.1, 2.0, 12), f, 0.004, eye)


def big_dome(k, b):
    """415 417 / 409 383: a collar ring, an ellipsoid shell in the seam colour, its plating as inlaid
    strips (lifted, with sides) alternating along / across per panel, like the deck's weave; a boss."""
    g, M = k.g, b.m
    bm = g.bm
    cx, cy = DOME_C
    collar = M(PAL_COLLAR, roughness=0.4, metallic=0.55)
    seam = M(PAL_DOME_SEAM, roughness=0.6, metallic=0.35)
    plate = M(PAL_DOME, roughness=0.42, metallic=0.5)
    R = DOME_R
    g.prism(ell(cx, cy, R + 2.4, R + 2.4, 48), [ell(cx, cy, R - 0.4, R - 0.4, 48)], DECK_TOP - 0.005, 0.362, collar,
            chamfer=1.0, drop=0.02, bottom=False)
    for k_ in range(16):  # collar bolts
        a = 2 * math.pi * (k_ + 0.5) / 16
        g.prism(ell(cx + (R + 1.0) * math.cos(a), cy + (R + 1.0) * math.sin(a), 0.7, 0.7, 6), [], 0.35, 0.372, collar, bottom=False)
    X0, Y0 = g.s.x(cx), g.s.y(cy)
    Rw = R * PX

    def P(phi, th, lift=0.0):
        c, s = math.cos(phi), math.sin(phi)
        p = Vector((Rw * c * math.cos(th), Rw * c * math.sin(th), DOME_H * s))
        n = Vector((c * math.cos(th) / Rw, c * math.sin(th) / Rw, s / DOME_H)).normalized()
        q = p + n * lift
        return Vector((X0 + q.x, Y0 + q.y, DOME_Z0 + q.z)), n

    # the shell
    NPH, NTH = 14, 48
    phis = [0.5 * math.pi * i / NPH for i in range(NPH)]
    rings = [[bm.verts.new(P(ph, 2 * math.pi * j / NTH)[0]) for j in range(NTH)] for ph in phis]
    top = bm.verts.new((X0, Y0, DOME_Z0 + DOME_H))
    for lo, hi, ph in zip(rings, rings[1:], phis):
        for j in range(NTH):
            jj = (j + 1) % NTH
            face_out(bm, (lo[j], lo[jj], hi[jj], hi[j]), seam, P(ph, 2 * math.pi * (j + 0.5) / NTH)[1], smooth=True)
    for j in range(NTH):
        face_out(bm, (rings[-1][j], rings[-1][(j + 1) % NTH], top), seam, (0, 0, 1), smooth=True)

    # plating: the deck's basket weave (WEAVE bricks) draped over the ellipsoid, ~2 px strips
    clip = ell(cx, cy, R - 1.0, R - 1.0, 40)
    if ls.area(clip) < 0:
        clip = clip[::-1]

    def zf(x, y):
        t_ = 1 - ((x - cx) / R) ** 2 - ((y - cy) / R) ** 2
        return DOME_Z0 + DOME_H * math.sqrt(max(0.0, t_))

    nstrip = 0
    for r_ in range(int((cy - R) // TH), int((cy + R) // TH) + 1):
        for c_ in range(int((cx - R) // TW), int((cx + R) // TW) + 1):
            for bx0, by0, bx1, by1 in kit.WEAVE:
                X0, Y0, X1, Y1 = c_ * TW + bx0 + 0.3, r_ * TH + by0 + 0.3, c_ * TW + bx1 - 0.3, r_ * TH + by1 - 0.3
                horiz = (X1 - X0) > (Y1 - Y0)
                L = (X1 - X0) if horiz else (Y1 - Y0)
                n = max(1, int(round(L / 2.0)))
                cuts = [((X0 + (X1 - X0) * i / n) if horiz else (Y0 + (Y1 - Y0) * i / n)) for i in range(n + 1)]
                for i in range(n):
                    rect = ([(cuts[i], Y0), (cuts[i + 1], Y0), (cuts[i + 1], Y1), (cuts[i], Y1)] if horiz
                            else [(X0, cuts[i]), (X1, cuts[i]), (X1, cuts[i + 1]), (X0, cuts[i + 1])])
                    if ls.area(rect) < 0:
                        rect = rect[::-1]
                    pc = clip_convex(rect, clip)
                    pc = kit.Geo.clean(pc)
                    if len(pc) < 3 or abs(ls.area(pc)) < 0.15:
                        continue
                    pc = kit.Geo.outer(pc)
                    tv = [g.v(px, py, zf(px, py) + 0.011) for px, py in pc]
                    bv = [g.v(px, py, zf(px, py) - 0.004) for px, py in pc]
                    g.face(tv, plate, smooth=False)
                    npc = len(pc)
                    for e in range(npc):
                        f = (e + 1) % npc
                        p, q = pc[e], pc[f]
                        if any(abs(p[0 if horiz else 1] - c) < 1e-6 and abs(q[0 if horiz else 1] - c) < 1e-6 for c in cuts[1:-1]):
                            continue
                        g.face((bv[e], bv[f], tv[f], tv[e]), plate)
                    nstrip += 1
    # the boss on the crown
    zc = DOME_Z0 + DOME_H
    boss = M(8, roughness=0.4, metallic=0.55)
    g.prism(ell(cx, cy, 4.2, 4.2, 18), [], zc - 0.04, zc + 0.006, boss, chamfer=0.8, drop=0.012, bottom=False)
    g.dome(cx, cy, 2.4, 2.4, zc + 0.004, 0.014, boss, n=12, rings=2)
    return nstrip


# ---------------------------------------------------------------- build

def measure(b, red):
    """Feature positions read off the tiles (pattern px) and the regions' palette indices."""
    grid = b.grid
    H, W = grid.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    ts = b.ts
    feats = {"lights": {}, "turrets": {}, "orbs": []}
    for c in BAND_COLS:
        x0, y0, x1, y1 = b.cell_box(BAND_ROW, c)
        cell = np.zeros((H, W), bool)
        cell[y0:y1, x0:x1] = True
        if c in TURRET_COLS:
            brass = cell & (grid >= 160) & (grid <= 175)
            ys, xs = np.nonzero(brass & (yy < y0 + 21))
            feats["turrets"][c] = (float(xs.mean() + 0.5), float(y0 + 10.0))
        else:
            rr = cell & ((grid >> 4) == 7)
            feats["lights"][c] = [cc for cc in comps(rr, 20)]
    for r, cc in b.tiles_at(357):
        x0, y0, x1, y1 = b.cell_box(r, cc)
        cell = np.zeros((H, W), bool)
        cell[y0:y1, x0:x1] = True
        e = comps(cell & ((grid >> 4) == 7), 3)
        ex = float(np.mean([t[4] for t in e]))
        eys = sorted(t[5] for t in e)
        cy = (eys[0] + eys[-1]) / 2
        bright = cell & (grid >= 9) & (grid < 16) & ((xx - ex) ** 2 + (yy - cy) ** 2 <= 11.5 ** 2) & ((xx - ex) ** 2 + (yy - cy) ** 2 >= 5 ** 2)
        lugs = [(t[4], t[5]) for t in comps(bright, 2)]
        feats["orbs"].append(((ex, cy), lugs, [(t[4], t[5]) for t in e]))
    # palette per region
    tm = lambda m: trimmed_median(grid, m, ts)
    reg = {}
    tur = np.zeros((H, W), bool)
    for c, (tx, ty) in feats["turrets"].items():
        tur |= ((xx - tx) / TURRET_R[0]) ** 2 + ((yy - ty) / TURRET_R[1]) ** 2 <= 1
    reg["turret brass"] = tm(tur & (grid >= 160) & (grid <= 175))
    reg["turret windows"] = tm(tur & (grid >= 96) & (grid <= 111))
    reg["turret lamps"] = tm(kit.dil4(tur, 3) & ~tur & ((grid >> 4) == 7))
    orbw = np.zeros((H, W), bool)
    orbr = np.zeros((H, W), bool)
    for (ox, oy), _, _ in feats["orbs"]:
        d2 = (xx - ox) ** 2 + (yy - oy) ** 2
        orbw |= d2 <= 6.5 ** 2
        orbr |= (d2 > 6.5 ** 2) & (d2 <= 11 ** 2)
    reg["orb well"] = tm(orbw & ((grid >> 4) == 0))
    reg["orb bezel ring"] = tm(orbr)
    reg["orb eyes"] = tm(orbw & ((grid >> 4) == 7))
    dome = (xx - DOME_C[0]) ** 2 + (yy - DOME_C[1]) ** 2 <= DOME_R ** 2
    reg["dome"] = tm(dome)
    l347 = np.zeros((H, W), bool)
    l339 = np.zeros((H, W), bool)
    for c, cl in feats["lights"].items():
        for x0, y0, x1, y1, *_ in cl:
            (l347 if len(cl) == 1 else l339)[y0:y1 + 1, x0:x1 + 1] = True
    reg["347 panes"] = tm(l347 & ((grid >> 4) == 7))
    reg["339 capsules"] = tm(l339 & ((grid >> 4) == 7))
    print("regions (art trimmed median):", reg)
    return feats, reg


def build(bake=True, preview=None):
    lb.clear_scene()
    b = lb.Building("ring-dome")
    k = kit.Kit(b)
    fp = b.footprint
    H, W = b.H, b.W
    red = b.masks()["red"]
    feats, reg = measure(b, red)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5

    k.bed(fp)
    dm = k.deck_mask(fp)
    k.deck(dm)

    # parts (px) the rocks / kerb / paving keep off
    band = kit.box_mask((H, W), BAND_COLS[0] * TW, BAND_ROW * TH, (BAND_COLS[-1] + 1) * TW, (BAND_ROW + 1) * TH)
    orbs = np.zeros((H, W), bool)
    for (ox, oy), _, _ in feats["orbs"]:
        orbs |= (xx - ox) ** 2 + (yy - oy) ** 2 <= 12 ** 2
    dome = (xx - DOME_C[0]) ** 2 + (yy - DOME_C[1]) ** 2 <= (DOME_R + 3.0) ** 2
    parts = orbs | dome
    k.rock_layout(fp, dm, exclude=kit.dil4(parts | band, 2))
    k.kerb(dm, no_post=kit.dil4(parts, 2) | band)
    k.channels(fp)
    zone = kit.ero_disk(dm, kit.KERB_W)
    k.paving(zone & ~parts & ~band)
    k.rocks()

    # orb sockets (base model)
    for (ox, oy), lugs, eyes in feats["orbs"]:
        orb_socket(k, ox, oy, lugs, eyes, b)
    nstrip = big_dome(k, b)

    k.no_needles()
    objects = k.objects()
    coll = objects[0].users_collection[0]

    # D139: per band cell, the light ("open": its lights and the weave round them) and the lid
    # ("covered": the weave over the whole cell), each its own Geo / object.
    base_g = k.g
    cover = []
    nwin = 0
    for c in BAND_COLS:
        x0, y0, x1, y1 = b.cell_box(BAND_ROW, c)
        cell = kit.box_mask((H, W), x0, y0, x1, y1)
        czone = zone & cell
        light_px = np.zeros((H, W), bool)
        geo_open = kit.Geo(b)
        k.g = geo_open
        if c in TURRET_COLS:
            tx, ty = feats["turrets"][c]
            nwin += turret(k, tx, ty, b.grid, b)
            light_px |= ((xx - tx) / (TURRET_R[0] + 3.5)) ** 2 + ((yy - ty) / (TURRET_R[1] + 2.5)) ** 2 <= 1
            light_px |= kit.box_mask((H, W), tx - 4.5, ty, tx + 4.5, ty + TURRET_R[1] + 8)
        else:
            cl = feats["lights"][c]
            fat = len(cl) == 1
            for lx0, ly0, lx1, ly1, *_ in cl:
                if fat:
                    lens_unit(k, lx0, ly0, lx1, ly1, 3.0, fat=True)
                else:
                    lens_unit(k, lx0, ly0, lx1, ly1, (lx1 - lx0 + 1) / 2 - 0.15, house_pad=(0.9, 1.9))
                light_px |= kit.box_mask((H, W), lx0 - 2.5, ly0 - 2.5, lx1 + 4, ly1 + 4)
        k.paving(czone & ~light_px)
        geo_cov = kit.Geo(b)
        k.g = geo_cov
        k.paving(czone)
        for when, geo in (("open", geo_open), ("covered", geo_cov)):
            o = lb.mesh_object(f"{lb.SHAPES}-{b.prefix}-{b.name}-cell-{BAND_ROW}-{c}-{when}", geo.bm, b.pal.materials, coll)
            o["tyrian_cell"] = [BAND_ROW, c]
            o["tyrian_when"] = when
            cover.append(o)
    k.g = base_g
    objects += cover

    b.finish(objects, fp, bake=bake, preview=preview)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
