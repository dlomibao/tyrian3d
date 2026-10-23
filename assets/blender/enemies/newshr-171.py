"""Brown rock (newshr.shp frame 171): a 3D version of its sprite.

Seen in episode 3 (levels 19 and 4). A small tumbling rock, 9 x 11 px: a rounded lump of brown
stone lit from the upper left, its lightest face near the top and a speck of dark red at its top
tip. One frame, one model: a lumpy rock whose outline follows the sprite and whose faces take the
colour of the sprite pixel under them, the lighter pixels standing a little prouder.

Run: blender --background --python assets/blender/enemies/newshr-171.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b022 as lib  # noqa: E402

NAME = "newshr-171"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def lumps(x, y, z):
    """Irregular facets so it reads as stone, not an egg."""
    return 1 + 0.08 * math.sin(3.7 * x + 0.9) * math.cos(3.1 * y - 1.2) + 0.06 * math.sin(4.9 * z + 2.3 * y + 0.5)


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14, sprite["frames"][0]["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    # Brown stone in pairs of shades (162-171), and the dark red speck (66, 67).
    shades = {i: mats(i + 1 if i % 2 == 0 else i, roughness=0.9) for i in range(162, 172)}
    red = mats(67, roughness=0.8)

    def slot(i):
        if i in (66, 67):
            return red
        return shades.get(i, shades[163])

    def brightness(i):
        return 0.3 if i in (66, 67) else (i - 162) / 9

    bm = bmesh.new()
    lib.rock(bm, grid, 0.21, slot, brightness, n=10, relief=0.22, lumps=lumps, under_slot=shades[163])
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
