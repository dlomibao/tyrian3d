"""Lava rock (newshe.shp frame 233): a 3D version of its sprite.

Seen in episode 1 (level section 16), episode 3 (section 8) and episode 4 (section 31). A lumpy
ball of black crust (columns 4-19, rows 7-21) with a smouldering dark red rim, molten light
showing through cracks across its face, a white-hot vent up and left (columns 7-10, rows 10-13)
and its lower right edge glowing orange. One frame, one model.

The crust's plates stand proud and the glowing cracks sit lower, so the ball reads as a cooling
rock with lava under its skin.

Run: blender --background --python assets/blender/enemies/newshe-233.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b033 as lib  # noqa: E402
from lib_b033 import common, ex, ey, px, row  # noqa: E402

NAME = "newshe-233"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(64, metallic=0.1, roughness=0.9),  # 0 black crust
        pal(113, metallic=0.1, roughness=0.8),  # 1 dark ember red
        pal(116, roughness=0.7, emission_strength=1.0),  # 2 smouldering red
        pal(119, emission_strength=2.5),  # 3 glowing red-orange cracks
        pal(124, emission_strength=4.0),  # 4 yellow-hot
        pal(121, emission_strength=3.0),  # 5 orange glow
        pal(127, emission_strength=6.0),  # 6 white-hot core
    ]
    CRUST, EMBER, RED, GLOW, HOT, ORANGE, WHITE = range(7)
    groups = {CRUST: (1, 64), EMBER: (112, 113, 114), RED: (115, 116, 117), GLOW: (118, 119, 120, 121),
              HOT: (122, 123, 124, 125, 126, 127)}
    mapping = {i: m for m, idx in groups.items() for i in idx}
    pixels = sprite["frames"][0]["pixels"]

    # The ball: columns 4-19 (half width 8 px), rows 7-21 (half height 7.5 px).
    a = (ex(20) - ex(4)) / 2
    b = (ey(7) - ey(22)) / 2
    cy = (ey(7) + ey(22)) / 2
    c = 0.26

    def bump(x, y, z):
        """Crust plates stand proud (with a little lumpiness), glowing cracks sit lower."""
        if z < -0.02:
            return 1.0
        m = mapping.get(lib.sprite_index(pixels, x, y), RED)
        lump = 0.5 + 0.5 * math.sin(x * 37.0 + y * 23.0) * math.cos(y * 31.0 - x * 13.0)
        return {CRUST: 1.0 + 0.04 * lump, EMBER: 0.985, RED: 0.98}.get(m, 0.955)

    bm = bmesh.new()
    faces = lib.ellipsoid(bm, 0.0, cy, a, b, c, rings=18, sides=30, bump=bump)
    lib.paint_from_sprite(faces, pixels, mapping, RED, below=EMBER)
    ell = (0.0, cy, a, b, c)

    # The vent up and left: an orange ring round a yellow-hot pool with a white core.
    vu, vv = px(8.6) / a, (row(11.9) - cy) / b
    lib.oval_on_ellipsoid(bm, ell, vu, vv, 2.7 / 12 / a, 2.4 / 12 / b, ORANGE, lift=0.99)
    lib.oval_on_ellipsoid(bm, ell, vu + 0.02, vv, 2.0 / 12 / a, 1.8 / 12 / b, HOT, lift=0.996)
    lib.oval_on_ellipsoid(bm, ell, vu + 0.03, vv + 0.02, 1.1 / 12 / a, 1.0 / 12 / b, WHITE, lift=1.002)

    # The glowing lower right edge (rows 17-21, columns 12-19): red sweeping into an orange-yellow
    # crescent where it's hottest.
    lib.band_on_ellipsoid(bm, ell, 0.86, 1.0, -115, -12, GLOW, lift=1.0, n=16, steps=3)
    lib.band_on_ellipsoid(bm, ell, 0.92, 0.99, -60, -32, HOT, lift=1.006, n=8, steps=2)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
