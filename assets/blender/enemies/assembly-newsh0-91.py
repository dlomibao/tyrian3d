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
M_FIN_U = MAT(10, 0.15, 0.42)    # upper collar feather (median 10)
M_FIN_M = MAT(8, 0.15, 0.45)     # middle feather (median 8: 8-9 lit left, 6-7 right)
M_FIN_L = MAT(6, 0.15, 0.48)     # lower feather (median 6)
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


# Fix round 2: the three grey tiers each side are ONE thin feather sheet (no separate hanging
# blocks, no gaps). Along r (back to front) the top is a sawtooth: each tier rises from the valley
# to a rounded back crest, slopes down through its lit rows and dives into the sprite's dark row
# (rows 12 and 17), a south-facing dark face the tilted game camera looks straight into. Across
# the sheet the thickness tapers from a fillet at the neck to a knife edge at the outline (no end
# caps). The upper tier's tips sweep up and out, the lower tier's down; barb grooves run outward
# and back (diagonal), not along the rows.
TIER_VALLEY = (13.0, 18.0)      # valley bottoms: the dive faces are exactly the dark rows 12 and 17
TIER_PROFILE = [(6.6, 0.55), (7.7, 1.0), (12.0, 0.62), (13.0, 0.0), (13.6, 1.0), (17.0, 0.6),
                (18.0, 0.0), (18.6, 1.0), (22.6, 0.55)]


def tier_of(r):
    return 0 if r < TIER_VALLEY[0] - 1.0 else (1 if r < TIER_VALLEY[1] - 1.0 else 2)


def build_feathers(bm, left):
    sgn = -1.0 if left else 1.0
    own = INNER & side_mask(left) & np.isin(REG, list("uml"))
    root = F & side_mask(left) & np.isin(REG, list("hbs")) & (RR > 7.0) & (RR < 22.5)
    root &= np.abs(CC - AXIS) > 2.6
    fld = smooth_field(own | root, 0.45)
    d = dist_fn_smooth(fld)
    d0 = 0.12  # the blurred distance at the 0.5 contour

    def edge(c, r):
        return min(1.0, max(0.0, d(c, r) - d0) / 1.6) ** 0.62

    def w_tier(r):
        """Per-tier weights (u, m, l), zero at the valleys between them."""
        v0, v1 = TIER_VALLEY
        wu = 1.0 - smoothstep(v0 - 1.4, v0, r)
        wl = smoothstep(v1, v1 + 1.4, r)
        wm = max(0.0, 1.0 - wu - wl) * smoothstep(v0, v0 + 1.4, r) * (1 - smoothstep(v1 - 1.4, v1, r))
        return wu, wm, wl

    def centre(c, r):
        dc = abs(c - AXIS)
        o = max(0.0, dc - 6.0)
        z = 8.6 - 0.05 * o
        wu, wm, wl = w_tier(r)
        z += wu * (0.7 + 2.3 * smoothstep(8.0, 18.5, dc))      # upper tier: tips swept up and out
        z += wm * (0.0 - 0.6 * smoothstep(8.0, 18.5, dc))
        z += wl * (-0.5 - 1.1 * smoothstep(7.0, 17.5, dc))     # lower tier: tips droop
        return z

    def taper(c):
        return 1.0 - 0.55 * smoothstep(7.0, 19.0, abs(c - AXIS))

    def groove(c, r):
        dc = abs(c - AXIS)
        ph = (r + 0.42 * dc) / 2.3
        g = 0.5 + 0.5 * math.cos(2 * math.pi * ph)
        k = smoothstep(7.5, 10.0, dc) * max(0.0, ease(TIER_PROFILE, r) - 0.5) * 2.0
        return 0.5 * g ** 3 * k

    def top(c, r):
        dc = abs(c - AXIS)
        e = edge(c, r)
        relief = 2.3 * ease(TIER_PROFILE, r) * (0.75 + 0.25 * (1 - smoothstep(9, 19, dc)))
        relief *= 0.3 + 0.7 * smoothstep(4.5, 9.0, dc)  # low under the horn and blade roots
        return centre(c, r) + e * taper(c) * (0.45 + relief - groove(c, r))

    def bot(c, r):
        dc = abs(c - AXIS)
        e = edge(c, r)
        fillet = 3.6 * (1.0 - smoothstep(4.5, 10.5, dc))  # the root fairs down into the neck
        return centre(c, r) - e * (0.9 * taper(c) + fillet)

    def mat(c, r, t):
        if not t:  # the root fillet under the fan is the neck's hide, the outer underside grey
            return M_NECK if abs(c - AXIS) < 9.0 else M_FIN_L
        if REG[min(H - 1, int(r)), min(W - 1, int(c))] in "hbs":
            return M_SLOT  # the fan root under the horn and blade: the dark ink gap between them
        for v in TIER_VALLEY:
            if v - 1.0 < r < v:  # whole grid cells (0.5 px), so no triangle teeth
                return M_GAP
        return (M_FIN_U, M_FIN_M, M_FIN_L)[tier_of(r)]

    relief_plate(bm, big_loop(fld), top, bot, 0.5, mat)


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
BLADE_SEC = [(1.0, 0.0), (0.45, 0.62), (0.0, 1.0), (-0.45, 0.62), (-1.0, 0.0), (0.0, -0.7)]


