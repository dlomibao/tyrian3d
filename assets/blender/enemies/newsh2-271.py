"""Grey rail pod (newsh2.shp frame 271): a 3D version of its sprite.

Seen in episode 1 (levels 1.28, 1.3, 1.36) and episode 3. It flies sideways with its nose to the
left of the screen: a round grey pod with a pointed nose, a brown collar round its middle, a dark
canopy strip on top with two glowing red lights, a gold stripe ahead of it and a bright grey
engine at the back. Two thin grey rails run alongside, above and below it on the screen, each
held by a brown arm that bends in to the pod's tail. The sprite is mirror symmetric about row 13.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-271.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as L  # noqa: E402
from lib_b048 import common  # noqa: E402

NAME = "newsh2-271"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = L.PX
AXIS_ROW = 13  # the sprite is symmetric about the centre of row 13


def X(c):
    """Sprite column edge (fractions allowed) to X."""
    return (c - 12) / 12


def Yr(r):
    """Sprite row (pixel centre, fractions allowed) to Y relative to the axis row."""
    return (AXIS_ROW - r) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.6, roughness=0.35),  # 0 grey hull
        pal(24, metallic=0.45, roughness=0.45),  # 1 brown collar
        pal(10, metallic=0.65, roughness=0.3),  # 2 bright grey engine
        pal(3, metallic=0.4, roughness=0.15),  # 3 dark canopy strip
        pal(119, emission_strength=4.0),  # 4 red lights
        pal(121, emission_strength=5.0),  # 5 orange light cores
        pal(26, metallic=0.5, roughness=0.35),  # 6 gold stripe and collar trim
        pal(7, metallic=0.6, roughness=0.35),  # 7 grey rails
        pal(23, metallic=0.35, roughness=0.5),  # 8 brown arms
        pal(13, metallic=0.7, roughness=0.25),  # 9 engine nozzle rim
        pal(165, metallic=0.3, roughness=0.55),  # 10 dark brown collar band
    ]
    HULL, COLLAR, ENGINE, CANOPY, RED, ORANGE, GOLD, RAIL, ARM, RIM, BAND = range(11)
    bm = bmesh.new()

    # The pod along X, nose (column 0) to tail (column 24): (column edge, half width px, half height).
    nose = [(0.0, 0.0, 0.0), (0.4, 1.3, 0.06), (1.0, 2.3, 0.09), (2.0, 3.3, 0.12), (3.5, 4.2, 0.15),
            (5.0, 4.8, 0.17), (7.0, 5.6, 0.19), (9.0, 6.3, 0.2), (14.2, 6.5, 0.2)]
    L.sweep(bm, [(X(c), 0, 0, w * PX, h) for c, w, h in nose], sides=12, mat=HULL)
    collar = [(14.0, 6.5, 0.2), (14.4, 6.7, 0.21), (18.2, 6.6, 0.21), (18.6, 5.0, 0.17), (19.0, 4.0, 0.14)]
    L.sweep(bm, [(X(c), 0, 0, w * PX, h) for c, w, h in collar], sides=12, mat=COLLAR)
    # Dark band round the front of the collar (the dark brown pixels at column 14).
    L.sweep(bm, [(X(14.4), 0, 0, 6.8 * PX, 0.215), (X(15.2), 0, 0, 6.8 * PX, 0.215)], sides=12, mat=BAND,
            cap_start=False, cap_end=False)
    tail = [(18.8, 3.6, 0.13), (19.5, 3.6, 0.13), (22.6, 3.4, 0.12), (23.4, 2.6, 0.1), (24.0, 1.6, 0.07)]
    L.sweep(bm, [(X(c), 0, 0, w * PX, h) for c, w, h in tail], sides=12, mat=ENGINE)
    L.sweep(bm, [(X(23.8), 0, 0, 2.0 * PX, 0.085), (X(24.15), 0, 0, 1.0 * PX, 0.04),
                 (X(24.2), 0, 0, 0.0, 0.0)], sides=12, mat=RIM)

    # Dark canopy strip on top (columns 12-18, rows 11-14) with the two red lights in it.
    L.ellipsoid(bm, X(15.0), 0, 0.17, 3.8 * PX, 2.1 * PX, 0.065, mat=CANOPY, segments=14, rings=6)
    for c, m in ((15.5, RED), (17.5, RED)):
        L.ellipsoid(bm, X(c), 0, 0.2, 0.9 * PX, 1.7 * PX, 0.045, mat=m, segments=8, rings=4)
        L.ellipsoid(bm, X(c), 0, 0.225, 0.4 * PX, 0.5 * PX, 0.025, mat=ORANGE, segments=6, rings=3)
    # Gold stripe ahead of it (columns 9-11, row 13).
    L.sweep(bm, [(X(8.8), 0, 0.195, 0.0, 0.0), (X(9.3), 0, 0.2, 0.6 * PX, 0.025),
                 (X(11.8), 0, 0.2, 0.6 * PX, 0.025), (X(12.3), 0, 0.195, 0.0, 0.0)], sides=6, mat=GOLD)

    # One rail and its arm (the upper ones on screen), mirrored below.
    side = bmesh.new()
    L.sweep(side, [(X(8.6), Yr(3), 0.0, 0.0, 0.0), (X(9.0), Yr(3), 0.0, 0.65 * PX, 0.05),
                   (X(17.0), Yr(3), 0.0, 0.65 * PX, 0.05)], sides=8, mat=RAIL)
    L.sweep(side, [(X(16.6), Yr(3.0), 0.0, 0.8 * PX, 0.055), (X(18.6), Yr(3.6), 0.0, 0.85 * PX, 0.055),
                   (X(21.0), Yr(4.9), 0.0, 0.85 * PX, 0.055), (X(23.3), Yr(5.6), 0.0, 0.8 * PX, 0.05),
                   (X(23.8), Yr(5.7), 0.0, 0.0, 0.0)], sides=8, mat=ARM)
    # Grey post from the arm in to the tail (column 21, rows 6-10).
    L.sweep(side, [(X(21.5), Yr(5.6), 0.0, 0.6 * PX, 0.045), (X(21.5), Yr(10.2), 0.0, 0.6 * PX, 0.045)],
            sides=8, mat=RAIL)
    me = bpy.data.meshes.new("tmp271")
    side.to_mesh(me)
    side.free()
    bm.from_mesh(me)
    for v in me.vertices:
        v.co.y = -v.co.y
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

    # Shift onto the sprite's axis (the centre of row 13).
    for v in bm.verts:
        v.co.y += L.row(AXIS_ROW)
    return L.to_object(NAME, bm, mats, coll)


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
