"""Shared parts for the asteroid-base buildings on the ground of map 1-3 (shapesz.dat, layer 0):
3D versions of the platforms drawn by the tiles, after the Gemini concepts
assets/blender/features/concepts/l1-bld-<name>.jpg (DECISIONS.md D34; lib_tiles.py for the basics).

Every building is one tile model: `Building(name)` loads its pattern (BUILDINGS below), the tiles'
pixels and a palette, and offers the common look of the concepts:

- the platform: a slab with the painted footprint's outline, its paved deck at DECK, the brown
  channels inlaid (CHANNEL_DROP below the deck), dark pits and hatches recessed; `surface()` makes a
  first version of the per-pixel heights and materials from the tiles' colours, which a building's
  script then edits (`set_region`, `raise_box`) before `terrace()` turns it into geometry;
- the rocky, crenellated rim: `rim_rocks()` sets bevelled rock blocks along the outline;
- red light capsules with an emissive glow (`capsule`), dark hatches (`hatch`), wall blocks
  (`wall_block`), domes (`dome`);
- `check()` (heights under ground enemies) and `export()` (lib_tiles.export_tile_model, plus
  `minRows`, which these shared tiles need: src/render/remaster/tileModels.ts).

Units and frame as lib_tiles: 1 unit = 12 tile px, origin at the pattern's centre, X right, Y up
(screen up), Z up, z = 0 the ground (black space on this map). Pixel coordinates (px, py) are in the
pattern at 1x, top-left (0, 0); `b.x(px)`, `b.y(py)` convert.

Heights (the game draws ground enemies at 0.45 units, D5; their models' bases sit at 0.39-0.45):
- under a cell with a ground enemy (`b.enemy_mask`; the turrets, red lights, orbs, pads and hatches
  of these buildings are mostly enemies drawn exactly over their tiles) the top stays between 0.30
  and ENEMY_MAX, so the enemy sits on it; DECK is the paving's height;
- rim rocks up to RIM_MAX; raised blocks and domes away from enemy cells up to TALL_MAX (the next
  pass, background 2's middle, is at 0.9).
Colours are palette materials (pal_<index>_<tag>) with indices from the tiles (PAL), so level
palettes, fades and filters apply; the concept's detail comes from the bake (texture_bake.py).
"""

import json
import math
import random
from pathlib import Path

import bmesh
import bpy
import numpy as np

import common
import lib_tiles as lt

ROOT = common.repo_root(__file__)
SHAPES = "shapesz"
LAYER = 0

DECK = 0.34  # the paving's top
ENEMY_MAX = 0.38  # highest top under a ground enemy's cell
ENEMY_MIN = 0.30  # lowest top under a ground enemy's cell (lower and it floats)
RIM_MAX = 0.50
TALL_MAX = 0.80
SLAB_BOTTOM = -0.04  # just under the ground plane
CHANNEL_DROP = 0.03  # channels are inlaid this much below the deck
PIT_DROP = 0.07  # dark pits and recesses
MIN_ROWS = 2  # rows that must be drawn and match before the model is placed (patterns.json)

#: Palette indices of the common parts (the level palette's ramps: 1-12 greys, 112-127 reds,
#: 160-175 and 16-31 browns). Pick shades from the tiles where a building differs.
PAL = {
    "pave": 6,  # paving (81 grey)
    "wall": 4,  # the slab's sides
    "rim": 5,  # rim rocks; rim_rocks() mixes in 4 and 6
    "channel": 164,  # brown channels
    "red": 115,  # red lights, emissive
    "red_dark": 112,  # their housings
    "dark": 1,  # pits, hatch interiors
    "metal": 9,  # light metal: hatch frames, raised plates
}

