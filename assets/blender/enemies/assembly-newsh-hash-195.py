"""Saw rotor (newsh#.shp, assembly of 4 pieces: newsh-hash-157, -159, -195, -197), DECISIONS.md D213.

What it is: the spinning steel saw of SAWBLADES (3.9) and IXMUCANE (3.4), 48 x 56 px: two
four-claw stars stacked 45 degrees apart round a square blue gem (each star is the four-claw
grabber of assembly-newsh-hash-41: a stem out of the hub, a thick and a thin straight prong), so
sixteen slim straight tines with ink between them. Each tine is drawn as a bright ground bevel
along its outer (cutting) edge, a dark body and a mid-grey back edge; the art is four exact
quarter-turn copies, so those tones turn with the blades: they are the blades' own bevels, not
light from the upper left.

Its five frames: 0 the rotor lit; 1 the same turned 22.5 degrees (the game alternates 0 and 1 every
tick: the spin); 2, 3, 4 are frame 0 two, four and six palette steps darker (it glides in dark,
frame 4, then lights up 3 -> 2 -> spin), and frame 3 is the whole drawing one pixel lower (a jolt
as it starts).

How it is built (the sprite is the ruler): every shape is traced from its own frame.
- Plan: the sprite's inner mask (tools/sprite_mask.py, D74), traced crisp: the pixel steps' middles
  fitted with straight lines that meet in sharp corners (`vectorise`), never blurred, so the tines
  stay straight bars with chisel tips. That plan is a thin dark plate (the sprite's ink, pal_1).
- Steel: the plate's metal pixels (not ink) stand on it as flat bars with a chamfered edge, so every
  ink line the sprite draws between two tines (a tine's outline over the star under it) is a real
  slot down to the dark plate, and the game's outline (the shell) is the ring round the whole.
- Bevels: the steel's top is cut along the sprite's own tone steps (five grey classes, small specks
  dropped), each band in its class's palette index: the bright cutting bevel, the dark body and the
  back edge of every tine, as long bands. The game's sun is nearly overhead and a tine is 3 px
  wide, so no section could shade itself into those bands (D176): they are cut and painted.
- Hub: the blue gem, a low glossy cabochon on the square the sprite draws, with its glint up-left.
Frame 0 (and 2, 3, 4) is drawn on the pixel grid's own angles and is traced as drawn. Frame 1 is the
same drawing at 22.5 degrees, irregular stairs and dithered tones, and is traced looser (TRACE).

Frames: <piece> covers frames 0 and 2 (the greys two steps darker on frame 2, frame-tagged palette,
D17); -f2 is frame 1, traced from its own drawing; -f3 covers frames 3 and 4 with two frame-tagged
copies (common.frame_part, as assembly-newsh-hash-41's -f3): .a frame 4 (six steps darker), .b
frame 3 (four steps darker, built one pixel lower: the jolt), each with its own outline shell.

Game contract kept: the three shapes and their frames, the four pieces cut with
common.split_assembly at the current layout, pal_<index> materials, the same glb and JSON paths.

    blender -b --factory-startup -P assembly-newsh-hash-195.py [-- --whole DIR]

--whole DIR also writes each shape whole (DIR/<shape>.glb, with its shell) for review.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "package.json").exists())
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh-hash-195"
# Pieces and where they sit in the 48 x 56 px assembly (left, top), from sprite.json `assemblyLayout`.
GRID = [("newsh-hash-157", 0, 0), ("newsh-hash-159", 24, 0), ("newsh-hash-195", 0, 28), ("newsh-hash-197", 24, 28)]
PIECES = [g[0] for g in GRID]
W, H = 48, 56
PX = 1 / 12

# key, export suffix, variant, the frame position it is traced from, the frame positions it shows
# on, palette steps darker than frame 0 per position, (dx, dy) px the drawing sits off its trace.
SHAPES = [
    ("f0", "", "", 0, [0, 2], {0: 0, 2: 2}, (0, 0)),
    ("f1", "-f2", "", 1, [1], {1: 0}, (0, 0)),
    ("f4", "-f3", ".a", 0, [4], {4: 6}, (0, 0)),
    ("f3", "-f3", ".b", 0, [3], {3: 4}, (0, 1)),
]
# The trace per frame position: (Douglas-Peucker tolerance px on the middles of the pixel steps,
# ink as strokes, px the tones are averaged along the blades). Frame 0 is drawn on the pixel grid's
# own angles (0, 45, 90 degrees): 0.26 keeps 1:1 and 2:1 pixel stairs straight and every real jog a
# corner, and its ink lines and tone bands are traced as drawn. Frame 1 is the same drawing at 22.5
# degrees, all irregular stairs and dithered tones: a looser fit draws its edges straight, its ink
# (one-pixel diagonal chains, which a pixel trace turns into beads) is stroked instead (a
# constant-width slot along the chain of ink pixel centres), and its tones are first averaged along
# each blade (2 px either way along the nearest long edge) and traced as a field between the pixel
# centres, so they come out as bands along the blades, not blotches or pixel stairs.
TRACE = {0: (0.26, False, 0), 1: (0.5, True, 2)}
STROKE_R = 0.58      # half width (px) of a stroked ink line
TONE_EPS = 0.3       # the tone bands' trace is never looser than this: a looser fit thins 1 px bands
SS = 4               # samples per px where the steel is cut by the strokes and the tone field traced

# Heights (units; 1 px = 1/12): the dark plate, the steel's edge and top, the gem.
Z_PLATE = 0.030      # top of the dark plate: the floor of the ink slots
Z_EDGE = 0.126       # top of the steel's vertical edge
Z_TOP = 0.138        # the steel's flat top
CHAMFER = 0.30       # chamfer width (px) from the edge to the flat top
Z_SHELL = 0.070      # top of the plain prism the outline shell is made from: under the steel's
                     # top and chamfers, so no fold of the shell stands over them as an ink hairline
Z_GEM = 0.128        # the gem's rim
GEM_H, GEM_R = 0.085, 3.4   # the cabochon's rise and how far in (px) it keeps rising

CORNER = 0.8         # how far (px) a corner may sit from the end of a straight run

# Tone classes of the steel: palette index cuts, the index each class is painted per frame position
# it is traced from, its roughness. The classes' own mean indices are 3.7, 5.5, 7.3, 9.4, 11.1 (frame
# 0) and 3.9, 5.5, 7.4, 9.5, 11.9 (frame 1); the game's light draws a palette grey a little darker
# and its tone mapping holds the brightest back, so the classes are painted up to a step and a half
# above their means. Checked in game at 3840x2160, compare view, SAWBLADES t2667 / t2660 (luma of
# the steel's pixels, original | model): frame 0 mean 108 | 108-111, median 107 | 102, 90th
# percentile 164 | 160-168; frame 1 mean 102 | 107, median 93 | 97, 90th percentile 142 | 153 (its
# averaged bands are broader than the sprite's dithered ones, so they are painted lighter; with the
# dark class at 6 the claws read darker than the sprite: 30% of the steel under luma 80 against 16%).
CUTS = [4.5, 6.5, 8.5, 10.5]
PAINT = {0: [4, 6, 8, 10, 12], 1: [4, 7, 8, 11, 13]}
ROUGH = [0.46, 0.42, 0.36, 0.30, 0.24]
BASE = 2             # the class the steel is before the other classes' bands are cut into it
MIN_PX = 3           # a class's specks smaller than this (px) join their surroundings
METALLIC, SPEC = 0.6, 0.75


# --- the sprite ------------------------------------------------------------------------------------

DATA = {n: common.load_sprite(ROOT, n) for n in PIECES}


def frame_idx(pos):
    """The whole assembly at frame position `pos`: palette indices (-1 transparent), and the colours."""
    idx = np.full((H, W), -1, int)
    colors = {}
    for n, x0, y0 in GRID:
        d = DATA[n]
        colors.update({int(k): tuple(v) for k, v in d["colors"].items()})
        idx[y0:y0 + 28, x0:x0 + 24] = np.array(d["frames"][pos]["pixels"])
    return idx, colors


def merged_sprite():
    data = dict(DATA[PIECES[0]])
    data["colors"] = dict(data["colors"])
    for n in PIECES[1:]:
        data["colors"].update(DATA[n]["colors"])
    return data


def is_gem(v):
    return (v >= 152) | (v == 143)


def is_steel(v):
    return (v >= 3) & (v <= 13)


# --- crisp tracing of a pixel mask -------------------------------------------------------------------

def trace(mask):
    """Closed loops of pixel-corner points round `mask`, the foreground 8-connected and on the right
    walking each loop (clockwise on screen, y down; holes the other way)."""
    h, w = mask.shape
    m = np.pad(mask.astype(bool), 1)
    nxt = {}
    for y in range(h):
        for x in range(w):
            if not m[y + 1, x + 1]:
                continue
            if not m[y, x + 1]:
                nxt.setdefault((x, y), []).append((x + 1, y))
            if not m[y + 1, x + 2]:
                nxt.setdefault((x + 1, y), []).append((x + 1, y + 1))
            if not m[y + 2, x + 1]:
                nxt.setdefault((x + 1, y + 1), []).append((x, y + 1))
            if not m[y + 1, x]:
                nxt.setdefault((x, y + 1), []).append((x, y))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, p, prev = [], start, None
        while True:
            outs = nxt.get(p)
            if not outs:
                break
            if len(outs) == 1 or prev is None:
                q = outs.pop(0)
            else:  # a pinch between two diagonal pixels: turn left, keeping both in one loop
                dx, dy = p[0] - prev[0], p[1] - prev[1]
                left = (p[0] + dy, p[1] - dx)
                q = left if left in outs else outs[0]
                outs.remove(q)
            if not outs:
                del nxt[p]
            loop.append(p)
            prev, p = p, q
            if p == start:
                break
        if len(loop) >= 4:
            loops.append(loop)
    return loops


def _dp(pts, eps):
    keep = [0, len(pts) - 1]
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p, d = pts[a], pts[b] - pts[a]
        n = math.hypot(*d)
        seg = pts[a + 1:b] - p
        dist = np.abs(seg[:, 0] * d[1] - seg[:, 1] * d[0]) / n if n > 1e-9 else np.hypot(seg[:, 0], seg[:, 1])
        i = int(dist.argmax())
        if dist[i] > eps:
            keep.append(a + 1 + i)
            stack += [(a, a + 1 + i), (a + 1 + i, b)]
    return sorted(keep)


def _fit(pts):
    c = pts.mean(0)
    if len(pts) < 2:
        return c, np.array([1.0, 0.0])
    return c, np.linalg.svd(pts - c)[2][0]


def _meet(l0, l1):
    (p, d), (q, e) = l0, l1
    det = d[1] * e[0] - d[0] * e[1]
    if abs(det) < 1e-6:
        return None
    r = q - p
    return p + (r[1] * e[0] - r[0] * e[1]) / det * d


def polygon(loop, eps, corner=CORNER):
    """A corner loop as a crisp polygon, (n, 2): the middles of its unit edges split into straight
    runs (Douglas-Peucker, `eps`), each run's least-squares line, the vertices where neighbouring
    lines meet (or, when that is more than `corner` from the run's end, the end on each line: a
    short chamfer)."""
    c = np.array(loop, float)
    mid = (c + np.roll(c, -1, 0)) / 2
    n = len(mid)
    if n < 6:
        return mid
    s = int(((mid - mid.mean(0)) ** 2).sum(1).argmax())
    order = np.roll(np.arange(n), -s)
    pts = np.vstack([mid[order], mid[order[:1]]])
    keep = _dp(pts, eps)
    runs = [(keep[i], keep[i + 1]) for i in range(len(keep) - 1)]
    if len(runs) < 3:
        return pts[keep[:-1]]
    lines = [_fit(pts[a:b + 1]) for a, b in runs]
    out = []
    for i, (a, b) in enumerate(runs):
        j = (i + 1) % len(runs)
        v = _meet(lines[i], lines[j])
        end = pts[b]
        if v is not None and math.hypot(*(v - end)) <= corner:
            out.append(v)
        else:
            for p, d in (lines[i], lines[j]):
                out.append(p + ((end - p) @ d) * d)
    out = np.array(out)
    return out[np.hypot(*(out - np.roll(out, 1, 0)).T) > 0.05]


def area(pg):
    return 0.5 * float((pg[:, 0] * np.roll(pg[:, 1], -1) - np.roll(pg[:, 0], -1) * pg[:, 1]).sum())


def vectorise(mask, eps, ss=1, min_area=0.0):
    """The crisp polygons (px) of a mask sampled `ss` times per px; loops under min_area px^2 dropped."""
    out = []
    for lp in trace(np.asarray(mask, bool)):
        pg = polygon(lp, eps * ss, CORNER * ss) / ss
        if len(pg) >= 3 and abs(area(pg)) >= min_area:
            out.append(pg)
    return out


def stroked_steel(plan_loops, gem_loops, ink, ring):
    """The steel where the ink is stroked: the plan less the gem and less a line STROKE_R px either
    side of the chain of ink pixel centres (each joined to its 8-neighbours; a diagonal only where
    no straight step makes the same join), sampled SS times per px. Rows of bools. `ring`: the ink
    of the sprite's outline ring, which is the game's outline: a line runs on to it (the slot opens
    through the steel's edge) but not along it."""
    ys, xs = (np.arange(H * SS) + 0.5) / SS, (np.arange(W * SS) + 0.5) / SS
    gx, gy = np.meshgrid(xs, ys)
    pts = np.stack([gx.ravel(), gy.ravel()], 1)
    keep = inside(pts, *segs(plan_loops)) & ~inside(pts, *segs(gem_loops))
    S = {(y, x) for y, x in zip(*np.nonzero(ink))}
    a, b = [], []
    for y, x in S:
        if not ring[y, x]:
            a.append((x + 0.5, y + 0.5))
            b.append((x + 0.5, y + 0.5))
        for dy, dx in ((0, 1), (1, -1), (1, 0), (1, 1)):
            if (y + dy, x + dx) not in S or (dy and dx and ((y + dy, x) in S or (y, x + dx) in S)):
                continue
            if ring[y, x] and ring[y + dy, x + dx]:
                continue
            a.append((x + 0.5, y + 0.5))
            b.append((x + dx + 0.5, y + dy + 0.5))
    near = dist_to(pts[keep], np.array(a), np.array(b)) < STROKE_R
    keep[np.nonzero(keep)[0][near]] = False
    return keep.reshape(H * SS, W * SS)


# --- tone classes ------------------------------------------------------------------------------------

def label(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), int)
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not lab[y, x]:
                n += 1
                stack = [(y, x)]
                lab[y, x] = n
                while stack:
                    cy, cx = stack.pop()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            yy, xx = cy + dy, cx + dx
                            if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                                lab[yy, xx] = n
                                stack.append((yy, xx))
    return lab, n


