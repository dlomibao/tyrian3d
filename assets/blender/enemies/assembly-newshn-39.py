"""GYGES's right arm claw (newshn.shp, assembly of newshn-1 over newshn-39): 3D versions of its
sprites.

WHAT IT IS: the claw at the tip of GYGES's (level 2.2) right swinging tentacle arm, the mirror image
of assembly-newshn-201 (its sprites are that claw's flipped left to right, column c there being
22 - c here, exactly, on all three poses). A grey-blue hooked pincer that hangs and swings in the air
while the scroll is stopped for the boss ('ground' is only its draw layer): free-floating, with a
round closed underside. See assembly-newshn-201.py for the parts; this script builds it with that
builder, mirrored.

Its three frames open the claw: 11 + 49 closed, 9 + 47 half open, 1 + 39 open. Each pose is built
whole, cut into its two pieces with common.split_assembly and exported with its own frame:
newshn-1 / -f2 / -f3 and newshn-39 / -f2 / -f3 cover frames 1 / 9 / 11 and 39 / 47 / 49.

    blender --background --factory-startup --python assets/blender/enemies/assembly-newshn-39.py \
        [-- --measure out_dir]
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("claw_left", Path(__file__).resolve().parent / "assembly-newshn-201.py")
claw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(claw)

NAME = "assembly-newshn-39"
# (piece, its top row in the assembly, {pose: (model, frame)}); newshn-39 sits 28 px below.
PIECES = [
    ("newshn-1", 0, {"A": ("newshn-1-f3", 11), "B": ("newshn-1-f2", 9), "C": ("newshn-1", 1)}),
    ("newshn-39", 28, {"A": ("newshn-39-f3", 49), "B": ("newshn-39-f2", 47), "C": ("newshn-39", 39)}),
]

if __name__ == "__main__":
    claw.build_assembly(__file__, NAME, PIECES, mirror=True)
