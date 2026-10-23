"""Helpers shared by batch b136's scripts (12x14 ground fragments from newshu.shp).

Coordinates: sprite pixel edges (x = column edge 0..12, y = row edge 0..14, rows counting down)
are turned into Blender units here, so the scripts can lay parts out straight from the pixels.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402,F401

W, H = 12, 14  # a size-1 sprite's block


def ex(x):
    """Sprite column edge to Blender X."""
    return (x - W / 2) / 12


def ey(y):
    """Sprite row edge to Blender Y (sprite up is +Y)."""
    return (H / 2 - y) / 12


def pts(outline):
    """Sprite-edge (x, y) outline to Blender XY, counter-clockwise seen from above."""
    out = [(ex(x), ey(y)) for x, y in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(out, out[1:] + out[:1]))
    return out if area > 0 else list(reversed(out))


def block(bm, outline, z0, z1, mat_index=0):
    """A flat-topped block from sprite-edge outline between heights z0 and z1."""
    common.slab(bm, pts(outline), z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def prism_x(bm, profile, x0, x1, mat_index=0):
    """Extrude a side profile [(row edge, z), ...] along X between column edges x0 and x1."""
    a = [bm.verts.new((ex(x0), ey(r), z)) for r, z in profile]
    b = [bm.verts.new((ex(x1), ey(r), z)) for r, z in profile]
    bm.faces.new(a).material_index = mat_index
    bm.faces.new(list(reversed(b))).material_index = mat_index
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat_index


def mound(bm, outline, centre, levels, mats, pin_x=None, pin_y=None):
    """A rounded mound over a sprite-edge outline: rings of the outline scaled toward `centre`
    (sprite edges) rising through `levels` [(scale, z), ...] from (1, 0) up to (0, top).
    `mats` gives a material index per band between rings (len(levels) - 1). Outline points on the
    column edge `pin_x` or row edge `pin_y` (where the object runs on past the tile) keep that
    coordinate in every ring, so the mound is cut off square there."""
    cx, cy = ex(centre[0]), ey(centre[1])
    base = pts(outline)
    px_ = None if pin_x is None else ex(pin_x)
    py_ = None if pin_y is None else ey(pin_y)
    rings = []
    for s, z in levels:
        if s == 0:
            rings.append([bm.verts.new((cx, cy, z))])
            continue
        ring = []
        for x, y in base:
            nx, ny = cx + (x - cx) * s, cy + (y - cy) * s
            if px_ is not None and abs(x - px_) < 1e-6:
                nx = x
            if py_ is not None and abs(y - py_) < 1e-6:
                ny = y
            ring.append(bm.verts.new((nx, ny, z)))
        rings.append(ring)
    n = len(base)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            if len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mats[k]
    bm.faces.new(list(reversed(rings[0]))).material_index = mats[0]


def preview(objects, root, name, sprite):
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objects, out, ref, size=sprite["frames"][0]["size"])
