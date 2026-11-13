"""GRYPHON head and wing tips (level 2.6 end boss), design B: silhouette and readability from the
small tilted game camera first, then detail. One merged item, six models:

  newsh0-119 (+ -f2, -f3, -f4)  the head, frames 119 / 121 / 123 / 129 (one model per jaw pose)
  newsh0-1, newsh0-3            the left wing tip: grey wrist claw + primary feather lobe, its sliver
  newsh0-15, newsh0-53          the right wing tip: claw + lobe, and the outer wing tile below it
  newsh0-13                     one dark pixel inside newsh0-15's lobe: a sunk wing-edge fragment

What it is: the beast's head seen from above, flying down the screen at the player. A blue-steel
beast skull: a broad domed cranium running on from the neck collar, a pale crest down the middle
that forks over the snout into two upper fangs hanging over a deep dark mouth, raised horn blades
along each outer edge swept back to the collar, dark brow slots, slanted glowing red eyes in dark
sockets with nasal vents inboard of them, cheek plates with a strut along their top sweeping down
to two hinge sleeves; and a lower jaw (rami sliding out of the sleeves, a dark trough with three
teeth, a round chin) that slides forward and drops open: 123 shut (jaw 4 px up, level), 121 (2 px
up, 4 deg), 119 (8 deg), 129 wide open (2 px down, 12 deg). The tilted camera looks into the open
mouth: dark trough, teeth, the fangs above, the chin dropped below the cheeks.

Readability first (the head is 24 px on screen): high crest and horn blades (a clear spine), eyes
as emissive lenses set in dark sockets under the brow (they read as red slits at any tilt), a
mouth that is a real cavity with a dark floor, the jaw a separate solid whose chin drops.

Wings: the tips are the D170 wings' own geometry. The sprite's right tip (newsh0-15, -53 and -13)
is a pixel-exact mirror of its left tip (newsh0-1 + newsh0-39's outer columns) about pixel column
93 (c -> 186 - c; checked: 521 of 521 pixels agree), so the left wing of assembly-newsh0-79 is
rebuilt here verbatim (its code is copied below, unchanged) and cut into the tip pieces: newsh0-1
and newsh0-3 at their own boxes, newsh0-15 and newsh0-53 from the left boxes [1, 25] mirrored
about edge 93.5. Style, heights, feathers and the claw are D170's by construction.

Units: assembly px (D170 frame: newsh0-1 at x0 0, mirror axis 96.5; Blender X = (c - 96.5) / 12,
Y = (56 - r) / 12, z px / 12) for the wing; head-local px (Grid 24 x 28: X = (c - 12) / 12,
Y = (14 - r) / 12) for the head, which sits at assembly (85, 92) under the neck (assembly-newsh0-91
at (72, 64); its bottom edge is z 1.9-11.2 px, the head's top row matches it).

Run: blender -b --python assets/blender/enemies/newsh0-119.py -- [--no-export] [--out x.glb] [--review DIR]
Exports (public/models/enemies, src/render/spriteModels): every model at its own origin with its outline shell (D51; from
a sealed pre-cull copy, D90/D118).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as SM  # noqa: E402

NAME = "newsh0-119"
HEAD_MODELS = [(NAME, 119, 0, 8.0), (f"{NAME}-f2", 121, -2, 4.0), (f"{NAME}-f3", 123, -4, 0.0),
               (f"{NAME}-f4", 129, 2, 12.0)]  # (model, frame, jaw dy px, jaw drop deg)
LEFT_TIP = ("newsh0-1", "newsh0-3")
RIGHT_TIP = ("newsh0-15", "newsh0-53")
# Piece boxes (x0, y0) in the D170 assembly frame; the right tip sits 7 px inboard of a mirror of
# the left about 96.5 (the event places it there), exactly at the mirror about 93.5.
BOX = {"newsh0-1": (0, 0), "newsh0-3": (24, 0), "newsh0-13": (144, 0), "newsh0-15": (162, 0),
       "newsh0-53": (162, 28)}
TIP_MIRROR = 93.5  # pixel edge e -> 187 - e
HEAD_AT = (85, 92)
NECK_AT = (72, 64)

# ==================================================================================================
# D170's left wing (assembly-newsh0-79.py, lines 62-690, copied unchanged but for the material tag
# and the unused materials). Integration: this block should move into a shared lib_gryphon.py that
# both scripts import.
# ==================================================================================================
D170 = "assembly-newsh0-79"  # the wings this tip continues (its left wing is rebuilt verbatim below)
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
for _n in (NAME,) + RIGHT_TIP + ("newsh0-3", "newsh0-13"):
    COLORS.update({int(k): tuple(v) for k, v in common.load_sprite(ROOT, _n)["colors"].items()})
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
            m = common.palette_material(self.sprite, index, f"n119b{len(self.list)}", metallic=metallic,
                                        roughness=roughness)
            m.name = f"pal_{index}_n119b_{len(self.list)}"
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
    # (Finer rows at the tip, where the sprite's talon opens from 2 to 4 px in a row: the grid IoU of
    # newsh0-1 / -15 needs the tip's width, not a needle.)
    for r in [12.5, 13.5, 14.5, 15.5, 16.5] + list(np.arange(18.0, 29.6, 1.6)):
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


# ==================================================================================================
# Design B: the head, the tip pieces, export and review
# ==================================================================================================

class Frame:
    """Pixel (c, r) edges -> Blender units: X = (c - cx) / 12, Y = (ry - r) / 12."""

    def __init__(self, cx, ry):
        self.cx, self.ry = cx, ry

    def X(self, c):
        return (c - self.cx) / 12

    def Y(self, r):
        return (self.ry - r) / 12

    def CR(self, v):
        return v.x * 12 + self.cx, self.ry - v.y * 12


FH = Frame(12.0, 14.0)  # head-local (Grid 24 x 28)
AXE = 11.5               # the skull's mirror line (pixel edge)


def pfn(xs, ys):
    """A monotone cubic through (xs, ys), clamped outside (pchip, as D170's stations)."""
    m = _pchip_slopes(xs, ys)

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1])
    return f


