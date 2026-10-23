"""Bronze pod with telescoping arms (newsh2.shp frames 159-167): a 3D version of its sprite.

Seen in episode 1 (levels 25-41), episode 2 and episode 3. A round bronze hull with a small
knob on top, a grey bar across its upper half with a shiny hub in the middle, and a dark slot
down the front. Over the five frames the bar's thin arms slide out of the hull one pixel a side
at a time (tips at 7, 8, 9, 10 and 11 px from the centre) and red-hot fins open round them. The
frames also alternate a shade darker and lighter, and frame 159 is drawn one row higher. So each
frame gets its own model: newsh2-159, newsh2-159-f2 (161) ... newsh2-159-f5 (167).

Run: blender --background --python assets/blender/enemies/newsh2-159.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-159"
U = 1 / 12

# Per frame: arm tip (px from centre), shade offset (0 dark, 1 light), rows shifted up, red fins
# as (centre x px, centre row, rx px, ry px, palette index) or None.
FRAMES = [
    (7, 0, 1, None),
    (8, 1, 0, None),
    (9, 0, 0, (7.3, 16.0, 1.0, 1.4, 114)),
    (10, 1, 0, (7.7, 14.6, 1.6, 3.4, 119)),
    (11, 1, 0, (8.2, 14.8, 2.2, 4.0, 119)),
]


def build_one(sprite, name, tip, shade, up, fins):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i + shade, NAME, **kw)  # noqa: E731
    mats = [
        pal(22, metallic=0.55, roughness=0.4),  # 0 bronze hull
        pal(24, metallic=0.6, roughness=0.35),  # 1 light bronze shoulders
        pal(167, metallic=0.5, roughness=0.35),  # 2 knob
        pal(5, metallic=0.7, roughness=0.3),  # 3 grey bar
        pal(13, metallic=0.8, roughness=0.15),  # 4 shiny hub
        pal(17, metallic=0.2, roughness=0.6),  # 5 dark slot
        pal(3, metallic=0.6, roughness=0.4),  # 6 dark grey arm tips
    ]
    HULL, SHOULDER, KNOB, BAR, HUB, SLOT, ARM = range(7)
    if fins:
        mats.append(common.palette_material(sprite, fins[4], NAME, emission_strength=3.0 if fins[4] == 119 else 1.5))
    FIN = 7
    R = lambda r: lib.row(r - up)  # noqa: E731
    E = lambda r: lib.ey(r - up)  # noqa: E731
    bm = bmesh.new()

    # Hull: columns 5-18, rows 10-22, squarish with a round bottom.
    hull = lib.Profile([(E(y), w * U, h, -0.02) for y, w, h in (
        (9.7, 0.0, 0.0), (10.0, 3.2, 0.12), (10.6, 5.0, 0.18), (11.6, 6.4, 0.23), (13.0, 7.0, 0.26),
        (17.0, 7.0, 0.27), (19.5, 6.9, 0.25), (20.6, 6.0, 0.22), (21.6, 4.6, 0.17), (22.6, 2.4, 0.1),
        (23.0, 0.0, 0.0))])
    hull.build(bm, sides=18, mat_index=HULL)
    # Lighter shoulders over the bar's top (rows 10-11, columns 6-8 and 15-17).
    for s in (-1, 1):
        lib.ellipsoid(bm, (s * 3.6 * U, R(10.8), 0.06), (2.2 * U, 1.4 * U, 0.12), segments=10, rings=6,
                      mat_index=SHOULDER)

    # Knob on top (rows 8-10, columns 10-13).
    lib.ellipsoid(bm, (0.0, R(9.2), 0.06), (2.3 * U, 1.8 * U, 0.12), segments=12, rings=6, mat_index=KNOB)

    # Dark slot down the front, rows 12-20, between the dark lines at columns 9 and 14.
    lib.drape_patch(bm, hull.top, -2.6 * U, 2.6 * U, E(20.2), E(15.0), nx=4, ny=5, lift=0.006,
                    depth=0.05, mat_index=SLOT)

    # The bar across the upper hull (rows 12-15), riding over it, and the thin arms out to the tips.
    yb, zb = R(13.5), 0.13
    lib.polyline_tube(bm, [(-7.0 * U, yb, zb), (7.0 * U, yb, zb)], 2.0 * U, sides=12, mat_index=BAR)
    for s in (-1, 1):
        lib.polyline_tube(bm, [(s * 5.0 * U, yb, zb), (s * (tip - 0.4) * U, yb, zb), (s * tip * U, yb, zb)],
                          [1.1 * U, 1.1 * U, 0.6 * U], sides=8, mat_index=ARM)
        # Collar where the bar ends.
        lib.polyline_tube(bm, [(s * 6.4 * U, yb, zb), (s * 7.2 * U, yb, zb)], 2.15 * U, sides=12, mat_index=ARM)
    # Shiny hub in the middle of the bar (columns 10-11, rows 12-15).
    lib.ellipsoid(bm, (-0.4 * U, R(13.6), zb), (2.4 * U, 2.6 * U, 2.6 * U), segments=14, rings=8, mat_index=HUB)

    # Red fins opening round the arms.
    if fins:
        cx, cr, rx, ry, _ = fins
        for s in (-1, 1):
            poly = lib.ellipse_polygon(s * cx * U, R(cr), rx * U, ry * U, n=12)
            if s < 0:
                poly = poly[::-1]
            common.slab(bm, poly, 0.04, z=zb - 0.02, mat_index=FIN)

    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, (frame, spec) in enumerate(zip(frames, FRAMES)):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        models.append((name, [build_one(sprite, name, *spec)], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
