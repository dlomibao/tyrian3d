""" assembly-newshr-273 (newshr.shp, 16 pieces, 96 x 112 px): the IXMUCANE boss's rock heap
with the red-eyed machine buried on its left edge.

What it is: a heap of broken boulders (brown, golden and a few grey stones, piled highest in the middle and
on the right) dumped over a dark machine. On the left the machine sticks out of the rubble: a radiator
of upright fins under the rocks at the top, a big glowing red orb in a machined grey bezel, two red
lenses in the deck below it, and a horizontal coil with red-lit windings, pipes running off to the left.
The machine's left side is cut straight (assembly-newshr-267's pile covers that edge at first, and its
own machine half carries on there); 267 and this heap slide apart in ev20 and uncover it.

Build (one object in assembly coordinates, cut into the 16 pieces with common.split_assembly):
- boulders: one lib_newshd_rock rock body per stone of the sprite (its region found by sharing the
  heap's pixels between seed points along the dark crevices), lofted from its own region, its waist
  standing higher the further it sits inside the heap, its summit leaning to the sprite's lit side,
  broken by planar fracture faces (chipped stone, crisp edges), the bottom flat on the ground; the
  D175 facet ramp gives every facet one shade of the stone's own palette ramp, its lit facets the
  sprite's highlights and those turned away its dark limb (matte, Specular IOR Level 0.15 as D178).
- the machine: hard surface: a chamfered housing on the sprite's machine outline, chamfered fins
  and headers in the radiator, a chamfered block with pipes, the orb's bezel a lofted ring with
  chamfered lips, the orb a glowing dome (metallic 1, rough, D126/D173), the eyes glowing domes in
  ring bezels, the coil (the jaw) a lying drum with glowing windings on the sprite's red rows and clamp
  rings on its grey rows, flanged pipes. The orb, eye and winding faces take the sprite's own red shade
  under them (red_glow, QA M4), so the swirl, the eyes' hot cores and the lit windings read as drawn.
- QA M4: the facet ramp runs with broad facets (28 deg, 8 px), one fine cut, big chips: clean faces.
- D90/D118 outline shell from a sealed copy of the whole heap, cut per piece without filling.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshr-273.py
     (exports the 16 pieces; with -- --views DIR also writes review renders)
"""

import heapq
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE), str(HERE.parents[2] / "tools")]
import common  # noqa: E402
import lib_newshd_rock as R  # noqa: E402
import sprite_mask as SM  # noqa: E402

ROOT = common.repo_root(__file__)
REF = ROOT / "reference" / "models"


# --- pixel data (the whole 96 x 112 sprite, its masks, the machine outline, the boulders) -------------------

ROWS = [["newshr-159", "newshr-161", "newshr-163", "newshr-165"],
        ["newshr-197", "newshr-199", "newshr-201", "newshr-203"],
        ["newshr-235", "newshr-237", "newshr-239", "newshr-241"],
        ["newshr-273", "newshr-275", "newshr-277", "newshr-279"]]

# The machine's outline in pixel edges (col, row) of the whole block (from the current script).
MACHINE = [(0, 21), (28, 21), (28, 35), (31, 36), (36, 38), (38, 39), (40, 41), (41, 44), (41, 48),
           (39, 51), (40, 53), (39, 54), (38, 56), (36, 56), (36, 68), (35, 68), (34, 69), (34, 72),
           (33, 72), (33, 75), (30, 75), (30, 85), (15, 85), (15, 86), (11, 86), (11, 82), (6, 82), (6, 85), (0.6, 85), (0.6, 71),
           (2, 70), (3, 69), (4, 68), (5, 67), (5, 57), (6, 56), (7, 55), (8, 54), (10, 53), (10, 44),
           (9, 42), (8, 41), (7, 39), (6, 38), (5, 37), (3, 36), (0, 36)]

# One point (col, row) on each boulder.
SEEDS = [
    (4, 10), (13, 9), (5, 16), (15, 16), (24, 17), (27, 12),
    (40, 9), (50, 8), (48, 15),
    (32, 23), (39, 26), (49, 22), (59, 25), (67, 23), (77, 30), (66, 33), (54, 33), (40, 35),
    (43, 44), (50, 41), (64, 45), (75, 46), (77, 39),
    (47, 57), (69, 64), (74, 56), (79, 53), (39, 56), (38, 65),
    (40, 79), (54, 76), (70, 73), (68, 81), (57, 84),
    (35, 89), (46, 89), (38, 96), (52, 98), (59, 88), (70, 87),
]
DARK = {1, 2, 160, 161, 66, 80, 112}


def load_grid():
    idx = [[-1] * W for _ in range(H)]
    colors = {}
    for j, names in enumerate(ROWS):
        for i, name in enumerate(names):
            d = json.loads((REF / name / "sprite.json").read_text())
            colors.update(d["colors"])
            for r, line in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(line.split()):
                    idx[28 * j + r][24 * i + c] = int(v)
    m = SM.masks(idx, {int(k): tuple(v) for k, v in colors.items()})
    return idx, colors, m


