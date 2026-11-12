"""Opened sensor pod (newshe.shp frame 235, 24 x 28 px, palette 5): a hard-surface machine that
is its sprite in 3D (D50-D53, D74).

Reading of the sprite: an armoured collar ring open to the ground, the shell of a sensor pod split
open. Its wall is a thin lip at the back and left (1 px) and thickens into a heavy armoured
crescent at the front and right (3-4 px), whose inner edge is a dark liner band (64-65) and whose
outer face is the lit armour (67-77). Inside sits the sensor: a salmon sphere (palette 73; its
near-white spot is sheen), gripped by a dark manipulator arm that rises from the front wall
(sprite cols 12-13, row 17), carries a pale lens knuckle (77, col 12 row 15), elbows at row 11 and
forks: one finger straight into the ball's right side (row 11), one hooking over its top (row 9).

Top-view edge: the INNER edge of the sprite's ink border (D74, tools/sprite_mask.py). The ring's
plan is fitted to that mask: inner and outer radii along rays from the bowl's centre, read from
the mask (bilinear between pixel centres, so the 0.5 crossing is the pixel edge) and low-passed
(Fourier) so the ring is round where the sprite is round.

Built in sprite px (c = column edge, r = row edge, z up from the ground), moved to Blender at the
end: X = (c - 12) / 12, Y = (14 - r) / 12, Z = z / 12.

Ring section (from the inner edge out): a dark liner lip, a V seam (panel line), the armour top,
a chamfer, a steep upper armour face, a belt seam (the pod's split line), a flared skirt, a foot. Radial panel seams split the thick crescent into plates,
with hex bolts on each plate. Underside: the closed flat bottom of the ring (no detail).

Run: blender --background --python assets/blender/enemies/newshe-235.py -- [--no-bake] [--out x.glb]
     [--preview out.png]
(no --out: public/models/enemies/newshe-235.glb and src/render/spriteModels/newshe-235.json)
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (cull_hidden, join, bake_maps)

NAME = "newshe-235"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
WT = ROOT
PX = 1 / 12

# --- materials ---------------------------------------------------------------------------------
# (slot, palette index, metallic, roughness). Indices: per-region medians of the sprite (ink 16
# dropped, darkest/brightest 15% trimmed as lighting). Satin metal.
MATS = [
    ("armour", 68, 0.35, 0.45),   # ring armour: outer rim pixels median 68
    ("glacis", 69, 0.35, 0.45),   # front/right glacis plates: median 69
    ("lip", 67, 0.35, 0.45),      # thin back/left lip: median 67
    ("liner", 65, 0.3, 0.5),      # dark inner liner band of the thick crescent (64-65)
    ("arm", 65, 0.4, 0.4),        # manipulator arm (claw pixels, ink dropped: 65)
    ("ball", 73, 0.25, 0.3),      # sensor sphere (median 73)
    ("lens", 77, 0.1, 0.15),      # lens knuckle on the arm (77)
    ("bolt", 70, 0.45, 0.35),     # bolt heads, catching light
    ("seam", 64, 0.2, 0.6),       # seam floors, sockets, pedestal
    ("ballseam", 66, 0.25, 0.4),  # the sphere's fine split line: a shade darker, not black
]
M = {name: i for i, (name, *_r) in enumerate(MATS)}
UNBAKED = {M["lens"]}


def materials(sprite):
    return [common.palette_material(sprite, idx, f"{NAME}_{name}", metallic=met, roughness=rough)
            for name, idx, met, rough in MATS]


# --- the plan, fitted to the sprite's inner mask ------------------------------------------------

def load_mask():
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as S
    idx, colors = S.load(NAME)
    m = S.masks(idx, colors)
    return m


BALL_PX = {(10, c) for c in range(8, 11)} | {(11, c) for c in range(7, 12)} | \
    {(12, c) for c in range(7, 12)} | {(13, c) for c in range(7, 11)}
CLAW_PX = {(9, 11), (9, 12), (10, 11), (10, 13), (11, 11), (11, 12), (11, 13), (11, 14), (12, 13), (12, 14),
           (13, 13), (14, 12), (14, 13), (15, 11), (15, 12), (15, 13), (16, 12), (17, 12), (17, 13)}
CEN = (11.2, 13.6)   # rays for the ring's radii start here (inside the bowl)
N = 120              # angular samples round the ring
HARM_OUT = 5         # Fourier harmonics kept: the outer edge is a smooth oval
HARM_IN = 7          # the opening a little freer


def ring_field(m):
    H, W = len(m["inner"]), len(m["inner"][0])
    F = [[0.0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if (r, c) in BALL_PX or (r, c) in CLAW_PX:
                continue
            if m["inner"][r][c] or m["free"][r][c]:
                F[r][c] = 1.0
    F[11][17] = F[11][18] = 0.45  # the right wall's ink notch at row 11: keep the ring whole

    def at(x, y):
        x -= 0.5
        y -= 0.5
        c0, r0 = math.floor(x), math.floor(y)
        fx, fy = x - c0, y - r0

        def g(r, c):
            return F[r][c] if 0 <= r < H and 0 <= c < W else 0.0
        return ((1 - fx) * (1 - fy) * g(r0, c0) + fx * (1 - fy) * g(r0, c0 + 1)
                + (1 - fx) * fy * g(r0 + 1, c0) + fx * fy * g(r0 + 1, c0 + 1))
    return at


def lowpass(vals, k):
    """Fourier series of vals (uniform round the circle) cut to k harmonics, as a function of
    the angle in radians."""
    n = len(vals)
    coef = []
    for h in range(k + 1):
        a = sum(v * math.cos(2 * math.pi * h * i / n) for i, v in enumerate(vals)) * 2 / n
        b = sum(v * math.sin(2 * math.pi * h * i / n) for i, v in enumerate(vals)) * 2 / n
        coef.append((a / (2 if h == 0 else 1), b))
    return lambda t: sum(a * math.cos(h * t) + b * math.sin(h * t) for h, (a, b) in enumerate(coef))


def fit_plan(m):
    at = ring_field(m)
    rin, rout = [], []
    for i in range(N):
        a = 2 * math.pi * i / N
        dx, dy = math.cos(a), math.sin(a)
        r = 0.0
        while at(CEN[0] + r * dx, CEN[1] + r * dy) < 0.5 and r < 14:
            r += 0.01
        rin.append(r)
        r = 14.0
        while at(CEN[0] + r * dx, CEN[1] + r * dy) < 0.5 and r > 0:
            r -= 0.01
        rout.append(r)
    fin, fout = lowpass(rin, HARM_IN), lowpass(rout, HARM_OUT)
    return fin, lambda t: max(fout(t), fin(t) + 0.9)


# --- solids --------------------------------------------------------------------------------------

class Model:
    def __init__(self):
        self.parts = []

    def add(self, bm, smooth=35):
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self.parts.append((bm, smooth))
        return bm

    def hull(self, pts, mat, smooth=30):
        bm = bmesh.new()
        verts = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
        for f in bm.faces:
            f.material_index = mat
        return self.add(bm, smooth)

    def revolve(self, centre, axis, profile, n=20, smooth=50):
        """A closed solid of revolution about `axis` through `centre`; profile [(t, radius, mat)]:
        t along the axis, radius 0 = on the axis; mat is the band from this point to the next."""
        ax = Vector(axis).normalized()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        u = ax.cross(ref).normalized()
        v = ax.cross(u)
        C = Vector(centre)
        bm = bmesh.new()
        rings = []
        for t, rad, _ in profile:
            if rad < 1e-6:
                rings.append([bm.verts.new(C + ax * t)])
            else:
                rings.append([bm.verts.new(C + ax * t + (u * math.cos(2 * math.pi * k / n) + v * math.sin(2 * math.pi * k / n)) * rad)
                              for k in range(n)])
        for (_, _, mat), r0, r1 in zip(profile, rings, rings[1:]):
            for k in range(n):
                j = (k + 1) % n
                if len(r0) == 1:
                    vs = (r0[0], r1[k], r1[j])
                elif len(r1) == 1:
                    vs = (r0[k], r1[0], r0[j])
                else:
                    vs = (r0[k], r1[k], r1[j], r0[j])
                f = bm.faces.new(vs)
                f.material_index = mat
        if len(rings[0]) > 1:
            bm.faces.new(rings[0]).material_index = profile[0][2]
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1]).material_index = profile[-1][2]
        return self.add(bm, smooth)

    def tube(self, path, radius, mat, sides=10, smooth=50):
        """A closed pipe of constant radius along path [(c, r, z)], mitred at the bends."""
        P = [Vector(p) for p in path]
        tans = []
        for k in range(len(P)):
            a = P[max(k - 1, 0)]
            b = P[min(k + 1, len(P) - 1)]
            tans.append((b - a).normalized())
        ref = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
        n0 = tans[0].cross(ref).normalized()
        bm = bmesh.new()
        rings = []
        nrm = n0
        for k, (p, t) in enumerate(zip(P, tans)):
            nrm = (nrm - t * nrm.dot(t)).normalized()
            bi = t.cross(nrm)
            # mitre: widen the ring at a bend
            sc = 1.0
            if 0 < k < len(P) - 1:
                d0 = (P[k] - P[k - 1]).normalized()
                d1 = (P[k + 1] - P[k]).normalized()
                sc = 1 / max(0.6, math.cos(d0.angle(d1) / 2)) if d0.dot(d1) < 0.9999 else 1.0
            rings.append([bm.verts.new(p + (nrm * math.cos(2 * math.pi * s / sides) + bi * math.sin(2 * math.pi * s / sides)) * radius * (1 + (sc - 1) * 0.5))
                          for s in range(sides)])
        for r0, r1 in zip(rings, rings[1:]):
            for s in range(sides):
                j = (s + 1) % sides
                bm.faces.new((r0[s], r0[j], r1[j], r1[s])).material_index = mat
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat
        return self.add(bm, smooth)


def sphere_profile(rad, mat, n=12, groove=None, gmat=None):
    """Profile for revolve(): a sphere of radius rad from -rad to +rad along the axis, with an
    optional V groove (a seam) at axis position `groove`."""
    prof = []
    for k in range(n + 1):
        a = math.pi * k / n
        t = -rad * math.cos(a)
        prof.append([t, rad * math.sin(a), mat])
    if groove is not None:
        g0, g1 = groove - 0.07, groove + 0.07
        prof = [p for p in prof if not (g0 - 0.05 < p[0] < g1 + 0.05)]
        rr = lambda t: math.sqrt(max(rad * rad - t * t, 0))
        ins = [[g0, rr(g0), gmat], [groove, rr(groove) - 0.09, gmat], [g1, rr(g1), mat]]
        prof = sorted(prof + ins, key=lambda p: p[0])
        for i in range(len(prof) - 1):
            if prof[i][0] < g0 - 1e-6:
                prof[i][2] = mat
    prof[0][1] = 0.0
    prof[-1][1] = 0.0
    return [tuple(p) for p in prof]


# --- the ring ------------------------------------------------------------------------------------

SEAMS_DEG = None  # filled by build_ring: angles of the radial seams


def lean(a):
    """How much of the liner's lean (0-1) the wall has at angle a (radians, image axes): full on
    the right crescent, none at the front band and round the thin back/left lip."""
    deg = (math.degrees(a) + 180) % 360 - 180
    return min(max((75 - deg) / 30, 0.0), 1.0) if deg > -30 else min(max((deg + 60) / 30, 0.0), 1.0)


def section(t, w=1.0):
    """(d, z) points of the ring's section for wall thickness t (sprite px), inner edge d = 0:
    inner face, chamfer, dark liner lip, a V seam, the armour top, a chamfer, the upper armour
    face, the belt seam, the lower skirt and the foot. Thin walls are the same section squeezed."""
    tt = max(t, 2.4)
    hA = 2.7 + 0.3 * min(t, 4.0)
    hL = hA + 0.15
    wl = min(max(0.36 * tt, 0.5), 1.25)
    g = 0.11
    wa = wl + g + max(0.25, min(0.6, 0.2 * tt))
    # thick walls: the inner liner face leans out as it rises (a funnel), widening the dark liner
    # band in plan to the sprite's 2-3 px while the outer plan stays put
    sl = w * min(max(0.45 * (tt - 1.5), 0.0), 1.15)
    pts = [(0.0, 0.0)] + [(d + sl, z) for d, z in
                          [(0.0, hL - 0.2), (0.2, hL), (wl - g, hL), (wl, hL - 0.4), (wl + g, hA), (wa, hA)]]
    wa += sl
    # outer face: a crisp chamfer, the steep upper armour face, the belt seam (the pod's split
    # line), then a lower skirt flaring out to the foot. Faceted, not puffed: machined plate.
    zm = 0.52 * hA
    dm = wa + 0.2 + 0.5 * (tt - wa - 0.2)
    pts += [(wa + 0.2, hA - 0.2), (dm, zm + 0.1), (dm - 0.14, zm - 0.04), (dm - 0.02, zm - 0.18),
            (tt - 0.06, 0.42), (tt, 0.3)]
    pts.append((tt, 0.0))
    s = t / tt
    return [(d * s, z) for d, z in pts]


def build_ring(m, fin, fout):
    # Sample angles (radians, image axes: 0 = +c, pi/2 = +r, down the sprite): uniform, plus a
    # narrow radial panel seam (a sunk sample between two close flanks) every 36 degrees round the
    # thick crescent.
    base = [2 * math.pi * i / N for i in range(N)]
    seam_deg = [d for d in range(-36, 180, 36) if fout(math.radians(d)) - fin(math.radians(d)) > 2.2]
    seams = [math.radians(d) % (2 * math.pi) for d in seam_deg]
    fl = math.radians(0.5)
    angs = [(a, False) for a in base if all(abs((a - sa + math.pi) % (2 * math.pi) - math.pi) > 1.6 * fl for sa in seams)]
    for sa in seams:
        angs += [(sa - fl, False), (sa, True), (sa + fl, False)]
    angs.sort()
    thick = [fout(a) - fin(a) for a, _ in angs]
    bm = bmesh.new()
    rings = []
    for (a, is_seam), t in zip(angs, thick):
        u = (math.cos(a), math.sin(a))
        sec = section(t, lean(a))
        if is_seam:
            # the seam: armour top and shell face sunk into a V
            sec = [(d, z - 0.3) if k in (5, 6) else ((d - 0.25, z) if 7 <= k <= len(sec) - 2 else (d, z))
                   for k, (d, z) in enumerate(sec)]
        rin = fin(a)
        rings.append([bm.verts.new((CEN[0] + (rin + d) * u[0], CEN[1] + (rin + d) * u[1], z)) for d, z in sec])
    N2 = len(rings)
    nsec = len(rings[0])
    for i in range(N2):
        j = (i + 1) % N2
        tk = 0.5 * (thick[i] + thick[j])
        a0, a1 = angs[i][0], angs[j][0] + (2 * math.pi if j == 0 else 0.0)
        deg = (math.degrees(0.5 * (a0 + a1)) + 180) % 360 - 180   # image axes, -90 = the back
        # The sprite's back-right quadrant (rows 7-13, right of col 11) is the dark 64/65 liner
        # band right across the wall, running from the right crescent round to the top; the lit
        # 67 lip is the back-left only, the rim 68 on the right, the glacis 69 at the front.
        back_right = -93 < deg < 0   # ends on the radial plate seam at 0 deg
        for k in range(nsec):
            l = (k + 1) % nsec
            f = bm.faces.new((rings[i][k], rings[j][k], rings[j][l], rings[i][l]))
            if k == nsec - 1:
                mat = M["seam"]  # bottom (unseen)
            elif k in (3, 4):  # the seam's V
                mat = M["seam"] if (tk > 1.7 or back_right) else M["lip"]
            elif k <= 2 or back_right:   # inner face + chamfer + liner top
                mat = M["liner"] if (tk > 1.7 or back_right) else M["lip"]
            elif tk <= 1.7:
                mat = M["lip"]
            else:
                mat = M["armour"] if (deg < 50 or tk <= 2.6) else M["glacis"]
            f.material_index = mat
    m.add(bm, smooth=32)
    # Hex bolts on the armour top, midway between the seams.
    for sa, sb in zip(seams, seams[1:]):
        a = 0.5 * (sa + sb)
        t = fout(a) - fin(a)
        sec = section(t, lean(a))
        d = 0.5 * (sec[5][0] + sec[6][0])
        c = CEN[0] + (fin(a) + d) * math.cos(a)
        r = CEN[1] + (fin(a) + d) * math.sin(a)
        z = sec[5][1]
        pts = []
        for k in range(6):
            ang = math.pi / 3 * k + a
            for rad, zz in ((0.24, z - 0.1), (0.24, z + 0.09), (0.16, z + 0.16)):
                pts.append((c + rad * math.cos(ang), r + rad * math.sin(ang), zz))
        m.hull(pts, M["bolt"])
    # Hinge knuckles on the back lip (sprite cols 11-14, row 7: the ink-only arc there), where
    # the pod's upper shell hinged open: two short barrels on the lip's outer face, a pin through.
    # (the sprite draws them in the dark 65 liner band)
    hm = M["liner"]
    for c0, c1 in ((10.9, 12.0), (12.9, 14.0)):
        m.revolve((c0, 7.22, 2.45), (1, 0, 0), [(0.0, 0.0, hm), (0.0, 0.42, hm), (0.08, 0.5, hm),
                                               (c1 - c0 - 0.08, 0.5, hm), (c1 - c0, 0.42, hm), (c1 - c0, 0.0, hm)], n=12)
    m.revolve((10.6, 7.22, 2.45), (1, 0, 0), [(0.0, 0.0, M["seam"]), (0.0, 0.2, M["seam"]), (3.7, 0.2, M["seam"]), (3.7, 0.0, M["seam"])], n=8)
    return thick, seams


# --- the sensor and its arm ----------------------------------------------------------------------

BALL_C = (9.4, 12.12)
BALL_R = 2.2
BALL_Z = 2.95


def build_sensor(m):
    c, r = BALL_C
    # The sphere, its seam ring a little above the equator.
    m.revolve((c, r, BALL_Z), (0, 0, 1), sphere_profile(BALL_R, M["ball"], n=14, groove=0.55, gmat=M["ballseam"]), n=28, smooth=60)
    # Pedestal under it (hidden from above): a short dark post with a flared foot.
    m.revolve((c, r, 0.0), (0, 0, 1), [(0.0, 0.0, M["seam"]), (0.0, 1.1, M["seam"]), (0.35, 1.1, M["seam"]),
                                     (0.6, 0.7, M["seam"]), (BALL_Z - 1.0, 0.7, M["seam"]), (BALL_Z - 1.0, 0.0, M["seam"])], n=12)
    # Socket collar where the arm's straight finger meets the ball (right side, row 11.5).
    m.revolve((11.15, 11.9, 3.1), (1, 0, 0), [(-0.1, 0.0, M["arm"]), (-0.1, 0.5, M["arm"]), (0.4, 0.5, M["arm"]),
                                             (0.55, 0.36, M["arm"]), (0.55, 0.0, M["arm"])], n=12)


def build_arm(m):
    R = 0.34
    # Stalk: from inside the front wall (row 19) up the col-13 line to the elbow (row 11.5).
    stalk = [(12.9, 19.4, 1.3), (12.9, 18.0, 2.1), (12.92, 16.6, 2.7), (12.95, 15.0, 3.05),
             (13.25, 13.4, 3.35), (13.6, 11.7, 3.55)]
    m.tube(stalk, R, M["arm"], sides=10)
    # Base clamp where it leaves the wall: a chamfered block sunk in the liner.
    m.hull([(c, r, z) for c in (12.45, 13.55) for r in (18.6, 19.6) for z in (0.0, 2.1)] +
           [(c, r, 2.45) for c in (12.6, 13.4) for r in (18.8, 19.4)], M["arm"])
    # Knuckle joint (sprite cols 12-13, rows 14-15): a drum across the arm, its pale lens facing
    # up-left (the 77 pixel).
    kc = (12.9, 15.0, 3.05)
    m.revolve((kc[0] - 0.8, kc[1], kc[2]), (1, 0, 0), [(0.0, 0.0, M["arm"]), (0.0, 0.7, M["arm"]), (0.12, 0.85, M["arm"]),
                                                     (1.48, 0.85, M["arm"]), (1.6, 0.7, M["arm"]), (1.6, 0.0, M["arm"])], n=14)
    # The lens: a pale domed eye about 1 px across, centred on the sprite's 77 pixel (col 12,
    # row 15), seated in a dark bezel on the drum's top and tipped a little up-left.
    m.revolve((12.5, 15.5, 3.45), (-0.2, -0.08, 0.98), [(0.0, 0.0, M["arm"]), (0.0, 0.6, M["arm"]), (0.32, 0.6, M["arm"]),
                                                       (0.36, 0.0, M["arm"])], n=14)
    m.revolve((12.5, 15.5, 3.45), (-0.2, -0.08, 0.98), [(0.2, 0.0, M["lens"]), (0.2, 0.5, M["lens"]), (0.4, 0.46, M["lens"]),
                                                       (0.52, 0.3, M["lens"]), (0.58, 0.0, M["lens"])], n=14)
    # Elbow joint.
    m.revolve((13.65, 11.6, 3.55), (0, 0, 1), sphere_profile(0.58, M["arm"], n=8), n=12)
    # Straight finger: a stub out right of the elbow, then a thin rod to the ball's socket.
    m.tube([(15.1, 11.6, 3.5), (13.65, 11.6, 3.55)], 0.48, M["arm"], sides=10)
    m.tube([(13.65, 11.6, 3.45), (12.7, 12.0, 3.25), (11.4, 12.0, 3.1)], 0.27, M["arm"], sides=8)
    # Hook finger: up from the elbow, over the ball's top right, down onto it.
    m.tube([(13.65, 11.4, 3.7), (13.55, 10.3, 4.3), (12.95, 9.75, 4.65), (12.2, 9.75, 4.75), (11.5, 9.95, 4.65),
            (10.75, 10.4, 4.4)], 0.29, M["arm"], sides=8)


# --- finishing -----------------------------------------------------------------------------------

def finish(m, mats, coll):
    mat4 = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    objs = []
    for k, (bm, smooth) in enumerate(m.parts):
        bmesh.ops.transform(bm, matrix=mat4, verts=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{NAME}_p{k}")
        bm.to_mesh(me)
        bm.free()
        for mt in mats:
            me.materials.append(mt)
        obj = bpy.data.objects.new(f"{NAME}_p{k}", me)
        coll.objects.link(obj)
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(smooth))
        objs.append(obj)
    return objs


def build(coll, sprite):
    mats = materials(sprite)
    mk = load_mask()
    rin, rout = fit_plan(mk)
    m = Model()
    thick, seams = build_ring(m, rin, rout)
    print("thickness min/max", round(min(thick), 2), round(max(thick), 2), "seams", [round(math.degrees(x)) for x in seams])
    build_sensor(m)
    build_arm(m)
    objs = finish(m, mats, coll)
    return T.join(objs, NAME)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite)
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        T.TEXTURED = tuple(i for i in range(len(MATS)) if i not in UNBAKED)
        T.TINT = (1.0, 1.0, 1.0)
        T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"))
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, faces=1500)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        fr = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / fr["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=fr["size"])


if __name__ == "__main__":
    main()
