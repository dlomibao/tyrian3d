"""newshe-233: the lava rock (newshe.shp 233), a cooling lava bomb.

What the sprite shows (reference/models/newshe-233, 24x28 block, palette 5, one frame):
- Plan: a lumpy ball, columns 4-19, rows 7-21 (16 x 15 px). The inner mask (D74) drops 12 ink
  pixels of the dark red ring on the top right; the rest of the edge is colour to the border.
- Crust: black (index 1, some 64) over most of the face, broken by thin dark red lines (112/113):
  the cracks between cooled plates. Its right flank is 112 (ember crust, the shaded side).
- The rim: a thin smouldering ring all round the outline, one pixel on the left, top and right
  (113-115), two to three on the bottom (115-118), opening on the lower right into a hot crescent
  (121-125 at columns 15-18, rows 15-20).
- The vent, up and left (columns 7-10, rows 10-13): a 4x4 glowing pit, 115/119 round its lip,
  120-124 inside, 126/127 white-hot at the core.
- Two small hot openings: below-right of the vent (column 12, rows 14-15: 118, 125) and right of
  it (row 11, column 13: 120).

Reading (rubric "Reading a sprite"): rock, so the bright pixels are hot material (emissive lava)
and the dark ones crust. Design (fix round 2): ONE closed, nearly round lumpy shell (height about
0.85 of the width), no loose plates, no flange. The ball is an icosphere mapped onto the plan; its
faces are labelled crust cells (Voronoi, the equator a cell boundary), the vent and two pits, and
the labels' boundaries are straightened. Then:
- the seam round the widest line is only a crack (the equator's cell boundary, sunk like the other
  cracks): the crust above and below it sits at the same radius. The sprite's rim ring is COLOUR:
  the crust plates in the band the top view sees as the outermost pixel ring (its width per angle
  from the sprite, one pixel round most of it, two to three at the bottom) take the rim's
  smouldering red; that band's edge is snapped to a smooth line;
- the verts on cell boundaries sink into V grooves and each cell is inset by a hair, the strips
  being the grooves' glowing walls: the lava shows only in the cracks;
- the hot crescent on the lower right is small crust cells (extra seeds on its hot pixels) with
  wide glowing gaps between them: cell-shaped openings, a little sunk, never whole flat faces;
- each crust cell is pressed towards its own plane (only inwards) and lifted along its normal on
  the upper half: a faceted, lumpy, matte rock with a broken upper outline; near the widest line
  the lift fades out, so nothing passes the plan;
- the vent is a modelled crater: one n-gon inset in rings that follow its outline, a sloped raised
  lip, crack walls going down, and the molten pool in concentric rings (120, 122, 124, 126 core)
  a little below the lip; the two small hot openings are the same in miniature (118/125, 115/120).
All lava, rim and crack materials show their own palette colour (metallic 1 / rough 1, glowing),
the crust is rough 0.93 / 0.9. Underside: the same shell, a few big cells, closed; no detail.

Run: Blender --background --factory-startup --python newshe-233.py [-- --out x.glb]
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

NAME = "newshe-233"
PX = 1 / 12
W, H = 24, 28

# --- tuning -----------------------------------------------------------------------------------
SUBDIV = 4           # icosphere subdivisions
CT, CB = 0.58, 0.52  # half height above / below the equator (units); the plan's radius is ~0.65
SHRINK = 0.000       # plan pulled in (units)
SEEDS_UP = 20        # crust cells over the upper half
SEEDS_UNDER = 7      # big cells under the equator (plausible closed shape only)
WAVE = 0.03          # the seam's wander up and down (units)
LUMP_Z = 0.07        # height lumps on the upper half (share of CT)
GROOVE = 0.020       # crack groove depth (units, along the normal)
GROOVE_W = 0.011     # crack groove wall width (each cell's inset)
FLAT = 0.65          # how far each crust cell is pressed onto its own plane (only inwards)
LIFT = 0.030         # max outward lift of a crust cell on top (lumps)
HOT_SINK = 0.030     # boundary verts of the hot cells sink this far (the gaps' floor)
VENT = (8.60, 11.50)  # vent centre (sprite pixel-index col, row)
VENT_R = 2.75        # vent radius (px)
# crater rings, outside in: (thickness (share of the crater radius), depth step (units, + up),
# palette index): a sloped lip rising from the crust, its top, the crack wall down, the pool rings
VENT_RINGS = [(0.07, 0.022, 115), (0.025, 0.0, 115), (0.04, -0.060, 117), (0.08, -0.003, 120),
              (0.10, -0.003, 122), (0.08, -0.002, 124)]
VENT_CORE = 126
PITS = [((12.0, 14.75), 0.95, [(0.16, 0.008, 118), (0.10, -0.020, 118), (0.12, -0.002, 122)], 125),
        ((13.15, 11.0), 0.80, [(0.16, 0.006, 115), (0.10, -0.016, 117), (0.15, -0.002, 120)], 122)]
REFINE = [(8.7, 11.6, 3.2), (12.0, 14.75, 1.7), (13.15, 11.0, 1.5), (16.3, 17.6, 2.8)]  # local subdivision (px)
HOT = 0.55           # heat above which a pixel is open lava
SEED = 233
SMOOTH_IT = 8
MIN_CELL = 5         # faces: smaller crust islands join their neighbour
EMBER_SHARE = 0.5
RING_MAX = 3         # rim pixels counted in from the edge
W_MIN, W_MAX = 0.75, 2.6  # rim width clamp (px) seen from the top
LOW_BAND = 0.16      # the smouldering band reaches this far below the equator (u.z)

# heat of each palette index: crust 0, ember lines dark, white-hot 1
HEAT = {1: 0.0, 64: 0.0, 112: 0.10, 113: 0.18, 114: 0.25, 115: 0.40, 116: 0.45, 117: 0.50,
        118: 0.58, 119: 0.62, 120: 0.68, 121: 0.74, 122: 0.80, 123: 0.84, 124: 0.90, 125: 0.93,
        126: 0.97, 127: 1.0}
# lava colour bins: (heat upper bound, palette index)
BINS = [(0.30, 113), (0.55, 115), (0.64, 117), (0.74, 119), (0.88, 122), (9.0, 126)]

# face labels
VENT_L = 200000      # the vent crater
PIT_L = 300000       # + pit index


def load():
    sprite = common.load_sprite(WT, NAME)
    pix = sprite["frames"][0]["pixels"]
    return sprite, pix


def inner_mask():
    """The inner mask (tools/sprite_mask.py newshe-233 --json): what the top view must cover."""
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as SM  # noqa: E402
    idx, colors = SM.load(NAME)[:2]
    m = SM.masks(idx, colors)
    inner = m["inner"] if isinstance(m, dict) else m[2]
    return [[bool(v) for v in r] for r in inner]


def ring_pixels(pix):
    """The smouldering rim: pixels >= 113 reached from the outside within RING_MAX steps, through
    pixels >= 113 only (the crust and its 112 ember lines stop it)."""
    hot = [[v >= 113 for v in r] for r in pix]

    def edge(y, x):
        return any(not (0 <= yy < H and 0 <= xx < W) or pix[yy][xx] < 0
                   for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)))
    ring = {(y, x): 1 for y in range(H) for x in range(W) if pix[y][x] >= 0 and hot[y][x] and edge(y, x)}
    front = list(ring)
    for d in range(2, RING_MAX + 1):
        nxt = []
        for y, x in front:
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < H and 0 <= xx < W and hot[yy][xx] and (yy, xx) not in ring:
                    ring[(yy, xx)] = d
                    nxt.append((yy, xx))
        front = nxt
    return ring


def heat_grid(pix, ring):
    """Per-pixel heat of the crust cap: rim pixels count as crust (the belt shows them) unless
    they're hot lava (the lower-right crescent); transparent pixels from the nearest opaque one."""
    g = [[None if v < 0 else (HEAT.get(v, 0.0) if (y, x) not in ring or HEAT.get(v, 0) >= 0.58 else 0.0)
          for x, v in enumerate(r)] for y, r in enumerate(pix)]
    for _ in range(4):
        n = [r[:] for r in g]
        for y in range(H):
            for x in range(W):
                if g[y][x] is None:
                    vals = [g[yy][xx] for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
                            if 0 <= yy < H and 0 <= xx < W and g[yy][xx] is not None]
                    if vals:
                        n[y][x] = sum(vals) / len(vals)
        g = n
    return [[0.0 if v is None else v for v in r] for r in g]


