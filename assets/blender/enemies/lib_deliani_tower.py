"""DELIANI's flamethrower tower (assembly-newshc-283 with its newshc-77 head): the true upright
tower, pure Python geometry. Used by assembly-newshc-283.py (body) and newshc-77.py (head frames),
which build it in the art's frame and export it upright with the `tyrian_oblique` and
`tyrian_depth_band` extras (D165).

Coordinates: u = sprite column edge (0..24, west -> east), v = plan row (north -> south), z = height,
all in sprite px; the tower's axis stands at (u, v) = (CU, VB). Azimuth th: 0 = facing south (the
player / art camera side), +pi/2 = east.

The art's camera (orthographic, from the south, 15 deg up) maps a point to the sprite column's
screen row s = VB + A*(v - VB) - K*z (screen column = u). Each part is
{"name", "pal", "tris": [[p, p, p], ...], "glow": float, "smooth": bool}.
"""

import math

ELEV = math.radians(15)
A, K = math.sin(ELEV), math.cos(ELEV)
VB = 95.4
CU = 12.0


def zOf(s):
    return (VB - s) / K


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    ln = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    return (a[0] / ln, a[1] / ln, a[2] / ln)


def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    if n == 2:
        m[0] = m[1] = d[0]
    else:
        for i in range(1, n - 1):
            if d[i - 1] * d[i] <= 0:
                m[i] = 0.0
            else:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        m[0], m[-1] = d[0], d[-1]

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = 0
        while x > xs[i + 1]:
            i += 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def P(th, r, z, cu=CU, cv=VB):
    return (cu + r * math.sin(th), cv + r * math.cos(th), z)


