"""Helpers shared by batch b076's model scripts (newsh3 ground structures of episode 4).

Coordinates: sprite column c / row r. ex/ey give a pixel *edge* (the left or top edge of column c /
row r; fractions allowed), px/row a pixel centre, for a w x h px block (24x28 by default; 12x14 for
size-1 sprites, 48x56 for a 2x2-piece assembly) whose centre is the Blender origin.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in Blender units


class Frame:
    """Pixel-edge to Blender coordinate mapping for a w x h px block centred on the origin."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def ex(self, c):
        return (c - self.w / 2) * U

    def ey(self, r):
        return (self.h / 2 - r) * U

    def px(self, c):
        return self.ex(c + 0.5)

    def row(self, r):
        return self.ey(r + 0.5)

    def p(self, c, r, z=0.0):
        """A 3D point at pixel edge coordinates (c, r) and height z."""
        return (self.ex(c), self.ey(r), z)


def quad(bm, pts, mat, smooth=False):
    """A face through 3D points (any count >= 3), given counter-clockwise seen from outside."""
    verts = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(verts)
    f.material_index = mat
    f.smooth = smooth
    return f


def ring_faces(bm, outer, inner, mats, smooth=False):
    """Four trapezoids joining an outer and an inner rectangle of 3D corner points (each given as
    [NW, NE, SE, SW]); mats = (north, east, south, west) material indices. Sides with no width are
    skipped. Faces wind so their normals point up (or outward for sloped risers)."""
    sides = [(0, 1), (1, 2), (2, 3), (3, 0)]
    for (a, b), m in zip(sides, mats):
        pts = [outer[a], outer[b], inner[b], inner[a]]
        if (Vector(pts[0]) - Vector(pts[3])).length < 1e-6 and (Vector(pts[1]) - Vector(pts[2])).length < 1e-6:
            continue
        # outer[a] -> outer[b] runs clockwise seen from above, so reverse for an upward normal.
        quad(bm, list(reversed(pts)), m, smooth)


def rect(F, c0, c1, r0, r1, z):
    """Corners [NW, NE, SE, SW] of a pixel-edge rectangle at height z."""
    return [F.p(c0, r0, z), F.p(c1, r0, z), F.p(c1, r1, z), F.p(c0, r1, z)]


def box(bm, F, c0, c1, r0, r1, z0, z1, mat, top_mat=None):
    """An axis-aligned block between pixel edges, from z0 to z1."""
    xs, ys = (F.ex(c0), F.ex(c1)), (F.ey(r1), F.ey(r0))
    outline = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[1], ys[1]), (xs[0], ys[1])]
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    if top_mat is not None:
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n:]:
            if f.normal.z > 0.5 or f.calc_center_median().z > z1 - 1e-6:
                f.material_index = top_mat


def ellipsoid(bm, centre, radii, mat, segments=16, rings=8, z_min=None, smooth=True):
    """A UV sphere scaled to radii (rx, ry, rz) at centre; with z_min, vertices below it are
    flattened onto it (a dome sitting on a surface)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    for v in res["verts"]:
        x, y, z = cx + v.co.x * radii[0], cy + v.co.y * radii[1], cz + v.co.z * radii[2]
        if z_min is not None:
            z = max(z, z_min)
        v.co = Vector((x, y, z))
    new = set(bm.faces) - before
    for f in new:
        f.material_index = mat
        f.smooth = smooth
    return new


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def composite_png(root, layout, w, h, x_off, y_off, out):
    """Several pieces' first frames as one w x h image: layout is (model, cx, cy) with each piece's
    centre in pixels relative to the image origin offset (x_off, y_off)."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = cx + x_off - 12, cy + y_off - 14
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run(root, name, build, file):
    """The usual main: build(sprite) returns a list of (model_name, objects, sprites) to export;
    with -- --preview <png>, the first model is previewed against the first frame and any others
    get <png stem>-<model>.png next to it against their own first frame; with -- --frames <dir>,
    each model's frames are rendered one row each into <dir>/<model>.png."""
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        frames = {f["image"]: f for f in sprite["frames"]}
        for i, (model, objects, sprites) in enumerate(models):
            sheet, size, fr = sprites[0]["sheet"], sprites[0]["size"], sprites[0]["frames"][0]
            stem = Path(sheet).stem
            image = f"frame-{stem}-{fr}.png"
            frame = frames.get(image, sprite["frames"][0])
            ref = Path(root) / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.parent / f"{out.stem}-{model}.png"
            common.render_preview(objects, str(path), ref, size=frame["size"], frame=frame["index"])
    if "--frames" in sys.argv:  # every frame of each model, one row each, into <dir>/<model>.png
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for model, objects, sprites in models:
            own = {f for s in sprites for f in s["frames"]}
            sub = {**sprite, "frames": [f for f in sprite["frames"] if f["index"] in own]}
            common.render_frame_previews(objects, out / f"{model}.png", sub, root)
    return sprite


