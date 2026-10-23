"""Right grey gun works, upper piece and barrel below (newsh9.shp frames 238 and 276): a 3D version
of their sprites.

Seen in episode 4 (level 4.18). The two pieces stand one above the other (sprite.json
`assemblyLayout`) and are windows onto one drawing, the mirror image of the left gun works
(assembly-newsh9-274): a sloped dark housing with a thick barrel pointing left, the round column
under it, and a barrel pointing straight down the screen from the junction below. The whole gun
works is built in lib_b089 and each window cut out of it (newsh9-239 and newsh9-258 are other
windows onto it).

Run: blender --background --python assets/blender/enemies/assembly-newsh9-276.py [-- --preview out.png]
(the preview is the whole gun works; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b089  # noqa: E402

if __name__ == "__main__":
    lib_b089.run("right", ["newsh9-238", "newsh9-276"], "assembly-newsh9-276")
