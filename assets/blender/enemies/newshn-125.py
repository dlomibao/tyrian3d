"""newshn-125 / newshn-15 / newshn-13, design A: GYGES's (level 2.2) tentacle-arm shell segments.

WHAT IT IS: one segment of GYGES's two swinging segmented arms. Each arm is a chain of blue spiral
shells (root to tip: 2 large newshn-13, 6 medium newshn-15, 5 small newshn-125) ending in a claw
(assembly-newshn-201 left, assembly-newshn-39 right). Every segment weaves on its own, 4 ticks out of
phase with the next, so the chain swings like a tentacle. They hang and swing in the air while the
scroll is stopped for the boss: the 'ground' layer is only the draw layer (not lying on the ground,
not a horned eye creature). So each segment is a free-floating spiral shell with a round, closed,
plain underside.

Design A leads with the blueprint geometry (tyrian-scratch/e2-enemies-2/newshn-125/blueprint/
model.js, ported here 1:1), built cross-section first, the way a gastropod shell grows:
  - The suture S(phi) is a spiral about the apex: pchip through the J traced from the sprite's dark
    groove pixels (rim at the top, down the right, curling under the spire at the bottom), then a log
    spiral inward (0.38 of the radius per turn), so about 2 whorls lie inside the J.
  - SPIRE: the suture climbs `step` (0.92 px) per turn, so the spire is 2-2.5 STEPPED whorls, not a
    smooth cone. Each spire whorl's section: a rounded riser `rise` (0.42 px) within `risew` (0.45 px)
    of its outer suture (the overlap step: the older suture tucks under it), a gentle climb inward,
    and a `channel` dip just before it runs under the next whorl's riser. Apex at sprite (10.5, 11.8).
  - BODY WHORL: a convex coil rising out of the J to a crest 0.4 of the way across (bulge 1.05 px),
    held under one convex crown (CAP_*: (1 - s^1.7)^0.6 of the distance s from a centre over the
    crescent to the rim, 5.85 px) faded in across the strip, so the shoulder peaks ~5.6 px over the
    crescent and rolls off to the rim in every direction, steepest to the left and the bottom. The
    crown starts curving from its centre, below the old plateau, so the side, front and rear
    elevations read as a domed coil under a stepped spire, not a flat-topped bun with the spire as
    a nub on it. The sprite's pale crescent (indices 59-61) is sheen on that coil crest.
  - FLANK (where the suture runs down the outer wall to the aperture at the top rim): an overlap
    step. The upper whorl's edge is a rounded lip LIP (0.42 px) proud of the wall below, going
    vertical at its foot over LIP_W (0.13 px); the wall below is the same envelope scaled down to
    start LIP under the lip and still meet the rim at 0 (no trough). The lip rises out of the rim
    at the aperture and hands over to the top suture's groove past ~0.2 turns (newshn-13, whose
    strip under the lip's end is widest, sooner: SPEC lip_fade, so the lip tucks into the groove
    instead of overhanging a flat lit shelf). The dark line there is the riser's foot in the suture
    colour, not a band painted on the wall.
  - RIM: the sprite's inner mask (D74), 48 radii about the footprint centre, so the top view matches
    the sprite row by row.
  - UNDERSIDE: a plain round dome 1.9 px below the rim, closed. The whole mesh is one closed
    2-manifold surface (no pinholes).
Colours: the sprite's own index per region: body = shell median, the suture band = J median (a thin
band on the channel floor only; the riser's shadow does the rest), underside = a ramp step darker.
Satin-gloss organic shell. Outline shell (D51/D90) from a crease-free proxy held under the model
(outline_source, the batch-1 fix that stopped the J and the whorl steps drawing as a black ink
spiral; inside the rim band it may fall toward the far side no steeper than 0.8, so it has no faces
turned from the tilted game camera there: the game's ink is the shell's back faces shifted up the
screen, and those showed as the black wedge at the flank lip's foot and the dashes along the J),
closed underneath along the round underside, then every shell vertex less than
SHELL_INSIDE (0.12 px) under the model pulled down to that depth (hold_inside: the shell no longer
shows through at the suture's end or along the rim seam). About 3.8-4k triangles per size.

    blender --background --factory-startup --python enemies/newshn-125.py [-- newshn-125 newshn-15 newshn-13] [--renders dir]
Exports public/models/enemies/<name>.glb and the spriteModels entry for each size.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
BLUEPRINT = ({"newshn-125":{"scale_k":1.01,"centre_px":[11.5,14],"rim_radius_48_px":[6.61,6.669,6.725,6.785,6.79,6.934,7.054,7.108,7.03,6.969,7.02,7.068,7.121,7.068,7.02,6.969,7.03,7.108,7.054,6.934,6.79,6.785,6.725,6.669,6.61,6.669,6.725,6.785,6.79,6.934,7.054,7.108,7.03,6.969,7.02,7.068,7.121,7.068,7.02,6.969,7.03,7.108,7.054,6.934,6.79,6.785,6.725,6.669],"params_px":{"h0":4.292,"step":0.929,"rise":0.424,"risew":0.454,"channel":0.101,"bulge":1.06,"crest":0.4,"recess":0.404,"turn":0.38,"capTurns":2.5,"dome":6.666,"under":1.919,"line":0.283}},"newshn-15":{"scale_k":1.143,"centre_px":[11.5,14],"rim_radius_48_px":[7.587,7.623,7.675,7.753,7.787,7.835,7.823,7.795,7.841,7.896,8.022,8.043,8.091,8.043,8.022,7.896,7.841,7.795,7.823,7.835,7.787,7.753,7.675,7.623,7.587,7.623,7.675,7.753,7.787,7.835,7.823,7.795,7.841,7.896,8.022,8.043,8.091,8.043,8.022,7.896,7.841,7.795,7.823,7.835,7.787,7.753,7.675,7.623],"params_px":{"h0":4.857,"step":1.051,"rise":0.48,"risew":0.514,"channel":0.114,"bulge":1.2,"crest":0.4,"recess":0.457,"turn":0.38,"capTurns":2.5,"dome":7.542,"under":2.171,"line":0.32}},"newshn-13":{"scale_k":1.317,"centre_px":[11.5,13.5],"rim_radius_48_px":[8.547,8.618,8.722,8.829,8.871,8.944,8.987,9.026,9.092,9.226,9.391,9.48,9.514,9.48,9.391,9.226,9.092,9.026,8.987,8.944,8.871,8.829,8.722,8.618,8.547,8.618,8.722,8.829,8.871,8.944,8.987,9.026,9.092,9.226,9.391,9.48,9.514,9.48,9.391,9.226,9.092,9.026,8.987,8.944,8.871,8.829,8.722,8.618],"params_px":{"h0":5.595,"step":1.211,"rise":0.553,"risew":0.592,"channel":0.132,"bulge":1.382,"crest":0.4,"recess":0.527,"turn":0.38,"capTurns":2.5,"dome":8.689,"under":2.501,"line":0.369}}})
PX = 1 / 12
TAU = 2 * math.pi

# Per size: the sprite's apex and visible J suture (sprite EDGE px), palette indices. The rim radii,
# footprint centre and size-scaled shape parameters come from the blueprint (fitted to each sprite's
# inner mask there).
SPEC = {
    "newshn-125": dict(
        apex=(10.5, 11.8),
        suture=[(9.4, 7.3), (11.0, 7.45), (12.3, 7.8), (13.05, 8.6), (13.4, 9.6), (13.5, 10.6), (13.55, 11.7),
                (13.5, 12.8), (13.1, 13.8), (12.3, 14.6), (11.2, 15.3), (10.3, 15.6)],
        idx=dict(body=56, suture=53, under=53),
    ),
    "newshn-15": dict(
        apex=(10.3, 11.5),
        suture=[(9.0, 6.3), (10.8, 6.45), (12.3, 6.9), (13.3, 7.8), (13.8, 8.8), (14.3, 9.9), (14.5, 11.0),
                (14.5, 12.3), (14.1, 13.4), (13.0, 14.3), (11.6, 15.0), (10.0, 15.5), (9.2, 15.5)],
        idx=dict(body=55, suture=50, under=52),
    ),
    "newshn-13": dict(
        apex=(9.8, 10.7),
        suture=[(11.5, 4.6), (13.0, 5.6), (13.7, 6.8), (14.2, 8.0), (14.6, 9.3), (14.7, 10.5), (14.6, 11.7),
                (14.2, 12.8), (13.4, 13.8), (12.3, 14.6), (11.0, 15.2), (9.8, 15.6)],
        idx=dict(body=53, suture=49, under=51),
        # the widest strip under the lip's end: handed over sooner, so the lip tucks into the groove
        # instead of overhanging a flat shelf (a lit scoop in the side view)
        lip_fade=(0.08, 0.10),
    ),
}
FLANK_END = 0.28   # turns: the flank lip has handed over to the top suture's groove by here
FLANK_DENSE = 0.0  # turns from the aperture built at 4x column density
LIP = 0.42  # px (x size): the flank overlap step, the upper whorl's edge proud of the lower one
LIP_W = 0.13  # px (x size): its riser width (a rounded lip, vertical at the foot)
# the body whorl is held under one convex crown (Shell.crown): CAP_Z (1 - s^CAP_P)^CAP_Q, s the
# distance from its centre over the crescent to the rim along that direction, so the coil shoulder
# peaks ~5.6 px over the crescent and rolls off to the rim every way (the elevations read as a
# domed coil, not a flat-topped bun); the spire stands above it
CAP_D = (4.2, 3.4)   # crown centre from the apex (px, x size): over the crescent
CAP_Z = 5.85        # crown height (px, x size) before the soft min (the shoulder peaks ~5.6)
CAP_P, CAP_Q = 1.7, 0.6   # crown profile (1 - s^P)^Q, s = distance from the centre / to the rim
CAP_SOFT, CAP_T = 0.2, 0.35   # soft-min width (px) and the share of the strip it fades in over
COLS = 48  # columns per turn
SHARP_DEG = 89  # only true corners split normals
RISER_FLANK = 0.34  # px (x size): width of the top suture's riser (past the flank)
SHELL_MAT = dict(metallic=0.1, roughness=0.32)   # satin-gloss shell: the crescent is sheen from the game light


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
        lo, hi = 0, n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        t = (x - xs[lo]) / h[lo]
        return ((2 * t ** 3 - 3 * t * t + 1) * ys[lo] + (t ** 3 - 2 * t * t + t) * h[lo] * m[lo]
                + (-2 * t ** 3 + 3 * t * t) * ys[lo + 1] + (t ** 3 - t * t) * h[lo] * m[lo + 1])
    return f


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def lip_w(n, fade=(0.15, 0.12)):
    """Share of the flank lip at n turns from the aperture: it rises out of the rim, holds down the
    flank and hands over to the top suture's groove (from fade[0] turns, over fade[1])."""
    return smooth(n / 0.06) * (1 - smooth((n - fade[0]) / fade[1]))


