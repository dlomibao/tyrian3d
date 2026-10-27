"""Helpers shared by batch b080's enemy scripts (build-models.sh skips lib_ modules).

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y.
- Mats: palette materials created on demand, one slot per (index, finish).
- Mesh builders that tag each face flat or smooth: ring lofts along any path, tubes along X or Y,
  ellipsoids and domes, prisms (extruded outlines) and boxes.
- to_object keeps each face's own smooth flag; preview renders a model beside its sprite.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    """Pixel grid of w x h pixels centred on the origin: x(c) is the centre of column c, y(r) the
    centre of row r (sprite up is +Y). Fractions are allowed; x(c - 0.5) is the left edge of c."""

    def __init__(self, w=24, h=28, ox=0.0, oy=0.0):
        self.w, self.h, self.ox, self.oy = w, h, ox, oy

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U + self.ox

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U + self.oy


class Mats:
    """Palette materials, one slot per (palette index, finish), made on demand. `colors` maps
    index -> RGB (merge several sprites' `colors` for an assembly)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.3, roughness=0.5, emission_strength=0.0, frames=None, part=None):
        """`frames` ({sprite frame: palette index}) animates the colour (common.palette_material);
        such a material is named after `part` (pal_<index>_<tag>_<part>), so give each its own."""
        key = (index, metallic, roughness, emission_strength)
        if frames:
            key += (part, tuple(sorted(frames.items())))
        if key not in self.slots:
            if frames:
                tag = f"{self.tag}_{part}"
            else:
                n = sum(1 for k in self.slots if k[0] == index and len(k) == 4)
                tag = self.tag if n == 0 else f"{self.tag}_{n}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness,
                                                     emission_strength=emission_strength, frames=frames))
        return self.slots[key]


def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def ring_loft(bm, rings, mat=0, smooth=True, cap_start=True, cap_end=True):
    """Join rings of points (lists of equal length, or a single point for a tip) with quads."""
    vrings = [[bm.verts.new(Vector(p)) for p in ring] for ring in rings]
    faces = []
    for r0, r1 in zip(vrings, vrings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(f))
    if cap_start and len(vrings[0]) > 2:
        faces.append(bm.faces.new(list(reversed(vrings[0]))))
    if cap_end and len(vrings[-1]) > 2:
        faces.append(bm.faces.new(vrings[-1]))
    return _faces(bm, faces, mat, smooth)


def ellipse_ring(centre, a_vec, b_vec, sides, phase=0.5, power=1.0):
    """Points round an ellipse: centre + a_vec cos t + b_vec sin t. power < 1 squares it off."""
    pts = []
    for i in range(sides):
        t = 2 * math.pi * (i + phase) / sides
        c, s = math.cos(t), math.sin(t)
        if power != 1.0:
            c = math.copysign(abs(c) ** power, c)
            s = math.copysign(abs(s) ** power, s)
        pts.append(Vector(centre) + Vector(a_vec) * c + Vector(b_vec) * s)
    return pts


def tube_x(bm, sections, sides=12, mat=0, smooth=True, power=1.0, cap_start=True, cap_end=True):
    """A loft along X: sections are (x, y_centre, half_y, z_centre, half_z) in units. Zero size
    collapses to a point."""
    rings = []
    for x, yc, hy, zc, hz in sections:
        if hy == 0 and hz == 0:
            rings.append([(x, yc, zc)])
        else:
            rings.append(ellipse_ring((x, yc, zc), (0, -hy, 0), (0, 0, hz), sides, power=power))
    return ring_loft(bm, rings, mat, smooth, cap_start, cap_end)


def tube_y(bm, sections, sides=12, mat=0, smooth=True, power=1.0, cap_start=True, cap_end=True):
    """A loft along Y: sections are (y, x_centre, half_x, z_centre, half_z) in units."""
    rings = []
    for y, xc, hx, zc, hz in sections:
        if hx == 0 and hz == 0:
            rings.append([(xc, y, zc)])
        else:
            rings.append(ellipse_ring((xc, y, zc), (hx, 0, 0), (0, 0, hz), sides, power=power))
    return ring_loft(bm, rings, mat, smooth, cap_start, cap_end)


