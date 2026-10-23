"""Helpers shared by batch b120's model scripts (the newsh2 brass turret block and the long pipe).

Mostly copied from lib_b053.

Pixel coordinates: a grid w x h px whose centre is the Blender origin. `X(c)` and `Y(r)` take
pixel centres (fractions allowed), 1 px = 1/12 unit, sprite up is +Y.
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


def X(c, w=24):
    return (c + 0.5 - w / 2) / 12


def Y(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def _faces_done(bm, first, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, up=(0, 0, 1)):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path; the width is measured across the path (perpendicular to `up`), the
    height along `up`. A ring of zero size collapses to a point (a rounded or pointed end)."""
    first = len(bm.faces)
    up = Vector(up)
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t = t - up * t.dot(up)
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
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
    _faces_done(bm, first, mat, smooth)


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, smooth=True, bump=None):
    """An ellipsoid at `centre` with radii (rx, ry, rz); bump(dir) -> scale makes it lumpy."""
    first = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        d = v.co.copy()
        s = bump(d) if bump else 1.0
        v.co = Vector((cx + d.x * rx * s, cy + d.y * ry * s, cz + d.z * rz * s))
    _faces_done(bm, first, mat, smooth)


def dome(bm, centre, radii, mat=0, segments=16, rings=5, smooth=True):
    """The upper half of an ellipsoid, its flat base at centre z."""
    first = len(bm.faces)
    cx, cy, cz = centre
    rx, ry, rz = radii
    rows = []
    for i in range(rings):
        a = (math.pi / 2) * i / rings
        rows.append([bm.verts.new((cx + rx * math.cos(a) * math.cos(t), cy + ry * math.cos(a) * math.sin(t),
                                   cz + rz * math.sin(a)))
                     for t in (2 * math.pi * k / segments for k in range(segments))])
    top = bm.verts.new((cx, cy, cz + rz))
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    for k in range(segments):
        bm.faces.new((rows[-1][k], rows[-1][(k + 1) % segments], top))
    bm.faces.new(list(reversed(rows[0])))
    _faces_done(bm, first, mat, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False, top_mat=None):
    """Extrude an outline of (x, y) units (any winding) from z0 to z1."""
    first = len(bm.faces)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in outline]
    bm.faces.new(list(reversed(lo)))
    topf = bm.faces.new(hi)
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    _faces_done(bm, first, mat, smooth)
    if top_mat is not None:
        topf.material_index = top_mat


def inset(outline, d):
    """Offset a convex-ish outline inwards by d (outline in either winding)."""
    n = len(outline)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    s = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(outline[i - 1]), Vector(outline[i]), Vector(outline[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * s
        n1 = Vector((-e1.y, e1.x)) * s
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        cos = max(0.3, b.dot(n0))
        q = p1 + b * (d / cos)
        out.append((q.x, q.y))
    return out


def bevel_prism(bm, outline, z0, z1, bevel, mat=0, top_mat=None, bevel_h=None):
    """A prism from z0 to z1 whose top edge is chamfered inwards by `bevel`."""
    first = len(bm.faces)
    bevel_h = bevel if bevel_h is None else bevel_h
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    top = inset(outline, bevel)
    n = len(outline)
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo)))
    topf = bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], hi[j], hi[i]))
    _faces_done(bm, first, mat, False)
    if top_mat is not None:
        topf.material_index = top_mat


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def mirror(bm, first_vert, axis="y", about=0.0):
    """Add a mirror image of the geometry built since vertex index `first_vert`, reflected across
    the plane x = about (axis "x") or y = about (axis "y")."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[first_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = [e for e in bm.edges if all(v in verts for v in e.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        if axis == "x":
            v.co.x = 2 * about - v.co.x
        else:
            v.co.y = 2 * about - v.co.y
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


# --- assemblies -------------------------------------------------------------------------------

def assembly_grid(root, piece):
    """The whole assembly's first-frame pixels as one grid: returns (grid, colours, x0, y0) where
    grid[r][c] is a palette index (-1 transparent) and (x0, y0) is the screen pixel of grid (0, 0)."""
    data = common.load_sprite(root, piece)
    # Only this assembly's own pieces (the layout can also list a neighbouring enemy).
    layout = [e for e in data["assemblyLayout"] if e["model"] in data["assemblyPieces"]]
    x0 = min(e["cx"] for e in layout) - 12
    y0 = min(e["cy"] for e in layout) - 14
    w = max(e["cx"] for e in layout) + 12 - x0
    h = max(e["cy"] for e in layout) + 14 - y0
    grid = [[-1] * w for _ in range(h)]
    colors = {}
    for e in layout:
        d = common.load_sprite(root, e["model"])
        colors.update(d["colors"])
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[e["cy"] - 14 - y0 + r][e["cx"] - 12 - x0 + c] = v
    return grid, colors, x0, y0, layout


def composite_png(grid, colors, out, pad_to=None):
    """Write a grid of palette indices as a PNG (1 px per sprite px), centred in a pad_to=(w, h)
    canvas if given (render_preview expects the 24:28 shape)."""
    import numpy as np
    h, w = len(grid), len(grid[0])
    W, H = pad_to or (w, h)
    img = np.zeros((H, W, 4), dtype=np.float32)
    ox, oy = (W - w) // 2, (H - h) // 2
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v >= 0:
                img[oy + r, ox + c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def paint(bm, first_face, sample, slot_for, up_only=True):
    """Set the material of every face added since `first_face` from the sprite pixel under its
    centre: sample(x, y) -> palette index or None; slot_for(index) -> slot or None (leave it)."""
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[first_face:])  # outward, whatever the winding
    bm.normal_update()
    for f in bm.faces[first_face:]:
        if up_only and f.normal.z < 0.2:
            continue
        c = f.calc_center_median()
        idx = sample(c.x, c.y)
        if idx is None or idx < 0:
            continue
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def export_assembly(root, obj, pieces_layout, out_preview, grid, colors, size):
    """Split `obj` (built in assembly units) into its pieces, export each, and render previews."""
    pieces = common.split_assembly(obj, pieces_layout)
    for name, _, _ in pieces_layout:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [pieces[name]], f"enemies/{name}", data["sprites"])
    if out_preview:
        import tempfile
        out = Path(out_preview)
        w, h = len(grid[0]), len(grid)
        W = max(w, round(h * 24 / 28))
        H = round(W * 28 / 24)
        W = max(W, round(H * 24 / 28))
        ref = composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(W, H))
        common.render_preview([obj], str(out), str(ref), size=W / 12, view_px=640)
        for name, _, _ in pieces_layout:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    return pieces