def softmin(a, b, k):
    return min(a, b) - k * math.log1p(math.exp(-abs(a - b) / k))


class Shell:
    """The blueprint's point model (model.js Shell), in sprite px."""

    def __init__(self, name, bp, overrides=None):
        s = SPEC[name]
        self.name, self.s = name, s
        self.cx, self.cy = bp["centre_px"]
        self.ax, self.ay = s["apex"]
        self.knots = bp["rim_radius_48_px"]
        self.k = bp["scale_k"]
        self.P = dict(bp["params_px"])
        for key, v in (overrides or {}).items():
            self.P[key] = v if key in ("turn", "crest", "capTurns") else v * self.k
        phis, rs = [], []
        for u, v in s["suture"]:
            a = math.atan2(v - self.ay, u - self.ax)
            if phis:
                while a < phis[-1] - math.pi:
                    a += TAU
                while a > phis[-1] + math.pi:
                    a -= TAU
            phis.append(a)
            rs.append(math.hypot(u - self.ax, v - self.ay))
        rs[0] = self.rim_from_apex(phis[0])
        self.phi0, self.phi_vis = phis[0], phis[-1]
        c = math.log(1 / self.P["turn"]) / TAU
        rl, pl = rs[-1], phis[-1]
        x = 0.6
        while rl * math.exp(-c * x) > 0.5:
            phis.append(pl + x)
            rs.append(rl * math.exp(-c * x))
            x += 0.6
        phis.append(phis[-1] + 1.2)
        rs.append(0.0)
        self.phi_end = phis[-1]
        self.R = pchip(phis, rs)
        self.cache = {}
        self.ccx, self.ccy = self.ax + CAP_D[0] * self.k, self.ay + CAP_D[1] * self.k
        self.crim = []
        for i in range(360):
            a = TAU * i / 360
            lo, hi = 0.0, 25.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if self.inside(self.ccx + mid * math.cos(a), self.ccy + mid * math.sin(a)):
                    lo = mid
                else:
                    hi = mid
            self.crim.append(lo)

    def crown(self, u, v):
        """The body whorl's convex crown under sprite point (u, v) (px)."""
        du, dv = u - self.ccx, v - self.ccy
        x = (math.atan2(dv, du) % TAU) / TAU * 360
        i = int(x)
        f = x - i
        rr = self.crim[i % 360] * (1 - f) + self.crim[(i + 1) % 360] * f
        s = min(1.0, math.hypot(du, dv) / max(rr, 1e-6))
        return self.k * CAP_Z * max(0.0, 1 - s ** CAP_P) ** CAP_Q

    def rim_r(self, theta):
        r = self.knots
        n = len(r)
        x = ((theta % TAU) + TAU) % TAU / TAU * n
        i = int(math.floor(x))
        t = x - i
        p0, p1, p2, p3 = r[(i - 1) % n], r[i % n], r[(i + 1) % n], r[(i + 2) % n]
        return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                      + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)

    def inside(self, u, v):
        du, dv = u - self.cx, v - self.cy
        return math.hypot(du, dv) < self.rim_r(math.atan2(dv, du))

    def rim_from_apex(self, phi):
        c, s_ = math.cos(phi), math.sin(phi)
        lo, hi = 0.0, 20.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if self.inside(self.ax + c * mid, self.ay + s_ * mid):
                lo = mid
            else:
                hi = mid
        return lo

    def lip_w(self, n):
        return lip_w(n, self.s.get("lip_fade", (0.15, 0.12)))

    def suture(self, phi):
        return 0.0 if phi >= self.phi_end else self.R(phi)

    def point(self, phi, r):
        return self.ax + r * math.cos(phi), self.ay + r * math.sin(phi)

    def turns(self, phi):
        return (min(phi, self.phi_end) - self.phi0) / TAU

    def hs_base(self, n):
        P = self.P
        cap = P["capTurns"]
        m = n if n <= cap else cap + 0.25 * (1 - math.exp(-(n - cap) / 0.25))
        return P["h0"] + P["step"] * m

    def rho(self, phi, r):
        u, v = self.point(phi, r)
        du, dv = u - self.cx, v - self.cy
        return min(1.0, math.hypot(du, dv) / self.rim_r(math.atan2(dv, du)))

    def fall(self, zc, phi, rc, r):
        a, b = self.rho(phi, rc), self.rho(phi, r)
        if b <= a:
            return zc
        return zc * math.sqrt(max(0.0, 1 - b * b) / max(1e-4, 1 - a * a))

    def body_at(self, phi, n_in, rin, rim, r):
        """Body whorl section: convex coil out of the J to a crest, then the dome shoulder to the rim."""
        P = self.P
        w = rim - rin
        hin = self.hs(n_in) if rin > 1e-9 else self.hs(self.turns(self.phi_end))
        if w < 1e-6:
            return hin
        t = (r - rin) / w
        bl = P["bulge"] * (1 - 0.55 * smooth((n_in - 0.6) / 0.3))
        tc = P["crest"]
        rcr = rin + tc * w
        rh = self.rho(phi, rcr)
        zc = min(hin + bl * min(1.0, w / (2.6 * self.k)),
                 P["dome"] * math.sqrt(max(0.0, 1 - rh * rh)) + 0.3 * self.k)
        if zc < hin + 0.05:
            z = self.fall(hin, phi, rin, r)
        elif t <= tc:
            z = hin + (zc - hin) * math.sin(math.pi / 2 * t / tc)
        else:
            z = self.fall(zc, phi, rcr, r)
        # the crown: the whole body whorl held under one convex dome peaking over the crescent and
        # rolling off to the rim in every direction (the elevations read as a coiled shell, not a
        # flat-topped bun); faded in across the strip so the inner suture keeps its height
        cap = self.crown(*self.point(phi, r))
        if cap < z + 0.6:
            kk = CAP_SOFT * self.k * min(1.0, z / (1.5 * self.k)) + 1e-4
            z = z + (softmin(z, cap, kk) - z) * smooth(t / CAP_T)
        # FLANK: where the suture comes down the outer wall to the aperture, the strip outside it is
        # the wall below the upper whorl's lip: the same envelope, scaled down so it starts LIP under
        # the lip's top at the suture and still meets the rim at 0. No trough, no slit.
        if n_in < FLANK_END and rin > 1e-9:
            wb = 1 - smooth((n_in - 0.16) / 0.12)
            if wb > 0:
                e0 = self.env(n_in, rin)
                zf = self.env(n_in, r) * (hin / e0) if e0 > 1e-6 else 0.0
                z = z + (zf - z) * wb
        return z

    def env(self, n, r):
        phi = self.phi0 + n * TAU
        return self.body_at(phi, n + 1, self.suture(phi + TAU), self.rim_from_apex(phi), r)

    def hs(self, n):
        n = max(0.0, n)
        key = round(n * 1e9)
        if key in self.cache:
            return self.cache[key]
        base = self.hs_base(n)
        if n < 0.6:
            # down the flank the suture sits LIP under the upper whorl's lip (fading out into the rim at
            # the aperture); past it, `recess` down in the top suture's groove
            drop = LIP * self.k * self.lip_w(n) + self.P["recess"] * smooth((n - 0.18) / 0.15)
            ev = self.env(n, self.suture(self.phi0 + n * TAU)) - drop
            m = softmin(base, ev, 0.12)
            base = max(0.0, m + (base - m) * smooth((n - 0.3) / 0.3))
        self.cache[key] = base
        return base

    def height(self, t, rin, rout, n_in, n_out, phi):
        """Height across a whorl strip (t 0 at its inner suture .. 1 at its outer edge)."""
        P = self.P
        hin = self.hs(n_in) if rin > 1e-9 else self.hs(self.turns(self.phi_end))
        w = rout - rin
        if w < 1e-6:
            return hin
        if n_out is None:
            return self.body_at(phi, n_in, rin, rout, rin + t * w)
        hout = self.hs(n_out)
        # SPIRE WHORL: the riser (overlap step) out of its outer suture, the climb, the channel dip
        x = (1 - t) * w
        rw = min(P["risew"], 0.45 * w)
        rise = min(P["rise"], 0.6 * (hin - hout))
        g = rise * math.sin(math.pi / 2 * min(1.0, x / rw))
        d = t * w
        bump = math.sin(math.pi * d / (0.4 * self.k)) if d < 0.4 * self.k else 0.0
        zs = hout + g + (hin - hout - rise) * (x / w) ** 0.85 - P["channel"] * min(1.0, w / 1.2) * bump
        # near the aperture this strip is the outer wall: blend to the coil falling to the rim
        e = smooth(n_out / 0.45)
        if e < 1:
            rr = rin + t * w
            lw = self.lip_w(n_out)
            tr = self.riser_t(n_out, w)
            q = clamp01((t - tr) / max(1e-6, 1 - tr))
            # the flank lip: a rounded edge going vertical at its foot (lit top over a shadowed
            # riser); past the flank, the top suture's softer riser
            q = (1 - math.sqrt(max(0.0, 1 - q * q))) * lw + smooth(q) * (1 - lw)
            zb = self.env(n_out, rr) + (hout - self.env(n_out, rout)) * q
            zs = zb + (zs - zb) * e
        return zs

    def riser_t(self, n_out, w):
        """Where the outer-wall riser starts across a strip of width w (t), by turns from the aperture."""
        lw = self.lip_w(n_out)
        width = (LIP_W * lw + RISER_FLANK * (1 - lw)) * self.k
        return max(0.0, 1 - width / w) if w > 1e-6 else 0.0

    def under_z(self, u, v):
        """The round underside dome (z <= 0) under sprite point (u, v)."""
        du, dv = u - self.cx, v - self.cy
        rho = min(1.0, math.hypot(du, dv) / self.rim_r(math.atan2(dv, du)))
        return -self.P["under"] * math.sqrt(max(0.0, 1 - rho * rho))


