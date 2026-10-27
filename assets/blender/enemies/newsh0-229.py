"""Blue crawler (newsh0.shp frames 229, 231, 233): a 3D version of its sprite.

A ground unit in episode 2 (level 22), facing down the screen: a blue steel hull that widens
from a notched top, with two bright ribs running down it from rounded humps, a dark channel
between them, then two leg pods at the bottom corners, each with a slanting row of red lights,
and a short central snout with a red-hot vent across it. The frames only brighten the leg lights,
so one model covers them all and animates: each light steps from dark red (229) through red (231)
to orange (233) in its own palette colours.

Run: blender --background --python assets/blender/enemies/newsh0-229.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b104 as lib  # noqa: E402
from lib_b104 import common, ex, ey, px, row  # noqa: E402

NAME = "newsh0-229"  # symmetric about the edge between columns 11 and 12 (X = 0)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(50, metallic=0.4, roughness=0.6),  # 0 dark floor and channel
        pal(55, metallic=0.55, roughness=0.45),  # 1 hull walls
        pal(57, metallic=0.6, roughness=0.4),  # 2 hull top / flanks
        pal(60, metallic=0.65, roughness=0.3),  # 3 ribs
        pal(62, metallic=0.7, roughness=0.25),  # 4 rib crests
        pal(57, metallic=0.6, roughness=0.35),  # 5 legs and snout
        pal(116, emission_strength=3.0),  # 6 red vent
        pal(121, emission_strength=5.0),  # 7 vent core
        pal(52, metallic=0.5, roughness=0.5),  # 8 shadowed hull
        # The leg lights, top to bottom along each slanting row, brightening frame by frame.
        common.palette_material(sprite, 113, f"{NAME}-light1", emission_strength=3.0, frames={231: 115, 233: 117}),
        common.palette_material(sprite, 114, f"{NAME}-light2", emission_strength=3.0, frames={231: 116, 233: 121}),
        common.palette_material(sprite, 116, f"{NAME}-light3", emission_strength=4.0, frames={231: 118, 233: 120}),
    ]
    FLOOR, WALL, TOP, RIB, CREST, LEG, RED, CORE, SHADE, LIGHT1, LIGHT2, LIGHT3 = range(12)
    bm = bmesh.new()

    def at(x, fn):
        start = len(bm.verts)
        fn()
        common.shift_x(bm, start, x)

    # Hull (rows 8-16): narrow at the notched top, widening to columns 5-18, with chamfered top edges.
    outline = [(-7 / 12, ey(17)), (-7 / 12, ey(11)), (-6 / 12, ey(10)), (-5 / 12, ey(9)), (-4 / 12, ey(8))]
    outline = outline + [(-x, y) for x, y in reversed(outline)]
    outline = list(reversed(outline))  # counter-clockwise from above
    rings = [[(x, y, z) for x, y in outline] for z in (0.0, 0.14)]
    cx, cy = 0.0, ey(12.5)
    rings.append([(cx + (x - cx) * 0.86, cy + (y - cy) * 0.9, 0.22) for x, y in outline])
    lib.ring_loft(bm, rings, [WALL, TOP], cap_mats=(FLOOR, TOP))

    # Dark floor under the bottom half, showing between the legs and the snout (rows 16-23).
    lib.prism(bm, [(ex(6), ey(23)), (ex(18), ey(23)), (ex(18), ey(16)), (ex(6), ey(16))], 0.0, 0.03,
              mat_index=FLOOR)
    hull = common.mesh_object(f"{NAME}_hull", bm, mats, coll, smooth=False)
    bm = bmesh.new()

    # Dark channel down the middle of the hull (columns 11-12, rows 8-13).
    lib.stack(bm, 0.0, row(10.5), [(0.18, 1.0 / 12, 3.0 / 12, 3.0), (0.235, 1.0 / 12, 3.0 / 12, 3.0)], n=12,
              mats=SHADE)

    # Ribs (columns 9-10 / 13-14): a rounded hump at the top running down into a ridge to row 17.
    rib = [(7.5, 0.0, 0.0, 0.2), (8.0, 1.7, 0.08, 0.22), (9.2, 2.3, 0.12, 0.23), (11, 2.0, 0.11, 0.23),
           (13, 1.5, 0.09, 0.22), (16.5, 1.3, 0.08, 0.2), (17.3, 0.0, 0.0, 0.19)]
    for x in (px(9.4), px(13.6)):
        at(x, lambda: common.loft(bm, [(row(r), w / 12, h, z) for r, w, h, z in rib], sides=10, mat_index=RIB))
        at(x, lambda: common.loft(bm, [(row(r), w * 0.35 / 12, 0.03, z + h * 0.92)
                                       for r, w, h, z in rib[1:-1]], sides=6, mat_index=CREST))

    # Leg pods (columns 6-8 / 15-17, rows 15-23), rounded at the bottom, with slanting red lights.
    leg = [(14.5, 1.5, 0.1, 0.1), (17, 1.6, 0.12, 0.12), (20, 1.6, 0.12, 0.12), (22.6, 1.4, 0.1, 0.1),
           (23.6, 0.8, 0.07, 0.08), (23.9, 0.0, 0.0, 0.07)]
    lights = [(8, 20, LIGHT1), (7, 21, LIGHT2), (6, 22, LIGHT3)]
    for side in (-1, 1):
        x = side * -px(7)
        at(x, lambda: common.loft(bm, [(row(r), w / 12, h, z) for r, w, h, z in leg], sides=10, mat_index=LEG))
        for c, r, m in lights:
            lx = px(c) if side < 0 else px(23 - c)
            lib.dome(bm, lx, row(r), 0.17, 0.85 / 12, 0.85 / 12, 0.07, n=10, steps=2, mats=m)

    # Central snout (columns 10-13, rows 16-22) with the red-hot vent across it at rows 18-20.
    snout = [(16, 2.0, 0.1, 0.12), (17.5, 2.0, 0.1, 0.12), (21, 1.6, 0.09, 0.11), (22.4, 1.2, 0.07, 0.1),
             (23.0, 0.0, 0.0, 0.09)]
    common.loft(bm, [(row(r), w / 12, h, z) for r, w, h, z in snout], sides=10, mat_index=LEG)
    common.loft(bm, [(row(17.9), 2.1 / 12, 0.105, 0.12), (row(19.3), 2.15 / 12, 0.11, 0.12),
                     (row(20.6), 1.8 / 12, 0.1, 0.115)], sides=10, mat_index=RED)
    lib.dome(bm, 0.0, row(19.4), 0.2, 0.8 / 12, 0.9 / 12, 0.05, n=10, steps=2, mats=CORE)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj, hull], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
