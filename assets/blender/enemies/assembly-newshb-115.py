"""Blue-pipe machine (newshb.shp, assembly of 15 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.10). Fifteen 2x2 ground enemies side by side make one 120x84 px
structure (sprite.json `assemblyLayout`): two big dark-blue pipes run down the screen, each with
a grey grille clamp, a ribbed grey canister and, beside it, a glowing blue lamp in an arched
housing, and bend into a fat heart-shaped manifold at the bottom. The manifold sits on a round grey
deck with lavender side panels, a curved track and vents; inside it is a navy floor panel with a
stepped grey block. Remodelled on the concept (assets/blender/features/concepts/): each part sits
where the registered concept (assets/blender/textures/<name>/concept.png) draws it, within the
sprite's outline, so the concept detail texture_bake.py projects onto it lands on the right part.
Two gun ports flank the loop (in newshb-117 and newshb-121), and lattice towers stand at both
sides, leaning back (they are drawn tall in the sprite): antenna masts with chamfered housings.

The structure is built once in assembly coordinates (left half mirrored about the pipes' axis,
assembly pixel column 59.5), then cut into its fifteen pieces with common.split_assembly. The
sprite is lit from the upper left, so its right half is drawn in shadow (near-black deck, dark
purple side panel) and its side panels carry the sprite's dark outline: that's lighting, not paint
(the game's sun casts the pipes' shadow and draws the outline), so both halves get the lit half's
mid-tone colours and the same deck. The pipes, loop, lamps and gun stacks are round solids about
as tall as they are wide; the pipes and loop are polished metal, so their streaks of light are
shine from the game's lights, not colour.

newshb-117's port has a sliding hatch: closed (frame 117), a quarter open (195), half open
(233), and open with a muzzle flash (197, 235, 271, 273, which only vary the flash), so it gets
four models: newshb-117, -f2, -f3 and -f4. newshb-121's port is always open and only flashes, so
one model covers its five frames. The flashes animate (common.frame_part, one per frame): in -f4
a small dim flash (197), a big one (235), a dying ember with the hatch's edge sliding back in
(271) and the biggest (273); in newshb-121 none (121), a dim spark (199), the biggest (201), a
medium red one (237) and a bright one (275).

Run: blender --background --python assets/blender/enemies/assembly-newshb-115.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b121 as L  # noqa: E402

NAME = "assembly-newshb-115"
ROOT = common.repo_root(__file__)
PIECES = ["newshb-39", "newshb-41", "newshb-43", "newshb-45", "newshb-47",
          "newshb-77", "newshb-79", "newshb-81", "newshb-83", "newshb-85",
          "newshb-115", "newshb-117", "newshb-119", "newshb-121", "newshb-123"]
# Assembly pixel (0, 0) is the top-left corner of newshb-39 (screen 163, -31); the assembly is
# 120 x 84 px and its centre (screen 223, 11) is the Blender origin.
CX0, CY0 = 223, 11
F = L.Frame(60, 42)
AXIS = 59.5  # pixel edge between the two pipes' mirror images
AX = F.x(AXIS)


def mirror_col(e):
    return 2 * AXIS - e


# Hatch states of newshb-117's port: (model suffix, frames, hatch's left edge or None if open).
HATCH = [("", [117], 25.0), ("-f2", [195], 27.0), ("-f3", [233], 29.0), ("-f4", [197, 235, 271, 273], None)]
PORT_L = (25.0, 59.0, 33.0, 68.0)  # left port opening (pixel edges c0, r0, c1, r1)
HATCH_271 = 31.0  # on frame 271 the hatch's edge shows at the port's right side
BASE_TOP = 0.10  # floor of the platform (and of the dark pool inside the loop)
COLLAR_TOP = 0.45  # the deck: about 5.4 px thick
DZ = COLLAR_TOP - 0.18  # how far the port, hatch and flashes rose with the deck
# Remodelled on the concept (assets/blender/textures/assembly-newshb-115/concept.png, the concept
# registered to the sprite): every part sits where the concept draws it, nudged where the concept's
# left half runs a pixel or two outside the sprite's outline (the sprite decides the outline).
# The big pipes are round cylinders of constant diameter (22 px wide, as wide as the sprite's): centre column, half width
# (px), axis height and radius (units).
PIPE_COL, PIPE_W = 42.9, 11.0
PIPE_RZ = PIPE_W / 12
PIPE_Z = PIPE_RZ + 0.01
# Each pipe runs straight down to row 40, then bends into the fat heart-shaped manifold: its outer
# wall runs on straight down the sprite while the tube narrows to the manifold's 12 px (rows 40-56),
# and to 9 px along the bottom, where it passes under the stepped block.
DOWN = [(PIPE_COL, -1.0), (PIPE_COL, 30.0), (PIPE_COL, 38.0), (41.8, 44.0), (39.6, 50.0), (38.0, 56.0),
        (37.8, 61.5), (39.4, 66.0), (42.8, 69.0), (47.5, 70.6), (53.5, 70.9), (AXIS, 71.0)]
# The heart's two upper lobes: from inside each pipe's bend inward to the dip at the top centre.
LOBE = [(41.0, 48.6), (45.0, 48.3), (49.5, 48.4), (54.0, 49.0), (57.5, 49.7), (AXIS, 50.0)]
LOBE_W, LOBE_SQ = 4.6, 1.35


def materials(sprite):
    tag = "nshb115"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(8, metallic=0.5, roughness=0.5),  # 0 base floor, lower deck
        pal(11, metallic=0.5, roughness=0.45),  # 1 light grey deck (the concept's deck plating)
        pal(12, metallic=0.5, roughness=0.4),  # 2 bright ribs, rails, hatch
        pal(90, metallic=0.3, roughness=0.5),  # 3 lavender side panels
        pal(89, metallic=0.3, roughness=0.55),  # 4 purple top plates
        pal(52, metallic=0.8, roughness=0.3),  # 5 navy pipes, polished metal
        pal(53, metallic=0.8, roughness=0.28),  # 6 navy manifold and lamp housings, polished metal
        pal(54, metallic=0.6, roughness=0.35),  # 7 navy floor inside the heart
        pal(4, metallic=0.5, roughness=0.6),  # 8 dark grey clamp body, canister rod, block, bay strips
        pal(5, metallic=0.5, roughness=0.45),  # 9 grey tiles, tower boxes, canister discs
        pal(7, metallic=0.5, roughness=0.5),  # 10 tower masts
        pal(152, metallic=0.0, roughness=0.1, emission_strength=4.0),  # 11 blue lamp glass (lower)
        pal(141, metallic=0.0, roughness=0.1, emission_strength=5.0),  # 12 lamp hot spot
        pal(2, metallic=0.2, roughness=0.8),  # 13 port interior, vents
        pal(116, emission_strength=2.0),  # 14 ember in the right port
        pal(120, emission_strength=3.5),  # 15 muzzle flash
        pal(126, emission_strength=5.0),  # 16 flash core
        pal(5, metallic=0.5, roughness=0.45),  # 17 tower bodies
        pal(3, metallic=0.5, roughness=0.6),  # 18 (unused)
        pal(92, metallic=0.3, roughness=0.5),  # 19 light lavender posts
        pal(155, metallic=0.0, roughness=0.1, emission_strength=4.5),  # 20 bright upper lamp glass
    ]


(BASE, COLLAR, RIB, LAV, PURP, PIPE, LOOP, POOL, CLAMP, TILE, SHAFT, LAMP, HOT, PORT, EMBER, FLASH,
 CORE, TOWER, DRIB, POST, LAMP2) = range(21)

# Muzzle flashes: (centre column, centre row (pixel edges, as in the sprites), {frame: blobs from the
# outside in, as (material, radius px)}). DIM is the dark red flash_materials() adds.
DIM = 21
FLASH_117 = (28.6, 64.3, {197: [(EMBER, 1.8)], 235: [(FLASH, 3.2), (CORE, 1.6)], 271: [(DIM, 1.2)],
                          273: [(FLASH, 3.6), (CORE, 2.6)]})
FLASH_121 = (91.4, 63.4, {199: [(DIM, 1.6)], 201: [(FLASH, 3.8), (CORE, 2.4)], 237: [(EMBER, 2.4), (FLASH, 1.2)],
                          275: [(FLASH, 3.0), (CORE, 1.6)]})


def flash_materials(sprite, mats):
    """materials() plus the dark red of the faintest flashes (DIM)."""
    return mats + [common.palette_material(sprite, 113, "nshb115", emission_strength=1.5)]


def reflect_since(bm, n_verts, axis_x):
    """Mirror, in place, everything added since vertex index n_verts (about Blender x = axis_x)."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[n_verts:]
    for v in verts:
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=list({f for v in verts for f in v.link_faces}))


