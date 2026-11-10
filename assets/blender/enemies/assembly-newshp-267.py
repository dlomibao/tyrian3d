"""Brown pump tower on a grey stone plinth (newshp.shp 115/229/231/267/269, an assembly of 5 pieces),
silhouette and readability from the small tilted game camera first, then detail.

Seen in 1.1 ASTEROID1, 1.2 ASTEROID2, 1.3 ASTEROID?, 2.4 ASTCITY, 3.2 AST. CITY. Five 2x2 ground
enemies make one 48 x 84 px structure: a grey dressed-stone platform (rows 28-83) carrying a raised
light plinth, a brown pump machine with brass plates and a brass reservoir, a dark open lattice
gantry running up the screen to a three-tier brass pressure vessel lying on saddles north of the
platform (newshp-115: its three frames move the shine from tier to tier), and a hydraulic ram arm
reaching down the screen to a pump head on the stone apron, beside a sunken grille.

Design B reads at game size by HEIGHT TIERS with clean value steps, each a clear hard mass:
  stone 0.6-1.4 px  <  plinth 2.4  <  pump head 4.8  <  body 6.4  <  gantry rails 7.4, ram 7.6
  <  reservoir 8.2  <  gearbox 9.0  <  vessel 11.6 (the tallest, brightest thing, at the back).
Deep gaps separate masses (V-grooved plinth slabs, an open hatch and slot in the gantry, a recessed
deck with gussets beside the gearbox, a drain channel at the machine's foot, a sunken grille with
free-standing ribs), so the small tilted view keeps the sprite's dark accents as real cavities.

Rules held (D52, D65, D74): the top view is the D74 inner mask row by row (the vessel's tiers are
lofted through the mask's row extents with pchip; the platform is the sprite's full rectangle);
the sprite's palette index per region (median, darkest/brightest 15 % dropped); highlights are
sheen (the col-4 rim, col-14 ram glint, the tier shines) never geometry or paint; the vessel's
tier shine is animated per frame (D17): base 21, lit 26 / 26 / 27 on frames 115 / 117 / 119.
Underside: flat closed bases on z = 0 only. No concept projection; outline shell (D51).

Coordinates: assembly px, x = column - 24 (pixel edges), y = 42 - row (up-screen +), z px up;
Blender = px / 12. Assembly px (0, 0) is screen (164, -32); the centre (24, 42) is screen (188, 10),
the same CX0, CY0 as assets/blender/enemies/assembly-newshp-267.py, so common.split_assembly cuts
the same five pieces.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshp-267.py   (--no-bake skips the AO/roughness bake)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)
ROOT = WT

NAME = "assembly-newshp-267"
TAG = "nshp267"
PIECES = ["newshp-115", "newshp-229", "newshp-231", "newshp-267", "newshp-269"]
CX0, CY0 = 188, 10
PX = 1 / 12

# Vessel: section z half-height = K * half-width, axis height ZC.
K = 0.70
ZC = 6.7


def X(c):
    return c - 24.0


def Y(r):
    return 42.0 - r


# --- sprite / materials -------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(WT, "newshp-267")
    for name in PIECES:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


MATS = [
    # name, palette index, metallic, roughness, frames
    ("STONE", 5, 0.0, 0.88, None),
    ("STONE_LT", 7, 0.0, 0.85, None),
    ("PLINTH", 9, 0.0, 0.8, None),
    ("TRENCH", 1, 0.0, 0.9, None),
    ("PIT", 2, 0.05, 0.9, None),
    ("RIB", 4, 0.3, 0.6, None),
    ("BODY", 167, 0.3, 0.55, None),
    ("GEARBOX", 166, 0.3, 0.52, None),
    ("BODY_DK", 164, 0.3, 0.6, None),
    ("SKIRT", 162, 0.3, 0.65, None),
    ("DECK", 161, 0.25, 0.7, None),
    ("WELL", 160, 0.1, 0.9, None),
    ("RAIL", 162, 0.35, 0.55, None),
    ("TIE", 165, 0.35, 0.5, None),
    ("YOKE", 168, 0.3, 0.5, None),
    ("HEAD", 163, 0.3, 0.58, None),
    ("BRASS", 23, 0.4, 0.48, None),
    ("BRASS_PL", 22, 0.45, 0.4, None),
    ("BRASS_DK", 21, 0.45, 0.46, None),
    ("BRASS_NUT", 20, 0.45, 0.45, None),
    ("BOLT", 25, 0.5, 0.38, None),
    ("TIER_T", 21, 0.45, 0.46, {119: 27}),
    ("TIER_M", 21, 0.45, 0.46, {117: 26}),
    ("TIER_B", 21, 0.45, 0.46, {115: 26}),
    ("COLLAR", 17, 0.45, 0.5, None),
    ("SADDLE", 164, 0.3, 0.6, None),
]
M = {n: i for i, (n, *_r) in enumerate(MATS)}


def materials(sprite):
    out = []
    for n, idx, met, rough, frames in MATS:
        tag = f"{TAG}-{n.lower()}" if frames else TAG
        out.append(common.palette_material(sprite, idx, tag, metallic=met, roughness=rough, frames=frames))
    return out


# --- builders (px) -------------------------------------------------------------------------------

def box(P, c0, r0, c1, r1, z0, z1, ch, mat, chz=None):
    """Chamfered box over pixel edges c0..c1, r0..r1 (rows down-screen)."""
    T.hull(P, T.cbox(X(c0), X(c1), Y(r1), Y(r0), z0, z1, ch, chz), mat)


def prism(P, outline, z0, z1, ch, mat):
    """Convex prism on an outline of (col, row) pixel edges, top edges chamfered by ch."""
    pts = [(X(c), Y(r)) for c, r in outline]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    top = []
    for x, y in pts:
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1
        top.append((x + dx / d * ch * 1.3, y + dy / d * ch * 1.3, z1))
    T.hull(P, [(x, y, z0) for x, y in pts] + [(x, y, z1 - ch) for x, y in pts] + top, mat)


def hullpts(P, pts_cr, mat):
    """Convex hull of (col, row, z) points."""
    T.hull(P, [(X(c), Y(r), z) for c, r, z in pts_cr], mat)


def cyl_z(P, c, r, rad, z0, z1, mat, n=8, ch=0.0):
    """Upright cylinder (bolt heads, bosses) at pixel position (c, r)."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        x, y = X(c) + rad * math.cos(a), Y(r) + rad * math.sin(a)
        pts.append((x, y, z0))
        if ch:
            pts.append((x, y, z1 - ch))
            pts.append((X(c) + (rad - ch) * math.cos(a), Y(r) + (rad - ch) * math.sin(a), z1))
        else:
            pts.append((x, y, z1))
    T.hull(P, pts, mat)


def cyl_x(P, c0, c1, r, z, rad, mat, n=12, ch=0.15):
    """A pin along the screen's x axis (columns c0..c1) at row r, height z; ends chamfered."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        dy, dz = math.cos(a), math.sin(a)
        for c, rr in ((c0, rad - ch), (c0 + ch, rad), (c1 - ch, rad), (c1, rad - ch)):
            pts.append((X(c), Y(r) + rr * dy, z + rr * dz))
    T.hull(P, pts, mat)


def ring_loft(P, stations, mat, n=24, cap=True):
    """A closed loft along y through elliptical sections: stations (row, xc_col, half_w, zc, half_h).
    Zero-size stations collapse to a point (domes)."""
    rings = []
    for r, c, w, zc, h in stations:
        y = Y(r)
        if w <= 1e-4:
            rings.append([P.v((X(c), y, zc))])
            continue
        rings.append([P.v((X(c) + w * math.cos(2 * math.pi * k / n), y,
                           zc + h * math.sin(2 * math.pi * k / n))) for k in range(n)])
    cen = [Vector((X(c), Y(r), zc)) for r, c, w, zc, h in stations]
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        away = tuple((cen[i] + cen[i + 1]) / 2)
        if len(a) == 1 and len(b) == 1:
            continue
        for k in range(n):
            j = (k + 1) % n
            if len(a) == 1:
                P.f((a[0], b[k], b[j]), mat, away=away)
            elif len(b) == 1:
                P.f((a[k], a[j], b[0]), mat, away=away)
            else:
                P.f((a[k], a[j], b[j], b[k]), mat, away=away)
    if cap:
        if len(rings[0]) > 1:
            P.f(rings[0], mat, out=(0, 1, 0))
        if len(rings[-1]) > 1:
            P.f(rings[-1], mat, out=(0, -1, 0))


def cyl_y(P, c, z, r0, r1, rad, mat, n=16, ch=0.25):
    """A cylinder along the screen's y axis (rows r0..r1), axis at column c, height z, ends chamfered."""
    ring_loft(P, [(r0, c, rad - ch, z, rad - ch), (r0 + ch, c, rad, z, rad),
                  (r1 - ch, c, rad, z, rad), (r1, c, rad - ch, z, rad - ch)], mat, n=n)


# --- the vessel (newshp-115) ---------------------------------------------------------------------

