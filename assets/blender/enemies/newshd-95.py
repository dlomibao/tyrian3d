"""Small grey-blue asteroid (newshd.shp frame 95): a 3D version of its sprite.

Seen in episodes 1-3. A round, faceted boulder traced to the sprite's silhouette (grown over its
dark rim), about as tall as it is wide as the sprite's highlight and black rim say, its lit facets
raised (the bright streak down its left-centre stands as a crest) and painted with the sprite's own
blue-grey ramp (see lib_b014.rock). Facets over the sprite's black rim take its near-black.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-95.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshd-95"
RIM = 1  # the sprite's near-black rim pixels


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]

    def rim(bm, mats, shade):
        mats.append(common.palette_material(sprite, RIM, NAME, metallic=0.15, roughness=0.9))
        k = len(mats) - 1
        bm.normal_update()
        for f in bm.faces:
            if f.normal.z < -0.3:
                continue
            c = f.calc_center_median()
            if shade.index(c.x, c.y) in lib.OUTLINE:
                f.material_index = k

    bm, mats, _ = lib.rock(sprite, NAME, frame["pixels"], size=frame["size"], half_height=0.46,
                           relief=0.08, seed=95, grow=1.15, flat_bottom=0.9, extra=rim)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
