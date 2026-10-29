"""Bronze pod with telescoping arms (newsh2.shp frames 159-167): a 3D version of its sprite.

Seen in episode 1 (levels 25-41), episode 2 and episode 3. A round bronze ball clad in armour
plates, a steel band strapped across its upper half with a cross-shaped steel frame plate at its
middle, a steel capsule lying along the ball's front over that frame and down into a dark bay cut
in below the band, and a short boxy post on the crown. The plate layout, capsule and post follow
the concept (assets/blender/features/concepts/newsh2-159.jpg, registered to the sprite in
assets/blender/textures/newsh2-159/concept.png). Over the five frames the band's thin arms slide
out of the ball one pixel a side at a time (tips at 8, 9, 10, 11 and 12 px from the centre, outline
included) and red-hot fins open round them. The frames also alternate a shade darker and lighter,
and frame 159 is drawn one row higher. So each frame gets its own model: newsh2-159, newsh2-159-f2
(161) ... newsh2-159-f5 (167).

Rows and columns below are frame 161's (159 is shifted up one row by `up`); x is in px from the
sprite's centre line (column edge 12).

Run: blender --background --python assets/blender/enemies/newsh2-159.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-159"
U = 1 / 12

# Per frame: arm tip (px from centre), shade offset (0 dark, 1 light), rows shifted up, red fins
# as (centre x px, centre row, rx px, ry px, palette index) or None.
FRAMES = [
    (8, 0, 1, None),
    (9, 1, 0, None),
    (10, 0, 0, (7.9, 16.0, 1.0, 1.0, 114)),
    (11, 1, 0, (8.0, 14.4, 1.1, 3.6, 119)),
    (12, 1, 0, (8.5, 14.8, 1.6, 4.2, 119)),
]

# The ball: (row edge, half width px). Its cross-sections are round: half height = ROUND x width.
BODY = ((8.1, 0.0), (8.4, 3.0), (9.0, 4.6), (10.0, 5.9), (11.0, 7.0), (12.0, 7.7), (13.0, 8.0),
        (19.6, 8.0), (20.3, 7.5), (21.2, 6.6), (22.2, 5.3), (23.2, 3.8), (23.8, 2.2), (24.05, 0.0))
ROUND = 0.95
CENTRE_ROW = 16.05

# The steel band strapped round the ball (rows 12-15, centre on row edge BAR_ROW): a flat strap
# BAR_HW px either side of its centre line, BAR_T px thick with bevelled edges. The ball narrows
# under it (to PINCH_W px, the groove the strap sits in).
BAR_ROW, BAR_HW, BAR_T, BAR_BEV = 14.0, 2.0, 1.6, 0.4
PINCH_W, PINCH_IN, PINCH_OUT = 6.4, 2.0, 2.25

# Armour plates on the ball, traced from the concept. Each plate is a curved shell PLATE_LIFT px
# out from the ball along its normal, with a straight wall down into it; its edges are smooth,
# evenly sampled curves: straight seams in the top view, or curves at a fixed fraction of the
# ball's outline (PLATE_K for the outer edge, the rim's inner edge between RIM_K and LOWER_K).
PLATE_K, PLATE_LIFT, PLATE_DEPTH = 0.94, 0.5, 1.0
G = 0.18  # half a seam's width
SHOULDER_SEAMS = (5.4, 2.6)  # above the band: outer | inner shoulder plate | channel round the post
UPPER_EDGE = 12.0 - G  # the shoulder plates' lower edge, at the band
LOWER_EDGE = 16.2 + G  # the lower plates' upper edge, at the band
FLANK_SEAM = 5.0  # flank plate | lighter bay-side plate
BAYSIDE = ((LOWER_EDGE, 4.0 - G), (17.9, 3.15 + G), (20.0 - G, 3.15 + G))  # its inner edge (row, |x|)
BOTTOM_EDGE = 20.0 + G  # the bottom plate's upper edge, under the bay
RIM_K = 0.80  # the rolled rim round the bottom: between RIM_K and PLATE_K of the outline
LOWER_K = RIM_K - 0.03  # the lower plates' outer edge, inside the rim
RIM_LIFT = 0.3  # the rim stands lower than the plates, so it doesn't read as a lip
RIM_SPLITS = (-178.0, -128.0, -52.0, -2.0)  # degrees round the centre (0 = right, -90 = bottom)
# The dark bay under the band (cols 9-15, rows 16-20): straight-sided, wider at the band.
BAY = [(-3.7, 15.6), (3.7, 15.6), (2.8, 17.8), (2.8, 19.9), (-2.8, 19.9), (-2.8, 17.8)]
BAY_DEPTH = 4.5


def body_width(r):
    for (r0, w0), (r1, w1) in zip(BODY, BODY[1:]):
        if r0 <= r <= r1:
            return w0 + (w1 - w0) * (r - r0) / (r1 - r0)
    return 0.0


def ball_top(x, r):
    """Height (px) of the unpinched round ball at (x px, row)."""
    w = body_width(r)
    if w <= 0 or abs(x) >= w:
        return 0.0
    return ROUND * w * math.sqrt(1 - (x / w) ** 2)


def body_sections(E):
    """Loft sections (y, half width, half height, z) in units: round, pinched under the bar."""
    rows = {r for r, _ in BODY}
    rows |= {9.5, 10.5, 11.5, 15.0, 16.0, 17.0, 18.0, 19.0, 20.75, 21.7, 22.7}
    rows |= {BAR_ROW + s * d for s in (-1, 1) for d in (0.0, PINCH_IN, PINCH_OUT)}
    out = []
    for r in sorted(rows):
        w = body_width(r)
        h = ROUND * w
        d = abs(r - BAR_ROW)
        p = 1.0 if d <= PINCH_IN else max(0.0, (PINCH_OUT - d) / (PINCH_OUT - PINCH_IN))
        p = p * p * (3 - 2 * p)
        if w > PINCH_W:
            w -= p * (w - PINCH_W)
        out.append((E(r), w * U, h * U, 0.0))
    return out


# --- 2D helpers in (x px, row) --------------------------------------------------------------------

def outline_radius(theta):
    """Distance (px) from the ball's top-view centre to its outline at angle theta (radians,
    0 = right, positive = up the screen)."""
    lo, hi = 0.0, 12.0
    for _ in range(30):
        m = 0.5 * (lo + hi)
        x, r = m * math.cos(theta), CENTRE_ROW - m * math.sin(theta)
        if abs(x) <= body_width(r) and BODY[0][0] <= r <= BODY[-1][0]:
            lo = m
        else:
            hi = m
    return lo


def outline_pt(theta, k):
    rho = k * outline_radius(theta)
    return (rho * math.cos(theta), CENTRE_ROW - rho * math.sin(theta))


def resample(poly, step=0.5):
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        n = max(1, math.ceil(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n)]
    clean = []
    for p in out:
        if not clean or math.dist(p, clean[-1]) > 0.05:
            clean.append(p)
    if len(clean) > 2 and math.dist(clean[0], clean[-1]) < 0.05:
        clean.pop()
    return clean


def rel(x, r):
    """How far (x px, row) is out from the ball's top-view centre, as a fraction of the outline."""
    th = math.atan2(CENTRE_ROW - r, x)
    return math.hypot(x, CENTRE_ROW - r) / outline_radius(th)


