"""Red boulder (newsh8.shp frame 102): a 3D version of its sprite.

Seen in episode 3 (levels 3.4 and 3.19). A small (12x14 px) ground object: a smooth red
egg-shaped dome lit from the top left, with a lighter rim of reflected light round its lower
right (reflected light, so not modelled). One frame, one model: a slightly egg-shaped dome
sitting on the ground.

Run: blender --background --python assets/blender/enemies/newsh8-102.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b082  # noqa: E402

NAME = "newsh8-102"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12


def px(c):
    """Sprite column (pixel centre) to Blender X (12x14 tile)."""
    return (c + 0.5 - 6) / 12


def row(r):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (7 - (r + 0.5)) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(72, metallic=0.25, roughness=0.35),  # 0 red body
    ]
    BODY = 0
    bm = bmesh.new()
    # The dome covers columns 0-10, rows 0-12 (centre column 5, row 6).
    lib_b082.ellipsoid(bm, px(5.0), row(6.1), 0.06, 5.5 * PX, 6.5 * PX, 0.4, mat=BODY, segments=20, rings=10,
                       floor=0.0)
    return lib_b082.to_object(NAME, bm, mats, coll)


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
