"""SuperCarrot (player ship, tyrian.shp#8 frame 119 and its banking frames 115-123): a 3D version
of its sprite.

A flying carrot, point up the screen: a round orange root with ridges, one brown eye with a
glowing pupil in the middle of it, and a tuft of three green leaves trailing behind. Built
around the middle of sprite column 11.

Run: blender --background --python assets/blender/ships/ship-supercarrot.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import dome, loft, tube  # noqa: E402

NAME = "ship-supercarrot"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the middle of sprite column 11


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(122, metallic=0.0, roughness=0.5),  # 0 orange root
        pal(124, metallic=0.0, roughness=0.4),  # 1 light ridges
        pal(186, metallic=0.1, roughness=0.35),  # 2 brown eye
        pal(176, metallic=0.0, roughness=0.6),  # 3 dark socket
        pal(126, emission_strength=4.0),  # 4 glowing pupil
        pal(199, metallic=0.0, roughness=0.6),  # 5 leaves
        pal(195, metallic=0.0, roughness=0.6),  # 6 stem
        pal(118, metallic=0.0, roughness=0.6),  # 7 dark red-orange base
    ]
    ROOT_, RIDGE, EYE, SOCKET, PUPIL, LEAF, STEM, BASE = range(8)
    bm = bmesh.new()

    # The root, tip (row 0) to its flat top (row 18): (row, half width px); round in section.
    body = [(0.2, 0.0), (1.0, 0.6), (3.0, 1.5), (5.0, 2.5), (7.0, 3.4), (10.0, 4.5), (13.0, 5.4),
            (15.0, 5.6), (16.5, 5.2), (17.5, 4.3), (18.4, 2.8)]
    ring = lambda r, w: (r, AXIS, w, w * 0.6 if w else 0, 0.0)  # noqa: E731
    loft(bm, [ring(r, w) for r, w in body], sides=16, mat=ROOT_)
    loft(bm, [(18.2, AXIS, 3.0, 1.9, 0.0), (19.0, AXIS, 2.0, 1.3, 0.0)], sides=12, mat=BASE)
    # Ridges round the root (the light bands at rows 6, 8 and 14).
    for r, w in ((6.4, 2.95), (8.6, 3.9), (14.4, 5.6)):
        loft(bm, [(r - 0.35, AXIS, w + 0.15, (w + 0.15) * 0.6, 0.0), (r + 0.35, AXIS, w + 0.15, (w + 0.15) * 0.6, 0.0)],
             sides=16, mat=RIDGE)

    # The eye (rows 9-13, columns 9-13): a dark socket, a brown eyeball and a glowing pupil on top.
    dome(bm, AXIS, 11.8, 2.6, 2.4, 1.1, z=2.3, rings=2, sides=14, mat=SOCKET)
    dome(bm, AXIS, 11.3, 2.3, 2.2, 1.9, z=2.3, rings=4, sides=14, mat=EYE)
    dome(bm, AXIS, 11.3, 0.9, 0.9, 0.4, z=4.0, rings=2, sides=8, mat=PUPIL)

    # The stem (rows 18-21) and three leaves fanning out behind: (col, row, half width, half height, z).
    tube(bm, [(AXIS, 18.0, 1.5, 1.0, 0.0), (11.0, 20.0, 1.4, 0.9, -0.2), (10.8, 21.2, 1.3, 0.8, -0.3)],
         sides=8, mat=STEM)
    leaves = [
        # Left: down and out to column 6 at row 25.
        [(10.2, 20.6, 1.1, 0.35, -0.2), (8.6, 21.9, 1.6, 0.4, -0.3), (7.2, 23.3, 1.2, 0.35, -0.5),
         (5.8, 25.2, 0, 0, -0.7)],
        # Middle: straight back to row 27.
        [(11.0, 20.5, 1.6, 0.4, -0.1), (11.4, 22.5, 2.2, 0.45, -0.2), (11.1, 24.5, 1.5, 0.4, -0.4),
         (10.5, 27.0, 0, 0, -0.6)],
        # Right: out to column 15 at row 23.
        [(11.8, 20.8, 1.1, 0.35, -0.2), (13.3, 22.0, 1.3, 0.4, -0.3), (15.2, 23.8, 0, 0, -0.5)],
    ]
    for leaf in leaves:
        tube(bm, leaf, sides=6, mat=LEAF, power=0.8)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
