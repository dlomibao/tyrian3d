"""Corner of a blue lump (newsh0.shp frame 3): a 3D version of its sprite.

Seen in episode 2 (level 2.12), briefly. The sprite is a single blue pixel in its bottom-left
corner: the last bit of the rounded blue lump at the bottom right of newsh0-1, its neighbour in
the row of pieces. Modelled as that lump's corner, a small quarter dome cut at the tile's left
and bottom edges.

Run: blender --background --python assets/blender/enemies/newsh0-3.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "newsh0-3"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)


def build(sprite):
    coll = common.reset_collection(NAME)
    m = lib.Mats(NAME, sprite["colors"])
    LUMP = m(52, metallic=0.45, roughness=0.4)
    bm = bmesh.new()
    lib.ellipsoid(bm, G.ex(0), G.ey(28), -0.02, 1.15 / 12, 1.3 / 12, 0.07, mat=LUMP, segments=12, rings=6)
    lib.clip(bm, [((G.ex(0), 0, 0), (-1, 0, 0)), ((0, G.ey(28), 0), (0, -1, 0))])
    return lib.to_object(NAME, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], f"enemies/{NAME}", sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite["frames"][0]["image"])


if __name__ == "__main__":
    main()
