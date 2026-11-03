"""Helpers for the background structure models (DECISIONS.md D34): 3D versions of background tiles.

The tiles come from `npm run tiles` (tests/tools/tileReference.test.ts), which writes
reference/tiles/<shapes>/tiles.json: each tile's pixels as palette indices at 1x and MMPX 2x, the
layers and levels that use it, and the in-level palette's colours. reference/ is git-ignored (D3);
the models are the tile art in 3D, which may be committed (D16).

Conventions (as for the enemy models, assets/blender/README.md):
- 1 unit = 12 tile px. A model stands for a pattern of tiles, `rows` x `cols`, and its origin is
  the pattern's centre. Blender X = screen right, Y = screen up, Z = up.
- Background 3 (layer 2) models are placed at their draw pass's height (D5): z = 0 is the top
  of the structure's base; keep them within about -0.35..+0.35 so they stay between the passes
  above and below. Ground (layer 0) models stand on the ground at z = 0 and keep low (ground
  enemies sit on some of them at 0.45 units).
- Colours are palette materials (pal_<index>_<tag>), so level palettes and fades apply.
"""

import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np

import common

TILE_W, TILE_H = 24, 28
PX = 1 / 12  # units per tile pixel


class Tileset:
    """reference/tiles/<shapes>/tiles.json, with each tile's pixels as numpy arrays."""

    def __init__(self, root, shapes="shapesz", layer=0):
        path = Path(root) / "reference" / "tiles" / shapes / "tiles.json"
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing: run `npm run tiles` (TILES_SHAPES={shapes[6:]})")
        data = json.loads(path.read_text())
        self.root = Path(root)
        #: The layer being modelled: on layers 1 and 2, index 0 is transparent (as the game draws
        #: them), whatever other levels use the tile for.
        self.layer = layer
        self.name = shapes
        self.file = data["shapes"]
        self.colors = {int(k): tuple(v) for k, v in data["colors"].items()}
        self.tiles = {}
        for n, t in data["tiles"].items():
            t["px"] = np.array([[int(v) for v in r.split()] for r in t["pixels"]], dtype=np.int32)
            t["px2"] = np.array([[int(v) for v in r.split()] for r in t["pixels2x"]], dtype=np.int32)
            self.tiles[int(n)] = t
        lum = np.zeros(256)
        for i, (r, g, b) in self.colors.items():
            lum[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        self.lum = lum

    def grid(self, pattern, scale=1):
        """The pattern's pixels as one array (rows x cols tiles, `scale` 1 or 2), -1 = transparent:
        index 0 when modelling layer 1 or 2, and pattern cells of -1."""
        rows, cols = len(pattern), len(pattern[0])
        h, w = TILE_H * scale, TILE_W * scale
        out = np.full((rows * h, cols * w), -1, dtype=np.int32)
        for r, row in enumerate(pattern):
            for c, n in enumerate(row):
                if n < 0:
                    continue
                t = self.tiles[n]
                px = (t["px"] if scale == 1 else t["px2"]).copy()
                if self.layer > 0:
                    px[px == 0] = -1
                out[r * h:(r + 1) * h, c * w:(c + 1) * w] = px
        return out

    def rgb(self, index):
        return self.colors[int(index)]


class Frame:
    """Pixel coordinates of a pattern to model coordinates (origin at the pattern's centre)."""

    def __init__(self, pattern, scale=1):
        self.rows, self.cols = len(pattern), len(pattern[0])
        self.scale = scale
        self.w = TILE_W * self.cols * scale
        self.h = TILE_H * self.rows * scale
        self.unit = PX / scale

    def x(self, px):
        """Pixel column (any fraction; a pixel's left edge is its integer) to X."""
        return (px - self.w / 2) * self.unit

    def y(self, py):
        """Pixel row (a pixel's top edge is its integer) to Y."""
        return (self.h / 2 - py) * self.unit


class Palette:
    """Palette materials for one model, made on demand: pal(index) -> material slot."""

    def __init__(self, ts, tag, **defaults):
        self.ts, self.tag, self.defaults = ts, tag, defaults
        self.materials = []
        self.slots = {}

    def __call__(self, index, **kw):
        key = (int(index), tuple(sorted(kw.items())))
        if key not in self.slots:
            opts = dict(self.defaults)
            opts.update(kw)
            name = f"pal_{int(index)}_{self.tag}" + ("" if not kw else "_" + "_".join(f"{k}{v}" for k, v in sorted(kw.items())))
            emission = opts.pop("emission_strength", 0.0)
            # `plain=True`: texture_bake.py leaves the material untextured (the island rock, which
            # must look the same in a structure as on the per-tile models round it).
            plain = opts.pop("plain", False)
            color = common.srgb(*self.ts.rgb(index))
            mat = common.material(name, color, emission=color if emission else None, emission_strength=emission, **opts)
            if plain:
                mat["tyrian_plain"] = True
            self.slots[key] = len(self.materials)
            self.materials.append(mat)
        return self.slots[key]


# --- Geometry ------------------------------------------------------------------------------------

def mask_slab(bm, mask, frame, z_bottom, z_top, mat_top, mat_side=None, mat_bottom=None, top_height=None, smooth_top=False,
              support=None):
    """A slab with the outline of `mask` (bool array in `frame` pixels) from z_bottom to z_top.

    `top_height`, an array like mask, raises each top cell by that much (a relief); side walls
    follow it. With `smooth_top` a corner takes the mean of its cells' heights (else the highest)
    and the top is smooth shaded, for carved surfaces; the sides stay flat. Coplanar top faces of
    one material can be merged afterwards (dissolve_coplanar). `mat_top` and `mat_side` are a
    material slot or a function (x, y) -> slot of the cell (for a side, the cell it closes).
    `support` (bool, like mask; default mask) is the cells a corner's height comes from: a piece
    cut from a bigger relief passes the whole relief's cells, so pieces built apart meet exactly."""
    mat_side = mat_top if mat_side is None else mat_side
    mat_bottom = mat_side if mat_bottom is None else mat_bottom
    support = mask if support is None else support
    h, w = mask.shape
    top_v, bot_v = {}, {}

    def corner_z(cx, cy):
        if top_height is None:
            return z_top
        vals = [top_height[y, x] for y in (cy - 1, cy) for x in (cx - 1, cx) if 0 <= y < h and 0 <= x < w and support[y, x]]
        if not vals:
            return z_top
        return z_top + (sum(vals) / len(vals) if smooth_top else max(vals))

    def vt(cx, cy):
        v = top_v.get((cx, cy))
        if v is None:
            v = top_v[(cx, cy)] = bm.verts.new((frame.x(cx), frame.y(cy), corner_z(cx, cy)))
        return v

    def vb(cx, cy):
        v = bot_v.get((cx, cy))
        if v is None:
            v = bot_v[(cx, cy)] = bm.verts.new((frame.x(cx), frame.y(cy), z_bottom))
        return v

    mats = mat_top if callable(mat_top) else (lambda x, y: mat_top)
    sides = mat_side if callable(mat_side) else (lambda x, y: mat_side)
    bottoms = mat_bottom if callable(mat_bottom) else (lambda x, y: mat_bottom)
    for y in range(h):
        for x in range(w):
            if not mask[y, x]:
                continue
            # Counter-clockwise seen from above (+Z): screen y grows downward, Blender Y upward.
            f = bm.faces.new((vt(x, y + 1), vt(x + 1, y + 1), vt(x + 1, y), vt(x, y)))
            f.material_index = mats(x, y)
            f.smooth = smooth_top
            bm.faces.new((vb(x, y), vb(x + 1, y), vb(x + 1, y + 1), vb(x, y + 1))).material_index = bottoms(x, y)
            for (dx, dy), (a, b) in (((0, -1), ((x, y), (x + 1, y))), ((1, 0), ((x + 1, y), (x + 1, y + 1))),
                                     ((0, 1), ((x + 1, y + 1), (x, y + 1))), ((-1, 0), ((x, y + 1), (x, y)))):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and mask[ny, nx]:
                    continue
                bm.faces.new((vb(*a), vb(*b), vt(*b), vt(*a))).material_index = sides(x, y)


def dissolve_coplanar(bm):
    """Merge coplanar faces of the same material (fewer triangles for the flat parts)."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts, edges=bm.edges, delimit={"MATERIAL"})


def dome(bm, cx, cy, rx, ry, angle, z0, height, mat, sides=10, rings=3, squash=0.0):
    """A rounded stone: a half ellipsoid on the plane z = z0, radii rx, ry (units) turned by `angle`.
    `squash` (0..1) flattens its top."""
    ca, sa = math.cos(angle), math.sin(angle)
    top = bm.verts.new((cx, cy, z0 + height * (1 - squash * 0.3)))
    ring_verts = []
    for k in range(1, rings + 1):
        phi = (math.pi / 2) * k / rings  # from the top down to the equator
        r = math.sin(phi)
        z = z0 + height * math.cos(phi) * (1 - squash * 0.3 * (1 - k / rings))
        ring = []
        for i in range(sides):
            t = 2 * math.pi * i / sides
            lx, ly = rx * r * math.cos(t), ry * r * math.sin(t)
            ring.append(bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, z)))
        ring_verts.append(ring)
    first = ring_verts[0]
    for i in range(sides):
        bm.faces.new((top, first[i], first[(i + 1) % sides])).material_index = mat
    for r0, r1 in zip(ring_verts, ring_verts[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r1[i], r1[j], r0[j])).material_index = mat
    bm.faces.new(list(reversed(ring_verts[-1]))).material_index = mat  # bottom


def block(bm, cx, cy, rx, ry, angle, z0, height, mat, sides=8, bevel=0.3):
    """A carved block: an elliptic prism of `sides` faces (8: octagonal) with a bevelled top, on the
    plane z = z0, radii rx, ry (units) turned by `angle`."""
    ca, sa = math.cos(angle), math.sin(angle)

    def ring(scale, z):
        out = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides
            lx, ly = rx * scale * math.cos(t), ry * scale * math.sin(t)
            out.append(bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, z)))
        return out

    top = ring(1 - bevel, z0 + height)
    edge = ring(1.0, z0 + height * (1 - bevel * 0.8))
    base = ring(1.0, z0)
    bm.faces.new(top).material_index = mat
    for a, b in ((top, edge), (edge, base)):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((b[i], b[j], a[j], a[i])).material_index = mat
    bm.faces.new(list(reversed(base))).material_index = mat


def components(mask):
    """4-connected components of a bool array: a list of (ys, xs) index arrays."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or seen[y0, x0]:
                continue
            stack = [(y0, x0)]
            seen[y0, x0] = True
            ys, xs = [], []
            while stack:
                y, x = stack.pop()
                ys.append(y)
                xs.append(x)
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            out.append((np.array(ys), np.array(xs)))
    return out


def blur(img, sigma):
    """Gaussian blur of a 2D array (edges repeat)."""
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(img, r, mode="edge")
    tmp = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, pad)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, tmp)


