"""Floor hatch with a red eye (newsh3.shp frames 18, 56, 94, 284): a 3D version of its sprites.

Seen in episode 4 (level 4.29). A grey floor tile with a red-rimmed pit in it. Closed (frame 18)
two grey hatch plates fill the pit; as it opens (56, 94, 284) the plates slide back under the rim
at the top and bottom and a grey turret housing with a glowing red eye rises in the middle.
Each frame is a different shape, so each gets its own model: newsh3-18 (closed), -f2, -f3, -f4.

Run: blender --background --python assets/blender/enemies/newsh3-18.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b115 as lib  # noqa: E402

NAME = "newsh3-18"
ROOT = common.repo_root(__file__)
X, Y = lib.ex, lib.ey

FLOOR = 0.1  # top of the floor tile
RIM = 0.15  # top of the red rim round the pit
PLATE = 0.085  # top of the hatch plates

# Per frame: upper plate (row edges), lower plate, the light lip of the lower plate, the turret
# housing's top (None while closed) and whether the plates show their diagonal crease.
STATES = [
    (18, dict(upper=(4, 13), lower=(13.4, 22), crease=True, turret=None)),
    (56, dict(upper=(4, 11), lower=(16, 22), crease=True, turret=0.07)),
    (94, dict(upper=(4, 9), lower=(18, 22), crease=False, turret=0.16)),
    (284, dict(upper=(4, 7), lower=(20, 22), crease=False, turret=0.2)),
]


def build(sprite, name, state):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.4, roughness=0.6),  # 0 floor
        pal(3, metallic=0.3, roughness=0.8),  # 1 seams in the floor
        pal(7, metallic=0.5, roughness=0.45),  # 2 light floor ridges
        pal(73, metallic=0.4, roughness=0.45),  # 3 lit side of the rim
        pal(72, metallic=0.4, roughness=0.5),  # 4 shaded side of the rim
        pal(77, metallic=0.4, roughness=0.35),  # 5 rim corner highlight
        pal(2, metallic=0.2, roughness=0.9),  # 6 pit
        pal(4, metallic=0.45, roughness=0.55),  # 7 hatch plates
        pal(6, metallic=0.5, roughness=0.45),  # 8 turret housing top
        pal(117, emission_strength=3.0),  # 9 red eye
        pal(119, emission_strength=4.0),  # 10 bright eye
        pal(123, emission_strength=5.0),  # 11 eye core
    ]
    FL, SEAM, RIDGE, RIM_LIT, RIM_DARK, CORNER, PIT, PLATE_M, HOUSING, EYE, EYE_HOT, CORE = range(12)
    bm = bmesh.new()

    # Floor tile round the pit, with its seams and ridges.
    lib.box(bm, X(0), Y(28), X(3), Y(0), 0, FLOOR, mat=FL)
    lib.box(bm, X(20), Y(28), X(24), Y(0), 0, FLOOR, mat=FL)
    lib.box(bm, X(3), Y(3), X(20), Y(0), 0, FLOOR, mat=FL)
    lib.box(bm, X(3), Y(28), X(20), Y(23), 0, FLOOR, mat=FL)
    lib.box(bm, X(2), Y(28), X(3), Y(0), FLOOR - 0.01, FLOOR + 0.004, mat=SEAM)
    lib.box(bm, X(0), Y(3), X(20), Y(2), FLOOR - 0.01, FLOOR + 0.004, mat=SEAM)
    lib.box(bm, X(21), Y(25), X(22), Y(5), FLOOR - 0.01, FLOOR + 0.018, mat=RIDGE)
    lib.box(bm, X(3), Y(25), X(21), Y(24), FLOOR - 0.01, FLOOR + 0.018, mat=RIDGE)
    lib.box(bm, X(0), Y(16), X(2), Y(15), FLOOR - 0.01, FLOOR + 0.012, mat=RIDGE)

    # Red rim round the pit: lit on the left and top, shaded on the right and bottom.
    lib.box(bm, X(3), Y(23), X(4), Y(3), 0, RIM, mat=RIM_LIT)
    lib.box(bm, X(4), Y(4), X(19), Y(3), 0, RIM, mat=RIM_LIT)
    lib.box(bm, X(19), Y(23), X(20), Y(3), 0, RIM, mat=RIM_DARK)
    lib.box(bm, X(4), Y(23), X(19), Y(22), 0, RIM, mat=RIM_DARK)
    lib.box(bm, X(3), Y(4.5), X(4.5), Y(3), RIM - 0.01, RIM + 0.012, mat=CORNER)

    # Pit floor.
    lib.box(bm, X(4), Y(22), X(19), Y(4), 0, 0.02, mat=PIT)

    # Hatch plates, tucked under the rim, with a light lip on the lower one.
    u0, u1 = state["upper"]
    l0, l1 = state["lower"]
    lib.box(bm, X(4), Y(u1), X(19), Y(u0), 0.03, PLATE, mat=PLATE_M)
    lib.box(bm, X(4), Y(l1), X(19), Y(l0), 0.03, PLATE, mat=PLATE_M)
    lib.box(bm, X(4), Y(l0 + 1), X(19), Y(l0), PLATE - 0.01, PLATE + 0.01, mat=FL)
    if state["crease"]:
        # The light diagonal crease across each plate.
        if u1 - u0 > 6:
            lib.bar(bm, (X(18), Y(7.5)), (X(7), Y(12.5)), 1.2 / 12, PLATE - 0.01, PLATE + 0.008, mat=FL)
            lib.bar(bm, (X(5.5), Y(17.5)), (X(17), Y(20.5)), 1.2 / 12, PLATE - 0.01, PLATE + 0.008, mat=FL)
        else:
            lib.bar(bm, (X(17), Y(7.5)), (X(7), Y(10.5)), 1.2 / 12, PLATE - 0.01, PLATE + 0.008, mat=FL)
            lib.bar(bm, (X(5.5), Y(19.5)), (X(17), Y(20.6)), 1.0 / 12, PLATE - 0.01, PLATE + 0.008, mat=FL)

    top = state["turret"]
    if top is not None:
        # Turret housing on a stem, with a strut to the right, and the eye on top.
        lib.box(bm, X(8), Y(17), X(15), Y(10), 0.02, top, mat=FL)
        lib.box(bm, X(8.3), Y(11), X(14.7), Y(10), top - 0.01, top + 0.012, mat=HOUSING)
        lib.box(bm, X(11), Y(19.5), X(12), Y(17), 0.02, top * 0.6, mat=FL)
        lib.bar(bm, (X(15), Y(14)), (X(18), Y(9.5)), 1.3 / 12, 0.02, top * 0.7, mat=PLATE_M)
        lib.ellipsoid(bm, X(11.5), Y(13), top, 2.4 / 12, 2.1 / 12, 0.075, mat=EYE, segments=14, rings=6, half=True)
        lib.ellipsoid(bm, X(11.6), Y(12.8), top + 0.02, 1.5 / 12, 1.3 / 12, 0.07, mat=EYE_HOT, segments=12, rings=5,
                      half=True)
        lib.ellipsoid(bm, X(11.6), Y(12.5), top + 0.05, 0.7 / 12, 0.7 / 12, 0.045, mat=CORE, segments=10, rings=4,
                      half=True)

    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    shown = []
    for i, (frame, state) in enumerate(STATES):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, state)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", lib.frame_subset(sprite, [frame]))
        shown.append((frame, [obj]))
    lib.preview_frames(ROOT, NAME, sprite, shown, sys.argv)


if __name__ == "__main__":
    main()
