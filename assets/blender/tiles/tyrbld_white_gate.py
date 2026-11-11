"""The white gates set into the edges of TYRIAN's rock islands (map 1-9, layer 2, Background3Over
pass: everything <= L2_OVER_MAX 0.38), hard-surface (D65, D141). Each is three courses of white
marble ashlar (pillowed blocks with a drafted margin round the top), held by two riveted brass
L-straps, each strap two plates split by a stepped Greek-key groove with cross joints where the art
shows them. Under the lowest course the art paints a dark band (palette 1-3): here a sunken trench
(a gate pit) in front of the gate, the lowest course standing down into it as the gate's face; the
west gate has a dark doorway in that face, at the darkest pixels of the band. The rock round the
gate is the islands' own per-tile rock (Structure.rock, plain, cut where the trench is). Texture:
AO/roughness bake only ("bake": "model").

  white-gate-w: 185 186 / 195 196 (island's west edge; straps on the gate's right)
  white-gate-e: 187 188 / 197 198 (island's east edge; straps on the gate's left, split courses)

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_white_gate.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_white_gate.py -- [--no-bake] [--preview <dir>]
"""


import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402


# --- Layout (pattern px at 1x, the 48x56 2x2 pattern), read off the tiles' pixels ------------------
# blocks: marble tops (x0, y0, x1, y1); straps: each brass L as its two rectangles; key: the stepped
# groove splitting each L into an inner and an outer plate (polyline); joints: short cross grooves
# (px, py, "h"|"v": along which axis the plate runs there); trench: the box the dark band lies in;
# door: the doorway in the lowest course's face (x0, x1) or None.
GATES = {
    "white-gate-w": dict(
        blocks=[(11.7, 4.0, 29.55, 10.85), (11.7, 15.15, 29.3, 24.85), (11.7, 29.25, 29.55, 39.0)],
        straps=[[(29.7, 3.9, 33.95, 11.1), (10.9, 11.0, 33.95, 15.0)],
                [(11.3, 25.0, 33.95, 29.1), (29.7, 29.0, 33.95, 45.0)]],
        keys=[[(10.0, 13.6), (19.0, 13.6), (19.0, 12.4), (31.8, 12.4), (31.8, 2.0)],
              [(10.0, 27.4), (17.0, 27.4), (17.0, 26.2), (31.8, 26.2), (31.8, 47.0)]],
        joints=[(23.0, 14.3, "h"), (28.5, 11.7, "h"), (23.0, 28.2, "h")],
        trench=(10.5, 39.0, 36.0, 47.0),
        door=(12.7, 16.6),  # the band's darkest columns (index 1), a 1 px jamb left
    ),
    "white-gate-e": dict(
        blocks=[(18.15, 7.0, 29.55, 13.85), (29.75, 7.0, 35.0, 13.85),
                (14.0, 18.15, 31.5, 26.85), (31.7, 18.15, 35.0, 26.85),
                (18.15, 31.15, 28.9, 39.6), (29.1, 31.15, 35.0, 39.6)],
        straps=[[(14.0, 7.0, 18.0, 14.2), (14.0, 14.0, 35.0, 18.0)],
                [(14.0, 27.0, 35.0, 31.0), (14.0, 30.8, 18.0, 45.0)]],
        keys=[[(15.6, 5.0), (15.6, 16.6), (25.4, 16.6), (25.4, 15.4), (37.0, 15.4)],
              [(16.4, 47.0), (16.4, 28.4), (24.0, 28.4), (24.0, 29.6), (37.0, 29.6)]],
        joints=[(17.0, 10.5, "v"), (30.0, 16.0, "h"), (17.0, 38.0, "v")],
        trench=(13.0, 39.0, 37.0, 47.0),
        door=None,
    ),
}

# --- Heights (units; layer 2: z = 0 the islands' rock top; over: <= 0.38) ---------------------------
BLOCK_TOP = 0.345
BLOCK_FOOT = -0.04
STRAP_BASE = 0.125  # the L's base plate; the groove floor
STRAP_TOP = 0.165  # the two key plates
RIVET_H = 0.018
TRENCH_FLOOR = -0.17
DOOR_TOP = 0.19  # the doorway's lintel (under the block's top section)
DOOR_DEPTH = 2.6  # px into the lowest course
KEY_GAP = 0.7  # px, the Greek-key groove's width
JOINT_GAP = 0.4
S4 = 4  # raster scale for the strap plates' outlines

MARBLE = dict(roughness=0.38, metallic=0.0)
BRASS = dict(roughness=0.40, metallic=0.35)


