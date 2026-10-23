"""Sand pod (newsha.shp frames 91, 129): a 3D version of its sprite.

Seen in episode 1 (level 31). A ground tile of brown sand with a glossy tan dome sunk in a dark
crater: a round hatch ring on its top, a small knob on a stalk at its upper right, a spike lying
on the sand below it and a glowing red vent slanting across its lower-left flank. The two frames
only brighten the vent, so one model covers both.

Run: blender --background --python assets/blender/enemies/newsha-91.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b087 as lib  # noqa: E402

NAME = "newsha-91"
C, R = 10.0, 11.6  # dome centre (pixel column / row)
RX, RY, H = 7.6 / 12, 7.0 / 12, 0.42  # dome radii and height
Z0 = 0.05  # top of the sand


def surface(c, r, lift=0.0):
    """The point on the dome above pixel (c, r) and its outward normal."""
    x, y = lib.px(c) - lib.px(C), lib.row(r) - lib.row(R)
    s = (x / RX) ** 2 + (y / RY) ** 2
    z = H * math.sqrt(max(0.0, 1 - s))
    n = Vector((x / RX ** 2, y / RY ** 2, z / H ** 2)).normalized()
    p = Vector((lib.px(C) + x, lib.row(R) + y, Z0 + z))
    return p + n * lift, n


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(22, metallic=0.0, roughness=0.95),  # 0 sand
        pal(17, metallic=0.0, roughness=0.9),  # 1 dark crater
        pal(27, metallic=0.5, roughness=0.25),  # 2 glossy dome
        pal(24, metallic=0.45, roughness=0.35),  # 3 hatch ring
        pal(20, metallic=0.3, roughness=0.5),  # 4 hatch centre
        pal(28, metallic=0.55, roughness=0.25),  # 5 knob
        pal(25, metallic=0.4, roughness=0.4),  # 6 spike
        pal(113, metallic=0.2, roughness=0.6),  # 7 vent lip
        pal(117, emission_strength=2.5),  # 8 vent glow
        pal(121, emission_strength=4.5),  # 9 vent hot spot
    ]
    SAND, CRATER, DOME, RING, HATCH, KNOB, SPIKE, LIP, GLOW, HOT = range(10)
    bm = bmesh.new()

    # Sand filling the tile, and the dark crater the dome sits in.
    lib.box(bm, lib.ex(0), lib.ey(28), lib.ex(24), lib.ey(0), 0.0, Z0, mat=SAND)
    lib.dome(bm, lib.px(11.8), lib.row(13.6), Z0 + 0.002, 8.6 / 12, 9.0 / 12, 0.006, segments=24, rings=1,
             mat=CRATER, smooth=False)

    # The dome.
    lib.dome(bm, lib.px(C), lib.row(R), Z0, RX, RY, H, segments=24, rings=7, mat=DOME)

    # Hatch on top: a raised ring round a dark recessed centre (columns 6-15, rows 7-15).
    hc, hr = 10.2, 10.9
    ring = []
    for k in range(20):
        a = 2 * math.pi * k / 20
        p, _ = surface(hc + 3.6 * math.cos(a), hr - 3.4 * math.sin(a), 0.01)
        ring.append(p)
    ring.append(ring[0])
    lib.polyline_tube(bm, ring, 0.8 / 12, sides=6, mat=RING, caps=False)
    top, n = surface(hc, hr)
    lib.ellipsoid(bm, tuple(top - n * 0.015), 2.7 / 12, 2.6 / 12, 0.03, mat=HATCH, segments=14, rings=5)

    # Knob on a short stalk at the upper right (columns 15-17, rows 3-6).
    p0, n0 = surface(14.8, 6.6, -0.02)
    tip = Vector((lib.px(16.9), lib.row(4.1), Z0 + 0.2))
    lib.polyline_tube(bm, [tuple(p0), tuple(tip)], 0.7 / 12, sides=6, mat=SPIKE)
    lib.ellipsoid(bm, tuple(tip), 1.25 / 12, 1.25 / 12, 1.1 / 12, mat=KNOB, segments=10, rings=5)

    # Spike lying on the sand below the dome (column 10, rows 18-23).
    start = len(bm.verts)
    common.loft(bm, [(lib.row(17.0), 1.3 / 12, 0.08, Z0 + 0.06), (lib.row(19.5), 1.0 / 12, 0.06, Z0 + 0.05),
                     (lib.row(22.0), 0.6 / 12, 0.04, Z0 + 0.03), (lib.row(23.8), 0.0, 0.0, Z0 + 0.02)],
                sides=8, mat_index=SPIKE)
    common.shift_x(bm, start, lib.px(10.2))

    # Glowing vent slanting across the lower-left flank (columns 3-8, rows 13-18).
    path = [(3.6, 13.3), (4.6, 14.6), (5.7, 15.8), (6.9, 16.9), (8.0, 17.6)]
    lib.polyline_tube(bm, [tuple(surface(c, r, -0.03)[0]) for c, r in path], 1.25 / 12, sides=8, mat=LIP)
    lib.polyline_tube(bm, [tuple(surface(c, r, 0.0)[0]) for c, r in path[:-1]], 1.0 / 12, sides=8, mat=GLOW)
    lib.ellipsoid(bm, tuple(surface(5.2, 15.6, 0.05)[0]), 0.8 / 12, 0.8 / 12, 0.04, mat=HOT, segments=8, rings=4)

    return lib.to_object(NAME, bm, mats, coll)


def main(sprite):
    return [(NAME, [build(sprite)], sprite["sprites"], "frame-newsha-91.png")]


if __name__ == "__main__":
    lib.run(NAME, main, __file__)
