"""Blue bat-winged beast (newsh0.shp, assembly of 13 pieces): a 3D version of its sprites.

Seen in level 2.12. Pieces of newsh0.shp side by side make one 168 x 84 px creature
(sprite.json `assemblyLayout`): a spiny blue head with two long horns reaching up the screen, a
dark jaw hanging below it, a ribbed grey shell on each shoulder, and two huge feathered wings
that sweep out and up to a grey claw at each tip. Each wing has three feather fingers along its
upper edge, a bright bone along its lower edge from the tip down to the elbow, and an arm from
the elbow back to the body with a dark underside.

The creature is mirror symmetric about the centre of assembly pixel column 96. It is built once
(the left half, mirrored, then the centre parts) in assembly coordinates and cut into this
batch's thirteen pieces with common.split_assembly. The top-row pieces of the layout
(newsh0-1, -3, -7, -9, -13: the horn tips and the left wing claw) are separate catalogue
entries, so they are built here for the fit but not exported. Every piece has one frame.

Assembly pixel (0, 0) is screen (30, -32), the top-left corner of newsh0-1.

Run: blender --background --python assets/blender/enemies/assembly-newsh0-79.py [-- --preview out.png]
(the preview is the whole creature; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh0-79"
ROOT = common.repo_root(__file__)
PIECES = ["newsh0-79", "newsh0-81", "newsh0-83", "newsh0-85", "newsh0-87", "newsh0-89", "newsh0-39",
          "newsh0-41", "newsh0-43", "newsh0-45", "newsh0-47", "newsh0-49", "newsh0-51"]
SX0, SY0 = 30, -32  # screen position of assembly pixel (0, 0)
AXIS_EDGE = 96.5  # the mirror axis: the centre of assembly pixel column 96
ROW0 = 56  # assembly row edge at Blender Y = 0 (the middle of this batch's pieces)
PX = 1 / 12


def XE(e):
    """Assembly column edge (pixel c spans edges c..c+1) to Blender X."""
    return (e - AXIS_EDGE) / 12


def YE(e):
    """Assembly row edge to Blender Y: sprite up is +Y."""
    return (ROW0 - e) / 12


def X(c):
    """Assembly pixel column (centre, fractions allowed) to Blender X."""
    return XE(c + 0.5)


def Y(r):
    """Assembly pixel row (centre) to Blender Y."""
    return YE(r + 0.5)


# --- geometry helpers (after assembly-newsht-39.py) --------------------------------------------

def sweep(bm, path, sides=8, mat=0, smooth=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; a ring of zero size collapses to a point."""
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
        rings.append([bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a)))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
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
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px, half_height, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1; outline is (col_edge, row_edge) points."""
    pts = [(XE(c), YE(r)) for c, r in outline]
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def mirror_all(bm):
    """Add a mirror image (about the axis, X = 0) of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
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


# Wing dihedral: the wings rise linearly from the wing root (column edge 74) out to the tip.
ROOT_X = XE(74)
DIHEDRAL = 0.024  # z per unit of X outboard of the root


