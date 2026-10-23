"""Red canister on a pole (newsh5.shp frame 168): a 3D version of its sprite.

Seen in episode 4 (level 22), where seven to nine of them hang one under the other on a long
blue-grey pole (sprite.json `assemblyLayout`), so the pole runs right through the 24x28 block and
lines up with the next link above and below. The canister is a glossy red drum with a cap on
top (a small orange lamp and a grey clamp), seams at rows 10 and 18, the pole showing through
grey slots above and below, and a blue-grey bracket and a slimmer red tank on its right side.
One frame.

Run: blender --background --python assets/blender/enemies/newsh5-168.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b051 as lib  # noqa: E402

NAME = "newsh5-168"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    g = lib.sprite_grid(sprite)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(113, metallic=0.3, roughness=0.4),  # 0 dark red seams and edges
        pal(115, metallic=0.35, roughness=0.3),  # 1 deep red
        pal(117, metallic=0.35, roughness=0.25),  # 2 red
        pal(119, metallic=0.35, roughness=0.2),  # 3 bright red
        pal(121, metallic=0.3, roughness=0.2),  # 4 orange highlight
        pal(98, metallic=0.25, roughness=0.45),  # 5 dark blue-grey
        pal(101, metallic=0.3, roughness=0.4),  # 6 blue-grey
        pal(104, metallic=0.3, roughness=0.35),  # 7 light blue-grey
        pal(106, metallic=0.35, roughness=0.3),  # 8 bright blue-grey
        pal(123, emission_strength=5.0),  # 9 orange lamp
    ]
    SEAM, RED1, RED2, RED3, RED4, B98, B101, B104, B106, LAMP = range(10)

    def slot(i):
        if 112 <= i <= 113:
            return SEAM
        if 114 <= i <= 116:
            return RED1
        if 117 <= i <= 118:
            return RED2
        if 119 <= i <= 120:
            return RED3
        if 121 <= i <= 127:
            return RED4
        if 96 <= i <= 99:
            return B98
        if 100 <= i <= 102:
            return B101
        if 103 <= i <= 105:
            return B104
        if 106 <= i <= 111:
            return B106
        return None

    bm = bmesh.new()

    # The pole, column 11, through the whole block (pixel edges -0.5 and 27.5 so links meet).
    lib.sweep(bm, g, [(11.0, -0.5, 0.0, 4.5, 0.15), (11.0, 27.5, 0.0, 4.5, 0.15)], sides=12, mat=B104,
              cap_start=True, cap_end=True)

    pole_faces = len(bm.faces)

    # The drum: cap (rows 4-9), seam, body (rows 11-17), seam, lower part (rows 19-23).
    drum = [(3.6, 4.0), (4.2, 6.2), (5.2, 7.2), (6.2, 7.6), (9.2, 7.6), (9.8, 7.2), (10.4, 7.2),
            (11.0, 7.6), (17.4, 7.6), (18.0, 7.2), (18.6, 7.2), (19.2, 7.6), (21.8, 7.5), (22.8, 6.9),
            (23.7, 5.8), (24.3, 3.5)]
    sections = []
    for r, w in drum:
        sections.append((12.0, r, 0.0, w, 0.27 * min(1.0, w / 7.6) ** 0.5))
    lib.sweep(bm, g, sections, sides=18, mat=RED2, power=0.8)

    # Blue-grey bracket on the right (columns 15-20, rows 10-14) and the grey slot at column 15.
    lib.box(bm, g, 15, 10, 20, 14, -0.12, 0.25, mat=B101)
    lib.box(bm, g, 15, 15, 15, 19, 0.1, 0.24, mat=B104)
    # The pole showing through the slots at the top (columns 10-11) and bottom (columns 10-13),
    # and the grey clamp at the top left (row 7, column 7).
    lib.box(bm, g, 10, 4, 11, 7, 0.1, 0.285, mat=B106)
    lib.box(bm, g, 10, 19, 13, 23, 0.05, 0.27, mat=B104)
    lib.plate(bm, g, [(7, 7), (10, 7), (10, 8), (8, 8), (8, 10), (7, 10)], 0.1, 0.27, mat=B104)

    lib.paint(bm, g, slot, start=pole_faces, under=SEAM, average=False)
    # Faces turned to the light read a shade brighter, like the sprite's glossy drum.
    for f in lib.faces_from(bm, pole_faces):
        if f.normal.z > 0.8 and f.material_index in (SEAM, RED1, RED2, RED3):
            f.material_index += 1

    # The orange lamp on the cap (row 6, columns 13-14).
    lib.ellipsoid(bm, (g.X(13.5), g.Y(6.4), 0.24), (1.4 * lib.PX, 1.2 * lib.PX, 0.06), segments=10, rings=5,
                  mat=LAMP)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
