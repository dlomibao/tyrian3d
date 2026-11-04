"""Dragonwing (player 2's ship in a two-player game: tyrian.shp#8 frames 13 and 51 drawn side by side
as one 48 x 28 object, banking frames 9-17 / 47-55): a hard-surface ship built the USP Talon's way
(assets/blender/usp_talon.py, DECISIONS D50-D53).

The sprite is authoritative for the plan outline, the windshield and the colours: the top view
follows frame 13 row by row (two big round-nosed engine pods with square tails, a swept fin out of
each pod's flank to a blunt tip at rows 15-17, a low deck between each pod and the body, the body's
two forward jaws at row 7, rear shoulders and the red engine block at rows 21-25), the dark
windshield fills the sprite's sunken cockpit between the jaws' ridges (rows 9-14, columns 21-27),
and each part takes the palette index the sprite uses where it covers it (the median of those
pixels, the darkest shading 16-18 and the highlights 29-31 left out as lighting). There is no
concept image; the side, front and underside are designed to fit: machined octagon pods with
armour petals over their round noses, lengthwise top strips, tail caps round deep nozzles, gear
doors and intakes underneath; wedge fins with a top plate; jaw ridges framing a raked canopy; a
dorsal hump with a spine strip; vented rear shoulders; a glowing engine block of lengthwise vanes
over a red bed that continues down its rear face as the exhaust; a keel, chin guns and belly plates.

How it is built (as the Talon):
- Every part is a low-poly cage in sprite px: x across from the symmetry axis (column edge 24.5,
  right +), y = sprite row (aft +), z up; moved to Blender at the end (X = (x + 0.5) / 12,
  Y = (14 - y) / 12, Z = z / 12; the origin is the middle of the 48 x 28 block).
- Plan widths between stations are monotone cubic (pchip), so lofts never swell.
- Dark gunmetal cores under separate armour plates that stand 0.25-0.45 px proud with 45-degree
  chamfers, so panel lines are real gaps. Flat faces stay flat (sharp by angle, weighted normals).
- Texture: no concept projection (there are no concept maps for this ship). This script bakes
  ambient occlusion with an edge lift (a colour multiplier, slightly cool: TINT, D53) and a
  roughness/metalness map. Base Color = map x palette colour.
- Palette materials (pal_<index>) so palettes, fades and the hit flash apply; the engine's bed
  and hot cores are emissive palette reds and oranges (118, 122).
- Exported beside it: an outline shell (common.outline_shell, D51) and `tyrian_engines` (two red
  glows behind the engine block for the menu backdrop).
The banking frames only move the highlights, so the model rolls instead (src/render/spriteModels.ts
`group`).

    Blender --background --factory-startup --python ship-dragonwing.py -- [--out path.glb] [--no-bake] [--preview png]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
# The Talon's generic hard-surface helpers: pchip curves, parts, sections, lofts, armour plates,
# chamfered hulls, the machined pod section, hidden-face culling and the join with weighted normals.
from usp_talon import (Part, Section, cbox, cull_hidden, fillet, frange, hull, join, loft,  # noqa: E402
                       loft_rings, pchip, plate)

NAME = "ship-dragonwing"
MODEL = f"ships/{NAME}"
PX = 1 / 12

# Material slots.
(POD, POD_DK, FIN, DECK, BODY, RIDGE, HUMP, REAR, SHOULDER, GUN, DEEP, GLASS, ENG, VANE, GLOW, HOT,
 BELLY, SPINE) = range(18)
# The palette index of each, from frame 13 (median of the pixels each part covers, 16-18 and 29-31
# left out): pods 22 (their tails and caps 21), fins 21, deck 22, the body's flanks 24, the jaw
# ridges 25 and the hump behind the cockpit 25, the rear deck 20, the rear shoulders 21, the
# engine housing 114 with darker vanes 113, glowing bed 118 and hot cores 122; gunmetal 19, recesses
# and glass 16.
PAL_OF = {POD: 22, POD_DK: 21, FIN: 21, DECK: 22, BODY: 24, RIDGE: 25, HUMP: 25, REAR: 20, SHOULDER: 21,
          GUN: 19, DEEP: 16, GLASS: 16, ENG: 114, VANE: 113, GLOW: 118, HOT: 122, BELLY: 21, SPINE: 26}

# Satin, not mirror metal (D52, D53): the metalness of the bronze parts is scaled to ~0.15-0.18.
METAL = 0.3
# The baked colour map's cool tint (D53): three's Neutral tone mapping pulls the lit tan toward
# saturated bronze (blue loses the most); this keeps the game's colour on the sprite's khaki.
TINT = (0.88, 0.94, 1.0)


def materials(sprite):
    def pal(slot, tag, metallic, roughness, emission=0.0):
        i = PAL_OF[slot]
        return common.palette_material(sprite, i, f"dragonwing_{tag}", metallic=metallic * METAL,
                                       roughness=roughness, emission_strength=emission)
    return [
        pal(POD, "pod", 0.6, 0.36),
        pal(POD_DK, "pod_dark", 0.55, 0.44),
        pal(FIN, "fin", 0.55, 0.4),
        pal(DECK, "deck", 0.5, 0.44),
        pal(BODY, "body", 0.55, 0.4),
        pal(RIDGE, "ridge", 0.6, 0.32),
        pal(HUMP, "hump", 0.6, 0.34),
        pal(REAR, "rear", 0.5, 0.46),
        pal(SHOULDER, "shoulder", 0.55, 0.42),
        pal(GUN, "gunmetal", 0.55, 0.46),
        pal(DEEP, "recess", 0.3, 0.8),
        common.palette_material(sprite, PAL_OF[GLASS], "dragonwing_glass", metallic=0.0, roughness=0.05),
        pal(ENG, "engine", 0.2, 0.5, emission=0.3),
        pal(VANE, "vane", 0.3, 0.5, emission=0.15),
        pal(GLOW, "engine_glow", 0.0, 0.4, emission=0.6),
        pal(HOT, "engine_core", 0.0, 0.4, emission=1.4),
        pal(BELLY, "belly", 0.4, 0.55),
        pal(SPINE, "spine", 0.6, 0.3),
    ]


# --- plan and sections (sprite px; right side, mirrored for the left) ---------------------------

def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# Engine pods. The plan's outboard and inboard edges (x_o, x_i) by row, fitted to frame 13's mask
# including its dark outline ring: a round nose at row 6 (the inboard side sweeping in faster, to
# column 13 at row 8), widest at rows 10-12, then straight under the fin to a square tail at row 21.
_PY = [7.0, 7.2, 7.45, 7.75, 8.1, 8.5, 9.0, 9.5, 10.0, 10.5, 11.5, 12.5, 14.0, 16.0, 18.0, 18.6, 19.2, 19.7,
       20.2, 20.5, 20.75, 20.9]
_PXO = [15.8, 16.9, 17.6, 18.0, 18.25, 18.35, 18.35, 18.37, 18.8, 19.17, 19.25, 19.2, 19.1, 19.0, 18.8, 18.55,
        18.3, 18.25, 18.25, 18.2, 18.05, 17.85]
_PXI = [15.5, 14.6, 13.9, 13.4, 13.0, 12.4, 11.2, 10.55, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5,
        10.7, 11.3, 11.5, 11.7, 11.9]
PXO = pchip(_PY, _PXO)
PXO_R = PXO  # the inner mask is symmetric (the outer ring's one-pixel asymmetry at row 7 is ink)
PXI = pchip(_PY, _PXI)
_PZY = [7.0, 7.2, 7.45, 7.75, 8.1, 9.0, 10.0, 18.6, 20.2, 20.6, 20.9]
PRZ = pchip(_PZY, [1.1, 2.0, 2.65, 3.0, 3.25, 3.6, 4.15, 4.15, 4.05, 3.85, 3.55])
POD_CZ = 0.0
POD_KEEL_R = 1.8
POD_PLATE = 0.3
POD_START, POD_END = 7.0, 20.85


def _pod_unit():
    """The pod section, half sizes 1 x 1 (u outboard, v up): the Talon's machined octagon (same
    vertex order) with a tall outboard flank that leans in from its middle to near-square corners
    (a shallow chevron). The model rolls 35 degrees for the full banking frames (drawListRenderer
    MAX_ROLL), yet those frames are barely narrower than the level one (one pixel per edge per bank
    step): the flank's middle sets the level edge, its tall corners (a little inboard) the rolled
    ones, so every frame keeps the sprite's edge (D74). FENCE does the same on the fins."""
    a, b = 2.6, 2.3
    t = 0.17 * a  # tumblehome
    # Inboard, where the pod meets the deck, a deep chamfer on top and a belly sloping up from the
    # outboard keel: rolled, the pod's inboard edge stays where the banking frames draw it.
    corners = [(-0.3 * a, b), (a - t - 0.12 * a, b), (a - t, 0.9 * b), (a, 0.0), (a - t, -0.9 * b),
               (a - t - 0.12 * a, -b), (-0.3 * a, -0.75 * b), (-a, -0.3 * b), (-a, 0.45 * b)]
    pts = fillet(corners, (1.0, 0.2, 0.2, 0.08, 0.2, 0.3, 0.8, 0.8, 0.9), (2, 2, 2, 1, 2, 2, 2, 2, 2))
    return [(u / a, v / b) for u, v in pts]


