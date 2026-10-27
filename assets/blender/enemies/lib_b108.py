"""Helpers shared by batch b108's model scripts (newsh7 ice-level ground pieces).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r) for a 24x28 block. Assembly scripts pass their own block size.
Several helpers are copied from lib_b007 (ring_loft, tube, polyline_tube, ellipse_ring).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True, smooth=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.
    `mats` is one material index, or a list with one per band between consecutive rings."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    faces = []
    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        m = mats[b] if isinstance(mats, list) else mats
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            f = bm.faces.new(face)
            f.material_index = m
            faces.append(f)
    first = mats[0] if isinstance(mats, list) else mats
    last = mats[-1] if isinstance(mats, list) else mats
    if cap_start and len(verts[0]) > 2:
        f = bm.faces.new(list(reversed(verts[0])))
        f.material_index = first
        faces.append(f)
    if cap_end and len(verts[-1]) > 2:
        f = bm.faces.new(verts[-1])
        f.material_index = last
        faces.append(f)
    for f in faces:
        f.smooth = smooth
    return verts


def ellipse_ring(cx, cy, z, rx, ry, n=12, phase=0.5):
    """n points of an ellipse around (cx, cy) at height z (counter-clockwise from +X)."""
    return [(cx + rx * math.cos(2 * math.pi * (i + phase) / n), cy + ry * math.sin(2 * math.pi * (i + phase) / n), z)
            for i in range(n)]


def tube(bm, p0, p1, radius, sides=6, mat_index=0, caps=True, smooth=True):
    """A round bar between two 3D points."""
    return polyline_tube(bm, [p0, p1], radius, sides=sides, mat_index=mat_index, caps=caps, smooth=smooth)


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, smooth=True, squash=1.0):
    """One continuous tube along a polyline with mitred joints. `radius` is a number or one per
    point; `squash` scales the tube's height (its extent along Z) for flat ridges."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    rings = []
    for c, t, r in zip(pts, tangents, radii):
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized()
        v = t.cross(u).normalized()
        if v.z < 0:
            v = -v
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            off = r * (math.cos(a) * u + math.sin(a) * v)
            off.z *= squash
            ring.append(tuple(c + off))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps, smooth=smooth)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid centred at (x, y, z) (units). With z_min, vertices below it are flattened onto
    it (a dome sitting on a surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        co = Vector((x + v.co.x * rx, y + v.co.y * ry, z + v.co.z * rz))
        if z_min is not None and co.z < z_min:
            co.z = z_min
        v.co = co
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def dome(bm, x, y, z0, rx, ry, h, mat=0, segments=16, rings=5, smooth=True):
    """A half-ellipsoid dome standing on z0 (its base an ellipse rx x ry, its top at z0 + h)."""
    rs = []
    for i in range(rings):
        a = (math.pi / 2) * i / rings
        rs.append(ellipse_ring(x, y, z0 + h * math.sin(a), rx * math.cos(a), ry * math.cos(a), n=segments))
    rs.append([(x, y, z0 + h)])
    ring_loft(bm, rs, mat, cap_start=True, cap_end=False, smooth=smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (x, y) points in units (counter-clockwise or
    clockwise: normals are recalculated at the end)."""
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def frustum(bm, outline_bottom, outline_top, z0, z1, mat=0, smooth=False, cap_bottom=True):
    """Join two outlines (same point count, (x, y) units) at heights z0 and z1: a sloped block."""
    rings = [[(x, y, z0) for x, y in outline_bottom], [(x, y, z1) for x, y in outline_top]]
    ring_loft(bm, rings, mat, cap_start=cap_bottom, cap_end=True, smooth=smooth)


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


def merged_sprite(root, first, names):
    """`first`'s sprite.json with the colours of every named piece, so any piece's index is valid."""
    data = common.load_sprite(root, first)
    for name in names:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w_px, h_px, cx0=0, cy0=0, frames=None):
    """The whole assembly's sprite (each piece's first frame, or `frames[name]`) as one image of
    w_px x h_px with screen pixel (cx0, cy0) at its centre."""
    import numpy as np
    img = np.zeros((h_px, w_px, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][(frames or {}).get(name, 0)]
        x0, y0 = cx - cx0 + w_px // 2 - 12, cy - cy0 + h_px // 2 - 14
        for r, prow in enumerate(frame["pixels"]):
            for c, v in enumerate(prow):
                if v >= 0 and 0 <= y0 + r < h_px and 0 <= x0 + c < w_px:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w_px, h_px, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run(name, build, file):
    """The usual main for a single model: build, export every model and, with -- --preview <png>,
    preview the first (and <png stem>-f2.png etc. for the others).

    `build(sprite)` returns a list of (model_name, objects, sprites, frame_index) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites, _ in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for i, (model, objects, _, fi) in enumerate(models):
            frame = sprite["frames"][fi]
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.parent / f"{model}.png"
            common.render_preview(objects, str(path), ref, size=frame["size"])
    if "--frame-previews" in sys.argv:  # every frame of the first model, one row each
        common.render_frame_previews(models[0][1], sys.argv[sys.argv.index("--frame-previews") + 1], sprite, root)
    return sprite


def arch_loft(bm, sections, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True, x_of=None):
    """A loft of half-ellipse arches standing on the ground, along Y: each section is
    (x_centre, y, half_width, height, z_base) in units. The flat bottom is closed, so it's a solid
    hump (a shell, dome or ridge). A section with zero width and height is a point."""
    rings = []
    for x, y, w, h, z0 in sections:
        if w == 0 and h == 0:
            rings.append([(x, y, z0)])
            continue
        ring = []
        for i in range(sides + 1):
            a = math.pi * i / sides
            ring.append((x + w * math.cos(a), y, z0 + h * math.sin(a)))
        rings.append(ring)
    return ring_loft(bm, rings, mat, cap_start=cap_start, cap_end=cap_end, smooth=smooth)


def rotate_new(bm, start, pivot, angle, axis="X"):
    """Rotate every vertex added since index `start` about `pivot` by `angle` radians."""
    from mathutils import Matrix
    bm.verts.ensure_lookup_table()
    m = Matrix.Rotation(angle, 4, axis)
    p = Vector(pivot)
    for v in bm.verts[start:]:
        v.co = p + m @ (v.co - p)
