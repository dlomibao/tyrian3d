"""the plain rock wall stretch (newsh3 166/168/170 over 204/206/208, 72x40 px) of SURFACE's sandy rock wall.

One object with the rock arch (assembly-newsh3-198) and the other wall stretches: the shared
builder lives in assembly-newsh3-198.py (rock from lib_b017, D175 facet ramp, outline shell D189).
This script exports only its own models. Run:
tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh3-166.py
"""

import importlib.util
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("assembly_newsh3_198", _here / "assembly-newsh3-198.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["assembly_newsh3_198"] = _mod
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    _mod.build_and_export(["wall"], argv)
