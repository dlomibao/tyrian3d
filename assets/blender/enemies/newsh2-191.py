"""Spinning arch (newsh2.shp frames 191-205): a hard-surface machine that is its sprite in 3D (D50-D53).

Seen in episode 1 (levels 25-41) and episode 3 (enemy types 10 and 12). The sprite (24 x 28 px) is
authoritative for the plan, the parts' places and their palette colours.

A horseshoe of bronze armour tiles over a dark core, a wedge in section (deep at its inner edge,
along which run dark steel rails, thin at the crown edge), coming down into two deep ridge-backed
steel leg housings (dark collars at rows 7 and 12, louvres on the sloped faces, vent slots, side
plates) that run on into blades with chisel tips; a flattened bronze barrel pod hangs in the middle
on two chamfered beams with clamp blocks and bearing collars, a louvred hatch on its back and a dark
port deep in its nose. The model is symmetric in Z (the -Z face shows in frames 201-205 as it turns
over), so the detail is mirrored rather than a separate underside.

Depth (Z) comes from the spin frames: edge-on frame 199 draws arch and legs 7 px across (outline
ring included) with a 3 px, then 5 px crown, so the band and legs are about 6.2-6.6 px deep; the
legs' hexagonal section (flat 3 px sides, faces sloping to a narrow ridge) and the band's wedge keep
the frames between (193-197, 201-205) as narrow as they are drawn.

Units in the builders: sprite px. X = pixel-edge column (0..24), Y = pixel-edge row (0 = screen top
= rear), Z = height off the spin plane.

The eight frames turn the whole thing about the screen's vertical axis, so the model is built once
(frame 191, unturned) and exported eight times, each turned about Y through column edge 11.5 to the
angle its frame shows (ANGLES, fitted to each frame's mask: 0, 40, 59, 74.5, 90, then back out
on the other side): newsh2-191 (frame 191), newsh2-191-f2 (193) ... newsh2-191-f8 (205). Frames 197
and 201 draw the leg housings 8 px across (an even count, centred half a pixel off the axis that
frames 191 and 199 fix), so no turned rigid model matches their housing rows exactly.

Palette materials (pal_<index>) so palettes, fades and the hit flash apply; satin metal.
Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50).
Cycles bakes a colour multiplier (ambient occlusion, edge lift) and a roughness/metalness map once
on frame 191's model to assets/blender/textures/newsh2-191/bake/; every frame's model is a turned
copy sharing those UVs and maps. An outline shell (common.outline_shell, D51) rides as a child of
each frame's model.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-191.py
     [-- --preview out.png] [--no-bake]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402

REPO = common.repo_root(__file__)
TAG = "newsh2_191"
NAME = "newsh2-191"
PX = 1 / 12
AX = 11.5  # spin axis (pixel-edge column)
# turn per frame (degrees about Y), fitted to the eight sprite frames' masks (top ortho IoU)
ANGLES = [0.0, 40.0, 59.0, 74.5, 90.0, 105.5, 121.0, 140.0]

# ---------------- tunables (sprite px) ----------------
T = dict(
    bandHW=1.48,   # band radial half width (1 colour px + outline = 3 px)
    bandHD=3.3,    # band half depth at its inner edge: edge-on frame 199 is 7 px across (ring included)
    crestZ=1.3,    # half depth at its outer edge on the crown (199's crown: 3 px, then 5, then 7)
    crestRise=0.5,  # ... deeper where the band turns down (x |tangent y|): 195/203's shoulders
    bandK=0.65,    # the faces slope from the outer edge to 30% inside the centre line (a wedge)
    legHX=1.42, legHZ=3.1,       # leg housing half sizes (199: legs 7 px deep, ring included)
    bladeHX=1.5, bladeHZ=3.05,   # blade half sizes
    legCU=1.17, legCV=1.4,        # leg corner chamfers across (X) and along the depth (Z): the deep
                                 # chamfers keep the near-edge-on frames (193-197) as narrow as drawn
    podFlat=0.8,   # pod depth / width
)
PAL = dict(band=25, joint=163, rail=5, collar=6, housing=11, plate=9, blade=9, tip=7, groove=4,
           strut=7, clamp=4, bearing=4, pod=23, pod_seam=162, pod_low=20, pod_cap=4, hatch=2,
           slot=2, bolt=7, port=2)
# satin metal: (metallic, roughness) per palette index
FINISH = {25: (0.32, 0.42), 23: (0.32, 0.42), 163: (0.25, 0.5), 162: (0.2, 0.55), 21: (0.3, 0.45),
          5: (0.3, 0.45), 4: (0.3, 0.5), 6: (0.3, 0.45), 7: (0.3, 0.45), 9: (0.3, 0.42),
          10: (0.3, 0.42), 2: (0.1, 0.6)}


# ---------------- small vector helpers ----------------
def V(*a):
    return Vector(a)


def P(p):
    """px coordinates (X col edge, Y row edge, Z) -> model units relative to the spin axis."""
    return Vector(((p[0] - AX) * PX, (14 - p[1]) * PX, p[2] * PX))


class Builder:
    """Accumulates parts in one bmesh; each closed part gets its normals recalculated on its own,
    open decals are oriented explicitly."""

    def __init__(self, sprite):
        self.sprite = sprite
        self.bm = bmesh.new()
        self.mats, self.slot = [], {}

    def mat(self, i):
        if i not in self.slot:
            self.slot[i] = len(self.mats)
            m, r = FINISH.get(i, (0.3, 0.45))
            self.mats.append(common.palette_material(self.sprite, i, NAME, metallic=m, roughness=r))
        return self.slot[i]

    def loft(self, rings, pals, cap0=True, cap1=True, cap_pals=None):
        """rings: lists of px points (or a single point); pals: palette index per band (or one)."""
        bm = self.bm
        vs = [[bm.verts.new(P(p)) for p in r] for r in rings]
        faces = []
        for b, (r0, r1) in enumerate(zip(vs, vs[1:])):
            pal = pals[b] if isinstance(pals, (list, tuple)) else pals
            n = max(len(r0), len(r1))
            for i in range(n):
                j = (i + 1) % n
                if len(r0) == 1:
                    q = (r0[0], r1[j], r1[i])
                elif len(r1) == 1:
                    q = (r0[i], r0[j], r1[0])
                else:
                    q = (r0[i], r0[j], r1[j], r1[i])
                f = bm.faces.new(q)
                f.material_index = self.mat(pal)
                faces.append(f)
        first = pals[0] if isinstance(pals, (list, tuple)) else pals
        last = pals[-1] if isinstance(pals, (list, tuple)) else pals
        if cap_pals:
            first, last = cap_pals
        if cap0 and len(vs[0]) > 2:
            f = bm.faces.new(list(reversed(vs[0])))
            f.material_index = self.mat(first)
            faces.append(f)
        if cap1 and len(vs[-1]) > 2:
            f = bm.faces.new(vs[-1])
            f.material_index = self.mat(last)
            faces.append(f)
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        return faces

    def box(self, lo, hi, pal):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        ring = lambda y: [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
        return self.loft([ring(y0), ring(y1)], pal)

    def decal(self, pts, pal, outward):
        """One open polygon (px points) facing along `outward` (a px-space direction)."""
        vs = [self.bm.verts.new(P(p)) for p in pts]
        f = self.bm.faces.new(vs)
        f.material_index = self.mat(pal)
        f.normal_update()
        o = Vector((outward[0], -outward[1], outward[2]))
        if f.normal.dot(o) < 0:
            f.normal_flip()
        return f


# ---------------- section rings (px) ----------------
def ch_ring(o, u, v, hu, hv, ch, chv=None):
    """Chamfered rectangle section: corners cut `ch` along u and `chv` (default ch) along v."""
    cv = ch if chv is None else chv
    pts = [(hu, -hv + cv), (hu, hv - cv), (hu - ch, hv), (-hu + ch, hv), (-hu, hv - cv), (-hu, -hv + cv),
           (-hu + ch, -hv), (hu - ch, -hv)]
    return [tuple(o[k] + u[k] * a + v[k] * b for k in range(3)) for a, b in pts]


def band_ring(o, u, v, hu, hv, hc, ch, k=0.3):
    """Band section: inner side (-u) full depth hv with chamfers, outer side (+u) bevelled to hc;
    the faces slope from u = hu(1 - 2k) out to the outer edge."""
    pts = [(hu, -hc), (hu, hc), (hu - 2 * hu * k, hv), (-hu + ch, hv), (-hu, hv - ch), (-hu, -hv + ch),
           (-hu + ch, -hv), (hu - 2 * hu * k, -hv)]
    return [tuple(o[k2] + u[k2] * a + v[k2] * b for k2 in range(3)) for a, b in pts]


def ell_ring(o, u, v, hu, hv, n=24):
    out = []
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        out.append(tuple(o[k] + u[k] * hu * math.cos(t) + v[k] * hv * math.sin(t) for k in range(3)))
    return out


# ---------------- the band's centre line ----------------
CTRL_L = [(5.5, 7.2), (5.5, 6.1), (5.55, 5.55), (6.2, 4.72), (7.2, 3.92), (7.95, 3.1), (8.7, 2.55),
          (9.75, 2.5), (11.5, 2.5)]


def catmull(Pts, sub=8):
    out = []
    for i in range(len(Pts) - 1):
        p0, p1, p2, p3 = Pts[max(0, i - 1)], Pts[i], Pts[i + 1], Pts[min(len(Pts) - 1, i + 2)]
        for s in range(sub):
            t = s / sub
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in range(2)))
    out.append(Pts[-1])
    return out


class Path2:
    def __init__(self, pts):
        self.p = pts
        self.S = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.S.append(self.S[-1] + math.dist(a, b))
        self.L = self.S[-1]

    def at(self, s):
        S, p = self.S, self.p
        i = 0
        while i < len(S) - 2 and S[i + 1] < s:
            i += 1
        t = (s - S[i]) / max(1e-9, S[i + 1] - S[i])
        x = p[i][0] + (p[i + 1][0] - p[i][0]) * t
        y = p[i][1] + (p[i + 1][1] - p[i][1]) * t
        tx, ty = p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]
        ln = math.hypot(tx, ty) or 1
        tx, ty = tx / ln, ty / ln
        return (x, y, 0.0), (-ty, tx, 0.0), (tx, ty, 0.0)  # point, normal (into the arch), tangent

    def nearest(self, x, y):
        return min(zip(self.p, self.S), key=lambda ps: math.dist(ps[0], (x, y)))[1]

    def sweep(self, s0, s1, sec, step=0.45):
        n = max(1, math.ceil((s1 - s0) / step))
        return [sec(*self.at(s0 + (s1 - s0) * i / n)) for i in range(n + 1)]


Z = (0.0, 0.0, 1.0)


def neg(a):
    return tuple(-q for q in a)


def add(a, b, k=1.0):
    return tuple(a[i] + b[i] * k for i in range(3))


def build_geometry(B):
    ctrl = CTRL_L + [(2 * AX - x, y) for x, y in reversed(CTRL_L[:-1])]
    path = Path2(catmull(ctrl, 8))
    L = path.L
    hd, hc, bk = T["bandHD"], T["crestZ"], T["bandK"]

    def HW(t):
        """Band half width: the sprite's 3 px on the straight runs, thinner across the 45-degree
        shoulders, where its pixel stair is 3 px per row (about 2.1 px measured square to the band)."""
        return T["bandHW"] * (1 - 0.26 * (2 * t[0] * t[1]) ** 2)

    def HC(t):
        """Band half depth at the outer edge: thin on the crown, deeper down the shoulders."""
        return hc + T["crestRise"] * abs(t[1])

    # --- BAND: a wedge section, deep at the inner edge (7 px edge-on) and thin at the crown edge;
    # dark core, bronze armour tiles with real gaps, dark steel rails along the deep inner edge.
    B.loft(path.sweep(0, L, lambda p, n, t: band_ring(p, neg(n), Z, HW(t) * 0.93, hd * 0.88, HC(t) * 0.88, 0.3, bk)),
           PAL["joint"])
    joint_pts = [(5.62, 5.3), (7.5, 3.3), (9.05, 2.58), (11.5, 2.5)]
    joints = sorted([path.nearest(x, y) for x, y in joint_pts] +
                    [path.nearest(2 * AX - x, y) for x, y in joint_pts[:-1]])
    bounds = [0.0] + joints + [L]
    gap = 0.11
    tiles = []
    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        s0 = a + (gap if i else 0.0)
        s1 = b - (gap if i < len(bounds) - 2 else 0.0)
        tiles.append((s0, s1))
        # each tile: a chamfered armour plate, its ends bevelled back (rings pulled in at the ends)
        def sec(p, n, t):
            return band_ring(p, neg(n), Z, HW(t), hd, HC(t), 0.3, bk)
        rings = path.sweep(s0, s1, sec, step=0.42)
        # chamfer the tile ends: shrink the first and last ring slightly, add an inner ring
        def shrink(r, k):
            c = [sum(q[j] for q in r) / len(r) for j in range(3)]
            return [tuple(c[j] + (q[j] - c[j]) * k for j in range(3)) for q in r]
        if len(rings) >= 2:
            p0, n0, t0 = path.at(s0)
            p1, n1, t1 = path.at(s1)
            e0 = band_ring(p0, neg(n0), Z, HW(t0), hd, HC(t0), 0.3, bk)
            e1 = band_ring(p1, neg(n1), Z, HW(t1), hd, HC(t1), 0.3, bk)
            a0 = band_ring(add(p0, t0, 0.12), neg(n0), Z, HW(t0), hd, HC(t0), 0.3, bk)
            a1 = band_ring(add(p1, t1, -0.12), neg(n1), Z, HW(t1), hd, HC(t1), 0.3, bk)
            inner = [r for r in rings[1:-1]]
            rings = [shrink(e0, 0.86) if i else e0, a0] + inner + [a1, shrink(e1, 0.86) if i < len(bounds) - 2 else e1]
        B.loft(rings, PAL["band"])
    # rails along the inner edge, both faces (the frame of the armour)
    for sz in (1, -1):
        off_z = hd - 0.12
        B.loft(path.sweep(0.25, L - 0.25, lambda p, n, t: ch_ring(add(add(p, n, HW(t) - 0.28), Z, sz * off_z), n, Z, 0.24, 0.22, 0.07),
                          step=0.6), PAL["rail"])
    # bolt heads: a pair on each tile's sloped face, both faces, square to the slope
    for s0, s1 in tiles:
        sm = (s0 + s1) / 2
        p, n, t = path.at(sm)
        n = neg(n)  # band_ring's +u: outward, to the crown edge
        hu = HW(t)
        u0 = hu * (1 - 2 * bk)
        m = (hd - HC(t)) / (hu - u0)          # the slope's fall per unit outward
        du = u0 + 0.42 * (hu - u0)
        ln = math.hypot(m, 1)
        for sz in (1, -1):
            nrm = add(tuple(q * m / ln for q in n), (0, 0, sz / ln))
            tan = add(tuple(q / ln for q in n), (0, 0, -sz * m / ln))
            for dt in ((-0.45, 0.45) if s1 - s0 > 1.6 else (0.0,)):
                c = add(add(add(p, n, du), t, dt), (0, 0, sz * (hd - m * (du - u0))))
                B.loft([ell_ring(add(c, nrm, -0.05), tan, t, 0.16, 0.16, 6),
                        ell_ring(add(c, nrm, 0.08), tan, t, 0.13, 0.13, 6),
                        [add(c, nrm, 0.11)]], PAL["bolt"], cap1=False)

    # --- LEGS: deep ridge-backed prisms. The section is a long hexagon: flat outer and inner side
    # faces (the sprite's 3 px from above), sloping up to a narrow ridge on each face, so the legs
    # are 6-7 px deep edge-on (frame 199) and as narrow as drawn in the frames between (193-197).
    H, D, BX, E = T["legHX"], T["legHZ"], T["bladeHX"], T["bladeHZ"]
    CU, CV = T["legCU"], T["legCV"]
    secs = [  # y, hx, hz, chamfer across, chamfer in depth, palette of the band that starts here
        (6.55, H + 0.08, D + 0.03, CU + 0.08, CV, "collar"), (7.55, H + 0.08, D + 0.03, CU + 0.08, CV, "collar"),
        (7.55, H, D, CU, CV, "housing"), (12.0, H, D, CU, CV, "housing"),
        (12.0, H + 0.08, D + 0.03, CU + 0.08, CV, "collar"), (12.85, H + 0.08, D + 0.03, CU + 0.08, CV, "collar"),
        (12.85, BX, E, BX - 0.25, CV, "blade"), (18.7, BX, E, BX - 0.25, CV, "blade"),
        (19.3, 0.8, E - 0.6, 0.68, CV * 0.7, "tip"), (19.78, 0.3, E - 1.15, 0.25, CV * 0.5, None)]
    zs = D - CV  # half height of the legs' flat side faces
    for side in (1, -1):
        mx = lambda x: x if side > 0 else 2 * AX - x
        cx = mx(5.5)
        rings = [ch_ring((cx, y, 0.0), (1, 0, 0), Z, hx, hz, cu, cv) for y, hx, hz, cu, cv, _ in secs]
        pals = [PAL["tip"] if s[5] in (None, "tip") else PAL[s[5]] for s in secs[:-1]]
        B.loft(rings, pals, cap_pals=(PAL["collar"], PAL["tip"]))
        # outer side plate on the housing (raised armour panel)
        ox = cx - side * H
        B.box((min(ox, ox - side * 0.08), 8.05, -(zs - 0.15)), (max(ox, ox - side * 0.08), 11.55, zs - 0.15), PAL["plate"])
        # inner side: three vent slots (dark inserts)
        ix = cx + side * H
        for z in (-0.62 * (zs - 0.4), 0.0, 0.62 * (zs - 0.4)):
            B.box((min(ix, ix + side * 0.05), 8.2, z - 0.28), (max(ix, ix + side * 0.05), 9.6, z + 0.28), PAL["slot"])

        def slope(sx, sz, t, y, hu, hv, cu, off=0.035):
            """A point on the leg's sloped face (sx: +1 inner / -1 outer in sprite x, sz: face),
            t from 0 at the ridge to 1 at the side face, lifted `off` off the surface."""
            ln = math.hypot(cu, cv)
            nx, nz = CV / ln, cu / ln
            x = hu - cu + cu * t + nx * off
            z = hv - CV * t + nz * off
            return (cx + side * sx * x, y, sz * z)

        def panel(sx, sz, t0, t1, y0, y1, pal, part):
            hu, hv, cu = (H, D, CU) if part == "housing" else (BX, E, BX - 0.25)
            q = [slope(sx, sz, t0, y0, hu, hv, cu), slope(sx, sz, t1, y0, hu, hv, cu),
                 slope(sx, sz, t1, y1, hu, hv, cu), slope(sx, sz, t0, y1, hu, hv, cu)]
            ln = math.hypot(cu, CV)
            B.decal(q, pal, (side * sx * CV / ln, 0, sz * cu / ln))

        cv = CV
        for sz in (1, -1):
            for sx in (1, -1):
                panel(sx, sz, 0.08, 0.92, 9.95, 10.08, PAL["groove"], "housing")     # cross seams
                panel(sx, sz, 0.08, 0.92, 15.6, 15.72, PAL["groove"], "blade")
            for y in (8.15, 8.6, 9.05):                                            # louvres, outer slope
                panel(-1, sz, 0.25, 0.75, y, y + 0.2, PAL["slot"], "housing")
            for y in (13.4, 17.7):                                                 # bolts, inner slope
                hu, hv, cu = BX, E, BX - 0.25
                c = slope(1, sz, 0.55, y, hu, hv, cu, 0.0)
                ln = math.hypot(cu, CV)
                nrm = (side * CV / ln, 0.0, sz * cu / ln)
                tan = (sz * cu / ln, 0.0, -side * CV / ln)
                B.loft([ell_ring(add(c, nrm, -0.05), tan, (0, 1, 0), 0.17, 0.17, 6),
                        ell_ring(add(c, nrm, 0.09), tan, (0, 1, 0), 0.14, 0.14, 6),
                        [add(c, nrm, 0.12)]], PAL["bolt"], cap1=False)
        # --- STRUT: chamfered beam from the housing to the pod, clamp block, bearing collar
        xs = [mx(x) for x in (6.7, 6.95, 7.7, 8.5)]
        sr = [ch_ring((x, 10.5, 0.0), (0, 1, 0), Z, 1.5 if i < 1 else 1.42, 1.6 if i < 1 else 1.35, 0.35)
              for i, x in enumerate(xs)]
        B.loft(sr, PAL["strut"])
        lo, hi = mx(6.75), mx(7.35)
        B.box((min(lo, hi), 9.05, -2.2), (max(lo, hi), 11.95, 2.2), PAL["clamp"])
        for sz in (1, -1):  # clamp bolts
            c = mx(7.05)
            for y in (9.6, 11.4):
                z0 = sz * 2.2
                B.loft([ell_ring((c, y, z0 - sz * 0.05), (1, 0, 0), (0, 1, 0), 0.15, 0.15, 6),
                        ell_ring((c, y, z0 + sz * 0.08), (1, 0, 0), (0, 1, 0), 0.12, 0.12, 6),
                        [(c, y, z0 + sz * 0.1)]], PAL["bolt"], cap1=False)
        br = [ell_ring((mx(x), 10.5, 0.0), (0, 1, 0), Z, 1.4 if i % 3 else 1.2, 1.55 if i % 3 else 1.3, 12)
              for i, x in enumerate((7.75, 7.9, 8.35, 8.6))]
        B.loft(br, PAL["bearing"])

    # --- POD: flattened bronze barrel lying along Y; a hub at the rear, a deep dark port in the nose
    pf = T["podFlat"]
    pod = [(5.95, 0.85, "pod_cap"), (6.1, 0.85, "pod_cap"), (6.1, 1.65, "pod_cap"), (6.35, 2.35, "pod_cap"),
           (6.65, 2.8, "pod"), (7.05, 3.3, "pod"), (7.55, 3.52, "pod"), (11.55, 3.52, "pod_seam"),
           (11.75, 3.32, "pod_seam"), (11.95, 3.44, "pod_low"), (12.6, 3.3, "pod_low"), (13.25, 2.75, "pod_low"),
           (13.95, 2.0, "pod_cap"), (14.3, 1.7, "pod_cap"), (14.78, 1.18, "pod_cap"), (14.78, 0.78, "port"),
           (14.25, 0.7, None)]
    rings = [[(AX, 5.9, 0.0)]] + [ell_ring((AX, y, 0.0), (1, 0, 0), Z, w, w * pf, 20) for y, w, _ in pod] + \
        [[(AX, 14.25, 0.0)]]
    pals = [PAL["pod_cap"]] + [PAL[r] if r else PAL["port"] for _, _, r in pod]
    pals[-2] = PAL["port"]
    B.loft(rings, pals)

    def pod_hw(y):
        body = [s for s in pod[2:14]]
        for (y0, w0, _), (y1, w1, _) in zip(body, body[1:]):
            if y0 <= y <= y1:
                return w0 + (w1 - w0) * (y - y0) / max(1e-9, y1 - y0)
        return 0.0

    def surf(x, y, sz, e=0.035):
        w = pod_hw(y)
        h = w * pf
        d = (x - AX) / w if w else 0
        return (x, y, sz * (h * math.sqrt(max(0.0, 1 - d * d)) + e))

    def strip(pts, half, pal, sz):
        for a, b in zip(pts, pts[1:]):
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty)
            nx, ny = -ty / ln * half, tx / ln * half
            q = [surf(a[0] - nx, a[1] - ny, sz), surf(b[0] - nx, b[1] - ny, sz),
                 surf(b[0] + nx, b[1] + ny, sz), surf(a[0] + nx, a[1] + ny, sz)]
            B.decal(q, pal, (0, 0, sz))

    def seg(a, b, n):
        return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]

    for sz in (1, -1):
        strip(seg((AX - 1.0, 7.5), (AX - 1.0, 11.5), 6), 0.07, PAL["pod_seam"], sz)
        strip(seg((AX + 1.0, 7.5), (AX + 1.0, 11.5), 6), 0.07, PAL["pod_seam"], sz)
        strip(seg((AX - 2.6, 12.6), (AX - 1.2, 13.4), 3), 0.06, PAL["pod_seam"], sz)
        strip(seg((AX - 1.2, 13.4), (AX + 1.2, 13.4), 3), 0.06, PAL["pod_seam"], sz)
        strip(seg((AX + 1.2, 13.4), (AX + 2.6, 12.6), 3), 0.06, PAL["pod_seam"], sz)
        strip(seg((AX - 3.0, 7.15), (AX + 3.0, 7.15), 12), 0.05, PAL["pod_seam"], sz)
        # hatch near the rear of the pod (four dark louvres) and two oval slots on the lower panels
        for i in range(4):
            x0 = AX - 0.7 + i * 0.35
            B.decal([surf(x0 + 0.03, 7.55, sz, 0.045), surf(x0 + 0.32, 7.55, sz, 0.045),
                     surf(x0 + 0.32, 8.3, sz, 0.045), surf(x0 + 0.03, 8.3, sz, 0.045)], PAL["hatch"], (0, 0, sz))
        for sx in (-1, 1):
            c = AX + sx * 1.95
            B.decal([surf(c + 0.32 * math.cos(2 * math.pi * k / 10), 13.0 + 0.45 * math.sin(2 * math.pi * k / 10), sz, 0.045)
                     for k in range(10)], PAL["slot"], (0, 0, sz))



def turn_matrix(angle):
    """Turn about the spin axis (column edge 11.5) by `angle` about Y."""
    t = (AX - 12) * PX
    return Matrix.Translation((t, 0, 0)) @ Matrix.Rotation(angle, 4, "Y") @ Matrix.Translation((-t, 0, 0))


def build_base(sprite, coll):
    """Frame 191's model (unturned), the spin axis on column edge 11.5."""
    B = Builder(sprite)
    build_geometry(B)
    bm = B.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(((AX - 12) * PX, 0, 0)), verts=bm.verts)
    for f in bm.faces:
        f.smooth = True
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for mt in B.mats:
        mesh.materials.append(mt)
    mesh.set_sharp_from_angle(angle=math.radians(33))
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    return obj


