"""Rock wall (newsh3.shp 166, 168, 170 over 204, 206, 208): a 3D version of its sprites.

Seen in episode 4 (levels 4.2 and 4.29). Six 2x2 pieces make a 72x40 px stretch of a sandy rock
wall: a smooth, light top face with a long highlight, broken into darker blocks and crevices along
its lower edge. The stretch tiles end to end (and with the clamp stretch, newsh^ 77-119), so its
left and right ends are cut straight and not rounded off.

Built once in assembly coordinates as one solid, faceted rock (lib_b017.wall_rock: outline from
the sprite, rounded top and bottom, light plates proud, dark cracks sunk, facets in the sprite's
colours), then cut into the six pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-166.py [-- --preview out.png]
(the preview is the whole stretch; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b017 as lib  # noqa: E402

NAME = "assembly-newsh3-166"
ROOT = common.repo_root(__file__)
# Top-left pixel of each piece. The catalogue lists them with the arch (assembly-newsh3-198) but
# gives no layout for them; their edges match up in this order.
PLACEMENTS = [
    ("newsh3-166", 0, 0, 0), ("newsh3-168", 24, 0, 0), ("newsh3-170", 48, 0, 0),
    ("newsh3-204", 0, 28, 0), ("newsh3-206", 24, 28, 0), ("newsh3-208", 48, 28, 0),
]


def build(sheet):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nsh3_166", sheet.colors)
    mask = [[v >= 0 for v in row] for row in sheet.pix]
    bm = bmesh.new()
    lib.wall_rock(bm, sheet, mats, mask)
    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    sheet = lib.Sheet(ROOT, PLACEMENTS)
    obj = build(sheet)
    pieces = lib.export_pieces(ROOT, obj, sheet, PLACEMENTS)
    if "--preview" in sys.argv:
        lib.previews(ROOT, sys.argv[sys.argv.index("--preview") + 1], obj, pieces, sheet)


if __name__ == "__main__":
    main()
