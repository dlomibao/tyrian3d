"""Morphing crystal (newshg.shp frames 77-93 and 115-119): a 3D version of its sprite.

Seen in episode 2 (level sections 4 and 19). A dark red solid with glowing orange edges that
shifts shape in a loop: a pyramid (seen point-on, its three near edges glowing where they meet),
which swells round into a ball with a white-hot spot and a glowing seam, then sets into a cube
(seen corner-on) and sharpens back into the pyramid. One model per shape:

- newshg-77: the pyramid (frames 77, 79, 119)
- newshg-77-f2: the swelling pyramid (frames 81, 117)
- newshg-77-f3: the ball (frames 83, 85, 87, 89)
- newshg-77-f4: the rounded cube (frame 91)
- newshg-77-f5: the cube (frames 93, 115)

The sharp shapes are true polyhedra with glowing edge bars; the rounded ones are a ball pulled
part way toward the polyhedron and painted from their frame.

Run: blender --background --python assets/blender/enemies/newshg-77.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b034 as lib  # noqa: E402
from lib_b034 import common, px, row  # noqa: E402

NAME = "newshg-77"


def P(c, r, z):
    return Vector((px(c), row(r), z))


# The pyramid (frame 77): near vertex V at column 12, row 17 with the top, bottom-left and
# bottom-right corners behind it.
TETRA = [P(12, 17, 0.28), P(12.2, 2.3, -0.1), P(3.3, 21.5, -0.1), P(21.0, 21.5, -0.1)]
TETRA_FACES = [(0, 2, 1, 115 + 1), (0, 1, 3, 114), (0, 3, 2, 115), (1, 2, 3, 112)]
# The cube (frame 93), corner-on: near vertex V and its neighbours upper-left, bottom and upper-right.
CUBE_V = P(13, 10, 0.3)
CUBE_E = [P(5.1, 6.4, 0.1) - CUBE_V, P(12.7, 21.6, 0.1) - CUBE_V, P(21.7, 5.6, 0.1) - CUBE_V]


def cube_geometry(v, e, scale=1.0):
    e = [x * scale for x in e]
    a, b, c = (v + x for x in e)
    ab, bc, ac = v + e[0] + e[1], v + e[1] + e[2], v + e[0] + e[2]
    f = v + e[0] + e[1] + e[2]
    verts = [v, a, b, c, ab, bc, ac, f]
    # (corner indices, palette index of the face): top face, left face, right face, then the back.
    faces = [((0, 3, 6, 1), 115), ((0, 1, 4, 2), 114), ((0, 2, 5, 3), 113),
             ((1, 6, 7, 4), 112), ((2, 4, 7, 5), 112), ((3, 5, 7, 6), 112)]
    return verts, faces


def polyhedron(bm, verts, faces, slot_of_index):
    """Flat-faced solid; faces wound so normals point away from the centroid."""
    cen = sum(verts, Vector()) / len(verts)
    bv = [bm.verts.new(v) for v in verts]
    for idx, pal in faces:
        pts = [verts[i] for i in idx]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        fc = sum(pts, Vector()) / len(pts)
        if n.dot(fc - cen) < 0:
            idx = tuple(reversed(idx))
        bm.faces.new([bv[i] for i in idx]).material_index = slot_of_index(pal)


def planes_of(verts, faces):
    cen = sum(verts, Vector()) / len(verts)
    out = []
    for idx, _ in faces:
        pts = [verts[i] for i in idx]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
        if n.dot(pts[0] - cen) < 0:
            n = -n
        out.append((n, n.dot(pts[0])))
    return cen, out


def morph_ball(bm, cen, planes, radii, t, power=6.0, grow=1.0, segments=32, rings=22):
    """A ball (poles along Y) whose radius in each direction is lerp(rounded polyhedron, ellipsoid,
    t). The polyhedron is rounded by a soft minimum over its planes (lower `power` = rounder),
    which shrinks it at the corners, so `grow` scales it back up."""
    rx, ry, rz = radii

    def point(u):
        r_ell = 1.0 / math.sqrt((u.x / rx) ** 2 + (u.y / ry) ** 2 + (u.z / rz) ** 2)
        if planes:
            inv = [max(0.0, n.dot(u)) / ((d - n.dot(cen)) * grow) for n, d in planes]
            r_poly = sum(k ** power for k in inv) ** (-1.0 / power)
            r = (1 - t) * r_poly + t * r_ell
        else:
            r = r_ell
        return cen + u * r

    top = bm.verts.new(point(Vector((0, 1, 0))))
    bot = bm.verts.new(point(Vector((0, -1, 0))))
    grid = []
    for i in range(1, rings):
        th = math.pi * i / rings
        grid.append([bm.verts.new(point(Vector((math.sin(th) * math.cos(2 * math.pi * (k + 0.5) / segments),
                                                 math.cos(th),
                                                 math.sin(th) * math.sin(2 * math.pi * (k + 0.5) / segments)))))
                     for k in range(segments)])
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((top, grid[0][j], grid[0][k]))
        bm.faces.new((bot, grid[-1][k], grid[-1][j]))
    for a, b in zip(grid, grid[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def materials(sprite, model):
    pal = lambda i, **kw: common.palette_material(sprite, i, model, **kw)  # noqa: E731
    return [
        pal(112, metallic=0.3, roughness=0.5),  # 0 darkest face
        pal(113, metallic=0.3, roughness=0.4),  # 1 dark face
        pal(115, metallic=0.3, roughness=0.35),  # 2 red face
        pal(117, metallic=0.3, roughness=0.3, emission_strength=0.5),  # 3 bright red
        pal(119, roughness=0.3, emission_strength=2.0),  # 4 glowing red
        pal(121, roughness=0.3, emission_strength=3.0),  # 5 orange glow
        pal(124, roughness=0.3, emission_strength=4.0),  # 6 yellow glow
        pal(127, roughness=0.2, emission_strength=5.0),  # 7 white-hot
        pal(72, metallic=0.4, roughness=0.15),  # 8 pink glint
        pal(172, metallic=0.4, roughness=0.1),  # 9 pale glint
        pal(114, metallic=0.3, roughness=0.4),  # 10 mid face
        pal(116, metallic=0.3, roughness=0.35),  # 11 face
    ]


def slot(i):
    """Material slot for a palette index (the sprite's ramp 112-127 and its glints)."""
    if i < 0:
        return None
    if i in (1, 64, 66, 67, 68, 112):
        return 0
    if 69 <= i <= 75:
        return 8
    if i >= 170 or 18 <= i <= 29:
        return 9
    return {113: 1, 114: 10, 115: 2, 116: 11, 117: 3, 118: 4, 119: 4, 120: 5, 121: 5, 122: 5,
            123: 6, 124: 6, 125: 6, 126: 7, 127: 7}.get(i, 2)


def glow_edges(bm, v, ends, hot_slot=6, edge_slot=4):
    """Glowing bars along the near edges from vertex v, with a hot knot where they meet."""
    for e in ends:
        lib.polyline_tube(bm, [tuple(v), tuple(v + (e - v) * 0.5), tuple(e)],
                          [0.75 / 12, 0.55 / 12, 0.25 / 12], sides=6, mat_index=edge_slot)
    lib.ellipsoid(bm, tuple(v), (1.0 / 12, 1.0 / 12, 0.04), segments=10, rings=5, mat_index=hot_slot)


def frame_pixels(sprite, index):
    return next(f["pixels"] for f in sprite["frames"] if f["index"] == index)


def build(sprite):
    coll = common.reset_collection(NAME)
    order = [f["index"] for f in sprite["frames"]]
    out = []

    def add(model, obj, frames, preview):
        out.append((model, [obj], lib.subset(sprite, frames)))
        sprite.setdefault("_preview", {})[model] = order.index(preview)

    # Pyramid.
    model = NAME
    bm = bmesh.new()
    polyhedron(bm, TETRA, [(f[:3], f[3]) for f in TETRA_FACES], slot)
    glow_edges(bm, TETRA[0], TETRA[1:], hot_slot=6)
    add(model, common.mesh_object(model, bm, materials(sprite, model), coll, smooth=False), [77, 79, 119], 77)

    # Swelling pyramid: half way to a ball, painted from frame 81.
    model = f"{NAME}-f2"
    cen, planes = planes_of(TETRA, [(f[:3], f[3]) for f in TETRA_FACES])
    cen = Vector((px(12), row(13.5), 0.0))
    bm = bmesh.new()
    morph_ball(bm, cen, planes, (9.0 / 12, 9.6 / 12, 0.27), 0.2, power=5.0, grow=1.12)
    lib.paint(bm, frame_pixels(sprite, 81), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12, average=False)
    add(model, common.mesh_object(model, bm, materials(sprite, model), coll, smooth=True), [81, 117], 81)

    # Ball (frames 83-89), painted from frame 85: white-hot spot upper left, glowing seam lower right.
    model = f"{NAME}-f3"
    bm = bmesh.new()
    morph_ball(bm, Vector((px(11.5), row(13.6), 0.0)), [], (9.1 / 12, 9.8 / 12, 0.28), 1.0)
    lib.paint(bm, frame_pixels(sprite, 85), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12)
    # The white-hot spot (columns 9-12, rows 10-12) as a glowing blister.
    lib.ellipsoid(bm, (px(10.6), row(11.0), 0.235), (2.0 / 12, 1.7 / 12, 0.06), segments=12, rings=5, mat_index=7)
    add(model, common.mesh_object(model, bm, materials(sprite, model), coll, smooth=True), [83, 85, 87, 89], 85)

    # Rounded cube (frame 91): the cube pulled a third of the way to a ball.
    model = f"{NAME}-f4"
    verts, faces = cube_geometry(P(12.6, 9.8, 0.3), CUBE_E, 1.0)
    cen, planes = planes_of(verts, faces)
    bm = bmesh.new()
    morph_ball(bm, Vector((cen.x, cen.y, 0.0)), planes, (9.4 / 12, 10.6 / 12, 0.29), 0.1, power=5.0, grow=1.13)
    lib.paint(bm, frame_pixels(sprite, 91), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12)
    add(model, common.mesh_object(model, bm, materials(sprite, model), coll, smooth=True), [91], 91)

    # Cube, corner-on (frames 93, 115).
    model = f"{NAME}-f5"
    verts, faces = cube_geometry(CUBE_V, CUBE_E)
    bm = bmesh.new()
    polyhedron(bm, verts, faces, slot)
    glow_edges(bm, verts[0], verts[1:4], hot_slot=6)
    add(model, common.mesh_object(model, bm, materials(sprite, model), coll, smooth=False), [93, 115], 93)
    return out


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