def seg_d(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def sweep_f(bm, fr, path, section, mat, smooth=True):
    """D170's sweep in frame `fr`: path [(c, r, z_px, half_width_px, half_height_px)]."""
    if len(path) < 2:
        return []
    pts = [Vector((fr.X(c), fr.Y(r), z / 12)) for c, r, z, _, _ in path]
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


def ellipsoid_f(bm, fr, c, r, z, rx, ry, rz, mat, angle=0.0, seg=16, rings=8):
    """An ellipsoid (radii px) turned by `angle` about Z (radians, in the XY plane)."""
    before = set(bm.verts)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    ca, sa = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        lx, ly, lz = v.co.x * rx / 12, v.co.y * ry / 12, v.co.z * rz / 12
        v.co = Vector((fr.X(c) + lx * ca - ly * sa, fr.Y(r) + lx * sa + ly * ca, z / 12 + lz))
    for f in {f for v in set(bm.verts) - before for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


def pad_f(bm, fr, c, r, rx, ry, surf, mat, angle=0.0, lift=0.1, sink=0.06, depth=0.5, seg=24, rings=12):
    """A dark pad laid on a curved surface: an ellipse (radii px, turned by `angle`) whose every
    vertex follows surf(c, r) (px), its rim `sink` px under the surface and its middle `lift` px over
    it, the lower half `depth` px down. No edge stands proud of the dome on a slope (a flat ellipsoid
    there shows its downhill edge as a blade)."""
    before = set(bm.verts)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    ca, sa = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        u, w, h = v.co.x * rx, v.co.y * ry, v.co.z
        pc, pr = c + u * ca - w * sa, r - (u * sa + w * ca)  # as ellipsoid_f's turn; r runs down -Y
        s = surf(pc, pr)
        z = s - sink + (lift + sink) * h if h >= 0 else s - sink + depth * h
        v.co = Vector((fr.X(pc), fr.Y(pr), z / 12))
    for f in {f for v in set(bm.verts) - before for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


def relief_f(bm, fr, loop, top_fn, bot_fn, step, mat_fn, smooth_z=0, relax=0, band=3, lens=False):
    """D170's relief_plate in frame `fr`: a plate over the closed (c, r) loop on a step-px grid, its
    top at top_fn(c, r), bottom at bot_fn(c, r) (px); mat_fn(c, r, top) per face. `relax` Laplacian
    passes (x, y and z) over the top vertices within `band` edge hops of the rim even out the grid's
    sliver cells along the rolled-off wall (they shade as vertical streaks); the rim stays put, so
    the plan outline does not move. `lens` welds the top and bottom rims into one edge at their mean
    height: the rolled top meets the rolled underside in a round lip with no vertical wall band (a
    wall's quads shade in streaks under smooth normals)."""
    old_v, old_f = set(bm.verts), set(bm.faces)
    pts = [(fr.X(c), fr.Y(r)) for c, r in loop]
    ar = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if ar < 0:
        pts = pts[::-1]
    common.slab(bm, pts, 1.0, z=0.0)

    def new_geom():
        nv = [v for v in bm.verts if v not in old_v]
        nvs = set(nv)
        ne = list({e for v in nv for e in v.link_edges if all(w in nvs for w in e.verts)})
        nf = [f for f in bm.faces if f not in old_f]
        return nv + ne + nf

    cs = [c for c, _ in loop]
    rs = [r for _, r in loop]
    c = math.floor(min(cs)) + step
    while c < max(cs):
        bmesh.ops.bisect_plane(bm, geom=new_geom(), plane_co=(fr.X(c), 0, 0), plane_no=(1, 0, 0))
        c += step
    r = math.floor(min(rs)) + step
    while r < max(rs):
        bmesh.ops.bisect_plane(bm, geom=new_geom(), plane_co=(0, fr.Y(r), 0), plane_no=(0, 1, 0))
        r += step
    faces = [f for f in bm.faces if f not in old_f]
    caps = [f for f in faces if all(v.co.z > 0 for v in f.verts) or all(v.co.z < 0 for v in f.verts)]
    bmesh.ops.triangulate(bm, faces=caps, quad_method="BEAUTY", ngon_method="BEAUTY")
    verts = [v for v in bm.verts if v not in old_v]
    top = {v: v.co.z > 0 for v in verts}
    for v in verts:
        c, r = fr.CR(v.co)
        v.co.z = (top_fn(c, r) if top[v] else bot_fn(c, r)) / 12
    if lens:
        pairs = {}
        for v in verts:
            if top[v]:
                for e in v.link_edges:
                    b = e.other_vert(v)
                    if not top.get(b, True) and abs(b.co.x - v.co.x) < 1e-7 and abs(b.co.y - v.co.y) < 1e-7:
                        pairs[b] = v
        for b, v in pairs.items():
            v.co.z = 0.5 * (v.co.z + b.co.z)
        bmesh.ops.weld_verts(bm, targetmap=pairs)
        verts = [v for v in verts if v.is_valid]
    # Relax the heights (z only) of the top's inner vertices: the grid's sliver triangles at the
    # rim and the recess walls otherwise shade as streaks and teeth. The rim ring stays put.
    rim = {v for v in verts if top[v] and any(not top[e.other_vert(v)] for e in v.link_edges)}
    if lens:
        rim = set(pairs.values())
    inner = [v for v in verts if top[v] and v not in rim]
    for _ in range(smooth_z):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=False, use_axis_y=False, use_axis_z=True)
    if relax:
        # Top and bottom alike: the bottom's roll-off is what a low camera sees under the front rim.
        brim = rim if lens else {v for v in verts if not top[v] and any(top[e.other_vert(v)] for e in v.link_edges)}
        binner = [v for v in verts if not top[v] and v not in brim]
        for _ in range(smooth_z):
            bmesh.ops.smooth_vert(bm, verts=binner, factor=0.5, use_axis_x=False, use_axis_y=False, use_axis_z=True)
        for side, edge in ((True, rim), (False, brim)):
            ring, near = set(edge), set()
            for _ in range(band):
                ring = {e.other_vert(v) for v in ring for e in v.link_edges
                        if top.get(e.other_vert(v)) == side and e.other_vert(v) not in edge} - near
                near |= ring
            near = list(near)
            for _ in range(relax):
                bmesh.ops.smooth_vert(bm, verts=near, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    for f in [f for f in bm.faces if f not in old_f]:
        cen = f.calc_center_median()
        c, r = fr.CR(cen)
        f.material_index = mat_fn(c, r, all(top[v] for v in f.verts))
        f.smooth = True


class Plan:
    """A plan region from a pixel mask: its smoothed contour loop (D170's contour_loops: the
    staircase faired into one curve) and the distance to it. `roff` rows of padding sit above row 0
    (an open seam there: the outline does not round off along it)."""

    def __init__(self, mask, roff=0, sigma=0.5):
        self.roff = roff
        self.field = smooth_field(mask, sigma)
        # The chamfer distance is quantised on the 1/3 px lattice; blurred (1/2 px) it rolls the rim
        # off evenly instead of in ridges along the flank.
        dist = _chamfer(self.field >= 0.5)
        k = np.arange(-4, 5)
        g = np.exp(-0.5 * (k / 1.5) ** 2)
        g /= g.sum()
        dist = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 0, dist)
        dist = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 1, dist)
        self.dist = np.maximum(0.0, dist - 0.12)
        loops = contour_loops(self.field, 0.05)
        loop = max(loops, key=lambda lp: abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(lp, lp[1:] + lp[:1]))))
        self.loop = [(c, r - roff) for c, r in loop]

    def d(self, c, r):
        rr = r + self.roff
        return field_at(self.dist, c, rr) if field_at(self.field, c, rr) >= 0.5 else 0.0


