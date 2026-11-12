"""Green dome generator (newshj.shp, assembly-newshj-51): design A, engineering first.

WHAT IT IS: a standing machine. A lens-shaped platform (a round deck on a short wall over a conical
skirt and a small sole) carries a fluted column; on the column sits a hopper-shaped head with three
pale glossy domes on its lid, a dark louvred grille on its front, two hanging struts at its chin, a
red yoke clamp each side of the column top, and on each flank a vertical canister pod with a red
cap, a red cup under it and a red J-bracket (with a yellow lamp) that hangs from the pod and curls
in under the head to carry it.

The sprite is this machine drawn the way Tyrian draws tall things (D82, D161): an orthographic camera
from the south, E = 15 deg up, so a model point (u, v, z) lands on screen row
    s = VB + sin(E) (v - VB) - cos(E) z         (u = sprite column edge, v = plan row south +)
Every round rim in the sprite is an ellipse about a quarter as tall as it is wide; the deck is a
full circle (r 21.5), the domes are round. Heights and plan positions below are solved from the
sprite rows they must land on (cross-sections first, then the art view).

Coordinates while building: sprite px, X = u east, Y = -v north, Z = up; the machine's axis stands
at (AX, VB) on the ground. The model is the true upright machine (D82 approach C, D165): the glbs
hold the four 24x28 pieces (newshj-13/15 head, 51/53 base), cut along the ART view's rows and
columns (tilted planes through the upright model) and re-centred about their own block centre, still
standing. Each piece and its outline shell (`tyrian_outline`) carry the D165 glTF extras read by
src/render/obliqueView.ts (origin/main 538a8fc2):
  tyrian_oblique    [cos E, sin E, axisZ]   axisZ = (VB - (r0 + 14)) * PX
  tyrian_depth_band [lo, hi, 0, ZTOP * PX]  BAND = (lo, hi), the same [y0, y1] on all four pieces
axisZ is the plan row of the machine's axis relative to the piece's block centre (glTF +z south);
it is the same convention as assembly-newshc-283.py art_view(), whose (VB - 42 - r0) carries that
script's +28 row offset. The renderer then draws a vertex (x, y up, z) at
(x, axisZ + sin E (z - axisZ) - cos E y), which is the screen-row formula above.

Depth band: the machines are event 49-52 enemies in slots 25-49 ("ground", BONUS/BOTANY) and 75-99
("ground2", TORM/BOTANY). JE_drawEnemy(50) and JE_drawEnemy(100) both draw in Pass.GroundEnemies
(0.45 units, src/render/passHeights.ts); background 2 mid is 0.9. BAND = (0, 0.35) keeps every
height within the brief's +-0.35 of that pass and 0.1 under background 2 mid, tighter than the
[0, 0.4] D165 shipped for DELIANI's towers (its [0, 0.8] poked through the layer above).

Colours: the sprite median per region (lighting excluded). pod_yoke and tie_rod use 33 although the
sprite median there is 1: index 1 is the near-black outline/shadow ink of those thin dark parts,
which is lighting, so the darkest body colour 33 is the deliberate choice, not a mismatch.

Run:
  python3 assembly-newshj-51.py                        # art-view IoU per piece + region colours
  tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshj-51.py
      (blender -b --python assembly-newshj-51.py -- [--views DIR] [--no-export])
Exports public/models/enemies/newshj-{13,15,51,53}.glb and their spriteModels entries.
"""

import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = Path("/Users/dlomibao/projects/tyrian-worktrees/e2-enemies-1")
NAME = "assembly-newshj-51"
FIN = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-1/assembly-newshj-51/final")
FIN.mkdir(parents=True, exist_ok=True)

E = 15.0
A, K = math.sin(math.radians(E)), math.cos(math.radians(E))
AX = 24.5          # mirror axis (column edge coordinate)
VB = 51.3          # plan row of the machine's axis on the ground
PX = 1.0 / 12.0
BAND = (0.0, 0.35)  # depth band (units above the base, D165): see the header
PIECES = {"newshj-13": (0, 0), "newshj-15": (24, 0), "newshj-51": (0, 28), "newshj-53": (24, 28)}

# Palette indices (sprite medians per region, lighting excluded)
P = dict(DECK=40, WALL=34, WALLB=37, CHAMF=38, SKIRT=33, PANEL=43, BOLT=42, HATCH=33, LENS=46,
         FOOT=41, SHAFT=42, RIB=42, BAND=41,
         HEAD=39, LID=40, LIP=36, GRILLE=33, SLAT=34, CHIN=41, LEG=36, REAR=38,
         DOME=45, DOMEC=44, BULK=41, DRING=43, POD=40, PODBAND=41,
         CAP=114, RED=114, YOKE=114, BOSS=119, PODLO=38, LAMP=124, HOOD=120)
EMIT = {124: 1.2, 120: 0.35}


def zrow(row, v_front):
    """Height at which a point at plan row v_front shows on screen row `row`."""
    return (VB + A * (v_front - VB) - row) / K


# ---------------------------------------------------------------------------------------------
# Geometry (pure Python, so it can be measured without Blender)
# ---------------------------------------------------------------------------------------------

