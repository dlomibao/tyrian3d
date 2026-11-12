"""GRYPHON (level 2.6 end boss), design B: silhouette and readability from the tilted game camera
first, then detail. newsh0.shp assembly, this batch's 13 pieces (two rows, 168 x 56 px:
newsh0-39..51 over newsh0-79..89); the top-row pieces (horn tips, left claw) are built for the fit
but not exported.

What it is: a blue bat-winged flying beast seen from above, flying down the screen at the player.
A spiny skull between two long horns swept back (up the screen), a broad dark jaw below it, a
ribbed grey scallop shell on each shoulder, and two huge feathered wings swept back to a grey claw
at each tip. Each wing: a bony leading edge (the forearm from the claw down to the elbow knob,
then the thick upper arm back to the shoulder), overlapping primary feathers lying along the span
whose tips make the fingers of the trailing (upper) edge, and a row of coverts over them.

Readability (the small tilted camera): a gull dihedral (the arm rises from the shoulder, the hand
flatter out to the tip), the shells standing up as raised fans, the horns rising toward their tips,
a high skull with a crest, overlapping feather blades with real steps between them.

Plan: every part's top view comes from the sprite's inner mask (D74): the wing plate is the
contour of the wing's mask region, smoothed; parts on top stay inside it.

Units: c, r = assembly px (pixel c spans [c, c + 1]); mirror axis at c = 96.5; Blender
X = (c - 96.5) / 12, Y = (56 - r) / 12 (row 56 is the batch's middle), z px / 12 up.

Exports every batch piece with its outline shell (D90/D118: from a sealed pre-cull copy) through
export_sprite_model (public/models/enemies/newsh0-NN.glb + its spriteModels entry); --no-export skips
that, --out writes one scratch GLB of all pieces in place, --review DIR renders the review views.

Fix round 3: the skull reads ribbed and spiny, not a smooth nose cone: a spine rib each side of the
crest (cols 92 / 100, rows 45-59, the sprite's bright stripe pairs) with two swept-back spikes each,
an outer rib over the brow (cols 88 / 104), and the snout broken into segments (two ridges along it at
cols 93 / 99 and three low transverse ribs at rows 67, 71, 75), its finish rougher (no glossy dome).
All inside the existing silhouette (top view unchanged).

Fix round 2: the mandible ring (two raised blue rib arcs from under the arms round the dark mouth to
the chin, pal 52 upper, 50 lower), chin tendrils, the snout ending at row 79.6 in a blunt nose (pal
50), the throat a low dark recess; pchip-resampled head, snout, throat and belly stations with rounded
back, chin and belly ends; the wing root tapers at its outline (no slab ends from the side).

Fix round 1: keeled horns that flatten toward the top cut (a flush lens end, not a round nozzle); a
domed skull, a snout rising out of the jaw, and a torso and shoulders under the wing roots (side
views); the chin ends at row 83.2 and the right jaw edge follows the sprite's own asymmetry.

Run: blender --background --python assembly-newsh0-79.py -- [--no-export] [--out x.glb] [--review DIR]
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

NAME = "assembly-newsh0-79"
AXIS = 96.5
ROW0 = 56.0
W, H = 168, 84
BATCH = ["newsh0-79", "newsh0-81", "newsh0-83", "newsh0-85", "newsh0-87", "newsh0-89", "newsh0-39",
         "newsh0-41", "newsh0-43", "newsh0-45", "newsh0-47", "newsh0-49", "newsh0-51"]


def X(c):
    return (c - AXIS) / 12


def Y(r):
    return (ROW0 - r) / 12


def CR(v):
    return v.x * 12 + AXIS, ROW0 - v.y * 12


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------------------------------
# Sprite and masks
# --------------------------------------------------------------------------------------------------

def compose_sprite():
    """The whole 168 x 84 creature as palette indices: every piece of newsh0-39's sprite.json
    `assemblyLayout` (also the top-row horn tips and claw) placed at its screen position
    (assembly pixel (0, 0) is screen (30, -32)); the colours of all of them."""
    lay = common.load_sprite(ROOT, "newsh0-39")["assemblyLayout"]
    idx = -np.ones((H, W), int)
    cols, boxes = {}, {}
    for e in lay:
        s = common.load_sprite(ROOT, e["model"])
        cols.update({int(k): tuple(v) for k, v in s["colors"].items()})
        px = np.array(s["frames"][0]["pixels"])
        h, w = px.shape
        x0, y0 = e["cx"] - w // 2 - 30, e["cy"] - h // 2 + 32
        m = px >= 0
        idx[y0:y0 + h, x0:x0 + w][m] = px[m]
        boxes[e["model"]] = (x0, y0)
    return idx, cols, boxes


IDX, COLORS, BOXES = compose_sprite()
MASKS = SM.masks(IDX.tolist(), COLORS)
F = np.array(MASKS["inner"], bool) | np.array(MASKS["free"], bool)
GREY = (IDX >= 3) & (IDX <= 14)

SUB = 3
PAD = 4


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


def region(cond):
    """F restricted by cond(c, r) (pixel centre), as a bool grid."""
    cc, rr = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    return F & cond(cc, rr)


# Wing (left): the mask west of column 86, minus the horn and the grey claw at the tip.
CLAW = GREY & (np.arange(W)[None, :] < 13)
WING_M = region(lambda c, r: (c < 86.5) & ~((r < 44) & (c > 77))) & ~CLAW
# Bridge the 1 px ink seams inside the wing (the claw's edge): fill tiny holes.
WING_FIELD = smooth_field(WING_M, 0.55)
WING_DIST = _chamfer(WING_FIELD >= 0.5)


def wing_dist(c, r):
    return field_at(WING_DIST, c, r) if field_at(WING_FIELD, c, r) >= 0.5 else 0.0


def col_extent(mask, c):
    rs = np.where(mask[:, int(c)])[0]
    return (rs.min(), rs.max() + 1) if len(rs) else (None, None)


# --------------------------------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------------------------------

class Mats:
    def __init__(self):
        self.sprite = {"name": NAME, "colors": {str(k): list(v) for k, v in COLORS.items()}}
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.0, roughness=0.6):
        key = (index, metallic, roughness)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nsh079b{len(self.list)}", metallic=metallic,
                                        roughness=roughness)
            m.name = f"pal_{index}_nsh079b_{len(self.list)}"
            self.list.append(m)
        return self.slots[key]


MAT = Mats()
# Palette indices (sprite region medians, blueprint/region_colours.json): wing navy 53 (outer) / 54
# (mid), bones 55, arm underside 49, claw 7, shell 8, horn 55, skull 53, snout 49-50.
M_PLATE = MAT(52, 0.0, 0.7)        # wing membrane between the feathers (reads as the grooves)
M_PRIM = MAT(53, 0.05, 0.55)       # primary feathers
M_COV = MAT(54, 0.05, 0.5)         # coverts
M_BONE = MAT(55, 0.05, 0.42)       # forearm bone
M_ARM = MAT(54, 0.05, 0.5)         # upper arm, elbow knob
M_DARK = MAT(49, 0.0, 0.8)         # jaw flaps beside the snout, under the arm
M_CLAW = MAT(7, 0.15, 0.4)         # claw
M_SHELL = MAT(7, 0.15, 0.5)        # shell base (between the ribs)
M_RIB = MAT(9, 0.15, 0.4)          # shell ribs
M_HORN = MAT(55, 0.05, 0.42)       # horns
M_SKULL = MAT(53, 0.05, 0.55)      # skull
M_CREST = MAT(55, 0.05, 0.45)      # crest, brows
M_SPIKE = MAT(56, 0.05, 0.4)       # spikes
M_JAW = MAT(50, 0.0, 0.72)        # snout (sprite median of the snout proper, cols 90-102 rows 64-78: 50)
M_JAWR = MAT(52, 0.0, 0.55)        # jaw ridges
M_MAND_HI = MAT(52, 0.05, 0.42)   # fix 2: mandible ring, upper arc (its crest pixels 51-54, rows 71-73)
M_MAND_LO = MAT(50, 0.05, 0.45)   # fix 2: mandible ring, lower arc and chin; chin tendrils (48-50)
M_EYE = MAT(59, 0.0, 0.2)         # eyes: the sprite's bright pair (pal 59-60) at cols 91-92 / 99-100, row 62


# --------------------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------------------

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


def mirror_all(bm):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


# --------------------------------------------------------------------------------------------------
# The beast (px: c east, r south, z up)
# --------------------------------------------------------------------------------------------------

def dih(c):
    """Gull dihedral: the arm rises from the shoulder (c 86) to the elbow (c 48), the hand flatter."""
    c = min(c, 86.0)
    z = 2.5 + 0.21 * (86 - max(c, 48))
    if c < 48:
        z += 0.1 * (48 - c)
    return z


# Leading edge: forearm from the claw base to the elbow, then the upper arm to the shoulder.
# The bone is one continuous tube: it starts inside the claw's root (the claw's last pixels reach row
# 31), runs down the leading edge to the elbow knuckle, turns there and runs on as the arm.
FOREARM = [(7.6, 27.0), (9.5, 30.5), (13.5, 36), (18, 41.5), (23, 47), (28, 52), (33, 56.5), (38, 61), (42.5, 65),
           (45.2, 67.8), (46.6, 69.2)]
ELBOW = FOREARM[-1]
UPPERARM = [ELBOW, (50, 67.0), (54, 64.9), (58, 63.4), (64, 62.8), (71, 62.8), (78, 62.7), (84, 62.5)]


def _seg_dist(p, poly):
    best = 1e9
    q = Vector(p)
    for a, b in zip(poly, poly[1:]):
        a, b = Vector(a), Vector(b)
        t = max(0.0, min(1.0, (q - a).dot(b - a) / max((b - a).length_squared, 1e-9)))
        best = min(best, (q - (a + (b - a) * t)).length)
    return best


LE = FOREARM + UPPERARM[1:]


def wing_top(c, r):
    d_edge = wing_dist(c, r)
    rnd = math.sqrt(min(1.0, (d_edge + 0.35) / 3.0))
    d_le = _seg_dist((c, r), LE)
    span = smoothstep(4, 80, c)
    thick = 1.1 + (1.0 + 2.6 * span) * math.exp(-d_le / 9.0)
    return dih(c) + thick * rnd


def wing_bot(c, r):
    d_edge = wing_dist(c, r)
    rnd = math.sqrt(min(1.0, (d_edge + 0.35) / 3.0))
    d_le = _seg_dist((c, r), LE)
    span = smoothstep(4, 80, c)
    # Fix 1: a fleshy shoulder under the wing root (it thickens toward the body and runs into the
    # torso), so the side view sees a rounded flank, not the flat underside of a plank.
    root = 2.6 * smoothstep(62, 86, c)
    # Fix 2: the root's bulk tapers in over the 6 px inside the outline, so the wing root's edges
    # (rows ~49 and ~66 by the body) are no vertical slab ends from the side.
    return dih(c) - (0.5 + 1.6 * span * math.exp(-d_le / 7.0)) * rnd - root * smoothstep(0.0, 6.0, d_edge)


def wing_mat(c, r, top):
    if r > 66.5 and c > 56:
        return M_DARK
    return M_PLATE


def build_wing(bm):
    loops = contour_loops(WING_FIELD, 0.08)
    loop = max(loops, key=lambda lp: abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(lp, lp[1:] + lp[:1]))))
    print("wing loop", len(loop), "points;", len(loops), "loops")
    relief_plate(bm, loop, wing_top, wing_bot, 2.5, wing_mat)

    # Feathers: three shingled rows of broad blades lying along the span (tip -> root runs down
    # toward the body), primaries at the trailing edge (their tips are the edge's fingers), then
    # secondaries and coverts each a step higher toward the leading edge. Each blade's width is held
    # inside the mask, so the plan stays the sprite's.
    d = Vector((0.72, 0.69)).normalized()  # tip -> root
    blades = []
    rows = (
        # (tip columns, chord fraction of the tip from the trailing edge, length, half width, lift, mat)
        ([11.0, 14.5, 18.0, 21.5, 25.0, 28.5, 32.0, 35.5, 39.0, 42.5, 46.5, 50.5, 54.5, 58.5, 62.5], 0.0, 30.0, 3.0,
         0.25, M_PRIM),
        ([16, 20.5, 25, 29.5, 34, 38.5, 43, 47.5, 52, 56.5, 61, 65.5, 70], 0.34, 22.0, 3.0, 1.0, M_COV),
        ([24, 29.5, 35, 40.5, 46, 51.5, 57, 62.5, 68, 73.5], 0.64, 14.0, 3.0, 1.75, M_COV),
    )
    for cols, frac, length, w0, lift, mat in rows:
        for i, c in enumerate(cols):
            r0, r1 = col_extent(WING_M, c)
            if r0 is None:
                continue
            tip = Vector((c, r0 + 0.6 + frac * (r1 - r0)))
            blades.append((tip, d, length, w0, lift + 0.05 * (len(cols) - i), mat))
    # Rounded edges with a flat crown (a square-root fall-off toward the outline), not a lens.
    BLADE = [(1, 0.1), (0.9, 0.6), (0.55, 0.92), (0, 1.0), (-0.55, 0.92), (-0.9, 0.6), (-1, 0.1), (-0.8, -0.45),
             (0.8, -0.45)]
    for tip, dd, length, w0, lift, mat in blades:
        n = max(5, int(length / 3.0))  # fix 2: fewer stations (triangle budget; the bow stays smooth)
        path = []
        for k in range(n + 1):
            s = k / n  # 0 tip .. 1 root
            p = tip + dd * (length * s)
            p = p + Vector((-dd.y, dd.x)) * (0.9 * math.sin(math.pi * s))
            c, r = p.x, p.y
            if s < 0.3:
                prof = math.sqrt(max(0.0, 1 - ((0.3 - s) / 0.32) ** 2))
            else:
                prof = 1.0 - 0.5 * smoothstep(0.55, 1.0, s)
            w = min(w0 * prof, wing_dist(c, r) - 0.2)
            if r > 61.0 and c > 50:  # the blades end at the arm; its dark skin fold stays visible below
                w = 0.0
            z = wing_top(c, r) + lift - 0.25
            if k == 0 or k == n or w < 0.35:
                path.append((c, r, z, 0.0, 0.0))
                if k > 0:
                    break
                continue
            path.append((c, r, z, w, min(0.7, 0.3 * w)))
        if len([q for q in path if q[3] > 0]) >= 2:
            sweep(bm, path, BLADE, mat)

    # Forearm bone along the leading edge, then the thick upper arm (its underside is lit dark).
    fp = []
    for i, (c, r) in enumerate(FOREARM):
        t = i / (len(FOREARM) - 1)
        w = 1.1 + 1.2 * t
        fp.append((c, r, wing_top(c, r) - 0.2, w, w * 0.8))
    sweep(bm, fp, ROUND8, M_BONE)
    ap = []
    for i, (c, r) in enumerate(UPPERARM):
        bl = smoothstep(46, 53, c)
        z = (1 - bl) * (wing_top(c, r) - 0.2) + bl * (dih(c) + 0.9)
        w = 2.3 + 1.3 * smoothstep(46.5, 60, c)
        ap.append((c, r, z, w, 0.8 * w))
    sweep(bm, ap, ROUND10, M_ARM)
    # A lit bone ridge on the arm's leading flank (the sprite's bright line along rows 63-64).
    sweep(bm, [(52, 66.0, dih(52) + 3.2, 0.0, 0.0), (56, 64.4, dih(56) + 3.5, 1.1, 0.7),
               (64, 63.6, dih(64) + 3.7, 1.4, 0.8), (72, 63.6, dih(72) + 3.7, 1.3, 0.8),
               (79, 63.6, dih(79) + 3.7, 0.0, 0.0)], ROUND6, M_BONE)
    # The skin fold under the arm (the sprite's dark strip, rows 66-68, pal 49): a low flap on the
    # membrane, sloping off the arm's flank.
    FOLD = [(55.5, 67.6), (60, 67.2), (66, 67.2), (72, 67.2), (78, 67.0), (83, 66.8)]
    fz = lambda c, r: wing_top(c, r) + 0.15  # noqa: E731
    sweep(bm, [(FOLD[0][0], FOLD[0][1], fz(*FOLD[0]), 0.0, 0.0)]
          + [(c, r, fz(c, r), 2.1, 0.6) for c, r in FOLD[1:-1]] + [(FOLD[-1][0], FOLD[-1][1], fz(*FOLD[-1]), 0.0, 0.0)],
          [(1, 0.0), (0.75, 0.75), (-0.75, 0.75), (-1, 0.0), (-0.75, -0.8), (0.75, -0.8)], M_DARK)
    # Elbow knuckle: grows out of the bone at the turn (no loose sphere).
    ellipsoid(bm, ELBOW[0] + 0.3, ELBOW[1] - 0.2, wing_top(*ELBOW) + 0.3, 3.6, 3.0, 2.3, M_ARM, seg=14, rings=7)

    # Claw at the tip: a grey talon hooking up from the wrist.
    cl = []
    for r in np.arange(11.0, 29.6, 1.6):
        cs = np.where(CLAW[int(r)])[0] if CLAW[int(r)].any() else None
        if cs is None:
            continue
        c0, c1 = cs.min() + 0.15, cs.max() + 0.85
        cl.append(((c0 + c1) / 2, r, (c1 - c0) / 2))
    claw = [(cl[0][0], cl[0][1] - 0.6, dih(7) + 5.0, 0.0, 0.0)]
    for c, r, w in cl:
        t = (r - 11) / 18.6
        claw.append((c, r, dih(c) + 1.6 + 3.4 * (1 - t) ** 1.6, w, w * 0.8))
    claw.append((cl[-1][0] + 0.8, cl[-1][1] + 1.2, dih(9) + 1.6, 0.0, 0.0))
    sweep(bm, claw, ROUND8, M_CLAW)


# Shoulder shell: the grey fan on each shoulder (sprite cols 61-84, rows 42-58).
SHELL_HUB = (80.5, 57.5)
SHELL_TIPS = [(62.5, 45.2), (66.5, 43.6), (71.0, 43.0), (75.5, 43.2), (80.0, 44.0), (83.0, 46.5)]


def build_shell(bm):
    m = GREY & F & (np.arange(W)[None, :] > 58) & (np.arange(W)[None, :] < 86)
    m[:38] = False
    m[60:] = False
    # include the ink seams between the ribs
    mm = m.copy()
    mm[1:-1, 1:-1] |= (m[:-2, 1:-1] & m[2:, 1:-1]) | (m[1:-1, :-2] & m[1:-1, 2:])
    fld = smooth_field(mm, 0.5)
    loops = contour_loops(fld, 0.08)
    loop = max(loops, key=lambda lp: abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(lp, lp[1:] + lp[:1]))))
    dist = _chamfer(fld >= 0.5)

    def top(c, r):
        d = field_at(dist, c, r) if field_at(fld, c, r) >= 0.5 else 0.0
        f = min(1.0, (d + 0.08) / 4.0) ** 0.6  # fix 1: rounded rim, no standing wall at the edge
        back = smoothstep(58, 42, r)  # the fan stands up toward its upper (back) edge
        base = wing_top(min(c, 85), r) + 0.3
        return base + (2.5 + 5.0 * back) * f

    relief_plate(bm, loop, top, lambda c, r: wing_top(min(c, 85), r) - 1.0, 2.0, lambda c, r, t: M_SHELL)
    hub = Vector(SHELL_HUB)
    for tip in SHELL_TIPS:
        tip = Vector(tip)
        path = []
        for k, (f, ww) in enumerate(((0.0, 0.0), (0.06, 1.0), (0.3, 1.25), (0.55, 1.2), (0.8, 0.95), (0.94, 0.6),
                                     (1.0, 0.0))):
            p = tip + (hub - tip) * f
            if field_at(fld, p.x, p.y) < 0.5:
                continue
            w = min(1.6 * ww, max(0.0, field_at(dist, p.x, p.y) - 0.2)) if 0 < f < 1 else 0.0
            path.append((p.x, p.y, top(p.x, p.y) - 0.15, w, 0.0 if w == 0 else 0.75 * w))
        sweep(bm, path, ROUND8, M_RIB)
    # hinge knuckle at the hub
    ellipsoid(bm, SHELL_HUB[0] - 1.0, SHELL_HUB[1] - 1.0, top(SHELL_HUB[0] - 1, SHELL_HUB[1] - 1) - 0.4, 2.2, 2.0, 1.4,
              M_SHELL, seg=10, rings=5)


# Horn section (fix 1): a keeled horn, not a round tube: a ridge along the top, flatter flanks and a
# shallow belly. Its height falls faster than its width toward the tip, so the end at the batch's
# top cut (row 28; the tips are the upper batch's) is a flat flush lens, not a round nozzle.
# (u scaled 0.95: the old round section's width, which the plan was fitted to.)
HORN_SEC = [(0.95 * u, v) for u, v in ((1.0, 0.0), (0.78, 0.5), (0.42, 0.86), (0.0, 1.0), (-0.42, 0.86),
                                       (-0.78, 0.5), (-1.0, 0.0), (-0.7, -0.5), (0.0, -0.66), (0.7, -0.5))]


def build_horn(bm):
    rows = []
    for r in range(0, 44):
        cs = np.where(F[r, 78:97])[0]
        if len(cs):
            rows.append((r + 0.5, 78 + cs.min(), 78 + cs.max() + 1))
    path = [(rows[0][1] + 0.5, -0.1, 14.5, 0.0, 0.0)]
    rr = np.array([q[0] for q in rows])
    cc = np.array([(q[1] + q[2]) / 2 for q in rows])
    ww = np.array([(q[2] - q[1]) / 2 for q in rows])
    ker = np.ones(5) / 5
    cs_ = np.convolve(np.pad(cc, 2, mode="edge"), ker, "valid")
    ws_ = np.convolve(np.pad(ww, 2, mode="edge"), ker, "valid")
    for r, cm, wm in list(zip(rr, cs_, ws_))[1::2]:
        c0, c1 = cm - wm, cm + wm
        w = wm + 0.2
        t = r / 44
        ring = 1.0 + 0.03 * math.cos(2 * math.pi * r / 4.0) * smoothstep(8, 20, r)  # growth rings
        z = 14.5 - 5.5 * t
        hr = 0.42 + 0.4 * smoothstep(26, 44, r)  # flat toward the tip, full at the root
        path.append(((c0 + c1) / 2, r, z, w * ring, w * hr * ring))
    # into the skull
    for r, c, w in ((44.5, 89.2, 5.6), (47.5, 90.2, 5.0), (50.5, 91.2, 3.0)):
        path.append((c, r, 8.4 - (r - 44.5) * 0.2, w, w * 0.8))
    path.append((92.0, 52.5, 7.0, 0.0, 0.0))
    sweep(bm, path, HORN_SEC, M_HORN)


# Skull and jaw: (row, half width, top z, side z, bottom z) px.
# Fix 1: a domed skull (top_exp 1.3, flanks leaning in) with a rounded back (no vertical back plate
# between the horns) and a shallow round belly that meets the wing roots' underside (no deep slab
# under the wing).
# Fix 2: the back of the skull rounds over into the horn roots (it starts low and rises over two
# rows, no vertical plate), the cheeks round under, and the stations are pchip-resampled so the side
# profile is one curve. The widths (the plan) are fix 1's.
HEAD = pchip_stations([(43.9, 3.2, 7.2, 6.4, 5.2), (44.4, 7.4, 9.4, 6.0, 3.2), (45.2, 9.8, 11.3, 5.5, 1.2),
                       (47.0, 11.0, 13.0, 5.0, -0.6), (52.0, 11.6, 14.2, 5.0, -1.4), (57.0, 11.4, 13.0, 4.8, -1.8),
                       (61.0, 11.2, 12.0, 4.5, -2.0), (64.0, 11.6, 10.6, 4.0, -1.8), (67.0, 11.8, 8.4, 3.6, -1.4),
                       (68.6, 9.0, 6.4, 3.4, -0.8), (69.4, 6.0, 5.0, 3.2, 0.4)], 1.4)
HEAD_EXP = 1.3
# The muzzle: the sprite's central snout (cols 88-104 at row 70 narrowing to 93-99 at row 78), a V
# from under the skull to a blunt round nose at row 79.6, pointing at the player.
# Fix 2: it ends where the sprite's snout ends (row 79); below it is the dark mouth with the chin
# tendrils, ringed by the mandible arcs (build_jaw). Its bottom rises toward the nose, so from the
# side it is a rounded snout, not a plank ending in a wedge.
MUZZLE = pchip_stations([(62.5, 8.6, 10.8, 4.2, 0.6), (66.0, 9.0, 10.1, 3.9, 0.8), (70.0, 8.4, 9.0, 3.6, 1.1),
                         (73.0, 7.6, 8.0, 3.4, 1.5), (75.5, 6.6, 7.0, 3.2, 1.9), (77.5, 5.2, 6.0, 3.1, 2.4),
                         (78.8, 3.6, 5.1, 3.1, 2.8), (79.6, 1.6, 4.3, 3.4, 3.2)], 1.2)
MUZZLE_EXP = 1.15
# The throat under it: the dark recess (pal 49) filling the jaw's wide V outline between the
# snout and the mandible ribs; fix 2 drops its crown (it is the negative space now) and rounds its
# belly up into the chin.
THROAT = pchip_stations([(60.0, 8.5, 3.8, 2.0, -1.6), (63.0, 12.0, 3.9, 1.8, -2.2), (68.0, 13.6, 3.6, 1.5, -2.2),
                         (72.0, 13.6, 3.3, 1.3, -1.6), (76.0, 12.8, 3.0, 1.1, -0.8), (80.0, 11.8, 2.8, 1.0, -0.3),
                         (82.3, 10.8, 2.7, 1.0, 0.1), (83.0, 9.6, 2.5, 1.1, 0.4), (83.15, 7.4, 2.2, 1.2, 0.8),
                         (83.32, 4.0, 1.8, 1.3, 1.2)], 1.5)
THROAT_EXP = 1.1
LOFT_EXP = {id(HEAD): HEAD_EXP, id(MUZZLE): MUZZLE_EXP, id(THROAT): THROAT_EXP}


def loft_top(sections, c, r):
    if not sections[0][0] <= r <= sections[-1][0]:
        return None
    w = interp(sections, r, 1)
    u = (c - AXIS) / max(w, 1e-6)
    if abs(u) >= 1:
        return None
    s = math.sqrt(1 - u * u)
    zt, zs = interp(sections, r, 2), interp(sections, r, 3)
    return zs + (zt - zs) * s ** LOFT_EXP.get(id(sections), 0.75)


def head_top(c, r):
    zs = [z for z in (loft_top(L, c, r) for L in (HEAD, MUZZLE, THROAT)) if z is not None]
    return max(zs) if zs else 2.0


def head_mat(r, s, top):
    return M_SKULL


def on_head(path, lift=0.0):
    return [(c, r, head_top(c, r) + lift, w, h) for c, r, w, h in path]


EYE = (92.5, 62.5)


def build_head_left(bm):
    """Left-side details of the head (mirrored with the wing)."""
    # Brow ridge from the horn base in toward the crest, over the eye.
    sweep(bm, on_head([(88.0, 47.0, 0.0, 0.0), (88.6, 49.5, 1.4, 1.0), (90.0, 53.0, 1.5, 1.0),
                       (92.0, 55.2, 1.3, 0.9), (94.5, 56.5, 0.0, 0.0)], -0.25), ROUND6, M_CREST)
    # Cheek ridge down the side of the head to the jaw.
    sweep(bm, on_head([(87.0, 52.0, 0.0, 0.0), (86.6, 56.0, 1.4, 0.9), (86.6, 61.0, 1.6, 1.0),
                       (86.0, 65.0, 1.6, 1.0), (85.6, 68.5, 0.0, 0.0)], -0.3), ROUND6, M_CREST)
    # Eye: a glossy dome standing on the skull at the sprite's bright pixels (cols 91-92 / 99-100,
    # row 62; the mirror puts the pair at 92.5 / 100.5, within half a pixel of both), under the brow.
    ellipsoid(bm, EYE[0], EYE[1], head_top(*EYE) - 0.35, 1.45, 1.1, 1.0, M_EYE, seg=12, rings=6)
    # Mandible ridges along the muzzle's edges (the V lines of the jaw: the sprite's cheek bands,
    # cols 87-89 rows 63-75, set off from the snout by the ink slit at col 90), to the nose.
    path = [(AXIS - interp(MUZZLE, 64.0, 1) + 1.2, 64.0, 0.0, 0.0)]
    for r in (66.0, 69.0, 72.0, 75.0, 77.5):
        path.append((AXIS - interp(MUZZLE, r, 1) + 1.0, r, 1.2, 0.8))
    path.append((AXIS - 2.2, 79.3, 0.0, 0.0))
    sweep(bm, on_head(path, -0.35), ROUND6, M_JAWR)
    build_skull_ribs_left(bm)
    build_jaw_left(bm)


def build_skull_ribs_left(bm):
    """Fix 3: the sprite's head is ribbed (bright stripe pairs at cols 92 / 100 and 87-88 / 104-105,
    rows 45-59; ink slits at cols 90 / 102). A spine rib each side of the crest with two spikes swept
    back (up the screen), an outer rib inside the brow, and segment ridges along the snout."""
    sweep(bm, on_head([(92.4, 44.6, 0.0, 0.0), (92.3, 46.0, 0.9, 0.9), (92.2, 50.0, 1.05, 1.1),
                       (92.3, 54.0, 1.0, 1.0), (92.6, 57.5, 0.85, 0.8), (92.9, 59.6, 0.0, 0.0)], -0.2),
          ROUND6, M_CREST)
    for r in (48.5, 54.0):
        z = head_top(92.3, r)
        sweep(bm, [(92.3, r + 1.8, z + 0.2, 0.0, 0.0), (92.3, r + 0.9, z + 0.5, 1.0, 0.9),
                   (92.3, r - 0.3, z + 1.5, 0.6, 0.55), (92.3, r - 1.3, z + 2.6, 0.0, 0.0)], ROUND6, M_SPIKE)
    sweep(bm, on_head([(88.4, 47.2, 0.0, 0.0), (88.0, 49.0, 0.8, 0.8), (87.9, 52.5, 0.9, 0.85),
                       (88.3, 56.0, 0.75, 0.7), (88.8, 58.2, 0.0, 0.0)], -0.25), ROUND6, M_CREST)
    # Snout ridges (cols 93 / 99: the sprite's lit lines down the snout, rows 64-77).
    sweep(bm, on_head([(93.6, 63.6, 0.0, 0.0), (93.5, 65.5, 0.8, 0.7), (93.6, 69.5, 0.85, 0.7),
                       (93.9, 73.5, 0.75, 0.6), (94.3, 76.5, 0.6, 0.5), (94.6, 78.0, 0.0, 0.0)], -0.25),
          ROUND6, M_JAWR)


def build_snout_segments(bm):
    """Fix 3: three low transverse ribs across the snout (rows 67, 71, 75), so it reads as plated
    segments from the tilted camera, not one glossy dome."""
    for r, half in ((67.0, 6.6), (71.0, 6.0), (75.0, 4.8)):
        pts = []
        n = 9
        for k in range(n):
            u = -1 + 2 * k / (n - 1)
            c = AXIS + u * half
            w = 0.0 if k in (0, n - 1) else 0.55
            pts.append((c, r + 0.35 * u * u, w, 0.5 * w / 0.55 if w else 0.0))
        sweep(bm, on_head(pts, -0.15), ROUND6, M_JAWR)


def jaw_surf(c, r):
    """The surface under the jaw's ribs: the throat / snout, or the wing plate where the arc runs out
    onto the arm's dark fold."""
    zs = [z for z in (loft_top(L, c, r) for L in (HEAD, MUZZLE, THROAT)) if z is not None]
    if field_at(WING_FIELD, min(c, 86.0), r) >= 0.5 and c < 87.5:
        zs.append(wing_top(min(c, 86.0), r))
    return max(zs) if zs else 1.5


