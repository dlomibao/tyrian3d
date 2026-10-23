"""Helpers shared by batch b054's models: sprite coordinates, ellipsoids, tubes and cushions
placed anywhere, and per-face colours sampled from the sprite (several adapted from lib_b004).

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def dims(size):
    """Sprite block size in pixels (w, h) for size 1 or 2."""
    return (12, 14) if size == 1 else (24, 28)


def px(c, size=2):
    """Sprite column (pixel centre, or any fractional column) to Blender X."""
    w, _ = dims(size)
    return (c + 0.5 - w / 2) / 12


def row(r, size=2):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    _, h = dims(size)
    return (h / 2 - (r + 0.5)) / 12


def P(c, r, z=0.0, size=2):
    """A 3D point at sprite pixel centre (c, r) and height z."""
    return (px(c, size), row(r, size), z)


def sample(pixels, x, y, size=2):
    """The palette index of the sprite pixel under Blender (x, y), or -1 outside / transparent."""
    w, h = dims(size)
    c = int(math.floor(x * 12 + w / 2))
    r = int(math.floor(h / 2 - y * 12))
    if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
        return pixels[r][c]
    return -1


def ellipsoid(bm, centre, radii, segments=16, rings=10, mat_index=0, flat_bottom=None):
    """An ellipsoid at `centre` with semi-axes `radii` (x, y, z), lofted along Y. `flat_bottom`
    squashes its lower half to that fraction of its height."""
    a, b, c = radii
    sections = [(-b, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        t = math.pi * i / rings
        sections.append((-b * math.cos(t), a * math.sin(t), c * math.sin(t), 0.0))
    sections.append((b, 0.0, 0.0, 0.0))
    start = len(bm.verts)
    common.loft(bm, sections, sides=segments, mat_index=mat_index)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        if flat_bottom is not None and v.co.z < 0:
            v.co.z *= flat_bottom
        v.co += Vector(centre)


def transform_from(bm, start, matrix):
    """Apply a 4x4 matrix to every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts[start:])


def tube(bm, points, radii, sides=8, mat_index=0, flat=1.0, cap=True, widths=None):
    """A tube along a polyline of 3D points, with a radius per point (0 closes to a tip). `flat`
    squashes the cross-section in Z; `widths` (optional) gives a separate horizontal radius per
    point so a tube can be wide and low."""
    pts = [Vector(p) for p in points]
    widths = widths or radii
    rings = []
    for i, (p, rad, wid) in enumerate(zip(pts, radii, widths)):
        if rad == 0 and wid == 0:
            rings.append([bm.verts.new(p)])
            continue
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nup = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * math.cos(ang) * wid + nup * math.sin(ang) * rad * flat))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f).material_index = mat_index
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0]).material_index = mat_index
        if len(rings[-1]) > 1:
            bm.faces.new(list(reversed(rings[-1]))).material_index = mat_index


def chaikin(points, rounds=2, closed=True):
    """Round off a polyline's corners by corner cutting."""
    pts = [Vector(p) for p in points]
    for _ in range(rounds):
        out = []
        n = len(pts) if closed else len(pts) - 1
        if not closed:
            out.append(pts[0])
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append(p.lerp(q, 0.25))
            out.append(p.lerp(q, 0.75))
        if not closed:
            out.append(pts[-1])
        pts = out
    return [tuple(p) for p in pts]


def ccw(poly):
    """The polygon made counter-clockwise (seen from above)."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0, *_), (x1, y1, *_) in zip(poly, poly[1:] + poly[:1]))
    return list(reversed(poly)) if area < 0 else list(poly)


def inset_polygon(poly, d):
    """Move each vertex of a counter-clockwise polygon `d` units inward."""
    out = []
    n = len(poly)
    for i, (x, y, *_) in enumerate(poly):
        ax, ay = poly[i - 1][:2]
        bx, by = poly[(i + 1) % n][:2]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        out.append((x - ty / ln * d, y + tx / ln * d))
    return out


def edge_outline(points, size=2, rounds=2):
    """A counter-clockwise Blender polygon from pixel-edge (column, row) corners, rounded by
    corner cutting."""
    w, h = dims(size)
    pts = [((c - w / 2) / 12, (h / 2 - r) / 12) for c, r in points]
    return ccw(chaikin(pts, rounds=rounds))


def ellipse_polygon(cx, cy, rx, ry, n=16, tilt=0.0):
    ct, st = math.cos(tilt), math.sin(tilt)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ex, ey = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + ex * ct - ey * st, cy + ex * st + ey * ct))
    return pts


def cushion(bm, outline, z, top, bottom, bevel, steps=3, mat_index=0, side=0.0):
    """A flat-topped cushion over a counter-clockwise outline: straight sides `side` tall centred on
    `z`, then rounded shoulders (`steps` rings, inset up to `bevel` units) rising `top` above and
    sinking `bottom` below them, with flat caps inside."""
    rings_top, rings_bot = [], []
    for k in range(steps + 1):
        a = math.pi / 2 * k / steps
        inset = bevel * (1 - math.cos(a))
        poly = inset_polygon(outline, inset) if inset > 1e-6 else [p[:2] for p in outline]
        rings_top.append([bm.verts.new((x, y, z + side / 2 + top * math.sin(a))) for x, y in poly])
        rings_bot.append([bm.verts.new((x, y, z - side / 2 - bottom * math.sin(a))) for x, y in poly])
    n = len(outline)
    faces = []
    if side > 1e-6:
        r0, r1 = rings_bot[0], rings_top[0]
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for rings in (rings_top, rings_bot):
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
        faces.append(bm.faces.new(rings[-1]))
    if side <= 1e-6:
        # Weld the two rims together.
        bmesh.ops.remove_doubles(bm, verts=rings_top[0] + rings_bot[0], dist=1e-6)
    for f in faces:
        if f.is_valid:
            f.material_index = mat_index


def faces_from(bm, start):
    bm.faces.ensure_lookup_table()
    return bm.faces[start:]


def paint(bm, faces, pixels, slot_of, size=2, min_nz=0.0, under_slot=None, average=True):
    """Give each upward face the material slot of the sprite pixels under it (slot_of(index) ->
    slot or None to keep its own). `average` takes the mean index over the face, for shades of
    one ramp. Faces facing down (normal z < min_nz) get `under_slot` if given."""
    faces = list(faces)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.normal_update()
    for f in faces:
        if f.normal.z < min_nz:
            if f.normal.z < -0.1 and under_slot is not None:
                f.material_index = under_slot
            continue
        cen = f.calc_center_median()
        if average:
            pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
            vals = [sample(pixels, p.x, p.y, size) for p in pts]
            vals = [v for v in vals if v >= 0]
            idx = round(sum(vals) / len(vals)) if vals else -1
        else:
            idx = sample(pixels, cen.x, cen.y, size)
        slot = slot_of(idx)
        if slot is not None:
            f.material_index = slot


def ramp(table):
    """slot_of from [(lo, hi, slot), ...] ranges of palette indices."""
    def slot_of(i):
        for lo, hi, slot in table:
            if lo <= i <= hi:
                return slot
        return None
    return slot_of


def mirror_x(bm, start, end=None):
    """Duplicate the geometry added since `start` (faces only) mirrored in X."""
    bm.faces.ensure_lookup_table()
    faces = bm.faces[start:end]
    vmap = {}
    for f in faces:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
            vs.append(vmap[v])
        nf = bm.faces.new(list(reversed(vs)))
        nf.material_index = f.material_index


def preview(objs, sprite, root, name, frame=0):
    """Render the preview if the script was given `-- --preview <png>`."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][frame]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][frame]["size"])
