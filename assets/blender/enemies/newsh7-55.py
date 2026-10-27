"""Glowing core in the ice (newsh7.shp frames 55, 93, 131): a 3D version of its sprite.

Seen in episode 3 (level section 10). A ground tile of blue ice with a red-hot core set in it: a
low ice mound with a metal rim round the core, light ice ridges running out from the mound and a
dark crack down its right side. The frames only heat the core up (dark red, then orange with a
pale pink highlight, then white hot), so one model covers them all; the core's colours change per
frame (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh7-55.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b108 as lib  # noqa: E402
from lib_b108 import common, ex, ey, px, row  # noqa: E402

NAME = "newsh7-55"
P = 1 / 12
BASE = 0.04  # top of the ice slab


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(58, metallic=0.1, roughness=0.35),  # 0 ice
        pal(60, metallic=0.1, roughness=0.3),  # 1 lighter ice mound
        pal(61, metallic=0.1, roughness=0.25),  # 2 bright ice ridges
        pal(51, metallic=0.1, roughness=0.5),  # 3 dark crack
        pal(9, metallic=0.7, roughness=0.3),  # 4 metal rim
        pal(165, metallic=0.5, roughness=0.45),  # 5 brown inner rim
        # 6 red-hot core: orange on frame 93, white hot on 131
        common.palette_material(sprite, 117, f"{NAME}-core", emission_strength=3.0, frames={93: 122, 131: 127}),
        # 7 white-hot centre, whiter on frame 131
        common.palette_material(sprite, 126, f"{NAME}-hot", emission_strength=5.0, frames={131: 127}),
        pal(78, emission_strength=4.0),  # 8 pale pink highlight (frame 93)
    ]
    ICE, MOUND, RIDGE, CRACK, RIM, INNER, CORE, HOT, PINK = range(9)
    bm = bmesh.new()

    # The ice tile.
    lib.plate(bm, [(ex(0), ey(28)), (ex(24), ey(28)), (ex(24), ey(0)), (ex(0), ey(0))], 0.0, BASE, mat=ICE)

    # Low mound round the core (rows 5-17, columns 4-18).
    cx, cy = px(11.0), row(10.6)
    lib.ring_loft(bm, [lib.ellipse_ring(cx, cy - 0.3 * P, BASE - 0.005, 8.2 * P, 7.4 * P, n=16),
                       lib.ellipse_ring(cx, cy - 0.2 * P, BASE + 0.05, 6.8 * P, 6.2 * P, n=16),
                       lib.ellipse_ring(cx, cy, BASE + 0.09, 5.6 * P, 5.0 * P, n=16)],
                  MOUND, cap_start=False, cap_end=True)

    # Metal rim (rows 7-14, columns 7-15) and a brown lip inside it.
    rim = [(cx + 4.3 * P * math.cos(a * math.pi / 6), cy + 3.9 * P * math.sin(a * math.pi / 6), BASE + 0.1)
           for a in range(13)]
    lib.polyline_tube(bm, rim, 0.75 * P, sides=6, mat_index=RIM, caps=False)
    lib.ring_loft(bm, [lib.ellipse_ring(cx, cy, BASE + 0.09, 4.0 * P, 3.6 * P, n=16),
                       lib.ellipse_ring(cx, cy, BASE + 0.12, 3.6 * P, 3.2 * P, n=16)],
                  INNER, cap_start=False, cap_end=False)

    # The core: a big glowing dome filling the rim, with a hotter centre up and left.
    lib.dome(bm, cx, cy, BASE + 0.09, 3.7 * P, 3.3 * P, 0.13, mat=CORE, segments=16, rings=5)
    # The hot centre is its own part: a small white-hot spot on frames 55 and 131, and on frame 93
    # a wider pale pink highlight over the upper left half of the core (rows 8-11, columns 8-11).
    hbm = bmesh.new()
    lib.ellipsoid(hbm, px(10.0), row(9.8), BASE + 0.17, 1.8 * P, 1.6 * P, 0.06, mat=HOT, segments=10, rings=6)
    hot = common.frame_part(lib.to_object(f"{NAME}-hot", hbm, mats, coll), [55, 131])
    pbm = bmesh.new()
    lib.ellipsoid(pbm, px(9.6), row(9.9), BASE + 0.165, 2.3 * P, 2.1 * P, 0.06, mat=PINK, segments=12, rings=6)
    pink = common.frame_part(lib.to_object(f"{NAME}-pink", pbm, mats, coll), [93])

    # Bright ice ridges running out from the mound.
    z = BASE + 0.005
    for path in (
        [(8, 15), (7, 17.5), (6.2, 20), (5.2, 23.5)],  # down and left
        [(11, 16.5), (11, 21), (11.3, 25.5)],  # straight down
        [(14.5, 16), (15.6, 18.5), (16.6, 21.5)],  # down and right
        [(6.5, 9.2), (4, 9.2), (2, 10.2)],  # left, upper
        [(6.2, 12.3), (3.5, 12.5), (1.8, 13.5)],  # left, lower
        [(16.5, 9.4), (18.5, 10.2), (19.4, 12.2)],  # right
        [(3, 0.2), (3, 3.6), (1.6, 4.5)],  # top-left corner
        [(19.3, 0.2), (19.3, 3.4)],  # top-right corner
        [(10.5, 24), (11.5, 27.5)],  # bottom
    ):
        pts = [(px(c), row(r), z) for c, r in path]
        lib.polyline_tube(bm, pts, 1.1 * P, sides=4, mat_index=RIDGE, squash=0.35)

    # Dark crack down the right side (columns 17-21, rows 3-23).
    crack = [(16.5, 3.8), (18.2, 5.2), (19.8, 8.5), (20.4, 12.5), (19.6, 15.5), (20.0, 18.5), (19.6, 22.5)]
    lib.polyline_tube(bm, [(px(c), row(r), BASE) for c, r in crack], 1.0 * P, sides=4,
                      mat_index=CRACK, squash=0.15, smooth=False)

    return [lib.to_object(NAME, bm, mats, coll), hot, pink]


def main(sprite):
    return [(NAME, build(sprite), sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, main, __file__)