def mat_glow(index, strength):
    """A glow (D126: the palette colour x strength replaces the lit colour); metallic 1 / rough so no
    reflection washes it out (D173)."""
    key = (index, "glow", strength)
    if key not in MAT.slots:
        MAT.slots[key] = len(MAT.list)
        m = common.palette_material(MAT.sprite, index, f"n119b{len(MAT.list)}", metallic=1.0, roughness=0.9,
                                    emission_strength=strength)
        m.name = f"pal_{index}_n119b_{len(MAT.list)}"
        MAT.list.append(m)
    return MAT.slots[key]


# --------------------------------------------------------------------------------------------------
# Head: sprite, masks, regions
# --------------------------------------------------------------------------------------------------

HEAD = common.load_sprite(ROOT, NAME)
HCOL = {int(k): tuple(v) for k, v in HEAD["colors"].items()}
HPIX = {f["index"]: f["pixels"] for f in HEAD["frames"]}
HMASK = {}
for _k, _px in HPIX.items():
    _m = SM.masks(_px, HCOL)
    HMASK[_k] = np.array(_m["inner"], bool) | np.array(_m["free"], bool)

# Skull: frame 119's inner mask, rows 0-12 (the jaw is its own part), its top row a seam with the
# neck collar: filled across (cols 0-22) and padded upward, so it neither notches nor rounds off.
MOUTH_HW = pfn([8.4, 9.5, 10.5, 12.0, 14.0], [2.6, 3.8, 4.9, 5.0, 5.0])  # the mouth's half width by row
_sk = HMASK[119].copy()
_sk[13:] = False
for _r in range(9, 13):  # the mouth is a notch in the plan (its edge a clean lip); a palate plate fills it
    for _c in range(24):
        if abs(_c + 0.5 - AXE) <= MOUTH_HW(_r + 0.5):
            _sk[_r, _c] = False
_sk[0, 0:23] = True
ROFF = 3
SKULL = Plan(np.vstack([np.repeat(_sk[:1], ROFF, 0), _sk]), ROFF, 0.5)

# Jaw plan, in frame 119's jaw position: frame 129's inner rows 13-24 (the fully slid-out jaw:
# rami, trough, chin) moved up 2, run on straight back under the skull to row 5 (hidden in the
# head in every pose; the rami ride in the sleeves).
_jm = np.zeros((28, 24), bool)
_jm[11:23] = HMASK[129][13:25]
for _r in range(5, 11):
    _jm[_r] = _jm[11]
JAWP = Plan(_jm, 0, 0.5)


def eye_fit(left):
    """Centre (edge coords), unit major axis (pointing down the screen) and semi-axes of the red
    eye pixels on one side."""
    pts = np.array([(c + 0.5, r + 0.5) for r in range(23) for c in range(24)
                    if HPIX[119][r][c] >= 112 and ((c < 12) == left)], float)
    mu = pts.mean(0)
    w, v = np.linalg.eigh(np.cov((pts - mu).T))
    major = v[:, 1] if v[1, 1] >= 0 else -v[:, 1]
    return mu, major, 2.0 * math.sqrt(w[1]) + 0.55, 2.0 * math.sqrt(w[0]) + 0.5


EYES = [eye_fit(True), eye_fit(False)]
SOCK = 1.7  # the eye lens sits this deep (px) below the skull surface
CARVE = 1.3  # the socket dish's depth (px)