def hills(lum, mask, sigma=2.0, floor=0.2):
    """Split the masked pixels into bright hills: each pixel climbs the smoothed brightness to a
    local peak, and the pixels that reach one peak are one blob (a stone, a tree crown). Pixels
    darker than `floor` (the gaps) are left out. Returns (ys, xs) arrays, as components()."""
    h, w = lum.shape
    sm = blur(np.where(mask, lum, 0.0), sigma)
    sm = np.where(mask, sm, -1.0)
    nxt = np.arange(h * w)
    for y in range(h):
        for x in range(w):
            if not mask[y, x]:
                continue
            best, bv = y * w + x, sm[y, x]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and sm[ny, nx] > bv:
                        best, bv = ny * w + nx, sm[ny, nx]
            nxt[y * w + x] = best
    for _ in range(h + w):  # follow the pointers to the peaks
        nxt = nxt[nxt]
    labels = nxt.reshape(h, w)
    keep = mask & (lum > floor)
    out = []
    for peak in np.unique(labels[keep]):
        ys, xs = np.nonzero(keep & (labels == peak))
        out.append((ys, xs))
    return out


def ellipse(ys, xs):
    """Centre, radii (in pixels, ~2 sigma) and angle of a pixel blob, from its second moments."""
    cy, cx = ys.mean() + 0.5, xs.mean() + 0.5
    if len(xs) < 3:
        return cx, cy, 0.8, 0.8, 0.0
    cov = np.cov(np.stack([xs + 0.5 - cx, ys + 0.5 - cy]))
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, 0.15)
    rx, ry = 2 * math.sqrt(vals[1]), 2 * math.sqrt(vals[0])
    angle = math.atan2(vecs[1, 1], vecs[0, 1])
    return cx, cy, rx, ry, angle


