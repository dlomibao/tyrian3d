"""assembly-newsh-caret-54, design A: a blue U-shaped flying gun platform (a "tuning fork"),
newsh^.shp 16 | 18 over 54 | 56 (four 24x28 px pieces, one frame each, 48x56 px whole; ICE EXIT 4.8,
BRAINIAC 4.15, ICESECRET 4.20). Units 412-415 drift and weave as one rigid link: one flying craft.

What it is (read from the 48x56 sprite, light from the upper left):
- Two big blue gun pods (the fork's prongs, cols 7-19, rows 1-22) with rounded noses facing up the
  screen. Each has a panel seam (the dark L: col 9 rows 4-11, then row 11 to col 12), a small blister
  on its inner flank (cols 18-19, rows 10-14) and a grey clamp band round its outer side and top
  (rows 17-21) with a mounting lug standing out past the pod (cols 5-6) and a lit front flange
  (row 17). A light-blue coolant pipe runs down the pod's back (col 12), over the clamp, across it
  (row 19) and down off it on the outer side (col 8).
- Below a seam (row 22) each pod runs into a narrower strut (rows 23-30) with a grey actuator
  cylinder on top (cols 12-13) and a long tank on its inner flank (cols 18-20, rows 22-33).
- A dark grey hinge knuckle (rows 31-35) joins the strut to the lower arm (rows 36-44), whose
  inner flank carries the actuator's piston rod (cols 15-16); the arms bend inward into the round
  rear bar (rows 45-52).
- On the bar's middle a turret: a grey ring (rows 45-47) with a dark neck and a split blue gun
  housing (two lobes either side of a dark slot, rows 37-42) pointing up between the prongs;
  two small blue domes sit on the bar beside it (cols 18-20 and 28-30).
The pale streaks (col 14 and col 34 down the pods, the arms' crests, the bar's crest rows 49-50)
are sheen on glossy paint, the ink ring and the dark flanks are lighting: not modelled.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh-caret-54.py
Exports public/models/enemies/newsh-caret-<n>.glb (each piece at its own origin with its outline shell)
and the src/render/spriteModels entries. A build writes nothing else.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "assembly-newsh-caret-54"
PIECES = ["newsh-caret-16", "newsh-caret-18", "newsh-caret-54", "newsh-caret-56"]
# Piece centres relative to the block centre (screen 169, 45): 16/18 at cy 31, 54/56 at cy 59.
LAYOUT = [("newsh-caret-16", -12, -14), ("newsh-caret-18", 12, -14),
          ("newsh-caret-54", -12, 14), ("newsh-caret-56", 12, 14)]
PX = 1 / 12
AXIS = 24.5  # mirror line: the centre of pixel column 24 (pixel-edge units)


def X(u):
    """Pixel-edge column u of the 48x56 block (0 = left edge) to Blender X."""
    return (u - 24) * PX


def Y(v):
    """Pixel-edge row v (0 = top edge) to Blender Y (sprite up = +Y)."""
    return (28 - v) * PX


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys) (Fritsch-Carlson)."""
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
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


# ---- geometry helpers ---------------------------------------------------------------------------

def sp(c, e):
    return math.copysign(abs(c) ** (2.0 / e), c)


def section(w, ht, hb, e_top, e_bot, theta):
    """A superellipse section point: (lateral px, vertical units) at angle theta (0 = +lateral,
    pi/2 = top). The top and bottom halves have their own height and exponent (a fuller top, a
    shallower belly)."""
    c, s = math.cos(theta), math.sin(theta)
    e = e_top if s >= 0 else e_bot
    return w * sp(c, e), (ht if s >= 0 else hb) * sp(s, e)


def chamfer_profile(ft, sh, fb, sb, bev=0.08):
    """A chamfered hull section in normalized units (lateral -1..1, vertical -1..1), counter-clockwise
    from the outer flank: a flat top (half width ft) breaking through a chamfer to the flank at
    height sh, the flank, and a shallower chamfer to a flat belly (fb, sb). Each corner is cut by a
    small bevel (two points), so the shading turns crisply but not razor-sharp."""
    corners = [(1.0, sh), (ft, 1.0), (-ft, 1.0), (-1.0, sh), (-1.0, -sb), (-fb, -1.0), (fb, -1.0), (1.0, -sb)]
    out = []
    n = len(corners)
    for i, c in enumerate(corners):
        p, q = corners[i - 1], corners[(i + 1) % n]
        for a in (p, q):
            d = math.hypot(a[0] - c[0], a[1] - c[1])
            t = min(0.45, bev / d)
            out.append((c[0] + (a[0] - c[0]) * t, c[1] + (a[1] - c[1]) * t))
    return out


