"""Grey capsule with a glowing core (newshk.shp frame 276): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A fat grey barrel lying up the screen, its ends chamfered so it
reads as an octagon from above, shaded in stripes along its length and ringed by a dark groove
round its middle. A raised band runs down its centre: plain at the ends, with grilles of three
slats either side of a glowing red-orange core across the groove. A rectangular loop handle
sticks out of each end.

Run: blender --background --python assets/blender/enemies/newshk-276.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b045 as lib  # noqa: E402
from lib_b045 import U, common, ex, ey  # noqa: E402

NAME = "newshk-276"
HZ = 0.22  # the barrel's half height in the middle

# Palette index of each column's stripe along the barrel (row 10 of the sprite); the centre
# band (columns 9-15) is built on top.
STRIPES = [9, 9, 9, 12, 10, 10, 7, 11, 10, 10, 10, 10, 10, 10, 10, 10, 5, 8, 6, 10, 10, 5, 6, 3]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    used = sorted(set(STRIPES) | {3, 4, 12, 13, 14})
    mats = [pal(i, metallic=0.4, roughness=0.4) for i in used]
    slot = {i: k for k, i in enumerate(used)}
    mats += [pal(113, metallic=0.4, roughness=0.5), pal(121, emission_strength=3.0),
             pal(125, emission_strength=5.0)]
    RIM, GLOW, HOT = range(len(used), len(used) + 3)
    DARK, GROOVE, BAND, SLAT, BAND_HI = slot[3], slot[4], slot[11], slot[13], slot[14]
    bm = bmesh.new()

    # The barrel: rings of a squarish profile, one node per column edge across the top.
    def profile(w, hz):
        top = []
        for k in range(25):
            x = (k - 12) / 12
            z = hz * max(0.0, 1 - x * x) ** 0.35
            top.append((x * w / 12, z))
        bottom = []
        for k in range(1, 6):
            a = math.pi * k / 6
            bottom.append((math.cos(a) * w / 12, -hz * 0.75 * math.sin(a)))
        return list(reversed(top)) + bottom  # right to left over the top, back under

    seg_mats = list(reversed([slot[i] for i in STRIPES])) + [slot[5]] * 6
    sections = [(3.2, 4.5), (4.0, 7.5), (5, 8.5), (6, 9.5), (7, 10.5), (8, 11.5), (9, 12), (12.9, 12),
                (13.1, 11.2), (13.9, 11.2), (14.1, 12), (19, 12), (20, 11.5), (21, 10.5), (22, 9.5),
                (23, 8.5), (24, 7.5), (24.8, 4.5)]
    rings, band_mats = [], []
    for k, (r, w) in enumerate(sections):
        hz = HZ * min(1.0, (w / 12) ** 0.6)
        if 13 < r < 14:
            hz *= 0.92
        rings.append([(x, ey(r), z) for x, z in profile(w, hz)])
        if k:
            groove = 13 < (r + sections[k - 1][0]) / 2 < 14
            band_mats.append([GROOVE] * len(seg_mats) if groove else seg_mats)
    f0 = len(bm.faces)
    lib.ring_loft(bm, rings, band_mats, cap_mats=(DARK, DARK))
    lib.set_smooth(bm, f0)

    # Centre band (columns 9-15): plain blocks at the ends, grilles of three slats each side of
    # the core.
    x0, x1 = ex(9), ex(16)
    lib.bevel_prism(bm, [(x0, ey(24.2)), (x1, ey(24.2)), (x1, ey(3.8)), (x0, ey(3.8))], 0.08, 0.25, 0.02,
                    mat_index=DARK)
    for r0, r1 in ((3.6, 7.0), (21.0, 24.4)):
        lib.bevel_prism(bm, [(x0, ey(r1)), (x1, ey(r1)), (x1, ey(r0)), (x0, ey(r0))], 0.1, 0.3, 0.025,
                        mat_index=BAND_HI, side_mat=BAND)
    for r0, r1 in ((7.0, 11.4), (16.6, 21.0)):
        for c in (10, 12, 14):
            lib.bevel_prism(bm, [(ex(c), ey(r1)), (ex(c + 1), ey(r1)), (ex(c + 1), ey(r0)), (ex(c), ey(r0))],
                            0.2, 0.29, 0.012, mat_index=SLAT, side_mat=BAND)

    # The core: a glowing drum across the band (rows 12-15) in a dark red rim, hot in the middle.
    lib.box(bm, x0, ey(16.6), x1, ey(11.4), 0.1, 0.24, RIM)
    f0 = len(bm.faces)
    lib.loft_x(bm, [(ex(9.2), 1.6 * U, 0.05), (ex(15.8), 1.6 * U, 0.05)], ey(14), 0.25, sides=10, mat_index=GLOW)
    lib.ellipsoid(bm, (ex(12.5), ey(14), 0.28), (2.2 * U, 1.1 * U, 0.035), sides=10, rings=6, mat_index=HOT)
    lib.set_smooth(bm, f0)

    # Loop handles out of each end (columns 7-17, rows 0-2 and 25-27).
    for flip in (False, True):
        def R(r):
            return ey(28 - r) if flip else ey(r)
        f0 = len(bm.faces)
        lib.loft_x(bm, [(ex(7), 0.75 * U, 0.05), (ex(18), 0.75 * U, 0.05)], R(2.5), 0.1, sides=8,
                   mat_index=slot[12])
        lib.set_smooth(bm, f0)
        for c0, c1 in ((7, 8.2), (16, 18)):
            lo, hi = sorted((R(0.2), R(3.5)))
            lib.box(bm, ex(c0), lo, ex(c1), hi, 0.03, 0.15, slot[7], top_mat=slot[7])
    return [lib.mesh_object_mixed(NAME, bm, mats, coll)]


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
