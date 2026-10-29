"""Golden horned arm (newsh4.shp, assembly of 7 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.3) and episode 3 (level 3.17). Seven 2x2 enemies in a row make one
168x28 px object (sprite.json `assemblyLayout`): a long brass horn that tapers and curls down to a
point at the far left, its plating telescoping at collared joints, held by steel clamps with grille
slats along its top, a cable bay with a lit rail along its underside, raised bands and a grilled
port near its root, a round ball knuckle, a ribbed steel neck and the start of a gripper housing cut
off at the right edge: a brass drum with armour plates, steel frame rails and claws, a band of vent
fins and a heavy end cap ring. Each piece is a single frame.

Remodelled on the concept (assets/blender/features/concepts/assembly-newsh4-231.jpg): each part sits
where the registered concept (assets/blender/textures/assembly-newsh4-231/concept.png) draws it,
within the sprite's outline, so the detail texture_bake.py projects onto it lands on the right part.
The brass is one mid tone; the sprite's lit tops and dark lower halves are the light's work. The
whole arm is built once in assembly coordinates, then cut into the seven pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-231.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b061 as lib  # noqa: E402

NAME = "assembly-newsh4-231"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-231", "newsh4-233", "newsh4-235", "newsh4-267", "newsh4-269", "newsh4-271", "newsh4-273"]
W, H = 168, 28  # assembly size in px; piece i covers columns 24 i .. 24 i + 23
# Assembly pixel edge (0, 0) is the top-left corner of newsh4-231 (screen 98 - 12, 15 - 14). The
# Blender origin is the assembly's centre, which is the centre of newsh4-267 (screen 170, 15).
CX0, CY0 = 170, 15
U = 1 / 12
# The horn, knuckle and segment are round tubes and a ball (the sprite lights their tops and
# shades their lower halves): each is about as tall as it is wide.
ROUND = 0.95


def X(e):
    """Assembly pixel edge coordinate (column c's centre is c + 0.5) to Blender X."""
    return (e - W / 2) * U


def Y(e):
    """Assembly pixel edge coordinate (row r's centre is r + 0.5) to Blender Y (sprite up is +Y)."""
    return (H / 2 - e) * U


def load():
    """The pieces' sprites, their merged colours and the whole arm's pixels as one grid."""
    grid = [[-1] * W for _ in range(H)]
    colors, sprites = {}, {}
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        sprites[name] = data
        colors.update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r][24 * i + c] = v
    return grid, colors, sprites


def horn_profile(grid):
    """For each column of the horn (2..122): (centre row, vertical half width) in pixel edges,
    from the sprite's filled rows, smoothed. Past column 112 the knuckle hangs below the horn, so
    the horn keeps the rows 1-12 it has there."""
    raw = {}
    for c in range(2, 123):
        if c <= 112:
            rows = [r for r in range(H) if grid[r][c] != -1]
            top, bottom = min(rows), max(rows) + 1
        else:
            top, bottom = 1, 13
        raw[c] = (top, bottom)
    prof = {}
    for c in raw:
        near = [raw[k] for k in range(c - 2, c + 3) if k in raw]
        top = sum(t for t, _ in near) / len(near)
        bottom = sum(b for _, b in near) / len(near)
        prof[c] = ((top + bottom) / 2, (bottom - top) / 2)
    return prof


def horn_path(prof):
    """Sections (x, y, z, half_width, half_height) down the horn from its tip to inside the knuckle."""
    path = [(X(2.0), Y(25.9), 0.0, 0.0, 0.0)]
    c = 2.6
    while c < 122:
        k = int(c)
        m, vh = prof[k]
        m1, _ = prof[min(k + 2, 122)]
        m0, _ = prof[max(k - 2, 2)]
        slope = (m1 - m0) / (min(k + 2, 122) - max(k - 2, 2))
        w = vh * math.cos(math.atan(slope)) * U
        h = ROUND * w + 0.004
        path.append((X(c + 0.5), Y(m), 0.0, w, h))
        c += 1.5 if c > 6 else 1.0
    return path


def faces_since(bm, n):
    bm.faces.ensure_lookup_table()
    return bm.faces[n:]