def along_blades(idx, steel, loops, reach, min_len=2.5):
    """The steel pixels' palette indices averaged along the blades: each pixel with the steel pixels
    up to `reach` px either way along its nearest long (min_len px) edge of the steel's outline."""
    p0, p1 = segs(loops)
    ln = np.hypot(*(p1 - p0).T)
    p0, p1, ln = p0[ln >= min_len], p1[ln >= min_len], ln[ln >= min_len]
    out = idx.astype(float)
    for y, x in zip(*np.nonzero(steel)):
        p = np.array([x + 0.5, y + 0.5])
        t = np.clip(((p - p0) * (p1 - p0)).sum(1) / (ln * ln), 0, 1)
        k = int(np.hypot(*(p - (p0 + t[:, None] * (p1 - p0))).T).argmin())
        tv = (p1[k] - p0[k]) / ln[k]
        tot = wsum = 0.0
        for st in range(-reach, reach + 1):
            xx, yy = int(math.floor(p[0] + tv[0] * st)), int(math.floor(p[1] + tv[1] * st))
            if 0 <= xx < W and 0 <= yy < H and steel[yy, xx]:
                wt = reach + 1 - abs(st)
                tot += wt * idx[yy, xx]
                wsum += wt
        out[y, x] = tot / wsum
    return out


