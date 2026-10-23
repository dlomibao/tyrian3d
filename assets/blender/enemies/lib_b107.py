"""Helpers shared by the b107 model scripts (newsha.shp ground pieces): pixel coordinates,
plates from pixel outlines, ellipsoids, tori, and an object builder that keeps per-face shading.

Coordinates: a sprite (or assembly) `w` px wide and `h` px tall, centred on the origin. Pixel
*edges* are used for outlines (column c's left edge is c, its right edge c + 1), pixel centres
for round things (c + 0.5).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


class Grid:
    """Maps pixel coordinates of a w x h px block (centred on the origin) to Blender X/Y."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def x(self, c):
        """Pixel-edge column (fractions allowed) to X."""
        return (c - self.w / 2) * PX

    def y(self, r):
        """Pixel-edge row to Y (sprite up is +Y)."""
        return (self.h / 2 - r) * PX


def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (any winding)."""
    pts = [(g.x(c), g.y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    before = set(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, before, mat, smooth)


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    """An axis-aligned box over pixel edges c0..c1, r0..r1."""
    plate(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def bevel_plate(bm, g, outline, z0, z1, inset, mat=0, top_mat=None, smooth=False):
    """A plate whose top edge is chamfered inward by `inset` px (a frustum-like slab)."""
    pts = [(g.x(c), g.y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    n = len(pts)
    # Inset each vertex along the bisector of its edges.
    inner = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        b = (n0 + n1)
        if b.length < 1e-6:
            b = n0
        b.normalize()
        d = inset * PX / max(0.3, b.dot(n0))
        q = p1 + b * d
        inner.append((q.x, q.y))
    before = set(bm.faces)
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    mid = [bm.verts.new((x, y, z1 - inset * PX)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in inner]
    bm.faces.new(list(reversed(bot)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], top[j], top[i]))
    topf = bm.faces.new(top)
    _tag(bm, before, mat, smooth)
    if top_mat is not None:
        topf.material_index = top_mat
    del cx, cy


def ellipsoid(bm, g, c, r, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, cut_below=None):
    """An ellipsoid centred on pixel-edge point (c, r) at height z. `cut_below` drops the
    vertices below that height onto it (a dome sitting on a surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.x(c) + v.co.x * rx_px * PX, g.y(r) + v.co.y * ry_px * PX, z + v.co.z * rz))
        if cut_below is not None and v.co.z < cut_below:
            v.co.z = cut_below
    _tag(bm, before, mat, True)


def torus(bm, g, c, r, z, major_px, minor_px, minor_z, mat=0, segments=24, sides=8,
          ry_scale=1.0):
    """A torus lying flat, centred on pixel-edge point (c, r) at height z. The tube is minor_px
    across and minor_z tall (half sizes)."""
    before = set(bm.faces)
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ring = []
        for k in range(sides):
            b = 2 * math.pi * k / sides
            rad = (major_px + minor_px * math.cos(b)) * PX
            ring.append(bm.verts.new((g.x(c) + rad * math.cos(a),
                                      g.y(r) + rad * math.sin(a) * ry_scale,
                                      z + minor_z * math.sin(b))))
        rings.append(ring)
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
    _tag(bm, before, mat, True)


def cylinder(bm, g, c, r, z0, z1, rx_px, ry_px=None, mat=0, segments=16, smooth=True):
    """An upright (elliptic) cylinder centred on pixel-edge point (c, r)."""
    ry_px = rx_px if ry_px is None else ry_px
    before = set(bm.faces)
    bot, top = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        x = g.x(c) + rx_px * PX * math.cos(a)
        y = g.y(r) + ry_px * PX * math.sin(a)
        bot.append(bm.verts.new((x, y, z0)))
        top.append(bm.verts.new((x, y, z1)))
    bm.faces.new(list(reversed(bot)))
    caps = [bm.faces.new(top)]
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    _tag(bm, before, mat, smooth)
    for f in caps:
        f.smooth = False


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


def preview_args():
    if "--preview" in sys.argv:
        return sys.argv[sys.argv.index("--preview") + 1]
    return None
