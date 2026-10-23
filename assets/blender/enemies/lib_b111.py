"""Helpers shared by batch b111's enemy scripts (newshv ground objects from episode 2).

Not a model itself: build-models.sh skips lib_ files.
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    """Sprite column (pixel centre) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    """Sprite column edge (left edge of column c) to Blender X."""
    return (c - w / 2) / 12


def ey(r, h=28):
    """Sprite row edge (top edge of row r) to Blender Y."""
    return (h / 2 - r) / 12


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


def mirror_all_x(bm):
    """Mirror the whole mesh left to right (flips face winding back afterwards)."""
    for v in bm.verts:
        v.co.x = -v.co.x
    for f in bm.faces:
        f.normal_flip()


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box."""
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude an outline (counter-clockwise from above) from z0 to z1."""
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def revolve(bm, profile, sides, mat_of, cx=0.0, cy=0.0, angle0=0.0, sx=1.0, sy=1.0, cap_bottom=True):
    """A solid of revolution around a vertical axis at (cx, cy). `profile` is [(radius, z), ...]
    from bottom to top; a radius of 0 is a point (a tip). mat_of(ring, seg) picks each band's
    material slot (ring = index of the band's lower profile point, seg = segment around).
    sx, sy stretch it into an ellipse. Returns the first face index."""
    first = len(bm.faces)
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((cx, cy, z))])
            continue
        ring = []
        for i in range(sides):
            a = angle0 + 2 * math.pi * i / sides
            ring.append(bm.verts.new((cx + sx * r * math.cos(a), cy + sy * r * math.sin(a), z)))
        rings.append(ring)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[i], r1[j])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat_of(k, i)
    if cap_bottom and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_of(0, 0)
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_of(len(rings) - 1, 0)
    return first


def loft_x(bm, sections, sides=8, mat_index=0, cap_start=True, cap_end=True, y=0.0):
    """Loft rings along +X. Each section is (x, half_width_y, half_height_z, z_centre)."""
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    # loft builds along Y with width on X: swap X and Y (a mirror, so flip the faces back).
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x, v.co.y = v.co.y, v.co.x + y
    return start


def set_smooth(bm, first_face, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.smooth = smooth


def mesh_object_mixed(name, bm, materials, collection):
    """Like common.mesh_object but keeps each face's own smooth flag."""
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


def run(root, name, build, sprite=None):
    """Load the sprite, build, export enemies/<name> and render the preview if asked."""
    sprite = sprite or common.load_sprite(root, name)
    obj = build(sprite)
    objs = obj if isinstance(obj, list) else [obj]
    common.export_sprite_model(root, objs, f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"])


def _tangents(pts):
    from mathutils import Vector
    vs = [Vector(p) for p in pts]
    out = []
    for i in range(len(vs)):
        a = vs[max(i - 1, 0)]
        b = vs[min(i + 1, len(vs) - 1)]
        out.append((b - a).normalized())
    return vs, out


def tube_path(bm, pts, radii, sides=8, mat_index=0, flat=1.0, cap=True):
    """A tube along a 3D polyline `pts`, radius per point (a list or one number); `flat` scales the
    section's vertical axis. A radius of 0 ends in a point."""
    from mathutils import Vector
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    vs, ts = _tangents(pts)
    rings = []
    for p, t, r in zip(vs, ts, radii):
        if r == 0:
            rings.append([bm.verts.new(p)])
            continue
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(t).normalized()
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ring.append(bm.verts.new(p + r * math.cos(a) * side + r * flat * math.sin(a) * up))
        rings.append(ring)
    _bridge(bm, rings, sides, mat_index, cap)


def _bridge(bm, rings, sides, mat_index, cap, closed=True):
    for r0, r1 in zip(rings, rings[1:]):
        n = sides if closed else sides - 1
        for i in range(n):
            j = (i + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat_index
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1]).material_index = mat_index


def sweep_xy(bm, path, half_widths, heights, profile, mat_index=0, z0=0.0, offset=0.0):
    """Sweep a cross-section along a path in the XY plane (a ground-hugging band: hoods, walls,
    ridges). `profile` is a closed list of (u, v): u in [-1, 1] across the band (+1 is to the left
    of travel), v in [0, 1] up; each point lands at path + normal * (offset + u * half_width),
    z = z0 + v * height."""
    from mathutils import Vector
    pts = [(x, y, 0.0) for x, y in path]
    vs, ts = _tangents(pts)
    rings = []
    for p, t, hw, h in zip(vs, ts, half_widths, heights):
        n = Vector((-t.y, t.x, 0.0)).normalized()
        rings.append([bm.verts.new(p + n * (offset + u * hw) + Vector((0, 0, z0 + v * h))) for u, v in profile])
    _bridge(bm, rings, len(profile), mat_index, True)


def clamp_z(bm, start, zmin=0.0):
    """Flatten every vertex added since `start` that dips below zmin (a flat base on the ground)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        if v.co.z < zmin:
            v.co.z = zmin
