"""Steel eye ball (newshl.shp 117): a 3D version of its sprite.

Seen in episode 4 (level 45). A polished grey ball about 9 px across sitting on the ground, with a
round blue lens on its down-screen side: a dark blue rim around a paler blue iris with a white
glint. The ball is a slightly squashed sphere resting on z = 0; the lens is an oval cap that
follows the ball's curve just below its centre (facing down-screen), its rim standing a little
proud around a domed, glowing iris.

Run: blender --background --python assets/blender/enemies/newshl-117.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b098 as lib  # noqa: E402

NAME = "newshl-117"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14, sprite["frames"][0]["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    shell = mats(11, metallic=0.7, roughness=0.3)
    rim = mats(53, metallic=0.4, roughness=0.25)
    iris = mats(57, metallic=0.2, roughness=0.15, emission_strength=2.0)
    glint = mats(61, metallic=0.0, roughness=0.1, emission_strength=4.0)

    bm = bmesh.new()
    # The ball: columns 2-10, rows 3-11 (the 1s around it are the outline), centred on column 6, row 7.
    cx, cy = grid.x(6), grid.y(7)
    r, rz = 4.6 * U, 0.3
    cz = rz - 0.03
    lib.cube_blob(bm, (cx, cy, cz), (r, r, rz), n=8, mat_index=shell)

    def ball_z(x, y):
        k = ((x - cx) / r) ** 2 + ((y - cy) / r) ** 2
        return cz + rz * max(0.0, 1 - k) ** 0.5

    # The lens: an oval over columns 4-8, rows 7-10 (centre column 6, row 8.6), a dark blue rim
    # standing a little proud of the ball around a domed paler iris.
    lib.surface_cap(bm, (grid.x(6), grid.y(8.6)), (2.6 * U, 2.15 * U), ball_z,
                    [(1.08, -0.02, rim), (1.0, 0.022, rim), (0.85, 0.03, rim), (0.62, 0.028, rim),
                     (0.56, 0.035, iris), (0.3, 0.05, iris), (0.0, 0.055, iris)], sides=18)
    # The white glint (row 9, column 6).
    lib.surface_cap(bm, (grid.x(6), grid.y(9.15)), (0.6 * U, 0.55 * U), ball_z,
                    [(1.0, 0.045, glint), (0.5, 0.062, glint), (0.0, 0.066, glint)], sides=8)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
