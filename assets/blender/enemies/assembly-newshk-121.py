"""WARNING sign before the boss (newshk.shp frames 121 + 123, assembly of 2 pieces), design A.

What it is: a neon sign, 36 x 22 px of ink in a 48 x 28 block. A shallow black sign cabinet (the
sprite's index-32 field behind the word) carries the word WARNING bent in thin green neon tube; one
more neon run starts at the left end of the underline, runs along the cabinet's bottom edge, turns
up the right end as a bracket, leaves the cabinet's top-right corner, steps left, rises diagonally
up-left and on up to an arrowhead (a chevron of the same tube) pointing up the screen. The arrow is
outside the cabinet, so it rides on a thin black mounting spine under the tube with standoff posts.
In 3.6 FLEET and 4.12 LAVA RUN it sweeps up the screen fast (ev19, -8..-10 px/tick).

Plan (rule 1, D74 inner edge): the cabinet's plan is the inner mask's dark field (rows 14-21,
cols 2-35, its top-right corner cut back between the G and the bracket); the letters' tops stand
one pixel proud of the cabinet's top edge as the sprite draws them. Tubes are 1.1 px glass (the
sprite's one-pixel strokes); the arrow's diagonal is a heavier 1.7 px bore (the sprite's three-pixel
diagonal), tapering into the 1.1 px bracket and shaft.

Colour (rule 1, per region): cabinet pal 32 (the field), satin black with a slightly raised F0
(Specular IOR Level 0.25, roughness 0.55, D176) so it reads as black lacquer, not a hole, without a grey apron. Neon: every tube run (letters,
underline, bracket, arrow and arrowhead) is one even glow colour, pal 197, the measured region
median. The sprite's per-row ramp on the letters (195-201), the underline's 193 dashes and its
199-203 pulse and the arrowhead's radial ramp are lighting and glow falloff (rule 2): sheen and
lighting make that gradient, not painted bands (fix round 1). Glows:
metallic 1, roughness 0.55 (D126/D173), strength 0.8-1.0: in game the sprite's brightness, with
enough lit term left that the tubes still read round.

Outline shell (D51/D90/D118): from a sealed copy (the cabinet prism up to the tube centres, plus the
arrow run and head as one tube), voxel remeshed, every island kept (the left arrow arm is its own
island in piece 121 after the cut), sliced open per piece so no ink lies along the seam.

Underside: the cabinet's closed bottom and a smaller closed rear box; no detail.

Output: public/models/enemies/<piece>.glb (piece + its _outline shell, centred) and the
spriteModels entries. --measure [DIR] also writes report.json, pal.json and views/ to DIR (default: a
new temp folder).

    Blender -b --factory-startup -P assembly-newshk-121.py -- [--measure [DIR]]
"""

import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newshk-121"
PIECES = [("newshk-121", -12), ("newshk-123", 12)]  # piece, centre px from the assembly centre
W, H = 48, 28
PX = 1 / 12

_idx, _colors = SM.load(NAME)
MASKS = SM.masks(_idx, _colors, [])
INNER = MASKS["inner"]


def X(e):
    """Column edge coordinate (pixel c spans e = c .. c+1) to Blender X."""
    return (e - W / 2) / 12


def Y(s):
    """Row edge coordinate to Blender Y (sprite up is +Y)."""
    return (H / 2 - s) / 12


def E(x):
    return x * 12 + W / 2


def S(y):
    return H / 2 - y * 12


# --- dimensions (units) ------------------------------------------------------------------------

Z_BOT = 0.0          # cabinet bottom
Z_TOP = 0.12         # cabinet face
BEVEL = 0.022        # chamfer on the face edge
GROOVE = (0.042, 0.066, 0.02)  # panel line round the cabinet sides: z0, z1, depth
R_L = 0.52           # letter tube radius, px
GAP = 0.018          # standoff gap between tube and face, units
Z_T = Z_TOP + GAP + R_L * PX  # tube centre height

# --- strokes (pixel centres (c, r)) ------------------------------------------------------------

