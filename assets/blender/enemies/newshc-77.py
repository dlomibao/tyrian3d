"""newshc-77: the pop-up ball turret on each pillar head of assembly-newshc-283.

newshc.shp frames 77-89 (one shape per frame) plus the damaged frame 91. Design A leads with the
blueprint (scratch blueprint/model.js), engineering first, cross-sections before detail:

- Axis. The head is the north end of a pillar that LIES on the ground (assembly-newshc-283): the
  pillar's axis runs north-south at z = HA = 5 px, its section a flattened superellipse
  (half-width 7.95, half-height 0.62 x that, exponent 2.3). Everything below is built on that axis.
- Hood. The red hood is the pillar's end housing, the pillar section lofted with pchip stations,
  split along the sprite's 1 px seam (col 11, x -1..0) into two clamshell halves. Each half has a
  chamfered seam lip, a modelled panel groove where its nose starts to taper, a slide-actuator cap
  on its outer wall and (east half) the recessed rail channel the sprite shows in dark red (67).
  At rest the halves slide sideways on two rods (frames 85/87/89: 1/2/3 px each side) and show the
  dark-red launcher core between them with its black port (66/16).
- Neck. A telescoping ram of four chamfered stages ON the pillar axis (a collar, not a stem on the
  ground; D116 open issue): frames 77/79/81 show 6/3/1 rows of it as the head rides north out of
  the pillar mouth.
- Ball. A satin steel ellipsoid (pal 8, roughness 0.44, not chrome; D116 open issue) cupped in the
  hood, its mesh pole on the eye axis so the socket is a clean circle: a machined bezel, a dark
  socket recessed 0.85 px into the ball (a real recess, D116 open issue) and the lens dome in it,
  glowing 112-118 on frames 79-87. A red enamel band (73) over the meridian, a dark sight slit.
- Frame 91: the ball and hood are gone: the ram's torn collar, dark inside, and a bent rod.

Colours are the sprite's palette index per region (blueprint table: medians without the darkest /
brightest 15%). Underside: the flat closed floor of each loft only. No texture bake (there is no
textures/newshc-77 folder); outline shell per frame (D51).

Units: geometry in sprite px (x east, y north, z up; origin = the 24x28 block's centre,
x = col_edge - 12, y = 14 - row_edge), scaled by 1/12 to Blender units at the end.

Run: blender --background --python newshc-77_A.py -- [--views DIR] [--measure DIR]
Exports one glb per frame (the game models: newshc-77, newshc-77-f2 .. -f7, newshc-77-f8 for frame 91),
each tagged with frame_part([frame]) plus its outline shell, and registers it in src/render/spriteModels.
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

OUT = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-2/newshc-77/final")
REF91 = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-2/newshc-77/blueprint/ref91")
NAME = "newshc-77"
PX = 1 / 12

# --- engineering constants (sprite px) ------------------------------------------------------------
PE, ZA, K, ZF = 2.3, 5.0, 0.62, 0.2          # section exponent, pillar axis z, flattening, floor z
BALL = dict(row=14.8, rx=8.0, ry=8.0, rz=6.6, zc=6.0)   # rest position (frame 83)
HOOD_H = 5.0
CUT = (-1.0, 0.0)                              # seam between the hood halves (sprite col 11)
SEAM_CH = 0.35                                 # chamfer on each half's seam lip
FR = {  # s: rows the head stands north of rest; o: px each hood half slides out; eye: (core, rim, r core, r lit)
    77: dict(s=6, o=0, eye=None), 79: dict(s=3, o=0, eye=(112, 112, 0.0, 1.2)),
    81: dict(s=1, o=0, eye=(114, 112, 0.7, 1.7)), 83: dict(s=0, o=0, eye=(118, 114, 0.95, 1.9)),
    85: dict(s=0, o=1, eye=(118, 113, 1.15, 2.1)), 87: dict(s=0, o=2, eye=(114, 112, 0.8, 1.8)),
    89: dict(s=0, o=3, eye=None), 91: dict(wreck=True),
}
FRAMES = [77, 79, 81, 83, 85, 87, 89, 91]
PAL = dict(ball=8, stripe=73, bezel=6, socket=2, lens_off=2, hood=71, channel=67, core=66, port=16,
           ram=5, ram_slot=2, rod=5, boss=5, slit=3, wreck=5, wreck_in=1, wreck_rod=7)


def model_name(frame):
    i = FRAMES.index(frame)
    return NAME if i == 0 else f"{NAME}-f{i + 1}"


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson), clamped outside the stations."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

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


# --- mesh builder with per-face orientation hints ---------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.hints = []

    def ring(self, pts):
        return [self.bm.verts.new(p) for p in pts]

    def face(self, vs, mat, out):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        self.hints.append((f, Vector(out)))
        return f

    def loft(self, rings, mat, cap0=True, cap1=True, inward=False, ref=None, closed=True, outf=None):
        """Quads between equal-length point rings. Each face points away from its ring centre (or
        `ref(i, k)`, a point per profile index), toward it with inward. `mat` is a slot or a
        function of the face centre."""
        R = [self.ring(r) for r in rings]
        cents = [sum((Vector(p) for p in r), Vector()) / len(r) for r in rings]
        n = len(rings[0])
        for k in range(len(R) - 1):
            a, b = R[k], R[k + 1]
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                c = (Vector(rings[k][i]) + Vector(rings[k][j]) + Vector(rings[k + 1][i]) + Vector(rings[k + 1][j])) / 4
                r0 = ref(i, k) if ref else (cents[k] + cents[k + 1]) / 2
                out = outf(c, i, k) if outf else (c - r0) * (-1 if inward else 1)
                self.face((a[i], a[j], b[j], b[i]), mat(c) if callable(mat) else mat, out)
        for ok, k, k2 in ((cap0, 0, 1), (cap1, len(R) - 1, len(R) - 2)):
            if not ok:
                continue
            c = cents[k]
            cv = self.bm.verts.new(c)
            out = c - cents[k2]
            for i in range(n):
                j = (i + 1) % n
                m = mat(c) if callable(mat) else mat
                self.face((cv, R[k][i], R[k][j]), m, out)

    def finish(self, name, mats, coll, sharp=34):
        for f, o in self.hints:
            if f.is_valid:
                f.normal_update()
                if f.normal.dot(o) < 0:
                    f.normal_flip()
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges)
        bmesh.ops.transform(bm, matrix=Matrix.Scale(PX, 4), verts=bm.verts)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for mt in mats:
            me.materials.append(mt)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp))
        return obj


# --- sections ------------------------------------------------------------------------------------

def zt(x, W, H, za):
    return za + H * max(0.0, 1 - min(1.0, abs(x) / W) ** PE) ** (1 / PE)


def section(W, H, za=ZA, x0=-1e9, x1=1e9, notches=(), cut=None, extra=()):
    """The pillar's flattened superellipse (half-width W, half-height H, axis za, flat floor ZF) as a
    closed (x, z) ring of fixed length: the top sampled by x (plus notch / chamfer edges), the rest by
    angle. [x0, x1] clamps it (a hood half; the clamped points form the flat seam wall). notches
    (a, b, d) sink the top between x = a..b by d. cut = seam x: its top lip gets a SEAM_CH chamfer."""
    f = 0.78
    xs = [W * f - 2 * W * f * i / 18 for i in range(19)]
    for a, b, _ in notches:
        xs += [b + 0.02, b - 0.02, a + 0.02, a - 0.02]
    xs += list(extra)
    top = sorted(xs, reverse=True)
    P = []
    for x in top:
        z = zt(x, W, H, za)
        for a, b, d in notches:
            if a < x < b:
                z -= d
        P.append([x, z])
    th = math.acos(f ** (PE / 2))
    M = 26
    for i in range(1, M):
        t = math.pi - th + (math.pi + 2 * th) * i / M
        c, s = math.cos(t), math.sin(t)
        P.append([W * math.copysign(abs(c) ** (2 / PE), c), max(ZF, za + H * math.copysign(abs(s) ** (2 / PE), s))])
    out = []
    for x, z in P:
        xc = min(x1, max(x0, x))
        if xc != x:
            z = min(z, zt(xc, W, H, za))
        if cut is not None and z > za:
            dist = abs(xc - cut)
            if dist < SEAM_CH:
                z = min(z, zt(xc, W, H, za) - (SEAM_CH - dist))
        out.append((xc, z))
    return out


def loft_y(m, stations, mat, cap0=True, cap1=True):
    """Stations dicts {y, W, H, za, x0, x1, notches, cut, dx, extra} -> a closed loft along y."""
    rings = []
    for s in stations:
        sec = section(s["W"], s["H"], s.get("za", ZA), s.get("x0", -1e9), s.get("x1", 1e9), s.get("notches", ()),
                      s.get("cut"), s.get("extra", ()))
        rings.append([(x + s.get("dx", 0.0), s["y"], z) for x, z in sec])
    # orientation reference: the section's own axis (x centre of its x range, za)
    def ref(i, k):
        s = stations[k]
        xa = (max(s.get("x0", -s["W"]), -s["W"]) + min(s.get("x1", s["W"]), s["W"])) / 2 + s.get("dx", 0.0)
        return Vector((xa, (stations[k]["y"] + stations[k + 1]["y"]) / 2, s.get("za", ZA) * 0.8 + 0.6))
    m.loft(rings, mat, cap0, cap1, ref=ref)


def ell_z(x, y, R):
    q = 1 - (x / R[0]) ** 2 - (y / R[1]) ** 2
    return None if q < 0 else R[2] * math.sqrt(q)


# --- the head -----------------------------------------------------------------------------------------

def build_head(frame, S):
    """One frame's head as a Mesh. S: material slot by role."""
    F = FR[frame]
    m = Mesh()
    b_row = BALL["row"] - F["s"]
    yb = 14 - b_row
    o = F["o"]
    Y = lambda u: yb - u  # noqa: E731  (u: px south of the ball centre)
    C = Vector((0.0, yb, BALL["zc"]))
    R = (BALL["rx"], BALL["ry"], BALL["rz"])

    # ---- ball: ellipsoid, mesh pole on the eye axis (tilted north) --------------------------------
    sy = 4.3 / R[1]
    ua = Vector((0.0, sy, math.sqrt(1 - sy * sy)))
    e1 = ua.cross(Vector((1, 0, 0))).normalized()
    e2 = ua.cross(e1)
    a0 = 0.40
    NB = 44

    def bpt(a, b):
        d = ua * math.cos(a) + e1 * (math.sin(a) * math.cos(b)) + e2 * (math.sin(a) * math.sin(b))
        p = Vector((C.x + d.x * R[0], C.y + d.y * R[1], C.z + d.z * R[2]))
        p.z = max(ZF, p.z)
        return p

    angs = [a0, a0 + 0.04, a0 + 0.1] + [a0 + 0.1 + (math.pi - 0.06 - a0 - 0.1) * i / 24 for i in range(1, 25)]
    rings = [[tuple(bpt(a, 2 * math.pi * j / NB)) for j in range(NB)] for a in angs]
    m.loft(rings, S["ball"], cap0=False, cap1=True, ref=lambda i, k: C)
    rim = [Vector(p) for p in rings[0]]
    cen = sum(rim, Vector()) / len(rim)
    # axis: the ellipsoid normal at the pole
    ax = Vector((ua.x / R[0], ua.y / R[1], ua.z / R[2])).normalized()
    # machined bezel lip round the socket (0.22 px proud), chamfered
    lip = [cen + (p - cen) * 1.13 - ax * 0.05 for p in rim]
    lip_up = [cen + (p - cen) * 1.09 + ax * 0.2 for p in rim]
    lip_top = [cen + (p - cen) * 1.03 + ax * 0.26 for p in rim]
    lip_in = [p + ax * 0.18 for p in rim]
    bz = [lip, lip_up, lip_top, lip_in, [tuple(p) for p in rim]]
    bz = [[tuple(p) for p in r] for r in bz]
    m.loft(bz, S["bezel"], cap0=False, cap1=False,
           ref=lambda i, k: cen + (rim[i] - cen) * 1.06 + ax * 0.02)
    # recessed socket: wall straight down the axis, then a dark floor 0.85 px deep
    depth = 0.85
    wall_mid = [p - ax * 0.45 for p in rim]
    floor = [cen + (p - cen) * 0.93 - ax * depth for p in rim]
    m.loft([[tuple(p) for p in r] for r in (rim, wall_mid, floor)], S["socket"], cap0=False, cap1=True, inward=True,
           ref=lambda i, k: cen - ax * 0.4)
    # fix the floor cap's orientation: it must face out of the socket (along +ax)
    fc = cen - ax * depth
    for f, h in m.hints[-NB:]:
        h[:] = ax
    # lens dome in the socket
    lens_r = 2.05
    l1 = ax.cross(Vector((1, 0, 0))).normalized()
    l2 = ax.cross(l1)
    lens_rings = []
    for rr in (2.05, 1.92, 1.78, 1.64, 1.5, 1.36, 1.22, 1.08, 0.94, 0.8, 0.65, 0.5, 0.34, 0.18, 0.03):
        h = 0.04 + 0.8 * math.sqrt(max(0.0, 1 - (rr / lens_r) ** 2))
        lens_rings.append([tuple(fc + l1 * (math.cos(2 * math.pi * j / 24) * rr) + l2 * (math.sin(2 * math.pi * j / 24) * rr) + ax * h)
                           for j in range(24)])
    E = F["eye"]
    if E:
        core, rimc, rc, rl = E

        def lens_mat(c):
            d = c - fc
            rad = (d - ax * d.dot(ax)).length
            return S["eye_core"] if rad < rc else S["eye_rim"] if rad < rl else S["lens_off"]
        m.loft(lens_rings, lens_mat, cap0=False, cap1=True, ref=lambda i, k: fc - ax * 1.0)
    else:
        m.loft(lens_rings, S["lens_off"], cap0=False, cap1=True, ref=lambda i, k: fc - ax * 1.0)

    # red enamel band over the meridian (x -1..1), chamfered edges, broken by the bezel
    def band(ya, yb2, n=12, w=1.0, up=0.14):
        rr = []
        for i in range(n + 1):
            yy = ya + (yb2 - ya) * i / n
            ring = []
            for x, dz in ((-w, -0.2), (-w, up - 0.06), (-w + 0.12, up), (w - 0.12, up), (w, up - 0.06), (w, -0.2)):
                z = ell_z(x, yy, R)
                ring.append((x, yb + yy, BALL["zc"] + z + dz))
            rr.append(ring)
        m.loft(rr, S["stripe"], ref=lambda i, k: Vector((0, yb + (ya + yb2) / 2, BALL["zc"] + 2.0)))
    band(-2.2, 1.8)
    band(6.75, 7.72, n=4)
    # dark sight slit across the ball south of the band: an inlay strip, chamfered
    rr = []
    for i in range(5):
        yy = -3.1 + 0.8 * i / 4
        ring = []
        for x, dz in ((-2.0, -0.25), (-2.0, 0.04), (-1.9, 0.08), (1.9, 0.08), (2.0, 0.04), (2.0, -0.25)):
            ring.append((x, yb + yy, BALL["zc"] + ell_z(x, yy, R) + dz))
        rr.append(ring)
    m.loft(rr, S["slit"], ref=lambda i, k: Vector((0, yb - 2.7, BALL["zc"] + 2.0)))

    # ---- hood: two clamshell halves, the pillar section on its axis ---------------------------
    hw = pchip([-1.7, -1.2, -0.5, 0.4, 1.6, 9.8, 10.7, 11.7, 12.6, 13.2], [5.0, 6.0, 7.0, 7.8, 8.0, 8.0, 7.15, 6.15, 4.6, 3.7])
    GROOVE_U, GW, GD = 10.3, 0.22, 0.18
    hus = [-1.7, -1.4, -1.0, -0.5, 0, 0.4, 0.9, 1.6, 3, 5, 7, 7.18, 7.2, 9, 9.8,
           GROOVE_U - GW - 0.06, GROOVE_U - GW, GROOVE_U + GW, GROOVE_U + GW + 0.06,
           10.7, 11.2, 11.7, 12.2, 12.4, 12.6, 12.95, 13.05, 13.2]
    NOSE_CH = 0.4   # the nose (south end) of each half closes on a chamfer, not a flat disc

    for side in (-1, 1):
        st = []
        for u in hus:
            W = hw(u)
            H = min(HOOD_H, W * K) * (0.84 + 0.1 * max(0, u) if u < 1.6 else 1.0)
            g = GROOVE_U - GW - 1e-6 <= u <= GROOVE_U + GW + 1e-6
            if g:
                W, H = W - GD, H - GD
            if u >= 13.2:
                W, H = W - NOSE_CH, H - NOSE_CH
            if side > 0:
                d = 0.35 if 7.2 <= u <= 12.4 else 0.0
                s = dict(y=Y(u), W=W, H=H, x0=CUT[1], notches=[(1.0, 3.0, d)], cut=CUT[1], dx=o,
                         extra=(CUT[1] + SEAM_CH, CUT[1] + SEAM_CH * 0.5))
            else:
                s = dict(y=Y(u), W=W, H=H, x1=CUT[0], cut=CUT[0], dx=-o,
                         extra=(CUT[0] - SEAM_CH, CUT[0] - SEAM_CH * 0.5))
            st.append(s)

        def hmat(c, side=side):
            if side > 0 and 1.0 < c.x - o < 3.0 and Y(12.35) < c.y < Y(7.25) and c.z > zt(c.x - o, 8, 5, ZA) - 0.55:
                return S["channel"]
            return S["hood"]
        loft_y(m, st, hmat)
        # slide-actuator cap on the outer wall (a stepped boss, 0.2 px proud)
        bx, bu, br = side * (8.0 + o), 3.2, 2.0
        R2 = []
        for rr_, dx in ((br, -0.1), (br, 0.08), (br * 0.82, 0.2), (br * 0.55, 0.2), (br * 0.5, 0.28), (0.01, 0.28)):
            R2.append([(bx + side * dx, Y(bu) + math.cos(2 * math.pi * j / 20) * rr_, ZA + math.sin(2 * math.pi * j / 20) * rr_)
                       for j in range(20)])
        m.loft(R2, S["boss"], cap0=True, cap1=False, ref=lambda i, k, bx=bx: Vector((bx - side * 1.0, Y(bu), ZA)))

    # core between the halves (dark red), its black launch port a 1.1 px recess
    cs = []
    for u, dz in ((5.4, 0), (6.5, 0), (7.18, 0), (7.2, 1.1), (9.2, 1.1), (9.22, 0), (10.5, 0), (11.5, 0), (12.4, 0), (12.9, 0)):
        H0 = min(HOOD_H, hw(u) * K)
        cs.append(dict(y=Y(u), W=min(3.5, hw(u) - 0.6), H=H0 - 0.9 - dz, dx=-0.5))
    loft_y(m, cs, lambda c: S["port"] if (Y(9.21) < c.y < Y(7.19) and c.z > 5.5) else S["core"])
    # slide rods for the halves
    for u in (3.8, 11.0):
        ring = [(Y(u) + 0.6 * math.cos(2 * math.pi * j / 10), 2.2 + 0.6 * math.sin(2 * math.pi * j / 10)) for j in range(10)]
        m.loft([[(-6.4 - o, y, z) for y, z in ring], [(6.4 + o, y, z) for y, z in ring]], S["rod"],
               ref=lambda i, k, u=u: Vector((0.0, Y(u), 2.2)))

    # ---- neck: telescoping ram on the pillar axis, chamfered stage lips ------------------------
    u_max = 28 - b_row
    stages = [(13.2, 14.2, 3.0, 1.4), (14.2, 15.2, 4.0, 2.0), (15.2, 16.2, 5.0, 2.0), (16.2, 30, 6.0, 2.0)]
    for i, (u0, u1, W, sw) in enumerate(stages):
        if u0 >= u_max - 0.05:
            continue
        u1 = min(u1, u_max)
        H = W * K
        nt = [(-sw, sw, 0.55)]
        ch = 0.22
        st = [dict(y=Y(u0), W=W - ch, H=H - ch, notches=nt), dict(y=Y(u0 + ch), W=W, H=H, notches=nt),
              dict(y=Y(u1), W=W, H=H, notches=nt)]

        def rmat(c, H=H, sw=sw, u0=u0, u1=u1):
            if abs(c.x) < sw and c.z > ZA + H - 0.7 and Y(u1) + 0.01 < c.y < Y(u0) - 0.01:
                return S["ram_slot"]
            return S["ram"]
        loft_y(m, st, rmat)
    return m


