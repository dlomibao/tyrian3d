"""Helpers for batch b028: the grey robot arms of level 4.20 (newsh9.shp).

Two arms hang into the screen from the top, one on each side: assembly-newsh9-39 (pieces
newsh9-1, newsh9-3 and newsh9-39, the left arm) and assembly-newsh9-45 (newsh9-5, newsh9-7 and
newsh9-45, the right arm, the left one mirrored and shifted one pixel). Each is three 2x2 enemies
in an L: a rounded shoulder housing at the top right with two knuckles on it, a jaw block under
it, a big grey upper arm running down to the left with a socket ring round a dark opening, and a
forearm ending in a looped claw that holds a glowing blue gem.

`build_arm` builds the left arm in its assembly's pixel grid (48 x 56 px, pixel-edge coordinates:
pixel column c spans c..c+1, rows count down the screen) and mirrors it for the right one.
Helpers copied and adapted from assembly-newsht-39.py and lib_b003.py.
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
W, H = 48, 56  # assembly grid in pixels


def X(c):
    """Assembly pixel-edge column to Blender X (the grid's centre is the origin)."""
    return (c - W / 2) / 12


def Y(r):
    """Assembly pixel-edge row to Blender Y: sprite up is +Y."""
    return (H / 2 - r) / 12


# --- geometry helpers --------------------------------------------------------------------------

def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=10, mat=0, smooth=True, closed=False, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; a ring of zero size collapses to a point.
    `closed` joins the last ring back to the first (a loop)."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    n = len(pts)
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        if closed:
            t = pts[(i + 1) % n] - pts[(i - 1) % n]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
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
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    faces = []
    for r0, r1 in pairs:
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
    if not closed:
        if cap_start and len(rings[0]) > 1:
            faces.append(bm.faces.new(list(reversed(rings[0]))))
        if cap_end and len(rings[-1]) > 1:
            faces.append(bm.faces.new(rings[-1]))
    _faces(bm, faces, mat, smooth)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=14, rings=7, smooth=True):
    """An ellipsoid centred on pixel-edge point (col, row) at height z."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _faces(bm, set(bm.faces) - before, mat, smooth)


def _inset(outline, d):
    """Move each vertex of a closed XY outline inward by `d` (from lib_b003.inset_outline)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length * sign, ex_ / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def plate(bm, outline, z0, z1, mat=0, bevel=0.0, top_mat=None, tilt=None):
    """A prism from z0 up to z1 over an outline of (col, row) pixel edges, its top edges chamfered
    in by `bevel` px. `tilt` (dz_per_col, dz_per_row, col0, row0) slopes the top: each top vertex
    is raised by dz_per_col * (c - col0) + dz_per_row * (r - row0)."""
    pts = [(X(c), Y(r)) for c, r in outline]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if area < 0:
        outline = list(reversed(outline))
        pts = list(reversed(pts))
    top = _inset(pts, bevel * PX) if bevel else pts

    def dz(x, y):
        if not tilt:
            return 0.0
        c, r = x * 12 + W / 2, H / 2 - y * 12
        return tilt[0] * (c - tilt[2]) + tilt[1] * (r - tilt[3])

    bh = min(bevel * PX * 0.8, (z1 - z0) * 0.5) if bevel else 0.0
    n = len(pts)
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    mid = [bm.verts.new((x, y, z1 - bh + dz(x, y))) for x, y in pts]
    hi = [bm.verts.new((x, y, z1 + dz(x, y))) for x, y in top]
    faces = [bm.faces.new(list(reversed(lo)))]
    tf = bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((lo[i], lo[j], mid[j], mid[i])))
        if bevel:
            faces.append(bm.faces.new((mid[i], mid[j], hi[j], hi[i])))
    _faces(bm, faces, mat, False)
    _faces(bm, [tf], mat if top_mat is None else top_mat, False)


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


