"""newshs-269, the red dome pod (newshs.shp frame 269, 24x28; an air unit of 6 levels): a hard-surface
machine that is its sprite in 3D (the standard of the player ships and level-1 enemies, D50-D53, D65).

Reading of the sprite (the user's rules: plan, features and colours from the sprite):
- An egg-shaped grey collar (columns 1-23, rows 0-26; mirror line at column edge 12.5), a rounded
  ridge whose crest runs ~1.5 px in from the edge (the bright line at column 2) with its inner slope
  falling to a dark well round the dome. Panel seams split it in four plates: the notch at the top
  (row 0, columns 11-12) and the ink nicks at the sides (row 10, columns 1 and 23).
- A big red glass dome (centre column edge 12.5, row edge 10.5, radius 8.5), glossy: the orange and
  yellow patch top left is the light's sheen on the glass, not a part.
- A grey gun drum (a ball split down the middle) set into the dome's front, rows 9-15, columns
  8-16: two rounded halves on a horizontal axis with a slot between them (column 12) holding the
  barrel, which points to the front (down the screen, the way the pod flies).
- At the front (rows 20-26, columns 8-16) a recessed channel (a gun chute) between two rails,
  a low spine in it; the dark columns 8 and 15 are the seams between the rails and the collar.
- Colours, trimmed medians per region: collar 5 (its lower half reads 4: shadow), drum 6, slot
  and barrel 4, dome 115, rails 4, channel 2, seams 1-3 (core 3).
- Top view: the D74 inner edge (tools/sprite_mask.py), the sprite has ink only along its bottom
  row and the bottom-left; the plan is a smooth egg (pchip half widths per row).

Local build frame (sprite px): x = column edge - 12.5, y = row edge (front = +y), z up.
Blender: X = (x + 0.5) / 12, Y = (14 - y) / 12, Z = z / 12.

Exports public/models/enemies/newshs-269.glb (the model, AO/roughness maps baked by the script,
D50; no concept projection) with its outline shell (D51), and src/render/spriteModels/newshs-269.json.

Run: blender --background --factory-startup --python assets/blender/enemies/newshs-269.py --
     [--no-bake] [--measure m.json] [--renders dir] [--top top.png] [--preview out.png]
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "newshs-269"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

# --- materials ----------------------------------------------------------------------------------
COLLAR, CORE, CHAN, BELLY, DOME, DRUM, HUB, BORE, RAIL, SPINE, BAND = range(11)
PAL_OF = {COLLAR: 4, CORE: 3, CHAN: 2, BELLY: 4, DOME: 115, DRUM: 6, HUB: 4, BORE: 1, RAIL: 4, SPINE: 3, BAND: 4}
TEXTURED = (COLLAR, CORE, CHAN, BELLY, DRUM, HUB, RAIL, SPINE, BAND)
TINT = (0.98, 0.99, 1.0)


def materials(sprite):
    def pal(slot, tag, metallic, roughness, emit=0.0):
        return common.palette_material(sprite, PAL_OF[slot], f"{NAME}_{tag}", metallic=metallic,
                                       roughness=roughness, emission_strength=emit)
    return [
        pal(COLLAR, "collar", 0.35, 0.4),
        pal(CORE, "core", 0.2, 0.6),
        pal(CHAN, "channel", 0.15, 0.65),
        pal(BELLY, "belly", 0.25, 0.55),
        pal(DOME, "dome", 0.0, 0.38),  # satin, no glow: the sprite dome is a deep crimson with one soft sheen
        pal(DRUM, "drum", 0.4, 0.32),
        pal(HUB, "hub", 0.35, 0.42),
        pal(BORE, "bore", 0.0, 0.9),
        pal(RAIL, "rail", 0.35, 0.4),
        pal(SPINE, "spine", 0.3, 0.45),
        pal(BAND, "band", 0.4, 0.36),
    ]


# --- plan ---------------------------------------------------------------------------------------
# Half width of the egg by row (row centre), inside each row's pixel margins (k, k + 1) of the
# sprite's inner mask, as a smooth curve (no flats where the sprite is round).
_PY = [0.0, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 16.5, 17.5, 18.5, 19.5, 20.5,
       21.5, 22.5, 23.5, 24.5, 25.5, 26.0]
_PW = [2.7, 3.6, 5.6, 7.25, 8.45, 9.3, 9.9, 10.45, 10.85, 11.2, 11.42, 11.5, 11.5, 11.35, 11.15,
       10.72, 10.25, 9.65, 9.15, 8.45, 7.45, 5.75, 4.5]
PLAN = pchip(_PY, _PW)
Y0, Y1 = 0.0, 26.0
DC = (0.0, 10.5)     # centre of the collar's plates and seams (the side nicks are on row 10)
R_DOME = 8.5         # dome base half width (columns 4-20)
DOME_E = ((0.0, 11.0), 8.5, 9.0)  # dome base ellipse: rows 2-19 (18 rows) by columns 4-20 (17)
LIP_E = ((0.0, 10.75), 9.05, 9.3)  # collar's inner lip (dark well between it and the dome)
RW = 9.05
XC = -0.5            # the chin's centre line: its pattern is mirrored about column edge 12, not 12.5
Z0 = 0.95            # well floor / dome base
H_DOME = 4.3
CHIN_X = 3.75        # lower plates end here, from XC (the seam slot outside each rail)
SEAM_G = {0.0: 0.8, 180.0: 0.8, 270.0: 1.0}  # seams (degrees) and their gap widths
CH = 0.25            # plate end chamfer


def boundary():
    ys = [Y0 + (Y1 - Y0) * i / 104 for i in range(105)]
    right = [(PLAN(y), y) for y in ys]
    left = [(-x, y) for x, y in reversed(right)]
    return right + left


BOUND = boundary()


def ray_bound(o, d):
    """Distance along d from o to the plan boundary (first hit, t > 0)."""
    best = None
    n = len(BOUND)
    for i in range(n):
        (ax, ay), (bx, by) = BOUND[i], BOUND[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        t = ((ax - o[0]) * ey - (ay - o[1]) * ex) / den
        s = ((ax - o[0]) * d[1] - (ay - o[1]) * d[0]) / den
        if t > 1e-6 and -1e-9 <= s <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return best


def ro(theta):
    th = math.radians(theta)
    return ray_bound(DC, (math.cos(th), math.sin(th)))


def ellipse_t(o, d, e):
    """t where o + t d leaves the ellipse e = ((cx, cy), a, b) going outward."""
    (cx, cy), a, b = e
    fx, fy = (o[0] - cx) / a, (o[1] - cy) / b
    dx, dy = d[0] / a, d[1] / b
    A = dx * dx + dy * dy
    B = fx * dx + fy * dy
    C = fx * fx + fy * fy - 1.0
    return (-B + math.sqrt(max(B * B - A * C, 0.0))) / A


def lip_t(o, d):
    """t where o + t d meets the collar's inner lip going outward."""
    return ellipse_t(o, d, LIP_E)


