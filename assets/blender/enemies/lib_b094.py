"""Helpers shared by batch b094's scripts (the spinning claw and the blade rotor assemblies).

Both assemblies are four 2x2 pieces round a hub at their centre and are four-fold rotationally
symmetric, so their scripts model one arm in hub-relative pixel coordinates (x right, y up, in
sprite pixels), copy it round the hub and turn the whole thing to each animation frame's angle.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


# --- geometry, in sprite pixels (x right, y up) with z in units ---------------------------------

def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (x_px, y_px, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; a ring of zero size collapses to a point."""
    pts = [Vector((x * PX, y * PX, z)) for x, y, z, _, _ in path]
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
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def ellipsoid(bm, x, y, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid centred at pixel (x, y) and height z; z_min flattens everything below it."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((x * PX + v.co.x * rx_px * PX, y * PX + v.co.y * ry_px * PX, z + v.co.z * rz))
        if z_min is not None and v.co.z < z_min:
            v.co.z = z_min
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat-topped block from z0 to z1 with an outline of (x_px, y_px), counter-clockwise."""
    n = len(bm.faces)
    common.slab(bm, [(x * PX, y * PX) for x, y in outline], z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def ngon(r, sides, start=0.0):
    """A regular polygon outline of radius r (pixels), counter-clockwise."""
    return [(r * math.cos(start + 2 * math.pi * i / sides), r * math.sin(start + 2 * math.pi * i / sides))
            for i in range(sides)]


def frustum(bm, x, y, r0, r1, z0, z1, sides=12, mat=0, smooth=True, cap_top=True):
    """A cone frustum (radii in pixels) standing from z0 to z1."""
    bot = [bm.verts.new(((x + r0 * math.cos(2 * math.pi * i / sides)) * PX,
                         (y + r0 * math.sin(2 * math.pi * i / sides)) * PX, z0)) for i in range(sides)]
    top = [bm.verts.new(((x + r1 * math.cos(2 * math.pi * i / sides)) * PX,
                         (y + r1 * math.sin(2 * math.pi * i / sides)) * PX, z1)) for i in range(sides)]
    faces = [bm.faces.new(list(reversed(bot)))]
    if cap_top:
        faces.append(bm.faces.new(top))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    faces[0].smooth = False
    if cap_top:
        faces[1].smooth = False


def copy_rotated(bm, verts_from, faces_from, angles_deg):
    """Duplicate the geometry added since (verts_from, faces_from) at each angle (degrees,
    counter-clockwise about the origin)."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    faces = bm.faces[faces_from:]
    verts = bm.verts[verts_from:]
    edges = list({e for f in faces for e in f.edges})
    for a in angles_deg:
        dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + list(faces))["geom"]
        dv = [e for e in dup if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.rotate(bm, verts=dv, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(a), 3, "Z"))
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()


def transform(bm, verts_from, angle_deg=0.0, scale=1.0, scale_z=None, dx_px=0.0, dy_px=0.0):
    """Scale (about the origin), turn counter-clockwise and then move the verts added since
    verts_from."""
    bm.verts.ensure_lookup_table()
    m = Matrix.Rotation(math.radians(angle_deg), 3, "Z")
    sz = scale if scale_z is None else scale_z
    for v in bm.verts[verts_from:]:
        co = Vector((v.co.x * scale, v.co.y * scale, v.co.z * sz))
        co = m @ co
        v.co = co + Vector((dx_px * PX, dy_px * PX, 0))


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


# --- assemblies --------------------------------------------------------------------------------

def merged_sprite(root, names):
    """The first piece's sprite.json with every piece's colours, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def frame_subset(sprites, indices):
    """`sprites` (load_sprite(...)["sprites"]) keeping only the frames at these positions."""
    out = []
    for s in sprites:
        s = dict(s)
        s["frames"] = [s["frames"][i] for i in indices]
        out.append(s)
    return out


def composite_png(root, grid, frame_index, out, w=48, h=56, pad_to=None):
    """The whole assembly's sprite at one frame as an image. grid: [(name, left_px, top_px)].
    pad_to=(W, H) centres it in a bigger transparent image (render_preview wants 24:28)."""
    import numpy as np
    W, H = pad_to or (w, h)
    ox, oy = (W - w) // 2, (H - h) // 2
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, x0, y0 in grid:
        data = common.load_sprite(root, name)
        frame = data["frames"][frame_index]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[oy + y0 + r, ox + x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def silhouette_report(obj, root, grid, frame_index, w=48, h=56, label=""):
    """Compare the model's top view with the sprite's filled (non-outline) pixels at one frame:
    prints how many pixels match and an ASCII map (X both, s sprite only, m model only).
    Model coordinates: pixel (c, r) of the w x h block is at X = (c + 0.5 - w/2)/12,
    Y = (h/2 - r - 0.5)/12."""
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, deps)
    mask = [[0] * w for _ in range(h)]
    for name, x0, y0 in grid:
        frame = common.load_sprite(root, name)["frames"][frame_index]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v > 1:
                    mask[y0 + r][x0 + c] = 1
    both = s_only = m_only = 0
    lines = []
    for r in range(h):
        line = ""
        for c in range(w):
            x, y = (c + 0.5 - w / 2) / 12, (h / 2 - r - 0.5) / 12
            hit = tree.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)))[0] is not None
            s = mask[r][c]
            if hit and s:
                both += 1
                line += "X"
            elif s:
                s_only += 1
                line += "s"
            elif hit:
                m_only += 1
                line += "m"
            else:
                line += "."
        lines.append(line)
    print(f"silhouette {label}: both {both}, sprite only {s_only}, model only {m_only}, "
          f"IoU {both / max(1, both + s_only + m_only):.2f}")
    print("\n".join(lines))
