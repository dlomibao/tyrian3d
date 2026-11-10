"""newshi-278 : the red bomber's nose (newshi.shp frame 278, 24 x 28 px), rebuilt
hard-surface to the D65 standard so it continues the D116 red bomber (assembly-newshi-243).

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"; sprite_mask inner mask):
- It flies just below the bomber, whose fuselage is cut open at its row 56: the nose's row 0 is the
  joint. The bomber's last section there is a superellipse, half width 9.1 px, top 5.4 px, bottom
  -3.5 px (assembly-newshi-243.py FUSE, r = 56); its axis lands on the nose's column edge 12.5.
- Rows 0-2, cols 3-21: a collar ring the full fuselage width (half 9.5), lit on top (71).
- Rows 3-8: two cheek fairings (cols 3-4 / 20-21, dark red 66-69, the fuselage skin running on as
  side jaws) split from the cone by a slot (cols 5 / 19, ink 16 / 1). The damaged frames (268, 270,
  272) draw that slot transparent: it is a real gap, so the cheeks are separate jaws with only a low
  web joining them to the cone under the gap.
- The cone (cols 6-18, half 6.5) runs straight to row 13, then tapers ogive-like to a point:
  half widths 5.5 (rows 14-15), 4.5 (16-17), 3.5 (18-19), 2.5 (20-22), 1.5 (23), 0.5 (24-25).
- A light ridge (cols 9-13, 73-79; col 11's 77-79 is sheen) runs down the back from the joint,
  continuing the bomber's nose ridge, and fades out by row 12.
- Two lighter bands across it (rows 13 and 19, 72 / 71, flanked by ink-dark 16 on the edges):
  raised joint rings where the cone's sections meet (the step in width at row 14 is the ring).
- Row 23 (16 at both edges): a tip collar; rows 24-25, one pixel wide: a pitot probe.

Colours (trimmed medians, ../regions.py): collar 71, cheeks 66 (lit outer column 68-69; 67 used,
see notes), ridge 73.5 -> 73, cone 70 (interior; 69 with its shading ring), band 13 72, band 19 71,
tip 68. Satin painted metal throughout.

Hard surface (D50-D53, D65): pchip-interpolated superellipse lofts (collar, cone, cheeks) with cut
ring grooves for panel joints, chamfered raised rings, a chamfered ridge strip conforming to the
hull, inset flank hatches (raised plates whose gaps are the panel lines), bolt heads on the collar,
a machined tip collar and probe. Underside: the lofts' closed bottoms only.

Units while building: sprite px (x = column edge - 12, y = row edge, down the screen = forward,
z up), moved to Blender by usp_talon.finish (1/12, y flipped). Axis at x = 0.5.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshi-278.py
"""

import math
import sys
from pathlib import Path

import bpy

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshi-278"
HERE = Path(__file__).resolve().parent
XC = 0.5  # the axis: column edge 12.5


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, metallic=0.35, roughness=0.42):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{NAME}_{part}",
                                                     metallic=metallic, roughness=roughness))
        return self.slots[key]


# --- a superellipse section body, stations pchip-interpolated -------------------------------------
class Body:
    """Stations (y, w, zc, h, hb, n): half width w, top h above the centre zc, bottom hb below it,
    superellipse exponent n. pt(y, a, grow) is the surface point at angle a (deg, 0 = +x side,
    90 = top), pushed out by `grow` px."""

    def __init__(self, stations, xc=XC):
        ys = [s[0] for s in stations]
        self.y0, self.y1 = ys[0], ys[-1]
        self.f = [T.pchip(ys, [s[k] for s in stations]) for k in range(1, 6)]
        self.xc = xc

    def par(self, y):
        y = min(max(y, self.y0), self.y1)
        return [f(y) for f in self.f]

    def pt(self, y, a, grow=0.0):
        w, zc, h, hb, n = self.par(y)
        q = math.radians(a)
        c, s = math.cos(q), math.sin(q)
        e = 2.0 / max(n, 1.0)
        x = math.copysign(abs(c) ** e, c) * max(0.0, w + grow)
        z = math.copysign(abs(s) ** e, s) * max(0.0, (h if s >= 0 else hb) + grow)
        return (self.xc + x, y, zc + z)

    def top(self, y, u):
        """Height of the upper surface at x = xc + u (or None outside it)."""
        w, zc, h, hb, n = self.par(y)
        if abs(u) >= w:
            return None
        return zc + h * (1 - (abs(u) / w) ** n) ** (1 / n)


