"""Small grey-blue asteroid (newshd.shp frame 114): a 3D version of its sprite.

Seen in episodes 1-3. A chunky rock traced to the sprite's silhouette (its dark outline ring
included), about 10 px tall for its 12 px width, its two lit facet clusters raised as the high points
and painted with the sprite's own blue-grey ramp (see lib_b014.rock). The faces over the sprite's
near-black rim take that near-black. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-114.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402
import common  # noqa: E402  (lib_b014 puts assets/blender on the path)

NAME = "newshd-114"
RIM = (-1, 1, 32)  # transparent, the near-black rim and the outline index
SHADES = 6
HALF = 0.5  # half thickness (units): the top stands about 7.5 px above the midplane
SLATE = 102  # the sprite's mid blue-grey, for the flanks and underside
ROUND = 0.7  # < 1 rounds the top over into a dome with steep sides


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    size = frame["size"]

    _, edges = lib.shade_slots(sprite, frame["pixels"], SHADES)

    def reshape(bm, mats, shade):
        # Round the top over: lift the upper flanks (z -> zmax * (z / zmax) ** ROUND) so the top is
        # a broad dome and the sides fall steeply to the rim, like a boulder rather than a cone.
        zmax = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            if v.co.z > 0:
                v.co.z = zmax * (v.co.z / zmax) ** ROUND
        # Repaint for the new normals (as lib_b014.rock does): the sprite's shade under each face,
        # one shade darker on the steep rim.
        bm.normal_update()
        for f in bm.faces:
            if f.normal.z < -0.3:
                f.material_index = 0
                continue
            cen = f.calc_center_median()
            pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
            vals = [x for x in (shade.at(q.x, q.y, blur=0.3) for q in pts) if x is not None]
            if not vals:
                f.material_index = 1 if f.normal.z > 0.3 else 0
                continue
            k = lib.band_of(edges, sum(vals) / len(vals))
            if f.normal.z < 0.2:
                k = max(0, k - 1)
            f.material_index = k
        # The sprite's outer ring is near-black (indices 32 and 1): faces over it that show from
        # above take index 1.
        mats.append(common.palette_material(sprite, 1, NAME + "_rim", metallic=0.15, roughness=0.9))
        rim = len(mats) - 1
        for f in bm.faces:
            c = f.calc_center_median()
            if f.normal.z > 0.0 and shade.index(c.x, c.y) in RIM:
                f.material_index = rim
        # Faces that face down or sit below the equator never show from above: give them the
        # sprite's blue-grey slate (index 102) rather than the neutral dark grey of its darkest
        # band, so the rock's flanks read blue-grey in the 3/4 and game views (the light darkens
        # them anyway).
        mats.append(common.palette_material(sprite, SLATE, NAME + "_slate", metallic=0.15, roughness=0.85))
        slate = len(mats) - 1
        for f in bm.faces:
            if f.normal.z <= 0.0 or f.calc_center_median().z < 0.0:
                f.material_index = slate

    bm, mats, _ = lib.rock(sprite, NAME, frame["pixels"], size=size, half_height=HALF, relief=0.07,
                           seed=114, grow=1.25, flat_bottom=0.5, shades=SHADES, extra=reshape)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
