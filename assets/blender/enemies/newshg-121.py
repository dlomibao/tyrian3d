"""Orb claw (newshg.shp frames 121, 123, 125): a 3D version of its sprite.

Seen in episode 2 (level sections 4 and 19). A glossy violet orb on a shoulder bar, with two
jointed arms hanging below it (a round upper segment, a round lower segment and a curved tan claw
each). Over the three frames the claws close (the left arm first, then both) while the orb charges
from dark to white-hot, so each frame gets its own model: newshg-121 (open), newshg-121-f2 (frame
123) and newshg-121-f3 (closed, frame 125).

Run: blender --background --python assets/blender/enemies/newshg-121.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b034 as lib  # noqa: E402
from lib_b034 import common, px, row  # noqa: E402

NAME = "newshg-121"

# Per frame: (sheet frame, model, (left upper, left lower), (right upper, right lower) shifts in px
# toward the middle, orb palette index, orb glow).
STATES = [
    (121, NAME, (0, 0), (0, 0), 89, 0.0),
    (123, f"{NAME}-f2", (1, 1), (0, 0), 91, 1.5),
    (125, f"{NAME}-f3", (1.5, 3), (1.5, 3), 95, 4.0),
]


def build_state(sprite, model, coll, left, right, orb_index, glow):
    pal = lambda i, **kw: common.palette_material(sprite, i, model, **kw)  # noqa: E731
    mats = [
        pal(89, metallic=0.45, roughness=0.3),  # 0 arm segments
        pal(92, metallic=0.4, roughness=0.2),  # 1 segment highlights
        pal(84, metallic=0.4, roughness=0.5),  # 2 dark joints, shoulder bar
        pal(25, metallic=0.5, roughness=0.35),  # 3 tan claws
        pal(31, metallic=0.4, roughness=0.2),  # 4 claw highlight
        pal(orb_index, metallic=0.2, roughness=0.1, emission_strength=glow),  # 5 orb
        pal(95, metallic=0.1, roughness=0.05, emission_strength=max(glow, 1.0)),  # 6 orb glint
    ]
    ARM, HI, JOINT, CLAW, CLAW_HI, ORB, GLINT = range(7)
    bm = bmesh.new()

    # The orb (rows 1-8, columns 8-16) on a dark collar.
    lib.ellipsoid(bm, (px(12), row(4.5), 0.05), (4.6 / 12, 4.2 / 12, 0.24), segments=20, rings=10,
                  mat_index=ORB, bottom=0.6)
    if glow < 3:
        # A glint at its upper left (columns 10-12, rows 3-5) while it is not yet white-hot.
        lib.ellipsoid(bm, (px(11.2), row(3.8), 0.18), (1.7 / 12, 1.4 / 12, 0.11), segments=10, rings=5,
                      mat_index=GLINT)
    lib.ellipsoid(bm, (px(12), row(8.2), 0.0), (4.0 / 12, 1.3 / 12, 0.08), segments=12, rings=5, mat_index=JOINT)

    for sign, (su, sl) in ((-1, left), (1, right)):
        def X(c, sign=sign):
            """Column on the left side (c < 12) mirrored to the right for sign > 0."""
            return px(c) if sign < 0 else px(24 - c)
        # Shoulder bar from the collar to the upper segment (row 9).
        lib.polyline_tube(bm, [(X(11.5), row(9.0), 0.0), (X(7.5 + su), row(9.6), 0.0)], 1.0 / 12, sides=8,
                          mat_index=ARM, flat=0.7)
        # Upper segment (rows 9-14, columns 4-9).
        cu, ru = 6.6 + su, 11.8
        lib.ellipsoid(bm, (X(cu), row(ru), 0.0), (3.2 / 12, 2.8 / 12, 0.16), segments=14, rings=7, mat_index=ARM)
        lib.ellipsoid(bm, (X(cu - 0.6), row(ru - 0.6), 0.06), (1.5 / 12, 1.3 / 12, 0.1), segments=10, rings=5,
                      mat_index=HI)
        # Joint and lower segment (rows 15-19, columns 2-7).
        cl, rl = 4.6 + sl, 17.4
        lib.polyline_tube(bm, [(X(cu - 1.0), row(ru + 1.5), 0.0), (X(cl + 0.8), row(rl - 1.5), 0.0)], 1.0 / 12,
                          sides=8, mat_index=JOINT, flat=0.7)
        lib.ellipsoid(bm, (X(cl), row(rl), 0.0), (3.3 / 12, 2.8 / 12, 0.16), segments=14, rings=7, mat_index=ARM)
        lib.ellipsoid(bm, (X(cl - 0.7), row(rl - 0.7), 0.06), (1.6 / 12, 1.2 / 12, 0.1), segments=10, rings=5,
                      mat_index=HI)
        # Tan claw curving down and in (rows 20-25).
        pts = [(cl, 19.4), (cl + 0.4, 21.4), (cl + 0.9, 23.2), (cl + 1.9, 24.7), (cl + 3.2, 25.6)]
        lib.polyline_tube(bm, [(X(c), row(r), -0.01) for c, r in pts],
                          [1.6 / 12, 1.5 / 12, 1.2 / 12, 0.8 / 12, 0.0], sides=8, mat_index=CLAW, flat=0.6)
        lib.polyline_tube(bm, [(X(c + 0.5), row(r), 0.05) for c, r in pts[1:4]], [0.5 / 12, 0.4 / 12, 0.25 / 12],
                          sides=5, mat_index=CLAW_HI, flat=0.6)
    return common.mesh_object(model, bm, mats, coll, smooth=True)


def build(sprite):
    coll = common.reset_collection(NAME)
    out = []
    order = [f["index"] for f in sprite["frames"]]
    for frame, model, left, right, orb, glow in STATES:
        obj = build_state(sprite, model, coll, left, right, orb, glow)
        out.append((model, [obj], lib.subset(sprite, [frame])))
        sprite.setdefault("_preview", {})[model] = order.index(frame)
    return out


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
