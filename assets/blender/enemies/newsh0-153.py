"""Violet cross pod (newsh0.shp frames 153, 155, 157), a hard-surface hover pod that is
its sprite in 3D. Sibling of batch 2's newsh0-125 armoured hover pod (same build and style).

What it is: a small flyer of BOTANY B (2.11, ground layer scroll 1). Most spawns swoop on
right-angle 2 px/tick patrols (ev19 links), often paired at dx +-24 with 153/229, so it hovers:
a round closed belly, centred near z = 0, not a ground emplacement. Symmetric, no facing.

Read from the sprite (inner mask 17 x 17 px round the centre pixel col 12 / row 13):
  - a round saucer body of radius 7 px (rows 7-19, cols 5-19);
  - its top split into four rounded armour quarters by a cross seam 1 px wide (col 12, row 13,
    dark 83-86 from rim to rim);
  - a knob N/S/E/W (5 px wide, 2 px past the body: rows 5-6 / 20-21, cols 4-5 / 19-20) on a
    darker collar (row 7 / 19: 86): built as short emitter stubs with a domed cap;
  - a core at the cross. The frames only charge it: dim (153), a red diamond (155: 118 / 116 /
    114 two px out along the seam), hot (157: 123 / 120 core, the seam glowing 117 -> 116 -> 115
    four px out each way). One body; the core and seam glows are frame parts.

Palette index per region (sprite median, darkest shading and brightest sheen ignored): checked
by --measure. Texture: AO/roughness bake only (no foil), outline shell from a sealed copy (D51/D90).

Run: blender --background --factory-startup --python newsh0-153.py -- [--no-bake] [--out X.glb]
                                                                    [--measure m.json] [--render DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "newsh0-153"
FRAMES = (153, 155, 157)
PX = 1 / 12
AXU = 12.5   # axis of symmetry: the centre of column 12 (column edge 12.5)
CY = 13.5    # the centre of row 13 (row edge 13.5); y below is a row edge, down the screen

(QUARTER, KNOB, COLLAR, RIM, CHASSIS, SEAM, CAP, LENS, BOLT,
 G5_RIM, G5_MID, G5_HEART, G7_115, G7_116, G7_117, G7_CORE, G7_HEART) = range(17)
MATS = {
    QUARTER: (88, 0.3, 0.34, 0.0),   # the four armour quarters (trimmed medians 88-89)
    KNOB: (89, 0.3, 0.32, 0.0),      # knob heads (rows 5-6 / 20-21, cols 4-5 / 19-20: 88-90)
    COLLAR: (86, 0.35, 0.4, 0.0),    # knob collars (row 7 / 19: 86)
    RIM: (86, 0.35, 0.4, 0.0),       # the saucer's rim band
    CHASSIS: (83, 0.4, 0.5, 0.0),    # belly (underside: plain closed shape)
    SEAM: (84, 0.4, 0.5, 0.0),       # the seam floor between the quarters (83-86)
    CAP: (87, 0.35, 0.36, 0.0),      # knob end caps
    LENS: (85, 0.6, 0.3, 0.0),       # frame 153: the dim core
    BOLT: (86, 0.45, 0.4, 0.0),      # bolts
    # glows (D126: strength 1 = the palette colour unlit; D173: glow surfaces metallic 1, rough)
    G5_RIM: (114, 1.0, 0.85, 1.0),   # frame 155: the diamond's tips along the seam
    G5_MID: (116, 1.0, 0.85, 1.0),   # its ring
    G5_HEART: (118, 1.0, 0.85, 1.0), # its centre
    G7_115: (115, 1.0, 0.85, 1.0),   # frame 157: the seam 4 px out
    G7_116: (116, 1.0, 0.85, 1.0),   # 3 px out
    G7_117: (117, 1.0, 0.85, 1.0),   # 1-2 px out
    G7_CORE: (120, 1.0, 0.85, 1.0),  # the core
    G7_HEART: (123, 1.0, 0.85, 1.2), # its yellow heart
}
GLOW = tuple(range(9, 17))
# Light steel, as newsh0-125 fix round 1: metallic 0.3 keeps the palette violet's value, the F0 of
# IOR 2.0 through Specular IOR Level (D176) gives the crowns a white sheen like the sprite's 93-95.
STEEL = (QUARTER, KNOB, CAP)
STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)
TINT = (0.97, 0.985, 1.0)

# --- geometry helpers (sprite px: xr from the axis, y = sprite row edge, down the screen, z up) ----

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, vs, mat):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        return f


def ring(cx, y, hw, zb, zt, n=20, p=2.6, pb=None, hwb=None):
    """A superellipse section (x-z) at row y: half width hw (hwb at the bottom), from zb to zt."""
    pb = p if pb is None else pb
    hwb = hw if hwb is None else hwb
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        e = p if s >= 0 else pb
        w = hw if s >= 0 else hwb
        x = cx + w * math.copysign(abs(c) ** (2 / e), c)
        z = zc + hh * math.copysign(abs(s) ** (2 / e), s)
        pts.append((x, y, z))
    return pts


def loft(m, rings, mat, mats=None):
    """Closed tube through rings (lists of xyz with the same count), capped both ends."""
    vr = [[m.bm.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for k, (a, b) in enumerate(zip(vr, vr[1:])):
        mk = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mk)
    m.face(vr[0], mats[0] if mats else mat)
    m.face(list(reversed(vr[-1])), mats[-1] if mats else mat)
    return vr


def hull(m, pts, mat):
    """Convex hull of points (chamfered blocks)."""
    bm = m.bm
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch, z1b=None, chz=None):
    """Corner points of a chamfered box; the top may slope from z1 (y0 end) to z1b (y1 end)."""
    chz = ch if chz is None else chz
    z1b = z1 if z1b is None else z1b
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for zz, sz in ((z0, 1), (None, -1)):
                if zz is None:
                    zz = z1 if y == y0 else z1b
                pts += [(x + sx * ch, y, zz + sz * chz), (x, y + sy * ch, zz + sz * chz), (x + sx * ch, y + sy * ch, zz)]
    return pts


def dome(m, cx, cy, rx, ry, z0, h, mat, n=16, k=5, p=2.2, base=0.0):
    """A closed dome: superellipse plan rx x ry at z0 (with a short vertical skirt `base`), rising h."""
    rings = []
    if base > 0:
        rings.append([(cx + x, cy + y, z0 - base) for x, y in _plan(rx, ry, n, p)])
    for i in range(k + 1):
        phi = (math.pi / 2) * i / (k + 1)
        s = math.cos(phi)
        rings.append([(cx + x * s, cy + y * s, z0 + h * math.sin(phi)) for x, y in _plan(rx, ry, n, p)])
    vr = [[m.bm.verts.new(q) for q in r] for r in rings]
    apex = m.bm.verts.new((cx, cy, z0 + h))
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mat)
    for i in range(n):
        j = (i + 1) % n
        m.face((vr[-1][i], vr[-1][j], apex), mat)
    m.face(list(reversed(vr[0])), mat)


def _plan(rx, ry, n, p):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((rx * math.copysign(abs(c) ** (2 / p), c), ry * math.copysign(abs(s) ** (2 / p), s)))
    return out


def cyl(m, p0, p1, r, mat, n=8, r1=None):
    """A capped cylinder (or cone, r1) from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.to_track_quat("Z", "Y")
    rot = q.to_matrix().to_4x4()
    mid = (p0 + p1) / 2
    res = bmesh.ops.create_cone(m.bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                                radius2=r if r1 is None else r1, depth=d.length,
                                matrix=Matrix.Translation(mid) @ rot)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def mirror(fn):
    for s in (-1, 1):
        fn(s)




