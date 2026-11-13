"""assembly-newsh-caret-203: UNDERDELI's torpedo B (newsh^.shp frames 203, 204, 206), the mirror of
torpedo A with its nose to the right. The geometry lives in assembly-newsh-caret-198.py (one builder
for both torpedoes); this script loads it and exports only torpedo B's three models.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh-caret-203.py
"""

import importlib.util
from pathlib import Path

_src = Path(__file__).resolve().parent / "assembly-newsh-caret-198.py"
_spec = importlib.util.spec_from_file_location("assembly_newsh_caret_198", _src)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.export_variant("B")
