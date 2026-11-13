"""Design A: the falling fire column (assembly-newshk-17 + -51 + -89) and the grey heater craft
(newshk-283), episode 3 (3.6 FLEET) and 4 (LAVA RUN).

THE FIRE COLUMN. In the game three kinds of unit are spawned at one x and fall together, head
first, as one object about 72 x 150 px: the head (assembly-newshk-89: newshk-89/91/93, rounding off
at the bottom), three or four flame segments (assembly-newshk-51: newshk-51/53/55, cut flat at
top and bottom) and the dome end (assembly-newshk-17: newshk-13/15/17, rounding off at the top;
its pixels are the head's flipped). Each unit is 72x28 px and they are spawned 24 px apart, so
each overlaps its neighbour by 4 rows.

All three are built by one rule, so they join without a seam: a pillar of fire lofted down the
sprite in sections every half pixel. Each section spans the sprite's own run in that row (left and
right edges smoothed lightly and interpolated with pchip, so the ragged flame edge reads as tongues,
not pixel steps); its top is a semi-ellipse whose height comes from the run's half width (capped at
HMAX), its underside a flatter one (UNDER). Where a unit really ends (the head's bottom, the dome's
top) the height rounds off over R_END px, so the ends are domes. On top of the ellipse a soft relief
(a band-pass of the sprite's brightness, never pixel steps) raises the yellow and white flame
tongues in the side bands; the white core stays one smooth crown. Every face takes the palette
index of the sprite under its centre (the sprite blurred a little, so the colour bands have smooth
contours, not pixel squares); all of them glow (metallic 1, rough, D126/D173), the white core fully,
the red rim partly so the form still shades.

The overlap: a unit's bottom 4 rows lie under the next unit's top 4 rows. They round off downwards (SINK
over the 4 rows), so the lower unit's top always covers them (no z-fighting) and at the visible
seam both are the same height. The outline shell (D51, D90 from the closed body) is cut open at
the joins (rows 0 and 24 where a unit continues) and at the piece seams, so no ink line crosses
the column.

THE HEATER (newshk-283). A grey craft flying down the screen, prongs first: a housing with a
sloped roof at the back (top of the sprite), a sunken dark vent framed in light grey across its
middle, ribbed side strips, an overhang lip (row 13), and two thick prongs hanging down the screen,
each with a dark slot on its inner side holding red-hot elements, and pale tips.

This one script builds all four models; run directly it exports only assembly-newshk-51 (the 89, 17 and
newshk-283 scripts call main(only=...) for theirs), so each glb has one builder.
Run: blender --background --python assets/blender/enemies/assembly-newshk-51.py [-- --only NAME] [--views DIR] [--review]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

SCRATCH = Path(tempfile.gettempdir()) / "assembly-newshk-51"  # --review's masks and report
U = 1 / 12  # one sprite pixel in Blender units

# --- the fire column --------------------------------------------------------------------------------

FIRE = [
    # name, pieces left to right, cut at the top (continues above), cut at the bottom, sink bottom
    ("assembly-newshk-17", ["newshk-13", "newshk-15", "newshk-17"], False, True, True),
    ("assembly-newshk-51", ["newshk-51", "newshk-53", "newshk-55"], True, True, True),
    ("assembly-newshk-89", ["newshk-89", "newshk-91", "newshk-93"], True, False, False),
]
W, H = 72, 28
HMAX = 13.0  # crown height of the pillar, px
ASPECT = 0.5  # crown height per px of half width (narrow end rows are lower)
UNDER = 0.5  # underside depth as a share of the crown height
R_END = 11.0  # a real end (head, dome) rounds off over this many px
SINK = 0.7  # the bottom 4 overlap rows round off, losing up to this share of their height (under the next unit)
RELIEF = 0.45  # px of relief per palette step of band-passed brightness
RELIEF_MAX = 1.3
STEP_Y = 0.7  # section spacing, px
N_TOP = 84  # points across the top
N_BOT = 10  # points across the underside
EDGE_SMOOTH = (1, 4, 1)  # weights for the run edges (row above, row, row below)
# Glow per palette index (D126: 1 = the palette colour unlit; below 1 the rest is lit, metallic 1,
# rough, so the red and orange flanks still shade and show the form).
GLOW = {127: 1.0, 126: 1.0, 125: 0.95, 124: 0.92, 123: 0.88, 122: 0.84, 121: 0.8, 120: 0.76,
        119: 0.7, 118: 0.66, 117: 0.62, 116: 0.6, 115: 0.6}


def composite(pieces):
    grid = np.full((H, W), -1, dtype=int)
    colors = {}
    for i, name in enumerate(pieces):
        data = common.load_sprite(ROOT, name)
        colors.update(data["colors"])
        px = np.array(data["frames"][0]["pixels"], dtype=int)
        sub = grid[:, i * 24:(i + 1) * 24]
        sub[px >= 0] = px[px >= 0]
    return grid, colors


def blur(a, sigma):
    if sigma <= 0:
        return a.copy()
    r = max(1, int(math.ceil(3 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, r, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, p)
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, p)
    return p


def filled_index(grid):
    """The index grid with transparent pixels filled from their nearest opaque neighbours (so a
    blur near the outline doesn't pull in 'nothing')."""
    g = grid.astype(float)
    known = grid >= 0
    g[~known] = 0
    for _ in range(80):
        if known.all():
            break
        acc = np.zeros_like(g)
        cnt = np.zeros_like(g)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            sh = np.roll(np.roll(g, dr, 0), dc, 1)
            sk = np.roll(np.roll(known, dr, 0), dc, 1)
            if dr == -1:
                sk[-1, :] = False
            if dr == 1:
                sk[0, :] = False
            if dc == -1:
                sk[:, -1] = False
            if dc == 1:
                sk[:, 0] = False
            acc += np.where(sk, sh, 0)
            cnt += sk
        new = (~known) & (cnt > 0)
        g[new] = acc[new] / cnt[new]
        known = known | new
    return g


def bilinear(a, x, y):
    """a sampled at sprite position (x, y) px (pixel centres at +0.5)."""
    h, w = a.shape
    fx = min(max(x - 0.5, 0.0), w - 1.0)
    fy = min(max(y - 0.5, 0.0), h - 1.0)
    x0, y0 = int(fx), int(fy)
    x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
    tx, ty = fx - x0, fy - y0
    return ((a[y0, x0] * (1 - tx) + a[y0, x1] * tx) * (1 - ty)
            + (a[y1, x0] * (1 - tx) + a[y1, x1] * tx) * ty)


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def edge_curves(grid):
    """The run's left and right edge (px) as smooth functions of y (px from the grid's top)."""
    rows = [r for r in range(H) if (grid[r] >= 0).any()]
    xl = {r: float(np.nonzero(grid[r] >= 0)[0][0]) for r in rows}
    xr = {r: float(np.nonzero(grid[r] >= 0)[0][-1] + 1) for r in rows}
    a, b, c = EDGE_SMOOTH

    def soft(e):
        out = {}
        for r in rows:
            up, dn = e.get(r - 1, e[r]), e.get(r + 1, e[r])
            out[r] = (a * up + b * e[r] + c * dn) / (a + b + c)
        return out
    xl, xr = soft(xl), soft(xr)
    yc = [r + 0.5 for r in rows]
    fl = T.pchip(yc, [xl[r] for r in rows])
    fr = T.pchip(yc, [xr[r] for r in rows])

    def edges(y):
        yy = min(max(y, yc[0]), yc[-1])
        return fl(yy), fr(yy)
    return edges, rows


SEGMENT_EDGES = None  # the flame segment's (assembly-newshk-51) edges, set in build_fire


def fire_unit(name, pieces, cut_top, cut_bottom, sink, coll):
    grid, colors = composite(pieces)
    sprite = {"name": name, "colors": colors}
    own, rows = edge_curves(grid)
    r0, r1 = rows[0], rows[-1]
    seg = SEGMENT_EDGES or own

    def edges(y):
        """Own edges, blended over the 4 overlap rows towards the neighbour's: at a cut top
        towards the segment's bottom rows (the unit above), at a cut bottom towards the segment's
        top rows (the unit below), so both units have one section at the seam and the lower one's
        sunk rows stay inside the upper one's."""
        L, R = own(y)
        if cut_top and y < 4:
            t = smoothstep(y / 4)
            L2, R2 = seg(y + 24)
            L, R = L2 + (L - L2) * t, R2 + (R - R2) * t
        if cut_bottom and y > H - 4:
            t = smoothstep((y - (H - 4)) / 4)
            L2, R2 = seg(y - 24)
            L, R = L + (L2 - L) * t, R + (R2 - R) * t
            L, R = L + 1.2 * t, R - 1.2 * t  # tucked in a little: the next unit's top covers it
        return L, R

    idx = filled_index(grid)
    colour = blur(idx, 0.55)
    bright = blur(idx, 1.0) - blur(idx, 3.2)  # band-pass: the flame tongues, not the big bands
    core = blur((grid == 127).astype(float), 1.5)

    used = sorted({int(v) for v in grid.ravel() if v >= 0})
    mats, mat_of = [], {}
    for v in used:
        mat_of[v] = len(mats)
        mats.append(common.palette_material(sprite, v, name, metallic=1.0, roughness=0.9,
                                            emission_strength=GLOW.get(v, 0.7)))

    def pal_at(x, y):
        v = int(round(bilinear(colour, x, y)))
        v = min(max(v, used[0]), used[-1])
        while v not in mat_of:
            v += 1
        return mat_of[v]

    ya = 0.0 if cut_top else float(r0)
    yb = float(H) if cut_bottom else float(r1 + 1)
    ys = T.frange(ya, yb, STEP_Y)
    us = [-math.cos(math.pi * i / N_TOP) for i in range(N_TOP + 1)]  # -1..1, dense at the edges
    ub = [math.cos(math.pi * j / N_BOT) for j in range(1, N_BOT)]  # 1..-1 inner points

    def crown(y, half):
        hgt = min(HMAX, ASPECT * half)
        if not cut_top:
            hgt *= math.sqrt(max(0.0, 1 - (1 - min(1.0, (y - ya) / R_END)) ** 2))
        if not cut_bottom:
            hgt *= math.sqrt(max(0.0, 1 - (1 - min(1.0, (yb - y) / R_END)) ** 2))
        if sink and y > H - 4:
            hgt *= 1 - SINK * smoothstep((y - (H - 4)) / 4)
        return max(hgt, 0.35)

    bm = bmesh.new()
    rings = []
    for y in ys:
        L, R = edges(y)
        cx, half = (L + R) / 2, (R - L) / 2
        hgt = crown(y, half)
        ring = []
        for u in us:
            x = cx + u * half
            s = math.sqrt(max(0.0, 1 - u * u))
            z = hgt * s
            # Relief: tongues in the flanks, faded out at the outline and over the white crown.
            rel = RELIEF * bilinear(bright, x, y)
            rel = max(-RELIEF_MAX, min(RELIEF_MAX, rel))
            rel *= smoothstep(s / 0.45) * (1 - min(1.0, bilinear(core, x, y)))
            # At a real end the relief fades out; at a seam it is 0 on the seam row (row 0 of the
            # lower unit, row 24 of the upper one), so both units meet in one smooth section.
            rel *= smoothstep((y - ya) / 3) if not cut_top else smoothstep(y / 3)
            rel *= smoothstep((yb - y) / 3) if not cut_bottom else smoothstep((H - 4 - y) / 3)
            ring.append(bm.verts.new(((x - W / 2) * U, (H / 2 - y) * U, (z + rel) * U)))
        for u in ub:
            x = cx + u * half
            z = -UNDER * hgt * math.sqrt(max(0.0, 1 - u * u))
            ring.append(bm.verts.new(((x - W / 2) * U, (H / 2 - y) * U, z * U)))
        rings.append((y, cx, half, ring))
    n = len(rings[0][3])
    for (ya_, _, _, ra), (yb_, _, _, rb) in zip(rings, rings[1:]):
        ym = (ya_ + yb_) / 2
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
            co = (ra[i].co + ra[j].co + rb[i].co + rb[j].co) / 4
            f.material_index = pal_at(co.x / U + W / 2, ym)
            f.smooth = True
    # End caps: a fan from the section's centre, each sliver in the colour at its outer edge (the
    # flank's red where a sunk overlap row shows beside its neighbour, never the white core).
    for k, (y, cx, half, ring) in ((0, rings[0]), (1, rings[-1])):
        ctr = sum((v.co for v in ring), Vector()) / len(ring)
        cv = bm.verts.new(ctr)
        for i in range(n):
            j = (i + 1) % n
            tri = (ring[i], ring[j], cv) if k == 1 else (ring[j], ring[i], cv)
            f = bm.faces.new(tri)
            ex_ = (ring[i].co.x + ring[j].co.x) / 2 / U + W / 2
            side = min(abs(ex_ - (cx - half)), abs(ex_ - (cx + half)))
            f.material_index = pal_at(cx - half + 0.5 if ex_ < cx else cx + half - 0.5, y) \
                if side < 6 else pal_at(ex_, y)
            f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = common.mesh_object(name, bm, mats, coll, smooth=None)
    return obj, grid, colors


def open_cut(obj, x0, x1, y0, y1, centre, name, coll):
    """A copy of obj inside the box (assembly px, x right, y down), cuts left open, moved so
    `centre` (assembly px) is the origin."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    planes = (((x0 - W / 2) * U, 0, 0), (-1, 0, 0)), (((x1 - W / 2) * U, 0, 0), (1, 0, 0)), \
             ((0, (H / 2 - y1) * U, 0), (0, -1, 0)), ((0, (H / 2 - y0) * U, 0), (0, 1, 0))
    for co, no in planes:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                               plane_no=no, clear_outer=True)
    cx, cy = (centre[0] - W / 2) * U, (H / 2 - centre[1]) * U
    bmesh.ops.translate(bm, vec=(-cx, -cy, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def build_fire(coll):
    """Returns {unit: (pieces {name: obj}, shells {name: obj}, whole body, grid, colors)}."""
    global SEGMENT_EDGES
    SEGMENT_EDGES = edge_curves(composite(FIRE[1][1])[0])[0]
    out = {}
    for name, pieces, cut_top, cut_bottom, sink in FIRE:
        body, grid, colors = fire_unit(name, pieces, cut_top, cut_bottom, sink, coll)
        shell = common.outline_shell(body, coll, voxel=0.03, faces=4000, smooth=6, inside=0.004)
        layout = [(p, 12 + 24 * i - W / 2, 0) for i, p in enumerate(pieces)]
        parts = common.split_assembly(body, layout, coll)
        shells = {}
        # Open at the seams: the upper unit's shell ends on the seam row (its row 24), so its
        # inner side never shows through the lower unit's top; the lower one's runs from row 0.
        ytop = 1.5 if cut_top else -5.0
        ybot = H - 4.0 if cut_bottom else H + 5.0
        for i, p in enumerate(pieces):
            # Shells: open at piece seams; trimmed open where the column continues.
            sh = open_cut(shell, 24 * i, 24 * (i + 1), ytop, ybot, (24 * i + 12, H / 2),
                          f"{p}_outline", coll)
            sh.data.shade_smooth()
            sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
            sh["tyrian_outline"] = True
            shells[p] = sh
        for o in (body, shell):
            o.hide_render = True
            o.hide_set(True)
        out[name] = (parts, shells, body, grid, colors)
    return out


# --- the heater craft (newshk-283) -----------------------------------------------------------------

HEATER = "newshk-283"


def rounded_loop(x0, x1, z0, z1, r_top, r_bot, n=4):
    """A section (x, z) with rounded top corners (radius r_top) and chamfered bottom ones."""
    pts = []
    for cx, cz, a0, a1, r in ((x1 - r_top, z1 - r_top, 0, 90, r_top), (x0 + r_top, z1 - r_top, 90, 180, r_top)):
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    pts += [(x0, z0 + r_bot), (x0 + r_bot, z0), (x1 - r_bot, z0), (x1, z0 + r_bot)]
    return pts


def loft_xz(part, sections, mat, cap0=True, cap1=True, mats=None):
    """Loft along y through [(y, [(x, z), ...])] with the same point count; mats[i] per band."""
    rings = [[part.v((x, y, z)) for x, z in pts] for y, pts in sections]
    centres = [(sum(x for x, _ in pts) / len(pts), y, sum(z for _, z in pts) / len(pts)) for y, pts in sections]
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            part.f((r0[i], r0[j], r1[j], r1[i]), mats[k] if mats else mat, away=centres[k])
    if cap0:
        part.f(rings[0], mats[0] if mats else mat, out=(0, -1, 0))
    if cap1:
        part.f(rings[-1], mats[-1] if mats else mat, out=(0, 1, 0))


def build_heater(coll):
    """Sprite px coordinates: x = column - 12 (centre 0), y = row (down the screen), z up."""
    data = common.load_sprite(ROOT, HEATER)
    sprite = {"name": HEATER, "colors": data["colors"]}

    def pal(i, **kw):
        return common.palette_material(sprite, i, HEATER, **kw)
    mats = [
        pal(9, metallic=0.55, roughness=0.32),  # 0 GREY housing, prongs
        pal(8, metallic=0.55, roughness=0.36),  # 1 SIDE shoulders, rear ramp
        pal(10, metallic=0.5, roughness=0.3),  # 2 RAIL side strips
        pal(11, metallic=0.5, roughness=0.26),  # 3 FRAME vent frame, prong tips
        pal(6, metallic=0.4, roughness=0.5),  # 4 GROOVE grooves, vent floor
        pal(5, metallic=0.4, roughness=0.55),  # 5 LIP front face of the housing
        pal(1, metallic=0.2, roughness=0.7),  # 6 BLACK slot walls and floor
        pal(116, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 7 ROD red-hot
        pal(123, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 8 HOT left hot spot
        pal(121, metallic=1.0, roughness=0.85, emission_strength=1.0),  # 9 HOT2 right hot spot
        pal(13, metallic=0.5, roughness=0.25),  # 10 BOLT
        pal(112, metallic=1.0, roughness=0.9, emission_strength=0.6),  # 11 EMBER divider glow
        pal(3, metallic=0.3, roughness=0.6),  # 12 SHADE vent back wall
    ]
    for m in mats:  # polished grey: F0 through Specular IOR Level (D176)
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if m.name.split("_")[1] in ("9", "8", "10", "11", "13"):
            b.inputs["Specular IOR Level"].default_value = 0.7
    GREY, SIDE, RAIL, FRAME, GROOVE, LIP, BLACK, ROD, HOT, HOT2, BOLT, EMBER, SHADE = range(13)
    P = T.Part(HEATER, smooth_angle=35)
    X = lambda c: c - 12.0  # noqa: E731  sprite column edge -> x
    DECK, BASE = 7.5, -1.5

    # Housing, rows 4-13.6: a block with rounded shoulders (cols 0-2), the deck at DECK.
    def housing(y):
        return rounded_loop(X(0.0), X(24.0), BASE, DECK, 2.2, 0.8)
    loft_xz(P, [(4.0, housing(4.0)), (13.0, housing(13.0))], GREY)
    # Rear edge chamfer row 3.6-4.2 and rear ramp (the sloped roof, rows 1-4): a frustum from the
    # housing's back edge (cols 6-18 at DECK) down to cols 10-14 at row 1.
    T.hull(P, [(X(1.0), 4.4, DECK - 0.4), (X(23.0), 4.4, DECK - 0.4), (X(1.0), 4.4, BASE),
               (X(23.0), 4.4, BASE), (X(2.0), 3.9, DECK - 1.4), (X(22.0), 3.9, DECK - 1.4),
               (X(2.0), 3.9, BASE + 0.5), (X(22.0), 3.9, BASE + 0.5)], SIDE)
    T.hull(P, [(X(5.8), 4.2, DECK), (X(18.2), 4.2, DECK), (X(6.3), 3.0, DECK - 0.5),
               (X(17.7), 3.0, DECK - 0.5), (X(8.5), 2.0, DECK - 1.7), (X(15.5), 2.0, DECK - 1.7),
               (X(10.4), 1.15, DECK - 3.2), (X(13.6), 1.15, DECK - 3.2),
               (X(5.8), 4.2, BASE), (X(18.2), 4.2, BASE), (X(10.4), 1.15, BASE + 1.0),
               (X(13.6), 1.15, BASE + 1.0)], GREY)
    # Front lip (row 13): the housing's face falls to the prongs over a chamfer, dark (D176).
    T.hull(P, [(X(0.3), 12.8, DECK), (X(23.7), 12.8, DECK), (X(0.3), 13.9, DECK - 2.2),
               (X(23.7), 13.9, DECK - 2.2), (X(0.3), 13.9, BASE), (X(23.7), 13.9, BASE),
               (X(0.3), 12.8, BASE), (X(23.7), 12.8, BASE)], LIP)
    # Side rails (col 2 / 21) and the bolt columns (col 4 / 19) with two bolts each.
    for c in (2.0, 21.0):
        P_pts = T.cbox(X(c), X(c + 1.0), 4.6, 12.6, DECK - 0.5, DECK + 0.45, 0.25)
        T.hull(P, P_pts, RAIL)
        for r in (6.5, 11.0):  # cross grooves on the rails
            T.hull(P, T.cbox(X(c - 0.05), X(c + 1.05), r, r + 0.4, DECK + 0.2, DECK + 0.5, 0.05), GROOVE)
    for c in (4.5, 19.5):
        for r in (4.9, 9.5):
            pts = []
            for k in range(8):
                a = 2 * math.pi * k / 8
                for zz, rr in ((DECK - 0.1, 0.55), (DECK + 0.25, 0.42), (DECK + 0.38, 0.2)):
                    pts.append((X(c) + rr * math.cos(a), r + rr * math.sin(a), zz))
            T.hull(P, pts, BOLT)
    # The vent (cols 7-17, rows 7-10.5): a light frame round a recess 2 px deep, the far wall in
    # shade, the floor mid grey with two louvre bars.
    T.hull(P, T.cbox(X(7.0), X(17.0), 6.7, 7.4, DECK - 0.3, DECK + 0.9, 0.25), FRAME)
    T.hull(P, T.cbox(X(7.0), X(17.0), 10.0, 10.9, DECK - 0.3, DECK + 0.9, 0.25), FRAME)
    T.hull(P, T.cbox(X(7.0), X(7.7), 6.7, 10.9, DECK - 0.3, DECK + 0.9, 0.25), FRAME)
    T.hull(P, T.cbox(X(16.3), X(17.0), 6.7, 10.9, DECK - 0.3, DECK + 0.9, 0.25), FRAME)
    # (the housing's deck runs under the frame; the recess is the frame's dark floor and a far
    # wall sloping back into shade)
    T.hull(P, [(X(7.7), 7.4, DECK + 0.03), (X(16.3), 7.4, DECK + 0.03), (X(7.7), 8.2, DECK + 0.03),
               (X(16.3), 8.2, DECK + 0.03), (X(7.7), 7.4, DECK - 0.1), (X(16.3), 7.4, DECK - 0.1)], SHADE)
    T.hull(P, T.cbox(X(7.7), X(16.3), 8.2, 10.0, DECK - 0.1, DECK + 0.03, 0.02), LIP)
    for r in (8.5, 9.3):
        T.hull(P, T.cbox(X(7.9), X(16.1), r, r + 0.4, DECK, DECK + 0.25, 0.1), GROOVE)

    # Prongs, rows 13.5-27.6. Left: body cols 0-6 (a groove at col 3), slot cols 6-10 (black
    # walls, a divider at col 8, red-hot rods at cols 7 and 9); right mirrored about col 11.5.
    PT = 5.6  # prong top
    for side in (-1, 1):
        def C(c):  # left-prong column -> x (mirror about column edge 11.5 for the right one)
            return X(c) if side < 0 else X(23.0 - c)
        def lo(a, b):
            return min(a, b), max(a, b)
        def body_round(y):
            """The prong body's section: a big round on its outer top corner."""
            a, b = lo(C(0.0), C(6.2))
            r = 1.8
            if side < 0:  # outer side at a (left)
                arc = [(a + r + r * math.cos(t), PT - r + r * math.sin(t))
                       for t in (math.radians(90 + 90 * k / 4) for k in range(5))]
                return [(b, PT)] + arc + [(a, BASE + 0.6), (a + 0.6, BASE), (b, BASE)]
            arc = [(b - r + r * math.cos(t), PT - r + r * math.sin(t))
                   for t in (math.radians(90 * k / 4) for k in range(5))]
            return [(a, BASE), (b - 0.6, BASE), (b, BASE + 0.6)] + arc + [(a, PT)]
        loft_xz(P, [(13.6, body_round(13.6)), (23.6, body_round(23.6))], GREY)
        # groove along the body top (col 3)
        g0, g1 = lo(C(2.8), C(3.8))
        T.hull(P, T.cbox(g0, g1, 14.0, 23.2, PT - 0.9, PT + 0.05, 0.15), GROOVE)
        # panel line across the body at row 22
        p0, p1 = lo(C(3.8), C(6.0))
        T.hull(P, T.cbox(p0, p1, 21.9, 22.4, PT - 0.6, PT + 0.05, 0.08), LIP)
        # slot: floor, outer wall (col 6), divider (col 8), inner wall (col 10), rods 7 and 9
        s0, s1 = lo(C(6.0), C(10.0))
        T.hull(P, T.cbox(s0, s1, 13.6, 23.6, BASE, PT - 2.4, 0.1), BLACK)
        w0, w1 = lo(C(5.9), C(6.6))
        T.hull(P, T.cbox(w0, w1, 13.6, 23.6, BASE, PT - 0.3, 0.15), BLACK)
        d0, d1 = lo(C(7.75), C(8.25))
        T.hull(P, T.cbox(d0, d1, 15.5, 23.4, PT - 2.6, PT - 1.0, 0.1), EMBER)
        i0, i1 = lo(C(9.55), C(10.0))
        T.hull(P, T.cbox(i0, i1, 13.6, 23.6, BASE, PT - 1.2, 0.12), BLACK)
        for c in (7.0, 9.0):
            xc = C(c + 0.5)
            for (ya, yb, m) in ((14.6, 20.5, ROD), (20.5, 21.6, HOT if side < 0 and c == 9.0 else
                                                     (HOT2 if side > 0 and c == 9.0 else ROD)),
                                (21.6, 23.4, ROD)):
                pts = []
                for k in range(10):
                    a = 2 * math.pi * k / 10
                    for yy in (ya, yb):
                        pts.append((xc + 0.55 * math.cos(a), yy, PT - 1.5 + 0.55 * math.sin(a)))
                T.hull(P, pts, m)
        # hood over the slot's top end (rows 13.6-15.6): its shadow is the sprite's dark grey there
        T.hull(P, T.cbox(s0, s1, 13.4, 14.6, PT - 0.9, PT - 0.1, 0.25), LIP)
        # tip, rows 23.4-27.6: a rounded, polished cap over the body and slot ends
        tip = []
        t0, t1 = lo(C(0.9), C(8.1))
        for zz, ins in ((BASE + 0.4, 0.5), (PT - 1.4, 0.0), (PT - 0.25, 0.6)):
            rr = 2.4
            for cxs, a0 in ((t0 + rr + ins, 90), (t1 - rr - ins, 0)):
                for k in range(5):
                    a_ = math.radians(a0 + 90 * k / 4)
                    tip.append((cxs + rr * math.cos(a_), 27.75 - ins - rr + rr * math.sin(a_), zz))
            tip += [(t0 + ins, 23.4, zz), (t1 - ins, 23.4, zz)]
        T.hull(P, tip, FRAME)
    obj = T.finish(P, mats, coll)
    return obj


# --- measuring and views ------------------------------------------------------------------------

def top_samples(objs, w, h, k=4):
    """Raycast straight down over a w x h px grid (origin at its centre), k rays per px: returns
    (mask k*h x k*w bool, index k*h x k*w int palette index or -1)."""
    bm = bmesh.new()
    mat_names = []
    for o in objs:
        me = o.data
        tmp = bmesh.new()
        tmp.from_mesh(me)
        bmesh.ops.transform(tmp, matrix=o.matrix_world, verts=tmp.verts)
        base = len(mat_names)
        mat_names += [m.name for m in me.materials]
        for f in tmp.faces:
            f.material_index += base
        me2 = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me2)
        tmp.free()
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    mask = np.zeros((h * k, w * k), bool)
    index = np.full((h * k, w * k), -1, int)
    for j in range(h * k):
        for i in range(w * k):
            x = ((i + 0.5) / k - w / 2) * U
            y = (h / 2 - (j + 0.5) / k) * U
            hit = tree.ray_cast(Vector((x, y, 50.0)), Vector((0, 0, -1)), 100.0)
            if hit[0] is not None:
                mask[j, i] = True
                nm = mat_names[bm.faces[hit[2]].material_index]
                if nm.startswith("pal_"):
                    index[j, i] = int(nm.split("_")[1])
    bm.free()
    return mask, index


