"""Red fortress centre (newshf.shp, four 2x2 pieces: newshf-157, -159 top, newshf-195, -197
bottom): a 3D version of its sprites, built whole and cut into the four pieces.

Seen in episode 1 (levels 1.10, 1.29, 1.38), 2 and 3 and 4. It is the middle of a wide red
ground fortress (the left part is assembly-newshf-191 and the right part assembly-newshf-199,
with the glowing fins). Its four pieces make a 48x56 px block:

- a tall rounded tower down the middle (columns 13-35, rows 5-41) with a rounded top end, a
  seam down its axis, a groove round its cap and a chevron of grooves low down,
- lower wings either side (columns 0-12 and 36-47, rows 13-42) with two pipes running down
  each and raised cross bars,
- a slatted lower deck under each wing (rows 43-55),
- a grey gun under the tower: three barrels pointing down the screen between two dark grey
  housings.

Each piece is one frame, so each gets one model. The whole block is mirror symmetric about
pixel column 24 (the tower's seam).

Run: blender --background --python assets/blender/enemies/assembly-newshf-195.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newshf-195"
ROOT = common.repo_root(__file__)
PIECES = ["newshf-157", "newshf-159", "newshf-195", "newshf-197"]
# Assembly pixel (0, 0) is the top-left corner of newshf-157 (screen cx 142 - 12, cy -18 - 14);
# the block is 48 x 56 px and its centre (screen 154, -4) is the Blender origin.
CX0, CY0 = 154, -4
W, H = 48, 56
AXIS = 24  # mirror axis: the centre of pixel column 24
PX = 1 / 12


def X(c):
    """Assembly pixel column (centre; fractions allowed, n.5 is a pixel edge) to Blender X."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def M(c):
    """Mirror a column about the axis."""
    return 2 * AXIS - c


# --- geometry helpers --------------------------------------------------------------------------

def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=8, mat=0, smooth=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units); rings stand
    across the path in the XY plane and along Z."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    _faces(bm, faces, mat, smooth)


def arch(bm, col, sections, mat, p=2.6, k=12):
    """A rounded hump along Y on a flat base: sections are (row, half_width_px, height, z0); the
    cross-section is the upper half of a superellipse of exponent p (2 = ellipse, higher = boxier)."""
    rings = []
    for r, w, h, z0 in sections:
        ring = []
        for i in range(k + 1):
            a = math.pi * i / k
            c, s = math.cos(a), math.sin(a)
            x = w * PX * math.copysign(abs(c) ** (2 / p), c)
            ring.append(bm.verts.new((X(col) + x, Y(r), z0 + h * abs(s) ** (2 / p))))
        rings.append(ring)
    top, flat = [], []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(k):
            top.append(bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i])))
        flat.append(bm.faces.new((r0[k], r0[0], r1[0], r1[k])))
    flat.append(bm.faces.new(list(reversed(rings[0]))))
    flat.append(bm.faces.new(rings[-1]))
    _faces(bm, top, mat, True)
    _faces(bm, flat, mat, False)


def block(bm, c0, c1, profile, mat, z0=0.0):
    """A box from pixel edge c0 to c1 whose top height follows profile [(row, z_top), ...] down
    the sprite (rows are pixel edges, first and last are its ends)."""
    rings = []
    for r, zt in profile:
        y = Y(r)
        rings.append([bm.verts.new((X(c0), y, z0)), bm.verts.new((X(c1), y, z0)),
                      bm.verts.new((X(c1), y, zt)), bm.verts.new((X(c0), y, zt))])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    _faces(bm, faces, mat, False)


def plate(bm, c0, r0, c1, r1, z0, z1, mat):
    """A flat box between pixel edges (c0, r0) and (c1, r1), from z0 to z1."""
    block(bm, c0, c1, [(r0, z1), (r1, z1)], mat, z0=z0)


def interp(profile, r):
    """Piecewise-linear lookup in [(row, value...), ...] (rows increasing)."""
    if r <= profile[0][0]:
        return profile[0][1:]
    for a, b in zip(profile, profile[1:]):
        if r <= b[0]:
            t = (r - a[0]) / (b[0] - a[0])
            return tuple(va + (vb - va) * t for va, vb in zip(a[1:], b[1:]))
    return profile[-1][1:]


