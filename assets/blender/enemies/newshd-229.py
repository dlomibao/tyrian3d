"""Crystal asteroid (newshd.shp frames 229/231/233/235): a 3D version of its sprite, on the crag
builder (lib_crag_rock, D239).

What it is: newshd-123's rock (the same pixels but the light: built from that sprite with its seed,
so the two are one stone) with a blue crystal in the junction of its crevices, at (12.5, 14.5):
dormant on 229 (a dark blue-grey shard), small and lit on 231 (the cross: arms 151, heart 154),
large and lit on 233 (tips 150, facets 152/154, heart 157) and brighter on 235 (154, 156/158, heart
141). A random-spawn rock of ASTEROID1, tumbling free: round and closed underneath (D122). The
frames differ only in the light, so one rock carries a crystal per look (frame-tagged, D17); the
crystals are D123's, wedged between the stones at the height where the crevice is as wide as they
are, so the whole diamond shows from above.

    blender -b --factory-startup -P assets/blender/enemies/newshd-229.py -- [--no-bake] [--out file.glb]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

common = lib.common

NAME = "newshd-229"
PX = 1 / 12
SPEC = {"seed": 123, "source": "newshd-123"}

GEM_C = (12.5, 14.5)  # sprite point of the light (col, row): the crevices' junction
# Each look: (name, frames, girdle radius px (tip on the axes), apex height over the girdle px,
# bands [(palette, emission, {frame: palette})] outer to heart).
GEMS = [
    ("dormant", [229], 1.3, 1.6, [(102, 0.0, None)]),
    ("small", [231], 1.9, 2.6, [(151, 3.0, None), (154, 4.0, None)]),
    ("big", [233, 235], 2.8, 3.6, [(150, 3.5, {235: 154}), (152, 4.0, {235: 156}),
                                   (154, 4.5, {235: 158}), (157, 6.0, {235: 141})]),
]
GEM_IN = 0.6  # the girdle sits this far (px) under the stones' faces round it


def girdle_z(obj, rad):
    """Height (px) at which a crystal of girdle radius `rad` px sits: the highest the rock stands
    under its four tips and between them, less GEM_IN."""
    zs = []
    for k in range(8):
        a = math.pi * k / 4
        o = Vector(((GEM_C[0] - 12 + rad * math.cos(a)) * PX, (14 - GEM_C[1] - rad * math.sin(a)) * PX, 3.0))
        hit, loc, *_ = obj.ray_cast(o, Vector((0, 0, -1)))
        if hit:
            zs.append(loc.z / PX)
    return (max(zs) if zs else 0.0) - GEM_IN


def gem(sprite, coll, name, frames, rad, height, bands, z0):
    """A four-sided bipyramid crystal, its tips along the sprite's axes (its top view the sprite's
    diamond): a short vertical girdle, then crown rings shrinking to the apex, one ring per colour
    band, so from above the bands nest as the sprite's rings do; the pavilion sinks into the rock."""
    n = len(bands)
    bm = bmesh.new()
    mats = []
    for k, (idx, em, fr) in enumerate(bands):
        mats.append(common.palette_material(sprite, idx, f"{NAME}_{name}{k}", metallic=0.1 if em else 0.0,
                                            roughness=0.18 if em else 0.35, emission_strength=em, frames=fr))
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    gc, gr = GEM_C

    def ring(rr, z):
        return [bm.verts.new((gc - 12 + rr * dx, gr + rr * dy, z)) for dx, dy in dirs]

    gl = ring(rad, z0 - 0.35)
    gu = ring(rad, z0)
    apex = bm.verts.new((gc - 12, gr, z0 + height))
    bottom = bm.verts.new((gc - 12, gr, z0 - 0.35 - 2.6))

    def fan(rr, z, at):  # a ring of 4 at angles `at` + 90 k
        return [bm.verts.new((gc - 12 + rr * math.cos(math.radians(at + 90 * k)),
                              gr + rr * math.sin(math.radians(at + 90 * k)), z)) for k in range(4)]
    for k in range(4):
        j = (k + 1) % 4
        bm.faces.new((gl[k], gl[j], gu[j], gu[k])).material_index = 0
        bm.faces.new((gl[j], gl[k], bottom)).material_index = 0
    if n <= 2:
        # one crown: girdle to a heart ring (0.34 r) and its apex
        hr = ring(rad * 0.34, z0 + height * 0.7) if n == 2 else None
        for k in range(4):
            j = (k + 1) % 4
            if hr:
                bm.faces.new((gu[k], gu[j], hr[j], hr[k])).material_index = 0
                bm.faces.new((hr[k], hr[j], apex)).material_index = 1
            else:
                bm.faces.new((gu[k], gu[j], apex)).material_index = 0
    else:
        # the sprite's star: tips (band 0) round a square table on the diagonals (band 1, its corners
        # over the diagonal pixels), a diamond on the axes inside it (band 2, the four pixels next to
        # the heart) and the heart's own little pyramid (band 3)
        sq = fan(rad * 0.66, z0 + height * 0.38, 45)   # corners between tips k and k+1
        dm = ring(rad * 0.45, z0 + height * 0.66)
        ht = ring(rad * 0.21, z0 + height * 0.86)
        for k in range(4):
            j = (k + 1) % 4
            i = (k - 1) % 4
            bm.faces.new((gu[k], gu[j], sq[k])).material_index = 0      # edge facet
            bm.faces.new((sq[i], gu[k], sq[k])).material_index = 0      # tip facet
            bm.faces.new((sq[i], sq[k], dm[k])).material_index = 1      # tip-side table facet
            bm.faces.new((dm[k], sq[k], dm[j])).material_index = 1      # diagonal table facet
            bm.faces.new((dm[k], dm[j], ht[j], ht[k])).material_index = 2
            bm.faces.new((ht[k], ht[j], apex)).material_index = 3
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    obj = common.mesh_object(f"{NAME}_light_{name}", bm, mats, coll, smooth=False)
    return common.frame_part(obj, frames)



def parts(sprite, s, obj, coll):
    return [gem(sprite, coll, nm, fr, rad, h, bands, girdle_z(obj, rad)) for nm, fr, rad, h, bands in GEMS]


if __name__ == "__main__":
    lib.main(NAME, SPEC, parts=parts)
