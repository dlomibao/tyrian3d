"""Helpers shared by batch b101's enemy models (newshf.shp ground pieces).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b101 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def ex(e, w=24):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (e - w / 2) / 12


def ey(e, h=28):
    """Sprite row edge (0 = top edge of row 0) to Blender Y."""
    return (h / 2 - e) / 12


def pts(edges, w=24, h=28):
    """A list of (column edge, row edge) pairs to Blender XY points."""
    return [(ex(c, w), ey(r, h)) for c, r in edges]


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    """Move every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def set_smooth(bm, face_start, smooth=True):
    """Mark the faces added since index `face_start` smooth (or flat)."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[face_start:]:
        f.smooth = smooth


def mesh_object_mixed(name, bm, materials, collection):
    """Like common.mesh_object, but keeps each face's own smooth flag (see set_smooth)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def merged_colors(root, names):
    """A sprite-like dict whose `colors` merge the palettes of several sprite.json files."""
    merged = {"name": "+".join(names), "colors": {}}
    for n in names:
        merged["colors"].update(common.load_sprite(root, n)["colors"])
    return merged


def _signed_area(poly):
    n = len(poly)
    return sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) / 2


def ccw(poly):
    """The polygon in counter-clockwise order (seen from above)."""
    return list(poly) if _signed_area(poly) > 0 else list(reversed(poly))


def offset_polygon(poly, dists):
    """Move each edge of a counter-clockwise polygon inward by its own distance (dists[i] is for the
    edge from poly[i] to poly[i+1]); each vertex goes to where its two offset edges meet."""
    n = len(poly)
    if not isinstance(dists, (list, tuple)):
        dists = [dists] * n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length  # inward (left) normal for a CCW polygon
        d = dists[i]
        lines.append(((x0 + nx * d, y0 + ny * d), (dx, dy), (nx, ny)))
    out = []
    for i in range(n):
        (p, u, _), (q, v, nq) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append((q[0], q[1]))
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def frustum(bm, bottom, top, z0, z1, mat=0, top_mat=None):
    """A solid joining a bottom outline at z0 to a top outline (same vertex count) at z1."""
    n = len(bottom)
    lo = [bm.verts.new((x, y, z0)) for x, y in bottom]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = mat
    bm.faces.new(hi).material_index = mat if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat


def prism(bm, outline, z0, z1, mat=0, top_mat=None):
    """Extrude an XY outline from z0 up to z1."""
    outline = ccw(outline)
    frustum(bm, outline, outline, z0, z1, mat, top_mat)


def bevel_block(bm, outline, z0, z1, bevel, bevel_h=None, mat=0, top_mat=None, edges=None):
    """A prism from z0 to z1 whose top edges are chamfered: walls rise to z1 - bevel_h, then a
    sloped band leads in by `bevel` (per edge if a list; `edges` = list of booleans picks which
    edges are chamfered) to the flat top."""
    outline = ccw(outline)
    n = len(outline)
    bevel_h = bevel if bevel_h is None else bevel_h
    if edges is not None:
        d = [bevel if e else 0.0 for e in edges]
    else:
        d = bevel
    top = offset_polygon(outline, d)
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = mat
    bm.faces.new(hi).material_index = mat if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i])).material_index = mat
        bm.faces.new((mid[i], mid[j], hi[j], hi[i])).material_index = mat


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, top_mat=None):
    """An axis-aligned box."""
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, top_mat)


def ellipsoid(bm, centre, radii, sides=16, rings=8, mat=0):
    """An ellipsoid (radii rx, ry, rz) at `centre`, lofted along Y, smooth shaded."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    sections = [(-ry, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        a = math.pi * i / rings
        sections.append((-ry * math.cos(a), rx * math.sin(a), rz * math.sin(a), 0.0))
    sections.append((ry, 0.0, 0.0, 0.0))
    start, fstart = len(bm.verts), len(bm.faces)
    common.loft(bm, sections, sides=sides, mat_index=mat)
    move(bm, start, cx, cy, cz)
    set_smooth(bm, fstart)


def cylinder_y(bm, x, y0, y1, z, rx, rz, sides=12, mat=0, cap_mat=None):
    """A cylinder lying along Y from y0 to y1 (y0 < y1), smooth sided."""
    fstart = len(bm.faces)
    start = len(bm.verts)
    common.loft(bm, [(y0, rx, rz, z), (y1, rx, rz, z)], sides=sides, mat_index=mat)
    move(bm, start, x, 0, 0)
    bm.faces.ensure_lookup_table()
    faces = bm.faces[fstart:]
    for f in faces:
        f.smooth = len(f.verts) == 4
        if cap_mat is not None and len(f.verts) != 4:
            f.material_index = cap_mat


def cylinder_z(bm, x, y, z0, z1, rx, ry, sides=12, mat=0, top_mat=None):
    """An upright cylinder (elliptic, radii rx, ry) from z0 to z1, smooth sided."""
    fstart = len(bm.faces)
    ring = [(x + rx * math.cos(2 * math.pi * (i + 0.5) / sides), y + ry * math.sin(2 * math.pi * (i + 0.5) / sides))
            for i in range(sides)]
    frustum(bm, ring, ring, z0, z1, mat, top_mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[fstart:]:
        f.smooth = len(f.verts) == 4


def geom_since(bm, vstart):
    """The verts, edges and faces built from vertex index `vstart` on."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[vstart:]
    vs = set(verts)
    edges = [e for e in bm.edges if all(v in vs for v in e.verts)]
    faces = [f for f in bm.faces if all(v in vs for v in f.verts)]
    return verts + edges + faces