def solve(f, lo, hi, it=40):
    """Bisection: f(lo) and f(hi) have opposite signs."""
    flo = f(lo)
    for _ in range(it):
        m = 0.5 * (lo + hi)
        if (f(m) > 0) == (flo > 0):
            lo, flo = m, f(m)
        else:
            hi = m
    return 0.5 * (lo + hi)


def ball_surface(x, r):
    """Height (px) of the ball (with its pinch under the band) at (x px, row), as lofted."""
    w = body_width(r)
    h = ROUND * w
    d = abs(r - BAR_ROW)
    p = 1.0 if d <= PINCH_IN else max(0.0, (PINCH_OUT - d) / (PINCH_OUT - PINCH_IN))
    p = p * p * (3 - 2 * p)
    if w > PINCH_W:
        w -= p * (w - PINCH_W)
    if w <= 0:
        return 0.0
    u = min(abs(x) / w, 0.995)  # plate edges never quite reach the outline
    return h * math.sqrt(1 - u * u)


def surf(x, r, off, E):
    """The point `off` px out along the ball's normal from its surface over (x px, row), in units."""
    e = 0.03
    z = ball_surface(x, r)
    fx = (ball_surface(x + e, r) - ball_surface(x - e, r)) / (2 * e)
    fr = (ball_surface(x, r + e) - ball_surface(x, r - e)) / (2 * e)
    # world y = -row (px), so dz/dy = -fr; normal = (-dz/dx, -dz/dy, 1)
    nx, ny, nz = -fx, fr, 1.0
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    return ((x + off * nx / ln) * U, E(r) + off * ny / ln * U, (z + off * nz / ln) * U)


