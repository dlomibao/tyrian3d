"""GRYPHON neck and collar (level 2.6 end boss), design B: silhouette and readability from the small
tilted game camera first, then detail. newsh0.shp assembly of two pieces (newsh0-91 | newsh0-93,
48 x 28 px), rigid on the same link as the D170 wings/skull (assembly-newsh0-79, drawn over the
middle of its lower row) and the red-eyed head newsh0-119 (dy +28, directly below).

What it is: the beast's neck seen from above, flying down the screen. A pale beaded dorsal spine
down the middle in a dark tendon channel; a blue crest horn each side sweeping back (up the
screen) and rising to its point; a grey blade standing between each horn and the spine; three grey
collar feathers fanning out each side (upper, middle, lower: separated by dark gaps); and the
mottled, scaled collar of the body across the bottom, running on into the head.

Readability (tilted camera): the horn tips and blades rise well above the neck, the three feathers
on each side are separate blades with real dark steps between them and droop a little toward their
tips (a fan, not a plate), the spine is a row of vertebra beads, the collar a domed mass of scales.

Fix round 1: no dark backing plate. Each grey band is a feather fan: a smooth shingled body whose
edges are elliptic (round leading edge, thin tip; blurred distance field, no crinkle) and whose root
runs on under the horn into the neck (no air gap), carrying three tapered blades that radiate from
the root (the D170 shell's ribs). Horn and blade tip stations are faired into one monotone cubic
(no per-row zigzag). Collar: flat shingled scales lying down the neck, no thin grafts (its own edge
covers the row-23 corner pixel), and the run-on rounds in plan and profile into the cap.

Fix round 2: the three tiers each side are one thin feather sheet (sawtooth along r: crest, lit
slope, a dark dive face on the sprite's dark rows 12 / 17 that the tilted camera looks into),
tapering to a knife edge at the outline, upper tips swept up, lower drooping, diagonal barb grooves,
its root faired down into the neck (no slot). The spine is one continuous keeled ridge with soft
vertebra steps; the horns are slim hooks (dark fan root shows as the ink gap beside them); the
collar is a dome whose top curves down and forward into the head over a U-shaped belly, its run-on
an analytic half ellipse in plan; the neck core's back end is rounded.

QA round 2 (E2 QA sweep; this script replaces D177's older lib_b025 build): the feather tiers are fans
of quills, one lanceolate blade per sprite row whose pointed tips make each tier's stepped outer edge,
radiating from the root, shingled (north on top) and cascading down toward the head, dark recessed
webs on the sprite's dark rows 12 / 17; they rise from the neck into the horn roots (no slot under
the horns). The outline shell is built from a proxy in which each tier is one smooth envelope (the
quills' own remesh broke into ink shards). The grey blades are faired tables with a monotone width
from a blunt rounded point (no bulb); horns and blades stand lower. The collar is a round dome whose
belly leaves the side line vertically (no crease, no straight skirt) with low faired scale rows.

QA round 3: no stacked quills. Each tier is one swept feather fan: a single loft with the pchip
outline, a constant rounded chamfer and a monotone section, pleated by four flutes that run straight
from a root bunched at the tier's south-inner corner (under the horn) to pointed tips along the
serrated outer edge (the loft's grid follows the ribs, so the folds shade clean; the grooves are a
step darker), and sweeping up toward the tip (upper tier most), so the quills point up and out and
splay. The dark webs are thin level strips tucked under the fans (no slab ends). The blades are slim
C-curved knives whose width rises monotonically from a blunt point. The collar is a lower elliptic
dome on a higher side line over a tucked belly, with rows of staggered flat-topped scale plates and
darker seams, ramping down to a thin lip at the box edge; the neck core's belly is higher (no tub).

Each side is built from its own sprite pixels (the sprite is not mirror-exact). Every part's top
view comes from the sprite's inner mask (D74) and its region map. Underside: one closed round belly.

Units: c, r = assembly px (pixel c spans [c, c + 1]); Blender X = (c - 24) / 12, Y = (14 - r) / 12
(the assembly centre is the origin; newsh0-91 is X < 0), z px / 12 up, same scale as D170 (its
skull top is z 13 px).

Run: blender --background --python assembly-newsh0-91.py -- [--no-export] [--out x.glb] [--review DIR]
Exports both pieces (each with its outline shell) through export_sprite_model; --no-export skips that, --out
writes one scratch GLB with both pieces in place.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh0-91"
PIECES = ["newsh0-91", "newsh0-93"]
CX0, CY0 = 126, -17  # the assembly centre in screen px (layout cx 114 / 138, cy -17)
AXIS = 24.5          # the sprite's visual centre line (the spine column 24)
W, H = 48, 28


def X(c):
    return (c - 24) / 12


def Y(r):
    return (14 - r) / 12


def CR(v):
    return v.x * 12 + 24, 14 - v.y * 12


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def compose_sprite():
    idx = -np.ones((H, W), int)
    cols = {}
    for k, name in enumerate(PIECES):
        s = common.load_sprite(ROOT, name)
        cols.update({int(a): tuple(b) for a, b in s["colors"].items()})
        idx[:, 24 * k:24 * k + 24] = np.array(s["frames"][0]["pixels"])
    return idx, cols


IDX, COLORS = compose_sprite()
MASKS = SM.masks(IDX.tolist(), COLORS)
INNER = np.array(MASKS["inner"], bool)
F = INNER | np.array(MASKS["free"], bool)

# Region map (blueprint labels, one char per sprite px): h horn, b blade, s slot (dark channel),
# e spine, u / m / l upper / middle / lower collar feather, c collar (body).
REGION = [
    ".....................b.....b....................",
    "..................h.bbb...bbb.h.................",
    ".................hhbbbb..bbbbbhh................",
    ".................hhhbbss.sbbhhhhh...............",
    "................hhhhbbssehbbbhhhh...............",
    "................hhhhbbbsesbbhhhhh...............",
    "................hhhhhbbsesbbhhhhh...............",
    "......uuuuuuuuu.hhhhhhbsesbhhhhhhhuuuuuuuuu.....",
    "......uuuuuuuuuhhhhhhhbsesshhhhhhhuuuuuuuuu.....",
    ".......uuuuuuuuuuhhhhhhseshhhhhhuuuuuuuuuu......",
    ".........uuuuuuuuuhhhhhseshhhhhuuuuuuuuu........",
    "..........uuuuuuuuhhhhhheshhhhhuuuuuuu..........",
    ".........uuuuuuuuuubshhseshhbbuuuuuuuuuu........",
    "........mmmmmmmmmmmmshseesshsmmmmmmmmmmmm.......",
    ".......mmmmmmmmmmmmmshseeeshsmmmmmmmmmmmmm......",
    "......mmmmmmmmmmmmmmshseeeshsmmmmmmmmmmmmmm.....",
    "......mmmmmmmmmmmmmmshseeeshsmmmmmmmmmmmmmm.....",
    ".......mmmmmmmmmmmmmhhheeeshhmmmmmmmmmmmmm......",
    ".......lllllllllllllhhheeeshhlllllllllllll......",
    "........llllllllllllhhhseehhhllllllllllll.......",
    ".........lllllllllllhhhseehhhhllllllllll........",
    "..........llllllllhlhhheeehhhhhllllllll.........",
    "...........lllcchhhlhhheeehhhhhhhlllll..........",
    "............ccccccccccceeeccccccccccc...........",
    ".............cccccccccceeecccccccccc............",
    "............ccccccccccceeeccccccccccc...........",
    "............ccccccccccceeeccccccccccc...........",
    "............ccccccccccceeeccccccccccc...........",
]
REG = np.array([list(r) for r in REGION])
CC, RR = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
LEFT = CC < AXIS

SUB = 3
PAD = 4
# ---- helpers copied from assembly-newsh0-79.py (D170) ----
def smooth_field(mask, sigma_px=0.5):
    big = np.kron(np.pad(mask.astype(np.float32), PAD), np.ones((SUB, SUB), np.float32))
    s = sigma_px * SUB
    k = np.arange(-int(3 * s) - 1, int(3 * s) + 2)
    g = np.exp(-0.5 * (k / s) ** 2)
    g /= g.sum()
    big = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 0, big)
    big = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 1, big)
    return big


def lattice_cr(i, j):
    return (j + 0.5) / SUB - PAD, (i + 0.5) / SUB - PAD


def field_at(field, c, r):
    x = (c + PAD) * SUB - 0.5
    y = (r + PAD) * SUB - 0.5
    j, i = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - j, y - i
    hgt, wid = field.shape
    i, j = max(0, min(hgt - 2, i)), max(0, min(wid - 2, j))
    return ((1 - fx) * (1 - fy) * field[i, j] + fx * (1 - fy) * field[i, j + 1]
            + (1 - fx) * fy * field[i + 1, j] + fx * fy * field[i + 1, j + 1])


def _chamfer(ins):
    hgt, wid = ins.shape
    big = 10 ** 6
    d = np.where(ins, big, 0).astype(np.int64)
    for i in range(hgt):
        row, prev = d[i], d[i - 1] if i > 0 else None
        for j in range(wid):
            if row[j]:
                m = row[j]
                if prev is not None:
                    m = min(m, prev[j] + 3)
                    if j > 0:
                        m = min(m, prev[j - 1] + 4)
                    if j + 1 < wid:
                        m = min(m, prev[j + 1] + 4)
                if j > 0:
                    m = min(m, row[j - 1] + 3)
                row[j] = m
    for i in range(hgt - 1, -1, -1):
        row, nxt = d[i], d[i + 1] if i + 1 < hgt else None
        for j in range(wid - 1, -1, -1):
            if row[j]:
                m = row[j]
                if nxt is not None:
                    m = min(m, nxt[j] + 3)
                    if j > 0:
                        m = min(m, nxt[j - 1] + 4)
                    if j + 1 < wid:
                        m = min(m, nxt[j + 1] + 4)
                if j + 1 < wid:
                    m = min(m, row[j + 1] + 3)
                row[j] = m
    return d / 3.0 / SUB


def contour_loops(field, tol=0.08):
    """Closed contour loops ((c, r) px) of field = 0.5 (marching squares, Douglas-Peucker)."""
    hgt, wid = field.shape
    ins = field >= 0.5

    def pos(key):
        kind, i, j = key
        a = (i, j)
        bq = (i, j + 1) if kind == "h" else (i + 1, j)
        fa, fb = field[a], field[bq]
        t = (0.5 - fa) / (fb - fa)
        ca, ra = lattice_cr(*a)
        cb, rb = lattice_cr(*bq)
        return (ca + (cb - ca) * t, ra + (rb - ra) * t)

    adj = {}

    def seg(a, bq):
        adj.setdefault(a, []).append(bq)
        adj.setdefault(bq, []).append(a)

    for i in range(hgt - 1):
        for j in range(wid - 1):
            fl = (ins[i, j], ins[i, j + 1], ins[i + 1, j + 1], ins[i + 1, j])
            k = sum(fl)
            if k == 0 or k == 4:
                continue
            E = [("h", i, j), ("v", i, j + 1), ("h", i + 1, j), ("v", i, j)]
            cross = [e for e in range(4) if fl[e] != fl[(e + 1) % 4]]
            if len(cross) == 2:
                seg(E[cross[0]], E[cross[1]])
            else:
                centre = field[i:i + 2, j:j + 2].mean() >= 0.5
                if fl[0]:
                    if centre:
                        seg(E[0], E[1]); seg(E[2], E[3])  # noqa: E702
                    else:
                        seg(E[3], E[0]); seg(E[1], E[2])  # noqa: E702
                else:
                    if centre:
                        seg(E[3], E[0]); seg(E[1], E[2])  # noqa: E702
                    else:
                        seg(E[0], E[1]); seg(E[2], E[3])  # noqa: E702
    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        if len(loop) >= 3:
            loops.append([pos(k) for k in loop])
    return [dp_closed(lp, tol) for lp in loops]


def dp_closed(pts, tol):
    n = len(pts)
    if n < 6:
        return pts
    far = max(range(n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)

    def dp(seq):
        if len(seq) < 3:
            return seq
        (x0, y0), (x1, y1) = seq[0], seq[-1]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        best, bi = -1, 0
        for i in range(1, len(seq) - 1):
            d = abs(dy * (seq[i][0] - x0) - dx * (seq[i][1] - y0)) / ln
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [seq[0], seq[-1]]
        return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])

    a = dp(pts[:far + 1])
    b = dp(pts[far:] + [pts[0]])
    return a[:-1] + b[:-1]



LENS = [(1, 0), (0.6, 0.55), (0, 1.0), (-0.6, 0.55), (-1, 0), (-0.5, -0.45), (0.5, -0.45)]
ROUND8 = [(math.cos(2 * math.pi * (k + 0.5) / 8), math.sin(2 * math.pi * (k + 0.5) / 8)) for k in range(8)]
ROUND10 = [(math.cos(2 * math.pi * (k + 0.5) / 10), math.sin(2 * math.pi * (k + 0.5) / 10)) for k in range(10)]
ROUND6 = [(math.cos(2 * math.pi * (k + 0.5) / 6), math.sin(2 * math.pi * (k + 0.5) / 6)) for k in range(6)]


def sweep(bm, path, section, mat, smooth=True):
    """A tube along path [(c, r, z_px, half_width_px, half_height_px)], section [(u, v)] in the
    ring plane (u across the path in XY, v up). A ring of zero size is a point."""
    if len(path) < 2:
        return []
    pts = [Vector((X(c), Y(r), z / 12)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w <= 1e-6 and h <= 1e-6:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (u * w / 12) + up * (v * h / 12)) for u, v in section])
    n = len(section)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            try:
                faces.append(bm.faces.new(f))
            except ValueError:
                pass
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        if len(ring) > 1:
            try:
                faces.append(bm.faces.new(list(reversed(ring)) if rev else ring))
            except ValueError:
                pass
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def ellipsoid(bm, c, r, z, rx, ry, rz, mat, seg=12, rings=6, zmin=None):
    before = set(bm.verts)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        zz = z + v.co.z * rz
        if zmin is not None:
            zz = max(zz, zmin)
        v.co = Vector((X(c) + v.co.x * rx / 12, Y(r) + v.co.y * ry / 12, zz / 12))
    for f in {f for v in set(bm.verts) - before for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


def relief_plate(bm, loop, top_fn, bot_fn, step, mat_fn):
    """A plate over the closed (c, r) loop, cut into a step x step px grid; its top follows
    top_fn(c, r) and its bottom bot_fn(c, r) (px). mat_fn(c, r, top) picks each face's material."""
    old_v, old_e, old_f = set(bm.verts), set(bm.edges), set(bm.faces)
    pts = [(X(c), Y(r)) for c, r in loop]
    ar = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if ar < 0:
        pts = pts[::-1]
    common.slab(bm, pts, 1.0, z=0.0)

    def new_geom():
        return ([v for v in bm.verts if v not in old_v] + [e for e in bm.edges if e not in old_e]
                + [f for f in bm.faces if f not in old_f])

    cs = [c for c, _ in loop]
    rs = [r for _, r in loop]
    c = math.floor(min(cs)) + step
    while c < max(cs):
        bmesh.ops.bisect_plane(bm, geom=new_geom(), plane_co=(X(c), 0, 0), plane_no=(1, 0, 0))
        c += step
    r = math.floor(min(rs)) + step
    while r < max(rs):
        bmesh.ops.bisect_plane(bm, geom=new_geom(), plane_co=(0, Y(r), 0), plane_no=(0, 1, 0))
        r += step
    faces = [f for f in bm.faces if f not in old_f]
    caps = [f for f in faces if all(v.co.z > 0 for v in f.verts) or all(v.co.z < 0 for v in f.verts)]
    res = bmesh.ops.triangulate(bm, faces=caps, quad_method="BEAUTY", ngon_method="BEAUTY")
    verts = [v for v in bm.verts if v not in old_v]
    top = {v: v.co.z > 0 for v in verts}
    for v in verts:
        c, r = CR(v.co)
        v.co.z = (top_fn(c, r) if top[v] else bot_fn(c, r)) / 12
    for f in [f for f in bm.faces if f not in old_f]:
        cen = f.calc_center_median()
        c, r = CR(cen)
        f.material_index = mat_fn(c, r, all(top[v] for v in f.verts))
        f.smooth = True