# Fix 2: the mandible ring. In the sprite (rows 67-83) the lower jaw is a curved blue rib that comes
# out from under the arm at col ~79, row 70 (pal 50-54, its lit crest 52-54 at rows 71-73), sweeps
# down round the mouth (cols 84-88, rows 74-80) and closes at the chin (rows 81-83, pal 48-50); the
# dark channel inside it (the ink at cols 86-88, rows 67-75) and the dark mouth under the snout
# (rows 79-82) are the throat's recess. Two short tendrils hang from the snout's nose (col 93, rows
# 79-80; mirrored).
MAND = [(77.8, 69.5, 0.0), (79.8, 70.1, 1.35), (81.9, 71.1, 1.75), (83.7, 72.5, 1.6), (84.9, 74.3, 1.35),
        (85.5, 76.3, 1.2), (86.2, 78.2, 1.1), (87.4, 80.0, 1.05), (89.2, 81.4, 1.0), (91.8, 82.1, 0.95),
        (94.6, 82.35, 0.9), (97.2, 82.35, 0.9), (98.6, 82.35, 0.0)]


def build_jaw_left(bm):
    def ribpath(pts, lift):
        out = []
        for c, r, w in pts:
            out.append((c, r, jaw_surf(c, r) + lift * (0.6 + 0.4 * min(1.0, w)), w, 0.85 * w))
        return out

    upper = [q for q in MAND if q[1] <= 76.4]
    lower = [q for q in MAND if q[1] >= 76.2]
    # The lit upper arc (pal 52) and the dark lower arc and chin (pal 50) overlap one station.
    sweep(bm, ribpath(upper + [(lower[1][0], lower[1][1], 0.0)], 0.55), ROUND8, M_MAND_HI)
    sweep(bm, ribpath([(upper[-2][0], upper[-2][1], 0.0)] + lower, 0.55), ROUND8, M_MAND_LO)
    # Chin tendrils under the nose.
    nose = loft_top(MUZZLE, 93.4, 78.4) or 4.0
    sweep(bm, [(93.4, 77.6, nose - 0.4, 0.0, 0.0), (93.4, 78.6, nose - 0.6, 0.75, 0.6),
               (93.3, 79.8, jaw_surf(93.3, 79.8) + 0.5, 0.6, 0.5), (93.2, 80.9, jaw_surf(93.2, 80.9) + 0.25, 0.0, 0.0)],
          ROUND6, M_MAND_LO)


