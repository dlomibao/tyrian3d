"""Spiked molten mine (newshl.shp 116): a 3D version of its sprite.

Seen in episode 4 (levels 40 and 45), alongside the molten rocks (newshl-115). A lava ball about
9 px across with four dark spikes pointing up, down, left and right; the white-hot core glows just
above its centre. The ball is a lumpy ellipsoid painted from the sprite's pixels (the hot colours
glow); the spikes are dark-red cones.

Run: blender --background --python assets/blender/enemies/newshl-116.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "newshl-116"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14, sprite["frames"][0]["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    crust = mats(113, metallic=0.0, roughness=0.9)
    warm = mats(116, metallic=0.0, roughness=0.7, emission_strength=0.8)
    hot = mats(119, metallic=0.0, roughness=0.5, emission_strength=2.0)
    hotter = mats(122, metallic=0.0, roughness=0.4, emission_strength=3.0)
    white = mats(127, metallic=0.0, roughness=0.3, emission_strength=5.0)
    spike = mats(112, metallic=0.3, roughness=0.6)

    def slot(i):
        if i <= 114:
            return crust
        if i <= 117:
            return warm
        if i <= 120:
            return hot
        if i <= 124:
            return hotter
        return white

    bm = bmesh.new()
    # The ball: columns 1-9, rows 3-11, centred on column 5, row 7.
    cx, cy = grid.x(5), grid.y(7)
    rx, ry, rz = 4.6 * lib.U, 4.7 * lib.U, 0.2

    def lumps(x, y, z):
        idx = grid.sample(cx + x * rx, cy + y * ry) if z > -0.3 else None
        heat = 0.0 if idx is None else max(0.0, min(1.0, (idx - 115) / 9))
        wobble = 1 + 0.05 * math.sin(3.3 * x + 0.7) * math.cos(2.9 * y + 1.1)
        return wobble * (1.04 - 0.09 * heat * max(0.0, z))

    first = lib.cube_blob(bm, (cx, cy, 0.0), (rx, ry, rz), n=8, mat_index=crust, bump=lumps)
    lib.paint(bm, first, grid, slot)

    # Spikes: up to row 0, down to row 13, out to columns 0 and 10 (rows 6-8).
    for (tc, tr), (bc, br), r in (((5, -0.4), (5, 3.0), 1.3), ((5, 13.4), (5, 11.0), 1.2),
                                   ((-0.4, 7), (2.0, 7), 1.4), ((10.4, 7), (8.0, 7), 1.4)):
        base, tip = (grid.x(bc), grid.y(br), 0.0), (grid.x(tc), grid.y(tr), 0.0)
        lib.tube(bm, [(base, r * lib.U), (tip, 0)], sides=8, mat_index=spike)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
