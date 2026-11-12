"""DELIANI's purple hull (shapesz.dat 550-575, 580, 582-583, 593-595 and 290-304 on layer 2, background 3; maps
1-5, 3-11 New Deli and 4-1 HARVEST): one model per tile, built in context (lib_delbld.py; DECISIONS.md D34,
D83, D65).

What it is: the overhead hull the ship flies under (background 3 is drawn over the player in DELIANI):
blocks of purple deck plating (575, a brick-like pattern of plates) edged by a thick bumper tube, purple
with grey clamp rings every tile, that runs round each block and turns its corners in rounded elbows.
- straight rims: 551 (top edge of a block), 571 (bottom), 560 (left), 562 (right); the horizontal tube
  fills the tile's 28 rows, the vertical one 19-20 of its 24 columns, the deck the rest;
- outer corners 550, 552, 570, 572 and inner corners 553, 554, 563, 564 (where a block's rim turns into an
  arm's): elbows of the same tube;
- a cross tube of deck plating bridging two blocks (595, its ends 593/594 at the rims);
- set into the deck: a vent grille with open slots (574), blue panels (561, 573), a blue machine with
  red lights beside the rim (582, 583) and, on HARVEST, a steel panel with a red light (580);
- the spring assemblies (555-559, 565-569, 290-304): two segmented beams linked by curved arms.

How each tile is built (2x MMPX pixels, so curves are smooth; transparent pixels stay open, so the outline
is the sprite's): a height field over the tile's pixels, from what each part is rather than from the
pixels' brightness (art rule 2: the art's shading and sheen are lighting):
- tubes: analytic primitives per tile (straight lines and elliptic elbows, in tile px) give each pixel its
  distance from the tube's centre line; the tube's section is a half ellipse 0.26 high, so straights,
  elbows and the tees where a cross tube meets a rim are one smooth surface; each ring of the tube is a
  grey clamp or a purple segment by the majority of its pixels (a clamp is one part, not the art's
  speckle of shading);
- clamps (D136): chunky brackets round the tube, a squarer section standing 0.05 proud with eased ends;
  their big ink-dark areas are housings sunk 0.07 in their own shade (the art's index there), with the
  slats across them standing between grooves; a clamp's foot on the deck is a block 0.11 high with
  rounded edges;
- the clamps' outer half on the side rims (560, 562 and the cut clamps of 593, 594; D152): machined parts,
  not the height field: the housing a pocket with vertical walls and a flat floor in the art's ink, the
  slats bevelled bars standing in a dark well (CLAMP_DETAIL, rectangles fitted to the 1x art);
- the tubes' long thin ink lines (the clamps' slats and outlines, the segments' greek keys, the elbows'
  ribs) are grooves 0.06 deep and the purple segments' big dark areas shallow recesses, both floored in
  the art's ink shade of their ramp; the segments' darker seam lines are shallower grooves;
- deck: plates 0.03 proud between seams 0.02 deep (the art's darker purple lines, found against the
  plating round them), the seams floored in the art's seam shade, with deeper grooves on its ink lines;
- grille: its bars proud of a sunk frame, slots open; panels sunk, the machine a raised block with its red
  lights glowing;
- springs: no primitives (their arms are drawn in perspective): the art's blocks and arms as plates (the
  regions between its ink lines), each standing by its brightness with rounded edges, so a thin arm is a
  round bar and a block a box; the ink between them is a groove; each plate takes its own median palette
  index (the art's dark blocks stay dark), snapped within its ramp to one set of shades for all spring tiles.
Smooth edges (D149): the height field is a grid of 2x pixels, so the outline and every edge between two
parts (clamp and housing, plate and seam, tube and groove) would follow the art's pixel staircases. Each
such edge is moved onto a smooth curve through the middles of its steps (lib_delbld.boundary_moves:
straight runs and square corners stay, stairs become lines and curves); the corners on a tile edge with
art on both sides stay put, so neighbours built in their own blocks still meet. Specks of a part (at most
SPECK 2x pixels) join the part round them; each part shades smooth within itself and creases where it
meets another; the occlusion bake samples the moved surface.
Colours: one palette index per part (grey clamps, from the face of the clamp; purple tube, deck, seams,
housings, the tubes' ink, brackets, blue, red; a spring's plates each their own), the median of its
pixels with the darkest and brightest 15% dropped. In game the sun shines from the camera's side into
every groove, so a groove's occlusion alone never darkens it as the art's ink: grooves take the art's
ink shade, as the girders' window lips do (D134).

Heights (layer 2 models stay within about +-0.35 of the pass height): deck top 0, tube crown +0.26,
clamps about +0.31, underside -0.22.

Run: tools/build-models.sh -j 2 assets/blender/tiles/delbld_hull.py
     Blender -b --factory-startup -P delbld_hull.py -- [--no-bake] [tile ...]
"""

import math
import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_delbld as kit  # noqa: E402
import lib_tiles as lt  # noqa: E402

ROOT = common.repo_root(__file__)
SHAPES = "shapesz"
LAYER = 2

