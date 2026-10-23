"""Helpers shared by batch b034's model scripts (newshg.shp fliers of episode 2).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block. Several helpers are adapted from lib_b003,
lib_b004 and lib_b007.
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402,F401


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.
    `mats` is one material index or a list with one per band."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    mat = (lambda b: mats[b]) if isinstance(mats, list) else (lambda b: mats)
    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat(b)
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = mat(0)
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = mat(len(verts) - 2)
    return verts


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, flat=1.0):
    """A continuous round tube along a polyline (mitred joints). `radius` is a number or one per
    point; `flat` scales the ring's vertical (Z-ish) axis to flatten it."""
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
        if r == 0:
            rings.append([tuple(c)])
            continue
        rings.append([tuple(c + r * (math.cos(a) * u + flat * math.sin(a) * v))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def ellipsoid(bm, centre, radii, segments=16, rings=8, mat_index=0, z_power=1.0, bottom=1.0):
    """A UV ellipsoid. `bottom` scales the lower half's height (0.4 flattens the underside)."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    top = bm.verts.new((cx, cy, cz + rz))
    bot = bm.verts.new((cx, cy, cz - rz * bottom))
    grid = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        s, c = math.sin(phi), math.cos(phi)
        zz = c * rz if c > 0 else c * rz * bottom
        grid.append([bm.verts.new((cx + rx * s * math.cos(2 * math.pi * k / segments),
                                   cy + ry * s * math.sin(2 * math.pi * k / segments), cz + zz))
                     for k in range(segments)])
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((top, grid[0][k], grid[0][j])).material_index = mat_index
        bm.faces.new((bot, grid[-1][j], grid[-1][k])).material_index = mat_index
    for a, b in zip(grid, grid[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((a[k], b[k], b[j], a[j])).material_index = mat_index


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2,
                mat_index=mat_index)


def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` (edges move by d)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
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


def bevel_prism(bm, outline, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None, bottom_bevel=0.0):
    """A prism from z0 to z1 with chamfered top edges (and optionally bottom edges)."""
    bevel_h = bevel if bevel_h is None else bevel_h
    top = inset_outline(outline, bevel)
    low = inset_outline(outline, bottom_bevel) if bottom_bevel else outline
    n = len(outline)
    lo = [bm.verts.new((x, y, z0)) for x, y in low]
    rings = [lo]
    if bottom_bevel:
        rings.append([bm.verts.new((x, y, z0 + bottom_bevel)) for x, y in outline])
    rings.append([bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline])
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    rings.append(hi)
    bm.faces.new(list(reversed(lo))).material_index = mat_index
    bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat_index


def mask_outline(pixels, keep, smooth=2, thin=True, w=24, h=28):
    """The outline of the sprite pixels for which keep(index) is true (largest region), traced
    round pixel corners and smoothed by corner cutting; Blender XY, counter-clockwise."""
    inside = lambda c, r: 0 <= r < h and 0 <= c < w and keep(pixels[r][c])  # noqa: E731
    edges = {}
    for r in range(h):
        for c in range(w):
            if not inside(c, r):
                continue
            if not inside(c, r - 1):
                edges[(c + 1, r)] = (c, r)
            if not inside(c, r + 1):
                edges[(c, r + 1)] = (c + 1, r + 1)
            if not inside(c - 1, r):
                edges[(c, r)] = (c, r + 1)
            if not inside(c + 1, r):
                edges[(c + 1, r + 1)] = (c + 1, r)
    loops, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        loops.append(loop)
    loop = max(loops, key=len)
    pts = [Vector((c, r)) for c, r in loop]
    for _ in range(smooth):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append(p * 0.75 + q * 0.25)
            out.append(p * 0.25 + q * 0.75)
        pts = out
    poly = [((p.x - w / 2) / 12, (h / 2 - p.y) / 12) for p in pts]
    if thin:
        poly = poly[::2]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    return poly


def transform(bm, start, matrix):
    """Apply a 4x4 matrix to every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co = matrix @ v.co


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    transform(bm, start, Matrix.Translation((dx, dy, dz)))


def mirror_new_x(bm, start, cx=0.0):
    """Duplicate the geometry added since vertex `start`, mirrored across X = cx."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start:]
    faces = list({f for v in verts for f in v.link_faces})
    geom = verts + list({e for v in verts for e in v.link_edges}) + faces
    m = Matrix.Translation((cx, 0, 0)) @ Matrix.Scale(-1, 4, (1, 0, 0)) @ Matrix.Translation((-cx, 0, 0))
    dup = bmesh.ops.duplicate(bm, geom=geom)
    new_verts = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in new_verts:
        v.co = m @ v.co
    new_faces = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=new_faces)


def run(name, build, file, preview_frame=0):
    """Build, export each model and, with -- --preview <png>, preview the first.
    `build(sprite)` returns a list of (model_name, objects, sprites)."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][preview_frame]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
        # Extra previews of the other models, next to the first: <out>-<model>.png
        for model, objects, _ in models[1:]:
            idx = model_frame(sprite, model)
            if idx is None:
                continue
            f = sprite["frames"][idx]
            extra = str(out)[:-4] + "-" + model.split("-")[-1] + ".png"
            common.render_preview(objects, extra, root / "reference" / "models" / name / f["image"], size=f["size"])
    return sprite


def model_frame(sprite, model):
    """Index of the sprite frame a model is previewed against, set by build via sprite['_preview']."""
    return sprite.get("_preview", {}).get(model)


def subset(sprite, frames):
    """The sprite's `sprites` list restricted to these sheet frame numbers."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out