def merged_sprite(root, pieces):
    """The first piece's sprite.json with every piece's colours, so any piece's index is valid."""
    data = common.load_sprite(root, pieces[0])
    for name in pieces[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


# --- the arm -----------------------------------------------------------------------------------

def build_arm(name, sprite, coll, mirror=False):
    """The whole arm as one object in its assembly grid (left arm; `mirror` builds the right one:
    its pixel column c is the left arm's column 46 - c)."""
    tag = name
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.3, roughness=0.4),  # 0 lit grey faces
        pal(5, metallic=0.3, roughness=0.45),  # 1 shaded grey faces
        pal(2, metallic=0.2, roughness=0.6),  # 2 dark undersides
        pal(3, metallic=0.2, roughness=0.7),  # 3 dark hollows
        pal(7, metallic=0.35, roughness=0.35),  # 4 mid grey housings
        pal(10, metallic=0.4, roughness=0.3),  # 5 bright rims
        pal(12, metallic=0.4, roughness=0.25),  # 6 highlights
        pal(4, metallic=0.3, roughness=0.5),  # 7 dark grey
        pal(6, metallic=0.3, roughness=0.4),  # 8 grey neck
        pal(153, emission_strength=4.0),  # 9 blue gem
        pal(158, emission_strength=5.0),  # 10 gem highlight
        pal(8, metallic=0.35, roughness=0.3),  # 11 light-mid grey
    ]
    LIT, SHADE, UNDER, HOLLOW, MID, RIM, HI, DARK, NECK, GEM, GEMHI, LMID = range(12)
    bm = bmesh.new()

    # Shoulder housing at the top right (rows 2-11, columns 24-47): a rounded drum lying across
    # the screen, with two knuckles on top.
    sweep(bm, [(23.6, 8.0, 0.0, 0.0, 0.0), (24.6, 7.6, 0.02, 2.4, 0.1), (27.0, 7.0, 0.04, 3.3, 0.15),
               (30.0, 6.6, 0.05, 3.9, 0.18), (34.0, 6.6, 0.06, 4.4, 0.2), (39.0, 6.8, 0.06, 4.3, 0.2),
               (43.0, 7.0, 0.06, 3.9, 0.19), (45.6, 7.3, 0.05, 3.0, 0.15), (46.8, 7.6, 0.04, 1.5, 0.08),
               (47.1, 7.8, 0.04, 0.0, 0.0)], sides=12, mat=MID)
    ellipsoid(bm, 37.6, 6.2, 0.2, 2.1, 2.6, 0.09, mat=RIM)
    ellipsoid(bm, 42.2, 6.8, 0.19, 1.8, 2.4, 0.085, mat=RIM)
    ellipsoid(bm, 37.9, 6.0, 0.265, 0.9, 1.2, 0.035, mat=HI, segments=10, rings=5)
    ellipsoid(bm, 42.4, 6.6, 0.25, 0.7, 1.0, 0.03, mat=HI, segments=10, rings=5)

    # Neck between the housing and the upper arm (rows 8-13).
    plate(bm, [(17, 12.5), (21, 9), (26, 8), (34, 8.5), (37, 11), (36, 13.5), (26, 13.5)],
          -0.16, 0.1, mat=NECK)
    # Mouth: the dark gap between the housing and the jaw (rows 11-13, columns 36-45).
    plate(bm, [(35, 11), (45.5, 10.5), (45.5, 14), (35, 14)], -0.14, 0.02, mat=HOLLOW)

    # Jaw block under the housing (rows 13-21, columns 35-45) and its dark underside (rows 21-27).
    plate(bm, [(35.5, 14), (45, 13.8), (45, 21), (43, 22), (37.5, 21.5), (35, 18.5)],
          -0.14, 0.13, mat=LIT, bevel=0.8)
    plate(bm, [(35.5, 21), (45, 20.5), (44.6, 23), (41.5, 26.5), (39.5, 27.6), (36, 27.6)],
          -0.2, 0.0, mat=DARK, tilt=(0.0, -0.025, 0, 21))

    # Upper arm: the lit face (columns 17-26, rows 11-30) on a shaded lower-left block (columns
    # 9-18, rows 17-24) whose underside (rows 24-30) falls away in shadow.
    plate(bm, [(17, 12.5), (20.5, 10.5), (26.5, 11), (27, 14), (26.5, 26), (22.5, 30.2), (17, 30.2), (17, 18)],
          -0.2, 0.16, mat=LIT, bevel=1.0)
    plate(bm, [(16.5, 13), (17.8, 13), (17.8, 25), (9, 24.5), (11, 21), (13, 19), (15.5, 16.5)],
          -0.2, 0.09, mat=SHADE, bevel=0.6, tilt=(0.004, 0.0, 17, 0))
    plate(bm, [(9, 24.3), (17.8, 24.5), (17.8, 30.5), (8.8, 30.5)],
          -0.2, 0.05, mat=UNDER, tilt=(0.0, -0.022, 0, 24.3))
    # Highlight ridge on the edge between the lit and the shaded face.
    sweep(bm, [(20.8, 19.6, 0.15, 0.0, 0.0), (20.4, 20.4, 0.15, 0.9, 0.035), (19.2, 22.6, 0.14, 0.8, 0.03),
               (18.3, 25.5, 0.13, 0.7, 0.03), (17.9, 27.2, 0.12, 0.0, 0.0)], sides=6, mat=RIM)
    ellipsoid(bm, 20.6, 20.5, 0.18, 0.9, 0.8, 0.03, mat=HI, segments=8, rings=4)

    # Socket: a bright ring round a dark opening (columns 26-38, rows 12-27).
    plate(bm, [(26, 14), (30, 13.5), (34, 14.5), (37, 19), (35.5, 22.5), (33, 26), (29, 24), (26.5, 22)],
          -0.18, -0.02, mat=HOLLOW)
    plate(bm, [(28.5, 18), (31.5, 17), (34, 20), (33, 23), (30, 22)], -0.18, 0.0, mat=UNDER)
    sweep(bm, [(25.6, 15.0, 0.1, 1.5, 0.08), (27.4, 13.4, 0.11, 1.7, 0.085), (30.5, 13.0, 0.12, 1.9, 0.09),
               (33.6, 14.0, 0.12, 1.9, 0.09), (35.4, 16.0, 0.12, 1.8, 0.09), (37.0, 18.4, 0.11, 1.6, 0.08),
               (38.6, 20.0, 0.1, 1.2, 0.06)], sides=10, mat=RIM)
    sweep(bm, [(28.0, 21.0, 0.0, 0.0, 0.0), (28.8, 21.8, 0.04, 1.4, 0.07), (30.3, 24.0, 0.06, 1.7, 0.08),
               (32.6, 25.4, 0.06, 1.7, 0.08), (34.6, 26.6, 0.04, 1.4, 0.07), (35.6, 27.3, 0.02, 0.0, 0.0)],
          sides=8, mat=LMID)

    # Forearm drum hanging under the upper arm (columns 15-22, rows 29-39).
    sweep(bm, [(19.0, 29.2, 0.0, 0.0, 0.0), (19.0, 29.6, 0.0, 2.6, 0.11), (19.0, 30.6, 0.0, 3.6, 0.15),
               (19.0, 36.8, 0.0, 3.6, 0.15), (18.8, 38.2, 0.0, 2.8, 0.12), (18.6, 39.2, 0.0, 0.0, 0.0)],
          sides=12, mat=MID)

    # Looped claw (columns 5-15, rows 31-47): a dark outer finger, an arch over the top and a
    # bright inner finger, closing round a dark gap and meeting over the gem.
    plate(bm, [(6, 38), (13.5, 38.5), (13.5, 40.5), (11.5, 44.5), (9.5, 47), (5, 47), (5, 44)],
          -0.12, 0.06, mat=DARK)  # the claw's dark lower half, filled between the fingers
    plate(bm, [(8.5, 34.5), (12.5, 34.5), (12.5, 39), (8.5, 39)], -0.12, -0.02, mat=UNDER)
    sweep(bm, [(7.6, 45.0, 0.02, 2.4, 0.1), (7.4, 41.0, 0.03, 2.3, 0.11), (7.6, 37.0, 0.04, 2.0, 0.11)],
          sides=10, mat=NECK)
    sweep(bm, [(7.0, 38.0, 0.04, 0.0, 0.0), (7.0, 37.0, 0.04, 1.6, 0.1), (7.4, 35.0, 0.05, 2.2, 0.12),
               (8.6, 33.3, 0.06, 2.4, 0.13), (10.6, 32.8, 0.06, 2.4, 0.13), (12.4, 33.6, 0.06, 1.8, 0.11),
               (13.2, 34.8, 0.06, 0.0, 0.0)], sides=10, mat=MID)
    sweep(bm, [(12.4, 32.4, 0.08, 0.0, 0.0), (12.8, 33.4, 0.08, 1.2, 0.1), (13.2, 37.0, 0.08, 1.3, 0.1),
               (13.2, 39.6, 0.08, 1.3, 0.1), (12.2, 42.0, 0.07, 1.4, 0.09), (10.8, 44.4, 0.06, 1.4, 0.09),
               (9.4, 46.6, 0.06, 0.0, 0.0)], sides=8, mat=RIM)
    # Collar over the gem and the gem itself (rows 44-51).
    ellipsoid(bm, 7.0, 45.6, 0.04, 2.6, 1.4, 0.1, mat=LMID, segments=12, rings=6)
    ellipsoid(bm, 8.6, 46.4, 0.1, 1.0, 0.7, 0.04, mat=HI, segments=8, rings=4)
    ellipsoid(bm, 6.6, 48.8, 0.0, 2.8, 2.4, 0.12, mat=GEM)
    ellipsoid(bm, 7.2, 48.3, 0.08, 1.0, 0.8, 0.05, mat=GEMHI, segments=8, rings=4)

    if mirror:
        for v in bm.verts:
            v.co.x = -v.co.x - PX
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return to_object(name, bm, mats, coll)