def poly_ray(poly, theta):
    """Where a ray from the origin at angle theta leaves a convex normalized profile."""
    dx, dy = math.cos(theta), math.sin(theta)
    best = None
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        ex, ey = x1 - x0, y1 - y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = (x0 * ey - y0 * ex) / den
        s_ = (x0 * dy - y0 * dx) / den
        if t > 0 and -1e-9 <= s_ <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return dx * best, dy * best


def sweep(bm, st, sides=28, cap0=True, cap1=True, e_top=3.0, e_bot=2.2, smooth=True):
    """A loft along a path in the XY plane. st: list of dicts with u, v (centre, pixel edges),
    w (half width, px), zc (centre z), ht / hb (height above / depth below zc, units) and mat (the
    material of the band from this station to the next). Rings stand perpendicular to the path.
    A station with w == 0 is a point (a rounded end). Returns the rings."""
    pts = [Vector((X(s["u"]), Y(s["v"]), 0.0)) for s in st]
    rings = []
    for i, s in enumerate(st):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(Vector((0, 0, 1)))
        if s["w"] <= 0:
            rings.append([bm.verts.new(pts[i] + Vector((0, 0, s["zc"])))])
            continue
        ring = []
        if "ft" in s:
            prof = chamfer_profile(s["ft"], s["sh"], s["fb"], s["sb"], s.get("bev", 0.08))
            for lx, ly in prof:
                up = ly * (s["ht"] if ly >= 0 else s["hb"])
                ring.append(bm.verts.new(pts[i] + side * (lx * s["w"] * PX) + Vector((0, 0, s["zc"] + up))))
        else:
            for k in range(sides):
                th = 2 * math.pi * k / sides
                lat, up = section(s["w"], s["ht"], s["hb"], s.get("et", e_top), s.get("eb", e_bot), th)
                ring.append(bm.verts.new(pts[i] + side * (lat * PX) + Vector((0, 0, s["zc"] + up))))
        rings.append(ring)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        mat = st[i]["mat"]
        fs = []
        if len(r0) == 1 and len(r1) == 1:
            continue
        nk = max(len(r0), len(r1))
        for k in range(nk):
            j = (k + 1) % nk
            if len(r0) == 1:
                fs.append(bm.faces.new((r0[0], r1[k], r1[j])))
            elif len(r1) == 1:
                fs.append(bm.faces.new((r0[k], r0[j], r1[0])))
            else:
                fs.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
        for f in fs:
            f.material_index = mat
            f.smooth = smooth
        if "ft" in st[i] and not st[i].get("soft") and len(r0) > 1 and len(r1) > 1:
            # chamfered sections: every longitudinal edge is a crease (flat facets round the
            # section, smooth along the path)
            for k in range(nk):
                e = bm.edges.get((r0[k], r1[k]))
                if e is not None:
                    e.smooth = False
    if cap0 and len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = st[0]["mat"]
    if cap1 and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.material_index = st[-1]["mat"]
    return rings


def hull(bm, pts, mat, smooth=False):
    """Convex hull of `pts` added to `bm` (coplanar triangles merged), material `mat`."""
    tmp = bmesh.new()
    for p in pts:
        tmp.verts.new(p)
    res = bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    junk = res["geom_interior"] + res["geom_unused"]
    if junk:
        bmesh.ops.delete(tmp, geom=list({g for g in junk if isinstance(g, bmesh.types.BMVert)}), context="VERTS")
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(0.5), verts=tmp.verts[:], edges=tmp.edges[:])
    for f in tmp.faces:
        f.material_index = mat
        f.smooth = smooth
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def cbox(bm, u0, u1, v0, v1, z0, z1, mat, ch=0.4, chz=None):
    """A box over pixel edges u0..u1, v0..v1, z0..z1 with chamfered vertical corners and top and
    bottom edges (`ch` px across, `chz` units)."""
    chz = ch * PX if chz is None else chz
    c = ch * PX
    x0, x1, y0, y1 = X(u0), X(u1), Y(v1), Y(v0)
    pts = []
    for z, inset in ((z0, c), (z0 + chz, 0.0), (z1 - chz, 0.0), (z1, c)):
        a0, a1, b0, b1 = x0 + inset, x1 - inset, y0 + inset, y1 - inset
        pts += [(a0 + c, b0, z), (a1 - c, b0, z), (a1, b0 + c, z), (a1, b1 - c, z),
                (a1 - c, b1, z), (a0 + c, b1, z), (a0, b1 - c, z), (a0, b0 + c, z)]
    hull(bm, pts, mat)


def tube(bm, pts, r, mat, sides=10, caps=True, rz=None):
    """A round tube through 3D points `pts` (Blender coords), radius r (rz: vertical radius)."""
    rz = r if rz is None else rz
    rings = []
    P = [Vector(p) for p in pts]
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        s = t.cross(a).normalized()
        up = s.cross(t).normalized()
        rings.append([bm.verts.new(p + s * (r * math.cos(2 * math.pi * k / sides))
                                   + up * (rz * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mat
            f.smooth = True
    if caps:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = mat
            f.smooth = False
    return rings


def ellipsoid(bm, u, v, z, rx_px, ry_px, rz, mat, segs=20, rings=10, zmin=-1.0):
    """An ellipsoid centred at pixel-edge (u, v), height z; zmin > -1 flattens its bottom (a dome)."""
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=rings, radius=1.0)
    for vv in tmp.verts:
        vv.co.z = max(vv.co.z, zmin)
        vv.co = Vector((X(u) + vv.co.x * rx_px * PX, Y(v) + vv.co.y * ry_px * PX, z + vv.co.z * rz))
    for f in tmp.faces:
        f.material_index = mat
        f.smooth = True
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def mirror_all(bm, axis_u=AXIS):
    """Add the mirror image about the vertical line u = axis_u of everything built so far."""
    ax = X(axis_u)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def boolean_cut(bm, mats, build_target, build_cutters):
    """Build a closed target and cutters in their own meshes, subtract the cutters (EXACT; the cut
    walls take the cutter's material) and append the result to bm."""
    objs = []
    for i, fn in enumerate([build_target] + list(build_cutters)):
        b = bmesh.new()
        fn(b)
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        me = bpy.data.meshes.new(f"_nshc54a_tmp{i}")
        b.to_mesh(me)
        b.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(f"_nshc54a_tmp{i}", me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    target = objs[0]
    for cutter in objs[1:]:
        cutter.hide_render = True
        mod = target.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "EXACT"
        mod.material_mode = "INDEX"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    bm.from_mesh(me)
    for ob in objs:
        old = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(me)


# ---- the prong loft -----------------------------------------------------------------------------

# Stations of the left prong down its centre line: v (row edge), u centre, half width (px), centre z,
# height above and depth below. Pod (rows 1-22), strut (23-30), knuckle neck (31-35), lower arm
# (36-44), then the bend into the bar to the mirror line.
POD = dict(
    v=[0.85, 1.25, 1.9, 2.6, 3.5, 4.5, 5.6, 7.0, 8.6, 10.2, 13.0, 15.5, 17.2, 21.0, 21.9],
    u=[12.1, 12.1, 12.0, 11.9, 11.8, 11.75, 11.6, 11.95, 12.35, 12.55, 12.55, 13.3, 13.0, 13.0, 13.0],
    w=[0.0, 1.55, 2.45, 3.05, 3.6, 4.1, 4.5, 4.85, 5.35, 5.55, 5.55, 5.6, 5.95, 5.95, 5.95],
    ht=[0.0, 0.13, 0.20, 0.25, 0.29, 0.32, 0.35, 0.37, 0.39, 0.40, 0.40, 0.40, 0.40, 0.39, 0.37],
    hb=[0.0, 0.10, 0.15, 0.18, 0.20, 0.22, 0.23, 0.24, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.24],
)
POD_ZC = 0.06
POD_PROF = (0.52, 0.3, 0.55, 0.25)    # chamfered section: flat top, shoulder height, belly, its chamfer
STRUT_PROF = (0.5, 0.3, 0.55, 0.25)
ARM_PROF = (0.45, 0.3, 0.55, 0.25)


def prof(p):
    return dict(zip(("ft", "sh", "fb", "sb"), p))


def prong_stations(M):
    st = []
    zcp = POD_ZC
    for i, v in enumerate(POD["v"]):
        st.append(dict(u=POD["u"][i], v=v, w=POD["w"][i], zc=zcp - 0.02 * (1 - min(1.0, v / 6)) if i else zcp - 0.02,
                       ht=POD["ht"][i], hb=POD["hb"][i], mat=M["pod"], **prof(POD_PROF), soft=v < 5.5,
                       bev=0.08 + 0.3 * max(0.0, 1 - (v - 1.0) / 4.0)))
    # seam groove between the pod and the strut (the dark row 22)
    st[-1]["mat"] = M["seam"]
    st.append(dict(u=13.0, v=22.45, w=5.6, zc=0.05, ht=0.31, hb=0.21, mat=M["seam"], **prof(POD_PROF)))
    st.append(dict(u=13.0, v=22.9, w=5.0, zc=0.05, ht=0.33, hb=0.21, mat=M["strut"], **prof(STRUT_PROF)))
    # strut
    for u, v, w, ht in ((13.05, 24.0, 4.95, 0.33), (13.25, 26.0, 4.75, 0.32), (13.6, 27.8, 4.4, 0.31),
                        (13.9, 29.5, 4.05, 0.30), (13.75, 31.0, 3.5, 0.27)):
        st.append(dict(u=u, v=v, w=w, zc=0.04, ht=ht, hb=0.20, mat=M["strut"], **prof(STRUT_PROF)))
    # neck inside the hinge knuckle (hidden by it)
    st[-1]["mat"] = M["joint"]
    for u, v, w in ((13.2, 33.2, 2.4), (13.1, 35.3, 2.4)):
        st.append(dict(u=u, v=v, w=w, zc=0.03, ht=0.22, hb=0.17, mat=M["joint"], **prof(STRUT_PROF)))
    # lower arm, the bend and the bar to the mirror line: control stations resampled along a smooth
    # (pchip by chord length) centre line so the bend stays fair
    st[-1]["mat"] = M["arm"]
    C = [(13.3, 36.6, 3.0, 0.27), (13.45, 39.0, 3.0, 0.27), (13.75, 42.0, 2.95, 0.27), (14.05, 44.0, 3.05, 0.27),
         (14.85, 45.8, 3.25, 0.27), (16.0, 47.6, 3.6, 0.27), (18.3, 48.5, 3.55, 0.275), (21.0, 48.9, 3.55, 0.28),
         (23.3, 49.15, 3.95, 0.28), (AXIS, 49.15, 3.95, 0.28)]
    sl = [0.0]
    for (u0, v0, *_), (u1, v1, *_) in zip(C, C[1:]):
        sl.append(sl[-1] + math.hypot(u1 - u0, v1 - v0))
    fu, fv, fw, fh = (pchip(sl, [c[k] for c in C]) for k in range(4))
    n = int(sl[-1] / 0.7)
    for i in range(n + 1):
        t = sl[-1] * i / n
        v = fv(t)
        st.append(dict(u=fu(t), v=v, w=fw(t), zc=0.03, ht=fh(t), hb=0.19 + 0.01 * min(1.0, max(0.0, (v - 44) / 4)),
                       mat=M["arm"] if v < 44.6 else M["bar"], **prof(ARM_PROF)))
    st[-1]["u"], st[-1]["v"] = AXIS, 49.15
    st[-2]["v"] = 49.15
    return st


# ---- materials ----------------------------------------------------------------------------------

def materials(sprite):
    tag = "nshc54a"

    def pal(i, metallic, roughness, spec=None, **kw):
        m = common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness, **kw)
        if spec is not None:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    # (key, palette index, metallic, roughness, F0 / Specular IOR Level)
    spec = [
        ("pod", 55, 0.15, 0.34, 0.6),       # glossy painted blue (pod median 55)
        ("blister", 53, 0.15, 0.34, 0.6),
        ("seam", 50, 0.4, 0.55, None),     # panel seams and the gun slot
        ("strut", 52, 0.15, 0.36, 0.6),     # strut / lower arm median 52
        ("arm", 52, 0.15, 0.36, 0.6),
        ("bar", 53, 0.15, 0.34, 0.6),       # bar median 53
        ("tank", 54, 0.15, 0.34, 0.6),      # inner tank median 54
        ("pipe", 59, 0.15, 0.3, 0.7),      # coolant pipe median 59
        ("clamp", 5, 0.6, 0.38, None),     # grey clamp median 5 (satin steel)
        ("flange", 6, 0.6, 0.36, None),    # its lit front flange (row 17 median 6)
        ("rod", 6, 0.6, 0.34, None),      # actuator cylinder (median 6)
        ("piston", 5, 0.6, 0.34, None),   # piston rod down the arm (lit side 5; col 16 is its shaded side, 2-4)
        ("joint", 4, 0.6, 0.42, None),     # hinge knuckle (median 4)
        ("jointcap", 3, 0.55, 0.45, None),
        ("pin", 7, 0.75, 0.32, None),
        ("ring", 4, 0.65, 0.40, None),     # turret ring (collar median 4)
        ("ringlip", 7, 0.7, 0.34, None),   # its lit lip (7/10)
        ("neck", 2, 0.5, 0.5, None),       # dark neck (rows 43-44)
        ("gun", 53, 0.15, 0.32, 0.6),       # split gun housing lobes (median 53, the slot 49-50)
        ("dome", 52, 0.15, 0.34, 0.6),      # bar domes (median 52)
        ("lug", 5, 0.7, 0.40, None),
    ]
    mats, M, seen = [], {}, {}
    for key, idx, met, rough, spc in spec:
        sig = (idx, met, rough, spc)
        if sig not in seen:
            seen[sig] = len(mats)
            mats.append(pal(idx, met, rough, spec=spc))
        M[key] = seen[sig]
    return mats, M


# ---- parts --------------------------------------------------------------------------------------

def pod_section_at(v):
    """(u centre, w, zc, ht, hb) of the pod at row edge v (pchip of the stations)."""
    vs = POD["v"][1:]
    f = {k: pchip(vs, POD[k][1:]) for k in ("u", "w", "ht", "hb")}
    return f["u"](v), f["w"](v), POD_ZC, f["ht"](v), f["hb"](v)


def build_clamp(bm, M):
    """The grey clamp band round the pod's top and outer flank (rows 17-21), its lit front flange
    (row 17) and the mounting lug standing out past the pod (cols 5-6)."""
    v0, v1 = 16.95, 22.0
    u_c, w, zc, ht, hb = pod_section_at(19.5)
    poly = chamfer_profile(*POD_PROF)
    # lateral is measured toward the OUTER side (-X); the band runs from the inner top (2 px
    # inboard of the pod's centre) over the top and down the outer flank to below the equator.
    th0 = math.atan2(1.0, -1.9 / (w + 0.9))
    ths = [th0 + (-0.42 - th0) * k / 26 for k in range(27)]

    def ring(v, grow_px, grow_z):
        out = []
        for th in ths:
            lx, ly = poly_ray(poly, th)
            lat = lx * (w + grow_px)
            up = ly * ((ht if ly >= 0 else hb) + grow_z)
            out.append(Vector((X(u_c) - lat * PX, Y(v), zc + up)))
        return out

    def band(va, vb, t_out, mat_top, mat_side, chamfer=0.35):
        rows = []
        for v, g in ((va, t_out - chamfer), (va + chamfer * 0.8, t_out), (vb - chamfer * 0.8, t_out), (vb, t_out - chamfer)):
            o = ring(v, g, g * PX)
            i = ring(v, -0.4, -0.4 * PX)
            rows.append([bm.verts.new(p) for p in o] + [bm.verts.new(p) for p in reversed(i)])
        n = len(ths)
        L = 2 * n
        for ra, rb in zip(rows, rows[1:]):
            for k in range(L):
                j = (k + 1) % L
                f = bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
                f.material_index = mat_side if k in (n - 1, L - 1) else mat_top
                f.smooth = k < n - 1
        for r, rev in ((rows[0], False), (rows[-1], True)):
            for k in range(n - 1):
                q = (r[k], r[k + 1], r[L - 2 - k], r[L - 1 - k])
                f = bm.faces.new(tuple(reversed(q)) if rev else q)
                f.material_index = mat_side
                f.smooth = False

    band(v0 + 0.75, v1, 1.15, M["clamp"], M["clamp"])
    band(v0, v0 + 0.95, 1.55, M["flange"], M["flange"], chamfer=0.25)  # the lit front flange
    # mounting lug on the outer side (cols 5-6): a chamfered block bolted to the band
    cbox(bm, 4.95, 7.2, 17.15, 21.85, zc - 0.17, zc + 0.19, M["lug"], ch=0.45)
    # two bolt heads on the lug's top
    for vb in (18.4, 20.6):
        ellipsoid(bm, 6.0, vb, zc + 0.19, 0.55, 0.55, 0.035, M["pin"], segs=12, rings=6, zmin=0.0)


def build_hinge(bm, M, u_out=11.0, u_in=15.45, right=False):
    """The dark grey hinge knuckle (rows 31-35): a barrel across the arm (axis X) with recessed end
    caps and a pin boss on the outer end. The sprite's right knuckle reaches 3 px further in than
    the left one (cols 29-32, rows 33-36), so each side is built with its own inner end."""
    vc, zc = 33.25, 0.05
    ry, rz = 2.35, 0.25
    us = (u_out, u_out + 0.3, u_in - 0.3, u_in)
    if right:
        us = tuple(2 * AXIS - u for u in reversed(us))
    pts = [(X(u), Y(vc), zc) for u in us]
    rings = []
    sides = 18
    for k, (x, y, z) in enumerate(pts):
        s = 0.86 if k in (0, 3) else 1.0
        rings.append([bm.verts.new((x, y + ry * PX * s * math.cos(2 * math.pi * i / sides),
                                    z + rz * s * math.sin(2 * math.pi * i / sides))) for i in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = M["joint"]
            f.smooth = True
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(list(reversed(ring)) if rev else ring)
        f.material_index = M["jointcap"]
        f.smooth = False
    # pin boss on the outer end
    ub = (10.75, u_out + 0.05) if not right else (2 * AXIS - u_out - 0.05, 2 * AXIS - 10.75)
    tube(bm, [(X(ub[0]), Y(vc), zc), (X(ub[1]), Y(vc), zc)], 1.1 * PX, M["pin"], sides=12, rz=1.1 * PX)


def surface_tree(bm):
    return BVHTree.FromBMesh(bm)


def z_on(tree, u, v, lift=0.0, default=0.0):
    hit = tree.ray_cast(Vector((X(u), Y(v), 5.0)), Vector((0, 0, -1)))
    return (hit[0].z if hit[0] is not None else default) + lift


def surface_path(tree, pts, lift, n_per=6, smooth_win=2):
    """Densify a (u, v) polyline and drop each point onto the surface below, `lift` above it; the
    heights are max-filtered over a small window so the tube rides over steps, not into them."""
    dense = []
    for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
        for k in range(n_per):
            t = k / n_per
            dense.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
    dense.append(pts[-1])
    zs = [z_on(tree, u, v) for u, v in dense]
    zf = [max(zs[max(0, i - smooth_win):i + smooth_win + 1]) for i in range(len(zs))]
    return [(X(u), Y(v), z + lift) for (u, v), z in zip(dense, zf)]


def build_left(bm, M, mats, detail=True):
    """Everything left of the mirror line (mirrored afterwards)."""
    st = prong_stations(M)
    if detail:
        # the pod with its L panel seam cut in (col 9 rows 4-11, then row 11 to col 12)
        def target(b):
            sweep(b, st, cap1=True)

        tb = bmesh.new()
        sweep(tb, st, cap1=False)
        tree = surface_tree(tb)
        tb.free()

        def groove(pts):
            def cutter(b):
                path = surface_path(tree, pts, 0.0, n_per=6, smooth_win=0)
                tube(b, path, 0.45 * PX, M["seam"], sides=8, rz=0.9 * PX)
            return cutter
        cutters = [groove([(9.55, 3.9), (9.45, 6.0), (9.45, 11.9)]), groove([(9.0, 11.55), (11.0, 11.55), (12.9, 11.6)])]
        boolean_cut(bm, mats, target, cutters)
        # drop the temporary cap on the mirror line (the mirror welds the open end)
        ax = X(AXIS)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(abs(v.co.x - ax) < 1e-5 for v in f.verts)],
                         context="FACES_ONLY")
    else:
        sweep(bm, st, cap1=False)

    if detail:
        build_clamp(bm, M)
    else:
        u_c, w, zc, ht, hb = pod_section_at(19.5)
        cbox(bm, 4.95, 7.6, 17.15, 21.85, zc - 0.17, zc + 0.19, M["lug"], ch=0.45)
    # blister on the pod's inner flank (cols 18-19, rows 10-14)
    ellipsoid(bm, 18.55, 12.95, 0.07, 1.55, 2.65, 0.19, M["blister"], segs=18, rings=10)
    # the long tank on the strut's inner flank (cols 18-20, rows 22-33), its tail tapering into the
    # knuckle
    tank = [dict(u=19.2, v=21.7, w=0.0, zc=0.06, ht=0.0, hb=0.0, mat=M["tank"])]
    for u, v, w, ht in ((19.0, 22.2, 1.0, 0.12), (19.3, 23.2, 1.6, 0.17), (19.35, 25.0, 1.8, 0.19),
                        (19.15, 27.5, 1.85, 0.19), (19.05, 28.9, 1.85, 0.18), (18.75, 30.6, 1.6, 0.17), (18.35, 32.4, 1.7, 0.16),
                        (18.0, 34.0, 1.3, 0.11), (17.8, 34.9, 0.0, 0.0)):
        tank.append(dict(u=u, v=v, w=w, zc=0.05, ht=ht, hb=ht * 0.8, mat=M["tank"]))
    for k, t in enumerate(tank):  # a chamfered fairing, its rounded ends left soft
        t.update(prof((0.5, 0.25, 0.55, 0.25)), soft=k < 2 or k >= len(tank) - 3, bev=0.12)
    sweep(bm, tank)

    if not detail:
        return
    tb = bmesh.new()
    sweep(tb, st, cap1=False)
    tree = surface_tree(tb)
    tb.free()
    # coolant pipe: down the pod's back (col 12), over the clamp, across it (row 19) and down
    # off it on the outer side (col 8), sinking into the strut's flank
    full = bmesh.new()
    sweep(full, st, cap1=False)
    build_clamp(full, M)
    ftree = surface_tree(full)
    full.free()
    pipe = surface_path(ftree, [(12.5, 11.9), (12.5, 16.6), (12.5, 19.5), (10.0, 19.5), (8.55, 19.5),
                                (8.55, 21.0)], 0.35 * PX, n_per=5, smooth_win=2)
    # off the clamp's edge it drops down the strut's outer flank
    pipe += [(X(8.6), Y(22.2), pipe[-1][2] - 0.04), (X(8.9), Y(23.1), z_on(tree, 8.9, 23.1, 0.0) - 0.02)]
    tube(bm, pipe, 0.62 * PX, M["pipe"], sides=10)
    # pipe clips: small grey saddles where it leaves the pod (row 12) and on the strut
    # actuator cylinder on the strut's top (cols 12-13, rows 23-30) and its piston rod down the lower
    # arm's inner flank (cols 15-16, rows 33-44)
    cyl = surface_path(tree, [(13.0, 22.9), (13.05, 26.5), (13.15, 30.6)], 0.55 * PX, n_per=4, smooth_win=1)
    tube(bm, cyl, 1.05 * PX, M["rod"], sides=12)
    # cylinder end glands (slightly bigger collars)
    for (x, y, z) in (cyl[0], cyl[-1]):
        tube(bm, [(x, y + 0.4 * PX, z), (x, y - 0.4 * PX, z)], 1.3 * PX, M["pin"], sides=12)
    zr = 0.245
    rod = [(X(14.2), Y(32.4), 0.25), (X(14.9), Y(34.0), 0.25), (X(15.45), Y(35.8), zr),
           (X(15.65), Y(37.5), zr), (X(15.7), Y(41.0), zr), (X(15.85), Y(43.6), zr - 0.01), (X(16.6), Y(45.6), zr - 0.05)]
    tube(bm, rod, 0.95 * PX, M["piston"], sides=12)
    # the rod's clevis where it meets the knuckle (cols 14-17, rows 35-37)
    cbox(bm, 14.6, 17.9, 35.4, 37.7, 0.02, 0.25, M["piston"], ch=0.5)
    # domes on the bar beside the turret (cols 18-20, rows 45-47)
    ellipsoid(bm, 19.6, 46.5, z_on(tree, 19.6, 46.5, -0.02), 1.55, 1.35, 0.11, M["dome"], segs=16, rings=8, zmin=-0.3)


def build_turret(bm, M, mats, detail=True):
    """The turret on the bar's middle: a grey ring (rows 45-47), a dark neck and the split blue gun
    housing pointing up between the prongs (rows 37-42)."""
    tb = bmesh.new()
    sweep(tb, prong_stations({k: 0 for k in ("pod", "seam", "strut", "joint", "arm", "bar")}), cap1=False)
    tree = surface_tree(tb)
    tb.free()
    uc, vc = AXIS, 46.55
    zb = z_on(tree, uc, vc) - 0.05
    # turret ring: a short vertical cylinder with a chamfered lit lip
    sides = 24
    rings = []
    for r_px, z, mat in ((2.35, zb, M["ring"]), (2.35, zb + 0.10, M["ring"]), (2.45, zb + 0.13, M["ringlip"]),
                         (2.2, zb + 0.16, M["ringlip"]), (1.6, zb + 0.17, M["ring"])):
        rings.append(([bm.verts.new((X(uc) + r_px * PX * math.cos(2 * math.pi * k / sides),
                                     Y(vc) + r_px * PX * 1.0 * math.sin(2 * math.pi * k / sides), z))
                       for k in range(sides)], mat))
    for (r0, m0), (r1, _) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = m0
            f.smooth = True
    f = bm.faces.new(rings[-1][0])
    f.material_index = M["ring"]
    f = bm.faces.new(list(reversed(rings[0][0])))
    f.material_index = M["ring"]
    zg = zb + 0.12
    # the gun: neck (dark) out of the ring, then the housing with its slot
    gun = [dict(u=AXIS, v=46.0, w=1.25, zc=zg, ht=0.09, hb=0.09, mat=M["neck"]),
           dict(u=AXIS, v=43.2, w=1.25, zc=zg, ht=0.09, hb=0.09, mat=M["neck"]),
           dict(u=AXIS, v=42.75, w=1.75, zc=zg, ht=0.13, hb=0.11, mat=M["gun"])]
    for v, w, ht in ((42.2, 1.7, 0.14), (41.3, 1.85, 0.16), (40.4, 2.3, 0.18), (39.2, 2.55, 0.18), (38.3, 2.4, 0.17),
                     (37.55, 1.85, 0.14), (37.05, 1.1, 0.09), (36.8, 0.0, 0.0)):
        gun.append(dict(u=AXIS, v=v, w=w, zc=zg, ht=ht, hb=ht * 0.85, mat=M["gun"]))
    if detail:
        def target(b):
            sweep(b, gun, sides=24, e_top=2.4, e_bot=2.2)

        def slot(b):
            cbox(b, AXIS - 0.6, AXIS + 0.6, 36.4, 42.4, zg - 0.02, zg + 0.4, M["seam"], ch=0.15)
        boolean_cut(bm, mats, target, [slot])
    else:
        sweep(bm, gun, sides=24, e_top=2.4, e_bot=2.2)


def build(coll, detail=True, name=NAME):
    sprite = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    mats, M = materials(sprite)
    bm = bmesh.new()
    build_left(bm, M, mats, detail)
    mirror_all(bm)
    ax = X(AXIS)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if abs(v.co.x - ax) < 1e-4], dist=1e-4)
    build_hinge(bm, M)
    build_hinge(bm, M, u_in=18.6, right=True)
    build_turret(bm, M, mats, detail)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only);
    copied from newsh7-39 design A (originally newshv-10.py, D185). x and y are untouched."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
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
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    pieces = common.split_assembly(obj, LAYOUT)
    # The outline shell's source (D51/D189): a sealed copy without the seams, pipe and actuator, so the
    # smoothed shell can't bridge the grooves and draw ink across the top.
    plain = build(coll, detail=False, name=NAME + "_plain")
    sealed = common.split_assembly(plain, LAYOUT)
    bpy.data.objects.remove(plain, do_unlink=True)
    bpy.context.view_layer.update()
    shells = {}
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        # the split's filled cut faces are flat
        for poly in p.data.polygons:
            if len(poly.vertices) > 8:
                poly.use_smooth = False
        src = sealed[name]
        bpy.context.view_layer.update()
        sh = common.outline_shell(src, coll, voxel=0.016, faces=4000, inside=0.01, islands="outer")
        sh.name = sh.data.name = f"{name}_outline"
        sink_shell(sh, src, margin=0.03, reach=0.08)
        print("SHELL", name, len(sh.data.vertices), "verts", "TRIS", sum(len(q.vertices) - 2 for q in p.data.polygons))
        bpy.data.objects.remove(src, do_unlink=True)
        shells[name] = sh
    for name, _, _ in LAYOUT:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    for name, cx, cy in LAYOUT:
        pieces[name].location = shells[name].location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    print("TOTAL TRIS", sum(len(q.vertices) - 2 for q in obj.data.polygons))


if __name__ == "__main__":
    main()