def tube_z(bm, sections, sides=12, mat=0, smooth=True, power=1.0, cap_start=True, cap_end=True,
           angle=0.0):
    """A loft up Z: sections are (z, x_centre, y_centre, half_x, half_y), rotated by `angle`."""
    ca, sa = math.cos(angle), math.sin(angle)
    rings = []
    for z, xc, yc, hx, hy in sections:
        if hx == 0 and hy == 0:
            rings.append([(xc, yc, z)])
        else:
            rings.append(ellipse_ring((xc, yc, z), (hx * ca, hx * sa, 0), (-hy * sa, hy * ca, 0),
                                      sides, power=power))
    return ring_loft(bm, rings, mat, smooth, cap_start, cap_end)


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a 3D path of (x, y, z, half_width, half_height): rings stand perpendicular to
    the path; width is across the path in XY (or X for a vertical path) and height is the
    remaining perpendicular. Zero size collapses to a point."""
    pts = [Vector(p[:3]) for p in path]
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
        side = t.cross(ref).normalized()
        up = side.cross(t).normalized()
        if w == 0 and h == 0:
            rings.append([pts[i]])
        else:
            rings.append(ellipse_ring(pts[i], side * w, up * h, sides))
    return ring_loft(bm, rings, mat, smooth, cap_start, cap_end)


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, smooth=True, zmin=None):
    """An ellipsoid; with zmin, vertices below it are flattened onto it (a dome on a base)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        co = Vector((centre[0] + v.co.x * radii[0], centre[1] + v.co.y * radii[1],
                     centre[2] + v.co.z * radii[2]))
        if zmin is not None and co.z < zmin:
            co.z = zmin
        v.co = co
    return _faces(bm, list(set(bm.faces) - before), mat, smooth)


def dome(bm, centre, radii, mat=0, segments=16, rings=5, smooth=True, power=1.0):
    """A half ellipsoid standing on z = centre.z with a flat base (radii x, y, height)."""
    cx, cy, cz = centre
    rs = []
    for k in range(rings):
        a = (math.pi / 2) * k / rings
        r, z = math.cos(a), math.sin(a)
        if power != 1.0:
            z = z ** power
        rs.append(ellipse_ring((cx, cy, cz + z * radii[2]), (radii[0] * r, 0, 0), (0, radii[1] * r, 0),
                               segments))
    rs.append([(cx, cy, cz + radii[2])])
    return ring_loft(bm, rs, mat, smooth, cap_start=True, cap_end=False)


def prism(bm, outline, z0, z1, mat=0, smooth=False, top_mat=None):
    """Extrude an XY outline (counter-clockwise seen from above, units) from z0 to z1."""
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    top = [bm.verts.new((x, y, z1)) for x, y in outline]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    _faces(bm, faces, mat, smooth)
    if top_mat is not None:
        faces[0].material_index = top_mat
    return faces


def bevel_prism(bm, outline, z0, z1, inset, mat=0, top_mat=None, smooth=False):
    """A prism whose top edge is chamfered: the top face is the outline inset by `inset` units,
    `inset` below z1 the full outline. Outline counter-clockwise."""
    inner = inset_polygon(outline, inset)
    rings = [[(x, y, z0) for x, y in outline], [(x, y, z1 - inset) for x, y in outline],
             [(x, y, z1) for x, y in inner]]
    faces = ring_loft(bm, rings, mat, smooth)
    if top_mat is not None:
        faces[-1].material_index = top_mat
    return faces


def inset_polygon(poly, d):
    """Offset a counter-clockwise polygon inwards by d (simple miter)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        m = (n0 + n1)
        if m.length < 1e-6:
            m = n0
        m.normalize()
        k = d / max(m.dot(n0), 0.3)
        q = p1 + m * k
        out.append((q.x, q.y))
    return out


def rounded_rect(x0, y0, x1, y1, r, n=3):
    """Counter-clockwise outline of a rectangle with rounded corners (radius r, n steps each)."""
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ellipse_outline(cx, cy, rx, ry, n=16):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    return prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat)


def transform(bm, first_vert, matrix):
    """Apply a 4x4 matrix to every vertex added since index first_vert."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[first_vert:]:
        v.co = matrix @ v.co


def rotate_z(bm, first_vert, angle, cx=0.0, cy=0.0):
    m = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(angle, 4, "Z") @ Matrix.Translation((-cx, -cy, 0))
    transform(bm, first_vert, m)


def mirror_x(bm, first_vert=0, axis=0.0):
    """Add a mirror image about x = axis of the geometry whose verts start at first_vert."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[first_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
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


def faces_of(objs):
    return sum(len(o.data.polygons) for o in objs)


def preview(objs, root, name, sprite, frame=0, out=None):
    """If the script was run with -- --preview <png>, render objs beside the sprite's frame."""
    if out is None:
        if "--preview" not in sys.argv:
            return
        out = sys.argv[sys.argv.index("--preview") + 1]
    f = sprite["frames"][frame]
    ref = Path(root) / "reference" / "models" / name / f["image"]
    common.render_preview(objs, str(out), str(ref), size=f["size"])