def loft(P, body, ys, mat_of, sides=40, grooves=(), cap0=True, tip=None, cap_mat=None):
    """Rings of `body` at ys; grooves [(y, half width, depth, mat)] cut as real ring grooves.
    tip: a point (x, y, z) the last ring closes to; else a flat cap. mat_of(ymid, a)."""
    samples = set(round(y, 4) for y in ys)
    shrink = {}
    for gy, ghw, gd, _ in grooves:
        for yy in (gy - ghw, gy + ghw):
            samples.add(round(yy, 4))
        for yy in (gy - ghw + 0.03, gy + ghw - 0.03):
            samples.add(round(yy, 4))
            shrink[round(yy, 4)] = gd
        for yy in list(samples):
            if gy - ghw + 0.03 < yy < gy + ghw - 0.03:
                samples.discard(yy)
    Y = sorted(samples)
    angs = [360.0 * (k + 0.5) / sides for k in range(sides)]
    rings = [[P.v(body.pt(y, a, -shrink.get(round(y, 4), 0.0))) for a in angs] for y in Y]

    def gmat(ym):
        for gy, ghw, gd, gm in grooves:
            if abs(ym - gy) < ghw:
                return gm
        return None
    for i in range(len(Y) - 1):
        ym = (Y[i] + Y[i + 1]) / 2
        gm = gmat(ym)
        for k in range(sides):
            j = (k + 1) % sides
            am = (angs[k] + angs[j] + (360 if j == 0 else 0)) / 2
            mid = body.pt(ym, am)
            ctr = (body.xc, ym, body.par(ym)[1])
            out = (mid[0] - ctr[0], 0.0, mid[2] - ctr[2])
            P.f([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]],
                gm if gm is not None else mat_of(ym, am), out=out)
    if cap0:
        P.f(rings[0], cap_mat if cap_mat is not None else mat_of(Y[0], 90), out=(0, -1, 0))
    if tip is not None:
        t = P.v(tip)
        for k in range(sides):
            j = (k + 1) % sides
            am = (angs[k] + angs[j] + (360 if j == 0 else 0)) / 2
            mid = body.pt(Y[-1], am)
            P.f([rings[-1][k], rings[-1][j], t], mat_of(Y[-1], am),
                out=(mid[0] - body.xc, 0.4, mid[2] - body.par(Y[-1])[1]))
    else:
        P.f(rings[-1], cap_mat if cap_mat is not None else mat_of(Y[-1], 90), out=(0, 1, 0))
    return rings


def ring_band(P, body, y0, y1, grow, mat, sides=40, ch=0.14):
    """A raised, chamfered ring round body between y0 and y1 (a joint band)."""
    st = [(y0, -0.05), (y0 + ch, grow), (y1 - ch, grow), (y1, -0.05)]
    angs = [360.0 * (k + 0.5) / sides for k in range(sides)]
    rings = [[P.v(body.pt(y, a, g)) for a in angs] for y, g in st]
    for i in range(len(st) - 1):
        for k in range(sides):
            j = (k + 1) % sides
            am = (angs[k] + angs[j] + (360 if j == 0 else 0)) / 2
            p = body.pt((st[i][0] + st[i + 1][0]) / 2, am)
            ctr = body.par(p[1])[1]
            P.f([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], mat,
                out=(p[0] - body.xc, 0.0, p[2] - ctr))
    P.f(rings[0], mat, out=(0, -1, 0))
    P.f(rings[-1], mat, out=(0, 1, 0))


