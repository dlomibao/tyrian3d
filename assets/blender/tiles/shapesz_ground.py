"""Structures on the ground (background 1) of shapesz.dat in Episode 1's TYRIAN: 3D versions of
the tiles, standing on the remastered ground (DECISIONS.md D34).

- Two bunkers, each a 2x2 block of tiles: one with a gold ring and two gold domes on a dark body
  (320 321 / 330 331), one an armoured hull with gold chevrons (322 323 / 332 333); and a wreck,
  3x2 (340-342 / 350-352). Ground enemies (turrets) sit on the bunkers, so they stay below about
  0.2 units. Each is its silhouette (the grey, near-black and gold pixels; the dirt around is left
  to the ground) raised as relief, brighter parts higher, in its own colours; the ring bunker's
  ring is a torus and its domes are domes.
- Grey boulders on the dirt (112, 113): a rounded stone per stone in the art.
- The forest (210-214, 220-224, 230-234): a crown for each tree in the art (lib_tiles.boulders
  finds them as hills of brightness), standing on the painted forest.

Run: blender --background --python assets/blender/tiles/shapesz_ground.py [-- --preview out_dir]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_tiles as lt  # noqa: E402

ROOT = common.repo_root(__file__)
SHAPES = "shapesz"
LAYER = 0

#: name: (pattern, relief height, extras)
STRUCTURES = {
    "bunker-ring": ([[320, 321], [330, 331]], 0.12, "ring"),
    "bunker-hull": ([[322, 323], [332, 333]], 0.16, None),
    "wreck": ([[340, 341, 342], [350, 351, 352]], 0.1, None),
}
BOULDERS = [112, 113]
TREES = [210, 211, 212, 213, 214, 220, 221, 222, 223, 224, 230, 231, 232, 233, 234]


def ground_colours(ts, pattern):
    """The palette indices of the ground around a pattern: every index in the tiles found next to
    its cells (tiles.json neighbours) that aren't part of it."""
    inside = {n for row in pattern for n in row}
    out = set()
    for n in inside:
        for side in ts.tiles[n]["neighbours"].values():
            for nb in side:
                t = nb["tile"]
                if t not in inside and t in ts.tiles:
                    out.update(int(v) for v in np.unique(ts.tiles[t]["px"]))
    return out


def silhouette(ts, grid, pattern):
    """The structure's pixels: those in colours the ground around it doesn't have, closed up
    (which takes in its gold, a colour the dirt shares), with holes filled and specks dropped."""
    dirt = ground_colours(ts, pattern)
    core = (grid >= 0) & ~np.isin(grid, list(dirt))
    closed = lt.blur(core.astype(float), 1.8) > 0.3
    h, w = closed.shape
    filled = closed.copy()
    for ys, xs in lt.components(~closed):
        if not (ys.min() == 0 or xs.min() == 0 or ys.max() == h - 1 or xs.max() == w - 1):
            filled[ys, xs] = True
    keep = np.zeros_like(filled)
    for ys, xs in lt.components(filled):
        if len(ys) >= 60:
            keep[ys, xs] = True
    return lt.blur(keep.astype(float), 1.2) > 0.5


