"""Clamshell pod (newshd.shp frames 157, 159, 161): a 3D version of its sprite.

Seen in episode 1 (level 1.5). A dark glossy egg-shaped pod on the ground, split down the middle
into two shells that slide apart to show a grey housing with a glowing red-orange eye on top
(it hides inside when they close). The frames change shape, so each gets a model:
newshd-157 wide open (157), newshd-157-f2 half open (159) and newshd-157-f3 closed (161).

Run: blender --background --python assets/blender/enemies/newshd-157.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b138 as lib  # noqa: E402
from lib_b138 import common, ex, ey  # noqa: E402

NAME = "newshd-157"

# Per frame: left shell [outer, inner] and right shell [inner, outer] column edges, and the housing
# (column edges, or None when it's shut inside) with the eye's centre column.
FRAMES = [
    {"frame": 157, "model": NAME, "left": (2, 8), "right": (16, 22), "core": (9, 15), "eye": 12.0, "legs": True},
    {"frame": 159, "model": f"{NAME}-f2", "left": (3, 9), "right": (13, 19), "core": (8.6, 13.4), "eye": 11.0,
     "legs": False},
    {"frame": 161, "model": f"{NAME}-f3", "left": (5, 11), "right": (11, 17), "core": None},
]
SHELL_RZ = 0.4
# Each shell's width (px, from its inner edge out) down its length: (row, width), from the sprite.
SHELL_W = [(1.7, 1.6), (2.5, 3.0), (3.5, 4.0), (4.5, 5.0), (5.5, 5.6), (6.5, 6.0), (10.5, 6.0), (14.5, 6.0),
           (15.5, 5.6), (16.5, 5.1), (17.5, 4.6), (18.5, 4.1), (19.5, 3.5), (20.5, 2.8), (21.5, 2.0), (22.4, 1.0),
           (22.9, 0.3)]


def shell(bm, inner, side, mat, inner_mat, steps=6):
    """One half of the pod: rounded cross-sections (a quarter ellipse from the inner edge out to the
    sprite's width at that row) lofted down its length, with a flat inner face and bottom."""
    import math
    rings = []
    for r, w in SHELL_W:
        h = SHELL_RZ * (w / 6.0) ** 0.45
        ring = [(ex(inner), ey(r), 0.0)]
        for k in range(steps + 1):
            t = (math.pi / 2) * k / steps
            ring.append((ex(inner + side * w * math.sin(t)), ey(r), h * math.cos(t)))
        rings.append(ring)
    faces = lib.ring_loft(bm, rings, mat)
    bm.normal_update()
    for f in faces:
        if abs(f.normal.x) > 0.95 and f.normal.x * side < 0:
            f.material_index = inner_mat
    return faces


def build_frame(sprite, spec, coll):
    name = spec["model"]
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.6, roughness=0.25),  # 0 shells
        pal(3, metallic=0.4, roughness=0.5),  # 1 shells' dark inner faces
        pal(10, metallic=0.6, roughness=0.25),  # 2 the right shell's lit lip
        pal(8, metallic=0.4, roughness=0.45),  # 3 housing top
        pal(3, metallic=0.3, roughness=0.6),  # 4 housing front (shade)
        pal(120, emission_strength=3.5),  # 5 eye
        pal(124, emission_strength=5.0),  # 6 eye's hot centre
        pal(5, metallic=0.4, roughness=0.5),  # 7 legs
    ]
    SHELL, INNER, LIP, TOP, FRONT, EYE, HOT, LEG = range(8)
    bm = bmesh.new()
    lo, li = spec["left"]
    shell(bm, li, -1, SHELL, INNER)
    ri, ro = spec["right"]
    shell(bm, ri, 1, SHELL, INNER)
    # The right shell's lit lip along its inner edge, over the top.
    pts = [(ex(ri) + 0.022, ey(r), max(0.02, SHELL_RZ * (w / 6.0) ** 0.45 - 0.01)) for r, w in SHELL_W[1:-1]]
    lib.polyline_tube(bm, pts, 0.028, sides=6, mat_index=LIP)

    if spec["core"]:
        c0, c1 = spec["core"]
        # Housing: a block whose top carries the eye, with a lower shaded step in front.
        lib.box(bm, ex(c0), ex(c1), ey(10.2), ey(6.0), 0.0, 0.27, TOP)
        lib.box(bm, ex(c0), ex(c1), ey(13.0), ey(10.2), 0.0, 0.15, FRONT)
        ecx = ex(spec["eye"])
        lib.dome(bm, ecx, ey(8.5), 2.1 / 12, 1.7 / 12, 0.07, z=0.26, rings=3, sides=12, mat_index=EYE)
        lib.dome(bm, ecx, ey(8.4), 0.9 / 12, 0.8 / 12, 0.095, z=0.26, rings=3, sides=8, mat_index=HOT)
        if spec.get("legs"):
            for c in (c0, c1 - 1):
                lib.box(bm, ex(c), ex(c + 1), ey(16.0), ey(13.0), 0.0, 0.11, LEG)

    return common.mesh_object(name, bm, mats, coll, smooth=True)


def build(sprite):
    coll = common.reset_collection(NAME)
    sheet = sprite["sprites"][0]
    out = []
    for spec in FRAMES:
        obj = build_frame(sprite, spec, coll)
        fi = next(i for i, f in enumerate(sprite["frames"]) if f["index"] == spec["frame"])
        sprites = [{**sheet, "frames": [spec["frame"]]}]
        out.append((spec["model"], [obj], sprites, fi))
    return out


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
