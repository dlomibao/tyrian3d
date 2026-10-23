"""Helpers shared by batch b038's model scripts (the newsh^ boss assembly).

All coordinates are pixel EDGES of a sprite (or assembly) grid: column c spans c..c+1, so the
centre of pixel column c is c + 0.5. A Grid maps them to Blender units (1 px = 1/12 unit, sprite up
is +Y), with its origin at edge (x0, y0).
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
    def __init__(self, x0, y0):
        self.x0, self.y0 = x0, y0

    def X(self, c):
        return (c - self.x0) / 12

    def Y(self, r):
        return (self.y0 - r) / 12


def _faces_since(bm, before):
    return [f for f in bm.faces if f not in before]


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, angle=0.0):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; width is across the path, height along Z. A ring of
    zero size collapses to a point (a rounded or pointed end). `angle` turns the ring's vertices
    (sides=4 with angle=0.5 gives a box-like section)."""
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
            a = 2 * math.pi * (k + 0.5 + angle) / sides
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


def box(bm, g, path, sides=8, mat=0, smooth=False, **kw):
    """A sweep with a chamfered-box section (8 sides turned so the flats face up and sideways)."""
    sweep(bm, g, path, sides=sides, mat=mat, smooth=smooth, angle=-0.5 if sides % 4 == 0 else 0.0, **kw)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False, bevel=0.0):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (any winding). `bevel`
    (units) chamfers its top edges."""
    pts = [(g.X(c), g.Y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    before = set(bm.faces)
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    tf = bm.faces.new(top)
    bm.faces.new(list(reversed(bottom)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(tf.edges), offset=bevel, segments=1, affect="EDGES",
                        clamp_overlap=True)
    for f in _faces_since(bm, before):
        f.material_index = mat
        f.smooth = smooth


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    """An ellipsoid centred on pixel edge (col, row) at height z."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in _faces_since(bm, before):
        f.material_index = mat
        f.smooth = True


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


def composite_png(root, layout, out, width, height, ox, oy):
    """The whole assembly's sprite (each piece's first frame) as one image of width x height px.
    `layout` is (model, cx, cy) in screen pixels; screen pixel (ox, oy) lands at the image's top
    left."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = cx - 12 - ox, cy - 14 - oy
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
