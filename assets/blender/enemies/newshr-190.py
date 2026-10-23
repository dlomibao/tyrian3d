"""Tan rock (newshr.shp frame 190): a 3D version of its sprite.

Seen in episode 3 (levels 19 and 4). A small tumbling rock, 9 x 11 px: an elongated lump of sandy
stone lying on the diagonal from upper right to lower left, lit from the upper left, with darker
brown edges. One frame, one model: a lumpy rock whose outline follows the sprite and whose faces
take the colour of the sprite pixel under them, the lighter pixels standing a little prouder.

Run: blender --background --python assets/blender/enemies/newshr-190.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b022 as lib  # noqa: E402

NAME = "newshr-190"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def lumps(x, y, z):
    """Irregular facets so it reads as stone, not a sausage."""
    return 1 + 0.07 * math.sin(4.1 * x - 0.7) * math.cos(3.3 * y + 0.8) + 0.06 * math.sin(4.5 * z + 2.7 * x + 1.1)


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14, sprite["frames"][0]["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    # Sandy stone in pairs of shades (19-27); 178 and 179 are the darkest brown edge pixels.
    dark = mats(20, roughness=0.9)
    shades = {19: dark, 20: dark, 178: dark, 179: dark}
    for i in range(21, 28):
        shades[i] = mats(i + 1 if i % 2 == 1 and i < 27 else i, roughness=0.9)

    def slot(i):
        return shades.get(i, dark)

    def brightness(i):
        return 0.05 if i in (178, 179) else (i - 19) / 8

    bm = bmesh.new()
    lib.rock(bm, grid, 0.19, slot, brightness, n=10, relief=0.22, lumps=lumps, under_slot=dark)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
