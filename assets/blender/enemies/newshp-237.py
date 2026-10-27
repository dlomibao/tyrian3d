"""Shuttered eye bunker (newshp.shp frames 237-283): a 3D version of its sprites.

Seen in episode 1 (level 1.21). A rounded grey stone housing (columns 3-18, rows 0-13) set in
rubbly ground, with a louvred apron falling away below it to a dark trench. In the housing's
square well a red lens looks out from under a shutter. The frames slide the shutter and take the
lens away, so each shape is its own model:

    newshp-237     open, lens showing (frames 237 and 239, which only brighten the lens: its
                   materials take each frame's palette colour, palette_material frames=)
    newshp-237-f2  shutter half closed (245)
    newshp-237-f3  shutter closed (279)
    newshp-237-f4  shutter nearly closed (281)
    newshp-237-f5  open, the lens gone and its socket empty (283)

Run: blender --background --python assets/blender/enemies/newshp-237.py [-- --preview out.png]
(-- previews every state: <out>.png and newshp-237-f<n>.png beside it; -- --frames <png> renders
every frame of each state).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b067 as lib  # noqa: E402
from lib_b067 import PX, common  # noqa: E402

NAME = "newshp-237"
SHEET = "newshp.shp"
# (model, frames, shutter's lower edge row or None when retracted, lens shown)
STATES = [
    (NAME, (237, 239), None, True),
    (f"{NAME}-f2", (245,), 8, False),
    (f"{NAME}-f3", (279,), 12, False),
    (f"{NAME}-f4", (281,), 10, False),
    (f"{NAME}-f5", (283,), None, False),
]


def build(sprite):
    g = lib.Grid(24, 28)
    m = lib.Mats(sprite, NAME)
    m.add(117, emission_strength=3.0)
    m.add(121, emission_strength=5.0)
    models = []
    for model, frames, shutter, lens in STATES:
        coll = common.reset_collection(model)
        bm = bmesh.new()
        extra = []
        lib.terrain(bm, g, m)
        lib.housing(bm, g, m)
        if shutter is None:
            # Shutter slid up under the rim: its lit lip across rows 3-4, its face in row 5.
            lib.frustum(bm, g, 7.6, 2, 16.4, 5.6, 0.12, 0.26, m[11], sides=(m[12], m[9], m[7], m[6]), inset=0.3)
            if lens:
                # The lens and its socket are their own object, with their own materials: frame 239
                # brightens the lens (113 -> 118 round its rim, 117 -> 123 at its centre) and
                # lights up the socket round it (grey 5-6 -> 8-10).
                lm = lib.Mats(sprite, f"{NAME}_lens")
                lm.add(6, "socket", frames={239: 9})
                lm.add(113, "lens", emission_strength=3.0, frames={239: 118})
                lm.add(117, "lens_core", emission_strength=5.0, frames={239: 123})
                lbm = bmesh.new()
                lib.frustum(lbm, g, 9, 6, 15, 11, 0.12, 0.17, lm.slot["socket"], sides=(lm[4], lm[5], lm[7], lm[5]),
                            inset=0.4)
                cx, cy = g.x(12), g.y(8)
                lib.dome(lbm, cx, cy, 0.15, 2.1 * PX, 2.1 * PX, 0.09, lm.slot["lens"], segs=12, rings=3)
                lib.dome(lbm, cx, cy + 0.4 * PX, 0.2, 0.9 * PX, 0.9 * PX, 0.05, lm.slot["lens_core"], segs=8, rings=2)
                extra = [lib.to_object(f"{model}-lens", lbm, lm.list, coll)]
            else:
                # The lens socket (columns 9-14, rows 6-10).
                lib.frustum(bm, g, 9, 6, 15, 11, 0.12, 0.17, m[6], sides=(m[4], m[5], m[7], m[5]), inset=0.4)
                # Empty socket: a dark ring where the lens sat.
                lib.frustum(bm, g, 10, 6.5, 14, 10, 0.165, 0.18, m[3], sides=(m[2], m[2], m[5], m[5]), inset=0.5)
        else:
            # Shutter slid down over the well, its lower edge at row `shutter`.
            lib.frustum(bm, g, 7.6, 2, 16.4, shutter, 0.12, 0.28, m[9], sides=(m[12], m[11], m[7], m[6]), inset=0.3)
        obj = lib.to_object(model, bm, m.list, coll)
        models.append((model, [obj] + extra, lib.subset(sprite, {(SHEET, f) for f in frames})))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
