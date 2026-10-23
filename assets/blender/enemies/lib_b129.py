"""Helpers shared by batch b129's model scripts (two ground assemblies from newsh2.shp).

Not a model script itself (tools/build-models.sh skips lib_ files). Some helpers are adapted
from enemies/assembly-newsht-39.py.
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
    """Pixel grid of a w x h px object (a piece or a whole assembly) centred on the origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        """Pixel column (centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) * PX

    def Y(self, r):
        """Pixel row (centre) to Blender Y: sprite up is +Y."""
        return (self.h / 2 - (r + 0.5)) * PX


def _faces(bm, rings, closed, mat, smooth, cap_start, cap_end):
    faces = []
    n = max(len(r) for r in rings)
    segs = n if closed else n - 1
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(segs):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 2:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 2:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


# A chamfered box section for sweep(profile=...): flat top, bevelled shoulders, flat bottom.
CHAMFER = [(1.0, 0.0), (1.0, 0.5), (0.72, 1.0), (-0.72, 1.0), (-1.0, 0.5), (-1.0, 0.0)]


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, half=False,
          profile=None):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path; the width is measured across the path in the XY plane and the
    height along Z. A ring of zero size collapses to a point. With half=True only the upper half
    of each ring is built (a dome-like rail whose flat bottom sits at the path's z). `profile`
    replaces the ring with (across, up) points in -1..1 (e.g. CHAMFER), closed along its ends."""
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    if profile:
        unit = profile
    elif half:
        angles = [math.pi * k / sides for k in range(sides + 1)]
    else:
        angles = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    if not profile:
        unit = [(math.cos(a), math.sin(a)) for a in angles]
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w * PX * u) + up * (h * v)) for u, v in unit])
    return _faces(bm, rings, True, mat, smooth, cap_start, cap_end)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel-edge coordinates (col 0 is
    the left edge of pixel 0). Either winding works."""
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def poly(bm, pts, mat=0, smooth=False):
    """One face from 3D points (Blender coordinates)."""
    f = bm.faces.new([bm.verts.new(p) for p in pts])
    f.material_index = mat
    f.smooth = smooth
    return f


def mirror_all(bm, axis_x):
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


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece, so any index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, pieces, w, h, out):
    """The whole object's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects. `pieces` is [(name, left_px, top_px)] in the w x h px object."""
    import numpy as np
    pw = max(w, math.ceil(h * 24 / 28))
    ph = round(pw * 28 / 24)
    img = np.zeros((ph, pw, 4), dtype=np.float32)
    ox, oy = (pw - w) // 2, (ph - h) // 2
    for name, x0, y0 in pieces:
        data = common.load_sprite(root, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[oy + y0 + r, ox + x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", pw, ph, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out, pw / 12
