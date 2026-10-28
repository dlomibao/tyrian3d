"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275): a 3D version of
its sprite.

A U of round tube, open end forward, with a round brown pod hung in the middle on two short
struts. The tube is one path: a grey pipe down each side (columns 5 and 17, rows 7-21) with a
bright-over-dark collar at rows 13-14 and 18-19, turning tan at row 20, a 45-degree step down to
row 24 and a flat bottom bar with the sprite's light and dark segments. The tube is about 2.6 px
across, so with its shaded rims it covers the sprite's 1 px dark outline; the banking frames show
the arms about 3 px deep, so it is about as tall as it is wide. The pod is a bullet with a round
section (about 7 px wide with its outline, 5.4 px tall) and a hemispherical nose with a shallow
dark window cut into it. Built around the middle of sprite column 11.

Run: blender --background --python assets/blender/ships/ship-u-ship.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import H, W, loft, tube  # noqa: E402

NAME = "ship-u-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the middle of sprite column 11
LEFT, RIGHT = AXIS - 6.0, AXIS + 6.0  # the pipes, columns 5 and 17

TUBE_R = 1.3  # radius of the U's tube, px (the 1 px core plus most of its outline each side)
COLLAR_R = 1.5  # the raised bright collars
GROOVE_R = 1.12  # the dark segment of the bottom bar
BEND_R = 1.1  # the bends into the 45-degree runs
DIAG_R = 0.88  # the 45-degree runs: the sprite's diagonal is 3 px wide across a row, 2 px square to it
MITRE = 1.0 / math.cos(math.pi / 8)  # keeps the tube's width round the 45-degree bends


