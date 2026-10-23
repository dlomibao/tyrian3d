"""Spinning arch (newsh2.shp frames 191-205): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. A horseshoe-shaped band, bronze over the top and
grey down the two legs, with a bronze barrel pod hung in the middle on two short struts. The band
is one pixel thick seen face on and five pixels deep (frame 199 shows it edge on), and the eight
frames turn the whole thing about the screen's vertical axis. So the model is built once and
exported eight times, each turned about Y to the angle its frame shows (read off how far apart the
two legs are drawn: 12, 9, 6, 4, 0 pixels, then back out on the other side): newsh2-191 (frame
191), newsh2-191-f2 (193) ... newsh2-191-f8 (205). It spins about column 11.

Run: blender --background --python assets/blender/enemies/newsh2-191.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-191"
AXIS = 11  # the column the arch spins about
DEPTH = 2.25 / 12  # half the band's depth (frame 199 draws it 5 px; the turned frames a little less)
# Leg spacing per frame (px): the angle each frame is turned by is acos(spacing / 12).
SPACING = [12, 9, 6, 4, 0, -4, -6, -9]


def X(c):
    """Sprite column (pixel centre) to X relative to the spin axis."""
    return (c - AXIS) / 12


def build_one(sprite, name, angle):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.6, roughness=0.35),  # 0 grey leg edges
        pal(7, metallic=0.6, roughness=0.4),  # 1 grey leg faces
        pal(27, metallic=0.65, roughness=0.3),  # 2 bronze arch edges
        pal(24, metallic=0.6, roughness=0.35),  # 3 bronze arch faces
        pal(4, metallic=0.5, roughness=0.5),  # 4 dark collars
        pal(25, metallic=0.6, roughness=0.3),  # 5 bronze pod
        pal(22, metallic=0.5, roughness=0.4),  # 6 darker pod bottom
        pal(16, metallic=0.2, roughness=0.5),  # 7 dark nozzle
    ]
    LEG_E, LEG_F, ARCH_E, ARCH_F, COLLAR, POD, POD_LOW, NOZZLE = range(8)
    bm = bmesh.new()

    # The band: centreline through the pixel centres, bottom edge of row 18 up the left leg, over
    # the top (row 2) and down the right leg. Bronze above row 6.5, grey below.
    half = [(5, 18.5), (5, 12.0), (5, 7.0), (5.15, 5.4), (6.0, 4.0), (7.0, 3.0), (8.2, 2.15), (9.6, 2.0)]
    path = [(X(c), lib.row(r)) for c, r in half] + [(0.0, lib.row(2.0))]
    path += [(-x, y) for x, y in reversed(path[:-1])]
    split = lib.ey(7)

    def mat_of(_seg, mid, side):
        arch = mid.y > split
        if side in ("front", "back"):
            return ARCH_E if arch else LEG_E
        return ARCH_F if arch else LEG_F

    lib.ribbon(bm, path, 0.5 / 12, DEPTH, mat_of)

    # Dark collars round both legs at rows 7 and 12.
    for c in (5, 17):
        for r in (7, 12):
            x0, y0 = X(c), lib.row(r)
            w, d, h = 0.75 / 12, DEPTH + 0.2 / 12, 0.5 / 12
            ring_lo = [(x0 - w, y0 - h, -d), (x0 + w, y0 - h, -d), (x0 + w, y0 - h, d), (x0 - w, y0 - h, d)]
            ring_hi = [(x, y0 + h, z) for x, _, z in ring_lo]
            lib.ring_loft(bm, [ring_lo, ring_hi], COLLAR)

    # Struts from the legs to the pod (row 10).
    for s in (-1, 1):
        lib.tube(bm, (s * 5.4 / 12, lib.row(10), 0), (s * 2.0 / 12, lib.row(10), 0), 0.45 / 12, sides=6,
                 mat_index=LEG_F)

    # The pod: a round barrel five pixels across, rows 7-13, rounded at the bottom.
    sections = [(6.55, 1.6), (6.9, 2.3), (7.6, 2.55), (11.8, 2.55), (12.6, 2.2), (13.3, 1.5), (13.7, 0.7)]
    rings = [lib.ellipse_ring(0, 0, 0, r / 12, r / 12, n=12) for _, r in sections]
    rings = [[(x, lib.row(sr), y) for x, y, _ in ring] for (sr, _), ring in zip(sections, rings)]
    rings = [[(0.0, lib.row(6.5), 0.0)]] + rings + [[(0.0, lib.row(13.85), 0.0)]]
    band_mats = [POD] * 4 + [POD_LOW] * 3 + [NOZZLE]
    lib.ring_loft(bm, rings, band_mats, smooth=True)

    # Turn it about the spin axis and put the axis on column 11.
    bmesh.ops.transform(bm, matrix=Matrix.Translation((lib.px(AXIS), 0, 0)) @ lib.rot_y(angle), verts=bm.verts)
    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build_one(sprite, name, math.acos(SPACING[k] / 12))
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
