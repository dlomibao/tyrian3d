"""ASTEROID?'s cross pad (map 1-3 rows 233-237, shapesz 5x5 pattern, layer 0), hard-surface rebuild.

A square body of grey machinery set into a ring of rock, a raised gunmetal cross on it carrying
three red light capsules per arm in silver bezels and a hot core in a framed square at the centre.
Everything is read off the tile art (pattern px, origin top-left, y down):

- the rock ring is not modelled: the tiles stay drawn under the model (keepTiles, layer 0), so the
  HD ground's own painting of these tiles shows round it, the same rock as the islands beside it
  (D86; boulders or slabs would break with them, D63/D66);
- the body: a chamfered octagon with a spine under the vertical arm, stepping down at both ends to
  the art's ribbed columns running out into the rock, quadrants of plates split by panel gaps,
  bolts, vents, hatches and a pipe along each arm;
- the cross: one chamfered slab (exactly the five enemy cells, top 0.30), the capsules (red blobs
  of the art, bezel = their 1-2 px silver ring, index 8; lens 113 glowing) and the core (113).

Geometry only from the tiles; no concept is projected (art rule 4). The only texture is the
model's AO/roughness bake (Building.bake_model, ground=0: the HD ground under it).
No D51 outline shell: tile models draw no ink outline (structureInstances.ts turns it off, tiles join
edge to edge, D8), so a shell would only add an instanced draw and a shadow caster (D141).

    Blender --background --factory-startup --python assets/blender/tiles/l1bld_cross_pad.py -- [--no-bake] [--preview x.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402


# --- Layout (pattern px) --------------------------------------------------------------------------
BODY = (24, 30, 96, 110)  # the machinery's octagon (box), corners cut BODY_CUT
BODY_CUT = 15
SPINE = (45, 26, 75, 114)  # the spine under the vertical arm (a lip past the octagon)
SPINE_ENDS = [(46, 16, 74, 31), (46, 109, 74, 122)]  # its lower steps, out into the rock
V_ARM = (48, 28, 72, 112)  # cells (1,2), (2,2), (3,2)
H_ARM = (24, 56, 96, 84)  # cells (2,1), (2,2), (2,3)
# Red lights (bbox of the art's red pixels, px): vertical arm (lying across x), horizontal (standing)
CAPS_V = [(50, 30, 68, 37), (50, 39, 68, 46), (50, 48, 68, 55), (50, 86, 68, 93), (50, 95, 68, 102), (50, 104, 68, 111)]
CAPS_H = [(25, 61, 31, 79), (33, 61, 39, 79), (41, 61, 47, 79), (73, 61, 79, 79), (81, 61, 87, 79), (89, 61, 95, 79)]
CORE = (52, 60, 67, 80)
# The four machinery quadrants (between the arms, inside the octagon)
QUADS = [(25.5, 31.5, 47, 55), (73, 31.5, 94.5, 55), (25.5, 85, 47, 108.5), (73, 85, 94.5, 108.5)]

# --- Heights --------------------------------------------------------------------------------------
BODY_Z = 0.20  # the body's deck
PLATE_Z = 0.245  # quadrant plates
ARM_Z = 0.30  # the cross's top (enemy cells: 0.30..0.38)
BEZEL_Z = 0.342
LENS_Z = 0.362
CORE_Z = 0.370
END_Z = 0.09  # the spine's end steps

# --- Palette indices (the art's own, per region: medians without the darkest / brightest) -------
I_ARM, I_ARM_EDGE = 6, 7
I_BEZEL = 8
I_BODY, I_BODY_DARK, I_PLATE_A, I_PLATE_B = 4, 2, 5, 4  # quadrants: the art's mode 5, median 4
I_LENS, I_CORE = 113, 113
I_LENS_HOT, I_CORE_HOT = 115, 116  # the art's brightest streaks: the glow's crest
I_PIPE = 6


def clip_convex(poly, clip):
    """Sutherland-Hodgman: `poly` clipped to the convex polygon `clip` (both pattern px)."""
    def area(p):
        return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2
    if area(clip) < 0:
        clip = list(reversed(clip))
    out = list(poly)
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

        def cut(p, q):
            dx1, dy1 = q[0] - p[0], q[1] - p[1]
            dx2, dy2 = b[0] - a[0], b[1] - a[1]
            den = dx1 * dy2 - dy1 * dx2
            t = ((a[0] - p[0]) * dy2 - (a[1] - p[1]) * dx2) / den
            return (p[0] + t * dx1, p[1] + t * dy1)

        src, out = out, []
        for j in range(len(src)):
            p, q = src[j], src[(j + 1) % len(src)]
            if inside(q):
                if not inside(p):
                    out.append(cut(p, q))
                out.append(q)
            elif inside(p):
                out.append(cut(p, q))
        if not out:
            return []
    return out


def octagon(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def stadium(x0, y0, x1, y1, grow=0.0, segs=4):
    """A capsule's outline round a box (px): round ends on the short sides."""
    x0, y0, x1, y1 = x0 - grow, y0 - grow, x1 + grow, y1 + grow
    r = min(x1 - x0, y1 - y0) / 2
    return lb.Building.rounded_box(None, x0, y0, x1, y1, corner_px=r * 0.999, segments=segs)