def loft_axis(bm, sections, n_top, n_bot, mat_fn, centre=AXIS, top_exp=0.75):
    """A body down the centre line: sections (row, half_width, z_top, z_side, z_bottom) px.
    mat_fn(row, s, top) picks materials (s 0 at the side line, 1 on the centre). top_exp shapes the
    crown: 0.75 is a boxy superellipse, >= 1 a dome whose flanks lean in (round skull, no slab)."""
    rings, info = [], {}
    for r, w, zt, zs, zb in sections:
        ring = []
        for k in range(n_top + 1):
            u = -math.cos(math.pi * k / n_top)
            s = math.sqrt(max(0.0, 1 - u * u))
            v = bm.verts.new((X(centre + u * w), Y(r), (zs + (zt - zs) * s ** top_exp) / 12))
            info[v] = (r, s, 1)
            ring.append(v)
        for k in range(n_bot - 1, 0, -1):
            u = -math.cos(math.pi * k / n_bot)
            s = math.sqrt(max(0.0, 1 - u * u))
            v = bm.verts.new((X(centre + u * w * 0.97), Y(r), (zs - (zs - zb) * s) / 12))
            info[v] = (r, s, 0)
            ring.append(v)
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        m = len(r0)
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            rr, ss, tt = (sum(info[v][i] for v in f.verts) / 4 for i in range(3))
            f.material_index = mat_fn(rr, ss, tt > 0.5)
            f.smooth = True
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(list(reversed(ring)) if rev else ring)
        f.material_index = mat_fn(sections[0][0] if rev else sections[-1][0], 0.5, True)
        f.smooth = True


