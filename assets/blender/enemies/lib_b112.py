"""Helpers for batch b112 (the newshh waterfall assembly). Not a model script: build-models.sh
skips lib_ files.

Coordinates are assembly pixels: column `c` and row `r` (pixel centres; fractions allowed) of a
block `w` x `h` px whose centre is the Blender origin. Sprite up is +Y, 1 px = 1/12 unit."""

import math

import bmesh
import bpy
from mathutils import Vector

PX = 1 / 12


class Grid:
    """Pixel <-> Blender mapping for a w x h px block centred on the origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


class Mats:
    """Palette materials created on first use; `slot(index)` returns the material slot."""

    def __init__(self, sprite, tag, settings=None):
        self.sprite, self.tag = sprite, tag
        self.settings = settings or {}
        self.list, self.slots = [], {}

    def slot(self, index):
        if index not in self.slots:
            kw = self.settings.get(index, {"metallic": 0.1, "roughness": 0.6})
            import common
            self.list.append(common.palette_material(self.sprite, index, self.tag, **kw))
            self.slots[index] = len(self.list) - 1
        return self.slots[index]


def interp(profile, t):
    """Piecewise linear interpolation of [(t, value), ...] (sorted by t), clamped at the ends."""
    if t <= profile[0][0]:
        return profile[0][1]
    for (t0, v0), (t1, v1) in zip(profile, profile[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return v0 + (v1 - v0) * k
    return profile[-1][1]


def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def ramp(bm, g, e0, e1, profile, mat, r_from=None, r_to=None, step=1.0, lift=0.0, base=0.0):
    """A solid block between pixel-edge columns e0 and e1 (X), from row edge r_from to r_to (Y),
    whose top follows `profile` [(row_edge, z)] (plus `lift`) and whose bottom is at z = base.
    Row edges are where pixel rows begin (edge r is the top of row r)."""
    r_from = profile[0][0] if r_from is None else r_from
    r_to = profile[-1][0] if r_to is None else r_to
    rows = [r_from]
    knots = [t for t, _ in profile if r_from < t < r_to]
    t = r_from
    while t + step < r_to:
        t += step
        rows.append(t)
    rows = sorted(set(rows + knots + [r_to]))
    x0, x1 = g.X(e0 - 0.5), g.X(e1 - 0.5)
    rings = []
    for r in rows:
        y = g.Y(r - 0.5)
        z = interp(profile, r) + lift
        rings.append([bm.verts.new(co) for co in ((x0, y, base), (x1, y, base), (x1, y, z), (x0, y, z))])
    faces = []
    for a, b in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    _faces(bm, faces, mat, False)


def plate(bm, g, outline, z0, z1, mat, smooth=False):
    """A flat prism from z0 to z1 with an outline of (col, row) pixel edges."""
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    _faces(bm, faces, mat, smooth)


def sweep(bm, g, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; a ring of zero size collapses to a point.
    (After assets/blender/enemies/assembly-newsht-39.py.)"""
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
    rings = []
    up = Vector((0, 0, 1))
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
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    faces = []
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
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    _faces(bm, faces, mat, smooth)


def loft_bands(bm, x, sections, sides=6, smooth=True):
    """A loft along Y at Blender X `x`, like common.loft, but each section carries the material
    of the band from it to the next: sections are (y, half_width, half_height, z, mat). A section
    of zero size is a point (a tip). Ends are capped unless they are points."""
    rings = []
    for y, w, h, z, _ in sections:
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x, y, z))])
            continue
        rings.append([bm.verts.new((x + w * math.cos(2 * math.pi * (i + 0.5) / sides), y,
                                    z + h * math.sin(2 * math.pi * (i + 0.5) / sides))) for i in range(sides)])
    for (r0, r1), sec in zip(zip(rings, rings[1:]), sections):
        faces = []
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[i])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[i], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
        _faces(bm, faces, sec[4], smooth)
    if len(rings[0]) > 1:
        _faces(bm, [bm.faces.new(list(reversed(rings[0])))], sections[0][4], smooth)
    if len(rings[-1]) > 1:
        _faces(bm, [bm.faces.new(rings[-1])], sections[-2][4], smooth)


def ellipsoid(bm, g, c, r, z, rx_px, ry_px, rz, mat=0, segments=8, rings=4, smooth=True):
    """An ellipsoid centred on pixel (c, r) at height z."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.X(c) + v.co.x * rx_px * PX, g.Y(r) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _faces(bm, set(bm.faces) - before, mat, smooth)


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


def composite_png(pixels, colors, w, h, out):
    """Write {(col, row): palette index} as a w x h PNG (transparent elsewhere)."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for (c, r), v in pixels.items():
        if v >= 0 and 0 <= c < w and 0 <= r < h:
            img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
