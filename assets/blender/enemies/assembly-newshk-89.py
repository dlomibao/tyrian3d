"""Fireball (newshk.shp frames 89, 91, 93, assembly of 3 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.12) and 4 (4.4). Three 2x2 enemies side by side make the bottom of
a huge fireball, 72 x 23 px, cut flat at the top of the sprites: a white-hot core with yellow
streaks, an orange layer and a red-orange rim along its slanting sides and broad bottom.

Built whole in assembly coordinates as three nested lofts (rim, yellow layer, white core), each
following the sprite's outline row by row and rounding off at the bottom, with a few lumps and
streaks on the core; then cut into the three pieces with common.split_assembly. All of it glows.

Run: blender --background --python assets/blender/enemies/assembly-newshk-89.py [-- --preview out.png]
(the preview is the whole fireball; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b032 as lib  # noqa: E402

common = lib.common
NAME = "assembly-newshk-89"
ROOT = common.repo_root(__file__)
PIECES = [("newshk-89", 0), ("newshk-91", 24), ("newshk-93", 48)]  # name, first assembly column
W, H = 72, 28  # assembly size in px; its centre (column edge 36, row edge 14) is the origin


def X(c):
    return lib.X(c, W)


def Y(r):
    return lib.Y(r, H)


def extents():
    """Each row's (left edge, right edge) in assembly px, from the sprites' pixels."""
    rows = {}
    for name, off in PIECES:
        frame = common.load_sprite(ROOT, name)["frames"][0]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    lo, hi = rows.get(r, (99, -1))
                    rows[r] = (min(lo, c + off), max(hi, c + off + 1))
    return [rows[r] for r in sorted(rows)]


def layer(bm, ext, inset, bottom, height, zc, mat, sides=12):
    """A loft down the fireball (top row to `bottom` row edge), `inset` px inside the outline,
    `height` half-height at the top, rounding down towards the bottom."""
    path = []
    last = None
    for r, (lo, hi) in enumerate(ext):
        if r + 0.5 >= bottom - 0.3:
            break
        lo, hi = lo + inset, hi - inset
        f = math.sqrt(max(0.0, 1 - ((r + 0.5) / bottom) ** 2.2))
        rr = -0.5 if r == 0 else r  # the first section sits on the flat top edge
        path.append((X((lo + hi) / 2 - 0.5), Y(rr), zc, (hi - lo) / 2 * lib.PX, max(0.015, height * f)))
        last = (lo, hi)
    lo, hi = last
    path.append((X((lo + hi) / 2 - 0.5), Y(bottom - 0.5), zc, (hi - lo) / 2 * 0.8 * lib.PX, 0.01))
    lib.sweep(bm, path, sides=sides, mat=mat, power=3.0, fixed_side=(1, 0, 0))


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshk89"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, roughness=0.6, metallic=0.0, **kw)  # noqa: E731
    mats = [
        pal(119, emission_strength=2.5),  # 0 red rim
        pal(121, emission_strength=3.0),  # 1 orange layer
        pal(124, emission_strength=3.5),  # 2 yellow layer
        pal(127, emission_strength=4.5),  # 3 white-hot core
        pal(122, emission_strength=3.0),  # 4 orange streaks
        pal(126, emission_strength=4.0),  # 5 pale yellow lumps
    ]
    RIM, ORANGE, YELLOW, CORE, STREAK, PALE = range(6)
    bm = bmesh.new()
    ext = extents()

    layer(bm, ext, 0.0, 23.0, 0.2, 0.0, RIM)
    layer(bm, ext, 1.0, 22.3, 0.205, 0.02, ORANGE)
    layer(bm, ext, 2.4, 21.2, 0.21, 0.045, YELLOW)
    layer(bm, ext, 5.0, 19.0, 0.21, 0.075, CORE, sides=14)

    # Lumps of white fire on the core, and streaks of yellow and orange where the sprite has them.
    for c, r, rx, ry, rz, z, m in [
        (33, 8, 7, 3.5, 0.04, 0.27, PALE), (47, 7, 6, 3.0, 0.04, 0.27, PALE),
        (29.5, 13, 3.0, 1.4, 0.03, 0.235, STREAK), (56.5, 13.5, 1.4, 3.5, 0.03, 0.22, STREAK),
        (44, 15.5, 4.0, 1.4, 0.03, 0.21, YELLOW), (36, 16.5, 3.5, 1.3, 0.03, 0.2, YELLOW),
        (22, 7, 1.4, 3.5, 0.03, 0.22, YELLOW), (60.5, 4, 1.4, 3.0, 0.03, 0.235, YELLOW),
    ]:
        lib.ellipsoid(bm, (X(c), Y(r), z), (rx * lib.PX, ry * lib.PX, rz), mat=m, segments=10, rings=5)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, [n for n, _ in PIECES])
    obj = build(sprite)
    # Piece centres in px from the assembly centre (split_assembly: X = cx / 12, Y = -cy / 12).
    layout = [(name, off + 12 - W / 2, 0) for name, off in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name, _ in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, layout, 72, 84, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=6, view_px=480)
        for name, _ in PIECES:
            lib.preview([pieces[name]], ROOT, name, common.load_sprite(ROOT, name),
                        out=out.parent / f"{name}.png")


if __name__ == "__main__":
    main()
