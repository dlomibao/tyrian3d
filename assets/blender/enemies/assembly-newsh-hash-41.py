"""Spinning four-claw grabber (newsh#.shp, assembly of 4 pieces: newsh-hash-1, -3, -39, -41), design A.

What it is: a flying spinning grabber, 48 x 56 px (4 x 4.7 units): a square bronze hub with a
polished dome, and four forged steel claw arms pivoted on pins at the hub's corners. Each arm is a
stem out of the hub corner, a knuckle and two hooked prongs (a thick one and a thin finger) raked
to the clockwise side. The sprite's nine frames are the machine turning in 22.5 degree steps
(frames 0-3), two darker repeats of frame 2 (4 = frame 2 one palette step darker, 5 = a fatter,
counter-clockwise smeared drawing two steps darker), then the arms shorter and darker as it sinks
away (6, 7, 8).

Plan (the user's rule 1: the sprite's top-down outline, D74 inner edge): every shape's plan is the
sprite's own inner mask (thin parts' free border pixels at half weight), traced as one smooth
closed contour (bilinear field, light Gaussian, marching squares, resampled). The solid under it:
a vertical edge band, a radiused (quarter-round) top edge rolling onto a flat face, and a raised
rib wherever the part is wide enough (stem, knuckle, main prong, hub plate): forged bar stock with
a machined rib, faired (smooth profiles of the exact distance to the contour, no creases to
crinkle). Underside: a plain rounded closed bottom (no detail).
Hub: the plate is the sprite's brown square; on it a turned collar and a satin brown dome (the amber
spot up-left of the hub's centre is the dome's sheen, art rule 2: it stays up-left in every frame
while the hub turns), and four pivot pins at the square's corners where the arms leave it (frame
0's bright corner dots).

Colour: the sprite's median palette index per region (darkest ink and brightest sheen left out):
arms grey 8/7/7/8 on frames 0-3, 6 on frame 4 (frame-tagged palette, D17), 5/4/4/3 on 5-8; hub
brown 23 (frames 0, 1, 3) or 22. Satin metal (metallic 0.7, roughness 0.38); the dome the hub's
brown, satin (roughness 0.32). The top's normals are the faired surface's own (top_normals): a
continuous sheen along each claw's rounded edge, no dot per contour vertex.

Game contract kept: the seven shapes (<piece>, -f2, -f3, -f4, -f5, -f6, -f7) and their frames, the
four pieces cut with common.split_assembly at the current layout, pal_<index> materials, the -f3
grey darkening a step on frame 4. New in -f3: frame 5 gets its own drawing (the smear is 0.67 IoU
from frame 2): two frame-tagged variants per piece (.a frames 2/4, .b frame 5), each with its own
outline shell (frame_part, as newshm-123).

Outline shell (D51/D90): common.outline_shell from a sealed copy of each whole shape, held inside
the model, then sliced open per piece (no ink along the seams).

Output: public/models/enemies/<piece><suffix>.glb and src/render/spriteModels/<piece><suffix>.json for the
four pieces x seven shapes (-f3 carries both drawings and their shells). With --out file.glb also one
review glb with every shape in assembly position (shape k moved +5k units in X).

    blender -b --factory-startup -P assembly-newsh-hash-41.py -- [--out file.glb]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

HERE = Path(__file__).resolve().parent
WT = next(p for p in HERE.parents if (p / "package.json").exists())  # repo root
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh-hash-41"
OUT = HERE / "assembly-newsh-hash-41_review.glb"
GRID = [("newsh-hash-1", 0, 0), ("newsh-hash-3", 24, 0), ("newsh-hash-39", 0, 28), ("newsh-hash-41", 24, 28)]
PIECES = [g[0] for g in GRID]
W, H = 48, 56
PX = 1 / 12
SPACING = 5.0  # shape k sits at X + SPACING * k in the glb

# key, export suffix, frame positions it covers (the first is the one it is traced from), arm angle
# (degrees anticlockwise from frame 2, for the hub's pins), hub (centre x, y in sprite px from the
# top-left, half size px), grey index, brown index, {frame position: grey index}
SHAPES = [
    ("f0", "", [0], 45.0, (24.5, 27.5, 4.5), 8, 23, None),
    ("f1", "-f2", [1], 22.5, (24.5, 27.5, 4.75), 7, 23, None),
    ("f2a", "-f3", [2, 4], 0.0, (24.5, 27.5, 4.75), 7, 22, {4: 6}),
    ("f2b", "-f3", [5], 0.0, (24.0, 28.0, 4.75), 5, 22, None),
    ("f3", "-f4", [3], -22.5, (24.5, 27.5, 4.75), 8, 23, None),
    ("f6", "-f5", [6], 0.0, (25.5, 27.5, 4.25), 4, 22, None),
    ("f7", "-f6", [7], 0.0, (25.5, 29.0, 4.0), 4, 22, None),
    ("f8", "-f7", [8], 0.0, (25.0, 28.0, 2.5), 3, 22, None),
]

# Bridge half-width (px) per shape: frame 8's stems are ink lines, kept thin.
BRIDGE_R = {"f8": 0.3}
# Field overrides per shape (sigma px, free weight): frame 8's claws are 1-2 px, so a lighter blur keeps their tips.
FIELD = {}
# Frame 8 is drawn in 1 px lines, many of them diagonal: its plan is a stroke field instead (every
# inner or free pixel a disc of this radius, joined to its 8-neighbours by capsules), which keeps a
# diagonal one-pixel line one pixel wide where a blurred field either drops it or fattens it.
STROKE = {"f8": 0.34}
# Carve radius (px) round a crook pixel (transparent, the mask on three sides: the hole in each of
# frame 8's claw hooks). The outline shell's voxel remesh narrows a hole by a fraction of a pixel,
# so the model's own hole is opened a little wider than the half-coverage mark.
CROOK_RC = 0.62
# Height scale per shape: the machine sinking away is drawn smaller and thinner (frames 6-8).
ZS = {"f6": 0.92, "f7": 0.85, "f8": 0.55}

# Section (units): the edge band, the radiused top edge, the rib, the bottom.
WALL_T = 0.075   # top of the vertical edge band
R1, E1 = 0.52, 0.045   # 45-degree chamfered top edge: width (px, a vertex ring), rise
RC, E3 = 2.6, 0.022    # a low crown over the flat top: width (px), rise (faired, no rib to ripple)
WALL_B, EB, RB = 0.065, 0.045, 1.0  # bottom band, rounded bottom: rise, width
RINGS = (0.26, 0.52, 0.8, 1.1)  # vertex rings this far inside the contour (px): a clean radius
SUB = 6          # field samples per sprite px
SIGMA = 0.32     # Gaussian (px)
FREE_W = 0.62    # thin parts' free border pixels' weight in the field
THRESH = 0.5
STEP = 0.42      # contour resample and interior grid spacing (px)


# --- the sprite ------------------------------------------------------------------------------------

def load_piece(name):
    return json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())


DATA = {n: load_piece(n) for n in PIECES}


def frame_idx(pos):
    idx = [[-1] * W for _ in range(H)]
    colors = {}
    for n, x0, y0 in GRID:
        d = DATA[n]
        colors.update({int(k): tuple(v) for k, v in d["colors"].items()})
        for r, row in enumerate(SM._rows(d["frames"][pos])):
            for c, v in enumerate(row):
                if v >= 0:
                    idx[y0 + r][x0 + c] = v
    return idx, colors


def merged_sprite():
    data = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


def is_hub(v):
    return 16 <= v <= 31 or 160 <= v <= 170 or 120 <= v <= 127


# --- the plan: field, contour ------------------------------------------------------------------------

def blur(a, sigma):
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, a)


def upsample(px):
    """Bilinear field at SUB samples per px; sample (i, j) sits at px ((j + 0.5) / SUB, (i + 0.5) / SUB)
    with a border of 2 px (zeros)."""
    pad = np.pad(px, 2)
    hh, ww = pad.shape
    ys = (np.arange(hh * SUB) + 0.5) / SUB - 0.5
    xs = (np.arange(ww * SUB) + 0.5) / SUB - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, hh - 2)
    x0 = np.clip(np.floor(xs).astype(int), 0, ww - 2)
    fy = np.clip(ys - y0, 0, 1)[:, None]
    fx = np.clip(xs - x0, 0, 1)[None, :]
    a = pad[y0][:, x0]
    b = pad[y0][:, x0 + 1]
    c = pad[y0 + 1][:, x0]
    d = pad[y0 + 1][:, x0 + 1]
    return a * (1 - fy) * (1 - fx) + b * (1 - fy) * fx + c * fy * (1 - fx) + d * fy * fx


def to_px(i, j):
    """Sample grid coordinates (row i, col j, fractional) -> sprite px (x, y), top-left origin."""
    return (j + 0.5) / SUB - 2.0, (i + 0.5) / SUB - 2.0


def march(f, t):
    """Closed contours of f = t (marching squares, saddles by the cell mean) as lists of (x, y) px,
    the inside on the left walking each loop (counter-clockwise in screen space y-down: CW)."""
    hh, ww = f.shape
    segs = []
    for i in range(hh - 1):
        row0, row1 = f[i], f[i + 1]
        for j in range(ww - 1):
            a, b, c, d = row0[j], row0[j + 1], row1[j + 1], row1[j]  # tl tr br bl
            code = (a > t) * 1 + (b > t) * 2 + (c > t) * 4 + (d > t) * 8
            if code == 0 or code == 15:
                continue

            def e(k):
                if k == 0:
                    return (i, j + (t - a) / (b - a))
                if k == 1:
                    return (i + (t - b) / (c - b), j + 1)
                if k == 2:
                    return (i + 1, j + (t - d) / (c - d))
                return (i + (t - a) / (d - a), j)
            table = {1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 6: [(0, 2)], 7: [(3, 2)],
                     8: [(2, 3)], 9: [(2, 0)], 11: [(2, 1)], 12: [(1, 3)], 13: [(1, 0)], 14: [(0, 3)]}
            if code in (5, 10):
                mid = (a + b + c + d) / 4 > t
                if code == 5:
                    pairs = [(3, 2), (1, 0)] if mid else [(3, 0), (1, 2)]
                else:
                    pairs = [(0, 1), (2, 3)] if mid else [(0, 3), (2, 1)]
            else:
                pairs = table[code]
            for p, q in pairs:
                segs.append((e(p), e(q)))
    key = lambda p: (round(p[0], 5), round(p[1], 5))  # noqa: E731
    nxt = {}
    for p, q in segs:
        nxt[key(p)] = q
    loops, seen = [], set()
    for start in list(nxt):
        if start in seen:
            continue
        loop, k = [], start
        while k not in seen and k in nxt:
            seen.add(k)
            loop.append(k)
            k = key(nxt[k])
        if len(loop) > 3:
            loops.append([to_px(i, j) for i, j in loop])
    return loops


def area(loop):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
        a += x0 * y1 - x1 * y0
    return a / 2


def resample(loop, step, iters=2):
    pts = np.array(loop + loop[:1])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(6, int(round(s[-1] / step)))
    u = np.linspace(0, s[-1], n, endpoint=False)
    x = np.interp(u, s, pts[:, 0])
    y = np.interp(u, s, pts[:, 1])
    out = np.stack([x, y], 1)
    # one pass of neighbour smoothing (Laplacian, light) to drop the marching steps
    for _ in range(iters):
        out = 0.5 * out + 0.25 * (np.roll(out, 1, 0) + np.roll(out, -1, 0))
    return out


def plan(pos, bridge_r=0.62, sigma=SIGMA, free_w=FREE_W, gain=1.0, stroke=None):
    """Contours (list of (n, 2) arrays in px) and the label field for one frame position."""
    idx, colors = frame_idx(pos)
    m = SM.masks(idx, colors)
    inner = np.array(m["inner"], float)
    free = np.array(m["free"], float)
    px = np.clip(inner + free_w * free, 0, 1)
    if stroke:
        f = stroke_field(join_pixels(inner + free > 0, np.array(m["outer"], bool)), stroke)
    else:
        f = blur(upsample(px), sigma * SUB) * gain
    f = bridge(f, bridge_r)
    hub = np.array([[1.0 if v >= 0 and is_hub(v) else 0.0 for v in row] for row in idx])
    hubf = blur(upsample(hub), 0.5 * SUB)

    def keep(lp):
        a = abs(area(lp))
        if a > 0.8:
            return True
        cx, cy = np.mean(lp, 0)
        hv = hubf[int((cy + 2) * SUB), int((cx + 2) * SUB)]
        return a > 0.1 and hv < 0.3  # a small hole: the gap in a claw's crook, not the hub's ink dots
    step = STEP * (0.7 if stroke else 1.0)
    loops = [resample(lp, step, 3 if stroke else 2) for lp in march(f, THRESH) if keep(lp)]
    print(f"plan frame {pos}: {len(loops)} loop(s), areas {[round(abs(area([tuple(p) for p in lp])), 1) for lp in loops]}")
    return loops, hubf, m


def join_pixels(mask, outer):
    """`mask` plus the fewest drawn (`outer`) pixels that join all its 8-connected pieces to the
    biggest: a claw cut off by a line of ink is joined through that ink, not across the gap."""
    from collections import deque
    mask = mask.copy()
    nb = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    for _ in range(40):
        comps = sorted(components(mask), key=len, reverse=True)
        if len(comps) < 2:
            break
        main = {tuple(p) for p in comps[0]}
        start = [tuple(p) for p in comps[1]]
        prev = {p: None for p in start}
        q = deque(start)
        end = None
        while q and end is None:
            y, x = q.popleft()
            for dy, dx in nb:
                n = (y + dy, x + dx)
                if n in prev or not (0 <= n[0] < H and 0 <= n[1] < W) or not outer[n]:
                    continue
                prev[n] = (y, x)
                if n in main:
                    end = n
                    break
                q.append(n)
        if end is None:
            for p in start:
                mask[p] = False
            continue
        p = prev[end]
        while p is not None:
            mask[p] = True
            p = prev[p]
    return mask


def stroke_field(mask, r):
    """Field (as upsample's grid) that is 0.5 at distance r from the pixel graph of `mask`
    (pixel centres, joined to their 8-neighbours)."""
    hh, ww = (H + 4) * SUB, (W + 4) * SUB
    ii, jj = np.mgrid[0:hh, 0:ww]
    yy, xx = (ii + 0.5) / SUB - 2.0, (jj + 0.5) / SUB - 2.0
    best = np.full((hh, ww), 1e9)
    pts = [(y, x) for y, x in zip(*np.nonzero(mask))]
    S = set(pts)
    for y, x in pts:
        for dy, dx in ((0, 0), (0, 1), (1, -1), (1, 0), (1, 1)):
            if (dy, dx) != (0, 0) and (y + dy, x + dx) not in S:
                continue
            if dy and dx and ((y + dy, x) in S or (y, x + dx) in S):
                continue  # a diagonal step already joined through an orthogonal neighbour
            ax, ay = x + 0.5, y + 0.5
            bx, by = ax + dx, ay + dy
            lo_y, hi_y = int((min(ay, by) - r - 1 + 2) * SUB), int((max(ay, by) + r + 1 + 2) * SUB)
            lo_x, hi_x = int((min(ax, bx) - r - 1 + 2) * SUB), int((max(ax, bx) + r + 1 + 2) * SUB)
            sy, sx = slice(max(lo_y, 0), hi_y), slice(max(lo_x, 0), hi_x)
            px_, py_ = xx[sy, sx], yy[sy, sx]
            vx, vy = bx - ax, by - ay
            ll = vx * vx + vy * vy
            t = np.clip(((px_ - ax) * vx + (py_ - ay) * vy) / ll, 0, 1) if ll else 0
            d = np.hypot(px_ - (ax + t * vx), py_ - (ay + t * vy))
            best[sy, sx] = np.minimum(best[sy, sx], d)
    f = np.clip(0.5 + (r - best) * 2.0, 0, 1)
    # carve: every pixel outside the mask next to it keeps under half its area covered (the crook
    # between a claw's two 1 px prongs would fill otherwise)
    near = set()
    for y, x in pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (y + dy, x + dx) not in S:
                    near.add((y + dy, x + dx))
    for y, x in near:
        cy, cx = y + 0.5, x + 0.5
        sy = slice(max(int((cy - 1.2 + 2) * SUB), 0), int((cy + 1.2 + 2) * SUB))
        sx = slice(max(int((cx - 1.2 + 2) * SUB), 0), int((cx + 1.2 + 2) * SUB))
        d = np.hypot(xx[sy, sx] - cx, yy[sy, sx] - cy)
        walls = sum((y + a, x + b) in S for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        rc = CROOK_RC if walls >= 3 else 0.44  # a crook pixel (mask on three sides) carved deeper
        f[sy, sx] = np.minimum(f[sy, sx], np.clip(0.5 + (d - rc) * 2.0, 0, 1))
    return f


def components(mask, conn=8):
    """Connected components (8- or 4-connected) of a boolean array: list of (n, 2) arrays of (row, col)."""
    from collections import deque
    seen = np.zeros(mask.shape, bool)
    out = []
    hh, ww = mask.shape
    for i0, j0 in zip(*np.nonzero(mask)):
        if seen[i0, j0]:
            continue
        q, comp = deque([(i0, j0)]), []
        seen[i0, j0] = True
        while q:
            i, j = q.popleft()
            comp.append((i, j))
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if conn == 4 and di and dj:
                        continue
                    a, b = i + di, j + dj
                    if 0 <= a < hh and 0 <= b < ww and mask[a, b] and not seen[a, b]:
                        seen[a, b] = True
                        q.append((a, b))
        out.append(np.array(comp))
    return out


def bridge(f, radius=0.62):
    """Join every island of the plan to the main body (the hub's): a claw finger the sprite cuts
    off with a line of ink (frames 6-8 draw the thin fingers and frame 8 the stems in ink alone)
    is a part of the arm, not a loose piece. A capsule of `radius` px from the island's nearest
    point to the body's, painted into the field; repeated until one piece is left."""
    for _ in range(12):
        comps = sorted(components(f > THRESH, 4), key=len, reverse=True)
        comps = [c for c in comps if len(c) > 2 * SUB]
        if len(comps) < 2:
            return f
        main, isl = comps[0], comps[1]
        a = main[::2].astype(float)
        b = isl.astype(float)
        best = (1e9, None, None)
        for k in range(0, len(b), 256):
            d = ((b[k:k + 256, None, :] - a[None]) ** 2).sum(2)
            i, j = np.unravel_index(np.argmin(d), d.shape)
            if d[i, j] < best[0]:
                best = (d[i, j], b[k + i], a[j])
        _, p, q = best
        # push both ends a little into their parts, so the joint is solid
        v = q - p
        n = np.linalg.norm(v) + 1e-9
        p, q = p - v / n * SUB * 0.5, q + v / n * SUB * 0.5
        ii, jj = np.mgrid[0:f.shape[0], 0:f.shape[1]]
        t = np.clip(((ii - p[0]) * (q[0] - p[0]) + (jj - p[1]) * (q[1] - p[1])) / max(1e-9, ((q - p) ** 2).sum()), 0, 1)
        dist = np.hypot(ii - (p[0] + t * (q[0] - p[0])), jj - (p[1] + t * (q[1] - p[1]))) / SUB
        f = np.maximum(f, np.clip(1.0 - (dist - radius) * 2.0, 0, 1) * (THRESH + 0.3))
    return f


def seg_arrays(loops):
    a = np.concatenate([lp for lp in loops])
    b = np.concatenate([np.roll(lp, -1, 0) for lp in loops])
    return a, b


def dist_to(pts, a, b):
    """Distance (px) from each point to the nearest contour segment."""
    out = np.full(len(pts), 1e9)
    ab = b - a
    ll = np.maximum((ab ** 2).sum(1), 1e-12)
    for k in range(0, len(pts), 512):
        p = pts[k:k + 512, None, :]
        t = np.clip(((p - a[None]) * ab[None]).sum(2) / ll[None], 0, 1)
        q = a[None] + t[..., None] * ab[None]
        out[k:k + 512] = np.sqrt(((p - q) ** 2).sum(2)).min(1)
    return out


def inside(pts, a, b):
    """Even-odd point in polygon (all loops)."""
    res = np.zeros(len(pts), bool)
    for k in range(0, len(pts), 512):
        p = pts[k:k + 512, None, :]
        y0, y1 = a[None, :, 1], b[None, :, 1]
        cond = (y0 > p[..., 1]) != (y1 > p[..., 1])
        xint = a[None, :, 0] + (p[..., 1] - y0) / np.where(y1 - y0 == 0, 1e-12, y1 - y0) * (b[None, :, 0] - a[None, :, 0])
        res[k:k + 512] = ((cond & (p[..., 0] < xint)).sum(1) % 2) == 1
    return res


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def z_top(d):
    """The top's height over the distance (px) in from the contour: a rounded edge (a quarter sine,
    meeting the flat with zero slope: no crease for the sheen to break on) and a low crown."""
    return WALL_T + E1 * np.sin(0.5 * np.pi * np.clip(d / R1, 0, 1)) + E3 * smoothstep((d - R1) / (RC - R1))


def z_top_slope(d):
    """d z_top / d d (units per px)."""
    t = np.clip(d / R1, 0, 1)
    edge = np.where(d < R1, E1 * 0.5 * np.pi / R1 * np.cos(0.5 * np.pi * t), 0.0)
    u = np.clip((d - R1) / (RC - R1), 0, 1)
    crown = np.where((d > R1) & (d < RC), E3 * 6 * u * (1 - u) / (RC - R1), 0.0)
    return edge + crown


def nearest_on(pts, a, b):
    """Nearest contour point to each point (px): the point, its segment index and parameter."""
    out = np.zeros_like(pts)
    seg = np.zeros(len(pts), int)
    par = np.zeros(len(pts))
    ab = b - a
    ll = np.maximum((ab ** 2).sum(1), 1e-12)
    for k in range(0, len(pts), 512):
        p = pts[k:k + 512, None, :]
        t = np.clip(((p - a[None]) * ab[None]).sum(2) / ll[None], 0, 1)
        q = a[None] + t[..., None] * ab[None]
        i = np.sqrt(((p - q) ** 2).sum(2)).argmin(1)
        r = np.arange(len(i))
        out[k:k + 512] = q[r, i]
        seg[k:k + 512] = i
        par[k:k + 512] = t[r, i]
    return out, seg, par


def contour_normals(loops):
    """Inward unit normal at every contour point (central difference), as seg_arrays' order, and
    the index of each point's successor."""
    a, b = seg_arrays(loops)
    ns, nxt, base = [], [], 0
    for lp in loops:
        t = np.roll(lp, -1, 0) - np.roll(lp, 1, 0)
        n = np.stack([-t[:, 1], t[:, 0]], 1)
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-9)[:, None]
        if inside(lp + n * 0.1, a, b).mean() < 0.5:
            n = -n
        ns.append(n)
        nxt.append(base + (np.arange(len(lp)) + 1) % len(lp))
        base += len(lp)
    return np.concatenate(ns), np.concatenate(nxt)


def z_bot(d):
    t = np.clip(d / RB, 0, 1)
    return -(WALL_B + EB * np.sqrt(1 - (1 - t) ** 2))


def W2B(x, y):
    """Sprite px (top-left origin, y down) -> Blender units (assembly centre at the origin, y up)."""
    return (x - W / 2) * PX, (H / 2 - y) * PX


# --- the solid ---------------------------------------------------------------------------------------

def plate(bm, loops, hubf, GREY, BROWN):
    a, b = seg_arrays(loops)
    cont = [tuple(p) for p in a]
    edges, base = [], 0
    for lp in loops:
        n = len(lp)
        edges += [(base + i, base + (i + 1) % n) for i in range(n)]
        base += n
    xs = np.arange(-2, W + 2, STEP)
    ys = np.arange(-2, H + 2, STEP)
    gx, gy = np.meshgrid(xs, ys)
    grid = np.stack([gx.ravel(), gy.ravel()], 1)
    grid[:, 0] += (np.round(grid[:, 1] / STEP) % 2) * STEP / 2  # staggered rows: better triangles
    grid = grid[inside(grid, a, b)]
    grid = grid[dist_to(grid, a, b) > RINGS[-1] + 0.6 * STEP]
    # rings: each contour point moved in along its inward normal, kept where that really is the
    # ring's distance in (not across a thin part)
    ring = []
    for lp in loops:
        t = np.roll(lp, -1, 0) - np.roll(lp, 1, 0)
        n = np.stack([-t[:, 1], t[:, 0]], 1)
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-9)[:, None]
        if inside(lp + n * 0.1, a, b).mean() < 0.5:
            n = -n
        for dk in RINGS:
            q = lp + n * dk
            ok = inside(q, a, b) & (np.abs(dist_to(q, a, b) - dk) < 0.06)
            ring.append(q[ok])
    ring = np.concatenate(ring) if ring else np.zeros((0, 2))
    keep, cells = [], set()
    for q in ring:
        c = (round(q[0] / 0.16), round(q[1] / 0.16))
        if c in cells:
            continue
        cells.add(c)
        keep.append(q)
    verts2 = [Vector(p) for p in cont] + [Vector(tuple(p)) for p in keep] + [Vector(tuple(p)) for p in grid]
    vo, eo, fo, ov, oe, of = delaunay_2d_cdt(verts2, edges, [], 0, 1e-6)
    P = np.array([[v.x, v.y] for v in vo])
    d = dist_to(P, a, b)
    on = np.zeros(len(P), bool)
    out_of = {}
    for i, orig in enumerate(ov):
        for o in orig:
            if o < len(cont):
                on[i] = True
                out_of[o] = i
    d[on] = 0.0
    zt, zb = z_top(d), z_bot(d)
    top = [bm.verts.new((*W2B(x, y), z)) for (x, y), z in zip(P, zt)]
    bot = [bm.verts.new((*W2B(x, y), z)) for (x, y), z in zip(P, zb)]
    tris = [f for f in fo if len(f) == 3]
    top_layer = bm.faces.layers.int.get("plate_top") or bm.faces.layers.int.new("plate_top")
    cen = np.array([P[list(f)].mean(0) for f in tris])
    keep = inside(cen, a, b)

    def label(x, y):
        i = int(round((y + 2.0) * SUB - 0.5))
        j = int(round((x + 2.0) * SUB - 0.5))
        i = min(max(i, 0), hubf.shape[0] - 1)
        j = min(max(j, 0), hubf.shape[1] - 1)
        return BROWN if hubf[i, j] > 0.5 else GREY

    for f, k, c in zip(tris, keep, cen):
        if not k:
            continue
        # top (y down in px -> flipped in Blender: px-CW is Blender-CCW) and bottom
        try:
            ft = bm.faces.new([top[f[0]], top[f[1]], top[f[2]]])
            fb = bm.faces.new([bot[f[2]], bot[f[1]], bot[f[0]]])
        except ValueError:
            continue
        m = label(*c)
        ft.material_index = fb.material_index = m
        ft[top_layer] = 1
        ft.smooth = fb.smooth = True
    base = 0
    for lp in loops:
        n = len(lp)
        for i in range(n):
            p, q = out_of.get(base + i), out_of.get(base + (i + 1) % n)
            if p is None or q is None or p == q:
                continue
            try:
                fw = bm.faces.new([top[p], top[q], bot[q], bot[p]])
            except ValueError:
                continue
            e = next((e for e in fw.edges if top[p] in e.verts and top[q] in e.verts), None)
            other = [g for g in e.link_faces if g is not fw] if e else []
            fw.material_index = other[0].material_index if other else label(*((P[p] + P[q]) / 2))
            fw.smooth = True
        base += n
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if not v.link_faces], dist=0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    return float(zt.max())


def disc(bm, cx, cy, r, z0, z1, mat, sides=24, rtop=None, chamfer=0.0):
    """A turned disc / pin (radii px, centre px in sprite space) from z0 to z1, chamfered top."""
    X, Y = W2B(cx, cy)
    rt = r if rtop is None else rtop
    rings = [(r, z0), (r, z1 - chamfer), (rt - chamfer / PX * 0.9 if chamfer else rt, z1)]
    vs = []
    for rr, z in rings:
        vs.append([bm.verts.new((X + rr * PX * math.cos(2 * math.pi * k / sides),
                                 Y + rr * PX * math.sin(2 * math.pi * k / sides), z)) for k in range(sides)])
    faces = [bm.faces.new(list(reversed(vs[0])))]
    for r0, r1 in zip(vs, vs[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    faces.append(bm.faces.new(vs[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def dome(bm, cx, cy, r, z0, h, mat, seg=32, rings=10):
    X, Y = W2B(cx, cy)
    ring_verts = []
    for k in range(rings + 1):
        phi = (math.pi / 2) * k / rings
        rr = r * math.cos(phi) * PX
        z = z0 + h * math.sin(phi)
        if k == rings:
            ring_verts.append([bm.verts.new((X, Y, z))])
        else:
            ring_verts.append([bm.verts.new((X + rr * math.cos(2 * math.pi * s / seg), Y + rr * math.sin(2 * math.pi * s / seg), z))
                               for s in range(seg)])
    faces = [bm.faces.new(list(reversed(ring_verts[0])))]
    for r0, r1 in zip(ring_verts, ring_verts[1:]):
        for s in range(seg):
            t = (s + 1) % seg
            if len(r1) == 1:
                faces.append(bm.faces.new((r0[s], r0[t], r1[0])))
            else:
                faces.append(bm.faces.new((r0[s], r0[t], r1[t], r1[s])))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def hub(bm, angle, hx, hy, s, ztop, BROWN, DOME):
    k = s / 4.75
    # turned collar round the dome, sunk into the plate
    disc(bm, hx, hy, 3.55 * k, ztop - 0.03, ztop + 0.022 * k, BROWN, sides=32, chamfer=0.008)
    dome(bm, hx, hy, 3.05 * k, ztop + 0.012, 0.13 * k, DOME)
    # pivot pins at the square's corners, where the arms leave it
    for q in range(4):
        a = math.radians(angle + 90 * q)
        # sprite y is down, Blender's up: an anticlockwise angle in Blender is -angle in the sprite
        px, py = hx + 0.93 * s * math.cos(a + math.pi / 2), hy - 0.93 * s * math.sin(a + math.pi / 2)
        disc(bm, px, py, 1.05 * k, ztop - 0.04, ztop + 0.02 * k, BROWN, sides=14, chamfer=0.01)


def build(key, pos, angle, hubp, grey, brown, frames, sprite, coll):
    tag = f"nsh41A{key}"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    if frames:
        fm = {}
        for n in PIECES:
            fr = DATA[n]["frames"]
            for p, gi in frames.items():
                fm[fr[p]["index"]] = gi
        gmat = common.palette_material(sprite, grey, tag + "arm", metallic=0.7, roughness=0.38, frames=fm)
    else:
        gmat = pal(grey, metallic=0.7, roughness=0.38)
    bmat = pal(brown, metallic=0.65, roughness=0.36)
    # the dome: the hub's own brown, satin (a little smoother than the plate); the sprite's amber
    # spot up-left of centre is its sheen (art rule 2), not a gold paint
    dmat = common.palette_material(sprite, brown, tag + "dome", metallic=0.75, roughness=0.32)
    mats = [gmat, bmat, dmat]
    GREY, BROWN, DOME = 0, 1, 2
    loops, hubf, m = plan(pos, BRIDGE_R.get(key, 0.62), *FIELD.get(key, (SIGMA, FREE_W, 1.0)), STROKE.get(key))
    bm = bmesh.new()
    zmax = plate(bm, loops, hubf, GREY, BROWN)
    hx, hy, s = hubp
    ztop = WALL_T + E1 + E3
    hub(bm, angle, hx, hy, s, ztop, BROWN, DOME)
    for v in bm.verts:
        v.co.z *= ZS.get(key, 1.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}_{key}")
    bm.to_mesh(me)
    bm.free()
    for mm in mats:
        me.materials.append(mm)
    obj = bpy.data.objects.new(f"{NAME}_{key}", me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(32))
    obj["plan"] = key
    PLANS[key] = (*seg_arrays(loops), *contour_normals(loops))
    return obj


PLANS = {}


def top_normals(obj, key, x0, y0):
    """Smooth the top's shading (D65 sheen, not studs): every corner of a plate top face gets the
    exact normal of the faired surface z = z_top(d) at that point (d: distance in from the plan's
    contour), so a sheen runs as one continuous streak along a claw's rounded edge instead of
    breaking into a dot per contour vertex. Edges between top faces are smooth; the top's edge
    onto the vertical band stays sharp. (x0, y0): the piece's offset in the assembly (units)."""
    me = obj.data
    att = me.attributes.get("plate_top")
    if att is None:
        return
    flag = np.zeros(len(me.polygons), np.int32)
    att.data.foreach_get("value", flag)
    zs = ZS.get(key, 1.0)
    a, b, cn, cnext = PLANS[key]
    # the 32-degree rule elsewhere (hub parts, band); smooth between two top faces; sharp where the
    # top meets any other face (the band, a hub part, a cut fill)
    owners = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            owners.setdefault(ek, []).append(bool(flag[p.index]))
    ekey = {e.key: e for e in me.edges}
    me.set_sharp_from_angle(angle=math.radians(32))
    for ek, fl in owners.items():
        e = ekey[ek]
        if all(fl) and len(fl) == 2:
            e.use_edge_sharp = False
        elif any(fl):
            e.use_edge_sharp = True
    me.update()
    corner = [Vector(n.vector) for n in me.corner_normals]
    pts, idxs = [], []
    for p in me.polygons:
        if not flag[p.index]:
            continue
        for li in p.loop_indices:
            q = me.vertices[me.loops[li].vertex_index].co
            pts.append(((q.x + x0) / PX + W / 2, H / 2 - (q.y + y0) / PX))
            idxs.append(li)
    if idxs:
        P = np.array(pts)
        Q, i, t = nearest_on(P, a, b)
        d = np.linalg.norm(P - Q, axis=1)
        # the inward direction: the contour's own normal at the nearest point, interpolated between
        # its vertices (smooth along the contour, not one flat facet per segment)
        g = (1 - t)[:, None] * cn[i] + t[:, None] * cn[cnext[i]]
        g /= np.maximum(np.linalg.norm(g, axis=1), 1e-9)[:, None]  # px, y down
        # the rounded edge's slope only: the crown (0.02 units over 2 px) is shaded flat, so its
        # faint ridge along a part's middle (where the nearest edge flips) makes no jagged crease
        s = z_top_slope(np.minimum(d, R1)) * zs / PX  # units of rise per unit run
        nx, ny = -s * g[:, 0], s * g[:, 1]  # Blender y = -px y
        nz = np.ones(len(d))
        ln = np.sqrt(nx * nx + ny * ny + nz * nz)
        for li, x, y, z in zip(idxs, nx / ln, ny / ln, nz / ln):
            corner[li] = Vector((x, y, z))
    me.normals_split_custom_set([tuple(n) for n in corner])
    me.attributes.remove(me.attributes["plate_top"])


def split_open(obj, layout, coll, suffix):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}{suffix}_outline")
        bm.to_mesh(me)
        bm.free()
        for mm in obj.data.materials:
            me.materials.append(mm)
        s = bpy.data.objects.new(f"{name}{suffix}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else OUT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()
    layout = [(n, x0 + 12 - 24, y0 + 14 - 28) for n, x0, y0 in GRID]
    objs, info, per_file = [], {}, {}
    for k, (key, suffix, poss, angle, hubp, grey, brown, frames) in enumerate(SHAPES):
        whole = build(key, poss[0], angle, hubp, grey, brown, frames, sprite, coll)
        closed = whole.copy()
        closed.data = whole.data.copy()
        coll.objects.link(closed)
        bpy.context.view_layer.update()
        shell = common.outline_shell(closed, coll, voxel=0.010, faces=9000, smooth=4, inside=0.003)
        bpy.data.objects.remove(closed)
        bpy.context.view_layer.update()
        variant = {"f2a": ".a", "f2b": ".b"}.get(key, "")
        pieces = common.split_assembly(whole, [(f"{n}{suffix}{variant}", cx, cy) for n, cx, cy in layout])
        shells = split_open(shell, layout, coll, f"{suffix}{variant}")
        bpy.data.objects.remove(shell)
        bpy.context.view_layer.update()
        info[key] = {"whole_tris": sum(len(p.vertices) - 2 for p in whole.data.polygons), "pieces": {}}
        for n, cx, cy in layout:
            pc = pieces[f"{n}{suffix}{variant}"]
            sh = shells[n]
            if variant:  # -f3's two drawings: each piece's own sprite indices
                fr = DATA[n]["frames"]
                common.frame_part(pc, [fr[p]["index"] for p in poss])
                common.frame_part(sh, [fr[p]["index"] for p in poss])
            for o in (pc, sh):
                o.location = (cx / 12 + SPACING * k, -cy / 12, 0)
                objs.append(o)
            per_file.setdefault(f"{n}{suffix}", []).extend([pc, sh])
            top_normals(pc, key, cx / 12, -cy / 12)
            info[key]["pieces"][pc.name] = sum(len(p.vertices) - 2 for p in pc.data.polygons)
        whole.location = (SPACING * k, 0, 0)
        whole["shape_key"] = key
    bpy.context.view_layer.update()
    if "--out" in argv:  # review export: every shape in assembly position
        common.export_glb(objs, out)
        wholes = [o for o in coll.objects if "shape_key" in o]
        common.export_glb(wholes, out.with_name(out.stem + "_wholes.glb"))
    for fname, group in per_file.items():  # the game's per-piece files, each piece at its own origin
        piece = next(n for n in PIECES if fname == n or fname.startswith(n + "-f"))
        positions = []
        for key, suffix, poss, *_ in SHAPES:
            if piece + suffix == fname:
                positions += poss
        data = common.load_sprite(WT, piece)
        want = {data["frames"][p]["index"] for p in positions}
        sprites = [dict(s, frames=[f for f in s["frames"] if f in want]) for s in data["sprites"]]
        sprites = [s for s in sprites if s["frames"]]
        for o in group:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        common.export_sprite_model(WT, group, f"enemies/{fname}", sprites)
    if "--info" in argv:
        (Path(argv[argv.index("--info") + 1])).write_text(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
