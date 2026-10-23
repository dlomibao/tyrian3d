"""Grey fork ship (newsh2.shp frame 269): a 3D version of its sprite.

Seen in episode 1 (levels 1.28, 1.30, 1.36) and 3.17. It flies nose right: a fat grey bullet of
a fuselage with cream cowls and two red lights at its back, a shiny tail cylinder through a thin
upright spar, and two thin rails reaching forward above and below it on swept brown struts. The
sprite is mirror symmetric about row 13. One frame.

Run: blender --background --python assets/blender/enemies/newsh2-269.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b053 as lib  # noqa: E402
from lib_b053 import PX, X, Y  # noqa: E402

NAME = "newsh2-269"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 13.0  # the sprite's mirror row


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.55, roughness=0.35),  # 0 grey hull
        pal(11, metallic=0.6, roughness=0.25),  # 1 light grey: highlights, tail cylinder
        pal(4, metallic=0.4, roughness=0.5),  # 2 dark grey: slot, spar
        pal(29, metallic=0.3, roughness=0.4),  # 3 cream cowls
        pal(165, metallic=0.2, roughness=0.6),  # 4 dark brown under the cowls
        pal(23, metallic=0.3, roughness=0.5),  # 5 brown struts
        pal(7, metallic=0.6, roughness=0.3),  # 6 rails
        pal(119, emission_strength=3.5),  # 7 red lights
        pal(31, emission_strength=2.0),  # 8 pale light on the flank
    ]
    HULL, LIGHT, DARK, CREAM, BROWN, STRUT, RAIL, RED, PALE = range(9)
    bm = bmesh.new()
    yc = Y(AXIS)

    # Fuselage along +X, back (column 4) to nose (column 23.6): (column, half width px, half height).
    hull = [(3.8, 0.0, 0.0), (4.2, 2.6, 0.1), (5.0, 4.6, 0.17), (6.5, 5.6, 0.2), (8.5, 6.1, 0.22),
            (12.0, 6.2, 0.23), (15.0, 5.8, 0.22), (17.0, 4.9, 0.2), (19.0, 3.9, 0.17), (20.5, 3.1, 0.14),
            (21.8, 2.0, 0.1), (22.8, 1.0, 0.06), (23.6, 0.0, 0.0)]
    lib.sweep(bm, [(X(c), yc, 0.0, w * PX, h) for c, w, h in hull], sides=16, mat=HULL)
    # A light spine along the top of the fuselage's upper half (rows 8-10 are its highlight).
    lib.sweep(bm, [(X(8.0), Y(9.3), 0.13, 0.0, 0.0), (X(9.0), Y(9.3), 0.15, 1.2 * PX, 0.05),
                   (X(15.0), Y(9.5), 0.15, 1.2 * PX, 0.05), (X(17.5), Y(10.0), 0.12, 0.0, 0.0)],
              sides=8, mat=LIGHT)
    # Dark slot across the middle of the back (rows 11-12, columns 7-11) and a groove at row 14.
    lib.box(bm, X(6.5), Y(12.4), X(11.5), Y(11.0), 0.15, 0.235, mat=DARK)
    lib.box(bm, X(12.6), Y(14.4), X(16.5), Y(13.7), 0.17, 0.225, mat=DARK)
    # Pale light on the flank (row 13, columns 12-14) with a bright seam above and below it.
    lib.sweep(bm, [(X(11.8), Y(13.0), 0.2, 0.0, 0.0), (X(12.2), Y(13.0), 0.21, 0.55 * PX, 0.03),
                   (X(14.4), Y(13.0), 0.2, 0.55 * PX, 0.03), (X(14.8), Y(13.0), 0.2, 0.0, 0.0)],
              sides=8, mat=PALE)
    lib.sweep(bm, [(X(12.0), Y(10.8), 0.2, 0.5 * PX, 0.025), (X(12.0), Y(15.6), 0.2, 0.5 * PX, 0.025)],
              sides=6, mat=LIGHT, up=(0, 0, 1))

    # Two red lights at the back of the slot (columns 6 and 8, rows 12-14).
    for c in (6.0, 8.0):
        lib.sweep(bm, [(X(c), Y(11.6), 0.2, 0.0, 0.0), (X(c), Y(12.0), 0.215, 0.5 * PX, 0.035),
                       (X(c), Y(14.0), 0.215, 0.5 * PX, 0.035), (X(c), Y(14.4), 0.2, 0.0, 0.0)],
                  sides=8, mat=RED)

    # ---- the half above the axis (mirrored below) ----
    first = len(bm.verts)
    # Cream cowl hugging the back of the fuselage (columns 5-8, rows 8-10) on a dark brown lip.
    lib.ellipsoid(bm, (X(7.6), Y(7.9), 0.0), (2.6 * PX, 1.1 * PX, 0.15), mat=BROWN, segments=12, rings=6)
    lib.ellipsoid(bm, (X(6.2), Y(9.6), 0.06), (1.5 * PX, 1.2 * PX, 0.17), mat=CREAM, segments=12, rings=6)

    # Swept brown strut from the rail's back end down to the spar's top (rows 3-6).
    lib.sweep(bm, [(X(6.4), Y(3.0), 0.0, 0.0, 0.0), (X(5.6), Y(3.4), 0.0, 1.0 * PX, 0.06),
                   (X(3.6), Y(5.0), 0.0, 1.1 * PX, 0.065), (X(1.0), Y(5.9), 0.0, 1.1 * PX, 0.065),
                   (X(-0.3), Y(6.1), 0.0, 0.0, 0.0)], sides=8, mat=STRUT)
    # Rail reaching forward (row 3, columns 6-14) with a bright collar at column 8.
    lib.sweep(bm, [(X(5.8), Y(3.0), 0.0, 0.0, 0.0), (X(6.3), Y(3.0), 0.0, 0.75 * PX, 0.05),
                   (X(14.2), Y(3.0), 0.0, 0.75 * PX, 0.05), (X(14.9), Y(3.0), 0.0, 0.0, 0.0)],
              sides=8, mat=RAIL)
    lib.sweep(bm, [(X(7.6), Y(3.0), 0.0, 0.95 * PX, 0.06), (X(8.5), Y(3.0), 0.0, 0.95 * PX, 0.06)],
              sides=8, mat=LIGHT)
    lib.mirror(bm, first, axis="y", about=yc)

    # Upright spar at the back (column 2, rows 6-20) and the shiny tail cylinder through it.
    lib.sweep(bm, [(X(2.0), Y(5.6), 0.0, 0.8 * PX, 0.05), (X(2.0), Y(20.4), 0.0, 0.8 * PX, 0.05)],
              sides=8, mat=DARK)
    lib.sweep(bm, [(X(-0.4), Y(12.3), 0.0, 0.0, 0.0), (X(-0.1), Y(12.3), 0.0, 1.6 * PX, 0.1),
                   (X(0.8), Y(12.3), 0.0, 2.2 * PX, 0.13), (X(3.5), Y(12.6), 0.0, 2.2 * PX, 0.13),
                   (X(4.6), Y(12.8), 0.0, 1.8 * PX, 0.11)], sides=12, mat=LIGHT)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
