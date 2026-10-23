"""Helpers shared by batch b057's model scripts (build-models.sh skips lib_ modules).

A Grid turns sprite pixel coordinates (column, row; pixel centres, fractions allowed) of a block
W x H pixels into Blender units: sprite up is +Y, 1 px = 1/12 unit, the block's centre is the
origin. Sizes (half widths, radii) are given in pixels unless a name says units. Heights (z) are
in units.
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
    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def _mark(bm, before, mat, smooth):
    new =[f for f in bm.faces if f not in before]
    for f in new:
        f.material_index = mat
        f.smooth = smooth
    return new


def loft(bm, g, col, sections, sides=12, mat=0, smooth=True, phase=0.5, power=1.0,
         cap_start=True, cap_end=True):
    """Loft rings down the sprite (along Y) centred on column `col`. Sections are
    (row, half_w_px, half_h_units, z[, sweep_px]): sweep pulls the ring's sides back down the
    sprite by up to sweep px (0 on the centreline, full at the widest point), so a rim seen from
    above is a chevron. phase 0 puts a vertex on top (a ridge), 0.5 a flat face. power < 1 squares
    the section off. A section with zero width and height is a point."""
    before = set(bm.faces)
    rings = []
    for s in sections:
        r, w, h, z = s[:4]
        sweep = s[4] if len(s) > 4 else 0.0
        x0, y0 = g.X(col), g.Y(r)
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x0, y0, z))])
            continue
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + phase) / sides + math.pi / 2
            c, sn = math.cos(a), math.sin(a)
            u = math.copysign(abs(c) ** power, c)
            v = math.copysign(abs(sn) ** power, sn)
            ring.append(bm.verts.new((x0 + w * PX * u, y0 - sweep * PX * abs(u), z + h * v)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(f)
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    return _mark(bm, before, mat, smooth)


def sweep(bm, g, path, sides=10, mat=0, smooth=True, power=1.0, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_w_px, half_h_units). Rings stand square to the
    path in the XY plane; width is across the path, height along Z. Zero size is a point."""
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
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            cu, sv = math.cos(a), math.sin(a)
            u = math.copysign(abs(cu) ** power, cu)
            v = math.copysign(abs(sv) ** power, sv)
            ring.append(bm.verts.new(pts[i] + side * (w * PX * u) + up * (h * v)))
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
    return _mark(bm, before, mat, smooth)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, angle=0.0,
              bottom=1.0):
    """An ellipsoid centred on (col, row, z). angle turns it in the XY plane (radians, ccw).
    bottom < 1 flattens its lower half."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    ca, sa = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        x, y = v.co.x * rx_px * PX, v.co.y * ry_px * PX
        zz = v.co.z * rz * (bottom if v.co.z < 0 else 1.0)
        v.co = Vector((g.X(col) + x * ca - y * sa, g.Y(row) + x * sa + y * ca, z + zz))
    return _mark(bm, before, mat, True)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 (units) with an outline of (col, row) pixel *edges* (the corner
    at the top-left of pixel (c, r) is (c, r))."""
    before = set(bm.faces)
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    return _mark(bm, before, mat, smooth)


def mirror_about(bm, axis_x, faces=None):
    """Add a mirror image about X = axis_x (units) of `faces` (default: everything so far)."""
    if faces is None:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    else:
        verts = {v for f in faces for v in f.verts}
        edges = {e for f in faces for e in f.edges}
        geom = list(verts) + list(edges) + list(faces)
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
    """The first name's sprite.json with the colours of every named piece."""
    data = common.load_sprite(root, names[0])
    for n in names:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def composite_png(root, layout, w, out):
    """The whole assembly's sprite (first frames) as one image, padded to a square-ish 24:28 box
    of size `w` px wide (h = w * 28 / 24) with the assembly in the middle. layout entries are
    (name, cx, cy) with the assembly centre at (0, 0)."""
    import numpy as np
    bw, bh = w, int(round(w * 28 / 24))
    img = np.zeros((bh, bw, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + bw / 2 - 12), int(cy + bh / 2 - 14)
        for r, rowv in enumerate(frame["pixels"]):
            for c, v in enumerate(rowv):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", bw, bh, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def assembly_previews(root, obj, pieces, layout, size_tiles, out):
    """Preview of the whole object plus one per piece next to it."""
    import tempfile
    out = Path(out)
    ref = composite_png(root, layout, size_tiles * 12, Path(tempfile.mkdtemp()) / "assembly.png")
    common.render_preview([obj], str(out), ref, size=size_tiles, view_px=480)
    for name, piece in pieces.items():
        data = common.load_sprite(root, name)
        img = root / "reference" / "models" / name / data["frames"][0]["image"]
        common.render_preview([piece], str(out.parent / f"{name}.png"), img, size=2)
