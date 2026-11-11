"""Steel ledge with a glowing lamp, newshm-7: the bay piece of the assembly-newshm-45 dome
(composite cols 24-48, rows 28-56) with its two glacis door leaves slid apart over a glowing emitter
lens. Frames 7 / 9 / 11 (newshm.shp size 2, 24x28) only open the doors wider and brighten the lens.
Frame 85 (the closed piece) is NOT built here: assembly-newshm-45.py exports it as newshm-7-f2.

How: the piece IS the assembly's piece. This script loads assembly-newshm-45.py as a module (read
only, nothing in it is changed) and builds the whole dome with the assembly's own hull, cutters and
parts, so the hull, yoke tip, apron, seam and outline shell meet newshm-83 / -87 / -47
exactly as newshm-7-f2 does. What changes in the bay:

- The two glacis leaves (the assembly's leaves, same plan, top = z_glacis, 0.22 px chamfer) become
  0.8 px door plates riding on a rail bed cut 0.9 px under the glacis; per frame they translate
  rigidly along x to the sprite's opening (inner edges, local x: f7 9 / 15, f9 6 / 18, f11 4 / 20),
  so the leaf keeps its own shape as it slides into the hull pocket beside the bay (clipped at the
  tile edge, where the neighbour pieces cover it). One frame_part per leaf per frame (D17).
  The leaves are exactly newshm-7-f2's leaves (no added detail), so 85 -> 7 -> 9 -> 11 reads as the
  same doors sliding; the sprite's lit inner leaf edge is their chamfer catching the light.
- Two guide rails cross the bay at its top and bottom edges (pal 99), under the leaves.
- Under the opening, a well (local x 3.2..21) cut 2.6 px under the glacis, parallel to it, dark (98)
  floor, 100 walls. On its floor a machined emitter: a satin steel bezel (103) with eight cap screws (107)
  round a smooth low glass dome and a centre nub. The lens is one static mesh in five uneven, wobbly
  bands (fix 2: a broad hot core set a little left of centre, a broad orange band, a thin orange-red
  transition, a thin dark-red rim, the unlit glass), so it reads as the sprite's blotchy glow, not a
  bullseye; each band animates its palette colour per frame (palette_material frames=, D17): a dull
  ember slit on 7 (core 121; the leaves at 9.6 / 14.4 frame it 4 px wide, 7 tall like the sprite),
  hot on 9 (123 / 121 / 119 / 116) and hottest and widest on 11 (124 / 122 / 120 / 117 / 115).
  The glass is polished tinted metal with a modest emission (see EMIT) so the game's tone map keeps it
  saturated orange / yellow (a dielectric lens rendered as a pink disc with a cream centre).
  The outermost lens band (the unlit dark glass, pal 98 on 7 / 9) is rough dielectric (LENS_OUT_FIN, fix 3),
  not the core's mirror, which showed the environment as a cyan ring round the lens in the game render.
  The apron (105) and the bezel are satin in this piece (FIN_X): at the assembly's finish they showed
  chrome streaks / a cyan environment glint in the game render.

Undersides: the assembly's closed hull base; no detail. No floor plate (D130).
Texture: none by default (no textures/newshm-7 folder). -- --bake runs the AO/roughness model bake of the
static piece (usp_talon.bake_maps); tried, it streaked the apron and hull in the game renderer, so off. Outline shell: from the whole dome with the
leaves closed (exactly newshm-7-f2's shell), cut to the piece without caps, as the assembly does.

Also (D118 follow-up): a dark sloped lintel (pal 99) over the door slot at the bay's north edge, the
sprite's dark rows 6-7, which the leaves slide under; a 101 rail lip along the bay's east and west edges
under the leaves. Rails and lips are built inside the tile and joined after the crop, and the cropped
body is welded and cleaned (close_slivers): no open edges outside the floor plate. Report for the
assembly owner: the yoke tip is pal 69, sprite 67; newshm-7-f2 has one open sliver (pal 98, at the
seam's north end) and A.slab's chamfered slabs leave an open corner, which the self-union hides.
Rule IoU (tools/sprite_mask.py --measure) is 0.9702 on every frame (the sprite's mask is a full rectangle).

Run: blender -b --factory-startup -P assets/blender/enemies/newshm-7.py [-- --out <glb>] [--bake]
"""