def eye_q(c, r, grow=(0.55, 0.45)):
    """Smallest normalised elliptic radius of (c, r) to either eye (1 at the socket's rim)."""
    best = 9.0
    for mu, major, a, b in EYES:
        u = (c - mu[0]) * major[0] + (r - mu[1]) * major[1]
        v = -(c - mu[0]) * major[1] + (r - mu[1]) * major[0]
        best = min(best, (u / (a + grow[0])) ** 2 + (v / (b + grow[1])) ** 2)
    return best


def blob(c, r, cx, cy, rx, ry):
    return math.exp(-(((c - cx) / rx) ** 2 + ((r - cy) / ry) ** 2))


# Dark recesses the sprite draws inside the skull (pixel centres): brow slots between the horn
# blade and the brow, nasal vents under-inboard of each eye. Each side from its own pixels.
SLOTS = [(2.5, 3.0, 0.75, 1.15), (19.8, 3.3, 1.35, 1.05)]
VENTS = [(7.0, 7.1, 1.55, 0.85), (16.0, 7.0, 1.05, 0.9)]
CROWN = pfn([0, 3, 6, 9, 12, 14], [11.0, 10.8, 10.1, 9.0, 7.8, 7.2])
FLOOR = 3.0  # palate floor px


def mid_z(r):
    return 6.2 - 0.9 * min(max(r, 0), 13) / 13


def bot_z(r):
    return 2.0 + 0.5 * min(max(r, 0), 13) / 13


def mirror_c(c):
    return c if c <= AXE else 2 * AXE - c


def skull_surface(c, r, rnd_on=True):
    """The skull's top without the recesses (px)."""
    d = SKULL.d(c, r)
    rnd = math.sqrt(min(1.0, (d + 0.04) / 2.6)) if rnd_on else 1.0
    dx = abs(c - AXE)
    z = CROWN(r) * (1 - 0.30 * (dx / 11.5) ** 2)
    mc = mirror_c(c)
    z += 0.9 * math.exp(-(seg_d((mc, r), (2.8, 8.8), (4.9, 12.0)) / 1.4) ** 2)  # cheek plates
    mid = mid_z(r)
    return mid + (z - mid) * rnd


def skull_top(c, r):
    d = SKULL.d(c, r)
    rnd = math.sqrt(min(1.0, (d + 0.04) / 2.6))
    z = skull_surface(c, r)
    rec = CARVE * smoothstep(1.5, 0.45, eye_q(c, r))  # a shallow, soft dish: its dark pad is a plate (clean edge)
    z -= rec * rnd
    return z


def skull_bot(c, r):
    d = SKULL.d(c, r)
    rnd = math.sqrt(min(1.0, (d + 0.04) / 2.6))
    mid = mid_z(r)
    return min(mid - (mid - bot_z(r)) * rnd, skull_top(c, r) - 0.6)


def head_mats():
    return {
        "body": MAT(54, 0.1, 0.45),     # cranium, cheeks (region median 54)
        "crest": MAT(58, 0.1, 0.4),     # crest, forks, upper fangs (58)
        "horn": MAT(52, 0.1, 0.45),     # horn blades (52)
        "slot": MAT(49, 0.0, 0.85),     # brow slots (49)
        "socket": MAT(48, 0.0, 0.8),    # eye sockets, nasal vents (48)
        "palate": MAT(49, 0.0, 0.9),    # mouth floor (49)
        "sleeve": MAT(50, 0.1, 0.5),    # hinge sleeves (50)
        "rami": MAT(50, 0.1, 0.48),     # jaw rami (50)
        "trough": MAT(48, 0.0, 0.92),   # jaw trough (48)
        "chin": MAT(51, 0.1, 0.45),     # chin (51)
        "teeth": MAT(53, 0.1, 0.38),    # lower teeth (53)
        "eye": mat_glow(114, 1.0),      # eye lens (region median 114)
        "eyecore": mat_glow(118, 1.0),  # its hot slit (the sprite's 117-119 centre)
    }


KEEL = [(1, 0), (0.82, 0.45), (0.42, 0.86), (0, 1.0), (-0.42, 0.86), (-0.82, 0.45), (-1, 0), (-0.55, -0.6),
        (0.55, -0.6)]
ROUND10 = [(math.cos(2 * math.pi * (k + 0.5) / 10), math.sin(2 * math.pi * (k + 0.5) / 10)) for k in range(10)]
ROUND16 = [(math.cos(2 * math.pi * (k + 0.5) / 16), math.sin(2 * math.pi * (k + 0.5) / 16)) for k in range(16)]


def build_skull(bm, M):
    def mat(c, r, top):
        if not top:
            return M["body"]
        return M["body"]
    relief_f(bm, FH, SKULL.loop, skull_top, skull_bot, 0.3, mat, smooth_z=4, relax=6, band=4, lens=True)
    # The skull's built top (after the relax passes, which lift the dish floors a little), for the
    # pads to lie on: a ray straight down onto the mesh, skull_top where it misses.
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromBMesh(bm)

    def built_top(c, r):
        hit = tree.ray_cast(Vector((FH.X(c), FH.Y(r), 2.0)), Vector((0, 0, -1)), 4.0)[0]
        return hit.z * 12 if hit is not None else skull_top(c, r)

    # Palate: the mouth's dark floor, a plate under the notch (a hair wider, so no gap shows).
    pr = [8.65 + 0.2 * k for k in range(0, 25)]
    pal = [(AXE - MOUTH_HW(r) - 0.12, r) for r in pr] + [(AXE + MOUTH_HW(r) + 0.12, r) for r in pr[::-1]]
    # Its bottom sits just under the floor, at the skull's own underside (bot_z), never below it: a
    # deeper plate hangs out under the hinge and chin as a black slab.
    def pal_top(c, r):
        return FLOOR - 0.4 * smoothstep(11.0, 13.5, r)
    relief_f(bm, FH, pal, pal_top, lambda c, r: min(pal_top(c, r) - 0.25, bot_z(r) + 0.15), 0.5,
             lambda c, r, top: M["palate"], smooth_z=0)

    # Crest down the middle (rows 0-6, 5 px wide), forking at row ~5.5 over the snout into two
    # prongs (cols 9 / 13) that drop as upper fangs into the mouth.
    path = []
    for r in np.arange(-0.8, 6.01, 0.6):
        hw = pfn([0, 4, 6], [2.35, 1.95, 1.45])(r)
        path.append((AXE, r, skull_surface(AXE, r, False) - 0.15, hw, 1.25))
    path.append((AXE, 6.6, skull_surface(AXE, 6.6, False) - 0.3, 0.0, 0.0))
    sweep_f(bm, FH, path, KEEL, M["crest"])
    for s in (-1, 1):
        pts = [(0.5, 5.0), (1.2, 6.3), (1.85, 7.5), (2.0, 8.5)]
        fp = [(AXE + s * u, r, skull_surface(AXE + s * u, r, False) + 0.05, w, 0.8 * w)
              for (u, r), w in zip(pts, (0.9, 0.95, 0.95, 0.9))]
        fang = [(AXE + s * 2.0, 9.4, 7.7, 0.72, 0.62), (AXE + s * 1.97, 10.4, 6.5, 0.6, 0.52),
                (AXE + s * 1.93, 11.4, 5.2, 0.45, 0.42), (AXE + s * 1.9, 12.1, 4.2, 0.28, 0.27),
                (AXE + s * 1.88, 12.7, 3.4, 0.0, 0.0)]
        sweep_f(bm, FH, fp + fang, KEEL, M["crest"])

    # Horn blades along the outer edges, rising back to the collar (cols 0-1 / 21-22, rows 0-6).
    for cs in ((1.75, 1.9, 2.2, 2.5), (21.75, 21.6, 21.3, 21.0)):
        hp = []
        for c, r, lift, w in zip(cs, (-0.8, 1.5, 3.8, 6.4), (0.95, 0.75, 0.4, 0.0), (0.9, 0.85, 0.65, 0.0)):
            z = skull_surface(c, r) + lift - 0.25
            hp.append((c, r, z, w, max(0.0, 0.75 * w)))
        sweep_f(bm, FH, hp, KEEL, M["horn"])

    # Brow ridges over the eyes, rising inward to the crest (the sprite's lit diagonal).
    for pts in (((9.6, 4.4), (7.6, 2.8), (5.3, 1.5), (3.9, 1.1)), ((13.4, 4.4), (15.4, 2.8), (17.6, 1.5), (19.0, 1.1))):
        bp = [(pts[0][0], pts[0][1], skull_surface(*pts[0]) - 0.1, 0.0, 0.0)]
        for (c, r), w in zip(pts[1:], (0.8, 0.72, 0.55)):
            bp.append((c, r, skull_surface(c, r) - 0.05, w, 0.55))
        bp.append((pts[-1][0] - 0.6 * (1 if pts[0][0] < AXE else -1), pts[-1][1] - 0.1,
                   skull_surface(*pts[-1]) - 0.3, 0.0, 0.0))
        sweep_f(bm, FH, bp, KEEL, M["body"])

    # Cheek struts (row 8's lit bar) from the outer edge to the vents.
    for pts in (((1.6, 8.7), (2.6, 8.6), (5.0, 8.5), (7.4, 8.4), (8.2, 8.4)),
                ((21.4, 8.7), (20.4, 8.6), (18.0, 8.5), (15.6, 8.4), (14.8, 8.4))):
        sp = []
        for i, (c, r) in enumerate(pts):
            w = 0.0 if i in (0, len(pts) - 1) else 0.5
            sp.append((c, r, skull_surface(c, r) - 0.05, w, 0.45 if w else 0.0))
        sweep_f(bm, FH, sp, KEEL, M["body"])

    # Dark pads (clean elliptic edges, D170-style plates): eye sockets in their dishes, brow slots and
    # nasal vents flush on the cranium.
    # Each pad follows the skull's top vertex by vertex (pad_f): the sockets lie in their dishes,
    # the slots and vents on the dome, with no edge standing proud on the slope.
    for mu, major, a, b in EYES:
        ang = math.atan2(-major[1], major[0])
        pad_f(bm, FH, mu[0], mu[1], a + 0.55, b + 0.45, built_top, M["socket"], angle=ang, lift=0.12, sink=-0.02,
              seg=32, rings=14)
    for (cx, cy, rx, ry), mat in [(s_, M["slot"]) for s_ in SLOTS] + [(v_, M["socket"]) for v_ in VENTS]:
        pad_f(bm, FH, cx, cy, rx * 0.8, ry * 0.8, built_top, mat, lift=0.12, sink=-0.02, seg=24, rings=12)

    # Eyes: emissive lenses set in the sockets, slanted as the sprite's red slits, a hot core slit.
    for mu, major, a, b in EYES:
        ang = math.atan2(-major[1], major[0])  # (c, r) -> (X, Y): r runs down -Y
        zs = skull_surface(mu[0], mu[1]) - 0.9
        # (The socket pad used to stand over the lens rim and hide it; now the pad lies in its dish the
        # lens is sized to the red the player saw: the sprite's ~3 x 3 px slit.)
        ellipsoid_f(bm, FH, mu[0], mu[1], zs, a * 0.76, b * 0.8, 0.75, M["eye"], angle=ang)
        ellipsoid_f(bm, FH, mu[0], mu[1], zs + 0.3, a * 0.5, b * 0.35, 0.62, M["eyecore"], angle=ang, seg=12,
                    rings=6)

    # Hinge sleeves at the cheek tips (row 13 '222'): the jaw rami slide in and out of them.
    for c in (6.4, 16.6):
        path = [(c, 11.4, 4.5, 0.0, 0.0), (c, 11.6, 4.5, 1.2, 1.0), (c, 12.1, 4.5, 1.5, 1.3),
                (c, 13.2, 4.5, 1.5, 1.3), (c, 13.55, 4.5, 1.25, 1.1), (c, 13.6, 4.5, 0.0, 0.0)]
        sweep_f(bm, FH, path, ROUND16, M["sleeve"])


PIVOT = (12.4, 4.5)  # jaw hinge: the sleeves' axis (row, z px)


def jaw_top(c, r):
    d = JAWP.d(c, r)
    rnd = math.sqrt(min(1.0, (d + 0.04) / 1.8))
    # Each ramus a rounded bar (crown 1.3 px in from the outline), its inner flank rolling down
    # into the trough; the outer flank rolls down to the knife-edge rim.
    dx = abs(c - AXE)
    inner = math.sqrt(max(0.0, min(1.0, (dx - 2.9) / 1.4)))
    base = 2.9 + (5.5 + 0.3 * smoothstep(14, 17, r) - 2.9) * inner
    q = 1 - ((c - AXE) / 5.4) ** 2 - ((r - 20.4) / 3.0) ** 2
    # The chin dome: an elliptic cap whose edge eases in (q^0.6, not a sqrt cliff), blended into the
    # rami with a soft max (no crease to crinkle on the grid).
    chin = (4.4 + 2.0 * max(0.0, q) ** 0.6) * smoothstep(17.2, 19.0, r)
    k = 0.8
    h = min(1.0, max(0.0, 0.5 + 0.5 * (chin - base) / k))
    z = base + (chin - base) * h + k * h * (1 - h)
    mid = 3.6
    return mid + (z - mid) * rnd


def jaw_bot(c, r):
    d = JAWP.d(c, r)
    rnd = math.sqrt(min(1.0, (d + 0.04) / 1.8))
    mid = 3.6
    low = 1.5 if r > 13 else 2.4  # inside the skull at the back
    return min(mid - (mid - low) * rnd, jaw_top(c, r) - 0.6)


def build_jaw(bm, M):
    def mat(c, r, top):
        # Regions by plan position only (a height test zigzags along the grid on the flanks).
        if r > 18.3:
            return M["chin"]
        if not top or abs(c - AXE) > 3.3:
            return M["rami"]
        return M["trough"]
    relief_f(bm, FH, JAWP.loop, jaw_top, jaw_bot, 0.3, mat, smooth_z=4, relax=6, band=4, lens=True)
    # Three lower teeth rising from the trough (cols 9, 11, 13).
    for c, r, hgt in ((9.5, 17.0, 3.0), (11.5, 17.8, 3.3), (13.5, 17.0, 3.0)):
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.62 / 12, radius2=0.0, depth=hgt / 12)
        rot = Matrix.Rotation(math.radians(-14), 4, "X")  # tips lean back into the mouth
        for v in res["verts"]:
            v.co = rot @ v.co
            v.co += Vector((FH.X(c), FH.Y(r), (2.6 + hgt / 2) / 12))
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = M["teeth"]
            f.smooth = True


def clip_bm(bm, planes):
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            for f in res["faces"]:
                f.smooth = False