LETTERS = [
    # W
    [(2, 13), (2, 19), (6, 19), (6, 13)], [(4, 19), (4, 15)],
    # A
    [(8, 19), (8, 13), (10, 13), (10, 19)], [(8, 16), (10, 16)],
    # R
    [(12, 19), (12, 13), (13, 13), (14, 14), (14, 15), (13, 16), (12, 16)], [(13, 16), (14, 17), (14, 19)],
    # N
    [(16, 19), (16, 13), (19, 16)], [(19, 13), (19, 19)],
    # I
    [(21, 13), (23, 13)], [(22, 13), (22, 19)], [(21, 19), (23, 19)],
    # N
    [(25, 19), (25, 13), (28, 16)], [(28, 13), (28, 19)],
    # G
    [(32, 13), (31, 13), (30, 14), (30, 18), (31, 19), (32, 19), (33, 18), (33, 16), (32, 16)],
]

# The underline -> bracket -> arrow run (edge coords e, s and tube radius in px per point), traced
# from the sprite's green pixel centres row by row.
RUN = [
    (2.25, 21.5, 0.55), (33.3, 21.5, 0.58), (34.5, 20.55, 0.84), (35.5, 19.4, 0.62), (35.5, 13.9, 0.62),
    (34.6, 12.5, 0.86), (33.7, 11.5, 0.68), (30.4, 11.5, 0.62), (29.5, 10.5, 0.9), (26.5, 7.5, 0.9),
    (25.8, 6.5, 0.72), (25.5, 5.4, 0.55), (25.5, 2.3, 0.55),
]
# The arrowhead's barbs, apex out (each a gently curved tube, as the sprite's swept-back chevron).
HEAD_L = [(25.5, 1.68, 0.6), (24.65, 2.5, 0.62), (24.0, 3.5, 0.64), (23.0, 4.5, 0.6), (21.45, 5.55, 0.5),
          (20.5, 6.45, 0.5)]
HEAD_R = [(51.0 - e, s, r) for e, s, r in HEAD_L]
# A dark backing plate behind the arrowhead (the sprite's ink between barbs and shaft is inner).
HEAD_PLATE = [(25.5, 2.7), (29.85, 4.2), (28.6, 4.95), (28.0, 5.2), (28.0, 6.0), (24.0, 6.0), (24.0, 5.2),
              (22.4, 4.95), (21.15, 4.2)]


# --- geometry helpers --------------------------------------------------------------------------

def fillet(pts, rad=0.45, step=0.22):
    """Round each interior corner of a polyline [(e, s, r)] with a quadratic arc (trimmed to at most
    `rad` px and 45% of either leg) and resample at `step` px. Returns [(e, s, r)]."""
    P = [Vector((p[0], p[1])) for p in pts]
    R = [p[2] for p in pts]
    out = [(P[0], R[0])]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u0, u1 = (b - a), (c - b)
        t = min(rad, 0.45 * u0.length, 0.45 * u1.length)
        if u0.length < 1e-6 or u1.length < 1e-6:
            continue
        p0, p2 = b - u0.normalized() * t, b + u1.normalized() * t
        r0 = R[i - 1] + (R[i] - R[i - 1]) * (1 - t / u0.length)
        r2 = R[i] + (R[i + 1] - R[i]) * (t / u1.length)
        out.append((p0, r0))
        for k in range(1, 6):
            q = k / 6
            out.append(((1 - q) ** 2 * p0 + 2 * q * (1 - q) * b + q * q * p2, r0 + (r2 - r0) * q))
        out.append((p2, r2))
    out.append((P[-1], R[-1]))
    res = [out[0]]
    for (pa, ra), (pb, rb) in zip(out, out[1:]):
        L = (pb - pa).length
        n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1):
            q = k / n
            res.append((pa + (pb - pa) * q, ra + (rb - ra) * q))
    clean = [res[0]]
    for p, r in res[1:]:
        if (p - clean[-1][0]).length > 1e-4:
            clean.append((p, r))
    return [(p.x, p.y, r) for p, r in clean]


