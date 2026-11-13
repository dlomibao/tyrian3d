"""Twin-claw jet (newsh3.shp frames 10, 48), DESIGN A.

What it is: a small attack craft (e4:223, armour 8) that enters from the left edge and crosses the
screen to the right, so its nose is to the right (+x) and its tail to the left. Seen from above, as
the sprite draws it:

  - two claws: blade hulls lying in the plane, one north and one south, mirror images about the
    centre row. Each is blunt and round at the tail (columns 1-3), deepest over columns 6-15 and
    sweeps to a sharp point at the nose (column 22). Plan from two pchip curves through the
    middles of the inner mask's steps (outer edge arching from row 6 over row 4 down to the tip at
    row 7.5; inner edge straight along row 9, stepping in to row 8 past column 13). Section: a
    thick round spine on the outer side with a flat top, a lengthwise panel groove (the sprite's
    dark row 6 / row 20), then a chamfered blade bevel falling to a blunt inner edge (the sprite's
    light row 7 / row 19 strip). Level along their length (no lean under the off-axis camera).
    Two chamfered armour plates stand proud on each spine, split by a seam at column 10.
  - the spine: a gunmetal strut along y at columns 3-6 that joins the claws, flaring into
    gussets under them at rows 9-10 and 16-17 (the sprite's dark root pixels); two machined bands
    round it. The sprite's light column 4 is sheen on its rounded face.
  - the torch: a short finned emitter on the strut's nose face at row 13.5 firing the fire jet
    forward between the claws (columns 6-20): an outer red plume, an orange mantle and a yellow
    core, per frame (common.frame_part): frame 10 the long full jet with the core near the root,
    frame 48 a thinner jet with its core two columns further on.
  - the engine: a small bell nozzle on the strut's tail face; its exhaust is the little flame out
    of the left side (columns 0-2), wider and redder on frame 10, a thin bright jet on frame 48.

Steel is satin (pal 6 spine, pal 7 plates, pal 8 bevel: the medians of the claw regions; F0 via
Specular IOR Level, D176). The sprite's bright tail-end spots are sheen. Flames glow (D126/D173:
metallic 1, roughness 0.9, emission about 1). Underside: the claws' and strut's mirrored
half-sections close it, no detail. The outline shell comes from a sealed copy of the steel only
(no plates, grooves or bands), islands="outer" (D189); the flames have no ink, as in the sprite.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh3-10.py
"""

import bisect
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = next(p for p in HERE.parents if (p / "package.json").exists())
NAME = "newsh3-10"
MID_R = 13.5          # the craft's centre line (row edge); the claws mirror about it


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def pchip(xs, ys):
    """Monotone cubic through (xs, ys) (copied from usp_talon.pchip)."""
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
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def P(x, r, z):
    """Sprite px (x = column edge, r = row edge, z up in px) -> Blender units."""
    return ((x - 12.0) / 12.0, (14.0 - r) / 12.0, z / 12.0)


# ---------------------------------------------------------------------------------------------
# Materials: key -> (palette index, metallic, roughness, emission, specular level)
MATS = [
    ("spine", 6, 0.6, 0.5, 0.0, 0.5),
    ("plate", 7, 0.6, 0.48, 0.0, 0.5),
    ("bevel", 8, 0.62, 0.42, 0.0, 0.55),
    ("strut", 5, 0.6, 0.28, 0.0, 0.8),
    ("nozzle", 3, 0.7, 0.45, 0.0, 0.5),
    ("bore", 1, 0.3, 0.8, 0.0, 0.3),
    ("red", 118, 1.0, 0.9, 1.0, 0.5),
    ("redlo", 117, 1.0, 0.9, 1.0, 0.5),
    ("orange", 121, 1.0, 0.9, 1.15, 0.5),
    ("amber", 120, 1.0, 0.9, 1.15, 0.5),
    ("yellow", 123, 1.0, 0.9, 1.2, 0.5),
    ("gold", 122, 1.0, 0.9, 1.2, 0.5),
]
K = {key: i for i, (key, *_r) in enumerate(MATS)}


