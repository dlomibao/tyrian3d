"""Small grey-blue asteroid (newshd.shp frame 95): a 3D version of its sprite.

Seen in episodes 1-3. A round, faceted boulder traced to the sprite's silhouette (grown over its
dark rim), about as tall as it is wide as the sprite's highlight and black rim say, its lit facets
raised and cut by big flat planes (CHIPS) into a faceted crest: the bright streak down its left-centre
is the crest's left face turned to the light (on rock a highlight is a lit face of real shape), and
a long face slopes away to the shadowed right, so it reads in game as broken stone with
sharp-edged facets, not a smooth pebble. The whole rock takes the sprite's blue-grey mid-tone in one matte material:
the sprite's dark grey limb, black outline and bright streak are its drawn lighting, which the
game's lights and outline make, so they are not painted on. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-95.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshd-95"
MID = 103  # the blue-grey mid-tone of the sprite's rock

# Chips knocked off the rock: (azimuth deg, elevation deg, depth as a fraction of the rock's extent
# along that direction). Each is a flat planar facet, so the rock reads as broken stone with sharp
# edges rather than a smooth pebble. Depths stay shallow enough that the top-view outline holds.
CHIPS = [
    # The crest: two big faces meeting along the bright streak left of centre, the left one turned
    # to the light, the right one sloping away to the shadowed right side.
    (178, 40, 0.15),
    (15, 36, 0.20),
    # Its ends: the crest's upper and lower slopes.
    (95, 38, 0.13),
    (265, 38, 0.13),
    # Corner facets.
    (140, 52, 0.13),
    (215, 48, 0.12),
    (50, 42, 0.15),
    (320, 42, 0.13),
    # Small chips so it's broken stone, not a cut gem.
    (60, 70, 0.08),
    (330, 66, 0.07),
    (200, 70, 0.06),
    (120, 66, 0.06),
    (160, 26, 0.05),
    (75, 28, 0.05),
    (345, 26, 0.05),
    (250, 24, 0.05),
]


def chip(bm):
    """Cut each CHIPS plane off the rock and cap it with one flat face."""
    for az, el, depth in CHIPS:
        a, e = math.radians(az), math.radians(el)
        n = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        proj = [v.co.dot(n) for v in bm.verts]
        hi, lo = max(proj), min(proj)
        d = hi - depth * (hi - lo)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n, clear_outer=True)
        cut = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.holes_fill(bm, edges=cut, sides=0)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.normal_update()


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    bm, _, _ = lib.rock(sprite, NAME, frame["pixels"], size=frame["size"], half_height=0.85,
                        relief=0.10, seed=95, grow=1.15, flat_bottom=0.8,
                        subdiv=2)
    chip(bm)
    # One matte rock colour; lib.rock's per-face shade bands would bake the sprite's lighting in.
    mats = [common.palette_material(sprite, MID, NAME, metallic=0.0, roughness=0.8)]
    for f in bm.faces:
        f.material_index = 0
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
