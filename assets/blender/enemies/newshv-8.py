"""Red-lamp turret (newshv.shp frame 8): a 3D version of its sprite.

Seen in episode 2 (level 2.17). A ground emplacement: a wide dark grey base with two feet at the
front, a bright grey rounded block standing in the middle, a glowing red dome on each side with a
hot yellow spot, and two small red eyes in the front panel below the block.

Run: blender --background --python assets/blender/enemies/newshv-8.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b081 as lib  # noqa: E402

NAME = "newshv-8"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def poly(points):
    return [(lib.ex(c), lib.ey(r)) for c, r in points]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(103, metallic=0.5, roughness=0.45),  # 0 base top
        pal(105, metallic=0.5, roughness=0.4),  # 1 base walls and bevel
        pal(109, metallic=0.6, roughness=0.3),  # 2 bright block
        pal(101, metallic=0.4, roughness=0.55),  # 3 block's dark sides
        pal(118, metallic=0.2, roughness=0.3, emission_strength=2.0),  # 4 red domes
        pal(122, emission_strength=4.0),  # 5 hot spots
        pal(115, emission_strength=3.0),  # 6 red eyes
        pal(107, metallic=0.55, roughness=0.35),  # 7 front panel
        pal(113, metallic=0.3, roughness=0.5),  # 8 dome rims
    ]
    TOP, WALL, BLOCK, SIDE, DOME, HOT, EYE, PANEL, RIM = range(9)
    bm = bmesh.new()

    # Base (columns 2-21, rows 11-19) with two feet reaching forward at the corners.
    base = poly([(2, 11), (22, 11), (22, 20), (16, 20), (15, 19), (15, 18), (9, 18), (9, 19),
                 (8, 20), (2, 20)])
    lib.bevel_prism(bm, base, 0.0, 0.17, 1.2 * U, 0.06, mat_index=WALL, top_mat=TOP)
    # Raised front panel between the feet with the eyes (columns 7-16, rows 14-17).
    lib.bevel_prism(bm, poly([(6.5, 13.6), (17.5, 13.6), (17.5, 17.6), (6.5, 17.6)]), 0.1, 0.22,
                    0.8 * U, 0.04, mat_index=WALL, top_mat=PANEL)
    for c in (9, 12):
        lib.box(bm, lib.ex(c + 0.1), lib.ey(15.95), lib.ex(c + 0.9), lib.ey(15.05), 0.18, 0.25, EYE)
    for c in (8, 13):
        lib.box(bm, lib.ex(c + 0.1), lib.ey(15.95), lib.ex(c + 0.9), lib.ey(15.05), 0.18, 0.235, SIDE)

    # The bright block (columns 8-15, rows 6-13): rounded on top, sloping down at the front.
    f0 = len(bm.faces)
    s = len(bm.verts)
    common.loft(bm, [(lib.ey(5.8), 3.0 * U, 0.17, 0.27), (lib.ey(6.3), 3.9 * U, 0.24, 0.24),
                     (lib.ey(10.6), 3.9 * U, 0.24, 0.24), (lib.ey(12.6), 3.8 * U, 0.17, 0.2),
                     (lib.ey(13.9), 3.4 * U, 0.1, 0.17)], sides=12, mat_index=BLOCK)
    lib.move(bm, s, dx=lib.ex(12))
    # Darker side walls of the block (the dark columns 8 and 15).
    for c in (8.2, 15.0):
        lib.box(bm, lib.ex(c), lib.ey(13.6), lib.ex(c + 0.8), lib.ey(6.4), 0.1, 0.3, SIDE)

    # Glowing red domes (columns 2-7 and 16-21, rows 8-13), each with a hot spot on its outer top.
    for cx, hot in ((5.0, 3.9), (19.0, 20.1)):
        lib.dome(bm, (lib.ex(cx), lib.ey(11.0), 0.12), (3.4 * U, 3.2 * U, 0.03), sides=16, rings=1,
                 mat_index=RIM)
        lib.dome(bm, (lib.ex(cx), lib.ey(11.0), 0.14), (3.0 * U, 2.9 * U, 0.24), sides=16, rings=4,
                 mat_index=DOME)
        lib.ellipsoid(bm, (lib.ex(hot), lib.ey(10.5), 0.35), (1.2 * U, 1.1 * U, 0.05), sides=10,
                      rings=5, mat_index=HOT)
    lib.set_smooth(bm, f0, True)
    return lib.mesh_object_mixed(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
