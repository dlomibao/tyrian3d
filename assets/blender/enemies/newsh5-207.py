"""Brain spawn drill (newsh5.shp frame 207): a 3D version of its sprite.

Seen in episode 4 (level 4.22, the brain level). A dark red, shell-like pod pointing down the
screen: a wide round cap at the back with little side lips, a bright collar between two grooves,
a body bulging into two lobes either side of a centre groove, and a long tapering spike with a
light ridge down its middle. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-207.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402
from lib_b030 import PX, px, row  # noqa: E402

NAME = "newsh5-207"
CX = px(12)  # the sprite is symmetric about column 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(73, metallic=0.2, roughness=0.4),  # 0 cap
        pal(67, metallic=0.1, roughness=0.6),  # 1 grooves
        pal(75, metallic=0.25, roughness=0.3),  # 2 bright collar
        pal(69, metallic=0.15, roughness=0.5),  # 3 body
        pal(74, metallic=0.2, roughness=0.35),  # 4 lobes, spike ridge
        pal(70, metallic=0.15, roughness=0.45),  # 5 spike
    ]
    CAP, GROOVE, COLLAR, BODY, LOBE, SPIKE = range(6)
    bm = bmesh.new()

    def loft(sections, mat, sides=14, cx=CX):
        """sections: (row, half width px, half height px, z px)."""
        start = len(bm.verts)
        before = len(bm.faces)
        common.loft(bm, [(row(r), w * PX, h * PX, z * PX) for r, w, h, z in sections], sides=sides)
        common.shift_x(bm, start, cx)
        lib.tag_faces(bm, before, mat, True)

    # Cap at the back (rows 1-3), with a groove under it.
    loft([(0.4, 0.0, 0.0, 0.6), (0.6, 3.5, 2.0, 0.6), (1.1, 5.4, 3.2, 0.4), (2.0, 6.4, 3.8, 0.2),
          (3.0, 6.6, 3.6, 0.0), (3.4, 5.6, 3.0, -0.2)], CAP)
    loft([(3.3, 5.0, 2.4, -0.2), (4.0, 4.6, 2.5, -0.2)], GROOVE)
    # Bright collar (rows 4-5) and the groove under it (row 6).
    loft([(3.9, 4.6, 2.7, -0.2), (4.5, 5.0, 3.2, 0.0), (5.6, 5.0, 3.2, 0.0), (6.2, 4.6, 2.8, 0.0)], COLLAR)
    loft([(6.1, 4.4, 2.6, 0.0), (6.9, 4.6, 2.7, 0.0)], GROOVE)
    # Body (rows 7-16): widest at rows 7-11, then a step in.
    loft([(6.8, 5.2, 3.2, 0.0), (7.5, 5.7, 3.6, 0.0), (11.5, 5.7, 3.6, 0.0), (12.3, 4.8, 3.3, 0.0),
          (16.4, 4.7, 3.2, 0.0), (17.2, 3.9, 2.8, 0.0)], BODY)
    # The two lobes either side of the centre groove (columns 9-11 and 13-14, rows 10-16).
    for c, w in ((10.2, 2.3), (13.8, 2.0)):
        lib.ellipsoid(bm, px(c), row(12.8), 1.6 * PX, w * PX, 3.9 * PX, 2.6 * PX, mat=LOBE, segments=12, rings=6)
    # A band across the top of the body (rows 7-8).
    lib.sausage(bm, [(px(8.5), row(7.8)), (px(15.5), row(7.8))], 1.0 * PX, 1.2 * PX, mat=LOBE,
                z_of=lambda x, y: 2.4 * PX)
    # Spike (rows 17-26) with a light ridge down its middle.
    loft([(16.9, 4.0, 2.8, 0.0), (17.5, 3.8, 2.7, 0.0), (19.5, 3.4, 2.4, 0.0), (21.5, 2.6, 1.9, 0.0),
          (23.5, 1.6, 1.3, 0.0), (25.3, 0.8, 0.7, 0.0), (26.6, 0.0, 0.0, 0.0)], SPIKE, sides=12)
    def spike_top(x, y):
        r = 13.5 - y * 12  # sprite row
        return max(0.5, 2.7 - 0.24 * (r - 17.5) - 0.3) * PX
    lib.sausage(bm, [(px(12), row(17.6)), (px(12), row(20.5)), (px(12), row(23.2))],
                [0.85 * PX, 0.75 * PX, 0.5 * PX], [0.7 * PX, 0.6 * PX, 0.45 * PX], mat=LOBE, z_of=spike_top)

    return lib.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)
