"""Fire star (newsh5.shp frames 278, 280, 282): a faceted molten crystal star.

What it is: a small, short-lived glowing hazard. In BRAINIAC the brain launches it (type 644, homing)
and type 541 rises fast up the ground layer; in SQUADRON type 726 hovers over the rows of turrets and
fires. So it floats: a free crystal, closed all round, not a ground object.

Reading the sprite (frame 278, 24x28): the inner mask (sprite_mask.py, the ink ring left to the
game's outline) is exactly a square (pixel centres 6..18) united with a diamond |dx| + |dy| <= 10
about pixel (12, 12): a four-pointed star whose points stand out of a square body. The points'
ridges run bright (122-127) into a white-hot centre; the body is four blocky quarter lobes (median
116-118) parted by darker valleys along the axes (113-115), each lobe with a hot spot on its outer
corner (123-124, on every lobe whatever the light, so glow, not sheen). The frames 280/282 shrink it:
square half 5.5 / 4.5 px, points 8.5 / 7.5 px (278: 6.5 / 10.5).

Built as: four long crystal blades along the axes (a chamfered, glowing ridge strip on top, two
facets each side, a keel below; the plan exactly the diamond's arms), four chunky faceted lobes in
the square's quarters (a chamfered rounded block, its top a low off-centre pyramid of facets leaning
to the outer corner, the corner facets glowing hot), and an octagonal white-hot core spire where the
blades meet. Flat-shaded facets (a crystal), glow surfaces metallic 1 and rough (D126, D173). The
underside is the same parts closed by their keels and lower chamfers (no detail).

One model per frame (newsh5-278, -f2, -f3). Exports public/models/enemies/newsh5-278[-f2|-f3].glb and the spriteModels JSONs (no review output).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh5-278.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newsh5-278"
PX = 1 / 12
W, H = 24, 28
CX, CY = 12.5, 12.5  # star centre, in pixel edges (the middle of pixel (12, 12))

# frame: (point reach R, square half q), px from the centre, fitted to the inner mask.
SIZES = {278: (10.5, 6.5), 280: (8.5, 5.5), 282: (7.5, 4.5)}
TAGS = {278: NAME, 280: f"{NAME}-f2", 282: f"{NAME}-f3"}


def pchip(xs, ys, x):
    """Monotone cubic (Fritsch-Carlson) through (xs, ys) at x."""
    n = len(xs)
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
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
    i = max(k for k in range(n - 1) if xs[k] <= x)
    t = (x - xs[i]) / h[i]
    h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
    h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]


def P(x, y, z):
    """Star-local px (x right, y up, z up) to Blender units."""
    return ((CX + x - W / 2) * PX, (H / 2 - CY + y) * PX, z * PX)


# Ridge height along a blade, by t = d / R (px at frame 278; scaled with the star).
RIDGE_T = [0.0, 0.2, 0.45, 0.62, 0.8, 0.93, 1.0]
RIDGE_Z = [5.0, 4.45, 3.55, 2.95, 1.95, 1.0, 0.4]


def blade(bm, R, q, s, angle, zone):
    """One crystal point along `angle`: a 7-vertex section (keel, base edges, shoulders, ridge strip)
    lofted from inside the core to the tip; the plan half width is the diamond's, R - d.
    `zone(part, t)` gives a face's material by part ("ridge", "blade", "flank", "under") and its
    place t = d / R along the blade: the glow cools from the core out to the tip."""
    ca, sa = math.cos(angle), math.sin(angle)
    ds = [0.6, 1.4, 2.2, 3.0]
    d = 3.0
    while d < R - 0.9:
        d += 0.55
        ds.append(min(d, R - 0.9))
    ds += [R - 0.55, R - 0.25]
    rings = []
    for d in ds:
        t = d / R
        zt = pchip(RIDGE_T, RIDGE_Z, t) * s
        wb = max(0.05, min(R - d, R - q + 0.35))  # plan half width (the diamond's arm)
        zb = 0.55 * s * min(1.0, (R - d) / 1.5 + 0.35)  # base edge height
        rw = max(0.1, s * min(0.42 + 0.35 * max(0.0, 1 - t / 0.5), (R - d) / 3.0 * 0.42 + 0.13))  # ridge strip half width
        ws = max(rw + 0.12, 0.5 * wb)
        zs = zb + (zt - zb) * 0.68
        sec = [(0.0, 0.0), (wb, zb), (ws, zs), (rw, zt), (-rw, zt), (-ws, zs), (-wb, zb)]
        ring = []
        for w, z in sec:
            x, y = d * ca - w * sa, d * sa + w * ca
            ring.append(bm.verts.new(P(x, y, z)))
        rings.append(ring)
    tip = bm.verts.new(P(R * ca, R * sa, 0.32 * s))
    part = {0: "under", 1: "flank", 2: "blade", 3: "ridge", 4: "blade", 5: "flank", 6: "under"}
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        t = (ds[i] + ds[i + 1]) / 2 / R
        for j in range(7):
            k = (j + 1) % 7
            bm.faces.new((r0[j], r0[k], r1[k], r1[j])).material_index = zone(part[j], t)
    last = rings[-1]
    for j in range(7):
        k = (j + 1) % 7
        bm.faces.new((last[j], last[k], tip)).material_index = zone(part[j] if j != 3 else "blade", 1.0)
    bm.faces.new(list(reversed(rings[0]))).material_index = zone("under", 0.0)


def rrect(cx, cy, hx, hy, radii, m=3):
    """Rounded rectangle loop (CCW), a fixed count of points (4 * (m + 1)): corners in the order
    (+,+), (-,+), (-,-), (+,-), each with its own radius."""
    pts = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        r = max(0.04, min(radii[k], hx - 0.02, hy - 0.02))
        ox, oy = cx + sx * (hx - r), cy + sy * (hy - r)
        a0 = k * math.pi / 2
        for i in range(m + 1):
            a = a0 + (math.pi / 2) * i / m
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def lobe(bm, q, s, sx, sy, mats):
    """One quarter lobe: a chamfered rounded block from the axis valley (g) to the square's edge (q),
    its top a low pyramid of facets with its peak toward the outer corner; the facets that face that
    corner glow hot."""
    LOBE, HOT, UNDER = mats
    g = 0.9
    cx, cy = sx * (g + q) / 2, sy * (g + q) / 2
    hx = hy = (q - g) / 2
    # corner radii in rrect order (+,+), (-,+), (-,-), (+,-): the outer corner is (sx, sy)
    order = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    radii = []
    for cxs, cys in order:
        if (cxs, cys) == (sx, sy):
            radii.append(0.75)  # outer corner of the square, nearly crisp
        elif (cxs, cys) == (-sx, -sy):
            radii.append(1.1)  # inner corner, under the core
        else:
            radii.append(0.55)
    # (inset px, z px at 278)
    levels = [(0.55, 0.0), (0.0, 0.75), (0.0, 1.95), (0.22, 2.35), (0.85, 2.62)]
    loops = []
    for inset, z in levels:
        pts = rrect(cx, cy, hx - inset, hy - inset, [max(0.04, r - inset * 0.6) for r in radii])
        loops.append([bm.verts.new(P(x, y, z * s)) for x, y in pts])
    n = len(loops[0])
    band_mat = [UNDER, LOBE, LOBE, LOBE]
    outer = (sx / math.sqrt(2), sy / math.sqrt(2))

    def facing(vs):
        mx = sum(v[0] for v in vs) / len(vs) - cx
        my = sum(v[1] for v in vs) / len(vs) - cy
        ln = math.hypot(mx, my) or 1.0
        return (mx * outer[0] + my * outer[1]) / ln

    pts2d = rrect(cx, cy, hx, hy, radii)
    for b in range(len(loops) - 1):
        a0, a1 = loops[b], loops[b + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a0[i], a0[j], a1[j], a1[i]))
            mat = band_mat[b]
            if b >= 2 and facing([pts2d[i], pts2d[j]]) > 0.85:
                mat = HOT  # the chamfer facet on the outer corner
            f.material_index = mat
    peak = bm.verts.new(P(cx + sx * 0.3 * hx, cy + sy * 0.3 * hy, 2.95 * s))
    top = loops[-1]
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((top[i], top[j], peak))
        f.material_index = HOT if facing([pts2d[i], pts2d[j]]) > 0.72 else LOBE
    bm.faces.new(list(reversed(loops[0]))).material_index = UNDER


def core(bm, s, mats):
    """A small octagonal spire where the blades meet: vertices on the axes, so each blade's ridge
    runs up one of its edges; yellow-hot facets under a white-hot tip."""
    BASE, HOTC, HOTTER, WHITE, UNDER = mats
    rings = [(1.2, 0.0), (1.95, 2.9), (1.8, 4.35), (1.05, 5.3), (0.42, 5.75)]
    loops = []
    for r, z in rings:
        loops.append([bm.verts.new(P(r * s * math.cos(k * math.pi / 4), r * s * math.sin(k * math.pi / 4),
                                     z * s)) for k in range(8)])
    mats_b = [BASE, HOTC, HOTTER, WHITE]
    for b in range(len(loops) - 1):
        for k in range(8):
            j = (k + 1) % 8
            bm.faces.new((loops[b][k], loops[b][j], loops[b + 1][j], loops[b + 1][k])).material_index = mats_b[b]
    apex = bm.verts.new(P(0, 0, 6.0 * s))
    for k in range(8):
        j = (k + 1) % 8
        bm.faces.new((loops[-1][k], loops[-1][j], apex)).material_index = WHITE
    bm.faces.new(list(reversed(loops[0]))).material_index = UNDER


def L_frames(sprite, index):
    """sprite["sprites"] cut down to this model's frame."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f == index]
        if keep:
            out.append({**s, "frames": keep})
    return out


