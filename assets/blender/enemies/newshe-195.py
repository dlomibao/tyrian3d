"""newshe-195: the small red pod with two lenses (newshe.shp frame 195), hard-surface.

What the sprite shows (reference/models/newshe-195, 24x28, palette 5, one frame, a ground unit):
- Plan: a round body, cols 2-22 x rows 4-24, the ink border only on its top and left (the lit
  lower right draws colour to the edge). Inner mask fitted in polar about (x 0.55, y 14.9) sprite
  px (x = column edge - 12, y = row edge): R(theta) ~ 10.17 px with small harmonics (Fourier,
  five terms), so the plan is round where the sprite is round.
- A dark glass visor (palette 1, glints 64) over the top and back half: a rounded shield, widest
  at rows 9-12 (cols 5-19), wrapping over the back edge to the ink border (row 5 cols 9-13, row 6
  col 7) and narrowing to a point at row 18
  (col 13). Polar fit V(theta) about the same centre, seven terms.
- Two lights on the visor: a big one (white 127 core, 2x2 at cols 8-9 rows 10-11; 122-125 ring
  cols 7-10 rows 9-12; housing cols 6-11 rows 8-13) and a small dim one (121 core at col 14 row
  10, 115-117 ring cols 13-15 rows 9-11). "A saturated colour with a near-white core is a light."
- The rest is red armour (113-116); the orange crescent on the lower right (117-125) and the dark
  upper left rim are lighting on a round body (sheen), not parts.

Design: a squat armoured sentry pod. A lathed core (flat underside, a skirt band with a machined
groove, a chamfered shoulder ledge, a low dome); five chamfered armour petals round the visor's
front and sides with real gaps between them and a bolt at each corner; the visor glass draped on
the dome inside a raised chamfered frame; the two lenses as machined housings standing out of the
glass along its normal with recessed emissive lenses and domed cores; a louvred vent housing
on the front skirt (toward the game camera), bolted access panels on the flanks and the back.

Colours (median palette index per region, darkest 112 and brightest >= 120 left out as lighting):
petals 114 (the body's median; 115 and up only in the lower-right sheen), core 114, skirt band
116 (the outer ring's median away from the sheen; E2 QA M4), frame 113, recesses 112, glass 1, big lens housing 114 ring 123 core
127 (emissive), small lens housing 113 ring 117 core 121 (emissive). Polished, clear-coated red
lacquer with a raised F0 (D176), so the rim's crescent is the game's own sheen.

Run: blender --background --python assets/blender/enemies/newshe-195.py [-- --preview out.png] [--no-bake] [--out x.glb]

No concept maps: the model bakes its own AO/roughness maps (D50); the outline shell is D51.
"""

import math
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip  # noqa: E402

NAME = "newshe-195"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# --- plan ---------------------------------------------------------------------------------------
CX, CY = 0.55, 14.9  # the body's centre in sprite px (x = column edge - 12, y = row edge)
# r(theta) = a0 + sum a_n cos(n t) + b_n sin(n t); theta with y down (90 deg = front, screen bottom).
R_F = [(10.1728, 0.0), (-0.0157, 0.0032), (0.1332, 0.0479), (-0.0733, -0.119), (0.0658, 0.0236),
       (-0.0904, 0.0046)]
# The visor: the convex hull of the sprite's dark glass (palette 1/64 and the lenses on it, pixel
# corners inset 0.3 px), Chaikin-smoothed, as its radius about (CX, CY) every 3.75 degrees.
V_TAB = [
    4.927, 4.648, 4.411, 4.21, 4.041, 3.902, 3.787, 3.693, 3.619, 3.562, 3.521, 3.496,
    3.485, 3.488, 3.506, 3.538, 3.584, 3.646, 3.724, 3.814, 3.908, 3.813, 3.661, 3.526,
    3.411, 3.315, 3.236, 3.174, 3.126, 3.092, 3.071, 3.063, 3.066, 3.078, 3.102, 3.137,
    3.182, 3.239, 3.31, 3.394, 3.493, 3.608, 3.741, 3.893, 4.067, 4.266, 4.493, 4.75,
    5.045, 5.389, 5.784, 6.23, 6.712, 7.184, 7.616, 8.008, 8.367, 8.699, 9.001, 9.26,
    9.475, 9.674, 9.856, 9.972, 10.018, 10.038, 10.032, 9.96, 9.863, 9.767, 9.682, 9.612,
    9.542, 9.471, 9.4, 9.327, 9.254, 9.184, 9.122, 9.088, 9.08, 9.087, 9.086, 9.006,
    8.877, 8.736, 8.591, 8.413, 8.204, 7.971, 7.64, 7.135, 6.594, 6.088, 5.642, 5.256,
]


