"""Grey and red corner block (newshu.shp frame 19, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 1 (level section 19) and episode 3 (level section 23). A ground piece filling the
lower right of its tile: a grey housing whose rounded top catches the light along its front edge,
a red band below it with a bright spot on the left and shadow on the right, and a pipe along the
bottom, red where it pokes out to the left and grey, brightening to a pale end, under the housing. One frame, so one model.

Run: blender --background --python assets/blender/enemies/newshu-19.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b136 as lib  # noqa: E402
from lib_b136 import common  # noqa: E402

NAME = "newshu-19"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.5, roughness=0.4),  # 0 grey housing
        pal(13, metallic=0.55, roughness=0.25),  # 1 bright rounded front edge
        pal(72, metallic=0.35, roughness=0.45),  # 2 red band
        pal(75, metallic=0.3, roughness=0.35),  # 3 bright red spot
        pal(5, metallic=0.4, roughness=0.55),  # 4 shadowed right of the band
        pal(8, metallic=0.45, roughness=0.45),  # 5 grey pipe
        pal(12, metallic=0.5, roughness=0.25),  # 6 pipe's pale end
        pal(73, metallic=0.35, roughness=0.45),  # 7 red pipe stub
        pal(3, metallic=0.3, roughness=0.6),  # 8 dark base plate
    ]
    HOUSING, EDGE, BAND, SPOT, SHADE, STEP, PALE, PIPE, BASE = range(9)
    bm = bmesh.new()

    # Base plate under the whole footprint (columns 7-11, rows 6-13).
    lib.block(bm, [(7.5, 6.5), (12.0, 6.5), (12.0, 12.2), (7.5, 12.2)], 0.0, 0.05, BASE)

    # Grey housing (columns 8-11, rows 7-9): rounded top falling toward its lit front edge.
    lib.prism_x(bm, [(6.6, 0.0), (6.6, 0.22), (7.2, 0.27), (8.0, 0.285), (8.8, 0.27), (9.6, 0.0)],
                7.8, 12.0, HOUSING)
    # The bright rounded front edge (row 9, columns 8-10).
    lib.prism_x(bm, [(8.8, 0.0), (8.8, 0.26), (9.3, 0.25), (9.9, 0.2), (10.2, 0.13), (10.2, 0.0)],
                7.8, 11.0, EDGE)
    lib.prism_x(bm, [(8.8, 0.0), (8.8, 0.25), (9.3, 0.24), (9.9, 0.19), (10.2, 0.12), (10.2, 0.0)],
                11.0, 12.0, SHADE)

    # Red band (rows 10-11) under the housing's front, a bright spot on its left, shadow at the right.
    lib.prism_x(bm, [(10.0, 0.0), (10.0, 0.16), (11.0, 0.15), (12.0, 0.12), (12.0, 0.0)], 7.8, 11.0, BAND)
    lib.prism_x(bm, [(10.0, 0.0), (10.0, 0.155), (11.0, 0.145), (12.0, 0.115), (12.0, 0.0)], 11.0, 12.0, SHADE)
    lib.block(bm, [(8.9, 10.8), (10.0, 10.8), (10.0, 11.8), (8.9, 11.8)], 0.1, 0.162, SPOT)
    lib.block(bm, [(10.0, 11.0), (11.0, 11.0), (11.0, 12.0), (10.0, 12.0)], 0.1, 0.152, SHADE)
    housing = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # A pipe along the bottom (rows 12-13), red where it pokes out to the left (columns 5-6) and
    # grey, brightening to a pale end, where it runs under the housing and off the tile's right.
    bm = bmesh.new()
    for x0, x1, mat in ((4.6, 7.6, PIPE), (7.6, 10.2, STEP), (10.2, 12.0, PALE)):
        a = len(bm.verts)
        common.loft(bm, [(0.0, 0.085, 0.085, 0.085), ((x1 - x0) / 12, 0.085, 0.085, 0.085)], sides=10, mat_index=mat)
        bm.verts.ensure_lookup_table()
        for v in bm.verts[a:]:
            x, y = v.co.x, v.co.y
            v.co.x = lib.ex(x0) + y
            v.co.y = lib.ey(13.0) + x
    pipe = common.mesh_object(NAME + "-pipe", bm, mats, coll, smooth=True)
    return [housing, pipe]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = build(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