def inside(poly, x, y):
    n, hit = len(poly), False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def machine_mask():
    return [[inside(MACHINE, c + 0.5, r + 0.5) for c in range(W)] for r in range(H)]


def segment(idx, keep, seeds=None):
    seeds = SEEDS if seeds is None else seeds
    INF = float("inf")
    cost = [[INF] * W for _ in range(H)]
    owner = [[-1] * W for _ in range(H)]
    hp = []
    for i, (c, r) in enumerate(seeds):
        cost[r][c] = 0
        owner[r][c] = i
        heapq.heappush(hp, (0, c, r, i))
    while hp:
        d, c, r, i = heapq.heappop(hp)
        if d > cost[r][c] or owner[r][c] != i:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if not (0 <= nc < W and 0 <= nr < H) or not keep[nr][nc]:
                continue
            v = idx[nr][nc]
            step = 4.0 if v in DARK else 1.0
            if d + step < cost[nr][nc]:
                cost[nr][nc] = d + step
                owner[nr][nc] = i
                heapq.heappush(hp, (d + step, nc, nr, i))
    return owner


def depth_map(keep):
    """Chebyshev distance (px) to the outside of `keep`."""
    from collections import deque
    dist = [[0 if not keep[r][c] else -1 for c in range(W)] for r in range(H)]
    q = deque((c, r) for r in range(H) for c in range(W) if dist[r][c] == 0)
    # the picture's edge counts as outside too
    while q:
        c, r = q.popleft()
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                nc, nr = c + dc, r + dr
                if 0 <= nc < W and 0 <= nr < H and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    q.append((nc, nr))
    for r in range(H):
        for c in range(W):
            if dist[r][c] == -1:
                dist[r][c] = 30
    return dist


NAME = "assembly-newshr-273"
W, H = 96, 112
PX = 1 / 12
TAG = "nshr273"


