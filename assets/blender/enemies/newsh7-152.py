"""Small blue crystal (newsh7.shp frame 152, a 12x14 size-1 sprite), design A: a cut gem in a steel
ferrule, the small cousin of newsh7-53 (same build, same family look).

What it is: a cut blue gem lying flat, its north end held in a satin steel cap. The sprite is a
pixel octagon under a 6 px wide cap (rows 1-2). Its pale lines (palette 135-141) are the polished
bevel round the table: the table's sides at columns 2 and 9 (rows 3-8), and two 45 degree edges
that meet in a short flat at row 11 (columns 5-6), so the table is a shield with a pointed south
end. A transverse ridge at row 6 runs across the whole crown (pale 140 on the side facets, light
blue 158 across the table); north of it the crown falls toward the cap, which is why the sprite
draws the north table darker (median 152) than the south (155). The crown steps and girdle are the
sprite's outer blues (154), the pavilion underneath a plain closed cone to a short keel (151).
Flat facets, no beads; the sprite's ring is ink and its bright pixels are sheen.

The cap is a ferrule along the gem's axis: an elliptical section lofted along Y (pchip stations
matched to the sprite rows: full 6 px width on rows 1-2, rounded north corners), a chamfered domed
nose, a machined groove and a lip collar where it grips the gem. Satin steel, palette 57 (the
cap's median; the light band at columns 4-5 is its sheen).

One frame (152). Run: blender --background --python assets/blender/enemies/newsh7-152.py [-- --preview out.png]
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402

NAME = "newsh7-152"
PX = 1 / 12
W, H = 12, 14


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
    """Offset a closed polygon by d px outward (d > 0) or inward (d < 0), keeping the vertex count
    (edge lines moved and re-intersected; collinear neighbours move along the normal)."""
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
        if abs(den) < 1e-6:
            out.append((pts[i][0] + n2[0] * d, pts[i][1] + n2[1] * d))
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def lerp2(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


# --- The gem's plan (pixel-edge coordinates) ------------------------------------------------------
# The girdle is the sprite's inner mask (inside its ink ring): an octagon whose 45 degree corners
# cut the pixel staircases through their mid-points (x+y=5.5, y-x=-6.5 at the top, x-y=-9.5 and
# x+y=21.5 at the bottom). Every loop has the same 12 vertices: the corners plus a pair at the
# ridge (rows 6.1 / 6.9) on each side. The top edge (row 2.7) runs under the cap's lip.
RN, RS = 6.1, 6.9
GIRDLE = [(2.8, 2.7), (9.2, 2.7), (11.0, 4.5), (11.0, RN), (11.0, RS), (11.0, 10.5),
          (8.5, 13.0), (3.5, 13.0), (1.0, 10.5), (1.0, RS), (1.0, RN), (1.0, 4.5)]
# The table: the centre of the sprite's pale lines (columns 2 and 9, the 45 degree edges through
# (3,9) (4,10) (5,11) and their mirror, the flat at row 11 between columns 5 and 6).
TABLE = [(3.2, 3.0), (8.8, 3.0), (9.45, 3.9), (9.45, RN), (9.45, RS), (9.45, 8.75),
         (6.7, 11.5), (5.3, 11.5), (2.55, 8.75), (2.55, RS), (2.55, RN), (2.55, 3.9)]
LINE = 0.44                  # half width of the bevelled table edge (the pale line), px
ZG_TOP, ZG_BOT = 1.45, 1.0   # girdle band
Z_S1, Z_TAB = 2.35, 3.0      # crown step and the table at the ridge
SLOPE_N, SLOPE_S = 0.2, 0.06  # the crown falls this much per px north / south of the ridge band


def drop(y):
    return SLOPE_N * max(0.0, RN - y) + SLOPE_S * max(0.0, y - RS)


def build(sprite):
    coll = common.reset_collection(NAME)

    def gem(i, rough=0.22, emit=0.35, spec=0.2, tag="gem"):
        m = common.palette_material(sprite, i, f"{NAME}-{tag}", metallic=0.0, roughness=rough,
                                    emission_strength=emit)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:  # D176: a polished dielectric's F0
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    mats = [
        gem(155, tag="table"),                      # 0 table, south of the ridge
        gem(152, emit=0.0, tag="tablen"),           # 1 table north of the ridge (the darker band)
        gem(154, tag="step"),                       # 2 crown facets
        gem(140, rough=0.1, emit=1.0, tag="line"),  # 3 bevelled table edge, ridge edges
        gem(158, rough=0.1, emit=0.8, tag="ridge"),  # 4 ridge band across the table
        gem(151, rough=0.15, emit=0.1, tag="pav"),  # 5 girdle and pavilion
    ]
    TAB, TABN, STEP, LINEM, RIDGE, PAV = range(6)

    bm = bmesh.new()
    t_out = offset_poly(TABLE, LINE)
    t_in = offset_poly(TABLE, -LINE)
    s1 = [lerp2(g, t, 0.55) for g, t in zip(GIRDLE, t_out)]
    keel = [(6 + (u - 6) * 0.2, min(max(v, 6.0), 10.5)) for u, v in GIRDLE]
    p1 = [lerp2(g, k, 0.5) for g, k in zip(GIRDLE, keel)]
    n = len(GIRDLE)

    def loop(pts, z, share=0.0):
        return [bm.verts.new(P(u, v, z - share * drop(v))) for u, v in pts]

    L_keel = loop(keel, -1.3)
    L_p1 = loop(p1, 0.2)
    L_gb = loop(GIRDLE, ZG_BOT)
    L_gt = loop(GIRDLE, ZG_TOP)
    L_s1 = loop(s1, Z_S1, 0.55)
    L_to = loop(t_out, Z_TAB - 0.22, 1.0)
    L_ti = loop(t_in, Z_TAB, 1.0)

    ridge = {3, 9}  # the ridge band's edges on the right and left

    def band(a, b, matf):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = matf(i)

    step_mat = lambda i: LINEM if i in ridge else STEP  # noqa: E731
    band(L_keel, L_p1, lambda i: PAV)
    band(L_p1, L_gb, lambda i: PAV)
    band(L_gb, L_gt, lambda i: PAV)
    band(L_gt, L_s1, step_mat)
    band(L_s1, L_to, step_mat)
    band(L_to, L_ti, lambda i: LINEM)
    # The table: north of the ridge, the ridge band, south of it (each planar).
    bm.faces.new([L_ti[k] for k in (10, 11, 0, 1, 2, 3)]).material_index = TABN
    bm.faces.new([L_ti[k] for k in (3, 4, 9, 10)]).material_index = RIDGE
    bm.faces.new([L_ti[k] for k in (4, 5, 6, 7, 8, 9)]).material_index = TAB
    c = bm.verts.new(P(6.0, 8.3, -1.3))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((L_keel[j], L_keel[i], c)).material_index = PAV
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    gem_obj = common.mesh_object(f"{NAME}_gem", bm, mats, coll, smooth=False)

    # --- The steel cap: a ferrule along Y over the gem's north end. --------------------------------
    cap_mats = [common.palette_material(sprite, 57, NAME, metallic=0.35, roughness=0.3),
                common.palette_material(sprite, 52, NAME, metallic=0.7, roughness=0.45)]
    STEEL, GROOVE = 0, 1
    # Half width (px) per station: rows 1-2 cover columns 3-8 (half width 3) and the ink on row 0
    # is narrower (columns 4-7), so the north corners round off over the first half pixel.
    wf = pchip([0.95, 1.1, 1.35, 1.7, 2.3, 2.75], [2.35, 2.7, 2.92, 2.98, 3.0, 3.02])
    ZC, KZ = 1.9, 0.82  # section centre height and height/width ratio
    stations = [(0.86, 1.6, STEEL)]  # chamfered end face
    for v in (0.95, 1.05, 1.2, 1.4, 1.6):
        stations.append((v, wf(v), STEEL))
    # machined groove
    stations += [(1.78, wf(1.78), STEEL), (1.84, wf(1.84) - 0.22, GROOVE), (2.0, wf(2.0) - 0.22, STEEL),
                 (2.06, wf(2.06), STEEL)]
    for v in (2.3, 2.6):
        stations.append((v, wf(v), STEEL))
    # lip collar: a step out, flat band, chamfer back, tucked into the gem
    stations += [(2.66, wf(2.66), STEEL), (2.72, 3.16, STEEL), (3.15, 3.16, STEEL),
                 (3.28, 2.95, STEEL), (4.0, 2.5, STEEL)]
    sides = 32
    bm = bmesh.new()
    rings = []
    for v, w, m in stations:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(P(6 + w * math.cos(a), v, ZC + KZ * w * math.sin(a))))
        rings.append((ring, m))
    for (r0, m0), (r1, _) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = m0
    nose = bm.verts.new(P(6, 0.8, ZC))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[0][0][j], rings[0][0][k], nose)).material_index = STEEL
    tail = bm.verts.new(P(6, 4.2, ZC))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[-1][0][k], rings[-1][0][j], tail)).material_index = STEEL
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cap = common.mesh_object(f"{NAME}_cap", bm, cap_mats, coll, smooth=True)
    mod = cap.modifiers.new("ssa", "EDGE_SPLIT")  # hard edges at the groove and collar steps
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
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
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
    shell = common.outline_shell(joined, coll, voxel=0.012, faces=1200, inside=0.003)
    sink_shell(shell, joined, 0.4 * PX, 0.8 * PX)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(joined, do_unlink=True)
    objs = parts + [shell]
    common.export_sprite_model(root, objs, f"enemies/{NAME}", sprite["sprites"])
    tris = 0
    for o in parts:
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    print(f"model triangles {tris}, shell faces {len(shell.data.polygons)}")
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        common.render_preview(parts, out, root / "reference" / "models" / NAME / frame["image"], size=frame["size"])


if __name__ == "__main__":
    main()
