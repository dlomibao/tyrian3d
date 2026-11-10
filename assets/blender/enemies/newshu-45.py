"""Purple pod with twin burners (newshu.shp frames 45, 47, 49, 51), a hard-surface 3D
version of its sprite.

Seen in episode 1 and episode 3. The sprite (24 x 28, nose at the bottom, so the burners at the top
are its tail) reads as:
  hull      a broad rounded pod, rows 11-26, widest (inner half width 10 px) on rows 15-20, coming
            to a blunt nose at row 26, narrower (half width 7) at its shoulders on rows 12-13 and 5
            on row 11 where it meets the engines. Purple 86 (shading 83-85 and sheen 88-90 are
            lighting). A belt groove runs round its waist and two transverse panel lines cross it.
  shoulders two lamp pods at the shoulders (rows 11-13, columns 4-6 / 17-19), their pink 73 / 70
            lenses on the rear (row 12) -> pink 73 lenses on purple pods.
  dome      a pale dome (89-95, median 92) on rows 11-13 centred on the spine, with a red lamp at
            its front (row 13, columns 11-12): dark (1) on frame 45, 114 on the others.
  slits     two glowing vent slots across the back, row 15 (x -2..2) and row 17 (x -3..3), in bezels;
            their ends dark on frame 45 and lit on the others, brightening frame by frame.
  trench    a recessed trench down the nose (rows 19-25, x -3..3, dark 82 / 81 walls) holding two
            gun barrels (columns 10 and 13, red 73 / 71 / 69 -> 71) on an 83 floor, a dark-red 66
            block between their muzzles and a dark 96 port at the nose tip.
  engines   two pink 72 nozzle bells (rows 9-10, columns 8-10 / 13-15) facing the tail, each in a
            dark 82 trough (thin side walls at columns 7 / 11 and 12 / 16, a floor and a crossbar at
            row 5): the sprite draws the housing in its ink colour, so the walls are thin plates on
            the ink line and the game's outline gives the dark frame.
  flames    per frame (common.frame_part): two tongues fitted to each frame's flame pixels row by
            row (each row's run of 112-122 pixels in that half), an emissive sheath (the tongue's
            median index) with a brighter core ridge (the core column's median), and the side licks
            of frames 49 / 51 as thin branches peeling off the tongues.

Units: sprite px, X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12 (usp_talon.finish).
Underside: a plain closed elliptic belly. No bake (no textures folder; at 22 px the maps would not
show). Outline shell of the static body (D51); the flames have none (the shell switches the model's
own outline off, so they glow without ink).

Run: blender --background --python assets/blender/enemies/newshu-45.py (tools/build-models.sh)
"""

import math
import statistics
import sys
from pathlib import Path

import bmesh
import bpy

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshu-45"
MODEL = f"enemies/{NAME}"
FRAMES = (45, 47, 49, 51)

# --- hull tables (sprite px; y = sprite row edge, x centred on the sprite's axis, z up) ------------
# Half width: at each row centre the inner mask's half width (rows 11: 5, 12-13: 7 with the lamp
# pods, 14: 9, 15-20: 10, 21: 9, 22: 8, 23: 6, 24: 5, 25: 3, 26: 1).
W_TAB = [(10.0, 3.1), (10.2, 3.7), (10.5, 4.05), (11.5, 5.05), (12.5, 5.95), (13.5, 7.15), (14.5, 9.2),
         (15.5, 10.0), (16.5, 10.15), (18.0, 10.2), (19.5, 10.15), (20.5, 10.0), (21.5, 9.1), (22.5, 8.05),
         (23.5, 6.3), (24.5, 4.85), (25.5, 3.05), (26.3, 1.55), (26.8, 0.55), (27.05, 0.15)]
ZT_TAB = [(10.0, 2.0), (10.5, 2.5), (11.5, 3.1), (12.5, 3.55), (13.5, 3.95), (15.0, 4.4), (17.0, 4.6),
          (19.0, 4.55), (21.0, 4.2), (22.5, 3.7), (24.0, 2.9), (25.5, 2.0), (26.5, 1.3), (27.05, 0.9)]
ZB_TAB = [(10.0, -0.6), (10.5, -1.0), (12.0, -1.6), (15.0, -2.0), (20.0, -2.0), (23.0, -1.6), (25.0, -1.0),
          (27.05, -0.2)]