def finish(name, bm, coll):
    """bmesh -> object with only the materials it uses (pal_ names kept). The underside's
    near-flat faces are merged (a plain closed shape: no triangles spent there)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    under = [f for f in bm.faces if f.normal.z < -0.97]
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(4), verts=list({v for f in under for v in f.verts}),
                             edges=list({e for f in under for e in f.edges}), delimit={"MATERIAL"})
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                          ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    used = sorted({f.material_index for f in bm.faces})
    remap = {old: i for i, old in enumerate(used)}
    for f in bm.faces:
        f.material_index = remap[f.material_index]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for old in used:
        me.materials.append(MAT.list[old])
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build_head(coll, name, dy, deg):
    M = head_mats()
    bm = bmesh.new()
    build_skull(bm, M)
    clip_bm(bm, [((0, FH.Y(0.0), 0), (0, 1, 0))])  # the seam with the neck collar
    before = set(bm.verts)
    build_jaw(bm, M)
    jaw = [v for v in bm.verts if v not in before]
    rot = Matrix.Rotation(math.radians(deg), 4, "X")
    piv = Vector((0, FH.Y(PIVOT[0]), PIVOT[1] / 12))
    for v in jaw:
        v.co = piv + rot @ (v.co - piv)
        v.co.y -= dy / 12
    return finish(name, bm, coll)


# --------------------------------------------------------------------------------------------------
# Wing tip pieces from D170's left wing
# --------------------------------------------------------------------------------------------------

def build_left_wing(coll):
    bm = bmesh.new()
    build_wing(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("wingL")
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new("wingL", me)
    coll.objects.link(obj)
    return obj


def cut_piece(src, name, box_left, mirror, origin, coll, sink=0.0):
    """Cut the left wing to box_left (c0, r0, c1, r1, assembly px), mirror it about edge 93.5 for
    the right tip, and move it to the piece's own origin (its box centre, assembly px)."""
    c0, r0, c1, r1 = box_left
    bm = bmesh.new()
    bm.from_mesh(src.data)
    clip_bm(bm, [((X(c0), 0, 0), (-1, 0, 0)), ((X(c1), 0, 0), (1, 0, 0)),
                 ((0, Y(r0), 0), (0, 1, 0)), ((0, Y(r1), 0), (0, -1, 0))])
    if mirror:
        for v in bm.verts:
            v.co.x = -v.co.x - (2 * AXIS - 2 * TIP_MIRROR) / 12
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    ox, oy = X(origin[0] + 12), Y(origin[1] + 14)
    for v in bm.verts:
        v.co.x -= ox
        v.co.y -= oy
        v.co.z -= sink / 12
    used = sorted({f.material_index for f in bm.faces})
    remap = {old: i for i, old in enumerate(used)}
    for f in bm.faces:
        f.material_index = remap[f.material_index]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for old in used:
        me.materials.append(src.data.materials[old])
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def cull_hidden(obj, ndirs=32):
    """Delete faces no ray from outside can reach (D170's cull_hidden)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        rr = math.sqrt(1 - z * z)
        dirs.append(Vector((rr * math.cos(golden * i), rr * math.sin(golden * i), z)))
    dead = []
    for f in bm.faces:
        n = f.normal
        if n.z > 0.2:
            continue
        c = f.calc_center_median()
        pts = [c] + [c.lerp(v.co, 0.85) for v in f.verts]
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * 1e-3
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


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def shell_for(obj, coll, voxel, faces):
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    sealed.location = (0, 0, 0)
    bpy.context.view_layer.update()
    try:
        sh = common.outline_shell(sealed, coll, voxel=voxel, faces=faces, inside=0.004)
    except Exception as err:  # a fragment too small to remesh
        print("no shell for", obj.name, err)
        sh = None
    bpy.data.objects.remove(sealed, do_unlink=True)
    if sh is not None:
        sh.name = sh.data.name = f"{obj.name}_outline"
        if not len(sh.data.polygons):
            bpy.data.objects.remove(sh, do_unlink=True)
            sh = None
    return sh


def build_all(coll):
    models, shells = {}, {}
    for name, frame, dy, deg in HEAD_MODELS:
        models[name] = build_head(coll, name, dy, deg)
    wing = build_left_wing(coll)
    models["newsh0-1"] = cut_piece(wing, "newsh0-1", (0, 0, 24, 28), False, BOX["newsh0-1"], coll)
    models["newsh0-3"] = cut_piece(wing, "newsh0-3", (24, 0, 48, 28), False, BOX["newsh0-3"], coll)
    models["newsh0-15"] = cut_piece(wing, "newsh0-15", (1, 0, 25, 28), True, BOX["newsh0-15"], coll)
    models["newsh0-53"] = cut_piece(wing, "newsh0-53", (1, 28, 25, 56), True, BOX["newsh0-53"], coll)
    # newsh0-13: its one dark pixel (167, 27) lies on newsh0-15's lobe (mirror pixel 19, 27): that bit
    # of wing, sunk 0.15 px so it never fights newsh0-15's surface.
    models["newsh0-13"] = cut_piece(wing, "newsh0-13", (18.9, 26.9, 20.1, 28.0), True, BOX["newsh0-13"], coll,
                                    sink=0.15)
    bpy.data.objects.remove(wing, do_unlink=True)
    for name, obj in models.items():
        head = name.startswith(NAME)
        shells[name] = shell_for(obj, coll, 0.02 if head else 0.03, 1600 if head else 900)
        n = cull_hidden(obj)
        obj.data.set_sharp_from_angle(angle=math.radians(88 if head else 40))
        if head:
            # Face-area weighted normals: the relief grid's sliver cells along the rolled walls and the
            # chin no longer bend the shading into streaks.
            wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
            wn.mode = "FACE_AREA"
            wn.keep_sharp = True
            wn.weight = 50
            common._apply_modifiers(obj)
        print(f"{name}: culled {n}, {tris(obj)} tris")
    return models, shells


# --------------------------------------------------------------------------------------------------
# Review renders (scratch only)
# --------------------------------------------------------------------------------------------------

def assembly_pos(name):
    """Blender (X, Y) of a model's origin in the D170 assembly frame."""
    if name.startswith(NAME):
        x0, y0 = HEAD_AT
    else:
        x0, y0 = BOX[name]
    return X(x0 + 12), Y(y0 + 14)


