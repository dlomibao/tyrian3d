"""Rock wall with purple octagon hatches (newsh2.shp 273 | 275 | 277, enemy types 32-34): hard-surface,
as the player ships (DECISIONS.md D50-D53).

Seen in episode 1 (level 1.3) and episode 3. A row of 2x2 pieces (sprite.json `assemblyLayout`, 96 x 28
px as built here): newsh2-273 at the left end, newsh2-275 repeated in the middle and newsh2-277 at the
right end. The same wall as assembly-newsh2-279.

The sprite is authoritative (D52): every tile holds one big purple octagon armour hatch (sprite rows
4-19), a purple rampart band runs along the top behind the hatches (rows 0-4), a lighter purple wedge
housing fills the V between each pair of hatches, and grey and beige boulders fill the rest, all where
the sprite draws them; each part takes the sprite's own palette index there (the trimmed median of
that region's pixels: hatch 88, band 89, wedge 90, stone 6 and its neighbours, beige 170). Satin
purple metal, matte stone. The concept (assets/blender/features/concepts/assembly-newsh2-273.jpg) only
guides the side, front and rear.

The machine (sprite px: c east, r south, z up; 1 px = 1/12 unit):
- each hatch is a heavy armoured block standing a tier above everything else: a dark collar, an
  undercut skirt with a machined groove round it and vertical stiffener ribs on the five faces the
  camera sees, a broad chamfer (the sprite's lit rim), and on its dark (86) top an outer and an inner
  ring of eight separate armour plates with real gaps between them, a well with eight recessed slots,
  four lifting tabs, a hub with a cap, and two hinge knuckles on a pin joining it to the band;
- the band is a stepped rampart beam with raised, bolted panels; between the hatches an armoured
  block with cooling ribs sits on it and a lighter (90) wedge housing with an inset plate and a spine
  drops into the V, with a slatted vent at its foot and a ram bracket with two lugs in the crevice;
- the grey boulders are rounded, smooth-shaded cobbles (as the sprite shades them, and as
  assembly-newsh2-279's stones) with slightly leaning crowns; the beige stones are closed, convex,
  smooth rounded stones;
- the underside is only the closed foundation slab (no detail: almost never seen).

Texture: no concept projection (maps.json "bake": "model"); an ambient-occlusion / edge colour
multiplier and a roughness / metalness map baked with Cycles, as the player ships, one small atlas
per piece (baked in the row with its neighbours as occluders), so a GLB carries only its own. Outline shell as
common.outline_shell (D51), cut into the pieces without filling the seams.

Built whole in assembly coordinates (left, two middles, right) and cut into the pieces with
common.split_assembly (pivot = each piece's centre); everything per tile repeats with a 24 px period,
so the middle piece tiles. Each piece goes to public/models/enemies/<piece>.glb with its
src/render/spriteModels/<piece>.json entry (common.export_sprite_model).

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newsh2-273.py
     [-- --no-bake] [--out row.glb] [--no-export] [--preview out.png]
--out also writes the whole row (pieces at their assembly places, the middle one twice) for checks;
--no-export skips writing the game models.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh2-273"
TILES = ["newsh2-273", "newsh2-275", "newsh2-275", "newsh2-277"]
KINDS = ["left", "mid", "mid", "right"]
TW, TH = 24, 28
NT = len(TILES)
W = TW * NT

# Heights in sprite px (z). Low to high: bed, band, wedge, housing, rocks, hatch, hub.
BED_BOT, BED_TOP = -1.8, 0.5
Z = dict(band=2.4, band_panel=3.0, housing=3.8, housing_panel=4.25, wedge=3.4,
         hatch_skirt=4.4, hatch=6.2, plate_o=6.75, plate_i=6.6, well=6.3, hub=7.3, cap=7.55)
OCT = [(8.5, 4), (15.5, 4), (21, 9.5), (21, 14.5), (15.5, 20), (8.5, 20), (3, 14.5), (3, 9.5)]


# ---- 2D helpers (sprite px: c east, r south) --------------------------------------------------

def area(p):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) / 2


def offset(p, d):
    """Offset a convex polygon inwards by d (either winding)."""
    s = 1 if area(p) > 0 else -1
    n = len(p)
    lines = []
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        nx, ny = (-dy / ln, dx / ln) if s > 0 else (dy / ln, -dx / ln)
        lines.append((a[0] + nx * d, a[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        A, B = lines[i - 1], lines[i]
        den = A[2] * B[3] - A[3] * B[2]
        if abs(den) < 1e-9:
            out.append((B[0], B[1]))
            continue
        t = ((B[0] - A[0]) * B[3] - (B[1] - A[1]) * B[2]) / den
        out.append((A[0] + A[2] * t, A[1] + A[3] * t))
    return out


def centroid(p):
    a = area(p)
    cx = sum((p[i][0] + p[i - 1][0]) * (p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1]) for i in range(len(p)))
    cy = sum((p[i][1] + p[i - 1][1]) * (p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1]) for i in range(len(p)))
    return cx / (6 * a), cy / (6 * a)


def scaled(p, s, ctr):
    return [(ctr[0] + (c - ctr[0]) * s, ctr[1] + (r - ctr[1]) * s) for c, r in p]


def hull(pts):
    pts = sorted(set(pts))
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])  # noqa: E731
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def clip_rect(p, x0, y0, x1, y1):
    def clip(poly, inside, inter):
        out = []
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            ia, ib = inside(a), inside(b)
            if ia:
                out.append(a)
            if ia != ib:
                out.append(inter(a, b))
        return out
    lx = lambda x: lambda a, b: (x, a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))  # noqa: E731
    ly = lambda y: lambda a, b: (a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), y)  # noqa: E731
    p = clip(p, lambda q: q[0] >= x0, lx(x0))
    p = clip(p, lambda q: q[0] <= x1, lx(x1))
    p = clip(p, lambda q: q[1] >= y0, ly(y0))
    p = clip(p, lambda q: q[1] <= y1, ly(y1))
    # drop near-duplicate points (a hull vertex on the clip line), which would make sliver faces
    out = []
    for q in p:
        if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 0.08:
            out.append(q)
    if len(out) > 3 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= 0.08:
        out.pop()
    return out


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def ngon(cx, cy, r, n=8, rot=math.pi / 8):
    return [(cx + math.cos(rot + 2 * math.pi * k / n) * r, cy + math.sin(rot + 2 * math.pi * k / n) * r)
            for k in range(n)]


def inside(p, x, y):
    c = False
    j = len(p) - 1
    for i in range(len(p)):
        if (p[i][1] > y) != (p[j][1] > y) and x < (p[j][0] - p[i][0]) * (y - p[i][1]) / (p[j][1] - p[i][1]) + p[i][0]:
            c = not c
        j = i
    return c


def rnd(seed, k):
    return math.sin(seed * 12.9898 + k * 78.233) * 0.5 + 0.5


# ---- sprite --------------------------------------------------------------------------------------

def sprite_grid(root):
    rows = [[] for _ in range(TH)]
    for t in TILES:
        px = common.load_sprite(root, t)["frames"][0]["pixels"]
        for r in range(TH):
            rows[r] += px[r]
    return rows


def cls(v):
    if v < 0:
        return "."
    if 84 <= v <= 92:
        return "P"
    if v >= 167:
        return "B"
    return "G"


def trimmed_median(vals):
    if not vals:
        return None
    a = sorted(vals)
    k = int(len(a) * 0.15)
    b = a[k:len(a) - k] or a
    return b[(len(b) - 1) // 2]


# ---- mesh building -------------------------------------------------------------------------------

class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.mat_index = {}

    def mat(self, pal):
        if pal not in self.mat_index:
            self.mat_index[pal] = len(self.mat_index)
        return self.mat_index[pal]

    def v(self, c, r, z):
        return self.bm.verts.new(((c - W / 2) / 12, (TH / 2 - r) / 12, z / 12))

    def faces_from_rings(self, rings, pal, top_pal=None, apex=None, smooth=False):
        m = self.mat(pal)
        n = len(rings[0])
        faces = []
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                faces.append(self.bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
        tm = self.mat(top_pal if top_pal is not None else pal)
        if apex is not None:
            a = self.v(*apex)
            top = [self.bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], a)) for i in range(n)]
        else:
            top = [self.bm.faces.new(rings[-1])]
        bot = self.bm.faces.new(list(reversed(rings[0])))
        for f in faces + [bot]:
            f.material_index = m
            f.smooth = smooth and f is not bot  # the buried bottom cap stays flat: no bent foot normals
        for f in top:
            f.material_index = tm
            f.smooth = smooth

    def loft(self, pal, poly, prof, top_pal=None):
        """Footprint `poly` offset inwards by prof[i][0] at height prof[i][1], capped both ends."""
        rings = [[self.v(c, r, z) for c, r in (offset(poly, d) if d else poly)] for d, z in prof]
        self.faces_from_rings(rings, pal, top_pal)


def build(B, grid):
    # 1. Foundation slab: the dark cast bed between the stones; its underside tapers in a little so
    # it reads as a closed block from low angles. No detail underneath.
    B.loft(4, rect(0, 0, W, TH), [(0.9, BED_BOT), (0.3, BED_BOT + 0.5), (0, -0.6), (0, BED_TOP - 0.3), (0.35, BED_TOP)])

    # 2. Rampart band along the top (sprite rows 0-4): stepped rear face, raised panels (90 / 89, as
    # the sprite's lighter and darker band panels) with bolt heads.
    bx0, bx1 = 13, W - 12
    B.loft(89, rect(bx0, 0.0, bx1, 4.4), [(0, BED_TOP - 0.3), (0, 1.2), (0.35, 1.55), (0.35, 1.95), (0.7, Z["band"])])
    for t in range(NT):
        o = t * TW
        for a, b, pal in ((5, 11.6, 90), (12.5, 19.2, 89)):
            if o + a < bx0 or o + b > bx1:
                continue
            B.loft(pal, rect(o + a, 0.45, o + b, 3.9),
                   [(0, Z["band"] - 0.3), (0, Z["band_panel"] - 0.35), (0.4, Z["band_panel"])])
            for bx in (o + a + 0.9, o + b - 0.9):
                B.loft(86, ngon(bx, 1.0, 0.32, 6, 0),
                       [(0, Z["band_panel"] - 0.1), (0, Z["band_panel"] + 0.12), (0.1, Z["band_panel"] + 0.2)])

    # 3. Seam housings between the hatches: an armoured block on the band with cooling ribs, a
    # lighter wedge filling the V between the hatches (the sprite's 90/91 wedge, rows 4-11) with an
    # inset plate and a spine, a slatted vent at its foot and a ram bracket with two lugs below.
    for t in range(1, NT):
        s = t * TW
        B.loft(88, rect(s - 4.2, 0.2, s + 4.2, 4.3), [(0, BED_TOP), (0, Z["housing"] - 0.6), (0.6, Z["housing"])])
        B.loft(89, rect(s - 3.0, 1.0, s + 3.0, 3.6),
               [(0, Z["housing"] - 0.2), (0, Z["housing_panel"] - 0.25), (0.35, Z["housing_panel"])])
        for k in range(3):
            B.loft(86, rect(s - 2.4, 1.5 + k * 0.75, s + 2.4, 1.5 + k * 0.75 + 0.3),
                   [(0, Z["housing_panel"] - 0.1), (0, Z["housing_panel"] + 0.12)])
        wedge = [(s - 9.0, 4.0), (s + 9.0, 4.0), (s + 3.0, 10.0), (s + 3.0, 11.0), (s - 3.0, 11.0), (s - 3.0, 10.0)]
        B.loft(90, wedge, [(0, BED_TOP), (0, Z["wedge"] - 0.7), (0.7, Z["wedge"])])
        B.loft(90, offset(wedge[:3] + [(s - 3.0, 10.0)], 1.0),
               [(0, Z["wedge"] - 0.2), (0, Z["wedge"] + 0.05), (0.2, Z["wedge"] + 0.2)])
        B.loft(90, [(s - 1.6, 4.3), (s + 1.6, 4.3), (s + 1.0, 9.6), (s - 1.0, 9.6)],
               [(0, Z["wedge"] - 0.2), (0, Z["wedge"] + 0.2), (0.3, Z["wedge"] + 0.4)])
        B.loft(2, rect(s - 2.4, 11.0, s + 2.4, 11.9), [(0, BED_TOP), (0, 2.6)])
        for k in range(3):
            zz = 0.9 + k * 0.6
            B.loft(5, rect(s - 2.1, 11.05, s + 2.1, 11.95 - k * 0.12), [(0, zz), (0, zz + 0.22)])
        B.loft(4, rect(s - 1.2, 12.1, s + 1.2, 14.6), [(0, BED_TOP), (0, 1.6), (0.3, 1.9)])
        for x0 in (s - 3.2, s + 1.2):  # the two ram lugs
            B.loft(3, rect(x0, 12.8, x0 + 2.0, 13.9), [(0, 0.9), (0, 1.6), (0.2, 1.8)])

    # 4. Octagon hatches.
    for t in range(NT):
        o = t * TW
        oct_ = [(o + c, r) for c, r in OCT]
        cx, cy = o + 12, 12
        B.loft(85, offset(oct_, 0.9), [(0, BED_TOP - 0.2), (0, 1.2)])
        # The armour block: undercut foot, skirt with a machined groove round it, chamfer (the
        # sprite's lit rim) up to a dark (86) top that carries the plates.
        B.loft(88, oct_, [(0.55, 0.9), (0, 1.5), (0, 2.6), (0.22, 2.72), (0.22, 2.98), (0, 3.1),
                          (0, Z["hatch_skirt"]), (0.35, Z["hatch_skirt"] + 0.7), (1.0, Z["hatch_skirt"] + 1.4),
                          (1.5, Z["hatch"])], top_pal=86)
        # Stiffener ribs on the five skirt faces the camera and the sides see (E, SE, S, SW, W).
        for i in range(2, 7):
            a, b = oct_[i], oct_[(i + 1) % 8]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = ty, -tx
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if (mx + nx - cx) ** 2 + (my + ny - cy) ** 2 < (mx - cx) ** 2 + (my - cy) ** 2:
                nx, ny = -nx, -ny
            for f in ((0.25, 0.5, 0.75) if L > 6 else (0.3, 0.7)):
                px, py = a[0] + tx * L * f, a[1] + ty * L * f
                hw, d = 0.3, 0.4
                q = [(px - tx * hw - nx * 0.05, py - ty * hw - ny * 0.05), (px + tx * hw - nx * 0.05, py + ty * hw - ny * 0.05),
                     (px + tx * hw + nx * d, py + ty * hw + ny * d), (px - tx * hw + nx * d, py - ty * hw + ny * d)]
                B.loft(87, q, [(0, 1.3), (0, Z["hatch_skirt"] - 0.25), (0.15, Z["hatch_skirt"] + 0.05)])
        # Outer and inner rings of eight separate armour plates, real gaps over the dark top.
        top = offset(oct_, 1.62)
        mid_o = offset(oct_, 3.4)
        mid_i = offset(oct_, 3.75)
        well = offset(oct_, 5.5)
        gap = 0.26
        for i in range(8):
            j = (i + 1) % 8
            B.loft(88, offset([top[i], top[j], mid_o[j], mid_o[i]], gap),
                   [(0, Z["hatch"] - 0.2), (0, Z["plate_o"] - 0.3), (0.3, Z["plate_o"])])
            B.loft(88, offset([mid_i[i], mid_i[j], well[j], well[i]], gap),
                   [(0, Z["hatch"] - 0.2), (0, Z["plate_i"] - 0.26), (0.26, Z["plate_i"])])
        B.loft(88, well, [(0, Z["hatch"] - 0.2), (0.2, Z["well"])])
        for k in range(8):
            a = math.pi / 8 + 2 * math.pi * k / 8
            ux, uy = math.cos(a), math.sin(a)
            rr, hw, hl = 3.25, 0.25, 0.8
            g = [(cx + ux * (rr - hw) - uy * hl, cy + uy * (rr - hw) + ux * hl), (cx + ux * (rr + hw) - uy * hl, cy + uy * (rr + hw) + ux * hl),
                 (cx + ux * (rr + hw) + uy * hl, cy + uy * (rr + hw) - ux * hl), (cx + ux * (rr - hw) + uy * hl, cy + uy * (rr - hw) - ux * hl)]
            B.loft(85, g, [(0, Z["well"] - 0.1), (0, Z["well"] + 0.03)])
        # Four lifting tabs on the ring seam, each with a dark eye.
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            px, py = cx + dx * 5.6, cy + dy * 5.6
            hx, hy = (0.6, 1.15) if dx else (1.15, 0.6)
            B.loft(89, rect(px - hx, py - hy, px + hx, py + hy),
                   [(0, Z["plate_i"] - 0.2), (0, Z["plate_o"] + 0.12), (0.15, Z["plate_o"] + 0.3)])
            B.loft(85, ngon(px, py, 0.32, 6, 0), [(0, Z["plate_o"] + 0.2), (0, Z["plate_o"] + 0.33)])
        # Two hinge knuckles on a pin, joining the hatch to the band behind it.
        B.loft(86, rect(o + 9.0, 3.85, o + 15.2, 4.5), [(0, Z["band"] - 0.4), (0, Z["band"] + 0.9), (0.15, Z["band"] + 1.1)])
        for hx in (9.2, 13.4):
            B.loft(88, rect(o + hx, 3.8, o + hx + 1.6, 5.3),
                   [(0, Z["band"] - 0.4), (0, Z["hatch"] - 0.9), (0.45, Z["hatch"] - 0.35)])
        B.loft(88, ngon(cx, cy, 2.45), [(0, Z["well"] - 0.1), (0, Z["hub"] - 0.5), (0.65, Z["hub"])])
        B.loft(89, ngon(cx, cy, 1.2), [(0, Z["hub"] - 0.1), (0.2, Z["cap"])])

    # 5. Stones, where the sprite draws them; palette = the sprite's own pixels under each stone.
    seed = [1]

    def stone(x, y, rx, ry, beige=False, h=None, slot=None, pal_dx=0.0):
        """slot: the stone's index in the per-tile pattern; such stones take the same shape (seed)
        and colour (sampled at the middle tile 2, pal_dx away) on every tile, so stones crossing a
        tile edge match across the cut and the middle piece tiles seamlessly. Rings are the convex
        outline scaled toward its centroid (never inverted), so every stone is a closed convex solid."""
        if slot is not None:
            sd = 100 + slot
        else:
            sd = seed[0]
            seed[0] += 1
        n = 9 + sd % 3
        pts = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.35 * (rnd(sd, k) - 0.5)) / n
            rr = 0.92 + 0.12 * (math.sin(sd * 4.1 + k * 2.7) * 0.5 + 0.5)
            pts.append((x + math.cos(a) * rx * rr, y + math.sin(a) * ry * rr))
        pts = clip_rect(hull(pts), 0.02, 0.02, W - 0.02, TH - 0.02)
        if area(pts) < 0:
            pts = pts[::-1]
        ctr = centroid(pts)
        mr = min(rx, ry)
        hh = h if h is not None else min(3.5, 0.8 * mr + 0.6)
        vals = []
        sx = x + pal_dx
        spts = [(c + pal_dx, r) for c, r in pts]
        for r in range(math.floor(y - ry), math.ceil(y + ry) + 1):
            for c in range(math.floor(sx - rx), math.ceil(sx + rx) + 1):
                if not (0 <= r < TH and 0 <= c < W):
                    continue
                v = grid[r][c]
                k = cls(v)
                if k in "P." or not inside(spts, c + 0.5, r + 0.5):
                    continue
                if (k == "B") == beige:
                    vals.append(v)
        pal = trimmed_median(vals)
        if pal is None:
            pal = 170 if beige else 7
        if beige:
            # A smooth, rounded stone: a quarter-ellipse profile closed by an apex.
            rings = []
            for k, th in enumerate((0, 20, 42, 62, 78)):
                s = math.cos(math.radians(th)) if k else 1.0
                z = BED_TOP - 0.2 if k == 0 else BED_TOP + hh * math.sin(math.radians(th))
                rings.append([B.v(c, r, z) for c, r in scaled(pts, max(s, 0.2), ctr)])
            B.faces_from_rings(rings, pal, apex=(ctr[0], ctr[1], BED_TOP + hh), smooth=True)
            return
        # A rounded grey cobble, smooth shaded as the sprite draws it: a full, slightly flattened
        # dome (superellipse profile) whose crown leans a little one way and whose rings are nudged
        # a touch, so no two stones are the same; the buried bottom ring stays flat shaded so the
        # smooth normals don't bend down at the foot.
        tx = (rnd(sd, 91) - 0.5) * 2
        ty = (rnd(sd, 37) - 0.5) * 2
        rings = []
        for si, th in enumerate((0, 16, 32, 48, 62, 75)):
            s = math.cos(math.radians(th)) ** 0.55 if si else 1.0
            z = BED_TOP - 0.2 if si == 0 else BED_TOP + hh * math.sin(math.radians(th))
            lean = 0.12 * hh * (th / 75) ** 1.5
            ring = []
            for k, (c, r) in enumerate(scaled(pts, max(s, 0.22), ctr)):
                dz = 0.0
                if si >= 2:
                    dz = ((c - ctr[0]) / max(rx, 0.1) * tx + (r - ctr[1]) / max(ry, 0.1) * ty) * lean
                    dz += (rnd(sd * 3 + si, k) - 0.5) * 0.05 * hh
                ring.append(B.v(c, r, z + dz))
            rings.append(ring)
        B.faces_from_rings(rings, pal, apex=(ctr[0], ctr[1], BED_TOP + hh), smooth=True)

    for t, kind in enumerate(KINDS):
        o = t * TW
        dx = 48 - o  # sample colours at tile 2 (a middle tile between two middle tiles)
        stone(o - 1.0 + (0.6 if t == 0 else 0), 19.6, 5.4, 4.3, h=3.7, slot=None if t == 0 else 0, pal_dx=0 if t == 0 else dx)
        stone(o + 5.4, 22.6, 3.6, 2.6, slot=1, pal_dx=dx)
        stone(o + 9.6, 22.4, 2.0, 1.9, slot=2, pal_dx=dx)
        stone(o + 17.6, 22.4, 2.8, 2.4, slot=3, pal_dx=dx)
        stone(o + 1.2, 25.6, 1.9, 2.0, slot=4, pal_dx=dx)
        stone(o + 6.3, 27.7, 4.8, 2.15, beige=True, h=2.6, slot=5, pal_dx=dx)
        stone(o + 13.4, 26.5, 2.6, 1.6, slot=6, pal_dx=dx)
        stone(o + 20.0, 26.0, 4.0, 2.1, slot=7, pal_dx=dx)
        if t > 0:
            stone(o + 1.4, 13.6, 1.4, 2.0, h=1.4, slot=8, pal_dx=dx)
        if kind == "left":
            stone(5.3, 1.5, 5.8, 3.45, beige=True, h=2.6)
            stone(12.0, 2.0, 1.25, 2.2)
            stone(1.4, 10.6, 1.6, 4.6)
            stone(2.6, 6.3, 2.6, 1.4)
        if kind == "right":
            stone(o + 16.0, 2.0, 3.4, 2.4)
            stone(o + 21.2, 2.2, 2.7, 2.4)
            stone(o + 22.2, 7.8, 1.7, 3.6)
            stone(o + 22.4, 13.2, 1.5, 2.0)
    stone(W - 2.4, 19.6, 2.6, 4.3, h=3.6)


MAT_STYLE = {  # (metallic, roughness) per palette family: satin purple metal, matte stone
    "P": (0.3, 0.55),
    "B": (0.0, 0.8),
    "G": (0.0, 0.9),
}


def make_row(root):
    grid = sprite_grid(root)
    sprite = common.load_sprite(root, TILES[0])
    for t in TILES[1:]:
        sprite["colors"].update(common.load_sprite(root, t)["colors"])
    coll = common.reset_collection(NAME)
    B = Builder()
    build(B, grid)
    bm = B.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    tag = "a" + NAME.split("assembly-")[1]
    mats = [None] * len(B.mat_index)
    for pal, idx in B.mat_index.items():
        metal, rough = MAT_STYLE[cls(pal)] if cls(pal) != "." else (0.0, 0.9)
        if pal in (2, 3, 4, 5):  # vent, rams and the bed: dark steel, not stone
            metal, rough = 0.3, 0.6
        mats[idx] = common.palette_material(sprite, pal, tag, metallic=metal, roughness=rough)
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, coll


# --- bake (as the ships: occlusion / edge colour multiplier, roughness / metalness) ---------------

def bake_maps(obj, out_dir, size=512, samples=64, prefix="nsh2_273"):
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
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
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
    col_img = bpy.data.images.new(f"{prefix}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{prefix}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
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
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
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
                L(v, comb.inputs[k])
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
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        if mode == "colour":
            import numpy as np
            px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            px = px.reshape(-1, 4)
            px[px[:, 0] < 0.3] = (0.85, 0.85, 0.85, 1.0)  # unbaked texels (the bake writes >= 0.48)
            img.pixels.foreach_set(px.ravel())
        if mode == "rm":
            # A floor on the roughness: a sub-texel face (a rib's chamfer) can sample an unbaked
            # (black) texel, which would read as a mirror-smooth white speck.
            import numpy as np
            px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            px = px.reshape(-1, 4)
            unbaked = px[:, 0] < 0.5  # the bake writes R = 1 everywhere it reaches
            px[unbaked] = (1.0, 0.6, 0.3, 1.0)
            px[:, 1] = np.maximum(px[:, 1], 0.32)
            img.pixels.foreach_set(px.ravel())
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


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no outline along the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def seam_normals(parts, row, layout):
    """Stones that cross a tile edge are cut in two; each half would shade from its own faces only,
    a crease down the cut. Give the smooth (stone) vertices of each piece the row's own normals
    (custom normals by data transfer), so the halves shade as one stone. Vertices of flat faces
    keep theirs."""
    for name, cx, cy in layout:
        piece = parts[name]
        me = piece.data
        def on_cut(p):  # a cap that split_assembly filled at the cut (x = +-1, y = +-14/12)
            return all(abs(abs(me.vertices[v].co.x) - 1.0) < 1e-4 for v in p.vertices) or \
                all(abs(abs(me.vertices[v].co.y) - 14 / 12) < 1e-4 for v in p.vertices)
        flat = {v for p in me.polygons if not p.use_smooth and not on_cut(p) for v in p.vertices}
        vg = piece.vertex_groups.new(name="smooth")
        vg.add([v.index for v in me.vertices if v.index not in flat], 1.0, "REPLACE")
        row.location = (-cx / 12, cy / 12, 0)
        bpy.context.view_layer.update()
        mod = piece.modifiers.new("seam", "DATA_TRANSFER")
        mod.object = row
        mod.use_loop_data = True
        mod.data_types_loops = {"CUSTOM_NORMAL"}
        mod.loop_mapping = "POLYINTERP_NEAREST"
        mod.vertex_group = vg.name
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = piece
        piece.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        piece.vertex_groups.remove(piece.vertex_groups["smooth"])
    row.location = (0, 0, 0)
    bpy.context.view_layer.update()


def bake_pieces(parts, row_tiles, centres, out_dir):
    """Bake each piece into its own small atlas (512 colour, 256 roughness / metalness: the same
    texel density as one 1024 atlas over the row, a quarter of the bytes per GLB). Each piece bakes
    at its place in the row with its neighbours there as occluders (and nothing else render
    visible), so the occlusion runs on across the seams as on the whole row. The piece gets its own
    copies of the palette materials (still named pal_<index>_..., so palettes, fades and the hit
    flash work) carrying its atlas."""
    scene_objs = list(bpy.context.scene.objects)
    for p, obj in parts.items():
        me = obj.data
        for i, m in enumerate(me.materials):
            c = m.copy()
            c.name = f"{m.name}_{p.split('-')[1]}"
            me.materials[i] = c
        i0 = row_tiles.index(p)
        temps = []
        for i, (t, (cx, cy)) in enumerate(zip(row_tiles, centres)):
            if i == i0:
                continue
            o = bpy.data.objects.new(f"occl_{p}_{i}", parts[t].data)
            bpy.context.scene.collection.objects.link(o)
            o.location = (cx / 12, -cy / 12, 0)
            temps.append(o)
        saved = {o.name: o.hide_render for o in scene_objs}
        for o in scene_objs:
            o.hide_render = o is not obj
        cx, cy = centres[i0]
        obj.location = (cx / 12, -cy / 12, 0)
        bpy.context.view_layer.update()
        bake_maps(obj, out_dir, prefix=f"nsh2_{p.split('-')[1]}")
        obj.location = (0, 0, 0)
        for o in temps:
            bpy.data.objects.remove(o)
        for o in scene_objs:
            o.hide_render = saved[o.name]


def main(script_file):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(script_file)
    obj, coll = make_row(root)
    print(f"{NAME} row: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    centres = [(TW * i + TW / 2 - W / 2, 0) for i in range(NT)]
    layout, seen = [], set()
    for t, (cx, cy) in zip(TILES, centres):
        if t not in seen:
            seen.add(t)
            layout.append((t, cx, cy))
    parts = common.split_assembly(obj, layout, coll)
    seam_normals(parts, obj, layout)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_pieces(parts, TILES, centres, tempfile.mkdtemp(prefix="nsh2_273_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.014, faces=4000)
    shells = split_open(shell, layout, coll)
    for p, _, _ in layout:
        print(f"{NAME} piece {p}: {sum(len(f.vertices) - 2 for f in parts[p].data.polygons)} triangles, "
              f"outline {len(shells[p].data.polygons)} faces")
    if "--no-export" not in argv:
        for p, _, _ in layout:
            data = common.load_sprite(root, p)
            common.export_sprite_model(root, [parts[p], shells[p]], f"enemies/{p}", data["sprites"], image_format=fmt)
    if "--out" in argv:
        # The row as the game lays it out (a check file only): each piece at its tile, the middle
        # piece twice (a linked copy, never exported as a model of its own).
        objs = []
        for i, (t, (cx, cy)) in enumerate(zip(TILES, centres)):
            for src in (parts[t], shells[t]):
                o = bpy.data.objects.new(f"{src.name}.row{i}", src.data)
                for k in src.keys():
                    o[k] = src[k]
                coll.objects.link(o)
                o.location = (cx / 12, -cy / 12, 0)
                objs.append(o)
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb(objs, out, image_format=fmt)
        print("wrote", out)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for p, _, _ in layout:
            data = common.load_sprite(root, p)
            img = root / "reference" / "models" / p / data["frames"][0]["image"]
            common.render_preview([parts[p]], str(out.parent / f"{p}.png"), str(img), size=2)


if __name__ == "__main__":
    main(__file__)
