"""Falling canister (newshd.shp frame 77): a 3D version of its sprite.

Seen in episode 1 (levels 1.5 and 1.28). A grey steel canister, 13 x 25 px, flying nose down the
screen: a rounded head with a dark band and a slot on its right side, a slightly narrower neck, a
barrel-shaped body with a dark seam down its right side, and a red nose cone (its right side
darker, brown) poking out of a grey skirt at the bottom. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-77.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b036 as lib  # noqa: E402
from lib_b036 import common  # noqa: E402

NAME = "newshd-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U
CX = 12  # the canister's centre column


def ey(r):
    """Sprite row edge (top edge of row r) to Blender Y."""
    return (14 - r) * U


def ex(c):
    return (c - 12) * U


FLAT = 0.5  # the canister's height over its width


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = lib.Mats(NAME, sprite["colors"])
    head = mats(10, metallic=0.45, roughness=0.35)
    band = mats(6, metallic=0.45, roughness=0.4)
    neck = mats(8, metallic=0.45, roughness=0.35)
    body = mats(9, metallic=0.45, roughness=0.35)
    skirt = mats(7, metallic=0.45, roughness=0.4)
    slot = mats(2, metallic=0.3, roughness=0.6)
    seam = mats(3, metallic=0.4, roughness=0.6)
    red = mats(72, metallic=0.35, roughness=0.45)
    tip = mats(68, metallic=0.35, roughness=0.5)
    brown = mats(165, metallic=0.3, roughness=0.55)
    cx = (CX + 0.5 - 12) * U

    bm = bmesh.new()

    def at(x, fn):
        start = len(bm.verts)
        fn()
        common.shift_x(bm, start, x)

    def seg(sections, mat, sides=16, **kw):
        """A stretch of the canister: (row edge, half width px) sections, flattened by FLAT."""
        at(cx, lambda: common.loft(bm, [(ey(r), w * U, w * U * FLAT, 0.0) for r, w in sections],
                                   sides=sides, mat_index=mat, **kw))

    # Head (rows 3-8): a rounded dome, then the dark band under it (rows 8-10).
    seg([(2.95, 0.0), (3.1, 2.4), (3.6, 3.6), (4.5, 4.7), (5.5, 5.6), (6.6, 6.35), (8.0, 6.5)], head)
    seg([(8.0, 6.5), (10.4, 6.5), (10.9, 5.8)], band)
    # Neck (rows 11-12) and body (rows 13-19), which swells back out.
    seg([(10.9, 5.6), (12.9, 5.6), (13.2, 6.4)], neck)
    seg([(13.2, 6.4), (16.0, 6.5), (19.0, 6.4), (19.6, 5.7)], body)
    # The lower body narrows to the skirt round the nose cone.
    seg([(19.6, 5.6), (20.4, 5.4), (20.9, 4.9)], skirt)
    for side in (-1, 1):
        # The skirt's two sides (columns 7-8 and 16-17, rows 20-22) either side of the cone.
        at(cx + side * 4.4 * U, lambda: common.loft(
            bm, [(ey(19.8), 1.2 * U, 2.6 * U * FLAT, 0.0), (ey(21.5), 1.0 * U, 2.3 * U * FLAT, 0.0),
                 (ey(23.0), 0.6 * U, 1.6 * U * FLAT, 0.0)], sides=8, mat_index=skirt))
    # The red nose cone (rows 20-27) out of the skirt.
    seg([(19.8, 3.6), (21.0, 3.7), (23.0, 3.6), (24.4, 3.3), (25.4, 2.4), (26.4, 1.5), (27.3, 0.6),
         (27.8, 0.0)], red, sides=14)
    # Its tip a darker red.
    seg([(26.6, 1.42), (27.35, 0.62), (27.85, 0.0)], tip, sides=14, cap_start=False)
    # The brown stripe down the cone's right side (columns 13-14, rows 20-24).
    bm_start = len(bm.verts)
    common.loft(bm, [(ey(20.0), 0.8 * U, 0.3 * U, 0.0), (ey(21.0), 1.2 * U, 0.4 * U, 0.0),
                     (ey(23.0), 1.1 * U, 0.4 * U, 0.0), (ey(24.6), 0.9 * U, 0.3 * U, 0.0),
                     (ey(25.2), 0.0, 0.0, 0.0)], sides=8, mat_index=brown)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[bm_start:]:
        v.co.x += cx + 1.0 * U
        v.co.z += 3.6 * U * FLAT * 0.8
    parts = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)

    # Flat details: the slot in the head's right side (row 9, columns 13-15) and the seam down the
    # body's right side (column 15, rows 13-18).
    bm = bmesh.new()

    def surface(c, hw=6.5):
        """The canister's top surface height above column edge c."""
        off = min(abs(c - (CX + 0.5)), hw * 0.98)
        return hw * U * FLAT * (1 - (off / hw) ** 2) ** 0.5

    top = surface(13.0) + 0.012
    common.slab(bm, [(ex(13), ey(10)), (ex(16.2), ey(10)), (ex(16.2), ey(9)), (ex(13), ey(9))], 0.1,
                z=top - 0.05, mat_index=slot)
    top = surface(15.1) + 0.01
    common.slab(bm, [(ex(15.1), ey(19.3)), (ex(15.9), ey(19.3)), (ex(15.9), ey(13.4)), (ex(15.1), ey(13.4))],
                0.08, z=top - 0.04, mat_index=seam)
    details = common.mesh_object(f"{NAME}_details", bm, mats.list, coll, smooth=False)
    return [parts, details]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, objs, sprite)


if __name__ == "__main__":
    main()
