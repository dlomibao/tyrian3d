"""Design A for assembly-newsha-49 (newsha.shp 49 | 51): the "WARNING / MISSILE SHIPS!!" flying sign.

WHAT IT IS: a free-flying neon channel-letter sign that races up the screen ahead of the missile
ships (2.10 SOH JIN, sky layer, armour 0). No backing plate: each glyph is a channel letter (a
glowing face, a chamfered trim cap round it, darker returns down its sides), the three text lines
hang on a slim dark raceway frame behind the letters, and three small lift jets under the frame
keep it up. Nothing touches the ground.

Cross-sections first (engineering read, then the sprite):
- letter stroke: a chamfered channel, 1 px wide, face pal 120 (glow 1.0, D126), trim chamfer pal
  119 (glow 0.9), returns pal 118 (glow 0.75), back pal 116. WARNING stands 2.0 px, MISSILE SHIPS!!
  1.6 px. Strokes are swept along the glyph centre lines with mitred joints, so the diagonals are
  straight 45-degree bars, never pixel staircases; free ends are chamfered.
- WARNING's dark left column (the sprite's 118 pixels) is the letter's west bevel: a 1 px wedge
  falling from the face to 0.9 px, the chiselled return of a bevel-cut letter (lit sheen is not
  paint; this is the sprite's own darker index, so it gets its own face).
- underlines: tapered chamfered blades, full height mid-span and lower / narrower / darker at the
  tails, one palette index per sprite column (116 118 119 120 ... 120 119 118 116 and so on).
- swoosh fins: triangular plates under MISSILE's E tail and before SHIPS, their hypotenuse a broad
  bevel in the sprite's 116 / 117.
- raceway: three pal 4 tubes (one per text line) and three spars just behind the letters' backs,
  0.28 px thick (under half a pixel, so they never count as sprite pixels), pal 7 clamp nodes, and
  three pal 4 lift-jet pods under the nodes (the underside: a plausible closed shape, no detail).
Glow materials are metallic 1, roughness 0.9 (D173), strengths per the blueprint.

Units: sprite px (1/12 u). x = column - 24, y = 14 - row (assembly coordinates centred on the sign,
screen (173, 39)); newsha-49 is x < 0, newsha-51 x > 0. z up from the letter backs.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsha-49.py
Builds the whole sign in assembly coordinates, cuts the glowing letters and the raceway into
newsha-49 (left) / newsha-51 (right) with common.split_assembly, gives each piece its own outline
shell (from that piece's letters only) and exports enemies/newsha-49 and enemies/newsha-51.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402

WT = common.repo_root(__file__)
ROOT = WT
NAME = "assembly-newsha-49"
TAG = "nsha49A"
PIECES = ["newsha-49", "newsha-51"]
CX0, CY0 = 173, 39
W, H = 48, 28
U = 1 / 12  # one sprite px in units

# heights (px)
H_BIG, H_SMALL, H_BAR = 2.0, 1.6, 1.35
CH = 0.22  # trim chamfer
SW = 0.9  # stroke width (a 1.0 bar fills the inner corners of the 90-degree turns)
FLANK_LO = 0.9  # WARNING's west bevel: outer edge height
BAR_Z = {120: 1.35, 119: 1.2, 118: 1.05, 117: 0.95, 116: 0.85, 114: 0.7}
BAR_W = {120: 1.0, 119: 0.92, 118: 0.86, 117: 0.82, 116: 0.78, 114: 0.72}
GLOW = {120: 1.0, 119: 0.9, 118: 0.75, 117: 0.65, 116: 0.55, 114: 0.4}

# --- glyphs (sprite pixel indices (col, row); centre lines through pixel centres) -------------------
# Each stroke: (points, ext0, ext1): ext = square-cap extension at that end in px (0.5 free end,
# 0 where it starts inside another stroke).
BIG = [  # WARNING
    ([(3, 6), (3, 10), (4, 11), (6, 11), (7, 10), (7, 6)], .5, .5),
    ([(5, 9), (5, 11)], .5, .5),
    ([(10, 11), (10, 7), (11, 6), (12, 7), (12, 11)], .5, .5),
    ([(10, 8), (12, 8)], .5, .5),
    ([(15, 11), (15, 6), (16, 6), (17, 7), (17, 8), (16, 9), (15, 9)], .5, .5),
    ([(16, 9), (17, 10), (17, 11)], .25, .5),
    ([(20, 11), (20, 6)], .5, .5),
    ([(20, 6), (23, 9), (23, 11)], .25, .5),
    ([(26, 7), (26, 11)], .5, .5),
    ([(29, 11), (29, 6)], .5, .5),
    ([(29, 6), (32, 9), (32, 11)], .25, .5),
    ([(37, 7), (36, 6), (35, 7), (35, 10), (36, 11), (37, 11), (38, 10), (38, 9)], .5, .5),
]
# WARNING's 118 west bevels: (points, ext0, ext1); a single point is a 1 px pad whose high side
# faces the letter.
FLANK = [
    ([(2, 6), (2, 10), (3, 11)], .5, .5),
    ([(10, 6), (9, 7), (9, 11)], .5, .5),
    ([(14, 6), (14, 11)], .5, .5),
    ([(19, 6), (19, 11)], .5, .5),
    ([(26, 6)], .5, .5),
    ([(25, 7), (25, 11)], .5, .5),
    ([(28, 6), (28, 11)], .5, .5),
    ([(35, 6), (34, 7), (34, 10), (35, 11)], .5, .5),
]
SMALL = [  # MISSILE, SHIPS!!
    ([(2, 20), (2, 17), (3, 16), (5, 16), (6, 17), (6, 20)], .5, .5),
    ([(4, 16), (4, 18)], .5, .5),
    ([(8, 16), (8, 20)], .5, .5),
    ([(12, 16), (11, 16), (10, 17), (11, 18), (12, 19), (11, 20), (10, 20)], .5, .5),
    ([(16, 16), (15, 16), (14, 17), (15, 18), (16, 19), (15, 20), (14, 20)], .5, .5),
    ([(18, 16), (18, 20)], .5, .5),
    ([(20, 16), (20, 20), (22, 20)], .5, .5),
    ([(26, 16), (24, 16), (24, 20), (26, 20)], .5, .5),
    ([(24, 18), (25, 18)], .25, .5),
    ([(16, 22), (15, 22), (14, 23), (15, 24), (16, 25), (15, 26), (14, 26)], .5, .5),
    ([(18, 22), (18, 26)], .5, .5),
    ([(20, 22), (20, 26)], .5, .5),
    ([(18, 24), (20, 24)], .25, .25),
    ([(22, 22), (22, 26)], .5, .5),
    ([(24, 26), (24, 22), (25, 22), (26, 23), (25, 24), (24, 24)], .5, .5),
    ([(30, 22), (29, 22), (28, 23), (29, 24), (30, 25), (29, 26), (28, 26)], .5, .5),
    ([(32, 22), (32, 24)], .5, .5),
    ([(34, 22), (34, 24)], .5, .5),
]
DOTS = [(32, 26), (34, 26)]  # the !! dots: square studs
# underlines / swooshes: (row, first col, palette per column)
BARS = [
    (13, 4, [116, 118, 119] + [120] * 27 + [119, 118, 116]),
    (20, 28, [120] * 8 + [118, 116, 114]),
    (22, 3, [116, 118, 119] + [120] * 7),
]
# swoosh fins: outer triangle (pixel edge coords), the bevelled edge (vertex pair), its palette
FINS = [
    ([(28.0, 15.5), (28.0, 21.0), (33.5, 21.0)], (2, 0), 116),
    ([(7.5, 22.0), (13.0, 22.0), (13.0, 27.0), (12.5, 27.0)], (3, 0), 117),
]
# raceway (pixel edge coords, as the blueprint)
# on pixel edges, so the 0.28 px tubes split across two pixels and never count as sprite pixels
RODS = [((2.6, 11.0), (38.4, 11.0)), ((2.5, 18.0), (29.0, 18.0)), ((12.5, 24.0), (34.0, 24.0)),
        ((3.0, 6.5), (3.0, 22.5)), ((21.0, 6.5), (21.0, 26.5)), ((34.0, 7.0), (34.0, 26.5))]
NODES = [(3, 11), (21, 11), (34, 11), (3, 18), (21, 18), (34, 18), (21, 24), (34, 24)]
JETS = [(3, 11), (21, 18), (34, 24)]
ROD_R, ROD_Z = 0.14, -0.16


def P(c, r):
    """Pixel (col, row) centre -> px space."""
    return Vector((c + 0.5 - W / 2, H / 2 - (r + 0.5)))


def E(c, r):
    """Pixel-edge coords -> px space."""
    return Vector((c - W / 2, H / 2 - r))


def load_grid():
    g = [[-1] * W for _ in range(H)]
    sprite = None
    for k, name in enumerate(PIECES):
        data = common.load_sprite(WT, name)
        for r, line in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                g[r][c + 24 * k] = v
        if sprite is None:
            sprite = data
        else:
            sprite["colors"].update(data["colors"])
    # the raceway's greys: same sheet and palette (5), from the grey ship in the same layout
    sprite["colors"].update(common.load_sprite(WT, "newsha-47")["colors"])
    sprite["colors"].update(common.load_sprite(WT, "newsha-39")["colors"])
    return g, sprite


class Builder:
    def __init__(self, slot):
        self.bm = bmesh.new()
        self.slot = slot
        self.part = self.bm.faces.layers.int.new("part")
        self.parts = []

    def begin(self, name):
        self.parts.append(name)
        return len(self.parts) - 1

    def face(self, pts, pal, pid):
        vs = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(vs)
        f.material_index = self.slot[pal]
        f[self.part] = pid
        f.smooth = False
        return f


def sweep(B, pid, pts, profile, mats, ext0, ext1, end_ch=CH, tangent=None):
    """Sweep a closed (n, z) profile (n = offset to the left of travel, px) along a 2D polyline
    with mitred joints. `mats` gives each profile edge's palette index (edge k: point k -> k+1).
    Free ends (ext > 0) get the square cap and a chamfer: the profile's top drops by end_ch over
    the last end_ch of length."""
    pts = [Vector(p) for p in pts]
    if len(pts) == 1:
        t = Vector(tangent).normalized()
        pts = [pts[0] - t * 1e-3, pts[0] + t * 1e-3]
    dirs = [(b - a).normalized() for a, b in zip(pts, pts[1:])]
    left = [Vector((-d.y, d.x)) for d in dirs]
    zmax = max(z for _, z in profile)

    def inset(prof):
        return [(n, min(z, zmax - end_ch)) for n, z in prof]

    stations = []  # (point, normal, scale, profile)
    if ext0 >= 0.4:
        stations.append((pts[0] - dirs[0] * ext0, left[0], 1.0, inset(profile)))
        stations.append((pts[0] - dirs[0] * max(ext0 - end_ch, 0), left[0], 1.0, profile))
    else:  # a joint end, buried in the stroke it starts from
        stations.append((pts[0] - dirs[0] * ext0, left[0], 1.0, profile))
    for i in range(1, len(pts) - 1):
        m = (left[i - 1] + left[i])
        m.normalize()
        stations.append((pts[i], m, 1.0 / max(m.dot(left[i]), 0.3), profile))
    if ext1 >= 0.4:
        stations.append((pts[-1] + dirs[-1] * max(ext1 - end_ch, 0), left[-1], 1.0, profile))
        stations.append((pts[-1] + dirs[-1] * ext1, left[-1], 1.0, inset(profile)))
    else:
        stations.append((pts[-1] + dirs[-1] * ext1, left[-1], 1.0, profile))
    rings = []
    for p, nrm, s, prof in stations:
        rings.append([Vector((p.x + nrm.x * n * s, p.y + nrm.y * n * s, z)) for n, z in prof])
    k = len(profile)
    for a, b in zip(rings, rings[1:]):
        for j in range(k):
            j1 = (j + 1) % k
            quad = [a[j], a[j1], b[j1], b[j]]
            if (quad[0] - quad[3]).length < 1e-6 and (quad[1] - quad[2]).length < 1e-6:
                continue
            B.face(quad, mats[j], pid)
    capmat = mats[1]
    B.face(list(reversed(rings[0])), capmat, pid)
    B.face(rings[-1], capmat, pid)


def chan_profile(h, w=SW, c=CH):
    prof = [(-w / 2, 0), (w / 2, 0), (w / 2, h - c), (w / 2 - c, h), (-w / 2 + c, h), (-w / 2, h - c)]
    return prof, [116, 118, 119, 120, 119, 118]


def flank_profile(h, high_left):
    """WARNING's west bevel: 1 px wide, falling from the letter's trim line (h - CH) on the letter's
    side to FLANK_LO on the outside, running 0.3 px on under the letter."""
    s = 1 if high_left else -1
    prof = [(-0.5 * s, 0), (0.8 * s, 0), (0.8 * s, h - CH - 0.02), (0.5 * s, h - CH - 0.02),
            (-0.5 * s, FLANK_LO)]
    return prof, [116, 118, 118, 118, 118]  # mirrored loops get their winding from recalc_face_normals


def is_main(g, c, r):
    return 0 <= r < H and 0 <= c < W and g[r][c] == 120


def build_letters(B, g, strokes, h, label):
    prof, mats = chan_profile(h)
    for i, (pts, e0, e1) in enumerate(strokes):
        pid = B.begin(f"{label}{i}")
        sweep(B, pid, [P(*p) for p in pts], prof, mats, e0, e1)


def build_flanks(B, g):
    for i, (pts, e0, e1) in enumerate(FLANK):
        pid = B.begin(f"bevel{i}")
        if len(pts) == 1:
            c, r = pts[0]
            # the letter pixel next to the pad
            for dc, dr in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                if is_main(g, c + dc, r + dr):
                    break
            toward = Vector((dc, -dr))
            tangent = Vector((toward.y, -toward.x))  # its left is `toward`... checked below
            left = Vector((-tangent.y, tangent.x))
            high_left = left.dot(toward) > 0
            prof, mats = flank_profile(H_BIG, high_left)
            sweep(B, pid, [P(c, r)], prof, mats, 0.5, 0.5, tangent=tangent)
            continue
        a, b = P(*pts[0]), P(*pts[1])
        d = (b - a).normalized()
        left = Vector((-d.y, d.x))
        mid = (a + b) / 2 + left * 0.9
        cc, rr = int(math.floor(mid.x + W / 2)), int(math.floor(H / 2 - mid.y))
        high_left = is_main(g, cc, rr)
        prof, mats = flank_profile(H_BIG, high_left)
        sweep(B, pid, [P(*p) for p in pts], prof, mats, e0, e1)


def build_dots(B):
    prof, mats = chan_profile(H_SMALL, w=0.96)
    for i, (c, r) in enumerate(DOTS):
        pid = B.begin(f"dot{i}")
        sweep(B, pid, [P(c, r)], prof, mats, 0.48, 0.48, tangent=(1, 0))


def pchip(xs, ys, x):
    """Monotone cubic (Fritsch-Carlson) through (xs, ys) at x."""
    n = len(xs)
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    hs = [xs[i + 1] - xs[i] for i in range(n - 1)]
    dl = [(ys[i + 1] - ys[i]) / hs[i] for i in range(n - 1)]
    m = [dl[0]] + [0.0] * (n - 2) + [dl[-1]]
    for i in range(1, n - 1):
        if dl[i - 1] * dl[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * hs[i] + hs[i - 1], hs[i] + 2 * hs[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])
    i = max(k for k in range(n - 1) if xs[k] <= x)
    t = (x - xs[i]) / hs[i]
    h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
    h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    return h00 * ys[i] + h10 * hs[i] * m[i] + h01 * ys[i + 1] + h11 * hs[i] * m[i + 1]


def build_bars(B):
    """Underline blades: a chamfered hexagon section lofted along the row, height and width
    following each column's palette step (pchip through the column centres), one material per
    column; both ends chamfered."""
    for i, (row, c0, pals) in enumerate(BARS):
        pid = B.begin(f"bar{i}")
        n = len(pals)
        xc = [c0 + k + 0.5 for k in range(n)]
        hz = [BAR_Z[p] for p in pals]
        hw = [BAR_W[p] / 2 for p in pals]
        y = H / 2 - (row + 0.5)
        # stations: every column edge plus quarter points (smooth taper), chamfered ends
        xs = []
        for k in range(n):
            xs += [c0 + k, c0 + k + 0.5]
        xs.append(c0 + n)
        ends = (xs[0], xs[-1])
        xs = [ends[0], ends[0] + CH] + xs[1:-1] + [ends[1] - CH, ends[1]]
        rings = []
        for x in xs:
            h = pchip(xc, hz, x)
            w = pchip(xc, hw, x)
            top = h - (CH if x in ends else 0)
            cc = min(CH, w * 0.45)
            prof = [(-w, 0), (w, 0), (w, top - cc), (w - cc, top), (-w + cc, top), (-w, top - cc)]
            if x in ends:
                prof = [(-w, 0), (w, 0), (w, top - cc), (w - cc, top - cc), (-w + cc, top - cc), (-w, top - cc)]
            X = x - W / 2
            rings.append(([Vector((X, y + nn, z)) for nn, z in prof], x))
        for (a, xa), (b, xb) in zip(rings, rings[1:]):
            col = int(math.floor((xa + xb) / 2 - c0))
            pal = pals[min(max(col, 0), n - 1)]
            mats = [116, 118 if pal == 120 else min(pal, 118), 119 if pal == 120 else pal, pal,
                    119 if pal == 120 else pal, 118 if pal == 120 else min(pal, 118)]
            for j in range(6):
                j1 = (j + 1) % 6
                # profile goes -y .. +y; the loft runs +x, so (a_j, b_j, b_j1, a_j1) faces out
                B.face([a[j], b[j], b[j1], a[j1]], mats[j], pid)
        B.face(list(reversed(rings[0][0])), pals[0], pid)
        B.face(rings[-1][0], pals[-1], pid)


def build_fins(B):
    """Swoosh fins: a flat plate at bar height; every edge has the trim chamfer, the hypotenuse a
    broad bevel (1 px across in the sprite's grid) falling to 0.5 px."""
    for i, (poly, bev, pal) in enumerate(FINS):
        pid = B.begin(f"fin{i}")
        O = [E(*p) for p in poly]
        # make it counter-clockwise in px space (y up)
        area = sum(O[k].x * O[(k + 1) % len(O)].y - O[(k + 1) % len(O)].x * O[k].y for k in range(len(O)))
        idx = list(range(len(O)))
        if area < 0:
            O = O[::-1]
            idx = idx[::-1]
        nO = len(O)
        bevel_edge = None
        for k in range(nO):
            a, b = idx[k], idx[(k + 1) % nO]
            if {a, b} == set(bev):
                bevel_edge = k
        h = H_BAR
        ins, drop = [], []
        for k in range(nO):
            if k == bevel_edge:
                ins.append(1 / math.sqrt(2))
                drop.append(h - 0.5)
            else:
                ins.append(CH)
                drop.append(CH)
        # inward offset lines, intersected at each vertex -> top polygon
        lines = []
        for k in range(nO):
            a, b = O[k], O[(k + 1) % nO]
            d = (b - a).normalized()
            inn = Vector((-d.y, d.x))  # CCW: inside is left
            lines.append((a + inn * ins[k], d))
        T = []
        for k in range(nO):
            (p1, d1), (p2, d2) = lines[k - 1], lines[k]
            den = d1.x * d2.y - d1.y * d2.x
            t = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / den
            T.append(p1 + d1 * t)
        v3 = lambda p, z: Vector((p.x, p.y, z))  # noqa: E731
        B.face([v3(p, h) for p in T], 120, pid)
        B.face([v3(p, 0) for p in reversed(O)], 116, pid)
        for k in range(nO):
            k1 = (k + 1) % nO
            zt = h - drop[k]
            wall = 118 if k != bevel_edge else pal
            B.face([v3(O[k], 0), v3(O[k1], 0), v3(O[k1], zt), v3(O[k], zt)], 118 if k != bevel_edge else 116, pid)
            B.face([v3(O[k], zt), v3(O[k1], zt), v3(T[k1], h), v3(T[k], h)], pal if k == bevel_edge else 119, pid)
            # corner closure where the two edges' bevel heights differ
            zp = h - drop[k - 1]
            if abs(zp - zt) > 1e-6:
                B.face([v3(O[k], min(zp, zt)), v3(O[k], max(zp, zt)), v3(T[k], h)][:: (1 if zp < zt else -1)],
                       pal, pid)
            del wall


def tube(B, pid, a, b, r, z, pal, sides=8):
    a, b = Vector((a.x, a.y, z)), Vector((b.x, b.y, z))
    d = (b - a).normalized()
    u = d.cross(Vector((0, 0, 1)))
    if u.length < 1e-6:
        u = Vector((1, 0, 0))
    u.normalize()
    v = d.cross(u)
    ra = [a + (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * r for k in range(sides)]
    rb = [p + (b - a) for p in ra]
    for k in range(sides):
        k1 = (k + 1) % sides
        f = B.face([ra[k], ra[k1], rb[k1], rb[k]], pal, pid)
        f.smooth = True
    B.face(list(reversed(ra)), pal, pid)
    B.face(rb, pal, pid)


def cyl_z(B, pid, centre, r, z0, z1, pal_side, pal_cap_bot, pal_cap_top, sides=12, r1=None):
    r1 = r if r1 is None else r1
    lo = [Vector((centre.x + r * math.cos(2 * math.pi * k / sides), centre.y + r * math.sin(2 * math.pi * k / sides), z0))
          for k in range(sides)]
    hi = [Vector((centre.x + r1 * math.cos(2 * math.pi * k / sides), centre.y + r1 * math.sin(2 * math.pi * k / sides), z1))
          for k in range(sides)]
    for k in range(sides):
        k1 = (k + 1) % sides
        f = B.face([lo[k], lo[k1], hi[k1], hi[k]], pal_side, pid)
        f.smooth = True
    B.face(list(reversed(lo)), pal_cap_bot, pid)
    B.face(hi, pal_cap_top, pid)


def build_frame(B):
    for i, (a, b) in enumerate(RODS):
        pid = B.begin(f"rod{i}")
        tube(B, pid, E(*a), E(*b), ROD_R, ROD_Z - (0.0 if i < 3 else 0.0), 4)
    for i, (c, r) in enumerate(NODES):
        pid = B.begin(f"node{i}")
        cyl_z(B, pid, E(c, r), 0.24, ROD_Z - 0.2, -0.02, 7, 7, 7, sides=10)
    for i, (c, r) in enumerate(JETS):
        pid = B.begin(f"jet{i}")
        p = E(c, r)
        cyl_z(B, pid, p, 0.30, -0.75, ROD_Z - 0.2, 4, 4, 4, sides=12, r1=0.26)
        cyl_z(B, pid, p, 0.22, -0.85, -0.75, 7, 4, 7, sides=12)


def outline_shell_all(obj, collection, voxel=0.011, faces=4000, smooth=4, inside=0.003):
    """common.outline_shell, but keeping every island (the sign is many separate letters; the
    shared helper keeps only the largest). Built from a sealed copy of the letters only (the thin
    raceway and jets get no ink)."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -inside
        common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def to_object(name, B, mats, coll, scale=U):
    bm = B.bm
    # weld and orient each part on its own: parts overlap (strokes cross inside a glyph), and a
    # weld across parts would join solids at shared points and confuse the normals
    lay = bm.faces.layers.int.get("part")
    byp = {}
    for f in bm.faces:
        byp.setdefault(f[lay], []).append(f)
    for faces in byp.values():
        vs = list({v for f in faces for v in f.verts})
        bmesh.ops.remove_doubles(bm, verts=vs, dist=1e-5)
    byp = {}
    for f in bm.faces:
        byp.setdefault(f[lay], []).append(f)
    for faces in byp.values():
        bmesh.ops.recalc_face_normals(bm, faces=faces)
    bmesh.ops.scale(bm, vec=(scale, scale, scale), verts=bm.verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def build(g, sprite):
    coll = common.reset_collection(NAME)
    pals = [120, 119, 118, 117, 116, 114, 4, 7]
    mats = []
    for p in pals:
        if p in GLOW:
            mats.append(common.palette_material(sprite, p, TAG, metallic=1.0, roughness=0.9, emission_strength=GLOW[p]))
        elif p == 4:
            mats.append(common.palette_material(sprite, p, TAG, metallic=0.6, roughness=0.42))
        else:
            mats.append(common.palette_material(sprite, p, TAG, metallic=0.7, roughness=0.35))
    slot = {p: k for k, p in enumerate(pals)}
    # letters (the outline shell is made from this object alone)
    L = Builder(slot)
    build_letters(L, g, BIG, H_BIG, "WARNING_")
    build_flanks(L, g)
    build_letters(L, g, SMALL, H_SMALL, "MS_")
    build_dots(L)
    build_bars(L)
    build_fins(L)
    letters = to_object(NAME + "_letters", L, mats, coll)
    F = Builder(slot)
    build_frame(F)
    frame = to_object(NAME + "_frame", F, mats, coll)
    parts = L.parts + F.parts
    # offset frame part ids so the joined object keeps unique ids
    off = len(L.parts)
    for poly, v in zip(frame.data.polygons, frame.data.attributes["part"].data):
        v.value += off
    return letters, frame, parts, coll


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def drop_strays(obj):
    """split_assembly keeps faces lying exactly on a cut plane; drop those that join nothing inside."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    eps = 1e-5

    def on_edge(f):
        return any(all(abs(v.co.x - b) < eps for v in f.verts) for b in (-1.0, 1.0)) or \
            any(all(abs(v.co.y - b) < eps for v in f.verts) for b in (-14 / 12, 14 / 12))

    flat = {f for f in bm.faces if on_edge(f)}
    stray = [f for f in flat if all(set(e.link_faces) <= flat for e in f.edges)]
    bmesh.ops.delete(bm, geom=stray, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    g, sprite = load_grid()
    letters, frame, parts, coll = build(g, sprite)
    for o in (letters, frame):
        if "part" in o.data.attributes:
            o.data.attributes.remove(o.data.attributes["part"])
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    lp = common.split_assembly(letters, layout)
    fp = common.split_assembly(frame, layout)
    export = []
    for name in PIECES:
        drop_strays(lp[name])
        drop_strays(fp[name])
        shell = outline_shell_all(lp[name], coll)  # ink from this piece's letters only
        shell.name = f"{name}_outline"
        piece = join([lp[name], fp[name]], name)
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [piece, shell], f"enemies/{name}", data["sprites"])
        export.append((piece, shell))
        print(f"{name}: {sum(len(p.vertices) - 2 for p in piece.data.polygons)} tris, shell {len(shell.data.polygons)} faces")


if __name__ == "__main__":
    main()
