"""Grey gun emplacement (newsh^.shp frame 45) of UNDERDELI's brick wall: a 3D version of its sprite.

One object with the red and grey crab (assembly-newsh-caret-45): the shared builder lives in
assembly-newsh-caret-45.py. This script exports only its own model. Run:
tools/build-models.sh -j 2 assets/blender/enemies/newsh-caret-45.py
"""

import importlib.util
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("assembly_newsh_caret_45", _here / "assembly-newsh-caret-45.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["assembly_newsh_caret_45"] = _mod
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _crab, _cs, _emp, _es, _p, _s = _mod.build_all()
    _mod.export_emplacement(_emp, _es)