class Geo:
    NSEG = 48

    def __init__(self):
        self.parts = []

    def add(self, name, pal, tris, glow=0.0, smooth=True):
        self.parts.append({"name": name, "pal": pal, "tris": tris, "glow": glow, "smooth": smooth})

    @staticmethod
    def strip(tris, r0, r1, closed=True):
        n = len(r0)
        last = n if closed else n - 1
        for k in range(last):
            j = (k + 1) % n
            tris.append([r0[k], r0[j], r1[j]])
            tris.append([r0[k], r1[j], r1[k]])

    @staticmethod
    def cap_fan(tris, ring, c, flip=False):
        for k in range(len(ring)):
            a, b = ring[k], ring[(k + 1) % len(ring)]
            tris.append([b, a, c] if flip else [a, b, c])

    def lathe(self, name, pal, R, z0, z1, n=None, step=0.5, cap0=False, cap1=False, glow=0.0, cu=CU, cv=VB):
        n = n or self.NSEG
        tris = []
        zs = []
        z = z0
        while z < z1 - 1e-6:
            zs.append(z)
            z += step
        zs.append(z1)
        ths = [2 * math.pi * k / n for k in range(n)]
        rings = [[P(th, R(zz, th), zz, cu, cv) for th in ths] for zz in zs]
        for i in range(len(rings) - 1):
            self.strip(tris, rings[i], rings[i + 1])
        if cap0:
            self.cap_fan(tris, rings[0], (cu, cv, z0), flip=True)
        if cap1:
            self.cap_fan(tris, rings[-1], (cu, cv, z1))
        self.add(name, pal, tris, glow)

    def patch(self, name, pal, R, th0, th1, z0, z1, dr, glow=0.0):
        nt = max(2, math.ceil(abs(th1 - th0) / 0.08))
        nz = max(1, math.ceil((z1 - z0) / 0.6))
        tris = []

        def grid(off):
            g = []
            for i in range(nz + 1):
                z = z0 + (z1 - z0) * i / nz
                g.append([P(th0 + (th1 - th0) * k / nt, R(z) + off, z) for k in range(nt + 1)])
            return g
        o = grid(dr)
        b = grid(-0.15 if dr > 0 else 0.15)
        for i in range(nz):
            for k in range(nt):
                tris.append([o[i][k], o[i][k + 1], o[i + 1][k + 1]])
                tris.append([o[i][k], o[i + 1][k + 1], o[i + 1][k]])

        def wall(a, c):
            for k in range(len(a) - 1):
                tris.append([a[k], a[k + 1], c[k + 1]])
                tris.append([a[k], c[k + 1], c[k]])
        wall(o[0], b[0])
        wall(o[nz], b[nz])
        wall([r[0] for r in o], [r[0] for r in b])
        wall([r[nt] for r in o], [r[nt] for r in b])
        self.add(name, pal, tris, glow, smooth=False)

    def tube(self, name, pal, p0, d, ln, r0, r1, n=18, cap0=True, cap1=True, glow=0.0):
        d = norm(d)
        t = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
        e1 = norm(cross(d, t))
        e2 = cross(d, e1)

        def ring(c, r):
            return [add(c, add(mul(e1, r * math.cos(2 * math.pi * k / n)), mul(e2, r * math.sin(2 * math.pi * k / n))))
                    for k in range(n)]
        p1 = add(p0, mul(d, ln))
        a, b = ring(p0, r0), ring(p1, r1)
        tris = []
        self.strip(tris, a, b)
        if cap0:
            self.cap_fan(tris, a, p0, flip=True)
        if cap1:
            self.cap_fan(tris, b, p1)
        self.add(name, pal, tris, glow)
        return p1

    def obox(self, name, pal, c, ax, h, ch=0.0, glow=0.0):
        """Oriented box, its vertical edges chamfered by ch (machined blocks, not raw cubes)."""
        tris = []
        if ch <= 0:
            v = []
            for sx in (-1, 1):
                for sy in (-1, 1):
                    for sz in (-1, 1):
                        v.append(add(c, add(mul(ax[0], sx * h[0]), add(mul(ax[1], sy * h[1]), mul(ax[2], sz * h[2])))))
            for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
                tris.append([v[q[0]], v[q[1]], v[q[2]]])
                tris.append([v[q[0]], v[q[2]], v[q[3]]])
        else:
            ch = min(ch, h[0] * 0.45, h[1] * 0.45)
            oct2 = [(h[0] - ch, h[1]), (h[0], h[1] - ch), (h[0], -h[1] + ch), (h[0] - ch, -h[1]),
                    (-h[0] + ch, -h[1]), (-h[0], -h[1] + ch), (-h[0], h[1] - ch), (-h[0] + ch, h[1])]

            def pt(x, y, z):
                return add(c, add(mul(ax[0], x), add(mul(ax[1], y), mul(ax[2], z))))
            bot = [pt(x, y, -h[2]) for x, y in oct2]
            top = [pt(x, y, h[2]) for x, y in oct2]
            # ring order is clockwise seen from +ax2: reverse for outward faces
            bot, top = bot[::-1], top[::-1]
            self.strip(tris, bot, top)
            self.cap_fan(tris, top, pt(0, 0, h[2]))
            self.cap_fan(tris, bot, pt(0, 0, -h[2]), flip=True)
        self.add(name, pal, tris, glow, smooth=False)

    def surf_box(self, name, pal, R, th, z, w, h, depth, ch=0.0, glow=0.0):
        r = R(z)
        n = (math.sin(th), math.cos(th), 0)
        t = (math.cos(th), -math.sin(th), 0)
        c = add((CU, VB, z), mul(n, r + depth / 2 - 0.3))
        self.obox(name, pal, c, [t, n, (0, 0, 1)], [w / 2, depth / 2 + 0.3, h / 2], ch=ch, glow=glow)

    def sphere_patch(self, name, pal, c, r, la0, la1, th0, th1, tk, xf=None, glow=0.0, smooth=True):
        nl = max(2, math.ceil(abs(la1 - la0) / 0.1))
        nt = max(2, math.ceil(abs(th1 - th0) / 0.09))
        tris = []

        def pt(la, th, rr):
            p = (c[0] + rr * math.cos(la) * math.sin(th), c[1] + rr * math.cos(la) * math.cos(th), c[2] + rr * math.sin(la))
            return xf(p) if xf else p

        def g(rr):
            return [[pt(la0 + (la1 - la0) * i / nl, th0 + (th1 - th0) * k / nt, rr) for k in range(nt + 1)]
                    for i in range(nl + 1)]
        o = g(r)
        b = g(r - tk) if tk > 0 else None
        for i in range(nl):
            for k in range(nt):
                tris.append([o[i][k], o[i][k + 1], o[i + 1][k + 1]])
                tris.append([o[i][k], o[i + 1][k + 1], o[i + 1][k]])
                if b:
                    tris.append([b[i][k], b[i + 1][k + 1], b[i][k + 1]])
                    tris.append([b[i][k], b[i + 1][k], b[i + 1][k + 1]])
        if b:
            def wall(a, c2):
                for k in range(len(a) - 1):
                    tris.append([a[k], a[k + 1], c2[k + 1]])
                    tris.append([a[k], c2[k + 1], c2[k]])
            wall(o[0], b[0])
            wall(o[nl], b[nl])
            wall([q[0] for q in o], [q[0] for q in b])
            wall([q[nt] for q in o], [q[nt] for q in b])
        self.add(name, pal, tris, glow, smooth)


