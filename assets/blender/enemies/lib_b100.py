"""Helpers shared by batch b100's model scripts: the two side towers of the red newshf fortress.

The fortress (levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16) is fourteen 2x2 ground enemies. Its two
upper corners are separate assemblies of four pieces each, mirror images of one another:
assembly-newshf-191 (left: newshf-153, 155, 191, 193) and assembly-newshf-199 (right: newshf-161,
163, 199, 201). Each is a 48 x 56 px block: a rounded drum on the outside, three glowing red rods
in slots that reach up the screen, light ribs between the slots, and below them a body with dark
channels and a rounded hub. The middle of the fortress (assembly-newshf-270) is another batch.

`build_side` builds one corner in its own assembly coordinates, written in the left corner's pixel
grid (column c, row r of the 48 x 56 block); the right corner is the same build mirrored
(column c there is column 48 - c here), with its first rod one row lower.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


def merged_sprite(root, pieces):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, pieces[0])
    for name in pieces[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_grid(root, pieces, x0, y0, w=48, h=56):
    """The assembly's first frames as one grid of palette indices (-1 transparent); (x0, y0) is the
    screen pixel of its top-left corner."""
    grid = [[-1] * w for _ in range(h)]
    for name in pieces:
        data = common.load_sprite(root, name)
        lay = next(e for e in data["assemblyLayout"] if e["model"] == name)
        ox, oy = lay["cx"] - 12 - x0, lay["cy"] - 14 - y0
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[oy + r][ox + c] = v
    return grid


def composite_png(root, pieces, grid, out):
    """The grid as an image (for render_preview with size = width / 12)."""
    import numpy as np
    colors = {}
    for name in pieces:
        colors.update(common.load_sprite(root, name)["colors"])
    h, w = len(grid), len(grid[0])
    img = np.zeros((h, w, 4), dtype=np.float32)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def ring_loft(bm, rings, mats, smooth=True, cap_start=True, cap_end=True, sharp_segments=()):
    """Join rings of 3D points (same length, or one point for a tip). `mats` is a material index
    per band (list) or one for all; a band's entry may also be a list per segment. Caps and the
    bands' `sharp_segments` are flat shaded with sharp edges, so smooth shading stays on the curve."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]

    def mat(band, seg):
        m = mats[band] if isinstance(mats, list) else mats
        return m[seg] if isinstance(m, list) else m

    faces, flat = [], []
    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            face = bm.faces.new(f)
            face.material_index = mat(b, i)
            (flat if i in sharp_segments else faces).append(face)
    if cap_start and len(verts[0]) > 2:
        face = bm.faces.new(list(reversed(verts[0])))
        face.material_index = mat(0, 0)
        flat.append(face)
    if cap_end and len(verts[-1]) > 2:
        face = bm.faces.new(verts[-1])
        face.material_index = mat(len(verts) - 2, 0)
        flat.append(face)
    for f in faces:
        f.smooth = smooth
    for f in flat:
        f.smooth = False
        if smooth:
            for e in f.edges:
                e.smooth = False
    return faces + flat


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