# --- the pod (u: px east of the axis, v: px north of the centre, z: px up) ----------------------

def P(u, v, z):
    return (u, CY - v, z)


def rot(u, v, k):
    """Rotate (u, v) by k quarter turns counter-clockwise (from above)."""
    for _ in range(k % 4):
        u, v = -v, u
    return u, v


R_BODY = 7.1      # saucer wall radius (the inner mask's round rim, rows 7-19)
R_Q = 7.0         # armour quarters' outer radius
G = 0.55          # half width of the cross seam (col 12 / row 13)
RC = 0.75         # quarter corner rounding
Z_FLOOR = 3.05    # seam floor (the saucer's top deck)


def quarter_poly(d, n_arc=28):
    """The NE quarter's plan inset by d: convex, so erode its core by e = max(RC, d) and dilate it
    back by e - d (round corners of radius RC - d, sharp once d passes RC)."""
    e = max(RC, d)
    a = G + e
    rr = R_Q - e
    top = math.sqrt(max(rr * rr - a * a, 1e-6))
    core = [(a, a), (top, a)]
    t0, t1 = math.atan2(a, top), math.atan2(top, a)
    for i in range(1, n_arc):
        t = t0 + (t1 - t0) * i / n_arc
        core.append((rr * math.cos(t), rr * math.sin(t)))
    core.append((a, top))
    rho = e - d
    if rho <= 1e-6:
        return core
    out = []
    m = len(core)
    for i in range(m):
        p0, p1, p2 = core[i - 1], core[i], core[(i + 1) % m]
        n0 = _normal(p0, p1)
        n1 = _normal(p1, p2)
        a0, a1 = math.atan2(n0[1], n0[0]), math.atan2(n1[1], n1[0])
        while a1 < a0:
            a1 += 2 * math.pi
        steps = max(1, int((a1 - a0) / math.radians(12)))
        for s in range(steps + 1):
            t = a0 + (a1 - a0) * s / steps
            out.append((p1[0] + rho * math.cos(t), p1[1] + rho * math.sin(t)))
    return out


