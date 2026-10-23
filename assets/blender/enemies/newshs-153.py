"""Red lamp panel (newshs.shp frames 153-163): a 3D version of its sprite.

A ground block that fills its whole tile (levels 1.21, 1.5, 1.6, 2.8, 3.15): a grey metal plate
with three rounded red glass lamps stacked down it, each in a raised bezel, and a strip of
machinery down its right side. The six frames only move the glow from lamp to lamp, so one model
covers them all (the lamps glow in the palette's red).

Run: blender --background --python assets/blender/enemies/newshs-153.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b080 as L  # noqa: E402
import common  # noqa: E402

NAME = "newshs-153"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
g = L.Grid(24, 28)


def stadium(x0, x1, y0, y1, n=4):
    """Counter-clockwise outline of a capsule (rounded ends left and right) between pixel edges."""
    r = (y0 - y1) / 2  # y0 is the top (larger Y)
    return L.rounded_rect(x0, y1, x1, y0, min(r, (x1 - x0) / 2) * 0.65, n)


def lamp_dome(bm, x0, x1, y0, y1, z0, h, mat, steps=4):
    """A capsule-shaped glass lens rising h above z0, rings shrinking towards its top."""
    rings = []
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for k in range(steps + 1):
        t = k / steps
        s = (1 - t * t) ** 0.5  # round profile
        hw, hh = (x1 - x0) / 2, (y0 - y1) / 2
        sx = hw - hh * (1 - s)  # the ends round off, the straight middle stays wide
        sy = hh * s
        outline = L.rounded_rect(cx - sx, cy - sy, cx + sx, cy + sy, max(sy * 0.7, 0.002), 4)
        rings.append([(x, y, z0 + h * t) for x, y in outline])
    return L.ring_loft(bm, rings, mat, smooth=True, cap_start=True, cap_end=True)


def build(sprite):
    coll = common.reset_collection(NAME)
    m = L.Mats(NAME, sprite["colors"])
    PLATE = m(6, metallic=0.5, roughness=0.55)
    BEZEL = m(9, metallic=0.6, roughness=0.4)
    DARK = m(3, metallic=0.4, roughness=0.6)
    RIM = m(113, metallic=0.3, roughness=0.4)
    LENS = m(115, metallic=0.1, roughness=0.15, emission_strength=2.5)
    CORE = m(117, metallic=0.1, roughness=0.15, emission_strength=3.0)
    RAIL = m(7, metallic=0.5, roughness=0.45)
    BOLT = m(11, metallic=0.7, roughness=0.3)
    bm = bmesh.new()

    # The plate: the whole tile, a low block with a chamfered top edge.
    L.bevel_prism(bm, [(g.x(-0.5), g.y(27.5)), (g.x(23.5), g.y(27.5)), (g.x(23.5), g.y(-0.5)),
                       (g.x(-0.5), g.y(-0.5))], 0.0, 0.14, 0.02, mat=PLATE)

    for top in (1, 10, 19):  # each lamp: bezel rows top-1 .. top+7, lens rows top+1 .. top+7
        # Raised bezel round the lamp (its top and left edges are the bright lines in the sprite).
        bez = stadium(g.x(0.6), g.x(20.4), g.y(top - 0.4), g.y(top + 7.9), n=4)
        L.bevel_prism(bm, bez, 0.12, 0.25, 0.035, mat=BEZEL)
        # Dark red lip and the glass lens on it.
        lip = stadium(g.x(1.5), g.x(19.5), g.y(top + 0.6), g.y(top + 7.6), n=4)
        L.prism(bm, lip, 0.24, 0.27, mat=RIM)
        lamp_dome(bm, g.x(1.9), g.x(19.1), g.y(top + 0.9), g.y(top + 7.3), 0.26, 0.09, LENS)
        lamp_dome(bm, g.x(4.5), g.x(16.0), g.y(top + 2.6), g.y(top + 5.8), 0.33, 0.035, CORE)

    # Machinery strip down the right side (columns 20-23): a rail, and a block per lamp.
    L.box(bm, g.x(19.6), g.y(27.2), g.x(21.4), g.y(-0.2), 0.12, 0.21, mat=RAIL)
    for top in (1, 10, 19):
        L.bevel_prism(bm, [(g.x(21.5), g.y(top + 6.5)), (g.x(23.4), g.y(top + 6.5)),
                           (g.x(23.4), g.y(top + 0.5)), (g.x(21.5), g.y(top + 0.5))], 0.12, 0.22, 0.02,
                      mat=DARK)
        L.tube_z(bm, [(0.2, g.x(22.4), g.y(top + 3.5), 0.045, 0.045), (0.25, g.x(22.4), g.y(top + 3.5), 0.04, 0.04),
                      (0.27, g.x(22.4), g.y(top + 3.5), 0.0, 0.0)], sides=8, mat=BOLT)
    # Dark seams between the lamps (rows 9 and 18).
    for r in (9, 18):
        L.box(bm, g.x(0.0), g.y(r + 0.4), g.x(23.0), g.y(r - 0.4), 0.13, 0.15, mat=DARK)

    return L.to_object(NAME, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    L.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
