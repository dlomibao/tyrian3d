"""Gun pod pointing left (newsh5.shp frames 39 and 41, assembly of 2 pieces): a 3D version of
its sprites.

Seen in episode 4 (level 4.12). The mirror image, pixel for pixel, of the gun pod of
assembly-newsh5-45: a 48x28 px pod whose bullet-shaped blue head and barrel point left
(newsh5-39) out of a grey ring frame holding a dark blue orb, with a blue capsule clamped to its
right side (newsh5-41). Built whole by lib_b042.build_gunpod(flip=True) and cut into the two
pieces with common.split_assembly. One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-39.py [-- --preview out.png]
(the preview is the whole pod; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b042 as lib  # noqa: E402

NAME = "assembly-newsh5-39"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-39", "newsh5-41"]


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = lib.build_gunpod(sprite, NAME, flip=True)
    # Screen centres from sprite.json; the assembly's centre (screen 216, 61) is the origin.
    centre = {e["model"]: (e["cx"], e["cy"]) for e in sprite["assemblyLayout"]}
    cx0 = (centre["newsh5-39"][0] + centre["newsh5-41"][0]) / 2
    cy0 = centre["newsh5-39"][1]
    layout = [(n, centre[n][0] - cx0, centre[n][1] - cy0) for n in PIECES]
    lib.export_assembly(ROOT, obj, layout, size=4)


if __name__ == "__main__":
    main()
