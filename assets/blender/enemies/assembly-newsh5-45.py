"""Gun pod pointing right (newsh5.shp frames 43 and 45, assembly of 2 pieces): a 3D version of
its sprites.

Seen in episode 4 (level 4.12). Two 2x2 enemies side by side make one 48x28 px gun pod: a blue
capsule clamped to a grey ring frame (newsh5-43) that holds a dark blue orb, and from the ring a
light barrel sleeve, a grey band and a bullet-shaped blue head with the gun barrel out of its nose
(newsh5-45). Built whole by lib_b042.build_gunpod (newsh5-39 + 41 is its mirror image) and cut
into the two pieces with common.split_assembly. One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-45.py [-- --preview out.png]
(the preview is the whole pod; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b042 as lib  # noqa: E402

NAME = "assembly-newsh5-45"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-43", "newsh5-45"]


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = lib.build_gunpod(sprite, NAME)
    # Screen centres from sprite.json; the assembly's centre (screen 128, 117) is the origin.
    centre = {e["model"]: (e["cx"], e["cy"]) for e in sprite["assemblyLayout"]}
    cx0 = (centre["newsh5-43"][0] + centre["newsh5-45"][0]) / 2
    cy0 = centre["newsh5-43"][1]
    layout = [(n, centre[n][0] - cx0, centre[n][1] - cy0) for n in PIECES]
    lib.export_assembly(ROOT, obj, layout, size=4)


if __name__ == "__main__":
    main()