def _pchip_slopes(xs, ys):
    """Fritsch-Carlson slopes: a monotone cubic through the stations (no overshoot)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    return m


def pchip_stations(sections, step=1.0):
    """Fix 2: resample loft stations (row, ...) along a monotone cubic per column, so the side
    profile of the head, jaw and belly is a smooth curve, not straight runs with kinks."""
    xs = [s[0] for s in sections]
    cols = list(zip(*sections))[1:]
    slopes = [_pchip_slopes(xs, list(c)) for c in cols]
    out = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        n = max(1, int(math.ceil((x1 - x0) / step)))
        for k in range(n):
            t = k / n
            hh = x1 - x0
            h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
            h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
            row = [x0 + t * hh]
            for c, m in zip(cols, slopes):
                row.append(h00 * c[i] + h10 * hh * m[i] + h01 * c[i + 1] + h11 * hh * m[i + 1])
            out.append(tuple(row))
    out.append(tuple(sections[-1]))
    return out


def interp(sections, r, i):
    for a, b in zip(sections, sections[1:]):
        if a[0] <= r <= b[0]:
            t = (r - a[0]) / (b[0] - a[0])
            return a[i] + (b[i] - a[i]) * t
    return sections[0][i] if r < sections[0][0] else sections[-1][i]


def cull_hidden(obj, grid=2, ndirs=32):
    """Delete faces no ray from outside can reach (after assembly-newsh2-9.py)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 1e-3
    dead = []
    for f in bm.faces:
        n = f.normal
        if n.z > 0.2:  # faces turned up stay: the game camera looks down on them
            continue
        c = f.calc_center_median()
        pts = [c] + [c.lerp(v.co, 0.85) for v in f.verts]
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


# --------------------------------------------------------------------------------------------------
# Materials (palette indices: trimmed sprite medians per region, both sides together)
# --------------------------------------------------------------------------------------------------

class Mats:
    def __init__(self):
        self.sprite = {"name": NAME, "colors": {str(k): list(v) for k, v in COLORS.items()}}
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.0, roughness=0.6):
        key = (index, metallic, roughness)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nsh091b{len(self.list)}", metallic=metallic,
                                        roughness=roughness)
            m.name = f"pal_{index}_nsh091b_{len(self.list)}"
            self.list.append(m)
        return self.slots[key]


MAT = Mats()
# The D170 GRYPHON's finish: blue hide and horn nearly dielectric, satin; grey shell a little metallic.
M_HORN = MAT(55, 0.05, 0.42)     # crest horns (horn region median 55)
M_BLADE = MAT(8, 0.15, 0.4)      # grey blades by the spine (median 8: 9 lit left, 8 right)
M_FIN_U = MAT(10, 0.1, 0.58)    # upper collar feather (median 10)
M_FIN_M = MAT(8, 0.1, 0.6)     # middle feather (median 8: 8-9 lit left, 6-7 right)
M_FIN_L = MAT(6, 0.1, 0.62)     # lower feather (median 6)
M_GRV_U = MAT(8, 0.1, 0.62)      # QA round 3: each fan's pleat grooves, a step darker (rib-aligned bands)
M_GRV_M = MAT(6, 0.1, 0.64)
M_GRV_L = MAT(4, 0.1, 0.66)
M_GAP = MAT(3, 0.05, 0.8)        # dark backing seen in the gaps between the feathers
M_SLOT = MAT(49, 0.0, 0.8)       # dark tendon channel either side of the spine
M_NECK = MAT(54, 0.05, 0.5)      # neck flanks and belly (crown median 54)
M_SPINE_HI = MAT(55, 0.05, 0.4)  # thin upper spine ridge, rows 4-12 (col 24 median 55)
M_SPINE = MAT(57, 0.05, 0.38)    # vertebra beads, rows 13-27 (col 24 median 57)
M_SCALE = MAT(54, 0.05, 0.5)     # collar scales (crown median 54)
M_HIDE = MAT(53, 0.05, 0.6)      # collar hide between the scales (the mottling's darker steps)


# --------------------------------------------------------------------------------------------------
# Parts (px: c east, r south = front, toward the head; z up)
# --------------------------------------------------------------------------------------------------

def big_loop(field):
    loops = contour_loops(field, 0.08)
    return max(loops, key=lambda lp: abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(lp, lp[1:] + lp[:1]))))


def dist_fn(field):
    dist = _chamfer(field >= 0.5)
    return lambda c, r: field_at(dist, c, r) if field_at(field, c, r) >= 0.5 else 0.0


def dist_fn_smooth(field, sigma_px=0.6):
    """Fix round 1: the chamfer distance blurred (no 1/3-px kinks), so the feathers' rounded rims
    and grooves shade as smooth surfaces, not crinkled foil."""
    dist = _chamfer(field >= 0.5)
    s = sigma_px * SUB
    k = np.arange(-int(3 * s) - 1, int(3 * s) + 2)
    g = np.exp(-0.5 * (k / s) ** 2)
    g /= g.sum()
    dist = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 0, dist)
    dist = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 1, dist)
    return lambda c, r: max(0.0, field_at(dist, c, r)) if field_at(field, c, r) >= 0.5 else 0.0


def side_mask(left):
    return LEFT if left else ~LEFT


def ease(knots, x):
    """Smooth (zero-slope smoothstep) interpolation through knots [(x, y)]: crisp tier crests and
    valleys without the kinks of a straight piecewise ramp."""
    if x <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t * t * (3 - 2 * t)
    return knots[-1][1]