def despeckle(c, min_cells):
    """Class map `c` with every 8-connected piece of a class smaller than min_cells given the class
    most of its 4-neighbours have (the nearest class on a tie)."""
    h, w = c.shape
    for _ in range(2):
        for k in range(len(CUTS) + 1):
            lab, n = label(c == k)
            size = np.bincount(lab.ravel(), minlength=n + 1)
            for i in range(1, n + 1):
                if size[i] >= min_cells:
                    continue
                ys, xs = np.nonzero(lab == i)
                votes = {}
                for y, x in zip(ys, xs):
                    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and c[yy, xx] >= 0 and c[yy, xx] != k:
                            votes[c[yy, xx]] = votes.get(c[yy, xx], 0) + 1
                if votes:
                    c[ys, xs] = max(votes.items(), key=lambda kv: (kv[1], -abs(kv[0] - k)))[0]
    return c


def carry(v, empty, steps=4):
    """`v` carried `steps` px outward over the pixels where `empty`: each takes what most of its
    filled 4-neighbours have (ints) or their mean (floats)."""
    v, empty = v.copy(), empty.copy()
    ints = v.dtype.kind == "i"
    for _ in range(steps):
        nxt, filled = v.copy(), []
        for y, x in zip(*np.nonzero(empty)):
            near = [v[yy, xx] for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
                    if 0 <= yy < H and 0 <= xx < W and not empty[yy, xx]]
            if near:
                nxt[y, x] = max(set(near), key=lambda u: (near.count(u), -abs(u - BASE))) if ints else sum(near) / len(near)
                filled.append((y, x))
        v = nxt
        for y, x in filled:
            empty[y, x] = False
    return v


