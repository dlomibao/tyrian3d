"""Red spore (newsh5.shp frames 19 and 38): a 3D version of its sprite.

Seen in episode 4 (levels 4.22 and 4.25). A small dark red blob, about 10 px across, a little
lumpy: a lighter swelling on its upper left (where the sprite catches an orange-yellow glint) and
a smaller one on its right. The two frames are the same blob turning slightly, so one model
covers both, with a blob per frame (common.frame_part): on frame 38 it is narrower and a pixel
lower, with a dimmer glint.

Run: blender --background --python assets/blender/enemies/newsh5-19.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402
from lib_b030 import PX  # noqa: E402

NAME = "newsh5-19"


def px(c):
    return lib.px(c, w=12)


def row(r):
    return lib.row(r, h=14)


def blob(bm, glint_at, squeeze=1.0, drop=0.0, glint_h=1.0):
    """The blob: a body with two lighter swellings and a darker lump under it, squeezed across
    by `squeeze` about its centre column and moved down `drop` px, and the glint (centre in
    sprite px, `glint_h` px tall) placed after that."""
    BODY, LIGHT, GLINT, DARK = range(4)
    lib.ellipsoid(bm, px(5.0), row(5.6), 0.0, 4.6 * PX, 5.1 * PX, 3.4 * PX, mat=BODY, segments=16, rings=10)
    lib.ellipsoid(bm, px(3.5), row(4.4), 0.4 * PX, 3.0 * PX, 3.2 * PX, 3.0 * PX, mat=LIGHT, segments=12, rings=7,
                  rot=0.5)
    lib.ellipsoid(bm, px(7.4), row(4.8), 0.0, 2.6 * PX, 2.6 * PX, 2.6 * PX, mat=LIGHT, segments=12, rings=7)
    lib.ellipsoid(bm, px(4.4), row(8.4), -0.2 * PX, 2.8 * PX, 1.9 * PX, 2.6 * PX, mat=DARK, segments=12, rings=7)
    for v in bm.verts:
        v.co.x = px(5.0) + (v.co.x - px(5.0)) * squeeze
        v.co.y -= drop * PX
    lib.ellipsoid(bm, px(glint_at[0]), row(glint_at[1]), 2.9 * PX, 1.2 * PX * squeeze, glint_h * PX, 0.7 * PX,
                  mat=GLINT, segments=8, rings=4)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(116, metallic=0.15, roughness=0.35),  # 0 body
        pal(118, metallic=0.2, roughness=0.25),  # 1 lighter swellings
        common.palette_material(sprite, 121, f"{NAME}-glint", metallic=0.1, roughness=0.2, emission_strength=1.5,
                                frames={38: 120}),  # 2 glint, dimmer on frame 38
        pal(113, metallic=0.1, roughness=0.5),  # 3 dark underside lump
    ]
    bm = bmesh.new()
    blob(bm, (3.3, 3.4))
    first = common.frame_part(lib.to_object(NAME, bm, mats, coll), [19])
    # Frame 38: the blob turned a little, narrower (columns 1-9 instead of 0-10) and a pixel
    # lower (rows 1-11), its glint a little lower too (rows 3-4).
    bm = bmesh.new()
    blob(bm, (3.4, 3.9), squeeze=0.85, drop=1.0, glint_h=1.5)
    second = common.frame_part(lib.to_object(f"{NAME}-turn-38", bm, mats, coll), [38])
    return [first, second]


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, build(sprite), sprite["sprites"])], __file__)
