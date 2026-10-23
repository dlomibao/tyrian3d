"""Helpers shared by batch b005's model scripts (build-models.sh skips lib_ modules).

- Dome: an oblate spheroid (a squashed ball) and the surface/normal queries the relief parts use.
- patch: a rounded lump that sits on a dome's surface, following its curve (organs, lenses).
- surface_tube: a tube laid along a path drawn in top view, hugging a dome (ribs, veins, rims).
- frame grouping and a pure-Python PNG writer for assembly reference images.
"""

import math
import struct
import zlib

from mathutils import Matrix, Vector


def grid_x(c, w):
    """Sprite column (pixel centre) of a grid w px wide to Blender X."""
    return (c + 0.5 - w / 2) / 12


def grid_y(r, h):
    """Sprite row (pixel centre) of a grid h px tall to Blender Y (sprite up is +Y)."""
    return (h / 2 - (r + 0.5)) / 12


class Dome:
    """An oblate spheroid: radius `r` in XY around (cx, cy), half height `h`, centred on z = zc."""

    def __init__(self, r, h, cx=0.0, cy=0.0, zc=0.0):
        self.r, self.h, self.cx, self.cy, self.zc = r, h, cx, cy, zc

    def clamp(self, x, y, margin=0.995):
        dx, dy = x - self.cx, y - self.cy
        d = math.hypot(dx, dy)
        lim = self.r * margin
        if d > lim:
            dx, dy = dx * lim / d, dy * lim / d
        return self.cx + dx, self.cy + dy

    def z(self, x, y):
        """Top surface height above (x, y) (clamped to the dome's outline)."""
        x, y = self.clamp(x, y)
        q = 1 - ((x - self.cx) ** 2 + (y - self.cy) ** 2) / self.r ** 2
        return self.zc + self.h * math.sqrt(max(q, 0.0))

    def normal(self, x, y):
        x, y = self.clamp(x, y)
        z = self.z(x, y) - self.zc
        n = Vector(((x - self.cx) / self.r ** 2, (y - self.cy) / self.r ** 2, z / self.h ** 2))
        return n.normalized()

    def point(self, x, y, lift=0.0):
        x, y = self.clamp(x, y)
        return Vector((x, y, self.z(x, y))) + self.normal(x, y) * lift

    def build(self, bm, mat_index=0, segments=40, rings=20):
        """The spheroid itself (closed)."""
        top = bm.verts.new((self.cx, self.cy, self.zc + self.h))
        bottom = bm.verts.new((self.cx, self.cy, self.zc - self.h))
        lat = []
        for i in range(1, rings):
            phi = math.pi * i / rings  # from the top
            ring = []
            for j in range(segments):
                a = 2 * math.pi * j / segments
                ring.append(bm.verts.new((self.cx + self.r * math.sin(phi) * math.cos(a),
                                          self.cy + self.r * math.sin(phi) * math.sin(a),
                                          self.zc + self.h * math.cos(phi))))
            lat.append(ring)
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((top, lat[0][j], lat[0][k])).material_index = mat_index
            bm.faces.new((bottom, lat[-1][k], lat[-1][j])).material_index = mat_index
            for r0, r1 in zip(lat, lat[1:]):
                bm.faces.new((r0[j], r1[j], r1[k], r0[k])).material_index = mat_index


def patch(bm, dome, cx, cy, rx, ry, height, angle=0.0, mat_index=0, sides=16, rings=4, depth=0.05):
    """A rounded lump on the dome's surface: an ellipse (rx, ry, rotated by `angle` radians) in top
    view centred on (cx, cy), rising `height` above the surface at its centre. Closed underneath
    (sunk `depth` below the surface) so it can be cut cleanly."""
    ca, sa = math.cos(angle), math.sin(angle)

    def at(u, t, lift):
        lx, ly = rx * u * math.cos(t), ry * u * math.sin(t)
        return dome.point(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, lift)

    centre = bm.verts.new(at(0, 0, height))
    rings_v = []
    for i in range(1, rings + 1):
        u = i / rings
        lift = height * math.sqrt(max(1 - u * u, 0.0)) if i < rings else -0.012
        rings_v.append([bm.verts.new(at(u, 2 * math.pi * j / sides, lift)) for j in range(sides)])
    under = bm.verts.new(at(0, 0, -depth))
    for j in range(sides):
        k = (j + 1) % sides
        bm.faces.new((centre, rings_v[0][j], rings_v[0][k])).material_index = mat_index
        for r0, r1 in zip(rings_v, rings_v[1:]):
            bm.faces.new((r0[j], r1[j], r1[k], r0[k])).material_index = mat_index
        bm.faces.new((under, rings_v[-1][k], rings_v[-1][j])).material_index = mat_index


