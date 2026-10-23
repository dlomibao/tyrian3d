"""Dome walker (newsh8.shp frames 115, 117, 119): a 3D version of its sprite.

Seen in episode 3 (level 3.4). A grey metal dome with a red lamp on its crown and a glowing red
core under its front edge, sitting on a brown crossbar with two legs that end in hooked feet.
The three frames only pulse the lamp and the core (and twitch the hooks by a pixel), so one
model covers them all.

Run: blender --background --python assets/blender/enemies/newsh8-115.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b060 as L  # noqa: E402

NAME = "newsh8-115"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = L.px(12)  # the sprite is mirror symmetric about pixel column 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.75, roughness=0.3),  # 0 grey dome
        pal(5, metallic=0.7, roughness=0.4),  # 1 dark grey: shaded side, collar
        pal(13, metallic=0.8, roughness=0.2),  # 2 light grey highlight
        pal(123, emission_strength=3.5),  # 3 crown lamp
        pal(121, emission_strength=4.0),  # 4 core
        pal(126, emission_strength=5.0),  # 5 core's hot centre
        pal(23, metallic=0.3, roughness=0.55),  # 6 brown frame
        pal(19, metallic=0.25, roughness=0.6),  # 7 dark brown
        pal(27, metallic=0.35, roughness=0.45),  # 8 light brown
        pal(115, metallic=0.3, roughness=0.5),  # 9 dark red lamp and core sockets
    ]
    GREY, DGREY, LGREY, LAMP, CORE, HOT, BROWN, DBROWN, LBROWN, SOCKET = range(10)
    pixels = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    # The dome (rows 3-10 at the middle), a full-width hood: (row, half width px, half height, z).
    dome = L.loft_y(bm, 12, [(2.9, 3.0, 0.05, 0.02), (3.6, 5.0, 0.1, 0.03), (4.6, 7.0, 0.15, 0.04),
                              (5.8, 8.4, 0.19, 0.04), (7.2, 9.6, 0.22, 0.04), (8.8, 10.3, 0.235, 0.04),
                              (10.0, 10.4, 0.23, 0.04), (10.9, 10.2, 0.2, 0.03)], sides=16, mat=GREY)
    # Its skirts reach down both sides to row 14 (columns 2-7 and 17-22).
    skirt = L.loft_y(bm, 4.6, [(8.5, 2.6, 0.15, 0.02), (11.0, 2.8, 0.16, 0.02), (13.6, 2.6, 0.13, 0.0),
                               (14.4, 1.6, 0.08, 0.0)], sides=10, mat=GREY)
    skirt += L.mirror(bm, AXIS, skirt)
    # Dark underside of the front edge, over the core (rows 10-12).
    L.loft_y(bm, 12, [(10.4, 6.0, 0.1, -0.02), (12.2, 5.6, 0.08, -0.04)], sides=12, mat=DGREY)
    L.paint(bm, dome + skirt, pixels,
            lambda v, s: LGREY if v >= 11.5 else (GREY if v >= 6.5 else DGREY))

    # Red lamp on the crown (rows 0-3), half sunk into the back of the dome.
    L.ellipsoid(bm, L.P(12.6, 1.8, 0.07), (3.6 * L.PX, 2.1 * L.PX, 0.08), segments=14, rings=7, mat=SOCKET)
    L.ellipsoid(bm, L.P(12.5, 1.6, 0.1), (2.4 * L.PX, 1.4 * L.PX, 0.075), segments=12, rings=6, mat=LAMP)

    # Brown crossbar under the dome (rows 15-17) and the struts up into the skirts (rows 13-14).
    bar = L.ptube(bm, [(2.9, 16.0, -0.04, 1.6), (3.6, 15.9, -0.04, 2.0), (20.4, 15.9, -0.04, 2.0),
                       (21.1, 16.0, -0.04, 1.6)], sides=12, mat=BROWN, flat=0.75)
    strut = L.plate(bm, [(8, 13), (10, 13), (10, 15), (8, 15)], -0.12, 0.04, mat=DBROWN)
    strut += L.mirror(bm, AXIS, strut)

    # Glowing core under the front of the dome (rows 12-16).
    L.ellipsoid(bm, L.P(12, 14.2, -0.02), (3.4 * L.PX, 3.0 * L.PX, 0.13), segments=14, rings=7, mat=SOCKET)
    L.ellipsoid(bm, L.P(12, 14.1, 0.0), (2.7 * L.PX, 2.4 * L.PX, 0.13), segments=14, rings=7, mat=CORE)
    L.ellipsoid(bm, L.P(12, 14.0, 0.08), (1.2 * L.PX, 1.1 * L.PX, 0.065), segments=10, rings=5, mat=HOT)

    # Left leg (column 8-9) down to a hooked foot (rows 21-26) whose claw curls up at column 1-2.
    leg = L.ptube(bm, [(8.6, 16.5, -0.06, 1.1), (8.6, 21.0, -0.08, 1.2), (8.0, 23.0, -0.09, 1.6)],
                  sides=8, mat=BROWN)
    leg += L.ellipsoid(bm, L.P(6.2, 23.9, -0.09), (3.4 * L.PX, 2.7 * L.PX, 0.11), segments=12, rings=6, mat=BROWN)
    leg += L.ptube(bm, [(4.4, 24.2, -0.09, 2.0), (3.0, 23.8, -0.08, 1.6), (2.0, 22.6, -0.06, 1.2),
                        (1.7, 21.2, -0.05, 0.8), (1.8, 20.2, -0.05, 0.0)], sides=8, mat=LBROWN)
    leg += L.mirror(bm, AXIS, leg)
    L.paint(bm, leg + bar, pixels, lambda v, s: LBROWN if v >= 24.5 else (BROWN if v >= 20.5 else DBROWN))

    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = L.preview_args()
    if out:
        L.preview([obj], ROOT, NAME, sprite["frames"][0]["image"], out)


if __name__ == "__main__":
    main()