def X(c):  # pixel edge column -> Blender X (origin at the block's centre)
    return (c - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


# --- the sprite ----------------------------------------------------------------------------------------

IDX, COLORS, MASKS = load_grid()
INNER = MASKS["inner"]
MACH = machine_mask()
SPR = {"name": NAME, "colors": COLORS, "frames": [{"pixels": IDX, "width": W, "height": H}]}


def lum(v):
    r, g, b = COLORS[str(v)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def family(v):
    if 2 <= v <= 13:
        return 0
    if 16 <= v <= 31:
        return 1
    if 160 <= v <= 175:
        return 10
    return None


# --- materials -------------------------------------------------------------------------------------------

MATS = {}


def mat(index, kind="metal"):
    key = (index, kind)
    if key in MATS:
        return MATS[key]
    if kind == "rock":
        m = common.palette_material(SPR, index, TAG, metallic=0.0, roughness=0.9)
        spec_level(m, 0.15)
    elif kind == "glow":
        m = common.palette_material(SPR, index, f"{TAG}_glow", metallic=1.0, roughness=0.9, emission_strength=GLOW[index])
    elif kind == "rglow":  # the sprite's own red shades on the orb, eyes and coil (QA M4): unlit palette colour
        m = common.palette_material(SPR, index, f"{TAG}_rg", metallic=1.0, roughness=0.9, emission_strength=1.0)
    elif kind == "polish":  # rails, bezel lips: smoother satin metal
        m = common.palette_material(SPR, index, f"{TAG}_pol", metallic=0.55, roughness=0.32)
        spec_level(m, 0.7)
    else:  # satin machine metal
        m = common.palette_material(SPR, index, f"{TAG}_m", metallic=0.4, roughness=0.45)
        spec_level(m, 0.5)
    MATS[key] = m
    return m


GLOW = {116: 0.9, 114: 0.9, 118: 0.5}  # mostly glow: the lit part (and its metal reflection, F0 = colour) stays small (D126)


def spec_level(m, v):
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = v
            break


# --- hard-surface helpers (pixel coordinates in, Blender units out) ----------------------------------------

class Part:
    """One bmesh with a material list; faces tagged by material and smooth/flat."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def slot(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def tag(self, start, m, smooth=False):
        self.bm.faces.ensure_lookup_table()
        k = self.slot(m)
        for f in self.bm.faces[start:]:
            f.material_index = k
            f.smooth = smooth

    def obj(self, coll, sharp=30):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        coll.objects.link(o)
        me.set_sharp_from_angle(angle=math.radians(sharp))
        return o


def hull(P, pts, m):
    """Convex hull of Blender-space points (a chamfered block)."""
    bm = P.bm
    n = len(bm.faces)
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    P.tag(n, m, False)


def chbox(P, c0, r0, c1, r1, z0, z1, ch, m, chz=None):
    """A box over pixel edges c0..c1, r0..r1, z0..z1 (units), its top edges chamfered `ch` px
    (and `chz` units down); the bottom stays square on the ground."""
    x0, x1, y0, y1 = X(c0), X(c1), Y(r1), Y(r0)
    d = ch * PX
    dz = chz if chz is not None else d
    pts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
    pts += [(x0, y0, z1 - dz), (x1, y0, z1 - dz), (x1, y1, z1 - dz), (x0, y1, z1 - dz)]
    pts += [(x0 + d, y0 + d, z1), (x1 - d, y0 + d, z1), (x1 - d, y1 - d, z1), (x0 + d, y1 - d, z1)]
    hull(P, pts, m)


def offset_poly(pts, d):
    """Offset a closed polygon (CCW, Blender XY) inward by d along the vertex bisectors."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        cosh = max(0.35, b.dot(n0))
        q = p1 + b * (d / cosh)
        out.append((q.x, q.y))
    return out


def ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if a > 0 else pts[::-1]


def plinth(P, outline_px, z0, z1, ch, m):
    """A slab on a pixel-edge outline, z0..z1, its top edge chamfered `ch` px (ring inset)."""
    base = ccw([(X(c), Y(r)) for c, r in outline_px])
    top = offset_poly(base, ch * PX)
    bm = P.bm
    n0 = len(bm.faces)
    rings = [[bm.verts.new((x, y, z0)) for x, y in base],
             [bm.verts.new((x, y, z1 - ch * PX)) for x, y in base],
             [bm.verts.new((x, y, z1)) for x, y in top]]
    k = len(base)
    for a, b in zip(rings, rings[1:]):
        for i in range(k):
            j = (i + 1) % k
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[-1])
    bm.faces.new(list(reversed(rings[0])))
    P.tag(n0, m, False)


def tube(P, a, b, r, m, sides=12, rz=None, flange=None, smooth=True):
    """A cylinder between Blender points a and b, radius r (units), elliptical with rz; optional
    flanges (radius, length) at both ends."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(up).normalized()
    v = u.cross(ax).normalized()
    rz = r if rz is None else rz
    bm = P.bm
    n0 = len(bm.faces)

    def ring(c, rr, rrz):
        return [bm.verts.new(c + u * rr * math.cos(2 * math.pi * (k + 0.5) / sides)
                             + v * rrz * math.sin(2 * math.pi * (k + 0.5) / sides)) for k in range(sides)]

    stations = []
    L = (b - a).length
    if flange:
        fr, fl = flange
        fl = min(fl, L * 0.3)
        for t, rr in ((0, fr), (fl, fr), (fl, r), (L - fl, r), (L - fl, fr), (L, fr)):
            stations.append((a + ax * t, rr, rr * rz / r))
    else:
        stations = [(a, r, rz), (b, r, rz)]
    rings = [ring(c, rr, rrz) for c, rr, rrz in stations]
    for p, q in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((p[k], p[j], q[j], q[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    P.tag(n0, m, smooth)


def ring_bezel(P, c, r, rx, ry, w_px, z0, z1, m, segs=40, lip=0.35):
    """A lofted elliptical ring round pixel (c, r): inner radii rx, ry (px), w_px wide, z0..z1, its
    inner and outer top lips chamfered (`lip` of the width)."""
    bm = P.bm
    n0 = len(bm.faces)
    cx, cy = X(c), Y(r)
    prof = [(w_px, z0), (w_px, z1 - (z1 - z0) * 0.3), (w_px * (1 - lip), z1), (w_px * lip, z1),
            (0.0, z1 - (z1 - z0) * 0.3), (0.0, z0)]
    rings = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        ct, st = math.cos(t), math.sin(t)
        ring = []
        for d, z in prof:
            ring.append(bm.verts.new((cx + (rx + d) * ct * PX, cy + (ry + d) * st * PX, z)))
        rings.append(ring)
    k = len(prof)
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % segs]
        for j in range(k):
            jj = (j + 1) % k
            bm.faces.new((a[j], b[j], b[jj], a[jj]))
    P.tag(n0, m, True)


def dome(P, c, r, rx, ry, z0, h, m, segs=32, rings=9, flat_top=0.0):
    """A dome (half ellipsoid) over pixel (c, r), radii rx, ry px, from z0 up h units; closed."""
    bm = P.bm
    n0 = len(bm.faces)
    cx, cy = X(c), Y(r)
    rows = []
    for k in range(rings + 1):
        phi = (math.pi / 2) * k / rings
        s, zf = math.cos(phi), math.sin(phi)
        if k == rings:
            break
        rows.append([bm.verts.new((cx + rx * PX * s * math.cos(2 * math.pi * i / segs),
                                   cy + ry * PX * s * math.sin(2 * math.pi * i / segs), z0 + h * zf))
                     for i in range(segs)])
    top = bm.verts.new((cx, cy, z0 + h))
    for a, b in zip(rows, rows[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for i in range(segs):
        bm.faces.new((rows[-1][i], rows[-1][(i + 1) % segs], top))
    bm.faces.new(list(reversed(rows[0])))
    P.tag(n0, m, True)


# --- the machine -----------------------------------------------------------------------------------------

MZ = 1.1


def machine(coll):
    P = Part(f"{NAME}_machine")
    BODY, DARK, MID, LIGHT, RIB = mat(3), mat(2), mat(4), mat(5), mat(5, "polish")
    RAIL = mat(7, "polish")
    ORB, LENS = mat(116, "glow"), mat(114, "glow")
    SAMPLE = ORB  # faces whose glow takes the sprite's red shade under them (red_glow)

    # Housing: the sprite's machine outline, a chamfered slab low in the heap (rocks bury its right side).
    plinth(P, MACHINE, 0.0, 0.26, 0.8, BODY)

    # Radiator (columns 0-20, rows 21-37): a recessed back plate, a header across the top and the foot,
    # five main fins and thinner fins between them.
    chbox(P, 0, 21.2, 19.6, 37.6, 0.0, 0.31, 0.4, DARK)
    tube(P, (X(0), Y(22.6), 0.40), (X(19.4), Y(22.6), 0.40), 1.4 * PX, MID, sides=10, rz=1.2 * PX,
         flange=(1.8 * PX, 0.6 * PX))
    chbox(P, 0, 35.4, 19.6, 37.6, 0.0, 0.38, 0.5, MID)
    for c in (1.3, 5.3, 9.3, 13.3, 17.3):
        chbox(P, c - 0.85, 23.2, c + 0.85, 36.0, 0.0, 0.47, 0.45, RIB, chz=0.035)
    for c in (3.3, 7.3, 11.3, 15.3):
        chbox(P, c - 0.45, 24.0, c + 0.45, 35.6, 0.0, 0.39, 0.25, BODY, chz=0.02)

    # Block right of the radiator (columns 20-28): chamfered, a pipe across it and one down it.
    chbox(P, 19.6, 21.2, 28.6, 37.0, 0.0, 0.47, 1.0, MID)
    chbox(P, 21.0, 22.6, 27.2, 26.0, 0.40, 0.51, 0.5, LIGHT)
    tube(P, (X(17.0), Y(28.2), 0.47), (X(28.4), Y(28.2), 0.47), 1.0 * PX, RAIL, sides=10, flange=(1.4 * PX, 0.7 * PX))
    tube(P, (X(23.2), Y(29.6), 0.45), (X(23.2), Y(37.6), 0.45), 0.9 * PX, LIGHT, sides=10)

    # The orb's housing: a grey collar on the left, a block on the right with a polished rail.
    plinth(P, [(5, 37), (14, 36), (14, 40), (11, 44), (11, 53), (14, 57), (6, 57), (6, 55),
               (10, 53), (10, 44), (6, 39)], 0.0, 0.40, 0.6, LIGHT)
    plinth(P, [(29, 37), (36, 38), (40, 41), (41, 44), (41, 48), (39, 51), (39, 54),
               (36, 57), (31, 57), (33, 50), (32, 42)], 0.0, 0.48, 0.8, MID)
    tube(P, (X(34.0), Y(41.5), 0.49), (X(34.0), Y(56.0), 0.49), 0.95 * PX, RAIL, sides=10, flange=(1.3 * PX, 0.8 * PX))
    chbox(P, 36.6, 42.0, 40.2, 47.5, 0.30, 0.52, 0.5, DARK)

    # The orb (columns 12-32, rows 39-55): a glowing dome in a machined bezel.
    OC, OR = (22.0, 47.2)
    chbox(P, 11.0, 38.0, 33.0, 56.6, 0.0, 0.30, 0.8, DARK)  # the socket's floor
    ring_bezel(P, OC, OR, 9.7, 7.9, 1.8, 0.24, 0.43, LIGHT)
    dome(P, OC, OR, 9.9, 8.1, 0.26, 0.40, SAMPLE, segs=56, rings=14)

    # Deck under the orb (rows 56-67) with the two red lenses in ring bezels.
    chbox(P, 5.0, 56.0, 35.6, 67.4, 0.0, 0.38, 1.0, BODY)
    chbox(P, 7.0, 57.6, 14.0, 66.0, 0.30, 0.42, 0.5, DARK)
    # the eyes (QA M4): glowing domes on the sprite's own eye pixels (cols 16-19 / 22-27), their faces
    # taking the sprite's red shades (red_glow), a bright core where the sprite's eye burns
    for (c, r, rx, ry) in ((18.3, 63.7, 2.2, 2.4), (25.1, 63.3, 3.0, 3.3)):
        ring_bezel(P, c, r, rx, ry, 0.8, 0.34, 0.45, LIGHT, segs=28)
        dome(P, c, r, rx + 0.1, ry + 0.1, 0.36, 0.13, SAMPLE, segs=28, rings=6)
    tube(P, (X(14.0), Y(58.4), 0.44), (X(33.0), Y(58.4), 0.44), 0.55 * PX, RAIL, sides=8)

    # The coil (columns 17-26, rows 67-84): a lying drum with glowing windings and clamp rings.
    cxc = X(21.5)
    tube(P, (cxc, Y(67.0), 0.30), (cxc, Y(84.2), 0.30), 3.5 * PX, BODY, sides=16, rz=1.4 * PX,
         flange=(3.9 * PX, 0.5 * PX))
    # the jaw (QA M4): the windings on the sprite's red rows (69, 71-74, 77-78, 80-81), glowing in its
    # own red shades (red_glow: the hot 122 in row 72), grey clamp rings on its grey rows (68, 70, 76, 79)
    for r0, r1 in ((68.8, 70.1), (70.9, 75.0), (76.9, 79.0), (79.9, 82.1)):
        tube(P, (cxc, Y(r0), 0.30), (cxc, Y(r1), 0.30), 3.9 * PX, SAMPLE, sides=20, rz=1.8 * PX)
    for r in (68.4, 70.5, 76.3, 79.45, 83.0):
        tube(P, (cxc, Y(r - 0.38), 0.30), (cxc, Y(r + 0.38), 0.30), 4.15 * PX, LIGHT, sides=20, rz=1.97 * PX)

    # Pipes off to the left (rows 67, 70, 73) and one down the right side (column 29).
    tube(P, (X(5.6), Y(67.2), 0.32), (X(11.0), Y(67.2), 0.32), 1.0 * PX, BODY, sides=10, flange=(1.4 * PX, 0.8 * PX))
    tube(P, (X(2.2), Y(70.3), 0.33), (X(15.0), Y(70.3), 0.33), 1.05 * PX, LIGHT, sides=10, flange=(1.45 * PX, 0.8 * PX))
    tube(P, (X(0.55), Y(73.3), 0.31), (X(18.0), Y(73.3), 0.31), 1.0 * PX, MID, sides=10, flange=(1.4 * PX, 0.8 * PX))
    tube(P, (X(29.4), Y(56.5), 0.31), (X(29.4), Y(84.8), 0.31), 1.2 * PX, MID, sides=10, flange=(1.6 * PX, 0.9 * PX))
    # The lower machine: dark blocks, chamfered.
    chbox(P, 0.6, 74.6, 6.0, 85.0, 0.0, 0.32, 0.8, DARK)
    chbox(P, 5.0, 74.6, 11.0, 82.0, 0.0, 0.32, 0.8, DARK)
    chbox(P, 10.6, 74.8, 30.0, 85.0, 0.0, 0.30, 0.8, DARK)
    for r in (77.5, 80.5, 83.5):
        chbox(P, 1.0, r - 0.6, 5.4 if r > 80 else 9.6, r + 0.6, 0.28, 0.36, 0.3, MID, chz=0.02)
    for v in P.bm.verts:  # the machine stands taller than the flat sketch: about 9 px at the orb
        v.co.z *= MZ
    red_glow(P, SAMPLE)
    return P.obj(coll, sharp=35)


def red_field():
    """The sprite's red ramp (112-127) over the machine, as a smooth field: red pixels keep their
    index, the dark ink inside the red parts (1-3) counts as 112, and the rest takes the nearest red
    (a few dilation steps), blurred (sigma 0.35 px) so the bands follow contours, not pixel squares."""
    import numpy as np
    a = np.array(IDX)
    red = (a >= 112) & (a <= 127)
    val = np.where(red, a, np.where((a >= 1) & (a <= 3), 112, 0)).astype(float)
    known = val > 0
    for _ in range(6):
        pad, pm = np.pad(val, 1), np.pad(known, 1)
        acc = np.zeros_like(val)
        cnt = np.zeros_like(val)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                acc += pad[1 + dr:1 + dr + H, 1 + dc:1 + dc + W] * pm[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]
                cnt += pm[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]
        val = np.where(known, val, np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0))
        known = val > 0
    val = np.where(known, val, 114.0)
    k = np.arange(-2, 3)
    g = np.exp(-(k ** 2) / (2 * 0.35 ** 2))
    g /= g.sum()
    val = np.apply_along_axis(lambda r: np.convolve(r, g, mode="same"), 1, np.pad(val, ((0, 0), (2, 2)), mode="edge"))[:, 2:-2]
    val = np.apply_along_axis(lambda c: np.convolve(c, g, mode="same"), 0, np.pad(val, ((2, 2), (0, 0)), mode="edge"))[2:-2, :]
    return val


def red_glow(P, placeholder):
    """Every face on `placeholder` takes the glow of the sprite's red shade under its centre
    (bilinear in red_field), so the orb's swirl, the eyes' hot cores and the coil's lit windings are
    the sprite's own reds, as faces of the parts' meshes (no decals)."""
    field = red_field()
    k = P.slot(placeholder)

    def at(u, v):
        x, y = u - 0.5, v - 0.5
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - x0, y - y0
        acc = 0.0
        for dy, wy in ((0, 1 - fy), (1, fy)):
            for dx, wx in ((0, 1 - fx), (1, fx)):
                r, c = min(max(y0 + dy, 0), H - 1), min(max(x0 + dx, 0), W - 1)
                acc += wy * wx * field[r, c]
        return acc

    used = {}
    for f in P.bm.faces:
        if f.material_index != k:
            continue
        c = f.calc_center_median()
        i = int(round(min(max(at(c.x / PX + W / 2, H / 2 - c.y / PX), 112), 127)))
        if i not in used:
            used[i] = P.slot(mat(i, "rglow"))
        f.material_index = used[i]
    # drop the placeholder slot when no face is left on it
    if not any(f.material_index == k for f in P.bm.faces):
        P.mats.pop(k)
        for f in P.bm.faces:
            if f.material_index > k:
                f.material_index -= 1
    print(f"{NAME}: red glow shades {sorted(used)}")


# --- the boulders ----------------------------------------------------------------------------------------

STONE_BASE = {
    "metallic": 0.0, "roughness": 0.9, "rise": 0.7, "fall": 0.8, "summit_gain": 0.06, "summit_r": 2.4,
    "ridges": [], "valleys": [], "tilt": 0.0, "lumps": 0.02, "grow": 0.4, "smooth": 1, "steps": 48,
    "waist": 0.0, "fine": 1, "fine_depth": (0.03, 0.05), "rim_spalls": 3, "rim_depth": (0.02, 0.035),
    "top_pow": 0.55, "bot_pow": 0.85,
}
CUTS = [(160, 78, 0.10), (20, 74, 0.08), (150, 46, 0.16), (205, 40, 0.13), (110, 52, 0.12),
        (245, 50, 0.12), (10, 44, 0.15), (60, 50, 0.12), (330, 42, 0.14), (290, 56, 0.12)]
RAMP = {"bias": 0.0, "angle": 28.0, "size": 8.0, "sprite": 0.35}  # QA M4: broad, clean faces along the stone's own ramp


class StoneGrid(R.Grid):
    def __init__(self, mask):
        self.w, self.h = W, H
        self.inner = mask


def stones():
    keep = [[INNER[r][c] and not MACH[r][c] for c in range(W)] for r in range(H)]
    own = segment(IDX, keep)
    whole = [[INNER[r][c] for c in range(W)] for r in range(H)]
    dist = depth_map(whole)
    out = []
    for i, seed in enumerate(SEEDS):
        px = [(c, r) for r in range(H) for c in range(W) if own[r][c] == i]
        if len(px) < 5:
            continue
        cu = sum(c + 0.5 for c, _ in px) / len(px)
        cv = sum(r + 0.5 for _, r in px) / len(px)
        vals = sorted((IDX[r][c] for c, r in px if family(IDX[r][c]) is not None), key=lum)
        fams = {}
        for v in vals:
            fams[family(v)] = fams.get(family(v), 0) + 1
        fam = max(fams, key=fams.get)
        fv = [v for v in vals if family(v) == fam]
        k = len(fv) * 15 // 100
        mid_vals = fv[k:len(fv) - k] or fv
        mid = mid_vals[len(mid_vals) // 2]
        thr = sorted(lum(v) for v in fv)[max(0, len(fv) - max(1, len(fv) // 5))]
        lit = [(c + 0.5, r + 0.5) for c, r in px if family(IDX[r][c]) == fam and lum(IDX[r][c]) >= thr]
        bu = sum(p[0] for p in lit) / len(lit) if lit else cu
        bv = sum(p[1] for p in lit) / len(lit) if lit else cv
        d = dist[int(cv)][int(cu)]
        out.append(dict(i=i, px=px, centre=(cu, cv), mid=mid, fam=fam, bright=(bu, bv), depth=d))
    return own, out


def stone_mask(own, i, grow):
    m = [[own[r][c] == i for c in range(W)] for r in range(H)]
    for _ in range(grow):
        m = [[INNER[r][c] and (m[r][c] or any(0 <= r + dr < H and 0 <= c + dc < W and m[r + dr][c + dc]
                                               for dr in (-1, 0, 1) for dc in (-1, 0, 1)))
              for c in range(W)] for r in range(H)]
    return m


def lit_mask(own, i):
    """The stone's pixels without the dark crevice ink between stones (the geometry and the game's ink
    draw those): the facet ramp matches the stone's own shades."""
    m = [[own[r][c] == i and IDX[r][c] not in (1, 160, 161, 66, 80) for c in range(W)] for r in range(H)]
    return m if sum(map(sum, m)) >= 4 else [[own[r][c] == i for c in range(W)] for r in range(H)]


