"""Rock gun (newshk.shp frames 1-11, 39-49, 77-87): a 3D version of its sprites.

Seen in episode 3 (level 3.10). A blue-grey speckled boulder that opens up to shoot: in some
frames a grey gun pod pokes out of its left or right side, in others a stubby cannon swings out
of its underside (down-left, down or down-right) with a glowing fireball in its mouth. The orange
glints on the rim in frames 1-5 and the muzzle flash in 39/43 are details, so the frames fall into
six shapes, one model each:

  newshk-1     the bare boulder (frames 1, 3, 5, 7, 9, 11)
  newshk-1-f2  pod on the left (39, 45)        newshk-1-f3  pod on the right (43, 49)
  newshk-1-f4  cannon down-left (77, 83)       newshk-1-f5  cannon down (79, 85)
  newshk-1-f6  cannon down-right (81, 87)

Run: blender --background --python assets/blender/enemies/newshk-1.py [-- --preview out.png]
(each variant's preview goes next to out.png as <variant>.png).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector, noise

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b032 as lib  # noqa: E402

common = lib.common
NAME = "newshk-1"
ROOT = common.repo_root(__file__)
X, Y, PX = lib.X, lib.Y, lib.PX

BALL_C, BALL_R = 13.0, 12.0  # boulder centre (column, row) and radii below
RX, RY, RZ = 9.6 * PX, 8.7 * PX, 0.3

VARIANTS = [  # (model name, frames, gun)
    (NAME, [1, 3, 5, 7, 9, 11], None),
    (f"{NAME}-f2", [39, 45], "left"),
    (f"{NAME}-f3", [43, 49], "right"),
    (f"{NAME}-f4", [77, 83], "downleft"),
    (f"{NAME}-f5", [79, 85], "down"),
    (f"{NAME}-f6", [81, 87], "downright"),
]


def boulder(bm, mat):
    """A slightly lumpy squashed ball."""
    verts = lib.ellipsoid(bm, (X(BALL_C), Y(BALL_R), 0.0), (RX, RY, RZ), mat=mat, segments=18, rings=10)
    for v in verts:
        n = noise.noise(Vector((v.co.x * 3.1 + 7.3, v.co.y * 3.1 - 2.1, v.co.z * 3.1 + 0.7)))
        k = 1 + 0.08 * n
        v.co.x = X(BALL_C) + (v.co.x - X(BALL_C)) * k
        v.co.y = Y(BALL_R) + (v.co.y - Y(BALL_R)) * k
        v.co.z *= k


def pod(bm, side, PIPE, DARK, RIM):
    """A short grey gun pod out of the boulder's side (columns 2-4 or 20-22, rows 8-15)."""
    s = -1 if side == "left" else 1
    c_out = 1.6 if s < 0 else 23.1  # pixel centre of the muzzle face's column edge
    x_out, x_in = X(c_out), X(BALL_C + s * 4)
    y = Y(11.6)
    path = [(x_in, y, 0.0, 3.6 * PX, 0.17), (X(c_out - s * 1.0), y, 0.0, 4.0 * PX, 0.19),
            (x_out, y, 0.0, 3.8 * PX, 0.18)]
    lib.sweep(bm, path, sides=12, mat=PIPE, cap_start=False)
    # A lighter ring round the pod (the bright band in row 10) and the dark bore.
    lib.sweep(bm, [(X(c_out - s * 1.4), y, 0.0, 4.15 * PX, 0.195), (X(c_out - s * 0.6), y, 0.0, 4.15 * PX, 0.195)],
              sides=12, mat=RIM)
    lib.sweep(bm, [(x_out + s * 0.004, y, 0.0, 2.0 * PX, 0.09), (x_out + s * 0.01, y, 0.0, 1.6 * PX, 0.07)],
              sides=10, mat=DARK)