# Torso (fix 1): the beast's body under the head and the wing roots, a rounded belly between the
# wings. Its crown stays inside the head and under the wings, so the top view is unchanged; from the
# side and front it gives the head and wings a body to sit on (no slab or open slots at the neck).
# Fix 2: pchip stations and a belly that curves (deepest at row 57), not a drum with a flat floor;
# both ends close to a small cap (no vertical end plates in the side view).
TORSO = pchip_stations([(44.3, 2.4, 1.6, 1.2, 0.8), (45.0, 6.0, 2.0, 1.0, -0.5), (48.0, 14.0, 2.5, 0.8, -2.6), (52.0, 17.0, 2.7, 0.7, -4.0),
                        (57.0, 18.0, 2.8, 0.6, -4.7), (61.0, 17.6, 2.8, 0.6, -4.4), (64.0, 16.0, 2.6, 0.6, -3.6),
                        (67.0, 12.0, 2.2, 0.6, -2.4), (69.5, 7.0, 1.8, 0.8, -1.0),
                        (70.8, 2.5, 1.4, 1.0, 0.6)], 1.5)


def build_centre(bm):
    loft_axis(bm, TORSO, 10, 4, lambda r, ss, t: M_PLATE, top_exp=1.0)
    loft_axis(bm, HEAD, 20, 6, head_mat, top_exp=HEAD_EXP)
    loft_axis(bm, MUZZLE, 14, 6, lambda r, ss, t: M_JAW, top_exp=MUZZLE_EXP)
    loft_axis(bm, THROAT, 14, 6, lambda r, ss, t: M_DARK, top_exp=THROAT_EXP)
    # Crest down the skull with three spikes swept back.
    crest = [(AXIS, r, head_top(AXIS, r) - 0.3, w, h) for r, w, h in
             ((43.9, 0.0, 0.0), (45.0, 1.4, 1.0), (50.0, 1.8, 1.3), (57.0, 1.8, 1.3), (63.0, 1.5, 1.0),
              (67.0, 0.0, 0.0))]
    sweep(bm, crest, ROUND6, M_CREST)
    for r in (46.0, 51.5, 57.0):
        z = head_top(AXIS, r)
        sweep(bm, [(AXIS, r + 2.4, z + 0.3, 0.0, 0.0), (AXIS, r + 1.2, z + 0.6, 1.5, 1.2),
                   (AXIS, r - 0.4, z + 2.0, 0.9, 0.8), (AXIS, r - 1.6, z + 3.6, 0.0, 0.0)], ROUND6, M_SPIKE)
    # Ridge down the middle of the jaw.
    sweep(bm, on_head([(AXIS, 64.5, 0.0, 0.0), (AXIS, 68.0, 1.6, 0.9), (AXIS, 74.0, 1.4, 0.8),
                       (AXIS, 78.0, 0.9, 0.55), (AXIS, 79.5, 0.0, 0.0)], -0.3), ROUND6, M_JAWR)
    build_snout_segments(bm)


