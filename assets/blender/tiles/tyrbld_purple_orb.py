"""The purple carved block with the blue orb on TYRIAN's islands (map 1-9, layer 2; 3x3 tiles
155/156/157, 165/149/167, 175/176/177), after the concept assets/blender/features/concepts/
tyr-purple-orb.jpg: a carved purple stone plate with chamfered corners, quartered by grooves into
four raised panels, a carved ring round a brass ring holding a glowing blue orb in the middle and
two blue capsule lights below it, eight faceted cracked-stone bosses round its edge (corners and
side middles) on a low purple base, on the island's rock.

Every cell carries a top enemy (newsh2 279/281/283, 245/169/207, 273/275/277: the "purple eye
fortress"), so the whole model stays under L2_ENEMY_MAX (0.33) and shows only after kills. The
tiles are shared by every purple shape; the plan's minRows 2 tells it apart. It replaces its
tiles, so it carries the rock they paint: the slab from Structure.rock, and boulders built here
the way the per-tile models build theirs (lib_tiles.boulders), with the stones of the rock tiles
round its first copy continued across the edge, so the cobbles join the neighbouring islands'.
Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_purple_orb.py
    python tools/concept_maps.py tile:shapesz-tyrbld-purple-orb --concept tyr-purple-orb --span -0.19,-0.07,2.38,2.09 --px 32
    python assets/blender/tiles/tyrbld_purple_orb.py --maps
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-purple-orb

The span is fractional: the Gemini concept is squeezed vertically against the tiles (its bosses at
pattern y 14/38/61.5 against the art's 11.5/40/68), so it is stretched back onto the art.

`--maps` (plain Python, after concept_maps) edits the concept maps: the rock round the block gets
no concept detail (the per-tile rock models next to it are untextured, and the concept paints
darker, rougher ground than they show), and the block's own carving gets more contrast so the
panels, the ring and the frame read from the game camera.
"""

import math
import sys
from pathlib import Path

import numpy as np

# Pattern pixels (1x, 72 x 84), read off the tile art (and the registered concept).
PLATE = (12.0, 15.0, 61.0, 63.0)  # the carved plate's box (x0, y0, x1, y1)
PLATE_CUT = 8.0  # its corners chamfered this much (where the corner bosses sit)
BASE = (11.5, 11.0, 61.5, 68.5)  # the low purple base under plate and bosses (through their centres)
BASE_CUT = 4.0
GROOVE_X, GROOVE_Y = 36.5, 38.5  # the grooves quartering it (through the orb)
ORB = (36.5, 38.5)
ORB_R = 6.5
RING_R = (10.3, 7.6)  # the brass ring's outer and inner radius
CARVED_R = (15.5, 13.6)  # the carved ring round it on the panels
CAPSULES = [((29.0, 47.0), -0.7), ((44.0, 47.5), 0.7)]  # centre, angle (radians, screen)
BOSSES = [  # cx, cy, rx, ry: the round stones at the corners and side middles
    (12.0, 11.5, 9.0, 8.0), (36.5, 11.0, 8.5, 7.5), (60.5, 11.5, 9.0, 8.0),
    (11.5, 40.0, 8.5, 8.5), (61.0, 40.0, 8.5, 8.5),
    (12.0, 68.5, 9.0, 8.5), (36.5, 68.5, 9.0, 8.5), (60.5, 68.5, 9.0, 8.5),
]

BASE_Z = (0.035, 0.07)  # purple base: chamfer foot, top
PLATE_EDGE_Z = 0.10  # the plate's chamfer
PLATE_Z = 0.145  # its frame (and the grooves between the panels)
PANEL_Z = (0.185, 0.22)  # the four raised panels: bevel foot, top
CARVED_Z = 0.232
RING_Z = (PANEL_Z[1] - 0.01, 0.255)
BOSS_Z = (0.0, 0.31)  # bosses: from the rock up to their crown
ORB_Z = (0.235, 0.325)
CAPSULE_Z = (0.21, 0.27)

