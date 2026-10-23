"""Helpers shared by batch b061's enemy scripts (build-models.sh skips lib_ modules).

- Mats: palette materials created on demand, one slot per palette index (adapted from lib_b006).
- sweep: an elliptical tube along a path in the XY plane (width across the path, height in Z).
- ellipsoid: a UV ellipsoid.
- paint: give faces the material of the sprite pixel under them (seen from above).
- compose: the pixels of several sprites laid out as one image, and a PNG of it for previews.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


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


def sweep(bm, path, sides=12, mat_index=0, cap_start=True, cap_end=True):
    """A tube along `path`, a list of (x, y, z, half_width, half_height) in units. Each ring stands
    perpendicular to the path in the XY plane: half_width is measured across the path, half_height
    along Z. A ring of zero size collapses to a point (a tip). Returns the index of its first face."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
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
            bm.faces.new(f).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index
    return first


def ellipsoid(bm, centre, radii, segments=16, rings=8, mat_index=0):
    """A UV ellipsoid at `centre` with radii (rx, ry, rz). Returns the index of its first face."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        f.material_index = mat_index
    return first


def paint(bm, first_face, sample, slot_for, under_slot=None, min_nz=-0.35, last_face=None):
    """Set the material of each face from `first_face` (to `last_face`) from the sprite under it:
    sample(x, y) -> palette index or None, averaged over the face's centre and corners;
    slot_for(index) -> material slot (None leaves it). Faces pointing down (normal z < min_nz) get
    `under_slot` if given."""
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[first_face:last_face])
    bm.normal_update()
    for f in bm.faces[first_face:last_face]:
        if f.normal.z < min_nz:
            if under_slot is not None:
                f.material_index = under_slot
            continue
        c = f.calc_center_median()
        pts = [c] + [c.lerp(v.co, 0.6) for v in f.verts]
        vals = [sample(p.x, p.y) for p in pts]
        vals = [v for v in vals if v is not None]
        if not vals:
            continue
        idx = max(set(vals), key=vals.count) if len(set(vals)) > 2 else round(sum(vals) / len(vals))
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def to_object(name, bm, mats, coll, smooth=True):
    """Like common.mesh_object, but keeps the bmesh's normals as built (recalculated once)."""
    return common.mesh_object(name, bm, mats, coll, smooth=smooth)


def write_png(grid, colors, out, pad_to=None):
    """Write palette-index rows (`grid`, -1 transparent) as an RGBA PNG, 1 px per sprite pixel,
    centred in a (w, h) canvas if `pad_to` is given."""
    import numpy as np
    h, w = len(grid), len(grid[0])
    cw, ch = pad_to or (w, h)
    img = np.zeros((ch, cw, 4), dtype=np.float32)
    x0, y0 = (cw - w) // 2, (ch - h) // 2
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v >= 0:
                img[y0 + r, x0 + c] = [*(k / 255 for k in colors[str(v)]), 1.0]
    im = bpy.data.images.new("b061_sprite", cw, ch, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def cube_blob(bm, centre, radii, n=8, mat_index=0):
    """An ellipsoid made from a subdivided cube (an even quad grid seen from above, unlike a UV
    sphere's pole; from lib_b006), radii (rx, ry, rz). Returns the index of its first face."""
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
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        v.co = (cx + rx * sx, cy + ry * sy, cz + rz * sz)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.material_index = mat_index
    return first_face
