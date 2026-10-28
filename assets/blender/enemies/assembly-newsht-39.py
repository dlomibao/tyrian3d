"""Red crab boss (newsht.shp, assembly of 12 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.19), 3 and 4. Twelve 2x2 enemies side by side make one 144x56 px
machine (sprite.json `assemblyLayout`): a red body with two dark glass orbs set in U-shaped
frames, a grey visor between them, a grey cannon below, two glowing exhausts on its back, and
two arms that reach out sideways on a beam and hang down to claws with a glowing red eye
(newsht-39 and newsht-49, whose three frames only brighten the eye, so one model covers them:
the eye's materials take each frame's palette colour, palette_material frames=; see eye_materials).

The whole machine is built once in assembly coordinates (left half, mirrored about pixel column
71, which is the sprite's axis), then cut into the twelve pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsht-39.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it; -- --frames <dir>
renders every frame of the two claws to <dir>/<piece>.png).
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

def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, step=None, flat=1.0):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path; the width is measured across the path in the XY plane and the
    height along Z. A ring of zero size collapses to a point (a rounded or pointed end). With
    `step` (px), extra rings are put in between so no two are further apart (so the sprite's
    colours can be painted along it). `flat` < 1 squares the cross-section off (a superellipse:
    a band with a flat top and rounded edges rather than a round tube)."""
    if step:
        dense = [path[0]]
        for a, b in zip(path, path[1:]):
            n = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
            dense += [tuple(p + (q - p) * k / n for p, q in zip(a, b)) for k in range(1, n + 1)]
        path = dense
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
            ca, sa = math.cos(a), math.sin(a)
            ca, sa = math.copysign(abs(ca) ** flat, ca), math.copysign(abs(sa) ** flat, sa)
            ring.append(bm.verts.new(pts[i] + side * (w * PX * ca) + up * (h * sa)))
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


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True, step=None):
    """A loft down the sprite (along Y) centred on column `col`: sections are
    (row, half_width_px, half_height_units, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth, step=step)


# Painted plate tops: {(col, row): (z, mirrored)} of the sprite pixels on top of a flat plate;
# after the build each gets its own small quad, coloured from the sprite (see paint).
DECALS = {}
MIRRORED = [True]  # plates built now are on the left half and get mirrored


def inside(poly, x, y):
    """Point in polygon (even-odd), poly in (col, row) edge coordinates."""
    n, hit = len(poly), False
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def plate(bm, outline, z0, z1, mat=0, smooth=False, paint=True):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges. With `paint`, the
    sprite's pixels on its top are painted on it (the highest plate over a pixel wins)."""
    pts = [(X(c - 0.5), Y(r - 0.5)) for c, r in outline]
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth
    if paint:
        cs = [c for c, _ in outline]
        rs = [r for _, r in outline]
        for pc in range(math.floor(min(cs)), math.ceil(max(cs))):
            for pr in range(math.floor(min(rs)), math.ceil(max(rs))):
                if inside(outline, pc + 0.5, pr + 0.5) and DECALS.get((pc, pr), (-1,))[0] < z1:
                    DECALS[(pc, pr)] = (z1, MIRRORED[0], paint if isinstance(paint, str) else family(SLOT_PAL[mat]))


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


def to_object(name, bm, mats, coll, recalc=True):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# --- colours from the sprite --------------------------------------------------------------------

def family(i):
    """The palette ramp a colour index belongs to: grey, red (the hull) or glow (eye, exhausts)."""
    return "grey" if 1 <= i <= 15 else "red" if 64 <= i <= 79 else "glow" if 112 <= i <= 127 else None


# Each ramp is painted with a few of its shades (for red the five that fit the sprite's pixels
# best; for grey and glow the ones the model has anyway), so each piece keeps few materials.
QUANT = {"red": (66, 68, 69, 71, 74), "grey": (2, 5, 9), "glow": (113, 116, 119, 122, 125)}
SLOT_PAL = []
RED_LIFT = 1  # palette index of each material slot (set by build)


def lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(c)) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.9505
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.089
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))


