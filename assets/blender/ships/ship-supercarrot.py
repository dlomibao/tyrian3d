"""SuperCarrot (player ship, tyrian.shp#8 frame 119 and its banking frames 115-123), built the way
the USP Talon is (assets/blender/usp_talon.py, DECISIONS.md D50-D53): a hard-surface ship that reads
as a real spacecraft from every angle, with modelled panel lines and detail, a small baked occlusion
map instead of a concept projection, an outline shell and named engine glows.

The sprite is authoritative (D52) for the plan outline, the eye (the ship's cockpit) and the colours:
- Plan: the carrot root follows frame 119's teardrop row by row (PLAN, a smooth pchip fitted to the
  INNER edge of the sprite's ink border, D74 / docs/agents/OUTLINE-BORDER.md: the game's own ink
  outline stands in for the border; a pointed tip at row 1 widening steadily to a round belly at
  rows 13-16 and a rounded back at row 19), the tail its three leaves (a blade out to the left, a
  keel down the middle, a short blade to the right) and the stem between.
- Banking: the game rolls this one model up to 35 degrees for frames 115-123, so every frame is
  matched by the rolled top view (tools/sprite_mask.py rule IoU >= 0.95 on each). The root's section
  is round enough (SE_N, HT, HB) that its rolled outline stays on the sprite's; the tail parts sit at
  heights that roll to where the banking frames draw them (see the tail's plan outlines).
- Eye: the sprite's round bronze patch (rows 9-13, 21 pixels, a disc of radius 2.5 px round
  column/row 11.5) is a raised bronze housing with a glossy lens; the pale centre pixel is sheen.
- Colours: each part takes the palette index the sprite uses where it covers it (the median of
  those pixels, the darkest shading and the brightest highlights left out as lighting): armour 121,
  the upper chevron band 122, the tip 120, the collar 118, the eye rim 181 and lens 183 (dark
  recess 176), the stem 194, the left leaf 197, the keel and right leaf 196, the keel spine 200,
  dark green machinery 193.
The concept (features/concepts/ship-supercarrot.jpg) guides the rest where it agrees: armour plates
whose seams arch forward over the top (stacked chevrons), a raised eye housing with a segmented dark
ring, a ribbed collar at the back, flank louvres, and a green mechanical tail of armour blades with
green-glowing engines under them. Underneath: a keel strake, gear doors and intakes.

How it is built (as usp_talon.py, whose helpers it uses):
- Every part is a low-poly cage in sprite px (x = column - 12, y = sprite row, aft is +y, z up),
  moved to Blender at the end (X = x / 12, Y = (14 - y) / 12, Z = z / 12).
- The root is a core of superelliptic sections (pchip widths, so it never swells) under separate
  armour plates that stand 0.3 px proud with 45-degree chamfered edges, so panel lines are real
  gaps; the tail's blades are chamfered slabs. Flat faces stay flat (sharp by angle, weighted
  normals); hidden faces culled.
- Texture: no concept projection (texture_bake.py skips it: "bake": "model" in its maps.json). The
  script bakes ambient occlusion with an edge lift (a colour multiplier, slightly cool: TINT, D53)
  and a roughness/metalness map. Base Color = map x palette colour.
- Materials are palette materials (pal_<index>_...) so palettes, fades and the hit flash apply; the
  engine glows are emissive palette greens.
- Exported beside it: an outline shell (common.outline_shell, D51) and `tyrian_engines` (three
  green engine glows) on the object.

    Blender --background --factory-startup --python ship-supercarrot.py -- [--out path.glb] [--no-bake] [--preview png]

Default: export public/models/ships/ship-supercarrot.glb and its sprite model entry
(common.export_sprite_model). --out writes only that .glb (for render checks); --no-bake leaves the
model plain (fast iterations).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from usp_talon import Part, cbox, cull_hidden, fillet, finish, frange, hull, join, pchip  # noqa: E402

NAME = "ship-supercarrot"
MODEL = f"ships/{NAME}"
PX = 1 / 12
AX = -0.5  # the root's axis (sprite column 11.5)

# Material slots and their palette index, metalness, roughness (satin; D52, D53).
(ARMOUR, ARMOUR_LT, TIP, CORE, COLLAR, BELLY, DEEP, RIM, LENS, STEM, GCORE, FIN_L, FIN_R, SPINE,
 GLOW, GLOW_CORE) = range(16)
MATS = {
    ARMOUR: (121, "armour", 0.18, 0.42),
    ARMOUR_LT: (122, "armour_light", 0.18, 0.4),
    TIP: (120, "tip", 0.22, 0.34),
    CORE: (112, "core", 0.15, 0.6),
    COLLAR: (118, "collar", 0.2, 0.42),
    BELLY: (121, "belly", 0.12, 0.55),
    DEEP: (176, "recess", 0.1, 0.8),
    RIM: (181, "eye_rim", 0.3, 0.34),
    LENS: (183, "eye_glass", 0.1, 0.06),
    STEM: (194, "stem", 0.2, 0.44),
    GCORE: (193, "machinery", 0.2, 0.5),
    FIN_L: (197, "leaf", 0.12, 0.52),
    FIN_R: (196, "leaf_dark", 0.12, 0.52),
    SPINE: (200, "spine", 0.18, 0.34),
}
GLOWS = {GLOW: (203, "engine_glow", 2.0), GLOW_CORE: (205, "engine_core", 3.0)}
TEXTURED = tuple(i for i in MATS if i != LENS)

# The baked colour map's tint (linear multipliers), per material (D53). The game's lighting and
# three's Neutral tone mapping (it subtracts a small offset from every channel) shift lit colours:
# measured on top renders lit like the game, the orange armour came out ~1.5 degrees yellower and
# more saturated than its flat colour, the green leaves washed out (saturation 0.76 against the
# sprite's 0.99) and the eye's bronze, the Talon's khaki ramp, more saturated. So the orange map
# trims green a little, the green map trims red and blue, and the bronze takes the Talon's cool tint.
# A multiplier cannot add blue to the near-pure orange, so its saturation stays a little high.
TINT = (1.0, 0.95, 0.97)
TINTS = {RIM: (0.76, 0.86, 1.0), DEEP: (0.76, 0.86, 1.0)}
for _slot in (STEM, GCORE, FIN_L, FIN_R, SPINE):
    TINTS[_slot] = (0.8, 1.0, 0.8)


def materials(sprite):
    out = []
    for i in range(16):
        if i in GLOWS:
            idx, tag, strength = GLOWS[i]
            out.append(common.palette_material(sprite, idx, f"{NAME}_{tag}", metallic=0.0, roughness=0.4,
                                               emission_strength=strength))
        else:
            idx, tag, metal, rough = MATS[i]
            out.append(common.palette_material(sprite, idx, f"{NAME}_{tag}", metallic=metal, roughness=rough))
    return out


# --- the root's shape ---------------------------------------------------------------------------

# The plan outline (half width by row, sprite px), fitted to the INNER edge of frame 119's ink
# border (D74, docs/agents/OUTLINE-BORDER.md: the game's own ink outline stands in for the sprite's
# border): a pointed tip at row 1 widening steadily to the round belly at rows 13-16 and a rounded
# back ending at row 19. Each row's half width sits within half a pixel of the inner mask's
# staircase (cols 11, 10-12, 9-13, 8-14, 7-15, 6-16, 7-15, 9-13 round column 11.5).
TIP0 = 0.85  # the point
PLAN_Y = [TIP0, 1.5, 2.5, 3.5, 4.5, 5.5, 7.0, 8.5, 10.0, 11.5, 13.0, 13.6, 14.5, 15.5, 16.3, 17.0, 17.6, 18.2, 18.6, 19.0]
PLAN_W = [0.0, 0.42, 0.75, 1.3, 1.85, 2.38, 3.05, 3.5, 4.05, 4.6, 5.06, 5.36, 5.5, 5.55, 5.48, 5.05, 4.35, 2.75, 2.4, 1.9]
PLAN = pchip(PLAN_Y, PLAN_W)
D = 0.3  # how far the armour plates stand out of the core
RAIL = 0.12  # and the side rails stand out of the plates (the rails make the plan outline)
Y_END = 19.0  # the root's back

# Section: a superellipse (a little square, so it reads machined, not inflated), taller above the
# axis than below.
SE_N = 2.5
SE_E = 2 / SE_N
HT, HB = 0.86, 0.85  # top and bottom heights, fractions of the half width
ZC = 0.0


def CW(y):
    """Core half width."""
    return max(0.08, PLAN(min(max(y, TIP0), Y_END)) - D - RAIL)


def core_pt(y, a):
    """Point on the core at row y, angle a (degrees from straight up, positive toward +x)."""
    w = CW(y)
    t = math.radians(a)
    s, c = math.sin(t), math.cos(t)
    x = AX + w * math.copysign(abs(s) ** SE_E, s)
    h = (HT if c >= 0 else HB) * w
    return Vector((x, y, ZC + h * math.copysign(abs(c) ** SE_E, c)))


def core_n(y, a):
    pa = core_pt(y, a + 0.4) - core_pt(y, a - 0.4)
    py = core_pt(y + 0.03, a) - core_pt(y - 0.03, a)
    n = pa.cross(py)
    p = core_pt(y, a)
    if n.dot(p - Vector((AX, y, ZC))) < 0:
        n = -n
    return n.normalized()


def surf(y, a, off=0.0):
    return core_pt(y, a) + core_n(y, a) * off


def top_z(x, y):
    """Height of the core's upper surface at plan point (x, y)."""
    w = CW(y)
    u = min(1.0, abs(x - AX) / w)
    return ZC + HT * w * (1 - u ** SE_N) ** (1 / SE_N)


