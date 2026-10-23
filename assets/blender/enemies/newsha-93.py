"""Red dome pad (newsha.shp frames 93, 131): a 3D version of its sprite.

Seen in episode 1 (levels 13, 23) and 3. A ground tile of grey rubble and sand with a tan ring
lying on it and a glossy red dome inside the ring. In its second frame the ring flares into a
wider glowing yellow ring and the dome opens into a red rim round a smaller brown dome with a
bright glint, a change of shape, so each frame gets its own model: newsha-93 (frame 93) and
newsha-93-f2 (frame 131). The geometry is lib_b087.build_pad, shared with the green newsha-17.

Run: blender --background --python assets/blender/enemies/newsha-93.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b087 as lib  # noqa: E402

NAME = "newsha-93"
CFG = dict(plate=6, sand=170, rock=9, dark_rock=4, ring=234, ring_emit=0.0, socket=227, dome=71,
           lit_ring=123, lit_socket=226, inner=232, glint=79)


def build(sprite):
    return [
        (NAME, [lib.build_pad(sprite, NAME, CFG, False)], lib.frames_subset(sprite, [93]), "frame-newsha-93.png"),
        (f"{NAME}-f2", [lib.build_pad(sprite, NAME, CFG, True)], lib.frames_subset(sprite, [131]),
         "frame-newsha-131.png"),
    ]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
