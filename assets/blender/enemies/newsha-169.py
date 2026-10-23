"""Spiked mine (newsha.shp frames 169, 207, 245): a 3D version of its sprite.

Seen in episode 1 (levels 13, 23) and 3 (levels 2, 12). A grey ball sitting on the ground, studded
with short spikes pointing up (the bright dots on the sprite) and ringed by long spikes pointing
out sideways. The three frames turn the ball, so the side spikes stand at different angles and
lengths: each frame gets its own model, newsha-169 (169), newsha-169-f2 (207) and -f3 (245),
sharing the ball and its studs.

Run: blender --background --python assets/blender/enemies/newsha-169.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b087 as lib  # noqa: E402

NAME = "newsha-169"
C, R = 11.5, 12.8  # ball centre (pixel column / row)
RX, RY, RZ = 8.4 / 12, 7.8 / 12, 0.4  # ball radii (units)
ZC = RZ + 0.02  # ball centre height: it sits on the ground

# Side spike tips (pixel column, row) per frame, from the sprite.
SPIKES = {
    169: [(11, 0.8), (2.2, 4.2), (-0.2, 13), (21.8, 13), (11, 23.6), (21.2, 23.4), (18.6, 5.8)],
    207: [(11, 1.8), (3.0, 4.8), (-0.2, 13), (22.8, 13), (11, 25.6), (3.0, 21.6), (20.4, 22.4), (19.4, 4.8)],
    245: [(11, 2.8), (20.4, 3.8), (0.8, 13), (23.8, 13), (11, 26.6), (2.0, 22.6), (19.6, 21.6)],
}
# Short spikes pointing up out of the top of the ball (the bright dots).
STUDS = [(6.8, 8.6), (14.2, 7.2), (6.2, 13.2), (11.2, 12.6), (15.2, 16.0), (7.4, 17.0), (16.4, 11.8)]


def surface(c, r):
    """The point on the ball's upper surface above pixel (c, r), and its outward normal."""
    x, y = lib.px(c) - lib.px(C), lib.row(r) - lib.row(R)
    s = (x / RX) ** 2 + (y / RY) ** 2
    z = RZ * math.sqrt(max(0.0, 1 - s))
    n = Vector((x / RX ** 2, y / RY ** 2, z / RZ ** 2)).normalized()
    return Vector((lib.px(C) + x, lib.row(R) + y, ZC + z)), n


def build_frame(sprite, frame):
    tag = NAME if frame == 169 else f"{NAME}-f{[169, 207, 245].index(frame) + 1}"
    coll = common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.6, roughness=0.4),  # 0 ball
        pal(12, metallic=0.7, roughness=0.3),  # 1 spikes
        pal(14, metallic=0.75, roughness=0.25),  # 2 stud tips
        pal(5, metallic=0.5, roughness=0.5),  # 3 dark band round the ball's waist
    ]
    BALL, SPIKE, STUD, BAND = range(4)
    bm = bmesh.new()

    lib.ellipsoid(bm, (lib.px(C), lib.row(R), ZC), RX, RY, RZ, mat=BALL, segments=18, rings=10)
    lib.ellipse_torus(bm, lib.px(C), lib.row(R), ZC - 0.04, RX * 0.97, RY * 0.97, 0.6 / 12, 0.05, segments=24,
                      sides=6, mat=BAND)

    centre = Vector((lib.px(C), lib.row(R), ZC))
    for c, r in SPIKES[frame]:
        tip = Vector((lib.px(c), lib.row(r), ZC))
        d = (tip - centre).normalized()
        # The spike starts inside the ball, where its direction meets the ball's waist.
        reach = 1 / math.sqrt((d.x / RX) ** 2 + (d.y / RY) ** 2)
        base = centre + d * reach * 0.8
        lib.cone(bm, base, tip, 1.5 / 12, sides=6, mat=SPIKE)

    for c, r in STUDS:
        p, n = surface(c, r)
        lib.cone(bm, p - n * 0.04, p + n * 0.13, 1.1 / 12, sides=6, mat=SPIKE)
        lib.ellipsoid(bm, tuple(p + n * 0.11), 0.4 / 12, 0.4 / 12, 0.03, mat=STUD, segments=6, rings=3)

    return tag, lib.to_object(tag, bm, mats, coll)


def build(sprite):
    out = []
    for frame in (169, 207, 245):
        tag, obj = build_frame(sprite, frame)
        out.append((tag, [obj], lib.frames_subset(sprite, [frame]), f"frame-newsha-{frame}.png"))
    return out


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
