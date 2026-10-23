"""Grey and red fortress, lower part (newsh9.shp, assembly of 6 pieces): a 3D version of its sprites.

Seen in episode 4 (levels 4.4 and 4.18). Six 2x2 ground enemies side by side (newsh9-47, -49 and
-51 over newsh9-85, -87 and -89, sprite.json `assemblyLayout`) make the lower 72 x 56 px of a
big symmetric structure: red fenders under a grey dome, a dark machinery bay with two red lenses,
a grey ball on a neck in the middle, and below them a grey shell with a raised lip, four red pods
in dark sockets, a spine down the middle and two tusks at the bottom.

The whole fortress (with newsh9-28 and newsh9-32 above, see lib_b085.py) is built once and cut
into the pieces with common.split_assembly, so all of them line up.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-85.py [-- --preview out.png]
(the preview is the whole fortress; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b085 as lib  # noqa: E402  (puts assets/blender on the path for common)
import common  # noqa: E402


def main():
    preview = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    obj, pieces = lib.export_pieces(lib.ASSEMBLY, preview)
    if preview:
        ref = lib.composite_png(Path(tempfile.mkdtemp()) / "fortress.png")
        common.render_preview([obj], preview, ref, size=6, view_px=640)


if __name__ == "__main__":
    main()