# --- the fortress ------------------------------------------------------------------------------

# Tower: (row, half width px, height) from its rounded top end to its straight bottom end.
TOWER = [(4.5, 2.6, 0.24), (5.5, 4.5, 0.33), (6.5, 6.6, 0.39), (7.5, 8.6, 0.43), (8.5, 10.0, 0.46),
         (9.5, 11.0, 0.48), (11.0, 11.4, 0.5), (42.5, 11.5, 0.5)]
TP = 2.6  # its superellipse exponent


def tower_z(c, r):
    """Height of the tower's top surface over pixel (c, r)."""
    w, h = interp(TOWER, r)
    u = min(abs(c - AXIS) / w, 0.999)
    return h * (1 - u ** TP) ** (1 / TP)


# Wings: top height down the sprite, low under the tower's shadow at the top and highest at the
# bright band (rows 32-36).
WING = [(12.5, 0.17), (22.0, 0.2), (31.0, 0.25), (37.0, 0.25), (42.5, 0.23)]


def wing_z(r):
    return interp(WING, r)[0]


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshf195"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(72, metallic=0.3, roughness=0.45),  # 0 tower red
        pal(69, metallic=0.25, roughness=0.55),  # 1 wing and deck slats
        pal(73, metallic=0.35, roughness=0.35),  # 2 pipes
        pal(70, metallic=0.3, roughness=0.5),  # 3 upper cross bars
        pal(74, metallic=0.35, roughness=0.4),  # 4 lower cross bars, panel
        pal(66, metallic=0.2, roughness=0.65),  # 5 deck
        pal(67, metallic=0.2, roughness=0.6),  # 6 grooves and red struts
        pal(65, metallic=0.2, roughness=0.7),  # 7 seam
        pal(2, metallic=0.4, roughness=0.6),  # 8 dark base under the gun
        pal(4, metallic=0.6, roughness=0.4),  # 9 gun housings
        pal(10, metallic=0.75, roughness=0.25),  # 10 barrels
        pal(6, metallic=0.7, roughness=0.35),  # 11 barrel collars
        pal(64, metallic=0.2, roughness=0.8),  # 12 dark line
        pal(71, metallic=0.3, roughness=0.5),  # 13 deck lip
        pal(12, metallic=0.75, roughness=0.2),  # 14 muzzles
    ]
    TOWERM, WINGM, PIPE, BAR, BAR2, DECK, GROOVE, SEAM, BASE, HOUSING, BARREL, COLLAR, LINE, LIP, MUZZLE = range(15)
    bm = bmesh.new()

    # ---- tower ----
    arch(bm, AXIS, [(r, w, h, 0.0) for r, w, h in TOWER], TOWERM, p=TP, k=14)

    def groove(points, mat=GROOVE, w=0.45, h=0.014, steps=4):
        path = []
        for (c0, r0), (c1, r1) in zip(points, points[1:]):
            for s in range(steps + (1 if (c1, r1) == points[-1] else 0)):
                t = s / steps
                c, r = c0 + (c1 - c0) * t, r0 + (r1 - r0) * t
                path.append((c, r, tower_z(c, r) + 0.004, w, h))
        sweep(bm, path, sides=4, mat=mat, smooth=False)

    # Seam down the axis and the groove round the cap (row 14, then down and out to the edges).
    groove([(AXIS, 5.2), (AXIS, 14.0), (AXIS, 42.3)], mat=SEAM, w=0.5, steps=3)
    groove([(14.0, 19.8), (19.0, 14.3), (29.0, 14.3), (34.0, 19.0)], steps=3)
    # Chevron low down, converging on the seam.
    groove([(19.6, 32.4), (23.4, 36.8)], steps=3)
    groove([(M(19.6), 32.4), (M(23.4), 36.8)], steps=3)

    # ---- wings, decks and gun, left half (mirrored for the right) ----
    for side in (-1, 1):
        m = (lambda c: c) if side < 0 else M
        # Wing body: the outer edge reaches the block's edge (column 0 on the left, 47 on the right).
        c_out, c_in = (-0.5, 12.5) if side < 0 else (47.5, 35.5)
        lo, hi = min(c_out, c_in), max(c_out, c_in)
        block(bm, lo, hi, WING, WINGM)
        # Two pipes down each wing (columns 1-2 and 5-6), riding its top.
        for c in (1.5, 5.5):
            path = [(m(c), r, wing_z(r) + 0.02, 1.15, 0.055) for r in (13.4, 13.6, 22, 31, 37, 42.4, 42.6)]
            path[0] = (m(c), 13.3, wing_z(13.3) + 0.01, 0.6, 0.03)
            path[-1] = (m(c), 42.7, wing_z(42.7) + 0.01, 0.6, 0.03)
            sweep(bm, path, sides=8, mat=PIPE)
        # Cross bars: an upper one (row 18-21) with a dark line under it, and a bright lower one.
        a, b = sorted((m(3.5), m(11.5)))
        plate(bm, a, 17.5, b, 21.5, 0.0, wing_z(21.5) + 0.03, BAR)
        plate(bm, a, 21.5, b, 22.5, 0.0, wing_z(22.5) + 0.006, LINE)
        a, b = sorted((m(6.5), m(11.5)))
        plate(bm, a, 38.5, b, 42.5, 0.0, wing_z(38.5) + 0.04, BAR2)
        # Between the pipe and the tower (columns 8-11): two dark sunken panels above and below
        # the upper bar, and a raised panel down to the lower bar.
        a, b = sorted((m(7.5), m(11.5)))
        plate(bm, a, 13.5, b, 17.5, 0.0, wing_z(17.5) + 0.004, GROOVE)
        plate(bm, a, 22.5, b, 27.5, 0.0, wing_z(27.5) + 0.004, GROOVE)
        block(bm, a, b, [(r, wing_z(r) + 0.015) for r in (27.5, 31.0, 38.5)], LIP)

        # Lower deck (rows 43-55): slats, a vertical rib, a bright lip, then a lower step.
        block(bm, lo, hi, [(42.5, 0.15), (52.5, 0.15)], DECK)
        plate(bm, lo, 43.5, hi, 46.5, 0.0, 0.18, WINGM)
        plate(bm, lo, 47.5, hi, 49.5, 0.0, 0.17, WINGM)
        a, b = sorted((m(8.5), m(9.5)))
        plate(bm, a, 42.5, b, 51.5, 0.0, 0.19, WINGM)
        plate(bm, lo, 51.5, hi, 52.5, 0.0, 0.18, LIP)
        block(bm, lo, hi, [(52.5, 0.1), (55.5, 0.1)], WINGM)

        # Gun housing beside the barrels (rows 43-52) and its red strut.
        a, b = sorted((m(12.5), m(18.5))) if side < 0 else (29.5, 34.5)
        plate(bm, a, 42.5, b, 52.5, 0.0, 0.19, HOUSING)
        a, b = (18.5, 19.5) if side < 0 else (34.5, 35.5)
        plate(bm, a, 42.5, b, 51.5, 0.0, 0.21, GROOVE)

    # Dark base under the gun and the three barrels pointing down the screen.
    plate(bm, 12.5, 42.5, 35.5, 55.5, 0.0, 0.05, BASE)
    plate(bm, 19.5, 42.5, 29.5, 52.5, 0.0, 0.09, HOUSING)
    for c, rw, rz in ((20.5, 1.2, 0.085), (AXIS, 1.5, 0.1), (M(20.5), 1.2, 0.085)):
        zc = 0.05 + rz
        sweep(bm, [(c, 41.5, zc, rw, rz), (c, 51.5, zc, rw, rz)], sides=10, mat=BARREL)
        sweep(bm, [(c, 51.4, zc, rw * 1.15, rz * 1.15), (c, 52.6, zc, rw * 1.15, rz * 1.15)], sides=10, mat=COLLAR)
        sweep(bm, [(c, 52.5, zc, rw * 0.95, rz * 0.95), (c, 55.6, zc, rw * 0.95, rz * 0.95)], sides=10, mat=MUZZLE)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for mat in mats:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite():
    """newshf-195's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshf-195")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The four pieces' sprites as one 48 x 56 image (the shape render_preview expects for size 4)."""
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + W // 2 - 12, cy + H // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
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
