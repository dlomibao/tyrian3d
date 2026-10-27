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
            color = common.srgb(*self.ts.rgb(index))
            mat = common.material(name, color, emission=color if emission else None, emission_strength=emission, **opts)
            self.slots[key] = len(self.materials)
            self.materials.append(mat)
        return self.slots[key]


# --- Geometry ------------------------------------------------------------------------------------

def mask_slab(bm, mask, frame, z_bottom, z_top, mat_top, mat_side=None, mat_bottom=None, top_height=None):
    """A slab with the outline of `mask` (bool array in `frame` pixels) from z_bottom to z_top.

    `top_height`, an array like mask, raises each top cell by that much (a relief); side walls
    follow it. Coplanar top faces of one material are merged afterwards (dissolve_coplanar)."""
    mat_side = mat_top if mat_side is None else mat_side
    mat_bottom = mat_side if mat_bottom is None else mat_bottom
    h, w = mask.shape
    top_v, bot_v = {}, {}

    def corner_z(cx, cy):
        if top_height is None:
            return z_top
        vals = [top_height[y, x] for y in (cy - 1, cy) for x in (cx - 1, cx) if 0 <= y < h and 0 <= x < w and mask[y, x]]
        return z_top + (max(vals) if vals else 0.0)

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
    for y in range(h):
        for x in range(w):
            if not mask[y, x]:
                continue
            # Counter-clockwise seen from above (+Z): screen y grows downward, Blender Y upward.
            bm.faces.new((vt(x, y + 1), vt(x + 1, y + 1), vt(x + 1, y), vt(x, y))).material_index = mats(x, y)
            bm.faces.new((vb(x, y), vb(x + 1, y), vb(x + 1, y + 1), vb(x, y + 1))).material_index = mat_bottom
            for (dx, dy), (a, b) in (((0, -1), ((x, y), (x + 1, y))), ((1, 0), ((x + 1, y), (x + 1, y + 1))),
                                     ((0, 1), ((x + 1, y + 1), (x, y + 1))), ((-1, 0), ((x, y + 1), (x, y)))):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and mask[ny, nx]:
                    continue
                bm.faces.new((vb(*a), vb(*b), vt(*b), vt(*a))).material_index = mat_side


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
             chosen=None, min_pixels=8, quantile=0.5, shrink=1.0):
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
