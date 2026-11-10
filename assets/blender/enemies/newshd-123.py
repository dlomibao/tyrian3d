"""newshd-123 (design A): the grey asteroid of newshd.shp frame 123 (23 x 23 px inside a 24 x 28 cell),
rebuilt as one faceted boulder of five lumps split by dark cracks.

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"; material first: rock, so its
highlights are lit faces of real shape, matte, not sheen):
- Outline: a rounded boulder, stepped down on its upper left where the top-right lump rises above the
  left one (rows 2-5 hold only the top-right lump, cols 13-22). The ink ring is the game's outline: the
  top view goes to the inner edge of that ring (D74, tools/sprite_mask.py).
- Lumps (power-diagram seeds in regions.py, set along the cracks): a big pale lump on the left (rows
  6-14, cols 3-12), the top-right lump (rows 3-12, cols 12-22, darker on its shadowed right side), a
  bright knob in the middle (cols 13-17, rows 10-14; the 13/14 streak at col 14 is its lit crest, a
  ridge running down the screen), and two lower lumps (lower left rows 15-23, lower right rows 13-23).
- Cracks: the dark row-14 band across the left (4-7 between 9-11s), the col 12-13 seam from row 5
  down to the knob, the seams round the knob and between the two lower lumps. They are cut in (V
  grooves where two lumps meet), their walls a dark grey (palette 5). The dark band at rows 20-24 and
  the right edge are the rock's shadowed lower and right flanks: lighting, not paint.
- Colours (each region's trimmed median, darkest and brightest sixths dropped, measure.py): left 9,
  knob 10, lower left 8, top right 6, lower right 6 (the darker right half against the pale left).

Build (D50-D53, D65 applied to rock): each lump is the convex hull of seeded, jittered points (an
equator ring on the outline, a chamfered shoulder, two top rings and a crest; a belly reaching under
the rock's centre), so its faces are big flat broken-stone facets, then flat chips are knocked off
its top (each skipped if it would cut a crack lip or the outline ring). Along a crack the lip is held
back from the seam and the groove floor pushed past it, so neighbouring lumps interpenetrate under a
V groove ~1.5-2 px wide at the lip (LIP), its floor just past the seam (NEAR) and top points held
back behind the lip, so its pal_5 walls show from the tilted camera; under each seam a filler hull closes the crease lower down the flanks, so the
rock reads as one boulder, not a bunch of pebbles. Matte stone (metallic 0.05, roughness 0.82) as
the newshd asteroids it flies with (newshd-95, lib_newshd_rock). Underside: the lumps' bellies merge into one closed
rounded bottom (no detail). No crack floor or filler hull may round off a notch of the outline (Grid.outside_in; the
upper-left step). AO/roughness bake as newshd-95 (T.bake_maps, 512 px, untinted; --no-bake skips
it), then the outline shell (D51) from the joined lumps.

Units while building: sprite px (x = column edge - 12, y = row edge, down the screen, z up), moved to
Blender at the end (X = x / 12, Y = (14 - y) / 12, Z = z / 12, as usp_talon.finish).

Run: Blender -b --factory-startup -P assets/blender/enemies/newshd-123.py (tools/build-models.sh)
"""

import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
# Lump partition of the sprite's inner mask: power-diagram seeds (name, col, row, radius) following
# the sprite's cracks, and the inner mask itself (tools/sprite_mask.py newshd-123; '#' = inside).
LUMPS = [
    ("left", 7.0, 10.0, 6.0),
    ("topright", 17.5, 7.0, 5.0),
    ("knob", 14.6, 12.4, 3.0),
    ("lowleft", 6.5, 18.0, 4.6),
    ("lowright", 16.5, 17.0, 4.2),
]
MASK = [
    "........................",
    "........................",
    "..............ooooo.....",
    ".............o#####oo...",
    "............o########oo.",
    ".....ooooooo###########o",
    ".....o#################o",
    "...oo##################o",
    "..o#####################",
    "..o####################o",
    "..o####################o",
    "..o####################o",
    "..o####################o",
    "..o####################o",
    "...o###################o",
    "..o####################o",
    "..o####################o",
    "..o####################o",
    ".o#####################o",
    ".o####################o.",
    ".o###################o..",
    ".o##################o...",
    "..o################o....",
    "...oo###########ooo.....",
    ".....ooooooooooo........",
    "........................",
    "........................",
    "........................",
]


