"""Red blob (newsh3.shp frames 128, 130, 132): a 3D version of its sprite.

Seen in episode 4 (level 4.6), on the ground. A big glossy dark-red dome, wider than it is deep,
with a white-hot spot glowing through its upper left behind a yellow and orange halo, a brighter
red rim catching the light down its right side, and a spill of red goo and droplets round its
foot. The three frames only bob the dome a pixel and move the droplets, so one model covers
them all.

Run: blender --background --python assets/blender/enemies/newsh3-128.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b076 as lib  # noqa: E402

NAME = "newsh3-128"
ROOT = common.repo_root(__file__)
F = lib.Frame(24, 28)
U = lib.U

# The dome: centre (pixel edges), radii in px, height.
DC, DR, RX, RY, RZ = 11.5, 11.9, 10.5, 8.6, 0.46


def dome_z(c, r):
    t = 1 - ((c - DC) / RX) ** 2 - ((r - DR) / RY) ** 2
    return RZ * math.sqrt(max(0.0, t))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(114, metallic=0.1, roughness=0.18),  # 0 dark red dome
        pal(112, metallic=0.0, roughness=0.4),  # 1 darkest red goo
        pal(115, metallic=0.1, roughness=0.2),  # 2 lit rim
        pal(116, metallic=0.0, roughness=0.3),  # 3 red droplets
        pal(122, emission_strength=3.0),  # 4 orange halo
        pal(125, emission_strength=4.0),  # 5 yellow halo
        pal(127, emission_strength=5.0),  # 6 white-hot spot
        pal(118, metallic=0.0, roughness=0.3, emission_strength=1.5),  # 7 bright droplets
    ]
    DOME, GOO, RIM, DROP, HALO, GLOW, HOT, BRIGHT = range(8)
    bm = bmesh.new()

    # The dome.
    lib.ellipsoid(bm, (F.ex(DC), F.ey(DR), 0.0), (RX * U, RY * U, RZ), DOME, segments=24, rings=12, z_min=0.0)

    # The bright rim down its right side: a thin band hugging the surface from row 7 to row 18.
    pts = []
    for k in range(13):
        a = math.radians(-60 + k * 9.5)  # from upper right round to lower right
        c = DC + (RX - 1.4) * math.cos(a)
        r = DR - (RY - 1.2) * math.sin(a)
        pts.append((F.ex(c), F.ey(r), dome_z(c, r) - 0.005))
    radii = [0.5 * U + 0.35 * U * math.sin(math.pi * k / 12) for k in range(13)]
    lib.tube(bm, pts, radii, sides=6, mat=RIM)

    # The hot spot in its upper left (columns 6-10, rows 6-10) with its halo.
    hc, hr = 8.4, 8.4
    z = dome_z(hc, hr)
    lib.ellipsoid(bm, (F.ex(hc), F.ey(hr), z - 0.01), (2.5 * U, 2.4 * U, 0.04), HALO, segments=12, rings=6)
    lib.ellipsoid(bm, (F.ex(hc - 0.2), F.ey(hr + 0.1), z + 0.005), (1.6 * U, 1.5 * U, 0.04), GLOW, segments=10,
                  rings=5)
    lib.ellipsoid(bm, (F.ex(hc - 0.3), F.ey(hr + 0.2), z + 0.02), (1.0 * U, 0.9 * U, 0.035), HOT, segments=8,
                  rings=4)

    # The spill of goo round its foot (rows 17-23) and droplets beyond it.
    lib.ellipsoid(bm, (F.ex(12.0), F.ey(19.6), 0.0), (8.6 * U, 3.0 * U, 0.06), GOO, segments=16, rings=4,
                  z_min=0.0)
    lib.ellipsoid(bm, (F.ex(11.6), F.ey(21.3), 0.0), (2.0 * U, 1.3 * U, 0.05), DROP, segments=8, rings=4,
                  z_min=0.0)
    lib.ellipsoid(bm, (F.ex(16.0), F.ey(20.6), 0.0), (2.4 * U, 1.0 * U, 0.05), DROP, segments=8, rings=4,
                  z_min=0.0)
    for c, r, sx, sy, mat in ((3.8, 23.0, 1.2, 1.4, BRIGHT), (8.8, 24.6, 1.6, 0.9, BRIGHT),
                              (10.8, 25.5, 0.9, 0.9, DROP), (16.5, 24.6, 1.2, 0.9, BRIGHT),
                              (21.6, 22.8, 1.0, 1.2, DROP), (20.6, 20.6, 0.9, 0.9, BRIGHT),
                              (1.8, 18.4, 1.0, 1.4, BRIGHT)):
        lib.ellipsoid(bm, (F.ex(c), F.ey(r), 0.0), (sx * U, sy * U, 0.04), mat, segments=8, rings=3,
                      z_min=0.0)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run(ROOT, NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)


if __name__ == "__main__":
    main()
