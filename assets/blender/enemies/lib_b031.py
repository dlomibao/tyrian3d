"""Helpers shared by batch b031's model scripts (build-models.sh skips lib_ modules).

Coordinates are sprite pixel *edges*: column c runs from c to c + 1 and row r from r to r + 1, so a
pixel's centre is (c + 0.5, r + 0.5). X(c) and Y(r) turn them into Blender units for a 24x28 block
(sprite up is +Y, 1 px = 1/12 unit, the block's centre is the origin); pass w=12, h=14 for size-1
sprites. Heights (z) are in pixels too. Every builder marks its faces smooth or flat, and
`to_object` keeps those flags.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

W, H = 24, 28


def X(c, w=W):
    """Sprite x (pixel edges) to Blender X."""
    return (c - w / 2) / 12


def Y(r, h=H):
    """Sprite y (pixel edges, down the sprite) to Blender Y."""
    return (h / 2 - r) / 12


def P(px):
    """Pixels to units."""
    return px / 12


def _ring_point(a, power):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)


def _join(bm, rings, mat, smooth, cap_start, cap_end):
    faces = []
    sides = max(len(r) for r in rings)
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
            faces.append(bm.faces.new(face))
    if cap_start and len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0])))
        f.smooth = False
        f.material_index = mat
    if cap_end and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.smooth = False
        f.material_index = mat
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def tube(bm, points, sides=10, mat=0, power=1.0, smooth=True, cap_start=True, cap_end=True, xy=(W, H)):
    """A tube along a path in the sprite plane: points are (col, row, half_w, half_h, z) in pixels
    (edges). Each ring stands square to the path, half_w across it and half_h up; zero half width
    and height is a tip. power < 1 squares the cross-section off (0.5 is a rounded box). A path
    straight down the rows is a fuselage loft."""
    w, h = xy
    pos = [(X(c, w), Y(r, h)) for c, r, *_ in points]
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
    _join(bm, rings, mat, smooth, cap_start, cap_end)


def loft_y(bm, col, sections, **kw):
    """A tube down the sprite (along rows) centred on column `col`: sections are
    (row, half_w, half_h, z) in pixels."""
    tube(bm, [(col, r, hw, hh, z) for r, hw, hh, z in sections], **kw)


def loft_x(bm, row, sections, **kw):
    """A tube across the sprite (along columns) centred on row `row`: sections are
    (col, half_w, half_h, z) in pixels, half_w measured along the rows."""
    tube(bm, [(c, row, hw, hh, z) for c, hw, hh, z in sections], **kw)


def slab(bm, outline, z0, z1, mat=0, bevel=0.0, smooth=False, xy=(W, H)):
    """Extrude an outline of (col, row) pixel-edge points between heights z0 and z1 (pixels).
    bevel (pixels) shrinks the top face towards the outline's centre for a chamfered edge."""
    w, h = xy
    pts = [(X(c, w), Y(r, h)) for c, r in outline]
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
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bottom)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def box(bm, c0, r0, c1, r1, z0, z1, mat=0, bevel=0.0, xy=(W, H)):
    """An axis-aligned block over pixel edges c0..c1, r0..r1, heights z0..z1 (pixels)."""
    slab(bm, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat, bevel=bevel, xy=xy)


def ellipsoid(bm, c, r, z, rx, ry, rz, mat=0, segments=14, rings=7, lower=1.0, smooth=True, xy=(W, H)):
    """An ellipsoid centred on (col, row) pixel edges at height z, radii in pixels. lower < 1
    flattens the underside (0 makes a dome on a flat base)."""
    w, h = xy
    x0, y0 = X(c, w), Y(r, h)
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        k = 1.0 if v.co.z >= 0 else lower
        v.co.x, v.co.y, v.co.z = x0 + v.co.x * P(rx), y0 + v.co.y * P(ry), P(z + v.co.z * rz * k)
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def mirror_x(bm, axis_c, start_vert=0, xy=(W, H)):
    """Add a mirror image, about pixel-edge column `axis_c`, of the geometry whose vertices were
    all added at or after index `start_vert`."""
    w, _ = xy
    ax = X(axis_c, w)
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + faces)["geom"]
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


def faces(obj):
    return len(obj.data.polygons)


def merged_sprite(root, names):
    """The first name's sprite.json with the colours of every listed sprite merged in, so any of
    their palette indices is valid for palette_material."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w, h, x0, y0):
    """The first frames of several pieces as one image (w x h px; piece centre (cx, cy) lands at
    pixel (cx + x0, cy + y0)), for render_preview."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        pw, ph = (24, 28) if frame["size"] == 2 else (12, 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                yy, xx = cy + y0 - ph // 2 + r, cx + x0 - pw // 2 + c
                if v >= 0 and 0 <= yy < h and 0 <= xx < w:
                    img[yy, xx] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def preview_arg():
    if "--preview" in sys.argv:
        return sys.argv[sys.argv.index("--preview") + 1]
    return None


def run_single(root, name, build):
    """The usual main for one model: build(sprite) -> object; export it with every sprite frame
    and, with -- --preview <png>, render the preview."""
    sprite = common.load_sprite(root, name)
    obj = build(sprite)
    common.export_sprite_model(root, [obj], f"enemies/{name}", sprite["sprites"])
    out = preview_arg()
    if out:
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview([obj], out, ref, size=frame["size"])
    return obj


def stock_half(bm, m, c0=0.0, w=W, dz=0.0, fin_end=24.0):
    """The left half of the tank-and-teeth shape that newshc-197/199 (green and pink) and newshc-269
    (grey and blue, the stock of the big gun) share: a tank lying across the sprite (rows 3-9) with
    two grooved rings near its inner end, a bar under it (rows 10-13) ending in a bulb at the outer
    end, a block of dark vertical fins hanging below (columns 7-20, rows 13-19) and half of the
    spine block in the middle (columns 21-23). Columns are the piece's own (0-24, the inner edge at
    24), shifted by c0 into an image w px wide; m maps part names to material slots. fin_end is
    where the fin block stops towards the middle."""
    xy = (w, H)
    C = lambda c: c + c0  # noqa: E731
    # Tank (columns 1-20, rows 3-9), rounded at its outer end.
    loft_x(bm, 5.9, [(C(0.8), 1.4, 1.2, 1.0 + dz), (C(1.3), 2.6, 2.2, 1.0 + dz), (C(2.3), 3.2, 2.7, 1.0 + dz),
                     (C(3.6), 3.35, 2.8, 1.0 + dz), (C(20.6), 3.35, 2.8, 1.0 + dz)],
           sides=14, mat=m["tank"], xy=xy)
    for c in (16.0, 18.0):
        loft_x(bm, 5.9, [(C(c), 3.5, 2.95, 1.0 + dz), (C(c + 1.0), 3.5, 2.95, 1.0 + dz)],
               sides=14, mat=m["ring"], xy=xy)
    # Bar under the tank (rows 10-13) with a pale top edge, and the bulb at its outer end.
    loft_x(bm, 11.9, [(C(3.0), 2.1, 1.6, -0.4 + dz), (C(24.0), 2.1, 1.6, -0.4 + dz)],
           sides=10, mat=m["bar"], cap_end=False, xy=xy)
    loft_x(bm, 10.9, [(C(3.5), 0.0, 0.0, 0.7 + dz), (C(4.3), 0.6, 0.45, 0.8 + dz), (C(17.5), 0.6, 0.45, 0.8 + dz),
                      (C(18.3), 0.0, 0.0, 0.7 + dz)], sides=6, mat=m["bar_hi"], xy=xy)
    ellipsoid(bm, C(4.6), 12.6, -0.6 + dz, 3.6, 2.5, 1.9, mat=m["bar"], segments=14, rings=6, xy=xy)
    # Dark fin block (columns 7-20, rows 13-19) with raised fins.
    slab(bm, [(C(7.4), 13.0), (C(fin_end), 13.0), (C(fin_end), 18.9), (C(7.4), 18.9)], -2.7 + dz, -0.6 + dz,
         mat=m["fin_base"], xy=xy)
    for a, b, k in ((8.0, 12.0, "fin_hi"), (13.0, 14.0, "fin"), (15.0, 16.0, "fin"), (17.0, 18.0, "fin"),
                    (19.0, 21.0, "fin_hi")):
        box(bm, C(a), 13.2, C(b), 19.0 if b != 14.0 else 19.6, -2.7 + dz, 0.0 + dz, mat=m[k], bevel=0.25, xy=xy)
    # Half the spine block (columns 21-23, rows 2-12).
    slab(bm, [(C(20.6), 1.6), (C(24.0), 1.6), (C(24.0), 12.6), (C(20.6), 12.6)], -1.4 + dz, 3.8 + dz,
         mat=m["spine"], xy=xy)
