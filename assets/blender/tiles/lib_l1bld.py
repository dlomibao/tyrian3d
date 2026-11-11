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
import lib_sockets as ls
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

    # Hard-surface kit (D65's standard for structures, D141) ---------------------------------------
    #
    # Smooth outlines instead of pixel terraces, chamfered prisms, bolts, a top-view coverage check
    # and the model's own AO/roughness bake (no concept projection, CLAUDE.md art rule 4). Nothing
    # here runs unless a script calls it: the concept-baked buildings keep their look. A script starts
    # with clear_scene() and ends with finish() (check, top_iou, bake_model, preview, export); D139's
    # cover parts survive the bake as their own objects. ASTEROID?'s platform parts (rim rocks, kerb,
    # basket-weave paving, gratings, lights, hatches) are lib_l1kit.py's Kit.

    def outlines(self, mask, tol=0.6, min_px=6):
        """Smooth polygons round each 4-connected part of `mask` (bool, pattern px): its pixel
        outline traced at the pixels' corners (lib_sockets.trace, outer outline only: holes are not
        cut, build round them) and simplified (Douglas-Peucker, `tol` px), so the art's pixel
        staircases become straight diagonals. Parts under `min_px` pixels are dropped. Returns
        [[(px, py), ...], ...] in pattern px (y down), ready for slab()."""
        polys = []
        for ys, xs in lt.components(mask):
            if len(ys) < min_px:
                continue
            part = np.zeros(mask.shape, bool)
            part[ys, xs] = True
            loop = ls.trace(part)
            poly = ls.simplify(loop, tol) if tol else loop
            if len(poly) >= 3 and abs(ls.area(poly)) > 1.0:
                polys.append(poly)
        return polys

    def slab(self, poly, z0, z1, mat=None, chamfer_px=1.0, drop=0.03, side_mat=None, bevel_mat=None, smooth=False):
        """A hard-surface prism over the polygon `poly` (pattern px, either winding) from z0 up to a
        flat top at z1, its top edge chamfered `chamfer_px` in and `drop` down (0: a square edge).
        `side_mat` for the walls, `bevel_mat` for the chamfer (default `mat`). Flat shaded unless
        `smooth`. Closed (a bottom at z0). Adds to self.parts."""
        mat = self.m("wall") if mat is None else mat
        side_mat = mat if side_mat is None else side_mat
        bevel_mat = mat if bevel_mat is None else bevel_mat
        pts = [(float(x), float(y)) for x, y in poly]
        if ls.area(pts) < 0:  # screen y down: counter-clockwise in Blender's Y-up
            pts.reverse()
        n = len(pts)
        inner = ls.inset(pts, chamfer_px) if chamfer_px and drop else pts
        if inner is not pts and ls.area(inner) < 0.3 * ls.area(pts):
            inner = pts  # a sliver: the chamfer would turn it inside out
        bm = bmesh.new()
        base = [bm.verts.new((self.x(x), self.y(y), z0)) for x, y in pts]
        rings = [base]
        mats = []
        if inner is not pts:
            rings.append([bm.verts.new((self.x(x), self.y(y), z1 - drop)) for x, y in pts])
            mats.append(side_mat)
            rings.append([bm.verts.new((self.x(x), self.y(y), z1)) for x, y in inner])
            mats.append(bevel_mat)
        else:
            rings.append([bm.verts.new((self.x(x), self.y(y), z1)) for x, y in pts])
            mats.append(side_mat)
        for (a, b), mi in zip(zip(rings, rings[1:]), mats):
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mi
        bm.faces.new(rings[-1]).material_index = mat
        bm.faces.new(list(reversed(base))).material_index = side_mat
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self._merge(bm, smooth=smooth)

    def rim(self, poly, width_px, z0, z1, mat=None, keep=None, **kw):
        """A raised band `width_px` wide along the inside of the polygon `poly` (pattern px), from z0
        to z1: a rail round a walkway, a frame round a hatch or recess (build the recess's floor
        lower, the rim round it), a ring on a disc. One closed prism per edge, mitred at the
        corners. `keep(i, a, b)` (edge i from point a to b, pattern px) can leave edges out: a rail
        open where the walkway runs off the map. Other keywords go to slab() (chamfer_px defaults
        to 0 here: give the band's top a chamfer only if it's wide)."""
        pts = [(float(x), float(y)) for x, y in poly]
        if ls.area(pts) < 0:
            pts.reverse()
        inner = ls.inset(pts, width_px)
        kw.setdefault("chamfer_px", 0)
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            if keep is not None and not keep(i, pts[i], pts[j]):
                continue
            self.slab([pts[i], pts[j], inner[j], inner[i]], z0, z1, mat, **kw)

    def slab_mask(self, mask, z0, z1, mat=None, tol=0.6, min_px=6, **kw):
        """slab() over each part of a pixel mask (outlines()); returns the polygons."""
        polys = self.outlines(mask, tol=tol, min_px=min_px)
        for poly in polys:
            self.slab(poly, z0, z1, mat, **kw)
        return polys

    def rounded_box(self, x0, y0, x1, y1, corner_px=1.5, segments=2):
        """A box's outline (pattern px) with its corners cut round (`segments` per corner; 1 = a
        45-degree chamfer), for slab()."""
        c = max(0.0, min(corner_px, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
        if c <= 0:
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        pts = []
        for cx, cy, a0 in ((x1 - c, y0 + c, -90), (x1 - c, y1 - c, 0), (x0 + c, y1 - c, 90), (x0 + c, y0 + c, 180)):
            for k in range(segments + 1):
                a = math.radians(a0 + 90 * k / segments)
                pts.append((cx + c * math.cos(a), cy + c * math.sin(a)))
        return pts

    def ngon(self, px, py, r_px, sides=8, angle=None, ry_px=None):
        """A regular polygon's outline (pattern px), e.g. the art's octagonal discs, for slab()."""
        a0 = math.pi / sides if angle is None else angle
        ry = r_px if ry_px is None else ry_px
        return [(px + r_px * math.cos(a0 + 2 * math.pi * i / sides), py + ry * math.sin(a0 + 2 * math.pi * i / sides))
                for i in range(sides)]

    def bolts(self, points, z0, r_px=0.7, height=0.015, mat=None, sides=6):
        """Small hex bolt heads (or rivets) at `points` [(px, py), ...], standing on the plane z0."""
        mat = self.m("metal") if mat is None else mat
        for px, py in points:
            bm = bmesh.new()
            lt.block(bm, self.x(px), self.y(py), r_px * lt.PX, r_px * lt.PX, 0.0, z0 - 0.005, height + 0.005, mat, sides=sides, bevel=0.3)
            self._merge(bm)

    def coverage(self, objects, scale=2, include_plain=False, z_min=None):
        """What the objects cover seen from straight above: bool (H*scale, W*scale) over the
        pattern, a sample on where any face (projected to the ground) contains the sample's
        centre. Faces in plain materials (the island rock, `tyrian_plain`) are left out unless
        `include_plain`; with `z_min`, faces wholly below it are too."""
        out = np.zeros((self.H * scale, self.W * scale), bool)
        for o in objects:
            if o.type != "MESH":
                continue
            me, mw = o.data, o.matrix_world
            me.calc_loop_triangles()
            co = np.array([tuple(mw @ v.co) for v in me.vertices]).reshape(-1, 3)
            if not len(co):
                continue
            # pattern px (scaled), y down
            sx = (co[:, 0] / lt.PX + self.W / 2) * scale
            sy = (self.H / 2 - co[:, 1] / lt.PX) * scale
            plain = [bool(m and m.get("tyrian_plain")) for m in me.materials]
            for tri in me.loop_triangles:
                if not include_plain and plain and plain[tri.material_index]:
                    continue
                vi = list(tri.vertices)
                if z_min is not None and co[vi, 2].max() < z_min:
                    continue
                xs, ys = sx[vi], sy[vi]
                x0, x1 = max(0, int(np.floor(xs.min()))), min(out.shape[1], int(np.ceil(xs.max())) + 1)
                y0, y1 = max(0, int(np.floor(ys.min()))), min(out.shape[0], int(np.ceil(ys.max())) + 1)
                if x1 <= x0 or y1 <= y0:
                    continue
                gy, gx = np.mgrid[y0:y1, x0:x1] + 0.5
                (ax, bx, cx), (ay, by, cy) = xs, ys
                d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(d) < 1e-12:
                    continue
                l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
                l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
                inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l1 + l2 <= 1 + 1e-6)
                out[y0:y1, x0:x1] |= inside
        return out

    def top_iou(self, objects, mask, scale=2, **kw):
        """IoU of the model's top view (coverage(), plain rock left out) with `mask` (bool,
        pattern px at 1x: what the art paints for the model's own parts, e.g. purple_mask()).
        Prints it with the over/under areas; returns the IoU."""
        cov = self.coverage(objects, scale=scale, **kw)
        ref = np.kron(mask, np.ones((scale, scale), bool))
        inter, union = (cov & ref).sum(), (cov | ref).sum()
        iou = float(inter) / max(1, union)
        print(f"top view {self.name}: IoU {iou:.3f} vs the art's mask (model only {(cov & ~ref).sum() / scale ** 2:.0f} px, "
              f"art only {(ref & ~cov).sum() / scale ** 2:.0f} px)")
        return iou

    def bake_model(self, objects, size=None, samples=48, ground=None, out_dir=None, ao=(0.025, 0.16), grit=None):
        """The model's own AO/roughness bake (D65: no concept projection, `"bake": "model"`). The
        non-plain faces of `objects` are joined into one object and baked; faces in plain
        materials (the island rock, Structure.rock) go to a second object, unbaked, as they must
        look like the per-tile rock round them, but still occlude the bake. `ground` (z) adds a
        temporary plane under the footprint as an occluder only (layer 0: the HD ground the
        building stands on, D86), deleted after. Two textures, wired into every non-plain,
        non-emissive material on the "bake" UV map: colour = AO at two scales (`ao`, units) plus an
        edge lift, as a grey multiplier on the palette colour (so palette fades and filters still
        apply; open flat tops stay at the palette colour), and roughness/metal (G/B) from the
        material's own values, rougher in crevices. `size` (px) defaults to about 5 texels per
        pattern px, 1024..4096. Returns the objects to export (pass them to export(..., baked=True)).

        `grit` (a dict, None for the plain bake above): a worn, gritty finish (ASTEROID?'s station
        kit, lib_l1kit.GRIT): "floor" / "occl" / "edge" the colour multiplier's terms (floor + occl
        x AO + edge x edge lift, capped at 1: a deeper occlusion than the plain bake's 0.62 + 0.45),
        "grime" the most a grime mottle darkens by (object-space noise: stains at "scale" per unit
        and a speckle 4.5 times finer, mixed with a random value per connected piece weighted
        "island", so each brick or post wears differently: the atlas is too coarse to carry a
        finer noise on small parts), and "rough" how much the same mottle spreads the roughness (+-). Darkening only, so no face
        ever reads lighter than its palette index (highlights stay sheen).

        Cover parts (D139: objects with the custom properties `tyrian_cell` / `tyrian_when`, drawn
        per cell only while a ground enemy covers it, or only while none does) are baked in the same
        atlas but come back as their own objects, their tags kept (plain faces included, unbaked), so
        the renderer can still switch them per cell: [hard, (rock), cover parts...]."""
        import tempfile

        coll = objects[0].users_collection[0]
        hard_bm, rock_bm = bmesh.new(), bmesh.new()
        rock_bm.loops.layers.uv.new("rock")  # before the first merge, or merging drops it (Structure.rock)
        part_layer = hard_bm.faces.layers.int.new("tyrian_part")  # 0 the model, k the k-th cover part
        materials = list(self.pal.materials)
        plain = {i for i, m in enumerate(materials) if m.get("tyrian_plain")}
        covers = []  # (name, {tag: value}) per cover part, index k - 1
        for o in objects:
            if o.type != "MESH":
                continue
            tags = {k: o[k] for k in ("tyrian_cell", "tyrian_when") if k in o}
            if tags:
                covers.append((o.name, {k: (list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v) for k, v in tags.items()}))
            passes = ((hard_bm, None),) if tags else ((hard_bm, False), (rock_bm, True))
            for target, keep_plain in passes:
                bm = bmesh.new()
                bm.from_mesh(o.data)
                bm.transform(o.matrix_world)
                if keep_plain is not None:
                    drop = [f for f in bm.faces if (f.material_index in plain) != keep_plain]
                    bmesh.ops.delete(bm, geom=drop, context="FACES")
                if target is hard_bm:
                    lay = bm.faces.layers.int.get("tyrian_part") or bm.faces.layers.int.new("tyrian_part")
                    for f in bm.faces:
                        f[lay] = len(covers) if tags else 0
                tmp = bpy.data.meshes.new("tmp_split")
                bm.to_mesh(tmp)
                bm.free()
                target.from_mesh(tmp)
                bpy.data.meshes.remove(tmp)
        for o in objects:
            bpy.data.objects.remove(o, do_unlink=True)
        base = f"{SHAPES}-{self.prefix}-{self.name}"
        hard = mesh_object(f"{base}-model", hard_bm, materials, coll)
        for uv in [uv.name for uv in hard.data.uv_layers]:
            hard.data.uv_layers.remove(hard.data.uv_layers[uv])  # the rock's "rock" map, unused here
        out = [hard]
        if len(rock_bm.faces):
            rock = mesh_object(f"{base}-rock", rock_bm, materials, coll)
            if grit and not grit.get("plain_uv", True):
                # D150: the plain faces' "rock" map carries no texture here (the kit's rocks and posts
                # are flat palette colour): 8 bytes a vertex less in the GLB
                for uv in [uv.name for uv in rock.data.uv_layers]:
                    rock.data.uv_layers.remove(rock.data.uv_layers[uv])
            out.append(rock)
        else:
            rock_bm.free()
        catcher = None
        if ground is not None:
            m = 2.0
            bm = bmesh.new()
            w, h = self.W * lt.PX / 2 + m, self.H * lt.PX / 2 + m
            vs = [bm.verts.new((x, y, ground)) for x, y in ((-w, -h), (w, -h), (w, h), (-w, h))]
            bm.faces.new(vs)
            catcher = common.mesh_object(f"{base}-ao-ground", bm, [], coll)
        if size is None:
            size = int(min(4096, max(1024, 2 ** round(math.log2(math.sqrt(self.W * self.H) * 5)))))
        # Only the model (and the ground catcher) occludes: anything else in the scene, such as
        # --factory-startup's default 2x2x2 cube at the origin or an earlier export of the same run,
        # would bake its shadow in (a dark 24x24 px square round the pattern's centre).
        own = set(out) | ({catcher} if catcher is not None else set())
        others = [o for o in bpy.context.scene.objects if o not in own and not o.hide_render]
        for o in others:
            o.hide_render = True
        try:
            _bake(hard, size, samples, ao, Path(out_dir or tempfile.mkdtemp(prefix=f"{base}_bake_")),
                  skip={i for i, m in enumerate(materials) if i in plain or _emissive(m)}, grit=grit)
        finally:
            for o in others:
                o.hide_render = False
        if catcher is not None:
            bpy.data.objects.remove(catcher, do_unlink=True)
        out += _split_covers(hard, covers, coll)
        tris = sum(len(p.vertices) - 2 for p in hard.data.polygons)
        print(f"baked {base}: {size} px, {len(hard.data.polygons)} faces, {tris} triangles (+ plain rock)")
        return out

    def finish(self, objects, mask, bake=True, preview=None, ground="layer", size=None, ao=(0.025, 0.16), samples=48,
               name=None, strict=True, grit=None):
        """The hard-surface standard's last steps in one call (D141): check() (heights; `strict`
        raises), top_iou() against `mask` (bool, pattern px at 1x: what the art paints for the
        model's own parts), bake_model() (`ground` "layer": an occluder at z = 0 on layer 0, the HD
        ground the structure stands on, D86; none on layer 2, where the plain island rock occludes),
        a preview (lib_tiles.preview: the tiles | top view | game view | three-quarter, into the
        folder `preview`, as tools/build-models.sh -p passes it), and export(..., baked=bake).
        `grit`: bake_model's worn finish (lib_l1kit.GRIT). Prints and returns {"iou", "triangles", "glb_bytes"}."""
        self.check(objects, strict=strict)
        iou = self.top_iou(objects, mask)
        if ground == "layer":
            ground = 0.0 if self.layer == 0 else None
        if bake:
            objects = self.bake_model(objects, size=size, samples=samples, ground=ground, ao=ao, grit=grit)
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects if o.type == "MESH")
        if preview:
            lt.preview(self.ts, objects, self.pattern, Path(preview) / f"{SHAPES}-{self.prefix}-{name or self.name}.png", view_px=480)
        out = self.export(objects, name=name, baked=bake)
        size_b = Path(out).stat().st_size if out else 0
        print(f"finish {self.prefix}-{name or self.name}: IoU {iou:.4f}, {tris} triangles, {size_b / 1e6:.2f} MB")
        return {"iou": iou, "triangles": tris, "glb_bytes": size_b}

    def export(self, objects, name=None, baked=False):
        """Export public/models/tiles/shapesz/<prefix>-<name>.glb and src/render/tileModels/
        shapesz-<prefix>-<name>.json (with minRows unless it's None, and keepTiles if set). `baked`
        (after bake_model): the baked maps go in as WebP (the rock's lossless data textures stay
        as they are) and the model's maps.json is marked `"bake": "model"`, so
        tools/build-models.sh doesn't project a concept over it."""
        name = name or self.name
        out = lt.export_tile_model(self.ts, objects, f"{self.prefix}-{name}", self.layer, self.pattern, keep_tiles=self.keep_tiles,
                                   image_format="WEBP" if baked else "AUTO")
        if baked:
            own_bake(f"{SHAPES}-{self.prefix}-{name}")
        path = ROOT / "src" / "render" / "tileModels" / f"{SHAPES}-{self.prefix}-{name}.json"
        entry = json.loads(path.read_text())
        if self.min_rows is not None:
            entry["minRows"] = self.min_rows
        path.write_text(json.dumps(entry, indent=1) + "\n")
        return out