def tone_classes(idx, steel, smooth=None):
    """(class map, its samples per px): the class (0 darkest .. len(CUTS)) of the steel by its
    palette index, specks under MIN_PX px joined to their surroundings, carried outward over
    everything else (so a class's edge crosses the steel's edge squarely).
    As drawn: one sample per pixel. With `smooth` (the indices averaged along the blades): the
    averaged tones are a field, sampled SS times per px between the pixel centres, so the bands'
    edges run as straight lines instead of pixel stairs; it is cut where each class keeps the share
    of the steel it has as drawn (the averaging moves the bands' edges, not how much is bright)."""
    c = np.where(steel, np.digitize(idx, CUTS), -1)
    if smooth is None:
        return carry(despeckle(c, MIN_PX), c < 0), 1
    share = np.cumsum(np.bincount(c[steel], minlength=len(CUTS) + 1))[:-1] / steel.sum()
    cuts = np.quantile(smooth[steel], share)
    f = carry(np.where(steel, smooth, float(np.median(smooth[steel]))), ~steel)
    pos_y, pos_x = (np.arange(H * SS) + 0.5) / SS - 0.5, (np.arange(W * SS) + 0.5) / SS - 0.5
    y0, x0 = np.clip(np.floor(pos_y).astype(int), 0, H - 2), np.clip(np.floor(pos_x).astype(int), 0, W - 2)
    fy, fx = np.clip(pos_y - y0, 0, 1)[:, None], np.clip(pos_x - x0, 0, 1)[None, :]
    up = (f[y0][:, x0] * (1 - fy) * (1 - fx) + f[y0][:, x0 + 1] * (1 - fy) * fx
          + f[y0 + 1][:, x0] * fy * (1 - fx) + f[y0 + 1][:, x0 + 1] * fy * fx)
    # specks down to half MIN_PX stay: the field's smallest bright bands are the sprite's glints
    return despeckle(np.digitize(up, cuts), MIN_PX * SS * SS // 2), SS


# --- polygons: distance, inside ------------------------------------------------------------------------

def segs(loops):
    return np.concatenate(loops), np.concatenate([np.roll(lp, -1, 0) for lp in loops])


def dist_to(pts, a, b):
    out = np.full(len(pts), 1e9)
    ab = b - a
    ll = np.maximum((ab ** 2).sum(1), 1e-12)
    for k in range(0, len(pts), 512):
        p = pts[k:k + 512, None, :]
        t = np.clip(((p - a[None]) * ab[None]).sum(2) / ll[None], 0, 1)
        out[k:k + 512] = np.sqrt(((p - (a[None] + t[..., None] * ab[None])) ** 2).sum(2)).min(1)
    return out


def inside(pts, a, b):
    """Point in polygon over all loops, by winding number (the loops as `trace` walks them: holes
    the other way round), so where two fitted lobes of a loop overlap a hair the point is still in."""
    res = np.zeros(len(pts), bool)
    for k in range(0, len(pts), 512):
        p = pts[k:k + 512, None, :]
        y0, y1 = a[None, :, 1], b[None, :, 1]
        up = (y0 <= p[..., 1]) & (y1 > p[..., 1])
        down = (y0 > p[..., 1]) & (y1 <= p[..., 1])
        xint = a[None, :, 0] + (p[..., 1] - y0) / np.where(y1 - y0 == 0, 1e-12, y1 - y0) * (b[None, :, 0] - a[None, :, 0])
        right = p[..., 0] < xint
        res[k:k + 512] = ((up & right).sum(1) - (down & right).sum(1)) != 0
    return res


def rings(loops, depths):
    """Points `depths` px inside the loops' edges (the inside is on the right of every edge), kept
    where that really is their distance in: the rim of a chamfer, the rings of a dome."""
    a, b = segs(loops)
    out = []
    for lp in loops:
        d = np.roll(lp, -1, 0) - lp
        ln = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)
        nin = np.stack([-d[:, 1], d[:, 0]], 1) / ln[:, None]
        for i in range(len(lp)):
            j = (i + 1) % len(lp)
            ts = np.linspace(0, 1, max(2, int(math.ceil(ln[i] / 0.75)) + 1))
            for depth in depths:
                for t in ts:
                    out.append((lp[i] + d[i] * t + nin[i] * depth, depth))
                k = 1 + nin[i] @ nin[j]  # the mitre at the corner to the next edge
                if k > 0.3:
                    out.append((lp[j] + (nin[i] + nin[j]) / k * depth, depth))
    if not out:
        return np.zeros((0, 2))
    pts = np.array([p for p, _ in out])
    dep = np.array([d for _, d in out])
    ok = inside(pts, a, b) & (dist_to(pts, a, b) >= dep - 0.02)
    keep, cells = [], set()
    for p in pts[ok]:
        cell = (round(p[0] / 0.06), round(p[1] / 0.06))
        if cell not in cells:
            cells.add(cell)
            keep.append(p)
    return np.array(keep) if keep else np.zeros((0, 2))