class Geo:
    def __init__(self):
        self.v = []
        self.f = []      # (indices, pal, part)
        self.smooth = []

    def add_v(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def face(self, idx, pal, part, smooth=True):
        self.f.append((tuple(idx), pal, part))
        self.smooth.append(smooth)

    def loft(self, rings, pals, part, cap0=True, cap1=True, smooth=True):
        """rings: list of lists of 3D points (same count, CCW seen from +Z); pals[i] between ring i and i+1."""
        ids = [[self.add_v(p) for p in r] for r in rings]
        n = len(rings[0])
        for i in range(len(ids) - 1):
            pal = pals[i] if isinstance(pals, (list, tuple)) else pals
            a, b = ids[i], ids[i + 1]
            for j in range(n):
                k = (j + 1) % n
                self.face((a[j], a[k], b[k], b[j]), pal, part, smooth)
        p0 = pals[0] if isinstance(pals, (list, tuple)) else pals
        p1 = pals[-1] if isinstance(pals, (list, tuple)) else pals
        if cap0:
            self._cap(ids[0], p0, part, flip=True, smooth=smooth)
        if cap1:
            self._cap(ids[-1], p1, part, flip=False, smooth=smooth)

    def loft_open(self, rings, pal, part, smooth=False):
        """An open strip between polylines (no wrap), closed at its ends by fans to the first/last points."""
        ids = [[self.add_v(p) for p in r] for r in rings]
        n = len(rings[0])
        for i in range(len(ids) - 1):
            a, b = ids[i], ids[i + 1]
            for j in range(n - 1):
                self.face((a[j], a[j + 1], b[j + 1], b[j]), pal, part, smooth)
        for j in (0, n - 1):
            col = [r[j] for r in ids]
            self.face(tuple(col) if j else tuple(reversed(col)), pal, part, smooth)

    def _cap(self, ring, pal, part, flip, smooth):
        c = [sum(self.v[i][a] for i in ring) / len(ring) for a in range(3)]
        ci = self.add_v(c)
        n = len(ring)
        for j in range(n):
            k = (j + 1) % n
            tri = (ring[j], ring[k], ci) if not flip else (ring[k], ring[j], ci)
            self.face(tri, pal, part, smooth)


def oval_depth(r, dx):
    """Plan half-depth of the base's superellipse (radius r) at offset dx from the axis."""
    t = min(1.0, abs(dx) / r)
    return BASE_SY * r * (1 - t ** BASE_N) ** (1 / BASE_N)


def arc_pts(r, z, a0, a1, steps=14):
    """Points on the base's superellipse at radius r from angle a0 to a1 (deg), centre (AX, -VB)."""
    out = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        c, s_ = math.cos(a), math.sin(a)
        out.append((AX + r * sq(c, 2.0 / BASE_N), -VB + BASE_SY * r * sq(s_, 2.0 / BASE_N), z))
    return out


def sq(t, n):
    """Signed power for superellipses."""
    return math.copysign(abs(t) ** n, t)


def loop_oval(cx, cy, rx, ry, z, sides=48, n=2.0, phase=0.0):
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides + phase
        c, s = math.cos(a), math.sin(a)
        pts.append((cx + rx * sq(c, 2.0 / n), cy + ry * sq(s, 2.0 / n), z))
    return pts


def loop_rrect(cx, cy, hw, hd, rad, z, seg=4):
    """Rounded rectangle, CCW, starting at the east side."""
    rad = max(0.01, min(rad, hw - 0.01, hd - 0.01))
    pts = []
    for (qx, qy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (hw - rad), cy + qy * (hd - rad)
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / seg)
            pts.append((ox + rad * math.cos(a), oy + rad * math.sin(a), z))
    return pts


def lathe(g, cx, cy, prof, pals, part, sides=40, sy=1.0, n=2.0, cap0=True, cap1=True, phase=0.0, smooth=True):
    """Surface of revolution through prof [(r, z)] bottom to top (oval if sy != 1)."""
    rings = [loop_oval(cx, cy, r, r * sy, z, sides, n, phase) for r, z in prof]
    g.loft(rings, pals, part, cap0=cap0 and prof[0][0] > 1e-6, cap1=cap1 and prof[-1][0] > 1e-6, smooth=smooth)


def block(g, x0, x1, y0, y1, z0, z1, pal, part, ch=0.25):
    """A chamfered box (plan rounded-rect sections)."""
    cx, cy, hw, hd = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    ch = min(ch, hw * 0.45, hd * 0.45, (z1 - z0) * 0.45)
    rings = [loop_rrect(cx, cy, hw - ch, hd - ch, ch * 0.6, z0),
             loop_rrect(cx, cy, hw, hd, ch * 1.2, z0 + ch),
             loop_rrect(cx, cy, hw, hd, ch * 1.2, z1 - ch),
             loop_rrect(cx, cy, hw - ch, hd - ch, ch * 0.6, z1)]
    g.loft(rings, pal, part, smooth=False)


def frame_along(path):
    """Tangent, normal, binormal along a 3D polyline (rotation-minimising, start normal = +Y)."""
    out = []
    prev_n = None
    for i, p in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(len(path) - 1, i + 1)]
        t = [b[k] - a[k] for k in range(3)]
        ln = math.sqrt(sum(c * c for c in t)) or 1.0
        t = [c / ln for c in t]
        if prev_n is None:
            ref = [0.0, 1.0, 0.0]
        else:
            ref = prev_n
        d = sum(ref[k] * t[k] for k in range(3))
        nrm = [ref[k] - d * t[k] for k in range(3)]
        ln = math.sqrt(sum(c * c for c in nrm)) or 1.0
        nrm = [c / ln for c in nrm]
        bn = [t[1] * nrm[2] - t[2] * nrm[1], t[2] * nrm[0] - t[0] * nrm[2], t[0] * nrm[1] - t[1] * nrm[0]]
        out.append((t, nrm, bn))
        prev_n = nrm
    return out


def sweep(g, path, hw, hh, pal, part, rad=0.4, seg=3):
    """A rounded-rect tube (half sizes hw along the binormal, hh along the normal) along path."""
    fr = frame_along(path)
    base = loop_rrect(0.0, 0.0, hw, hh, rad, 0.0, seg)
    rings = []
    for p, (t, nrm, bn) in zip(path, fr):
        # section in the plane (bn, nrm); keep CCW looking along +t
        rings.append([tuple(p[k] + x * bn[k] + y * nrm[k] for k in range(3)) for x, y, _ in base])
    # orientation: loft assumes CCW looking down the axis of travel when travel is +Z
    g.loft(rings, pal, part, smooth=False)


def mirror(g, start, part_suffix=("_l", "_r")):
    """Mirror faces added since `start` about u = AX (new faces, reversed winding)."""
    n0 = len(g.f)
    vmap = {}
    for fi in range(start, n0):
        idx, pal, part = g.f[fi]
        new = []
        for i in idx:
            if i not in vmap:
                x, y, z = g.v[i]
                vmap[i] = g.add_v((2 * AX - x, y, z))
            new.append(vmap[i])
        g.face(tuple(reversed(new)), pal, part.replace(part_suffix[0], part_suffix[1]), g.smooth[fi])


# ---------------------------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------------------------

Y0 = -VB  # plan Y of the axis
BASE_SY, BASE_N = 0.8, 2.35


