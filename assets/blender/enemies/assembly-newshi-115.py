"""Grey dome fortress (newshi.shp, assembly of 14 pieces): a 3D version of its sprites.

Seen in episode 1 (levels 1.10, 1.29, 1.38) and episode 3 (3.21). Fourteen 2x2 ground enemies
make one 96 x 112 px structure (sprite.json `assemblyLayout`): a long grey dome, rounded at its
front (the top of the screen) and ribbed along its length, with a darker collar round its nose.
A red hoop leans over the nose, its legs sinking into the dome's sides, and a grey spire with a
row of red lights runs from the top of the hoop down to a grey capsule on the nose. Under the
capsule a red gantry (two L brackets, a cross bar, four rails over a dark slot) and a red loop
hang down the dome. On each side a red pipe and struts lead out to a jointed red and grey arm
that reaches down the screen to a grey foot with an orange lamp. White blocks circle the nose
under the hoop; they move between the two animation frames, so the four pieces they show in
(newshi-3, -5, -41, -43) get a second model (<piece>-f2) with the blocks where frame 2 has them.

The whole structure is built once in assembly coordinates (mirror symmetric about pixel column
48, the sprite's axis), then cut into the pieces with common.split_assembly. It is a ground
object: its base is at z = 0.

Run: blender --background --python assets/blender/enemies/assembly-newshi-115.py [-- --preview out.png]
(the preview is the whole structure, out-f2.png the second frame, and each piece also gets
<piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newshi-115"
ROOT = common.repo_root(__file__)
# Assembly pixel (0, 0) is the top-left corner of the 96 x 112 px block (screen 102, -32); its
# centre (screen 150, 24) is the Blender origin.
SX0, SY0 = 102, -32
W_PX, H_PX = 96, 112
AXIS = 48.5  # the axis runs down the middle of pixel column 48 (edge coordinates)
ANIMATED = ["newshi-3", "newshi-5", "newshi-41", "newshi-43"]


def X(c):
    """Assembly x in pixel-edge coordinates (column c spans c..c+1) to Blender X."""
    return (c - W_PX / 2) / 12


def Y(r):
    """Assembly y in pixel-edge coordinates to Blender Y: sprite up is +Y."""
    return (H_PX / 2 - r) / 12


def mx(c):
    """Mirror an x (pixel-edge coordinates) about the axis."""
    return 2 * AXIS - c


# --- the dome's shape --------------------------------------------------------------------------

NOSE, FULL, TAIL = 28.0, 62.5, 102.5  # the nose tip, where it reaches full width, where it narrows
HALF_W = 33.5  # px
HEIGHT = 1.5  # units
XS_N = 2.1  # cross-section superellipse exponent (a little fuller than an ellipse)


def dome_w(r):
    """Half width (px) of the dome at row r."""
    if r <= NOSE:
        return 0.0
    if r < FULL:
        t = (FULL - r) / (FULL - NOSE)
        return HALF_W * max(0.0, 1 - t ** 1.8) ** (1 / 1.8)
    if r <= TAIL:
        return HALF_W
    return HALF_W - (r - TAIL) * 0.32


def dome_h(r):
    """Height (units) of the dome's crest at row r."""
    return HEIGHT * (dome_w(r) / HALF_W) ** 0.7


def surf(c, r):
    """Height of the dome's surface at (c, r) in pixel-edge coordinates (0 outside it)."""
    w = dome_w(r)
    if w <= 0:
        return 0.0
    u = min(1.0, abs(c - AXIS) / w)
    return dome_h(r) * max(0.0, 1 - u ** XS_N) ** (1 / XS_N)


# --- geometry helpers --------------------------------------------------------------------------

