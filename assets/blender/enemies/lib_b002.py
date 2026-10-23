"""Helpers shared by batch b002's model scripts (build-models.sh skips lib_ modules).

Coordinates are sprite pixel *edges* in a 24x28 block: column c runs from c to c + 1 and row r
from r to r + 1, so a pixel's centre is (c + 0.5, r + 0.5). X(c) and Y(r) turn them into Blender
units (sprite up is +Y, 1 px = 1/12 unit, the block's centre is the origin).
"""

import math

import bmesh

W, H = 24, 28


def X(c):
    """Sprite x (pixel edges) to Blender X."""
    return (c - W / 2) / 12


def Y(r):
    """Sprite y (pixel edges, down the sprite) to Blender Y."""
    return (H / 2 - r) / 12


def P(px):
    """Pixels to units."""
    return px / 12


def _ring_point(a, power):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)


def loft(bm, sections, sides=12, mat=0, power=1.0, cap_start=True, cap_end=True):
    """Loft rings along the sprite's rows. Each section is (row, col, half_w, half_h, z) with row
    and col in pixel edges and half_w, half_h, z in pixels. A section with zero half width and
    height is a point (a tip). power < 1 squares the cross-section off (0.5 is a rounded box)."""
    rings = []
    for r, c, hw, hh, z in sections:
        y, x = Y(r), X(c)
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, P(z)))])
            continue
        ring = []
        for i in range(sides):
            u, v = _ring_point(2 * math.pi * (i + 0.5) / sides, power)
            ring.append(bm.verts.new((x + P(hw) * u, y, P(z) + P(hh) * v)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat


def slab(bm, outline, z0, z1, mat=0, bevel=0.0):
    """Extrude an outline of (col, row) pixel-edge points between heights z0 and z1 (pixels).
    bevel (pixels) insets the top face for a chamfered edge."""
    pts = [(X(c), Y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    bottom = [bm.verts.new((x, y, P(z0))) for x, y in pts]
    if bevel:
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        top = []
        for x, y in pts:
            dx, dy = cx - x, cy - y
            d = math.hypot(dx, dy) or 1
            k = min(P(bevel) / d, 0.9)
            top.append(bm.verts.new((x + dx * k, y + dy * k, P(z1))))
    else:
        top = [bm.verts.new((x, y, P(z1))) for x, y in pts]
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(bottom))).material_index = mat
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i])).material_index = mat


def dome(bm, c, r, rx, ry, h, z=0.0, rings=4, sides=12, mat=0, bottom=True):
    """A half ellipsoid on the plane at height z (pixels), centred on (col, row) pixel edges, with
    radii rx, ry and height h in pixels. bottom closes its base. A negative h hangs it down."""
    x0, y0 = X(c), Y(r)
    loops = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        loops.append([bm.verts.new((x0 + P(rx) * math.cos(t) * math.cos(a), y0 + P(ry) * math.cos(t) * math.sin(a),
                                    P(z + h * math.sin(t))))
                      for a in (2 * math.pi * i / sides for i in range(sides))])
    tip = bm.verts.new((x0, y0, P(z + h)))
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mat
    for i in range(sides):
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % sides], tip)).material_index = mat
    if bottom:
        bm.faces.new(list(reversed(loops[0]))).material_index = mat


def mirror(axis, c):
    """Mirror a column about the column `axis` (pixel edges)."""
    return 2 * axis - c


def tube(bm, points, sides=8, mat=0, power=1.0, cap_start=True, cap_end=True):
    """Like loft, but along a path in the sprite plane: points are (col, row, half_w, half_h, z)
    (pixels, edges). Each ring is square to the path, half_w across it and half_h up. Zero half
    width and height is a tip. Leaves, curved bands and bent tubes."""
    pos = [(X(c), Y(r)) for c, r, *_ in points]
    rings = []
    for i, (c, r, hw, hh, z) in enumerate(points):
        x, y = pos[i]
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, P(z)))])
            continue
        (x0, y0), (x1, y1) = pos[max(i - 1, 0)], pos[min(i + 1, len(pos) - 1)]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        ring = []
        for k in range(sides):
            u, v = _ring_point(2 * math.pi * (k + 0.5) / sides, power)
            ring.append(bm.verts.new((x + nx * P(hw) * u, y + ny * P(hw) * u, P(z) + P(hh) * v)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat
