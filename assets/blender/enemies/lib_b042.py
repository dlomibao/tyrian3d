"""Helpers shared by batch b042's model scripts (newsh5 gun pods, falling fireball, small probe).

Coordinates: a `Grid` maps sprite (or assembly) pixel columns and rows to Blender X / Y for a
block of w x h pixels centred on the origin: X(c) and Y(r) give a pixel's centre (fractions
allowed), sprite up is +Y and one pixel is 1/12 unit.
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
    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def _join(bm, rings, mat, smooth, cap_start=True, cap_end=True):
    """Faces between consecutive rings of BMVerts (a ring of one vert is a tip)."""
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 2:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 2:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, power=1.0):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in grid `g`. Rings
    stand perpendicular to the path in the XY plane; the width is measured across the path and the
    height along Z. A ring of zero size collapses to a point (a rounded or pointed end). `power` < 1
    squares the cross-section off (a superellipse)."""
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
            a = 2 * math.pi * (k + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            ca = math.copysign(abs(ca) ** power, ca)
            sa = math.copysign(abs(sa) ** power, sa)
            ring.append(bm.verts.new(pts[i] + side * (w * PX * ca) + up * (h * sa)))
        rings.append(ring)
    return _join(bm, rings, mat, smooth, cap_start, cap_end)


def loft_x(bm, g, row, sections, sides=12, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A body of revolution (flattened in Z) along +X, centred on pixel row `row`: sections are
    (col, half_width_px, half_height_units, z)."""
    rings = []
    y0 = g.Y(row)
    for c, w, h, z in sections:
        x = g.X(c)
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x, y0, z))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new((x, y0 - w * PX * math.cos(a), z + h * math.sin(a))))
        rings.append(ring)
    return _join(bm, rings, mat, smooth, cap_start, cap_end)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid centred on a pixel; with z_min the vertices below it are flattened onto it
    (a dome with a flat base)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        p = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
        if z_min is not None:
            p.z = max(p.z, z_min)
        v.co = p
    new = set(bm.faces) - before
    for f in new:
        f.material_index = mat
        f.smooth = True
    return new


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (the top-left corner
    of pixel (c, r) is (c, r)), counter-clockwise seen from above."""
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def mirror_copy(bm, axis="y", about=0.0, faces=None):
    """Add a mirror image of `faces` (default: everything built so far) about the line X = about
    (axis "x") or Y = about (axis "y")."""
    if faces is None:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    else:
        faces = list(faces)
        verts = {v for f in faces for v in f.verts}
        edges = {e for f in faces for e in f.edges}
        geom = list(verts) + list(edges) + faces
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        if axis == "x":
            v.co.x = 2 * about - v.co.x
        else:
            v.co.y = 2 * about - v.co.y
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


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, size):
    """The pieces' first frames as one image (screen layout (name, cx, cy) relative to the
    assembly's centre), on a canvas of size*12 x size*14 px that render_preview expects."""
    import numpy as np
    W, H = size * 12, size * 14
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + W / 2 - 12), int(cy + H / 2 - 14)
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0 and 0 <= y0 + r < H and 0 <= x0 + c < W:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export_assembly(root, obj, layout, size):
    """Cut `obj` (built in assembly coordinates) into its pieces, export each with its own sprites
    and, with -- --preview <png>, preview the whole object and each piece (<piece>.png beside it)."""
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in layout:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", size)
        common.render_preview([obj], str(out), ref, size=size, view_px=480)
        for name, _, _ in layout:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    return pieces


# --- the newsh5 gun pod (assemblies newsh5-43 + 45, and its mirror image newsh5-39 + 41) ------

