"""Clamped red core (newsh5.shp frame 166), a 3D version of its sprite.

Seen in episode 4 (BRAINIAC, 4.15, main=22): unit e4:521, terrain-fixed on the top layer, spawned
in rows 24 px apart, so the blocks tile into a horizontal band. The sprite fills the top half of
its 24x28 block (rows 0-14).

What it is, built as such: a lump of glowing red bio-mass (dark red, palette 113 at the median of all its red pixels)
held in a clamp rack. Each block's ends are HALF a clamp yoke: a machined grey block (pal 104)
over rows 1-5 with a jaw leg running down the mass's side (column 2 / column 21, rows 6-8). Two
neighbouring blocks' halves meet flat at the block edge and read as one yoke straddling the join,
gripping both masses. A grey spindle (pal 105) runs along row 5 out of each yoke into the mass;
where it crosses the mass's middle (columns 10-14) it is a glowing heater sleeve (pal 120, the
sprite's hot bar) lying in a groove between the lobes. A branch pipe tees off the spindle at
column 6 and loops up over the upper-left lobe to row 2 (the sprite's grey L); a second pipe
leaves the right jaw along row 7, drops down column 16 and runs along row 9 into a dark grey
clamp shoe (pal 101) that grips the mass's lower lip (columns 10-13, rows 9-14). The orange-white
spot on the left lobe (5,7) is a glowing vent (pal 123) in a small crater, its rim lit (pal 116).
The mass's bright and dark pixels elsewhere are lighting: one dark red, lumpy, lit by the game.
Glows are metallic 1 / rough (D126, D173). Underside: a flat closed base.

    blender --background --python assets/blender/enemies/newsh5-166.py [-- --preview out.png]

Exports public/models/enemies/newsh5-166.glb (mesh + outline shell, pal_<index> materials).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402  (read-only use)

NAME = "newsh5-166"
P = 1 / 12  # one sprite pixel


def U(x):
    """Sprite x (pixel-edge coordinate, 0..24) to units."""
    return (x - 12.0) * P


def V(y):
    """Sprite y (pixel-edge coordinate, 0..28, down) to units."""
    return (14.0 - y) * P


ZB = -2.2  # base of everything (px)


# --- The mass: a heightfield over a smoothed outline ------------------------------------------

def chaikin(pts, n=3):
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        pts = out
    return pts


# Clockwise on screen (y down) = counter-clockwise in model space.
MASS_POLY = [(2.9, 1.9), (8.7, 1.9), (9.0, 0.75), (13.1, 0.75), (13.4, 1.9), (21.1, 1.9),
             (21.15, 11.4), (20.85, 12.6), (19.9, 13.15), (14.0, 13.15), (9.0, 13.15), (4.1, 13.15),
             (3.15, 12.6), (2.85, 11.4)]
C = (12.0, 7.4)


def resample(pts, n):
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    lens = [math.dist(a, b) for a, b in segs]
    tot = sum(lens)
    out, acc, k = [], 0.0, 0
    for i in range(n):
        t = tot * i / n
        while acc + lens[k] < t:
            acc += lens[k]
            k += 1
        a, b = segs[k]
        f = (t - acc) / lens[k]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


OUTLINE = None


def edge_dist(x, y):
    best = 1e9
    n = len(OUTLINE)
    for i in range(n):
        ax, ay = OUTLINE[i]
        bx, by = OUTLINE[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def g2(x, y, cx, cy, sx, sy):
    return math.exp(-((x - cx) / sx) ** 2 - ((y - cy) / sy) ** 2)


LUMPS = [  # x, y, sx, sy, amplitude (px)
    (11.1, 2.9, 2.0, 2.3, 2.6),   # top-centre lobe (pokes up to row 1)
    (5.0, 3.1, 1.8, 1.7, 1.7),    # upper-left lobe, under the branch pipe
    (16.6, 3.0, 3.0, 1.6, 1.9),   # upper-right lobe
    (5.9, 9.4, 2.6, 2.7, 2.4),    # left lobe (the vent)
    (12.4, 7.4, 2.5, 1.2, 1.3),   # middle lobe under the heater sleeve
    (17.9, 10.6, 2.6, 2.2, 2.3),  # right lower lobe
    (9.0, 11.2, 1.2, 1.6, 0.9),   # small nodule left of the shoe
    (14.6, 11.9, 1.4, 1.1, 0.7),  # small nodule right of the shoe
    (19.8, 7.6, 1.0, 1.4, 0.6),
    (8.0, 6.5, 1.2, 1.0, 0.9),    # bulge over the spindle, left of the sleeve
    (15.4, 5.6, 0.9, 1.1, 0.9),   # bulge over the spindle, right of the sleeve
    # smaller nodules: the lumpy surface
    (4.4, 11.6, 0.9, 0.8, 0.6), (7.4, 8.4, 0.8, 0.9, 0.5), (6.8, 11.3, 1.0, 0.9, 0.55),
    (4.2, 6.6, 0.7, 0.8, 0.45), (10.4, 1.6, 0.6, 0.7, 0.4), (12.0, 4.2, 0.8, 0.8, 0.5),
    (15.2, 2.6, 0.9, 0.8, 0.6), (18.6, 3.4, 1.0, 0.9, 0.6), (19.8, 2.8, 0.7, 0.7, 0.4),
    (16.0, 10.4, 0.9, 1.0, 0.55), (19.4, 11.8, 0.8, 0.7, 0.45), (18.4, 8.6, 0.8, 0.8, 0.5),
    (11.2, 7.9, 0.7, 0.6, 0.35), (14.2, 7.6, 0.7, 0.6, 0.35), (5.2, 4.4, 0.7, 0.6, 0.4),
]
CREASES = [  # polyline, depth, half width (px): the dark creases between lobes
    ([(9.0, 0.8), (8.9, 4.0)], 0.7, 0.45),
    ([(13.3, 1.0), (13.6, 4.2)], 0.6, 0.45),
    ([(9.4, 8.6), (15.2, 8.7)], 0.5, 0.5),
    ([(9.1, 9.0), (9.3, 13.0)], 0.5, 0.45),
    ([(7.6, 3.2), (8.2, 4.4)], 0.8, 0.6),   # the dark pit inside the pipe loop
    ([(3.4, 8.4), (5.6, 6.0)], 0.45, 0.4),
    ([(17.0, 4.6), (20.4, 5.0)], 0.4, 0.45),
    ([(15.6, 9.0), (16.4, 12.6)], 0.4, 0.4),
    ([(4.0, 10.4), (8.4, 10.0)], 0.35, 0.4),
]
VENT = (5.45, 7.55)
SLEEVE_Y, SLEEVE_X0, SLEEVE_X1 = 5.5, 9.7, 14.8
SPINDLE_Z = 2.6  # spindle centre height (px)


def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def mass_z(x, y, d=None):
    """Top of the mass (px) at sprite (x, y)."""
    if d is None:
        d = edge_dist(x, y)
    re = 2.0
    dd = min(d, re)
    base = 1.0 * math.sqrt(max(0.0, 1 - (1 - dd / re) ** 2))  # rounded edge to 1 px
    inner = min(1.0, d / 2.6)
    inner = inner * inner * (3 - 2 * inner)
    h = 1.3
    for cx, cy, sx, sy, a in LUMPS:
        h += a * g2(x, y, cx, cy, sx, sy)
    for pl, dep, w in CREASES:
        dist = min(seg_dist(x, y, pl[i], pl[i + 1]) for i in range(len(pl) - 1))
        h -= dep * math.exp(-(dist / w) ** 2)
    # groove for the heater sleeve along row 5
    wx = 1 / (1 + math.exp(-(x - (SLEEVE_X0 - 0.2)) / 0.35)) * 1 / (1 + math.exp((x - (SLEEVE_X1 + 0.2)) / 0.35))
    gz = SPINDLE_Z + 0.25
    groove = math.exp(-((y - SLEEVE_Y) / 1.1) ** 2) * wx
    h = h * (1 - groove) + min(h, gz) * groove
    # vent crater
    r = math.hypot(x - VENT[0], y - VENT[1])
    h -= 0.5 * math.exp(-(r / 0.95) ** 2)
    h += 0.35 * math.exp(-((r - 1.25) / 0.45) ** 2)
    return base + inner * h


def build_mass(bm, mats_idx):
    global OUTLINE
    MASS, EMBER = mats_idx
    OUTLINE = resample(chaikin(MASS_POLY, 3), 88)
    n = len(OUTLINE)
    # top rings: s from 1 (edge) to 0 (centre), dense near the edge
    ss = [1.0, 0.985, 0.965, 0.94, 0.91, 0.87, 0.82, 0.76, 0.70, 0.63, 0.56, 0.49, 0.42, 0.35,
          0.28, 0.21, 0.14, 0.07]
    rings = []
    for s in ss:
        ring = []
        for (ox, oy) in OUTLINE:
            x, y = C[0] + (ox - C[0]) * s, C[1] + (oy - C[1]) * s
            z = 0.0 if s == 1.0 else mass_z(x, y)
            ring.append((U(x), V(y), z * P))
        rings.append(ring)
    rings.append([(U(C[0]), V(C[1]), mass_z(*C) * P)])
    before = len(bm.faces)
    lib.ring_loft(bm, rings, MASS, True, cap_start=False, cap_end=False)
    top_faces = bm.faces[before:] if False else None
    bm.faces.ensure_lookup_table()
    for f in bm.faces[before:]:
        c = f.calc_center_median()
        sx, sy = c.x / P + 12.0, 14.0 - c.y / P
        r = math.hypot(sx - VENT[0], sy - VENT[1])
        near_sleeve = (SLEEVE_X0 - 0.3 < sx < SLEEVE_X1 + 0.3) and (5.0 < sy < 7.6) and c.z / P > 1.5
        if r < 1.75 or near_sleeve:
            f.material_index = EMBER
    # underside: rounded lower edge to a flat base
    low = []
    for s, zf in ((0.985, 0.35), (0.955, 0.7), (0.92, 0.92), (0.88, 1.0), (0.5, 1.0)):
        low.append([(U(C[0] + (ox - C[0]) * s), V(C[1] + (oy - C[1]) * s), ZB * zf * P)
                    for (ox, oy) in OUTLINE])
    low.append([(U(C[0]), V(C[1]), ZB * P)])
    lib.ring_loft(bm, [rings[0]] + low, MASS, True, cap_start=False, cap_end=False)


# --- Hard parts ------------------------------------------------------------------------------

def cbox(bm, x0, x1, y0, y1, z0, z1, ch, mat, chz=None, open_x=()):
    """A chamfered box in sprite coords (x, y px edges, z px), top edges chamfered by ch,
    vertical edges by chz (default ch). Bottom edges square (they sit on the base)."""
    chz = ch if chz is None else chz
    def ring(z, inset, zx_ch):
        # octagon-ish footprint: vertical-edge chamfers zx_ch, inset all round by `inset`
        a0, a1, b0, b1 = x0 + inset, x1 - inset, y0 + inset, y1 - inset
        c = zx_ch
        return [(a0 + c, b0), (a1 - c, b0), (a1, b0 + c), (a1, b1 - c), (a1 - c, b1), (a0 + c, b1),
                (a0, b1 - c), (a0, b0 + c)]
    rings = [ring(z0, 0, chz), ring(z1 - ch, 0, chz), ring(z1, ch, max(0.0, chz - ch * 0.4))]
    pts = [[(U(x), V(y), z * P) for (x, y) in r] for (r, z) in zip(rings, (z0, z1 - ch, z1))]
    before = len(bm.faces)
    lib.ring_loft(bm, pts, mat, False, cap_start=True, cap_end=True)
    return before


def tube(bm, pts3, r, mat, sides=10, cap0=True, cap1=True, round_ends=False):
    """A round tube through (x, y, z) sprite-px points, radius r px."""
    path = [(U(x), V(y), z * P, r * P, r * P) for (x, y, z) in pts3]
    if round_ends:
        a, b = Vector(pts3[0]), Vector(pts3[1])
        d = (a - b).normalized()
        q = a + d * r * 0.6
        path.insert(0, (U(q.x), V(q.y), q.z * P, r * 0.75 * P, r * 0.75 * P))
    lib.sweep(bm, path, sides=sides, mat=mat, smooth=True, cap_start=cap0, cap_end=cap1)


def rounded_path(pts, rad=0.9, steps=4):
    """Round the corners of a 2D/3D polyline (each corner a quarter arc-ish of radius rad)."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        d0, d1 = (p0 - p1).normalized(), (p2 - p1).normalized()
        a, b = p1 + d0 * rad, p1 + d1 * rad
        for k in range(steps + 1):
            t = k / steps
            q = (1 - t) ** 2 * a + 2 * (1 - t) * t * p1 + t * t * b
            out.append(tuple(q))
    out.append(pts[-1])
    return out


