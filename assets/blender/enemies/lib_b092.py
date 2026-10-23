"""Helpers for batch b092 (the grey walker base of level 3.12, assembly-newsho-156).

Shapes are given in screen pixel-edge coordinates of an assembly: (x, y) with x to the right and
y down the screen, converted by an `Space` with the assembly's origin. Not a model script
(build-models.sh skips lib_ files).
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


class Space:
    """Screen pixel edges (x, y) to Blender XY, with (x0, y0) as the origin."""

    def __init__(self, x0, y0):
        self.x0, self.y0 = x0, y0

    def __call__(self, x, y):
        return ((x - self.x0) / 12, -(y - self.y0) / 12)


def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` (along its corner's bisector).
    (Copied from lib_b003.)"""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length * sign, ex_ / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def ccw(outline):
    """The outline counter-clockwise (seen from +Z)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    return list(outline) if area > 0 else list(reversed(outline))


def rounded_prism(bm, outline, z0, z1, r=0.0, steps=2, mat=0, top_mat=None, smooth_edge=True, bottom=True):
    """A prism (outline in Blender XY) from z0 to z1 whose top edge is rounded with radius `r`
    in `steps` segments. The walls and rounded band take `mat`, the flat top `top_mat`."""
    outline = ccw(outline)
    top_mat = mat if top_mat is None else top_mat
    r = min(r, (z1 - z0) * 0.95)
    rings = [[bm.verts.new((x, y, z0)) for x, y in outline]]
    if r > 0:
        for k in range(steps + 1):
            a = math.pi / 2 * k / steps
            ins = r * (1 - math.cos(a))
            z = z1 - r + r * math.sin(a)
            pts = inset_outline(outline, ins) if ins > 1e-6 else outline
            rings.append([bm.verts.new((x, y, z)) for x, y in pts])
    else:
        rings.append([bm.verts.new((x, y, z1)) for x, y in outline])
    n = len(outline)
    if bottom:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
    f = bm.faces.new(rings[-1])
    f.material_index = top_mat
    for ri, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mat
            f.smooth = smooth_edge and ri > 0


def circle(cx, cy, rx, ry=None, n=16):
    ry = rx if ry is None else ry
    return [(cx + rx * math.cos(2 * math.pi * (i + 0.5) / n), cy + ry * math.sin(2 * math.pi * (i + 0.5) / n))
            for i in range(n)]


def tube(bm, points, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube through points (x, y, z, radius) in Blender units; rings stand perpendicular to the
    path. A radius of 0 makes a point."""
    pts = [Vector(p[:3]) for p in points]
    rings = []
    for i, p in enumerate(points):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized()
        v = u.cross(t).normalized()
        rad = p[3]
        if rad == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + u * (rad * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + v * (rad * math.sin(2 * math.pi * (k + 0.5) / sides))) for k in range(sides)])
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


def mirror_from(bm, start_vert, axis_x):
    """Add a mirror image (about X = axis_x) of everything built since vertex index `start_vert`."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = [e for e in bm.edges if all(v in verts for v in e.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
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
    """The first sprite.json with the colours of all of them merged, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, width, height):
    """The pieces' first frames as one image of width x height sprite px, with the layout's (0, 0)
    (piece centres relative to the assembly origin) in the middle."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + width / 2 - 12), int(cy + height / 2 - 14)
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