def sample(g, c, r):
    """Bilinear heat at sprite position (column, row) in pixel units (pixel centres at +0.5)."""
    x, y = c - 0.5, r - 0.5
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0

    def at(xx, yy):
        return g[min(H - 1, max(0, yy))][min(W - 1, max(0, xx))]
    return ((at(x0, y0) * (1 - fx) + at(x0 + 1, y0) * fx) * (1 - fy)
            + (at(x0, y0 + 1) * (1 - fx) + at(x0 + 1, y0 + 1) * fx) * fy)


def plan_radius(mask):
    """The inner mask's edge as a radius per degree round its centroid (px), smoothed."""
    pts = [(x + 0.5, y + 0.5) for y in range(H) for x in range(W) if mask[y][x]]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)

    def inside(c, r):
        xi, yi = math.floor(c), math.floor(r)
        return 0 <= yi < H and 0 <= xi < W and mask[yi][xi]
    raw = []
    for k in range(360):
        a = math.radians(k)
        d = 0.0
        while inside(cx + (d + 0.02) * math.cos(a), cy - (d + 0.02) * math.sin(a)):
            d += 0.02
        raw.append(d)
    # circular smoothing: the pixel staircase becomes the curve through its corners' middles
    sm = []
    for k in range(360):
        ws = [(j, math.exp(-0.5 * (j / 7.0) ** 2)) for j in range(-18, 19)]
        sm.append(sum(raw[(k + j) % 360] * w for j, w in ws) / sum(w for _, w in ws))
    return cx, cy, sm