POD_UNIT = _pod_unit()
POD_N = len(POD_UNIT)


def pod_s(deg):
    """Loop parameter (vertex index + fraction) where the ray at `deg` degrees from straight up,
    toward outboard (negative: inboard), meets the pod section (as usp_talon.pod_s)."""
    t = math.radians(deg % 360)
    dx, dz = math.sin(t), math.cos(t)
    best = None
    for i in range(POD_N):
        (ax, az), (bx, bz) = POD_UNIT[i], POD_UNIT[(i + 1) % POD_N]
        ex, ez = bx - ax, bz - az
        den = dx * ez - dz * ex
        if abs(den) < 1e-12:
            continue
        r = (ax * ez - az * ex) / den
        u = (ax * dz - az * dx) / den
        if r > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or r < best[0]):
            best = (r, i + u)
    return best[1] - (POD_N if deg < 0 and best[1] > POD_N / 2 else 0)


def pod_inset(y):
    """The core is the plan minus the plates, except at the bare gunmetal nose cap."""
    return POD_PLATE * smooth01((y - 7.25) / 0.6)


def pod_loop(y, side=1, grow=0.0):
    xo, xi = (PXO_R if side > 0 else PXO)(y), PXI(y)
    cx = side * (xo + xi) / 2
    rx = max(0.15, (xo - xi) / 2 - pod_inset(y) + grow)
    rz = max(0.15, PRZ(y) - pod_inset(y) + grow)
    # The right pod's belly hangs a little deeper (POD_KEEL_R): frame 9, the hard bank that lifts
    # the right side, is drawn a pixel wider on the right than frame 17 is on the left.
    k = POD_KEEL_R - 1.0 if side > 0 else 0.0
    return [(cx + side * rx * u, POD_CZ + rz * v * (1.0 + k * max(0.0, u) if v < 0 else 1.0)) for u, v in POD_UNIT], (cx, POD_CZ)