def build():
    g = Geo()
    cy = Y0

    # ---- BASE: a round deck on a short wall over a conical skirt (the lens), sole on the ground ----
    R = 21.5
    z_rim = zrow(44.8, VB)    # bottom of the wall at the deck's sides
    z_deck = zrow(40.5, VB)   # deck top at its sides (9.5)
    prof = [(0.0, 0.0), (3.5, 0.0), (4.3, 0.25), (20.6, z_rim - 0.55), (R, z_rim),
            (R, z_deck - 0.35), (R - 0.35, z_deck), (R - 1.6, z_deck + 0.05), (9.0, z_deck + 0.35), (7.2, z_deck + 0.4)]
    pals = [P["SKIRT"], P["SKIRT"], P["SKIRT"], P["WALL"], P["WALL"], P["CHAMF"], P["DECK"], P["DECK"], P["DECK"]]
    lathe(g, AX, cy, prof, pals, "base", sides=72, cap1=True, sy=BASE_SY, n=BASE_N)
    zd = z_deck + 0.05

    # deck rails and plates (left, mirrored): sprite cols 11-12 and 14 (rows 37-44), plate cols 3-10 rows 42-43,
    # pads cols 18-20 rows 42-45
    def deck_v(row, z):
        """plan v of a point on the deck at height z drawn on sprite row `row`"""
        return VB + (row - VB + K * z) / A
    s0 = len(g.f)
    zt = zd + 0.55
    for (u0, u1, r0, r1) in ((10.2, 12.95, 37.0, 44.6), (13.7, 15.4, 36.6, 45.2)):
        va, vb = deck_v(r0, zt), deck_v(r1, zt)
        lim = oval_depth(R - 1.6, AX - u0)
        va, vb = max(va, VB - lim), min(vb, VB + lim)
        block(g, u0, u1, -vb, -va, zd - 0.2, zt, P["PANEL"], "deck_rail_l", ch=0.2)
    va, vb = deck_v(41.9, zt), deck_v(43.9, zt)
    # pale trim band round the wall's side (sprite cols 3-10, rows 42-43): a partial ring, west arc
    zb0, zb1 = zrow(43.9, VB), zrow(42.1, VB)
    rings = []
    for z, grow in ((zb0, 0.0), (zb0 + 0.15, 0.3), (zb1 - 0.15, 0.3), (zb1, 0.0)):
        rings.append(arc_pts(R + grow, z, 180.0, 232.0))
    g.loft_open(rings, P["WALLB"], "wall_band_l")
    va, vb = deck_v(41.8, zt + 0.3), deck_v(45.6, zt + 0.3)
    lim = oval_depth(R - 1.2, AX - 18.0)
    block(g, 17.0, 21.0, -min(vb, VB + lim), -va, zd - 0.2, zt + 0.3, P["PANEL"], "deck_pad_l", ch=0.25)
    # deck bolts round the rim
    for ang in (200, 222, 244):
        a = math.radians(ang)
        bx, by = AX + (R - 2.6) * math.cos(a), cy + BASE_SY * (R - 2.6) * math.sin(a)
        lathe(g, bx, by, [(0.55, zd - 0.1), (0.55, zd + 0.3), (0.3, zd + 0.45)], P["BOLT"], "deck_bolt_l", sides=8)
    for ang in (150, 128):
        a = math.radians(ang)
        bx, by = AX + (R - 2.6) * math.cos(a), cy + BASE_SY * (R - 2.6) * math.sin(a)
        lathe(g, bx, by, [(0.55, zd - 0.1), (0.55, zd + 0.3), (0.3, zd + 0.45)], P["BOLT"], "deck_bolt_l", sides=8)
    mirror(g, s0)

    # front hatch on the skirt (cols 18-31 rows 48-50) with a pale lens at col 24 row 50
    hz0, hz1 = 1.6, z_rim - 0.2
    # skirt surface radius at height z: 8.4 + (20.6 - 8.4) * (z - 0.25) / (z_rim - 0.8)
    def skirt_r(z):
        return 4.3 + (20.6 - 4.3) * (z - 0.25) / (z_rim - 0.55 - 0.25)
    rings = []
    hs = 5.6
    for z in (hz0, (hz0 + hz1) / 2, hz1):
        r = skirt_r(z) + 0.35
        pts = []
        for i in range(9):
            x = AX + hs * (i / 8 * 2 - 1) * (r / skirt_r(hz1))
            dx = x - AX
            y = cy - BASE_SY * math.sqrt(max(0.0, r * r - dx * dx))
            pts.append((x, y, z))
        rings.append(pts)
    # hatch as a thin shell: outer surface + back at skirt
    hatch_outer = rings
    ids = [[g.add_v(p) for p in r] for r in hatch_outer]
    inner = [[g.add_v((p[0], p[1] + 0.6, p[2])) for p in r] for r in hatch_outer]
    for i in range(len(ids) - 1):
        for j in range(8):
            g.face((ids[i][j], ids[i + 1][j], ids[i + 1][j + 1], ids[i][j + 1]), P["HATCH"], "front_hatch", False)
            g.face((inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j], inner[i][j]), P["HATCH"], "front_hatch", False)
    for i in range(len(ids) - 1):
        for j in (0,):
            g.face((inner[i][j], inner[i + 1][j], ids[i + 1][j], ids[i][j]), P["HATCH"], "front_hatch", False)
        j = 8
        g.face((ids[i][j], ids[i + 1][j], inner[i + 1][j], inner[i][j]), P["HATCH"], "front_hatch", False)
    for j in range(8):
        g.face((ids[0][j], ids[0][j + 1], inner[0][j + 1], inner[0][j]), P["HATCH"], "front_hatch", False)
        g.face((ids[-1][j + 1], ids[-1][j], inner[-1][j], inner[-1][j + 1]), P["HATCH"], "front_hatch", False)
    # lens at the hatch's foot and a bar across its top
    zl = 2.2
    rl = skirt_r(zl) + 0.6
    g_y = cy - BASE_SY * rl
    lathe_pts = []
    rings = [loop_oval(AX, g_y, 0.95, 0.95, 0, 12)]
    # the lens: a short cylinder pointing south (built as a loft along -Y)
    lens = []
    for k, (rr, dy) in enumerate(((0.95, 0.0), (0.95, -0.45), (0.6, -0.75))):
        ring = []
        for i in range(12):
            a = 2 * math.pi * i / 12
            ring.append((AX + rr * math.cos(a), g_y + dy, zl + rr * math.sin(a)))
        lens.append(ring)
    # loft along -Y: rings CCW seen from -Y means reverse
    g.loft([list(reversed(r)) for r in lens], P["LENS"], "hatch_lens", smooth=True)

    # ---- COLUMN: flared fluted foot, ribbed neck, upper shaft into the head ----
    z_foot_top = zrow(32.0, VB - 4.2)          # back-top of the foot (r 4.2) on row 32
    z_neck_top = zrow(29.9, VB)          # front-bottom of the upper shaft on row 28.8
    z_head_bot = zrow(23.8, VB + 6.5)
    col = [(6.9, zd - 0.6), (6.9, zd + 0.3), (6.7, zd + 2.2), (6.2, zd + 4.6), (5.4, zd + 6.0), (4.6, zd + 6.7), (4.55, z_foot_top - 0.6),
           (4.55, z_foot_top - 0.4), (4.55, z_foot_top), (2.7, z_foot_top + 0.05), (2.6, z_foot_top + 0.4),
           (2.6, z_neck_top - 0.4), (2.7, z_neck_top - 0.05), (3.6, z_neck_top), (3.6, z_head_bot + 1.5)]
    cpal = [P["FOOT"], P["FOOT"], P["FOOT"], P["FOOT"], P["SHAFT"], P["SHAFT"], P["BAND"], P["BAND"], P["BAND"], P["SHAFT"],
            P["SHAFT"], P["SHAFT"], P["BAND"], P["SHAFT"]]
    lathe(g, AX, cy, col, cpal, "column_shaft", sides=48, phase=math.radians(3.75))
    # 12 flute ribs on the foot and on the upper shaft (rib tops pale), front rib pair at +-15 deg
    for k in range(12):
        a = math.radians(-90 + 15 + 30 * k)
        for seg_ in (((6.8, zd + 0.9), (6.7, zd + 2.2), (6.2, zd + 4.6), (5.4, zd + 6.0), (4.6, zd + 6.7),
                      (4.55, z_foot_top - 0.7)),
                     ((3.6, z_neck_top + 0.2), (3.6, z_head_bot + 1.2))):
            path = []
            for r, z in seg_:
                r = r + (0.12 if r > 4 else -0.2)
                path.append((AX + r * math.cos(a), cy + r * math.sin(a), z))
            # rib: thin box oriented radially, built as a sweep along +Z
            ca, sa = math.cos(a), math.sin(a)
            rings = []
            for (x, y, z) in path:
                pts = []
                for (dr, dt) in ((-0.45, -0.42), (0.25, -0.42), (0.45, -0.2), (0.45, 0.2), (0.25, 0.42), (-0.45, 0.42)):
                    pts.append((x + dr * ca - dt * sa, y + dr * sa + dt * ca, z))
                rings.append(pts)
            g.loft(rings, P["RIB"], "column_rib", smooth=False)
        # neck ribs (thin)
        r = 2.6 - 0.1
        rings = []
        for z in (z_foot_top + 0.5, z_neck_top - 0.5):
            x, y = AX + r * math.cos(a), cy + r * math.sin(a)
            ca, sa = math.cos(a), math.sin(a)
            rings.append([(x + dr * ca - dt * sa, y + dr * sa + dt * ca, z)
                          for dr, dt in ((-0.3, -0.3), (0.2, -0.3), (0.2, 0.3), (-0.3, 0.3))])
        g.loft(rings, P["RIB"], "column_rib", smooth=False)

    # ---- HEAD: a hopper, wide at the lid, tapering to the chin ----
    HD = 8.0             # half depth of the head (plan)
    z_hb = z_head_bot
    z_knee = zrow(20.5, VB + HD)
    z_top = zrow(15.2, VB + HD)
    hp = [(11.5, 6.5, z_hb, 2.5), (12.6, 7.1, z_hb + 0.25, 2.8), (15.5, HD, z_knee, 3.2), (15.5, HD, z_top - 0.9, 3.2)]
    rings = [loop_rrect(AX, cy, hw, hd, rad, z, 4) for hw, hd, z, rad in hp]
    rings.insert(0, loop_rrect(AX, cy, 10.6, 5.6, 2.0, z_hb - 0.05, 4))
    g.loft(rings, [P["HEAD"], P["HEAD"], P["HEAD"], P["HEAD"]], "head_body", smooth=False)
    # lid: overhanging slab with a dark lip under its front edge (sprite row 15)
    lid = [(15.4, HD - 0.1, z_top - 0.95, 3.0), (16.0, HD + 0.5, z_top - 0.55, 3.3), (16.0, HD + 0.5, z_top + 0.15, 3.3),
           (15.6, HD + 0.1, z_top + 0.55, 3.0)]
    rings = [loop_rrect(AX, cy, hw, hd, rad, z, 4) for hw, hd, z, rad in lid]
    g.loft(rings, [P["LIP"], P["LID"], P["LID"]], "head_lid", smooth=False)
    z_lid = z_top + 0.55

    # grille: dark recessed louvre box across the front (cols 17-31, rows 19-22)
    gy = cy - HD
    g_z0, g_z1 = zrow(22.3, VB + HD + 0.6), zrow(18.8, VB + HD + 0.6)
    block(g, 16.9, 32.1, gy - 0.6, gy + 1.0, g_z0, g_z1, P["GRILLE"], "grille", ch=0.25)
    for zz in (zrow(20.3, VB + HD + 0.9), zrow(21.7, VB + HD + 0.9)):
        block(g, 17.4, 31.6, gy - 0.95, gy + 0.2, zz - 0.32, zz + 0.32, P["SLAT"], "grille_slat", ch=0.12)
    # vent fins on the head's face either side above the grille (sprite cols 15/17/19 and 29/31/33, rows 16-18)
    fz0, fz1 = zrow(18.6, VB + HD + 0.5), zrow(15.9, VB + HD + 0.5)
    for fu in (15.5, 17.5, 19.5):
        for uu in (fu, 2 * AX - fu):
            block(g, uu - 0.38, uu + 0.38, gy - 0.55, gy + 0.6, fz0, fz1, P["PANEL"], "vent_fin", ch=0.12)
    # chin panel under the grille (cols 20-27 rows 22-23, light)
    zc0, zc1 = zrow(24.0, VB + 6.9), zrow(22.3, VB + 7.2)
    block(g, 20.2, 28.8, cy - 7.0, cy - 4.0, zc0, zc1, P["CHIN"], "chin", ch=0.2)

    # rear service panel and vents (rear view detail)
    block(g, 18.0, 31.0, cy + HD - 0.3, cy + HD + 0.45, z_knee + 0.4, z_top - 1.4, P["REAR"], "rear_panel", ch=0.2)
    for i in range(3):
        zz = z_knee + 1.2 + i * 1.3
        block(g, 19.0, 30.0, cy + HD + 0.3, cy + HD + 0.75, zz - 0.3, zz + 0.3, P["SLAT"], "rear_vent", ch=0.1)

    s0 = len(g.f)
    # chin struts (cols 14-16, rows 24-26), hanging from the head's chin
    leg_bot = zrow(27.0, VB + 6.2)
    block(g, 14.55, 16.95, cy - 6.2, cy - 3.6, leg_bot, z_hb + 1.0, P["LEG"], "head_leg_l", ch=0.3)
    block(g, 14.3, 17.5, cy - 6.4, cy - 3.4, zrow(24.7, VB + 6.4), z_hb + 0.8, P["LEG"], "head_leg_root_l", ch=0.3)
    # red yoke clamp each side of the column top (cols 18-19, rows 24-26)
    yk0, yk1 = zrow(26.2, VB + 2.6), z_hb + 0.4
    block(g, 18.0, 21.0, cy - 2.6, cy + 2.6, yk0, yk1, P["YOKE"], "yoke_l", ch=0.35)
    # tie rod from the strut's foot to the yoke (rows 25-26, cols 17-18, dark in the sprite)
    tz = zrow(26.2, VB + 4.6)
    rod = []
    for xx in (16.5, 18.3):
        rod.append([(xx, cy - 4.0 + 0.62 * math.cos(2 * math.pi * i / 8), tz + 0.62 * math.sin(2 * math.pi * i / 8))
                    for i in range(8)])
    g.loft(rod, P["GRILLE"], "tie_rod_l", smooth=True)
    # bolt through the yoke (pointing west)
    by_z = (yk0 + yk1) / 2
    lens_r = []
    for rr, dx in ((0.6, 0.0), (0.6, -0.5), (0.35, -0.7)):
        lens_r.append([(18.0 + dx, cy + 1.2 + rr * math.cos(2 * math.pi * i / 8), by_z + rr * math.sin(2 * math.pi * i / 8))
                       for i in range(8)])
    g.loft(lens_r, P["RED"], "yoke_bolt_l", smooth=False)

    # ---- POD: a vertical canister on each flank (cols 3-8, rows 8-21): red cap on top, red clamp band, ----
    # a red strap down its front carrying a lamp, curling in under the head to the chin.
    pu = 6.05
    pr = 3.0
    z_pb = zrow(21.6, VB + 2.2)       # rounded foot, front-bottom on row 21.6
    z_ps = zrow(8.0, VB - 2.0)        # shoulder top (r ~2) on row 8
    z_cap = zrow(6.0, VB - 1.6)
    zcb = zrow(16.9, VB + pr + 0.25)
    pprof = [(0.0, z_pb - 0.2), (1.2, z_pb), (1.9, z_pb + 0.6), (2.4, z_pb + 1.6), (2.45, zcb - 0.2), (pr, zcb + 0.2), (pr, z_ps - 3.0),
             (2.75, z_ps - 1.8), (2.3, z_ps - 0.8), (1.9, z_ps)]
    lathe(g, pu, cy, pprof, [P["PODLO"]] * 5 + [P["POD"]] * 4, "pod_l", sides=28)
    # light ring a third of the way up
    zb = zrow(12.6, VB + pr)
    lathe(g, pu, cy, [(pr + 0.15, zb - 0.3), (pr + 0.15, zb + 0.3)], P["PODBAND"], "pod_band_l", sides=28,
          cap0=False, cap1=False)
    # red cap: a clamp disc with a raised boss (cols 5-7, rows 6-7)
    lathe(g, 6.5, cy, [(1.5, z_ps - 0.3), (1.6, z_ps), (1.6, z_cap - 0.3), (1.4, z_cap)],
          [P["CAP"], P["CAP"], P["CAP"]], "pod_cap_l", sides=24)
    lathe(g, 6.5, cy, [(1.0, z_cap - 0.1), (0.9, z_cap + 0.25), (0.6, z_cap + 0.4)], P["BOSS"], "pod_boss_l", sides=12)
    # red clamp band round the pod (row 16, cols 4-8)
    zcb = zrow(16.9, VB + pr + 0.25)
    lathe(g, pu, cy, [(pr + 0.05, zcb - 0.1), (pr + 0.28, zcb), (pr + 0.28, zcb + 1.1), (pr + 0.05, zcb + 1.2)],
          P["HEAD"], "pod_clamp_l", sides=28, cap0=False, cap1=False)
    # yoke tying the pod to the head side
    block(g, 8.4, 9.9, cy - 2.0, cy + 2.0, zrow(21.2, VB + 2.0), z_ps - 2.6, P["GRILLE"], "pod_yoke_l", ch=0.3)

    # strap: from the clamp band down the pod's front, then in under the head to the chin
    def rowz(row, v):
        return zrow(row, v)
    vf = VB + pr + 0.55             # strap mid-plane in front of the pod
    path = [(6.4, -vf, zcb + 0.4), (6.4, -vf, rowz(19.0, vf)), (6.4, -vf, rowz(20.6, vf)), (6.75, -vf, rowz(21.5, vf)),
            (7.6, -vf, rowz(22.15, vf)), (8.9, -vf, rowz(22.45, vf)), (10.6, -vf, rowz(22.5, vf)), (12.6, -vf, rowz(22.4, vf))]
    sweep_box(g, path, 1.3, 0.6, P["RED"], "bracket_l")
    # lamp on the strap's front (col 6, rows 18-19): a hooded lens
    zl = zrow(19.7, vf + 0.6)
    lamp = []
    for rr, dy in ((0.72, 0.0), (0.72, -0.5), (0.42, -0.8)):
        lamp.append([(6.4 + rr * math.cos(2 * math.pi * i / 10), -vf - 0.6 + dy, zl + rr * 1.1 * math.sin(2 * math.pi * i / 10))
                     for i in range(10)])
    g.loft([list(reversed(r)) for r in lamp], P["LAMP"], "lamp_l", smooth=True)
    zh = zrow(18.3, vf + 1.2)
    block(g, 5.5, 7.3, -vf - 1.25, -vf + 0.2, zh - 0.35, zh + 0.4, P["HOOD"], "lamp_hood_l", ch=0.15)

    mirror(g, s0)

    # ---- DOMES: two outer (cols 8-19) and a narrower centre one (cols 21-28): rounded-square glass ----
    def dome(u, rx, ry, top_row, pal, part, n_plan=3.5, n_prof=5.0):
        z0 = z_lid - 0.1
        h = 4.0
        for _ in range(30):
            best = 1e9
            for i in range(0, 41):
                t = i / 40
                f = (1 - t ** n_prof) ** (1 / n_prof)
                zz = z0 + h * t
                best = min(best, VB - A * ry * f - K * zz)
            h += (best - top_row) / K
        rings = []
        for i in range(0, 17):
            t = (i / 16) ** 0.8
            f = (1 - t ** n_prof) ** (1 / n_prof) if t < 1 else 0.0
            f = max(f, 0.0)
            rings.append(loop_oval(u, cy, rx * f + 1e-3, ry * f + 1e-3, z0 + h * t, 40, n_plan))
        g.loft(rings, pal, part, cap0=True, cap1=False, smooth=True)
        g.loft([loop_oval(u, cy, rx + 0.3, ry + 0.3, z_lid - 0.2, 40, n_plan),
                loop_oval(u, cy, rx + 0.3, ry + 0.3, z_lid + 0.05, 40, n_plan),
                loop_oval(u, cy, rx, ry, z_lid + 0.2, 40, n_plan)], P["DRING"], part + "_ring", cap0=False, cap1=False)
    # bulkheads framing the dome bay (cols 8, 20, 29, 40): pale plates standing between the domes
    for bu, top in ((8.75, 5.0), (20.15, 6.0)):
        for uu in (bu, 2 * AX - bu):
            zt_ = zrow(top, VB - 3.6)
            block(g, uu - 0.6, uu + 0.6, cy - 4.2, cy + 3.6, z_lid - 0.3, zt_, P["BULK"], "bulkhead", ch=0.25)
    dome(14.0, 5.85, 5.4, 5.0, P["DOME"], "dome_l")
    dome(2 * AX - 14.0, 5.85, 5.4, 5.0, P["DOME"], "dome_r")
    dome(AX, 4.15, 4.6, 6.0, P["DOMEC"], "dome_c")
    return g


