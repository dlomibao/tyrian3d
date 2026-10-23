"""Brown ground turret (newshp.shp frames 13-93 and newsh2.shp 39-131): a 3D version of its sprites.

Seen in episode 1 (levels 1.3, 1.6) and 3. A grey base plate, longer than it is wide, with two
prongs reaching forward either side of the gun and a red lamp at its back; on it a brown turret
block with a long gun (grey sleeve, brown muzzle). The whole turret turns to aim, in eight
directions, so each direction is its own model, exporting the frames that show it (newsh2.shp
repeats newshp.shp's eight directions):

    newshp-13 up-left, -f2 up, -f3 up-right, -f4 left, -f5 right, -f6 down-left, -f7 down,
    -f8 down-right.

The turret is built once pointing up (+Y) about its turret block, then turned and placed on each
direction's turret block.

Run: blender --background --python assets/blender/enemies/newshp-13.py [-- --preview out.png]
(-- previews every direction: <out>.png and newshp-13-f<n>.png beside it).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b067 as lib  # noqa: E402
from lib_b067 import PX, common  # noqa: E402

NAME = "newshp-13"

# (model, aim angle in degrees from +X, turret pivot in pixel-edge coords (col, row), frames).
DIRECTIONS = [
    (NAME, 135, (13.5, 13.25), {("newshp.shp", 13)}),
    (f"{NAME}-f2", 90, (11.75, 13.5), {("newshp.shp", 15), ("newsh2.shp", 45)}),
    (f"{NAME}-f3", 45, (11.5, 13.25), {("newshp.shp", 17), ("newsh2.shp", 93)}),
    (f"{NAME}-f4", 180, (14.5, 12.0), {("newshp.shp", 51), ("newsh2.shp", 39)}),
    (f"{NAME}-f5", 0, (10.5, 12.0), {("newshp.shp", 55), ("newsh2.shp", 43)}),
    (f"{NAME}-f6", -135, (13.5, 11.5), {("newshp.shp", 89), ("newsh2.shp", 129)}),
    (f"{NAME}-f7", -90, (11.5, 12.5), {("newshp.shp", 91), ("newsh2.shp", 41)}),
    (f"{NAME}-f8", -45, (11.5, 11.5), {("newshp.shp", 93), ("newsh2.shp", 131)}),
]


def turret(bm, m):
    """The turret pointing up (+Y), its turret block centred on the origin. Units are pixels / 12."""
    def P(pts):
        return [(x * PX, y * PX) for x, y in pts]

    # Base plate: a dark lower plate and a lighter bevelled top (8 x 11 px behind the prongs).
    body = [(-4.5, -5.6), (4.5, -5.6), (5.6, -4.4), (5.6, 1.4), (4.6, 2.4), (-4.6, 2.4), (-5.6, 1.4), (-5.6, -4.4)]
    lib.prism(bm, P(body), 0.0, 0.07, m[4])
    top = [(x * 0.9, y * 0.92 - 0.1) for x, y in body]
    lib.prism(bm, P(top), 0.07, 0.11, m[6], top=m[7])
    # Prongs reaching forward either side of the gun (columns 8-9 and 13-14 of the up frame).
    for s in (-1, 1):
        prong = [(1.5, 1.5), (3.6, 1.5), (3.6, 5.2), (3.0, 6.2), (1.5, 6.2)]
        if s < 0:
            prong = [(-x, y) for x, y in reversed(prong)]
        lib.prism(bm, P(prong), 0.0, 0.1, m[6], top=m[8])
    # The red lamp at the back.
    lib.frustum(bm, lib.Grid(0, 0), -1.0, 4.0, 1.0, 5.0, 0.1, 0.135, m[116], inset=0.2)
    # Turret block: a rounded brown box, lighter on top, with a dark skirt under it.
    lib.prism(bm, P([(-2.8, -2.4), (2.8, -2.4), (2.8, 2.1), (-2.8, 2.1)]), 0.09, 0.14, m[162])
    n = len(bm.faces)
    common.loft(bm, [(-2.3 * PX, 0.0, 0.0, 0.2), (-2.2 * PX, 2.3 * PX, 0.07, 0.17),
                     (1.7 * PX, 2.3 * PX, 0.07, 0.17), (1.9 * PX, 0.0, 0.0, 0.2)], sides=10, mat_index=m[22])
    lib.set_smooth(bm, n)
    lib.dome(bm, -0.3 * PX, 0.0, 0.2, 1.4 * PX, 1.6 * PX, 0.04, m[25], segs=10, rings=2)
    # The gun: grey sleeve out of the block, brown muzzle.
    lib.tube(bm, (0, 1.5 * PX, 0.18), (0, 7.0 * PX, 0.18), 0.75 * PX, sides=8, mat=m[8])
    lib.tube(bm, (0, 6.8 * PX, 0.18), (0, 10.4 * PX, 0.18), 0.6 * PX, sides=8, mat=m[24], radius1=0.5 * PX)


def build(sprite):
    g = lib.Grid(24, 28)
    m = lib.Mats(sprite, NAME, metallic=0.45, roughness=0.45)
    m.add(116, emission_strength=3.0)
    models = []
    for model, angle, (pc, pr), frames in DIRECTIONS:
        coll = common.reset_collection(model)
        bm = bmesh.new()
        turret(bm, m)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((g.x(pc), g.y(pr), 0))
                            @ Matrix.Rotation(math.radians(angle - 90), 4, "Z"), verts=bm.verts)
        obj = lib.to_object(model, bm, m.list, coll)
        models.append((model, [obj], lib.subset(sprite, frames)))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
