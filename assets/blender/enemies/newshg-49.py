"""Bronze pincer beetle (newshg.shp frames 49, 51, 53): a 3D version of its sprite.

Seen in episode 2 (level sections 10 and 12). A bronze beetle shell with a bright ridge down its
back, two curved horns sweeping up and out from its shoulders, small wing lobes at its sides and
two long curved pincers hanging below that nearly meet at their tips. The frames close the horns
and pincers in by a pixel per side each, so each frame gets its own model: newshg-49 (open, frame
49), newshg-49-f2 (frame 51) and newshg-49-f3 (closed, frame 53).

Run: blender --background --python assets/blender/enemies/newshg-49.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b034 as lib  # noqa: E402
from lib_b034 import common, px, row  # noqa: E402

NAME = "newshg-49"
MIRROR_C = 24  # the sprite is symmetric about column 12: column c mirrors to 24 - c


def build_state(sprite, model, coll, s):
    """One pose: the horns and pincers moved in by `s` pixels per side."""
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.55, roughness=0.35),  # 0 shell bronze
        pal(29, metallic=0.6, roughness=0.2),  # 1 ridge highlight
        pal(19, metallic=0.5, roughness=0.5),  # 2 dark underside / stems
        pal(26, metallic=0.55, roughness=0.3),  # 3 light horns, lobes
        pal(22, metallic=0.55, roughness=0.4),  # 4 pincers
        pal(25, metallic=0.55, roughness=0.3),  # 5 pincer highlight
    ]
    SHELL, RIDGE, DARK, HORN, PINCER, PHI = range(6)
    bm = bmesh.new()

    def both(fn):
        """Build fn(c) for the left side (column function) and its mirror."""
        fn(lambda c: px(c))
        fn(lambda c: px(MIRROR_C - c))

    # Shell (rows 0-13, centred on column 12): a domed oval, widest across the shoulders.
    shell = [(0.3, 0.0, 0.0), (0.8, 2.6, 0.9), (1.8, 3.8, 1.5), (3.5, 4.6, 1.9), (6.0, 5.0, 2.1),
             (8.5, 5.0, 2.1), (10.5, 4.6, 1.9), (12.0, 3.8, 1.5), (13.0, 2.4, 1.0), (13.6, 0.0, 0.0)]
    start = len(bm.verts)
    common.loft(bm, [(row(r), w / 12, h / 12, 0.03) for r, w, h in shell], sides=14, mat_index=SHELL)
    common.shift_x(bm, start, px(12))
    # The bright ridge down the back (column 12, rows 1-9).
    lib.polyline_tube(bm, [(px(12), row(0.9), 0.03 + 1.0 / 12), (px(12), row(2.5), 0.03 + 1.75 / 12),
                           (px(12), row(6.0), 0.03 + 2.05 / 12), (px(12), row(9.5), 0.03 + 1.95 / 12)],
                      [0.25 / 12, 0.6 / 12, 0.55 / 12, 0.2 / 12], sides=6, mat_index=RIDGE, flat=0.6)
    # A dark lower plate under the shell's rear (rows 10-12).
    lib.ellipsoid(bm, (px(12), row(11.2), -0.02), (5.6 / 12, 2.2 / 12, 0.08), segments=14, rings=6,
                  mat_index=DARK)

    def side(X):
        # Wing lobes at the shell's lower sides (rows 9-11, columns 5-7).
        lib.ellipsoid(bm, (X(6.8), row(10.0), 0.0), (2.4 / 12, 1.9 / 12, 0.08), segments=10, rings=5,
                      mat_index=HORN)
        # Horn: from the shoulder (row 7, column 7) sweeping up and out to the tip (row 1, column 3).
        # A broad flat blade, widest at the shoulder.
        pts = [(8.4, 7.8, 0.0), (6.6, 6.2, 0.01), (5.0 + s * 0.4, 4.6, 0.02), (4.0 + s * 0.8, 3.0, 0.03),
               (3.3 + s, 1.3, 0.03), (3.0 + s, 0.1, 0.03)]
        lib.polyline_tube(bm, [(X(c), row(r), z) for c, r, z in pts],
                          [2.6 / 12, 2.2 / 12, 1.7 / 12, 1.2 / 12, 0.8 / 12, 0.0], sides=8, mat_index=HORN,
                          flat=0.4)
        # Stem under the shell (rows 12-15, columns 9-10) and the pincer curving out and back.
        pts = [(9.6, 12.0), (9.2, 13.6), (8.2 + s * 0.5, 15.2), (7.0 + s, 16.6), (6.3 + s, 18.4),
               (6.0 + s, 20.5), (6.0 + s, 22.5), (6.4 + s, 24.3), (7.3 + s, 25.8), (8.4 + s, 26.7)]
        rad = [1.5, 1.4, 1.5, 1.6, 1.6, 1.5, 1.4, 1.2, 0.9, 0.4]
        lib.polyline_tube(bm, [(X(c), row(r), -0.03) for c, r in pts], [v / 12 for v in rad], sides=8,
                          mat_index=PINCER, flat=0.6)
        # A light streak along each pincer's inner face (column 7-8 highlights, rows 16-22).
        hl = [(c + 0.5, r) for c, r in pts[3:8]]
        lib.polyline_tube(bm, [(X(c), row(r), -0.03 + 0.06) for c, r in hl], 0.45 / 12, sides=5,
                          mat_index=PHI, flat=0.5)

    both(side)
    obj = common.mesh_object(model, bm, mats, coll, smooth=True)
    return obj


def build(sprite):
    coll = common.reset_collection(NAME)
    out = []
    for s, (model, frame) in enumerate(((NAME, 49), (f"{NAME}-f2", 51), (f"{NAME}-f3", 53))):
        obj = build_state(sprite, model, coll, s)
        out.append((model, [obj], lib.subset(sprite, [frame])))
        sprite.setdefault("_preview", {})[model] = [f["index"] for f in sprite["frames"]].index(frame)
    return out


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
