"""Glowing wall hatch (newshd.shp frames 239, 241, 243): a 3D version of its sprite.

Seen in episode 1 (level 1.21). A whole 24x28 tile of grey stone wall: courses of bricks round a
big rounded steel hatch (a shield-shaped lid with a lit rim, panel seams across its top and a rib
down its lower half) with a red-hot crescent glowing out from under its lower edge. The three
frames only pulse the glow, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshd-239.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b138 as lib  # noqa: E402
from lib_b138 import common, ex, ey  # noqa: E402

NAME = "newshd-239"

FLOOR = 0.06  # top of the wall's mortar bed
# Bricks as (first col, end col, first row, end row) pixel edges.
BRICKS = [
    (0, 3, 0, 4), (0, 3, 5, 9), (0, 3, 10, 13), (0, 3, 14, 18),
    (21, 24, 0, 2), (21, 24, 2, 5), (21, 24, 5, 9), (21, 24, 10, 14), (21, 24, 14, 19),
    (0, 6, 19, 23), (7, 11, 20, 23), (12, 15, 20, 23), (16, 19, 20, 23), (20, 24, 19, 23),
    (0, 3, 24, 28), (4, 7, 24, 28), (8, 11, 24, 28), (12, 15, 24, 28), (16, 19, 24, 28), (20, 24, 24, 28),
]
# The hatch: straight sides from the top of the tile down to row 8.25, then a round bottom.
LID_L, LID_R, LID_ARC_ROW = 3.6, 19.1, 8.25
LID_CX = (LID_L + LID_R) / 2
LID_R_PX = (LID_R - LID_L) / 2


def lid_outline():
    pts = [(ex(LID_L), ey(0)), (ex(LID_L), ey(LID_ARC_ROW))]
    for k in range(1, 12):
        a = math.pi + math.pi * k / 12  # left, round the bottom, to the right
        pts.append((ex(LID_CX + LID_R_PX * math.cos(a)), ey(LID_ARC_ROW - LID_R_PX * math.sin(a))))
    pts += [(ex(LID_R), ey(LID_ARC_ROW)), (ex(LID_R), ey(0))]
    return pts


def crescent(rx, ry, inner, a0):
    """The glow under the lid: an elliptical arc below the lid (rx, ry in px round the lid's arc
    centre) from angle pi + a0 to 2 pi - a0, back along a circle of radius `inner` inside the lid."""
    outer, back = [], []
    n = 14
    for k in range(n + 1):
        a = math.pi + a0 + (math.pi - 2 * a0) * k / n
        outer.append((ex(LID_CX + rx * math.cos(a)), ey(LID_ARC_ROW - ry * math.sin(a))))
        back.append((ex(LID_CX + inner * math.cos(a)), ey(LID_ARC_ROW - inner * math.sin(a))))
    return outer + list(reversed(back))


def build(sprite):
    coll = common.reset_collection(NAME)
    pix = sprite["frames"][0]["pixels"]
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(3, metallic=0.05, roughness=0.95),  # 0 mortar and the shadowed floor
        pal(9, metallic=0.6, roughness=0.35),  # 1 hatch face
        pal(12, metallic=0.6, roughness=0.3),  # 2 lit rim
        pal(5, metallic=0.5, roughness=0.45),  # 3 rim's lower (shaded) side
        pal(7, metallic=0.5, roughness=0.5),  # 4 panel seams
        pal(10, metallic=0.6, roughness=0.3),  # 5 rib
        pal(116, emission_strength=2.5),  # 6 red glow
        pal(121, emission_strength=4.0),  # 7 hot orange core of the glow
        pal(8, metallic=0.5, roughness=0.4),  # 8 rim's right side / seams
    ]
    brick_slot = {}
    MORTAR, FACE, RIM, RIM_LOW, SEAM, RIB, GLOW, HOT, RIM_R = range(9)
    bm = bmesh.new()

    # Mortar bed over the whole tile.
    lib.box(bm, ex(0), ex(24), ey(28), ey(0), 0.0, FLOOR, MORTAR)

    # Bricks, each painted with the sprite's commonest grey over it.
    for k, (c0, c1, r0, r1) in enumerate(BRICKS):
        idx = lib.dominant(pix, c0, c1, r0, r1, skip=lib.OUTLINE + tuple(range(112, 128)), default=4)
        idx = max(idx, 3)
        if idx not in brick_slot:
            brick_slot[idx] = len(mats)
            mats.append(pal(idx, metallic=0.05, roughness=0.9))
        top = FLOOR + 0.05 + 0.012 * ((k * 7) % 3)
        lib.box(bm, ex(c0 + 0.12), ex(c1 - 0.12), ey(r1 - 0.12), ey(r0 + 0.12), FLOOR - 0.01, top, brick_slot[idx])

    # The glow, sunk just above the floor under the lid's lower edge.
    lib.prism(bm, crescent(9.5, 11.6, LID_R_PX - 1.0, 0.29), FLOOR - 0.01, FLOOR + 0.02, GLOW)
    lib.prism(bm, crescent(8.3, 10.2, LID_R_PX - 1.0, 0.75), FLOOR, FLOOR + 0.03, HOT)

    # The hatch lid: a flat-topped plate with a rounded rim.
    top = 0.31
    faces = lib.pillow(bm, lid_outline(), (ex(LID_CX), ey(7.0)), FLOOR,
                       [(0.975, 0.19), (0.94, 0.27), (0.88, top - 0.005), (0.5, top)], FACE)
    bm.normal_update()
    for f in faces:
        n = f.normal
        if n.z > 0.8:
            f.material_index = FACE
        elif n.y < -0.45:
            f.material_index = RIM_LOW
        elif n.x > 0.45:
            f.material_index = RIM_R
        else:
            f.material_index = RIM

    # Panel seams across the top half, and the rib (flanked by seams) down the lower half.
    t = 0.3 / 12
    z0, z1 = top - 0.02, top + 0.012
    lib.box(bm, ex(4.7), ex(18.3), ey(6.5) + -t, ey(6.5) + t, z0, z1, SEAM)
    for c in (7.5, 15.5):
        lib.box(bm, ex(c) - t, ex(c) + t, ey(6.5), ey(0.4), z0, z1, RIM_R)
    for c in (9.5, 11.5):
        lib.box(bm, ex(c) - t, ex(c) + t, ey(14.3), ey(6.5), z0, z1, RIM_R)
    lib.box(bm, ex(10.15), ex(10.85), ey(14.6), ey(6.6), z0, top + 0.03, RIB)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
