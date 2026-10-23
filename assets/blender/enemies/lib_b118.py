"""Helpers shared by the b118 model scripts (build-models.sh skips lib_ files).

Coordinates are sprite (or assembly composite) pixels: a Grid maps pixel edges and centres of a
w x h pixel image, centred on the origin, to Blender units (1 px = 1/12 unit, sprite up = +Y).
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
    """Pixel coordinates of a w x h image (centred on the origin) to Blender X/Y."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def xe(self, c):
        """Pixel-edge column (c = 0 is the left edge of column 0) to X."""
        return (c - self.w / 2) / 12

    def ye(self, r):
        """Pixel-edge row to Y (sprite up is +Y)."""
        return (self.h / 2 - r) / 12

    def xc(self, c):
        """Pixel-centre column to X."""
        return self.xe(c + 0.5)

    def yc(self, r):
        """Pixel-centre row to Y."""
        return self.ye(r + 0.5)


def ring_loft(bm, rings, mat=0, smooth=True, cap_start=True, cap_end=True):
    """Join rings of points (lists of (x, y, z), all the same length, or one point for a tip)."""
    vrings = [[bm.verts.new(p) for p in ring] for ring in rings]
    faces = []
    n = max(len(r) for r in vrings)
    for r0, r1 in zip(vrings, vrings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(f))
    if cap_start and len(vrings[0]) > 2:
        faces.append(bm.faces.new(list(reversed(vrings[0]))))
    if cap_end and len(vrings[-1]) > 2:
        faces.append(bm.faces.new(vrings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def sweep(bm, pts, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand across the
    path's direction in the XY plane (width) and along Z (height). Zero size = a pointed tip."""
    up = Vector((0, 0, 1))
    cs = [Vector(p[:3]) for p in pts]
    rings = []
    for i, (x, y, z, w, h) in enumerate(pts):
        t = cs[min(i + 1, len(cs) - 1)] - cs[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([tuple(cs[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(cs[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    return ring_loft(bm, rings, mat=mat, smooth=smooth, cap_start=cap_start, cap_end=cap_end)


def tube3(bm, p0, p1, radius, sides=10, mat=0, smooth=True, caps=True, r1=None, flat=1.0):
    """A straight tube between 3D points (any direction); `flat` squashes it along the axis' normal
    nearest to Z."""
    a, b = Vector(p0), Vector(p1)
    d = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = u.cross(d).normalized()
    rings = []
    for c, r in ((a, radius), (b, radius if r1 is None else r1)):
        if r == 0:
            rings.append([tuple(c)])
            continue
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(c + u * (r * math.cos(ang)) + v * (r * flat * math.sin(ang))))
        rings.append(ring)
    return ring_loft(bm, rings, mat=mat, smooth=smooth, cap_start=caps, cap_end=caps)


def dome(bm, x, y, z0, rx, ry, rz, mat=0, segments=12, rings=4, smooth=True, bottom=False):
    """Upper half of an ellipsoid standing on z0 (open at the bottom unless `bottom`)."""
    rr = []
    for k in range(rings):
        phi = (math.pi / 2) * k / rings
        ring = []
        for i in range(segments):
            a = 2 * math.pi * (i + 0.5) / segments
            ring.append((x + rx * math.cos(phi) * math.cos(a), y + ry * math.cos(phi) * math.sin(a),
                         z0 + rz * math.sin(phi)))
        rr.append(ring)
    rr.append([(x, y, z0 + rz)])
    return ring_loft(bm, rr, mat=mat, smooth=smooth, cap_start=bottom, cap_end=False)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, smooth=True):
    rr = [[(x, y, z - rz)]]
    for k in range(1, rings):
        phi = -math.pi / 2 + math.pi * k / rings
        ring = []
        for i in range(segments):
            a = 2 * math.pi * (i + 0.5) / segments
            ring.append((x + rx * math.cos(phi) * math.cos(a), y + ry * math.cos(phi) * math.sin(a),
                         z + rz * math.sin(phi)))
        rr.append(ring)
    rr.append([(x, y, z + rz)])
    return ring_loft(bm, rr, mat=mat, smooth=smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False, top_mat=None):
    """Extrude an XY outline (units, counter-clockwise or not) from z0 to z1."""
    n0 = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    new = bm.faces[n0:]
    for f in new:
        f.smooth = smooth
    if top_mat is not None:
        new[0].material_index = top_mat
    return new


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth flag."""
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
    """The first piece's sprite.json with every piece's colours, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def composite_png(root, entries, out, w, h, x0=0, y0=0):
    """Paint frames into one w x h image: entries are (model, frame_index, left_px, top_px)."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, fidx, left, top in entries:
        data = common.load_sprite(root, name)
        frame = next(f for f in data["frames"] if f["index"] == fidx)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                yy, xx = top + y0 + r, left + x0 + c
                if v >= 0 and 0 <= yy < h and 0 <= xx < w:
                    img[yy, xx] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def face_count(objs):
    return sum(len(o.data.polygons) for o in objs if o.type == "MESH")
