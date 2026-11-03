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
import lib_rock_hd as rh

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

    def add(self, mat):
        """The slot of a material that isn't a palette colour (the HD rock's, rock_material)."""
        key = ("material", mat.name)
        if key not in self.slots:
            self.slots[key] = len(self.materials)
            self.materials.append(mat)
        return self.slots[key]


# --- Geometry ------------------------------------------------------------------------------------

def mask_slab(bm, mask, frame, z_bottom, z_top, mat_top, mat_side=None, mat_bottom=None, top_height=None, smooth_top=False,
              support=None, walls=None):
    """A slab with the outline of `mask` (bool array in `frame` pixels) from z_bottom to z_top.

    `top_height`, an array like mask, raises each top cell by that much (a relief); side walls
    follow it. With `smooth_top` a corner takes the mean of its cells' heights (else the highest)
    and the top is smooth shaded, for carved surfaces; the sides stay flat. Coplanar top faces of
    one material can be merged afterwards (dissolve_coplanar). `mat_top` and `mat_side` are a
    material slot or a function (x, y) -> slot of the cell (for a side, the cell it closes).
    `support` (bool, like mask; default mask) is the cells a corner's height comes from: a piece
    cut from a bigger relief passes the whole relief's cells, so pieces built apart meet exactly.
    `walls` (bool, like mask; default mask): a side wall is built only where the next cell is outside
    it, so pieces cut from one surface have no walls where they meet."""
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
                if 0 <= nx < w and 0 <= ny < h and (mask if walls is None else walls)[ny, nx]:
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
    # The island rock's textures (rock_material; the only images in a tile model) are packed lossless
    # WebP, which "AUTO" keeps.
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
# cobbles painted to tile. Every rock tile model, the rock round the structures built on the islands
# (lib_tyrbld.Structure.rock) and the rock round some enemies' machines (sprite_rock) are drawn the
# same way (DECISIONS.md D63, D66, D75):
# - colour: an HD texture made from the art by lib_rock_hd (the stones found in the pixels and
#   redrawn as smooth cushions with a soft mortar line, at rh.TEX texels per pixel), which the game
#   colours from the live palette (src/render/rockMaterial.ts): one material per tile, shared by
#   every tile and structure, so the same stone keeps its colour across a seam and fades, the hit
#   flash and the smoothies apply;
# - relief: the texture's height, as the game's bump (the stones' cushions and bevels, the mortar).
#   The top is level: geometry can't follow a tile's edge bands, and any relief there would differ
#   from the neighbour's, a crease along every seam. The island's outline is the tile's 2x pixels
#   with its stair steps rounded off (smooth_outline), its sides closed down to the slab's bottom;
# - seams: each tile's texture is made among its usual neighbours on TYRIAN's map and its edges
#   solved against every tile the map puts next to it, and for every pair the map has, both tiles get
#   an edge band computed together, which the game draws for the neighbour actually there
#   (lib_rock_hd.island_tiles, rockMaterial.ts);
# - the underside tiles (140-142) hang a face toward the camera from where their stones end, with
#   the roots painted on it.

#: The island rock tiles of shapesz.dat (shapesz_bg3.py, recipe "rock").
ROCK_TILES = (120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 140, 141, 142, 150, 151, 152)
#: The palette indices the original island rock is drawn in: the grey ramp, the tan and brass stones.
#: The HD rock keeps any shade of their ramps (lib_rock_hd.RAMPS) and snaps other paint to these.
ROCK_COLOURS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 24, 25, 27, 28, 163, 165, 167, 169, 171)
ROCK_BOTTOM = -0.3
ROCK_MERGE_DEG = 2.0  # nearly flat neighbouring faces merge
ROCK_UNDERSIDE = {140: 0.55, 141: 0.55, 142: 0.55}  # tile: how far its face hangs below the slab
ROCK_UNDER_SHADE = 2.5  # the shade of the rock under a structure's or enemy's own parts
ROCK_OUTLINE_SIGMA = 0.9  # 2x px: the outline's stair steps are rounded to this smooth curve
#: The rock's finish (shapesz_bg3.py's palette).
ROCK_FINISH = {"roughness": 0.55, "metallic": 0.05}


_ISLAND = {}