def dominant(indices, lum=None, prefer="mid", quantile=0.5):
    """The palette index a part stands for: the most common one (prefer="mode"), or a shade of its
    main colour: palette indices come in ramps of 16 shades, so the ramp with the most pixels in
    the part's brighter half wins (the dark outline doesn't), and the shade is its `quantile` by
    brightness (a little above the middle, as lighting darkens the model)."""
    vals = [int(v) for v in np.asarray(indices).ravel() if v >= 0]
    if not vals:
        return None
    if prefer == "mode" or lum is None:
        return max(set(vals), key=vals.count)
    vals.sort(key=lambda v: lum[v])
    upper = vals[len(vals) // 3:] or vals
    ramp = max({v >> 4 for v in upper}, key=lambda r: sum(1 for v in upper if v >> 4 == r))
    ramp_vals = [v for v in vals if v >> 4 == ramp]
    return ramp_vals[min(len(ramp_vals) - 1, int(len(ramp_vals) * quantile))]


def mesh(name, bm, pal, coll, smooth=False):
    return common.mesh_object(name, bm, pal.materials, coll, smooth=smooth)


# --- Export --------------------------------------------------------------------------------------

def export_tile_model(ts, objects, name, layer, pattern, keep_tiles=None):
    """Export to public/models/tiles/<shapes>/<name>.glb and register the pattern it stands for in
    src/render/tileModels/<shapes>-<name>.json (src/render/remaster/tileModels.ts)."""
    model = f"tiles/{ts.name}/{name}"
    out = common.export_glb(objects, ts.root / "public" / "models" / f"{model}.glb")
    entry = {"model": model, "shapes": ts.file, "layer": layer, "tiles": [list(map(int, r)) for r in pattern]}
    if keep_tiles is not None:
        entry["keepTiles"] = keep_tiles
    path = ts.root / "src" / "render" / "tileModels" / f"{ts.name}-{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, indent=1) + "\n")
    faces = sum(len(o.data.polygons) for o in objects if o.type == "MESH")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects if o.type == "MESH")
    print(f"exported {out} ({out.stat().st_size} bytes, {faces} faces, {tris} tris) and {path}")
    return out


