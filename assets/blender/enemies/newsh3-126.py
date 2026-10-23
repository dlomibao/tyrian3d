"""Horseshoe ring (newsh3.shp frame 126): a 3D version of its sprite.

Seen in episode 4 (levels 2 and 6). A steel ring round a tall hole: a rounded arch over the top,
brass bands down both sides, and two bulky blocks of machinery at the bottom with stubby legs,
joined across the bottom by a thin bar. The ring's width follows the sprite all the way round (ray
cast from the hole's centre), it is thickest at the bottom blocks and thinnest at the bar, and its
facets take the sprite's colours under them. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-126.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, ex, ey  # noqa: E402

NAME = "newsh3-126"


def half_height(a):
    s, c = math.sin(a), abs(math.cos(a))
    if s >= 0:
        return 0.11 + 0.025 * (1 - s)
    base = 0.135 + 0.04 * min(1.0, -s * 1.6)
    return base if c > 0.35 else 0.07 + (base - 0.07) * c / 0.35


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.35, roughness=0.45),  # 0 dark steel
        pal(7, metallic=0.35, roughness=0.4),  # 1 mid steel
        pal(10, metallic=0.4, roughness=0.3),  # 2 light steel
        pal(23, metallic=0.6, roughness=0.35),  # 3 brass bands
        pal(21, metallic=0.5, roughness=0.45),  # 4 dark brass
        pal(25, metallic=0.65, roughness=0.3),  # 5 light brass
    ]
    DARK, MID, LIGHT, BRASS, DBRASS, LBRASS = range(6)
    pixels = sprite["frames"][0]["pixels"]
    h, w = len(pixels), len(pixels[0])

    def keep(c, r):
        return 0 <= r < h and 0 <= c < w and pixels[r][c] != -1

    def slot(v):
        if v < 2:
            return None
        if v <= 5 or v == 254:
            return DARK
        if v <= 8:
            return MID
        if v <= 14:
            return LIGHT
        if v <= 22 or v == 164:
            return DBRASS
        if v <= 24:
            return BRASS
        return LBRASS

    bm = bmesh.new()
    # The ring round the hole's centre (pixel edge column 12.5, row 11.5).
    centre = (ex(12.5), ey(11.5))
    prof = lib.radial_profile(keep, 12.5, 11.5, n=60, smooth_passes=0, gap=1.1)
    ring = lib.closed_ring(bm, centre, prof, half_height, sides=10, power=0.7, mat_index=MID, grow=-0.45)
    lib.paint_faces(bm, ring, pixels, slot, under_slot=DARK, min_nz=-0.3)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
