"""Blue-pipe machine (newshb.shp, assembly of 15 pieces, CAMANIS boss middle body), D65 hard surface.

Balance of sprite fidelity, game-camera readability and engineering. Built once in assembly
coordinates (pixel edges, col 0..120, row 0..84; Blender origin at the assembly centre (60, 42)),
left half mirrored about the pipes' axis (col 59.5): the sprite's dark right half is its lighting.

Parts (concept + sprite agree):
  * two fat steel-blue pipes (satin, round) from the top edge (where newshb-2's pod housings take them)
    down to row ~44, bending into one heart-shaped manifold on the deck; seam rings; machined ends
    (flange lip, ten-bolt face, recessed cap with a hub) seen from the rear;
  * a grey grille clamp saddled over each pipe (a curved body with six chamfered riveted tiles and
    two straps), a ribbed canister lying on each pipe's outer shoulder, a thin rod along its top;
  * an arched lamp housing beside each pipe: navy chamfered frame, domed glowing blue lens;
  * two antenna booms each side (masts with chamfered housings, a side knob), cantilevered forward
    from the deck;
  * the round deck: a tapered hull, lavender wing bevel with three ribs, a bright rib, grey plates
    with real panel gaps, the riveted post plate, the gun port housing (hatch / flashes per frame),
    a curved two-rail track, slatted vents, the stepped block inside the heart over a navy floor.

Run: blender --background --python assets/blender/enemies/assembly-newshb-115.py
Finish: cull hidden faces, weighted normals, the AO/roughness bake (lib_b119.bake_maps, "--no-bake"
skips it; the per-frame hatch/flash extras keep unbaked material copies), an outline shell from a
sealed pre-cull copy. Exports each of the 15 pieces (newshb-117 in its hatch variants) to
public/models/enemies/ with the sprite entries in src/render/spriteModels/, each with its outline
shell (D90/D118).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b119  # noqa: E402  (bake_maps: the item's shared AO/roughness bake)
import usp_talon as T  # noqa: E402

NAME = "assembly-newshb-115"
TAG = "nshb115A"
PX = 1 / 12
W, H = 120, 84
AXIS = 59.5
PIECES = ["newshb-39", "newshb-41", "newshb-43", "newshb-45", "newshb-47",
          "newshb-77", "newshb-79", "newshb-81", "newshb-83", "newshb-85",
          "newshb-115", "newshb-117", "newshb-119", "newshb-121", "newshb-123"]
CX0, CY0 = 223, 11  # screen point of the assembly centre (col 60, row 42)


def X(c):
    return (c - 60.0) * PX


def Y(r):
    return (42.0 - r) * PX


def V(c, r, z):
    return Vector((X(c), Y(r), z))


def mirror_col(c):
    return 2 * AXIS - c


# --- materials -----------------------------------------------------------------------------------

(BASE, COLLAR, RIB, LAV, PURP, PIPE, LOOP, POOL, CLAMP, TILE, SHAFT, LAMP, HOT, PORT, EMBER, FLASH,
 CORE, TOWER, DARK, POST, LAMP2, DIM, LAVD, BLOCK, CLAMPB) = range(25)
# Slots that take the AO/roughness bake (D53/D65); the glows stay plain.
TEXTURED = (BASE, COLLAR, RIB, LAV, PURP, PIPE, LOOP, POOL, CLAMP, TILE, SHAFT, PORT, TOWER, DARK, POST, LAVD, BLOCK,
            CLAMPB)
SPEC = {PIPE: 0.5, LOOP: 0.5, TILE: 0.6, COLLAR: 0.6, RIB: 0.6}


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.5),   # BASE hull sides, lower deck
        pal(9, metallic=0.5, roughness=0.42),   # COLLAR deck plating (lit median 9)
        pal(10, metallic=0.5, roughness=0.4),   # RIB raised strip, rails, hatch
        pal(89, metallic=0.3, roughness=0.5),   # LAV lavender wing (lit median 89)
        pal(84, metallic=0.3, roughness=0.55),  # PURP purple corner plates (84)
        pal(52, metallic=0.35, roughness=0.42),  # PIPE steel-blue pipes, satin (blue median 51, lit mean 53-54: 52)
        pal(52, metallic=0.35, roughness=0.38),  # LOOP manifold, satin (as the pipes)
        pal(52, metallic=0.6, roughness=0.4),   # POOL navy floor in the heart (52)
        pal(3, metallic=0.55, roughness=0.55),  # CLAMP dark grey clamp body (gaps), slats
        pal(5, metallic=0.55, roughness=0.42),  # TILE grey tiles, canister discs (5)
        pal(7, metallic=0.55, roughness=0.45),  # SHAFT masts
        pal(148, metallic=1.0, roughness=0.9, emission_strength=2.0),  # LAMP lens (148; glow D126/D173)
        pal(155, metallic=1.0, roughness=0.9, emission_strength=1.6),  # HOT lens core
        pal(2, metallic=0.2, roughness=0.8),    # PORT port interior, vent wells
        pal(116, metallic=1.0, roughness=0.9, emission_strength=2.0),  # EMBER
        pal(120, metallic=1.0, roughness=0.9, emission_strength=3.0),  # FLASH
        pal(126, metallic=1.0, roughness=0.9, emission_strength=4.0),  # CORE
        pal(5, metallic=0.55, roughness=0.45),  # TOWER housings (same index as TILE)
        pal(3, metallic=0.5, roughness=0.6),    # DARK lamp frame, vent wells, rod
        pal(91, metallic=0.3, roughness=0.5),   # POST light lavender post (91)
        pal(152, metallic=1.0, roughness=0.9, emission_strength=2.2),  # LAMP2 bright upper lens
        pal(113, metallic=1.0, roughness=0.9, emission_strength=1.5),  # DIM flash
        pal(90, metallic=0.3, roughness=0.5),   # LAVD wing ribs and inner rim (90)
        pal(4, metallic=0.55, roughness=0.5),   # BLOCK stepped block, tower housings (4)
        pal(6, metallic=0.55, roughness=0.5),   # CLAMPB grille clamp body (6)
    ]
    for i, k in SPEC.items():
        b = next(n for n in mats[i].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = k
    return mats


# --- mesh builder ----------------------------------------------------------------------------------

class M:
    """A bmesh with a material and a 'part' tag per face (the part tag is for the region check)."""

    def __init__(self):
        self.bm = bmesh.new()
        self.part = self.bm.faces.layers.int.new("part")
        self.cur = 0
        self.names = []

    def tag(self, name):
        if name not in self.names:
            self.names.append(name)
        self.cur = self.names.index(name)

    def face(self, verts, mat):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        f[self.part] = self.cur
        return f

    def nv(self, p):
        return self.bm.verts.new(p)

    def mark(self):
        return len(self.bm.verts)

    def mirror_since(self, n):
        bm = self.bm
        bm.verts.ensure_lookup_table()
        verts = bm.verts[n:]
        faces = list({f for v in verts for f in v.link_faces})
        edges = list({e for v in verts for e in v.link_edges})
        dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
        ax = X(AXIS)
        for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
            v.co.x = 2 * ax - v.co.x
        bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def rings_faces(m, rings, mat, cap0=True, cap1=True, mats=None):
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        n = len(a)
        mt = mats[i] if mats else mat
        for k in range(n):
            j = (k + 1) % n
            m.face((a[k], a[j], b[j], b[k]), mt)
    if cap0:
        m.face(list(reversed(rings[0])), mats[0] if mats else mat)
    if cap1:
        m.face(rings[-1], mats[-1] if mats else mat)


def area2(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def inset(pts, d):
    """Offset a CCW (x, y) polygon inward by d (miter, clamped)."""
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
        cs = max(0.4, b.dot(n1))
        q = p1 + b * (d / cs)
        out.append((q.x, q.y))
    return out


def inset_px(outline_px, d_px):
    pts = [(X(c), Y(r)) for c, r in outline_px]
    flip = area2(pts) < 0
    if flip:
        pts = pts[::-1]
    out = [(x / PX + 60.0, 42.0 - y / PX) for x, y in inset(pts, d_px * PX)]
    return out[::-1] if flip else out


def dedupe(pts, eps=1e-4):
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps):
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def slab(m, outline_px, z0, z1, mat, ch=0.03, chb=0.0, top_mat=None, bot_mat=None, z1s=None):
    """A chamfered block over an outline of (col, row) edges: sides from z0 up to z1 - ch, a 45 degree
    chamfer to a top inset by ch (units). chb insets the bottom (a tapered underside).
    z1s: optional per-point top heights (sloped top)."""
    pts = dedupe([(X(c), Y(r)) for c, r in outline_px])
    tops = list(z1s) if z1s else [z1] * len(pts)
    if area2(pts) < 0:
        pts, tops = pts[::-1], tops[::-1]
    rings = []
    if chb > 0:
        rings.append([m.nv((x, y, z0)) for x, y in inset(pts, chb)])
        rings.append([m.nv((x, y, z0 + chb * 0.8)) for x, y in pts])
    else:
        rings.append([m.nv((x, y, z0)) for x, y in pts])
    if ch > 0:
        rings.append([m.nv((x, y, t - ch)) for (x, y), t in zip(pts, tops)])
        rings.append([m.nv((x, y, t)) for (x, y), t in zip(inset(pts, ch), tops)])
    else:
        rings.append([m.nv((x, y, t)) for (x, y), t in zip(pts, tops)])
    mats = [mat] * (len(rings) - 1)
    rings_faces(m, rings, mat, cap0=False, cap1=False, mats=mats)
    m.face(list(reversed(rings[0])), bot_mat if bot_mat is not None else mat)
    m.face(rings[-1], top_mat if top_mat is not None else mat)


def dome_slab(m, outline_px, z0, z1, rise, mat, steps=4, shrink=0.6):
    """A lens: sides z0..z1, then a rounded top rising `rise` over `steps` inset rings (shrink px)."""
    pts = dedupe([(X(c), Y(r)) for c, r in outline_px])
    if area2(pts) < 0:
        pts = pts[::-1]
    rings = [[m.nv((x, y, z0)) for x, y in pts], [m.nv((x, y, z1)) for x, y in pts]]
    for k in range(1, steps + 1):
        a = k / steps * math.pi / 2
        d = shrink * PX * (1 - math.cos(a)) * 2.2
        rings.append([m.nv((x, y, z1 + rise * math.sin(a))) for x, y in inset(pts, d)])
    rings_faces(m, rings, mat, cap0=True, cap1=True)


def chbox(m, c0, r0, c1, r1, z0, z1, mat, ch=0.3, chz=None, top_mat=None):
    """A box with chamfered vertical corners (ch px) and top edges (chz units)."""
    chz = ch * PX if chz is None else chz
    o = [(c0 + ch, r0), (c1 - ch, r0), (c1, r0 + ch), (c1, r1 - ch), (c1 - ch, r1), (c0 + ch, r1), (c0, r1 - ch),
         (c0, r0 + ch)]
    slab(m, o, z0, z1, mat, ch=chz, top_mat=top_mat)


def lathe(m, col, prof, mat, sides=16, cap0=True, cap1=True, mats=None):
    """A solid of revolution about an axis down the sprite at column col: prof = [(row, radius_px,
    axis_z)] (radius 0 = a point)."""
    rings = []
    for r, rad, z in prof:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(m.nv((X(col) + math.cos(a) * rad * PX, Y(r), z + math.sin(a) * rad * PX)))
        rings.append(ring)
    rings_faces(m, rings, mat, cap0, cap1, mats=mats)


def xcyl(m, c0, c1, row, z, rad, mat, sides=10):
    rings = []
    for c in (c0, c0 + 0.25, c1 - 0.25, c1):
        rr = rad - (0.25 if c in (c0, c1) else 0.0)
        rings.append([m.nv((X(c), Y(row) + math.cos(2 * math.pi * (k + 0.5) / sides) * rr * PX,
                            z + math.sin(2 * math.pi * (k + 0.5) / sides) * rr * PX)) for k in range(sides)])
    rings_faces(m, rings, mat)


def tube(m, pts, radius, mat, sides=24, squash=1.0, cap0=True, cap1=True):
    """A round pipe along (col, row, z) points with parallel-transported rings."""
    radii = list(radius) if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    P = [V(c, r, z) for c, r, z in pts]
    n = len(P)
    tans = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((0, 0, 1))
    u = (ref - tans[0] * ref.dot(tans[0])).normalized()
    rings = []
    for i in range(n):
        if i:
            u = (u - tans[i] * u.dot(tans[i])).normalized()
        v = tans[i].cross(u)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            off = (u * math.cos(a) + v * math.sin(a)) * radii[i]
            off.z *= squash
            ring.append(m.nv(P[i] + off))
        rings.append(ring)
    rings_faces(m, rings, mat, cap0, cap1)


def spline(pts, per=6):
    """Open Catmull-Rom through (col, row, z) points."""
    m = len(pts)
    out = []
    for i in range(m - 1):
        p0, p1, p2, p3 = (pts[max(0, min(m - 1, i + k))] for k in (-1, 0, 1, 2))
        for s in range(per):
            t = s / per
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                                    + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for i in range(len(xs) - 1):
        if x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + (ys[i + 1] - ys[i]) * t
    return ys[-1]


# --- shape data (pixel edges) ----------------------------------------------------------------------

PIPE_COL, PIPE_W = 43.0, 10.6         # big pipe centre column and half width (px)
PIPE_R = PIPE_W * PX                  # radius (units)
PIPE_Z = PIPE_R + 0.01                # axis height
# The pipe's centre line, top edge down into the manifold (left half; the right half is mirrored).
DOWN = [(PIPE_COL, 0.0), (PIPE_COL, 30.0), (PIPE_COL, 38.0), (41.9, 44.0), (39.8, 50.0), (38.3, 56.0),
        (38.1, 61.5), (39.6, 66.0), (42.9, 69.0), (47.5, 70.6), (53.5, 70.9), (AXIS, 71.0)]
LOBE = [(41.0, 49.4), (45.0, 49.1), (49.5, 49.2), (54.0, 50.0), (57.5, 51.0), (AXIS, 51.4)]
LOBE_W, LOBE_SQ = 4.6, 1.35
DECK = 0.62          # deck plate tops
HULL = 0.40          # hull slab top (under the wing bevel and plates)
PORT_L = (25.0, 59.0, 33.0, 68.0)
DZ = DECK - 0.18     # port/hatch/flash heights follow the deck
# newshb-117's hatch states: (model, frames, the hatch's left edge or None when open). The models are
# named in full so tools/inventory.mjs counts their frames as this assembly's.
HATCH = [("newshb-117", [117], 25.0), ("newshb-117-f2", [195], 27.0), ("newshb-117-f3", [233], 29.0),
         ("newshb-117-f4", [197, 235, 271, 273], None)]
HATCH_271 = 31.0
FLASH_117 = (28.6, 63.4, {197: [(EMBER, 1.8)], 235: [(FLASH, 3.2), (CORE, 1.6)], 271: [(DIM, 1.2)],
                          273: [(FLASH, 3.6), (CORE, 2.6)]})
FLASH_121 = (91.4, 63.4, {199: [(DIM, 1.6)], 201: [(FLASH, 3.8), (CORE, 2.4)], 237: [(EMBER, 2.4), (FLASH, 1.2)],
                          275: [(FLASH, 3.0), (CORE, 1.6)]})

EDGE_C = [3.0, 4.6, 17.5, 33.0, 37.0, 41.8, 46.0]
EDGE_R = [47.4, 46.3, 45.3, 38.5, 38.5, 44.0, 49.0]


def edge_row(c):
    """Row of the deck's upper (diagonal) edge at column c."""
    return interp(EDGE_C, EDGE_R, c)