def strip(bm, outer, inner, z_outer, z_inner, z0, mat):
    """A band between two matching lines of (col, row) points, its top sloping from z_outer on
    the outer line to z_inner on the inner one, standing on z0."""
    n = len(bm.faces)
    rows = []
    for (co, ro), (ci, ri) in zip(outer, inner):
        rows.append([bm.verts.new((F.x(co), F.y(ro), z_outer)), bm.verts.new((F.x(ci), F.y(ri), z_inner)),
                     bm.verts.new((F.x(ci), F.y(ri), z0)), bm.verts.new((F.x(co), F.y(ro), z0))])
    for a, b in zip(rows, rows[1:]):
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(rows[0])
    bm.faces.new(list(reversed(rows[-1])))
    for f in L.faces_since(bm, n):
        f.material_index = mat
        f.smooth = False


def tube(bm, pts, radius, mat, sides=16, closed=False, smooth=True, squash=1.0):
    """A pipe of round section (radius in units, or one per point for a reducer) along a 3D path of
    (col, row, z) points, its rings carried along by parallel transport so bends keep the full
    diameter; squash scales the section's height. Open ends are flat caps (smooth=False on them)."""
    radii = list(radius) if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    squashes = list(squash) if isinstance(squash, (list, tuple)) else [squash] * len(pts)
    P = [Vector((F.x(c), F.y(r), z)) for c, r, z in pts]
    m = len(P)
    tans = []
    for i in range(m):
        if closed:
            t = P[(i + 1) % m] - P[(i - 1) % m]
        else:
            t = P[min(i + 1, m - 1)] - P[max(i - 1, 0)]
        tans.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    u = (ref - tans[0] * ref.dot(tans[0])).normalized()
    n = len(bm.faces)
    rings = []
    for i in range(m):
        if i:
            u = u - tans[i] * u.dot(tans[i])
            u.normalize()
        v = tans[i].cross(u)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            off = (u * math.cos(a) + v * math.sin(a)) * radii[i]
            off.z *= squashes[i]
            ring.append(bm.verts.new(P[i] + off))
        rings.append(ring)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for r0, r1 in pairs:
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    caps = []
    if not closed:
        caps = [bm.faces.new(list(reversed(rings[0]))), bm.faces.new(rings[-1])]
    for f in L.faces_since(bm, n):
        f.material_index = mat
        f.smooth = smooth and f not in caps


