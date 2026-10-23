"""Helpers shared by batch b115's model scripts (ground structures from newsh3.shp).

Coordinates are pixel EDGES: edge column c is the left edge of sprite column c, so a pixel
(c, r) covers edges c..c+1 and r..r+1. ex/ey turn edges into Blender X/Y for a w x h px block
centred on the origin (sprite up is +Y).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def faces_since(bm, first):
    bm.faces.ensure_lookup_table()
    return bm.faces[first:]


def set_faces(bm, first, mat=None, smooth=None):
    for f in faces_since(bm, first):
        if mat is not None:
            f.material_index = mat
        if smooth is not None:
            f.smooth = smooth


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, smooth=False):
    """An axis-aligned box in Blender units."""
    n = len(bm.faces)
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    set_faces(bm, n, smooth=smooth)


def prism(bm, pts, z0, z1, mat=0, smooth=False):
    """Extrude an XY outline (Blender units, any winding) from z0 to z1."""
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if area < 0:
        pts = list(reversed(pts))
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    set_faces(bm, n, smooth=smooth)


def frustum(bm, bottom, top, mat=0, smooth=False, cap_bottom=True):
    """Join two closed rings of 3D points with the same count (a tapered solid); caps both."""
    vb = [bm.verts.new(p) for p in bottom]
    vt = [bm.verts.new(p) for p in top]
    n = len(vb)
    first = len(bm.faces)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    bm.faces.new(vt)
    if cap_bottom:
        bm.faces.new(list(reversed(vb)))
    set_faces(bm, first, mat=mat, smooth=smooth)
    return vb, vt


def xloft(bm, sections, mat=0, smooth=False):
    """Loft profiles along X: sections are (x, [(y, z), ...]) with the same point count each,
    every profile a closed polygon in the YZ plane. Ends are capped."""
    rings = [[bm.verts.new((x, y, z)) for y, z in prof] for x, prof in sections]
    first = len(bm.faces)
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    set_faces(bm, first, mat=mat, smooth=smooth)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, smooth=True, half=False, rot=0.0):
    """An ellipsoid (or, with half, its upper half: a dome sitting on z with a flat base) in
    Blender units, turned by `rot` radians about Z."""
    first = len(bm.faces)
    c, s = math.cos(rot), math.sin(rot)
    lo = 0 if half else -rings // 2
    hi = rings // 2 if half else rings - rings // 2
    steps = hi - lo
    lat = [math.pi / 2 * (lo + i) / (rings // 2 if half else rings / 2) for i in range(steps)]
    ring_verts = []
    for a in lat:
        ring = []
        for k in range(segments):
            t = 2 * math.pi * k / segments
            lx, ly = math.cos(a) * math.cos(t) * rx, math.cos(a) * math.sin(t) * ry
            ring.append(bm.verts.new((x + lx * c - ly * s, y + lx * s + ly * c, z + math.sin(a) * rz)))
        ring_verts.append(ring)
    top = bm.verts.new((x, y, z + rz))
    for r0, r1 in zip(ring_verts, ring_verts[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    for k in range(segments):
        bm.faces.new((ring_verts[-1][k], ring_verts[-1][(k + 1) % segments], top))
    if half:
        bm.faces.new(list(reversed(ring_verts[0])))
    else:
        bottom = bm.verts.new((x, y, z - rz))
        for k in range(segments):
            bm.faces.new((ring_verts[0][(k + 1) % segments], ring_verts[0][k], bottom))
    for f in faces_since(bm, first):
        f.material_index = mat
        f.smooth = smooth and not (half and len(f.verts) == segments)


def cylinder(bm, x, y, z0, z1, rx, ry=None, mat=0, sides=12, smooth=True):
    ry = rx if ry is None else ry
    pts = [(x + rx * math.cos(2 * math.pi * (i + 0.5) / sides), y + ry * math.sin(2 * math.pi * (i + 0.5) / sides))
           for i in range(sides)]
    first = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    for f in faces_since(bm, first):
        f.smooth = smooth and abs(f.normal.z) < 0.5


def transform_since(bm, first_vert, matrix):
    bm.verts.ensure_lookup_table()
    for v in bm.verts[first_vert:]:
        v.co = matrix @ v.co


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth flag."""
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
    """The first piece's sprite.json with every piece's colours merged in."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, w_px, h_px):
    """The pieces' first frames composed into one w_px x h_px image centred on the origin of the
    layout (cx, cy relative to the assembly centre), padded to 24:28 for render_preview."""
    import numpy as np
    size = max(w_px / 24, h_px / 28)
    W, H = int(round(24 * size)), int(round(28 * size))
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
    return out, W / 12


def export_assembly(root, obj, layout, preview_args, assembly_w, assembly_h):
    """Split `obj` (built in assembly coordinates) into the layout's pieces, export each with its
    sprites and, with --preview, render the whole object and each piece."""
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in layout:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in preview_args:
        import tempfile
        out = Path(preview_args[preview_args.index("--preview") + 1])
        ref, size = composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", assembly_w, assembly_h)
        common.render_preview([obj], str(out), str(ref), size=size, view_px=480)
        for name, _, _ in layout:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    return pieces


# --- the tan bunkers of level 4.2 (newsh3-122/124 and newsh3-84/86) -----------------------------

def bunker(bm, spec, M):
    """A long low bunker, 48 x 22 px, seen from above: a flat roof between two ribs, bevelled
    end caps, a sloped front face (the darker band at the bottom of the sprite) and chamfered back
    corners. `spec` gives everything in assembly pixel edges (cols 0..48, rows 0..28). M maps
    part names to material slots."""
    X = lambda c: ex(c, 48)  # noqa: E731
    Y = lambda r: ey(r, 28)  # noqa: E731
    H = spec["height"]
    front_top = spec["front_top"]  # row edge where the roof meets the front slope

    def prof(back, fb, h):
        """YZ profile: back wall, roof, front slope down to the front-bottom edge."""
        ft = min(front_top, fb - 1.0)
        return [(Y(back), 0.0), (Y(fb), 0.0), (Y(fb - 0.5), h * 0.15), (Y(ft), h), (Y(back + 0.5), h),
                (Y(back), h * 0.8)]

    sections = spec["sections"]

    def hf(c):
        for (c0, _, _, h0), (c1, _, _, h1) in zip(sections, sections[1:]):
            if c0 <= c <= c1:
                return h0 + (h1 - h0) * (c - c0) / (c1 - c0)
        return sections[-1][3]

    first = len(bm.faces)
    xloft(bm, [(X(c), prof(b, fb, H * k)) for c, b, fb, k in sections], mat=M["roof"])
    # Colour the hull by facing: roof, end caps, front slope and back wall.
    hull = list(faces_since(bm, first))
    bmesh.ops.recalc_face_normals(bm, faces=hull)
    for f in hull:
        f.normal_update()
        n = f.normal
        if abs(n.x) > 0.1 and abs(n.x) >= abs(n.y):
            f.material_index = M["cap"] if n.x < 0 else M.get("cap_r", M["cap"])
        elif n.y < -0.2:
            f.material_index = M["front"]
        elif n.y > 0.2:
            f.material_index = M["back"]

    # Raised ribs and ledges on the roof: (col0, col1, row0, row1, height above roof, part).
    for c0, c1, r0, r1, dz, part in spec.get("bars", []):
        top = H * hf((c0 + c1) / 2) + dz
        box(bm, X(c0), Y(r1), X(c1), Y(r0), top - 0.04, top, mat=M[part])
    # Recessed panels: a dark plate with a raised inner plate.
    for c0, r0, c1, r1, inner in spec.get("panels", []):
        box(bm, X(c0), Y(r1), X(c1), Y(r0), H - 0.03, H + 0.006, mat=M["groove"])
        ic0, ir0, ic1, ir1 = inner
        box(bm, X(ic0), Y(ir1), X(ic1), Y(ir0), H - 0.03, H + 0.022, mat=M["panel"])
    # Glowing vents in the bevelled end cap: (col0, col1, row0, row1, part), standing just proud
    # of the sloping cap.
    for c0, c1, r0, r1, part in spec.get("vents", []):
        top = H * hf((c0 + c1) / 2) + 0.012
        box(bm, X(c0), Y(r1), X(c1), Y(r0), top - 0.06, top, mat=M[part])


def bar(bm, p0, p1, width, z0, z1, mat=0):
    """A straight flat-topped bar from XY point p0 to p1 (Blender units), `width` across."""
    d = Vector((p1[0] - p0[0], p1[1] - p0[1]))
    d.normalize()
    n = Vector((-d.y, d.x)) * (width / 2)
    pts = [(p0[0] - n.x, p0[1] - n.y), (p1[0] - n.x, p1[1] - n.y), (p1[0] + n.x, p1[1] + n.y),
           (p0[0] + n.x, p0[1] + n.y)]
    prism(bm, pts, z0, z1, mat=mat)


def frame_subset(sprite, frames):
    """The sprite's `sprites` entry narrowed to the given frame indices (one sheet)."""
    ref = sprite["sprites"][0]
    return [{"sheet": ref["sheet"], "size": ref["size"], "frames": list(frames)}]


def preview_frames(root, name, sprite, objs_by_frame, argv):
    """With --preview <png>: render each model beside its first frame. The first model goes to
    <png>, the others to <png stem>-f2.png, -f3.png, ..."""
    if "--preview" not in argv:
        return
    out = Path(argv[argv.index("--preview") + 1])
    for i, (frame_index, objs) in enumerate(objs_by_frame):
        frame = next(f for f in sprite["frames"] if f["index"] == frame_index)
        ref = root / "reference" / "models" / name / frame["image"]
        path = out if i == 0 else out.with_name(f"{out.stem}-f{i + 1}.png")
        common.render_preview(objs, str(path), ref, size=frame["size"])
