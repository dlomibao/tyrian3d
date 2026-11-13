"""Twin cannon pair, left half (newshv.shp 14 + 16): a 3D version of its sprites.

Seen in episode 4: UNDERDELI (4.7) flies a pair on the sky layer at the screen edges; in DREAD-NOT
(4.14) they are the dreadnought's side cannons. Each script builds the whole pair (the right cannon
is the mirror of the left) with lib_cannon_pair14 and exports only its own two pieces, so the halves
meet at the seam. See lib_cannon_pair14.py for the design (hard-surface barrel, wing mount,
bulkhead, turntable and ball-joint coupling; outline shell from the closed pair).

Run: blender --background --python assets/blender/enemies/assembly-newshv-14.py [-- --measure DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_cannon_pair14 as lib  # noqa: E402

if __name__ == "__main__":
    lib.main(["newshv-14", "newshv-16"], "assembly-newshv-14")
