"""Ball turret in the grass (newshj.shp frames 83, 85, 87, 121, 123, 125): a 3D version of its sprites.

Seen in episode 2 (level 2.2), beside the waterfall bunkers. A grey steel ball sits in a dark
collar ringed by a light rim, in a patch of jungle grass. Closed (frame 83) the ball is smooth;
open (the other five frames) an iris on its upper side shows a glowing eye, and seams run down
the shell from it. The open frames only change the eye's colour, so:

- newshj-83 (frame 83): the closed ball.
- newshj-83-f2 (frames 85, 87, 121, 123, 125): the ball with its eye open.

Run: blender --background --python assets/blender/enemies/newshj-83.py [-- --preview out.png]
(the preview is the closed ball; the open one is written to newshj-83-f2.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b077 as L  # noqa: E402

NAME = "newshj-83"
ROOT = common.repo_root(__file__)
U = L.U
GREENS = set(range(32, 36)) | set(range(192, 200))
DOME_C, DOME_R = (10.8, 11.6), (8.6, 7.6)  # pixel centre coords, radii px
DOME_Z, DOME_H = 0.1, 0.5


def dome_z(c, r):
    """Height of the ball's surface over pixel (c, r)."""
    d = ((c - DOME_C[0]) / DOME_R[0]) ** 2 + ((r - DOME_C[1]) / DOME_R[1]) ** 2
    return DOME_Z + DOME_H * max(0.0, 1 - d) ** 0.5


def build(model, sprite, frame_index, open_eye):
    coll = common.reset_collection(model)
    pixels = sprite["frames"][frame_index]["pixels"]
    grid = L.Grid(24, 28, pixels, weight=lambda i: 1.8 if 194 <= i <= 199 else 1.0)
    M = L.Mats(model, sprite["colors"])
    X, Y = grid.x, grid.y
    BALL = M(9, metallic=0.6, roughness=0.3)
    COLLAR = M(4, metallic=0.5, roughness=0.45)
    RIM = M(10, metallic=0.65, roughness=0.3)
    SEAM = M(106, metallic=0.6, roughness=0.3)
    bm = bmesh.new()

    # Grass over the whole tile, with bright blades standing up.
    def grass_slot(i):
        if i in GREENS:
            return M(i, metallic=0.0, roughness=1.0)
        return M(194, metallic=0.0, roughness=1.0)
    flat = lambda c, r: 0.035  # noqa: E731
    L.terrain(bm, grid, 0, 0, 24, 28, flat, grass_slot, cell=2.0)
    L.tufts(bm, grid, 0, 0, 24, 28, lambda i: i >= 196 and i in GREENS, grass_slot, flat, seed=3)

    # The collar the ball sits in (its dark band shows under the ball, rows 18-21) and its light
    # rim, which shows round the lower right (rows 14-21).
    L.disc_z(bm, X(11.6), Y(14.0), 0.0, 0.13, 9.3 * U, 7.8 * U, sides=24, mat_index=COLLAR)
    ring = [(X(11.6) + 9.0 * U * math.cos(a), Y(14.0) + 7.5 * U * math.sin(a), 0.14, 0.7 * U, 0.03)
            for a in [2 * math.pi * k / 24 for k in range(25)]]
    L.sweep(bm, ring, sides=6, mat_index=RIM, cap_start=False, cap_end=False)

    # The ball.
    L.blob(bm, (X(DOME_C[0]), Y(DOME_C[1]), DOME_Z), (DOME_R[0] * U, DOME_R[1] * U, DOME_H),
           segments=22, rings=11, mat_index=BALL)

    if open_eye:
        # The iris: a dark red socket round a glowing eye (rows 5-12, columns 7-14).
        ec, er = 10.6, 8.6
        z = dome_z(ec, er)
        L.blob(bm, (X(ec), Y(er), z - 0.02), (4.0 * U, 3.8 * U, 0.06), segments=16, rings=6,
               mat_index=M(116, metallic=0.4, roughness=0.4))
        L.blob(bm, (X(ec), Y(er), z), (3.1 * U, 2.9 * U, 0.065), segments=16, rings=6,
               mat_index=M(122, emission_strength=4.0))
        L.blob(bm, (X(ec - 0.4), Y(er - 0.4), z + 0.03), (1.5 * U, 1.4 * U, 0.05), segments=10, rings=5,
               mat_index=M(126, emission_strength=6.0))
        # Seams down the shell: from the eye down the front (column 11) and on the right (column 16).
        for pts in ([(11.2, 12.6), (11.2, 15.0), (11.2, 17.5), (11.2, 19.0)],
                    [(15.2, 6.5), (16.0, 8.5), (16.3, 10.5), (16.0, 12.5)],
                    [(12.6, 13.5), (14.0, 13.2), (15.0, 12.6)]):
            path = [(X(c), Y(r), dome_z(c, r) + 0.005, 0.45 * U, 0.02) for c, r in pts]
            L.sweep(bm, path, sides=6, mat_index=SEAM)

    return L.to_object(model, bm, M.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    frames = sprite["sprites"][0]["frames"]
    out = L.preview_arg()
    for model, fi, open_eye, keep in ((NAME, 0, False, frames[:1]), (f"{NAME}-f2", 2, True, frames[1:])):
        obj = build(model, sprite, fi, open_eye)
        common.export_sprite_model(ROOT, [obj], f"enemies/{model}", L.frames_subset(sprite["sprites"], keep))
        if out:
            png = out if model == NAME else out.parent / f"{model}.png"
            ref = ROOT / "reference" / "models" / NAME / sprite["frames"][fi]["image"]
            common.render_preview([obj], str(png), ref, size=2)


if __name__ == "__main__":
    main()