def densify(pts, step=0.5):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / step))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a))))
    return out


def ride(pts2, r, lift, zmin=None):
    """Lift a 2D path onto the mass: centre at mass top + lift (smoothed), at least zmin."""
    zs = [mass_z(x, y) + lift for x, y in pts2]
    if zmin is not None:
        zs = [max(z, zm) for z, zm in zip(zs, zmin)] if isinstance(zmin, list) else [max(z, zmin) for z in zs]
    for _ in range(3):  # smooth
        zs = [zs[0]] + [(zs[i - 1] + 2 * zs[i] + zs[i + 1]) / 4 for i in range(1, len(zs) - 1)] + [zs[-1]]
    return [(x, y, z) for (x, y), z in zip(pts2, zs)]


def bolt(bm, x, y, z, r, mat, h=0.35, sides=6):
    ring0 = [(U(x + r * math.cos(2 * math.pi * k / sides)), V(y + r * math.sin(2 * math.pi * k / sides)), (z - 0.2) * P)
             for k in range(sides)]
    ring1 = [(a, b, (z + h) * P) for a, b, _ in ring0]
    ring2 = [(U(x + 0.7 * r * math.cos(2 * math.pi * k / sides)), V(y + 0.7 * r * math.sin(2 * math.pi * k / sides)),
              (z + h + 0.12) * P) for k in range(sides)]
    lib.ring_loft(bm, [ring0, ring1, ring2], mat, False)