def sweep_box(g, path, hu, hv, pal, part):
    """A chamfered box section (hu across the path in the X/Z plane, hv along Y) swept along a path in the
    X/Z plane (constant Y)."""
    rings = []
    n = len(path)
    for i, p in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        ln = math.hypot(tx, tz) or 1.0
        tx, tz = tx / ln, tz / ln
        nx, nz = -tz, tx  # in-plane normal
        c = 0.35
        sec = [(hu, -hv + c), (hu, hv - c), (hu - c, hv), (-hu + c, hv), (-hu, hv - c), (-hu, -hv + c),
               (-hu + c, -hv), (hu - c, -hv)]
        rings.append([(p[0] + s * nx, p[1] + w, p[2] + s * nz) for s, w in sec])
    # make winding outward: check with a cross product at the first ring
    ids_before = len(g.f)
    g.loft(rings, pal, part, smooth=False)
    fix_orientation(g, ids_before, path)


def fix_orientation(g, start, path):
    """Flip faces added since `start` if they point toward the path (inward)."""
    for fi in range(start, len(g.f)):
        idx, pal, part = g.f[fi]
        pts = [g.v[i] for i in idx]
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        nrm = newell(pts)
        # nearest path point
        best = min(path, key=lambda q: sum((q[k] - c[k]) ** 2 for k in range(3)))
        d = [c[k] - best[k] for k in range(3)]
        if sum(nrm[k] * d[k] for k in range(3)) < 0:
            g.f[fi] = (tuple(reversed(idx)), pal, part)