# ---- the column's profile R(z), traced from the sprite's inner mask (D74) ------------------------
# (screen row of the axis, radius) -> heights with zOf. Round sections everywhere.
ST = [
    (97.6, 6.9), (97.0, 7.6), (96.0, 7.9), (94.5, 8.0),
    (84.0, 8.0), (81.6, 8.0), (80.2, 6.8), (78.8, 6.4),
    (77.4, 5.7), (76.4, 6.1),
    (75.4, 6.3), (74.2, 7.2), (73.0, 8.0), (67.6, 8.0), (66.2, 6.8), (64.6, 6.4),
    (63.6, 6.0), (55.4, 6.0),
    (54.4, 5.6), (53.6, 6.1),
    (52.4, 6.4), (51.2, 7.2), (50.0, 8.0), (43.6, 8.0),
    (42.4, 6.8), (41.2, 4.5), (40.2, 3.7),
    (39.2, 3.0), (38.4, 3.7), (37.4, 5.5), (36.2, 7.0), (35.0, 8.0), (30.6, 8.0), (29.8, 7.0), (29.0, 6.3),
]
_zs = [zOf(s) for s, _ in ST]
_order = sorted(range(len(ST)), key=lambda i: _zs[i])
Rcol = pchip([_zs[i] for i in _order], [ST[i][1] for i in _order])
Z_TOP = zOf(29.0)


def foot_chamfer(z, th):
    w = max(0.0, -math.sin(th))
    k = max(0.0, 1 - z / 4.2)
    return 2.6 * k * k * w * w


def Rbase(z, th=0.0):
    return Rcol(z) - foot_chamfer(z, th)