def composite_png(root, layout, out):
    """The whole arm's sprite as one image, padded to the 24:28 shape that render_preview expects
    for size 4 (48 x 56 px)."""
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, c0, r0 in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        for r, prow in enumerate(frame["pixels"]):
            for c, v in enumerate(prow):
                if v >= 0:
                    img[r0 + r, c0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run_assembly(script_file, name, pieces, mirror):
    """Build the arm, split it into its pieces, export each, and render previews if asked."""
    root = common.repo_root(script_file)
    sprite = merged_sprite(root, pieces)
    coll = common.reset_collection(name)
    obj = build_arm(name, sprite, coll, mirror=mirror)
    lay = sprite["assemblyLayout"]
    minx = min(e["cx"] for e in lay)
    miny = min(e["cy"] for e in lay)
    # Piece top-left corners in the grid, and centres relative to the grid's centre (split_assembly).
    corners = [(e["model"], e["cx"] - minx, e["cy"] - miny) for e in lay]
    layout = [(n, c0 + 12 - W / 2, r0 + 14 - H / 2) for n, c0, r0 in corners]
    parts = common.split_assembly(obj, layout)
    for piece in pieces:
        data = common.load_sprite(root, piece)
        common.export_sprite_model(root, [parts[piece]], f"enemies/{piece}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, corners, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([parts[piece]], str(out.parent / f"{piece}.png"), img, size=2)
