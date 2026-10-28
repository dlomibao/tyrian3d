"""Shield drone in a spinning ring (newsh2.shp frames 229-243): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. A small grey shield-shaped core, one rounded dome
about 9 px across with a dark crease down the middle and a flat red-orange light on each top
corner, inside a ring of two polished grey arcs (about 140 degrees each, with gaps between them),
round pipes about 4 px thick with squared-off ends. The ring turns clockwise 22.5 degrees a frame,
so the eight frames are eight models of the same thing with the ring turned: newsh2-229 (frame 229),
newsh2-229-f2 (231) ... newsh2-229-f8 (243). The sprite's whole drone shifts by a pixel between
frames; each model is centred where its frame draws it (found from the core's top-left light).

Run: blender --background --python assets/blender/enemies/newsh2-229.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-229"
U = 1 / 12
RING_R = 8.5 * U
TUBE_R = 2.1 * U  # the arms are 4 px across, outline included
HALF_ARC = math.radians(70)
DOME_H = 4.6  # px above the ring's mid-plane
BASE = -1.5  # px, the core's underside
GROOVE = 1.0  # px, depth of the centre groove (flat-bottomed, 1 px wide)

# The core's outline (offset from its centre in px, up = +y): half-width per height, flat across the
# top (sprite row 8) and narrowing to a point at the bottom (rows 14-16).
OUTLINE = ((-4.5, 0.9), (-3.8, 1.8), (-2.8, 2.9), (-1.8, 3.9), (-1.0, 4.5), (1.0, 4.5), (2.6, 4.5),
           (3.4, 4.5), (3.7, 4.3), (4.0, 3.85), (4.5, 3.4))


def half_width(y):
    for (y0, w0), (y1, w1) in zip(OUTLINE, OUTLINE[1:]):
        if y0 <= y <= y1:
            return w0 + (w1 - w0) * (y - y0) / (y1 - y0)
    return OUTLINE[0][1] if y < OUTLINE[0][0] else OUTLINE[-1][1]


def dome(x, y):
    """Height in px of the core's dome (without the crease) at offset (x, y) px from its centre."""
    w = half_width(y)
    u = min(1.0, abs(x) / w)
    e = max(0.0, 1 - (y / 4.5) ** 4) ** 0.5
    return DOME_H * max(0.0, 1 - u * u) ** 0.5 * e


def frame_centre(frame):
    """The drone's centre in a frame, in px edges: 3.5 px right of and below its top-left light."""
    for r, line in enumerate(frame["pixels"]):
        vals = [int(v) for v in (line.split() if isinstance(line, str) else line)]
        if 121 in vals:
            return vals.index(121) + 3.5, r + 3.5
    return 12.5, 13.5


def groove_depth(y):
    """The centre groove's depth in px at height y: full down the body, fading out above the bottom
    tip (y < -2.5) so the tip stays one point."""
    t = max(0.0, min(1.0, (y + 3.6) / 1.1))
    return GROOVE * t * max(0.0, 1 - (y / 4.5) ** 4) ** 0.5


def build_core(bm, cx, cy, core_mat, groove_mat, eye_mat, eye2_mat, rim_mat):
    ys = [y for y, _ in OUTLINE]
    grid = []
    # Columns: the groove is a 1 px wide flat-bottomed channel (walls at +-0.5 px, floor +-0.42 px).
    for y in ys:
        w = half_width(y)
        go, gi = min(0.5 / w, 0.3), min(0.42 / w, 0.26)
        us = (-1, -0.85, -0.6, -0.35, -go, -gi, gi, go, 0.35, 0.6, 0.85, 1)
        rowv = []
        for u in us:
            x = u * w
            z = dome(x, y) - (groove_depth(y) if abs(u) <= gi + 1e-9 else 0.0)
            rowv.append(bm.verts.new((cx + x * U, cy + y * U, z * U)))
        grid.append(rowv)
    nx = len(grid[0]) - 1
    mid = nx // 2
    for j in range(len(grid) - 1):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            groove = i in (mid - 2, mid - 1, mid, mid + 1) and ys[j] > -3.6
            f.material_index = groove_mat if groove else core_mat
            f.smooth = not groove
    # Skirt down to the underside, then close it.
    rim = [grid[0][i] for i in range(nx + 1)] + [grid[j][nx] for j in range(1, len(grid))]
    rim += [grid[-1][i] for i in range(nx - 1, -1, -1)] + [grid[j][0] for j in range(len(grid) - 2, 0, -1)]
    low = [bm.verts.new((v.co.x, v.co.y, BASE * U)) for v in rim]
    n = len(rim)
    for k in range(n):
        a, b = k, (k + 1) % n
        if rim[a].co.z == low[a].co.z and rim[b].co.z == low[b].co.z:
            continue
        f = bm.faces.new((rim[a], low[a], low[b], rim[b]))
        f.material_index = rim_mat
    f = bm.faces.new(list(reversed(low)))
    f.material_index = core_mat
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)

    # Flat red-orange lights on the top corners: 2 x 1 px (row 9) plus the outer px below (row 10).
    top = lambda x, y: dome((x - cx) / U, (y - cy) / U) * U  # noqa: E731
    for s in (-1, 1):
        for (xa, xb, ya, yb), m in (((1.5, 3.5, 2.5, 3.5), eye_mat), ((2.5, 3.5, 1.5, 2.5), eye2_mat)):
            x0, x1 = sorted((cx + s * xa * U, cx + s * xb * U))
            lib.drape_patch(bm, top, x0, x1, cy + ya * U, cy + yb * U, nx=2, ny=1, lift=0.3 * U, depth=1.0 * U,
                            mat_index=m, smooth=False)


