"""Blue eyeball (newsh5.shp frames 127, 129, 131): a 3D version of its sprite.

Seen in episode 4 (levels 20 and 25). A glossy blue ball with a dark socket and black pupil
looking down the screen. The three frames turn the ball, so the ball's outline and the eye's shape
change: one model per frame (newsh5-127, newsh5-127-f2, newsh5-127-f3).

Run: blender --background --python assets/blender/enemies/newsh5-127.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-127"
ROOT = common.repo_root(__file__)

# Per frame, in sprite pixels: the ball (centre col, row, half width, half height, inside the
# dark rim) and the eye seen from above: dark socket, mid-blue ring, black pupil (col, row, rx, ry).
FRAMES = {
    127: {"body": (11.5, 12.0, 10.4, 9.0), "iris": (12.5, 14.2, 5.6, 3.4),
          "ring": (12.8, 14.8, 3.6, 2.2), "pupil": (13.0, 15.2, 2.7, 1.6)},
    129: {"body": (12.0, 12.0, 10.0, 10.0), "iris": (12.5, 14.0, 5.6, 4.3),
          "ring": (12.6, 14.9, 3.3, 3.0), "pupil": (13.0, 15.8, 2.0, 2.2)},
    131: {"body": (12.0, 12.0, 9.0, 11.0), "iris": (12.2, 14.2, 5.0, 5.3),
          "ring": (12.5, 15.0, 3.0, 3.8), "pupil": (12.8, 15.7, 1.7, 3.0)},
}


def build(sprite, name, frame):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(58, metallic=0.35, roughness=0.25),  # 0 glossy blue ball
        pal(51, metallic=0.2, roughness=0.4),  # 1 dark socket
        pal(55, metallic=0.3, roughness=0.3),  # 2 iris ring
        pal(48, metallic=0.1, roughness=0.15),  # 3 pupil
    ]
    bm = bmesh.new()
    lib.eyeball(bm, frame, 2, 0.36, (0, 1, 2, 3))
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    first = None
    for i, (index, frame) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, frame)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [index]}])
        first = first or obj
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh5-{index}.png"
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=2)


if __name__ == "__main__":
    main()
