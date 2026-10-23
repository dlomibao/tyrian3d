"""Green dome pad (newsha.shp frames 17, 55): a 3D version of its sprite.

Seen in episode 1 (levels 13, 23) and 3. The green twin of newsha-93: a ground tile of grey
rubble and sand with a glowing green ring lying on it and a glossy dark green dome inside. In
its second frame the ring flares wider and brighter, with white sparkles, and the dome opens into
a dark green rim round a smaller bright green dome with a white glint, a change of shape, so each
frame gets its own model: newsha-17 (frame 17) and newsha-17-f2 (frame 55). The geometry is
lib_b087.build_pad.

Run: blender --background --python assets/blender/enemies/newsha-17.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b087 as lib  # noqa: E402

NAME = "newsha-17"
CFG = dict(plate=6, sand=170, rock=9, dark_rock=4, ring=202, ring_emit=1.2, socket=195, dome=39,
           lit_ring=207, lit_socket=194, inner=200, glint=47, ring_glint=31)


def build(sprite):
    return [
        (NAME, [lib.build_pad(sprite, NAME, CFG, False)], lib.frames_subset(sprite, [17]), "frame-newsha-17.png"),
        (f"{NAME}-f2", [lib.build_pad(sprite, NAME, CFG, True)], lib.frames_subset(sprite, [55]),
         "frame-newsha-55.png"),
    ]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
