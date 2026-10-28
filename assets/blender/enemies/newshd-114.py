"""Small grey-blue asteroid (newshd.shp frame 114): a 3D version of its sprite.

Seen in episodes 1-3. A chunky rock traced to the sprite's silhouette (its dark outline ring
included), about 10 px tall for its 12 px width, its two lit facet clusters raised as the high points
(see lib_b014.rock). Matte stone in one mid blue-grey: the game's light shades it and draws its
outline. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-114.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402
import common  # noqa: E402  (lib_b014 puts assets/blender on the path)

NAME = "newshd-114"
SHADES = 6
HALF = 0.5  # half thickness (units): the top stands about 7.5 px above the midplane
ROCK = 103  # the sprite's mid blue-grey, for the whole rock
ROUND = 0.7  # < 1 rounds the top over into a dome with steep sides


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    size = frame["size"]

    def reshape(bm, mats, _shade):
        # Round the top over: lift the upper flanks (z -> zmax * (z / zmax) ** ROUND) so the top is
        # a broad dome and the sides fall steeply to the rim, like a boulder rather than a cone.
        zmax = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            if v.co.z > 0:
                v.co.z = zmax * (v.co.z / zmax) ** ROUND
        # One colour for the whole rock: the sprite's mid blue-grey. Its light and dark pixels,
        # the dark grey ring (index 3) round the edge and the near-black outline (32, 1) are the
        # sprite's drawn lighting and outline; the game lights the raised facet clusters and draws
        # the outline itself, so painting them in would darken the rock twice. Stone is matte.
        rock = common.palette_material(sprite, ROCK, NAME, metallic=0.0, roughness=0.7)
        mats[:] = [rock]
        for f in bm.faces:
            f.material_index = 0

    bm, mats, _ = lib.rock(sprite, NAME, frame["pixels"], size=size, half_height=HALF, relief=0.07,
                           seed=114, grow=1.25, flat_bottom=0.5, shades=SHADES, extra=reshape)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