YOKE_TOP = 3.3


def half_yoke(bm, x0, x1, inner_side, leg_x0, leg_x1, flare0, flare1, YOKE, BOLT):
    """One half of a clamp yoke: a chamfered block x0..x1 over rows 1-5 whose flat end lies on the
    block edge (it meets the neighbour's half there), and a jaw leg down the mass side to row 9."""
    # body: a rounded pipe-coupling housing (it continues the terrain pipe the blocks sit on),
    # section constant along x, a flange on the mass-side end, the block-edge end flat.
    sec = [(1.0, ZB), (6.0, ZB), (6.0, 1.3), (5.75, 2.3), (5.1, 2.95), (4.2, YOKE_TOP - 0.05),
           (3.3, YOKE_TOP), (2.4, YOKE_TOP - 0.1), (1.6, 2.75), (1.15, 2.0), (1.0, 1.2)]
    cy, cz = 3.5, ZB

    def ring(x, grow):
        out = []
        for (y, z) in sec:
            yy = cy + (y - cy) * (1 + grow / 2.5)
            zz = z + grow if z > ZB else z
            out.append((U(x), V(yy), zz * P))
        return out
    s0 = inner_side
    xin, xout = (x1, x0) if s0 > 0 else (x0, x1)
    st = [(xout, 0.0), (xin - s0 * 1.05, 0.0), (xin - s0 * 1.0, 0.22), (xin - s0 * 0.3, 0.22),
          (xin - s0 * 0.12, 0.08), (xin, -0.25)]
    if s0 < 0:
        st = list(reversed(st))
    lib.ring_loft(bm, [ring(x, g) for x, g in st], YOKE, False, cap_start=True, cap_end=True)
    stations = [(5.4, flare0, flare1, 2.3), (6.6, (flare0 + leg_x0) / 2, (flare1 + leg_x1) / 2, 2.6),
                (7.5, leg_x0, leg_x1, 2.5), (8.4, leg_x0, leg_x1, 2.2), (9.1, leg_x0 + 0.15, leg_x1 - 0.15, 1.7)]
    rings = []
    for y, a, b, zt in stations:
        c = 0.35
        ring = [(a, ZB), (b, ZB), (b, zt - c), (b - c, zt), (a + c, zt), (a, zt - c)]
        rings.append([(U(x), V(y), z * P) for (x, z) in ring])
    lib.ring_loft(bm, rings, YOKE, False, cap_start=True, cap_end=True)


