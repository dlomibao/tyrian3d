"""GYGES's left arm claw (newshn.shp, assembly of newshn-163 over newshn-201): 3D versions of its
sprites. assembly-newshn-39.py builds the right claw (its mirror) with this script's builder.

WHAT IT IS: the claw at the tip of one of GYGES's (level 2.2) two swinging tentacle arms (the chain
of blue spiral shells newshn-125 / -15 / -13 hangs above it). It hangs and swings in the air while
the scroll is stopped for the boss: the 'ground' layer is only the draw layer, so it is built
free-floating, with a round closed underside (not lying on the ground, not a horned eye creature).

A grey-blue hooked pincer, 18 x 34 px over two rows of pieces (newshn-201 under newshn-163 holds only
the claw tips):
  - HAND (rows 0-15): a chitin-plate carapace tapering up to the horn-shaped wrist tip where the
    tentacle joins, its crest down the middle (the light pixels down its left are its lit flank).
  - FIXED FINGER (rows 16-33): the long curved blade tapering to a point, its top a raised rim lip
    over the hand's lower edge (the sprite's light band across row 16: a real overlap step).
  - SOCKET: the dark blue (52/53) hinge cup cut into the hand's lower right where the knuckle seats.
  - KNUCKLE: the round grey knob carrying the cyan lens (136, glowing, in a pale 60 bezel); in the
    open pose a link bar ties it to the hand's upper right.
  - MOVABLE FINGER (dactyl): a hooked blade hanging from the knuckle on a pin (the sprite's
    '2 101 2' neck), its tip curling back in.
The claw opens over three frames (ani 1 20): A closed (163 over 201), B half open (203 / 205),
C open (207 / 245). Each pose is built whole from its own sprite pixels (every part's outline row
by row from the sprite's inner mask, D74), cut into its two pieces with common.split_assembly and
exported with its own frame: newshn-163 / -f2 / -f3 and newshn-201 / -f2 / -f3. The outline shell
(D51) is made from the whole pose and cut open at the piece seam, so the seam draws no ink line.

    blender --background --factory-startup --python assets/blender/enemies/assembly-newshn-201.py \
        [-- --measure out_dir]
--measure renders each whole pose's top view on the sprite grid and prints its rule IoU
(tools/sprite_mask.py) per pose.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as SM  # noqa: E402

PX = 1 / 12
NAME = "assembly-newshn-201"
# (piece, its top row in the assembly, {pose: (model, frame)}); newshn-201 sits 28 px below.
PIECES = [
    ("newshn-163", 0, {"A": ("newshn-163", 163), "B": ("newshn-163-f2", 203), "C": ("newshn-163-f3", 207)}),
    ("newshn-201", 28, {"A": ("newshn-201", 201), "B": ("newshn-201-f2", 205), "C": ("newshn-201-f3", 245)}),
]

# Per pose (left claw's sprite columns): K = first column of the knuckle / dactyl where they touch
# the hand; knob rows; the neck (pin) row; the dactyl's rows; the lens (column, row of its centre:
# the 60 pixel over the 136 one); the link bar (rows, first column) where it shows.
POSES = {
    "A": dict(K=12, knob=(11, 16), neck=17, dact=(18, 31), lens=(13.5, 14.0), link=None),
    "B": dict(K=13, knob=(8, 13), neck=14, dact=(15, 28), lens=(15.5, 11.0), link=None),
    "C": dict(K=14, knob=(6, 11), neck=12, dact=(13, 26), lens=(17.5, 9.0), link=((7, 9), 13)),
}
# Palette indices: each part's sprite median (ink, darkest and brightest sixths left out): hand,
# finger and knuckle 102, dactyl 103; the socket 53; the lens 136 in a 60 bezel; pin and link 101.
IDX = dict(hand=102, finger=102, knob=102, dact=103, pin=101, socket=53, lens=136, bezel=60)
SATIN = dict(metallic=0.35, roughness=0.42)
SOCKET_AT = (11.1, 14.7, 1.35, 1.6)  # centre u, v; radii u, v (px): the blue hinge cup
PARTS = ("hand", "finger", "knob", "dact", "pin", "socket", "lens", "bezel")


# --------------------------------------------------------------------------- the sprite's parts

def pose_pixels(sprites, pieces, pose, mirror):
    """The whole pose's palette rows (rows 0-55) in the LEFT claw's columns, and its colours."""
    idx, colors = [], {}
    for piece, _, models in pieces:
        data = sprites[piece]
        fr = next(f for f in data["frames"] if f["index"] == models[pose][1])
        idx += [list(r) for r in fr["pixels"]]
        colors.update({int(k): tuple(v) for k, v in data["colors"].items()})
    if mirror:  # the right claw's column 22 - c is the left claw's column c (exactly, all poses)
        idx = [[row[22 - c] if 0 <= 22 - c < 24 else -1 for c in range(24)] for row in idx]
    return idx, colors


def label(idx, colors, p):
    """{(row, col): part} for every inner-mask pixel (D74): hand, finger, knob, link, neck, dact."""
    m = SM.masks(idx, colors)
    lab = {}
    for r, row in enumerate(idx):
        runs, c = [], 0
        while c < 24:
            if row[c] >= 0:
                s = c
                while c < 24 and row[c] >= 0:
                    c += 1
                runs.append((s, c - 1))
            else:
                c += 1
        for c in range(24):
            if not m["inner"][r][c] or m["free"][r][c]:
                continue
            lk = p["link"]
            if lk and lk[0][0] <= r <= lk[0][1] and lk[1] <= c < lk[1] + 2:
                lab[r, c] = "link"
                continue
            mov = p["knob"][0] <= r <= p["dact"][1] and (c >= p["K"] or (len(runs) > 1 and c >= runs[1][0]))
            if mov and len(runs) > 1 and c <= runs[0][1] and r > p["neck"]:
                mov = False
            if not mov:
                part = "hand" if r <= 15 else "finger"
            elif r < p["neck"]:
                part = "knob" if r >= p["knob"][0] else "hand"
            elif r == p["neck"]:
                part = "neck"
            else:
                part = "dact"
            lab[r, c] = part
    return lab, m


def edges(lab, part):
    """{row: (left, right)} pixel-edge extents of a part per row."""
    out = {}
    for (r, c), p in lab.items():
        if p == part:
            lo, hi = out.get(r, (99, -99))
            out[r] = (min(lo, c), max(hi, c + 1))
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------- geometry helpers

def pchip(xs, ys):
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

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        lo = max(i for i in range(n - 1) if xs[i] <= x)
        t = (x - xs[lo]) / h[lo]
        return ((2 * t ** 3 - 3 * t * t + 1) * ys[lo] + (t ** 3 - 2 * t * t + t) * h[lo] * m[lo]
                + (-2 * t ** 3 + 3 * t * t) * ys[lo + 1] + (t ** 3 - t * t) * h[lo] * m[lo + 1])
    return f


def B(u, v, z):
    """Sprite point (column u, row v, both continuous; z px up) to Blender (top piece's centre = 0)."""
    return Vector(((u - 12) * PX, (14 - v) * PX, z * PX))


def smooth_rows(rows, passes=1):
    """The per-row pixel edges relaxed (1-2-1) so the loft's sides don't ripple at every pixel step
    (a 1 px staircase lofted as is reads as rings round the part)."""
    rs = list(rows)
    for _ in range(passes):
        new = {}
        for i, r in enumerate(rs):
            if 0 < i < len(rs) - 1 and rs[i - 1] == r - 1 and rs[i + 1] == r + 1:
                new[r] = tuple(0.25 * rows[r - 1][k] + 0.5 * rows[r][k] + 0.25 * rows[r + 1][k] for k in (0, 1))
            else:
                new[r] = rows[r]
        rows = new
    return rows


def interp_edges(rows):
    """L(v), R(v): pchip through each row's centre."""
    rs = list(rows)
    if len(rs) >= 3:
        fl = pchip([r + 0.5 for r in rs], [rows[r][0] for r in rs])
        fr = pchip([r + 0.5 for r in rs], [rows[r][1] for r in rs])
        return fl, fr
    vs = [r + 0.5 for r in rs]

    def at(v, k):
        if v <= vs[0]:
            return rows[rs[0]][k]
        if v >= vs[-1]:
            return rows[rs[-1]][k]
        i = max(i for i in range(len(vs)) if vs[i] <= v)
        t = (v - vs[i]) / (vs[i + 1] - vs[i])
        return rows[rs[i]][k] * (1 - t) + rows[rs[i + 1]][k] * t
    return (lambda v: at(v, 0)), (lambda v: at(v, 1))


KT, KB = 14, 8  # top / bottom segments of a loft section
SH, WALL = 0.32, 0.62  # chamfer: the shoulder line (share of the half width) and its height (share)


def section(L, R, a, ht, hb, n=2.4, z0=0.0):
    """Closed ring of (u, z): the top from the left edge over the crest (a of the width from the
    left) to the right edge, a squarish-round (superellipse n) chamfered section; then the round
    underside back."""
    w = max(R - L, 1e-4)
    xc = L + a * w
    pts = []
    for j in range(KT + 1):
        s = (1 - math.cos(math.pi * j / KT)) / 2
        x = L + s * w
        q = (x - L) / max(xc - L, 1e-6) if x <= xc else (R - x) / max(R - xc, 1e-6)
        q = min(1.0, max(0.0, q))
        # chamfered: a rounded side wall up to the shoulder line (q = SH), then a flatter facet
        # climbing to the keel
        if q <= SH:
            z = WALL * (1 - (1 - q / SH) ** n) ** (1 / n)
        else:
            t = (q - SH) / (1 - SH)
            z = WALL + (1 - WALL) * (1 - (1 - t) ** 1.35)
        pts.append((x, z0 + ht * z))
    mid, hw = (L + R) / 2, w / 2
    for j in range(1, KB):
        qq = math.cos(math.pi * j / KB)
        pts.append((mid + qq * hw, z0 - hb * math.sqrt(max(0.0, 1 - qq * qq))))
    return pts


def loft(bm, stations, mat, mat_of=None):
    """stations: [(v, ring)] with rings of equal length, or ('point', v, u, z) at either end."""
    rings = []
    for st in stations:
        if st[0] == "point":
            _, v, u, z = st
            rings.append([bm.verts.new(B(u, v, z))])
        else:
            v, ring = st
            rings.append([bm.verts.new(B(u, v, z)) for u, z in ring])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                fv = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                fv = (r0[k], r1[0], r0[j])
            else:
                fv = (r0[k], r1[k], r1[j], r0[j])
            faces.append(bm.faces.new(fv))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        if len(ring) > 2:
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            n = len(ring)
            for k in range(n):
                j = (k + 1) % n
                faces.append(bm.faces.new((ring[j], ring[k], c) if rev else (ring[k], ring[j], c)))
    for f in faces:
        f.material_index = mat_of(f) if mat_of else mat
        f.smooth = True
    return faces


def part_loft(bm, rows, H, mat, a=0.45, hb_k=0.55, hb_0=0.35, ends=("point", "point"), ext=(0.55, 0.55),
              step=0.5, dent=None, mat_of=None, n=2.4, z0=0.0, end_u=(None, None), smooth=1):
    """A part lofted down the rows from its per-row extents. H(v) = crest height. Ends: 'point' (a tip:
    width and height close to a point `ext` px past the last row centre) or 'blunt' (the height rounds
    off, the width barely narrows: a rim/riser closed by a flat cap)."""
    rows = smooth_rows(rows, smooth)
    L, R = interp_edges(rows)
    v0, v1 = min(rows) + 0.5, max(rows) + 0.5
    vs = []
    v = v0
    while v < v1 - 1e-6:
        vs.append(v)
        v += step
    vs.append(v1)

    def ring_at(vv, vh, ts=1.0, tw=1.0):
        l, r = L(vv), R(vv)
        mid = (l + r) / 2
        l, r = mid + (l - mid) * tw, mid + (r - mid) * tw
        ht = H(vh) * ts
        hb = (hb_k * H(vh) + hb_0) * ts
        ring = section(l, r, a, ht, hb, n=n, z0=z0)
        if dent:
            ring = [(u, z - (dent(u, vh) if z > z0 else 0.0)) for u, z in ring]
        return ring

    def cap(end, vend, sign):
        e = ext[end]
        res = []
        for t in (0.35, 0.65, 0.85, 0.96):
            vv = vend + sign * t * e
            s = math.sqrt(max(0.0, 1 - t * t))
            if ends[end] == "point":
                res.append((vv, ring_at(vend, vv, ts=s ** 0.7, tw=s)))
            else:
                res.append((vv, ring_at(vend, vv, ts=0.35 + 0.65 * s, tw=1 - 0.12 * t * t)))
        if ends[end] == "point":
            l, r = L(vend), R(vend)
            u = end_u[end] if end_u[end] is not None else (l + r) / 2
            res.append(("point", vend + sign * e, u, z0 + 0.1 * H(vend)))
        return res

    stations = cap(0, v0, -1)[::-1] + [(v, ring_at(v, v)) for v in vs] + cap(1, v1, +1)
    return loft(bm, stations, mat, mat_of)


def ellipsoid(bm, cu, cv, cz, ru, rv, rzt, rzb, mat, seg=20, rings=10, sq=2.0):
    """An ellipsoid (top / bottom half heights rzt / rzb); sq > 2 squares its plan (superellipse)."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for vt in res["verts"]:
        x, y, z = vt.co
        if sq != 2.0 and (x or y):
            th = math.atan2(y, x)
            k = (abs(math.cos(th)) ** sq + abs(math.sin(th)) ** sq) ** (-1 / sq)
            x, y = x * k, y * k
        vt.co = B(cu + x * ru, cv - y * rv, cz + z * (rzt if z > 0 else rzb))
    faces = {f for vt in res["verts"] for f in vt.link_faces}
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def tube(bm, p0, p1, r, mat, seg=10, rz=None):
    """A round bar between two sprite points (u, v, z), capped."""
    a, b = B(*p0), B(*p1)
    d = b - a
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r * PX, radius2=r * PX,
                                depth=d.length)
    q = d.to_track_quat("Z", "Y")
    for vt in res["verts"]:
        co = vt.co.copy()
        if rz:
            co.y *= rz
        vt.co = q @ co + (a + b) / 2
    faces = {f for vt in res["verts"] for f in vt.link_faces}
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


# --------------------------------------------------------------------------- the claw

HAND_H = pchip([0.5, 2.0, 4.0, 7.0, 10.0, 13.0, 15.5], [1.3, 2.3, 3.3, 4.3, 4.8, 4.8, 4.3])
FINGER_H = pchip([16.0, 16.5, 17.3, 18.3, 21.0, 24.0, 28.0, 31.0, 33.0],
                 [4.75, 4.85, 4.3, 4.0, 3.8, 3.3, 2.5, 1.7, 1.0])
DACT_H = pchip([0.0, 3.0, 8.0, 14.0], [2.7, 2.5, 2.0, 1.25])


def socket_dent(u, v):
    cu, cv, ru, rv = SOCKET_AT
    d2 = ((u - cu) / ru) ** 2 + ((v - cv) / rv) ** 2
    return 1.5 * math.exp(-d2 * 1.6)


def build_pose(sprites, pieces, pose, mirror, mats_of, tag):
    p = POSES[pose]
    idx, colors = pose_pixels(sprites, pieces, pose, mirror)
    lab, m = label(idx, colors, p)
    M = {k: i for i, k in enumerate(PARTS)}
    bm = bmesh.new()

    def in_socket(f):
        c = f.calc_center_median()
        u, v, z = c.x / PX + 12, 14 - c.y / PX, c.z / PX
        cu, cv, ru, rv = SOCKET_AT
        return z > 0.3 and ((u - cu) / (ru * 0.95)) ** 2 + ((v - cv) / (rv * 0.95)) ** 2 < 1.0

    hand = edges(lab, "hand")
    finger = edges(lab, "finger")
    # the hand runs on under the finger's rim lip (the overlap step), its end tucked inside
    hrows = dict(hand)
    last = max(hand)
    hrows[last + 1] = (max(hand[last][0], finger[last + 1][0] + 0.3), min(hand[last][1], finger[last + 1][1] - 0.3))
    part_loft(bm, hrows, lambda v: HAND_H(v) if v < 15.6 else HAND_H(15.5) - 1.6 * (v - 15.5),
              M["hand"], a=0.47, ends=("point", "blunt"), ext=(0.5, 0.3), dent=socket_dent,
              mat_of=lambda f: M["socket"] if in_socket(f) else M["hand"], end_u=(6.0, None))
    # the finger's rim lip stands up over the hand's lower edge (lit top, shadowed riser)
    frows = dict(finger)
    first = min(finger)
    frows[first - 1] = finger[first]
    frows = dict(sorted(frows.items()))
    part_loft(bm, frows, lambda v: FINGER_H(max(v, 16.0)), M["finger"], a=0.45,
              ends=("blunt", "point"), ext=(0.45, 0.75), step=0.5, dent=socket_dent,
              mat_of=lambda f: M["socket"] if in_socket(f) else M["finger"], end_u=(None, 9.6))
    # the knuckle: a round knob, the lens in its bezel facing up-left as the sprite's 60 / 136 pixels
    kn = [(r, c) for (r, c), q in lab.items() if q == "knob"]
    # an ellipse of the knob pixels' own centroid and spread (r = 2 sigma for a filled ellipse)
    cu = sum(c + 0.5 for _, c in kn) / len(kn)
    cv = sum(r + 0.5 for r, _ in kn) / len(kn)
    ru = 2 * math.sqrt(sum((c + 0.5 - cu) ** 2 for _, c in kn) / len(kn) + 1 / 12)
    rv = 2 * math.sqrt(sum((r + 0.5 - cv) ** 2 for r, _ in kn) / len(kn) + 1 / 12)
    kz, kt, kb = 1.3, 3.0, 2.6
    ellipsoid(bm, cu, cv, kz, ru * 0.97, rv * 0.97, kt, kb, M["knob"], seg=24, rings=12, sq=2.5)
    lu, lv = p["lens"]
    q2 = min(0.9, ((lu - cu) / ru) ** 2 + ((lv - cv) / rv) ** 2)
    lz = kz + kt * math.sqrt(1 - q2)
    ellipsoid(bm, lu, lv, lz - 0.3, 0.7, 1.05, 0.5, 0.3, M["bezel"], seg=14, rings=6)
    ellipsoid(bm, lu, lv + 0.2, lz - 0.18, 0.45, 0.62, 0.55, 0.3, M["lens"], seg=12, rings=6)
    # the pin (the sprite's dark-sided neck) from the knuckle down into the dactyl, with a collar
    nk = sorted(c for (r, c), q in lab.items() if q == "neck")
    nu = (nk[0] + nk[-1] + 1) / 2 if nk else cu
    nv = p["neck"] + 0.5
    # the dactyl: a hooked blade from the pin, tapering to its tip
    drows = edges(lab, "dact")
    d0 = min(drows)
    du = sum(drows[d0]) / 2
    # the pin's upper bar runs 0.15 px on past the joint (inside the collar): ended exactly on the
    # lower bar's cap, the two caps coincided where the bars line up (pose A) and their shared ring
    # welded into edges of four faces
    jx, jy = 0.5 * (du - nu), nv - cv
    jl = math.hypot(jx, jy) or 1.0
    tube(bm, (nu, cv, 0.6), (nu + jx * (1 + 0.15 / jl), nv + jy * 0.15 / jl, 0.6), 0.85, M["pin"], seg=10)
    tube(bm, (nu + 0.5 * (du - nu), nv, 0.6), (du, d0 + 0.8, 0.6), 0.85, M["pin"], seg=10)
    tube(bm, (nu, nv - 0.3, 0.6), (nu, nv + 0.25, 0.6), 1.05, M["pin"], seg=12, rz=0.9)
    part_loft(bm, drows, lambda v: DACT_H(v - d0), M["dact"], a=0.5, hb_k=0.6, hb_0=0.25,
              ends=("blunt", "point"), ext=(0.4, 0.6), step=0.5, z0=0.2)
    # the link bar to the hand (open pose)
    if p["link"]:
        (r0, r1), c0 = p["link"]
        vm = (r0 + r1 + 1) / 2 + 0.45
        tube(bm, (c0 - 1.5, vm, 1.4), (cu, vm, 1.4), 0.85, M["pin"], seg=12, rz=1.25)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{tag}-{pose}")
    bm.to_mesh(me)
    bm.free()
    for k in PARTS:
        me.materials.append(mats_of[k])
    if mirror:
        for vt in me.vertices:
            vt.co.x = -vt.co.x - PX
        me.flip_normals()
    try:
        me.set_sharp_from_angle(angle=math.radians(60))
    except AttributeError:
        pass
    obj = bpy.data.objects.new(f"{tag}-{pose}", me)
    return obj, (idx, colors, m)


def _apply(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    obj.data = new


def hold_inside(shell, sealed, inside):
    """Put every shell vertex `inside` under the sealed surface, along its outward normal at the
    nearest point (a shrinkwrap in INSIDE mode leaves the vertices already inside where they are,
    a hair under the surface, and the shell then shows through the model in specks)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(sealed.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    tree = BVHTree.FromBMesh(bm)
    for vt in shell.data.vertices:
        loc, nrm, _, _ = tree.find_nearest(vt.co)
        if loc is not None:
            vt.co = loc - nrm * inside
    bm.free()
    shell.data.update()


def outline_shell(obj, coll, voxel=0.011, faces=2000, smooth=4, inside=0.15 * PX):
    """common.outline_shell, keeping every island (the dactyl and knuckle can stand apart from the
    hand), and held inside the model (D88/D90) against a sealed copy: the parts overlap (the hand
    runs on under the finger's rim, the pin into the knuckle), so the model has inner faces that
    would steer a shrinkwrap; a fine voxel remesh of it is the clean outer surface to hold to. Every
    shell vertex is put `inside` under that surface (a smoothed remesh otherwise lies right on the
    model and shows through it in specks wherever it is drawn with colour)."""
    def remeshed(src, name, size):
        me = src.data.copy()
        me.materials.clear()
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        rm = o.modifiers.new("remesh", "REMESH")
        rm.mode = "VOXEL"
        rm.voxel_size = size
        rm.adaptivity = 0.0
        return o
    sealed = remeshed(obj, f"{obj.name}_sealed", 0.004)
    _apply(sealed)
    shell = remeshed(obj, f"{obj.name}_outline", voxel)
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    _apply(shell)
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
        _apply(shell)
    if inside > 0:
        hold_inside(shell, sealed, inside)
    bpy.data.objects.remove(sealed, do_unlink=True)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def split_open(obj, layout, suffix="_outline"):
    """common.split_assembly's cut without capping (for the outline shells): a capped shell draws an
    ink line across the claw at the piece seam."""
    out = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        me.shade_smooth()
        o = bpy.data.objects.new(name + suffix, me)
        o["tyrian_outline"] = True
        coll.objects.link(o)
        out[name] = o
    return out


def render_mask(objs, path, rows=56):
    """Flat white top view of `objs` on the sprite grid (24 x rows px at 12 per px), transparent."""
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o not in objs
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sd = scene.display.shading
    sd.light = "FLAT"
    sd.color_type = "SINGLE"
    sd.single_color = (1, 1, 1)
    sd.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_percentage = 100
    scene.render.resolution_x, scene.render.resolution_y = 24 * 12, rows * 12
    cam = bpy.data.objects.get("mask_cam")
    if cam is None:
        cd = bpy.data.cameras.new("mask_cam")
        cd.type = "ORTHO"
        cam = bpy.data.objects.new("mask_cam", cd)
        scene.collection.objects.link(cam)
    cam.data.ortho_scale = rows / 12
    cam.location = (0, (14 - rows / 2) / 12, 5)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def build_assembly(script_file, name, pieces, mirror):
    root = common.repo_root(script_file)
    sprites = {p: common.load_sprite(root, p) for p, _, _ in pieces}
    merged = dict(sprites[pieces[0][0]])
    merged["colors"] = {}
    for s in sprites.values():
        merged["colors"].update(s["colors"])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    measure = Path(argv[argv.index("--measure") + 1]) if "--measure" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(merged, i, name, **kw)  # noqa: E731
    mats_of = dict(
        hand=pal(IDX["hand"], **SATIN), finger=pal(IDX["finger"], **SATIN), knob=pal(IDX["knob"], **SATIN),
        dact=pal(IDX["dact"], **SATIN), pin=pal(IDX["pin"], metallic=0.45, roughness=0.38),
        socket=pal(IDX["socket"], metallic=0.3, roughness=0.5),
        lens=pal(IDX["lens"], metallic=1.0, roughness=0.6, emission_strength=1.0),
        bezel=pal(IDX["bezel"], metallic=0.6, roughness=0.3))
    report = {}
    for pose in ("A", "B", "C"):
        obj, (idx, colors, m) = build_pose(sprites, pieces, pose, mirror, mats_of, name)
        coll.objects.link(obj)
        bpy.context.view_layer.update()
        shell = outline_shell(obj, coll)
        layout = [(models[pose][0], 0, rows) for _, rows, models in pieces]
        cut = common.split_assembly(obj, layout)
        for pc in cut.values():  # the cut's cap keeps its own normals (no shading seam across the claw)
            try:
                pc.data.set_sharp_from_angle(angle=math.radians(60))
            except AttributeError:
                pass
        shells = split_open(shell, layout)
        tris = 0
        for piece, rows, models in pieces:
            model, frame = models[pose]
            src = sprites[piece]["sprites"][0]
            assert frame in src["frames"], (piece, frame)
            subset = [{**src, "frames": [frame]}]
            shells[model].name = f"{model}_outline"
            common.export_sprite_model(root, [cut[model], shells[model]], f"enemies/{model}", subset)
            tris += sum(len(pp.vertices) - 2 for pp in cut[model].data.polygons)
        rep = dict(tris=tris, outline_faces=len(shell.data.polygons))
        if measure:
            measure.mkdir(parents=True, exist_ok=True)
            if mirror:  # measure against the right claw's own pixels
                ridx = [[row[22 - c] if 0 <= 22 - c < 24 else -1 for c in range(24)] for row in idx]
                m = SM.masks(ridx, colors)
            png = measure / f"{name}-{pose}-mask.png"
            render_mask([obj], png)
            rep.update(SM.measure(m, SM.read_png_mask(str(png))))
        report[pose] = rep
        print(f"POSE {name} {pose} {json.dumps(rep)}")
        for o in [shell] + list(cut.values()) + list(shells.values()):
            o.hide_render = True
        obj.hide_render = True
    if measure:
        (measure / f"{name}.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    build_assembly(__file__, NAME, PIECES, mirror=False)