# Body: the core between the decks, from its front face at row 8.25 (between the jaws) to the
# engine's dark rear lip at row 25.95. (row, half width, top, keel)
_BY = [9.0, 9.2, 9.6, 10.4, 12.0, 15.0, 19.0, 20.5, 21.6, 22.5, 23.0, 24.2, 24.55, 24.8, 25.0]
BW = pchip(_BY, [5.7, 6.1, 6.2, 6.2, 6.2, 6.2, 6.2, 6.2, 6.2, 6.2, 5.25, 5.2, 5.15, 5.0, 4.7])
BT = pchip(_BY, [1.35, 1.5, 1.8, 2.0, 2.1, 2.1, 2.0, 1.45, 1.2, 1.15, 1.1, 1.1, 1.1, 1.05, 1.0])
BB = pchip(_BY, [-0.5, -0.85, -1.3, -1.7, -2.05, -2.15, -2.15, -2.1, -2.05, -2.0, -1.9, -1.8, -1.7, -1.6, -1.45])
B_DECK, B_SHOULDER, B_FLANK, B_CHINE = 0.62, 0.22, 0.15, 0.0


def body_loop(y):
    """Closed section: s = 0 top centre, 1 deck edge, 2 shoulder, 3 flank foot, 4 chine, 5 keel;
    then back up the left side (s 6-9)."""
    w, t, b = BW(y), BT(y), BB(y)
    h = t - b
    right = [(0.0, t), (B_DECK * w, t), (w, t - B_SHOULDER * h), (w, b + B_FLANK * h), (B_DECK * w, b + B_CHINE * h),
             (0.0, b)]
    pts = right + [(-x, z) for x, z in reversed(right[1:-1])]
    return pts, (0.0, (t + b) / 2)


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # Sprite px to Blender: X = (x + 0.5) / 12, Y = (14 - y) / 12, Z = z / 12 (a reflection in y).
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def mirror_pts(pts, side):
    return [(side * x, y, z) for x, y, z in pts]


