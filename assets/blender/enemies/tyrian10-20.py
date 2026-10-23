"""Spinning grey disc (tyrian.shp #10 frames 20-25): a 3D version of its sprite.

Seen in episode 1 (level 16) and episode 4. A small grey metal disc, a thick coin with a bevelled
bright rim, that spins about the screen's vertical: frame 20 shows its flat face, the next frames
turn it until it's edge-on (frame 23) and back round. The outline changes from frame to frame, so
each frame gets the same disc turned to its angle: tyrian10-20, tyrian10-20-f2 ... -f6.

Run: blender --background --python assets/blender/enemies/tyrian10-20.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b039 as lib  # noqa: E402

NAME = "tyrian10-20"
ROOT = common.repo_root(__file__)
U = 1 / 12

# Frame -> turn about the vertical (degrees), picked so the outline's width matches the sprite
# (9, 7, 5, 3, 5, 7 px inside the outline). Negative shows the rim on the right (frames 21, 22).
FRAMES = [(20, 0), (21, -50), (22, -70), (23, -90), (24, 70), (25, 50)]

# Centre of the disc: column 5, row 6 of the 12x14 tile.
CX, CY = lib.px(5, 12), lib.row(6, 14)


def build(sprite, name, angle):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.45, roughness=0.35),  # 0 grey face
        pal(9, metallic=0.5, roughness=0.3),  # 1 bevelled rim
        pal(11, metallic=0.5, roughness=0.25),  # 2 bright edge band
    ]
    FACE, BEVEL, EDGE = range(3)
    bm = bmesh.new()
    # Profile from the top face's centre round the rim to the bottom's (radius, z) in px: a thick
    # coin 3 px across, slightly domed faces, a bevel on both sides and a straight edge band.
    prof = [(0, 1.7), (2.2, 1.6), (3.8, 1.35), (4.4, 0.9), (4.65, 0.45), (4.65, -0.45), (4.4, -0.9),
            (3.8, -1.35), (2.2, -1.6), (0, -1.7)]
    mats_bands = [FACE, FACE, BEVEL, BEVEL, EDGE, BEVEL, BEVEL, FACE, FACE]
    lib.lathe(bm, [(r * U, z * U) for r, z in prof], sides=24, mats=mats_bands)
    lib.transform(bm, 0, lib.rotate_y(math.radians(angle)))
    lib.transform(bm, 0, lambda p: (p[0] + CX, p[1] + CY, p[2]))
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    models = []
    for i, (frame, angle) in enumerate(FRAMES):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        models.append((name, [build(sprite, name, angle)], [frame]))
    lib.export_frames(ROOT, NAME, models, "tyrian10")


if __name__ == "__main__":
    main()
