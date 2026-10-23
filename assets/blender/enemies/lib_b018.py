"""Helpers shared by batch b018's model scripts (newshh brown pods, grey gunship, eye block and
the horned head of level 2.2).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left
or top edge of column c / row r), for a 24x28 block.
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


def _mark(bm, faces_before, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[faces_before:]:
        f.material_index = mat
        f.smooth = smooth


def row_outline(pixels, keep, rows=None, w=24, h=28, inset=0.0):
    """A counter-clockwise (seen from above) polygon round the pixels for which keep(r, c, v) is
    true, from each row's leftmost and rightmost kept pixel (fine for shapes that are convex along
    rows). One vertex per row and side at the row's centre, plus the top and bottom edges.
    `inset` (pixels) pulls each side inward."""
    spans = []
    for r, line in enumerate(pixels):
        if rows is not None and r not in rows:
            continue
        cols = [c for c, v in enumerate(line) if keep(r, c, v)]
        if cols:
            spans.append((r, min(cols), max(cols) + 1))
    left, right = [], []
    for i, (r, c0, c1) in enumerate(spans):
        ys = [r + 0.5]
        if i == 0:
            ys = [r + 0.02, r + 0.5]
        if i == len(spans) - 1:
            ys = [r + 0.5, r + 0.98]
        for y in ys:
            left.append((ex(c0 + inset, w), ey(y, h)))
            right.append((ex(c1 - inset, w), ey(y, h)))
    return left + list(reversed(right))


def chaikin(points, rounds=1):
    """Round off a closed polygon's corners by corner cutting."""
    pts = [Vector(p) for p in points]
    for _ in range(rounds):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append(p.lerp(q, 0.25))
            out.append(p.lerp(q, 0.75))
        pts = out
    return [tuple(p) for p in pts]


def pillow(bm, outline, centre, z_mid, top, bottom, rings_top=4, rings_bottom=2, mat=0, mat_bottom=None,
           smooth=True, power=2.0, height_at=None, wall=0.0):
    """A rounded solid whose top view is `outline` (counter-clockwise XY points): rings of the
    outline shrunk toward `centre` (x, y), rising to `top` above z_mid and falling to `bottom` below.
    `power` shapes the dome (2 = round, higher = flatter top with steeper sides). `height_at(x, y)`
    optionally scales the height at each outline point (for a ridge or a slope). `wall` adds a
    vertical band of that height at the rim before the dome starts."""
    cx, cy = centre
    f0 = len(bm.faces)

    def ring(s, z_scale, sign):
        pts = []
        for x, y in outline:
            hx = height_at(x, y) if height_at else 1.0
            h = (top if sign > 0 else bottom) * hx
            pts.append(bm.verts.new((cx + (x - cx) * s, cy + (y - cy) * s,
                                     z_mid + sign * (wall / 2 + h * z_scale))))
        return pts

    def profile(k, n):
        # s from 1 (rim) to 0 (centre); z = (1 - s^p)^(1/p)
        t = k / n
        a = t * math.pi / 2
        s = math.cos(a)
        z = math.sin(a)
        if power != 2.0:
            s = abs(math.cos(a)) ** (2 / power)
            z = abs(math.sin(a)) ** (2 / power)
        return s, z

    tops = [ring(*profile(k, rings_top), 1) for k in range(rings_top)]
    first = 0 if wall else 1  # without a wall the bottom shares the top's rim
    bots = ([] if wall else [tops[0]]) + [ring(*profile(k, rings_bottom), -1) for k in range(first, rings_bottom)]
    top_pt = bm.verts.new((cx, cy, z_mid + wall / 2 + top))
    bot_pt = bm.verts.new((cx, cy, z_mid - wall / 2 - bottom))
    n = len(outline)

    def band(r0, r1, m):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = m
            f.smooth = smooth

    def fan(r, p, m, flip):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r[i], r[j], p) if not flip else (r[j], r[i], p))
            f.material_index = m
            f.smooth = smooth

    mb = mat if mat_bottom is None else mat_bottom
    for a, b in zip(tops, tops[1:]):
        band(a, b, mat)
    fan(tops[-1], top_pt, mat, False)
    if wall:
        band(bots[0], tops[0], mat)
    for a, b in zip(bots, bots[1:]):
        band(b, a, mb)
    fan(bots[-1], bot_pt, mb, True)
    return f0


def ellipsoid(bm, centre, radii, mat=0, segments=12, rings=6, smooth=True, rot=None):
    f0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        p = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
        if rot is not None:
            p = rot @ p
        v.co = Vector(centre) + p
    _mark(bm, f0, mat, smooth)


def dome(bm, centre, radii, mat=0, segments=16, rings=4, smooth=True, base=True):
    """Upper half of an ellipsoid sitting at centre z (radii x, y, height)."""
    cx, cy, cz = centre
    f0 = len(bm.faces)
    rs = []
    for k in range(rings):
        a = k / rings * math.pi / 2
        rs.append([bm.verts.new((cx + radii[0] * math.cos(a) * math.cos(t), cy + radii[1] * math.cos(a) * math.sin(t),
                                 cz + radii[2] * math.sin(a)))
                   for t in (2 * math.pi * (i + 0.5) / segments for i in range(segments))])
    top = bm.verts.new((cx, cy, cz + radii[2]))
    for a, b in zip(rs, rs[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for i in range(segments):
        bm.faces.new((rs[-1][i], rs[-1][(i + 1) % segments], top))
    if base:
        bm.faces.new(list(reversed(rs[0])))
    _mark(bm, f0, mat, smooth)


def ring_loft(bm, rings, mat=0, cap_start=True, cap_end=True, smooth=True):
    """Join rings of 3D points (same length, or a single point for a tip) in order."""
    f0 = len(bm.faces)
    verts = [[bm.verts.new(p) for p in r] for r in rings]
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face)
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0])))
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1])
    _mark(bm, f0, mat, smooth)