def fourier(coef, t):
    return coef[0][0] + sum(a * math.cos(n * t) + b * math.sin(n * t) for n, (a, b) in enumerate(coef) if n)


def R(t):
    return fourier(R_F, t) - 0.08  # a hair inside the fit: the round edge falls on the pixel steps


VMAX = 0.9  # the visor wraps over the back (row 5) down to the shoulder


def v_radius(t):
    """Periodic Catmull-Rom through V_TAB."""
    n = len(V_TAB)
    u = (t % (2 * math.pi)) / (2 * math.pi) * n
    i = int(u)
    f = u - i
    p0, p1, p2, p3 = (V_TAB[(i + k) % n] for k in (-1, 0, 1, 2))
    return 0.5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (3 * p1 - p0 - 3 * p2 + p3) * f ** 3)


def rho_v(t):
    return min(v_radius(t) / R(t), VMAX)


# --- body profile (rho = r / R(theta), z in sprite px) -------------------------------------------
RHO_SK = 0.995  # skirt
RHO_D = 0.935  # dome foot
Z_SH, Z_TOP = 2.5, 6.6


def z_dome(rho):
    rho = min(max(rho, 0.0), RHO_D)
    return Z_SH + (Z_TOP - Z_SH) * (1 - (rho / RHO_D) ** 2.3) ** 0.5


def S(t, rho):
    r = rho * R(t)
    return Vector((CX + r * math.cos(t), CY + r * math.sin(t), z_dome(rho)))


def frame_at(t, rho):
    """Point on the dome, its outward normal, the radial (d/drho) and around (d/dt) unit tangents."""
    rho = min(rho, RHO_D - 0.012)
    e = 1e-4
    p = S(t, rho)
    if rho < 0.02:
        dr = Vector((math.cos(t), math.sin(t), 0.0))
        n = Vector((0, 0, 1))
        da = n.cross(dr)
        return p, n, dr, da.normalized()
    dr = (S(t, rho + e) - S(t, rho - e)).normalized()
    da = (S(t + e, rho) - S(t - e, rho)).normalized()
    n = da.cross(dr).normalized()
    if n.z < 0:
        n = -n
    return p, n, dr, da


def SO(t, rho, off):
    p, n, _, _ = frame_at(t, rho)
    return p + n * off


# --- materials ------------------------------------------------------------------------------------
CORE, PLATE, FRAME, DEEP, GLASS, HOUS1, RING1, CORE1, HOUS2, RING2, CORE2, BOLT, SKIRT = range(13)
# E2 QA M4 (BONUS 2.3): the satin version (metallic 0.15-0.24, roughness 0.36-0.46, skirt 113) read
# as a dull, flat maroon dome; the original is a dark glossy shell whose rim catches a bright
# red-orange crescent. The sprite's outer 1-3 px ring is 114-116 away from the sheen (median 116 with
# the lit 120-125 crescent and the dark 112-113 limb left out as lighting), the body inside it
# 113-114. So the skirt and its rounded rim bead take 116 and every red part is a polished lacquer
# (art rule 2: the crescent is sheen, not paint). The sheen's colour: a red metal's reflection is pure
# red, and pure red pushed bright goes pink under the game's Neutral tone mapping (D126), never
# orange; the sprite's sheen runs 117 -> 120 -> 123 -> 125 -> 127, red through orange to white. So
# the lacquer is mostly dielectric with a raised F0 (Specular IOR Level, D176) tinted by the
# sprite's own mid-sheen colour (palette 122, as Specular Tint, exported as KHR_materials_specular's
# specularColorFactor): its highlights come out orange and run to yellow-white at the peak, as the
# sprite's do. The colour under the sheen stays the palette index.
PAL_OF = {CORE: 114, PLATE: 114, FRAME: 113, DEEP: 112, GLASS: 1, HOUS1: 114, RING1: 123, CORE1: 127,
          HOUS2: 113, RING2: 117, CORE2: 121, BOLT: 116, SKIRT: 116}
