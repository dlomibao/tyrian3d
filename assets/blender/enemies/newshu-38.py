"""Grey dome fragment with a red slot (newshu.shp frame 38, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 1 (level section 19) and episode 3 (level section 23). A ground piece: the rounded
lower-left shoulder of a grey dome, brightest along the top edge where it continues off the tile
and falling away to a dark rim on the left and the diagonal lower-left edge. In the lower right a
dark recessed slot holds a short red light strip. One frame, so one model.

Run: blender --background --python assets/blender/enemies/newshu-38.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b136 as lib  # noqa: E402
from lib_b136 import common  # noqa: E402

NAME = "newshu-38"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# The dome's footprint in sprite edges; the slot (columns 9-11, rows 6-12) is cut out of it after.
OUTLINE = [(4.0, 0.0), (12.0, 0.0), (12.0, 13.4), (9.4, 13.3), (7.4, 12.4), (6.2, 11.6),
           (4.6, 10.6), (3.3, 9.7), (2.3, 8.7), (1.5, 7.8), (1.3, 5.0), (1.3, 2.4), (2.0, 1.2), (3.0, 0.4)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.45, roughness=0.5),  # 0 dark lower rim
        pal(6, metallic=0.5, roughness=0.4),  # 1 dome flank
        pal(8, metallic=0.5, roughness=0.35),  # 2 dome crown
        pal(11, metallic=0.55, roughness=0.3),  # 3 bright top edge
        pal(2, metallic=0.3, roughness=0.7),  # 4 slot recess
        pal(66, metallic=0.3, roughness=0.6),  # 5 dark red slot floor
        pal(71, emission_strength=3.5),  # 6 red light
        pal(73, emission_strength=4.0),  # 7 light's bright top
    ]
    RIM, FLANK, CROWN, TOP, RECESS, FLOOR, LIGHT, LIGHT_TOP = range(8)
    bm = bmesh.new()

    lib.mound(bm, OUTLINE, (12.0, 0.0),
              [(1.0, 0.0), (0.96, 0.08), (0.86, 0.16), (0.7, 0.23), (0.5, 0.275), (0.28, 0.295), (0.0, 0.3)],
              [RIM, RIM, FLANK, FLANK, CROWN, TOP])
    dome = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # Cut the slot into the dome's lower right, down to the height of its dark floor.
    bm = bmesh.new()
    lib.block(bm, [(9.2, 6.0), (12.5, 6.0), (12.5, 14.5), (9.2, 14.5)], 0.072, 1.0, 0)
    cutter = common.mesh_object(NAME + "-cutter", bm, [], coll)
    mod = dome.modifiers.new("slot", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    with bpy.context.temp_override(object=dome, active_object=dome):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    bm = bmesh.new()

    # The slot: a dark recess below the dome's surface, its floor dark red at the bottom right.
    lib.block(bm, [(9.2, 6.0), (12.0, 6.0), (12.0, 13.4), (9.4, 13.3)], 0.0, 0.074, RECESS)
    lib.block(bm, [(10.0, 10.0), (12.0, 10.0), (12.0, 13.2), (10.0, 13.0)], 0.07, 0.08, FLOOR)
    # The red light strip (column 10, rows 7-9), brightest at its top.
    lib.block(bm, [(10.0, 7.8), (11.0, 7.8), (11.0, 10.0), (10.0, 10.0)], 0.06, 0.11, LIGHT)
    lib.block(bm, [(10.0, 7.0), (11.0, 7.0), (11.0, 7.8), (10.0, 7.8)], 0.06, 0.115, LIGHT_TOP)

    return [dome, common.mesh_object(NAME + "-slot", bm, mats, coll, smooth=False)]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = build(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
