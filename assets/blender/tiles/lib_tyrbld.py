"""Shared parts for the structures of Episode 1's first level, TYRIAN (map 1-9, shapesz.dat): 3D
versions of the bunkers and wreck on the ground (layer 0) and of the fortress, bridges, purple carved
blocks, gates, drums, lava pits and craters on the floating islands of background 3 (layer 2), after
the Gemini concepts assets/blender/features/concepts/tyr-<name>.jpg (DECISIONS.md D34, D44).

Built on lib_l1bld.py (map 1-3's buildings: its Building's terraced deck, rocks, capsules, hatches,
walls, domes, check and export all apply). `Structure(name)` takes its pattern, enemies and matching
from the plan, assets/blender/tiles/tyrbld_patterns.json (tests/render/remaster.test.ts checks the
plan against every level), and adds TYRIAN's kits:

- layer 2's frame (below) and the rock of the islands around a structure's own parts: `rock()`
  rebuilds the per-tile look of shapesz_bg3.py (a dark slab with a boulder per painted stone, the
  hanging underside of tiles 140-142) for any pixels of the pattern, because layer-2 structures
  replace their tiles; layer-0 ones stand on their tiles, which stay drawn;
- the metal walkway (fortress, bridges): `walkway()` decks the walkway tiles' pixels (their own
  outline, so rounded corners and T-junctions come from the art) with a raised rail along the
  outline, open where the walkway runs off the map's edge; `rail_studs()` adds the studs;
- purple carved stone (cross, orb, 2x2/2x3/2x5): `purple_mask()`, `carved()` (a raised, chamfered
  slab), `knob()` (the octagonal bosses round the edge), `blobs()` (ellipses of painted parts, to
  place knobs from the art);
- `lathe()`: a surface of revolution along X or Y (drums, domes, orbs, pipes); `light()`: an
  emissive dome or lens;
- `export()`: also writes the plan's variant entries and removes the per-tile entries (and their
  .glb) the structure replaces, then prints the concept, bake and render commands.

Units and frame as lib_tiles / lib_l1bld: 1 unit = 12 tile px, origin at the pattern's centre, X
right, Y up (screen up), Z up. Pixel coordinates (px, py) are in the pattern at 1x, top-left
(0, 0); `s.x(px)`, `s.y(py)` convert. Heights are relative to the layer's plane (the model is placed
at its draw pass's height, and scaled about that plane with the pass, D5/D6):

- layer 0 (ground, z = 0 the ground; ground enemies drawn at 0.45): as lib_l1bld: under an enemy
  cell the top stays in ENEMY_MIN..ENEMY_MAX (0.30..0.38), elsewhere up to TALL_MAX 0.80;
- layer 2 (background 3 at 2.1; top enemies at 2.5, player shots at 2.9): z = 0 is the islands'
  surface (the per-tile rock slabs' top; their boulders reach about 0.2, the walkway deck is at
  0.06). Under an enemy cell the top stays in L2_ENEMY_MIN..L2_ENEMY_MAX (0.22..0.33: the enemy's
  model sits about 0.4 above, scaled); elsewhere up to L2_TALL_MAX 0.70; the bottom no lower than
  L2_Z_MIN -0.90 (slabs end at L2_SLAB_BOTTOM -0.30, the hanging undersides lower).
  Structures the plan marks `over` (rows 199-324: bridges, gates, drums) are drawn in the
  Background3Over pass at 4.15 late in the level, just under enemies at 4.55 and over the player:
  their tops stay under L2_OVER_MAX 0.38.
`check()` enforces these. Colours are palette materials (level palette 5's indices: PAL_T below,
or any index from the tiles' pixels via `s.m(index)` / `s.dominant(mask)`).
"""

import json
import math
import random
from pathlib import Path

import bmesh
import bpy
import numpy as np

import common
import lib_l1bld as lb
import lib_tiles as lt

ROOT = lb.ROOT
SHAPES = lb.SHAPES
PLAN_PATH = Path(__file__).resolve().parent / "tyrbld_patterns.json"
PLAN = json.loads(PLAN_PATH.read_text())["structures"]
MAP_WIDTHS = (14, 14, 15)

# Layer 2's frame (see the module's docstring).
L2_DECK = 0.06
L2_ENEMY_MAX = 0.33
L2_ENEMY_MIN = 0.22
L2_RIM_MAX = 0.30
L2_TALL_MAX = 0.70
L2_OVER_MAX = 0.38
L2_SLAB_BOTTOM = -0.30
L2_Z_MIN = -0.90

