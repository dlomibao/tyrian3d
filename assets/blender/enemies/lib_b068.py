"""Helpers shared by batch b068's model scripts (newsh5 ground objects of episode 4).

Not a model script itself: tools/build-models.sh skips lib_ files.
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


def X(c, w=24):
    """Sprite column (pixel centre; fractions allowed) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def Y(r, h=28):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def EX(e, w=24):
    """Pixel edge (column boundary) to Blender X."""
    return (e - w / 2) / 12


def EY(e, h=28):
    """Pixel edge (row boundary) to Blender Y."""
    return (h / 2 - e) / 12


def set_faces(bm, first, mat=None, smooth=None):
    """Set material and/or smooth flag on every face added since index `first`."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        if mat is not None:
            f.material_index = mat
        if smooth is not None:
            f.smooth = smooth


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def rotate_z(bm, start, angle, cx=0.0, cy=0.0):
    """Rotate every vertex added since `start` about the Z axis through (cx, cy), radians CCW."""
    bm.verts.ensure_lookup_table()
    c, s = math.cos(angle), math.sin(angle)
    for v in bm.verts[start:]:
        x, y = v.co.x - cx, v.co.y - cy
        v.co.x, v.co.y = cx + x * c - y * s, cy + x * s + y * c


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, angle=0.0, floor=None, smooth=True):
    """An ellipsoid with semi-axes `radii` (units), turned by `angle` about Z. With `floor` set,
    vertices below that height are pressed flat onto it (a dome sitting on the ground)."""
    f0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    c, s = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        x, y, z = v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]
        v.co = Vector((centre[0] + x * c - y * s, centre[1] + x * s + y * c, centre[2] + z))
        if floor is not None and v.co.z < floor:
            v.co.z = floor
    set_faces(bm, f0, mat, smooth)


def blob(bm, centre, radii, mat=0, segments=16, rings=8, power=1.0, angle=0.0, floor=None, smooth=True):
    """A superellipsoid: power < 1 squares it off (0.5 is a rounded box), 1 is an ellipsoid."""
    f0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    c, s = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        x, y, z = (math.copysign(abs(q) ** power, q) * r for q, r in zip(v.co, radii))
        v.co = Vector((centre[0] + x * c - y * s, centre[1] + x * s + y * c, centre[2] + z))
        if floor is not None and v.co.z < floor:
            v.co.z = floor
    set_faces(bm, f0, mat, smooth)


def ellipsoid_z(centre, radii, angle, x, y, floor=0.0):
    """Height of the top of an ellipsoid (as built by `ellipsoid`) above point (x, y)."""
    c, s = math.cos(-angle), math.sin(-angle)
    dx, dy = x - centre[0], y - centre[1]
    lx, ly = dx * c - dy * s, dx * s + dy * c
    t = 1 - (lx / radii[0]) ** 2 - (ly / radii[1]) ** 2
    if t <= 0:
        return floor
    return max(floor, centre[2] + radii[2] * math.sqrt(t))


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True, phase=0.5):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path in XY; the width is across the path and the height along Z. A ring
    of zero size collapses to a point. phase=0 with 4 sides gives a diamond section (a ridge on
    top and a keel below)."""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    f0 = len(bm.faces)
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
    set_faces(bm, f0, mat, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an XY outline (units, any winding) from z0 to z1."""
    f0 = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    set_faces(bm, f0, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def radial(poly, cx, cy, n, phase=0.5):
    """Points where rays from (cx, cy) at n even angles meet a closed polygon's boundary, so that
    loops of different shapes (an octagon, an ellipse) get matching vertices for `terraces`."""
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + phase) / n
        dx, dy = math.cos(a), math.sin(a)
        best = None
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = ((x0 - cx) * ey - (y0 - cy) * ex) / den
            u = ((x0 - cx) * dy - (y0 - cy) * dx) / den
            if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
                best = t
        out.append((cx + dx * best, cy + dy * best))
    return out


def ellipse_pts(cx, cy, rx, ry, n, phase=0.5):
    return [(cx + rx * math.cos(2 * math.pi * (k + phase) / n), cy + ry * math.sin(2 * math.pi * (k + phase) / n))
            for k in range(n)]


def terraces(bm, loops, mats, cap_bottom=None, cap_top=None):
    """Join loops of (x, y, z) points (all the same length, same winding) with bands of quads:
    band i between loops i and i+1 gets material mats[i]. Caps close the first and last loop
    with an n-gon of the given material (None leaves it open)."""
    vloops = [[bm.verts.new(p) for p in loop] for loop in loops]
    n = len(loops[0])
    for i, (a, b) in enumerate(zip(vloops, vloops[1:])):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = mats[i]
    if cap_bottom is not None:
        bm.faces.new(list(reversed(vloops[0]))).material_index = cap_bottom
    if cap_top is not None:
        bm.faces.new(vloops[-1]).material_index = cap_top


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


def frame_subset(sprite, frames):
    """sprite["sprites"] cut down to the given frame indices (for animations needing several models)."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def export_frames(root, name, sprite, models, extra_preview=True):
    """Export one model per frame group. `models` is a list of (object, [frame indices]); the
    first is `name`, the rest `name-f2`, `name-f3`, ... With --preview, the first model's preview
    goes to the given path and the others' beside it as <name>-fN.png."""
    out = preview_arg()
    for i, (obj, frames) in enumerate(models):
        model_name = name if i == 0 else f"{name}-f{i + 1}"
        common.export_sprite_model(root, [obj], f"enemies/{model_name}", frame_subset(sprite, frames))
        if out:
            frame = next(f for f in sprite["frames"] if f["index"] == frames[0])
            ref = Path(root) / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.parent / f"{model_name}.png"
            common.render_preview([obj], str(path), ref, size=frame["size"])


def resample(poly, step):
    """A closed polygon with extra points so no edge is longer than `step` (corners are kept)."""
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
        out.extend((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n))
    return out


def toward_ellipse(points, cx, cy, rx, ry, scale=1.0):
    """For each point, the point on the ellipse (centre cx, cy) in the same direction from the
    centre: an inner loop with one vertex per outer vertex, for `terraces`."""
    out = []
    for x, y in points:
        a = math.atan2(y - cy, x - cx)
        r = scale / math.sqrt((math.cos(a) / rx) ** 2 + (math.sin(a) / ry) ** 2)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def pull(points, cx, cy, d):
    """Move each point `d` units toward (cx, cy) (a rough inset for a bevel)."""
    out = []
    for x, y in points:
        dx, dy = cx - x, cy - y
        n = math.hypot(dx, dy) or 1.0
        out.append((x + dx / n * d, y + dy / n * d))
    return out


def at_z(points, z):
    return [(x, y, z) for x, y in points]
