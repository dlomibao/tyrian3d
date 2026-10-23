"""Helpers shared by batch b084's model scripts (newsha.shp ground objects)."""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def ellipsoid(bm, centre, radii, normal=(0, 0, 1), segments=16, rings=8, mat=0, smooth=True):
    """An ellipsoid at `centre` (units) with radii (rx, ry, rz), its Z axis turned to `normal`
    (so a flattened one can lie on a sloped surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    rot = Vector((0, 0, 1)).rotation_difference(Vector(normal).normalized())
    for v in res["verts"]:
        p = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
        v.co = rot @ p + Vector(centre)
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def tube(bm, points, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube through 3D points: each point is (x, y, z, half_width, half_height) in units. Rings
    stand across the path (width in the XY plane, height along Z); a zero ring is a point."""
    pts = [Vector(p[:3]) for p in points]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(points):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a)))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
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


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat block from z0 to z1 with an XY outline (units, counter-clockwise from above)."""
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


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


def composite_png(root, pieces, out, width, height, frame_of=None):
    """Several pieces' sprites as one image: `pieces` is [(name, left, top)] with each 24x28
    sprite's top-left corner in the width x height image; frame_of[name] picks a frame (default
    the first)."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, left, top in pieces:
        data = common.load_sprite(root, name)
        frame = data["frames"][(frame_of or {}).get(name, 0)]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= top + r < height and 0 <= left + c < width:
                    img[top + r, left + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", width, height, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
