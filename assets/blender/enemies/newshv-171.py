"""Blue rod (newshv.shp frame 171, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 2 (level 2.17). A short steel-blue cylinder lying across the screen (columns
1-10, rows 3-8) with rounded ends, two dark grooves (columns 3 and 8) and a brighter collar in
the middle where the highlight sits. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshv-171.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b043 as lib  # noqa: E402

NAME = "newshv-171"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)
AXIS = 6.0  # row edge of the rod's axis (rows 3-8)
R = 3.0  # radius in px across the screen
H = 0.17  # half height


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(59, metallic=0.6, roughness=0.3),  # 0 rod
        pal(55, metallic=0.5, roughness=0.5),  # 1 grooves
        pal(60, metallic=0.7, roughness=0.2),  # 2 bright collar
    ]
    ROD, GROOVE, COLLAR = range(3)
    bm = bmesh.new()

    def seg(sections, mat):
        lib.loft_x(bm, G, AXIS, [(c, w, w / R * H, 0.0) for c, w in sections], sides=12, mat=mat)

    seg([(1.0, 0.0), (1.15, 1.9), (1.5, 2.7), (2.0, 3.0), (3.05, 3.0)], ROD)  # rounded left end
    seg([(2.95, 2.6), (4.05, 2.6)], GROOVE)
    seg([(3.95, 3.0), (5.05, 3.0)], ROD)
    seg([(4.95, 3.1), (7.05, 3.1)], COLLAR)
    seg([(6.95, 3.0), (8.05, 3.0)], ROD)
    seg([(7.95, 2.6), (9.05, 2.6)], GROOVE)
    seg([(8.95, 3.0), (10.0, 3.0), (10.5, 2.7), (10.85, 1.9), (11.0, 0.0)], ROD)  # rounded right end
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    lib.silhouette_report(obj, sprite["frames"][0]["pixels"], G)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