def cannon(bm, mouth, PIPE, DARK, GLOW, HOT):
    """A stubby mortar swung out of the underside, its mouth (at `mouth`, column and row) tipped up
    towards the viewer with a glowing fireball in it, ringed by the grey barrel."""
    mc, mr = mouth
    m = Vector((X(mc), Y(mr), 0.16))
    o = Vector((X(BALL_C), Y(BALL_R), 0.0))
    d = (m - o)
    d.z = 0
    d.normalize()
    d3 = Vector((d.x * 0.7, d.y * 0.7, 0.72)).normalized()
    back = m - d3 * (6.0 * PX)
    path = [(*back, 3.8 * PX, 3.0 * PX), (*(m - d3 * (1.5 * PX)), 4.8 * PX, 3.8 * PX), (*m, 4.8 * PX, 3.8 * PX)]
    lib.sweep(bm, path, sides=14, mat=PIPE, up_dir=(0, 0, 1))
    lib.sweep(bm, [(*(m + d3 * 0.003), 3.6 * PX, 2.8 * PX), (*(m + d3 * 0.006), 3.4 * PX, 2.6 * PX)],
              sides=14, mat=DARK, up_dir=(0, 0, 1))
    lib.ellipsoid(bm, tuple(m + d3 * (0.6 * PX)), (3.3 * PX, 3.0 * PX, 0.1), mat=GLOW, segments=12, rings=6)
    lib.ellipsoid(bm, tuple(m + d3 * (1.6 * PX)), (1.7 * PX, 1.6 * PX, 0.06), mat=HOT, segments=10, rings=5)


def flecks(bm, mat):
    """Darker pits speckling the boulder's top."""
    for c, r, rad in [(9.5, 8.5, 1.6), (15.5, 7.0, 1.4), (12.5, 13.5, 1.5), (17.5, 13.0, 1.7),
                      (7.5, 13.5, 1.3), (11.0, 17.5, 1.4), (19.0, 9.5, 1.2)]:
        x, y = X(c), Y(r)
        u = ((x - X(BALL_C)) / RX) ** 2 + ((y - Y(BALL_R)) / RY) ** 2
        z = RZ * math.sqrt(max(0.0, 1 - u))
        lib.ellipsoid(bm, (x, y, z - 0.012), (rad * PX, rad * PX, 0.02), mat=mat, segments=8, rings=4)


def build(sprite, name, gun):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(109, metallic=0.1, roughness=0.85),  # 0 pale blue-grey rock
        pal(10, metallic=0.6, roughness=0.35),  # 1 grey gun metal
        pal(3, metallic=0.4, roughness=0.6),  # 2 dark bore
        pal(13, metallic=0.6, roughness=0.3),  # 3 light grey band
        pal(122, emission_strength=4.0),  # 4 glowing fireball
        pal(126, emission_strength=6.0),  # 5 its white-hot heart
        pal(107, metallic=0.1, roughness=0.9),  # 6 darker pits
    ]
    ROCK, PIPE, DARK, RIM, GLOW, HOT, PIT = range(7)
    bm = bmesh.new()
    boulder(bm, ROCK)
    flecks(bm, PIT)
    if gun in ("left", "right"):
        pod(bm, gun, PIPE, DARK, RIM)
    elif gun == "down":
        cannon(bm, (12.6, 20.4), PIPE, DARK, GLOW, HOT)
    elif gun == "downleft":
        cannon(bm, (5.6, 18.4), PIPE, DARK, GLOW, HOT)
    elif gun == "downright":
        cannon(bm, (20.6, 18.0), PIPE, DARK, GLOW, HOT)
    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for name, frames, gun in VARIANTS:
        obj = build(sprite, name, gun)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": frames}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            k = next(i for i, f in enumerate(sprite["frames"]) if f["index"] == frames[0])
            lib.preview([obj], ROOT, NAME, sprite, frame=k,
                        out=out if name == NAME else out.parent / f"{name}.png")
            obj.hide_render = True


if __name__ == "__main__":
    main()