def pattern_png(ts, pattern, path, scale=8):
    """The pattern as the original tiles, `scale` px per tile px, transparent where nothing is drawn,
    for previews beside the model."""
    grid = ts.grid(pattern)
    h, w = grid.shape
    img = np.zeros((h * scale, w * scale, 4), dtype=np.float32)
    for y in range(h):
        for x in range(w):
            v = grid[y, x]
            if v < 0:
                continue
            r, g, b = ts.rgb(v)
            img[y * scale:(y + 1) * scale, x * scale:(x + 1) * scale] = (r / 255, g / 255, b / 255, 1)
    flipped = img[::-1]  # Blender images are bottom-up
    out = bpy.data.images.new("pattern_png", w * scale, h * scale, alpha=True)
    out.pixels[:] = flipped.ravel()
    out.filepath_raw = str(path)
    out.file_format = "PNG"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    out.save()
    bpy.data.images.remove(out)
    return path


def preview(ts, objects, pattern, out_png, view_px=320):
    """Render the model beside its tiles (common.render_preview)."""
    import tempfile
    ref = Path(tempfile.mkdtemp()) / "pattern.png"
    pattern_png(ts, pattern, ref)
    return common.render_preview(objects, out_png, ref, size=(TILE_W * len(pattern[0]), TILE_H * len(pattern)), view_px=view_px)


def preview_arg():
    """The folder for previews: `-- --preview <dir>`, or the folder of `--preview <file>.png` as
    tools/build-models.sh passes it (a tile script exports several models)."""
    import sys
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--preview" not in argv:
        return None
    path = Path(argv[argv.index("--preview") + 1])
    return path.parent if path.suffix == ".png" else path


# --- Tile surfaces -------------------------------------------------------------------------------

class Snapper:
    """Few materials per model: a tile's pixels snap to its `limit` most common palette indices
    (nearest colour), so one model draws in a handful of calls."""

    def __init__(self, ts, indices, limit=5):
        vals = [int(v) for v in np.asarray(indices).ravel() if v >= 0]
        counts = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        self.ts = ts
        self.keep = [v for v, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]
        self.cache = {}

    def __call__(self, index):
        index = int(index)
        if index not in self.cache:
            r, g, b = self.ts.rgb(index)
            self.cache[index] = min(self.keep, key=lambda k: sum((a - c) ** 2 for a, c in zip(self.ts.rgb(k), (r, g, b))))
        return self.cache[index]


def lum_of(ts, grid):
    return np.where(grid >= 0, ts.lum[np.maximum(grid, 0)], 0.0)


def context(ts, n):
    """Tile n between its most common neighbours on each side (corners empty), as a 3x3 pattern."""
    nb = ts.tiles[n]["neighbours"]
    side = lambda k: nb[k][0]["tile"] if nb[k] else -1  # noqa: E731
    valid = lambda t: t if t in ts.tiles else -1  # noqa: E731
    return [[-1, valid(side("up")), -1], [valid(side("left")), n, valid(side("right"))], [-1, valid(side("down")), -1]]


def snap_shade(index, chosen, spread=2):
    """A stone's colour snaps to an already chosen shade of the same ramp (palette indices come in
    ramps of 16) within `spread` shades; otherwise it's added to `chosen`."""
    for c in chosen:
        if c >> 4 == index >> 4 and abs(c - index) <= spread:
            return c
    chosen.append(index)
    return index


def boulders(ts, n, pal, bm, keep=None, z0=-0.03, max_height=0.2, sigma=2.2, gap=0.22, sides=10, squash=0.2,
             chosen=None, min_pixels=8, quantile=0.5, shrink=1.0, shape="dome"):
    """A rounded boulder for each stone painted on tile n (2x pixels; a stone is a hill of
    brightness, lt.hills), sized, turned and coloured like its pixels. Stones are found with the
    tile between its usual neighbours, built whole and cut at the tile's edges, so one crossing
    an edge continues on the next tile. `keep(ys, xs)` (2x pixel coordinates in the tile, may be
    outside it) can drop stones, e.g. where a hand-built part covers the art."""
    ctx = context(ts, n)
    grid = ts.grid(ctx, 2)
    lum = lum_of(ts, grid)
    frame = Frame(ctx, scale=2)
    oy, ox = TILE_H * 2, TILE_W * 2
    chosen = [] if chosen is None else chosen
    sb = bmesh.new()
    for ys, xs in hills(lum, grid >= 0, sigma=sigma, floor=gap):
        if len(ys) < min_pixels:
            continue
        inside = (ys >= oy) & (ys < oy + TILE_H * 2) & (xs >= ox) & (xs < ox + TILE_W * 2)
        if not inside.any() or (keep and not keep(ys - oy, xs - ox)):
            continue
        cx, cy, rx, ry, ang = ellipse(ys, xs)
        rx, ry = (rx + 0.6) * shrink / 24, (ry + 0.6) * shrink / 24
        height = min(max_height, 0.55 * min(rx, ry) + 0.02)
        colour = snap_shade(dominant(grid[ys, xs], ts.lum, quantile=quantile), chosen)
        if shape == "block":
            block(sb, frame.x(cx), frame.y(cy), rx, ry, -ang, z0, height, pal(colour), sides=sides)
        else:
            dome(sb, frame.x(cx), frame.y(cy), rx, ry, -ang, z0, height, pal(colour), sides=sides, rings=3, squash=squash)
    cut_to_tile(sb)
    # Move the stones into `bm` (bmesh has no direct join; go through a temporary mesh).
    tmp = bpy.data.meshes.new("tmp_stones")
    sb.to_mesh(tmp)
    sb.free()
    bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


