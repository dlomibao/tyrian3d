"""Grey and red fortress, upper right flank (newsh9.shp frame 32): a 3D version of its sprite.

Seen in episode 4 (levels 4.4 and 4.18). It sits 14 px above newsh9-51 (whose top half it
repeats pixel for pixel), between the fortress's lower part (assembly-newsh9-85) and its big grey
dome (newsh9-10 and newsh9-12): the dome's right flank and the red fender curling under it.

The whole fortress is built once in lib_b085.py and this piece is cut out of it with
common.split_assembly, so it lines up with its neighbours.

Run: blender --background --python assets/blender/enemies/newsh9-32.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b085 as lib  # noqa: E402


def main():
    preview = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_pieces(["newsh9-32"], preview)


if __name__ == "__main__":
    main()