def _catmull(pts, n):
    """Resample a polyline of 2D points to n points along a Catmull-Rom spline through them."""
    pts = [Vector((p[0], p[1])) for p in pts]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    segs = len(pts) - 1
    for i in range(n):
        s = i / (n - 1) * segs
        k = min(int(s), segs - 1)
        t = s - k
        p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    return out


def surface_tube(bm, dome, pts, radius, lift=0.0, mat_index=0, sides=6, samples=14, taper=0.35, flat=1.0,
                 z_of=None):
    """A tube along a path given in top view (Blender XY), lying on the dome (its axis `lift` above
    the surface along the normal) or, with z_of(x, y), at that height. Ends taper to points.
    `flat` scales the cross-section along the surface normal."""
    path2 = _catmull(pts, samples)
    centres, normals = [], []
    for p in path2:
        if z_of is None:
            centres.append(dome.point(p.x, p.y, lift))
            normals.append(dome.normal(p.x, p.y))
        else:
            centres.append(Vector((p.x, p.y, z_of(p.x, p.y))))
            normals.append(Vector((0, 0, 1)))
    rings_v = []
    n = len(centres)
    for i, (c, nz) in enumerate(zip(centres, normals)):
        tan = (centres[min(i + 1, n - 1)] - centres[max(i - 1, 0)]).normalized()
        side = tan.cross(nz).normalized()
        up = side.cross(tan).normalized()
        t = i / (n - 1)
        edge = min(t, 1 - t) / taper if taper > 0 else 1.0
        rr = radius * (math.sin(min(edge, 1.0) * math.pi / 2) if taper > 0 else 1.0)
        if i in (0, n - 1):
            rings_v.append([bm.verts.new(c)])
            continue
        ring = []
        for j in range(sides):
            a = 2 * math.pi * (j + 0.5) / sides
            ring.append(bm.verts.new(c + side * rr * math.cos(a) + up * rr * flat * math.sin(a)))
        rings_v.append(ring)
    for r0, r1 in zip(rings_v, rings_v[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                face = (r0[j], r1[0], r0[k])
            else:
                face = (r0[j], r1[j], r1[k], r0[k])
            bm.faces.new(face).material_index = mat_index


def ellipsoid(bm, centre, radii, mat_index=0, segments=12, rings=6, rot=None):
    """A closed ellipsoid at `centre` with semi-axes `radii`, optionally rotated by matrix `rot`."""
    rot = rot or Matrix.Identity(3)
    c = Vector(centre)
    rx, ry, rz = radii

    def v(x, y, z):
        return bm.verts.new(c + rot @ Vector((x * rx, y * ry, z * rz)))

    top, bottom = v(0, 0, 1), v(0, 0, -1)
    lat = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        lat.append([v(math.sin(phi) * math.cos(2 * math.pi * j / segments),
                      math.sin(phi) * math.sin(2 * math.pi * j / segments), math.cos(phi))
                    for j in range(segments)])
    for j in range(segments):
        k = (j + 1) % segments
        bm.faces.new((top, lat[0][j], lat[0][k])).material_index = mat_index
        bm.faces.new((bottom, lat[-1][k], lat[-1][j])).material_index = mat_index
        for r0, r1 in zip(lat, lat[1:]):
            bm.faces.new((r0[j], r1[j], r1[k], r0[k])).material_index = mat_index


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
