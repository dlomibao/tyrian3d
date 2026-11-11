"""Grey ridge-topped block stencilled 26 on a dark grilled plinth (newshs.shp 13|15 over 51|53 over
89|91: six 2x2 pieces, one 48 x 84 px object of the grey stone fortress set). Design B: silhouette
and readability from the small tilted game camera first, then detail.

Read off the sprite (sprite px: c = column east, r = row south (front, the player), z up; one px
= 1/12 u; origin = the assembly centre c 24, r 42):
- THE BLOCK: an armoured gable-roofed bunker, chevron in plan (D74 inner mask): its back end points
  north (apex r 11.9 on the ridge c 24, eave corners r 17.2 / 17.8), its front end is the same
  chevron notched back (r 52 at the ridge, 57.3 / 58 at the eaves). Eaves at c 7 / 41. Roof pitch
  ~17 deg (eave z 5, ridge z 10.2) so the lit west slope / shaded east slope of the sprite comes
  from the light, not paint (both slopes 9; rubric: a darker symmetric half is shadow).
- ROOF ARMOUR: separate chamfered plates on the slopes with real gaps between them: a back band
  (to the joint at r 22.5) and a front band (from r 42.5) cut at the sprite's seam columns (back
  10/14/19 | 28/32/35, front 11/17 | 28/32/36), the middle plate of each slope carries the
  stencilled 26 (the sprite's own numeral pixels, smoothed 2x, one paint 12 both sides).
- RIDGE CAP: a chamfered capping bar on the ridge (the sprite's bright 10/11 line, cols 22-23).
- The block's walls stand under a 0.6 px eave overhang; the front wall (under a 1 px hood) is the
  dark mouth of the sprite's rows 52-58 (paint 3), over a trench (2) that runs round the block as
  a gutter (the sprite's dark col 6 / col 41). Hatches on the flanks, a service door on each back
  face (never seen by the game camera; plain).
- THE PLINTH: dark grey cast rims (6) with chamfers (the lit col 4 / shaded cols 42-43 are those
  chamfers in light and shade), the deck (2) in front of the block carrying the equipment row
  (4): a box, a split housing, the louvred vent (frame 4, well 1, bars 3), the open port (well 1
  under a lintel) and a grooved box; a kerb (6) whose lit south bevel is the sprite's row 69.
- THE GRILLE RAMP: a bed (2) sloping from the kerb down to the floor, eight ribs (4) on the
  sprite's 4-px pitch (lit columns 8, 12, ... 36), cheeks (5), a sill (4) at row 79.
- NO FLOOR (D129): the sprite's stone floor round the block is the tile's ground, which the game
  draws in HD (the plate painted per pixel from the sprite, lib_b073.floor, showed as grey pixel
  cells on it). The machine stands on the ground.
Underside: closed, plain.

Seen in episodes 1-3 (levels 1.2, 2.4, 3.2); damaged frames 17/55 show this intact model (D87).
Built whole and cut into the six pieces (body, outline shell) with common.split_assembly.
Texture: AO/roughness bake only, no concept projection (D50, D65).

Run: blender -b --factory-startup -P assets/blender/enemies/assembly-newshs-13.py [-- --no-bake]
(also writes a combined preview glb to $NSHS13_PREVIEW if set).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
WT = common.repo_root(__file__)
import lib_b073 as L  # noqa: E402  (read only: Grid, Mats)
import usp_talon as T  # noqa: E402

import os  # noqa: E402
OUT = Path(os.environ["NSHS13_PREVIEW"]) if os.environ.get("NSHS13_PREVIEW") else None
NAME = "assembly-newshs-13"
TAG = "nshs13"
PIECES = [["newshs-13", "newshs-15"], ["newshs-51", "newshs-53"], ["newshs-89", "newshs-91"]]
LAYOUT = [("newshs-13", -12, -28), ("newshs-15", 12, -28), ("newshs-51", -12, 0), ("newshs-53", 12, 0),
          ("newshs-89", -12, 28), ("newshs-91", 12, 28)]
SMOOTH = 30.0

# --- dimensions (sprite px) -------------------------------------------------------------------
EAVE, RIDGE = 5.6, 10.8          # roof surface under the plates at the eave line and the ridge
SLAB = 0.8                       # roof slab thickness at the fascia
PT, PCH = 0.5, 0.2               # plate thickness above the slab, plate top chamfer
GAP = 0.18                       # half gap between plates
CL, CR, CM = 7.0, 41.0, 24.0     # eaves, ridge
BACK = (17.2, 11.9, 17.8)        # back chevron r at c 7, 24, 41
FRONT = (57.3, 52.0, 58.0)       # front chevron r at c 7, 24, 41
WALL_IN = 0.6                    # wall inset under the eave
HOOD = 1.1                       # front wall set back under the roof's front edge
DECK, KERB = 1.8, 2.7            # plinth deck top, kerb top
TRENCH = 0.6                     # trench / gutter floor
P0, P1 = 4.0, 44.0               # plinth columns
PN, PS = 28.0, 69.6              # plinth rows (north end at the piece seam, south at the ramp)
GW, GE = 6.2, 41.8               # gutters: west c 6.2-7.6, east c 40.4-41.8
EQ_N = 58.5                      # equipment row north edge (trench south edge)
KN = 65.6                        # kerb north face
RAMP = (69.6, 79.0, 2.1, 0.6)    # ramp r0, r1, z0, z1
SILL = (78.6, 80.2, 0.95)
RIBS = [8.5 + 4 * k for k in range(8)]
SEAMS_B = {"L": [10, 14, 19], "R": [28, 32, 35]}
SEAMS_F = {"L": [11, 17], "R": [28, 32, 36]}
JOINT_B, JOINT_F = 22.5, 42.5
CAP_W, CAP_H = 1.15, 0.75        # ridge cap half width, height above the plates


def X(c):
    return (c - 24.0) / 12.0


def Y(r):
    return (42.0 - r) / 12.0


def Z(z):
    return z / 12.0


def back_r(c):
    return BACK[1] + (BACK[0] - BACK[1]) * (CM - c) / (CM - CL) if c <= CM else \
        BACK[1] + (BACK[2] - BACK[1]) * (c - CM) / (CR - CM)


def front_r(c):
    return FRONT[1] + (FRONT[0] - FRONT[1]) * (CM - c) / (CM - CL) if c <= CM else \
        FRONT[1] + (FRONT[2] - FRONT[1]) * (c - CM) / (CR - CM)


def roof_z(c):
    """Slab top (under the plates) at column c."""
    t = (c - CL) / (CM - CL) if c <= CM else (CR - c) / (CR - CM)
    return EAVE + (RIDGE - EAVE) * max(0.0, min(1.0, t))


# --- mesh building ----------------------------------------------------------------------------

class Mesh:
    """A bmesh in sprite px. Closed solids get their normals from recalc (per island); open
    decals are tagged 'up' and face up."""

    def __init__(self):
        self.bm = bmesh.new()
        self.up = self.bm.faces.layers.int.new("up")

    def v(self, p):
        return self.bm.verts.new((X(p[0]), Y(p[1]), Z(p[2])))

    def face(self, pts_or_verts, mat, up=False):
        vs = [p if isinstance(p, bmesh.types.BMVert) else self.v(p) for p in pts_or_verts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = False
        f[self.up] = 1 if up else 0
        return f

    def solid(self, rings, side, top=None, bottom=None):
        """Loops of (c, r, z), same length, bridged in order; the first and last loops capped.
        side: a material or a list per segment (segment i joins point i and i+1)."""
        vr = [[self.v(p) for p in ring] for ring in rings]
        n = len(rings[0])
        for a, b in zip(vr, vr[1:]):
            for i in range(n):
                j = (i + 1) % n
                m = side[i] if isinstance(side, (list, tuple)) else side
                self.face([a[i], a[j], b[j], b[i]], m)
        self.face(vr[0], bottom if bottom is not None else (side if isinstance(side, int) else side[0]))
        self.face(vr[-1], top if top is not None else (side if isinstance(side, int) else side[0]))

    def prism(self, poly, z0, z1, side, top=None, ch=0.0, chz=None, bottom=None):
        """A vertical prism over poly [(c, r)], top edge chamfered by ch (chz high)."""
        chz = ch if chz is None else chz
        rings = [[(c, r, z0) for c, r in poly]]
        if ch > 0:
            rings.append([(c, r, z1 - chz) for c, r in poly])
            rings.append([(c, r, z1) for c, r in inset(poly, ch)])
        else:
            rings.append([(c, r, z1) for c, r in poly])
        self.solid(rings, side, top=top, bottom=bottom)

    def box(self, c0, r0, c1, r1, z0, z1, side, top=None, ch=0.0, chz=None):
        self.prism([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, side, top=top, ch=ch, chz=chz)


def area2(poly):
    a = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a += p[0] * q[1] - q[0] * p[1]
    return a


def inset(poly, d):
    """Inward miter offset of a simple polygon by d."""
    n = len(poly)
    s = 1.0 if area2(poly) > 0 else -1.0
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * s, dx / ln * s
        lines.append((a[0] + nx * d, a[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        l1, l2 = lines[(i - 1) % n], lines[i]
        den = l1[2] * l2[3] - l1[3] * l2[2]
        if abs(den) < 1e-9:
            out.append((l2[0], l2[1]))
            continue
        t = ((l2[0] - l1[0]) * l2[3] - (l2[1] - l1[1]) * l2[2]) / den
        out.append((l1[0] + l1[2] * t, l1[1] + l1[3] * t))
    return out


# --- the sprite ---------------------------------------------------------------------------------

def load_composite():
    colors, grid = {}, [[-1] * 48 for _ in range(84)]
    for ri, row in enumerate(PIECES):
        for ci, n in enumerate(row):
            d = common.load_sprite(WT, n)
            colors.update(d["colors"])
            for r, line in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(line):
                    if v >= 0:
                        grid[ri * 28 + r][ci * 24 + c] = v
    return {"name": NAME, "colors": colors, "pixels": grid}, grid


def scale2x(mask):
    """EPX on a binary mask: rounds the stencil's stair steps at half-pixel resolution."""
    h, w = len(mask), len(mask[0])

    def at(r, c):
        return mask[r][c] if 0 <= r < h and 0 <= c < w else 0
    out = [[0] * (2 * w) for _ in range(2 * h)]
    for r in range(h):
        for c in range(w):
            p, a, b, cc, d = at(r, c), at(r - 1, c), at(r, c + 1), at(r, c - 1), at(r + 1, c)
            e0 = a if (cc == a and cc != d and a != b) else p
            e1 = b if (a == b and a != cc and b != d) else p
            e2 = cc if (d == cc and d != b and cc != a) else p
            e3 = d if (b == d and b != a and d != cc) else p
            out[2 * r][2 * c], out[2 * r][2 * c + 1] = e0, e1
            out[2 * r + 1][2 * c], out[2 * r + 1][2 * c + 1] = e2, e3
    return out


