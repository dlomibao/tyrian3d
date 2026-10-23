"""Big blue spiral shell (newshn.shp frame 13), the largest of three: a 3D version of its sprite.

Seen in level 2.4, lying on the ground: a round blue shell with its spire raised on the upper
left, a dark groove spiralling round the spire from the top edge down to the bottom, and the
light outer whorl curving round the right and the bottom. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshn-13.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b071 as lib  # noqa: E402

NAME = "newshn-13"


def build(sprite):
    return lib.shell(
        NAME, sprite, centre=(11.0, 13.3), radii=(8.6, 9.2), height=0.46,
        knob=(9.0, 9.4, 3.7, 0.13),
        groove=[(15.2, 5.4), (13.4, 7.4), (13.8, 9.5), (13.9, 11.6), (13.1, 13.1), (11.6, 14.3),
                (10.0, 15.0), (8.7, 15.1)],
        ridge=[(16.8, 11.2), (16.9, 13.6), (16.3, 15.5), (14.8, 17.2), (12.0, 18.3), (9.2, 18.6),
               (6.8, 18.1)],
        idx=(54, 58, 49, 57, 51))


if __name__ == "__main__":
    lib.shell_main(NAME, build)