# QA round 2: the three grey tiers each side are three separate feathers, each a clean loft (no
# pixel mask in its surface, no ripple): a grid of stations along r (every 1/8 px) by columns from
# a root buried in the neck core out to the tier's own outer edge. That edge is one monotone cubic
# (pchip) through the sprite's row-centre extents of that tier only (a quarter px out), with the
# tier's tip a rounded point at its sprite corner: the upper and lower feathers point out and back
# (their tips at the back outer corner, the outer edge receding toward the root), the middle one out
# and forward. The section across each feather is monotone: a rounded leading (back) edge, the crest
# just behind it, one even slope down to the trailing (front) edge. Every rim (back, outer, front)
# has the same rounded chamfer (a circular roll-off of constant radius in plan, from a smooth min of
# the distances to the three edges). The feathers thin from root to tip, rise from the neck at the
# horn roots (no slot under the horns) and fan out: the upper tip swept up, the middle level, the
# lower drooping. Between the tiers a dark recessed web fills the sprite's dark rows 12 and 17 (the
# sprite's notches between the feathers at the outline).
FAN_CI = {True: 21.6, False: 27.4}   # inner edge: inside the neck core (dc 2.9), never seen
TIER_ROWS = [(8, 11), (13, 16), (18, 22)]
GAP_ROWS = (12, 17)
TIER_R = [(7.78, 12.12), (12.88, 17.1), (17.86, 22.9)]      # back / front edge rows of each feather
TIER_TIP_BACK = [True, False, True]   # the tip at the back outer corner (else the front outer corner)
# mid-surface height (px) at the root (dc 5.5) and at the tip; the back edge stands TIER_SLOPE higher
TIER_Z = [(11.0, 15.0), (10.4, 12.9), (9.8, 11.3)]   # QA round 3: each fan sweeps up toward its tip
TIER_SLOPE = 0.55
TIER_MAT = TIER_GROOVE = None  # filled after the materials


def tier_of(r):
    return 0 if r < 12.5 else (1 if r < 17.5 else 2)


def pchip_eval(xs, ys, x):
    m = _pchip_slopes(xs, ys)
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    hh = xs[i + 1] - xs[i]
    t = (x - xs[i]) / hh
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * hh * m[i]
            + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * hh * m[i + 1])


def _extent(r, left, out=0.25):
    cols = np.where(INNER[r] & (LEFT[r] if left else ~LEFT[r]))[0]
    return cols.min() - out if left else cols.max() + 1 + out


def tier_outer(k, left):
    """The feather's outer edge c(r): pchip through its rows' extents, its ends pulled in to round
    the corners; the tip corner a short rounded point."""
    a, b = TIER_ROWS[k]
    r0, r1 = TIER_R[k]
    sgn = 1.0 if left else -1.0   # + is inward (toward the axis) on the left
    rs = [r + 0.5 for r in range(a, b + 1)]
    cs = [_extent(r, left) for r in range(a, b + 1)]
    if TIER_TIP_BACK[k]:
        # the point: the first row's extent held just behind the back edge, then a short round-in
        rs = [r0, r0 + 0.3] + rs
        cs = [cs[0] + sgn * 0.75, cs[0] + sgn * 0.08] + cs
        cs[2] = cs[2] - sgn * 0.08
        rs += [r1]
        cs += [cs[-1] + sgn * 1.0]
    else:
        rs = [r0] + rs + [r1 - 0.3, r1]
        cs = [cs[0] + sgn * 0.6] + cs
        cs[-1] = cs[-1] - sgn * 0.08
        cs += [cs[-1] + sgn * 0.08, cs[-1] + sgn * 0.75]
    return lambda r: pchip_eval(rs, cs, r)


def _smin(ds, k=0.18):
    m = min(ds)
    return m - k * math.log(sum(math.exp(-(d - m) / k) for d in ds))


# QA round 3: each tier is ONE swept feather fan (no stacked quills): one loft whose outline is the
# pchip outer edge above, with a constant rounded chamfer all round and a monotone section (crest
# behind the leading back edge, one slope to the trailing front edge). The fan is pleated: N_RIB
# shallow flutes radiate from the tier's hub (its root, south-inner, under the horn) to pointed
# feather tips on the outer edge, so the quills point up and out along the sprite's sweep and splay
# from the root. The loft's grid runs along the ribs. The whole sheet is pleated (top and bottom together), its outer edge serrated
# between the tips, and it sweeps up toward the tip (the upper tier most).
N_RIB = [4, 4, 4]
SERR = 0.4     # serration of the outer edge between the feather tips (plan px)
FLUTE = 0.6    # pleat depth (px)


def _lin_interp(x, xs, ys):
    """Piecewise linear, extrapolated past both ends."""
    if x <= xs[0]:
        return ys[0] + (x - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0])
    if x >= xs[-1]:
        return ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
    return float(np.interp(x, xs, ys))


