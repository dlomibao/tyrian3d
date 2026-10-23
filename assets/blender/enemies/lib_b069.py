"""Helpers shared by batch b069's enemy models (newshi.shp ground objects).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b069 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path in the XY plane; the width is measured across the path and the
    height along Z. A ring of zero size collapses to a point (a pointed or rounded end).
    Returns the new faces."""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
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
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
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
    return faces


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, half=False):
    """An ellipsoid (or, with half=True, its upper half: a dome on z) centred at (x, y, z), in units."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    verts = res["verts"]
    if half:
        for v in verts:
            v.co.z = max(v.co.z, 0.0)
    for v in verts:
        v.co = Vector((x + v.co.x * rx, y + v.co.y * ry, z + v.co.z * rz))
    if half:
        bmesh.ops.remove_doubles(bm, verts=[v for v in verts if v.is_valid], dist=1e-5)
    new = set(bm.faces) - before
    for f in new:
        f.material_index = mat
        f.smooth = True
    return new


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


def composite_png(root, layout, out, width, height):
    """The first frames of an assembly's pieces as one image, `width` x `height` px with the
    assembly origin (cx, cy = 0, 0) in its middle. Layout entries are (name, cx, cy)."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + width / 2 - 12), int(cy + height / 2 - 14)
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0 and 0 <= y0 + r < height and 0 <= x0 + c < width:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", width, height, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
