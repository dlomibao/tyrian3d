"""Pillar of fire (newshk.shp frames 51, 53, 55, assembly of 3 pieces): a 3D version of its sprites.

Seen in episodes 3 (level 3.12) and 4 (level 4.4). Three 2x2 pieces side by side make one
72x28 px column of flame that roars up the screen out of the top of a machine (the newsho
pieces below it, modelled elsewhere): ragged red and orange edges, yellow tongues and a broad
white-hot core. The flame runs off the top and bottom of the pieces, so it is cut flat there.

The fire is a relief traced pixel by pixel from the sprite, on a flat base at z = 0: every sprite
pixel is one top face in its own palette colour, so from above it is the sprite. The broad white
core (the run of white pixels through the middle of each row) is one flat, smooth sheet 1 px
thick, as even as the sprite draws it. All the relief is in the flames on either side: each
pixel stands as high as it is bright (red tips about 1 px, orange 2-2.6, yellow 3-3.2, the white
streaks 4-4.3), softened a little with its neighbours, so the yellow and white licks stand up as
ridges with the dark red gaps between them; within 4 px of the core they sink to its level, so
the sheet runs smoothly into them. Built once in assembly coordinates and cut into the
three pieces with common.split_assembly along pixel edges. Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newshk-51.py [-- --preview out.png]
(the preview is the whole column; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b010 as lib  # noqa: E402

NAME = "assembly-newshk-51"
ROOT = common.repo_root(__file__)
# (piece, screen cx, cy) from sprite.json assemblyLayout.
PIECES = [("newshk-51", 92, 55), ("newshk-53", 116, 55), ("newshk-55", 140, 55)]
CORE_INDEX = 127  # the white-hot core
CORE_PX = 1.0  # the core sheet's thickness, sprite px
LOW, HIGH = 115, 127  # flame palette ramp: darkest red .. white (emission strength)
# Flame pixel heights (sprite px) by palette index: red tips low, orange, yellow licks, and the
# white streaks along their crests about 1 px proud of the yellow.
FLAME_PX = {115: 0.8, 116: 0.9, 117: 1.0, 118: 1.2, 119: 1.4, 120: 1.6, 121: 2.0, 122: 2.3,
            123: 2.6, 124: 3.0, 125: 3.2, 126: 4.0, 127: 4.3}
SMOOTH = 0.35  # how much each flame pixel is blended with its neighbours' mean
RAMP_PX = 4.0  # flames rise from the core's height over this many px out from it


def core_mask(grid):
    """Per row, the run of white pixels through the middle of the grid: the flat core."""
    h, w = len(grid), len(grid[0])
    mid = w // 2
    core = [[False] * w for _ in range(h)]
    for r, line in enumerate(grid):
        if line[mid] != CORE_INDEX:
            continue
        a = mid
        while a > 0 and line[a - 1] == CORE_INDEX:
            a -= 1
        b = mid
        while b < w - 1 and line[b + 1] == CORE_INDEX:
            b += 1
        for c in range(a, b + 1):
            core[r][c] = True
    return core


def pixel_heights(grid, core):
    """Height (sprite px) of each pixel's top: the core flat, flames by brightness, softened."""
    h, w = len(grid), len(grid[0])
    raw = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v < 0:
                continue
            if core[r][c]:
                raw[r][c] = CORE_PX
            else:
                raw[r][c] = FLAME_PX[min(max(v, LOW), HIGH)]
    out = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if raw[r][c] is None:
                continue
            if core[r][c]:
                out[r][c] = CORE_PX
                continue
            near = [raw[q][p] for q in (r - 1, r, r + 1) for p in (c - 1, c, c + 1)
                    if 0 <= q < h and 0 <= p < w and raw[q][p] is not None and not core[q][p]]
            mean = sum(near) / len(near)
            z = (1 - SMOOTH) * raw[r][c] + SMOOTH * mean
            # Near the core the flames sink to its level, so the sheet runs into them smoothly.
            d = min((abs(p - c) for p in range(w) if core[r][p]), default=None)
            if d is not None:
                t = min(1.0, d / RAMP_PX)
                t = t * t * (3 - 2 * t)
                z = CORE_PX + (z - CORE_PX) * t
            out[r][c] = z
    return out


