"""Helpers shared by batch b114's model scripts (not a model itself; build-models.sh skips lib_ files)."""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


def to_object(name, bm, mats, coll, merge=0.0):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag (and can weld
    coincident vertices first, which turns collapsed loft sections into clean points)."""
    if merge:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def dome(bm, x, y, rx, ry, rz, mat=0, segments=16, rings=5, sink=30.0, smooth=True):
    """A ball resting on the ground (z = 0), sunk so its lowest visible ring is `sink` degrees
    below its equator: an ellipsoid of radii (rx, ry, rz) in units, clipped flat at z = 0.
    Returns the z of the ellipsoid's centre."""
    s0 = math.radians(-sink)
    zc = rz * math.sin(-s0)  # centre height so the bottom ring sits on z = 0
    ring_verts = []
    for k in range(rings):
        a = s0 + (math.pi / 2 - s0) * k / rings
        ring = []
        for i in range(segments):
            t = 2 * math.pi * (i + 0.5) / segments
            ring.append(bm.verts.new((x + rx * math.cos(a) * math.cos(t),
                                      y + ry * math.cos(a) * math.sin(t),
                                      zc + rz * math.sin(a))))
        ring_verts.append(ring)
    top = bm.verts.new((x, y, zc + rz))
    faces = []
    for r0, r1 in zip(ring_verts, ring_verts[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append(bm.faces.new((ring_verts[-1][i], ring_verts[-1][j], top)))
    faces.append(bm.faces.new(list(reversed(ring_verts[0]))))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return zc


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, smooth=True):
    """A full ellipsoid centred at (x, y, z), radii in units."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co.x, v.co.y, v.co.z = x + v.co.x * rx, y + v.co.y * ry, z + v.co.z * rz
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def section_loft(bm, sections, strip_mats, bottom_mat=0, smooth=False):
    """A faceted body lofted along Y through cross-sections that all have the same number of
    points. Each section is (y, [(x, z), ...]) with the points running left to right across the
    top (the first and last usually on the ground, z = 0); the outline is closed underneath.
    `strip_mats(k, i)` gives the material of the facet between points i and i+1 of sections k
    and k+1. Ends are capped. Sections whose points coincide collapse when welded (to_object's
    `merge`), giving pointed tips."""
    rings = []
    for y, pts in sections:
        rings.append([bm.verts.new((x, y, z)) for x, z in pts])
    n = len(rings[0])
    faces = []
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = strip_mats(k, i) if j else bottom_mat
            faces.append(f)
    for ring, last in ((rings[0], False), (rings[-1], True)):
        if len({tuple(round(c, 5) for c in v.co) for v in ring}) >= 3:
            f = bm.faces.new(ring if last else list(reversed(ring)))
            f.material_index = strip_mats(0 if not last else len(rings) - 2, 0)
            faces.append(f)
    for f in faces:
        f.smooth = smooth
    return faces