def write_mask_png(path, mask):
    hgt, wid = mask.shape
    img = bpy.data.images.new("mask", wid, hgt, alpha=True)
    px = np.zeros((hgt, wid, 4), np.float32)
    px[mask] = (1, 1, 1, 1)
    img.pixels[:] = px[::-1].ravel()
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def setup_render(px=640):
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bg.inputs[1].default_value = 1.0
    if "sun" not in bpy.data.objects:
        sd = bpy.data.lights.new("sun", "SUN")
        sd.energy = 3.0
        sun = bpy.data.objects.new("sun", sd)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(15))


def render_views(objs, out_dir, extent, centre=(0, 0, 0), tag="", px=640, under=True):
    scene = bpy.context.scene
    setup_render(px)
    keep = set(objs) | {bpy.data.objects["sun"]}
    hidden = []
    for o in scene.objects:
        if o.type == "MESH" and o not in keep and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    c = Vector(centre)
    d = extent * 2.2
    views = {
        "top": ((0, 0, d), True),
        "game": ((0, -d * 0.55, d * 0.85), False),
        "q34": ((d * 0.62, -d * 0.62, d * 0.55), False),
        "side": ((d, 0, 0.02), True),
        "front": ((0, -d, 0.02), True),
        "rear": ((0, d, 0.02), True),
        "under": ((d * 0.3, -d * 0.4, -d * 0.8), False),
    }
    if not under:
        views.pop("under")
    paths = {}
    for nm, (loc, ortho) in views.items():
        cd = bpy.data.cameras.new("cam")
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = extent
        else:
            cd.lens = 50
            cd.sensor_width = 36
        cam = bpy.data.objects.new("cam", cd)
        scene.collection.objects.link(cam)
        cam.location = c + Vector(loc)
        if nm == "top":
            cam.rotation_euler = (0, 0, 0)
        else:
            cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Z" if nm in ("side", "front", "rear") else "Y").to_euler()
        if not ortho:
            # fit: distance chosen so the extent fills about 80% of the frame
            cd.lens = 50 * (cam.location - c).length / (extent * 1.45)
        scene.camera = cam
        p = Path(out_dir) / f"{tag}{nm}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        paths[nm] = p
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cd)
    for o in hidden:
        o.hide_render = False
    return paths