def bl(u, v, z):
    return Vector(((u - 12) * PX, (14 - v) * PX, z * PX))


def build_mesh(sh, name, mats):
    """model.js build(): a single spiral strip from the aperture to the apex (COLS columns per turn), the
    rows crowded at the suture band and at the riser, columns zipped together, then the underside."""
    P = sh.P
    # columns per turn: COLS even, 4x denser over the first FLANK_DENSE turns (where the suture runs
    # down the flank to the aperture and the strips are narrow), the same offsets every turn so the
    # suture vertices of one turn are the outer edge of the next
    offs = sorted(set([round(TAU * i / COLS, 9) for i in range(COLS)]
                      + [round(TAU * FLANK_DENSE * i / 48, 9) for i in range(48 if FLANK_DENSE else 0)]))
    N = len(offs)
    phis = []
    k = 0
    while not phis or phis[-1] < sh.phi_end + TAU:
        for o in offs:
            phis.append(sh.phi0 + k * TAU + o)
            if phis[-1] >= sh.phi_end + TAU:
                break
        k += 1
    ncol = len(phis)
    rims = [sh.rim_from_apex(p) for p in phis]
    sut = [sh.suture(p) for p in phis]
    sut[0] = rims[0]

    def rout(j):
        return sut[j - N] if j >= N else rims[j]

    bm = bmesh.new()
    verts = {}

    def V(key, phi, r, z):
        if key not in verts:
            u, v = sh.point(phi, r)
            verts[key] = bm.verts.new(bl(u, v, z))
        return verts[key]

    NI = 5
    cols = []
    gis = []
    lips = []  # (riser start t, lip share) of the outer-wall riser per column (spire strips)
    for j in range(ncol):
        phi, rin, ro = phis[j], sut[j], rout(j)
        w = ro - rin
        vis = smooth((phi - sh.phi0) / 0.5) * smooth((sh.phi_vis - phi) / 0.5 + 0.2)
        gi = min(0.25, P["line"] * max(0.15, vis) / w) if w > 1e-6 else 0.0
        if j < N:  # down the flank the dark line is the lip's shadowed riser, not paint on the wall
            gi *= 1 - sh.lip_w(sh.turns(phi))
        gis.append(gi)
        n_out = sh.turns(phi - TAU) if j >= N else None
        lips.append((sh.riser_t(n_out, w), sh.lip_w(n_out)) if j >= N and n_out < 0.45 else (1.0, 0.0))
        ts = [0.0, gi * 0.5, gi]
        for i in range(1, NI + 1):
            x = i / (NI + 1)
            ts.append(gi + (1 - gi - 0.02) * (1 - (1 - x) ** 1.6))
        if j >= N:
            rwT = min(0.45, P["risew"] / w) if w > 1e-6 else 0.0
            rfT = min(0.45, RISER_FLANK * sh.k / w) if w > 1e-6 else 0.0
            for f in (0.15, 0.35, 0.6, 0.85):
                ts.append(1 - rwT * f)
            if lips[j][0] < 1:  # the flank lip's rounded edge and riser
                for f in (0.3, 0.6, 0.85, 1.0):
                    ts.append(1 - (1 - lips[j][0]) * f)
        else:
            ts += [0.985, 0.995]
        ts.append(1.0)
        srt = sorted(set(round(t * 1e6) / 1e6 for t in ts))
        uniq = [0.0]
        for t in srt[1:-1]:
            # the body whorl keeps every row (its strip is only a fraction of a px wide where the
            # suture meets the aperture: dropping rows there zipped the flank into a staircase)
            if (j < N and w > 0.02) or ((t - uniq[-1]) * w >= 0.03 and (1 - t) * w >= 0.03):
                uniq.append(t)
        uniq.append(1.0)
        col = []
        for i, t in enumerate(uniq):
            r = rin + t * w
            if i == 0:
                key = ("apex",) if rin <= 1e-9 else ("s", j)
            elif i == len(uniq) - 1:
                key = ("s", j - N) if j >= N else ("rim", j % N)
            else:
                key = ("b", j, i)
            if key[0] == "rim":
                z = 0.0
            else:
                z = sh.height(t, rin, ro, sh.turns(phi), sh.turns(phi - TAU) if j >= N else None, phi)
            col.append((V(key, phi, r, z), t))
        cols.append(col)

    MI = {"body": 0, "suture": 1, "under": 2}
    seen = set()

    def tri(a, b, c, kind):
        if a is b or b is c or a is c:
            return
        if ((a.co - b.co).length < 1e-7 or (b.co - c.co).length < 1e-7 or (a.co - c.co).length < 1e-7):
            return
        k = frozenset((a, b, c))
        if k in seen:
            return
        seen.add(k)
        try:
            f = bm.faces.new((a, b, c))
        except ValueError:
            return
        f.material_index = MI[kind]
        f.smooth = True

    for j in range(ncol - 1):
        A, B = cols[j], cols[j + 1]
        ia = ib = 0
        pm = (phis[j] + phis[j + 1]) / 2
        wA = rout(j) - sut[j]
        while ia < len(A) - 1 or ib < len(B) - 1:
            adv_a = ib >= len(B) - 1 or (ia < len(A) - 1 and A[ia + 1][1] <= B[ib + 1][1])
            tm = (A[ia][1] + A[ia + 1][1]) / 2 if adv_a else (B[ib][1] + B[ib + 1][1]) / 2
            kind = "body"
            # the suture band: the column's own band rows (at most a quarter of the strip, so a strip
            # narrowing into the aperture never turns dark right across)
            if tm < min(gis[j], gis[j + 1]) + 1e-6 and sh.phi0 + 0.05 < pm < sh.phi_vis + 0.1:
                kind = "suture"
            # the flank lip's riser foot (the shadowed face under the lit edge) in the suture colour
            lw = min(lips[j][1], lips[j + 1][1])
            if lw > 0.35 and tm > max(lips[j][0], lips[j + 1][0]) + 0.6 * (1 - max(lips[j][0], lips[j + 1][0])):
                kind = "suture"
            if adv_a:
                tri(A[ia][0], A[ia + 1][0], B[ib][0], kind)
                ia += 1
            else:
                tri(A[ia][0], B[ib + 1][0], B[ib][0], kind)
                ib += 1

    # round closed underside
    ring = [cols[j][-1][0] for j in range(N)]
    NR = 5
    rings = [ring]
    cxm, cym = (sh.cx - 12) * PX, (14 - sh.cy) * PX
    for i in range(1, NR + 1):
        a = i / NR * math.pi / 2
        s, z = math.cos(a), -P["under"] * math.sin(a) * PX
        if i == NR:
            pole = bm.verts.new(Vector((cxm, cym, z)))
            rings.append([pole] * N)
        else:
            rings.append([bm.verts.new(Vector((cxm + (p.co.x - cxm) * s, cym + (p.co.y - cym) * s, z)))
                          for p in ring])
    for i in range(NR):
        for j in range(N):
            a, b = rings[i][j], rings[i][(j + 1) % N]
            c, e = rings[i + 1][(j + 1) % N], rings[i + 1][j]
            tri(a, e, c, "under")
            tri(a, c, b, "under")

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    for _ in range(4):  # collapse the shortest edge of any sliver (apex): closed, no area left
        tiny = [f for f in bm.faces if f.calc_area() < 1e-7]
        if not tiny:
            break
        bmesh.ops.collapse(bm, edges=[min(tiny[0].edges, key=lambda e: e.calc_length())])
        bm.verts.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    return obj


