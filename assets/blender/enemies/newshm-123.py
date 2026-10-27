"""Steel walker (newshm.shp frames 123, 125, 127): a 3D version of its sprite.

A ground enemy in episode 2 (levels 10 and 19), seen from above: a hooded head at the top with
a dark visor slot, a dark spine flanked by two pairs of blue lights, broad shoulders with
rounded pads, and a long rounded body below. As it walks the shoulders and body spread a pixel
each side (frame 125), the light moves from one shoulder pad to the other and the hood's lit crown
turns a pixel right each frame, so one model covers them all with a body, shoulders and crown per
frame (common.frame_part, STEPS).

Run: blender --background --python assets/blender/enemies/newshm-123.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-123"
AXIS = 12.5  # the figure's centre column


def rect(c0, r0, c1, r1):
    """Counter-clockwise outline of the pixel block from column c0 to c1 and row r0 to r1 (edges)."""
    x0, x1 = (c0 - 12) / 12, (c1 - 12) / 12
    y0, y1 = (14 - r1) / 12, (14 - r0) / 12
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def box(bm, flat, c0, r0, c1, r1, z0, z1, mat):
    """A block, its faces recorded in `flat` (face ranges to flat shade)."""
    bm.faces.ensure_lookup_table()
    start = len(bm.faces)
    flat.append((start, start + 6))
    common.slab(bm, rect(c0, r0, c1, r1), z1 - z0, z=(z0 + z1) / 2, mat_index=mat)


def loft_at(bm, col, sections, sides=12, mat=0):
    start = len(bm.verts)
    common.loft(bm, [(lib.Y(r), w / 12, h, z) for r, w, h, z in sections], sides=sides, mat_index=mat)
    common.shift_x(bm, start, lib.X(col))


BODY, LIT, DARK, SLOT, LIGHT, RIDGE = range(6)

# What changes as it walks, per frame: the body's half-width at rows 18.5 and 21 (it spreads a
# pixel each side on 125), the shoulders' outer edges (a pixel wider each side on 125), which
# shoulder pad catches the light (the right one on 123, both on 125, the left one on 127), and
# the hood's lit crown, which turns a pixel right on each frame (column 10, 11, 12).
STEPS = {
    123: dict(body=(3.6, 3.1), shoulders=(6.8, 18.2), pads=(BODY, LIT), crown=0.0),
    125: dict(body=(4.6, 4.0), shoulders=(5.8, 19.2), pads=(LIT, LIT), crown=1.0),
    127: dict(body=(3.6, 3.1), shoulders=(6.8, 18.2), pads=(LIT, BODY), crown=2.0),
}


def build_step(bm, flat, body, shoulders, pads, crown):
    """The parts that move between frames."""
    # Long rounded body below the shoulders (rows 14-24), widest at rows 18-19.
    w18, w21 = body
    loft_at(bm, AXIS, [(14.0, 2.6, 0.13, 0.17), (15.5, 3.0, 0.16, 0.18), (18.5, w18, 0.18, 0.18), (21.0, w21, 0.17, 0.17),
                       (23.3, 2.6, 0.14, 0.15), (24.5, 1.6, 0.08, 0.13), (24.9, 0.0, 0.0, 0.12)], sides=12, mat=BODY)
    # Shoulders (rows 10-14, columns 7-18): a dark frame with a chest block and two round pads.
    c0, c1 = shoulders
    box(bm, flat, c0, 10.6, c1, 14.4, 0.0, 0.30, DARK)
    cx, cy = lib.P(AXIS - 0.3, 12.0)
    lib.dome(bm, cx, cy, 2.6 / 12, 2.4 / 12, 0.18, z=0.28, rings=4, sides=12, mat=BODY)
    for col, mat in ((c0 + 1.2, pads[0]), (c1 - 1.2, pads[1])):
        x, y = lib.P(col, 12.0)
        lib.dome(bm, x, y, 1.6 / 12, 2.0 / 12, 0.16, z=0.26, rings=4, sides=10, mat=mat)
    # Hood's lit crown.
    loft_at(bm, AXIS - 1.2 + crown, [(2.8, 0.0, 0.0, 0.36), (3.4, 1.0, 0.04, 0.38), (4.4, 1.0, 0.04, 0.37),
                                     (5.0, 0.0, 0.0, 0.33)], sides=6, mat=RIDGE)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(56, metallic=0.55, roughness=0.3),  # 0 body steel
        pal(59, metallic=0.55, roughness=0.25),  # 1 lit steel (pads, hood crown)
        pal(54, metallic=0.5, roughness=0.35),  # 2 darker steel (shoulder frame, light posts)
        pal(49, metallic=0.4, roughness=0.5),  # 3 near-black (spine channel, visor slot)
        pal(153, emission_strength=3.5),  # 4 blue lights
        pal(61, metallic=0.6, roughness=0.2),  # 5 highlight ridge
    ]
    bm = bmesh.new()
    flat = []

    # Lit centre ridge of the body (column 12).
    loft_at(bm, 12.2, [(15.8, 0.0, 0.0, 0.33), (16.5, 0.9, 0.04, 0.335), (21.0, 0.8, 0.04, 0.325), (23.5, 0.0, 0.0, 0.28)],
            sides=6, mat=RIDGE)
    # Chest highlight (column 11).
    loft_at(bm, 11.0, [(10.6, 0.0, 0.0, 0.42), (11.2, 0.6, 0.03, 0.44), (12.8, 0.5, 0.03, 0.43), (13.4, 0.0, 0.0, 0.40)],
            sides=6, mat=RIDGE)

    # Spine (rows 6-9, columns 11-14): two steel rails round a dark channel.
    box(bm, flat, 10.6, 5.6, 14.4, 10.6, 0.0, 0.22, SLOT)
    for col in (11.0, 14.0):
        loft_at(bm, col, [(5.6, 0.5, 0.12, 0.17), (10.6, 0.5, 0.12, 0.17)], sides=8, mat=BODY)

    # Blue lights either side of the spine (rows 7 and 9) on short dark posts.
    for side in (-1, 1):
        for row, col_off, r in ((7.0, 3.5, 0.7), (9.0, 4.0, 0.95)):
            col = AXIS + side * col_off
            x, y = lib.P(col, row)
            lib.dome(bm, x, y, (r + 0.35) / 12, (r + 0.25) / 12, 0.14, z=0.0, rings=2, sides=8, mat=DARK)
            lib.dome(bm, x, y, r / 12, r / 12, 0.07, z=0.13, rings=3, sides=8, mat=LIGHT)

    # Hood (rows 2-5, columns 9-16): a rounded cap, lit crown, with the dark visor slot facing down.
    start = len(bm.verts)
    common.loft(bm, [(lib.Y(2.4), 2.4 / 12, 0.10, 0.20), (lib.Y(3.0), 3.4 / 12, 0.17, 0.21),
                     (lib.Y(4.2), 4.0 / 12, 0.19, 0.20), (lib.Y(5.6), 3.9 / 12, 0.17, 0.18)],
                sides=12, mat_index=BODY)
    common.shift_x(bm, start, lib.X(AXIS))
    box(bm, flat, 10.8, 4.9, 14.2, 5.95, 0.10, 0.27, SLOT)

    parts = [lib.finish(NAME, bm, mats, coll, flat_z=1.01, flat_ranges=flat)]
    for frame, step in STEPS.items():
        sbm, sflat = bmesh.new(), []
        build_step(sbm, sflat, **step)
        obj = lib.finish(f"{NAME}-step-{frame}", sbm, mats, coll, flat_z=1.01, flat_ranges=sflat)
        parts.append(common.frame_part(obj, [frame]))
    return parts


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
