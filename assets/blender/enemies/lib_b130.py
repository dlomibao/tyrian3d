"""Helpers for batch b130 (the newshe.shp rib-backed creature, assembly-newshe-123).

Coordinates are assembly pixels: column c and row r of the 96 x 56 px assembly image, whose
centre (column 48, row 28 edges) is the Blender origin. Sprite up is +Y, one pixel is 1/12 unit.
"""

import math

import bmesh
import bpy
from mathutils import Vector

PX = 1 / 12
ASM_W, ASM_H = 96, 56


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - ASM_W / 2) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (ASM_H / 2 - (r + 0.5)) / 12


def _bridge(bm, rings, mats, smooth=True, cap_start=True, cap_end=True):
    """Join rings (lists of verts, or a single vert for a point) with quads/triangles.
    mats[i] is the material of the band between ring i and ring i + 1."""
    faces = []
    n = max(len(r) for r in rings)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        if len(r0) == 1 and len(r1) == 1:
            continue
        band = []
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            band.append(bm.faces.new(f))
        for f in band:
            f.material_index = mats[i]
        faces += band
    if cap_start and len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mats[0]
        faces.append(f)
    if cap_end and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.material_index = mats[-1]
        faces.append(f)
    for f in faces:
        f.smooth = smooth
    return faces


DOME_EXP = 0.6


def dome_ring(c, top, bottom, h, n=12, z0=0.0):
    """Points of a half-ellipse cross-section at column c, spanning rows top..bottom (pixel
    edges included) and rising h above z0: from the bottom edge over the top to the top edge."""
    yb, yt = Y(bottom + 0.5), Y(top - 0.5)
    yc, hw = (yb + yt) / 2, (yt - yb) / 2
    pts = []
    for k in range(n + 1):
        t = math.pi * k / n
        s = math.sin(t)
        pts.append((X(c), yc - hw * math.cos(t), z0 + h * (abs(s) ** DOME_EXP)))
    return pts


def dome_loft(bm, sections, mats, n=12, z0=0.0, smooth=True):
    """A rounded hump along X sitting on z0: sections are (col, top_row, bottom_row, height).
    mats is one material index, or one per band (len(sections) - 1). Ends are capped flat."""
    if isinstance(mats, int):
        mats = [mats] * (len(sections) - 1)
    rings = []
    for c, top, bottom, h in sections:
        rings.append([bm.verts.new(p) for p in dome_ring(c, top, bottom, h, n, z0)])
    return _bridge(bm, rings, list(mats) + [mats[-1]], smooth=smooth)


def dome_height(sections, c, r):
    """Height of a dome_loft surface above column c, row r (0 outside it)."""
    for (c0, t0, b0, h0), (c1, t1, b1, h1) in zip(sections, sections[1:]):
        if c0 <= c <= c1:
            u = (c - c0) / (c1 - c0) if c1 != c0 else 0
            top, bottom, h = t0 + (t1 - t0) * u, b0 + (b1 - b0) * u, h0 + (h1 - h0) * u
            yb, yt = Y(bottom + 0.5), Y(top - 0.5)
            yc, hw = (yb + yt) / 2, (yt - yb) / 2
            q = (Y(r) - yc) / hw
            if abs(q) >= 1:
                return 0.0
            return h * (math.sqrt(1 - q * q) ** DOME_EXP)
    return 0.0


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in XY; a ring of zero size collapses to a point."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
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
    return _bridge(bm, rings, [mat] * len(rings), smooth=smooth, cap_start=cap_start, cap_end=cap_end)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


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


def composite_png(common, root, layout, cx0, cy0, out):
    """The whole assembly's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size ASM_W / 12. layout entries are (model, cx, cy) relative to
    the assembly centre (cx0, cy0 already subtracted)."""
    import numpy as np
    w = ASM_W
    h = round(w * 14 / 12)
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = cx + w // 2 - 12, cy + h // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