def grid_plate(bm, grid, E, mat, lift=PLATE_LIFT, depth=PLATE_DEPTH):
    """A curved armour plate on the ball from a quad grid of top-view points grid[i][j] (x px, row):
    a smooth shell `lift` px out along the ball's normal, its boundary the grid's evenly sampled
    edge curves, and a straight wall from that edge down into the ball (`depth` px along the
    normal). Collapsed grid columns (several equal points) are welded."""
    key = lambda p: (round(p[0], 4), round(p[1], 4))  # noqa: E731
    top, low = {}, {}
    for row in grid:
        for p in row:
            k = key(p)
            if k not in top:
                top[k] = bm.verts.new(surf(p[0], p[1], lift, E))
                low[k] = surf(p[0], p[1], -depth, E)

    def up_face(vs):
        a, b, c = (v.co for v in vs[:3])
        if (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) < 0:
            vs = vs[::-1]
        return vs

    for i in range(len(grid) - 1):
        for j in range(len(grid[0]) - 1):
            ks = []
            for p in (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]):
                k = key(p)
                if k not in ks:
                    ks.append(k)
            if len(ks) < 3:
                continue
            vs = [top[k] for k in ks]
            if len(vs) == 4:  # split along the shorter diagonal
                d0 = (vs[0].co - vs[2].co).length
                d1 = (vs[1].co - vs[3].co).length
                tris = [vs[:3], [vs[0], vs[2], vs[3]]] if d0 <= d1 else [[vs[0], vs[1], vs[3]], vs[1:]]
            else:
                tris = [vs]
            for t in tris:
                try:
                    f = bm.faces.new(up_face(t))
                except ValueError:
                    continue
                f.material_index = mat
                f.smooth = True
    # The boundary loop: round the grid's edge.
    ni, nj = len(grid), len(grid[0])
    loop = [grid[0][j] for j in range(nj)] + [grid[i][nj - 1] for i in range(1, ni)]
    loop += [grid[ni - 1][j] for j in range(nj - 2, -1, -1)] + [grid[i][0] for i in range(ni - 2, 0, -1)]
    ks = []
    for p in loop:
        k = key(p)
        if not ks or ks[-1] != k:
            ks.append(k)
    if ks[0] == ks[-1]:
        ks.pop()
    area = sum(top[a].co.x * top[b].co.y - top[b].co.x * top[a].co.y for a, b in zip(ks, ks[1:] + ks[:1]))
    if area < 0:
        ks.reverse()
    lows = {k: bm.verts.new(low[k]) for k in ks}
    for a, b in zip(ks, ks[1:] + ks[:1]):
        f = bm.faces.new((top[a], lows[a], lows[b], top[b]))
        f.material_index = mat
        f.smooth = False
        e = bm.edges.get((top[a], top[b]))
        if e:
            e.smooth = False


