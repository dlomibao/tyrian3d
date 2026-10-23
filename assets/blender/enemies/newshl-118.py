"""Red lava lump (newshl.shp 118): a 3D version of its sprite.

Seen in episode 4 (level 45), beside the molten rocks (newshl-115, 116). A dark red egg of rock
about 9 x 10 px, tilted from upper right to lower left, with a hot orange spot near its upper left
and darker crust down its right side. The lump is a lumpy ellipsoid resting on the ground whose
outline follows the sprite's silhouette (each direction from the centre is stretched to the
sprite's edge); its faces take the colour of the sprite pixel under them, the hot spot glowing.

Run: blender --background --python assets/blender/enemies/newshl-118.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b098 as lib  # noqa: E402

NAME = "newshl-118"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][0]["pixels"]
    grid = lib.Grid(12, 14, pixels)
    mats = lib.Mats(NAME, sprite["colors"])
    crust = mats(113, metallic=0.1, roughness=0.75)
    rock = mats(115, metallic=0.1, roughness=0.55)
    red = mats(117, metallic=0.1, roughness=0.45, emission_strength=0.8)
    hot = mats(121, metallic=0.0, roughness=0.4, emission_strength=3.0)

    def slot(i):
        if i <= 113:
            return crust
        if i <= 115:
            return rock
        if i <= 118:
            return red
        return hot

    # The filled area (the 1s are the outline): its centroid is the lump's centre.
    filled = [(c, r) for r, row in enumerate(pixels) for c, v in enumerate(row) if v not in (-1, 1)]
    cc = sum(c for c, _ in filled) / len(filled)
    cr = sum(r for _, r in filled) / len(filled)
    # The outline's radius in 72 directions, smoothed so the pixel steps don't make spikes.
    n = 72
    raw = [lib.mask_radius(pixels, cc, cr, 2 * math.pi * k / n, skip=(-1, 1)) + 0.4 for k in range(n)]
    smooth = [sum(raw[(k + d) % n] for d in range(-4, 5)) / 9 for k in range(n)]

    def radius(angle):
        t = (angle % (2 * math.pi)) / (2 * math.pi) * n
        k = int(t)
        f = t - k
        return smooth[k % n] * (1 - f) + smooth[(k + 1) % n] * f

    base = 4.8
    cx, cy = grid.x(cc), grid.y(cr)
    rz = 0.24
    cz = rz * 0.85

    def shape(x, y, z):
        flat = math.hypot(x, y)
        stretch = radius(math.atan2(y, x)) / base if flat > 1e-6 else 1.0
        wobble = 1 + 0.03 * math.sin(3.4 * x + 0.6) * math.cos(3.1 * y - 1.2) + 0.03 * math.sin(4.7 * z + 2.1 * y)
        # Stretch sideways to the sprite's outline; the top stays where it is.
        return (1 + (stretch - 1) * flat) * wobble

    first = lib.cube_blob(bm := bmesh.new(), (cx, cy, cz), (base * U, base * U, rz), n=9, mat_index=rock,
                          bump=shape)
    lib.paint(bm, first, grid, slot, up_only=True)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