#: TYRIAN's tiles by kind (shapesz_bg3.py).
WALK = {180, 181, 183, 184, 191, 192, 193, 194, 200, 201}
PURPLE = {149, 155, 156, 157, 158, 159, 165, 167, 168, 169, 175, 176, 177}
MACHINE = {160, 161, 170, 171}
GATE = {185, 186, 187, 188, 195, 196, 197, 198}
ROCK = {120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 140, 141, 142, 150, 151, 152}
UNDERSIDE = {140, 141, 142}
UNDERSIDE_DROP = 0.55  # how far the underside tiles' face hangs below the slab (shapesz_bg3.py)

#: Palette 5 indices of the common parts (ramps of 16: 0-15 greys, 16-31 brass/brown, 48-63 blue,
#: 80-95 purple, 112-127 red, 160-175 tan). lib_l1bld's kinds (pave, wall, rim, channel, red,
#: red_dark, dark, metal) are kept so its Building methods work unchanged.
PAL_T = {
    "pave": 5, "wall": 4, "rim": 5, "channel": 19, "red": 115, "red_dark": 112, "dark": 2, "metal": 9,
    "walk": 5,  # walkway deck (69 grey)
    "walk_dark": 4,
    "rail": 9,  # the walkway's raised rim and studs (121 grey); 11 for highlights
    "rock": 6, "rock_dark": 2, "tan": 166,
    "purple": 88, "purple_dark": 86, "purple_light": 90,
    "brass": 21, "brass_dark": 18, "brass_light": 24,
    "white": 11,  # the gates' stone blocks
    "blue": 52,  # the orb, emissive
    "lava": 115,  # emissive
}
_KIND_DEFAULTS = {
    "red": dict(emission_strength=2.5, roughness=0.3), "lava": dict(emission_strength=2.0, roughness=0.5),
    "blue": dict(emission_strength=0.8, roughness=0.2, metallic=0.1),
    "metal": dict(metallic=0.6, roughness=0.4), "rail": dict(metallic=0.6, roughness=0.35),
    "walk": dict(metallic=0.5, roughness=0.5), "walk_dark": dict(metallic=0.5, roughness=0.5),
    "brass": dict(metallic=0.7, roughness=0.35), "brass_dark": dict(metallic=0.6, roughness=0.45),
    "brass_light": dict(metallic=0.7, roughness=0.3),
    "red_dark": dict(metallic=0.3, roughness=0.5), "dark": dict(roughness=0.9),
    "purple": dict(roughness=0.6), "purple_dark": dict(roughness=0.65), "purple_light": dict(roughness=0.55),
}


