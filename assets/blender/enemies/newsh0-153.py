"""Violet cross mine (newsh0.shp frames 153, 155, 157): a 3D version of its sprite.

A ground emplacement in episode 2 (level 22): a violet steel dome in four rounded quarters split
by a cross-shaped seam, with a stubby knob sticking out north, south, east and west. The frames
light the seam: a red spark at the centre that spreads along the cross. That is a glow, so one
model covers all three, with the seam glowing red and an orange core where its arms meet.

Run: blender --background --python assets/blender/enemies/newsh0-153.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b104 as lib  # noqa: E402
from lib_b104 import common, px, row  # noqa: E402

NAME = "newsh0-153"
CX, CY = px(12), row(13)  # the centre pixel; the sprite is symmetric about it


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(83, metallic=0.4, roughness=0.6),  # 0 dark base and seam floor
        pal(86, metallic=0.55, roughness=0.4),  # 1 quarter walls
        pal(89, metallic=0.6, roughness=0.35),  # 2 quarters
        pal(92, metallic=0.65, roughness=0.3),  # 3 quarter crowns
        pal(90, metallic=0.6, roughness=0.35),  # 4 knobs
        pal(94, metallic=0.65, roughness=0.25),  # 5 knob caps
        pal(117, emission_strength=3.0),  # 6 red seam glow
        pal(120, emission_strength=4.0),  # 7 orange centre
        pal(123, emission_strength=5.0),  # 8 yellow core
    ]
    BASE, WALL, QUARTER, CROWN, KNOB, CAP, SEAM, CENTRE, CORE = range(9)
    bm = bmesh.new()

    # Dark round base under the dome (columns 7-17, rows 8-18).
    lib.stack(bm, CX, CY, [(0.0, 5.6 / 12, 5.6 / 12, 2.2), (0.12, 5.6 / 12, 5.6 / 12, 2.2)], n=24, mats=BASE)

    # Four quarters, each a rounded dome centred in its quadrant, leaving a cross-shaped seam.
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = CX + sx * 2.6 / 12, CY + sy * 2.6 / 12
            lib.stack(bm, cx, cy, [
                (0.04, 3.0 / 12, 3.0 / 12, 2.4),
                (0.12, 3.0 / 12, 3.0 / 12, 2.4),
                (0.20, 2.7 / 12, 2.7 / 12, 2.2),
                (0.27, 2.0 / 12, 2.0 / 12, 2.0),
                (0.31, 1.0 / 12, 1.0 / 12, 2.0),
                (0.32, 0.0, 0.0, 2.0),
            ], n=16, mats=[WALL, QUARTER, QUARTER, CROWN, CROWN])

    # Knobs north, south, west and east (rows 5-7 / 19-21, columns 4-6 / 18-20).
    for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
        kx, ky = CX + dx * 6.3 / 12, CY + dy * 6.3 / 12
        rx, ry = (2.5 / 12, 2.2 / 12) if dx == 0 else (2.2 / 12, 2.5 / 12)
        lib.dome(bm, kx, ky, 0.0, rx, ry, 0.08, n=14, steps=3, p=2.6, base=0.1, mats=KNOB)
        lib.dome(bm, kx + dx * 0.3 / 12, ky + dy * 0.3 / 12, 0.15, rx * 0.5, ry * 0.5, 0.05, n=10, steps=2,
                 mats=CAP)

    # The glowing seam: a red cross down the grooves, with an orange core where its arms meet.
    for along_x in (True, False):
        half, w = 5.4 / 12, 0.6 / 12
        rx, ry = (half, w) if along_x else (w, half)
        lib.stack(bm, CX, CY, [(0.1, rx, ry, 4.0), (0.25, rx, ry, 4.0)], n=12, mats=SEAM)
    lib.dome(bm, CX, CY, 0.18, 1.3 / 12, 1.3 / 12, 0.12, n=12, steps=3, mats=CENTRE)
    lib.dome(bm, CX, CY, 0.28, 0.6 / 12, 0.6 / 12, 0.04, n=10, steps=2, mats=CORE)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
