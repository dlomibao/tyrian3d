"""Helpers shared by batch b012's model scripts (the newsh^ U-shaped assembly).

Geometry is placed in sprite pixel coordinates through a Grid: column c / row r (pixel centres,
fractions allowed) of a w x h px block whose centre is the Blender origin. Sprite up is +Y and one
sprite pixel is 1/12 unit. Adapted from assembly-newsht-39.py (sweep, ellipsoid, mirror).
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
    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; the width is across the path, the height along Z.
    A ring of zero size collapses to a point (a rounded or pointed end)."""
    before = set(bm.faces)
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
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
        rings.append([bm.verts.new(pts[i] + side * (w * PX * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + up * (h * math.sin(2 * math.pi * (k + 0.5) / sides)))
                      for k in range(sides)])
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
    _tag(bm, before, mat, smooth)


def loft_y(bm, g, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px, half_height, z)."""
    sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (the top-left corner
    of pixel (c, r) is (c, r)), counter-clockwise seen from above or not, normals get fixed."""
    before = set(bm.faces)
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, before, mat, smooth)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=14, rings=7):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _tag(bm, before, mat, True)


def mirror_all(bm, axis_x):
    """Add a mirror image about the vertical line X = axis_x of everything built so far."""
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


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w, h):
    """The whole assembly's sprite (first frames) as one image of w x h px (w:h must be 24:28 for
    render_preview), each piece placed by its centre (cx, cy) relative to the image centre."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w // 2 - 12), int(cy + h // 2 - 14)
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