def patch(P, S, y0, y1, u0, u1, lift, ch, mat_top, mat_side, ny=10, nu=6, sink=0.3, taper=None,
          crown=0.0, lift_of=None):
    """A chamfered plate lying on a surface: S(y, u, lift) is the surface point at (y, u) pushed
    `lift` out. Runs y0..y1, spans u0..u1 (or taper(y) -> (u0, u1)); its top stands `lift` out,
    its walls sink `sink` into the surface (strips, hatches, ridges that conform to the hull)."""
    def span(y):
        return taper(y) if taper else (u0, u1)

    def sec(y, end):
        a, b = span(y)
        c = min(ch, (b - a) * 0.3)
        us = [a + c + (b - a - 2 * c) * k / (nu - 1) for k in range(nu)]
        L = lift_of(y) if lift_of else lift
        cc = min(ch, L * 0.6)
        mid, half = (a + b) / 2, max(1e-6, (b - a) / 2)

        def top(u):
            t = (u - mid) / half
            return (L - (cc if end else 0.0)) - (L - cc) * crown * t * t
        pts = [S(y, a, -sink), S(y, a, L - cc - (L - cc) * crown)]
        pts += [S(y, u, top(u)) for u in us]
        pts += [S(y, b, L - cc - (L - cc) * crown), S(y, b, -sink)]
        return pts
    ys = [y0] + [y0 + ch + (y1 - y0 - 2 * ch) * k / (ny - 1) for k in range(ny)] + [y1]
    secs = [[P.v(p) for p in sec(y, i in (0, len(ys) - 1))] for i, y in enumerate(ys)]
    m = len(secs[0])
    for i in range(len(ys) - 1):
        A, B = secs[i], secs[i + 1]
        for k in range(m - 1):
            ix = mat_top if 1 <= k < m - 2 else mat_side
            P.f([A[k], A[k + 1], B[k + 1], B[k]], ix, away=tuple(_inward(A, B)))
    P.f(secs[0], mat_side, out=(0, -1, 0))
    P.f(secs[-1], mat_side, out=(0, 1, 0))


