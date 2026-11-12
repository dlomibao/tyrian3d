"""Tropical Cherry Companion (sidekick 29, tyrian.shp#8 frames 113, 132 and 151), final.

What it is: a small companion drone that trails the player's ship along its path (style 3, like
its green sibling Mint-O-Ship, frames 112/131/150 of the same sheet columns; the two sprites are
the same drawing, pixel for pixel, in another colour ramp). The sprite is an egg 10 px wide and
13 px long in its 12x14 block, centred on column edge 7, drawn in the red/orange ramp 114-127:
- a dark ink ring (index 114, luma 24) on about 70% of its boundary: the game draws its own ink
  outline, so the hull's top view sits on the INNER edge of that ring (D74): 8 px wide (rows 3-8),
  6 px at rows 2, 9 and 10, 4 px at rows 1 and 11;
- an orange shell (123) with a white sheen streak at its upper left (rows 2-6, cols 4-6: sheen on
  the satin shell, not geometry);
- a lens at columns 6-7, rows 5-7 that charges up (cells (7,5), (6,6), (7,6), (6,7), (7,7) change
  over the frames): 125/123/120 on frame 113, 126/125 on 132 and white (127/126/124) on 151, the
  animation running 113, 132, 151, 132; so its centre is (7.0, 6.45), not row 6;
- a darker band (117-119, with 114-116 in its deepest part) that curls from above-right of the lens
  round under it and out to the lower left (rows 4-9): the "swirl". It is not plain shading: the
  flank beyond it brightens again (122-124, a 127 rim glint at row 9), so it is modelled as a real
  feature: a broad recessed swirl well (floor 116) inside a raised rim (118) that curls from the
  lens's top round its right and fills the dark lower-right mass down to the tail;
- a darker tail cowl (rows 9-11: dark 116-118 between two orange streaks (4,9)-(5,10)-(6,11) and
  (8,10)-(7,11), 121-124) and a deep red lower hull (118).

Built as a believable machine: a satin orange upper shell domed high over a deep-red rounded lower
hull, parted by a recessed equator seam; shallow panel grooves across the nose cap and the aft
cowl; a glowing lens dome in a thin dark bezel; the swirl well, a dark pocket with a raised red
rim, spiralling from the lens round its right into the lower body; two orange ribs on the red tail
cowl converging on the exhaust; a muzzle and an exhaust sunk as dimples into the nose and
tail; small dim running lamps (ramp 120, not white: the sprite has no lights there) in the seam
on each flank. Lofted along a smooth outline (centripetal
Catmull-Rom through the outline stations and the well's boundary; the ribs pchip-interpolated), smooth shaded
with crisp edges kept at the seam, grooves, bezel and vane. One mesh covers all frames: the lens
and its hot core change palette index per frame (palette_material frames=). AO/roughness bake by
the script itself (D50, D65; maps kept in scratch), outline shell (D51). Follow-up (D162 review
"fix 7"): lens moved down to cover rows 5-7, core dome to (6.7, 6.0), the white pal 127 lights
replaced by dim lamps, triangles trimmed (coarser loft, hidden faces culled). Re-review: the broad
swirl well and the cowl's orange ribs restored; lens/core one ramp step cooler (lens 124/125/126
over 113/132/151, near its cells' medians 123/125/126).

Run: tools/build-models.sh assets/blender/sidekicks/tropical-cherry-companion.py
Scratch measuring: blender -b --python <this> -- --renders <dir> (also exports the model)
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

MODEL = "sidekicks/tropical-cherry-companion"
NAME = "sidekick-tropical-cherry-companion"
TAG = "tropical-cherry-companion"
ROOT = WT
FRAMES = [113, 132, 151]
P = 1 / 12  # one sprite pixel
AXIS = 7.0  # centreline: sprite column edge 7
SHARP = math.radians(38)
UPPER_SEGS, BELLY_SEGS = 14, 6
SECTIONS = 20
HERE = Path("/Users/dlomibao/projects/tyrian-scratch/followups-1116/tropical-cherry-companion/final")  # bake maps


def X(col):
    return (col - 6) * P


def Y(row):
    return (7 - row) * P


# Hull outline (row edge, half width px): on the inner edge of the sprite's ink ring (D74), fitted
# so the top view covers exactly the inner mask on the sprite grid (outline_fit.py: grid IoU 1.0).
OUTLINE = [(0.45, 0.0), (0.56, 0.8), (0.8, 1.4), (1.2, 1.95), (1.7, 2.42), (2.3, 2.95), (3.0, 3.5),
           (3.6, 3.88), (4.3, 4.07), (5.5, 4.16), (7.0, 4.16), (8.1, 4.06), (8.7, 3.82), (9.2, 3.45),
           (9.9, 3.08), (10.5, 2.78), (11.0, 2.42), (11.5, 1.95), (11.9, 1.4), (12.25, 0.75), (12.45, 0.0)]
WMAX = 4.16
TOP = 1.0  # upper shell height / half width
BOTTOM = 0.8  # lower hull depth / half width
ROUND = 2.2  # superellipse exponent of the upper shell section
SEAM_Z = 0.3
SEAM_H = 0.55
SEAM_D = 0.28
GROOVES = [(2.95, 0.09, 0.12), (9.95, 0.09, 0.12)]  # nose cap / aft cowl panel lines


def arc(n, a0, a1):
    return [a0 + (a1 - a0) * i / n for i in range(n + 1)]


def _smooth_outline(per=24):
    pts = [OUTLINE[0]] + OUTLINE + [OUTLINE[-1]]
    pts[0] = (2 * OUTLINE[0][0] - OUTLINE[1][0], 2 * OUTLINE[0][1] - OUTLINE[1][1])
    pts[-1] = (2 * OUTLINE[-1][0] - OUTLINE[-2][0], 2 * OUTLINE[-1][1] - OUTLINE[-2][1])
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]

        def tj(a, b):
            return max(1e-6, math.dist(a, b) ** 0.5)
        t0 = 0.0
        t1 = t0 + tj(p0, p1)
        t2 = t1 + tj(p1, p2)
        t3 = t2 + tj(p2, p3)
        for k in range(per):
            t = t1 + (t2 - t1) * k / per

            def lerp(a, b, ta, tb):
                return tuple((tb - t) / (tb - ta) * u + (t - ta) / (tb - ta) * v for u, v in zip(a, b))
            a1, a2, a3 = lerp(p0, p1, t0, t1), lerp(p1, p2, t1, t2), lerp(p2, p3, t2, t3)
            b1, b2 = lerp(a1, a2, t0, t2), lerp(a2, a3, t1, t3)
            out.append(lerp(b1, b2, t1, t2))
    out.append(OUTLINE[-1])
    return out


DENSE = _smooth_outline()


def half_width(row):
    for (r0, w0), (r1, w1) in zip(DENSE, DENSE[1:]):
        if r0 <= row <= r1:
            return w0 + (w1 - w0) * (row - r0) / (r1 - r0)
    return 0.0


def height_width(row):
    """Half width that sets the hull's height at a row: a full egg over the whole length (a
    superellipse, slightly fuller toward the nose), never above the plan width, so the side view is
    an egg crowned in the middle, not a loaf with a flat top."""
    w = half_width(row)
    r0, r1 = OUTLINE[0][0], OUTLINE[-1][0]
    c = r0 + 0.47 * (r1 - r0)
    L = (c - r0) if row < c else (r1 - c)
    u = min(1.0, abs(row - c) / L)
    egg = WMAX * (1 - u ** 2.3) ** (1 / 2.3)
    return min(egg, w + 0.6) if w > 0 else 0.0


def hull_ring(w, hw, zone, inset=0.0):
    s = min(1.0, w / 3.0)
    d, h = SEAM_D * s, SEAM_H * s
    zu, zl = SEAM_Z, SEAM_Z - h
    pts = []
    for a in arc(UPPER_SEGS, 0.0, math.pi):
        c, sn = math.cos(a), math.sin(a)
        k = inset * min(1.0, 3.0 * sn)
        x = (w - k) * math.copysign(abs(c) ** (2 / ROUND), c)
        z = zu + TOP * (hw - k) * abs(sn) ** (2 / ROUND)
        pts.append((x, z, zone))
    pts[-1] = (-w, zu, "seam")
    pts += [(-(w - d), zu, "seam"), (-(w - d), zl, "seam")]
    wl = w - 0.12 * s
    pts.append((-wl, zl, "belly"))
    for a in arc(BELLY_SEGS, math.pi, 2 * math.pi)[1:-1]:
        pts.append((wl * math.cos(a), zl + BOTTOM * hw * math.sin(a), "belly"))
    pts += [(wl, zl, "seam"), (w - d, zl, "seam"), (w - d, zu, "seam")]
    return pts


def hull_sections():
    first, last = OUTLINE[1][0], OUTLINE[-2][0]
    line = [(r, w) for r, w in DENSE if first <= r <= last]
    line = [(first, half_width(first))] + line + [(last, half_width(last))]
    acc = [0.0]
    for a, b in zip(line, line[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    rows = []
    for i in range(SECTIONS + 1):
        target = acc[-1] * i / SECTIONS
        k = next(k for k in range(1, len(acc)) if acc[k] >= target - 1e-9)
        f = (target - acc[k - 1]) / max(1e-9, acc[k] - acc[k - 1])
        rows.append(line[k - 1][0] + (line[k][0] - line[k - 1][0]) * f)
    rows = [r for r in rows if all(abs(r - g) > gw + 0.18 for g, gw, _ in GROOVES)]
    secs = [(r, None) for r in rows]
    for g, gw, inset in GROOVES:
        secs += [(g - gw, None), (g + gw, None), (g - gw + 1e-4, inset), (g + gw - 1e-4, inset)]
    secs.sort(key=lambda t: t[0])
    out = []
    for r, inset in secs:
        if inset:
            zone = "groove"
        else:
            zone = "nose" if r < GROOVES[0][0] else "cowl" if r >= GROOVES[1][0] else "shell"
        out.append((r, half_width(r), height_width(r), zone, inset or 0.0))
    for i in range(len(out) - 1):
        if out[i + 1][3] == "groove":
            out[i] = out[i][:3] + ("groove", out[i][4])
    return out


def build_hull(bm, M):
    secs = hull_sections()
    rings, keys = [], []
    for row, w, hw, zone, inset in secs:
        pts = hull_ring(w, hw, zone, inset)
        rings.append([bm.verts.new((X(AXIS) + x * P, Y(row), z * P)) for x, z, _ in pts])
        keys.append([k for _, _, k in pts])
    n = len(rings[0])
    for (r0, r1), k in zip(zip(rings, rings[1:]), keys):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = M[k[i]]
    for ring, side in ((rings[0], 1), (rings[-1], -1)):
        y = ring[0].co.y - side * 0.3 * P
        zc = sum(v.co.z for v in ring) / n
        tip = bm.verts.new((X(AXIS), y, zc))
        for i in range(n):
            j = (i + 1) % n
            face = (ring[j], ring[i], tip) if side == 1 else (ring[i], ring[j], tip)
            bm.faces.new(face).material_index = M["dimple"]
    return [sum(v.co.z for v in rings[0]) / n, sum(v.co.z for v in rings[-1]) / n]


def shell_z(col, row):
    w = half_width(row)
    if w <= 0:
        return SEAM_Z
    u = min(1.0, abs(col - AXIS) / w)
    return SEAM_Z + TOP * height_width(row) * (1 - u ** ROUND) ** (1 / ROUND)


def disc_loft(bm, centre, rings, sides, mats, axis="z"):
    cx, cy, cz = centre
    verts = []
    for off, r in rings:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            u, v = r * math.cos(a) * P, r * math.sin(a) * P
            if axis == "z":
                ring.append(bm.verts.new((cx + u, cy + v, cz + off * P)))
            else:
                ring.append(bm.verts.new((cx + u, cy + off * P, cz + v)))
        verts.append(ring)
    for i, (r0, r1) in enumerate(zip(verts, verts[1:])):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mats[i]
    return verts


def dome(bm, centre, radius, height, sides, mat, segs=4, sy=1.0):
    cx, cy, cz = centre
    verts = []
    for i in range(segs):
        t = i / segs * (math.pi / 2)
        off, r = height * math.sin(t), radius * math.cos(t)
        verts.append([bm.verts.new((cx + r * math.cos(2 * math.pi * (k + 0.5) / sides) * P,
                                    cy + sy * r * math.sin(2 * math.pi * (k + 0.5) / sides) * P, cz + off * P))
                      for k in range(sides)])
    top = bm.verts.new((cx, cy, cz + height * P))
    for r0, r1 in zip(verts, verts[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((verts[-1][k], verts[-1][j], top)).material_index = mat
    bm.faces.new(list(reversed(verts[0]))).material_index = mat


def bezel(bm, centre, base, r_in, r_out, mat, sides=20, sy=1.0):
    """Thin dark ring round the lens (an oval sy times as long as wide), a hair over the shell,
    rising a little at its lower right."""
    col, row = centre
    cx, cy = X(col), Y(row)
    rings = [[], [], [], []]
    for k in range(sides):
        a = 2 * math.pi * k / sides
        c, s = math.cos(a), math.sin(a)
        lr = max(0.0, (c - s) / math.sqrt(2))
        lift = 0.3 + 0.2 * lr ** 1.5  # clear of the swirl well's floor
        h_out = shell_z(col + r_out * c, row - sy * r_out * s) + lift
        h_in = shell_z(col + r_in * c, row - sy * r_in * s) + lift
        top = max(h_out, h_in)
        for ring, r, z in zip(rings, (r_out, r_out, r_in, r_in), (base - 1.0, top - 0.08, top, base - 0.3)):
            ring.append(bm.verts.new((cx + r * c * P, cy + sy * r * s * P, z * P)))
    for v, k in zip(rings[1], range(sides)):
        a = 2 * math.pi * k / sides
        v.co.x -= 0.12 * math.cos(a) * P
        v.co.y -= sy * 0.12 * math.sin(a) * P
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat


# The swirl well: a broad recessed pocket over the sprite's dark mass (the "9" curling from
# above-right of the lens round its lower right into the dark lower body, rows 4-10). Its smooth
# boundary (sprite col, row), clockwise from the lens top; it passes through the lens, whose bezel
# covers that part. Keeps the gold flank cells (col 10, (9,4), the (9,9) glint, (4,7), (4,9), (5,6))
# outside and every dark cell ((7..8,4), (8..9,5..8), (5,7), (4..8,8), (5..8,9)) inside.
WELL = [(7.0, 5.0), (6.9, 4.05), (7.8, 3.8), (8.6, 3.92), (9.05, 4.45), (9.85, 5.35), (10.05, 6.4),
        (10.0, 7.7), (9.8, 8.6), (9.2, 9.15), (8.9, 9.9), (7.8, 10.15), (6.8, 10.15), (5.9, 10.05),
        (4.9, 9.35), (4.05, 8.35), (4.9, 7.55), (5.7, 6.95), (6.3, 6.3)]
WELL_FLOOR = 0.13  # px over the shell (clear of it: no z-fight)
RIM_W, RIM_LIFT = 0.27, 0.32  # rim half width, height over the shell (px)
# Orange ribs on the tail cowl (sprite (4,9) 122, (5,10) 121, (6,11) 121 and (8,10) 124, (7,11) 123):
# two strakes converging on the exhaust, a V.
RIBS = [[(4.55, 9.2, 0.26), (5.0, 9.8, 0.32), (5.55, 10.45, 0.34), (6.05, 11.05, 0.32), (6.45, 11.6, 0.24)],
        [(8.6, 10.12, 0.26), (8.3, 10.5, 0.32), (7.95, 10.95, 0.32), (7.55, 11.6, 0.24)]]
RIB_LIFT = 0.2


def closed_curve(pts, per=8):
    """Closed centripetal Catmull-Rom through pts."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]

        def tj(a, b):
            return max(1e-6, math.dist(a, b) ** 0.5)
        t0, t1 = 0.0, tj(p0, p1)
        t2 = t1 + tj(p1, p2)
        t3 = t2 + tj(p2, p3)
        for k in range(per):
            t = t1 + (t2 - t1) * k / per

            def lerp(a, b, ta, tb):
                return tuple((tb - t) / (tb - ta) * u + (t - ta) / (tb - ta) * v for u, v in zip(a, b))
            a1, a2, a3 = lerp(p0, p1, t0, t1), lerp(p1, p2, t1, t2), lerp(p2, p3, t2, t3)
            b1, b2 = lerp(a1, a2, t0, t2), lerp(a2, a3, t1, t3)
            out.append(lerp(b1, b2, t1, t2))
    return out


