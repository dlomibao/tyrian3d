"""Small grey-blue asteroid (newshd.shp frame 114): a 3D version of its sprite.

Seen in episodes 1-3. A chunky rock traced to the sprite's silhouette (its dark outline ring
included), about 10 px tall for its 12 px width, its two lit facet clusters raised as the high points
(see lib_b014.rock), each flattened into one broad facet turned toward the game's sun (plateaus) so
the light picks the facets out. Matte stone in one mid blue-grey (no painted outline or shading):
the game's light shades it and draws its outline. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-114.py [-- --preview out.png]
"""

import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402
import common  # noqa: E402  (lib_b014 puts assets/blender on the path)

NAME = "newshd-114"
SHADES = 6
HALF = 0.5  # half thickness (units): the top stands about 7.5 px above the midplane
ROCK = 105  # the mean of the sprite body's blue-greys (inside its outline ring), for the whole rock
ROUND = 0.7  # < 1 rounds the top over into a dome with steep sides

# The sprite's two lit facet clusters are lit faces of real shape: each becomes one flat facet
# turned toward the game's sun (src/render/view.ts: from the left and the screen bottom, high up;
# in Blender axes SUN) so the light picks it out, instead of a pointed peak whose small faces all
# catch the light alike. Top vertices brighter than LIT (sprite luminance) are flattened onto their
# cluster's plane through its highest point; the dark crack between them stays sunk.
SUN = Vector((-6.0, -8.4, 20.0)).normalized()
LIT = 120
TILT = 1.0  # 1 = facet faces straight at the sun, 0 = level


def plateaus(bm, shade):
    """Flatten each lit cluster of top vertices onto one plane tilted toward the sun."""
    zmax = max(v.co.z for v in bm.verts)
    lit = [v for v in bm.verts if v.co.z > 0.35 * zmax and (shade.at(v.co.x, v.co.y) or 0) > LIT]
    if len(lit) < 4:
        return
    # Two clusters (2-means on x, y), seeded with the two lit vertices farthest apart.
    c0 = max(lit, key=lambda v: v.co.x + v.co.y).co.xy
    c1 = min(lit, key=lambda v: v.co.x + v.co.y).co.xy
    for _ in range(8):
        g0 = [v for v in lit if (v.co.xy - c0).length <= (v.co.xy - c1).length]
        g1 = [v for v in lit if (v.co.xy - c0).length > (v.co.xy - c1).length]
        if not g0 or not g1:
            break
        c0 = sum((v.co.xy for v in g0), Vector((0, 0))) / len(g0)
        c1 = sum((v.co.xy for v in g1), Vector((0, 0))) / len(g1)
    n = Vector((SUN.x * TILT, SUN.y * TILT, 1.0)).normalized()
    for group in (g0, g1):
        if not group:
            continue
        top = max(group, key=lambda v: v.co.z).co.copy()
        for v in group:
            v.co.z = top.z - (n.x * (v.co.x - top.x) + n.y * (v.co.y - top.y)) / n.z
            v.co.z = min(v.co.z, zmax * 1.05)
    bm.normal_update()


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
        rock = common.palette_material(sprite, ROCK, NAME, metallic=0.0, roughness=0.8)
        mats[:] = [rock]
        for f in bm.faces:
            f.material_index = 0

    bm, mats, shade = lib.rock(sprite, NAME, frame["pixels"], size=size, half_height=HALF, relief=0.12,
                           seed=114, grow=1.25, flat_bottom=0.5, shades=SHADES, extra=reshape)
    plateaus(bm, shade)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