def centre_col(r):
    """Column of the pipe/manifold centre line at row r (left half)."""
    cs = [c for c, _ in DOWN]
    rs = [r_ for _, r_ in DOWN]
    return interp(rs, cs, r)


def pipe_top(c, grow=0.0):
    t = (c - PIPE_COL) / PIPE_W
    return PIPE_Z + (PIPE_R + grow) * math.sqrt(max(0.0, 1.0 - t * t))


def plate_poly(c0, r0, c1, r1, gap=0.15):
    """Deck plate: the box [c0, c1] x [r0, r1], below the deck's upper edge and left of the manifold
    centre line (the manifold covers the rest), with a `gap` px panel line kept free round it."""
    def right(r):
        return min(c1, centre_col(r) if r < 71.0 else 999.0) - gap

    def top(c):
        return max(r0, edge_row(c) + gap)
    pts = []
    c = c0
    while True:
        rt = top(c)
        if c >= right(rt) or c >= c1 - gap:
            break
        pts.append((c, rt))
        c += 0.5
    rt = top(c)
    cr = min(c, right(rt))
    pts.append((cr, rt))
    r = rt + 0.5
    while r < r1:
        pts.append((right(r), r))
        r += 0.75
    pts.append((right(r1), r1))
    pts.append((c0, r1))
    return dedupe(pts, 1e-3)