def structure(ts, name, pattern, amp, extra):
    coll = common.reset_collection(f"{SHAPES}-{name}")
    pal = lt.Palette(ts, f"{SHAPES}{name}", roughness=0.6, metallic=0.25)
    grid = ts.grid(pattern, 2)
    frame = lt.Frame(pattern, scale=2)
    mask = silhouette(ts, grid, pattern)
    # Fill the silhouette's own dirt-coloured pixels with the nearest structure colour.
    snap = lt.Snapper(ts, grid[mask & ((np.maximum(grid, 0) >> 4) != 1) | (mask & (lt.lum_of(ts, grid) > 0.42))], limit=5)
    gold = (np.maximum(grid, 0) >> 4 == 1) & (lt.lum_of(ts, grid) > 0.42) & mask
    if gold.any():
        snap.keep.append(lt.dominant(grid[gold], ts.lum))  # the gold trim always keeps its colour
        snap.cache.clear()
    heights = 0.03 + lt.relief_heights(ts, np.where(mask, grid, -1), amp, sigma=1.0)
    # Round the silhouette's edge down so it sits into the ground rather than standing as a wall.
    edge = lt.blur(mask.astype(float), 2.0)
    heights *= np.clip((edge - 0.3) / 0.5, 0.2, 1.0)
    heights = np.round(heights / 0.02) * 0.02  # terraces, so flat parts merge into few faces
    bm = bmesh.new()
    lt.mask_slab(bm, mask, frame, -0.02, 0.0, lambda x, y: pal(snap(grid[y, x])), pal(snap(grid[mask][0])), top_height=heights)
    lt.dissolve_coplanar(bm)

    if extra == "ring":
        gold = pal(26, roughness=0.35, metallic=0.7)
        # The ring: centre (19, 10) px of the 48x56 block, radius 11, tube 2.2.
        ring = bmesh.new()
        major, minor = 11 * lt.PX, 2.2 * lt.PX
        cx, cy = frame.x(19 * 2), frame.y(10 * 2)
        seg, tube = 24, 8
        rings = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring_v = []
            for j in range(tube):
                b = 2 * math.pi * j / tube
                r = major + minor * math.cos(b)
                ring_v.append(ring.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), 0.1 + minor * 0.8 * math.sin(b))))
            rings.append(ring_v)
        for i in range(seg):
            for j in range(tube):
                a, b = rings[i], rings[(i + 1) % seg]
                ring.faces.new((a[j], b[j], b[(j + 1) % tube], a[(j + 1) % tube])).material_index = gold
        tmp = bpy.data.meshes.new("tmp_ring")
        ring.to_mesh(tmp)
        ring.free()
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        for px, py in ((5, 30), (32, 30)):
            lt.dome(bm, frame.x(px * 2), frame.y(py * 2), 5 * lt.PX, 4.5 * lt.PX, 0.0, 0.0, 0.17, gold, sides=12, rings=4)

    return [lt.mesh(f"{SHAPES}-{name}", bm, pal, coll, smooth=False)]


def boulder_tile(ts, n):
    name = f"t{n}"
    coll = common.reset_collection(f"{SHAPES}-{name}")
    pal = lt.Palette(ts, f"{SHAPES}{name}", roughness=0.8)
    bm = bmesh.new()

    def keep(ys, xs):
        g = ts.grid([[n]], 2)
        inside = (ys >= 0) & (ys < g.shape[0]) & (xs >= 0) & (xs < g.shape[1])
        vals = g[ys[inside], xs[inside]]
        return len(vals) > 0 and np.mean((vals >> 4) == 0) > 0.5

    lt.boulders(ts, n, pal, bm, keep=keep, z0=-0.02, max_height=0.17, sigma=2.4, gap=0.18, min_pixels=12)
    return [lt.mesh(f"{SHAPES}-{name}", bm, pal, coll, smooth=True)] if len(bm.faces) else []


def tree_tile(ts, n):
    name = f"t{n}"
    coll = common.reset_collection(f"{SHAPES}-{name}")
    pal = lt.Palette(ts, f"{SHAPES}{name}", roughness=0.9)
    bm = bmesh.new()
    grid = ts.grid([[n]], 2)

    def keep(ys, xs):
        # A crown: green, brighter than the grass, and big enough.
        inside = (ys >= 0) & (ys < grid.shape[0]) & (xs >= 0) & (xs < grid.shape[1])
        if inside.sum() < 0.3 * len(ys):
            return True  # mostly in the neighbour: its own pixels decide there
        vals = grid[ys[inside], xs[inside]]
        lum = ts.lum[np.maximum(vals, 0)]
        return np.mean((vals >> 4) == 2) > 0.8 and np.percentile(lum, 85) > 0.24

    lt.boulders(ts, n, pal, bm, keep=keep, z0=0.0, max_height=0.36, sigma=2.2, gap=0.1, sides=9, squash=0.0, min_pixels=14,
                quantile=0.55, shrink=0.8)
    return [lt.mesh(f"{SHAPES}-{name}", bm, pal, coll, smooth=True)] if len(bm.faces) else []


def main():
    ts = lt.Tileset(ROOT, SHAPES, layer=LAYER)
    preview = lt.preview_arg()
    for name, (pattern, amp, extra) in STRUCTURES.items():
        objects = structure(ts, name, pattern, amp, extra)
        lt.export_tile_model(ts, objects, name, LAYER, pattern)
        if preview:
            lt.preview(ts, objects, pattern, Path(preview) / f"{SHAPES}-{name}.png", view_px=240)
    for n in BOULDERS + TREES:
        objects = (boulder_tile if n in BOULDERS else tree_tile)(ts, n)
        if not objects:
            print(f"t{n}: nothing to model")
            continue
        lt.export_tile_model(ts, objects, f"t{n}", LAYER, [[n]])
        if preview:
            lt.preview(ts, objects, [[n]], Path(preview) / f"{SHAPES}-t{n}.png", view_px=240)


main()
