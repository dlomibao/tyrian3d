"""Grey claw with a fire jet (newsh3.shp frames 8 and 46): a 3D version of its sprite.

Seen in episode 4 (levels 2, 6 and 10). Two curved grey blades, one above the other, sweep left
from a short spine on the right to sharp tips, like a pair of pincers seen from above; a thin rod
joins the spine's two halves, a red and orange flame jets left from it between the blades and a
small red glow comes out of its right side. The two frames only flicker the flame, so one model
covers both.

Run: blender --background --python assets/blender/enemies/newsh3-8.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b052 as lib  # noqa: E402
from lib_b052 import P, X, Y  # noqa: E402

NAME = "newsh3-8"
MIRROR_ROW = 13.0  # the blades mirror each other about this row edge

# Upper blade along the columns: (col edge, row centre, half width px, half height px, z px).
BLADE = [
    (0.1, 7.5, 0.0, 0.0, 0.0),
    (0.6, 7.5, 0.5, 0.35, 0.0),
    (3.0, 7.0, 1.0, 0.7, 0.0),
    (5.0, 6.5, 1.6, 1.0, 0.1),
    (7.5, 6.1, 1.9, 1.2, 0.2),
    (10.0, 6.1, 2.2, 1.4, 0.3),
    (13.0, 6.4, 2.6, 1.7, 0.4),
    (16.0, 6.6, 2.6, 1.8, 0.4),
    (18.5, 6.8, 2.1, 1.6, 0.3),
    (20.5, 7.0, 1.7, 1.4, 0.2),
    (22.3, 7.5, 1.5, 1.1, 0.1),
    (23.0, 7.6, 1.0, 0.7, 0.0),
    (23.2, 7.6, 0.0, 0.0, 0.0),
]

# The spine down the right side, along the rows: (row edge, col centre, half width, half height, z).
SPINE = [
    (7.5, 16.5, 2.6, 1.6, 0.0),
    (9.0, 16.6, 3.0, 1.8, 0.0),
    (10.4, 17.4, 2.4, 1.6, 0.0),
    (11.3, 19.2, 1.5, 1.3, 0.0),
    (13.0, 19.5, 1.3, 1.2, 0.0),
    (14.7, 19.2, 1.5, 1.3, 0.0),
    (15.6, 17.4, 2.4, 1.6, 0.0),
    (17.0, 16.6, 3.0, 1.8, 0.0),
    (18.5, 16.5, 2.6, 1.6, 0.0),
]


def grey_slot(i):
    """Material slot for a grey sprite pixel (palette 1-12, dark to light)."""
    if i < 1 or i > 12:
        return None
    if i <= 3:
        return 0
    if i <= 6:
        return 1
    if i <= 8:
        return 2
    return 3


def mirror_y_from(bm, start, row_edge):
    """Duplicate the geometry added since vertex `start`, mirrored about a row edge (faces flipped)."""
    y0 = Y(row_edge)
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start:]
    faces = {f for v in verts for f in v.link_faces}
    vmap = {v: bm.verts.new((v.co.x, 2 * y0 - v.co.y, v.co.z)) for v in verts}
    for f in faces:
        bm.faces.new([vmap[v] for v in reversed(f.verts)]).material_index = f.material_index


def build(sprite, frame):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(3, metallic=0.35, roughness=0.5),  # 0 dark grey
        pal(5, metallic=0.35, roughness=0.45),  # 1 grey
        pal(7, metallic=0.35, roughness=0.4),  # 2 light grey
        pal(10, metallic=0.35, roughness=0.3),  # 3 highlights
        pal(117, roughness=0.4, emission_strength=3.0),  # 4 red flame
        pal(121, roughness=0.4, emission_strength=4.0),  # 5 orange flame core
        pal(123, roughness=0.3, emission_strength=5.0),  # 6 yellow hot spot
        pal(119, roughness=0.4, emission_strength=3.0),  # 7 red glow on the right
    ]
    DARK, FLAME, CORE, SPOT, GLOW = 0, 4, 5, 6, 7
    bm = bmesh.new()

    # The grey frame: upper blade, its mirror below and the spine, coloured from the sprite.
    start = len(bm.verts)
    lib.loft_x(bm, BLADE, sides=10, mat=2)
    mirror_y_from(bm, start, MIRROR_ROW)
    lib.loft(bm, SPINE, sides=10, mat=2)
    lib.paint(bm, sprite["frames"][frame]["pixels"], grey_slot, under_slot=DARK, min_nz=-0.1)

    # The flame jetting left between the blades (rows 11-15, from the rod to column 4).
    lib.loft_x(bm, [
        (3.8, 14.3, 0.0, 0.0, 0.0),
        (5.5, 14.1, 0.7, 0.5, 0.0),
        (7.5, 13.9, 1.1, 0.8, 0.0),
        (10.5, 13.4, 1.8, 1.1, 0.0),
        (13.0, 13.0, 2.1, 1.3, 0.0),
        (15.5, 12.9, 1.6, 1.0, 0.0),
        (18.4, 13.0, 1.0, 0.8, 0.0),
    ], sides=10, mat=FLAME)
    lib.loft_x(bm, [
        (8.0, 13.4, 0.0, 0.0, 0.5),
        (10.5, 13.2, 0.8, 0.6, 0.6),
        (13.5, 12.8, 1.1, 0.7, 0.6),
        (16.5, 12.9, 0.7, 0.5, 0.4),
        (17.5, 13.0, 0.0, 0.0, 0.3),
    ], sides=8, mat=CORE)
    lib.ellipsoid(bm, X(14.0), Y(12.6), P(0.9), P(1.1), P(0.7), P(0.5), segments=8, rings=4, mat=SPOT)

    # The small red glow out of the rod's right side (columns 21-23).
    lib.loft_x(bm, [
        (19.8, 13.5, 1.3, 0.9, 0.0),
        (22.3, 13.5, 1.0, 0.7, 0.0),
        (24.0, 13.5, 0.0, 0.0, 0.0),
    ], sides=8, mat=GLOW)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [obj]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
