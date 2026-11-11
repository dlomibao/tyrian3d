"""DELIANI's girder track (shapesz.dat 576-579, 586-589, 596-599 on layer 1, background 2; maps 1-5 and
3-11): one model per tile, built in context (lib_delbld.py; DECISIONS.md D34, D83, D65).

What it is: an elevated steel girder track drawn over the ground vehicles (background 2's middle pass),
a network of straights (586 vertical, 587 horizontal), corners (588 ┌, 589 ┐, 578 └, 579 ┘), tees
(596 ┬, 597 ┴, 598 ├, 599 ┤) and crossings (576, 577). Each piece is a lattice deck, a steel plate
with rows of rectangular windows through which the ground shows, carried between two box rails that
run along the track's closed sides and turn its corners; where two open sides meet (the inside of a
corner or a junction) the rails end in a short L that joins the rails of the branches.

From the pixels, per tile (1x, 24x28):
- windows: the transparent pixels; the near-black ring round each (palette 1) is not paint but the
  window's depth: a lip 0.09 below the deck's top; in game the step and its occlusion stayed as light
  as the deck, so the lip's top takes the ramp's darkest steel index (96), the window's dark recess;
- rails: on a closed side (its edge row or column all near-black) rows 1-4 (top), 23-26 (bottom),
  columns 1-3 (left) or 20-22 (right), a box beam standing proud of the deck with bevelled edges; the
  near-black line outside it is the girder's outer lip (like the windows'), not an outline; the bright
  line along each rail is sheen on the bevel;
- the inside of a corner: an L of the same beams, rows 1-4 x columns 0-3 and rows 0-4 x columns 1-3
  (rotated per corner), which meets the branches' rails at the tile edges;
- colours: the deck and the rails each take the median palette index of their pixels (the shading and
  highlights dropped), from the steel-blue ramp 96-108.

Heights: the deck is 0.12 thick (z -0.12..0) and the rails stand 0.22 above it, so the whole track is
within -0.12..+0.22 of its pass height (0.9), well clear of the ground enemies (0.45) it passes over.

Run: tools/build-models.sh -j 2 assets/blender/tiles/delbld_girders.py
     Blender -b --factory-startup -P delbld_girders.py -- [--no-bake] [tile ...]
"""

import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_delbld as kit  # noqa: E402
import lib_tiles as lt  # noqa: E402

ROOT = common.repo_root(__file__)
SHAPES = "shapesz"
LAYER = 1
TILES = (576, 577, 578, 579, 586, 587, 588, 589, 596, 597, 598, 599)

DECK_BOTTOM, DECK_TOP = -0.12, 0.0
WINDOW_LIP = -0.09     # the top of the lip round each window and along the girder's outer edge
RAIL_TOP = 0.22
RAIL_BEVEL, DECK_BEVEL = 0.05, 0.010
STEEL = dict(metallic=0.12, roughness=0.45)   # satin, as the flagship models (D65): metal darkens the diffuse


def closed_sides(px):
    """The sides of a tile the track doesn't continue through: its edge row or column is all ink."""
    return {
        "U": bool(np.all(px[0] <= 1)),
        "D": bool(np.all(px[-1] <= 1)),
        "L": bool(np.all(px[:, 0] <= 1)),
        "R": bool(np.all(px[:, -1] <= 1)),
    }


def rail_mask(px):
    """The rails of one tile (1x pixels), from which of its sides are closed."""
    h, w = px.shape
    closed = closed_sides(px)
    m = np.zeros((h, w), dtype=bool)
    if closed["U"]:
        m[1:5, :] = True
    if closed["D"]:
        m[23:27, :] = True
    if closed["L"]:
        m[:, 1:4] = True
    if closed["R"]:
        m[:, 20:23] = True
    # The inside of a corner between two open sides: an L joining the branches' rails.
    for v, hz in (("U", "L"), ("U", "R"), ("D", "L"), ("D", "R")):
        if closed[v] or closed[hz]:
            continue
        rows = slice(1, 5) if v == "U" else slice(23, 27)
        rows_long = slice(0, 5) if v == "U" else slice(23, 28)
        cols = slice(0, 4) if hz == "L" else slice(20, 24)
        cols_short = slice(1, 4) if hz == "L" else slice(20, 23)
        m[rows, cols] = True
        m[rows_long, cols_short] = True
    return m & (px > 0)


