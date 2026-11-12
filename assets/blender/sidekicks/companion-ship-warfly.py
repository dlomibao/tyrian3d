"""Companion Ship Warfly (sidekick 19; tyrian.shp#9 frames 87/89, drawn 2x2 = a 24x28 block):

What it is: a small red-brown manta/delta escort fighter that trails the player's ship (style 1).
Reading the sprite (symmetric about the middle of column 12):
- a pointed nose cap (rows 8-10, palette 68, its lit centre ridge on column 12);
- a grey dome canopy (rows 10-13, columns 10-14; glass 104 in a dark 101-102 frame; the 63 glint at
  (11, 11) is sheen, not geometry);
- leading-edge root extensions out to columns 7/17 on row 12, and from their tips a bright ridge that
  runs in to the canopy's shoulders (rows 13-15) and back out to the trailing edge (rows 16-17): the
  crease where the raised fuselage deck meets the down-sloping wing. Lit on both sides, so it is a
  ridge: here a raised strake;
- broad wings (median 70) to rounded tips at columns 3/21 (rows 15-16), a flat trailing edge (row 18);
- a lit dorsal spine (column 12, rows 14-18, 74) between two short engine nacelles (columns 10-11 /
  13-14, rows 16-18; dark intake 163, heat-tinted nozzle 115), dark-teal louvre strips (51-56)
  running back-outwards beside them;
- the exhaust flame, one per frame (87 long, to row 22, 120/123; 89 short, to row 20, 119/122):
  emissive parts shown per frame (common.frame_part). No banking frames, so D93 does not apply.

 leads with the silhouette from the small tilted game camera: a pronounced fuselage hump
under the dome so the side and rear read as a fighter rather than a flat plate, anhedral wings that
catch the light differently left and right (as the sprite's 71 / 68 wings do), raised crease strakes
for the sprite's bright chevron, a dorsal spine that stands clear between round nacelles, and a
two-tone emissive plume. Details (panel lines as V grooves and proud plates: nose seam, slats, flaps,
louvre slats) only where the game camera sees them; the underside is a plain closed belly.

Units while building: sprite px, x = c - 12.5 (pixel-edge column c), y = 14 - r (north = the nose),
z up. Blender: X = (x + 0.5) / 12, Y = y / 12, Z = z / 12 (the block's centre is column edge 12).

    Blender --background --factory-startup --python sidekicks/companion-ship-warfly.py -- [--no-bake] [--preview out.png]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
MODEL = "sidekicks/companion-ship-warfly"

NAME = "sidekick-companion-ship-warfly"
TAG = "warfly"
PX = 1 / 12
pchip, frange, Part, hull, cbox = T.pchip, T.frange, T.Part, T.hull, T.cbox


def ST(pts):
    return pchip([p[0] for p in pts], [p[1] for p in pts])


# --- stations (r = sprite row, pixel edge) ---------------------------------------------------------
# Half width of the top outline on the inner mask (D74): nose w = r - 8, the LERX kink at row 12,
# leading edge w = r - 7 (rows 12-15), the round tip at row 16 (|x| 8.78), the flat trailing edge at 18.
W = ST([[7.78, 0.0], [8.5, 0.62], [11.5, 3.55], [11.95, 4.25], [12.5, 5.5], [15.35, 8.35], [16.0, 8.78],
        [16.6, 8.5], [17.5, 7.55], [18.0, 6.7]])
# The crease (deck edge): x of the sprite's bright ridge pixels (4.5, 3, 2, 2, 3, 4 on rows 12-17).
XC = ST([[7.78, 0.0], [9.0, 0.45], [10.5, 1.15], [11.9, 2.5], [12.5, 3.9], [13.5, 2.9], [14.5, 2.15],
         [15.5, 2.05], [16.5, 2.75], [17.5, 3.6], [18.0, 4.0]])
ZC = ST([[7.78, 1.2], [9.0, 1.6], [10.5, 1.95], [12.5, 2.1], [14.5, 2.3], [16.5, 2.2], [18.0, 1.95]])
# Deck centre: a fuselage hump (design B: higher than the crease, so the side view reads a body).
ZD = ST([[7.78, 1.25], [9.0, 1.85], [10.5, 2.3], [12.0, 2.55], [14.0, 2.6], [15.5, 2.45], [18.0, 2.05]])
# Wing edge top (anhedral) and the keel.
ZE = ST([[7.78, 1.2], [10.0, 1.05], [12.5, 0.95], [15.5, 0.62], [16.6, 0.62], [18.0, 0.8]])
TE = 0.3
ZB = ST([[7.78, 1.0], [9.0, 0.5], [11.0, 0.12], [16.0, 0.08], [18.0, 0.35]])
NOSE_SEAM = 10.0

DOME = dict(r=12.0, rx=2.18, ry=1.78, z0=2.3, h=1.65, frame=0.36)
SPINE = dict(r0=13.6, r1=18.5, hwB=0.55, hwT=0.26, zT=ST([[13.6, 2.85], [14.3, 3.2], [16.5, 3.05], [18.5, 2.45]]))
NAC = dict(x=1.25, z=1.85, R=0.6, r0=15.8, r1=18.35)
# Flame half widths per frame (the inner mask's rows 18-21 / 18-19), palette outer / core.
FLAME = {
    87: dict(hw=[[17.9, 2.2], [18.4, 3.3], [19.0, 3.05], [19.5, 2.5], [20.5, 1.55], [21.5, 0.6], [22.05, 0.0]],
             pal=120, core=123),
    89: dict(hw=[[17.9, 2.2], [18.3, 2.6], [18.8, 2.3], [19.3, 1.6], [19.8, 0.8], [20.1, 0.0]],
             pal=119, core=122),
}

# --- materials -------------------------------------------------------------------------------------
(HULL, NOSE, BELLY, COLLAR, GLASS, SPINE_M, NACELLE, INTAKE, NOZZLE, NOZ_GLOW, LOUVRE, CANNON, DEEP) = range(13)
# Palette index per slot: the sprite's median per region (lighting extremes dropped): wing / hull 70,
# nose 68, dome 104 (frame 102), spine 74, nacelle 68 with its intake 163, nozzle 115, louvres 54.
PAL_OF = {HULL: 70, NOSE: 68, BELLY: 67, COLLAR: 102, GLASS: 104, SPINE_M: 74, NACELLE: 68, INTAKE: 163,
          NOZZLE: 115, NOZ_GLOW: 120, LOUVRE: 54, CANNON: 103, DEEP: 64}
METAL = 0.3
TEXTURED = (HULL, NOSE, BELLY, COLLAR, SPINE_M, NACELLE, INTAKE, NOZZLE, LOUVRE, CANNON, DEEP)
# Baked map tint on the red hull: the game's Neutral tone mapping pushes the lit red toward a
# saturated orange-red; a little less red keeps the sprite's brown-red (D53's reasoning, smaller).
TINT = (0.94, 0.98, 1.0)


def materials(sprite):
    def rgb(i):
        return common.srgb(*sprite["colors"][str(i)])

    def pal(slot, tag, metallic, roughness):
        i = PAL_OF[slot]
        return common.material(f"pal_{i}_{TAG}_{tag}", rgb(i), metallic=metallic * METAL, roughness=roughness)
    glow = PAL_OF[NOZ_GLOW]
    return [
        pal(HULL, "hull", 0.7, 0.42),
        pal(NOSE, "nose", 0.7, 0.38),
        pal(BELLY, "belly", 0.6, 0.5),
        pal(COLLAR, "canopy_frame", 0.8, 0.35),
        common.material(f"pal_{PAL_OF[GLASS]}_{TAG}_glass", rgb(PAL_OF[GLASS]), metallic=0.2, roughness=0.26),
        pal(SPINE_M, "spine", 0.75, 0.36),
        pal(NACELLE, "nacelle", 0.7, 0.4),
        pal(INTAKE, "intake", 0.4, 0.6),
        pal(NOZZLE, "nozzle", 0.8, 0.4),
        common.material(f"pal_{glow}_{TAG}_nozzle_glow", rgb(glow), roughness=0.4, emission=rgb(glow),
                        emission_strength=1.0),
        pal(LOUVRE, "louvre", 0.6, 0.45),
        pal(CANNON, "cannon", 0.85, 0.32),
        pal(DEEP, "recess", 0.3, 0.8),
    ]


# --- hull section --------------------------------------------------------------------------------

def top_profile(r):
    """(x, z) from the centre line out to the edge: a crowned deck to the crease, the wing down to a
    chamfered, rounded edge."""
    w = max(W(r), 0.03)
    xc = min(XC(r), 0.72 * w)
    zc, zd, ze = ZC(r), ZD(r), ZE(r)
    xe = max(w - 0.24, xc + 0.05)
    return [(0.0, zd), (0.4 * xc, zd - (zd - zc) * 0.18), (0.75 * xc, zd - (zd - zc) * 0.6), (xc, zc),
            (xc + (xe - xc) * 0.35, zc + (ze - zc) * 0.42), (xc + (xe - xc) * 0.7, zc + (ze - zc) * 0.76),
            (xe, ze), (w, ze - 0.12)]


def bot_profile(r):
    """(x, z) from the edge back to the keel: a plain closed belly."""
    w = max(W(r), 0.03)
    xc = min(XC(r), 0.72 * w)
    ze, zb = ZE(r), ZB(r)
    zeb = ze - TE
    xe = max(w - 0.26, xc + 0.05)
    return [(w, zeb + 0.06), (xe, zeb), (xc + (xe - xc) * 0.5, zb + (zeb - zb) * 0.5), (xc, zb + 0.05), (0.0, zb)]


def top_z(x, r):
    P = top_profile(r)
    ax = abs(x)
    for (x0, z0), (x1, z1) in zip(P, P[1:]):
        if ax <= x1:
            t = (ax - x0) / ((x1 - x0) or 1)
            return z0 + (z1 - z0) * t
    return P[-1][1]


def hull_loop(y, grow=0.0):
    r = 14 - y
    T_ = top_profile(r)
    B_ = bot_profile(r)
    pts = [(-x, z) for x, z in reversed(T_[1:])] + list(T_) + list(B_) + [(-x, z) for x, z in reversed(B_[:-1])]
    cx, cz = 0.0, (ZD(r) + ZB(r)) / 2
    if grow:
        vn, _ = T.offset_loop(pts, (cx, cz))
        pts = [(x + nx * grow, z + nz * grow) for (x, z), (nx, nz) in zip(pts, vn)]
    return pts, (cx, cz)


def build_hull(P):
    """One loft, tail to nose, with V-groove panel lines at the nose seam and the deck joint."""
    rows = [18.0, 17.7, 17.4, 17.05, 16.7, 16.35, 16.05, 15.75, 15.4, 15.0, 14.5, 14.0, 13.6, 13.2, 12.8,
            12.4, 12.1, 11.8, 11.5, 11.0, 10.5]
    rings, mats = [], []
    for r in rows:
        rings.append((hull_loop, 14 - r, 0.0))
        mats.append(HULL)
    # Nose seam: a V groove at row 10, the radome cap forward of it.
    for r, g in ((NOSE_SEAM + 0.09, 0.0), (NOSE_SEAM, -0.09), (NOSE_SEAM - 0.09, 0.0)):
        rings.append((hull_loop, 14 - r, g))
        mats.append(HULL if r > NOSE_SEAM else NOSE)
    for r in (9.5, 9.0, 8.6, 8.25, 8.0, 7.86):
        rings.append((hull_loop, 14 - r, 0.0))
        mats.append(NOSE)
    T.loft_rings(P, rings, mats[:-1] + [NOSE], cap0=True, cap1=True)
    # The tail cap: the core's back face is the trailing edge, darker (it sits in the plume's light).


# --- surface plates (conform to the hull top) --------------------------------------------------------

def surf_plate(P, xa, xb, r0, r1, mat, side, d=0.1, c=0.07, rstep=0.4, ncol=None, depth=0.3, zf=None):
    """A plate standing `d` proud of the hull top between |x| = xa(r)..xb(r) and rows r0..r1 on one
    side (side = +1 right, -1 left, 0 = across the centre line, xa = -xb), its edges chamfered `c`, a
    skirt down `depth` into the hull."""
    zf = zf or top_z
    rs = [r0, r0 + c] + frange(r0 + c, r1 - c, rstep)[1:-1] + [r1 - c, r1]
    wmax = max(xb(r) - xa(r) for r in rs)
    n = ncol or max(2, int(math.ceil(wmax / 0.45)))
    us = [0.0] + [i / n for i in range(n + 1)] + [1.0]
    grid = []
    for i, r in enumerate(rs):
        a, b = xa(r), xb(r)
        wd = max(b - a, 1e-3)
        cu = min(c / wd, 0.3)
        row = []
        for j, u in enumerate(us):
            uu = cu if j == 1 else (1 - cu if j == len(us) - 2 else u)
            uu = 0.0 if j == 0 else (1.0 if j == len(us) - 1 else max(cu, min(1 - cu, uu)))
            x = a + (b - a) * uu
            border = i in (0, len(rs) - 1) or j in (0, len(us) - 1)
            X = x * (side if side else 1)
            row.append(P.v((X, 14 - r, zf(x, r) + (d - c if border else d))))
        grid.append(row)
    for i in range(len(rs) - 1):
        for j in range(len(us) - 1):
            P.f((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]), mat, out=(0, 0, 1))
    # Skirts.
    def low(v, x, r):
        return P.v((v.co.x, v.co.y, zf(x, r) - depth))
    perim = []
    for j in range(len(us)):
        perim.append((0, j))
    for i in range(1, len(rs)):
        perim.append((i, len(us) - 1))
    for j in range(len(us) - 2, -1, -1):
        perim.append((len(rs) - 1, j))
    for i in range(len(rs) - 2, 0, -1):
        perim.append((i, 0))
    rm = (r0 + r1) / 2
    xm = (xa(rm) + xb(rm)) / 2 * (side if side else 1)
    lows = {}
    for (i, j) in perim:
        v = grid[i][j]
        ax = abs(v.co.x)
        lows[(i, j)] = P.v((v.co.x, v.co.y, zf(ax, rs[i]) - depth))
    for k in range(len(perim)):
        a, b = perim[k], perim[(k + 1) % len(perim)]
        va, vb = grid[a[0]][a[1]], grid[b[0]][b[1]]
        mid_r = (rs[a[0]] + rs[b[0]]) / 2
        cxm = (xa(mid_r) + xb(mid_r)) / 2 * (side if side else 1)
        P.f((va, vb, lows[b], lows[a]), mat, away=(cxm, 14 - mid_r, (va.co.z + vb.co.z) / 2 - 0.2))
    return grid


def lin(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    def f(r):
        if r <= xs[0]:
            return ys[0]
        for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
            if r <= x1:
                return y0 + (y1 - y0) * (r - x0) / (x1 - x0)
        return ys[-1]
    return f


def build_plates(P):
    for s in (-1, 1):
        # Crease strake: a raised rib along the sprite's bright chevron, from the LERX root to the
        # trailing edge.
        surf_plate(P, lambda r: min(XC(r), 0.72 * W(r)) - 0.24, lambda r: min(XC(r), 0.72 * W(r)) + 0.24,
                   12.3, 17.92, HULL, s, d=0.17, c=0.08, rstep=0.4, ncol=2)
        # Canopy sill: the darker forebody panel beside the dome (68 on (9,11) (9,12) (10,13)).
        surf_plate(P, lin([[11.0, 2.35], [12.6, 2.35], [13.3, 1.6], [13.95, 1.55]]),
                   lin([[11.0, 3.2], [12.0, 3.4], [12.9, 3.3], [13.4, 2.55], [13.95, 2.45]]),
                   11.0, 13.95, NOSE, s, d=0.07, c=0.05, rstep=0.5, ncol=2)
        # Heat-tinted exhaust tile outboard of each nozzle (115 on (10,17) / (14,17)).
        surf_plate(P, lambda r: 1.7, lambda r: 2.42, 16.95, 17.95, NOZZLE, s, d=0.1, c=0.05, rstep=0.5, ncol=2)
        # Leading-edge slat, a panel inside the swept edge.
        surf_plate(P, lambda r: W(r) - 1.15, lambda r: W(r) - 0.42, 12.75, 15.55, HULL, s, d=0.08, c=0.06,
                   rstep=0.45, ncol=2)
        # Outboard flap and aileron along the trailing edge.
        surf_plate(P, lambda r: 4.35, lambda r: 5.95, 17.15, 17.93, HULL, s, d=0.08, c=0.06, rstep=0.4, ncol=3)
        surf_plate(P, lambda r: 6.1, lambda r: min(7.25, W(r) - 0.35), 17.0, 17.9, HULL, s, d=0.08, c=0.06,
                   rstep=0.45, ncol=2)
        # Wing-root panel between the strake and the slat, rows 13.2-16.6.
        surf_plate(P, lambda r: min(XC(r), 0.72 * W(r)) + 0.42, lambda r: max(min(XC(r), 0.72 * W(r)) + 0.9,
                                                                               W(r) - 1.35),
                   13.1, 16.9, HULL, s, d=0.05, c=0.05, rstep=0.6, ncol=3)
        # Louvre strip beside each engine, running back-outwards (51/54/56 on (11,15) (10,16) (9,17)).
        lx = lin([[15.0, 0.62], [17.85, 2.55]])
        surf_plate(P, lambda r: lx(r), lambda r: lx(r) + 0.72, 15.0, 17.85, LOUVRE, s, d=0.06, c=0.05,
                   rstep=0.35, ncol=2)
        for k in range(1, 6):
            r = 15.0 + 2.85 * k / 6
            x0 = lx(r) + 0.06
            hull(P, [(s * x0, 14 - r + dy, top_z(x0, r) + dz) for dy in (-0.07, 0.07) for dz in (0.0, 0.16)]
                 + [(s * (x0 + 0.6), 14 - r + dy, top_z(x0 + 0.6, r) + dz) for dy in (-0.07, 0.07) for dz in (0.0, 0.16)],
                 DEEP)


def build_canopy(G, F):
    """The grey dome on the fuselage hump, in a dark chamfered frame (rows 10-13, columns 10-14)."""
    D = DOME
    cy = 14 - D["r"]
    n = 24
    rx, ry, fw = D["rx"], D["ry"], D["frame"]
    # Frame: foot (inside the hull), outer top, inner top, inner foot under the glass edge.
    rings = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        def at(kx, dz):
            x, y = (rx + kx) * ca, cy + (ry + kx * ry / rx) * sa
            return (x, y, top_z(x, 14 - y) + dz)
        z_out = top_z((rx + fw) * ca, 14 - (cy + (ry + fw) * sa))
        rings.append([F.v((( rx + fw) * ca, cy + (ry + fw * ry / rx) * sa, z_out - 0.3)),
                      F.v(((rx + fw) * ca, cy + (ry + fw * ry / rx) * sa, max(z_out, D["z0"] - 0.25) + 0.12)),
                      F.v(((rx + fw * 0.3) * ca, cy + (ry + fw * 0.3 * ry / rx) * sa, D["z0"] + 0.22)),
                      F.v(((rx - 0.02) * ca, cy + (ry - 0.02) * sa, D["z0"] + 0.18)),
                      F.v(((rx - 0.1) * ca, cy + (ry - 0.1) * sa, D["z0"] - 0.3))])
    for k in range(n):
        a, b = rings[k], rings[(k + 1) % n]
        for i in range(4):
            F.f((a[i], a[i + 1], b[i + 1], b[i]), COLLAR, away=(0.0, cy, D["z0"] - 1.0))
    # Glass: a slightly forward-swept dome (its crown a touch aft of centre, like a bubble canopy).
    steps = 7
    domes = []
    for j in range(steps):
        t = j / steps
        ph = t * math.pi / 2
        s = math.cos(ph)
        lift = D["h"] * math.sin(ph)
        domes.append([G.v((rx * s * math.cos(2 * math.pi * k / n), cy - 0.15 * (1 - s) + ry * s * math.sin(2 * math.pi * k / n),
                           D["z0"] + 0.1 + lift)) for k in range(n)])
    crown = G.v((0.0, cy - 0.15, D["z0"] + 0.1 + D["h"]))
    gc = (0.0, cy, D["z0"])
    for l0, l1 in zip(domes, domes[1:]):
        for k in range(n):
            m = (k + 1) % n
            G.f((l0[k], l0[m], l1[m], l1[k]), GLASS, away=gc)
    for k in range(n):
        G.f((domes[-1][k], domes[-1][(k + 1) % n], crown), GLASS, away=gc)
    # Close the glass underneath (inside the frame).
    G.f(list(reversed(domes[0])), GLASS, out=(0, 0, -1))


def build_spine(P):
    """The lit dorsal spine: a chamfered ridge from behind the dome to the tail, between the nacelles."""
    S = SPINE
    rs = frange(S["r0"], S["r1"], 0.4)
    rings = []
    for k, r in enumerate(rs):
        y = 14 - r
        zt = S["zT"](r)
        t = 0.55 if k == 0 else 1.0
        hb, ht = S["hwB"] * t, S["hwT"] * t
        zb = ZD(min(r, 18.0)) - 0.3
        rings.append([P.v(p) for p in ((-hb, y, zb), (hb, y, zb), (hb, y, zt - 0.28), (ht, y, zt), (-ht, y, zt),
                                       (-hb, y, zt - 0.28))])
    c = lambda r: (0.0, 14 - r, (S["zT"](r) + ZD(min(r, 18.0))) / 2 - 0.2)
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(6):
            j = (i + 1) % 6
            P.f((a[i], a[j], b[j], b[i]), SPINE_M, away=c(rs[k]))
    P.f(rings[0], SPINE_M, out=(0, 1, 0))
    P.f(rings[-1], SPINE_M, out=(0, -1, 0))
    # Two cross grooves on the spine top (access panel lines): thin dark bars just proud.
    for r in (15.3, 16.9):
        zt = S["zT"](r)
        hull(P, cbox(-S["hwT"] - 0.02, S["hwT"] + 0.02, 14 - r - 0.05, 14 - r + 0.05, zt - 0.05, zt + 0.015, 0.01),
             DEEP)


def tube(P, x, z, prof, mats, n=12, cap0=True, cap1=True):
    """A round part along y at (x, z): prof [(r, radius)], mats per segment."""
    rings = []
    for r, rad in prof:
        rings.append([P.v((x + rad * math.cos(2 * math.pi * k / n), 14 - r, z + rad * math.sin(2 * math.pi * k / n)))
                      for k in range(n)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        m = mats[i] if isinstance(mats, (list, tuple)) else mats
        for k in range(n):
            j = (k + 1) % n
            P.f((a[k], a[j], b[j], b[k]), m, away=(x, 14 - (prof[i][0] + prof[i + 1][0]) / 2, z))
    m0 = mats[0] if isinstance(mats, (list, tuple)) else mats
    m1 = mats[-1] if isinstance(mats, (list, tuple)) else mats
    if cap0:
        P.f(rings[0], m0, out=(0, 1, 0))
    if cap1:
        P.f(rings[-1], m1, out=(0, -1, 0))


def build_nacelles(P):
    N = NAC
    for s in (-1, 1):
        x = s * N["x"]
        R = N["R"]
        # Cowl (dark intake ramp at the front, 163), the body (68), a band, the heat-tinted nozzle (115).
        tube(P, x, N["z"], [(N["r0"], 0.5 * R), (N["r0"] + 0.25, 0.92 * R), (16.7, R), (16.9, R), (16.9, 1.06 * R),
                            (17.1, 1.06 * R), (17.1, R), (17.75, 0.97 * R)],
             [INTAKE, INTAKE, NACELLE, NACELLE, DEEP, NACELLE, NACELLE], cap0=False, cap1=False)
        # Intake mouth: a dark recess in the cowl's lip.
        tube(P, x, N["z"], [(N["r0"], 0.5 * R), (N["r0"] + 0.18, 0.32 * R)], INTAKE, cap0=False, cap1=True)
        # Nozzle: flared petals ring, its inside dark, a glowing disc deep in it.
        tube(P, x, N["z"], [(17.75, 0.97 * R), (17.85, 1.02 * R), (N["r1"], 0.9 * R), (N["r1"], 0.66 * R),
                            (N["r1"] - 0.3, 0.6 * R)], [NOZZLE, NOZZLE, NOZZLE, DEEP], cap0=False, cap1=False)
        tube(P, x, N["z"], [(N["r1"] - 0.32, 0.6 * R), (N["r1"] - 0.3, 0.6 * R)], NOZ_GLOW, cap0=False, cap1=True)
        # A pylon fairing joining the nacelle to the deck (hides the seam).
        hull(P, [(x + dx, 14 - r, z) for dx in (-0.35, 0.35) for r in (16.0, 17.6)
                 for z in (top_z(abs(x) + dx * s, r) - 0.2, N["z"])], NACELLE)


def build_cannons(P):
    """Twin cannons in the LERX roots: under the wing, so only their muzzles show from the front."""
    for s in (-1, 1):
        tube(P, s * 3.45, 0.42, [(11.75, 0.16), (11.95, 0.2), (12.4, 0.22), (14.2, 0.26)], CANNON, n=10)
        tube(P, s * 3.45, 0.42, [(11.75, 0.1), (11.85, 0.06)], DEEP, n=10, cap0=False)


# --- the flame (per frame, emissive) ------------------------------------------------------------

def build_flame(f, coll, sprite):
    F = FLAME[f]
    hw = ST(F["hw"])
    r0, r1 = F["hw"][0][0], F["hw"][-1][0]
    outer = Part(f"{TAG}_flame_{f}", smooth_angle=80)
    core = Part(f"{TAG}_flame_core_{f}", smooth_angle=80)
    n = 12
    rings, crings = [], []
    steps = 10
    for i in range(steps + 1):
        r = r0 + (r1 - r0) * i / steps
        h = max(0.02, hw(r))
        y = 14 - r
        rings.append([outer.v((h * math.cos(2 * math.pi * k / n), y,
                               NAC["z"] - 0.05 + (0.12 + min(0.5, 0.26 * h)) * math.sin(2 * math.pi * k / n))) for k in range(n)])
        hc = max(0.015, 0.55 * hw(r0 + (r - r0) * 1.1))
        crings.append([core.v((hc * math.cos(2 * math.pi * k / 8), y,
                               NAC["z"] + 0.02 + min(0.75, 0.55 * hc + 0.18) * math.sin(2 * math.pi * k / 8)))
                       for k in range(8)])
    for part, rr, m in ((outer, rings, 0), (core, crings, 0)):
        for i in range(len(rr) - 1):
            a, b = rr[i], rr[i + 1]
            nn = len(a)
            for k in range(nn):
                j = (k + 1) % nn
                part.f((a[k], a[j], b[j], b[k]), m, away=(0.0, (a[0].co.y + b[0].co.y) / 2, NAC["z"]))
        part.f(rr[0], m, out=(0, 1, 0))
        part.f(rr[-1], m, out=(0, -1, 0))
    rgb = lambda i: common.srgb(*sprite["colors"][str(i)])
    mo = common.material(f"pal_{F['pal']}_{TAG}_flame_{f}", rgb(F["pal"]), roughness=0.6, emission=rgb(F["pal"]),
                         emission_strength=1.0)
    mc = common.material(f"pal_{F['core']}_{TAG}_flame_core_{f}", rgb(F["core"]), roughness=0.6,
                         emission=rgb(F["core"]), emission_strength=1.05)
    objs = [finish(outer, [mo], coll), finish(core, [mc], coll)]
    for o in objs:
        common.frame_part(o, [f])
    return objs


# --- mesh building --------------------------------------------------------------------------------

def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, PX, 0, 0), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def build(coll, mats):
    H = Part(f"{TAG}_hull", smooth_angle=38)
    build_hull(H)
    D = Part(f"{TAG}_details", smooth_angle=35)
    build_plates(D)
    build_spine(D)
    build_nacelles(D)
    build_cannons(D)
    G = Part(f"{TAG}_glass", smooth_angle=70)
    F = Part(f"{TAG}_frame", smooth_angle=40)
    build_canopy(G, F)
    objs = [finish(p, mats, coll) for p in (H, D, G, F)]
    for o in objs:
        print("warfly part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# --- texture: baked occlusion and edge wear (as ship-u-ship.py's, copied: no shared edits) -------

def bake_maps(obj, out_dir, size=512, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{TAG}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size // 2, size // 2, alpha=False)
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
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.1
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
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
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, TINT[k]), comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
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
    for o in list(bpy.data.objects):  # the factory scene's cube, camera and light
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    objs = build(coll, mats)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    flames = build_flame(87, coll, sprite) + build_flame(89, coll, sprite)
    ftris = sum(len(p.vertices) - 2 for o in flames for p in o.data.polygons)
    print(f"warfly: hull {tris} triangles, flames {ftris}")
    # Menu engine glow behind the nozzles (glTF axes x, y up, z aft), as the ships carry.
    obj["tyrian_engines"] = {"color": "#ff6a1a", "at": [[round((s * NAC["x"] + 0.5) * PX, 4), round(NAC["z"] * PX, 4),
                                                         round((NAC["r1"] + 0.3 - 14) * PX, 4)] for s in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="warfly_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=1500, inside=0.003)
    print(f"warfly: outline shell {len(shell.data.polygons)} faces")
    common.export_sprite_model(ROOT, [obj, shell] + flames, MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj, shell] + flames, argv[argv.index("--preview") + 1], ref, size=frame["size"])


if __name__ == "__main__":
    main()
