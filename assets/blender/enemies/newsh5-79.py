"""Green eye pod (newsh5.shp frame 79): a 3D version of its sprite.

Seen in episode 4 (level 4.20). A round green ball, 20 px across, lit from the top left, with a
deep socket in its lower half: the socket's top wall is in shadow, its lower right wall catches
the light, and a dark glossy lens sits in it with a glint at its top left. Here it's a ball with
a crater pressed into it and a dark dome for the lens. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh5-79.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b037 as L  # noqa: E402

NAME = "newsh5-79"
PX = 1 / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(43, metallic=0.3, roughness=0.35),  # 0 green shell
        pal(34, metallic=0.4, roughness=0.12),  # 1 dark glossy lens
        pal(44, metallic=0.2, roughness=0.2, emission_strength=2.0),  # 2 glint in the lens
    ]
    SHELL, LENS, GLINT = range(3)
    bm = bmesh.new()

    # The ball (columns 3-21, rows 3-21).
    cx, cy = L.EX(12.5), L.EY(12.5)
    r, rz = 9.6 * PX, 0.3
    L.cube_sphere(bm, (cx, cy, 0.0), (r, r, rz), cuts=11, mat=SHELL)

    # The socket (columns 6-18, rows 10-21): press a crater into the top of the ball.
    sx, sy, sr, depth = L.EX(12.4), L.EY(16.0), 5.8 * PX, 0.13
    for v in bm.verts:
        if v.co.z <= 0:
            continue
        d = math.hypot(v.co.x - sx, v.co.y - sy) / sr
        if d < 1.0:
            v.co.z -= depth * (1 - d * d) ** 1.5

    # The lens in the socket, and its glint (columns 10-11, rows 12-13).
    surface = rz * math.sqrt(max(0.0, 1 - ((sx - cx) ** 2 + (sy - cy) ** 2) / r ** 2))
    floor = surface - depth
    L.ellipsoid(bm, (sx, sy + 0.2 * PX, floor + 0.03), (5.0 * PX, 5.0 * PX, 0.075), mat=LENS, segments=20, rings=10)
    L.ellipsoid(bm, (L.EX(11.0), L.EY(13.1), floor + 0.085), (1.2 * PX, 1.0 * PX, 0.03), mat=GLINT,
                segments=10, rings=5)

    return L.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    L.run(__file__, NAME, build)
