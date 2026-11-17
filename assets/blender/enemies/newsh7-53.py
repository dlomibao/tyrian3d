"""Blue crystal (newsh7.shp frames 53, 91, 129), an emerald-cut gem in a steel ferrule.

What it is: a cut blue gem lying flat, its north end held in a polished steel cap. The sprite is a
pixel octagon (45 degree corners on all four sides), and its pale lines are the facet edges of a
step cut: the table's outline (the left line at column 5, the right one at column 17, the bottom
line at row 20 and the two chamfered corners), corner joins running out to the girdle (column 15
under the table, row 17 on the right), and a transverse ridge at row 12 that runs across the whole
crown. North of the ridge the crown slopes down into the cap, which is why the sprite draws that
band darker (rows 8-11). So the gem is built as a faceted solid: girdle octagon, two crown steps,
a bevelled table edge (the pale lines, polished), a flat ridge band and a step-cut pavilion to a
short keel underneath (closed, plain). Flat facets, no beads, no glow: the pale lines are the
polished bevels' colour (142, unlit paint is gone), and they run as the sprite's U (left, south,
right below the ridge, the ridge's east end), not round the top. The SE crown (rows 17-22, white in
the sprite) is a polished pale-blue face (159, half metallic) whose steps pick up the light at their
own angles. The table is a cut dome: kite facets up to an alternately raised ring, a star ring and
a fan to the apex, leaning 10-35 degrees; half metallic (its reflection tinted by its blue) and
smooth, so each facet takes the sun and the environment's light panels at its own angle: some go
pale or white, some deep blue. That is the sparkle, sheen not paint (art rule 2). A dielectric at a
high F0 turned the whole table milky instead (the environment's even grey wash). North of the ridge
the outer facets are the sprite's navy band (148) with its light middle spot (157) at the centre.

The cap (rows 3-6) is a polished steel dome lying along the gem's axis: the same flattened
elliptical section lofted along Y (pchip widths matched to the sprite rows), its crown following a
profile that peaks at row 5 and falls about 20 degrees south into the gem, so the light above and
the sun (from the west, D205) lay a streak down its left-centre and the east side falls off dark,
as the sprite draws it. Palette 58, part metallic, coated. No groove or lip collar: those rings
read as a jar's mouth.

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
# each side. The top edge (row 6.8) runs under the cap's shoulder.
RN, RS = 12.05, 12.95
GIRDLE = [(5.6, 6.8), (18.4, 6.8), (21.0, 9.4), (21.0, RN), (21.0, RS), (21.0, 19.6),
          (15.6, 25.0), (8.4, 25.0), (3.0, 19.6), (3.0, RS), (3.0, RN), (3.0, 9.4)]
# The table's outline: the centre of the sprite's pale lines (left line column 5, right column 17,
# bottom row 20, chamfered corners down to (9.6, 20.4) and (15.4, 20.4)).
TABLE = [(6.3, 6.8), (16.8, 6.8), (17.5, 8.6), (17.5, RN), (17.5, RS), (17.5, 17.4),
         (15.4, 20.4), (9.6, 20.4), (5.5, 16.3), (5.5, RS), (5.5, RN), (5.5, 8.6)]
LINE = 0.6                    # half width of the bevelled table edge (the pale line), px
ZG_TOP, ZG_BOT = 2.9, 2.2      # girdle band
Z_S1, Z_S2, Z_TAB = 5.0, 6.35, 7.45  # crown steps and the table at the ridge
# (apex u, v), rise px, inner ring (fraction toward the apex), its alternating lift px: south, north
TABLE_APEX = {True: ((11.3, 16.4), 1.8, 0.5, 0.6), False: ((12.8, 9.7), 0.9, 0.6, 0.25)}
SLOPE_N, SLOPE_S = 0.30, 0.11  # the crown falls this much per px north / south of the ridge band


GEM_SPEC = 0.5 * ((1.4 / 3.4) ** 2 / 0.04)  # Specular IOR Level for an F0 of IOR 2.4 (D176)
# The crown steps' own F0 lower (about 0.065): at 0.17 the environment's even grey wash turned the
# saturated blues milky; the polished bevels keep the full F0 and a coat. The table's facets are
# half metallic instead (no coat), so their reflections are tinted blue and differ facet to facet.
BODY_SPEC = 0.8
GEM_ROUGH, GEM_COAT_ROUGH = 0.08, 0.05
STAR_T, STAR_LIFT = 0.35, 0.2  # the star ring: fraction toward the apex, alternating lift px
TAB_ROUGH, TAB_SPEC, TAB_COAT, TAB_METAL = 0.1, 0.5, 0.0, 0.6


def drop(y):
    return SLOPE_N * max(0.0, RN - y) + SLOPE_S * max(0.0, y - RS)


def build(sprite):
    coll = common.reset_collection(NAME)

    def gem(i, frames, rough=GEM_ROUGH, emit=0.0, spec=BODY_SPEC, coat=0.0, tag="gem", metal=0.0):
        # A cut gem: a dielectric with a diamond-like F0 (D176: Specular IOR Level, IOR ~2.4) and a
        # clear coat, low roughness, so every facet catches the sun and the environment's panels at
        # its own angle: the sprite's white facet glints come out as sheen, not paint (art rule 2).
        m = common.palette_material(sprite, i, f"{NAME}-{tag}", metallic=metal, roughness=rough,
                                    emission_strength=emit, frames=frames)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = spec
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = GEM_COAT_ROUGH
        return m

    mats = [
        gem(156, {91: 155, 129: 154}, rough=TAB_ROUGH, spec=TAB_SPEC, coat=TAB_COAT, metal=TAB_METAL, tag="table"),   # 0 table, south of the ridge
        gem(157, {91: 156, 129: 155}, rough=TAB_ROUGH, spec=TAB_SPEC, coat=TAB_COAT, metal=TAB_METAL, tag="tablen"),  # 1 north table's light middle spot
        gem(155, {91: 154, 129: 153}, tag="step"),         # 2 crown steps, sides and north
        gem(153, {129: 152}, tag="stepb"),                 # 3 crown steps, south
        gem(142, {91: 140, 129: 159}, rough=0.06, spec=GEM_SPEC, coat=1.0, tag="line"),  # 4 polished bevel (the pale lines)
        gem(159, {91: 158, 129: 157}, rough=0.06, spec=GEM_SPEC, coat=1.0, tag="ridge"),  # 5 ridge band on the table
        gem(150, {91: 149, 129: 148}, rough=0.15, coat=0.0, tag="pav"),    # 6 girdle and pavilion
        gem(148, {91: 147, 129: 146}, rough=TAB_ROUGH, spec=TAB_SPEC, coat=TAB_COAT, tag="tablenw"),  # 7 north table, the navy band
        gem(159, {91: 158, 129: 157}, rough=0.08, spec=0.5, metal=0.5, tag="glint"),  # 8 SE crown, a polished face
    ]
    TAB, TABN, STEP, STEPB, LINEM, RIDGE, PAV, TABNW, GLINT = range(9)

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

    # The SE crown (girdle edge 5, rows 17-22 east of column 15) is white in the sprite from the
    # table's chamfer to the girdle: a polished face there, every step.
    def step_mat(i):
        if i == 5:
            return GLINT
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
    band(L_to, L_ti, lambda i: STEP if i in (0, 1) else (RIDGE if i == 2 else LINEM))
    # The table: north of the ridge, the ridge band, south of it (each planar). Walk the loop from
    # the face's first base vertex so the polygon stays in order across the wrap.
    for base, m in (([10, 11, 0, 1, 2, 3], TABN), ([3, 4, 9, 10], RIDGE), ([4, 5, 6, 7, 8, 9], TAB)):
        if m == RIDGE:
            vs = [L_ti[k] for k, (i, s) in enumerate(entries) if i in base]
        else:
            start = next(k for k, (i, s) in enumerate(entries) if i == base[0])
            vs, vb = [], []  # the rim's vertices and their base (loop) vertex
            for d in range(m_):
                k = (start + d) % m_
                if entries[k][0] in base:
                    vs.append(L_ti[k])
                    vb.append(entries[k][0])
        if m == RIDGE:
            bm.faces.new(vs).material_index = m
            continue
        # The table is not a flat plate but a cut, faceted dome: an outer ring of kite facets up to a
        # raised inner ring (alternately high and low, so neighbouring facets lean differently) and a
        # fan to the apex. Facets lean 10-35 degrees, so under the sun (from the west and the camera's
        # side, D205) and the environment each one is lit or dark at its own angle: the gem sparkles
        # instead of reading as one glossy plate (D65), while the pale lines stay its outline.
        (au, av), rise, ring_t, jit = TABLE_APEX[m == TAB]
        z0 = sum(v.co.z for v in vs) / len(vs)
        apex = bm.verts.new(P(au, av, 0))
        apex.co.z = z0 + rise * PX
        # One ring vertex per base vertex (a doubled corner join is one corner here, its two rim
        # copies closing on it with a sliver triangle), so the inner facets are not slivers.
        groups = []  # (first rim index, last rim index) per base vertex, in order
        for k, bi in enumerate(vb):
            if groups and vb[groups[-1][0]] == bi:
                groups[-1] = (groups[-1][0], k)
            else:
                groups.append((k, k))
        n = len(groups)
        mid = []
        for g, (k0, k1) in enumerate(groups):
            q = ((vs[k0].co + vs[k1].co) / 2).lerp(apex.co, ring_t)
            q.z += (jit if g % 2 == 0 else -jit) * PX
            mid.append(bm.verts.new(q))
        # North of the ridge the sprite's table is a navy band (147-150) across nearly its whole width
        # with a lighter spot in the middle (154-159): the outer facets take the navy, the fan the spot.
        outer = TABNW if m == TABN else m
        for g in range(n):
            h = (g + 1) % n
            a0, a1 = vs[groups[g][1]], vs[groups[h][0]]
            if groups[g][0] != groups[g][1]:
                bm.faces.new((vs[groups[g][0]], a0, mid[g])).material_index = outer
            if g % 2 == 0:
                bm.faces.new((a0, a1, mid[h])).material_index = outer
                bm.faces.new((a0, mid[h], mid[g])).material_index = outer
            else:
                bm.faces.new((a0, a1, mid[g])).material_index = outer
                bm.faces.new((a1, mid[h], mid[g])).material_index = outer
        # Star facets: a third ring at the middle ring's edge mid-points, part way up to the apex, so
        # the crown's centre is cut too (more facets, more angles to catch a light).
        star = []
        for k in range(n):
            j = (k + 1) % n
            q = ((mid[k].co + mid[j].co) / 2).lerp(apex.co, STAR_T)
            q.z += STAR_LIFT * PX * (1 if k % 2 else -1)
            star.append(bm.verts.new(q))
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((mid[k], mid[j], star[k])).material_index = m
            bm.faces.new((mid[j], star[j], star[k])).material_index = m
            bm.faces.new((star[k], star[j], apex)).material_index = m
    # Keel: close the bottom.
    c = bm.verts.new(P(12.0, 16.0, -2.2))
    for k in range(m_):
        j = (k + 1) % m_
        bm.faces.new((L_keel[j], L_keel[k], c)).material_index = PAV
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    gem_obj = common.mesh_object(f"{NAME}_gem", bm, mats, coll, smooth=False)

    # --- The steel cap: a ferrule along Y over the gem's north end. --------------------------------
    # The cap is polished steel in the sprite: grey (52-62), a bright white streak along its middle
    # (cols 9-11, palette 60-62: the light's reflection along a round section), a dark right side.
    # So: palette 58 (the cap's lighter half, its median is 57), a domed crown, a little metallic and
    # coated with a high F0, smooth shaded: the top light and the sun (from the west) lay a streak
    # down the round top and the east side falls off dark (lighting, not paint). No groove or lip
    # step: those rings read as the mouth of a jar; a plain shoulder into the gem.
    def capm(i, metallic, rough, coat, spec):
        m = common.palette_material(sprite, i, NAME, metallic=metallic, roughness=rough)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = spec
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.04
        return m
    cap_mats = [capm(58, 0.2, 0.18, 1.0, GEM_SPEC)]
    STEEL = 0
    # Half width (px) per station, from the sprite's rows: row 3 x 8..16, rows 4-5 x 7..17, row 6
    # x 6..18; the shoulder at rows 6.7-7.5 sits over the gem's top edge.
    wf = pchip([3.0, 3.35, 3.9, 4.6, 5.4, 6.1, 6.7], [3.35, 4.05, 4.65, 4.95, 5.2, 5.75, 6.15])
    # Each section is the same flattened ellipse (height/width KZ); its crown follows its own profile:
    # a dome, highest at row 5 and falling about 20 degrees to the south into the gem, so the spine
    # faces the light above and then the sun (from the west, toward the camera, D205): the light lies
    # along the crown as one streak (the sprite's) and the east side falls off dark. A crown that rose
    # to the south (the section's height growing with its width) faced away and ringed it with bands.
    KZ = 0.8
    top = pchip([2.86, 3.3, 4.2, 5.0, 5.8, 6.6, 7.3, 8.4], [6.0, 7.4, 8.5, 8.7, 8.5, 8.1, 7.7, 7.0])
    stations = []  # (row, half width, material of the band that starts here)
    stations.append((2.86, 2.4, STEEL))  # rounded end face
    stations.append((2.93, 3.0, STEEL))
    for v in (3.05, 3.3, 3.55, 3.8, 4.05, 4.3, 4.6, 4.9, 5.2, 5.6, 6.0, 6.45, 6.7):
        stations.append((v, wf(v), STEEL))
    stations += [(7.1, 6.25, STEEL), (7.5, 6.1, STEEL), (8.4, 5.6, STEEL)]
    sides = 40
    bm = bmesh.new()
    rings = []
    for v, w, m in stations:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            zc = top(v) - KZ * w  # every section the same flattened ellipse, its crown on the profile
            ring.append(bm.verts.new(P(12 + w * math.cos(a), v, zc + KZ * w * math.sin(a))))
        rings.append((ring, m))
    for (r0, m0), (r1, _) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = m0
    # Nose: the end face, a shallow dome inset.
    nose = bm.verts.new(P(12, 2.78, top(2.86) - KZ * 2.4))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[0][0][j], rings[0][0][k], nose)).material_index = STEEL
    tail = bm.verts.new(P(12, 8.6, top(8.4) - KZ * 5.6))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[-1][0][k], rings[-1][0][j], tail)).material_index = STEEL
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cap = common.mesh_object(f"{NAME}_cap", bm, cap_mats, coll, smooth=True)
    # A hard edge round the end face only (auto-smooth by angle).
    for o in (cap,):
        mod = o.modifiers.new("ssa", "EDGE_SPLIT")
        mod.split_angle = math.radians(55)
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
