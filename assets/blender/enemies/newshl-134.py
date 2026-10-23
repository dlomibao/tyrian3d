"""Red-banded canister (newshl.shp 134): a 3D version of its sprite.

Seen in episode 4 (level 45). A small grey metal canister lying on the ground, nose down the
screen, about 4 x 12 px: a short dark cap at the back (rows 1-3) on a thin neck (row 4), then a
bulb-shaped body (rows 5-11) that narrows to a collar, swells to its widest at rows 7-10 and ends
in a dark rounded tip, with a glowing red band round its middle (row 8). The sprite's light
stripe down column 5 shows it is round, so it is a lathe (loft along Y) resting on z = 0.

Run: blender --background --python assets/blender/enemies/newshl-134.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b098 as lib  # noqa: E402

NAME = "newshl-134"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14)
    mats = lib.Mats(NAME, sprite["colors"])
    cap = mats(7, metallic=0.6, roughness=0.4)
    body = mats(9, metallic=0.7, roughness=0.3)
    dark = mats(4, metallic=0.5, roughness=0.5)
    band = mats(118, metallic=0.2, roughness=0.3, emission_strength=2.5)

    bm = bmesh.new()
    zc = 2.1 * U  # the axis, so the widest part (rows 7-10) rests on the ground
    x0 = grid.x(5.5)  # columns 4-7

    def lathe(profile, mat, sides=14):
        """profile: (sprite row, radius px) along the canister."""
        start = len(bm.verts)
        common.loft(bm, [(grid.y(r), w * U, w * U, zc) for r, w in profile], sides=sides, mat_index=mat)
        common.shift_x(bm, start, x0)

    # The back cap (rows 1-3): flat back, 4 px wide, narrowing into the neck.
    lathe([(0.55, 0.0), (0.55, 1.5), (0.8, 1.95), (2.4, 2.0), (3.0, 1.5), (3.6, 0.9)], cap)
    # The thin neck (row 4).
    lathe([(3.5, 0.75), (4.6, 0.75)], dark, sides=10)
    # The body: a collar (rows 5-6), the swell (rows 7-10) and the dark tip (rows 10-11).
    lathe([(4.5, 0.0), (4.5, 1.0), (5.0, 1.15), (6.3, 1.15), (6.9, 1.8), (7.55, 2.0)], body)
    lathe([(7.5, 2.15), (7.55, 2.18), (8.45, 2.18), (8.5, 2.15)], band, sides=16)
    lathe([(8.45, 2.0), (9.5, 2.0), (10.2, 1.8)], body)
    lathe([(10.2, 1.8), (10.8, 1.45), (11.4, 0.9), (11.75, 0.0)], dark)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
