"""Brain (newsh5.shp frames 233, 235, 237, 239: an assembly of four pieces): a 3D version of its sprites.

Seen in episode 4 (level 22). Four 2x2 enemies side by side make one 96x28 px brain: two
hemispheres split by a dark fissure down the middle, their surface packed with pink folds (gyri)
between dark grooves, brightest on the inner halves. Each hemisphere is a low rounded lump whose
outline follows the sprite row by row; the folds are rounded ridges fitted to the sprite's
highlights, set into its surface and coloured from the pixels under them.

The whole brain is built once in assembly coordinates and cut into the four pieces with
common.split_assembly. One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-233.py [-- --preview out.png]
(the preview is the whole brain; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b029 as lib  # noqa: E402

NAME = "assembly-newsh5-233"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-233", "newsh5-235", "newsh5-237", "newsh5-239"]
FISSURE = 47  # column of the dark fissure between the hemispheres


def spans(pixels, left_half):
    """Per-row outline of one hemisphere: (row, left edge, right edge). The outer edge follows the
    sprite (lightly smoothed); the inner edge runs straight along the fissure."""
    outer = []
    for line in pixels:
        if left_half:
            outer.append(min(c for c in range(FISSURE + 1) if line[c] >= 0))
        else:
            outer.append(max(c for c in range(FISSURE, len(line)) if line[c] >= 0) + 1)
    n = len(outer)
    smooth = [(outer[max(i - 1, 0)] + 2 * outer[i] + outer[min(i + 1, n - 1)]) / 4 for i in range(n)]
    if left_half:
        return [(r, smooth[r], FISSURE - 1.0) for r in range(n)]
    return [(r, FISSURE + 1.5, smooth[r]) for r in range(n)]


def body_spans(rows, top, bottom):
    """Body spans at pixel centres, ends at the tile edges; slightly rounded at the cut edges."""
    res = []
    n = len(rows)
    for r, left, right in rows:
        k = 1.0 if 1 <= r <= n - 2 else 0.8
        res.append((r + 0.5, left, right, top * k, bottom * k))
    r, left, right = rows[0]
    res.insert(0, (0.0, left + 0.5, right - 0.5, top * 0.55, bottom * 0.55))
    r, left, right = rows[-1]
    res.append((float(n), left + 0.5, right - 0.5, top * 0.55, bottom * 0.55))
    return res


def build(colors, pixels, grid):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    pal = lambda i, **kw: common.palette_material(sprite, i, "ns5b233", **kw)  # noqa: E731
    mats = [
        pal(64, metallic=0.0, roughness=0.9),  # 0 fissure
        pal(66, metallic=0.05, roughness=0.75),  # 1 deep grooves (the hemisphere under the folds)
        pal(68, metallic=0.1, roughness=0.6),  # 2 dark folds
        pal(70, metallic=0.1, roughness=0.5),  # 3 folds
        pal(72, metallic=0.1, roughness=0.45),  # 4 light folds
        pal(74, metallic=0.1, roughness=0.4),  # 5 lighter folds
        pal(76, metallic=0.1, roughness=0.35),  # 6 bright highlights
        pal(78, metallic=0.1, roughness=0.3),  # 7 brightest
    ]

    def slot(i):
        if not 64 <= i <= 79:
            return None
        return min(max((i - 64) // 2 + 1, 1), 7) if i >= 66 else 1

    bm = bmesh.new()
    halves = []
    for left_half in (True, False):
        rows = spans(pixels, left_half)
        body = lib.Body(grid, body_spans(rows, 0.3, 0.14), power=0.9)
        n0 = len(bm.faces)
        body.build(bm, mat=1, sides=40)
        bm.faces.ensure_lookup_table()
        lib.paint(bm, pixels, grid, slot, faces=bm.faces[n0:])
        halves.append(body)

    def surface_for(x, y):
        return halves[0] if x < grid.X(FISSURE - 0.5) else halves[1]

    class Surface:
        def top(self, x, y):
            return surface_for(x, y).top(x, y)

    paths = lib.trace_ridges(pixels, min_level=4, drop=3.5, max_len=14)
    n = lib.ridge_tubes(bm, paths, pixels, grid, Surface(), slot, width=2.0, height=0.04,
                        height_per_level=0.003, sink=0.35)
    print(f"{n} folds")

    # The fissure: a dark trough between the hemispheres, filling the gap in the outline.
    lib.plate(bm, [(grid.X(FISSURE - 2.5), grid.Y(-0.5)), (grid.X(FISSURE - 2.5), grid.Y(27.5)),
                   (grid.X(FISSURE + 2.5), grid.Y(27.5)), (grid.X(FISSURE + 2.5), grid.Y(-0.5))][::-1],
              -0.1, 0.03, mat=0)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    pixels, colors, w, h, (sx0, sy0), layout = lib.assembly_pixels(ROOT, PIECES)
    grid = lib.Grid(w, h)
    obj = build(colors, pixels, grid)
    # Screen position of the grid's centre (the Blender origin).
    cx0, cy0 = sx0 + w / 2, sy0 + h / 2
    pieces = common.split_assembly(obj, [(n, layout[n][0] - cx0, layout[n][1] - cy0) for n in PIECES])
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.write_png(Path(tempfile.mkdtemp()) / "assembly.png", pixels, colors)
        common.render_preview([obj], str(out), str(ref), size=(w, h), view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
