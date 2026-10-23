"""Brown seed pod (newshh.shp frame 131): a 3D version of its sprite.

Seen in episode 2 (level 2.4). A bronze shell shaped like a shield or seed, pointed at the
bottom: a pale keel runs down its middle, a rounded cap sits on top behind a dark seam, two
small hooks stick out at the shoulders and two bumps bulge from its flanks. One frame.

Run: blender --background --python assets/blender/enemies/newshh-131.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b018 as lib  # noqa: E402
from lib_b018 import px, row  # noqa: E402

NAME = "newshh-131"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.45, roughness=0.4),  # 0 bronze shell
        pal(20, metallic=0.4, roughness=0.55),  # 1 dark underside and seam
        pal(28, metallic=0.5, roughness=0.3),  # 2 pale keel
        pal(26, metallic=0.5, roughness=0.35),  # 3 light cap
        pal(25, metallic=0.45, roughness=0.4),  # 4 hooks and flank bumps
    ]
    SHELL, DARK, KEEL, CAP, HOOK = range(5)
    pixels = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    # The shell: a hull lofted down the sprite, each row as wide as its non-outline pixels
    # (leaving out the shoulder hooks), with a ridge along the middle like the sprite's lit left
    # and shaded right faces.
    keep = lambda r, c, v: v not in (-1, 1) and (r > 8 or r < 4 or 5 <= c <= 19)  # noqa: E731
    spans = lib.row_spans(pixels, keep, range(1, 25), inset=-0.3)
    wmax = max(hw for _, hw in spans.values())
    H, B = 0.3, 0.14

    def height(r):
        return H * (spans[r][1] / wmax) ** 0.6

    rings = []
    for r in sorted(spans):
        xc, hw = spans[r]
        xc = px(12)  # the sprite is symmetric about column 12
        rings.append(lib.section_ring(xc, row(r), hw, -0.02, height(r), B * (hw / wmax) ** 0.6, keel=1.3))
    rings.append([(px(12), row(25.3), -0.01)])
    lib.ring_loft(bm, rings, mat=SHELL)

    # The cap: a rounder dome over rows 1-5, raised above the shell behind the seam.
    lib.dome(bm, (px(12.2), row(3.0), 0.04), (6.6 / 12, 3.0 / 12, 0.26), mat=CAP, segments=20, rings=5)
    # The dark seam under the cap's front edge (rows 4-5).
    lib.tube(bm, [(px(5.8), row(4.8), 0.08), (px(9), row(5.6), 0.2), (px(12.2), row(5.9), 0.24),
                  (px(15.5), row(5.6), 0.2), (px(18.6), row(4.8), 0.08)], 0.05, sides=6, mat=DARK)

    # The keel down the middle (column 12), a raised pale ridge on the shell.
    keel = [(px(12), row(r), -0.02 + height(r) - 0.01) for r in (6, 8, 11, 14, 17, 20, 22)]
    keel.append((px(12), row(24.6), 0.0))
    lib.tube(bm, keel, [0.07, 0.085, 0.085, 0.08, 0.07, 0.06, 0.045, 0.0], sides=8, mat=KEEL, flat=0.5)

    # Shoulder hooks (rows 4-7, columns 2-4 and 19-22): short curved horns, mirrored.
    v0, f0 = len(bm.verts), len(bm.faces)
    lib.tube(bm, [(px(5.2), row(7.5), 0.03), (px(3.6), row(6.8), 0.04), (px(3.0), row(5.4), 0.04),
                  (px(3.6), row(4.3), 0.03)], [0.07, 0.06, 0.05, 0.0], sides=6, mat=HOOK)
    # Flank bumps (rows 11-13, columns 3-5).
    lib.ellipsoid(bm, (px(4.2), row(12.3), 0.03), (0.13, 0.12, 0.09), mat=HOOK, segments=10, rings=5)
    lib.mirror_new(bm, v0, f0, axis_x=px(12))

    obj = lib.to_object(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
