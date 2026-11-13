"""TORM insect craft abdomen segment (newshh.shp frames 230+232): a 3D version of its sprites.

Seen in episode 2 (level 2.2): a green-and-chrome abdomen segment, 46x28 px of one giant flying insect craft, in a column
with newshh-155 (tail spike) above, and the D170 head (assembly-newshh-159/197) below. A free-flying
armoured plate: green carapace on top, satin-chrome side shells, a round closed belly. Built per
segment by lib_torm_abdomen (design B), cut into its two pieces, one frame each.

Run: blender --background --python assets/blender/enemies/assembly-newshh-230.py [-- --review outdir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_torm_abdomen as lib  # noqa: E402

if __name__ == "__main__":
    lib.run("230")
