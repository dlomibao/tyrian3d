"""Tan claw craft (newsh8.shp frames 267, 269, 271): a 3D version of its sprites.

Seen in episode 3 (level 3.4). Two thick tan arms sweep out from the top of the craft and curl
down into legs either side of a grey housing. A glowing red T-shaped emitter stands on the
housing's back, and a hot slot in its front, between two short grey prongs, closes from frame to
frame: wide open (267), half shut (269) and a slit (271). The slot changes shape, so each frame
gets its own model (newsh8-267, -f2, -f3). Frame 267 is drawn one pixel right of the others, so
its model's axis is too.

Run: blender --background --python assets/blender/enemies/newsh8-267.py [-- --preview out.png]
(each model's preview is written as <model>.png next to out.png).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b035 as lib  # noqa: E402

NAME = "newsh8-267"
ROOT = common.repo_root(__file__)
PX = lib.PX
G = lib.Grid(24, 28)

# frame -> (axis column, width of the hot slot in px)
FRAMES = [(267, 12, 5.0), (269, 11, 3.0), (271, 11, 1.0)]


def build(sprite, name, axis_col, slot):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh8_267", **kw)  # noqa: E731
    mats = [
        pal(25, metallic=0.25, roughness=0.5),  # 0 tan arms
        pal(28, metallic=0.4, roughness=0.3),  # 1 light ridges
        pal(21, metallic=0.3, roughness=0.6),  # 2 dark tan underside of the legs
        pal(7, metallic=0.6, roughness=0.35),  # 3 grey housing
        pal(11, metallic=0.7, roughness=0.25),  # 4 light grey lid
        pal(113, metallic=0.2, roughness=0.6),  # 5 dark red slot rim
        pal(123, emission_strength=5.0),  # 6 hot slot
        pal(119, emission_strength=3.0),  # 7 red emitter
        pal(124, emission_strength=5.0),  # 8 emitter bulb
        pal(9, metallic=0.6, roughness=0.35),  # 9 grey prongs
    ]
    ARM, RIDGE, UNDER, HOUSE, LID, RIM, HOT, RED, BULB, PRONG = range(10)
    ax = G.x(axis_col)
    X = lambda dc: ax + dc * PX  # noqa: E731  (dc: px from the axis)
    y = G.y
    bm = bmesh.new()

    # ---- left arm (mirrored) ----
    start = len(bm.verts)
    # The arm, from its root beside the emitter (row 9), out over the shoulder (rows 12-17) and
    # down into the leg (rows 18-23): (px from axis, row, z, half width px, half height).
    arm = [(-2.8, 8.4, 0.05, 0.0, 0.0), (-2.8, 8.8, 0.05, 1.6, 0.06), (-3.1, 10.0, 0.06, 2.3, 0.09),
           (-4.2, 11.6, 0.06, 3.4, 0.12), (-5.6, 13.4, 0.05, 4.1, 0.14), (-6.4, 15.3, 0.03, 3.9, 0.13),
           (-7.4, 16.9, 0.01, 2.7, 0.1), (-7.1, 18.4, 0.0, 1.6, 0.08), (-6.9, 21.4, -0.01, 1.6, 0.08),
           (-6.5, 22.9, -0.02, 1.2, 0.06), (-6.3, 23.6, -0.02, 0.0, 0.0)]
    lib.sweep(bm, [(X(c), y(r), z, w * PX, h) for c, r, z, w, h in arm], sides=10, mat=ARM)
    # The bright ridge along the arm's outer crest and the lit inner edge of the shoulder.
    crest = [(-5.4, 12.2, 0.13, 0.0, 0.0), (-6.0, 12.8, 0.15, 0.8, 0.04), (-7.4, 14.4, 0.14, 0.9, 0.045),
             (-8.4, 16.0, 0.09, 0.8, 0.04), (-8.0, 18.4, 0.06, 0.7, 0.035), (-7.9, 21.2, 0.05, 0.6, 0.03),
             (-7.6, 22.4, 0.04, 0.0, 0.0)]
    lib.sweep(bm, [(X(c), y(r), z, w * PX, h) for c, r, z, w, h in crest], sides=6, mat=RIDGE)
    inner = [(-4.0, 12.0, 0.1, 0.0, 0.0), (-4.0, 12.6, 0.11, 0.7, 0.035), (-4.0, 16.0, 0.08, 0.7, 0.035),
             (-4.2, 16.8, 0.05, 0.0, 0.0)]
    lib.sweep(bm, [(X(c), y(r), z, w * PX, h) for c, r, z, w, h in inner], sides=6, mat=RIDGE)
    # Dark underside of the leg.
    leg = [(-6.6, 17.5, -0.05, 0.0, 0.0), (-6.6, 18.0, -0.05, 1.2, 0.05), (-6.4, 22.4, -0.06, 1.0, 0.04),
           (-6.2, 23.0, -0.06, 0.0, 0.0)]
    lib.sweep(bm, [(X(c), y(r), z, w * PX, h) for c, r, z, w, h in leg], sides=6, mat=UNDER)
    # Grey prong under the housing (row 19, 2 px off the axis).
    lib.sweep(bm, [(X(-2.0), y(16.5), -0.02, 0.6 * PX, 0.04), (X(-2.0), y(19.3), -0.02, 0.55 * PX, 0.035),
                   (X(-2.0), y(19.8), -0.02, 0.0, 0.0)], sides=6, mat=PRONG)
    lib.mirror_x(bm, start, axis=ax)

    # ---- centre ----
    # Grey housing between the arms (rows 12-17, 7 px wide) with a light lid across row 14.
    lib.sweep(bm, [(ax, y(11.4), 0.01, 3.0 * PX, 0.07), (ax, y(11.8), 0.01, 3.5 * PX, 0.1),
                   (ax, y(17.2), 0.01, 3.5 * PX, 0.1), (ax, y(17.6), 0.01, 3.0 * PX, 0.07)], sides=8, mat=HOUSE,
              smooth=False)
    lib.box(bm, X(-2.6), y(14.5), X(2.6), y(13.4), 0.09, 0.115, mat=LID)
    # The hot slot in the housing's front (rows 15-17), its width set by the frame.
    lib.box(bm, X(-slot / 2 - 0.4), y(17.5), X(slot / 2 + 0.4), y(14.6), 0.08, 0.1, mat=RIM)
    lib.box(bm, X(-slot / 2), y(17.3), X(slot / 2), y(15.5), 0.09, 0.105, mat=HOT)

    # Red emitter on the housing's back: a crossbar (row 7), a bulb (row 8) and the stem (rows 8-13).
    lib.sweep(bm, [(X(-2.6), y(7.0), 0.13, 0.0, 0.0), (X(-2.2), y(7.0), 0.13, 0.8 * PX, 0.05),
                   (X(2.2), y(7.0), 0.13, 0.8 * PX, 0.05), (X(2.6), y(7.0), 0.13, 0.0, 0.0)], sides=8, mat=RED)
    lib.ellipsoid(bm, ax, y(8.0), 0.13, 1.4 * PX, 1.0 * PX, 0.05, mat=BULB, segments=10, rings=5)
    lib.sweep(bm, [(ax, y(8.0), 0.12, 0.7 * PX, 0.045), (ax, y(12.0), 0.12, 0.7 * PX, 0.045),
                   (ax, y(13.6), 0.1, 0.6 * PX, 0.04), (ax, y(14.0), 0.1, 0.0, 0.0)], sides=8, mat=RED)

    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    out = lib.preview_arg()
    for i, (frame, axis_col, slot) in enumerate(FRAMES):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, axis_col, slot)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [frame]}])
        if out:
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh8-{frame}.png"
            common.render_preview([obj], out if i == 0 else out.with_name(f"{name}.png"), ref, size=2)


if __name__ == "__main__":
    main()