def chaikin(pts, iters=2):
    """Corner-cutting smoothing of [(e, s, r)], endpoints kept."""
    for _ in range(iters):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append(tuple(0.75 * x + 0.25 * y for x, y in zip(a, b)))
            out.append(tuple(0.25 * x + 0.75 * y for x, y in zip(a, b)))
        out.append(pts[-1])
        pts = out
    return pts


def resample(pts, step=0.22):
    res = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1):
            q = k / n
            res.append(tuple(x + (y - x) * q for x, y in zip(a, b)))
    return res


def tube(bm, path, z, mat_of, sides=10, caps=True):
    """A round tube along [(e, s, r_px)] at height z; rounded (hemispherical) ends when caps.
    mat_of(e, s) gives each face's material by its centre."""
    pts = [Vector((X(e), Y(s), z)) for e, s, _ in path]
    rads = [r * PX for *_, r in path]
    up = Vector((0, 0, 1))
    frames = []
    for i in range(len(pts)):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(up).normalized()
        frames.append((t, side))
    rings = []

    def ring(c, side, r):
        return [bm.verts.new(c + side * (r * math.cos(2 * math.pi * (k + 0.5) / sides))
                             + up * (r * math.sin(2 * math.pi * (k + 0.5) / sides)))
                for k in range(sides)]
    if caps:  # start dome
        t, side = frames[0]
        for a in (75, 55, 30):
            ca = math.radians(a)
            rings.append(ring(pts[0] - t * rads[0] * math.sin(ca), side, rads[0] * math.cos(ca)))
        rings.insert(0, [bm.verts.new(pts[0] - t * rads[0])])
    for i, p in enumerate(pts):
        rings.append(ring(p, frames[i][1], rads[i]))
    if caps:
        t, side = frames[-1]
        for a in (30, 55, 75):
            ca = math.radians(a)
            rings.append(ring(pts[-1] + t * rads[-1] * math.sin(ca), side, rads[-1] * math.cos(ca)))
        rings.append([bm.verts.new(pts[-1] + t * rads[-1])])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[k])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[k], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if not caps:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        c = f.calc_center_median()
        f.material_index = mat_of(E(c.x), S(c.y))
        f.smooth = True
    return faces


def cylinder(bm, e, s, z0, z1, r_px, mat, sides=10):
    """A vertical post at pixel position (e, s) from z0 to z1."""
    c = Vector((X(e), Y(s), 0))
    r = r_px * PX
    bot = [bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z0)))
           for k in range(sides)]
    top = [bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z1)))
           for k in range(sides)]
    fs = [bm.faces.new(list(reversed(bot))), bm.faces.new(top)]
    for k in range(sides):
        j = (k + 1) % sides
        fs.append(bm.faces.new((bot[k], bot[j], top[j], top[k])))
    for f in fs:
        f.material_index = mat
        f.smooth = len(f.verts) == 4
    return fs


def offset_poly(poly, d):
    """Offset a CCW polygon [(x, y)] outward by d (miter)."""
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        n0 = Vector(((b - a).y, -(b - a).x)).normalized()
        n1 = Vector(((c - b).y, -(c - b).x)).normalized()
        m = (n0 + n1)
        m = m.normalized() / max(0.3, m.normalized().dot(n0)) if m.length > 1e-6 else n0
        out.append(tuple(b + m * d))
    return out


def ccw(poly):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return poly if area > 0 else list(reversed(poly))


def stack_prism(bm, poly, layers, mat, top_mat=None, bottom=True, top=True):
    """A prism through rings of the plan polygon: layers [(z, offset_units)], bottom to top. Side
    faces between consecutive rings; caps on the first and last ring."""
    poly = ccw(poly)
    rings = [[bm.verts.new((x, y, z)) for x, y in (offset_poly(poly, d) if d else poly)] for z, d in layers]
    n = len(poly)
    fs = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            fs.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for f in fs:
        f.material_index = mat
        f.smooth = False
    if bottom:
        fb = bm.faces.new(list(reversed(rings[0])))
        fb.material_index = mat
    if top:
        ft = bm.faces.new(rings[-1])
        ft.material_index = top_mat if top_mat is not None else mat
    return rings


