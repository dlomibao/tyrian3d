"""Green energy arrow (newsh5.shp frames 114, 228, 266): a 3D version of its sprite.

Seen in episode 4 (levels 4.18 and 4.20). A glowing green arrow flying right: a round shaft with a
white-hot core and a pointed four-faced head. The three frames only fade it (the same pixels in
dimmer greens), so one model covers them all.

Run: blender --background --python assets/blender/enemies/newsh5-114.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "newsh5-114"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(199, metallic=0.1, roughness=0.4, emission_strength=2.5),  # 0 green shell
        pal(207, metallic=0.1, roughness=0.3, emission_strength=3.5),  # 1 bright green head
        pal(47, roughness=0.3, emission_strength=5.0),  # 2 white-hot core
    ]
    SHELL, BRIGHT, CORE = range(3)
    g = lib.Grid(12, 14)
    yc = g.y(6)
    bm = bmesh.new()

    # Shaft (rows 5-7, columns 0-7), a rounded tail end, into the back of the head.
    x0, x1 = g.x(-0.5), g.x(7.5)
    lib.loft_x(bm, [(x0, 0.9 * U, 0.8 * U, 0.0), (x0 + 0.4 * U, 1.5 * U, 1.2 * U, 0.0),
                    (x1, 1.5 * U, 1.2 * U, 0.0)], y=yc, sides=10, mat_index=SHELL)
    # White core along row 6 (columns 1-9), bulging out of the shaft's top.
    lib.loft_x(bm, [(g.x(0.6), 0.0, 0.0, 0.0), (g.x(1.5), 0.7 * U, 0.55 * U, 0.0),
                    (g.x(8.5), 0.7 * U, 0.55 * U, 0.0), (g.x(9.6), 0.0, 0.0, 0.0)],
               y=yc, z=0.85 * U, sides=8, mat_index=CORE)

    lib.set_smooth(bm, 0)

    # Head: a four-faced point from its back (column 7, rows 3-9) to the tip (column 11).
    def head(xb, xt, hw, hh, z, mat):
        back = [bm.verts.new(p) for p in ((xb, yc, z + hh), (xb, yc + hw, z), (xb, yc, z - hh), (xb, yc - hw, z))]
        tip = bm.verts.new((xt, yc, z))
        bm.faces.new(list(reversed(back))).material_index = mat
        for i in range(4):
            bm.faces.new((back[i], back[(i + 1) % 4], tip)).material_index = mat

    head(g.x(6.6), g.x(11.5), 3.5 * U, 2.0 * U, 0.0, SHELL)
    # Brighter inner head (columns 8-10) standing out of the shell's faces.
    head(g.x(7.6), g.x(10.6), 2.3 * U, 1.75 * U, 0.25 * U, BRIGHT)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