def inside(poly, c, r):
    hit = False
    for (c0, r0), (c1, r1) in zip(poly, poly[1:] + poly[:1]):
        if (r0 > r) != (r1 > r) and c < c0 + (r - r0) * (c1 - c0) / (r1 - r0):
            hit = not hit
    return hit


def in_lens(c, r, k):
    return ((c - LENS_C[0]) / k) ** 2 + ((r - LENS_C[1]) / (k * LENS_SY)) ** 2 < 1.0


def strip(bm, samples, lift, top_mat, wall_mat, sink=0.4, ch=0.12):
    """A raised chamfered strip along samples [(col, row, half width)]: its top follows the shell's
    curve `lift` px over it, its walls sink `sink` px into the shell; ends capped."""
    n = len(samples) - 1
    rings = []
    for i, (c, r, w) in enumerate(samples):
        a = samples[max(0, i - 1)]
        b = samples[min(n, i + 1)]
        dc, dr = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dc, dr) or 1.0
        nc, nr = -dr / L, dc / L
        ring = []
        for side, inset, dz in ((-1, 0.0, -sink), (-1, 0.0, -ch), (-1, ch, 0.0),
                                (1, ch, 0.0), (1, 0.0, -ch), (1, 0.0, -sink)):
            ww = max(0.05, w - inset)
            pc, pr = c + side * ww * nc, r + side * ww * nr
            ring.append(bm.verts.new((X(pc), Y(pr), (shell_z(pc, pr) + lift + dz) * P)))
        rings.append(ring)
    mats = [wall_mat, wall_mat, top_mat, wall_mat, wall_mat]
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(5):
            bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k])).material_index = mats[k]
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring).material_index = wall_mat