BOTTOM = -0.22
TUBE_H = 0.26
CLAMP_UP = 0.05
GROOVE = -0.06
SEAM = -0.02
PLATE_UP = 0.03
BRACKET_UP = 0.11
HOUSING = -0.07
SEAM_DARK = 0.05
CROSS_H = 0.22
SPRING_H = 0.24
#: A part's piece of at most this many 2x cells is a speck of the art, not a shape (D149).
SPECK = 3
#: How far the part edges and the outline are smoothed (lib_delbld.boundary_moves' sigma, in 2x pixel
#: corners) and how far the outline's smoothed stretches are pushed out (cells), D149. The outer elbows'
#: outline is one long arc of 1x steps: a curve through them all leaves it at IoU 0.985-0.988 against the
#: tile's 1x pixels (D134's measure), so there it is smoothed less and grown a little to stay >= 0.99.
EDGE_SIGMA = 2.0
OUTLINE = {550: (0.9, 0.06), 552: (0.9, 0.06), 570: (0.9, 0.06), 572: (0.9, 0.06)}
OUTLINE_DEFAULT = (2.0, 0.0)
#: Flat faces within this many degrees merge (lib_delbld.tidy_flat): the slopes round a smoothed plate turn
#: a few degrees per cell, and each as its own face made the deck half as big again.
FLAT_MERGE = 5.0
#: The shades a spring's plates snap to, within their own ramp (grey, purple), every other step.
SPRING_SHADES = (2, 4, 6, 8, 10, 12, 81, 83, 85, 87, 89, 91)
HULL = dict(metallic=0.12, roughness=0.5)
#: The clamps' outer half, machined (D152): the art's dark housing, its grille of slats and the slot beside
#: the clamp's face, as hard-surface parts instead of the height field (where D149's smoothing melted them).
#: Rectangles in the tile's 1x px (x0, y0, x1, y1; x right, y down), fitted to the art. A pocket is cut out of
#: the height field (vertical walls, its edges not moved) and floored POCKET_DEPTH below the clamp's face in
#: the art's ink there (D136); a bar is a bevelled bar standing in a pocket, BAR_INSET below the face. The
#: art's transparent pixels in a pocket stay open, as square holes.
CLAMP_DETAIL = {
    560: dict(pockets=(("housing", (2, 1, 6, 7)), ("grille", (0, 7, 11, 14)), ("grille", (10, 2, 11, 7))),
              bars=((1, 8, 10, 9), (1, 10, 10, 11), (1, 12, 10, 13))),
    # The same clamp's top five rows, cut by the cross tube.
    593: dict(pockets=(("housing", (2, 1, 6, 5)), ("grille", (10, 2, 11, 5))), bars=()),
}


def _mirror(d):
    flip = lambda r: (lt.TILE_W - r[2], r[1], lt.TILE_W - r[0], r[3])  # noqa: E731
    return dict(pockets=tuple((k, flip(r)) for k, r in d["pockets"]), bars=tuple(flip(r) for r in d["bars"]))


CLAMP_DETAIL[562] = _mirror(CLAMP_DETAIL[560])   # the right rim is the left one mirrored, pixel for pixel
CLAMP_DETAIL[594] = _mirror(CLAMP_DETAIL[593])
POCKET_DEPTH = {"housing": 0.07, "grille": 0.08}
BAR_INSET = 0.015
BAR_CHAMFER = 0.25 * lt.PX

# Tube primitives, in tile px (x right 0..24, y down 0..28):
#   ("line", (x0, y0), (x1, y1), half_width, height)
#   ("arc", (cx, cy), (sx, sy), (rx, ry), (w0, w1), height): the elbow's centre line runs from
#   (cx + sx*rx, cy) at phi = 0 to (cx, cy + sy*ry) at phi = 90 degrees, its half width from w0 to w1.
H_RIM = ("line", (-30, 14), (54, 14), 14, TUBE_H)          # 551 top, 571 bottom: the tube fills the rows
L_RIM = ("line", (9.75, -30), (9.75, 58), 9.75, TUBE_H)     # 560: columns 0-19, the deck to its right
R_RIM = ("line", (14, -30), (14, 58), 10, TUBE_H)           # 562: columns 4-23, the deck to its left


def arc(cx, cy, sx, sy, rx, ry, w0, w1):
    return ("arc", (cx, cy), (sx, sy), (rx, ry), (w0, w1), TUBE_H)


SPECS = {
    575: dict(),
    551: dict(tubes=[H_RIM]),
    571: dict(tubes=[H_RIM]),
    560: dict(tubes=[L_RIM]),
    562: dict(tubes=[R_RIM]),
    # Outer corners: from the vertical rim to the horizontal one.
    550: dict(tubes=[arc(24, 28, -1, -1, 14.25, 14, 9.75, 14)]),
    552: dict(tubes=[arc(0, 28, 1, -1, 14, 14, 10, 14)]),
    570: dict(tubes=[arc(24, 0, -1, 1, 14.25, 14, 9.75, 14)]),
    572: dict(tubes=[arc(0, 0, 1, 1, 14, 14, 10, 14)]),
    # Inner corners: a block's rim turning into an arm's; the deck fills the rest.
    553: dict(tubes=[arc(0, 0, 1, 1, 9.75, 14, 9.75, 14)]),
    554: dict(tubes=[arc(24, 0, -1, 1, 10, 14, 10, 14)]),
    563: dict(tubes=[arc(0, 28, 1, -1, 9.75, 14, 9.75, 14)]),
    564: dict(tubes=[arc(24, 28, -1, -1, 10, 14, 10, 14)]),
    # The cross tube and its ends at the rims.
    595: dict(tubes=[("line", (-30, 13.5), (54, 13.5), 13, CROSS_H)]),
    593: dict(tubes=[L_RIM, ("line", (-30, 13.5), (9.75, 13.5), 13, CROSS_H)]),
    594: dict(tubes=[R_RIM, ("line", (14, 13.5), (54, 13.5), 13, CROSS_H)]),
    # Set into the deck.
    574: dict(kind="grille"),
    561: dict(kind="panel"),
    573: dict(kind="panel"),
    582: dict(kind="machine"),
    583: dict(kind="machine"),
    580: dict(kind="machine"),   # HARVEST: a steel panel with a red light set in the deck
}
SPRINGS = (555, 556, 557, 558, 559, 565, 566, 567, 568, 569, 290, 291, 292, 293, 294, 300, 301, 302, 303, 304)
for _n in SPRINGS:
    SPECS[_n] = dict(kind="spring")
