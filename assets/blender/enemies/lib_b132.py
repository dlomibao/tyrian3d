"""Helpers shared by batch b132's model scripts (the newsha skull crate assembly).

Coordinates are pixel edges of the assembly's pixel map: E(c) is the left edge of column c and
F(r) the top edge of row r (so pixel (c, r) spans E(c)..E(c + 1), F(r)..F(r + 1)). The origin
(column 48, row 56) is set by the assembly script through ORIGIN.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ORIGIN = [48, 56]
PX = 1 / 12


def E(c):
    """Pixel edge column to Blender X."""
    return (c - ORIGIN[0]) / 12


def F(r):
    """Pixel edge row to Blender Y (sprite up is +Y)."""
    return (ORIGIN[1] - r) / 12


def _mark(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def box(bm, c0, r0, c1, r1, z0, z1, mat=0, bevel=0.0, smooth=False):
    """A block over pixel edges c0..c1, r0..r1 from z0 to z1. `bevel` (units) chamfers the top
    edges, so the top face is inset by it and the chamfer runs down to z1 - bevel."""
    before = set(bm.faces)
    x0, x1, y0, y1 = E(c0), E(c1), F(r1), F(r0)
    def ring(z, inset):
        return [bm.verts.new((x, y, z)) for x, y in
                ((x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x1 - inset, y1 - inset), (x0 + inset, y1 - inset))]
    rings = [ring(z0, 0.0)]
    if bevel > 0:
        rings.append(ring(z1 - bevel, 0.0))
        rings.append(ring(z1, bevel))
    else:
        rings.append(ring(z1, 0.0))
    bm.faces.new(list(reversed(rings[0])))
    for a, b in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[-1])
    _mark(bm, before, mat, smooth)


def relief(bm, outline, z0, z1, inset=0.0, mat=0, smooth=False):
    """A plate with an outline of (col, row) pixel edges (counter-clockwise seen from above, i.e.
    clockwise in pixel rows) from z0 to z1, its top shrunk toward the centroid by `inset` px."""
    before = set(bm.faces)
    pts = [(E(c), F(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        k = max(0.0, 1 - inset * PX / d)
        top.append(bm.verts.new((cx + dx * k, cy + dy * k, z1)))
    bm.faces.new(list(reversed(bottom)))
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    _mark(bm, before, mat, smooth)


def strap(bm, c0, c1, r0, r1, z0, z1, mat=0, segments=6):
    """A metal strap along Y over columns c0..c1 (edges), rows r0..r1: flat sides up to a rounded
    top whose crown is at z1. Built as a profile across X extruded along Y."""
    before = set(bm.faces)
    x0, x1 = E(c0), E(c1)
    xm, hw = (x0 + x1) / 2, (x1 - x0) / 2
    shoulder = z1 - min(hw * 0.45, (z1 - z0) * 0.5)
    prof = [(x0, z0)]
    for i in range(segments + 1):
        a = math.pi * (1 - i / segments)
        prof.append((xm + hw * math.cos(a), shoulder + (z1 - shoulder) * math.sin(a)))
    prof.append((x1, z0))
    ya, yb = F(r1), F(r0)
    ring_a = [bm.verts.new((x, ya, z)) for x, z in prof]
    ring_b = [bm.verts.new((x, yb, z)) for x, z in prof]
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))
    bm.faces.new(ring_a)
    bm.faces.new(list(reversed(ring_b)))
    _mark(bm, before, mat, True)


def sweep(bm, path, radius, sides=8, mat=0, smooth=True):
    """A round tube through 3D points `path` (Blender units), capped at both ends."""
    from mathutils import Vector
    pts = [Vector(p) for p in path]
    before = set(bm.faces)
    rings = []
    prev_u = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized()
        if prev_u is not None and u.dot(prev_u) < 0:
            u = -u
        prev_u = u
        v = t.cross(u).normalized()
        rings.append([bm.verts.new(p + radius * (math.cos(2 * math.pi * k / sides) * u
                                                 + math.sin(2 * math.pi * k / sides) * v))
                      for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    _mark(bm, before, mat, smooth)


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


def composite_png(root, pieces, layout, out, width, height, offset):
    """The pieces' first frames as one image of width x height px; `layout` gives each piece's
    centre (cx, cy) relative to the image's top-left pixel edge minus `offset`."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        if name not in pieces:
            continue
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = cx + offset[0] - 12, cy + offset[1] - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < height and 0 <= x0 + c < width:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", width, height, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