# --- parts ---------------------------------------------------------------------------------------

def roof_slab(M, mt):
    """The roof slab: fascia SLAB thick at the eaves, gable top, chevron ends."""
    E0 = EAVE - SLAB
    top = {"BL": (CL, back_r(CL), EAVE), "BA": (CM, BACK[1], RIDGE), "BR": (CR, back_r(CR), EAVE),
           "FR": (CR, front_r(CR), EAVE), "FN": (CM, FRONT[1], RIDGE), "FL": (CL, front_r(CL), EAVE)}
    t = {k: M.v(p) for k, p in top.items()}
    b = {k: M.v((p[0], p[1], E0)) for k, p in top.items()}
    M.face([t["BL"], t["BA"], t["FN"], t["FL"]], mt["slab"])
    M.face([t["BA"], t["BR"], t["FR"], t["FN"]], mt["slab"])
    order = ["BL", "BA", "BR", "FR", "FN", "FL"]
    M.face([b[k] for k in order], mt["soffit"])
    for i, k in enumerate(order):
        k2 = order[(i + 1) % 6]
        M.face([b[k], b[k2], t[k2], t[k]], mt["fascia"])


def plate(M, poly, mat, z_of, t=PT, ch=PCH):
    """A roof plate over plan poly on the slope (z_of(c) = slope), t thick, chamfered top."""
    rings = [[(c, r, z_of(c) - 0.15) for c, r in poly],
             [(c, r, z_of(c) + t - ch) for c, r in poly],
             [(c, r, z_of(c) + t) for c, r in inset(poly, ch)]]
    M.solid(rings, mat)


def strip(c0, c1, lo, hi, g0=GAP, g1=GAP):
    """Plan quad between columns c0..c1 and rows lo(c)..hi(c), inset by the half gaps."""
    a, b = c0 + g0, c1 - g1
    return [(a, lo(a) + GAP), (b, lo(b) + GAP), (b, hi(b) - GAP), (a, hi(a) - GAP)]


def roof_plates(M, mt):
    const = lambda v: (lambda c: v)  # noqa: E731
    for side in ("L", "R"):
        c_out, c_in = (CL, CM - CAP_W + 0.05) if side == "L" else (CM + CAP_W - 0.05, CR)
        lo_c, hi_c = (c_out, c_in)
        # back band, front band: strips at the seams; middle: one plate (carries the 26)
        for seams, lo, hi in ((SEAMS_B[side], back_r, const(JOINT_B)), (SEAMS_F[side], const(JOINT_F), front_r)):
            cuts = [lo_c] + seams + [hi_c]
            for a, b in zip(cuts, cuts[1:]):
                g0 = 0.0 if a == lo_c and side == "L" else GAP
                g1 = 0.0 if b == hi_c and side == "R" else GAP
                plate(M, strip(a, b, lo, hi, g0, g1), mt["plate"], roof_z)
        g0 = 0.0 if side == "L" else GAP
        g1 = 0.0 if side == "R" else GAP
        plate(M, strip(lo_c, hi_c, const(JOINT_B), const(JOINT_F), g0, g1), mt["plate"], roof_z)


