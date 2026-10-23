"""Rifle muzzle tip (newshc.shp frame 238): a 3D version of its sprite.

Seen in episode 1 (level 1.19) and episode 3 (level 3.23). This 1x1 enemy sits at the left end of
the big blue rifle (assembly-newshc-243): the rounded, lit end of the muzzle tube and the lower
nozzle under it, which continue newshc-239's barrel row for row. It is cut from the same whole
rifle (lib_b058.build_gun) so it lines up. A single frame.

Run: blender --background --python assets/blender/enemies/newshc-238.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b058 as lib  # noqa: E402

NAME = "newshc-238"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    gun = lib.build_gun("newshc-238-gun")
    obj = lib.cut_box(gun, NAME, *lib.MUZZLE_BOX)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
