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

Within a model the frames still differ, so each animates (common.frame_part, palette_material
frames=): the pyramid catches a pink glint on its left face on frame 79 and comes back rounded at
the base on frame 119 (its own body, painted from that frame); the swelling pyramid's frame 117 is
the cube rounding off on its way back (its own body); the ball gets a body painted from each
frame, its hot spot white on 85 and pale on the others; the cube's lower edge fades to a dull
pink glint on frame 115.

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


def outline_cone(bm, pixels, apex, base_z=-0.04, under_z=-0.16, segments=40, rings=10):
    """A low cone from `apex` (a near vertex, x, y, z) out to the frame's outline in every
    direction, with a shallower cone under it: for the in-between shapes, whose outline is neither
    the pyramid's nor the cube's. Paint it with lib.paint."""
    ax, ay, az = apex

    def reach(ang):
        r, last = 0.0, 0.0
        while r < 1.3:
            if lib.sample(pixels, ax + r * math.cos(ang), ay + r * math.sin(ang)) >= 0:
                last = r
            r += 0.25 / 12
        return last + 0.4 / 12

    raw = [reach(2 * math.pi * k / segments) for k in range(segments)]
    # Soften the pixel steps in the outline.
    radii = [(raw[k - 1] + 2 * raw[k] + raw[(k + 1) % segments]) / 4 for k in range(segments)]

    def ring(t, top):
        h = (az - base_z) * (1 - t) ** 0.8 + base_z if top else base_z + (under_z - base_z) * (1 - t) ** 0.6
        return [bm.verts.new((ax + r * t * math.cos(2 * math.pi * k / segments),
                              ay + r * t * math.sin(2 * math.pi * k / segments), h))
                for k, r in enumerate(radii)]

    tip = bm.verts.new((ax, ay, az))
    bottom = bm.verts.new((ax, ay, under_z))
    tops = [ring(i / rings, True) for i in range(1, rings + 1)]
    unders = [ring(i / rings, False) for i in range(1, rings)] + [tops[-1]]
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((tip, tops[0][k], tops[0][j]))
        bm.faces.new((bottom, unders[0][j], unders[0][k]))
        for a, b in zip(tops, tops[1:]):
            bm.faces.new((a[k], b[k], b[j], a[j]))
        for a, b in zip(unders, unders[1:]):
            bm.faces.new((a[j], b[j], b[k], a[k]))
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


def glow_edges(bm, v, ends, hot_slot=6, edge_slot=4, knot=True):
    """Glowing bars along the near edges from vertex v, with a hot knot where they meet.
    `edge_slot` is one slot or one per edge."""
    slots = edge_slot if isinstance(edge_slot, list) else [edge_slot] * len(ends)
    for e, slot in zip(ends, slots):
        lib.polyline_tube(bm, [tuple(v), tuple(v + (e - v) * 0.5), tuple(e)],
                          [0.75 / 12, 0.55 / 12, 0.25 / 12], sides=6, mat_index=slot)
    if knot:
        glow_knot(bm, v, hot_slot)


def glow_knot(bm, v, hot_slot):
    lib.ellipsoid(bm, tuple(v), (1.0 / 12, 1.0 / 12, 0.04), segments=10, rings=5, mat_index=hot_slot)


def face_patch(bm, a, b, c, centre, radii, mat_index, lift=0.006, sides=12):
    """A flat elliptical patch lying on the plane through a, b, c (lifted off it along its
    upward normal), centred over the XY point `centre` with XY radii `radii`."""
    n = (b - a).cross(c - a).normalized()
    if n.z < 0:
        n = -n

    def on_plane(x, y):
        return Vector((x, y, a.z - (n.x * (x - a.x) + n.y * (y - a.y)) / n.z)) + n * lift

    ring = [bm.verts.new(on_plane(centre[0] + radii[0] * math.cos(2 * math.pi * k / sides),
                                  centre[1] + radii[1] * math.sin(2 * math.pi * k / sides)))
            for k in range(sides)]
    bm.faces.new(ring).material_index = mat_index


def tag(obj, frames):
    return common.frame_part(obj, frames)


def frame_pixels(sprite, index):
    return next(f["pixels"] for f in sprite["frames"] if f["index"] == index)