def build(index):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    tag = TAGS[index]
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(tag)
    R, q = SIZES[index]
    s = R / 10.5

    def pal(i, glow, rough, part=""):
        # `part` keeps one index used at two glow strengths as two materials (pal_<i>_<tag><part>).
        return common.palette_material(sprite, i, tag + part, metallic=1.0, roughness=rough, emission_strength=glow)

    # The glow cools from the core out: ridge strips 125 -> 120, facets 122 -> 117, in steps along t.
    RIDGE_STEPS = [(0.3, 125, 1.0), (0.5, 124, 0.95), (0.65, 123, 0.9), (0.8, 122, 0.8), (2.0, 120, 0.7)]
    BLADE_STEPS = [(0.3, 122, 0.7), (0.5, 121, 0.6), (0.7, 120, 0.5), (0.85, 119, 0.45), (2.0, 117, 0.35)]
    mats, ridge_ix, blade_ix = [], [], []
    for _, i, glow in RIDGE_STEPS:
        ridge_ix.append(len(mats))
        mats.append(pal(i, glow, 0.85, "-ridge"))
    for _, i, glow in BLADE_STEPS:
        blade_ix.append(len(mats))
        mats.append(pal(i, glow, 0.6))
    UNDER = len(mats)
    mats += [
        pal(115, 0.25, 0.7),   # keels, undersides, the tips' lower flanks
        pal(118, 0.6, 0.6),    # lobes
        pal(123, 0.9, 0.85),   # lobe hot corners, core band
        pal(126, 1.1, 0.9),    # white-hot tip
    ]
    LOBE, HOT, WHITE = UNDER + 1, UNDER + 2, UNDER + 3

    def zone(part, t):
        if part == "ridge":
            return next(ix for (lim, _, _), ix in zip(RIDGE_STEPS, ridge_ix) if t < lim)
        if part == "blade":
            return next(ix for (lim, _, _), ix in zip(BLADE_STEPS, blade_ix) if t < lim)
        if part == "flank":
            return blade_ix[-1] if t < 0.85 else UNDER
        return UNDER

    bm = bmesh.new()
    for k in range(4):
        blade(bm, R, q, s, k * math.pi / 2, zone)
    for sx in (-1, 1):
        for sy in (-1, 1):
            lobe(bm, q, s, sx, sy, (LOBE, HOT, UNDER))
    core(bm, s, (blade_ix[0], HOT, ridge_ix[0], WHITE, UNDER))
    obj = common.mesh_object(tag, bm, mats, coll, smooth=False)
    # D51/D118/D189: the shell from a sealed copy (nothing is culled), every outer island kept.
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.006, faces=2400, inside=0.003, islands="outer")
    shell.name = f"{tag}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    assert len(shell.data.polygons) > 0, "empty outline shell"
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    common.export_sprite_model(WT, [obj, shell], f"enemies/{tag}", L_frames(sprite, index))
    print(f"{tag}: model triangles {tris}, shell faces {len(shell.data.polygons)}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    frames = [int(argv[argv.index("--only") + 1])] if "--only" in argv else list(SIZES)
    for f in frames:
        build(f)


if __name__ == "__main__":
    main()