def build_wreck(S):
    """Frame 91: the ram's collar torn open on top (dark inside), the ball and hood gone, a bent rod."""
    m = Mesh()
    STEP = [(21.0, 0, 4), (21.95, 0, 4), (22.0, -2, 4), (23.95, -2, 4), (24.0, -3, 5), (24.95, -3, 5), (25.0, -4, 5), (27.0, -4, 5)]
    outer, inner = [], []
    for r, a, b in STEP:
        c, W, y, H = (a + b) / 2, (b - a) / 2, 14 - r, 4.2
        zr = 5.6 + (r - 21) * 0.6 if r < 23 else 6.8
        ring, ring_in = [], []
        for i in range(13):
            t = math.pi + math.pi * i / 12
            cs, sn = math.cos(t), math.sin(t)
            ring.append((c + W * math.copysign(abs(cs) ** (2 / PE), cs), y, max(ZF, ZA + H * math.copysign(abs(sn) ** (2 / PE), sn))))
            ring_in.append((c + (W - 0.9) * math.copysign(abs(cs) ** (2 / PE), cs), y,
                            max(ZF + 0.8, ZA + (H - 0.9) * math.copysign(abs(sn) ** (2 / PE), sn))))
        ring = [(c - W, y, zr)] + ring + [(c + W, y, zr)]
        ring_in = [(c - W + 0.9, y, zr)] + ring_in + [(c + W - 0.9, y, zr)]
        outer.append(ring)
        inner.append(list(reversed(ring_in)))
    shell = [o_ + i_ for o_, i_ in zip(outer, inner)]
    m.loft(shell, lambda c: S["wreck_in"] if (c.z < 6.5 and abs(c.x - 0.5) < 3.4 and c.y < -7.1) else S["wreck"],
           cap0=True, cap1=False,
           outf=lambda c, i, k: (Vector((c.x, c.y, c.z)) - Vector(((STEP[k][1] + STEP[k][2]) / 2, c.y, ZA))) * (1 if (i < 15 or i == 29) else -1))
    for a, b in ((-4, -3), (4, 5)):
        sq = [(a, -13), (b, -13), (b, -14), (a, -14)]
        m.loft([[(x, y, ZF) for x, y in sq], [(x, y, 6.6) for x, y in sq]], S["wreck"])
    sq = [(1, -6.05), (3, -6.05), (3, -7.0), (1, -7.0)]
    m.loft([[(x, y, 3.5) for x, y in sq], [(x, y, 6.4) for x, y in sq]], S["wreck_rod"])
    pts = [(1.5, -7.0, 5.0), (1.5, -5.5, 5.6), (1.6, -4.0, 6.6), (1.8, -2.9, 7.4)]
    m.loft([[(p[0] + 0.55 * math.cos(2 * math.pi * j / 8), p[1], p[2] + 0.55 * math.sin(2 * math.pi * j / 8)) for j in range(8)]
            for p in pts], S["wreck_rod"])
    return m