def body(G):
    B = zOf
    G.lathe("base_foot", 4, Rbase, 0, B(92.5), cap0=True)
    G.lathe("base_drum", 4, lambda z, th: Rcol(z), B(92.5), B(81.0))
    G.lathe("drum2_shoulder", 6, lambda z, th: Rcol(z), B(81.0), B(77.9))
    G.lathe("gap77", 3, lambda z, th: Rcol(z), B(77.9), B(76.9))
    G.lathe("drum1", 5, lambda z, th: Rcol(z), B(76.9), B(64.2))
    G.lathe("shaft", 3, lambda z, th: Rcol(z), B(64.2), B(55.0))
    G.lathe("gap54", 3, lambda z, th: Rcol(z), B(55.0), B(53.9))
    G.lathe("drum0", 5, lambda z, th: Rcol(z), B(53.9), B(44.4))
    G.lathe("bell", 72, lambda z, th: Rcol(z), B(44.4), B(40.6), glow=0.35)
    G.lathe("neck40", 3, lambda z, th: Rcol(z), B(40.6), B(38.8))
    G.lathe("cup", 7, lambda z, th: Rcol(z), B(38.8), Z_TOP)
    # cup top: a chamfered annulus (the lit rim) and the bore the head's neck slides in
    n = G.NSEG
    ro, ri = Rcol(Z_TOP), 6.15
    ths = [2 * math.pi * k / n for k in range(n)]
    a = [P(t, ro, Z_TOP) for t in ths]
    a2 = [P(t, ro - 0.5, Z_TOP + 0.4) for t in ths]
    b = [P(t, ri, Z_TOP + 0.4) for t in ths]
    c = [P(t, ri, Z_TOP - 6) for t in ths]
    tris = []
    G.strip(tris, a, a2)
    G.strip(tris, a2, b)
    G.add("cup_rim", 5, tris)
    t2 = []
    G.strip(t2, b, c)
    G.cap_fan(t2, c, (CU, VB, Z_TOP - 6))
    G.add("cup_bore", 1, t2)
    # panel seams: modelled grooves where the modules meet (thin dark rings set into the skin)
    for nm, row in (("seam_base", 84.4), ("seam_drum1_lo", 73.4), ("seam_drum1_hi", 67.0),
                    ("seam_drum0", 50.4), ("seam_cup", 35.4)):
        z = zOf(row)
        G.lathe(nm, 3, lambda zz, th: Rcol(zz) - 0.25, z - 0.35, z + 0.35, step=0.35)
    # module flanges: thin machined lips standing proud at the drums' upper shoulders (the sprite's
    # bright row at the top of each drum is this lip catching the light)
    for nm, row in (("lip_drum0", 44.0), ("lip_drum1", 67.4), ("lip_base", 82.0)):
        z = zOf(row)
        G.lathe(nm, 6, lambda zz, th: Rcol(zz) + 0.22, z - 0.3, z + 0.3, step=0.3)

    # ---- cup: two red-lit vent bays either side of the grey guide rail (south face) ----
    zv0 = zOf(34.6) + A * 8 * math.cos(0.6) / K
    zv1 = min(zOf(30.0) + A * 8 * math.cos(0.6) / K, Z_TOP - 0.8)
    # vent housings stand proud of the cup (a recess in the solid lathe was buried and never showed):
    # a dark frame, the louvred face (west lit red, east in shadow), louvre slats on it
    G.patch("cup_vent_bay_w", 1, Rcol, -0.86, -0.28, zv0 - 0.4, min(zv1 + 0.4, Z_TOP - 0.5), 0.3)
    G.patch("cup_vent_w", 70, Rcol, -0.80, -0.34, zv0, zv1, 0.45, glow=0.5)
    G.patch("cup_vent_bay_e", 1, Rcol, 0.20, 0.86, zv0 - 0.4, min(zv1 + 0.4, Z_TOP - 0.5), 0.3)
    G.patch("cup_vent_e", 67, Rcol, 0.26, 0.80, zv0, zv1, 0.45)
    for i in range(4):
        z = zv0 + (i + 0.6) * (zv1 - zv0) / 4.2
        G.patch(f"cup_louvre_w{i}", 67, Rcol, -0.80, -0.34, z - 0.18, z + 0.18, 0.55)
        G.patch(f"cup_louvre_e{i}", 66, Rcol, 0.26, 0.80, z - 0.18, z + 0.18, 0.55)
    # guide rail: a grey rib down the cup's south face, over the neck and the bell
    z0, z1 = zOf(44.8), Z_TOP - 0.2
    ax = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    G.obox("rail_cup", 6, (CU - 0.5, VB + 7.6, (zOf(35.2) + z1) / 2), ax, [1.4, 0.7, (z1 - zOf(35.2)) / 2], ch=0.3)
    G.obox("rail_neck", 4, (CU - 0.5, VB + 5.6, (z0 + zOf(35.2)) / 2), ax, [1.3, 2.1, (zOf(35.2) - z0) / 2], ch=0.3)
    G.obox("rail_foot", 6, (CU - 0.5, VB + 7.4, z0 + 0.6), ax, [1.6, 1.0, 0.6], ch=0.3)
    # ---- red lamps on the drums' lower south shoulders ----
    G.surf_box("lamp_drum0_housing", 70, Rcol, 0, zOf(52.6) + A * 6.6 / K, 4.2, 2.6, 0.9, ch=0.4)
    G.surf_box("lamp_drum0_lens", 71, Rcol, 0, zOf(52.3) + A * 6.6 / K, 3.0, 1.4, 1.25, ch=0.3, glow=0.6)
    G.surf_box("lamp_drum1_housing", 70, Rcol, 0, zOf(75.6) + A * 6.6 / K, 4.2, 2.6, 0.9, ch=0.4)
    G.surf_box("lamp_drum1_lens", 71, Rcol, 0, zOf(75.3) + A * 6.6 / K, 3.0, 1.4, 1.25, ch=0.3, glow=0.6)
    # ---- bolt heads on the shaft's east flank (col 17) and a cable duct between them ----
    for i, row in enumerate((57.2, 59.4, 60.6, 62.4)):
        G.surf_box(f"shaft_bolt{i}", 5, Rcol, 1.18, zOf(row) + A * 6 * math.cos(1.18) / K, 1.0, 0.8, 0.7, ch=0.25)
    G.patch("shaft_duct", 3, Rcol, 0.98, 1.36, zOf(63.4), zOf(55.6), 0.35)
    # ---- base: access hatch on the south-west face, recessed in a frame ----
    # (a raised, bolted-on door: recessed into the solid drum it was buried and never showed)
    z0 = zOf(92.4) + A * 8 * math.cos(0.9) / K
    z1 = zOf(85.8) + A * 8 * math.cos(0.9) / K
    G.patch("hatch_frame", 66, Rcol, -1.48, -0.28, z0 - 0.5, z1 + 0.5, 0.3)
    G.patch("hatch_door", 67, Rcol, -1.40, -0.46, z0, z1, 0.42)
    G.patch("hatch_jamb", 16, Rcol, -0.46, -0.32, z0, z1, 0.36)
    G.surf_box("hatch_handle", 69, Rcol, -0.95, (z0 + z1) / 2, 0.6, 1.6, 0.9)
    # foot flange: the bolted ring where the tower meets its pad
    G.lathe("foot_flange", 3, lambda z, th: Rbase(z, th) + 0.3, 0, 0.9, step=0.45)
    # anchor bolts round the flange (machined detail at the foot)
    for k in range(10):
        th = (k + 0.5) * 2 * math.pi / 10
        G.surf_box(f"anchor{k}", 5, lambda z, th=th: Rbase(z, th) + 0.25, th, 0.55, 0.8, 0.7, 0.5, ch=0.2)


