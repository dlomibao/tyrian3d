"""Helpers shared by batch b009's model scripts (newsh2 flyers of episodes 1 and 3).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block. ring_loft, tube and polyline_tube come from
lib_b007; ribbon, ellipsoid and the per-face smooth flag are this batch's.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

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


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True, cap_mats=None, smooth=False):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.

    `mats` gives a material index per band between consecutive rings (an int applies to all, a
    list of ints per band, or a list of lists per band and segment). Caps close the first/last ring
    (with cap_mats = (start, end) material indices, default the first/last band's)."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]

    def mat(band, seg):
        m = mats
        if isinstance(m, list):
            m = m[band]
        if isinstance(m, list):
            m = m[seg]
        return m

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
            f = bm.faces.new(face)
            f.material_index = mat(b, i)
            f.smooth = smooth
    first = mat(0, 0) if not cap_mats else cap_mats[0]
    last = mat(len(verts) - 2, 0) if not cap_mats else cap_mats[1]
    if cap_start and len(verts[0]) > 2:
        f = bm.faces.new(list(reversed(verts[0])))
        f.material_index = first
    if cap_end and len(verts[-1]) > 2:
        f = bm.faces.new(verts[-1])
        f.material_index = last
    return verts


def tube(bm, p0, p1, radius, sides=6, mat_index=0, caps=True, smooth=True):
    """A thin round bar between two 3D points (pipes, struts)."""
    a, b = Vector(p0), Vector(p1)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for c in (a, b):
        ring = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides
            ring.append(tuple(c + radius * (math.cos(t) * u + math.sin(t) * v)))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps, smooth=smooth)


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, smooth=True, flat=1.0):
    """One continuous round tube along a polyline, with mitred joints. `radius` can be a number or a
    list with one radius per point. `flat` squashes the cross-section along the frame's second axis."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for i, (c, t) in enumerate(zip(pts, tangents)):
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(c + radii[i] * (math.cos(a) * u + math.sin(a) * v * flat)))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps, smooth=smooth)


def ribbon(bm, path, half_w, half_d, mat_of, z=0.0, closed=False):
    """A flat band swept along a 2D path in the XY plane: `half_w` across the path in the plane,
    `half_d` along Z. mat_of(segment_index, midpoint, side) gives each face's material, side being
    "front" (+Z), "back" (-Z), "out" (left of the path) or "in". Flat shaded, mitred joints."""
    pts = [Vector((x, y)) for x, y in path]
    n = len(pts)
    rings = []
    for i in range(n):
        if closed:
            d0 = (pts[i] - pts[i - 1]).normalized()
            d1 = (pts[(i + 1) % n] - pts[i]).normalized()
        else:
            d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
            d1 = (pts[i + 1] - pts[i]).normalized() if i < n - 1 else None
            if d0 is None:
                d0 = d1
            if d1 is None:
                d1 = d0
        t = (d0 + d1).normalized()
        nrm = Vector((-t.y, t.x))
        scale = 1.0 / max(0.4, nrm.dot(Vector((-d1.y, d1.x))))
        o = nrm * half_w * scale
        p = pts[i]
        rings.append([bm.verts.new((p.x + o.x, p.y + o.y, z + half_d)),
                      bm.verts.new((p.x - o.x, p.y - o.y, z + half_d)),
                      bm.verts.new((p.x - o.x, p.y - o.y, z - half_d)),
                      bm.verts.new((p.x + o.x, p.y + o.y, z - half_d))])
    sides = ("front", "in", "back", "out")
    segs = n if closed else n - 1
    for s in range(segs):
        r0, r1 = rings[s], rings[(s + 1) % n]
        mid = (pts[s] + pts[(s + 1) % n]) / 2
        for k in range(4):
            j = (k + 1) % 4
            f = bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
            f.material_index = mat_of(s, mid, sides[k])
    if not closed:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mat_of(0, pts[0], "end")
        f = bm.faces.new(rings[-1])
        f.material_index = mat_of(segs - 1, pts[-1], "end")


def ellipsoid(bm, centre, radii, segments=16, rings=8, mat_index=0, smooth=True, z_cut=None):
    """An ellipsoid (rx, ry, rz) at centre, poles along Y. With z_cut, verts below that height
    (relative to the centre) are flattened onto it (a dome with a flat base)."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    ring_pts = [[(cx, cy + ry, cz)]]
    for i in range(1, rings):
        t = math.pi * i / rings
        ring = []
        for k in range(segments):
            a = 2 * math.pi * (k + 0.5) / segments
            z = rz * math.sin(t) * math.sin(a)
            if z_cut is not None:
                z = max(z, z_cut)
            ring.append((cx + rx * math.sin(t) * math.cos(a), cy + ry * math.cos(t), cz + z))
        ring_pts.append(ring)
    ring_pts.append([(cx, cy - ry, cz)])
    return ring_loft(bm, ring_pts, mat_index, smooth=smooth)


def transform_since(bm, start, matrix):
    bm.verts.ensure_lookup_table()
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts[start:])


def mirror_since(bm, start):
    """Duplicate everything added since vertex index `start`, mirrored in X."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    verts = set(bm.verts[start:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    mapping = {}
    for v in verts:
        mapping[v] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
    for f in faces:
        nf = bm.faces.new([mapping[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index
        nf.smooth = f.smooth


def finish(name, bm, materials, collection):
    """Turn a bmesh into an object keeping each face's own smooth flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def frames_subset(sprite, indices):
    """The sprite list with only the given frame indices (for one model of an animation)."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in indices]
        if keep:
            out.append({**s, "frames": keep})
    return out


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview each: the first model to
    <png>, the others to <png stem>-<suffix>.png, each beside the first frame it covers.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        by_index = {f["index"]: f for f in sprite["frames"]}
        for i, (model, objects, sprites) in enumerate(models):
            frame = by_index[sprites[0]["frames"][0]]
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.with_name(f"{out.stem}{model[len(name):]}.png")
            common.render_preview(objects, str(path), ref, size=frame["size"])
    return sprite


def rot_y(angle):
    return Matrix.Rotation(angle, 4, "Y")


def ellipse_ring(cx, cy, z, rx, ry, n=10, phase=0.5):
    """n points of an ellipse around (cx, cy) at height z (counter-clockwise from +X)."""
    return [(cx + rx * math.cos(2 * math.pi * (i + phase) / n), cy + ry * math.sin(2 * math.pi * (i + phase) / n), z)
            for i in range(n)]
