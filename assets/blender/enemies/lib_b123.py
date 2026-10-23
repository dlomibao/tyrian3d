"""Helpers shared by the b123 model scripts (newshp ground pieces): pixel-space builders.

Everything is placed in sprite pixels: a Grid maps a pixel column/row (centre, fractions allowed)
to Blender X/Y, with sprite up = +Y and 1 px = 1/12 unit. Edges of pixel c are c - 0.5 and c + 0.5.
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


class Grid:
    """Pixel (col, row) centres to Blender X/Y for an image w x h px centred on the origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) * PX

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) * PX


def _tag(bm, before, mat, smooth):
    new = [f for f in bm.faces if f not in before]
    for f in new:
        f.material_index = mat
        f.smooth = smooth
    return new


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0, smooth=False):
    """An axis-aligned box over pixel edges c0..c1 (left..right) and r0..r1 (top..bottom rows)."""
    plate(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat, smooth)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (any winding)."""
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    before = set(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _tag(bm, before, mat, smooth)


def bevel_box(bm, g, c0, r0, c1, r1, z0, z1, bev, mat=0, smooth=False):
    """A box whose top edges are chamfered by `bev` units (horizontal and vertical)."""
    x0, x1 = g.X(c0 - 0.5), g.X(c1 - 0.5)
    y0, y1 = g.Y(r1 - 0.5), g.Y(r0 - 0.5)
    before = set(bm.faces)
    lo = [bm.verts.new(v) for v in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
    mid = [bm.verts.new(v) for v in ((x0, y0, z1 - bev), (x1, y0, z1 - bev), (x1, y1, z1 - bev), (x0, y1, z1 - bev))]
    top = [bm.verts.new(v) for v in ((x0 + bev, y0 + bev, z1), (x1 - bev, y0 + bev, z1),
                                     (x1 - bev, y1 - bev, z1), (x0 + bev, y1 - bev, z1))]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(top)
    for a, b in ((lo, mid), (mid, top)):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], b[j], b[i]))
    _tag(bm, before, mat, smooth)


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). A ring of zero
    size collapses to a point."""
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
    rings = []
    up = Vector((0, 0, 1))
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
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
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
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
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def loft_y(bm, g, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px,
    half_height_units, z_centre)."""
    sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, zmin=None):
    """An ellipsoid centred on pixel (col, row) at height z; vertices below zmin are flattened
    onto it (a dome sitting on a surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        nz = z + v.co.z * rz
        if zmin is not None:
            nz = max(nz, zmin)
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, nz))
    _tag(bm, before, mat, True)


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


def preview_arg():
    if "--preview" in sys.argv:
        return sys.argv[sys.argv.index("--preview") + 1]
    return None