def spline(pts, per=6, closed=True):
    """Catmull-Rom points through (col, row, z) control points, `per` per span."""
    m = len(pts)
    out = []
    spans = m if closed else m - 1
    for i in range(spans):
        p0, p1, p2, p3 = (pts[(i + k) % m] if closed else pts[max(0, min(m - 1, i + k))] for k in (-1, 0, 1, 2))
        for s in range(per):
            t = s / per
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                                    + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    if not closed:
        out.append(pts[-1])
    return out


def pipe_top(c, grow=0.0, rx=PIPE_W):
    """Height of the big pipe's upper surface over edge column c (grow lifts it)."""
    t = (c - PIPE_COL) / rx
    return PIPE_Z + (PIPE_RZ + grow) * math.sqrt(max(0.0, 1.0 - t * t))


def seg(bm, col, r0, r1, w0, w1, z0, z1, mat, sides=8, smooth=False):
    """A segment lying down the sprite from row r0 to r1, its axis at heights z0 to z1 (so it can
    lean), half width w0 to w1 px and as tall as wide. sides=8 with flat shading is a chamfered box
    (the concept's tower housings); more sides and smooth shading is a cylinder."""
    n = len(bm.faces)
    L.sweep(bm, F, [(col, r0, z0, w0, w0 * L.PX), (col, r1, z1, w1, w1 * L.PX)], sides=sides, mat=mat,
            smooth=smooth)
    for f in L.faces_since(bm, n):
        if len(f.verts) > 4:
            f.smooth = False


def drum(bm, col, r0, r1, half_w, z0, z1, mat, sides=10):
    """A round segment: a cylinder down the sprite from row r0 to r1 with flat (sharp) ends."""
    seg(bm, col, r0, r1, half_w, half_w, z0, z1, mat, sides=sides, smooth=True)


def side_knob(bm, c0, c1, row, h, z):
    """A round knob sticking out sideways from a tower housing."""
    n = len(bm.faces)
    L.sweep(bm, F, [(c0, row, z, h, h * L.PX * 0.9), (c1, row, z, h, h * L.PX * 0.9)], sides=8, mat=TILE)
    for f in L.faces_since(bm, n):
        if len(f.verts) > 4:
            f.smooth = False