def newell(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % len(pts)]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return (nx, ny, nz)


# ---------------------------------------------------------------------------------------------
# Measuring (art view): rasterise, IoU per piece vs the inner masks, colour per sprite pixel
# ---------------------------------------------------------------------------------------------

def art(p):
    """(screen column, screen row, nearness to the art camera) of a build point."""
    x, y, z = p
    v = -y
    return x, VB + A * (v - VB) - K * z, K * v + A * z


def rasterise(g, k=8, W=48, H=56):
    import numpy as np
    cov = np.zeros((H * k, W * k), bool)
    depth = np.full((H * k, W * k), -1e9)
    pal = np.full((H * k, W * k), -1, int)
    prt = np.full((H * k, W * k), -1, int)
    names = sorted({f[2] for f in g.f})
    pid = {n: i for i, n in enumerate(names)}
    V = np.array([art(p) for p in g.v])
    for idx, pa, part in g.f:
        for t in range(1, len(idx) - 1):
            tri = V[[idx[0], idx[t], idx[t + 1]]]
            xs, ys = tri[:, 0] * k, tri[:, 1] * k
            x0, x1 = max(0, int(math.floor(xs.min()))), min(W * k - 1, int(math.ceil(xs.max())))
            y0, y1 = max(0, int(math.floor(ys.min()))), min(H * k - 1, int(math.ceil(ys.max())))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            l3 = 1 - l1 - l2
            m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            if not m.any():
                continue
            d = l1 * tri[0, 2] + l2 * tri[1, 2] + l3 * tri[2, 2]
            sub_cov = cov[y0:y1 + 1, x0:x1 + 1]
            sub_d = depth[y0:y1 + 1, x0:x1 + 1]
            sub_p = pal[y0:y1 + 1, x0:x1 + 1]
            sub_cov |= m
            win = m & (d > sub_d)
            sub_d[win] = d[win]
            sub_p[win] = pa
            prt[y0:y1 + 1, x0:x1 + 1][win] = pid[part]
    rasterise.names = names
    rasterise.prt = prt
    return cov, pal