# --- mesh helpers -------------------------------------------------------------------------------

def body_core(P):
    ys = [TIP0 + d for d in (0.25, 0.38, 0.55, 0.8, 1.1)] + frange(2.4, 18.6, 0.55) + [18.8, Y_END]
    angs = [360 * k / 36 for k in range(36)]
    rings = [[P.v(tuple(core_pt(y, a))) for a in angs] for y in ys]
    for y, r0, r1 in zip(ys, rings, rings[1:]):
        for i in range(36):
            j = (i + 1) % 36
            P.f((r0[i], r0[j], r1[j], r1[i]), CORE, away=(AX, y, ZC))
    P.f(rings[0], CORE, out=(0, -1, 0))
    P.f(rings[-1], CORE, out=(0, 1, 0))


def pplate(P, y0f, y1f, a0, a1, mat, d=D, c=0.13, depth=0.35, ystep=0.6, astep=10.0, closed=False,
           ch0=True, ch1=True, skirt0=True):
    """An armour plate on the root standing `d` proud of the core, between the edges y0f(a) and
    y1f(a) (rows, functions of the angle) and from angle a0 to a1 (degrees; closed: all round), with
    45-degree chamfered edges `c` wide and skirts down to `depth` under the core."""
    if closed:
        n = int(round(360 / astep))
        cols = [(a0 + 360 * k / n, False) for k in range(n)]
    else:
        am = (a0 + a1) / 2
        ym = (y0f(am) + y1f(am)) / 2
        ca = min(math.degrees(c / max(CW(ym) * 0.9, 0.4)), (a1 - a0) / 4)
        inner = frange(a0 + ca, a1 - ca, astep)
        cols = [(a0, True)] + [(a, False) for a in inner] + [(a1, True)]
    spans = [(y0f(a), y1f(a)) for a, _ in cols]
    m = max(0, max(int(math.ceil((yb - ya - 2 * c) / ystep)) - 1 for ya, yb in spans))
    grid = []  # grid[col][row] = (vert, y, a, border)
    for (a, bc), (ya, yb) in zip(cols, spans):
        cc = min(c, (yb - ya) / 3)
        ys = [ya, ya + cc] + [ya + cc + (yb - ya - 2 * cc) * j / (m + 1) for j in range(1, m + 1)] + [yb - cc, yb]
        col = []
        for k, y in enumerate(ys):
            border = bc or (k == 0 and ch0) or (k == len(ys) - 1 and ch1)
            col.append((P.v(tuple(surf(y, a, d - c if border else d))), y, a))
        grid.append(col)
    nc, nr = len(grid), len(grid[0])
    for i in range(nc if closed else nc - 1):
        j = (i + 1) % nc
        for k in range(nr - 1):
            y = grid[i][k][1]
            P.f((grid[i][k][0], grid[j][k][0], grid[j][k + 1][0], grid[i][k + 1][0]), mat, away=(AX, y, ZC))

    def skirt(chain, outf):
        low = [P.v(tuple(surf(y, a, -depth))) for _, y, a in chain]
        for k in range(len(chain) - 1):
            y, a = (chain[k][1] + chain[k + 1][1]) / 2, (chain[k][2] + chain[k + 1][2]) / 2
            P.f((chain[k][0], chain[k + 1][0], low[k + 1], low[k]), mat, out=tuple(outf(y, a)))

    def dy(y, a):
        return surf(y + 0.05, a) - surf(y - 0.05, a)

    def da(y, a):
        return surf(y, a + 0.5) - surf(y, a - 0.5)
    wrap = [0] if closed else []
    if skirt0:
        skirt([grid[i][0] for i in list(range(nc)) + wrap], lambda y, a: -dy(y, a))
    skirt([grid[i][-1] for i in list(range(nc)) + wrap], dy)
    if not closed:
        skirt(grid[0], lambda y, a: -da(y, a))
        skirt(grid[-1], da)
    return grid


