"""Grey dart lying sideways, nose to the right (newsh^.shp frame 190): a 3D version of its sprite.

Seen in episode 4 (levels 4.4, 4.14). The grey dart of newsh-caret-171 lying on its side across the
screen, nose (with the glowing red band) to the right: a rod with two sets of swept fins, wide at the
back. One frame.

Run: blender --background --python assets/blender/enemies/newsh-caret-190.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b072 import dart  # noqa: E402

NAME = "newsh-caret-190"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
MAPPING = lambda c, r: (r, 10 - c)  # the dart of newsh-caret-171 turned a quarter turn anticlockwise: its row r becomes column r


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = dart(sprite, NAME, common.reset_collection(NAME), NAME, MAPPING)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