# Trench depth down the nose.
TD_TAB = [(10.0, 0.0), (18.9, 0.0), (19.5, 0.95), (20.5, 1.1), (25.5, 1.1), (27.05, 0.8)]
ZC = 0.45          # waist (belt) height
BELT = 0.3         # half height of the belt band
GROOVE = 0.26      # belt groove depth
P_TOP = 2.3        # superellipse exponent of the upper hull
TW = 3.0           # trench half width at its rim
TWALL = 0.95       # trench wall run (rim to floor edge), covers columns 9 and 14
ZN = 0.9           # nozzle / flame axis height
NOZ_X = 2.5        # nozzle centres (columns 8-10 and 13-15)

Wf = T.pchip(*zip(*W_TAB))
ZTf = T.pchip(*zip(*ZT_TAB))
ZBf = T.pchip(*zip(*ZB_TAB))
TDf = T.pchip(*zip(*TD_TAB))


def top(x, y):
    """Height of the (untrenched) upper hull at x, y."""
    w, zt = Wf(y), ZTf(y)
    zu = ZC + BELT
    u = min(1.0, abs(x) / w)
    return zu + (zt - zu) * (1 - u ** P_TOP) ** (1 / P_TOP)


def trench_w(y):
    return min(TW, 0.74 * Wf(y))


def floor_z(x, y):
    return top(x, y) - TDf(y)


# --- materials --------------------------------------------------------------------------------------
(HULL, DARKLINE, TWALLM, DOME, LENS, NOZ, NOZIN, HOUS, RAIL, BLOCK, PORT, LAMP, SLIT_END, SLIT_CORE,
 SLIT_HOT, NOZGLOW, BEZEL) = range(17)


def static_materials(sprite):
    pal = lambda i, tag=NAME, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(86, metallic=0.4, roughness=0.42),                      # hull purple
        pal(83, metallic=0.3, roughness=0.6),                       # panel lines, trench floor
        pal(82, metallic=0.3, roughness=0.6),                       # trench walls
        pal(92, metallic=0.15, roughness=0.2),                      # pale dome
        pal(71, metallic=0.35, roughness=0.3, emission_strength=0.8),  # shoulder lenses (70 / 73 -> 71)
        pal(72, metallic=0.45, roughness=0.38),                     # nozzle bells
        pal(65, metallic=0.2, roughness=0.7),                       # nozzle bores
        pal(82, metallic=0.35, roughness=0.5),                      # burner housing (same index)
        pal(71, metallic=0.45, roughness=0.38),                     # gun barrels
        pal(66, metallic=0.3, roughness=0.55),                      # block between the muzzles
        pal(96, metallic=0.1, roughness=0.8),                       # nose port, bores
        common.palette_material(sprite, 114, f"{NAME}-lamp", emission_strength=3.0, frames={45: 1}),
        common.palette_material(sprite, 114, f"{NAME}-slitend", emission_strength=3.0,
                                frames={45: 1, 49: 116, 51: 118}),
        common.palette_material(sprite, 114, f"{NAME}-slitcore", emission_strength=3.2,
                                frames={47: 115, 49: 117, 51: 121}),
        common.palette_material(sprite, 116, f"{NAME}-slithot", emission_strength=3.5,
                                frames={49: 118, 51: 122}),
        common.palette_material(sprite, 117, f"{NAME}-nozglow", emission_strength=3.5),
        pal(85, metallic=0.4, roughness=0.4),                       # dome bezel, vent bezels
    ]


# --- geometry helpers (Part in sprite px) -------------------------------------------------------------

def ring_faces(part, a, b, mat, centre=None, out=None, ccw=False):
    """Quads between two rings. ccw: the rings run counter-clockwise in (x, z) seen from +y, so each
    face's outward normal is its loop tangent turned clockwise (works for concave loops too)."""
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        m = mat[i] if isinstance(mat, list) else mat
        if ccw:
            tx, tz = a[j].co.x - a[i].co.x + b[j].co.x - b[i].co.x, a[j].co.z - a[i].co.z + b[j].co.z - b[i].co.z
            part.f((a[i], a[j], b[j], b[i]), m, out=(tz, 0.0, -tx))
        elif out is not None:
            part.f((a[i], a[j], b[j], b[i]), m, out=out)
        else:
            part.f((a[i], a[j], b[j], b[i]), m, away=centre)