def seam(side, top, p=1.4):
    """A plate seam round the root: at row `side` on the flanks and belly, arching to row `top` over
    the top centre (top < side: forward, a chevron; top > side: back)."""
    def f(a):
        a = (a + 180) % 360 - 180
        if abs(a) >= 90:
            return side
        return side + (top - side) * math.cos(math.radians(a)) ** p
    return f


def shift(f, dy):
    return lambda a: f(a) + dy


def poly_offset(poly, dist):
    """Offset a closed plan polygon [(x, y)] outward by dist (negative: inward), mitred."""
    n = len(poly)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    sgn = 1 if area > 0 else -1
    normals = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        normals.append((sgn * (y1 - y0) / ln, -sgn * (x1 - x0) / ln))
    out = []
    for i in range(n):
        (ax, ay), (bx, by) = normals[i - 1], normals[i]
        sx, sy = ax + bx, ay + by
        ln = math.hypot(sx, sy) or 1e-9
        ux, uy = sx / ln, sy / ln
        cos_half = max(0.4, ux * bx + uy * by)
        out.append((poly[i][0] + ux * dist / cos_half, poly[i][1] + uy * dist / cos_half))
    return out


def slab(P, poly, zt, zb, mat, c=0.14, side_mat=None):
    """A chamfered slab: the plan polygon [(x, y)] between the planes zt(x, y) and zb(x, y)
    (linear functions, so its faces stay flat), its top and bottom edges chamfered `c`."""
    inner = poly_offset(poly, -c)
    sm = mat if side_mat is None else side_mat
    ti = [P.v((x, y, zt(x, y))) for x, y in inner]
    to = [P.v((x, y, zt(x, y) - c)) for x, y in poly]
    bo = [P.v((x, y, zb(x, y) + c)) for x, y in poly]
    bi = [P.v((x, y, zb(x, y))) for x, y in inner]
    P.f(ti, mat, out=(0, 0, 1))
    P.f(bi, sm, out=(0, 0, -1))
    n = len(poly)
    cx = sum(x for x, _ in poly) / n
    cy = sum(y for _, y in poly) / n
    nrm = poly_offset(poly, 1.0)
    for i in range(n):
        j = (i + 1) % n
        ox = (nrm[i][0] - poly[i][0] + nrm[j][0] - poly[j][0])
        oy = (nrm[i][1] - poly[i][1] + nrm[j][1] - poly[j][1])
        P.f((ti[i], ti[j], to[j], to[i]), mat, out=(ox, oy, 1.0))
        P.f((to[i], to[j], bo[j], bo[i]), sm, out=(ox, oy, 0.0))
        P.f((bo[i], bo[j], bi[j], bi[i]), sm, out=(ox, oy, -1.0))
    return (cx, cy)


def smooth_poly(pts, radius, k=3):
    return fillet(pts, radius, k)