TILES = tuple(SPECS)

GREY = set(range(1, 16))
PURPLE = set(range(80, 96))
BLUE = set(range(48, 64)) | set(range(128, 140))
RED = set(range(112, 120))
STEEL = set(range(96, 112))
INK = {1, 2, 3, 80, 81}


def tube_field(spec_tubes, h, w, scale):
    """The tube primitives over a tile's h x w grid (`scale` px per tile px): height (0 where no tube),
    which primitive is highest at each pixel, the pixel's ring along it (a 1-px step along the
    centre line), so a clamp or a segment is a whole ring of the tube, and the pixel's distance from
    the centre line as a fraction of the half width with that primitive's crown height (for the
    clamps' squarer section)."""
    ys, xs = np.mgrid[0:h, 0:w]
    px = (xs + 0.5) / scale
    py = (ys + 0.5) / scale
    out = np.zeros((h, w))
    prim = np.full((h, w), -1)
    ring = np.zeros((h, w), dtype=int)
    qn = np.full((h, w), 1.0)
    top = np.zeros((h, w))
    for i, t in enumerate(spec_tubes):
        if t[0] == "line":
            (x0, y0), (x1, y1), hw, height = t[1], t[2], t[3], t[4]
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy)
            u = np.clip(((px - x0) * dx + (py - y0) * dy) / (L * L), 0, 1)
            d = np.hypot(px - (x0 + u * dx), py - (y0 + u * dy))
            wid = np.full_like(d, hw)
            along = u * L
        else:
            (cx, cy), (sx, sy), (rx, ry), (w0, w1), height = t[1], t[2], t[3], t[4], t[5]
            ex = (px - cx) * sx / rx
            ey = (py - cy) * sy / ry
            phi = np.clip(np.arctan2(np.maximum(ey, 0), np.maximum(ex, 0)), 0, math.pi / 2)
            rho = np.hypot(np.maximum(ex, 0), np.maximum(ey, 0))
            R = np.hypot(rx * np.cos(phi), ry * np.sin(phi))
            d = np.where((ex < 0) | (ey < 0), np.inf, np.abs(rho - 1) * R)
            wid = w0 + (w1 - w0) * phi / (math.pi / 2)
            along = phi * (rx + ry) / 2
        hgt = height * np.sqrt(np.clip(1 - (d / wid) ** 2, 0, 1))
        better = hgt > out
        out = np.where(better, hgt, out)
        prim = np.where(better, i, prim)
        ring = np.where(better, np.floor(along).astype(int), ring)
        qn = np.where(better, np.clip(d / wid, 0, 1), qn)
        top = np.where(better, height, top)
    return out, prim, ring, qn, top


def ramp_of(v):
    if v in RED:
        return "red"
    if v in BLUE:
        return "blue"
    if v in PURPLE:
        return "purple"
    if v in GREY:
        return "grey"
    if v in STEEL:
        return "steel"
    return "other"


def majority_fill(cls, ink, size=2):
    """Ink pixels take the most common class round them (ink is lighting or a seam, not a part); inside
    a big dark area (no other pixel near) a pixel keeps its own ramp."""
    out = cls.copy()
    h, w = cls.shape
    ys, xs = np.nonzero(ink)
    for y, x in zip(ys, xs):
        win = cls[max(0, y - size):y + size + 1, max(0, x - size):x + size + 1]
        winink = ink[max(0, y - size):y + size + 1, max(0, x - size):x + size + 1]
        vals = [c for c, k in zip(win.ravel(), winink.ravel()) if not k and c != ""]
        if vals:
            out[y, x] = max(set(vals), key=vals.count)
        elif cls[y, x] == "":
            out[y, x] = "purple"
    return out


def thin_lines(mask):
    """Pixels of `mask` that are part of thin lines, not big areas (big dark areas are shadow)."""
    m = np.pad(mask, 1).astype(int)
    count = sum(m[1 + dy:m.shape[0] - 1 + dy, 1 + dx:m.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    return mask & (count <= 6)


def seam_lines(ts, grid, lum, solid):
    """The plating's seams: its darker purple pixels (80-86) that are darker than the plating round them
    (a 5x5 window of the 2x art), so a seam line and its crossings are found, but a whole plate drawn in
    a darker shade stays a plate."""
    k = np.ones(5)
    def box(a):
        a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, a)
        return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, a)
    mean = box(np.where(solid, lum, 0.0)) / np.maximum(box(solid.astype(float)), 1)
    step = ts.lum[88] - ts.lum[86]
    return solid & np.isin(grid, list(range(80, 87))) & (lum < mean - 0.3 * step)


def long_lines(mask, min_px):
    """The pixels of `mask` in 8-connected pieces of at least `min_px` pixels (a line, not a speck)."""
    lab = labels(np.where(mask, "m", ""), diagonal=True)
    ids, counts = np.unique(lab[lab > 0], return_counts=True)
    keep = set(int(i) for i, c in zip(ids, counts) if c >= min_px)
    return mask & np.isin(lab, list(keep))