def quantise(sprite, i):
    """The painted shade for sprite colour i: the nearest (CIE76) of its ramp's QUANT shades."""
    if family(i) == "red" and i < 79:
        i += RED_LIFT  # under the game's light the sprite's shades read a step darker
    li = lab(sprite["colors"][str(i)])
    return min(QUANT[family(i)], key=lambda q: sum((a - b) ** 2 for a, b in zip(li, lab(sprite["colors"][str(q)]))))


def sprite_grid(sprite):
    """The whole machine's sprite (first frames) as palette indices, [row][col], -1 = empty."""
    grid = [[-1] * 144 for _ in range(56)]
    for e in sprite["assemblyLayout"]:
        if e["model"] not in PIECES:
            continue
        frame = common.load_sprite(ROOT, e["model"])["frames"][0]
        x0, y0 = e["cx"] - CX0 + 60, e["cy"] - CY0 + 14
        for r, row in enumerate(frame["pixels"]):
            vals = row.split() if isinstance(row, str) else row
            for c, v in enumerate(vals):
                v = int(v)
                if v >= 0 and 0 <= y0 + r < 56 and 0 <= x0 + c < 144:
                    grid[y0 + r][x0 + c] = v
    return grid


def paint(bm, grid, sprite, slot_of, skip, glass=()):
    """Colour the model from the sprite: every face that looks up takes the (quantised) colour of
    the sprite pixel under its centre, when that pixel is of the face's own ramp (red on red, grey
    on grey), and every painted plate pixel gets its own quad just above the plate's top. Faces
    in `skip` (the claws' animated eye) keep their materials; faces in `glass` (the orbs) keep
    theirs but where the sprite draws their lit spots (its highlight and lower rim)."""
    bm.normal_update()
    marked = bm.faces.layers.int.get("paint")
    for f in bm.faces:
        if f.material_index in skip or f.normal.z <= 0.05:
            continue
        fam = family(SLOT_PAL[f.material_index])
        # Round red parts (smooth faces) keep one even colour so their curvature does the
        # shading: the sprite's baked light and dark would show as blotches on them. Only parts
        # marked `paint` (the bands round the orbs, whose lit edge is the sprite's) are painted.
        if f.smooth and fam == "red" and not (marked and f[marked]):
            continue
        k = 2 if marked and f[marked] else 1  # a wider window on the bands, so they don't blotch
        c = f.calc_center_median()
        pc, pr = math.floor(c.x * 12 + 72), math.floor(28 - c.y * 12)
        if f.material_index in glass:
            lit = sorted(grid[r][c] for r in range(pr - 1, pr + 2) for c in range(pc - 1, pc + 2)
                         if 0 <= r < 56 and 0 <= c < 144 and family(grid[r][c]) == "grey")
            v = lit[len(lit) // 2] if len(lit) >= 5 else 0
            if v >= 6:
                f.material_index = slot_of(9 if v >= 9 else 5)
            continue
        # The median shade of the sprite pixels of the face's own ramp round its centre (not the
        # black outline round every part), so 1 px seams don't break a curved face into dashes.
        near = sorted(quantise(sprite, grid[r][c]) for r in range(pr - k, pr + k + 1) for c in range(pc - k, pc + k + 1)
                      if 0 <= r < 56 and 0 <= c < 144 and grid[r][c] > 1 and family(grid[r][c]) == fam)
        if len(near) >= 3:
            f.material_index = slot_of(near[len(near) // 2])
    tops = {}
    for (pc, pr), (z, mirrored, fam) in DECALS.items():
        for cc in ((pc, 2 * AXIS_COL - pc) if mirrored else (pc,)):
            if tops.get((cc, pr), (-1,))[0] < z:
                tops[(cc, pr)] = (z, fam)
    lift = 0.6 * PX + 0.006  # above the fattened plate top
    for (pc, pr), (z, fam) in tops.items():
        v = grid[pr][pc] if 0 <= pr < 56 and 0 <= pc < 144 else -1
        if v < 0 or family(v) != fam:
            continue
        x0, x1, y0, y1 = X(pc - 0.5), X(pc + 0.5), Y(pr + 0.5), Y(pr - 0.5)
        vs = [bm.verts.new((x, y, z + lift)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        f = bm.faces.new(vs)
        f.material_index = slot_of(quantise(sprite, v))
        f.smooth = False
    if marked:
        bm.faces.layers.int.remove(marked)
    bm.normal_update()


# --- the machine -------------------------------------------------------------------------------

def ring(bm, col, row, z, radius_px, tube_px, tube_h, mat=0, n=16):
    """A torus lying flat (a raised rim) round (col, row), as a closed sweep."""
    path = []
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        path.append((col + radius_px * math.cos(a), row + radius_px * math.sin(a), z, tube_px, tube_h))
    sweep(bm, path, sides=6, mat=mat, cap_start=False, cap_end=False)


def round_loft(col, sections, z, k=1.0):
    """Sections (row, half_width_px) of a round loft: each ring as tall as it is wide (times k)."""
    return [(r, w, w * PX * k, z) for r, w in sections]


def fatten(bm, d):
    """Grow every solid outward by d units (an even offset along the vertex normals), so the
    sprite's 1 px edge pixels are covered from above."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    moves = [(v, v.normal * d * min(2.0, v.calc_shell_factor())) for v in bm.verts if v.link_faces]
    for v, off in moves:
        v.co += off


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    DECALS.clear()
    MIRRORED[0] = True
    tag = "nsht39"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(71, metallic=0.05, roughness=0.5),  # 0 red hull
        pal(69, metallic=0.05, roughness=0.55),  # 1 darker red plates
        pal(66, metallic=0.2, roughness=0.6),  # 2 deep red bands and grooves
        pal(74, metallic=0.05, roughness=0.4),  # 3 light red ribs
        pal(4, metallic=0.3, roughness=0.12),  # 4 dark glass orbs: glossy, so the light's highlight shows
        pal(5, metallic=0.7, roughness=0.35),  # 5 grey pipes and canisters
        pal(2, metallic=0.2, roughness=0.8),  # 6 dark recesses
        pal(9, metallic=0.8, roughness=0.25),  # 7 bright grey rims
        pal(119, emission_strength=3.0),  # 8 eye glow (animated on the claw pieces)
        pal(125, emission_strength=5.0),  # 9 eye core (animated on the claw pieces)
        pal(113, metallic=0.2, roughness=0.5),  # 10 eye socket
        pal(7, metallic=0.75, roughness=0.25),  # 11 bright grey visor
        pal(116, emission_strength=3.0),  # 12 exhaust bed (now painted from the sprite; kept so slots stay put)
        pal(122, emission_strength=5.0),  # 13 exhaust streaks: orange
    ]
    HULL, PLATE, BAND, RIB, ORB, PIPE, DARK, RIM, GLOW, HOT, SOCKET, VISOR, VENT, STREAK = range(14)
    EYE = {GLOW, HOT, SOCKET}  # animated per frame on the claw pieces (eye_materials): never painted
    KEEP = EYE
    mats[ORB].metallic, mats[ORB].roughness = 0.3, 0.12  # the viewport (preview) gloss too
    SLOT_PAL[:] = [int(m.name.split("_")[1]) for m in mats]

    def slot_of(i):
        """The slot of palette colour i for painting (added on first use)."""
        for k, m in enumerate(mats):
            if SLOT_PAL[k] == i and k not in EYE:
                return k
        same = next((m for k, m in enumerate(mats) if SLOT_PAL[k] == i), None)
        if same is None:
            fam = family(i)
            same = (pal(i, emission_strength=2.5 if i < 120 else 5.0) if fam == "glow" else
                    pal(i, metallic=0.5, roughness=0.35) if fam == "grey" else
                    pal(i, metallic=0.05, roughness=0.55))
        mats.append(same)
        SLOT_PAL.append(i)
        return len(mats) - 1

    bm = bmesh.new()
    PAINT = bm.faces.layers.int.new("paint")

    # Heights (px above z = 0): the hull plates stand about 5 px, the frames round the orbs about
    # 8, the orbs are spheres about 12 px tall, the arms round about 10-11 px, the claws about 8.

    # ---- left half (mirrored below) ----

    # Arm: a round beam out of the shoulder, bending down into a thick upper arm (columns 4-15).
    ARM_Z = 0.44
    arm = round_loft(9.5, [(19.7, 1.5), (20.3, 3.0), (21.2, 4.2), (22.5, 5.2), (24.0, 5.9), (34.6, 5.9),
                           (35.4, 6.2), (38.4, 6.2), (39.4, 4.4)], ARM_Z, k=0.95)
    # The upper arm is as wide as the sprite's (columns 3-16) but keeps its height.
    arm[4:6] = [(r, 6.45, h, z) for r, _, h, z in arm[4:6]]
    arm[-2] = (38.4, 6.2, 5.9 * PX * 0.9, 0.40)
    arm[-1] = (39.9, 5.0, 4.4 * PX * 0.9, 0.34)  # the cuff is wide at its bottom edge
    loft_y(bm, 9.5, arm, sides=16, mat=HULL, step=2.0)
    # Ribs down the upper arm (on its round top) and a dark band at its cuff.
    for dc in (-2.6, 0.0, 2.6):
        zr = ARM_Z + 5.9 * PX * 0.95 * math.sqrt(1 - (dc / 5.9) ** 2)
        loft_y(bm, 9.5 + dc, [(23.5, 0.0, 0.0, zr), (24.5, 0.7, 0.05, zr), (34.0, 0.7, 0.05, zr), (34.8, 0.0, 0.0, zr)],
               sides=6, mat=RIB)
    loft_y(bm, 9.5, [(34.7, 6.15, 5.75 * PX * 0.95 + 0.012, ARM_Z), (35.3, 6.35, 5.95 * PX * 0.95 + 0.012, ARM_Z)],
           sides=16, mat=BAND)

    # Forearm and claw (columns 8-21, rows 39-53): a pod about 8 px tall, dipping where the eye
    # looks out of its top; the eye sits in a raised dark socket rim with its glow sunk inside.
    CLAW_Z = 0.2
    loft_y(bm, 13.4, [(39.0, 3.5, 0.25, CLAW_Z), (40.0, 5.0, 0.36, CLAW_Z), (41.5, 6.0, 0.43, CLAW_Z),
                      (44.0, 6.3, 0.44, CLAW_Z), (45.3, 6.5, 0.22, CLAW_Z), (49.2, 6.5, 0.22, CLAW_Z),
                      (51.0, 5.6, 0.33, CLAW_Z), (52.4, 4.0, 0.25, CLAW_Z), (53.3, 1.8, 0.1, CLAW_Z)],
           sides=16, mat=HULL)
    loft_y(bm, 18.9, [(39.6, 0.0, 0.0, 0.22), (40.4, 1.1, 0.28, 0.22), (49.5, 1.2, 0.28, 0.22),
                      (50.6, 0.0, 0.0, 0.22)], sides=8, mat=PLATE)  # rib down its outer side
    sweep(bm, [(6.6, 47.5, 0.27, 0.0, 0.0), (7.0, 47.5, 0.27, 1.0, 0.1), (10.5, 47.5, 0.27, 1.0, 0.1)],
          sides=8, mat=PIPE)  # grey stub out of its outer side

    # Grey works behind the top of the upper arm: a round ringed canister and a box (rows 10-19).
    CAN = [(10.8, 0.0), (11.3, 1.8), (12.0, 2.3), (12.7, 2.3), (13.0, 1.8), (13.4, 2.3), (14.7, 2.3),
           (15.0, 1.8), (15.4, 2.3), (20.0, 2.3)]
    loft_y(bm, 10.6, round_loft(10.6, CAN, 0.34), sides=10, mat=PIPE)
    plate(bm, [(13, 10.4), (17.4, 10.4), (19.5, 12.5), (19.5, 20), (15, 20), (15, 13), (13, 13)], 0.0, 0.48, mat=PIPE)
    plate(bm, [(16, 16.5), (19.5, 16.5), (19.5, 19.5), (16, 19.5)], 0.48, 0.53, mat=RIM)
    sweep(bm, [(19.5, 18.0, 0.36, 1.2, 0.1), (25.5, 18.0, 0.36, 1.2, 0.1)], sides=8, mat=PIPE)
    # Round dark hose down the inside of the upper arm (rows 24-36).
    sweep(bm, [(21.8, 24.2, 0.3, 2.0, 0.17), (20.4, 26.5, 0.3, 2.0, 0.17), (18.9, 29.0, 0.28, 2.0, 0.17),
               (17.7, 31.5, 0.26, 2.0, 0.17), (17.1, 34.5, 0.24, 1.9, 0.16), (17.2, 36.4, 0.22, 1.7, 0.14), (17.8, 38.2, 0.2, 1.5, 0.12)],
          sides=10, mat=PIPE)

    # The round beam from the shoulder out to the arm (rows 20-22).
    sweep(bm, [(12.0, 22.0, 0.5, 2.4, 0.15), (42.5, 22.0, 0.5, 2.4, 0.15)], sides=10, mat=HULL)

    # Shoulder block (columns 26-42, rows 14-23), 6 px tall with ribs on top, a claw hanging under it.
    plate(bm, [(25.2, 14.5), (26.2, 13.2), (38, 13.2), (39, 15), (39, 17), (42, 17), (42.5, 24), (27, 24), (26, 23)],
          0.0, 0.40, mat=HULL)
    for c in (26.6, 28.6, 30.6, 32.6):
        plate(bm, [(c, 14.6), (c + 1, 14.6), (c + 1, 19.6), (c, 19.6)], 0.40, 0.46, mat=RIB)
    # Diagonal brace from the beam up to the hose (the light ridge from column 30, row 20 to 37, 15).
    sweep(bm, [(29.0, 20.8, 0.44, 1.2, 0.06), (37.8, 14.6, 0.44, 1.2, 0.06)], sides=8, mat=RIB)
    # A strut hanging under the shoulder (columns 27-29, rows 23-29): a 3 px round post with a
    # flat foot across its end (columns 26-31, rows 29-30).
    loft_y(bm, 28.6, [(22.5, 2.3, 1.5 * PX, 0.22), (29.0, 2.3, 1.5 * PX, 0.22)], sides=8, mat=PLATE)
    plate(bm, [(26.5, 28.5), (32.2, 28.5), (32.2, 31), (26.5, 31)], 0.0, 0.3, mat=PLATE)
    # Bracket under the cheek (columns 43-48, rows 24-31): a post, a foot and a dark floor.
    loft_y(bm, 44.0, round_loft(44.0, [(23.5, 1.0), (30.5, 1.0)], 0.2), sides=6, mat=PLATE)
    plate(bm, [(43, 24), (45, 24), (45, 31), (43, 31)], 0.0, 0.22, mat=PLATE)
    plate(bm, [(45, 29.5), (48.5, 29.5), (48.5, 31), (45, 31)], 0.0, 0.22, mat=PLATE)
    plate(bm, [(45, 24), (48.5, 24), (48.5, 29.5), (45, 29.5)], 0.0, 0.06, mat=DARK)

    # Thick round grey hose from the back of the body down to the shoulder (rows 6-13).
    sweep(bm, [(44.0, 7.9, 0.42, 2.5, 2.6 * PX), (40.2, 9.0, 0.42, 3.4, 3.0 * PX), (36.8, 10.8, 0.41, 3.4, 3.0 * PX),
               (35.0, 12.8, 0.4, 3.0, 2.8 * PX), (35.0, 14.4, 0.38, 2.4, 2.4 * PX)], sides=12, mat=PIPE)

    # Upper band across the back of the body (rows 9-12), round, rounded at its outer end.
    sweep(bm, [(40.6, 11.0, 0.27, 0.0, 0.0), (41.2, 11.0, 0.27, 1.6, 1.6 * PX), (42.3, 11.0, 0.27, 2.4, 2.4 * PX),
               (44.0, 11.0, 0.27, 2.6, 2.6 * PX), (63.5, 11.0, 0.27, 2.6, 2.6 * PX)], sides=10, mat=HULL,
          step=2.0)
    # Cheek plate between the band and the orb's frame (columns 39-62, rows 13-24), 5 px tall,
    # with a stepped plate on its outer half.
    plate(bm, [(39, 13), (63, 13), (63, 25), (53, 25), (51.5, 26), (43, 26), (39, 22)], 0.0, 0.29, mat=PLATE)
    plate(bm, [(40, 13.5), (48, 13.5), (48, 22), (43.5, 24.5), (40, 21.5)], 0.29, 0.40, mat=HULL)

    # Frame round the orb, a band standing proud of the cheek: from the middle over the top
    # of the orb, down its outer side, round the bottom and up the inner strut.
    FRAME = [(64.5, 14.6, 1.8), (60.0, 14.8, 2.0), (55.5, 15.8, 2.3), (51.8, 18.6, 2.6), (49.6, 23.0, 2.9),
             (49.1, 28.0, 3.1), (50.0, 33.5, 4.0), (51.6, 35.6, 4.2), (54.0, 37.1, 4.2), (58.0, 37.4, 4.1), (62.0, 36.9, 3.9),
             (65.0, 33.5, 3.1), (65.9, 29.0, 2.7), (65.9, 24.4, 2.3)]
    # A band about 5 px tall (the sprite's lit-edged C), not a full round tube, so the orb
    # stands clear above it.
    # Its cross-section is a superellipse: a flat top about 5 px up with rounded edges.
    n0 = len(bm.faces)
    sweep(bm, [(c, r, 0.15, w, 0.24) for c, r, w in FRAME], sides=12, mat=HULL, step=1.5, flat=0.5)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f[PAINT] = 1
    # The dark glass orb (columns 54-64, rows 17-27): a sphere about 12 px tall.
    ellipsoid(bm, 59.3, 22.4, 0.42, 5.6, 5.6, 0.54, mat=ORB, segments=18, rings=10)
    # The grey lip under it (rows 30-33).
    sweep(bm, [(51.8, 31.6, 0.25, 0.0, 0.0), (52.4, 31.6, 0.25, 1.5, 1.5 * PX), (60.6, 31.6, 0.25, 1.5, 1.5 * PX),
               (61.2, 31.6, 0.25, 0.0, 0.0)], sides=8, mat=PIPE)
    # Dark recess behind the orb and the visor, well below the plates and frames round it.
    plate(bm, [(50, 12.5), (AXIS_COL + 0.5, 12.5), (AXIS_COL + 0.5, 36), (50, 36)], 0.0, 0.12, mat=DARK)

    # Exhaust on the back, slanting out (columns 54-66, rows 1-8): a dark red glowing bed sunk
    # between the spine and the lip in front of it, with orange streaks down it.
    # The housing is hull red; its glowing bed (the sprite's pixels, painted) sits about a pixel
    # below the lip in front of it and the spine beside it.
    plate(bm, [(60.5, 1.3), (67.4, 1.3), (67.4, 4.0), (62.3, 8.5), (53.5, 8.5)], 0.0, 0.34, mat=HULL, paint="glow")
    plate(bm, [(59, 8.2), (68, 8.2), (68, 10), (58, 10)], 0.0, 0.42, mat=BAND)

    mirror_all(bm)
    MIRRORED[0] = False

    # The claws' eyes (built per side: the right claw's eye sits about 1.5 px further in than a
    # mirror image of the left's): a raised dark rim round a socket sunk about 2 px into the pod,
    # the glow at its floor and a hot core on the glow.
    for col, hot in ((13.5, 13.1), (127.2, 127.4)):
        ring(bm, col, 47.1, 0.56, 2.9, 0.8, 0.15, mat=SOCKET)  # rim top about 2.5 px above the lens
        ellipsoid(bm, col, 47.1, 0.43, 2.3, 2.2, 0.03, mat=GLOW)
        ellipsoid(bm, hot, 46.6, 0.45, 0.8, 0.8, 0.025, mat=HOT)

    # ---- centre parts (symmetric about the axis) ----

    # Raised spine between the exhausts (columns 62-81, rows 4-12), about 7 px, with a plate on top.
    loft_y(bm, AXIS_COL, [(3.8, 2.5, 0.1, 0.25), (4.6, 3.6, 0.2, 0.25), (6.0, 8.5, 0.3, 0.25),
                          (8.0, 10.0, 0.32, 0.23), (12.0, 10.5, 0.32, 0.21), (12.8, 9.0, 0.22, 0.19)],
           sides=12, mat=HULL)
    loft_y(bm, AXIS_COL, [(4.8, 0.0, 0.0, 0.54), (5.6, 3.6, 0.06, 0.54), (11.7, 3.8, 0.06, 0.53),
                          (12.3, 0.0, 0.0, 0.53)], sides=8, mat=PLATE)
    # Round grey visor between the orbs (columns 65-77, rows 16-18; the sprite's rows 13-15 above
    # it are the dark slot), on a grey bracket above the dark recess.
    sweep(bm, [(63.8, 17.2, 0.48, 0.0, 0.0), (64.6, 17.2, 0.48, 1.7, 0.17), (78.4, 17.2, 0.48, 1.7, 0.17),
               (79.2, 17.2, 0.48, 0.0, 0.0)], sides=10, mat=VISOR)
    plate(bm, [(68, 19.5), (75, 19.5), (75, 24), (68, 24)], 0.0, 0.35, mat=PIPE)
    # Round cannon pointing down the screen between the frames (columns 68-74, rows 28-34).
    loft_y(bm, AXIS_COL, round_loft(AXIS_COL, [(28.0, 3.0), (33.6, 3.2)], 0.3), sides=12, mat=PIPE)
    loft_y(bm, AXIS_COL, [(33.5, 3.4, 0.29, 0.3), (34.6, 3.5, 0.29, 0.3), (34.8, 2.2, 0.18, 0.3)],
           sides=12, mat=RIM)

    fatten(bm, 0.6 * PX)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    paint(bm, grid, sprite, slot_of, KEEP, glass={ORB})
    return to_object(NAME, bm, mats, coll, recalc=False)


def eye_materials(piece, sprite):
    """Animate the claw's eye on a claw piece (newsht-39 or newsht-49). The eye brightens: on
    newsht-39 frames 39 -> 77 -> 79, on newsht-49 (its mirror image) 49 -> 87 -> 85; its glow, hot
    core and socket rise a few palette steps. In the claw pieces the glow, hot and socket slots
    hold nothing but the eye, so the piece's own copies of those slots get animated materials
    (the other pieces, whose exhausts share the glow and hot materials, keep them as they are)."""
    tag = "nsht39_eye"
    slots = {
        8: common.palette_material(sprite, 119, tag, emission_strength=3.0,
                                   frames={77: 122, 79: 125, 85: 125, 87: 122}),  # GLOW
        9: common.palette_material(sprite, 125, tag, emission_strength=5.0,
                                   frames={77: 126, 79: 127, 85: 127, 87: 126}),  # HOT
        10: common.palette_material(sprite, 113, tag, metallic=0.2, roughness=0.5,
                                    frames={77: 114, 79: 116, 85: 116, 87: 114}),  # SOCKET
    }
    for slot, mat in slots.items():
        piece.data.materials[slot] = mat


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
    obj = build(sprite, sprite_grid(sprite))
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in ("newsht-39", "newsht-49"):
        eye_materials(pieces[name], sprite)
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
    if "--frames" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for name in ("newsht-39", "newsht-49"):
            common.render_frame_previews([pieces[name]], str(out / f"{name}.png"), common.load_sprite(ROOT, name), ROOT)


if __name__ == "__main__":
    main()