# --- materials ---------------------------------------------------------------------------------------

def materials(sprite, frame):
    tag = f"{NAME}A_{frame}"

    def pal(i, role, **kw):
        return common.palette_material(sprite, i, f"{tag}_{role}", **kw)
    mats, S = [], {}

    def add(role, i, **kw):
        S[role] = len(mats)
        mats.append(pal(i, role, **kw))
    if FR[frame].get("wreck"):
        add("wreck", PAL["wreck"], metallic=0.5, roughness=0.5)
        add("wreck_in", PAL["wreck_in"], metallic=0.2, roughness=0.8)
        add("wreck_rod", PAL["wreck_rod"], metallic=0.6, roughness=0.4)
        return mats, S
    add("ball", PAL["ball"], metallic=0.55, roughness=0.44)
    add("bezel", PAL["bezel"], metallic=0.6, roughness=0.38)
    add("socket", PAL["socket"], metallic=0.2, roughness=0.7)
    add("lens_off", PAL["lens_off"], metallic=0.0, roughness=0.15)
    add("stripe", PAL["stripe"], metallic=0.25, roughness=0.4)
    add("slit", PAL["slit"], metallic=0.3, roughness=0.6)
    add("hood", PAL["hood"], metallic=0.28, roughness=0.42)
    add("channel", PAL["channel"], metallic=0.25, roughness=0.55)
    add("boss", PAL["boss"], metallic=0.6, roughness=0.4)
    add("core", PAL["core"], metallic=0.25, roughness=0.55)
    add("port", PAL["port"], metallic=0.1, roughness=0.85)
    add("rod", PAL["rod"], metallic=0.65, roughness=0.35)
    add("ram", PAL["ram"], metallic=0.55, roughness=0.42)
    add("ram_slot", PAL["ram_slot"], metallic=0.2, roughness=0.75)
    E = FR[frame]["eye"]
    if E:
        add("eye_core", E[0], metallic=0.0, roughness=0.2, emission_strength=4.0)
        add("eye_rim", E[1], metallic=0.0, roughness=0.2, emission_strength=2.5)
    return mats, S