# --- bake (no concept projection: occlusion and roughness only, D50) ----------------------

def bake_maps(obj, out_dir, tag, size=1024, samples=64, skip=()):
    """UV the model and bake a grey colour multiplier (two-scale ambient occlusion plus an edge
    lift) and a metallic-roughness map (G roughness, B metallic) with Cycles, then wire them into
    the palette materials (Base Color = map x palette colour) except those named in `skip`."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(dict.fromkeys(me.materials))
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.2
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.45, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for m in [q for q in mats if q.name not in skip]:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def frames_subset(sprite, indices):
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in indices]
        if keep:
            out.append({**s, "frames": keep})
    return out


def build(sprite, bake=True):
    """[(model_name, [model, outline shell], sprites)] for the eight spin frames."""
    frames = sprite["sprites"][0]["frames"]
    coll = common.reset_collection(NAME)
    base = build_base(sprite, coll)
    if bake:  # before the shell exists, so it can't occlude the model
        bake_dir = REPO / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(base, bake_dir, TAG, size=512, samples=64)
    base_shell = common.outline_shell(base, coll, voxel=0.012, faces=1000)
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        if k == 0:
            obj, shell = base, base_shell
        else:
            fc = common.reset_collection(name)
            m = turn_matrix(math.radians(ANGLES[k]))
            obj = base.copy()
            obj.data = base.data.copy()
            obj.data.transform(m)
            obj.name = obj.data.name = name
            fc.objects.link(obj)
            shell = base_shell.copy()
            shell.data = base_shell.data.copy()
            shell.data.transform(m)
            shell.name = shell.data.name = f"{name}_outline"
            fc.objects.link(shell)
        shell.parent = obj
        models.append((name, [obj, shell], frames_subset(sprite, [frame])))
    return models


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(REPO, NAME)
    bake = "--no-bake" not in argv
    models = build(sprite, bake=bake)
    print(f"{NAME}: {tri_count(models[0][1][0])} triangles, outline shell {tri_count(models[0][1][1])}")
    for model, objects, sprites in models:
        common.export_sprite_model(REPO, objects, f"enemies/{model}", sprites,
                                   image_format="WEBP" if bake else "AUTO")
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        by_index = {f["index"]: f for f in sprite["frames"]}
        for i, (model, objects, sprites) in enumerate(models):
            frame = by_index[sprites[0]["frames"][0]]
            ref = REPO / "reference" / "models" / NAME / frame["image"]
            path = out if i == 0 else out.with_name(f"{out.stem}{model[len(NAME):]}.png")
            common.render_preview(objects[:1], str(path), ref, size=frame["size"])


if __name__ == "__main__":
    main()
