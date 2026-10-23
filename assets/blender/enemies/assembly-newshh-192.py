"""Narrow green beetle (newshh.shp frames 192 and 194, two pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.2). Two 2x2 enemies side by side make one 48 x 28 px beetle
(sprite.json `assemblyLayout`): a green body with a pointed, ridged head up the screen and a broad
tail with two lobes, under two grey shell plates that sweep from its shoulders down its sides and
meet in a band across its middle. The wide beetle (assembly-newshh-230) is the same with its
shells spread apart.

Built whole in assembly coordinates (lib_b056.build_beetle), then cut into the two pieces.

Run: blender --background --python assets/blender/enemies/assembly-newshh-192.py [-- --preview out.png]
(the preview is the whole beetle; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b056 as lib  # noqa: E402

NAME = "assembly-newshh-192"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-192", "newshh-194"]
CX0, CY0 = 234, -1  # screen position of the beetle's 48 x 28 px block centre (the Blender origin)
HEAD = [(2.0, 1.5), (3.0, 3.5), (4.0, 4.5), (5.0, 5.5), (6.0, 6.5), (7.0, 7.5), (8.0, 8.5), (9.0, 9.5)]


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = lib.build_beetle(sprite, NAME, 0, HEAD)
    lib.export_assembly(ROOT, obj, PIECES, CX0, CY0, sprite["assemblyLayout"], 4)


if __name__ == "__main__":
    main()