def build(sprite, frame, coll):
    mats, S = materials(sprite, frame)
    m = build_wreck(S) if FR[frame].get("wreck") else build_head(frame, S)
    obj = m.finish(model_name(frame), mats, coll)
    common.frame_part(obj, [frame])
    return obj


def sprite_for(frame):
    if frame == 91:
        d = json.loads((REF91 / NAME / "sprite.json").read_text())
    else:
        d = json.loads((WT / "reference" / "models" / NAME / "sprite.json").read_text())
    fr = next(f for f in d["frames"] if f["index"] == frame)
    return d, [[int(v) for v in r.split()] for r in fr["pixels"]]


# --- rendering ---------------------------------------------------------------------------------------

def camera(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cam = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def setup_eevee(scene):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.30, 0.32, 0.36, 1)
    bg.inputs["Strength"].default_value = 1.0
    if "v_sun" not in bpy.data.objects:
        sun = bpy.data.lights.new("v_sun", "SUN")
        sun.energy = 3.4
        sun.angle = math.radians(8)
        o = bpy.data.objects.new("v_sun", sun)
        scene.collection.objects.link(o)
        o.rotation_euler = (math.radians(38), math.radians(-22), math.radians(-30))
        fill = bpy.data.lights.new("v_fill", "SUN")
        fill.energy = 0.9
        f = bpy.data.objects.new("v_fill", fill)
        scene.collection.objects.link(f)
        f.rotation_euler = (math.radians(-50), math.radians(30), math.radians(150))