def build_side(name, sprite, grid, mirror):
    """One corner tower in assembly coordinates (origin at the centre of its 48 x 56 block)."""
    coll = common.reset_collection(name)
    tag = name.replace("assembly-", "")
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(65, metallic=0.2, roughness=0.8),  # 0 near-black slots and channels
        pal(67, metallic=0.3, roughness=0.55),  # 1 dark brown drum
        pal(69, metallic=0.3, roughness=0.5),  # 2 brown body plates
        pal(71, metallic=0.3, roughness=0.45),  # 3 lighter plates
        pal(73, metallic=0.35, roughness=0.4),  # 4 ribs
        pal(75, metallic=0.4, roughness=0.35),  # 5 lit rims and hub
        pal(77, metallic=0.4, roughness=0.3),  # 6 brightest rib edges
        pal(113, metallic=0.2, roughness=0.5, emission_strength=0.8),  # 7 rod, dark root
        pal(116, metallic=0.2, roughness=0.45, emission_strength=1.5),  # 8 rod, dull red
        pal(118, metallic=0.1, roughness=0.4, emission_strength=2.5),  # 9 rod, glowing red
        pal(114, metallic=0.2, roughness=0.45, emission_strength=1.0),  # 10 rod, dark far end
        pal(121, emission_strength=3.5),  # 11 orange bands
        pal(124, emission_strength=4.5),  # 12 yellow stripe
        pal(68, metallic=0.3, roughness=0.5),  # 13 hub body, drum's upper side
    ]
    SLOT, DRUM, PLATE, LIGHT, RIB, RIM, EDGE, ROOT, DULL, GLOW, FAR, BAND, STRIPE, HUB = range(len(mats))
    bm = bmesh.new()
    shift = 1 if mirror else 0  # the right corner's first rod and its rim sit one row lower

    def X(c):
        """Left-corner pixel column (centre; fractions allowed) to Blender X."""
        return (((48 - c) if mirror else c) + 0.5 - 24) / 12

    def Y(r):
        return (28 - (r + 0.5)) / 12

    def block(c0, c1, r0, r1, z0, z1, m):
        """A box over pixel columns c0..c1 and rows r0..r1 (inclusive) from z0 to z1."""
        pts = [(X(c0 - 0.5), Y(r0 - 0.5)), (X(c1 + 0.5), Y(r0 - 0.5)),
               (X(c1 + 0.5), Y(r1 + 0.5)), (X(c0 - 0.5), Y(r1 + 0.5))]
        n = len(bm.faces)
        common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=m)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n:]:
            f.smooth = False

    def poly(edges, z0, z1, m):
        n = len(bm.faces)
        common.slab(bm, [(X(c), Y(r)) for c, r in edges], z1 - z0, z=(z0 + z1) / 2, mat_index=m)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n:]:
            f.smooth = False

    # Dark floor of the slots and channels, following the outline's stepped top edge.
    poly([(13.5, 25.5), (13.5, 55.5), (47.5, 55.5), (47.5, 12.5), (34.5, 12.5), (34.5, 18.5),
          (22.5, 18.5), (22.5, 25.5)], 0.0, 0.14, SLOT)

    # The drum on the outside: a quarter round from the outline up to the slot of the first rod.
    rows = [r for r in range(len(grid)) if any(v not in (-1, 1) for v in grid[r][:14])] if not mirror \
        else [r for r in range(len(grid)) if any(v not in (-1, 1) for v in grid[r][35:])]
    top_row = rows[0]

    def outer(r):
        """The drum's outer edge (left-corner terms) in row r, smoothed over the pixel steps."""
        def edge(rr):
            rr = min(max(rr, top_row), len(grid) - 1)
            cols = [c for c in range(len(grid[rr])) if grid[rr][c] not in (-1, 1, 16)]
            return (min(cols) if not mirror else 48 - max(cols)) - 0.5
        return sum(k * edge(r + d) for d, k in zip(range(-2, 3), (1, 2, 3, 2, 1))) / 9

    rings = []
    seg = 8
    z_top = 0.3
    for i, r in enumerate([top_row - 0.4] + list(range(top_row, len(grid))) + [len(grid) - 0.5]):
        rr = min(max(round(r), top_row), len(grid) - 1)
        x_out = outer(rr)
        x_in = 13.5 if rr <= 42 + shift else 11.5
        k = 0.35 if i == 0 else 1.0  # the first ring is a low lip that rounds the drum's top end
        ring = []
        for s in range(seg + 1):
            t = (math.pi / 2) * s / seg
            ring.append((X(x_in - (x_in - x_out) * math.cos(t)), Y(r), z_top * k * math.sin(t)))
        ring.append((X(x_in), Y(r), 0.0))
        rings.append(ring)
    ring_loft(bm, rings, [[DRUM] * 3 + [HUB] * 3 + [RIB, RIB, DRUM, DRUM]] * (len(rings) - 1),
              sharp_segments=(seg, seg + 1))

    # Ribs between the slots (z up to ~0.35) and the outer wall on the far side.
    block(23, 23, 20 + shift, 41 + shift, 0.0, 0.33, RIB)
    block(25, 25, 19, 35, 0.0, 0.35, EDGE)
    block(35, 35, 16, 35, 0.0, 0.33, RIB)
    block(37, 37, 14, 35, 0.0, 0.35, EDGE)
    block(47, 47, 13, 36, 0.0, 0.34, RIB)

    # Lit rims across the foot of each rod.
    block(13, 23, 42 + shift, 42 + shift, 0.0, 0.31, RIM)
    block(23, 35, 36, 36, 0.0, 0.31, RIM)
    block(35, 47, 31, 31, 0.0, 0.31, RIM)

    # Body plates below the rods, with the dark channels (the floor) running down between them.
    block(13, 15, 43 + shift, 55, 0.0, 0.28, DRUM)
    block(21, 23, 43 + shift, 55, 0.0, 0.28, PLATE)
    block(25, 28, 37, 55, 0.0, 0.27, PLATE)
    block(25, 25, 37, 55, 0.0, 0.29, LIGHT)
    block(33, 35, 37, 55, 0.0, 0.28, LIGHT)
    # The hub under the third rod: a block with a rounded, lit drum lying across it.
    block(37, 47, 32, 51, 0.0, 0.26, HUB)
    block(37, 40, 52, 55, 0.0, 0.27, PLATE)
    block(45, 47, 52, 55, 0.0, 0.27, PLATE)
    hub = []
    sides = 12
    for c in (36.6, 37.0, 47.5):
        k = 0.85 if c == 36.6 else 1.0
        ring = []
        for s in range(sides):
            a = 2 * math.pi * (s + 0.5) / sides
            ring.append((X(c), Y(39.2) + 4.6 * PX * k * math.cos(a), 0.2 + 0.14 * k * math.sin(a)))
        hub.append(ring)
    ring_loft(bm, hub, RIM)

    # The three glowing rods: (content columns, top row, bottom row).
    rods = [((15, 21), 12 + shift, 40 + shift), ((27, 33), 6, 34), ((39, 45), 1, 29)]
    sides = 10
    for (c0, c1), rt, rb in rods:
        cc = (c0 + c1) / 2
        hw = (c1 - c0 + 1) / 2 * PX
        hh = 0.11

        def zc(r):
            return 0.30 + 0.10 * (rb - r) / (rb - rt)

        def ring(r, kw=1.0, kh=1.0, dz=0.0):
            pts = []
            for s in range(sides):
                a = 2 * math.pi * (s + 0.5) / sides
                pts.append((X(cc) + hw * kw * math.cos(a), Y(r), zc(r) + dz + hh * kh * math.sin(a)))
            return pts

        L = rb - rt
        sections = [(-0.5, 0.6, 0.45, None), (-0.15, 0.92, 0.85, FAR), (0.4, 1.0, 1.0, FAR),
                    (3.5, 1.0, 1.0, FAR), (16.5, 1.0, 1.0, GLOW), (21.5, 1.0, 1.0, DULL),
                    (L + 0.5, 1.0, 1.0, ROOT)]
        ring_loft(bm, [ring(rt + o, kw, kh) for o, kw, kh, _ in sections], [m for *_, m in sections[1:]])
        # Orange bands round the rod.
        for o in (6, 15):
            ring_loft(bm, [ring(rt + o - 0.5, 1.04, 1.12), ring(rt + o + 0.5, 1.04, 1.12)], BAND)
        # Yellow stripe down its screen-left side.
        sc = c1 if mirror else c0
        dx = abs(X(sc) - X(cc)) / hw
        lift = hh * math.sqrt(max(0.0, 1 - dx * dx)) + 0.012

        def stripe(r, k=1.0):
            x, y, z = X(sc), Y(r), zc(r) + lift
            w, t = 0.5 * PX * k, 0.022 * k
            return [(x - w, y, z - t), (x + w, y, z - t), (x + w, y, z + t), (x - w, y, z + t)]

        ring_loft(bm, [stripe(rt + 4), stripe(rt + 15)], STRIPE, smooth=False)

    return to_object(name, bm, mats, coll)


def main(script_file, name, pieces, x0, y0, mirror):
    """Build, split and export one corner. (x0, y0) is the screen pixel of its block's top-left
    corner; its centre (x0 + 24, y0 + 28) is the Blender origin."""
    root = common.repo_root(script_file)
    sprite = merged_sprite(root, pieces)
    grid = composite_grid(root, pieces, x0, y0)
    obj = build_side(name, sprite, grid, mirror)
    cx0, cy0 = x0 + 24, y0 + 28
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in sprite["assemblyLayout"]
              if e["model"] in pieces]
    split = common.split_assembly(obj, layout)
    for piece in pieces:
        data = common.load_sprite(root, piece)
        common.export_sprite_model(root, [split[piece]], f"enemies/{piece}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, pieces, grid, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([split[piece]], str(out.parent / f"{piece}.png"), img, size=2)