# Grey shades the model is painted in (sprite palette indices, dark to light). Each face seen from
# above takes the one nearest in brightness to the sprite pixel under it, so the lit model shows
# the sprite's shading: white highlight bands on the arcs, light silver lobes on the core, black
# outline pixels on the flanks.
SHADES = (2, 4, 6, 8, 10, 12, 14)
STEEP = 0.5  # faces steeper than this (normal z) are flanks
FLANK = 4  # the darkest shade a flank takes


def frame_pixels(frame):
    return [[int(v) for v in (line.split() if isinstance(line, str) else line)] for line in frame["pixels"]]


def paint(bm, pixels, colors, skip, slot_of):
    """Give every face not in `skip` the shade of the sprite pixel under its centre (its nearest
    opaque neighbour on the silhouette's edge); faces underneath get the darkest shade."""
    lum = {int(k): sum(v) / 3 for k, v in colors.items()}
    rows, cols = len(pixels), len(pixels[0])

    def index_at(c, r):
        for dc, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            cc, rr = c + dc, r + dr
            if 0 <= rr < rows and 0 <= cc < cols and pixels[rr][cc] >= 0:
                return pixels[rr][cc]
        return SHADES[0]

    for f in bm.faces:
        if f.material_index in skip:
            continue
        f.normal_update()
        if f.normal.z < -0.2:
            f.material_index = slot_of[SHADES[0]]
            continue
        c = f.calc_center_median()
        i = index_at(math.floor(c.x / U + 12), math.floor(14 - c.y / U))
        y = lum.get(i, 0)
        if f.normal.z < STEEP:
            # Steep flanks only show from above as the sprite's 1 px black outline, which the game
            # draws itself; a mid grey keeps them from reading as a black band from the game camera.
            y = max(y, lum[FLANK])
        f.material_index = slot_of[min(SHADES, key=lambda k: abs(lum[k] - y))]


def build_one(sprite, name, turn, centre, pixels):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(121, emission_strength=4.0),  # 0 lights' top row: orange (sprite index 121)
        pal(119, emission_strength=4.0),  # 1 lights' outer drop: red (sprite index 119)
    ]
    EYE, EYE2 = 0, 1
    slot_of = {}
    for k in SHADES:
        slot_of[k] = len(mats)
        # Low metallic so the lit model reads as silver like the sprite, not dark chrome.
        mats.append(pal(k, metallic=0.2, roughness=0.35))
    BODY = slot_of[SHADES[-1]]
    cx, cy = (centre[0] - 12) * U, (14 - centre[1]) * U
    bm = bmesh.new()

    # Two arcs of constant thickness with flat ends, centred left and right in frame 229, turned
    # clockwise by `turn`.
    n = 20
    for mid in (math.pi, 0.0):
        pts = []
        for i in range(n + 1):
            a = mid - turn - HALF_ARC + 2 * HALF_ARC * i / n
            pts.append((cx + RING_R * math.cos(a), cy + RING_R * math.sin(a), 0.0))
        lib.polyline_tube(bm, pts, TUBE_R, sides=10, mat_index=BODY)

    build_core(bm, cx, cy, BODY, BODY, EYE, EYE2, BODY)
    paint(bm, pixels, sprite["colors"], (EYE, EYE2), slot_of)
    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    by_index = {f["index"]: f for f in sprite["frames"]}
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        f = by_index[frame]
        obj = build_one(sprite, name, k * math.pi / 8, frame_centre(f), frame_pixels(f))
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