JAW_SHIFT = 0.8


def jaw_asymmetry(bm, d=JAW_SHIFT):
    """Fix 1: the sprite is not mirror-exact along the jaw's lower right edge: its ring runs 1 px
    further in on the right (cols 106-118, rows 70-82; the left's ring at col 85 mirrors to col 108,
    the right's is at col 106). Slide the right half's verts there in by d px (west), ramped in over
    cols 98.5-103.5 (inside the muzzle) and rows 68-70, out past col 121 (the wing's bottom)."""
    for v in bm.verts:
        c, r = CR(v.co)
        if c <= AXIS + 1:
            continue
        k = smoothstep(98.5, 103.5, c) * smoothstep(68.0, 70.0, r) * (1 - smoothstep(121.0, 124.0, c))
        if k > 0:
            v.co.x -= d * k / 12


def build(coll):
    bm = bmesh.new()
    build_wing(bm)
    build_shell(bm)
    build_horn(bm)
    build_head_left(bm)
    mirror_all(bm)
    build_centre(bm)
    jaw_asymmetry(bm)
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
# Pieces, culling, export
# --------------------------------------------------------------------------------------------------

def piece_boxes():
    return {n: BOXES[n] for n in BATCH}


def split_pieces(obj, coll):
    out = {}
    for name, (c0, r0) in piece_boxes().items():
        x0, y0 = X(c0 + 12), Y(r0 + 14)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
                for f in res["faces"]:
                    f.smooth = False
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        p = bpy.data.objects.new(name, me)
        coll.objects.link(p)
        p.location = (x0, y0, 0)
        out[name] = p
    return out


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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    print("whole tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))
    pieces = split_pieces(obj, coll)
    shells, total = [], 0
    for name, p in pieces.items():
        # D90/D118: the shell comes from a sealed copy taken before culling.
        sealed = p.copy()
        sealed.data = p.data.copy()
        coll.objects.link(sealed)
        loc = p.location.copy()
        sealed.location = (0, 0, 0)
        bpy.context.view_layer.update()
        sh = common.outline_shell(sealed, coll, voxel=0.03, faces=900, inside=0.004)
        sh.name = sh.data.name = f"{name}_outline"
        sh.location = loc
        bpy.data.objects.remove(sealed, do_unlink=True)
        shells.append(sh)
        n = cull_hidden(p) if "--nocull" not in argv else 0
        p.data.set_sharp_from_angle(angle=math.radians(40))
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: culled {n}, {tris} tris")
    print("total tris", total)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        (rv / "materials.json").write_text(json.dumps(sorted({k[0] for k in MAT.slots})))
        (rv / "tris.txt").write_text(f"triangles: {total} over 13 pieces (after culling hidden faces)")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + shells, out)
        print("exported", out)
    if "--review" in argv:
        review(obj, list(pieces.values()), shells, Path(argv[argv.index("--review") + 1]))
    if "--no-export" not in argv:
        export_pieces(pieces, shells)


