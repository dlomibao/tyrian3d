"""Pink housing with a glowing slit (newshd.shp frames 267-273): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.5, 1.6, 2.8, 3.15). A tall rounded housing of pink-red metal on
the stone floor, with lugs on both flanks, dark vents beside a raised inner frame and, down
its middle, a slit whose core glows from dull red to white-hot. The frames only change the
glow, so one model covers them all: a cold core on frame 267 and a glowing one whose colour
follows the frame (frame_part, palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshd-267.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshd-267"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][3]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # Lugs on the flanks (columns 0-2 and 18-20, rows 6-17).
    L.pillow(bm, L.chamfer(g, 0, 5.6, 4, 18.4, 1), 0.0, 0.18, 0.5 * L.U, mat=m.metal(68), top_mat=m.metal(72))
    L.pillow(bm, L.chamfer(g, 17, 5.6, 21, 18.4, 1), 0.0, 0.18, 0.5 * L.U, mat=m.metal(68), top_mat=m.metal(72))
    # The housing (columns 2-18, rows 0-25).
    L.pillow(bm, L.chamfer(g, 2, 0, 19, 26, 2.5), 0.0, 0.28, 1.0 * L.U, mat=m.metal(70), top_mat=m.metal(72))
    # Dark vents beside the inner frame.
    for c0, c1 in ((3, 6), (15, 18)):
        L.box(bm, g.ex(c0), g.ey(17), g.ex(c1), g.ey(7), 0.2, 0.283, mat=m.metal(2))
    # The inner frame (columns 6-14, rows 2-21), lighter, round the slit.
    frame = L.chamfer(g, 6, 2, 15, 21.5, 1.5)
    L.pillow(bm, frame, 0.2, 0.36, 0.6 * L.U, mat=m.metal(74), top_mat=m.metal(76))
    # The slit (columns 8-12, rows 5-18): dark rim and the core. The rim reddens as the core
    # heats up (frames 271, 273).
    L.box(bm, g.ex(8), g.ey(18.6), g.ex(13), g.ey(4.6), 0.3, 0.362,
          mat=m.anim(113, "rim", {271: 114, 273: 117}, metallic=0.6, roughness=0.35))
    obj = L.finish(NAME, bm, m, coll)

    # The core: cold, the housing's pink-grey, on frame 267; then glowing dull red (269),
    # orange (271) and white-hot (273).
    def core(mat):
        cbm = bmesh.new()
        L.loft_y(cbm, g.x(9.8), [(g.ey(6.5), 0.0, 0.0, 0.355), (g.ey(7.5), 1.4 * L.U, 0.025, 0.355),
                                 (g.ey(16.5), 1.4 * L.U, 0.025, 0.355), (g.ey(17.5), 0.0, 0.0, 0.355)],
                 sides=8, mat=mat)
        return cbm
    cold = L.part(f"{NAME}-core-cold", core(m.metal(71)), m, coll, [267])
    hot = L.part(f"{NAME}-core-hot", core(m.anim(122, "core", {269: 117, 271: 122, 273: 126},
                                                   emission_strength=4.0)), m, coll, [269, 271, 273])
    return [(NAME, [obj, cold, hot], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