# --- the sign ----------------------------------------------------------------------------------

def panel_plan():
    """Cabinet plan in pixel-edge coords (e, s)."""
    return [(2.0, 14.0), (4.1, 14.0), (4.1, 14.85), (4.9, 14.85), (4.9, 14.0), (29.0, 14.0), (29.0, 12.1),
            (33.0, 12.1), (33.0, 15.55), (33.4, 16.0), (35.15, 16.0), (35.15, 21.1), (34.3, 22.0),
            (2.8, 22.0), (2.8, 20.6), (2.0, 20.0)]


def merged_sprite():
    data = common.load_sprite(WT, "newshk-121")
    data["colors"].update(common.load_sprite(WT, "newshk-123")["colors"])
    return data


def set_spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = level


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshk121a"
    mats, index_of = [], {}

    def pal(i, **kw):
        key = (i, tuple(sorted(kw.items())))
        if key not in index_of:
            m = common.palette_material(sprite, i, tag + (f"g{round(kw['emission_strength'] * 100)}" if kw.get("emission_strength") else ""), **kw)
            index_of[key] = len(mats)
            mats.append(m)
        return index_of[key]

    PANEL = pal(32, metallic=0.3, roughness=0.55)
    set_spec(mats[PANEL], 0.25)

    def glow(i, s=0.9):
        return pal(i, metallic=1.0, roughness=0.55, emission_strength=s)

    bm = bmesh.new()

    # Cabinet: face chamfer, a panel-line groove round the sides, a closed bottom; a smaller rear
    # box underneath (the transformer housing), closed.
    plan = [(X(e), Y(s)) for e, s in panel_plan()]
    g0, g1, gd = GROOVE
    stack_prism(bm, plan, [(Z_BOT, -0.012), (Z_BOT + 0.012, 0.0), (g0, 0.0), (g0 + 0.006, -gd),
                           (g1 - 0.006, -gd), (g1, 0.0), (Z_TOP - BEVEL, 0.0), (Z_TOP, -BEVEL)], PANEL)
    box = [(X(e), Y(s)) for e, s in [(5, 15.5), (31, 15.5), (31, 20.5), (5, 20.5)]]
    stack_prism(bm, box, [(-0.07, -0.01), (-0.06, 0.0), (Z_BOT + 0.01, 0.0)], PANEL, top=False)
    # Bolt heads on the screen-bottom face (the face the tilted camera sees) and the top face.
    for e in (4.0, 12.0, 20.0, 28.0, 33.6):
        for s_face, sign in ((22.0, 1), (14.0, -1)):
            if s_face == 14.0 and e > 31:
                continue
            c = Vector((X(e), Y(s_face) - sign * 0.004, (g1 + Z_TOP - BEVEL) / 2 + 0.008))
            before = set(bm.faces)
            res = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
            for v in res["verts"]:
                co = v.co.copy()
                v.co = c + Vector((co.x * 0.018, co.y * 0.012, co.z * 0.018))
            for f in set(bm.faces) - before:
                f.material_index = PANEL
                f.smooth = True

    # Neon tubes: one even glow colour per tube run, the measured region median (pal 197 for the
    # letters, underline, bracket and arrow). The sprite's row ramp, the underline's pulse and the
    # arrowhead's radial ramp are its lighting and glow falloff (art rule 2): sheen and lighting
    # make that gradient here, not paint.
    TUBE = glow(197, 0.9)

    def letter_mat(e, s):
        return TUBE

    for stroke in LETTERS:
        path = fillet([(c + 0.5, r + 0.5, R_L) for c, r in stroke], rad=0.42)
        tube(bm, path, Z_T, letter_mat, sides=10)
        # The tube dives into the cabinet at both ends (electrode back-bends), and a clear standoff
        # holds it mid-stroke; both hide under the tube from above.
        for (e, s, _), (e2, s2, _) in ((path[0], path[3]), (path[-1], path[-4])):
            d = Vector((e2 - e, s2 - s))
            d = d.normalized() * 0.35 if d.length > 1e-6 else d
            pe, ps = e + d.x, s + d.y
            if ps > 14.15:
                cylinder(bm, pe, ps, Z_TOP - 0.01, Z_T, R_L * 0.85, letter_mat(pe, ps))

    # Underline, bracket and arrow: one run of tube.
    def run_mat(e, s):
        return TUBE

    run = fillet(RUN, rad=0.4)
    tube(bm, run, Z_T, run_mat, sides=12)

    def head_mat(e, s):
        return TUBE

    for barb in (HEAD_L, HEAD_R):
        tube(bm, resample(chaikin(barb)), Z_T, head_mat, sides=12)

    # Mounting spine under the arrow (outside the cabinet): a thin black rod below the tube with
    # standoff posts, from the cabinet's top-right corner up to the head.
    z_sp = Z_T - 0.075
    spine = [(35.5, 16.6, 0.28)] + [(e, s_, 0.28) for e, s_, _ in RUN[4:]]
    tube(bm, fillet(spine, rad=0.4), z_sp, lambda e, s: PANEL, sides=8)
    for barb in (HEAD_L, HEAD_R):
        tube(bm, resample(chaikin([(e, s_, 0.26) for e, s_, _ in barb[1:-1]])), z_sp, lambda e, s: PANEL, sides=8)
    for e, s_ in ((35.5, 15.0), (34.6, 12.5), (31.5, 11.5), (28.0, 9.0), (25.6, 5.5), (25.5, 3.0),
                  (23.0, 4.5), (28.0, 4.5)):
        cylinder(bm, e, s_, z_sp, Z_T, 0.24, PANEL, sides=8)
    # The arrowhead's backing plate, its face level with the cabinet's.
    hp = [(X(e), Y(s_)) for e, s_ in HEAD_PLATE]
    stack_prism(bm, hp, [(z_sp - 0.03, -0.006), (z_sp - 0.024, 0.0), (Z_TOP - 0.012, 0.0), (Z_TOP, -0.012)], PANEL)
    # The spine's foot: a short post down into the cabinet's top-right corner.
    cylinder(bm, 35.5, 16.6, Z_TOP - 0.01, z_sp + 0.02, 0.32, PANEL, sides=8)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, coll