def trimmed_index(s, region, lo=0.15, hi=0.10):
    """The region's palette index: median by brightness of its pixels, ignoring the darkest `lo`
    and brightest `hi` (lighting: outline ring, shading, sheen)."""
    vals = s.grid[region & (s.grid >= 0)]
    if not len(vals):
        return None
    lum = s.ts.lum
    vals = np.array(sorted(vals.tolist(), key=lambda v: lum[v]))
    n = len(vals)
    core = vals[int(n * lo):max(int(n * lo) + 1, int(n * (1 - hi)))]
    return int(core[len(core) // 2])


def box_mask(s, b, scale=1):
    x0, y0, x1, y1 = b
    yy, xx = np.mgrid[0:s.H * scale, 0:s.W * scale] + 0.5
    xx, yy = xx / scale, yy / scale
    return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)


def polyline_mask(s, pts, width, scale):
    """Pixels (at `scale`) within width/2 of the polyline."""
    yy, xx = np.mgrid[0:s.H * scale, 0:s.W * scale] + 0.5
    xx, yy = xx / scale, yy / scale
    out = np.zeros(xx.shape, bool)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / max(L2, 1e-9), 0, 1)
        d = np.hypot(xx - (ax + t * dx), yy - (ay + t * dy))
        out |= d <= width / 2
    return out


def polys_of(mask, scale, tol=0.12, min_area=0.6):
    """Outlines (pattern px) of the 4-connected parts of a mask at `scale`."""
    polys = []
    for ys, xs in lt.components(mask):
        part = np.zeros(mask.shape, bool)
        part[ys, xs] = True
        loop = [(x / scale, y / scale) for x, y in ls.trace(part)]
        poly = ls.simplify(loop, tol)
        if len(poly) >= 3 and abs(ls.area(poly)) >= min_area:
            polys.append(poly)
    return polys


def loft(s, poly_at, rings, z0, mat, side_mat=None, smooth=False):
    """A closed lofted prism: `rings` [(inset_px, z), ...] bottom edge to top, each ring the outline
    poly_at(inset) (same vertex count); bottom cap at z0 under ring 0's outline, top cap on the last.
    The hard-surface section: walls, chamfers, a pillowed or drafted top."""
    side_mat = mat if side_mat is None else side_mat
    bm = bmesh.new()
    loops = []
    base_poly = poly_at(rings[0][0])
    if ls.area(base_poly) < 0:
        flip = True
    else:
        flip = False

    def pts(inset):
        p = [(float(x), float(y)) for x, y in poly_at(inset)]
        return list(reversed(p)) if flip else p

    base = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in pts(rings[0][0])]
    loops.append(base)
    for inset, z in rings:
        loops.append([bm.verts.new((s.x(x), s.y(y), z)) for x, y in pts(inset)])
    n = len(base)
    for k, (a, b) in enumerate(zip(loops, loops[1:])):
        mi = side_mat if k == 0 else mat
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mi
    bm.faces.new(loops[-1]).material_index = mat
    bm.faces.new(list(reversed(base))).material_index = side_mat
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=smooth)


def marble_block(s, box, z0, mat, foot_mat=None, notch=None):
    """One ashlar block: square walls, a rounded (pillowed) top edge in four steps, a drafted margin
    0.8 px wide a hair below the face, the face itself. `notch` (x0, x1, depth, z_top): a doorway
    cut into the south face up to z_top (the block's lower part is built round it)."""
    x0, y0, x1, y1 = box
    t = BLOCK_TOP

    def outline(inset):
        return s.rounded_box(x0 + inset, y0 + inset, x1 - inset, y1 - inset,
                             corner_px=max(0.25, 0.9 - inset * 0.3), segments=3)

    rings = [(0.0, t - 0.075), (0.12, t - 0.040), (0.35, t - 0.020), (0.65, t - 0.010),
             (1.05, t - 0.009), (1.25, t - 0.002), (1.4, t)]
    low = z0
    if notch is not None:
        nx0, nx1, depth, ztop = notch
        # The lower part: the block's outline minus the doorway, up to ztop.
        poly = [(x0, y0), (x1, y0), (x1, y1), (nx1, y1), (nx1, y1 - depth), (nx0, y1 - depth), (nx0, y1), (x0, y1)]
        s.slab(poly, z0, ztop, foot_mat or mat, chamfer_px=0, drop=0)
        low = ztop
        # A clean recessed doorway: dark liners on its back wall (the full door width), both jambs
        # and its ceiling, so the opening reads as a dark hole cut square into the stone, the
        # lintel flush with the face.
        dark = s.m(1, roughness=0.95)
        yb = y1 - depth
        for poly in ([(nx0, yb), (nx1, yb), (nx1, yb + 0.25), (nx0, yb + 0.25)],
                     [(nx0, yb), (nx0 + 0.2, yb), (nx0 + 0.2, y1 - 0.02), (nx0, y1 - 0.02)],
                     [(nx1 - 0.2, yb), (nx1, yb), (nx1, y1 - 0.02), (nx1 - 0.2, y1 - 0.02)]):
            s.slab(poly, z0, ztop, dark, chamfer_px=0, drop=0)
        s.slab([(nx0, yb), (nx1, yb), (nx1, y1 - 0.02), (nx0, y1 - 0.02)], ztop - 0.02, ztop - 0.001, dark,
               chamfer_px=0, drop=0)
    elif foot_mat is not None and z0 < 0:
        # The part standing down into the trench: the gate's foundation course.
        s.slab(outline(0.0), z0, 0.0, foot_mat, chamfer_px=0, drop=0)
        low = 0.0
    loft(s, outline, rings, low, mat)