def export_pieces(pieces, shells):
    """Each piece at its own origin with its outline shell, through the sprite-model contract
    (public/models/enemies/<piece>.glb and its spriteModels entry, every sprite frame)."""
    for sh in shells:
        sh.hide_render = False
    for name in BATCH:
        p = pieces[name]
        sh = next(s for s in shells if s.name == f"{name}_outline")
        p.location = (0, 0, 0)
        sh.location = (0, 0, 0)
        bpy.context.view_layer.update()
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", data["sprites"])


def review(whole, pieces, shells, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.world.color = (0.035, 0.04, 0.05)
    scene.render.resolution_percentage = 100
    whole.hide_render = True
    for s in shells:
        s.hide_render = True
    k = 8
    cx, cy = X(84), Y(42)  # centre of the 168 x 84 grid

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

    eng = {}
    for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = e
            eng["eevee"] = e
            break
        except TypeError:
            pass
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.view_settings.view_transform = "Standard"
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
        sh.cavity_type = "BOTH"
        sh.show_object_outline = False
        sh.show_specular_highlight = not flat
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    # Top views on the sprite grid (whole model for the full 168 x 84 composite).
    whole.hide_render = False
    for p in pieces:
        p.hide_render = True
    c = cam("top", (cx, cy, 30), (cx, cy, 0), ortho=W / 12, rx=W * k, ry=H * k)
    c.rotation_euler = (0, 0, 0)
    shot(out / "top_mask_whole.png", flat=True, transparent=True)
    whole.hide_render = True
    for p in pieces:
        p.hide_render = False
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_flat.png", flat=True)
    shot(out / "top_lit.png")
    mx = X(84)
    for nm, loc, look in (("front", (mx, -60, 0.3), (mx, 0, 0.3)), ("rear", (mx, 60, 0.3), (mx, 0, 0.3)),
                          ("side", (-60, Y(56), 0.3), (0, Y(56), 0.3))):
        cam(nm, loc, look, ortho=W / 12 * 1.02 if nm != "side" else 8.0, rx=1100, ry=300)
        shot(out / f"{nm}.png")
    d = 26
    ctr = Vector((mx, Y(52), 0.3))
    for nm, az, el in (("q_high", 35, 35), ("q_rear", 220, 32)):
        a, e = math.radians(az), math.radians(el)
        cam(nm, ctr + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), ctr,
            lens=50, rx=1000, ry=700)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam("game", ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=55, rx=1000, ry=600)
    shot(out / "game.png")
    cam("under", (cx, cy, -30), (cx, cy, 0), ortho=W / 12 * 1.02, rx=W * 5, ry=H * 5)
    shot(out / "under.png")
    for s in shells:
        s.hide_render = False
    cam("game_ink", ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=55, rx=1000, ry=600)
    shot(out / "game_shell.png")


if __name__ == "__main__":
    main()