def vessel(P):
    """Three lofted brass tiers through the D74 inner mask's row extents (pixel-edge columns at
    each row centre; the left edge sits inside the sprite's ink, the right edge on its outer edge),
    joined at two flanged necks, on three saddles. Each tier has its own animated material."""
    def tier(rows, mat, n=28):
        rs = [r for r, l, rr in rows]
        cs = T.pchip(rs, [(l + rr) / 2 for r, l, rr in rows])
        ws = T.pchip(rs, [(rr - l) / 2 for r, l, rr in rows])
        st = []
        a, b = rs[0], rs[-1]
        steps = max(8, int((b - a) / 0.3))
        for i in range(steps + 1):
            r = a + (b - a) * i / steps
            w = max(0.0, ws(r))
            st.append((r, cs(r), w, ZC, K * w))
        ring_loft(P, st, mat, n=n)

    # top tier, rows 4-10 (north dome first)
    tier([(3.72, 14.5, 14.5), (3.85, 12.6, 16.4), (4.15, 11.4, 17.6), (4.5, 11, 18), (5.5, 10, 19),
          (6.5, 9.05, 19.95), (7.5, 9.05, 19.95), (8.5, 9.6, 20.0), (9.5, 9.9, 19.9), (10.3, 10.6, 19.4),
          (10.9, 11.6, 18.4)], M["TIER_T"])
    # neck 1 + flange (row 11 is the dark collar)
    ring_loft(P, [(10.4, 14.6, 3.6, ZC, 3.6 * K), (12.2, 14.6, 3.6, ZC, 3.6 * K)], M["COLLAR"], n=24)
    ring_loft(P, [(10.55, 14.5, 4.25, ZC, 4.25 * K), (10.75, 14.5, 4.5, ZC, 4.5 * K),
                  (11.45, 14.5, 4.5, ZC, 4.5 * K), (11.65, 14.5, 4.25, ZC, 4.25 * K)], M["COLLAR"], n=24)
    # middle tier, rows 12-17
    tier([(11.4, 14.6, 14.6), (11.55, 11.8, 17.4), (11.9, 10.0, 19.2), (12.5, 9.05, 19.95),
          (13.5, 8.05, 20.95), (15.0, 8.0, 21.0), (16.5, 8.05, 20.95), (17.3, 8.4, 20.6), (17.9, 9.6, 19.4),
          (18.3, 11.5, 17.5)], M["TIER_M"])
    # neck 2 + flange (rows 17-18 dark)
    ring_loft(P, [(17.2, 14.7, 5.6, ZC, 5.6 * K), (17.4, 14.7, 6.0, ZC, 6.0 * K),
                  (18.0, 14.7, 6.0, ZC, 6.0 * K), (18.3, 14.7, 5.6, ZC, 5.6 * K)], M["COLLAR"], n=28)
    # bottom tier, rows 18-27, its south dome running into the gantry head over the platform edge
    tier([(17.75, 15.0, 15.0), (17.9, 11.0, 19.0), (18.2, 8.4, 21.6), (18.5, 7.05, 22.95),
          (19.5, 6.05, 23.95), (21.5, 6.0, 24.0), (23.5, 6.0, 24.0), (24.5, 6.05, 23.95),
          (25.5, 7.05, 22.95), (26.5, 8.05, 21.95), (27.5, 9.05, 20.95), (28.5, 10.4, 19.4),
          (29.3, 12.2, 17.6), (29.75, 15.0, 15.0)], M["TIER_B"], n=32)
    # bolt ring heads on the two flanges (top half only: what the camera sees)
    for rr, w, zc in ((11.1, 4.5, ZC), (17.7, 6.0, ZC)):
        for k in range(1, 8):
            a = math.pi * k / 8
            c = 14.6 + (w + 0.05) * math.cos(a)
            z = zc + (w + 0.05) * K * math.sin(a)
            cx = c - 0.25 * math.cos(a)
            box(P, cx - 0.3, rr - 0.35, cx + 0.3, rr + 0.35, z - 0.5, z + 0.25, 0.08, M["BOLT"])
    # filler boss on the north dome and a gauge stub on the top tier
    cyl_z(P, 14.2, 5.6, 0.9, ZC + 2.4, ZC + 4.25, M["BRASS_NUT"], n=10, ch=0.2)
    # saddles: steel cradles from the ground up to under the equator (their tips show at the tier
    # sides in the sprite: col 9/19 at row 7, the SE rim of the bottom tier)
    def saddle(r0, r1, c, w, wt):
        """A steel cradle extruded along y: flat sides at +-w, its top hugging the tier's underside
        (an ellipse of half-width wt), so its horns reach up the flanks (their tips show at the
        tier's sides in the sprite: col 9/19 at row 7, the SE rim of the bottom tier)."""
        ht = K * wt
        prof = [(c - w, 0.0), (c + w, 0.0)]
        n = 14
        for i in range(n + 1):
            x = w - 2 * w * i / n
            u = min(0.999, abs(x) / wt)
            prof.append((c + x, ZC - ht * math.sqrt(1 - u * u) + 0.25))
        ring = []
        for r in (r0, r1):
            ring.append([P.v((X(cc), Y(r), z)) for cc, z in prof])
        cen = (X(c), Y((r0 + r1) / 2), ZC * 0.4)
        m = len(prof)
        for k in range(m):
            j = (k + 1) % m
            P.f((ring[0][k], ring[0][j], ring[1][j], ring[1][k]), M["SADDLE"], away=cen)
        P.f(ring[0], M["SADDLE"], out=(0, 1, 0))
        P.f(ring[1], M["SADDLE"], out=(0, -1, 0))
    saddle(6.3, 7.7, 14.5, 5.4, 5.5)
    saddle(14.2, 16.0, 14.5, 6.4, 6.5)
    saddle(20.8, 22.6, 15.0, 8.9, 9.0)
    saddle(24.6, 26.2, 15.0, 7.9, 8.4)
    # saddle base plates on the ground
    for r0, r1, c, w in ((6.2, 7.8, 14.5, 5.0), (14.2, 16.0, 14.5, 6.0), (20.8, 26.4, 15.0, 7.4)):
        box(P, c - w, r0, c + w, r1, 0, 0.5, 0.15, M["SADDLE"])
    # feed pipe from the gantry into the south dome
    cyl_y(P, 15.0, 6.2, 27.0, 31.0, 1.3, M["BRASS_DK"], n=14, ch=0.2)


# --- the platform ---------------------------------------------------------------------------------

STONE_W_JOINTS = [28, 37, 41.5, 46.5, 51.5, 55.5, 60.5, 65.5, 69.5, 74.5, 79.5, 84]
STONE_E_JOINTS = [28, 32.3, 37, 48.2, 54.5, 61.2, 67.5, 74.5, 79.5, 84]


# Plinth top slabs (col, row pixel edges), split by V joints.
SLABS = [
    (3.7, 28.02, 7.0, 36.5), (7.0, 28.02, 11.2, 36.5), (3.7, 36.5, 11.2, 40.3), (3.7, 40.3, 11.2, 45.0),
    (3.7, 45.0, 6.4, 57.5), (3.7, 57.5, 11.2, 70.0),
    (11.2, 28.02, 21.0, 45.0), (21.0, 28.02, 24.6, 45.0),
    (24.6, 28.02, 34.4, 36.5), (34.4, 28.02, 43.0, 32.4), (34.4, 32.4, 43.0, 36.5),
    (35.0, 36.5, 43.0, 48.6), (38.5, 48.6, 43.0, 57.5),
    (11.2, 45.0, 38.5, 57.5),
    (11.2, 57.5, 19.6, 70.0),
    (33.6, 62.6, 43.0, 70.0),
]


