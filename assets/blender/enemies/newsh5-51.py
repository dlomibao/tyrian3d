"""Molten fireball (newsh5.shp frame 51): a 3D version of its sprite.

Seen in episode 4 (level 4.31). A round, 22 px ball of lava: hot yellow and orange plates split by
dark red cracks. Here it's a flattened ball whose surface takes the sprite's colour under each
face (darkest cracks to white-hot spots, all but the cracks glowing) and whose plates stand a
little proud of the cracks. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh5-51.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b037 as L  # noqa: E402

NAME = "newsh5-51"

def bucket(i):
    """Palette index of a lava pixel to a material slot (None for the outline)."""
    if not 112 <= i <= 127:
        return None
    if i <= 115:
        return 0
    if i <= 118:
        return 1
    if i <= 120:
        return 2
    if i <= 122:
        return 3
    if i <= 124:
        return 4
    return 5


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(115, metallic=0.1, roughness=0.85),  # 0 dark cracks
        pal(118, roughness=0.7, emission_strength=1.5),  # 1 deep red
        pal(120, roughness=0.6, emission_strength=2.0),  # 2 red orange
        pal(122, roughness=0.55, emission_strength=2.5),  # 3 orange
        pal(124, roughness=0.5, emission_strength=3.5),  # 4 yellow
        pal(126, roughness=0.45, emission_strength=5.0),  # 5 white hot
    ]
    pixels = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    cx, cy = L.EX(12.5), L.EY(13.5)
    rxy, rz = 10.6 / 12, 0.29
    L.cube_sphere(bm, (cx, cy, 0.0), (rxy, rxy, rz), cuts=9, mat=2)

    # Hot plates stand proud of the cracks: push each vertex out by the heat of the pixel under it.
    def heat(x, y):
        col = int(math.floor(x * 12 + 12))
        r = int(math.floor(14 - y * 12))
        if 0 <= r < 28 and 0 <= col < 24 and 112 <= pixels[r][col] <= 127:
            return min(max((pixels[r][col] - 112) / 15, 0.0), 1.0)
        return 0.5
    for v in bm.verts:
        h = heat(v.co.x, v.co.y)
        dx, dy = v.co.x - cx, v.co.y - cy
        s = 1.0 + 0.05 * (h - 0.55) if abs(v.co.z) > rz * 0.35 else 1.0
        v.co.x, v.co.y = cx + dx * min(s, 1.0), cy + dy * min(s, 1.0)
        v.co.z *= 1.0 + 0.35 * (h - 0.55)

    L.paint_from_pixels(bm, 0, pixels, bucket)
    return L.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    L.run(__file__, NAME, build)
