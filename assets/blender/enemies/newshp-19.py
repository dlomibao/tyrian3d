"""Small missile (newshp.shp frames 19, 38, 57, 76): a 3D version of its sprite.

Seen in episode 1 (level 1.21). A 12x14 px rocket lying nose up the screen: a wide blue-grey
warhead with a red light at its tip, a slim brown body and a grey tail. The four frames only
brighten the red light, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshp-19.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b123 as lib  # noqa: E402

NAME = "newshp-19"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(103, metallic=0.3, roughness=0.4),  # 0 blue-grey warhead
        pal(10, metallic=0.4, roughness=0.3),  # 1 grey warhead stripe
        pal(25, metallic=0.3, roughness=0.4),  # 2 brown body
        pal(26, metallic=0.45, roughness=0.35),  # 3 light brown body ridge
        pal(9, metallic=0.6, roughness=0.35),  # 4 grey tail
        pal(120, emission_strength=4.0),  # 5 red tip light
    ]
    HEAD, STRIPE, BODY, RIDGE, TAIL, LIGHT = range(6)
    bm = bmesh.new()
    zc = 0.15  # the rocket lies on the ground, its axis this high

    # Warhead (columns 4-8, rows 0-4): flat-nosed and wide, rounding into the body.
    lib.loft_y(bm, G, 6.0, [(0.0, 1.6, 0.1, zc), (0.4, 2.4, 0.14, zc), (1.0, 2.6, 0.15, zc),
                            (4.4, 2.6, 0.15, zc), (5.0, 1.9, 0.12, zc)], sides=12, mat=HEAD)
    lib.loft_y(bm, G, 6.0, [(1.4, 0.6, 0.02, zc + 0.145), (4.6, 0.6, 0.02, zc + 0.145)], sides=6, mat=STRIPE)
    # Red light on the nose (column 6, rows 0-2).
    lib.ellipsoid(bm, G, 6.0, 0.6, zc + 0.06, 1.0, 1.0, 0.09, mat=LIGHT, segments=10, rings=6)
    # Brown body (columns 5-7, rows 5-9) with a light ridge on top.
    lib.loft_y(bm, G, 6.0, [(4.6, 1.6, 0.12, zc), (9.6, 1.6, 0.12, zc)], sides=10, mat=BODY)
    lib.loft_y(bm, G, 6.0, [(5.4, 0.5, 0.02, zc + 0.115), (9.2, 0.5, 0.02, zc + 0.115)], sides=6, mat=RIDGE)
    # Grey tail (rows 10-12) tapering to the nozzle at row 13.
    lib.loft_y(bm, G, 6.0, [(9.5, 1.6, 0.12, zc), (11.5, 1.5, 0.11, zc), (12.8, 1.1, 0.09, zc),
                            (13.6, 0.6, 0.06, zc), (13.9, 0.0, 0.0, zc)], sides=10, mat=TAIL)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
