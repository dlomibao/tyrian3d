"""Spiked ice mine (newsha.shp frames 167, 205, 243): a 3D version of its sprite.

Seen in episode 1 (level 1.13) and 3 (3.12). A faceted pale-cyan crystal ball, its top
textured with the sprite's own light and dark patches and a few short spikes pointing up out of
it, ringed by eight long spikes. The ball stays still while the spikes turn from frame to frame
(the top and upper-left spikes shorten as they tilt towards the viewer, the bottom and
lower-left ones lengthen), so each frame gets its own model: newsha-167, newsha-167-f2 and
newsha-167-f3, the same ball with the spikes as that frame shows them.

Run: blender --background --python assets/blender/enemies/newsha-167.py [-- --preview out.png]
(the preview is frame 167; the other frames' models get <model>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b044 as lib  # noqa: E402
import common  # noqa: E402

NAME = "newsha-167"
PX = lib.PX
C_COL, C_ROW = 11, 13  # the ball's centre pixel
R_BALL = 7.5  # px
Z_BALL = 0.24  # the ball's half height (units)
L_SPIKE = 13.5  # a spike's full 3D reach from the centre, px

# Each frame's ring of spikes: the tip pixel (column, row) of each, as the sprite shows it.
SPIKES = [
    [(11, 1), (2, 4), (0, 13), (21, 13), (11, 23), (21, 23), (18, 6), (4, 20)],  # 167
    [(11, 2), (3, 5), (0, 13), (22, 13), (11, 25), (20, 22), (19, 5), (3, 21)],  # 205
    [(11, 3), (4, 6), (1, 13), (23, 13), (11, 26), (19, 21), (20, 4), (2, 22)],  # 243
]
# Short spikes pointing up out of the ball, seen end-on as the brightest pixels on its face.
STUBS = [(7, 9), (14, 7), (11, 12.5), (6, 13), (15, 16), (7, 17)]


def ball_point(nx, ny, nz):
    """A point on the ball for a unit direction: a squircle (the sprite's ball is squarish) in
    XY, squashed in Z."""
    p = 4.0
    rxy = math.hypot(nx, ny)
    if rxy > 1e-6:
        c, s = abs(nx / rxy), abs(ny / rxy)
        f = (c ** p + s ** p) ** (-1 / p)
    else:
        f = 1.0
    return Vector((lib.px(C_COL) + nx * R_BALL * PX * f, lib.row(C_ROW) + ny * R_BALL * PX * f, nz * Z_BALL))


def build_frame(sprite, fi, model):
    coll = common.reset_collection(model)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    shades = [211, 213, 216, 219, 222]  # the ball's face, darkest to brightest
    mats = [pal(i, metallic=0.25, roughness=0.2) for i in shades]
    mats.append(pal(218, metallic=0.3, roughness=0.15))  # 5 spikes
    SPIKE = 5
    pixels = sprite["frames"][0]["pixels"]  # the ball's face is the same in every frame

    def shade(v):
        if v <= 211:
            return 0
        if v <= 214:
            return 1
        if v <= 217:
            return 2
        if v <= 220:
            return 3
        return 4

    bm = bmesh.new()
    res = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in res["verts"]:
        v.co = ball_point(*v.co.normalized())
    for f in bm.faces:
        f.smooth = False
        c = f.calc_center_median()
        col = int(math.floor(c.x * 12 + 12))
        rw = int(math.floor(14 - c.y * 12))
        v = pixels[rw][col] if 0 <= rw < 28 and 0 <= col < 24 else -1
        if f.normal.z < -0.2:
            f.material_index = 0  # underside
        elif v < 0:
            f.material_index = 2
        else:
            f.material_index = shade(v)

    # The ring of spikes, tilted out of the plane as far as the sprite foreshortens them.
    centre = Vector((lib.px(C_COL), lib.row(C_ROW), 0.0))
    for tc, tr in SPIKES[fi]:
        d = Vector(((tc - C_COL) * PX, -(tr - C_ROW) * PX, 0.0))
        d2 = d.length / PX + 0.5  # px from the centre to the tip's outer edge
        direction = d.normalized()
        tilt = 0.35 * math.sqrt(max(0.0, L_SPIKE ** 2 - d2 ** 2)) * PX
        sign = 1.0 if tr <= C_ROW else -1.0
        tip = centre + direction * d2 * PX + Vector((0, 0, sign * min(tilt, 0.3)))
        base = centre + (tip - centre) * (6.0 / d2)
        lib.cone(bm, base, tip, 1.9 * PX, sides=6, mat=SPIKE)

    # Short spikes standing up off the ball's face.
    for c, r in STUBS:
        n = Vector(((c - C_COL) / R_BALL, -(r - C_ROW) / R_BALL, 0.0))
        nz = math.sqrt(max(0.05, 1 - min(1.0, n.length) ** 2))
        surf = ball_point(n.x, n.y, nz)
        up = Vector((n.x * 0.5, n.y * 0.5, 1.0)).normalized()
        lib.cone(bm, surf - up * 0.03, surf + up * 0.08, 1.1 * PX, sides=5, mat=4)

    return lib.to_object(model, bm, mats, coll)


def build(sprite):
    sheet = sprite["sprites"][0]
    models = []
    for fi, frame in enumerate(sheet["frames"]):
        model = NAME if fi == 0 else f"{NAME}-f{fi + 1}"
        sprites = [{**sheet, "frames": [frame]}]
        models.append((model, [build_frame(sprite, fi, model)], sprites, fi))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