def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=8, mat=0, smooth=True, box=False, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in pixel-edge
    coordinates. Rings stand perpendicular to the path in the XY plane; the width is across the
    path and the height along Z. box=True gives a chamfered rectangular section."""
    before = set(bm.faces)
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    if box:
        prof = [(1, 0.6), (0.6, 1), (-0.6, 1), (-1, 0.6), (-1, -0.6), (-0.6, -1), (0.6, -1), (1, -0.6)]
    else:
        prof = [(math.cos(2 * math.pi * (k + 0.5) / sides), math.sin(2 * math.pi * (k + 0.5) / sides))
                for k in range(sides)]
    n = len(prof)
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w / 12 * a) + up * (h * b)) for a, b in prof])
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _tag(bm, before, mat, smooth)


def block(bm, c0, r0, c1, r1, z0, z1, mat=0, bevel=0.35):
    """A box over pixel-edge columns c0..c1 and rows r0..r1 from z0 to z1, its top edges
    chamfered by `bevel` px."""
    before = set(bm.faces)
    b = min(bevel, (c1 - c0) / 3, (r1 - r0) / 3)
    bz = min(b / 12, (z1 - z0) / 3)
    base = ccw([(c0, r0), (c1, r0), (c1, r1), (c0, r1)])
    top = ccw([(c0 + b, r0 + b), (c1 - b, r0 + b), (c1 - b, r1 - b), (c0 + b, r1 - b)])
    ring = lambda pts, z: [bm.verts.new((X(c), Y(r), z)) for c, r in pts]  # noqa: E731
    lo, mid, hi = ring(base, z0), ring(base, z1 - bz), ring(top, z1)
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for a, bb in ((lo, mid), (mid, hi)):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], bb[j], bb[i]))
    _tag(bm, before, mat, False)


def densify(outline, step=2.0):
    out = []
    for (c0, r0), (c1, r1) in zip(outline, outline[1:] + outline[:1]):
        n = max(1, math.ceil(math.hypot(c1 - c0, r1 - r0) / step))
        out += [(c0 + (c1 - c0) * k / n, r0 + (r1 - r0) * k / n) for k in range(n)]
    return out


def conform(bm, outline, t, mat=0, sink=0.05, lift=0.0, step=2.0):
    """A plate on the dome's surface with the outline (pixel-edge coordinates, any winding):
    its top follows the surface `t` above it (plus `lift`), its bottom sinks `sink` into it."""
    before = set(bm.faces)
    pts = ccw(densify(outline, step))
    top = [bm.verts.new((X(c), Y(r), surf(c, r) + lift + t)) for c, r in pts]
    bot = [bm.verts.new((X(c), Y(r), surf(c, r) + lift - sink)) for c, r in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    _tag(bm, before, mat, False)


def ccw(pts):
    """The outline (pixel-edge coordinates) ordered counter-clockwise as seen from above in
    Blender (rows run down the screen, so that is clockwise in pixel terms)."""
    area = sum(X(c0) * Y(r1) - X(c1) * Y(r0) for (c0, r0), (c1, r1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area > 0 else list(reversed(pts))


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def hull(points):
    """2D convex hull (counter-clockwise)."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def chunk(bm, pixels, z0, z1, mat=0):
    """A bevelled block over the convex hull of a cluster of pixels (col, row)."""
    before = set(bm.faces)
    corners = [(c + dc, r + dr) for c, r in pixels for dc in (0, 1) for dr in (0, 1)]
    hp = ccw(hull(corners))
    cc = sum(p[0] for p in hp) / len(hp)
    cr = sum(p[1] for p in hp) / len(hp)
    shrink = lambda k: [(cc + (c - cc) * k, cr + (r - cr) * k) for c, r in hp]  # noqa: E731
    lo = [bm.verts.new((X(c), Y(r), z0)) for c, r in hp]
    mid = [bm.verts.new((X(c), Y(r), z1 - 0.06)) for c, r in shrink(0.95)]
    hi = [bm.verts.new((X(c), Y(r), z1)) for c, r in shrink(0.72)]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(hp)
    for a, b in ((lo, mid), (mid, hi)):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    _tag(bm, before, mat, False)


def mirror(bm, faces):
    """Add a mirror image (about the axis) of the given faces."""
    verts = {v for f in faces for v in f.verts}
    edges = {e for f in faces for e in f.edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + list(faces))["geom"]
    ax = X(AXIS)
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


# --- pixel data --------------------------------------------------------------------------------

