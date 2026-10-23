"""Helpers for batch b058: the big blue gun of levels 1.19 and 3.23 (newshc.shp frames 238-243).

Three 2x2 enemies side by side (newshc-239, -241, -243, assembly-newshc-243) and a 1x1 piece
(newshc-238) on the left make one rifle 84 px long, lying across the screen with its muzzle to the
left: a ringed muzzle with a glowing flash under it, a thin barrel with collars and brackets, the
receiver with a raised sight box, a grip and magazine hanging down onto a purple mounting plate,
and at the back a grey canister over a ribbed stock.

`build_gun` makes the whole rifle once in assembly coordinates; the scripts cut their pieces from
it (assembly-newshc-243.py the three 2x2 pieces, newshc-238.py the muzzle tile) so they line up.

Assembly coordinates: column c / row r of the 72 x 28 px block made of newshc-239 (columns 0-23),
newshc-241 (24-47) and newshc-243 (48-71), rows 0-27. newshc-238 is the 12 x 14 tile at columns
-12..-1, rows 0-13 (its barrel rows match newshc-239's). The Blender origin is newshc-241's centre
(column edge 36, row edge 14), screen (218, -18) in the layout.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
PIECES = ["newshc-239", "newshc-241", "newshc-243"]
ALL = PIECES + ["newshc-238"]
CX0, CY0 = 218, -18  # screen position of the origin (newshc-241's centre)
PX = 1 / 12


def X(c):
    """Assembly pixel column centre (fractions allowed) to Blender X."""
    return (c + 0.5 - 36) / 12


def Y(r):
    """Assembly pixel row centre to Blender Y (sprite up is +Y)."""
    return (14 - (r + 0.5)) / 12


def EX(c):
    """Left edge of column c to Blender X."""
    return (c - 36) / 12


def EY(r):
    """Top edge of row r to Blender Y."""
    return (14 - r) / 12


# --- geometry helpers --------------------------------------------------------------------------

def _mark(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) pixel centres.
    Rings stand across the path; width is measured in the XY plane, height along Z. A ring of
    zero size is a point (a rounded or pointed end)."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
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


def plate(bm, outline, z0, z1, mat=0, bevel=0.0, smooth=False):
    """A block from z0 to z1 with an outline of (col, row) pixel edges, edges optionally bevelled."""
    before = set(bm.faces)
    pts = [(EX(c), EY(r)) for c, r in outline]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    new = set(bm.faces) - before
    if bevel:
        edges = list({e for f in new for e in f.edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, offset_type="OFFSET", segments=1,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    _mark(bm, before, mat, smooth)


def box(bm, c0, c1, r0, r1, z0, z1, mat=0, bevel=0.0):
    """A block over columns c0..c1-1 and rows r0..r1-1 (pixel edges)."""
    plate(bm, [(c0, r0), (c0, r1), (c1, r1), (c1, r0)], z0, z1, mat=mat, bevel=bevel)


def prism_x(bm, c0, c1, section, mats, cap_mat=None):
    """A bar from column edge c0 to c1 whose cross-section is a polygon of (row edge, z) points;
    `mats` gives the material of the side from each point to the next."""
    a = [bm.verts.new((EX(c0), EY(r), z)) for r, z in section]
    b = [bm.verts.new((EX(c1), EY(r), z)) for r, z in section]
    n = len(section)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[i] if isinstance(mats, list) else mats
    cm = cap_mat if cap_mat is not None else (mats[0] if isinstance(mats, list) else mats)
    bm.faces.new(list(reversed(a))).material_index = cm
    bm.faces.new(b).material_index = cm


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    _mark(bm, before, mat, True)


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


def cut_box(obj, name, x0, y0, hw, hh, collection=None):
    """Like common.split_assembly for one box of any size: keep the part of `obj` inside the box
    centred on (x0, y0) units with half sizes hw, hh, cut faces filled, moved to the origin."""
    coll = collection or obj.users_collection[0]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                   ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in obj.data.materials:
        mesh.materials.append(mat)
    piece = bpy.data.objects.new(name, mesh)
    coll.objects.link(piece)
    return piece


def merged_sprite():
    """newshc-241's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshc-241")
    for name in ALL:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def layout():
    """[(piece, cx, cy)] relative to the origin, for common.split_assembly."""
    data = common.load_sprite(ROOT, "newshc-241")
    return [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in data["assemblyLayout"]]


# Where newshc-238's 12 x 14 tile sits: columns -12..-1, rows 0-13.
MUZZLE_BOX = ((-6 - 36) / 12, (14 - 7) / 12, 6 / 12, 7 / 12)