def rad_at(sm, a):
    d = math.degrees(a) % 360
    k = int(d)
    f = d - k
    return sm[k] * (1 - f) + sm[(k + 1) % 360] * f


def noise3(p, seed=0):
    """A cheap smooth noise from a few sines (no textures, deterministic)."""
    x, y, z = p
    return (math.sin(3.1 * x + 1.7 * y + 0.3 + seed) * math.cos(2.3 * y - 1.1 * z + seed * 0.7)
            + 0.6 * math.sin(5.3 * z + 2.9 * x - seed) * math.cos(4.1 * x + 3.3 * y + 1.1)) / 1.6


def bin_of(h):
    return next(idx for top, idx in BINS if h < top)


def build(coll, sprite, pix):
    mask = inner_mask()
    ring = ring_pixels(pix)
    g = heat_grid(pix, ring)
    pcx, pcy, sm = plan_radius(mask)
    ox, oy = (pcx - W / 2) * PX, (H / 2 - pcy) * PX     # plan centre in Blender units

    # rim width per degree (px): ring pixels met marching in from the edge, smoothed
    raw_w = []
    for k in range(360):
        a = math.radians(k)
        d, n = 0.15, 0
        while d < RING_MAX + 1:
            c, r = pcx + (sm[k] - d) * math.cos(a), pcy - (sm[k] - d) * math.sin(a)
            if (int(r), int(c)) in ring:
                n += 1
            elif n:
                break
            d += 0.25
        raw_w.append(n * 0.25)
    ker = [(j, math.exp(-0.5 * (j / 8.0) ** 2)) for j in range(-24, 25)]
    WR = [min(W_MAX, max(W_MIN, sum(raw_w[(k + j) % 360] * w for j, w in ker) / sum(w for _, w in ker)))
          for k in range(360)]

    # the rim's heat per degree: the outermost rim pixel met marching in, smoothed round the rim
    raw_h = []
    for k in range(360):
        a = math.radians(k)
        d, h = 0.15, None
        while d < 3 and h is None:
            c, r = pcx + (sm[k] - d) * math.cos(a), pcy - (sm[k] - d) * math.sin(a)
            v = pix[min(H - 1, max(0, int(r)))][min(W - 1, max(0, int(c)))]
            if v >= 0:
                h = HEAT.get(v, 0.0) if (int(r), int(c)) in ring else 0.18
            d += 0.25
        raw_h.append(0.18 if h is None else h)
    ker5 = [(j, math.exp(-0.5 * (j / 3.0) ** 2)) for j in range(-9, 10)]
    RH = [sum(raw_h[(k + j) % 360] * w for j, w in ker5) / sum(w for _, w in ker5) for k in range(360)]

    vc, vr = VENT

    def vent_d(c, r):
        """Distance from the vent centre (pixel-index coords), a little irregular."""
        t = math.atan2(r - vr, c - vc)
        return math.hypot(c - vc, (r - vr) * 1.1) / (1 + 0.03 * math.sin(3 * t + 1.0))

    def pos(u):
        """Unit-sphere point u on the ball: a near-round lumpy ball over the plan."""
        a = math.atan2(u.y, u.x)
        rp = rad_at(sm, a) * PX - SHRINK
        zz = max(-1.0, min(1.0, u.z))
        hh = math.sqrt(max(0.0, 1 - zz * zz))
        up = max(0.0, zz)
        z = (CT if zz >= 0 else CB) * zz
        z *= 1 + LUMP_Z * noise3(u * 1.6, 1.3) * up ** 1.5          # lumps on the upper outline
        z += WAVE * (0.6 * math.sin(2 * a + 0.7) + 0.4 * math.sin(3 * a - 1.2)) * (1 - abs(zz)) ** 2
        rh = rp * hh * (1 - 0.05 * (0.5 + 0.5 * noise3(u * 1.8, 5.0)) * up * up)   # only inwards
        return Vector((ox + rh * math.cos(a), oy + rh * math.sin(a), z))

    def cr(p):
        """Sprite pixel-index coords (col, row) of a point's top-view position."""
        return p.x / PX + W / 2 - 0.5, H / 2 - p.y / PX - 0.5

    def u_of(c, r):
        """The upper-half unit-sphere point whose top view is sprite pixel (col, row)."""
        x, y = c + 0.5 - pcx, -(r + 0.5 - pcy)
        a = math.atan2(y, x)
        hh = min(0.97, math.hypot(x, y) / rad_at(sm, a))
        return Vector((hh * math.cos(a), hh * math.sin(a), math.sqrt(1 - hh * hh)))

    def zb(a):
        """Top edge of the rim band (u.z): the top view sees the band as the sprite's rim width
        the edge wandering a little like a crack."""
        wob = 0.8 + 0.15 * math.sin(5 * a + 0.9) + 0.1 * math.sin(9 * a - 0.4)
        hb = max(0.35, 1 - rad_at(WR, a) * wob / rad_at(sm, a))
        return math.sqrt(1 - hb * hb)

    def zl(a):
        return -(LOW_BAND + 0.05 * math.sin(3 * a + 0.4))

    # --- the sphere, finer where the small hot features sit ---------------------------------
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=SUBDIV, radius=1.0)
    for v in bm.verts:
        v.co.normalize()
    for it in range(2):
        sel = set()
        for f in bm.faces:
            u = f.calc_center_median().normalized()
            if u.z <= 0:
                continue
            c, r = cr(pos(u))
            if any(math.hypot(c - fc, r - fr) < fr_ for fc, fr, fr_ in (REFINE if it < 1 else REFINE[:3])):
                sel.add(f)
        edges = list({e for f in sel for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        for v in bm.verts:
            v.co.normalize()
    # the equator, exact: the seam crack between the upper and lower cells
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                           plane_co=(0, 0, 0), plane_no=(0, 0, 1))
    fixed = set()
    for v in bm.verts:
        if abs(v.co.z) < 1e-6:
            xy = Vector((v.co.x, v.co.y)).normalized()
            v.co = Vector((xy.x, xy.y, 0.0))
            fixed.add(v.index)
        else:
            v.co.normalize()
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    unit = [v.co.copy() for v in bm.verts]

    # --- crust cell seeds ----------------------------------------------------------------------
    rnd = random.Random(SEED)
    gold = math.pi * (3 - math.sqrt(5))
    seeds = []
    for i in range(SEEDS_UP):        # Fibonacci over the upper half
        z = 1 - (i + 0.5) / SEEDS_UP
        rr = math.sqrt(max(0.0, 1 - z * z))
        sd = Vector((rr * math.cos(gold * i), rr * math.sin(gold * i), z))
        sd += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.12
        seeds.append(sd.normalized())
    # the hot crescent: one small cell per hot pixel, so its glow comes through as gaps
    for y in range(H):
        for x in range(W):
            v = pix[y][x]
            if v >= 0 and HEAT.get(v, 0) >= 0.58 and vent_d(x, y) > 3.2 \
                    and all(math.hypot(x - pc, y - pr) > rad + 0.8 for (pc, pr), rad, _, _ in PITS):
                seeds.append(u_of(x, y))
    NU = len(seeds)
    under = [Vector((math.cos(a), math.sin(a), -0.5)).normalized() for a in
             (i * 2 * math.pi / (SEEDS_UNDER - 1) + 0.3 for i in range(SEEDS_UNDER - 1))] + [Vector((0, 0, -1))]

    def is_crust(lab_):
        return 0 <= lab_ < VENT_L

    # --- labels --------------------------------------------------------------------------------
    label = {}
    for f in bm.faces:
        u = (sum((unit[v.index] for v in f.verts), Vector()) / len(f.verts)).normalized()
        if u.z < 0:
            wn = u + Vector((noise3(u * 2.0, 4.0), noise3(u * 2.0, 7.0), noise3(u * 2.0, 9.0))) * 0.10
            label[f.index] = NU + max(range(len(under)), key=lambda k: wn.dot(under[k]))
            continue
        c, r = cr(pos(u))
        if vent_d(c, r) < VENT_R:
            label[f.index] = VENT_L
            continue
        pit = next((k for k, ((pc, pr), rad, _, _) in enumerate(PITS) if math.hypot(c - pc, r - pr) < rad), None)
        if pit is not None:
            label[f.index] = PIT_L + pit
            continue
        wn = u + Vector((noise3(u * 2.0, 4.0), noise3(u * 2.0, 7.0), noise3(u * 2.0, 9.0))) * 0.05
        label[f.index] = max(range(NU), key=lambda k: wn.dot(seeds[k]) + (0.004 if k >= SEEDS_UP else 0))

    def islands(fs_):
        fs = set(fs_)
        out = []
        while fs:
            st = [fs.pop()]
            isl = [st[0]]
            while st:
                f = st.pop()
                for e in f.edges:
                    for o in e.link_faces:
                        if o in fs:
                            fs.remove(o)
                            st.append(o)
                            isl.append(o)
            out.append(isl)
        return out

    # tidy: small crust islands join the crust label round them (never across the equator)
    for _ in range(2):
        groups = {}
        for f in bm.faces:
            groups.setdefault(label[f.index], []).append(f)
        for lab_, fs in groups.items():
            if not is_crust(lab_):
                continue
            for isl in islands(fs):
                if len(isl) >= MIN_CELL:
                    continue
                side = lab_ < NU
                nb = [label[o.index] for f in isl for e in f.edges for o in e.link_faces
                      if label[o.index] != lab_ and is_crust(label[o.index]) and (label[o.index] < NU) == side]
                if nb:
                    best = max(set(nb), key=nb.count)
                    for f in isl:
                        label[f.index] = best
    # every crust island its own cell
    groups = {}
    for f in bm.faces:
        groups.setdefault(label[f.index], []).append(f)
    nxt = 0
    upper_cell = {}
    for lab_, fs in sorted(groups.items(), key=lambda kv: kv[0]):
        if not is_crust(lab_):
            continue
        for isl in islands(fs):
            for f in isl:
                label[f.index] = nxt
            upper_cell[nxt] = lab_ < NU
            nxt += 1

    # straighten the zigzag boundaries between labels (on the unit sphere)
    for _ in range(SMOOTH_IT):
        moves = {}
        for v in bm.verts:
            if len({label[f.index] for f in v.link_faces}) != 2:
                continue
            nbs = [e.other_vert(v) for e in v.link_edges
                   if len({label[f.index] for f in e.link_faces}) == 2]
            if len(nbs) != 2:
                continue
            mid = (unit[nbs[0].index] + unit[nbs[1].index]) * 0.5
            if v.index not in fixed:
                moves[v.index] = (unit[v.index] * 0.5 + mid * 0.5).normalized()
        for i, u in moves.items():
            unit[i] = u
        rel = {}
        for v in bm.verts:
            if len({label[f.index] for f in v.link_faces}) == 1:
                nb = sum((unit[e.other_vert(v).index] for e in v.link_edges), Vector()) / len(v.link_edges)
                if v.index not in fixed:
                    rel[v.index] = (unit[v.index] * 0.6 + nb * 0.4).normalized()
        for i, u in rel.items():
            unit[i] = u

    # --- the rim band: colour only, its edges snapped onto smooth lines ------------------------
    def fu(f):
        return (sum((unit[v.index] for v in f.verts), Vector()) / len(f.verts)).normalized()
    band = {}
    for f in bm.faces:
        u = fu(f)
        a = math.atan2(u.y, u.x)
        band[f.index] = 0 if not is_crust(label[f.index]) else (
            1 if 0 <= u.z < zb(a) else 2 if zl(a) < u.z < 0 else 0)
    for _ in range(2):   # lone faces follow their neighbours
        for f in bm.faces:
            if not is_crust(label[f.index]):
                continue
            nb = [band[o.index] for e in f.edges for o in e.link_faces if o is not f]
            if nb.count(band[f.index]) == 0:
                band[f.index] = max(set(nb), key=nb.count)
    for v in bm.verts:
        if v.index in fixed:
            continue
        bs = {band[f.index] for f in v.link_faces}
        u = unit[v.index]
        a = math.atan2(u.y, u.x)
        if bs == {0, 1}:
            z = zb(a)
        elif bs == {0, 2}:
            z = zl(a)
        else:
            continue
        xy = Vector((u.x, u.y)).normalized() * math.sqrt(1 - z * z)
        unit[v.index] = Vector((xy.x, xy.y, z))

    # the band's edges are cracks too: each crust cell splits there into its own plates
    groups = {}
    for f in bm.faces:
        if is_crust(label[f.index]):
            groups.setdefault((label[f.index], band[f.index]), []).append(f)
    nxt = 0
    up_ = {}
    for key, fs in sorted(groups.items(), key=lambda kv: kv[0]):
        for isl in islands(fs):
            for f in isl:
                label[f.index] = nxt
            up_[nxt] = upper_cell[key[0]]
            nxt += 1
    upper_cell = up_

    # --- hot cells: the crescent's glow comes through wide gaps round small plates --------------
    cells = {}
    for f in bm.faces:
        if is_crust(label[f.index]):
            cells.setdefault(label[f.index], []).append(f)
    open_w, open_h = {}, {}
    for lab_, fs in cells.items():
        if not upper_cell[lab_]:
            continue
        hs = []
        for f in fs:
            c, r = cr(pos(fu(f)))
            hs.append(sample(g, c + 0.5, r + 0.5))
        hot = [h for h in hs if h >= HOT]
        frac = len(hot) / len(hs)
        if frac >= 0.25:
            open_w[lab_] = 0.016 + 0.030 * min(1.0, frac)
            open_h[lab_] = max(hot) * 0.95

    # --- shape ---------------------------------------------------------------------------------
    vlabs = {v.index: {label[f.index] for f in v.link_faces} for v in bm.verts}
    for v in bm.verts:
        v.co = pos(unit[v.index])
    bm.normal_update()
    normal = {v.index: v.normal.copy() for v in bm.verts}

    offs = {v.index: 0.0 for v in bm.verts}   # displacement along the normal
    for v in bm.verts:
        labs = vlabs[v.index]
        if len(labs) == 1:
            continue
        if any(not is_crust(l_) for l_ in labs):
            offs[v.index] = 0.0          # the craters' outer edge: their lips rise from here
        elif v.index in fixed:
            offs[v.index] = -0.008       # the equator seam: a crack, barely sunk
        elif any(l_ in open_w for l_ in labs):
            offs[v.index] = -HOT_SINK
        else:
            offs[v.index] = -GROOVE

    # crust cells: pressed onto their own plane (inwards only) and lifted: lumpy facets on top,
    # both fading out towards the widest line so the plan stays the sprite's
    cell_of = {}
    for lab_, fs in cells.items():
        vs = {v for f in fs for v in f.verts}
        inner = [v for v in vs if len(vlabs[v.index]) == 1]
        bnd = [v for v in vs if len(vlabs[v.index]) > 1]
        if not inner or not bnd:
            continue
        n = sum((f.normal * f.calc_area() for f in fs), Vector()).normalized()
        plane = sum(b.co.dot(n) for b in bnd) / len(bnd)
        lift = LIFT * (0.3 + 0.7 * rnd.random()) * (max(0.0, n.z) ** 1.2 if upper_cell[lab_] else 0.15)
        # rings in from the cell's edge: press and lift ease in over three of them (no steep
        # slope at the edge where the mesh is fine round the craters)
        depth = {v: 0 for v in bnd}
        front = list(bnd)
        while front:
            nxt_ = []
            for v in front:
                for e in v.link_edges:
                    o = e.other_vert(v)
                    if o in vs and o not in depth:
                        depth[o] = depth[v] + 1
                        nxt_.append(o)
            front = nxt_
        for v in inner:
            d = v.co.dot(n) - plane
            ease = min(1.0, depth.get(v, 3) / 3.0)
            cell_of[v.index] = (n, max(0.0, d) * FLAT * ease, lift * ease)
    for v in bm.verts:
        fz = min(1.0, abs(unit[v.index].z) / 0.35)
        v.co = v.co + normal[v.index] * offs[v.index]
        if v.index in cell_of:
            n, press, lift = cell_of[v.index]
            v.co = v.co - n * press * fz + normal[v.index] * lift * fz
    bm.normal_update()

    # --- layers --------------------------------------------------------------------------------
    lab = bm.faces.layers.int.new("lab")
    bnd_l = bm.faces.layers.int.new("band")
    col = bm.faces.layers.int.new("col")      # fixed palette colour of crater faces
    for f in bm.faces:
        f[lab] = label[f.index]
        f[bnd_l] = band[f.index]
        f[col] = 0

    # --- craters: the vent and the two small openings, modelled in rings -----------------------
    def crater(faces, rings, core):
        """Dissolve the crater's faces into one n-gon, then build its rings by scaling that
        outline towards its centre (no inset spikes at the outline's concave corners): each ring
        steps by its thickness and depth (along the ball's normal there), the core a fan."""
        res = bmesh.ops.dissolve_faces(bm, faces=[f for f in faces if f.is_valid], use_verts=True)
        reg = sorted(res["region"], key=lambda f: -f.calc_area())
        for f in reg[1:]:
            f[col] = rings[0][2]
        cur = reg[0]
        prev = list(cur.verts)
        cen = sum((v.co for v in prev), Vector()) / len(prev)
        nrm = (cen - Vector((ox, oy, 0.0))).normalized()
        r0 = sum(((v.co - cen) - nrm * (v.co - cen).dot(nrm)).length for v in prev) / len(prev)
        lab_c = cur[lab]
        bmesh.ops.delete(bm, geom=[cur], context="FACES_ONLY")
        t, dz = 0.0, 0.0
        for th, dp, idx in rings:
            t += th
            dz += dp
            s_ = max(0.08, 1 - t)
            ring_v = [bm.verts.new(cen + (v.co - cen) * s_ + nrm * dz) for v in prev]
            n = len(prev)
            for i in range(n):
                f = bm.faces.new((prev[i], prev[(i + 1) % n], ring_v[(i + 1) % n], ring_v[i]))
                f[col] = idx
                f[lab] = lab_c
                f[bnd_l] = 0
            prev = ring_v
        cv = bm.verts.new(cen + nrm * (dz - 0.004))
        n = len(prev)
        for i in range(n):
            f = bm.faces.new((prev[i], prev[(i + 1) % n], cv))
            f[col] = core
            f[lab] = lab_c
            f[bnd_l] = 0

    crater([f for f in bm.faces if f[lab] == VENT_L], VENT_RINGS, VENT_CORE)
    for k, (_, _, rings, core) in enumerate(PITS):
        fs = [f for f in bm.faces if f[lab] == PIT_L + k]
        if fs:
            crater(fs, rings, core)

    # --- materials -----------------------------------------------------------------------------
    mats, slot = [], {}

    def mat(kind, idx):
        if (kind, idx) not in slot:
            if kind == "crust":
                m = common.palette_material(sprite, idx, NAME, metallic=0.0, roughness=0.93)
            elif kind == "ember":
                m = common.palette_material(sprite, idx, NAME, metallic=0.0, roughness=0.9)
            else:
                # lava, the smouldering rim and the crack walls: metallic 1 / rough 1 kills the
                # diffuse term, so in game they show the palette colour itself, matte
                m = common.palette_material(sprite, idx, NAME, metallic=1.0, roughness=1.0, emission_strength=1.0)
            bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            m.roughness = bs.inputs["Roughness"].default_value    # viewport/workbench previews too
            m.metallic = bs.inputs["Metallic"].default_value
            slot[(kind, idx)] = len(mats)
            mats.append(m)
        return slot[(kind, idx)]

    def lava(idx):
        return mat("lava", idx)

    def rim_bin(p):
        h = rad_at(RH, math.atan2(p.y - oy, p.x - ox))
        return bin_of(max(0.18, h if h >= 0.6 else min(h, 0.5)))

    # crack grooves: each crust cell inset by a hair (a hot cell by a wide gap); the strip runs
    # from the cell's face down to the sunk boundary, so two neighbours' strips make the groove
    cells_ = {}
    for f in bm.faces:
        if is_crust(f[lab]):
            cells_.setdefault(f[lab], []).append(f)
    for lab_, fs in cells_.items():
        before = set(bm.faces)
        th = GROOVE_W
        if lab_ in open_w:   # a wide gap, but the plate keeps about a third of the cell
            th = min(open_w[lab_], 0.36 * math.sqrt(sum(f.calc_area() for f in fs) / math.pi))
        bmesh.ops.inset_region(bm, faces=fs, thickness=th, depth=0.0,
                               use_even_offset=False, use_boundary=True)
        for f in set(bm.faces) - before:
            f[lab] = -2 - lab_ if lab_ in open_w else -1
    bm.normal_update()

    # the rim colour per crust cell (its band faces' mean rim heat): colour changes follow cells
    cell_rim = {}
    for lab_, fs in cells_.items():
        hs = [rad_at(RH, math.atan2(f.calc_center_median().y - oy, f.calc_center_median().x - ox))
              for f in fs if f[bnd_l] == 1]
        if hs:
            h = sum(hs) / len(hs)
            cell_rim[lab_] = bin_of(max(0.18, h if h >= 0.6 else min(h, 0.5)))

    for f in bm.faces:
        lab_ = f[lab]
        p = f.calc_center_median()
        c, r = cr(p)
        if f[col]:
            f.material_index = lava(f[col])
        elif lab_ == -1:
            # groove floor: the crack's dull glow, a little hotter where the sprite is hot
            if f[bnd_l] == 1:
                h = rad_at(RH, math.atan2(p.y - oy, p.x - ox))
                f.material_index = lava(bin_of(max(0.18, h)) if h >= 0.6 else 113)
            else:
                h = sample(g, c + 0.5, r + 0.5) if p.z > 0 else 0.0
                f.material_index = lava(115 if h >= 0.30 else 113)
        elif lab_ <= -2:
            f.material_index = lava(bin_of(open_h[-2 - lab_]))
        elif f[bnd_l] == 1:
            f.material_index = lava(cell_rim[lab_]) if lab_ not in open_w else mat("ember", 112)
        elif f[bnd_l] == 2:
            f.material_index = mat("ember", 112)
        elif lab_ in open_w:
            f.material_index = mat("ember", 112)
        else:
            f.material_index = mat("crust", 1)

    # ember cells where the sprite draws the crust dark red (112-114) rather than black
    for lab_, fs in cells_.items():
        ups = [f for f in fs if f.is_valid and f[lab] == lab_ and f[bnd_l] == 0 and f.calc_center_median().z > 0.05]
        if not ups:
            continue
        reds = 0
        for f in ups:
            c, r = cr(f.calc_center_median())
            idx = pix[min(H - 1, max(0, round(r)))][min(W - 1, max(0, round(c)))]
            reds += idx in (112, 113, 114)
        if reds / len(ups) > EMBER_SHARE:
            for f in ups:
                f.material_index = mat("ember", 112)

    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    print("validate:", me.validate(verbose=False))
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, pix = load()
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite, pix)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=1600, smooth=6)
    shell.name = shell.data.name = f"{NAME}_outline"
    if "--out" in argv:   # a scratch build for review renders
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb([obj, shell], out)
        print("exported", out)
        return
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
