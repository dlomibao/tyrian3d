"""Helpers shared by batch b015's model scripts (the newsh4 boss, assembly-newsh4-124).

Coordinates are assembly pixels: column c (0-119) and row r (0-111) of the whole 120 x 112 px
object, whose centre (the edge between columns 59/60 and rows 55/56) is the Blender origin.
X(c) / Y(r) give a pixel's centre; fractions are allowed, so X(c - 0.5) is its left edge.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

W, H = 120, 112  # assembly size in pixels
PX = 1 / 12  # one sprite pixel in units


def X(c):
    return (c + 0.5 - W / 2) / 12


def Y(r):
    return (H / 2 - (r + 0.5)) / 12


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; the width is measured across the path and the
    height along Z. A ring of zero size collapses to a point (a pointed or rounded end)."""
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


def loft_y(bm, col, sections, sides=12, mat=0, smooth=True):
    """A loft down the sprite (along -Y) centred on column `col`: sections are
    (row, half_width_px, half_height_units, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False, tilt=None):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (any winding).
    `tilt(col, row)` optionally adds a z offset per outline point (to slope the plate)."""
    pts = [(X(c - 0.5), Y(r - 0.5), tilt(c, r) if tilt else 0.0) for c, r in outline]
    top = [bm.verts.new((x, y, z1 + dz)) for x, y, dz in pts]
    bot = [bm.verts.new((x, y, z0 + dz)) for x, y, dz in pts]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def box(bm, c0, r0, c1, r1, z0, z1, mat=0):
    """An axis-aligned box over pixel columns c0..c1 and rows r0..r1 (inclusive pixel ranges)."""
    plate(bm, [(c0, r0), (c1 + 1, r0), (c1 + 1, r1 + 1), (c0, r1 + 1)], z0, z1, mat=mat)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, top_only=False):
    """An ellipsoid (or, with top_only, its upper half: a dome) centred on pixel (col, row)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        zz = max(v.co.z, 0.0) if top_only else v.co.z
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + zz * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True
    if top_only:
        bmesh.ops.remove_doubles(bm, verts=res["verts"], dist=1e-5)


def mirror_all(bm, axis_col):
    """Add a mirror image, about the centre of pixel column `axis_col`, of everything built so far."""
    ax = X(axis_col)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
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


def merged_sprite(root, pieces):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, pieces[0])
    for name in pieces[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, width, height, frames=None):
    """The whole object's sprite as one image (`layout` entries are (model, cx, cy) relative to
    the assembly centre, `frames` optionally {model: frame index}), centred on a width x height
    canvas (which must have the 12:14 shape render_preview expects)."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        if frames and name in frames:
            frame = next(f for f in data["frames"] if f["index"] == frames[name])
        x0, y0 = cx + width // 2 - 12, cy + height // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", width, height, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
