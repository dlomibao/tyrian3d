"""Helpers shared by batch b011's model scripts (newsh3 fireball, spiked mines, rings and rocks).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass w=12, h=14 for size-1 sprites).
Tube helpers are copied from lib_b007, the outline helpers from lib_b003 / lib_b004.
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402,F401


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True, cap_mats=None):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.

    `mats` gives a material index per band between consecutive rings (an int applies to all, a
    list of ints per band, or a list of lists per band and segment). Caps close the first/last ring
    (with cap_mats = (start, end) material indices, default the first/last band's)."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]

    def mat(band, seg):
        m = mats
        if isinstance(m, list):
            m = m[band]
        if isinstance(m, list):
            m = m[seg]
        return m
    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat(b, i)
    first = mat(0, 0) if not cap_mats else cap_mats[0]
    last = mat(len(verts) - 2, 0) if not cap_mats else cap_mats[1]
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = first
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = last
    return verts


def tube(bm, p0, p1, radius, sides=6, mat_index=0, caps=True, r1=None):
    """A round bar between two 3D points (pipes, struts, spikes). r1 tapers it (0 = a point)."""
    a, b = Vector(p0), Vector(p1)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for c, rad in ((a, radius), (b, radius if r1 is None else r1)):
        if rad == 0:
            rings.append([tuple(c)])
            continue
        ring = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides
            ring.append(tuple(c + rad * (math.cos(t) * u + math.sin(t) * v)))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, flat=1.0):
    """One continuous round tube along a polyline, with mitred joints (rings face the bisector).
    `radius` can be a number or a list with one radius per point (0 = a tip). `flat` scales the
    ring's vertical (Z) extent for flattened bands."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for i, (c, t) in enumerate(zip(pts, tangents)):
        u = (u - t * u.dot(t)).normalized()  # carry the frame along (parallel transport)
        v = t.cross(u).normalized()
        if radii[i] == 0:
            rings.append([tuple(c)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            off = radii[i] * (math.cos(a) * u + math.sin(a) * v)
            off.z *= flat
            ring.append(tuple(c + off))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def loft2(bm, sections, sides=12, mat_index=0, power=1.0, cap_start=True, cap_end=True, wobble=None):
    """Loft rings along Y. Each section is (y, x_centre, half_width, half_height, z_centre) in
    units; zero half width and height is a tip. power < 1 squares the cross-section off.
    wobble(angle, y) -> radius factor ripples the rings (flame flutes)."""
    rings = []
    for y, xc, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([(xc, y, z)])
            continue
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            c, s = math.cos(a), math.sin(a)
            u, v = math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)
            k = wobble(a, y) if wobble else 1.0
            ring.append((xc + w * u * k, y, z + h * v * k))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=cap_start, cap_end=cap_end)


def ellipsoid(bm, centre, radii, segments=12, rings=6, mat_index=0, rot=None, top_only=False):
    """An ellipsoid (or, with top_only, its upper half closed by a flat base). `rot` is a 3x3
    Matrix applied before moving it to `centre`."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    m = rot or Matrix.Identity(3)
    lo = 0 if top_only else -rings
    pts = []
    for k in range(lo, rings + 1):
        t = (math.pi / 2) * k / rings
        if k == rings:
            pts.append([(0.0, 0.0, rz)])
            continue
        if k == -rings:
            pts.append([(0.0, 0.0, -rz)])
            continue
        ring = []
        for i in range(segments):
            a = 2 * math.pi * (i + 0.5) / segments
            ring.append((rx * math.cos(t) * math.cos(a), ry * math.cos(t) * math.sin(a), rz * math.sin(t)))
        pts.append(ring)
    rings_w = [[tuple(Vector((cx, cy, cz)) + m @ Vector(p)) for p in ring] for ring in pts]
    return ring_loft(bm, rings_w, mat_index, cap_start=top_only, cap_end=False)


def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` (along its corner's bisector)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length * sign, ex_ / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def ccw(outline):
    """The outline counter-clockwise (seen from above)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    return list(outline) if area > 0 else list(reversed(outline))


