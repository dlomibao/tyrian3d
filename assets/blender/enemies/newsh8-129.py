"""Carrot pod (newsh8.shp frame 129): a 3D version of its sprite.

Seen in episode 3 (level 3.19). An orange carrot flying point first down the screen, with a tuft
of green leaves on top and a round brown porthole with a glowing yellow light in its belly.

Run: blender --background --python assets/blender/enemies/newsh8-129.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b060 as L  # noqa: E402

NAME = "newsh8-129"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(122, metallic=0.05, roughness=0.55),  # 0 orange skin
        pal(119, metallic=0.05, roughness=0.6),  # 1 red-orange rings
        pal(124, metallic=0.05, roughness=0.5),  # 2 yellow-orange highlight
        pal(200, metallic=0.0, roughness=0.55),  # 3 green leaves
        pal(196, metallic=0.0, roughness=0.6),  # 4 dark green
        pal(203, metallic=0.0, roughness=0.5),  # 5 light green
        pal(181, metallic=0.4, roughness=0.45),  # 6 brown porthole rim
        pal(176, metallic=0.2, roughness=0.6),  # 7 dark porthole socket
        pal(126, emission_strength=4.0),  # 8 porthole light
        pal(185, metallic=0.5, roughness=0.3),  # 9 light brown lens ring
    ]
    SKIN, SHADE, HIGH, LEAF, DLEAF, LLEAF, RIM, SOCKET, LIGHT, LENS = range(10)
    pixels = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    # The carrot: rounded shoulder at row 9, widest at rows 11-14, tapering to the tip at row 27.
    body = [(8.7, 0.0), (9.0, 2.6), (9.6, 3.9), (10.5, 5.0), (11.6, 5.6), (14.0, 5.6), (16.5, 5.0),
            (18.5, 4.2), (20.5, 3.6), (22.5, 2.6), (24.5, 1.6), (26.0, 0.9), (27.4, 0.0)]
    skin = L.loft_y(bm, 12.3, [(r, w, w * L.PX * 0.8, 0.0) for r, w in body], sides=14, mat=SKIN)
    # The sprite's yellow glow down the belly, under the porthole (rows 18-24).
    L.loft_y(bm, 12.0, [(17.5, 0.0, 0.0, 0.18), (18.5, 2.4, 0.16, 0.16), (21.0, 2.0, 0.15, 0.12),
                        (23.5, 1.2, 0.1, 0.07), (25.0, 0.0, 0.0, 0.04)], sides=10, mat=HIGH)
    # A few shallow growth rings across it.
    for r, w in ((12.5, 5.65), (17.5, 4.65), (21.5, 3.15)):
        L.loft_y(bm, 12.3, [(r - 0.25, w, w * L.PX * 0.82, 0.0), (r + 0.25, w, w * L.PX * 0.82, 0.0)],
                 sides=14, mat=SHADE)

    # Porthole (rows 14-18, columns 10-15): a brown rim round a glowing light.
    z = 0.37
    L.ellipsoid(bm, L.P(12.6, 16.2, z - 0.06), (3.0 * L.PX, 2.8 * L.PX, 0.08), segments=14, rings=7, mat=RIM)
    L.ellipsoid(bm, L.P(12.6, 16.2, z - 0.04), (2.1 * L.PX, 2.0 * L.PX, 0.075), segments=12, rings=6, mat=SOCKET)
    L.ellipsoid(bm, L.P(12.4, 16.2, z - 0.01), (1.3 * L.PX, 1.3 * L.PX, 0.06), segments=10, rings=5, mat=LENS)
    L.ellipsoid(bm, L.P(12.3, 16.1, z + 0.02), (0.75 * L.PX, 0.75 * L.PX, 0.04), segments=8, rings=4, mat=LIGHT)

    # Leaves (rows 0-8): a tall middle frond and one to each side, from the top of the carrot.
    leaves = []
    leaves += L.ptube(bm, [(12.0, 8.6, 0.02, 1.4), (12.0, 6.5, 0.06, 2.0), (12.3, 3.5, 0.08, 1.6),
                           (12.2, 1.6, 0.08, 1.0), (11.8, 0.2, 0.07, 0.0)], sides=8, mat=LEAF, flat=0.45)
    leaves += L.ptube(bm, [(11.2, 7.8, 0.02, 1.2), (9.5, 5.6, 0.05, 1.5), (7.6, 3.6, 0.06, 1.2),
                           (6.6, 1.8, 0.05, 0.8), (6.4, 0.9, 0.05, 0.0)], sides=8, mat=LEAF, flat=0.45)
    leaves += L.ptube(bm, [(12.8, 7.6, 0.02, 1.2), (14.6, 5.2, 0.05, 1.5), (16.0, 4.2, 0.06, 1.1),
                           (17.3, 3.6, 0.05, 0.0)], sides=8, mat=LEAF, flat=0.45)
    L.paint(bm, leaves, pixels, lambda v, s: LLEAF if v >= 201.5 else (LEAF if v >= 196.5 else DLEAF))

    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = L.preview_args()
    if out:
        L.preview([obj], ROOT, NAME, sprite["frames"][0]["image"], out)


if __name__ == "__main__":
    main()
