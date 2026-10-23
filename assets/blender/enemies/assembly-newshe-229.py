"""Red pod with glowing lenses (newshe.shp, assembly of 4 pieces): a 3D version of its sprites.

A ground structure: four 2x2 enemies (newshe-191 top left, 193 top right, 229 bottom left, 231
bottom right) make one round pod about 34 x 31 px. Several pods stand in a row in game, each
made of the same four pieces (where two pods overlap, a piece of one hides a piece of the other).
The pod is a low red dome lit from the front, with a big dark glass cap set towards its back
left. On the cap sit a big white-hot lens, a smaller one below it and two dim red studs.

The pod is built once in the coordinates of its 48 x 56 px block, then cut into the four pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshe-229.py [-- --preview out.png]
(the preview is the whole pod; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b070 as lib  # noqa: E402

NAME = "assembly-newshe-229"
ROOT = common.repo_root(__file__)
# Each piece's top-left corner in the 48 x 56 px block of one pod, and its centre relative to the
# block's centre (as in sprite.json's assemblyLayout: 191 at cx 74, cy 12, 193 at 98, 12, 229 at
# 74, 40 and 231 at 98, 40, whose middle is 86, 26).
PIECES = [("newshe-191", 0, 0), ("newshe-193", 24, 0), ("newshe-229", 0, 28), ("newshe-231", 24, 28)]


def composite_pixels():
    grid = [[-1] * 48 for _ in range(56)]
    colors = {}
    for name, c0, r0 in PIECES:
        data = common.load_sprite(ROOT, name)
        colors.update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[r0 + r][c0 + c] = v
    return grid, colors


def build():
    coll = common.reset_collection(NAME)
    pixels, colors = composite_pixels()
    grid = lib.Grid(48, 56, pixels)
    X, Y = grid.x, grid.y
    mats = lib.Mats("nshe229", colors)
    SHADE = mats(113, metallic=0.3, roughness=0.5)  # shadowed back of the body
    BODY = mats(116, metallic=0.3, roughness=0.45)
    LIT = mats(118, metallic=0.3, roughness=0.4)
    HOT = mats(121, metallic=0.35, roughness=0.35)  # brightest front rim
    GLASS = mats(64, metallic=0.5, roughness=0.25)  # dark glass cap
    SOCKET = mats(115, metallic=0.4, roughness=0.3)
    STUD = mats(117, emission_strength=1.5)
    RING = mats(122, emission_strength=3.0)
    CORE = mats(127, emission_strength=5.0)
    bm = bmesh.new()

    # Body: cols 7-40, rows 12-42 (pixel centres 23.5, 27.0, radii 17 x 15.5).
    body = ((X(23.5), Y(27.0), 0.0), (17.2 / 12, 15.7 / 12, 0.42))
    first = lib.dome(bm, *body, segments=36, rings=8, mat_index=BODY, power=0.8)

    def body_slot(v):
        if v in (1, 64) or v <= 113:
            return SHADE
        if v <= 116:
            return BODY
        if v <= 119:
            return LIT
        return HOT
    lib.paint(bm, first, grid, body_slot)

    # Dark glass cap: cols 10-33, rows 14-33, tilted so its rim hugs the body.
    cap_xy, cap_r = (X(21.6), Y(23.4)), (12.4 / 12, 10.6 / 12)
    z0, shear = lib.fit_cap(body, cap_xy, cap_r, power=0.8)
    cap = ((cap_xy[0], cap_xy[1], z0), (cap_r[0], cap_r[1], 0.2))
    lib.dome(bm, *cap, segments=32, rings=6, mat_index=GLASS, shear=shear)

    def surface(x, y):
        return lib.dome_z(*cap, x, y, shear=shear) or z0

    # Big white-hot lens (cols 14-22, rows 18-26) and a smaller one (cols 24-28, rows 26-30).
    lib.lens(bm, surface, X(18.2), Y(22.0), [(5.3 / 12, 0.03, SOCKET), (4.4 / 12, 0.05, RING),
                                             (3.4 / 12, 0.07, CORE)], segments=20)
    lib.lens(bm, surface, X(25.8), Y(28.0), [(2.9 / 12, 0.025, SOCKET), (2.2 / 12, 0.04, RING),
                                             (1.3 / 12, 0.05, CORE)], segments=14)
    # Two dim red studs (cols 23-26, rows 16-17 and cols 27-30, rows 19-21).
    lib.lens(bm, surface, X(24.6), Y(16.7), [(1.9 / 12, 0.035, STUD)], segments=12)
    lib.lens(bm, surface, X(28.6), Y(20.4), [(2.1 / 12, 0.04, STUD)], segments=12)

    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    obj = build()
    layout = [(name, c0 + 12 - 24, r0 + 14 - 28) for name, c0, r0 in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, PIECES, 48, 56, Path(tempfile.mkdtemp()) / "pod.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name, _, _ in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