def build_gunpod(sprite, name, flip=False):
    """The gun pod of level 4.12: a blue capsule on a grey ring frame that holds a dark blue orb,
    and a barrel with a bullet-shaped blue head pointing along +X (flip=True points it along -X).

    Built in the 48 x 28 px assembly of newsh5-43 (columns 0-23) and newsh5-45 (24-47), whose
    axis is pixel row 13; the origin is the assembly's centre."""
    g = Grid(48, 28)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.7, roughness=0.35),  # 0 grey frame
        pal(10, metallic=0.75, roughness=0.25),  # 1 light grey bands and inner edge
        pal(4, metallic=0.6, roughness=0.45),  # 2 dark grey gun and caps
        pal(57, metallic=0.4, roughness=0.3),  # 3 blue head and capsule
        pal(56, metallic=0.5, roughness=0.15),  # 4 glossy blue orb
        pal(59, metallic=0.5, roughness=0.2),  # 5 light blue barrel sleeve
        pal(55, metallic=0.45, roughness=0.3),  # 6 blue spikes and vanes
        pal(13, metallic=0.8, roughness=0.2),  # 7 bright grey highlights
        pal(106, metallic=0.6, roughness=0.35),  # 8 blue-grey frame edges
    ]
    FRAME, LIGHT, DARK, BLUE, ORB, SLEEVE, SPIKE, BRIGHT, EDGE = range(9)
    bm = bmesh.new()
    AXIS = 13  # pixel row of the pod's axis
    yaxis = g.Y(AXIS)

    # ---- upper half (mirrored about the axis below) ----
    upper = set()

    def keep(faces):
        upper.update(faces)

    # Ring frame: the left bar (columns 11-13) up and round into the thick top arm (rows 2-7)
    # and down its right side into the barrel's flange (column 23-24).
    keep(sweep(bm, g, [(12.2, AXIS, 0.0, 1.6, 0.1), (12.2, 9.5, 0.0, 1.6, 0.1), (12.6, 7.2, 0.0, 1.7, 0.1),
                       (14.0, 5.6, 0.0, 1.6, 0.1), (16.0, 5.2, 0.0, 1.8, 0.1), (18.5, 4.5, 0.0, 2.6, 0.12),
                       (20.5, 4.4, 0.0, 2.7, 0.12), (22.2, 5.6, 0.0, 2.2, 0.11), (22.9, 7.6, 0.0, 1.6, 0.1),
                       (23.4, 9.6, 0.0, 1.3, 0.09)], sides=8, mat=FRAME, cap_start=False))
    # Light inner edge along the bar and the arm.
    keep(sweep(bm, g, [(12.8, AXIS, 0.06, 0.7, 0.05), (12.8, 9.0, 0.06, 0.7, 0.05), (13.6, 7.0, 0.06, 0.7, 0.05),
                       (16.0, 6.4, 0.07, 0.7, 0.05), (20.0, 6.2, 0.07, 0.7, 0.05), (21.4, 6.6, 0.06, 0.6, 0.05)],
                   sides=6, mat=LIGHT, cap_start=False))
    # The spike off the top arm pointing forward (columns 21-27, row 4).
    keep(sweep(bm, g, [(20.5, 4.0, 0.03, 1.2, 0.07), (24.0, 4.0, 0.03, 1.1, 0.06), (26.2, 4.1, 0.03, 0.9, 0.05),
                       (27.3, 4.2, 0.03, 0.0, 0.0)], sides=8, mat=SPIKE))
    # Capsule's grey cap (rows 7-9) with the blue knob above it (columns 8-10, rows 5-7).
    keep(sweep(bm, g, [(8.0, 7.0, 0.0, 0.0, 0.0), (8.0, 7.4, 0.0, 2.6, 0.1), (8.0, 8.4, 0.0, 3.4, 0.13),
                       (8.0, 10.4, 0.0, 3.4, 0.13)], sides=10, mat=DARK))
    keep(ellipsoid(bm, g, 9.0, 5.8, 0.03, 1.8, 1.4, 0.07, mat=SPIKE, segments=10, rings=6))
    keep(sweep(bm, g, [(10.5, 8.0, 0.02, 0.8, 0.05), (12.0, 8.0, 0.02, 0.8, 0.05)], sides=6, mat=DARK))
    # Blue vanes at the base of the head (columns 27-33, rows 8-9).
    keep(sweep(bm, g, [(27.6, 9.4, 0.02, 0.0, 0.0), (28.2, 9.2, 0.02, 0.9, 0.06), (31.0, 8.6, 0.02, 1.1, 0.07),
                       (32.8, 8.5, 0.02, 1.0, 0.06)], sides=8, mat=SPIKE))

    mirror_copy(bm, "y", yaxis, faces=upper)

    # ---- along the axis ----
    # Blue capsule on the left of the frame (columns 5-10, rows 10-16), its light side facing out.
    sweep(bm, g, [(7.6, 9.4, 0.0, 3.3, 0.14), (7.6, 10.2, 0.0, 3.5, 0.16), (7.6, 15.8, 0.0, 3.5, 0.16),
                  (7.6, 16.6, 0.0, 3.3, 0.14)], sides=12, mat=BLUE)
    sweep(bm, g, [(9.3, 10.6, 0.11, 0.6, 0.04), (9.3, 15.4, 0.11, 0.6, 0.04)], sides=6, mat=BRIGHT)
    # Dark glossy orb inside the ring (columns 17-23, rows 10-16).
    ellipsoid(bm, g, 20.0, AXIS, 0.0, 3.8, 3.8, 0.22, mat=ORB, segments=16, rings=8)
    # Flange (column 24), light sleeve (25-31), grey band (32-35), the blue head (36-44) and the
    # gun barrel out of its nose (rows 12-14).
    loft_x(bm, g, AXIS, [(22.8, 0.0, 0.0, 0.0), (23.0, 3.6, 0.12, 0.0), (24.6, 4.2, 0.14, 0.0),
                         (25.0, 2.6, 0.1, 0.0)], sides=12, mat=EDGE)
    loft_x(bm, g, AXIS, [(24.8, 2.4, 0.09, 0.0), (31.6, 2.4, 0.09, 0.0)], sides=10, mat=SLEEVE)
    loft_x(bm, g, AXIS, [(31.4, 2.7, 0.1, 0.0), (33.0, 2.9, 0.11, 0.0), (33.3, 5.4, 0.17, 0.0),
                         (35.2, 5.7, 0.18, 0.0), (35.6, 4.0, 0.13, 0.0)], sides=16, mat=LIGHT)
    loft_x(bm, g, AXIS, [(35.3, 5.2, 0.14, 0.0), (35.8, 6.4, 0.19, 0.0), (38.5, 6.5, 0.2, 0.0),
                         (40.5, 6.0, 0.19, 0.0), (42.2, 4.9, 0.16, 0.0), (43.6, 3.5, 0.12, 0.0),
                         (44.6, 2.4, 0.08, 0.0)], sides=16, mat=BLUE)
    loft_x(bm, g, AXIS, [(37.5, 1.3, 0.07, 0.16), (44.5, 1.3, 0.07, 0.16), (45.3, 1.1, 0.06, 0.12),
                         (45.5, 0.0, 0.0, 0.12)], sides=8, mat=LIGHT)

    if flip:
        bmesh.ops.scale(bm, vec=(-1, 1, 1), verts=bm.verts)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return to_object(name, bm, mats, coll)
