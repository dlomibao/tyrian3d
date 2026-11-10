"""Crystal asteroid (newshd.shp frames 229/231/233/235), design A: a closed round boulder of four
lumps split by dark V-groove crevices, with a blue crystal growing out of the crevices' junction
whose light switches on and swells into a glowing diamond (D123 follow-up).

Identity: a random-spawn rock of level 1.1 (no event places it, nothing launches it; mv(0,2),
xAccel 93), tumbling free in space, so it is round and closed underneath (no flat base, D122).
23 x 23 px inside a 24 x 28 cell. The frames differ only in the light, so one rock carries a
crystal per look: dormant (229, a dark blue-grey shard sunk in the crack), small and lit (231, the
cross: arms 151, heart 154), large and lit (233: tips 150, facets 152/154, heart 157; 235 the same
crystal brighter: 154, 156/158, heart 141).

Reading of the sprite (rubric "Reading a sprite"; rock, so bright spots are lit faces of real shape):
- Lumps (power diagram, along the dark crevices): the big pale upper-left lump (rows 6-14, crest
  at cols 7-9 rows 8-13), the upper-right lump with its knob reaching the top edge (rows 3-12),
  the lower-left lump (rows 15-23) and the lower-right lump with its bright ridge down col 16.
- Crevices: the dark band along row 14 (cols 3-12), the col-13 crack between the upper lumps, the
  row-12 seam between the right lumps and the col-14 crack between the lower ones; all four meet at
  (12.5, 14.5), where the crystal sits. The dark bottom rows 20-23 and right edge are flank in
  shadow (lighting, not paint); the lit pixels round the crystal on 233/235 are its glow, not paint.
- Colours: each lump's trimmed median (darkest and brightest sixths dropped): upper-left 9,
  upper-right 7, lower-left 7, lower-right 7 (its bright knob over the crystal, cols 13-16 rows 11-13, is its crest: no
  crack parts it from the ridge below, so it is the same lump); crevice walls 4 (as newshd-85).

Build: newshd-85's rock recipe (copied here; see that script and D121/D123): convex hulls of
jittered points per lump, flat chips, V grooves at the seams with filler hulls under them, matte
stone (metallic 0, roughness 0.86), fracture chamfer, AO/roughness bake untinted, outline shell.

    blender -b --factory-startup -P newshd-229.py [-- --no-bake] [--out file.glb]
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
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as SM  # noqa: E402

NAME = "newshd-229"
MODEL = f"enemies/{NAME}"
PX = 1 / 12
# Lump partition of the sprite's inner mask: power-diagram seeds (name, col, row, radius) following
# the sprite's crevices.
LUMPS = [
    ("ul", 7.3, 10.2, 5.4),
    ("ur", 18.3, 7.6, 5.3),
    ("ll", 8.0, 19.0, 5.2),
    ("lr", 17.6, 15.2, 4.9),
]
CRACK = 4  # crevice walls: the sprite's crevice grey

# Per lump: palette index, crest points (col, row) (two for a ridge), crest height px, seed, chips
# [(azimuth deg of the facet's normal, elevation deg, depth px below the lump's top along it)].
# Azimuth in sprite terms: 0 = right, 90 = up the screen.
LOOK = {
    "ul": (9, [(7.8, 9.0), (8.6, 12.0)], 10.4, 31,
           [(135, 58, 1.0), (40, 50, 1.3), (100, 36, 2.0), (180, 40, 1.8), (220, 50, 1.2), (300, 52, 1.0),
            (150, 26, 2.4), (260, 30, 2.2)]),
    "ur": (7, [(16.4, 5.2), (18.4, 8.2)], 9.4, 32,
           [(110, 55, 1.2), (30, 48, 1.4), (70, 34, 2.0), (340, 36, 1.8), (160, 44, 1.4), (250, 52, 1.2)]),
    "ll": (7, [(7.2, 18.4)], 8.8, 33,
           [(150, 55, 1.3), (230, 44, 1.5), (270, 34, 2.0), (200, 30, 2.2), (300, 50, 1.2), (60, 46, 1.4)]),
    "lr": (7, [(14.8, 12.2), (16.6, 15.8)], 9.0, 34,
           [(120, 56, 1.2), (20, 46, 1.4), (300, 50, 1.3), (340, 30, 2.0), (220, 44, 1.2), (160, 40, 1.6)]),
}
TOP_RINGS = ((0.78, 0.64), (0.52, 0.80), (0.27, 0.92))  # (shrink toward the crest, height as a share of it)
TOP_OF = {"ul": ((0.78, 0.60), (0.52, 0.76), (0.27, 0.90))}  # the big lump peaks, no table top
TOP_JIT = (0.6, 1.0, 0.6)  # top ring jitter: xy px, z px, share of points kept (a broken surface)
LIP_Z = 0.74    # crevice lip height (share of the lump's crest)
LIP_OF = {"ul": 0.66}  # the big lump's crown rises well clear of its lip
DEPTH = 1.6     # groove floor this far (px) under the lower of the two lips
LIP = 0.75      # crevice lip held back from the seam (px): a groove ~1.5 px wide at the lip
PAST = 1.0      # the rock under the groove pushed past the seam into the neighbour (px)
NEAR = 0.2      # groove floor point just past the seam (px): steep V walls
OUT_IN = 0.05   # outline points pulled in a hair (px)
BUMPS = set()
BELLY = -8.6    # lowest point of the underside (px): round, no flat base
ROCK_C = (12.5, 13.6)  # centre of the whole rock (col, row), where the bellies meet
SMALL_CHIPS = 20  # extra random small facets per lump (seeded)
FILL_TOL = -0.2   # crack floors and filler hulls stay this far (px) off the centre of any cell outside
CRACK_W = 1.6     # crevice walls: faces centred within this of a seam (px)
CHAMFER = 0.012   # fracture-edge chamfer (Blender units)


def masks():
    idx, colors = SM.load(NAME, ref=ROOT / "reference" / "models")
    inner = SM.masks(idx, colors)["inner"]
    return ["".join("#" if inner[r][c] else "." for c in range(len(inner[0]))) for r in range(len(inner))]


def owner(c, r, lumps=LUMPS):
    """The lump under sprite point (c, r): a power diagram of the seeds (straight seams, convex)."""
    best, bi = None, None
    for i, (_, cx, cy, rad) in enumerate(lumps):
        d = (c - cx) ** 2 + (r - cy) ** 2 - rad ** 2
        if best is None or d < best:
            best, bi = d, i
    return bi


# --- 2D helpers (newshd-123's; should move into a shared rock lib) --------------------------------
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


def floor_of(a, b):
    return min(lip_of(a), lip_of(b)) - DEPTH


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
                           32 if len(cells) > 60 else 20):
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
        # a crevice when a step past the region's edge lands in another lump (not over the outline)
        hits = [G.at(c + ux * t, r + uy * t) for t in (0.5, 0.9)]
        probe = next((h for h in hits if h not in (-1, li)), -1)
        if probe != -1:
            own = lip_of(li)
            pts.append((c - ux * LIP - 12, r - uy * LIP, own + j(0.08)))
            keep.append(pts[-1])
            reach = [t for t in (PAST * 1.3, PAST, 0.7, 0.4, 0.0) if G.at(c + ux * t, r + uy * t) != -1]
            reach = [t for t in reach if G.hull_ok(base + floor2d + [(c + ux * t, r + uy * t)], bad0)]
            far = reach[0] if reach else 0.0
            near = min(far, NEAR)
            floor2d.append((c + ux * far, r + uy * far))
            pts.append((c + ux * near - 12, r + uy * near, floor_of(li, probe) + j(0.08)))
            pts.append((c + ux * far - 12, r + uy * far, j(0.5)))
        else:
            # outline: the widest ring near z = 0, a chamfered shoulder above it
            pts.append((c - ux * OUT_IN - 12 + j(0.05), r - uy * OUT_IN + j(0.05), j(0.8)))
            keep.append(pts[-1])
            pts.append((c - ux * 1.1 - 12 + j(0.3), r - uy * 1.1 + j(0.3), peak * rng.uniform(0.42, 0.56)))
        for f, zf in TOP_OF.get(name, TOP_RINGS):  # top rings toward the crest
            if rng.random() < TOP_JIT[2]:
                tc, tr, tz = pc + (c - pc) * f + j(TOP_JIT[0]), pr + (r - pr) * f + j(TOP_JIT[0]), peak * zf + j(TOP_JIT[1])
                # held back behind the lip, so the lip is the groove's edge and its wall drops
                # steeply to the floor (a top point near the seam would roof the groove over)
                for _ in range(20):
                    if G.seam_dist(tc, tr) >= LIP + 0.15 or math.hypot(tc - pc, tr - pr) < 0.3:
                        break
                    tc, tr = tc + (pc - tc) * 0.12, tr + (pr - tr) * 0.12
                pts.append((tc - 12, tr, tz))
        for f, z in ((0.86, BELLY * 0.42), (0.55, BELLY * 0.84)):  # belly, toward the rock's centre
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
    """Flat facets knocked off a lump: each a plane (normal from azimuth/elevation in sprite terms,
    `depth` px below the lump's highest point along it) cut off and capped flat. A chip that would cut
    a point of `keep` is skipped, so the crevices and the silhouette hold."""
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
    extra = [(rng.uniform(0, 360), rng.uniform(25, 55), rng.uniform(0.3, 0.8)) for _ in range(SMALL_CHIPS)]
    chip(bm, chips + extra, keep)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.5), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, pts


def filler_points(G, pts_of, a, b):
    """Points of lumps a and b near their seam and below their groove floor: their hull bridges the V
    crease two convex lumps leave down the rock's flanks, so a crevice runs in from the top and closes
    lower down instead of splitting the rock like a pumpkin's ribs."""
    zmax = floor_of(a, b) - 0.3
    pts = [(x, y, z) for li in (a, b) for (x, y, z) in pts_of[li]
           if z <= zmax and G.seam_dist(x + 12, y, {a, b}) < 3.2]
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
            mats.append(common.palette_material(sprite, idx, NAME, metallic=0.0, roughness=0.86))
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

    # crevice walls: steep faces near a seam whose outward side runs into another lump, in the groove
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
        if nbs and cpt.z < min(lip_of(li), lip_of(nbs[0])) + 0.3 and \
                max(v.co.z for v in f.verts) < lip_of(li) + 0.2:
            f.material_index = crack

    # sprite px to Blender (a reflection in y: flip the faces)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    # chamfer the fracture edges (one narrow segment): each break catches a thin line of light
    bev = obj.modifiers.new("chamfer", "BEVEL")
    bev.width = CHAMFER
    bev.segments = 1
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(25)
    common._apply_modifiers(obj)
    return sprite, obj, coll


# --- the crystal ---------------------------------------------------------------------------------
GEM_C = (12.5, 14.5)  # sprite point of the light (col, row): the four crevices' junction
# Each look: (name, frames, girdle radius px (tip on the axes), apex height over the girdle px,
# bands [(palette, emission, {frame: palette})] outer to heart, metallic, roughness).
GEMS = [
    ("dormant", [229], 1.3, 1.6, [(102, 0.0, None)]),
    ("small", [231], 1.9, 2.6, [(151, 3.0, None), (154, 4.0, None)]),
    ("big", [233, 235], 2.8, 3.6, [(150, 3.5, {235: 154}), (152, 4.0, {235: 156}),
                                   (154, 4.5, {235: 158}), (157, 6.0, {235: 141})]),
]
GEM_SINK = 1.5  # girdle this far (px) above the groove floor at the junction


def floor_z(obj, c, r):
    """Height (px) of the rock's top surface over sprite point (c, r)."""
    o = Vector(((c - 12) * PX, (14 - r) * PX, 3.0))
    hit, loc, *_ = obj.ray_cast(o, Vector((0, 0, -1)))
    return loc.z / PX if hit else 0.0


def gem(sprite, coll, name, frames, rad, height, bands, z0):
    """A four-sided bipyramid crystal, its tips along the sprite's axes (its top view the sprite's
    diamond): a short vertical girdle, then crown rings shrinking to the apex, one ring per colour
    band, so from above the bands nest as the sprite's rings do; the pavilion sinks into the rock."""
    n = len(bands)
    bm = bmesh.new()
    mats = []
    for k, (idx, em, fr) in enumerate(bands):
        mats.append(common.palette_material(sprite, idx, f"{NAME}_{name}{k}", metallic=0.1 if em else 0.0,
                                            roughness=0.18 if em else 0.35, emission_strength=em, frames=fr))
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    gc, gr = GEM_C

    def ring(rr, z):
        return [bm.verts.new((gc - 12 + rr * dx, gr + rr * dy, z)) for dx, dy in dirs]

    gl = ring(rad, z0 - 0.35)
    gu = ring(rad, z0)
    apex = bm.verts.new((gc - 12, gr, z0 + height))
    bottom = bm.verts.new((gc - 12, gr, z0 - 0.35 - 2.6))

    def fan(rr, z, at):  # a ring of 4 at angles `at` + 90 k
        return [bm.verts.new((gc - 12 + rr * math.cos(math.radians(at + 90 * k)),
                              gr + rr * math.sin(math.radians(at + 90 * k)), z)) for k in range(4)]
    for k in range(4):
        j = (k + 1) % 4
        bm.faces.new((gl[k], gl[j], gu[j], gu[k])).material_index = 0
        bm.faces.new((gl[j], gl[k], bottom)).material_index = 0
    if n <= 2:
        # one crown: girdle to a heart ring (0.34 r) and its apex
        hr = ring(rad * 0.34, z0 + height * 0.7) if n == 2 else None
        for k in range(4):
            j = (k + 1) % 4
            if hr:
                bm.faces.new((gu[k], gu[j], hr[j], hr[k])).material_index = 0
                bm.faces.new((hr[k], hr[j], apex)).material_index = 1
            else:
                bm.faces.new((gu[k], gu[j], apex)).material_index = 0
    else:
        # the sprite's star: tips (band 0) round a square table on the diagonals (band 1, its corners
        # over the diagonal pixels), a diamond on the axes inside it (band 2, the four pixels next to
        # the heart) and the heart's own little pyramid (band 3)
        sq = fan(rad * 0.66, z0 + height * 0.38, 45)   # corners between tips k and k+1
        dm = ring(rad * 0.45, z0 + height * 0.66)
        ht = ring(rad * 0.21, z0 + height * 0.86)
        for k in range(4):
            j = (k + 1) % 4
            i = (k - 1) % 4
            bm.faces.new((gu[k], gu[j], sq[k])).material_index = 0      # edge facet
            bm.faces.new((sq[i], gu[k], sq[k])).material_index = 0      # tip facet
            bm.faces.new((sq[i], sq[k], dm[k])).material_index = 1      # tip-side table facet
            bm.faces.new((dm[k], sq[k], dm[j])).material_index = 1      # diagonal table facet
            bm.faces.new((dm[k], dm[j], ht[j], ht[k])).material_index = 2
            bm.faces.new((ht[k], ht[j], apex)).material_index = 3
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    obj = common.mesh_object(f"{NAME}_light_{name}", bm, mats, coll, smooth=False)
    return common.frame_part(obj, frames)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite, obj, coll = build()
    zf = min(floor_z(obj, GEM_C[0] + dx, GEM_C[1] + dy) for dx in (-0.3, 0.3) for dy in (-0.3, 0.3))
    print(f"groove floor at the junction: {zf:.2f} px")
    gems = [gem(sprite, coll, nm, fr, rad, h, bands, zf + GEM_SINK) for nm, fr, rad, h, bands in GEMS]
    fmt = "AUTO"
    if "--no-bake" not in argv:
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
    shell = common.outline_shell(obj, coll, faces=2500)
    shell.name = f"{NAME}_outline"
    objs = [obj] + gems + [shell]
    if out:
        common.export_glb(objs, out, image_format=fmt)
    else:
        common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"], image_format=fmt)
    tris = []
    for o in objs:
        o.data.calc_loop_triangles()
        tris.append(len(o.data.loop_triangles))
    print(f"built {NAME}: rock {tris[0]}, gems {tris[1:-1]}, shell {tris[-1]}, total {sum(tris)}")


if __name__ == "__main__":
    main()
