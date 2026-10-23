"""Rock arch (newsh3.shp 162, 164, 241 over 198, 200, 202, 279, 281): a 3D version of its sprites.

Seen in episode 4 (levels 4.2 and 4.29). Eight 2x2 pieces make one 120x56 px span of a sandy rock
arch: from its left foot (198) it climbs to a crown of big faceted boulders (162, 164, 241) and
comes down to the right (279, 281), with the darker, striated inside of the arch under the crown
and open sky through it. The arch carries on past the right and bottom edges (pieces the game
places elsewhere), so the rock isn't rounded off there.

The arch is built once in assembly coordinates as one solid, faceted rock: its outline follows the
sprite, its top rises from the edges into a rounded crown with the sprite's light plates standing
proud and its dark cracks sunk, and every facet takes the sprite's colour under it. Then it is cut
into the eight pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-198.py [-- --preview out.png]
(the preview is the whole arch; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b017 as lib  # noqa: E402

NAME = "assembly-newsh3-198"
ROOT = common.repo_root(__file__)
# Each piece's top-left pixel in the assembly (its sprite.json assemblyLayout, one arch of the
# three in it: 198 at screen (56, 11) is column 0, row 28).
PLACEMENTS = [
    ("newsh3-162", 24, 0, 0), ("newsh3-164", 48, 0, 0), ("newsh3-241", 72, 0, 0),
    ("newsh3-198", 0, 28, 0), ("newsh3-200", 24, 28, 0), ("newsh3-202", 48, 28, 0),
    ("newsh3-279", 72, 28, 0), ("newsh3-281", 96, 28, 0),
]


def build(sheet):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nsh3_198", sheet.colors)
    dark = mats(19, roughness=0.9)  # underside and cut faces
    rock = {i: mats(i, metallic=0.05 if i < 27 else 0.15, roughness=0.85 if i < 27 else 0.6) for i in range(16, 32)}
    mask = [[v >= 0 for v in row] for row in sheet.pix]
    # The crown's right end (column 95, rows 12-27) is a cut edge: measure the rounding as if the
    # rock carried on to the right there.
    dt_mask = [row[:] for row in mask]
    for r in range(28):
        for c in range(96, sheet.w):
            dt_mask[r][c] = mask[r][95]

    def lift(c, r):
        # The crown (rows 0-30) is the top of the arch; the striated inside below it slopes down
        # into the opening.
        return 0.08 if r < 26 else 0.08 - min(0.16, (r - 26) * 0.008)

    bm = bmesh.new()
    lib.rock_shell(bm, sheet, mask, lambda v, _p: rock.get(v, dark), top=0.34, bottom=0.2, edge=0.05,
                   radius=12.0, relief=0.22, step=1.6, bottom_step=5.0, blur_px=2, lum=lambda v: (v - 16) / 15,
                   open_sides="rb", dt_mask=dt_mask, bottom_slot=dark, top_lift=lift)
    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    sheet = lib.Sheet(ROOT, PLACEMENTS)
    obj = build(sheet)
    pieces = lib.export_pieces(ROOT, obj, sheet, PLACEMENTS)
    if "--preview" in sys.argv:
        lib.previews(ROOT, sys.argv[sys.argv.index("--preview") + 1], obj, pieces, sheet)


if __name__ == "__main__":
    main()
