"""Helpers shared by batch b056's models (newshh.shp, level 2.2). Not a model script itself
(tools/build-models.sh skips lib_ files).

Everything works in sprite pixel coordinates on a grid `g` (Grid): columns run right, rows run
down, and a grid of w x h px has its centre at the Blender origin. 1 px = 1/12 unit.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


class Grid:
    """A w x h px block (a 2x2 sprite is 24 x 28; an assembly is wider) centred on the origin."""

    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def X(self, c):
        """Pixel column (centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) * PX

    def Y(self, r):
        """Pixel row (centre) to Blender Y: sprite up is +Y."""
        return (self.h / 2 - (r + 0.5)) * PX

    def EX(self, e):
        """Pixel edge (column boundary) to Blender X."""
        return (e - self.w / 2) * PX

    def EY(self, e):
        """Pixel edge (row boundary) to Blender Y."""
        return (self.h / 2 - e) * PX


def _faces_since(bm, n):
    bm.faces.ensure_lookup_table()
    return bm.faces[n:]


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) pixel centres. Rings
    stand across the path; the width is measured across the path in XY and the height along Z. A
    ring of zero size is a point (a rounded or pointed end)."""
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
    rings = []
    up = Vector((0, 0, 1))
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


def loft_y(bm, g, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px, half_height, z)."""
    sweep(bm, g, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def loft_x(bm, g, row, sections, sides=10, mat=0, smooth=True):
    """A loft across the sprite along row `row`: sections are (col, half_height_px, half_z, z),
    the half height measured along the sprite's rows."""
    sweep(bm, g, [(c, row, z, w, h) for c, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def pillow(bm, g, outline, z0, z1, insets=(), mat=0, top_mat=None, smooth=False):
    """A plate from z0 to z1 whose outline is (col, row) pixel edges, its top rounded off by
    insets: each (thickness_px, rise) insets the top face inward and lifts it by `rise`."""
    n = len(bm.faces)
    pts = [(g.EX(c), g.EY(r)) for c, r in outline]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    new = _faces_since(bm, n)
    top = max(new, key=lambda f: f.calc_center_median().z)
    for thick, rise in insets:
        res = bmesh.ops.inset_region(bm, faces=[top], thickness=thick * PX, depth=rise, use_even_offset=True)
        for f in res["faces"]:
            f.material_index = mat
    if top_mat is not None:
        top.material_index = top_mat
    for f in _faces_since(bm, n):
        f.smooth = smooth


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, squash_bottom=1.0):
    """An ellipsoid centred on a pixel; `squash_bottom` < 1 flattens its underside."""
    before = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        vz = v.co.z * (squash_bottom if v.co.z < 0 else 1.0)
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + vz * rz))
    for f in _faces_since(bm, before):
        f.material_index = mat
        f.smooth = True


def mirror_all(bm, axis_x):
    """Add a mirror image, about Blender X = axis_x, of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
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
    """The whole assembly's sprite (first frames) as one image of size x size*14/12 tiles
    (12 x 14 px each), centred like the model: layout entries are (name, cx, cy) relative to the
    Blender origin, in screen pixels."""
    import numpy as np
    W, H = size * 12, size * 14
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + W / 2 - 12), int(cy + H / 2 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < H and 0 <= x0 + c < W:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export_assembly(root, obj, pieces, cx0, cy0, layout_source, preview_size):
    """Cut `obj` (built with the assembly centre at screen (cx0, cy0) as the origin) into its
    pieces, export each with its own sprites, and render previews when asked for."""
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in layout_source if e["model"] in pieces]
    parts = common.split_assembly(obj, layout)
    for name in pieces:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [parts[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", preview_size)
        common.render_preview([obj], str(out), ref, size=preview_size, view_px=480)
        for name in pieces:
            data = common.load_sprite(root, name)
            img = Path(root) / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([parts[name]], str(out.parent / f"{name}.png"), img, size=2)
    return parts


# --- the green beetles (assemblies newshh-192/194 and newshh-230/232) ----------------------------

BEETLE_AXIS = 25  # both beetles are mirror symmetric about assembly pixel column 25

# The left grey shell of the narrow beetle (newshh-192), pixel edges (col, row); the wide one
# (newshh-230) has the same shell moved `spread` px further out on each side.
BEETLE_SHELL = [(16, 5), (20, 5), (19, 6), (18, 7), (17, 8), (16, 9), (16.5, 10), (18, 11), (22, 12),
                (23, 13), (24, 14), (24, 18), (23, 19), (20, 19.6), (18, 20.5), (16, 21.5), (14, 22.5),
                (13, 21.5), (13, 20), (8.5, 20), (7, 19), (7, 13), (8, 12), (8, 11), (9, 10), (10, 9),
                (11, 8), (12, 7), (14, 6)]


def head_height(w):
    """The beetle head's half height (units) where it is w px half wide."""
    return min(0.19, 0.03 + w * 0.016)