class Fan:
    def __init__(self, k, left, pleat=True, grow=0.0):
        self.k, self.left, self.pleat, self.grow = k, left, pleat, grow
        self.sgn = 1.0 if left else -1.0
        self.co0 = tier_outer(k, left)
        self.r0, self.r1 = TIER_R[k]
        n = N_RIB[k]
        self.rib_r = [self.r0 + (i + 0.5) * (self.r1 - self.r0) / n for i in range(n)]
        self.ci = FAN_CI[left]
        # the ribs: straight in plan from a root bunched toward the tier's south-inner corner (under the
        # horn) out to their tips, so they splay up and out
        hr0 = self.r1 - 0.6
        self.rib_root = [hr0 + (r - hr0) * 0.15 for r in self.rib_r]
        poly = np.array([(self.co(r), r) for r in np.linspace(self.r0, self.r1, 300)])
        self.poly = poly
        c_tip = min(poly[:, 0]) if left else max(poly[:, 0])
        self.dc_tip = abs(c_tip - AXIS)

    def ridge(self, s):
        return 0.5 + 0.5 * math.cos(2 * math.pi * s)

    def co(self, r):
        c = self.co0(r)
        if not self.pleat:
            return c
        s = _lin_interp(r, self.rib_r, list(range(len(self.rib_r))))
        g = self.ridge(s) ** 2
        taper = smoothstep(self.r0, self.r0 + 0.55, r) * smoothstep(self.r1, self.r1 - 0.55, r)
        return c - self.sgn * SERR * (g - 0.375) * taper

    def rib_knots(self, uu):
        """Rows (r) of the back edge, each rib and the front edge at column fraction uu: the ribs run
        straight from the bunched root (uu 0, inside the neck) to their tips on the outline (uu 1)."""
        n = len(self.rib_r)
        rs = [r0 + (r1 - r0) * uu for r0, r1 in zip(self.rib_root, self.rib_r)]
        return [0.0] + [(i + 0.5) / n for i in range(n)] + [1.0], [self.r0] + rs + [self.r1]

    def mid(self, c, r):
        zr, zt = TIER_Z[self.k]
        dc = abs(c - AXIS)
        u = max(0.0, min(1.0, (dc - 5.5) / (self.dc_tip - 5.5)))
        g = u * u * (3 - 2 * u) if self.k else u ** 1.3   # swept up toward the tip
        z = zr + (zt - zr) * g
        s = (r - self.r0) / (self.r1 - self.r0)
        z += TIER_SLOPE * (0.5 - s) * (0.4 + 0.6 * smoothstep(4.0, 8.0, dc))
        return z, u, s

    def heights(self, c, r, sp=None, uu=1.0):
        """Top and bottom z (px) at (c, r); sp is the pleat coordinate (rib i at sp = i), None = flat."""
        RR, RIM = 0.6, 0.1
        z, u, s = self.mid(c, r)
        t = 0.8 - 0.55 * u + self.grow
        dd = np.sqrt((self.poly[:, 0] - c) ** 2 + (self.poly[:, 1] - r) ** 2).min()
        d = _smin([r - self.r0, self.r1 - r, float(dd)])
        e = max(0.0, min(1.0, d / RR))
        b = math.sqrt(max(0.0, 1.0 - (1.0 - e) ** 2))   # constant circular chamfer
        crest = 1.0 - 0.45 * smoothstep(0.15, 1.0, s)   # monotone section
        top = z + RIM + max(0.0, t * crest - RIM) * b
        bot = z - RIM - max(0.0, 1.1 * t - RIM) * b
        if self.pleat and sp is not None:
            fade = smoothstep(0.22, 0.6, uu)
            dz = FLUTE * (self.ridge(sp) - 0.5) * fade * (0.35 + 0.65 * b)
            top += dz
            bot += 0.85 * dz
        return top, bot

    def build(self, bm):
        """The loft's grid follows the ribs (rows of constant pleat coordinate), so the pleats shade
        as clean straight folds, not a staircase across a row grid."""
        left = self.left
        n = len(self.rib_r)
        NV = n * 8 + 6
        vs_ = [0.5 - 0.5 * math.cos(math.pi * i / NV) for i in range(NV + 1)]
        NU = 34
        us = [0.35 * (j / NU) + 0.65 * math.sin(0.5 * math.pi * j / NU) for j in range(NU + 1)]
        mt, mg = TIER_MAT[self.k], TIER_GROOVE[self.k]
        ve, re_ = self.rib_knots(1.0)
        T, B = [], []
        for v in vs_:
            r_e = float(np.interp(v, ve, re_))
            o = self.co(r_e)
            sp = n * v - 0.5
            tr, br = [], []
            for uu in us:
                c = self.ci + (o - self.ci) * uu
                kv, kr = self.rib_knots(uu)
                r = float(np.interp(v, kv, kr))
                zt_, zb_ = self.heights(c, r, sp, uu)
                tr.append(bm.verts.new((X(c), Y(r), zt_ / 12)))
                br.append(bm.verts.new((X(c), Y(r), zb_ / 12)))
            T.append(tr)
            B.append(br)

        def quad(vs, m):
            if not left:
                vs = tuple(reversed(vs))
            try:
                f = bm.faces.new(vs)
            except ValueError:
                return
            f.material_index = m
            f.smooth = True

        for i in range(len(vs_) - 1):
            for j in range(NU):
                sp = n * 0.5 * (vs_[i] + vs_[i + 1]) - 0.5
                groove = self.pleat and self.ridge(sp) < 0.27 and us[j] > 0.42
                quad((T[i][j], T[i][j + 1], T[i + 1][j + 1], T[i + 1][j]), mg if groove else mt)
                quad((B[i][j], B[i + 1][j], B[i + 1][j + 1], B[i][j + 1]), M_FIN_L if j > NU // 3 else M_NECK)
            quad((T[i][NU], B[i][NU], B[i + 1][NU], T[i + 1][NU]), mt)
            quad((T[i][0], T[i + 1][0], B[i + 1][0], B[i][0]), M_NECK)
        for j in range(NU):
            quad((T[0][j], B[0][j], B[0][j + 1], T[0][j + 1]), mt)
            quad((T[-1][j], T[-1][j + 1], B[-1][j + 1], B[-1][j]), mt)


def build_web(bm, g, left):
    """The dark web between two fans: a thin lens-section strip along the gap row, tucked under both
    fans' rims (only the slot between them shows), tapering to a point at the sprite's dark-row tip."""
    ci = FAN_CI[left]
    sgn = 1.0 if left else -1.0
    ext = _extent(g, left, 0.0) - sgn * 0.45
    ka = 0 if g == 12 else 1
    fa, fb = Fan(ka, left, pleat=False), Fan(ka + 1, left, pleat=False)
    rc = 0.5 * (TIER_R[ka][1] + TIER_R[ka + 1][0])
    path = []
    n = 24
    # level at the root's height: the fans sweep up away from it, so it reads as the deep slot between
    # them, and from the side it is a thin dark line, not a rising slab
    cr = ci + (ext - ci) * 0.3
    z = min(fa.heights(cr, TIER_R[ka][1] - 0.45)[1], fb.heights(cr, TIER_R[ka + 1][0] + 0.45)[1]) - 0.2
    for i in range(n + 1):
        u = i / n
        c = ci + (ext - ci) * u
        w = 0.85 * math.sqrt(max(0.0, 1 - smoothstep(0.82, 1.0, u) ** 2))
        if i == n:
            w = 0.0
        path.append((c, rc, z, w, 0.0 if w == 0 else 0.16))
    path[0] = (path[0][0] + sgn * 0.3, rc, path[0][2], 0.0, 0.0)
    sweep(bm, path, WEB_SEC, M_GAP)


def build_feathers(bm, left, proxy=False):
    global TIER_MAT, TIER_GROOVE
    TIER_MAT = (M_FIN_U, M_FIN_M, M_FIN_L)
    TIER_GROOVE = (M_GRV_U, M_GRV_M, M_GRV_L)
    for k in range(3):
        Fan(k, left, pleat=not proxy, grow=0.12 if proxy else 0.0).build(bm)
    for g in GAP_ROWS:
        build_web(bm, g, left)



def extents(mask, rows):
    out = []
    for r in rows:
        cs = np.where(mask[r])[0]
        if len(cs):
            out.append((r + 0.5, cs.min(), cs.max() + 1))
    return out


def smooth_rows(rows, k=3):
    rr = np.array([q[0] for q in rows])
    cc = np.array([(q[1] + q[2]) / 2 for q in rows])
    ww = np.array([(q[2] - q[1]) / 2 for q in rows])
    ker = np.ones(k) / k
    p = k // 2
    return (rr, np.convolve(np.pad(cc, p, mode="edge"), ker, "valid"),
            np.convolve(np.pad(ww, p, mode="edge"), ker, "valid"))


# Horn section: keeled (a ridge along the top, flatter flanks, shallow belly), as D170's horns.
HORN_SEC = [(u, v) for u, v in ((1.0, 0.0), (0.78, 0.5), (0.42, 0.86), (0.0, 1.0), (-0.42, 0.86),
                                (-0.78, 0.5), (-1.0, 0.0), (-0.7, -0.5), (0.0, -0.66), (0.7, -0.5))]
WEB_SEC = [(1.0, 0.0), (0.85, 0.75), (0.0, 1.0), (-0.85, 0.75), (-1.0, 0.0), (-0.85, -0.75), (0.0, -1.0),
           (0.85, -0.75)]
# fix round 4: a 12-point lens (the 6-point one split its normals at the 40 degree sharp angle and
# shaded faceted)
# fix round 4: the horn root web is a fillet (concave flanks flaring into the core), not a post
FILLET_SEC = [(1.7, -1.0), (1.0, -0.55), (0.62, 0.1), (0.42, 0.7), (0.0, 1.0), (-0.42, 0.7), (-0.62, 0.1),
              (-1.0, -0.55), (-1.7, -1.0), (0.0, -1.05)]
BLADE_SEC = [(math.cos(a), (1.0 if math.sin(a) > 0 else 0.7) * math.sin(a) * (0.85 + 0.15 * abs(math.sin(a))))
             for a in (2 * math.pi * k / 12 for k in range(12))]


# Tip stations per side (c centre, r, half width px), fitted to the sprite's own horn and blade
# pixels at the top rows (rows 1-6), where the smoothed per-row extents lose the points.
HORN_TIP = {
    True: [(18.45, 1.45, 0.0), (18.5, 2.3, 0.55), (18.5, 3.4, 1.0), (18.65, 4.7, 1.45), (19.1, 6.0, 1.7)],
    False: [(30.6, 1.45, 0.0), (30.65, 2.3, 0.55), (30.65, 3.4, 1.05), (30.45, 4.7, 1.45), (30.1, 6.0, 1.75)],
}
BLADE_TIP = {
    True: [(21.9, 0.75, 0.0), (21.95, 1.5, 0.85), (21.0, 2.35, 0.95), (21.3, 3.6, 1.45), (21.8, 4.8, 1.6)],
    False: [(27.4, 0.95, 0.0), (27.5, 1.6, 1.0), (27.5, 2.6, 1.2), (27.0, 3.6, 1.3), (27.0, 4.6, 1.6)],
}


def tip_fix(rr, cs, ws, table, r_max):
    """Replace the stations above r_max by the tip table (interpolated at the same rows)."""
    ts = np.array(table)
    cs, ws = cs.copy(), ws.copy()
    for i, r in enumerate(rr):
        if r < r_max:
            cs[i] = np.interp(r, ts[:, 1], ts[:, 0])
            ws[i] = np.interp(r, ts[:, 1], ts[:, 2])
    return cs, ws


def fair(rr, cs, ws, step=0.4, passes=2, pin=1):
    """Fix round 1: fair the per-row stations (tip table + smoothed extents) into one smooth curve:
    a few 3-tap passes on the centre line and widths (the tip's point kept), then a monotone cubic
    through them sampled every `step` rows, so no row-to-row zigzag reaches the silhouette."""
    cs, ws = np.array(cs, float), np.array(ws, float)
    c0, w0 = cs[:pin].copy(), ws[:pin].copy()
    for _ in range(passes):
        cs[1:-1] = 0.25 * cs[:-2] + 0.5 * cs[1:-1] + 0.25 * cs[2:]
        ws[1:-1] = 0.25 * ws[:-2] + 0.5 * ws[1:-1] + 0.25 * ws[2:]
        cs[:pin], ws[:pin] = c0, w0  # the point and its first station stay on the sprite's tip pixel
    st = pchip_stations([(float(r), float(c), float(w)) for r, c, w in zip(rr, cs, ws)], step)
    return (np.array([q[0] for q in st]), np.array([q[1] for q in st]),
            np.array([max(0.0, q[2]) for q in st]))


HORN_WMAX = [(1.5, 0.04), (2.3, 0.8), (3.4, 1.6), (5.0, 1.72), (7.5, 1.75), (9.5, 1.62), (11.5, 1.35), (13.5, 1.05), (16.0, 1.05),
             (18.0, 1.35)]
HORN_WMIN = [(12.0, 0.0), (13.2, 0.95), (16.8, 0.95), (18.0, 0.0)]


def horn_z(r):
    """The horn rises from the neck (row 22) to its point at the top (row 1): readable as a crest
    horn from the tilted camera, its tip standing over the D170 skull row."""
    return 10.9 + 3.4 * (1 - smoothstep(0.5, 15.0, r)) ** 1.4


def build_horn(bm, left):
    m = F & (REG == "h") & side_mask(left)
    if left:
        m &= ~((RR > 19.5) & (CC < 20)) & ~((RR < 12) & (CC > 23))
    else:
        m &= ~((RR > 18.5) & (CC > 29)) & ~((RR < 12) & (CC < 26.5))
    rows = extents(m, range(0, 23))
    rr, cs, ws = smooth_rows(rows)
    cs, ws = tip_fix(rr, cs, ws, HORN_TIP[left], 5.8)
    rr, cs, ws = fair(rr, cs, ws, 0.5, 1)
    # fix round 3: a blunt tip at the sprite's tip width (no needle past the outline shell): the
    # first stations hold at least 0.42 px half width and close in a short round cap
    # fix round 4: one smooth taper to a small round point (a cone with a rounded end, its width
    # never larger toward the tip): no bulb, no nipple
    r_tip = rr[0] - 0.35

    def w_lim(r):
        d = max(0.0, r - r_tip)
        return 0.36 * d + 0.24 * math.sqrt(min(1.0, d / 0.45))

    path = [(cs[0] + (0.06 if left else -0.06), r_tip, horn_z(r_tip), 0.0, 0.0)]
    for d in (0.04, 0.12, 0.24):
        r = r_tip + d
        path.append((cs[0] + (0.06 if left else -0.06) * (1 - d / 0.35), r, horn_z(r), w_lim(r), w_lim(r) * 0.62))
    web = []
    for r, c, w in zip(rr, cs, ws):
        # fix round 2: a slim hook, not a bulb: the pale-blue pixels are 4 px wide at most (the rest
        # of the region is the dark ink gap, the fan root under it), and the waist is filled out
        w = min(w, float(np.interp(r, *zip(*HORN_WMAX))))
        w = max(w, float(np.interp(r, *zip(*HORN_WMIN))))
        ring = 1.0 + 0.045 * math.cos(2 * math.pi * r / 3.0) * smoothstep(5, 9, r)  # growth rings
        w = (w + 0.04 * smoothstep(3, 6, r)) * ring
        hr = 0.5 + 0.22 * smoothstep(2, 9, r)  # fix round 2: a flatter, slimmer hook
        w = min(w, w_lim(r))
        w = max(w, w_lim(r) * (0.85 - 0.85 * smoothstep(r_tip + 1.2, r_tip + 2.2, r)))  # no pinch at the tip
        path.append((c, r, horn_z(r), w, w * hr * 1.05))
        if r > 6.0:
            # fix round 3: the horn's root web, a narrow dark keel from under the horn down into the
            # neck core, so the horn does not hover over the body (no open slot from the side)
            top = min(horn_z(r) - 0.2, 9.4 + 1.8 * (r - 6.0))
            bot = 8.0
            g = smoothstep(6.0, 8.0, r)   # fix round 4: grows from a point (no flat end facing north)
            if not web:
                web.append((c, r - 0.3, horn_z(r) - 0.4, 0.0, 0.0))
            top = bot + (top - bot) * (0.25 + 0.75 * g)
            web.append((c, r, 0.5 * (top + bot), (0.62 * w + 0.05) * g, 0.5 * (top - bot) * max(0.15, g)))
    # root sinks into the collar
    c_end = cs[-1]
    # fix round 4: the root flares and dips into the collar (a fillet, no cut stub at the join)
    path.append((c_end, 22.9, horn_z(22.9) - 0.3, ws[-1] * 1.15, ws[-1] * 0.8))
    path.append((c_end, 23.6, 9.6, ws[-1] * 1.3, ws[-1] * 0.7))
    path.append((c_end, 24.6, 8.4, 0.0, 0.0))
    sweep(bm, path, HORN_SEC, M_HORN)
    sweep(bm, web, FILLET_SEC, M_NECK)


# QA round 2: the grey blades are explicit faired tables (row, centre c, half width px) fitted to the
# sprite's own blade pixels (left cols 20-22, right 26-28, rows 1-8; their dark ink-side pixels too): the width grows monotonically
# from a blunt rounded point (no bulb, no neck), the centre line is one gentle curve, and the section
# is a flat keeled blade (height 0.7 of the width), so the tilted camera sees a blade, not a club.
# QA round 3: the blade is a slim curved knife: its centre line one smooth C (pchip through three
# stations fitted to the sprite's blade pixels), its half width rising monotonically from a small blunt
# point (rows 1-4) and then easing off toward the root (no knob, no curl at the top).
BLADE = {
    True: {"c": [(0.7, 21.7), (4.0, 21.4), (8.6, 22.55)],
           "w": [(0.7, 0.0), (1.25, 0.92), (2.5, 1.06), (3.6, 1.1), (4.8, 1.1), (6.0, 0.95), (7.4, 0.72),
                 (8.6, 0.5)]},
    False: {"c": [(0.75, 27.45), (4.5, 27.4), (8.6, 26.45)],
            "w": [(0.75, 0.0), (1.35, 0.8), (2.5, 1.1), (3.5, 1.3), (4.6, 1.33), (6.0, 0.95), (7.4, 0.7),
                  (8.6, 0.5)]},
}


def build_blade(bm, left):
    tab = BLADE[left]
    rc, cc = zip(*tab["c"])
    rw, ww = zip(*tab["w"])
    path = []
    r = rw[0]
    while r <= rw[-1] + 1e-6:
        c = pchip_eval(list(rc), list(cc), r)
        w = max(0.0, pchip_eval(list(rw), list(ww), r))
        t = smoothstep(rw[0], rw[-1] + 1.5, r)
        z = 14.2 - 3.8 * t
        path.append((c, r, z, w, w * 0.68))
        r += 0.05 if r < rw[1] else 0.2
    # into the core
    path.append((cc[-1] + (0.15 if left else -0.15), 9.6, 10.6, 0.42, 0.36))
    path.append((cc[-1] + (0.3 if left else -0.3), 10.4, 10.0, 0.0, 0.0))
    sweep(bm, path, BLADE_SEC, M_BLADE)


# Neck core: (row, half width, top z, side z, bottom z). Its crown is the dark tendon channel (only
# seen between the spine, blades and horns); the flanks and round belly are the neck's hide.
# Fix round 3: the crown runs up under the spine and the horn roots (no slot between them and the
# body), and the back end is a rounded nose (an elliptic cap in plan and profile, no flat wall). It
# ends inside the collar.
def _core_sections():
    out = []
    # fix round 4: the crown stands up to the spine's belly and the horns' mid-height (11.6 px), so
    # nothing hovers from the side; the nose is a full round dome (no cup, no wall).
    r0, r1, zm = 4.6, 10.0, 9.8
    for k in range(17):
        r = r0 + (r1 - r0) * (1 - math.cos(0.5 * math.pi * k / 16))
        e = max(0.1, math.sqrt(max(0.0, 1 - ((r1 - r) / (r1 - r0)) ** 2)))
        out.append((r, 5.7 * e, zm + (11.7 - zm) * e ** 0.7, zm - (zm - 7.5) * e, zm - (zm - 6.2) * e))
    out += [(12.0, 5.7, 11.75, 7.9, 6.0), (16.0, 5.7, 11.7, 7.7, 5.9), (20.0, 6.1, 11.5, 7.5, 5.9),
            (22.5, 6.6, 11.0, 7.3, 6.0), (24.5, 6.0, 9.6, 7.0, 6.1), (25.6, 3.6, 8.8, 6.8, 6.2),
            (26.2, 0.8, 8.0, 6.7, 6.3)]
    return pchip_stations(out, 0.5)


CORE = _core_sections()


def core_mat(r, s, top):
    return M_SLOT if top and s > 0.55 and 6.8 < r < 22.5 else M_NECK


# Spine section: a keeled ridge (narrow crown, flanks falling into the dark channels).
SPINE_SEC = [(1.0, 0.0), (0.82, 0.42), (0.5, 0.78), (0.18, 0.98), (0.0, 1.0), (-0.18, 0.98), (-0.5, 0.78),
             (-0.82, 0.42), (-1.0, 0.0), (-0.6, -0.55), (0.0, -0.7), (0.6, -0.55)]


def build_spine(bm):
    """Fix round 2: one continuous lofted ridge (no beads): thin over rows 4-12 between the blades,
    broadening at row 13 down the collar, with shallow shingled vertebra steps (each vertebra's back
    edge a little proud, sloping down to the next) instead of separate spheres."""
    widths = [(4.1, 0.0), (4.5, 0.16), (5.3, 0.36), (6.5, 0.55), (12.0, 0.62), (13.6, 1.15), (16.0, 1.3), (25.0, 1.32),
              (27.0, 1.1), (27.9, 0.0)]
    # fix round 3: the rear end is a long tapered point dipping into the core's nose (no blunt cap)
    tops = [(4.1, 10.0), (5.0, 10.9), (6.0, 11.6), (12.0, 11.9), (14.0, 12.2), (22.0, 11.9), (24.0, 11.5),
            (26.0, 10.4), (27.0, 9.0), (27.9, 7.6)]
    path, r = [], 4.1
    while r <= 27.9 + 1e-6:
        w = np.interp(r, *zip(*widths))
        z = float(np.interp(r, *zip(*tops)))
        per = 2.0 if r < 13.0 else 2.7
        ph = ((r - (5.0 if r < 13.0 else 13.4)) / per) % 1.0
        step = smoothstep(0.0, 0.22, ph) if ph < 0.22 else 1.0 - (ph - 0.22) / 0.78
        step *= smoothstep(5.4, 7.6, r)     # a soft proud back edge, sloping down to the next
        amp = 0.14 if r < 13.0 else 0.22
        wv = w * (1.0 + 0.07 * step)
        hv = (0.72 if r < 13.0 else 0.95) * min(1.0, w / 0.55) ** 0.8
        path.append((AXIS, r, z + amp * step - 0.15, wv, hv))
        r += 0.2
    path[0] = (AXIS, path[0][1], path[0][2], 0.0, 0.0)
    path[-1] = (AXIS, path[-1][1], path[-1][2], 0.0, 0.0)
    for f in sweep(bm, path, SPINE_SEC, M_SPINE):
        if CR(f.calc_center_median())[1] < 13.0:
            f.material_index = M_SPINE_HI


# Fix round 3: the collar is the top of the beast's body, one smooth loft (a pchip through these
# stations: row, centre c, half width, crown z, side-line z, keel z). Its plan follows the sprite's
# rows 22-27 (row-centre extents, a quarter px in), then runs on past the bottom edge under the head
# (dy +28) to a round nose. The top is a dome falling off to both sides and, past row 24, forward
# and down into the head; the front face is low and rounds into the belly. Its scales are a smooth
# displacement of that dome: overlapping elliptic plates, each one rising to a free back lip (the
# sprite's lit scale edges), combined by a soft maximum, so they follow the dome with no facets.
def _collar_sections():
    # Each piece is cut at its 24 x 28 px box (split_assembly fills the cut), so nothing may run on
    # past row 28. QA round 3: a lower dome on a higher side line over a tucked belly (no tall side
    # walls, no tub), whose top ramps down from row 24 to a thin lip at the box edge, under the head's
    # brow (dy +28), instead of a steep cut front.
    return [(21.2, 24.5, 4.5, 9.9, 8.8, 7.8), (21.8, 24.5, 9.0, 10.5, 7.9, 6.6),
            (22.5, 24.55, 11.45, 10.9, 7.4, 6.0), (23.5, 24.55, 11.6, 11.0, 7.2, 5.8),
            (24.5, 24.7, 11.05, 10.7, 7.0, 5.8), (25.5, 24.55, 11.6, 10.0, 6.8, 5.8),
            (26.5, 24.6, 11.7, 9.0, 6.5, 5.9), (27.3, 24.85, 11.95, 7.6, 6.2, 6.0),
            (27.97, 24.95, 11.2, 6.15, 6.05, 5.95)]


COLLAR = _collar_sections()
SCALE_P, SCALE_W = 1.5, 2.45   # scale rows (r) and scale width (c), px


def collar_scales(c, r):
    """QA round 3: the collar's scale plates: rows of rounded, flat-topped plates (staggered half a
    plate per row) with narrow V seams between them. Returns the plate height 0..1 (0 in a seam)."""
    q = (r - 22.35) / SCALE_P
    j = math.floor(q)
    t = q - j
    x = (c - AXIS) / SCALE_W + (0.5 if j % 2 else 0.0)
    hx = abs(math.sin(math.pi * x)) ** 0.6
    hr = math.sin(math.pi * t ** 0.65) ** 0.6   # the crest toward the plate's free back edge
    return hr * hx


def build_collar(bm):
    st = pchip_stations([(r, cen, w, zt, zs, zb) for r, cen, w, zt, zs, zb in COLLAR], 0.14)
    n_top, n_bot = 100, 14
    rings = []
    for r, cen, w, zt, zs, zb in st:
        ring = []
        for k in range(n_top + 1):
            u = -math.cos(math.pi * k / n_top)
            sv = math.sqrt(max(0.0, 1 - u * u))
            c = cen + u * w
            z = zs + (zt - zs) * sv               # an elliptic dome falling to both sides
            amp = 0.38 * smoothstep(0.25, 0.6, sv) * smoothstep(1.3, 2.1, abs(c - AXIS))
            amp *= smoothstep(22.2, 22.9, r) * (1 - smoothstep(27.0, 27.8, r))
            h = collar_scales(c, r)
            z += amp * (h - 1.0) + 0.2 * amp
            ring.append((bm.verts.new((X(c), Y(r), z / 12)), amp > 0.12 and h < 0.55))
        for k in range(n_bot - 1, 0, -1):
            u = -math.cos(math.pi * k / n_bot)
            sv = math.sqrt(max(0.0, 1 - u * u))
            # the belly tucks well in under the side line (no tall straight wall below it)
            cb = cen + u * w * (1.0 - 0.4 * sv * sv)
            ring.append((bm.verts.new((X(cb), Y(r), (zs - (zs - zb) * sv) / 12)), None))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        m = len(r0)
        for k in range(m):
            j = (k + 1) % m
            qs = (r0[k], r0[j], r1[j], r1[k])
            f = bm.faces.new([v for v, _ in qs])
            if any(fl is None for _, fl in qs):
                f.material_index = M_HIDE
            else:
                f.material_index = M_HIDE if sum(1 for _, fl in qs if fl) >= 3 else M_SCALE
            f.smooth = True
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        vs = [v for v, _ in ring]
        f = bm.faces.new(list(reversed(vs)) if rev else vs)
        f.material_index = M_HIDE
        f.smooth = True


def build(coll, proxy=False):
    bm = bmesh.new()
    for left in (True, False):
        build_feathers(bm, left, proxy)
        build_horn(bm, left)
        build_blade(bm, left)
    loft_axis(bm, CORE, 16, 6, core_mat, top_exp=1.0)
    build_spine(bm)
    build_collar(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME + ("_proxy" if proxy else ""))
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME + ("_proxy" if proxy else ""), me)
    coll.objects.link(obj)
    return obj


