"""Hard-surface pipe junction for ASTEROID?'s pipe junction (map 1-3 ground, layer 0; shapesz.dat rows 238-249, cols 3-11),
hard-surface (D65's standard for structures, D141): exported with lb.Building.export (baked).

What the tiles paint, and how it is built (pattern px, y down; 1 unit = 12 px; z = 0 the ground):
- a ring of boulders round the whole platform (the rim tiles 360-382): a dark rubble bed (one prism,
  the footprint's outline with the channels' interior cut out as a hole) with faceted boulders where
  the art paints its stones (lib_tiles.hills on the art's brightness: one boulder per lit stone, its
  ellipse, its own palette index);
- a parapet of masonry posts just inside the rocks (the art's row of light bars), split every 4 px;
- brick masonry (running bond, the art's own brick size, each brick in the palette index the art
  paints under it, within one step of the masonry's median) on a mortar deck, round the channels and on
  the L-shaped islands the loops wind round;
- the brown channels (tiles 365/367/379/385/387/389/366/376, a strip 16-18 px wide through each cell's
  centre, rounded at the turns): recessed 1 px under the deck, a dark floor with the art's rust-brown
  pavers (its brown blobs, outlines simplified, each in its own index);
- the stem's open end (the base complex's top rows 10-11 are the base model's): the channel floor
  climbs three sluice steps to the base's channel height (0.312) and the deck, bricks and rubble meet
  the base's heights (deck 0.300, plates 0.345, bed 0.28) at py 280.

No ground enemies sit on it. Underside: the slabs' flat bottoms only.

    blender --background --factory-startup --python assets/blender/tiles/l1bld_pipe_junction.py -- [--no-bake] [--views <dir>]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, geometry  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402

OUT = Path("/Users/dlomibao/projects/tyrian-scratch/structures-1/l1bld_pipe_junction/final")
END_PY = 280  # the model's last row (rows 10-11 are the base complex's)

# Heights (units). The base complex (its blueprint) uses bed 0.28, deck 0.300, plates 0.345,
# channel 0.312, kerb 0.366: the stem's end meets those.
Z_BOTTOM = -0.04
FLOOR = 0.215  # channel floor (1 px under the deck)
PAVER = 0.012  # the rust pavers stand this much on the floor
BED = 0.28  # rubble under the boulders
ROCK_TOP = 0.56  # highest boulder (no enemies on this building; TALL_MAX 0.8)
DECK = 0.300  # mortar deck
BRICK = 0.345  # brick tops
POST = 0.368  # parapet posts
ISLAND = 0.365  # the islands' bricks stand a little proud of the deck round them
SLUICE = [(254, 0.245), (263, 0.275), (271, 0.312)]  # (from py, floor z) up the stem's end

# Channel strips: through each channel tile's centre (11, 13.5), +-8 px across a vertical run, +-9
# across a horizontal one (measured on tiles 389 and 379), rounded r 4 at the turns.
CH_SIGMA, CH_T, CH_LIGHT = 2.0, 0.10, 0.6  # channel evidence (brown density - 0.6 light density) > 0.10
AXIS = 107.5  # the art's mirror axis (px)
STEM_Y0 = 150  # below this the stem is one straight strip
ROCK_BAND = 11  # px from the outline: the boulders (the art's rock tiles end there)
POST_BAND = 6  # the parapet's width inside the rocks
POST_PITCH = 4.8  # px between the parapet posts
BRICK_W, BRICK_H, GAP = 5.0, 4.0, 0.7  # brick module (px) and the joint
PAVER_W, PAVER_H, PAVER_GAP = 5.0, 4.0, 0.6  # the channel's pavers


# --- pixel helpers ------------------------------------------------------------------------------

def disc_dilate(mask, r):
    out = mask.copy()
    h, w = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r + r * 0.5:
                continue
            src = mask[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
            out[max(0, dy):h - max(0, -dy), max(0, dx):w - max(0, -dx)] |= src
    return out


def disc_erode(mask, r):
    return ~disc_dilate(~mask, r)


def fill_holes(mask):
    out = mask.copy()
    for ys, xs in lt.components(~mask):
        if ys.min() > 0 and xs.min() > 0 and ys.max() < mask.shape[0] - 1 and xs.max() < mask.shape[1] - 1:
            out[ys, xs] = True
    return out


def channel_mask(b):
    """The brown channels where the art paints them: brown-fleck density minus light-brick density
    (Gaussian, sigma 2), made mirror-symmetric about x = 107.5 (the art's own axis), thresholded,
    opened, specks dropped and small holes filled; the stem below py 150 a straight strip at the
    art's mean edges. The islands the loops wind round stay out (holes)."""
    g = np.maximum(b.grid, 0)
    brown = np.vectorize(is_brown)(g) & (b.grid >= 0)
    light = (b.grid >= 6) & ~brown
    ev = lt.blur(brown.astype(float), CH_SIGMA) - CH_LIGHT * lt.blur(light.astype(float), CH_SIGMA)
    ev = (ev + np.roll(ev[:, ::-1], -1, axis=1)) / 2
    m = lb.open_(ev > CH_T, 1)
    m = lb.drop_small(m, 60)
    holes = ~m
    m |= holes & ~lb.drop_small(holes, 40)
    # The stem: straight, symmetric about the axis, as wide as the art's channel there on average.
    rows = m[STEM_Y0:END_PY]
    w = float(np.mean(rows.sum(axis=1)))
    x0, x1 = AXIS - w / 2, AXIS + w / 2
    m[STEM_Y0:] = False
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]] + 0.5
    m |= (yy >= STEM_Y0) & (xx >= x0) & (xx < x1)
    print(f"stem channel x {x0:.1f}..{x1:.1f} ({w:.1f} px)")
    # Smooth the outline a little (blur and re-threshold: round corners, no pixel wobble).
    m = lt.blur(m.astype(float), 1.0) > 0.5
    return m