def plane(z0, x0=0.0, y0=0.0, kx=0.0, ky=0.0):
    return lambda x, y: z0 + kx * (x - x0) + ky * (y - y0)


def tube_y(P, cx, cz, prof, mat, sides=8, rnd=0.35, cap0=True, cap1=True, mats=None):
    """A machined tube along +y: a chamfered, filleted octagon section of radius r at each (y, r)
    of `prof`; mats[i] (default mat) between ring i and i + 1."""
    corners = [(math.cos(2 * math.pi * (k + 0.5) / sides), math.sin(2 * math.pi * (k + 0.5) / sides)) for k in range(sides)]
    unit = fillet(corners, rnd, 1)
    rings = []
    for y, r in prof:
        rings.append([P.v((cx + r * u, y, cz + r * v)) for u, v in unit])
    n = len(unit)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        y0, y1 = prof[i][0], prof[i + 1][0]
        m = mat if mats is None else mats[i]
        for k in range(n):
            kk = (k + 1) % n
            if abs(y1 - y0) < 1e-6:
                P.f((r0[k], r0[kk], r1[kk], r1[k]), m, out=(0, 1 if prof[i + 1][1] < prof[i][1] else -1, 0))
            else:
                P.f((r0[k], r0[kk], r1[kk], r1[k]), m, away=(cx, (y0 + y1) / 2, cz))
    if cap0:
        P.f(rings[0], mat, out=(0, -1, 0))
    if cap1:
        P.f(rings[-1], mats[-1] if mats else mat, out=(0, 1, 0))


def nozzle(P, nx, nz, y0, s, shroud=True):
    """An engine nozzle pointing aft (+y) from row y0, scale s: collar, bell and a deep glowing
    throat (as the Talon's)."""
    prof = [(0.74, y0, GCORE), (0.82, y0 + 0.12, GCORE), (0.82, y0 + 0.4, GCORE), (0.76, y0 + 0.48, GCORE),
            (0.74, y0 + 0.75, GCORE), (0.6, y0 + 0.75, GCORE), (0.53, y0 + 0.5, GLOW), (0.47, y0 + 0.15, GLOW_CORE),
            (0.0, y0 + 0.15, GLOW_CORE)]
    prof = [(r * s, y0 + (y - y0) * s, m) for r, y, m in prof]
    N = 16
    rings = []
    for r, y, _ in prof:
        rings.append([P.v((nx + r * math.cos(2 * math.pi * (k + 0.5) / N), y, nz + r * math.sin(2 * math.pi * (k + 0.5) / N)))
                      for k in range(N)] if r > 0 else [P.v((nx, y, nz))])
    for i in range(len(prof) - 1):
        r0, r1 = rings[i], rings[i + 1]
        ya, yb = prof[i][1], prof[i + 1][1]
        inside = i >= 5
        for k in range(N):
            kk = (k + 1) % N
            if len(r1) == 1:
                P.f((r0[k], r0[kk], r1[0]), prof[i][2], out=(0, 1, 0))
            elif inside:
                P.f((r0[k], r0[kk], r1[kk], r1[k]), prof[i][2],
                    away=(nx + 50 * (r0[k].co.x - nx), (ya + yb) / 2, nz + 50 * (r0[k].co.z - nz)))
            elif abs(prof[i][0] - prof[i + 1][0]) > 0.05 * s and abs(ya - yb) < 0.01:
                P.f((r0[k], r0[kk], r1[kk], r1[k]), prof[i][2], out=(0, 1, 0))
            else:
                P.f((r0[k], r0[kk], r1[kk], r1[k]), prof[i][2], away=(nx, (ya + yb) / 2, nz))
    # The back of the collar meets whatever it stands out of: a cap behind it.
    P.f(rings[0], GCORE, out=(0, -1, 0))


# --- the root -----------------------------------------------------------------------------------

EYE_X, EYE_Y = -0.5, 11.5  # the eye's centre: sprite column/row 11.5
R_RIM, R_RIM_IN, R_LENS, R_SOCK = 2.5, 2.02, 1.78, 2.8
G = 0.16  # panel gap

S0 = seam(3.6, 2.8)     # the tip cap's back edge
S1 = seam(6.6, 4.4)
S2 = seam(10.0, 7.1)
S3 = seam(13.6, 15.6)   # behind the eye the seam arches back round it
S4 = seam(17.2, 17.2)  # the collar
COLLAR_END = 18.8


def lo(f):
    return shift(f, G / 2)


def hi(f):
    return shift(f, -G / 2)


def const(v):
    return lambda a: v


def eye_angle(ynom):
    """The angle where the plate surface is R_SOCK + G/2 from the eye's centre in plan (row ynom)."""
    a0, a1 = 0.0, 90.0
    for _ in range(40):
        m = (a0 + a1) / 2
        if surf(ynom, m, D).x - EYE_X < R_SOCK + G / 2:
            a0 = m
        else:
            a1 = m
    return a0


