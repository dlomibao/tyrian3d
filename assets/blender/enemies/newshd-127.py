"""Grey pod with two red lamps (newshd.shp frames 127, 129, 131): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.6, 2.8, 3.15), in a row of six along the top of the fortress set
(assembly-newshd-127; the pieces repeat, so each is modelled on its own). A wide oval grey metal
pod sits on the stone floor; a raised pale plate runs down its middle with two red lamps. The
frames only brighten the lamps, so one model covers them all, the lamps' colour following the
frame (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshd-127.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshd-127"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][0]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # The oval pod: columns 2-22, rows 4-22, its seam darker round the middle.
    cx, cy = g.x(11.6), g.y(13.4)
    L.dome(bm, cx, cy, 10.4 * L.U, 9.2 * L.U, 0.2, z0=L.FLOOR - 0.01, sides=24, rings=4, mat=m.metal(9),
           power=2.2, flat=0.25)
    L.dome(bm, cx, cy, 10.6 * L.U, 9.4 * L.U, 0.07, z0=L.FLOOR - 0.01, sides=24, rings=1, mat=m.metal(4),
           power=2.2, flat=0.9)
    # Ribs across the pod either side of the plate (light grey at columns 4-6 and 17-19).
    for c0, c1 in ((3.2, 7.6), (16.0, 20.4)):
        L.loft_x(bm, g.y(9.3), [(g.x(c0), 0.6 * L.U, 0.02, 0.17), (g.x(c1), 0.6 * L.U, 0.02, 0.2)],
                 sides=6, mat=m.metal(11))
        L.loft_x(bm, g.y(17.6), [(g.x(c0), 0.6 * L.U, 0.02, 0.17), (g.x(c1), 0.6 * L.U, 0.02, 0.2)],
                 sides=6, mat=m.metal(11))

    # The pale plate down the middle (columns 8-15, rows 5-21) with a darker inset.
    plate = [(g.ex(8), g.ey(21.5)), (g.ex(16), g.ey(21.5)), (g.ex(16), g.ey(5)), (g.ex(8), g.ey(5))]
    L.pillow(bm, plate, 0.1, 0.27, 0.6 * L.U, mat=m.metal(12), top_mat=m.metal(8))
    # Two red lamps (columns 10-13, rows 9-11 and 15-18), brightening from red (127) through
    # orange (129) to yellow-orange (131).
    lamp = m.anim(119, "lamp", {129: 121, 131: 123}, emission_strength=3.0)
    for r in (10.0, 16.4):
        L.dome(bm, g.x(11.5), g.y(r), 2.4 * L.U, 2.1 * L.U, 0.03, z0=0.265, sides=12, rings=1,
               mat=m.metal(7), flat=0.85)
        L.dome(bm, g.x(11.5), g.y(r), 1.8 * L.U, 1.6 * L.U, 0.06, z0=0.27, sides=12, rings=3,
               mat=lamp)
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