def clip(bm, plane_co, plane_no, geom=None):
    """Cut away everything (or just `geom`) on the side of the plane the normal points to,
    filling the cut."""
    if geom is None:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane_co, plane_no=plane_no, clear_outer=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        for f in res["faces"]:
            f.smooth = False


def clip_tile(bm, w=24, h=28):
    """Clip a bmesh to its sprite tile's box (in X and Y)."""
    hw, hh = w / 24, h / 24
    for co, no in (((-hw, 0, 0), (-1, 0, 0)), ((hw, 0, 0), (1, 0, 0)),
                   ((0, -hh, 0), (0, -1, 0)), ((0, hh, 0), (0, 1, 0))):
        clip(bm, co, no)


def preview(objects, root, name, sprite, frame=0):
    """Render the standard preview if `--preview <png>` was given."""
    if "--preview" not in sys.argv:
        return
    out = sys.argv[sys.argv.index("--preview") + 1]
    ref = Path(root) / "reference" / "models" / name / sprite["frames"][frame]["image"]
    common.render_preview(objects, out, ref, size=sprite["frames"][frame]["size"])


# --- The red armoured corners (newshf-230, newshf-238) -------------------------------------------

def build_corner(sprite, name, spec):
    """A corner of a red armoured hull: a chamfered red slab (its outer edge sloping to the
    ground), raised ribs on top, and a grey ball half sunk in a dark socket at the tile edge.

    spec: hull (edge-coord outline), chamfer (list of booleans per hull edge, CCW order after
    ccw()), ribs [(outline, highlight?)], socket outline, ball (col, row, radius_px, clip side)."""
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(65, metallic=0.15, roughness=0.6),  # 0 dark red hull top
        pal(67, metallic=0.15, roughness=0.6),  # 1 red sloped flanks
        pal(69, metallic=0.35, roughness=0.45),  # 2 red ribs
        pal(71, metallic=0.35, roughness=0.4),  # 3 light red rib tops
        pal(2, metallic=0.2, roughness=0.8),  # 4 dark socket
        pal(7, metallic=0.75, roughness=0.2),  # 5 grey ball
    ]
    HULL, FLANK, RIB, RIBTOP, SOCKET, BALL = range(6)
    bm = bmesh.new()

    H = 0.22

    def chamfered(outline, flags, z1, bevel, top_mat):
        poly = pts(outline)
        if _signed_area(poly) < 0:  # keep the flags with their edges when reversing
            poly = list(reversed(poly))
            n = len(flags)
            flags = [flags[(n - 2 - i) % n] for i in range(n)]
        bevel_block(bm, poly, 0.0, z1, bevel / 12, bevel_h=bevel / 12 * 0.8, mat=FLANK, top_mat=top_mat,
                    edges=flags)

    chamfered(spec["hull"], spec["chamfer"], H, spec.get("bevel", 1.6), HULL)
    chamfered(spec["ledge"], spec["ledge_chamfer"], H - 0.07, 1.2, FLANK)

    for outline, top in spec["ribs"]:
        o = ccw(pts(outline))
        bevel_block(bm, o, H - 0.05, H + 0.07, 0.5 / 12, bevel_h=0.03, mat=RIB, top_mat=RIBTOP if top else RIB)

    prism(bm, pts(spec["socket"]), H - 0.04, H + 0.012, mat=SOCKET)

    c, r, rad, side = spec["ball"]
    start = len(bm.verts)
    ellipsoid(bm, (ex(c), ey(r), H - 0.02), (rad / 12, rad / 12, 0.2), sides=20, rings=10, mat=BALL)
    clip(bm, (side * 1.0, 0, 0), (side, 0, 0), geom=geom_since(bm, start))
    return bm, mats, coll
