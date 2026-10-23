"""Blue spiral shell (newshn.shp frame 15), a size up from newshn-125: a 3D version of its sprite.

Seen in level 2.4, lying on the ground: a round blue shell with its spire raised on the upper
left, a dark groove spiralling round the spire from the top edge down to the bottom, and the
light outer whorl curving round the right and the bottom. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshn-15.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b071 as lib  # noqa: E402

NAME = "newshn-15"


def build(sprite):
    return lib.shell(
        NAME, sprite, centre=(11.0, 13.5), radii=(7.6, 8.1), height=0.42,
        knob=(9.2, 10.4, 3.6, 0.12),
        groove=[(14.8, 6.4), (13.6, 8.2), (13.6, 10.0), (14.0, 12.0), (13.4, 13.3), (12.0, 14.3),
                (10.4, 15.1), (9.0, 15.3)],
        ridge=[(16.6, 11.0), (16.8, 13.2), (16.3, 15.2), (15.0, 16.9), (13.0, 18.0), (10.2, 18.5),
               (7.6, 18.2)],
        idx=(55, 59, 50, 58, 52))


if __name__ == "__main__":
    lib.shell_main(NAME, build)
