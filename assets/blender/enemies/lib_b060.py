"""Helpers shared by batch b060's models (newsh8.shp: the rock worm and its burrow, the dome
walker, the antlered spider, the carrot): sprite coordinates, ellipsoids, rocks and tubes placed
anywhere, pixel-outline plates, mirroring, per-face colours sampled from the sprite, previews.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


def px(c, w=24):
    """Sprite column (pixel centre, fractions allowed) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def P(c, r, z=0.0):
    """A point at sprite pixel (c, r) (pixel centres) and height z."""
    return Vector((px(c), row(r), z))


def _faces_since(bm, n):
    bm.faces.ensure_lookup_table()
    return bm.faces[n:]


def ellipsoid(bm, centre, radii, segments=12, rings=6, mat=0, smooth=True, angle=0.0, seed=None, rough=0.0):
    """An ellipsoid at `centre` (Blender units) with semi-axes `radii`, turned `angle` radians about
    Z. With `seed`, its vertices are pushed in and out by up to `rough` (a fraction) for a rock."""
    n = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    rnd = random.Random(seed) if seed is not None else None
    rot = Matrix.Rotation(angle, 3, "Z")
    cache = {}
    for v in res["verts"]:
        co = Vector(v.co)
        if rnd:
            key = (round(co.x, 4), round(co.y, 4), round(co.z, 4))
            k = cache.setdefault(key, 1 + rnd.uniform(-rough, rough))
            co *= k
        co = Vector((co.x * radii[0], co.y * radii[1], co.z * radii[2]))
        v.co = rot @ co + Vector(centre)
    for f in _faces_since(bm, n):
        f.material_index = mat
        f.smooth = smooth
    return list(_faces_since(bm, n))


def tube(bm, points, radii, sides=8, mat=0, flat=1.0, cap=True, smooth=True):
    """A tube along a polyline of 3D points with a radius per point (0 closes to a tip). `flat`
    squashes the cross-section in Z. Returns its faces."""
    n = len(bm.faces)
    pts = [Vector(p) for p in points]
    rings = []
    for i, (p, rad) in enumerate(zip(pts, radii)):
        if rad == 0:
            rings.append([bm.verts.new(p)])
            continue
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nup = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * math.cos(a) * rad + nup * math.sin(a) * rad * flat))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f)
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0])
        if len(rings[-1]) > 1:
            bm.faces.new(list(reversed(rings[-1])))
    faces = list(_faces_since(bm, n))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def ptube(bm, path, sides=8, mat=0, flat=1.0, cap=True, smooth=True):
    """tube() with a path of (col, row, z, radius_px) in sprite pixels."""
    return tube(bm, [P(c, r, z) for c, r, z, _ in path], [rad * PX for _, _, _, rad in path],
                sides=sides, mat=mat, flat=flat, cap=cap, smooth=smooth)


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True, cap=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px,
    half_height_units, z_centre). Returns its faces."""
    n = len(bm.faces)
    common.loft(bm, [(row(r), w * PX, h, z) for r, w, h, z in sections], sides=sides, mat_index=mat,
                cap_start=cap, cap_end=cap)
    bm.verts.ensure_lookup_table()
    faces = list(_faces_since(bm, n))
    verts = {v for f in faces for v in f.verts}
    for v in verts:
        v.co.x += px(col)
    for f in faces:
        f.smooth = smooth
    return faces


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1; `outline` is (col, row) pixel corners (col 0 row 0 is the
    sprite's top-left corner), in either winding."""
    pts = [((c - 12) / 12, (14 - r) / 12) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    faces = list(_faces_since(bm, n))
    for f in faces:
        f.smooth = smooth
    return faces


def mirror(bm, axis_x, faces):
    """Add a mirror image (about X = axis_x) of `faces`. Returns the new faces."""
    verts = {v for f in faces for v in f.verts}
    edges = {e for f in faces for e in f.edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + list(faces))["geom"]
    new_faces = [e for e in dup if isinstance(e, bmesh.types.BMFace)]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    return new_faces


def sample(pixels, x, y, w=24, h=28, ox=0.0, oy=0.0):
    """Palette index of the sprite pixel under Blender (x, y) (-1 outside or transparent). (ox, oy)
    is where the sprite's centre sits in Blender, for sprites placed inside a bigger model."""
    c = int(math.floor((x - ox) * 12 + w / 2))
    r = int(math.floor(h / 2 - (y - oy) * 12))
    if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
        return pixels[r][c]
    return -1


def paint(bm, faces, pixels, slot_of, spread=0.6, **kw):
    """Give each face (pointing up at all) the slot slot_of(mean index, current slot) of the
    sprite pixels under it (None leaves it), for shading a part from its sprite ramp."""
    bmesh.ops.recalc_face_normals(bm, faces=list(faces))
    for f in faces:
        f.normal_update()
        if f.normal.z < 0.05:
            continue
        cen = f.calc_center_median()
        pts = [cen] + [cen.lerp(v.co, spread) for v in f.verts]
        vals = [sample(pixels, p.x, p.y, **kw) for p in pts]
        vals = [v for v in vals if v > 1]
        if not vals:
            continue
        slot = slot_of(sum(vals) / len(vals), f.material_index)
        if slot is not None:
            f.material_index = slot


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
    """The first name's sprite.json with the colours of all of them, so any index is valid."""
    data = common.load_sprite(root, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def frames_subset(sprite, frames):
    """sprite["sprites"] keeping only the given frame numbers."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def frame_pixels(sprite, index):
    return next(f["pixels"] for f in sprite["frames"] if f["index"] == index)


def preview_args():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def preview(objs, root, name, image, out, size=2):
    """Render a preview of `objs` beside reference/models/<name>/<image> to `out`."""
    ref = Path(root) / "reference" / "models" / name / image
    common.render_preview(objs, str(out), ref, size=size)


def composite_png(root, parts, w, h, out):
    """Paint sprites into one w x h image: parts are (sprite_name, frame_index, x0, y0) with the
    sprite's top-left pixel at (x0, y0). For previews of assemblies."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, index, x0, y0 in parts:
        data = common.load_sprite(root, name)
        pixels = frame_pixels(data, index)
        for r, line in enumerate(pixels):
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
