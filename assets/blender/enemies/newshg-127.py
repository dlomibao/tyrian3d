"""Hooped orb mine (newshg.shp frames 127, 129, 131): a 3D version of its sprite.

Seen in episode 2 (level sections 4 and 19). A small steel-blue ball with a hoop round it (seen
edge-on from above as the tabs at its sides) and a dark gun port on its lower right face. The
three frames turn the port a little: its dark mouth sits low in the middle on frame 127, a pixel to
the right on 129 and further right with a lighter rim on 131. One model covers them all, with a
mouth per frame (common.frame_part).

Run: blender --background --python assets/blender/enemies/newshg-127.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b034 as lib  # noqa: E402
from lib_b034 import common, ex, ey, px, row  # noqa: E402

NAME = "newshg-127"
CX, CY = ex(13), ey(14)  # the ball spans columns 7-18 and rows 8-19


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(59, metallic=0.5, roughness=0.3),  # 0 ball
        pal(52, metallic=0.5, roughness=0.45),  # 1 hoop
        pal(60, metallic=0.5, roughness=0.25),  # 2 port lip, light band
        pal(49, metallic=0.3, roughness=0.6),  # 3 port mouth
        pal(62, metallic=0.4, roughness=0.15),  # 4 lens glint
        pal(55, metallic=0.5, roughness=0.4),  # 5 equator seam
    ]
    BALL, HOOP, LIP, MOUTH, GLINT, SEAM = range(6)
    bm = bmesh.new()

    # The ball: 12 px across, flattened to keep it low.
    lib.ellipsoid(bm, (CX, CY, 0.0), (5.9 / 12, 5.9 / 12, 0.27), segments=20, rings=10, mat_index=BALL)
    # A seam band round the equator, just proud of the surface.
    lib.polyline_tube(bm, [(CX + 5.95 / 12 * math.cos(a), CY + 5.95 / 12 * math.sin(a), 0.0)
                           for a in (2 * math.pi * k / 20 for k in range(21))], 0.35 / 12, sides=4,
                      mat_index=SEAM, caps=False)

    # The hoop: a band in the X-Z plane, seen edge-on from above as tabs at columns 6 and 19 (rows 13-15).
    # It sinks into the ball over the top so only the side tabs show from above.
    pts = [(CX + 6.6 / 12 * math.cos(a), CY + 0.2 / 12, 0.17 * math.sin(a)) for a in
           (2 * math.pi * k / 24 for k in range(25))]
    lib.polyline_tube(bm, pts, 1.1 / 12, sides=6, mat_index=HOOP, caps=False, flat=0.6)

    # Gun port on the lower right face (columns 12-15, rows 15-18): a lipped socket with a dark mouth.
    pcx, pcy = px(13.3), row(16.4)
    dz = 0.27 * math.sqrt(max(0.0, 1 - ((pcx - CX) ** 2 + (pcy - CY) ** 2) / (5.9 / 12) ** 2))
    lib.ellipsoid(bm, (pcx, pcy, dz - 0.03), (2.3 / 12, 2.1 / 12, 0.07), segments=14, rings=6, mat_index=LIP)
    # Glints on the port's upper-left lip (columns 11-12, row 15) and lower right (column 15, row 18).
    lib.ellipsoid(bm, (px(11.5), row(15.5), dz + 0.015), (1.0 / 12, 0.6 / 12, 0.03), segments=8, rings=4,
                  mat_index=GLINT)
    lib.ellipsoid(bm, (px(15), row(18), dz - 0.05), (0.6 / 12, 0.5 / 12, 0.03), segments=8, rings=4,
                  mat_index=GLINT)
    parts = [common.mesh_object(NAME, bm, mats, coll, smooth=True)]

    # The dark mouth, one per frame: (frame, centre offset from the lip's centre in px, radii in px).
    for frame, dx, dy, rx, ry in ((127, -0.8, -0.5, 1.2, 1.1), (129, 0.2, -0.2, 1.2, 1.1),
                                  (131, 0.8, 0.3, 1.1, 1.0)):
        mbm = bmesh.new()
        lib.ellipsoid(mbm, (pcx + dx / 12, pcy + dy / 12, dz + 0.01), (rx / 12, ry / 12, 0.04), segments=12,
                      rings=4, mat_index=MOUTH)
        parts.append(common.frame_part(common.mesh_object(f"{NAME}-mouth-{frame}", mbm, mats, coll, smooth=True),
                                       [frame]))
    return [(NAME, parts, sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