def _split_covers(hard, covers, coll):
    """bake_model's cover parts back out of the baked object, by its "tyrian_part" face attribute:
    one object per part (its faces, the "bake" UV map and materials kept, its tags as custom
    properties); the attribute is removed from every object."""
    out = []
    me = hard.data
    if covers:
        for k, (name, tags) in enumerate(covers, start=1):
            bm = bmesh.new()
            bm.from_mesh(me)
            lay = bm.faces.layers.int.get("tyrian_part")
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != k], context="FACES")
            if not len(bm.faces):
                bm.free()
                continue
            o = mesh_object(name, bm, list(me.materials), coll)
            for key, v in tags.items():
                o[key] = v
            out.append(o)
        bm = bmesh.new()
        bm.from_mesh(me)
        lay = bm.faces.layers.int.get("tyrian_part")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != 0], context="FACES")
        bm.to_mesh(me)
        bm.free()
    for o in [hard] + out:
        attr = o.data.attributes.get("tyrian_part")
        if attr is not None:
            o.data.attributes.remove(attr)
    bpy.context.view_layer.update()
    return out


def clear_scene():
    """Delete every object in the scene (--factory-startup's default 2x2x2 cube at the origin, or an
    earlier model of the same run). bake_model already hides other objects from its bake (D141); call
    this first anyway in a script that builds several models, so each export starts clean."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()


def own_bake(entry):
    """Mark assets/blender/textures/<entry>/maps.json `"bake": "model"` (written if missing): the
    model's script bakes its own maps, so tools/build-models.sh and texture_bake.py leave it alone
    (D50, D65). An existing file's other keys (and concept maps lib_sockets.py --maps edits) stay."""
    path = ROOT / "assets" / "blender" / "textures" / entry / "maps.json"
    meta = json.loads(path.read_text()) if path.exists() else {"name": entry, "tile": True}
    if meta.get("bake") != "model":
        meta["bake"] = "model"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(meta, indent=1) + "\n")
        print(f"{path.relative_to(ROOT)}: \"bake\": \"model\"")