def tower(bm, col, parts, z_of, knob):
    """An antenna mast lying down the sprite and leaning back (drawn tall): parts are (kind, first
    row, last row, half width px at each end) from its tip down to its foot, kind "mast" (a round
    rod) or "box" (a chamfered housing); z_of(row) is the height of its axis there. knob is a round
    stub out of a housing's side: (col0, col1, row, half width px)."""
    for kind, r0, r1, w0, w1, *dc in parts:
        c = col + (dc[0] if dc else 0.0)
        if kind == "mast":
            seg(bm, c, r0 - 0.05, r1 + 0.05, w0, w1, z_of(r0), z_of(r1), SHAFT, sides=8, smooth=True)
        else:
            seg(bm, c, r0, r1, w0, w1, z_of(r0), z_of(r1), TOWER, sides=8)
    c0, c1, r, h = knob
    side_knob(bm, c0, c1, r, h, z_of(r))


def arc(cx, cy, radius, a0, a1, n):
    """(col, row) points on a circle round (cx, cy), angles in degrees (row grows down the sprite)."""
    return [(cx + radius * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))),
             cy + radius * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]


def deck_edge_row(c):
    """Row of the platform's diagonal upper edge at column c (the concept's long diagonal seam)."""
    return 52.2 + (c - 4.8) * (38.5 - 52.2) / (33.0 - 4.8)


