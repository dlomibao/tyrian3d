"""Steel ball (newshm.shp frame 115, newsha.shp frames 165, 203, 241, 279): a 3D version of its sprite.

A ground object in episode 1 (levels 13, 21, 23) and episode 3 (level 2): a glossy blue-grey
ball resting on the ground, lit from the upper left with a rim reflection at the lower right.
The newsha frames are the same ball drawn darker (it pulses): every shade 5, 3 and 2 steps down on
frames 165, 203 and 241, back to normal on 279. One model covers every frame; its material takes
the darker shade on those frames.

Run: blender --background --python assets/blender/enemies/newshm-115.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-115"


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, 57, f"{NAME}-pulse", metallic=0.6, roughness=0.2,
                                    frames={165: 52, 203: 54, 241: 55})]
    bm = bmesh.new()
    # The ball spans columns 3-20 and rows 5-21 (centre column 11.5, row 13).
    cx, cy = lib.P(11.5, 13.0)
    rx, ry = 9.0 / 12, 8.6 / 12
    zc, rz = 0.30, 0.43  # its widest point and vertical radius; the bottom is cut by the ground
    sides, rings = 24, 10
    phi0 = -math.asin(zc / rz)  # latitude where the ball meets z = 0
    lat = []
    for k in range(rings):
        phi = phi0 + (math.pi / 2 - phi0) * k / rings
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ring.append(bm.verts.new((cx + rx * math.cos(phi) * math.cos(a), cy + ry * math.cos(phi) * math.sin(a),
                                      zc + rz * math.sin(phi))))
        lat.append(ring)
    apex = bm.verts.new((cx, cy, zc + rz))
    for r0, r1 in zip(lat, lat[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    for i in range(sides):
        bm.faces.new((lat[-1][i], lat[-1][(i + 1) % sides], apex))
    bm.faces.new(list(reversed(lat[0])))
    return lib.finish(NAME, bm, mats, coll, flat_z=1.01)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