def build_root(P):
    body_core(P)
    # Tip cap all round, its front meeting a polished point.
    pplate(P, const(TIP0 + 0.4), hi(S0), 0, 360, TIP, closed=True, ch0=False, skirt0=False, ystep=0.4, astep=12)
    ring = [surf(TIP0 + 0.4, 360 * k / 30, D) for k in range(30)]
    hull(P, [tuple(p) for p in ring] + [(AX, TIP0 - 0.05, ZC + 0.05)], TIP)
    # Band A: top, flanks and belly.
    for a0, a1, mat in ((-48, 48, ARMOUR), (48, 132, ARMOUR), (132, 228, BELLY), (228, 312, ARMOUR)):
        g = math.degrees(G / 2 / max(CW(5.0), 1))
        pplate(P, lo(S0), hi(S1), a0 + g, a1 - g, mat, ystep=0.7)
    # Band B: rows 4.4-10 (the sprite's lighter upper body, 122).
    for a0, a1, mat in ((-45, 45, ARMOUR_LT), (45, 128, ARMOUR_LT), (128, 232, BELLY), (232, 315, ARMOUR_LT)):
        g = math.degrees(G / 2 / CW(8.0))
        pplate(P, lo(S1), hi(S2), a0 + g, a1 - g, mat)
    # Band C round the eye: the centre panels ahead of and behind the eye hug its socket; the flank
    # panels split at the eye's row.
    af, ab = eye_angle(9.6), eye_angle(13.4)

    def ring_front(a, ynom=9.6):
        dx = abs(surf(ynom, a, D).x - EYE_X)
        r = R_SOCK + G / 2
        return EYE_Y - math.sqrt(max(0.0, r * r - dx * dx))

    def ring_back(a, ynom=13.4):
        dx = abs(surf(ynom, a, D).x - EYE_X)
        r = R_SOCK + G / 2
        return EYE_Y + math.sqrt(max(0.0, r * r - dx * dx))
    g = math.degrees(G / 2 / CW(11.0))
    pplate(P, lo(S2), lambda a: min(ring_front(a), EYE_Y - G / 2), -af + g, af - g, ARMOUR_LT, astep=6)
    pplate(P, lambda a: max(ring_back(a), EYE_Y + G / 2), hi(S3), -ab + g, ab - g, ARMOUR, astep=6)
    for sx in (1, -1):
        def A(a0, a1, sx=sx):
            return (a0, a1) if sx > 0 else (-a1, -a0)
        pplate(P, lo(S2), const(EYE_Y - G / 2), *A(af + g, 122 - g), ARMOUR)
        pplate(P, const(EYE_Y + G / 2), hi(S3), *A(ab + g, 122 - g), ARMOUR)
    pplate(P, lo(S2), hi(S3), 122 + g, 238 - g, BELLY)
    # Band D: rows 13.6-17.
    for a0, a1, mat in ((-42, 42, ARMOUR), (42, 124, ARMOUR), (124, 236, BELLY), (236, 318, ARMOUR)):
        g = math.degrees(G / 2 / CW(15.5))
        pplate(P, lo(S3), hi(S4), a0 + g, a1 - g, mat)
    # The collar: a dark ring with two ribs over the top and under the belly (the concept's ribbed
    # band at the back).
    pplate(P, lo(S4), const(COLLAR_END), 0, 360, COLLAR, closed=True, ystep=0.6, astep=10)
    for y in (17.6, 18.25):
        for a0, a1 in ((-72, 72), (108, 252)):
            pplate(P, const(y), const(y + 0.32), a0, a1, COLLAR, d=D + 0.14, c=0.08, astep=8)
    # Side rails along the widest line, from the tip cap to the collar: they carry the plan
    # outline unbroken over the panel seams (the concept's edge rails).
    for sx in (1, -1):
        a0, a1 = (81, 99) if sx > 0 else (-99, -81)
        pplate(P, const(2.9), const(18.6), a0, a1, ARMOUR, d=D + RAIL, c=0.1, ystep=0.7, astep=6)

    # Flank louvres (the concept's dark vents along the sides): a dark grille low on each flank
    # panel with three slats, two per side.
    for sx in (1, -1):
        for y0, y1 in ((6.95, 9.35), (14.0, 16.4)):
            a0, a1 = (104, 124) if sx > 0 else (-124, -104)
            pplate(P, const(y0), const(y1), a0, a1, DEEP, d=D + 0.06, c=0.04, astep=5)
            for k in range(3):
                yy = y0 + 0.35 + k * (y1 - y0 - 0.7) / 2
                pplate(P, const(yy - 0.13), const(yy + 0.13), a0 + 1, a1 - 1, COLLAR, d=D + 0.16, c=0.04, astep=5)
    # Reaction-control ports on the nose: dark recessed blocks low on each flank.
    for sx in (1, -1):
        for y in (4.3, 5.2):
            p = surf(y, 112 * sx, D)
            hull(P, [(p.x + sx * x, yy, p.z + z) for x, yy, z in cbox(-0.35, 0.18, y - 0.3, y + 0.3, -0.25, 0.25, 0.05)], DEEP)

    # Underneath: a keel strake along the centre line, a nose gear door, two main gear doors with
    # hinge blocks, and intake scoops low on the flanks.
    pts = []
    for y, drop in ((6.5, 0.1), (8.0, 0.45), (15.0, 0.45), (16.6, 0.1)):
        b = surf(y, 180, 0).z
        pts += [(AX + sx * x, y, z) for sx in (-1, 1) for x, z in ((0.45, b + 0.5), (0.32, b - drop - D), (0.15, b - drop - D - 0.1))]
    hull(P, pts, CORE)
    pplate(P, const(7.3), const(9.6), 163, 197, ARMOUR, d=D + 0.16)
    for sx in (1, -1):
        a0, a1 = (150, 172) if sx > 0 else (188, 210)
        pplate(P, const(13.9), const(16.6), a0, a1, ARMOUR, d=D + 0.16)
        for y in (14.2, 16.0):
            p = surf(y, (a0 + a1) / 2, D + 0.16)
            hull(P, [(p.x + x, yy, p.z + z) for x, yy, z in cbox(-0.25, 0.25, y - 0.22, y + 0.22, -0.35, 0.05, 0.05)], CORE)
        # Intake scoop: an orange lip with a dark mouth facing forward.
        p = surf(11.5, 140 * sx, D)
        hull(P, [(p.x + sx * x, yy, p.z + z) for x, yy, z in cbox(-0.9, 0.35, 10.2, 12.8, -0.55, 0.45, 0.2)], ARMOUR)
        hull(P, [(p.x + sx * x, yy, p.z + z) for x, yy, z in cbox(-0.7, 0.18, 10.1, 10.35, -0.38, 0.3, 0.04)], DEEP)