def build_side(bm):
    """The left half of the machine (built twice, the second copy mirrored into the right half:
    the sprite's and the concept's dark right half is their lighting, not a different deck)."""
    deck = COLLAR_TOP
    # Round platform: the bottom of a disc, its upper edge rising diagonally to the pipes.
    outline = [(AXIS, 45.0), (53.0, 44.0), (33.0, 38.5), (17.5, 45.5), (4.8, 52.2), (4.5, 58.0),
               (5.5, 64.0), (7.5, 70.0), (10.5, 76.0), (14.0, 81.0), (16.5, 85.0), (AXIS, 85.0)]
    L.prism(bm, F, outline, 0.0, BASE_TOP, mat=BASE)
    # Lavender side panel (the concept's wing): a bevel rising inward from about 1 px at the rim to
    # 4.3 px at its inner edge (column 16), with three raised stripes across it (rows 55-58).
    edge = [(4.0, 46.0), (4.0, 52.2), (4.0, 59.0), (5.0, 65.0), (6.0, 68.0), (7.0, 70.5), (9.0, 74.5), (11.0, 78.5),
            (12.3, 81.5), (13.2, 85.0)]
    edge_in = [(c + 1.4, r) for c, r in edge]
    strip(bm, edge, edge_in, 0.07, 0.17, 0.0, LAV)
    outer = [(15.0, 45.3), (9.0, 45.8)] + edge_in
    inner = [(16.0, 45.0), (16.0, 45.5)] + [(16.0, r) for _, r in edge_in]
    strip(bm, outer, inner, 0.17, 0.36, 0.0, LAV)
    slope = lambda c: 0.17 + (c - 5.4) / (16.0 - 5.4) * 0.19  # noqa: E731
    for r0, r1 in ((55.0, 55.8), (56.3, 57.1), (57.6, 58.4)):
        cs = [5.6, 16.0, 16.0, 5.6]
        L.prism(bm, F, [(c, r) for c, r in zip(cs, (r0, r0, r1, r1))], 0.1, [slope(c) + 0.035 for c in cs], mat=LAV)
    L.prism(bm, F, [(16.0, 45.5), (17.0, 45.0), (17.0, 85.0), (16.0, 85.0)], 0.0, 0.42, mat=RIB)
    # The deck plating between the side panel and the manifold; it runs under the manifold's tube
    # (to its centre line) and, below it, in to the middle.
    down = [(c, r) for c, r in DOWN if r >= 44.0]
    L.prism(bm, F, [(17.0, 45.0), (33.0, 38.5), (37.0, 38.5)] + down + [(AXIS, 85.0), (17.0, 85.0)], 0.0, deck, mat=COLLAR)
    # A raised strip down the deck beside the rib (columns 17-20).
    L.prism(bm, F, [(17.2, deck_edge_row(17.2) + 0.3), (20.2, deck_edge_row(20.2) + 0.3), (20.2, 85.0), (17.2, 85.0)],
            0.1, deck + 0.05, mat=COLLAR)
    # Riveted plate round the lavender post (columns 22-31, rows 41-56) and the post itself.
    L.prism(bm, F, [(22.0, deck_edge_row(22.0) + 0.2), (31.6, deck_edge_row(31.6) + 0.2), (31.6, 56.5), (22.0, 56.5)],
            0.1, deck + 0.04, mat=COLLAR)
    L.prism(bm, F, [(26.0, deck_edge_row(26.0) + 0.5), (31.4, deck_edge_row(31.4) + 0.5), (31.4, 55.0), (26.0, 55.0)],
            0.1, deck + 0.13, mat=POST)
    # Gun port housing (columns 24-33, rows 58-68), standing a px above the deck; the hatch and
    # flash are added per model. Left of it, a slatted vent cut into the deck.
    c0, r0, c1, r1 = PORT_L
    wall = COLLAR
    L.box(bm, F, c0 - 1, r0 - 1.5, c1 + 1, r0, 0.1, 0.28 + DZ, mat=wall)
    L.box(bm, F, c0 - 1, r1, c1 + 1, r1 + 1.2, 0.1, 0.28 + DZ, mat=wall)
    L.box(bm, F, c0 - 1, r0, c0, r1, 0.1, 0.28 + DZ, mat=wall)
    L.box(bm, F, c1, r0, c1 + 1, r1, 0.1, 0.28 + DZ, mat=wall)
    L.box(bm, F, c0, r0, c1, r1, 0.1, 0.19 + DZ, mat=PORT)
    L.box(bm, F, 21.8, 60.3, 23.9, 67.7, 0.1, deck + 0.005, mat=PORT)
    for k in range(6):
        r = 60.8 + 1.15 * k
        L.box(bm, F, 22.0, r, 23.7, r + 0.55, deck - 0.04, deck - 0.005, mat=CLAMP)
    # Curved track on the deck below the port: two raised rails round the manifold, a sunken band
    # between them (the concept's riveted arc, columns 25-43, rows 70-84).
    for radius in (26.0, 29.6):
        pts = [(c, r, deck, 0.55, 0.035) for c, r in arc(52.5, 58.0, radius, 158.0, 113.0, 9) if r <= 85.2]
        L.sweep(bm, F, pts, sides=4, mat=RIB, smooth=False)

    # Lamp housing (the concept's arched light, columns 23-32, rows 18-44): a dark navy frame
    # beside the pipe, its glowing blue glass set in it, bright upper half round a hot spot.
    house = [(32.2, 18.5), (30.0, 18.8), (28.6, 19.8), (27.6, 21.2), (26.6, 23.0), (25.6, 25.0), (24.6, 27.5),
             (23.8, 30.5), (23.2, 34.0), (23.2, deck_edge_row(23.2) + 1.0), (32.2, deck_edge_row(32.2) + 1.0)]
    L.prism(bm, F, house, 0.0, 0.5, mat=LOOP)
    glass = [(31.4, 19.8), (30.2, 20.0), (29.2, 20.8), (28.3, 22.0), (27.3, 23.8), (26.3, 25.8), (25.4, 28.0),
             (24.9, 30.0), (24.3, 34.0), (24.3, deck_edge_row(24.3) - 0.3), (31.4, deck_edge_row(31.4) - 0.3)]
    L.prism(bm, F, glass, 0.3, 0.58, mat=LAMP)
    L.ellipsoid(bm, F, 28.2, 27.0, 0.585, 2.6, 5.0, 0.02, mat=LAMP2, segments=10, rings=4)
    L.ellipsoid(bm, F, 28.2, 26.0, 0.6, 1.3, 1.8, 0.025, mat=HOT, segments=8, rings=4)

    # Grey grille clamp: an angular box saddled over the pipe's top (columns 35-48, rows 0-18), two
    # columns of three riveted tiles with a dark strap between, and two strap bands round the pipe.
    ctop = PIPE_Z + PIPE_RZ + 0.1
    L.box(bm, F, 35.3, -1.0, 47.5, 18.5, PIPE_Z + 0.2, ctop, mat=CLAMP)
    for r0, r1 in ((-1.0, 5.4), (6.2, 10.9), (11.7, 18.2)):
        for cc0, cc1 in ((35.6, 41.0), (41.8, 47.2)):
            L.box(bm, F, cc0, r0, cc1, r1, ctop - 0.02, ctop + 0.06, mat=TILE)
    for r0, r1 in ((5.6, 6.9), (11.0, 12.3)):
        tube(bm, [(PIPE_COL, r0, PIPE_Z), (PIPE_COL, r1, PIPE_Z)], PIPE_RZ + 0.05, TILE, sides=16)
    # A riveted seam ring round the pipe (row 27).
    tube(bm, [(PIPE_COL, 26.6, PIPE_Z), (PIPE_COL, 27.4, PIPE_Z)], PIPE_RZ + 0.02, PIPE, sides=16)
    # Ribbed canister on the pipe (columns 35-41, rows 30-42): a coil of six grey discs on a dark rod,
    # ending in a plain sleeve, standing proud of the pipe.
    z = pipe_top(37.4) + 0.1
    drum(bm, 37.4, 29.6, 42.0, 1.8, z, z, CLAMP, sides=10)
    for k in range(6):
        r = 30.0 + 1.4 * k
        drum(bm, 37.4, r, r + 0.85, 2.6, z, z, TILE, sides=10)
    drum(bm, 37.4, 38.6, 42.0, 2.5, z, z, TILE, sides=10)
    # Thin rod lying along the pipe's top (column 44, rows 18-43) with a small clamp on it.
    zr = pipe_top(44.5) + 0.03
    drum(bm, 44.5, 17.5, 43.0, 0.45, zr, zr, SHAFT, sides=6)
    L.box(bm, F, 43.7, 26.0, 45.3, 27.4, zr - 0.05, zr + 0.06, mat=TILE)
    # The bay between the pipes: a bevelled frame strip and a small pipe along the pipe's inner side
    # (columns 53-56, rows 15-32: the sprite's thin rods; the rest of the gap stays open, as in the sprite).
    L.prism(bm, F, [(53.4, 15.0), (54.4, 15.0), (55.2, 16.6), (55.2, 30.0), (54.4, 31.6), (53.4, 31.6)], 0.0, 0.55,
            mat=CLAMP)
    drum(bm, 55.6, 15.0, 31.6, 0.45, 0.62, 0.62, TILE, sides=6)
    # Purple plate reaching in from above (columns 22-32, rows 0-8), its outer corner rounded.
    L.prism(bm, F, [(22.0, -1.0), (32.0, -1.0), (32.0, 8.2), (29.5, 8.2), (27.6, 7.0), (25.8, 5.2), (24.0, 3.0),
                    (22.6, 1.0)],
            0.0, 0.35, mat=PURP)