def ridge_cap(M, mt):
    top = RIDGE + PT + CAP_H
    sec = [(-CAP_W, None, -0.1), (-CAP_W, top - 0.3, 0), (-CAP_W + 0.35, top, 0), (CAP_W - 0.35, top, 0),
           (CAP_W, top - 0.3, 0), (CAP_W, None, -0.1)]

    def ring(rf, d):
        out = []
        for dc, z, dz in sec:
            c = CM + dc
            zz = z if z is not None else roof_z(c) + PT + dz
            out.append((c, rf(c) + d, zz))
        return out
    M.solid([ring(back_r, 0.35), ring(front_r, -0.25)], mt["ridge"])
    # bolt heads along the cap
    for r in range(16, 52, 6):
        M.box(CM - 0.35, r - 0.35, CM + 0.35, r + 0.35, top - 0.1, top + 0.22, mt["bolt"], ch=0.12)


def bolt(M, mt, c, r, z, s=0.3, h=0.2):
    M.box(c - s, r - s, c + s, r + s, z - 0.1, z + h, mt["bolt"], ch=0.1)


def eave_bolts(M, mt):
    """Bolt heads (paint 10) along the eave edges at the plate corners, and down the plinth rims."""
    for c in (CL + 0.55, CR - 0.55):
        for r in (back_r(c) + 1.0, JOINT_B - 1.0, JOINT_B + 1.0, JOINT_F - 1.0, JOINT_F + 1.0, front_r(c) - 1.0):
            bolt(M, mt, c, r, roof_z(c) + PT - 0.05, s=0.28)
    for r in (31.0, 37.0, 43.0, 49.0, 55.0, 61.0):
        for c in (P0 + 1.5, P1 - 1.5):
            bolt(M, mt, c, r, DECK, s=0.28)


def numerals(M, grid, mt):
    """The stencilled 26 on the middle plates: the sprite's numeral pixels, scale2x, painted."""
    regions = (("L", 8, 22, lambda i: i >= 11 and i <= 15 or i in (108, 109)),
               ("R", 26, 41, lambda i: 10 <= i <= 15 or i in (106, 108)))
    r0, r1 = 23, 42
    for side, c0, c1, is_ink in regions:
        mask = [[1 if is_ink(grid[r][c]) else 0 for c in range(c0, c1)] for r in range(r0, r1)]
        big = scale2x(mask)
        for rr, line in enumerate(big):
            cc = 0
            while cc < len(line):
                if not line[cc]:
                    cc += 1
                    continue
                e = cc
                while e < len(line) and line[e]:
                    e += 1
                ca, cb = c0 + cc / 2, c0 + e / 2
                ra, rb = r0 + rr / 2, r0 + (rr + 1) / 2
                z = lambda c: roof_z(c) + PT + 0.03  # noqa: E731
                M.face([(ca, rb, z(ca)), (cb, rb, z(cb)), (cb, ra, z(cb)), (ca, ra, z(ca))], mt["numeral"], up=True)
                cc = e


