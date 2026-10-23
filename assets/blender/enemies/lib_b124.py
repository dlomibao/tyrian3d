"""Helpers shared by batch b124's model scripts (build-models.sh skips lib_ modules).

Coordinates are sprite pixel *edges*: column c runs from c to c + 1 and row r from r to r + 1, so a
pixel's centre is (c + 0.5, r + 0.5). A Frame maps them into Blender units for a block of w x h
pixels whose centre is the origin (sprite up is +Y, 1 px = 1/12 unit). Heights are in units.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


class Frame:
    """Pixel-edge (col, row) to Blender (x, y) for a w x h px block centred on the origin."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def x(self, c):
        return (c - self.w / 2) * PX

    def y(self, r):
        return (self.h / 2 - r) * PX

    def xy(self, c, r):
        return self.x(c), self.y(r)


def _faces_after(bm, before):
    bm.faces.ensure_lookup_table()
    return bm.faces[before:]


def set_faces(bm, before, mat=0, smooth=False):
    for f in _faces_after(bm, before):
        f.material_index = mat
        f.smooth = smooth


def slab(bm, fr, outline, z0, z1, mat=0, bevel=0.0, smooth=False):
    """Extrude an outline of (col, row) pixel-edge points from z0 to z1 (units). bevel (px) pulls
    the top face toward the centroid for a chamfered edge."""
    before = len(bm.faces)
    pts = [fr.xy(c, r) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    if bevel:
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        top = []
        for x, y in pts:
            dx, dy = cx - x, cy - y
            d = math.hypot(dx, dy) or 1
            k = min(bevel * PX / d, 0.9)
            top.append(bm.verts.new((x + dx * k, y + dy * k, z1)))
    else:
        top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bottom)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    set_faces(bm, before, mat, smooth)


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, rot_z=0.0, half=False, smooth=True):
    """An ellipsoid at a 3D centre (units) with radii (units), turned rot_z radians about Z.
    half keeps only the top half (a dome with a flat base)."""
    before = len(bm.faces)
    rx, ry, rz = radii
    loops = []
    for k in range(1, rings):
        t = math.pi / 2 - math.pi * k / rings  # latitude, top to bottom
        if half and t < 0:
            break
        loops.append([(rx * math.cos(t) * math.cos(a), ry * math.cos(t) * math.sin(a), rz * math.sin(t))
                      for a in (2 * math.pi * i / segments for i in range(segments))])
    rot = Matrix.Rotation(rot_z, 3, "Z")
    c = Vector(centre)
    vloops = [[bm.verts.new(c + rot @ Vector(p)) for p in loop] for loop in loops]
    top = bm.verts.new(c + Vector((0, 0, rz)))
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((top, vloops[0][i], vloops[0][j]))
    for l0, l1 in zip(vloops, vloops[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((l0[j], l0[i], l1[i], l1[j]))
    if half:
        bm.faces.new(vloops[-1][::-1])
    else:
        bot = bm.verts.new(c - Vector((0, 0, rz)))
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((bot, vloops[-1][j], vloops[-1][i]))
    set_faces(bm, before, mat, smooth)


def tube(bm, points, radii, sides=8, mat=0, flat=1.0, cap=True, smooth=True, up=(0, 0, 1), power=1.0):
    """A tube along a polyline of 3D points (units) with a radius per point (0 closes to a tip).
    `flat` scales the cross-section along the ring's 'up' direction (squashed tubes); power < 1
    squares the cross-section off (0.5 is a rounded box)."""
    before = len(bm.faces)
    pts = [Vector(p) for p in points]
    rings = []
    upv = Vector(up)
    for i, (p, rad) in enumerate(zip(pts, radii)):
        if rad == 0:
            rings.append([bm.verts.new(p)])
            continue
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(upv)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nup = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            cu, su = math.cos(ang), math.sin(ang)
            cu, su = math.copysign(abs(cu) ** power, cu), math.copysign(abs(su) ** power, su)
            ring.append(bm.verts.new(p + side * cu * rad + nup * su * rad * flat))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f)
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0])
        if len(rings[-1]) > 1:
            bm.faces.new(list(reversed(rings[-1])))
    set_faces(bm, before, mat, smooth)