def platform(P):
    # stone bed (the full sprite rectangle, rows 28-83)
    box(P, 0, 28, 48, 84, 0, 0.6, 0.12, M["STONE"])
    g = 0.14  # half joint
    # dressed blocks west (cols 0-3: col 3 is the joint shadow to the plinth rim)
    for a, b in zip(STONE_W_JOINTS, STONE_W_JOINTS[1:]):
        if a >= 69.5:
            continue
        box(P, 0.02, a + g, 3.6, b - g, 0.3, 1.4, 0.3, M["STONE"])
    # dressed blocks east (cols 45-47), beyond the trench
    for a, b in zip(STONE_E_JOINTS, STONE_E_JOINTS[1:]):
        box(P, 45.1, a + g, 47.98, b - g, 0.3, 1.35, 0.3, M["STONE"])
    # south-west apron blocks under and beside the arm (rows 70-83, cols 0-11)
    for c0, r0, c1, r1 in ((0.02, 70.0, 6.0, 74.5), (6.0, 70.0, 11.0, 74.5), (0.02, 74.5, 6.2, 79.5),
                           (6.2, 74.5, 11.0, 79.5), (0.02, 79.5, 3.8, 83.98), (3.8, 79.5, 11.0, 83.98)):
        box(P, c0 + g, r0 + g, c1 - g, r1 - g, 0.3, 1.25, 0.3, M["STONE"])
    # south kerb (rows 82-83) under the grille and the trench mouth
    for c0, c1 in ((11.0, 20.0), (20.0, 32.0), (32.0, 45.1)):
        box(P, c0 + g, 82.0, c1 - g, 83.98, 0.3, 1.1, 0.28, M["STONE"])

    # raised plinth: a base block plus top slabs split by V joints (the sprite's darker joint
    # rows/cols), its west edge chamfered (the bright col-4 rim is that edge catching the light)
    box(P, 3.7, 28.02, 43.0, 70.0, 0.4, 1.9, 0.0, M["PLINTH"])
    gj = 0.12
    for c0, r0, c1, r1 in SLABS:
        ch = 0.42 if c0 < 4 else 0.3
        box(P, c0 + (0 if c0 < 4 else gj), r0 + (0 if r0 < 28.1 else gj), c1 - (0 if c1 > 42.9 else gj),
            r1 - (0 if r1 > 69.9 else gj), 1.5, 2.4, ch, M["PLINTH"])
    # drain channel at the machine's foot (the sprite's black band, rows 58-62, median 1), and a
    # stone slipway rising out of it to the plinth's south edge (rows 63-69, the sprite's 1->9
    # gradient, median 5) beside the arm; east of it the plinth slab stays flat (lit 8-10)
    box(P, 19.6, 57.5, 43.0, 62.8, 0.4, 0.9, 0.05, M["TRENCH"])
    hullpts(P, [(19.75, 62.6, 0.4), (33.5, 62.6, 0.4), (19.75, 69.95, 0.4), (33.5, 69.95, 0.4),
                (19.75, 62.6, 0.95), (33.5, 62.6, 0.95), (19.75, 69.6, 2.4), (33.5, 69.6, 2.4),
                (19.75, 69.95, 2.2), (33.5, 69.95, 2.2)], M["STONE"])
    for r in (64.4, 66.2, 68.0):
        z = 0.95 + (r - 62.6) / 7.0 * 1.45
        hullpts(P, [(20.2, r - 0.3, z - 0.3), (33.1, r - 0.3, z - 0.3), (20.2, r + 0.3, z - 0.2), (33.1, r + 0.3, z - 0.2),
                    (20.2, r - 0.15, z + 0.22), (33.1, r - 0.15, z + 0.22), (20.2, r + 0.15, z + 0.25), (33.1, r + 0.15, z + 0.25)],
                M["STONE_LT"])

    # trench down the east side (cols 43-45) with a dark liner
    box(P, 43.0, 28.02, 45.1, 83.0, 0.0, 0.35, 0.05, M["TRENCH"])

    # sunken grille (rows 70-82, cols 20-43): dark pit, stone frame, free-standing ribs on a spine
    box(P, 20.0, 70.0, 43.0, 82.0, 0.0, 0.2, 0.05, M["TRENCH"])
    box(P, 19.4, 70.0, 20.6, 82.0, 0.0, 1.0, 0.2, M["STONE"])
    box(P, 20.0, 81.2, 43.0, 82.2, 0.0, 0.9, 0.2, M["STONE"])
    box(P, 20.0, 69.9, 43.0, 70.8, 0.0, 1.0, 0.15, M["STONE"])
    box(P, 20.6, 75.7, 42.6, 76.4, 0.25, 0.55, 0.1, M["RIB"])
    for c in (24, 28, 32, 36, 40):
        box(P, c + 0.05, 70.7, c + 0.95, 81.3, 0.25, 0.85, 0.22, M["RIB"])


# --- the machine ---------------------------------------------------------------------------------

Z0 = 2.4  # plinth top


