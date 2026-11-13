"""Grey and red fortress, lower part (newsh9.shp, assembly of 6 pieces): a 3D version of its sprites.

Seen in episode 4: UNDERDELI (main=14), LAVA RUN (main=4) and DREAD-NOT (main=18). Six 2x2 ground
pieces side by side (newsh9-47, -49 and -51 over newsh9-85, -87 and -89, sprite.json
`assemblyLayout`) make the lower 72 x 56 px of the fortress: red fenders under a grey dome, a dark
machinery bay with two red lenses, a grey sensor ball on a neck, and below them a grey shell with a
raised lip, four red pods in dark sockets, a spine down the middle and two tusks.

The whole fortress (with newsh9-28/-32 and the dome newsh9-10/-12) is built once in lib_b085.py and
cut into pieces with common.split_assembly, so they line up; this script exports its six.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-85.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b085 as lib  # noqa: E402

PIECES = ["newsh9-47", "newsh9-49", "newsh9-51", "newsh9-85", "newsh9-87", "newsh9-89"]


def main():
    preview = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_pieces(PIECES, preview)


if __name__ == "__main__":
    main()
