"""Brown horned bowl (newshh.shp frame 93): a 3D version of its sprite.

Seen in episode 2 (level 2.4), with the brown seed pods (newshh-131). A bronze body like a
deep bowl with a ridge down its front, a pale rim across its middle, a round dome sitting in the
bowl behind the rim, and two horns at the rim's ends curling up and back. One frame.

Run: blender --background --python assets/blender/enemies/newshh-93.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b018 as lib  # noqa: E402
from lib_b018 import px, row  # noqa: E402

NAME = "newshh-93"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(23, metallic=0.45, roughness=0.4),  # 0 bronze bowl
        pal(19, metallic=0.4, roughness=0.55),  # 1 dark underside and the shadow under the dome
        pal(27, metallic=0.5, roughness=0.3),  # 2 pale rim and ridge
        pal(24, metallic=0.5, roughness=0.3),  # 3 dome
        pal(23, metallic=0.45, roughness=0.4),  # 4 horns
    ]
    BOWL, DARK, RIM, DOME, HORN = range(5)
    pixels = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    # The bowl (rows 10-19, columns 3-21, leaving out the horns): a hull lofted down the sprite
    # with a ridge down its front like the sprite's lit left and shaded right halves.
    keep = lambda r, c, v: v not in (-1, 1) and 4 <= c <= 20 or (v not in (-1, 1) and r >= 11)  # noqa: E731
    raw = lib.row_spans(pixels, keep, range(9, 20), inset=-0.3)
    # Smooth the stair-stepped widths a little (the sprite's sides are a curve).
    spans = {r: (px(12), (raw.get(r - 1, raw[r])[1] + 2 * raw[r][1] + raw.get(r + 1, raw[r])[1]) / 4)
             for r in raw}
    wmax = max(hw for _, hw in spans.values())
    H = 0.24

    def height(r):
        return H * (spans[r][1] / wmax) ** 0.5

    rings = [[(px(12), row(8.6), 0.05)]]
    for r in sorted(spans):
        hw = spans[r][1]
        rings.append(lib.section_ring(px(12), row(r), hw, -0.04, height(r), 0.16 * (hw / wmax) ** 0.5,
                                      keel=1.4))
    rings.append([(px(12), row(19.9), -0.04)])
    lib.ring_loft(bm, rings, mat=BOWL)

    # The rim across the middle (rows 11-12), bowed toward the front.
    rim = [(px(c), row(r), z) for c, r, z in ((3.2, 11.2, 0.1), (6, 11.8, 0.17), (9, 12.1, 0.2),
                                                (12, 12.2, 0.21), (15, 12.1, 0.2), (18, 11.8, 0.17),
                                                (20.8, 11.2, 0.1))]
    lib.tube(bm, rim, 0.06, sides=6, mat=RIM, flat=0.6)
    # The ridge down the front (column 12, rows 12-19).
    ridge = [(px(12), row(r), -0.04 + height(r) - 0.01) for r in (13, 14, 16, 17)]
    ridge.append((px(12), row(19.5), -0.02))
    lib.tube(bm, ridge, [0.06, 0.06, 0.05, 0.04, 0.0], sides=6, mat=RIM, flat=0.5)

    # The dome in the bowl behind the rim (rows 5-10, columns 7-17), with a dark shadow ring.
    lib.dome(bm, (px(12), row(8.6), 0.08), (5.4 / 12, 3.4 / 12, 0.24), mat=DOME, segments=18, rings=5)
    lib.tube(bm, [(px(12) + 5.4 / 12 * 0.98 * c, row(8.8) + 3.4 / 12 * 0.95 * s, 0.09)
                  for c, s in ((1, 0), (0.71, -0.71), (0, -1), (-0.71, -0.71), (-1, 0))],
             0.05, sides=6, mat=DARK)

    # A horn at each end of the rim (columns 2-5, rows 5-11), curling up and back, mirrored.
    v0, f0 = len(bm.verts), len(bm.faces)
    lib.tube(bm, [(px(5.3), row(11.2), 0.04), (px(3.9), row(9.8), 0.1), (px(3.0), row(7.8), 0.15),
                  (px(2.9), row(6.0), 0.2), (px(3.1), row(5.0), 0.22)],
             [0.14, 0.13, 0.11, 0.07, 0.0], sides=8, mat=HORN, flat=0.8)
    lib.mirror_new(bm, v0, f0, axis_x=px(12))

    obj = lib.to_object(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