def loft_cap(s, polys, mat, smooth=True, top_mat=None):
    """A closed, lofted solid through rings `polys` [(poly px, z), ...] (same vertex count), bottom
    and top capped: lens domes and the like."""
    bm = bmesh.new()
    rings = [[bm.verts.new((s.x(x), s.y(y), z)) for x, y in poly] for poly, z in polys]
    n = len(rings[0])
    top_mat = mat if top_mat is None else top_mat
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    bm.faces.new(rings[-1]).material_index = top_mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=smooth)


def shrink(poly, cx, cy, k):
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in poly]


def pipe(s, p0, p1, z_floor, r_px, mat, flange_mat, sides=8):
    """A pipe on a floor between two px points with collars at both ends (closed cylinders)."""
    def cyl(a, b, zc, r):
        bm = bmesh.new()
        x0, y0, x1, y1 = s.x(a[0]), s.y(a[1]), s.x(b[0]), s.y(b[1])
        ln = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / ln, (x1 - x0) / ln
        rings = []
        for cx, cy in ((x0, y0), (x1, y1)):
            rings.append([bm.verts.new((cx + nx * r * math.cos(2 * math.pi * (k + 0.5) / sides),
                                        cy + ny * r * math.cos(2 * math.pi * (k + 0.5) / sides),
                                        zc + r * math.sin(2 * math.pi * (k + 0.5) / sides))) for k in range(sides)])
        for k in range(sides):
            m = (k + 1) % sides
            bm.faces.new((rings[0][k], rings[0][m], rings[1][m], rings[1][k])).material_index = mat_i[0]
        bm.faces.new(rings[0]).material_index = mat_i[0]
        bm.faces.new(list(reversed(rings[1]))).material_index = mat_i[0]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm, smooth=True)

    r = r_px * lt.PX
    zc = z_floor + r * 0.35  # half sunk into the deck (in a cradle)
    mat_i = [mat]
    cyl(p0, p1, zc, r)
    ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ux, uy = (p1[0] - p0[0]) / ln, (p1[1] - p0[1]) / ln
    mat_i[0] = flange_mat
    for (px, py), sg in ((p0, 1), (p1, -1)):
        cyl((px + sg * ux * 0.4, py + sg * uy * 0.4), (px + sg * ux * 1.6, py + sg * uy * 1.6), zc, r * 1.3)


# --- Machinery ------------------------------------------------------------------------------------

