"""Domed ring (newsh3.shp frame 195): a 3D version of its sprite.

Seen in episode 4 (levels 4, 31, 36). A thick steel ring, heaviest along its top where a glossy
red dome sits on it, with red lights in its narrow sides and a red emitter set in its bottom. The
ring's width follows the sprite all the way round (ray cast from the hole's centre) and its facets
take the sprite's greys under them. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-195.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, ex, ey  # noqa: E402

NAME = "newsh3-195"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.45, roughness=0.45),  # 0 dark steel
        pal(8, metallic=0.45, roughness=0.4),  # 1 mid steel
        pal(11, metallic=0.5, roughness=0.3),  # 2 light steel
        pal(71, metallic=0.3, roughness=0.4),  # 3 red trim
        pal(72, metallic=0.4, roughness=0.15),  # 4 glossy red dome
        pal(75, roughness=0.3, emission_strength=2.5),  # 5 red lights
    ]
    DARK, MID, LIGHT, RED, DOME, LAMP = range(6)
    pixels = sprite["frames"][0]["pixels"]
    h, w = len(pixels), len(pixels[0])

    def keep(c, r):
        return 7 <= r < h and 0 <= c < w and pixels[r][c] != -1

    def slot(v):
        if v < 0 or v in (1, 16, 64):
            return None
        if v <= 6:
            return DARK
        if v <= 9:
            return MID
        if v <= 14:
            return LIGHT
        return RED

    bm = bmesh.new()
    # The ring, round the hole's centre (pixel edge column 12.5, row 16.5).
    centre = (ex(12.5), ey(16.5))
    prof = lib.radial_profile(keep, 12.5, 16.5, n=40)
    ring = lib.closed_ring(bm, centre, prof, lambda a: 0.1 + 0.05 * max(0.0, math.sin(a)),
                           sides=10, power=0.75, mat_index=DARK, grow=-0.45)
    lib.paint_faces(bm, ring, pixels, slot, under_slot=DARK, min_nz=-0.3)
    lib.set_smooth(bm, 0)

    # The red dome on top (columns 8-16, rows 2-6), sunk into the ring's top.
    lib.ellipsoid(bm, (ex(12.5), ey(4.9), 0.06), (5.0 / 12, 3.6 / 12, 0.19), segments=16, rings=5,
                  mat_index=DOME)
    # Red lights in the sides (columns 3-4 / 20-21, rows 13-15) and the emitter at the bottom
    # (columns 11-13, rows 20-23).
    for c in (4.0, 21.0):
        lib.ellipsoid(bm, (ex(c), ey(14.6), 0.0), (1.2 / 12, 1.8 / 12, 0.1), segments=8, rings=3,
                      mat_index=LAMP)
    lib.ellipsoid(bm, (ex(12.5), ey(21.8), 0.05), (1.6 / 12, 2.0 / 12, 0.1), segments=8, rings=3,
                  mat_index=LAMP)

    obj = lib.mesh_object_mixed(NAME, bm, mats, coll)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