def build_eye(P):
    """The eye housing: an orange socket ring on the hull, a raised bronze rim with a flat machined
    top, a dark recessed ring with eight bronze teeth, and the glossy lens."""
    N = 40
    zc = top_z(EYE_X, EYE_Y)
    # The rim's machined top is a plane tilted with the hull (lower at the front, higher at the
    # back), so the housing stands the same height proud of the hull all round.
    z_f = top_z(EYE_X, EYE_Y - R_RIM) + D + 0.42
    z_b = top_z(EYE_X, EYE_Y + R_RIM) + D + 0.42

    def zr(y):
        return z_f + (z_b - z_f) * (y - (EYE_Y - R_RIM)) / (2 * R_RIM)
    z_rim = zr(EYE_Y)

    def ring(r, zf):
        return [P.v((EYE_X + r * math.cos(2 * math.pi * k / N), EYE_Y + r * math.sin(2 * math.pi * k / N),
                     zf(EYE_X + r * math.cos(2 * math.pi * k / N), EYE_Y + r * math.sin(2 * math.pi * k / N)))) for k in range(N)]

    def band(r0, r1, mat, out):
        for k in range(N):
            j = (k + 1) % N
            P.f((r0[k], r0[j], r1[j], r1[k]), mat, out=out(k))

    def radial(k, s=1.0):
        t = 2 * math.pi * (k + 0.5) / N
        return (s * math.cos(t), s * math.sin(t), 0.0)
    # Socket: follows the hull, 0.42 proud, chamfered outside.
    so_lo = ring(R_SOCK, lambda x, y: top_z(x, y) - 0.3)
    so_ch = ring(R_SOCK, lambda x, y: top_z(x, y) + D + 0.12 - 0.12)
    so_top = ring(R_SOCK - 0.12, lambda x, y: top_z(x, y) + D + 0.12)
    si_top = ring(R_RIM - 0.02, lambda x, y: top_z(x, y) + D + 0.12)
    band(so_lo, so_ch, ARMOUR_LT, radial)
    band(so_ch, so_top, ARMOUR_LT, lambda k: (*radial(k)[:2], 1.0))
    band(so_top, si_top, ARMOUR_LT, lambda k: (0, 0, 1))
    # Rim: outer wall from below the socket up to a chamfer and the flat top, inner wall down to the
    # recess floor.
    r_lo = ring(R_RIM, lambda x, y: top_z(x, y))
    r_ch = ring(R_RIM, lambda x, y: zr(y) - 0.12)
    r_top = ring(R_RIM - 0.12, lambda x, y: zr(y))
    r_in = ring(R_RIM_IN + 0.08, lambda x, y: zr(y))
    r_in2 = ring(R_RIM_IN, lambda x, y: zr(y) - 0.08)
    r_fl = ring(R_RIM_IN, lambda x, y: zr(y) - 0.42)
    band(r_lo, r_ch, RIM, radial)
    band(r_ch, r_top, RIM, lambda k: (*radial(k)[:2], 1.0))
    band(r_top, r_in, RIM, lambda k: (0, 0, 1))
    band(r_in, r_in2, RIM, lambda k: (*radial(k, -1)[:2], 1.0))
    band(r_in2, r_fl, DEEP, lambda k: radial(k, -1))
    # Recess floor out to the lens.
    f_in = ring(R_LENS, lambda x, y: zr(y) - 0.42)
    band(r_fl, f_in, DEEP, lambda k: (0, 0, 1))
    # Eight teeth across the recess (the concept's segmented ring).
    for k in range(8):
        t = 2 * math.pi * (k + 0.5) / 8
        u, v = math.cos(t), math.sin(t)
        pts = []
        for r in (R_LENS - 0.05, R_RIM_IN + 0.02):
            for w in (-0.16, 0.16):
                for dz in (-0.45, -0.14):
                    py = EYE_Y + r * v + w * u
                    pts.append((EYE_X + r * u - w * v, py, zr(py) + dz))
        hull(P, pts, RIM)
    # Lens: a glossy dome from the recess floor.
    K = 7
    base = z_rim - 0.42

    def zb(y):
        return zr(y) - 0.42
    rings = []
    for i in range(K + 1):
        f = i / K
        r = R_LENS * math.cos(f * math.pi / 2 * 0.96)
        z = base + 0.16 + 0.72 * math.sin(f * math.pi / 2 * 0.96)
        rings.append([P.v((EYE_X + r * math.cos(2 * math.pi * k / N), EYE_Y + r * math.sin(2 * math.pi * k / N),
                           z - base + zb(EYE_Y + r * math.sin(2 * math.pi * k / N)))) for k in range(N)])
    lens_lo = ring(R_LENS, lambda x, y: zb(y))
    band(lens_lo, rings[0], LENS, radial)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(N):
            j = (k + 1) % N
            P.f((r0[k], r0[j], r1[j], r1[k]), LENS, away=(EYE_X, EYE_Y, base - 2.0))
    P.f(rings[-1], LENS, out=(0, 0, 1))
    return z_rim


