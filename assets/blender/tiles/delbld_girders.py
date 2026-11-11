"""DELIANI's girder track (shapesz.dat 576-579, 586-589, 596-599 on layer 1, background 2; maps 1-5 and
3-11): one model per tile, built in context (lib_delbld.py; DECISIONS.md D34, D83, D65).

What it is: an elevated steel girder track drawn over the ground vehicles (background 2's middle pass),
a network of straights (586 vertical, 587 horizontal), corners (588 ┌, 589 ┐, 578 └, 579 ┘), tees
(596 ┬, 597 ┴, 598 ├, 599 ┤) and crossings (576, 577). Each piece is a lattice deck, a steel plate
with rows of rectangular windows through which the ground shows, carried between two box rails that
run along the track's closed sides and turn its corners; where two open sides meet (the inside of a
corner or a junction) the rails end in a short L that joins the rails of the branches.

From the pixels, per tile (1x, 24x28):
- windows: the transparent pixels; the near-black ring round each (palette 1) is the window's recess: a
  lip 0.035 below the deck's top (shallow, so the whole ring shows at the tilted camera) in the ramp's
  darkest steel (96), and the recess's walls too: lit by the sun from the camera's side, a deeper step
  stayed as light as the deck (D134, D136);
- rails: on a closed side (its edge row or column all near-black) rows 1-4 (top), 23-26 (bottom),
  columns 1-3 (left) or 20-22 (right), a box beam 0.24 high standing proud of the deck, its top edges
  rounded (0.11, smooth shaded) so the art's bright rail line is sheen on the rounding; the beams are
  notched at the art's joints (columns 11|12 of a horizontal rail, rows 13-15 of a vertical one); the
  near-black line outside a rail is the girder's outer lip (like the windows'), not an outline;
- the inside of a corner: an L of the same beams, rows 1-4 x columns 0-3 and rows 0-4 x columns 1-3
  (rotated per corner), which meets the branches' rails at the tile edges;
- colours: the deck takes the median palette index of its pixels (the shading and highlights dropped),
  from the steel-blue ramp 96-108, and the rails the same steel (D136: their own median, a shade darker,
  left them dark bars in game).

Heights: the deck is 0.12 thick (z -0.12..0) and the rails stand 0.22 above it (from -0.02), so the whole track is
within -0.12..+0.22 of its pass height (0.9), well clear of the ground enemies (0.45) it passes over.

Run: tools/build-models.sh -j 2 assets/blender/tiles/delbld_girders.py
     Blender -b --factory-startup -P delbld_girders.py -- [--no-bake] [tile ...]
"""

import sys
from pathlib import Path

import bmesh
import bpy
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
WINDOW_LIP = -0.035    # the top of the lip round each window and along the girder's outer edge
RAIL_TOP = 0.22
RAIL_RADIUS, DECK_BEVEL = 0.11, 0.03
STEEL = dict(metallic=0.15, roughness=0.32)   # satin, as the flagship models (D65): metal darkens the diffuse


def closed_sides(px):
    """The sides of a tile the track doesn't continue through: its edge row or column is all ink."""
    return {
        "U": bool(np.all(px[0] <= 1)),
        "D": bool(np.all(px[-1] <= 1)),
        "L": bool(np.all(px[:, 0] <= 1)),
        "R": bool(np.all(px[:, -1] <= 1)),
    }


def rail_rects(px):
    """The rails of one tile as rectangles (rows r0:r1, columns c0:c1 in 1x pixels), from which of its
    sides are closed."""
    closed = closed_sides(px)
    out = []
    if closed["U"]:
        out.append((1, 5, 0, 24))
    if closed["D"]:
        out.append((23, 27, 0, 24))
    if closed["L"]:
        out.append((0, 28, 1, 4))
    if closed["R"]:
        out.append((0, 28, 20, 23))
    # The inside of a corner between two open sides: an L joining the branches' rails.
    for v, hz in (("U", "L"), ("U", "R"), ("D", "L"), ("D", "R")):
        if closed[v] or closed[hz]:
            continue
        rows = (1, 5) if v == "U" else (23, 27)
        rows_long = (0, 5) if v == "U" else (23, 28)
        cols = (0, 4) if hz == "L" else (20, 24)
        cols_short = (1, 4) if hz == "L" else (20, 23)
        out.append((*rows, *cols))
        out.append((*rows_long, *cols_short))
    return out


def rail_mask(px):
    """The rails of one tile (1x pixels) as a mask."""
    m = np.zeros(px.shape, dtype=bool)
    for r0, r1, c0, c1 in rail_rects(px):
        m[r0:r1, c0:c1] = True
    return m & (px > 0)


def merge_rects(rects):
    """Join rectangles that continue one another (same rows and touching columns, or the reverse), so
    a rail running through several tiles of the block is one beam."""
    rects = sorted(set(rects))
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(rects):
            for j, b in enumerate(rects):
                if i == j:
                    continue
                if a[0] == b[0] and a[1] == b[1] and a[3] == b[2]:
                    m = (a[0], a[1], a[2], b[3])
                elif a[2] == b[2] and a[3] == b[3] and a[1] == b[0]:
                    m = (a[0], b[1], a[2], a[3])
                else:
                    continue
                rects = sorted(set([r for k, r in enumerate(rects) if k not in (i, j)] + [m]))
                changed = True
                break
            if changed:
                break
    return rects


