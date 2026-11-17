"""Rock-heap edge piece (newshd.shp frame 31, one 12 x 14 tile): the lower-right quarter of the
heap's missing top-left piece.

It is a stone or two of the drifting rock heap assembly-newshd-89 and spawns with it, so
assets/blender/enemies/assembly-newshd-89.py builds the heap whole from all ten sprites and cuts
this model out of it (D239), writing enemies/newshd-31 and its src/render/spriteModels entry. This
script runs that one; with tools/build-models.sh list the assembly's script only (each of these
rebuilds the whole heap).

Run: blender --background --factory-startup --python assets/blender/enemies/newshd-31.py
"""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "assembly-newshd-89.py"), run_name="__main__")