def build(sprite, coll, proxy=False):
    pal = lambda i, tag="", **kw: common.palette_material(sprite, i, NAME + tag, **kw)  # noqa: E731
    mats = [
        pal(113, metallic=0.0, roughness=0.42, emission_strength=0.2),                          # 0 mass
        pal(116, metallic=1.0, roughness=0.85, emission_strength=0.5),  # 1 ember (lit by the glow)
        pal(120, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 2 heater sleeve
        pal(123, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 3 vent core
        pal(104, metallic=0.75, roughness=0.38),                        # 4 yoke
        pal(105, metallic=0.8, roughness=0.32),                         # 5 spindle, pipes
        pal(101, metallic=0.7, roughness=0.42),                         # 6 shoe
        pal(103, metallic=0.75, roughness=0.36),                        # 7 bolts, collars
    ]
    MASS, EMBER, SLEEVE, VENTM, YOKE, PIPE, SHOE, BOLT = range(8)
    bm = bmesh.new()
    build_mass(bm, (MASS, EMBER))

    # Yoke halves. Left: x 0..4 (columns 0-3), jaw on column 2. Right: x 21..24, jaw on column 21.
    half_yoke(bm, 0.0, 4.05, +1, 1.95, 3.25, 0.95, 3.3, YOKE, BOLT)
    half_yoke(bm, 20.95, 24.0, -1, 20.8, 22.1, 20.0, 23.0, YOKE, BOLT)

    # Spindle along row 5, yoke to yoke (inside both yokes at the ends so it meets the next block).
    sz = SPINDLE_Z
    tube(bm, [(0.0, 5.5, sz), (SLEEVE_X0, 5.5, sz)], 0.78, PIPE, sides=12)
    tube(bm, [(SLEEVE_X1, 5.5, sz), (24.0, 5.5, sz)], 0.78, PIPE, sides=12)
    # heater sleeve: ribbed glowing barrel
    xs = [SLEEVE_X0 + (SLEEVE_X1 - SLEEVE_X0) * k / 20 for k in range(21)]
    path = []
    for k, x in enumerate(xs):
        r = 1.05 if k in (0, 20) else (0.98 if k % 2 else 0.9)
        path.append((U(x), V(5.5), sz * P, r * P, r * P))
    lib.sweep(bm, path, sides=14, mat=SLEEVE, smooth=True)
    # collars where the spindle enters the sleeve and leaves the yokes
    for x in (SLEEVE_X0 - 0.35, SLEEVE_X1 + 0.35, 4.35, 20.65):
        tube(bm, [(x - 0.3, 5.5, sz), (x + 0.3, 5.5, sz)], 1.08, BOLT, sides=12)

    # Branch pipe: tee at column 6 on the spindle, up column 6 to row 2, east to column 8, into the mass.
    br2 = densify(rounded_path([(6.5, 5.3), (6.5, 2.55), (9.0, 2.55)], rad=0.8), 0.4)
    br = ride(br2, 0.6, 0.25, zmin=sz)
    tube(bm, br, 0.58, PIPE, sides=10)
    tube(bm, [(6.5, 5.5, sz + 0.2), (6.5, 5.5, sz + 1.25)], 0.85, BOLT, sides=10)  # tee boss
    bx, by, bz = br[-1]
    tube(bm, [(bx - 0.35, by, bz), (bx + 0.25, by, bz)], 0.8, BOLT, sides=10)  # gland into the mass

    # Lower pipe: out of the right jaw along row 7, down column 16, along row 9 into the shoe.
    lp2 = densify(rounded_path([(21.0, 7.5), (16.55, 7.5), (16.55, 9.45), (13.0, 9.45)], rad=0.8), 0.4)
    lp = ride(lp2, 0.6, 0.3)
    tube(bm, lp, 0.6, PIPE, sides=10)

    # Clamp shoe gripping the mass's lower lip: columns 10-13, rows 9-14.
    secs = [(9.0, 3.35), (10.0, 3.6), (12.5, 3.2), (13.4, 2.4), (14.0, 1.3)]
    rings = []
    for y, zt in secs:
        x0, x1, c = 9.65, 13.45, 0.45
        ring = [(x0, ZB), (x1, ZB), (x1, zt - c), (x1 - c, zt), (x0 + c, zt), (x0, zt - c)]
        rings.append([(U(x), V(y), z * P) for (x, z) in ring])
    lib.ring_loft(bm, rings, SHOE, False, cap_start=True, cap_end=True)
    bolt(bm, 11.4, 11.4, 3.35, 0.55, BOLT)

    # Vent core: a glowing bead in the crater.
    vz = mass_z(*VENT)
    lib.ellipsoid(bm, U(VENT[0]), V(VENT[1]), (vz + 0.25) * P, 1.3 * P, 1.25 * P, 0.65 * P, mat=VENTM, segments=12, rings=6)

    obj = lib.to_object(NAME, bm, mats, coll)
    return obj


def build_model(sprite):
    coll = common.reset_collection(NAME)
    proxy = build(sprite, coll, proxy=True)
    shell = common.outline_shell(proxy, coll, voxel=0.006, faces=3000, smooth=2, inside=0.003, islands="outer")
    bpy.data.objects.remove(proxy, do_unlink=True)
    obj = build(sprite, coll)
    assert obj.name == NAME and shell.name == f"{NAME}_outline", (obj.name, shell.name)
    assert len(shell.data.polygons) > 0
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"tris {tris} shell faces {len(shell.data.polygons)}")
    return [(NAME, [obj, shell], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build_model, __file__)
