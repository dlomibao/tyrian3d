"""Spinning twin pod (newsh8.shp, ten frames): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). A small tan craft: two ringed pods with glowing red
caps on top, joined by a rounded centre plate that has two short prongs under it. The ten frames
spin it about the screen's vertical axis, from face on (frame 19) to edge on (frame 114) and on
round, so it gets one model per distinct angle: the same craft turned. Frames that show the same
angle turned the other way (38/151, 57/132, 76/152, 95/133) look the same from above and share
a model.

Run: blender --background --python assets/blender/enemies/newsh8-19.py [-- --preview out.png]
(each model's preview is written as <model>.png next to out.png).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b035 as lib  # noqa: E402

NAME = "newsh8-19"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)
PX = lib.PX

# Distinct angles (degrees about the screen's vertical axis) and the frames that show each. The
# pods are 4 px either side of the centre face on; the frames show them 3.5, 2.5, 1.5 and 0.5 px
# out, then edge on.
ANGLES = [(0, [19]), (29, [38, 151]), (51, [57, 132]), (68, [76, 152]), (83, [95, 133]), (90, [114])]
POD_X = 4.0  # px from the centre, face on
Z_SCALE = 0.6  # keep the edge-on frames from standing too tall


def build(sprite, name, angle):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh8_19", **kw)  # noqa: E731
    mats = [
        pal(26, metallic=0.35, roughness=0.4),  # 0 pod tan
        pal(28, metallic=0.4, roughness=0.3),  # 1 light rings
        pal(22, metallic=0.3, roughness=0.55),  # 2 dark grooves, nozzle
        pal(24, metallic=0.3, roughness=0.45),  # 3 centre plate
        pal(119, emission_strength=3.5),  # 4 glowing red caps
        pal(19, metallic=0.2, roughness=0.7),  # 5 dark recess under the plate
    ]
    POD, RING, GROOVE, PLATE, GLOW, DARK = range(6)
    bm = bmesh.new()
    y = G.y

    # Pods (rows 1-12): a red cap, a long tan barrel, a light ring at row 8, a groove at row 9,
    # a lower barrel and an open nozzle at the bottom.
    r = 1.45 * PX
    for side in (-1, 1):
        start = len(bm.verts)
        lib.sweep(bm, [(0, y(0.6), 0, 0.0, 0.0), (0, y(0.9), 0, r * 0.75, r * 0.75), (0, y(1.6), 0, r, r)],
                  sides=10, mat=GLOW, cap_end=False)
        lib.sweep(bm, [(0, y(1.6), 0, r, r), (0, y(7.4), 0, r, r)], sides=10, mat=POD,
                  cap_start=False, cap_end=False)
        lib.sweep(bm, [(0, y(7.4), 0, r, r), (0, y(7.6), 0, r * 1.08, r * 1.08), (0, y(8.4), 0, r * 1.08, r * 1.08),
                       (0, y(8.6), 0, r, r)], sides=10, mat=RING, cap_start=False, cap_end=False)
        lib.sweep(bm, [(0, y(8.6), 0, r, r), (0, y(9.0), 0, r * 0.9, r * 0.9), (0, y(9.4), 0, r, r)],
                  sides=10, mat=GROOVE, cap_start=False, cap_end=False)
        lib.sweep(bm, [(0, y(9.4), 0, r, r), (0, y(12.0), 0, r * 0.95, r * 0.95)], sides=10, mat=POD,
                  cap_start=False, cap_end=False)
        lib.sweep(bm, [(0, y(12.0), 0, r * 0.95, r * 0.95), (0, y(12.4), 0, r * 0.8, r * 0.8),
                       (0, y(12.0), 0, r * 0.45, r * 0.45)], sides=10, mat=GROOVE, cap_start=False)
        lib.transform(bm, start, lambda v, s=side: v + Vector((s * POD_X * PX, 0, 0)))

    # Centre plate between the pods (rows 2-8), rounded front and back, and a narrower tab under
    # it (rows 8-9) ending in two prongs (row 10) with a dark recess between them.
    lib.sweep(bm, [(0, y(1.5), 0, 2.4 * PX, 0.6 * PX), (0, y(1.9), 0, 3.0 * PX, 0.8 * PX),
                   (0, y(7.6), 0, 3.0 * PX, 0.8 * PX), (0, y(8.0), 0, 2.2 * PX, 0.7 * PX),
                   (0, y(9.4), 0, 2.0 * PX, 0.65 * PX)], sides=8, mat=PLATE)
    lib.sweep(bm, [(0, y(8.6), -0.1 * PX, 1.2 * PX, 0.5 * PX), (0, y(9.6), -0.1 * PX, 1.2 * PX, 0.5 * PX)],
              sides=6, mat=DARK)
    for side in (-1, 1):
        start = len(bm.verts)
        lib.sweep(bm, [(0, y(9.0), 0, 0.55 * PX, 0.5 * PX), (0, y(10.4), 0, 0.5 * PX, 0.45 * PX),
                       (0, y(10.8), 0, 0.0, 0.0)], sides=6, mat=PLATE)
        lib.transform(bm, start, lambda v, s=side: v + Vector((s * 1.5 * PX, 0, 0)))

    # Turn the craft about the vertical (sprite Y) axis.
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    lib.transform(bm, 0, lambda v: Vector((v.x * ca - v.z * sa, v.y, (v.x * sa + v.z * ca) * Z_SCALE)))
    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    out = lib.preview_arg()
    for i, (angle, frames) in enumerate(ANGLES):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, angle)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": frames}])
        if out:
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh8-{frames[0]}.png"
            common.render_preview([obj], out if i == 0 else out.with_name(f"{name}.png"), ref, size=1)


if __name__ == "__main__":
    main()