import importlib.util
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
EN = HERE
sys.path.insert(0, str(EN.parent))
sys.path.insert(0, str(EN))
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location("assembly_newshm_45", EN / "assembly-newshm-45.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)  # module level only: sprite composite, outline radii, vents (no main())

NAME = "newshm-7"
TAG = "nshm7"
FRAMES = [7, 9, 11]
OX, OY = 24.0, 28.0                     # piece origin in the composite
PIECE = [(NAME, 0.0, 14.0)]             # split_assembly layout entry (A.LAYOUT's newshm-7-f2)
OUT = None
BAKE = False

# --- the bay (composite px) -------------------------------------------------------------------------
G = 0.22                                # half-gap of the closed leaves at the seam (assembly)
LEAF_Y0, LEAF_Y1 = A.GL_TOP + 0.25, A.GL_BOT - 0.15
LEAF_T = 0.8                            # door plate thickness
RAIL_DROP = 0.9                         # rail bed under the glacis
WELL_X = (OX + 3.2, OX + 20.97)       # east wall off the rail bed's 2 px grid line (x 45: boolean slivers)
WELL_Y = (A.GL_TOP, A.GL_BOT + 0.05)    # south wall stops 0.1 px short of the apron leaf's face
WELL_D = 2.6
# leaf inner edges (local x) per frame, read from the sprite's lit / dark columns
OPEN = {7: (9.6, 14.4), 9: (6.0, 18.0), 11: (4.0, 20.0)}
LENS_C = (OX + 12.4, OY + 11.35)        # plan centre of the lens (sprite glow centroid, frames 7-11)
BEZEL = (5.35, 6.0, 0.55)               # inner / outer radius, height over the well floor
# The glow (fix 2): a smooth low dome, no fresnel steps, in a few UNEVEN, blotchy bands like the sprite's
# glow: a broad hot core (inner ~1/3 of the radius, its centre 0.45 px left / 0.25 px up of the lens
# centre, where the sprite's yellow sits on 9 and 11), a broad orange band (to ~0.53 r), a thin orange-red
# transition (to ~0.64 r), a thin dark-red rim (to ~0.75 r) and the unlit dark glass out to the bezel.
# Band edges wobble (low harmonics, one lobe toward the sprite's second hot spot, lower right on 11).
BANDS = [1.9, 2.85, 3.45, 4.0]          # outer radius of bands 0-3 (band 4 runs to the bezel)
BAND_C = [(-0.45, -0.25), (-0.25, -0.12), (-0.1, -0.05), (0.0, 0.0)]  # band boundary centres (east, south)
BAND_WOB = [(0.07, 0.05, 0.0), (0.06, 0.04, 0.10), (0.05, 0.03, 0.08), (0.03, 0.02, 0.04)]  # (2nd, 3rd, lobe)
LOBE_A = math.atan2(1.2, 3.0)           # lobe direction (sprite f11 hot spot: +3 px east, +1.2 px south)
LENS_H = 0.4                            # dome height over the well floor at the centre
# palette per band (core outward) per frame: dull ember -> hot -> hottest (sprite glow by radius)
BAND_PAL = {7: [121, 118, 115, 98, 98], 9: [123, 121, 119, 116, 98], 11: [124, 122, 120, 117, 115]}
NB = 5

# Lens glass: the glow is its emission and the glass a low, polished, tinted reflector (metallic: no white
# diffuse, so the lit part stays the palette hue). The game's neutral tone map whitens any lit colour that
# overshoots, which turned a dielectric or rough lens's reds pink and its core cream; this keeps the
# sprite's saturated ember / orange / yellow (checked in ?viewer=newshm-7 at the game angle, palette 5).
EMIT = 0.4
LENS_METAL, LENS_ROUGH = 1.0, 0.15
# Fix 3: the outermost band is the unlit dark glass (pal 98 navy on 7 / 9). At the core's mirror finish it
# reflected the room environment as a saturated cyan-blue ring in the game render; smoked glass instead:
# dielectric and rough, so it stays near-black navy. The coloured core bands keep the mirror finish.
LENS_OUT_FIN = (0.0, 0.9)
# Fix 2: finishes overriding the assembly's FIN in this piece only. The apron / lip (105 steel) at the
# assembly's 0.38 roughness pooled the room light in two chrome streaks along the lip at the game angle;
# satin (0.58) keeps it the sprite's flat grey. The bezel and its screws, near-mirror, glinted the
# environment's cyan on frame 9: rough and barely metallic, they stay steel grey.
# Fix 3: the apron at (0.3, 0.7) still rendered brighter and bluer than the hull top in the game viewer
# (it faces the camera); the hull's own metalness with a rough finish brings it to the hull's grey
# (viewer frame 9 mean RGB 124/141/157 -> 102/119/132, hull top 88/99/118) without the streaks.
FIN_X = {(105, "steel"): (0.75, 0.72), "bezel": (0.2, 0.62)}

# extra materials (registered before A builds anything: A.to_obj gives every mesh all A.MATS)
RAIL = A.M(99, "dark")
WELLF = A.M(98, "dark")
WELLW = A.M(100, "dark")
BEZ = A.M(103, "bezel")
SCREW = A.M(107, "bezel")
LEAFM = A.M(102, "leaf")             # the moving leaves: own material (not in the bake)
CUT = A.M(101, "dark")
RAILLIP = A.M(101, "dark")
WELLN = A.M(99, "dark")
LENS = [A.M(BAND_PAL[7][i], f"lens{i}") for i in range(NB)]


def zg(x, y):
    return A.z_glacis(x, y)


# --- lens plane ---------------------------------------------------------------------------------------

def lens_frame():
    """Origin, axes (east, down-slope) and normal of the well floor at the lens (composite px)."""
    cx, cy = LENS_C
    zf = lambda x, y: zg(x, y) - WELL_D  # noqa: E731
    o = Vector((cx, cy, zf(cx, cy)))
    dzdx = zf(cx + 0.5, cy) - zf(cx - 0.5, cy)
    dzdy = zf(cx, cy + 0.5) - zf(cx, cy - 0.5)
    ex = Vector((1, 0, dzdx)).normalized()
    ey = Vector((0, 1, dzdy)).normalized()
    n = ex.cross(ey).normalized()
    if n.z < 0:
        n = -n
    ey = n.cross(ex).normalized()
    return o, ex, ey, n


def revolve(prof, mats, sides=40, name="rev", frame=None, closed=False):
    """Closed solid of revolution about the lens axis: prof = [(r, h)], first and last at r = 0 or
    closed by caps; mats[i] for the band between prof[i] and prof[i + 1]."""
    o, ex, ey, n = frame or lens_frame()
    bm = bmesh.new()
    rings = []
    for r, h in prof:
        if r < 1e-6:
            p = o + n * h
            rings.append([bm.verts.new((p.x, -p.y, p.z))])
            continue
        rv = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            p = o + ex * (r * math.cos(a)) + ey * (r * math.sin(a)) + n * h
            rv.append(bm.verts.new((p.x, -p.y, p.z)))
        rings.append(rv)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for i, (Ar, Br) in enumerate(pairs):
        if len(Ar) == 1 and len(Br) == 1:
            continue
        for k in range(sides):
            kk = (k + 1) % sides
            if len(Ar) == 1:
                f = bm.faces.new((Ar[0], Br[kk], Br[k]))
            elif len(Br) == 1:
                f = bm.faces.new((Ar[k], Ar[kk], Br[0]))
            else:
                f = bm.faces.new((Ar[k], Ar[kk], Br[kk], Br[k]))
            f.material_index = mats[i]
    for R_ in (() if closed else (rings[0], rings[-1])):
        if len(R_) > 1:
            bm.faces.new(R_).material_index = mats[0]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return A.to_obj(bm, name, recalc=False)


def lens(fr, rim, sides=64):
    """The lens glass: a closed low dome on the well floor (rim wall from 0.2 under the floor). Rings:
    the core centre, then per band a mid ring and its wobbly outer boundary; the last band ends on the
    round rim. Heights follow one smooth dome about the lens centre, so band edges are colour only."""
    o, ex, ey, n = fr
    dome = lambda r: 0.18 + (LENS_H - 0.18) * (1 - min(1.0, r / rim) ** 2) ** 0.6  # noqa: E731

    def bnd(k, a):
        if k >= NB - 1:
            return 0.0, 0.0, rim
        w2, w3, lobe = BAND_WOB[k]
        da = math.atan2(math.sin(a - LOBE_A), math.cos(a - LOBE_A))
        r = BANDS[k] * (1 + w2 * math.cos(2 * a + 0.7 + k) + w3 * math.cos(3 * a + 2.1 - 0.8 * k)
                        + lobe * math.exp(-(da / 0.6) ** 2))
        return BAND_C[k][0], BAND_C[k][1], r

    def pt(u, v):
        x, y = u, v
        p = o + ex * x + ey * y + n * dome(math.hypot(x, y))
        return (p.x, -p.y, p.z)

    bm = bmesh.new()
    angs = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    centre = bm.verts.new(pt(*BAND_C[0]))
    rings, mats = [], []          # rings[j]: list of verts; mats[j]: material of the faces inside ring j
    prev = [(BAND_C[0][0], BAND_C[0][1]) for _ in angs]
    for k in range(NB):
        outer = []
        for a in angs:
            cx, cy, r = bnd(k, a)
            outer.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        steps = 3 if k == 0 else 2
        for s_ in range(1, steps + 1):
            t = s_ / steps
            ring = [bm.verts.new(pt(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t))
                    for p0, p1 in zip(prev, outer)]
            rings.append(ring)
            mats.append(LENS[k])
        prev = outer
    for j, ring in enumerate(rings):
        for k in range(sides):
            kk = (k + 1) % sides
            if j == 0:
                f = bm.faces.new((centre, ring[k], ring[kk]))
            else:
                f = bm.faces.new((rings[j - 1][k], rings[j - 1][kk], ring[kk], ring[k]))
            f.material_index = mats[j]
    # rim wall down under the floor, and the bottom cap
    low = []
    for a in angs:
        p = o + ex * (rim * math.cos(a)) + ey * (rim * math.sin(a)) - n * 0.2
        low.append(bm.verts.new((p.x, -p.y, p.z)))
    top = rings[-1]
    for k in range(sides):
        kk = (k + 1) % sides
        bm.faces.new((top[k], top[kk], low[kk], low[k])).material_index = LENS[NB - 1]
    bm.faces.new(list(reversed(low))).material_index = LENS[NB - 1]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return A.to_obj(bm, "lens", recalc=False)


def emitter():
    """Bezel ring, cap screws, the banded lens dome and its centre nub, on the well floor."""
    fr = lens_frame()
    o, ex, ey, n = fr
    parts = []
    ri, ro, bh = BEZEL
    # bezel: a machined steel ring, chamfered top edges, sunk 0.2 into the floor
    parts.append(revolve([(ri - 0.05, -0.2), (ri - 0.05, bh - 0.12), (ri + 0.1, bh), (ro - 0.18, bh),
                          (ro, bh - 0.2), (ro + 0.08, -0.2)],
                         [BEZ] * 6, sides=48, name="bezel", frame=fr, closed=True))
    # lens: a smooth low dome in NB uneven, wobbly palette bands (see BANDS)
    parts.append(lens(fr, ri - 0.02))
    # centre nub (the emitter tip), core colour
    cn = o + ex * BAND_C[0][0] + ey * BAND_C[0][1]
    parts.append(revolve([(0.0, LENS_H - 0.12), (0.5, LENS_H - 0.12), (0.5, LENS_H + 0.02), (0.32, LENS_H + 0.14),
                          (0.0, LENS_H + 0.17)], [LENS[0]] * 4, sides=16, name="nub", frame=(cn, ex, ey, n)))
    # eight cap screws on the bezel
    rb = (ri + ro) / 2
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        c = o + ex * (rb * math.cos(a)) + ey * (rb * math.sin(a))
        f2 = (c, ex, ey, n)
        parts.append(revolve([(0.0, bh - 0.05), (0.24, bh - 0.05), (0.24, bh + 0.08), (0.15, bh + 0.17),
                              (0.0, bh + 0.19)], [SCREW] * 4, sides=8, name="screw", frame=f2))
    return parts


# --- bay ----------------------------------------------------------------------------------------------

def bay_cutters():
    """Rail bed across the bay, the deeper well under the opening."""
    x0, x1 = A.BAY
    y0, y1 = WELL_Y
    cs = [A.slab([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 30.0, lambda x, y: zg(x, y) - RAIL_DROP, RAIL,
                 grid=2.0, name="cut_rail")]
    cs.append(A.slab([(WELL_X[0], y0), (WELL_X[1], y0), (WELL_X[1], y1), (WELL_X[0], y1)], 30.0,
                     lambda x, y: zg(x, y) - WELL_D, WELLW, bot=WELLF, grid=1.0, name="cut_well"))
    return cs


def rails():
    """Two guide rails across the bay (top and bottom edges), the leaves ride on them."""
    out = []
    # built inside the tile (0.01 px in from its edges, so no end face lies in the hull's cut caps): they
    # are not cropped with the body (its self-union left open slivers where they crossed the tile edge)
    x0, x1 = max(A.BAY[0], OX + 0.01), min(A.BAY[1], OX + 23.99)
    for ya, yb in ((A.GL_TOP + 0.3, A.GL_TOP + 0.95), (A.GL_BOT - 0.75, A.GL_BOT - 0.1)):
        out.append(A.slab([(x0, ya), (x1, ya), (x1, yb), (x0, yb)], lambda x, y: zg(x, y) - LEAF_T - 0.03,
                          lambda x, y: zg(x, y) - RAIL_DROP - 0.3, RAIL, chamfer=0.1, grid=1.0, name="rail"))
    # rail lips along the bay's east and west edges, 0.12 px proud of the rail bed, under the leaves,
    # between the rails with 0.05 px of air at each end
    ya, yb = A.GL_TOP + 1.0, A.GL_BOT - 0.8
    for xa, xb in ((x0, A.BAY[0] + 1.33), (A.BAY[1] - 1.33, x1)):
        out.append(A.slab([(xa, ya), (xb, ya), (xb, yb), (xa, yb)],
                          lambda x, y: zg(x, y) - RAIL_DROP + 0.12, lambda x, y: zg(x, y) - RAIL_DROP - 0.36, RAILLIP,
                          chamfer=0.1, grid=1.0, name="raillip"))
    return out


def lintel():
    """The door slot's hood on the bay's north edge: a dark sloped lip (the sprite's dark rows 6-7) the
    leaves slide under. Its underside sits 0.02 px over the leaf tops."""
    x0, x1 = A.BAY
    ya, yb = A.GL_TOP - 0.02, A.GL_TOP + 1.55
    top = lambda x, y: zg(x, y) + 0.04 + 0.3 * (1.0 - (y - ya) / (yb - ya)) ** 1.2  # noqa: E731
    return [A.slab([(x0, ya), (x1, ya), (x1, yb), (x0, yb)], top, lambda x, y: zg(x, y) + 0.03, WELLN,
                   grid=1.0, name="lintel")]


def leaf(side, sh, closed=False):
    """One glacis leaf (L or R) slid sh px along x: the assembly's leaf, rigidly translated."""
    x0, x1 = (A.BAY[0] + 0.25, A.SEAM_X - G) if side == "L" else (A.SEAM_X + G, A.BAY[1] - 0.25)
    poly = [(x0 + sh, LEAF_Y0), (x1 + sh, LEAF_Y0), (x1 + sh, LEAF_Y1), (x0 + sh, LEAF_Y1)]
    top = lambda x, y: zg(x - sh, y)  # noqa: E731
    bot = 3.0 if closed else (lambda x, y: zg(x - sh, y) - LEAF_T)
    objs = [A.slab(poly, top, bot, A.PANEL if closed else LEAFM, chamfer=0.22, grid=2.0, name=f"leaf_{side}")]
    return objs


def dup(o):
    c = o.copy()
    c.data = o.data.copy()
    A.COLL.objects.link(c)
    return c


def crop(body, floor, loose):
    """The piece: the body (all closed solids) intersected with the tile box (EXACT, self-union), so its
    cut faces are capped in the dark cut colour (101); the floor plate is not exported (D130, as the
    assembly: the game draws the tile's ground in HD), so it is dropped. `loose` (the rails
    and rail lips, closed solids built inside the tile) is only joined: cropped in the self-union it
    left open slivers at the tile edge."""
    box = A.slab([(OX, OY - 0.001), (OX + 24, OY - 0.001), (OX + 24, OY + 28), (OX, OY + 28)], 20.0, -1.0,
                 CUT, grid=0, name="crop_box")
    mod = body.modifiers.new("crop", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.solver = "EXACT"
    mod.use_self = True
    mod.object = box
    mod.material_mode = "INDEX"
    common._apply_modifiers(body)
    bpy.data.objects.remove(box, do_unlink=True)
    body = A.join([body, loose], "body")
    close_slivers(body)  # also closes the chamfered rail slabs' open corner (A.slab leaves one there)
    bpy.data.objects.remove(floor, do_unlink=True)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.translate(bm, vec=(0, 14 / 12, 0), verts=bm.verts)
    bm.to_mesh(body.data)
    bm.free()
    body.name = NAME
    body.data.name = NAME
    return body


def close_slivers(obj):
    """Weld the cropped body (1e-4 px) and fill what the exact booleans still leave open: tiny cut slivers
    (one inherited from the assembly's own cutters, as on newshm-7-f2). Each fill takes the colour of the
    face beside it."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nb = lambda: sum(1 for e in bm.edges if e.is_boundary)  # noqa: E731
    n0 = nb()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)  # glb units (0.0012 px)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-4)
    for _ in range(3):  # open boolean slivers: drop the hair-thin faces on an open edge, fill what is left
        bad = {f for e in bm.edges if e.is_boundary for f in e.link_faces if f.calc_area() < 1e-4}
        if not bad:
            break
        bmesh.ops.delete(bm, geom=list(bad), context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bnd = [e for e in bm.edges if e.is_boundary]
    if bnd:
        res = bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
        for f in res["faces"]:
            for lp in f.loops:
                other = [o for o in lp.edge.link_loops if o.face is not f]
                if other:
                    f.material_index = other[0].face.material_index
                    if other[0].vert is lp.vert:   # same winding along the shared edge: flip
                        f.normal_flip()
                    break
    # triangulate here (the exporter drops the zero-area triangles of a collinear n-gon, which opens
    # cracks along the well's east wall) and dissolve those degenerate triangles
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5)
    # coincident triangles the cutters' overlaps leave (the exporter keeps one of each, which opened the
    # strip along the well's east wall): keep the copy whose winding agrees with its neighbours
    groups = {}
    for f in bm.faces:
        groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)

    def agree(f, group):
        n = 0
        for lp in f.loops:
            for o in lp.edge.link_loops:
                if o.face not in group and o.vert is not lp.vert:
                    n += 1
                    break
        return n
    dead, ndup = [], 0
    for fs in groups.values():
        if len(fs) > 1:
            ndup += len(fs) - 1
            sc = [agree(f, fs) for f in fs]
            if len(fs) == 2 and fs[0].normal.dot(fs[1].normal) < 0 and sc[0] == sc[1]:
                dead += fs                    # a membrane between two cells: both go
            else:
                best = fs[sc.index(max(sc))]
                dead += [f for f in fs if f is not best]
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    print(f"{NAME}_B: {ndup} duplicate triangles, {len(dead)} removed")
    left = sum(1 for e in bm.edges if e.is_boundary)
    thin = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    print(f"{NAME}_B: {thin} zero-area triangles left")
    bm.to_mesh(obj.data)
    bm.free()
    print(f"{NAME}_B: body boundary edges {n0} -> {left} after weld + fill")


def build():
    A.COLL = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": A.COLS}
    A.MATERIALS = {}
    for idx, fin in A.MATS:
        if fin.startswith("lens"):
            band = int(fin[4:])
            frames = {f: BAND_PAL[f][band] for f in (9, 11)}
            met, rough = LENS_OUT_FIN if band == NB - 1 else (LENS_METAL, LENS_ROUGH)
            A.MATERIALS[(idx, fin)] = common.palette_material(sprite, idx, f"{TAG}_{fin}", metallic=met,
                                                              roughness=rough, emission_strength=EMIT,
                                                              frames=frames)
        else:
            met, rough = FIN_X.get((idx, fin)) or FIN_X.get(fin) or A.FIN["steel" if fin == "leaf" else fin]
            A.MATERIALS[(idx, fin)] = common.palette_material(sprite, idx, f"{TAG}_{fin}", metallic=met,
                                                              roughness=rough)
    # hull with the assembly's cuts plus the rail bed and the well
    hull = A.build_hull()
    cs = A.cutters() + bay_cutters()
    cc = bpy.data.collections.new(f"{NAME}_cutters")
    for c in cs:
        A.COLL.objects.unlink(c)
        cc.objects.link(c)
    bpy.context.scene.collection.children.link(cc)
    mod = hull.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.operand_type = "COLLECTION"
    mod.collection = cc
    mod.material_mode = "INDEX"
    common._apply_modifiers(hull)
    for c in cs:
        bpy.data.objects.remove(c, do_unlink=True)
    # the assembly's parts without its closed glacis leaves
    parts = [p for p in A.build_parts() if not p.name.startswith("glacis")]
    gone = [p for p in bpy.data.objects if p.name.startswith("glacis")]
    for p in gone:
        bpy.data.objects.remove(p, do_unlink=True)
    parts += lintel() + emitter()
    loose = A.join(rails(), "rails")
    body = A.join([hull] + parts, "body")
    # bolts: not the four leaf-corner bolts (they ride on the leaves, off the tile when open)
    leaf_bolts = {(24.8, 35.6), (48.2, 35.6), (24.8, 44.0), (48.2, 44.0)}
    A.BOLTS[:] = [b for b in A.BOLTS if b not in leaf_bolts]
    body = A.join([body, A.add_bolts(body)], "body")
    floor = A.build_floor()
    whole = A.join([dup(body), dup(loose), dup(floor)], "whole")  # for the outline shell only

    # outline shell: the dome with the leaves closed (= newshm-7-f2's shell), cut open to the piece
    closed = leaf("L", 0.0, closed=True) + leaf("R", 0.0, closed=True)
    src = A.join([whole] + closed, "shell_src")
    bm = bmesh.new()
    bm.from_mesh(src.data)
    stone = set(A.STONE.values())
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in stone], context="FACES")
    bm.to_mesh(src.data)
    bm.free()
    shell = common.outline_shell(src, A.COLL, voxel=0.016, faces=A.OUTLINE_FACES)
    bpy.data.objects.remove(src, do_unlink=True)
    sh = A.split_open(shell, PIECE, A.COLL)[NAME]
    sh.data.materials.clear()
    sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    bpy.data.objects.remove(shell, do_unlink=True)

    piece = crop(body, floor, loose)
    A.smooth(piece)
    if BAKE:
        # AO / roughness bake of the static piece (model bake, no concept projection), as the assembly
        # bakes newshm-7-f2; the leaves (LEAFM) and the lens bands keep plain palette materials.
        import tempfile
        import usp_talon as T
        slots = [k for k in A.MATS if not k[1].startswith("lens") and k[1] != "leaf"]
        tex = T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(A.MATS.index(k) for k in slots)
        try:
            T.bake_maps(piece, tempfile.mkdtemp(prefix="nshm7B_bake_"), size=1024, samples=64)
        finally:
            T.TEXTURED = tex
    out = [piece, sh]
    print(f"{NAME}_B: body {A.tris(piece)} tris, shell {A.tris(sh)}")
    # per-frame leaves, cut to the tile
    for f in FRAMES:
        le, re = OPEN[f]
        for side, sh_ in (("L", OX + le - (A.SEAM_X - G)), ("R", OX + re - (A.SEAM_X + G))):
            objs = leaf(side, sh_)
            lo = A.join(objs, f"leaf{side}_{f}")
            p = common.split_assembly(lo, PIECE, A.COLL)[NAME]
            bpy.data.objects.remove(lo, do_unlink=True)
            if not p.data.polygons:
                bpy.data.objects.remove(p, do_unlink=True)
                continue
            p.name = f"{NAME}-leaf{side}-{f}"
            A.smooth(p)
            common.frame_part(p, [f])
            out.append(p)
            print(f"{NAME}_B: leaf {side} frame {f}: slide {sh_:+.2f} px, {A.tris(p)} tris")
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    global BAKE
    BAKE = "--bake" in argv
    objs = build()
    total = sum(A.tris(o) for o in objs if not o.get("tyrian_outline"))
    print(f"{NAME}_B: total {total} tris (all frames' leaves, shell excluded)")
    if out is None:
        root = common.repo_root(__file__)
        sprites = [{**s_, "frames": [f for f in s_["frames"] if f in FRAMES]}
                   for s_ in common.load_sprite(root, NAME)["sprites"]]
        sprites = [s_ for s_ in sprites if s_["frames"]]
        common.export_sprite_model(root, objs, f"enemies/{NAME}", sprites)
    else:
        common.export_glb(objs, out, image_format="WEBP" if BAKE else "AUTO")
    print(f"{NAME}_B: wrote {out}")


if __name__ == "__main__":
    main()
