"""Helpers shared by batch b019's model scripts (build-models.sh skips lib_ modules).

Coordinates are pixel *edges* of a grid w x h px (a sprite block or a whole assembly): column c
runs from c to c + 1 and row r from r to r + 1, so pixel (c, r) has its centre at (c + 0.5, r + 0.5).
Grid.x / Grid.y turn them into Blender units (sprite up is +Y, 1 px = 1/12 unit, the grid's
centre is the origin). Heights (z) are in units.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def x(self, c):
        """Pixel-edge column to Blender X."""
        return (c - self.w / 2) * U

    def y(self, r):
        """Pixel-edge row (down the sprite) to Blender Y."""
        return (self.h / 2 - r) * U

    def xy(self, c, r):
        return self.x(c), self.y(r)


def _se(a, power):
    """Superellipse point on the unit ring: power < 1 squares the section off."""
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)


def _join_rings(bm, rings, sides, mat, cap_start=True, cap_end=True):
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces


def tube(bm, g, points, sides=10, mat=0, power=1.0, cap_start=True, cap_end=True, smooth=True):
    """A tube along a path in the sprite plane: points are (col, row, half_w_px, half_h, z), cols and
    rows in pixel edges, half_h and z in units. Rings stand square to the path (half_w across it,
    half_h up). A zero-size point is a tip. power < 1 squares the section off (0.5 is a rounded box).
    A straight run down the sprite is a loft (fuselages, keels)."""
    pos = [Vector((g.x(c), g.y(r))) for c, r, *_ in points]
    rings = []
    for i, (c, r, hw, hh, z) in enumerate(points):
        p = pos[i]
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((p.x, p.y, z))])
            continue
        d = pos[min(i + 1, len(pos) - 1)] - pos[max(i - 1, 0)]
        d.normalize()
        n = Vector((-d.y, d.x))
        ring = []
        for k in range(sides):
            u, v = _se(2 * math.pi * (k + 0.5) / sides, power)
            q = p + n * (hw * U * u)
            ring.append(bm.verts.new((q.x, q.y, z + hh * v)))
        rings.append(ring)
    faces = _join_rings(bm, rings, sides, mat, cap_start, cap_end)
    for f in faces:
        f.smooth = smooth
    return faces


def slab(bm, g, outline, z0, z1, mat=0, bevel=0.0, smooth=False):
    """Extrude an outline of (col, row) pixel-edge points between heights z0 and z1 (units). bevel
    (px) pulls the top face in toward the outline's centroid for a chamfered edge."""
    pts = [Vector((g.x(c), g.y(r))) for c, r in outline]
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    cen = sum(pts, Vector((0, 0))) / len(pts)
    bottom = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    top = []
    for p in pts:
        q = p
        if bevel:
            d = cen - p
            k = min(bevel * U / (d.length or 1), 0.9)
            q = p + d * k
        top.append(bm.verts.new((q.x, q.y, z1)))
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bottom)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    """A box over pixel edges c0..c1, r0..r1, from z0 to z1."""
    return slab(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def ellipsoid(bm, g, c, r, rx_px, ry_px, rz, z=0.0, mat=0, segments=16, rings=8, smooth=True):
    """An ellipsoid centred on pixel edge point (c, r) at height z: radii rx, ry in px, rz in units."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((g.x(c) + v.co.x * rx_px * U, g.y(r) + v.co.y * ry_px * U, z + v.co.z * rz))
    new = list(set(bm.faces) - before)
    for f in new:
        f.material_index = mat
        f.smooth = smooth
    return new


def mirror_all(bm, axis_x=0.0):
    """Add a mirror image (about the vertical plane X = axis_x) of everything built so far."""
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


def composite_png(root, layout, w, h, out, pad_h=None):
    """The whole assembly's sprite (first frames) as one image, w x h px, centred vertically in a
    canvas pad_h px tall (render_preview wants the 12:14 shape of a size-N sprite). Layout entries
    are (name, cx, cy) relative to the assembly's centre."""
    import numpy as np
    ph = pad_h or h
    img = np.zeros((ph, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w / 2 - 12), int(cy + ph / 2 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < ph and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, ph, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run_assembly(root, name, pieces, centre, build, size, grid_w, grid_h, finish=None):
    """Build an assembly whole, cut it into its pieces, export each and, with -- --preview <png>,
    render the whole thing (and <piece>.png per piece next to it). `centre` is the assembly
    centre in screen pixels (cx, cy) as the layout gives them. `finish(parts, sprite)`, if given,
    can adjust the cut pieces ({name: object}) before they're exported; with -- --frames it also
    renders every animated piece's frames to <piece>-frames.png next to the preview."""
    sprite = merged_sprite(root, pieces)
    obj = build(sprite)
    cx0, cy0 = centre
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in sprite["assemblyLayout"]
              if e["model"] in pieces]
    parts = common.split_assembly(obj, layout)
    if finish:
        finish(parts, sprite)
    for piece in pieces:
        data = common.load_sprite(root, piece)
        common.export_sprite_model(root, [parts[piece]], f"enemies/{piece}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, layout, grid_w, grid_h, Path(tempfile.mkdtemp()) / "assembly.png",
                            pad_h=round(size * 14))
        common.render_preview([obj], str(out), ref, size=size, view_px=640)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([parts[piece]], str(out.parent / f"{piece}.png"), img, size=2)
            if "--frames" in sys.argv and len(data["frames"]) > 1:
                common.render_frame_previews([parts[piece]], str(out.parent / f"{piece}-frames.png"), data, root)
