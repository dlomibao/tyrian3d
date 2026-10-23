"""Helpers shared by batch b046's models (lips, tongue, energy orb): sprite and assembly pixel
coordinates, lofts along X or Y with free cross-sections, ellipsoids, per-face colours sampled
from the sprite, and assembly previews.

build-models.sh skips lib_ files; the model scripts import this next to them.
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


class Grid:
    """Pixel coordinates of a w x h px image (a sprite or a whole assembly) centred on the origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        """Column (pixel centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        """Row (pixel centre) to Blender Y: sprite up is +Y."""
        return (self.h / 2 - (r + 0.5)) / 12

    def col(self, x):
        return x * 12 + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - y * 12


def assemble_pixels(root, layout):
    """One pixel grid for several pieces: layout is [(name, col0, row0)] with each piece's top-left
    pixel in the grid. Returns (rows, colors) with every piece's colours merged."""
    pieces = [(common.load_sprite(root, n), c0, r0) for n, c0, r0 in layout]
    w = max(c0 + 24 for _, c0, _ in pieces)
    h = max(r0 + 28 for _, _, r0 in pieces)
    rows = [[-1] * w for _ in range(h)]
    colors = {}
    for data, c0, r0 in pieces:
        colors.update(data["colors"])
        for r, line in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    rows[r0 + r][c0 + c] = v
    return rows, colors


def _ring(sides, power):
    """Unit ring points (cos, sin) of a superellipse: power < 1 squarer, 1 round."""
    pts = []
    for i in range(sides):
        a = 2 * math.pi * (i + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        pts.append((math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)))
    return pts


def _bridge(bm, rings, sides, mat, cap_start, cap_end):
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def loft_x(bm, sections, sides=12, mat=0, power=1.0, cap_start=True, cap_end=True):
    """Loft along X. Sections are (x, y_centre, half_y, half_z, z_centre); a section with zero
    half sizes is a point (a pointed or rounded end)."""
    unit = _ring(sides, power)
    rings = []
    for x, yc, hy, hz, zc in sections:
        if hy == 0 and hz == 0:
            rings.append([bm.verts.new((x, yc, zc))])
        else:
            rings.append([bm.verts.new((x, yc + hy * c, zc + hz * s)) for c, s in unit])
    return _bridge(bm, rings, sides, mat, cap_start, cap_end)


def loft_y(bm, sections, sides=12, mat=0, power=1.0, groove=None, cap_start=True, cap_end=True):
    """Loft along Y. Sections are (y, x_centre, half_x, half_z, z_centre). `groove` is
    (x, half_width, depth): the top surface dips by up to `depth` around that X (a tongue's
    furrow)."""
    unit = _ring(sides, power)
    rings = []
    for y, xc, hx, hz, zc in sections:
        if hx == 0 and hz == 0:
            rings.append([bm.verts.new((xc, y, zc))])
            continue
        ring = []
        for c, s in unit:
            x, z = xc + hx * c, zc + hz * s
            if groove and s > 0:
                gx, gw, depth = groove
                z -= depth * s * math.exp(-((x - gx) / gw) ** 2)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    return _bridge(bm, rings, sides, mat, cap_start, cap_end)


def ellipsoid(bm, centre, radii, segments=16, rings=8, mat=0):
    """An ellipsoid at `centre` with semi-axes `radii` (x, y, z)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    new = set(bm.faces) - before
    for f in new:
        f.material_index = mat
        f.smooth = True
    return list(new)


def smooth_profile(values, passes=1):
    """A light moving average (ends kept) to soften a per-pixel staircase profile."""
    v = list(values)
    for _ in range(passes):
        v = [v[0]] + [(v[i - 1] + 2 * v[i] + v[i + 1]) / 4 for i in range(1, len(v) - 1)] + [v[-1]]
    return v


def paint(faces, grid, pixels, slot_of, min_nz=0.25, spread=0.6):
    """Give each upward-facing face the slot of the sprite pixels under it: the mean palette
    index under its centre and toward its corners, mapped by slot_of(index) -> slot or None
    (leave the face as it is)."""
    for f in faces:
        f.normal_update()
        if f.normal.z < min_nz:
            continue
        cen = f.calc_center_median()
        pts = [cen] + [cen.lerp(v.co, spread) for v in f.verts]
        vals = []
        for p in pts:
            c, r = int(round(grid.col(p.x))), int(round(grid.row(p.y)))
            if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]) and pixels[r][c] >= 0:
                vals.append(pixels[r][c])
        if not vals:
            continue
        slot = slot_of(vals)
        if slot is not None:
            f.material_index = slot


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


def pixels_png(rows, colors, out, w, h):
    """Write a pixel grid (palette indices, -1 transparent) as a w x h PNG, the grid centred."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    r0, c0 = (h - len(rows)) // 2, (w - len(rows[0])) // 2
    for r, line in enumerate(rows):
        for c, v in enumerate(line):
            if v >= 0:
                img[r0 + r, c0 + c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("b046_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def preview_arg():
    return sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
