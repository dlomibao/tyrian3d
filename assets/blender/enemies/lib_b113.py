"""Helpers shared by batch b113's scripts (round mines and balls of newsha.shp)."""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


def frame_of(direction):
    """Two unit vectors perpendicular to `direction` (the second one as close to +Z as possible,
    or +Y for a vertical direction), for building rings around an axis."""
    d = Vector(direction).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
    u = d.cross(ref).normalized()
    v = u.cross(d).normalized()
    return d, u, v


def tube(bm, origin, direction, sections, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A loft along any direction from `origin` (units). Sections are (distance, half_width,
    half_height) in units; width is across the axis in the frame's u, height along v (towards +Z
    for a horizontal axis). A section of zero size collapses to a point (a spike tip)."""
    d, u, v = frame_of(direction)
    o = Vector(origin)
    rings = []
    for dist, w, h in sections:
        c = o + d * dist
        if w == 0 and h == 0:
            rings.append([bm.verts.new(c)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(c + u * (w * math.cos(a)) + v * (h * math.sin(a))))
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


def ellipsoid(bm, centre, rx, ry, rz, mat=0, segments=24, rings=12, smooth=True):
    """An ellipsoid at `centre` (units) with radii in units."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    for vert in res["verts"]:
        vert.co = Vector((cx + vert.co.x * rx, cy + vert.co.y * ry, cz + vert.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
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


def merged_sprite(root, first, pieces):
    """`first`'s sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, first)
    for name in pieces:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, size):
    """The whole assembly's sprite (first frames) as one image of size*12 x size*14 px with the
    assembly centre (layout offsets 0, 0) in the middle, as render_preview(size=size) expects."""
    import numpy as np
    w, h = size * 12, size * 14
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx) + w // 2 - 12, int(cy) + h // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
