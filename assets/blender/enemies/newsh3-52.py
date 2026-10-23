"""Copper shield pod (newsh3.shp frame 52, newshd.shp frame 117): a 3D version of its sprite.

Seen in episode 2 level 8 and episode 4 level 6. A domed copper carapace shaped like a heraldic
shield: three lobes along its top edge (a ring-shaped lug in the middle), a point at the bottom,
pale ribs radiating over the shell and a glowing orange gem in the lower middle where they meet.
Both frames are the same picture, so one model covers them.

Run: blender --background --python assets/blender/enemies/newsh3-52.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b052 as lib  # noqa: E402
from lib_b052 import P, X, Y  # noqa: E402

NAME = "newsh3-52"
POWER = 0.8

# The shell, lofted down the rows: (row edge, centre col, half width px, half height px, z px).
# Widths follow the sprite (outline pixels excluded): full width rows 6-17, narrowing to the point.
SHELL = [
    (5.0, 12.0, 9.2, 1.4, 0.4),
    (6.0, 12.0, 11.0, 2.4, 0.3),
    (8.0, 12.0, 11.0, 2.9, 0.2),
    (12.0, 12.0, 11.0, 3.2, 0.1),
    (16.0, 12.0, 11.0, 3.1, 0.0),
    (18.0, 12.0, 10.6, 2.9, 0.0),
    (19.5, 12.0, 9.6, 2.6, 0.0),
    (21.0, 12.0, 8.4, 2.3, 0.0),
    (22.5, 12.0, 6.6, 1.9, 0.0),
    (23.5, 12.0, 4.6, 1.5, 0.0),
    (24.6, 12.0, 2.8, 1.0, 0.0),
    (25.0, 12.0, 0.0, 0.0, 0.0),
]

# Pale ribs over the shell, as (col, row) pixel edges, from the rim toward the gem.
RIBS = [
    [(3.6, 5.6), (6.2, 8.0), (8.6, 10.6), (10.8, 13.2), (11.8, 15.4)],      # upper left
    [(20.0, 6.4), (17.6, 8.6), (15.2, 11.0), (13.4, 13.4), (12.4, 15.4)],    # upper right
    [(10.6, 8.6), (10.8, 11.0), (11.2, 13.4), (11.8, 15.2)],                 # under the lug, left
    [(13.6, 8.4), (13.4, 11.0), (12.9, 13.4), (12.3, 15.2)],                 # under the lug, right
    [(2.4, 13.4), (4.6, 15.6), (7.6, 15.6), (10.2, 16.2)],                   # lower left, upper
    [(3.0, 18.6), (6.0, 18.8), (8.4, 17.8), (10.2, 17.6)],                   # lower left, lower
    [(20.8, 18.8), (17.8, 18.8), (15.4, 17.8), (13.8, 17.6)],                # lower right
    [(13.4, 19.6), (14.6, 20.8), (15.4, 22.4), (14.6, 23.8)],                # down to the point
]


def _section(y):
    """Interpolate the shell section (col, hw, hh, z in px) at Blender y."""
    rows = [(Y(r), c, hw, hh, z) for r, c, hw, hh, z in SHELL]
    if y >= rows[0][0]:
        return rows[0][1:]
    for (y0, *a), (y1, *b) in zip(rows, rows[1:]):
        if y1 <= y <= y0:
            t = (y0 - y) / (y0 - y1)
            return tuple(u + (v - u) * t for u, v in zip(a, b))
    return rows[-1][1:]


def top(x, y):
    """Height (units) of the shell's upper surface over (x, y)."""
    c, hw, hh, z = _section(y)
    if hw <= 0:
        return P(z)
    u = min(abs(x - X(c)) / P(hw), 1.0)
    return P(z) + P(hh) * (1 - u ** (2 / POWER)) ** (POWER / 2)


def build(sprite, frame):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(73, metallic=0.25, roughness=0.45),  # 0 copper shell
        pal(68, metallic=0.25, roughness=0.55),  # 1 dark copper underside
        pal(78, metallic=0.3, roughness=0.3),  # 2 pale ribs
        pal(75, metallic=0.3, roughness=0.35),  # 3 lobes and lug
        pal(66, metallic=0.2, roughness=0.7),  # 4 the lug's hole
        pal(121, emission_strength=3.5),  # 5 orange gem
        pal(125, emission_strength=5.0),  # 6 yellow gem core
        pal(117, emission_strength=2.5),  # 7 red lower gem
    ]
    SHELLM, UNDER, RIB, LOBE, HOLE, GEM, CORE, RED = range(8)
    bm = bmesh.new()

    lib.loft(bm, SHELL, sides=16, mat=SHELLM, power=POWER)
    # Darker underside.
    bm.normal_update()
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < -0.2:
            f.material_index = UNDER

    # The two side lobes on the top edge (cols 2-6 and 17-21, rows 4-5).
    for c in (4.4, 19.6):
        lib.ellipsoid(bm, X(c), Y(5.4), P(1.2), P(2.7), P(1.9), P(1.6), segments=10, rings=6, mat=SHELLM)

    # The lug in the middle of the top edge: a ring lying on the shell (cols 9-14, rows 3-8).
    lx, ly = X(12.0), Y(6.2)
    lib.ellipsoid(bm, lx, ly + P(0.4), P(0.6), P(2.6), P(2.0), P(1.4), segments=12, rings=6, mat=LOBE)
    lib.torus(bm, lx, ly - P(0.3), top(lx, ly) + P(0.7), P(1.6), P(0.8), major=14, minor=6, mat=LOBE)
    lib.dome(bm, lx, ly - P(0.4), top(lx, ly) + P(0.3), P(0.8), P(0.8), P(0.5), rings=2, sides=10, mat=HOLE)

    # Ribs draped over the shell.
    for rib in RIBS:
        pts, radii = [], []
        for i, (c, r) in enumerate(rib):
            x, y = X(c), Y(r)
            pts.append((x, y, top(x, y) + P(0.15)))
            radii.append(P(0.9) if 0 < i < len(rib) - 1 else P(0.6))
        lib.tube(bm, pts, radii, sides=6, mat=RIB, flat=0.6)

    # The gem (cols 10-13, rows 16-19): orange dome, yellow core up and left, red below.
    gx, gy = X(12.0), Y(18.0)
    gz = top(gx, gy)
    lib.dome(bm, gx, gy, gz - P(0.4), P(2.3), P(2.3), P(2.0), rings=4, sides=14, mat=GEM)
    lib.dome(bm, gx - P(0.4), gy + P(0.6), gz + P(0.6), P(1.0), P(0.9), P(1.0), rings=3, sides=10, mat=CORE)
    lib.dome(bm, gx + P(0.2), gy - P(1.2), gz - P(0.3), P(1.4), P(0.8), P(1.3), rings=3, sides=10, mat=RED)

    return [common.mesh_object(NAME, bm, mats, coll, smooth=True)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