def sealed_copy(coll):
    """The outline shell's source: the cabinet prism up to the tube centres, plus the arrow run and
    head as tubes (no letters' gaps, standoffs or bolts: ink on the silhouette only)."""
    bm = bmesh.new()
    plan = [(X(e), Y(s)) for e, s in panel_plan()]
    stack_prism(bm, plan, [(Z_BOT, 0.0), (Z_T, 0.0)], 0)
    # The letters' tops stand above the cabinet's top edge: a band of the sealed copy there.
    for stroke in LETTERS:
        path = fillet([(c + 0.5, r + 0.5, R_L) for c, r in stroke], rad=0.42)
        tube(bm, path, Z_T, lambda e, s: 0, sides=8)
    tube(bm, fillet(RUN, rad=0.4), Z_T, lambda e, s: 0, sides=10)
    for barb in (HEAD_L, HEAD_R):
        tube(bm, resample(chaikin(barb)), Z_T, lambda e, s: 0, sides=10)
    stack_prism(bm, [(X(e), Y(s)) for e, s in HEAD_PLATE], [(Z_TOP - 0.06, 0.0), (Z_T, 0.0)], 0)
    mesh = bpy.data.meshes.new(NAME + "_sealed")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(NAME + "_sealed", mesh)
    coll.objects.link(obj)
    return obj