def set_faces(bm, n, mat, smooth):
    for f in faces_since(bm, n):
        f.material_index = mat
        f.smooth = smooth


def prism(bm, outline, z0, z1, mat, bevel=0.0):
    """A hard, flat-topped block from z0 to z1 over an outline of (col, row) pixel edges, its top
    edges chamfered by `bevel` (units)."""
    pts = [(X(c), Y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    n = len(bm.faces)
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    top_face = bm.faces.new(top)
    bm.faces.new(list(reversed(bottom)))
    k = len(pts)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(top_face.edges), offset=bevel, segments=1, affect="EDGES", profile=0.5)
    set_faces(bm, n, mat, False)


def bar(bm, a, b, half_w, z0, z1, mat, bevel=0.0):
    """A straight hard bar from pixel point a to b (col, row), half_w px either side."""
    (ca, ra), (cb, rb) = a, b
    d = math.hypot(cb - ca, rb - ra)
    nc, nr = -(rb - ra) / d * half_w, (cb - ca) / d * half_w
    prism(bm, [(ca + nc, ra + nr), (cb + nc, rb + nr), (cb - nc, rb - nr), (ca - nc, ra - nr)], z0, z1, mat, bevel)


class Tube:
    """A round tube lying along the sprite's columns: centre row m(c), half width w(c) px, and height
    ROUND * w (the tubes are centred on z = 0)."""

    def __init__(self, fn):
        self.fn = fn  # c -> (centre row, half width px)

    def z(self, c, r):
        m, w = self.fn(c)
        t = (r - m) / w
        return ROUND * w * U * math.sqrt(max(0.0, 1 - t * t))

    def wrap(self, bm, c0, c1, r0, r1, lift, mat, sink=0.6, nc=3, na=6, smooth=False):
        """A plate wrapped round the tube's upper side between columns c0..c1 and rows r0..r1 (as
        seen from above), standing `lift` px proud of the surface and sunk `sink` px into it: a
        clamp, band or panel that follows the tube's curve."""
        n = len(bm.faces)
        cols = [c0 + (c1 - c0) * i / nc for i in range(nc + 1)]
        grid_o, grid_i = [], []
        for c in cols:
            m, w = self.fn(c)
            a0 = math.acos(max(-0.995, min(0.995, (m - r0) / w)))
            a1 = math.acos(max(-0.995, min(0.995, (m - r1) / w)))
            ro, ri = [], []
            for j in range(na + 1):
                a = a0 + (a1 - a0) * j / na
                for rad, out in ((w + lift, ro), (w - sink, ri)):
                    out.append(bm.verts.new((X(c), Y(m) + rad * U * math.cos(a), ROUND * rad * U * math.sin(a))))
            grid_o.append(ro)
            grid_i.append(ri)
        for i in range(nc):
            for j in range(na):
                bm.faces.new((grid_o[i][j], grid_o[i + 1][j], grid_o[i + 1][j + 1], grid_o[i][j + 1]))
                bm.faces.new((grid_i[i][j + 1], grid_i[i + 1][j + 1], grid_i[i + 1][j], grid_i[i][j]))
        for i in range(nc):  # the plate's edges along its rows
            for j in (0, na):
                q = (grid_o[i][j], grid_i[i][j], grid_i[i + 1][j], grid_o[i + 1][j])
                bm.faces.new(q if j == 0 else q[::-1])
        for i in (0, nc):  # and its ends
            for j in range(na):
                q = (grid_o[i][j], grid_o[i][j + 1], grid_i[i][j + 1], grid_i[i][j])
                bm.faces.new(q if i == 0 else q[::-1])
        set_faces(bm, n, mat, False)
        if smooth:
            for f in faces_since(bm, n)[: nc * na]:
                f.smooth = True

    def ring(self, bm, c, length, scale, mat, sides=16, smooth=True):
        """A band right round the tube at column c, `length` px long, `scale` times its size."""
        n = len(bm.faces)
        pts = []
        for e in (c, c + length):
            m, w = self.fn(e)
            pts.append((X(e), Y(m), 0.0, w * scale * U, ROUND * w * scale * U))
        lib.sweep(bm, pts, sides=sides, mat_index=mat)
        set_faces(bm, n, mat, smooth)


def to_object(name, bm, mats, coll):
    """A mesh object keeping each face's own smooth or flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# Remodelled on the concept (assets/blender/features/concepts/assembly-newsh4-231.jpg, registered to
# the sprite as assets/blender/textures/assembly-newsh4-231/concept.png): every part sits where the
# concept draws it, inside the sprite's outline (the sprite decides the outline), so the concept
# detail texture_bake.py projects straight down lands on the matching part.
# Telescoping joints of the horn's plating, where the concept draws a collar (columns).
HORN_JOINTS = (9.4, 13.2, 44.6, 63.6, 85.4)
# Raised bands round the horn root (the sprite's bright columns 90, 94 and 104; the concept's panel
# seams at 89, 93 and 103) and the seam where the root meets the elbow.
ROOT_BANDS = (89.3, 93.2, 103.2, 111.0)
# The gripper housing (the thick segment): a round drum, rows 1-22 (centre row 11.5, 10.5 px).
SEG_M, SEG_W = 11.5, 10.5


def seg_fn(c):
    """The gripper drum's (centre row, half width px) at column c: a rounded shoulder from column
    133.3 to 140, full width to the end cap."""
    pts = [(133.3, 2.5), (133.8, 6.0), (134.8, 8.0), (136.2, 9.3), (137.8, 10.1), (139.5, 10.5)]
    if c >= 139.5:
        return SEG_M, SEG_W
    for (a, wa), (b, wb) in zip(pts, pts[1:]):
        if a <= c <= b:
            return SEG_M - 0.5 * (1 - (c - 133.3) / 6.2), wa + (wb - wa) * (c - a) / (b - a)
    return SEG_M - 0.5, 2.5


def build(grid, colors):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nsh4_231", colors)
    gold = lambda i: mats(i, metallic=0.55, roughness=0.35)  # noqa: E731
    steel = lambda i: mats(i, metallic=0.75, roughness=0.32)  # noqa: E731
    # One mid gold for the brass shell (the game's light draws the sprite's lit tops and shaded
    # undersides); a lighter gold for the collars and bands catching the light.
    body, collar = gold(22), gold(25)
    clamp, clamp_hi, dark, slot = steel(5), steel(7), steel(3), mats(1, metallic=0.3, roughness=0.6)
    blue = steel(106)
    bm = bmesh.new()

    # The horn, from its tip curling down at the bottom left up and along to inside the knuckle:
    # one round tube that tapers to a point.
    prof = horn_profile(grid)
    lib.sweep(bm, horn_path(prof), sides=16, mat_index=body)
    set_faces(bm, 0, body, True)

    def horn_fn(c):
        m, vh = prof[max(2, min(122, int(c)))]
        return m, vh

    horn = Tube(horn_fn)
    # Collars at the plating's telescoping joints, and the root's raised bands.
    for c in HORN_JOINTS:
        horn.ring(bm, c - 0.45, 0.9, 1.07, collar)
    for c in ROOT_BANDS:
        horn.ring(bm, c - 0.35, 0.7, 1.05, collar if c < 110 else gold(20))

    # Steel clamps wrapped over the horn's upper side where the concept draws them (cols, rows),
    # the two nearest the root with grille slats across them.
    for c0, c1, r0, r1, mat, slats in ((39.8, 45.0, 7.6, 12.4, clamp, 0), (58.0, 63.2, 5.0, 9.4, clamp, 0),
                                       (80.4, 85.2, 2.6, 8.6, clamp, 4), (107.0, 111.0, 1.4, 5.0, blue, 3)):
        horn.wrap(bm, c0, c1, r0, r1, 0.9, mat)
        for k in range(slats):
            r = r0 + 0.9 + k * (r1 - r0 - 1.8) / max(1, slats - 1)
            horn.wrap(bm, c0 + 0.6, c1 - 0.6, r - 0.25, r + 0.25, 1.5, clamp_hi, sink=0.0, nc=1, na=1)
    # The dark grille port on the root's lower flank (cols 95-99.5, rows 8.4-12.4): a steel frame
    # round a dark recess with slats.
    horn.wrap(bm, 94.8, 99.8, 8.2, 12.6, 0.8, clamp, nc=2, na=4)
    horn.wrap(bm, 95.6, 99.0, 8.9, 11.9, 0.95, slot, sink=0.0, nc=1, na=3)
    for r in (9.6, 10.6, 11.5):
        horn.wrap(bm, 95.8, 98.8, r - 0.2, r + 0.2, 1.2, clamp_hi, sink=0.0, nc=1, na=1)

    # The cable bay under the horn (cols 45-112): a lit rail along the lower flank (row 12) and two
    # dark cables slung along it between the clamps.
    rail = []
    for c in range(46, 113, 3):
        m, vh = horn_fn(c)
        r = min(12.3, m + vh - 0.9)
        rail.append((X(c + 0.5), Y(r), horn.z(c + 0.5, r) * 0.85, 0.6 * U, 0.6 * U))
    n = len(bm.faces)
    lib.sweep(bm, rail, sides=6, mat_index=collar)
    set_faces(bm, n, collar, True)
    for r_off, (ca, cb) in ((-1.2, (64.0, 88.0)), (-1.9, (69.0, 86.0))):
        cable = []
        for i in range(9):
            c = ca + (cb - ca) * i / 8
            m, vh = horn_fn(c)
            r = m + vh + r_off + 0.4 * math.sin(math.pi * i / 8)
            cable.append((X(c), Y(r), horn.z(c, r) + 0.15 * U, 0.35 * U, 0.35 * U))
        n = len(bm.faces)
        lib.sweep(bm, cable, sides=6, mat_index=dark)
        set_faces(bm, n, dark, True)

    # The knuckle: a brass ball joint (columns 114-134, rows 1-19) where the horn's elbow turns
    # down, and its lower lobe hanging to a point at column 126.
    n = len(bm.faces)
    lib.cube_blob(bm, (X(124.5), Y(8.0), 0.0), (9.5 * U, 7.5 * U, 7.6 * U), n=8, mat_index=body)
    lib.cube_blob(bm, (X(125.6), Y(13.2), -0.05), (5.4 * U, 6.2 * U, 4.6 * U), n=6, mat_index=body)
    set_faces(bm, n, body, True)
    # The neck between the ball and the gripper (cols 130-137): a ribbed steel shaft.
    neck = Tube(lambda c: (10.0, 5.6))
    n = len(bm.faces)
    lib.sweep(bm, [(X(129.5), Y(10.0), 0.0, 5.6 * U, ROUND * 5.6 * U), (X(137.0), Y(10.0), 0.0, 5.6 * U,
                                                                         ROUND * 5.6 * U)], sides=16, mat_index=dark)
    set_faces(bm, n, dark, True)
    for c in (131.0, 133.0):
        neck.ring(bm, c, 0.9, 1.12, clamp)

    # The gripper housing: a brass drum (cols 133-160) with a rounded shoulder, a band of vent slots
    # (cols 155-160) and a heavy end cap ring (cols 160-168, cut open at the assembly's edge).
    drum = Tube(seg_fn)
    sections = [133.3, 133.8, 134.8, 136.2, 137.8, 139.5] + [141.5 + 2 * i for i in range(7)] + [155.0]
    n = len(bm.faces)
    lib.sweep(bm, [(X(c), Y(seg_fn(c)[0]), 0.0, seg_fn(c)[1] * U, ROUND * seg_fn(c)[1] * U) for c in sections],
              sides=24, mat_index=body, cap_end=False)
    set_faces(bm, n, body, True)
    n = len(bm.faces)
    lib.sweep(bm, [(X(155.0), Y(SEG_M), 0.0, (SEG_W - 0.7) * U, ROUND * (SEG_W - 0.7) * U),
                   (X(160.0), Y(SEG_M), 0.0, (SEG_W - 0.7) * U, ROUND * (SEG_W - 0.7) * U)],
              sides=24, mat_index=dark, cap_start=False, cap_end=False)
    set_faces(bm, n, dark, True)
    # Vent fins round the band (cols 155.5-159.5): rings standing proud between dark slots.
    for c in (155.6, 157.0, 158.4):
        drum.ring(bm, c, 0.7, 1.0, gold(21), sides=24)
    cap = [(160.0, SEG_W - 0.4), (160.6, SEG_W + 0.0), (163.0, SEG_W + 0.0), (163.6, SEG_W - 0.5),
           (164.3, SEG_W - 0.5), (164.9, SEG_W - 0.1), (168.6, SEG_W - 0.1)]
    n = len(bm.faces)
    lib.sweep(bm, [(X(c), Y(SEG_M), 0.0, w * U, ROUND * w * U) for c, w in cap], sides=24, mat_index=gold(24))
    set_faces(bm, n, gold(24), True)

    # Plating on the drum: an upper and a lower armour plate either side of a riveted strap
    # (cols 141-154), and steel frame rails along its top and bottom edges (rows 1-3, 18-21).
    drum.wrap(bm, 140.6, 154.0, 3.0, 9.2, 0.7, gold(23), nc=4, na=6, smooth=True)
    drum.wrap(bm, 140.6, 154.0, 12.6, 18.4, 0.7, gold(23), nc=4, na=6, smooth=True)
    drum.wrap(bm, 141.8, 152.6, 9.6, 12.2, 1.0, gold(24), nc=3, na=3, smooth=True)
    drum.wrap(bm, 138.6, 157.4, 1.6, 2.8, 1.1, clamp, nc=4, na=2)
    drum.wrap(bm, 138.6, 157.4, 19.2, 20.8, 1.1, clamp, nc=4, na=2)

    # Steel claws gripping the drum's shoulder: an upper hinge bracket (cols 132.5-141, rows 4-7.5)
    # with its pin, a lower claw arm angled down to the bottom rail, and a diagonal strut across
    # the lower plate (cols 150-157).
    def on_drum(pts, lift):
        """(z0, z1) for a hard part over these (col, row) points: from just under the drum's
        surface to `lift` px above its highest point, so it sits on the curve, not beside it."""
        zs = [drum.z(c, r) if c >= 133.3 else 0.0 for c, r in pts]
        return min(zs) - 0.8 * U, max(zs) + lift * U

    def sample(a, b, k=5):
        return [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k + 1)]

    hinge = [(132.6, 4.4), (141.0, 4.0), (141.0, 7.4), (132.6, 7.2)]
    z0, z1 = on_drum(sample((134.0, 4.2), (141.0, 4.2)) + sample((134.0, 7.3), (141.0, 7.3)), 1.4)
    prism(bm, hinge, min(z0, 0.0), z1, clamp, bevel=0.3 * U)
    prism(bm, [(139.2, 4.9), (142.0, 4.9), (142.0, 6.7), (139.2, 6.7)], z1 - 0.1, z1 + 0.8 * U,
          clamp_hi, bevel=0.25 * U)
    for a, b, hw, lift, mat in (((132.8, 13.6), (141.0, 17.6), 1.0, 1.2, clamp),
                                ((141.0, 17.6), (149.0, 18.0), 0.8, 1.0, clamp),
                                ((149.6, 10.4), (157.2, 14.6), 0.7, 1.4, clamp),
                                ((150.2, 2.0), (154.6, 2.0), 0.8, 1.6, clamp_hi)):
        pts = sample(a, b)
        z0, z1 = on_drum([(c, r + d) for c, r in pts for d in (-hw, hw)], lift)
        bar(bm, a, b, hw, z0, z1, mat, bevel=0.2 * U)

    return to_object(NAME, bm, mats.list, coll)


def main():
    grid, colors, sprites = load()
    obj = build(grid, colors)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprites[PIECES[0]]["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites[name]["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = lib.write_png(grid, colors, Path(tempfile.mkdtemp()) / "arm.png", pad_to=(W, W * 14 // 12))
        common.render_preview([obj], str(out), ref, size=W // 12, view_px=840)
        for name in PIECES:
            data = sprites[name]
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