# --- the left half (mirrored) ------------------------------------------------------------------------

RIM = [(4.3, 52.6), (4.6, 58.0), (5.6, 64.0), (7.6, 70.0), (10.2, 76.0), (13.0, 81.0), (15.4, 84.6)]


def build_deck_half(m):
    m.tag("hull")
    # Hull slab: the round deck's body, tapered underneath (a closed, plain underside).
    top_edge = [(c, edge_row(c)) for c in (17.5, 25.0, 33.0, 37.0)]
    rim = [(c, r, 0) for c, r in RIM]
    rim = [(c, r) for c, r, _ in spline(rim, per=4)]
    outline = [(AXIS, 46.0), (41.8, 44.0)] + top_edge[::-1] + [(5.2, 46.6), (4.4, 48.2)] + rim + [(AXIS, 84.6)]
    slab(m, outline, 0.0, HULL, BASE, ch=0.03, chb=0.22)
    # Lavender wing: a bevel rising from the rim to column 16, three raised ribs across it.
    m.tag("wing")
    wing_o = [(5.4, 47.3), (5.0, 49.0)] + [(c + 0.6, r) for c, r in rim]
    wing_o = [(c, r) for c, r in wing_o if r <= 84.6 and c < 15.4]

    def wz(c):
        return HULL + 0.06 + (min(c, 16.0) - 4.0) / 12.0 * (DECK - HULL - 0.04)
    outline = [(16.0, 45.6)] + [(c, r) for c, r in wing_o] + [(16.0, 84.6)]
    tops = [wz(c) for c, _ in outline]
    slab(m, outline, HULL - 0.05, 0, LAV, ch=0.015, z1s=tops)
    for r0, r1 in ((55.0, 55.9), (56.4, 57.3), (57.8, 58.7)):
        cl = interp([r for _, r in wing_o], [c for c, _ in wing_o], r0) + 1.0
        o = [(cl, r0), (15.8, r0), (15.8, r1), (cl, r1)]
        slab(m, o, HULL, 0, LAVD, ch=0.012, z1s=[wz(c) + 0.04 for c, _ in o])
    # Lavender rim strip along the wing's inner edge (the sprite's bright 90/91 column).
    m.tag("rib")
    slab(m, [(16.0, 45.4), (17.1, 44.9), (17.1, 84.6), (16.0, 84.6)], HULL - 0.02, DECK + 0.03, LAVD, ch=0.02)
    # Deck plates with real panel gaps.
    m.tag("deck")
    for c0, r0, c1, r1, top in ((17.4, 40.0, 21.7, 84.6, DECK + 0.03),   # raised strip by the rib
                                (22.0, 38.0, 99.0, 57.0, DECK),          # plate round the post (under the pipe)
                                (22.0, 57.3, 99.0, 69.6, DECK),          # plate with the gun port
                                (22.0, 69.9, AXIS - 0.15, 84.6, DECK)):  # lower plate, round the manifold
        slab(m, plate_poly(c0, r0, c1, r1), HULL - 0.02, top, COLLAR, ch=0.018)
    # Rivets along the strip and round the post plate (tiny chamfered studs).
    for r in (50.0, 56.0, 62.0, 68.0, 74.0, 80.0):
        chbox(m, 18.9, r, 20.1, r + 1.0, DECK, DECK + 0.055, TILE, ch=0.3, chz=0.015)
    # Lavender post on its plate.
    m.tag("post")
    po = [(26.2, edge_row(26.2) + 0.8), (31.2, edge_row(31.2) + 0.8), (31.2, 55.2), (26.2, 55.2)]
    slab(m, po, DECK - 0.02, DECK + 0.13, POST, ch=0.03)
    # Gun port housing: a chamfered collar standing proud, the dark well inside (hatch per frame).
    m.tag("port")
    c0, r0, c1, r1 = PORT_L
    top = 0.28 + DZ
    for o in ([(c0 - 1.1, r0 - 1.5), (c1 + 1.1, r0 - 1.5), (c1 + 1.1, r0), (c0 - 1.1, r0)],
              [(c0 - 1.1, r1), (c1 + 1.1, r1), (c1 + 1.1, r1 + 1.3), (c0 - 1.1, r1 + 1.3)],
              [(c0 - 1.1, r0), (c0, r0), (c0, r1), (c0 - 1.1, r1)],
              [(c1, r0), (c1 + 1.1, r0), (c1 + 1.1, r1), (c1, r1)]):
        slab(m, o, DECK - 0.02, top, COLLAR, ch=0.02)
    slab(m, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], DECK - 0.02, 0.19 + DZ, PORT, ch=0.0)
    # Slatted vent left of the port.
    m.tag("vent")
    slab(m, [(21.9, 60.3), (23.9, 60.3), (23.9, 67.7), (21.9, 67.7)], HULL, DECK + 0.035, DARK, ch=0.0)
    for k in range(6):
        r = 60.7 + 1.15 * k
        chbox(m, 22.1, r, 23.7, r + 0.6, DECK - 0.03, DECK + 0.02, CLAMP, ch=0.15, chz=0.01)
    # Curved track: two raised rails round the manifold.
    m.tag("track")
    def arc_strip(ra, rb, z1, mat, ch):
        angs = [160.0 - 50.0 * k / 16 for k in range(17)]
        a_pts = [(52.5 + ra * math.cos(math.radians(a)), 58.0 + ra * math.sin(math.radians(a))) for a in angs]
        b_pts = [(52.5 + rb * math.cos(math.radians(a)), 58.0 + rb * math.sin(math.radians(a))) for a in angs]
        keep = [i for i in range(17) if a_pts[i][1] <= 84.6 and b_pts[i][1] <= 84.6]
        o = [a_pts[i] for i in keep] + [b_pts[i] for i in reversed(keep)]
        slab(m, o, DECK - 0.03, z1, mat, ch=ch)
    # the sunken band between the rails (darker plating, the sprite's 7), the rails proud of it
    arc_strip(26.3, 29.3, DECK + 0.012, SHAFT, 0.006)
    for ra in (25.7, 29.2):
        arc_strip(ra, ra + 0.7, DECK + 0.045, RIB, 0.012)
    # Lamp housing beside the pipe: navy chamfered arch, a domed glowing lens.
    m.tag("lamp_house")
    house = [(32.4, 19.2), (30.6, 19.4), (29.1, 20.4), (28.0, 21.8), (26.9, 23.7), (26.0, 25.8), (25.1, 28.3),
             (24.4, 31.2), (23.9, 34.3), (23.8, edge_row(23.8) + 1.2), (32.4, edge_row(32.4) + 1.2)]
    slab(m, house, 0.0, 0.88, DARK, ch=0.06, chb=0.06)
    m.tag("lamp")
    glass = inset_px(house, 0.55)
    dome_slab(m, glass, 0.60, 0.84, 0.12, LAMP, steps=4, shrink=0.9)
    upper = [(31.3, 20.9), (30.5, 21.1), (29.5, 21.9), (28.6, 23.1), (27.7, 25.0), (26.9, 27.0), (26.2, 29.2),
             (25.9, 31.0), (31.3, 31.0)]
    dome_slab(m, upper, 0.80, 0.912, 0.03, LAMP2, steps=3, shrink=0.8)
    hot = [(27.4, 24.6), (28.4, 23.6), (29.4, 24.0), (29.6, 26.6), (28.6, 28.4), (27.4, 28.0), (27.0, 26.4)]
    dome_slab(m, hot, 0.90, 0.945, 0.006, HOT, steps=2, shrink=0.5)
    # Grille clamp saddled over the pipe: a curved dark body with six chamfered tiles, two straps.
    m.tag("clamp")
    arc_band(m, 35.4, 47.6, 0.0, 18.4, PIPE_W - 0.3, PIPE_W + 0.9, CLAMPB, ch=0.5)
    m.tag("tiles")
    for r0, r1 in ((0.3, 5.3), (6.3, 10.9), (11.8, 17.8)):
        for cc0, cc1 in ((35.8, 41.1), (41.9, 47.2)):
            arc_band(m, cc0, cc1, r0, r1, PIPE_W + 0.6, PIPE_W + 1.6, TILE, ch=0.45)
            for rc in (r0 + 0.9, r1 - 0.9):  # rivet heads
                for cc in (cc0 + 0.9, cc1 - 0.9):
                    z = pipe_top(cc, 1.6 * PX)
                    chbox(m, cc - 0.35, rc - 0.35, cc + 0.35, rc + 0.35, z - 0.03, z + 0.03, CLAMP, ch=0.15, chz=0.01)
    m.tag("strap")
    for r0, r1 in ((5.45, 6.75), (11.0, 12.25)):
        lathe(m, PIPE_COL, [(r0, PIPE_W - 0.1, PIPE_Z), (r0 + 0.2, PIPE_W + 0.3, PIPE_Z), (r1 - 0.2, PIPE_W + 0.3, PIPE_Z),
                            (r1, PIPE_W - 0.1, PIPE_Z)], PIPE, sides=32)
    # Pipe flange at the top edge (where newshb-2 takes the pipe) and a seam ring (row 27).
    m.tag("flange")
    # the end (seen from the rear): a chamfered flange lip, a bolt face with ten hex bolts, a bevel
    # into a recessed cap and a raised hub, all inside row 0 (newshb-2's pod takes it there)
    W_ = PIPE_W
    lathe(m, PIPE_COL, [(1.6, W_, PIPE_Z), (1.2, W_ + 0.3, PIPE_Z), (0.25, W_ + 0.3, PIPE_Z), (0.06, W_ + 0.1, PIPE_Z),
                        (0.06, W_ - 0.25, PIPE_Z), (0.3, W_ - 0.5, PIPE_Z), (0.3, W_ - 1.45, PIPE_Z),
                        (0.85, W_ - 1.8, PIPE_Z), (0.85, 3.1, PIPE_Z), (0.4, 2.8, PIPE_Z), (0.2, 2.3, PIPE_Z),
                        (0.2, 0.0, PIPE_Z)], PIPE, sides=32, cap0=False, cap1=False,
          mats=[PIPE, PIPE, PIPE, PIPE, TILE, TILE, TILE, DARK, TILE, TILE, TILE])
    for k in range(10):
        a = 2 * math.pi * (k + 0.5) / 10
        bc, bz = PIPE_COL + math.cos(a) * (W_ - 0.95), PIPE_Z + math.sin(a) * (W_ - 0.95) * PX
        lathe(m, bc, [(0.32, 0.38, bz), (0.12, 0.38, bz), (0.05, 0.25, bz), (0.05, 0.0, bz)], TILE, sides=6,
              cap0=True, cap1=False)
    lathe(m, PIPE_COL, [(26.4, PIPE_W, PIPE_Z), (26.7, PIPE_W + 0.35, PIPE_Z), (27.5, PIPE_W + 0.35, PIPE_Z),
                        (27.8, PIPE_W, PIPE_Z)], PIPE, sides=32)
    # Ribbed canister on the pipe's outer shoulder: grey discs on a dark rod, a plain sleeve.
    m.tag("canister")
    z = pipe_top(37.6) + 0.06
    prof = [(29.4, 0.0, z), (29.4, 1.5, z), (29.6, 1.8, z)]
    for k in range(6):
        r = 30.0 + 1.4 * k
        prof += [(r, 1.8, z), (r, 2.25, z), (r + 0.15, 2.6, z), (r + 0.7, 2.6, z), (r + 0.85, 2.25, z),
                 (r + 0.85, 1.8, z)]
    prof += [(38.6, 1.8, z), (38.6, 2.3, z), (38.75, 2.5, z), (41.8, 2.5, z), (42.1, 2.1, z), (42.1, 0.0, z)]
    mats = []
    for (a, ra, _), (b, rb, _) in zip(prof, prof[1:]):
        mats.append(TILE if max(ra, rb) > 2.0 else CLAMP)
    lathe(m, 37.6, prof, TILE, sides=14, cap0=False, cap1=False, mats=mats)
    # Thin rod along the pipe's top with a small clamp block.
    m.tag("rod")
    zr = pipe_top(44.6) + 0.035
    lathe(m, 44.6, [(17.6, 0.0, zr), (17.6, 0.45, zr), (43.0, 0.45, zr), (43.0, 0.0, zr)], DARK, sides=8)
    chbox(m, 43.8, 26.0, 45.4, 27.5, zr - 0.06, zr + 0.06, TILE, ch=0.25, chz=0.015)
    # The bay between the pipes: a bevelled frame strip and a small pipe along the pipe's inner side.
    m.tag("bay")
    # a small service pipe along the big pipe's inner flank, on two brackets
    lathe(m, 54.3, [(15.0, 0.0, 0.42), (15.0, 0.45, 0.42), (15.3, 0.6, 0.42), (31.3, 0.6, 0.42), (31.6, 0.45, 0.42),
                    (31.6, 0.0, 0.42)], TILE, sides=10)
    for rb in (17.0, 29.0):
        chbox(m, 51.0, rb, 54.9, rb + 1.4, 0.0, 0.40, CLAMP, ch=0.3, chz=0.02)  # into the pipe: welded
    # Purple plate reaching in from the top corner, its outer corner rounded.
    m.tag("purple")
    # (its inner edge runs on under the pipe, to column 40, so it is a bracket welded to the pipe's
    # underside, not a loose plate; hidden from above by the pipe)
    slab(m, [(22.6, 0.0), (40.0, 0.0), (40.0, 7.5), (29.8, 7.5), (27.8, 6.4), (25.9, 4.6), (24.3, 2.5), (23.2, 0.8)],
         0.0, 0.40, PURP, ch=0.04, chb=0.04)


