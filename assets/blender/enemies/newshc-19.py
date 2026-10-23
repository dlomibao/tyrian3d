"""Purple bollard (newshc.shp frame 19, size 1): a 3D version of its sprite.

Seen in episode 1 (level 1.19) and 3 (3.23). A small purple post lying on the ground: a wide
round cap at the back (rows 1-5) with a dark seam under it, then a narrower body with a light
rim at its top that tapers to a rounded front end. One frame.

Run: blender --background --python assets/blender/enemies/newshc-19.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b110 as lib  # noqa: E402

NAME = "newshc-19"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
FR = lib.Frame(12, 14)
PX = lib.PX


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(87, metallic=0.4, roughness=0.4),  # 0 cap
        pal(83, metallic=0.3, roughness=0.6),  # 1 dark seam
        pal(88, metallic=0.4, roughness=0.4),  # 2 body
        pal(92, metallic=0.5, roughness=0.3),  # 3 light rim
    ]
    CAP, SEAM, BODY, RIM = range(4)
    bm = bmesh.new()
    ye = FR.ye

    def hh(w, top):
        return top * math.sqrt(min(1.0, w / 4.0)) if w else 0.0

    cap = [(0.9, 0.0), (1.0, 2.6), (1.5, 4.2), (2.2, 5.0), (4.8, 5.0), (5.2, 4.8), (5.6, 4.4), (6.1, 3.8)]
    lib.loft_y(bm, 0.0, [(ye(r), w * PX, hh(w, 0.36), 0.0) for r, w in cap], sides=14, arc=(0, math.pi),
               mats=[CAP, CAP, CAP, CAP, SEAM, SEAM, SEAM], mat=CAP)
    body = [(5.8, 3.9), (6.6, 3.8), (7.0, 3.5), (9.0, 3.1), (11.0, 2.3), (12.4, 2.0), (12.9, 1.4), (13.1, 0.0)]
    lib.loft_y(bm, 0.0, [(ye(r), w * PX, hh(w, 0.28), 0.0) for r, w in body], sides=14, arc=(0, math.pi),
               mats=[RIM, RIM, BODY, BODY, BODY, BODY, BODY], mat=BODY)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        common.render_preview([obj], out, lib.sprite_png(ROOT, NAME, sprite), size=1)


if __name__ == "__main__":
    main()
