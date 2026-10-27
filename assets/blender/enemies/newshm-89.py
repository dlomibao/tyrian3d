"""Grey twin-blade fighter (newshm.shp frames 89, 91, 93): a 3D version of its sprite.

Seen in episode 2 (levels 2.10 and 2.19). It flies nose down the screen: two long grey blades
side by side, each with a bright raised inner ridge and a rolled outer rim, wide at the shoulders
and tapering to two prongs at the bottom with a gap between them. A dark recessed bridge with two
light ribs joins them at the shoulders, and an engine between two grey nozzle cheeks at the back
(top of the sprite) blows a red-orange flame with a yellow-white core. The three frames only
change the flame's length (its tip reaches rows 5, 4 and 3), so one model covers them all, with a
flame per frame (common.frame_part).

Run: blender --background --python assets/blender/enemies/newshm-89.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b016 as lib  # noqa: E402

NAME = "newshm-89"
P = 1 / 12  # one sprite pixel
CENTRE = lib.px(12)  # the sprite is symmetric about column 12


def blade_top(w, _):
    """Top of a blade from its inner edge outward: a sharp inner ridge, a shallow valley, a
    rolled outer rim."""
    return [(0.0, 0.55), (0.13 * w, 1.0), (0.3 * w, 0.78), (0.5 * w, 0.68), (0.72 * w, 0.74),
            (0.88 * w, 0.62), (w, 0.15)]


def blade_bottom(w, _):
    return [(0.0, 0.45), (0.13 * w, 0.75), (0.3 * w, 0.9), (0.5 * w, 0.95), (0.72 * w, 0.85),
            (0.88 * w, 0.6), (w, 0.15)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(12, metallic=0.55, roughness=0.3),  # 0 bright inner ridges and bridge ribs
        pal(8, metallic=0.5, roughness=0.4),  # 1 grey blade plating
        pal(10, metallic=0.5, roughness=0.35),  # 2 light outer rims and nozzle cheeks
        pal(6, metallic=0.4, roughness=0.5),  # 3 dark underside
        pal(3, metallic=0.3, roughness=0.6),  # 4 dark recessed bridge
        pal(117, emission_strength=3.0),  # 5 red outer flame
        pal(123, emission_strength=4.5),  # 6 orange-yellow flame core
        pal(126, emission_strength=6.0),  # 7 white-hot centre
    ]
    RIDGE, PLATE, RIM, UNDER, BRIDGE, FLAME, CORE, HOT = range(8)
    bm = bmesh.new()

    # Left blade, back (top) to nose prong (bottom): (pixel row edge, outer column edge,
    # top half-height px, bottom half-height px). Its inner edge is column 11's left edge; the
    # right blade is its mirror about column 12.
    sections = [
        (9.9, 8.0, 1.6, 1.2), (10.4, 6.9, 2.4, 1.7), (11.2, 5.7, 2.8, 2.0), (12.0, 5.05, 3.0, 2.1),
        (14.7, 5.05, 3.0, 2.1), (15.3, 6.6, 2.9, 2.0), (16.0, 7.0, 2.8, 2.0), (19.0, 7.3, 2.4, 1.7),
        (22.0, 8.3, 2.0, 1.4), (24.0, 9.3, 1.6, 1.1), (25.9, 10.3, 1.0, 0.7),
    ]
    blade = [(lib.ey(r), lib.ex(11), lib.ex(xo), ht * P, hb * P, None) for r, xo, ht, hb in sections]
    strip = [RIDGE, RIDGE, PLATE, PLATE, RIM, RIM]
    for side in (1, -1):
        lib.profile_blade(bm, blade, blade_top, blade_bottom, strip, side=side, mirror_about=CENTRE,
                          under_mat=UNDER)

    # Dark recessed bridge between the blades at the shoulders (rows 11-15, columns 11-13), with
    # two light ribs across it (rows 12 and 14).
    x0, x1 = lib.ex(10.7), lib.ex(14.3)
    common.slab(bm, [(x0, lib.ey(16.2)), (x1, lib.ey(16.2)), (x1, lib.ey(10.8)), (x0, lib.ey(10.8))],
                0.2, z=-0.02, mat_index=BRIDGE)
    for r in (12, 14):
        y0, y1 = lib.ey(r + 1) + 0.15 * P, lib.ey(r) - 0.15 * P
        common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.06, z=0.1, mat_index=RIDGE)

    # Grey nozzle cheeks either side of the engine (columns 10 and 14, rows 8-10).
    for side in (1, -1):
        start = len(bm.verts)
        common.loft(bm, [(lib.ey(10.8), 0.55 * P, 1.9 * P, 0.0), (lib.ey(9.0), 0.55 * P, 1.8 * P, 0.0),
                         (lib.ey(7.9), 0.4 * P, 1.2 * P, 0.0)], sides=6, mat_index=RIM)
        common.shift_x(bm, start, CENTRE + side * 2 * P)

    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # The flame, from inside the nozzle out past the back (rows 5-10, columns 8-16): a flat red
    # outer flame, an orange-yellow core above it and a white-hot centre at the nozzle. Its tip
    # reaches row 5 on frame 89, row 4 on 91 and row 3 on 93; each frame gets a flame stretched
    # from the nozzle (row 10.8) to its tip.
    flames = [
        (FLAME, [(10.8, 2.4, 1.0), (9.0, 3.6, 1.2), (7.6, 3.3, 1.1), (6.6, 2.0, 0.9), (5.6, 0.9, 0.6),
                 (4.9, 0.0, 0.0)], 0.0),
        (CORE, [(10.8, 1.5, 1.6), (9.5, 1.65, 1.7), (8.0, 1.4, 1.5), (7.0, 0.8, 1.1), (6.2, 0.0, 0.0)], 0.02),
        (HOT, [(10.6, 0.7, 1.9), (9.6, 0.8, 2.0), (8.6, 0.0, 0.0)], 0.03),
    ]
    parts = [body]
    for frame, tip in ((89, 4.9), (91, 3.9), (93, 2.9)):
        k = (10.8 - tip) / (10.8 - 4.9)
        fbm = bmesh.new()
        for mat, secs, z in flames:
            start = len(fbm.verts)
            common.loft(fbm, [(lib.ey(10.8 - (10.8 - r) * k), w * P, h * P, z) for r, w, h in secs], sides=8, mat_index=mat)
            common.shift_x(fbm, start, CENTRE)
        parts.append(common.frame_part(common.mesh_object(f"{NAME}-flame-{frame}", fbm, mats, coll, smooth=True), [frame]))
    return parts


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, build(sprite), sprite["sprites"])], __file__)