def ground(bm, fr, grid, cell, c0, r0, cols, rows, slot_of, height_of, base=0.0, mat_side=0, inset=0.02):
    """Jungle-floor relief: a grid of cell x cell px quads over pixels (c0..c0+cols, r0..r0+rows)
    of `grid` (rows of palette indices, -1 transparent), each corner raised by height_of(index)
    averaged over the pixels around it, each quad coloured slot_of(most common index). The sides
    drop to z = 0. The outer edge is pulled in by `inset` px so a cut along it (split_assembly)
    leaves no wall lying in the cut plane."""
    nx, ny = cols // cell, rows // cell

    def px_at(c, r):
        if r0 <= r < r0 + rows and c0 <= c < c0 + cols and 0 <= r < len(grid) and 0 <= c < len(grid[0]):
            return grid[r][c]
        return -1

    verts = {}
    for j in range(ny + 1):
        for i in range(nx + 1):
            c, r = c0 + i * cell, r0 + j * cell
            hs = [height_of(px_at(c + dc, r + dr)) for dc in (-1, 0) for dr in (-1, 0)
                  if px_at(c + dc, r + dr) >= 0]
            z = base + (sum(hs) / len(hs) if hs else 0.0)
            if i in (0, nx) or j in (0, ny):
                z = base
            ce = c + (inset if i == 0 else -inset if i == nx else 0.0)
            re = r + (inset if j == 0 else -inset if j == ny else 0.0)
            verts[i, j] = bm.verts.new((fr.x(ce), fr.y(re), z))
    for j in range(ny):
        for i in range(nx):
            idx = [px_at(c0 + i * cell + a, r0 + j * cell + b) for a in range(cell) for b in range(cell)]
            idx = [v for v in idx if v >= 0]
            slot = slot_of(max(set(idx), key=idx.count)) if idx else mat_side
            f = bm.faces.new((verts[i, j + 1], verts[i + 1, j + 1], verts[i + 1, j], verts[i, j]))
            f.material_index = slot
            f.smooth = True
    # Skirt down to z = 0 and a bottom.
    ring = ([verts[i, 0] for i in range(nx + 1)] + [verts[nx, j] for j in range(1, ny + 1)]
            + [verts[i, ny] for i in range(nx - 1, -1, -1)] + [verts[0, j] for j in range(ny - 1, 0, -1)])
    low = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in ring]
    if base > 0:
        n = len(ring)
        for k in range(n):
            m = (k + 1) % n
            f = bm.faces.new((ring[k], ring[m], low[m], low[k]))
            f.material_index = mat_side
    f = bm.faces.new(low)
    f.material_index = mat_side


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
    """The first name's sprite.json with the colours of every listed model merged in."""
    data = common.load_sprite(root, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def composite_png(root, layout, w, h, out, frame_of=None):
    """Several pieces' sprites as one image (w x h px), each piece's 24x28 block with its top-left
    corner at layout (name, c0, r0). frame_of(name) picks the frame index (default 0)."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, c0, r0 in layout:
        data = common.load_sprite(root, name)
        k = frame_of(name) if frame_of else 0
        frame = data["frames"][min(k, len(data["frames"]) - 1)]
        for r, rowv in enumerate(frame["pixels"]):
            for c, v in enumerate(rowv):
                if v >= 0 and 0 <= r0 + r < h and 0 <= c0 + c < w:
                    img[r0 + r, c0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def drop_slivers(obj, min_area=1e-6):
    """Remove zero-area faces and loose edges and vertices (what a cut along a model's flat edge
    can leave behind, e.g. common.split_assembly cutting exactly through a skirt)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < min_area], context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj
