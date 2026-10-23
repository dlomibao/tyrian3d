"""Lava larva (newshe.shp, assembly of 8 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.8), lying on the ground. Eight 2x2 ground enemies side by side make
one 96x56 px creature (sprite.json `assemblyLayout`): a dark red, segmented grub lying along the
screen with its head on the left. The head has two glowing yellow eyes over a dark open mouth
with a bright lower lip, a collar of pink knobs behind the eyes and a thin feeler curling down
from its chin along its belly to a row of pink feet. Six body segments, each with a glowing
leading rim and a pink knob on its back, taper to a dark tail cap with a pink stinger.

The whole creature is built once in assembly coordinates and cut into the pieces with
common.split_assembly. newshe-277 (eggs below it in the layout) is a separate enemy, not part
of this model. Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newshe-121.py [-- --preview out.png]
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

NAME = "assembly-newshe-121"
ROOT = common.repo_root(__file__)
PIECES = ["newshe-121", "newshe-119", "newshe-117", "newshe-115",
          "newshe-83", "newshe-81", "newshe-79", "newshe-77"]
# Assembly pixel (0, 0) is the top-left corner of newshe-77 (screen cx 213 - 12, cy 1 - 14);
# the creature's 96 x 56 px block has its centre (screen 249, 15) at the Blender origin.
CX0, CY0 = 249, 15
PX = 1 / 12


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 48) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (28 - (r + 0.5)) / 12


# --- body profile ------------------------------------------------------------------------------

# (column, top row, bottom row) of the body's outline, head to tail, without the feeler and feet.
PROFILE = [
    (7.6, 21.5, 28.0), (8.0, 19.0, 30.0), (9.0, 17.0, 32.5), (10.0, 16.0, 35.0), (12.0, 14.0, 36.8),
    (14.0, 12.0, 37.2), (16.0, 11.0, 37.4), (20.0, 10.0, 37.4), (24.0, 10.0, 37.0), (27.0, 10.0, 39.5),
    (29.0, 8.3, 42.5), (32.0, 8.5, 44.0), (35.0, 8.5, 45.0), (37.0, 5.0, 46.0), (40.0, 4.0, 46.0),
    (43.0, 3.0, 45.0), (46.0, 5.0, 43.0), (48.0, 6.5, 42.0), (52.0, 5.0, 41.2), (55.0, 5.0, 42.0),
    (57.0, 8.8, 43.0), (60.0, 8.0, 44.0), (64.0, 8.0, 45.0), (65.5, 11.8, 45.0), (70.0, 12.0, 44.5),
    (72.5, 12.0, 43.5), (74.0, 13.8, 43.0), (78.0, 14.0, 40.0), (80.0, 15.0, 37.0), (85.0, 15.5, 37.0),
    (87.0, 17.0, 36.8), (89.0, 19.0, 35.0), (91.0, 20.0, 30.8), (92.5, 21.5, 28.8), (93.6, 23.5, 26.0),
]


def profile(c):
    """(top row, bottom row) of the body at column c, interpolated."""
    if c <= PROFILE[0][0]:
        return PROFILE[0][1:]
    for (c0, t0, b0), (c1, t1, b1) in zip(PROFILE, PROFILE[1:]):
        if c <= c1:
            f = (c - c0) / (c1 - c0)
            return t0 + (t1 - t0) * f, b0 + (b1 - b0) * f
    return PROFILE[-1][1:]


def height_for(half_w):
    """The body's height (units) for a half width (units): a rounded but low grub."""
    return 0.5 * half_w + 0.06


EXP = 0.7  # cross-section exponent: <1 makes the D-shaped section fuller


def surface_z(c, r):
    """Height of the body's top surface over assembly pixel (c, r)."""
    t, b = profile(c)
    yc, w = (Y(t - 0.5) + Y(b + 0.5)) / 2, (Y(t - 0.5) - Y(b + 0.5)) / 2
    u = (Y(r) - yc) / w
    if abs(u) >= 1:
        return 0.0
    return height_for(w) * (1 - u * u) ** (EXP / 2)


# --- geometry helpers --------------------------------------------------------------------------

