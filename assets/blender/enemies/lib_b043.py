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


def gun_materials(sprite, tag):
    """Materials for gun(), in its index order."""
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(107, metallic=0.7, roughness=0.3),  # 0 body cylinder and barrel
        pal(103, metallic=0.6, roughness=0.4),  # 1 lower block
        pal(110, metallic=0.8, roughness=0.2),  # 2 bright ribs
        pal(108, metallic=0.8, roughness=0.25),  # 3 rail
        pal(105, metallic=0.6, roughness=0.4),  # 4 keel
        pal(101, metallic=0.4, roughness=0.6),  # 5 dark joint behind the pod
        pal(117, metallic=0.1, roughness=0.4, emission_strength=2.0),  # 6 red engine pod
        pal(122, emission_strength=5.0),  # 7 its hot core
        pal(116, emission_strength=3.0),  # 8 red lights under the barrel
        pal(104, metallic=0.6, roughness=0.45),  # 9 jaw
        pal(118, emission_strength=3.0),  # 10 red light at the keel's end
    ]


def gun(bm, g):
    """The side gun of newshv-44 + newshv-46 in its 48 x 28 px assembly (pixel edges, newshv-44
    on columns 0-24): a red glowing engine pod on the left, a fat body cylinder (rows 5-18) with
    cooling ribs over its upper flank and a keel under it, and a barrel running right that hooks
    down at its end over a jaw with a row of red lights. Material indices follow gun_materials()."""
    TUBE, BLOCK, RIB, RAIL, KEEL, JOINT, POD, CORE, LIGHT, JAW, LIGHT2 = range(11)
    AXIS, R, ZC, HZ = 12.0, 7.0, 0.0, 0.2  # body cylinder: axis row edge, radius px, z centre, half height

    # Body cylinder (columns 8-24, rows 5-18), lit on its upper flank, shaded below.
    loft_x(bm, g, AXIS, [(8.2, 6.0, 0.17, ZC), (9.0, 6.8, 0.195, ZC), (10.0, R, HZ, ZC), (22.5, R, HZ, ZC),
                         (24.5, 6.4, 0.185, ZC), (25.5, 5.0, 0.16, ZC)], sides=14, mat=TUBE)
    # Cooling ribs over its upper flank (columns 9, 11, 13, 15; rows 5-11).
    import math as _m
    for c in (9.5, 11.5, 13.5, 15.5):
        path = []
        for t in range(8, 84, 12):
            a = _m.radians(t)
            path.append((c, AXIS - (R + 0.15) * _m.sin(a), ZC + (HZ + 0.012) * _m.cos(a), 0.42, 0.025))
        sweep(bm, g, path, sides=6, mat=RIB)
    # Strip under the pod (rows 16-18 from column 3) and the keel under the body (rows 19-23).
    plate(bm, g, [(3, 15.5), (9, 15.5), (9, 19), (3, 19)], -0.14, 0.02, mat=BLOCK)
    plate(bm, g, [(7, 17.5), (24.3, 17.5), (24.3, 21), (23, 22), (22, 23), (21, 24), (15, 24), (13, 23),
                  (11, 22), (9, 21), (7, 20)], -0.14, -0.02, mat=KEEL)
    loft_x(bm, g, 21.0, [(12.5, 0.0, 0.0, -0.02), (13.5, 1.1, 0.05, -0.02), (21.5, 1.1, 0.05, -0.02),
                         (22.5, 0.0, 0.0, -0.02)], sides=8, mat=RAIL)  # light ridge down the keel
    ellipsoid(bm, g, 24.4, 19.9, -0.05, 0.8, 1.0, 0.06, mat=LIGHT2, segments=10, rings=5)
    # Rail along the lower flank (row 14, columns 17-23).
    zr = ZC + HZ * _m.sqrt(1 - (2.5 / R) ** 2) + 0.01
    loft_x(bm, g, 14.5, [(16.6, 0.0, 0.0, zr), (17.2, 0.6, 0.035, zr), (23.6, 0.6, 0.035, zr),
                         (24.2, 0.0, 0.0, zr)], sides=6, mat=RAIL)

    # Barrel (rows 7-15) out of the body, hooking down at its end (columns 37-45).
    sweep(bm, g, [(22.0, 10.8, 0.0, 4.4, 0.17), (28, 11.1, 0.0, 4.1, 0.165), (33, 11.7, 0.0, 3.9, 0.16),
                  (37, 12.2, 0.0, 3.8, 0.155), (40.0, 13.3, 0.0, 3.6, 0.15), (42.0, 15.0, 0.0, 3.4, 0.14),
                  (42.7, 17.0, -0.01, 3.2, 0.13), (42.8, 19.2, -0.02, 3.1, 0.12), (42.8, 20.1, -0.02, 0.0, 0.0)],
          sides=12, mat=TUBE)
    # Dark joint ring between the pod and the body (column 8).
    loft_x(bm, g, 12.0, [(7.4, 5.0, 0.15, 0.0), (8.6, 5.0, 0.15, 0.0)], sides=12, mat=JOINT)

    # Red engine pod (columns 2-7, rows 8-15) with its hot core up and left of centre.
    ellipsoid(bm, g, 5.0, 12.0, 0.0, 3.2, 4.1, 0.19, mat=POD, segments=16, rings=8)
    ellipsoid(bm, g, 4.9, 10.3, 0.05, 1.5, 1.5, 0.16, mat=CORE, segments=10, rings=6)

    # Jaw under the barrel (rows 15-18, columns 28-39) with red lights along its top (row 15).
    plate(bm, g, [(28.3, 14.0), (40.0, 14.0), (40.0, 18), (31.5, 18), (30, 18.5), (29, 17)], -0.13, -0.01,
          mat=JAW)
    for c0, c1 in ((32, 33), (34, 36), (37, 38)):
        ellipsoid(bm, g, (c0 + c1) / 2, 15.6, -0.02, (c1 - c0) / 2 + 0.1, 0.7, 0.06, mat=LIGHT,
                  segments=10, rings=5)


def sprite_pixels(root, layout, w, h):
    """The first frames of several pieces as one w x h grid of palette indices (-1 empty);
    layout is (name, cx, cy) with each piece's centre relative to the grid's centre."""
    grid = [[-1] * w for _ in range(h)]
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        x0, y0 = int(cx + w / 2 - 12), int(cy + h / 2 - 14)
        for r, prow in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(prow):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid
