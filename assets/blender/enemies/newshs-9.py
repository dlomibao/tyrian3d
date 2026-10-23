"""Small grey drone (newshs.shp frames 9, 10, 28, 29): a 3D version of its sprite.

Seen in episode 1 (level 23) and episode 3 (level 2). A one-tile silver craft: a wide hammerhead
bar at the top, a narrow neck, a body with two rounded side pods, and a glowing band near the
tail (rows 10) above a short grey nozzle. The four frames only change the band's glow (red to
yellow), so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshs-9.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b040 as lib  # noqa: E402

NAME = "newshs-9"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
S = 1  # sprite size: one 12x14 tile
AXIS = 5.5  # column edge the sprite is symmetric about (its centre column is 5)


def row(r):
    return lib.row(r, S)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(13, metallic=0.55, roughness=0.3),  # 0 bright fuselage spine
        pal(12, metallic=0.5, roughness=0.35),  # 1 hammerhead bar
        pal(9, metallic=0.5, roughness=0.4),  # 2 wings (the dark grooves between spine and pods) and nozzle
        pal(14, metallic=0.55, roughness=0.3),  # 3 side pods
        pal(122, emission_strength=4.0),  # 4 engine glow band
                pal(15, metallic=0.6, roughness=0.25),  # 5 nose highlight
    ]
    SPINE, BAR, WING, POD, GLOW, NOSE = range(6)
    cx = lib.ex(AXIS, S)
    bm = bmesh.new()

    # Fuselage down the centre column: (row, half width px, half height px).
    body = [(0.95, 0.0, 0.0), (1.2, 1.0, 0.8), (2.0, 1.45, 1.15), (3.2, 1.45, 1.15), (4.1, 1.25, 1.0),
            (4.7, 1.3, 1.1), (5.6, 1.05, 1.3), (8.0, 1.05, 1.3), (9.0, 1.3, 1.15), (9.7, 1.35, 1.05)]
    start = len(bm.verts)
    common.loft(bm, [(row(r), w / 12, h / 12, 0.0) for r, w, h in body], sides=10, mat_index=SPINE)
    lib.move(bm, start, dx=cx)
    # Glowing band (row 10) and the grey nozzle under it (row 11).
    start = len(bm.verts)
    common.loft(bm, [(row(9.55), 1.5 / 12, 1.1 / 12, 0.0), (row(10.5), 1.5 / 12, 1.1 / 12, 0.0)],
                sides=10, mat_index=GLOW)
    common.loft(bm, [(row(10.45), 1.45 / 12, 1.05 / 12, 0.0), (row(11.2), 1.4 / 12, 0.95 / 12, 0.0),
                     (row(11.95), 0.9 / 12, 0.6 / 12, 0.0)], sides=10, mat_index=WING)
    lib.move(bm, start, dx=cx)
    # Bright nose cap at the top of the spine (row 1, the 15 highlight).
    start = len(bm.verts)
    common.loft(bm, [(row(1.6), 0.6 / 12, 0.5 / 12, 0.08), (row(1.2), 0.45 / 12, 0.4 / 12, 0.08),
                     (row(0.95), 0.0, 0.0, 0.07)], sides=8, mat_index=NOSE)
    lib.move(bm, start, dx=cx)

    # Hammerhead bar across rows 1-3 (columns 2-8, row 3 columns 3-7).
    bar = lib.mirror_outline([(2, 1.0), (2, 3.0), (3, 3.0), (3, 3.95)], AXIS, S)
    lib.bevel_prism(bm, bar, -0.05, 0.065, 0.025, mat_index=BAR, bottom_bevel=0.015)

    # Side wings behind the neck (rows 5-9) and the rounded bright pods on them.
    wing = lib.mirror_outline([(3.2, 5.0), (2.0, 6.1), (2.0, 9.0), (3.0, 9.7), (4.0, 10.0)], AXIS, S)
    lib.bevel_prism(bm, wing, -0.06, 0.04, 0.02, mat_index=WING, bottom_bevel=0.015)
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(row(4.9), 0.0, 0.0, 0.03), (row(5.5), 0.75 / 12, 0.6 / 12, 0.035),
                         (row(7.6), 1.0 / 12, 0.8 / 12, 0.035), (row(8.7), 0.7 / 12, 0.55 / 12, 0.03),
                         (row(9.2), 0.0, 0.0, 0.02)], sides=8, mat_index=POD)
        lib.move(bm, start, dx=cx + side * 2.5 / 12)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