def _emissive(m):
    if m is None or not m.use_nodes:
        return False
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    return bsdf is not None and bsdf.inputs["Emission Strength"].default_value > 0


def _bake(obj, size, samples, ao, out_dir, skip, grit=None):
    """AO/roughness bake of one object onto a "bake" UV map (as the enemies' bake_maps, D65), wired
    into its materials except the slots in `skip`; `grit` as Building.bake_model."""
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.002, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    tag = obj.name
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        o_ = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = o_.inputs["Surface"].links[0].from_socket if o_.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def mth(op, a, b_=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((a, b_)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    nt.links.new(val, n.inputs[k])
            return n.outputs[0]

        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = ao[0]
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = ao[1]
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.6, mth("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        mottle = None
        if grit:
            # grime: two octaves of object-space noise, 0 (clean) .. 1 (grimiest patch)
            tc = node("ShaderNodeTexCoord")
            nz = node("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = grit.get("scale", 6.0)
            nz.inputs["Detail"].default_value = 6.0
            nz.inputs["Roughness"].default_value = 0.62
            nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
            nz2 = node("ShaderNodeTexNoise")
            nz2.inputs["Scale"].default_value = grit.get("scale", 6.0) * 4.5
            nz2.inputs["Detail"].default_value = 3.0
            nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
            # stains (the coarse octave), speckle (the fine one), each 0..1 above its noise's middle,
            # and a random value per connected piece (a brick, a post: each plate worn differently)
            stain = mth("MINIMUM", mth("MAXIMUM", mth("MULTIPLY", mth("SUBTRACT", nz.outputs["Fac"], 0.48), 6.0), 0.0), 1.0)
            speck = mth("MINIMUM", mth("MAXIMUM", mth("MULTIPLY", mth("SUBTRACT", nz2.outputs["Fac"], 0.48), 6.0), 0.0), 1.0)
            isl = geo.outputs["Random Per Island"]
            wi = grit.get("island", 0.0)
            mottle = mth("MINIMUM", mth("ADD", mth("ADD", mth("MULTIPLY", stain, 0.6 * (1 - wi)), mth("MULTIPLY", speck, 0.4 * (1 - wi))),
                                        mth("MULTIPLY", isl, wi)), 1.0)
        if mode == "colour":
            if grit:
                val = mth("MINIMUM", mth("ADD", mth("ADD", grit["floor"], mth("MULTIPLY", occl, grit["occl"])),
                                         mth("MULTIPLY", edge, grit["edge"])), 1.0)
                val = mth("MULTIPLY", val, mth("SUBTRACT", 1.0, mth("MULTIPLY", mottle, grit["grime"])))
            else:
                val = mth("MINIMUM", mth("ADD", mth("ADD", 0.62, mth("MULTIPLY", occl, 0.45)), mth("MULTIPLY", edge, 0.12)), 1.0)
            for k in range(3):
                nt.links.new(val, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.14)))
            if grit:
                r = mth("ADD", r, mth("MULTIPLY", mth("SUBTRACT", mottle, 0.5), 2.0 * grit["rough"]))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
        nt.links.new(comb.outputs[0], em.inputs["Color"])
        o_ = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], o_.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=8, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            o_ = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], o_.inputs["Surface"])
        out_dir.mkdir(parents=True, exist_ok=True)
        img.filepath_raw = str(out_dir / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i, m in enumerate(mats):
        if i in skip:
            continue
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
