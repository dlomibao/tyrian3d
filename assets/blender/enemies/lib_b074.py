"""Helpers shared by batch b074's enemy scripts (build-models.sh skips lib_ files)."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def ex(e, w=24):
    """A sprite pixel edge (0 = left edge of column 0) to Blender X."""
    return (e - w / 2) / 12


def ey(e, h=28):
    """A sprite pixel edge (0 = top edge of row 0) to Blender Y: sprite up is +Y."""
    return (h / 2 - e) / 12


def frustum(bm, outline, z0, z1, inset=0.0, mat_index=0, mat_top=None):
    """Extrude a convex outline (CCW seen from above) from z0 to z1, the top shrunk toward the
    outline's centroid by `inset` units: a bevelled plinth."""
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    top = []
    for x, y in outline:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        top.append((x - dx / d * inset, y - dy / d * inset))
    bot = [bm.verts.new((x, y, z0)) for x, y in outline]
    tv = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(tv).material_index = mat_index if mat_top is None else mat_top
    bm.faces.new(list(reversed(bot))).material_index = mat_index
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], tv[j], tv[i])).material_index = mat_index


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box."""
    frustum(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, 0.0, mat_index)


def loft_x(bm, sections, y, z, sides=12, mat_index=0, cap_start=True, cap_end=True):
    """common.loft along +X instead of +Y: sections are (x, half_depth_y, half_height_z),
    centred on (y, z)."""
    start = len(bm.verts)
    common.loft(bm, [(x, w, h, 0.0) for x, w, h in sections], sides=sides, mat_index=mat_index,
                cap_start=cap_start, cap_end=cap_end)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        # loft ring: (w cos a, y_along, h sin a) -> along X, width in Y.
        along, across, up = v.co.y, v.co.x, v.co.z
        v.co.x, v.co.y, v.co.z = along, y - across, z + up
    # The swap mirrors handedness; mesh_object recalculates normals.


def sweep(bm, path, segs=6, mat_index=0, z0=0.0):
    """A rounded ridge lying on the ground along a 2D path: path is [(x, y, half_width, height)].
    Each cross-section is a half ellipse (flat base at z0) perpendicular to the path."""
    rings = []
    n = len(path)
    for i, (x, y, w, h) in enumerate(path):
        xa, ya = path[max(i - 1, 0)][:2]
        xb, yb = path[min(i + 1, n - 1)][:2]
        tx, ty = xb - xa, yb - ya
        d = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / d, tx / d
        ring = []
        for k in range(segs + 1):
            a = math.pi * k / segs
            s, c = math.cos(a), math.sin(a)
            ring.append(bm.verts.new((x + nx * w * s, y + ny * w * s, z0 + h * c)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(segs):
            bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k])).material_index = mat_index
        bm.faces.new((r0[segs], r0[0], r1[0], r1[segs])).material_index = mat_index
    bm.faces.new(rings[0]).material_index = mat_index
    bm.faces.new(list(reversed(rings[-1]))).material_index = mat_index


def dome(bm, cx, cy, z, rx, ry, rz, sides=12, rings=4, mat_index=0):
    """A half ellipsoid standing on z, with a flat base."""
    layers = []
    for k in range(rings):
        a = math.pi / 2 * k / rings
        layers.append([bm.verts.new((cx + rx * math.cos(a) * math.cos(t), cy + ry * math.cos(a) * math.sin(t),
                                     z + rz * math.sin(a)))
                       for t in (2 * math.pi * i / sides for i in range(sides))])
    top = bm.verts.new((cx, cy, z + rz))
    for r0, r1 in zip(layers, layers[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat_index
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((layers[-1][i], layers[-1][j], top)).material_index = mat_index
    bm.faces.new(list(reversed(layers[0]))).material_index = mat_index
