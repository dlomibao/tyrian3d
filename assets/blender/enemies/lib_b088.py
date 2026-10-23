"""Helpers for batch b088's scripts (not a model: tools/build-models.sh skips lib_ files).

Geometry is given in assembly pixel coordinates: (col, row) of pixel *edges* (fractions allowed),
with the conversion to Blender units set up by `Grid`. Adapted from assembly-newsht-39.py.
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
    """Pixel-edge coordinates (col, row) -> Blender (x, y): col `c0`, row `r0` is the origin."""

    def __init__(self, c0, r0):
        self.c0, self.r0 = c0, r0

    def x(self, c):
        return (c - self.c0) / 12

    def y(self, r):
        return (self.r0 - r) / 12

    def xy(self, c, r):
        return Vector((self.x(c), self.y(r), 0.0))


def _closest_on_polyline(p, pts):
    if len(pts) == 1:
        return pts[0].copy()
    best, best_d = None, None
    for a, b in zip(pts, pts[1:]):
        ab = b - a
        t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        q = a + ab * t
        d = (p - q).length_squared
        if best_d is None or d < best_d:
            best, best_d = q, d
    return best


def pillow(bm, grid, outline, spine, h_edge, h_peak, z0=0.0, mat=0, wall_mat=None,
           rings=(1.0, 0.9, 0.75, 0.55, 0.35, 0.15), profile=None):
    """A rounded plate or dome: the outline (pixel-edge (col, row) points) stands as a wall from z0
    to z0 + h_edge, and the top rises to z0 + h_peak along the spine (one point for a dome, a
    polyline for a long blade). Each outline point moves toward its nearest spine point in rings
    (scale factors `rings`, 1 = outline); the height follows a quarter circle by default."""
    pts = [grid.xy(c, r) for c, r in outline]
    # counter-clockwise from above
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    sp = [grid.xy(c, r) for c, r in spine]
    targets = [_closest_on_polyline(p, sp) for p in pts]
    prof = profile or (lambda s: math.sqrt(max(0.0, 1 - s * s)))
    n = len(pts)
    bottom = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    layers = []
    for s in rings:
        z = z0 + h_edge + (h_peak - h_edge) * prof(s)
        layers.append([bm.verts.new((t.x + (p.x - t.x) * s, t.y + (p.y - t.y) * s, z)) for p, t in zip(pts, targets)])
    faces_flat, faces_smooth = [], []
    faces_flat.append(bm.faces.new(list(reversed(bottom))))
    for i in range(n):
        j = (i + 1) % n
        faces_flat.append(bm.faces.new((bottom[i], bottom[j], layers[0][j], layers[0][i])))
    for l0, l1 in zip(layers, layers[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces_smooth.append(bm.faces.new((l0[i], l0[j], l1[j], l1[i])))
    faces_smooth.append(bm.faces.new(layers[-1]))
    for f in faces_flat:
        f.material_index = mat if wall_mat is None else wall_mat
        f.smooth = False
    faces_flat[0].material_index = mat
    for f in faces_smooth:
        f.material_index = mat
        f.smooth = True


def sweep(bm, grid, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units); rings stand across
    the path in XY, the height is along Z. A ring of zero size is a point (a pointed end)."""
    pts = [Vector((grid.x(c), grid.y(r), z)) for c, r, z, _, _ in path]
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


def mirror_all(bm, axis_x):
    """Add a mirror image, about x = axis_x, of everything built so far."""
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


def merged_sprite(root, first, pieces):
    """`first`'s sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, first)
    for name in pieces:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, width, height, cx0, cy0):
    """The whole object's sprite (first frames) as one image of width x height px; `layout` is
    (name, cx, cy) relative to the image centre (cx0, cy0 already subtracted)."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + width // 2 - 12), int(cy + height // 2 - 14)
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