def shell_from(sealed, coll, voxel=0.01, faces=4000, smooth=4):
    shell = sealed.copy()
    shell.data = sealed.data.copy()
    shell.name = NAME + "_outline"
    coll.objects.link(shell)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    common._apply_modifiers(shell)
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.clear()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    return shell


def cut_open(obj, name, cx_px, coll):
    """The part of obj inside a piece's 24 x 28 px box, cut open (no cap), moved to its origin."""
    x0 = cx_px / 12
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hw, hh = 1.0, 14 / 12
    for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                   ((0, -hh, 0), (0, -1, 0)), ((0, hh, 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    bmesh.ops.translate(bm, vec=(-x0, 0, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in obj.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o["tyrian_outline"] = True
    return o


def islands(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen, n = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1
        stack = [v]
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            stack.extend(e.other_vert(x) for e in x.link_edges)
    bm.free()
    return n


# --- measuring ---------------------------------------------------------------------------------

def raycast_grid(obj, k):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mats = [m.name for m in obj.data.materials]
    top = []
    for yy in range(H * k):
        s = (yy + 0.5) / k
        row = []
        for xx in range(W * k):
            e = (xx + 0.5) / k
            hit, *_ = ev.ray_cast(Vector((X(e), Y(s), 5.0)), Vector((0, 0, -1)))
            row.append(bool(hit))
        top.append(row)
    pal = [[None] * W for _ in range(H)]
    hgt = [[0.0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            hit, loc, nrm, fi = ev.ray_cast(Vector((X(c + 0.5), Y(r + 0.5), 5.0)), Vector((0, 0, -1)))
            if hit:
                pal[r][c] = int(mats[obj.data.polygons[fi].material_index].split("_")[1])
                hgt[r][c] = loc.z
    return top, pal, hgt


def measure(obj):
    k = 8
    top, pal, hgt = raycast_grid(obj, k)
    out = {"whole": SM.measure(MASKS, top)}
    g = [[sum(top[r * k + j][c * k + i] for j in range(k) for i in range(k)) / (k * k) >= 0.5
          for c in range(W)] for r in range(H)]
    diff = []
    for r in range(H):
        line = ""
        for c in range(W):
            s, m, fr = INNER[r][c], g[r][c], MASKS["free"][r][c]
            line += ("#" if s and m else "-" if s else "+" if m and not fr else "f" if fr and m else
                     "o" if MASKS["outer"][r][c] else ".")
        diff.append(line)
    out["diff"] = diff
    # Per-pixel colour: the model's top index at each green sprite pixel vs the sprite's index.
    green = [(r, c) for r in range(H) for c in range(W) if _idx[r][c] >= 193]
    exact = sum(pal[r][c] == _idx[r][c] for r, c in green)
    near = sum(pal[r][c] is not None and pal[r][c] >= 193 and abs(pal[r][c] - _idx[r][c]) <= 2 for r, c in green)
    dark_ok = sum(pal[r][c] == 32 for r in range(H) for c in range(W) if _idx[r][c] == 32 and INNER[r][c])
    dark_n = sum(1 for r in range(H) for c in range(W) if _idx[r][c] == 32 and INNER[r][c])
    regions = {"letters": (2, 33, 13, 19), "underline": (2, 33, 21, 21), "bracket": (35, 35, 13, 19),
               "shaft": (25, 34, 6, 11), "head": (20, 30, 1, 6)}
    col = {}
    for n, (c0, c1, r0, r1) in regions.items():
        sp = sorted(_idx[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if _idx[r][c] >= 193)
        md = Counter(pal[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                     if _idx[r][c] >= 193 and pal[r][c] is not None)
        col[n] = {"sprite_median": sp[len(sp) // 2] if sp else None, "model": md.most_common(4)}
    out["colour"] = {"green_exact": f"{exact}/{len(green)}", "green_within2": f"{near}/{len(green)}",
                     "dark_field_32": f"{dark_ok}/{dark_n}", "regions": col}
    out["max_height"] = max(max(r) for r in hgt)
    return out, pal, hgt


# --- review renders ----------------------------------------------------------------------------

def setup_render():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.30, 0.33, 0.36, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = Vector((6, 8.4, -20)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    fill.rotation_euler = Vector((-0.4, -0.6, -0.4)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def render_views(obj, out):
    out.mkdir(parents=True, exist_ok=True)
    scene, cam = setup_render()
    cx, cy = X(18.5), Y(11.5)
    c = Vector((cx, cy, 0.15))

    def look(loc, target=c):
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()

    def shoot(name, w, h, ortho=None, lens=50):
        scene.render.resolution_x, scene.render.resolution_y = w, h
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
        cam.data.clip_end = 100
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    cam.location = (cx, cy, 10)
    cam.rotation_euler = (0, 0, 0)
    shoot("top", 900, 620, ortho=3.4)
    look((cx, cy - 12, 0.2), (cx, cy, 0.2))
    shoot("front", 900, 300, ortho=3.4)       # the screen-bottom face
    look((cx, cy + 12, 0.2), (cx, cy, 0.2))
    shoot("rear", 900, 300, ortho=3.4)
    look((cx - 12, cy, 0.2), (cx, cy, 0.2))
    shoot("side", 700, 300, ortho=2.6)        # the left end
    look((cx + 12, cy, 0.2), (cx, cy, 0.2))
    shoot("side_r", 700, 300, ortho=2.6)
    look((cx - 3.2, cy - 3.4, 2.6))
    shoot("q_front", 900, 600, lens=50)
    look((cx + 3.4, cy + 2.6, 2.4))
    shoot("q_rear", 900, 600, lens=50)
    a = math.radians(15)
    look((cx, cy - 22 * math.sin(a), 22 * math.cos(a)))
    shoot("game", 900, 620, lens=135)
    look((cx - 2.6, cy - 3.0, 0.7))
    shoot("low", 900, 520, lens=50)
    cam.location = (cx, cy, -10)
    cam.rotation_euler = (math.pi, 0, 0)
    shoot("under", 900, 620, ortho=3.4)


# --- main --------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sprite = merged_sprite()
    obj, coll = build(sprite)
    report = {"tris": sum(len(p.vertices) - 2 for p in obj.data.polygons)}
    HERE = None  # --measure output folder
    if "--measure" in argv:
        i = argv.index("--measure")
        HERE = Path(argv[i + 1]) if i + 1 < len(argv) and not argv[i + 1].startswith("--") \
            else Path(tempfile.mkdtemp(prefix="nshk121_measure_"))
        HERE.mkdir(parents=True, exist_ok=True)
        print("MEASURE_DIR", HERE)
        m, pal, hgt = measure(obj)
        report.update(m)
        (HERE / "pal.json").write_text(json.dumps({"pal": pal, "hgt": hgt}))
    sealed = sealed_copy(coll)
    shell = shell_from(sealed, coll)
    layout = [(n, cx, 0) for n, cx in PIECES]
    pieces = common.split_assembly(obj, layout, coll)
    exported, info = [], {}
    for name, cx in PIECES:
        p = pieces[name]
        sh = cut_open(shell, f"{name}_outline", cx, coll)
        info[name] = {"tris": sum(len(q.vertices) - 2 for q in p.data.polygons),
                      "parts": islands(p), "shell_islands": islands(sh),
                      "shell_faces": len(sh.data.polygons)}
        assert len(sh.data.polygons) > 0, f"{name}: empty outline shell"
        exported.append((p, sh, cx))
    report["pieces"] = info
    for p, sh, cx in exported:
        data = common.load_sprite(WT, p.name)
        common.export_sprite_model(WT, [p, sh], f"enemies/{p.name}", data["sprites"])
    if "--measure" in argv:
        for o in coll.objects:
            o.hide_render = o is not obj
        render_views(obj, HERE / "views")
        (HERE / "report.json").write_text(json.dumps(report, indent=1))
    print("REPORT", json.dumps({k: v for k, v in report.items() if k != "diff"}))
    print("\n".join(report.get("diff", [])))


if __name__ == "__main__":
    main()