def neighbours_of(ts, n):
    closed = closed_sides(kit.pixels(ts, n))
    return {s: (-1 if closed[s] else kit.usual_neighbour(ts, n, s, allowed=set(TILES))) for s in "LRUD"}


def build(ts, n, coll, bake_on):
    cells = kit.context_cells(ts, n, neighbours_of(ts, n))
    grid = kit.context_grid(ts, cells)
    frame = lt.Frame(cells, 1)
    h, w = grid.shape
    empty = grid < 0
    hole = grid == 0
    solid = grid > 0
    pad = np.pad(empty, 1, constant_values=True)
    near_empty = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    outline = (grid == 1) & near_empty
    hp = np.pad(hole, 1, constant_values=False)
    near_hole = np.zeros_like(hole)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            near_hole |= hp[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx]
    ring = (grid == 1) & near_hole & ~outline

    rails = np.zeros((h, w), dtype=bool)
    for r, row in enumerate(cells):
        for c, t in enumerate(row):
            if t >= 0:
                rails[r * lt.TILE_H:(r + 1) * lt.TILE_H, c * lt.TILE_W:(c + 1) * lt.TILE_W] = rail_mask(kit.pixels(ts, t))
    deck = solid
    centre = grid[lt.TILE_H:2 * lt.TILE_H, lt.TILE_W:2 * lt.TILE_W]
    cr = rails[lt.TILE_H:2 * lt.TILE_H, lt.TILE_W:2 * lt.TILE_W]
    cring = ring[lt.TILE_H:2 * lt.TILE_H, lt.TILE_W:2 * lt.TILE_W] | outline[lt.TILE_H:2 * lt.TILE_H, lt.TILE_W:2 * lt.TILE_W]
    steel = set(range(96, 109))
    deck_index = kit.region_index(ts, centre[(centre > 1) & ~cr & ~cring], prefer=steel)
    rail_index = kit.region_index(ts, centre[(centre > 1) & cr], prefer=steel) or deck_index

    mats = kit.Mats(ts, f"g{n}", **STEEL)
    DECK = mats(deck_index)
    # The lip round a window is the window's recess: in game (D53) a 0.09 step with its occlusion
    # stays as light as the deck, while the art's ring is the darkest thing on the girder, so the
    # lip takes the ramp's darkest index the art uses round its windows (96; the ring itself is 1).
    LIP = mats(96)
    RAIL = mats(rail_index, metallic=0.18, roughness=0.32)   # smoother: the art's bright rail lines are its sheen

    # The deck plate, and below its top the windows' lips and the girder's outer lip: steps down, so
    # the window reads by its depth and its occlusion.
    lip = ring | outline
    bm = bmesh.new()
    lt.mask_slab(bm, deck & ~lip, frame, DECK_BOTTOM, DECK_TOP, DECK)
    kit.tidy(bm)
    kit.bevel(bm, DECK_BEVEL, segments=1, angle=50)
    lb = bmesh.new()
    lt.mask_slab(lb, lip, frame, DECK_BOTTOM, WINDOW_LIP, LIP, mat_side=DECK, walls=lip | (deck & ~lip))
    kit.tidy(lb)
    me = kit.bpy.data.meshes.new("_lips")
    lb.to_mesh(me)
    lb.free()
    bm.from_mesh(me)
    kit.bpy.data.meshes.remove(me)
    rb = bmesh.new()
    lt.mask_slab(rb, rails, frame, DECK_TOP - 0.02, RAIL_TOP, RAIL)
    kit.tidy(rb)
    kit.bevel(rb, RAIL_BEVEL, segments=2, angle=50)
    me = kit.bpy.data.meshes.new("_rails")
    rb.to_mesh(me)
    rb.free()
    bm.from_mesh(me)
    kit.bpy.data.meshes.remove(me)
    name = f"delbld-girder-{n}"
    obj = kit.finish(ts, coll, name, bm, mats, LAYER, bake_on=bake_on)
    return obj


def main():
    ts = lt.Tileset(ROOT, SHAPES, layer=LAYER)
    only, bake_on = kit.build_args()
    preview = lt.preview_arg()
    coll = common.reset_collection("delbld_girders")
    for n in TILES:
        if only and n not in only:
            continue
        obj = build(ts, n, coll, bake_on)
        kit.export(ts, [obj], f"delbld-girder-{n}", LAYER, n, image_format="WEBP" if bake_on else "AUTO")
        if preview:
            lt.preview(ts, [obj], [[n]], Path(preview) / f"{SHAPES}-delbld-girder-{n}.png", view_px=240)


main()
