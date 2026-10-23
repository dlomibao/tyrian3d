"""Helpers shared by batch b126's models (a jungle bunker built from four 2x2 pieces, and a green
pod crawler): pixel-edge coordinates for any block size, prisms and frustums from pixel outlines,
ellipsoids, a jungle ground heightfield painted from the sprite, and objects that keep each face's
own smooth flag.

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
    """Pixel coordinates of a block `w` x `h` px whose centre is the Blender origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def E(self, c, r):
        """Pixel edge coordinates (column c, row r; 0 is the block's left / top edge) to Blender XY."""
        return ((c - self.w / 2) / 12, (self.h / 2 - r) / 12)

    def X(self, c):
        """Pixel centre column (fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        """Pixel centre row to Blender Y (sprite up is +Y)."""
        return (self.h / 2 - (r + 0.5)) / 12


def _mark(bm, start_faces, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start_faces:]:
        f.material_index = mat
        f.smooth = smooth


def prism(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A vertical prism from z0 to z1 over an outline of pixel edges (col, row), clockwise on
    screen (counter-clockwise in Blender)."""
    pts = [g.E(c, r) for c, r in outline]
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _mark(bm, n, mat, smooth)


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    prism(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat)


def frustum(bm, g, bottom, z0, top, z1, side_mats, top_mat, bottom_cap=True):
    """A solid joining a bottom outline at z0 to a top outline at z1 (same number of corners,
    pixel edges, clockwise on screen). side_mats gives each side's material (side i runs from
    corner i to corner i + 1); a single int colours them all."""
    n = len(bottom)
    if isinstance(side_mats, int):
        side_mats = [side_mats] * n
    vb = [bm.verts.new((*g.E(c, r), z0)) for c, r in bottom]
    vt = [bm.verts.new((*g.E(c, r), z1)) for c, r in top]
    f = bm.faces.new(vt)
    f.material_index = top_mat
    if bottom_cap:
        bm.faces.new(list(reversed(vb))).material_index = top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vb[i], vb[j], vt[j], vt[i])).material_index = side_mats[i]


def ellipsoid(bm, x, y, z, a, b, c, segments=12, rings=6, mat=0, smooth=True):
    """An ellipsoid at Blender (x, y, z) with semi-axes a, b, c (units)."""
    n = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((x + v.co.x * a, y + v.co.y * b, z + v.co.z * c))
    _mark(bm, n, mat, smooth)


def loft_y(bm, x, sections, sides=10, mat=0, smooth=True):
    """common.loft along Y moved to column X; sections are (y, half_width, half_height, z)."""
    n, start = len(bm.faces), len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat)
    common.shift_x(bm, start, x)
    _mark(bm, n, mat, smooth)


def loft_x(bm, y, sections, sides=10, mat=0, smooth=True):
    """A loft along X at Blender Y = y; sections are (x, half_depth_y, half_height, z)."""
    n, start = len(bm.faces), len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        # loft builds along +Y with width on X: swap so it runs along +X with depth on Y.
        v.co.x, v.co.y = v.co.y, -v.co.x + y
    _mark(bm, n, mat, smooth)


def mirror_x(bm, axis_x, start_verts=0, start_faces=0):
    """Add a mirror image about X = axis_x of the geometry built since the given indices."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    faces = bm.faces[start_faces:]
    dup = bmesh.ops.duplicate(bm, geom=list(faces))["geom"]
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


def ground(bm, g, pixels, height_of, slot_of, cell=2, skip=None, smooth=True):
    """Jungle ground as a low heightfield on a grid of `cell` px squares over the whole block:
    each grid corner's height is height_of(index) averaged over the pixels round it, and each
    cell takes slot_of(index) of the most common index class among its pixels. Cells for which
    skip(indices) is true (hidden under a building) are left out. Returns nothing."""
    h, w = len(pixels), len(pixels[0])
    verts = {}

    def vert(c, r):
        if (c, r) not in verts:
            vals = [height_of(pixels[rr][cc]) for rr in range(r - cell // 2, r + cell // 2)
                    for cc in range(c - cell // 2, c + cell // 2) if 0 <= rr < h and 0 <= cc < w]
            z = sum(vals) / len(vals)
            verts[(c, r)] = bm.verts.new((*g.E(c, r), z))
        return verts[(c, r)]

    for r in range(0, h, cell):
        for c in range(0, w, cell):
            idx = [pixels[rr][cc] for rr in range(r, min(r + cell, h)) for cc in range(c, min(c + cell, w))]
            if skip and skip(idx):
                continue
            slots = [slot_of(i) for i in idx]
            slot = max(set(slots), key=slots.count)
            quad = [vert(c, r + cell), vert(c + cell, r + cell), vert(c + cell, r), vert(c, r)]
            f = bm.faces.new(quad)
            f.material_index = slot
            f.smooth = smooth
    # Close the sides down to z = 0 round the block's border so the pad reads as solid ground.
    border = []
    for c in range(0, w, cell):
        border.append(((c, h), (c + cell, h)))
    for r in range(h, 0, -cell):
        border.append(((w, r), (w, r - cell)))
    for c in range(w, 0, -cell):
        border.append(((c, 0), (c - cell, 0)))
    for r in range(0, h, cell):
        border.append(((0, r), (0, r + cell)))
    for a, b in border:
        if a not in verts or b not in verts:
            continue
        va, vb = verts[a], verts[b]
        da = bm.verts.new((va.co.x, va.co.y, 0.0))
        db = bm.verts.new((vb.co.x, vb.co.y, 0.0))
        f = bm.faces.new((da, db, vb, va))
        f.material_index = slot_of(-1)
        f.smooth = False


def merged_sprite(root, names):
    """The first name's sprite.json with the colours of every listed sprite merged in."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_pixels(root, layout, w, h):
    """The first frames of the pieces in `layout` [(name, col0, row0)] as one pixel grid."""
    grid = [[-1] * w for _ in range(h)]
    for name, c0, r0 in layout:
        frame = common.load_sprite(root, name)["frames"][0]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[r0 + r][c0 + c] = v
    return grid


def composite_png(pixels, colors, out, pad_w, pad_h):
    """Write a pixel grid as a PNG padded (centred) to pad_w x pad_h for render_preview."""
    h, w = len(pixels), len(pixels[0])
    im = bpy.data.images.new("composite_sprite", pad_w, pad_h, alpha=True)
    buf = [0.0] * (pad_w * pad_h * 4)
    x0, y0 = (pad_w - w) // 2, (pad_h - h) // 2
    for r in range(h):
        for c in range(w):
            v = pixels[r][c]
            if v < 0:
                continue
            rgb = colors[str(v)]
            yy = pad_h - 1 - (y0 + r)
            i = (yy * pad_w + x0 + c) * 4
            buf[i:i + 4] = [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1.0]
    im.pixels[:] = buf
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def ring_y(bm, x, y0, y1, a, c, z, sides=16, mat=0, smooth=True):
    """A short open-ended elliptic band (rib) round the Y axis at column X from y0 to y1."""
    loft_y(bm, x, [(y0, a, c, z), (y1, a, c, z)], sides=sides, mat=mat, smooth=smooth)
