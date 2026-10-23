"""Helpers shared by batch b040's enemy models (newshs.shp grey fighters).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b040 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
Some helpers are copied from lib_b003 (inset_outline, bevel_prism).
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def dims(size):
    """Sprite block size in pixels (w, h) for size 1 or 2."""
    return (12, 14) if size == 1 else (24, 28)


def px(c, size=2):
    """Sprite column (pixel centre) to Blender X."""
    return (c + 0.5 - dims(size)[0] / 2) / 12


def row(r, size=2):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (dims(size)[1] / 2 - (r + 0.5)) / 12


def ex(e, size=2):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (e - dims(size)[0] / 2) / 12


def ey(e, size=2):
    """Sprite row edge (0 = top edge of row 0) to Blender Y."""
    return (dims(size)[1] / 2 - e) / 12


def outline(edges, size=2):
    """[(column edge, row edge), ...] to Blender XY, in the order given."""
    return [(ex(c, size), ey(r, size)) for c, r in edges]


def mirror_outline(half, axis_edge, size=2):
    """A closed outline from its left half (column/row edges, top to bottom, left of `axis_edge`):
    returns the full outline counter-clockwise seen from above, in Blender XY."""
    left = list(half)
    right = [(2 * axis_edge - c, r) for c, r in reversed(half)]
    pts = outline(left + right, size)
    return pts  # left side goes down (top to bottom), right side comes back up: counter-clockwise


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    """Move every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def scale(bm, start, sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """Scale every vertex added since `start` about (cx, cy, cz)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x = cx + (v.co.x - cx) * sx
        v.co.y = cy + (v.co.y - cy) * sy
        v.co.z = cz + (v.co.z - cz) * sz


def inset_outline(outline_pts, d):
    """Move each vertex of a closed XY outline inward by `d` (from lib_b003)."""
    n = len(outline_pts)
    area = sum(outline_pts[i][0] * outline_pts[(i + 1) % n][1] - outline_pts[(i + 1) % n][0] * outline_pts[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline_pts[i - 1], outline_pts[i], outline_pts[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length * sign, ex_ / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def bevel_prism(bm, outline_pts, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None, bottom_bevel=0.0):
    """A prism from z0 to z1 whose top edges are chamfered by `bevel` (and the bottom ones by
    `bottom_bevel`). `top_mat` (default mat_index) colours the flat top. Outline counter-clockwise."""
    bevel_h = bevel if bevel_h is None else bevel_h
    top = inset_outline(outline_pts, bevel)
    rings = []
    if bottom_bevel:
        rings.append([bm.verts.new((x, y, z0)) for x, y in inset_outline(outline_pts, bottom_bevel)])
        rings.append([bm.verts.new((x, y, z0 + bottom_bevel)) for x, y in outline_pts])
    else:
        rings.append([bm.verts.new((x, y, z0)) for x, y in outline_pts])
    rings.append([bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline_pts])
    rings.append([bm.verts.new((x, y, z1)) for x, y in top])
    n = len(outline_pts)
    bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    bm.faces.new(rings[-1]).material_index = mat_index if top_mat is None else top_mat
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat_index


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0, bevel=0.0):
    """An axis-aligned box (optionally with a chamfered top)."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    bevel_prism(bm, pts, z0, z1, bevel, mat_index=mat_index)


def dome(bm, cx, cy, rx, ry, h, z=0.0, rings=4, sides=12, mat_index=0):
    """A half-ellipsoid dome on z, centred at (cx, cy), with a flat bottom."""
    pts = []
    for k in range(rings + 1):
        t = (math.pi / 2) * k / rings
        pts.append((math.cos(t), z + h * math.sin(t)))
    layers = []
    for s, zz in pts[:-1]:
        layers.append([bm.verts.new((cx + rx * s * math.cos(2 * math.pi * (i + 0.5) / sides),
                                     cy + ry * s * math.sin(2 * math.pi * (i + 0.5) / sides), zz))
                       for i in range(sides)])
    apex = bm.verts.new((cx, cy, z + h))
    bm.faces.new(list(reversed(layers[0]))).material_index = mat_index
    for a, b in zip(layers, layers[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat_index
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((layers[-1][i], layers[-1][j], apex)).material_index = mat_index


def preview(objs, sprite, root, name, frame=0):
    """Render the preview if the script was given `-- --preview <png>`."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][frame]
        ref = Path(root) / "reference" / "models" / name / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])