def heap_height(d):
    """The waist height (units) of a stone whose centre lies d px inside the heap."""
    return min(0.55, 0.045 * max(d - 1.5, 0.0))


def build_stone(s, own, coll):
    g = StoneGrid(stone_mask(own, s["i"], 1))
    area = len(s["px"])
    cu, cv = s["centre"]
    bu, bv = s["bright"]
    summit = (cu + 0.35 * (bu - cu), cv + 0.35 * (bv - cv))
    rnd = random.Random(s["i"] * 7 + 3)
    waist = heap_height(s["depth"])
    h_top = min(0.55, 0.10 + 0.032 * math.sqrt(area))
    rot = rnd.uniform(-25, 25)
    spec = dict(STONE_BASE, seed=s["i"] + 1, summit=summit, h_top=h_top, h_bot=waist + 0.1,
                cuts=[((az + rot) % 360, el, dp) for az, el, dp in CUTS if rnd.random() > 0.2])
    sectors = max(12, min(22, int(1.8 * math.sqrt(area))))
    bm, _ = R.rock_body(g, spec, sectors=sectors, rings_top=5, rings_bot=2)
    R.cut_planes(bm, spec["cuts"] + R.fine_cuts(spec))
    R.chip_planes(bm, 6.0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.translate(bm, vec=(0, 0, waist), verts=bm.verts)
    for v in bm.verts:  # flat on the ground: the underside is a plain closed base
        if v.co.z < 0.0:
            v.co.z = 0.0
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    m = mat(s["mid"], "rock")
    o = common.mesh_object(f"{NAME}_stone{s['i']}", bm, [m], coll, smooth=True)
    st = o.data.attributes.new("stone", "INT", "FACE")
    for dd in st.data:
        dd.value = s["i"]
    return o


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = objs[0]
    o.name = o.data.name = name
    # one slot per material
    uniq = []
    for m in o.data.materials:
        if m not in uniq:
            uniq.append(m)
    remap = [uniq.index(m) for m in o.data.materials]
    fm = [remap[p.material_index] for p in o.data.polygons]
    o.data.materials.clear()
    for m in uniq:
        o.data.materials.append(m)
    for p, k in zip(o.data.polygons, fm):
        p.material_index = k
    return o


def build(coll):
    own, info = stones()
    objs = [build_stone(s, own, coll) for s in info]
    mach = machine(coll)
    sattr = mach.data.attributes.new("stone", "INT", "FACE")
    for dd in sattr.data:
        dd.value = -1
    obj = join(objs + [mach], NAME)
    # the facet ramp per stone (D175), on its own region; facet normals set on the pieces after the split
    st = [d.value for d in obj.data.attributes["stone"].data]
    for s in info:
        m = mat(s["mid"], "rock")
        slot = list(obj.data.materials).index(m)
        g = StoneGrid(lit_mask(own, s["i"]))
        R.facet_ramp(SPR, g, obj, dict(STONE_BASE, mid=s["mid"], ramp=RAMP),
                     faces=[k for k, v in enumerate(st) if v == s["i"]], mid=s["mid"], slot=slot, flat={})
    for m in obj.data.materials:
        if m.name.startswith("pal_") and ("-r" in m.name or m.name.endswith(TAG)):
            spec_level(m, 0.15)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Roughness"].default_value = 0.9
            bsdf.inputs["Metallic"].default_value = 0.0
    return obj, info


# --- shell, pieces ----------------------------------------------------------------------------------------

SHELL = dict(R.D90_SHELL, faces=6000, inside=0.008)


def layout():
    out = []
    for j, names in enumerate(ROWS):
        for i, name in enumerate(names):
            out.append((name, 24 * i + 12 - W / 2, 28 * j + 14 - H / 2))
    return out


def split_open(obj, lay, coll):
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


# --- views ---------------------------------------------------------------------------------------------

def setup_render(px, py, engine="EEVEE"):
    scene = bpy.context.scene
    if engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
        scene.view_settings.view_transform = "Standard"
    else:
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = e
                break
            except TypeError:
                pass
        try:
            scene.view_settings.view_transform = "Standard"
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = px, py
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def lights():
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.25, 0.25, 0.28, 1)
    bg.inputs[1].default_value = 0.6
    # the art's light comes from the upper left
    for nm, rot, en in (("key", (math.radians(40), 0, math.radians(135)), 3.5),
                        ("fill", (math.radians(60), 0, math.radians(-40)), 0.8)):
        ld = bpy.data.lights.new(nm, "SUN")
        ld.energy = en
        lo = bpy.data.objects.new(nm, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)