def fire_relief(bm, grid, mat_of):
    """The relief: a top face per pixel, walls where a pixel meets nothing, a flat base at z=0."""
    h, w = len(grid), len(grid[0])
    core = core_mask(grid)
    hp = pixel_heights(grid, core)

    def filled(r, c):
        return 0 <= r < h and 0 <= c < w and grid[r][c] >= 0

    # Vertex (i, j) is the corner at column edge i (0..w), row edge j (0..h).
    def corner_z(i, j):
        around = [(j - 1, i - 1), (j - 1, i), (j, i - 1), (j, i)]
        around = [(r, c) for r, c in around if filled(r, c)]
        if any(core[r][c] for r, c in around):
            return CORE_PX / 12
        return sum(hp[r][c] for r, c in around) / len(around) / 12

    def X(i):
        return (i - w / 2) / 12

    def Y(j):
        return (h / 2 - j) / 12

    top, base = {}, {}

    def vt(i, j):
        if (i, j) not in top:
            top[(i, j)] = bm.verts.new((X(i), Y(j), corner_z(i, j)))
        return top[(i, j)]

    def vb(i, j):
        if (i, j) not in base:
            base[(i, j)] = bm.verts.new((X(i), Y(j), 0.0))
        return base[(i, j)]

    for r in range(h):
        for c in range(w):
            if not filled(r, c):
                continue
            mat = mat_of[grid[r][c]]
            # Top (counter-clockwise seen from above: +X right, +Y up = row -1).
            f = bm.faces.new((vt(c, r + 1), vt(c + 1, r + 1), vt(c + 1, r), vt(c, r)))
            f.material_index = mat
            f.smooth = not core[r][c]
            f = bm.faces.new((vb(c, r), vb(c + 1, r), vb(c + 1, r + 1), vb(c, r + 1)))
            f.material_index = mat
            f.smooth = False
            # Walls on edges facing an empty pixel or the grid's edge.
            for (dr, dc), (a, b) in (((-1, 0), ((c + 1, r), (c, r))),  # row above: edge j = r
                                     ((1, 0), ((c, r + 1), (c + 1, r + 1))),
                                     ((0, -1), ((c, r), (c, r + 1))),
                                     ((0, 1), ((c + 1, r + 1), (c + 1, r)))):
                if filled(r + dr, c + dc):
                    continue
                f = bm.faces.new((vb(*a), vb(*b), vt(*b), vt(*a)))
                f.material_index = mat
                f.smooth = False


def fire_assembly(root, file, name, pieces):
    grid, colors, (cx0, cy0), w, h = lib.assembly_grid(root, pieces)
    sprite = {"name": name, "colors": colors}
    coll = common.reset_collection(name)
    used = sorted({v for line in grid for v in line if v >= 0})
    mats, mat_of = [], {}
    for v in used:
        t = (min(max(v, LOW), HIGH) - LOW) / (HIGH - LOW)
        mat_of[v] = len(mats)
        mats.append(common.palette_material(sprite, v, name, metallic=0.0, roughness=0.6,
                                            emission_strength=2.5 + 2.5 * t))
    bm = bmesh.new()
    fire_relief(bm, grid, mat_of)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    obj = lib.to_object(name, bm, mats, coll)
    layout = [(m, cx - cx0, cy - cy0) for m, cx, cy in pieces]
    parts = common.split_assembly(obj, layout)
    for m, _, _ in pieces:
        data = common.load_sprite(root, m)
        common.export_sprite_model(root, [parts[m]], f"enemies/{m}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        size = math.ceil(max(w / 24, h / 28)) * 2
        ref = lib.grid_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", size * 12, size * 14)
        common.render_preview([obj], str(out), str(ref), size=size, view_px=480)
        for m, _, _ in pieces:
            data = common.load_sprite(root, m)
            img = root / "reference" / "models" / m / data["frames"][0]["image"]
            common.render_preview([parts[m]], str(out.parent / f"{m}.png"), img, size=2)
    return obj, parts


def main():
    fire_assembly(ROOT, __file__, NAME, PIECES)


if __name__ == "__main__":
    main()
