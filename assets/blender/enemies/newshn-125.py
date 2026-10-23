"""Small blue spiral shell (newshn.shp frame 125): a 3D version of its sprite.

Seen in level 2.4, lying on the ground: a round blue shell with its spire raised on the upper
left, a dark groove spiralling round the spire from the top edge down to the bottom, and the
light outer whorl curving round the right and the bottom. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshn-125.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b071 as lib  # noqa: E402

NAME = "newshn-125"


def build(sprite):
    return lib.shell(
        NAME, sprite, centre=(11.0, 13.6), radii=(6.6, 7.1), height=0.38,
        knob=(9.5, 10.9, 3.5, 0.11),
        groove=[(13.6, 7.0), (13.1, 8.6), (13.0, 10.2), (13.0, 12.0), (12.5, 13.6), (11.4, 14.7),
                (10.2, 15.3), (9.2, 15.4)],
        ridge=[(15.6, 10.8), (16.0, 12.6), (15.5, 14.4), (14.3, 16.1), (12.6, 17.4), (10.5, 18.1),
               (8.2, 18.2)],
        idx=(57, 60, 51, 59, 54))


if __name__ == "__main__":
    lib.shell_main(NAME, build)
