"""Grey panelled dome (newsh9.shp frames 10 and 12, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 4 (UNDERDELI, LAVA RUN, DREAD-NOT), the top of the grey and red fortress. The two
2x2 pieces side by side (sprite.json `assemblyLayout`, 48x28 px) are the top of its big grey dome,
divided into panels by raised seams. It is part of the one fortress built in lib_b085.py and cut
into pieces with common.split_assembly; this script exports newsh9-10 and newsh9-12.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-10.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b085 as lib  # noqa: E402

PIECES = ["newsh9-10", "newsh9-12"]


def main():
    preview = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_pieces(PIECES, preview)


if __name__ == "__main__":
    main()
