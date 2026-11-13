"""Red blob (newsh3.shp frames 128, 130, 132).

What it is: a living blob of molten goo squatting on the ground of 4.6 (CORE): rows of them are
fixed to the terrain (e4:253, e4:256), the 'air' flag notwithstanding (D120). Shot, 253 bursts
into the molten fireball newsh3-229; 256 spits that fireball as a homing shot. So: a glossy, dark
red skin of goo bulging into a dome, a white-hot nucleus glowing through its upper left, and a
viscous spill with droplets round its foot.

Reading the 24x28 sprite (D74: the 1 px ink ring 112 is the game's outline, so the top view goes
to the INNER mask):
  - dome: rows 3-19, columns 1-22; its skin is 114 (113/112 down the lower right are its shade,
    the 115/116 band down the right side and along its foot is reflected light: lighting, never
    paint or geometry, art rule 2).
  - hot spot: 127 core (2x2), 124-126 round it, 118-122 halo, in the upper left (columns 6-10,
    rows 7-11 on frame 128). A glowing nucleus bulging through the skin: a domed lens of three
    emissive rings.
  - spill: rows 19-25, a ragged skirt of goo (median 113) below and beside the dome's foot, with
    droplets (bright 116-118 cores in ink) thrown round it, different on every frame.
  - frames: 130 lifts the dome's top a pixel and pulls its right side in; 132 lifts it two and
    pulls both sides in, the nucleus riding up with it. One body per frame (common.frame_part).

Built as one faired polar surface per frame about the dome's centre: a superelliptic dome whose
foot blends (smooth max) into a low spill with a rounded meniscus lip; the spill's outline is the
frame's main inner-mask region, rounded (blurred mask, half level), so the silhouette matches row
by row. Droplets: beads at the mask's detached pieces; detached ink-only specks get a pinhead bead
(too small to cover a sprite pixel) so the game's ink draws them as the sprite does.
Underside: flat and closed (it sits on the ground).

Run: blender --background --python assets/blender/enemies/newsh3-128.py [-- --preview out.png]
(exports public/models/enemies/newsh3-128.glb and src/render/spriteModels/newsh3-128.json; the repo
is found from this file's location; --out X.glb additionally writes a review copy)
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]   # the repo (assets/blender/enemies/<this>)
NAME = "newsh3-128"

U = 1 / 12      # one sprite px in Blender units
W, H = 24, 28   # the sprite

SKIN, GOO, DROP, BRIGHT, HALO, RING, CORE = range(7)
MATS = [  # (key, palette index, metallic, roughness, specular IOR level, emission)
    ("skin", 114, 0.45, 0.22, 0.5, 0.0),     # glossy dark red skin (metallic: red-tinted gloss)
    ("goo", 114, 0.35, 0.3, 0.5, 0.0),       # the spill (non-ink median 114), a little less glossy
    ("drop", 115, 0.2, 0.2, 0.8, 0.0),       # plain droplets
    ("bright", 118, 0.0, 0.3, 0.6, 0.45),    # droplets still glowing (ember)
    ("halo", 121, 1.0, 0.55, 0.5, 0.8),      # nucleus: orange halo (D126/D173 glow: metallic 1, rough)
    ("ring", 125, 1.0, 0.5, 0.5, 1.0),       # yellow ring
    ("core", 127, 1.0, 0.45, 0.5, 1.4),      # white-hot core
]

# Per frame: the dome's plan (centre column, top row edge, half width, the row of its waist, the
# row edge of its foot; fitted to the inner mask above row 17), its height (px), the nucleus centre
# (edge coords).
FRAMES = {
    128: dict(dome=(12.0, 4.25, 10.25, 17.5, 19.6), h=6.6, hot=(8.4, 9.0)),
    130: dict(dome=(11.5, 3.25, 9.75, 17.5, 19.4), h=7.4, hot=(8.4, 8.0)),
    132: dict(dome=(11.75, 2.5, 9.25, 17.5, 19.2), h=8.2, hot=(9.4, 7.0)),
}

NSEG = 80            # around
NDOME = 16           # rings rim -> pole on the dome
NSPILL = 6           # rings dome foot -> spill rim
DOME_P = 2.8         # plan superellipse exponent (fitted)
PROFILE_POW = 0.55   # dome profile: membrane ** this
PROFILE = 2.3        # dome superellipse exponent (2 = ellipse; more = fuller shoulders, a blob)
SPILL_H = 0.8        # px
LIP = 1.1            # px, the spill's rounded edge width
FILLET = 2.0         # px, smooth-max blend of dome into spill
SEAL_FILLET = 4.0    # px, the same for the outline shell's sealed copy
BLUR = 0.35          # px, mask blur (rounds the staircase)
LEVEL = 0.5
SMOOTH_PASSES = 1
HOT_R = (1.1, 1.75, 2.5)   # px: core, ring, halo radii
HOT_BULGE = 0.45     # px the nucleus bulges out of the skin


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def X(c):
    """Edge coordinate c (0 = the sprite's left edge) -> units."""
    return (c - W / 2) * U


def Y(r):
    return (H / 2 - r) * U


# --- The masks ------------------------------------------------------------------------------------

def sprite_masks(frame):
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as S
    idx, colors = S.load(NAME, frame, ref=WT / "reference" / "models")
    m = S.masks(idx, colors, ())
    return {k: np.array(m[k], bool) for k in ("outer", "inner", "border", "free")}, np.array(idx)


def components(mask):
    """8-connected components of a bool array: list of [(r, c), ...], biggest first."""
    seen = np.zeros_like(mask, bool)
    out = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        stack, comp = [(r0, c0)], []
        seen[r0, c0] = True
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < mask.shape[0] and 0 <= cc < mask.shape[1] and mask[rr, cc] and not seen[rr, cc]:
                        seen[rr, cc] = True
                        stack.append((rr, cc))
        out.append(comp)
    return sorted(out, key=len, reverse=True)


def blurred_field(mask, k=16, pad=3):
    big = np.kron(np.pad(mask.astype(float), pad), np.ones((k, k)))
    s = BLUR * k
    xs = np.arange(-int(3 * s) - 1, int(3 * s) + 2)
    g = np.exp(-0.5 * (xs / s) ** 2)
    g /= g.sum()
    big = np.apply_along_axis(lambda v: np.convolve(v, g, "same"), 0, big)
    big = np.apply_along_axis(lambda v: np.convolve(v, g, "same"), 1, big)

    def sample(c, r):
        fx = (c + pad) * k - 0.5
        fy = (r + pad) * k - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        if x0 < 0 or y0 < 0 or x0 + 1 >= big.shape[1] or y0 + 1 >= big.shape[0]:
            return 0.0
        a = big[y0, x0] * (1 - tx) + big[y0, x0 + 1] * tx
        b = big[y0 + 1, x0] * (1 - tx) + big[y0 + 1, x0 + 1] * tx
        return a * (1 - ty) + b * ty
    return sample


def polar_radii(field, cen, smooth=SMOOTH_PASSES):
    radii = []
    for i in range(NSEG):
        a = 2 * math.pi * i / NSEG
        dx, dy = math.cos(a), -math.sin(a)
        t, step = 0.0, 0.05
        while field(cen[0] + dx * t, cen[1] + dy * t) >= LEVEL and t < 20:
            t += step
        lo, hi = max(0.0, t - step), t
        for _ in range(20):
            mid = (lo + hi) / 2
            if field(cen[0] + dx * mid, cen[1] + dy * mid) >= LEVEL:
                lo = mid
            else:
                hi = mid
        radii.append((lo + hi) / 2)
    pts = np.array([(cen[0] + r * math.cos(2 * math.pi * i / NSEG), cen[1] - r * math.sin(2 * math.pi * i / NSEG))
                    for i, r in enumerate(radii)])
    k = np.array([1, 4, 6, 4, 1], float) / 16
    for _ in range(smooth):
        pts = sum(k[j] * np.roll(pts, j - 2, axis=0) for j in range(5))
    d = pts - np.array(cen)
    return np.hypot(d[:, 0], d[:, 1])


def frame_layout(frame):
    """(outer radii, dome radii, beads) of a frame. beads: (c, r, rx, ry, material) edge coords/px."""
    spec = FRAMES[frame]
    m, idx = sprite_masks(frame)
    inner = m["inner"]
    comps = components(inner)
    main = np.zeros_like(inner)
    for r, c in comps[0]:
        main[r, c] = True
    cx, top, rx, waist, foot = spec["dome"]
    cen = (cx, (top + foot) / 2)
    rm = polar_radii(blurred_field(main), cen)

    def dome_r(a):
        """Distance from cen along angle a to the dome's plan: a superellipse (DOME_P) whose upper
        half reaches up to `top` and out to rx at the waist row, and whose lower half closes at
        the foot row."""
        dx, dy = math.cos(a), -math.sin(a)
        lo, hi = 0.0, 20.0
        for _ in range(32):
            mid = (lo + hi) / 2
            y = cen[1] + dy * mid
            ny = (y - waist) / ((waist - top) if y < waist else (foot - waist))
            if abs(dx * mid / rx) ** DOME_P + abs(ny) ** DOME_P < 1:
                lo = mid
            else:
                hi = mid
        return lo
    rd = np.array([dome_r(2 * math.pi * i / NSEG) for i in range(NSEG)])
    # The outline: the dome's plan above its waist, the spill's rounded mask below (blended over
    # the sides), never inside the dome's foot.
    ro = []
    for i in range(NSEG):
        a = 2 * math.pi * i / NSEG
        y = cen[1] - rd[i] * math.sin(a)       # row of the dome's edge in this direction
        w = min(1.0, max(0.0, (y - (waist - 2.0)) / 3.0))   # 0 above the waist, 1 below
        w = w * w * (3 - 2 * w)
        ro.append(max(rd[i] + 0.12 * w, rd[i] * (1 - w) + rm[i] * w))
    ro = np.array(ro)
    beads = []
    # Detached pieces of the inner mask: real droplets covering their pixels.
    for comp in comps[1:]:
        rs = [p[0] for p in comp]
        cs = [p[1] for p in comp]
        vals = [idx[r][c] for r, c in comp]
        mat = BRIGHT if max(vals) >= 117 else DROP
        if len(comp) <= 2:
            beads.append((np.mean(cs) + 0.5, np.mean(rs) + 0.5, 0.5 + 0.5 * (max(cs) - min(cs) + 1) / 2,
                          0.5 + 0.5 * (max(rs) - min(rs) + 1) / 2, mat))
        else:   # a cluster: one bead per pixel, merging into a splash
            for r, c in comp:
                beads.append((c + 0.5, r + 0.5, 0.62, 0.62, BRIGHT if idx[r][c] >= 117 else DROP))
    # Pixels of the main region the rounded outline leaves out (one-pixel drips and necks): a drip
    # bead each, sitting into the spill's edge.
    poly = [(cen[0] + ro[i] * math.cos(2 * math.pi * i / NSEG), cen[1] - ro[i] * math.sin(2 * math.pi * i / NSEG))
            for i in range(NSEG)]

    def inside(c, r):
        n, ins = len(poly), False
        for i in range(n):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
            if (y1 > r) != (y2 > r) and c < x1 + (r - y1) * (x2 - x1) / (y2 - y1):
                ins = not ins
        return ins
    for r, c in comps[0]:
        if not inside(c + 0.5, r + 0.5):
            beads.append((c + 0.5, r + 0.5, 0.62, 0.62, BRIGHT if idx[r][c] >= 117 else GOO))
    # Ink-only specks touching nothing else: pinhead beads (the game's ink draws the speck).
    near = np.zeros_like(inner)
    for r, c in zip(*np.nonzero(inner)):
        near[max(0, r - 1):r + 2, max(0, c - 1):c + 2] = True
    for comp in components(m["border"] & ~near):
        rs = [p[0] for p in comp]
        cs = [p[1] for p in comp]
        vals = [idx[r][c] for r, c in comp]
        mat = BRIGHT if max(vals) >= 117 else DROP
        beads.append((np.mean(cs) + 0.5, np.mean(rs) + 0.5, 0.3, 0.3, mat))
    return cen, ro, rd, beads, inflated(cen, rd)


def inflated(cen, rd, k=8):
    """The dome's height as an inflated membrane over its plan (a skin under surface tension:
    lap(u) = -1 inside, 0 on the edge), normalised to 1 at its peak. Its contours round the plan's
    corners off, so no crease runs from the corners up to the crown (as a polar profile would).
    Solved coarse to fine (Jacobi) at 1, 2, 4 and 8 cells per sprite px."""
    def plan(kk):
        gh, gw = H * kk, W * kk
        rr, cc = np.mgrid[0:gh, 0:gw]
        c = (cc + 0.5) / kk - cen[0]
        r = (rr + 0.5) / kk - cen[1]
        ang = np.arctan2(-r, c) % (2 * math.pi)
        t = ang / (2 * math.pi) * NSEG
        i0 = np.floor(t).astype(int) % NSEG
        f = t - np.floor(t)
        edge = rd[i0] * (1 - f) + rd[(i0 + 1) % NSEG] * f
        return np.hypot(c, r) < edge
    u = None
    for kk, iters in ((1, 800), (2, 800), (4, 1000), (8, 1200)):
        inside = plan(kk)
        u = np.zeros(inside.shape) if u is None else np.kron(u, np.ones((2, 2)))
        h2 = (1.0 / kk) ** 2
        for _ in range(iters):
            nb = (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) + h2) / 4
            u = np.where(inside, nb, 0.0)
    gh, gw = u.shape
    u = u / u.max()

    def sample(ce, re_):
        fx, fy = ce * k - 0.5, re_ * k - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        x0, y0 = min(max(x0, 0), gw - 2), min(max(y0, 0), gh - 2)
        a = u[y0, x0] * (1 - tx) + u[y0, x0 + 1] * tx
        b = u[y0 + 1, x0] * (1 - tx) + u[y0 + 1, x0 + 1] * tx
        return max(0.0, a * (1 - ty) + b * ty)
    return sample