TEXTURED = (CORE, PLATE, FRAME, DEEP, HOUS1, HOUS2, BOLT, SKIRT)
TINT = (1.0, 0.97, 0.94)
BODY_METAL = 0.85  # the body: a dark red metal, its reflections red
SPEC_RIM = 0.8  # F0 0.064 (x the tint) on the rim band, bead and skirt, where the crescent is
METAL = 0.3  # a little red metal under the lacquer
SHEEN_PAL = 122  # the sprite's mid-sheen orange, the lacquer's specular tint


def materials(sprite):
    sheen = common.srgb(*sprite["colors"][str(SHEEN_PAL)])

    def pal(slot, tag, metallic, roughness, glow=0.0, coat=0.0, coat_rough=0.08, spec=None, tint=None):
        mat = common.palette_material(sprite, PAL_OF[slot], f"pod195_{tag}", metallic=metallic,
                                      roughness=roughness, emission_strength=glow)
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = coat_rough
        if spec is not None:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        if tint is not None:
            bsdf.inputs["Specular Tint"].default_value = (*tint, 1.0)
        return mat
    return [
        pal(CORE, "core", BODY_METAL, 0.24),
        pal(PLATE, "armour", BODY_METAL, 0.22),
        pal(FRAME, "frame", BODY_METAL, 0.24),
        pal(DEEP, "recess", 0.06, 0.75),
        pal(GLASS, "glass", 0.0, 0.06, coat=1.0, coat_rough=0.04),
        pal(HOUS1, "lens_housing", BODY_METAL, 0.22),
        pal(RING1, "lens_ring", 0.0, 0.3, glow=1.3),
        pal(CORE1, "lens_core", 0.0, 0.2, glow=3.0),
        pal(HOUS2, "lens2_housing", BODY_METAL, 0.22),
        pal(RING2, "lens2_ring", 0.0, 0.3, glow=1.2),
        pal(CORE2, "lens2_core", 0.0, 0.2, glow=1.8),
        pal(BOLT, "bolt", METAL, 0.2, spec=SPEC_RIM, tint=sheen),
        pal(SKIRT, "skirt", METAL, 0.12, spec=SPEC_RIM, tint=sheen),
    ]


def thetas(t0, t1, step):
    n = max(1, math.ceil((t1 - t0) / step))
    return [t0 + (t1 - t0) * i / n for i in range(n + 1)]


NT = 64
FULL = [2 * math.pi * i / NT for i in range(NT)]


# --- core: lathe ----------------------------------------------------------------------------------
# The rim (E2 QA M4): a rounded bead from the skirt wall (RHO_SK, z 1.7) over a quarter round to the
# dome foot (RHO_D, z 2.3), radius (RHO_SK - RHO_D) R ~ 0.6 px, in place of the old 45 deg chamfer
# and flat ledge. Its normals sweep from level to straight up, so somewhere along the front of it
# the game's sun and environment always find the mirror angle: the sprite's lit crescent (117-125
# on the lower right) comes out as sheen on the polished rim, not as paint. The plan is unchanged.
Z_RIM0, Z_RIM1 = 1.7, 2.3
# The rim band goes on up the dome's steep flank to RHO_RIM, below the petals' lower edge (see
# rho_out): from above it is a ~2 px red ring round the front, where the sprite's crescent is, with
# normals from level to ~50 deg up, so the sun's highlight always lands on it somewhere.
RHO_RIM = 0.8
RIM = [((RHO_SK - RHO_D) * math.cos(math.radians(a)) + RHO_D, Z_RIM0 + (Z_RIM1 - Z_RIM0) * math.sin(math.radians(a)))
       for a in range(0, 91, 10)]


def build_core(P):
    prof = [(0.0, 0.0), (0.9, 0.0), (0.965, 0.3), (RHO_SK, 0.65), (RHO_SK, 1.2), (0.975, 1.2),
            (0.975, 1.5), (RHO_SK, 1.5)] + RIM
    mats = [CORE, CORE, SKIRT, SKIRT, DEEP, SKIRT, SKIRT] + [SKIRT] * (len(RIM))
    dome = [RHO_D * (1 - (i / 10) ** 1.6) for i in range(1, 10)]  # finer near the foot
    dome = sorted(set(dome) | {0.885, 0.83, RHO_RIM}, reverse=True)
    for rho in dome:
        prof.append((rho, z_dome(rho)))
        mats.append(SKIRT if rho >= RHO_RIM - 1e-9 else CORE)  # the lacquered rim band below the petals
    prof.append((0.0, Z_TOP))
    mats.append(CORE)
    rings = []
    for rho, z in prof:
        if rho < 1e-6:
            rings.append([P.v((CX, CY, z))] * NT)
        else:
            rings.append([P.v((CX + rho * R(t) * math.cos(t), CY + rho * R(t) * math.sin(t), z)) for t in FULL])
    away = (CX, CY, 1.4)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(NT):
            j = (i + 1) % NT
            if r0[i] is r0[j]:
                P.f((r0[i], r1[j], r1[i]), mats[k], away=away)
            elif r1[i] is r1[j]:
                P.f((r0[i], r0[j], r1[i]), mats[k], away=away)
            else:
                P.f((r0[i], r0[j], r1[j], r1[i]), mats[k], away=away)


# --- visor: glass and frame -----------------------------------------------------------------------
FW = 0.75  # frame width, px (narrower at the back, where the glass runs down to the shoulder)


def fw(t):
    return max(0.34, min(FW, (RHO_D - 0.012 - rho_v(t)) * R(t)))


# The glass wraps over the back: from FULL index WRAP0 to WRAP1 (213.75 to 309.4 deg, where the
# sprite's glass runs out to the ink border) there's no frame lip; the glass follows the dome foot,
# the shoulder ledge and its chamfer out to the hull's own radius (+0.02), then turns down into
# the body. The frame is an open sweep round the front and sides, its lip easing down at both ends.
WRAP0, WRAP1 = 38, 55
RHO_E_MAX = RHO_SK  # to the chamfer's outer edge


def wrap_path(t, rho0, rho_e):
    """Glass points 0.06 out from the core's profile at angle t, from just past rho0 out to rho_e,
    plus a drop point back into the body and the outward direction there. The core's own polyline
    beyond the dome: its last dome ring (0.912), the foot (RHO_D, 2.3), the
    rounded rim (RIM) out to (RHO_SK, Z_RIM0)."""
    knots = [(r, z_dome(r)) for r in (0.888, 0.9, 0.906)] + [(0.912, z_dome(0.912))] + RIM[::-1]
    knots = [k for k in knots if k[0] > rho0 + 0.004]
    r = R(t)
    full = [(rho0, z_dome(rho0))]
    if rho_e > rho0 + 0.004:
        for k in knots:
            prev = full[-1]
            if k[0] >= rho_e:
                f = (rho_e - prev[0]) / (k[0] - prev[0])
                full.append((rho_e, prev[1] + (k[1] - prev[1]) * f))
                break
            full.append(k)

    def seg_n(a, b):
        da, dz = (b[0] - a[0]) * r, b[1] - a[1]
        ln = math.hypot(da, dz)
        return (-dz / ln, da / ln)
    out = []
    for i in range(1, len(full)):
        n1 = seg_n(full[i - 1], full[i])
        if i + 1 < len(full):
            n2 = seg_n(full[i], full[i + 1])
            m = (n1[0] + n2[0], n1[1] + n2[1])
            ml = math.hypot(*m)
            m = (m[0] / ml, m[1] / ml)
            k = 0.06 / max(0.5, m[0] * n1[0] + m[1] * n1[1])
        else:
            m, k = n1, 0.06
        rho, z = full[i]
        rr = rho * r + m[0] * k
        out.append(Vector((CX + rr * math.cos(t), CY + rr * math.sin(t), z + m[1] * k)))
    if len(full) > 1:
        ln = seg_n(full[-2], full[-1])
        end = out[-1]
    else:
        ln = seg_n((rho0 - 0.003, z_dome(rho0 - 0.003)), full[0])
        end = SO(t, rho0, 0.06)
    nrm = Vector((ln[0] * math.cos(t), ln[0] * math.sin(t), ln[1]))
    tan = Vector((ln[1] * math.cos(t), ln[1] * math.sin(t), -ln[0]))  # along the profile, outward
    return out, end - nrm * 0.14, tan