def masks():
    return MASK


def owner(c, r, lumps=LUMPS):
    """The lump under sprite point (c, r): a power diagram of the seeds (straight seams, convex)."""
    best, bi = None, None
    for i, (_, cx, cy, rad) in enumerate(lumps):
        d = (c - cx) ** 2 + (r - cy) ** 2 - rad ** 2
        if best is None or d < best:
            best, bi = d, i
    return bi

NAME = "newshd-123"
PX = 1 / 12
CRACK = 5  # crack walls: the dark grey of the sprite's seams

# Per lump (same order as regions.LUMPS): palette index, crest points (col, row) (two for a ridge),
# crest height px, seed, chips [(azimuth deg of the facet's normal, elevation deg, depth px below the
# lump's top along it)]. Azimuth in sprite terms: 0 = right, 90 = up the screen.
LOOK = {
    "left": (9, [(6.8, 10.4)], 7.6, 11, [(135, 62, 1.6), (200, 48, 1.4), (60, 50, 1.2), (250, 45, 1.3)]),
    "topright": (6, [(16.2, 5.4)], 7.0, 12, [(110, 58, 1.3), (20, 40, 1.4), (300, 52, 1.2), (160, 45, 1.0)]),
    "knob": (10, [(14.2, 10.8), (14.6, 13.6)], 8.3, 13, [(170, 55, 1.0), (10, 50, 1.2)]),
    "lowleft": (8, [(6.8, 17.0)], 6.6, 14, [(150, 60, 1.3), (240, 40, 1.4), (40, 50, 1.0)]),
    "lowright": (6, [(16.2, 16.4)], 6.0, 15, [(120, 60, 1.2), (330, 42, 1.3), (250, 46, 1.2)]),
}
TOP_RINGS = ((0.76, 0.72), (0.52, 0.86), (0.27, 0.96))  # (shrink toward the crest, height as a share of it)
TOP_OF = {"knob": ((0.6, 0.9), (0.3, 0.98))}
TOP_JIT = (0.6, 1.2, 0.55)  # top ring jitter: xy px, z px, share of points kept (a broken surface)  # the knob is a long ridge, not a spike
LIP_Z = 0.72    # crack lip height (share of the lump's crest)
LIP_OF = {"knob": 0.8}  # the knob's crest stands proud, its lip high
FLOOR_K = 0.5   # groove floor: this share of the lower of the two lips (a crack ~3 px deep)
LIP = 1.25      # crack lip held back from the seam (px): a groove ~2 px wide at the lip
PAST = 1.0      # the rock under the groove pushed past the seam into the neighbour (px)
NEAR = 0.25     # groove floor point just past the seam (px): steep V walls
OUT_IN = 0.05   # outline points pulled in a hair (px)
BUMPS = {(23, 8)}  # a one-pixel rim bump on the right edge the hull would stretch over 8 rows
BELLY = -7.4    # lowest point of the underside (px)
ROCK_C = (11.6, 13.4)  # centre of the whole rock (col, row), where the bellies meet
SMALL_CHIPS = 18 # extra random small facets per lump (seeded)
FILL_TOL = -0.2  # crack floors and filler hulls stay this far (px) off the centre of any cell outside the outline
CRACK_W = 2.0   # crack walls: faces centred within this of a seam (px)


