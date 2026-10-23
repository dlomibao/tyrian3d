"""Helpers shared by batch b035's model scripts (newsh8 enemies). Not a model script itself
(tools/build-models.sh skips lib_ files)."""

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
    """Sprite pixel coordinates to Blender: column c / row r (pixel centres, fractions allowed) of a
    w x h block whose centre is the origin. Sprite up is +Y."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def x(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def _new_faces(bm, before):
    bm.faces.ensure_lookup_table()
    return bm.faces[before:]


def finish(bm, before, mat, smooth):
    for f in _new_faces(bm, before):
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, pts, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, up=(0, 0, 1)):
    """A tube through `pts` = [(x, y, z, half_width, half_height)] in units. Rings stand across the
    path: the width is measured across the path in the XY plane, the height along `up`. A ring of
    zero size collapses to a point (a rounded or pointed end)."""
    before = len(bm.faces)
    pos = [Vector((x, y, z)) for x, y, z, _, _ in pts]
    upv = Vector(up)
    rings = []
    for i, (x, y, z, w, h) in enumerate(pts):
        t = pos[min(i + 1, len(pos) - 1)] - pos[max(i - 1, 0)]
        t = t - upv * t.dot(upv)
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(upv)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pos[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pos[i] + side * (w * math.cos(a)) + upv * (h * math.sin(a))))
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
    finish(bm, before, mat, smooth)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, half=False):
    """An ellipsoid (radii in units); `half` keeps only the top half (a dome on z)."""
    before = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    verts = res["verts"]
    if half:
        drop = [v for v in verts if v.co.z < -1e-4]
        bmesh.ops.delete(bm, geom=drop, context="VERTS")
        verts = [v for v in verts if v.is_valid]
        for v in verts:
            v.co.z = max(v.co.z, 0.0)
    for v in verts:
        v.co = Vector((x + v.co.x * rx, y + v.co.y * ry, z + v.co.z * rz))
    finish(bm, before, mat, True)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (x, y) in units (counter-clockwise from above)."""
    before = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2)
    finish(bm, before, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    plate(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def mirror_x(bm, start_vert=0, axis=0.0):
    """Add a mirror image (about x = axis) of the geometry made since vertex `start_vert`."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = {e for f in faces for e in f.edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def transform(bm, start_vert, fn):
    """Apply fn(Vector) -> Vector to every vertex made since `start_vert`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start_vert:]:
        v.co = fn(v.co.copy())


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


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def bevel_box(bm, x0, y0, x1, y1, z0, z1, bevel=0.02, mat=0, segments=1):
    """An axis-aligned box (units) with its edges bevelled (chamfered when segments is 1)."""
    before = len(bm.faces)
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res["verts"]
    for v in verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segments, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    finish(bm, before, mat, segments > 1)


def composite_png(root, layout, out, w_px, h_px, ox, oy):
    """Draw each piece's first frame (layout: (name, left_col, top_row) in a w_px x h_px image) into
    one PNG, for an assembly's preview."""
    import numpy as np
    img = np.zeros((h_px, w_px, 4), dtype=np.float32)
    for name, c0, r0 in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[oy + r0 + r, ox + c0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w_px, h_px, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
