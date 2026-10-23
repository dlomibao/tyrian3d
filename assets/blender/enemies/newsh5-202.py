"""Small grey eyeball (newsh5.shp frames 202, 221): a 3D version of its sprite.

Seen in episode 4 (level 20). A small grey ball with a dark socket and pupil looking down the
screen. The two frames turn the ball (round, then tall and narrow), so each gets a model:
newsh5-202 and newsh5-202-f2.

Run: blender --background --python assets/blender/enemies/newsh5-202.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-202"
ROOT = common.repo_root(__file__)

# Per frame, in sprite pixels (12x14 tile): the ball (centre col, row, half width, half height)
# and the eye seen from above: dark socket, grey ring, black pupil (col, row, rx, ry).
FRAMES = {
    202: {"body": (6.0, 6.0, 4.9, 4.9), "iris": (6.0, 7.6, 2.6, 2.0),
          "ring": (6.1, 8.0, 1.7, 1.3), "pupil": (6.2, 8.3, 1.2, 0.9)},
    221: {"body": (6.0, 6.0, 3.9, 5.9), "iris": (6.0, 7.8, 1.6, 2.8),
          "ring": (6.2, 8.2, 1.1, 1.9), "pupil": (6.4, 8.6, 0.8, 1.3)},
}


def build(sprite, name, frame):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(11, metallic=0.35, roughness=0.3),  # 0 grey ball
        pal(4, metallic=0.2, roughness=0.4),  # 1 dark socket
        pal(7, metallic=0.3, roughness=0.3),  # 2 iris ring
        pal(2, metallic=0.1, roughness=0.15),  # 3 pupil
    ]
    bm = bmesh.new()
    lib.eyeball(bm, frame, 1, 0.18, (0, 1, 2, 3), sides=20)
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for i, (index, frame) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, frame)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [index]}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh5-{index}.png"
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=1)


if __name__ == "__main__":
    main()