def labels(cls, diagonal=False):
    """4-connected (or 8-) regions of equal non-empty class: an int label per pixel (0 = none)."""
    h, w = cls.shape
    lab = np.zeros((h, w), dtype=int)
    n = 0
    for y0 in range(h):
        for x0 in range(w):
            if lab[y0, x0] or cls[y0, x0] == "":
                continue
            n += 1
            c = cls[y0, x0]
            stack = [(y0, x0)]
            lab[y0, x0] = n
            while stack:
                y, x = stack.pop()
                nbs = ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
                if diagonal:
                    nbs += ((y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1))
                for yy, xx in nbs:
                    if 0 <= yy < h and 0 <= xx < w and not lab[yy, xx] and cls[yy, xx] == c:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
    return lab


def erosion_depth(lab, steps):
    """How many 4-neighbour erosions each labelled pixel survives inside its own region (0..steps)."""
    depth = np.zeros(lab.shape)
    cur = lab > 0
    for _ in range(steps):
        p = np.pad(np.where(cur, lab, 0), 1)
        same = (p[1:-1, 1:-1] > 0)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            same &= p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx] == p[1:-1, 1:-1]
        depth += same
        cur = same
    return depth


def absorb_specks(part_id, height, solid, max_px, tile=None):
    """Pieces of a part (4-connected) of at most `max_px` cells take the part most common round them
    and that part's mean height there (in place). `tile` (th, tw): a piece touching a tile's edge row or
    column is left as it is, as its size there depends on the neighbour the block was built with."""
    H, W = part_id.shape
    lab = labels(np.where(solid, part_id.astype(str), ""))
    ids, counts = np.unique(lab[lab > 0], return_counts=True)
    for k in ids[counts <= max_px]:
        ys, xs = np.nonzero(lab == k)
        if tile and (np.isin(ys % tile[0], (0, tile[0] - 1)).any() or np.isin(xs % tile[1], (0, tile[1] - 1)).any()):
            continue
        nb = {}
        for y, x in zip(ys, xs):
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < H and 0 <= xx < W and solid[yy, xx] and lab[yy, xx] != k:
                    nb.setdefault(int(part_id[yy, xx]), []).append(height[yy, xx])
        if not nb:
            continue
        best = max(nb, key=lambda p: len(nb[p]))
        part_id[ys, xs] = best
        height[ys, xs] = float(np.mean(nb[best]))


def add_machined(ts, bm, frame, mats, centre, art1, floor, solid, pocket_kind, bars, bar_cells, face, depth):
    """The machined clamp parts (D152): each pocket's floor, a slab over its cells (the art's holes open,
    no wall against the field round it, whose own walls close the pocket), in the art's ink there; and
    the bevelled bars standing in them, following the clamp's face along their length."""
    def index(sel):
        for region in (centre, (slice(None), slice(None))):
            idx = kit.region_index(ts, art1[region][sel[region]], prefer=GREY)
            if idx is not None:
                return idx
        return None

    floor_mat = {}
    for k in sorted(set(pocket_kind[floor])):
        floor_mat[k] = mats(index(floor & (pocket_kind == k) & ~bar_cells), metallic=0.2, roughness=0.45)
    before = set(bm.faces)
    lt.mask_slab(bm, floor, frame, BOTTOM, 0.0, lambda x, y: floor_mat[pocket_kind[y, x]], top_height=face - depth,
                 smooth_top=True, support=floor, walls=solid)
    # Flat-shaded, so tidy_flat merges the floor's cells (it turns only a few degrees across a pocket).
    for f in set(bm.faces) - before:
        f.smooth = False
    if not bars:
        return
    bar_mat = mats(index(bar_cells), metallic=0.2, roughness=0.3)
    for x0, y0, x1, y1 in bars:
        along_x = (x1 - x0) >= (y1 - y0)
        prof = face[y0:y1, x0:x1].mean(0 if along_x else 1)
        dep = depth[y0:y1, x0:x1].max()
        pos = np.arange(x0, x1) + 0.5 if along_x else np.arange(y0, y1) + 0.5
        kit.machined_bar(bm, frame, (x0, y0, x1, y1), lambda s: float(np.interp(s, pos, prof)) - BAR_INSET,
                         lambda s: float(np.interp(s, pos, prof)) - dep - 0.01, BAR_CHAMFER, bar_mat)


def centre_of(PR, PC, TH, TW):
    """The pattern's cells in its block (one ring of context round it)."""
    return (slice(TH, (PR + 1) * TH), slice(TW, (PC + 1) * TW))


def neighbours_of(ts, n):
    px = kit.pixels(ts, n)
    edge = {"U": px[0], "D": px[-1], "L": px[:, 0], "R": px[:, -1]}
    out = {}
    for s in "LRUD":
        out[s] = -1 if np.all(edge[s] == 0) else kit.usual_neighbour(ts, n, s, allowed=set(TILES))
    return out


