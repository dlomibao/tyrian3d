"""Helpers shared by batch b006's enemy scripts (build-models.sh skips lib_ modules).

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y.
- Mats: palette materials created on demand, one slot per palette index.
- paint: give faces the material of the sprite pixel under them (seen from above).
- blob: a lumpy ellipsoid (rocks, cores).
- box: an axis-aligned box from pixel bounds.
"""

import math
import sys
from pathlib import Path

import bmesh

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

    def sample(self, x, y, skip=(-1, 1), reach=2):
        """The palette index of the pixel under (x, y); transparent and outline pixels are skipped
        for the nearest other pixel within `reach` pixels (None if there is none)."""
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

    def __call__(self, index, metallic=0.3, roughness=0.5, emission_strength=0.0, frames=None):
        """`frames` animates the colour as in common.palette_material ({sprite frame: index})."""
        key = (index, metallic, roughness, emission_strength)
        if frames:
            key += (tuple(sorted(frames.items())),)
        if key not in self.slots:
            tag = self.tag if not emission_strength else f"{self.tag}_glow"
            if frames:
                tag += "_anim"
            if any(k[0] == index and k != key for k in self.slots):
                tag = f"{self.tag}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength,
                                                     frames=frames))
        return self.slots[key]


def merged_colors(sprites):
    colors = {}
    for s in sprites:
        colors.update(s["colors"])
    return colors


def paint(bm, first_face, grid, slot_for, up_only=False):
    """Set the material of every face added since face index `first_face` from the sprite pixel
    under its centre: slot_for(palette_index) -> material slot (or None to leave it). With up_only,
    faces pointing down keep their material."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        if up_only and f.normal.z < -0.2:
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y)
        if idx is None:
            continue
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def blob(bm, centre, radii, segments=16, rings=10, mat_index=0, bump=None):
    """A UV ellipsoid at `centre` with radii (rx, ry, rz); bump(x, y, z unit-sphere direction) -> scale
    factor makes it lumpy. Returns the index of its first face."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    cx, cy, cz = centre
    rx, ry, rz = radii
    top = bm.verts.new((cx, cy, cz + rz * (bump(0, 0, 1) if bump else 1)))
    bottom = bm.verts.new((cx, cy, cz - rz * (bump(0, 0, -1) if bump else 1)))
    ring_verts = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        ring = []
        for j in range(segments):
            th = 2 * math.pi * j / segments
            d = (math.sin(phi) * math.cos(th), math.sin(phi) * math.sin(th), math.cos(phi))
            s = bump(*d) if bump else 1
            ring.append(bm.verts.new((cx + rx * d[0] * s, cy + ry * d[1] * s, cz + rz * d[2] * s)))
        ring_verts.append(ring)
    for j in range(segments):
        k = (j + 1) % segments
        bm.faces.new((top, ring_verts[0][j], ring_verts[0][k])).material_index = mat_index
        bm.faces.new((bottom, ring_verts[-1][k], ring_verts[-1][j])).material_index = mat_index
    for a, b in zip(ring_verts, ring_verts[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((a[j], b[j], b[k], a[k])).material_index = mat_index
    return first


def cube_blob(bm, centre, radii, n=8, mat_index=0, bump=None):
    """An ellipsoid made from a subdivided cube (an even quad grid seen from above, unlike a UV
    sphere's pole), radii (rx, ry, rz); bump(direction) -> scale makes it lumpy. Returns the index
    of its first face."""
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    first_face, first_vert = len(bm.faces), len(bm.verts)
    cube = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in cube["verts"] for e in v.link_edges})
    if n > 1:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=n - 1, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in bm.verts[first_vert:]:
        x, y, z = v.co
        # Even cube-to-sphere mapping.
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        s = bump(sx, sy, sz) if bump else 1
        v.co = (cx + rx * sx * s, cy + ry * sy * s, cz + rz * sz * s)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.material_index = mat_index
    return first_face


def tube(bm, points, sides=8, mat_index=0, cap_start=True, cap_end=True):
    """A loft along any path: points are ((x, y, z), radius); radius 0 makes a point (a spike tip).
    Each ring is perpendicular to the path at that point."""
    from mathutils import Vector
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
            bm.faces.new(face).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box between corners (x0, y0, z0) and (x1, y1, z1) (units)."""
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def cylinder_x(bm, x0, x1, y, z, ry, rz, sides=12, mat_index=0, caps=True):
    """A cylinder along X from x0 to x1 centred on (y, z) with radii ry (across) and rz (up)."""
    start = len(bm.verts)
    common.loft(bm, [(x0, ry, rz, 0.0), (x1, ry, rz, 0.0)], sides=sides, mat_index=mat_index,
                cap_start=caps, cap_end=caps)
    rotate_new_to_x(bm, start, y, z)


def loft_x(bm, sections, y, z, sides=12, mat_index=0, cap_start=True, cap_end=True):
    """common.loft along X instead of Y: sections are (x, half_across_y, half_height, z_offset)."""
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    rotate_new_to_x(bm, start, y, z)


def rotate_new_to_x(bm, start, y, z):
    """Turn geometry lofted along Y (x across, y along) to run along X, centred on (y, z)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        across, along = v.co.x, v.co.y
        v.co.x, v.co.y = along, y - across
        v.co.z += z


def faces_since(bm, first):
    bm.faces.ensure_lookup_table()
    return bm.faces[first:]


def preview(root, name, objs, sprite, frame=0):
    """Render the --preview PNG if the script was asked for one."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][frame]
        ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])
