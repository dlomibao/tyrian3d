"""Shield drone in a spinning ring (newsh2.shp frames 229-243): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. A small grey shield-shaped core about 9 px across, two
rounded lobes either side of a cut-in seam down the middle, with a domed red-orange light lens on each
top corner, inside a ring of two polished grey arcs (about 140 degrees each, with gaps between them),
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
LOBE_DIP = 0.4  # how far the dome sags toward the seam between the two lobes (fraction of its height)
LENS_H = 0.9  # px, how far each corner light's lens domes up above its rim

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
    # Two lobes: the surface dips toward the centre seam, so each half crowns about 2 px out.
    lobe = 1 - LOBE_DIP * math.exp(-(x / 1.3) ** 2)
    return DOME_H * max(0.0, 1 - u * u) ** 0.5 * e * lobe


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


def build_core(bm, cx, cy, core_mat, groove_mat, eye_mat, rim_mat):
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
            groove = i in (mid - 1, mid, mid + 1) and ys[j] > -3.6  # the two walls and the floor
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

    # Red-orange lights on the top corners: 2 x 1 px (row 9) plus the outer px below (row 10), a glowing
    # lens domed up over the lobe's corner so it reads from the game camera.
    for s in (-1, 1):
        def top(x, y, s=s):
            lx, ly = (x - cx) / U, (y - cy) / U
            r2 = ((abs(lx) - 2.7) ** 2 + (ly - 2.7) ** 2) / 1.35 ** 2
            return (dome(lx, ly) + LENS_H * max(0.0, 1 - r2) ** 0.5) * U

        # Each pixel in its own colour, brightest at the outer top corner: (outer top, inner top, outer below).
        cols = eye_mat[0] if s < 0 else eye_mat[1]
        for (xa, xb, ya, yb), m in zip(((2.5, 3.5, 2.5, 3.5), (1.5, 2.5, 2.5, 3.5), (2.5, 3.5, 1.5, 2.5)), cols):
            x0, x1 = sorted((cx + s * xa * U, cx + s * xb * U))
            lib.drape_patch(bm, top, x0, x1, cy + ya * U, cy + yb * U, nx=2, ny=2, lift=0.35 * U,
                            depth=1.8 * U, mat_index=m, smooth=True)


def build_one(sprite, name, turn, centre):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(121, emission_strength=4.0),  # 0 left light, outer top: orange
        pal(119, emission_strength=4.0),  # 1 left light, inner top: red
    ]
    # Each part in its mid-tone; the sprite's white streaks on the arcs and silver lobes on the core
    # are sheen on polished metal, and its black ring is the outline the game draws itself, so none
    # of that is painted on: the metallic material and the game's lights make the shine.
    mats += [
        pal(10, metallic=0.85, roughness=0.22),  # 2 ring arcs: polished grey metal
        pal(9, metallic=0.8, roughness=0.25),  # 3 core dome: polished grey metal
        pal(4, metallic=0.5, roughness=0.45),  # 4 the core's centre crease (a real cut-in groove)
    ]
    RING, CORE, GROOVE = 2, 3, 4
    mats += [
        pal(117, emission_strength=4.0),  # 5 left light, outer below: dark red
        pal(120, emission_strength=4.0),  # 6 right light, outer top: orange
        pal(118, emission_strength=4.0),  # 7 right light, inner top and outer below: dark red
    ]
    EYES = ((0, 1, 5), (6, 7, 7))  # per side (left, right): outer top, inner top, outer below
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
        lib.polyline_tube(bm, pts, TUBE_R, sides=10, mat_index=RING)

    build_core(bm, cx, cy, CORE, GROOVE, EYES, CORE)
    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    by_index = {f["index"]: f for f in sprite["frames"]}
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        f = by_index[frame]
        obj = build_one(sprite, name, k * math.pi / 8, frame_centre(f))
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
