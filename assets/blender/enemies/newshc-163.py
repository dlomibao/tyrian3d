"""Blue housing without its cannon (newshc.shp frame 163): a 3D version of its sprite.

Seen in episodes 1 (level 1.19) and 3 (3.23, 3.6). The same machine as newshc-155 (built by
assembly-newshc-165.py) with no cannon: a blue hood of two lobes, a grey housing with dark ports
on its sloped front, a grey bracket on the ground below with a long rod down its middle, and a
small blue fitting under the bracket (rows 25-26). One frame, one model.

Run: blender --background --python assets/blender/enemies/newshc-163.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b097 import PX, X, YE, pbox, preview, preview_args, sweep, to_object, turret_base  # noqa: E402

NAME = "newshc-163"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(57, metallic=0.2, roughness=0.4),  # 0 blue hood
        pal(60, metallic=0.4, roughness=0.3),  # 1 hood highlight
        pal(52, metallic=0.3, roughness=0.6),  # 2 dark blue skirt
        pal(54, metallic=0.4, roughness=0.4),  # 3 darker blue corner strips
        pal(106, metallic=0.6, roughness=0.35),  # 4 grey housing
        pal(109, metallic=0.6, roughness=0.3),  # 5 housing top edge
        pal(98, metallic=0.4, roughness=0.6),  # 6 dark ports
        pal(2, metallic=0.2, roughness=0.8),  # 7 dark floor
        pal(7, metallic=0.6, roughness=0.4),  # 8 bracket rails
        pal(4, metallic=0.5, roughness=0.5),  # 9 bracket top bar
        pal(10, metallic=0.6, roughness=0.3),  # 10 centre rod
        pal(59, metallic=0.5, roughness=0.3),  # 11 blue fitting
        pal(100, metallic=0.4, roughness=0.5),  # 12 fitting body
        pal(96, metallic=0.2, roughness=0.8),  # 13 dark socket of the missing cannon
    ]
    M = dict(hood=0, hood_hi=1, skirt=2, corner=3, housing=4, housing_hi=5, port=6, floor=7, rail=8, bar=9,
             rod=10)
    bm = bmesh.new()
    turret_base(bm, M, M["corner"], centre_rod_top=13.2)
    # Dark socket where newshc-155's cannon stands (columns 9-14, row 13) and the groove between
    # the lobes (columns 11-12, rows 3-8).
    pbox(bm, 9, 12, 14, 14, 0.0, 0.17, 13)
    pbox(bm, 11, 3, 12, 9, 0.0, 0.22, 2)
    # Small blue fitting under the bracket (columns 10-13, rows 24-26).
    pbox(bm, 10, 24, 13, 25, 0.0, 0.05, 12)
    for c in (10, 13):
        sweep(bm, [(X(c), YE(24.2), 0.04, 0.5 * PX, 0.035), (X(c), YE(26.9), 0.04, 0.5 * PX, 0.035)], sides=6, mat=11)
    return to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = preview_args()
    if out:
        preview(ROOT, [obj], out, sprite)


if __name__ == "__main__":
    main()
