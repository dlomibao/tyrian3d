"""Helpers shared by batch b070's enemy scripts (build-models.sh skips lib_ modules).

Some are copied from lib_b006 (Grid, Mats, paint, blob, tube); the rest are this batch's own:
- dome: a half ellipsoid on a flat base (pods, rocks and caps that sit on the ground), optionally
  sheared so its base tilts.
- crater: a ring wall round an open middle, from an outer and an inner outline.
- to_object: like common.mesh_object, but keeps each face's own smooth flag.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    """Pixel grid of width w and height h (pixels), centred on the origin: column c, row r (pixel
    centres at c + 0.5, r + 0.5) map to X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12. Fractional
    columns/rows are allowed; x(c) is the centre of column c."""

    def __init__(self, w, h, pixels=None):
        self.w, self.h, self.pixels = w, h, pixels

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U

    def col(self, x):
        return x / U + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - y / U

    def sample(self, x, y, skip=(-1,), reach=2):
        """The palette index of the pixel under (x, y); `skip` pixels are passed over for the
        nearest other pixel within `reach` pixels (None if there is none)."""
        if self.pixels is None:
            return None
        c, r = int(round(self.col(x))), int(round(self.row(y)))
        best = None
        for d in range(reach + 1):
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    if max(abs(dr), abs(dc)) != d:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < self.h and 0 <= cc < self.w:
                        v = self.pixels[rr][cc]
                        if v not in skip:
                            dist = dr * dr + dc * dc
                            if best is None or dist < best[0]:
                                best = (dist, v)
            if best is not None:
                return best[1]
        return None


class Mats:
    """Palette materials, one slot per (palette index, finish). `colors` maps index -> RGB (merge
    several sprites' `colors` for an assembly)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.3, roughness=0.5, emission_strength=0.0):
        key = (index, metallic, roughness, emission_strength)
        if key not in self.slots:
            tag = self.tag if not emission_strength else f"{self.tag}_glow"
            if any(k[0] == index and k != key for k in self.slots):
                tag = f"{self.tag}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[key]


def paint(bm, first_face, grid, slot_for, up_only=True, skip=(-1,)):
    """Set the material of every face added since face index `first_face` from the sprite pixel
    under its centre: slot_for(palette_index) -> material slot (or None to leave it). With up_only,
    faces pointing down keep their material."""
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    for f in bm.faces[first_face:]:
        if up_only and f.normal.z < -0.2:
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y, skip=skip)
        if idx is None:
            continue
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def blob(bm, centre, radii, segments=16, rings=10, mat_index=0, smooth=True):
    """A UV ellipsoid at `centre` (units) with radii (rx, ry, rz). Returns its first face index."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    cx, cy, cz = centre
    rx, ry, rz = radii
    top = bm.verts.new((cx, cy, cz + rz))
    bottom = bm.verts.new((cx, cy, cz - rz))
    ring_verts = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        ring_verts.append([bm.verts.new((cx + rx * math.sin(phi) * math.cos(2 * math.pi * j / segments),
                                         cy + ry * math.sin(phi) * math.sin(2 * math.pi * j / segments),
                                         cz + rz * math.cos(phi))) for j in range(segments)])
    faces = []
    for j in range(segments):
        k = (j + 1) % segments
        faces.append(bm.faces.new((top, ring_verts[0][j], ring_verts[0][k])))
        faces.append(bm.faces.new((bottom, ring_verts[-1][k], ring_verts[-1][j])))
    for a, b in zip(ring_verts, ring_verts[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append(bm.faces.new((a[j], b[j], b[k], a[k])))
    for f in faces:
        f.material_index = mat_index
        f.smooth = smooth
    return first


def dome(bm, centre, radii, segments=20, rings=6, mat_index=0, shear=(0.0, 0.0), power=1.0,
         base=True, smooth=True, angle=0.0):
    """A half ellipsoid on a flat base: centre (x, y, z0) is the middle of its base, radii
    (rx, ry, h). `shear` (dz per unit of x, y from the centre) tilts the whole dome, base included.
    `power` < 1 makes the profile fuller (flatter top, steeper sides), > 1 more pointed. `angle`
    turns the footprint (radians). Returns its first face index."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    cx, cy, cz = centre
    rx, ry, h = radii
    ca, sa = math.cos(angle), math.sin(angle)

    def at(u, v, z):
        x, y = u * ca - v * sa, u * sa + v * ca
        return (cx + x, cy + y, cz + z + shear[0] * x + shear[1] * y)

    ring_verts = []
    for i in range(rings):
        t = i / rings  # 0 at the base, up to the top
        phi = t * math.pi / 2
        s = math.cos(phi) ** power
        z = h * math.sin(phi)
        ring_verts.append([bm.verts.new(at(rx * s * math.cos(2 * math.pi * j / segments),
                                           ry * s * math.sin(2 * math.pi * j / segments), z))
                           for j in range(segments)])
    top = bm.verts.new(at(0.0, 0.0, h))
    faces = []
    for a, b in zip(ring_verts, ring_verts[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append(bm.faces.new((a[j], a[k], b[k], b[j])))
    for j in range(segments):
        k = (j + 1) % segments
        faces.append(bm.faces.new((ring_verts[-1][j], ring_verts[-1][k], top)))
    for f in faces:
        f.smooth = smooth
    if base:
        f = bm.faces.new(list(reversed(ring_verts[0])))
        f.smooth = False
        faces.append(f)
    for f in faces:
        f.material_index = mat_index
    return first


def dome_z(centre, radii, x, y, shear=(0.0, 0.0), power=1.0):
    """Height of a dome() surface above (x, y), or None outside it (power 1 only is exact)."""
    cx, cy, cz = centre
    rx, ry, h = radii
    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
    if d >= 1:
        return None
    return cz + shear[0] * (x - cx) + shear[1] * (y - cy) + h * math.sqrt(1 - d)


def crater(bm, outer, inner, profile, mat_index=0, smooth=True):
    """A ring wall: `outer` and `inner` are closed outlines with the same number of points (units,
    counter-clockwise from above). `profile` is a list of (t, z): t = 0 on the outer outline, 1 on
    the inner, z the height there (each a number, or a list with one value per outline point).
    Returns its first face index."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    n = len(outer)
    rows = []
    for t, z in profile:
        zs = z if isinstance(z, (list, tuple)) else [z] * n
        rows.append([bm.verts.new((outer[i][0] + (inner[i][0] - outer[i][0]) * t,
                                   outer[i][1] + (inner[i][1] - outer[i][1]) * t, zs[i])) for i in range(n)])
    rows.append(rows[0])  # close the bottom
    faces = []
    for a, b in zip(rows, rows[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in faces:
        f.material_index = mat_index
        f.smooth = smooth
    return first


def ellipse(cx, cy, rx, ry, n=24, start=0.0):
    """Points of an ellipse (counter-clockwise), in units."""
    return [(cx + rx * math.cos(start + 2 * math.pi * i / n), cy + ry * math.sin(start + 2 * math.pi * i / n))
            for i in range(n)]


def tube(bm, points, sides=8, mat_index=0, cap_start=True, cap_end=True, smooth=True):
    """A loft along any path: points are ((x, y, z), radius); radius 0 makes a point (a tip).
    Each ring is perpendicular to the path at that point."""
    pts = [(Vector(p), r) for p, r in points]
    rings = []
    for i, (p, r) in enumerate(pts):
        a = pts[max(0, i - 1)][0]
        b = pts[min(len(pts) - 1, i + 1)][0]
        d = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        w = d.cross(u).normalized()
        if r == 0:
            rings.append([bm.verts.new(p)])
            continue
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * (k + 0.5) / sides) * u +
                                            math.sin(2 * math.pi * (k + 0.5) / sides) * w))
                      for k in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                face = (r0[k], r0[j], r1[0])
            else:
                face = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(face))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat_index
        f.smooth = smooth


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


def preview(root, name, objs, sprite, frame=0):
    """Render the --preview PNG if the script was asked for one."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][frame]
        ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])
