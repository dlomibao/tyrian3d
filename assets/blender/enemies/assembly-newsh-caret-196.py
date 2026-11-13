"""The EYESPY (4.20) giant red lips, newsh^ 196 + 208 (48 x 28 px).

Built by lib_b046 (shared builder: faired flesh height fields over the sprite's inner mask, opaque
glossy organic materials, outline shell from a sealed copy). Exports only its own models.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-196.py [-- --review DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b046 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run("lips")
