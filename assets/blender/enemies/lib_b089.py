"""Helpers shared by batch b089's model scripts: the grey multi-barrel gun works of level 4.18
(newsh9.shp frames 235, 236, 238, 239, 254, 258, 274 and 276).

Those eight 2x2 sprites are windows onto two big drawings in the sprite sheet, each 3x4 tiles
(36x56 px): a "left" gun works (tiles from 235) and a "right" one (tiles from 238) that is its
mirror image (sheet column c' = 31 - c, to within the dark outline). Each gun works is a sloped
housing with a thick barrel pointing sideways out of it and a thin one pointing the other way, a
round column down from the housing to a dark junction block, and from that a barrel slanting down
and out and another pointing straight down the screen.

The whole gun works is built once (in "composite" pixel coordinates: column c and row r of the
36x56 drawing, its centre the origin) and each sprite's 24x28 window is cut out of it with
common.split_assembly, so overlapping windows show the same geometry.

Ground object: the base sits on z = 0 and everything builds upward.
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
TAG = "nsh9gw"
PX = 1 / 12  # one sprite pixel in units
W, H = 36, 56  # the composite drawing, pixels

# Each sprite's window: top-left pixel in its composite drawing.
WINDOWS = {
    "left": {"newsh9-235": (0, 0), "newsh9-236": (12, 0), "newsh9-254": (0, 14), "newsh9-274": (12, 28)},
    "right": {"newsh9-238": (0, 0), "newsh9-239": (12, 0), "newsh9-258": (12, 14), "newsh9-276": (0, 28)},
}
ALL = [n for side in WINDOWS.values() for n in side]


def X(c):
    """Composite column (pixel centre; fractions allowed) to Blender X."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Composite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def EX(e):
    """Composite pixel edge (left edge of column e) to Blender X."""
    return (e - W / 2) / 12


def EY(e):
    """Composite pixel edge (top edge of row e) to Blender Y."""
    return (H / 2 - e) / 12


# --- geometry helpers --------------------------------------------------------------------------

def sweep(bm, path, sides=12, mat=0, smooth=True, cap_start=True, cap_end=True, cap_mat=None):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) with pixel-centre
    coordinates. Rings stand perpendicular to the path in the XY plane; the width is measured
    across the path and the height along Z. A ring of zero size collapses to a point."""
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
            faces.append((bm.faces.new(f), mat))
    if cap_start and len(rings[0]) > 1:
        faces.append((bm.faces.new(list(reversed(rings[0]))), mat if cap_mat is None else cap_mat))
    if cap_end and len(rings[-1]) > 1:
        faces.append((bm.faces.new(rings[-1]), mat if cap_mat is None else cap_mat))
    for f, m in faces:
        f.material_index = m
        f.smooth = smooth


def prism(bm, outline, z0, tops, mat=0):
    """A block on an outline of (col, row) pixel edges from z0 up to a per-vertex top height
    (`tops` is one z per outline point, or a single z). The top face is fanned from its centre."""
    if not isinstance(tops, (list, tuple)):
        tops = [tops] * len(outline)
    pts = [(EX(c), EY(r)) for c, r in outline]
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z)) for (x, y), z in zip(pts, tops)]
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    centre = bm.verts.new((cx, cy, sum(tops) / len(tops)))
    faces = [bm.faces.new(list(reversed(bottom)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
        faces.append(bm.faces.new((top[i], top[j], centre)))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


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


# --- the gun works -----------------------------------------------------------------------------

def merged_sprite():
    """One sprite dict whose colours are every b089 piece's, so any of their indices is valid."""
    data = common.load_sprite(ROOT, "newsh9-236")
    for name in ALL:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build_left(bm):
    """The left gun works in composite coordinates (the right one is its mirror image)."""
    # Material slots, see materials().
    DARK, HOUSE, BODY, BARREL, LIGHT, STRIPE, BRIGHT, CAP, COLUMN = range(9)
    MUZZLE = DARK

    # Sloped housing (rows 1-14, columns 11-22): low along its diagonal upper-left edge, rising to
    # where the big barrel comes out on the right.
    prism(bm, [(19, 1), (21, 1), (21.5, 4.5), (22.5, 14.5), (12.5, 14.5), (12.5, 10.5), (10.8, 9.6)], 0.0,
          [0.16, 0.2, 0.36, 0.34, 0.3, 0.26, 0.13], mat=HOUSE)

    # The big barrel pointing right (rows 5-12, out to column 29) with its lit end face.
    sweep(bm, [(13.0, 8.6, 0.3, 4.0, 0.17), (27.4, 8.6, 0.3, 4.0, 0.17)], sides=14, mat=BARREL, cap_end=False)
    sweep(bm, [(27.4, 8.6, 0.3, 4.1, 0.175), (28.6, 8.6, 0.3, 4.1, 0.175), (29.2, 8.6, 0.3, 3.4, 0.145),
               (29.3, 8.6, 0.3, 0.0, 0.0)], sides=14, mat=LIGHT)
    sweep(bm, [(29.0, 9.2, 0.3, 0.0, 0.0), (29.25, 9.2, 0.3, 1.8, 0.08), (29.5, 9.2, 0.3, 0.0, 0.0)],
          sides=8, mat=CAP)  # the bright spot on its end
    # The lit stripe along its lower side (row 10).
    sweep(bm, [(14.0, 10.2, 0.445, 0.7, 0.025), (27.2, 10.2, 0.445, 0.7, 0.025)], sides=6, mat=BRIGHT)

    # The thin barrel pointing left (rows 11-13, columns 1-11) on a dark bracket.
    sweep(bm, [(0.6, 12.0, 0.2, 1.7, 0.12), (12.5, 12.0, 0.2, 1.7, 0.12)], sides=10, mat=BODY, cap_mat=MUZZLE)
    sweep(bm, [(1.2, 11.9, 0.315, 0.55, 0.02), (11.0, 11.9, 0.315, 0.55, 0.02)], sides=6, mat=STRIPE)
    prism(bm, [(5.5, 13.5), (12.5, 13.5), (12.5, 16.5), (8.5, 16.5), (5.5, 14.8)], 0.0, 0.1, mat=DARK)

    # Round column down from the housing to the junction (columns 10-22, rows 11-25), lit where
    # its top end rounds over under the barrel.
    sweep(bm, [(16.2, 10.6, 0.0, 0.0, 0.0), (16.2, 11.2, 0.12, 4.5, 0.15), (16.2, 12.5, 0.16, 6.0, 0.22),
               (16.3, 14.5, 0.16, 6.5, 0.24), (16.3, 25.5, 0.16, 6.5, 0.24)], sides=14, mat=COLUMN)
    ellipsoid(bm, 16.8, 12.0, 0.31, 4.6, 1.9, 0.1, mat=STRIPE)

    # Dark junction block (columns 15-30, rows 25-33).
    prism(bm, [(15.5, 24.5), (24.0, 24.5), (25.5, 27.0), (28.0, 27.8), (31.0, 29.2), (31.0, 34.0),
               (26.0, 34.0), (21.5, 33.5), (17.0, 32.0), (15.5, 29.5)], 0.0,
          [0.24, 0.24, 0.22, 0.2, 0.17, 0.15, 0.2, 0.22, 0.2, 0.22], mat=HOUSE)
    ellipsoid(bm, 18.4, 29.8, 0.24, 2.4, 2.0, 0.07, mat=BODY)  # a lighter hub on its left

    # Barrel slanting down to the lower left (muzzle at columns 3-5, rows 32-33).
    sweep(bm, [(16.0, 23.6, 0.17, 2.6, 0.13), (4.6, 32.4, 0.17, 2.6, 0.13)], sides=10, mat=BARREL,
          cap_mat=MUZZLE)
    sweep(bm, [(13.2, 25.4, 0.3, 0.6, 0.02), (5.6, 31.4, 0.3, 0.6, 0.02)], sides=6, mat=BRIGHT)

    # Barrel straight down the screen (columns 21-25, rows 30-44) out of a lit elbow.
    sweep(bm, [(23.5, 29.6, 0.18, 2.8, 0.14), (23.5, 30.6, 0.18, 2.8, 0.14)], sides=12, mat=LIGHT, cap_end=False)
    sweep(bm, [(23.5, 30.6, 0.17, 2.6, 0.13), (23.3, 35.0, 0.16, 2.6, 0.13), (23.0, 38.5, 0.15, 2.4, 0.12),
               (22.7, 39.5, 0.15, 2.0, 0.11), (22.6, 43.3, 0.15, 2.0, 0.11), (22.6, 44.0, 0.15, 1.6, 0.09)],
          sides=12, mat=BARREL, cap_start=False, cap_mat=MUZZLE)
    sweep(bm, [(23.4, 33.0, 0.29, 0.55, 0.02), (22.9, 42.6, 0.26, 0.55, 0.02)], sides=6, mat=STRIPE)


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    return [
        pal(2, metallic=0.1, roughness=0.7),  # 0 dark bracket and muzzles
        pal(3, metallic=0.15, roughness=0.6),  # 1 dark housing and junction
        pal(7, metallic=0.2, roughness=0.5),  # 2 lighter metal: thin barrel, hub
        pal(6, metallic=0.25, roughness=0.4),  # 3 barrels
        pal(10, metallic=0.3, roughness=0.35),  # 4 lit rings and elbows
        pal(9, metallic=0.3, roughness=0.35),  # 5 lit stripes
        pal(11, metallic=0.3, roughness=0.3),  # 6 bright stripes
        pal(14, metallic=0.3, roughness=0.3),  # 7 glint on the big barrel's end
        pal(5, metallic=0.15, roughness=0.55),  # 8 the column
    ]