def region_index(grid, lum, mask, keep=None):
    """The art's palette index for a region: median by brightness of its pixels, the darkest and
    brightest eighth left out (shading and highlights are lighting)."""
    v = [int(i) for i in grid[mask] if i > 0 and (keep is None or keep(int(i)))]
    if not v:
        return None
    v.sort(key=lambda i: lum[i])
    k = len(v) // 8
    core = v[k:len(v) - k] or v
    return core[len(core) // 2]


def is_brown(i):
    return 160 <= i < 176 or 16 <= i < 32


def is_grey(i):
    return 1 <= i <= 15


# --- geometry helpers (copies of the kit's shapes, plus holes) ----------------------------------

def loops_of(mask, tol, min_px=6):
    """[(outer, [holes])] per 4-connected part of `mask`: pixel-corner outlines, simplified."""
    out = []
    H, W = mask.shape
    for ys, xs in lt.components(mask):
        if len(ys) < min_px:
            continue
        part = np.zeros(mask.shape, bool)
        part[ys, xs] = True
        outer = ls.simplify(ls.trace(part), tol)
        holes = []
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sub = ~part[y0:y1, x0:x1]
        for hy, hx in lt.components(sub):
            if hy.min() == 0 or hx.min() == 0 or hy.max() == sub.shape[0] - 1 or hx.max() == sub.shape[1] - 1:
                continue
            if len(hy) < min_px:
                continue
            hm = np.zeros(mask.shape, bool)
            hm[hy + y0, hx + x0] = True
            holes.append(ls.simplify(ls.trace(hm), tol))
        out.append((outer, holes))
    return out


def ccw(poly):
    return list(poly) if ls.area(poly) > 0 else list(reversed(poly))


def prism(b, outer, holes, z0, z1, mat, chamfer=0.0, drop=0.0, side_mat=None, bevel_mat=None, bottom=True):
    """A closed prism over a polygon with holes (pattern px), flat top at z1, the top edge chamfered
    `chamfer` px in (holes out) and `drop` down."""
    side_mat = mat if side_mat is None else side_mat
    bevel_mat = mat if bevel_mat is None else bevel_mat
    outer = ccw([(float(x), float(y)) for x, y in outer])
    holes = [ccw([(float(x), float(y)) for x, y in h]) for h in holes]
    bm = bmesh.new()
    V = lambda p, z: bm.verts.new((b.x(p[0]), b.y(p[1]), z))
    tops = []
    bots = []
    for loop, sign in [(outer, 1)] + [(h, -1) for h in holes]:
        base = [V(p, z0) for p in loop]
        if chamfer and drop:
            top_pts = ls.inset(loop, chamfer * sign)
            mid = [V(p, z1 - drop) for p in loop]
            top = [V(p, z1) for p in top_pts]
            rings, mats = [base, mid, top], [side_mat, bevel_mat]
        else:
            top = [V(p, z1) for p in loop]
            rings, mats = [base, top], [side_mat]
        n = len(loop)
        for (a, c), mi in zip(zip(rings, rings[1:]), mats):
            for i in range(n):
                j = (i + 1) % n
                f = bm.faces.new((a[i], a[j], c[j], c[i]))
                f.material_index = mi
        tops.append(top)
        bots.append(base)
    for rings_, z, up in ((tops, z1, True), (bots, z0, False)):
        if not up and not bottom:
            continue
        flat = [v for r in rings_ for v in r]
        tris = geometry.tessellate_polygon([[v.co.to_tuple() for v in r] for r in rings_])
        for t in tris:
            try:
                f = bm.faces.new([flat[i] for i in t])
                f.material_index = mat if up else side_mat
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def box(b, x0, y0, x1, y1, z0, z1, mat, chamfer=0.0, drop=0.0):
    """A small closed block (pattern px box) with an optional chamfered top edge."""
    poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    prism(b, poly, [], z0, z1, mat, chamfer=chamfer, drop=drop)


def boulder(b, cx, cy, rx, ry, angle, z0, z1, mat, rng, sides=7):
    """A faceted boulder: base ring, a wide shoulder, a narrower upper ring and a small, off-centre
    top facet (lit from the upper left, as the art), all slightly irregular: rock, flat-shaded."""
    ca, sa = math.cos(angle), math.sin(angle)
    h = z1 - z0
    prof = [(0.0, 1.0), (0.42, 0.99), (0.78, 0.76), (1.0, 0.3)]
    jit = [1.0 + (rng.random() - 0.5) * 0.28 for _ in range(sides)]
    tw = [(rng.random() - 0.5) * 0.35 for _ in range(sides)]
    bm = bmesh.new()
    rings = []
    shift = (-0.18 * rx, -0.18 * ry)  # the top leans to the light (upper left in pattern px)
    for k, (fz, sc) in enumerate(prof):
        ring = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides + tw[i] * (0.4 if k else 0.0)
            lx, ly = rx * sc * jit[i] * math.cos(t), ry * sc * jit[i] * math.sin(t)
            lx += shift[0] * fz
            ly += shift[1] * fz
            px, py = cx + lx * ca - ly * sa, cy + lx * sa + ly * ca
            z = z0 + h * fz + (0 if k in (0, len(prof) - 1) else (rng.random() - 0.5) * 0.12 * h)
            ring.append(bm.verts.new((b.x(px), b.y(py), z)))
        rings.append(ring)
    bm.faces.new(rings[-1]).material_index = mat
    for a, c in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], c[j], c[i])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def brick_field(field, bw, bh, gap, make, grid, phase=0, min_w=2.2):
    """Running-bond courses `bh` px tall over a pixel mask: in each course, every run of columns
    wholly in the field is cut into bricks `bw` long (alternate courses offset half a brick), the
    ends clipped to the run; rows a full course can't cover get a half-height course. make(x0, y0,
    x1, y1, art_pixels) builds one (returns False to leave it out). Returns the count."""
    H, W = field.shape
    covered = np.zeros_like(field)
    n = 0
    for height in (bh, bh / 2):
        y = 0.0
        k = 0
        while y + height <= H + 1e-6:
            r0, r1 = int(round(y)), int(round(y + height))
            band = field[r0:r1] & ~covered[r0:r1]
            ok = band.all(axis=0) if r1 > r0 else np.zeros(W, bool)
            x = 0
            while x < W:
                if not ok[x]:
                    x += 1
                    continue
                a = x
                while x < W and ok[x]:
                    x += 1
                e = x
                off = ((k + phase) % 2) * bw / 2
                cuts = [a] + [c for c in np.arange(off - bw, W + bw, bw) if a + min_w <= c <= e - min_w] + [e]
                for c0, c1 in zip(cuts, cuts[1:]):
                    if c1 - c0 < min_w:
                        continue
                    vals = grid[r0:r1, int(c0):int(math.ceil(c1))]
                    if make(c0 + gap / 2, y + gap / 2, c1 - gap / 2, y + height - gap / 2, vals):
                        n += 1
                covered[r0:r1, a:e] |= True
            y += height
            k += 1
    return n