# --- 2D helpers -----------------------------------------------------------------------------------
def hull2d(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def resample(poly, n):
    """n points evenly spaced along a closed polygon."""
    segs = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    lens = [math.dist(a, b) for a, b in segs]
    total = sum(lens)
    out = []
    for k in range(n):
        t = total * k / n
        for (a, b), L in zip(segs, lens):
            if t <= L or (a, b) == segs[-1]:
                f = t / L if L else 0
                out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                break
            t -= L
    return out


class Grid:
    """The sprite's inner mask, each cell owned by a lump, and the seams between lumps."""

    def __init__(self):
        self.m = masks()
        self.h, self.w = len(self.m), len(self.m[0])
        self.own = {}
        for r in range(self.h):
            for c in range(self.w):
                if self.m[r][c] == "#":
                    self.own[(c, r)] = owner(c + 0.5, r + 0.5)
        self.seams = []  # cell edges between two lumps: ((c0, r0, c1, r1), {owners})
        for (c, r), o in self.own.items():
            for dc, dr in ((1, 0), (0, 1)):
                o2 = self.own.get((c + dc, r + dr))
                if o2 is not None and o2 != o:
                    seg = (c + 1, r, c + 1, r + 1) if dc else (c, r + 1, c + 1, r + 1)
                    self.seams.append((seg, {o, o2}))

    def outside_in(self, pts, tol=0.05):
        """Cells outside the inner mask whose centre lies inside the 2D hull of pts (col, row)."""
        h = hull2d(pts)
        n = len(h)
        if n < 3:
            return set()
        area = sum(h[i][0] * h[(i + 1) % n][1] - h[(i + 1) % n][0] * h[i][1] for i in range(n))
        sgn = 1 if area > 0 else -1
        lo_c, hi_c = min(p[0] for p in h), max(p[0] for p in h)
        lo_r, hi_r = min(p[1] for p in h), max(p[1] for p in h)
        out = set()
        for r in range(max(0, int(lo_r) - 1), min(self.h, int(hi_r) + 2)):
            for c in range(max(0, int(lo_c) - 1), min(self.w, int(hi_c) + 2)):
                if self.m[r][c] == "#":
                    continue
                x, y = c + 0.5, r + 0.5
                inside = True
                for i in range(n):
                    (ax, ay), (bx, by) = h[i], h[(i + 1) % n]
                    L = math.hypot(bx - ax, by - ay) or 1.0
                    if sgn * ((bx - ax) * (y - ay) - (by - ay) * (x - ax)) / L < tol:
                        inside = False
                        break
                if inside:
                    out.add((c, r))
        return out

    def hull_ok(self, pts, allowed):
        return self.outside_in(pts, FILL_TOL) <= allowed

    def at(self, c, r):
        """Lump index under sprite point (c, r) (column/row coordinates), -1 outside."""
        return self.own.get((int(math.floor(c)), int(math.floor(r))), -1)

    def seam_dist(self, c, r, pair=None):
        best = 99.0
        for (c0, r0, c1, r1), owners in self.seams:
            if pair is not None and owners != pair:
                continue
            dx, dy = c1 - c0, r1 - r0
            t = max(0.0, min(1.0, ((c - c0) * dx + (r - r0) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(c - (c0 + dx * t), r - (r0 + dy * t)))
        return best


def lip_of(li):
    name = LUMPS[li][0]
    return LOOK[name][2] * LIP_OF.get(name, LIP_Z)


# --- lumps ----------------------------------------------------------------------------------------
def lump_points(G, li, rng):
    """The hull points of lump li in sprite px (x = c - 12, y = r), and the points chips must keep
    (crack lips and the outline ring)."""
    name = LUMPS[li][0]
    _, peaks, peak, _, _ = LOOK[name]
    cells = [k for k, v in G.own.items() if v == li]
    # the hull of the cells' centres, grown half a pixel: on a stepped diagonal edge it cuts each step
    # in half (a hull of the cells' corners covers every step whole and reads a pixel fat)
    cen = (sum(c for c, _ in cells) / len(cells) + 0.5, sum(r for _, r in cells) / len(cells) + 0.5)
    ring = []
    for (c, r) in resample(hull2d([(c + 0.5, r + 0.5) for c, r in cells if (c, r) not in BUMPS]),
                           30 if len(cells) > 40 else 18):
        d = math.hypot(c - cen[0], r - cen[1]) or 1.0
        ring.append((c + (c - cen[0]) / d * 0.5, r + (r - cen[1]) / d * 0.5))
    pc = sum(p[0] for p in peaks) / len(peaks)
    pr = sum(p[1] for p in peaks) / len(peaks)
    j = lambda s: rng.uniform(-s, s)  # noqa: E731
    pts, keep = [], []
    base, floor2d = list(ring), []
    bad0 = G.outside_in(base, FILL_TOL)
    for (c, r) in ring:
        dx, dy = c - cen[0], r - cen[1]
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        # a crack when a step past the region's edge lands in another lump (not over the outline)
        hits = [G.at(c + ux * t, r + uy * t) for t in (0.5, 0.9)]
        probe = next((h for h in hits if h not in (-1, li)), -1)
        if probe != -1:
            # crack: an even lip held back from the seam, the groove floor past it (inside the
            # neighbour), and the lump going on down into the rock's body under the crack
            own = lip_of(li)
            pts.append((c - ux * LIP - 12, r - uy * LIP, own + j(0.08)))
            keep.append(pts[-1])
            # (never out over the outline, where a seam meets it at a slant, nor so far that the
            # lump's hull would round off a notch of the outline, as at the upper-left step)
            reach = [t for t in (PAST * 1.3, PAST, 0.7, 0.4, 0.0) if G.at(c + ux * t, r + uy * t) != -1]
            reach = [t for t in reach if G.hull_ok(base + floor2d + [(c + ux * t, r + uy * t)], bad0)]
            far = reach[0] if reach else 0.0
            near = min(far, NEAR)
            floor2d.append((c + ux * far, r + uy * far))
            pts.append((c + ux * near - 12, r + uy * near, FLOOR_K * min(own, lip_of(probe)) + j(0.08)))
            pts.append((c + ux * far - 12, r + uy * far, j(0.5)))
        else:
            # outline: the widest ring near z = 0, a chamfered shoulder above it
            pts.append((c - ux * OUT_IN - 12 + j(0.05), r - uy * OUT_IN + j(0.05), j(0.8)))
            keep.append(pts[-1])
            pts.append((c - ux * 1.1 - 12 + j(0.3), r - uy * 1.1 + j(0.3), peak * rng.uniform(0.42, 0.56)))
        for f, zf in TOP_OF.get(name, TOP_RINGS):  # top rings toward the crest
            if rng.random() < TOP_JIT[2]:
                tc, tr, tz = pc + (c - pc) * f + j(TOP_JIT[0]), pr + (r - pr) * f + j(TOP_JIT[0]), peak * zf + j(TOP_JIT[1])
                # held back behind the crack lip, so the lip is the groove's edge and its wall
                # drops steeply to the floor (a top point near the seam would roof the groove over)
                for _ in range(20):
                    if G.seam_dist(tc, tr) >= LIP + 0.15 or math.hypot(tc - pc, tr - pr) < 0.3:
                        break
                    tc, tr = tc + (pc - tc) * 0.12, tr + (pr - tr) * 0.12
                pts.append((tc - 12, tr, tz))
        for f, z in ((0.86, BELLY * 0.4), (0.55, BELLY * 0.82)):  # belly, toward the rock's centre
            bc = ROCK_C[0] + (c - ROCK_C[0]) * f
            br = ROCK_C[1] + (r - ROCK_C[1]) * f
            pts.append((bc - 12 + j(0.5), br + j(0.5), z + j(0.5)))
    for (qc, qr) in peaks:
        pts.append((qc - 12, qr, peak))
    pts.append((ROCK_C[0] - 12, ROCK_C[1], BELLY))
    return pts, keep


def convex(bm, pts):
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")


def chip(bm, chips, keep):
    """Flat facets knocked off a lump's top: each a plane (normal from azimuth/elevation in sprite
    terms, `depth` px below the lump's highest point along it) cut off and capped flat. A chip that
    would cut a point of `keep` is skipped, so the cracks and the silhouette hold."""
    for az, el, depth in chips:
        a, e = math.radians(az), math.radians(el)
        n = Vector((math.cos(a) * math.cos(e), -math.sin(a) * math.cos(e), math.sin(e)))  # sprite y is down
        hi = max(v.co.dot(n) for v in bm.verts)
        if any(Vector(p).dot(n) > hi - depth - 0.05 for p in keep):
            continue
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * (hi - depth), plane_no=n, clear_outer=True)
        cut = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.holes_fill(bm, edges=cut, sides=0)


def lump_mesh(G, li):
    name = LUMPS[li][0]
    _, _, _, seed, chips = LOOK[name]
    rng = random.Random(seed)
    pts, keep = lump_points(G, li, rng)
    bm = bmesh.new()
    convex(bm, pts)
    extra = [(rng.uniform(0, 360), rng.uniform(30, 72), rng.uniform(0.3, 0.9)) for _ in range(SMALL_CHIPS)]
    chip(bm, chips + extra, keep)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.5), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, pts


def filler_points(G, pts_of, a, b):
    """Points of lumps a and b near their seam and below their groove floor: their hull bridges the
    V crease two convex lumps leave down the rock's flanks, so a crack runs in from the top and closes
    lower down instead of splitting the rock like a pumpkin's ribs."""
    zmax = FLOOR_K * min(lip_of(a), lip_of(b)) - 0.3
    pts = [(x, y, z) for li in (a, b) for (x, y, z) in pts_of[li]
           if z <= zmax and G.seam_dist(x + 12, y, {a, b}) < 3.2]
    # its top view stays inside the outline: drop the hull corners that bridge a notch of it (the
    # upper-left step, where the top-right lump rises above the left one)
    while len(pts) >= 8:
        bad = G.outside_in([(x + 12, y) for x, y, _ in pts], FILL_TOL)
        if not bad:
            break
        hull = set(hull2d([(x + 12, y) for x, y, _ in pts]))
        cand = [p for p in pts if (p[0] + 12, p[1]) in hull]
        best = min(cand, key=lambda p: len(G.outside_in([(x + 12, y) for x, y, _ in pts if (x, y, _) != p], FILL_TOL)))
        pts.remove(best)
    return pts


def build():
    sprite = common.load_sprite(ROOT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    G = Grid()
    mats, slot = [], {}

    def mat(idx):
        if idx not in slot:
            slot[idx] = len(mats)
            mats.append(common.palette_material(sprite, idx, NAME, metallic=0.05, roughness=0.82))
        return slot[idx]

    bm = bmesh.new()
    tmp = bpy.data.meshes.new("tmp")
    owner_of, pts_of = [], {}

    def add(lb, m, who):
        for f in lb.faces:
            f.material_index = m
        lb.to_mesh(tmp)
        lb.free()
        n0 = len(bm.faces)
        bm.from_mesh(tmp)
        owner_of.extend([who] * (len(bm.faces) - n0))

    for li, (name, *_rest) in enumerate(LUMPS):
        lb, pts_of[li] = lump_mesh(G, li)
        add(lb, mat(LOOK[name][0]), li)
    # fillers under the seams, in the darker lump's colour
    lum = lambda li: sum(sprite["colors"][str(LOOK[LUMPS[li][0]][0])])  # noqa: E731
    for pair in sorted({tuple(sorted(o)) for _, o in G.seams}):
        fp = filler_points(G, pts_of, *pair)
        if len(fp) < 8:
            continue
        lb = bmesh.new()
        convex(lb, fp)
        bmesh.ops.triangulate(lb, faces=lb.faces[:])
        bmesh.ops.recalc_face_normals(lb, faces=lb.faces[:])
        add(lb, mat(LOOK[LUMPS[min(pair, key=lum)][0]][0]), -1)
    bpy.data.meshes.remove(tmp)

    # crack walls: steep faces near a seam whose outward side runs into another lump, inside the groove
    crack = mat(CRACK)
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    for f, li in zip(bm.faces, owner_of):
        n, cpt = f.normal, f.calc_center_median()
        if li < 0 or n.z < -0.2 or n.z > 0.85 or cpt.z < 0.5:
            continue
        if G.seam_dist(cpt.x + 12, cpt.y) > CRACK_W:
            continue
        h = math.hypot(n.x, n.y) or 1.0
        hit = [G.at(cpt.x + 12 + n.x / h * s, cpt.y + n.y / h * s) for s in (0.5, 1.0)]
        nbs = [o for o in hit if o not in (-1, li)]
        # below the lower of the two lips, every corner at or under this lump's own lip (a proud
        # lump's flank and the faces rising from the lip to the crest stay rock)
        if nbs and cpt.z < min(lip_of(li), lip_of(nbs[0])) + 0.4 and \
                max(v.co.z for v in f.verts) < lip_of(li) + 0.2:
            f.material_index = crack

    # sprite px to Blender (a reflection in y: flip the faces)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return sprite, obj, coll


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, obj, coll = build()
    fmt = "AUTO"
    if "--no-bake" not in argv:
        # AO/roughness bake as the newshd asteroids it flies with (newshd-95, lib_newshd_rock): grey occlusion in
        # the cracks and facet roots, untinted (TINT 1,1,1), on every palette material
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(len(obj.data.materials)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), size=512, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    # the outline shell (D51) after the bake, so its occlusion rays never hit it
    shell = common.outline_shell(obj, coll, faces=2500)
    shell.name = f"{NAME}_outline"
    objs = [obj, shell]
    common.export_sprite_model(ROOT, objs, f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    tris = []
    for o in objs:
        o.data.calc_loop_triangles()
        tris.append(len(o.data.loop_triangles))
    print(f"built {NAME}: {tris[0]} triangles, shell {tris[1]}")


if __name__ == "__main__":
    main()