def dloft(bm, sections, n=14, mat=0, smooth=True):
    """Loft along X of D-shaped sections (flat bottom on the ground, rounded top). Each section
    is (column, top row, bottom row, height in units, base z); top/bottom are pixel rows whose
    outer edges bound the section."""
    rings = []
    for c, t, b, h, z0 in sections:
        y0, y1 = Y(t - 0.5), Y(b + 0.5)
        yc, w = (y0 + y1) / 2, (y0 - y1) / 2
        ring = []
        for k in range(n):
            a = math.pi * k / (n - 1)
            ring.append(bm.verts.new((X(c), yc + w * math.cos(a), z0 + h * max(math.sin(a), 0.0) ** EXP)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=8, mat=0, smooth=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). A ring of zero
    size collapses to a point."""
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
        rings.append([bm.verts.new(pts[i] + side * (w * PX * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + up * (h * math.sin(2 * math.pi * (k + 0.5) / sides)))
                      for k in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[k])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[k], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


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


# --- the creature ------------------------------------------------------------------------------

def segment(bm, c0, c1, mat, lead=0.94, trail=0.88, steps=5, n=14):
    """One body segment from column c0 to c1, a barrel that follows the profile: full size just
    behind its leading (left) edge and tucked in at its trailing edge, under the next segment."""
    sections = []
    for i in range(steps + 1):
        f = i / steps
        c = c0 + (c1 - c0) * f
        s = lead + (1 - lead) * min(f / 0.15, 1.0) if f < 0.5 else 1 - (1 - trail) * max((f - 0.6) / 0.4, 0.0)
        t, b = profile(c)
        mid, half = (t + b) / 2, (b - t + 1) / 2 * s
        w = half * PX
        sections.append((c, mid - half + 0.5, mid + half - 0.5, height_for(w) * s, 0.0))
    dloft(bm, sections, n=n, mat=mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshe121"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(115, metallic=0.2, roughness=0.45),  # 0 dark red body
        pal(112, metallic=0.1, roughness=0.3),  # 1 near-black mouth and tail cap
        pal(119, metallic=0.1, roughness=0.4, emission_strength=2.0),  # 2 glowing segment rims
        pal(73, metallic=0.1, roughness=0.5),  # 3 pink knobs
        pal(68, metallic=0.1, roughness=0.6),  # 4 brown knob bases, feet
        pal(127, emission_strength=5.0),  # 5 eyes
        pal(121, emission_strength=3.0),  # 6 eye rims, lips, hot streaks
        pal(117, metallic=0.2, roughness=0.45),  # 7 red feeler
        pal(116, metallic=0.2, roughness=0.45),  # 8 lighter red head
    ]
    BODY, DARK, RIM, KNOB, BASE, EYE, HOT, FEELER, HEAD = range(9)
    bm = bmesh.new()

    # Head (columns 8-28): a rounded dome, front tapered to the snout.
    head = []
    for c in (7.6, 8.2, 9.0, 10.0, 12.0, 15.0, 19.0, 23.0, 26.0, 28.0):
        t, b = profile(c)
        w = (b - t + 1) / 2 * PX
        head.append((c, t, b, height_for(w), 0.0))
    dloft(bm, head, n=14, mat=HEAD)

    # Body segments and the glowing rim on each one's leading edge.
    segs = [(26.5, 36.5), (35.5, 49.0), (48.5, 56.8), (56.2, 65.2), (64.6, 73.2), (72.6, 79.8)]
    for c0, c1 in segs:
        segment(bm, c0, c1, BODY)
        t, b = profile(c0 + 0.6)
        mid, half = (t + b) / 2, (b - t + 1) / 2 * 1.015
        w = half * PX
        dloft(bm, [(c0 + 0.1, mid - half + 0.5, mid + half - 0.5, height_for(w), 0.0),
                   (c0 + 2.2, mid - half + 0.5, mid + half - 0.5, height_for(w), 0.0)],
              n=14, mat=RIM)
        # A hot streak down the middle of the rim.
        hw = half * 0.8
        dloft(bm, [(c0 + 0.9, mid - hw + 0.5, mid + hw - 0.5, height_for(w) + 0.012, 0.0),
                   (c0 + 1.5, mid - hw + 0.5, mid + hw - 0.5, height_for(w) + 0.012, 0.0)],
              n=12, mat=HOT)
    # Tail (columns 79-94): a segment narrowing to a dark rounded cap.
    tail = []
    for c in (79.2, 81.0, 83.0, 85.5, 87.5, 89.5, 91.0, 92.5, 93.6):
        t, b = profile(c)
        w = (b - t + 1) / 2 * PX
        tail.append((c, t, b, height_for(w), 0.0))
    dloft(bm, tail[:4], n=14, mat=BODY)
    dloft(bm, tail[3:], n=14, mat=DARK)
    t, b = profile(79.8)
    dloft(bm, [(79.3, t - 0.3, b + 0.3, height_for((b - t + 1.6) / 2 * PX), 0.0),
               (81.2, t - 0.3, b + 0.3, height_for((b - t + 1.6) / 2 * PX), 0.0)], n=14, mat=RIM)

    # Eyes: glowing domes in orange rims (columns 19-26, rows 12-22).
    for c, r, rx, ry in ((22.8, 14.2, 3.0, 2.4), (22.6, 20.5, 3.6, 2.0)):
        z = surface_z(c, r)
        ellipsoid(bm, c, r, z - 0.03, rx + 1.2, ry + 1.0, 0.1, mat=HOT)
        ellipsoid(bm, c, r, z, rx, ry, 0.12, mat=EYE)

    # Mouth: a dark recess under the eyes (columns 11-28, rows 24-31), with a bright lower lip.
    for c, r, rx, ry in ((19.5, 27.6, 8.0, 3.4), (12.5, 27.0, 2.5, 3.0)):
        ellipsoid(bm, c, r, surface_z(c, r) - 0.05, rx, ry, 0.08, mat=DARK, segments=14)
    lip = [(9.2, 21.0), (9.4, 25.0), (10.3, 29.0), (12.3, 32.4), (16.0, 34.2), (20.0, 34.0),
           (23.5, 32.6), (26.0, 30.8)]
    sweep(bm, [(c, r, surface_z(c, r) - 0.03, 1.4, 0.06) for c, r in lip], sides=8, mat=HOT)
    brow = [(10.0, 19.0), (12.5, 17.5), (16.0, 16.8), (19.0, 17.2)]
    sweep(bm, [(c, r, surface_z(c, r) - 0.02, 1.0, 0.04) for c, r in brow], sides=6, mat=HOT)

    # Pink knobs: a collar behind the eyes and one on the back of each segment.
    knobs = [(32.0, 11.9, 3.4, 2.6), (33.1, 18.0, 3.2, 2.6), (30.7, 23.9, 2.8, 1.6),
             (45.1, 13.3, 3.4, 1.8), (54.6, 14.1, 2.8, 1.8), (63.2, 16.1, 2.8, 1.8),
             (70.5, 18.3, 2.4, 1.8), (76.5, 20.0, 1.9, 2.0), (88.4, 21.6, 2.6, 2.6)]
    for c, r, rx, ry in knobs:
        z = surface_z(c, r)
        ellipsoid(bm, c, r, z - 0.02, rx + 0.8, ry + 0.8, 0.06, mat=BASE)
        ellipsoid(bm, c, r, z + 0.02, rx, ry, 0.08, mat=KNOB)
    # Tail stinger curling down from the cap (columns 84-91, rows 24-33).
    sting = [(90.2, 24.0, 1.4), (90.0, 27.0, 1.3), (88.6, 30.0, 1.1), (86.4, 32.2, 0.8), (84.2, 33.4, 0.0)]
    sweep(bm, [(c, r, surface_z(c, r) + 0.0 if w else surface_z(84.6, 33.0), w, w * 0.045)
               for c, r, w in sting], sides=8, mat=KNOB)

    # Feeler: from the chin down and along the belly to the feet (rows 38-51).
    feeler = [(9.0, 37.8, 0.0), (10.0, 39.5, 1.2), (13.0, 43.4, 1.6), (17.0, 46.8, 1.8), (22.0, 48.8, 1.9),
              (28.0, 49.3, 2.0), (34.0, 48.8, 2.0), (42.0, 47.8, 1.6), (50.0, 48.0, 1.4), (56.0, 47.5, 1.4),
              (58.0, 46.5, 0.0)]
    sweep(bm, [(c, r, 0.08, w, w * 0.06) for c, r, w in feeler], sides=8, mat=FEELER)
    # Feet: pink pads on the feeler and under the belly.
    for c, r, rx, ry in ((28.7, 49.0, 2.4, 1.6), (38.5, 47.3, 3.2, 1.5), (60.0, 43.5, 1.6, 2.0)):
        ellipsoid(bm, c, r, 0.12, rx + 1.0, ry + 1.0, 0.08, mat=BASE)
        ellipsoid(bm, c, r, 0.15, rx, ry, 0.1, mat=KNOB)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newshe-121's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshe-121")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The creature's sprite as one image, padded to the 24:28 shape render_preview expects for
    size 8 (96 x 112 px, the creature in the middle)."""
    import numpy as np
    img = np.zeros((112, 96, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 48 - 12, cy + 56 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 96, 112, alpha=True)
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
    print(f"whole creature: {len(obj.data.polygons)} faces")
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
