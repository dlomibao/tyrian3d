"""Small green gem (newshv.shp frame 38, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A faceted diamond, bright along a ridge just right of centre, with
a short stalk trailing below it. It is the green twin of newshv-57 (red) and newshv-19 (blue):
the same pixels with the indices shifted, so this follows that model's shape (lib_b003.small_gem,
copied here), standing on the ground (base at z = 0) since this one is a ground enemy.

Run: blender --background --python assets/blender/enemies/newshv-38.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b081 as lib  # noqa: E402

NAME = "newshv-38"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U
W, H = 12, 14
LIFT = 0.09  # raise it so its lowest point is on the ground


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.4, roughness=0.4),  # 0 edge facets
        pal(44, metallic=0.45, roughness=0.3),  # 1 body facets
        pal(47, roughness=0.2, emission_strength=2.0),  # 2 bright crown, a glowing core
        pal(39, metallic=0.4, roughness=0.5),  # 3 stalk
        pal(42, metallic=0.4, roughness=0.4),  # 4 stalk tip
    ]
    EDGE, BODY, CROWN, STALK, TIP = range(5)
    cy = lib.ey(7.5, H)

    bm = bmesh.new()
    # The diamond: corners at columns 1 and 11 (edges), rows 3 and 12; 10 px wide, 9 px tall.
    lib.rings_solid(bm, (0.0, cy), [
        (0.0, -0.09, EDGE),
        (3.6 * U, -0.045, EDGE),
        (5.0 * U, 0.0, EDGE),
        (4.2 * U, 0.05, EDGE),
        (2.8 * U, 0.1, BODY),
        (1.0 * U, 0.135, CROWN),
        (0.0, 0.145, CROWN),
    ], sides=4)
    lib.scale(bm, 0, sy=0.9, cy=cy)
    # The bright ridge sits just right of centre (column 6): nudge the crown that way.
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        if v.co.z > 0.12:
            v.co.x += 0.25 * U
    lib.move(bm, 0, dz=LIFT)
    gem = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # The stalk below it (rows 11.5-14, columns 5-6), darker with a lighter knob at the end.
    bm = bmesh.new()
    z = -0.01 + LIFT
    common.loft(bm, [(lib.ey(11.2, H), 0.95 * U, 0.7 * U, z), (lib.ey(12.9, H), 0.95 * U, 0.7 * U, z)],
                sides=8, mat_index=STALK)
    common.loft(bm, [(lib.ey(12.9, H), 1.0 * U, 0.75 * U, z), (lib.ey(13.6, H), 0.95 * U, 0.7 * U, z),
                     (lib.ey(14.0, H), 0.0, 0.0, z)], sides=8, mat_index=TIP)
    stalk = common.mesh_object(f"{NAME}_stalk", bm, mats, coll, smooth=True)
    return [gem, stalk]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = build(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
