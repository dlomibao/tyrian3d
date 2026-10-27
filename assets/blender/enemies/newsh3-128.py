"""Red blob (newsh3.shp frames 128, 130, 132): a 3D version of its sprite.

Seen in episode 4 (level 4.6), on the ground. A big glossy dark-red dome, wider than it is deep,
with a white-hot spot glowing through its upper left behind a yellow and orange halo, a brighter
red rim catching the light down its right side, and a spill of red goo and droplets round its
foot. The three frames pulse it: the dome stretches up a pixel at a time and pulls in at the
sides, the hot spot riding up with it, and the droplets splash about. One model covers them all,
with the dome and droplets of each frame (common.frame_part) over the spill, which stays put.

Run: blender --background --python assets/blender/enemies/newsh3-128.py [-- --preview out.png] [--frames dir]
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

# The dome on each frame: centre (pixel edges), radii in px, height, and the hot spot's centre.
# Its foot stays put while it pulses: on 130 its top rises a pixel and its right side pulls in
# one, on 132 its top rises two and both sides pull in one, the hot spot riding up with it.
DOMES = {
    128: (11.5, 11.9, 10.5, 8.6, 0.46, 8.4, 8.4),
    130: (11.0, 11.4, 10.0, 9.1, 0.49, 8.4, 7.4),
    132: (11.5, 10.9, 9.5, 9.6, 0.51, 9.4, 6.4),
}

# Droplets thrown round its foot on each frame: (column, row, px across, px down, bright?).
DROPS = {
    128: [(3.8, 23.0, 1.2, 1.4, True), (8.8, 24.6, 1.6, 0.9, True), (10.8, 25.5, 0.9, 0.9, False),
          (16.5, 24.6, 1.2, 0.9, True), (21.6, 22.8, 1.0, 1.2, False), (20.6, 20.6, 0.9, 0.9, True),
          (1.8, 18.4, 1.0, 1.4, True)],
    130: [(2.0, 17.4, 1.0, 1.4, True), (21.0, 17.9, 1.0, 1.2, True), (5.5, 20.5, 0.9, 0.9, True),
          (19.5, 21.5, 0.9, 0.9, True), (11.5, 24.5, 0.8, 0.8, False), (3.9, 25.7, 1.0, 1.0, False),
          (16.4, 25.2, 1.3, 1.2, False), (12.1, 26.7, 1.1, 0.9, False)],
    132: [(1.8, 15.8, 1.0, 1.3, True), (3.6, 17.5, 0.7, 0.7, False), (3.4, 19.4, 1.4, 0.8, True),
          (0.9, 21.5, 0.9, 1.0, False), (20.6, 18.6, 0.9, 1.0, True), (17.5, 19.5, 0.8, 0.8, True),
          (21.5, 19.6, 0.7, 0.8, False), (7.5, 21.5, 0.8, 0.8, True), (9.5, 23.9, 0.7, 1.3, False),
          (13.7, 23.6, 1.2, 1.2, True), (17.5, 24.5, 0.8, 0.8, False), (4.5, 25.5, 0.7, 0.7, False)],
}


def dome_z(c, r, dome):
    dc, dr, rx, ry, rz = dome[:5]
    t = 1 - ((c - dc) / rx) ** 2 - ((r - dr) / ry) ** 2
    return rz * math.sqrt(max(0.0, t))


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

    # The spill of goo round its foot (rows 17-23), the same on every frame.
    bm = bmesh.new()
    lib.ellipsoid(bm, (F.ex(12.0), F.ey(19.6), 0.0), (8.6 * U, 3.0 * U, 0.06), GOO, segments=16, rings=4,
                  z_min=0.0)
    lib.ellipsoid(bm, (F.ex(11.6), F.ey(21.3), 0.0), (2.0 * U, 1.3 * U, 0.05), DROP, segments=8, rings=4,
                  z_min=0.0)
    lib.ellipsoid(bm, (F.ex(16.0), F.ey(20.6), 0.0), (2.4 * U, 1.0 * U, 0.05), DROP, segments=8, rings=4,
                  z_min=0.0)
    parts = [lib.to_object(NAME, bm, mats, coll)]

    for frame, dome in DOMES.items():
        dc, dr, rx, ry, rz, hc, hr = dome
        bm = bmesh.new()

        # The dome.
        lib.ellipsoid(bm, (F.ex(dc), F.ey(dr), 0.0), (rx * U, ry * U, rz), DOME, segments=24, rings=12, z_min=0.0)

        # The bright rim down its right side: a thin band hugging the surface from row 7 to row 18.
        pts = []
        for k in range(13):
            a = math.radians(-60 + k * 9.5)  # from upper right round to lower right
            c = dc + (rx - 1.4) * math.cos(a)
            r = dr - (ry - 1.2) * math.sin(a)
            pts.append((F.ex(c), F.ey(r), dome_z(c, r, dome) - 0.005))
        radii = [0.5 * U + 0.35 * U * math.sin(math.pi * k / 12) for k in range(13)]
        lib.tube(bm, pts, radii, sides=6, mat=RIM)

        # The hot spot in its upper left (columns 6-10, rows 6-10 on frame 128) with its halo.
        z = dome_z(hc, hr, dome)
        lib.ellipsoid(bm, (F.ex(hc), F.ey(hr), z - 0.01), (2.5 * U, 2.4 * U, 0.04), HALO, segments=12, rings=6)
        lib.ellipsoid(bm, (F.ex(hc - 0.2), F.ey(hr + 0.1), z + 0.005), (1.6 * U, 1.5 * U, 0.04), GLOW,
                      segments=10, rings=5)
        lib.ellipsoid(bm, (F.ex(hc - 0.3), F.ey(hr + 0.2), z + 0.02), (1.0 * U, 0.9 * U, 0.035), HOT, segments=8,
                      rings=4)

        # The droplets beyond the spill.
        for c, r, sx, sy, bright in DROPS[frame]:
            lib.ellipsoid(bm, (F.ex(c), F.ey(r), 0.0), (sx * U, sy * U, 0.04), BRIGHT if bright else DROP,
                          segments=8, rings=3, z_min=0.0)
        parts.append(common.frame_part(lib.to_object(f"{NAME}-{frame}", bm, mats, coll), [frame]))

    return parts


def main():
    lib.run(ROOT, NAME, lambda sprite: [(NAME, build(sprite), sprite["sprites"])], __file__)


if __name__ == "__main__":
    main()