def body(M, mt):
    """Walls under the roof: west/east inset WALL_IN, back faces inset, front wall under the hood."""
    E0 = EAVE - SLAB + 0.05
    a, b = CL + WALL_IN, CR - WALL_IN
    poly = [(a, back_r(a) + WALL_IN), (CM, BACK[1] + WALL_IN), (b, back_r(b) + WALL_IN),
            (b, front_r(b) - HOOD), (CM, FRONT[1] - HOOD), (a, front_r(a) - HOOD)]
    w, f = mt["wall"], mt["front"]
    M.prism(poly, 0.0, E0, [w, w, w, f, f, w], top=w)
    # a parting band round the walls (cast course) at z 2.4-2.9, proud 0.15
    band = inset(poly, -0.15)
    M.prism(band, 2.4, 2.9, [w, w, w, f, f, w], top=w)
    # flank hatches (raised frames) and back service doors
    for r0, r1 in ((31.0, 37.0), (44.0, 50.0)):
        for c, s in ((a, -1), (b, 1)):
            M.box(min(c, c + s * 0.18), r0, max(c, c + s * 0.18), r1, 3.05, 4.05, mt["hatch"])
    # back faces: a service door low on each wall, a louvred vent high on each gable of the slab
    for sgn in (-1, 1):
        cA = CM + sgn * 9.0
        rw = back_r(cA) + WALL_IN
        face_box(M, sgn, cA, rw, 1.6, 0.0, 3.7, 0.12, mt["hatch"])          # door leaf
        face_box(M, sgn, cA, rw, 1.9, 3.7, 4.0, 0.2, mt["hatch"])           # door lintel
        cV = CM + sgn * 5.0
        rv = back_r(cV)
        zv = roof_z(cV) - 1.2
        face_box(M, sgn, cV, rv, 1.9, zv - 2.2, zv, 0.12, mt["fascia"])    # vent frame
        face_box(M, sgn, cV, rv, 1.5, zv - 1.9, zv - 0.3, 0.05, mt["well"])  # dark well
        for k in range(3):
            z = zv - 1.75 + k * 0.55
            face_box(M, sgn, cV, rv, 1.45, z, z + 0.25, 0.22, mt["louvre"])


def face_box(M, sgn, c, r, half_u, z0, z1, out, mat):
    """A box on a back (chevron) face: centred on (c, r) on the face line, half_u along the face,
    from out (outward) to -0.3 (into the wall), z0..z1."""
    du, dr = (CM - CL), (BACK[1] - BACK[0]) if sgn < 0 else (BACK[2] - BACK[1])
    if sgn > 0:
        du = CR - CM
    ln = math.hypot(du, dr)
    u = (du / ln, dr / ln)
    n = (u[1], -u[0])  # outward (north)
    if n[1] > 0:
        n = (-n[0], -n[1])
    pts = []
    for a, b in ((-half_u, -0.3), (half_u, -0.3), (half_u, out), (-half_u, out)):
        pts.append((c + u[0] * a + n[0] * b, r + u[1] * a + n[1] * b))
    M.prism(pts, z0, z1, mat)


def plinth(M, mt):
    p, k = mt["plinth"], mt["kerb"]
    # gutters and the trench floor (around and in front of the block)
    M.box(GW, PN, CL + WALL_IN + 0.05, EQ_N, 0.0, TRENCH, mt["trench"])
    M.box(CR - WALL_IN - 0.05, PN, GE, EQ_N, 0.0, TRENCH, mt["trench"])
    trench = [(CL + WALL_IN, front_r(CL + WALL_IN) - HOOD - 0.1), (CM, FRONT[1] - HOOD - 0.1),
              (CR - WALL_IN, front_r(CR - WALL_IN) - HOOD - 0.1), (CR - WALL_IN, EQ_N), (CL + WALL_IN, EQ_N)]
    M.prism(trench, 0.0, TRENCH, mt["trench"])
    # deck block (equipment stands on it) and the kerb
    # the deck band cut into three kerbed slabs (joints at c 18.2 and 34.75) on a dark base
    M.box(GW, EQ_N, GE, KN, 0.0, TRENCH + 0.3, mt["trench"])
    for a, z in ((GW, 18.05), (18.35, 34.6), (34.9, GE)):
        M.box(a, EQ_N, z, KN, 0.0, DECK, mt["deckside"], top=mt["deck"], ch=0.15)
    M.prism([(GW, KN), (GE, KN), (GE, PS - 1.2), (GW, PS - 1.2)], 0.0, KERB, k)
    # kerb's lit south bevel down to the ramp top
    M.solid([[(GW, PS - 1.2, 0.0), (GE, PS - 1.2, 0.0), (GE, PS, 0.0), (GW, PS, 0.0)],
             [(GW, PS - 1.2, KERB), (GE, PS - 1.2, KERB), (GE, PS, RAMP[2] + 0.2), (GW, PS, RAMP[2] + 0.2)]], k)