def well_rim(bm, top_mat, wall_mat):
    """The well's rim: a raised lip just inside its boundary, from where the boundary leaves the lens
    bezel round to where it meets it again (ends tapered under the bezel)."""
    curve = closed_curve(WELL, per=6)
    keep = [not in_lens(c, r, 1.2) for c, r in curve]
    i0 = next(i for i in range(len(curve)) if keep[i] and not keep[i - 1])
    run = []
    for k in range(len(curve)):
        i = (i0 + k) % len(curve)
        if not keep[i]:
            break
        run.append(curve[i])
    run = [curve[i0 - 1]] + run + [curve[(i0 + len(run)) % len(curve)]]
    samples = []
    for i, (c, r) in enumerate(run):
        a, b = run[max(0, i - 1)], run[min(len(run) - 1, i + 1)]
        dc, dr = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dc, dr) or 1.0
        nc, nr = -dr / L, dc / L
        if not inside(curve, c + 0.2 * nc, r + 0.2 * nr):
            nc, nr = -nc, -nr
        samples.append((c + 0.13 * nc, r + 0.13 * nr, RIM_W))
    strip(bm, samples, RIM_LIFT, top_mat, wall_mat, sink=0.45)


def well_floor(bm, mat, step=0.25):
    """The well's floor: a sheet following the shell WELL_FLOOR px over it, inside the boundary and
    outside the lens bezel (its jagged edge sits under the rim and the bezel). Faces point up."""
    curve = closed_curve(WELL, per=6)
    cs, rs = [c for c, _ in curve], [r for _, r in curve]
    c0, r0 = math.floor(min(cs) / step) * step, math.floor(min(rs) / step) * step
    nc, nr = int((max(cs) - c0) / step) + 2, int((max(rs) - r0) / step) + 2
    verts = {}

    def v(i, j):
        if (i, j) not in verts:
            c, r = c0 + i * step, r0 + j * step
            verts[i, j] = bm.verts.new((X(c), Y(r), (shell_z(c, r) + WELL_FLOOR) * P))
        return verts[i, j]
    for j in range(nr):
        for i in range(nc):
            c, r = c0 + (i + 0.5) * step, r0 + (j + 0.5) * step
            if inside(curve, c, r) and not in_lens(c, r, 1.12):
                # (col, row) -> (x, -y): this order is counter-clockwise seen from above
                bm.faces.new((v(i, j), v(i, j + 1), v(i + 1, j + 1), v(i + 1, j))).material_index = mat