def build(sprite):
    coll = common.reset_collection(NAME)
    order = [f["index"] for f in sprite["frames"]]
    out = []

    def add(model, objs, frames, preview):
        out.append((model, objs, lib.subset(sprite, frames)))
        sprite.setdefault("_preview", {})[model] = order.index(preview)

    tetra_faces = [(f[:3], f[3]) for f in TETRA_FACES]

    # Pyramid (frames 77, 79): its knot is white-hot on 77 and a pale glint on 79, where a pink
    # glint also lies on the left face (columns 7-11, rows 9-12) and a small one at the right
    # corner (columns 17-18, rows 17-18). Frame 119 is the pyramid still rounded at the base: a
    # low cone from the near vertex to that frame's outline, painted from it, with the glowing edges.
    model = NAME
    mats = materials(sprite, model)
    bm = bmesh.new()
    polyhedron(bm, TETRA, tetra_faces, slot)
    glow_edges(bm, TETRA[0], TETRA[1:], knot=False)
    pyramid = tag(common.mesh_object(model, bm, mats, coll, smooth=False), [77, 79])
    knots = []
    for frames, hot in (([77], 6), ([79], 9)):
        bm = bmesh.new()
        glow_knot(bm, TETRA[0], hot)
        knots.append(tag(common.mesh_object(f"{model}-knot-{frames[0]}", bm, mats, coll, smooth=False), frames))
    bm = bmesh.new()
    face_patch(bm, TETRA[0], TETRA[2], TETRA[1], (px(9.3), row(10.6)), (2.3 / 12, 2.0 / 12), 8)
    face_patch(bm, TETRA[0], TETRA[1], TETRA[3], (px(17.6), row(17.6)), (1.0 / 12, 0.8 / 12), 8)
    glint = tag(common.mesh_object(f"{model}-glint-79", bm, mats, coll, smooth=False), [79])
    bm = bmesh.new()
    v = Vector((px(12), row(17), 0.26))
    outline_cone(bm, frame_pixels(sprite, 119), v)
    lib.paint(bm, frame_pixels(sprite, 119), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12)
    glow_edges(bm, v, [P(12.2, 2.8, 0.0), v + (TETRA[2] - TETRA[0]) * 0.3, v + (TETRA[3] - TETRA[0]) * 0.3],
               hot_slot=9)
    rounded = tag(common.mesh_object(f"{model}-119", bm, mats, coll, smooth=True), [119])
    add(model, [pyramid, *knots, glint, rounded], [77, 79, 119], 77)

    # Swelling pyramid: half way to a ball, painted from frame 81. Frame 117 is the cube rounding
    # off into the pyramid: a low cone from its near corner to the frame's outline, painted from it.
    model = f"{NAME}-f2"
    mats = materials(sprite, model)
    cen, planes = planes_of(TETRA, tetra_faces)
    cen = Vector((px(12), row(13.5), 0.0))
    bm = bmesh.new()
    morph_ball(bm, cen, planes, (9.0 / 12, 9.6 / 12, 0.27), 0.2, power=5.0, grow=1.12)
    lib.paint(bm, frame_pixels(sprite, 81), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12, average=False)
    swell = tag(common.mesh_object(model, bm, mats, coll, smooth=True), [81])
    bm = bmesh.new()
    outline_cone(bm, frame_pixels(sprite, 117), (px(12.4), row(10.5), 0.28))
    lib.paint(bm, frame_pixels(sprite, 117), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12)
    back = tag(common.mesh_object(f"{model}-117", bm, mats, coll, smooth=True), [117])
    add(model, [swell, back], [81, 117], 81)

    # Ball (frames 83-89), a body painted from each frame: the hot spot (columns 8-11, rows 10-12)
    # is white-hot on 85 and a pale glint on the others, and the glowing seam at the lower right
    # shifts. The hot spot stands as a blister.
    model = f"{NAME}-f3"
    mats = materials(sprite, model)
    parts = []
    for frame in (85, 83, 87, 89):
        bm = bmesh.new()
        morph_ball(bm, Vector((px(11.5), row(13.6), 0.0)), [], (9.1 / 12, 9.8 / 12, 0.28), 1.0)
        lib.paint(bm, frame_pixels(sprite, frame), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12)
        lib.ellipsoid(bm, (px(10.6), row(11.0), 0.235), (2.0 / 12, 1.7 / 12, 0.06), segments=12, rings=5,
                      mat_index=7 if frame == 85 else 9)
        name = model if frame == 85 else f"{model}-{frame}"
        parts.append(tag(common.mesh_object(name, bm, mats, coll, smooth=True), [frame]))
    add(model, parts, [83, 85, 87, 89], 85)

    # Rounded cube (frame 91): the cube pulled a third of the way to a ball.
    model = f"{NAME}-f4"
    verts, faces = cube_geometry(P(12.6, 9.8, 0.3), CUBE_E, 1.0)
    cen, planes = planes_of(verts, faces)
    bm = bmesh.new()
    morph_ball(bm, Vector((cen.x, cen.y, 0.0)), planes, (9.4 / 12, 10.6 / 12, 0.29), 0.1, power=5.0, grow=1.13)
    lib.paint(bm, frame_pixels(sprite, 91), slot, under_slot=0, min_nz=-0.3, spread=0.5 / 12)
    add(model, [common.mesh_object(model, bm, materials(sprite, model), coll, smooth=True)],
        [91], 91)

    # Cube, corner-on (frames 93, 115). Its lower edge glows red on 93 and fades to a dull pink
    # glint on 115 (column 12, rows 13-17).
    model = f"{NAME}-f5"
    mats = materials(sprite, model) + [
        common.palette_material(sprite, 119, f"{model}-edge", roughness=0.3, emission_strength=2.0,
                                frames={115: 70}),  # 12 lower edge
    ]
    verts, faces = cube_geometry(CUBE_V, CUBE_E)
    bm = bmesh.new()
    polyhedron(bm, verts, faces, slot)
    glow_edges(bm, verts[0], verts[1:4], hot_slot=6, edge_slot=[4, 12, 4])
    add(model, [common.mesh_object(model, bm, mats, coll, smooth=False)], [93, 115], 93)
    return out


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