def lin(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def column_grid(x0, x1, r_a, r_b, step=0.45):
    """Grid over columns x0..x1, each from row r_a(x) to row r_b(x), evenly sampled."""
    nx = max(2, math.ceil(abs(x1 - x0) / step))
    xs = lin(x0, x1, nx)
    span = max(abs(r_b(x) - r_a(x)) for x in xs)
    nr = max(2, math.ceil(span / step))
    return [[(x, r) for r in lin(r_a(x), r_b(x), nr)] for x in xs]


def row_grid(r0, r1, x_a, x_b, step=0.45):
    """Grid over rows r0..r1, each from x_a(row) to x_b(row), evenly sampled."""
    nr = max(2, math.ceil(abs(r1 - r0) / step))
    rs = lin(r0, r1, nr)
    span = max(abs(x_b(r) - x_a(r)) for r in rs)
    nx = max(2, math.ceil(span / step))
    return [[(x, r) for x in lin(x_a(r), x_b(r), nx)] for r in rs]


def curve_row(x, k, upper, edge):
    """The row where column x crosses the curve at fraction k of the outline, going out (up or
    down the screen) from row `edge`; `edge` itself if that is already outside the curve."""
    if rel(x, edge) >= k:
        return edge
    far = CENTRE_ROW - 12 if upper else CENTRE_ROW + 12
    return solve(lambda r: rel(x, r) - k, far, edge)


def curve_x(r, k, side=-1):
    """The column where row r crosses the curve at fraction k of the outline, on one side."""
    return solve(lambda x: rel(side * x, r) - k, 0.0, 12.0) * side


def chamfer_block(bm, poly, z0, z1, cham, mat, top_mat=None):
    """A hard block on a top-view polygon (units), from z0 up to z1, its top edge chamfered by
    `cham` (inset and drop)."""
    def inset(p, d):
        n = len(p)
        out = []
        sgn = 1 if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) > 0 else -1
        for i in range(n):
            a, b, c = p[i - 1], p[i], p[(i + 1) % n]
            e1 = (b[0] - a[0], b[1] - a[1])
            e2 = (c[0] - b[0], c[1] - b[1])
            l1, l2 = math.hypot(*e1), math.hypot(*e2)
            n1 = (-e1[1] / l1 * sgn, e1[0] / l1 * sgn)
            n2 = (-e2[1] / l2 * sgn, e2[0] / l2 * sgn)
            m = (n1[0] + n2[0], n1[1] + n2[1])
            ml = m[0] * n1[0] + m[1] * n1[1]
            out.append((b[0] + d * m[0] / ml, b[1] + d * m[1] / ml))
        return out
    rings = [[(x, y, z0) for x, y in poly], [(x, y, z1 - cham) for x, y in poly],
             [(x, y, z1) for x, y in inset(poly, cham)]]
    tm = mat if top_mat is None else top_mat  # the top face and its bevel
    lib.ring_loft(bm, rings, [mat, tm], cap_start=True, cap_end=True, cap_mats=(mat, tm), smooth=False)


def append_mesh(bm, obj):
    """Copy an object's mesh (faces, material indices, smooth flags) into bm, then delete it."""
    mesh = obj.data
    verts = [bm.verts.new(v.co) for v in mesh.vertices]
    for p in mesh.polygons:
        f = bm.faces.new([verts[i] for i in p.vertices])
        f.material_index = p.material_index
        f.smooth = p.use_smooth
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)


