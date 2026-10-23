"""Beer mug (tyrian.shp#10 frame 241): a 3D version of its sprite.

Seen in episode 1 (level section 41). The sprite draws a fluted glass tankard from the side,
mouth up the screen: grey glass at the top, brown beer below a pale foam line, a darker base, and
a grey loop handle on the right. In 3D it lies on its side in the screen plane: a ten-sided
fluted body along Y (the bright stripes are the flutes' ridges), open at the mouth, with the handle
as a round loop beside it. The near-black pixels to the right of and below the mug (indices 160
and 161) are its drop shadow and the dark ring round it is outline; neither is modelled.

Run: blender --background --python assets/blender/enemies/tyrian10-241.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b021 as lib  # noqa: E402
from lib_b021 import common, ey, px, row  # noqa: E402

NAME = "tyrian10-241"
CX = (11 - 12) / 12  # the body's centre line: columns 5-16
W = 6.0 / 12  # body half width (12 px)
H = 3.4 / 12  # body half height (out of the screen)
SIDES = 10


def ring(y, s=1.0):
    """A ring round the body at height y, scaled by s, with a vertex on top (a flute ridge)."""
    pts = []
    for i in range(SIDES):
        a = 2 * math.pi * (i + 0.5) / SIDES  # vertex 2 is at 90 degrees
        pts.append((CX + s * W * math.cos(a), y, s * H * math.sin(a)))
    return pts


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.45, roughness=0.15),  # 0 grey glass
        pal(23, metallic=0.1, roughness=0.3),  # 1 beer
        pal(27, metallic=0.1, roughness=0.5),  # 2 foam line
        pal(24, metallic=0.2, roughness=0.35),  # 3 base
        pal(13, metallic=0.5, roughness=0.15),  # 4 bright lip
        pal(3, metallic=0.2, roughness=0.6),  # 5 dark inside
    ]
    GLASS, BEER, FOAM, BASE, LIP, INSIDE = range(6)

    # Body from the base (row 20) to the mouth (row 6), then back in and down into the mug.
    bm = bmesh.new()
    rings = [ring(ey(21), 0.88), ring(ey(20.6)), ring(ey(19.8)), ring(ey(13)), ring(ey(12.1), 1.02),
             ring(ey(11.9)), ring(ey(6.5)), ring(ey(6.1), 1.03), ring(ey(6.0), 0.84), ring(ey(7.5), 0.8)]
    lib.ring_loft(bm, rings, [BASE, BASE, BEER, FOAM, FOAM, GLASS, LIP, LIP, INSIDE],
                  cap_mats=(BASE, INSIDE))
    body = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # Smooth parts: the flutes' bright ridges and the handle.
    smats = [
        pal(15, metallic=0.4, roughness=0.12),  # 0 glass highlight
        pal(29, metallic=0.1, roughness=0.25),  # 1 beer highlight
        pal(9, metallic=0.55, roughness=0.25),  # 2 handle grey
        pal(12, metallic=0.55, roughness=0.2),  # 3 handle highlight
    ]
    HI_GLASS, HI_BEER, HANDLE, HANDLE_HI = range(4)
    bm = bmesh.new()
    r = 0.35 / 12
    # Ridges at 54, 90 and 126 degrees: columns 14, 11 and 8 in the sprite.
    for a in (54, 90, 126):
        x = CX + W * math.cos(math.radians(a))
        z = H * math.sin(math.radians(a))
        lib.tube(bm, (x, ey(11.8), z), (x, ey(6.6), z), r, sides=6, mat_index=HI_GLASS)
        lib.tube(bm, (x, ey(19.8), z), (x, ey(12.4), z), r, sides=6, mat_index=HI_BEER)

    # The handle: a loop from the glass (row 9) out to column 20 and back to the beer (row 18).
    loop = [(px(15.6), row(9.2), 0.0), (px(18.3), row(9.3), 0.0), (px(19.6), row(10.3), 0.0),
            (px(20.0), row(11.8), 0.0), (px(20.0), row(16.2), 0.0), (px(19.5), row(17.5), 0.0),
            (px(18.2), row(18.2), 0.0), (px(15.6), row(18.2), 0.0)]
    lib.polyline_tube(bm, loop, 0.85 / 12, sides=8, mat_index=HANDLE)
    lib.polyline_tube(bm, [(x, y, 0.055) for x, y, _ in loop[2:6]], 0.35 / 12, sides=6, mat_index=HANDLE_HI)
    parts = common.mesh_object(f"{NAME}_parts", bm, smats, coll, smooth=True)

    return [(NAME, [body, parts], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
