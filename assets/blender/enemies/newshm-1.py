"""Red wall block (newshm.shp frame 1): a 3D version of its sprite.

Seen in episode 1 (levels 31 and 33) and episode 4 (level 27), laid side by side into walls
(assembly-newshm-1: every piece of that layout is this same tile, and each tile is a whole
block on its own, so each piece is modelled by itself; newshm-15, -17, -53, -55 and -153 are the
same block with an emblem). A glossy rounded block about half as tall as it is wide: short
vertical walls, a 2-3 px rounded shoulder on the north, west and east (the sprite's lit
north-west rim and dark east rim), a flat top, and the south edge rolling down
toward the viewer over the sprite's dark lower third (its front wall).

The footprint follows the sprite's body inside its 1 px black outline (the game draws that
outline): a rounded rectangle whose corners match the sprite's staircase. Each face takes the
palette colour of the sprite pixel under it (snapped to a few shades of the red ramp), so from
above the block shows the sprite's bands: the bright top-left rim and glint spot, the dark east
rim, the dark front band and the south-east glint; the walls below are the dark side shades.

Run: blender --background --python assets/blender/enemies/newshm-1.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-1"

# Footprint: a rounded rectangle just inside the outline ring (pixel coordinates, 24x28 block).
EDGE_X = 11.45   # half width, px (the outline ring's centre is at 11.5)
EDGE_Y = 13.45   # half height, px
CORNER = 9.2     # corner radius, px: matches the sprite's corner staircase (5, 3, 2, 1, 1, 0 px in)

# Rings from the base up, in px: (inset west, inset east, inset north, inset south, z).
PROFILE = [
    (0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0, 0.0, 3.5),     # short vertical wall
    (0.35, 0.35, 0.3, 1.6, 6.6),
    (1.0, 0.9, 0.8, 3.8, 8.7),
    (1.8, 1.6, 1.4, 6.0, 10.0),
    (2.7, 2.3, 2.0, 8.1, 10.75),
    (3.5, 3.0, 2.6, 10.0, 11.1),   # edge of the flat top (the cap)
]
CORNER_SEGS = 7
SIDE_SPLITS = (3, 1)  # pieces along each straight west/east and north/south edge

# Palette shades the faces snap to (the sprite's red ramp, 65 dark .. 79 bright).
SHADES = (67, 68, 69, 70, 71, 73, 75)


def _outline(iw, ie, inn, ins):
    """Counter-clockwise rounded-rectangle outline (units) for a ring with these insets (px)."""
    x0, x1 = (-EDGE_X + iw) / 12, (EDGE_X - ie) / 12
    y0, y1 = (-EDGE_Y + ins) / 12, (EDGE_Y - inn) / 12
    r = max(2.5, CORNER - (iw + ie + inn) / 3) / 12  # about concentric with the base corners
    r = max(0.0, min(r, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4))
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    nsplit = [SIDE_SPLITS[0], SIDE_SPLITS[1], SIDE_SPLITS[0], SIDE_SPLITS[1]]  # after each corner: east, north, west, south
    pts = []
    for k, (cx, cy, a0) in enumerate(corners):
        for i in range(CORNER_SEGS + 1):
            a = math.radians(a0 + 90 * i / CORNER_SEGS)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        # straight edge to the next corner's start (exclusive of both ends)
        nx, ny, na = corners[(k + 1) % 4]
        a1 = math.radians(na)
        end = (nx + r * math.cos(a1), ny + r * math.sin(a1))
        start = pts[-1]
        for s in range(1, nsplit[k]):
            t = s / nsplit[k]
            pts.append((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t))
    return pts


def _sprite_grid(sprite):
    rows = sprite["frames"][0]["pixels"]
    return [[int(v) for v in (r.split() if isinstance(r, str) else r)] for r in rows]


def _shade_under(grid, x, y):
    """Palette index of the sprite body pixel under (x, y) units, or the nearest body pixel when
    that is outline or empty."""
    H, W = len(grid), len(grid[0])
    c, r = int(math.floor(x * 12 + W / 2)), int(math.floor(H / 2 - y * 12))
    best = None
    for rad in range(0, 4):
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] > 1:
                    d = dr * dr + dc * dc
                    if best is None or d < best[0]:
                        best = (d, grid[rr][cc])
        if best:
            return best[1]
    return 71


def _lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(v)) for v in rgb)
    X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = [v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116 for v in (X, Y, Z)]
    return (116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2]))


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = _sprite_grid(sprite)
    labs = {int(k): _lab(v) for k, v in sprite["colors"].items()}
    mats = [common.palette_material(sprite, i, NAME, metallic=0.35, roughness=0.3) for i in SHADES]
    snap = {}
    for k, lk in labs.items():
        snap[k] = min(range(len(SHADES)), key=lambda j: sum((a - b) ** 2 for a, b in zip(lk, labs[SHADES[j]])))

    bm = bmesh.new()
    rings = []
    for iw, ie, inn, ins, z in PROFILE:
        rings.append([bm.verts.new((x, y, z / 12)) for x, y in _outline(iw, ie, inn, ins)])
    n = len(rings[0])
    assert all(len(r) == n for r in rings)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            c = f.calc_center_median()
            f.normal_update()
            if f.normal.z < 0.25:
                # Near-vertical walls can't be seen from above: the dark side of the block, a
                # shade darker on the south front the game camera looks at.
                f.material_index = SHADES.index(67 if f.normal.y < -0.5 else 68)
            else:
                # Sloped faces take the colour of the sprite pixel above them.
                k = snap[_shade_under(grid, c.x, c.y)]
                if f.normal.y < -0.3:  # the south-east glint stays a soft gleam on the front
                    k = min(k, SHADES.index(73))
                f.material_index = k
    cap = bm.faces.new(rings[-1])
    cap.material_index = SHADES.index(71)
    bot = bm.faces.new(list(reversed(rings[0])))
    bot.material_index = SHADES.index(67)
    obj = lib.finish(NAME, bm, mats, coll)
    for poly in obj.data.polygons:  # the base stays flat so the walls shade evenly
        if poly.normal.z < -0.9:
            poly.use_smooth = False
    return obj


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