def measure(g, out_png=None):
    import numpy as np
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as SM
    k = 8
    cov, pal = rasterise(g, k)
    res = {}
    worst = 1.0
    full_inner = np.zeros((56, 48), bool)
    full_free = np.zeros((56, 48), bool)
    full_idx = np.full((56, 48), -1, int)
    grid_all = np.zeros((56, 48), bool)
    for name, (c0, r0) in PIECES.items():
        idx, colors = SM.load(name, None, str(WT / "reference" / "models"))
        partners = SM.pulse_partners(idx, SM.load_frames(name, str(WT / "reference" / "models")))
        m = SM.masks(idx, colors, partners)
        top = cov[r0 * k:(r0 + 28) * k, c0 * k:(c0 + 24) * k]
        mm = SM.measure(m, top.tolist())
        res[name] = mm
        worst = min(worst, mm["iou_rule_grid"])
        full_inner[r0:r0 + 28, c0:c0 + 24] = np.array(m["inner"])
        full_free[r0:r0 + 28, c0:c0 + 24] = np.array(m["free"])
        full_idx[r0:r0 + 28, c0:c0 + 24] = np.array(idx)
    covg = cov.reshape(56, k, 48, k).mean(axis=(1, 3)) >= 0.5
    # colour: model's front-most palette at each sprite pixel centre vs the sprite index
    cen = pal[k // 2::k, k // 2::k]
    agree = []
    for (rr, cc) in zip(*np.nonzero(full_inner & covg)):
        s, mpal = full_idx[rr, cc], cen[rr, cc]
        agree.append((s, mpal))
    exact = sum(1 for s, m_ in agree if s == m_)
    near = sum(1 for s, m_ in agree if s >> 4 == m_ >> 4 and abs(s - m_) <= 2)
    res["colour"] = {"pixels": len(agree), "exact": exact, "within2": near}
    prt = rasterise.prt[k // 2::k, k // 2::k]
    table = []
    import re as _re
    groups = {}
    for i, n in enumerate(rasterise.names):
        groups.setdefault(_re.sub(r"_(l|r)$", "", n), []).append(i)
    for gname, ids in sorted(groups.items()):
        sel = np.isin(prt, ids) & full_inner & covg
        if sel.sum() < 2:
            continue
        sp = np.sort(full_idx[sel])
        lo, hi = int(len(sp) * 0.15), int(len(sp) * 0.85)
        core = sp[lo:max(hi, lo + 1)]
        mp = np.bincount(cen[sel]).argmax()
        table.append((gname, int(sel.sum()), int(np.median(core)), int(mp)))
    res["regions"] = table
    res["worst"] = worst
    rows = []
    for r in range(56):
        line = ""
        for c in range(48):
            s, mm_ = full_inner[r, c], covg[r, c]
            line += "#" if s and mm_ else ("-" if s else ("+" if mm_ else "."))
        rows.append(f"{r:2d} {line}")
    res["diff"] = rows
    if out_png:
        from PIL import Image
        img = np.zeros((56, 48, 3), np.uint8)
        img[full_inner & covg] = (60, 180, 120)
        img[full_inner & ~covg] = (230, 60, 60)
        img[~full_inner & covg] = (80, 120, 255)
        Image.fromarray(img).resize((48 * 8, 56 * 8), Image.NEAREST).save(out_png)
        # palette render of the art view
        cols = {}
        for name in PIECES:
            cols.update(json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())["colors"])
        im2 = np.zeros((56 * k, 48 * k, 3), np.uint8) + 20
        for pi in np.unique(pal):
            if pi < 0:
                continue
            im2[pal == pi] = cols.get(str(pi), (255, 0, 255))
        Image.fromarray(im2).save(str(out_png).replace(".png", "_pal.png"))
    return res


# ---------------------------------------------------------------------------------------------
# Blender: mesh, outline shell, art-row cut into pieces, export, views
# ---------------------------------------------------------------------------------------------

def blender_main(argv):
    import bpy
    import bmesh
    from mathutils import Matrix, Vector
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import common

    views = argv[argv.index("--views") + 1] if "--views" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    bpy.context.view_layer.update()
    sprite = {"name": NAME, "colors": {}}
    for name in PIECES:
        sprite["colors"].update(common.load_sprite(WT, name)["colors"])

    g = build()
    pals = sorted({pa for _, pa, _ in g.f})
    mats = []
    for pa in pals:
        if pa in EMIT:
            m = common.palette_material(sprite, pa, "nshj51A", metallic=0.2, roughness=0.4, emission_strength=EMIT[pa])
        elif pa in (45, 44):
            m = common.palette_material(sprite, pa, "nshj51A", metallic=0.15, roughness=0.22)
        elif pa >= 112:
            m = common.palette_material(sprite, pa, "nshj51A", metallic=0.45, roughness=0.42)
        elif pa in (33, 34, 36):
            m = common.palette_material(sprite, pa, "nshj51A", metallic=0.3, roughness=0.6)
        else:
            m = common.palette_material(sprite, pa, "nshj51A", metallic=0.4, roughness=0.45)
        mats.append(m)
    mi = {pa: i for i, pa in enumerate(pals)}

    bm = bmesh.new()
    bv = [bm.verts.new(p) for p in g.v]
    for (idx, pa, part), sm in zip(g.f, g.smooth):
        try:
            f = bm.faces.new([bv[i] for i in idx])
        except ValueError:
            continue
        f.material_index = mi[pa]
        f.smooth = sm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Scale(PX, 4), verts=bm.verts)
    me = bpy.data.meshes.new(NAME + "_A")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME + "_A", me)
    coll.objects.link(obj)
    bpy.context.view_layer.update()
    me.set_sharp_from_angle(angle=math.radians(35))
    print("tris", sum(len(p.vertices) - 2 for p in me.polygons))

    shell = common.outline_shell(obj, coll, voxel=0.02, faces=6000, smooth=6, inside=0.005)

    # ---- cut into the four pieces along the ART view's rows/columns, re-centre each upright ----
    def cut(src, c0, r0, fill):
        bmc = bmesh.new()
        bmc.from_mesh(src.data)
        # art row of a point (Blender units): s*PX = VB*PX + A(-Y - VB*PX) - K Z
        n_row = Vector((0.0, -A, -K))  # gradient of s wrt (X,Y,Z) (scaled)
        planes = []
        # rows r0..r0+28: keep s >= r0 and s <= r0+28 ; s = VB(1-A)PX + n_row.p
        off = VB * (1 - A) * PX
        for srow, keep_ge in ((r0, True), (r0 + 28, False)):
            if (srow == 0 and keep_ge) or (srow == 56 and not keep_ge):
                continue
            # plane: n_row.p = srow*PX - off; point on plane
            d = srow * PX - off
            co = n_row * (d / n_row.length_squared)
            planes.append((co, -n_row if keep_ge else n_row))  # clear_outer removes the side the normal points to
        for xcol, keep_ge in ((c0, True), (c0 + 24, False)):
            if (xcol == 0 and keep_ge) or (xcol == 48 and not keep_ge):
                continue
            co = Vector((xcol * PX, 0, 0))
            planes.append((co, Vector((-1, 0, 0)) if keep_ge else Vector((1, 0, 0))))
        for co, no in planes:
            geom = bmc.verts[:] + bmc.edges[:] + bmc.faces[:]
            res = bmesh.ops.bisect_plane(bmc, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            if fill:
                edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
                if edges:
                    # the cut edges are sharp and the caps flat, so the caps' normals never bleed
                    # into the surface's smooth shading (a dark seam where the pieces meet)
                    for e in edges:
                        e.smooth = False
                    caps = bmesh.ops.holes_fill(bmc, edges=edges, sides=0)["faces"]
                    for f in caps:
                        f.smooth = False
        # re-centre on the piece block: X - col_c, Y + row_c (Y = -v)
        cc, rc = c0 + 12, r0 + 14
        bmesh.ops.translate(bmc, vec=(-cc * PX, rc * PX, 0), verts=bmc.verts)
        mesh = bpy.data.meshes.new("cut")
        bmc.to_mesh(mesh)
        bmc.free()
        for m in src.data.materials:
            mesh.materials.append(m)
        return mesh

    ztop = max(v[2] for v in g.v)
    out_objs = []
    for name, (c0, r0) in PIECES.items():
        rc = r0 + 14
        tag = {"tyrian_oblique": [K, A, (VB - rc) * PX],
               "tyrian_depth_band": [BAND[0], BAND[1], 0.0, ztop * PX]}
        pm = cut(obj, c0, r0, True)
        po = bpy.data.objects.new(name, pm)
        coll.objects.link(po)
        for kk, vv in tag.items():
            po[kk] = vv
        sm = cut(shell, c0, r0, False)
        so = bpy.data.objects.new(name + "_outline", sm)
        coll.objects.link(so)
        so["tyrian_outline"] = True
        for kk, vv in tag.items():
            so[kk] = vv
        so.parent = po
        out_objs += [po, so]
        print(name, "faces", len(pm.polygons), "tag", tag)

    if "--no-export" not in argv:
        obj.hide_render = shell.hide_render = True
        for name in PIECES:
            mine = [o for o in out_objs if o.name == name or o.name == name + "_outline"]
            common.export_sprite_model(WT, mine, f"enemies/{name}", common.load_sprite(WT, name)["sprites"])

    if views:
        render_views(obj, shell, out_objs, Path(views), g)


def render_views(obj, shell, pieces, out, g):
    import bpy
    from mathutils import Vector, Matrix
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in pieces:
        o.hide_render = True
    obj.hide_render = False
    shell.hide_render = True
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 1.0
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(40), math.radians(-25), math.radians(-30))
    fill = bpy.data.lights.new("fill", "SUN")
    fill.energy = 0.9
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(-60), math.radians(30), math.radians(160))
    # ground disc
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=3.2, fill_type="NGON", location=(AX * PX, -VB * PX, -0.002))
    gnd = bpy.context.active_object
    gm = bpy.data.materials.new("gnd")
    gm.diffuse_color = (0.12, 0.13, 0.12, 1)
    gm.use_nodes = True
    bsdf = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.09, 0.1, 0.09, 1)
    gnd.data.materials.append(gm)

    c = Vector((AX * PX, -VB * PX, 2.1))
    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def shot(fname, direction, ortho=None, lens=60, dist=14.0, target=c, hide_ground=False):
        d = Vector(direction).normalized()
        cam.location = target + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if d.z > 0.999:
            cam.rotation_euler = (0.0, 0.0, 0.0)
        if ortho:
            cam_d.type = "ORTHO"
            cam_d.ortho_scale = ortho
        else:
            cam_d.type = "PERSP"
            cam_d.lens = lens
        gnd.hide_render = hide_ground
        scene.render.filepath = str(out / fname)
        bpy.ops.render.render(write_still=True)

    def az(deg, elev):
        a, e = math.radians(deg), math.radians(elev)
        # deg 0 = from south (-Y)
        return (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))

    shot("top.png", (0, 0, 1), ortho=5.4, target=Vector((AX * PX, -VB * PX, 0)))
    shot("front.png", az(0, 0.01), ortho=5.4)
    shot("side.png", az(90, 0.01), ortho=5.4)
    shot("rear.png", az(180, 0.01), ortho=5.4)
    shot("q34.png", az(-35, 30), lens=50)
    shot("q34r.png", az(145, 35), lens=50)
    shot("art.png", az(0, E), ortho=5.4)
    shot("under.png", az(20, -40), lens=50, hide_ground=True)
    # game camera: the art-view squeezed form (what the renderer would draw), seen from the game's tilt
    obj.hide_render = True
    gnd.hide_render = True
    gm2 = art_form(obj, g)
    gm2.hide_render = False
    shot("game.png", (0, -math.sin(math.radians(32)), math.cos(math.radians(32))), lens=50, dist=9.5,
         target=Vector((AX * PX, -28 * PX, 0.2)), hide_ground=False)
    shot("game_top.png", (0, 0, 1), ortho=5.4, target=Vector((AX * PX, -28 * PX, 0.2)))
    gm2.hide_render = True
    obj.hide_render = False


