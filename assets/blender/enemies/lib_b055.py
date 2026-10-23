"""Helpers for batch b055 (the newshk yoke boss, assembly-newshk-237).

Coordinates are assembly pixel EDGES (col, row): column edge e is Blender X = (e - X0) / 12 and
row edge r is Blender Y = (Y0 - r) / 12, so pixel (c, r) covers [c, c + 1] x [r, r + 1]. Heights
are in units. Not a model script (build-models.sh skips lib_ files).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12
X0, Y0 = 36.0, 42.0  # assembly edge (36, 42) is the Blender origin (screen cx 141, cy 71)


def X(e):
    return (e - X0) * PX


def Y(r):
    return (Y0 - r) * PX


def _set(bm, first_face, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in pixel edges.
    Rings stand perpendicular to the path in the XY plane; a ring of zero size is a point."""
    n0 = len(bm.faces)
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a)))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _set(bm, n0, mat, smooth)


def loft_y(bm, col, sections, sides=12, mat=0, smooth=True):
    """A loft down the screen centred on column edge `col`: sections (row, half_width_px, half_height, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def _ccw(pts):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area > 0 else list(reversed(pts))


def inset(pts, d):
    """Move each vertex of a counter-clockwise polygon (Blender XY) `d` units inward (mitred)."""
    out = []
    n = len(pts)
    for i in range(n):
        p = Vector(pts[i])
        a = Vector(pts[i - 1])
        b = Vector(pts[(i + 1) % n])
        e1 = (p - a).normalized()
        e2 = (b - p).normalized()
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        bis = n1 + n2
        if bis.length < 1e-6:
            bis = n1
        bis.normalize()
        k = d / max(bis.dot(n1), 0.35)
        q = p + bis * k
        out.append((q.x, q.y))
    return out


def pillow(bm, outline, z0, z1, bevel=0.8, mat=0, smooth=False, bottom_bevel=None):
    """A plate with the outline (col, row edges) from z0 to z1, its top and bottom edges chamfered
    by `bevel` pixels so it reads as a solid part, not a cut-out."""
    n0 = len(bm.faces)
    base = _ccw([(X(c), Y(r)) for c, r in outline])
    bb = bevel if bottom_bevel is None else bottom_bevel
    h = z1 - z0
    layers = []
    if bb:
        layers.append((bb * PX, z0))
        layers.append((0.0, z0 + min(h * 0.3, bb * PX * 0.8)))
    else:
        layers.append((0.0, z0))
    if bevel:
        layers.append((0.0, z1 - min(h * 0.3, bevel * PX * 0.8)))
        layers.append((bevel * PX, z1))
    else:
        layers.append((0.0, z1))
    rings = []
    for d, z in layers:
        poly = inset(base, d) if d else base
        rings.append([bm.verts.new((x, y, z)) for x, y in poly])
    n = len(base)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    _cap(bm, rings[-1], up=True)
    _cap(bm, rings[0], up=False)
    _set(bm, n0, mat, smooth)


def _cap(bm, ring, up=True):
    """Fill a (possibly concave) counter-clockwise ring with triangles facing up or down."""
    from mathutils.geometry import tessellate_polygon
    tris = tessellate_polygon([[Vector((v.co.x, v.co.y, 0.0)) for v in ring]])
    for a, b, c in tris:
        tri = [ring[a], ring[b], ring[c]]
        e1 = tri[1].co - tri[0].co
        e2 = tri[2].co - tri[0].co
        if (e1.x * e2.y - e1.y * e2.x > 0) != up:
            tri.reverse()
        try:
            bm.faces.new(tri)
        except ValueError:
            pass


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid centred on pixel edge (col, row) at height z. z_min flattens what's below it."""
    n0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        zz = z + v.co.z * rz
        if z_min is not None:
            zz = max(zz, z_min)
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, zz))
    _set(bm, n0, mat, True)


def mirror_all(bm, axis_edge, first_vert=0):
    """Add a mirror image about column edge `axis_edge` of everything from vertex `first_vert` on."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[first_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + faces)["geom"]
    ax = X(axis_edge)
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite(root, names):
    """The first name's sprite.json with the colours of every listed piece."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w_px, h_px, ox, oy):
    """The pieces' first frames as one image (w_px x h_px), piece centre (cx, cy) drawn at
    (cx + ox, cy + oy)."""
    import numpy as np
    img = np.zeros((h_px, w_px, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = cx + ox - 12, cy + oy - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h_px and 0 <= x0 + c < w_px:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w_px, h_px, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
