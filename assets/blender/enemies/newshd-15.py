"""Rock sliver, lower-left corner (newshd.shp frame 15, a 1x1 edge piece of the drifting rock heap
assembly-newshd-89).

It is built and exported by assets/blender/enemies/newshd-31.py together with newshd-31 (the two
are the heap's edge fillers and share one rock), which writes enemies/newshd-15 and its
src/render/spriteModels entry. This script runs that one, so building either gives both;
tools/build-models.sh with both listed builds twice, so list only one of them.

Run: blender --background --python assets/blender/enemies/newshd-15.py
"""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "newshd-31.py"), run_name="__main__")