def cam(name, loc, look, ortho=None, lens=50):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_end = 200
    c = bpy.data.objects.new(name, data)
    scene.collection.objects.link(c)
    c.location = loc
    d = Vector(look) - Vector(loc)
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = c
    return c


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def views(out_dir, obj, shell):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH" and o is not obj and o is not shell:
            o.hide_render = True
    shell.hide_render = True
    K = 8
    # 1. top view, palette indices encoded in red (flat), for IoU and region colours
    setup_render(W * K, H * K, "WORKBENCH")
    keep = {m.name: tuple(m.diffuse_color) for m in obj.data.materials}
    for m in obj.data.materials:
        i = int(m.name.split("_")[1])
        s = i / 255
        lin = ((s + 0.055) / 1.055) ** 2.4 if s > 0.04045 else s / 12.92
        m.diffuse_color = (lin, 0, 0, 1)
    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "idx_top.png")
    for m in obj.data.materials:
        m.diffuse_color = keep[m.name]
    # 2. lit views (EEVEE), with the shell drawn as a black inverted hull for the game-camera views
    lights()
    setup_render(W * K, H * K)
    c = cam("top_lit", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "top.png")
    D = 22.0
    vs = {
        "game": (0, -D * math.sin(math.radians(20)), D * math.cos(math.radians(20))),
        "steep": (0, -D * math.sin(math.radians(40)), D * math.cos(math.radians(40))),
        "front": (0, -D, 0.25),
        "rear": (0, D, 0.25),
        "side_w": (-D, 0, 0.25),
        "side_e": (D, 0, 0.25),
        "q_sw": (-D * 0.55, -D * 0.6, D * 0.55),
        "q_se": (D * 0.55, -D * 0.6, D * 0.5),
        "q_nw": (-D * 0.5, D * 0.6, D * 0.55),
        "under": (0, -0.5, -D),
    }
    setup_render(900, 900)
    for nm, loc in vs.items():
        cam(nm, loc, (0, 0, 0.2), lens=100)
        render(out_dir / f"{nm}.png")


