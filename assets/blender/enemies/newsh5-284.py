"""Flying ear, lobe at the bottom right (newsh5.shp frame 284): a 3D version of its sprite.

Seen in episode 4 (level 20), beside its mirror image newsh5-245. A flat tan ear: a rolled rim all
round, a dark hollow inside it, the Y-shaped antihelix ridge, the tragus bumps and a fleshy lobe.
The shared builder is lib_b004.ear. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-284.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-284"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
MIRROR = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(25, metallic=0.0, roughness=0.6),  # 0 skin
        pal(27, metallic=0.0, roughness=0.55),  # 1 rim
        pal(23, metallic=0.0, roughness=0.7),  # 2 hollow
        pal(20, metallic=0.0, roughness=0.8),  # 3 dark concha and fossa
        pal(27, metallic=0.0, roughness=0.55),  # 4 antihelix ridge
        pal(29, metallic=0.0, roughness=0.45),  # 5 highlights: tragus, antitragus, rim
    ]
    bm = bmesh.new()
    lib.ear(bm, MIRROR, (0, 1, 2, 3, 4, 5))
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
