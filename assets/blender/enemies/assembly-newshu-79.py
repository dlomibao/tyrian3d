"""Wrecked machine (newshu.shp, assembly of 7 pieces): a 3D version of its sprites, built whole and
cut into the pieces.

Seen in episode 1 (level 1.19) and episode 3 (level 3.23), on the ground. Seven 2x2 enemies make
one 72 x 84 px structure (sprite.json `assemblyLayout`): newshu-1, -3, -5 along the top,
newshu-39, -41, -43 below them and newshu-79 under the middle. From the top: a row of posts (a tall
grey one with a red slot, a grey one with a pale purple crystal on top, red pillars and a grey
drum), then a dark body strewn with wreckage on the left (red pillars and stubs, purple plates,
grey blocks, a red pipe), a purple bar and a dark red wedge in the middle, grey pipes on the right
and a purple lens in a grey housing at the right end; a stalk runs down to a turret on a blue pad
(newshu-79): a dark round block with a grey rim, a purple panel with red stripes on top, a red tank
on its left and a red box behind.

Everything stands on a low dark base traced from the sprite's silhouette. The pieces have one
frame each. Shared parts (the posts, the stalk and the lens) are in lib_b127, which the other
version of the right-hand block (assembly-newshu-15.py) also uses.

Run: blender --background --python assets/blender/enemies/assembly-newshu-79.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b127 as lib  # noqa: E402

NAME = "assembly-newshu-79"
ROOT = common.repo_root(__file__)
PIECES = [1, 3, 5, 39, 41, 43, 79]
W, H = 72, 84
BLUE = range(96, 103)


def build(b, pixels):
    # Low dark base under the whole structure (not the blue pad round the turret).
    b.pixel_slab(lib.without_strays(pixels), lambda v: v >= 0 and v not in BLUE, 0.0, 0.08, 2)

    lib.towers(b, red_column_end=26)
    lib.grey_column(b, 25.0)
    lib.stem(b)
    lib.disc(b, 90, 93)

    # -- upper left: posts and stubs (rows 19-30) --
    b.box(20, 22, 19, 22, 0.0, 0.34, 9, bevel=0.4, top=13)
    b.box(21, 22, 22, 26, 0.0, 0.3, 72, bevel=0.4, top=75)
    b.box(20, 20, 23, 26, 0.0, 0.26, 7, bevel=0.3)
    b.box(17, 20, 25, 30, 0.0, 0.28, 72, bevel=0.5, top=73)
    b.box(18, 19, 28, 29, 0.27, 0.29, 77)
    b.box(16, 16, 29, 30, 0.0, 0.2, 8, bevel=0.3)
    b.box(27, 27, 20, 26, 0.0, 0.18, 162, bevel=0.3)
    b.box(28, 30, 24, 26, 0.0, 0.22, 70, bevel=0.3, top=73)
    b.box(8, 9, 26, 32, 0.0, 0.34, 72, bevel=0.5, top=75)
    # Debris between them: brown struts and red stubs (columns 20-29, rows 28-36).
    b.box(22, 23, 28, 30, 0.0, 0.14, 162, bevel=0.3, top=19)
    b.box(24, 27, 30, 30, 0.0, 0.18, 72, bevel=0.3, top=73)
    b.box(25, 27, 31, 32, 0.0, 0.12, 162, bevel=0.3, top=16)
    b.box(20, 20, 31, 33, 0.0, 0.2, 70, bevel=0.3, top=71)
    b.box(21, 22, 33, 36, 0.0, 0.1, 162, bevel=0.3)
    b.box(27, 29, 35, 36, 0.0, 0.2, 71, bevel=0.3, top=73)
    b.box(28, 28, 31, 33, 0.0, 0.14, 162, bevel=0.3)
    b.box(10, 10, 29, 32, 0.0, 0.14, 19, bevel=0.2)

    # -- grey blocks under the tall post (columns 32-41, rows 20-28) --
    b.box(32, 37, 20, 27, 0.0, 0.2, 5, bevel=0.4, top=6)
    b.box(32, 33, 23, 28, 0.0, 0.3, 11, bevel=0.4, top=12)
    b.box(33, 37, 23, 23, 0.0, 0.25, 11, bevel=0.3)
    b.box(35, 36, 24, 26, 0.0, 0.27, 7, bevel=0.3, top=10)
    b.box(38, 41, 24, 25, 0.0, 0.22, 8, bevel=0.3, top=8)
    b.box(37, 41, 26, 26, 0.0, 0.24, 73, bevel=0.3, top=75)
    b.box(42, 43, 25, 30, 0.0, 0.32, 72, bevel=0.4, top=75)
    b.box(40, 41, 28, 31, 0.0, 0.26, 6, bevel=0.3, top=8)

    # -- right: grey frame with a red panel, pipes (columns 44-55, rows 20-37) --
    b.box(47, 54, 20, 28, 0.0, 0.3, 5, bevel=0.5, top=6)
    b.box(50, 52, 22, 27, 0.0, 0.33, 70, bevel=0.4, top=73)
    b.box(54, 54, 20, 30, 0.0, 0.32, 8, bevel=0.3)
    b.box(44, 46, 20, 27, 0.0, 0.16, 3, bevel=0.3)
    b.loft_x(30.4, [(44.6, 1.4, 0.11, 0.14), (54.4, 1.4, 0.11, 0.14)], 8, sides=8)
    b.loft_x(33.6, [(40.4, 1.5, 0.13, 0.15), (55.5, 1.5, 0.13, 0.15)], 8, sides=8)
    b.loft_x(33.6, [(49.8, 1.7, 0.15, 0.15), (52.6, 1.7, 0.15, 0.15)], 11, sides=8)
    b.loft_y(42.5, [(34.6, 1.4, 0.12, 0.13), (45.0, 1.4, 0.12, 0.13)], 5, sides=8)
    b.box(43, 46, 35, 37, 0.0, 0.24, 8, bevel=0.4, top=10)
    b.box(44, 46, 38, 44, 0.0, 0.2, 69, bevel=0.3)
    b.box(47, 48, 39, 42, 0.0, 0.16, 5, bevel=0.3)
    b.box(49, 53, 39, 43, 0.0, 0.18, 19, bevel=0.3)
    b.box(50, 53, 39, 40, 0.0, 0.24, 73, bevel=0.4, top=76)
    b.box(52, 54, 36, 37, 0.0, 0.16, 7, bevel=0.3)

    # -- middle: purple box, red wedge, purple bar, grey drum (columns 22-39, rows 29-46) --
    b.box(36, 39, 29, 32, 0.0, 0.34, 90, bevel=0.5, top=91)
    b.box(36, 39, 33, 33, 0.0, 0.2, 82, bevel=0.3)
    b.prism([(35, 35), (39, 35), (39, 44), (38, 44), (35, 41)], 0.0, 0.3, 69, bevel=0.5)
    b.box(36.3, 38.6, 35, 35, 0.28, 0.315, 73)
    b.box(25, 33, 39, 42, 0.0, 0.26, 90, bevel=0.6)
    b.loft_x(42.4, [(25.3, 0.7, 0.04, 0.24), (33.7, 0.7, 0.04, 0.24)], 93, sides=6)
    b.box(25, 33, 43, 43, 0.0, 0.16, 86, bevel=0.3)
    b.loft_x(36.6, [(29.6, 2.0, 0.13, 0.14), (34.2, 2.0, 0.13, 0.14)], 8, sides=10)
    b.box(29, 31, 31, 33, 0.0, 0.16, 162, bevel=0.3)
    b.box(29, 30, 32, 33, 0.0, 0.2, 73, bevel=0.3, top=75)
    b.loft_x(37.5, [(22.2, 0.9, 0.07, 0.12), (28.8, 0.9, 0.07, 0.12)], 75, sides=8)
    b.box(22, 28, 38, 38, 0.0, 0.08, 164, bevel=0.2)
    b.box(27, 28, 29, 30, 0.0, 0.18, 72, bevel=0.3, top=73)

    # -- left: red stubs, grey block, purple plates, brown blocks (columns 8-27, rows 31-46) --
    b.box(20, 23, 40, 43, 0.0, 0.24, 72, bevel=0.4, top=73)
    b.loft_x(43.5, [(20.6, 0.6, 0.05, 0.2), (23.6, 0.6, 0.05, 0.2)], 77, sides=6)
    b.box(18, 19, 40, 41, 0.0, 0.16, 71, bevel=0.3)
    b.box(19, 23, 44, 46, 0.0, 0.12, 19, bevel=0.3)
    b.box(26, 27, 45, 46, 0.0, 0.12, 19, bevel=0.3, top=70)
    b.box(16, 20, 34, 37, 0.0, 0.26, 8, bevel=0.4, top=10)
    b.box(12, 15, 31, 32, 0.0, 0.22, 72, bevel=0.4, top=75)
    b.box(12, 15, 33, 34, 0.0, 0.1, 19, bevel=0.3)
    b.box(8, 10, 33, 39, 0.0, 0.26, 88, bevel=0.5, top=89)
    b.box(11, 15, 39, 42, 0.0, 0.2, 88, bevel=0.5)
    b.box(12, 14, 36, 38, 0.0, 0.12, 82, bevel=0.3, top=84)

    # -- the turret on its blue pad (newshu-79, columns 24-47, rows 56-83) --
    b.box(24, 47, 56, 83, 0.0, 0.02, 98)
    for c0, c1, r0, r1 in ((24, 27, 56, 60), (43, 47, 56, 60), (24, 33, 80, 83), (35, 41, 82, 83), (43, 47, 80, 83)):
        b.box(c0, c1, r0, r1, 0.0, 0.03, 101, bevel=0.2, top=102)
    b.prism([(25, 62), (27, 61), (42, 60.5), (46, 62), (47, 64), (47, 74), (46, 76.5), (44, 78.6), (34, 78.6),
             (30, 77.5), (27.5, 75.5), (25, 74)], 0.0, 0.18, 2, bevel=0.5)
    b.prism([(29, 63), (31, 61.6), (43, 61.6), (45.4, 63), (46, 66), (46, 71), (44.5, 73.5), (42, 74.4),
             (32, 74.4), (30, 73.4), (29, 71)], 0.0, 0.26, 5, bevel=0.8, top=2)
    b.box(35, 41, 65, 68, 0.0, 0.34, 90, bevel=0.4, top=90)
    b.box(36, 36, 65, 68, 0.3, 0.345, 72)
    b.box(39, 39, 64, 68, 0.3, 0.345, 73)
    b.box(35, 41, 69, 70, 0.0, 0.3, 84, bevel=0.3)
    for c in (35, 37, 39):
        b.box(c, c, 72, 73, 0.1, 0.28, 70, bevel=0.2)
    b.loft_y(26.5, [(61.6, 1.2, 0.1, 0.14), (62.2, 1.6, 0.14, 0.14), (71.4, 1.6, 0.14, 0.14), (72.0, 1.2, 0.1, 0.14)],
             69, sides=8)
    b.box(25, 25, 62.4, 70.4, 0.18, 0.27, 72)
    b.box(31, 34, 58, 62, 0.0, 0.3, 70, bevel=0.5, top=75)
    b.box(29, 29, 62, 66, 0.0, 0.27, 10, bevel=0.3, top=13)


def main():
    placed = []
    for f in PIECES:
        c, r = lib.sheet_origin(f)
        placed.append((f"newshu-{f}", c, r))
    pixels, colors = lib.grid_pixels(ROOT, placed, W, H)
    palette = {"name": NAME, "colors": colors}
    mats = lib.Mats(palette, "nshu79", lib.material_settings())
    grid = lib.Grid(W, H)
    b = lib.Builder(grid, mats)
    build(b, pixels)
    coll = common.reset_collection(NAME)
    obj = b.finish(NAME, coll)

    # Each piece's centre relative to the grid's centre, in px (the layout's cx/cy agree with this).
    layout = [(name, c + 12 - W // 2, r + 14 - H // 2) for name, c, r in placed]
    sprite = common.load_sprite(ROOT, "newshu-79")
    for e in sprite["assemblyLayout"]:
        mine = next(item for item in layout if item[0] == e["model"])
        assert (e["cx"] - 56, e["cy"] - 10) == mine[1:], (e, mine)
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in layout:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.grid_png(out.with_name(f"{out.stem}-sprite.png"), pixels, colors)
        common.render_preview([obj], str(out), ref, size=6, view_px=640)
        for name, _, _ in layout:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
