"""Helpers shared by the b075 model scripts (build-models.sh skips lib_ files).

Coordinates: sprite column c / row r (pixel centres, fractions allowed) map to Blender X / Y with
the block's centre at the origin; one sprite pixel is 1/12 unit. Edge variants take pixel edges
(column c's left edge is c, its right edge c + 1).
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


def X(c, w=24):
    """Sprite column (pixel centre) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def Y(r, h=28):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def XE(c, w=24):
    """Sprite pixel edge (column index of the left edge) to Blender X."""
    return (c - w / 2) / 12


def YE(r, h=28):
    """Sprite pixel edge (row index of the top edge) to Blender Y."""
    return (h / 2 - r) / 12


def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude a polygon of Blender (x, y) points from z0 to z1."""
    before = set(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _tag(bm, before, mat, smooth)


def box(bm, c0, r0, c1, r1, z0, z1, mat=0, w=24, h=28):
    """A box over sprite pixel edges: columns c0..c1, rows r0..r1 (edges), z0..z1."""
    prism(bm, [(XE(c0, w), YE(r1, h)), (XE(c1, w), YE(r1, h)), (XE(c1, w), YE(r0, h)), (XE(c0, w), YE(r0, h))],
          z0, z1, mat=mat)


def bevel_box(bm, x0, y0, x1, y1, z0, z1, bevel, mat=0, smooth=False):
    """A box in Blender units with its top edges chamfered by `bevel`."""
    before = set(bm.faces)
    b = bevel
    lo = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    hi = [(x0 + b, y0 + b), (x1 - b, y0 + b), (x1 - b, y1 - b), (x0 + b, y1 - b)]
    vb = [bm.verts.new((x, y, z0)) for x, y in lo]
    vm = [bm.verts.new((x, y, z1 - b)) for x, y in lo]
    vt = [bm.verts.new((x, y, z1)) for x, y in hi]
    bm.faces.new(list(reversed(vb)))
    bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vb[i], vb[j], vm[j], vm[i]))
        bm.faces.new((vm[i], vm[j], vt[j], vt[i]))
    _tag(bm, before, mat, smooth)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=16, rings=8, smooth=True, zmin=None):
    """An ellipsoid in Blender units centred at (x, y, z). With zmin, vertices below zmin are
    flattened onto it (a dome sitting on a surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        co = Vector((x + v.co.x * rx, y + v.co.y * ry, z + v.co.z * rz))
        if zmin is not None and co.z < zmin:
            co.z = zmin
        v.co = co
    _tag(bm, before, mat, smooth)


def cylinder(bm, x, y, z0, z1, rx, ry=None, sides=16, mat=0, smooth=True, cap_mat=None, top=True, bottom=True):
    """A vertical (Z) cylinder with an elliptical section, from z0 to z1."""
    ry = rx if ry is None else ry
    before = set(bm.faces)
    lo, hi = [], []
    for i in range(sides):
        a = 2 * math.pi * (i + 0.5) / sides
        lo.append(bm.verts.new((x + rx * math.cos(a), y + ry * math.sin(a), z0)))
        hi.append(bm.verts.new((x + rx * math.cos(a), y + ry * math.sin(a), z1)))
    side = []
    for i in range(sides):
        j = (i + 1) % sides
        side.append(bm.faces.new((lo[i], lo[j], hi[j], hi[i])))
    caps = []
    if top:
        caps.append(bm.faces.new(hi))
    if bottom:
        caps.append(bm.faces.new(list(reversed(lo))))
    _tag(bm, before, mat, smooth)
    for f in caps:
        f.smooth = False
        if cap_mat is not None:
            f.material_index = cap_mat


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of Blender points (x, y, z, half_width, half_height). Rings stand
    perpendicular to the path in the XY plane; height is along Z. A ring of zero size is a point."""
    before = set(bm.faces)
    pts = [Vector((p[0], p[1], p[2])) for p in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, hh) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and hh == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (hh * math.sin(a))))
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
    _tag(bm, before, mat, smooth)


def mirror_x(bm, start_vert, axis=0.0):
    """Duplicate every vertex (and its faces) added since `start_vert`, mirrored about x = axis."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start_vert:]
    faces = {f for v in verts for f in v.link_faces}
    edges = {e for v in verts for e in v.link_edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + list(faces))["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
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


def frames_subset(sprite, frames):
    """sprite["sprites"] keeping only the given frame numbers."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def frame_image(root, sprite, frame_no):
    """The reference image of a sprite frame number (e.g. 169 -> frame-newshd-169.png)."""
    for f in sprite["frames"]:
        if f["image"].endswith(f"-{frame_no}.png"):
            return root / "reference" / "models" / sprite["name"] / f["image"]
    return root / "reference" / "models" / sprite["name"] / sprite["frames"][0]["image"]