# --- the tail -----------------------------------------------------------------------------------

# Plan outlines (x = column - 12, y = row), fitted to the inner edge of frame 119's ink round its
# three leaves (D74): the stem (cols 10-12 at row 19, 9-11 at row 20), the left blade (cols 7-8 at
# rows 21-22, out to col 6 at rows 23-24), the keel down the middle (cols 9-14 at row 22, 10-12 at
# row 24, 10 at row 26) and the short right blade (cols 13-14 at rows 22-23). The gaps between them
# (col 8 at row 23, cols 7-9 at row 24) stay open.
#
# The banking frames (115-123) are this model rolled up to 35 degrees (src/render/drawListRenderer.ts
# MAX_ROLL), and their tails differ from a flat one rolled: the left blade tucks in, the keel's back
# widens both ways and the right blade reaches further out when the ship banks left. So the parts
# sit at heights that roll to where the sprite draws them: the left blade flat at the roll axis (it
# narrows, cols 7-8 on every frame), the keel a tall blade rising aft (its height swings out to col 8
# banked left and col 13 banked right), the right blade drooping aft (it swings out to col 15 banked
# left and tucks under banked right) and a ventral skeg under the keel (hidden level, col 13 banked
# left).
LEFT_FIN = [(-2.8, 20.8), (-4.1, 20.85), (-4.55, 21.15), (-4.55, 22.75), (-5.6, 23.1), (-5.65, 24.5), (-5.45, 24.95),
            (-4.7, 24.85), (-4.05, 24.0), (-3.6, 23.0)]
KEEL = [(-2.0, 20.95), (-0.8, 21.05), (0.2, 21.45), (0.6, 22.0), (0.8, 23.9), (0.5, 24.7), (-0.3, 25.4), (-0.6, 26.4),
        (-0.75, 27.0), (-1.45, 27.0), (-1.6, 26.3), (-2.1, 25.0), (-2.7, 23.5), (-2.9, 21.9), (-2.8, 21.0)]
KEEL_SPLIT = 25.5  # the keel's top rises to here, then its trailing blade falls away
RIGHT_FIN = [(0.4, 21.6), (1.4, 21.85), (2.35, 22.1), (2.65, 22.4), (2.65, 22.8), (3.1, 23.05), (3.1, 23.75),
             (2.8, 24.0), (0.6, 23.95), (0.4, 22.2)]
HUB = [(-3.9, 20.95), (0.3, 21.05), (0.55, 21.5), (0.55, 22.8), (-2.6, 22.8), (-3.9, 22.5)]


def clip_y(poly, y, keep_below):
    """The part of a closed plan polygon [(x, y)] with row < y (keep_below) or > y."""
    def inside(p):
        return p[1] <= y if keep_below else p[1] >= y
    out = []
    for i in range(len(poly)):
        p, q = poly[i - 1], poly[i]
        if inside(q):
            if not inside(p):
                t = (y - p[1]) / (q[1] - p[1])
                out.append((p[0] + t * (q[0] - p[0]), y))
            out.append(q)
        elif inside(p):
            t = (y - p[1]) / (q[1] - p[1])
            out.append((p[0] + t * (q[0] - p[0]), y))
    return out


