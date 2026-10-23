"""Pale violet crystal shard (newshv.shp frame 50): a 3D version of its sprite.

Seen in episode 2 (levels 2.12 and 2.19). A long six-sided crystal lying diagonally, its point at
the top left and a blunt faceted end at the bottom right, with a bright crest along its top. The
sprite is symmetric about the 45-degree line from its point, so the crystal is lofted along that
line (half widths measured across it, row by row of the sprite) and turned into place.

Run: blender --background --python assets/blender/enemies/newshv-50.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-50"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Distance along the axis from the point (sprite px) and half width across it (px), for the body
# and then the end cap past the dark seam at about 21 px.
BODY = [(0.5, 0.0), (2.0, 1.2), (5.5, 3.2), (8.5, 4.6), (12.5, 6.0), (17.0, 6.0), (20.4, 5.6)]
CAP = [(20.6, 5.5), (21.2, 5.5), (22.3, 4.6), (23.4, 3.0), (24.0, 1.2), (24.1, 0.0)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(92, metallic=0.2, roughness=0.3),  # 0 crystal body
        pal(94, metallic=0.25, roughness=0.2),  # 1 bright end facets
        pal(87, metallic=0.2, roughness=0.5),  # 2 dark seam before the end
    ]
    BODY_M, CAP_M, SEAM_M = range(3)
    u = 1 / 12

    def sections(points):
        # Six sides with a vertex on top (the crest); flatter than wide. The side vertices sit at
        # 30 degrees, so the ring's half width is w * cos(30): scale up to keep the silhouette.
        k = 1 / math.cos(math.radians(30))
        return [(t * u, w * k * u, min(w * 0.42, 2.5) * u, 0.0) for t, w in points]

    bm = bmesh.new()
    common.loft(bm, sections(BODY), sides=6, mat_index=BODY_M)
    common.loft(bm, sections([(20.3, 5.65), (20.9, 5.65)]), sides=6, mat_index=SEAM_M)
    common.loft(bm, sections(CAP), sides=6, mat_index=CAP_M)

    # Lofted along +Y from the point; turn +Y to point down-right (sprite +col, +row) and put the
    # point on the sprite's tip (column 1, row 5 pixel centre).
    lib.rotate_z(bm, 0, math.radians(-135))
    lib.move(bm, 0, lib.px(1), lib.row(5))
    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
