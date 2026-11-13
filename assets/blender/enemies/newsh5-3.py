"""Purple bat-winged pod (newsh5.shp frames 3-17), final build from design A.

What it is: a purple armoured flyer seen from above, head first (it climbs back up the screen
head first after its swoop). Read from the sprite (24x28):

  - head: two round sensor lobes (rows 1-5) side by side, a dark crease between them (row 4);
    the bright pixels on them (3,9) (3,14) are sheen on domes, not bumps.
  - neck (rows 5-9): a narrow spine with two raised rails (columns 10, 13) either side of a dark
    channel (columns 11-12), widening into
  - a collar (rows 10-12) that carries the wing spar right across the craft and two white eye
    lenses (row 12, columns 10 and 13); a dark crease behind it (row 13) with two vent holes
    (columns 9, 14).
  - body (rows 14-25, columns 6-17): a boxy hull with a rounded front shoulder (rows 14-16, the lit
    band), a dark centre channel (columns 11-12, rows 17-24) with three rungs (rows 18, 20, 22),
    a glowing green light tube each side (columns 7-8, rows 17-23) in a channel, ending in two
    rear emitter heels with dark green lenses (rows 24-25), a notch between them.
  - wings (columns 0-5 each side, rows 11-23): bat wings drooping outward off the spar: two ribs
    (columns 2 and 4) and an outer finger (column 0), the membrane sagging between them, a
    scalloped trailing edge; the lower half of the column-4 rib is a green light.

The frames only run the lights: frame 3 dark (rungs and wing-rib lights off, tubes and lenses
dimmer), the other seven lit with a bright bar scanning down the body one row per frame, rows
18 (frame 5) to 24 (frame 17), columns 8-15: one glowing rod per frame (common.frame_part).

Run: blender --background --python assets/blender/enemies/newsh5-3.py
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
NAME = "newsh5-3"
U = 1 / 12
W_SPR, H_SPR = 24, 28
LIT = (5, 7, 9, 11, 13, 15, 17)

# (key, palette index on frame 3, {frame: index}, metallic, roughness, emission)
MATS = [
    ("hull", 87, None, 0.45, 0.42, 0.0),
    ("lobe", 86, None, 0.5, 0.36, 0.0),
    ("wing", 85, None, 0.35, 0.5, 0.0),
    ("rib", 88, None, 0.5, 0.38, 0.0),
    ("groove", 82, None, 0.3, 0.65, 0.0),
    ("eye", 93, None, 1.0, 0.7, 0.85),
    ("tube", 196, {f: 199 for f in LIT}, 1.0, 0.75, 1.0),
    ("lens", 38, {f: 40 for f in LIT}, 1.0, 0.6, 0.6),
    ("rung", 197, {3: 82}, 1.0, 0.75, 1.0),
    ("riblight", 194, {3: 87}, 1.0, 0.75, 0.9),
    ("bar", 205, {15: 206, 17: 207}, 1.0, 0.8, 1.1),
    ("collar", 88, None, 0.45, 0.4, 0.0),
]
HULL, LOBE, WING, RIB, GROOVE, EYE, TUBE, LENS, RUNG, RIBL, BAR, COLLAR = range(len(MATS))


# ---- geometry in sprite px: x = column edge - 12 (left negative), y = row edge (down), z = px up.
# Converted to Blender (X right, Y up the sprite, Z up) at the end.

def pchip(xs, ys):
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
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


class Mesh:
    def __init__(self, bm):
        self.bm = bm

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

    def rings(self, rings, mats, closed=True, cap0=True, cap1=True, smooth=True):
        """rings: list of point lists (same length). mats(i_ring, j_seg) -> material."""
        vr = [[self.v(p) for p in r] for r in rings]
        n = len(rings[0])
        segs = n if closed else n - 1
        for i in range(len(vr) - 1):
            for j in range(segs):
                k = (j + 1) % n
                self.f([vr[i][j], vr[i][k], vr[i + 1][k], vr[i + 1][j]], mats(i, j), smooth)
        for cap, r, rev in ((cap0, vr[0], True), (cap1, vr[-1], False)):
            if cap:
                c = [sum(v.co[a] for v in r) / n for a in range(3)]
                cv = self.v(c)
                for j in range(segs):
                    k = (j + 1) % n
                    tri = [r[j], r[k], cv] if not rev else [r[k], r[j], cv]
                    self.f(tri, mats(0 if rev else len(vr) - 2, j), smooth)
        return vr


def ellipsoid(M, c, r, mat, seg=20, rings=10, zcut=None):
    pts = []
    for i in range(1, rings):
        th = math.pi * i / rings
        ring = []
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            ring.append((c[0] + r[0] * math.sin(th) * math.cos(ph), c[1] + r[1] * math.sin(th) * math.sin(ph),
                         c[2] + r[2] * math.cos(th)))
        pts.append(ring)
    top = M.v((c[0], c[1], c[2] + r[2]))
    bot = M.v((c[0], c[1], c[2] - r[2]))
    vr = [[M.v(p) for p in ring] for ring in pts]
    for i in range(len(vr) - 1):
        for j in range(seg):
            k = (j + 1) % seg
            M.f([vr[i][j], vr[i + 1][j], vr[i + 1][k], vr[i][k]], mat)
    for j in range(seg):
        k = (j + 1) % seg
        M.f([top, vr[0][j], vr[0][k]], mat)
        M.f([bot, vr[-1][k], vr[-1][j]], mat)


def tube(M, path, radii, mat, sides=10, cap0=True, cap1=True, matf=None):
    """Sweep along 3D path points with (rw, rh) half sizes; rings perpendicular to the path."""
    from mathutils import Vector
    P = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1))
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nrm = side.cross(t).normalized()
        rw, rh = radii[i]
        ring = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            q = p + side * (rw * math.cos(a)) + nrm * (rh * math.sin(a))
            ring.append(tuple(q))
        rings.append(ring)
    return M.rings(rings, matf or (lambda i, j: mat), cap0=cap0, cap1=cap1)


# ---- fuselage: one loft head-to-tail with a station profile -------------------------------------

# key stations: y, T top, B bottom, W half width, gd groove depth, rh rail height, sd strip depth,
# xs0/xs1 strip channel, xc shoulder start
KEYS = [
    # y     T    B     W    gd   rh   sd   xs0  xs1  xc
    (4.0, 2.4, 0.6, 2.6, 0.0, 0.0, 0.0, 1.9, 2.0, 2.05),
    (4.6, 3.0, 0.2, 3.0, 0.45, 0.4, 0.0, 2.3, 2.4, 2.5),
    (6.0, 3.2, -0.2, 3.0, 0.5, 0.45, 0.0, 2.3, 2.4, 2.5),
    (8.5, 3.3, -0.6, 3.0, 0.5, 0.45, 0.0, 2.3, 2.4, 2.5),
    (9.6, 3.6, -1.0, 4.0, 0.3, 0.3, 0.0, 3.0, 3.2, 3.4),
    (10.2, 4.3, -1.6, 5.0, 0.0, 0.0, 0.0, 3.0, 4.6, 4.7),
    (11.2, 4.9, -2.0, 6.0, 0.0, 0.0, 0.0, 3.0, 5.0, 5.2),
    (12.4, 4.8, -2.3, 6.0, 0.0, 0.0, 0.0, 3.0, 5.0, 5.2),
    (13.4, 3.5, -2.5, 6.0, 0.0, 0.0, 0.0, 3.0, 5.0, 5.2),
    (15.2, 4.3, -2.6, 6.0, 0.0, 0.0, 0.0, 3.0, 5.0, 5.2),
    (16.6, 3.8, -2.6, 6.0, 0.0, 0.0, 0.0, 3.0, 5.0, 5.2),
    (16.9, 3.6, -2.6, 6.0, 0.9, 0.0, 0.7, 3.0, 5.0, 5.2),
    (20.0, 3.5, -2.5, 6.0, 0.9, 0.0, 0.7, 3.0, 5.0, 5.2),
    (22.8, 3.3, -2.2, 6.0, 0.9, 0.0, 0.7, 3.0, 5.0, 5.2),
    (23.6, 2.8, -1.6, 5.9, 0.9, 0.0, 0.7, 3.0, 5.0, 5.2),
    (24.0, 2.0, -0.9, 5.6, 0.5, 0.0, 0.4, 3.0, 5.0, 5.2),
]
GW = 1.0  # groove half width (columns 11-12)
XR = 1.5  # neck rails (columns 10 and 13)


def station(y):
    cols = list(zip(*KEYS))
    return [pchip(list(cols[0]), list(cols[k]))(y) for k in range(1, len(KEYS[0]))]


def profile(y):
    """Closed ring (x, z) list, left half then mirrored; and the segment kinds."""
    T, B, W, gd, rh, sd, xs0, xs1, xc = station(y)
    rc = min(1.1, (T - B) * 0.3)
    rb = min(1.4, (T - B) * 0.35)
    top = [
        (0.0, T - gd, "g"), (GW - 0.12, T - gd, "g"), (GW, T - gd * 0.4 + rh * 0.3, "w"),
        (GW + 0.12, T + rh * 0.85, "r"), (XR, T + rh, "r"), (XR + 0.38, T + rh * 0.7, "r"),
        (XR + 0.7, T + rh * 0.15, "h"),
        (xs0 - 0.06, T, "h"), (xs0 + 0.06, T - sd, "s"), ((xs0 + xs1) / 2, T - sd * 1.1, "s"), (xs1 - 0.06, T - sd, "s"),
        (xs1 + 0.06, T, "h"),
        (xc, T, "h"),
    ]
    half, lastx = [], -1.0
    for x, z, k in top:
        x = max(x, lastx + 0.03)
        lastx = x
        half.append((x, z, k))
    xc = lastx
    W = max(W, xc + 0.3)
    for a in (0.3, 0.6, 0.85):
        th = a * math.pi / 2
        half.append((xc + (W - xc) * math.sin(th), T - rc * (1 - math.cos(th)), "c"))
    half.append((W, T - rc, "c"))
    half.append((W, B + rb, "c"))
    for a in (0.4, 0.8):
        th = a * math.pi / 2
        half.append((W - rb * (1 - math.cos(th)) * 0.9, B + rb * (1 - math.sin(th)), "b"))
    half.append((W - rb, B, "b"))
    half.append((0.0, B - 0.1, "b"))
    ring = [(-x, z, k) for x, z, k in half] + [(x, z, k) for x, z, k in reversed(half)][1:-1]
    return ring, (T, B, W, gd, rh, sd)


def fuselage(M):
    ys = []
    y = 4.0
    while y < 24.0:
        ys.append(round(y, 3))
        y += 0.9 if y < 16 else 1.4
    extra = [4.6, 9.6, 10.2, 11.2, 12.4, 13.4, 15.2, 16.6, 16.9, 23.6, 24.0]
    ys = sorted(set(ys + extra))
    rings, info = [], []
    for y in ys:
        ring, st = profile(y)
        rings.append([(x, y, z) for x, z, _ in ring])
        info.append((st, [k for _, _, k in ring]))

    def mats(i, j):
        st, kinds = info[i]
        st2 = info[min(i + 1, len(info) - 1)][0]
        k = kinds[j]
        k2 = kinds[(j + 1) % len(kinds)]
        y = (ys[i] + ys[min(i + 1, len(ys) - 1)]) / 2
        if k == k2 == "g" and min(st[3], st2[3]) > 0.2:
            return GROOVE
        if k == k2 == "s" and min(st[5], st2[5]) > 0.2:
            return GROOVE
        if k == k2 == "r" and min(st[4], st2[4]) > 0.2:
            return RIB
        if 9.9 < y < 13.0 and k in ("h", "r", "w", "g", "s") and k2 != "b":
            return COLLAR
        return HULL
    M.rings(rings, mats, cap0=True, cap1=True)
    return ys


def top_z(x, y):
    """Fuselage top height at (x, y) (for placing parts on it)."""
    T, B, W, gd, rh, sd, xs0, xs1, xc = station(y)
    return T


# ---- wings --------------------------------------------------------------------------------------

def te_base(c):
    """Trailing edge row (edge coordinate) at column edge c (0 = wing tip)."""
    return pchip([0.0, 0.6, 1.0, 1.5, 2.5, 3.5, 4.5, 5.5, 6.6], [17.45, 18.6, 20.0, 21.0, 21.35, 21.9, 22.5, 23.2, 24.2])(c)


RIBS = (0.55, 2.5, 4.5)  # column positions of the outer finger and the two ribs


def te(c):
    """With scallops between the rib tips (shallow: the sprite's notches are single dark pixels)."""
    s = 0.0
    for a, b in ((0.55, 2.5), (2.5, 4.5), (4.5, 6.4)):
        if a < c < b:
            s = 0.35 * math.sin(math.pi * (c - a) / (b - a))
    return te_base(c) - s


LE = 11.05  # leading edge row edge


SAG = [0.28]


def wing_z(c, y, bottom=False):
    """Membrane height: droops outward (c -> 0) and aft, sags between ribs."""
    span = (6.4 - c) / 6.4  # 0 at root, 1 at tip
    t = (y - LE) / max(0.5, te_base(c) - LE)
    z = 2.2 - 3.6 * span ** 1.25 - 1.2 * t
    sag = 0.0
    for a, b in ((0.55, 2.5), (2.5, 4.5), (4.5, 6.2)):
        if a < c < b:
            sag = SAG[0] * math.sin(math.pi * (c - a) / (b - a)) * min(1.0, t * 3)
    z -= sag
    if bottom:
        z -= 0.55 - 0.15 * span
    return z


def wing(M, side, ribs=True):
    """Closed thin wing shell for one side (side=-1 left). Root buried in the hull side."""
    cs = [0.0, 0.3, 0.6, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.6, 6.4, 6.9]
    nt = 8
    top, bot = [], []
    for c in cs:
        c0 = min(c, 6.4)
        y0 = LE + max(0.0, 1.0 * (1.3 - c) / 1.3)
        y1 = te(c0) if c <= 6.4 else te(6.4) + 0.2
        if c < 0.01:
            y1 = te(0.0) - 0.2
        rt, rb = [], []
        for i in range(nt + 1):
            t = i / nt
            y = y0 + (y1 - y0) * t
            x = side * (12 - c)
            rt.append((x, y, wing_z(c0, y)))
            rb.append((x, y, wing_z(c0, y, True)))
        top.append(rt)
        bot.append(rb)
    vt = [[M.v(p) for p in r] for r in top]
    vb = [[M.v(p) for p in r] for r in bot]
    n = len(cs)
    for i in range(n - 1):
        for j in range(nt):
            M.f([vt[i][j], vt[i + 1][j], vt[i + 1][j + 1], vt[i][j + 1]], WING)
            M.f([vb[i][j + 1], vb[i + 1][j + 1], vb[i + 1][j], vb[i][j]], WING)
    # rims: leading (j=0), trailing (j=nt), tip (i=0), root (i=n-1)
    for i in range(n - 1):
        M.f([vt[i][0], vb[i][0], vb[i + 1][0], vt[i + 1][0]], WING)
        M.f([vt[i + 1][nt], vb[i + 1][nt], vb[i][nt], vt[i][nt]], WING)
    for j in range(nt):
        M.f([vt[0][j + 1], vb[0][j + 1], vb[0][j], vt[0][j]], WING)
        M.f([vt[n - 1][j], vb[n - 1][j], vb[n - 1][j + 1], vt[n - 1][j + 1]], WING)

    # leading-edge spar: a round tube along row 11.8 from inside the collar to the tip
    path, radii = [], []
    for c in (6.8, 5.5, 4.0, 2.5, 1.8, 1.4, 1.15):
        y = 11.85
        z = wing_z(min(c, 6.4), LE + 0.3) + 0.15
        path.append((side * (12 - c), y, z))
        k = 1.0 if c > 1.7 else (0.85 if c > 1.3 else 0.5)
        radii.append((0.82 * k, 0.78 * k))
    tube(M, path, radii, RIB, sides=10)
    if not ribs:
        return
    # outer finger down the tip edge, ribs at columns 2 and 4 (column 4's lower half is a light)
    for cr, light in ((0.62, False), (2.5, False), (4.5, True)):
        yend = te(cr) - (0.45 if cr > 1 else 0.6)
        n_s = 7
        path, radii, mats = [], [], []
        for i in range(n_s + 1):
            t = i / n_s
            y = 11.9 + (yend - 11.9) * t
            c = cr + (0.0 if cr > 1 else 0.05 * t)
            path.append((side * (12 - c), y, wing_z(c, y) + 0.12))
            r = 0.44 * (1 - 0.4 * t ** 1.5)
            radii.append((r, r * 0.9))
            mats.append(RIBL if (light and y > 15.9) else RIB)
        tube(M, path, radii, RIB, sides=7, matf=lambda i, j, mats=mats: mats[min(i + 1, len(mats) - 1)])


# ---- small parts --------------------------------------------------------------------------------

def head(M):
    for s in (-1, 1):
        ellipsoid(M, (s * 2.75, 3.45, 2.75), (2.8, 2.5, 1.95), LOBE, seg=16, rings=8)
        # a seam collar where the lobe sits on the neck (a ring band, slightly proud)
    # brow bridge between the lobes, low, so the dark crease (row 4) stays
    tube(M, [(-1.2, 4.6, 2.6), (0, 4.75, 2.45), (1.2, 4.6, 2.6)], [(0.6, 0.5)] * 3, HULL, sides=8)


def eyes(M):
    for s in (-1, 1):
        x, y = s * 1.5, 12.5
        z = top_z(x, y)
        # socket rim then the lens dome
        tube(M, [(x, y, z - 0.3), (x, y, z + 0.25)], [(0.75, 0.75), (0.75, 0.75)], HULL, sides=10)
        ellipsoid(M, (x, y, z + 0.25), (0.58, 0.58, 0.38), EYE, seg=10, rings=5)


def vents(M):
    # the two vent holes in the crease behind the collar (row 13, columns 9 and 14): dark sockets
    for s in (-1, 1):
        x, y = s * 2.5, 13.5
        z = top_z(x, y)
        tube(M, [(x, y, z - 0.9), (x, y, z + 0.08)], [(0.5, 0.42), (0.5, 0.42)], GROOVE, sides=10)


def light_tubes(M):
    """The green light tubes in the side channels (columns 7-8), into the emitter heels."""
    for s in (-1, 1):
        x = s * 4.0
        path, radii = [], []
        for y in (16.95, 17.4, 19.5, 21.5, 23.0, 24.0):
            T = station(y)[0]
            path.append((x, y, T - 0.12))
            radii.append((1.0, 0.45))
        tube(M, path, radii, TUBE, sides=8)
        # emitter heel: a rounded pontoon carrying the tube past the hull, a dark green lens on its end
        heel = []
        for y, hw, cx, zt, zb in ((21.5, 2.35, 3.75, 2.9, -1.8), (23.0, 2.4, 3.7, 2.9, -1.7), (24.2, 2.45, 3.65, 2.6, -1.4),
                                  (24.75, 1.9, 4.05, 2.2, -1.0), (25.2, 1.25, 4.4, 1.7, -0.5), (25.55, 0.55, 4.5, 1.1, 0.1)):
            ring = []
            for j in range(14):
                a = 2 * math.pi * j / 14
                ca, cz = math.cos(a), math.sin(a)
                ex = 2.5
                px = math.copysign(abs(ca) ** (2 / ex), ca) * hw
                pz = math.copysign(abs(cz) ** (2 / ex), cz)
                pz = (zt + zb) / 2 + pz * (zt - zb) / 2
                ring.append((s * cx + px, y, pz))
            heel.append(ring)
        M.rings(heel, lambda i, j: HULL, cap0=True, cap1=True)
        # lens: a dark green glass dome on the heel's top rear (rows 24-25, columns 7-8)
        ellipsoid(M, (s * 4.15, 24.65, 2.15), (1.0, 0.85, 0.55), LENS, seg=12, rings=6)


def rungs(M):
    for r in (18, 20, 22):
        y = r + 0.5
        T = station(y)[0]
        tube(M, [(-1.05, y, T - 0.55), (1.05, y, T - 0.55)], [(0.32, 0.32)] * 2, RUNG, sides=8)


def side_beads(M):
    """A raised bead along each top side edge of the hull (column 6, rows 14-23)."""
    for s in (-1, 1):
        path, radii = [], []
        for y in (13.9, 15.2, 16.6, 18.5, 20.5, 22.4, 23.3):
            T = station(y)[0]
            path.append((s * 5.45, y, T - 0.15))
            radii.append((0.45, 0.35))
        tube(M, path, radii, RIB, sides=8)


def bar(M, r):
    y = r + 0.5
    T = station(min(y, 23.9))[0] if y < 24 else 2.2
    z = T + 0.15
    if r >= 23:
        z = max(T, 2.4) + 0.2
    tube(M, [(-4.0, y, z), (4.0, y, z)], [(0.42, 0.34)] * 2, BAR, sides=8)


def to_blender(bm):
    for v in bm.verts:
        x, y, z = v.co
        v.co = ((x) * U, (14 - y) * U, z * U)


def sharpen(bm, deg=42):
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if a.normal.angle(b.normal, 0) > math.radians(deg) or a.material_index != b.material_index:
                e.smooth = False


def build():
    import bmesh
    import bpy
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import common

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = []
    for key, idx, fr, met, rough, em in MATS:
        m = common.palette_material(sprite, idx, f"{NAME}-{key}", frames=fr, metallic=met, roughness=rough,
                                    emission_strength=em)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.5
        mats.append(m)

    def make(name, fill, smooth_deg=42):
        bm = bmesh.new()
        fill(Mesh(bm))
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        to_blender(bm)
        bm.normal_update()
        sharpen(bm, smooth_deg)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob

    def body(M):
        fuselage(M)
        head(M)
        wing(M, -1)
        wing(M, 1)
        eyes(M)
        vents(M)
        light_tubes(M)
        rungs(M)
        side_beads(M)

    obj = make(NAME, body)
    bars = []
    for k, frame in enumerate(LIT):
        b = make(f"{NAME}-bar-{frame}", lambda M, r=18 + k: bar(M, r))
        common.frame_part(b, [frame])
        bars.append(b)

    # outline shell from a sealed copy: fuselage, lobes, wings, spar, heels (no grooves' detail matters:
    # the shell is a voxel remesh, smoothed, held inside the model)
    def seal(M):
        fuselage(M)
        head(M)
        SAG[0] = 0.0
        wing(M, -1, ribs=False)
        wing(M, 1, ribs=False)
        SAG[0] = 0.28
        light_tubes(M)
    sobj = make(NAME + "_seal", seal)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sobj, coll, voxel=0.01, faces=2600, smooth=4, inside=0.004, islands="outer")
    bpy.data.objects.remove(sobj, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"

    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    tris_bars = 0
    for b in bars:
        b.data.calc_loop_triangles()
        tris_bars += len(b.data.loop_triangles)
    objs = [obj] + bars + [shell]
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    print("MANIFEST", json.dumps({NAME: {"frames": [3] + list(LIT), "tris": tris, "tris_bars": tris_bars,
                                         "shell_faces": len(shell.data.polygons)}}))


if __name__ == "__main__":
    build()
