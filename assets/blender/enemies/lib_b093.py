"""Helpers shared by batch b093's model scripts (build-models.sh skips lib_ modules).

Coordinates are sprite pixel *edges* of the whole assembly: column c runs from c to c + 1 and row r
from r to r + 1, so a pixel's centre is (c + 0.5, r + 0.5). X(c) and Y(r) turn them into Blender
units (sprite up is +Y, 1 px = 1/12 unit) about an origin (OX, OY) in the same pixel-edge
coordinates. Heights (z) are in Blender units, with the ground at z = 0.
"""

import math

import bmesh
import bpy

PX = 1 / 12  # one sprite pixel in units


class Frame:
    """Pixel-edge coordinates of a W x H block whose centre is the Blender origin."""

    def __init__(self, w, h):
        self.ox, self.oy = w / 2, h / 2

    def X(self, c):
        return (c - self.ox) * PX

    def Y(self, r):
        return (self.oy - r) * PX


def _ring_point(a, power):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)


def stack(bm, F, rings, top_mat=0, side_mat=0, bottom=True, smooth=False):
    """A solid through rings of the same vertex count, bottom to top. Each ring is (points, z) with
    points a list of (col, row) pixel edges. side_mat is a material index or a function
    (ring_segment, edge_index) -> index, edge i running from point i to point i + 1."""
    loops = [[bm.verts.new((F.X(c), F.Y(r), z)) for c, r in pts] for pts, z in rings]
    faces = []
    n = len(loops[0])
    for k, (l0, l1) in enumerate(zip(loops, loops[1:])):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((l0[i], l0[j], l1[j], l1[i]))
            f.material_index = side_mat(k, i) if callable(side_mat) else side_mat
            faces.append(f)
    top = bm.faces.new(loops[-1])
    top.material_index = top_mat
    faces.append(top)
    if bottom:
        b = bm.faces.new(list(reversed(loops[0])))
        b.material_index = side_mat(0, 0) if callable(side_mat) else side_mat
        faces.append(b)
    for f in faces:
        f.smooth = smooth
    return faces


def prism(bm, F, pts, z0, z1, mat=0, side_mat=None, bottom=True):
    """Extrude an outline of (col, row) pixel edges from z0 to z1."""
    return stack(bm, F, [(pts, z0), (pts, z1)], top_mat=mat,
                 side_mat=mat if side_mat is None else side_mat, bottom=bottom)


def box(bm, F, c0, r0, c1, r1, z0, z1, mat=0, side_mat=None):
    return prism(bm, F, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat, side_mat)


def sweep(bm, F, path, sides=8, mat=0, smooth=True, power=1.0, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand square to
    the path in the XY plane: the width runs across the path, the height along Z. A ring of zero
    size is a point (a rounded or pointed end). power < 1 squares the section off."""
    pos = [(F.X(c), F.Y(r)) for c, r, *_ in path]
    rings = []
    for i, (c, r, z, hw, hh) in enumerate(path):
        x, y = pos[i]
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, z))])
            continue
        (x0, y0), (x1, y1) = pos[max(i - 1, 0)], pos[min(i + 1, len(pos) - 1)]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        ring = []
        for k in range(sides):
            u, v = _ring_point(2 * math.pi * (k + 0.5) / sides, power)
            ring.append(bm.verts.new((x + nx * hw * PX * u, y + ny * hw * PX * u, z + hh * v)))
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
    return faces


def ellipsoid(bm, F, c, r, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, upper=False):
    """An ellipsoid centred on (col, row) pixel edges at height z. upper keeps only the top half
    (closed by a flat base at z)."""
    x0, y0 = F.X(c), F.Y(r)
    lo = 0 if upper else -rings // 2
    hi = rings // 2
    loops = []
    for k in range(lo, hi):
        t = (math.pi / 2) * k / (rings // 2)
        loops.append([bm.verts.new((x0 + rx_px * PX * math.cos(t) * math.cos(a),
                                    y0 + ry_px * PX * math.cos(t) * math.sin(a), z + rz * math.sin(t)))
                      for a in (2 * math.pi * i / segments for i in range(segments))])
    tip = bm.verts.new((x0, y0, z + rz))
    faces = []
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append(bm.faces.new((l0[i], l0[j], l1[j], l1[i])))
    for i in range(segments):
        faces.append(bm.faces.new((loops[-1][i], loops[-1][(i + 1) % segments], tip)))
    if upper:
        faces.append(bm.faces.new(list(reversed(loops[0]))))
    else:
        bot = bm.verts.new((x0, y0, z - rz))
        for i in range(segments):
            faces.append(bm.faces.new((loops[0][(i + 1) % segments], loops[0][i], bot)))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def mirror_since(bm, vert_start, axis_x):
    """Mirror every vertex added since index vert_start about X = axis_x (faces keep their
    winding; normals are recalculated when the object is made)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[vert_start:]:
        v.co.x = 2 * axis_x - v.co.x


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


def merged_sprite(common, root, names):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(common, root, layout, w, h, out):
    """The assembly's sprite (first frames of the pieces in `layout`, given as (name, cx, cy) with
    (0, 0) the assembly's centre) as one image, padded to the 24:28 shape render_preview expects
    for a size of w / 24 tiles."""
    import numpy as np
    ih = w * 28 // 24
    img = np.zeros((ih, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w / 2 - 12), int(cy + ih / 2 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < ih and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, ih, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