def rims_chamfered(M, mt):
    """Rims with a real chamfer: section [outer foot, outer top-chamfer, inner top, inner foot]."""
    p = mt["plinth"]
    for c_out, c_in, d in ((P0, GW, 1), (P1, GE, -1)):
        sec = [(c_out, 0.0), (c_out, DECK - 0.7), (c_out + d * 0.7, DECK), (c_in, DECK), (c_in, 0.0)]
        rings = [[(c, PN, z) for c, z in sec], [(c, PS, z) for c, z in sec]]
        M.solid(rings, p)


def equipment(M, mt):
    d = DECK
    box, top = mt["box"], mt["boxtop"]
    # box A
    M.box(7.2, 59.0, 10.6, 64.9, d - 0.1, 3.5, box, top=top, ch=0.3)
    # split housing B with its lintel
    M.box(11.6, 59.6, 13.9, 64.9, d - 0.1, 3.4, box, top=top, ch=0.25)
    M.box(14.5, 59.6, 18.0, 64.9, d - 0.1, 3.4, box, top=top, ch=0.25)
    M.box(11.4, 58.3, 18.2, 59.6, d - 0.1, 3.8, box, top=top, ch=0.2)
    # louvred vent C: frame bars, dark well, louvre bars
    fr, z1 = mt["frame"], 3.3
    M.box(18.4, 58.9, 27.0, 59.7, d - 0.1, z1, fr, ch=0.15)
    M.box(18.4, 64.2, 27.0, 65.0, d - 0.1, z1, fr, ch=0.15)
    M.box(18.4, 59.7, 19.1, 64.2, d - 0.1, z1, fr, ch=0.12)
    M.box(26.3, 59.7, 27.0, 64.2, d - 0.1, z1, fr, ch=0.12)
    M.box(19.1, 59.7, 26.3, 64.2, d - 0.1, d + 0.3, mt["well"])
    for c in (19.75, 21.55, 23.35, 25.15):
        M.box(c - 0.45, 59.7, c + 0.45, 64.2, d + 0.3, z1 - 0.2, mt["louvre"], ch=0.12)
    # port D: an open hatch (dark well) under a lintel
    M.box(27.3, 58.2, 34.6, 59.9, d - 0.1, 4.0, box, top=top, ch=0.25)
    M.box(27.3, 64.2, 34.6, 65.0, d - 0.1, 3.0, fr, ch=0.15)
    M.box(27.3, 59.9, 28.0, 64.2, d - 0.1, 3.0, fr, ch=0.12)
    M.box(33.9, 59.9, 34.6, 64.2, d - 0.1, 3.0, fr, ch=0.12)
    M.box(28.0, 59.9, 33.9, 64.2, d - 0.1, d + 0.15, mt["well"])
    # box E with a groove (two boxes)
    M.box(34.9, 59.0, 36.0, 64.9, d - 0.1, 3.4, box, top=top, ch=0.25)
    M.box(36.5, 59.0, 39.6, 64.9, d - 0.1, 3.4, box, top=top, ch=0.25)
    # the small housing in the trench mouth (sprite c 22-23 rows 55-57)
    M.box(21.7, 55.2, 24.3, 58.6, TRENCH - 0.1, 2.6, box, top=top, ch=0.2)


