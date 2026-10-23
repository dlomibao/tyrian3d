"""Horned eye creature, facing the other way (newshn.shp, assembly of newshn-1 over newshn-39):
3D versions of its sprites.

Seen in level 2.4, on the ground. The mirror image of assembly-newshn-201 (its sprites are that
creature's flipped left to right, column c there being 22 - c here): a grey horn-shaped hood on
top of a lower body that tapers down to a point, a dark blue shoulder socket on its left, and an
arm holding a round grey eye with a glowing cyan lens, from which a hooked tentacle hangs down.

Its three frames swing the eye out and up (11 + 49: eye against the body; 9 + 47: half raised;
1 + 39: swung out), so each pose is built whole (lib_b071.creature, mirrored), cut into its two
pieces with common.split_assembly and exported with its own frame: newshn-1 / -f2 / -f3 and
newshn-39 / -f2 / -f3 cover frames 1 / 9 / 11 and 39 / 47 / 49.

Run: blender --background --python assets/blender/enemies/assembly-newshn-39.py [-- --preview out.png]
(the preview is the whole creature in pose A, <out>-B.png and <out>-C.png the other poses; each
piece model also gets <model>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b071 as lib  # noqa: E402

NAME = "assembly-newshn-39"
# (piece, its top row in the assembly, {pose: (model, frame)}); newshn-39 sits 28 px below.
PIECES = [
    ("newshn-1", 0, {"A": ("newshn-1-f3", 11), "B": ("newshn-1-f2", 9), "C": ("newshn-1", 1)}),
    ("newshn-39", 28, {"A": ("newshn-39-f3", 49), "B": ("newshn-39-f2", 47), "C": ("newshn-39", 39)}),
]

if __name__ == "__main__":
    lib.creature_assembly(__file__, NAME, PIECES, mirror=True)
