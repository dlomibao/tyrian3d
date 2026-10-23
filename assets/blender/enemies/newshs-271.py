"""Grey walker turret (newshs.shp frame 271): a 3D version of its sprite.

A ground gun (level 3.15) built like a little grey robot: a round head with a raised rim and a
flat cap, a broad shoulder block, two arms reaching down and out to the sides, and a thick gun
barrel pointing down the screen with a dark bore in its collared muzzle.

Run: blender --background --python assets/blender/enemies/newshs-271.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b080 as L  # noqa: E402
import common  # noqa: E402

NAME = "newshs-271"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
g = L.Grid(24, 28)
U = L.U
CX = g.x(11.5)  # the sprite's axis


def build(sprite):
    coll = common.reset_collection(NAME)
    m = L.Mats(NAME, sprite["colors"])
    BODY = m(9, metallic=0.65, roughness=0.35)
    LIGHT = m(11, metallic=0.7, roughness=0.3)
    BRIGHT = m(12, metallic=0.75, roughness=0.25)
    DARK = m(5, metallic=0.5, roughness=0.5)
    BORE = m(2, metallic=0.2, roughness=0.8)
    bm = bmesh.new()

    # Neck under the head (rows 11-14).
    L.tube_z(bm, [(0.0, CX, g.y(12.5), 4.0 * U, 2.0 * U), (0.32, CX, g.y(12.0), 4.0 * U, 2.2 * U)],
             sides=14, mat=DARK)
    # Head (columns 6-17, rows 5-12): a drum with a rounded rim and a flat cap set into it.
    hx, hy = CX, g.y(8.6)
    L.tube_z(bm, [(0.18, hx, hy, 5.2 * U, 3.6 * U), (0.36, hx, hy, 5.8 * U, 4.1 * U),
                  (0.42, hx, hy, 5.6 * U, 3.95 * U), (0.45, hx, hy, 5.0 * U, 3.5 * U),
                  (0.45, hx, hy, 3.6 * U, 2.4 * U), (0.43, hx, hy, 3.4 * U, 2.25 * U)], sides=20, mat=LIGHT)
    L.tube_z(bm, [(0.40, hx, g.y(8.3), 3.5 * U, 2.3 * U), (0.47, hx, g.y(8.3), 3.4 * U, 2.2 * U),
                  (0.48, hx, g.y(8.3), 0.0, 0.0)], sides=20, mat=BODY)
    # Lit lower lip of the head (row 11).
    L.tube_x(bm, [(g.x(8.0), g.y(11.0), 0.6 * U, 0.33, 0.035), (g.x(15.0), g.y(11.0), 0.6 * U, 0.33, 0.035)],
             sides=6, mat=BRIGHT)

    # Shoulder block (rows 14-19, columns 4-19): rounded ends, a lit front edge.
    sh = L.rounded_rect(g.x(3.6), g.y(19.4), g.x(19.4), g.y(13.6), 2.2 * U, 3)
    L.bevel_prism(bm, sh, 0.0, 0.27, 0.05, mat=BODY)
    L.tube_x(bm, [(g.x(6.0), g.y(14.4), 0.7 * U, 0.25, 0.03), (g.x(17.0), g.y(14.4), 0.7 * U, 0.25, 0.03)],
             sides=6, mat=BRIGHT)
    # Two plates on the block either side of the neck (the light patches at rows 15-17).
    for c0, c1 in ((4.6, 8.4), (14.6, 18.4)):
        L.bevel_prism(bm, L.rounded_rect(g.x(c0), g.y(17.4), g.x(c1), g.y(15.0), 0.8 * U, 2),
                      0.25, 0.3, 0.02, mat=LIGHT)

    # Arms: from the shoulders down and out to the hands (columns 0-3 and 20-23, rows 19-22).
    start = len(bm.verts)
    L.sweep(bm, [(g.x(5.0), g.y(17.2), 0.2, 0.0, 0.0), (g.x(4.6), g.y(17.6), 0.2, 1.7 * U, 0.1),
                 (g.x(2.6), g.y(19.4), 0.15, 1.6 * U, 0.09), (g.x(1.2), g.y(21.0), 0.11, 1.5 * U, 0.085),
                 (g.x(0.6), g.y(21.7), 0.1, 0.0, 0.0)], sides=10, mat=LIGHT)
    L.ellipsoid(bm, (g.x(1.6), g.y(20.6), 0.11), (1.9 * U, 1.9 * U, 0.09), mat=BODY, segments=10, rings=6)
    L.mirror_x(bm, start, axis=CX)

    # Gun barrel down the screen (columns 8-15, rows 18-26) with a collar and a dark bore.
    L.tube_y(bm, [(g.y(17.5), CX, 3.0 * U, 0.17, 0.15), (g.y(22.8), CX, 3.0 * U, 0.17, 0.15)],
             sides=16, mat=BODY)
    L.tube_y(bm, [(g.y(22.6), CX, 3.3 * U, 0.17, 0.165), (g.y(26.3), CX, 3.3 * U, 0.17, 0.165)],
             sides=16, mat=LIGHT)
    L.tube_y(bm, [(g.y(26.2), CX, 1.7 * U, 0.17, 0.08), (g.y(26.4), CX, 1.7 * U, 0.17, 0.08)],
             sides=12, mat=BORE)
    # Bright stripe along its top and the dark slot near the muzzle (rows 20-22 and 24-25).
    L.tube_y(bm, [(g.y(19.5), CX, 0.9 * U, 0.31, 0.02), (g.y(22.5), CX, 0.9 * U, 0.31, 0.02)], sides=6, mat=BRIGHT)
    L.box(bm, CX - 1.0 * U, g.y(25.4), CX + 1.0 * U, g.y(23.6), 0.3, 0.345, mat=BORE)

    return L.to_object(NAME, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    L.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