def build_towers(bm):
    # Tall antenna mast (column 15.5, rows 2-48): tip rod, node housing, rod, a big housing with a
    # round knob on its side and a chamfered foot, rod, and a wide base housing.
    za = lambda r: 0.38 + (46.0 - r) * 0.0088  # noqa: E731
    tower(bm, 15.5, [("mast", 1.8, 8.0, 1.4, 1.4), ("box", 8.0, 10.6, 2.4, 2.4), ("mast", 10.6, 13.8, 1.4, 1.4),
                     ("box", 13.8, 24.5, 3.4, 3.4), ("box", 24.5, 26.5, 3.4, 2.4), ("mast", 26.5, 35.5, 2.4, 2.4),
                     ("box", 35.5, 47.0, 4.9, 4.9, -1.0)], za, knob=(9.9, 12.4, 20.5, 2.6))
    # Short antenna mast (column 6.5, rows 17-51).
    zb = lambda r: 0.30 + (51.0 - r) * 0.0095  # noqa: E731
    tower(bm, 6.5, [("mast", 17.0, 23.2, 1.4, 1.4), ("box", 23.2, 26.0, 2.4, 2.4), ("mast", 26.0, 29.4, 1.4, 1.4),
                    ("box", 29.4, 41.0, 3.4, 3.4), ("box", 41.0, 43.0, 3.4, 2.4), ("box", 43.0, 51.0, 2.4, 2.4)],
          zb, knob=(1.0, 3.4, 36.8, 3.6))