def render(scene, cam, objs, path, res):
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def top_mask(scene, obj, path, k=8):
    """Orthographic top view on the sprite grid (24k x 28k), alpha, Workbench, for sprite_mask."""
    eng = scene.render.engine
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1, 1, 1)
    scene.render.film_transparent = True
    cam = camera(scene, "v_mask", (0, 0, 20), (0, 0, 0), ortho=28 / 12)
    cam.rotation_euler = (0, 0, 0)
    render(scene, cam, [obj], path, (24 * k, 28 * k))
    bpy.data.objects.remove(cam, do_unlink=True)
    scene.render.engine = eng
    scene.render.film_transparent = False


def index_render(scene, obj, path, k=8):
    """Top view where each face shows its material's palette index (R = index / 255, flat)."""
    eng = scene.render.engine
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    vt = scene.view_settings.view_transform
    scene.view_settings.view_transform = "Raw" if "Raw" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items_static] else "Standard"
    saved = [mt.diffuse_color[:] for mt in obj.data.materials]
    for mt in obj.data.materials:
        idx = int(mt.name.split("_")[1])
        mt.diffuse_color = (idx / 255, 0, 0, 1)
    cam = camera(scene, "v_idx", (0, 0, 20), (0, 0, 0), ortho=28 / 12)
    cam.rotation_euler = (0, 0, 0)
    render(scene, cam, [obj], path, (24 * k, 28 * k))
    bpy.data.objects.remove(cam, do_unlink=True)
    for mt, c in zip(obj.data.materials, saved):
        mt.diffuse_color = c
    scene.view_settings.view_transform = vt
    scene.render.engine = eng
    scene.render.film_transparent = False