def machine(P):
    # --- main body, left half (cols 6-24, rows 45-57): rounded lit west edge, panel joint at row 54,
    # a sloped south face down to the plinth (rows 56.5-60)
    zt = 6.4
    # west part (cols 6-13.5) with a generous west chamfer (the lit col 6-7 edge)
    hullpts(P, [(c, r, z) for c in (6.0, 13.6) for r in (45.0, 56.4) for z in (Z0,)] +
            [(6.0, 45.6, zt - 1.1), (6.0, 56.0, zt - 1.1), (7.1, 45.0, zt - 0.2), (7.1, 56.4, zt - 0.2),
             (7.5, 45.4, zt), (7.5, 53.8, zt), (13.6, 45.4, zt), (13.6, 53.8, zt), (13.6, 45.0, zt - 0.3),
             (13.6, 56.4, zt - 0.4)], M["BODY"])
    # east part of the left body (cols 17.5-24)
    box(P, 17.5, 45.0, 24.2, 53.9, Z0, zt, 0.35, M["BODY"])
    # floor of the gantry slot between them (rows 45-53, dark)
    box(P, 13.4, 44.8, 17.7, 54.0, Z0, 4.6, 0.2, M["DECK"])
    # the strip south of the row-54 joint, full width (cols 6-24) with the sloped front
    hullpts(P, [(6.1, 54.2, Z0), (24.2, 54.2, Z0), (6.1, 60.2, Z0), (24.2, 60.6, Z0),
                (6.3, 54.2, zt - 0.4), (24.2, 54.2, zt - 0.3), (6.8, 54.5, zt - 0.1), (24.0, 54.5, zt - 0.1),
                (6.8, 56.6, zt - 0.1), (24.0, 56.8, zt - 0.1)], M["BODY"])
    # --- body right half (cols 24-39): low recessed deck at rows 43.5-49 with gussets, full height
    # block rows 48.6-56.6, sloped south face to row 60
    box(P, 24.0, 43.4, 35.2, 49.0, Z0, 4.4, 0.25, M["BODY_DK"])
    for c0, c1 in ((28.9, 29.9), (31.0, 32.0), (33.8, 35.0)):
        box(P, c0, 43.6, c1, 48.8, 4.0, 6.2, 0.18, M["BODY"])
    hullpts(P, [(24.0, 48.6, Z0), (39.0, 48.6, Z0), (24.0, 60.6, Z0), (38.8, 60.2, Z0),
                (24.0, 48.6, 6.3), (39.0, 48.6, 6.1), (24.2, 48.9, 6.6), (38.6, 48.9, 6.6),
                (24.2, 56.6, 6.6), (38.6, 56.6, 6.6), (24.0, 56.9, 6.3), (39.0, 56.9, 6.1)], M["BODY"])
    # dark skirt along the foot of the south faces (the sprite's darkest brown rows 58-60)
    hullpts(P, [(6.3, 59.6, Z0), (38.6, 59.6, Z0), (6.3, 61.0, Z0), (38.6, 60.8, Z0),
                (6.3, 59.6, 3.4), (38.6, 59.6, 3.4), (6.3, 60.3, 3.4), (38.6, 60.1, 3.4)], M["SKIRT"])
    # recess left of the lower brass plate (rows 54-56, cols 29-32) and the plate itself
    box(P, 28.8, 53.6, 32.6, 56.4, 5.4, 6.62, 0.12, M["SKIRT"])
    box(P, 32.8, 51.8, 36.6, 56.2, 6.3, 7.05, 0.22, M["BRASS"])
    for c, r in ((33.5, 52.5), (35.9, 52.5), (33.5, 55.5), (35.9, 55.5)):
        cyl_z(P, c, r, 0.32, 6.9, 7.25, M["BOLT"], n=6)
    # panel joints on the right body top (blueprint lines): a groove at row 52.7 cols 24-32
    box(P, 24.3, 52.5, 32.4, 52.9, 6.45, 6.75, 0.0, M["SKIRT"])

    # bolted flange seam between the two cast housings at col 22 (the sprite's seam)
    box(P, 21.75, 48.4, 22.25, 56.2, zt - 0.15, zt + 0.12, 0.0, M["SKIRT"])
    for r in (49.5, 52.5, 55.5):
        cyl_z(P, 22.0, r, 0.3, zt + 0.1, zt + 0.4, M["BOLT"], n=6)
    # access hatch on the west body top, bolted
    box(P, 7.9, 46.2, 12.8, 52.8, 6.2, 6.75, 0.22, M["BODY"])
    for c, r in ((8.5, 46.8), (12.2, 46.8), (8.5, 52.2), (12.2, 52.2)):
        cyl_z(P, c, r, 0.28, 6.6, 6.95, M["BOLT"], n=6)
    # access cover on the right body top (cols 25-32, rows 49.4-52.2)
    box(P, 25.0, 49.4, 32.2, 52.2, 6.4, 6.9, 0.2, M["BODY"])
    # drive coupling from the gearbox's south face over the recessed deck
    cyl_y(P, 26.6, 6.4, 43.4, 46.4, 1.05, M["BRASS_DK"], n=12, ch=0.15)
    cyl_y(P, 26.6, 6.4, 45.4, 46.2, 1.35, M["BRASS_NUT"], n=12, ch=0.12)

    # --- connector bridging gantry and gearbox (cols 19.5-24, rows 42-48)
    box(P, 19.4, 41.8, 24.4, 48.0, Z0, 7.0, 0.35, M["BODY"])

    # --- gearbox (upper block, cols 24-39, rows 36-44), the tallest machine block
    box(P, 24.0, 36.0, 39.0, 43.6, Z0, 9.0, 0.45, M["GEARBOX"])
    # brass cover on it (cols 28-33, rows 37-43): flat top, its south half a bevel (rows 40-42 darker)
    hullpts(P, [(28.0, 37.0, 8.8), (33.0, 37.0, 8.8), (28.0, 42.8, 8.8), (33.0, 42.8, 8.8),
                (28.2, 37.2, 9.6), (32.8, 37.2, 9.6), (28.2, 39.8, 9.6), (32.8, 39.8, 9.6),
                (28.2, 42.6, 9.1), (32.8, 42.6, 9.1)], M["BRASS_PL"])
    for c, r in ((28.7, 37.8), (32.3, 37.8)):
        cyl_z(P, c, r, 0.32, 9.4, 9.85, M["BOLT"], n=6)
    # gearbox side ribs on the east face (col 38-39 darker = east face), and a shaft boss west
    for r in (37.5, 40.0, 42.5):
        box(P, 38.6, r - 0.4, 39.5, r + 0.4, 3.0, 8.4, 0.15, M["GEARBOX"])
    # --- brass reservoir behind it (cols 24.5-34, rows 28-36), strap at rows 34.4-35.4
    box(P, 24.4, 28.05, 34.0, 36.2, Z0, 8.2, 0.55, M["BRASS"])
    box(P, 24.2, 34.4, 34.2, 35.4, Z0, 8.4, 0.2, M["BRASS_DK"])
    box(P, 25.2, 30.8, 33.2, 31.2, 8.1, 8.3, 0.0, M["BRASS_DK"])  # lid seam
    cyl_z(P, 31.6, 29.7, 0.75, 8.0, 8.9, M["BRASS_NUT"], n=10, ch=0.15)  # filler cap

    # --- the gantry (cols 11-19, rows 28.5-53): two box rails, a dark deck with a pipe slot and an
    # open hatch to a black well, cross ties, a valve block
    zr = 7.4
    box(P, 11.0, 28.6, 13.2, 53.6, Z0, zr, 0.4, M["RAIL"])
    box(P, 17.6, 28.6, 19.4, 53.6, Z0, zr, 0.35, M["RAIL"])
    box(P, 13.0, 28.8, 17.8, 44.8, Z0, 2.7, 0.0, M["WELL"])  # black well floor
    box(P, 13.1, 28.8, 15.6, 33.6, 4.4, 5.1, 0.12, M["DECK"])  # deck either side of the slot
    box(P, 16.6, 28.8, 17.7, 33.6, 4.4, 5.1, 0.12, M["DECK"])
    box(P, 13.1, 36.6, 17.7, 44.8, 4.4, 5.1, 0.12, M["DECK"])
    for r0, r1 in ((35.9, 37.0), (43.0, 45.0)):
        box(P, 10.9, r0, 19.5, r1, 4.8, zr + 0.25, 0.25, M["TIE"])
    box(P, 10.9, 30.4, 19.5, 31.2, 5.6, zr + 0.15, 0.2, M["RAIL"])  # light tie at the head
    box(P, 10.8, 51.6, 19.6, 54.2, 5.8, zr + 0.3, 0.35, M["TIE"])  # header the rails end in
    # valve block with a hex cap (rows 38.5-42.5, cols 13.6-17.4)
    box(P, 13.6, 38.4, 17.4, 42.6, 4.8, 6.6, 0.3, M["TIE"])
    cyl_z(P, 15.3, 40.2, 0.9, 6.4, 7.2, M["BRASS_NUT"], n=6, ch=0.15)

    # --- left extension (cols 6-13, rows 56-64): a lower housing with its SW corner cut on the
    # sprite's stair diagonal
    prism(P, [(6.1, 56.4), (13.2, 56.4), (13.2, 64.0), (10.8, 64.0), (6.1, 60.6)], Z0, 4.8, 0.35, M["BODY_DK"])


