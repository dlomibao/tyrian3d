"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275): a 3D version of
its sprite.

A U-shaped band standing on edge, open end forward, with a bell-shaped brown pod hung in the
middle on two short struts. Seen from above (the level frame) the band is a thin line; the
banking frames show its grey and brown sides, so it is a tall ribbon: grey arms with dark
joints, turning brown where it curves round behind the pod. Built around the middle of sprite
column 11.

Run: blender --background --python assets/blender/ships/ship-u-ship.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import dome, loft, tube  # noqa: E402

NAME = "ship-u-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the middle of sprite column 11

BAND_W = 0.6  # half thickness of the band, px (one sprite pixel wide from above)
BAND_H = 2.3  # half height of the band, px


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.65, roughness=0.3),  # 0 grey arms
        pal(5, metallic=0.5, roughness=0.5),  # 1 dark joints
        pal(26, metallic=0.5, roughness=0.4),  # 2 brown curve
        pal(24, metallic=0.45, roughness=0.4),  # 3 brown pod
        pal(163, metallic=0.2, roughness=0.25),  # 4 dark window and groove
        pal(7, metallic=0.6, roughness=0.4),  # 5 struts
        pal(29, metallic=0.5, roughness=0.35),  # 6 pale stripe on the pod
    ]
    ARM, JOINT, CURVE, POD, DARK, STRUT, PALE = range(7)
    bm = bmesh.new()

    def band(points, mat, w=BAND_W, h=BAND_H, **kw):
        tube(bm, [(c, r, w, h, 0.0) for c, r in points], sides=8, mat=mat, power=0.35, **kw)

    # The U's curve behind the pod (rows 20-25), brown: a half ellipse from one arm to the other.
    cx, cy, rx, ry = AXIS, 20.2, 6.0, 4.3
    curve = [(cx - rx * math.cos(t), cy + ry * math.sin(t)) for t in (math.pi * i / 10 for i in range(11))]
    band([(cx - rx, 19.8)] + curve + [(cx + rx, 19.8)], CURVE, cap_start=False, cap_end=False)
    for side in (1, -1):
        c = AXIS - rx if side == 1 else AXIS + rx
        # Grey arm (rows 7-20 at columns 5 and 17), ends flat at the front.
        band([(c, 7.7), (c, 13.0), (c, 20.0)], ARM)
        # Dark joints round the arm (rows 14 and 19).
        for r in (14.0, 19.0):
            band([(c, r), (c, r + 1.0)], JOINT, w=BAND_W + 0.15, h=BAND_H + 0.15)
        # Strut from the arm to the pod (row 16).
        strut = [(c, 16.5), (AXIS - 2.0 if side == 1 else AXIS + 2.0, 16.5)]
        tube(bm, [(x, r, 0.55, 0.6, 0.0) for x, r in strut], sides=6, mat=STRUT)

    # The pod: a bell, round at the front (row 12), flat at the back (row 20).
    pod = [(12.3, 0, 0, 0.3), (12.8, 1.4, 1.3, 0.2), (13.6, 2.1, 1.9, 0.1), (15.0, 2.5, 2.2, 0.0),
           (19.9, 2.5, 2.2, 0.0)]
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in pod], sides=14, mat=POD)
    # Dark window at the front (rows 13-14) and the shaded groove down the right side (column 12).
    dome(bm, AXIS + 0.4, 14.3, 1.4, 1.1, 0.5, z=1.75, rings=2, sides=10, mat=DARK)
    loft(bm, [(15.2, AXIS + 0.9, 0.45, 0.3, 2.1), (19.9, AXIS + 0.9, 0.45, 0.3, 2.1)], sides=6, mat=DARK)
    # Pale highlight stripe down the left (column 10, rows 16-19).
    loft(bm, [(15.6, AXIS - 1.2, 0.45, 0.3, 1.95), (19.9, AXIS - 1.2, 0.45, 0.3, 1.95)], sides=6, mat=PALE)

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