def review(models, shells, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    eevee = None
    for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = e
            eevee = e
            break
        except TypeError:
            pass
    try:
        scene.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.3
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.world.use_nodes = True
    bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.05, 0.055, 0.065, 1)
    bgn.inputs[1].default_value = 0.8
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 4.0
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(15))
    extra = []

    def cam(loc, look, ortho=None, lens=50, rx=600, ry=600, up_y=True):
        d = bpy.data.cameras.new("c")
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new("c", d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        return o

    def show(objs):
        for o in scene.objects:
            if o.type == "MESH":
                o.hide_render = o not in objs

    def shot(path, flat=False):
        if flat:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh = scene.display.shading
            sh.light = "FLAT"
            sh.color_type = "SINGLE"
            sh.single_color = (1, 1, 1)
            sh.show_cavity = False
            sh.show_specular_highlight = False
            sh.show_object_outline = False
            scene.render.film_transparent = True
        else:
            scene.render.engine = eevee
            scene.render.film_transparent = False
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    def top_cam(k, w=24, h=28, at=(0, 0)):
        c = cam((at[0], at[1], 30), (at[0], at[1], 0), ortho=max(w, h) / 12, rx=w * k, ry=h * k)
        c.rotation_euler = (0, 0, 0)

    t = math.radians(32)
    for name, obj in models.items():
        show([obj])
        top_cam(8)
        shot(out / f"mask_{name}.png", flat=True)
        top_cam(12)
        shot(out / f"top_{name}.png")
        if name.startswith(NAME):
            d = 5.2
            ctr = Vector((0, -0.15, 0.4))
            cam(ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=55, rx=560, ry=500)
            shot(out / f"game_{name}.png")
            show([obj, shells[name]] if shells.get(name) else [obj])
            shot(out / f"gameink_{name}.png")
            show([obj])
    head = models[NAME]
    show([head])
    ctr = Vector((0, -0.2, 0.45))
    for nm, loc, ortho in (("side", (-30, -0.2, 0.45), 2.6), ("front", (0, -30, 0.45), 2.4),
                           ("rear", (0, 30, 0.45), 2.4)):
        cam(loc, (loc[0] * 0 if nm != "side" else 0, -0.2 if nm == "side" else 0, 0.45), ortho=ortho, rx=600, ry=330)
        shot(out / f"{nm}_{NAME}.png")
    for nm, az, el, mdl in (("q_high", 35, 35, NAME), ("q_rear", 220, 32, NAME), ("q_low", 20, 14, f"{NAME}-f4"),
                            ("q_high4", -35, 35, f"{NAME}-f4")):
        show([models[mdl]])
        a, e = math.radians(az), math.radians(el)
        d = 5.5
        cam(ctr + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), ctr,
            lens=50, rx=600, ry=480)
        shot(out / f"{nm}.png")
    show([head])
    cam((0, -30, 0.5), (0, 0, 0.5), ortho=1.3, rx=900, ry=600)
    shot(out / "front_close.png")
    c = cam((0, 0, -30), (0, 0, 0), ortho=2.6, rx=420, ry=420)
    shot(out / "under.png")

    # Wing tips in place: 3/4 views of each tip.
    placed = {}
    for name, obj in models.items():
        placed[name] = obj.location.copy()
        obj.location = (*assembly_pos(name), 0)
    bpy.context.view_layer.update()
    for nm, objs, ctr_c in (("tipL", ["newsh0-1", "newsh0-3"], (16, 22)),
                            ("tipR", ["newsh0-15", "newsh0-53", "newsh0-13"], (174, 30))):
        show([models[n] for n in objs])
        ctr = Vector((X(ctr_c[0]), Y(ctr_c[1]), 1.1))
        for v, az, el in (("hi", 30 if nm == "tipL" else -30, 35), ("game", 0, 58)):
            a, e = math.radians(az), math.radians(el)
            d = 9
            cam(ctr + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), ctr,
                lens=50, rx=600, ry=520)
            shot(out / f"{nm}_{v}.png")

    # Context: the D170 wings, the neck, the back spikes from public/models, with these models.
    before = set(bpy.data.objects)
    lay = common.load_sprite(ROOT, "newsh0-39")["assemblyLayout"]
    imported = []
    want = [(e["model"], e["cx"] - 12 - 30, e["cy"] - 14 + 32) for e in lay
            if e["model"] not in ("newsh0-1", "newsh0-3", "newsh0-13")]
    want += [("newsh0-91", NECK_AT[0], NECK_AT[1]), ("newsh0-93", NECK_AT[0] + 24, NECK_AT[1])]
    for m, x0, y0 in want:
        p = ROOT / "public" / "models" / "enemies" / f"{m}.glb"
        if not p.exists():
            print("context: missing", p)
            continue
        old = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(p))
        for o in set(bpy.data.objects) - old:
            if o.parent is None:
                o.location = (X(x0 + 12) + o.location.x, Y(y0 + 14) + o.location.y, o.location.z)
            if o.type == "MESH" and "outline" not in o.name and not any(
                    s.material and s.material.name.startswith("outline_shell") for s in o.material_slots):
                imported.append(o)
    bpy.context.view_layer.update()
    mine = [models[n] for n in models if n in (NAME, "newsh0-1", "newsh0-3", "newsh0-13", "newsh0-15", "newsh0-53")]
    show(imported + mine)
    ctr = Vector((X(96), Y(62), 1.0))
    d = 26
    cam(ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=55, rx=1100, ry=760)
    shot(out / "context_game.png")
    c = cam((ctr.x, ctr.y, 40), (ctr.x, ctr.y, 0), ortho=17.5, rx=1100, ry=760)
    c.rotation_euler = (0, 0, 0)
    shot(out / "context_top.png")
    # Head close-up in context (neck seam), game camera.
    hx, hy = assembly_pos(NAME)
    ctr = Vector((hx, hy + 0.6, 0.6))
    d = 8
    cam(ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=55, rx=700, ry=560)
    shot(out / "context_head.png")
    a = math.radians(35)
    cam(ctr + Vector((d * 0.6 * math.sin(a), -d * 0.6 * math.cos(a), d * 0.55)), ctr, lens=50, rx=700, ry=560)
    shot(out / "context_head_q.png")
    for o in set(bpy.data.objects) - before:
        bpy.data.objects.remove(o, do_unlink=True)
    for name, obj in models.items():
        obj.location = placed[name]


def export_all(models, shells):
    """Every model at its own origin with its outline shell (D51), to public/models/enemies/<name>.glb,
    and its spriteModels entry (the frames it replaces)."""
    sprites = {n: common.load_sprite(ROOT, n)["sprites"] for n in ("newsh0-119", "newsh0-1", "newsh0-3",
                                                                   "newsh0-13", "newsh0-15", "newsh0-53")}
    frame_of = {n: f for n, f, _, _ in HEAD_MODELS}
    for name, obj in models.items():
        if name in frame_of:
            sp = [dict(s, frames=[frame_of[name]]) for s in sprites[NAME] if frame_of[name] in s["frames"]]
        else:
            sp = sprites[name]
        objs = [obj] + ([shells[name]] if shells.get(name) is not None else [])
        for o in objs:
            o.hide_render = False
        common.export_sprite_model(ROOT, objs, f"enemies/{name}", sp)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    models, shells = build_all(coll)
    info = {n: {"tris": tris(o), "materials": [m.name for m in o.data.materials]} for n, o in models.items()}
    print(json.dumps(info, indent=1))
    for o in shells.values():
        if o is not None:
            o.hide_render = True
    if "--no-export" not in argv:
        export_all(models, shells)
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        objs = list(models.values()) + [s for s in shells.values() if s is not None]
        for o in objs:
            o.hide_render = False
        common.export_glb(objs, out)
        for o in shells.values():
            if o is not None:
                o.hide_render = True
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        (rv / "info.json").write_text(json.dumps(info, indent=1))
        review(models, shells, rv)


if __name__ == "__main__":
    main()