def build_centre(bm):
    # The two big pipes and the heart-shaped manifold: ONE round tube swept along one path, from
    # the left pipe's top straight down the screen, round the left lobe, along the bottom (under
    # the stepped block) and up round the right lobe into the right pipe.
    def radius(row):
        """Half width (px) of the tube where its centre line is at `row`."""
        def ease(a, b, t):
            t = min(1.0, max(0.0, t))
            return a + (b - a) * t * t * (3 - 2 * t)
        if row < 58.0:
            return ease(PIPE_W, 6.0, (row - 40.0) / 16.0)
        return ease(6.0, 4.5, (row - 60.0) / 9.0)

    ctrl = DOWN + [(mirror_col(c), r) for c, r in reversed(DOWN[:-1])]
    per = 3
    path = spline([(c, r, 0.0) for c, r in ctrl], per=per, closed=False)
    path = path[:1] + path[per:-per] + path[-1:]  # the straight runs need no rings between their ends
    rad = [radius(r) / 12 for _, r, _ in path]
    n = len(bm.faces)
    sides = 16
    tube(bm, [(c, r, w + 0.01) for (c, r, _), w in zip(path, rad)], rad, PIPE, sides=sides)
    for k, f in enumerate(L.faces_since(bm, n)):  # the manifold is drawn a shade brighter than the pipes
        i = k // sides
        if i + 1 < len(path) and min(path[i][1], path[i + 1][1]) >= 46.0:
            f.material_index = LOOP
    # The heart's upper lobes, from inside each pipe's bend to the dip at the top centre.
    top = LOBE + [(mirror_col(c), r) for c, r in reversed(LOBE[:-1])]
    lz = LOBE_W / 12 * LOBE_SQ + 0.02
    tube(bm, spline([(c, r, lz) for c, r in top], per=3, closed=False), LOBE_W / 12, LOOP, sides=12, squash=LOBE_SQ)
    # The navy floor panel inside the heart (about 4 px up), under the inner half of the tube.
    inner = [(c, r) for c, r in LOBE[::-1]] + [(c, r) for c, r in DOWN if r >= 50.0]
    inner = inner + [(mirror_col(c), r) for c, r in reversed(inner[1:-1])]
    L.prism(bm, F, inner, 0.0, 0.34, mat=POOL)
    # The stepped block inside it: a row of three small tiles, a row of three wider ones, and the
    # big block over the manifold's bottom (columns 50-66, rows 63-76) with a T-shaped seam.
    # (The block sits 1.2 px left of the axis, where the concept draws it.)
    for c0, c1 in ((54.1, 56.7), (57.0, 59.6), (59.9, 62.5)):
        L.box(bm, F, c0, 54.0, c1, 57.1, 0.2, 0.5, mat=TILE)
    for c0, c1 in ((52.1, 56.8), (57.0, 59.6), (59.8, 64.5)):
        L.box(bm, F, c0, 57.8, c1, 61.6, 0.2, 0.62, mat=TILE)
    L.box(bm, F, 50.3, 63.0, 66.3, 67.0, 0.3, 0.88, mat=TILE)
    L.box(bm, F, 50.3, 67.4, 58.0, 75.6, 0.3, 0.84, mat=TILE)
    L.box(bm, F, 58.6, 67.4, 66.3, 75.6, 0.3, 0.84, mat=TILE)
    L.box(bm, F, 58.0, 67.0, 58.6, 75.6, 0.3, 0.80, mat=TILE)
    L.box(bm, F, 50.3, 67.0, 66.3, 67.4, 0.3, 0.80, mat=TILE)
    L.box(bm, F, 63.0, 69.6, 64.6, 74.8, 0.3, 0.845, mat=PORT)  # small vent on its right side
    # Slatted vents in the deck below it, one each side of the centre (columns 48-56, rows 81-84).
    for c0, c1 in ((47.2, 54.6), (64.4, 71.8)):
        L.box(bm, F, c0, 81.3, c1, 84.6, 0.1, COLLAR_TOP + 0.005, mat=PORT)
        for k in range(5):
            cc = c0 + 0.4 + 1.4 * k
            L.box(bm, F, cc, 81.6, cc + 0.7, 84.3, COLLAR_TOP - 0.04, COLLAR_TOP - 0.005, mat=CLAMP)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    bm = bmesh.new()
    build_side(bm)
    n = len(bm.verts)
    build_side(bm)
    reflect_since(bm, n, AX)
    n = len(bm.verts)
    build_towers(bm)
    L.mirror_since(bm, n, AX)
    build_centre(bm)
    # The right port is always open; its flashes (newshb-121) are separate frame parts.
    return L.to_object(NAME, bm, mats, coll), mats


def flash_objects(mats, flash, piece_offset, name, coll):
    """One object per frame of `flash` (FLASH_117 or FLASH_121): its glowing blobs at the port, in
    the piece's coordinates, shown only on that frame. Frame 271 also gets the hatch's edge."""
    col, row, frames = flash
    x0, y0 = piece_offset
    parts = []
    for frame, blobs in frames.items():
        bm = bmesh.new()
        for k, (mat, r) in enumerate(blobs):
            L.ellipsoid(bm, F, col, row, 0.21 + DZ + 0.04 * k, r, r, 0.06 - 0.01 * k, mat=mat, segments=12, rings=6)
        if frame == 271:
            c0, r0, c1, r1 = PORT_L
            L.box(bm, F, HATCH_271, r0, c1, r1, 0.19 + DZ, 0.265 + DZ, mat=RIB)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        parts.append(common.frame_part(L.to_object(f"{name}-{frame}", bm, mats, coll), [frame]))
    return parts


def hatch_object(mats, hatch_left, piece_offset, name, coll):
    """newshb-117's sliding hatch (or the muzzle flash when it's open), in the piece's coordinates."""
    c0, r0, c1, r1 = PORT_L
    bm = bmesh.new()
    if hatch_left is not None:
        L.box(bm, F, hatch_left, r0, c1, r1, 0.19 + DZ, 0.265 + DZ, mat=RIB)
        L.box(bm, F, hatch_left + 0.2, r0 + 0.8, hatch_left + 1.0, r1 - 0.8, 0.265 + DZ, 0.28 + DZ, mat=COLLAR)
    else:
        L.ellipsoid(bm, F, (c0 + c1) / 2 - 0.5, (r0 + r1) / 2, 0.21 + DZ, 3.4, 3.4, 0.07, mat=FLASH, segments=12, rings=6)
        L.ellipsoid(bm, F, (c0 + c1) / 2 - 0.5, (r0 + r1) / 2, 0.24 + DZ, 1.8, 1.8, 0.06, mat=CORE, segments=10, rings=5)
    x0, y0 = piece_offset
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    return L.to_object(name, bm, mats, coll)