def _normal(p, q):
    """Outward normal of edge p->q of a counter-clockwise polygon."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    ln = math.hypot(dx, dy) or 1.0
    return (dy / ln, -dx / ln)


QC = (R_Q + G) / (1 + math.sqrt(2))   # the quarter's in-centre lies on the diagonal at (QC, QC)


def ray_ring(poly, n=40):
    """n boundary points of a convex polygon by rays from the in-centre at even angles."""
    cx = cy = QC
    pts = []
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        dx, dy = math.cos(t), math.sin(t)
        best = None
        for j in range(len(poly)):
            (x0, y0), (x1, y1) = poly[j], poly[(j + 1) % len(poly)]
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            s = ((x0 - cx) * ey - (y0 - cy) * ex) / den
            w = ((x0 - cx) * dy - (y0 - cy) * dx) / den
            if s > 0 and -1e-9 <= w <= 1 + 1e-9 and (best is None or s < best):
                best = s
        pts.append((cx + best * dx, cy + best * dy))
    return pts


# quarter profile: a vertical wall and an even chamfer (inset rings of the plan), then a smooth
# crown: the chamfer's top ring scaled toward the in-centre, rising to a low rounded top (the
# sprite's four rounded quarters; no skeleton ridges)
Q_WALL = [(0.0, 2.6), (0.0, 3.35), (0.18, 3.6), (0.45, 3.78)]
Q_CROWN = 0.78                     # crown rise above the chamfer's top ring
Q_LAM = [0.86, 0.7, 0.52, 0.32, 0.14]


def q_z(d):
    """Height of the quarter's top at inset d from its plan edge (bolts sit on it)."""
    d0 = Q_WALL[-1][0]
    if d <= d0:
        return Q_WALL[-1][1]
    lam = max(0.0, 1 - (d - d0) / (2.55 - d0))
    return Q_WALL[-1][1] + Q_CROWN * (1 - lam ** 2)


def build_quarter(m, k):
    rings = []
    for d, z in Q_WALL:
        rings.append([(u, v, z) for u, v in ray_ring(quarter_poly(d))])
    top = rings[-1]
    zt = Q_WALL[-1][1]
    for lam in Q_LAM:
        rings.append([(QC + (u - QC) * lam, QC + (v - QC) * lam, zt + Q_CROWN * (1 - lam ** 2)) for u, v, _ in top])
    rings = [[P(*rot(u, v, k), z) for u, v, z in r] for r in rings]
    vr = [[m.bm.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), QUARTER)
    apex = m.bm.verts.new(P(*rot(QC, QC, k), zt + Q_CROWN))
    for i in range(n):
        m.face((vr[-1][i], vr[-1][(i + 1) % n], apex), QUARTER)
    m.face(list(reversed(vr[0])), QUARTER)
    # machined detail: two hex bolts on the outer shoulder
    for ang in (27.0, 63.0):
        r = R_Q - 0.95
        u, v = rot(r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)), k)
        z = q_z(0.95)
        cyl(m, P(u, v, z - 0.3), P(u, v, z + 0.07), 0.24, BOLT, n=6)