# --- the arm --------------------------------------------------------------------------------------

def arm(P):
    # cradle cheeks either side of the ram (cols 11-13, 17.6-19.6; rows 56.6-68)
    box(P, 10.9, 56.6, 13.2, 68.0, Z0, 5.6, 0.45, M["BODY"])
    box(P, 17.5, 56.6, 19.7, 68.0, Z0, 5.6, 0.35, M["BODY"])
    box(P, 13.0, 56.6, 17.7, 67.6, Z0, 3.6, 0.1, M["SKIRT"])  # cradle floor
    # polished ram (cols 13-17.5): a brass cylinder, its glint (col 14) is sheen; gland nut rows 65.6-67.6
    cyl_y(P, 15.25, 5.35, 56.0, 66.0, 2.25, M["BRASS_DK"], n=20, ch=0.2)
    cyl_y(P, 15.25, 5.35, 65.6, 67.8, 2.45, M["BRASS_NUT"], n=12, ch=0.3)
    # clevis pin through the cheeks at the ram's root
    cyl_x(P, 10.6, 20.0, 58.4, 4.6, 0.75, M["BRASS_NUT"], n=12, ch=0.15)
    # yoke across the plinth edge (rows 67.6-70.2), lit top
    box(P, 10.8, 67.6, 19.8, 70.3, 0.6, 6.5, 0.5, M["YOKE"])
    # pump head on the stone apron (rows 70-76) with a joint at row 73
    box(P, 11.0, 70.2, 19.6, 73.0, 0.6, 4.8, 0.5, M["HEAD"])
    box(P, 11.0, 73.2, 19.6, 76.0, 0.6, 4.8, 0.5, M["HEAD"])
    # brass flange band (rows 76-79): rounded, wider
    ring_loft(P, [(75.8, 15.3, 4.2, 2.4, 2.4), (76.3, 15.3, 4.75, 2.4, 2.85), (78.6, 15.3, 4.75, 2.4, 2.85),
                  (79.1, 15.3, 4.2, 2.4, 2.4)], M["BRASS"], n=16)
    box(P, 11.0, 75.9, 19.6, 79.0, 0.6, 2.6, 0.1, M["BRASS"])  # flat foot under it
    # outlet cap (rows 79-82)
    box(P, 11.3, 79.0, 19.4, 82.0, 0.6, 3.5, 0.5, M["HEAD"])
    cyl_y(P, 15.3, 2.2, 81.8, 82.6, 1.0, M["HEAD"], n=10, ch=0.15)  # outlet stub