ENTRY = "shapesz-tyrbld-purple-orb"
#: Per-tile rock models next to the first copy (map rows 364-368, cols 2-6, layer 2): pattern
#: cell -> tile. The row above is walkway (180), so no stones continue from there.
NEIGHBOURS = {(1, -1): 131, (2, -1): 131, (0, 3): 151, (1, 3): 131, (2, 3): 131,
              (3, 0): 131, (3, 1): 131, (3, 2): 131}
ROCK_TILES = {120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 150, 151, 152}  # shapesz_bg3 plain rock


def octagon(x0, y0, x1, y1, cut):
    """The corners (px, clockwise on screen) of a box with its corners cut by `cut`."""
    return [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1 - cut), (x1 - cut, y1), (x0 + cut, y1), (x0, y1 - cut), (x0, y0 + cut)]


def inside_poly(p, poly):
    """p inside (or on) the convex polygon poly."""
    n = len(poly)
    sgn = 0
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        c = (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)
        if abs(c) < 1e-6:
            continue
        if sgn == 0:
            sgn = 1 if c > 0 else -1
        elif (c > 0) != (sgn > 0):
            return False
    return True


def poly_mask(poly, h, w, scale=1.0):
    """Bool mask (h x w, `scale` texels per px) of a convex polygon in px."""
    yy, xx = (np.mgrid[0:h, 0:w] + 0.5) / scale
    m = np.ones((h, w), bool)
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        side = lambda x, y: (bx - ax) * (y - ay) - (by - ay) * (x - ax)  # noqa: E731
        m &= np.sign(side(xx, yy)) * np.sign(side(cx, cy)) >= 0
    return m


def block_mask(h, w, scale=1.0, grow=0.0):
    """Where the block stands (base, plate and bosses), grown by `grow` px."""
    x0, y0, x1, y1 = BASE
    m = poly_mask(octagon(x0 - grow, y0 - grow, x1 + grow, y1 + grow, BASE_CUT), h, w, scale)
    yy, xx = (np.mgrid[0:h, 0:w] + 0.5) / scale
    for cx, cy, rx, ry in BOSSES:
        m |= ((xx - cx) / (rx + grow)) ** 2 + ((yy - cy) / (ry + grow)) ** 2 <= 1
    return m


