"""Grey tank with a red band (newshs.shp frames 165, 167 over 203, 205): a 3D version of its
sprites.

Seen in episode 3 (level 3.15). Four 2x2 pieces make one 48 x 56 px tank seen from above: two
grey tracks at the front with dark treads, a grey hull with louvred fenders and red side panels,
a red band across it, a red block behind and a pale ball turret on top, and a sloping red glacis
between the tracks.

Built whole and cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshs-165.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshs-165"
PIECES = [["newshs-165", "newshs-167"], ["newshs-203", "newshs-205"]]
HULL_TOP = 0.3
TRACK_TOP = 0.24


def build(sprite, g):
    coll = common.reset_collection(NAME)
    m = L.Mats("nshs165", sprite["colors"])
    tones = L.grey_tones(m, sprite["colors"], finish=lambda i: m(i, metallic=0.2, roughness=0.75))
    grey = lambda i: tones(i) if 1 <= i <= 15 else None  # noqa: E731
    bm = bmesh.new()

    # Tracks (columns 3-18 and 30-45, rows 28-54), their tops showing the treads.
    for c0, c1 in ((3, 19), (30, 46)):
        L.pillow(bm, L.chamfer(g, c0, 27, c1, 55, 1.5), 0.0, TRACK_TOP, 0.4 * L.U, mat=m.metal(5))
        L.painted(bm, g, c0, 29, c1, 54, lambda x, y: TRACK_TOP + 0.003, grey)

    # The hull (columns 3-45, rows 9-29), its top painted with the fenders' louvres.
    L.pillow(bm, L.chamfer(g, 3, 8.5, 46, 30, 1.0), 0.0, HULL_TOP, 0.4 * L.U, mat=m.metal(6), top_mat=m.metal(8))
    L.painted(bm, g, 3, 9, 46, 17, lambda x, y: HULL_TOP + 0.003, grey)
    # Red side panels (columns 3-8 and 40-45, rows 17-28).
    for c0, c1 in ((3, 9), (39.5, 45.5)):
        L.pillow(bm, L.rect(g, c0, 17.5, c1, 28.5), 0.0, HULL_TOP + 0.03, 0.5 * L.U, mat=m.metal(67),
                 top_mat=m.metal(69))
    # The red band across (columns 10-38, rows 17-21) and the red block behind the turret.
    L.pillow(bm, L.rect(g, 9.5, 16.6, 38.5, 21.6), 0.0, HULL_TOP + 0.06, 0.5 * L.U, mat=m.metal(68),
             top_mat=m.metal(72))
    L.pillow(bm, L.rect(g, 21.5, 8.6, 27.5, 14), 0.0, HULL_TOP + 0.06, 0.4 * L.U, mat=m.metal(67),
             top_mat=m.metal(70))
    # Sloping red glacis between the tracks (columns 19-29, rows 30-44).
    x0, x1 = g.ex(19), g.ex(30)
    y0, y1 = g.ey(29.5), g.ey(44.5)
    L.ring_loft(bm, [[(x0, y0, 0.0), (x0, y1, 0.0), (x0, y1, 0.1), (x0, y0, HULL_TOP)],
                     [(x1, y0, 0.0), (x1, y1, 0.0), (x1, y1, 0.1), (x1, y0, HULL_TOP)]], mat=m.metal(69))
    L.box(bm, g.ex(20), g.ey(34.5), g.ex(29), g.ey(33), 0.0, 0.24, mat=m.metal(69))  # its lighter rib

    # The ball turret (columns 16-32, rows 8-28) with a bright crown.
    L.dome(bm, g.x(23.8), g.y(16.0), 8.2 * L.U, 7.6 * L.U, 0.26, z0=HULL_TOP - 0.04, sides=24, rings=5,
           mat=m.metal(10))
    L.dome(bm, g.x(21.5), g.y(12.5), 2.6 * L.U, 2.4 * L.U, 0.04, z0=HULL_TOP + 0.17, sides=12, rings=2,
           mat=m.metal(12), flat=0.3)
    return L.finish(NAME, bm, m, coll), []


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 2, 2)