# --- the build ----------------------------------------------------------------------------------

def build(bake=True, views=None):
    b = lb.Building("pipe-junction")
    ts = b.ts
    grid = b.grid
    lum = ts.lum
    H, W = grid.shape
    rows = np.arange(H)[:, None] * np.ones((1, W), bool)
    live = rows < END_PY

    # Masks. The full pattern's footprint (rows 0-11), so the stem's cut at py 280 is not an edge.
    painted = grid > 0
    fpf = fill_holes(lb.close(painted, 2) & (grid >= 0))
    fp = b.footprint  # rows 0-9 (what the model covers)
    rock = fp & ~disc_erode(fpf, ROCK_BAND)
    chan = channel_mask(b) & fp & ~rock
    mason = fp & ~rock & ~chan
    post = mason & disc_dilate(rock, POST_BAND)
    ys_, xs_ = np.nonzero(fp)
    print(f"footprint {fp.sum()} px (rows 0..{ys_.max()}), rock {rock.sum()}, channel {chan.sum()}, masonry {mason.sum()}, parapet {post.sum()}")

    # The art's palette index per region.
    brown = np.vectorize(is_brown)(np.maximum(grid, 0))
    idx = dict(
        bed=region_index(grid, lum, rock & (grid <= 3)),
        rock=region_index(grid, lum, rock & (grid >= 4), is_grey),
        post=region_index(grid, lum, post & (grid >= 4), is_grey),
        brick=region_index(grid, lum, mason & ~post & (grid >= 4), is_grey),
        mortar=region_index(grid, lum, mason & (grid <= 3)),
        floor=region_index(grid, lum, chan & ~brown),
        rust=region_index(grid, lum, chan & brown, is_brown),
        channel=region_index(grid, lum, chan),
    )
    for k, v in idx.items():
        print(f"region {k:8s} index {v} rgb {ts.rgb(v)}")

    m = b.m
    mat_bed = m(idx["bed"], roughness=0.95)
    mat_floor = m(idx["floor"], roughness=0.9)
    mat_mortar = m(idx["mortar"], roughness=0.9)
    mat_wall = m(idx["mortar"] + 1, roughness=0.85)

    # 1. The channel floor: one slab over the whole footprint (the rubble and the deck stand on it).
    for outer, holes in loops_of(fp, tol=0.9):
        prism(b, outer, holes, Z_BOTTOM, FLOOR, mat_floor, side_mat=mat_bed)

    # 2. The rubble bed under the boulders: the footprint's outline, the rocks' inner edge a hole.
    for outer, holes in loops_of(rock | (fp & ~fpf), tol=0.9):
        prism(b, outer, holes, Z_BOTTOM + 0.01, BED, mat_bed, chamfer=1.0, drop=0.02)

    # 3. The mortar deck round the channels and the islands (holes: the channels).
    deck_mask = lb.open_(mason, 1)
    for outer, holes in loops_of(deck_mask, tol=0.8, min_px=20):
        prism(b, outer, holes, FLOOR - 0.03, DECK, mat_mortar, chamfer=0.6, drop=0.015, side_mat=mat_wall)

    # 4. The parapet: posts along the rocks' inner edge, 4 px apart (the art's light bars).
    smooth_in = lt.blur((fp & ~rock).astype(float), 1.5) > 0.5
    inner_edge = [outer for outer, hs in loops_of(smooth_in, tol=1.5, min_px=200)]
    mat_post = m(idx["post"], roughness=0.7)
    mat_post_lt = m(idx["post"] + 1, roughness=0.7)
    n_posts = 0
    for loop in inner_edge:
        loop = ccw(loop)
        inn = ls.inset(loop, POST_BAND)
        n = len(loop)
        for i in range(n):
            j = (i + 1) % n
            a, c = np.array(loop[i]), np.array(loop[j])
            ai, ci = np.array(inn[i]), np.array(inn[j])
            if a[1] >= END_PY - 1.5 and c[1] >= END_PY - 1.5:
                continue  # the open end
            L = float(np.hypot(*(c - a)))
            k = max(1, int(round(L / POST_PITCH)))
            for s in range(k):
                t0, t1 = s / k, (s + 1) / k
                g0, g1 = t0 + (0.35 / L if s else 0), t1 - (0.35 / L if s < k - 1 else 0)
                p0, p1 = a + (c - a) * g0, a + (c - a) * g1
                q0, q1 = ai + (ci - ai) * g0, ai + (ci - ai) * g1
                if max(p0[1], p1[1], q0[1], q1[1]) > END_PY:
                    continue
                mid = (p0 + p1 + q0 + q1) / 4
                v = grid[min(H - 1, int(mid[1])), min(W - 1, int(mid[0]))]
                mt = mat_post_lt if v >= idx["post"] + 2 else mat_post
                prism(b, [tuple(p0), tuple(p1), tuple(q1), tuple(q0)], [], DECK - 0.02, POST, mt, chamfer=0.35, drop=0.012, bottom=False)
                n_posts += 1
    print(f"parapet posts {n_posts}")

    # 5. Bricks: running bond over the masonry inside the parapet, each in the art's index under it
    # (within one step of the masonry's median); the islands' stand a little prouder.
    field = mason & ~disc_dilate(rock, POST_BAND) & live
    near = disc_dilate(rock, POST_BAND + 2)
    edge = np.zeros_like(mason)  # the outer masonry ring; the rest are the islands
    for ys, xs in lt.components(mason):
        if near[ys, xs].any():
            edge[ys, xs] = True
    mid_i = idx["brick"]
    isl_i = region_index(grid, lum, mason & ~edge & (grid >= 4), is_grey)
    print(f"region island   index {isl_i} rgb {ts.rgb(isl_i)} (outer masonry {mid_i})")

    def brick(x0, y0, x1, y1, vals):
        cy_, cx_ = min(H - 1, int((y0 + y1) / 2)), min(W - 1, int((x0 + x1) / 2))
        outer = edge[cy_, cx_]
        base_i = mid_i if outer else isl_i
        vi = region_index(vals, lum, np.ones(vals.shape, bool), is_grey) or base_i
        vi = int(min(base_i + 1, max(base_i - 1, vi)))
        top = BRICK if outer else ISLAND
        prism(b, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [], DECK - 0.02, top - (0.006 if vi < mid_i else 0),
              m(vi, roughness=0.75), bottom=False)
        return True

    nb = brick_field(field, BRICK_W, BRICK_H, GAP, brick, grid)
    print(f"bricks {nb}")

    # 6. The channel's paving: rust-brown pavers in running bond on the dark floor, each in the brown
    # the art paints under it; where the art is mostly dark, the paver is missing (its dark mottle).
    def floor_at(py):
        z = FLOOR
        for y0, zz in SLUICE:
            if py >= y0:
                z = zz
        return z

    rust_i = idx["rust"]

    def paver(x0, y0, x1, y1, vals):
        bv = [int(v) for v in vals.ravel() if v > 0 and is_brown(int(v))]
        frac = len(bv) / max(1, vals.size)
        if frac < 0.18:
            return False
        vi = region_index(np.array(bv), lum, np.ones(len(bv), bool), is_brown) if frac >= 0.45 else 163
        vi = vi or rust_i
        z0 = floor_at((y0 + y1) / 2)
        prism(b, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [], z0 - 0.01, z0 + PAVER, m(vi, roughness=0.8), bottom=False)
        return True

    pave_field = disc_erode(chan, 1) & live
    npv = brick_field(pave_field, PAVER_W, PAVER_H, PAVER_GAP, paver, grid, phase=1)
    print(f"rust pavers {npv}")

    # 7. The sluice steps at the stem's end, up to the base's channel height (0.312) at py 280.
    stem = chan & (rows >= SLUICE[0][0]) & live
    sx = np.nonzero(stem.any(axis=0))[0]
    x0s, x1s = float(sx.min()), float(sx.max() + 1)
    mat_step = m(idx["mortar"] + 2, roughness=0.7)
    for k, (y0, z) in enumerate(SLUICE):
        prism(b, s_rbox(x0s, y0, x1s, END_PY), [], FLOOR - 0.02, z, mat_step if k < len(SLUICE) - 1 else m(idx["rust"], roughness=0.8),
              chamfer=0.4, drop=0.01)

    # 8. Boulders: one per stone the art paints in the rim (its brightness hills), its ellipse and index.
    rng = __import__("random").Random(238)
    lumg = np.where(grid >= 0, lum[np.maximum(grid, 0)], 0.0)
    stones = lt.hills(lumg, rock & live & (grid >= 2), sigma=1.6, floor=0.17)
    nr = 0
    for ys, xs in stones:
        if len(ys) < 5:
            continue
        cx, cy, rx, ry, ang = lt.ellipse(ys, xs)
        rx, ry = min(7.5, max(2.6, rx * 1.15)), min(7.5, max(2.6, ry * 1.15))
        if cy + max(rx, ry) * 0.8 > END_PY:
            continue
        part = np.zeros_like(rock)
        part[ys, xs] = True
        vi = region_index(grid, lum, part, is_grey) or idx["rock"]
        vi = int(min(idx["rock"] + 2, max(idx["rock"] - 1, vi)))
        r = (rx + ry) / 2
        top = min(ROCK_TOP, BED + 0.08 + 0.034 * r + 0.03 * rng.random())
        boulder(b, cx, cy, rx, ry, ang, BED - 0.06, top, m(vi, roughness=0.85), rng, sides=rng.choice((6, 7)))
        nr += 1
    print(f"boulders {nr}")

    coll = common.reset_collection("pipe-junction")
    bmesh.ops.recalc_face_normals(b.parts, faces=b.parts.faces)
    obj = lb.mesh_object("shapesz-l1bld-pipe-junction", b.parts, b.pal.materials, coll)
    objects = [obj]
    b.check(objects)
    iou = b.top_iou(objects, fp)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"triangles {tris}")
    if bake:
        objects = b.bake_model(objects, size=2048, ground=0.0, out_dir=OUT / "bake")
    b.export(objects, baked=bake)
    print(f"exported pipe-junction IoU {iou:.3f}")
    if views:
        render_views(b, objects, Path(views))
    return b, objects


