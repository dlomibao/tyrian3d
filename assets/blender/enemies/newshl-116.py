"""Spiked molten mine (newshl.shp 116): a 3D version of its sprite.

Seen in episode 4 (levels 40 and 45), alongside the molten rocks (newshl-115). A lava ball about
10 px across with four dark spikes pointing up, down, left and right; the white-hot core glows just
above its centre. The ball is a sphere as tall as it is wide (slightly fuller on the diagonals, as
the sprite's body is) on a fine grid. Everything seen from above takes the sprite pixel under it,
with soft blends between pixels and a soft white glow around the core (the hot colours glow in
game, and the finish is matte); the underside takes a blurred copy. Its shading normals lean
towards the light so it reads lit all over, as a glowing ball. The spikes are dark-red cones.

Run: blender --background --python assets/blender/enemies/newshl-116.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "newshl-116"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


# The sprite's heat ramp, darkest to white-hot: the near-black index 1 (the pit, and the outline's
# corners) below the darkest red.
RAMP = [1, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 127]
# The palette colours the ball is painted in (one material each), with their glow in game.
BANDS = [(1, 0.0), (112, 0.0), (113, 0.0), (114, 0.0), (115, 0.3), (116, 0.5), (117, 0.8),
         (118, 1.0), (119, 1.3), (120, 1.6), (121, 2.0), (122, 2.5), (123, 3.0), (124, 3.5),
         (127, 5.0)]
# Faces with normal z above TOP_NZ (what the camera sees from above) take the sprite pixel under
# them, blending into the next pixel over the SOFT px either side of the pixel edge (a smoothstep),
# so each pixel's colour holds at its centre and the ball's heat changes in gradients a pixel long
# rather than hard blocks. The sides and underside take a blurred copy (weights: the pixel, its edge
# neighbours, its corners).
SOFT = 0.4
BLUR_SIDE = (4, 2, 1)
TOP_NZ = -0.3
# The white-hot core (column 5, row 6) glows past its pixel: heat at least GLOW[0] within GLOW[1] px
# of its centre, fading to nothing at GLOW[2] px up and left (towards its yellow neighbours) and
# GLOW[3] px elsewhere, short of its neighbours' centres, which keep the sprite's colours; so the
# core is a soft white spot rather than a square.
HOT = (5, 6)
GLOW = (14, 0.45, 1.9, 1.05)
N_CUBE = 18
# The outline ring's palette indices (near-black and the darkest red), and how much cooler (in RAMP
# steps) than its inner neighbours a ring pixel is painted.
OUTLINE_INDICES = (1, 112)
RING_COOL = 1.0
# The spikes are hardened crust, drawn 1 px wide so all their 112 pixels are outline; their centre
# pixels are 114-116, so they take 115, matte like rock.
SPIKE_INDEX = 115
# The lava glows, so it should read lit all over rather than dark on the side away from the light
# with a grey sheen where it faces the viewer: the ball's shading normals lean LEAN times their own
# length towards LEAN_DIR (up and to the left, towards the game's sun; Blender axes). They still
# vary with the surface, so the ball keeps a soft rounded shading.
LEAN_DIR = (-1.0, 0.1, 1.0)
LEAN = 3.5


def heat_field(grid, blur):
    """The sprite's heat (position on RAMP) per pixel, averaged over its neighbours with `blur`
    weights (None: unblurred). None where transparent."""
    h, w = grid.h, grid.w
    raw = [[None if grid.pixels[r][c] == -1 else
            (RAMP.index(grid.pixels[r][c]) if grid.pixels[r][c] in RAMP else 1)
            for c in range(w)] for r in range(h)]

    def opaque(r, c):
        return 0 <= r < h and 0 <= c < w and grid.pixels[r][c] != -1

    # The sprite's dark outline ring (the darkest pixels, OUTLINE_INDICES, on the edge of the
    # shape) is its drawn edge, not lava: the game draws its own outline, so those pixels take the
    # mean heat of their inner neighbours and the ball's rim and sides keep the lava's colours.
    ring = {(r, c) for r in range(h) for c in range(w)
            if grid.pixels[r][c] in OUTLINE_INDICES and any(
                not opaque(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1))}
    fixed = [row[:] for row in raw]
    for r, c in ring:
        inner = [raw[r + dr][c + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                 if opaque(r + dr, c + dc) and (r + dr, c + dc) not in ring]
        if inner:
            fixed[r][c] = max(raw[r][c], sum(inner) / len(inner) - RING_COOL)
    raw = fixed
    if blur is None:
        return raw
    out = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if raw[r][c] is None:
                continue
            tot = wsum = 0.0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and raw[rr][cc] is not None:
                        k = blur[abs(dr) + abs(dc)]
                        tot += k * raw[rr][cc]
                        wsum += k
            out[r][c] = tot / wsum
    return out


def soft_step(f):
    """Weight of the next pixel at fraction f (0-1) of the way between two pixel centres: 0 until
    SOFT px before the edge, then a smooth ramp to 1 at SOFT px past it."""
    t = min(1.0, max(0.0, (f - 0.5 + SOFT) / (2 * SOFT)))
    return t * t * (3 - 2 * t)


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = [[int(v) for v in row.split()] if isinstance(row, str) else row
              for row in sprite["frames"][0]["pixels"]]
    grid = lib.Grid(12, 14, pixels)
    mats = lib.Mats(NAME, sprite["colors"])
    # Matte: the lava glows rather than shines.
    bands = [mats(i, metallic=0.0, roughness=0.9, emission_strength=e) for i, e in BANDS]
    spike = mats(SPIKE_INDEX, metallic=0.0, roughness=0.8)
    fields = heat_field(grid, None), heat_field(grid, BLUR_SIDE)

    def heat_at(field, x, y, soft=False):
        """Sample of a heat field at (x, y) units: bilinear, or with soft=True nearly the nearest
        pixel (soft_step); transparent neighbours are skipped."""
        c, r = grid.col(x), grid.row(y)
        c0, r0 = int(math.floor(c)), int(math.floor(r))
        fc, fr = c - c0, r - r0
        if soft:
            fc, fr = soft_step(fc), soft_step(fr)
        tot = wsum = 0.0
        for rr, wr in ((r0, 1 - fr), (r0 + 1, fr)):
            for cc, wc in ((c0, 1 - fc), (c0 + 1, fc)):
                if 0 <= rr < grid.h and 0 <= cc < grid.w and field[rr][cc] is not None:
                    tot += wr * wc * field[rr][cc]
                    wsum += wr * wc
        return tot / wsum if wsum else 0.0

    bm = bmesh.new()
    # The ball: a sphere about 10 px across and as tall, centred on column 5, row 7. Slightly
    # squared off on the diagonals as the sprite's body is, so its corners are covered.
    cx, cy = grid.x(5), grid.y(7)
    rad = 5.15 * lib.U
    # The near-black pixel at column 5, row 9 is painted, not cut: a pit there catches a ring of
    # highlight that reads as an eye from the game camera.

    def shape(x, y, z):
        return 1 + 0.12 * (4 * x * x * y * y) ** 3  # corners only, about +12% on the diagonals

    first = lib.cube_blob(bm, (cx, cy, 0.0), (rad, rad, rad), n=N_CUBE, mat_index=bands[0], bump=shape)
    n_ball_verts = len(bm.verts)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        c = f.calc_center_median()
        top = f.normal.z > TOP_NZ
        h = heat_at(fields[0] if top else fields[1], c.x, c.y, soft=top)
        if top:
            dc, dr = grid.col(c.x) - HOT[0], grid.row(c.y) - HOT[1]
            # Towards the dimmer neighbours (right and below, orange 120) the glow ends sooner.
            end = GLOW[2] if dc <= 0 and dr <= 0 else GLOW[3]
            d = math.hypot(dc, dr)
            h = max(h, GLOW[0] * min(1.0, max(0.0, (end - d) / (end - GLOW[1]))))
        # Band by heat: each band is the RAMP position nearest its palette index.
        best = min(range(len(BANDS)), key=lambda i: abs(RAMP.index(BANDS[i][0]) - h))
        f.material_index = bands[best]

    # Spikes, a little wider at the base than the ball's rim: up past row 0, down past row 13 and
    # out past columns 0 and 10 (the sprite's side spikes cover rows 6-8).
    for (tc, tr), (bc, br), r in (((5, -0.9), (5, 3.0), 1.4), ((5, 13.9), (5, 11.0), 1.4),
                                   ((-0.9, 7), (2.0, 7), 1.6), ((10.9, 7), (8.0, 7), 1.6)):
        base, tip = (grid.x(bc), grid.y(br), 0.0), (grid.x(tc), grid.y(tr), 0.0)
        lib.tube(bm, [(base, r * lib.U), (tip, 0)], sides=8, mat_index=spike)
    obj = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)
    # The ball's vertices come first (to_mesh keeps the bmesh order); the spikes keep their own.
    lean = Vector(LEAN_DIR).normalized() * LEAN
    normals = [(Vector(v.normal) + lean).normalized() if i < n_ball_verts else Vector(v.normal)
               for i, v in enumerate(obj.data.vertices)]
    obj.data.normals_split_custom_set_from_vertices(normals)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
