"""Grey dart, upright (newsh^.shp frame 171 and newshd.shp frames 171, 190, 209): a 3D version of
its sprites.

Seen in episodes 3 and 4 (levels 3.15, 4.4, 4.14). A grey dart lying on the ground, nose down the
screen: a rod with two sets of swept fins (wide at the back, at the top of the sprite) and a red
band near its blunt nose. The newshd frames only cycle the band's colour (red to yellow), so one
model covers all four; the band glows. The same dart lies sideways in newsh-caret-152 and -190.

Run: blender --background --python assets/blender/enemies/newsh-caret-171.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b072 import dart  # noqa: E402

NAME = "newsh-caret-171"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
MAPPING = None  # the dart is built as this sprite shows it


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
