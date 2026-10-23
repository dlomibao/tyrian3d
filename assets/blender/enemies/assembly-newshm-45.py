"""Steel dome with red trim (newshm.shp frames 45, 47, 49 over 83, 85, 87): a 3D version of its
sprites.

Seen in episode 3 (level 3.15). Six 2x2 pieces make one 72 x 56 px dome on the stone floor:
a broad blue-steel dome with red trim (a yoke round a red capsule at the top, crescents at the
lower corners), two small dark ports and two brown vents, and dark seams down and across it.
The bottom middle piece is frame 85 of catalogue entry newshm-7 (whose other frames, 7, 9 and
11, are a separate lamp tile, newshm-7.py), so it is exported as newshm-7-f2.

Built whole and cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshm-45.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshm-45"
PIECES = [["newshm-45", "newshm-47", "newshm-49"], ["newshm-83", "newshm-7-f2", "newshm-87"]]


def build(sprite, g):
    coll = common.reset_collection(NAME)
    m = L.Mats("nshm45", sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # The dome (columns 5-67, rows 2-54).
    cx, cy, rx, ry, h = g.x(35.8), g.y(28.0), 31.0 * L.U, 25.8 * L.U, 0.46
    L.dome(bm, cx, cy, rx, ry, h, z0=0.0, sides=32, rings=8, mat=m.metal(105))
    zf = L.dome_z(cx, cy, rx, ry, h, z0=0.0)
    red_dark, red_light, seam = m.metal(68), m.metal(72), m.metal(98)
    steel_dark, steel_light = m.metal(102), m.metal(108)

    def trim(i):
        if 65 <= i <= 69:
            return red_dark
        if 70 <= i <= 78 or 118 <= i <= 126:
            return red_light
        if 96 <= i <= 99:
            return seam
        if 100 <= i <= 103:
            return steel_dark
        if 107 <= i <= 111:
            return steel_light
        return None
    # Red trim and dark seams painted on the dome (the capsule and vents are modelled below).
    L.painted(bm, g, 5, 2, 68, 55, zf, trim, skip=(-1, 1), max_run=3)

    # The red capsule at the top (columns 33-40, rows 4-17) with an orange highlight.
    top = zf(g.x(36.5), g.y(10.5)) - 0.03
    L.loft_y(bm, g.x(36.5), [(g.ey(3.6), 0.0, 0.0, top), (g.ey(4.6), 2.6 * L.U, 0.05, top),
                             (g.ey(6.5), 3.8 * L.U, 0.08, top), (g.ey(15.5), 3.8 * L.U, 0.08, top),
                             (g.ey(17.6), 3.0 * L.U, 0.05, top)], sides=12, mat=m.metal(70))
    L.loft_y(bm, g.x(35.2), [(g.ey(5.0), 0.0, 0.0, top + 0.06), (g.ey(6.0), 0.5 * L.U, 0.02, top + 0.07),
                             (g.ey(11.0), 0.5 * L.U, 0.02, top + 0.07), (g.ey(12.0), 0.0, 0.0, top + 0.06)],
             sides=6, mat=m.glow(121, 2.0))
    # Two dark ports (rows 12-15) and two brown vents (rows 30-38), sunk into the dome.
    for c in (16.4, 55.6):
        x, y = g.x(c), g.y(13.6)
        L.dome(bm, x, y, 2.0 * L.U, 2.0 * L.U, 0.02, z0=zf(x, y) - 0.02, sides=10, rings=1,
               mat=m.metal(100), flat=0.8)
        x, y = g.x(c), g.y(34.6)
        L.dome(bm, x, y, 4.4 * L.U, 4.4 * L.U, 0.03, z0=zf(x, y) - 0.025, sides=16, rings=1,
               mat=m.metal(106), flat=0.85)
        L.dome(bm, x, y, 3.4 * L.U, 3.4 * L.U, 0.03, z0=zf(x, y) - 0.015, sides=16, rings=2,
               mat=m.metal(165), flat=0.4)
    return L.finish(NAME, bm, m, coll), []


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 3, 2, frames_of={"newshm-7-f2": [85]})