def segmented_tube(bm, points, mats, sides=10):
    """tube() along points (col, row, radius) or (col, row, half_w, half_h), round in section unless
    half_h is given, one material per segment."""
    n0 = len(bm.faces)
    rings = [(p[0], p[1], p[2], p[-1], 0.0) for p in points]
    tube(bm, rings, sides=sides, mat=mats[0])
    faces = list(bm.faces)[n0:]
    for k, m in enumerate(mats):
        for f in faces[k * sides:(k + 1) * sides]:
            f.material_index = m
    faces[-1].material_index = mats[-1]  # the end cap


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.35, roughness=0.35),  # 0 grey pipe
        pal(10, metallic=0.35, roughness=0.35),  # 1 lighter grey pipe between the collars
        pal(11, metallic=0.35, roughness=0.3),  # 2 bright collar
        pal(6, metallic=0.35, roughness=0.45),  # 3 dark band under a collar
        pal(28, metallic=0.2, roughness=0.45),  # 4 tan arm
        pal(26, metallic=0.2, roughness=0.45),  # 5 bar, light
        pal(25, metallic=0.2, roughness=0.45),  # 6 bar, mid
        pal(21, metallic=0.2, roughness=0.55),  # 7 bar, dark groove
        pal(25, metallic=0.2, roughness=0.45),  # 8 pod
        pal(163, metallic=0.1, roughness=0.3),  # 9 dark window
        pal(7, metallic=0.35, roughness=0.4),  # 10 struts
        pal(3, metallic=0.35, roughness=0.5),  # 11 shaded flanks of the grey parts
        pal(162, metallic=0.2, roughness=0.55),  # 12 shaded flanks of the tan and brown parts
    ]
    G9, G10, G11, G6, TAN, BAR_L, BAR_M, BAR_D, POD, DARK, STRUT, G_SHADE, B_SHADE = range(13)
    bm = bmesh.new()
    R, C, D = TUBE_R, COLLAR_R, GROOVE_R

    # The U, one tube from the top of the left pipe round to the top of the right one. Each pipe:
    # a rounded top end (row 7), grey, a bright collar over a dark band at rows 13-14 and 18-19,
    # then tan from row 20 into the bend.
    def pipe(c):
        pts = [(c, 7.0, R, 0.4), (c, 7.9, R), (c, 13.0, R), (c, 13.08, C), (c, 13.92, C), (c, 14.0, R),
               (c, 15.0, R), (c, 18.0, R), (c, 18.08, C), (c, 18.92, C), (c, 19.0, R), (c, 20.0, R)]
        mats_ = [G9, G9, G11, G11, G11, G6, G10, G11, G11, G11, G6]
        return pts, mats_

    lp, lm = pipe(LEFT)
    rp, rm = pipe(RIGHT)
    bend_l, bend_r = (LEFT, 21.5, BEND_R * MITRE, BEND_R), (RIGHT, 21.5, BEND_R * MITRE, BEND_R)
    # The bottom bar along row 24 (centre 24.5), columns 8-14: light, mid, tan, dark, tan, mid, light.
    bar = [(8.5, 24.5, BEND_R * MITRE, BEND_R), (9.0, 24.5, R), (10.0, 24.5, R), (11.0, 24.5, R), (11.08, 24.5, D),
           (11.92, 24.5, D), (12.0, 24.5, R), (13.0, 24.5, R), (14.0, 24.5, R), (14.5, 24.5, BEND_R * MITRE, BEND_R)]
    bar_m = [BAR_L, BAR_M, TAN, BAR_D, BAR_D, BAR_D, TAN, BAR_M, BAR_L]
    diag_l = [(6.5, 22.5, DIAG_R), (7.5, 23.5, DIAG_R)]
    diag_r = [(15.5, 23.5, DIAG_R), (16.5, 22.5, DIAG_R)]
    points = lp + [bend_l] + diag_l + bar + diag_r + [bend_r] + list(reversed(rp))
    mats_u = (lm + [TAN] * 4  # row 20 to the bend, the bend down to the bar
              + bar_m + [TAN] * 4  # the bar, then up to the right bend and row 20
              + list(reversed(rm)))
    segmented_tube(bm, points, mats_u)

    # Struts from the pipes to the pod (row 16, columns 6-7 and 15-16), grey tubes.
    for side in (-1, 1):
        x0, x1 = AXIS + side * 4.9, AXIS + side * 2.9
        tube(bm, [(x0, 16.5, 1.15, 1.0, 0.0), (x1, 16.5, 1.15, 1.0, 0.0)], sides=8, mat=STRUT)

    # The pod: a bullet, round in section, hemispherical at the front (row 12), cut off at the back
    # (row 20); the light left side and dark right column of the sprite come from the lighting.
    pod = [(12.0, 0.0, 0.0), (12.2, 1.2, 1.0), (12.6, 1.95, 1.65), (13.3, 2.65, 2.25), (14.2, 3.15, 2.6),
           (15.2, 3.35, 2.7), (19.9, 3.35, 2.7), (20.3, 3.3, 1.9), (20.8, 3.1, 0.9), (21.0, 2.6, 0.3)]
    n0 = len(bm.faces)
    loft(bm, [(r, AXIS, w, h, 0.0) for r, w, h in pod], sides=16, mat=POD)
    # Shallow dark window in the nose (rows 13-14, columns 9-11): faces there turn dark and sink
    # about 0.3 px.
    sink = set()
    for f in list(bm.faces)[n0:]:
        cen = f.calc_center_median()
        col, row, z = cen.x * 12 + W / 2, H / 2 - cen.y * 12, cen.z * 12
        if 13.0 < row < 15.0 and 9.2 < col < 12.3 and z > 0.6:
            f.material_index = DARK
            sink.update(f.verts)
    for v in sink:
        v.co.z -= 0.3 / 12

    # The sprite draws every part as a lit core inside a 1 px dark rim: the steep flanks of each
    # round part (what is seen from above round its lit top) take the dark of its ramp.
    shade = {m: G_SHADE for m in (G9, G10, G11, G6, STRUT)}
    shade.update({m: B_SHADE for m in (TAN, BAR_L, BAR_M, BAR_D, POD)})
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        steep = 0.55 if f.material_index == POD else 0.8
        if f.material_index in shade and f.normal.z < steep:
            f.material_index = shade[f.material_index]

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
