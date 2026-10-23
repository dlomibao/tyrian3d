"""Wide green beetle (newshh.shp frames 230 and 232, two pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.2). Two 2x2 enemies side by side make one 48 x 28 px beetle
(sprite.json `assemblyLayout`): a green body with a pointed, ridged head up the screen and a broad
tail with two lobes, under two grey shell plates that sweep from its shoulders down its sides.
The narrow beetle (assembly-newshh-192) is the same with its shells closed into a band across
its middle; here they sit 4 px further out and the body is 4 px wider each side.

Built whole in assembly coordinates (lib_b056.build_beetle), then cut into the two pieces.

Run: blender --background --python assets/blender/enemies/assembly-newshh-230.py [-- --preview out.png]
(the preview is the whole beetle; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b056 as lib  # noqa: E402

NAME = "assembly-newshh-230"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-230", "newshh-232"]
CX0, CY0 = 234, 27  # screen position of the beetle's 48 x 28 px block centre (the Blender origin)
HEAD = [(1.0, 2.5), (2.0, 5.5), (3.0, 7.5), (4.0, 8.5), (5.0, 9.5), (6.0, 10.5), (7.0, 11.5), (8.0, 12.5), (9.0, 13.5)]


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = lib.build_beetle(sprite, NAME, 4, HEAD)
    lib.export_assembly(ROOT, obj, PIECES, CX0, CY0, sprite["assemblyLayout"], 4)


if __name__ == "__main__":
    main()