class Structure(lb.Building):
    """One TYRIAN structure (an entry of tyrbld_patterns.json): pattern, pixels, masks, geometry.

    Attributes as lib_l1bld.Building (ts, pattern, rows, cols, W, H, grid, cover, footprint,
    enemy_mask, pal, height, mat, parts) plus plan (the entry), layer, over and the frame's limits
    (deck, enemy_min, enemy_max, rim_max, tall_max, z_min, slab_bottom)."""

    prefix = "tyrbld"

    def __init__(self, name, tag=None):
        plan = PLAN[name]
        self.plan = plan
        self.layer = plan["layer"]
        self.over = plan.get("over", False)
        self.min_rows = plan.get("minRows")
        self.keep_tiles = plan.get("keepTiles")
        if self.layer == 2:
            self.deck, self.enemy_min, self.enemy_max = L2_DECK, L2_ENEMY_MIN, L2_ENEMY_MAX
            self.rim_max, self.slab_bottom, self.z_min = L2_RIM_MAX, L2_SLAB_BOTTOM, L2_Z_MIN
            self.tall_max = L2_OVER_MAX if self.over else L2_TALL_MAX
        tiles = plan["tiles"]
        spec = dict(pattern=tiles, cover_rows=(0, len(tiles) - 1), enemies=[tuple(c) for c in plan["enemies"]],
                    concept=plan["concepts"][0]["name"] if plan["concepts"] else None)
        super().__init__(name, tag=tag, spec=spec)
        self._rng = random.Random(f"tyrbld-{name}")
        self.blank()

    # Masks ---------------------------------------------------------------------------------------

    def make_footprint(self):
        """Layer 2: every painted pixel of the pattern's cells (index 0 is see-through there);
        layer 0: as lib_l1bld (the painted platform, closed). Restrict it with set_footprint()."""
        if self.layer == 2:
            return self.cover & (self.grid >= 0)
        return super().make_footprint()

    def set_footprint(self, mask):
        """What the deck may cover (bool, pattern px), e.g. a bunker's own outline on its dirt."""
        self.footprint = mask & self.cover
        self.blank()

    def blank(self):
        """Empty deck heights (nan) and materials (-1): set them with set_region / raise_box /
        walkway / carved, then terrace()."""
        self.height = np.full((self.H, self.W), np.nan, dtype=np.float32)
        self.mat = np.full((self.H, self.W), -1, dtype=np.int32)

    def cells_mask(self, tiles=None, cells=None):
        """Pixels (bool, pattern px) of the cells holding one of `tiles`, or the (row, col) `cells`."""
        m = np.zeros((self.H, self.W), bool)
        for r, row in enumerate(self.pattern):
            for c, t in enumerate(row):
                if t < 0 or (tiles is not None and t not in tiles) or (cells is not None and (r, c) not in cells):
                    continue
                m[r * lt.TILE_H:(r + 1) * lt.TILE_H, c * lt.TILE_W:(c + 1) * lt.TILE_W] = True
        return m & self.cover

    def ramp_mask(self, *ramps):
        """Painted pixels whose palette index is in one of the ramps (index >> 4): 0 greys, 1 brass,
        3 blue, 5 purple, 7 red, 10 tan."""
        return (self.grid >= 0) & np.isin(np.maximum(self.grid, 0) >> 4, ramps)

    def lum(self):
        return lt.lum_of(self.ts, self.grid)

    def dominant(self, mask, prefer="mode"):
        """The palette index a region is painted in (lib_tiles.dominant)."""
        return lt.dominant(self.grid[mask & (self.grid >= 0)], self.ts.lum, prefer=prefer)

    def ellipse_mask(self, cx, cy, rx, ry):
        yy, xx = np.mgrid[0:self.H, 0:self.W] + 0.5
        return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0

    def blobs(self, mask, min_px=12):
        """Ellipses (cx, cy, rx, ry, angle; px, angle in screen terms) of the 4-connected parts of
        `mask`: where the art paints knobs, lights, panels."""
        return [lt.ellipse(ys, xs) for ys, xs in lt.components(mask) if len(ys) >= min_px]

    # Materials -----------------------------------------------------------------------------------

    def m(self, kind_or_index, **kw):
        """Material slot for a PAL_T kind ("walk", "purple", "brass", "red", ...) or a palette
        index (pick shades from the tiles: self.dominant(mask))."""
        if isinstance(kind_or_index, str):
            kw = {**_KIND_DEFAULTS.get(kind_or_index, {}), **kw}
            return self.pal(PAL_T[kind_or_index], **kw)
        return self.pal(kind_or_index, **kw)

    # Rock (layer 2's islands) --------------------------------------------------------------------

    def rock(self, cells=None, exclude=None, cut=None, bottom=None, boulders=True, max_height=0.2):
        """The islands' rock as the per-tile models draw it (shapesz_bg3.py), for the painted
        pixels of `cells` ((row, col) list; default every cell): a slab from `bottom` (default
        slab_bottom) up to z = 0, dark between the stones, except where `cut` (bool, pattern px at
        1x: a hole for a part that goes deeper); a rounded boulder for each painted stone mostly
        outside `exclude` (bool, 1x: where the structure's own parts are); and on the underside
        tiles (140-142) the face that hangs down with the roots painted on it. Adds to self.parts."""
        bottom = self.slab_bottom if bottom is None else bottom
        k2 = np.ones((2, 2), bool)
        ex2 = np.kron(np.zeros((self.H, self.W), bool) if exclude is None else exclude, k2)
        cut2 = np.kron(np.zeros((self.H, self.W), bool) if cut is None else cut, k2)
        g2 = self.ts.grid(self.pattern, 2)
        th, tw = lt.TILE_H * 2, lt.TILE_W * 2
        cells = [(r, c) for r, row in enumerate(self.pattern) for c, t in enumerate(row) if t >= 0] if cells is None else cells
        region = np.zeros(g2.shape, bool)
        for r, c in cells:
            region[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = True
        region &= (g2 >= 0) & ~cut2
        if not region.any():
            return
        lum = lt.lum_of(self.ts, g2)
        dark = lt.dominant(g2[region & (lum <= 0.22)], prefer="mode")
        DARK = self.pal(3 if dark is None else dark)
        drop = np.zeros(g2.shape)
        cell_mat = {}
        for r, c in cells:
            if self.pattern[r][c] not in UNDERSIDE:
                continue
            ys, xs = slice(r * th, (r + 1) * th), slice(c * tw, (c + 1) * tw)
            own, lo = g2[ys, xs], lum[ys, xs]
            opaque = own >= 0
            start = np.full(tw, th * 0.3)
            for x in range(tw):
                col = np.nonzero(opaque[:, x] & (lo[:, x] > 0.22))[0]
                col = col[col < th * 0.55]
                if len(col):
                    start[x] = col.max() + 1
            d = np.zeros((th, tw))
            for y in range(th):
                d[y, :] = -UNDERSIDE_DROP * np.clip((y - start) / max(1.0, th - start.min()), 0, 1) ** 0.8
            drop[ys, xs] = d
            hang = opaque & (d < -0.01)
            if hang.any():
                snap = lt.Snapper(self.ts, own[hang], limit=5)
                for y, x in zip(*np.nonzero(hang)):
                    cell_mat[(c * tw + x, r * th + y)] = self.pal(snap(own[y, x]))
        bm = bmesh.new()
        lt.mask_slab(bm, region, lt.Frame(self.pattern, 2), bottom + min(0.0, drop.min()), 0.0,
                     lambda x, y: cell_mat.get((x, y), DARK), DARK, top_height=np.where(region, drop, 0.0))
        lt.dissolve_coplanar(bm)
        self._merge(bm)
        if not boulders:
            return
        chosen = []
        for r, c in cells:
            n = self.pattern[r][c]
            cex = ex2[r * th:(r + 1) * th, c * tw:(c + 1) * tw]
            cdrop = drop[r * th:(r + 1) * th, c * tw:(c + 1) * tw]

            def keep(ys, xs, cex=cex, cdrop=cdrop):
                inside = (ys >= 0) & (ys < th) & (xs >= 0) & (xs < tw)
                yi, xi = ys[inside], xs[inside]
                if len(yi) == 0:
                    return True
                return (~cex[yi, xi] & (cdrop[yi, xi] > -0.05)).mean() > 0.6

            sb = bmesh.new()
            lt.boulders(self.ts, n, self.pal, sb, keep=keep, gap=0.22, quantile=0.3, max_height=max_height, chosen=chosen)
            # lt.boulders builds round the tile's own centre: move it to the cell's.
            ox = self.x((c + 0.5) * lt.TILE_W)
            oy = self.y((r + 0.5) * lt.TILE_H)
            for v in sb.verts:
                v.co.x += ox
                v.co.y += oy
            self._merge(sb)

    # Walkways (fortress, bridges) ----------------------------------------------------------------

    def walkway(self, mask=None, deck=None, rail_px=3, rail_h=0.05, mat=None, rail_mat=None, open_edges=None):
        """The walkway deck: the walkway tiles' painted pixels (or `mask`) at `deck` (default
        self.deck) with a rail `rail_px` wide, `rail_h` higher, along the outline: the art's own
        outline, so rounded corners and T-junctions follow the tiles. `open_edges` ("left",
        "right", "top", "bottom"; default: the sides where the pattern meets the map's edge) get
        no rail, as the walkway runs on off the map. Sets the deck's heights and materials (call
        terrace() after); returns the walkway mask."""
        deck = self.deck if deck is None else deck
        walk = (self.cells_mask(WALK) & self.footprint) if mask is None else mask & self.footprint
        if open_edges is None:
            c0, c1 = self.plan["map"]["cols"]
            open_edges = [e for e, on in (("left", c0 == 0), ("right", c1 == MAP_WIDTHS[self.layer] - 1)) if on]
        pad = rail_px + 1
        big = np.pad(walk, pad, mode="constant")
        if "left" in open_edges:
            big[pad:-pad, :pad] = walk[:, :1]
        if "right" in open_edges:
            big[pad:-pad, -pad:] = walk[:, -1:]
        if "top" in open_edges:
            big[:pad, pad:-pad] = walk[:1, :]
        if "bottom" in open_edges:
            big[-pad:, pad:-pad] = walk[-1:, :]
        d = lb.depth(big, limit=rail_px + 2)[pad:-pad, pad:-pad]
        rail = walk & (d <= rail_px)
        self.set_region(walk, deck, self.m("walk") if mat is None else mat)
        self.set_region(rail, deck + rail_h, self.m("rail") if rail_mat is None else rail_mat)
        self._walk, self._rail = walk, rail
        return walk

    def rail_studs(self, spacing=6.0, radius_px=1.6, height=0.03, mat=None):
        """Studs along the walkway's rail (after walkway()), every `spacing` px."""
        rail = getattr(self, "_rail", None)
        if rail is None or not rail.any():
            return 0
        d = lb.depth(rail)
        core = rail & (d == d[rail].max())
        taken = []
        for y, x in zip(*np.nonzero(core)):
            if all((x - tx) ** 2 + (y - ty) ** 2 >= spacing ** 2 for tx, ty in taken):
                taken.append((x, y))
        for x, y in taken:
            z0 = float(self.height[y, x])
            self.dome(x + 0.5, y + 0.5, radius_px, radius_px, z0 - 0.005, height, self.m("rail") if mat is None else mat, sides=8, rings=2)
        return len(taken)

    # Purple carved stone -------------------------------------------------------------------------

    def purple_mask(self):
        """The purple stone's pixels (ramp 5, small gaps closed, specks dropped)."""
        m = self.footprint & self.ramp_mask(5)
        return lb.drop_small(lb.open_(lb.close(m, 1), 1), 20)

    def carved(self, mask, z, mat=None, chamfer_px=2, chamfer_drop=0.03, edge_mat=None):
        """A raised carved slab over `mask`: top at z, a chamfer step `chamfer_px` wide round it
        `chamfer_drop` lower (sets the deck; terrace() after)."""
        mat = self.m("purple") if mat is None else mat
        inner = lb.erode(mask, chamfer_px) if chamfer_px else mask
        self.set_region(mask, z - chamfer_drop, mat if edge_mat is None else edge_mat)
        self.set_region(inner, z, mat)
        return inner

    def knob(self, px, py, r_px, z0, z1, mat=None, sides=8, angle=None, bevel=0.35, ry_px=None):
        """An octagonal carved boss (bevelled block) centred at (px, py), radius r_px (ry_px), from
        z0 up to z1."""
        mat = self.m("purple") if mat is None else mat
        bm = bmesh.new()
        lt.block(bm, self.x(px), self.y(py), r_px * lt.PX, (ry_px or r_px) * lt.PX,
                 math.pi / sides if angle is None else angle, z0, z1 - z0, mat, sides=sides, bevel=bevel)
        self._merge(bm)

    # Round parts, prisms and lights ------------------------------------------------------------

    def prism(self, profile, a0, a1, axis="x", mat=None, mats=None):
        """A closed prism: the polygon `profile` [(b_px, z), ...] extruded along the axis from a0 to
        a1 px. axis "x": b is the pixel row (py) and the prism runs from px a0 to a1; axis "y": b
        is the pixel column (px) and it runs from py a0 to a1. `mats`, one per profile edge (edge
        i joins point i and i+1), overrides `mat` on the sides; the ends take `mat`. For bodies,
        housings, bars, straps: a drum's lid and front face are one profile."""
        mat = self.m("brass") if mat is None else mat
        bm = bmesh.new()

        def co(b, z, a):
            return (self.x(a), self.y(b), z) if axis == "x" else (self.x(b), self.y(a), z)

        e0 = [bm.verts.new(co(b, z, a0)) for b, z in profile]
        e1 = [bm.verts.new(co(b, z, a1)) for b, z in profile]
        n = len(profile)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((e0[i], e0[j], e1[j], e1[i])).material_index = mats[i] if mats else mat
        bm.faces.new(e0).material_index = mat
        bm.faces.new(list(reversed(e1))).material_index = mat
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self._merge(bm)

    # Round parts and lights ----------------------------------------------------------------------

    def lathe(self, profile, px, py, axis="x", z=0.0, mat=None, sides=16, cap=True, squash=1.0, mats=None, smooth=True):
        """A surface of revolution: `profile` [(t_px, r_px), ...] along the axis ("x": screen
        right, "y": screen down, "z": up) from the point (px, py) at height z, radius r_px at each
        station (0 closes to a point). `squash` scales the vertical radius (a drum lying on the
        deck). `mats`, one per segment, overrides `mat`. Ends closed when `cap`."""
        mat = self.m("brass") if mat is None else mat
        bm = bmesh.new()
        cx, cy = self.x(px), self.y(py)
        rings = []
        for t, r in profile:
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                u, w = r * math.cos(a) * lt.PX, r * math.sin(a) * lt.PX
                if axis == "x":
                    co = (cx + t * lt.PX, cy + u, z + w * squash)
                elif axis == "y":
                    co = (cx + u, cy - t * lt.PX, z + w * squash)
                else:
                    co = (cx + u, cy + w, z + t * lt.PX)
                ring.append(bm.verts.new(co))
            rings.append(ring)
        for k, (a_, b_) in enumerate(zip(rings, rings[1:])):
            mi = mats[k] if mats else mat
            for i in range(sides):
                j = (i + 1) % sides
                bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = mi
        if cap:
            for ring, mi in ((rings[0], mats[0] if mats else mat), (rings[-1], mats[-1] if mats else mat)):
                try:
                    bm.faces.new(ring).material_index = mi
                except ValueError:
                    pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self._merge(bm, smooth=smooth)

    def light(self, px, py, r_px, z0, height=None, kind="red", strength=None, ry_px=None, sides=12):
        """A glowing lens: a dome of an emissive material ("red", "lava", "blue" or a palette
        index) on the plane z0."""
        kw = {} if strength is None else {"emission_strength": strength}
        if isinstance(kind, str):
            mat = self.m(kind, **kw)
        else:
            mat = self.pal(kind, emission_strength=2.5 if strength is None else strength, roughness=0.3)
        self.dome(px, py, r_px, ry_px or r_px, z0, r_px * lt.PX * 0.7 if height is None else height, mat, sides=sides, rings=3)

    # Export --------------------------------------------------------------------------------------

    def objects(self, deck_bm=None, coll=None):
        """The structure's objects: the terraced deck (`deck_bm`, or terrace() if any deck height
        was set) and the parts."""
        if deck_bm is not None or not np.isnan(self.height).all():
            return super().objects(deck_bm, coll)
        coll = coll or common.reset_collection(f"{SHAPES}-{self.prefix}-{self.name}")
        bmesh.ops.recalc_face_normals(self.parts, faces=self.parts.faces)
        return [lb.mesh_object(f"{SHAPES}-{self.prefix}-{self.name}-parts", self.parts, self.pal.materials, coll)]


    def export(self, objects, name=None):
        """lib_l1bld's export (public/models/tiles/shapesz/tyrbld-<name>.glb, src/render/tileModels/
        shapesz-tyrbld-<name>.json with the plan's minRows / keepTiles), then the plan's variants,
        and the replaced per-tile entries removed."""
        name = name or self.name
        out = super().export(objects, name)
        model = f"tiles/{SHAPES}/{self.prefix}-{name}"
        tm = ROOT / "src" / "render" / "tileModels"
        for v in self.plan.get("variants", []):
            entry = {"model": model, "shapes": self.ts.file, "layer": self.layer, "tiles": v["tiles"], "offset": v["offset"]}
            if self.min_rows is not None:
                entry["minRows"] = self.min_rows
            if self.keep_tiles is not None:
                entry["keepTiles"] = self.keep_tiles
            path = tm / f"{SHAPES}-{self.prefix}-{v['name']}.json"
            path.write_text(json.dumps(entry, indent=1) + "\n")
            print(f"variant {path.name}: {v['tiles']} offset {v['offset']}")
        for old in self.plan.get("replaces", []):
            for path in (tm / f"{old}.json", ROOT / "public" / "models" / "tiles" / SHAPES / f"{old[len(SHAPES) + 1:]}.glb"):
                if path.exists():
                    path.unlink()
                    print(f"removed {path.relative_to(ROOT)} (replaced by {model})")
        print("next:\n" + "\n".join(commands(name)))
        return out


def commands(name):
    """The concept-maps, bake and render commands for a structure (as `next:` after export)."""
    plan = PLAN[name]
    entry = f"{SHAPES}-tyrbld-{name}"
    parts = plan["concepts"]
    if len(parts) == 1:
        span = ",".join(str(v) for v in parts[0]["span"])
        cm = f"tile:{entry} --concept {parts[0]['name']} --span {span}"
    else:
        cm = f"tile:{entry} " + " ".join(f"--part {p['name']}:{','.join(str(v) for v in p['span'])}" for p in parts)
    return [
        f"  /Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python tools/concept_maps.py {cm}",
        f"  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:{entry}",
        f"  /Applications/Blender.app/Contents/MacOS/Blender --background --python <scratchpad>/tyrbld/render.py -- {name} <outdir>",
    ]