def build_beetle(sprite, name, spread, head):
    """A green beetle 48 x 28 px (two 2x2 pieces side by side): a green body with a pointed head
    up the screen and a broad tail with two lobes, under two grey shell plates that sweep from the
    shoulders out and down the sides. `spread` moves the shells and the body's sides outward (0 for
    the narrow beetle, 4 for the wide one); `head` is the head's (row, half width px) up to row 9."""
    g = Grid(48, 28)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(39, metallic=0.15, roughness=0.5),  # 0 green body
        pal(36, metallic=0.1, roughness=0.6),  # 1 dark green tail lobes
        pal(43, metallic=0.15, roughness=0.4),  # 2 light green ridges
        pal(105, metallic=0.55, roughness=0.4),  # 3 grey shell sides
        pal(107, metallic=0.6, roughness=0.35),  # 4 grey shell top
        pal(108, metallic=0.65, roughness=0.3),  # 5 light shell rim
        pal(109, metallic=0.7, roughness=0.2),  # 6 bright studs
    ]
    BODY, LOBE, RIDGE, SHELL, TOP, RIM, STUD = range(7)
    s = spread
    bm = bmesh.new()

    # Green body down the axis: (row, half width px, half height).
    # It sits low under the shells (rows 11-19) and rises again at the head and the tail.
    body = [(r, w, h) for r, w, h in [(head[0][0] - 0.4, 0.0, 0.0)] + [(r, w, head_height(w)) for r, w in head]]
    body += [(11.5, 10.5 + s, 0.14), (13.0, 10.8 + s, 0.12), (18.0, 11.0 + s, 0.12), (20.5, 11.5 + s, 0.17),
             (23.0, 12.5 + s, 0.18), (24.2, 12.5 + s, 0.17), (25.2, 11.0 + s, 0.12), (25.8, 7.0, 0.08), (26.1, 0.0, 0.0)]
    loft_y(bm, g, BEETLE_AXIS, [(r, w, h, 0.0) for r, w, h in body], sides=14, mat=BODY)

    # Two lobes either side of the notch at the back.
    ellipsoid(bm, g, 19.0 - s, 25.2, -0.01, 3.6, 1.8, 0.1, mat=LOBE, segments=12, rings=6)

    # Grey shell over the left side, its top rounded off, a light rim along its upper edge and
    # bright studs where the sprite's highlights are.
    shell = [(c - s, r) for c, r in BEETLE_SHELL]
    pillow(bm, g, shell, -0.04, 0.17, insets=((1.0, 0.05), (1.2, 0.03)), mat=SHELL, top_mat=TOP)
    sweep(bm, g, [(18.6 - s, 5.4, 0.21, 0.0, 0.0), (17.5 - s, 5.6, 0.21, 0.7, 0.04), (15.0 - s, 6.6, 0.215, 0.8, 0.045),
                  (12.8 - s, 8.0, 0.22, 0.8, 0.045), (10.8 - s, 9.6, 0.22, 0.8, 0.045), (9.3 - s, 11.2, 0.22, 0.8, 0.045),
                  (8.4 - s, 12.8, 0.21, 0.7, 0.04), (8.0 - s, 14.5, 0.2, 0.0, 0.0)], sides=6, mat=RIM)
    for c, r in ((12.5, 12.0), (14.0, 10.0), (20.0, 14.0), (22.0, 15.0), (17.0, 15.0), (9.5, 15.5), (11.5, 17.0)):
        ellipsoid(bm, g, c - s, r, 0.25, 0.7, 0.7, 0.025, mat=STUD, segments=8, rings=4)

    mirror_all(bm, g.X(BEETLE_AXIS))

    if s == 0:
        # The narrow beetle's shells meet in a band across its middle (rows 14-17).
        pillow(bm, g, [(23, 14), (28, 14), (28, 18), (23, 18)], -0.04, 0.17, insets=((0.6, 0.05),),
               mat=SHELL, top_mat=TOP)

    # Light ridges across the head and down the tail.
    bars = ((4.0, 1.8), (6.0, 2.0), (8.0, 2.0)) + (((10.0, 2.0), (12.0, 1.8), (14.0, 1.6)) if s else ())
    for r, w in bars:
        z = head_height(dict(head)[r]) * 0.97 if r in dict(head) else 0.13
        loft_x(bm, g, r, [(BEETLE_AXIS - w - 0.4, 0.0, 0.0, z), (BEETLE_AXIS - w, 0.5, 0.03, z),
                          (BEETLE_AXIS + w, 0.5, 0.03, z), (BEETLE_AXIS + w + 0.4, 0.0, 0.0, z)], sides=6, mat=RIDGE)
    for dc in (-3.5 - s / 2, 0.0, 3.5 + s / 2):
        loft_y(bm, g, BEETLE_AXIS + dc, [(19.0, 0.0, 0.0, 0.19), (19.6, 0.55, 0.03, 0.195), (22.4, 0.55, 0.03, 0.185),
                                          (23.0, 0.0, 0.0, 0.18)], sides=6, mat=RIDGE)

    return to_object(name, bm, mats, coll)
