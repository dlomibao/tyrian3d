"""Red crystal (tyrian.shp#10 frames 39-49, odd): a 3D version of its sprite.

Seen in episodes 1-4. The sprite draws a long red-orange crystal lying on the ground, points up
and down the screen: an elongated hexagon (columns 6-16, rows 3-23) with a bright ridge down the
middle (column 11), a lighter left face, a darker right face with a bright outer edge (column 16)
and pyramid tips. The six frames only move a sparkle of yellow-white glints across it, so one model
covers them all: an eight-sided crystal prism with a ridge on top, lying on its bottom ridge, with
four-sided pyramid tips, each facet coloured like its part of the sprite. The sparkle is a
diagonal band of light sweeping from the top-left tip (frame 41) to the bottom-right (49), one
band per frame (common.frame_part); frame 39 has none. Index 112 (near black
red) is its outline and isn't modelled.

Run: blender --background --python assets/blender/enemies/tyrian10-39.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b106 as lib  # noqa: E402
from lib_b106 import common, ex, ey  # noqa: E402

NAME = "tyrian10-39"
CX = ex(11.5)  # the ridge: column 11
W = 5.9 / 12  # half width (columns 6-16 plus a little of the dark rim)
H = 0.22  # half height; the crystal rests on its bottom ridge at z = 0
# The cross-section: ridge on top, upper faces, narrow outer edges, the underside.
SECTION = [(0, 1), (0.78, 0.62), (1, 0), (0.78, -0.62), (0, -1), (-0.78, -0.62), (-1, 0), (-0.78, 0.62)]


def ring(y, s=1.0):
    return [(CX + s * W * u, y, H + s * H * v) for u, v in SECTION]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(118, metallic=0.1, roughness=0.35),  # 0 left face
        pal(116, metallic=0.1, roughness=0.35),  # 1 right face (darker)
        pal(123, metallic=0.1, roughness=0.3),  # 2 bright right edge
        pal(120, metallic=0.1, roughness=0.3),  # 3 left edge
        pal(114, metallic=0.1, roughness=0.2),  # 4 underside, dark facets
        pal(121, metallic=0.1, roughness=0.3),  # 5 bright facets on the tips
        pal(122, metallic=0.1, roughness=0.2, emission_strength=1.5),  # 6 ridge glint
    ]
    LEFT, RIGHT, EDGE_R, EDGE_L, DARK, BRIGHT, GLINT = range(7)

    # Segments of the section: 0 top-right, 1 right edge, 2-5 underside, 6 left edge, 7 top-left.
    body = [RIGHT, EDGE_R, DARK, DARK, DARK, DARK, EDGE_L, LEFT]
    top_tip = [RIGHT, RIGHT, DARK, DARK, DARK, DARK, EDGE_L, EDGE_L]
    bottom_tip = [BRIGHT, BRIGHT, DARK, DARK, DARK, DARK, DARK, DARK]
    bm = bmesh.new()
    rings = [[(CX, ey(2.4), H)], ring(ey(8.0)), ring(ey(13.2), 1.02), ring(ey(18.6)), [(CX, ey(24.6), H)]]
    lib.ring_loft(bm, rings, [top_tip, body, body, bottom_tip])
    crystal = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # Thin bright edges: the ridge (column 11) and the right edge's glint (column 16).
    bm = bmesh.new()
    rid = [(p[0], p[1], p[2] + 0.004) for p in (rings[0][0], ring(ey(8.0))[0], ring(ey(13.2), 1.02)[0], ring(ey(18.6))[0],
                                                rings[-1][0])]
    lib.polyline_tube(bm, rid[1:4], 0.22 / 12, sides=4, mat_index=GLINT)
    edge = [ring(ey(9.0))[1], ring(ey(13.2), 1.02)[1], ring(ey(17.6))[1]]
    lib.polyline_tube(bm, [(x + 0.005, y, z + 0.004) for x, y, z in edge], 0.22 / 12, sides=4, mat_index=GLINT)
    glints = common.mesh_object(f"{NAME}_glints", bm, mats, coll, smooth=True)

    # The sweeping sparkle: on each frame after the first a diagonal band of the crystal lights up
    # orange-yellow with a white-hot core, moving from the top-left tip to the bottom-right. Each
    # band is a thin shell over the crystal cut between two diagonals (pixels with column + row in
    # the given range).
    mats += [pal(123, metallic=0.1, roughness=0.25, emission_strength=1.0),  # 7 band
             pal(126, metallic=0.1, roughness=0.2, emission_strength=2.0),  # 8 white-hot core
             pal(122, metallic=0.1, roughness=0.25, emission_strength=0.8),  # 9 fading band
             pal(125, metallic=0.1, roughness=0.2, emission_strength=1.5)]  # 10 fading core
    BAND, CORE, FADE_BAND, FADE_CORE = range(7, 11)
    sweeps = {41: ((13, 21, BAND), (16, 18, CORE)), 43: ((16, 23, BAND), (19, 21, CORE)),
              45: ((20, 26, BAND), (22, 24, CORE)), 47: ((22, 28, BAND), (24, 26, CORE)),
              49: ((26, 33, FADE_BAND), (29, 31, FADE_CORE))}
    parts = [crystal, glints]
    for frame, bands in sweeps.items():
        bm = bmesh.new()
        for (s0, s1, mat), lift in zip(bands, (0.004, 0.008)):
            sheen_band(bm, crystal, s0, s1, lift, mat)
        parts.append(common.frame_part(common.mesh_object(f"{NAME}_sparkle_{frame}", bm, mats, coll, smooth=False),
                                       [frame]))

    return [(NAME, parts, sprite["sprites"])]


def sheen_band(bm, obj, s0, s1, lift, mat):
    """Add to `bm` a copy of `obj`'s surface pushed out by `lift`, kept only between the diagonals
    through pixels with column + row = s0 and s1 (inclusive), all of material `mat`."""
    shell = bmesh.new()
    shell.from_mesh(obj.data)
    shell.normal_update()
    for v in shell.verts:
        v.co += v.normal * lift
    # Column + row of a pixel centre is 12x - 12y + 25 at (x, y), so the edges of the band are the
    # lines x - y = (s - 25 -/+ 0.5) / 12.
    for s, sign in ((s0 - 0.5, -1), (s1 + 0.5, 1)):
        geom = shell.verts[:] + shell.edges[:] + shell.faces[:]
        bmesh.ops.bisect_plane(shell, geom=geom, plane_co=((s - 25) / 12, 0, 0), plane_no=(sign, -sign, 0),
                               clear_outer=True)
    for f in shell.faces:
        f.material_index = mat
    mesh = bpy.data.meshes.new("sheen_tmp")
    shell.to_mesh(mesh)
    shell.free()
    bm.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
