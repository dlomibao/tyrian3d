"""Blue armoured gunship (newshv.shp frame 48): a 3D version of its sprite.

Seen in episode 2 (levels 17 and 19). A heavy steel-blue craft flying down the screen: a raised
spine with a dark slot runs up its top, flanked by two big rounded shoulder plates; a grey gun bar
crosses its middle with a red eye at the centre; rounded side pods hang below the shoulders with
grey claws under them, and the ridged lower hull tapers to a short tail. Blue and grey faces take
the shade of the sprite pixels under them. One frame.

Run: blender --background --python assets/blender/enemies/newshv-48.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b054 as lib  # noqa: E402

NAME = "newshv-48"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
P = lib.P
U = 1 / 12  # one sprite pixel


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(52, metallic=0.4, roughness=0.5),  # 0 dark steel (seams, underside)
        pal(55, metallic=0.45, roughness=0.45),  # 1 steel blue
        pal(58, metallic=0.5, roughness=0.4),  # 2 light steel
        pal(61, metallic=0.5, roughness=0.3),  # 3 highlights
        pal(50, metallic=0.2, roughness=0.6),  # 4 dark slot
        pal(3, metallic=0.6, roughness=0.45),  # 5 dark grey
        pal(7, metallic=0.65, roughness=0.4),  # 6 grey
        pal(10, metallic=0.7, roughness=0.3),  # 7 light grey
        pal(115, metallic=0.2, roughness=0.4, emission_strength=2.0),  # 8 red eye rim
        pal(119, metallic=0.1, roughness=0.3, emission_strength=4.0),  # 9 red eye
    ]
    DARK, STEEL, LIGHT, HIGH, SLOT, GREY_D, GREY, GREY_L, RED_D, RED = range(10)
    pixels = sprite["frames"][0]["pixels"]
    blue = lib.ramp([(50, 53, DARK), (54, 56, STEEL), (57, 59, LIGHT), (60, 62, HIGH)])
    grey = lib.ramp([(2, 4, GREY_D), (5, 7, GREY), (8, 12, GREY_L)])
    bm = bmesh.new()

    # Lower hull (columns 6-17, rows 13-26) tapering to the tail stub (columns 10-13, row 27).
    start = len(bm.faces)
    hull = [(12.6, 3.6, 0.10), (13.6, 5.6, 0.14), (15.0, 6.0, 0.15), (20.0, 6.0, 0.15), (24.5, 5.9, 0.14),
            (25.8, 5.2, 0.12), (26.6, 3.4, 0.08), (27.4, 2.0, 0.05), (27.8, 0.0, 0.0)]
    common.loft(bm, [(lib.row(r), w * U, h, -0.02) for r, w, h in hull], sides=12, mat_index=STEEL)
    # Ridges along the upper hull (columns 10 and 13) and rails down its lower edges (7 and 16).
    for c in (10, 13):
        lib.tube(bm, [P(c, 12.8, 0.09), P(c, 14.0, 0.12), P(c, 17.6, 0.12), P(c, 18.2, 0.1)],
                 [0.0, 0.5 * U, 0.5 * U, 0.0], widths=[0.0, 0.6 * U, 0.6 * U, 0.0], sides=6, mat_index=LIGHT)
    for c in (7, 16):
        lib.tube(bm, [P(c, 19.8, 0.08), P(c, 20.6, 0.1), P(c, 25.0, 0.09), P(c, 25.8, 0.06)],
                 [0.0, 0.5 * U, 0.5 * U, 0.0], widths=[0.0, 0.6 * U, 0.6 * U, 0.0], sides=6, mat_index=LIGHT)

    # Raised spine up the top (columns 9-14, rows 0-9).
    spine = lib.edge_outline([(9, 0), (15, 0), (15, 10), (9, 10)], rounds=1)
    lib.cushion(bm, spine, 0.02, 0.17, 0.08, 0.9 * U, steps=3, mat_index=STEEL, side=0.04)

    # Shoulder plates (columns 1-8, rows 1-9), mirrored.
    shoulder_start = len(bm.faces)
    shoulder = lib.edge_outline([(4, 1), (9, 1), (9, 10), (1, 10), (1, 4), (2, 3), (3, 2)], rounds=2)
    lib.cushion(bm, shoulder, 0.0, 0.11, 0.07, 1.4 * U, steps=3, mat_index=STEEL, side=0.04)
    # Side pod below it (columns 1-6, rows 10-16).
    pod = [(9.3, 0.0, 0.0, 0.0), (9.6, 2.0, 0.08, 0.0), (11.0, 2.4, 0.1, 0.0), (13.5, 2.5, 0.11, 0.0),
           (14.5, 2.9, 0.11, 0.0), (15.6, 2.5, 0.1, 0.0), (16.6, 1.7, 0.07, 0.0), (17.3, 0.0, 0.0, 0.0)]
    s = len(bm.verts)
    common.loft(bm, [(lib.row(r), w * U, h, z) for r, w, h, z in pod], sides=10, mat_index=STEEL)
    common.shift_x(bm, s, lib.px(3.6))
    # The shoulder's light inner ridge (column 7, rows 2-8) and the lit top of its outer lobe.
    lib.tube(bm, [P(7, 1.6, 0.13), P(7, 2.6, 0.155), P(7, 7.0, 0.15), P(7, 8.2, 0.12)],
             [0.0, 0.45 * U, 0.45 * U, 0.0], widths=[0.0, 0.6 * U, 0.6 * U, 0.0], sides=6, mat_index=HIGH)
    lib.ellipsoid(bm, P(4.0, 3.4, 0.13), (2.0 * U, 1.6 * U, 0.035), segments=10, rings=5, mat_index=HIGH)
    mirror_end = len(bm.faces)
    lib.mirror_x(bm, shoulder_start, mirror_end)
    lib.paint(bm, lib.faces_from(bm, start), pixels, blue, under_slot=DARK)

    # The dark slot down the spine (columns 11-12, rows 3-6).
    slot = lib.edge_outline([(11, 3), (13, 3), (13, 7), (11, 7)], rounds=1)
    common.slab(bm, slot, 0.02, z=0.21, mat_index=SLOT)

    # Grey claws under the side pods (columns 2-5, rows 17-22), mirrored.
    start = len(bm.faces)
    lib.tube(bm, [P(2.4, 16.6, 0.0), P(2.8, 18.2, 0.03), P(3.2, 19.8, 0.04), P(3.9, 21.2, 0.03), P(4.8, 22.4, 0.0)],
             [0.6 * U, 1.0 * U, 1.1 * U, 1.0 * U, 0.0], widths=[1.0 * U, 1.6 * U, 1.9 * U, 1.5 * U, 0.0],
             sides=8, mat_index=GREY)
    lib.paint(bm, lib.faces_from(bm, start), pixels, grey)
    lib.mirror_x(bm, start)

    # Grey gun bar across the middle (columns 6-17, rows 10-13) with the red eye at its centre.
    start = len(bm.faces)
    lib.tube(bm, [P(5.6, 11.6, 0.04), P(6.2, 11.6, 0.06), P(11.5, 11.6, 0.07), P(16.8, 11.6, 0.06),
                  P(17.4, 11.6, 0.04)],
             [1.2 * U, 1.9 * U, 2.0 * U, 1.9 * U, 1.2 * U], sides=10, flat=0.7, mat_index=GREY)
    lib.paint(bm, lib.faces_from(bm, start), pixels, grey)
    lib.ellipsoid(bm, P(11.5, 11.2, 0.15), (1.5 * U, 2.0 * U, 0.06), segments=10, rings=6, mat_index=RED_D)
    lib.ellipsoid(bm, P(11.5, 11.0, 0.18), (0.9 * U, 1.2 * U, 0.05), segments=8, rings=5, mat_index=RED)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
