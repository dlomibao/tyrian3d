"""Red canister on a pole (newsh5.shp frame 168): the canister link of the grey twin-walker gate unit.

Seen in episode 4 (level 22), where nine of them hang one under the other on a long blue-grey pole,
so the pole runs through the 24x28 block and lines up with the link above and below. The model is
built by the shared builder in assembly-newsh5-85.py (one read of the sprites, one set of
materials); this script exports only newsh5-168 (the gate pieces are exported by that script).

Run: blender --background --python assets/blender/enemies/newsh5-168.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("assembly_newsh5_85", Path(__file__).resolve().parent / "assembly-newsh5-85.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.build_and_export("pole")
