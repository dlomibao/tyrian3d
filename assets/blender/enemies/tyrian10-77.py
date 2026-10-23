"""Green crystal (tyrian.shp #10 frames 77-87): a 3D version of its sprite.

Seen in episode 3 (level 25) and episode 4. A long cut emerald pointing up and down the screen:
pointed ends, straight sides, a bright ridge down its middle that opens into a small diamond-shaped
table facet below the centre, a broad facet each side of the ridge and a narrow facet along each
edge. The six frames only sweep a white glint across it, so one model covers them all.

Run: blender --background --python assets/blender/enemies/tyrian10-77.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b039 as lib  # noqa: E402

NAME = "tyrian10-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = 1 / 12

# Centre of the crystal: column 11, row 13.
CX, CY = lib.px(11), lib.row(13)
H = 3.4 * U  # height of the ridge above the girdle
RIDGE = 0.6 * U  # half width of the ridge bevels

# Down the crystal, (px above the centre, half width in px, half width of the table facet in px).
SECTIONS = [(11.0, 0.0, 0.0), (5.5, 5.5, 0.0), (2.5, 5.5, 0.0), (1.0, 5.5, 1.1), (-1.0, 5.5, 2.1),
            (-3.0, 5.5, 1.3), (-4.5, 5.5, 0.0), (-5.5, 5.5, 0.0), (-11.0, 0.0, 0.0)]


def ring(dy, w, tw):
    """12 points round the crystal at dy px above the centre (see the segment list in build)."""
    if w == 0:
        return [(CX, CY + dy * U, 0.25 * H)]
    W, T = w * U, max(tw, 0.05) * U
    r = RIDGE * min(1.0, w / 5.5)
    xz = [(T, H), (T + r, H - 0.18 * U), (0.62 * W, 0.6 * H), (W, 0.0), (0.62 * W, -0.6 * H),
          (0.3 * W, -0.8 * H), (-0.3 * W, -0.8 * H), (-0.62 * W, -0.6 * H), (-W, 0.0),
          (-0.62 * W, 0.6 * H), (-T - r, H - 0.18 * U), (-T, H)]
    return [(CX + x, CY + dy * U, z) for x, z in xz]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.1, roughness=0.2),  # 0 left broad facet
        pal(37, metallic=0.1, roughness=0.2),  # 1 right broad facet
        pal(43, metallic=0.1, roughness=0.15),  # 2 bright ridge
        pal(41, metallic=0.1, roughness=0.15),  # 3 table facet
        pal(42, metallic=0.1, roughness=0.2),  # 4 right narrow facet
        pal(39, metallic=0.1, roughness=0.2),  # 5 left narrow facet
        pal(35, metallic=0.1, roughness=0.3),  # 6 underside
    ]
    LEFT, RIGHT, RIDGE_M, TABLE, RNARROW, LNARROW, UNDER = range(7)
    # Segments of a ring: right ridge bevel, right broad facet, right narrow facet, five underside,
    # left narrow facet, left broad facet, left ridge bevel, table.
    seg = [RIDGE_M, RIGHT, RNARROW, UNDER, UNDER, UNDER, UNDER, UNDER, LNARROW, LEFT, RIDGE_M, TABLE]
    bm = bmesh.new()
    lib.ring_loft(bm, [ring(*s) for s in SECTIONS], [seg] * (len(SECTIONS) - 1))
    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