def island_hd(ts):
    """The HD rock textures' channels of every island tile, {n: lib_rock_hd.compose dict}: made once
    per tileset (and cached on disk by lib_rock_hd)."""
    if ts.name not in _ISLAND:
        # The rock tiles and every tile TYRIAN's islands carry (the structures' cells build their
        # rock from their own tile's pixels, Structure.rock), solved together at their seams.
        on_map = {int(n) for n in np.unique(rh.level_map(ts.root, "1-9", 2)) if n >= 0}
        tiles = sorted((set(ROCK_TILES) | on_map) & set(ts.tiles))
        _ISLAND[ts.name] = rh.island_tiles(ts.root, tiles, {n: t["px"] for n, t in ts.tiles.items()}, ts.colors,
                                           [k for k in ROCK_COLOURS if k in ts.colors], band_tiles=tiles)
    return _ISLAND[ts.name]


def _data_image(name, rgb, alpha=None):
    """A packed, non-colour, lossless WebP image from (H, W, 3) uint8, row 0 at the top; `alpha`
    (H, W, 0..1) makes it RGBA. The glTF export embeds a packed WebP as it is, whatever its image
    format (the structures' bake and the enemies export lossy WebP, which would smear this data:
    its height lives in the colour channels a lossy encoder halves)."""
    import tempfile
    h, w = rgb.shape[:2]
    tmp = bpy.data.images.new(f"{name}-tmp", w, h, alpha=alpha is not None)
    tmp.colorspace_settings.name = "Non-Color"
    a = np.ones((h, w, 1), np.float32) if alpha is None else np.round(np.clip(alpha, 0, 1) * 255)[..., None] / 255.0
    px = np.concatenate([rgb.astype(np.float32) / 255.0, a.astype(np.float32)], -1)[::-1]
    tmp.pixels.foreach_set(px.ravel())
    path = str(Path(tempfile.mkdtemp(prefix="rock_hd_")) / f"{name}.webp")
    tmp.filepath_raw = path
    tmp.file_format = "WEBP"
    tmp.save(quality=100)  # 100: lossless
    bpy.data.images.remove(tmp)
    img = bpy.data.images.load(path)
    img.name = name
    img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "STRAIGHT" if alpha is not None else "NONE"
    img.pack()
    return img


def rock_material(name, ch, ramps=rh.RAMPS, bands=None, alpha=None):
    """The HD rock material `name` with its texture from `ch` (lib_rock_hd.compose): R the shade,
    G the ramp code, B the height (the game's bump), sampled on the "rock" UV map. Marked
    `tyrian_rock_ramps` (the palette ramps the G code steps through; the game draws it with
    src/render/rockMaterial.ts) and `tyrian_plain` (texture_bake.py leaves it alone). With `bands`
    (lib_rock_hd.island_tiles: the tile's edge band for each neighbour the map gives it) they go in a
    second texture (lib_rock_hd.band_texture, on the emission slot, which the game reads as data),
    their keys in `tyrian_rock_bands`, row by row, BAND_DEPTH rows each. `alpha` (the texture's size,
    0..1): the rock's coverage, in the texture's alpha; the game draws it translucent by it
    (`tyrian_rock_fade`: an enemy's rock fading into the island under it)."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    img = _data_image(f"{name}-tex", rh.texture_rgb(ch), alpha)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = ROCK_FINISH["roughness"]
    bsdf.inputs["Metallic"].default_value = ROCK_FINISH["metallic"]
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "rock"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat["tyrian_rock_ramps"] = [int(r) for r in ramps]
    mat["tyrian_plain"] = True
    if alpha is not None:
        mat["tyrian_rock_fade"] = True
    if bands:
        keys, rgb = rh.band_texture(bands)
        btex = nt.nodes.new("ShaderNodeTexImage")
        btex.image = _data_image(f"{name}-bands", rgb)
        btex.interpolation = "Linear"
        btex.extension = "EXTEND"
        nt.links.new(btex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
        mat["tyrian_rock_bands"] = list(keys)
        mat["tyrian_rock_band_depth"] = rh.BAND_DEPTH
        mat["tyrian_rock_band_fade"] = rh.BAND_FADE
    # In Blender the texture's raw data is no colour; show a mid grey in the viewport.
    mat.diffuse_color = (0.4, 0.4, 0.4, 1.0)
    return mat


def rock_uvs(bm, frame):
    """A "rock" UV map: every vertex's place in `frame` (top view), which the texture covers."""
    layer = bm.loops.layers.uv.get("rock") or bm.loops.layers.uv.new("rock")
    for f in bm.faces:
        for loop in f.loops:
            co = loop.vert.co
            px = co.x / frame.unit + frame.w / 2
            py = frame.h / 2 - co.y / frame.unit
            loop[layer].uv = (px / frame.w, 1 - py / frame.h)