def zipper(P, a, b, mat, away):
    """Triangulate between two vertex chains of any lengths (>= 1 each)."""
    i = j = 0
    while i < len(a) - 1 or j < len(b) - 1:
        fa = (i + 1) / (len(a) - 1) if len(a) > 1 else 2.0
        fb = (j + 1) / (len(b) - 1) if len(b) > 1 else 2.0
        if j >= len(b) - 1 or (i < len(a) - 1 and fa <= fb):
            P.f((a[i], a[i + 1], b[j]), mat, away=away)
            i += 1
        else:
            P.f((a[i], b[j + 1], b[j]), mat, away=away)
            j += 1


def build_visor(G, F):
    # Glass: draped polar patch inside the frame, 0.06 px above the dome.
    rings = [[G.v((CX, CY, Z_TOP + 0.06))] * NT]
    for f in (0.2, 0.4, 0.58, 0.74, 0.87, 0.96, 1.0):
        rings.append([G.v(tuple(SO(t, f * rho_v(t), 0.06))) for t in FULL])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(NT):
            j = (i + 1) % NT
            if r0[i] is r0[j]:
                G.f((r0[i], r1[j], r1[i]), GLASS, out=(0, 0, 1))
            else:
                G.f((r0[i], r0[j], r1[j], r1[i]), GLASS, away=(CX, CY, -6.0))
    # The wrap over the back, from the patch's edge.
    away = (CX, CY, 0.0)
    cols, drops = [], []
    for i in range(WRAP0, WRAP1 + 1):
        t = FULL[i]
        rho_e = min(v_radius(t) / R(t) + 0.02, RHO_E_MAX)
        pts, drop, tan = wrap_path(t, rho_v(t), rho_e)
        cols.append([rings[-1][i]] + [G.v(tuple(p)) for p in pts])
        drops.append((G.v(tuple(drop)), tan))
    for a, b in zip(cols, cols[1:]):
        zipper(G, a, b, GLASS, away)
    for (a, (da, ta_)), (b, (db, tb_)) in zip(zip(cols, drops), zip(cols[1:], drops[1:])):
        G.f((a[-1], b[-1], db, da), GLASS, out=tuple(ta_ + tb_))
    # Frame: a raised lip round the glass, chamfered, buried skirt outside; open over the wrap.
    ta, tb = FULL[WRAP1], FULL[WRAP0] + 2 * math.pi
    ease = math.radians(22.0)

    def prof(t):
        w = fw(t)
        c = min(0.14, w / 3)
        e = min(t - ta, tb - t) / ease
        k = 0.25 + 0.75 * (1.0 if e >= 1 else e * e * (3 - 2 * e))
        return [(-0.05, -0.05), (0.0, 0.3 * k), (c, 0.44 * k), (w - c, 0.44 * k), (w, 0.3 * k), (w, -0.25)]
    ts = thetas(ta, tb, 2 * math.pi / NT)
    grid = sweep(F, prof, ts, lambda t: rho_v(t), FRAME)
    for row, t, sgn in ((grid[0], ts[0], -1), (grid[-1], ts[-1], 1)):
        _, _, _, da = frame_at(t, rho_v(t))
        F.f([v for v, _, _ in row], FRAME, out=tuple(da * sgn))


def sweep(P, prof, ts, base, mat, closed=False):
    """Sweep a profile [(d px along the dome's radial tangent, offset along its normal)] round
    base(theta). Faces oriented from the profile's own 2D outward normals."""
    grid = []
    profs = []
    for t in ts:
        r = R(t)
        row = []
        pr = prof(t) if callable(prof) else prof
        profs.append(pr)
        for d, off in pr:
            rho = base(t) + d / r
            p, n, dr, _ = frame_at(t, rho)
            row.append((P.v(tuple(p + n * off)), n, dr))
        grid.append(row)
    m = len(ts) if closed else len(ts) - 1
    for i in range(m):
        j = (i + 1) % len(ts)
        for k in range(len(profs[i]) - 1):
            (d0, o0), (d1, o1) = profs[i][k], profs[i][k + 1]
            ox, oy = -(o1 - o0), (d1 - d0)  # direction rotated +90 deg
            _, n, dr = grid[i][k]
            out = dr * ox + n * oy
            P.f((grid[i][k][0], grid[j][k][0], grid[j][k + 1][0], grid[i][k + 1][0]), mat, out=tuple(out))
    return grid


