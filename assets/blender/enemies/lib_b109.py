"""Helpers shared by batch b109's model scripts (ground structures from newshj.shp).

Coordinates: a Grid maps sprite pixel *edges* (column e from the left edge, row e from the top
edge, fractions allowed) of a w x h px block to Blender units, with the block's centre at the
origin, sprite up = +Y and 1 px = 1/12 unit. Pixel column c's centre is edge c + 0.5.
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

    def x(self, e):
        return (e - self.w / 2) * PX

    def y(self, e):
        return (self.h / 2 - e) * PX

    def p(self, c, r):
        return (self.x(c), self.y(r))

    def pts(self, outline):
        return [self.p(c, r) for c, r in outline]


def sym(outline, axis):
    """A closed outline from its left half: points (col, row) from the top of the axis round the
    left side to the bottom of the axis; the right half is mirrored about edge column `axis`.
    The first and last points should lie on the axis."""
    right = [(2 * axis - c, r) for c, r in reversed(outline[1:-1])]
    return list(outline) + right


def _signed_area(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def ccw(pts):
    return pts if _signed_area(pts) > 0 else list(reversed(pts))


def inset(pts, d):
    """Inset a CCW polygon by d (mitred, clamped at sharp corners)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        cos_half = max(b.dot(n0), 0.35)
        q = p1 + b * (d / cos_half)
        out.append((q.x, q.y))
    return out


def skin(bm, rings, mat=0, smooth=False, cap_start=True, cap_end=True, mats=None):
    """Join rings of equal vertex count, each a list of (x, y, z); caps are n-gons.
    `mats` optionally gives a material per band (len(rings) - 1)."""
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    faces = []
    n = len(vs[0])
    for k, (r0, r1) in enumerate(zip(vs, vs[1:])):
        m = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = m
            faces.append(f)
    if cap_start:
        f = bm.faces.new(list(reversed(vs[0])))
        f.material_index = mats[0] if mats else mat
        faces.append(f)
    if cap_end:
        f = bm.faces.new(vs[-1])
        f.material_index = mats[-1] if mats else mat
        faces.append(f)
    for f in faces:
        f.smooth = smooth
    return faces


def prism(bm, pts, z0, z1, mat=0, bevel=0.0, top_mat=None, side_mat=None, smooth=False):
    """Extrude a polygon (units) from z0 to z1, the top edge chamfered by `bevel`."""
    pts = ccw(pts)
    rings = [[(x, y, z0) for x, y in pts]]
    if bevel > 0:
        rings.append([(x, y, z1 - bevel) for x, y in pts])
        rings.append([(x, y, z1) for x, y in inset(pts, bevel)])
        band = [side_mat if side_mat is not None else mat] * 2
    else:
        rings.append([(x, y, z1) for x, y in pts])
        band = [side_mat if side_mat is not None else mat]
    faces = skin(bm, rings, mat=mat, smooth=smooth, mats=band)
    faces[-1].material_index = top_mat if top_mat is not None else mat
    faces[-2].material_index = mat
    return faces


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, bevel=0.0):
    return prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat, bevel=bevel)


def dome(bm, cx, cy, rx, ry, h, z0=0.0, sides=16, rings=5, mat=0, power=1.0, square=1.0):
    """A half ellipsoid standing on z0 (flat bottom), radii in units. `square` < 1 makes its plan
    a rounded rectangle (superellipse exponent); `power` < 1 makes its sides steeper."""
    vs = []
    for k in range(rings):
        phi = (math.pi / 2) * k / rings
        rr, zz = math.cos(phi) ** power, math.sin(phi)
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            ca = math.copysign(abs(ca) ** square, ca)
            sa = math.copysign(abs(sa) ** square, sa)
            ring.append(bm.verts.new((cx + rx * rr * ca, cy + ry * rr * sa, z0 + h * zz)))
        vs.append(ring)
    top = bm.verts.new((cx, cy, z0 + h))
    faces = []
    for r0, r1 in zip(vs, vs[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((vs[-1][i], vs[-1][j], top)))
    bottom = bm.faces.new(list(reversed(vs[0])))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    bottom.material_index = mat
    return faces


def ellipsoid(bm, cx, cy, cz, rx, ry, rz, segments=12, rings=6, mat=0):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path in XY; width is across the path, height along Z. A ring of zero
    size collapses to a point."""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
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
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
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


def mirror_since(bm, vstart, ax):
    """Mirror the geometry made of verts created since index `vstart` about X = ax (adds a copy)."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[vstart:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
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
    """The first name's sprite.json with the colours of every listed sprite."""
    data = common.load_sprite(root, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def composite_png(root, layout, w, h, out, pad_to=None):
    """The pieces' first frames composed into one image. layout: (name, x0, y0) of each piece's
    top-left pixel in a w x h canvas. pad_to = (W, H) centres it on a bigger canvas."""
    import numpy as np
    W, H = pad_to or (w, h)
    ox, oy = (W - w) // 2, (H - h) // 2
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, x0, y0 in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= oy + y0 + r < H and 0 <= ox + x0 + c < W:
                    img[oy + y0 + r, ox + x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def rock(bm, cx, cy, rx, ry, h, seed, jitter=0.18, z0=0.0, sides=9, rings=3, mat=0, tilt=(0.0, 0.0)):
    """A lumpy faceted rock: a dome on z0 whose upper vertices are pushed about by up to `jitter`
    (a fraction of the radii), seeded so it builds the same every time. `tilt` leans its top
    (dx, dy in units)."""
    import random
    rnd = random.Random(seed)
    v_start = len(bm.verts)
    faces = dome(bm, cx, cy, rx, ry, h, z0=z0, sides=sides, rings=rings, mat=mat)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[v_start:]:
        t = (v.co.z - z0) / h
        if t < 1e-4:
            s = 1 + rnd.uniform(-jitter, jitter) * 0.6
            v.co.x = cx + (v.co.x - cx) * s
            v.co.y = cy + (v.co.y - cy) * s
            continue
        v.co.x += rnd.uniform(-jitter, jitter) * rx + tilt[0] * t
        v.co.y += rnd.uniform(-jitter, jitter) * ry + tilt[1] * t
        v.co.z += rnd.uniform(-jitter, jitter) * h * 0.6
    for f in faces:
        f.smooth = False
    return faces