def darken(ch, flat, shade=ROCK_UNDER_SHADE):
    """The texture channels `ch` with the rock under a part (`flat`, 2x cells) dark and level: its
    shade at most `shade`, grey, no bump, the edge soft (no pixel steps round the part's feet)."""
    k = rh.TEX // 2
    w = rh.smoothstep(0.25, 0.75, rh.blur(rh.nearest(flat.astype(float), k), 0.3 * rh.TEX))
    out = dict(ch)
    out["shade"] = ch["shade"] * (1 - w) + np.minimum(ch["shade"], shade) * w
    out["code"] = ch["code"] * (1 - w)
    out["height"] = ch["height"] * (1 - w)
    return out


def darken_band(band, key, flat, shade=ROCK_UNDER_SHADE):
    """An edge band (lib_rock_hd.pair_bands, "<side>:<tile>") darkened as darken() darkens its tile."""
    k = rh.TEX // 2
    w = rh.smoothstep(0.25, 0.75, rh.blur(rh.nearest(flat.astype(float), k), 0.3 * rh.TEX))
    d = rh.BAND_DEPTH
    side = key.split(":")[0]
    strip = {"left": w[:, :d].T, "right": w[:, ::-1][:, :d].T, "up": w[:d], "down": w[::-1][:d]}[side]
    out = dict(band)
    out["shade"] = band["shade"] * (1 - strip) + np.minimum(band["shade"], shade) * strip
    out["code"] = band["code"] * (1 - strip)
    out["height"] = band["height"] * (1 - strip)
    return out


def smooth_outline(bm, mask, frame, sigma=ROCK_OUTLINE_SIGMA, fixed_border=True):
    """Round the stair steps of a mask_slab's outline: every vertex on the outline (a corner with
    some of its cells in `mask` and some not) moves onto the 0.5 level of the mask blurred by
    `sigma` cells, at most 0.6 cells. Corners on the array's border stay, so tiles still meet."""
    h, w = mask.shape
    m = rh.blur(mask.astype(float), sigma)
    mp = np.pad(m, 1, mode="edge")
    inside = np.pad(mask, 1, constant_values=False)
    moves = {}
    for cy in range(1 if fixed_border else 0, h if fixed_border else h + 1):
        for cx in range(1 if fixed_border else 0, w if fixed_border else w + 1):
            cells = inside[cy:cy + 2, cx:cx + 2]
            if cells.all() or not cells.any():
                continue
            # The blurred mask at the corner and its gradient (cells: rows cy-1, cy; cols cx-1, cx).
            q = mp[cy:cy + 2, cx:cx + 2]
            v = q.mean()
            gx = (q[:, 1] - q[:, 0]).mean()
            gy = (q[1] - q[0]).mean()
            g2 = gx * gx + gy * gy
            if g2 < 1e-6:
                continue
            t = (0.5 - v) / g2
            dx, dy = np.clip(t * gx, -0.6, 0.6), np.clip(t * gy, -0.6, 0.6)
            moves[(round(frame.x(cx), 5), round(frame.y(cy), 5))] = (dx * frame.unit, -dy * frame.unit)
    for v in bm.verts:
        mv = moves.get((round(v.co.x, 5), round(v.co.y, 5)))
        if mv:
            v.co.x += mv[0]
            v.co.y += mv[1]


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


