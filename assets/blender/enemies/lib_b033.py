"""Helpers shared by batch b033's model scripts (the newshe.shp orbs).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def sprite_index(pixels, x, y, w=24, h=28):
    """The palette index of the sprite pixel under Blender (x, y), or -1 outside / transparent."""
    c = math.floor(x * 12 + w / 2)
    r = math.floor(h / 2 - y * 12)
    if 0 <= r < len(pixels) and 0 <= c < len(pixels[r]):
        return pixels[r][c]
    return -1


def ellipsoid(bm, cx, cy, a, b, c, rings=16, sides=24, z=0.0, bump=None):
    """An ellipsoid (half sizes a in X, b in Y, c in Z) as a loft along Y with rings in the XZ
    plane. `bump(x, y, z) -> scale` can push vertices in or out along their radius (rough
    surfaces). Returns the faces it made."""
    import bmesh  # noqa: F401
    start = len(bm.faces)
    sections = []
    for i in range(rings + 1):
        t = math.pi * i / rings
        sy = cy + b * math.cos(t)
        s = math.sin(t)
        if i in (0, rings):
            sections.append((sy, 0.0, 0.0, z))
        else:
            sections.append((sy, a * s, c * s, z))
    vstart = len(bm.verts)
    common.loft(bm, sections, sides=sides)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[vstart:]:
        v.co.x += cx
        if bump:
            k = bump(v.co.x, v.co.y, v.co.z)
            v.co.x = cx + (v.co.x - cx) * k
            v.co.y = cy + (v.co.y - cy) * k
            v.co.z = z + (v.co.z - z) * k
    bm.faces.ensure_lookup_table()
    return bm.faces[start:]


def paint_from_sprite(faces, pixels, mapping, default, below=None):
    """Give each face the material of the sprite pixel above its centre (seen from the top):
    `mapping` maps palette index -> material slot; pixels it doesn't list (or transparent ones)
    get `default`. Faces under z = 0 get `below` if given (else the same lookup)."""
    for f in faces:
        cen = f.calc_center_median()
        if below is not None and cen.z < -0.03:
            f.material_index = below
            continue
        idx = sprite_index(pixels, cen.x, cen.y)
        f.material_index = mapping.get(idx, default)


def paint(faces, fn):
    """Give each face the material slot fn(face centre) returns (None keeps its slot)."""
    for f in faces:
        m = fn(f.calc_center_median())
        if m is not None:
            f.material_index = m


def ellipsoid_point(cx, cy, a, b, c, u, v, lift=1.0, z=0.0):
    """The point on the top of an ellipsoid above top-view coordinates (u, v) in units of its
    half sizes (u = (x - cx) / a, v = (y - cy) / b), pushed out by `lift`."""
    w = math.sqrt(max(0.0, 1.0 - u * u - v * v))
    return (cx + a * u * lift, cy + b * v * lift, z + c * w * lift)


def surface_patch(bm, grid, mat_index=0):
    """A sheet of quads through a grid (rows of 3D points, all the same length), e.g. a
    highlight or band lying just above a curved surface. Returns the faces."""
    verts = [[bm.verts.new(p) for p in r] for r in grid]
    faces = []
    for r0, r1 in zip(verts, verts[1:]):
        for i in range(len(r0) - 1):
            f = bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
            f.material_index = mat_index
            faces.append(f)
    return faces


def oval_on_ellipsoid(bm, ell, cu, cv, ru, rv, mat_index, lift=1.006, n=16, rings=3):
    """A smooth oval patch lying on top of ellipsoid `ell` = (cx, cy, a, b, c), centred at (cu, cv)
    with radii (ru, rv), all in units of the ellipsoid's half sizes."""
    cx, cy, a, b, c = ell
    grid = []
    for k in range(rings + 1):
        s = k / rings
        grid.append([ellipsoid_point(cx, cy, a, b, c, cu + ru * s * math.cos(2 * math.pi * i / n),
                                     cv + rv * s * math.sin(2 * math.pi * i / n), lift)
                     for i in range(n + 1)])
    return surface_patch(bm, grid, mat_index)


def band_on_ellipsoid(bm, ell, r0, r1, a0, a1, mat_index, lift=1.006, n=12, steps=4, taper=True):
    """A crescent patch on ellipsoid `ell` between top-view radii r0..r1 (fractions of the half
    sizes) and angles a0..a1 (degrees, counter-clockwise from +X), tapering at the ends."""
    cx, cy, a, b, c = ell
    rows = []
    for k in range(steps + 1):
        s = k / steps
        pts = []
        for i in range(n + 1):
            t = i / n
            ang = math.radians(a0 + (a1 - a0) * t)
            inner = r1 - (r1 - r0) * math.sin(math.pi * t) if taper else r0
            r = inner + (r1 - inner) * s
            pts.append(ellipsoid_point(cx, cy, a, b, c, r * math.cos(ang), r * math.sin(ang), lift))
        rows.append(pts)
    return surface_patch(bm, rows, mat_index)


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview the first.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
    return sprite
