"""Helpers shared by batch b025's enemy scripts (build-models.sh skips lib_ modules).

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y; x()/y() take pixel centres,
  ex()/ey() pixel edges (corners), so outlines can be traced round pixels.
- Mats: palette materials made on demand, one slot per (index, finish).
- sweep / loft_y: tubes along a path in pixel coordinates (rings stand across the path).
- plate / pillow: extruded outlines, flat or with chamfered (rounded-looking) top edges.
- ellipsoid: a smooth ellipsoid, optionally turned about Z.
- mirror_x: mirror everything built since a vertex index about a vertical line.
- to_object: like common.mesh_object, but keeps each face's own smooth flag.
- paint: colour faces from the sprite pixel under them (shades of one ramp).
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
    """A w x h pixel grid centred on the origin (or with its pixel (c0, r0) corner offset, for
    assemblies). Column c, row r (pixel centre) -> X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U

    def ex(self, c):
        """Pixel edge (corner) column to X: edge c is the left edge of column c."""
        return (c - self.w / 2) * U

    def ey(self, r):
        return (self.h / 2 - r) * U

    def col(self, x):
        return x / U + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - y / U


class Mats:
    """Palette materials, one slot per (palette index, finish); `colors` maps index -> RGB."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.4, roughness=0.45, emission_strength=0.0):
        key = (index, metallic, roughness, emission_strength)
        if key not in self.slots:
            tag = self.tag
            if any(k[0] == index for k in self.slots):
                tag = f"{self.tag}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[key]


def merged_colors(root, names):
    colors = {}
    for n in names:
        colors.update(common.load_sprite(root, n)["colors"])
    return colors


def _faces_from(bm, first):
    bm.faces.ensure_lookup_table()
    return bm.faces[first:]


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, power=1.0):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in grid g. Rings stand
    across the path (in the XY plane) and up Z; a ring of zero size is a point. `power` < 1
    squares the section off (superellipse)."""
    first = len(bm.faces)
    pts = [Vector((g.x(c), g.y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
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
            ca, sa = math.cos(a), math.sin(a)
            ca = math.copysign(abs(ca) ** power, ca)
            sa = math.copysign(abs(sa) ** power, sa)
            ring.append(bm.verts.new(pts[i] + side * (w * U * ca) + up * (h * sa)))
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
            bm.faces.new(f)
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    for f in _faces_from(bm, first):
        f.material_index = mat
        f.smooth = smooth
    return first


def loft_y(bm, g, col, sections, sides=10, mat=0, smooth=True, power=1.0):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px,
    half_height_units, z)."""
    return sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat,
                 smooth=smooth, power=power)


def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` along its corner's bisector."""
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


def _ccw(pts):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area > 0 else list(reversed(pts))


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 whose outline is a list of (col, row) pixel edges."""
    pts = _ccw([(g.ex(c), g.ey(r)) for c, r in outline])
    first = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    for f in _faces_from(bm, first):
        f.smooth = smooth
    return first


def pillow(bm, g, outline, z0, z1, round_px=1.5, round_h=0.5, steps=3, mat=0, top_mat=None, smooth=False):
    """An extruded outline (pixel-edge (col, row) points) from z0 to z1 with its top edge rounded
    off: the wall rises to z1 - round_h * (z1 - z0), then `steps` rings curve in by up to round_px
    pixels and up to the flat top at z1 (a quarter round). Keep round_px below half the narrowest
    part of the outline."""
    pts = _ccw([(g.ex(c), g.ey(r)) for c, r in outline])
    first = len(bm.faces)
    rh = round_h * (z1 - z0)
    rings = [(pts, z0), (pts, z1 - rh)]
    for k in range(1, steps + 1):
        th = k / steps * math.pi / 2
        rings.append((inset_outline(pts, round_px * U * (1 - math.cos(th))), z1 - rh + rh * math.sin(th)))
    vrings = [[bm.verts.new((x, y, z)) for x, y in ring] for ring, z in rings]
    n = len(pts)
    bm.faces.new(list(reversed(vrings[0])))
    for a, b in zip(vrings, vrings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    top = bm.faces.new(vrings[-1])
    for f in _faces_from(bm, first):
        f.material_index = mat
        f.smooth = smooth
    if top_mat is not None:
        top.material_index = top_mat
    return first


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=16, rings=8, angle=0.0, smooth=True, half=False):
    """An ellipsoid at (x, y, z) units with radii (rx, ry, rz) units, turned by `angle` (radians)
    about Z. `half` keeps only the top half (a dome, with a flat bottom)."""
    first = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    ca, sa = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        lx, ly, lz = v.co.x * rx, v.co.y * ry, v.co.z * rz
        if half and lz < 0:
            lz = 0.0
        v.co = Vector((x + lx * ca - ly * sa, y + lx * sa + ly * ca, z + lz))
    for f in _faces_from(bm, first):
        f.material_index = mat
        f.smooth = smooth
    return first


def mark(bm):
    """The vertices there are now: pass it to move / mirror_x to act on everything added after.
    (Vertex indices are not reliable for that: bmesh ops can free slots that new vertices reuse.)"""
    return set(bm.verts)


def _since(bm, before):
    return [v for v in bm.verts if v not in before]


def mirror_x(bm, axis_x, before):
    """Add a mirror image, about the vertical line X = axis_x, of every face whose vertices were all
    added since mark(bm) returned `before`."""
    new_verts = set(_since(bm, before))
    faces = [f for f in bm.faces if all(v in new_verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(new_verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def move(bm, before, dx=0.0, dy=0.0, dz=0.0):
    """Move everything added since mark(bm) returned `before`."""
    for v in _since(bm, before):
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


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


def paint(bm, first_face, g, pixels, slot_of, min_nz=0.3, reach=1, average=True):
    """Give each face added since `first_face` (whose normal points up at least min_nz) the slot of
    the sprite pixels under it: slot_of(palette_index) -> slot or None to leave it. With `average`,
    the mean index of the pixels under the face (shades of one ramp) is used."""
    bm.normal_update()
    h, w = len(pixels), len(pixels[0])
    for f in _faces_from(bm, first_face):
        if f.normal.z < min_nz:
            continue
        cen = f.calc_center_median()
        pts = [cen] + [cen.lerp(v.co, 0.5) for v in f.verts] if average else [cen]
        vals = []
        for p in pts:
            c, r = int(round(g.col(p.x))), int(round(g.row(p.y)))
            for d in range(reach + 1):
                found = None
                for dr in range(-d, d + 1):
                    for dc in range(-d, d + 1):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and pixels[rr][cc] > 1:
                            found = pixels[rr][cc]
                            break
                    if found is not None:
                        break
                if found is not None:
                    vals.append(found)
                    break
        if not vals:
            continue
        idx = round(sum(vals) / len(vals))
        slot = slot_of(idx)
        if slot is not None:
            f.material_index = slot


def preview(objs, root, name, frame_image, size=2):
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / frame_image
        common.render_preview(objs, out, ref, size=size)


def subset(sprites, frames):
    """The sprites list with only the given frame numbers kept."""
    out = []
    for s in sprites:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out