# --- assembly -------------------------------------------------------------------------------------

def finish(P, mats, coll):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.transform(bm, matrix=Matrix.Scale(PX, 4), verts=bm.verts)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(P.smooth_angle))
    return obj


def apply_mods(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    P = T.Part(NAME, smooth_angle=32.0)
    platform(P)
    machine(P)
    arm(P)
    vessel(P)
    obj = finish(P, mats, coll)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    apply_mods(obj)
    return obj, coll


def layout(sprite):
    return [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]


def bake_maps(obj, out_dir, size=1024, samples=48):
    """AO/edge colour multiplier + roughness/metal map (usp_talon.bake_maps as in newsh2-115),
    wired into every palette material (Base Color = map x palette)."""
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
        print(f"{NAME}: no GPU bake", err)
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
    col_img = bpy.data.images.new("nshp267_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nshp267_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(dict.fromkeys(me.materials))  # palette_material shares a material between parts
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

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.25
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
            nt.links.new(comb.outputs[0], em.inputs["Color"])
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
    for m in mats:
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


TIER_HOME = "newshp-115"


def split_keep_tiers(obj, lay, coll):
    """common.split_assembly, except that the vessel's tier faces (the per-frame lit materials,
    tyrian_frame_pal) all stay whole in newshp-115, the piece whose sprite frames animate them. The
    bottom tier's south dome runs 1.75 px past the row-28 cut; cut there, that tip went to
    newshp-229, which always draws frame 229, so it never lit on frame 115 and drew a dark band
    across the bowl's south tip."""
    def tier_idx(me):
        return {i for i, m in enumerate(me.materials) if m and "-tier_" in m.name}

    rest_me = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(rest_me)
    tiers = tier_idx(rest_me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in tiers], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(rest_me)
    bm.free()
    rest = bpy.data.objects.new(NAME + "_rest", rest_me)
    coll.objects.link(rest)
    pieces = common.split_assembly(rest, lay, coll)
    bpy.data.objects.remove(rest, do_unlink=True)
    _n, cx, cy = next(e for e in lay if e[0] == TIER_HOME)
    tier_me = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(tier_me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in tiers], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.translate(bm, vec=(-cx / 12, cy / 12, 0), verts=bm.verts)
    bm.to_mesh(tier_me)
    bm.free()
    home = pieces[TIER_HOME]
    t_obj = bpy.data.objects.new(NAME + "_tiers", tier_me)
    coll.objects.link(t_obj)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    home.select_set(True)
    t_obj.select_set(True)
    bpy.context.view_layer.objects.active = home
    bpy.ops.object.join()
    for name, piece in pieces.items():
        left = [m.name for m in piece.data.materials if m and "-tier_" in m.name
                and any(p.material_index == piece.data.materials.find(m.name) for p in piece.data.polygons)]
        print(f"{NAME}: {name} tier materials in use: {left}")
    return pieces


def split_open(obj, lay, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells)."""
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


# Outline shell (D51). Its source leaves out the bolt heads: decimated, the shell bridged from bolt
# to bolt in straight triangles that ran above the plates and the flange between them, and their
# back faces drew as black slashes across the plates. A coarse voxel and a tight face budget let the decimated shell wander above
# the large flat plates by more than a small inset, and its back faces drew as black scratches on
# the top view; a finer voxel, more faces and a deeper inset keep it under every flat face.
SHELL_VOXEL, SHELL_FACES, SHELL_INSIDE = 0.014, 14000, 0.015


def slab_fill():
    """Boxes (px: c0, r0, c1, r1, z0, z1) that fill the plinth's V joints for the outline shell.
    Each slab's box reaches its nominal edge where another slab lies across the joint and stops
    0.45 px short (inside the slab's chamfer) where the joint is an outer edge."""
    def in_slab(c, r):
        return any(c0 < c < c1 and r0 < r < r1 for c0, r0, c1, r1 in SLABS)

    def shared(pts):
        return all(in_slab(c, r) for c, r in pts)
    out = []
    for c0, r0, c1, r1 in SLABS:
        cs = [c0 + (c1 - c0) * k / 8 for k in range(1, 8)]
        rs = [r0 + (r1 - r0) * k / 8 for k in range(1, 8)]
        a = c0 if shared([(c0 - 0.4, r) for r in rs]) else c0 + 0.45
        b = c1 if shared([(c1 + 0.4, r) for r in rs]) else c1 - 0.45
        n = r0 if shared([(c, r0 - 0.4) for c in cs]) else r0 + 0.45
        s_ = r1 if shared([(c, r1 + 0.4) for c in cs]) else r1 - 0.45
        out.append((a, n, b, s_, 1.6, 2.39))
    return out


# The flat stone pieces need far fewer shell faces than the machine (cost: the shells were twice
# the model's triangles). Thinned after the split, with the cut edges held so neighbouring shells
# still meet.
SHELL_PIECE_FACES = {"newshp-269": 1100, "newshp-231": 2400}


def thin_shell(s, faces):
    if not faces or len(s.data.polygons) <= faces:
        return
    me = s.data
    grp = s.vertex_groups.new(name="free")
    edge_faces = {}
    for poly in me.polygons:
        for key in poly.edge_keys:
            edge_faces[key] = edge_faces.get(key, 0) + 1
    border = {v for key, n in edge_faces.items() if n == 1 for v in key}
    grp.add([v.index for v in me.vertices if v.index not in border], 1.0, "REPLACE")
    dec = s.modifiers.new("thin", "DECIMATE")
    dec.ratio = faces / len(me.polygons)
    dec.vertex_group = "free"
    dec.vertex_group_factor = 1000.0
    apply_mods(s)
    s.vertex_groups.clear()


def shell_source(obj):
    """A mesh copy of `obj` without the bolt heads and with the plinth's slab joints filled (the
    outline shell's source)."""
    me = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == M["BOLT"]], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # The slab joints are V grooves; the shell's inverted hull folds in each one and drew it as a
    # hard black line (the sprite's joints are a step or two darker, which the grooves' own shading
    # gives), most visibly the long col-21 joint beside the gantry riser.
    # Likewise the shallow crease where the left body's top meets the strip south of its row-54
    # joint drew as broken dashes across the body.
    zt = 6.4
    for c0, r0, c1, r1, z0, z1 in slab_fill() + [(7.2, 53.4, 23.8, 56.3, Z0, zt - 0.14)]:
        vs = [bm.verts.new((X(c) * PX, Y(r) * PX, z * PX)) for c in (c0, c1) for r in (r0, r1) for z in (z0, z1)]
        bmesh.ops.convex_hull(bm, input=vs)
    bm.to_mesh(me)
    bm.free()
    return me


def make_shell(src_me, coll):
    src = bpy.data.objects.new(NAME + "_shellsrc", src_me)
    coll.objects.link(src)
    shell = common.outline_shell(src, coll, voxel=SHELL_VOXEL, faces=SHELL_FACES, inside=SHELL_INSIDE)
    bpy.data.objects.remove(src, do_unlink=True)
    return shell


def seam_normals(piece, whole, cx, cy):
    """Give a piece the whole mesh's own (weighted) normals by data transfer, so neighbouring
    pieces shade as one surface across the cuts; a per-piece WEIGHTED_NORMAL weighs the cut caps and
    leaves a step in the shading at every piece boundary."""
    me = piece.data
    # The caps split_assembly fills at the cuts share smooth edges with the faces they close, so
    # they would join those faces' normal fans (custom normals are stored per fan) and drag the
    # transferred normals off. Make every cap edge sharp and the caps flat: their own fans.
    def on_cut(poly):
        vs = [me.vertices[v].co for v in poly.vertices]
        return all(abs(abs(co.x) - 1.0) < 1e-4 for co in vs) or all(abs(abs(co.y) - 14 / 12) < 1e-4 for co in vs)
    caps = [poly for poly in me.polygons if on_cut(poly)]
    sharp = me.attributes.get("sharp_edge") or me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    for poly in caps:
        poly.use_smooth = False
    edge_of = {e.key: e.index for e in me.edges}
    for poly in caps:
        for key in poly.edge_keys:
            sharp.data[edge_of[key]].value = True
    whole.location = (-cx / 12, cy / 12, 0)
    bpy.context.view_layer.update()
    mod = piece.modifiers.new("seam", "DATA_TRANSFER")
    mod.object = whole
    mod.use_loop_data = True
    mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "NEAREST_POLYNOR"
    apply_mods(piece)
    whole.location = (0, 0, 0)
    bpy.context.view_layer.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    obj, coll = build(sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: whole {tris} triangles")
    if "--views" in argv:  # review renders (flat palette, before the bake); needs the scratch views.py
        sys.path.insert(0, argv[argv.index("--views-lib") + 1])
        import views
        shell0 = make_shell(shell_source(obj), coll)
        views.render_all(obj, shell0, argv[argv.index("--views") + 1])
        bpy.data.objects.remove(shell0, do_unlink=True)
    src_me = shell_source(obj)  # before the bake, which may rearrange the material slots
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_maps(obj, tempfile.mkdtemp(prefix="nshp267_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), after the bake so its occlusion rays never hit it.
    shell = make_shell(src_me, coll)
    lay = layout(sprite)
    pieces = split_keep_tiers(obj, lay, coll)
    shells = split_open(shell, lay, coll, "_outline")
    shell.hide_render = True
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for name, cx, cy in lay:
        p = pieces[name]
        seam_normals(p, obj, cx, cy)
        s = shells[name]
        thin_shell(s, SHELL_PIECE_FACES.get(name))
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, s], f"enemies/{name}", data["sprites"], image_format=fmt)
        pt = sum(len(q.vertices) - 2 for q in p.data.polygons)
        print(f"{NAME}: piece {name} at ({cx}, {cy}) px: {pt} triangles; shell {len(s.data.polygons)} faces")


if __name__ == "__main__":
    main()
