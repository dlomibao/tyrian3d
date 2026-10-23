"""Horned gunship with a glowing core (newshk.shp frame 278): a 3D version of its sprite.

Seen in episode 3 (level 3.12). Nose down the screen. The back half: two grey horns rising up
the outer edges, braced to a grey collar round a big glowing orange-yellow core in the middle,
on a darker deck whose front edge is a bright ridge with a small red light. The front half: a wide
grey block with tan vent frames at both sides, bright rails either side of a sunken dark red
channel down the middle, where two pink-red pipes and a grey rod run out past the nose.

Run: blender --background --python assets/blender/enemies/newshk-278.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b045 as lib  # noqa: E402
from lib_b045 import U, common, ex, ey, px  # noqa: E402

NAME = "newshk-278"
AXIS = ex(12.5)  # the centre parts' axis (column 12's centre)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.55, roughness=0.4),  # 0 block top
        pal(8, metallic=0.55, roughness=0.4),  # 1 block sides
        pal(12, metallic=0.65, roughness=0.3),  # 2 bright rails, ridges
        pal(10, metallic=0.6, roughness=0.35),  # 3 horns
        pal(5, metallic=0.5, roughness=0.5),  # 4 dark deck
        pal(26, metallic=0.3, roughness=0.5),  # 5 tan vent frame
        pal(9, metallic=0.5, roughness=0.4),  # 6 vent centre
        pal(112, metallic=0.3, roughness=0.6),  # 7 dark red channel, rims
        pal(72, metallic=0.35, roughness=0.4),  # 8 pink-red pipes
        pal(67, metallic=0.4, roughness=0.45),  # 9 pipe ends
        pal(3, metallic=0.4, roughness=0.6),  # 10 dark nose housing
        pal(15, metallic=0.7, roughness=0.25),  # 11 rod tip
        pal(116, emission_strength=2.5),  # 12 red light
        pal(121, emission_strength=3.0),  # 13 core glow
        pal(127, emission_strength=5.0),  # 14 core hot centre
        pal(113, metallic=0.3, roughness=0.5),  # 15 core rim
        pal(6, metallic=0.55, roughness=0.4),  # 16 collar
        pal(29, metallic=0.3, roughness=0.45),  # 17 tan highlight
    ]
    (TOP, SIDE, BRIGHT, HORN, DECK, TAN, VENT, CHANNEL, PIPE, PIPE_END, NOSE, TIP, LIGHT, GLOW, HOT, RIM,
     COLLAR, TAN_HI) = range(18)
    bm = bmesh.new()

    # ---- left side, mirrored about the axis ----
    start = len(bm.verts)
    f0 = len(bm.faces)
    # Horn (column 2, rows 0-11), widening into the deck.
    lib.polyline_tube(bm, [(ex(2.5), ey(0.2), 0.08), (ex(2.5), ey(1.2), 0.08), (ex(2.5), ey(5), 0.07),
                           (ex(2.8), ey(9), 0.06), (ex(3.2), ey(11.5), 0.05)],
                      [0.4 * U, 1.1 * U, 1.3 * U, 1.7 * U, 1.9 * U], sides=8, mat_index=HORN, flat=0.9)
    # Brace from the horn to the core's collar (row 8).
    lib.polyline_tube(bm, [(ex(3.4), ey(8.6), 0.08), (ex(8.4), ey(8.0), 0.11)], 0.75 * U, sides=6,
                      mat_index=BRIGHT)
    # Rail (columns 7-8, rows 15-24).
    lib.polyline_tube(bm, [(ex(8), ey(14.6), 0.1), (ex(8), ey(24.6), 0.1)], 1.0 * U, sides=8, mat_index=BRIGHT,
                      flat=0.8)
    # Pink-red pipe (column 10) down the channel and out past the nose.
    lib.polyline_tube(bm, [(px(10), ey(15), 0.03), (px(10), ey(21), 0.03)], 0.8 * U, sides=8, mat_index=PIPE)
    lib.polyline_tube(bm, [(px(10), ey(21), 0.03), (px(10), ey(26.8), 0.02)], [0.8 * U, 0.7 * U], sides=8,
                      mat_index=PIPE_END)
    lib.set_smooth(bm, f0)
    lib.mirror_x(bm, start, axis=AXIS)

    # ---- lower block (rows 14-24), split round the channel (columns 9-15) ----
    for c0, c1 in ((0, 9.2), (15.8, 24)):
        lib.bevel_prism(bm, [(ex(c0), ey(24)), (ex(c1), ey(24)), (ex(c1), ey(14)), (ex(c0), ey(14))], -0.12, 0.09,
                        0.12, bevel_h=0.05, mat_index=TOP, side_mat=SIDE)
    # The channel's dark red floor, and the pink-red bracket across it (rows 16-17).
    lib.box(bm, ex(9), ey(24), ex(16), ey(14), -0.1, 0.0, CHANNEL)
    lib.box(bm, ex(9.6), ey(18), ex(15.4), ey(15.8), 0.0, 0.07, PIPE)
    # Tan vent frames (columns 2-4 and 19-21, rows 15-18 and 20-23) with grey centres.
    for c in (2, 19):
        for r0, r1 in ((15, 19), (20, 24)):
            lib.bevel_prism(bm, [(ex(c), ey(r1 - 0.1)), (ex(c + 3), ey(r1 - 0.1)), (ex(c + 3), ey(r0 + 0.1)),
                                 (ex(c), ey(r0 + 0.1))], 0.0, 0.12, 0.02, mat_index=TAN, side_mat=TAN_HI)
            lib.box(bm, ex(c + 1), ey(r1 - 1.1), ex(c + 2), ey(r0 + 1.1), 0.1, 0.135, VENT)
    # Dark housing under the nose (rows 24-25) and the grey rod out of it (column 12).
    lib.bevel_prism(bm, [(ex(7.5), ey(25.6)), (ex(17.5), ey(25.6)), (ex(17.5), ey(23.5)), (ex(7.5), ey(23.5))],
                    -0.09, 0.05, 0.015, mat_index=NOSE)
    f0 = len(bm.faces)
    lib.polyline_tube(bm, [(px(12), ey(18), 0.02), (px(12), ey(26.3), 0.02)], 0.65 * U, sides=8, mat_index=SIDE)
    lib.ellipsoid(bm, (px(12), ey(26.4), 0.02), (0.75 * U, 0.7 * U, 0.055), sides=8, rings=6, mat_index=TIP)
    lib.set_smooth(bm, f0)

    # ---- back half: deck, collar and core ----
    # Deck (rows 9-14) between the horns, its front edge a bright ridge (row 12) with a red light.
    lib.bevel_prism(bm, [(ex(2.5), ey(14.2)), (ex(22.5), ey(14.2)), (ex(22.5), ey(9.5)), (ex(19), ey(8.5)),
                         (ex(6), ey(8.5)), (ex(2.5), ey(9.5))], -0.1, 0.13, 0.02, mat_index=DECK, side_mat=DECK)
    f0 = len(bm.faces)
    lib.polyline_tube(bm, [(ex(5), ey(12.6), 0.13), (ex(20), ey(12.6), 0.13)], 0.75 * U, sides=8,
                      mat_index=BRIGHT, flat=0.7)
    lib.set_smooth(bm, f0)
    lib.box(bm, ex(10.8), ey(14.1), ex(14.2), ey(12.8), 0.08, 0.16, LIGHT)
    # Grey collar (columns 7-17, rows 4-10) round the core.
    lib.bevel_prism(bm, [(ex(7), ey(10.5)), (ex(18), ey(10.5)), (ex(18), ey(5)), (ex(16), ey(3.4)), (ex(9), ey(3.4)),
                         (ex(7), ey(5))], -0.06, 0.15, 0.03, mat_index=COLLAR, side_mat=DECK)
    # The core: a glowing dome in a dark red rim, white-hot in the middle (rows 3-10).
    f0 = len(bm.faces)
    lib.ellipsoid(bm, (AXIS, ey(6.7), 0.12), (3.9 * U, 4.4 * U, 0.08), sides=16, rings=8, mat_index=RIM)
    lib.ellipsoid(bm, (AXIS, ey(6.6), 0.13), (3.0 * U, 3.6 * U, 0.15), sides=16, rings=8, mat_index=GLOW)
    lib.ellipsoid(bm, (AXIS, ey(6.4), 0.2), (1.6 * U, 1.6 * U, 0.09), sides=12, rings=6, mat_index=HOT)
    lib.set_smooth(bm, f0)
    return [lib.mesh_object_mixed(NAME, bm, mats, coll)]


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