# --- armour petals ----------------------------------------------------------------------------------
GAP = 0.32  # px between petals and between petals and the visor frame
PET_D, PET_C = 0.26, 0.1
RHO_OUT = 0.905  # the petals' outer edge where they meet the visor wrap at the back sides


def rho_out(t, rho_in):
    """The petals stop at RHO_RIM round the front and sides (the rim band shows below them) and
    reach RHO_OUT only where the visor leaves them too narrow (the back of the end petals)."""
    return max(RHO_RIM, min(RHO_OUT, rho_in + 0.16))
PETALS = [(-24.0, 16.0), (16.0, 62.0), (62.0, 118.0), (118.0, 164.0), (164.0, 204.0)]


def petal(P, D, a0, a1):
    t0, t1 = math.radians(a0), math.radians(a1)
    rmid = R((t0 + t1) / 2)
    gt = GAP / 2 / (rmid * 0.75)  # half gap in radians at about three quarters out
    t0, t1 = t0 + gt, t1 - gt
    ct = PET_C / (rmid * 0.75)
    ts = [t0, t0 + ct] + thetas(t0 + ct, t1 - ct, math.radians(6.0))[1:-1] + [t1 - ct, t1]

    def rho_in(t):
        return rho_v(t) + (fw(t) + GAP) / R(t)

    nr = 5
    grid = []
    for ci, t in enumerate(ts):
        r = R(t)
        a = rho_in(t)
        b = rho_out(t, a)
        cr = PET_C / r
        rhos = [a, a + cr] + [a + cr + (b - a - 2 * cr) * k / nr for k in range(1, nr)] + [b - cr, b]
        row = []
        for ri, rho in enumerate(rhos):
            border = ci in (0, len(ts) - 1) or ri in (0, len(rhos) - 1)
            row.append((P.v(tuple(SO(t, rho, PET_D - PET_C if border else PET_D))), t, rho))
        grid.append(row)
    tm = (t0 + t1) / 2
    pc = SO(tm, (rho_in(tm) + rho_out(tm, rho_in(tm))) / 2, 0.0)
    _, pn, _, _ = frame_at(tm, (rho_in(tm) + rho_out(tm, rho_in(tm))) / 2)
    away = tuple(pc - pn * 4.0)
    nc, nrr = len(grid), len(grid[0])
    for ci in range(nc - 1):
        for ri in range(nrr - 1):
            P.f((grid[ci][ri][0], grid[ci + 1][ri][0], grid[ci + 1][ri + 1][0], grid[ci][ri + 1][0]), PLATE, away=away)

    def skirt(chain):
        low = [P.v(tuple(SO(t, rho, -0.3))) for _, t, rho in chain]
        for k in range(len(chain) - 1):
            P.f((chain[k][0], chain[k + 1][0], low[k + 1], low[k]), PLATE, away=away)
    skirt([grid[ci][0] for ci in range(nc)])
    skirt([grid[ci][-1] for ci in range(nc)])
    skirt(grid[0])
    skirt(grid[-1])
    # Bolts: a hex stud near each outer corner, one by each inner corner where the petal is deep.
    for t in (t0 + 2.2 * ct + 0.05, t1 - 2.2 * ct - 0.05):
        bolt(D, t, rho_out(t, rho_in(t)) - 0.07, PET_D)
        if rho_out(t, rho_in(t)) - rho_in(t) > 0.3:
            bolt(D, t, rho_in(t) + 0.07, PET_D)


