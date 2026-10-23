"""Tan fighter (newsh5.shp frame 49): a 3D version of its sprite.

Seen in episode 4 (level 4.47). A sand-coloured plane, nose up the screen: a slim fuselage with
a light spine and a bubble canopy behind the wings, two forward-swept canards at the nose, straight
main wings carrying a grey gun pod at each tip, and a small swept tail wing above a tapering tail.
One frame.

Run: blender --background --python assets/blender/enemies/newsh5-49.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402
from lib_b030 import PX, ex, ey, px, row  # noqa: E402

NAME = "newsh5-49"
CX = px(12)  # the sprite is symmetric about column 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.3, roughness=0.45),  # 0 tan hull and wings
        pal(28, metallic=0.35, roughness=0.35),  # 1 light spine, leading edges
        pal(21, metallic=0.25, roughness=0.55),  # 2 shaded tail wing, fuselage sides
        pal(6, metallic=0.7, roughness=0.3),  # 3 grey gun pods
        pal(9, metallic=0.75, roughness=0.25),  # 4 pod tips
        pal(29, metallic=0.5, roughness=0.15),  # 5 canopy
    ]
    HULL, SPINE, SHADE, POD, TIP, CANOPY = range(6)
    bm = bmesh.new()

    # ---- left side, mirrored below ----
    # Forward-swept canard from the nose out to columns 5-6, row 1.
    lib.plate(bm, [(ex(5.4), ey(0.9)), (ex(8.6), ey(0.9)), (ex(11.6), ey(3.6)), (ex(11.6), ey(5.2)),
                   (ex(10.2), ey(5.2)), (ex(6.8), ey(2.6))], -0.8 * PX, 0.9 * PX, mat=HULL)
    lib.sausage(bm, [(px(6.2), row(1.3)), (px(9.6), row(3.6))], 0.6 * PX, 0.5 * PX, mat=SPINE,
                z_of=lambda x, y: 0.8 * PX)
    # Main wing (rows 7-12): straight leading edge, trailing edge sweeping in to the root.
    lib.plate(bm, [(ex(10.0), ey(6.6)), (ex(2.0), ey(6.6)), (ex(2.0), ey(9.4)), (ex(5.0), ey(10.4)),
                   (ex(7.2), ey(12.2)), (ex(10.0), ey(12.8))], -1.1 * PX, 0.9 * PX, mat=HULL)
    lib.sausage(bm, [(px(2.6), row(7.1)), (px(9.4), row(7.1))], 0.7 * PX, 0.6 * PX, mat=SPINE,
                z_of=lambda x, y: 0.8 * PX)
    # Grey gun pod at the wing tip (column 3, rows 4-11).
    start = len(bm.verts)
    before = len(bm.faces)
    common.loft(bm, [(ey(4.4), 0.0, 0.0, 0.0), (ey(4.8), 0.6 * PX, 0.6 * PX, 0.0), (ey(5.6), 0.95 * PX, 0.95 * PX, 0.0),
                     (ey(11.4), 0.95 * PX, 0.95 * PX, 0.0), (ey(12.0), 0.0, 0.0, 0.0)], sides=8)
    common.shift_x(bm, start, px(3))
    lib.tag_faces(bm, before, POD, True)
    lib.ellipsoid(bm, px(3), row(5.2), 0.0, 0.8 * PX, 0.8 * PX, 0.8 * PX, mat=TIP, segments=8, rings=4)
    # Swept tail wing (rows 17-19).
    lib.plate(bm, [(ex(10.4), ey(16.8)), (ex(6.0), ey(17.2)), (ex(5.4), ey(18.4)), (ex(8.0), ey(20.0)),
                   (ex(10.4), ey(20.2))], -0.6 * PX, 0.6 * PX, mat=SHADE)
    lib.mirror_x(bm, axis=CX)

    # ---- centre ----
    def loft(sections, mat, sides=12):
        start = len(bm.verts)
        before = len(bm.faces)
        common.loft(bm, [(row(r), w * PX, h * PX, z * PX) for r, w, h, z in sections], sides=sides)
        common.shift_x(bm, start, CX)
        lib.tag_faces(bm, before, mat, True)

    loft([(0.5, 0.0, 0.0, 0.3), (1.0, 0.8, 0.7, 0.3), (3.0, 1.5, 1.3, 0.3), (5.0, 2.4, 1.9, 0.2),
          (6.6, 3.2, 2.3, 0.0), (12.0, 3.2, 2.3, 0.0), (13.2, 2.5, 2.0, 0.0), (16.6, 2.4, 1.8, 0.0),
          (19.6, 2.3, 1.6, 0.0), (21.2, 1.8, 1.3, 0.0), (23.6, 1.3, 0.9, 0.0), (25.4, 0.6, 0.4, 0.0),
          (26.0, 0.0, 0.0, 0.0)], HULL)
    # Light spine down the nose and over the wings.
    lib.sausage(bm, [(px(12), row(1.6)), (px(12), row(4.6)), (px(11.5), row(6.6)), (px(11.5), row(12.4))],
                [0.7 * PX, 0.9 * PX, 1.2 * PX, 1.2 * PX], 0.6 * PX, mat=SPINE,
                z_of=lambda x, y: min(2.0, 0.9 + 0.25 * (13.5 - y * 12 - 0.5)) * PX)
    # Darker flanks behind the wings and canopy (rows 13-16).
    lib.ellipsoid(bm, px(12), row(14.6), 1.4 * PX, 1.7 * PX, 2.2 * PX, 1.2 * PX, mat=CANOPY, segments=12, rings=6)
    lib.sausage(bm, [(px(12), row(20.4)), (px(12), row(24.0))], [0.8 * PX, 0.4 * PX], 0.4 * PX, mat=SPINE,
                z_of=lambda x, y: max(0.4, 1.4 - 0.2 * ((13.5 - y * 12) - 20.4)) * PX)

    return lib.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)