def build(ts, pattern, name, coll, bake_on, block_kind=None):
    """One model for `pattern` (rows of tiles; one tile for the kit's pieces), built in its 3x3 (or
    bigger) block. `block_kind`: build the whole pattern as that kind (a whole-structure model, D47)."""
    S = 2
    PR, PC = len(pattern), len(pattern[0])
    rows, cols = PR + 2, PC + 2
    TH, TW = lt.TILE_H * S, lt.TILE_W * S
    H, W = rows * TH, cols * TW
    n = pattern[0][0]
    if block_kind or SPECS[n].get("kind") == "spring":
        # A spring tile meets several different tiles on a side (555 is under 565 and under 567 in the
        # same assembly), so its context is its own edge pixels carried outward: what it builds at an
        # edge depends on that edge alone, and the tile across, built the same way from the art's
        # continuing pixels, meets it.
        own = np.vstack([np.hstack([ts.tiles[t]["px2"] for t in row]) for row in pattern])
        grid = np.pad(own, ((TH,) * 2, (TW,) * 2), mode="edge").astype(np.int32)
        cells = [[pattern[min(max(r - 1, 0), PR - 1)][min(max(c - 1, 0), PC - 1)] for c in range(cols)] for r in range(rows)]
    else:
        cells = kit.context_cells(ts, n, neighbours_of(ts, n))
        grid = np.full((H, W), -1, dtype=np.int32)
        for r in range(rows):
            for c in range(cols):
                t = cells[r][c]
                if t >= 0:
                    grid[r * TH:(r + 1) * TH, c * TW:(c + 1) * TW] = ts.tiles[t]["px2"]
    solid = grid > 0
    cls = np.full((H, W), "", dtype=object)
    for v in np.unique(grid[solid]):
        cls[grid == v] = ramp_of(int(v))
    ink = np.isin(grid, list(INK)) & solid
    cls = majority_fill(np.where(solid, cls, ""), ink & ~np.isin(cls, ["blue", "red"]))

    # Height per cell: tubes (per context cell, each from its own tile's spec), deck, details.
    height = np.zeros((H, W))
    tube = np.zeros((H, W), dtype=bool)
    plated = np.zeros((H, W), dtype=bool)
    key = np.full((H, W), -1)
    qn = np.ones((H, W))
    crown = np.zeros((H, W))
    kind = np.full((H, W), "deck", dtype=object)
    for r in range(rows):
        for c in range(cols):
            t = cells[r][c]
            if t < 0:
                continue
            spec = SPECS.get(t, {})
            sl = (slice(r * TH, (r + 1) * TH), slice(c * TW, (c + 1) * TW))
            k = block_kind or spec.get("kind", "hull")
            kind[sl] = k
            if spec.get("tubes") and not block_kind:
                f, prim, ring, q, top = tube_field(spec["tubes"], TH, TW, S)
                height[sl] = f
                qn[sl] = q
                crown[sl] = top
                tube[sl] = f > 0.02
                plated_prims = [i for i, tp in enumerate(spec["tubes"]) if tp[-1] == CROSS_H]
                plated[sl] = (f > 0.02) & np.isin(prim, plated_prims)
                key[sl] = np.where(prim >= 0, (r * cols + c) * 100000 + prim * 1000 + ring, -1)

    # On the tubes a part is a whole ring: a grey clamp or a purple segment by the majority of the ring's
    # pixels, so the art's shading and seams don't speckle it (the plated cross tube is all deck).
    rings = tube & ~plated & np.isin(cls, ["grey", "purple"])
    for k in np.unique(key[rings]):
        sel = rings & (key == k)
        clean = sel & ~ink
        grey = int(np.count_nonzero(clean & (cls == "grey")))
        purple = int(np.count_nonzero(clean & (cls == "purple")))
        cls[sel] = "grey" if grey > purple else "purple"
    cls[plated & np.isin(cls, ["grey", "purple"])] = "purple"
    lum = np.where(solid, ts.lum[np.maximum(grid, 0)], 0.0)
    line_ink = thin_lines(ink)
    deck = solid & ~tube & (kind == "hull")
    # Deck plates: the brick pattern's seams (darker purple lines, found against the plating round them)
    # are grooves between plates standing proud. The seams are floored in the art's seam shade (their own
    # palette index, as a window's lip on the girders, D134): in game the sun shines into a groove and
    # its occlusion alone left the plating a flat sheet.
    seam_px = long_lines(seam_lines(ts, grid, lum, solid), 8)
    seam = deck & seam_px
    pseam = plated & seam_px
    for sel, sm in ((deck, seam), (plated, pseam)):
        height[sel & ~sm & ~line_ink] += PLATE_UP
        height[sel & sm] += SEAM
    height[deck & line_ink] += GROOVE
    # Grey brackets on the deck (a clamp's foot): blocks with rounded edges, their ink lines grooves.
    bracket = deck & (cls == "grey") & ~ink
    # Rounded by a blurred mask, not by whole-pixel erosion steps, so they shade smooth (D149); on a tile's
    # edge rows and columns the erosion steps as before, as the seam's heights are the mean of both
    # sides' and the tile across may be built with a different neighbour.
    lab_b = labels(np.where(bracket, "b", ""))
    edge_b = np.clip(erosion_depth(lab_b, 2) / 2.0, 0, 1)
    ys, xs = np.mgrid[0:H, 0:W]
    rim = np.isin(ys % TH, (0, TH - 1)) | np.isin(xs % TW, (0, TW - 1))
    edge_b = np.where(rim, edge_b, np.clip((lt.blur(bracket.astype(float), 1.2) - 0.4) / 0.45, 0, 1))
    height[bracket] += (BRACKET_UP * (0.35 + 0.65 * np.sqrt(edge_b)))[bracket]
    # Tube clamps: a squarer section than the round purple segments, standing proud, with their ends
    # rounded (the raise is eased over a pixel), so each reads as a chunky bracket round the tube.
    clamp = tube & ~plated & (cls == "grey")
    box = crown * np.clip(1 - qn ** 3, 0, 1) ** (1 / 3)
    up = np.where(clamp, np.maximum(box - height, 0) + CLAMP_UP, 0.0)
    up = lt.blur(up, 0.8) * (tube & ~plated)
    height += up
    # Tube details: the art's thin ink lines (the clamps' slats and recesses, the segments' plate seams,
    # the elbows' radial ribs) are grooves, and so are the purple segments' darker seam lines (thin lines
    # darker than the plating round them).
    groove_t = tube & long_lines(line_ink & tube, 10)
    height[groove_t] += GROOVE
    purple_seg = tube & ~plated & (cls == "purple") & ~groove_t
    local = lt.blur(np.where(solid, lum, 0.0), 2.0) / np.maximum(lt.blur(solid.astype(float), 2.0), 1e-3)
    pseam_t = purple_seg & long_lines(thin_lines(purple_seg & (lum < local - SEAM_DARK)), 8)
    height[pseam_t] += GROOVE * 0.6
    # A clamp's (or a bracket's) big dark areas are housings: sunk below its face, in their own shade
    # (the art's palette index for that region), with the slats across them standing between grooves.
    housing = (clamp | bracket | (deck & (cls == "grey"))) & ink & ~line_ink
    height[housing] += HOUSING
    # A purple segment's big dark areas are shallow recesses. The tubes' ink (grooves and recesses) is
    # floored in the art's ink shade of its ramp, as the plating's seams: lit by the sun from the
    # camera's side, a groove's occlusion alone left the tube a plain drum.
    recess = tube & ~plated & (cls == "purple") & ink & ~line_ink
    height[recess] += HOUSING * 0.4
    tube_ink = (groove_t | recess) & ~housing
    # Grille: bars proud, the rest of the frame sunk; slots are open (transparent).
    grille = solid & (kind == "grille")
    height[grille] = np.where(lum[grille] > ts.lum[86], 0.04, -0.04)
    # Panels: sunk; machine: a raised block with its red lights.
    panel = solid & (kind == "panel")
    height[panel & (cls == "blue")] = -0.03
    height[panel & (cls != "blue")] = PLATE_UP
    machine = solid & (kind == "machine")
    height[machine & (cls == "blue")] = 0.10
    height[machine & (cls == "red")] = 0.12
    height[machine & (cls == "steel")] = 0.06
    height[machine & np.isin(cls, ["purple", "grey"])] = PLATE_UP
    # Springs: the art's blocks and arms as plates (regions between its ink lines, one part each),
    # each standing by its brightness (lit tops high, the blocks' shaded sides low; one scale for every
    # tile, so neighbours meet) with rounded edges, so a thin arm is a round bar and a block a box.
    spring = solid & (kind == "spring")
    plate_index = np.full((H, W), -1)
    spring_lab = np.zeros((H, W), dtype=int)
    if spring.any():
        lab = labels(np.where(spring & ~ink, cls, ""))
        spring_lab = lab
        lo, hi = ts.lum[84], ts.lum[92]
        # Each pixel's brightness smoothed within its colour (not across the ink lines' other side much),
        # so a plate stands about level and plates that cross a tile edge meet.
        lum_s = np.zeros((H, W))
        for c in ("grey", "purple", "blue", "red", "other"):
            m = spring & ~ink & (cls == c)
            if m.any():
                sm = lt.blur(np.where(m, lum, 0.0), 1.5) / np.maximum(lt.blur(m.astype(float), 1.5), 1e-3)
                lum_s[m] = sm[m]
        base = SPRING_H * np.clip((lum_s - lo) / (hi - lo), 0.15, 1.0)
        edge = erosion_depth(lab, 3) / 3.0
        height[spring] = (base + 0.04 * np.sqrt(np.clip(edge * (2 - edge), 0, 1)))[spring]
        # Ink between the plates: a groove below its neighbours.
        nb = lt.blur(np.where(spring & ~ink, height, 0.0), 1.0) / np.maximum(lt.blur((spring & ~ink).astype(float), 1.0), 1e-3)
        sink = spring & ink
        height[sink] = np.maximum(nb[sink] - 0.05, 0.0)
        # Each plate is its own part: the median palette index of its pixels (the art's dark blocks stay
        # dark, its arms light), snapped to the tile's few most used; ink takes its nearest plate's.
        plate_index = np.full((H, W), -1)
        for k in np.unique(lab[lab > 0]):
            sel = lab == k
            idx = kit.region_index(ts, grid[sel])
            if idx is not None:
                plate_index[sel] = idx
        for _ in range(4):
            todo = spring & (plate_index < 0)
            if not todo.any():
                break
            p = np.pad(plate_index, 1, constant_values=-1)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nbv = p[1 + dy:H + 1 + dy, 1 + dx:W + 1 + dx]
                take = todo & (plate_index < 0) & (nbv >= 0)
                plate_index[take] = nbv[take]
        # One set of shades for every spring tile, so the two halves of a plate that crosses a tile
        # edge (each median of its own half) land on the same shade.
        def snap(v):
            shades = [k for k in SPRING_SHADES if ramp_of(k) == ramp_of(int(v))]
            return min(shades, key=lambda k: abs(k - v)) if shades else v
        plate_index = np.where(plate_index >= 0, np.vectorize(snap)(np.maximum(plate_index, 0)), -1)

    # The clamps' outer half, machined (D152): pockets cut out of the field, floored in the art's ink, and
    # bevelled bars standing in them. Their cells take the 1x art's coverage (square holes, as the art's).
    pocket = np.zeros((H, W), dtype=bool)
    pocket_kind = np.full((H, W), "", dtype=object)
    bars = []
    if not block_kind:
        for r in range(rows):
            for c in range(cols):
                det = CLAMP_DETAIL.get(cells[r][c])
                if not det:
                    continue
                for pk, (x0, y0, x1, y1) in det["pockets"]:
                    sl = (slice(r * TH + y0 * S, r * TH + y1 * S), slice(c * TW + x0 * S, c * TW + x1 * S))
                    pocket[sl] = True
                    pocket_kind[sl] = pk
                for x0, y0, x1, y1 in det["bars"]:
                    bars.append((c * TW + x0 * S, r * TH + y0 * S, c * TW + x1 * S, r * TH + y1 * S))
    art1 = np.repeat(np.repeat(kit.context_grid(ts, cells), S, 0), S, 1)
    floor = pocket & (art1 > 0)
    bar_cells = np.zeros((H, W), dtype=bool)
    for x0, y0, x1, y1 in bars:
        bar_cells[y0:y1, x0:x1] = True
    if pocket.any():
        # The clamp's face over a pocket: its squarer section with the raise (a pocket's own cells may be
        # holes or ink that never took the raise), a function of the distance from the tube's centre only.
        face = box + CLAMP_UP
        depth = np.vectorize(lambda k: POCKET_DEPTH.get(k, 0.0))(pocket_kind)
        height[floor] = (face - depth)[floor]
        height[bar_cells & floor] = (face - BAR_INSET)[bar_cells & floor]
    solid = (solid & ~pocket) | floor
    _debug_dump(name, grid=grid, height=height, plate_idx=np.where(seam, 85, -1), solid=solid, tube=tube)
    # Materials: one palette index per part, from the centre tile's pixels (or the block's).
    centre = centre_of(PR, PC, TH, TW)
    mats = kit.Mats(ts, name.replace("delbld-hull-", "h"), **HULL)

    def part_index(sel, prefer, use_ink=False):  # noqa: E301
        for region in (centre, (slice(None), slice(None))):
            v = grid[region][sel[region] & (use_ink | ~ink[region])]
            idx = kit.region_index(ts, v, prefer=prefer)
            if idx is not None:
                return idx
        return None

    slot = {}
    for part, sel, prefer, kw in (
        ("tube_purple", tube & (cls == "purple"), PURPLE, {}),
        # A clamp's colour is its face's (the inner half of the tube's width), not its fins' and flanks'.
        ("tube_grey", tube & (cls == "grey") & (qn < 0.6), GREY, dict(metallic=0.2, roughness=0.28)),
        ("deck", (deck | panel | machine | grille | spring) & (cls == "purple"), PURPLE, {}),
        ("bracket", (deck | spring | machine | grille | panel) & (cls == "grey"), GREY, dict(metallic=0.2, roughness=0.35)),
        ("housing", housing, GREY, dict(metallic=0.2, roughness=0.45)),
        ("seam", seam, PURPLE, dict(roughness=0.7)),
        ("ink_purple", tube_ink & (cls == "purple"), PURPLE, dict(roughness=0.6)),
        ("ink_grey", tube_ink & (cls == "grey"), GREY, dict(metallic=0.2, roughness=0.45)),
        ("blue", solid & (cls == "blue"), BLUE, dict(metallic=0.2, roughness=0.3)),
        ("red", solid & (cls == "red"), RED, dict(emission_strength=1.2)),
        ("steel", solid & (cls == "steel"), STEEL, dict(metallic=0.2, roughness=0.4)),
    ):
        idx = part_index(sel, prefer, use_ink=part in ("housing", "seam", "ink_purple", "ink_grey"))
        if idx is not None:
            slot[part] = mats(idx, **kw)
    fallback = slot.get("deck") or slot.get("tube_purple") or next(iter(slot.values()))

    def part_at(x, y):
        """The part a cell belongs to (a material, or a carving that shares one): the edges between
        parts are what boundary_moves smooths."""
        c = cls[y, x]
        if spring[y, x] and plate_index[y, x] >= 0 and c in ("grey", "purple", "other"):
            return ("plate", int(plate_index[y, x]), c == "grey", int(spring_lab[y, x]))
        if c in ("red", "blue", "steel"):
            return (c, bool(grille[y, x] and height[y, x] > 0))
        if housing[y, x] and "housing" in slot:
            return ("housing",)
        if seam[y, x] and "seam" in slot:
            return ("seam",)
        if tube_ink[y, x]:
            part = "ink_grey" if c == "grey" else "ink_purple"
            if part in slot:
                return (part,)
        if tube[y, x]:
            return ("tube_grey" if c == "grey" else "tube_purple", bool(pseam_t[y, x]))
        if c == "grey":
            return ("bracket", bool(line_ink[y, x] and deck[y, x]))
        return ("deck", bool(line_ink[y, x] and deck[y, x]), bool(grille[y, x] and height[y, x] > 0))

    part_slot = {
        "housing": "housing", "seam": "seam", "ink_grey": "ink_grey", "ink_purple": "ink_purple",
        "tube_grey": "tube_grey", "tube_purple": "tube_purple", "bracket": "bracket", "deck": "deck",
        "red": "red", "blue": "blue", "steel": "steel",
    }

    def mat_for(part):
        if part[0] == "plate":
            return mats(part[1], **(dict(metallic=0.2, roughness=0.35) if part[2] else {}))
        return slot.get(part_slot[part[0]], fallback)

    parts = {}
    part_id = np.full((H, W), -1)
    for y, x in zip(*np.nonzero(solid)):
        part_id[y, x] = parts.setdefault(part_at(x, y), len(parts))
    # Specks of a part (a few 2x pixels: the 2x art's shading, not a shape) join the part round them,
    # at its height, so they neither stay square nor pin the edges round them to the art's steps.
    absorb_specks(part_id, height, solid, SPECK, tile=(TH, TW))
    part_mat = {i: mat_for(p) for p, i in parts.items()}
    # A pocket is its own part to boundary_moves, its corners fixed (its edges are straight already).
    main = solid & ~pocket
    part_id[pocket] = -1
    part_id[floor] = len(parts)
    pp = np.pad(pocket, 1)
    pocket_corners = pp[:-1, :-1] | pp[:-1, 1:] | pp[1:, :-1] | pp[1:, 1:]

    def mat_at(x, y):
        return part_mat[part_id[y, x]]

    frame = lt.Frame(cells, S)
    bm = bmesh.new()
    lt.mask_slab(bm, main, frame, BOTTOM, 0.0, mat_at, top_height=height, smooth_top=True, support=main)
    # The tubes and springs smooth-shaded, the rest flat; then only the flat parts merged (the underside,
    # the deck's plates): merging a tube's coplanar strips into long faces spoils its shading.
    # The deck's brackets too: rounded blocks, flat-shaded they read as pixel facets (D149).
    smooth_cells = tube | spring | np.isin(part_id, [i for p, i in parts.items() if p[0] == "bracket"])
    bm.normal_update()
    face_part = {}
    for f in bm.faces:
        f.smooth = False
        if f.normal.z > 0.2:
            c = f.calc_center_median()
            x = int((c.x / frame.unit) + frame.w / 2)
            y = int(frame.h / 2 - c.y / frame.unit)
            if 0 <= x < W and 0 <= y < H:
                f.smooth = bool(smooth_cells[y, x])
                face_part[f] = part_id[y, x]
    # Each part shades smooth within itself and creases where it meets another (a groove's lip, a
    # bracket's foot), so the carving reads crisp without per-pixel facets (D149).
    for e in bm.edges:
        fs = e.link_faces
        if len(fs) == 2 and fs[0] in face_part and fs[1] in face_part and face_part[fs[0]] != face_part[fs[1]]:
            e.smooth = False
    # The outline and the edges between parts follow the art's pixel steps: move them onto smooth
    # curves through the steps (D149), the tile edges pinned so neighbours still meet.
    o_sigma, o_grow = OUTLINE.get(n, OUTLINE_DEFAULT) if not block_kind else OUTLINE_DEFAULT
    dx, dy = kit.boundary_moves(part_id, sigma=EDGE_SIGMA, outline_sigma=o_sigma, outline_grow=o_grow,
                                pin_x=range(0, W + 1, TW), pin_y=range(0, H + 1, TH), pin_solid=solid,
                                keep=pocket_corners)
    kit.move_grid_verts(bm, frame, dx, dy)
    if floor.any():
        add_machined(ts, bm, frame, mats, centre, art1, floor, solid, pocket_kind, bars, bar_cells, face, depth)
    _debug_dump(name + "-parts", part_id=part_id, dx=dx, dy=dy, height=height, solid=solid)
    kit.tidy_flat(bm, angle=FLAT_MERGE)
    glow = {slot["red"]} if "red" in slot else set()
    # The maps come from the height field (lib_delbld.field_bake): roughness and metalness per part.
    rough = np.full((H, W), HULL["roughness"])
    metal = np.full((H, W), HULL["metallic"])
    shiny = (cls == "grey")
    rough[shiny], metal[shiny] = 0.35, 0.2
    rough[cls == "blue"], metal[cls == "blue"] = 0.3, 0.2
    # The bake's field follows the moved edges too (4 samples per cell), so its occlusion has no steps.
    k = 4
    f_solid, f_rough, f_metal, f_height = kit.warp_cells((solid, rough, metal), dx, dy, k,
                                                         corners=kit.corner_heights(height, solid))
    field = dict(height=f_height, solid=f_solid, rough=f_rough, metal=f_metal, scale=S * k)
    return kit.finish(ts, coll, name, bm, mats, LAYER, bake_on=bake_on, skip_slots=glow, field=field, cols=PC, rows=PR)


def _debug_dump(name, **arrays):
    """DELBLD_DEBUG=<dir>: the block's arrays (height field, parts) as <dir>/<name>.npz, to look at what
    the art became."""
    import os
    out = os.environ.get("DELBLD_DEBUG")
    if out:
        np.savez(f"{out}/{name}.npz", **{k: np.asarray(v, dtype=float if v.dtype == object else v.dtype) if v.dtype != object else np.zeros(v.shape) for k, v in arrays.items()})


def main():
    ts = lt.Tileset(ROOT, SHAPES, layer=LAYER)
    only, bake_on = kit.build_args()
    preview = lt.preview_arg()
    coll = common.reset_collection("delbld_hull")
    jobs = [(f"delbld-hull-{n}", [[n]], None) for n in TILES]
    for name, pattern, kind in jobs:
        if only and not (set(t for row in pattern for t in row) & only):
            continue
        obj = build(ts, pattern, name, coll, bake_on, block_kind=kind)
        kit.export(ts, [obj], name, LAYER, pattern, image_format="WEBP" if bake_on else "AUTO")
        if preview:
            lt.preview(ts, [obj], pattern, Path(preview) / f"{SHAPES}-{name}.png", view_px=240)


main()
