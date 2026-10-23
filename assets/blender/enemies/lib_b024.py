"""Helpers for batch b024's models (the newshn.shp mouth boss). build-models.sh skips lib_ files."""

import math

import bmesh
import bpy
from mathutils import Vector


def ray_radius(poly, centre, theta):
    """Distance from `centre` to the farthest crossing of a closed polygon [(x, y), ...] along the
    ray at angle `theta` (the polygon should be star-shaped about the centre)."""
    cx, cy = centre
    dx, dy = math.cos(theta), math.sin(theta)
    best = 0.0
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        wx, wy = x0 - cx, y0 - cy
        t = (wx * ey - wy * ex) / den
        s = (wx * dy - wy * dx) / den
        if t > 0 and -1e-9 <= s <= 1 + 1e-9:
            best = max(best, t)
    return best


def mirror_poly(left, axis):
    """A closed outline from its left half (top to bottom, ending on the axis or not), mirrored
    about x = axis: returns left + mirrored right (bottom to top)."""
    right = [(2 * axis - x, y) for x, y in reversed(left)]
    return left + right


def tube(bm, pts, radii, sides=8, mat=0, flat=1.0, smooth=True):
    """A tube through 3D points with a radius per point (0 = pointed end). Rings stand across the
    path; `flat` scales the ring's height (z-ish) against its width."""
    pts = [Vector(p) for p in pts]
    up = Vector((0, 0, 1))
    rings = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nrm = side.cross(t).normalized()
        if r <= 0:
            rings.append([bm.verts.new(p)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * (r * math.cos(a)) + nrm * (r * flat * math.sin(a))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                break
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def blob(bm, centre, radii, segments=16, rings=8, mat=0, bump=None, smooth=True):
    """An ellipsoid (rx, ry, rz) at centre; bump(dx, dy, dz) -> radius scale makes it lumpy.
    Returns its faces."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    def vert(d):
        s = bump(*d) if bump else 1.0
        return bm.verts.new((cx + rx * d[0] * s, cy + ry * d[1] * s, cz + rz * d[2] * s))
    top, bottom = vert((0, 0, 1)), vert((0, 0, -1))
    ring_verts = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        ring_verts.append([vert((math.sin(phi) * math.cos(2 * math.pi * j / segments),
                                 math.sin(phi) * math.sin(2 * math.pi * j / segments), math.cos(phi)))
                           for j in range(segments)])
    faces = []
    for j in range(segments):
        k = (j + 1) % segments
        faces.append(bm.faces.new((top, ring_verts[0][j], ring_verts[0][k])))
        faces.append(bm.faces.new((bottom, ring_verts[-1][k], ring_verts[-1][j])))
    for a, b in zip(ring_verts, ring_verts[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append(bm.faces.new((a[j], b[j], b[k], a[k])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


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
