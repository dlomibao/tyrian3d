"""Helpers for batch b099's model scripts (build-models.sh skips lib_ modules).

Coordinates are assembly pixel *edges*: column c runs from c to c + 1 and row r from r to r + 1
(a pixel's centre is c + 0.5, r + 0.5), down the sprite. X(c) and Y(r) turn them into Blender
units for a block W x H px centred on the origin (sprite up is +Y, 1 px = 1/12 unit). Heights (z)
are in units.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


class Grid:
    """Pixel-edge to Blender conversion for a W x H px block centred on the origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        return (c - self.w / 2) * PX

    def Y(self, r):
        return (self.h / 2 - r) * PX


def _se(t, p):
    """Superellipse coordinate: sign(t) |t|^(2/p) (p = 2 is an ellipse, larger is boxier)."""
    return math.copysign(abs(t) ** (2.0 / p), t)


def hull(bm, g, sections, n=12, p=3.0, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A loft down the sprite of upper-half superellipse sections standing on a flat base.
    Each section is (row, col_left, col_right, height, z0[, mat]) with row and cols in pixel edges
    and height, z0 in units. A section's own mat (if given) paints the strip after it."""
    rings = []
    mats = []
    for s in sections:
        r, cl, cr, h, z0 = s[:5]
        mats.append(s[5] if len(s) > 5 else mat)
        xc, hw = g.X((cl + cr) / 2), (cr - cl) / 2 * PX
        y = g.Y(r)
        ring = []
        for i in range(n + 1):
            a = math.pi * i / n
            ring.append(bm.verts.new((xc + hw * _se(math.cos(a), p), y, z0 + h * abs(math.sin(a)) ** (2.0 / p))))
        rings.append(ring)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            f = bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
            f.material_index = mats[k]
            f.smooth = smooth
        f = bm.faces.new((r0[n], r0[0], r1[0], r1[n]))
        f.material_index = mats[k]
    if cap_start:
        bm.faces.new(list(reversed(rings[0]))).material_index = mats[0]
    if cap_end:
        bm.faces.new(rings[-1]).material_index = mats[-1]


def hull_z(g, sections, c, r, p=3.0):
    """Height of a hull's top surface at pixel (c, r) (edges), 0 outside it."""
    rows = [s[0] for s in sections]
    if r <= rows[0] or r >= rows[-1]:
        return 0.0
    k = next(i for i in range(len(rows) - 1) if rows[i] <= r <= rows[i + 1])
    a, b = sections[k], sections[k + 1]
    t = (r - a[0]) / ((b[0] - a[0]) or 1)
    cl, cr, h, z0 = (a[i] + (b[i] - a[i]) * t for i in (1, 2, 3, 4))
    hw = (cr - cl) / 2
    u = abs(c - (cl + cr) / 2) / hw if hw else 1
    if u >= 1:
        return 0.0
    return z0 + h * (1 - u ** p) ** (1 / p)


def mound(bm, g, c, r, rx, ry, h, z0=0.0, p=2.0, pz=None, seg=16, rings=5, mat=0, smooth=True, bottom=True):
    """An upper-half superellipsoid: footprint centred on (col, row) (edges) with radii rx, ry px
    (superellipse exponent p, boxier when larger), rising h units above z0 (profile pz)."""
    pz = pz or p
    x0, y0 = g.X(c), g.Y(r)
    loops = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        rad = math.cos(t) ** (2.0 / pz)
        z = z0 + h * math.sin(t) ** (2.0 / pz)
        loops.append([bm.verts.new((x0 + rx * PX * rad * _se(math.cos(a), p), y0 + ry * PX * rad * _se(math.sin(a), p), z))
                      for a in (2 * math.pi * (i + 0.5) / seg for i in range(seg))])
    tip = bm.verts.new((x0, y0, z0 + h))
    faces = []
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            faces.append(bm.faces.new((l0[i], l0[j], l1[j], l1[i])))
    for i in range(seg):
        faces.append(bm.faces.new((loops[-1][i], loops[-1][(i + 1) % seg], tip)))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    if bottom:
        bm.faces.new(list(reversed(loops[0]))).material_index = mat


def tube(bm, g, points, sides=8, mat=0, p=2.0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, half_width_px, half_height_units, z_units) points (pixel
    edges), each ring square to the path in the sprite plane. Zero half width and height is a tip."""
    pos = [(g.X(c), g.Y(r)) for c, r, *_ in points]
    rings = []
    for i, (c, r, hw, hh, z) in enumerate(points):
        x, y = pos[i]
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, z))])
            continue
        (xa, ya), (xb, yb) = pos[max(i - 1, 0)], pos[min(i + 1, len(pos) - 1)]
        dx, dy = xb - xa, yb - ya
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            u, v = _se(math.cos(a), p), _se(math.sin(a), p)
            ring.append(bm.verts.new((x + nx * hw * PX * u, y + ny * hw * PX * u, z + hh * v)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[k])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[k], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def prism(bm, g, outline, z0, z1, mat=0, inset=0.0, smooth=False):
    """Extrude an outline of (col, row) pixel-edge points from z0 to z1 (units). inset (px)
    shrinks the top face toward the centroid for a chamfer."""
    pts = [(g.X(c), g.Y(r)) for c, r in outline]
    area = sum(xa * yb - xb * ya for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = []
    for x, y in pts:
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1
        k = min(inset * PX / d, 0.9) if inset else 0.0
        top.append(bm.verts.new((x + dx * k, y + dy * k, z1)))
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bottom)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0, inset=0.0):
    prism(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat, inset=inset)


def ring(bm, g, c, r, r_out, r_in, z0, z1, sides=16, mat=0, smooth=True):
    """An annulus (a pipe end or a muzzle ring) standing from z0 to z1, radii in px."""
    x0, y0 = g.X(c), g.Y(r)
    loops = []
    for rad, z in ((r_out, z0), (r_out, z1), (r_in, z1), (r_in, z0)):
        loops.append([bm.verts.new((x0 + rad * PX * math.cos(a), y0 + rad * PX * math.sin(a), z))
                      for a in (2 * math.pi * i / sides for i in range(sides))])
    for l0, l1 in zip(loops, loops[1:] + loops[:1]):
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((l0[i], l0[j], l1[j], l1[i]))
            f.material_index = mat
            f.smooth = smooth


def mirror_new(bm, g, start_vert, start_face, axis_col):
    """Duplicate everything added since (start_vert, start_face) mirrored about column axis_col."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    faces = bm.faces[start_face:]
    verts = bm.verts[start_vert:]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + list(faces))["geom"]
    ax = g.X(axis_col)
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


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece, so any index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite(root, layout):
    """The assembly's pixels {(col, row): index} and colours from the layout frames.
    layout is sprite.json assemblyLayout; returns (pixels, colours, min_cx, min_cy, w, h)."""
    min_cx = min(e["cx"] for e in layout) - 12
    min_cy = min(e["cy"] for e in layout) - 14
    w = max(e["cx"] for e in layout) + 12 - min_cx
    h = max(e["cy"] for e in layout) + 14 - min_cy
    pixels, colours = {}, {}
    for e in layout:
        data = common.load_sprite(root, e["model"])
        colours.update(data["colors"])
        index = int(e["frame"].split("|")[2])
        frame = next(f for f in data["frames"] if f["index"] == index)
        x0, y0 = e["cx"] - 12 - min_cx, e["cy"] - 14 - min_cy
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    pixels[(x0 + c, y0 + r)] = v
    return pixels, colours, min_cx, min_cy, w, h


def composite_png(pixels, colours, w, h, out, pad_to=None):
    """Write the composite as a PNG, centred in a pad_to = (W, H) canvas (render_preview wants
    the 24:28 shape)."""
    import numpy as np
    pw, ph = pad_to or (w, h)
    img = np.zeros((ph, pw, 4), dtype=np.float32)
    x0, y0 = (pw - w) // 2, (ph - h) // 2
    for (c, r), v in pixels.items():
        img[y0 + r, x0 + c] = [*(ch / 255 for ch in colours[str(v)]), 1.0]
    im = bpy.data.images.new("b099_composite", pw, ph, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
