"""Helpers shared by batch b030's model scripts (the newsh5 brain, its spawn and a few fliers).

Coordinates: sprite column c / row r (fractions allowed) of a w x h pixel block whose centre is
the origin. px/row give a pixel's centre, ex/ey a pixel edge (the left or top edge of column c /
row r). One sprite pixel is 1/12 unit; sprite up is +Y, out of the screen is +Z.
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


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def tag_faces(bm, before, mat, smooth):
    """Set material and smooth flag on the faces added since `before` (a face count)."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[before:]:
        f.material_index = mat
        f.smooth = smooth


def ring_loft(bm, rings, mat=0, smooth=True, cap_start=True, cap_end=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order."""
    before = len(bm.faces)
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        if n == 1:
            continue
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face)
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0])))
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1])
    tag_faces(bm, before, mat, smooth)
    return verts


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of 3D points (x, y, z, half_width, half_height), all in units. Rings
    stand perpendicular to the path's direction in the XY plane: the width is measured across the
    path in XY and the height along Z. A ring of zero size collapses to a point (a rounded end)."""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([tuple(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    return ring_loft(bm, rings, mat, smooth, cap_start, cap_end)


def sausage(bm, pts, w, h, sides=8, mat=0, z_of=None, lift=0.0):
    """A rounded tube through 2D points [(x, y), ...] in units with half width w and half height h
    (numbers or one per point), tapering to rounded ends. Its centre sits at z_of(x, y) + lift
    (z_of defaults to 0)."""
    n = len(pts)
    ws = w if isinstance(w, (list, tuple)) else [w] * n
    hs = h if isinstance(h, (list, tuple)) else [h] * n
    zf = z_of or (lambda x, y: 0.0)
    P = [Vector((x, y)) for x, y in pts]
    d0 = (P[0] - P[1]).normalized() if n > 1 else Vector((0, 1))
    d1 = (P[-1] - P[-2]).normalized() if n > 1 else Vector((0, -1))
    path = []
    # rounded start: a point, then a ring at 70% size, then the body
    for k, (f, s) in enumerate(((1.0, 0.0), (0.55, 0.8))):
        q = P[0] + d0 * ws[0] * f
        path.append((q.x, q.y, zf(q.x, q.y) + lift, ws[0] * s, hs[0] * s))
    for i, p in enumerate(P):
        path.append((p.x, p.y, zf(p.x, p.y) + lift, ws[i], hs[i]))
    for f, s in ((0.55, 0.8), (1.0, 0.0)):
        q = P[-1] + d1 * ws[-1] * f
        path.append((q.x, q.y, zf(q.x, q.y) + lift, ws[-1] * s, hs[-1] * s))
    return sweep(bm, path, sides=sides, mat=mat)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, smooth=True, rot=0.0):
    """An ellipsoid centred at (x, y, z) in units, optionally turned by `rot` radians about Z."""
    before = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    c, s = math.cos(rot), math.sin(rot)
    for v in res["verts"]:
        lx, ly = v.co.x * rx, v.co.y * ry
        v.co = Vector((x + lx * c - ly * s, y + lx * s + ly * c, z + v.co.z * rz))
    tag_faces(bm, before, mat, smooth)


def dome(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=4, smooth=True):
    """The top half of an ellipsoid (a dome) sitting on z, closed underneath."""
    before = len(bm.faces)
    pts = []
    for j in range(rings + 1):
        a = (math.pi / 2) * j / rings
        pts.append((math.cos(a), math.sin(a)))
    ringsv = []
    for cr, sz in pts:
        if cr < 1e-6:
            ringsv.append([(x, y, z + rz)])
            continue
        ringsv.append([(x + rx * cr * math.cos(2 * math.pi * (k + 0.5) / segments),
                        y + ry * cr * math.sin(2 * math.pi * (k + 0.5) / segments), z + rz * sz)
                       for k in range(segments)])
    ring_loft(bm, ringsv, mat, smooth, cap_start=True, cap_end=False)
    tag_faces(bm, before, mat, smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (x, y) points in units (counter-clockwise)."""
    before = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2)
    tag_faces(bm, before, mat, smooth)


def mirror_x(bm, axis=0.0, start_vert=0):
    """Add a mirror image (about X = axis) of the geometry built since vertex `start_vert`."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
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


def run(name, build, file):
    """The usual main: build(sprite) returns a list of (model_name, objects, sprites); export each
    and, with -- --preview <png>, preview the first next to the first frame (and any further model
    next to its own first frame, as <png stem>-<model>.png)."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], str(out), ref, size=frame["size"])
        for model, objects, sprites in models[1:]:
            fr = sprites[0]["frames"][0]
            img = next(f["image"] for f in sprite["frames"] if f["image"].endswith(f"-{fr}.png"))
            common.render_preview(objects, str(out.parent / f"{out.stem}-{model}.png"),
                                  root / "reference" / "models" / name / img, size=frame["size"])
    return sprite
