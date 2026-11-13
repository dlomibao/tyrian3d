"""Wall of fire (CORE, newsh3 pieces): a 3D version of its sprites.

The whole fire (14 pieces, four assemblies) is built in lib_b050; this script exports only the
pieces of assembly-newsh3-118.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-118.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_b050  # noqa: E402

if __name__ == "__main__":
    lib_b050.build_assembly("assembly-newsh3-118")