def import_ctx(path, offset):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objs = []
    for o in set(bpy.data.objects) - before:
        if o.type == "MESH" and "outline" not in o.name:
            o.location = (o.location.x + offset[0], o.location.y + offset[1], o.location.z)
            objs.append(o)
        elif o.type == "MESH":
            o.hide_render = True
    return objs


def views(scene, objs, outdir):
    setup_eevee(scene)
    outdir.mkdir(parents=True, exist_ok=True)
    pillar = import_ctx(WT / "public" / "models" / "enemies" / "newshc-115.glb", (0, -28 / 12))
    D = 6
    cams = {
        "top": ((0, 0, 20), (0, 0, 0), 2.6),
        "side": ((D, 0, 0.5), (0, 0, 0.5), 2.6),
        "front": ((0, -D, 0.5), (0, 0, 0.5), 2.0),
        "rear": ((0, D, 0.5), (0, 0, 0.5), 2.0),
        "q34": ((-3.2, -3.4, 3.4), (0, 0.1, 0.35), None),
        "q34r": ((3.2, 3.4, 3.0), (0, 0.1, 0.35), None),
        "game": ((0, -0.5 - 6 * math.sin(math.radians(32)), 6 * math.cos(math.radians(32))), (0, -0.5, 0.3), None),
        "under": ((1.6, -2.6, -3.0), (0, 0, 0.3), None),
    }
    sets = {
        "top": [77, 83, 89], "side": [77, 89], "front": [83, 89], "rear": [77], "q34": [77, 87], "q34r": [85],
        "game": [77, 81, 83, 87, 89, 91], "under": [77],
    }
    for key, (loc, look, ortho) in cams.items():
        cam = camera(scene, f"v_{key}", loc, look, ortho=ortho, lens=55)
        if key == "top":
            cam.rotation_euler = (0, 0, 0)
        for fr in sets[key]:
            sel = [objs[fr]] + (pillar if key in ("game", "side") else [])
            render(scene, cam, sel, outdir / f"{key}_{fr}.png", (520, 420) if key != "top" else (420, 490))
        bpy.data.objects.remove(cam, do_unlink=True)


