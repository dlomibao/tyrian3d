"""Helpers shared by batch b102's model scripts (build-models.sh skips lib_ modules).

Adapted from lib_b005 (Dome, patch, surface_tube): here the dome is an elliptical half spheroid
standing on z = 0 (ground objects build upward), and relief parts follow its surface.
"""

import math

from mathutils import Vector


def px(c, w=24):
    """Sprite column (pixel centre, may be fractional) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    """Sprite row (pixel centre, may be fractional) to Blender Y (sprite up is +Y)."""
    return (h / 2 - (r + 0.5)) / 12


class HalfDome:
    """Upper half of a spheroid with semi-axes rx, ry (top view) and height h, base on z = 0."""

    def __init__(self, cx, cy, rx, ry, h):
        self.cx, self.cy, self.rx, self.ry, self.h = cx, cy, rx, ry, h

    def clamp(self, x, y, margin=0.98):
        dx, dy = (x - self.cx) / self.rx, (y - self.cy) / self.ry
        d = math.hypot(dx, dy)
        if d > margin:
            dx, dy = dx * margin / d, dy * margin / d
        return self.cx + dx * self.rx, self.cy + dy * self.ry

    def z(self, x, y):
        x, y = self.clamp(x, y)
        q = 1 - ((x - self.cx) / self.rx) ** 2 - ((y - self.cy) / self.ry) ** 2
        return self.h * math.sqrt(max(q, 0.0))

    def normal(self, x, y):
        x, y = self.clamp(x, y)
        n = Vector(((x - self.cx) / self.rx ** 2, (y - self.cy) / self.ry ** 2, self.z(x, y) / self.h ** 2))
        return n.normalized()

    def point(self, x, y, lift=0.0):
        x, y = self.clamp(x, y)
        return Vector((x, y, self.z(x, y))) + self.normal(x, y) * lift

    def build(self, bm, ring_mats, segments=24, bottom_mat=None):
        """The dome, closed by a flat base. `ring_mats` gives a material per latitude band, top
        band first (its length sets the number of bands)."""
        rings = len(ring_mats)
        top = bm.verts.new((self.cx, self.cy, self.h))
        lat = []
        for i in range(1, rings + 1):
            phi = math.pi / 2 * i / rings
            lat.append([bm.verts.new((self.cx + self.rx * math.sin(phi) * math.cos(2 * math.pi * j / segments),
                                      self.cy + self.ry * math.sin(phi) * math.sin(2 * math.pi * j / segments),
                                      self.h * math.cos(phi))) for j in range(segments)])
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((top, lat[0][j], lat[0][k])).material_index = ring_mats[0]
            for b, (r0, r1) in enumerate(zip(lat, lat[1:]), start=1):
                bm.faces.new((r0[j], r1[j], r1[k], r0[k])).material_index = ring_mats[b]
        bm.faces.new(list(reversed(lat[-1]))).material_index = ring_mats[-1] if bottom_mat is None else bottom_mat


def patch(bm, dome, cx, cy, rx, ry, height, angle=0.0, mat_index=0, sides=16, rings=4, depth=0.05):
    """A rounded lump on the dome's surface: an ellipse (rx, ry rotated by `angle`) in top view
    centred on (cx, cy), rising `height` above the surface at its centre, closed underneath."""
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
    """Resample 2D points to n points along a Catmull-Rom spline through them."""
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


def surface_tube(bm, dome, pts, radius, lift=0.0, mat_index=0, sides=6, samples=14, taper=0.35, flat=1.0):
    """A tube along a top-view path (Blender XY) lying on the dome, its axis `lift` above the
    surface. `radius` is a number or (start, end) to grow along the path. Ends taper to points.
    `flat` scales the cross-section along the surface normal."""
    path2 = _catmull(pts, samples)
    centres = [dome.point(p.x, p.y, lift) for p in path2]
    normals = [dome.normal(p.x, p.y) for p in path2]
    r0, r1 = radius if isinstance(radius, (tuple, list)) else (radius, radius)
    rings_v = []
    n = len(centres)
    for i, (c, nz) in enumerate(zip(centres, normals)):
        if i in (0, n - 1):
            rings_v.append([bm.verts.new(c)])
            continue
        tan = (centres[i + 1] - centres[i - 1]).normalized()
        side = tan.cross(nz).normalized()
        up = side.cross(tan).normalized()
        t = i / (n - 1)
        edge = min(t, 1 - t) / taper if taper > 0 else 1.0
        rr = (r0 + (r1 - r0) * t) * (math.sin(min(edge, 1.0) * math.pi / 2) if taper > 0 else 1.0)
        rings_v.append([bm.verts.new(c + side * rr * math.cos(2 * math.pi * (j + 0.5) / sides)
                                     + up * rr * flat * math.sin(2 * math.pi * (j + 0.5) / sides))
                        for j in range(sides)])
    for a, b in zip(rings_v, rings_v[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            if len(a) == 1:
                face = (a[0], b[j], b[k])
            elif len(b) == 1:
                face = (a[j], b[0], a[k])
            else:
                face = (a[j], b[j], b[k], a[k])
            bm.faces.new(face).material_index = mat_index