# --- mesh helpers (one bmesh; closed solids; normals recalculated at the end) --------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat):
        vs = list(dict.fromkeys(vs))
        if len(vs) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def loft(self, rings, mats, closed=False, caps=True, cap_mat=None):
        """rings: lists of 3D points (same count, each a closed loop). mats(i_ring, j_seg) -> mat."""
        R = [[self.v(p) for p in ring] for ring in rings]
        k = len(R[0])
        rng = range(len(R)) if closed else range(len(R) - 1)
        for i in rng:
            a, b = R[i], R[(i + 1) % len(R)]
            for j in range(k):
                jj = (j + 1) % k
                self.f((a[j], a[jj], b[jj], b[j]), mats(i, j))
        if caps and not closed:
            cm = cap_mat if cap_mat is not None else mats(0, 0)
            self.f(R[0], cm)
            self.f(list(reversed(R[-1])), cm)
        return R

    def lathe(self, origin, axis, profile, sides, mats, phase=0.5):
        """Closed solid of revolution; profile [(t, r)], r = 0 at the ends allowed (poles)."""
        o, a = Vector(origin), Vector(axis).normalized()
        u = a.cross(Vector((0, 0, 1)))
        if u.length < 1e-3:
            u = a.cross(Vector((1, 0, 0)))
        u.normalize()
        w = a.cross(u)
        rings = []
        for t, r in profile:
            c = o + a * t
            if r < 1e-6:
                rings.append([self.v(c)])
            else:
                rings.append([self.v(c + r * (math.cos(2 * math.pi * (k + phase) / sides) * u
                                              + math.sin(2 * math.pi * (k + phase) / sides) * w))
                              for k in range(sides)])
        for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
            m = mats[min(i, len(mats) - 1)]
            for k in range(sides):
                kk = (k + 1) % sides
                self.f([r0[k % len(r0)], r0[kk % len(r0)], r1[kk % len(r1)], r1[k % len(r1)]], m)
        if len(rings[0]) > 1:
            self.f(rings[0], mats[0])
        if len(rings[-1]) > 1:
            self.f(list(reversed(rings[-1])), mats[-1])

    def hull(self, points, mat):
        bm = self.bm
        verts = [bm.verts.new(p) for p in points]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        live = [v for v in verts if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        live = [v for v in verts if v.is_valid]
        for f in {f for v in live for f in v.link_faces}:
            f.material_index = mat


def offset_poly(pts, off):
    """Offset a closed 2D polygon outward by `off` (negative: inward), miter joins."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    segn = []
    for i in range(n):
        (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % n]
        dx, dz = x1 - x0, z1 - z0
        ln = math.hypot(dx, dz) or 1e-9
        segn.append((sgn * dz / ln, -sgn * dx / ln))
    out = []
    for i in range(n):
        ax, az = segn[i - 1]
        bx, bz = segn[i]
        sx, sz = ax + bx, az + bz
        ln = math.hypot(sx, sz) or 1e-9
        ux, uz = sx / ln, sz / ln
        c = max(0.4, ux * bx + uz * bz)
        out.append((pts[i][0] + ux * off / c, pts[i][1] + uz * off / c))
    return out


# --- collar plates ------------------------------------------------------------------------------

def crest_us(L):
    uc = max(0.55, L - 1.6)
    u4 = max(uc + 0.1, L - 1.0)
    return uc, u4


def plate_profile(L):
    """Closed (u, z) section of a collar plate, u from the inner lip outward, L to the plan edge.
    The crest and the shoulder are rounded (the sprite's sheen line along the collar's crest)."""
    uc, u4 = crest_us(L)
    us = max(L - 0.62, u4 + 0.05)
    return [
        (0.0, Z0), (0.0, 1.22), (0.32, 1.62),           # inner wall, chamfer
        (uc, 2.24), ((uc + u4) / 2, 2.37), (u4, 2.35),  # inner slope up to the rounded crest
        (us, 2.24), (L - 0.4, 2.04), (L - 0.17, 1.74), (L, 1.4),  # rounded shoulder to the band
        (L, 1.02), (L - 0.2, 0.9), (L, 0.78),          # a panel line round the band
        (L, 0.36), (L - 0.35, -0.04), (L - 1.0, -0.36),  # lower chamfer
        (max(0.2, L - 2.0), 0.55),                     # buried underside
    ]


BAND_SEGS = (9, 10, 11, 12)  # the outer band's faces (profile segments) take BAND


def station(o, d, shrink):
    """A plate section along the ray o + t d from the lip out; shrink insets it (plate-end chamfer,
    CH, or a panel line's floor, a number)."""
    t0 = lip_t(o, d)
    pi = (o[0] + d[0] * t0, o[1] + d[1] * t0)
    t1 = ray_bound(pi, d)
    prof = plate_profile(t1)
    if shrink:
        prof = offset_poly(prof, -(CH if shrink is True else shrink))
    return [(pi[0] + d[0] * u, pi[1] + d[1] * u, z) for u, z in prof]


def seam_line(theta, side, extra=0.0):
    """End line of a plate next to the seam at `theta`: parallel to the seam's radius, offset to the
    plate's side (+1 toward increasing theta) by half the gap (+ extra)."""
    th = math.radians(theta)
    d = (math.cos(th), math.sin(th))
    p = (-math.sin(th), math.cos(th))
    off = SEAM_G[theta % 360.0] / 2 + extra
    return ((DC[0] + p[0] * off * side, DC[1] + p[1] * off * side), d)


def chin_line(sign, extra=0.0):
    return ((XC + sign * (CHIN_X + extra), DC[1]), (0.0, 1.0))


def radial(theta):
    th = math.radians(theta)
    return (DC, (math.cos(th), math.sin(th)))


def blend(l0, l1, s):
    (o0, d0), (o1, d1) = l0, l1
    o = (o0[0] + (o1[0] - o0[0]) * s, o0[1] + (o1[1] - o0[1]) * s)
    d = (d0[0] + (d1[0] - d0[0]) * s, d0[1] + (d1[1] - d0[1]) * s)
    ln = math.hypot(*d)
    return (o, (d[0] / ln, d[1] / ln))


PANEL = 0.13   # panel line depth (the section's inset at its floor)


def plate(M, lines):
    """lines: (o, d) or (o, d, inset) stations; the end ones get the end chamfer."""
    rings = []
    for i, ln in enumerate(lines):
        shrink = True if i in (0, len(lines) - 1) else (ln[2] if len(ln) > 2 else False)
        rings.append(station(ln[0], ln[1], shrink))
    # Plates run with increasing theta; keep ring orientation consistent (normals fixed later).
    M.loft(rings, lambda i, j: BAND if j in BAND_SEGS else COLLAR, cap_mat=COLLAR)


def angles(a, b, step=4.5):
    n = max(1, int(math.ceil((b - a) / step)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def radials(a, b, panel=None, w=0.9):
    """Radial stations from a to b (degrees), with a modelled panel line (a V groove PANEL deep,
    2w degrees wide) across the plate at `panel`."""
    ts = angles(a, b)
    if panel is None:
        return [radial(t) for t in ts]
    ts = [t for t in ts if abs(t - panel) > w + 1.2]
    out = []
    for t in sorted(ts + [panel - w, panel, panel + w]):
        o, d = radial(t)
        out.append((o, d, PANEL) if t == panel else (o, d))
    return out


def build_collar(M):
    dmin = 6.0
    # Upper left (180 -> 270) and upper right (270 -> 360).
    for a, b in ((180.0, 270.0), (270.0, 360.0)):
        lines = [seam_line(a, +1), seam_line(a, +1, CH)]
        lines += radials(a + dmin, b - dmin, panel=(a + b) / 2)
        lines += [seam_line(b, -1, CH), seam_line(b, -1)]
        plate(M, lines)
    # Lower right (0 -> chin) and lower left (chin -> 180).
    th_end = 61.0
    rr = radials(dmin, th_end, panel=33.0)
    cl = chin_line(+1, CH)
    tail = [blend(rr[-1], cl, s) for s in (0.25, 0.5, 0.75)]
    plate(M, [seam_line(0.0, +1), seam_line(0.0, +1, CH)] + rr + tail + [cl, chin_line(+1)])
    rl = radials(180.0 - th_end, 180.0 - dmin, panel=147.0)
    cl = chin_line(-1, CH)
    head = [blend(cl, rl[0], s) for s in (0.25, 0.5, 0.75)]
    plate(M, [chin_line(-1), cl] + head + rl + [seam_line(180.0, -1, CH), seam_line(180.0, -1)])


# --- core (dark body under the plates, well floor, channel floor, belly) -------------------------

def ang_dist(a, b):
    d = (a - b) % 360.0
    return min(d, 360.0 - d)


def core_inset(theta):
    ins = 0.35
    for s in SEAM_G:
        x = ang_dist(theta, s) / 4.5
        if x < 1:
            ins = max(ins, 0.35 + 0.5 * (1 - x * x))
    return ins


CHIN_LO, CHIN_HI = 65.0, 122.0  # the chin's angular range from DC: both seam slots, end to end


def chin_amount(theta):
    """1 inside the chin's angular range (the rails and their seam slots), 0 outside; the core
    is low there (the channel floor), under the plates' ends too."""
    lo, hi = CHIN_LO, CHIN_HI
    if lo <= theta <= hi:
        return 1.0
    x = min(abs(theta - lo), abs(theta - hi)) / 3.0
    return max(0.0, 1.0 - x)


def build_core(M, n=96):
    thetas = [360.0 * k / n for k in range(n)]
    loops = []
    for th in thetas:
        R = ro(th)
        ins = core_inset(th)
        ch = chin_amount(th)
        zt = 1.55 * (1 - ch) + 0.5 * ch
        re = R - ins
        rl = lip_t(DC, (math.cos(math.radians(th)), math.sin(math.radians(th))))
        prof = [(rl - 1.2, Z0), (rl + 0.15, Z0), (rl + 0.5, zt), (re - 0.3, zt + 0.02), (re, zt - 0.28),
                (re, min(0.2, zt - 0.4)), (re - 0.9, -0.75), (R * 0.72, -1.75), (R * 0.45, -2.45), (R * 0.2, -2.85)]
        fixed = []
        last = -1
        for jj, (r, z) in enumerate(prof):
            if jj <= 5:
                r = max(r, last + 0.04)
            else:
                r = min(r, last - 0.04)
            fixed.append((r, z))
            last = r
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        loops.append([(DC[0] + c * r, DC[1] + s * r, z) for r, z in fixed])
    # Rings around the axis, one per profile index, plus poles.
    top = M.v((DC[0], DC[1], Z0))
    bot = M.v((DC[0], DC[1], -2.95))
    k = len(loops[0])
    V = [[M.v(loops[i][j]) for i in range(n)] for j in range(k)]

    def mat(j, i):
        ch = chin_amount(thetas[i])
        if j >= 5:
            return BELLY
        if 1 <= j <= 4 and ch > 0.5:
            return CHAN
        return CORE
    for i in range(n):
        ii = (i + 1) % n
        M.f((top, V[0][i], V[0][ii]), CORE)
        for j in range(k - 1):
            M.f((V[j][i], V[j + 1][i], V[j + 1][ii], V[j][ii]), mat(j, i))
        M.f((V[-1][i], bot, V[-1][ii]), BELLY)


# --- dome, gun drum, chin ---------------------------------------------------------------------

def cap_z(rho, base=Z0, h=H_DOME, rad=R_DOME):
    """Height of a spherical cap (base half width rad, height h) at normalised radius rho."""
    rs = (rad ** 2 + h ** 2) / (2 * h)
    zc = base + h - rs
    return zc + math.sqrt(max(rs * rs - (rad * min(rho, 1.0)) ** 2, 0.0))


def build_dome(M, sides=56, rings=11):
    """The glass dome: a spherical cap stretched to the sprite's base ellipse (DOME_E), so it
    runs from row 2 down to row 19, where its lip meets the top of the chin."""
    (cx, cy), a, b = DOME_E
    rs = (R_DOME ** 2 + H_DOME ** 2) / (2 * H_DOME)
    a0 = math.asin(R_DOME / rs)
    prof = [(Z0 - 0.15, 1.0 - 0.05 / R_DOME), (Z0, 1.0)]
    for i in range(1, rings):
        rho = rs * math.sin(a0 * (1 - i / rings)) / R_DOME
        prof.append((cap_z(rho), rho))
    rings_v = []
    for z, rho in prof:
        rings_v.append([M.v((cx + a * rho * math.cos(2 * math.pi * (k + 0.5) / sides),
                             cy + b * rho * math.sin(2 * math.pi * (k + 0.5) / sides), z))
                        for k in range(sides)])
    top = M.v((cx, cy, Z0 + H_DOME))
    for r0, r1 in zip(rings_v, rings_v[1:]):
        for k in range(sides):
            kk = (k + 1) % sides
            M.f((r0[k], r0[kk], r1[kk], r1[k]), DOME)
    for k in range(sides):
        M.f((rings_v[-1][k], rings_v[-1][(k + 1) % sides], top), DOME)
    M.f(list(reversed(rings_v[0])), DOME)


def dome_y(x):
    """Front edge (largest y) of the dome's base at x."""
    (cx, cy), a, b = DOME_E
    return cy + b * math.sqrt(max(1 - ((x - cx) / a) ** 2, 0.0))


def lip_y(x):
    (cx, cy), a, b = LIP_E
    return cy + b * math.sqrt(max(1 - ((x - cx) / a) ** 2, 0.0))


DRUM_Y, DRUM_Z, DRUM_R = 12.5, 4.25, 3.4


def build_drum(M):
    prof = [(0.5, 0.0), (0.5, 2.95), (0.72, DRUM_R), (1.6, DRUM_R),
            (2.45, 3.18), (3.2, 2.7), (3.8, 2.0), (4.2, 1.25), (4.42, 0.55), (4.5, 0.0)]
    for sx in (1, -1):
        M.lathe((0.0, DRUM_Y, DRUM_Z), (sx, 0, 0), prof, 28, [DRUM])
    # The hub between the halves (the slot's floor) and the barrel lying in the slot.
    M.lathe((-0.55, DRUM_Y, DRUM_Z), (1, 0, 0), [(0, 0), (0, 2.35), (1.1, 2.35), (1.1, 0)], 20, [HUB])
    by, bz = DRUM_Y - 1.0, DRUM_Z + 1.2
    tip = 16.35
    M.lathe((0.0, by, bz), (0, 1, -0.12), [(0, 0), (0, 0.42), (tip - by - 0.5, 0.42), (tip - by - 0.45, 0.5),
                                         (tip - by, 0.5), (tip - by, 0.28), (tip - by - 0.15, 0.28),
                                         (tip - by - 0.15, 0.0)], 12, [HUB, HUB, HUB, HUB, HUB, BORE, BORE])


def slab_pts(x0, x1, y0, y1, zt0, zt1, zb, ch):
    """Chamfered block, top sloping from zt0 (at y0) to zt1 (at y1)."""
    pts = []
    for y, zt, sy in ((y0, zt0, 1), (y1, zt1, -1)):
        for x, sx in ((x0, 1), (x1, -1)):
            pts += [(x + sx * ch, y, zt), (x, y, zt - ch), (x, y + sy * ch, zt - ch * 0.5),
                    (x + sx * ch, y + sy * ch, zt),
                    (x, y, zb), (x + sx * ch * 0.5, y + sy * ch * 0.5, zb - ch * 0.5)]
    return pts


def build_chin(M):
    """The chin, mirrored about XC (column edge 12) as the sprite draws it: seam slot (column 8) /
    rail (9) / channel (10) / raised centre block (11-12) / channel (13) / rail (14) / seam slot
    (15). The slots are real cuts between the plates' ends and the rails, floored in pal 1; the
    channels' floor is the core (pal 2), and the dome's lip comes down to row 19 above them."""
    yb = Y1 - 0.12
    for s in (1, -1):
        x0, x1 = sorted((XC + s * 2.0, XC + s * 3.2))
        y0 = max(dome_y(x0), dome_y(x1)) + 0.08
        M.hull(slab_pts(x0, x1, y0, yb, 1.5, 1.05, 0.2, 0.22), RAIL)
        # The seam slot's floor (dark, deep: 1-1.7 px below the plate and the rail on each side).
        q0, q1 = sorted((XC + s * 3.2, XC + s * CHIN_X))
        ys = min(lip_y(q0), lip_y(q1)) - 0.25
        M.hull(slab_pts(q0 - 0.02, q1 + 0.02, ys, yb, 0.62, 0.62, 0.2, 0.04), BORE)
    M.hull(slab_pts(XC - 1.0, XC + 1.0, 21.0, yb - 0.2, 1.24, 0.98, 0.3, 0.2), SPINE)


def build(coll, sprite):
    mats = materials(sprite)
    M = Mesh()
    build_core(M)
    build_collar(M)
    build_dome(M)
    build_drum(M)
    build_chin(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj


# --- outline shell (D51) ------------------------------------------------------------------------

def outline_shell(coll, n=72):
    """The ink outline's shell, built directly instead of voxel-remeshing the model (that one, a
    smoothed fill of the dome/collar well and the rail ends, rippled and drew black specks there
    in game). A closed loft round DC: a low cap under the dome (base slope ~50 deg), the well floor,
    the collar's section inset ~0.1 px (inner slope, crest, shoulder, band) and the belly. Its
    whole top faces the game camera (no slope past ~55 deg), so the outline pass, which draws only
    the shell's back faces, draws just the outer contour. Same material and extra as
    common.outline_shell (src/render/modelPrep.ts)."""
    (cx, cy), a, b = DOME_E
    sa, sb, sh, sz = a - 0.2, b - 0.2, 3.9, Z0 - 0.1
    loops = []
    for i in range(n):
        th = 360.0 * i / n
        d = (math.cos(math.radians(th)), math.sin(math.radians(th)))
        tD = ellipse_t(DC, d, ((cx, cy), sa, sb))
        tL = lip_t(DC, d)
        tB = ro(th)
        L = tB - tL
        uc, u4 = crest_us(L)
        prof = []
        for f in (0.2, 0.4, 0.6, 0.75, 0.88, 1.0):
            t = f * tD
            px, py = DC[0] + d[0] * t, DC[1] + d[1] * t
            rho = math.hypot((px - cx) / sa, (py - cy) / sb)
            prof.append((t, cap_z(rho, base=sz, h=sh, rad=sa)))
        # The crest comes down where the model does (D90, held inside): into the chin, to its channel
        # floor (0.5; rails top 1.05-1.5, spine 0.98), and over the plates' seams (their gap floor, the
        # core, at 1.55), so no part of the shell stands above the model there and its back faces
        # draw no ink sheet behind the chin or wedges in the seams.
        crest = chin_amount(th)
        low = 0.45 * crest + 9.0 * (1 - crest)
        for sd in SEAM_G:
            if ang_dist(th, sd) < 4.0:
                low = min(low, 1.45)
        cz = lambda z: min(z, low)  # noqa: E731
        prof += [(max(tD + 0.12, tL - 0.35), sz),
                 (tL + uc, cz(2.16)), (tL + (uc + u4) / 2, cz(2.26)), (tL + u4, cz(2.24)),
                 (tB - 0.45, cz(1.94)), (tB - 0.1, cz(1.36)), (tB - 0.1, 0.4), (tB - 0.42, 0.02),
                 (tB - 1.05, -0.28), (tB - 1.3, -0.62), (0.72 * tB, -1.62), (0.45 * tB, -2.32),
                 (0.2 * tB, -2.72)]
        loops.append([(DC[0] + d[0] * t, DC[1] + d[1] * t, z) for t, z in prof])
    bm = bmesh.new()
    rho0 = math.hypot((DC[0] - cx) / sa, (DC[1] - cy) / sb)
    top = bm.verts.new((DC[0], DC[1], cap_z(rho0, base=sz, h=sh, rad=sa)))
    bot = bm.verts.new((DC[0], DC[1], -2.8))
    k = len(loops[0])
    V = [[bm.verts.new(loops[i][j]) for i in range(n)] for j in range(k)]
    for i in range(n):
        ii = (i + 1) % n
        bm.faces.new((top, V[0][i], V[0][ii]))
        for j in range(k - 1):
            bm.faces.new((V[j][i], V[j + 1][i], V[j + 1][ii], V[j][ii]))
        bm.faces.new((V[-1][i], bot, V[-1][ii]))
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}_outline")
    bm.to_mesh(me)
    bm.free()
    shell = bpy.data.objects.new(f"{NAME}_outline", me)
    coll.objects.link(shell)
    me.shade_smooth()
    me.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def hold_inside(shell, obj, inside=0.004):
    """D90: every shell vertex outside the model goes back onto it, `inside` inside (Shrinkwrap)."""
    sw = shell.modifiers.new("inside", "SHRINKWRAP")
    sw.target = obj
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "INSIDE"
    sw.offset = -inside
    common._apply_modifiers(shell)


def bake_maps(obj, out_dir, size=1024, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", NAME)


# --- measuring ----------------------------------------------------------------------------------

def region_of(c, r, v):
    if v < 0:
        return None
    x, y = c + 0.5 - 12.5, r + 0.5
    if v >= 112:
        return "dome"
    if abs(x - XC) < 4.1 and y > 20.0:
        if c in (9, 14):
            return "rail"
        if c in (8, 15):
            return "chin_seam"
        if c in (10, 13):
            return "channel"
        if c in (11, 12):
            return "chin_block" if y > 21.0 else "channel"
        return "collar"
    if math.hypot(x, y - 10.5) < 8.6:
        return "slot" if c == 12 else "drum"
    return "collar"


def measure(obj, sprite, out):
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, deps)
    me = obj.data
    mat_pal = [int(m.name.split("_")[1]) for m in me.materials]
    grid = sprite["frames"][0]["pixels"]
    h, w = len(grid), len(grid[0])

    def hit(c, r):
        x, y = (c - w / 2) / 12, (h / 2 - r) / 12
        loc, nrm, idx, dist = tree.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)), 20.0)
        return None if loc is None else mat_pal[me.polygons[idx].material_index]
    centre = [[hit(c + 0.5, r + 0.5) for c in range(w)] for r in range(h)]
    col = {int(k): v for k, v in sprite["colors"].items()}
    lum = lambda i: sum(col.get(i, (0, 0, 0))) / 3  # noqa: E731

    def tmed(vals):
        s = sorted(vals, key=lum)
        n = len(s)
        t = n // 6 if n >= 6 else 0
        core = s[t:n - t] or s
        return core[len(core) // 2]
    regions = {}
    for r in range(h):
        for c in range(w):
            k = region_of(c, r, grid[r][c])
            if k:
                regions.setdefault(k, ([], []))
                regions[k][0].append(grid[r][c])
                if centre[r][c] is not None:
                    regions[k][1].append(centre[r][c])
    reg = {k: {"sprite": tmed(sv), "model": tmed(mv) if mv else None,
               "model_counts": {str(i): mv.count(i) for i in sorted(set(mv))}} for k, (sv, mv) in regions.items()}
    zs = [v.co.z for v in me.vertices]
    res = {"regions": reg, "model_grid": centre, "tris": sum(len(p.vertices) - 2 for p in me.polygons),
           "z_px": [min(zs) * 12, max(zs) * 12]}
    Path(out).write_text(json.dumps(res))
    print(f"tris {res['tris']} z {res['z_px']}")
    for k, v in reg.items():
        print(f"  {k:10s} sprite {v['sprite']:4d} model {v['model']}  {v['model_counts']}")
    for r in range(h):
        print("".join("." if centre[r][c] is None else ("r" if centre[r][c] >= 112 else "#") for c in range(w)))


# --- renders ------------------------------------------------------------------------------------

def setup_scene(objs):
    scene = bpy.context.scene
    for o in scene.objects:
        if o not in objs:
            o.hide_render = True
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "Standard"
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs[1].default_value = 1.0
    for name, rot, energy in (("key", (math.radians(40), math.radians(-25), math.radians(-30)), 4.0),
                              ("fill", (math.radians(60), math.radians(40), math.radians(140)), 0.9),
                              ("rim", (math.radians(110), 0, math.radians(90)), 1.0)):
        if bpy.data.objects.get(name):
            continue
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(8)
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.rotation_euler = rot
    return scene


def cam(scene, out_dir, name, loc, ortho=None, look=(0, 0, 0.2), lens=60, up="Y", res=(640, 640), transparent=False):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    co = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(co)
    co.location = loc
    co.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", up).to_euler()
    scene.camera = co
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.film_transparent = transparent
    scene.render.filepath = str(Path(out_dir) / f"{name}.png")
    bpy.ops.render.render(write_still=True)


def top_mask(objs, path, k=20):
    scene = setup_scene(objs)
    cam(scene, Path(path).parent, Path(path).stem, (0, 0, 8), ortho=28 / 12, look=(0, 0, 0),
        res=(24 * k, 28 * k), transparent=True)


def renders(objs, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(objs)
    s = 2.7
    cam(scene, out_dir, "top", (0, 0, 8), ortho=28 / 12 * 1.02, look=(0, 0, 0), res=(600, 700))
    cam(scene, out_dir, "side", (8, 0, 0.2), ortho=s)
    cam(scene, out_dir, "front", (0, -8, 0.2), ortho=s)
    cam(scene, out_dir, "rear", (0, 8, 0.2), ortho=s)
    cam(scene, out_dir, "under", (0, 0, -8), ortho=s, look=(0, 0, 0))
    d = 6.0
    cam(scene, out_dir, "q34_front", (d * 0.6, -d * 0.62, d * 0.55), lens=70)
    cam(scene, out_dir, "q34_rear", (-d * 0.62, d * 0.6, d * 0.55), lens=70)
    t = math.radians(32)
    cam(scene, out_dir, "game", (0, -d * math.sin(t), d * math.cos(t)), lens=70)
    cam(scene, out_dir, "low_front", (d * 0.35, -d * 0.9, d * 0.18), lens=70)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite)
    common._apply_modifiers(obj)
    T.cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    print(f"{NAME}: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    if "--measure" in argv:
        measure(obj, sprite, argv[argv.index("--measure") + 1])
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), size=1024, samples=64)
        fmt = "WEBP"
    # The built shell, held 0.004 inside the model (D90). A voxel shell (common.outline_shell, even
    # D90's 0.03 voxels held inside) drew ink specks round the dome's well and the drum.
    shell = outline_shell(coll)
    hold_inside(shell, obj)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    shell.hide_render = True
    if "--top" in argv:
        top_mask([obj], argv[argv.index("--top") + 1])
    if "--renders" in argv:
        renders([obj], argv[argv.index("--renders") + 1])
    if "--preview" in argv:
        common.render_preview([obj], argv[argv.index("--preview") + 1],
                              ROOT / "reference" / "models" / NAME / f"frame-{NAME}.png", size=2)


if __name__ == "__main__":
    main()
