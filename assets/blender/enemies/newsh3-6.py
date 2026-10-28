"""Four-pod spinner (newsh3.shp frame 6): a 3D version of its sprite.

Seen in episode 4 (levels 4 and 36). Four round steel pods on the diagonals, each a short narrow
stem from the hub swelling into a smooth ellipsoidal bulb about as tall as it is wide (9 px: 7 above
the base plane, 2.3 below), joined at a red ball hub about 5 px across that sits on the stems. A
bright stud sits on each pod's inner end where the sprite draws it (a lit pixel with a dark one
beside it, on all four pods alike). The pods are polished steel, all one mid-tone silver: the
sprite's lighter upper-left and darker lower-right pods, its dark stems and its outline ring are its
drawn lighting, which the game's lights, metal reflections and outline make. The hub is a glossy
red ball, one mid red; its highlight is shine, not paint. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-6.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common  # noqa: E402

NAME = "newsh3-6"

# A pod along its axis from the hub centre, in sprite px: (distance, half width, height of the top
# above the base plane, depth of the underside below it). Widths follow the sprite's lobes
# (outline included); the bulb is a round pod about as tall as it is wide, the stem lower.
POD = [(1.0, 1.3, 1.8, 1.0), (2.0, 1.6, 2.3, 1.2), (3.0, 1.9, 2.8, 1.4), (4.0, 2.7, 3.6, 1.6),
       (5.0, 3.9, 4.8, 1.9), (5.9, 4.2, 5.7, 2.1), (6.8, 4.3, 6.4, 2.2), (8.0, 4.35, 6.9, 2.3),
       (9.5, 4.35, 7.0, 2.3), (11.0, 4.2, 6.6, 2.2), (12.0, 3.4, 5.4, 1.9), (12.7, 2.6, 4.0, 1.5),
       (13.1, 1.8, 2.4, 1.1)]
TIP = 13.25  # the sprite's lobe ends blunt, a 4 px flat across at 13.1 px
SIDES = 14
# Hub centre (sprite px from the sprite centre): the red pixels at columns 10-13, rows 11-14.
HUB_X, HUB_Y = 0.0, 1.0
# Every pod and its stem: one mid-tone steel (the sprite's pods average index 9-10; metal reads a
# little darker than its colour, so 10), polished, so the light and environment shade and shine it.
POD_SHADE = 10
POD_METALLIC, POD_ROUGHNESS = 0.8, 0.3
STUD_SHADE = 13
# The hub: one mid red, glossy, no emission (it is lit like the rest).
HUB_SHADE = 73
# The bright studs, at the sprite pixels that draw them (col, row): one per lobe, at its inner end.
STUDS = [(8, 9), (15, 9), (8, 16), (15, 16)]


def pod_rings():
    rings = []
    for d, w, top, under in POD:
        ring = []
        for i in range(SIDES):
            a = 2 * math.pi * (i + 0.5) / SIDES
            u, v = math.cos(a), math.sin(a)
            z = top * v if v > 0 else under * v
            ring.append((w * u / 12, d / 12, z / 12))
        rings.append(ring)
    rings.append([(0.0, TIP / 12, 0.6 / 12)])
    return rings


def pod_top(d, lat):
    """Height (px) of a pod's top surface at distance d along its axis, lat px to the side."""
    for (d0, w0, t0, _), (d1, w1, t1, _) in zip(POD, POD[1:]):
        if d0 <= d <= d1:
            f = (d - d0) / (d1 - d0)
            w, t = w0 + f * (w1 - w0), t0 + f * (t1 - t0)
            v = math.sqrt(max(0.0, 1 - (lat / w) ** 2))
            return t * v
    return 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(POD_SHADE, metallic=POD_METALLIC, roughness=POD_ROUGHNESS),
            pal(STUD_SHADE, metallic=0.6, roughness=0.25),
            pal(HUB_SHADE, metallic=0.05, roughness=0.12)]
    pod_slot, stud_slot, hub_slot = 0, 1, 2

    bm = bmesh.new()
    cx, cy = HUB_X / 12, HUB_Y / 12

    for angle in (45, -45, 135, -135):
        start = len(bm.verts)
        lib.ring_loft(bm, pod_rings(), pod_slot, cap_start=True, cap_end=False)
        lib.rotate_new(bm, start, math.radians(angle), cx, cy)

    # The studs, each on its pod's surface where the sprite draws it, about 0.6 px proud.
    for col, row in STUDS:
        x, y = col + 0.5 - 12, 14 - (row + 0.5)
        ox, oy = x - HUB_X, y - HUB_Y
        d = (abs(ox) + abs(oy)) / math.sqrt(2)
        lat = abs(abs(ox) - abs(oy)) / math.sqrt(2)
        z = pod_top(d, lat)
        lib.ellipsoid(bm, (x / 12, y / 12, (z - 0.2) / 12), (0.75 / 12, 0.75 / 12, 0.8 / 12), segments=6,
                      rings=2, mat_index=stud_slot, top_only=True)

    # The hub: a salmon-red ball 5 px across standing on the stems, its top at about 5.5 px.
    lib.ellipsoid(bm, (cx, cy, 3.0 / 12), (2.5 / 12, 2.5 / 12, 2.5 / 12), segments=12, rings=4,
                  mat_index=hub_slot)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