def build(side, name):
    """The whole left or right gun works as one object named `name`, in composite coordinates."""
    sprite = merged_sprite()
    coll = common.reset_collection(name)
    bm = bmesh.new()
    build_left(bm)
    if side == "right":
        # Mirror: right column c' = 31 - c, which is Blender x -> -x - 4/12.
        for v in bm.verts:
            v.co.x = -v.co.x - 4 / 12
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return to_object(name, bm, materials(sprite), coll)


def layout(side, names):
    """split_assembly layout for the given sprites' windows: (name, cx, cy) in composite pixels
    relative to the composite's centre."""
    out = []
    for n in names:
        x0, y0 = WINDOWS[side][n]
        out.append((n, x0 + 12 - W / 2, y0 + 14 - H / 2))
    return out


def composite_png(side, out):
    """The whole drawing from the sprites' windows, padded to 48x56 (the 24:28 shape that
    render_preview expects for size 4), as a PNG."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for n, (x0, y0) in WINDOWS[side].items():
        data = common.load_sprite(ROOT, n)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c + 6] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("composite_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run(side, names, script_name):
    """Build the gun works, cut out `names`' windows, export each as enemies/<name> and, with
    `-- --preview out.png`, render the whole thing to out.png and each piece to <name>.png beside
    it (just out.png when there is a single piece)."""
    obj = build(side, f"{script_name}-whole")
    pieces = common.split_assembly(obj, layout(side, names))
    for n in names:
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, [pieces[n]], f"enemies/{n}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for n in names:
            data = common.load_sprite(ROOT, n)
            img = ROOT / "reference" / "models" / n / data["frames"][0]["image"]
            target = out if len(names) == 1 else out.parent / f"{n}.png"
            common.render_preview([pieces[n]], str(target), img, size=2)
        if len(names) > 1:
            import tempfile
            ref = composite_png(side, Path(tempfile.mkdtemp()) / "composite.png")
            common.render_preview([obj], str(out), ref, size=4, view_px=480)
