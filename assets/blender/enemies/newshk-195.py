"""Red orb (newshk.shp frame 195): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A glossy deep-red ball, 21 px across, with a white-hot glint up
on its upper left and a hot orange glow welling up along its lower right edge.

Run: blender --background --python assets/blender/enemies/newshk-195.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b032 as lib  # noqa: E402

common = lib.common
NAME = "newshk-195"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
X, Y, PX = lib.X, lib.Y, lib.PX

C, R = 12.0, 12.0  # centre column and row
RAD = 10.0 * PX
RZ = 0.3


def surface_z(c, r):
    u = ((X(c) - X(C)) ** 2 + (Y(r) - Y(R)) ** 2) / RAD ** 2
    return RZ * math.sqrt(max(0.0, 1 - u))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(116, metallic=0.2, roughness=0.2, emission_strength=0.6),  # 0 red ball
        pal(121, metallic=0.0, roughness=0.3, emission_strength=2.5),  # 1 orange glow, lower right
        pal(125, emission_strength=4.0),  # 2 yellow glint
        pal(127, emission_strength=6.0),  # 3 white-hot centre of the glint
        pal(118, metallic=0.2, roughness=0.25, emission_strength=1.0),  # 4 brighter red round the glint
    ]
    BALL, ORANGE, GLINT, HOT, BRIGHT = range(5)
    bm = bmesh.new()
    # A unit sphere turned so its pole sits under the glint (its rings then circle the glint),
    # then squashed to the ball's size.
    res = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=26, radius=1.0)
    u, v = (X(8.4) - X(C)) / RAD, (Y(8.4) - Y(R)) / RAD
    pole = Vector((u, v, math.sqrt(1 - u * u - v * v)))
    rot = Vector((0, 0, 1)).rotation_difference(pole)
    for vert in res["verts"]:
        p = rot @ vert.co
        vert.co = Vector((X(C) + p.x * RAD, Y(R) + p.y * RAD, p.z * RZ))
    for f in bm.faces:
        f.material_index = BALL
        f.smooth = True

    # Paint the ball's faces after the sprite: the glint up on the upper left (a brighter red
    # patch round a yellow spot with a white centre, columns 7-11, rows 7-11) and the orange glow
    # along the lower right rim (columns 17-21, rows 12-20).
    for f in bm.faces:
        p = f.calc_center_median()
        if p.z < 0:
            continue
        q = Vector(((p.x - X(C)) / RAD, (p.y - Y(R)) / RAD, p.z / RZ)).normalized()
        ang = math.degrees(q.angle(pole))  # rings round the glint
        if ang < 6:
            f.material_index = HOT
        elif ang < 13:
            f.material_index = GLINT
        elif ang < 21:
            f.material_index = BRIGHT
        # The far side of the ball from the glint, where it shows on top (lower right).
        if ang > 99 and p.z > 0.02:
            f.material_index = ORANGE
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
