"""Pop-up ball turret (newshc.shp frames 77-89): a 3D version of its sprites.

Seen in episode 1 (level 1.19) and 3 (3.23), on top of the two grey pillars of the machine
assembly-newshc-283 builds. A grey ball with a red stripe over it and an eye on top sits in a
red hood. Over its seven frames it sinks from fully raised (its grey stem showing below the hood)
down into the pillar, its eye glows red, and the hood opens out sideways with a widening slot at
its front. Every frame is a different shape, so each gets its own model: newshc-77 (frame 77),
newshc-77-f2 (79) ... newshc-77-f7 (89), built by lib_b110.build_head.

Run: blender --background --python assets/blender/enemies/newshc-77.py [-- --preview out.png]
(the preview shows frame 77; the other frames get <name>-f2.png ... next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b110 as lib  # noqa: E402

NAME = "newshc-77"
ROOT = common.repo_root(__file__)


def model_name(i):
    return NAME if i == 0 else f"{NAME}-f{i + 1}"


def build(sprite, frame, name):
    coll = common.reset_collection(name)
    p = lib.HEAD_FRAMES[frame]
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = lib.head_materials(pal, p["eye"])
    bm = bmesh.new()
    lib.build_head(bm, lib.Frame(), 0, 0, frame)
    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    sheet = sprite["sprites"][0]
    preview = lib.preview_arg()
    for i, frame in enumerate(sprite["frames"]):
        name = model_name(i)
        obj = build(sprite, frame["index"], name)
        subset = [{**sheet, "frames": [frame["index"]]}]
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", subset)
        if preview:
            out = Path(preview) if i == 0 else Path(preview).parent / f"{name}.png"
            common.render_preview([obj], str(out), lib.sprite_png(ROOT, NAME, sprite, i), size=2)


if __name__ == "__main__":
    main()