def circle(r, z, n=48, phase=0.5):
    return [P(r * math.cos(2 * math.pi * (i + phase) / n), r * math.sin(2 * math.pi * (i + phase) / n), z)
            for i in range(n)]


# the saucer: a closed round hull; the belly a plain shallow dome (underside: no detail)
SAUCER = [(1.8, 0.2, CHASSIS), (3.8, 0.45, CHASSIS), (5.4, 0.9, CHASSIS), (6.5, 1.5, CHASSIS),
          (7.0, 2.0, RIM), (R_BODY, 2.3, RIM), (R_BODY, 2.75, RIM), (6.95, 2.95, SEAM),
          (6.7, Z_FLOOR, SEAM)]


def build_saucer(m):
    rings = [circle(r, z) for r, z, _ in SAUCER]
    mats = [mt for _, _, mt in SAUCER[:-1]] + [SEAM]
    loft(m, rings, CHASSIS, mats=mats)


# knob stubs N/E/S/W: (s along the arm, half width, half height, material of the band after it)
ZK = 2.55
KNOB_ST = [(4.9, 1.95, 1.55, COLLAR), (6.0, 2.1, 1.66, COLLAR), (6.45, 2.1, 1.66, SEAM),
           (6.55, 1.95, 1.5, SEAM), (6.66, 1.95, 1.5, KNOB), (6.84, 2.45, 1.85, KNOB)]
# the head's rounded end: a superellipse (p = 3) dome from s = 7.55 to the tip at 8.48
for _i in range(1, 8):
    _t = _i / 8
    _f = (1 - _t ** 3) ** (1 / 3)
    KNOB_ST.append((7.55 + 0.93 * _t, 2.45 * _f, 1.85 * _f, KNOB))
KNOB_ST.insert(6, (7.55, 2.45, 1.85, KNOB))


def knob_ring(k, s, w, h, n=20, p=2.6):
    pts = []
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        c, sn = math.cos(t), math.sin(t)
        lat = w * math.copysign(abs(c) ** (2 / p), c)
        z = ZK + h * math.copysign(abs(sn) ** (2 / p), sn)
        u, v = rot(lat, s, k)   # k = 0: north arm, lateral along u
        pts.append(P(u, v, z))
    return pts


def build_knob(m, k):
    rings = [knob_ring(k, s, w, h) for s, w, h, _ in KNOB_ST]
    mats = [mt for *_, mt in KNOB_ST[:-1]] + [KNOB]
    vr = loft(m, rings, KNOB, mats=mats)
    # close the tip with a point instead of a flat cap
    last = vr[-1]
    f = m.bm.faces.get(list(reversed(last))) or m.bm.faces.get(last)
    if f is not None:
        m.bm.faces.remove(f)
    u, v = rot(0.0, 8.5, k)
    tip = m.bm.verts.new(P(u, v, ZK))
    for i in range(len(last)):
        m.face((last[i], last[(i + 1) % len(last)], tip), KNOB)


def build_body():
    m = Mesh()
    build_saucer(m)
    for k in range(4):
        build_quarter(m, k)
        build_knob(m, k)
    return m


def strip(m, a, b, mat, k, w=0.42, z0=Z_FLOOR - 0.05, z1=Z_FLOOR + 0.28):
    """A glowing bar in the seam floor, from a to b px out along arm k."""
    u0, v0 = rot(-w, a, k)
    u1, v1 = rot(w, b, k)
    x0, x1 = sorted((u0, u1))
    ya, yb = sorted((CY - v0, CY - v1))
    hull(m, cbox(x0, x1, ya, yb, z0, z1, 0.03), mat)


def build_core(frame):
    m = Mesh()
    z0 = Z_FLOOR - 0.05
    if frame == 153:
        dome(m, 0.0, CY, 1.25, 1.25, z0, 0.95, LENS, n=20, k=4, p=2.0)
    elif frame == 155:
        dome(m, 0.0, CY, 1.4, 1.4, z0, 1.0, G5_MID, n=20, k=4, p=2.0)
        dome(m, 0.0, CY, 0.7, 0.7, z0, 1.12, G5_HEART, n=14, k=4, p=2.0)
        for k in range(4):
            strip(m, 1.2, 2.5, G5_RIM, k)
    else:
        dome(m, 0.0, CY, 1.45, 1.45, z0, 1.05, G7_CORE, n=20, k=4, p=2.0)
        dome(m, 0.0, CY, 0.68, 0.68, z0, 1.18, G7_HEART, n=14, k=4, p=2.0)
        for k in range(4):
            strip(m, 1.2, 2.5, G7_117, k)
            strip(m, 2.5, 3.5, G7_116, k)
            strip(m, 3.5, 4.5, G7_115, k)
    return m

