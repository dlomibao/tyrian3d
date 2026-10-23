"""Horned eye creature (newshn.shp, assembly of newshn-163 over newshn-201): 3D versions of its
sprites.

Seen in level 2.4, on the ground. Two 2x2 pieces, one above the other, make one 24 x 33 px
creature: a grey horn-shaped hood (light crest down its left) on top of a lower body that tapers
down to a point, a dark blue shoulder socket on its right, and an arm holding a round grey eye
with a glowing cyan lens, from which a hooked tentacle hangs down to the ground.

Its three frames swing the eye out and up (163 + 201: eye against the body; 203 + 205: half
raised; 207 + 245: swung out), so each pose is built whole, cut into its two pieces with
common.split_assembly, and exported as newshn-163 / -f2 / -f3 and newshn-201 / -f2 / -f3, each
with its own frame.

Run: blender --background --python assets/blender/enemies/assembly-newshn-201.py [-- --preview out.png]
(the preview is the whole creature in pose A, <out>-B.png and <out>-C.png the other poses; each
piece model also gets <model>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b071 as lib  # noqa: E402

NAME = "assembly-newshn-201"
# (piece, its top row in the assembly, {pose: (model, frame)}); newshn-201 sits 28 px below.
PIECES = [
    ("newshn-163", 0, {"A": ("newshn-163", 163), "B": ("newshn-163-f2", 203), "C": ("newshn-163-f3", 207)}),
    ("newshn-201", 28, {"A": ("newshn-201", 201), "B": ("newshn-201-f2", 205), "C": ("newshn-201-f3", 245)}),
]

if __name__ == "__main__":
    lib.creature_assembly(__file__, NAME, PIECES, mirror=False)