def outline_source(obj, sh, coll, name, cell=0.125, erode=0.6, blur=0.45, margin=0.06, far_slope=0.8,
                   far_rim=1.0):
    """Batch-1's crease-free ink proxy (kept): the model's top as a height field, eroded/blurred
    under the whorl steps and the J so the voxel shell can't bridge them and draw a black spiral;
    toward the rim it follows the model's own convex shoulder. Inside the rim band (`far_rim` px)
    it falls toward the far side no steeper than `far_slope` (see below). Closed underneath along
    the round underside (held `margin` inside it), since the segment flies free."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(obj, dg)
    u0, v0 = sh.cx - 10.0, sh.cy - 10.0
    nu = nv = int(20.0 / cell) + 1
    us = u0 + cell * np.arange(nu)
    vs = v0 + cell * np.arange(nv)
    h = np.full((nv, nu), np.nan)
    inside = np.zeros((nv, nu), bool)
    drim = np.zeros((nv, nu))
    for iy, v in enumerate(vs):
        for ix, u in enumerate(us):
            du, dv = u - sh.cx, v - sh.cy
            rr = math.hypot(du, dv)
            rim = sh.rim_r(math.atan2(dv, du))
            if rr >= rim - 0.02:
                continue
            hit = bvh.ray_cast(Vector(((u - 12) * PX, (14 - v) * PX, 30 * PX)), Vector((0, 0, -1)))
            if hit[0] is None:
                continue
            inside[iy, ix] = True
            h[iy, ix] = hit[0].z / PX
            drim[iy, ix] = rim - rr
    big = np.where(inside, h, 1e9)
    k = int(round(erode / cell))
    ero = big.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if dx * dx + dy * dy <= k * k:
                ero = np.minimum(ero, np.roll(np.roll(big, dy, 0), dx, 1))
    b = int(math.floor(blur / cell))
    acc = np.zeros_like(ero)
    cnt = np.zeros_like(ero)
    src = np.where(inside, ero, 0.0)
    for dy in range(-b, b + 1):
        for dx in range(-b, b + 1):
            acc += np.roll(np.roll(src, dy, 0), dx, 1)
            cnt += np.roll(np.roll(inside.astype(float), dy, 0), dx, 1)
    low = np.where(inside, acc / np.maximum(cnt, 1), 0.0) - margin
    w = np.clip((drim - 1.0) / 1.2, 0.0, 1.0)
    w = w * w * (3 - 2 * w)
    z = np.where(inside, np.minimum(h - margin, w * low + (1 - w) * (h - margin)), 0.0)
    # The game's ink is the shell's back faces (those facing away from the tilted camera) shifted up
    # the screen, which at a 30-45 deg tilt lifts them a third of a px or more: any back face inside
    # the outline then shows over the model in front of it (the black wedge at the flank lip's foot,
    # the dashes along the J's riser and its end under the spire). So inside the rim band the proxy
    # may fall toward the far side (sprite up) no steeper than `far_slope` (a camera-facing surface
    # at a 45 deg tilt): swept from the far side, each cell is held at most far_slope x cell above
    # the one behind it. It only ever lowers the proxy (it stays under the model); the rim band, the
    # silhouette proper, neither moves nor holds the cells in front of it down.
    band = drim < far_rim
    lim = np.where(inside & ~band, z, np.inf)
    for iy in range(1, nv):
        lim[iy] = np.minimum(lim[iy], lim[iy - 1] + far_slope * cell)
    z = np.where(inside & ~band, np.minimum(z, lim), z)
    bm = bmesh.new()
    top, bot = {}, {}
    for iy in range(nv):
        for ix in range(nu):
            if inside[iy, ix]:
                zb = sh.under_z(us[ix], vs[iy]) + margin
                zb = min(zb, -0.02)
                zt = max(z[iy, ix], 0.02)
                top[iy, ix] = bm.verts.new(Vector(((us[ix] - 12) * PX, (14 - vs[iy]) * PX, zt * PX)))
                bot[iy, ix] = bm.verts.new(Vector(((us[ix] - 12) * PX, (14 - vs[iy]) * PX, zb * PX)))
    for iy in range(nv - 1):
        for ix in range(nu - 1):
            q = [(iy, ix), (iy, ix + 1), (iy + 1, ix + 1), (iy + 1, ix)]
            if all(c in top for c in q):
                bm.faces.new([top[c] for c in q])
                bm.faces.new([bot[c] for c in reversed(q)])
    tv = {vv: key for key, vv in top.items()}
    for e in list(bm.edges):
        if len(e.link_faces) != 1:
            continue
        a, c = e.verts
        if a not in tv or c not in tv:
            continue
        f = e.link_faces[0]
        loop = next(l for l in f.loops if l.edge == e)
        a, c = loop.vert, loop.link_loop_next.vert
        bm.faces.new([c, a, bot[tv[a]], bot[tv[c]]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{name}_outline_src")
    bm.to_mesh(me)
    bm.free()
    src_obj = bpy.data.objects.new(f"{name}_outline_src", me)
    coll.objects.link(src_obj)
    bpy.context.view_layer.update()
    return src_obj


SHELL_INSIDE = 0.12  # px: the outline shell held at least this far under the model's surface


def hold_inside(shell, obj, inside):
    """Pull every outline-shell vertex that lies outside the model, or less than `inside` under it,
    to `inside` under the model's surface along its outward normal at the nearest point. The proxy
    the shell is made from follows the model only roughly at the rim seam and the flank lip's foot,
    and a voxel shell smoothed over it stood a hair proud there: drawn in colour it showed through the
    body as a black diamond at the suture's end and specks along the equator."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    tree = BVHTree.FromBMesh(bm)
    moved = 0
    for vt in shell.data.vertices:
        loc, nrm, _, _ = tree.find_nearest(vt.co)
        if loc is not None and (vt.co - loc).dot(nrm) > -inside:
            vt.co = loc - nrm * inside
            moved += 1
    bm.free()
    shell.data.update()
    return moved


