"""Strapped crate (tyrian.shp #10 frame 129): a 3D version of its sprite.

Seen in episode 3 (level 25). A brown wooden chest lying at an angle, its long side running from
lower left to upper right, bound with grey iron straps, its lower-right side in deep shadow.
Built as a rounded block on the sprite's four corners (the lower-right side a steep dark slope,
as the sprite shows it), with raised iron straps, and each top face coloured from the sprite pixel
under it so the wood grain and straps land where the sprite has them.

Run: blender --background --python assets/blender/enemies/tyrian10-129.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b039 as lib  # noqa: E402

NAME = "tyrian10-129"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# The block's corners in sprite pixel-edge coordinates (col, row), just inside the outline:
# s runs along the long side (left corner -> top corner), t across it (upper-left side ->
# lower-right side, which is the shadowed slope).
P00, P10 = (1.8, 16.4), (13.0, 5.8)   # left, top
P01, P11 = (12.0, 22.2), (21.2, 13.4)  # bottom, right

# Cross-section round the block, (t, z) with z in units, top first and going over the
# shadowed side: a flat lid, rounded upper-left edge, the steep lower-right slope, a flat base.
PROFILE = [(0.00, -0.03), (0.015, 0.07), (0.05, 0.14), (0.11, 0.19), (0.20, 0.215), (0.30, 0.225),
           (0.40, 0.23), (0.50, 0.225), (0.60, 0.21), (0.67, 0.18), (0.74, 0.12), (0.82, 0.05),
           (0.90, -0.02), (0.97, -0.08), (0.985, -0.13), (0.85, -0.17), (0.50, -0.18), (0.15, -0.17),
           (0.02, -0.12)]

# Along s: (s, shrink) with the ends pulled in to round them.
STATIONS = [(0.0, 0.8), (0.015, 0.95), (0.05, 1.0)] + [(i / 16, 1.0) for i in range(1, 16)] + \
           [(0.95, 1.0), (0.985, 0.95), (1.0, 0.8)]

# The iron straps, as polylines of sprite pixel centres (col, row).
STRAPS = [
    [(11.3, 6.5), (11.0, 8.0), (10.2, 9.3), (8.2, 11.4), (8.4, 12.6), (9.8, 14.0), (10.6, 15.5), (10.8, 17.5),
     (11.0, 19.0)],
    [(12.8, 8.2), (13.8, 9.6), (14.0, 11.5), (14.0, 14.0), (14.2, 16.0)],
]


def to_st(x, y):
    """Inverse of to_xy (a few Newton steps from the middle)."""
    s, t = 0.5, 0.5
    for _ in range(12):
        x0, y0 = to_xy(s, t)
        d = 1e-4
        xs, ys = to_xy(s + d, t)
        xt, yt = to_xy(s, t + d)
        a, b, c, e = (xs - x0) / d, (xt - x0) / d, (ys - y0) / d, (yt - y0) / d
        det = a * e - b * c
        fx, fy = x - x0, y - y0
        s += (e * fx - b * fy) / det
        t += (-c * fx + a * fy) / det
    return s, t


def lid_height(x, y):
    """Height of the block's top over Blender (x, y), from the profile."""
    _, t = to_st(x, y)
    top = [(pt, z) for pt, z in PROFILE[:13]]
    t = min(max(t, top[0][0]), top[-1][0])
    for (t0, z0), (t1, z1) in zip(top, top[1:]):
        if t0 <= t <= t1:
            return z0 + (z1 - z0) * (t - t0) / ((t1 - t0) or 1)
    return top[-1][1]


def to_xy(s, t):
    """Bilinear map of (s, t) on the corners to Blender X, Y."""
    c = (1 - s) * (1 - t) * P00[0] + s * (1 - t) * P10[0] + (1 - s) * t * P01[0] + s * t * P11[0]
    r = (1 - s) * (1 - t) * P00[1] + s * (1 - t) * P10[1] + (1 - s) * t * P01[1] + s * t * P11[1]
    return lib.ex(c), lib.ey(r)


def section(s, shrink):
    """One ring of the block at s: the profile pulled toward its middle by `shrink` (rounded ends)."""
    pts = []
    for t, z in PROFILE:
        t2 = 0.5 + (t - 0.5) * (1 - (1 - shrink) * 0.3)
        z2 = z * shrink
        x, y = to_xy(s, t2)
        pts.append((x, y, z2))
    return pts


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(166, metallic=0.0, roughness=0.8),  # 0 wood
        pal(169, metallic=0.0, roughness=0.75),  # 1 light wood
        pal(172, metallic=0.0, roughness=0.7),  # 2 lit wood edges
        pal(163, metallic=0.0, roughness=0.85),  # 3 dark wood
        pal(161, metallic=0.0, roughness=0.9),  # 4 shadowed side
        pal(7, metallic=0.7, roughness=0.35),  # 5 iron strap
        pal(10, metallic=0.75, roughness=0.3),  # 6 lit iron
        pal(4, metallic=0.6, roughness=0.45),  # 7 dark iron
    ]
    WOOD, LIGHT, EDGE, DARKWOOD, SIDE, IRON, IRON_LIT, IRON_DARK = range(8)
    bm = bmesh.new()

    # The block.
    rings = [section(s, k) for s, k in STATIONS]
    lib.ring_loft(bm, rings, WOOD)

    def slot(i):
        if i in (64, 161, 16):
            return SIDE
        if 162 <= i <= 164:
            return DARKWOOD
        if 165 <= i <= 167:
            return WOOD
        if 168 <= i <= 170:
            return LIGHT
        if 171 <= i <= 173:
            return EDGE
        if 1 <= i <= 4:
            return IRON_DARK
        if 5 <= i <= 8:
            return IRON
        if 9 <= i <= 11:
            return IRON_LIT
        return None

    pixels = sprite["frames"][0]["pixels"]
    lib.paint_from_sprite(bm, pixels, slot, under_slot=SIDE, min_nz=-0.2)
    body = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # The two iron straps, raised a little where the sprite draws them: both run down the screen
    # over the lid and its front (sprite pixel centres, col and row).
    bm = bmesh.new()
    for line in STRAPS:
        pts = [(lib.px(c), lib.row(r)) for c, r in line]
        lib.strip(bm, pts, 1.6 / 12, 0.025, lid_height, lift=-0.012, mat_index=IRON)
    lib.paint_from_sprite(bm, pixels, lambda i: IRON_LIT if i in (9, 10, 11) else
                          (IRON if 5 <= i <= 8 else IRON_DARK), under_slot=IRON_DARK, min_nz=-0.2)
    straps = common.mesh_object(f"{NAME}_straps", bm, mats, coll, smooth=False)
    return [body, straps]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    lib.preview(objs, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
