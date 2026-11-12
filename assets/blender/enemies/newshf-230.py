"""newshf-230: red armour corner with a grey ball (newshf.shp frame 230), hard-surface.

The bottom-left corner of the red side tower of the Savara fortress (levels 1.8, 1.12, 1.17, 2.1,
3.10, 4.3; partner newshf-238 on the right tower). From the sprite, row by row:

- plan: a convex quarter-round corner, steep at the top left, 45 degrees through the middle, nearly
  flat along the bottom; its edge sits on the INNER edge of the sprite's ink border (D74). The top
  row and the right column are tile seams with the pieces round it: row 0 is deck and ledge
  (65/66) continuing the tower piece above, so deck, ledge and ribs all run to the top seam.
- a lower outboard ledge (cols 1-3, index 66), a modelled groove (col 4, index 1) and the deck,
- a flat dark deck (index 65) with a skirt that slopes down to the flat belly all round the curved edge,
  built as separate armour plates over a dark core, so the panel lines between them are real gaps,
- two raised ribs: rib A (cols 9-11, 68) ending in a ramp parallel to the edge; rib B (cols 13-16,
  69) bending round into a band (rows 14-18, 68) that runs to the right edge,
- in the corner they enclose, a dark socket (index 2) under a deck lip (row 0), with a grey ball
  (index 5) in a grey collar (4/2): the ball is a closed dome that ends at the tile's right edge
  (the exposed inner edge of the tower shows it from the side), the collar ends in a flat wall there.

What it is (D120/D122 identify the object first; DECISIONS D166): the red FLYING gun fortress at the end of
SAVARA, in three sections that separate, not a ground building. In 1.8 and 1.12 SAVARA it holds at
the top of the screen over open sea; event 20 then pushes the two wing
sections (assembly-newshf-191 with newshf-230 on the left, assembly-newshf-199 with newshf-238 on the
right) out sideways at +-6 px/tick and back, while the centre gun module (assembly-newshf-195) roams
on its own; in 1.17 SAVARA V the same pieces spawn on the sky layer. The model already reads as that
from the game camera: armoured hull plating, barrels and turrets over a closed flat underside, with no
foundations, legs or walls down to a ground. So it was not rebuilt, and its pieces and pivots are
unchanged so the split still works.

Satin metal (metallic 0.3, roughness 0.45-0.5): the sprite's bright pixels are sheen on the chamfers
and the ball, not geometry. Outline shell (D51; D90's 0.03 voxels held 0.004 inside). The
flat belly is at z = 0.

Run: blender --background --python assets/blender/enemies/newshf-230.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshf-230"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

# --- heights (Blender units) ------------------------------------------------------------------
Z_WALL = 0.05     # vertical wall at the foot of the skirt
Z_DECK = 0.27     # deck top
Z_RIB = 0.34      # rib tops
Z_LEDGE_IN, Z_LEDGE_OUT = 0.20, 0.13
Z_FLOOR = 0.12    # socket floor

TOP = 0.6         # the top tile seam. Row 0 is deck and ledge (65/66) continuing the piece above, but
                  # sprite_mask counts dark 65 at the picture's edge as ink (D74 border), and a top edge
                  # at or nearer than 0.5 px to row 0's top drops the grid IoU to 0.93 (< 0.95): at 0.55
                  # an 8x top render's sample rows still covered half of row 0 (0.9316), so 0.6. The
                  # game's outline ink (0.55-0.75 px) closes the gap: no ground shows at the seam
                  # (checked in Savara, tick 4650). Ribs run to the seam (row 0 is theirs in the mask).
LIP = 0.9         # the deck lip over the socket (row 0, cols 18-21 are 65)
RIGHT = 24.0


def B(c, r):
    """Sprite edge coords (column, row) to Blender XY."""
    return ((c - 12) * PX, (14 - r) * PX)


def S(x, y):
    """Blender XY back to sprite coords."""
    return (x / PX + 12, 14 - y / PX)


# --- plan curve (sprite coords): the inner edge of the ink border, pchip in chord length ------
CURVE_CTRL = [(0.55, TOP), (0.95, 1.6), (1.55, 3.0), (3.15, 6.3), (5.0, 8.45), (9.0, 12.45), (12.9, 16.3),
              (15.0, 18.75), (17.2, 20.65), (19.4, 21.7), (21.2, 22.0), (RIGHT, 22.0)]


def curve_points(step=0.45):
    t = [0.0]
    for (a, b), (c, d) in zip(CURVE_CTRL, CURVE_CTRL[1:]):
        t.append(t[-1] + math.hypot(c - a, d - b))
    fx = T.pchip(t, [p[0] for p in CURVE_CTRL])
    fy = T.pchip(t, [p[1] for p in CURVE_CTRL])
    n = max(2, int(math.ceil(t[-1] / step)))
    return [(fx(t[-1] * i / n), fy(t[-1] * i / n)) for i in range(n + 1)]


# --- polygon helpers (copied from lib_b101 / generalised; candidates for a shared lib) ----------

def signed_area(poly):
    n = len(poly)
    return sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) / 2


def offset_polygon(poly, dists):
    """Move each edge of a CCW polygon inward by its own distance. Where the two edges at a vertex
    meet at a real angle (> 12 degrees) the vertex goes to their offset lines' intersection; where
    they are nearly parallel (a sampled curve) it moves along the mean normal by the mean distance,
    so per-edge distances that vary along a curve never blow up into long miters."""
    n = len(poly)
    nrm, lines = [], []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        nrm.append((nx, ny))
        d = dists[i]
        lines.append(((x0 + nx * d, y0 + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        na, nb = nrm[i - 1], nrm[i]
        cosang = na[0] * nb[0] + na[1] * nb[1]
        if cosang > math.cos(math.radians(12)):
            mx, my = na[0] + nb[0], na[1] + nb[1]
            ml = math.hypot(mx, my) or 1.0
            d = (dists[i - 1] + dists[i]) / 2
            out.append((poly[i][0] + mx / ml * d, poly[i][1] + my / ml * d))
            continue
        den = u[0] * v[1] - u[1] * v[0]
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def hold_offsets(poly, dists, top):
    """offset_polygon's ring with its flipped edges collapsed. At an acute corner next to a short
    edge (rib B where its arm meets the band at the panel seam, and the band's corner clipped by
    the curved deck) the step of offset_polygon carries a short edge's top past itself: the top ring
    crossed itself and the plates' top faces poked through each other as a pale sliver at the bend.
    An edge whose top runs backwards is collapsed: its two top vertices become one, where the offset
    lines of the edges either side of it meet (a straight-skeleton edge event), repeated until no
    top edge runs backwards. Vertices of edges that never flip are left as they were."""
    n = len(poly)

    def line(i):
        (x0, y0), (x1, y1) = poly[i % n], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        return (x0 + nx * dists[i % n], y0 + ny * dists[i % n]), (dx, dy)

    groups = [[i, i, top[i]] for i in range(n)]  # first and last original vertex, top position
    for _ in range(n):
        m = len(groups)
        if m < 3:
            break
        for g in range(m):
            ga, gb = groups[g], groups[(g + 1) % m]
            e = ga[1]  # the original edge from ga's last vertex to gb's first
            ed = (poly[(e + 1) % n][0] - poly[e][0], poly[(e + 1) % n][1] - poly[e][1])
            td = (gb[2][0] - ga[2][0], gb[2][1] - ga[2][1])
            if ed[0] * td[0] + ed[1] * td[1] < 0:
                break
        else:
            break
        (p, u), (q, v) = line(ga[0] - 1), line(gb[1])
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-12:
            break
        k = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        merged = [ga[0], gb[1], (p[0] + u[0] * k, p[1] + u[1] * k)]
        groups[g] = merged
        del groups[(g + 1) % m]
    out = [None] * n
    for first, last, pos in groups:
        i = first
        while True:
            out[i] = pos
            if i == last:
                break
            i = (i + 1) % n
    return out


def clip_half(poly, a, nrm):
    """Keep the part of a polygon where (p - a) . nrm >= 0 (Sutherland-Hodgman, one plane)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp = (p[0] - a[0]) * nrm[0] + (p[1] - a[1]) * nrm[1]
        dq = (q[0] - a[0]) * nrm[0] + (q[1] - a[1]) * nrm[1]
        if dp >= 0:
            out.append(p)
        if (dp >= 0) != (dq >= 0):
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def dedupe(poly, eps=0.03 / 12):
    out = []
    for p in poly:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


