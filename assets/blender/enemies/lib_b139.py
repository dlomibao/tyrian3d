"""Helpers for batch b139's model scripts (the newsh^ red dome structure of level 4.14).

Geometry is placed in sprite pixel coordinates through a Grid: column c / row r (pixel centres,
fractions allowed) of a w x h px block whose centre is the Blender origin. Sprite up is +Y and one
sprite pixel is 1/12 unit. Copied from lib_b072.py (sweep, plates, domes and the brick floor for sprites that fill their
tile), plus closed rings and elliptical discs.
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
    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; the width is across the path, the height along Z.
    A ring of zero size collapses to a point (a rounded or pointed end)."""
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
        rings.append([bm.verts.new(pts[i] + side * (w * PX * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + up * (h * math.sin(2 * math.pi * (k + 0.5) / sides)))
                      for k in range(sides)])
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
    _tag(bm, before, mat, smooth)


def loft_y(bm, g, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px, half_height, z)."""
    sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (the top-left corner
    of pixel (c, r) is (c, r)), counter-clockwise seen from above or not, normals get fixed."""
    before = set(bm.faces)
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, before, mat, smooth)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=14, rings=7):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _tag(bm, before, mat, True)


def mirror_all(bm, axis_x):
    """Add a mirror image about the vertical line X = axis_x of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
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


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w, h):
    """The whole assembly's sprite (first frames) as one image of w x h px (w:h must be 24:28 for
    render_preview), each piece placed by its centre (cx, cy) relative to the image centre."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w // 2 - 12), int(cy + h // 2 - 14)
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def dome(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8):
    """The top half of an ellipsoid standing on z, its flat base closed. `rings` must be even."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    low = [v for v in res["verts"] if v.co.z < -1e-4]
    bmesh.ops.delete(bm, geom=low, context="VERTS")
    keep = [v for v in res["verts"] if v.is_valid]
    edges = {e for v in keep for e in v.link_edges if e.is_boundary}
    bmesh.ops.holes_fill(bm, edges=list(edges), sides=0)
    for v in keep:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _tag(bm, before, mat, True)


def floor_bricks(bm, g, pixels, slab_mat, dark_mat, light_mat, top=0.03, brick=0.018, min_index=2):
    """A thin floor plate under the whole tile (base at z = 0, top at `top`) with the background's
    bricks as low relief: each horizontal run of pixels of index >= min_index that the model built
    so far doesn't cover (seen from above) becomes a strip `brick` tall, light_mat where the run is
    brighter than index 3.5 on average, dark_mat otherwise. Call it last."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromBMesh(bm) if len(bm.faces) else None

    def covered(c, r):
        if tree is None:
            return False
        hit = tree.ray_cast(Vector((g.X(c), g.Y(r), 5.0)), Vector((0, 0, -1)))
        return hit[0] is not None and hit[0].z > top + brick * 0.5

    h, w = len(pixels), len(pixels[0])
    plate(bm, g, [(0, 0), (w, 0), (w, h), (0, h)], 0.0, top, mat=slab_mat)
    for r in range(h):
        c = 0
        while c < w:
            if pixels[r][c] >= min_index and not covered(c, r):
                c0 = c
                while c < w and pixels[r][c] >= min_index and not covered(c, r):
                    c += 1
                mean = sum(pixels[r][c0:c]) / (c - c0)
                plate(bm, g, [(c0, r), (c, r), (c, r + 1), (c0, r + 1)], top, top + brick,
                      mat=light_mat if mean > 3.5 else dark_mat)
            else:
                c += 1


def ring(bm, g, col, row, rx_px, ry_px, z, w_px, h, a0=0.0, a1=360.0, steps=24, sides=8, mat=0,
         caps=True):
    """A tube along an elliptical arc centred on pixel (col, row) with radii rx_px, ry_px, from angle
    a0 to a1 in degrees (0 = right, 90 = up the sprite), half width w_px across, half height h.
    A full turn (a1 - a0 = 360) is closed into a loop. w_px and h may also be functions of the
    position along the arc (0 to 1), to taper it."""
    wf = w_px if callable(w_px) else (lambda t: w_px)
    hf = h if callable(h) else (lambda t: h)
    full = abs(a1 - a0) >= 359.9
    n = steps if full else steps + 1
    pts = []
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((col + rx_px * math.cos(a), row - ry_px * math.sin(a)))
    before = set(bm.faces)
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r) in enumerate(pts):
        p = Vector((g.X(c), g.Y(r), z))
        if full:
            q0, q1 = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            q0, q1 = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        t = Vector((g.X(q1[0]) - g.X(q0[0]), g.Y(q1[1]) - g.Y(q0[1]), 0)).normalized()
        side = t.cross(up)
        u = i / steps
        rings.append([bm.verts.new(p + side * (wf(u) * PX * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + up * (hf(u) * math.sin(2 * math.pi * (k + 0.5) / sides)))
                      for k in range(sides)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if full else [])
    for r0, r1 in pairs:
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if not full and caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    _tag(bm, before, mat, True)


def disc(bm, g, col, row, rx_px, ry_px, z0, z1, mat=0, steps=24):
    """A flat elliptical plate centred on pixel (col, row), radii in px (to pixel edges), from z0 to z1."""
    before = set(bm.faces)
    pts = [(g.X(col) + rx_px * PX * math.cos(2 * math.pi * i / steps),
            g.Y(row) + ry_px * PX * math.sin(2 * math.pi * i / steps)) for i in range(steps)]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, before, mat, False)