def assembly_grid(frame):
    """The whole structure's pixels (palette indices, -1 transparent) for animation frame
    `frame` (0 or 1; pieces with one frame keep it), and the colours of every piece."""
    layout = common.load_sprite(ROOT, "newshi-115")["assemblyLayout"]
    grid = [[-1] * W_PX for _ in range(H_PX)]
    colors = {}
    for e in layout:
        data = common.load_sprite(ROOT, e["model"])
        colors.update(data["colors"])
        f = data["frames"][min(frame, len(data["frames"]) - 1)]
        x0, y0 = e["cx"] - 12 - SX0, e["cy"] - 14 - SY0
        for r, row in enumerate(f["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid, colors


WHITE = {12, 13, 14, 105, 106, 107, 108, 109, 110}


def white_blocks(grid):
    """Clusters of the white blocks between the hoop and the nose (rows 17-35, off the spire),
    as lists of pixels, with the cluster's most common bright index."""
    seen = set()
    out = []
    for r in range(17, 36):
        for c in range(26, 71):
            if (c, r) in seen or grid[r][c] not in WHITE or 43 <= c <= 53:
                continue
            stack, cluster = [(c, r)], []
            seen.add((c, r))
            while stack:
                pc, pr = stack.pop()
                cluster.append((pc, pr))
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = pc + dc, pr + dr
                    if (17 <= nr <= 35 and 26 <= nc <= 70 and not 43 <= nc <= 53
                            and (nc, nr) not in seen and grid[nr][nc] in WHITE):
                        seen.add((nc, nr))
                        stack.append((nc, nr))
            vals = [grid[pr][pc] for pc, pr in cluster]
            if len(cluster) < 3 or not any(v in (13, 14) or v >= 107 for v in vals):
                continue  # light pixels of the collar, not a block
            out.append(cluster)
    return out


# --- the structure -----------------------------------------------------------------------------

def build(sprite, grid, tag):
    coll = common.reset_collection(f"{NAME}{tag}")
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshi115", **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.45, roughness=0.35),  # 0 dome grey
        pal(7, metallic=0.45, roughness=0.4),  # 1 darker collar round the nose
        pal(12, metallic=0.5, roughness=0.3),  # 2 light ribs
        pal(72, metallic=0.25, roughness=0.55),  # 3 red
        pal(69, metallic=0.25, roughness=0.6),  # 4 dark red
        pal(75, metallic=0.3, roughness=0.35),  # 5 light red
        pal(2, metallic=0.2, roughness=0.8),  # 6 dark recesses
        pal(5, metallic=0.5, roughness=0.45),  # 7 dark grey machinery
        pal(8, metallic=0.5, roughness=0.4),  # 8 grey
        pal(11, metallic=0.35, roughness=0.35),  # 9 light grey (capsule, piston)
        pal(14, metallic=0.1, roughness=0.35),  # 10 white blocks
        pal(117, emission_strength=2.5),  # 11 dim red light
        pal(118, emission_strength=3.0),  # 12 red light
        pal(120, emission_strength=4.0),  # 13 orange light
        pal(6, metallic=0.5, roughness=0.4),  # 14 spire grey
        pal(4, metallic=0.4, roughness=0.5),  # 15 darker grey (spire neck, rails)
    ]
    DOME, COLLAR, RIB, RED, DRED, LRED, DARK, MECH, GREY, LGREY, WHITE_M, L1, L2, L3, SPIRE, DGREY = range(16)
    bm = bmesh.new()

    # ---- the dome: half superellipse sections lofted down the screen, flat underneath ----
    rows = [NOSE, 28.3, 29, 30, 31.5, 33, 35, 37.5, 40, 43, 46, 50, 54, 58, 62.5, 72, 82, 92, 102.5, 107, 112.5]
    segs = 18
    rings = []
    for r in rows:
        w, h = dome_w(r), dome_h(r)
        if w <= 0:
            rings.append([bm.verts.new((X(AXIS), Y(r), 0.0))] * (segs + 1))
            continue
        ring = []
        for k in range(segs + 1):
            a = math.pi * k / segs
            ca, sa = math.cos(a), math.sin(a)
            u = math.copysign(abs(ca) ** (2 / XS_N), ca)
            v = abs(sa) ** (2 / XS_N)
            ring.append(bm.verts.new((X(AXIS + w * u), Y(r), h * v)))
        rings.append(ring)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        rm = (rows[i] + rows[i + 1]) / 2
        for k in range(segs):
            if r0[0] is r0[1]:
                f = bm.faces.new((r0[0], r1[k], r1[k + 1]))
            else:
                f = bm.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
            u = abs(math.cos(math.pi * (k + 0.5) / segs))
            f.material_index = COLLAR if rm < 36 + 12 * u ** 1.5 else DOME
            f.smooth = True
    bottom = [ring[0] for ring in rings[1:]] + [ring[-1] for ring in reversed(rings[1:])]
    f = bm.faces.new([rings[0][0]] + bottom)
    f.material_index = DOME
    end = bm.faces.new(rings[-1])
    end.material_index = DOME

    # Ribs along the dome (the light lines at columns 23-24, 34 and 48-49 and their mirrors).
    for u, r_start in ((0.0, 74.0), (0.43, 33.0), (0.73, 37.0), (-0.43, 33.0), (-0.73, 37.0)):
        path = []
        for r in [r_start + (112.5 - r_start) * k / 10 for k in range(11)]:
            c = AXIS + u * dome_w(r)
            path.append((c, r, surf(c, r) + 0.005, 0.7, 0.03))
        sweep(bm, path, sides=6, mat=RIB, cap_start=True, cap_end=True)

    # ---- the hoop over the nose: a band between two superellipses, tilted up at the front ----
    cx, cy, n = AXIS, 34.5, 2.5

    def se(a, b, phi):
        c, s = math.cos(phi), math.sin(phi)
        return (cx + a * math.copysign(abs(c) ** (2 / n), c), cy - b * abs(s) ** (2 / n))

    def hoop_z(r):
        return 0.55 + (cy - r) * 0.036

    path = [(25.8, 45.0, 0.04, 1.0, 0.06), (26.0, 41.0, 0.2, 1.2, 0.08), (26.4, 37.5, 0.38, 1.5, 0.09)]
    steps = 26
    for k in range(steps + 1):
        phi = math.pi * (1 - k / steps)
        oc, orr = se(23.5, 23.5, phi)
        ic, irr = se(20.0, 16.5, phi)
        mc, mr = (oc + ic) / 2, (orr + irr) / 2
        hw = math.hypot(oc - ic, orr - irr) / 2
        path.append((mc, mr, hoop_z(mr), hw, 0.1))
    path += [(mx(26.4), 37.5, 0.38, 1.5, 0.09), (mx(26.0), 41.0, 0.2, 1.2, 0.08), (mx(25.8), 45.0, 0.04, 1.0, 0.06)]
    sweep(bm, path, sides=8, mat=RED)

    # ---- the spire with its lights, from the top of the hoop down to the capsule ----
    sweep(bm, [(48.5, 10.2, 1.66, 4.6, 0.09), (48.5, 12.0, 1.65, 4.6, 0.09), (48.5, 26.0, 1.5, 4.6, 0.09)],
          mat=SPIRE, box=True)
    sweep(bm, [(48.5, 10.2, 1.7, 0.0, 0.0), (48.5, 10.6, 1.7, 5.2, 0.07), (48.5, 12.3, 1.69, 5.2, 0.07),
               (48.5, 12.7, 1.69, 0.0, 0.0)], sides=8, mat=DGREY)  # cap over the hoop
    sweep(bm, [(48.5, 25.8, 1.5, 5.5, 0.12), (48.5, 29.0, 1.47, 5.5, 0.12)], mat=GREY, box=True)  # collar
    sweep(bm, [(48.5, 29.0, 1.47, 5.0, 0.1), (48.5, 30.5, 1.45, 5.0, 0.1)], mat=DARK, box=True)
    sweep(bm, [(48.5, 30.5, 1.44, 3.4, 0.08), (48.5, 35.0, 1.38, 3.4, 0.08)], mat=DGREY, box=True)  # neck
    for r0, r1, m in ((13.8, 15.0, L1), (15.8, 17.0, L1), (17.8, 20.0, L2), (20.8, 23.0, L2), (23.8, 26.0, L3)):
        block(bm, 47.0, r0, 51.0, r1, 1.5, 1.75 - (r0 - 10) * 0.0107, mat=m, bevel=0.3)
    # Grey capsule on the nose (columns 45-52, rows 35-44).
    zc = surf(48.5, 39.5)
    sweep(bm, [(48.5, 34.6, zc + 0.12, 0.0, 0.0), (48.5, 35.3, zc + 0.12, 2.8, 0.13), (48.5, 36.5, zc + 0.12, 3.8, 0.19),
               (48.5, 42.5, zc + 0.08, 3.8, 0.19), (48.5, 44.0, zc + 0.05, 2.6, 0.13), (48.5, 44.6, zc + 0.05, 0.0, 0.0)],
          sides=12, mat=LGREY)

    # ---- red gantry under the capsule (left half, mirrored) ----
    first = len(bm.faces)
    conform(bm, rect(37, 37, 40, 44), 0.16, mat=RED)  # L bracket: upright
    conform(bm, rect(40, 38, 43.5, 41), 0.13, mat=RED)  # ... and its arm to the capsule
    conform(bm, rect(39, 49, 41, 62), 0.1, mat=RED)  # outer rail
    conform(bm, rect(44, 48, 46, 62), 0.12, mat=RED)  # inner rail
    conform(bm, rect(39, 58, 46, 60), 0.13, mat=DRED)  # cross piece
    conform(bm, rect(41, 49, 48.5, 54), 0.015, mat=DARK)  # dark slot under the cross bar
    bm.faces.ensure_lookup_table()
    mirror(bm, bm.faces[first:])
    conform(bm, rect(47, 42, 50, 45.5), 0.16, mat=RED)  # stem from the capsule
    conform(bm, rect(41, 45, 57, 49), 0.17, mat=RED)  # cross bar
    # The loop hanging below (columns 46-51, rows 64-73) with its dark slot.
    loop = [(48.5 + 3.0 * math.sin(2 * math.pi * k / 14), 68.8 - 5.0 * math.cos(2 * math.pi * k / 14)) for k in range(14)]
    conform(bm, loop, 0.1, mat=RED, step=3)
    conform(bm, [(48, 69.5), (49.2, 69.5), (49.2, 72.5), (48, 72.5)], 0.11, mat=DARK)

    # ---- side arms (left, mirrored) ----
    first = len(bm.faces)
    # Red pipe out of the dome's side, bending down to the elbow.
    sweep(bm, [(23.0, 46.8, 0.5, 1.7, 0.12), (15.0, 46.8, 0.52, 1.7, 0.12), (12.6, 47.6, 0.52, 1.7, 0.12),
               (11.3, 49.5, 0.5, 1.6, 0.12), (10.8, 52.0, 0.48, 1.5, 0.11)], sides=8, mat=RED)
    block(bm, 6, 50.5, 14, 55, 0.0, 0.45, mat=MECH)  # grey elbow
    block(bm, 10, 55, 19, 58, 0.12, 0.34, mat=GREY)  # grey strut to the dome
    sweep(bm, [(9.0, 59.9, 0.36, 1.1, 0.08), (19.0, 59.9, 0.36, 1.1, 0.08)], sides=8, mat=DRED)  # red strut
    # Red shoulder block (columns 3-9, rows 55-61), rounded on top, with a light ridge.
    sweep(bm, [(6.5, 54.6, 0.27, 0.0, 0.0), (6.5, 55.0, 0.27, 3.0, 0.22), (6.5, 56.0, 0.27, 3.6, 0.3),
               (6.5, 61.0, 0.27, 3.6, 0.3), (6.5, 62.0, 0.27, 3.0, 0.24)], sides=10, mat=RED)
    sweep(bm, [(6.8, 55.3, 0.57, 0.0, 0.0), (6.8, 55.8, 0.57, 0.8, 0.03), (6.8, 61.0, 0.57, 0.8, 0.03),
               (6.8, 61.6, 0.57, 0.0, 0.0)], sides=6, mat=LRED)
    # Grey frame down the arm (columns 1-10, rows 62-75) with the red rod through it.
    block(bm, 2.5, 62, 9.5, 67, 0.0, 0.3, mat=MECH)
    block(bm, 1.0, 67, 11.0, 71, 0.0, 0.36, mat=MECH)
    block(bm, 7.5, 67.5, 10.5, 70.5, 0.36, 0.42, mat=LGREY)
    block(bm, 1.5, 71, 8.5, 75, 0.0, 0.26, mat=DGREY)
    sweep(bm, [(6.3, 62.0, 0.36, 1.6, 0.1), (6.3, 71.0, 0.36, 1.6, 0.1)], sides=8, mat=RED)
    sweep(bm, [(10.0, 70.5, 0.3, 1.0, 0.07), (10.0, 80.0, 0.3, 1.0, 0.07)], sides=8, mat=RED)  # outer bar
    sweep(bm, [(1.8, 68.0, 0.2, 0.9, 0.07), (1.8, 87.0, 0.2, 0.9, 0.07)], sides=6, mat=MECH)  # back rail
    # Red joint (columns 3-8, rows 75-79) and the grey piston below it (columns 4-7, rows 79-87).
    sweep(bm, [(5.8, 74.6, 0.25, 0.0, 0.0), (5.8, 75.2, 0.25, 2.6, 0.2), (5.8, 79.0, 0.25, 2.8, 0.22),
               (5.8, 80.0, 0.25, 2.2, 0.16)], sides=10, mat=RED)
    sweep(bm, [(5.8, 79.0, 0.24, 2.3, 0.16), (5.8, 87.5, 0.24, 2.3, 0.16)], sides=10, mat=LGREY)
    # Red rod down to the foot (rows 87-99).
    sweep(bm, [(3.0, 87.0, 0.24, 1.0, 0.07), (3.2, 90.5, 0.22, 1.0, 0.07), (4.6, 92.0, 0.2, 1.1, 0.08),
               (4.6, 99.5, 0.2, 1.1, 0.08)], sides=8, mat=RED)
    # Grey foot (columns 1-5, rows 99-103) with the orange lamp at its end.
    block(bm, 1.0, 99.5, 6.0, 104, 0.0, 0.32, mat=GREY)
    block(bm, 1.6, 103.6, 5.4, 106, 0.04, 0.22, mat=L3, bevel=0.3)
    bm.faces.ensure_lookup_table()
    mirror(bm, bm.faces[first:])

    # ---- white blocks circling the nose under the hoop ----
    for cluster in white_blocks(grid):
        size = len(cluster)
        chunk(bm, cluster, 0.0, 0.18 + min(0.22, size * 0.006), mat=WHITE_M)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f"{NAME}{tag}")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(f"{NAME}{tag}", mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite(colors):
    data = common.load_sprite(ROOT, "newshi-115")
    data["colors"] = dict(colors)
    return data


def composite_png(grid, colors, out):
    """The structure's sprite as one image (96 x 112 px, the 24:28 shape render_preview expects
    for size 8)."""
    import numpy as np
    img = np.zeros((H_PX, W_PX, 4), dtype=np.float32)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W_PX, H_PX, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    grid0, colors = assembly_grid(0)
    grid1, _ = assembly_grid(1)
    sprite = merged_sprite(colors)
    layout = [(e["model"], e["cx"] - SX0 - W_PX // 2, e["cy"] - SY0 - H_PX // 2) for e in sprite["assemblyLayout"]]
    names = [n for n, _, _ in layout]

    obj = build(sprite, grid0, "")
    pieces = common.split_assembly(obj, layout)
    obj2 = build(sprite, grid1, "-f2")
    pieces2 = common.split_assembly(obj2, [(f"{n}-f2", cx, cy) for n, cx, cy in layout if n in ANIMATED])

    for name in names:
        data = common.load_sprite(ROOT, name)
        sprites = data["sprites"]
        if name in ANIMATED:
            first, second = (dict(s, frames=[s["frames"][i]]) for s in sprites[:1] for i in (0, 1))
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", [first])
            common.export_sprite_model(ROOT, [pieces2[f"{name}-f2"]], f"enemies/{name}-f2", [second])
        else:
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites)

    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        tmp = Path(tempfile.mkdtemp())
        common.render_preview([obj], str(out), composite_png(grid0, colors, tmp / "a0.png"), size=8, view_px=640)
        common.render_preview([obj2], str(out.with_name(out.stem + "-f2.png")),
                              composite_png(grid1, colors, tmp / "a1.png"), size=8, view_px=640)
        for name in names:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
        for name in ANIMATED:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][1]["image"]
            common.render_preview([pieces2[f"{name}-f2"]], str(out.parent / f"{name}-f2.png"), img, size=2)


if __name__ == "__main__":
    main()
