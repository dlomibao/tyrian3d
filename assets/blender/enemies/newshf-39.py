"""Sand dome turret (newshf.shp frames 39, 41): a 3D version of its sprite.

Seen in episodes 1 and 3 (levels 1.10, 1.29, 1.31, 3.21). A shiny tan dome set into a patch of
sand that fills the whole tile, with a red eye on a raised boss looking out of its top, a small
ball on a stalk at its upper right, and a curved barrel that wraps round its lower right and
points down the screen. The two frames only brighten the eye, so one model covers both.

Run: blender --background --python assets/blender/enemies/newshf-39.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b095 as lib  # noqa: E402
import common  # noqa: E402

NAME = "newshf-39"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)

BASE = 0.03  # top of the sand plate
DOME = (10.6, 11.6, 8.4, 7.1, 0.40)  # centre col, row, radius x px, radius y px, height


def dome_z(c, r):
    """Height of the dome's surface over pixel (c, r)."""
    dc, dr, rx, ry, hz = DOME
    t = ((c - dc) / rx) ** 2 + ((r - dr) / ry) ** 2
    return BASE + hz * math.sqrt(max(0.0, 1 - t))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshf39", **kw)  # noqa: E731
    mats = [
        pal(23, metallic=0.0, roughness=0.95),  # 0 sand
        pal(28, metallic=0.5, roughness=0.3),  # 1 dome
        pal(20, metallic=0.4, roughness=0.5),  # 2 dark collar under the dome
        pal(113, metallic=0.3, roughness=0.4),  # 3 eye socket
        pal(118, emission_strength=3.0),  # 4 eye
        pal(125, emission_strength=5.0),  # 5 eye core
        pal(29, metallic=0.5, roughness=0.3),  # 6 ball and boss highlights
        pal(26, metallic=0.5, roughness=0.35),  # 7 barrel
    ]
    SAND, SHELL, COLLAR, SOCKET, EYE, CORE, BALL, BARREL = range(8)
    bm = bmesh.new()

    # Sand plate over the whole tile.
    lib.box(bm, G, 0, 0, 24, 28, 0.0, BASE, mat=SAND)

    # A dark collar where the dome meets the sand, then the dome itself.
    dc, dr, rx, ry, hz = DOME
    lib.ellipsoid(bm, G, dc + 0.4, dr + 0.6, BASE, rx + 0.4, ry + 0.4, 0.07, mat=COLLAR, segments=24, rings=8,
                  z_min=BASE)
    lib.ellipsoid(bm, G, dc, dr, BASE, rx, ry, hz, mat=SHELL, segments=28, rings=14, z_min=BASE)

    # Raised boss round the eye (its lit upper left and shadowed lower right ring the eye).
    ec, er = 9.4, 11.3
    lib.ellipsoid(bm, G, ec + 0.6, er + 0.6, dome_z(ec, er) - 0.06, 4.8, 4.6, 0.1, mat=SHELL, segments=20, rings=8)
    lib.ellipsoid(bm, G, ec, er, dome_z(ec, er) + 0.02, 2.9, 2.8, 0.05, mat=SOCKET, segments=16, rings=6)
    lib.ellipsoid(bm, G, ec, er, dome_z(ec, er) + 0.03, 2.3, 2.2, 0.055, mat=EYE, segments=16, rings=6)
    lib.ellipsoid(bm, G, ec - 0.1, er - 0.1, dome_z(ec, er) + 0.06, 1.0, 1.0, 0.04, mat=CORE, segments=10, rings=5)

    # Ball on a short stalk at the upper right (columns 15-18, rows 3-6).
    lib.sweep(bm, G, [(13.8, 7.2, dome_z(13.8, 7.2) - 0.03, 0.9, 0.05), (15.6, 5.6, 0.2, 0.8, 0.045)],
              sides=8, mat=BARREL)
    lib.ellipsoid(bm, G, 16.6, 4.6, 0.21, 1.7, 1.6, 0.13, mat=BALL, segments=12, rings=6)

    # Curved barrel: out of the dome's lower right, round under it and straight down the screen.
    path = [(16.2, 14.8, 0.24, 1.1, 0.07), (14.6, 16.6, 0.2, 1.2, 0.075), (12.4, 18.1, 0.16, 1.2, 0.075),
            (10.8, 19.4, 0.13, 1.1, 0.07), (10.4, 21.0, 0.11, 1.0, 0.065), (10.4, 23.4, 0.1, 1.0, 0.065),
            (10.4, 23.9, 0.1, 0.0, 0.0)]
    lib.sweep(bm, G, path, sides=10, mat=BARREL)
    # A muzzle ring near its end.
    lib.sweep(bm, G, [(10.4, 22.4, 0.1, 1.25, 0.08), (10.4, 23.2, 0.1, 1.25, 0.08)], sides=10, mat=BALL)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], f"enemies/{NAME}", sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