def prism(bm, profile, rows, mat):
    rings = []
    for k in (0, 1):
        rings.append([bm.verts.new((X(AXIS) + x * P, Y(rows[k]), z * P)) for x, z in profile])
    n = len(profile)
    bm.faces.new(rings[0]).material_index = mat
    bm.faces.new(list(reversed(rings[1]))).material_index = mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[0][j], rings[0][i], rings[1][i], rings[1][j])).material_index = mat


def crisp(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
            e.smooth = False


LENS_C = (7.0, 6.45)  # sprite cells (7,5) (6,6) (7,6) (6,7) (7,7) flash
LENS_SY = 1.35  # an oval lens: 2.1 px wide, 2.8 px long (rows 5.0-7.9), like the flashing cells
CORE_C = (6.7, 6.0)  # the hot core, up-left where the lens is brightest


def build(sprite):
    coll = common.reset_collection(TAG)

    def pal(i, tag=TAG, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    # Satin orange paint over metal (not gold): low metallic, mid roughness.
    mats = [
        pal(123, metallic=0.25, roughness=0.5),                       # 0 shell
        pal(118, f"{TAG}-cowl", metallic=0.3, roughness=0.48),         # 1 aft cowl (sprite tail median 118)
        pal(114, metallic=0.4, roughness=0.55),                        # 2 seam
        pal(118, metallic=0.35, roughness=0.5),                        # 3 lower hull
        pal(116, metallic=0.55, roughness=0.35),                       # 4 bezel, dimples
        pal(124, f"{TAG}-lens", emission_strength=0.6, frames={132: 125, 151: 126}),  # 5 lens (~cell medians)
        pal(120, f"{TAG}-lamp", metallic=0.0, roughness=0.3, emission_strength=0.25),  # 6 dim seam lamps
        pal(125, f"{TAG}-core", emission_strength=1.2, frames={132: 126, 151: 127}),  # 7 hot core
        pal(118, f"{TAG}-vane", metallic=0.3, roughness=0.45),         # 8 swirl-well rim top (band 118)
        pal(115, metallic=0.4, roughness=0.5),                         # 9 grooves, rim walls
        pal(116, f"{TAG}-well", metallic=0.35, roughness=0.55),        # 10 swirl-well floor (dark mass 114-117)
        pal(122, f"{TAG}-rib", metallic=0.3, roughness=0.45),          # 11 orange cowl ribs (121-124)
    ]
    M = {"shell": 0, "cowl": 1, "nose": 0, "seam": 2, "groove": 9, "belly": 3, "dimple": 4}
    TRIM, LENS, LAMP, CORE, VANE, DARK, WELLM, RIB = 4, 5, 6, 7, 8, 9, 10, 11

    bm = bmesh.new()
    build_hull(bm, M)

    lx, ly = LENS_C
    base = shell_z(lx, ly)
    bezel(bm, (lx, ly), base, 1.05, 1.3, TRIM, sy=LENS_SY)
    dome(bm, (X(lx), Y(ly), (base + 0.02) * P), 1.05, 0.45, 16, LENS, segs=4, sy=LENS_SY)
    # the hot core behind the glass, up-left of centre where the sprite's lens is brightest
    cc, cr = CORE_C
    dome(bm, (X(cc), Y(cr), (base + 0.12) * P), 0.4, 0.38, 10, CORE, segs=3)

    well_rim(bm, VANE, DARK)
    for rib in RIBS:
        ts = list(range(len(rib)))
        fc, fr, fw = (T.pchip(ts, [p[k] for p in rib]) for k in range(3))
        n = 10
        strip(bm, [(fc(t), fr(t), fw(t)) for t in ((len(rib) - 1) * i / n for i in range(n + 1))],
              RIB_LIFT, RIB, RIB, sink=0.35, ch=0.1)

    # running lamps in the seam on each flank (rows 6.6-7.4)
    for side in (1, -1):
        w = half_width(7.0)
        x0, x1 = w - SEAM_D - 0.05, w - 0.08
        zl, zu = SEAM_Z - SEAM_H + 0.12, SEAM_Z - 0.12
        lp = [(x0, zl), (x1, zl), (x1, zu), (x0, zu)]
        if side < 0:
            lp = [(-x, z) for x, z in reversed(lp)]
        prism(bm, lp, (6.6, 7.4), LAMP)

    crisp(bm)
    well_floor(bm, WELLM)  # after the normals pass: an open sheet, wound to face up
    body = common.mesh_object(TAG, bm, mats, coll, smooth=True)
    T.cull_hidden(body)
    return coll, body, mats


def bake(obj, out_dir):
    """AO + edge lift colour multiplier and metallic-roughness maps (usp_talon.bake_maps), on the
    painted parts only: the lens, core and lamps stay flat glowing colour."""
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()
    T.TINT, T.TEXTURED = (1.0, 0.98, 0.96), (0, 1, 2, 3, 4, 8, 9, 10, 11)
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- measuring and rendering (scratch only) ------------------------------------------------------

def frame_recolour(mats, frame):
    """Set materials to their colours on `frame` (tyrian_frame_rgb); returns a restore list."""
    saved = []
    for m in mats:
        rgb = m.get("tyrian_frame_rgb", {}).get(str(frame))
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        saved.append((m, tuple(bsdf.inputs["Base Color"].default_value), tuple(bsdf.inputs["Emission Color"].default_value)))
        if rgb is not None:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1)
            if bsdf.inputs["Emission Strength"].default_value > 0:
                bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
            m.diffuse_color = (*rgb, 1)
    return saved


def restore(saved):
    for m, bc, ec in saved:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = bc
        bsdf.inputs["Emission Color"].default_value = ec
        m.diffuse_color = bc


def cam(scene, name, loc, look, ortho=None, lens=50):
    c = bpy.data.objects.get(name)
    if c is None:
        c = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        c.data.type, c.data.ortho_scale = "ORTHO", ortho
    else:
        c.data.type, c.data.lens = "PERSP", lens
    c.data.clip_end = 100
    return c


def top_mask(body, out_png):
    """Unlit top-view silhouette at k=10 px per sprite px over the 12x14 block (alpha)."""
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not body
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.show_cavity = False
    scene.display.shading.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 120, 140
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.0
    c = cam(scene, "cam_mask", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)


def region_colours(body, sprite):
    """Raycast every sprite pixel centre from above: the palette index the model shows there per
    frame, and per-region medians (trimmed: the darkest and brightest 20% are lighting)."""
    scene = bpy.context.scene
    hid = [o for o in scene.objects if o.type == "MESH" and o is not body]
    for o in hid:
        o.hide_viewport = True
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    grid = [[None] * 12 for _ in range(14)]
    for y in range(14):
        for x in range(12):
            org = Vector((X(x + 0.5), Y(y + 0.5), 3.0))
            hit, loc, nor, idx, ob, _ = scene.ray_cast(dg, org, Vector((0, 0, -1)))
            if hit and ob.name == body.name:
                m = ob.material_slots[ob.data.polygons[idx].material_index].material
                grid[y][x] = m
    for o in hid:
        o.hide_viewport = False
    regions = {
        "shell": [(x, y) for y in range(1, 9) for x in range(12)
                  if not (5 <= x <= 7 and 4 <= y <= 7) and not (x >= 7 and 4 <= y <= 8) and not (y == 8)],
        "lens": [(7, 5), (6, 6), (7, 6), (6, 7), (7, 7)],
        "swirl": [(7, 4), (8, 4), (8, 5), (9, 5), (8, 6), (9, 6), (8, 7), (9, 7), (5, 7), (4, 8), (5, 8), (6, 8),
                  (7, 8), (8, 8), (9, 8), (5, 9), (6, 9), (7, 9), (8, 9)],
        "tail": [(x, y) for y in (10, 11) for x in range(12)],
    }

    def trimmed_median(v):
        v = sorted(v)
        if len(v) >= 5:
            k = len(v) // 5
            v = v[k:len(v) - k]
        return v[len(v) // 2] if v else None
    out = {}
    for f in FRAMES:
        px = next(fr for fr in sprite["frames"] if fr["index"] == f)["pixels"]

        def model_idx(m):
            if m is None:
                return None
            mp = m.get("tyrian_frame_pal", {})
            return int(mp[str(f)]) if str(f) in mp else int(m.name.split("_")[1])
        reg = {}
        for rn, cells in regions.items():
            sv = [px[y][x] for x, y in cells if px[y][x] >= 0]
            mv = [model_idx(grid[y][x]) for x, y in cells if grid[y][x] is not None]
            reg[rn] = {"sprite": trimmed_median(sv), "model": trimmed_median(mv)}
        out[f] = reg
        out[f"grid_{f}"] = [" ".join("%3s" % (model_idx(grid[y][x]) if grid[y][x] else ".") for x in range(12)) for y in range(14)]
    return out


def setup_eevee(scene, res):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.filter_size = 1.5
    scene.view_settings.view_transform = "Standard"
    w = scene.world or bpy.data.worlds.new("w")
    scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.06, 0.09, 1)
    bg.inputs["Strength"].default_value = 1.0
    sun = bpy.data.objects.get("rsun")
    if sun is None:
        ld = bpy.data.lights.new("rsun", "SUN")
        ld.energy = 3.5
        ld.angle = math.radians(4)
        sun = bpy.data.objects.new("rsun", ld)
        scene.collection.objects.link(sun)
        fl = bpy.data.lights.new("rfill", "SUN")
        fl.energy = 0.9
        fo = bpy.data.objects.new("rfill", fl)
        scene.collection.objects.link(fo)
        fo.rotation_euler = Vector((0.6, 0.5, -0.3)).to_track_quat("Z", "Y").to_euler()
    sun.rotation_euler = Vector((-0.5, 0.6, 0.9)).to_track_quat("Z", "Y").to_euler()  # light from upper left


def render_views(objs, mats, out_dir):
    scene = bpy.context.scene
    show = set(o.name for o in objs if not o.get("tyrian_outline"))
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in show
    zc = 0.25 * P
    views = {
        "top": ((0, 0, 4), (0, 0, 0), 15 / 12, (360, 420)),
        "game": ((0, -2.2 * 0.55, 2.2 * 0.85), (0, 0, zc), None, (400, 400)),
        "side": ((3, 0, zc), (0, 0, zc), 1.2, (420, 300)),
        "front": ((0, 3, zc), (0, 0, zc), 1.0, (340, 300)),
        "rear": ((0, -3, zc), (0, 0, zc), 1.0, (340, 300)),
        "q34": ((1.3, 1.1, 1.3), (0, 0, zc), None, (400, 380)),
        "under": ((1.0, -1.1, -1.4), (0, 0, zc), None, (300, 260)),
    }
    for f in FRAMES:
        saved = frame_recolour(mats, f)
        for v, (loc, look, ortho, res) in views.items():
            if v in ("under", "side", "front", "rear", "q34") and f != FRAMES[0]:
                continue
            setup_eevee(scene, res)
            c = cam(scene, "cam_" + v, loc, look, ortho, lens=60)
            if v == "top":
                c.rotation_euler = (0, 0, 0)
            scene.camera = c
            scene.render.filepath = str(out_dir / f"{f}_{v}.png")
            bpy.ops.render.render(write_still=True)
        restore(saved)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll, body, mats = build(sprite)
    fmt = "AUTO"
    if "--no-bake" not in args:
        HERE.mkdir(parents=True, exist_ok=True)
        bake(body, HERE / "bake")
        fmt = "WEBP"
    bpy.context.view_layer.update()
    shell = common.outline_shell(body, coll, faces=600)
    objs = [body, shell]
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"], image_format=fmt)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    report = {"triangles": tris, "body_tris": sum(len(p.vertices) - 2 for p in body.data.polygons)}
    if "--renders" in args:
        out = Path(args[args.index("--renders") + 1]).resolve()
        out.mkdir(parents=True, exist_ok=True)
        top_mask(body, out / "mask_top.png")
        report["iou"] = {}
        for f in FRAMES:
            r = subprocess.run(["python3", str(WT / "tools" / "sprite_mask.py"), NAME, "--frame", str(f),
                                "--measure", str(out / "mask_top.png"), "--json"],
                               capture_output=True, text=True, cwd=str(WT))
            try:
                d = json.loads(r.stdout)
                d = d[0] if isinstance(d, list) else d
                report["iou"][f] = {k: v for k, v in d.get("measure", d).items() if k.startswith("iou") or k.startswith("edge")}
            except Exception:
                report["iou"][f] = r.stdout[-400:] + r.stderr[-400:]
        report["colours"] = region_colours(body, sprite)
        render_views(objs, mats, out)
        (out / "report.json").write_text(json.dumps(report, indent=1))
    print("REPORT", json.dumps(report)[:3000])


if __name__ == "__main__":
    main()
