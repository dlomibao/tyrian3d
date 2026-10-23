"""Helpers shared by the b096 model scripts (not a model itself: build-models.sh skips lib_ files).

Coordinates are sprite pixels: a Grid maps pixel columns/rows (centres, fractions allowed) of a
w x h px block to Blender units, centred on the block (1 px = 1/12 unit, sprite up is +Y)."""

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
    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def tag_faces(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in XY; a ring of zero size collapses to a point."""
    before = set(bm.faces)
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
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
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    tag_faces(bm, before, mat, smooth)


def loft_y(bm, g, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px,
    half_height_units, z_centre)."""
    sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def dome(bm, g, col, row, rx_px, ry_px, height, z0=0.0, mat=0, segments=16, rings=5, angle=0.0):
    """Upper half of an ellipsoid sitting on z0: radii in px across X/Y (before rotating by
    `angle` radians, counter-clockwise seen from above), rising `height` units."""
    before = set(bm.faces)
    cx, cy = g.X(col), g.Y(row)
    ca, sa = math.cos(angle), math.sin(angle)
    top = bm.verts.new((cx, cy, z0 + height))
    layers = []
    for i in range(1, rings + 1):
        phi = (math.pi / 2) * i / rings  # from the top down to the equator
        s, c = math.sin(phi), math.cos(phi)
        ring = []
        for k in range(segments):
            a = 2 * math.pi * k / segments
            x, y = rx_px * PX * s * math.cos(a), ry_px * PX * s * math.sin(a)
            ring.append(bm.verts.new((cx + x * ca - y * sa, cy + x * sa + y * ca, z0 + height * c)))
        layers.append(ring)
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((top, layers[0][k], layers[0][j]))
    for r0, r1 in zip(layers, layers[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
    bm.faces.new(list(reversed(layers[-1])))
    tag_faces(bm, before, mat, smooth=True)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel *edges* (col 3 = the left
    edge of column 3), counter-clockwise seen from above."""
    before = set(bm.faces)
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    tag_faces(bm, before, mat, smooth)


def mirror_all(bm, ax):
    """Add a mirror image about X = ax of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
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


def preview_args():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None