def local_cyl(P, centre, n, u, rings, mat_of, seg=12, cap=True):
    """A turned part along n: rings [(radius, height)] from the bottom; mat_of[k] between ring k
    and k + 1. The last ring capped (a fan) if cap."""
    w = n.cross(u).normalized()
    built = []
    for r, h in rings:
        if r < 1e-6:
            built.append([P.v(tuple(centre + n * h))] * seg)
        else:
            built.append([P.v(tuple(centre + n * h + (u * math.cos(2 * math.pi * (k + 0.5) / seg)
                                                      + w * math.sin(2 * math.pi * (k + 0.5) / seg)) * r))
                          for k in range(seg)])
    for k, (r0, r1) in enumerate(zip(built, built[1:])):
        (ra, ha), (rb, hb) = rings[k], rings[k + 1]
        # Outward in the (radius, height) plane: rotate the profile direction by -90 deg.
        dr, dh = rb - ra, hb - ha
        orad, oh = dh, -dr
        for i in range(seg):
            j = (i + 1) % seg
            ang = 2 * math.pi * (i + 1) / seg
            radial = u * math.cos(ang) + w * math.sin(ang)
            out = tuple(radial * orad + n * oh)
            if r1[i] is r1[j]:
                P.f((r0[i], r0[j], r1[i]), mat_of[k], out=out)
            elif r0[i] is r0[j]:
                P.f((r0[i], r1[j], r1[i]), mat_of[k], out=out)
            else:
                P.f((r0[i], r0[j], r1[j], r1[i]), mat_of[k], out=out)
    if cap and rings[-1][0] > 1e-6:
        P.f(built[-1], mat_of[-1], out=tuple(n))


def bolt(D, t, rho, base):
    p, n, dr, _ = frame_at(t, rho)
    c = p + n * base
    local_cyl(D, c, n, dr, [(0.3, -0.2), (0.3, 0.12), (0.22, 0.2), (0.0, 0.2)], [BOLT, BOLT, BOLT], seg=6)


# --- lenses ---------------------------------------------------------------------------------------
LENSES = [  # (x, y) sprite px, housing r, lens r, core r, materials
    ((-3.0, 11.0), 2.75, 2.0, 1.05, (HOUS1, RING1, CORE1)),
    ((2.5, 10.5), 1.85, 1.35, 0.6, (HOUS2, RING2, CORE2)),
]


def build_lenses(L):
    for (x, y), rh, rl, rc, (hm, rm, cm) in LENSES:
        t = math.atan2(y - CY, x - CX)
        rho = math.hypot(x - CX, y - CY) / R(t)
        p, n, dr, _ = frame_at(t, rho)
        h = 0.55
        c = p + n * 0.06
        # Housing: a short turned barrel with a chamfered lip, the lens recessed in it, a domed core.
        rings = [(rh - 0.1, -0.6), (rh, -0.2), (rh, h - 0.14), (rh - 0.14, h), (rl + 0.12, h), (rl, h - 0.1),
                 (rl, h - 0.24), (rc + 0.08, h - 0.2), (rc, h - 0.12), (rc * 0.7, h + 0.02), (0.0, h + 0.08)]
        mats = [hm, hm, hm, hm, hm, hm, rm, rm, cm, cm]
        local_cyl(L, c, n, dr, rings, mats, seg=20 if rh > 2 else 14)


# --- skirt details --------------------------------------------------------------------------------
def skirt_frame(t, z):
    r = R(t) * RHO_SK
    p = Vector((CX + r * math.cos(t), CY + r * math.sin(t), z))
    nrm = Vector((math.cos(t), math.sin(t), 0.0))
    # include the plan's slope (dR/dt) for a true normal
    e = 1e-4
    tan = Vector((R(t + e) * math.cos(t + e) - R(t - e) * math.cos(t - e),
                  R(t + e) * math.sin(t + e) - R(t - e) * math.sin(t - e), 0)).normalized()
    nrm = Vector((tan.y, -tan.x, 0))
    if nrm.dot(Vector((math.cos(t), math.sin(t), 0))) < 0:
        nrm = -nrm
    return p, nrm, tan


def lbox(D, t, z, u0, u1, v0, v1, w0, w1, ch, mat):
    """A chamfered box on the skirt at angle t: u along the skirt, v up, w out of it."""
    p, nrm, tan = skirt_frame(t, z)
    up = Vector((0, 0, 1))
    pts = [tuple(p + tan * a + up * b + nrm * c) for a, b, c in cbox(u0, u1, v0, v1, w0, w1, ch)]
    hull(D, pts, mat)