def to_object(m, name, mats, coll, sharp=32):
    bm = m.bm
    # sprite px -> Blender units: X = (x + 0.5) / 12, Y = (14 - y) / 12, Z = z / 12
    T = Matrix(((PX, 0, 0, (AXU - 12) * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                          ngon_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp))
    return obj


def materials(sprite):
    out = []
    for i in range(len(MATS)):
        pal, met, rough, em = MATS[i]
        tag = f"{NAME}_A_{i}"
        mt = common.palette_material(sprite, pal, tag, metallic=met, roughness=rough, emission_strength=em)
        if i in STEEL:
            bsdf = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
        out.append(mt)
    return out

# --- bake (AO + edge lift, roughness/metal), after usp_talon.bake_maps / newshe-155 ----------------

def bake_maps(obj, out_dir, prefix, textured, size=512, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{prefix}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{prefix}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    b0 = next(n for n in me.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for img, c in ((col_img, (*TINT, 1.0)),
                   (rm_img, (1.0, b0.inputs["Roughness"].default_value, b0.inputs["Metallic"].default_value, 1.0))):
        img.pixels.foreach_set([v for _ in range(img.size[0] * img.size[1]) for v in c])
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.15)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.12)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=16, margin_type="EXTEND", use_clear=False)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    # per-object copies of the materials, so each frame wires its own maps
    for i in textured:
        m = mats[i].copy()
        me.materials[i] = m
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- measure -----------------------------------------------------------------------------------

