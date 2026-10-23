"""Helpers shared by batch b083's models (newsh2 ground machinery): sprite coordinates by pixel
edges, flat-bottomed lofts for things that sit on the ground, chamfered blocks, domes, tubes,
mirroring, and the composite sprite image for an assembly's preview.

Coordinates are pixel *edges*: u runs right from the block's left edge, v down from its top edge,
so pixel (col c, row r) has its centre at (c + 0.5, r + 0.5). build-models.sh skips lib_ files.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


class Grid:
    """A block of w x h sprite pixels centred on the Blender origin."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def x(self, u):
        return (u - self.w / 2) * PX

    def y(self, v):
        return (self.h / 2 - v) * PX


def _mark(bm):
    return len(bm.faces)


def _finish(bm, start, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = mat
        f.smooth = smooth


def box(bm, g, u0, v0, u1, v1, z0, z1, mat=0, chamfer=0.0, smooth=False):
    """A block over pixel edges u0..u1, v0..v1 from z0 to z1, its top edges chamfered by `chamfer` units."""
    start = _mark(bm)
    x0, x1 = sorted((g.x(u0), g.x(u1)))
    y0, y1 = sorted((g.y(v0), g.y(v1)))
    c = min(chamfer, (x1 - x0) / 2.01, (y1 - y0) / 2.01, (z1 - z0) * 0.99)
    rings = [((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    zs = [z0]
    if c > 0:
        rings.append(rings[0])
        zs.append(z1 - c)
        rings.append(((x0 + c, y0 + c), (x1 - c, y0 + c), (x1 - c, y1 - c), (x0 + c, y1 - c)))
        zs.append(z1)
    else:
        rings.append(rings[0])
        zs.append(z1)
    vr = [[bm.verts.new((x, y, z)) for x, y in ring] for ring, z in zip(rings, zs)]
    bm.faces.new(list(reversed(vr[0])))
    for a, b in zip(vr, vr[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(vr[-1])
    _finish(bm, start, mat, smooth)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (u, v) pixel edges (any winding)."""
    start = _mark(bm)
    pts = [(g.x(u), g.y(v)) for u, v in outline]
    # common.slab wants counter-clockwise seen from above
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _finish(bm, start, mat, smooth)


def dloft(bm, g, u_axis, sections, sides=8, mat=0, power=2.5, smooth=True, caps=True):
    """A flat-bottomed loft down the sprite (along -Y) centred on edge column u_axis. Sections are
    (v, half_width_px, z_top[, z_base]); each ring is the top half of a superellipse (power 2 is
    round, higher is boxier) standing on its base, so the part sits on the ground."""
    start = _mark(bm)
    e = 2 / power
    rings = []
    for sec in sections:
        v, hw, zt = sec[:3]
        zb = sec[3] if len(sec) > 3 else 0.0
        ring = []
        for i in range(sides + 1):
            a = math.pi * i / sides
            ca, sa = math.cos(a), math.sin(a)
            x = hw * PX * math.copysign(abs(ca) ** e, ca)
            z = zb + (zt - zb) * (abs(sa) ** e)
            ring.append(bm.verts.new((g.x(u_axis) + x, g.y(v), z)))
        rings.append(ring)
    n = sides + 1
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
        bm.faces.new((r0[n - 1], r0[0], r1[0], r1[n - 1]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    _finish(bm, start, mat, smooth)


def sweep(bm, g, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (u, v, z, half_width_px, half_height_units). Rings stand across the
    path in the XY plane; a ring of zero size closes to a point."""
    start = _mark(bm)
    pts = [Vector((g.x(u), g.y(v), z)) for u, v, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _finish(bm, start, mat, smooth)


def dome(bm, g, u, v, z, rx_px, ry_px, rz, mat=0, segments=16, rings=5, smooth=True):
    """The top half of an ellipsoid centred on edge point (u, v) at height z, with a flat base."""
    start = _mark(bm)
    cx, cy = g.x(u), g.y(v)
    top = bm.verts.new((cx, cy, z + rz))
    prev = [top]
    for j in range(1, rings + 1):
        phi = (math.pi / 2) * j / rings
        s, c = math.sin(phi), math.cos(phi)
        ring = [bm.verts.new((cx + rx_px * PX * s * math.cos(2 * math.pi * k / segments),
                              cy + ry_px * PX * s * math.sin(2 * math.pi * k / segments),
                              z + rz * c)) for k in range(segments)]
        for k in range(segments):
            kk = (k + 1) % segments
            if len(prev) == 1:
                bm.faces.new((prev[0], ring[k], ring[kk]))
            else:
                bm.faces.new((prev[k], ring[k], ring[kk], prev[kk]))
        prev = ring
    bm.faces.new(list(reversed(prev)))
    _finish(bm, start, mat, smooth)


def cylinder(bm, g, u, v, z0, z1, rx_px, ry_px=None, mat=0, sides=12, smooth=True):
    """An upright (elliptic) cylinder centred on edge point (u, v)."""
    start = _mark(bm)
    ry_px = rx_px if ry_px is None else ry_px
    cx, cy = g.x(u), g.y(v)
    rings = [[bm.verts.new((cx + rx_px * PX * math.cos(2 * math.pi * k / sides),
                            cy + ry_px * PX * math.sin(2 * math.pi * k / sides), z)) for k in range(sides)]
             for z in (z0, z1)]
    a, b = rings
    for k in range(sides):
        kk = (k + 1) % sides
        bm.faces.new((a[k], a[kk], b[kk], b[k]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    _finish(bm, start, mat, smooth)
    # caps flat
    bm.faces[-1].smooth = bm.faces[-2].smooth = False


def mirror_from(bm, start, ax):
    """Mirror every face added since face index `start` about the plane x = ax (adds a copy)."""
    bm.faces.ensure_lookup_table()
    faces = list(bm.faces[start:])
    verts = {v for f in faces for v in f.verts}
    edges = {e for f in faces for e in f.edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + faces)["geom"]
    for el in dup:
        if isinstance(el, bmesh.types.BMVert):
            el.co.x = 2 * ax - el.co.x
    bmesh.ops.reverse_faces(bm, faces=[el for el in dup if isinstance(el, bmesh.types.BMFace)])


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
    """The first piece's sprite.json with the colours of every piece, so any piece's index works."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w_px, h_px):
    """Pieces' first frames as one image of w_px x h_px, centred like the assembly's model (layout
    (name, cx, cy) relative to the image centre), for render_preview."""
    import numpy as np
    img = np.zeros((h_px, w_px, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w_px / 2 - 12), int(cy + h_px / 2 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, val in enumerate(row):
                if val >= 0 and 0 <= y0 + r < h_px and 0 <= x0 + c < w_px:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(val)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w_px, h_px, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def assembly_main(root, name, build, pieces, cx0, cy0, preview_tiles):
    """Build an assembly whole, split it into `pieces` (laid out by sprite.json assemblyLayout, with
    (cx0, cy0) as the screen pixel at the Blender origin), export each and render previews."""
    import tempfile
    sprite = merged_sprite(root, pieces)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in sprite["assemblyLayout"]
              if e["model"] in pieces]
    parts = common.split_assembly(obj, layout)
    for piece in pieces:
        data = common.load_sprite(root, piece)
        common.export_sprite_model(root, [parts[piece]], f"enemies/{piece}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        w_px, h_px = 24 * preview_tiles, 28 * preview_tiles
        ref = composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", w_px, h_px)
        common.render_preview([obj], str(out), str(ref), size=2 * preview_tiles, view_px=480)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([parts[piece]], str(out.parent / f"{piece}.png"), img, size=2)