# ---- the head (newshc-77), per frame ------------------------------------------------------------
HEAD = {
    77: dict(lift=6, open=0, glow=1), 79: dict(lift=3, open=0, glow=112), 81: dict(lift=1, open=0, glow=114),
    83: dict(lift=0, open=0, glow=118), 85: dict(lift=0, open=1, glow=118), 87: dict(lift=0, open=2, glow=114),
    89: dict(lift=0, open=3, glow=1),
}
RB = 7.85
ZC0 = zOf(14.85)
NOZ_EL = math.radians(38)


def head(G, frame):
    H = HEAD[frame]
    zc = ZC0 + H["lift"] / K
    c = (CU, VB, zc)
    # neck: a machined ram that slides out of the cup's bore, a guide collar at its foot
    G.lathe("head_neck", 4, lambda z, th: 4.3, zc - 15.6, zc - 3, step=4.2, n=32)
    G.lathe("head_collar", 7, lambda z, th: 6.0 - 0.5 * max(0.0, z - (zc - 16.6)), min(Z_TOP - 4, zc - 22), zc - 15.6,
            step=0.5, cap1=True)
    G.lathe("head_neck_ring", 3, lambda z, th: 4.6, zc - 12.4, zc - 11.6, step=0.4)
    # ball
    G.sphere_patch("ball", 8, c, RB, -0.15, math.pi / 2, -math.pi, math.pi, 0)
    G.sphere_patch("ball_low", 5, c, RB - 0.25, -math.pi / 2, -0.1, -math.pi, math.pi, 0)
    G.sphere_patch("ball_seam", 5, c, RB + 0.05, 0.05, 0.11, -math.pi, math.pi, 0.3)
    # red fuel line over the crown and down the front meridian, under the nozzle
    G.sphere_patch("fuel_line_front", 73, c, RB + 0.35, 0.07, 0.62, -0.13, 0.13, 0.45)
    G.sphere_patch("fuel_line_crown", 73, c, RB + 0.35, 0.95, 2.4, -0.13, 0.13, 0.45)
    # flame nozzle: a stubby barrel with a flared, ribbed muzzle on the upper front; bore dark or lit
    d = (0, math.cos(NOZ_EL), math.sin(NOZ_EL))
    p0 = add(c, mul(d, RB - 1.2))   # the barrel stands proud of the ball: its bore opens clear of it
    p1 = G.tube("nozzle_barrel", 5, p0, d, 2.6, 2.9, 2.6, n=24, cap1=False)
    G.tube("nozzle_ring", 6, add(p0, mul(d, 1.2)), d, 0.45, 3.05, 3.05, n=24, cap0=False, cap1=False)
    # flared muzzle bell with a rolled, heat-scorched lip (pal 2): reads as a flame nozzle tip
    pm = G.tube("nozzle_muzzle", 2, p1, d, 0.45, 2.6, 3.1, n=24, cap0=False, cap1=False)
    G.tube("nozzle_lip", 2, pm, d, 0.25, 3.1, 3.3, n=24, cap0=False, cap1=False)
    G.tube("nozzle_lip_face", 1, add(pm, mul(d, 0.25)), d, 0.0, 3.3, 2.2, n=24, cap0=False, cap1=False)
    G.tube("nozzle_bore", 1, add(p1, mul(d, 0.69)), mul(d, -1), 1.6, 2.2, 2.0, n=24, cap0=False, cap1=False)
    g = H["glow"]
    G.tube("nozzle_core", g, add(p1, mul(d, -0.5)), d, 0.15, 2.25, 2.25, n=24, glow=0.0 if g == 1 else 1.0)
    G.tube("pilot_igniter", 72, add(c, add(mul(d, RB + 0.2), (0, 0, -2.4))), d, 1.6, 0.55, 0.45, n=10)
    # the hood: two clamshell halves round the lower ball, seamed at the front; they slide apart
    # on rear guide posts (frames 85-89)
    RHf = pchip([-10.9, -10.2, -9.2, -8.0, 1.0], [6.2, 7.7, 8.05, 8.05, 8.05])
    for side in (-1, 1):
        hinge = (CU + side * 6.6, VB - 5.2)

        def xf(p, side=side):
            cl = lambda x: min(1.0, max(0.0, x))  # noqa: E731
            fl = 0.3 * H["open"] * cl((zc - 6.5 - p[2]) / 3.5)
            up = 0.95 * H["open"] * cl((p[2] - (zc - 7)) / 4)
            return (p[0] + side * (0.88 * H["open"] + fl), p[1], p[2] + up)
        th0, th1 = (0.04, math.pi) if side > 0 else (-math.pi, -0.04)
        nt = 18

        def zTop(th):
            return -4.4 + 1.7 * math.sin(th) ** 2

        def pt(dz, th, dr, xf=xf):
            rr = RHf(dz) + dr
            return xf((c[0] + rr * math.sin(th), c[1] + rr * math.cos(th), zc + dz))
        nl = 9
        rows, rows_in = [], []
        for i in range(nl + 1):
            ro, ri = [], []
            for k in range(nt + 1):
                th = th0 + (th1 - th0) * k / nt
                dz = zTop(th) + (-10.9 - zTop(th)) * i / nl
                ro.append(pt(dz, th, 0))
                ri.append(pt(dz, th, -0.5))
            rows.append(ro)
            rows_in.append(ri)
        tris = []
        for i in range(nl):
            for k in range(nt):
                tris.append([rows[i][k], rows[i][k + 1], rows[i + 1][k + 1]])
                tris.append([rows[i][k], rows[i + 1][k + 1], rows[i + 1][k]])
                tris.append([rows_in[i][k], rows_in[i + 1][k + 1], rows_in[i][k + 1]])
                tris.append([rows_in[i][k], rows_in[i + 1][k], rows_in[i + 1][k + 1]])

        def wall(a, b):
            for k in range(len(a) - 1):
                tris.append([a[k], a[k + 1], b[k + 1]])
                tris.append([a[k], b[k + 1], b[k]])
        wall(rows[0], rows_in[0])
        wall(rows[nl], rows_in[nl])
        j = 0 if side > 0 else nt
        wall([r[j] for r in rows], [r[j] for r in rows_in])
        tag = "e" if side > 0 else "w"
        G.add("hood_" + tag, 71, tris)
        # bottom lip of the half, closing in to the neck
        lt, o, i2 = [], [], []
        for k in range(nt + 1):
            th = th0 + (th1 - th0) * k / nt
            o.append(pt(-10.9, th, -0.25))
            i2.append(xf((c[0] + 4.1 * math.sin(th), c[1] + 4.1 * math.cos(th), zc - 11.0)))
        for k in range(nt):
            lt.append([o[k], o[k + 1], i2[k + 1]])
            lt.append([o[k], i2[k + 1], i2[k]])
        G.add("hood_lip_" + tag, 66, lt)
        # stiffening flutes, three per half
        for f in (0.55, 1.25, 2.0):
            th = side * f
            ft, a0, a1 = [], [], []
            for i in range(7):
                dz = zTop(th) + (-9.6 - zTop(th)) * i / 6
                a0.append(pt(dz, th - 0.05, 0.12))
                a1.append(pt(dz, th + 0.05, 0.12))
            for i in range(6):
                ft.append([a0[i], a1[i], a1[i + 1]])
                ft.append([a0[i], a1[i + 1], a0[i + 1]])
            G.add(f"hood_flute_{tag}{f}", 69, ft, smooth=False)
        G.tube("hood_guide_" + tag, 3, (hinge[0], hinge[1], zc - 9.5), (0, 0, 1), 7.5, 0.7, 0.7, n=10)
    # flame chamber behind the hood's front seam (shows when it opens)
    G.lathe("chamber", 16, lambda z, th: 7.25, zc - 10.2, zc - 3.6, step=6.6, n=40)
    if H["open"]:
        # the chamber's skirt: shows below the parted hood halves (sprite row 27, 67)
        G.lathe("chamber_skirt", 67, lambda z, th: 7.25 - 0.25 * ((zc - 10.2) - z), zc - 13.4, zc - 10.2, step=0.8)
    G.lathe("chamber_lip", 66, lambda z, th: 7.3, zc - 4.4, zc - 3.6, step=0.4)