def hull_section(y, inset=0.0):
    """The hull's section loop at row y as [(x, z)] and per-segment material ids. A belt groove at
    the waist, a superellipse top with the nose trench cut in (depth TDf, zero aft of row 19), an
    elliptic belly. `inset` pulls the loop in (a transverse panel line's floor)."""
    w, zt, zb, td = Wf(y), ZTf(y), ZBf(y), TDf(y)
    zu, zl = ZC + BELT, ZC - BELT
    tw = trench_w(y)
    fw = max(tw - TWALL, 0.3)
    trench = td > 0.03
    pts, mats = [], []

    def add(p, m):
        pts.append(p)
        mats.append(m)

    # right waist: belt band with its groove
    add((w, zl), HULL)
    add((w - GROOVE, zl + 0.08), DARKLINE)
    add((w - GROOVE, zu - 0.08), DARKLINE)
    add((w, zu), HULL)
    # right upper surface, chine to the trench rim
    a_end = math.acos(min(1.0, ((tw + 0.35) / w)) ** (P_TOP / 2))
    ups = []
    for i in range(1, 7):
        a = a_end * i / 6
        x = w * math.cos(a) ** (2 / P_TOP)
        ups.append((x, top(x, y)))
    for p in ups:
        add(p, HULL)
    # trench (or the plain dome where td is 0): rim, wall, curved floor
    add((tw, top(tw, y) + (0.12 if trench else 0.0)), TWALLM if trench else HULL)
    add((fw, floor_z(fw, y)), DARKLINE if trench else HULL)
    add((fw * 0.5, floor_z(fw * 0.5, y)), DARKLINE if trench else HULL)
    add((0.0, floor_z(0.0, y)), DARKLINE if trench else HULL)
    add((-fw * 0.5, floor_z(fw * 0.5, y)), DARKLINE if trench else HULL)
    add((-fw, floor_z(fw, y)), TWALLM if trench else HULL)
    add((-tw, top(tw, y) + (0.12 if trench else 0.0)), HULL)
    for x, z in reversed(ups):
        add((-x, z), HULL)
    add((-w, zu), DARKLINE)
    add((-w + GROOVE, zu - 0.08), DARKLINE)
    add((-w + GROOVE, zl + 0.08), DARKLINE)
    add((-w, zl), HULL)
    # belly, left to right (ellipse)
    for i in range(1, 8):
        a = math.pi + math.pi * i / 8
        add((w * math.cos(a), zl + (zl - zb) * math.sin(a)), HULL)
    if inset:
        cx = 0.0
        cz = (zt + zb) / 2
        vn, _ = T.offset_loop(pts, (cx, cz))
        pts = [(x - nx * inset, z - nz * inset) for (x, z), (nx, nz) in zip(pts, vn)]
    return pts, mats


def section_mats(trench):
    """Material of each segment of hull_section's loop (34 points): belt groove dark, trench walls
    and floor only where the trench is, the rest hull."""
    m = [HULL] * 34
    for i in (0, 1, 2, 23, 24, 25):
        m[i] = DARKLINE
    if trench:
        m[10] = m[15] = TWALLM
        for i in (11, 12, 13, 14):
            m[i] = DARKLINE
    return m


def build_hull(part):
    """Loft the hull through stations; transverse panel lines (rings stepped in) at two rows."""
    ys = [10.0, 10.15, 10.4, 10.8, 11.3, 11.8, 12.4, 13.0, 13.5, 14.0, 14.5, 15.0, 15.6, 16.4, 17.3, 18.2,
          18.9, 19.2, 19.5, 20.2, 21.0, 21.8, 22.6, 23.4, 24.2, 24.9, 25.5, 26.0, 26.4, 26.75, 27.05]
    lines = (14.25, 21.3)
    stations = [(y, 0.0, 0) for y in ys]
    for yl in lines:
        stations += [(yl, 0.0, 0), (yl, 0.2, 1), (yl + 0.3, 0.2, 0), (yl + 0.3, 0.0, 1)]
    stations.sort(key=lambda s: (round(s[0], 6), s[2]))
    rings = []
    for y, ins, _ in stations:
        pts, _m = hull_section(y, ins)
        vs = [part.v((x, y, z)) for x, z in pts]
        rings.append((vs, y, ins, (0.0, y, (ZTf(y) + ZBf(y)) / 2)))
    for (a, ya, ia, ca), (b, yb, ib, cb) in zip(rings, rings[1:]):
        if abs(yb - ya) < 1e-9:
            ring_faces(part, a, b, DARKLINE, out=(0, 1, 0) if ib > ia else (0, -1, 0))
        elif ia > 0 and ib > 0:
            ring_faces(part, a, b, DARKLINE, ccw=True)
        else:
            ring_faces(part, a, b, section_mats(max(TDf(ya), TDf(yb)) > 0.03), ccw=True)
    part.f(rings[0][0], HULL, out=(0, -1, 0))
    part.f(rings[-1][0], HULL, out=(0, 1, 0))