# --- The body -------------------------------------------------------------------------------------

def smax(a, b, k):
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k / 4


def build_body(bm, frame, layout, fillet=None):
    """The dome and its spill as one faired polar surface with a flat closed underside."""
    spec = FRAMES[frame]
    cen, ro, rd, _, memb = layout
    hd = spec["h"]

    def height(c, r, rho_d, dist_rim):
        # membrane value u ~ 1 - rho^2 near a round edge: u ** PROFILE_POW gives the profile
        # (0.5 = an ellipsoid; less = fuller shoulders, the blob's surface tension)
        dz = hd * memb(c, r) ** PROFILE_POW if rho_d < 1 else 0.0
        t = min(1.0, max(0.0, dist_rim / LIP))
        pz = SPILL_H * math.sqrt(max(0.0, 1 - (1 - t) ** 2))
        return smax(dz, pz, fillet or FILLET)

    rings = []   # list of (list of (c, r, z_px)), outermost first
    # spill rim -> dome foot
    for j in range(NSPILL):
        u = j / NSPILL
        u = u ** 1.4
        ring = []
        for i in range(NSEG):
            a = 2 * math.pi * i / NSEG
            rad = ro[i] + (rd[i] - ro[i]) * u
            ring.append((cen[0] + rad * math.cos(a), cen[1] - rad * math.sin(a), height(cen[0] + rad * math.cos(a), cen[1] - rad * math.sin(a), rad / rd[i], ro[i] - rad)))
        rings.append(ring)
    # dome foot -> pole
    for j in range(NDOME):
        phi = (math.pi / 2) * j / NDOME
        ring = []
        for i in range(NSEG):
            a = 2 * math.pi * i / NSEG
            rad = rd[i] * math.cos(phi)
            ring.append((cen[0] + rad * math.cos(a), cen[1] - rad * math.sin(a), height(cen[0] + rad * math.cos(a), cen[1] - rad * math.sin(a), rad / rd[i], ro[i] - rad)))
        rings.append(ring)
    pole = (cen[0], cen[1], height(cen[0], cen[1], 0.0, 99))
    vr = [[bm.verts.new((X(c), Y(r), z * U)) for c, r, z in ring] for ring in rings]
    vp = bm.verts.new((X(pole[0]), Y(pole[1]), pole[2] * U))
    faces = []
    for j, (r0, r1) in enumerate(zip(vr, vr[1:])):
        for i in range(NSEG):
            k = (i + 1) % NSEG
            f = bm.faces.new((r0[i], r0[k], r1[k], r1[i]))
            f.material_index = GOO if j < NSPILL - 1 else SKIN
            faces.append(f)
    for i in range(NSEG):
        f = bm.faces.new((vr[-1][i], vr[-1][(i + 1) % NSEG], vp))
        f.material_index = SKIN
        faces.append(f)
    # Underside: flat cap over the rim ring.
    bot = bm.faces.new(list(reversed(vr[0])))
    bot.material_index = GOO
    for f in faces:
        f.smooth = True
    import bmesh
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return faces


