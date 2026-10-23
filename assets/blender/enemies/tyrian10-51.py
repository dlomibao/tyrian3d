"""Blue gem (tyrian.shp#10 frames 51-55): a 3D version of its sprite.

Seen in episodes 1, 2 and 4. The 12x14 sprite draws a cut gem from above: a diamond-shaped
outline (columns 1-11, rows 2-12) with bright ridges running from the centre to its four points
(column 6 and row 7), lighter upper facets and darker lower ones. The five frames only brighten it
step by step (a pulse), so one model covers them all: a faceted gem with a low pavilion resting on
the ground, a girdle shaped like the sprite's outline and a crown rising to a glowing centre, its
ridges on the axes and its facets coloured by quadrant as in the sprite.

Run: blender --background --python assets/blender/enemies/tyrian10-51.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b106 as lib  # noqa: E402
from lib_b106 import common, ex, ey  # noqa: E402

NAME = "tyrian10-51"
CX, CY = ex(6.5, 12), ey(7.5, 14)  # the gem's centre (column 6, row 7)
R = 5.8 / 12  # centre to each point


def girdle(scale, z):
    """The outline: a diamond with blunt points, 12 points counter-clockwise from +X (every third on an axis)."""
    pts = []
    for k in range(4):
        a = math.pi / 2 * k
        c, s = math.cos(a), math.sin(a)
        for u, v in ((0.95, 0.0), (0.84, 0.14), (0.14, 0.84)):
            # (u, v) in the quadrant's frame: along this axis and the next.
            x = u * c - v * s
            y = u * s + v * c
            pts.append((CX + scale * R * x, CY + scale * R * y, z))
    return pts


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(57, metallic=0.2, roughness=0.25),  # 0 upper-left facets
        pal(56, metallic=0.2, roughness=0.25),  # 1 upper-right facets
        pal(53, metallic=0.2, roughness=0.25),  # 2 lower-left facets
        pal(54, metallic=0.2, roughness=0.25),  # 3 lower-right facets
        pal(59, metallic=0.2, roughness=0.1, emission_strength=1.2),  # 4 ridges
        pal(61, metallic=0.1, roughness=0.1, emission_strength=3.0),  # 5 glowing centre
        pal(49, metallic=0.2, roughness=0.3),  # 6 pavilion underneath
    ]
    UL, UR, LL, LR, RIDGE, CORE, UNDER = range(7)

    bm = bmesh.new()
    # Pavilion (base at z = 0) up to the girdle, then the crown in two tiers to the centre.
    star = []
    for p in girdle(0.48, 0.0):
        star.append(p)
    star = [(x, y, 0.25 if i % 3 == 0 else 0.21) for i, (x, y, _) in enumerate(star)]
    rings = [girdle(0.62, 0.0), girdle(1.0, 0.07), girdle(1.0, 0.1), star, girdle(0.14, 0.31)]
    verts = lib.ring_loft(bm, rings, 0, cap_start=True, cap_end=False)
    # Close the top with a little glowing table.
    top = bm.faces.new(verts[-1])
    top.material_index = CORE
    # Colour by quadrant; the pavilion and the girdle band are the dark underside.
    for f in bm.faces:
        if f is top:
            continue
        c = f.calc_center_median()
        if c.z < 0.085:
            f.material_index = UNDER
            continue
        dx, dy = c.x - CX, c.y - CY
        f.material_index = (UL if dx < 0 else UR) if dy > 0 else (LL if dx < 0 else LR)
    gem = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # Bright ridges from the centre to the four points (column 6 and row 7 in the sprite).
    bm = bmesh.new()
    g, s, t = girdle(1.0, 0.1), star, girdle(0.14, 0.31)
    for k in range(4):
        i = 3 * k
        lib.polyline_tube(bm, [(x, y, z + 0.002) for x, y, z in (g[i], s[i], t[i])], 0.2 / 12, sides=4,
                          mat_index=RIDGE)
    ridges = common.mesh_object(f"{NAME}_ridges", bm, mats, coll, smooth=True)

    return [(NAME, [gem, ridges], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
