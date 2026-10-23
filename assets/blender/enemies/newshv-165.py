"""Green beetle with a blue gem (newshv.shp frame 165): a 3D version of its sprite.

Seen in episode 2 (level 17). An organic green craft flying down the screen: two curled horns
sweep out and down on either side of a rounded upper pod that carries a brown, cross-shaped bud;
below it a broad green shell holds a big glossy blue gem, with blue claws curling round the
shell's lower edge. The model is built from those parts, rounded, and the green and blue faces
take the shade of the sprite pixels under them. One frame.

Run: blender --background --python assets/blender/enemies/newshv-165.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b054 as lib  # noqa: E402

NAME = "newshv-165"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
P = lib.P


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(35, metallic=0.0, roughness=0.7),  # 0 dark green creases and underside
        pal(37, metallic=0.05, roughness=0.6),  # 1 green shell
        pal(39, metallic=0.05, roughness=0.5),  # 2 mid green
        pal(42, metallic=0.1, roughness=0.45),  # 3 pale green highlights
        pal(18, metallic=0.2, roughness=0.6),  # 4 dark brown
        pal(20, metallic=0.25, roughness=0.5),  # 5 brown bud
        pal(25, metallic=0.3, roughness=0.4),  # 6 pale brown tip
        pal(146, metallic=0.3, roughness=0.25, emission_strength=1.0),  # 7 deep blue
        pal(149, metallic=0.4, roughness=0.2, emission_strength=2.0),  # 8 blue gem
        pal(154, metallic=0.4, roughness=0.15, emission_strength=3.0),  # 9 gem highlight
    ]
    DARK, GREEN, MID, PALE, BROWN_D, BROWN, BROWN_L, BLUE_D, BLUE, BLUE_L = range(10)
    pixels = sprite["frames"][0]["pixels"]
    green = lib.ramp([(34, 36, DARK), (37, 38, GREEN), (39, 40, MID), (41, 43, PALE)])
    brown = lib.ramp([(17, 18, BROWN_D), (19, 20, BROWN), (22, 25, BROWN_L)])
    blue = lib.ramp([(144, 146, BLUE_D), (147, 150, BLUE), (151, 156, BLUE_L)])
    bm = bmesh.new()

    # Curled horns (columns 1-6, rows 1-14), mirrored: a flattened tube from the tip at the top,
    # bulging outward, down to the foot beside the lower shell.
    start = len(bm.faces)
    path = [(5.8, 0.8), (5.2, 2.2), (4.3, 3.8), (3.5, 5.8), (3.3, 8.0), (3.1, 10.0), (2.8, 12.0),
            (3.0, 13.6), (3.2, 14.7)]
    half = [0.0, 1.3, 2.0, 2.5, 2.9, 2.9, 2.5, 1.9, 0.0]
    zs = [0.04, 0.05, 0.06, 0.07, 0.07, 0.06, 0.05, 0.04, 0.03]
    lib.tube(bm, [P(c, r, z) for (c, r), z in zip(path, zs)], [h / 12 * 0.75 for h in half],
             widths=[h / 12 for h in half], sides=10, mat_index=GREEN)
    # The horn's root, joining it to the pod (rows 6-10, columns 4-8).
    lib.ellipsoid(bm, P(6.0, 8.2, 0.03), (2.6 / 12, 2.6 / 12, 0.11), segments=10, rings=6, mat_index=GREEN)
    face_mark = len(bm.faces)
    lib.mirror_x(bm, start, face_mark)

    # Upper pod (columns 7-16, rows 2-14) with two little bumps on its top edge.
    lib.ellipsoid(bm, P(11.5, 8.3, 0.0), (5.0 / 12, 6.4 / 12, 0.2), segments=16, rings=10, mat_index=GREEN,
                  flat_bottom=0.6)
    for c in (9.6, 13.4):
        lib.ellipsoid(bm, P(c, 2.6, 0.04), (1.3 / 12, 1.2 / 12, 0.07), segments=8, rings=5, mat_index=GREEN)
    lib.paint(bm, lib.faces_from(bm, start), pixels, green, under_slot=DARK)

    # Brown bud on the pod: a diamond of bulb (rows 7-10) with a stalk up to row 4.
    start = len(bm.faces)
    lib.ellipsoid(bm, P(11.5, 8.7, 0.16), (3.3 / 12, 2.7 / 12, 0.08), segments=12, rings=8, mat_index=BROWN)
    lib.tube(bm, [P(11.5, 3.6, 0.17), P(11.5, 5.5, 0.2), P(11.5, 7.2, 0.21)], [0.0, 1.0 / 12, 1.2 / 12],
             sides=8, mat_index=BROWN)
    lib.paint(bm, lib.faces_from(bm, start), pixels, brown, average=False)
    lib.ellipsoid(bm, P(11.0, 9.0, 0.235), (0.9 / 12, 0.9 / 12, 0.02), segments=8, rings=4, mat_index=BROWN_L)

    # Lower shell (columns 4-19, rows 14-26).
    start = len(bm.faces)
    lib.ellipsoid(bm, P(11.5, 20.1, 0.0), (8.0 / 12, 6.4 / 12, 0.18), segments=18, rings=10, mat_index=GREEN,
                  flat_bottom=0.6)
    lib.paint(bm, lib.faces_from(bm, start), pixels, green, under_slot=DARK)

    # The blue gem (columns 8-15, rows 14-21): a big glossy dome set into the shell.
    start = len(bm.faces)
    lib.ellipsoid(bm, P(11.5, 17.6, 0.11), (3.9 / 12, 4.0 / 12, 0.12), segments=16, rings=8, mat_index=BLUE)
    lib.paint(bm, lib.faces_from(bm, start), pixels, blue)
    lib.ellipsoid(bm, P(10.2, 18.4, 0.2), (0.9 / 12, 1.4 / 12, 0.03), segments=8, rings=4, mat_index=BLUE_L)

    # Blue claws curling round the shell's lower edge, and the blue spots at its shoulders.
    start = len(bm.faces)
    claw = [(5.9, 21.0, 0.05), (6.4, 22.6, 0.06), (7.3, 23.8, 0.06), (8.5, 24.8, 0.05), (9.4, 25.3, 0.03)]
    lib.tube(bm, [P(*p) for p in claw], [0.0, 0.8 / 12, 0.8 / 12, 0.7 / 12, 0.0], sides=6, mat_index=BLUE_D,
             widths=[0.0, 1.0 / 12, 1.1 / 12, 0.9 / 12, 0.0])
    for c, r in ((6.0, 16.0), (6.0, 21.0)):
        lib.ellipsoid(bm, P(c, r, 0.07), (0.7 / 12, 0.7 / 12, 0.04), segments=6, rings=4, mat_index=BLUE_D)
    lib.mirror_x(bm, start)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