def build(name, overrides=None):
    bp = BLUEPRINT[name]
    sh = Shell(name, bp, overrides)
    sprite = common.load_sprite(WT, name)
    coll = common.reset_collection(name)
    idx = SPEC[name]["idx"]
    mats = [common.palette_material(sprite, idx[k], name, **SHELL_MAT) for k in ("body", "suture", "under")]
    obj = build_mesh(sh, name, mats)
    coll.objects.link(obj)
    try:
        obj.data.set_sharp_from_angle(angle=math.radians(SHARP_DEG))
    except AttributeError:
        pass
    bpy.context.view_layer.update()
    src = outline_source(obj, sh, coll, name)
    shell = common.outline_shell(src, coll, voxel=0.01, faces=1500, smooth=3, inside=0.03 * PX)  # held inside the J (D88)
    bpy.data.objects.remove(src, do_unlink=True)
    hold_inside(shell, obj, SHELL_INSIDE * PX)
    shell.name = shell.data.name = f"{name}_outline"
    return obj, shell, sh


def stats(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad = sum(1 for e in bm.edges if not e.is_manifold)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    tris = len(bm.faces)
    zmax = max(v.co.z for v in bm.verts) / PX
    top = max(bm.verts, key=lambda v: v.co.z).co
    bm.free()
    return dict(tris=tris, non_manifold_edges=bad, high_px=round(zmax, 2),
                high_at_sprite=(round(top.x / PX + 12, 2), round(14 - top.y / PX, 2)))


# ---------------------------------------------------------------- renders for the review sheet

def renders(name, obj, shell, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o not in (obj,)
    shell.hide_render = True
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sd = scene.display.shading
    sd.light = "STUDIO"
    sd.color_type = "MATERIAL"
    sd.show_cavity = False
    sd.show_object_outline = False
    sd.show_specular_highlight = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.03, 0.035, 0.05)
    scene.render.resolution_percentage = 100

    def cam(nm, loc, look, ortho=None, lens=60):
        data = bpy.data.cameras.new(nm)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        c = bpy.data.objects.new(nm, data)
        scene.collection.objects.link(c)
        c.location = loc
        c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return c

    # top mask on the sprite grid (24 x 28 px at 12 px per px), flat white on transparent
    scene.render.film_transparent = True
    sd.light = "FLAT"
    sd.color_type = "SINGLE"
    sd.single_color = (1, 1, 1)
    scene.render.resolution_x, scene.render.resolution_y = 24 * 12, 28 * 12
    c = cam("top", (0, 0, 5), (0, 0, 0), ortho=28 / 12)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(out_dir / "mask.png")
    bpy.ops.render.render(write_still=True)
    # lit views
    sd.light = "STUDIO"
    sd.color_type = "MATERIAL"
    scene.render.film_transparent = False
    scene.render.filepath = str(out_dir / "top.png")
    bpy.ops.render.render(write_still=True)
    scene.render.resolution_x = scene.render.resolution_y = 400
    cz = 2.5 * PX
    D = 2.0
    views = {
        "game": ((0, -D * math.sin(math.radians(32)), D * math.cos(math.radians(32))), 1.0),
        "side": ((D, 0, cz), 0),
        "front": ((0, D, cz), 0),
        "rear": ((0, -D, cz), 0),
        "q34": ((-D * 0.6, D * 0.6, D * 0.75), 0),
        "q34b": ((D * 0.65, -D * 0.6, D * 0.45), 0),
        "under": ((0.001, -0.3, -D), 0),
    }
    for nm, (loc, _) in views.items():
        c = cam(nm, loc, (0, 0, cz), ortho=1.75)
        scene.camera = c
        scene.render.filepath = str(out_dir / f"{nm}.png")
        bpy.ops.render.render(write_still=True)
    shell.hide_render = False


def main(names, render_dir=None):
    for name in names:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.context.view_layer.update()
        obj, shell, sh = build(name)
        sprite = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [obj, shell], f"enemies/{name}", sprite["sprites"])
        st = stats(obj)
        st["outline_faces"] = len(shell.data.polygons)
        print(name, st)
        if render_dir:
            renders(name, obj, shell, Path(render_dir) / name)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rd = args[args.index("--renders") + 1] if "--renders" in args else None
    names = [a for a in args if a.startswith("newshn-")]
    main(names or ["newshn-125", "newshn-15", "newshn-13"], rd)
