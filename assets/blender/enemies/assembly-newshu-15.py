"""Wrecked machine, intact right-hand block (newshu.shp frames 15, 17 over 53, 55): a 3D version of
its sprites, built whole and cut into the four pieces.

Seen in episode 1 (level 1.19) and episode 3 (level 3.23) as part of the machine of
assembly-newshu-79. These four 2x2 sprites are another version of that machine's right-hand block
(newshu-3, -5, -41, -43: the same posts along the top, the same stalk and lens), drawn whole where
the other is wrecked: a big grey drum lying across the middle with seams round it, a ledge in front
of it over a glowing-red grille, red ribs on the left, a grey block on the right, and the lens
coloured red instead of purple. The catalogue has no layout for them, so they are placed as on the
sprite sheet (a 48 x 56 px block), which is also where they line up with the machine.

Shared parts (the posts, the stalk and the lens) come from lib_b127. The pieces have one frame each.

Run: blender --background --python assets/blender/enemies/assembly-newshu-15.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b127 as lib  # noqa: E402

NAME = "assembly-newshu-15"
ROOT = common.repo_root(__file__)
# The block covers columns 24-71, rows 0-55 of the machine (assembly-newshu-79's grid).
W, H, C0, R0 = 48, 56, 24, 0
PIECES = {15: (0, 0), 17: (24, 0), 53: (0, 28), 55: (24, 28)}  # top-left corner in the block


def build(b, pixels):
    b.pixel_slab(lib.without_strays(pixels), lambda v: v >= 0, 0.0, 0.08, 2)

    lib.towers(b, red_column_end=25)
    lib.grey_column(b, 24.0)
    lib.stem(b)
    lib.disc(b, 73, 76)

    # The drum lying across the middle (rows 24-34), with seams and a light rib near its right end.
    b.loft_x(29.5, [(23.5, 5.5, 0.17, 0.2), (55.2, 5.5, 0.17, 0.2)], 8, sides=14)
    for c0, c1, mat in ((29.2, 30.2, 5), (36.0, 37.0, 4), (51.8, 53.2, 11)):
        b.loft_x(29.5, [(c0, 5.7, 0.18, 0.2), (c1, 5.7, 0.18, 0.2)], mat, sides=14)
    b.loft_x(26.6, [(24.0, 1.2, 0.03, 0.335), (51.5, 1.2, 0.03, 0.335)], 11, sides=6)
    b.box(26, 30, 23, 23, 0.0, 0.2, 5, bevel=0.3)
    b.box(27, 27, 20, 22, 0.0, 0.16, 162, bevel=0.3)

    # Grey blocks behind it: left of the grey column and on the right (rows 19-24).
    b.box(33, 38, 19, 24, 0.0, 0.3, 4, bevel=0.4)
    b.box(44, 53, 20, 24, 0.0, 0.32, 5, bevel=0.5, top=6)
    b.box(54, 54, 20, 33, 0.0, 0.34, 8, bevel=0.3)

    # The ledge in front of the drum (columns 30-43, rows 33-37) and the red grille under it.
    b.box(33, 43, 33, 37, 0.0, 0.26, 7, bevel=0.5, top=9)
    b.loft_x(35.5, [(33.3, 0.8, 0.04, 0.25), (43.7, 0.8, 0.04, 0.25)], 11, sides=6)
    b.box(30, 32, 33, 37, 0.0, 0.22, 6, bevel=0.4, top=10)
    for c0, c1, r0, r1 in ((33, 35, 38, 45), (42, 43, 38, 45), (36, 41, 45, 45), (36, 41, 43, 43)):
        b.box(c0, c1, r0, r1, 0.0, 0.2, 5, bevel=0.3, top=4)
    b.box(36, 41, 38, 39, 0.0, 0.17, 71)
    b.box(36, 41, 40, 42, 0.0, 0.15, 67)
    b.box(36, 41, 44, 44, 0.0, 0.15, 66)
    b.box(30, 31, 38, 41, 0.0, 0.16, 3, bevel=0.3)

    # Red ribs on the left (columns 24, 26, 28, rows 35-41).
    for c in (24, 26, 28):
        b.box(c, c, 35, 41, 0.0, 0.24, 69, bevel=0.3, top=73)

    # Under the right end: a grey block and a light pipe bent round its corner.
    b.box(44, 54, 35, 38, 0.0, 0.2, 4, bevel=0.4, top=5)
    b.box(45, 54, 44, 44, 0.0, 0.16, 7, bevel=0.3)
    b.box(54, 54, 40, 43, 0.0, 0.18, 9, bevel=0.3, top=11)
    b.box(35, 43, 45, 45, 0.0, 0.14, 4, bevel=0.3)


def main():
    placed = [(f"newshu-{f}", c, r) for f, (c, r) in PIECES.items()]
    pixels, colors = lib.grid_pixels(ROOT, placed, W, H)
    palette = {"name": NAME, "colors": colors}
    settings = lib.material_settings()
    settings[71] = dict(metallic=0.2, roughness=0.4, emission_strength=2.0)  # the grille glows
    mats = lib.Mats(palette, "nshu15", settings)
    b = lib.Builder(lib.Grid(W, H, C0, R0), mats)
    build(b, pixels)
    coll = common.reset_collection(NAME)
    obj = b.finish(NAME, coll)

    layout = [(name, c + 12 - W // 2, r + 14 - H // 2) for name, c, r in placed]
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in layout:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.grid_png(out.with_name(f"{out.stem}-sprite.png"), pixels, colors)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name, _, _ in layout:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