def tube(bm, points, radii, sides=8, mat=0, flat=1.0, caps=True, smooth=True):
    """A round tube along a 3D polyline with mitred joints. `radii` is a number or one per point
    (0 makes a pointed end). `flat` squashes the tube's height (z-ish direction) by that factor."""
    pts = [Vector(p) for p in points]
    radii = radii if isinstance(radii, (list, tuple)) else [radii] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    rings = []
    for c, t, r in zip(pts, tangents, radii):
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized()
        v = u.cross(t).normalized()
        if r == 0:
            rings.append([tuple(c)])
            continue
        rings.append([tuple(c + r * (math.cos(a) * u + flat * math.sin(a) * v))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    ring_loft(bm, rings, mat, cap_start=caps, cap_end=caps, smooth=smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    f0 = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _mark(bm, f0, mat, smooth)


def mirror_new(bm, v0, f0, axis_x=0.0):
    """Duplicate everything added since vertex v0 / face f0 mirrored about X = axis_x."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    faces = bm.faces[f0:]
    verts = bm.verts[v0:]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(faces))["geom"]
    for e in dup:
        if isinstance(e, bmesh.types.BMVert):
            e.co.x = 2 * axis_x - e.co.x
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


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview the first.

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
            target = out if i == 0 else out.parent / f"{model}.png"
            common.render_preview(objects, str(target), ref, size=frame["size"])
    return sprite


def surface_z(outline, centre, z_mid, top, x, y, power=2.0):
    """Height of a pillow's top (same outline, centre, z_mid, top, power) above point (x, y):
    finds how far (x, y) lies from the centre toward the outline along its ray."""
    cx, cy = centre
    dx, dy = x - cx, y - cy
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return z_mid + top
    ux, uy = dx / d, dy / d
    best = None
    n = len(outline)
    for i in range(n):
        ax, ay = outline[i][0] - cx, outline[i][1] - cy
        bx, by = outline[(i + 1) % n][0] - cx, outline[(i + 1) % n][1] - cy
        ex_, ey_ = bx - ax, by - ay
        den = ux * ey_ - uy * ex_
        if abs(den) < 1e-12:
            continue
        t = (ax * ey_ - ay * ex_) / den
        u = (ax * uy - ay * ux) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9:
            best = t if best is None else min(best, t)
    if best is None:
        return z_mid
    s = min(d / best, 1.0)
    # invert the profile: s = cos(a)^(2/p), z = sin(a)^(2/p)
    a = math.acos(s ** (power / 2))
    return z_mid + top * abs(math.sin(a)) ** (2 / power)


def pixel_keep(pixels, cols=None, rows=None, skip=(-1, 1)):
    """A keep(r, c, v) function for row_outline: pixels not in `skip`, optionally limited to
    column/row ranges."""
    def keep(r, c, v):
        if v in skip:
            return False
        if cols is not None and c not in cols:
            return False
        if rows is not None and r not in rows:
            return False
        return True
    return keep


def row_spans(pixels, keep, rows, inset=0.0, w=24):
    """{row: (centre_x, half_width)} in Blender units from each row's leftmost and rightmost kept
    pixel; `inset` (pixels) pulls each side in (negative pushes out)."""
    spans = {}
    for r in rows:
        cols = [c for c, v in enumerate(pixels[r]) if keep(r, c, v)]
        if cols:
            a, b = ex(min(cols) + inset, w), ex(max(cols) + 1 - inset, w)
            spans[r] = ((a + b) / 2, (b - a) / 2)
    return spans


def section_ring(xc, y, hw, z_mid, top, bottom, sides=16, keel=1.6, fullness=0.7, belly=0.5):
    """One cross-section (points in XZ at height y) of a hull: the top rises to a central ridge
    (`keel` is the exponent of |t|: 2 is round, nearer 1 is a sharper ridge; `fullness` < 1 makes
    the shoulders fuller), the bottom is a flatter curve (`belly`)."""
    pts = []
    for k in range(sides):
        a = 2 * math.pi * (k + 0.5) / sides
        t = math.cos(a)
        if math.sin(a) >= 0:
            z = z_mid + top * max(0.0, 1 - abs(t) ** keel) ** fullness
        else:
            z = z_mid - bottom * max(0.0, 1 - t * t) ** belly
        pts.append((xc + hw * t, y, z))
    return pts


def resample(points, n):
    """A closed polygon resampled to n points evenly spaced along its perimeter."""
    pts = [Vector((p[0], p[1])) for p in points]
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    lens = [(b - a).length for a, b in segs]
    total = sum(lens)
    out, i, acc = [], 0, 0.0
    for k in range(n):
        d = total * k / n
        while acc + lens[i] < d and i < len(segs) - 1:
            acc += lens[i]
            i += 1
        a, b = segs[i]
        t = (d - acc) / lens[i] if lens[i] else 0.0
        p = a.lerp(b, t)
        out.append((p.x, p.y))
    return out


def smooth_outline(pixels, keep, rows=None, inset=-0.3, n=56, rounds=2, w=24, h=28):
    """row_outline, rounded by corner cutting and resampled to n points."""
    return resample(chaikin(row_outline(pixels, keep, rows=rows, w=w, h=h, inset=inset), rounds), n)