# --- solids --------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, mat, smooth=False):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f


def ring_solid(M, rings, mats, cap_bottom_mat, cap_top_mat, top_smooth=False):
    """A closed solid through stacked rings [[(x, y, z), ...], ...] (same vertex count, CCW from
    above, bottom first); mats[i][k] is the material of the band between ring i and i + 1 on edge k
    (or one material for the whole band)."""
    vs = [[M.bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    M.face(list(reversed(vs[0])), cap_bottom_mat)
    M.face(vs[-1], cap_top_mat)
    for i in range(len(vs) - 1):
        for k in range(n):
            j = (k + 1) % n
            m = mats[i][k] if isinstance(mats[i], (list, tuple)) else mats[i]
            M.face((vs[i][k], vs[i][j], vs[i + 1][j], vs[i + 1][k]), m)
    return vs


def chamfer_block(M, plan, z0, z1, ch, chz, mat_side, mat_top, mat_ch=None):
    """A prism on a CCW plan with its top edges chamfered: ch[i] (Blender units) per edge, chz high."""
    plan = dedupe(plan)
    top = offset_polygon(plan, ch)
    rings = [[(x, y, z0) for x, y in plan], [(x, y, z1 - chz) for x, y in plan], [(x, y, z1) for x, y in top]]
    mats = [mat_side, [mat_ch if mat_ch is not None else mat_side if c > 1e-6 else mat_side for c in ch]]
    ring_solid(M, rings, mats, mat_side, mat_top)


# --- the model -----------------------------------------------------------------------------------

def build(sprite, coll):
    pal = lambda i, met=0.3, rough=0.48: common.palette_material(sprite, i, NAME, metallic=met, roughness=rough)  # noqa: E731
    mats = [
        pal(65, 0.3, 0.5),    # 0 DECK: dark red deck
        pal(66, 0.3, 0.48),   # 1 SKIRT: skirt plates, ledge, walls
        pal(68, 0.32, 0.45),  # 2 RIBA: rib A and the band
        pal(69, 0.32, 0.44),  # 3 RIBB: rib B
        pal(2, 0.2, 0.75),    # 4 SOCKET: dark socket
        pal(5, 0.55, 0.38),   # 5 BALL: grey ball (satin: the sprite's white spot is sheen)
        pal(64, 0.2, 0.7),    # 6 CORE: the dark core in the panel gaps
        pal(4, 0.5, 0.4),     # 7 COLLAR: grey collar round the ball
    ]
    DECK, SKIRT, RIBA, RIBB, SOCKET, BALL, CORE, COLLAR = range(8)
    # The skirt plates are the sprite's index 65 too (rows 19-21 and the diagonal's edge pixels).
    PLATE = DECK
    M = Mesh()

    curve = curve_points()                         # sprite coords, top-left to bottom-right
    # Where the curve crosses x = 4.5 (the ledge's step wall).
    # The sprite's col 4 is a dark groove (index 1, rows 0-8) between the ledge and the deck.
    STEP_X, LEDGE_X = 4.85, 4.15                   # deck's left edge, ledge's right edge

    def crossing(xc):
        k = next(i for i, p in enumerate(curve) if p[0] >= xc)
        (xa, ya), (xb, yb) = curve[k - 1], curve[k]
        return k, ya + (yb - ya) * (xc - xa) / (xb - xa)

    k, ycross = crossing(STEP_X)
    kl, ycl = crossing(LEDGE_X)
    upper_curve = [(STEP_X, ycross)] + [p for p in curve[k:] if math.hypot(p[0] - STEP_X, p[1] - ycross) > 0.1]
    ledge_curve = [p for p in curve[:kl] if math.hypot(p[0] - LEDGE_X, p[1] - ycl) > 0.1] + [(LEDGE_X, ycl)]
    groove_curve = [(LEDGE_X, ycl)] + [p for p in curve[kl:k] if LEDGE_X + 0.05 < p[0] < STEP_X - 0.05] + [(STEP_X, ycross)]

    # Socket corner (sprite coords), notched out of the deck; rib B wraps it.
    SOCK_X, SOCK_Y, SOCK_R = 16.9, 14.1, 3.2       # notch left edge, bottom edge, fillet radius
    notch = [(RIGHT, SOCK_Y)] + arc(SOCK_X + SOCK_R, SOCK_Y - SOCK_R, SOCK_R, 90, 180, 8) + [(SOCK_X, LIP)]
    # notch runs (24,14.1) -> fillet -> (16.9, LIP); the deck runs on over it as a lip to the top seam.
    # Deck loop in sprite order (clockwise on screen):
    deck_sprite = [(STEP_X, TOP), (RIGHT, TOP), (RIGHT, LIP)] + list(reversed(notch)) + [(RIGHT, 22.0)] \
        + list(reversed(upper_curve))[1:-1] + [(STEP_X, ycross)]
    # Blender CCW: sprite clockwise -> reflect y -> counter-clockwise.
    deck = dedupe([B(*p) for p in deck_sprite])
    if signed_area(deck) < 0:
        deck = list(reversed(deck))
    n = len(deck)

    def is_curve_edge(i):
        (c0, r0), (c1, r1) = S(*deck[i]), S(*deck[(i + 1) % n])
        seam = (abs(r0 - TOP) < 1e-3 and abs(r1 - TOP) < 1e-3) or (abs(c0 - RIGHT) < 1e-3 and abs(c1 - RIGHT) < 1e-3) \
            or (abs(c0 - STEP_X) < 1e-3 and abs(c1 - STEP_X) < 1e-3)
        inside_notch = min(c0, c1) >= SOCK_X - 1e-3 and max(r0, r1) <= SOCK_Y + 1e-3
        return not seam and not inside_notch

    curve_edge = [is_curve_edge(i) for i in range(n)]
    # Start the loop at the curve's first edge, so the curved run is contiguous (i0..i1).
    r0 = next(i for i in range(n) if curve_edge[i] and not curve_edge[i - 1])
    deck = deck[r0:] + deck[:r0]
    curve_edge = [is_curve_edge(i) for i in range(n)]
    assert sum(1 for i in range(n) if curve_edge[i] and not curve_edge[i - 1]) == 1

    def skirt_inset(i):
        """The skirt's width in px: about 1 px down the diagonal, 2.7 px along the bottom (the
        sprite's three dark rows under the band)."""
        if not curve_edge[i]:
            return 0.0
        (_, r0), (_, r1) = S(*deck[i]), S(*deck[(i + 1) % n])
        t = min(1.0, max(0.0, ((r0 + r1) / 2 - 13.0) / 8.0))
        t = t * t * (3 - 2 * t)
        return 1.05 + 1.65 * t

    ins = [skirt_inset(i) * PX for i in range(n)]
    GAP_IN = 0.3 * PX                                  # plate thickness over the core
    foot = deck
    mid = deck
    top = offset_polygon(deck, ins)
    core_off = [GAP_IN if curve_edge[i] else 0.0 for i in range(n)]
    foot_c = offset_polygon(foot, core_off)
    top_c = offset_polygon(top, core_off)

    def core_mat(i):
        if curve_edge[i]:
            return CORE
        (c0, _), (c1, _) = S(*deck[i]), S(*deck[(i + 1) % n])
        return DECK if abs(c0 - STEP_X) < 1e-3 and abs(c1 - STEP_X) < 1e-3 else SKIRT

    core_mats = [core_mat(i) for i in range(n)]
    # Core: the deck block shrunk by the plate thickness on the curved side (dark, seen in the gaps).
    ring_solid(M, [[(x, y, 0.0) for x, y in foot_c], [(x, y, Z_WALL) for x, y in foot_c],
                   [(x, y, Z_DECK) for x, y in top_c]], [core_mats, core_mats], CORE, DECK)
    # The deck plate over the core's top (so the deck has its own 0.3 px thick edge to the plates).
    # (The core top already is the deck colour; the plates below bring the skirt.)

    # Skirt plates along the curve, gaps between them at stations of about 5 px.
    curve_idx = [i for i in range(n) if curve_edge[i]]
    # contiguous run of curve edges i0..i1 (edge i joins vertex i and i + 1)
    i0, i1 = curve_idx[0], curve_idx[-1] + 1
    seglen = [math.hypot(deck[(i + 1) % n][0] - deck[i][0], deck[(i + 1) % n][1] - deck[i][1]) for i in range(n)]
    cum = [0.0]
    for i in range(i0, i1):
        cum.append(cum[-1] + seglen[i])
    total = cum[-1]
    nplates = max(1, round(total / (5.2 * PX)))
    gap = 0.32 * PX
    bounds = [total * j / nplates for j in range(nplates + 1)]

    def at(poly, s):
        """Point on the polyline poly[i0..i1] at arc length s (measured on the footprint)."""
        for j in range(len(cum) - 1):
            if s <= cum[j + 1] + 1e-12 or j == len(cum) - 2:
                f = (s - cum[j]) / max(1e-12, cum[j + 1] - cum[j])
                a, b = poly[i0 + j], poly[(i0 + j + 1) % n]
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

    for j in range(nplates):
        s0 = bounds[j] + (gap / 2 if j > 0 else 0.0)
        s1 = bounds[j + 1] - (gap / 2 if j < nplates - 1 else 0.0)
        ss = [s0] + [c for c in cum if s0 + 1e-9 < c < s1 - 1e-9] + [s1]
        outer = [[(*at(foot, s), 0.0) for s in ss], [(*at(mid, s), Z_WALL) for s in ss], [(*at(top, s), Z_DECK) for s in ss]]
        inner = [[(*at(foot_c, s), 0.0) for s in ss], [(*at(foot_c, s), Z_WALL) for s in ss], [(*at(top_c, s), Z_DECK) for s in ss]]
        # A closed plate: outer skin, inner skin, top strip, bottom strip, end caps.
        ov = [[M.bm.verts.new(p) for p in ring] for ring in outer]
        iv = [[M.bm.verts.new(p) for p in ring] for ring in inner]
        m = len(ss)
        for a in range(2):
            for b in range(m - 1):
                M.face((ov[a][b], ov[a][b + 1], ov[a + 1][b + 1], ov[a + 1][b]), PLATE)
                M.face((iv[a][b + 1], iv[a][b], iv[a + 1][b], iv[a + 1][b + 1]), CORE)
        for b in range(m - 1):
            M.face((ov[2][b], ov[2][b + 1], iv[2][b + 1], iv[2][b]), DECK)    # top strip
            M.face((ov[0][b + 1], ov[0][b], iv[0][b], iv[0][b + 1]), CORE)    # bottom
        for b, rev in ((0, False), (m - 1, True)):
            cap = [ov[0][b], ov[1][b], ov[2][b], iv[2][b], iv[1][b], iv[0][b]]
            M.face(list(reversed(cap)) if rev else cap, PLATE)

    # Ledge: the strip outboard of the step, its top sloping down to the outside.
    ledge = [B(*p) for p in [(LEDGE_X, TOP)] + ledge_curve]
    if signed_area(ledge) < 0:
        ledge = list(reversed(ledge))
    nl = len(ledge)

    def ledge_z(x, y):
        c, _ = S(x, y)
        t = min(1.0, max(0.0, (LEDGE_X - c) / 3.2))
        return Z_LEDGE_IN + (Z_LEDGE_OUT - Z_LEDGE_IN) * t

    def l_curve(i):
        (c0, r0), (c1, r1) = S(*ledge[i]), S(*ledge[(i + 1) % nl])
        return not ((abs(r0 - TOP) < 1e-3 and abs(r1 - TOP) < 1e-3) or (c0 > LEDGE_X - 0.01 and c1 > LEDGE_X - 0.01))

    lch = [0.55 * PX if l_curve(i) else 0.0 for i in range(nl)]
    ltop = offset_polygon(ledge, lch)
    ring_solid(M, [[(x, y, 0.0) for x, y in ledge], [(x, y, ledge_z(x, y) - 0.04) for x, y in ledge],
                   [(x, y, ledge_z(x, y)) for x, y in ltop]], [SKIRT, SKIRT], SKIRT, SKIRT)

    # The groove between ledge and deck (col 4): a dark floor, low, so both walls show as a cut line.
    groove = [B(*p) for p in [(LEDGE_X - 0.05, TOP), (STEP_X + 0.05, TOP)] + list(reversed(groove_curve))]
    groove = dedupe(list(reversed(groove)) if signed_area(groove) < 0 else groove)
    ring_solid(M, [[(x, y, 0.0) for x, y in groove], [(x, y, 0.10) for x, y in groove]], [CORE], CORE, CORE)

    # Clip regions for ribs: inside the deck top by 0.35 px on the curved side.
    clip_planes = []
    for i in range(n):
        if not curve_edge[i]:
            continue
        (x0, y0), (x1, y1) = top[i], top[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        clip_planes.append(((x0 + nx * 0.35 * PX, y0 + ny * 0.35 * PX), (nx, ny)))

    def clipped(poly_sprite):
        poly = [B(*p) for p in poly_sprite]
        if signed_area(poly) < 0:
            poly = list(reversed(poly))
        for a, nrm in clip_planes:
            poly = clip_half(poly, a, nrm)
            if len(poly) < 3:
                break
        return dedupe(poly)

    def rib(poly_sprite, mat, z0, ramp_px):
        poly = clipped(poly_sprite)
        m = len(poly)
        ch = []
        for i in range(m):
            (c0, r0), (c1, r1) = S(*poly[i]), S(*poly[(i + 1) % m])
            if (abs(r0) < 1e-3 and abs(r1) < 1e-3) or (abs(c0 - RIGHT) < 1e-3 and abs(c1 - RIGHT) < 1e-3):
                ch.append(0.0)                         # tile seams: square ends
            elif abs(c1 - c0) > 0.05 and abs(r1 - r0) > 0.05 and not (c0 > 16.5 and r1 < SOCK_Y + 0.2 and r0 < SOCK_Y + 0.2):
                ch.append(ramp_px * PX)                # an end cut parallel to the edge: a ramp
            else:
                ch.append(0.55 * PX)
        chz = 0.035
        top_r = hold_offsets(poly, ch, offset_polygon(poly, ch))
        # ramps run all the way down to the deck; other edges a 45-degree chamfer.
        rings = [[(x, y, z0) for x, y in poly],
                 [(x, y, (Z_DECK + 0.004) if ch[i] > 0.6 * PX or ch[i - 1] > 0.6 * PX else Z_RIB - chz)
                  for i, (x, y) in enumerate(poly)],
                 [(x, y, Z_RIB) for x, y in top_r]]
        ring_solid(M, rings, [mat, mat], mat, mat)

    # Rib A: cols 9-11, from the top seam to a ramp parallel to the edge.
    rib([(9.0, 0.0), (12.0, 0.0), (12.0, 20.0), (9.0, 20.0)], RIBA, Z_DECK - 0.03, 1.7)
    # Rib B with its band: cols 13-16 down, then round the socket to the right edge (rows 14-18).
    R_IN = SOCK_R + 0.1
    inner_fillet = arc(SOCK_X + 0.1 + R_IN, SOCK_Y + 0.1 - R_IN, R_IN, 180, 90, 8)
    ribB = [(13.0, 0.0), (SOCK_X + 0.1, 0.0)] + [(x, y) for x, y in inner_fillet] + [(RIGHT, SOCK_Y + 0.1 - 0.0), (RIGHT, 19.0), (13.0, 19.0)]
    # Rib B is two plates split by a panel seam at row 13.9: the upright arm (cols 13-16 and the top of
    # the fillet, sprite index 69) and the band round the socket to the right edge (rows 14-18, 68).
    # Each plate chamfers its edge on the seam, so the colour change sits in a real V groove.
    SPLIT = 13.9
    rib(clip_half(ribB, (0.0, SPLIT), (0.0, -1.0)), RIBB, Z_FLOOR - 0.01, 1.0)   # rows <= SPLIT: arm, 69
    rib(clip_half(ribB, (0.0, SPLIT), (0.0, 1.0)), RIBA, Z_FLOOR - 0.01, 1.0)    # rows >= SPLIT: band, 68

    # Machined detail on the plain deck (cols 5-8): a row of low bolt heads down its length, same index
    # 65 as the deck so the top-view colours and silhouette don't change; they catch light in game.
    for c, r in ((6.0, 1.6), (7.8, 1.6), (6.0, 5.2), (7.8, 5.2), (7.0, 8.8)):
        stud = [B(c + 0.42 * math.cos(math.radians(22.5 + 45 * i)), r + 0.42 * math.sin(math.radians(22.5 + 45 * i)))
                for i in range(8)]
        stud = list(reversed(stud)) if signed_area(stud) < 0 else stud
        chamfer_block(M, stud, Z_DECK - 0.01, Z_DECK + 0.022, [0.12 * PX] * 8, 0.01, DECK, DECK, DECK)

    # Socket floor in the notch.
    sock = [B(*p) for p in [(SOCK_X - 0.3, LIP - 0.3), (RIGHT, LIP - 0.3), (RIGHT, SOCK_Y + 0.3), (SOCK_X - 0.3, SOCK_Y + 0.3)]]
    sock = list(reversed(sock)) if signed_area(sock) < 0 else sock
    ring_solid(M, [[(x, y, 0.0) for x, y in sock], [(x, y, Z_FLOOR) for x, y in sock]], [SKIRT], SKIRT, SOCKET)

    # Ball and collar. The sprite's ball (rows 2-8 with its dark lower shading, cols 18-23, bright
    # core rows 3-7) is a closed dome whose right extent ends at the tile's right edge, so the exposed
    # inner edge of the tower shows a whole ball, never a cut. It stands in a grey collar (the 4/2
    # socket rim, about 9.6 px) whose own right side is a flat socket wall on the seam.
    xr = B(RIGHT, 0)[0]
    cx, cy, crx, cry = 21.4, 5.8, 4.3, 4.85             # collar plan (sprite px)
    collar = [B(cx + crx * math.cos(2 * math.pi * i / 40), cy + cry * math.sin(2 * math.pi * i / 40)) for i in range(40)]
    collar = list(reversed(collar)) if signed_area(collar) < 0 else collar
    collar = dedupe(clip_half(collar, (xr, 0.0), (-1.0, 0.0)))
    nc = len(collar)
    cch = [0.0 if abs(collar[i][0] - xr) < 1e-6 and abs(collar[(i + 1) % nc][0] - xr) < 1e-6 else 0.45 * PX
           for i in range(nc)]
    chamfer_block(M, collar, 0.0, Z_FLOOR + 0.055, cch, 0.03, SOCKET, COLLAR, COLLAR)

    bcx, bcy, brx, bry = 20.85, 5.5, 3.1, 3.5            # ball plan (sprite px): x 17.75-23.95
    bx, by = B(bcx, bcy)
    bz, brz = Z_FLOOR + 0.07, 0.25
    segs = 32
    lats = [-20, 0, 15, 30, 45, 58, 70, 80]
    rings = []
    for la in lats:
        c, s_ = math.cos(math.radians(la)), math.sin(math.radians(la))
        rings.append([M.bm.verts.new((bx + brx * PX * c * math.cos(2 * math.pi * i / segs),
                                      by + bry * PX * c * math.sin(2 * math.pi * i / segs),
                                      bz + brz * s_)) for i in range(segs)])
    pole = M.bm.verts.new((bx, by, bz + brz))
    M.face(list(reversed(rings[0])), SOCKET)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            M.face((r0[i], r0[j], r1[j], r1[i]), BALL, smooth=True)
    for i in range(segs):
        M.face((rings[-1][i], rings[-1][(i + 1) % segs], pole), BALL, smooth=True)

    bmesh.ops.remove_doubles(M.bm, verts=M.bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(M.bm, faces=M.bm.faces)
    me = bpy.data.meshes.new(NAME)
    smooth_flags = [f.smooth for f in M.bm.faces]
    M.bm.to_mesh(me)
    M.bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # Hard surface: flat faces flat, sharp by angle; the ball and collar smooth.
    for p, s in zip(me.polygons, smooth_flags):
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = common.outline_shell(obj, coll, voxel=0.03, inside=0.004)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles (+ shell {len(shell.data.polygons)} faces)")
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(ROOT) / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj, shell], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
