"""Helpers shared by batch b095's models (ground turrets, a spinner, the brown machine body):
sprite pixel coordinates, tubes swept along paths, ellipsoids, plates with pixel-edge outlines,
mirroring, and the whole-assembly preview.

build-models.sh skips lib_ files; the model scripts import this next to them.
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
    """Pixel coordinates of a w x h px block whose centre is the Blender origin. Columns and rows
    count from the top-left; `c`/`r` are pixel centres (fractions allowed), edge coordinates are
    `c + 0.5`."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def x(self, c):
        """Pixel column (centre) to Blender X."""
        return (c + 0.5 - self.w / 2) / 12

    def y(self, r):
        """Pixel row (centre) to Blender Y: sprite up is +Y."""
        return (self.h / 2 - (r + 0.5)) / 12

    def xe(self, e):
        """Pixel edge column to Blender X."""
        return (e - self.w / 2) / 12

    def ye(self, e):
        """Pixel edge row to Blender Y."""
        return (self.h / 2 - e) / 12


def _faces_since(bm, before):
    return [f for f in bm.faces if f not in before]


def _finish(faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in grid `g`'s pixel
    centres. Rings stand perpendicular to the path in the XY plane; the width is measured across
    the path and the height along Z. A ring of zero size collapses to a point (a rounded end)."""
    pts = [Vector((g.x(c), g.y(r), z)) for c, r, z, _, _ in path]
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
    _finish(faces, mat, smooth)
    return faces


def half_sweep(bm, g, path, sides=8, mat=0, smooth=True):
    """Like sweep, but only the upper half of each ring (a half-round moulding lying on z), closed
    underneath by a flat strip. Path entries are (col, row, z_base, half_width_px, height)."""
    pts = [Vector((g.x(c), g.y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        ring = []
        for k in range(sides + 1):
            a = math.pi * k / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            faces.append(bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k])))
        faces.append(bm.faces.new((r0[sides], r0[0], r1[0], r1[sides])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    _finish(faces, mat, smooth)
    return faces


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid centred on pixel (col, row) at height z. With z_min, vertices below it are
    flattened onto it (a dome sitting on a surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.x(col) + v.co.x * rx_px * PX, g.y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
        if z_min is not None and v.co.z < z_min:
            v.co.z = z_min
    faces = _faces_since(bm, before)
    _finish(faces, mat, True)
    return faces


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of pixel-edge (col, row) points, in either
    winding."""
    pts = [(g.xe(c), g.ye(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    before = set(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    faces = _faces_since(bm, before)
    _finish(faces, mat, smooth)
    return faces


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    """An axis-aligned block between pixel edges c0..c1, r0..r1."""
    return plate(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def wedge_plate(bm, g, outline, z0, mat=0):
    """A prism from z0 up to a top whose height varies per outline point: outline is a list of
    pixel-edge (col, row, z_top). The top is triangulated (it need not be flat)."""
    pts = [(g.xe(c), g.ye(r), zt) for c, r, zt in outline]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    before = set(bm.faces)
    top = [bm.verts.new((x, y, zt)) for x, y, zt in pts]
    bottom = [bm.verts.new((x, y, z0)) for x, y, _ in pts]
    tf = bm.faces.new(top)
    bm.faces.new(list(reversed(bottom)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    bmesh.ops.triangulate(bm, faces=[tf], quad_method="BEAUTY", ngon_method="BEAUTY")
    faces = _faces_since(bm, before)
    _finish(faces, mat, False)
    return faces


def mirror_since(bm, start_vert, axis_x):
    """Add a mirror image (about Blender x = axis_x) of every face whose vertices were all added
    since vertex index `start_vert`."""
    bm.verts.ensure_lookup_table()
    new = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in new for v in f.verts)]
    dup = bmesh.ops.duplicate(bm, geom=faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def rotate_since(bm, start_vert, angle, cx=0.0, cy=0.0):
    """Turn every vertex added since `start_vert` about the Z axis through (cx, cy)."""
    bm.verts.ensure_lookup_table()
    ca, sa = math.cos(angle), math.sin(angle)
    for v in bm.verts[start_vert:]:
        x, y = v.co.x - cx, v.co.y - cy
        v.co.x, v.co.y = cx + x * ca - y * sa, cy + x * sa + y * ca


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
        return sys.argv[sys.argv.index("--preview") + 1]
    return None


def preview(root, name, objs, sprite, frame=0, out=None):
    """Render the usual preview of `objs` beside frame `frame` of the sprite."""
    out = out or preview_arg()
    if not out:
        return
    f = sprite["frames"][frame]
    ref = Path(root) / "reference" / "models" / name / f["image"]
    common.render_preview(objs, str(out), str(ref), size=f["size"])


def subset(sprite, frames):
    """The sprite's `sprites` list cut down to the given frame indices."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def composite_png(root, pieces, w, h, ox, oy, out):
    """The first frames of several 2x2 pieces as one w x h px image: pieces are
    (name, left_col, top_row) in that image."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, x0, y0 in pieces:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + oy + r < h and 0 <= x0 + ox + c < w:
                    img[y0 + oy + r, x0 + ox + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
