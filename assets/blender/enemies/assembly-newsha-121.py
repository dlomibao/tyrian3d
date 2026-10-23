"""Tan bunker with a ball turret (newsha.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 3 (levels 3.2 and 3.25). Four 2x2 ground pieces make one 48x56 px concrete
block: newsha-83 (top left), newsha-85 (top right), newsha-121 (bottom left) and newsha-123
(bottom right). The block has chamfered top corners, a light lip along its top edge and light
ribs on its upper deck, a lower, darker terrace along the bottom split by a seam, and a grey
ball turret sitting in a dark round socket where the four pieces meet.

The sprite.json layout gives newsha-83, -85 and -123's screen centres; newsha-121 is the
fourth corner (column 128, row 38), where the catalogue snapshot shows the ring newsha-87
after it was destroyed.

The whole block is built once in assembly coordinates and cut into the pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsha-121.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b107 as lib  # noqa: E402

NAME = "assembly-newsha-121"
ROOT = common.repo_root(__file__)
# Screen centres of the pieces; the assembly's centre (screen 140, 24) is the Blender origin.
LAYOUT = [("newsha-83", 128, 10), ("newsha-85", 152, 10), ("newsha-121", 128, 38), ("newsha-123", 152, 38)]
CX0, CY0 = 140, 24
G = lib.Grid(48, 56)  # assembly pixel (0, 0) is newsha-83's top-left corner

DECK = 0.44  # height of the upper deck
TERRACE = 0.24  # height of the lower terrace


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsha121"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(26, metallic=0.05, roughness=0.8),  # 0 tan deck
        pal(28, metallic=0.05, roughness=0.75),  # 1 light lip and ribs
        pal(23, metallic=0.05, roughness=0.85),  # 2 darker sides
        pal(20, metallic=0.05, roughness=0.85),  # 3 brown terrace
        pal(22, metallic=0.05, roughness=0.8),  # 4 terrace ridges
        pal(17, metallic=0.0, roughness=0.9),  # 5 seam
        pal(3, metallic=0.3, roughness=0.6),  # 6 dark socket
        pal(6, metallic=0.7, roughness=0.35),  # 7 grey collar
        pal(8, metallic=0.8, roughness=0.2),  # 8 grey ball
    ]
    DECKM, LIGHT, SIDE, TERR, RIDGE, SEAM, SOCKET, COLLAR, BALL = range(len(mats))
    bm = bmesh.new()
    g = G

    # Upper block: chamfered top corners, rows 14-41, columns 10-39, bevelled top edge.
    lib.bevel_plate(bm, g, [(10, 17), (13, 14), (36, 14), (39, 17), (39, 41.5), (10, 41.5)],
                    0.0, DECK, 1.0, mat=SIDE, top_mat=DECKM)
    # Lower terrace (rows 41-52), split by a seam at column 22.
    lib.bevel_plate(bm, g, [(10, 41), (22, 41), (22, 52), (11, 52), (10, 51)], 0.0, TERRACE, 0.8,
                    mat=TERR, top_mat=TERR)
    lib.bevel_plate(bm, g, [(23, 41), (39, 41), (39, 52), (23, 52)], 0.0, TERRACE, 0.8,
                    mat=TERR, top_mat=TERR)
    lib.box(bm, g, 21.8, 41, 23.2, 52, 0.0, TERRACE - 0.08, mat=SEAM)
    # Light ridges across the terrace (rows 42 and 48).
    for r in (42.6, 47.6):
        lib.box(bm, g, 10.6, r, 21.6, r + 0.9, TERRACE - 0.01, TERRACE + 0.015, mat=RIDGE)
        lib.box(bm, g, 23.4, r, 38.4, r + 0.9, TERRACE - 0.01, TERRACE + 0.015, mat=RIDGE)

    # Light lip along the top edge (rows 15-17) and ribs on the deck.
    top = DECK + 0.025
    lib.box(bm, g, 13.2, 14.6, 36.0, 17.0, DECK - 0.01, top, mat=LIGHT)
    lib.box(bm, g, 13.0, 17.0, 14.0, 40.5, DECK - 0.01, top, mat=LIGHT)  # column 13
    lib.box(bm, g, 11.0, 33.0, 21.0, 34.0, DECK - 0.01, top, mat=LIGHT)  # row 33, left
    lib.box(bm, g, 21.0, 35.5, 22.0, 41.0, DECK - 0.01, top, mat=LIGHT)  # column 21, low
    lib.box(bm, g, 35.0, 33.5, 36.0, 41.0, DECK - 0.01, top, mat=LIGHT)  # column 35, low
    lib.box(bm, g, 32.0, 34.0, 35.0, 35.0, DECK - 0.01, top, mat=LIGHT)  # row 34, right
    lib.box(bm, g, 36.2, 17.5, 38.2, 41.0, DECK - 0.06, DECK - 0.005, mat=SIDE)  # right bevel strip

    # Ball turret: a dark socket (columns 16-32, rows 19-35), a grey collar and the ball.
    lib.cylinder(bm, g, 24.5, 27.0, DECK - 0.02, DECK + 0.01, 8.2, mat=SOCKET, segments=20)
    lib.torus(bm, g, 24.5, 27.0, DECK + 0.03, 7.2, 1.0, 0.05, mat=COLLAR, segments=24, sides=6)
    lib.ellipsoid(bm, g, 23.4, 26.2, DECK - 0.02, 6.6, 6.6, 0.34, mat=BALL, segments=18, rings=9,
                  cut_below=DECK)

    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsha-83's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsha-83")
    for name, _, _ in LAYOUT:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole block's sprite as one 48 x 56 image (what render_preview expects for size 4)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(name, cx - CX0, cy - CY0) for name, cx, cy in LAYOUT]
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in LAYOUT:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_args()
    if out:
        out = Path(out)
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name, _, _ in LAYOUT:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
