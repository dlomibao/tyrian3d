"""Pale crystal shard (newshv.shp frame 10): a 3D version of its sprite.

Seen in episode 2 (level 2.12). A long faceted crystal pointing up the screen: a ridge down
its middle (lit on the left, in shadow on the right), a dark groove near the bottom and a
rounded base cap below it. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshv-10.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b043 as lib  # noqa: E402

NAME = "newshv-10"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(91, metallic=0.25, roughness=0.3),  # 0 crystal body
        pal(88, metallic=0.2, roughness=0.5),  # 1 groove
        pal(92, metallic=0.25, roughness=0.3),  # 2 base cap
    ]
    bm = bmesh.new()
    lib.crystal(bm, lib.Grid(), (0, 1, 2))
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    lib.silhouette_report(obj, sprite["frames"][0]["pixels"], lib.Grid(), outline=(80,))
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