def arc_band(m, c0, c1, r0, r1, R0, R1, mat, ch=0.4, n=12):
    """A curved band saddled over the big pipe from column c0 to c1 and row r0 to r1, between radii
    R0 and R1 (px) about the pipe axis, its row ends and side edges chamfered (ch px)."""
    def section(r, cs0, cs1, rout):
        pts = []
        for k in range(n + 1):
            c = cs0 + (cs1 - cs0) * k / n
            dx = c - PIPE_COL
            pts.append((X(c), PIPE_Z + math.sqrt(max(0.0, rout * rout - dx * dx)) * PX))
        for k in range(n + 1):
            c = cs1 - (cs1 - cs0) * k / n
            dx = c - PIPE_COL
            pts.append((X(c), PIPE_Z + math.sqrt(max(0.0, R0 * R0 - dx * dx)) * PX))
        return [m.nv((x, Y(r), z)) for x, z in pts]
    rings = [section(r0, c0 + ch, c1 - ch, R1 - ch), section(r0 + ch, c0, c1, R1),
             section(r1 - ch, c0, c1, R1), section(r1, c0 + ch, c1 - ch, R1 - ch)]
    rings_faces(m, rings, mat)


def tower(m, col, parts, z_of, knob):
    """An antenna boom lying down the sprite, leaning back: parts are (kind, first row, last row, half
    width px at each end[, dcol]) from its tip down to its foot; "mast" a round rod with collars,
    "box" a chamfered housing (section: a rectangle with 30% chamfers)."""
    for kind, r0, r1, w0, w1, *dc in parts:
        c = col + (dc[0] if dc else 0.0)
        if kind == "mast":
            prof = [(r0 - 0.05, 0.0, z_of(r0)), (r0 - 0.05, w0 * 0.8, z_of(r0))]
            rr = r0 + 0.6
            while rr < r1 - 0.6:
                prof.append((rr, w0 * 0.8, z_of(rr)))
                rr += 1.6
            prof += [(r1 + 0.05, w1 * 0.8, z_of(r1)), (r1 + 0.05, 0.0, z_of(r1))]
            lathe(m, c, prof, SHAFT, sides=8)
            for k in range(1, int((r1 - r0) // 3.0) + 1):  # collars
                rc = r0 + k * (r1 - r0) / (int((r1 - r0) // 3.0) + 1)
                lathe(m, c, [(rc - 0.3, w0 * 0.8, z_of(rc)), (rc - 0.15, w0 + 0.15, z_of(rc)),
                             (rc + 0.15, w0 + 0.15, z_of(rc)), (rc + 0.3, w0 * 0.8, z_of(rc))], TILE, sides=8)
        else:
            def sec(r, w, inset_px=0.0):
                h = w * 0.85 * PX
                ww = (w - inset_px) * PX
                hh = h - inset_px * PX
                ch = 0.3 * min(ww, hh)
                z = z_of(r)
                pts = [(ww, -hh + ch), (ww, hh - ch), (ww - ch, hh), (-ww + ch, hh), (-ww, hh - ch), (-ww, -hh + ch),
                       (-ww + ch, -hh), (ww - ch, -hh)]
                return [m.nv((X(c) + x, Y(r), z + zz)) for x, zz in pts]
            e = min(0.35, (r1 - r0) / 4)
            rings = [sec(r0, w0, 0.35), sec(r0 + e, w0), sec(r1 - e, w1), sec(r1, w1, 0.35)]
            rings_faces(m, rings, BLOCK)
            # panel groove: a raised band at mid-length
            if r1 - r0 > 6:
                rm = (r0 + r1) / 2
                rings = [sec(rm - 0.5, w0 + 0.25, 0.2), sec(rm - 0.35, w0 + 0.25), sec(rm + 0.35, w0 + 0.25),
                         sec(rm + 0.5, w0 + 0.25, 0.2)]
                rings_faces(m, rings, CLAMP)
    c0, c1, r, h = knob
    xcyl(m, c0, c1, r, z_of(r), h, TILE)


def build_towers(m):
    m.tag("tower")
    za = lambda r: 0.60 + (46.0 - r) * 0.006  # noqa: E731
    tower(m, 15.5, [("mast", 1.8, 8.0, 0.9, 0.9), ("box", 8.0, 10.6, 1.6, 1.6), ("mast", 10.6, 13.8, 0.9, 0.9),
                    ("box", 13.8, 24.5, 2.5, 2.5), ("box", 24.5, 26.5, 2.5, 1.8), ("mast", 26.5, 36.3, 1.7, 1.7),
                    ("box", 36.3, 47.0, 4.0, 4.0, -1.0)], za, knob=(10.4, 12.8, 20.3, 2.4))
    zb = lambda r: 0.52 + (51.0 - r) * 0.007  # noqa: E731
    tower(m, 6.5, [("mast", 17.0, 23.2, 0.9, 0.9), ("box", 23.2, 26.9, 1.6, 1.6), ("mast", 26.9, 29.4, 0.9, 0.9),
                   ("box", 29.4, 41.0, 2.5, 2.5, 0.35), ("box", 41.0, 43.0, 2.5, 1.9, 0.2), ("box", 43.0, 51.0, 1.9, 1.9)],
          zb, knob=(1.5, 4.2, 36.4, 2.9))
    # the plinth both booms stand on, at the deck's upper corner
    chbox(m, 4.8, 41.6, 17.8, 47.5, HULL - 0.1, DECK + 0.10, BLOCK, ch=0.8, chz=0.05)


# --- centre: pipes, manifold, block ------------------------------------------------------------------

def build_centre(m):
    m.tag("pipe")

    def radius(row):
        def ease(a, b, t):
            t = min(1.0, max(0.0, t))
            return a + (b - a) * t * t * (3 - 2 * t)
        if row < 58.0:
            return ease(PIPE_W, 6.0, (row - 40.0) / 16.0)
        return ease(6.0, 4.5, (row - 60.0) / 9.0)

    ctrl = [(c, r, 0.0) for c, r in DOWN] + [(mirror_col(c), r, 0.0) for c, r in reversed(DOWN[:-1])]
    path = spline(ctrl, per=4)
    # the straight runs need no rings between their ends; keep a few for smooth shading
    keep = []
    for p in path:
        if p[1] < 36.0 and keep and keep[-1][1] < 36.0 and abs(p[0] - keep[-1][0]) < 1e-6 and abs(p[1] - keep[-1][1]) < 8:
            continue
        keep.append(p)
    if keep[-1] != path[-1]:
        keep.append(path[-1])
    path = keep
    rad = [radius(r) * PX for _, r, _ in path]
    n0 = len(m.bm.faces)
    def axis_z(r, w):
        t = min(1.0, max(0.0, (r - 38.0) / 10.0))
        t = t * t * (3 - 2 * t)
        return (w + 0.01) * (1 - t) + (DECK - 0.14 + w) * t
    tube(m, [(c, r, axis_z(r, w)) for (c, r, _), w in zip(path, rad)], rad, PIPE, sides=28, cap0=False, cap1=False)
    m.bm.faces.ensure_lookup_table()
    sides = 28
    for k, f in enumerate(m.bm.faces[n0:]):
        i = k // sides
        if i + 1 < len(path) and min(path[i][1], path[i + 1][1]) >= 46.0:
            f.material_index = LOOP
    m.tag("lobes")
    top = LOBE + [(mirror_col(c), r) for c, r in reversed(LOBE[:-1])]
    lz = LOBE_W * PX * LOBE_SQ + DECK - 0.14
    pts = spline([(c, r, lz) for c, r in top], per=3)
    tube(m, pts, LOBE_W * PX, LOOP, sides=16, squash=LOBE_SQ)
    m.tag("pool")
    inner = [(c, r) for c, r in LOBE[::-1]] + [(c, r) for c, r in DOWN if r >= 50.0]
    inner = inner + [(mirror_col(c), r) for c, r in reversed(inner[1:-1])]
    slab(m, inner, 0.0, DECK - 0.12, POOL, ch=0.0)
    # Stepped block: two rows of chamfered tiles and the big T-seamed block over the manifold's bottom.
    m.tag("block")
    B = DECK - 0.15
    for c0, c1 in ((54.1, 56.7), (57.0, 59.6), (59.9, 62.5)):
        chbox(m, c0, 54.0, c1, 57.1, B, B + 0.30, BLOCK, ch=0.35)
    for c0, c1 in ((52.1, 56.8), (57.0, 59.6), (59.8, 64.5)):
        chbox(m, c0, 57.8, c1, 61.6, B, B + 0.42, BLOCK, ch=0.4)
    chbox(m, 50.3, 63.0, 66.3, 67.0, B, B + 0.70, BLOCK, ch=0.5)
    chbox(m, 50.3, 67.3, 58.1, 75.6, B, B + 0.66, BLOCK, ch=0.5)
    chbox(m, 58.5, 67.3, 66.3, 75.6, B, B + 0.66, BLOCK, ch=0.5)
    chbox(m, 50.6, 66.9, 66.0, 67.4, B, B + 0.60, CLAMP, ch=0.1)
    chbox(m, 58.0, 67.2, 58.6, 75.4, B, B + 0.60, CLAMP, ch=0.1)
    chbox(m, 63.0, 69.6, 64.6, 74.8, B + 0.3, B + 0.67, DARK, ch=0.2, chz=0.005)
    # Slatted vents at the bottom centre, one each side.
    m.tag("vent")
    for c0, c1 in ((47.2, 54.6), (64.4, 71.8)):
        slab(m, [(c0, 81.3), (c1, 81.3), (c1, 84.6), (c0, 84.6)], HULL, DECK + 0.012, DARK, ch=0.0)
        for k in range(5):
            cc = c0 + 0.4 + 1.4 * k
            chbox(m, cc, 81.6, cc + 0.75, 84.4, DECK - 0.06, DECK - 0.005, CLAMP, ch=0.15, chz=0.01)


def build(sprite, coll):
    mats = materials(sprite)
    m = M()
    n = m.mark()
    build_deck_half(m)
    build_towers(m)
    m.mirror_since(n)
    build_centre(m)
    bm = m.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj, mats, m.names


# --- per-frame extras (hatch states, flashes) ---------------------------------------------------------

def to_obj(name, m, mats, coll):
    bm = m.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return o


def blob(m, col, row, z, r_px, rz, mat, seg=12, rings=6):
    res = bmesh.ops.create_uvsphere(m.bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * r_px * PX, Y(row) + v.co.y * r_px * PX, z + v.co.z * rz))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def hatch_object(mats, hatch_left, name, coll):
    c0, r0, c1, r1 = PORT_L
    m = M()
    if hatch_left is not None:
        chbox(m, hatch_left, r0, c1, r1, 0.19 + DZ, 0.265 + DZ, RIB, ch=0.15, chz=0.01)
        chbox(m, hatch_left + 0.2, r0 + 0.8, hatch_left + 1.0, r1 - 0.8, 0.26 + DZ, 0.28 + DZ, COLLAR, ch=0.1, chz=0.005)
    else:
        blob(m, (c0 + c1) / 2 - 0.5, (r0 + r1) / 2, 0.21 + DZ, 3.4, 0.07, FLASH)
        blob(m, (c0 + c1) / 2 - 0.5, (r0 + r1) / 2, 0.24 + DZ, 1.8, 0.06, CORE)
    return to_obj(name, m, mats, coll)


def flash_objects(mats, flash, name, coll):
    col, row, frames = flash
    out = []
    for frame, blobs in frames.items():
        m = M()
        for k, (mat, r) in enumerate(blobs):
            blob(m, col, row, 0.21 + DZ + 0.04 * k, r, 0.06 - 0.01 * k, mat)
        if frame == 271:
            c0, r0, c1, r1 = PORT_L
            chbox(m, HATCH_271, r0, c1, r1, 0.19 + DZ, 0.265 + DZ, RIB, ch=0.1, chz=0.01)
        out.append(common.frame_part(to_obj(f"{name}-{frame}", m, mats, coll), [frame]))
    return out


# --- pieces, shell -----------------------------------------------------------------------------------

def layout_of():
    data = common.load_sprite(WT, "newshb-115")
    return [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in data["assemblyLayout"] if e["model"] in PIECES]


def split_open(obj, layout, suffix=""):
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        p = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(p)
        result[name] = p
    return result


def keep_normals(piece, source, cx, cy):
    piece.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    mod = piece.modifiers.new("keep_normals", "DATA_TRANSFER")
    mod.object = source
    mod.use_loop_data = True
    mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "POLYINTERP_NEAREST"
    mod.use_object_transform = True
    bpy.ops.object.select_all(action="DESELECT")
    piece.select_set(True)
    bpy.context.view_layer.objects.active = piece
    bpy.ops.object.modifier_apply(modifier=mod.name)
    piece.location = (0, 0, 0)
    bpy.context.view_layer.update()


def apply_weighted(obj):
    bpy.context.view_layer.update()
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)


def sink_shell(shell, model, margin, reach):
    """Ink on the silhouette only (D90/D118/D185): drop each shell vertex `margin` under the lowest
    model top within `reach` of it, seen from above; x/y untouched."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    moved = 0
    for v in shell.data.vertices:
        w = shell.matrix_world @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = shell.matrix_world.inverted() @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print("shell sunk", moved, "of", len(shell.data.vertices))


# --- main -------------------------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(WT, "newshb-115")
    for name in PIECES:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = merged_sprite()
    coll = common.reset_collection(TAG)
    obj, mats, parts = build(sprite, coll)
    pre = obj.copy()
    pre.data = obj.data.copy()
    coll.objects.link(pre)
    T.cull_hidden(obj, grid=4, ndirs=40)
    apply_weighted(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{TAG}: {tris} triangles")
    plain = [mt.copy() for mt in mats]  # unbaked copies for the per-frame extras (no bake UVs)
    fmt = "AUTO"
    if "--no-bake" not in sys.argv:
        import tempfile
        lib_b119.bake_maps(obj, tempfile.mkdtemp(prefix="nshb115_bake_"), TEXTURED, "nshb115")
        fmt = "WEBP"
    sh = common.outline_shell(pre, coll, voxel=0.016, faces=8000, smooth=6, inside=0.004)
    sink_shell(sh, obj, 0.02, 0.06)
    bpy.data.objects.remove(pre, do_unlink=True)
    lay = layout_of()
    pieces = split_open(obj, lay)
    spieces = split_open(sh, lay, "_outline")
    piece_objs = {}
    for name, cx, cy in lay:
        keep_normals(pieces[name], obj, cx, cy)
        sp = spieces[name]
        sp["tyrian_outline"] = True
        sp.data.materials.clear()
        sp.data.materials.append(bpy.data.materials["outline_shell"])
        sp.data.shade_smooth()
        piece_objs[name] = [pieces[name], sp]
    offs = {n: (cx / 12, -cy / 12) for n, cx, cy in lay}
    for name in PIECES:
        data = common.load_sprite(WT, name)
        if name == "newshb-121":
            objs = piece_objs[name] + flash_objects(plain, FLASH_121, "newshb-121-flash", coll)
            for o in objs[2:]:
                o.data.transform(__import__("mathutils").Matrix.Translation((-offs[name][0], -offs[name][1], 0)))
            common.export_sprite_model(WT, objs, f"enemies/{name}", data["sprites"], image_format=fmt)
            continue
        if name != "newshb-117":
            common.export_sprite_model(WT, piece_objs[name], f"enemies/{name}", data["sprites"], image_format=fmt)
            continue
        for model, frames, left in HATCH:
            if left is None:
                extra = flash_objects(plain, FLASH_117, model + "-flash", coll)
            else:
                extra = [hatch_object(plain, left, f"{model}-hatch", coll)]
            for o in extra:
                o.data.transform(__import__("mathutils").Matrix.Translation((-offs[name][0], -offs[name][1], 0)))
            sprites = [dict(s, frames=[f for f in s["frames"] if f in frames]) for s in data["sprites"]]
            sprites = [s for s in sprites if s["frames"]]
            common.export_sprite_model(WT, piece_objs[name] + extra, f"enemies/{model}", sprites, image_format=fmt)


if __name__ == "__main__":
    main()