def band(D, a0, a1, z0, z1, w0, w1, ch, mat, step=3.0):
    """A chamfered block that follows the skirt's curve from angle a0 to a1 (degrees): z0-z1 up,
    w0-w1 out from the skirt surface (negative = buried)."""
    ts = thetas(math.radians(a0), math.radians(a1), math.radians(step))
    sec = [(w0, z0), (w1 - ch, z0), (w1, z0 + ch), (w1, z1 - ch), (w1 - ch, z1), (w0, z1)]
    rows = []
    for t in ts:
        p, nrm, _ = skirt_frame(t, 0.0)
        rows.append([D.v(tuple(p + nrm * w + Vector((0, 0, z)))) for w, z in sec])
    cen = skirt_frame((ts[0] + ts[-1]) / 2, 0.0)[0]
    away = (CX, CY, (z0 + z1) / 2)
    m = len(sec)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(m):
            kk = (k + 1) % m
            D.f((r0[k], r1[k], r1[kk], r0[kk]), mat, away=away)
    # End caps, chamfered by pulling the outer edge in a little.
    for r, t, sgn in ((rows[0], ts[0], -1), (rows[-1], ts[-1], 1)):
        _, _, tan = skirt_frame(t, 0.0)
        D.f(r, mat, out=tuple(tan * sgn))


def stud(D, a, z, base=0.0, r=0.17):
    t = math.radians(a)
    p, nrm, _ = skirt_frame(t, z)
    local_cyl(D, p + nrm * base, nrm, Vector((0, 0, 1)), [(r, -0.25), (r, 0.1), (r * 0.6, 0.15), (0.0, 0.15)],
              [BOLT, BOLT, BOLT], seg=6)


def build_skirt_details(D):
    # Front (toward the game camera): a louvred vent across the groove, sunk into the skirt.
    # A housing standing proud of the skirt: a chamfered frame (two rails and two posts) round a
    # dark back plate, four chamfered slats between, set 0.08 back from the frame's face.
    band(D, 73.0, 107.0, 1.82, 2.04, -0.4, 0.24, 0.06, FRAME)
    band(D, 73.0, 107.0, 0.68, 0.9, -0.4, 0.24, 0.06, FRAME)
    band(D, 73.0, 75.6, 0.8, 1.94, -0.4, 0.24, 0.06, FRAME, step=1.3)
    band(D, 104.4, 107.0, 0.8, 1.94, -0.4, 0.24, 0.06, FRAME, step=1.3)
    band(D, 75.0, 105.0, 0.85, 1.88, -0.4, 0.03, 0.0, DEEP)
    for k in range(4):
        z = 0.98 + k * 0.215
        band(D, 75.4, 104.6, z, z + 0.15, -0.2, 0.16, 0.045, PLATE)
    # Flanks and back: bolted access panels standing a little proud.
    for c, half in ((8.0, 8.5), (172.0, 8.5), (222.0, 7.0), (270.0, 7.0), (318.0, 7.0)):
        band(D, c - half, c + half, 0.62, 2.0, -0.4, 0.1, 0.07, PLATE)
        for su in (-1, 1):
            for z in (0.88, 1.74):
                stud(D, c + su * (half - 1.8), z, base=0.1)


def build(coll, sprite):
    mats = materials(sprite)
    core = Part("pod195_core", smooth_angle=28)
    build_core(core)
    glass = Part("pod195_glass", smooth_angle=60)
    frame = Part("pod195_frame", smooth_angle=30)
    build_visor(glass, frame)
    arm = Part("pod195_armour", smooth_angle=30)
    det = Part("pod195_details", smooth_angle=35)
    for a0, a1 in PETALS:
        petal(arm, det, a0, a1)
    lens = Part("pod195_lenses", smooth_angle=35)
    build_lenses(lens)
    build_skirt_details(det)
    return [T.finish(p, mats, coll) for p in (core, glass, frame, arm, det, lens)]


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "pod195")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    # The outline shell is made from the closed parts, before hidden faces are culled.
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(closed, coll, voxel=0.014, faces=1500, smooth=12)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
