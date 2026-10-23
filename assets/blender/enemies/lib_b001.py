"""Helpers shared by batch b001's model scripts (player ships). Not a model: build-models.sh skips lib_ files."""

import math


def px(x, w=24):
    """Sprite column (pixel centre) to Blender X."""
    return (x + 0.5 - w / 2) / 12


def row(r, h=28):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def loft_path(bm, sections, sides=8, mat_index=0, cap_start=True, cap_end=True):
    """Like common.loft, but each section carries its own X centre so the tube can bend sideways.

    Each section is (y, x_centre, half_width, half_height, z_centre); zero width and height
    collapse the section to a point (a tip)."""
    rings = []
    for y, x, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x, y, z))])
            continue
        rings.append([bm.verts.new((x + w * math.cos(a), y, z + h * math.sin(a)))
                      for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
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
            bm.faces.new(face).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index


def mirrored(sections):
    """The same loft_path sections mirrored across X = 0."""
    return [(y, -x, w, h, z) for y, x, w, h, z in sections]


def box(bm, x0, x1, y0, y1, z0, z1, mat_index=0):
    """An axis-aligned box."""
    v = [bm.verts.new((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        bm.faces.new([v[i] for i in f]).material_index = mat_index