def strap_plates(s, d, li, mat, plate_mat):
    """One brass L: a base plate over its two rectangles (chamfered), then the two key plates on it,
    split by the stepped groove and cut by the cross joints; rivets at the plates' ends."""
    rects = d["straps"][li]
    L4 = np.zeros((s.H * S4, s.W * S4), bool)
    for r in rects:
        L4 |= box_mask(s, r, S4)
    for poly in polys_of(L4, S4, tol=0.05):
        s.slab(poly, BLOCK_FOOT if li == 0 else BLOCK_FOOT, STRAP_BASE, mat, chamfer_px=0.35, drop=0.02)
    inner = L4
    # Shrink the plates 0.3 px from the base's edge (a step, so the plate reads as a separate part).
    shrink = lb.erode(inner, int(round(0.3 * S4)))
    cut = polyline_mask(s, d["keys"][li], KEY_GAP, S4)
    for jx, jy, along in d["joints"]:
        if not L4[int(jy * S4), int(jx * S4)]:
            continue
        if along == "h":
            cut |= box_mask(s, (jx - JOINT_GAP / 2, jy - 3, jx + JOINT_GAP / 2, jy + 3), S4) & L4
        else:
            cut |= box_mask(s, (jx - 3, jy - JOINT_GAP / 2, jx + 3, jy + JOINT_GAP / 2), S4) & L4
    plates = shrink & ~cut
    polys = polys_of(plates, S4, tol=0.1, min_area=1.0)
    rivets = []
    for poly in polys:
        s.slab(poly, STRAP_BASE - 0.01, STRAP_TOP, plate_mat, chamfer_px=0.3, drop=0.015)
        # Rivets near each convex end of the plate: its outline's corners, pulled 0.8 px inward.
        p = np.array(poly)
        inn = np.array(ls.inset([tuple(v) for v in poly], 0.85))
        for k in range(len(p)):
            a, b, c = p[k - 1], p[k], p[(k + 1) % len(p)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            sgn = 1 if ls.area([tuple(v) for v in poly]) > 0 else -1
            if cross * sgn > 0:  # convex corner
                q = inn[k]
                if all(math.hypot(q[0] - rx, q[1] - ry) > 2.4 for rx, ry in rivets):
                    rivets.append((float(q[0]), float(q[1])))
    for rx, ry in rivets:
        s.dome(rx, ry, 0.42, 0.42, STRAP_TOP - 0.004, RIVET_H, plate_mat, sides=10, rings=2)
    return plates


def build(name, bake=True, preview=None):
    lb.clear_scene()
    d = GATES[name]
    s = tb.Structure(name)
    g = s.grid

    # --- the art's masks ---------------------------------------------------------------------------
    brass_px = s.ramp_mask(1)
    bbox_all = np.zeros((s.H, s.W), bool)
    for rects in d["straps"]:
        for r in rects:
            bbox_all |= box_mask(s, r)
    brass_px &= lb.dilate(bbox_all, 1)
    blocks_px = np.zeros_like(brass_px)
    for b in d["blocks"]:
        blocks_px |= box_mask(s, b)
    lum = s.lum()
    trench_px = box_mask(s, d["trench"]) & (g >= 0) & (g <= 3) & ~bbox_all
    trench_px = lb.drop_small(lb.open_(lb.close(trench_px, 1), 1), 20)
    # The band's lighter pixels next to the face (the face's lit top) and the 1-px gaps against
    # the block and the strap belong to the pit too: close it and fill its bays.
    trench_px = lb.close(trench_px, 3) & box_mask(s, d["trench"]) & ~blocks_px & ~bbox_all & (g >= 0)
    low_row = int(round(max(b[3] for b in d["blocks"])))
    for x in range(s.W):  # each column of the pit runs from the lowest course down to its dark bottom
        ys = np.nonzero(trench_px[:, x])[0]
        if len(ys):
            top = low_row if ys.min() <= low_row + 2 else ys.min()
            trench_px[top:ys.max() + 1, x] = True
    for y in range(s.H):  # and no rock pillars left standing in it
        xs = np.nonzero(trench_px[y])[0]
        if len(xs):
            trench_px[y, xs.min():xs.max() + 1] = True
    trench_px &= ~blocks_px & ~bbox_all
    mask = lb.close(brass_px | blocks_px | bbox_all | trench_px, 1)

    # --- colours: each region's own index (trimmed median) -----------------------------------------
    i_brass = trimmed_index(s, brass_px)
    block_idx = [trimmed_index(s, box_mask(s, b) & ~brass_px) for b in d["blocks"]]
    i_floor = trimmed_index(s, trench_px, lo=0.0, hi=0.2)
    low_y1 = max(b[3] for b in d["blocks"])
    face_band = box_mask(s, (min(b[0] for b in d["blocks"]), low_y1, max(b[2] for b in d["blocks"]), low_y1 + 1.5))
    i_face = trimmed_index(s, face_band, lo=0.0, hi=0.0)
    print(f"{name}: brass {i_brass}, blocks {block_idx}, trench floor {i_floor}, face band {i_face}")
    # The plates' faces: the strap's inside pixels (its 1-px edge is the outline ring and bevel).
    i_plate = trimmed_index(s, lb.erode(brass_px, 1))
    print(f"{name}: plate faces {i_plate}")
    brass = s.m(i_brass, **BRASS)
    plate = s.m(i_plate, **BRASS)
    foot = s.m(i_face, roughness=0.8)
    floor = s.m(i_floor, roughness=0.9)

    # --- parts -------------------------------------------------------------------------------------
    for li in range(len(d["straps"])):
        strap_plates(s, d, li, brass, plate)
    # The strap that runs down beside the trench stands on the trench floor.
    for rects in d["straps"]:
        for r in rects:
            if r[3] > low_y1:
                s.slab([(r[0] + 0.05, max(r[1], low_y1 - 0.5)), (r[2] - 0.05, max(r[1], low_y1 - 0.5)),
                        (r[2] - 0.05, r[3] - 0.05), (r[0] + 0.05, r[3] - 0.05)], TRENCH_FLOOR - 0.02, BLOCK_FOOT + 0.001,
                       foot, chamfer_px=0, drop=0)
    for b, idx in zip(d["blocks"], block_idx):
        mat = s.m(idx, **MARBLE)
        lowest = abs(b[3] - low_y1) < 0.01
        notch = None
        if lowest and d["door"] is not None and d["door"][0] < b[2] and d["door"][1] > b[0]:
            notch = (max(d["door"][0], b[0] + 0.3), min(d["door"][1], b[2] - 0.3), DOOR_DEPTH, DOOR_TOP)
        marble_block(s, b, TRENCH_FLOOR - 0.02 if lowest else BLOCK_FOOT, mat, foot if lowest else None, notch)
    # --- the island's rock round it (plain), cut over the trench, and the trench floor under EVERY cut
    # pixel (pixel-exact outline: a simplified one leaves see-through slivers at the corners) ------
    cut = trench_px | (lb.dilate(trench_px, 1) & (blocks_px | bbox_all))
    if d["door"] is not None:
        dx0, dx1 = d["door"]
        cut |= box_mask(s, (dx0, low_y1 - DOOR_DEPTH, dx1, low_y1 + 0.5))
    # The rock pulls back about half a pixel round the cut's corners, so the floor runs half a pixel
    # (4-connected, at 2x) under the rock all round: hidden in the rock, no see-through corner.
    c2 = np.kron(cut, np.ones((2, 2), bool))
    p2 = np.pad(c2, 1)
    fl2 = np.zeros_like(c2)
    for dy, dx in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            fl2 |= p2[1 + dy:1 + dy + c2.shape[0], 1 + dx:1 + dx + c2.shape[1]]
    for poly in polys_of(fl2, 2, tol=0.01, min_area=0.2):
        s.slab(poly, tb.L2_SLAB_BOTTOM, TRENCH_FLOOR, floor, chamfer_px=0, drop=0)
    s.rock(exclude=lb.erode(mask, 1) & ~cut, cut=cut)

    objects = s.objects()
    s.finish(objects, mask, bake=bake, preview=preview)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for gname in GATES:
    build(gname, bake="--no-bake" not in argv, preview=lt.preview_arg())
