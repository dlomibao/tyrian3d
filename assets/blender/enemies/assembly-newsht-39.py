"""Red crab boss (newsht.shp, assembly of 12 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.19), 3 and 4. Twelve 2x2 enemies side by side make one 144x56 px
machine (sprite.json `assemblyLayout`): a red body with two dark glass orbs set in U-shaped
frames, a grey visor between them, a grey cannon below, two glowing exhausts on its back, and
two arms that reach out sideways on a beam and hang down to claws with a glowing red eye
(newsht-39 and newsht-49, whose three frames only brighten the eye, so one model covers them).

The whole machine is built once in assembly coordinates (left half, mirrored about pixel column
71, which is the sprite's axis), then cut into the twelve pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsht-39.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsht-39"
ROOT = common.repo_root(__file__)
PIECES = ["newsht-1", "newsht-3", "newsht-5", "newsht-7", "newsht-9", "newsht-11",
          "newsht-39", "newsht-41", "newsht-43", "newsht-45", "newsht-47", "newsht-49"]
# Assembly pixel (0, 0) is the top-left corner of newsht-1 (screen cx 81 - 12, cy 19 - 14);
# the assembly is 144 x 56 px and its centre (screen 141, 33) is the Blender origin.
CX0, CY0 = 141, 33
AXIS_COL = 71  # the sprite is mirror symmetric about the centre of pixel column 71


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 72) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (28 - (r + 0.5)) / 12


AX = X(AXIS_COL)
PX = 1 / 12  # one sprite pixel in units


# --- geometry helpers --------------------------------------------------------------------------

def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path; the width is measured across the path in the XY plane and the
    height along Z. A ring of zero size collapses to a point (a rounded or pointed end)."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
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


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite (along Y) centred on column `col`: sections are
    (row, half_width_px, half_height_units, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges."""
    pts = [(X(c - 0.5), Y(r - 0.5)) for c, r in outline]
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def mirror_all(bm):
    """Add a mirror image (about the sprite's axis) of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * AX - v.co.x
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


# --- the machine -------------------------------------------------------------------------------

def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsht39"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(71, metallic=0.35, roughness=0.45),  # 0 red hull
        pal(69, metallic=0.3, roughness=0.5),  # 1 darker red plates
        pal(66, metallic=0.2, roughness=0.6),  # 2 deep red bands and grooves
        pal(74, metallic=0.4, roughness=0.35),  # 3 light red ribs
        pal(3, metallic=0.85, roughness=0.18),  # 4 dark glass orbs
        pal(5, metallic=0.7, roughness=0.35),  # 5 grey pipes and canisters
        pal(2, metallic=0.2, roughness=0.8),  # 6 dark recesses
        pal(9, metallic=0.8, roughness=0.25),  # 7 bright grey rims
        pal(119, emission_strength=3.0),  # 8 exhaust glow
        pal(125, emission_strength=5.0),  # 9 hot exhaust streaks, eye core
        pal(113, metallic=0.2, roughness=0.5),  # 10 eye socket
        pal(4, metallic=0.75, roughness=0.3),  # 11 visor and cannon
    ]
    HULL, PLATE, BAND, RIB, ORB, PIPE, DARK, RIM, GLOW, HOT, SOCKET, VISOR = range(12)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Arm: a beam out of the shoulder, bending down into a thick upper arm (columns 4-14).
    loft_y(bm, 9.5, [(19.7, 1.5, 0.08, 0.0), (20.3, 3.0, 0.14, 0.0), (21.2, 4.2, 0.18, 0.0),
                     (22.5, 5.0, 0.21, 0.0), (24.0, 5.5, 0.22, 0.0), (34.6, 5.5, 0.22, 0.0),
                     (35.4, 5.9, 0.23, 0.0), (38.4, 5.9, 0.23, 0.0), (39.4, 4.4, 0.17, 0.0)],
           sides=14, mat=HULL)
    # Ribs down the upper arm and a dark band at its cuff.
    for dc in (-2.6, 0.0, 2.6):
        loft_y(bm, 9.5 + dc, [(23.5, 0.0, 0.0, 0.2), (24.5, 0.7, 0.05, 0.2 - abs(dc) * 0.012),
                              (34.0, 0.7, 0.05, 0.2 - abs(dc) * 0.012), (34.8, 0.0, 0.0, 0.2)],
               sides=6, mat=RIB)
    loft_y(bm, 9.5, [(34.7, 5.75, 0.226, 0.0), (35.3, 5.95, 0.233, 0.0)], sides=14, mat=BAND)

    # Forearm and claw (columns 8-20, rows 40-52) with the eye looking out of its top.
    loft_y(bm, 14.0, [(39.0, 3.5, 0.12, -0.02), (40.0, 5.0, 0.16, -0.02), (41.5, 6.0, 0.19, -0.02),
                      (49.5, 6.3, 0.2, -0.02), (50.8, 5.3, 0.17, -0.02), (52.0, 3.5, 0.12, -0.02),
                      (52.8, 1.5, 0.06, -0.02)], sides=14, mat=HULL)
    loft_y(bm, 18.8, [(39.6, 0.0, 0.0, 0.0), (40.4, 1.1, 0.16, 0.0), (49.5, 1.2, 0.16, 0.0),
                      (50.6, 0.0, 0.0, 0.0)], sides=8, mat=PLATE)  # rib down its outer side
    ellipsoid(bm, 13.6, 47.2, 0.15, 3.4, 3.2, 0.06, mat=SOCKET)
    ellipsoid(bm, 13.6, 47.2, 0.16, 2.5, 2.4, 0.065, mat=GLOW)
    ellipsoid(bm, 13.3, 46.6, 0.19, 1.1, 1.1, 0.045, mat=HOT)
    sweep(bm, [(7.2, 47.5, -0.01, 0.0, 0.0), (7.6, 47.5, -0.01, 1.0, 0.05), (10.5, 47.5, -0.01, 1.0, 0.05)],
          sides=8, mat=PIPE)  # grey stub on its inner side

    # Grey works behind the top of the upper arm: a ringed canister and a box (rows 10-19).
    loft_y(bm, 11.0, [(10.8, 0.0, 0.0, 0.05), (11.3, 1.8, 0.09, 0.05), (12.0, 2.3, 0.12, 0.05),
                      (12.7, 2.3, 0.12, 0.05), (13.0, 1.8, 0.09, 0.05), (13.4, 2.3, 0.12, 0.05),
                      (14.7, 2.3, 0.12, 0.05), (15.0, 1.8, 0.09, 0.05), (15.4, 2.3, 0.12, 0.05),
                      (20.0, 2.3, 0.12, 0.05)], sides=10, mat=PIPE)
    plate(bm, [(15, 11), (20, 11), (20, 20), (15, 20)], -0.08, 0.12, mat=PIPE)
    plate(bm, [(16, 16.5), (19.5, 16.5), (19.5, 19.5), (16, 19.5)], 0.12, 0.15, mat=RIM)
    sweep(bm, [(19.5, 18.0, 0.03, 1.2, 0.07), (25.5, 18.0, 0.03, 1.2, 0.07)], sides=8, mat=PIPE)
    # Hose down the inside of the upper arm (rows 25-35).
    sweep(bm, [(19.8, 23.5, 0.02, 1.5, 0.1), (19.2, 27.0, 0.02, 1.6, 0.1), (18.0, 30.5, 0.02, 1.6, 0.1),
               (17.2, 33.5, 0.0, 1.5, 0.09), (16.6, 35.8, -0.02, 1.4, 0.08)], sides=8, mat=PIPE)

    # The beam from the shoulder out to the arm (rows 20-22).
    sweep(bm, [(12.0, 21.4, 0.06, 1.8, 0.11), (42.5, 21.4, 0.06, 1.8, 0.11)], sides=10, mat=HULL)

    # Shoulder block (columns 26-41, rows 14-23) with ribs on top, and a claw hanging under it.
    plate(bm, [(26, 15), (27, 14), (38, 14), (39, 15), (39, 17), (42, 17), (42.5, 24), (27, 24), (26, 23)],
          -0.12, 0.12, mat=HULL)
    for c in (27.0, 29.6, 32.2, 34.8, 37.4):
        plate(bm, [(c, 14.6), (c + 1, 14.6), (c + 1, 19.6), (c, 19.6)], 0.12, 0.15, mat=RIB)
    loft_y(bm, 28.6, [(22.5, 2.0, 0.08, -0.05), (27.0, 1.6, 0.07, -0.05), (28.6, 2.5, 0.08, -0.05),
                      (30.6, 2.5, 0.08, -0.05), (31.6, 1.2, 0.05, -0.05)], sides=8, mat=PLATE)
    loft_y(bm, 43.0, [(23.5, 0.9, 0.06, -0.05), (30.5, 0.9, 0.06, -0.05)], sides=6, mat=PLATE)

    # Thick grey hose from the back of the body down to the shoulder (rows 6-13).
    sweep(bm, [(45.0, 7.0, 0.04, 2.6, 0.14), (41.5, 8.4, 0.04, 3.0, 0.15), (38.6, 10.2, 0.03, 3.0, 0.15),
               (37.0, 12.2, 0.02, 2.8, 0.14), (36.6, 14.5, 0.0, 2.4, 0.12)], sides=10, mat=PIPE)

    # Upper band across the back of the body (rows 9-12), rounded at its outer end.
    sweep(bm, [(40.6, 11.0, 0.03, 0.0, 0.0), (41.2, 11.0, 0.03, 1.6, 0.09), (42.3, 11.0, 0.03, 2.4, 0.13),
               (44.0, 11.0, 0.03, 2.6, 0.15), (AXIS_COL, 11.0, 0.03, 2.6, 0.15)], sides=10, mat=HULL)
    # Cheek plate between the band and the orb's frame (columns 39-62, rows 13-24).
    plate(bm, [(39, 13), (63, 13), (63, 25), (53, 25), (51.5, 26), (43, 26), (39, 22)], -0.12, 0.08, mat=PLATE)

    # U-shaped frame round the orb: down its outer side, round the bottom, up the inner strut.
    sweep(bm, [(48.6, 12.5, 0.03, 2.4, 0.12), (48.6, 20.0, 0.03, 2.7, 0.13), (49.0, 28.0, 0.03, 3.0, 0.13),
               (50.6, 34.0, 0.03, 3.2, 0.13), (54.0, 37.4, 0.03, 3.1, 0.13), (58.0, 38.0, 0.03, 3.1, 0.13),
               (62.0, 37.2, 0.03, 3.0, 0.13), (65.0, 34.0, 0.03, 2.9, 0.13), (65.9, 29.0, 0.03, 2.7, 0.12),
               (65.9, 24.4, 0.03, 2.3, 0.1)], sides=10, mat=HULL)
    # The dark glass orb (columns 54-64, rows 17-27) and the grey lip under it (rows 30-33).
    ellipsoid(bm, 59.3, 22.4, 0.0, 5.6, 5.6, 0.24, mat=ORB, segments=18, rings=9)
    sweep(bm, [(51.8, 31.6, 0.0, 0.0, 0.0), (52.4, 31.6, 0.0, 1.5, 0.07), (60.6, 31.6, 0.0, 1.5, 0.07),
               (61.2, 31.6, 0.0, 0.0, 0.0)], sides=8, mat=VISOR)
    # Dark recess behind the orb and the visor.
    plate(bm, [(50, 12.5), (AXIS_COL + 0.5, 12.5), (AXIS_COL + 0.5, 36), (50, 36)], -0.11, -0.05, mat=DARK)

    # Glowing exhaust on the back, slanting out (columns 54-66, rows 1-7), in a red housing.
    plate(bm, [(60, 1.5), (67.5, 1.5), (61.5, 8.5), (53.5, 8.5)], -0.04, 0.09, mat=GLOW)
    for off in (0.0, 3.0):
        plate(bm, [(61.4 + off, 2.2), (62.4 + off, 2.2), (57.0 + off, 7.8), (56.0 + off, 7.8)], 0.09, 0.11, mat=HOT)
    plate(bm, [(59, 8.2), (68, 8.2), (68, 10), (58, 10)], -0.06, 0.06, mat=BAND)

    mirror_all(bm)

    # ---- centre parts (symmetric about the axis) ----

    # Raised spine between the exhausts (columns 62-81, rows 4-12) with a plate down its middle.
    loft_y(bm, AXIS_COL, [(3.8, 2.5, 0.08, 0.07), (4.6, 3.6, 0.14, 0.08), (6.0, 8.5, 0.17, 0.08),
                          (8.0, 10.0, 0.18, 0.06), (12.5, 10.5, 0.18, 0.04), (13.6, 9.0, 0.12, 0.02)],
           sides=10, mat=HULL)
    loft_y(bm, AXIS_COL, [(4.8, 0.0, 0.0, 0.2), (5.6, 3.6, 0.06, 0.2), (12.4, 3.8, 0.06, 0.2),
                          (13.0, 0.0, 0.0, 0.2)], sides=8, mat=PLATE)
    # Grey visor between the orbs (columns 65-77, rows 14-19), on a dark bracket.
    sweep(bm, [(63.8, 17.0, 0.06, 0.0, 0.0), (64.6, 17.0, 0.06, 2.4, 0.12), (78.4, 17.0, 0.06, 2.4, 0.12),
               (79.2, 17.0, 0.06, 0.0, 0.0)], sides=10, mat=VISOR)
    plate(bm, [(68, 19.5), (75, 19.5), (75, 24), (68, 24)], -0.08, 0.04, mat=PIPE)
    # Cannon pointing down the screen between the frames (columns 68-74, rows 29-34).
    loft_y(bm, AXIS_COL, [(28.0, 3.0, 0.1, 0.0), (33.6, 3.2, 0.11, 0.0)], sides=12, mat=PIPE)
    loft_y(bm, AXIS_COL, [(33.5, 3.4, 0.12, 0.0), (34.6, 3.5, 0.12, 0.0), (34.8, 2.2, 0.08, 0.0)],
           sides=12, mat=RIM)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsht-39's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsht-39")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole machine's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 12 (144 x 168 px, the machine in the middle)."""
    import numpy as np
    img = np.zeros((168, 144, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 72 - 12, cy + 84 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 144, 168, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=12, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