def wreck_shell(obj, coll):
    """common.outline_shell keeps only the largest island of the remeshed model, and the wreck is
    several separate pieces (collar, two posts, rod): shell each loose part and join the shells."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen, groups = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, grp = [f], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            grp.append(x.index)
            for e in x.edges:
                stack.extend(o for o in e.link_faces if o.index not in seen)
        groups.append(grp)
    bm.free()
    shells = []
    for gi, grp in enumerate(groups):
        part = obj.copy()
        part.data = obj.data.copy()
        coll.objects.link(part)
        b = bmesh.new()
        b.from_mesh(part.data)
        keep = set(grp)
        b.faces.ensure_lookup_table()
        bmesh.ops.delete(b, geom=[f for f in b.faces if f.index not in keep], context="FACES")
        b.to_mesh(part.data)
        b.free()
        shells.append((part, common.outline_shell(part, coll, voxel=0.01, faces=300, smooth=4, inside=0.004)))
    bpy.ops.object.select_all(action="DESELECT")
    for _, sh in shells:
        sh.select_set(True)
    bpy.context.view_layer.objects.active = shells[0][1]
    bpy.ops.object.join()
    res = bpy.context.view_layer.objects.active
    for part, _ in shells:
        bpy.data.objects.remove(part, do_unlink=True)
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    try:
        sp91 = json.loads((REF91 / NAME / "sprite.json").read_text())
        sprite["colors"].update({k: v for k, v in sp91.get("colors", {}).items() if k not in sprite["colors"]})
    except OSError:
        pass
    coll = common.reset_collection(NAME + "_A")
    scene = bpy.context.scene
    objs, shells = {}, []
    tris = {}
    for fr in FRAMES:
        obj = build(sprite, fr, coll)
        objs[fr] = obj
        tris[fr] = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    sheet = sprite["sprites"][0]
    for fr, obj in objs.items():
        # the frame-91 wreck is thin and in pieces: a coarser shell keeps all of it
        if fr == 91:
            sh = wreck_shell(obj, coll)
        else:
            sh = common.outline_shell(obj, coll, voxel=0.012, faces=1400, smooth=6)
        sh.name = sh.data.name = f"{obj.name}_outline"
        common.frame_part(sh, [fr])
        shells.append(sh)
        common.export_sprite_model(WT, [obj, sh], f"enemies/{obj.name}", [{**sheet, "frames": [fr]}])
    print("TRIS", json.dumps(tris))
    if "--measure" in argv:
        md = Path(argv[argv.index("--measure") + 1])
        md.mkdir(parents=True, exist_ok=True)
        for fr, obj in objs.items():
            top_mask(scene, obj, md / f"top_{fr}.png")
            index_render(scene, obj, md / f"idx_{fr}.png")
        (md / "tris.json").write_text(json.dumps(tris))
    if "--views" in argv:
        views(scene, objs, Path(argv[argv.index("--views") + 1]))


if __name__ == "__main__":
    main()
