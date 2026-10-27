"""Red faceted disc (newshv.shp frames 123, 125, 127): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A round, domed disc with a stepped diamond on top: a bright outer
diamond ridge, a dark groove, and a bright pyramid in the middle. The three frames only dim the
whole disc (a pulse), so one model covers them, its colours stepping darker frame by frame. newshv-153 is the same disc in blue; this one uses the reds 64-79.

Run: blender --background --python assets/blender/enemies/newshv-123.py [-- --preview out.png] [--frame-previews frames.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-123"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = lib.gem_disc(sprite, NAME, 16)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)
    if "--frame-previews" in sys.argv:
        common.render_frame_previews(objects, sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
