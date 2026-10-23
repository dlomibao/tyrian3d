"""Molten rock (newshl.shp 115, newsh3.shp 134 and 135): a 3D version of its sprite.

Seen in episode 4 (levels 6, 40 and 45). A round lump of lava, 11 x 13 px: dark red crust broken by
orange and yellow glowing cracks. Frame 135 is the same rock glowing brighter (every index two
steps up), so one model covers all three frames. The rock is a lumpy ellipsoid whose faces take
the colour of the sprite pixel under them, the hot colours glowing.

Run: blender --background --python assets/blender/enemies/newshl-115.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "newshl-115"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def bump(x, y, z):
    """Gentle lumps so the rock isn't a perfect egg."""
    return 1 + 0.07 * math.sin(3.1 * x + 1.3) * math.cos(2.7 * y - 0.4) + 0.05 * math.sin(4.3 * z + 2.9 * x)


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    grid = lib.Grid(12, 14, frame["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    crust = mats(113, metallic=0.0, roughness=0.9)
    warm = mats(116, metallic=0.0, roughness=0.7, emission_strength=0.8)
    hot = mats(119, metallic=0.0, roughness=0.5, emission_strength=2.0)
    hotter = mats(122, metallic=0.0, roughness=0.4, emission_strength=3.0)
    white = mats(125, metallic=0.0, roughness=0.3, emission_strength=4.5)

    def slot(i):
        if i <= 114:
            return crust
        if i <= 117:
            return warm
        if i <= 120:
            return hot
        if i <= 123:
            return hotter
        return white

    bm = bmesh.new()
    # Rows 1-13, columns 0-10: centred on column 5, row 7.
    cx, cy = grid.x(5), grid.y(7)
    rx, ry = 5.4 * lib.U, 6.4 * lib.U

    def lumps(x, y, z):
        # The crust stands proud and the glowing cracks sink in a little.
        idx = grid.sample(cx + x * rx, cy + y * ry) if z > -0.3 else None
        heat = 0.0 if idx is None else max(0.0, min(1.0, (idx - 115) / 9))
        return bump(x, y, z) * (1.03 - 0.08 * heat * max(0.0, z))

    first = lib.cube_blob(bm, (cx, cy, 0.0), (rx, ry, 0.24), n=9, mat_index=crust, bump=lumps)
    lib.paint(bm, first, grid, slot)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
