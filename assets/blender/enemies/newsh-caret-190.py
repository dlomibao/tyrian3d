"""Grey dart lying sideways, nose to the right (newsh^.shp frame 190): a 3D version of its sprite.

Seen in episode 4 (levels 4.4, 4.14). The mirror of newsh-caret-152 (and the dart of newsh-caret-171
turned a quarter turn anticlockwise): a rod with swept fins and a glowing red nose band. It shares
the builder in newsh-caret-152.py and exports only its own model.

Run: blender --background --python assets/blender/enemies/newsh-caret-190.py [-- --no-bake]
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsh_caret_152", Path(__file__).resolve().with_name("newsh-caret-152.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.build_model("newsh-caret-190")
