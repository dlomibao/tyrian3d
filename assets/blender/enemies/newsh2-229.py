"""Shield drone in a spinning ring (newsh2.shp frames 229-243): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. A small grey shield-shaped core, split down the
middle into two rounded lobes with a red eye on each top corner, inside a ring of two polished
grey arcs (about 140 degrees each, with gaps between them). The core stays still while the ring
turns clockwise 22.5 degrees a frame, so the eight frames are eight models of the same thing with
the ring turned: newsh2-229 (frame 229), newsh2-229-f2 (231) ... newsh2-229-f8 (243).

Run: blender --background --python assets/blender/enemies/newsh2-229.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-229"
U = 1 / 12
CX, CY = lib.px(12), lib.row(13)  # the ring's centre
RING_R = 8.5 * U
TUBE_R = 1.3 * U
HALF_ARC = math.radians(70)


def build_one(sprite, name, turn):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.75, roughness=0.25),  # 0 ring
        pal(9, metallic=0.6, roughness=0.35),  # 1 core lobes
        pal(119, emission_strength=4.0),  # 2 red eyes
        pal(4, metallic=0.4, roughness=0.5),  # 3 dark groove
    ]
    RING, CORE, EYE, GROOVE = range(4)
    bm = bmesh.new()

    # Two arcs, centred left and right in frame 229, turned clockwise by `turn`.
    n = 14
    for centre in (math.pi, 0.0):
        pts, radii = [], []
        for i in range(n + 1):
            a = centre - turn - HALF_ARC + 2 * HALF_ARC * i / n
            pts.append((CX + RING_R * math.cos(a), CY + RING_R * math.sin(a), 0.0))
            end = min(i, n - i)
            radii.append(TUBE_R * (0.55, 0.85, 1.0)[min(end, 2)])
        lib.polyline_tube(bm, pts, radii, sides=8, mat_index=RING)

    # The core: two lobes either side of column 12, rows 9-15, flat across the top and pointed below.
    for s in (-1, 1):
        sections = []
        for r, w, h in ((8.6, 0.0, 0.0), (8.75, 1.3, 0.1), (9.3, 1.75, 0.15), (11.5, 1.85, 0.17),
                        (13.5, 1.7, 0.15), (14.5, 1.25, 0.12), (15.3, 0.6, 0.08), (15.7, 0.0, 0.0)):
            sections.append((lib.ey(r), w * U, h, 0.0))
        lib.Profile(sections).build(bm, sides=12, mat_index=CORE, dx=CX + s * 1.8 * U)
    # Dark groove between the lobes.
    common.slab(bm, [(CX - 0.35 * U, lib.ey(14.6)), (CX + 0.35 * U, lib.ey(14.6)), (CX + 0.35 * U, lib.ey(9.0)),
                     (CX - 0.35 * U, lib.ey(9.0))], 0.24, z=0.0, mat_index=GROOVE)
    # Red eyes on the top corners (columns 9-10 and 14-15, rows 9-10).
    for c in (9.7, 14.3):
        lib.ellipsoid(bm, (lib.px(c), lib.row(9.5), 0.1), (1.3 * U, 1.1 * U, 0.08), segments=10, rings=6,
                      mat_index=EYE)

    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build_one(sprite, name, k * math.pi / 8)
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
