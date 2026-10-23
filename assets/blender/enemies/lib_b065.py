"""Helpers for batch b065: the newsh4 boss made of two three-piece assemblies.

assembly-newsh4-81 (newsh4-81, -83, -85: the head, horns and shoulder pods) sits above
assembly-newsh4-123 (newsh4-119, -121, -123: the body, wings and engine pods), overlapping it by
4 px. Both are built in one shared frame so they line up in game: column c and row r are the
pixel edges of a 72 x 52 px grid whose left edge is screen x 135 and top edge screen y 159 (the
top-left of newsh4-81). The craft's mirror axis is column edge 30, which is Blender X = 0;
Blender Y = 0 is row edge 26.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

import common

PX = 1 / 12
AXIS = 30.0
MID_ROW = 26.0
# Screen pixel of the frame's origin, for common.split_assembly.
SCREEN_X0, SCREEN_Y0 = 135 + AXIS, 159 + MID_ROW


def X(c):
    """Column edge (fractions allowed) to Blender X."""
    return (c - AXIS) * PX


def Y(r):
    """Row edge to Blender Y (sprite up is +Y)."""
    return (MID_ROW - r) * PX


def mirror_c(c):
    """The column edge mirrored about the craft's axis."""
    return 2 * AXIS - c


def _faces_since(bm, n, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in XY; width is across the path, height along Z. A ring of zero
    size collapses to a point (a rounded or pointed end)."""
    n = len(bm.faces)
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
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
    _faces_since(bm, n, mat, smooth)


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column edge `col`: sections are
    (row, half_width_px, half_height_units, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges. z0 and z1 may be
    functions of (col, row) to slope the bottom or top."""
    n = len(bm.faces)
    zb = z0 if callable(z0) else (lambda c, r: z0)
    zt = z1 if callable(z1) else (lambda c, r: z1)
    top = [bm.verts.new((X(c), Y(r), zt(c, r))) for c, r in outline]
    bot = [bm.verts.new((X(c), Y(r), zb(c, r))) for c, r in outline]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    k = len(outline)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    _faces_since(bm, n, mat, smooth)


def box(bm, c0, r0, c1, r1, z0, z1, mat=0):
    prism(bm, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, half=False):
    """An ellipsoid centred on (col, row) edges at height z; `half` keeps only the top half
    (a dome sitting on z)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    verts = res["verts"]
    if half:
        for v in verts:
            v.co.z = max(v.co.z, 0.0)
        bmesh.ops.remove_doubles(bm, verts=verts, dist=1e-5)
        verts = [v for v in verts if v.is_valid]
    for v in verts:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def mirror_since(bm, start_vert, axis_c=AXIS):
    """Add a mirror image (about column edge `axis_c`, the craft's axis by default) of every
    vertex/face added since vertex index `start_vert`."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = [e for e in bm.edges if all(v in verts for v in e.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * X(axis_c) - v.co.x
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


def merged_sprite(root, pieces):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, pieces[0])
    for name in pieces[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def layout(root, pieces):
    """[(piece, x, y)] in screen pixels relative to the frame's origin, for split_assembly."""
    data = common.load_sprite(root, pieces[0])
    return [(e["model"], e["cx"] - SCREEN_X0, e["cy"] - SCREEN_Y0) for e in data["assemblyLayout"]
            if e["model"] in pieces]


def composite_png(root, lay, out, size=6):
    """The assembly's sprite (first frames) as one image centred on the frame's origin, sized
    for render_preview(size=size): size*12 x size*14 px."""
    import numpy as np
    w, h = size * 12, size * 14
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in lay:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(round(cx + w / 2 - 12)), int(round(cy + h / 2 - 14))
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export_assembly(root, obj, pieces, argv):
    """Split `obj` into its pieces, export each with its own sprites and, with --preview, render
    the whole assembly to the given png and each piece to <piece>.png beside it."""
    import sys
    import tempfile
    lay = layout(root, pieces)
    parts = common.split_assembly(obj, lay)
    for name in pieces:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [parts[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        ref = composite_png(root, lay, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=640)
        for name in pieces:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([parts[name]], str(out.parent / f"{name}.png"), img, size=2)
    return parts