def bend_wing(bm):
    """Cut everything at the wing root so each face stays planar, then lift what's outboard."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(ROOT_X, 0, 0), plane_no=(1, 0, 0))
    for v in bm.verts:
        if v.co.x < ROOT_X:
            v.co.z += (ROOT_X - v.co.x) * DIHEDRAL


# --- the creature ------------------------------------------------------------------------------

# Left wing outline (column edge, row edge), clockwise from the claw along the fingered upper
# edge to the root, then back along the lower edge. Taken from each column's filled extent.
WING = [
    (5, 13), (7, 11), (9, 14), (10.5, 16), (12, 18), (15, 18), (16, 21), (17.5, 25), (19, 25),
    (20.5, 24), (23, 24.5), (25, 28.5), (28, 31.5), (31, 34.5), (34, 37), (36.5, 38), (37, 32.5),
    (39.5, 31.8), (42, 32.5), (44, 33.5), (46, 36), (48, 38.5), (50, 40.5), (52, 42.5),
    (54, 44), (56, 46.5), (58, 48), (61, 49.8), (66, 47), (72, 43.5), (80, 44), (86, 46),
    (86, 62), (80, 64.5), (76, 66), (56, 66), (54, 67.5), (53.5, 75), (48, 75.5), (45, 74.5), (42, 71.5),
    (40, 68.5), (36, 64.5), (32, 61), (28, 57.5), (24, 54), (20, 50.5), (16, 46.5), (13, 43),
    (11.5, 39.5), (9.5, 35.5), (8.3, 32), (7, 28.5), (5.5, 25),
]
# The dark underside of the arm showing below it (rows 64-69).
UNDER = [(53.5, 64), (79, 64), (79, 68.5), (77, 69.6), (56, 69.6), (53.5, 71)]
# Grey shell on the shoulder: outline of its base.
SHELL = [(62, 46), (66, 44.5), (71, 43), (76, 43.2), (81, 44), (82.5, 47), (79, 53), (78, 57),
         (73, 57), (69, 52), (64, 49)]


def _inside(p, poly):
    x, y = p
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def _edge_dist(p, poly):
    best = 1e9
    for a, b in zip(poly, poly[1:] + poly[:1]):
        a, b, q = Vector(a), Vector(b), Vector(p)
        t = max(0.0, min(1.0, (q - a).dot(b - a) / max((b - a).length_squared, 1e-9)))
        best = min(best, (q - (a + (b - a) * t)).length)
    return best


def feather_paths(spacing=4.2, slope=0.8, margin=1.8, max_col=70):
    """Sweep paths for feather ridges: parallel lines (rows per column = slope) across the wing,
    kept inside WING by `margin` px and left of the shoulder shell."""
    d = Vector((1, slope)).normalized()
    n = Vector((-d.y, d.x))
    centre = Vector((38, 50))
    paths = []
    for k in range(-12, 13):
        run, runs = [], []
        for t in range(-90, 91):
            p = centre + n * (k * spacing) + d * t
            if p.x < max_col and _inside((p.x, p.y), WING) and _edge_dist((p.x, p.y), WING) >= margin:
                run.append(p)
            elif run:
                runs.append(run)
                run = []
        if run:
            runs.append(run)
        for run in runs:
            if len(run) < 8:
                continue
            idx = sorted({0, len(run) - 1, *range(0, len(run), 7)})
            pts = [run[i] for i in idx]
            path = []
            for j, p in enumerate(pts):
                end = j in (0, len(pts) - 1)
                path.append((p.x - 0.5, p.y - 0.5, 0.035, 0.0 if end else 1.7, 0.0 if end else 0.032))
            paths.append(path)
    return paths


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh079"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(54, metallic=0.15, roughness=0.6),  # 0 wing and body blue
        pal(56, metallic=0.3, roughness=0.42),  # 1 feather ridges, horns
        pal(58, metallic=0.35, roughness=0.35),  # 2 bright bones
        pal(50, metallic=0.15, roughness=0.7),  # 3 dark underside and jaw
        pal(10, metallic=0.55, roughness=0.35),  # 4 grey shell ribs and claw
        pal(6, metallic=0.5, roughness=0.45),  # 5 dark grey shell base
        pal(52, metallic=0.25, roughness=0.55),  # 6 deep blue jaw ridges, head grooves
        pal(55, metallic=0.3, roughness=0.45),  # 7 head blue
        pal(60, metallic=0.4, roughness=0.3),  # 8 pale highlights (head spikes)
    ]
    BLUE, RIDGE, BONE, DARK, GREY, GREYD, DEEP, HEAD, PALE = range(9)
    bm = bmesh.new()

    # ---- left wing (bent up, then mirrored) ----
    plate(bm, WING, -0.035, 0.035, mat=BLUE)
    plate(bm, UNDER, -0.07, 0.0, mat=DARK)
    # Feathers: raised ridges across the wing, running down toward the root like the sprite's
    # strokes, each clipped to the wing (the ones through a fingertip end in it).
    for i, path in enumerate(feather_paths()):
        sweep(bm, path, sides=6, mat=RIDGE if i % 2 else HEAD)
    # Bright bone along the lower edge from the tip to the elbow, then the arm to the body.
    sweep(bm, [(8.5, 29, 0.03, 0.0, 0.0), (10, 32, 0.035, 1.4, 0.04), (17, 42, 0.04, 1.8, 0.045),
               (28, 52, 0.04, 2.0, 0.05), (38, 59.5, 0.04, 2.0, 0.05), (45, 63.5, 0.04, 2.0, 0.05),
               (49, 64, 0.04, 2.0, 0.05)], sides=8, mat=BONE)
    sweep(bm, [(42, 64, 0.03, 0.0, 0.0), (44, 64, 0.04, 1.8, 0.05), (52, 63.8, 0.045, 2.0, 0.055),
               (60, 63.8, 0.045, 2.0, 0.055), (61, 63.8, 0.045, 0.0, 0.0)], sides=8, mat=BONE)
    sweep(bm, [(59, 64, 0.035, 0.0, 0.0), (60, 64, 0.04, 2.0, 0.05), (70, 64.2, 0.04, 2.2, 0.055),
               (79, 64.5, 0.03, 2.4, 0.06)], sides=8, mat=RIDGE)
    # The elbow knob below the arm (columns 42-53, rows 66-74).
    ellipsoid(bm, 48, 70, -0.01, 5.0, 4.0, 0.06, mat=BLUE)
    # Grey claw at the wing tip.
    sweep(bm, [(6.6, 11.6, 0.04, 0.0, 0.0), (7, 13, 0.045, 1.4, 0.05), (7.5, 18, 0.05, 2.3, 0.07),
               (8, 25, 0.045, 2.0, 0.06), (8.6, 30.5, 0.04, 0.0, 0.0)], sides=8, mat=GREY)

    bend_wing(bm)

    # ---- shoulder shell (sits at the wing root, not bent) ----
    plate(bm, SHELL, 0.0, 0.07, mat=GREYD)
    hub = (76.5, 55.5)
    for tip, w in (((62.5, 47.0), 1.3), ((66.5, 44.8), 1.6), ((70.5, 43.6), 1.7), ((74.5, 43.6), 1.7),
                   ((79.0, 44.6), 1.5)):
        sweep(bm, [(tip[0], tip[1], 0.1, 0.0, 0.0), (tip[0] + (hub[0] - tip[0]) * 0.08,
                                                      tip[1] + (hub[1] - tip[1]) * 0.08, 0.11, w, 0.05),
                   (tip[0] + (hub[0] - tip[0]) * 0.55, tip[1] + (hub[1] - tip[1]) * 0.55, 0.13, w * 1.1, 0.07),
                   (hub[0], hub[1], 0.1, w * 0.8, 0.05)], sides=8, mat=GREY)

    # ---- horn (left) ----
    sweep(bm, [(85.6, 2.0, 0.08, 0.0, 0.0), (85.7, 6, 0.08, 1.0, 0.04), (85.8, 14, 0.08, 1.6, 0.055),
               (86.2, 22, 0.08, 2.4, 0.07), (86.6, 30, 0.08, 3.0, 0.08), (87.2, 38, 0.08, 3.6, 0.09),
               (87.5, 44, 0.07, 4.0, 0.1), (88.5, 50, 0.05, 3.6, 0.09)], sides=8, mat=RIDGE)
    # Cheek ridges sweeping from the horn's base down the side of the head to the jaw.
    sweep(bm, [(86, 46, 0.12, 0.0, 0.0), (84, 50, 0.13, 1.5, 0.05), (81.5, 56, 0.1, 1.6, 0.05),
               (80.5, 62, 0.06, 1.5, 0.045), (81, 66, 0.03, 0.0, 0.0)], sides=6, mat=RIDGE)
    # V crest from the horn base in to the middle of the head.
    sweep(bm, [(89, 44, 0.16, 0.0, 0.0), (90, 45.5, 0.17, 1.2, 0.04), (94, 50, 0.21, 1.2, 0.04),
               (96, 52, 0.22, 0.0, 0.0)], sides=6, mat=PALE)
    # Tusks curving down over the dark jaw.
    sweep(bm, [(84, 62, 0.06, 0.0, 0.0), (84.5, 64, 0.07, 1.4, 0.04), (86.5, 70, 0.06, 1.4, 0.04),
               (88.5, 76, 0.03, 1.1, 0.03), (89.5, 80, 0.0, 0.0, 0.0)], sides=6, mat=DEEP)
    sweep(bm, [(91, 61, 0.1, 0.0, 0.0), (91.5, 63, 0.1, 1.2, 0.04), (92.5, 70, 0.08, 1.2, 0.04),
               (93.5, 76, 0.04, 1.0, 0.03), (94, 79, 0.02, 0.0, 0.0)], sides=6, mat=DEEP)

    mirror_all(bm)

    # ---- centre parts ----
    # Head: from between the horns down to where the jaw begins.
    loft_y(bm, 96, [(43.5, 0.0, 0.0, 0.06), (44.5, 4.0, 0.08, 0.08), (47, 9.0, 0.15, 0.06),
                    (51, 14.5, 0.19, 0.04), (56, 17.0, 0.2, 0.03), (61, 18.0, 0.19, 0.02),
                    (65, 16.0, 0.16, 0.0), (68, 11.0, 0.12, -0.01), (70, 0.0, 0.0, -0.01)], sides=12, mat=HEAD)
    # Dark jaw hanging below.
    loft_y(bm, 96, [(58, 0.0, 0.0, -0.02), (59, 15.0, 0.1, -0.02), (65, 19.0, 0.13, -0.03),
                    (70, 19.5, 0.12, -0.04), (75, 17.0, 0.1, -0.05), (79, 12.5, 0.08, -0.05),
                    (82, 8.0, 0.06, -0.05), (84.2, 0.0, 0.0, -0.05)], sides=12, mat=DARK)
    # Spine down the middle of the head with pale spikes.
    loft_y(bm, 96, [(45, 0.0, 0.0, 0.17), (46, 1.5, 0.04, 0.19), (52, 2.0, 0.05, 0.21),
                    (60, 2.0, 0.05, 0.2), (65, 1.5, 0.04, 0.14), (67, 0.0, 0.0, 0.1)], sides=6, mat=RIDGE)
    # A ridge down the middle of the jaw.
    loft_y(bm, 96, [(66, 0.0, 0.0, 0.06), (68, 1.6, 0.04, 0.08), (76, 1.4, 0.04, 0.04),
                    (82, 0.0, 0.0, 0.0)], sides=6, mat=DEEP)
    for r in (49.5, 54.5, 59.5):
        ellipsoid(bm, 96, r, 0.25, 1.1, 1.1, 0.03, mat=PALE, segments=8, rings=4)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh0-79's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh0-79")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole creature's sprite as one image at 2 px per sprite px, padded to the 24:28 shape
    render_preview expects for size 16 (192 x 224 sprite px), centred on the Blender origin."""
    import numpy as np
    w, h = 192 * 2, 224 * 2
    img = np.zeros((h, w, 4), dtype=np.float32)
    for e in layout:
        data = common.load_sprite(ROOT, e["model"])
        frame = data["frames"][0]
        for r, prow in enumerate(frame["pixels"]):
            for c, v in enumerate(prow):
                if v < 0:
                    continue
                ac, ar = e["cx"] - SX0 - 12 + c, e["cy"] - SY0 - 14 + r  # assembly pixel
                x, y = int(2 * (ac - AXIS_EDGE) + w / 2), int(2 * (ar - ROW0) + h / 2)
                img[y:y + 2, x:x + 2] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - SX0 - AXIS_EDGE, e["cy"] - SY0 - ROW0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(sprite["assemblyLayout"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=16, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