# ---------------------------------------------------------------------------------------------
def loft(bm, rings, mat, cap0=True, cap1=True):
    """Join rings of points (same length, or a single point as a tip) in order. mat(band, seg)."""
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    for b, (r0, r1) in enumerate(zip(vs, vs[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[i], r1[j])
            elif len(r1) == 1:
                f = (r0[i], r1[0], r0[j])
            else:
                f = (r0[i], r1[i], r1[j], r0[j])
            bm.faces.new(f).material_index = mat(b, i)
    for ring, cap, b in ((vs[0], cap0, 0), (vs[-1], cap1, len(vs) - 2)):
        if cap and len(ring) > 2:
            c = bm.verts.new([sum(v.co[k] for v in ring) / len(ring) for k in range(3)])
            n = len(ring)
            for i in range(n):
                f = (ring[i], ring[(i + 1) % n], c) if ring is vs[0] else (ring[(i + 1) % n], ring[i], c)
                bm.faces.new(f).material_index = mat(b, i)


# --- claws -----------------------------------------------------------------------------------
# Top claw edges (row edges) along x (column edges), fitted to the inner mask's step middles.
X0, X1 = 0.78, 23.3
R_OUT = pchip([0.78, 2.0, 3.0, 4.5, 6.0, 7.5, 14.5, 16.0, 17.5, 19.0, 20.5, 22.0, 23.3],
              [6.0, 5.85, 5.5, 4.9, 4.4, 4.05, 4.05, 4.45, 5.0, 5.5, 6.1, 6.8, 7.6])
R_IN = pchip([0.78, 10.5, 12.0, 13.5, 15.0, 21.0, 22.5, 23.3],
             [9.0, 9.0, 8.85, 8.35, 8.05, 8.0, 7.9, 7.6])
NOSE_R = 1.0     # the tail end is rounded over this length (px)
GROOVE = (-0.02, 0.12)   # panel groove across the section (u)


def claw_section(detail):
    """(u, v, kind) round the section; u -1 outer edge .. +1 inner edge, v -1 .. 1."""
    top = [(-1.0, 0.0, "s"), (-0.97, 0.45, "s"), (-0.86, 0.78, "s"), (-0.66, 0.96, "s"), (-0.4, 1.0, "s"),
           (GROOVE[0], 1.0, "s")]
    if detail:
        top += [(GROOVE[0] + 0.03, 0.84, "g"), (GROOVE[1] - 0.03, 0.84, "g")]
    top += [(GROOVE[1], 0.95, "b"), (0.45, 0.76, "b"), (0.78, 0.5, "b"), (0.95, 0.27, "b"), (1.0, 0.08, "b")]
    # underside: a plain closed half (no groove, fewer stations)
    bot = [(0.85, -0.42, "b"), (0.45, -0.8, "s"), (-0.3, -0.98, "s"), (-0.8, -0.82, "s"), (-0.97, -0.42, "s")]
    return top + bot


def claw_stations():
    xs = [X0, X0 + 0.04, X0 + 0.12, X0 + 0.25, X0 + 0.42, X0 + 0.62, X0 + 0.82, X0 + NOSE_R]
    x = 2.2
    while x < 21.5:
        xs.append(x)
        x += 0.75
    xs += [21.5, 22.0, 22.45, 22.85, 23.1]
    return xs


def claw_dims(x):
    ro, ri = R_OUT(x), R_IN(x)
    c, w = (ro + ri) / 2, (ri - ro) / 2
    h = max(0.22, min(1.6, 0.36 * 2 * w))
    if x < X0 + NOSE_R:
        t = (X0 + NOSE_R - x) / NOSE_R
        f = math.sqrt(max(0.0, 1 - t * t))
        w *= f
        h *= 0.35 + 0.65 * f
    return c, w, h


def build_claw(bm, north, detail):
    sec = claw_section(detail)
    rings = []
    for x in claw_stations():
        c, w, h = claw_dims(x)
        ring = []
        for u, v, _k in sec:
            r = c + u * w if north else 2 * MID_R - (c + u * w)
            ring.append(P(x, r, v * h))
        rings.append(ring)
    rings.append([P(X1, R_OUT(X1) if north else 2 * MID_R - R_OUT(X1), 0.0)])
    kinds = [k for _u, _v, k in sec]
    mat_of = {"s": K["spine"], "g": K["strut"], "b": K["bevel"]}

    def mat(b, i):
        a, bb = kinds[i], kinds[(i + 1) % len(kinds)]
        if "g" in (a, bb) and a == bb:
            return K["strut"]
        return mat_of["b"] if (a == "b" and bb == "b") else K["spine"]
    loft(bm, rings, mat, cap0=True, cap1=False)


def build_plates(bm, north):
    """Chamfered armour plates proud on the claw spine (u -0.80 .. -0.10), split at x 10.2."""
    sec = claw_section(False)
    us, vs = [p[0] for p in sec[:6]], [p[1] for p in sec[:6]]
    vtop = pchip(us, vs)
    for xa, xb in ((4.3, 10.05), (10.35, 15.6)):
        n = max(3, int((xb - xa) / 0.5))
        rings = []
        for k in range(n + 1):
            x = xa + (xb - xa) * k / n
            c, w, h = claw_dims(x)
            e = 0.0 if 0 < k < n else 0.12          # chamfered plate ends
            ua, ub = -0.80 + e / max(w, 0.1), -0.10 - e / max(w, 0.1)
            ring = []
            prof = [(ua, -0.12, 0.0), (ua, 0.06, 0.0), (ua + 0.10 / w, 0.17, 1), (ub - 0.10 / w, 0.17, 1),
                    (ub, 0.06, 0.0), (ub, -0.12, 0.0)]
            for u, dz, _t in prof:
                r = c + u * w if north else 2 * MID_R - (c + u * w)
                z = vtop(max(-1.0, min(GROOVE[0], u))) * h + dz - (0.1 if e and dz > 0.1 else 0.0)
                ring.append(P(x, r, z))
            rings.append(ring)
        loft(bm, rings, lambda b, i: K["plate"])


def build_louvres(bm, north):
    """A louvred vent panel on each claw's outer flank near the root (seen from the side and, on
    the south claw, by the tilted game camera): a dark recessed frame with four slats."""
    for x0 in (6.4, 7.3, 8.2, 9.1):
        x1 = x0 + 0.6
        c, w, h = claw_dims(x0 + 0.3)
        r_out = c - w if north else 2 * MID_R - (c - w)
        sgn = -1 if north else 1                 # outward in r
        for (za, zb, d, m) in ((-0.32 * h, 0.36 * h, -0.01, "bore"), (-0.12 * h, 0.2 * h, 0.05, "spine")):
            ra, rb = r_out + sgn * (-0.25), r_out + sgn * d
            xa, xb = (x0, x1) if m == "bore" else (x0 + 0.12, x1 - 0.12)
            pts = [(xa, ra, za), (xb, ra, za), (xb, rb, za), (xa, rb, za),
                   (xa, ra, zb), (xb, ra, zb), (xb, rb, zb), (xa, rb, zb)]
            vs = [bm.verts.new(P(*p)) for p in pts]
            for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                bm.faces.new([vs[i] for i in f]).material_index = K[m]


# --- strut / spine ---------------------------------------------------------------------------
R_TOP = [8.0, 9.0, 10.0, 10.8, 11.6, 12.2, 13.5]
XR_TOP = [10.5, 10.1, 9.2, 8.5, 6.6, 5.55, 5.4]
XL_TOP = [2.0, 2.9, 3.25, 3.4, 3.15, 3.1, 3.1]


def mirror_fn(rs, vals):
    rr = rs + [2 * MID_R - r for r in reversed(rs[:-1])]
    vv = vals + list(reversed(vals[:-1]))
    return pchip(rr, vv), rr[0], rr[-1]


XR, RA, RB = mirror_fn(R_TOP, XR_TOP)
XL, _, _ = mirror_fn(R_TOP, XL_TOP)
BANDS = (11.85, 15.15)


def strut_hz(r):
    d = abs(r - MID_R)
    return 1.25 + 0.3 * max(0.0, (d - 3.0) / 2.5) ** 2


def build_strut(bm, detail):
    rs = []
    r = RA
    while r <= RB + 1e-6:
        rs.append(round(r, 4))
        r += 0.5
    if detail:
        for b in BANDS:
            rs += [b - 0.22, b - 0.12, b + 0.12, b + 0.22]
    rs = sorted(set(rs))
    rings = []
    for r in rs:
        xl, xr, hz = XL(r), XR(r), strut_hz(r)
        s = 1.0
        if detail and any(abs(r - b) < 0.15 for b in BANDS):
            s = 0.9
        xc, hw = (xl + xr) / 2, (xr - xl) / 2
        hw2, hz2 = hw - (1 - s) * 0.8, hz * s
        ring = []
        for j in range(12):
            a = 2 * math.pi * j / 12
            ca, sa = math.cos(a), math.sin(a)
            # superellipse (n 3): a rounded box that still catches a sheen line along its crown
            ring.append(P(xc + hw2 * math.copysign(abs(ca) ** (2 / 3), ca), r,
                          hz2 * math.copysign(abs(sa) ** (2 / 3), sa)))
        rings.append(ring)
    post = [abs(r - MID_R) < 3.0 for r in rs]
    loft(bm, rings, lambda b, i: K["strut"] if (post[b] and post[b + 1]) else K["spine"])


# --- nozzles ---------------------------------------------------------------------------------
def ring_pts(x, rc, rad, n=14, zs=1.0):
    return [P(x, rc + rad * math.cos(2 * math.pi * k / n), rad * zs * math.sin(2 * math.pi * k / n))
            for k in range(n)]


def build_torch(bm, detail):
    """The emitter on the strut's nose face, firing +x at row 13.5: a dark finned housing (the
    sprite's dark columns 5-6) with a lipped nozzle and a dark bore."""
    rc = MID_R
    st = [(4.5, 1.55), (4.75, 1.78), (5.0, 1.82)]
    if detail:     # cooling fins: shallow rings round the housing
        st += [(5.2, 1.82), (5.25, 1.66), (5.45, 1.66), (5.5, 1.82), (5.7, 1.82), (5.75, 1.66), (5.95, 1.66),
               (6.0, 1.82)]
    st += [(6.25, 1.8), (6.45, 1.55), (6.55, 1.2), (6.8, 1.12), (6.95, 1.0)]
    rings = [ring_pts(x, rc, rad, n=12) for x, rad in st]
    if detail:
        rings += [ring_pts(6.85, rc, 0.7, n=12), ring_pts(6.2, rc, 0.55, n=12)]
    nb = len(st) - 1
    loft(bm, rings, lambda b, i: K["nozzle"] if b < nb + 1 else K["bore"], cap0=True, cap1=True)


def build_engine(bm, detail):
    """Bell nozzle on the strut's tail face, opening -x."""
    rc = MID_R
    st = [(3.4, 1.0), (2.9, 1.0), (2.75, 1.05), (2.2, 1.28), (2.0, 1.32)]
    rings = [ring_pts(x, rc, rad) for x, rad in st]
    if detail:
        rings += [ring_pts(2.05, rc, 1.12), ring_pts(2.7, rc, 0.7)]
    mats = [K["nozzle"]] * (len(st) - 1) + [K["nozzle"], K["bore"], K["bore"]]
    loft(bm, rings, lambda b, i: mats[b] if b < len(mats) else K["bore"])


# --- flames ----------------------------------------------------------------------------------
JETS = {
    10: dict(
        x=[6.0, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 17.0, 18.5, 19.5, 20.3],
        top=[13.4, 13.0, 12.4, 11.9, 11.3, 11.3, 11.9, 12.0, 12.1, 12.5, 13.0, 13.0, 13.05, 13.3, 13.9],
        bot=[13.9, 14.0, 14.1, 14.8, 15.0, 15.2, 15.8, 15.9, 15.8, 15.0, 15.0, 15.0, 14.9, 14.75, 14.2],
        mantle=(6.2, 16.6, 0.84, 0.1), core=(7.0, 13.6, 0.56, 0.16), lo="redlo", mid="orange", hot="yellow",
        tail=dict(x=[2.3, 2.0, 1.4, 0.8, 0.2, -0.05], hw=[0.9, 1.35, 1.35, 1.0, 0.55, 0.0], rc=13.55,
                  mat="redlo", inner="orange"),
    ),
    48: dict(
        x=[6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 12.6, 13.2, 14.0, 15.0, 16.5, 17.5, 18.5, 19.2],
        top=[13.4, 13.0, 12.9, 12.3, 11.95, 11.95, 11.5, 11.3, 11.3, 11.6, 12.0, 12.2, 12.8, 13.0, 13.45],
        bot=[13.9, 14.0, 14.3, 14.9, 15.4, 15.8, 15.5, 14.9, 14.15, 14.0, 14.0, 14.0, 13.95, 13.9, 13.6],
        mantle=(8.0, 17.2, 0.8, 0.04), core=(9.6, 15.0, 0.56, 0.02), lo="red", mid="amber", hot="yellow",
        tail=dict(x=[2.3, 2.0, 1.7, 1.2, 0.5, -0.05], hw=[0.9, 1.25, 0.62, 0.5, 0.45, 0.0], rc=13.5,
                  mat="amber", inner="gold"),
    ),
}


def build_flame(bm, spec):
    top, bot = pchip(spec["x"], spec["top"]), pchip(spec["x"], spec["bot"])
    xa, xb = spec["x"][0], spec["x"][-1]
    n_sides = 10

    def layer(x0, x1, scale, zk, mat, lift=0.0):
        n = max(5, int((x1 - x0) / 0.55))
        rings = []
        for k in range(1, n):
            x = x0 + (x1 - x0) * k / n
            t = (x - x0) / (x1 - x0)
            env = math.sin(math.pi * t) ** 0.6 if scale < 1 else 1.0
            c = (top(x) + bot(x)) / 2 - lift * (bot(x) - top(x))
            w = (bot(x) - top(x)) / 2 * scale * env
            ring = []
            for j in range(n_sides):
                a = 2 * math.pi * j / n_sides
                wob = 1.0 + 0.07 * math.cos(3 * a + x * 2.1) if scale == 1 else 1.0
                ring.append(P(x, c + w * wob * math.cos(a), w * zk * math.sin(a)))
            rings.append(ring)
        rings = [[P(x0, (top(x0) + bot(x0)) / 2, 0.0)]] + rings + [[P(x1, (top(x1) + bot(x1)) / 2, 0.0)]]
        loft(bm, rings, lambda b, i: K[mat], cap0=False, cap1=False)

    layer(xa, xb, 1.0, 0.58, "red")
    # the lower edge reads darker in the sprite (116/117): a low lip of the plume in the darker red
    layer(xa + 1.5, xb - 1.0, 0.86, 0.42, spec["lo"], lift=-0.1)
    m0, m1, ms, ml = spec["mantle"]
    layer(m0, m1, ms, 1.15, spec["mid"], lift=ml)
    c0, c1, cs, cl = spec["core"]
    layer(c0, c1, cs, 2.3, spec["hot"], lift=cl)
    # the engine's exhaust out of the tail (left)
    t = spec["tail"]
    xs, hws = t["x"], t["hw"]
    hw = pchip(list(reversed(xs)), list(reversed(hws)))
    rings = []
    for x in xs[:-1]:
        w = hw(x)
        rings.append(ring_pts(x, t["rc"], w, n=12, zs=0.8))
    rings.append([P(xs[-1], t["rc"], 0.0)])
    loft(bm, rings, lambda b, i: K[t["mat"]], cap0=True, cap1=False)
    rings = [ring_pts(x, t["rc"], hw(x) * 0.55, n=10, zs=1.6) for x in (2.25, 2.0, 1.6)] + [[P(1.0, t["rc"], 0.0)]]
    loft(bm, rings, lambda b, i: K[t["inner"]], cap0=True, cap1=False)


# ---------------------------------------------------------------------------------------------
def spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def build():
    import bmesh
    import bpy
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import common

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = [spec(common.palette_material(sprite, idx, f"{NAME}-{key}", metallic=m, roughness=r,
                                         emission_strength=e), sp)
            for key, idx, m, r, e, sp in MATS]

    def body(detail):
        bm = bmesh.new()
        build_claw(bm, True, detail)
        build_claw(bm, False, detail)
        build_strut(bm, detail)
        build_torch(bm, detail)
        build_engine(bm, detail)
        if detail:
            build_plates(bm, True)
            build_plates(bm, False)
            build_louvres(bm, True)
            build_louvres(bm, False)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm

    def obj_from(bm, name, smooth=True, split=35):
        for f in bm.faces:
            f.smooth = smooth
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(m)
        o = bpy.data.objects.new(name, mesh)
        coll.objects.link(o)
        if split:
            es = o.modifiers.new("hard", "EDGE_SPLIT")
            es.split_angle = math.radians(split)
            es.use_edge_sharp = False
        return o

    obj = obj_from(body(True), NAME)
    parts = [obj]
    tris = {}
    for frame, sp in JETS.items():
        bm = bmesh.new()
        build_flame(bm, sp)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        jet = obj_from(bm, f"{NAME}-jet-{frame}", split=0)
        parts.append(common.frame_part(jet, [frame]))
    bpy.context.view_layer.update()

    seal = obj_from(body(False), NAME + "_seal", split=0)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.006, faces=2000, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    for p in parts:
        p.data.calc_loop_triangles()
        tris[p.name] = len(p.data.loop_triangles)
    common.export_sprite_model(WT, parts + [shell], f"enemies/{NAME}", sprite["sprites"])
    print("MANIFEST", json.dumps({NAME: {"frames": [10, 48], "tris": tris,
                                         "shell_faces": len(shell.data.polygons)}}))


if __name__ == "__main__":
    build()
