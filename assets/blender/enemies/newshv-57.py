"""Small red gem (newshv.shp frame 57, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A shiny bulb with a diamond outline: a dark 1 px rim, a bright
cross of highlight just right of centre, and a short stalk trailing below it. newshv-19 is the same
gem in blue.

The bulb is round, not faceted: a smooth dome over the diamond plan, about 4.5 px above the
midplane and 3.5 px below it, widest at the rim. Its rings go from the diamond at the rim to a
rounder shape towards the crown, so the top has no creases, and they shift towards the sprite's
highlight (column 6) as they rise. The faces take the sprite's shades by band and by direction:
the dark rim, a mid-salmon body darker on the left, the bright cross along the axes and a bright
core at the crown.

Run: blender --background --python assets/blender/enemies/newshv-57.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-57"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

W, H = 12, 14
U = 1 / 12
SIDE = 3  # sectors per side of the diamond; the middle one faces a diagonal
TOP = 4.5 * U  # dome height above the midplane
BOTTOM = 3.5 * U  # depth of the rounded underside
TOP_RINGS = (1.0, 0.86, 0.76, 0.54, 0.22)  # ring scales from the rim in; an apex follows
BOTTOM_RINGS = (1.0, 0.6)
HIGHLIGHT_DX = 0.5 * U  # the bright cross is centred on column 6, half a pixel right of centre

# Palette index of each top band (dark rim, wall, body, inner, crown) in each sector. Sectors: the
# two halves of each arm of the sprite's cross (right_u is the upper half of the +X arm) and the
# four diagonals. The sprite is lit along the cross's right and top halves, darker on the left.
SHADES = {
    #          rim wall body inner crown
    "right_u": (72, 74, 76, 78, 79),
    "right_d": (72, 74, 76, 78, 79),
    "up_r":    (72, 74, 76, 78, 79),
    "up_l":    (72, 74, 74, 75, 79),
    "left_u":  (72, 74, 76, 76, 79),
    "left_d":  (72, 74, 76, 76, 79),
    "down_l":  (72, 74, 74, 77, 79),
    "down_r":  (72, 74, 76, 78, 79),
    "ur":      (72, 74, 76, 76, 78),
    "ul":      (72, 74, 74, 75, 79),
    "ll":      (72, 74, 74, 77, 79),
    "lr":      (72, 74, 76, 76, 78),
}
UNDERSIDE = 72


def unit_dirs():
    """Points around the unit diamond |x| + |y| = 1, evenly spaced along each side, corners
    included, counter-clockwise from +X."""
    corners = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    out = []
    for k in range(4):
        (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % 4]
        for i in range(SIDE):
            t = i / SIDE
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def sector_dir(i):
    """Which arm or diagonal sector i (between point i and i+1) faces."""
    side, k = divmod(i, SIDE)
    first = ("right_u", "up_l", "left_d", "down_r")  # the arm half at the side's start
    last = ("up_r", "left_u", "down_l", "right_d")  # the arm half at its end
    diag = ("ur", "ul", "ll", "lr")
    if k == 0:
        return first[side]
    if k == SIDE - 1:
        return last[side]
    return diag[side]


def ring_point(d, s, rx, ry):
    """The point in direction `d` (a point on the unit diamond) on the ring of scale `s`: the ring
    is a superellipse whose exponent goes from 1 (the diamond) at the rim to 2 (round) at the crown."""
    p = 1.0 + (1.0 - s)
    ang = math.atan2(d[1], d[0])
    c, sn = math.cos(ang), math.sin(ang)
    r = (abs(c) ** p + abs(sn) ** p) ** (-1 / p)
    return (s * r * c * rx + (1 - s) * HIGHLIGHT_DX, s * r * sn * ry)


def bulb(mats, slot, cx, cy, rx, ry, coll):
    import bmesh
    bm = bmesh.new()
    dirs = unit_dirs()
    n = len(dirs)

    def ring(s, z):
        return [bm.verts.new((cx + x, cy + y, z)) for x, y in (ring_point(d, s, rx, ry) for d in dirs)]

    rim = ring(1.0, 0.0)
    top = [rim] + [ring(s, TOP * (1 - s * s) ** 0.6) for s in TOP_RINGS[1:]]
    top_apex = bm.verts.new((cx + HIGHLIGHT_DX, cy, TOP))
    bot = [rim] + [ring(s, -BOTTOM * math.sqrt(1 - s * s)) for s in BOTTOM_RINGS[1:]]
    bot_apex = bm.verts.new((cx, cy, -BOTTOM))

    def bands(rings, apex, shade):
        for k in range(len(rings)):
            a = rings[k]
            b = rings[k + 1] if k + 1 < len(rings) else None
            for i in range(n):
                j = (i + 1) % n
                f = (a[i], a[j], b[j], b[i]) if b else (a[i], a[j], apex)
                bm.faces.new(f).material_index = slot[shade(k, i)]

    bands(top, top_apex, lambda k, i: SHADES[sector_dir(i)][k])
    bands(bot, bot_apex, lambda k, i: UNDERSIDE)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    used = sorted({i for shades in SHADES.values() for i in shades} | {UNDERSIDE, 71, 74})
    mats, slot = [], {}
    for i in used:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, NAME, metallic=0.35, roughness=0.3))

    cy = lib.ey(7.5, H)
    gem = bulb(mats, slot, 0.0, cy, 5.0 * U, 4.5 * U, coll)

    # The stalk below it (rows 12-13, columns 5-6): a round 2 px rod on the midplane, darker,
    # with a slightly fatter lighter knob at its end.
    import bmesh
    bm = bmesh.new()
    common.loft(bm, [(lib.ey(10.8, H), 1.0 * U, 1.0 * U, 0.0), (lib.ey(12.9, H), 1.0 * U, 1.0 * U, 0.0)],
                sides=6, mat_index=slot[71])
    common.loft(bm, [(lib.ey(12.9, H), 1.05 * U, 1.05 * U, 0.0), (lib.ey(13.6, H), 1.0 * U, 1.0 * U, 0.0),
                     (lib.ey(14.0, H), 0.0, 0.0, 0.0)], sides=6, mat_index=slot[74])
    stalk = common.mesh_object(f"{NAME}_stalk", bm, mats, coll, smooth=True)

    objects = [gem, stalk]
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