def ramp(M, mt):
    r0, r1, z0, z1 = RAMP

    def zr(r):
        return z0 + (z1 - z0) * (r - r0) / (r1 - r0)
    c0, c1 = 6.6, 40.6
    M.solid([[(c0, r0, 0), (c1, r0, 0), (c1, r1, 0), (c0, r1, 0)],
             [(c0, r0, z0), (c1, r0, z0), (c1, r1, z1), (c0, r1, z1)]], mt["bed"])
    for c in RIBS:
        sec = [(-0.6, -0.1), (-0.6, 0.6), (-0.35, 0.85), (0.35, 0.85), (0.6, 0.6), (0.6, -0.1)]
        rings = [[(c + dc, rr, zr(rr) + dz) for dc, dz in sec] for rr in (r0 - 0.05, r1)]
        M.solid(rings, mt["rib"])
    # cheeks: wedges from the rim height down to the sill
    for a, b in ((P0 + 0.6, c0), (c1, P1 - 0.6)):
        M.solid([[(a, r0, 0), (b, r0, 0), (b, r1, 0), (a, r1, 0)],
                 [(a, r0, DECK), (b, r0, DECK), (b, r1, z1 + 0.5), (a, r1, z1 + 0.5)]], mt["cheek"])
    # sill
    M.box(P0 + 0.6, SILL[0], P1 - 0.6, SILL[1], 0.0, SILL[2], mt["sill"], ch=0.3)


# --- object helpers -----------------------------------------------------------------------------

def to_object(M, name, mats, coll):
    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f[M.up] and f.normal.z < 0:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def weighted(o):
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(SMOOTH))
    wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(o)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def split_open(obj, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams)."""
    out = {}
    for name, cx, cy in LAYOUT:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, grid = load_composite()
    coll = common.reset_collection(NAME)
    m = L.Mats(TAG, sprite["colors"])

    def sat(i, rough=0.45, metal=0.45):
        return m(i, metallic=metal, roughness=rough)
    mt = {
        "slab": sat(9), "plate": sat(9), "fascia": sat(8), "soffit": sat(5, 0.6, 0.3), "ridge": sat(10, 0.4),
        "bolt": sat(10, 0.35), "numeral": sat(12, 0.6, 0.2), "wall": sat(8, 0.55, 0.35), "front": sat(3, 0.6, 0.3),
        "hatch": sat(7, 0.5, 0.4), "plinth": sat(6, 0.7, 0.2), "kerb": sat(6, 0.65, 0.25), "trench": sat(2, 0.8, 0.1),
        "deck": sat(2, 0.75, 0.2), "deckside": sat(4, 0.7, 0.2), "box": sat(4, 0.5, 0.45), "boxtop": sat(4, 0.5, 0.45),
        "frame": sat(4, 0.5, 0.45), "well": sat(1, 0.8, 0.1), "louvre": sat(3, 0.5, 0.4), "bed": sat(2, 0.75, 0.2),
        "rib": sat(4, 0.5, 0.45), "cheek": sat(3, 0.65, 0.25), "sill": sat(4, 0.6, 0.3),
    }
    M = Mesh()
    roof_slab(M, mt)
    roof_plates(M, mt)
    ridge_cap(M, mt)
    numerals(M, grid, mt)
    eave_bolts(M, mt)
    body(M, mt)
    plinth(M, mt)
    rims_chamfered(M, mt)
    equipment(M, mt)
    ramp(M, mt)
    machine = to_object(M, f"{NAME}_machine", m.list, coll)
    weighted(machine)

    fmt = "AUTO"
    if "--no-bake" not in argv:
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(range(len(machine.data.materials)))
        T.bake_maps(machine, tempfile.mkdtemp(prefix="nshs13B_bake_"), size=1024, samples=64)
        fmt = "WEBP"
    shell = common.outline_shell(machine, coll, voxel=0.012, faces=4000, smooth=6, inside=0.01)
    pieces = common.split_assembly(machine, LAYOUT, coll)
    shells = split_open(shell, coll)
    export, total = [], 0
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        p.name = name
        weighted(p)
        group = [p, shells[name]]
        t = sum(tris(o) for o in group if "outline" not in o.name)
        total += t
        print(f"built piece {name}: {t} tris (+ outline {tris(shells[name])})")
        common.export_sprite_model(WT, group, f"enemies/{name}", common.load_sprite(WT, name)["sprites"],
                                   image_format=fmt)
        export += group
    if OUT:
        for name, cx, cy in LAYOUT:
            for o in export:
                if o.name.startswith(name):
                    o.location = (cx / 12, -cy / 12, 0)
        machine.hide_render = shell.hide_render = True
        common.export_glb(export, OUT, image_format=fmt)
    print(f"built {NAME}: {total} triangles, body {tris(machine)}")


if __name__ == "__main__":
    main()
