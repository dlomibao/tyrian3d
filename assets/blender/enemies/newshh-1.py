"""Eye block (newshh.shp frames 1, 3, 39): a 3D version of its sprite.

Seen in episode 2 (level 2.4). A square block of scaly blue-grey stone that fills its whole
tile, with a lumpy tan ring like a flower set into it and a green eye in the ring's dark
socket. The three frames only change the eye's glow (dim on 1, wide open and bright with a
white-hot pupil on 3, dark on 39), so one model covers them all, with an eye for frames 1 and 39
(its colour changes) and a bigger, brighter one for frame 3.

Run: blender --background --python assets/blender/enemies/newshh-1.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b018 as lib  # noqa: E402
from lib_b018 import ex, ey, px, row  # noqa: E402

NAME = "newshh-1"
EYE_C, EYE_R = 12.3, 12.9  # centre of the ring and socket (column, row)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(102, metallic=0.2, roughness=0.75),  # 0 blue-grey stone
        pal(98, metallic=0.2, roughness=0.8),  # 1 dark sides and underside
        pal(107, metallic=0.25, roughness=0.6),  # 2 pale scales
        pal(171, metallic=0.35, roughness=0.45),  # 3 tan ring
        # 4 dark socket, lit dark green round the open eye on frame 3
        common.palette_material(sprite, 32, f"{NAME}_socket", metallic=0.4, roughness=0.3, frames={3: 35}),
        # 5 green eye, dark (socket black) on frame 39
        common.palette_material(sprite, 198, f"{NAME}_eye", metallic=0.1, roughness=0.2, emission_strength=4.0,
                                frames={39: 32}),
        pal(104, metallic=0.4, roughness=0.4),  # 6 grey bezel round the eye
        pal(175, metallic=0.4, roughness=0.35),  # 7 pale lobes of the ring
        pal(201, metallic=0.1, roughness=0.2, emission_strength=5.0),  # 8 wide-open bright green eye
        pal(15, metallic=0.0, roughness=0.2, emission_strength=6.0),  # 9 its white-hot pupil
    ]
    STONE, DARK, SCALE, RING, SOCKET, EYE, BEZEL, LOBE, BRIGHT, PUPIL = range(10)
    bm = bmesh.new()

    # The block: the whole 24x28 tile, bevelled at the top.
    x0, x1, y0, y1 = ex(0), ex(24), ey(28), ey(0)
    b = 0.06

    def rect(inset, z):
        return [(x0 + inset, y0 + inset, z), (x1 - inset, y0 + inset, z), (x1 - inset, y1 - inset, z),
                (x0 + inset, y1 - inset, z)]

    f0 = len(bm.faces)
    lib.ring_loft(bm, [rect(0.0, -0.18), rect(0.0, 0.06), rect(b, 0.06 + b)], mat=STONE, smooth=False)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[f0:]:
        if f.calc_center_median().z < 0.05 and abs(f.normal.z) < 0.5 or f.calc_center_median().z < -0.15:
            f.material_index = DARK
    top = 0.06 + b

    # Pale scales on the stone (short raised streaks where the sprite has its light pixels).
    for c, r0, r1 in ((1, 7.5, 10.5), (2, 17.5, 20.5), (20.5, 20.5, 22.5), (6, 1, 4), (11, 0.5, 3),
                      (18.5, 3, 4.8), (15, 24, 26.5), (6, 23, 27), (21.5, 0.5, 2.5), (1.5, 0.5, 3)):
        lib.tube(bm, [(px(c), row(r0), top - 0.01), (px(c), row((r0 + r1) / 2), top + 0.02),
                      (px(c), row(r1), top - 0.01)], 0.065, sides=6, mat=SCALE, flat=0.35)

    # The tan ring: a lumpy torus with eight lobes, slightly taller than wide.
    cx, cy = px(EYE_C), row(EYE_R)
    pts, radii = [], []
    n = 32
    for k in range(n):
        a = 2 * math.pi * k / n
        lobe = 1 + 0.05 * math.cos(8 * a)
        pts.append((cx + 6.1 / 12 * lobe * math.cos(a), cy + 6.7 / 12 * lobe * math.sin(a), top + 0.07))
        radii.append(2.3 / 12 * (1 + 0.14 * math.cos(8 * a)))
    lib.loop_tube(bm, pts, radii, sides=8, mat=RING, flat=0.6)
    # Pale highlights on the lobes facing the light (upper left).
    for k in range(8):
        a = 2 * math.pi * k / 8
        if math.cos(a - 2.4) < -0.2:
            continue
        lib.ellipsoid(bm, (cx + 6.8 / 12 * math.cos(a), cy + 7.4 / 12 * math.sin(a), top + 0.13),
                      (0.11, 0.11, 0.05), mat=LOBE, segments=8, rings=4)

    # The socket, its grey bezel and the eye.
    lib.dome(bm, (cx, cy, top - 0.02), (4.4 / 12, 4.8 / 12, 0.12), mat=SOCKET, segments=16, rings=4)
    lib.loop_tube(bm, [(cx + 4.0 / 12 * math.cos(a), cy + 4.4 / 12 * math.sin(a), top + 0.05)
                       for a in (2 * math.pi * k / 20 for k in range(20))], 0.045, sides=6, mat=BEZEL)
    obj = lib.to_object(NAME, bm, mats, coll)

    # The eye: dim on frame 1 and dark on 39 (one eye whose colour changes), wide open and
    # bright on frame 3 (rows 11-15, columns 10-15) with a white-hot pupil.
    bm = bmesh.new()
    lib.dome(bm, (cx, cy - 0.01, top + 0.04), (2.6 / 12, 2.6 / 12, 0.13), mat=EYE, segments=16, rings=4)
    eye = common.frame_part(lib.to_object(f"{NAME}-eye", bm, mats, coll), [1, 39])
    bm = bmesh.new()
    lib.dome(bm, (cx + 0.2 / 12, cy - 0.01, top + 0.04), (3.1 / 12, 2.9 / 12, 0.15), mat=BRIGHT, segments=16, rings=4)
    lib.dome(bm, (cx + 0.3 / 12, cy - 0.2 / 12, top + 0.17), (1.1 / 12, 1.1 / 12, 0.04), mat=PUPIL, segments=12, rings=3)
    open_eye = common.frame_part(lib.to_object(f"{NAME}-eye-open", bm, mats, coll), [3])
    return [(NAME, [obj, eye, open_eye], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
