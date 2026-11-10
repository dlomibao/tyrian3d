"""newshd-88, rebuilt from design A in lib_b138 (D123): see lib_b138.py for what it is and how it is built.

Run: blender --background --python assets/blender/enemies/newshd-88.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b138 as lib  # noqa: E402

NAME = "newshd-88"

if __name__ == "__main__":
    lib.build(NAME, __file__)