def wreck(G):
    """Frame 91: the head is gone. What is left: the ram's stub in the cup's bore, its torn guide
    collar standing on it and a bent feed rod sticking up out of it (sprite col 13, rows 16-20).
    The collar's front is blown away: the art looks into it (dark rows 24-27) and sees the torn
    back wall, its jagged top highest behind the rod (row 21, cols 12-15), lower to the west.
    The torn top is solved per azimuth so the art camera lands it on those rows."""
    cu, R0, R1 = 12.5, 4.4, 3.6
    rows = pchip([7.6, 8.5, 9.5, 10.5, 11.0, 12.0, 15.5, 16.3, 17.2], [26.4, 25.2, 24.2, 22.4, 22.4, 21.3, 21.2, 23.4, 24.8])
    n = 36
    ths = [2 * math.pi * k / n for k in range(n)]

    def zb(t):
        return 70.1 - 0.7 * max(0.0, (abs(math.sin(t)) - 0.9) / 0.1)

    def top(k, t):
        u = cu + R0 * math.sin(t)
        full = (VB + A * R0 * math.cos(t) - rows(u)) / K
        a = abs(math.atan2(math.sin(t), math.cos(t)))      # 0 = south (front)
        f = min(1.0, max(0.0, (a - 0.8) / 0.8))           # the front is torn away
        f = f * f * (3 - 2 * f)
        jag = (0.35 if k % 2 else -0.2) * f
        return zb(t) + f * (full - zb(t)) + jag
    jag = [max(zb(t), top(k, t)) for k, t in enumerate(ths)]
    outer_b = [P(t, R0, zb(t), cu) for t in ths]
    outer_t = [P(t, R0, jag[k], cu) for k, t in enumerate(ths)]
    inner_t = [P(t, R1, jag[k] - 0.25, cu) for k, t in enumerate(ths)]
    inner_b = [P(t, R1, zb(t) + 0.1, cu) for t in ths]
    tris = []
    Geo.strip(tris, outer_b, outer_t)
    G.add("stump", 5, tris)
    t2 = []
    Geo.strip(t2, outer_t, inner_t)
    G.add("stump_rim", 3, t2, smooth=False)
    t3 = []
    Geo.strip(t3, inner_t, inner_b)
    G.add("stump_in", 1, [[q[0], q[2], q[1]] for q in t3])
    t4 = []
    Geo.strip(t4, inner_b, outer_b)
    G.add("stump_foot", 2, t4, smooth=False)
    # the ram's stub below it, in the bore (its top dark: burnt)
    G.lathe("ram_stub", 3, lambda z, th: 3.6, Z_TOP - 3, 68.5, step=1.0, n=24, cu=cu, cap1=True)
    for k, th in enumerate((-1.3, 1.3)):  # lugs: the collar rests on them
        G.tube(f"lug{k}", 2, P(th, 3.9, 68.4, cu), (0, 0, 1), 1.4, 0.45, 0.45, n=8)
    # torn hood plates: two scraps of the clamshell still bolted to the collar's lugs, bent in, and a
    # snapped cable loop; they stand inside the collar's footprint (the sprite's dark interior)
    for k, (uu, lean, hh, pal) in enumerate(((10.9, 0.3, 2.0, 3), (14.3, -0.35, 1.6, 5), (12.0, 0.1, 1.0, 4))):
        c_, s_ = math.cos(lean), math.sin(lean)
        axl = [(c_, 0, s_), (0, 1, 0), (-s_, 0, c_)]
        G.obox(f"torn_plate{k}", pal, (uu, VB - 2.2 - k * 0.5, 70.9 + hh), axl, [0.3, 1.1, hh], ch=0.12)
    G.tube("cable_loop_a", 2, (12.4, VB - 1.2, 70.6), (0.2, -0.1, 1.0), 2.4, 0.3, 0.3, n=8)
    G.tube("cable_loop_b", 2, (12.9, VB - 1.0, 73.0), (0.6, 0.0, 0.5), 1.8, 0.3, 0.28, n=8)
    # the bent feed rod
    mid = G.tube("rod_lo", 7, (15.0, VB - 1.0, 73.0), (-0.5, 1.0, 4.8), 4.6, 0.55, 0.5, n=10)
    kink = (13.65, VB, 78.9)
    G.tube("rod_kink", 7, mid, sub(kink, mid), math.dist(kink, mid), 0.5, 0.47, n=10)
    G.tube("rod_hi", 7, kink, (0.0, 0.0, 1.0), 81.6 - kink[2], 0.47, 0.42, n=10)


def build(frame=None, with_body=True):
    G = Geo()
    if with_body:
        body(G)
    if frame == 91:
        wreck(G)
    elif frame is not None:
        head(G, frame)
    return G.parts