def build_tail(P):
    # The stem: a machined octagonal coupling out of the root's back, a flange at each end, into an
    # elbow collar leaning left (the sprite's stem steps a pixel left at row 20).
    tube_y(P, AX, 0.0, [(18.2, 1.75), (18.9, 1.75), (18.9, 1.85), (19.75, 1.85), (19.75, 1.5), (19.9, 1.3),
                        (20.2, 1.2)], STEM, sides=8, rnd=0.3)
    tube_y(P, -1.4, 0.0, [(19.85, 1.3), (20.05, 1.55), (20.75, 1.55), (20.95, 1.3)], STEM, sides=8, rnd=0.3)
    # Conduits from the root into the machinery, under the stem.
    for sx in (1, -1):
        tube_y(P, AX + sx * 0.75, -1.1, [(18.0, 0.28), (20.0, 0.28)], GCORE, sides=6, rnd=0.2)
    # Machinery deck under the blades.
    slab(P, smooth_poly(HUB, 0.3, 2), plane(-0.2), plane(-1.1), GCORE, c=0.15)
    # Left blade: near the roll axis, drooping a little outboard, a raised armour panel along it.
    zl = plane(0.1, x0=-4.55, kx=0.32)
    slab(P, smooth_poly(LEFT_FIN, 0.25, 2), zl, lambda x, y: zl(x, y) - 0.4, FIN_L, c=0.12)
    panel = [(-3.7, 21.3), (-4.3, 21.45), (-4.3, 22.9), (-5.2, 23.4), (-5.25, 24.3), (-4.45, 23.6), (-3.8, 22.9)]
    slab(P, smooth_poly(panel, 0.2, 2), lambda x, y: zl(x, y) + 0.17, lambda x, y: zl(x, y) - 0.25, FIN_L, c=0.08)
    # Right blade: drooping aft (50 degrees), a raised panel along it.
    zr = plane(0.1, y0=22.5, ky=-2.0)
    slab(P, smooth_poly(RIGHT_FIN, 0.22, 2), zr, lambda x, y: zr(x, y) - 0.38, FIN_R, c=0.1)
    panel = [(1.0, 22.3), (2.2, 22.45), (2.35, 23.0), (2.75, 23.25), (2.75, 23.65), (1.05, 23.65)]
    slab(P, smooth_poly(panel, 0.15, 2), lambda x, y: zr(x, y) + 0.16, lambda x, y: zr(x, y) - 0.2, FIN_R, c=0.07)
    # The keel down the middle: a tall armour blade rising aft with a raised spine, its trailing
    # blade falling away behind row 25.5.
    zk = plane(2.3, y0=20.5, ky=0.35)
    keel = smooth_poly(KEEL, 0.3, 2)
    fore = clip_y(keel, KEEL_SPLIT + 0.1, True)
    slab(P, fore, zk, plane(-1.35), FIN_R, c=0.2)
    spine = [(-1.75, 21.25), (-0.75, 21.3), (0.0, 21.85), (0.25, 23.8), (-0.4, 24.8), (-1.0, 25.6), (-1.6, 25.6),
             (-1.95, 24.6), (-2.3, 23.4), (-2.3, 21.8)]
    slab(P, smooth_poly(spine, 0.25, 2), lambda x, y: zk(x, y) + 0.3, lambda x, y: zk(x, y) - 0.3, SPINE, c=0.12)
    zt = plane(zk(0, KEEL_SPLIT), y0=KEEL_SPLIT, ky=-0.6)
    aft = clip_y(keel, KEEL_SPLIT - 0.3, False)
    slab(P, aft, zt, plane(-1.35 + 0.5 * (KEEL_SPLIT - 0.3 - 24.5), y0=KEEL_SPLIT - 0.3, ky=0.5), SPINE, c=0.15)
    # A ventral skeg under the keel.
    slab(P, smooth_poly([(-0.45, 23.4), (0.05, 23.4), (0.05, 25.0), (-0.45, 25.0)], 0.12, 2), plane(-0.9),
         plane(-3.1, y0=23.4, ky=0.25), FIN_R, c=0.08)
    # Vents along the keel's flanks: a dark grille with four slats on each side, and a panel strip
    # below it.
    for xs, sgn, y0, y1 in ((-2.85, -1, 21.6, 23.3), (0.72, 1, 22.0, 23.8)):
        hull(P, [(xs + sgn * x, y, z) for x, y, z in cbox(-0.2, 0.06, y0, y1, 0.0, 1.25, 0.04)], DEEP)
        for k in range(4):
            yy = y0 + 0.25 + k * (y1 - y0 - 0.5) / 3
            hull(P, [(xs + sgn * x, y, z) for x, y, z in cbox(-0.2, 0.12, yy - 0.09, yy + 0.09, 0.05, 1.2, 0.03)], GCORE)
        hull(P, [(xs + sgn * x, y, z) for x, y, z in cbox(-0.2, 0.08, y0 - 0.3, y1 + 0.2, -0.75, -0.3, 0.05)], FIN_R)
    # Engines under the blades and the keel: pods with nozzles glowing green at their backs.
    engines = []
    for cx, cz, y0, y1, r, s in ((-5.0, -0.5, 22.9, 24.6, 0.34, 0.42), (1.3, -0.65, 22.3, 23.8, 0.4, 0.48),
                                 (-1.1, -1.6, 21.0, 24.9, 0.55, 0.65)):
        tube_y(P, cx, cz, [(y0, r * 0.7), (y0 + 0.35, r), (y1 - 0.2, r), (y1, r * 0.95)], GCORE, sides=8, rnd=0.3)
        nozzle(P, cx, cz, y1 - 0.12, s)
        engines.append((cx, cz, y1 - 0.12 + 0.75 * s))
    return engines


def build(coll, sprite):
    mats = materials(sprite)
    root = Part("carrot_root", smooth_angle=32)
    build_root(root)
    eye = Part("carrot_eye", smooth_angle=40)
    build_eye(eye)
    tail = Part("carrot_tail", smooth_angle=32)
    engines = build_tail(tail)
    objs = [finish(p, mats, coll) for p in (root, eye, tail)]
    return objs, engines


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

def bake_maps(obj, out_dir, size=1024, samples=96):
    """As usp_talon.bake_maps: UV the model and bake a grey colour multiplier (ambient occlusion at
    two scales plus a light lift on bevelled edges, tinted per material: TINT, TINTS) and a
    metallic-roughness map, wired into the palette materials (Base Color = map x palette colour)."""
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
        print("supercarrot: no GPU bake", err)
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

    col_img = bpy.data.images.new("supercarrot_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("supercarrot_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"

    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(slot, m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
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
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            tt = TINTS.get(slot, TINT)
            for k in range(3):
                L(math_("MULTIPLY", v, tt[k]), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(i, m, mode) for i, m in enumerate(mats)}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
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

    for i in TEXTURED:
        m = mats[i]
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    objs, engines = build(coll, sprite)
    obj = join(objs, NAME)
    cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"supercarrot: {len(obj.data.polygons)} faces, {tris} triangles")
    # Where the menu backdrop puts its engine glows (src/ui/backdrop.ts): just behind the three
    # nozzles, in glTF axes (x, y up, z aft), in the nozzles' green (palette 205).
    obj["tyrian_engines"] = {"color": "#20e749",
                             "at": [[round(x * PX, 4), round(z * PX, 4), round((y + 0.5 - 14) * PX, 4)] for x, z, y in engines]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = out.parent if out else root / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, faces=1500)
    print(f"supercarrot: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
