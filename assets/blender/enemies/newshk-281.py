"""newshk-281, design A: FLEET's (3.6) red-eyed carrier pod as a hard-surface gunship.

What it is (brief + behaviour): type 708 on the sky layer, flies DOWN the screen at +2..+4 px/tick,
armour 40, and releases a pickup (type 533) when killed: a grey armoured carrier pod. So the sprite's
bottom (south) is its nose, and the slot in the raised frame on the nose block is the launch bay the
power-up leaves by.

What the sprite shows (reference/models/newshk-281, 24 x 28, one frame, palette 5):
- Plan: the full 24 px width from row 5/6 to row 23; a gabled head (rows 0-4, cols 8-16 widening to
  5-19, centred on col 12 + 0.5); a tapered prow (rows 24-26, cols 6-17 -> 10-13). Model edges go to
  the D74 inner mask (tools/sprite_mask.py).
- Nose block (rows 14-23): grey 9 deck, darker 8 side faces (cols 0-1 / 22-23, both sides: a real
  colour, not lighting), light 10 rails (cols 2-4 / 19-21), a light 11 frame (rows 17-20, cols 7-16)
  round a dark slot (rows 18-20, cols 8-15: 7 lip, 5-6 walls, 2-4 floor), a light front bar (row 23).
  Row 14 is a dark 5 seam right across: a groove between the block and the eye deck.
- Eye deck (rows 5-13): a big red glass eye (cols 7-17, rows 4-13; median 115) in a dark socket
  (the ink ring cols 6 / 18), white-hot at its lower left (127 at col 10 row 11, 125/121-124 round it):
  the glow inside the glass, seen through it. Two bright 10 struts rise either side of the eye
  (cols 4-5 / 19-20) and lean in over its top to a red keystone lens (cols 11-13, rows 0-3, 115 with a
  123 pip) in a dark gasket (the ink cols 10 / 14). Dark grey 6 shoulders (cols 0-4, rows 5-9) slope
  away outboard; light 10 ledges (rows 10-12) step out under them; row 13 is their dark front face.
- The eye's dark top and the bright lower-left are lighting (art rule 2): the eye is one glass, glow
  bands only where the sprite's hot spot is.

Units: c, r = sprite px EDGES (col 3 spans c 3..4); X = (c - 12) / 12, Y = (14 - r) / 12; z in px * PX.

Run: blender --background --python assets/blender/enemies/newshk-281.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402

NAME = "newshk-281"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
AX = 12.0   # nose block / body centre (edge coords)
HX = 12.5   # head, eye and struts centre (the sprite's head is half a pixel right of the body)


# --------------------------------------------------------------------------------------------------
# Materials (copied pattern from newshv-10.py: palette index per region, satin steel, glows D126/D173)
# --------------------------------------------------------------------------------------------------

import os  # noqa: E402
_st = [float(v) for v in os.environ.get("STEEL281", "0.85,0.65,0.5").split(",")]
STEEL = dict(metallic=_st[0], roughness=_st[1], spec=_st[2])
GLOW = dict(metallic=1.0, roughness=0.9)


class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.35, roughness=0.42, emit=0.0, spec=None):
        key = (index, metallic, roughness, emit, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"{NAME}A{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            if spec is not None:
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


# --------------------------------------------------------------------------------------------------
# Helpers (copied in: no shared lib edits)
# --------------------------------------------------------------------------------------------------

def _slopes(xs, ys):
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
    return m


class Pchip:
    """Monotone cubic through knots (x, y) (D52 station interpolation)."""

    def __init__(self, knots):
        self.x = [k[0] for k in knots]
        self.y = [k[1] for k in knots]
        self.m = _slopes(self.x, self.y)

    def __call__(self, x):
        xs, ys, m = self.x, self.y, self.m
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
        hh = xs[i + 1] - xs[i]
        t = (x - xs[i]) / hh
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * hh * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * hh * m[i + 1])


def P(c, r, z):
    """Edge coords (c, r) and z in px to Blender units."""
    return Vector(((c - 12) * PX, (14 - r) * PX, z * PX))


def verts(bm, pts):
    return [bm.verts.new(p) for p in pts]


def loft(bm, rings, mat, smooth=True, cap0=True, cap1=True, cap_mat=None):
    """Join rings (lists of BMVert of equal length; a 1-list is a tip) with quads; `mat` is an index or
    f(i, k) for segment k between ring i and i + 1."""
    mf = mat if callable(mat) else (lambda i, k: mat)
    n = max(len(r) for r in rings)
    out = []
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            j = (k + 1) % n
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                vs = (a[0], b[k], b[j])
            elif len(b) == 1:
                vs = (a[k], b[0], a[j])
            else:
                vs = (a[k], b[k], b[j], a[j])
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            f.material_index = mf(i, k)
            f.smooth = smooth
            out.append(f)
    cm = mf(0, 0) if cap_mat is None else cap_mat
    for ring, ok, rev in ((rings[0], cap0, True), (rings[-1], cap1, False)):
        if ok and len(ring) > 2:
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = cm
            f.smooth = False
            out.append(f)
    return out


def chbox(bm, c0, c1, r0, r1, z0, z1, ch, mat, chz=None):
    """A box with chamfered edges (convex hull of the chamfer points), in edge coords / px."""
    chz = ch if chz is None else chz
    pts = []
    for c, sc in ((c0, 1), (c1, -1)):
        for r, sr in ((r0, 1), (r1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(c + sc * ch, r, z + sz * chz), (c, r + sr * ch, z + sz * chz), (c + sc * ch, r + sr * ch, z)]
    hull_pts(bm, [P(*p) for p in pts], mat)


def hull_pts(bm, pts, mat):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in vs if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat
        f.smooth = False


def tmp_mesh(bm, nmat):
    me = bpy.data.meshes.new("_tmp")
    for _ in range(nmat):
        me.materials.append(None)
    bm.to_mesh(me)
    bm.free()
    return me


def cut_into(bm, outline, z0, z1, wall_mat, nmat):
    """Boolean-subtract a vertical prism (outline in edge coords (c, r), z0..z1 px) from the closed shell
    in bm, in place (newshv-10.py's cut_into); cut faces get `wall_mat`."""
    me = bpy.data.meshes.new("_shell")
    cm = bpy.data.meshes.new("_cut")
    slots = [bpy.data.materials.new("_slot") for _ in range(nmat)]
    for m in (me, cm):
        for sl in slots:
            m.materials.append(sl)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    shell = bpy.data.objects.new("_shell", me)
    cb = bmesh.new()
    lo = verts(cb, [P(c, r, z0) for c, r in outline])
    hi = verts(cb, [P(c, r, z1) for c, r in outline])
    loft(cb, [lo, hi], wall_mat, smooth=False)
    bmesh.ops.recalc_face_normals(cb, faces=cb.faces)
    cb.to_mesh(cm)
    cb.free()
    cutter = bpy.data.objects.new("_cut", cm)
    sc = bpy.context.scene.collection
    sc.objects.link(shell)
    sc.objects.link(cutter)
    mod = shell.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.material_mode = "INDEX"
    bpy.context.view_layer.update()
    ev = shell.evaluated_get(bpy.context.evaluated_depsgraph_get())
    out = bpy.data.meshes.new_from_object(ev)
    bm.clear()
    bm.from_mesh(out)
    for o in (shell, cutter):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in (me, cm, out):
        bpy.data.meshes.remove(m)
    for sl in slots:
        bpy.data.materials.remove(sl)


def section_loft(bm, rows, section, matf, cx=AX, cap_mat=None, smooth=False):
    """Loft along r: section(r) -> [(dx, z)] px round the cross-section (same count every row)."""
    rings = [verts(bm, [P(cx + dx, r, z) for dx, z in section(r)]) for r in rows]
    return loft(bm, rings, lambda i, k: matf(rows[i], rows[i + 1], k), smooth=smooth, cap_mat=cap_mat)


def sweep(bm, path, hw, hh, mat, power=4.0, sides=16, up=(0, 0, 1)):
    """A chamfered-bar tube along path [(c, r, z)] (z px); hw / hh half width / height in px (floats or
    per-point lists). Rings stand perpendicular to the path."""
    pts = [P(*p) for p in path]
    upv = Vector(up)
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(upv).normalized()
        u = side.cross(t).normalized()
        w = (hw[i] if isinstance(hw, list) else hw) * PX
        h = (hh[i] if isinstance(hh, list) else hh) * PX
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            e = 2 / power
            ring.append(p + side * (w * math.copysign(abs(ca) ** e, ca)) + u * (h * math.copysign(abs(sa) ** e, sa)))
        rings.append(verts(bm, ring))
    return loft(bm, rings, mat, smooth=False)


def pole_ellipsoid(bm, centre, radii, toward, mat, segments=32, rings=24):
    """lib_b032.pole_ellipsoid (copied): an ellipsoid whose UV pole sits at the surface point above
    `toward`, so faces painted by angle from the pole make round spots there. Units."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    u, v = (toward[0] - cx) / rx, (toward[1] - cy) / ry
    pole = Vector((u, v, math.sqrt(max(0.0, 1 - u * u - v * v)))).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(pole)
    for vert in res["verts"]:
        p = rot @ vert.co
        vert.co = Vector((cx + p.x * rx, cy + p.y * ry, cz + p.z * rz))
    faces = list({f for v in res["verts"] for f in v.link_faces})
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces, pole


def sink_shell(shell, model, margin, reach):
    """newshv-10.py's sink_shell (copied): drop every outline-shell vertex to `margin` under the lowest
    top surface within `reach` (seen from above), so the ink stays on the silhouette (D90/D118)."""
    from mathutils.bvhtree import BVHTree
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


def lerp_knots(knots, x):
    if x <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


# --------------------------------------------------------------------------------------------------
# The model
# --------------------------------------------------------------------------------------------------

DECK = 2.6        # nose-block deck height, px
EYE_C = (HX, 8.95)  # eye centre (edge coords)
EYE_R = (5.45, 4.85)  # eye plan radii, px
EYE_Z = 2.7       # eye equator height = socket lip
EYE_RZ = 3.3      # eye dome height above it


def build(coll, sprite):
    M = Mats(sprite)
    ARM = M(9, **STEEL)            # nose-block deck
    SIDE = M(8, **STEEL)           # darker side faces (cols 0-1 / 22-23)
    UNDER = M(8, metallic=0.3, roughness=0.55)
    RAIL = M(10, **STEEL)
    FRAME = M(11, **STEEL)
    BAYW = M(6, metallic=0.3, roughness=0.6)
    BAYF = M(4, metallic=0.2, roughness=0.75)
    SEAM = M(5, metallic=0.3, roughness=0.6)
    SHOULDER = M(6, **STEEL)
    LEDGE = M(10, **STEEL)
    STRUT = M(10, **STEEL)
    SOCKET = M(4, metallic=0.4, roughness=0.5)
    GASKET = M(3, metallic=0.3, roughness=0.6)
    EYE = M(115, metallic=0.0, roughness=0.14, emit=0.6, spec=1.0)
    G119 = M(119, emit=0.8, **GLOW)
    G122 = M(122, emit=0.95, **GLOW)
    G125 = M(125, emit=1.0, **GLOW)
    G127 = M(127, emit=1.2, **GLOW)
    LENS = M(115, metallic=0.0, roughness=0.18, emit=0.5, spec=1.0)
    PIP = M(123, emit=1.0, **GLOW)

    bm = bmesh.new()

    # ---- nose block (rows 14-24): a chamfered armoured box, the bay cut into its deck --------------
    hb = bmesh.new()
    hrows = [14.0, 14.3, 14.6, 14.95, 15.4, 16.5, 18.0, 19.5, 21.0, 22.4, 23.0, 23.3, 23.6, 23.85, 24.0]
    hw_k = [(14.0, 12.0), (23.0, 12.0), (23.3, 11.55), (24.0, 11.05)]
    zt_k = [(14.0, 1.2), (14.3, 1.75), (14.6, 2.25), (14.95, DECK), (23.3, DECK), (23.6, 2.3), (23.85, 1.85), (24.0, 1.4)]

    def hull_sec(r):
        hw, zt = lerp_knots(hw_k, r), lerp_knots(zt_k, r)
        zs = min(0.6, zt - 0.8)
        return [(-hw + 1.0, -2.5), (hw - 1.0, -2.5), (hw, -1.5), (hw, zs), (hw - 1.9, zt - 0.2), (hw - 2.25, zt),
                (-(hw - 2.25), zt), (-(hw - 1.9), zt - 0.2), (-hw, zs), (-hw, -1.5)]

    def hull_mat(r0, r1, k):
        if k in (0, 1, 9):
            return UNDER
        if k in (2, 8):
            return SIDE
        if k in (3, 7):
            return SIDE
        return SEAM if r1 <= 14.96 else ARM

    section_loft(hb, hrows, hull_sec, hull_mat, cap_mat=ARM)
    # the launch bay: open slot rows 18-21, cols 8-16, floor 1.8 px under the deck
    cut_into(hb, [(8.0, 18.0), (16.0, 18.0), (16.0, 21.0), (8.0, 21.0)], 0.8, 8.0, BAYW, len(M.list) + 8)
    # side panel lines: a long groove along each flank and a joint at row 19
    for c0, c1 in ((-1.0, 0.3), (23.7, 25.0)):
        cut_into(hb, [(c0, 15.6), (c1, 15.6), (c1, 22.6), (c0, 22.6)], -0.75, -0.3, SEAM, len(M.list) + 8)
    for f in hb.faces:
        if f.material_index == BAYW and f.normal.z > 0.9:
            f.material_index = BAYF
    bm.from_mesh(tmp_mesh(hb, len(M.list) + 8))

    # bay frame (rows 17-20, cols 7-16): raised bezel on three sides, open (flush) to the nose
    chbox(bm, 7.0, 17.0, 17.0, 18.0, 1.6, 3.35, 0.35, FRAME)
    chbox(bm, 7.0, 8.0, 17.0, 21.0, 1.6, 3.35, 0.35, FRAME)
    chbox(bm, 16.0, 17.0, 17.0, 21.0, 1.6, 3.35, 0.35, FRAME)
    # launch rollers in the bay (the slot's 5-6 bands): three low cross bars on its floor
    for r0 in (18.35, 19.25, 20.15):
        sweep(bm, [(8.05, r0 + 0.35, 1.15), (15.95, r0 + 0.35, 1.15)], 0.32, 0.32, BAYW, power=2.0, sides=8)

    # rails (cols 2-4 / 19-21, rows 15-22): two ribs bridged, a cross joint at row 19
    for side in (-1, 1):
        def C(c):
            return c if side < 0 else 2 * AX - c
        for ca, cb in ((2.0, 2.95), (3.95, 5.0)):
            a, b = sorted((C(ca), C(cb)))
            chbox(bm, a, b, 15.0, 23.0, 1.8, 3.3, 0.28, RAIL)
        a, b = sorted((C(2.0), C(5.0)))
        for r0, r1 in ((15.0, 16.0), (17.75, 18.85), (19.95, 21.0)):
            chbox(bm, a, b, r0, r1, 1.8, 3.15, 0.25, RAIL)
        chbox(bm, a + 0.15, b - 0.15, 18.85, 19.95, 1.8, 2.75, 0.2, SEAM)

    # front bar (row 23): a polished bumper across the nose
    chbox(bm, 2.0, 22.0, 22.85, 23.95, 0.8, 3.05, 0.45, FRAME)

    # prow (rows 24-27): a tapered keel nose under the bumper
    prows = [23.4, 24.0, 24.5, 25.0, 25.5, 26.0, 26.4, 26.75, 27.0]
    pw = Pchip([(23.4, 6.6), (24.0, 6.4), (25.0, 4.8), (26.0, 3.0), (26.75, 1.5), (27.0, 0.7)])
    pt = Pchip([(23.4, 1.4), (24.0, 1.3), (25.0, 0.8), (26.0, 0.1), (27.0, -0.6)])
    pb = Pchip([(23.4, -2.4), (24.0, -2.4), (25.0, -2.2), (26.0, -1.9), (27.0, -1.4)])

    def prow_sec(r):
        hw, zt, zb = pw(r), pt(r), pb(r)
        ch = min(0.8, hw * 0.35)
        return [(-hw + ch, zb), (hw - ch, zb), (hw, zb + ch), (hw, zt - ch), (hw - ch * 1.6, zt),
                (-(hw - ch * 1.6), zt), (-hw, zt - ch), (-hw, zb + ch)]

    section_loft(bm, prows, prow_sec,
                 lambda r0, r1, k: UNDER if k in (0, 1, 7) else (ARM if k == 4 else SIDE), cap_mat=SIDE)

    # ---- eye deck (rows 5-14): shoulders sloping outboard, a groove at its front --------------------
    urows = [5.0, 5.3, 5.7, 6.0, 7.0, 9.0, 11.0, 12.6, 13.0, 13.2, 13.5, 13.75, 14.0]
    uhw = [(5.0, 8.4), (5.3, 9.3), (5.7, 11.0), (6.0, 12.0), (13.0, 12.0), (13.2, 11.2), (14.0, 11.0)]
    uzt = [(5.0, 2.2), (5.5, 3.0), (6.0, 3.2), (12.6, 3.2), (13.2, 2.6), (13.75, 1.8), (14.0, 1.2)]
    uzo = [(5.0, 0.8), (6.0, 1.2), (12.6, 1.2), (13.5, 1.0), (14.0, 0.8)]

    def deck_sec(r):
        hw, zt, zo = lerp_knots(uhw, r), lerp_knots(uzt, r), lerp_knots(uzo, r)
        return [(-hw + 1.0, -2.0), (hw - 1.0, -2.0), (hw, -1.0), (hw, zo), (hw - 0.5, zo + 0.35),
                (hw - 5.6, zt), (-(hw - 5.6), zt), (-(hw - 0.5), zo + 0.35), (-hw, zo), (-hw, -1.0)]

    def deck_mat(r0, r1, k):
        if k in (0, 1, 9):
            return UNDER
        if r0 >= 13.15 and k in (3, 4, 5, 6, 7):
            return SEAM
        return SHOULDER

    section_loft(bm, urows, deck_sec, deck_mat, cap_mat=SHOULDER)
    # shoulder vents: two short slots per side (the sprite's dark ticks at col 2, rows 6-8)
    for side in (-1, 1):
        for cc in (1.7, 3.0):
            c = cc if side < 0 else 2 * AX - cc
            z0 = 1.2 + (3.2 - 1.2) * (abs(c - AX) - 12) / -5.6 if abs(c - AX) > 6.4 else 3.2
            chbox(bm, c - 0.3, c + 0.3, 6.4, 8.9, z0 - 0.6, z0 + 0.32, 0.15, GASKET)

    # ledges (rows 10-13): light plates stepping out under the shoulders, chamfered front edge
    chbox(bm, 0.05, 6.6, 10.0, 13.0, 0.4, 3.75, 0.5, LEDGE)
    chbox(bm, 18.4, 23.95, 10.0, 13.0, 0.4, 3.75, 0.5, LEDGE)

    # ---- head (rows 0-5): the gabled base under the struts and keystone ------------------------------
    head = [(8.15, 0.1), (6.95, 1.05), (6.05, 2.0), (6.05, 3.7), (5.0, 4.5), (4.2, 5.4), (4.2, 6.2)]
    outline = head + [(2 * HX - c, r) for c, r in reversed(head)]
    lo = verts(bm, [P(c, r, -0.4) for c, r in outline])
    hi = verts(bm, [P(c, r, 2.4) for c, r in outline])
    loft(bm, [lo, hi], SHOULDER, smooth=False, cap0=True, cap1=True, cap_mat=SHOULDER)

    # ---- the eye: a dark socket collar and a big red glass dome ---------------------------------------
    nseg = 40
    ex, ey = EYE_C
    rx, ry = EYE_R

    def ell(dr, z):
        return verts(bm, [P(ex + (rx + dr) * math.cos(2 * math.pi * k / nseg),
                            ey - (ry + dr) * math.sin(2 * math.pi * k / nseg), z) for k in range(nseg)])
    sock = [ell(0.8, 0.5), ell(0.8, 2.3), ell(0.55, EYE_Z + 0.05), ell(0.15, EYE_Z - 0.05), ell(-0.4, EYE_Z - 0.6)]
    loft(bm, sock, SOCKET, smooth=False, cap0=True, cap1=True)
    pole_at = P(10.45, 11.55, 0)
    faces, pole = pole_ellipsoid(bm, (P(ex, ey, EYE_Z).x, P(ex, ey, EYE_Z).y, EYE_Z * PX),
                                 (rx * PX, ry * PX, EYE_RZ * PX), (pole_at.x, pole_at.y), EYE, segments=40, rings=28)
    cen = Vector((P(ex, ey, EYE_Z).x, P(ex, ey, EYE_Z).y, EYE_Z * PX))
    for f in faces:
        p = f.calc_center_median()
        q = Vector(((p.x - cen.x) / (rx * PX), (p.y - cen.y) / (ry * PX), (p.z - cen.z) / (EYE_RZ * PX)))
        ang = math.degrees(q.normalized().angle(pole))
        if ang < 6.0:
            f.material_index = G127
        elif ang < 11.5:
            f.material_index = G125
        elif ang < 17.0:
            f.material_index = G122
        elif ang < 23.0:
            f.material_index = G119

    # ---- struts: two bright bars rising beside the eye and leaning in over it to the keystone -------
    spath = [(5.0, 12.4, 3.3), (5.0, 11.3, 4.2), (5.0, 9.4, 5.0), (5.1, 7.3, 5.6), (5.6, 5.3, 6.0),
             (6.6, 3.6, 6.2), (7.7, 2.1, 6.25), (8.75, 0.75, 6.2)]
    shw = [1.2, 1.2, 1.15, 1.15, 1.2, 1.3, 1.4, 1.4]
    for side in (-1, 1):
        pth = spath if side < 0 else [(2 * HX - c, r, z) for c, r, z in spath]
        sweep(bm, pth, shw, 0.95, STRUT, power=7.0, sides=20)
    # keystone housing joining the struts' heads, the red lens set in a dark gasket
    # its back slopes down to the head (a wedge in side view, not a box end)
    kp = []
    for c in (8.35, 16.65):
        d = 0.55 if c < HX else -0.55
        kp += [(c, 0.15, 1.5), (c + d, 0.15, 3.0), (c, 3.7, 1.5), (c, 3.7, 5.45), (c + d, 3.7, 6.0),
               (c + d, 1.4, 6.0), (c, 1.1, 5.4)]
    hull_pts(bm, [P(*q) for q in kp], STRUT)
    chbox(bm, 10.05, 14.95, 0.3, 3.85, 4.5, 6.4, 0.35, GASKET)
    sweep(bm, [(HX, 0.35, 6.1), (HX, 0.6, 6.1), (HX, 1.6, 6.15), (HX, 2.7, 6.1), (HX, 3.45, 6.05), (HX, 3.7, 6.05)],
          [0.9, 1.5, 1.65, 1.65, 1.5, 0.9], [0.45, 0.8, 0.9, 0.9, 0.8, 0.45], LENS, power=2.6, sides=16)
    sweep(bm, [(HX, 0.95, 6.75), (HX, 1.45, 6.85), (HX, 1.95, 6.75)], [0.35, 0.6, 0.35], [0.2, 0.3, 0.2], PIP,
          power=2.0, sides=10)

    me = bpy.data.meshes.new(NAME)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for m in M.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj, M


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, M = build(coll, sprite)
    obj.data.calc_loop_triangles()
    print(f"{NAME}: {len(obj.data.polygons)} faces, {len(obj.data.loop_triangles)} triangles")
    sealed = obj.copy()  # D90/D118: the outline shell from a sealed copy
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=3000, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    sink_shell(shell, sealed, 0.5 * PX, 1.2 * PX)
    bpy.data.objects.remove(sealed, do_unlink=True)
    assert len(shell.data.polygons) > 0, "empty outline shell"
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])


if __name__ == "__main__":
    main()
