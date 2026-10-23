"""Molten rock (newshg.shp frames 1-17 and 39-47): a 3D version of its sprite.

Seen in episode 2 (level section 4). A lumpy ball of glowing red rock, white-hot at its upper
left, with orange and yellow lava seams and a few cooled grey flakes. The 14 frames tumble the
same round rock (the seams and flakes move across it, the outline stays a lumpy ball), so one
model covers them all; its surface is painted from the first frame.

Run: blender --background --python assets/blender/enemies/newshg-1.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b034 as lib  # noqa: E402
from lib_b034 import common, ex, ey  # noqa: E402

NAME = "newshg-1"
CX, CY = ex(10.5), ey(12.5)  # the rock spans columns 2-19 and rows 3-21
HALF_H = 0.28


def silhouette_radius(pixels, angle):
    """Distance from the centre to the edge of the frame's filled pixels along `angle`."""
    r, step = 0.0, 0.25 / 12
    last = 0.0
    while r < 1.2:
        if lib.sample(pixels, CX + r * math.cos(angle), CY + r * math.sin(angle)) >= 0:
            last = r
        r += step
    return last + 0.4 / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(113, metallic=0.1, roughness=0.8),  # 0 dark crust
        pal(116, metallic=0.1, roughness=0.7, emission_strength=0.6),  # 1 red rock
        pal(119, roughness=0.6, emission_strength=2.0),  # 2 glowing red
        pal(121, roughness=0.5, emission_strength=3.0),  # 3 orange lava
        pal(123, roughness=0.4, emission_strength=4.0),  # 4 yellow lava
        pal(127, roughness=0.3, emission_strength=5.0),  # 5 white-hot
        pal(70, metallic=0.1, roughness=0.9),  # 6 cooled flake
        pal(112, metallic=0.1, roughness=0.9),  # 7 underside
    ]

    def slot_of(i):
        if i < 0:
            return None
        if i >= 126:
            return 5
        if i >= 122:
            return 4
        if i >= 120:
            return 3
        if i >= 118:
            return 2
        if i >= 115:
            return 1
        if i >= 112:
            return 0
        return 6  # 20, 29, 64-72, 165: grey and brown flakes

    pixels = sprite["frames"][0]["pixels"]
    # A sphere whose poles point along Y (so the top view is an even grid, not a pole star),
    # squashed to the sprite's outline in XY and to HALF_H in Z, with gentle lumps.
    segments, rings = 34, 24
    bm = bmesh.new()
    top = bm.verts.new((CX, CY + silhouette_radius(pixels, math.pi / 2), 0.0))
    bot = bm.verts.new((CX, CY - silhouette_radius(pixels, -math.pi / 2), 0.0))
    grid = []
    for i in range(1, rings):
        th = math.pi * i / rings
        ring = []
        for k in range(segments):
            ph = 2 * math.pi * (k + 0.5) / segments
            ux, uy, uz = math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)
            rad = silhouette_radius(pixels, math.atan2(uy, ux))
            lump = 1.0 + 0.045 * math.sin(i * 2.3 + k * 1.7) * math.sin(k * 0.9 + 0.4) * math.sin(th)
            z = uz * HALF_H * (1.0 if uz > 0 else 0.7) * lump
            ring.append(bm.verts.new((CX + rad * ux * lump, CY + rad * uy * lump, z)))
        grid.append(ring)
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((top, grid[0][j], grid[0][k]))
        bm.faces.new((bot, grid[-1][k], grid[-1][j]))
    for a, b in zip(grid, grid[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    lib.paint(bm, pixels, slot_of, under_slot=7, min_nz=-0.2, spread=0.6 / 12, average=True)
    # The white-hot blister at the upper left (columns 6-10, rows 6-10), standing a little proud.
    lib.ellipsoid(bm, (ex(9.3), ey(8.9), HALF_H * 0.74), (2.4 / 12, 1.9 / 12, 0.1), segments=14, rings=6,
                  mat_index=5, bottom=0.6)
    lib.ellipsoid(bm, (ex(9.3), ey(9.0), HALF_H * 0.68), (3.0 / 12, 2.5 / 12, 0.1), segments=14, rings=6,
                  mat_index=4, bottom=0.6)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
