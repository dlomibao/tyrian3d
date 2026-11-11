"""TYRIAN's fortress (map 1-9, layer 2, rows 334-378): hard-surface (D65, D141).

Silhouette and readability first: the walkway network is one family of steel deck sections that
match the tiles' outline exactly (square, as painted), each a chamfered slab with a stepped fascia
on its sides (so the deck edge reads as a girder from the tilted camera), V-grooved expansion
joints where a junction or corner meets a straight run, a low curb round every railed edge with the
art's segmented bumper rails (the bright strips, one pill per lit run, as the tiles paint them) on
it, the double row's middle divider, and the maze modelled as low ridged ribs (each lit maze line
of the art one hip-roofed rib, so the lighting paints its light and dark sides). The machine on
cells (20-21, 2-3) is a wrecked casing of red and brass armour plates with a pipe and exhaust caps
in a recessed dark core, on the rock its tiles paint. No turret mount: the art paints none, so the
deck under the enemy on cell (30, 5) stays as painted. Only texture: the model's own AO/roughness bake (no concept projection).

The machine's casing is a tub (thick stepped rim, recessed core) with chamfered red armour boxes
(inset panel, rivets), banded brass pipes with elbows, the exhaust drum and two capped domes; the rock
round it is the tiles' own (Structure.rock). No D51 outline shell (tile models draw no ink outline:
structureInstances.ts, D8, D141). Maze ribs only on
lit runs of RIB_MIN px or more (RIB_MIN_DOUBLE on the double row; triangle budget). Export contract as before (tileModels unchanged).

Build: tools/build-models.sh -j 2 assets/blender/tiles/tyrbld_fortress.py  (--no-bake
after "--" when running Blender directly, for fast geometry passes; never ship those)
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402


TW, TH = lt.TILE_W, lt.TILE_H  # 24 x 28
DECK = tb.L2_DECK  # 0.06: the walkway's top
FASCIA_Z = -0.11  # the step on the deck's sides
BOTTOM = tb.L2_SLAB_BOTTOM  # -0.30
CURB_Z = DECK + 0.03  # the low curb under the rails
RAIL_Z = DECK + 0.07  # the bumper rails' top (0.112)
RIB_MIN = 3  # px: shortest lit maze run given a rib (the art's 3-5 px runs are most of its maze)
RIB_MIN_DOUBLE = 4  # the double walkway (MID_ROWS): its 3 px dashes stay flat deck (triangle budget)
RIB_H = 0.042  # maze ribs above the deck
JOINT_CHAMFER = 0.45  # px: the deck sections' top chamfer (a V-groove where two sections meet)

# The art's indices (median of each region, highlights and shadow lines left out).
PAL_DECK, PAL_RIB, PAL_CURB, PAL_RAIL, PAL_SIDE, PAL_SIDE_LOW = 5, 5, 4, 9, 4, 3

JUNCTION = {181, 183, 184, 191, 192, 193, 194, 201}  # corners and T-junctions: each its own section
MID_ROWS = (17, 18)  # the double walkway: a divider rail between its two lanes

# The bent brass pipe through the machine's core (px, py, z).
MACHINE_PIPE = [(74.0, 578.5, 0.18), (70.8, 581.5, 0.195), (68.8, 585.0, 0.19), (67.6, 589.0, 0.17), (66.5, 593.0, 0.15)]


# --- small builders (copied, not shared: candidates for lib_l1bld) ------------------------------

def pillow(s, poly, z0, z1, mat, r_px=0.7, r_z=0.025, steps=2):
    """A closed prism over `poly` (pattern px) from z0 with a rounded top edge: straight walls to
    z1 - r_z, then `steps` inset rings on a quarter circle up to the flat top at z1. Smooth shaded
    (a bumper rail's satin sheen)."""
    pts = [(float(x), float(y)) for x, y in poly]
    if ls.area(pts) < 0:
        pts.reverse()
    rings = [(pts, z0), (pts, z1 - r_z)]
    a0 = ls.area(pts)
    for k in range(1, steps + 1):
        t = k / steps * math.pi / 2
        inner = ls.inset(pts, r_px * (1 - math.cos(t)))
        if ls.area(inner) < 0.2 * a0:
            break
        rings.append((inner, z1 - r_z + r_z * math.sin(t)))
    bm = bmesh.new()
    vr = [[bm.verts.new((s.x(x), s.y(y), z)) for x, y in ring] for ring, z in rings]
    n = len(pts)
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    bm.faces.new(vr[-1]).material_index = mat
    bm.faces.new(list(reversed(vr[0]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=True)


def bar(s, poly, z0, z1, mat, inset_px=0.55):
    """A bumper bar: walls sloping in `inset_px` from the polygon at z0 to a flat top at z1, no
    bottom (it stands on the curb); smooth shaded so it takes a satin sheen like a rounded rail."""
    pts = [(float(x), float(y)) for x, y in poly]
    if ls.area(pts) < 0:
        pts.reverse()
    inner = ls.inset(pts, inset_px)
    if ls.area(inner) < 0.15 * ls.area(pts):
        inner = ls.inset(pts, inset_px * 0.4)
    bm = bmesh.new()
    a = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in pts]
    b = [bm.verts.new((s.x(x), s.y(y), z1)) for x, y in inner]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    top = bm.faces.new(b)
    top.material_index = mat
    for f in bm.faces:
        f.normal_update()
    if top.normal.z < 0:
        for f in bm.faces:
            f.normal_flip()
    s._merge(bm, smooth=True)


def sweep_pill(s, path, hw, z0, z1, mat, inset_px=0.9):
    """A bumper rail swept along the polyline `path` [(px, py)] (pattern px): the straight pills'
    profile (walls sloping in `inset_px` from a base `hw` px either side of the path at z0 to a flat
    top at z1), mitred at each bend, flat ends, no bottom; smooth shaded (one satin rail round a
    corner instead of faceted pieces)."""
    pts = [np.array(p, float) for p in path]
    n = len(pts)
    offs = []
    for i in range(n):
        ds = []
        if i > 0:
            ds.append(pts[i] - pts[i - 1])
        if i < n - 1:
            ds.append(pts[i + 1] - pts[i])
        nrm = [np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-9) for d in ds]
        m = sum(nrm)
        m = m / max(np.hypot(*m), 1e-9)
        k = 1.0 / max(float(m @ nrm[0]), 0.5)
        offs.append(m * k)
    ti = hw - min(inset_px, hw * 0.8)
    prof = [(-hw, z0), (-ti, z1), (ti, z1), (hw, z0)]
    bm = bmesh.new()
    rings = [[bm.verts.new((s.x(p[0] + o[0] * w), s.y(p[1] + o[1] * w), z)) for w, z in prof] for p, o in zip(pts, offs)]
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((a[k], a[j], b[j], b[k])).material_index = mat
    bm.faces.new(rings[0]).material_index = mat
    bm.faces.new(list(reversed(rings[-1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # the bottom band (k = 3) was only there to close the shell for recalc: drop it
    bottoms = [f for f in bm.faces if len(f.verts) == 4 and all(abs(v.co.z - z0) < 1e-6 for v in f.verts)]
    bmesh.ops.delete(bm, geom=bottoms, context="FACES_ONLY")
    s._merge(bm, smooth=True)


def rail_rects(part):
    """Straight boxes (x0, y0, x1, y1, pattern px) covering a bright rail component: its box when it
    is a thin run, else split into its horizontal and vertical runs (an L at an inner corner), so
    every rail is a straight rounded bar, never a ragged outline (those read as sawtooth spikes)."""
    ys, xs = np.nonzero(part)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    if min(x1 - x0, y1 - y0) <= 3.5 and part[y0:y1, x0:x1].mean() >= 0.85:
        return [(x0, y0, x1, y1)]
    sub = part[y0:y1, x0:x1]
    hl = np.zeros(sub.shape, int)
    vl = np.zeros(sub.shape, int)
    for y in range(sub.shape[0]):
        for a, b in runs_1d(sub[y]):
            hl[y, a:b] = b - a
    for x in range(sub.shape[1]):
        for a, b in runs_1d(sub[:, x]):
            vl[a:b, x] = b - a
    out = []
    for m in (sub & (hl >= vl), sub & (vl > hl)):
        for yy, xx in lt.components(m):
            if len(yy) < 3:
                continue
            out.append((x0 + xx.min(), y0 + yy.min(), x0 + xx.max() + 1, y0 + yy.max() + 1))
    return out


def ribs(s, segs, z0, h, mat):
    """Hip-roofed ribs, one bmesh: each (x0, y0, x1, y1) pattern px box gets a ridge along its long
    axis (crest pulled in from the ends by half the width), sloped ends; no bottom (it sits on the
    deck). Six triangles each."""
    bm = bmesh.new()
    for x0, y0, x1, y1 in segs:
        horiz = (x1 - x0) >= (y1 - y0)
        w = (y1 - y0) if horiz else (x1 - x0)
        L = (x1 - x0) if horiz else (y1 - y0)
        e = min(w * 0.5, L * 0.5 - 0.05)
        if L <= 4.3:  # a short run: a low pyramid (4 triangles; the art's 3-4 px dashes)
            b = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            t = bm.verts.new((s.x((x0 + x1) / 2), s.y((y0 + y1) / 2), z0 + h))
            for i in range(4):
                bm.faces.new((b[i], b[(i + 1) % 4], t)).material_index = mat
            continue
        if horiz:
            cy = (y0 + y1) / 2
            crest = [(x0 + e, cy), (x1 - e, cy)]
        else:
            cx = (x0 + x1) / 2
            crest = [(cx, y0 + e), (cx, y1 - e)]
        b = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        t = [bm.verts.new((s.x(x), s.y(y), z0 + h)) for x, y in crest]
        if horiz:  # b0 top-left, b1 top-right, b2 bottom-right, b3 bottom-left (screen)
            faces = [(b[0], b[1], t[1], t[0]), (b[2], b[3], t[0], t[1]), (b[1], b[2], t[1]), (b[3], b[0], t[0])]
        else:
            faces = [(b[1], b[2], t[1], t[0]), (b[3], b[0], t[0], t[1]), (b[0], b[1], t[0]), (b[2], b[3], t[1])]
        for f in faces:
            bm.faces.new(f).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # recalc on open shells can flip: force every face's normal up
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    s._merge(bm)


def groove_lines(s, segs, z, mat):
    """Inlaid panel lines on the deck, one bmesh: each (x0, y0, x1, y1) pattern px box a flat strip
    just above the deck (2 triangles), dark and rough so it reads as a cut line."""
    bm = bmesh.new()
    for x0, y0, x1, y1 in segs:
        v = [bm.verts.new((s.x(x), s.y(y), z)) for x, y in ((x0, y0), (x0, y1), (x1, y1), (x1, y0))]
        f = bm.faces.new(v)
        f.material_index = mat
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    s._merge(bm)


def plate(s, pts, z0, z1, slope, chamfer_px, mat):
    """A raised armour plate: the polygon `pts` (pattern px) from z0 up to a tilted top (z1 at its
    centre, `slope` = dz per px right / down), with a chamfered rim (tyrbld_fortress.py's)."""
    bm = bmesh.new()
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    mx, my = s.x(cx), s.y(cy)

    def top(co):
        return z1 + slope[0] * (co.x - mx) / lt.PX - slope[1] * (co.y - my) / lt.PX

    ch = chamfer_px * lt.PX
    base = [bm.verts.new((s.x(px), s.y(py), z0)) for px, py in pts]
    face = bm.faces.new(base)
    face.normal_update()
    if face.normal.z < 0:
        face.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    for v in (g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)):
        v.co.z = top(v.co) - ch * 0.6
    tops = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.inset_region(bm, faces=tops, thickness=ch, depth=ch * 0.6, use_even_offset=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = mat
    s._merge(bm)


def tube(s, path, r_px, mat, sides=8):
    """A pipe of radius r_px along the polyline `path` [(px, py, z)], ends capped."""
    bm = bmesh.new()
    pts = [Vector((s.x(px), s.y(py), z)) for px, py, z in path]
    r = r_px * lt.PX
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = d.cross(Vector((0, 0, 1))).normalized()
        w = u.cross(d).normalized()
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * (k + 0.5) / sides) * u + math.sin(2 * math.pi * (k + 0.5) / sides) * w))
                      for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = mat
    s._merge(bm, smooth=True)


def smooth_poly(poly, tol=1.0, rounds=2, final_tol=0.45):
    """A pixel outline made a plausible machined edge: simplified (Douglas-Peucker, `tol` px), then
    Chaikin corner cutting `rounds` times (spikes become rounded corners), lightly re-simplified.
    Counter-clockwise in Blender's frame (positive ls.area)."""
    pts = ls.simplify([(float(x), float(y)) for x, y in poly], tol)
    for _ in range(rounds):
        out = []
        n = len(pts)
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            out += [(0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by), (0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by)]
        pts = out
    pts = ls.simplify(pts, final_tol)
    if ls.area(pts) < 0:
        pts.reverse()
    return pts


def ring_rim(s, poly, width_px, z0, z1, mat, chamfer_px=0.6, drop=0.015):
    """A band `width_px` wide inside the polygon, z0 to z1, as one closed ring (outer wall, top
    chamfer, flat top, inner wall): rim()'s look at a quarter of its triangles on a long outline."""
    pts = [(float(x), float(y)) for x, y in poly]
    if ls.area(pts) < 0:
        pts.reverse()
    ch = ls.inset(pts, chamfer_px)
    inner = ls.inset(pts, width_px)
    bm = bmesh.new()
    rings = [[bm.verts.new((s.x(x), s.y(y), z)) for x, y in ring] for ring, z in
             ((pts, z0), (pts, z1 - drop), (ch, z1), (inner, z1), (inner, z0))]
    n = len(pts)
    for k in range(5):
        a, b = rings[k], rings[(k + 1) % 5]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def fill_holes(mask):
    out = mask.copy()
    H, W = mask.shape
    for ys, xs in lt.components(~mask):
        if ys.min() > 0 and xs.min() > 0 and ys.max() < H - 1 and xs.max() < W - 1:
            out[ys, xs] = True
    return out


def runs_1d(row):
    """[(start, end_exclusive)] of True runs in a 1D bool array."""
    out, start = [], None
    for i, v in enumerate(list(row) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    return out


# --- the walkway ---------------------------------------------------------------------------------

def ntris(s):
    return sum(len(f.verts) - 2 for f in s.parts.faces)


def tile_kind(s):
    """(rows x cols) array of the pattern's tiles."""
    return np.array(s.pattern)


def walkway(s):
    g = s.grid
    pat = tile_kind(s)
    walk = s.cells_mask(tb.WALK) & s.footprint
    deck = s.m(PAL_DECK, roughness=0.55, metallic=0.15)
    rib = s.m(PAL_RIB, roughness=0.5, metallic=0.2)
    side = s.m(PAL_SIDE, roughness=0.65, metallic=0.1)
    side_low = s.m(PAL_SIDE_LOW, roughness=0.75, metallic=0.05)
    curb = s.m(PAL_CURB, roughness=0.55, metallic=0.25)

    # Sections: every junction/corner tile on its own, the straight runs between them as one piece
    # each (connected straight tiles). Their touching edges become V-grooved expansion joints.
    sec = np.full(pat.shape, -1, int)
    nid = 0
    for r in range(pat.shape[0]):
        for c in range(pat.shape[1]):
            if pat[r, c] in JUNCTION:
                sec[r, c] = nid
                nid += 1
    straight = np.isin(pat, list(tb.WALK - JUNCTION))
    for ys, xs in lt.components(straight):
        sec[ys, xs] = nid
        nid += 1
    polys = []
    for k in range(nid):
        cells = np.kron(sec == k, np.ones((TH, TW), bool)) & walk
        for poly in s.outlines(cells, tol=0.4, min_px=20):
            polys.append(poly)
            s.slab(poly, FASCIA_Z, DECK, deck, chamfer_px=JOINT_CHAMFER, drop=0.012, side_mat=side)
            low = ls.inset(poly, 0.9)
            s.slab(low, BOTTOM, FASCIA_Z + 0.004, side_low, chamfer_px=0)

    print("tris after deck:", ntris(s))
    # The curb along each railed edge: an edge is railed where the art paints a bright strip just
    # inside it (open map edges and the section joints are not).
    def railed(i, a, b):
        (ax, ay), (bx, by) = a, b
        L = math.hypot(bx - ax, by - ay)
        if L < 1.5:
            return False
        nx, ny = (by - ay) / L, -(bx - ax) / L  # one side's normal; test both
        vals = []
        for sgn in (1, -1):
            inside = []
            for t in np.linspace(0.1, 0.9, max(3, int(L))):
                px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                ok = True
                strip = []
                for dd in (0.5, 1.5):
                    qx, qy = int(math.floor(px + sgn * nx * dd)), int(math.floor(py + sgn * ny * dd))
                    if not (0 <= qx < s.W and 0 <= qy < s.H) or not walk[qy, qx]:
                        ok = False
                        break
                    strip.append(g[qy, qx])
                if ok:
                    inside.append(max(strip))
            vals.append(inside)
        inside = max(vals, key=len)
        if len(inside) < 0.6 * max(3, int(L)):
            return False
        # an interior joint has walkway on both sides
        out = vals[1] if inside is vals[0] else vals[0]
        if len(out) > 0.5 * len(inside):
            return False
        return float(np.mean(np.array(inside) >= 7)) > 0.3

    for poly in polys:
        pts = [(float(x), float(y)) for x, y in poly]
        if ls.area(pts) < 0:
            pts.reverse()
        n = len(pts)
        keep = [railed(i, pts[i], pts[(i + 1) % n]) for i in range(n)]
        inner = ls.inset(pts, 2.0)
        for i in range(n):
            if not keep[i]:
                continue
            j = (i + 1) % n
            a, b = pts[i], pts[j]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
            if (inner[i][0] - a[0]) * nx + (inner[i][1] - a[1]) * ny < 0:
                nx, ny = -nx, -ny
            # mitre only towards railed neighbours: square ends next to an open edge or a joint
            q3 = inner[i] if keep[(i - 1) % n] else (a[0] + 2.0 * nx, a[1] + 2.0 * ny)
            q2 = inner[j] if keep[j] else (b[0] + 2.0 * nx, b[1] + 2.0 * ny)
            q = [a, b, q2, q3]
            s.slab(q, DECK - 0.01, CURB_Z, curb, chamfer_px=0)

    print("tris after curb:", ntris(s))
    # The divider between the double row's lanes (rows 17-18), where both lanes are straight.
    r0, r1 = MID_ROWS
    ymid = r1 * TH
    for c0, c1 in runs_1d([straight[r0, c] and straight[r1, c] for c in range(pat.shape[1])]):
        x0, x1 = c0 * TW + (0 if c0 == 0 else 1.5), c1 * TW - (0 if c1 == pat.shape[1] else 1.5)
        s.slab(s.rounded_box(x0, ymid - 3, x1, ymid + 2, 0.8, 1), DECK - 0.01, CURB_Z, curb, chamfer_px=0)

    print("tris after divider:", ntris(s))
    # The corner tiles' rails turn round a fillet (the art's curved shadow line inside the bright
    # corner): one swept pill along the arc with a gusset plate filling the corner behind it. Their
    # zone is left out of the straight pills below.
    corners = {183: (-1, -1), 184: (1, -1), 193: (-1, 1), 194: (1, 1)}  # which corner, screen x/y
    E, R, RUN = 1.0, 8.0, 4.0  # rail centre in from the edges, arc radius, straight lead-in (px)
    corner_zone = np.zeros_like(walk)
    gusset_mat = s.m(8, roughness=0.5, metallic=0.35)
    for (r, c), kind in np.ndenumerate(pat):
        if kind not in corners:
            continue
        sx, sy = corners[kind]
        cx0 = (c + (1 if sx > 0 else 0)) * TW
        cy0 = (r + (1 if sy > 0 else 0)) * TH

        def at(u, v):  # u along x, v along y, measured into the tile from its outer corner
            return (cx0 - sx * u, cy0 - sy * v)

        lim = E + R + RUN
        xs_ = sorted((cx0, cx0 - sx * lim))
        ys_ = sorted((cy0, cy0 - sy * lim))
        corner_zone[int(ys_[0]):int(math.ceil(ys_[1])), int(xs_[0]):int(math.ceil(xs_[1]))] = True
        arc = [at(E + R - R * math.sin(math.pi / 2 * k / 8), E + R - R * math.cos(math.pi / 2 * k / 8)) for k in range(9)]
        path = [at(lim, E)] + arc + [at(E, lim)]
        idx = int(np.clip(np.median(g[corner_zone & s.cells_mask(cells=[(r, c)]) & (g >= 0)]), 7, 9))
        # the gusset: the corner behind the arc, a low plate under the rail
        gus = [at(0, 0), at(E + R + 0.6, 0), at(E + R + 0.6, E)] + arc[1:-1] + [at(E, E + R + 0.6), at(0, E + R + 0.6)]
        s.slab(gus, DECK - 0.01, CURB_Z + 0.006, gusset_mat, chamfer_px=0)
        sweep_pill(s, path, 0.94, CURB_Z - 0.006, RAIL_Z, rail_mats(s, idx), inset_px=0.8)

    print("tris after fillets:", ntris(s))
    # The straight bumper rails: one rounded bar per bright run the art paints along a railed edge
    # (a straight box per run, split at inner corners), in the run's own index: the dim grey lumps of
    # the vertical walkways' left rail (8) lower than the bright pills (9).
    d = edge_depth(s, walk)
    mid = np.zeros_like(walk)
    mid[ymid - 3:ymid + 2, :] = True
    mid &= walk & np.kron(straight, np.ones((TH, TW), bool))
    zone = ((d <= 3) | mid) & walk & ~corner_zone
    bright = zone & (g >= 8) & (g < 16)
    seg = lb.close(bright, 1) & zone
    seg = lb.drop_small(seg, 3)
    npill = 0
    for ys, xs in lt.components(seg):
        if len(ys) < 3:
            continue
        part = np.zeros_like(seg)
        part[ys, xs] = True
        for x0, y0, x1, y1 in rail_rects(part):
            w, h = x1 - x0, y1 - y0
            if max(w, h) < 2:
                continue
            ix0, ix1, iy0, iy1 = int(x0), int(math.ceil(x1)), int(y0), int(math.ceil(y1))
            if w < 1.6:  # widen a 1 px run to 1.6 px towards the deck, never off the walkway
                if ix0 - 1 >= 0 and walk[iy0:iy1, ix0 - 1].all():
                    x0 = x1 - 1.6
                elif ix1 < s.W and walk[iy0:iy1, ix1].all():
                    x1 = x0 + 1.6
            if h < 1.6:
                if iy0 - 1 >= 0 and walk[iy0 - 1, ix0:ix1].all():
                    y0 = y1 - 1.6
                elif iy1 < s.H and walk[iy1, ix0:ix1].all():
                    y1 = y0 + 1.6
            x0, y0, x1, y1 = x0 + 0.06, y0 + 0.06, x1 - 0.06, y1 - 0.06  # off the walkway's edge line
            box = (slice(int(y0), int(math.ceil(y1))), slice(int(x0), int(math.ceil(x1))))
            idx = int(np.clip(np.median(g[box]), 7, 9))
            top = RAIL_Z if idx >= 9 else RAIL_Z - 0.014
            ins = min(1.0, 0.42 * min(x1 - x0, y1 - y0))
            bar(s, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], CURB_Z - 0.006, top, rail_mats(s, idx), inset_px=ins)
            npill += 1

    print("tris after rails:", ntris(s))
    # The maze: a rib on every lit run (index 6-7) of the deck's inner part, ridged so the scene's
    # light paints its light and dark sides as the art does.
    inner_deck = walk & (d > 3) & ~lb.dilate(mid, 1)
    lit = inner_deck & ((g == 6) | (g == 7))
    def merged(runs):  # join runs in the same line split by a one-pixel gap
        out = []
        for a, b in [r for r in runs if r[1] - r[0] >= 2]:
            if out and a - out[-1][1] <= 1:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
        return out

    hruns = [(y, a, b) for y in range(s.H) for a, b in merged(runs_1d(lit[y])) if b - a >= 2]
    vruns = [(x, a, b) for x in range(s.W) for a, b in merged(runs_1d(lit[:, x])) if b - a >= 2]
    dy0, dy1 = MID_ROWS[0] * TH, (MID_ROWS[1] + 1) * TH
    def rib_min(y):  # y: the run's (first) pattern row
        return RIB_MIN_DOUBLE if dy0 <= y < dy1 else RIB_MIN
    long_h = np.zeros_like(lit)
    long_v = np.zeros_like(lit)
    for y, a, b in hruns:
        if b - a >= rib_min(y):
            long_h[y, a:b] = True
    for x, a, b in vruns:
        if b - a >= rib_min(a):
            long_v[a:b, x] = True
    segs = []
    covered = np.zeros_like(lit)
    for y, a, b in hruns:  # a 2 px run that is only the turn of a longer perpendicular rib: skip
        if b - a >= rib_min(y):
            segs.append((a - 0.1, y + 0.1, b + 0.1, y + 1.9))
            covered[max(0, y - 1):y + 3, max(0, a - 1):b + 1] = True
    for x, a, b in vruns:
        if b - a >= rib_min(a):
            segs.append((x + 0.1, a - 0.1, x + 1.9, b + 0.1))
            covered[max(0, a - 1):b + 1, max(0, x - 1):x + 3] = True
    print(f"maze: {len(segs)} lit ribs")
    ribs(s, segs, DECK - 0.004, RIB_H, rib)
    print("tris after ribs:", ntris(s))
    # The art's other maze lines: dark runs (4) that are not a rib's own shadow side are inlaid
    # panel lines, a shallow V-groove strip each (the maze at the art's density).
    dark = inner_deck & (g == 4) & ~covered
    grooves = []
    for y in range(s.H):
        for a_, b_ in runs_1d(dark[y]):
            if b_ - a_ >= 3:
                grooves.append((a_ + 0.05, y + 0.12, b_ - 0.05, y + 0.88))
    for x in range(s.W):
        for a_, b_ in runs_1d(dark[:, x]):
            if b_ - a_ >= 3:
                grooves.append((x + 0.12, a_ + 0.05, x + 0.88, b_ - 0.05))
    # plain (unbaked): strips under a texel wide come out black from the bake
    groove_lines(s, grooves, DECK + 0.0025, s.m(PAL_SIDE, roughness=0.85, metallic=0.05, plain=True))
    global N_GROOVE_TRIS
    N_GROOVE_TRIS = 2 * len(grooves)
    print(f"maze: {len(grooves)} panel lines; tris after grooves:", ntris(s))
    print(f"walkway: {len(polys)} deck sections, {npill} rails, {len(segs)} maze ribs")
    return walk


def rail_mats(s, idx):
    """The bumper rails' satin steel in the art's index (rougher than a mirror: no glints)."""
    return s.m(idx, roughness=0.42 if idx >= 9 else 0.5, metallic=0.45 if idx >= 9 else 0.35)


def edge_depth(s, walk):
    """Chessboard px distance from the walkway's edge, the map's left/right edges open (the walkway
    runs on off the map there)."""
    pad = 5
    big = np.pad(walk, pad)
    big[pad:-pad, :pad] = walk[:, :1]
    big[pad:-pad, -pad:] = walk[:, -1:]
    return lb.depth(big, limit=8)[pad:-pad, pad:-pad]


# --- the machine ---------------------------------------------------------------------------------

def armour(s, poly, z0, z1, mat, panel_mat, bolt_mat, chamfer=1.0, rivets=True):
    """A chamfered armour box with an inset top panel and rivets at its corners."""
    s.slab(poly, z0, z1, mat, chamfer_px=chamfer, drop=0.018)
    inner = ls.inset([(float(x), float(y)) for x, y in (poly if ls.area(poly) > 0 else list(reversed(poly)))], chamfer + 0.7)
    if len(inner) >= 3 and ls.area(inner) > 4:
        s.slab(inner, z1 - 0.012, z1 + 0.010, panel_mat, chamfer_px=0.25, drop=0.005)
        if rivets and ls.area(inner) > 14:
            s.bolts([(x, y) for x, y in ls.inset(inner, 0.7)][:4], z1 + 0.008, r_px=0.45, height=0.012, mat=bolt_mat)


def pipe_run(s, path, r_px, mat, band_mat, bands=(0.5,), sides=8):
    """A pipe along `path` [(px, py, z)] with fatter bands along each straight run and a collar
    at each elbow (the art's banded brass pipes)."""
    tube(s, path, r_px, mat, sides=sides)
    for a, b in zip(path, path[1:]):
        for t in bands:
            c = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            d = (b[0] - a[0], b[1] - a[1])
            L = math.hypot(*d) or 1.0
            u = (d[0] / L * 0.45, d[1] / L * 0.45)
            tube(s, [(c[0] - u[0], c[1] - u[1], c[2]), (c[0] + u[0], c[1] + u[1], c[2])], r_px * 1.3, band_mat, sides=sides)
    for p in path[1:-1]:
        s.dome(p[0], p[1], r_px * 1.25, r_px * 1.25, p[2] - r_px * lt.PX * 0.2, r_px * lt.PX * 1.4, band_mat, sides=8, rings=2)


def machine(s):
    cells = s.cells_mask(tb.MACHINE)
    g = s.grid
    ramp = np.maximum(g, 0) >> 4
    # brass 160-167 only: 168-172 are the rock's tan pebbles (the top corners, the bottom left)
    seed = cells & (g >= 0) & (np.isin(ramp, (1, 4)) | ((g >= 160) & (g <= 167)))
    m = lb.close(lb.open_((seed | (cells & (g >= 0) & (g <= 3))), 1), 1)
    body = np.zeros_like(m)
    for ys, xs in lt.components(m):
        if len(ys) > 60 and seed[ys, xs].any():
            body[ys, xs] = True
    body = fill_holes(body) & cells
    red_i = s.dominant(body & (ramp == 4))
    brass_i = s.dominant(body & (g >= 160) & (g <= 167))
    tan_i = s.dominant(body & (ramp == 1) & (g >= 20))  # the exhaust drum's lit tan (22-28)
    dark_i = s.dominant(body & (g >= 0) & (g <= 3))
    print(f"machine indices: red {red_i}, brass {brass_i}, tan {tan_i}, dark {dark_i}")
    casing = s.m(2, roughness=0.6, metallic=0.35)
    core = s.m(dark_i if dark_i is not None else 1, roughness=0.8, metallic=0.2)
    red = s.m(red_i, metallic=0.35, roughness=0.42)
    red_hi = s.m(red_i + 1, metallic=0.4, roughness=0.36)
    red_dark = s.m(max(64, red_i - 3), metallic=0.35, roughness=0.5)
    brass = s.m(brass_i, metallic=0.55, roughness=0.38)
    brass_dark = s.m(max(160, brass_i - 2), metallic=0.5, roughness=0.45)
    bolt = s.m(8, metallic=0.6, roughness=0.35)

    # The casing, a tub milled from one dark block: a thick rim wall with a stepped inner lip down
    # to the recessed core floor.
    # The outline is smoothed first (simplified at 1 px, then rounded by corner cutting) so the
    # rim's inset never folds the pixel staircase into star points.
    for poly in s.outlines(body, tol=1.0, min_px=40):
        poly = smooth_poly(poly)
        s.slab(poly, -0.04, 0.085, core, chamfer_px=0)
        ring_rim(s, poly, 2.2, -0.04, 0.15, casing, chamfer_px=0.6, drop=0.015)
        lip = smooth_poly(ls.inset(poly, 2.2), tol=0.4, rounds=1)
        if len(lip) >= 3 and ls.area(lip) > 0:
            ring_rim(s, lip, 1.0, 0.07, 0.118, casing, chamfer_px=0.3, drop=0.008)
    s.slab(s.rounded_box(60, 588.5, 70, 590.7, 0.5, 1), 0.08, 0.12, casing, chamfer_px=0.4, drop=0.01)
    s.slab(s.rounded_box(73, 589, 75.2, 600, 0.5, 1), 0.08, 0.115, casing, chamfer_px=0.4, drop=0.01)
    # Red armour (art positions): chamfered boxes, an inset top panel and rivets, highest.
    armour(s, [(51, 568), (52, 567), (58, 567), (58, 576), (51, 576)], 0.10, 0.29, red, red_hi, bolt, 1.0)
    armour(s, [(58.6, 567), (64.5, 567), (65, 568), (65, 571), (58.6, 571)], 0.10, 0.275, red, red_hi, bolt, 0.8, rivets=False)
    armour(s, s.rounded_box(69.5, 568, 76.2, 576.2, 0.8), 0.10, 0.30, red, red_hi, bolt, 1.0)
    armour(s, [(70, 576.2), (83.2, 576.2), (83.2, 588), (81, 588), (81, 578.2), (70, 578.2)], 0.10, 0.24, red_dark, red, bolt, 0.45, rivets=False)
    armour(s, [(61, 599), (67, 598.6), (68.5, 600.5), (71.5, 603), (70.5, 606.4), (61.4, 606.4)], 0.10, 0.28, red, red_hi, bolt, 1.0)
    armour(s, s.rounded_box(63.5, 584.5, 67.5, 587.5, 0.6), 0.10, 0.19, red_dark, red, bolt, 0.5, rivets=False)
    s.slab(s.rounded_box(53, 562, 55.4, 567.5, 0.5), 0.10, 0.24, red_dark, chamfer_px=0.4, drop=0.01)
    # Brass: bars, the left L frame, the post, the band along the top.
    for poly, z1, mat, ch in (
        (s.rounded_box(58.6, 571.6, 61.6, 577, 0.5), 0.215, brass, 0.4),
        (s.rounded_box(78.6, 566.6, 81.2, 576, 0.5), 0.235, brass, 0.5),
        (s.rounded_box(83.4, 580.5, 86.4, 588, 0.6), 0.20, brass_dark, 0.5),
        (s.rounded_box(63, 563.6, 76.5, 565.8, 0.5), 0.20, brass, 0.4),
        ([(48.2, 576.6), (59, 576.6), (59, 579.2), (51, 579.2), (51, 592), (48.2, 592)], 0.21, brass_dark, 0.5),
        (s.rounded_box(54, 585.5, 58, 590, 0.6), 0.18, brass, 0.5),
    ):
        s.slab(poly, 0.10, z1, mat, chamfer_px=ch, drop=0.018)
    # The exhaust drum at the lower left: a fat horizontal-ish cylinder lying north-south with
    # flanged ends and a strap (art px 52-60, y 590-605).
    # The art paints it dark brown, index 163 (48,32,16) over px 55-60, y 594-606 (median RGB about
    # (56,38,24)), with one lit tan streak (22-28): that streak is the light's sheen on the curve
    # (rubric: highlights are sheen), so the whole barrel is satin dark brass, no tan paint.
    drum_box = s.box_mask(55, 594, 61, 607)
    drum_i = s.dominant(body & drum_box & (g >= 160) & (g <= 167))
    print(f"drum index {drum_i}")
    barrel = s.m(drum_i if drum_i is not None else 163, metallic=0.4, roughness=0.56)
    cap = s.m(161, metallic=0.4, roughness=0.55)
    flange = s.m(165, metallic=0.45, roughness=0.5)  # the art's flange and strap rows are 164-165
    tube(s, [(57.5, 594.5, 0.075), (57.5, 606.0, 0.075)], 2.6, barrel, sides=12)
    for y in (594.0, 606.4):
        tube(s, [(57.5, y - 0.3, 0.075), (57.5, y + 0.3, 0.075)], 2.9, flange, sides=12)
    tube(s, [(57.5, 599.6, 0.075), (57.5, 600.6, 0.075)], 2.85, flange, sides=12)
    for y0, y1 in ((593.4, 593.75), (606.75, 607.1)):
        tube(s, [(57.5, y0, 0.075), (57.5, y1, 0.075)], 2.2, cap, sides=12)
    # Banded pipe runs with elbows through the core (the old pipe, and a shorter branch).
    pipe_run(s, [(74.0, 578.5, 0.17), (70.8, 581.5, 0.18), (68.8, 585.0, 0.178), (67.6, 589.0, 0.165), (66.5, 593.0, 0.15)], 1.3, brass, brass_dark)
    pipe_run(s, [(79.0, 580.5, 0.16), (79.0, 586.5, 0.16), (84.0, 586.5, 0.14)], 0.9, brass_dark, brass, bands=(0.5,))
    # The brass drum in the core, under the pipe.
    s.slab(s.ngon(74.5, 583.5, 3.4, 10), 0.08, 0.19, brass, chamfer_px=0.6, drop=0.015)
    s.slab(s.ngon(74.5, 583.5, 2.0, 10), 0.18, 0.205, brass_dark, chamfer_px=0.4, drop=0.01)
    # (No domes on the top edge: the art's tan stubs there are the rock's pebbles, 168-171.)
    s.bolts([(53, 574), (56.5, 574)], 0.29, r_px=0.5, height=0.012, mat=bolt)
    # Rock round it, the tiles' own (the light-grey square plate is this relief).
    s.rock(cells=[(r, c) for r in (20, 21) for c in (2, 3)], exclude=lb.dilate(body, 1), cut=body)
    return body


# --- build ---------------------------------------------------------------------------------------

def tri_count(objects, plain=False):
    n = 0
    for o in objects:
        if o.type != "MESH":
            continue
        for p in o.data.polygons:
            m = o.data.materials[p.material_index] if o.data.materials else None
            if bool(m and m.get("tyrian_plain")) == plain:
                n += len(p.vertices) - 2
    return n


def build(bake=True, preview=None):
    s = tb.Structure("fortress")
    walk = walkway(s)
    body = machine(s)
    objects = s.objects()
    s.check(objects)
    own = walk | body
    iou = s.top_iou(objects, own)
    cov = s.coverage(objects, scale=1)
    ious = {}
    for name, m, box in (("walk", walk, None), ("machine", body, (48, 560, 96, 616))):
        ref = m.copy()
        c = cov.copy()
        if box:
            x0, y0, x1, y1 = box
            sel = np.zeros_like(ref)
            sel[y0:y1, x0:x1] = True
            ref &= sel
            c &= sel
        else:
            c &= ~s.cells_mask(tb.MACHINE)
        ious[name] = (ref & c).sum() / max(1, (ref | c).sum())
        print(f"IoU {name}: {ious[name]:.4f} (model only {(c & ~ref).sum()}, art only {(ref & ~c).sum()})")
    np.save(SCRATCH / "coverage.npy", cov)
    print(f"triangles (no rock): {tri_count(objects)} + {N_GROOVE_TRIS} plain maze lines; rock {tri_count(objects, True) - N_GROOVE_TRIS}")
    if bake:
        objects = s.bake_model(objects, size=2048)
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / "shapesz-tyrbld-fortress.png", view_px=480)
    s.export(objects, baked=bake)
    print(f"IoU all {iou:.4f}")


N_GROOVE_TRIS = 0
SCRATCH = Path("/Users/dlomibao/projects/tyrian-scratch/structures-1/tyrbld_fortress/final")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