def w2b(x, y, off=(0, 0)):
    """Sprite px (top-left origin, y down) -> Blender units (assembly centre at the origin, y up)."""
    return (x + off[0] - W / 2) * PX, (H / 2 - y - off[1]) * PX


# --- solids ------------------------------------------------------------------------------------------

def solid(bm, walls, cuts, extra, z_of, z_bottom, mat_of, off, smooth_top=False):
    """A closed solid over the region inside the loops `walls`: its top triangulated with
    the loops `cuts` as edges too and the points `extra`, each top vertex at z_of(points px), a flat
    bottom at z_bottom, vertical walls. mat_of(centroids px) gives the top faces' material slots; a
    wall takes its top face's."""
    a, b = segs(walls)
    verts2, edges, wall_edge = [], [], []
    for lp, is_wall in [(lp, True) for lp in walls] + [(lp, False) for lp in cuts]:
        base = len(verts2)
        verts2 += [Vector(p) for p in lp]
        for i in range(len(lp)):
            edges.append((base + i, base + (i + 1) % len(lp)))
            wall_edge.append(is_wall)
    n_wall = sum(len(lp) for lp in walls)
    verts2 += [Vector(p) for p in extra]
    vo, eo, fo, ov, oe, _ = delaunay_2d_cdt(verts2, edges, [], 0, 1e-5)
    P = np.array([[v.x, v.y] for v in vo])
    on_wall = np.array([any(o < n_wall for o in orig) for orig in ov])
    z = z_of(P, on_wall)
    top = [bm.verts.new((*w2b(x, y, off), zz)) for (x, y), zz in zip(P, z)]
    bot = [bm.verts.new((*w2b(x, y, off), z_bottom)) for x, y in P]
    tris = [f for f in fo if len(f) == 3]
    cen = np.array([P[list(f)].mean(0) for f in tris])
    keep = inside(cen, a, b)
    mats = mat_of(cen)
    edge_mat = {}
    for f, k, m in zip(tris, keep, mats):
        if not k:
            continue
        try:
            ft = bm.faces.new([top[f[0]], top[f[1]], top[f[2]]])
            fb = bm.faces.new([bot[f[2]], bot[f[1]], bot[f[0]]])
        except ValueError:
            continue
        ft.material_index = fb.material_index = int(m)
        ft.smooth = smooth_top
        for i in range(3):
            edge_mat[frozenset((f[i], f[(i + 1) % 3]))] = int(m)
    for (p, q), orig in zip(eo, oe):
        if not any(wall_edge[o] for o in orig) or frozenset((p, q)) not in edge_mat:
            continue
        try:
            fw = bm.faces.new([top[p], top[q], bot[q], bot[p]])
        except ValueError:
            continue
        fw.material_index = edge_mat[frozenset((p, q))]
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")


def build(key, pos, off, sprite, fades, coll, closed=False):
    """One shape, whole, in assembly coordinates: the object, or with `closed` the plain closed solid
    its outline shell is made from (the plan as one low prism)."""
    idx, colors = frame_idx(pos)
    m = SM.masks(idx.tolist(), colors)
    inner = np.array(m["inner"])
    gem = inner & is_gem(idx)
    steel = inner & is_steel(idx)
    eps, strokes, reach = TRACE[pos]
    plan_loops = vectorise(inner, eps)
    gem_loops = vectorise(gem, eps)
    bm = bmesh.new()
    flat = lambda zz: (lambda P, on: np.full(len(P), zz))  # noqa: E731
    slot = lambda k: (lambda cen: np.full(len(cen), k))  # noqa: E731
    ga, gb = segs(gem_loops)

    def gem_z(P, on=None):
        d = dist_to(P, ga, gb)
        if on is not None:
            d[on] = 0.0
        return Z_GEM + GEM_H * np.sin(0.5 * np.pi * np.clip(d / GEM_R, 0, 1))

    n_cls = len(CUTS) + 1
    INK, GEM, GLINT = 0, n_cls + 1, n_cls + 2
    if closed:
        solid(bm, plan_loops, [], [], flat(Z_SHELL), 0.0, slot(0), off)
    else:
        # the dark plate: the sprite's ink between the tines, and under everything
        solid(bm, plan_loops, [], [], flat(Z_PLATE), 0.0, slot(INK), off)
        # the steel, cut into its tone bands
        if strokes:
            steel_loops = vectorise(stroked_steel(plan_loops, gem_loops, (idx >= 0) & ~steel & ~gem, np.array(m["border"])),
                                    0.45, SS, 0.3)
        else:
            steel_loops = vectorise(steel, eps)
        cls, css = tone_classes(idx, steel, along_blades(idx, steel, steel_loops, reach) if reach else None)
        cuts, tests = [], []
        for k in list(range(BASE + 1, n_cls)) + list(range(BASE - 1, -1, -1)):
            loops = vectorise(cls >= k if k > BASE else cls <= k, min(eps, TONE_EPS), css)
            if loops:
                cuts += loops
                tests.append((k, *segs(loops)))
        sa, sb = segs(steel_loops)

        def steel_z(P, on):
            d = dist_to(P, sa, sb)
            d[on] = 0.0
            return Z_EDGE + (Z_TOP - Z_EDGE) * np.clip(d / CHAMFER, 0, 1)

        def steel_mat(cen):
            out = np.full(len(cen), BASE)
            for k, a, b in tests:  # brighter then darker, each from the base outward
                hit = inside(cen, a, b)
                clash = hit & (((k > BASE) & (out < BASE)) | ((k < BASE) & (out > BASE)))
                out[hit & ~clash] = k
                if clash.any():  # two fits overlap: the pixel under the point decides
                    px = cls[np.clip((cen[clash, 1] * css).astype(int), 0, H * css - 1),
                             np.clip((cen[clash, 0] * css).astype(int), 0, W * css - 1)]
                    out[clash] = px
            return out + 1

        solid(bm, steel_loops, cuts, rings(steel_loops, [CHAMFER]), steel_z, Z_PLATE - 0.006, steel_mat, off)
    if not closed:
        # the gem: a low cabochon on the sprite's blue square
        solid(bm, gem_loops, [], rings(gem_loops, [0.45, 0.95, 1.55, 2.3, 3.2]), gem_z, Z_PLATE - 0.006,
              slot(GEM), off, smooth_top=True)
        # the sprite's white glint up-left (art rule 2: a flush spot on the dome, not a bump)
        gy, gx = np.argwhere(idx == 143)[0] if (idx == 143).any() else (25, 22)
        for r, mat, lift, sides in ((0.52, GLINT, 0.006, 10),):
            ring = np.array([[gx + 0.5 + r * math.cos(2 * math.pi * s / sides), gy + 0.5 + r * math.sin(2 * math.pi * s / sides)]
                             for s in range(sides)])
            ok = inside(ring, ga, gb)
            ring[~ok] = ring[~ok] * 0.5 + np.array([gx + 0.5, gy + 0.5]) * 0.5
            vs = [bm.verts.new((*w2b(x, y, off), zz + lift)) for (x, y), zz in zip(ring, gem_z(ring))]
            f = bm.faces.new(list(reversed(vs)))
            f.material_index = mat
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}_{key}{'_closed' if closed else ''}")
    bm.to_mesh(me)
    bm.free()
    if not closed:
        tag = f"nsh195{key}"
        base_fade = fades[min(fades)]
        frames = lambda i: {DATA[n]["frames"][p]["index"]: max(1, i - k)  # noqa: E731
                            for n in PIECES for p, k in fades.items() if k != base_fade}
        me.materials.append(common.palette_material(sprite, 1, tag + "ink", metallic=0.0, roughness=0.9))
        for k in range(n_cls):
            mat = common.palette_material(sprite, max(1, PAINT[pos][k] - base_fade), f"{tag}c{k}", metallic=METALLIC,
                                          roughness=ROUGH[k], frames=frames(PAINT[pos][k]) or None)
            bsdf = next(nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:  # polished steel: F0 up (D176)
                bsdf.inputs["Specular IOR Level"].default_value = SPEC
            me.materials.append(mat)
        me.materials.append(common.palette_material(sprite, 153, tag + "gem", metallic=0.0, roughness=0.12, emission_strength=0.55))
        me.materials.append(common.palette_material(sprite, 143, tag + "glint", emission_strength=1.0))
    obj = bpy.data.objects.new(me.name, me)
    coll.objects.link(obj)
    return obj


def split_open(obj, layout, coll, tag):
    """The outline shell cut into the pieces' boxes and left open at the cuts (no ink along the seams)."""
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
        me = bpy.data.meshes.new(f"{name}{tag}_outline")
        bm.to_mesh(me)
        bm.free()
        for mm in obj.data.materials:
            me.materials.append(mm)
        s = bpy.data.objects.new(me.name, me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    whole_dir = Path(argv[argv.index("--whole") + 1]) if "--whole" in argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()
    layout = [(n, x0 + 12 - W // 2, y0 + 14 - H // 2) for n, x0, y0 in GRID]
    per_file = {}
    for key, suffix, variant, pos, shown, fades, off in SHAPES:
        whole = build(key, pos, off, sprite, fades, coll)
        closed = build(key, pos, off, sprite, fades, coll, closed=True)
        bpy.context.view_layer.update()
        shell = common.outline_shell(closed, coll, voxel=0.010, faces=3500, smooth=3, inside=0.003, islands="outer")
        bpy.data.objects.remove(closed)
        bpy.context.view_layer.update()
        if whole_dir:
            common.export_glb([whole, shell], whole_dir / f"{key}.glb")
        pieces = common.split_assembly(whole, [(f"{n}{suffix}{variant}", cx, cy) for n, cx, cy in layout])
        shells = split_open(shell, layout, coll, f"{suffix}{variant}")
        tris = sum(len(p.vertices) - 2 for p in whole.data.polygons)
        print(f"{NAME} {key}: {tris} triangles whole, shell {len(shell.data.polygons)} faces")
        bpy.data.objects.remove(shell)
        bpy.data.objects.remove(whole)
        for n, _, _ in layout:
            pc, sh = pieces[f"{n}{suffix}{variant}"], shells[n]
            # smooth faces with every real crease sharp: flat faces in one plane share their
            # vertices in the glb (the look is the flat-shaded one, the file about a third smaller)
            pc.data.shade_smooth()
            pc.data.set_sharp_from_angle(angle=math.radians(12))
            if variant:  # -f3's two drawings, each shown on its own frame
                fr = [DATA[n]["frames"][p]["index"] for p in shown]
                common.frame_part(pc, fr)
                common.frame_part(sh, fr)
            per_file.setdefault((n, suffix), []).extend([pc, sh])
    bpy.context.view_layer.update()
    for (n, suffix), group in per_file.items():
        want = [p for _, sfx, _, _, shown, _, _ in SHAPES if sfx == suffix for p in shown]
        sprites = [dict(s, frames=[s["frames"][p] for p in sorted(want)]) for s in DATA[n]["sprites"]]
        common.export_sprite_model(ROOT, group, f"enemies/{n}{suffix}", sprites)


if __name__ == "__main__":
    main()