def art_form(obj, g):
    """A copy of the model drawn as obliqueView.ts draws it: (x, h, s) with h squeezed into BAND."""
    import bpy
    from mathutils import Matrix
    me = obj.data.copy()
    ztop = max(v[2] for v in g.v) * PX
    for v in me.vertices:
        x, y, z = v.co
        s = VB * PX + A * (-y - VB * PX) - K * z      # art row (units, south +)
        h = BAND[0] + (min(max(z / ztop, 0), 1)) * (BAND[1] - BAND[0])
        v.co = (x, -s, h)
    o = bpy.data.objects.new("artform", me)
    bpy.context.scene.collection.objects.link(o)
    me.update()
    return o


if __name__ == "__main__":
    if "bpy" in sys.modules:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        blender_main(argv)
    else:
        g = build()
        r = measure(g, str(FIN / "iou.png"))
        for kk in PIECES:
            print(kk, r[kk]["iou_rule_grid"], r[kk]["iou_rule"], "edge", r[kk]["edge_vs_inner_px"])
        print("worst", r["worst"], "colour", r["colour"], "tris", sum(len(f[0]) - 2 for f in g.f))
        for row in r["regions"]:
            print("  region %-18s px %4d sprite median %3d model %3d" % row)
        print("\n".join(r["diff"]))
