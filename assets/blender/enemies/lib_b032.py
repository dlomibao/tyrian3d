"""Helpers shared by batch b032's model scripts (newshk: fireball, warning sign, orbs, turret).

Coordinates: sprite column c / row r (pixel centres, fractions allowed). X(c, w) and Y(r, h) map
them to Blender units for a block w x h px whose centre is the origin (24 x 28 for a 2x2 sprite;
assemblies pass their own size). Sizes given in px are converted with PX.
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


def _mark(bm, before, mat, smooth):
    for f in bm.faces[before:] if isinstance(before, int) else set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def _se(a, power):
    """Superellipse point for angle a: power 2 is an ellipse, higher is boxier."""
    c, s = math.cos(a), math.sin(a)
    e = 2 / power
    return math.copysign(abs(c) ** e, c), math.copysign(abs(s) ** e, s)


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, up_dir=(0, 0, 1),
          power=2.0, fixed_side=None):
    """A tube along a path of (x, y, z, half_width, half_height), all in units. Rings stand
    perpendicular to the path; the width is measured across the path and the height along
    `up_dir`. A ring of zero size collapses to a point (a rounded or pointed end). `power` above 2
    makes the cross-section boxier (a superellipse). With `fixed_side` (a vector) every ring spans
    that direction and `up_dir` instead of turning with the path (a loft whose centre wanders)."""
    bm.faces.ensure_lookup_table()
    before = len(bm.faces)
    pts = [Vector(p[:3]) for p in path]
    up0 = Vector(up_dir).normalized()
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(up0) if fixed_side is None else -Vector(fixed_side)
        if side.length < 1e-6:
            side = t.cross(Vector((0, 1, 0)))
        side.normalize()
        up = side.cross(t).normalized() if fixed_side is None else up0
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            cu, su = _se(2 * math.pi * (k + 0.5) / sides, power)
            ring.append(bm.verts.new(pts[i] + side * (w * cu) + up * (h * su)))
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
    bm.faces.ensure_lookup_table()
    _mark(bm, before, mat, smooth)


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, smooth=True, z_min=None):
    """An ellipsoid at `centre` (units) with radii (rx, ry, rz) in units. With z_min, vertices
    below that height are flattened onto it (a dome sitting on a surface)."""
    bm.faces.ensure_lookup_table()
    before = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
        if z_min is not None and v.co.z < z_min:
            v.co.z = z_min
    bm.faces.ensure_lookup_table()
    _mark(bm, before, mat, smooth)
    return res["verts"]


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (x, y) points in units (any winding)."""
    bm.faces.ensure_lookup_table()
    before = len(bm.faces)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    _mark(bm, before, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    """An axis-aligned box between two corners (units)."""
    plate(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def bevel_plate(bm, outline, z0, z1, inset, mat=0, top_mat=None):
    """A plate whose top edge is chamfered: the outline at z0..z1-bevel, then the top face inset by
    `inset` units at z1. Outline must be convex-ish (each point moves toward the centroid)."""
    bm.faces.ensure_lookup_table()
    before = len(bm.faces)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    zb = z1 - inset
    def shrink(p):
        d = Vector((p[0] - cx, p[1] - cy))
        return (p[0] - d.normalized().x * inset, p[1] - d.normalized().y * inset) if d.length > inset else (cx, cy)
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, zb)) for x, y in outline]
    top = [bm.verts.new((*shrink(p), z1)) for p in outline]
    n = len(outline)
    bm.faces.new(list(reversed(bot)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], top[j], top[i]))
    tf = bm.faces.new(top)
    bm.faces.ensure_lookup_table()
    _mark(bm, before, mat, False)
    if top_mat is not None:
        tf.material_index = top_mat


def mirror_x(bm, face_start, axis=0.0):
    """Add a mirror image (about x = axis) of the faces from index `face_start` on."""
    bm.faces.ensure_lookup_table()
    faces = bm.faces[face_start:]
    dup = bmesh.ops.duplicate(bm, geom=list(faces))["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])
    bm.faces.ensure_lookup_table()


def nfaces(bm):
    bm.faces.ensure_lookup_table()
    return len(bm.faces)


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
    """The first name's sprite.json with the colours of every name, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def preview(objs, root, name, sprite, frame=0, out=None):
    """If the script got `-- --preview <png>`, render objs beside the given frame's image."""
    if out is None:
        if "--preview" not in sys.argv:
            return
        out = sys.argv[sys.argv.index("--preview") + 1]
    f = sprite["frames"][frame]
    ref = Path(root) / "reference" / "models" / name / f["image"]
    common.render_preview(objs, str(out), str(ref), size=f["size"])


def composite_png(root, layout, w, h, out):
    """Several pieces' first frames as one image (w x h px, padded so h/w = 28/24 for
    render_preview). layout is (name, cx, cy) with cx, cy the piece centre in px from the image
    centre."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w / 2 - 12), int(cy + h / 2 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