def rock_tile(ts, n, pal, region=None, flat=None, bottom=ROCK_BOTTOM, plain=False, cell=None):
    """The island rock of tile n as a bmesh, centred on the tile (Frame([[n]], 2)): a slab from
    `bottom` up to its level top (module notes above), in the tile's HD rock material with its edge
    bands (rock_t<n>, the same in every per-tile model). `region` (bool, the tile's 2x px) limits it
    to those of its painted pixels; `flat` pixels (where a structure's own parts stand) are level at
    z = 0 and dark, with a soft edge (darken). `cell` (row, col): a structure's cell, which gets a
    material of its own (`tyrian_rock_cell`), so the game can give each cell the bands of its own
    neighbours on the map. `plain` is kept for the callers (the rock is always plain)."""
    own = ts.grid([[n]], 2)
    opaque = own >= 0
    region = opaque if region is None else region & opaque
    if not region.any():
        return None
    ch = island_hd(ts)[n]
    heights = np.zeros(own.shape)
    if n in ROCK_UNDERSIDE:
        heights = underside_drop(own, lum_of(ts, own), ROCK_UNDERSIDE[n])
    flat = np.zeros_like(region) if flat is None else flat & region
    heights = np.where(flat, 0.0, heights)
    name, tex = f"rock_t{n}", ch
    if flat.any():
        # Under a structure's own parts: dark (the tile's texture and bands with that patch).
        import hashlib
        name += "_" + hashlib.sha1(np.packbits(flat).tobytes()).hexdigest()[:8]
        tex = darken(ch, flat)
        tex["bands"] = {k: darken_band(b, k, flat) for k, b in ch.get("bands", {}).items()}
    if cell is not None:
        name += f"_{cell[0]}_{cell[1]}"
    mat = rock_material(name, tex, bands=tex.get("bands"))
    if cell is not None:
        mat["tyrian_rock_cell"] = [int(cell[0]), int(cell[1])]
    rock = pal.add(mat)
    frame = Frame([[n]], scale=2)
    bm = bmesh.new()
    mask_slab(bm, region, frame, bottom + min(0.0, heights.min()), 0.0, rock, rock, rock,
              top_height=heights, smooth_top=n in ROCK_UNDERSIDE)
    smooth_outline(bm, region, frame)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    # Merge the level top into big faces, but keep every vertex along the tile's edge: a neighbour
    # keeps its own there, and an edge one side has as one long edge and the other as several (a
    # T-junction) rasterises with hairline gaps along the seam.
    hw, hh = TILE_W * PX / 2, TILE_H * PX / 2
    edge = lambda v: abs(abs(v.co.x) - hw) < 1e-5 or abs(abs(v.co.y) - hh) < 1e-5  # noqa: E731
    keep = {v for v in bm.verts if edge(v)}
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(ROCK_MERGE_DEG), verts=[v for v in bm.verts if v not in keep],
                             edges=[e for e in bm.edges if not (e.verts[0] in keep and e.verts[1] in keep)], delimit={"MATERIAL"})
    rock_uvs(bm, frame)
    return bm


# --- Island rock round an enemy's machine (DECISIONS.md D66, D75) ---------------------------------
#
# Some of TYRIAN's enemies that sit on the islands (the purple octagon walls, the eye fortress, the
# red machinery, the star core panel) fill their whole sprite: the machine, and round it island rock
# painted to blend with the tiles beneath. Their models build that rock as the islands do (an HD
# rock texture from the sprite's own pixels, lib_rock_hd, the same stones, mortar and cushions as
# rock_tile) and leave it out of the outline shell: there is no slab with walls, no boulders and no
# outline round the sprite's rectangle, so the rock reads as the island going on under the machine.
# The enemy is drawn about 0.4 units above the islands (top enemies at 2.5, background 3 at 2.1, D5)
# and placed on the camera ray through its screen point (D6), so the rock lands on screen exactly
# where the sprite's rock is drawn; it casts no shadow (`tyrian_ground`, the renderer's isGroundPart),
# which would otherwise lay a dark band along two of its edges on the island below.

#: How far below its top the rock's (unseen) underside is (units).
SPRITE_ROCK_SKIRT = 0.03
#: 2x px a piece's rock reaches over its neighbour's (no hairline between pieces drawn apart).
SPRITE_ROCK_OVERLAP = 1
#: How far (px) an enemy's rock fades out from the edge of its painted area into the island under it
#: (its own stones and the tiles' don't quite meet there).
SPRITE_ROCK_FADE = 1.5
#: Pixels (1x) of one other ramp in an enemy's rock for its rock texture to keep that colour (the
#: blue-grey stone of the red machinery); fewer, and they are snapped to ROCK_COLOURS.
EXTRA_RAMP_MIN = 12


class SpritePalette:
    """A Tileset-like palette for a sprite: `colors`, `lum` and `rgb(index)` (lum_of, Palette) from the
    level palette's colours, {index: (r, g, b)}."""

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