def composite_png(out):
    """The whole rifle's sprites as one image, 96 x 112 px (render_preview size 8), centred on the
    origin: assembly column c is image column c + 12, row r is image row r + 42."""
    import numpy as np
    img = np.zeros((112, 96, 4), dtype=np.float32)
    places = [(n, cx - 12 + 48, cy - 14 + 56) for n, cx, cy in layout()]
    places.append(("newshc-238", -12 + 12, 0 + 42))
    for name, x0, y0 in places:
        data = common.load_sprite(ROOT, name)
        for r, rw in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(rw):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 96, 112, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


# --- the rifle ---------------------------------------------------------------------------------

def build_gun(name="assembly-newshc-243"):
    sprite = merged_sprite()
    coll = common.reset_collection(name)
    tag = "nshc243"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(57, metallic=0.5, roughness=0.35),  # 0 blue steel
        pal(59, metallic=0.55, roughness=0.3),  # 1 light steel collars and lit edges
        pal(53, metallic=0.5, roughness=0.45),  # 2 dark steel body
        pal(50, metallic=0.4, roughness=0.55),  # 3 near-black recesses, magazine
        pal(55, metallic=0.5, roughness=0.4),  # 4 mid steel
        pal(9, metallic=0.75, roughness=0.25),  # 5 grey canister
        pal(12, metallic=0.8, roughness=0.2),  # 6 bright grey rings
        pal(5, metallic=0.6, roughness=0.4),  # 7 dark grey end
        pal(84, metallic=0.2, roughness=0.6),  # 8 purple plate
        pal(81, metallic=0.2, roughness=0.7),  # 9 dark purple floor
        pal(88, metallic=0.25, roughness=0.5),  # 10 light purple rim
        pal(119, emission_strength=3.5),  # 11 muzzle flash
        pal(125, emission_strength=6.0),  # 12 flash core
        pal(62, metallic=0.6, roughness=0.25),  # 13 glint
        pal(52, metallic=0.45, roughness=0.5),  # 14 deep steel
    ]
    (STEEL, LIGHT, BODY, DARK, MID, CAN, RING, CANEND, PLUM, FLOOR, RIM, FLASH, CORE,
     GLINT, DEEP) = range(15)
    bm = bmesh.new()

    # ---- muzzle (newshc-238 and the left of newshc-239) ----
    # Upper muzzle tube, rows 2-6, rounded at its lit tip (column -4).
    sweep(bm, [(-4.6, 3.8, 0.0, 0.0, 0.0), (-4.4, 3.8, 0.0, 1.3, 0.09), (-3.9, 4.0, 0.0, 2.2, 0.15),
               (-3.2, 4.0, 0.0, 2.5, 0.17), (3.7, 4.0, 0.0, 2.5, 0.17)], sides=12, mat=STEEL)
    sweep(bm, [(-3.9, 3.4, 0.14, 0.0, 0.0), (-3.5, 3.4, 0.14, 0.7, 0.05), (-2.6, 3.4, 0.14, 0.7, 0.05),
               (-2.2, 3.4, 0.14, 0.0, 0.0)], sides=6, mat=GLINT)
    sweep(bm, [(3.5, 4.5, 0.0, 2.6, 0.17), (4.6, 4.5, 0.0, 2.6, 0.17)], sides=12, mat=BODY)
    # Lower nozzle under it (rows 7-11), ending round at column -4.
    sweep(bm, [(-4.5, 9.0, -0.04, 0.0, 0.0), (-4.2, 9.0, -0.04, 1.6, 0.09), (-3.6, 9.0, -0.04, 2.4, 0.12),
               (-1.5, 9.0, -0.04, 2.4, 0.12), (0.0, 8.4, -0.04, 1.6, 0.1), (1.6, 8.0, -0.04, 1.2, 0.08)],
          sides=10, mat=MID)
    # The flash: a glowing tongue from column 5 out to the left (rows 8-10), hottest at column 4.
    sweep(bm, [(-0.4, 10.2, -0.04, 0.0, 0.0), (0.4, 10.1, -0.04, 0.6, 0.05), (2.2, 9.7, -0.04, 1.1, 0.07),
               (4.0, 9.2, -0.04, 1.6, 0.09), (5.1, 9.1, -0.04, 1.5, 0.09), (5.7, 9.1, -0.04, 0.0, 0.0)],
          sides=8, mat=FLASH)
    ellipsoid(bm, 4.0, 9.2, -0.02, 1.0, 0.9, 0.08, mat=CORE, segments=8, rings=4)

    # ---- barrel (columns 4-21) ----
    sweep(bm, [(4.5, 5.0, 0.0, 1.6, 0.11), (22.5, 5.0, 0.0, 1.6, 0.11)], sides=10, mat=STEEL)
    for c0, c1 in ((4.6, 6.4), (12.6, 14.4), (19.6, 21.4)):
        sweep(bm, [(c0, 4.6, 0.0, 2.1, 0.15), (c1, 4.6, 0.0, 2.1, 0.15)], sides=10, mat=LIGHT)
    # Front bracket under the barrel (columns 6-9, rows 6-12) with a lit rod down it.
    box(bm, 6, 10, 6, 13, -0.1, 0.07, mat=BODY, bevel=0.015)
    sweep(bm, [(8.4, 6.6, 0.075, 0.9, 0.05), (8.4, 10.6, 0.075, 0.9, 0.05)], sides=6, mat=LIGHT)
    # Thin rail from it back to a strut (row 11), and the strut up to the barrel (columns 15-16).
    sweep(bm, [(9.5, 11.0, 0.0, 0.6, 0.05), (15.5, 11.0, 0.0, 0.6, 0.05)], sides=6, mat=DEEP)
    sweep(bm, [(15.5, 6.5, 0.0, 1.0, 0.07), (15.5, 10.0, 0.0, 1.0, 0.07), (15.1, 12.6, 0.0, 0.6, 0.05)],
          sides=6, mat=BODY)

    # ---- receiver (columns 21-50) ----
    # Barrel shroud (columns 22-29, rows 3-7).
    sweep(bm, [(21.6, 5.0, 0.0, 2.2, 0.15), (22.3, 5.0, 0.0, 2.6, 0.17), (30.0, 5.0, 0.0, 2.6, 0.17)],
          sides=12, mat=STEEL)
    # Lower receiver (columns 26-38, rows 7-12) and the rail under its front (rows 12-13).
    box(bm, 25.5, 38.5, 6.5, 12.5, -0.15, 0.13, mat=BODY, bevel=0.025)
    sweep(bm, [(21.7, 12.6, -0.03, 0.0, 0.0), (22.1, 12.6, -0.03, 1.0, 0.07), (32.6, 12.6, -0.03, 1.0, 0.07),
               (33.0, 12.6, -0.03, 0.0, 0.0)], sides=8, mat=LIGHT)
    # Dark slot behind the sight box (columns 33-37, rows 9-12).
    box(bm, 33, 38, 9, 13, 0.1, 0.145, mat=DARK)
    # Raised sight box (columns 30-37, rows 1-8): lit front chamfer, flat top with a dark panel.
    prism_x(bm, 29.6, 38.0, [(0.6, -0.02), (2.6, 0.27), (6.6, 0.27), (8.6, 0.04), (8.6, -0.06), (0.6, -0.06)],
            [LIGHT, STEEL, BODY, BODY, BODY, BODY], cap_mat=STEEL)
    box(bm, 32, 37, 3.6, 5.6, 0.26, 0.285, mat=MID)
    sweep(bm, [(30.0, 1.6, 0.16, 0.0, 0.0), (30.3, 1.6, 0.16, 0.5, 0.05), (32.8, 1.6, 0.16, 0.5, 0.05),
               (33.1, 1.6, 0.16, 0.0, 0.0)], sides=6, mat=GLINT)
    # Rear receiver (columns 38-45, rows 3-12), stepped down behind the sight box.
    plate(bm, [(37.5, 2.6), (37.5, 12.6), (46, 12.6), (46, 4.6), (42, 4.6), (42, 2.6)], -0.15, 0.15,
          mat=DEEP, bevel=0.025)
    sweep(bm, [(38.3, 10.2, 0.15, 0.0, 0.0), (38.8, 10.2, 0.15, 0.7, 0.05), (43.4, 10.2, 0.15, 0.7, 0.05),
               (43.9, 10.2, 0.15, 0.0, 0.0)], sides=6, mat=STEEL)
    sweep(bm, [(38.4, 3.6, 0.13, 0.0, 0.0), (38.8, 3.6, 0.13, 0.7, 0.04), (41.0, 3.6, 0.13, 0.7, 0.04),
               (41.4, 3.6, 0.13, 0.0, 0.0)], sides=6, mat=LIGHT)
    box(bm, 42, 45, 6, 10, 0.12, 0.17, mat=MID, bevel=0.01)
    # Bright joint block between receiver and canister (columns 46-50, rows 2-10).
    prism_x(bm, 45.6, 51.0, [(1.8, 0.0), (3.0, 0.2), (7.0, 0.2), (10.8, 0.06), (10.8, -0.17), (1.8, -0.17)],
            [LIGHT, STEEL, STEEL, MID, MID, MID], cap_mat=LIGHT)

    # ---- back end (newshc-243) ----
    # Grey canister (columns 52-70, rows 3-10): a cylinder with two rings at its front and a
    # rounded end that bulges down over the butt.
    sweep(bm, [(51.4, 5.6, 0.0, 2.5, 0.2), (51.8, 5.6, 0.0, 2.9, 0.24), (65.5, 5.6, 0.0, 3.0, 0.25),
               (67.5, 6.1, -0.01, 3.6, 0.25), (69.4, 6.6, -0.02, 3.5, 0.22), (70.4, 6.8, -0.03, 2.6, 0.16),
               (70.9, 6.8, -0.03, 0.0, 0.0)], sides=14, mat=CAN)
    for c in (52.0, 54.0):
        sweep(bm, [(c - 0.45, 5.6, 0.0, 3.05, 0.255), (c + 0.45, 5.6, 0.0, 3.05, 0.255)], sides=14, mat=RING)
    sweep(bm, [(56.5, 3.8, 0.17, 0.0, 0.0), (57.0, 3.8, 0.17, 0.6, 0.06), (63.0, 3.8, 0.17, 0.6, 0.06),
               (63.5, 3.8, 0.17, 0.0, 0.0)], sides=6, mat=RING)
    sweep(bm, [(66.5, 8.5, -0.02, 0.0, 0.0), (67.0, 8.2, -0.02, 2.0, 0.17), (69.5, 8.6, -0.02, 2.0, 0.15),
               (70.4, 8.8, -0.02, 0.0, 0.0)], sides=8, mat=CANEND)
    # Stock under the canister (rows 10-12), lit along its middle, ending in a butt (rows 10-14).
    sweep(bm, [(45.8, 11.0, -0.05, 0.0, 0.0), (46.2, 11.0, -0.05, 1.6, 0.12), (63.0, 11.0, -0.05, 1.7, 0.13)],
          sides=10, mat=MID)
    sweep(bm, [(53.5, 10.9, 0.06, 0.0, 0.0), (54.0, 10.9, 0.06, 0.6, 0.04), (67.5, 10.9, 0.06, 0.6, 0.04),
               (68.0, 10.9, 0.06, 0.0, 0.0)], sides=6, mat=LIGHT)
    plate(bm, [(62, 9.6), (62, 13), (64, 15), (70, 15), (71, 13), (71, 9.6)], -0.14, 0.07,
          mat=STEEL, bevel=0.03)
    # Ribbed grip under the stock (columns 51-63, rows 13-19).
    plate(bm, [(50.6, 12.6), (51, 17), (54, 19), (63.6, 19), (63.6, 12.6)], -0.13, 0.03, mat=DARK, bevel=0.015)
    for c, r1 in ((52, 17.6), (54, 17.6), (56, 17.6), (58, 17.0)):
        sweep(bm, [(c, 13.4, 0.03, 0.0, 0.0), (c, 13.8, 0.03, 0.5, 0.05), (c, r1 - 0.4, 0.03, 0.5, 0.05),
                   (c, r1, 0.03, 0.0, 0.0)], sides=6, mat=MID)
    box(bm, 59.6, 63.4, 14.6, 18.6, -0.1, 0.07, mat=MID, bevel=0.015)

    # ---- grip, magazine and the purple plate (newshc-241) ----
    # Grip frame: the left bar (columns 30-31), the bottom (rows 21-23) and the lit right side.
    box(bm, 30, 32, 14.5, 21, -0.16, 0.06, mat=DEEP, bevel=0.015)
    box(bm, 30, 42, 20.5, 24, -0.16, 0.06, mat=DEEP, bevel=0.015)
    plate(bm, [(41, 15), (42, 15), (42, 23), (37.5, 23), (37.5, 21), (39, 18)], -0.16, 0.08,
          mat=MID, bevel=0.015)
    # Magazine between them (columns 33-40, rows 13-20), set a little lower.
    plate(bm, [(32.5, 12.5), (32.5, 20.5), (38, 20.5), (38.5, 18.5), (40.5, 15.5), (43, 15.5), (43, 12.5)],
          -0.16, 0.0, mat=DARK, bevel=0.015)
    box(bm, 33.5, 37.5, 13, 14.6, -0.02, 0.03, mat=DEEP)
    # Purple mounting plate filling newshc-241's tile: a dark floor with a raised rim.
    # (kept a hair inside the tile so the cut planes at its edges don't fall on its faces)
    L, R, T, B = 24.03, 47.97, 0.03, 27.9
    box(bm, L, R, T, B, -0.28, -0.22, mat=FLOOR)
    box(bm, L, 28.6, T, B, -0.24, -0.18, mat=PLUM, bevel=0.012)
    box(bm, 45.4, R, T, B, -0.24, -0.18, mat=PLUM, bevel=0.012)
    box(bm, 28.6, 45.4, 26.4, B, -0.24, -0.19, mat=PLUM, bevel=0.01)
    box(bm, 28.6, 45.4, T, 2.5, -0.24, -0.18, mat=RIM, bevel=0.01)
    box(bm, L, 28.6, T, 2.0, -0.18, -0.17, mat=RIM)
    box(bm, 46.4, R, T, B, -0.18, -0.17, mat=RIM)

    return to_object(name, bm, mats, coll)
