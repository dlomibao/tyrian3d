"""Red-eyed beetle pod (newshv.shp frames 197, 199, 201): a 3D version of its sprite.

Seen in episode 2 (level 17). A steel-blue craft flying down the screen with a big glowing red eye
in a blue housing at its front, curved purple horns round the housing and beside the body, green
pipes down its sides, a pale chest dome and a two-lobed rear shell with two red engine vents. The
three frames only brighten the eye and the vents, so one model covers them all; the eye, chest,
shell and horns take the shade of the sprite pixels under them.

Run: blender --background --python assets/blender/enemies/newshv-197.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b054 as lib  # noqa: E402

NAME = "newshv-197"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
P = lib.P
U = 1 / 12  # one sprite pixel
C = 12.0  # the sprite's mirror axis (pixel column)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(53, metallic=0.4, roughness=0.5),  # 0 dark steel
        pal(57, metallic=0.45, roughness=0.45),  # 1 steel blue
        pal(59, metallic=0.5, roughness=0.4),  # 2 light steel
        pal(62, metallic=0.5, roughness=0.3),  # 3 pale highlights
        pal(85, metallic=0.3, roughness=0.5),  # 4 dark purple horn
        pal(88, metallic=0.35, roughness=0.45),  # 5 purple horn
        pal(92, metallic=0.4, roughness=0.35),  # 6 pale horn
        pal(40, metallic=0.2, roughness=0.5),  # 7 green pipes
        pal(113, metallic=0.2, roughness=0.4, emission_strength=1.5),  # 8 dark red
        pal(116, metallic=0.2, roughness=0.35, emission_strength=2.5),  # 9 red eye
        pal(121, metallic=0.1, roughness=0.3, emission_strength=4.0),  # 10 bright glow
        pal(82, metallic=0.3, roughness=0.3),  # 11 pupil
    ]
    DARK, STEEL, LIGHT, PALE, PUR_D, PUR, PUR_L, PIPE, RED_D, RED, GLOW, PUPIL = range(12)
    pixels = sprite["frames"][0]["pixels"]
    blue = lib.ramp([(51, 54, DARK), (55, 57, STEEL), (58, 60, LIGHT), (61, 63, PALE)])
    purple = lib.ramp([(83, 86, PUR_D), (87, 90, PUR), (91, 95, PUR_L)])
    red = lib.ramp([(82, 82, PUPIL), (112, 114, RED_D), (115, 117, RED), (118, 127, GLOW)])
    bm = bmesh.new()

    # Rear shell (columns 5-19, rows 16-24), the chest (rows 10-15) and the eye housing (rows 2-11).
    start = len(bm.faces)
    shell = lib.edge_outline([(5, 15.6), (20, 15.6), (20, 20.5), (19, 22.5), (18, 23.8), (16, 25), (9, 25),
                              (7, 23.8), (6, 22.5), (5, 20.5)], rounds=2)
    lib.cushion(bm, shell, 0.0, 0.12, 0.07, 3.0 * U, steps=3, mat_index=LIGHT, side=0.04)
    lib.ellipsoid(bm, P(C, 12.8, -0.02), (6.3 * U, 3.6 * U, 0.15), segments=14, rings=8, mat_index=STEEL,
                  flat_bottom=0.6)
    lib.ellipsoid(bm, P(C, 6.5, -0.02), (6.6 * U, 4.9 * U, 0.17), segments=16, rings=10, mat_index=STEEL,
                  flat_bottom=0.6)
    # The pale chest dome (columns 10-13, rows 12-14).
    lib.ellipsoid(bm, P(C, 13.2, 0.08), (3.0 * U, 2.2 * U, 0.08), segments=12, rings=6, mat_index=PALE)
    lib.paint(bm, lib.faces_from(bm, start), pixels, blue, under_slot=DARK)
    # The groove between the shell's two lobes (column 12, rows 17-24).
    lib.tube(bm, [P(C, 15.8, 0.12), P(C, 17.0, 0.162), P(C, 21.0, 0.162), P(C, 23.4, 0.15), P(C, 24.6, 0.08)],
             [0.0, 0.25 * U, 0.25 * U, 0.25 * U, 0.0], widths=[0.0, 0.5 * U, 0.5 * U, 0.5 * U, 0.0],
             sides=6, mat_index=DARK)

    # The red eye (columns 8-16, rows 3-10), a big glowing dome with its dark pupil.
    start = len(bm.faces)
    lib.ellipsoid(bm, P(C, 6.6, 0.05), (4.6 * U, 4.1 * U, 0.19), segments=16, rings=9, mat_index=RED)
    lib.paint(bm, lib.faces_from(bm, start), pixels, red, average=False)
    # Its bright glint (columns 10-11, rows 6-8).
    lib.ellipsoid(bm, P(10.6, 7.0, 0.215), (1.1 * U, 1.6 * U, 0.03), segments=8, rings=4, mat_index=GLOW)

    # Engine vents on the shell (columns 9-10 and 14-15, rows 20-23), mirrored.
    start = len(bm.faces)
    lib.ellipsoid(bm, P(9.6, 21.6, 0.11), (1.0 * U, 1.9 * U, 0.05), segments=10, rings=6, mat_index=RED)
    lib.ellipsoid(bm, P(9.7, 20.6, 0.14), (0.6 * U, 0.8 * U, 0.03), segments=8, rings=4, mat_index=GLOW)

    # Green pipes down the sides (columns 6-7, rows 8-15).
    lib.tube(bm, [P(6.0, 7.8, 0.06), P(6.4, 9.0, 0.08), P(7.0, 10.6, 0.08), P(7.0, 13.5, 0.07), P(7.0, 15.4, 0.04)],
             [0.0, 0.6 * U, 0.6 * U, 0.6 * U, 0.0], widths=[0.0, 0.6 * U, 0.6 * U, 0.6 * U, 0.0],
             sides=6, mat_index=PIPE)

    # Purple horns: one curling round the housing (rows 2-8), one beside the body (rows 13-19).
    horn_start = len(bm.faces)
    lib.tube(bm, [P(8.4, 1.8, 0.04), P(6.8, 2.4, 0.06), P(5.1, 3.6, 0.07), P(4.0, 5.2, 0.07), P(3.8, 6.6, 0.06),
                  P(4.3, 8.3, 0.03)],
             [0.0, 0.8 * U, 1.0 * U, 1.1 * U, 0.9 * U, 0.0], widths=[0.0, 1.0 * U, 1.3 * U, 1.4 * U, 1.1 * U, 0.0],
             sides=8, mat_index=PUR)
    lib.tube(bm, [P(5.0, 12.8, 0.02), P(4.2, 13.8, 0.05), P(3.6, 15.4, 0.06), P(3.5, 17.0, 0.06), P(3.7, 18.4, 0.04),
                  P(4.2, 19.4, 0.02)],
             [0.0, 0.8 * U, 1.0 * U, 1.0 * U, 0.8 * U, 0.0], widths=[0.0, 1.1 * U, 1.4 * U, 1.3 * U, 1.0 * U, 0.0],
             sides=8, mat_index=PUR)
    lib.paint(bm, lib.faces_from(bm, horn_start), pixels, purple)

    # Mirror the vents, pipes and horns about column 12.
    s = len(bm.verts)
    lib.mirror_x(bm, start, len(bm.faces))
    bm.verts.ensure_lookup_table()
    for v in bm.verts[s:]:
        v.co.x += 2 * lib.px(C)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
