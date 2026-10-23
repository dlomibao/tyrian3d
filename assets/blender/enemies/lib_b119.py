"""Helpers shared by batch b119's scripts (the two four-piece ground structures of newshb.shp).

Both assemblies are a row of four 2x2 pieces, 96 x 28 px in all. Geometry is given in assembly
pixel coordinates (column 0-95, row 0-27, pixel centres; fractions allowed, so a pixel's left
edge is c - 0.5), and the whole row is built once and cut with common.split_assembly.
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
W, H = 96, 28  # assembly size in pixels


def X(c):
    """Assembly pixel column (centre) to Blender X; the assembly's centre is the origin."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def _xy(p):
    return (X(p[0]), Y(p[1]))


def _ccw(pts):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return area > 0


def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def stack(bm, rings, top_mat=0, side_mat=0, bottom_mat=None, smooth=False):
    """A solid through outlines of (col, row) points stacked in height: rings is a list of
    (outline, z) from the top down, every outline with the same number of points in the same
    winding. The top outline is capped with top_mat, the bottom one closed underneath. side_mat
    is a material index or a function (nx, ny) -> index of a side face's outward XY direction."""
    pts = [[_xy(p) for p in outline] for outline, _ in rings]
    if not _ccw(pts[-1]):
        pts = [p[::-1] for p in pts]
    vs = [[bm.verts.new((x, y, z)) for x, y in p] for p, (_, z) in zip(pts, rings)]
    f = bm.faces.new(vs[0])
    f.material_index, f.smooth = top_mat, False
    f = bm.faces.new(vs[-1][::-1])
    f.material_index, f.smooth = (top_mat if bottom_mat is None else bottom_mat), False
    n = len(vs[0])
    for k in range(len(vs) - 1):
        vt, vb, b = vs[k], vs[k + 1], pts[k + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
            dx, dy = b[j][0] - b[i][0], b[j][1] - b[i][1]
            ln = math.hypot(dx, dy) or 1.0
            f.material_index = side_mat(dy / ln, -dx / ln) if callable(side_mat) else side_mat
            f.smooth = smooth


def frustum(bm, top, bottom, z_top, z_bottom, top_mat=0, side_mat=0, bottom_mat=None, smooth=False):
    """A solid between two outlines of (col, row) points with the same number of points: `top`
    at z_top and `bottom` at z_bottom (both in the same winding)."""
    stack(bm, [(top, z_top), (bottom, z_bottom)], top_mat, side_mat, bottom_mat, smooth)


def blend(a, b, t):
    """Points t of the way from outline a to outline b."""
    return [(pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t) for pa, pb in zip(a, b)]


def plate(bm, outline, z0, z1, mat=0):
    """A flat plate from z0 to z1 with an outline of (col, row) points (use pixel edges)."""
    frustum(bm, outline, outline, z1, z0, top_mat=mat, side_mat=mat)


def box(bm, c0, r0, c1, r1, z0, z1, mat=0):
    """An axis-aligned box over pixel columns c0..c1 and rows r0..r1 (inclusive pixels)."""
    plate(bm, [(c0 - 0.5, r0 - 0.5), (c1 + 0.5, r0 - 0.5), (c1 + 0.5, r1 + 0.5), (c0 - 0.5, r1 + 0.5)],
          z0, z1, mat)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid; with z_min, vertices below it are flattened onto it (a dome on a base)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
        if z_min is not None:
            co.z = max(co.z, z_min)
        v.co = co
    _tag(bm, before, mat, True)


def tube_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite (along Y) on column `col`: sections are (row, half_width_px,
    half_height_units, z). Zero width and height make a point."""
    before = set(bm.faces)
    start = len(bm.verts)
    common.loft(bm, [(Y(r), w * PX, h, z) for r, w, h, z in sections], sides=sides, mat_index=mat)
    common.shift_x(bm, start, X(col))
    _tag(bm, before, mat, smooth)


def tube_x(bm, row, sections, sides=10, mat=0, smooth=True):
    """A loft across the sprite (along X) on row `row`: sections are (col, half_depth_px,
    half_height_units, z)."""
    before = set(bm.faces)
    start = len(bm.verts)
    common.loft(bm, [(X(c), w * PX, h, z) for c, w, h, z in sections], sides=sides, mat_index=mat)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:  # loft runs along +Y with width on X: swap X and Y
        v.co.x, v.co.y = v.co.y, Y(row) + v.co.x
    _tag(bm, before, mat, smooth)


def mirror_cols(bm, axis_col, start_vert=0):
    """Add a mirror image, about the centre of pixel column axis_col (fractions allowed), of the
    geometry whose vertices were added since start_vert."""
    ax = X(axis_col)
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
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


def merged_sprite(root, pieces):
    """The first piece's sprite.json with the colours of every piece, so any index is valid."""
    data = common.load_sprite(root, pieces[0])
    for name in pieces[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def layout(sprite, pieces):
    """(name, cx, cy) of each piece relative to the assembly's centre, for split_assembly."""
    entries = [e for e in sprite["assemblyLayout"] if e["model"] in pieces]
    cx0 = (min(e["cx"] for e in entries) + max(e["cx"] for e in entries)) / 2
    cy0 = (min(e["cy"] for e in entries) + max(e["cy"] for e in entries)) / 2
    return [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in entries]


def composite_png(root, lay, out):
    """The whole row's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 8 (96 x 112 px, the row in the middle)."""
    import numpy as np
    img = np.zeros((112, 96, 4), dtype=np.float32)
    for name, cx, cy in lay:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + 48 - 12), int(cy + 56 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 96, 112, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export_assembly(root, obj, sprite, pieces):
    """Cut the whole row into its pieces, export each with its own sprites and, with
    --preview <png>, render the whole row and each piece (<piece>.png beside it)."""
    lay = layout(sprite, pieces)
    parts = common.split_assembly(obj, lay)
    for name in pieces:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [parts[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, lay, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=8, view_px=480)
        for name in pieces:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([parts[name]], str(out.parent / f"{name}.png"), img, size=2)
    return parts