def sprite_ramps(pal, grid, machine):
    """The ramps an enemy's rock texture uses: lib_rock_hd.RAMPS, plus the most common other ramp
    painted where the machine doesn't stand if it has EXTRA_RAMP_MIN pixels; and the colours other
    paint snaps to (ROCK_COLOURS, and that ramp's shades)."""
    h, w = grid.shape
    under = machine.reshape(h, 2, w, 2).mean(axis=(1, 3)) > 0.5
    vals = grid[(grid >= 0) & ~under]
    counts = {}
    for v in vals:
        r = int(v) >> 4
        if r not in rh.RAMPS:
            counts[r] = counts.get(r, 0) + 1
    extra = max(counts, key=lambda r: (counts[r], -r)) if counts else None
    ramps = tuple(rh.RAMPS)
    keep = [k for k in ROCK_COLOURS if k in pal.colors]
    if extra is not None and counts[extra] >= EXTRA_RAMP_MIN:
        ramps += (extra,)
        keep += [i for i in range(extra * 16, extra * 16 + 16) if i in pal.colors]
    return ramps, keep


def sprite_rock(pal, grid, machine, layout, coll, tag, ground=0.0, piece=(24, 28), name_fmt="{}_rock"):
    """The island rock of an enemy's sprite (module notes above): one object per piece of `layout`.

    `pal`: the level palette (island_palette). `grid`: the sprite's pixels at 1x, an (h, w) array of
    palette indices (-1 transparent), the whole assembly for a multi-piece enemy. `machine`: bool
    (2h, 2w), where the machine stands (machine_footprint): the rock there is level at `ground` and
    dark under the machine, with a soft edge (darken: no pixel steps peek out round its feet). Elsewhere every painted pixel is rock: one HD rock texture for the whole
    grid (lib_rock_hd, rock_material `rock_<tag>`), the rock ramps' paint as it is, one other ramp
    kept if there is enough of it (sprite_ramps), the rest snapped to ROCK_COLOURS. `layout`:
    [(piece name, cx, cy)], each piece's centre in px from the grid's centre (as
    common.split_assembly); `piece`: its (w, h) in px. Each object's origin is its piece's centre;
    its heights and texture come from the whole grid, so the pieces meet exactly. Returns
    {piece name: object}."""
    grid = np.asarray(grid, dtype=np.int32)
    h, w = grid.shape
    rp = rh.Pal(pal.colors)
    ramps, keep = sprite_ramps(pal, grid, machine)
    ch = rh.compose(rh.fields(rp, rh.snap_rock(rp, grid, keep, ramps), ramps))
    g2 = rh.mmpx2x(grid, np.append(rp.lum[:256] * 765 + 1, 0.0))
    support = (g2 >= 0) | machine
    flat = machine
    # Coverage: 0 at the edge of the painted area (or the sprite's rectangle), 1 from SPRITE_ROCK_FADE in.
    k = rh.TEX // 2
    pad = int(3 * SPRITE_ROCK_FADE * rh.TEX)
    cover = np.pad(rh.nearest(support.astype(float), k), pad)
    cover = rh.blur(cover, SPRITE_ROCK_FADE * rh.TEX / 2)[pad:-pad, pad:-pad]
    alpha = rh.smoothstep(0.5, 0.98, cover)
    mat = rock_material(f"rock_{tag}", darken(ch, flat), ramps, alpha=alpha)
    frame = GridFrame(w, h, 2)
    out = {}
    for name, cx, cy in layout:
        x0, y0 = int(round((w / 2 + cx - piece[0] / 2) * 2)), int(round((h / 2 + cy - piece[1] / 2) * 2))
        # Each piece is drawn on its own (placed by the game at its sprite's place), so neighbouring
        # pieces can leave a hairline gap: each reaches SPRITE_ROCK_OVERLAP cells over its neighbour's
        # (same texture, same place: the overlap doesn't show).
        m = SPRITE_ROCK_OVERLAP
        region = np.zeros_like(support)
        region[max(0, y0 - m):y0 + piece[1] * 2 + m, max(0, x0 - m):x0 + piece[0] * 2 + m] = True
        region &= support
        if not region.any():
            continue
        p = Palette(pal, tag, plain=True, **ROCK_FINISH)
        rock = p.add(mat)
        bm = bmesh.new()
        # A sheet, no side walls: seen past the enemy's edge they drew a dark line round its rock.
        mask_slab(bm, region, frame, ground - SPRITE_ROCK_SKIRT, ground, rock, rock, rock, support=support,
                  walls=np.ones_like(support))
        smooth_outline(bm, support, frame)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(ROCK_MERGE_DEG), verts=bm.verts, edges=bm.edges,
                                 delimit={"MATERIAL"})
        rock_uvs(bm, frame)
        bmesh.ops.translate(bm, vec=(-cx * PX, cy * PX, 0), verts=bm.verts)
        obj = mesh(name_fmt.format(name), bm, p, coll, smooth=None)
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