def flat_cut_faces(piece):
    """Shade the faces that close a piece where split_assembly cut it flat, so a round part cut
    across (a pipe, the loop, a tower) keeps its smooth normals up to the cut instead of bending
    them toward the cut face (which drew a dark ring, a false waist, at every piece edge)."""
    hw, hh = 12 / 12, 14 / 12
    for poly in piece.data.polygons:
        c, nrm = poly.center, poly.normal
        on_x = abs(abs(c.x) - hw) < 1e-4 and abs(abs(nrm.x) - 1) < 1e-3
        on_y = abs(abs(c.y) - hh) < 1e-4 and abs(abs(nrm.y) - 1) < 1e-3
        if on_x or on_y:
            poly.use_smooth = False


def merged_sprite():
    data = common.load_sprite(ROOT, "newshb-115")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole machine's sprite (layout frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 10 (120 x 140 px, the machine in the middle)."""
    rows = [[(0.0, 0.0, 0.0, 0.0)] * 120 for _ in range(140)]
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        want = next(e["frame"] for e in data["assemblyLayout"] if e["model"] == name)
        frame = next((f for f in data["frames"] if want.endswith(f"|{f['index']}")), data["frames"][0])
        x0, y0 = cx + 60 - 12, cy + 70 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    rows[y0 + r][x0 + c] = (*(ch / 255 for ch in data["colors"][str(v)]), 1.0)
    return L.write_png(out, 120, 140, rows)


def main():
    sprite = merged_sprite()
    obj, mats = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    offsets = {name: (cx / 12, -cy / 12) for name, cx, cy in layout}
    pieces = common.split_assembly(obj, layout)
    for piece in pieces.values():
        flat_cut_faces(piece)
    coll = obj.users_collection[0]
    fmats = flash_materials(sprite, mats)
    exported = {}  # model name -> (objects, sprite image)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        if name == "newshb-121":
            objs = [pieces[name]] + flash_objects(fmats, FLASH_121, offsets[name], f"{name}-flash", coll)
            common.export_sprite_model(ROOT, objs, f"enemies/{name}", data["sprites"])
            exported[name] = (objs, data["frames"][0]["image"], name)
            continue
        if name != "newshb-117":
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
            exported[name] = ([pieces[name]], data["frames"][0]["image"], name)
            continue
        for suffix, frames, hatch_left in HATCH:
            model = name + suffix
            if hatch_left is None:
                extra = flash_objects(fmats, FLASH_117, offsets[name], f"{model}-flash", coll)
            else:
                extra = [hatch_object(mats, hatch_left, offsets[name], f"{model}-hatch", coll)]
            sprites = [dict(s, frames=[f for f in s["frames"] if f in frames]) for s in data["sprites"]]
            sprites = [s for s in sprites if s["frames"]]
            common.export_sprite_model(ROOT, [pieces[name]] + extra, f"enemies/{model}", sprites)
            exported[model] = ([pieces[name]] + extra, f"frame-newshb-{frames[0]}.png", name)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        # Whole machine with newshb-117's hatch a quarter open (the layout frame, 195).
        whole_hatch = hatch_object(mats, HATCH[1][2], (0.0, 0.0), "whole-hatch", coll)
        common.render_preview([obj, whole_hatch], str(out), ref, size=10, view_px=640)
        for model, (objs, image, piece) in exported.items():
            img = ROOT / "reference" / "models" / piece / image
            common.render_preview(objs, str(out.parent / f"{model}.png"), img, size=2)
    if "--frames" in sys.argv:  # every frame of the animated models, one row each
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for model, piece in (("newshb-117-f4", "newshb-117"), ("newshb-121", "newshb-121")):
            data = common.load_sprite(ROOT, piece)
            frames = {f for s in json.loads((ROOT / "src/render/spriteModels" / f"{model}.json").read_text())["sprites"]
                      for f in s["frames"]}
            data["frames"] = [f for f in data["frames"] if f["index"] in frames]
            common.render_frame_previews(exported[model][0], str(out.parent / f"{model}.png"), data, ROOT)


if __name__ == "__main__":
    main()
