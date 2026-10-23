"""Helpers shared by batch b047's model scripts (the newshi.shp red bomber and its nose).

Geometry helpers take a coordinate mapping `G` (an object with X(col) and Y(row) giving a
pixel centre in Blender units; fractions allowed) so the same code serves a single 24x28 sprite
and a whole assembly. Sizes across the sprite are in pixels, heights (z) in units.
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


class Grid:
    """Pixel (col, row) centres to Blender X/Y, with the axis (X = 0) at column `axis` and
    Y = 0 at row edge `mid` (the block's vertical centre)."""

    def __init__(self, axis, mid):
        self.axis, self.mid = axis, mid

    def X(self, c):
        return (c - self.axis) * PX

    def Y(self, r):
        return (self.mid - (r + 0.5)) * PX


def _finish(bm, before, mat, smooth):
    for f in bm.faces:
        if f not in before:
            f.material_index = mat
            f.smooth = smooth


def sweep(bm, G, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; a ring of zero size collapses to a point."""
    before = set(bm.faces)
    pts = [Vector((G.X(c), G.Y(r), z)) for c, r, z, _, _ in path]
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
            bm.faces.new(f)
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _finish(bm, before, mat, smooth)


def loft_y(bm, G, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px,
    half_height_units, z)."""
    sweep(bm, G, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, G, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 whose outline is (col, row) points (pixel centres; use
    .5 fractions for pixel edges)."""
    before = set(bm.faces)
    common.slab(bm, [(G.X(c), G.Y(r)) for c, r in outline], z1 - z0, z=(z0 + z1) / 2)
    _finish(bm, before, mat, smooth)


def rect(bm, G, c0, r0, c1, r1, z0, z1, mat=0):
    """A box over columns c0..c1 and rows r0..r1 (pixel-edge coordinates, e.g. 9.5..10.5)."""
    plate(bm, G, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def ellipsoid(bm, G, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((G.X(col) + v.co.x * rx_px * PX, G.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _finish(bm, before, mat, True)


def vfin(bm, G, col, profile, thickness_px, mat=0):
    """A thin upright fin in the plane of column `col`: profile is (row, z) points."""
    before = set(bm.faces)
    t = thickness_px * PX / 2
    x = G.X(col)
    left = [bm.verts.new((x - t, G.Y(r), z)) for r, z in profile]
    right = [bm.verts.new((x + t, G.Y(r), z)) for r, z in profile]
    bm.faces.new(left)
    bm.faces.new(list(reversed(right)))
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[j], left[i], right[i], right[j]))
    _finish(bm, before, mat, False)


def mirror_all(bm, axis_x=0.0):
    """Add a mirror image (about X = axis_x) of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
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


def merged_sprite(root, first, names):
    """`first`'s sprite.json with the colours of every named piece, so any piece's index is valid."""
    data = common.load_sprite(root, first)
    for name in names:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, cx0, cy0, width, height):
    """The pieces' first frames as one image `width` x `height` px whose centre is screen
    (cx0, cy0); layout is (model_name, cx, cy) in screen px."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0 = cx - cx0 + width // 2 - 12
        y0 = cy - cy0 + height // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < height and 0 <= x0 + c < width:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", width, height, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
