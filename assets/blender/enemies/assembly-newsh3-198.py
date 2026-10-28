"""Rock arch (newsh3.shp 162, 164, 241 over 198, 200, 202, 279, 281): a 3D version of its sprites.

Seen in episode 4 (levels 4.2 and 4.29). Eight 2x2 pieces make one 120x56 px span of a sandy rock
arch: from its left foot (198) it climbs to a crown of big faceted boulders (162, 164, 241) and
comes down to the right (279, 281), with the darker, striated inside of the arch under the crown
and open sky through it. The arch carries on past the right and bottom edges (pieces the game
places elsewhere), so the rock isn't rounded off there.

The arch is built once in assembly coordinates as one solid rock mound: its outline follows the
sprite pixel for pixel; across the band it rises from a low strip along the outer edge in a rounded
shoulder, then a broad top ramps gently up to a crest line about 19 px high under the crown (12 px
where the legs leave the sheet, cut off with a plain wall), and only over the last 8 px before the
opening does it drop, in an S, to a low lip, under which the rock is undercut in one smooth sweep
(down the legs the lip stays high). So the lit top faces up and towards the light, as in the
sprite. The heights are measured from a smoothed outline, so the sprite's pixel steps raise no
ridges. Each lit boulder rises gently from the crack on its upper-left side and drops steeply into
the sunk crack on its lower-right side, like the sprite's lit boulders and dark crack lines. Every facet
takes the sprite's colour under it. The top is smooth shaded; it is cut into the eight pieces
with common.split_assembly and each piece gets the whole arch's normals, so the shading runs on
across the cuts.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-198.py [-- --preview out.png]
(the preview is the whole arch; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b017 as lib  # noqa: E402

NAME = "assembly-newsh3-198"
ROOT = common.repo_root(__file__)
U = lib.U
# Each piece's top-left pixel in the assembly (its sprite.json assemblyLayout, one arch of the
# three in it: 198 at screen (56, 11) is column 0, row 28).
PLACEMENTS = [
    ("newsh3-162", 24, 0, 0), ("newsh3-164", 48, 0, 0), ("newsh3-241", 72, 0, 0),
    ("newsh3-198", 0, 28, 0), ("newsh3-200", 24, 28, 0), ("newsh3-202", 48, 28, 0),
    ("newsh3-279", 72, 28, 0), ("newsh3-281", 96, 28, 0),
]

# The mound's shape, in sprite px. Across the band the top is a broad face: a short rounded
# shoulder at the outer edge, then a gentle ramp up to a crest line FALL px from the opening, then
# an S-shaped drop to the lip (so the lit top faces up and towards the light, and only a narrow
# band near the opening faces away from it).
CREST = 19.5      # crest height under the crown
FOOT = 12.0       # crest height where the legs leave the sheet at the bottom (a plain cut wall)
LEG_ROW = 34      # rows above this are the crown (full crest height); below, the legs step down
SHOULDER = 6.0    # px from the outer edge to the top of its rounded shoulder...
SHOULDER_H = 0.55 # ... which is this share of the crest height
FALL = 8.0        # from the opening's edge back to the crest line
LIP = 0.2         # share of the local height left at the opening's edge under the crown...
LEG_LIP = 0.6     # ... and down the legs, which stay full-bodied to the sheet's bottom edge
LEG_ROWS = (40, 50)  # rows over which the lip changes from the one to the other
UNDERCUT = 7.0    # how far the rock under that lip is set back
UNDERCUT_SMOOTH = 6  # smoothing passes along the undercut's foot (no saw teeth under the lip)
EDGE = 0.3        # height at the outer edges
BOTTOM = 2.4      # depth of the underside
LOBE = 0.0        # px per unit of large-scale brightness above the mean
PILLOW = 3.5      # how far each lit boulder bulges between the cracks
PILLOW_R = 5.0    # px from the crack on a boulder's upper-left side to its top (a gentle lit face)...
PILLOW_STEEP = 1.3  # ... and from the crack on its lower-right side (a steep shaded drop)
CRACK = 1.8       # deepest crack
DARK_LUM = 0.42   # broad brightness under which the rock is the arch's shaded inside (no boulders)
SOFT_TOL = 1.6    # outline simplification for the distance fields (no stair-step ridges)
CHUNKS = [((20.5, 29.5), 7.0, 3.6)]  # the small lit boulder on the outer edge of the left leg: (c, r), height, radius
KEEP = [((4.0, 54.5), None, 2.5)]  # (the left foot's dark corner keeps its own pixels' colours too)
TOE = 0.9         # a low strip along the outline before the flank rises (no teeth at the ground)
CORNER = 3.0      # near the cut edges, the outer edge's distance is also measured from the raw outline
CORNER_LIFT = 0.8  # (plus this, so the foot keeps a low toe)
RINGS = (1.0, 2.0, 3.2, 4.7, 6.5, 8.6)  # rows of vertices along the smoothed outline, px in from it
RING_STEP = 1.3   # vertex spacing along those rows
STEP = 1.3        # interior facet size
BOTTOM_STEP = 5.0
TOL = 0.45        # outline simplification
TALL = 2.5        # ... and span more than this many px of height (not the cracks' small walls)
STEEP = 0.55      # facets steeper than this (normal z) take smoothed shades
OPENING_SEED = (75, 50)  # a pixel in the opening under the arch
CUT_COL, CUT_ROWS = 96, 28  # the crown's right end is cut (the rock carries on there)


def flood(mask, seed):
    """The empty pixels 4-connected to `seed`."""
    h, w = len(mask), len(mask[0])
    out = [[False] * w for _ in range(h)]
    stack = [seed]
    while stack:
        c, r = stack.pop()
        if 0 <= r < h and 0 <= c < w and not mask[r][c] and not out[r][c]:
            out[r][c] = True
            stack += [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
    return out


def clamp01(x):
    return max(0.0, min(1.0, x))


def smoothstep(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def chaikin(loop, iterations=3):
    """Corner-cut a closed polyline (rounds the sprite's pixel steps into a smooth line)."""
    for _ in range(iterations):
        n = len(loop)
        out = []
        for k in range(n):
            a, b = loop[k], loop[(k + 1) % n]
            out.append((a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25))
            out.append((a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75))
        loop = out
    return loop


class Segs:
    """Line segments with a coarse grid for nearest-distance queries."""

    def __init__(self, segs, cell=8.0):
        self.cell = cell
        self.grid = {}
        for a, b in segs:
            c0, c1 = sorted((a[0], b[0]))
            r0, r1 = sorted((a[1], b[1]))
            for gi in range(int(c0 // cell), int(c1 // cell) + 1):
                for gj in range(int(r0 // cell), int(r1 // cell) + 1):
                    self.grid.setdefault((gi, gj), []).append((a, b))

    def nearest(self, p, cap=40.0):
        """(distance, segment) of the nearest segment within `cap`, else (cap, None)."""
        gi, gj = int(p[0] // self.cell), int(p[1] // self.cell)
        best, seg = cap, None
        reach = 0
        while reach * self.cell <= best + self.cell:
            for di in range(-reach, reach + 1):
                for dj in range(-reach, reach + 1):
                    if max(abs(di), abs(dj)) != reach:
                        continue
                    for a, b in self.grid.get((gi + di, gj + dj), ()):
                        d = lib._seg_dist(p, a, b)
                        if d < best:
                            best, seg = d, (a, b)
            reach += 1
            if reach > cap / self.cell + 1:
                break
        return best, seg

    def dist(self, p, cap=40.0):
        return self.nearest(p, cap)[0]


def build(sheet):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nsh3_198", sheet.colors)
    dark = mats(19, metallic=0.0, roughness=1.0)  # underside, cut faces and the undercut
    rock = {i: mats(i, metallic=0.0, roughness=1.0 if i < 27 else 0.85) for i in range(16, 32)}
    h, w = sheet.h, sheet.w
    mask = [[v >= 0 for v in row] for row in sheet.pix]
    hole = flood(mask, OPENING_SEED)

    def filled(c, r):
        ci, ri = int(math.floor(c)), int(math.floor(r))
        return 0 <= ri < h and 0 <= ci < w and mask[ri][ci]

    def vkind(c, r):
        """A loop vertex: 'open' (the rock carries on past it), 'hole' (the opening's edge) or 'outer'."""
        e = 1e-3
        if c > w - e or r > h - e or (abs(c - CUT_COL) < e and r <= CUT_ROWS + e):
            return "open"
        ci, ri = int(round(c)), int(round(r))
        for dr in (-1, 0):
            for dc in (-1, 0):
                rr, cc = ri + dr, ci + dc
                if 0 <= rr < h and 0 <= cc < w and hole[rr][cc]:
                    return "hole"
        return "outer"

    def skind(a, b):
        """A loop segment's kind, from the empty pixel just outside its middle."""
        ka, kb = vkind(*a), vkind(*b)
        if ka == kb:
            return ka
        if "hole" in (ka, kb):
            return "hole"
        mc, mr = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        oc, orr = mc - ty / L * 0.5, mr + tx / L * 0.5  # outward
        ci, ri = int(math.floor(oc)), int(math.floor(orr))
        if not (0 <= ri < h and 0 <= ci < w) or (ci >= CUT_COL and ri < CUT_ROWS):
            return "open"
        return "outer"

    traced = lib.trace_loops(mask)
    loops = [lib.simplify_loop(l, TOL) for l in traced]
    loops = [l for l in loops if len(l) >= 3]
    # Split long outline edges so the outline's vertices are as close together as the rows inside
    # it (long edges fanning out to many row points make sliver facets that read as teeth).
    fine, kinds, seg_kinds = [], [], []
    for loop in loops:
        n = len(loop)
        pts, ks, sk = [], [], []
        for k in range(n):
            a, b = loop[k], loop[(k + 1) % n]
            kind_ab = skind(a, b)
            m = max(1, round(math.dist(a, b) / RING_STEP))
            for j in range(m):
                s = j / m
                pts.append((a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s))
                ks.append(vkind(*a) if j == 0 else kind_ab)
                sk.append(kind_ab)
        fine.append(pts)
        kinds.append(ks)
        seg_kinds += sk
    loops = fine
    segs = [(loop[k], loop[(k + 1) % len(loop)]) for loop in loops for k in range(len(loop))]
    all_segs = Segs(segs)
    kind_of = dict(zip(segs, seg_kinds))
    raw_outer = Segs([s for s, k in zip(segs, seg_kinds) if k == "outer"])
    open_segs = Segs([s for s, k in zip(segs, seg_kinds) if k == "open"])
    # The heights are measured from a smoothed outline: measured from the sprite's pixel steps,
    # every step would raise a ridge up the flank.
    soft_outer, soft_hole, soft_loops = [], [], []
    for loop in traced:
        soft = chaikin(lib.simplify_loop(loop, SOFT_TOL))
        if len(soft) < 3:
            continue
        soft_loops.append(soft)
        for k in range(len(soft)):
            sa, sb = soft[k], soft[(k + 1) % len(soft)]
            _, seg = all_segs.nearest(((sa[0] + sb[0]) / 2, (sa[1] + sb[1]) / 2), cap=4.0)
            kind = kind_of.get(seg, "open")
            if kind == "outer":
                soft_outer.append((sa, sb))
            elif kind == "hole":
                soft_hole.append((sa, sb))
    outer = Segs(soft_outer)
    soft_all = Segs([(l[k], l[(k + 1) % len(l)]) for l in soft_loops for k in range(len(l))])
    # The opening carries on below the sheet.
    hole_segs = soft_hole
    for c in range(w):
        if hole[h - 1][c] and (c == 0 or not hole[h - 1][c - 1]):
            hole_segs.append(((c, h), (c, h + 40)))
        if hole[h - 1][c] and (c == w - 1 or not hole[h - 1][c + 1]):
            hole_segs.append(((c + 1, h), (c + 1, h + 40)))
    inner = Segs(hole_segs)

    # Large-scale brightness, the dark cracks between the lit boulders, and the boulder facets
    # between them, per pixel.
    lum = [[clamp01((sheet.pix[r][c] - 16) / 15) if mask[r][c] else 0.0 for c in range(w)] for r in range(h)]
    big = lib.blur(lum, mask, 4)
    near = lib.blur(lum, mask, 2)
    vals = [big[r][c] for r in range(h) for c in range(w) if mask[r][c]]
    mean = sum(vals) / len(vals)
    d_edge = lib.distance_field(mask, "rb")
    lit = [[clamp01((big[r][c] - DARK_LUM - 0.04) / 0.16) if mask[r][c] else 0.0 for c in range(w)]
           for r in range(h)]
    is_crack = [[mask[r][c] and d_edge[r][c] > 2.2 and near[r][c] > 0.45 and lum[r][c] < near[r][c] - 0.1
                 for c in range(w)] for r in range(h)]
    crack = lib.blur([[1.0 if is_crack[r][c] else 0.0 for c in range(w)] for r in range(h)], mask, 1)
    d_crack = lib.distance_field([[mask[r][c] and not is_crack[r][c] for c in range(w)] for r in range(h)], "rb")
    # Each boulder is lit from the upper left like the sprite's: from the crack on its upper-left
    # side its top rises gently (facing the light), and at the crack on its lower-right side it
    # drops steeply (the sprite's dark crack lines sit on the boulders' lower-right edges).
    def pillow_at(c, r):
        d = d_crack[r][c]
        gc = d_crack[r][min(w - 1, c + 1)] - d_crack[r][max(0, c - 1)]
        gr = d_crack[min(h - 1, r + 1)][c] - d_crack[max(0, r - 1)][c]
        g = math.hypot(gc, gr) or 1.0
        away = (gc + gr) / (g * math.sqrt(2))  # +1: the nearest crack is up-left, -1: down-right
        rad = PILLOW_STEEP + (PILLOW_R - PILLOW_STEEP) * clamp01(0.5 + away)
        return smoothstep((d - 0.5) / rad)

    pillow = [[pillow_at(c, r) * lit[r][c] if mask[r][c] else 0.0 for c in range(w)] for r in range(h)]
    pillow = lib.blur(pillow, mask, 1)
    def height(c, r, on_hole=False):
        """The top's height (px) at corner-coordinate point (c, r) (`on_hole`: on the opening's edge)."""
        crest = CREST - (CREST - FOOT) * clamp01((r - LEG_ROW) / (h - LEG_ROW))
        d_out = outer.dist((c, r))
        if open_segs.dist((c, r), cap=CORNER + 1) < CORNER:
            # where the outline meets a cut edge the smoothed outline cuts the corner off: measure
            # from the raw outline too, so the corner comes down to the ground (no fin)
            d_out = min(d_out, raw_outer.dist((c, r)) + CORNER_LIFT)
        t = clamp01((d_out - TOE) / SHOULDER)
        d_in = 0.0 if on_hole else inner.dist((c, r))
        q = clamp01((d_out - TOE - SHOULDER) / max(1.0, d_out + d_in - TOE - SHOULDER - FALL))
        rise = (1 - (1 - t) ** 2) * (SHOULDER_H + (1 - SHOULDER_H) * q)
        u = clamp01(d_in / FALL)
        lip = LIP + (LEG_LIP - LIP) * smoothstep((r - LEG_ROWS[0]) / (LEG_ROWS[1] - LEG_ROWS[0]))
        fall = lip + (1 - lip) * smoothstep(u)
        b = lib.bilinear(big, mask, c, r) - mean
        k = lib.bilinear(crack, mask, c, r)
        bulge = PILLOW * lib.bilinear(pillow, mask, c, r)
        relief = (LOBE * max(-0.3, min(0.4, b)) + bulge - CRACK * k) * t * smoothstep(u * 1.5)
        z = crest * rise * fall + relief
        for (bc, br), top, rad in CHUNKS:
            q = 1 - ((c - bc) ** 2 + (r - br) ** 2) / rad ** 2
            if q > 0:
                z = max(z, top * math.sqrt(q))
        return max(EDGE, z)

    def ztop(c, r, boundary_kind):
        if boundary_kind == "outer":
            # the small boulder on the outer edge stands up from the ground there (a short wall)
            z = EDGE
            for (bc, br), top, rad in CHUNKS:
                qq = 1 - ((c - bc) ** 2 + (r - br) ** 2) / rad ** 2
                if qq > 0:
                    z = max(z, 0.6 * top * math.sqrt(qq))
            return z * U
        return height(c, r, boundary_kind == "hole") * U

    def zbot(c, r, boundary_kind):
        return -(EDGE if boundary_kind else BOTTOM) * U

    # The undercut: the bottom of the wall under the opening's lip is set back into the rock, easing
    # in over a few px where the opening's edge meets the cut edges.
    bottom_loops = []
    for loop, ks in zip(loops, kinds):
        n = len(loop)
        moved = []
        for k in range(n):
            c, r = loop[k]
            if ks[k] != "hole":
                moved.append((c, r))
                continue
            best = 1e9
            for sgn in (1, -1):
                dist, j = 0.0, k
                for _ in range(n):
                    j2 = (j + sgn) % n
                    dist += math.dist(loop[j], loop[j2])
                    j = j2
                    if ks[j] != "hole" or dist > 4:
                        break
                if ks[j] != "hole":
                    best = min(best, dist)
            a = loop[(k - 2) % n]
            b = loop[(k + 2) % n]
            tx, ty = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, ty) or 1.0
            amt = UNDERCUT * clamp01(best / 4)
            moved.append((c + ty / L * amt, r - tx / L * amt))  # inward is (ty, -tx)
        # The undercut's foot follows the pixel steps of the opening's edge: smooth it along the
        # loop so the wall under the lip is one even concave sweep, not a row of teeth.
        for _ in range(UNDERCUT_SMOOTH):
            moved = [((moved[(k - 1) % n][0] + 2 * moved[k][0] + moved[(k + 1) % n][0]) / 4,
                      (moved[(k - 1) % n][1] + 2 * moved[k][1] + moved[(k + 1) % n][1]) / 4)
                     if ks[k] == "hole" and ks[(k - 1) % n] == "hole" and ks[(k + 1) % n] == "hole"
                     else moved[k] for k in range(n)]
        bottom_loops.append(moved)

    # Rows of points following the outline, so the flanks rise in even steps.
    ring_pts = []
    bucket = {}

    def free(p, d):
        gi, gj = int(p[0] // 1), int(p[1] // 1)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in bucket.get((gi + di, gj + dj), ()):
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < d * d:
                        return False
        return True

    def add(p, o):
        if not filled(*p) or not lib._point_in_loops(p, loops):
            return
        if all_segs.dist(p, cap=o + 1) < min(0.45, o * 0.85) or soft_all.dist(p, cap=o + 1) < o * 0.85 \
                or not free(p, 0.7):
            return
        ring_pts.append(p)
        bucket.setdefault((int(p[0] // 1), int(p[1] // 1)), []).append(p)

    def normal(a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        return (b[1] - a[1]) / L, -(b[0] - a[0]) / L  # inward

    # The rows follow the smoothed outline (the heights are measured from it), so they rise in
    # even steps without the sprite's pixel steps.
    for loop in soft_loops:
        n = len(loop)
        # resample at RING_STEP
        samples = []
        for k in range(n):
            a, b = loop[k], loop[(k + 1) % n]
            L = math.dist(a, b)
            m = max(1, round(L / (RING_STEP * 0.5)))
            for i in range(m):
                s = i / m
                samples.append((a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s))
        ns = len(samples)
        acc = RING_STEP
        prev = samples[0]
        for k in range(ns):
            p0 = samples[k]
            acc += math.dist(prev, p0)
            prev = p0
            if acc < RING_STEP:
                continue
            acc = 0.0
            pa, pb = samples[(k - 2) % ns], samples[(k + 2) % ns]
            nx, ny = normal(pa, pb)
            for o in RINGS:
                add((p0[0] + nx * o, p0[1] + ny * o), o)
    inner_pts = [p for p in lib._fill_points(loops, mask, STEP, 1, margin=RINGS[-1] + 0.9) if free(p, 1.0)]

    bm = bmesh.new()
    ring_top, ring_bot = {}, {}
    flat_kinds = [k for ks in kinds for k in ks]

    def surface(outline, interior, zf, ring, is_top):
        vout, tris, ids, nb = lib._triangulate(outline, interior)
        verts = {}
        for k, co in enumerate(vout):
            oid = ids[k]
            if oid is not None and oid < nb:
                if oid not in ring:
                    ring[oid] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), zf(co.x, co.y, flat_kinds[oid])))
                verts[k] = ring[oid]
            else:
                verts[k] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), zf(co.x, co.y, None)))
        faces = []
        for f in tris:
            vs = [verts[j] for j in f]
            if len(set(vs)) < 3:
                continue
            if not is_top:
                vs.reverse()
            try:
                face = bm.faces.new(vs)
            except ValueError:
                continue
            faces.append((face, f, vout))
        return faces

    d_hole = lib.distance_field([[not hole[r][c] for c in range(w)] for r in range(h)], "lrtb")
    bot_pts = [p for p in lib._fill_points(loops, mask, BOTTOM_STEP, 8, margin=BOTTOM_STEP * 0.45)
               if lib.bilinear(d_hole, mask, *p) > UNDERCUT + 2]
    tops = surface(loops, ring_pts + inner_pts, ztop, ring_top, True)
    bots = surface(bottom_loops, bot_pts, zbot, ring_bot, False)
    smooth_idx = lib.blur([[min(31, max(16, sheet.pix[r][c])) if mask[r][c] else 0 for c in range(w)]
                           for r in range(h)], mask, 1)

    def edge_index(a, b, q):
        """The sprite pixel just inside edge a-b at its point nearest q."""
        tx, ty = b[0] - a[0], b[1] - a[1]
        L2 = tx * tx + ty * ty or 1.0
        s = clamp01(((q[0] - a[0]) * tx + (q[1] - a[1]) * ty) / L2)
        nx, ny = normal(a, b)
        pc, pr = a[0] + tx * s + nx * 0.5, a[1] + ty * s + ny * 0.5
        v = sheet.at(int(math.floor(pc)), int(math.floor(pr)))
        return v if v >= 0 else sheet.nearest(pc, pr, lambda i: i >= 0)

    smooth_tops = []
    for face, f, vout in tops:
        cc = sum(vout[j].x for j in f) / len(f)
        rr = sum(vout[j].y for j in f) / len(f)
        # Tall steep facets (the flanks, the faces into the cave) stretch a few sprite pixels over
        # their height: they take a smoothed shade (single dark or light pixels would streak them).
        # The low strip along the outline keeps the sprite's edge pixel.
        face.normal_update()
        d, seg = all_segs.nearest((cc, rr), cap=1.2)
        span = max(q.co.z for q in face.verts) - min(q.co.z for q in face.verts)
        on_chunk = any(math.dist((cc, rr), bc) < rad for bc, _, rad in CHUNKS + KEEP)
        if abs(face.normal.z) < STEEP and span > TALL * U and not on_chunk:
            v = max(16, min(31, round(lib.bilinear(smooth_idx, mask, cc, rr))))
        elif seg and d < 0.9:
            v = edge_index(*seg, (cc, rr))
        else:
            v = sheet.nearest(cc, rr, lambda i: i >= 0)
        face.material_index = rock.get(v, dark)
        smooth_tops.append(face)
    for face, _, _ in bots:
        face.material_index = dark
    # Walls between the top and bottom rings: the outer ones take the sprite's edge colour, the
    # undercut and the cut edges are in shadow.
    i = 0
    for loop in loops:
        n = len(loop)
        for k in range(n):
            a, b = i + k, i + (k + 1) % n
            if a in ring_top and b in ring_top and a in ring_bot and b in ring_bot:
                try:
                    face = bm.faces.new((ring_bot[a], ring_bot[b], ring_top[b], ring_top[a]))
                except ValueError:
                    continue
                if seg_kinds[a] == "outer":
                    s0, s1 = loop[k], loop[(k + 1) % n]
                    v = edge_index(s0, s1, ((s0[0] + s1[0]) / 2, (s0[1] + s1[1]) / 2))
                    face.material_index = rock.get(v, dark)
                else:
                    face.material_index = dark
        i += n
    # The top is smooth shaded (rounded rock, no facet noise); walls, underside and cut faces stay flat.
    return lib.to_object(NAME, bm, mats.list, coll, smooth_faces=smooth_tops)


def match_normals(obj, pieces, sheet):
    """Give each piece's smooth top the whole arch's normals, so the shading runs on across the
    cuts between pieces (each piece on its own would bend its normals at its cut edges)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc

    me = obj.data
    vn = [Vector() for _ in me.vertices]
    smooth_polys = [p for p in me.polygons if p.use_smooth]
    for p in smooth_polys:
        for v in p.vertices:
            vn[v] += p.normal * p.area
    vn = [n.normalized() if n.length > 1e-12 else Vector((0, 0, 1)) for n in vn]
    co = [obj.matrix_world @ v.co for v in me.vertices]
    tree = BVHTree.FromPolygons(co, [list(p.vertices) for p in smooth_polys])
    for name, c0, r0, _ in PLACEMENTS:
        piece = pieces[name]
        offset = Vector(((c0 + 12 - sheet.w / 2) / 12, -(r0 + 14 - sheet.h / 2) / 12, 0))
        pm = piece.data
        normals = []
        for poly in pm.polygons:
            for li in poly.loop_indices:
                n = poly.normal.copy()
                if poly.use_smooth:
                    q = pm.vertices[pm.loops[li].vertex_index].co + offset
                    hit, _, fi, dist = tree.find_nearest(q)
                    if hit is not None and dist < 1e-3:
                        vids = smooth_polys[fi].vertices
                        wts = poly_3d_calc([co[v] for v in vids], q)
                        m = sum((vn[v] * w for v, w in zip(vids, wts)), Vector())
                        if m.length > 1e-9 and m.normalized().dot(poly.normal) > 0.3:
                            n = m.normalized()
                normals.append(n)
        pm.normals_split_custom_set(normals)


def main():
    sheet = lib.Sheet(ROOT, PLACEMENTS)
    obj = build(sheet)
    # (lib.export_pieces, with the pieces' normals matched before export)
    layout = [(name, c0 + 12 - sheet.w / 2, r0 + 14 - sheet.h / 2) for name, c0, r0, _ in PLACEMENTS]
    pieces = common.split_assembly(obj, layout)
    match_normals(obj, pieces, sheet)
    for name, _, _ in layout:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sheet.sprites[name]["sprites"])
    if "--preview" in sys.argv:
        lib.previews(ROOT, sys.argv[sys.argv.index("--preview") + 1], obj, pieces, sheet)


if __name__ == "__main__":
    main()
