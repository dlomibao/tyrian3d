"""Red wall block (newshm.shp frame 1): a 3D version of its sprite.

Seen in episode 1 (levels 31 and 33) and episode 4 (level 27), laid side by side into walls
(assembly-newshm-1: every piece of that layout is this same tile, and each tile is a whole
block on its own, so each piece is modelled by itself; newshm-15, -17, -53, -55 and -153 are the
same block with an emblem). A glossy rounded block about half as tall as it is wide: short
vertical walls, a 2-3 px rounded shoulder on the north, west and east (the sprite's lit
north-west rim and dark east rim), a flat top, and the south edge rolling down
toward the viewer over the sprite's dark lower third (its front wall).

The footprint follows the sprite's body inside its 1 px black outline (the game draws that
outline): a rounded rectangle whose corners match the sprite's staircase. The whole block is the
sprite's mid-tone red (palette 71, its flat top) in a glossy painted-metal material: the sprite's
bright top-left rim and glints are sheen, and its dark east rim and dark front band are the
light falling off the shoulder and the front slope, so the game's lights make them instead of
paint (the rubric's "the sprite's lighting is not paint" and "metallic sheen is not geometry").

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

# The block's colour (the sprite's flat top) and its glossy painted-metal finish.
BODY = 71
METALLIC = 0.6
ROUGHNESS = 0.35


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


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, BODY, NAME, metallic=METALLIC, roughness=ROUGHNESS)]

    bm = bmesh.new()
    rings = []
    for iw, ie, inn, ins, z in PROFILE:
        rings.append([bm.verts.new((x, y, z / 12)) for x, y in _outline(iw, ie, inn, ins)])
    n = len(rings[0])
    assert all(len(r) == n for r in rings)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[-1])
    bm.faces.new(list(reversed(rings[0])))
    obj = lib.finish(NAME, bm, mats, coll)
    for poly in obj.data.polygons:  # the base stays flat so the walls shade evenly
        if poly.normal.z < -0.9:
            poly.use_smooth = False
    return obj


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
