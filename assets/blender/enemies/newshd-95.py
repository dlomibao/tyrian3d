"""Small grey-blue asteroid (newshd.shp frame 95): a 3D version of its sprite.

Seen in episodes 1-3. A round, faceted boulder traced to the sprite's silhouette (grown over its
dark rim), about as tall as it is wide as the sprite's highlight and black rim say, its lit facets
raised (the bright streak down its left-centre stands as a crest: on rock a highlight is a lit
face of real shape). The whole rock takes the sprite's blue-grey mid-tone in one matte material:
the sprite's dark grey limb, black outline and bright streak are its drawn lighting, which the
game's lights and outline make, so they are not painted on. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-95.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshd-95"
MID = 103  # the blue-grey mid-tone of the sprite's rock


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    bm, _, _ = lib.rock(sprite, NAME, frame["pixels"], size=frame["size"], half_height=0.46,
                        relief=0.08, seed=95, grow=1.15, flat_bottom=0.9)
    # One matte rock colour; lib.rock's per-face shade bands would bake the sprite's lighting in.
    mats = [common.palette_material(sprite, MID, NAME, metallic=0.03, roughness=0.85)]
    for f in bm.faces:
        f.material_index = 0
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
