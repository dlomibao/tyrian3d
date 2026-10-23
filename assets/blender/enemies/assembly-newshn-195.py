"""Mouth boss (newshn.shp, assembly of 17 pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Seventeen 2x2 enemies side by side make one 120 x 95 px organic
head (sprite.json `assemblyLayout`; the top row is cut off by the screen edge, the boss carries
on above it): a dark blue-grey biomechanical skull with a lumpy purple brain on top, three
glowing red eyes down each side, tentacles hanging off its flanks, purple claws low on each
side and a bony chin spike. Most of the face is a huge round mouth: a ring of pink gums with
bone fangs pointing inward, and a throat of dark red ridges sinking to a glowing core.

The animated pieces (newshn-119, -121, -157, -159) only light up the core in the throat, so each
keeps one model for all its frames.

The whole head is built once in assembly coordinates and cut into the pieces with
common.split_assembly. The head is a shell in polar rings round the mouth: from the outline in
to the gums, over the gums and down the throat to the core; its faces take the palette colour
of the sprite pixel under them, so the biomechanical texture, gums and throat ridges follow the
sprite. Brain, eyes, fangs, tentacles, claws and chin spike are modelled on top.

Run: blender --background --python assets/blender/enemies/assembly-newshn-195.py [-- --preview out.png]
(the preview is the whole head; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b024 as lib  # noqa: E402

NAME = "assembly-newshn-195"
ROOT = common.repo_root(__file__)
TAG = "nshn195"
PIECES = ["newshn-77", "newshn-79", "newshn-81", "newshn-83",
          "newshn-115", "newshn-117", "newshn-119", "newshn-121", "newshn-123",
          "newshn-153", "newshn-155", "newshn-157", "newshn-159", "newshn-161",
          "newshn-193", "newshn-195", "newshn-197"]
# Assembly pixel (0, 0) is screen (113, -31): the top-left corner of newshn-77. The head is mirror
# symmetric about pixel column 63 (screen x 176.5), which is Blender X = 0; pixel row 47.5
# (screen y 17) is Blender Y = 0.
SX0, SY0 = 113, -31
AXIS = 63
ROW0 = 47.5


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c - AXIS) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (ROW0 - r) / 12


def to_px(x, y):
    return x * 12 + AXIS, ROW0 - y * 12


PX = 1 / 12

# --- outlines (assembly pixel centres, left half from the top down; mirrored about AXIS) -------

# The head without its tentacles, claws and chin spike; it runs on above the top of the sprite.
OUT_LEFT = [(63, -8), (13, -8), (13, 12), (15.5, 14), (14.3, 17), (14.3, 20.5), (16, 22.5), (15.5, 24.5),
            (13.8, 27), (12, 30), (10, 32), (9, 34), (9, 40), (9.5, 43.5), (13, 45), (17, 46.5),
            (20, 48.3), (24, 50), (25.2, 52), (25.5, 54.5), (27.2, 57.2), (29.5, 59.5), (30.2, 62),
            (29.5, 65), (28.5, 68), (27.6, 71), (27.6, 74), (29, 76.5), (32, 78.5), (34, 80.5),
            (35.2, 83), (36, 86), (37.6, 88.3), (39.5, 90.3), (42.5, 91.8), (52, 92), (56, 91),
            (60, 90.5)]
# Outer and inner edge of the gums.
GUM_OUT_LEFT = [(63, 35), (52, 35), (49, 36.8), (46, 38.8), (42, 41.5), (38.5, 44.2), (36.2, 47), (35.2, 50),
                (35.5, 56), (37.5, 58.5), (38.6, 61), (38.8, 64), (41, 66.5), (43.5, 68.2), (44.5, 71),
                (44.6, 74.5), (45, 77.5), (45.8, 80.8), (48.2, 82.3), (50.5, 83.6), (54, 84.6), (57.5, 85.2)]
GUM_IN_LEFT = [(63, 40.6), (52, 40.6), (48.5, 42.6), (46.2, 45), (44.3, 47.3), (43.2, 50.5), (43.4, 53.5),
               (44, 57.5), (46.2, 60), (47.6, 63), (47.6, 67), (47.2, 71.5), (48.2, 75), (50.8, 78.6),
               (54, 80.8), (58, 82.2)]
CENTRE = (63.0, 60.0)  # the polar rings' centre: the middle of the mouth
CORE = (63.0, 56.0)  # the glowing core deep in the throat

# Palette families: the shell's faces take the sprite's colour, snapped to these shades.
FAMILIES = {
    "blue": [96, 97, 99, 101, 103, 105, 107],
    "gum": [65, 66, 69, 72, 75],
    "red": [112, 113, 114, 117, 120],
    "purple": [82, 83, 87, 90],
    "tooth": [19, 163, 169],
}
FAMILY_OF = {rep: fam for fam, reps in FAMILIES.items() for rep in reps}
DARK = {"blue": 96, "gum": 65, "red": 112, "purple": 82, "tooth": 163}


def rep_of(idx, context):
    """The shade (palette index) a sprite pixel stands for; outline black depends on where it is."""
    if idx < 0:
        return None
    if idx <= 4 or idx == 48:
        return DARK[context]
    for lo, hi, rep in ((16, 27, 19), (64, 65, 65), (66, 67, 66), (68, 70, 69), (71, 73, 72), (74, 77, 75),
                        (80, 82, 82), (83, 84, 83), (85, 88, 87), (89, 93, 90),
                        (96, 96, 96), (97, 97, 97), (98, 99, 99), (100, 101, 101), (102, 103, 103),
                        (104, 106, 105), (107, 111, 107), (255, 255, 107),
                        (112, 112, 112), (113, 113, 113), (114, 115, 114), (116, 118, 117), (119, 127, 120),
                        (160, 165, 163), (166, 174, 169)):
        if lo <= idx <= hi:
            return rep
    return None


class Palette:
    """Material slots by palette index, made on first use."""

    STYLE = {"blue": (0.3, 0.5), "gum": (0.05, 0.55), "red": (0.0, 0.7), "purple": (0.15, 0.55),
             "tooth": (0.1, 0.35)}

    def __init__(self, sprite):
        self.sprite = sprite
        self.mats = []
        self.slots = {}

    def __call__(self, idx, emission=0.0):
        if idx not in self.slots:
            fam = FAMILY_OF.get(idx, "blue")
            metallic, rough = self.STYLE[fam]
            if idx == 120:
                emission = emission or 2.5
            self.slots[idx] = len(self.mats)
            self.mats.append(common.palette_material(self.sprite, idx, TAG, metallic=metallic, roughness=rough,
                                                     emission_strength=emission))
        return self.slots[idx]


def load_grid():
    """The whole assembly's pixels (each piece's frame as laid out) as {(col, row): index}."""
    lay = common.load_sprite(ROOT, PIECES[0])["assemblyLayout"]
    grid = {}
    for e in lay:
        data = common.load_sprite(ROOT, e["model"])
        num = int(e["frame"].split("|")[2])
        frame = next(f for f in data["frames"] if f["index"] == num)
        x0, y0 = e["cx"] - 12 - SX0, e["cy"] - 14 - SY0
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[(x0 + c, y0 + r)] = v
    return grid


class Painter:
    def __init__(self, grid, pal):
        self.grid, self.pal = grid, pal

    def pixel(self, x, y):
        c, r = to_px(x, y)
        return self.grid.get((math.floor(c + 0.5), math.floor(r + 0.5)), -1)

    def relief(self, c, r):
        """Height offset from the sprite's shading round a point: its light ribs and knobs stand
        up, its dark gaps and sockets sink (a soft 5x5 average, so it follows forms, not pixels)."""
        total = wsum = 0.0
        c0, r0 = math.floor(c + 0.5), math.floor(r + 0.5)
        for dc in (-2, -1, 0, 1, 2):
            for dr in (-2, -1, 0, 1, 2):
                rep = rep_of(self.grid.get((c0 + dc, r0 + dr), -1), "blue")
                if rep is None:
                    continue
                w = math.exp(-((c0 + dc - c) ** 2 + (r0 + dr - r) ** 2) / 3.0)
                total += w * (FAMILIES["blue"].index(rep) if FAMILY_OF[rep] == "blue" else 2.5)
                wsum += w
        return max(-0.06, min(0.06, (total / wsum - 2.3) * 0.028)) if wsum else 0.0

    def paint(self, faces, context, default=None, min_nz=None):
        """Give each face the shade of the sprite pixels under it (a vote over a few points)."""
        for f in faces:
            if min_nz is not None:
                f.normal_update()
                if f.normal.z < min_nz:
                    continue
            cen = f.calc_center_median()
            reps = [rep_of(self.pixel(p.x, p.y), context)
                    for p in [cen] + [cen.lerp(v.co, 0.55) for v in f.verts]]
            reps = [r for r in reps if r is not None]
            if context == "gum" and any(r != DARK["gum"] for r in reps):
                reps = [r for r in reps if r != DARK["gum"]]  # the gums' dark cracks are teeth roots
            if not reps:
                if default is not None:
                    f.material_index = self.pal(default)
                continue
            fams = [FAMILY_OF[r] for r in reps]
            fam = max(set(fams), key=lambda k: (fams.count(k), k == context))
            order = FAMILIES[fam]
            pos = sum(order.index(r) for r in reps if FAMILY_OF[r] == fam) / fams.count(fam)
            f.material_index = self.pal(order[round(pos)])


# --- the shell -----------------------------------------------------------------------------------

def ring_points(poly_a, poly_b, t, n):
    """n points between two outlines (lerp t) along rays from CENTRE."""
    pts = []
    for j in range(n):
        th = 2 * math.pi * (j + 0.5) / n
        d = (math.cos(th), math.sin(th))
        ra, rb = lib.ray_radius(poly_a, CENTRE, th), lib.ray_radius(poly_b, CENTRE, th)
        rr = ra + (rb - ra) * t
        pts.append((CENTRE[0] + d[0] * rr, CENTRE[1] + d[1] * rr))
    return pts


def connect(bm, a, b):
    """Faces between two rings of verts (same count, or a twice as many as b)."""
    faces = []
    if len(b) == 1:
        for j in range(len(a)):
            faces.append(bm.faces.new((a[j], a[(j + 1) % len(a)], b[0])))
    elif len(a) == len(b):
        n = len(a)
        for j in range(n):
            faces.append(bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j])))
    else:
        n = len(b)
        for k in range(n):
            faces.append(bm.faces.new((a[2 * k], a[2 * k + 1], b[k])))
            faces.append(bm.faces.new((a[2 * k + 1], a[(2 * k + 2) % (2 * n)], b[(k + 1) % n], b[k])))
    return faces


def rim(d, depth=6.0):
    """0 at the outline, rising like a quarter ellipse to 1 at `depth` px in."""
    d = min(max(d, 0.0), depth) / depth
    return math.sqrt(max(0.0, 1 - (1 - d) ** 2))


def build_shell(bm, painter):
    out = lib.mirror_poly(OUT_LEFT, AXIS)
    gum_out = lib.mirror_poly(GUM_OUT_LEFT, AXIS)
    gum_in = lib.mirror_poly(GUM_IN_LEFT, AXIS)
    N, M, K = 256, 128, 64  # ring resolution: skin, gums, throat
    edge_z = -0.03

    def verts(pts, zs):
        return [bm.verts.new((X(c), Y(r), z)) for (c, r), z in zip(pts, zs)]

    def dome(c, r):
        """The skull's height away from its rim: highest round the brain and over the cheeks."""
        top = 0.24 + 0.06 * math.exp(-((c - AXIS) ** 2 / 500 + (r - 12) ** 2 / 300))
        cheek = 0.03 * math.exp(-((abs(c - AXIS) - 33) ** 2 / 120 + (r - 34) ** 2 / 200))
        return top + cheek

    edge = ring_points(out, out, 0.0, N)
    edge_v = verts(edge, [edge_z] * N)

    # Top: from the outline in to the gums, with the sprite's light ribs raised a little and its
    # dark crevices sunk.
    skin = []
    prev = edge_v
    for u in (0.02, 0.045, 0.075, 0.11, 0.15, 0.2, 0.25, 0.3, 0.36, 0.42, 0.48, 0.54, 0.6, 0.66, 0.72,
              0.78, 0.84, 0.9, 0.95, 1.0):
        pts = ring_points(out, gum_out, u, N)
        zs = []
        for (c, r), (ec, er) in zip(pts, edge):
            k = rim(math.hypot(c - ec, r - er), 8.0)
            zs.append(edge_z + (dome(c, r) - edge_z) * k + painter.relief(c, r) * k * (1 - u ** 4))
        ring = verts(pts, zs)
        skin += connect(bm, prev, ring)
        prev = ring

    # The gums: a fleshy lip that rises and rolls over into the throat.
    gums = []
    for v, z in ((0.2, 0.31), (0.45, 0.335), (0.7, 0.315), (1.0, 0.22)):
        ring = verts(ring_points(gum_out, gum_in, v, M), [z] * M)
        gums += connect(bm, prev, ring)
        prev = ring

    # The throat: ridged rings sinking from the gums to the core.
    rim_pts = ring_points(gum_in, gum_in, 0.0, K)
    throat = []
    steps = 14
    for i in range(1, steps):
        s = i / steps
        pts = [(c + (CORE[0] - c) * s, r + (CORE[1] - r) * s) for c, r in rim_pts]
        z = 0.22 - 0.33 * s ** 0.85 + 0.024 * math.cos(math.pi * i) * (1 - s)
        ring = verts(pts, [z] * K)
        throat += connect(bm, prev, ring)
        prev = ring
    tip = [bm.verts.new((X(CORE[0]), Y(CORE[1]), -0.13))]
    throat += connect(bm, prev, tip)

    # Underside: a shallow rounded belly.
    belly = []
    prev = edge_v
    for u, n in ((0.03, M), (0.1, K), (0.25, K // 2), (0.5, K // 2), (0.75, K // 2)):
        pts = ring_points(out, out, 0.0, n)
        rim_ref = pts
        pts = [(CENTRE[0] + (c - CENTRE[0]) * (1 - u), CENTRE[1] + (r - CENTRE[1]) * (1 - u)) for c, r in pts]
        zs = [edge_z - 0.15 * rim(math.hypot(c - ec, r - er)) for (c, r), (ec, er) in zip(pts, rim_ref)]
        ring = verts(pts, zs)
        belly += connect(bm, prev, ring)
        prev = ring
    belly += connect(bm, prev, [bm.verts.new((X(CENTRE[0]), Y(CENTRE[1]), -0.18))])

    for f in skin + gums + throat + belly:
        f.smooth = True
    painter.paint(skin, "blue", default=97)
    painter.paint(gums, "gum", default=69)
    painter.paint(throat, "red", default=113)
    for f in belly:
        f.material_index = painter.pal(97)


# --- parts on the shell ---------------------------------------------------------------------------

class Surface:
    def __init__(self, bm):
        self.tree = BVHTree.FromBMesh(bm)

    def z(self, c, r, default=0.0):
        hit = self.tree.ray_cast(Vector((X(c), Y(r), 3.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else default


def P(c, r, z):
    return (X(c), Y(r), z)


def mirrored(fn):
    """Call fn(sign, mirror) for the left part and its mirror image on the right."""
    fn(lambda c: c)
    fn(lambda c: 2 * AXIS - c)


def build_parts(bm, painter, surf):
    pal = painter.pal

    # Brain: a lumpy purple dome on top of the skull (columns 50-76, rows 0-20 and on above).
    def bump(dx, dy, dz):
        # Folds: a few crossing ripples, strongest on top, like the sprite's lumpy purple mass.
        return 1 + (0.07 * math.sin(14 * dx + 1.3) * math.sin(12 * dy + 0.4)
                    + 0.04 * math.sin(23 * dx + 7 * dy) + 0.03 * math.sin(19 * dy - 9 * dx)) * (0.3 + max(dz, 0))
    brain_c, brain_r = (13.6 * PX, 17.0 * PX, 0.19), P(AXIS, 4.0, 0.2)
    faces = lib.blob(bm, brain_r, brain_c, segments=36, rings=14, mat=pal(87), bump=bump)

    painter.paint(faces, "purple", default=87, min_nz=0.0)
    # Bony snout plate between the brain and the upper lip (rows 19-27).
    faces = lib.blob(bm, P(AXIS, 23.8, 0.24), (7.5 * PX, 4.2 * PX, 0.075), segments=16, rings=6, mat=pal(103))
    painter.paint(faces, "blue", default=103, min_nz=0.0)

    # The central knob of the upper lip, ending in a short dark tooth (column 63, rows 39-49).
    faces = lib.blob(bm, P(AXIS, 42.2, 0.27), (2.6 * PX, 3.2 * PX, 0.06), segments=12, rings=6, mat=pal(69))
    painter.paint(faces, "gum", default=69, min_nz=0.0)
    lib.tube(bm, [P(AXIS, 44.0, 0.25), P(AXIS, 46.5, 0.21), P(AXIS, 49.5, 0.15)],
             [1.4 * PX, 1.0 * PX, 0.0], sides=8, mat=pal(163))

    def side(m):
        # Eyes: a dark red socket with a glowing ball (three down each side).
        for c, r in ((37.5, 24.8), (32.3, 32.2), (29.6, 40.6)):
            z = surf.z(m(c), r)
            lib.blob(bm, P(m(c), r, z - 0.01), (2.7 * PX, 2.6 * PX, 0.05), segments=12, rings=6, mat=pal(113))
            lib.blob(bm, P(m(c), r - 0.2, z + 0.025), (1.6 * PX, 1.6 * PX, 0.04), segments=10, rings=5,
                     mat=pal(121, emission=4.0))

        # Fangs round the gums, pointing in and down into the throat: (base, tip, radius px).
        for (bc, br), (tc, tr), rad in (((56.4, 41.0), (57.8, 49.6), 1.5), ((44.0, 47.6), (50.6, 49.3), 1.6),
                                        ((40.6, 54.6), (48.6, 56.6), 1.6), ((44.6, 63.6), (49.6, 63.2), 1.3),
                                        ((46.6, 71.4), (51.6, 70.6), 1.2), ((52.8, 79.6), (54.6, 75.8), 1.1),
                                        ((60.0, 82.4), (60.3, 77.0), 1.1)):
            zb = surf.z(m(bc), br) - 0.01
            mc, mr = bc + (tc - bc) * 0.45, br + (tr - br) * 0.45
            lib.tube(bm, [P(m(bc), br, zb), P(m(mc), mr, zb - 0.025), P(m(tc), tr, zb - 0.07)],
                     [rad * PX, rad * 0.7 * PX, 0.0], sides=8, mat=pal(169))

        # Tentacles hanging off the flanks, thickening at their tips: (col, row, radius px).
        for path in ([(11.0, 40.0, 1.5), (8.7, 42.4, 1.4), (8.3, 44.3, 1.1), (8.6, 45.6, 0.0)],
                     [(15.0, 44.0, 1.6), (12.6, 47.5, 1.5), (11.3, 50.5, 1.5), (10.8, 52.6, 1.0), (10.7, 53.6, 0.0)],
                     [(21.5, 46.5, 1.7), (18.4, 49.5, 1.3), (16.8, 52.5, 1.2), (16.0, 55.5, 1.6), (16.0, 57.6, 1.0),
                      (16.0, 58.4, 0.0)],
                     [(26.5, 53.0, 1.7), (22.8, 56.0, 1.3), (21.2, 59.5, 1.1), (20.8, 62.0, 1.3), (21.6, 64.6, 1.9),
                      (21.6, 66.6, 1.4), (21.6, 67.9, 0.0)]):
            n = len(path)
            pts = [P(m(c), r, 0.04 - 0.06 * i / (n - 1)) for i, (c, r, _) in enumerate(path)]
            faces = lib.tube(bm, pts, [rr * PX for _, _, rr in path], sides=8, mat=pal(101))
            painter.paint(faces, "blue", default=101, min_nz=-0.2)

        # Purple claw low on each side, sweeping down and out (columns 27-38, rows 64-77).
        path = [(37.2, 64.6, 0.3, 3.0), (34.6, 68.5, 0.24, 3.4), (31.6, 72.2, 0.15, 2.7), (29.0, 75.4, 0.07, 1.6),
                (27.4, 77.4, 0.03, 0.0)]
        faces = lib.tube(bm, [P(m(c), r, z) for c, r, z, _ in path], [w * PX for *_, w in path], sides=10,
                         mat=pal(87), flat=0.4)
        painter.paint(faces, "purple", default=87, min_nz=-0.2)

    mirrored(side)

    # Chin spike (column 63, rows 89-94).
    faces = lib.tube(bm, [P(AXIS, 88.0, 0.06), P(AXIS, 91.0, 0.03), P(AXIS, 93.2, 0.0), P(AXIS, 94.4, 0.0)],
                     [1.8 * PX, 1.4 * PX, 0.9 * PX, 0.0], sides=8, mat=pal(103))
    painter.paint(faces, "blue", default=103, min_nz=-0.2)

    # The glowing core deep in the throat, in a red glow.
    lib.blob(bm, P(CORE[0], CORE[1], -0.1), (4.2 * PX, 3.6 * PX, 0.05), segments=14, rings=6, mat=pal(117))
    lib.blob(bm, P(CORE[0] + 0.3, CORE[1] - 0.2, -0.07), (2.4 * PX, 2.2 * PX, 0.05), segments=12, rings=6,
             mat=pal(121, emission=4.0))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = Palette(sprite)
    painter = Painter(load_grid(), pal)
    bm = bmesh.new()
    build_shell(bm, painter)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    surf = Surface(bm)
    build_parts(bm, painter, surf)
    return lib.to_object(NAME, bm, pal.mats, coll)


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(out):
    """The whole head's sprite as one image, 2 image px per sprite px, padded to the 240 x 280
    (size 10) frame render_preview expects, with Blender's origin in the middle."""
    import numpy as np
    sprite = merged_sprite()
    img = np.zeros((280, 240, 4), dtype=np.float32)
    for (c, r), v in load_grid().items():
        x, y = 2 * c - 7, 2 * (r + 22)  # column 63's centre and row 47.5 land on the image centre
        if 0 <= x and x + 2 <= 240 and 0 <= y and y + 2 <= 280:
            img[y:y + 2, x:x + 2] = [*(ch / 255 for ch in sprite["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 240, 280, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - (SX0 + AXIS + 0.5), e["cy"] - (SY0 + ROW0 + 0.5))
              for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=10, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