def build_one(sprite, name, tip, shade, up, fins):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i + shade, NAME, **kw)  # noqa: E731
    # Lighting pass: everything is metal, so each part is one mid-tone and the game's lights shade
    # it and make the shine; the sprite's dark rim ring, lit shoulders and white hot spots were its
    # drawn light, not paint. The concept's plate seams, rivets and wear come from the baked
    # texture (texture_bake.py) on top of these colours.
    steel = pal(6, metallic=0.55, roughness=0.4)
    mats = [
        pal(17, metallic=0.4, roughness=0.6),  # 0 dark under-structure in the channel round the post
        pal(22, metallic=0.55, roughness=0.4),  # 1 bronze armour plates
        pal(165, metallic=0.55, roughness=0.35),  # 2 post
        steel,  # 3 steel band
        pal(4, metallic=0.5, roughness=0.45),  # 4 dark steel frame plate on the band
        pal(17, metallic=0.0, roughness=0.9),  # 5 dark bay walls
        pal(4, metallic=0.75, roughness=0.3),  # 6 darker grey arms and bar ends
        pal(24, metallic=0.55, roughness=0.4),  # 7 the lighter flank plates beside the bay
        pal(4, metallic=0.6, roughness=0.45),  # 8 the dark steel capsule (the sprite's bay greys)
        pal(21, metallic=0.55, roughness=0.4),  # 9 the plain bronze ball
        pal(166, metallic=0.55, roughness=0.45),  # 10 the post's bevelled top (sprite's grey-bronze)
        steel,  # 11 capsule collars
        common.palette_material(sprite, 1, NAME, metallic=0.0, roughness=1.0),  # 12 bay floor
        pal(20, metallic=0.45, roughness=0.65),  # 13 the bottom plate and rim round it, dull
    ]
    BASE, PLATE, KNOB, BAR, FRAME, SLOT, ARM, FLANK, POD, RIM, CAP, COLLAR, FLOOR, BOTTOM = range(14)
    if fins:
        mats.append(common.palette_material(sprite, fins[4], NAME, emission_strength=3.0 if fins[4] == 119 else 1.5))
    FIN = 14
    R = lambda r: lib.row(r - up)  # noqa: E731
    E = lambda r: lib.ey(r - up)  # noqa: E731

    # Ball: rows 8-24, columns 4-19, as tall as it is wide, dark bronze (only seen in the seams).
    hull = lib.Profile(body_sections(E))
    hbm = bmesh.new()
    hull.build(hbm, sides=20, mat_index=BASE)
    bmesh.ops.recalc_face_normals(hbm, faces=hbm.faces)
    body = lib.finish(name + "-ball", hbm, mats, coll)

    # The dark bay under the band, cut BAY_DEPTH px into the ball: straight walls for 1.5 px, then
    # a funnel narrowing into the dark.
    bx, by = 0.0, E(17.8)
    outline = [(x * U, E(r)) for x, r in resample(BAY, 0.8)]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1])) < 0:
        outline.reverse()
    n = len(outline)
    cbm = bmesh.new()
    top = [cbm.verts.new((x, y, 2.0)) for x, y in outline]
    mid = [cbm.verts.new((x, y, hull.top(x, y) - 1.5 * U)) for x, y in outline]
    floor_z = hull.top(bx, by) - BAY_DEPTH * U
    bot = [cbm.verts.new((bx + 0.15 * (x - bx), by + 0.15 * (y - by), floor_z)) for x, y in outline]
    for k in range(n):
        j = (k + 1) % n
        cbm.faces.new((mid[k], mid[j], top[j], top[k])).material_index = SLOT
        cbm.faces.new((bot[k], bot[j], mid[j], mid[k])).material_index = FLOOR
    cbm.faces.new(list(reversed(bot))).material_index = FLOOR
    cbm.faces.new(top).material_index = SLOT
    cutter = common.mesh_object(name + "-cutter", cbm, mats, coll)
    mod = body.modifiers.new("bay", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=body, active_object=body):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    for p in body.data.polygons:
        if p.material_index in (SLOT, FLOOR):
            p.use_smooth = False
        elif not (abs(p.center.x) < 2.9 * U and p.center.y > E(12.6)):
            # Only the channel round the post (between the shoulder plates, above the band) is
            # the dark under-structure; elsewhere the ball is plain bronze (the plate seams get
            # their dark from the baked occlusion).
            p.material_index = RIM

    bm = bmesh.new()
    append_mesh(bm, body)

    # Armour plates (the concept's): two shoulder plates a side above the band, below it a flank
    # plate and a lighter plate beside the bay each side, a bottom plate under the bay and a rolled
    # rim in three segments round the bottom edge.
    so, si = SHOULDER_SEAMS
    for sd in (-1, 1):
        x_edge = curve_x(UPPER_EDGE, PLATE_K, sd)
        top_k = lambda x: curve_row(x, PLATE_K, True, UPPER_EDGE)  # noqa: E731
        band = lambda x: UPPER_EDGE  # noqa: E731
        grid_plate(bm, column_grid(x_edge, sd * (so + G), top_k, band), E, PLATE)
        grid_plate(bm, column_grid(sd * (so - G), sd * (si + G), top_k, band), E, PLATE)
        # Below the band: the flank plate out to the rim's inner edge ...
        bot_k = lambda x: curve_row(x, LOWER_K, False, LOWER_EDGE)  # noqa: E731
        x_edge = curve_x(LOWER_EDGE, LOWER_K, sd)
        grid_plate(bm, column_grid(x_edge, sd * (FLANK_SEAM + G), lambda x: LOWER_EDGE, bot_k), E, PLATE)

        # ... and the lighter plate beside the bay.
        def inner(r, sd=sd):
            for (r0, x0), (r1, x1) in zip(BAYSIDE, BAYSIDE[1:]):
                if r <= r1:
                    return sd * (x0 + (x1 - x0) * (r - r0) / (r1 - r0))
            return sd * BAYSIDE[-1][1]

        def outer(r, sd=sd):
            return sd * min(FLANK_SEAM - G, abs(curve_x(r, LOWER_K, sd)))
        grid_plate(bm, row_grid(LOWER_EDGE, BAYSIDE[-1][0], outer, inner), E, FLANK)
    # The bottom plate under the bay, out to the rim.
    xb = min(FLANK_SEAM - G, abs(curve_x(BOTTOM_EDGE, LOWER_K, 1)))
    grid_plate(bm, column_grid(-xb, xb, lambda x: BOTTOM_EDGE,
                               lambda x: curve_row(x, LOWER_K, False, BOTTOM_EDGE)), E, BOTTOM)
    # The rim: between RIM_K and PLATE_K of the outline, from the band's lower edge round the
    # bottom, standing a little lower than the plates and the same dull bronze as the bottom plate
    # (a lighter rim round a darker plate read as a bowl's lip from the game camera).
    th_lo = math.degrees(math.atan2(-(LOWER_EDGE - CENTRE_ROW), -7.8))
    splits = [th_lo] + list(RIM_SPLITS[1:-1]) + [-180 - th_lo]
    for a0, a1 in zip(splits, splits[1:]):
        a0g, a1g = a0 + (0.0 if a0 == splits[0] else 1.6), a1 - (0.0 if a1 == splits[-1] else 1.6)
        m = max(4, int((a0g - a1g) / 3))
        grid = [[outline_pt(math.radians(a), k) for k in lin(RIM_K, PLATE_K, 3)] for a in lin(a0g, a1g, m)]
        grid_plate(bm, grid, E, BOTTOM, lift=RIM_LIFT)

    # Post on the crown (cols 10-13, rows 7-11): a short squarish armoured block, about as deep as
    # it is wide, standing about 8 px tall, its top a bevelled steel cap.
    post = [(-2.0, 7.0), (1.85, 7.0), (1.85, 10.9), (-2.0, 10.9)]
    pp = [(x * U, E(r)) for x, r in post]
    pp = pp[::-1] if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pp, pp[1:] + pp[:1])) < 0 else pp
    chamfer_block(bm, pp, 0.0, 8.6 * U, 0.7 * U, KNOB, top_mat=CAP)

    # The band strapped round the ball (rows 12-15): a flat steel strap with bevelled edges, its
    # inner face on the pinched ball's cross-section and its outer face BAR_T px further out.
    yb = E(BAR_ROW)
    a_in, b_in = PINCH_W, ROUND * body_width(BAR_ROW)
    hw, bt, bv = BAR_HW, BAR_T, BAR_BEV
    sec = [(bt, -hw + bv), (bt, hw - bv), (bt - bv, hw), (0.0, hw), (0.0, -hw), (bt - bv, -hw)]
    n_arc = 32
    for k in range(len(sec)):
        strip = []
        for i in range(n_arc):
            t = 2 * math.pi * i / n_arc
            c, s = math.cos(t), math.sin(t)
            strip.append([bm.verts.new((-(a_in + d) * c * U, yb + dy * U, (b_in + d) * s * U))
                          for d, dy in (sec[k], sec[(k + 1) % len(sec)])])
        for i in range(n_arc):
            p, q = strip[i], strip[(i + 1) % n_arc]
            f = bm.faces.new((p[0], q[0], q[1], p[1]))
            f.material_index = BAR
            f.smooth = True

    # The cross-shaped steel frame plate on the band's middle (cols 9-15, rows 12-16), a flat
    # chamfered plate standing just proud of the strap, that the capsule lies across.
    frame = [(-3.4, 12.6), (-2.6, 11.9), (2.6, 11.9), (3.4, 12.6), (3.4, 15.4), (2.7, 16.2),
             (-2.7, 16.2), (-3.4, 15.4)]
    fp = [(x * U, E(r)) for x, r in frame]
    fp = fp[::-1] if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(fp, fp[1:] + fp[:1])) < 0 else fp
    chamfer_block(bm, fp, 5.0 * U, (b_in + bt + 0.35) * U, 0.35 * U, FRAME)

    # The steel capsule (cols 10-13, rows 11-19): a round-ended cylinder lying along the ball's
    # front, its dome over the frame plate and its tail sunk into the bay. Its axis falls from
    # 8.4 px at the dome to 6.7 px at the tail (its top just proud of the band and frame plate); it
    # is about as tall as it is wide.
    cw, ch = 1.8, 1.9
    r0, r1 = 11.0, 19.1
    z_at = lambda r: 8.4 + (6.7 - 8.4) * (r - r0) / (r1 - r0)  # noqa: E731
    secs = []
    dome = 1.8
    for t in (0.0, 0.25, 0.5, 0.7, 0.85, 1.0):
        r = r0 + dome * (1 - math.cos(t * math.pi / 2))
        k = math.sin(t * math.pi / 2)
        secs.append((r, k))
    for r, k in ((14.5, 1.0), (18.75, 0.95), (19.05, 0.7), (r1, 0.0)):
        secs.append((r, k))
    psec = [(E(r), cw * k * U, ch * k * U, z_at(r) * U) for r, k in secs]
    f0 = len(bm.faces)
    common.loft(bm, psec, sides=14, mat_index=POD)
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[f0:])
    for f in bm.faces[f0:]:
        f.smooth = True

    # Dark grey bar ends where the band meets the sides, and the thin arms out to the tips.
    for s in (-1, 1):
        x0, x1 = 6.6 * U, min(8.3, tip + 0.1) * U
        lib.polyline_tube(bm, [(s * x0, yb, 0.4 * U), (s * x1, yb, 0.4 * U)], 1.75 * U, sides=10, mat_index=ARM)
        if tip > 8.3:
            lib.polyline_tube(bm, [(s * 7.5 * U, yb, 0.4 * U), (s * (tip - 0.4) * U, yb, 0.4 * U),
                                   (s * tip * U, yb, 0.4 * U)],
                              [1.0 * U, 1.0 * U, 0.6 * U], sides=8, mat_index=ARM)

    # Red fins opening round the arms, outside the ball's sides.
    if fins:
        cx, cr, rx, ry, _ = fins
        for s in (-1, 1):
            poly = lib.ellipse_polygon(s * cx * U, R(cr), rx * U, ry * U, n=12)
            if s < 0:
                poly = poly[::-1]
            common.slab(bm, poly, 0.05, z=0.4 * U, mat_index=FIN)

    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, (frame, spec) in enumerate(zip(frames, FRAMES)):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        models.append((name, [build_one(sprite, name, *spec)], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