# Tip stations per side (c centre, r, half width px), fitted to the sprite's own horn and blade
# pixels at the top rows (rows 1-6), where the smoothed per-row extents lose the points.
HORN_TIP = {
    True: [(18.5, 1.45, 0.0), (18.7, 2.3, 0.6), (18.7, 3.4, 1.05), (18.9, 4.7, 1.55), (19.2, 6.0, 1.95)],
    False: [(30.5, 1.45, 0.0), (30.5, 2.3, 0.5), (30.1, 3.4, 1.6), (30.4, 4.7, 1.7), (30.1, 6.0, 2.05)],
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


HORN_WMAX = [(1.5, 0.04), (2.3, 0.8), (3.4, 1.6), (5.0, 1.7), (7.5, 1.65), (9.5, 1.6), (11.5, 1.35), (13.5, 1.05), (16.0, 1.05),
             (18.0, 1.35)]
HORN_WMIN = [(12.0, 0.0), (13.2, 0.95), (16.8, 0.95), (18.0, 0.0)]


def horn_z(r):
    """The horn rises from the neck (row 22) to its point at the top (row 1): readable as a crest
    horn from the tilted camera, its tip standing over the D170 skull row."""
    return 10.6 + 4.9 * (1 - smoothstep(0.5, 15.0, r)) ** 1.4


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
    path = [(cs[0] + (0.2 if left else -0.2), rr[0] - 0.9, horn_z(rr[0] - 0.9) + 0.6, 0.0, 0.0)]
    for r, c, w in zip(rr, cs, ws):
        # fix round 2: a slim hook, not a bulb: the pale-blue pixels are 4 px wide at most (the rest
        # of the region is the dark ink gap, the fan root under it), and the waist is filled out
        w = min(w, float(np.interp(r, *zip(*HORN_WMAX))))
        w = max(w, float(np.interp(r, *zip(*HORN_WMIN))))
        ring = 1.0 + 0.045 * math.cos(2 * math.pi * r / 3.0) * smoothstep(5, 9, r)  # growth rings
        w = (w + 0.04 * smoothstep(3, 6, r)) * ring
        hr = 0.5 + 0.22 * smoothstep(2, 9, r)  # fix round 2: a flatter, slimmer hook
        path.append((c, r, horn_z(r), w, w * hr * 1.05))
    # root sinks into the collar
    c_end = cs[-1]
    path.append((c_end, 23.6, 9.4, ws[-1] * 0.9, ws[-1] * 0.7))
    path.append((c_end, 24.6, 8.4, 0.0, 0.0))
    sweep(bm, path, HORN_SEC, M_HORN)


def build_blade(bm, left):
    m = F & (REG == "b") & side_mask(left)
    if left:
        m &= (RR < 12) & (CC > 19)
    else:
        m &= (RR < 9.5) & (CC < 30)
    rows = extents(m, range(0, 13))
    rr, cs, ws = smooth_rows(rows)
    cs, ws = tip_fix(rr, cs, ws, BLADE_TIP[left], 4.9)
    rr, cs, ws = fair(rr, cs, ws, 0.4, 1, pin=3)
    r_end = rr[-1] + 1.5
    path = [(cs[0], max(0.15, rr[0] - 0.6), 16.8, 0.0, 0.0)]
    for r, c, w in zip(rr, cs, ws):
        t = smoothstep(rr[0] - 0.6, r_end, r)
        z = 16.2 - 5.4 * t
        w = w + 0.02
        path.append((c, r, z, w, w * (1.25 - 0.35 * t)))
    path.append((cs[-1] + (0.3 if left else -0.3), r_end, 10.2, ws[-1] * 0.8, 0.8))
    path.append((cs[-1] + (0.5 if left else -0.5), r_end + 1.0, 9.6, 0.0, 0.0))
    sweep(bm, path, BLADE_SEC, M_BLADE)


# Neck core: (row, half width, top z, side z, bottom z). Its crown is the dark tendon channel (only
# seen between the spine, blades and horns); the flanks and round belly are the neck's hide.
CORE = pchip_stations([(4.3, 0.6, 9.0, 8.9, 8.7), (4.9, 2.2, 9.0, 8.5, 7.6), (5.8, 3.4, 8.9, 8.0, 6.2),
                       (7.2, 4.4, 8.8, 7.4, 4.8), (9.0, 4.8, 8.7, 7.1, 3.7), (12.0, 5.0, 8.6, 6.9, 3.0),
                       (18.0, 5.4, 8.6, 6.6, 2.6), (22.5, 7.0, 9.4, 6.4, 2.5), (26.0, 8.6, 8.4, 5.8, 2.6),
                       (29.0, 8.0, 6.6, 4.8, 3.0), (30.6, 4.8, 5.3, 4.4, 3.6), (31.3, 1.4, 4.6, 4.3, 4.1)], 1.0)


def core_mat(r, s, top):
    return M_SLOT if top and s > 0.55 and r < 22.5 else M_NECK


# Spine section: a keeled ridge (narrow crown, flanks falling into the dark channels).
SPINE_SEC = [(1.0, 0.0), (0.82, 0.42), (0.5, 0.78), (0.18, 0.98), (0.0, 1.0), (-0.18, 0.98), (-0.5, 0.78),
             (-0.82, 0.42), (-1.0, 0.0), (-0.6, -0.55), (0.0, -0.7), (0.6, -0.55)]


def build_spine(bm):
    """Fix round 2: one continuous lofted ridge (no beads): thin over rows 4-12 between the blades,
    broadening at row 13 down the collar, with shallow shingled vertebra steps (each vertebra's back
    edge a little proud, sloping down to the next) instead of separate spheres."""
    widths = [(4.6, 0.0), (5.2, 0.42), (6.5, 0.55), (12.0, 0.62), (13.6, 1.15), (16.0, 1.3), (27.0, 1.32),
              (29.6, 1.0), (30.6, 0.0)]
    tops = [(4.6, 10.7), (5.6, 11.2), (12.0, 11.5), (14.0, 11.9), (22.0, 11.6), (24.0, 11.3), (26.0, 10.9),
            (28.0, 9.7), (29.5, 8.4), (30.6, 7.0)]
    path, r = [], 4.6
    while r <= 30.6 + 1e-6:
        w = np.interp(r, *zip(*widths))
        z = float(np.interp(r, *zip(*tops)))
        per = 2.0 if r < 13.0 else 2.7
        ph = ((r - (5.0 if r < 13.0 else 13.4)) / per) % 1.0
        step = smoothstep(0.0, 0.22, ph) if ph < 0.22 else 1.0 - (ph - 0.22) / 0.78
        step = step if r > 5.4 else 0.0     # a soft proud back edge, sloping down to the next
        amp = 0.14 if r < 13.0 else 0.22
        wv = w * (1.0 + 0.07 * step)
        hv = (0.72 if r < 13.0 else 0.95) * min(1.0, w / 0.5)
        path.append((AXIS, r, z + amp * step - 0.15, wv, hv))
        r += 0.2
    path[0] = (AXIS, path[0][1], path[0][2], 0.0, 0.0)
    path[-1] = (AXIS, path[-1][1], path[-1][2], 0.0, 0.0)
    for f in sweep(bm, path, SPINE_SEC, M_SPINE):
        if CR(f.calc_center_median())[1] < 13.0:
            f.material_index = M_SPINE_HI


SCALE_SEC = [(1.0, 0.0), (0.7, 0.55), (0.0, 1.0), (-0.7, 0.55), (-1.0, 0.0), (-0.5, -0.4), (0.5, -0.4)]


def build_collar(bm):
    m = F & ((REG == "c") | ((REG == "h") & (RR > 20.5) & ((CC < 20) | (CC > 29.5))) | ((REG == "e") & (RR > 22.5)))
    # fix round 1: no thin grafts; the collar's own edge covers its pixels (opened then closed)
    m &= ~((RR < 22) & (np.abs(CC - AXIS) > 4.5))
    # run the collar on past the bottom edge (it continues into the head) to a round cap
    ext = np.zeros((H + 4, W), bool)
    m[22, 33:37] |= F[22, 33:37]  # the collar's own edge reaches the row-23 corner pixel (col 35)
    m[23, 33:36] |= F[23, 33:36]
    ext[:H] = m
    cols = np.where(m[H - 1])[0]
    cen, half = (cols.min() + cols.max() + 1) / 2.0, (cols.max() + 1 - cols.min()) / 2.0
    fld = smooth_field(ext, 0.55)
    # fix round 2: the run-on past the bottom edge is an analytic half ellipse in plan (no per-row
    # stair steps, so the front outline is a smooth curve with many segments)
    for i in range(fld.shape[0]):
        for j in range(fld.shape[1]):
            c, r = lattice_cr(i, j)
            if r > H - 1.0:
                q = 1.0 - ((c - cen) / half) ** 2 - ((r - (H - 1.0)) / 6.0) ** 2
                fld[i, j] = max(fld[i, j] if r < H else 0.0, min(1.0, max(0.0, 0.5 + 2.2 * q)))
    d = dist_fn_smooth(fld)

    def zmid(r):
        return 6.3 - 2.1 * smoothstep(25.0, 33.0, r)

    def cap_t(r):
        """Fix round 2: the top curves down and forward from row 23.5 into the head (a convex neck,
        no slab face); the belly closes later and higher, so the nose ends low and round."""
        return math.sqrt(max(0.0, 1.0 - max(0.0, (r - 23.5) / 9.5) ** 2))

    def cap_b(r):
        return math.sqrt(max(0.0, 1.0 - max(0.0, (r - 27.0) / 6.0) ** 2))

    def top0(c, r):
        f = min(1.0, (d(c, r) + 0.05) / 6.0)  # a sloped dome rim (no vertical wall round the edge)
        return 4.1 * (1.0 - (1.0 - f) ** 2)

    def bot0(c, r):
        f = min(1.0, (d(c, r) + 0.05) / 5.0)
        u = 1.0 - 0.4 * smoothstep(4.0, 12.5, abs(c - AXIS))  # a U-shaped belly, deepest on the axis
        return 3.8 * u * (1.0 - (1.0 - f) ** 2) ** 0.8

    def top(c, r):
        return zmid(r) + top0(c, r) * cap_t(r)

    def bot(c, r):
        return zmid(r) - bot0(c, r) * cap_b(r)

    relief_plate(bm, max(contour_loops(fld, 0.035), key=len), top, bot, 0.5, lambda c, r, t: M_HIDE)
    # flat overlapping shingle scales lying down the neck (toward the head): each a thin rounded
    # tongue whose back end tucks into the hide and whose front lip stands a little proud
    for i, r in enumerate((22.6, 24.2, 25.8, 27.4)):
        off = 0.0 if i % 2 == 0 else 1.1
        c = 12.6 + off
        while c < 37.0:
            if abs(c - AXIS) > 1.9 and d(c, r) > 1.3 and d(c, r + 1.3) > 0.9:
                path = []
                for t, ww in ((0.0, 0.55), (0.3, 1.0), (0.65, 1.05), (0.88, 0.8), (1.0, 0.0)):
                    rr = r - 0.6 + 1.9 * t
                    lift = -0.12 + 0.3 * t
                    path.append((c, rr, top(c, rr) + lift, 1.15 * ww, 0.16 if ww else 0.0))
                sweep(bm, path, SCALE_SEC, M_SCALE)
            c += 2.2


def build(coll):
    bm = bmesh.new()
    for left in (True, False):
        build_feathers(bm, left)
        build_horn(bm, left)
        build_blade(bm, left)
    loft_axis(bm, CORE, 12, 6, core_mat, top_exp=1.1)
    build_spine(bm)
    build_collar(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
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
    shells, total = [], 0
    for e in lay:
        name = e["model"]
        p = pieces[name]
        p.location = ((e["cx"] - CX0) / 12, -(e["cy"] - CY0) / 12, 0)
        bpy.context.view_layer.update()
        # D90/D118: the shell comes from a sealed copy taken before culling.
        sealed = p.copy()
        sealed.data = p.data.copy()
        coll.objects.link(sealed)
        loc = p.location.copy()
        sealed.location = (0, 0, 0)
        bpy.context.view_layer.update()
        sh = common.outline_shell(sealed, coll, voxel=0.03, faces=1200, inside=0.004)
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
