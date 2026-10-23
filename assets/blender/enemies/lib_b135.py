"""Helpers shared by batch b135's enemy models (ground structures from newshs.shp).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b135 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
Several helpers are copied from lib_b003.py.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def ex(e, w=24):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (e - w / 2) / 12


def ey(e, h=28):
    """Sprite row edge (0 = top edge of row 0) to Blender Y."""
    return (h / 2 - e) / 12


def outline_px(points, w=24, h=28):
    """A closed outline given in sprite edge coordinates, as counter-clockwise Blender XY."""
    pts = [(ex(c, w), ey(r, h)) for c, r in points]
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    return pts if area > 0 else list(reversed(pts))


def rect_px(c0, r0, c1, r1, w=24, h=28):
    """A rectangle between sprite edges, as a counter-clockwise Blender outline."""
    return outline_px([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], w, h)


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude an XY outline from z0 up to z1."""
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def inset_outline(outline, d):
    """Move each vertex of a closed counter-clockwise XY outline inward by `d`."""
    n = len(outline)
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length, ex_ / length))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def bevel_prism(bm, outline, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None):
    """A prism from z0 to z1 whose top edges are chamfered inward by `bevel` over `bevel_h`.
    `top_mat` (default mat_index) colours the flat top."""
    bevel_h = bevel if bevel_h is None else bevel_h
    top = inset_outline(outline, bevel)
    n = len(outline)
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = mat_index
    bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i])).material_index = mat_index
        bm.faces.new((mid[i], mid[j], hi[j], hi[i])).material_index = mat_index


def cylinder(bm, cx, cy, r, z0, z1, sides=12, mat_index=0):
    """An upright cylinder."""
    pts = [(cx + r * math.cos(2 * math.pi * (i + 0.5) / sides), cy + r * math.sin(2 * math.pi * (i + 0.5) / sides))
           for i in range(sides)]
    prism(bm, pts, z0, z1, mat_index)


def annulus(bm, cx, cy, r_out, r_in, z0, z1, sides=12, mat_index=0):
    """An upright tube (a ring with walls inside and out), open through the middle."""
    def ring(r, z):
        return [bm.verts.new((cx + r * math.cos(2 * math.pi * (i + 0.5) / sides),
                              cy + r * math.sin(2 * math.pi * (i + 0.5) / sides), z)) for i in range(sides)]
    ob, ot, ib, it = ring(r_out, z0), ring(r_out, z1), ring(r_in, z0), ring(r_in, z1)
    for i in range(sides):
        j = (i + 1) % sides
        for f in ((ob[i], ob[j], ot[j], ot[i]), (it[i], it[j], ib[j], ib[i]),
                  (ot[i], ot[j], it[j], it[i]), (ib[i], ib[j], ob[j], ob[i])):
            bm.faces.new(f).material_index = mat_index


def set_smooth(bm, face_start, smooth=True):
    """Mark the faces added since index `face_start` smooth (or flat)."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[face_start:]:
        f.smooth = smooth


def mesh_object_mixed(name, bm, materials, collection):
    """Like common.mesh_object, but keeps each face's own smooth flag (see set_smooth)."""
    import bmesh
    import bpy
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def run(root, name, build):
    """Load the sprite, build, export every frame on one model and render the preview if asked."""
    sprite = common.load_sprite(root, name)
    obj = build(sprite)
    common.export_sprite_model(root, [obj], f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = root / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    return obj
