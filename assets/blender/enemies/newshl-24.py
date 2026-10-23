"""Twin-plate spindle (newshl.shp 24): a 3D version of its sprite.

Seen in episode 4, level 40. A grey shaft runs across the sprite: a short nose, a wide body, two
tall oval plates (one thin, one thick) joined by a dark web with a red light above and below the
shaft, then a narrower shaft with red brackets above and below it and a flange where the sprite
is cut off. newshl 34 is exactly newshl 24 mirrored left to right, so both are built by
lib_b020.build_spindle. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshl-24.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b020 as lib  # noqa: E402

NAME = "newshl-24"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = lib.build_spindle(NAME, sprite, mirror=False)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