# --------------------------------------------------------------------------------------------------
# Pieces, shells, export, review
# --------------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    print("whole tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))
    lay = common.load_sprite(ROOT, PIECES[0])["assemblyLayout"]
    pieces = common.split_assembly(obj, [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in lay], coll)
    # QA round 2: the shells come from a proxy whose feather tiers are smooth envelopes
    proxy = build(coll, proxy=True)
    proxies = common.split_assembly(proxy, [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in lay], coll)
    bpy.data.objects.remove(proxy, do_unlink=True)
    shells, total = [], 0
    for e in lay:
        name = e["model"]
        p = pieces[name]
        p.location = ((e["cx"] - CX0) / 12, -(e["cy"] - CY0) / 12, 0)
        bpy.context.view_layer.update()
        # D90/D118: the shell comes from a sealed copy taken before culling.
        sealed = proxies[name]
        loc = p.location.copy()
        sealed.location = (0, 0, 0)
        bpy.context.view_layer.update()
        sh = common.outline_shell(sealed, coll, voxel=0.016, faces=4000, inside=0.012)
        # fix round 4: relax the shell after its inside shrinkwrap, so it bridges the seams (horn on
        # blade, spine and horn roots on the collar) as one smooth skin instead of folding into them
        # (the folds' back faces drew as black shards over the model)
        smo = sh.modifiers.new("relax", "SMOOTH")
        smo.factor, smo.iterations = 0.5, 8
        bpy.context.view_layer.objects.active = sh
        with bpy.context.temp_override(object=sh, active_object=sh):
            bpy.ops.object.modifier_apply(modifier=smo.name)
        sh.name = sh.data.name = f"{name}_outline"
        sh.location = loc
        bpy.data.objects.remove(sealed, do_unlink=True)
        shells.append(sh)
        n = cull_hidden(p)
        p.data.set_sharp_from_angle(angle=math.radians(40))
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: culled {n}, {tris} tris")
    print("total tris", total)
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + shells, out)
        print("exported", out)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        (rv / "materials.json").write_text(json.dumps(sorted({k[0] for k in MAT.slots})))
        (rv / "tris.txt").write_text(f"triangles: {total} over 2 pieces (after culling hidden faces)")
        review(obj, list(pieces.values()), shells, rv, "--context" in argv)
    if "--no-export" not in argv:
        export_pieces(pieces, shells)


