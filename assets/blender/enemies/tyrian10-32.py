"""Glowing green gem (tyrian.shp#10 frames 32-36): a 3D version of its sprite.

A bonus gem seen in episodes 1 to 4: a diamond-shaped cut stone, dark green at the edges
and pale at the centre, with a ring of bright facets. The five frames only brighten it (the
palette indices step up by one each frame), so one model covers them all, its colours
stepping up a shade per frame (palette_material frames=); the crown glows.

Run: blender --background --python assets/blender/enemies/tyrian10-32.py [-- --preview out.png] [--frame-previews frames.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b021 as lib  # noqa: E402

NAME = "tyrian10-32"


def build(sprite):
    models = lib.gem_model(sprite, NAME, body=35, crown=37, ridge=40, inner=42, core=45, glow=2.0, core_glow=4.0,
                           brighten=True)
    if "--frame-previews" in sys.argv:
        _, objects, _ = models[0]
        common.render_frame_previews(objects, sys.argv[sys.argv.index("--frame-previews") + 1], sprite,
                                     common.repo_root(__file__))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
