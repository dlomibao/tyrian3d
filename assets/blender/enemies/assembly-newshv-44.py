"""Grey gunship facing right (newshv.shp 44 + 46): the exact mirror of assembly-newshv-85.

Runs the same builder as assembly-newshv-85.py with NSHV_MIRROR=1 (c -> 48 - c, face winding
reversed, outline shells rebuilt), exporting newshv-44 and newshv-46.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshv-44.py
"""

import importlib.util
import os
from pathlib import Path

os.environ["NSHV_MIRROR"] = "1"
_spec = importlib.util.spec_from_file_location("assembly_newshv_85", Path(__file__).resolve().parent / "assembly-newshv-85.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.main()