def _inward(A, B):
    """A point under the middle of a patch (orientation hint: faces point away from it)."""
    base = (A[0].co + A[-1].co + B[0].co + B[-1].co) / 4
    topm = (A[len(A) // 2].co + B[len(B) // 2].co) / 2
    return base - (topm - base) * 2.0


def dome(P, c, r, hz, mat, seg=10, rings=3, axis_z=True):
    """A bolt head: a flattened hemisphere at c (x, y, z)."""
    cx, cy, cz = c
    pts = []
    for j in range(rings + 1):
        phi = (math.pi / 2) * j / rings
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(P.v((cx + r * math.cos(phi) * math.cos(a), cy + r * math.cos(phi) * math.sin(a),
                             cz + hz * math.sin(phi) if j < rings else cz + hz)))
        pts.append(ring)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            if j == rings - 1:
                P.f([pts[j][i], pts[j][k], pts[j + 1][0]], mat, away=(cx, cy, cz - 1))
            else:
                P.f([pts[j][i], pts[j][k], pts[j + 1][k], pts[j + 1][i]], mat, away=(cx, cy, cz - 1))
    P.f(pts[0], mat, out=(0, 0, -1))


def revolve(P, a, stations, mat_of, n=14):
    """Rings round a +y axis from point a: stations [(dy, r)], r = 0 at an end closes to a point."""
    ax, ay, az = a
    angs = [2 * math.pi * (k + 0.5) / n for k in range(n)]
    rings = []
    for dy, r in stations:
        rings.append([P.v((ax + r * math.cos(q), ay + dy, az + r * math.sin(q))) for q in angs])
    for i in range(len(stations) - 1):
        for k in range(n):
            j = (k + 1) % n
            qm = (angs[k] + angs[j] + (2 * math.pi if j == 0 else 0)) / 2
            P.f([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], mat_of(i),
                out=(math.cos(qm), 0.0, math.sin(qm)))
    if stations[0][1] > 1e-6:
        P.f(rings[0], mat_of(0), out=(0, -1, 0))
    if stations[-1][1] > 1e-6:
        P.f(rings[-1], mat_of(len(stations) - 2), out=(0, 1, 0))


# --- the nose -------------------------------------------------------------------------------------
# The collar: the bomber's last section (w 9.1, top 5.4, bottom -3.5) opening to the sprite's half
# width 9.5, with a chamfered front lip where the cone and the cheeks come out of it.
COLLAR = Body([(0.0, 9.1, 0.8, 4.6, 4.2, 3.2), (0.45, 9.42, 0.8, 4.78, 4.25, 3.2),
               (2.25, 9.42, 0.8, 4.78, 4.25, 3.2), (2.75, 9.0, 0.8, 4.4, 3.9, 3.2)])

# The cone: straight to the first band (row 13), then an ogive to the tip collar (row 23).
CONE = Body([
    (2.0, 6.55, 1.0, 4.22, 3.85, 2.8),
    (8.0, 6.50, 1.0, 4.18, 3.80, 2.8),
    (12.8, 6.38, 1.02, 4.02, 3.62, 2.7),
    (13.9, 5.98, 1.05, 3.78, 3.40, 2.6),
    (15.0, 5.70, 1.08, 3.60, 3.20, 2.55),
    (16.5, 4.85, 1.12, 3.18, 2.76, 2.45),
    (18.0, 4.25, 1.17, 2.78, 2.35, 2.35),
    (19.5, 3.45, 1.21, 2.30, 1.90, 2.3),
    (20.7, 2.85, 1.25, 1.92, 1.52, 2.25),
    (21.8, 2.55, 1.28, 1.66, 1.30, 2.2),
    (22.6, 2.25, 1.30, 1.45, 1.12, 2.2),
    (23.3, 1.80, 1.31, 1.16, 0.90, 2.1),
])


CONE_YS = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 12.8] + [13.3 + 0.6 * k for k in range(17)] + [23.3]


def cheek_body(side):
    """A cheek jaw: the fuselage skin running forward beside the cone (cols 3-4 / 20-21), its top
    falling and its plan rounding off at row 8."""
    xc = XC + side * 8.5
    return Body([(1.0, 0.95, 0.5, 3.1, 3.0, 3.0), (2.7, 0.95, 0.5, 2.85, 3.0, 3.0),
                 (5.0, 0.95, 0.45, 2.2, 2.8, 3.0), (6.8, 0.92, 0.4, 1.55, 2.5, 2.9),
                 (7.7, 0.80, 0.4, 1.05, 2.1, 2.7), (8.2, 0.50, 0.4, 0.7, 1.5, 2.4),
                 (8.45, 0.12, 0.4, 0.3, 0.7, 2.2)], xc=xc)


def surf_top(y, u):
    """The hull's upper surface (collar or cone, whichever is higher) at x = XC + u."""
    zs = [b.top(y, u) for b in (COLLAR, CONE) if b.y0 <= y <= b.y1]
    zs = [z for z in zs if z is not None]
    return max(zs) if zs else CONE.par(y)[1]


def build_nose(P, M):
    # collar ring: joint groove behind, bolt heads round its crown, bulkhead at the back
    loft(P, COLLAR, [0.0, 0.45, 1.0, 1.6, 2.25, 2.75], lambda y, a: M["collar"], sides=40,
         grooves=[(1.05, 0.13, 0.16, M["seam"])], cap_mat=M["bulk"])
    for u in (-6.3, -4.6, 4.6, 6.3):
        z = COLLAR.top(1.75, u)
        dome(P, (XC + u, 1.75, z - 0.05), 0.32, 0.22, M["bolt"], seg=8, rings=2)

    # cone: under-belly in the same red (closed shape only); panel joint groove on the radome
    loft(P, CONE, CONE_YS, lambda y, a: M["cone"], sides=32, cap0=True, tip=None, cap_mat=M["tip"])

    # joint bands (rows 13, 19) and the tip collar (row 23)
    ring_band(P, CONE, 12.75, 13.95, 0.32, M["band13"], sides=32)
    ring_band(P, CONE, 18.85, 19.85, 0.26, M["band19"], sides=32)
    # tip collar and pitot probe (rows 23-25, one pixel wide)
    revolve(P, (XC, 22.95, 1.31), [(0.0, 1.55), (0.12, 1.88), (0.55, 1.88), (0.7, 1.45), (0.95, 1.05),
                                   (1.2, 0.62), (1.35, 0.5), (2.6, 0.42), (2.75, 0.5), (2.95, 0.5),
                                   (3.15, 0.3), (3.3, 0.0)],
            lambda i: M["tipc"] if i < 4 else M["probe"], n=16)

    # ridge strip down the back (cols 9-13), from the joint, fading out before the first band
    def ridge_w(y):
        return T.pchip([0.0, 4.0, 8.0, 10.4, 12.2], [2.75, 2.55, 2.15, 1.55, 0.6])(y)

    def S_top(y, u, lift):
        return (XC + u, y, surf_top(y, u) + lift)
    patch(P, S_top, 0.0, 12.3, 0, 0, 0.5, 0.16, M["ridge"], M["seam"], ny=16, nu=7, sink=0.4,
          taper=lambda y: (-ridge_w(y), ridge_w(y)), crown=0.35,
          lift_of=T.pchip([0.0, 8.5, 11.0, 12.3], [0.5, 0.48, 0.3, 0.08]))

    # flank hatches on the cone (rows 3-12): raised plates whose gaps read as the panel lines
    for side in (1, -1):
        def S_cone(y, a, lift, side=side):
            aa = a if side > 0 else 180 - a
            return CONE.pt(y, aa, lift)
        patch(P, S_cone, 3.3, 8.7, 22, 58, 0.1, 0.08, M["cone"], M["seam"], ny=6, nu=7, sink=0.25)
        patch(P, S_cone, 9.3, 12.4, 22, 58, 0.1, 0.08, M["cone"], M["seam"], ny=4, nu=7, sink=0.25)
        patch(P, S_cone, 3.3, 12.4, -28, 15, 0.1, 0.08, M["cone"], M["seam"], ny=8, nu=6, sink=0.25)
        # a latch on each upper hatch
        p = CONE.pt(6.0, 40 if side > 0 else 140, 0.1)
        T.hull(P, T.cbox(p[0] - 0.45, p[0] + 0.45, 5.6, 6.4, p[2] - 0.3, p[2] + 0.16, 0.08), M["cone"])

    # cheeks (jaws) with a cross groove, and the low web under the slot
    for side in (1, -1):
        cb = cheek_body(side)
        loft(P, cb, [1.0, 2.7, 4.0, 5.0, 6.0, 6.8, 7.4, 7.8, 8.1, 8.3, 8.45],
             lambda y, a: M["cheek"], sides=20, grooves=[(4.6, 0.12, 0.12, M["seam"])])
        x0, x1 = sorted((XC + side * 7.75, XC + side * 6.0))
        T.hull(P, T.cbox(x0, x1, 2.6, 7.9, -2.4, -0.9, 0.15), M["web"])


def shell_proxy(coll):
    """A closed stand-in for the outline shell: the hull without the gaps."""
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    loft(P, COLLAR, [0.0, 0.45, 1.6, 2.25, 2.75], lambda y, a: 0, sides=40)
    loft(P, CONE, CONE_YS, lambda y, a: 0, sides=32,
         tip=(XC, 26.1, 1.31))
    for side in (1, -1):
        cb = cheek_body(side)
        loft(P, cb, [1.0, 2.7, 5.0, 6.8, 7.7, 8.2, 8.45], lambda y, a: 0, sides=20)
        x0, x1 = sorted((XC + side * 7.9, XC + side * 6.0))
        T.hull(P, T.cbox(x0, x1, 2.6, 7.9, -2.4, 2.4, 0.15), 0)
    return T.finish(P, [], coll)


def build():
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    Mt = Mats(sprite)
    M = {
        "collar": Mt(71, "collar"),
        "cone": Mt(70, "cone"),
        "cheek": Mt(67, "cheek"),
        "ridge": Mt(73, "ridge", metallic=0.35, roughness=0.38),
        "band13": Mt(72, "band13"),
        "band19": Mt(71, "band19"),
        "tipc": Mt(68, "tipc"),
        "tip": Mt(68, "tip"),
        "probe": Mt(68, "probe", metallic=0.55, roughness=0.32),
        "seam": Mt(66, "seam", roughness=0.55),
        "web": Mt(65, "web", roughness=0.6),
        "bulk": Mt(66, "bulk", roughness=0.55),
        "bolt": Mt(72, "bolt", metallic=0.55, roughness=0.32),
    }
    P = T.Part(NAME, smooth_angle=34)
    build_nose(P, M)
    obj = T.finish(P, Mt.list, coll)
    proxy = shell_proxy(coll)
    shell = common.outline_shell(proxy, coll, voxel=0.008, faces=1400, smooth=4, inside=0.01)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.context.view_layer.update()
    return sprite, obj, shell


MODEL = f"enemies/{NAME}"


if __name__ == "__main__":
    sprite, obj, shell = build()
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    for o in (obj, shell):
        o.data.calc_loop_triangles()
    print(f"built {NAME}: {len(obj.data.loop_triangles)} triangles, outline {len(shell.data.loop_triangles)}")