def bevel_prism(bm, outline, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None, bottom_bevel=0.0):
    """A prism from z0 to z1 whose top edges are chamfered: the walls rise to z1 - bevel_h and a
    sloped band leads in by `bevel` to the flat top. bottom_bevel chamfers the bottom the same way."""
    outline = ccw(outline)
    bevel_h = bevel if bevel_h is None else bevel_h
    top = inset_outline(outline, bevel)
    n = len(outline)
    if bottom_bevel:
        bot = inset_outline(outline, bottom_bevel)
        lo = [bm.verts.new((x, y, z0)) for x, y in bot]
        lo2 = [bm.verts.new((x, y, z0 + bottom_bevel)) for x, y in outline]
    else:
        lo = [bm.verts.new((x, y, z0)) for x, y in outline]
        lo2 = None
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = mat_index
    bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
    chain = [lo] + ([lo2] if lo2 else []) + [mid, hi]
    for a, b in zip(chain, chain[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat_index


def chaikin(points, rounds=2, closed=True):
    """Round off a polyline's corners by corner cutting."""
    pts = [Vector(p) for p in points]
    for _ in range(rounds):
        out = []
        n = len(pts) if closed else len(pts) - 1
        if not closed:
            out.append(pts[0])
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append(p.lerp(q, 0.25))
            out.append(p.lerp(q, 0.75))
        if not closed:
            out.append(pts[-1])
        pts = out
    return [tuple(p) for p in pts]


def edges_outline(points, w=24, h=28):
    """(col, row) pixel-edge points to Blender XY."""
    return [(ex(c, w), ey(r, h)) for c, r in points]


def row_extents(frames, keep, w=None):
    """{row: (first column, last column + 1)} (pixel edges) of the pixels for which keep(index) is
    true, over the union of the given frames' pixel rows."""
    out = {}
    for pixels in frames:
        for r, line in enumerate(pixels):
            cols = [c for c, v in enumerate(line) if v >= 0 and keep(v)]
            if not cols:
                continue
            c0, c1 = min(cols), max(cols) + 1
            if r in out:
                c0, c1 = min(c0, out[r][0]), max(c1, out[r][1])
            out[r] = (c0, c1)
    return out


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview the first.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
        # Further models (other shapes of an animation) get their own previews.
        for k, (model, objects, sprites) in enumerate(models[1:], start=2):
            idx = sprites[0]["frames"][0]
            fr = next(f for f in sprite["frames"] if f["index"] == idx)
            ref = root / "reference" / "models" / name / fr["image"]
            common.render_preview(objects, out.replace(".png", f"-f{k}.png"), ref, size=fr["size"])
    return sprite


def mirror_x_new(bm, start_vert, start_face=None):
    """Duplicate the geometry built since vertex index `start_vert` mirrored across X = 0."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start_vert:]
    faces = list({f for v in verts for f in v.link_faces})
    geom = list(verts) + faces + list({e for v in verts for e in v.link_edges})
    ret = bmesh.ops.duplicate(bm, geom=geom)
    new = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in new:
        v.co.x = -v.co.x
    newf = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=newf)


def set_smooth(bm, face_start, smooth=True):
    """Mark the faces added since index `face_start` smooth (or flat). (From lib_b003.)"""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[face_start:]:
        f.smooth = smooth


def mesh_object_mixed(name, bm, materials, collection):
    """Like common.mesh_object, but keeps each face's own smooth flag (see set_smooth)."""
    import bpy
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def diamond_spike(bm, base, tip, half_w, half_h, mats=(0, 0, 0, 0), z_dir=(0, 0, 1), steps=None):
    """A spike with a diamond cross-section (a ridge on top and below) from `base` to a point at
    `tip`. `mats` gives the material of its four faces: upper-right, upper-left, lower-left,
    lower-right (seen looking from base to tip). `steps` is a list of (t, scale) to bulge it."""
    a, b = Vector(base), Vector(tip)
    axis = (b - a).normalized()
    up = Vector(z_dir)
    side = axis.cross(up).normalized()  # right of the axis
    up = side.cross(axis).normalized()
    rings = []
    for t, s in (steps or [(0.0, 1.0)]):
        c = a.lerp(b, t)
        rings.append([tuple(c + side * half_w * s), tuple(c + up * half_h * s),
                      tuple(c - side * half_w * s), tuple(c - up * half_h * s)])
    rings.append([tuple(b)])
    band = [list(mats)] * (len(rings) - 1)
    return ring_loft(bm, rings, band, cap_start=True, cap_end=False, cap_mats=(mats[3], mats[3]))


def rotate_new(bm, start, angle, cx=0.0, cy=0.0, dx=0.0, dy=0.0):
    """Rotate the vertices added since index `start` by `angle` (radians, counter-clockwise from
    above) about the origin, then move them by (cx + dx, cy + dy)."""
    bm.verts.ensure_lookup_table()
    c, s = math.cos(angle), math.sin(angle)
    for v in bm.verts[start:]:
        x, y = v.co.x, v.co.y
        v.co.x = cx + dx + x * c - y * s
        v.co.y = cy + dy + x * s + y * c
