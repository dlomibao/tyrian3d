"""Helpers shared by batch b105's model scripts (build-models.sh skips lib_ modules).

Coordinates: a Grid maps sprite pixel edges (col, row; fractions allowed, so pixel c's centre is
c + 0.5) of a w x h px block to Blender X/Y with the block's centre at the origin.
"""

import math
import struct
import zlib

import bmesh
import bpy
from mathutils import Vector


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def x(self, e):
        """Pixel edge column to Blender X."""
        return (e - self.w / 2) / 12

    def y(self, e):
        """Pixel edge row to Blender Y (sprite up is +Y)."""
        return (self.h / 2 - e) / 12

    def xy(self, c, r):
        return self.x(c), self.y(r)


def mark(bm, first_face, smooth):
    """Set the smooth flag of every face added since index `first_face`."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.smooth = smooth


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, smooth=False):
    """An axis-aligned box (Blender units)."""
    n = len(bm.faces)
    xa, xb = min(x0, x1), max(x0, x1)
    ya, yb = min(y0, y1), max(y0, y1)
    v = [bm.verts.new(p) for p in ((xa, ya, z0), (xb, ya, z0), (xb, yb, z0), (xa, yb, z0),
                                   (xa, ya, z1), (xb, ya, z1), (xb, yb, z1), (xa, yb, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f]).material_index = mat
    mark(bm, n, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an outline (Blender XY, any winding) from z0 to z1."""
    n = len(bm.faces)
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    top = [bm.verts.new((x, y, z1)) for x, y in outline]
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(bot))).material_index = mat
    k = len(outline)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((bot[i], bot[j], top[j], top[i])).material_index = mat
    mark(bm, n, smooth)


def ellipsoid(bm, centre, radii, mat=0, segments=12, rings=6, half=False, smooth=True):
    """A closed ellipsoid at `centre` with semi-axes `radii`; `half` keeps only the top half
    (closed flat underneath at the centre's height)."""
    n = len(bm.faces)
    c = Vector(centre)
    rx, ry, rz = radii
    top = bm.verts.new(c + Vector((0, 0, rz)))
    lat = []
    last = rings // 2 if half else rings - 1
    for i in range(1, last + 1):
        phi = math.pi * i / rings
        lat.append([bm.verts.new(c + Vector((rx * math.sin(phi) * math.cos(2 * math.pi * j / segments),
                                             ry * math.sin(phi) * math.sin(2 * math.pi * j / segments),
                                             rz * math.cos(phi)))) for j in range(segments)])
    for j in range(segments):
        k = (j + 1) % segments
        bm.faces.new((top, lat[0][j], lat[0][k])).material_index = mat
        for r0, r1 in zip(lat, lat[1:]):
            bm.faces.new((r0[j], r1[j], r1[k], r0[k])).material_index = mat
    if half:
        bm.faces.new(list(reversed(lat[-1]))).material_index = mat
    else:
        bottom = bm.verts.new(c - Vector((0, 0, rz)))
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((bottom, lat[-1][k], lat[-1][j])).material_index = mat
    mark(bm, n, smooth)


class Dome:
    """The top half of an ellipsoid with semi-axes rx, ry (XY) and height h, base at z0."""

    def __init__(self, cx, cy, rx, ry, h, z0=0.0):
        self.cx, self.cy, self.rx, self.ry, self.h, self.z0 = cx, cy, rx, ry, h, z0

    def z(self, x, y):
        u = ((x - self.cx) / self.rx) ** 2 + ((y - self.cy) / self.ry) ** 2
        return self.z0 + self.h * math.sqrt(max(0.0, 1 - u))

    def build(self, bm, mat=0, segments=32, rings=16):
        ellipsoid(bm, (self.cx, self.cy, self.z0), (self.rx, self.ry, self.h), mat=mat,
                  segments=segments, rings=rings, half=True)


def drape(bm, surface, x0, y0, x1, y1, lift, mat=0, n=3, depth=0.04, side_mat=None):
    """A plate whose top follows `surface` (anything with z(x, y)) `lift` above it over the
    rectangle x0..x1, y0..y1 (an n x n grid), closed underneath `depth` below the surface."""
    first = len(bm.faces)
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    ys = [y0 + (y1 - y0) * j / n for j in range(n + 1)]
    top = [[bm.verts.new((x, y, surface.z(x, y) + lift)) for x in xs] for y in ys]
    bot = [[bm.verts.new((x, y, surface.z(x, y) - depth)) for x in xs] for y in ys]
    for j in range(n):
        for i in range(n):
            bm.faces.new((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i])).material_index = mat
            bm.faces.new((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1])).material_index = mat
    sm = mat if side_mat is None else side_mat
    ring = [(0, i) for i in range(n)] + [(j, n) for j in range(n)] + \
           [(n, i) for i in range(n, 0, -1)] + [(j, 0) for j in range(n, 0, -1)]
    for k, (j, i) in enumerate(ring):
        j2, i2 = ring[(k + 1) % len(ring)]
        bm.faces.new((bot[j][i], bot[j2][i2], top[j2][i2], top[j][i])).material_index = sm
    mark(bm, first, False)


def tube(bm, points, radius, mat=0, sides=6, caps=True, smooth=True):
    """A tube through 3D points with a constant (or per-point list of) radius."""
    first = len(bm.faces)
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) +
                                        b * math.sin(2 * math.pi * k / sides)) * radii[i]) for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat
    if caps:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat
    mark(bm, first, smooth)


def components(grid_pixels, keep):
    """Connected regions (4-neighbour) of pixels for which keep(col, row, index) is true:
    a list of lists of (col, row)."""
    h, w = len(grid_pixels), len(grid_pixels[0])
    seen = set()
    out = []
    for r in range(h):
        for c in range(w):
            if (c, r) in seen or not keep(c, r, grid_pixels[r][c]):
                continue
            stack, comp = [(c, r)], []
            seen.add((c, r))
            while stack:
                p = stack.pop()
                comp.append(p)
                pc, pr = p
                for q in ((pc + 1, pr), (pc - 1, pr), (pc, pr + 1), (pc, pr - 1)):
                    qc, qr = q
                    if 0 <= qc < w and 0 <= qr < h and q not in seen and keep(qc, qr, grid_pixels[qr][qc]):
                        seen.add(q)
                        stack.append(q)
            out.append(comp)
    return out


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


def write_png(path, rows):
    """Write an RGBA image (rows of (r, g, b, a) 0-255 tuples, top row first) as a PNG."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(v for px in row for v in px) for row in rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def compose_pixels(pieces, w, h, scale=12):
    """Image rows for several sprite frames placed in one w x h px grid: pieces is a list of
    (frame_pixels, colors, x0, y0). Transparent where no piece has a pixel."""
    grid = [[None] * w for _ in range(h)]
    for pixels, colors, x0, y0 in pieces:
        for r, row in enumerate(pixels):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    grid[y0 + r][x0 + c] = (*colors[str(v)], 255)
    out = []
    for row in grid:
        line = []
        for px in row:
            line.extend([px or (0, 0, 0, 0)] * scale)
        out.extend([line] * scale)
    return out


def compose_grid(pieces, w, h):
    """Palette-index grid (-1 transparent) of several frames placed in one w x h px block:
    pieces is a list of (frame_pixels, x0, y0)."""
    grid = [[-1] * w for _ in range(h)]
    for pixels, x0, y0 in pieces:
        for r, row in enumerate(pixels):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    grid[y0 + r][x0 + c] = v
    return grid
