"""Small red pod with two lenses (newshe.shp frame 195): a 3D version of its sprite.

A ground object, the one-piece cousin of assembly-newshe-229's pod: a low round red dome lit
from the front, with a dark glass cap over its back half and, on the cap, a white-hot lens on
the left and a dimmer orange one on the right, like a pair of eyes.

Run: blender --background --python assets/blender/enemies/newshe-195.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b070 as lib  # noqa: E402

NAME = "newshe-195"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(24, 28, sprite["frames"][0]["pixels"])
    X, Y = grid.x, grid.y
    mats = lib.Mats(NAME, sprite["colors"])
    SHADE = mats(113, metallic=0.3, roughness=0.5)
    BODY = mats(116, metallic=0.3, roughness=0.45)
    LIT = mats(118, metallic=0.3, roughness=0.4)
    HOT = mats(121, metallic=0.35, roughness=0.35)
    GLASS = mats(64, metallic=0.5, roughness=0.25)
    SOCKET = mats(115, metallic=0.4, roughness=0.3)
    DIM = mats(117, emission_strength=1.5)
    GLOW = mats(121, emission_strength=2.5)
    RING = mats(123, emission_strength=3.0)
    CORE = mats(127, emission_strength=5.0)
    bm = bmesh.new()

    # Body: cols 2-22, rows 4-24.
    body = ((X(12.0), Y(14.0), 0.0), (10.7 / 12, 10.7 / 12, 0.32))
    first = lib.dome(bm, *body, segments=28, rings=7, mat_index=BODY, power=0.8)

    def body_slot(v):
        if v in (1, 64) or v <= 113:
            return SHADE
        if v <= 116:
            return BODY
        if v <= 119:
            return LIT
        return HOT
    lib.paint(bm, first, grid, body_slot)

    # Dark glass cap over the back half (cols 5-19, rows 5-18).
    cap_xy, cap_r = (X(12.0), Y(11.4)), (7.7 / 12, 7.1 / 12)
    z0, shear = lib.fit_cap(body, cap_xy, cap_r, power=0.8)
    cap = ((cap_xy[0], cap_xy[1], z0), (cap_r[0], cap_r[1], 0.15))
    lib.dome(bm, *cap, segments=24, rings=5, mat_index=GLASS, shear=shear)

    def surface(x, y):
        return lib.dome_z(*cap, x, y, shear=shear) or z0

    # The lenses: a white-hot one (cols 6-11, rows 8-13) and a dim orange one (cols 13-15, rows 9-11).
    lib.lens(bm, surface, X(8.6), Y(10.6), [(2.9 / 12, 0.025, SOCKET), (2.1 / 12, 0.04, RING),
                                            (1.3 / 12, 0.055, CORE)], segments=16)
    lib.lens(bm, surface, X(14.0), Y(10.3), [(2.0 / 12, 0.02, SOCKET), (1.5 / 12, 0.03, DIM),
                                             (0.8 / 12, 0.04, GLOW)], segments=12)

    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