def cap_open_ends(obj):
    """Clean the seam caps split_assembly leaves where a part ends right on a piece seam (newshr-199's
    pal 3 box, newshr-237's pal 7 rail tube): its holes_fill there leaves zero-area slivers, a cap
    doubled over the part's own end face and duplicate corners, so the end reads as open once the
    vertices are welded (a piece drawn alone or left after its neighbour is destroyed). Weld the seam
    corners, drop the slivers, keep one outward face of each doubled pair, drop loose sheets left
    lying flat on the seam (a neighbour's end face with no body behind it), then fill what is still
    open (each cap takes the material of a face next to it)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hw, hh, eps = 1.0, 14 / 12, 1e-4

    def on_seam(co):
        return abs(abs(co.x) - hw) < eps or abs(abs(co.y) - hh) < eps

    seam = [v for v in bm.verts if on_seam(v.co)]
    if seam:
        bmesh.ops.remove_doubles(bm, verts=seam, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-6)
    groups = {}
    for f in bm.faces:
        groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
    drop = []
    for fs in groups.values():
        if len(fs) < 2:
            continue
        c = fs[0].calc_center_median()
        out = Vector((math.copysign(1, c.x), 0, 0)) if abs(abs(c.x) - hw) < eps else \
            Vector((0, math.copysign(1, c.y), 0))
        fs.sort(key=lambda f: -f.normal.dot(out))
        drop += fs[1:]
    # a neighbour's end face lying flat on the seam plane survives the bisect as a loose sheet with
    # no body behind it: drop such seam sheets (every edge open)
    stray = [f for f in bm.faces if f not in drop and all(on_seam(v.co) for v in f.verts)
             and all(len(e.link_faces) == 1 or all(g in drop or all(on_seam(v.co) for v in g.verts)
                                                   for g in e.link_faces) for e in f.edges)]
    stray = [f for f in stray if all(all(g in stray or g in drop for g in e.link_faces) for e in f.edges)]
    drop += stray
    if drop:
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        mat_of = {}
        for e in edges:
            for v in e.verts:
                mat_of[v] = e.link_faces[0].material_index
        new = bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]
        for f in new:
            f.material_index = next((mat_of[v] for v in f.verts if v in mat_of), f.material_index)
        if new:
            bmesh.ops.triangulate(bm, faces=new)
    left = sum(1 for e in bm.edges if e.is_boundary)
    if seam or drop or edges:
        print(f"{obj.name}: seam welded {len(seam)} verts, dropped {len(drop)} doubled or loose seam faces, "
              f"capped {len(edges)} open edges, {left} left")
    bm.to_mesh(obj.data)
    bm.free()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    obj, info = build(coll)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(info)} stones, {tris} triangles, non-manifold edges {open_edges}")
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, **SHELL)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    bpy.context.view_layer.update()
    lay = layout()
    pieces = common.split_assembly(obj, lay)
    for q in pieces.values():
        cap_open_ends(q)
    for q in pieces.values():
        q.data.set_sharp_from_angle(angle=math.radians(35))
        R.set_facet_normals(q)
    shells = split_open(shell, lay, coll)
    for name, _, _ in lay:
        print(f"{name}: {sum(len(p.vertices) - 2 for p in pieces[name].data.polygons)} triangles")
    for name, _, _ in lay:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    for o in list(pieces.values()) + list(shells.values()):
        o.hide_render = True
    if "--views" in argv:
        R.set_facet_normals(obj)
        views(argv[argv.index("--views") + 1], obj, shell)


if __name__ == "__main__":
    main()