def s_rbox(x0, y0, x1, y1, c=1.2):
    pts = []
    for qx, qy, a0 in ((x1 - c, y0 + c, -90), (x1, y1, None), (x0, y1, None), (x0 + c, y0 + c, 180)):
        if a0 is None:
            pts.append((qx, qy))
            continue
        for k in range(3):
            a = math.radians(a0 + 90 * k / 2)
            pts.append((qx + c * math.cos(a), qy + c * math.sin(a)))
    return pts


# --- views --------------------------------------------------------------------------------------

def render_views(b, objects, out):
    """EEVEE renders of the model: top (ortho), side, front, rear, 3/4 high, the game camera, underside."""
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o not in objects and o.type == "MESH":
            o.hide_render = True
    engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scene.render.engine = next((e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in engines), engines[0])
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bg.inputs[1].default_value = 0.6
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.0
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), 0, math.radians(-35))
    # a ground plane (the HD ground is dark rock)
    gm = bpy.data.meshes.new("gnd")
    gbm = bmesh.new()
    s = 30
    vs = [gbm.verts.new((x, y, 0)) for x, y in ((-s, -s), (s, -s), (s, s), (-s, s))]
    gbm.faces.new(vs)
    gbm.to_mesh(gm)
    gnd = bpy.data.objects.new("gnd", gm)
    gmat = common.material("gnd", (0.02, 0.02, 0.022), roughness=1.0)
    gm.materials.append(gmat)
    scene.collection.objects.link(gnd)

    w, h = b.W * lt.PX, END_PY * lt.PX
    cy0 = b.y(END_PY / 2)  # the covered part's centre
    centre = Vector((0, cy0, 0.2))

    def cam(name, loc, look, ortho=None, lens=50, res=(1200, 1200), fov=None):
        data = bpy.data.cameras.new(name)
        if fov:
            data.sensor_fit = "VERTICAL"
            data.angle = math.radians(fov)
        elif ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        data.clip_end = 500
        c = bpy.data.objects.new(name, data)
        scene.collection.objects.link(c)
        c.location = loc
        c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    gnd.hide_render = False
    cam("top", (0, cy0, 20), (0, cy0, 0), ortho=max(w, h) * 1.02, res=(int(1200 * w / h), 1200))
    wing = Vector((0, b.y(70), 0.3))
    el = math.radians(14)
    cam("side", wing + Vector((-24 * math.cos(el), 0, 24 * math.sin(el))), wing, lens=50, res=(1400, 700))
    cam("front", wing + Vector((0, -30 * math.cos(el), 30 * math.sin(el))), wing, lens=50, res=(1400, 700))
    cam("rear", wing + Vector((0, 24 * math.cos(el), 24 * math.sin(el))), wing, lens=50, res=(1400, 700))
    cam("q34", centre + Vector((14, -16, 13)), centre, lens=40, res=(1400, 1050))
    # the game camera (src/render/view.ts): fov 40, 15 degrees off straight down from the screen's bottom
    for name, tilt, dist, aim in (("game", 15, 30, centre), ("game_close", 32, 13, Vector((0, b.y(80), 0.3)))):
        t = math.radians(tilt)
        cam(name, aim + Vector((0, -dist * math.sin(t), dist * math.cos(t))), aim, fov=40,
            res=(1200, 1400) if name == "game" else (1400, 1000))
    gnd.hide_render = True
    cam("under", (0, cy0, -20), (0, cy0, 0), ortho=max(w, h) * 1.02, res=(int(900 * w / h), 900))


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, views=argv[argv.index("--views") + 1] if "--views" in argv else None)
