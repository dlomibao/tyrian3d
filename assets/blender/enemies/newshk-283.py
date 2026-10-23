"""Grey twin-pronged heater (newshk.shp frame 283): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A grey housing with a sloped roof at the back (top of the
sprite), a dark sunken window framed in light grey and two ribbed strips with rivets down its
sides, a dark lip under it, and two thick prongs hanging down the screen. Each prong's inner
side is a dark slot with red-hot elements glowing in it (a bright spot low on the left one), and
each ends in a pale tip. One frame.

Run: blender --background --python assets/blender/enemies/newshk-283.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b010 as lib  # noqa: E402
from lib_b010 import ex, ey, gx, gy  # noqa: E402

NAME = "newshk-283"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.55, roughness=0.4),  # 0 grey housing
        pal(8, metallic=0.55, roughness=0.45),  # 1 darker grey sides and roof
        pal(11, metallic=0.6, roughness=0.3),  # 2 light grey frame and ribs
        pal(5, metallic=0.5, roughness=0.5),  # 3 dark grey lip and grooves
        pal(3, metallic=0.4, roughness=0.6),  # 4 dark window and slots
        pal(13, metallic=0.6, roughness=0.25),  # 5 pale tips and rivets
        pal(116, emission_strength=3.0),  # 6 red-hot elements
        pal(123, emission_strength=5.0),  # 7 hot spot
        pal(10, metallic=0.55, roughness=0.35),  # 8 light grey strips
        pal(114, emission_strength=1.5),  # 9 dull red glow at the bottom of the slots
    ]
    GREY, SIDE, LIGHT, LIP, DARK, PALE, HOT, SPOT, STRIP, EMBER = range(10)
    bm = bmesh.new()
    top = 0.13  # housing top

    # Housing (rows 4-12), its sides bevelled down (the darker columns 0-1 and 22-23).
    lib.extrude_y(bm, [(ex(0), -0.12), (ex(24), -0.12), (ex(24), top - 0.08), (ex(22), top),
                       (ex(2), top), (ex(0), top - 0.08)], ey(13), ey(4), mat=GREY)
    # Sloped roof behind it (rows 1-3): a wedge falling away towards the top of the sprite.
    lib.prism(bm, [(ex(4), ey(4.2), top), (ex(20), ey(4.2), top), (ex(14), ey(1), top - 0.1),
                   (ex(10), ey(1), top - 0.1)], -0.08, mat=SIDE)
    # Dark lip under the housing (row 13), right across.
    lib.box(bm, 0, 13, 24, 14, -0.1, top - 0.04, mat=LIP)

    # Window: a light frame (columns 7-16, rows 7-10) round a dark sunken pane.
    lib.box(bm, 7, 6.8, 17, 7.6, top, top + 0.03, mat=LIGHT)
    lib.box(bm, 7, 10, 17, 11, top, top + 0.03, mat=LIGHT)
    lib.box(bm, 7, 6.8, 8, 11, top, top + 0.03, mat=LIGHT)
    lib.box(bm, 16, 6.8, 17, 11, top, top + 0.03, mat=LIGHT)
    lib.box(bm, 8, 7.6, 16, 10, top - 0.03, top + 0.005, mat=DARK)

    # Ribbed strips down the sides (columns 2 and 4, 19 and 21) with rivets (rows 4 and 9).
    for c in (2, 4, 19, 21):
        lib.box(bm, c + 0.1, 4, c + 0.9, 13, top - 0.01, top + 0.025, mat=STRIP)
    for c in (4, 19):
        for r in (4, 9):
            lib.stud(bm, gx(c), gy(r), top + 0.02, 0.6 * P, 0.03, mat=PALE)

    # Prongs (rows 14-24): grey blocks rounded on their outer sides, a groove down each.
    for c0, c1, groove, slot in ((0, 6, 3, (6, 10)), (17, 23, 19, (13, 17))):
        mid, half = (ex(c0) + ex(c1)) / 2, (ex(c1) - ex(c0)) / 2
        start = len(bm.verts)
        lib.rod_y(bm, 0.0, [(ey(14), half, 0.12, 0.0), (ey(23), half, 0.12, 0.0),
                            (ey(25.5), half * 0.95, 0.11, -0.01), (ey(27.2), half * 0.8, 0.08, -0.02),
                            (ey(28), half * 0.6, 0.04, -0.02)], sides=10, mat=GREY)
        bm.verts.ensure_lookup_table()
        for v in bm.verts[start:]:
            v.co.x += mid
        lib.box(bm, groove + 0.15, 14, groove + 0.85, 24, 0.0, 0.122, mat=LIP)
        # The slot on the prong's inner side, lower than the prong, glowing dull red inside.
        lib.box(bm, slot[0], 14, slot[1], 24.5, -0.1, 0.0, mat=DARK)
        lib.box(bm, slot[0] + 0.5, 14, slot[1] - 0.5, 24.3, 0.0, 0.03, mat=EMBER)
        # Pale tip at the prong's inner bottom corner (columns 4-7 and 16-19, rows 25-27).
        tip = gx(5) if c0 == 0 else gx(18)
        lib.rod_y(bm, tip, [(ey(24.6), 0.0, 0.0, 0.0), (ey(25), 1.6 * P, 0.1, 0.0), (ey(27), 1.8 * P, 0.1, 0.0),
                            (ey(27.8), 1.3 * P, 0.07, -0.01), (ey(28), 0.0, 0.0, -0.01)],
                  sides=10, mat=PALE)

    # Red-hot elements in the slots (columns 7 and 9, 13 and 15).
    for c, r0, r1 in ((7, 16, 24.5), (9, 14, 24), (13, 14, 24), (15, 16, 24.5)):
        lib.rod_y(bm, gx(c), [(ey(r0), 0.0, 0.0, 0.05), (ey(r0) - 0.4 * P, 0.6 * P, 0.035, 0.05),
                              (ey(r1) + 0.4 * P, 0.6 * P, 0.035, 0.05), (ey(r1), 0.0, 0.0, 0.05)],
                  sides=6, mat=HOT)
    lib.stud(bm, gx(9), gy(21), 0.06, 0.6 * P, 0.035, mat=SPOT)
    lib.stud(bm, gx(13), gy(21), 0.06, 0.5 * P, 0.03, mat=SPOT)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
