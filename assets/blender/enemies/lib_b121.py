"""Helpers for batch b121's scripts (the newshb.shp machine, assembly-newshb-115).

Coordinates are assembly pixel *edges*: e = 10 is the left edge of pixel column 10 and 10.5 its
centre. XE/YE turn them into Blender units for a layout whose origin is (ORIGIN_COL, ORIGIN_ROW).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


class Frame:
    """Pixel-edge to Blender coordinates, sprite up = +Y, with (col0, row0) at the origin."""

    def __init__(self, col0, row0):
        self.col0, self.row0 = col0, row0

    def x(self, e):
        return (e - self.col0) / 12

    def y(self, e):
        return (self.row0 - e) / 12


def faces_since(bm, n):
    bm.faces.ensure_lookup_table()
    return bm.faces[n:]


def prism(bm, F, outline, z0, z1, mat=0, smooth=False):
    """A flat-topped block from z0 up to z1 over an outline of (col, row) pixel edges; z1 can be a
    list (one top height per outline point) for sloped tops. Any winding order."""
    pts = [(F.x(c), F.y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    tops = list(z1) if isinstance(z1, (list, tuple)) else [z1] * len(pts)
    if area < 0:
        pts, tops = pts[::-1], tops[::-1]
    n = len(bm.faces)
    top = [bm.verts.new((x, y, z)) for (x, y), z in zip(pts, tops)]
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bottom)))
    k = len(pts)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    for f in faces_since(bm, n):
        f.material_index = mat
        f.smooth = smooth


def box(bm, F, c0, r0, c1, r1, z0, z1, mat=0):
    prism(bm, F, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def sweep(bm, F, path, sides=10, mat=0, smooth=True, closed=False, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand across
    the path (width in the XY plane, height along Z). A zero-size ring is a point (a tip).
    `closed` joins the last ring back to the first (a loop, no caps)."""
    pts = [Vector((F.x(c), F.y(r), z)) for c, r, z, _, _ in path]
    m = len(pts)
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        if closed:
            t = pts[(i + 1) % m] - pts[(i - 1) % m]
        else:
            t = pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    n = len(bm.faces)
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for r0, r1 in pairs:
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f)
    if not closed:
        if cap_start and len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0])))
        if cap_end and len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
    for f in faces_since(bm, n):
        f.material_index = mat
        f.smooth = smooth


def loft_y(bm, F, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on edge column `col`: sections are (row, half_width_px,
    half_height_units, z)."""
    sweep(bm, F, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def ellipsoid(bm, F, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8):
    """An ellipsoid centred on pixel edge coordinates (col, row) at height z."""
    n = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((F.x(col) + v.co.x * rx_px * PX, F.y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in faces_since(bm, n):
        f.material_index = mat
        f.smooth = True


def mirror_since(bm, n_verts, axis_x):
    """Add a mirror image (about Blender x = axis_x) of every vertex/face added since vertex index
    n_verts."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[n_verts:]
    faces = list({f for v in verts for f in v.link_faces})
    edges = list({e for v in verts for e in v.link_edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def write_png(path, width, height, rgba_rows):
    """Save rows (top first) of (r, g, b, a) floats 0-1 as a PNG through Blender."""
    im = bpy.data.images.new("b121_png", width, height, alpha=True)
    flat = []
    for row in reversed(rgba_rows):
        for px in row:
            flat.extend(px)
    im.pixels[:] = flat
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return path
