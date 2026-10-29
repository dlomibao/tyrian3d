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
    K = 0.85  # the pod is round: about as tall as it is wide

    def pod(stations, mat, sides=16, k=K, **kw):
        """A round section along X: (column edge, half width px), height k * width."""
        L.sweep(bm, [(X(c), 0, 0, w * PX, k * w * PX) for c, w in stations], sides=sides, mat=mat, **kw)

    # The pod along X, nose (column 0) to tail (column 24). A bullet-shaped nose cap to the
    # panel seam at column 7 (the dark column), then the body to the collar.
    pod([(0.0, 0.0), (0.15, 0.9), (0.6, 1.6), (1.5, 2.5), (2.5, 3.3), (3.5, 4.0), (5.0, 4.9), (6.4, 5.6),
         (7.0, 5.85)], HULL)
    pod([(6.95, 5.4), (7.3, 6.0), (8.2, 6.6), (9.5, 6.9), (14.2, 6.9)], HULL)
    # Brown armour collar round the rear half, a plate proud of the hull, rounding off at the back.
    pod([(13.9, 6.9), (14.3, 7.2), (16.6, 7.2), (17.5, 6.4), (18.3, 5.3), (18.9, 4.2), (19.1, 3.6)],
        COLLAR)
    # Dark band round the front of the collar (the dark brown pixels at column 14).
    pod([(14.3, 7.3), (15.0, 7.3)], BAND, cap_start=False, cap_end=False)
    # Round engine drum at the tail, a groove ring at column 21 (the dark column), nozzle rim.
    pod([(18.8, 3.2), (19.2, 3.4), (20.8, 3.4), (20.95, 2.95), (21.55, 2.95), (21.7, 3.4),
         (22.7, 3.3), (23.3, 2.8), (23.8, 2.0)], ENGINE, k=1.0)
    pod([(23.7, 2.2), (24.1, 1.9), (24.15, 1.1), (23.9, 0.0)], RIM, k=1.0)

    # Sensor bay on top (columns 12-18, rows 11-15): a dark recess framed by raised armour, two
    # red glass lights in it with orange cores and a dark divider between them.
    zt = 6.1 * PX  # the collar's top
    L.box(bm, X(11.8), -2.0 * PX, X(17.8), 2.0 * PX, zt - 2.0 * PX, zt + 0.05 * PX, mat=CANOPY)
    frame = (COLLAR, COLLAR, COLLAR, COLLAR)
    for s in (1, -1):  # the side rims (rows 10-11 and 15-16)
        L.bevel_plate(bm, [(X(11.6), s * 2.0 * PX), (X(18.0), s * 2.0 * PX), (X(18.0), s * 2.9 * PX),
                           (X(11.6), s * 2.9 * PX)], zt - 1.5 * PX, zt + 0.7 * PX, 0.3 * PX, frame)
    L.bevel_plate(bm, [(X(11.2), -2.9 * PX), (X(11.8), -2.9 * PX), (X(11.8), 2.9 * PX), (X(11.2), 2.9 * PX)],
                  zt - 1.6 * PX, zt + 0.55 * PX, 0.25 * PX, (HULL,) * 4)
    L.bevel_plate(bm, [(X(17.8), -2.9 * PX), (X(18.5), -2.9 * PX), (X(18.5), 2.9 * PX), (X(17.8), 2.9 * PX)],
                  zt - 3.0 * PX, zt + 0.6 * PX, 0.25 * PX, (COLLAR,) * 4)
    for c in (15.5, 17.4):
        L.ellipsoid(bm, X(c), 0, zt + 0.1 * PX, 0.75 * PX, 1.6 * PX, 0.55 * PX, mat=RED, segments=8, rings=4)
        L.ellipsoid(bm, X(c), 0, zt + 0.42 * PX, 0.35 * PX, 0.55 * PX, 0.35 * PX, mat=ORANGE, segments=6,
                    rings=3)
    # Brass plate ahead of it (columns 9-11, row 13), a flat raised plate.
    L.bevel_plate(bm, [(X(8.9), -0.6 * PX), (X(12.0), -0.6 * PX), (X(12.0), 0.6 * PX), (X(8.9), 0.6 * PX)],
                  5.2 * PX, 6.3 * PX, 0.25 * PX, (GOLD,) * 4)

    # One rail and its arm (the upper ones on screen), mirrored below. The rail is a flat bar and
    # the arm an angular beam (square sections: a 4-sided sweep has its corners at 45 degrees).
    SQ = 2 ** 0.5
    side = bmesh.new()
    L.sweep(side, [(X(8.3), Yr(3), 0.0, 0.8 * SQ * PX, 0.8 * SQ * PX),
                   (X(17.4), Yr(3), 0.0, 0.8 * SQ * PX, 0.8 * SQ * PX)], sides=4, mat=RAIL, smooth=False)
    L.sweep(side, [(X(16.6), Yr(3.0), 0.0, 0.95 * SQ * PX, 0.8 * SQ * PX),
                   (X(18.6), Yr(3.6), 0.0, 0.95 * SQ * PX, 0.8 * SQ * PX),
                   (X(21.0), Yr(4.9), 0.0, 0.95 * SQ * PX, 0.8 * SQ * PX),
                   (X(23.6), Yr(5.6), 0.0, 0.9 * SQ * PX, 0.75 * SQ * PX)], sides=4, mat=ARM, smooth=False)
    # Grey post from the arm in to the engine (column 21, rows 6-10).
    L.sweep(side, [(X(21.5), Yr(5.4), 0.0, 0.65 * PX, 0.65 * PX), (X(21.5), Yr(10.3), 0.0, 0.65 * PX, 0.65 * PX)],
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
