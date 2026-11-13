"""Flying ear, lobe at the bottom left (newsh5.shp frame 245): the exact mirror image of newsh5-284
(the two sprites are pixel-for-pixel mirrors), built by the same builder, newsh5-284.py.

Seen in episode 4 (level 20), beside newsh5-284. See that script for the model.
Exports only newsh5-245.

Run: blender --background --python assets/blender/enemies/newsh5-245.py
"""

import importlib
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402

builder = importlib.import_module("newsh5-284")
ROOT = common.repo_root(__file__)


def main():
    objs = builder.build_model("newsh5-245", True)
    common.export_sprite_model(ROOT, objs, "enemies/newsh5-245", common.load_sprite(ROOT, "newsh5-245")["sprites"])


if __name__ == "__main__":
    main()