def measure(frame_objs, sprite, sub=8):
    import sprite_mask as SM
    from mathutils.bvhtree import BVHTree
    res = {}
    W, H = 24, 28
    for frame, objs in frame_objs.items():
        fr = next(f for f in sprite["frames"] if f["index"] == frame)
        pix = fr["pixels"]
        bm = bmesh.new()
        offs = []
        for o in objs:
            tmp = bmesh.new()
            tmp.from_mesh(o.data)
            tmp.transform(o.matrix_world)
            me = bpy.data.meshes.new("m_tmp")
            tmp.to_mesh(me)
            tmp.free()
            offs.append((len(bm.faces), o))
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        bm.faces.ensure_lookup_table()
        tree = BVHTree.FromBMesh(bm)
        fmat = [f.material_index for f in bm.faces]
        top = [[False] * (W * sub) for _ in range(H * sub)]
        regions = {}
        for r in range(H):
            for c in range(W):
                counts = {}
                for j in range(sub):
                    for i in range(sub):
                        u, v = c + (i + 0.5) / sub, r + (j + 0.5) / sub
                        hit = tree.ray_cast(Vector(((u - 12) * PX, (14 - v) * PX, 5.0)), Vector((0, 0, -1)), 20.0)
                        if hit[0] is not None:
                            top[r * sub + j][c * sub + i] = True
                            counts[fmat[hit[2]]] = counts.get(fmat[hit[2]], 0) + 1
                if sum(counts.values()) >= sub * sub / 2 and pix[r][c] >= 0:
                    mi = max(counts, key=counts.get)
                    regions.setdefault(mi, []).append(pix[r][c])
        bm.free()
        idx, colors = SM.load(NAME, frame)
        mk = SM.masks(idx, colors)
        meas = SM.measure(mk, top)
        reg = {}
        for mi, vals in regions.items():
            pal = MATS[mi][0]
            sv = sorted(vals)
            lo, hi = len(sv) // 6, len(sv) - len(sv) // 6
            trimmed = sv[lo:hi] or sv
            reg[f"{mi}:pal{pal}"] = {"n": len(vals), "median_trim": trimmed[len(trimmed) // 2], "pixels": sv}
        grid = ["".join("#" if sum(top[r * sub + j][c * sub + i] for j in range(sub) for i in range(sub)) >= sub * sub / 2
                        else "." for c in range(W)) for r in range(H)]
        res[frame] = {**meas, "regions": reg, "top": grid}
    return res


# --- renders ------------------------------------------------------------------------------------

def _camera(name, loc, look, ortho=None, lens=None, up_y=False):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens or 50
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = (0, 0, 0) if up_y else d.to_track_quat("-Z", "Y").to_euler()
    return cam


def _render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_all(frame_objs, all_objs, out):
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        sc.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.5, 0.52, 0.58, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.35, 0.5, 1.0)).normalized().to_track_quat("Z", "Y").to_euler()
    gm = bpy.data.meshes.new("ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=3.0)
    bmesh.ops.translate(gbm, vec=(0, 0, -0.35), verts=gbm.verts)   # it hovers: ground well below
    gbm.to_mesh(gm)
    gbm.free()
    ground = bpy.data.objects.new("ground", gm)
    gm.materials.append(common.material("ground_mat", (0.13, 0.12, 0.1), roughness=0.9))
    sc.collection.objects.link(ground)
    C = Vector(((AXU - 12) * PX, (14 - CY) * PX, 0.2))
    views = {
        "top": ((C.x, 0, 10), (C.x, 0, 0), 2.0, None, True),
        "side": ((8, 0, C.z), (0, 0, C.z), 1.7, None, False),
        "front": ((C.x, -8, C.z), (C.x, 0, C.z), 1.7, None, False),
        "rear": ((C.x, 8, C.z), (C.x, 0, C.z), 1.7, None, False),
        "q_front": ((2.4, -2.9, 2.5), tuple(C), None, 60, False),
        "q_rear": ((-2.6, 2.6, 2.3), tuple(C), None, 60, False),
        "under": ((1.2, -1.8, -2.7), tuple(C), None, 55, False),
    }
    tilt = math.radians(32)
    dist = 9.0
    views["game"] = ((C.x, -dist * math.sin(tilt), dist * math.cos(tilt)), (C.x, 0, 0), None, 150, False)
    for frame, objs in frame_objs.items():
        for o in all_objs:
            o.hide_render = o not in objs
        for vn, (loc, look, ortho, lens, upy) in views.items():
            if frame != FRAMES[0] and vn not in ("top", "game", "q_front"):
                continue
            ground.hide_render = vn != "game"
            cam = _camera(f"c_{vn}", loc, look, ortho=ortho, lens=lens, up_y=upy)
            _render(cam, out / f"{vn}-{frame}.png", 480, 480)
        ground.hide_render = False
        cam = _camera("c_small", views["game"][0], views["game"][1], lens=150)
        _render(cam, out / f"gamesmall-{frame}.png", 80, 80)
    print("rendered", out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    body = to_object(build_body(), NAME, mats, coll)
    cores = {f: to_object(build_core(f), f"{NAME}-core-{f}", mats, coll, sharp=80) for f in FRAMES}
    for o in [body, *cores.values()]:
        o.data.calc_loop_triangles()
        print(f"{o.name}: {len(o.data.loop_triangles)} triangles")
    # outline shell from the closed, unbaked body (D51, D90/D118: sealed before anything else)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=900, smooth=6, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bdir = Path(tempfile.mkdtemp(prefix="nsh153_bake_"))
        for o in coll.objects:
            o.hide_render = o is not body
        bake_maps(body, bdir, "pod153A_body", [i for i in MATS if i not in GLOW])
        for o in coll.objects:
            o.hide_render = False
        fmt = "WEBP"
    for f, o in cores.items():
        common.frame_part(o, [f])
    export = [body, shell, *cores.values()]
    if "--out" in argv:
        glb = Path(opt("--out"))
        common.export_glb(export, glb, image_format=fmt)
    else:
        common.export_sprite_model(WT, export, f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    frame_objs = {f: [body, cores[f]] for f in FRAMES}
    if "--measure" in argv:
        res = measure(frame_objs, sprite)
        Path(opt("--measure")).write_text(json.dumps(res, indent=1))
        for f, r in res.items():
            print("MEASURE", f, "iou_rule_grid", r["iou_rule_grid"], "iou_rule", r["iou_rule"],
                  {k: v["median_trim"] for k, v in r["regions"].items()})
    if "--render" in argv:
        render_all(frame_objs, [body, shell, *cores.values()], Path(opt("--render")))


if __name__ == "__main__":
    main()