def body(s):
    edge = s.m(I_BODY_DARK, metallic=0.3, roughness=0.6)
    deck = s.m(I_BODY, metallic=0.5, roughness=0.5)
    oct_ = octagon(*BODY, BODY_CUT)
    s.slab(oct_, lb.SLAB_BOTTOM, BODY_Z, deck, chamfer_px=1.2, drop=0.025, side_mat=edge)
    # the spine under the vertical arm: a lip past the octagon, then a lower step at each end with the
    # art's ribbed columns ("|| ||" above and below the arm) running out into the rock
    s.slab(s.rounded_box(*SPINE, corner_px=3, segments=2), lb.SLAB_BOTTOM, BODY_Z - 0.006, deck,
           chamfer_px=1.0, drop=0.02, side_mat=edge)
    pipe_m = s.m(I_PIPE, metallic=0.55, roughness=0.4)
    flange = s.m(I_BEZEL, metallic=0.6, roughness=0.35)
    for box, (ya, yb) in zip(SPINE_ENDS, ((17.5, 29.6), (110.4, 120.5))):
        s.slab(s.rounded_box(*box, corner_px=3, segments=2), lb.SLAB_BOTTOM, END_Z, deck,
               chamfer_px=2.2, drop=0.04, side_mat=edge)
        for x in (49.0, 53.0, 67.0, 71.0):
            pipe(s, (x, ya), (x, yb), END_Z, 1.1, pipe_m, flange)
        s.slab(s.rounded_box(56.5, ya + 1, 63.5, yb - 1, 1.0), END_Z - 0.02, END_Z + 0.03,
               s.m(I_PLATE_A, metallic=0.35, roughness=0.5), chamfer_px=0.7, drop=0.012)
        s.bolts([(58, ya + 2.5), (62, ya + 2.5), (58, yb - 2.5), (62, yb - 2.5)], END_Z + 0.03, r_px=0.55,
                height=0.01, mat=flange)
    # quadrants: a sunk frame floor, 2 x 2 plates split by panel gaps (clipped by the octagon), bolts,
    # a pipe along the arm
    plate_a = s.m(I_PLATE_A, metallic=0.35, roughness=0.5)
    plate_b = s.m(I_PLATE_B, metallic=0.35, roughness=0.55)
    clip = octagon(BODY[0] + 1.5, BODY[1] + 1.5, BODY[2] - 1.5, BODY[3] - 1.5, BODY_CUT - 0.6)
    for k, (x0, y0, x1, y1) in enumerate(QUADS):
        left = k % 2 == 1  # right quadrants: the arm is on their left
        top = k >= 2  # bottom quadrants: the arm is above
        # pipe channel next to the vertical arm: 4 px
        if left:
            px_pipe, x0p = x0 + 2.2, x0 + 4.5
            x1p = x1
        else:
            px_pipe, x1p = x1 - 2.2, x1 - 4.5
            x0p = x0
        gap = 0.9
        mx = (x0p + x1p) / 2
        ys_ = [y0 + (y1 - y0) * f for f in (0.0, 0.36, 0.68, 1.0)] if not top else [y0 + (y1 - y0) * f for f in (0.0, 0.32, 0.64, 1.0)]
        inner_col = 0 if left else 1
        inner_row = 2 if not top else 0
        for row in range(3):
            for col in range(2):
                a, cc = (x0p, mx - gap / 2) if col == 0 else (mx + gap / 2, x1p)
                b, d = ys_[row] + (gap / 2 if row else 0), ys_[row + 1] - (gap / 2 if row < 2 else 0)
                poly = clip_convex(s.rounded_box(a, b, cc, d, 0.9, 1), clip)
                if len(poly) < 3:
                    continue
                checker = (row + col) % 2 == 0
                z = PLATE_Z + (0.010 if checker else 0.0)
                pm = plate_a if checker else plate_b
                vent = col == inner_col and row == inner_row
                hatch = row == 1 and col != inner_col
                if not (vent or hatch):
                    s.slab(poly, BODY_Z - 0.02, z, pm, chamfer_px=0.7, drop=0.012)
                    continue
                # a recess: the plate as a frame (rim) round a lower floor
                s.rim(poly, 1.3, BODY_Z - 0.02, z, pm)
                s.slab(shrink(poly, (a + cc) / 2, (b + d) / 2, 0.97), BODY_Z - 0.02, z - 0.025,
                       s.m(2 if vent else 3, metallic=0.3, roughness=0.65), chamfer_px=0)
                if vent:
                    vx0, vy0, vx1, vy1 = a + 1.3, b + 1.3, cc - 1.3, d - 1.3
                    nsl = max(2, int((vy1 - vy0) // 1.4))
                    for i in range(nsl):
                        sy = vy0 + 0.7 + i * (vy1 - vy0 - 1.4) / (nsl - 1)
                        s.slab([(vx0, sy - 0.28), (vx1, sy - 0.28), (vx1, sy + 0.28), (vx0, sy + 0.28)],
                               z - 0.03, z - 0.006, plate_b, chamfer_px=0)
                else:
                    s.bolts([((a + cc) / 2, (b + d) / 2)], z - 0.025, r_px=0.8, height=0.012, mat=flange)
        # bolts at the plates' inner corners (near the arms, always inside the octagon)
        bx = x0p + 1.5 if left else x1p - 1.5
        s.bolts([(bx, y0 + 1.5), (bx, y1 - 1.5)], PLATE_Z + 0.008, r_px=0.55, height=0.01, mat=flange)
        pipe(s, (px_pipe, y0 + 1.5), (px_pipe, y1 - 1.5), BODY_Z, 1.15, pipe_m, flange)
    # a cross pipe along the horizontal arm's edges inside the quadrants (between the arm and plates)
    return oct_


def cross(s):
    arm = s.m(I_ARM, metallic=0.5, roughness=0.45)
    edge = s.m(I_ARM_EDGE, metallic=0.5, roughness=0.4)
    side = s.m(3, metallic=0.4, roughness=0.55)
    vx0, vy0, vx1, vy1 = V_ARM
    hx0, hy0, hx1, hy1 = H_ARM
    c = 1.5  # outer corners cut
    poly = [(vx0 + c, vy0), (vx1 - c, vy0), (vx1, vy0 + c), (vx1, hy0), (hx1 - c, hy0), (hx1, hy0 + c), (hx1, hy1 - c),
            (hx1 - c, hy1), (vx1, hy1), (vx1, vy1 - c), (vx1 - c, vy1), (vx0 + c, vy1), (vx0, vy1 - c), (vx0, hy1),
            (hx0 + c, hy1), (hx0, hy1 - c), (hx0, hy0 + c), (hx0 + c, hy0), (vx0, hy0), (vx0, vy0 + c)]
    s.slab(poly, BODY_Z - 0.03, ARM_Z, arm, chamfer_px=1.0, drop=0.02, side_mat=side, bevel_mat=edge)
    # a raised rail (step) round the arm's edges: the art's light line framing the capsules
    bezel = s.m(I_BEZEL, metallic=0.65, roughness=0.32)
    lens = s.m(I_LENS, emission_strength=1.2, roughness=0.18, metallic=0.0)
    lens_hot = s.m(I_LENS_HOT, emission_strength=1.6, roughness=0.15, metallic=0.0)
    lens_rim = s.m(112, metallic=0.2, roughness=0.3)
    clamp = s.m(I_ARM_EDGE, metallic=0.55, roughness=0.38)
    for (x0, y0, x1, y1) in CAPS_V + CAPS_H:
        out = stadium(x0, y0, x1, y1, grow=1.3)
        s.rim(out, 1.5, ARM_Z - 0.01, BEZEL_Z, bezel, chamfer_px=0.5, drop=0.008)
        # dark well floor and the lens dome
        s.slab(stadium(x0, y0, x1, y1, grow=0.0), ARM_Z - 0.01, ARM_Z + 0.012, lens_rim, chamfer_px=0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        base = stadium(x0, y0, x1, y1, grow=-0.1, segs=6)
        rings = [(base, ARM_Z + 0.008)]
        for sc, z in ((0.97, LENS_Z - 0.022), (0.86, LENS_Z - 0.008), (0.62, LENS_Z)):
            # shrink the short side more than the long one: a pill-shaped glass top
            w, h = x1 - x0, y1 - y0
            kx = 1 - (1 - sc) * (min(w, h) / w) * 1.2
            ky = 1 - (1 - sc) * (min(w, h) / h) * 1.2
            rings.append(([(cx + (x - cx) * kx, cy + (y - cy) * ky) for x, y in base], z))
        loft_cap(s, rings, lens, top_mat=lens_hot)
    # clamps between neighbouring capsules (bridges on the bezels, as in the concept)
    for (a, b) in zip(CAPS_V, CAPS_V[1:]):
        if b[1] - a[3] < 6:
            ym = (a[3] + b[1]) / 2
            s.slab(s.rounded_box(56.5, ym - 1.0, 61.5, ym + 1.0, 0.4, 1), ARM_Z, BEZEL_Z + 0.006, clamp, chamfer_px=0.4, drop=0.006)
    for (a, b) in zip(CAPS_H, CAPS_H[1:]):
        if b[0] - a[2] < 6:
            xm = (a[2] + b[0]) / 2
            s.slab(s.rounded_box(xm - 1.0, 67.5, xm + 1.0, 72.5, 0.4, 1), ARM_Z, BEZEL_Z + 0.006, clamp, chamfer_px=0.4, drop=0.006)
    # bolts on the arm's tips
    flange = s.m(I_BEZEL, metallic=0.6, roughness=0.35)
    s.bolts([(50.5, 57.5), (69.5, 57.5), (50.5, 82.5), (69.5, 82.5)], ARM_Z, r_px=0.6, height=0.012, mat=flange)
    # The core: a chamfered square frame (rim), clamp plates on its sides, a dark well, the glowing lens
    x0, y0, x1, y1 = CORE
    frame = s.rounded_box(x0 - 2.2, y0 - 2.2, x1 + 2.2, y1 + 2.2, 2.6, 1)
    s.rim(frame, 2.4, ARM_Z - 0.01, CORE_Z - 0.006, bezel, chamfer_px=0.7, drop=0.01)
    s.slab(s.rounded_box(x0, y0, x1, y1, 1.6, 1), ARM_Z - 0.01, ARM_Z + 0.012, lens_rim, chamfer_px=0)
    core = s.m(I_CORE, emission_strength=1.6, roughness=0.15)
    base = s.rounded_box(x0 + 0.1, y0 + 0.1, x1 - 0.1, y1 - 0.1, 1.6, 2)
    ccx, ccy = (x0 + x1) / 2, (y0 + y1) / 2
    loft_cap(s, [(base, ARM_Z + 0.008), (shrink(base, ccx, ccy, 0.95), CORE_Z - 0.012), (shrink(base, ccx, ccy, 0.82), CORE_Z)], core,
             top_mat=s.m(I_CORE_HOT, emission_strength=1.8, roughness=0.12))
    for bx in ((ccx - 3, y0 - 3.2, ccx + 3, y0 - 0.8), (ccx - 3, y1 + 0.8, ccx + 3, y1 + 3.2),
               (x0 - 3.2, ccy - 3, x0 - 0.8, ccy + 3), (x1 + 0.8, ccy - 3, x1 + 3.2, ccy + 3)):
        s.slab(s.rounded_box(*bx, 0.5, 1), ARM_Z, CORE_Z + 0.002, clamp, chamfer_px=0.5, drop=0.008)


def objects_of(s):
    """Building.objects without a terraced deck (as lib_tyrbld.Structure.objects does)."""
    coll = common.reset_collection(f"{lb.SHAPES}-{s.prefix}-{s.name}")
    bmesh.ops.recalc_face_normals(s.parts, faces=s.parts.faces)
    return [lb.mesh_object(f"{lb.SHAPES}-{s.prefix}-{s.name}-parts", s.parts, s.pal.materials, coll)]


def build(bake=True):
    s = lb.Building("cross-pad")
    body(s)
    yy, xx = np.mgrid[0:s.H, 0:s.W] + 0.5
    x0, y0, x1, y1 = BODY
    c = BODY_CUT
    body_mask = ((xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1) & (xx - x0 + yy - y0 >= c) & (x1 - xx + yy - y0 >= c)
                 & (xx - x0 + y1 - yy >= c) & (x1 - xx + y1 - yy >= c))
    body_mask |= s.box_mask(*SPINE)
    for box in SPINE_ENDS:
        body_mask |= s.box_mask(*box)
    cross(s)
    objects = objects_of(s)
    s.check(objects)
    # The rock ring is the HD ground's own painting of these tiles (keepTiles: drawn under the model,
    # as the islands round it, D86); the model is the machinery only, so its mask is the body's.
    iou = s.top_iou(objects, body_mask)
    tris = sum(len(p.vertices) - 2 for o in objects for p in o.data.polygons)
    print(f"RESULT iou={iou:.4f} tris={tris}")
    if bake:
        objects = s.bake_model(objects, ground=0.0)
    if lt.preview_arg():
        lt.preview(s.ts, objects, s.pattern, Path(lt.preview_arg()) if str(lt.preview_arg()).endswith(".png") else Path(lt.preview_arg()) / "shapesz-l1bld-cross-pad.png", view_px=480)
    s.export(objects, baked=bake)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv)