def export_pieces(pieces, shells):
    """Each piece at its own origin with its outline shell, through the sprite-model contract
    (public/models/enemies/<piece>.glb and its spriteModels entry, every sprite frame)."""
    for name in PIECES:
        p = pieces[name]
        sh = next(s for s in shells if s.name == f"{name}_outline")
        sh.hide_render = False
        p.location = (0, 0, 0)
        sh.location = (0, 0, 0)
        bpy.context.view_layer.update()
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", data["sprites"])


def review(whole, pieces, shells, out, context=False):
    scene = bpy.context.scene
    eng = {}
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            eng["eevee"] = e
            break
        except TypeError:
            pass
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_percentage = 100
    whole.hide_render = True
    for s in shells:
        s.hide_render = True
    k = 16

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.2
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(10))
    scene.world.use_nodes = True
    bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.05, 0.055, 0.065, 1)
    bgn.inputs[1].default_value = 4.0

    def shot(path, flat=False, transparent=False):
        if not flat and "eevee" in eng:
            scene.render.engine = eng["eevee"]
            scene.render.film_transparent = True
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            scene.render.engine = "BLENDER_WORKBENCH"
            return
        sh.light = "FLAT" if flat else "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = not flat
        sh.show_object_outline = False
        sh.show_specular_highlight = not flat
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    c = cam("top", (0, 0, 30), (0, 0, 0), ortho=W / 12, rx=W * k, ry=H * k)
    c.rotation_euler = (0, 0, 0)
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_flat.png", flat=True)
    shot(out / "top_lit.png")
    zc = 0.8
    for nm, loc, look, orth in (("front", (0, -60, zc), (0, 0, zc), W / 12 * 1.1),
                                ("rear", (0, 60, zc), (0, 0, zc), W / 12 * 1.1),
                                ("side", (-60, 0, zc), (0, 0, zc), 4.2)):
        cam(nm, loc, look, ortho=orth, rx=1100, ry=520)
        shot(out / f"{nm}.png")
    d = 11
    ctr = Vector((0, 0, zc))
    for nm, az, el in (("q_high", 35, 35), ("q_rear", 215, 32), ("q_side", 85, 22)):
        a, e = math.radians(az), math.radians(el)
        cam(nm, ctr + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), ctr,
            lens=85, rx=1000, ry=700)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam("game", ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=85, rx=1000, ry=650)
    shot(out / "game.png")
    cam("under", (0, 0, -30), (0, 0, 0), ortho=W / 12 * 1.05, rx=W * 12, ry=H * 12 + 80)
    shot(out / "under.png")
    # The game's ink (OutlineEffect): an inverted hull of the shell pushed out along its normals,
    # back faces only. Rendered here the same way (a pushed, flipped, back-face-culled copy).
    ink = bpy.data.materials.new("ink_preview")
    ink.use_nodes = True
    bsdf = next(n for n in ink.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    ink.use_backface_culling = True
    for s in shells:
        hull = s.copy()
        hull.data = s.data.copy()
        bpy.context.scene.collection.objects.link(hull)
        bm = bmesh.new()
        bm.from_mesh(hull.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for v in bm.verts:
            v.co += v.normal * 0.018
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(hull.data)
        bm.free()
        hull.data.materials.clear()
        hull.data.materials.append(ink)
        hull.hide_render = False
        try:
            hull.visible_shadow = False
        except AttributeError:
            pass
    cam("game_ink", ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=85, rx=1000, ry=650)
    shot(out / "game_shell.png")
    if context:
        # the neck in place over the D170 wings and skull (its lower row's centre at dy -8 px) and the
        # head newsh0-119 below (dy +28 px), from the published models, for reading in context
        for s in shells:
            s.hide_render = True
        ctx = []
        lay79 = common.load_sprite(ROOT, "newsh0-39")["assemblyLayout"]
        items = [(e["model"], e["cx"] - 126, e["cy"] - 46) for e in lay79] + [("newsh0-119", 1, 28)]
        for nm, dx, dy in items:
            pth = ROOT / "public" / "models" / "enemies" / f"{nm}.glb"
            if not pth.exists():
                continue
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(pth))
            for o in set(bpy.data.objects) - before:
                if o.parent is None:
                    o.location.x += dx / 12
                    o.location.y += -dy / 12
                if "outline" in o.name:
                    o.hide_render = True
                ctx.append(o)
        bpy.context.view_layer.update()
        dd = 20
        c2 = Vector((0, -0.6, zc))
        cam("ctx_game", c2 + Vector((0, -dd * math.sin(t), dd * math.cos(t))), c2, lens=50, rx=1000, ry=700)
        shot(out / "ctx_game.png")
        a, e = math.radians(30), math.radians(30)
        cam("ctx_q", c2 + Vector((dd * math.cos(e) * math.sin(a), -dd * math.cos(e) * math.cos(a), dd * math.sin(e))),
            c2, lens=50, rx=1000, ry=700)
        shot(out / "ctx_q.png")


if __name__ == "__main__":
    main()