def cut_to_tile(bm, cols=1, rows=1):
    """Remove everything outside the pattern's bounds (cols x rows tiles around the origin)."""
    from mathutils import Vector
    hw, hh = TILE_W * cols / 2 * PX, TILE_H * rows / 2 * PX
    for co, no in (((hw, 0, 0), (1, 0, 0)), ((-hw, 0, 0), (-1, 0, 0)), ((0, hh, 0), (0, 1, 0)), ((0, -hh, 0), (0, -1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(co), plane_no=Vector(no), clear_outer=True)


def relief_heights(ts, grid, amp, sigma=1.2, lo=None, hi=None):
    """Heights for a carved or embossed surface: the smoothed brightness of each 2x pixel, scaled
    from 0 (darkest, or `lo`) to `amp` (brightest, or `hi`)."""
    lum = lum_of(ts, grid)
    sm = blur(np.where(grid >= 0, lum, lum[grid >= 0].mean() if (grid >= 0).any() else 0), sigma)
    lo = sm[grid >= 0].min() if lo is None else lo
    hi = sm[grid >= 0].max() if hi is None else hi
    return np.clip((sm - lo) / max(1e-6, hi - lo), 0, 1) * amp


# --- Island rock ---------------------------------------------------------------------------------
#
# The floating islands of background 3 (shapesz.dat tiles 120-152: TYRIAN and eight other levels) are
# cobbles painted to tile seamlessly. Every rock tile model, and the rock round the structures built
# on the islands (lib_tyrbld.Structure.rock), draws the tile's own 2x pixels as a relief, so that
# whatever tiles meet, the colours meet as the art does and the heights nearly so:
# - colour: each pixel snaps to the nearest of ROCK_COLOURS, one shared set (not chosen per tile, so
#   the same stone keeps its colour across a seam);
# - height: the pixel's brightness, smoothed a little and mapped by the fixed ROCK_LUM range (not
#   normalised per tile) to 0..ROCK_RELIEF: stones up, the dark between them down, the island's
#   edge rounded off. The smoothing sees the tile between its usual neighbours (context()); at the
#   tile's edge a vertex takes the tile's own pixels only, and the slab's side walls close what
#   little step is left against a neighbour;
# - the underside tiles (140-142) hang a face toward the camera from where their stones end, with
#   the roots painted on it.

#: The palette indices the island rock is drawn in: the grey ramp, the tan and brass stones.
ROCK_COLOURS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 24, 25, 27, 28, 163, 165, 167, 169, 171)
ROCK_DARK = 3  # the slab's sides and bottom
ROCK_RELIEF = 0.12  # units: how far a stone's top stands over the dark between stones
ROCK_LUM = (0.16, 0.62)  # smoothed brightness at height 0 and at ROCK_RELIEF
ROCK_SIGMA = 1.1  # the smoothing, 2x px
ROCK_BOTTOM = -0.3
ROCK_MERGE_DEG = 4.0  # nearly flat neighbouring faces of one colour merge (a third fewer triangles)
ROCK_UNDERSIDE = {140: 0.55, 141: 0.55, 142: 0.55}  # tile: how far its face hangs below the slab


class RockColours:
    """Snap a palette index to the nearest of ROCK_COLOURS (by RGB)."""

    def __init__(self, ts):
        self.ts = ts
        self.keep = [k for k in ROCK_COLOURS if k in ts.colors]
        self.cache = {}

    def __call__(self, index):
        index = int(index)
        if index not in self.cache:
            rgb = self.ts.rgb(index)
            self.cache[index] = min(self.keep, key=lambda k: sum((a - b) ** 2 for a, b in zip(self.ts.rgb(k), rgb)))
        return self.cache[index]


def rock_heights(ts, grid2):
    """The relief of `grid2` (2x px, -1 = nothing): smoothed brightness mapped by ROCK_LUM."""
    lum = lum_of(ts, grid2)
    sm = blur(lum, ROCK_SIGMA)
    lo, hi = ROCK_LUM
    return np.clip((sm - lo) / (hi - lo), 0, 1) * ROCK_RELIEF


def underside_drop(own, lum, drop):
    """The hanging face of an underside tile (2x px): 0 where its stones are, falling to -drop at the
    bottom from the row in each column where they end."""
    h, w = own.shape
    opaque = own >= 0
    start = np.full(w, h * 0.3)
    for x in range(w):
        col = np.nonzero(opaque[:, x] & (lum[:, x] > 0.22))[0]
        col = col[col < h * 0.55]
        if len(col):
            start[x] = col.max() + 1
    out = np.zeros((h, w))
    for y in range(h):
        out[y, :] = -drop * np.clip((y - start) / max(1.0, h - start.min()), 0, 1) ** 0.8
    return out


def rock_tile(ts, n, pal, region=None, flat=None, bottom=ROCK_BOTTOM, plain=False):
    """The island rock of tile n as a bmesh, centred on the tile (Frame([[n]], 2)): a slab from
    `bottom` up to its relief (module notes above). `region` (bool, the tile's 2x px) limits it
    to those of its painted pixels; `flat` pixels (where a structure's own parts stand) are level at
    z = 0 and dark. `plain` marks the materials so a structure's bake leaves them alone."""
    ctx = context(ts, n)
    grid = ts.grid(ctx, 2)
    th, tw = TILE_H * 2, TILE_W * 2
    own = grid[th:2 * th, tw:2 * tw]
    opaque = own >= 0
    region = opaque if region is None else region & opaque
    if not region.any():
        return None
    heights = rock_heights(ts, grid)[th:2 * th, tw:2 * tw]
    if n in ROCK_UNDERSIDE:
        drop = underside_drop(own, lum_of(ts, own), ROCK_UNDERSIDE[n])
        # The relief fades out as the face starts to hang, so the two join smoothly.
        heights = heights * (1 - np.clip(-drop / 0.08, 0, 1)) + drop
    flat = np.zeros_like(region) if flat is None else flat & region
    heights = np.where(flat, 0.0, heights)
    snap = RockColours(ts)
    kw = {"plain": True} if plain else {}
    dark = pal(ROCK_DARK, **kw)
    bm = bmesh.new()
    lt_mats = lambda x, y: dark if flat[y, x] else pal(snap(own[y, x]), **kw)  # noqa: E731
    mask_slab(bm, region, Frame([[n]], scale=2), bottom + min(0.0, heights.min()), 0.0, lt_mats, dark,
              top_height=heights, smooth_top=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(ROCK_MERGE_DEG), verts=bm.verts, edges=bm.edges, delimit={"MATERIAL"})
    return bm


# --- Island rock round an enemy's machine (DECISIONS.md D66) --------------------------------------
#
# Some of TYRIAN's enemies that sit on the islands (the purple octagon walls, the eye fortress, the
# red machinery, the star core panel) fill their whole sprite: the machine, and round it island rock
# painted to blend with the tiles beneath. Their models build that rock as the islands do (rock_tile:
# the pixels as a relief in ROCK_COLOURS, heights by ROCK_LUM, flat shaded, the per-tile models'
# finish) and leave it out of the outline shell: there is no slab with walls, no boulders and no
# outline round the sprite's rectangle, so the rock reads as the island going on under the machine.
# The enemy is drawn about 0.4 units above the islands (top enemies at 2.5, background 3 at 2.1, D5)
# and placed on the camera ray through its screen point (D6), so the rock lands on screen exactly
# where the sprite's rock is drawn; it casts no shadow (`tyrian_ground`, the renderer's isGroundPart),
# which would otherwise lay a dark band along two of its edges on the island below.

#: Palette ramps (index >> 4) the islands' rock is painted in: greys, brass, tan (ROCK_COLOURS).
ROCK_RAMPS = (0, 1, 10)
#: The per-tile rock models' finish (shapesz_bg3.py's palette).
ROCK_FINISH = {"roughness": 0.55, "metallic": 0.05}
#: How far the rock's edge walls go below its dark gaps (units): a sliver, in the stones' colours.
SPRITE_ROCK_SKIRT = 0.03


class SpritePalette:
    """A Tileset-like palette for a sprite: `colors`, `lum` and `rgb(index)` (RockColours, lum_of,
    Palette) from the level palette's colours, {index: (r, g, b)}."""

    def __init__(self, colors):
        self.colors = {int(k): tuple(v) for k, v in colors.items()}
        self.lum = np.zeros(256)
        for i, (r, g, b) in self.colors.items():
            self.lum[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    def rgb(self, index):
        return self.colors[int(index)]


def island_palette(root, extra=None):
    """The level palette as the island tiles have it (reference/tiles/shapesz), plus `extra` colours
    (a sprite's), as a SpritePalette."""
    colors = dict(Tileset(root, "shapesz", layer=2).colors)
    colors.update({int(k): tuple(v) for k, v in (extra or {}).items()})
    return SpritePalette(colors)


def mmpx2x(pix, luma):
    """MMPX 2x on palette indices, edges clamped: a copy of tools/terrain_hd.py's (the port of
    src/render/remaster/mmpx.ts that made the tiles' `pixels2x`), which needs PIL and so can't be
    imported in Blender. Sprites have no 2x pixels of their own; this gives them the tiles' look."""
    h, w = pix.shape
    P = np.pad(pix.astype(np.int32), 3, mode="edge")

    def s(dx, dy):
        return P[3 + dy:3 + dy + h, 3 + dx:3 + dx + w]

    A, B, C = s(-1, -1), s(0, -1), s(1, -1)
    D, E, F = s(-1, 0), s(0, 0), s(1, 0)
    G, H, I = s(-1, 1), s(0, 1), s(1, 1)
    Pp, S, Q, R = s(0, -2), s(0, 2), s(-2, 0), s(2, 0)
    Bl, Dl, El, Fl, Hl = luma[B], luma[D], luma[E], luma[F], luma[H]
    J, K, L, M = E.copy(), E.copy(), E.copy(), E.copy()
    act = (A != E) | (B != E) | (C != E) | (D != E) | (F != E) | (G != E) | (H != E) | (I != E)

    def any3(b, a0, a1, a2):
        return (b == a0) | (b == a1) | (b == a2)

    def all2(b, a0, a1):
        return (b == a0) & (b == a1)

    def all3(b, a0, a1, a2):
        return (b == a0) & (b == a1) & (b == a2)

    def all4(b, a0, a1, a2, a3):
        return (b == a0) & (b == a1) & (b == a2) & (b == a3)

    def none2(b, a0, a1):
        return (b != a0) & (b != a1)

    def none4(b, a0, a1, a2, a3):
        return (b != a0) & (b != a1) & (b != a2) & (b != a3)

    def put(cond, *pairs):
        c = act & cond
        for dst, src in pairs:
            dst[c] = src[c] if isinstance(src, np.ndarray) else src

    put((D == B) & (D != H) & (D != F) & ((El >= Dl) | (E == A)) & any3(E, A, C, G) & ((El < Dl) | (A != D) | (E != Pp) | (E != Q)), (J, D))
    put((B == F) & (B != D) & (B != H) & ((El >= Bl) | (E == C)) & any3(E, A, C, I) & ((El < Bl) | (C != B) | (E != Pp) | (E != R)), (K, B))
    put((H == D) & (H != F) & (H != B) & ((El >= Hl) | (E == G)) & any3(E, A, G, I) & ((El < Hl) | (G != H) | (E != S) | (E != Q)), (L, H))
    put((F == H) & (F != B) & (F != D) & ((El >= Fl) | (E == I)) & any3(E, C, G, I) & ((El < Fl) | (I != H) | (E != R) | (E != S)), (M, F))

    put((E != F) & all4(E, C, I, D, Q) & all2(F, B, H) & (F != s(3, 0)), (K, F), (M, F))
    put((E != D) & all4(E, A, G, F, R) & all2(D, B, H) & (D != s(-3, 0)), (J, D), (L, D))
    put((E != H) & all4(E, G, I, B, Pp) & all2(H, D, F) & (H != s(0, 3)), (L, H), (M, H))
    put((E != B) & all4(E, A, C, H, S) & all2(B, D, F) & (B != s(0, -3)), (J, B), (K, B))

    put((Bl < El) & all4(E, G, H, I, S) & none4(E, A, D, C, F), (J, B), (K, B))
    put((Hl < El) & all4(E, A, B, C, Pp) & none4(E, D, G, I, F), (L, H), (M, H))
    put((Fl < El) & all4(E, A, D, G, Q) & none4(E, B, C, I, H), (K, F), (M, F))
    put((Dl < El) & all4(E, C, F, I, R) & none4(E, B, A, G, H), (J, D), (L, D))

    hb = H != B
    h1 = hb & (H != A) & (H != E) & (H != C)
    put(h1 & all3(H, G, F, R) & none2(H, D, s(2, -1)), (L, M))
    put(h1 & all3(H, I, D, Q) & none2(H, F, s(-2, -1)), (M, L))
    b1 = hb & (B != I) & (B != G) & (B != E)
    put(b1 & all3(B, A, F, R) & none2(B, D, s(2, 1)), (J, K))
    put(b1 & all3(B, C, D, Q) & none2(B, F, s(-2, 1)), (K, J))
    fd = F != D
    d1 = fd & (D != I) & (D != E) & (D != C)
    put(d1 & all3(D, A, H, S) & none2(D, B, s(1, 2)), (J, L))
    put(d1 & all3(D, G, B, Pp) & none2(D, H, s(1, -2)), (L, J))
    f1 = fd & (F != E) & (F != A) & (F != G)
    put(f1 & all3(F, C, H, S) & none2(F, B, s(-1, 2)), (K, M))
    put(f1 & all3(F, I, B, Pp) & none2(F, H, s(-1, -2)), (M, K))

    out = np.empty((h * 2, w * 2), np.int32)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = J, K, L, M
    return out.astype(pix.dtype)


class GridFrame:
    """Pixel coordinates of a w x h px grid at `scale` to model units, origin at the grid's centre
    (Frame, for a sprite or assembly instead of a tile pattern)."""

    def __init__(self, w, h, scale=1):
        self.w, self.h, self.unit = w * scale, h * scale, PX / scale

    def x(self, px):
        return (px - self.w / 2) * self.unit

    def y(self, py):
        return (self.h / 2 - py) * self.unit


def machine_footprint(objects, w, h, ground=0.0, eps=0.012, scale=2):
    """Where `objects` (built in units round the w x h px grid's centre, X right, Y screen up) stand
    above `ground` + eps, seen from straight above: bool (h * scale, w * scale), one cell per
    `scale`x pixel."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, deps) for o in objects]
    frame = GridFrame(w, h, scale)
    out = np.zeros((h * scale, w * scale), bool)
    down = Vector((0, 0, -1))
    for y in range(h * scale):
        for x in range(w * scale):
            origin = Vector((frame.x(x + 0.5), frame.y(y + 0.5), 50.0))
            for t in trees:
                loc, *_ = t.ray_cast(origin, down)
                if loc is not None and loc.z > ground + eps:
                    out[y, x] = True
                    break
    return out


def is_rock_index(index):
    """Whether a sprite pixel is painted in the islands' rock colours (ROCK_RAMPS)."""
    return index >= 0 and (int(index) >> 4) in ROCK_RAMPS


def sprite_rock(pal, grid, machine, layout, coll, tag, ground=0.0, piece=(24, 28), name_fmt="{}_rock"):
    """The island rock of an enemy's sprite (module notes above): one object per piece of `layout`.

    `pal`: the level palette (island_palette). `grid`: the sprite's pixels at 1x, an (h, w) array of
    palette indices (-1 transparent), the whole assembly for a multi-piece enemy. `machine`: bool
    (2h, 2w), where the machine stands (machine_footprint): the rock there is level at `ground` and
    dark, under the machine. Elsewhere every painted pixel is relief: in the rock's ramps it takes
    the nearest of ROCK_COLOURS, as the island tiles do; any other colour (a blue stone, a sliver of
    the machine's paint where its model doesn't quite reach) keeps its own index. `layout`: [(piece name, cx, cy)], each piece's centre in px from the grid's centre (as
    common.split_assembly); `piece`: its (w, h) in px. Each object's origin is its piece's centre;
    its heights come from the whole grid, so the pieces meet exactly. Materials: pal_<i>_<tag>,
    the per-tile models' finish. Returns {piece name: object}."""
    grid = np.asarray(grid, dtype=np.int32)
    h, w = grid.shape
    g2 = mmpx2x(grid, np.append(pal.lum, 0.0))  # index -1 reads the appended 0 luma
    opaque = g2 >= 0
    support = opaque | machine
    flat = machine
    rocky = np.vectorize(is_rock_index)(g2)
    heights = np.where(flat, 0.0, rock_heights(pal, g2))
    snap = RockColours(pal)
    frame = GridFrame(w, h, 2)
    out = {}
    for name, cx, cy in layout:
        x0, y0 = int(round((w / 2 + cx - piece[0] / 2) * 2)), int(round((h / 2 + cy - piece[1] / 2) * 2))
        region = np.zeros_like(support)
        region[max(0, y0):y0 + piece[1] * 2, max(0, x0):x0 + piece[0] * 2] = True
        region &= support
        if not region.any():
            continue
        p = Palette(pal, tag, plain=True, **ROCK_FINISH)
        dark = p(ROCK_DARK)
        mats = lambda x, y: dark if flat[y, x] else p(snap(g2[y, x]) if rocky[y, x] else g2[y, x])  # noqa: E731
        bm = bmesh.new()
        mask_slab(bm, region, frame, ground - SPRITE_ROCK_SKIRT, ground, mats, mats, dark,
                  top_height=heights, smooth_top=True, support=support)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(ROCK_MERGE_DEG), verts=bm.verts, edges=bm.edges,
                                 delimit={"MATERIAL"})
        bmesh.ops.translate(bm, vec=(-cx * PX, cy * PX, 0), verts=bm.verts)
        obj = mesh(name_fmt.format(name), bm, p, coll, smooth=False)
        obj["tyrian_ground"] = True
        out[name] = obj
    return out


def sprite_grid(root, layout, w, h, frame=0, piece=(24, 28)):
    """The pixels (palette indices, -1 transparent) of `layout`'s pieces ([(model, cx, cy)], centres
    in px from the grid's centre, as sprite_rock) as one (h, w) array, each piece's `frame`-th frame,
    and the colours of all of them."""
    grid = np.full((h, w), -1, dtype=np.int32)
    colors = {}
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        colors.update(data["colors"])
        px = np.array(data["frames"][min(frame, len(data["frames"]) - 1)]["pixels"], dtype=np.int32)
        x0, y0 = int(round(w / 2 + cx - piece[0] / 2)), int(round(h / 2 + cy - piece[1] / 2))
        grid[y0:y0 + px.shape[0], x0:x0 + px.shape[1]] = np.where(px >= 0, px, grid[y0:y0 + px.shape[0], x0:x0 + px.shape[1]])
    return grid, colors


def build_sprite_rock(root, machine_objects, layout, w, h, coll, tag, ground=0.0, piece=(24, 28), grid=None):
    """sprite_rock for an enemy built round the w x h px grid's centre: the pieces' pixels
    (sprite_grid, or `grid`), the machine's footprint from `machine_objects` (machine_footprint)
    and the island palette. Returns {piece name: rock object}."""
    pix, colors = sprite_grid(root, layout, w, h, piece=piece)
    if grid is not None:
        pix = np.asarray(grid, dtype=np.int32)
    pal = island_palette(root, colors)
    machine = machine_footprint(machine_objects, w, h, ground=ground)
    return sprite_rock(pal, pix, machine, layout, coll, tag, ground=ground, piece=piece)
