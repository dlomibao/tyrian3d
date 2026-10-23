"""Grey crate marked 218 (newshp.shp frames 165, 167, 203, 205, 241, 243): a 3D version of its
sprites.

Seen in episodes 2 and 3 (levels 2.8, 3.15). Six 2x2 pieces (two across, three down) make one
48 x 84 px object: a long grey crate lying on a dark grilled plinth on the stone floor. Its top
is a flat panel with the number 218 stencilled along it in pale grey, with a light bevel down its
left side and a darker one down its right.

Built whole and cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshp-165.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshp-165"
PIECES = [["newshp-165", "newshp-167"], ["newshp-203", "newshp-205"], ["newshp-241", "newshp-243"]]
TOP, SHOULDER = 0.46, 0.32


def build(sprite, g):
    coll = common.reset_collection(NAME)
    m = L.Mats("nshp165", sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"], rect=(0, 28, 48, 84))
    tones = L.grey_tones(m, sprite["colors"], finish=lambda i: m(i, metallic=0.4, roughness=0.5))

    # The plinth under the front of the crate (columns 5-42, rows 50-68), its top grilled.
    L.box(bm, g.ex(5), g.ey(68.5), g.ex(42.5), g.ey(50), 0.0, 0.15, mat=m.metal(3))
    L.painted(bm, g, 5, 55, 43, 69, lambda x, y: 0.153, tones)

    # The crate (columns 6-41, rows 14-55): flat top panel between two bevels.
    y0, y1 = g.ey(55.5), g.ey(14)
    xl, xa, xb, xr = g.ex(6.2), g.ex(13), g.ex(33), g.ex(41.2)
    L.extrude_y(bm, [(xa, 0.0), (xa, TOP), (xl, SHOULDER), (xl, 0.0)], y0, y1, mat=m.metal(9))
    L.extrude_y(bm, [(xb, 0.0), (xr, 0.0), (xr, SHOULDER), (xb, TOP)], y0, y1, mat=m.metal(6))
    L.box(bm, xa, y0, xb, y1, 0.0, TOP, mat=m.metal(10))
    # The stencilled 218 and the panel's rims, painted on the top.
    pal = {12: m.metal(13), 13: m.metal(13), 14: m.metal(13), 15: m.metal(13), 11: m.metal(11),
           7: m.metal(7), 8: m.metal(8)}
    L.painted(bm, g, 13, 15, 33, 55, lambda x, y: TOP + 0.003, lambda i: pal.get(i))
    # Ribs down the bevels (the light and dark stripes at columns 7-12 and 33-40).
    for c in (8.0, 10.0):
        L.tube(bm, [(g.x(c), y0 + 0.02, SHOULDER + (TOP - SHOULDER) * (c - 6.2) / 6.8 + 0.005),
                    (g.x(c), y1 - 0.02, SHOULDER + (TOP - SHOULDER) * (c - 6.2) / 6.8 + 0.005)],
               0.35 * L.U, sides=6, mat=m.metal(8))
    for c in (35.0, 37.0, 39.0):
        L.tube(bm, [(g.x(c), y0 + 0.02, TOP - (TOP - SHOULDER) * (c + 0.5 - 33) / 8.2 + 0.005),
                    (g.x(c), y1 - 0.02, TOP - (TOP - SHOULDER) * (c + 0.5 - 33) / 8.2 + 0.005)],
               0.35 * L.U, sides=6, mat=m.metal(5))
    return L.finish(NAME, bm, m, coll), []


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 2, 3)