def piece_offsets(pieces):
    return {p: ((12 + 24 * i - W / 2) * U, 0.0) for i, p in enumerate(pieces)}


def export_piece(name, obj, shell):
    data = common.load_sprite(ROOT, name)
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{name}", data["sprites"])


def main(only=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]
    review = "--review" in argv
    views_dir = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    if review or views_dir:
        SCRATCH.mkdir(parents=True, exist_ok=True)
    coll = common.reset_collection("newshk51")
    fire = build_fire(coll)
    export = []
    stack = {"assembly-newshk-17": 48, "assembly-newshk-51": 24, "assembly-newshk-89": 0}
    report = {}
    for name, pieces, *_ in FIRE:
        parts, shells, body, grid, colors = fire[name]
        tris = 0
        for p in pieces:
            tris += sum(len(q.vertices) - 2 for q in parts[p].data.polygons)
            if only in (None, name):
                export_piece(p, parts[p], shells[p])
        offs = piece_offsets(pieces)
        for p in pieces:
            parts[p].location = (offs[p][0], offs[p][1], 0)
        bpy.context.view_layer.update()
        report[name] = {"triangles": tris}
        print(f"{name}: {tris} triangles")
        if review:
            mask, index = top_samples([parts[p] for p in pieces], W, H, k=4)
            write_mask_png(SCRATCH / f"top_{name}.png", mask)
            np.save(SCRATCH / f"topidx_{name}.npy", index)
        for p in pieces:
            parts[p].location = (offs[p][0], offs[p][1] + stack[name] * U, 0)
            shells[p].location = parts[p].location
            export += [parts[p], shells[p]]
    heater = build_heater(coll)
    hshell = common.outline_shell(heater, coll, voxel=0.02, faces=3000, smooth=6, inside=0.004)
    htris = sum(len(q.vertices) - 2 for q in heater.data.polygons)
    report[HEATER] = {"triangles": htris}
    print(f"{HEATER}: {htris} triangles")
    if only in (None, HEATER):
        export_piece(HEATER, heater, hshell)
    bpy.context.view_layer.update()
    if review:
        mask, index = top_samples([heater], 24, 28, k=4)
        write_mask_png(SCRATCH / f"top_{HEATER}.png", mask)
        np.save(SCRATCH / f"topidx_{HEATER}.npy", index)
        import json
        (SCRATCH / "report.json").write_text(json.dumps(report, indent=1))
    if views_dir:
        views_dir.mkdir(parents=True, exist_ok=True)
        render_views([heater], views_dir, extent=34 * U, tag="heater_")
        objs = [o for o in export if not o.name.endswith("_outline")]
        for k in (2, 3):
            for p in FIRE[1][1]:
                src = fire["assembly-newshk-51"][0][p]
                cp = bpy.data.objects.new(f"{p}_copy{k}", src.data)
                coll.objects.link(cp)
                cp.location = (src.location.x, (src.location.y / U + (k - 1) * 24) * U, 0)
                objs.append(cp)
        bpy.context.view_layer.update()
        render_views(objs, views_dir, extent=150 * U, centre=(0, 58 * U, 0), tag="col_")


if __name__ == "__main__":
    main(only="assembly-newshk-51")