#: The buildings, from patterns.json: their place on map 1-3, the pattern (every cell; -1 = empty
#: space), the rows the model covers (pipe-junction's last two rows are context: the base's top
#: edge, which the base model covers) and the cells (row, col) where ground enemies sit.
BUILDINGS = {
    "bunker": dict(
        concept="l1-bld-bunker", map_rows=(173, 178), map_cols=(1, 6), cover_rows=(0, 5),
        enemies=[(2, 2), (2, 3), (3, 2), (3, 3)],
        pattern=[
            [360, 361, 361, 361, 361, 362],
            [370, 415, 416, 416, 417, 372],
            [370, 418, 318, 319, 419, 372],
            [370, 418, 328, 329, 419, 372],
            [370, 409, 399, 399, 383, 372],
            [380, 381, 381, 381, 381, 382],
        ]),
    "ring-dome": dict(
        concept="l1-bld-ring-dome", map_rows=(154, 160), map_cols=(2, 11), cover_rows=(0, 6),
        enemies=[(1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (2, 1), (3, 1), (3, 8), (4, 8)],
        pattern=[
            [-1, 360, 361, 361, 361, 361, 361, 361, 362, -1],
            [360, 363, 347, 339, 358, 358, 339, 347, 364, 362],
            [370, 357, 374, 381, 373, 374, 381, 373, 371, 372],
            [370, 357, 372, 360, 363, 364, 362, 370, 357, 372],
            [380, 381, 382, 370, 415, 417, 372, 370, 357, 372],
            [-1, -1, -1, 370, 409, 383, 372, 380, 381, 382],
            [-1, -1, -1, 380, 381, 381, 382, -1, -1, -1],
        ]),
    "ring-dome-b": dict(
        concept="l1-bld-ring-dome", map_rows=(164, 170), map_cols=(1, 10), cover_rows=(0, 6),
        enemies=[(1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (2, 8), (3, 1), (3, 8), (4, 1)],
        pattern=[
            [-1, 360, 361, 361, 361, 361, 361, 361, 362, -1],
            [360, 363, 347, 339, 339, 339, 339, 347, 364, 362],
            [370, 371, 374, 381, 373, 374, 381, 373, 357, 372],
            [370, 357, 372, 360, 363, 364, 362, 370, 357, 372],
            [370, 357, 372, 370, 415, 417, 372, 380, 381, 382],
            [380, 381, 382, 370, 409, 383, 372, -1, -1, -1],
            [-1, -1, -1, 380, 381, 381, 382, -1, -1, -1],
        ]),
    "light-bridge": dict(
        concept="l1-bld-light-bridge", map_rows=(132, 136), map_cols=(1, 13), cover_rows=(0, 4),
        enemies=[(1, 5), (1, 6), (1, 7), (1, 8), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8),
                 (2, 9), (2, 10), (2, 11), (2, 12), (3, 1), (3, 2), (3, 11), (3, 12)],
        pattern=[
            [-1, -1, -1, -1, 360, 361, 361, 361, 361, 362, -1, -1, -1],
            [360, 361, 361, 361, 363, 358, 357, 357, 358, 364, 361, 361, 361],
            [370, 305, 306, 339, 339, 339, 339, 339, 339, 339, 339, 305, 306],
            [370, 315, 316, 374, 373, 371, 371, 371, 371, 374, 373, 315, 316],
            [380, 381, 381, 382, 380, 381, 381, 381, 381, 382, 380, 381, 381],
        ]),
    "red-bar": dict(
        concept="l1-bld-red-bar", map_rows=(225, 227), map_cols=(4, 9), cover_rows=(0, 2),
        enemies=[(1, 1), (1, 2), (1, 3), (1, 4)],
        pattern=[
            [360, 361, 361, 361, 361, 362],
            [370, 347, 339, 339, 347, 372],
            [380, 381, 381, 381, 381, 382],
        ]),
    "cross-pad": dict(
        concept="l1-bld-cross-pad", map_rows=(233, 237), map_cols=(5, 9), cover_rows=(0, 4),
        enemies=[(1, 2), (2, 1), (2, 2), (2, 3), (3, 2)],
        pattern=[
            [-1, 360, 361, 362, -1],
            [360, 363, 338, 364, 362],
            [370, 339, 347, 339, 372],
            [380, 373, 338, 374, 382],
            [-1, 380, 381, 382, -1],
        ]),
    "pipe-junction": dict(
        concept="l1-bld-pipe-junction", map_rows=(238, 249), map_cols=(3, 11), cover_rows=(0, 9),
        enemies=[],
        pattern=[
            [360, 361, 361, 362, -1, 360, 361, 361, 362],
            [370, 365, 367, 364, 361, 363, 365, 367, 372],
            [370, 389, 385, 379, 366, 379, 387, 389, 372],
            [370, 385, 379, 367, 389, 365, 379, 387, 372],
            [380, 381, 373, 385, 376, 387, 374, 381, 382],
            [-1, -1, 380, 373, 389, 374, 382, -1, -1],
            [-1, -1, -1, 370, 389, 372, -1, -1, -1],
            [-1, -1, -1, 370, 389, 372, -1, -1, -1],
            [-1, -1, -1, 370, 389, 372, -1, -1, -1],
            [-1, -1, -1, 370, 389, 372, -1, -1, -1],
            [361, 361, 361, 363, 389, 364, 361, 361, 361],
            [365, 379, 379, 379, 376, 379, 379, 379, 367],
        ]),
    "base-complex": dict(
        concept="l1-bld-base-complex", map_rows=(248, 286), map_cols=(1, 13), cover_rows=(0, 38),
        enemies=[(4, 8), (5, 4), (5, 6), (6, 6), (11, 5), (11, 7), (16, 6), (16, 7), (17, 3), (17, 6), (17, 7),
                 (17, 10), (20, 7), (20, 8), (20, 9), (29, 6), (30, 5), (30, 6), (30, 8), (30, 9), (31, 5), (31, 6),
                 (31, 8), (31, 9), (36, 1), (37, 4), (37, 5), (37, 8), (37, 9)],
        pattern=None),  # filled from the map below (39 x 13 cells)
}

# The base complex's 39 rows, map 1-3 rows 248-286, cols 1-13 (-1 = empty space).
_BASE = """
 -1 360 361 361 361 363 389 364 361 361 361 362  -1
 -1 370 365 379 379 379 376 379 379 379 367 372  -1
 -1 370 389 374 381 373 388 374 381 373 389 372  -1
 -1 370 389 372 360 363 371 364 361 363 389 372  -1
 -1 370 389 364 363 371 371 371 338 368 377 372  -1
 -1 370 375 369 338 371 371 371 374 373 389 372  -1
 -1 370 389 374 381 373 339 374 382 370 389 372  -1
 -1 370 389 364 361 363 378 364 361 363 389 372  -1
 -1 370 385 379 379 379 376 379 379 379 387 372  -1
 -1 380 381 381 373 371 389 371 374 381 381 382  -1
 -1  -1  -1  -1 370 371 389 371 372  -1  -1  -1  -1
360 361 361 361 363 371 389 371 372  -1  -1  -1  -1
370 371 371 371 371 371 389 371 364 361 362  -1  -1
370 371 365 379 379 379 377 371 371 371 372  -1  -1
370 371 389 371 374 373 389 371 374 373 364 362  -1
370 371 389 371 372 370 388 371 372 370 371 372  -1
370 371 389 371 372 370 305 306 372 370 371 372  -1
370 371 389 371 372 370 315 316 372 370 371 372  -1
370 371 389 371 372 380 381 381 382 370 371 372  -1
370 371 389 371 364 361 361 361 361 363 371 372  -1
370 371 389 371 347 347 384 384 347 347 371 364 362
370 371 385 379 379 379 379 366 379 369 298 299 372
370 371 371 371 371 371 371 389 371 371 308 309 372
380 381 381 381 381 381 373 389 371 374 381 381 382
 -1  -1  -1  -1  -1  -1 370 389 371 372  -1  -1  -1
 -1  -1  -1  -1  -1  -1 370 389 371 372  -1  -1  -1
 -1  -1  -1  -1  -1  -1 370 389 371 372  -1  -1  -1
 -1  -1  -1  -1  -1  -1 370 389 371 372  -1  -1  -1
 -1  -1  -1  -1 360 361 363 389 371 372  -1  -1  -1
 -1  -1  -1  -1 370 371 371 389 371 364 362  -1  -1
 -1 360 361 361 363 318 319 389 318 319 364 361 361
360 363 371 371 371 328 329 389 328 329 371 371 371
370 365 379 379 379 366 379 386 366 379 379 379 367
370 389 371 371 371 389 371 371 389 371 371 371 389
370 389 374 373 371 389 374 373 389 371 374 373 389
370 388 372 370 371 389 372 370 389 371 372 370 388
370 371 372 370 371 388 372 370 388 371 372 370 371
370 371 372 370 371 371 372 370 371 371 372 370 371
380 381 382 380 381 381 382 380 381 381 382 380 381
"""
BUILDINGS["base-complex"]["pattern"] = [[int(v) for v in line.split()] for line in _BASE.strip().splitlines()]


# --- Pixel helpers (numpy only: Blender's Python has no scipy) -----------------------------------

def shift(mask, dy, dx, fill=False):
    out = np.full_like(mask, fill)
    h, w = mask.shape
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = mask[ys, xs]
    return out


def dilate(mask, r=1):
    out = mask.copy()
    for _ in range(r):
        out = out | shift(out, 1, 0) | shift(out, -1, 0) | shift(out, 0, 1) | shift(out, 0, -1)
    return out


def erode(mask, r=1):
    return ~dilate(~mask, r)


def close(mask, r=1):
    return erode(dilate(mask, r), r)


def open_(mask, r=1):
    return dilate(erode(mask, r), r)


def depth(mask, limit=40):
    """Steps (4-neighbour) from each pixel of `mask` to the nearest pixel outside it, up to `limit`."""
    d = np.zeros(mask.shape, dtype=np.int32)
    cur = mask.copy()
    for i in range(1, limit + 1):
        d[cur] = i
        cur = erode(cur, 1)
        if not cur.any():
            break
    return d


def drop_small(mask, min_px):
    out = np.zeros_like(mask)
    for ys, xs in lt.components(mask):
        if len(ys) >= min_px:
            out[ys, xs] = True
    return out


# --- The building --------------------------------------------------------------------------------

class Building:
    """One building: its pattern, pixels, masks and the geometry being built.

    Attributes: ts (lib_tiles.Tileset), name, pattern, rows, cols, W, H (pattern size in px),
    grid (1x palette indices; -1 in empty cells), cover (bool, px of the cells the model covers),
    footprint (bool, the painted platform: what the model must cover), enemy_mask (bool, px of cells
    with a ground enemy), pal (lib_tiles.Palette), height / mat (per-pixel deck heights and material
    slots, from surface()), parts (bmesh of closed extra pieces: rocks, capsules, hatches, ...)."""

    # The frame's heights and names, as class attributes so a subclass can change them for another
    # map or layer (lib_tyrbld.py: TYRIAN's background 3); the defaults are map 1-3's ground.
    layer = LAYER
    prefix = "l1bld"  # model tiles/shapesz/<prefix>-<name>, entry shapesz-<prefix>-<name>.json
    deck = DECK
    enemy_max = ENEMY_MAX
    enemy_min = ENEMY_MIN
    rim_max = RIM_MAX
    tall_max = TALL_MAX
    z_min = None  # lowest vertex allowed (check()); None: no limit
    slab_bottom = SLAB_BOTTOM
    min_rows = MIN_ROWS
    keep_tiles = None  # the entry's keepTiles (None: the layer's default)

    def __init__(self, name, tag=None, spec=None):
        spec = BUILDINGS[name] if spec is None else spec
        self.name = name
        self.spec = spec
        self.ts = lt.Tileset(ROOT, SHAPES, layer=self.layer)
        self.pattern = spec["pattern"]
        self.rows, self.cols = len(self.pattern), len(self.pattern[0])
        self.W, self.H = self.cols * lt.TILE_W, self.rows * lt.TILE_H
        self.frame = lt.Frame(self.pattern, scale=1)
        self.grid = self.ts.grid(self.pattern, 1)
        r0, r1 = spec["cover_rows"]
        self.cover = np.zeros((self.H, self.W), bool)
        for r, row in enumerate(self.pattern):
            for c, t in enumerate(row):
                if t >= 0 and r0 <= r <= r1:
                    self.cover[r * lt.TILE_H:(r + 1) * lt.TILE_H, c * lt.TILE_W:(c + 1) * lt.TILE_W] = True
        self.footprint = self.make_footprint()
        self.enemy_mask = np.zeros_like(self.cover)
        for r, c in spec["enemies"]:
            self.enemy_mask[r * lt.TILE_H:(r + 1) * lt.TILE_H, c * lt.TILE_W:(c + 1) * lt.TILE_W] = True
        self.pal = lt.Palette(self.ts, tag or f"{self.prefix}{name.replace('-', '')}", roughness=0.85, metallic=0.0)
        self.height = None
        self.mat = None
        self.parts = bmesh.new()
        self._rng = random.Random(name)

    def make_footprint(self):
        """The painted platform in the covered cells (what the model must cover)."""
        painted = self.cover & (self.grid > 0)
        # The outline between the rim's painted rocks has gaps of black: close them, keep real holes
        # (pits, the yard inside a U) that are bigger than a few pixels.
        closed = close(painted, 2) & self.cover
        holes = self.cover & ~closed
        small = holes & ~drop_small(holes, 40)
        return closed | small

    # Coordinates ---------------------------------------------------------------------------------

    def x(self, px):
        return self.frame.x(px)

    def y(self, py):
        return self.frame.y(py)

    def cell_box(self, r, c):
        """A cell's pixel box (x0, y0, x1, y1)."""
        return c * lt.TILE_W, r * lt.TILE_H, (c + 1) * lt.TILE_W, (r + 1) * lt.TILE_H

    def tiles_at(self, tile):
        """Every (row, col) of the pattern holding `tile`."""
        return [(r, c) for r, row in enumerate(self.pattern) for c, t in enumerate(row) if t == tile]

    # Materials -----------------------------------------------------------------------------------

    def m(self, kind_or_index, **kw):
        """Material slot for a PAL kind ("pave", "rim", ...) or a palette index. Kinds come with
        sensible surface settings: red glows, metal shines."""
        if isinstance(kind_or_index, str):
            kind = kind_or_index
            index = PAL[kind]
            defaults = {"red": dict(emission_strength=2.5, roughness=0.3), "metal": dict(metallic=0.6, roughness=0.4),
                        "red_dark": dict(metallic=0.3, roughness=0.5), "dark": dict(roughness=0.9)}.get(kind, {})
            kw = {**defaults, **kw}
        else:
            index = kind_or_index
        return self.pal(index, **kw)

    # Masks from the tiles' colours ---------------------------------------------------------------

    def masks(self):
        """Per-pixel classes of the footprint from the tiles' colours: rim (the outer band of rocks),
        channel (browns), red (the red lights), dark (big near-black areas: pits, hatches, pads),
        pave (the rest)."""
        g = np.maximum(self.grid, 0)
        fp = self.footprint
        lum = lt.lum_of(self.ts, self.grid)
        ramp = g >> 4
        red = fp & (ramp == 7)
        red = open_(close(red, 1), 1)
        brown = fp & ((ramp == 10) | (ramp == 1))
        channel = drop_small(open_(close(brown, 1), 1), 30)
        dark = fp & (lum < 0.07) & ~red
        dark = drop_small(open_(dark, 1), 40)
        d = depth(fp)
        rim = fp & (d <= 7)
        return dict(rim=rim, channel=channel & ~rim, red=red & ~rim, dark=dark & ~rim, pave=fp & ~rim, depth=d)

    def surface(self, deck=None, channel=True, pits=True, red=True):
        """A first version of the deck: per-pixel heights (nan = no platform) and material slots.
        Paving at `deck`, channels CHANNEL_DROP lower, dark areas PIT_DROP lower (in a building's
        script, decide per area whether a dark spot is a pit, a hatch or an enemy's pad), red lights
        flush in red. The rim band is paving too: rim_rocks() covers it."""
        deck = self.deck if deck is None else deck
        mk = self.masks()
        self.height = np.full((self.H, self.W), np.nan, dtype=np.float32)
        self.mat = np.full((self.H, self.W), -1, dtype=np.int32)
        fp = self.footprint
        self.height[fp] = deck
        self.mat[fp] = self.m("pave")
        if channel:
            self.height[mk["channel"]] = deck - CHANNEL_DROP
            self.mat[mk["channel"]] = self.m("channel")
        if pits:
            self.height[mk["dark"]] = deck - PIT_DROP
            self.mat[mk["dark"]] = self.m("dark")
        if red:
            self.mat[mk["red"]] = self.m("red")
        self._masks = mk
        return mk

    def set_region(self, mask, z=None, mat=None):
        """Set the deck's height and/or material where `mask` (bool, pattern px) is on the footprint."""
        sel = mask & self.footprint
        if z is not None:
            self.height[sel] = z
        if mat is not None:
            self.mat[sel] = mat
        return sel

    def box_mask(self, x0, y0, x1, y1):
        m = np.zeros((self.H, self.W), bool)
        m[max(0, int(round(y0))):int(round(y1)), max(0, int(round(x0))):int(round(x1))] = True
        return m

    def raise_box(self, x0, y0, x1, y1, z, mat=None):
        """Deck heights in a pixel box set to z (a raised or sunk plate): a terrace step."""
        return self.set_region(self.box_mask(x0, y0, x1, y1), z, mat)

    # Geometry ------------------------------------------------------------------------------------

    def terrace(self, height=None, mat=None, bottom=None, wall_mat=None):
        """The deck as geometry: flat tops at each pixel's height (equal neighbours merged into
        rectangles), vertical walls between different heights and down to `bottom` at the edge
        (`wall_mat`, default "wall", for the outer sides; steps inside take the higher side's
        material), and a bottom. Returns the bmesh (the object is made by export())."""
        bottom = self.slab_bottom if bottom is None else bottom
        height = self.height if height is None else height
        mat = self.mat if mat is None else mat
        wall_mat = self.m("wall") if wall_mat is None else wall_mat
        H, W = height.shape
        has = ~np.isnan(height)
        hq = np.where(has, np.round(np.nan_to_num(height) * 1000).astype(np.int64), -10**9)
        bm = bmesh.new()
        verts = {}

        def v(px, py, z):
            k = (px, py, int(round(z * 1000)))
            vv = verts.get(k)
            if vv is None:
                vv = verts[k] = bm.verts.new((self.x(px), self.y(py), z))
            return vv

        def face(vs, normal, mi):
            # Order the loop so its normal points along `normal`.
            a, b, c = (vv.co for vv in vs[:3])
            n = (b - a).cross(c - a)
            if n.dot(normal) < 0:
                vs = list(reversed(vs))
            try:
                f = bm.faces.new(vs)
            except ValueError:
                return None
            f.material_index = int(mi)
            return f

        from mathutils import Vector
        up, down = Vector((0, 0, 1)), Vector((0, 0, -1))
        label = hq * 4096 + np.where(has, mat, 0)
        for lab_grid, z_of, normal, mi_of in ((label, lambda y, x: hq[y, x] / 1000, up, lambda y, x: mat[y, x]),
                                              (np.where(has, 1, 0), lambda y, x: bottom, down, lambda y, x: wall_mat)):
            done = ~has.copy()
            for y in range(H):
                x = 0
                while x < W:
                    if done[y, x]:
                        x += 1
                        continue
                    lab = lab_grid[y, x]
                    x1 = x
                    while x1 < W and not done[y, x1] and lab_grid[y, x1] == lab:
                        x1 += 1
                    y1 = y + 1
                    while y1 < H and not done[y1, x:x1].any() and (lab_grid[y1, x:x1] == lab).all():
                        y1 += 1
                    done[y:y1, x:x1] = True
                    z = z_of(y, x)
                    face([v(x, y1, z), v(x1, y1, z), v(x1, y, z), v(x, y, z)], normal, mi_of(y, x))
                    x = x1

        def z_at(y, x):
            if 0 <= y < H and 0 <= x < W and has[y, x]:
                return hq[y, x] / 1000
            return None

        # Walls on vertical pixel edges (between x-1 and x), merged along runs of rows.
        for x in range(W + 1):
            y = 0
            while y < H:
                zl, zr = z_at(y, x - 1), z_at(y, x)
                if zl == zr or (zl is None and zr is None):
                    y += 1
                    continue
                y1 = y + 1
                while y1 < H and z_at(y1, x - 1) == zl and z_at(y1, x) == zr:
                    y1 += 1
                hi_left = zr is None or (zl is not None and zl > zr)
                top = zl if hi_left else zr
                low = bottom if (zr if hi_left else zl) is None else (zr if hi_left else zl)
                outer = (zr if hi_left else zl) is None
                mi = wall_mat if outer else mat[y, x - 1] if hi_left else mat[y, x]
                normal = Vector((1, 0, 0)) if hi_left else Vector((-1, 0, 0))
                face([v(x, y, low), v(x, y1, low), v(x, y1, top), v(x, y, top)], normal, mi)
                y = y1
        # Walls on horizontal pixel edges (between y-1 and y), merged along runs of columns.
        for y in range(H + 1):
            x = 0
            while x < W:
                zu, zd = z_at(y - 1, x), z_at(y, x)
                if zu == zd or (zu is None and zd is None):
                    x += 1
                    continue
                x1 = x + 1
                while x1 < W and z_at(y - 1, x1) == zu and z_at(y, x1) == zd:
                    x1 += 1
                hi_up = zd is None or (zu is not None and zu > zd)
                top = zu if hi_up else zd
                other = zd if hi_up else zu
                low = bottom if other is None else other
                mi = wall_mat if other is None else mat[y - 1, x] if hi_up else mat[y, x]
                # The wall faces the lower side: pixel row y is below row y - 1 on screen (-Y).
                normal = Vector((0, -1, 0)) if hi_up else Vector((0, 1, 0))
                face([v(x, y, low), v(x1, y, low), v(x1, y, top), v(x, y, top)], normal, mi)
                x = x1
        return bm

    def rim_rocks(self, spacing=7.0, inset=3.0, size=(0.55, 0.85), height=None, sink=0.12,
                  rows=1, mats=None, keep=None, sides=(5, 7), jitter=0.35):
        """Rocks along the footprint's outline, as in the concepts' rocky, crenellated rims: bevelled
        blocks (lib_tiles.block) every `spacing` px, centred `inset` px inside the outline, `size`
        x spacing across (alternating big and small), tops between `height`, sunk `sink` under the
        deck where they stand. Over an enemy cell a rock is capped at ENEMY_MAX. `rows` > 1 adds an inner row of
        smaller rocks; `jitter` (fraction of a rock's size) roughens each one. `keep(px, py)` can drop rocks (e.g. where a wall or a stair meets the rim).
        Adds to self.parts; returns the number of rocks."""
        height = (0.40, self.rim_max) if height is None else height
        mats = mats or [self.m("rim"), self.m(4), self.m(6)]
        d = depth(self.footprint)
        n = 0
        for row in range(rows):
            inset_r = inset + row * spacing * 0.75
            scale = 1.0 - 0.3 * row
            # Pixels at about `inset_r` from the outline, taken in a fixed order with spacing between.
            ring = (d >= max(1, inset_r - 1)) & (d <= inset_r + 1)
            ys, xs = np.nonzero(ring)
            order = list(range(len(ys)))
            self._rng.shuffle(order)
            taken = []
            cell = {}
            sp = spacing * scale
            for i in order:
                px, py = xs[i] + 0.5, ys[i] + 0.5
                gx, gy = int(px // sp), int(py // sp)
                near = False
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for qx, qy in cell.get((gx + dx, gy + dy), ()):
                            if (qx - px) ** 2 + (qy - py) ** 2 < sp * sp:
                                near = True
                                break
                if near:
                    continue
                cell.setdefault((gx, gy), []).append((px, py))
                taken.append((px, py))
            for k, (px, py) in enumerate(taken):
                if keep and not keep(px, py):
                    continue
                big = (k % 2 == 0)
                r_px = sp * (size[1] if big else size[0]) * (0.9 + 0.2 * self._rng.random())
                rx = r_px * (0.8 + 0.3 * self._rng.random()) * lt.PX
                ry = r_px * (0.8 + 0.3 * self._rng.random()) * lt.PX
                top = height[0] + (height[1] - height[0]) * (self._rng.random() * (1.0 if big else 0.6))
                y0, y1 = int(max(0, py - r_px)), int(min(self.H, py + r_px + 1))
                x0, x1 = int(max(0, px - r_px)), int(min(self.W, px + r_px + 1))
                if self.enemy_mask[y0:y1, x0:x1].any():
                    top = min(top, self.enemy_max)
                # Sunk into the deck where it stands (DECK before surface()).
                here = self.height[min(self.H - 1, int(py)), min(self.W - 1, int(px))] if self.height is not None else np.nan
                z0 = (self.deck if np.isnan(here) else float(here)) - sink
                rock = bmesh.new()
                lt.block(rock, self.x(px), self.y(py), rx, ry, self._rng.random() * math.pi, z0, top - z0,
                         mats[self._rng.randrange(len(mats))], sides=self._rng.randint(*sides), bevel=0.35)
                # Break the regular prism: jitter each corner across and the top corners up and down.
                for vert in rock.verts:
                    vert.co.x += (self._rng.random() - 0.5) * jitter * rx
                    vert.co.y += (self._rng.random() - 0.5) * jitter * ry
                    if vert.co.z > z0 + 1e-6:
                        vert.co.z = min(vert.co.z + (self._rng.random() - 0.5) * jitter * (top - z0) * 0.5, top)
                self._merge(rock)
                n += 1
        return n

    def capsule(self, px, py, length, radius, axis="x", z=None, mat=None, housing=True, sides=12):
        """A red light capsule lying on the deck: a cylinder with round ends, `length` and `radius`
        in px, along "x" or "y", its top at z (default ENEMY_MAX - 0.01: they sit under enemies),
        glowing (mat default "red"); with `housing`, a dark frame around it, a little lower."""
        mat = self.m("red") if mat is None else mat
        r = radius * lt.PX
        half = max(0.0, length / 2 * lt.PX - r)
        ztop = (self.enemy_max - 0.01) if z is None else z
        zc = ztop - r
        cx, cy = self.x(px), self.y(py)
        ax = (1, 0) if axis == "x" else (0, 1)
        bm = bmesh.new()
        rings = []
        # Profile from one end to the other: hemisphere, cylinder, hemisphere.
        prof = []
        steps = 4
        for i in range(steps + 1):
            a = math.pi / 2 * (1 - i / steps)
            prof.append((-half - r * math.sin(a), r * math.cos(a)))
        for i in range(steps + 1):
            a = math.pi / 2 * i / steps
            prof.append((half + r * math.sin(a), r * math.cos(a)))
        for t, rad in prof:
            ring = []
            for j in range(sides):
                b = 2 * math.pi * j / sides
                u, w = rad * math.cos(b), rad * math.sin(b)  # u across, w up
                x = cx + ax[0] * t + (-ax[1]) * u
                y = cy + ax[1] * t + ax[0] * u
                ring.append(bm.verts.new((x, y, zc + w)))
            rings.append(ring)
        for r0, r1 in zip(rings, rings[1:]):
            for j in range(sides):
                k = (j + 1) % sides
                bm.faces.new((r0[j], r0[k], r1[k], r1[j])).material_index = mat
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(list(reversed(rings[-1]))).material_index = mat
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self._merge(bm)
        if housing:
            hl = length + 3
            hw = radius * 2 + 3
            w, h = (hl, hw) if axis == "x" else (hw, hl)
            self.wall_block(px - w / 2, py - h / 2, px + w / 2, py + h / 2, self.deck - 0.05, ztop - r * 0.6, self.m("red_dark"), bevel=0.25)

    def wall_block(self, x0, y0, x1, y1, z0, z1, mat=None, bevel=0.3):
        """A box with chamfered top edges over the pixel box, from z0 to z1 (bevel: fraction of the
        smaller side, at most 2 px)."""
        mat = self.m("wall") if mat is None else mat
        b = min(2.0, bevel * min(x1 - x0, y1 - y0) / 2)
        bm = bmesh.new()

        def ring(inset, z):
            return [bm.verts.new((self.x(px), self.y(py), z)) for px, py in
                    ((x0 + inset, y1 - inset), (x1 - inset, y1 - inset), (x1 - inset, y0 + inset), (x0 + inset, y0 + inset))]

        base = ring(0, z0)
        edge = ring(0, z1 - b * lt.PX)
        top = ring(b, z1)
        bm.faces.new(top).material_index = mat
        bm.faces.new(list(reversed(base))).material_index = mat
        for a, c in ((base, edge), (edge, top)):
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new((a[i], a[j], c[j], c[i])).material_index = mat
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self._merge(bm)

    def hatch(self, x0, y0, x1, y1, z=None, frame_px=2.0, depth_=0.05, mat_frame=None, mat_inside=None):
        """A dark hatch: a frame of light metal around a recessed dark panel (pixel box), its frame
        top at z (default ENEMY_MAX: hatches are often under enemies)."""
        z = self.enemy_max if z is None else z
        mat_frame = self.m("metal") if mat_frame is None else mat_frame
        mat_inside = self.m("dark") if mat_inside is None else mat_inside
        f = frame_px
        for bx in ((x0, y0, x1, y0 + f), (x0, y1 - f, x1, y1), (x0, y0 + f, x0 + f, y1 - f), (x1 - f, y0 + f, x1, y1 - f)):
            self.wall_block(*bx, self.deck - 0.05, z, mat_frame, bevel=0.2)
        self.wall_block(x0 + f, y0 + f, x1 - f, y1 - f, self.deck - 0.05, z - depth_, mat_inside, bevel=0.0)

    def dome(self, px, py, rx_px, ry_px, z0, height, mat=None, sides=20, rings=6):
        """A dome (half ellipsoid) on the plane z0, radii in px."""
        mat = self.m("metal") if mat is None else mat
        bm = bmesh.new()
        lt.dome(bm, self.x(px), self.y(py), rx_px * lt.PX, ry_px * lt.PX, 0.0, z0, height, mat, sides=sides, rings=rings)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self._merge(bm, smooth=True)

    def _merge(self, bm, smooth=False):
        if smooth:
            for f in bm.faces:
                f.smooth = True
        tmp = bpy.data.meshes.new("tmp_l1bld")
        bm.to_mesh(tmp)
        bm.free()
        self.parts.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)

    # Checks and export ---------------------------------------------------------------------------

    def check(self, objects, strict=True):
        """Heights: nothing above ENEMY_MAX over an enemy cell, nothing above TALL_MAX anywhere, and
        the footprint covered (top view). Prints the findings; with `strict` raises on a violation."""
        problems = []
        top = np.full((self.H, self.W), -1.0)
        for o in objects:
            if o.type != "MESH":
                continue
            me = o.data
            mw = o.matrix_world
            for poly in me.polygons:
                for vi in poly.vertices:
                    co = mw @ me.vertices[vi].co
                    px = int((co.x / lt.PX) + self.W / 2)
                    py = int(self.H / 2 - co.y / lt.PX)
                    if 0 <= px < self.W and 0 <= py < self.H:
                        top[py, px] = max(top[py, px], co.z)
                    if co.z > self.tall_max + 1e-4:
                        problems.append(f"vertex at z {co.z:.3f} > tall_max {self.tall_max}")
                    if self.z_min is not None and co.z < self.z_min - 1e-4:
                        problems.append(f"vertex at z {co.z:.3f} < z_min {self.z_min}")
        over = self.enemy_mask & (top > self.enemy_max + 1e-4)
        if over.any():
            ys, xs = np.nonzero(over)
            cells = sorted({(int(y) // lt.TILE_H, int(x) // lt.TILE_W) for y, x in zip(ys, xs)})
            problems.append(f"{over.sum()} vertices' px above enemy_max {self.enemy_max} in enemy cells {cells}")
        for p in problems[:10]:
            print("CHECK:", p)
        if not problems:
            print(f"check {self.name}: heights ok (max {top.max():.3f}; enemy cells max {top[self.enemy_mask].max() if self.enemy_mask.any() else 0:.3f})")
        if problems and strict:
            raise AssertionError(f"{self.name}: {len(problems)} height problems")
        return problems

    def objects(self, deck_bm=None, coll=None):
        """The building's objects: the terraced deck (`deck_bm` or terrace()) and the parts."""
        coll = coll or common.reset_collection(f"{SHAPES}-{self.prefix}-{self.name}")
        deck_bm = deck_bm or self.terrace()
        deck = mesh_object(f"{SHAPES}-{self.prefix}-{self.name}-deck", deck_bm, self.pal.materials, coll)
        objs = [deck]
        if len(self.parts.faces):
            bmesh.ops.recalc_face_normals(self.parts, faces=self.parts.faces)  # closed pieces
            parts = mesh_object(f"{SHAPES}-{self.prefix}-{self.name}-parts", self.parts, self.pal.materials, coll)
            objs.append(parts)
        return objs

    def export(self, objects, name=None):
        """Export public/models/tiles/shapesz/<prefix>-<name>.glb and src/render/tileModels/
        shapesz-<prefix>-<name>.json (with minRows unless it's None, and keepTiles if set)."""
        name = name or self.name
        out = lt.export_tile_model(self.ts, objects, f"{self.prefix}-{name}", self.layer, self.pattern, keep_tiles=self.keep_tiles)
        path = ROOT / "src" / "render" / "tileModels" / f"{SHAPES}-{self.prefix}-{name}.json"
        entry = json.loads(path.read_text())
        if self.min_rows is not None:
            entry["minRows"] = self.min_rows
        path.write_text(json.dumps(entry, indent=1) + "\n")
        return out


def mesh_object(name, bm, materials, collection):
    """Like common.mesh_object, but keeps the faces' winding as built (terrace() orients every face;
    recalculating normals on its open, T-jointed surfaces can flip some). Smooth flags kept."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj
