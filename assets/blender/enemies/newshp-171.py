"""Ground beacon (newshp.shp frames 171-285, size 1): a 3D version of its sprite.

Seen in episode 1 (level 1.21). A small grey dome on a darker collar with a cross-shaped lamp
on top. Its seven frames only brighten the lamp from dark red through orange to yellow (and the
dome round it catches the light), so one model covers them all: the lamp's and dome's materials
take each frame's palette colour (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshp-171.py [-- --preview out.png]
(-- --frames out.png renders every frame).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b067 as lib  # noqa: E402
from lib_b067 import PX, common  # noqa: E402

NAME = "newshp-171"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = lib.Grid(12, 14)
    m = lib.Mats(sprite, NAME, metallic=0.5, roughness=0.4)
    # The lamp brightens two palette steps a frame: its cross from 112 (frame 171) to 125 (285),
    # its centre from 113 to 127; the dome lightens a step or two as it does.
    frames = (190, 209, 228, 247, 266, 285)
    m.add(112, "lamp", emission_strength=3.0, frames=dict(zip(frames, (115, 117, 119, 121, 123, 125))))
    m.add(113, "lamp_core", emission_strength=5.0, frames=dict(zip(frames, (117, 119, 121, 123, 125, 127))))
    m.add(8, "dome", frames={209: 9, 228: 9, 247: 10, 266: 10, 285: 11})
    bm = bmesh.new()

    cx, cy = g.x(6.5), g.y(7.5)  # the dome fills columns 3-9, rows 4-10
    # Dark collar round the foot, then the grey dome.
    lib.dome(bm, cx, cy, 0.0, 3.6 * PX, 3.6 * PX, 0.06, m[4], segs=16, rings=2)
    lib.dome(bm, cx, cy, 0.03, 3.3 * PX, 3.3 * PX, 0.17, m.slot["dome"], segs=16, rings=5)
    # The cross-shaped lamp (columns 5-7, rows 6-8) and its hot centre.
    lib.frustum(bm, g, 5, 7, 8, 8, 0.17, 0.225, m.slot["lamp"], inset=0.15)
    lib.frustum(bm, g, 6, 6, 7, 9, 0.17, 0.225, m.slot["lamp"], inset=0.15)
    lib.dome(bm, cx, cy, 0.215, 0.6 * PX, 0.6 * PX, 0.03, m.slot["lamp_core"], segs=8, rings=2)

    obj = lib.to_object(NAME, bm, m.list, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