def lathe(part, prof, cx, mats, zfun, sides=16):
    """Revolve a closed profile [(y, r)] round an axis along y at x = cx, z = zfun(y). mats[i] is the
    material of segment i -> i + 1 (wrapping). Normals from the profile's winding."""
    area = sum(y0 * r1 - y1 * r0 for (y0, r0), (y1, r1) in zip(prof, prof[1:] + prof[:1]))
    sgn = 1 if area < 0 else -1
    rings = []
    for y, r in prof:
        cz = zfun(y)
        rings.append([part.v((cx + r * math.cos(2 * math.pi * k / sides), y,
                              cz + r * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        (y0, r0), (y1, r1) = prof[i], prof[j]
        ny, nr = sgn * (r1 - r0), -sgn * (y1 - y0)
        for k in range(sides):
            kk = (k + 1) % sides
            t = 2 * math.pi * (k + 0.5) / sides
            out = (nr * math.cos(t), ny, nr * math.sin(t))
            part.f((rings[i][k], rings[i][kk], rings[j][kk], rings[j][k]), mats[i % len(mats)], out=out)


def ellipsoid(part, c, r, mat, nu=16, nv=8, zmin=None):
    """An ellipsoid (closed), optionally cut flat at z = zmin."""
    cx, cy, cz = c
    rx, ry, rz = r
    rings = []
    for j in range(1, nv):
        v = -math.pi / 2 + math.pi * j / nv
        ring = []
        for i in range(nu):
            u = 2 * math.pi * i / nu
            z = cz + rz * math.sin(v)
            if zmin is not None:
                z = max(z, zmin)
            ring.append(part.v((cx + rx * math.cos(v) * math.cos(u), cy + ry * math.cos(v) * math.sin(u), z)))
        rings.append(ring)
    bot = part.v((cx, cy, cz - rz if zmin is None else max(cz - rz, zmin)))
    topv = part.v((cx, cy, cz + rz))
    for a, b in zip(rings, rings[1:]):
        ring_faces(part, a, b, mat, centre=c)
    for i in range(nu):
        k = (i + 1) % nu
        part.f((rings[0][k], rings[0][i], bot), mat, away=c)
        part.f((rings[-1][i], rings[-1][k], topv), mat, away=c)


def sheared_box(part, x0, x1, y0, y1, z0, z1, ch, mat, slope=0.0, chz=None):
    """A chamfered box, its z sheared by `slope` per px of y (to follow the nose's fall)."""
    pts = [(x, y, z + slope * (y - y0)) for x, y, z in T.cbox(x0, x1, y0, y1, z0, z1, ch, chz)]
    T.hull(part, pts, mat)


def ell_loft(part, stations, mat, sides=10, cap=True):
    """Loft elliptic sections [(y, xc, hw, zc, hz)]; closes small ends with a cap."""
    rings = []
    for y, xc, hw, zc, hz in stations:
        rings.append(([part.v((xc + max(hw, 0.02) * math.cos(2 * math.pi * k / sides), y,
                               zc + max(hz, 0.02) * math.sin(2 * math.pi * k / sides))) for k in range(sides)],
                      (xc, y, zc)))
    for (a, ca), (b, cb) in zip(rings, rings[1:]):
        ring_faces(part, a, b, mat, centre=ca)
    if cap:
        part.f(rings[0][0], mat, out=(0, -1 if stations[0][0] < stations[-1][0] else 1, 0))
        part.f(rings[-1][0], mat, out=(0, 1 if stations[0][0] < stations[-1][0] else -1, 0))


# --- the static body -------------------------------------------------------------------------------

def build_body(sprite, mats, coll):
    part = T.Part(f"{NAME}", smooth_angle=34.0)
    build_hull(part)

    # Shoulder lamp pods (rows 11.8-14.4 at x +-5.95) with pink lenses on their rear tops.
    for s in (-1, 1):
        xc = s * 5.95
        st = []
        for y, k in ((11.75, 0.35), (11.95, 0.75), (12.3, 0.95), (12.9, 1.0), (13.6, 0.97), (14.2, 0.85),
                     (14.6, 0.5)):
            st.append((y, xc, 1.1 * k, 1.55, 1.05 * k))
        ell_loft(part, st, HULL, sides=10)
        ellipsoid(part, (s * 5.95, 12.45, 2.15), (0.95, 0.62, 0.55), LENS, nu=12, nv=6)

    # Dome with a bezel ring, and the lamp at its front.
    zb = ZTf(12.55) - 0.25
    ellipsoid(part, (0.0, 12.6, zb), (3.45, 1.85, 0.42), BEZEL, nu=20, nv=5)
    ellipsoid(part, (0.0, 12.55, zb + 0.1), (3.0, 1.55, 1.45), DOME, nu=20, nv=8, zmin=zb - 0.2)
    ellipsoid(part, (0.0, 13.55, zb + 0.95), (1.0, 0.55, 0.42), LAMP, nu=12, nv=6)

    # Vent slots across the back: bezel (raised frame) and emissive inserts in segments.
    for row, segs in ((15, ((-2, -1, SLIT_END), (-1, 1, SLIT_CORE), (1, 2, SLIT_END))),
                      (17, ((-3, -2, SLIT_END), (-2, -1, SLIT_CORE), (-1, 1, SLIT_HOT), (1, 2, SLIT_CORE),
                            (2, 3, SLIT_END)))):
        x0, x1 = segs[0][0], segs[-1][1]
        zs = top(0.0, row + 0.5)
        ze = top(x1, row + 0.5)
        sheared_box(part, x0 - 0.25, x1 + 0.25, row - 0.22, row + 1.22, ze - 0.9, zs + 0.2, 0.12, BEZEL)
        for a, b, m in segs:
            zt = max(top(a, row + 0.5), top(b, row + 0.5)) + 0.26
            sheared_box(part, a + 0.03, b - 0.03, row + 0.06, row + 0.94, zt - 0.8, zt, 0.08, m)

    # Nose trench contents: two barrels, the block between the muzzles, the nose port.
    for s in (-1, 1):
        xc = s * 1.5
        zf = lambda y, xc=xc: floor_z(abs(xc), y) + 0.52  # noqa: E731
        prof = [(19.35, 0.05), (19.35, 0.5), (19.7, 0.56), (20.3, 0.56), (20.45, 0.46), (23.85, 0.44),
                (23.95, 0.52), (24.55, 0.52), (24.6, 0.3), (24.4, 0.22), (24.4, 0.05)]
        lathe(part, prof, xc, [RAIL] * 7 + [PORT, PORT, PORT, RAIL], zf, sides=12)
    zf0 = floor_z(0.0, 21.8)
    sheared_box(part, -0.95, 0.95, 21.8, 24.0, zf0 - 0.3, zf0 + 0.75, 0.15, BLOCK,
                slope=(floor_z(0.0, 24.0) - zf0) / 2.2)
    zp = floor_z(0.0, 24.0)
    sheared_box(part, -1.0, 1.0, 23.95, 25.9, zp - 0.9, zp + 0.25, 0.15, PORT,
                slope=(floor_z(0.0, 25.9) - zp) / 1.95)

    # Engines: nozzle bells facing the tail, bores dark, a glow at the bottom of each bore.
    for s in (-1, 1):
        xc = s * NOZ_X
        prof = [(11.3, 1.2), (10.4, 1.38), (9.6, 1.5), (9.1, 1.5), (8.95, 1.42), (8.95, 1.12), (9.5, 0.98),
                (9.85, 0.9), (9.85, 0.05), (11.3, 0.05)]
        lathe(part, prof, xc, [NOZ, NOZ, NOZ, NOZ, NOZ, NOZIN, NOZIN, NOZGLOW, NOZ, NOZ], lambda y: ZN, sides=14)
        # bell reinforcing ring
        lathe(part, [(10.15, 1.36), (9.75, 1.58), (9.45, 1.58), (9.35, 1.45), (10.15, 1.2)], xc,
              [NOZ], lambda y: ZN, sides=14)
        # trough: outer and inner walls (thin, on the sprite's ink lines), floor
        xo, xi = s * 4.1, s * 0.85
        for xw in (xo, xi):
            T.hull(part, T.cbox(xw - 0.2, xw + 0.2, 5.75, 9.9, ZN - 1.75, ZN + 1.15, 0.08), HOUS)
        a, b = sorted((xo, xi))
        T.hull(part, T.cbox(a, b, 5.75, 10.2, ZN - 1.75, ZN - 1.4, 0.08), HOUS)
    # crossbar at the tail (row 5), low under the flames
    T.hull(part, T.cbox(-4.3, 4.3, 5.75, 6.15, ZN - 1.75, ZN - 0.85, 0.1), HOUS)
    # a mounting yoke between the bells and the hull's rear face
    T.hull(part, T.cbox(-1.0, 1.0, 9.9, 10.6, ZN - 1.2, ZN + 0.9, 0.18), HOUS)

    obj = T.finish(part, mats, coll)
    return obj


# --- flames -----------------------------------------------------------------------------------------

def runs(cols):
    out = []
    for c in sorted(cols):
        if out and c == out[-1][1] + 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return out


def flame_fit(pix, side):
    """One side's tongue and licks from a frame's pixels. Returns (stations [(y_row, x0, x1)] from row
    8 up, lick strands [[(row, col), ...]], sheath pixels, core pixels)."""
    core_c = 9 if side < 0 else 14
    half = (lambda c: c <= 11) if side < 0 else (lambda c: c >= 12)
    rows = {}
    for r in range(0, 9):
        cols = [c for c in range(24) if half(c) and 112 <= pix[r][c] <= 122]
        if cols:
            rows[r] = runs(cols)
    main, licks, prev = [], [], None
    sheath, core = [], []
    for r in range(8, -1, -1):
        if r not in rows:
            if main:
                break
            continue
        rr = rows[r]
        pick = [g for g in rr if g[0] <= core_c <= g[1]]
        if not pick and prev:
            pick = [g for g in rr if g[0] <= prev[1] + 1 and g[1] >= prev[0] - 1]
        if not pick:
            break
        g = min(pick, key=lambda g: abs((g[0] + g[1]) / 2 - core_c))
        main.append((r, g[0], g[1]))
        sheath += [pix[r][c] for c in range(g[0], g[1] + 1)]
        if g[0] <= core_c <= g[1]:
            core.append(pix[r][core_c])
        for o in rr:
            if o is not g:
                licks += [(r, c) for c in range(o[0], o[1] + 1)]
        prev = g
    # rows above the tongue's tip: everything there is a lick
    top_row = main[-1][0] if main else 9
    for r, rr in rows.items():
        if r < top_row:
            licks += [(r, c) for g in rr for c in range(g[0], g[1] + 1)]
    # group licks (8-connected)
    strands, left = [], set(licks)
    while left:
        s = [left.pop()]
        i = 0
        while i < len(s):
            r, c = s[i]
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    q = (r + dr, c + dc)
                    if q in left:
                        left.remove(q)
                        s.append(q)
            i += 1
        strands.append(sorted(s, reverse=True))
    return main, strands, sheath, core


def nearest_index(sprite, v):
    keys = sorted(int(k) for k in sprite["colors"] if 112 <= int(k) <= 122)
    return min(keys, key=lambda k: abs(k - v))


def build_flames(sprite, frame_idx, pix, coll):
    part = T.Part(f"{NAME}-flame-{frame_idx}", smooth_angle=80.0)
    mats, mat_of = [], {}

    def mat(i, strength):
        if i not in mat_of:
            mat_of[i] = len(mats)
            mats.append(common.palette_material(sprite, i, f"{NAME}-flame", emission_strength=strength))
        return mat_of[i]

    report = {}
    for side in (-1, 1):
        main, strands, sheath, core = flame_fit(pix, side)
        if not main:
            continue
        sm = nearest_index(sprite, statistics.median_low(sorted(sheath)))
        cm = nearest_index(sprite, statistics.median_high(sorted(core[:3] if len(core) >= 3 else core)))
        cm = max(cm, sm + 1) if cm <= sm else cm
        report[side] = (sm, cm)
        base_y = 9.35
        tip_row = main[-1][0]
        tip_y = tip_row + 0.32
        # stations from the nozzle out: (y, xc, hw)
        st = [(base_y, None, None)]
        for r, c0, c1 in main:
            xc = (c0 + c1 + 1) / 2 - 12
            hw = (c1 - c0 + 1) / 2 - 0.06
            st.append((r + 0.5, xc, hw))
        st[0] = (base_y, st[1][1] * 0.6 + side * NOZ_X * 0.4, min(st[1][2], 1.1))
        ys = [s[0] for s in st][::-1]
        xf = T.pchip(ys, [s[1] for s in st][::-1])
        wf = T.pchip(ys, [s[2] for s in st][::-1])
        length = base_y - tip_y
        rise = 0.7

        def zc(y):
            return ZN + rise * (base_y - y) / length

        samples = []
        y = base_y
        while y > tip_row + 0.5:
            samples.append(y)
            y -= 0.42
        samples.append(tip_row + 0.5)
        stations = []
        for y in samples:
            hw = wf(y)
            stations.append((y, xf(y), hw, zc(y), 0.62 * hw + 0.18))
        # taper from the top row's centre to the tip
        hw_top = wf(tip_row + 0.5)
        x_top = xf(tip_row + 0.5)
        for t in (0.45, 0.8, 1.0):
            yy = tip_row + 0.5 - (tip_row + 0.5 - tip_y) * t
            k = (1 - t) ** 0.8
            stations.append((yy, x_top, max(hw_top * k, 0.03), zc(yy), max((0.62 * hw_top + 0.18) * k, 0.03)))
        ell_loft(part, stations, mat(sm, 3.5), sides=9)
        # core ridge: narrower, riding higher so it shows down the tongue's middle
        cst = []
        for y, xc, hw, z, hz in stations:
            frac = (base_y - y) / length
            if frac > 0.78:
                break
            k = 1.0 if frac < 0.55 else max(0.05, 1 - (frac - 0.55) / 0.23)
            cst.append((y, xc + (side * NOZ_X - xc) * 0.15, 0.48 * min(hw, 1.6) * k, z + 0.5 * hz,
                        0.62 * hz * k))
        if len(cst) >= 2:
            ell_loft(part, cst, mat(cm, 4.5), sides=7)
        # licks: thin branches from the tongue's base region out along their pixels
        for s in strands:
            lm = nearest_index(sprite, statistics.median_low(sorted(pix[r][c] for r, c in s)))
            pts = sorted(s, reverse=True)  # bottom first
            # one point per row (mean column)
            byrow = {}
            for r, c in pts:
                byrow.setdefault(r, []).append(c)
            rws = sorted(byrow, reverse=True)
            path = [(r + 0.5, sum(byrow[r]) / len(byrow[r]) + 0.5 - 12) for r in rws]
            # root: on the tongue one row below the lick's lowest pixel
            r0 = min(rws[0] + 1.5, base_y - 0.3)
            root = (r0, xf(r0) + side * 0.4 * wf(r0))
            path = [root] + path
            tip = (rws[-1] + 0.3, path[-1][1])
            path.append(tip)
            n = len(path)
            lst = []
            for i, (y, x) in enumerate(path):
                f = i / (n - 1)
                hw = 0.36 * (1 - f) ** 0.7 + 0.02
                lst.append((y, x, hw, zc(min(max(y, tip_y), base_y)) + 0.2 * f, hw * 0.9))
            ell_loft(part, lst, mat(max(lm, 113), 3.0), sides=6)
    obj = T.finish(part, mats, coll)
    common.frame_part(obj, [frame_idx])
    return obj, report


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = static_materials(sprite)
    body = build_body(sprite, mats, coll)
    print(f"body: {sum(len(p.vertices) - 2 for p in body.data.polygons)} triangles")
    objs = [body]
    for fr in sprite["frames"]:
        f, rep = build_flames(sprite, fr["index"], fr["pixels"], coll)
        print(f"flames {fr['index']}: {sum(len(p.vertices) - 2 for p in f.data.polygons)} triangles, "
              f"sheath/core {rep}")
        f.parent = body
        objs.append(f)
    shell = common.outline_shell(body, coll, voxel=0.012, faces=3000, inside=0.004)
    shell.parent = body
    objs.append(shell)
    common.export_sprite_model(WT, objs, MODEL, sprite["sprites"])


if __name__ == "__main__":
    main()