def build_beads(bm, beads):
    import bmesh
    from mathutils import Vector
    for c, r, rx, ry, mat in beads:
        before = set(bm.faces)
        res = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=5, radius=1.0)
        hz = min(rx, ry) * 0.75
        for v in res["verts"]:
            z = v.co.z
            # flattened drop: round top, flat bottom on the ground
            v.co = Vector((X(c) + v.co.x * rx * U, Y(r) + v.co.y * ry * U, max(0.0, z) * hz * U if z >= 0 else 0.0))
        bmesh.ops.remove_doubles(bm, verts=res["verts"], dist=1e-6)
        for f in set(bm.faces) - before:
            f.material_index = mat
            f.smooth = True


def build_nucleus(bm, frame, body_tree):
    """The white-hot nucleus: a lens bulging through the skin, three emissive rings."""
    from mathutils import Vector
    hc, hr = FRAMES[frame]["hot"]
    R = HOT_R[-1]
    nr, ns = 9, 32
    rings = []
    for j in range(nr + 1):
        d = R * (1 - j / nr)
        ring = []
        for i in range(ns if j < nr else 1):
            a = 2 * math.pi * i / ns
            c, r = hc + d * math.cos(a), hr - d * math.sin(a)
            hit = body_tree.ray_cast(Vector((X(c), Y(r), 2.0)), Vector((0, 0, -1)))
            z = hit[0].z if hit[0] is not None else 0.0
            n = hit[1] if hit[0] is not None else Vector((0, 0, 1))
            t = d / R
            bulge = HOT_BULGE * (1 - t * t) ** 1.2 - 0.06 * t ** 4
            p = Vector((X(c), Y(r), z)) + n * bulge * U
            ring.append((bm.verts.new(p), d))
        rings.append(ring)

    def mat_of(d):
        return CORE if d < HOT_R[0] else RING if d < HOT_R[1] else HALO
    for j in range(nr):
        a, b = rings[j], rings[j + 1]
        for i in range(ns):
            k = (i + 1) % ns
            if len(b) == 1:
                vs = (a[i][0], a[k][0], b[0][0])
                d = (a[i][1] + b[0][1]) / 2
            else:
                vs = (a[i][0], a[k][0], b[k][0], b[i][0])
                d = (a[i][1] + b[i][1]) / 2
            f = bm.faces.new(vs)
            f.material_index = mat_of(d)
            f.smooth = True


