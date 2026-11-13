"""assembly-newsh-caret-92: the left claw of SURFACE's mid-level guardian (Episode 4.4), pieces newsh-caret-92, -94, -129, -131, -133.
Built by lib_surface_claw.py (shared with the other claw); this script exports only its own five pieces.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh-caret-92.py
Exports public/models/enemies/newsh-caret-<n>.glb and src/render/spriteModels/newsh-caret-<n>.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_surface_claw as L  # noqa: E402

# This claw's pieces (the inventory reads the unit from these names).
PIECES = ("newsh-caret-92", "newsh-caret-94", "newsh-caret-129", "newsh-caret-131", "newsh-caret-133")
assert [p[0] for p in L.LEFT] == list(PIECES)

if __name__ == "__main__":
    L.run("left", sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