def maps():
    """Edit the concept maps (see the module's docstring)."""
    from PIL import Image
    from scipy import ndimage

    root = Path(__file__).resolve().parents[3]
    d = root / "assets/blender/textures" / ENTRY
    det = np.asarray(Image.open(d / "detail.png")).astype(np.float32) / 255
    hgt = np.asarray(Image.open(d / "height.png")).astype(np.float32) / 255
    h, w = det.shape[:2]
    scale = w / 72.0
    # The block's weight: 1 on it, fading to 0 over about a pixel round it (worked out at 1/4 size).
    q = 4
    small = block_mask(h // q, w // q, scale / q, grow=0.6).astype(np.float32)
    small = ndimage.gaussian_filter(small, scale / q * 0.6)
    wgt = np.clip(ndimage.zoom(small, (h / small.shape[0], w / small.shape[1]), order=1), 0, 1)[:h, :w]
    if det.ndim == 3:
        wgt3 = wgt[..., None]
    else:
        wgt3 = wgt
    neutral = 0.85
    det_block = np.clip(neutral + (det - neutral) * 1.5, 0, 1)
    det = det_block * wgt3 + 1.0 * (1 - wgt3)
    hgt_block = np.clip(0.5 + (hgt - 0.5) * 1.6, 0, 1)
    hw = wgt3 if hgt.ndim == det.ndim else wgt
    hgt = hgt_block * hw + 0.5 * (1 - hw)
    Image.fromarray((det * 255 + 0.5).astype(np.uint8)).save(d / "detail.png")
    Image.fromarray((hgt * 255 + 0.5).astype(np.uint8)).save(d / "height.png")
    print(f"{ENTRY}: detail and height edited ({w}x{h}); rock neutral, block contrast up")


if __name__ == "__main__" and "--maps" in sys.argv:
    maps()
    sys.exit(0)

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402


def offset_poly(poly, d):
    """A convex polygon's outline moved inward by d px (each edge offset, corners re-intersected)."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    lines = []
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        ln = math.hypot(ex, ey)
        nx, ny = -ey / ln, ex / ln
        if nx * (cx - ax) + ny * (cy - ay) < 0:
            nx, ny = -nx, -ny
        lines.append(((ax + nx * d, ay + ny * d), (ex, ey)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def slab(s, poly, z0, z1, chamfer_px, chamfer_z, top_mat, side_mat):
    """A carved slab: the convex outline `poly` (px) from z0 up to chamfer_z, then a chamfer
    `chamfer_px` wide up to the flat top at z1. Smooth diagonals, unlike the terraced deck."""
    bm = bmesh.new()
    inner = offset_poly(poly, chamfer_px)
    bot = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in poly]
    mid = [bm.verts.new((s.x(x), s.y(y), chamfer_z)) for x, y in poly]
    top = [bm.verts.new((s.x(x), s.y(y), z1)) for x, y in inner]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], mid[j], mid[i])).material_index = side_mat
        bm.faces.new((mid[i], mid[j], top[j], top[i])).material_index = side_mat
    bm.faces.new(top).material_index = top_mat
    bm.faces.new(list(reversed(bot))).material_index = side_mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def capsule(s, px, py, angle, mat):
    """A small glowing pill lying on the plate, turned by `angle` (a dome, elongated)."""
    bm = bmesh.new()
    lt.dome(bm, s.x(px), s.y(py), 3.2 * lt.PX, 1.7 * lt.PX, angle, CAPSULE_Z[0], CAPSULE_Z[1] - CAPSULE_Z[0], mat, sides=12, rings=3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=True)


def boss(s, cx, cy, rx, ry, mat):
    """A faceted boss: an octagonal dome in two flat-shaded rings, flat crowned (the original's
    panelled knobs, the concept's cracked-plate domes; the bake adds the cracks)."""
    bm = bmesh.new()
    lt.dome(bm, s.x(cx), s.y(cy), rx * lt.PX, ry * lt.PX, math.pi / 8, BOSS_Z[0], BOSS_Z[1] - BOSS_Z[0], mat,
            sides=8, rings=2, squash=0.45)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=False)


# Rock ------------------------------------------------------------------------------------------

GAP, SIGMA, MIN_PX, QUANTILE = 0.22, 2.2, 8, 0.3  # as lib_tiles.boulders / shapesz_bg3
STONE_RAMPS = (0x0, 0xA)  # grey and tan
ROCK_MAT = {"roughness": 0.55, "metallic": 0.05}  # shapesz_bg3's palette materials


def rock_slab(s):
    """The island's slab under the whole pattern, -0.30 to 0, in the dark the rock tiles round it
    paint between their stones (Structure.rock would take the purple's dark outline)."""
    own = s.ts.grid([[131]], 2)
    lum = lt.lum_of(s.ts, own)
    dark = lt.dominant(own[(own >= 0) & (lum <= GAP)], prefer="mode")
    DARK = s.pal(3 if dark is None else dark, **ROCK_MAT)
    g2 = s.ts.grid(s.pattern, 2)
    bm = bmesh.new()
    lt.mask_slab(bm, g2 >= 0, lt.Frame(s.pattern, 2), s.slab_bottom, 0.0, DARK, DARK)
    lt.dissolve_coplanar(bm)
    s._merge(bm)


def stone(s, bm, ys, xs, oy, ox, grid, chosen):
    """A boulder for the blob (ys, xs) of `grid` (2x px), placed with grid pixel (oy, ox) at the
    pattern's top-left, as lib_tiles.boulders builds it."""
    cx, cy, rx, ry, ang = lt.ellipse(ys, xs)
    rx, ry = (rx + 0.6) / 24, (ry + 0.6) / 24
    height = min(0.2, 0.55 * min(rx, ry) + 0.02)
    colour = lt.snap_shade(lt.dominant(grid[ys, xs], s.ts.lum, quantile=QUANTILE), chosen)
    lt.dome(bm, s.x((cx - ox) / 2), s.y((cy - oy) / 2), rx, ry, -ang, -0.03, height, s.pal(colour, **ROCK_MAT),
            sides=10, rings=3, squash=0.2)


def rock_boulders(s, exclude):
    """The boulders on the block's tiles: the stones of the per-tile rock models next to it that
    cross into it (whole, so each joins its other half), then the tiles' own stones (found with
    the real neighbours round them) where those leave room and the block doesn't stand."""
    th, tw = lt.TILE_H * 2, lt.TILE_W * 2
    H2, W2 = s.H * 2, s.W * 2
    ex2 = np.kron(exclude, np.ones((2, 2), bool))
    taken = np.zeros((H2, W2), bool)
    chosen = []
    bm = bmesh.new()

    # 1. The neighbours' stones that run over the edge (each neighbour finds its stones between its
    #    usual neighbours, lib_tiles.context, so do the same here).
    for (nr, nc), n in NEIGHBOURS.items():
        ctx = lt.context(s.ts, n)
        grid = s.ts.grid(ctx, 2)
        lum = lt.lum_of(s.ts, grid)
        for ys, xs in lt.hills(lum, grid >= 0, sigma=SIGMA, floor=GAP):
            if len(ys) < MIN_PX:
                continue
            if not ((ys >= th) & (ys < 2 * th) & (xs >= tw) & (xs < 2 * tw)).any():
                continue  # not the neighbour's own stone
            py = ys - th + nr * th  # pattern 2x px
            px = xs - tw + nc * tw
            ins = (py >= 0) & (py < H2) & (px >= 0) & (px < W2)
            if not ins.any():
                continue
            taken[py[ins], px[ins]] = True
            stone(s, bm, ys, xs, th - nr * th, tw - nc * tw, grid, chosen)

    # 2. The tiles' own stones, between their real neighbours (first copy).
    rows, cols = len(s.pattern), len(s.pattern[0])
    padded = [[-1] * (cols + 2) for _ in range(rows + 2)]
    for r in range(rows):
        for c in range(cols):
            padded[r + 1][c + 1] = s.pattern[r][c]
    for (nr, nc), n in NEIGHBOURS.items():
        padded[nr + 1][nc + 1] = n if n in ROCK_TILES else -1
    grid = s.ts.grid(padded, 2)
    lum = lt.lum_of(s.ts, grid)
    # Only the grey and tan stones climb to a peak; the purple block's bright pixels are not stones.
    lum = np.where(np.isin(np.maximum(grid, 0) >> 4, STONE_RAMPS) & (grid >= 0), lum, 0.0)
    taken_g = np.zeros(grid.shape, bool)
    taken_g[th:th + H2, tw:tw + W2] = taken | ex2
    for ys, xs in lt.hills(lum, grid >= 0, sigma=SIGMA, floor=GAP):
        if len(ys) < 2 * MIN_PX:
            continue  # slivers of stone next to the block's outline: no specks
        ins = (ys >= th) & (ys < th + H2) & (xs >= tw) & (xs < tw + W2)
        if ins.mean() < 0.5:
            continue  # mostly a neighbour's stone
        if taken_g[ys[ins], xs[ins]].mean() > 0.35:
            continue  # under the block, or where a neighbour's stone runs in
        stone(s, bm, ys, xs, th, tw, grid, chosen)

    lt.cut_to_tile(bm, cols=cols, rows=rows)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def build():
    s = tb.Structure("purple-orb")
    purple = s.purple_mask()
    base_mat = s.m(s.dominant(purple & lb.erode(purple, 1), prefer="mode") or tb.PAL_T["purple_dark"], roughness=0.65)
    plate_mat, edge_mat = s.m("purple"), s.m("purple_dark")
    panel_mat = s.m("purple_light")

    # The low purple base the plate and the bosses stand on: straight chamfered edges.
    slab(s, octagon(*BASE, BASE_CUT), -0.02, BASE_Z[1], 1.5, BASE_Z[0], base_mat, edge_mat)

    # The carved plate: chamfered outline, a frame round four raised bevelled panels with a groove
    # cross between them through the orb (the frame's meanders and the panels' carving come from
    # the bake).
    x0, y0, x1, y1 = PLATE
    slab(s, octagon(*PLATE, PLATE_CUT), BASE_Z[1] - 0.02, PLATE_Z, 2.5, PLATE_EDGE_Z, plate_mat, edge_mat)
    inset, gap = 4.0, 2.0
    frame = octagon(x0 + inset, y0 + inset, x1 - inset, y1 - inset, PLATE_CUT - 1.5)
    for qx0, qx1 in ((x0 + inset, GROOVE_X - gap), (GROOVE_X + gap, x1 - inset)):
        for qy0, qy1 in ((y0 + inset, GROOVE_Y - gap), (GROOVE_Y + gap, y1 - inset)):
            corner = [p for p in frame if qx0 - 1e-6 <= p[0] <= qx1 + 1e-6 and qy0 - 1e-6 <= p[1] <= qy1 + 1e-6]
            pts = corner + [(qx0, qy0), (qx1, qy0), (qx1, qy1), (qx0, qy1)]
            pts = [p for p in pts if (p in corner) or inside_poly(p, frame)]
            cxm = sum(p[0] for p in pts) / len(pts)
            cym = sum(p[1] for p in pts) / len(pts)
            pts = sorted(set(pts), key=lambda p: math.atan2(p[1] - cym, p[0] - cxm))
            slab(s, pts, PLATE_Z - 0.01, PANEL_Z[1], 1.6, PANEL_Z[0], panel_mat, plate_mat)

    # The carved ring round the orb, standing on the panels and across the grooves.
    co, ci = CARVED_R
    ch = (CARVED_Z - PLATE_Z) / lt.PX
    s.lathe([(0.0, co), (ch * 0.75, co), (ch, co - 0.6), (ch, ci + 0.6), (ch * 0.75, ci), (0.0, ci)],
            ORB[0], ORB[1], axis="z", z=PLATE_Z - 0.005, mats=[edge_mat, plate_mat, panel_mat, plate_mat, edge_mat],
            mat=edge_mat, sides=32, smooth=False)

    # The brass ring and the blue orb in it.
    ring_h = (RING_Z[1] - RING_Z[0]) / lt.PX
    outer, inner = RING_R
    s.lathe([(-0.3, outer), (ring_h * 0.7, outer), (ring_h, outer - 0.8), (ring_h, inner), (-0.3, inner)],
            ORB[0], ORB[1], axis="z", z=RING_Z[0], mats=[s.m("brass_dark"), s.m("brass"), s.m("brass_light"), s.m("dark")],
            mat=s.m("brass_dark"), sides=20, smooth=False)
    s.dome(ORB[0], ORB[1], inner + 0.3, inner + 0.3, ORB_Z[0] - 0.03, 0.03, s.m("dark"), sides=20, rings=1)
    s.light(ORB[0], ORB[1], ORB_R, ORB_Z[0], height=ORB_Z[1] - ORB_Z[0], kind="blue", sides=20)
    blue = s.m("blue")
    for (px, py), ang in CAPSULES:
        capsule(s, px, py, ang, blue)

    # The bosses: faceted cracked stones.
    for cx, cy, rx, ry in BOSSES:
        boss(s, cx, cy, rx, ry, plate_mat)

    # The island's rock round it: the slab, then boulders joined to the neighbours' (see above).
    rock_slab(s)
    keep_out = block_mask(s.H, s.W, grow=-0.5) | lb.erode(purple, 1)
    rock_boulders(s, keep_out)

    objects = s.objects()
    s.check(objects)
    s.export(objects)


build()
