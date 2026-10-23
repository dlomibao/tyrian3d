"""Old key (tyrian.shp#10 frame 243): a 3D version of its sprite.

Seen in episode 1 (level section 31). The sprite draws a bronze skeleton key lying on the ground,
bit up the screen: a round shaft (columns 12-14) with a dark collar near the top, a bit of two
arms reaching left with small hooked prongs (rows 4-5 and 9-10), and a broad oval bow at the
bottom with two dark holes. In 3D it lies flat: a slightly flattened round shaft, the arms and
prongs as low blocks, and the bow as a low dome. The near-black pixels right of and below it
(indices 160 and 161) are its drop shadow and the dark ring round it is outline; neither is
modelled.

Run: blender --background --python assets/blender/enemies/tyrian10-243.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b106 as lib  # noqa: E402
from lib_b106 import common, ex, ey, px  # noqa: E402

NAME = "tyrian10-243"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(25, metallic=0.75, roughness=0.3),  # 0 bronze shaft
        pal(26, metallic=0.75, roughness=0.3),  # 1 bright bit arms
        pal(23, metallic=0.75, roughness=0.35),  # 2 bow
        pal(19, metallic=0.6, roughness=0.45),  # 3 dark collar
        pal(16, metallic=0.2, roughness=0.8),  # 4 holes in the bow
        pal(28, metallic=0.8, roughness=0.25),  # 5 highlight ridge
    ]
    SHAFT, ARM, BOW, COLLAR, HOLE, HI = range(6)

    # Smooth parts: the shaft, collar and bow.
    bm = bmesh.new()
    sx = px(13)  # shaft centre line (columns 12-14)
    r = 1.5 / 12
    flat = 0.72
    zc = r * flat
    lib.polyline_tube(bm, [(sx, ey(3.95), zc), (sx, ey(12), zc), (sx, ey(17.5), zc)], r, sides=10,
                      mat_index=SHAFT, flat=flat)
    # The dark collar at row 7 and a thin highlight ridge along the shaft's top.
    lib.polyline_tube(bm, [(sx, ey(6.75), zc), (sx, ey(8.0), zc)], r * 1.12, sides=10, mat_index=COLLAR, flat=flat)
    lib.polyline_tube(bm, [(sx, ey(8.3), zc + r * flat * 0.9), (sx, ey(15.6), zc + r * flat * 0.9)], 0.3 / 12,
                      sides=6, mat_index=HI)

    # The bow: a low oval dome, columns 6-17 and rows 16-22.
    lib.spheroid(bm, (ex(12), ey(19.6), 0.0), (6.0 / 12, 3.6 / 12, 0.2), sides=20, rings=5,
                 mat_index=BOW, z_cut=0.0)
    smooth = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # Flat parts: the bit's arms and prongs, and the holes in the bow.
    bm = bmesh.new()
    h = 0.15
    lib.bevel_prism(bm, [(ex(6), ey(5.3)), (ex(13), ey(5.3)), (ex(13), ey(3.75)), (ex(6), ey(3.75))],
                    0.0, h, 0.25 / 12, mat_index=ARM)
    lib.bevel_prism(bm, [(ex(6.9), ey(6.1)), (ex(8.1), ey(6.1)), (ex(8.1), ey(4.9)), (ex(6.9), ey(4.9))],
                    0.0, h * 0.9, 0.2 / 12, mat_index=ARM)
    lib.bevel_prism(bm, [(ex(8), ey(11.3)), (ex(13), ey(11.3)), (ex(13), ey(9.7)), (ex(8), ey(9.7))],
                    0.0, h, 0.25 / 12, mat_index=ARM)
    lib.bevel_prism(bm, [(ex(7.9), ey(10.0)), (ex(9.1), ey(10.0)), (ex(9.1), ey(8.8)), (ex(7.9), ey(8.8))],
                    0.0, h * 0.9, 0.2 / 12, mat_index=ARM)
    # Holes: dark discs set into the dome's top (left one larger, right one small).
    for cx, cy, rx, ry in ((ex(9.6), ey(20.9), 1.5, 1.0), (ex(14.9), ey(20.6), 1.0, 0.7)):
        lib.prism(bm, lib.ellipse(cx, cy, rx / 12, ry / 12, n=10), 0.08, 0.188, mat_index=HOLE)
    flat_obj = common.mesh_object(f"{NAME}_flat", bm, mats, coll, smooth=False)

    return [(NAME, [smooth, flat_obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