def sink_shell_front(shell, layout):
    """Flatten the outline shell under the spill where the spill shows beyond the dome's foot
    (its front and lower sides): there the dome's foot is an internal edge seen over the spill, and
    the shell's hull drew it as an ink line across the foot. The shell keeps its height round the
    rest of the dome (its back and shoulders, the silhouette) and at the spill's own rim."""
    cen, ro, rd = layout[0], layout[1], layout[2]
    band = ro - rd
    for v in shell.data.vertices:
        c = v.co.x / U + W / 2
        r = H / 2 - v.co.y / U
        a = math.atan2(-(r - cen[1]), c - cen[0]) % (2 * math.pi)
        t = a / (2 * math.pi) * NSEG
        i = int(t) % NSEG
        f = t - int(t)
        b = band[i] * (1 - f) + band[(i + 1) % NSEG] * f
        rim = ro[i] * (1 - f) + ro[(i + 1) % NSEG] * f
        rad = math.hypot(c - cen[0], r - cen[1])
        w = min(1.0, max(0.0, (b - 0.3) / 0.7))
        w = w * w * (3 - 2 * w)
        w *= min(1.0, max(0.0, (rim - 0.5 - rad) / 0.6))    # keep the spill's rim
        dr = rd[i] * (1 - f) + rd[(i + 1) % NSEG] * f
        q = min(1.0, max(0.0, (rad / dr - 0.45) / 0.3))      # and the crown (no cliff by the pole)
        w *= q * q * (3 - 2 * q)
        if w <= 0:
            continue
        low = max(0.0, (SPILL_H - 0.35)) * U
        if v.co.z > low:
            v.co.z = v.co.z * (1 - w) + low * w
    shell.data.update()


def spec_level(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def build():
    import bmesh
    import bpy
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import common

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = [spec_level(common.palette_material(sprite, idx, NAME + ("" if key == "skin" else f"-{key}"),
                                               metallic=met, roughness=rough, emission_strength=em), lvl)
            for key, idx, met, rough, lvl, em in MATS]
    objs, manifest = [], {}
    for frame in FRAMES:
        layout = frame_layout(frame)
        oname = NAME if frame == 128 else f"{NAME}-{frame}"
        # Sealed copy for the outline shell: body + droplets with the dome's foot filled by a broad
        # cove (SEAL_FILLET), so the shell has no concave crease there to fold into an ink line
        # across the foot; it stands a hair over the real fillet, where only its unseen front
        # faces are. The nucleus lies inside the silhouette and gets no ink of its own.
        bm = bmesh.new()
        build_body(bm, frame, layout, fillet=SEAL_FILLET)
        build_beads(bm, layout[3])
        seal_me = bpy.data.meshes.new(oname + "_seal")
        bm.to_mesh(seal_me)
        bm.free()
        bm = bmesh.new()
        build_body(bm, frame, layout)
        build_beads(bm, layout[3])
        tree = BVHTree.FromBMesh(bm)
        build_nucleus(bm, frame, tree)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(oname)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(oname, mesh)
        coll.objects.link(obj)
        common.frame_part(obj, [frame])
        seal = bpy.data.objects.new(oname + "_seal", seal_me)
        coll.objects.link(seal)
        bpy.context.view_layer.update()
        shell = common.outline_shell(seal, coll, voxel=0.004, faces=2000, smooth=3, inside=0.002,
                                     islands="outer", min_new_px=1)
        bpy.data.objects.remove(seal, do_unlink=True)
        shell.name = f"{oname}_outline"
        sink_shell_front(shell, layout)
        assert len(shell.data.polygons) > 0, "empty outline shell"
        common.frame_part(shell, [frame])
        mesh.calc_loop_triangles()
        manifest[frame] = {"tris": len(mesh.loop_triangles), "shell_faces": len(shell.data.polygons),
                           "beads": len(layout[3])}
        objs += [obj, shell]
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    if arg("--out"):
        common.export_glb(objs, Path(arg("--out")))
    if "--preview" in sys.argv:
        frames = {f["index"]: f for f in sprite["frames"]}
        f0 = frames[128]
        common.render_preview(objs, sys.argv[sys.argv.index("--preview") + 1],
                              WT / "reference" / "models" / NAME / f0["image"], size=f0["size"], frame=128)
    print("MANIFEST", json.dumps({NAME: manifest}))


if __name__ == "__main__":
    build()