def joints(rects, gap=0.4):
    """Split the beams at the art's rail joints: a darker column then a bright one at columns 11|12 of
    every tile on a horizontal rail, a bracket at rows 13-15 on a vertical one. A joint is a notch
    between two beam ends, whose rounded ends catch the light as the art's bright ticks."""
    out = []
    for r0, r1, c0, c1 in rects:
        if r1 - r0 <= 5 and c1 - c0 > 6:
            cuts = [c for c in range(int(c0) // 24 * 24 + 12, int(c1), 24) if c0 + 2 < c < c1 - 2]
            edges = [c0] + [x for c in cuts for x in (c - gap / 2, c + gap / 2)] + [c1]
            out += [(r0, r1, edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
        elif c1 - c0 <= 4 and r1 - r0 > 6:
            cuts = [r for r in range(int(r0) // 28 * 28 + 14, int(r1), 28) if r0 + 2 < r < r1 - 2]
            edges = [r0] + [y for r in cuts for y in (r - gap / 2, r + gap / 2)] + [r1]
            out += [(edges[i], edges[i + 1], c0, c1) for i in range(0, len(edges), 2)]
        else:
            out.append((r0, r1, c0, c1))
    return out


def rail_beams(bm, rects, frame, z0, z1, radius, mat):
    """Each rectangle a box beam from z0 to z1 with its top edges rounded (`radius`, smooth shaded):
    the rounding is what catches the light as the art's bright rail lines."""
    for r0, r1, c0, c1 in rects:
        x0, x1 = frame.x(c0), frame.x(c1)
        y0, y1 = frame.y(r1), frame.y(r0)
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0)
        for v in tmp.verts:
            v.co.x = x0 if v.co.x < 0 else x1
            v.co.y = y0 if v.co.y < 0 else y1
            v.co.z = z0 if v.co.z < 0 else z1
        top_edges = [e for e in tmp.edges if all(v.co.z > (z0 + z1) / 2 for v in e.verts)]
        bmesh.ops.bevel(tmp, geom=top_edges, offset=radius, offset_type="OFFSET", segments=3, profile=0.5,
                        affect="EDGES", clamp_overlap=True, harden_normals=False)
        tmp.normal_update()
        for f in tmp.faces:
            f.material_index = mat
            f.smooth = 0.02 <= abs(f.normal.z) < 0.999
        me = bpy.data.meshes.new("_beam")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)


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
    # The rails are the girder's steel: the deck's index. Their own pixels' median (one shade darker:
    # the art draws a rail as one bright line over darker rows) left them darker than the deck in game,
    # where the art's rails read as bright bars; their rounded tops add the art's bright line as sheen.
    rail_index = deck_index

    mats = kit.Mats(ts, f"g{n}", **STEEL)
    DECK = mats(deck_index)
    # The lip round a window is the window's recess: in game (D53) a step with its occlusion stays as
    # light as the deck, while the art's ring is the darkest thing on the girder, so the lip and the
    # recess's walls take the ramp's darkest index the art uses round its windows (96; the ring itself
    # is 1), matte. The lip is shallow (D136), so at the tilted camera the near bar hides none of it.
    LIP = mats(96, metallic=0.0, roughness=0.75)
    RAIL = mats(rail_index, metallic=0.2, roughness=0.18)   # smoother: the art's bright rail lines are its sheen

    # The deck plate (its window edges rounded, in steel), and below its top the windows' lips and the
    # girder's outer lip.
    lip = ring | outline
    bm = bmesh.new()
    lt.mask_slab(bm, deck & ~lip, frame, DECK_BOTTOM, DECK_TOP, DECK, mat_side=LIP)
    kit.tidy(bm)
    kit.bevel(bm, DECK_BEVEL, segments=1, angle=50, material=DECK)
    lb = bmesh.new()
    lt.mask_slab(lb, lip, frame, DECK_BOTTOM, WINDOW_LIP, LIP, mat_side=DECK, walls=lip | (deck & ~lip))
    kit.tidy(lb)
    me = kit.bpy.data.meshes.new("_lips")
    lb.to_mesh(me)
    lb.free()
    bm.from_mesh(me)
    kit.bpy.data.meshes.remove(me)
    # The rails: box beams, rounded along their top edges, all steel (dark walls toward the trench between
    # two tracks were tried: they left the rail band darker than the art's in game).
    rects = []
    for r, row in enumerate(cells):
        for c, t in enumerate(row):
            if t >= 0:
                rects += [(r0 + r * lt.TILE_H, r1 + r * lt.TILE_H, c0 + c * lt.TILE_W, c1 + c * lt.TILE_W)
                          for r0, r1, c0, c1 in rail_rects(kit.pixels(ts, t))]
    rail_beams(bm, joints(merge_rects(rects)), frame, DECK_TOP - 0.02, RAIL_TOP, RAIL_RADIUS, RAIL)
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