def inset_poly(poly, d):
    """Shrink a convex plan polygon (x, y) by d (miter offsets)."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        nx, ny = dy / ln, -dx / ln
        if nx * ((x0 + x1) / 2 - cx) + ny * ((y0 + y1) / 2 - cy) < 0:
            nx, ny = -nx, -ny
        lines.append((x0 - nx * d, y0 - ny * d, dx, dy))
    out = []
    for i in range(n):
        ax, ay, adx, ady = lines[i - 1]
        bx, by, bdx, bdy = lines[i]
        den = adx * bdy - ady * bdx
        if abs(den) < 1e-9:
            out.append((bx, by))
            continue
        t = ((bx - ax) * bdy - (by - ay) * bdx) / den
        out.append((ax + adx * t, ay + ady * t))
    return out


def slab(part, poly, ztop, zbot, ch, mat, side=1):
    """A chamfered slab over a convex plan polygon; ztop/zbot are functions of (x, y) (planar)."""
    pts = []
    for (x, y), (ix, iy) in zip(poly, inset_poly(poly, ch)):
        pts += [(x, y, ztop(x, y) - ch), (x, y, zbot(x, y) + ch), (ix, iy, ztop(ix, iy)), (ix, iy, zbot(ix, iy))]
    hull(part, mirror_pts(pts, side), mat)


def stations_hull(part, stations, mat, side=1, ch=0.14):
    """Convex chamfered pieces between consecutive stations (y, x_in, x_out, z_bot, z_top)."""
    def sec(y, xi, xo, zb, zt):
        return [(xi, y, zb), (xi, y, zt - ch), (xi + ch, y, zt), (xo - ch, y, zt), (xo, y, zt - ch), (xo, y, zb)]
    for a, b in zip(stations, stations[1:]):
        hull(part, mirror_pts(sec(*a) + sec(*b), side), mat)


# --- the ship --------------------------------------------------------------------------------

def build_pods(P, D):
    for side in (1, -1):
        def L(y, side=side):
            return pod_loop(y, side)

        def G(y, grow, side=side):
            return pod_loop(y, side, grow)
        rings = [(G, y, 0.0) for y in [POD_START, 7.1, 7.25, 7.4, 7.6, 7.85] + frange(8.15, POD_END, 0.7)]
        loft_rings(P, rings, [GUN] * len(rings))

        def A(a, b, gap=0.0):
            return dict(s0=pod_s(a) + gap, s1=pod_s(b) - gap)
        # Front cowl: four armour petals over the round nose, the bare gunmetal cap at its tip.
        for a, b in ((-48, 57), (57, 133), (133, 224), (224, 312)):
            plate(P, L, 7.6, 10.0, POD, **A(a, b, 0.1), d=POD_PLATE, c=0.12, ystep=0.35)
        # Shell: two thick top strips with a lengthwise seam, from the cowl to the tail cap (the
        # sprite's seams run lengthwise; its bright top pixels are sheen on them).
        plate(P, L, 10.15, 20.25, POD, **A(-38, 2), d=0.42, c=0.14, ystep=0.7)
        plate(P, L, 10.15, 20.25, POD, **A(4, 46), d=0.42, c=0.14, ystep=0.7)
        # Outboard flank (the plan's outer edge), in two behind the fin root; lower; inboard.
        plate(P, L, 10.15, 15.85, POD, **A(48, 134), d=POD_PLATE, c=0.12, ystep=0.7)
        plate(P, L, 16.0, 20.25, POD, **A(48, 134), d=POD_PLATE, c=0.12, ystep=0.7)
        plate(P, L, 10.15, 20.25, POD_DK, **A(136, 222), d=POD_PLATE, c=0.12, ystep=0.7)
        plate(P, L, 10.15, 20.25, POD, **A(224, 318), d=POD_PLATE, c=0.12, ystep=0.7)
        # Access hatch on the outer top strip.
        plate(P, L, 12.4, 15.2, POD_DK, **A(14, 38), d=0.55, c=0.1, ystep=0.7)
        # Tail cap: four darker petals round the square tail, behind a panel break.
        for a, b in ((-48, 57), (57, 133), (133, 224), (224, 312)):
            plate(P, L, 20.4, POD_END + 0.1, POD_DK, **A(a, b, 0.1), d=POD_PLATE, c=0.1, ystep=0.4)
        # Aft bulkhead inside the cap, and a deep nozzle in it (dark, unlit: the sprite's only glow
        # is the engine block).
        pts = []
        for y, k in ((POD_END - 0.05, 0.9), (POD_END + 0.05, 0.9), (POD_END + 0.12, 0.8)):
            ring, (cx, cz) = pod_loop(y, side)
            pts += [(cx + (x - cx) * k, y, cz + (z - cz) * k) for x, z in ring]
        hull(P, pts, POD_DK)
        nx, nz = side * (PXO(20.5) + PXI(20.5)) / 2, POD_CZ - 0.1
        y0 = POD_END - 0.08
        prof = [(1.25, y0, GUN), (1.3, y0 + 0.12, GUN), (1.18, y0 + 0.22, GUN), (1.0, y0 + 0.22, GUN),
                (0.9, y0 - 0.5, DEEP), (0.0, y0 - 0.5, DEEP)]
        tube_profile(D, nx, nz, prof, axis_y=True)
        # Intake scoop under the pod's front: gunmetal lip, dark mouth.
        cx = side * (PXO(11.0) + PXI(11.0)) / 2
        hull(D, [(cx + side * x, y, z) for x, y, z in cbox(-1.3, 1.3, 9.9, 13.6, -3.45, -2.4, 0.25)], GUN)
        hull(D, [(cx + side * x, y, z) for x, y, z in cbox(-1.05, 1.05, 9.8, 10.05, -3.25, -2.6, 0.05)], DEEP)
        # Gear door under the pod's rear: a proud panel on the shell's belly, with hinge blocks.
        plate(P, L, 15.4, 19.3, BELLY, **A(160, 200), d=0.45, c=0.1, ystep=0.9)


def tube_profile(D, cx, cz, prof, axis_y=True, n=18):
    """A turned part along y at (cx, cz): prof = [(radius, y, mat)], radius 0 closes it."""
    rings = []
    for r, y, mat in prof:
        rings.append([D.v((cx + r * math.cos(2 * math.pi * (k + 0.5) / n), y, cz + r * math.sin(2 * math.pi * (k + 0.5) / n)))
                      for k in range(n)] if r > 0 else [D.v((cx, y, cz))])
    for i in range(len(prof) - 1):
        r0, r1 = rings[i], rings[i + 1]
        ya, yb = prof[i][1], prof[i + 1][1]
        mat = prof[i + 1][2]
        for k in range(n):
            kk = (k + 1) % n
            if len(r0) == 1:
                D.f((r0[0], r1[kk], r1[k]), mat, out=(0, -1, 0))
            elif len(r1) == 1:
                D.f((r0[k], r0[kk], r1[0]), mat, out=(0, 1 if yb > ya else -1, 0) if abs(yb - ya) > 1e-6 else (0, 1, 0))
            elif abs(ya - yb) < 1e-6:
                D.f((r0[k], r0[kk], r1[kk], r1[k]), mat, out=(0, 1, 0))
            elif prof[i + 1][0] < prof[i][0] and yb < ya:  # going back in: the inner wall faces the axis
                D.f((r0[k], r0[kk], r1[kk], r1[k]), mat, away=(cx + 50 * (r0[k].co.x - cx), (ya + yb) / 2, cz + 50 * (r0[k].co.z - cz)))
            else:
                D.f((r0[k], r0[kk], r1[kk], r1[k]), mat, away=(cx, (ya + yb) / 2, cz))


# Fins: out of each pod's flank to a blunt tip at rows 15-17 (column 1), a 45-degree leading edge
# from row 12 and a steep trailing edge back to the pod at row 19. Thin, thicker at the root.
FIN_POLY = [(17.6, 12.0), (18.7, 12.0), (21.95, 15.25), (22.15, 15.6), (22.15, 16.75), (21.1, 17.5),
            (19.1, 18.5), (17.6, 19.3)]
FIN_Z = 0.05
FENCE_KEEL_R = 1.25
# The tip fence along the fin's outer edge: (x, y, half height).
FENCE = [(19.0, 13.0, 2.2), (19.5, 13.5, 4.2), (20.5, 14.5, 4.8), (21.2, 15.2, 4.9), (21.35, 15.55, 4.9),
         (21.35, 16.8, 5.0), (20.4, 17.45, 5.1), (18.6, 18.35, 4.8), (18.0, 18.65, 3.3)]


def fin_top(x, y):
    return FIN_Z + 0.65 - 0.33 * max(0.0, x - 18.0) / 4.55


def fin_bot(x, y):
    return FIN_Z - 0.55 + 0.25 * max(0.0, x - 18.0) / 4.55


def build_fins(P, D):
    for side in (1, -1):
        slab(P, FIN_POLY, fin_top, fin_bot, 0.14, FIN, side)
        # A raised top plate inset from the edges (its gap reads as a panel line).
        top = inset_poly([(19.4, 12.75), (22.35, 15.7), (22.4, 15.95), (22.4, 16.65), (21.35, 17.35), (19.4, 18.3)], 0.3)
        slab(P, top, lambda x, y: fin_top(x, y) + 0.16, lambda x, y: fin_top(x, y) - 0.2, 0.08, FIN, side)
        # Navigation light flush in the tip's face (red to port, green to starboard is not in the
        # palette, so a small dark lens).
        hull(D, mirror_pts(cbox(22.25, 22.55, 15.75, 16.6, FIN_Z - 0.12, FIN_Z + 0.22, 0.05), side), DEEP)
        # Tip fence: a blade standing up and down along the fin's outer edge (the sprite's dark
        # blunt tip, rows 14-18). Seen from above it is only the edge; rolled to the full banking
        # frames it keeps the fin rows as wide as the sprite draws them.
        # (The right one reaches a little lower, as the right pod's belly: see pod_loop.)
        kb = FENCE_KEEL_R if side > 0 else 1.0
        for (x0, y0, h0), (x1, y1, h1) in zip(FENCE, FENCE[1:]):
            pts = []
            for x, y, h in ((x0, y0, h0), (x1, y1, h1)):
                for dx, k in ((0.0, 1.0), (-0.42, 0.92)):
                    pts += [(x + dx, y, FIN_Z + h * k), (x + dx, y, FIN_Z - h * k * kb)]
            hull(P, mirror_pts(pts, side), FIN)


def build_deck(P, D):
    for side in (1, -1):
        # The low deck between pod and body (columns 14-17, rows 9-19): a chamfered block buried in
        # both, two raised plates on top, an intake under its front edge.
        hull(P, mirror_pts(cbox(6.0, 11.0, 10.0, 19.0, -1.35, 0.95, 0.22), side), DECK)
        for y0, y1 in ((10.35, 14.45), (14.6, 18.65)):
            hull(P, mirror_pts(cbox(6.55, 10.45, y0, y1, 0.6, 1.2, 0.14), side), DECK)
        hull(D, mirror_pts(cbox(6.9, 10.1, 9.9, 10.3, -1.05, 0.4, 0.06), side), DEEP)
        for x in (7.9, 9.1):
            hull(D, mirror_pts(cbox(x - 0.09, x + 0.09, 9.84, 10.3, -1.05, 0.4, 0.03), side), GUN)


def build_body(P, D):
    L = body_loop
    loft(P, L, [9.0, 9.25, 9.55] + frange(9.95, 25.0, 0.8), GUN)
    for side in (1, -1):
        def S(a, b):
            return (a, b) if side > 0 else (10 - b, 10 - a)
        # Shoulder and flank plates (columns 18 and 30, the sprite's flank tone), and the rear flanks
        # past the shoulders.
        plate(P, L, 9.3, 18.4, BODY, *S(0.75, 2.6), d=0.3, c=0.12)
        plate(P, L, 22.95, 24.75, BODY, *S(0.75, 2.6), d=0.3, c=0.12)
        # Lower flank and belly plates.
        plate(P, L, 9.6, 24.6, BELLY, *S(2.7, 3.95), d=0.25, c=0.12, ystep=0.8)
    for y0, y1 in ((9.7, 15.9), (16.05, 24.5)):
        plate(P, L, y0, y1, BELLY, s0=4.15, s1=5.85, d=0.22, c=0.1, ystep=0.8)
    # Rear deck behind the hump, down to the engine (rows 19-20, the sprite's darker tone).
    plate(P, L, 18.9, 20.75, REAR, s0=-0.85, s1=0.85, d=0.2, c=0.1, ystep=0.5)
    # Keel strake under the centre line.
    pts = []
    for y, drop in ((10.5, 0.1), (12.0, 0.5), (21.0, 0.5), (23.5, 0.1)):
        b = BB(y) - 0.15
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.35, b + 0.4), (0.25, b - drop), (0.1, b - drop - 0.08))]
    hull(D, pts, GUN)
    # Chin guns under the jaws: twin barrels in a fairing.
    pts = []
    for y in (8.9, 9.8, 11.4):
        b = BB(max(y, 9.3)) + 0.1
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((1.9, b + 0.3), (1.9, b - 0.35), (1.6, b - 0.55))]
    hull(D, pts, GUN)
    for sx in (-1, 1):
        prof = [(0.0, 8.7, GUN), (0.2, 8.7, GUN), (0.2, 9.1, GUN), (0.26, 9.2, GUN), (0.26, 9.9, GUN), (0.0, 9.9, GUN)]
        tube_profile(D, sx * 1.25, BB(9.3) - 0.15, prof, n=8)
    # The front face between the jaws: a dark sensor slot.
    hull(D, cbox(-2.1, 2.1, 8.9, 9.15, BT(9.0) - 0.75, BT(9.0) - 0.35, 0.05), DEEP)


# Jaw ridges either side of the cockpit (columns 19-20 and 28-29), their tips hooking in to column 21
# at row 7 in front of the windshield. (row, x in, x out, z bottom, z top)
RIDGE_ST = [(8.0, 2.75, 5.2, 0.4, 2.0), (8.25, 2.45, 5.45, 0.2, 2.3), (9.25, 2.45, 5.45, 0.5, 2.85),
            (9.4, 3.45, 5.45, 0.6, 2.95), (10.0, 3.45, 5.45, 0.9, 3.2), (12.0, 3.45, 5.45, 1.2, 3.35),
            (16.0, 3.45, 5.45, 1.2, 3.25), (18.4, 3.6, 5.3, 1.2, 2.55)]


def build_top(P, D):
    for side in (1, -1):
        stations_hull(P, RIDGE_ST, RIDGE, side)
        # A polished strip along each ridge's top (the sprite's bright column), set into it.
        st = [(y, xi + 0.55, xo - 0.55, zt - 0.3, zt + 0.12) for y, xi, xo, zb, zt in RIDGE_ST[3:-1]]
        stations_hull(P, st, SPINE, side, ch=0.07)
        # Rear shoulders flanking the engine (columns 16-18, rows 19-22): chamfered blocks with a
        # dark vent of three slots on top.
        # (Tall: rolled to the banking frames, their corners hold the rear's width.)
        hull(P, mirror_pts(cbox(5.9, 8.45, 18.55, 19.95, -2.0, 2.1, 0.25), side), SHOULDER)
        hull(P, mirror_pts(cbox(5.9, 7.45, 18.55, 21.95, -2.0, 2.1, 0.2), side), SHOULDER)
        hull(P, mirror_pts(cbox(5.5, 6.45, 21.5, 22.95, -1.75, 1.95, 0.2), side), SHOULDER)
        hull(D, mirror_pts(cbox(6.3, 7.1, 19.0, 21.6, 1.85, 2.15, 0.06), side), DEEP)
        for y in (19.45, 20.25, 21.05):
            hull(D, mirror_pts(cbox(6.25, 7.15, y - 0.13, y + 0.13, 1.85, 2.2, 0.04), side), SHOULDER)
    # Dorsal hump behind the cockpit (rows 14-19), with a spine strip.
    st = [(14.0, -3.5, 3.5, 1.5, 3.15), (15.5, -3.5, 3.5, 1.5, 3.25), (18.0, -3.5, 3.5, 1.5, 3.05),
          (19.45, -3.3, 3.3, 1.4, 2.3)]
    stations_hull(P, st, HUMP, 1, ch=0.3)
    st = [(14.3, -0.55, 0.55, 2.9, 3.33), (15.5, -0.55, 0.55, 3.0, 3.43), (18.0, -0.55, 0.55, 2.8, 3.23),
          (19.0, -0.5, 0.5, 2.3, 2.75)]
    stations_hull(P, st, SPINE, 1, ch=0.1)


# Windshield: fills the sunken cockpit between the ridges (columns 21-27, rows 9-13), raked from a
# low front sill at row 8.9 up to a crown at row 12, its rear edge on the hump at row 14.
GL_Y0, GL_Y1, GL_W = 9.4, 14.05, 3.47


def glass_crown(y):
    return pchip([9.4, 9.9, 10.8, 12.0, 13.5, 14.05], [2.05, 2.55, 2.92, 3.12, 3.12, 3.05])(y)


def build_canopy(G, D):
    ys = [9.4, 9.55, 9.8, 10.15, 10.6, 11.1, 11.7, 12.4, 13.2, 13.7, 14.05]
    xs = [-1 + 2 * k / 12 for k in range(13)]
    grid = []
    for y in ys:
        row = []
        # Rear corners rounded a little (the sprite's cockpit is square at the back).
        w = GL_W - 0.5 * (1 - math.sqrt(max(0.0, 1 - ((max(0.0, y - 13.55)) / 0.5) ** 2)))
        for u in xs:
            z = glass_crown(y) - 0.32 * u * u
            row.append(G.v((u * w, y, z)))
        grid.append(row)
    for r0, r1 in zip(grid, grid[1:]):
        for i in range(len(xs) - 1):
            G.f((r0[i], r0[i + 1], r1[i + 1], r1[i]), GLASS, out=(0, -0.3, 1))
    # Walls down into the body: front, rear and sides.
    base = 1.2
    for row, out in ((grid[0], (0, -1, 0)), (grid[-1], (0, 1, 0))):
        low = [G.v((v.co.x, v.co.y, base)) for v in row]
        for i in range(len(row) - 1):
            G.f((row[i], row[i + 1], low[i + 1], low[i]), GLASS, out=out)
    for k, sx in ((0, -1), (-1, 1)):
        col = [r[k] for r in grid]
        low = [G.v((v.co.x, v.co.y, base)) for v in col]
        for i in range(len(col) - 1):
            G.f((col[i], col[i + 1], low[i + 1], low[i]), GLASS, out=(sx, 0, 0))
    # Front sill: a gunmetal bar across the foot of the windshield.
    hull(D, cbox(-GL_W, GL_W, 9.05, 9.5, BT(9.3) - 0.2, glass_crown(9.4) + 0.05, 0.08), GUN)


def build_engine(P, D):
    # Housing on the body's rear deck (columns 19-29, rows 21-24): a red frame round a glowing bed
    # with four dark vanes along it (the sprite's dark columns 21, 23, 25, 27); the bed's hot cores
    # in the middle slots. The dark lip behind it is the body's end (row 25).
    z0, ztop, zbed = 0.9, 1.75, 1.35
    hull(P, cbox(-5.4, 5.4, 20.7, 24.95, z0, ztop, 0.15), ENG)
    hull(D, cbox(-4.5, 4.5, 21.05, 24.65, zbed - 0.1, ztop + 0.02, 0.04), GLOW)
    for x in (-3.0, -1.0, 1.0, 3.0):
        hull(D, cbox(x - 0.45, x + 0.45, 20.95, 24.75, zbed, ztop + 0.1, 0.12), VANE)
    for x in (-2.0, 0.0, 2.0):
        hull(D, cbox(x - 0.4, x + 0.4, 22.15, 23.85, zbed, zbed + 0.06, 0.02), HOT)
    # Rear face: the exhaust grille on the body's end (below the lip): a dark frame, a glowing bed,
    # vanes continuing the top's.
    y = 24.95
    hull(D, cbox(-4.9, 4.9, y - 0.2, y + 0.06, -1.05, 0.75, 0.06), DEEP)
    hull(D, cbox(-4.5, 4.5, y - 0.15, y + 0.1, -0.85, 0.55, 0.04), GLOW)
    for x in (-3.0, -1.0, 1.0, 3.0):
        hull(D, cbox(x - 0.4, x + 0.4, y - 0.2, y + 0.3, -0.9, 0.6, 0.08), VANE)
    for x in (-2.0, 0.0, 2.0):
        hull(D, cbox(x - 0.35, x + 0.35, y - 0.1, y + 0.13, -0.6, 0.3, 0.03), HOT)


def build(coll, sprite):
    mats = materials(sprite)
    P = Part("dragonwing_hull", smooth_angle=30)
    D = Part("dragonwing_details", smooth_angle=35)
    pods = Part("dragonwing_pods", smooth_angle=34)
    G = Part("dragonwing_canopy", smooth_angle=60)
    build_body(P, D)
    build_deck(P, D)
    build_top(P, D)
    build_engine(P, D)
    build_fins(P, D)
    build_pods(pods, D)
    build_canopy(G, D)
    objs = [finish(p, mats, coll) for p in (P, pods, D, G)]
    for o in objs:
        print("dragonwing part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

TEXTURED = (POD, POD_DK, FIN, DECK, BODY, RIDGE, HUMP, REAR, SHOULDER, GUN, DEEP, BELLY, SPINE)


def bake_maps(obj, out_dir, size=1024, samples=96):
    """The Talon's bake (usp_talon.bake_maps) with this ship's slots: a grey colour multiplier
    (occlusion at two scales and a light lift on bevelled edges, tinted cool: TINT) and a
    metallic-roughness map (G roughness, B metallic); Base Color = map x palette colour."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("dragonwing: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")

    col_img = bpy.data.images.new("dragonwing_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("dragonwing_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.62, math_("MULTIPLY", occl, 0.5)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i in TEXTURED:
        m = mats[i]
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    obj = join(build(coll, sprite), NAME)
    # The outline shell is made from the closed parts, before hidden faces are culled (remeshing
    # the culled, open hull would wrap both sides of every open plate).
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"dragonwing: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glows (src/ui/backdrop.ts): just behind the engine's rear grille,
    # in glTF axes (x, y up, z aft), red-orange (palette 120's hue).
    obj["tyrian_engines"] = {"color": "#ff4a12", "at": [[round((sx * 2.5 + 0.5) * PX, 4), round(-0.15 * PX, 4),
                                                          round((25.8 - 14) * PX, 4)] for sx in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="dragonwing_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(closed, coll, faces=1500)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"dragonwing: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        frame = next(f for f in sprite["frames"] if f["image"].endswith("-13.png"))
        ref = root / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=(frame["width"], frame["height"]))


if __name__ == "__main__":
    main()
