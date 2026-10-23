"""Pale crystal shard, tilted (newshv.shp frame 12): a 3D version of its sprite.

Seen in episode 2 (levels 2.12 and 2.19). The same faceted crystal as newshv-10 (a ridge down
its middle, a dark groove near the base and a rounded base cap) turned 45 degrees so it points
to the upper right of the screen. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshv-12.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b043 as lib  # noqa: E402

NAME = "newshv-12"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(92, metallic=0.25, roughness=0.3),  # 0 crystal body (lighter than newshv-10's)
        pal(88, metallic=0.2, roughness=0.5),  # 1 groove
        pal(93, metallic=0.25, roughness=0.3),  # 2 base cap
    ]
    bm = bmesh.new()
    g = lib.Grid()
    faces = lib.crystal(bm, g, (0, 1, 2), blunt=True)
    # newshv-10's crystal turned 45 degrees clockwise about its centroid (column edge 12.5, row
    # edge 15.2), moved onto this sprite's centroid (12.8, 15.2), nudged.
    lib.transform_faces(faces, -45, centre=(g.X(12.5), g.Y(15.2)), move=(0.1 / 12, -0.2 / 12, 0.0))
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    lib.silhouette_report(obj, sprite["frames"][0]["pixels"], lib.Grid(), outline=(80,))
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
