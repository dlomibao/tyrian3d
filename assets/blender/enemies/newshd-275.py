"""Brown caged turret (newshd.shp frames 275, 277, 279): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.5, 2.8, 3.15), four of them in the fortress set
(assembly-newshd-127). A brown hood at the back, a square brown cage with steel pipes inside
it, red lamps on both flanks and a short neck down to a round barrel whose muzzle glows red.
The frames only brighten the lamps and the muzzle, so one model covers them all: the lamps'
colour follows the frame and each frame has its own muzzle glow (palette_material frames=,
frame_part).

Run: blender --background --python assets/blender/enemies/newshd-275.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshd-275"


def rect(g, c0, r0, c1, r1):
    return [(g.ex(c0), g.ey(r1)), (g.ex(c1), g.ey(r1)), (g.ex(c1), g.ey(r0)), (g.ex(c0), g.ey(r0))]


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][0]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    # Copper-brown frames (the sprite's 164-169) with lighter edges, steel-blue pipes in dark blue
    # windows.
    # Painted copper-brown metal; polished steel pipes.
    def paint(i):
        return m(i, metallic=0.4, roughness=0.4)

    BROWN, LIGHT, DARKB = paint(166), paint(169), paint(164)
    STEEL, DEEP = m(106, metallic=0.8, roughness=0.3), m(101, metallic=0.5, roughness=0.5)
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # Mount running off the top edge (columns 5-17, rows 0-2), a base plate about 3 px tall.
    L.pillow(bm, rect(g, 5, 0, 18, 3), 0.0, 0.25, 0.5 * L.U, mat=DARKB, top_mat=paint(102))
    # Hood across the back (columns 3-19, rows 2-5), the highest part, about 8.5 px.
    hood = L.ellipse(g.x(11), g.y(3.8), 8.6 * L.U, 2.4 * L.U, n=20, power=3.0)
    L.pillow(bm, hood, 0.0, 0.7, 1.2 * L.U, mat=paint(167), top_mat=paint(168), smooth=True)

    # The cage (columns 3-19, rows 5-17), about 7.5 px tall: a frame of brown bars round four
    # windows cut about 2.5 px into it (columns 9-13 rows 6-8, 4-6 and 16-18 rows 9-13, 9-13
    # rows 12-15), steel pipes inside them.
    TOP, FLOOR_W = 0.62, 0.42
    L.pillow(bm, rect(g, 3, 5, 20, 17), 0.0, FLOOR_W, 0.3 * L.U, mat=BROWN, top_mat=DEEP)
    for c0, r0, c1, r1 in ((3, 5, 9, 9), (3, 14, 9, 17), (14, 5, 20, 9), (14, 14, 20, 17), (3, 9, 4, 14),
                           (19, 9, 20, 14), (9, 5, 14, 6), (9, 9, 14, 12), (9, 16, 14, 17)):
        L.pillow(bm, rect(g, c0, r0, c1, r1), FLOOR_W - 0.02, TOP, 0.35 * L.U, mat=BROWN, top_mat=paint(166))
    for c0, c1 in ((7, 9), (14, 16)):  # light uprights either side of the middle
        L.pillow(bm, rect(g, c0, 5, c1, 17), FLOOR_W, TOP + 0.04, 0.4 * L.U, mat=BROWN, top_mat=LIGHT)
    for r0, r1 in ((8.6, 9.8), (15.8, 17)):  # cross bars
        L.pillow(bm, rect(g, 3.5, r0, 19.5, r1), FLOOR_W, TOP + 0.03, 0.3 * L.U, mat=BROWN, top_mat=paint(168))
    # Steel pipes in the windows: one across (row 10), one down the middle (columns 10-12).
    L.tube(bm, [(g.x(3.6), g.y(10.4), FLOOR_W + 0.06), (g.x(19.4), g.y(10.4), FLOOR_W + 0.06)], 0.8 * L.U,
           sides=8, mat=STEEL)
    L.tube(bm, [(g.x(11.5), g.y(6.2), FLOOR_W + 0.05), (g.x(11.5), g.y(15.5), FLOOR_W + 0.05)], 1.6 * L.U,
           sides=10, mat=STEEL, flat=0.7)

    # Red lamps on the flanks (columns 1-2 and 21-22, rows 7-12), brighter on 277 and brighter
    # still on 279: round knobs halfway up the cage's sides.
    lamp = m.anim(116, "lamp", {277: 118, 279: 121}, emission_strength=3.0)
    for c in (2.2, 20.8):
        L.ellipsoid(bm, g.x(c), g.y(10.0), 0.32, 1.7 * L.U, 3.1 * L.U, 0.17, sides=12, rings=6,
                    mat=lamp)

    # Neck (rows 17-20) stepping down from the cage to the barrel.
    neck = [(g.ex(5), g.ey(17)), (g.ex(18), g.ey(17)), (g.ex(17), g.ey(19)), (g.ex(15), g.ey(20.5)),
            (g.ex(8), g.ey(20.5)), (g.ex(6), g.ey(19))]
    L.pillow(bm, neck, 0.0, 0.46, 0.6 * L.U, mat=BROWN, top_mat=paint(165))
    L.tube(bm, [(g.x(8.5), g.y(18.8), 0.44), (g.x(14.5), g.y(18.8), 0.44)], 1.0 * L.U, sides=8, mat=STEEL)
    # The barrel (columns 8-14, rows 20-27): round, about 6.5 px tall, tapering to its glowing
    # muzzle.
    zb = 0.27
    L.loft_y(bm, g.x(11), [(g.ey(20.0), 3.0 * L.U, 0.25, zb), (g.ey(21.5), 3.6 * L.U, 0.27, zb),
                           (g.ey(25.0), 3.4 * L.U, 0.25, zb), (g.ey(26.6), 3.0 * L.U, 0.21, zb - 0.02),
                           (g.ey(27.6), 2.4 * L.U, 0.15, zb - 0.04)],
             sides=14, mat=paint(169))
    obj = L.finish(NAME, bm, m, coll)
    # The muzzle's glow: a dim red spot on 275 (columns 10-12, rows 24-25), a brighter one
    # spilling to the barrel's end on 277, a big bright one on 279 (columns 9-13, rows 23-27).
    parts = [obj]
    for frame, r, rx, ry, mat in ((275, 24.6, 1.5, 1.1, m.glow(114, 2.0)), (277, 25.4, 1.6, 2.0, m.glow(121, 3.5)),
                                  (279, 25.0, 2.4, 2.4, m.glow(121, 3.5))):
        mbm = bmesh.new()
        L.dome(mbm, g.x(11), g.y(r), rx * L.U, ry * L.U, 0.05, z0=zb + 0.23, sides=12, rings=3, mat=mat)
        parts.append(L.part(f"{NAME}-muzzle-{frame}", mbm, m, coll, [frame]))
    return [(NAME, parts, sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
