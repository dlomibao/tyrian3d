"""Helpers shared by batch b043's model scripts (newshv.shp: crystals, a rod, a hooded ship and
the two side-gun assemblies). build-models.sh skips lib_ files.

Coordinates here are sprite pixel EDGES: column c runs from c to c + 1, so a pixel's centre is
c + 0.5. Grid converts them to Blender units (1 px = 1/12 unit, sprite up = +Y, centre of the
sprite block = origin)."""

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
    """Pixel edges of a w x h px block to Blender X / Y (the block's centre is the origin)."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def X(self, c):
        return (c - self.w / 2) * PX

    def Y(self, r):
        return (self.h / 2 - r) * PX


# --- geometry ----------------------------------------------------------------------------------

def _faces(bm, rings, mat, smooth, cap_start, cap_end):
    sides = max(len(r) for r in rings)
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
    for f in faces:
        f.smooth = smooth
    caps = []
    if cap_start and len(rings[0]) > 1:
        caps.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        caps.append(bm.faces.new(rings[-1]))
    for f in caps:
        f.smooth = False  # flat end caps: smooth shading would bend their normals
    faces += caps
    for f in faces:
        f.material_index = mat
    return faces


def sweep(bm, g, path, sides=10, mat=0, smooth=True, phase=0.5, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in pixel edges.
    Rings stand across the path: width is measured in the XY plane, height along Z. A ring of
    zero size collapses to a point. `phase` turns the ring (0 puts a vertex at the sides and,
    for an even count, one on top: a ridge)."""
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    return _faces(bm, rings, mat, smooth, cap_start, cap_end)


def loft_y(bm, g, col, sections, **kw):
    """A tube down the sprite centred on column edge `col`: sections are (row, half_w_px, half_h, z)."""
    return sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], **kw)


def loft_x(bm, g, row, sections, **kw):
    """A tube across the sprite centred on row edge `row`: sections are (col, half_w_px, half_h, z)."""
    return sweep(bm, g, [(c, row, z, w, h) for c, w, h, z in sections], **kw)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, smooth=True, half=False):
    """An ellipsoid centred on pixel-edge point (col, row) at height z. `half` keeps only the top."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    if half:
        kill = [v for v in res["verts"] if v.co.z < -1e-4]
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
    new = set(bm.faces) - before
    verts = {v for f in new for v in f.verts}
    for v in verts:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    if half:
        edges = [e for f in new for e in f.edges if e.is_boundary]
        if edges:
            new |= set(bmesh.ops.holes_fill(bm, edges=list(set(edges)), sides=0)["faces"])
    for f in new:
        f.material_index = mat
        f.smooth = smooth
    return list(new)


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A prism from z0 to z1 with an outline of (col, row) pixel edges (any winding)."""
    pts = [(g.X(c), g.Y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    before = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    faces = bm.faces[before:]
    for f in faces:
        f.smooth = smooth
    return faces


def mirror_faces(bm, faces, axis_x=0.0):
    """Add a mirror image of `faces` about the vertical plane X = axis_x."""
    dup = bmesh.ops.duplicate(bm, geom=list(faces))["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def transform_faces(faces, rotate_deg=0.0, centre=(0.0, 0.0), move=(0.0, 0.0, 0.0)):
    """Rotate the vertices of `faces` about the vertical through `centre` (degrees, counter-
    clockwise seen from above), then move them."""
    a = math.radians(rotate_deg)
    ca, sa = math.cos(a), math.sin(a)
    cx, cy = centre
    for v in {v for f in faces for v in f.verts}:
        x, y = v.co.x - cx, v.co.y - cy
        v.co.x = cx + x * ca - y * sa + move[0]
        v.co.y = cy + x * sa + y * ca + move[1]
        v.co.z += move[2]


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth / flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# --- checking ----------------------------------------------------------------------------------

def silhouette_report(obj, pixels, g, outline=(1,), ox=0.0, oy=0.0):
    """Print the sprite grid marked by whether the model covers each pixel centre seen from above:
    '#' both, '+' model only, '-' sprite only, 'o' outline pixel the model covers, '.' empty.
    (ox, oy) is where the grid's centre is in the object's space."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tree = BVHTree.FromBMesh(bm)
    lines, miss, extra = [], 0, 0
    for r, prow in enumerate(pixels):
        line = ""
        for c, v in enumerate(prow):
            x, y = g.X(c + 0.5) + ox, g.Y(r + 0.5) + oy
            hit = tree.ray_cast(Vector((x, y, 10)), Vector((0, 0, -1)))[0] is not None
            if v < 0:
                line += "+" if hit else "."
                extra += hit
            elif v in outline:
                line += "o" if hit else " "
            else:
                line += "#" if hit else "-"
                miss += not hit
        lines.append(line)
    bm.free()
    print(f"silhouette {obj.name}: {miss} sprite px uncovered, {extra} px outside")
    print("\n".join(lines))


def merged_sprite(root, names):
    """The first name's sprite.json with the colours of all of them, so any index is valid."""
    data = common.load_sprite(root, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def preview_arg():
    return sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None


def composite_png(root, layout, out, w, h):
    """Several pieces' first frames as one w x h px image: layout is (name, cx, cy) with each
    piece's centre relative to the image centre."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        x0, y0 = int(cx + w / 2 - 12), int(cy + h / 2 - 14)
        for r, prow in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(prow):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


# --- shared shapes -----------------------------------------------------------------------------

def crystal(bm, g, mats, col=12.5, z=0.0, blunt=False):
    """The faceted crystal of newshv-10 (pointing up the sprite, tip at row 1.6, base at row 25):
    an eight-sided loft with a ridge along its top, a dark groove at row 19 and a rounded base
    cap. `mats` is (body, groove, base) material indices. `blunt` cuts the tip off square (newshv-12
shows it that way). Returns the faces."""
    body, groove, base = mats
    k = 0.034  # half height per px of half width
    faces = []
    top = [(1.6, 0.0), (2.5, 0.6), (4.5, 1.6), (6.5, 2.6), (8.5, 3.6), (10.5, 4.6), (12.5, 5.7),
           (14.2, 6.5), (18.2, 6.5), (19.0, 6.0)]
    if blunt:
        top = [(2.3, 0.0), (2.6, 1.7), (4.5, 2.4), (6.5, 3.2), (8.5, 4.0), (10.5, 4.8)] + top[6:]
    faces += loft_y(bm, g, col, [(r, w, w * k, z) for r, w in top], sides=8, mat=body, smooth=False, phase=0)
    faces += loft_y(bm, g, col, [(18.9, 5.9, 5.9 * k, z), (20.1, 5.9, 5.9 * k, z)], sides=8, mat=groove,
                    smooth=False, phase=0)
    low = [(20.0, 5.9), (20.6, 6.5), (21.9, 6.5), (22.7, 5.6), (23.5, 3.8), (24.4, 1.8), (25.0, 0.0)]
    faces += loft_y(bm, g, col, [(r, w, w * k * 0.9, z) for r, w in low], sides=8, mat=base, smooth=False,
                    phase=0)
    return faces
