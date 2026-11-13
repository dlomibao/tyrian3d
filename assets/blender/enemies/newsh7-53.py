"""Blue crystal (newsh7.shp frames 53, 91, 129), an emerald-cut gem in a steel ferrule.

What it is: a cut blue gem lying flat, its north end held in a polished steel cap. The sprite is a
pixel octagon (45 degree corners on all four sides), and its pale lines are the facet edges of a
step cut: the table's outline (the left line at column 5, the right one at column 17, the bottom
line at row 20 and the two chamfered corners), corner joins running out to the girdle (column 15
under the table, row 17 on the right), and a transverse ridge at row 12 that runs across the whole
crown. North of the ridge the crown slopes down into the cap, which is why the sprite draws that
band darker (rows 8-11). So the gem is built as a faceted solid: girdle octagon, two crown steps,
a bevelled table edge (the pale lines, polished), a flat ridge band and a step-cut pavilion to a
short keel underneath (closed, plain). Flat facets, no beads: the white is the polished bevel's
colour, the sprite's rim glints at columns 3 and 20 are sheen and are not painted.

The cap (rows 3-6) is a ferrule lying along the gem's axis: an elliptical section lofted along Y
(pchip stations matched to the sprite rows), a domed nose with a chamfered end face, a machined
groove and a raised lip collar where it grips the gem. Satin steel, palette 56 (the cap's median;
the light band and the dark right side are its drawn lighting).

Frames: one model. The blues step one palette index darker on 91 and two on 129, the pale lines
shimmer 142 -> 140 -> 159 (per-region medians of each frame), via palette_material frames=.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh7-53.py
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]  # repo root (assets/blender/enemies/<name>.py)
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

NAME = "newsh7-53"
PX = 1 / 12
W, H = 24, 28


def P(u, v, z):
    """Sprite pixel-edge coordinates (column u, row v) and height z in px -> world."""
    return ((u - W / 2) * PX, (H / 2 - v) * PX, z * PX)


def pchip(xs, ys):
    """Monotone cubic interpolation (copy of usp_talon.pchip)."""
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
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def offset_poly(pts, d):
    """Offset a closed polygon (clockwise on screen = counter-clockwise in y-up... any winding) by d
    px outward (d > 0) or inward (d < 0), keeping the vertex count (edge lines moved, re-intersected)."""
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ex_, ey_ = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ex_, ey_)
        nx, ny = ey_ / L, -ex_ / L
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (mx - cx) * nx + (my - cy) * ny < 0:
            nx, ny = -nx, -ny
        lines.append(((a[0] + nx * d, a[1] + ny * d), (ex_ / L, ey_ / L), (nx, ny)))
    out = []
    for i in range(n):
        (p1, d1, n1), (p2, d2, n2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-6:  # collinear edges: move the vertex along the normal
            out.append((pts[i][0] + n2[0] * d, pts[i][1] + n2[1] * d))
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def lerp2(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


# --- The gem's plan (pixel-edge coordinates) ------------------------------------------------------
# The girdle is the sprite's inner mask (inside its ink ring): an octagon whose 45 degree sides cut
# the pixel staircases through their mid-points (x+y=12.4, x-y=11.6, x+y=40.6, y-x=16.6). Every loop
# has the same 12 vertices: the octagon's corners plus a pair at the ridge (rows 12.05 / 12.95) on
# each side. The top edge (row 6.8) runs under the cap's lip.
RN, RS = 12.05, 12.95
GIRDLE = [(5.6, 6.8), (18.4, 6.8), (21.0, 9.4), (21.0, RN), (21.0, RS), (21.0, 19.6),
          (15.6, 25.0), (8.4, 25.0), (3.0, 19.6), (3.0, RS), (3.0, RN), (3.0, 9.4)]
# The table's outline: the centre of the sprite's pale lines (left line column 5, right column 17,
# bottom row 20, chamfered corners down to (9.6, 20.4) and (15.4, 20.4)).
TABLE = [(6.3, 6.8), (16.8, 6.8), (17.5, 8.6), (17.5, RN), (17.5, RS), (17.5, 17.4),
         (15.4, 20.4), (9.6, 20.4), (5.5, 16.3), (5.5, RS), (5.5, RN), (5.5, 8.6)]
LINE = 0.5                    # half width of the bevelled table edge (the pale line), px
ZG_TOP, ZG_BOT = 2.9, 2.2      # girdle band
Z_S1, Z_S2, Z_TAB = 5.0, 6.35, 7.45  # crown steps and the table at the ridge
SLOPE_N, SLOPE_S = 0.30, 0.11  # the crown falls this much per px north / south of the ridge band


def drop(y):
    return SLOPE_N * max(0.0, RN - y) + SLOPE_S * max(0.0, y - RS)


def build(sprite):
    coll = common.reset_collection(NAME)

    def gem(i, frames, rough=0.22, emit=0.35, spec=0.2, tag="gem"):
        m = common.palette_material(sprite, i, f"{NAME}-{tag}", metallic=0.0, roughness=rough,
                                    emission_strength=emit, frames=frames)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:  # D176: a polished dielectric's F0
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    mats = [
        gem(156, {91: 155, 129: 154}, tag="table"),        # 0 table, south of the ridge
        gem(152, {91: 151, 129: 150}, emit=0.0, tag="tablen"),       # 1 table north of the ridge (the dark band)
        gem(155, {91: 154, 129: 153}, tag="step"),         # 2 crown steps, sides and north
        gem(153, {129: 152}, tag="stepb"),                 # 3 crown steps, south
        gem(142, {91: 140, 129: 159}, rough=0.1, emit=1.0, tag="line"),  # 4 bevelled table edge
        gem(159, {91: 158, 129: 157}, rough=0.1, emit=0.8, tag="ridge"),           # 5 ridge band on the table
        gem(150, {91: 149, 129: 148}, rough=0.15, emit=0.1, tag="pav"),              # 6 girdle and pavilion
    ]
    TAB, TABN, STEP, STEPB, LINEM, RIDGE, PAV = range(7)

    bm = bmesh.new()
    t_out = offset_poly(TABLE, LINE)
    t_in = offset_poly(TABLE, -LINE)
    s1a = [lerp2(g, t, 0.24) for g, t in zip(GIRDLE, t_out)]
    s1b = [lerp2(g, t, 0.37) for g, t in zip(GIRDLE, t_out)]
    s2 = [lerp2(g, t, 0.68) for g, t in zip(GIRDLE, t_out)]
    keel = [(12 + (u - 12) * 0.16, min(max(v, 11.5), 20.5)) for u, v in GIRDLE]
    p1 = [lerp2(g, k, 0.5) for g, k in zip(GIRDLE, keel)]

    # Corner joins drawn pale in the sprite (column 15 under the table, row 17 on the right): those
    # loop vertices are doubled, JOIN px apart along the loop, and the narrow strip between the two
    # copies is a polished bevel down the facet edge, girdle to table.
    JOIN = 0.45
    DOUBLE = {5, 6}
    entries = []  # (base vertex, side): side -1 / +1 for the doubled copies, 0 otherwise
    for i in range(len(GIRDLE)):
        entries += [(i, -1), (i, 1)] if i in DOUBLE else [(i, 0)]
    m_ = len(entries)

    def expand(pts):
        out = []
        n0 = len(pts)
        for i, s in entries:
            p = pts[i]
            if s == 0:
                out.append(p)
                continue
            q = pts[(i + s) % n0]
            out.append(lerp2(p, q, JOIN / math.dist(p, q)))
        return out

    def loop(pts, z, share):
        return [bm.verts.new(P(u, v, z - share * drop(v))) for u, v in expand(pts)]

    L_keel = [bm.verts.new(P(u, v, -2.2)) for u, v in expand(keel)]
    L_p1 = [bm.verts.new(P(u, v, 0.4)) for u, v in expand(p1)]
    L_gb = [bm.verts.new(P(u, v, ZG_BOT)) for u, v in expand(GIRDLE)]
    L_gt = [bm.verts.new(P(u, v, ZG_TOP)) for u, v in expand(GIRDLE)]
    L_s1a = loop(s1a, Z_S1 - 0.35, 0.3)
    L_s1b = loop(s1b, Z_S1 + 0.3, 0.42)
    L_s2 = loop(s2, Z_S2, 0.72)
    L_to = loop(t_out, Z_TAB - 0.3, 1.0)
    L_ti = loop(t_in, Z_TAB, 1.0)

    def band(a, b, matf, joins=True):
        for k in range(m_):
            j = (k + 1) % m_
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            i, i2 = entries[k][0], entries[j][0]
            f.material_index = LINEM if (joins and i == i2) else matf(i)

    south = {5, 6, 7}          # the SE, S and SW sides (edges 5-6, 6-7, 7-8)
    ridge = {3, 9}             # the ridge band's edges on the right and left
    # The first crown step's edge is drawn pale on the right (column 20), the SE diagonal and the
    # left above the ridge (column 3, rows 10-12): a polished bevel there, a plain step elsewhere.
    lit_step = {2, 3, 4, 5, 9, 10}

    def step_mat(i):
        if i in ridge:
            return LINEM
        return STEPB if i in south else STEP

    band(L_keel, L_p1, lambda i: PAV, joins=False)
    band(L_p1, L_gb, lambda i: PAV, joins=False)
    band(L_gb, L_gt, lambda i: PAV, joins=False)
    band(L_gt, L_s1a, step_mat)
    band(L_s1a, L_s1b, lambda i: LINEM if i in lit_step else step_mat(i))
    band(L_s1b, L_s2, step_mat)
    band(L_s2, L_to, step_mat)
    band(L_to, L_ti, lambda i: LINEM)
    # The table: north of the ridge, the ridge band, south of it (each planar). Walk the loop from
    # the face's first base vertex so the polygon stays in order across the wrap.
    for base, m in (([10, 11, 0, 1, 2, 3], TABN), ([3, 4, 9, 10], RIDGE), ([4, 5, 6, 7, 8, 9], TAB)):
        if m == RIDGE:
            vs = [L_ti[k] for k, (i, s) in enumerate(entries) if i in base]
        else:
            start = next(k for k, (i, s) in enumerate(entries) if i == base[0])
            vs = []
            for d in range(m_):
                k = (start + d) % m_
                if entries[k][0] in base:
                    vs.append(L_ti[k])
        bm.faces.new(vs).material_index = m
    # Keel: close the bottom.
    c = bm.verts.new(P(12.0, 16.0, -2.2))
    for k in range(m_):
        j = (k + 1) % m_
        bm.faces.new((L_keel[j], L_keel[k], c)).material_index = PAV
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    gem_obj = common.mesh_object(f"{NAME}_gem", bm, mats, coll, smooth=False)

    # --- The steel cap: a ferrule along Y over the gem's north end. --------------------------------
    cap_mats = [common.palette_material(sprite, 57, NAME, metallic=0.35, roughness=0.3),
                common.palette_material(sprite, 52, NAME, metallic=0.7, roughness=0.45)]
    STEEL, GROOVE = 0, 1
    # Half width (px) per station, from the sprite's rows: row 3 x 8..16, rows 4-5 x 7..17, row 6
    # x 6..18; the lip at rows 6.7-7.5 sits over the gem's top edge.
    wf = pchip([3.0, 3.35, 3.9, 4.6, 5.4, 6.1, 6.7], [3.35, 4.05, 4.65, 4.95, 5.2, 5.75, 6.15])
    ZC, KZ = 4.3, 0.9  # section centre height and height/width ratio
    stations = []  # (row, half width, material of the band that starts here)
    stations.append((2.86, 2.2, STEEL))  # chamfered end face
    stations.append((2.95, 3.0, STEEL))
    for v in (3.1, 3.3, 3.55, 3.8, 4.05, 4.3):
        stations.append((v, wf(v), STEEL))
    # machined groove
    stations += [(4.5, wf(4.5), STEEL), (4.58, wf(4.58) - 0.3, GROOVE), (4.82, wf(4.82) - 0.3, STEEL),
                 (4.9, wf(4.9), STEEL)]
    for v in (5.2, 5.6, 6.0, 6.45):
        stations.append((v, wf(v), STEEL))
    # lip collar: a step out, flat band, chamfer back, tucked into the gem
    stations += [(6.6, wf(6.6), STEEL), (6.68, wf(6.68) + 0.28, STEEL), (7.35, 6.45, STEEL),
                 (7.5, 6.2, STEEL), (8.4, 5.6, STEEL)]
    sides = 40
    bm = bmesh.new()
    rings = []
    for v, w, m in stations:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(P(12 + w * math.cos(a), v, ZC + KZ * w * math.sin(a))))
        rings.append((ring, m))
    for (r0, m0), (r1, _) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = m0
    # Nose: the end face, a shallow dome inset.
    nose = bm.verts.new(P(12, 2.78, ZC))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[0][0][j], rings[0][0][k], nose)).material_index = STEEL
    tail = bm.verts.new(P(12, 8.6, ZC))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[-1][0][k], rings[-1][0][j], tail)).material_index = STEEL
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cap = common.mesh_object(f"{NAME}_cap", bm, cap_mats, coll, smooth=True)
    # Hard edges at the groove and the collar's steps (auto-smooth by angle).
    for o in (cap,):
        mod = o.modifiers.new("ssa", "EDGE_SPLIT")
        mod.split_angle = math.radians(40)
    return coll, [gem_obj, cap]


def sink_shell(shell, model, margin, reach):
    """Copied from newshv-10.py (D185): drop every shell vertex to `margin` under the lowest model top
    within `reach` (seen from above), so the outline's ink stays on the silhouette."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll, parts = build(sprite)
    # D90/D118: the shell from a sealed copy of the whole model (nothing is culled here).
    sealed = [p.copy() for p in parts]
    for s, p in zip(sealed, parts):
        s.data = p.data.copy()
        coll.objects.link(s)
        for m in list(s.modifiers):
            s.modifiers.remove(m)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(o in sealed)
    bpy.context.view_layer.objects.active = sealed[0]
    bpy.ops.object.join()
    joined = sealed[0]
    joined.name = f"{NAME}_sealed"
    shell = common.outline_shell(joined, coll, voxel=0.02, faces=1600, inside=0.004)
    sink_shell(shell, joined, 0.5 * PX, 1.2 * PX)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(joined, do_unlink=True)
    objs = parts + [shell]
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    tris = 0
    for o in parts:
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    print(f"exported: model triangles {tris}, shell faces {len(shell.data.polygons)}")


if __name__ == "__main__":
    main()
