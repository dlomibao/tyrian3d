"""Grey horned walker pod (newsh3.shp frame 1): a 3D version of its sprite.

Seen in episode 4 level 2. A dark grey machine: two horn-like plates rise from a crossbar at the
top, leaning in to points, with a vented block between them on short arms; below the crossbar a
round body of two dark pods split down the middle, each with a bright edge, sits in a curved
horseshoe rim. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh3-1.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b052 as lib  # noqa: E402
from lib_b052 import P, X, Y  # noqa: E402

NAME = "newsh3-1"

# Left horn along the rows: (row edge, col centre, half width px, half height px, z px). Its inner
# edge stays at column 7 while the outer edge leans out from column 5 to column 2.
HORN = [
    (0.3, 6.6, 0.0, 0.0, 1.0),
    (1.2, 6.5, 0.6, 0.6, 1.0),
    (3.0, 6.0, 1.1, 0.9, 0.9),
    (5.0, 5.5, 1.6, 1.2, 0.8),
    (7.0, 5.0, 2.1, 1.4, 0.7),
    (9.0, 4.6, 2.6, 1.6, 0.6),
    (12.0, 4.6, 2.6, 1.6, 0.5),
    (13.6, 5.2, 2.1, 1.3, 0.4),
    (14.0, 5.5, 0.0, 0.0, 0.3),
]

# The round lower body's hull: (row edge, col centre, half width, half height, z).
BODY = [
    (14.6, 12.0, 0.0, 0.0, -1.0),
    (15.0, 12.0, 5.0, 1.2, -1.0),
    (16.0, 12.0, 7.0, 1.5, -1.0),
    (17.5, 12.0, 8.0, 1.7, -1.0),
    (20.0, 12.0, 8.0, 1.8, -1.0),
    (22.0, 12.0, 8.0, 1.7, -1.0),
    (23.5, 12.0, 7.0, 1.5, -1.0),
    (24.6, 12.0, 6.0, 1.3, -1.0),
    (25.6, 12.0, 4.5, 1.0, -1.0),
    (26.0, 12.0, 0.0, 0.0, -1.0),
]

# The left pod, a rounded wedge: straight inner edge at column 11, outer edge curving in from
# column 5 to column 8 toward its bottom (rows 15-20).
POD = [
    (14.7, 8.4, 0.0, 0.0, 0.4),
    (15.1, 8.3, 2.0, 1.4, 0.4),
    (16.2, 8.1, 2.9, 2.2, 0.4),
    (17.6, 8.4, 2.6, 2.5, 0.4),
    (18.8, 8.8, 2.2, 2.4, 0.4),
    (19.8, 9.3, 1.7, 2.0, 0.4),
    (20.7, 9.7, 1.2, 1.4, 0.4),
    (21.1, 9.8, 0.0, 0.0, 0.4),
]


def grey_slot(i):
    """Material slot for a sprite pixel: greys 1-15 dark to light; the dark brown outline is darkest."""
    if i in (17, 18) or 1 <= i <= 3:
        return 0
    if i <= 5:
        return 1
    if i <= 7:
        return 2
    if i <= 10:
        return 3
    if i <= 15:
        return 4
    return None


def build(sprite, frame):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(3, metallic=0.15, roughness=0.55),  # 0 dark grey: vents, splits
        pal(5, metallic=0.15, roughness=0.5),  # 1 grey
        pal(7, metallic=0.15, roughness=0.45),  # 2 mid grey
        pal(9, metallic=0.15, roughness=0.4),  # 3 light grey
        pal(12, metallic=0.15, roughness=0.3),  # 4 highlights
    ]
    DARK, GREY, MID, LIGHT, BRIGHT = range(5)
    pixels = sprite["frames"][frame]["pixels"]
    bm = bmesh.new()

    # Horns, mirrored.
    start = len(bm.verts)
    lib.loft(bm, HORN, sides=10, mat=MID, power=0.7)
    lib.mirror_x_from(bm, start)

    # Crossbar (row 12, columns 2-21) and the arms joining the horns to the block (rows 10-12).
    lib.box(bm, 2.6, 11.8, 21.4, 13.6, -1.2, 1.4, mat=MID, bevel=0.4)
    for c0, c1 in ((6.8, 9.6), (14.4, 17.2)):
        lib.box(bm, c0, 9.8, c1, 12.4, -0.8, 1.6, mat=MID, bevel=0.3)

    # The vented block between the horns (columns 10-13, rows 4-11).
    lib.box(bm, 10.0, 4.0, 14.0, 12.2, -1.0, 3.2, mat=MID, bevel=0.5)

    # Necks down to the body (columns 9-10 and 13-14, rows 13-15).
    for c0 in (9.0, 13.0):
        lib.box(bm, c0, 13.0, c0 + 2.0, 15.5, -1.0, 1.0, mat=GREY)

    lib.paint(bm, pixels, grey_slot, under_slot=DARK, min_nz=-0.1)

    # The round body: a dark low hull, a horseshoe rim round its lower half and two pods on top,
    # split down the middle (columns 11-12).
    lib.loft(bm, BODY, sides=14, mat=DARK, power=0.8)
    first = len(bm.faces)
    rim = [(4.7, 16.6, 1.0), (4.7, 20.0, 1.1), (5.6, 22.6, 1.4), (8.0, 23.9, 1.6), (12.0, 24.3, 1.7),
           (16.0, 23.9, 1.6), (18.4, 22.6, 1.4), (19.3, 20.0, 1.1), (19.3, 16.6, 1.0)]
    pts = [(X(c), Y(r), P(0.6)) for c, r, _ in rim]
    lib.tube(bm, pts, [P(w) for _, _, w in rim], sides=8, mat=MID, flat=0.9)
    start = len(bm.verts)
    lib.loft(bm, POD, sides=12, mat=GREY, power=0.85)
    lib.mirror_x_from(bm, start)
    bm.faces.ensure_lookup_table()
    lib.paint(bm, pixels, grey_slot, faces=bm.faces[first:], under_slot=DARK, min_nz=-0.1)

    # Vents on the block (rows 4, 6 and 10-11, columns 11-12), set just above its top.
    for r0, r1 in ((4.2, 5.0), (6.0, 7.0), (10.0, 11.9)):
        lib.box(bm, 11.0, r0, 13.0, r1, 2.6, 3.4, mat=DARK)

    return [common.mesh_object(NAME, bm, mats, coll, smooth=True)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