def frame_subset(sprite, frames):
    """sprite['sprites'] narrowed to the given frame numbers (for a model covering only some)."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def prism(bm, F, outline, z0, z1, mat, bevel=0.0, top_mat=None):
    """A flat-topped block over a polygon of pixel-edge points (col, row), from z0 to z1. With
    bevel (units), the top is inset by that much at z1 and the sides slope out to the outline at
    z1 - bevel (a chamfered top edge); the chamfer takes `mat`, the top `top_mat` (default mat)."""
    pts = [Vector((F.ex(c), F.ey(r))) for c, r in outline]
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    n = len(pts)
    top_mat = mat if top_mat is None else top_mat
    if bevel <= 0:
        common.slab(bm, [(p.x, p.y) for p in pts], z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
        if top_mat != mat:
            bm.faces.ensure_lookup_table()
            bm.faces[-n - 2].material_index = top_mat
        return
    # Inset polygon: move each vertex along its corner bisector.
    inset = []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        d0, d1 = (b - a).normalized(), (c - b).normalized()
        n0, n1 = Vector((-d0.y, d0.x)), Vector((-d1.y, d1.x))  # inward normals (CCW polygon)
        m = (n0 + n1)
        m = m.normalized() / max(0.3, m.normalized().dot(n0)) if m.length > 1e-9 else n0
        inset.append(b + m * bevel)
    zb = z1 - bevel
    bot = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    mid = [bm.verts.new((p.x, p.y, zb)) for p in pts]
    top = [bm.verts.new((p.x, p.y, z1)) for p in inset]
    f = bm.faces.new(top)
    f.material_index = top_mat
    f = bm.faces.new(list(reversed(bot)))
    f.material_index = mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], mid[j], mid[i])).material_index = mat
        bm.faces.new((mid[i], mid[j], top[j], top[i])).material_index = mat


def annulus(bm, F, outer, inner, profile, n, mat, smooth=True):
    """A ring around ellipses in pixel-edge coordinates: outer/inner are (col, row, rx_px, ry_px).
    `profile` is a closed list of (t, z) from the inner (t=0) to the outer (t=1) edge, going over
    the top and back underneath, e.g. [(0, 0), (0, .2), (.5, .3), (1, .2), (1, 0)]."""
    rings = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        pi = Vector((F.ex(inner[0] + inner[2] * ca), F.ey(inner[1] - inner[3] * sa)))
        po = Vector((F.ex(outer[0] + outer[2] * ca), F.ey(outer[1] - outer[3] * sa)))
        rings.append([bm.verts.new((*(pi + (po - pi) * t), z)) for t, z in profile])
    m = len(profile)
    for k in range(n):
        r0, r1 = rings[k], rings[(k + 1) % n]
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat
            f.smooth = smooth


def loft_y(bm, F, col, sections, sides=8, mat=0, smooth=True, cap=True):
    """common.loft down the sprite centred on pixel-edge column `col`: sections are
    (row_edge, half_width_px, half_height_units, z)."""
    start = len(bm.verts)
    nf = len(bm.faces)
    common.loft(bm, [(F.ey(r), w * U, h, z) for r, w, h, z in sections], sides=sides, mat_index=mat,
                cap_start=cap, cap_end=cap)
    common.shift_x(bm, start, F.ex(col))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[nf:]:
        f.smooth = smooth


def loft_x(bm, F, row_edge, sections, sides=8, mat=0, smooth=True, cap=True):
    """A loft across the sprite (along X) at pixel-edge row `row_edge`: sections are
    (col_edge, half_depth_px (along Y), half_height_units, z)."""
    start = len(bm.verts)
    nf = len(bm.faces)
    # Build along Y with "y" = X, then swap axes (and flip winding with a mirror).
    common.loft(bm, [(F.ex(c), w * U, h, z) for c, w, h, z in sections], sides=sides, mat_index=mat,
                cap_start=cap, cap_end=cap)
    bm.verts.ensure_lookup_table()
    y0 = F.ey(row_edge)
    for v in bm.verts[start:]:
        v.co.x, v.co.y = v.co.y, y0 + v.co.x
    bm.faces.ensure_lookup_table()
    new = bm.faces[nf:]
    bmesh.ops.reverse_faces(bm, faces=new)
    for f in new:
        f.smooth = smooth


def tube(bm, points, radius, sides=6, mat=0, smooth=True, caps=True):
    """A round tube along a polyline of 3D points (radius a number or one per point), its rings
    facing the bisector at each joint (copied in spirit from lib_b007.polyline_tube)."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for c, t, rad in zip(pts, tangents, radii):
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        rings.append([bm.verts.new(c + rad * (math.cos(2 * math.pi * (k + 0.5) / sides) * u +
                                              math.sin(2 * math.pi * (k + 0.5) / sides) * v))
                      for k in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if caps:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        faces.append(bm.faces.new(rings[-1]))
    # Make the winding face outward: compare the first side face's normal with its offset from the axis.
    f = faces[0]
    f.normal_update()
    if f.normal.dot(f.calc_center_median() - pts[0]) < 0:
        bmesh.ops.reverse_faces(bm, faces=faces)
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces
