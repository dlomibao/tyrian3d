"""Fireball (newsh3.shp frames 267, 269): a 3D version of its sprite.

Seen in episode 4 (levels 6, 22 and 31). A teardrop of fire, tip up the screen and a round hot
belly below: a fluted red outer flame wrapped round an orange layer, a yellow core and a
white-hot heart low in the belly, each layer rising a little above the one round it so from above
they read as the sprite's colour bands. The two frames only flicker the flame: 269 is 267
mirrored left to right, so the flame sways and its hot heart swaps sides. One model covers both,
with the flame lofted from each frame's own pixels and shown on that frame (common.frame_part).
Everything glows.

Run: blender --background --python assets/blender/enemies/newsh3-267.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, ex, ey  # noqa: E402

NAME = "newsh3-267"


def smooth(values, n=1):
    out = list(values)
    for _ in range(n):
        out = [out[0]] + [(out[i - 1] + 2 * out[i] + out[i + 1]) / 4 for i in range(1, len(out) - 1)] + [out[-1]]
    return out


def layer_sections(frames, threshold, grow, top, belly=0.0, rows=None):
    """Loft sections for the flame layer made of pixels >= threshold: per row, the extents
    (grown by `grow` px each side), smoothed, with tips half a row past the ends. The layer's top
    sits at `top` over its middle (its half height scales with width up to that)."""
    ext = lib.row_extents(frames, lambda v: v >= threshold)
    rs = sorted(r for r in ext if rows is None or rows[0] <= r <= rows[1])
    cs = smooth([(ext[r][0] + ext[r][1]) / 2 for r in rs], 2)
    ws = smooth([(ext[r][1] - ext[r][0]) / 2 + grow for r in rs], 2)
    secs = [(ey(rs[0] - 0.1), ex(cs[0]), 0.0, 0.0, belly)]
    for r, c, w in zip(rs, cs, ws):
        hw = w / 12
        hh = min(top, hw * 0.9)
        secs.append((ey(r + 0.5), ex(c), hw, hh, belly))
    secs.append((ey(rs[-1] + 1.05), ex(cs[-1]), 0.0, 0.0, belly))
    return secs


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(118, roughness=0.6, emission_strength=2.0),  # 0 red outer flame
        pal(121, roughness=0.5, emission_strength=3.0),  # 1 orange
        pal(124, roughness=0.4, emission_strength=4.0),  # 2 yellow core
        pal(126, roughness=0.3, emission_strength=5.0),  # 3 white-hot heart
    ]
    RED, ORANGE, YELLOW, WHITE = range(4)
    def flutes(k, amp):
        return lambda a, y: 1.0 + amp * math.cos(k * a + y * 9.0)

    parts = []
    for frame in sprite["frames"]:
        frames = [frame["pixels"]]
        bm = bmesh.new()
        lib.loft2(bm, layer_sections(frames, 113, 0.45, 0.17), sides=16, mat_index=RED, wobble=flutes(7, 0.06))
        lib.loft2(bm, layer_sections(frames, 120, 0.1, 0.2, belly=0.03), sides=14, mat_index=ORANGE,
                  power=0.8, wobble=flutes(5, 0.07))
        lib.loft2(bm, layer_sections(frames, 123, -0.1, 0.2, belly=0.07, rows=(7, 24)), sides=12,
                  mat_index=YELLOW, power=0.8)
        lib.loft2(bm, layer_sections(frames, 125, -0.2, 0.17, belly=0.12, rows=(13, 21)), sides=10,
                  mat_index=WHITE, power=0.85)
        obj = common.mesh_object(f"{NAME}-{frame['index']}", bm, mats, coll, smooth=True)
        parts.append(common.frame_part(obj, [frame["index"]]))
    return [(NAME, parts, sprite["sprites"])]

if __name__ == "__main__":
    lib.run(NAME, build, __file__)
