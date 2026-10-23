"""Grey panelled dome (newsh9.shp frames 10 and 12, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 4 (levels 4.4 and 4.18), a ground structure. The two 2x2 pieces side by side
(sprite.json `assemblyLayout`, 48x28 px) are the top of a big grey dome whose rim is a circle of
about 30 px radius centred below them (the rest of the dome is in other, unrelated sprites). Its
surface is divided into panels by light seams (a cap at the top, a five-sided panel below it and
side panels), and the tops of two glossy red pods show at the bottom corners.

The dome is built whole in assembly coordinates, with the seams as low beads following its
surface, then cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-10.py [-- --preview out.png]
(the preview is the whole assembly; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh9-10"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-10", "newsh9-12"]
# Assembly pixel (0, 0) is the top-left corner of newsh9-10 (screen cx 149 - 12, cy -18 - 14);
# the assembly is 48 x 28 px and its centre (screen 161, -18) is the Blender origin.
CX0, CY0 = 161, -18
PX = 1 / 12

# The dome: rim circle centred on pixel (23.5, 38.5) with radius 30.3 px, height H.
DC, DR, DRAD = 23.5, 38.5, 30.3
H = 1.0


def X(c):
    return (c + 0.5 - 24) / 12


def Y(r):
    return (14 - (r + 0.5)) / 12


CENTRE = Vector((X(DC), Y(DR), 0.0))
RAD = DRAD * PX


def dome_z(x, y):
    d2 = ((x - CENTRE.x) ** 2 + (y - CENTRE.y) ** 2) / RAD ** 2
    return H * math.sqrt(max(0.0, 1.0 - d2))


def dome_normal(p):
    n = Vector((2 * (p.x - CENTRE.x) / RAD ** 2, 2 * (p.y - CENTRE.y) / RAD ** 2, 2 * p.z / H ** 2))
    return n.normalized()


def build_dome(bm, mat):
    """An ellipsoidal cap over the rim circle, closed underneath at z = 0."""
    seg = 72
    fracs = [0.0, 0.25, 0.42, 0.55, 0.65, 0.74, 0.81, 0.87, 0.92, 0.955, 0.98, 0.995, 1.0]
    top = bm.verts.new(CENTRE + Vector((0, 0, H)))
    rings = []
    for f in fracs[1:]:
        z = H * math.sqrt(max(0.0, 1 - f * f))
        rings.append([bm.verts.new(CENTRE + Vector((f * RAD * math.cos(2 * math.pi * i / seg),
                                                    f * RAD * math.sin(2 * math.pi * i / seg), z)))
                      for i in range(seg)])
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((top, rings[0][i], rings[0][j])))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            faces.append(bm.faces.new((r0[i], r1[i], r1[j], r0[j])))
    faces.append(bm.faces.new(list(reversed(rings[-1]))))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    faces[-1].smooth = False


def seam(bm, path, mat, width=0.75, height=0.03, lift=0.0, step=1.0, sides=6):
    """A bead lying on the dome along a polyline of (col, row) pixel centres, `width` px half wide."""
    pts2 = []
    for (c0, r0), (c1, r1) in zip(path, path[1:]):
        n = max(1, int(math.ceil(math.hypot(c1 - c0, r1 - r0) / step)))
        for k in range(n):
            t = k / n
            pts2.append((c0 + (c1 - c0) * t, r0 + (r1 - r0) * t))
    pts2.append(path[-1])
    pts = [Vector((X(c), Y(r), 0)) for c, r in pts2]
    for p in pts:
        p.z = dome_z(p.x, p.y) + lift
    rings = []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        nrm = dome_normal(p)
        t = (t - nrm * t.dot(nrm)).normalized()
        side = t.cross(nrm).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * (width * PX * math.cos(a)) + nrm * (height * math.sin(a))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat, segments=16, rings=8):
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


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9_10"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.5, roughness=0.4),  # 0 grey dome shell
        pal(10, metallic=0.6, roughness=0.3),  # 1 light seams
        pal(4, metallic=0.4, roughness=0.6),  # 2 dark grooves
        pal(71, metallic=0.2, roughness=0.25),  # 3 glossy red pods
        pal(9, metallic=0.6, roughness=0.35),  # 4 seam on the shaded side
    ]
    SHELL, SEAM, GROOVE, POD, SEAM2 = range(5)
    bm = bmesh.new()

    build_dome(bm, SHELL)

    # Left edge of the top cap, down column 18, bending left along row 18 to a junction.
    seam(bm, [(18.0, 9.2), (18.0, 16.3), (16.8, 17.5), (14.5, 18.0), (11.6, 18.4)], SEAM)
    # From the junction up-left to the rim, and down-left towards the left pod.
    seam(bm, [(11.6, 18.4), (10.0, 17.0), (8.9, 15.6), (8.3, 13.8), (8.0, 12.2)], SEAM)
    seam(bm, [(11.6, 18.4), (10.6, 20.2), (9.0, 21.3), (7.8, 22.4), (7.0, 23.8), (6.8, 26.0)], SEAM)
    # From column 18 down-right to the bottom of the five-sided panel, then straight down.
    seam(bm, [(18.0, 16.3), (18.2, 18.6), (19.3, 20.0), (20.4, 21.2), (21.4, 22.6), (21.6, 24.0),
              (21.6, 34.0)], SEAM)
    # Bottom of the top cap along row 14, round the corner and down column 27 to the bottom vertex.
    seam(bm, [(18.0, 14.0), (25.6, 14.0), (27.4, 15.0), (27.2, 16.6), (27.0, 21.0), (26.0, 22.2),
              (24.4, 23.1), (22.2, 23.4)], SEAM)
    # Right edge of the top cap, up-right to the rim.
    seam(bm, [(27.6, 14.2), (29.4, 12.8), (31.0, 11.4), (32.6, 10.2)], SEAM2)
    # The long seam down the shaded right side: a dark groove with a lit edge to its right.
    seam(bm, [(32.2, 11.6), (33.0, 14.0), (34.0, 16.0), (35.2, 17.8), (36.2, 19.8), (37.2, 21.6),
              (38.0, 23.2), (38.6, 26.0)], GROOVE, width=0.6, height=0.012)
    seam(bm, [(33.0, 12.4), (33.9, 14.4), (34.9, 16.2), (36.0, 18.1), (37.0, 20.0), (38.0, 21.8),
              (38.8, 23.4), (39.4, 25.0)], SEAM2, width=0.55, height=0.025)
    # Dark groove down the lower left panel.
    seam(bm, [(13.4, 21.6), (12.2, 23.0), (11.0, 24.4), (10.4, 25.8), (10.1, 28.0)], GROOVE,
         width=0.6, height=0.012)

    # Glossy red pods at the bottom corners, sitting on the dome's flank.
    for col in (3.0, 44.0):
        p = Vector((X(col), Y(29.0), 0))
        ellipsoid(bm, col, 29.0, dome_z(p.x, p.y) + 0.05, 5.6, 5.6, 0.32, POD)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole assembly's sprite as one image, padded to the 24:28 shape that render_preview
    expects for size 4 (48 x 56 px, the assembly in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
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
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
