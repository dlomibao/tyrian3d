"""Big asteroid (newshd.shp 7, 9, 45 and 47, a 2x2 block): a 3D version of its sprites.

Seen in episode 1 (level 1.5). Four 2x2 sprites make one grey boulder, 40 x 50 px, leaning to the
right: a big flat pale facet on its upper left, a knobbly ridge of lumps down its right side (one
on top, two beside the facet, a ringed crater in the middle and one below it), a broad lump on
the lower left with a bright ridge along its left edge, and a dim bulge at the bottom. The rock
follows the sprites' outline; its top rises in those lumps (and a little with the sprites'
shading, so the cracks sink), the facet is flattened, and each face takes the grey (or blue grey)
of the sprite pixel under it.

Built whole in assembly coordinates, then cut into the four pieces (newshd-7 top left, newshd-9
top right, newshd-45 bottom left, newshd-47 bottom right). Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newshd-45.py [-- --preview out.png]
(the preview is the whole rock; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b036 as lib  # noqa: E402
from lib_b036 import common  # noqa: E402

NAME = "assembly-newshd-45"
PIECES = ["newshd-7", "newshd-9", "newshd-45", "newshd-47"]
ROOT = common.repo_root(__file__)
CENTRE = (94, -2)  # the 48 x 56 block's centre in screen px (pieces at cx 82/106, cy -16/12)


def pieces():
    """{name: sprite} and the layout [(name, cx, cy)] relative to the block's centre."""
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    layout = [(e["model"], e["cx"] - CENTRE[0], e["cy"] - CENTRE[1])
              for e in sprites[PIECES[0]]["assemblyLayout"]]
    return sprites, layout


def merged_pixels(sprites, layout):
    """The whole rock's pixels, 48 x 56, from each piece's first frame."""
    grid = [[-1] * 48 for _ in range(56)]
    for name, cx, cy in layout:
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, line in enumerate(sprites[name]["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid


def build(pixels, colors):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(48, 56, pixels)
    mats = lib.Mats(NAME, colors)
    under = mats(4, metallic=0.1, roughness=0.9)
    bm = bmesh.new()
    lumps = [
        (34.0, 10.0, 6.5, 0.10),  # on top, right
        (19.5, 21.0, 10.0, 0.06),  # under the big facet
        (38.0, 16.5, 5.5, 0.10),  # beside the facet, right
        (30.0, 27.5, 5.0, 0.10),  # the ringed crater's rim, middle
        (39.5, 27.5, 4.0, 0.05),  # right edge
        (36.5, 35.0, 5.5, 0.09),  # below the crater
        (19.0, 38.0, 8.5, 0.12),  # broad lump, lower left
        (26.0, 46.5, 7.0, 0.04),  # dim bulge at the bottom
    ]
    flats = [(19.5, 21.0, 9.5, 0.44)]  # the big pale facet, upper left
    first = lib.rock(bm, grid, (26.5, 28.5), top=0.42, bottom=0.3, lumps=lumps, flats=flats, shade=0.08,
                     sigma=1.3, colors=colors, n=22, mat_index=under)
    lib.paint(bm, first, grid, lambda i: mats(i, metallic=0.1, roughness=0.85), min_nz=-0.3)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def composite_png(pixels, colors, out):
    """The whole rock's sprite as one 48 x 56 image."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for r, line in enumerate(pixels):
        for c, v in enumerate(line):
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprites, layout = pieces()
    colors = lib.merged_colors(sprites.values())
    pixels = merged_pixels(sprites, layout)
    obj = build(pixels, colors)
    cut = common.split_assembly(obj, layout)
    for name in PIECES:
        common.export_sprite_model(ROOT, [cut[name]], f"enemies/{name}", sprites[name]["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=(48, 56), view_px=480)
        for name in PIECES:
            img = ROOT / "reference" / "models" / name / sprites[name]["frames"][0]["image"]
            common.render_preview([cut[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
