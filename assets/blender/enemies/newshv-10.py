"""newshv-10, newshv-159, newshv-171: three newshv units built by one script (they once shared lib_b043).

  newshv-10   pale pink faceted crystal dart (24 x 28 block, 15 x 25 px), flies UP the screen point first in V
              formations of separate darts (type 794, sky layer, (0,-3) px/tick). A long hexagonal-section
              crystal: a lit crest ridge with a chamfer strip, two facets each side, a girdle edge, a shallow
              faceted belly; a cut groove ring at row 19 and a short faceted tail pavilion (rows 20-25).
  newshv-159  blue-steel hooded gunship (24 x 28 block), flies DOWN the screen nose first (type 811). The
              hood (rows 3-16) is the dorsal shell over the aft body, with a raised glowing chevron trim
              (orange core, red edges) and a blue cabochon sensor gem in a bezel under its apex, a vent
              notch cut into the rear lip (row 3, cols 11-12). Forward of the hood the nose body (rows 17-28) carries a
              raised pentagonal launcher hatch outlined by cut grooves, its launch slot at the front lip
              (row 26), and two forward claw prongs (cols 0-4 / 19-23) split from the body by grooves.
  newshv-171  the blue steel capsule it drops (12 x 14 block, size 1, type 812): a cylinder lying across the
              screen (cols 1-10, rows 3-8), chamfered flat ends with a recessed end disc, two shallow
              groove rings (cols 3 and 8) and a polished centre band.

Units: c, r = sprite px edges; X = (c - W/2) / 12, Y = (H/2 - r) / 12; Z up, sprite plane at z = 0.
Exports public/models/enemies/newshv-{10,159,171}.glb and their src/render/spriteModels entries.

Run: blender --background --python assets/blender/enemies/newshv-10.py -- [--only 10,159,171] [--review DIR]
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

OUT = Path(__file__).resolve().parent
NAMES = ["newshv-10", "newshv-159", "newshv-171"]
PX = 1 / 12


# --------------------------------------------------------------------------------------------------
# Materials: the sprite's own palette index per region (medians), satin finishes; glows metallic 1 /
# rough (D126, D173); polished blue steel gets F0 via Specular IOR Level (D176), as batch 2's newshv-85.
# --------------------------------------------------------------------------------------------------

class Mats:
    def __init__(self, name):
        self.name = name
        self.sprite = {"name": name, "colors": common.load_sprite(ROOT, name)["colors"]}
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.35, roughness=0.42, emit=0.0, spec=None):
        key = (index, metallic, roughness, emit, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"{self.name}A{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            if spec is not None:
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


# --------------------------------------------------------------------------------------------------
# Curves and mesh helpers (copied in: no shared lib)
# --------------------------------------------------------------------------------------------------

def _slopes(xs, ys):
    n = len(xs)
    if n < 2:
        return [0.0] * n
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


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def P(self, c, r, z):
        return Vector(((c - self.w / 2) * PX, (self.h / 2 - r) * PX, z))


def loft(bm, rings, mat, smooth=True, cap0=True, cap1=True):
    """Join rings (lists of BMVert, equal length; a 1-list is a tip point) with quads/tris; `mat` is an
    index or f(k) giving the material of the k-th segment round the ring. Returns the faces."""
    mf = mat if callable(mat) else (lambda k: mat)
    faces = []
    n = max(len(r) for r in rings)
    for a, b in zip(rings, rings[1:]):
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
            f.material_index = mf(k)
            f.smooth = smooth
            faces.append(f)
    for ring, ok, rev in ((rings[0], cap0, True), (rings[-1], cap1, False)):
        if ok and len(ring) > 2:
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = mf(0)
            f.smooth = False
            faces.append(f)
    return faces


def verts(bm, pts):
    return [bm.verts.new(p) for p in pts]


def superellipse(n, p, phase=0.0):
    """Unit superellipse ring (cos, sin) pairs, k = 0 at +X going counter-clockwise."""
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + phase) / n
        out.append((spow(math.cos(a), 2 / p), spow(math.sin(a), 2 / p)))
    return out


def hb_mesh(bm):
    """A bmesh as a throwaway mesh (for bm.from_mesh)."""
    me = bpy.data.meshes.new("_tmp")
    bm.to_mesh(me)
    bm.free()
    return me


def cut_into(bm, G, outline, z0, z1, mat, nmat):
    """Boolean-subtract a vertical prism (outline in sprite (c, r) on grid G, z0..z1) from the closed shell
    in bm, in place; the cut walls get material index `mat` (nmat = the material count, so indices map)."""
    me = bpy.data.meshes.new("_shell")
    bm.to_mesh(me)
    shell = bpy.data.objects.new("_shell", me)
    cb = bmesh.new()
    lo = verts(cb, [G.P(c, r, z0) for c, r in outline])
    hi = verts(cb, [G.P(c, r, z1) for c, r in outline])
    loft(cb, [lo, hi], mat, smooth=False)
    bmesh.ops.recalc_face_normals(cb, faces=cb.faces)
    cm = bpy.data.meshes.new("_cut")
    cb.to_mesh(cm)
    cb.free()
    for m in (me, cm):
        for _ in range(nmat):
            m.materials.append(None)
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


def finish(name, bm, mats, coll, sharp_deg=None, flat=False):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if flat:
        for p in me.polygons:
            p.use_smooth = False
    elif sharp_deg:
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    return obj


# --------------------------------------------------------------------------------------------------
# newshv-10: the crystal dart
# --------------------------------------------------------------------------------------------------

def build_10(coll):
    M = Mats("newshv-10")
    G = Grid(24, 28)
    AX = 12.5  # the crystal's axis: the centre of column 12
    CR = dict(metallic=0.08, roughness=0.22, spec=0.9)  # polished crystal: dielectric, high F0
    CREST = M(94, **CR)  # crest chamfer strip (the sprite's lit ridge, 93-95)
    L_IN = M(91, **CR)  # left inner facet (cols 9-11: 91)
    L_OUT = M(91, **CR)
    R_IN = M(90, **CR)  # right inner facet (cols 13-15: 88-90)
    R_OUT = M(89, **CR)
    GIRD = M(88, **CR)  # girdle edge band (the darker rim)
    BELLY = M(88, **CR)
    GROOVE = M(88, metallic=0.08, roughness=0.4, spec=0.6)  # row 19: all 88
    T_L = M(92, **CR)  # tail pavilion, left / crest / right (rows 20-24: 91-95)
    T_C = M(94, **CR)
    T_R = M(91, **CR)

    # Half width (px) by row edge: straight-sided point (slope 0.5 px per row, as the sprite steps),
    # widest rows 14-18, groove at 19, tail pavilion rows 20-25.
    def hw_body(r):
        return min(6.55, max(0.0, 0.5 * (r - 1.15)))

    # Section of the faceted dart (x / hw, z / hw): crest chamfer, two top facets a side, girdle band,
    # shallow belly. Height scales with width so facet angles stay constant (a cut crystal).
    TOP = 0.60
    BOT = 0.40
    SEC = [(0.06, TOP), (0.48, 0.80 * TOP), (0.90, 0.30 * TOP), (1.0, 0.06 * TOP), (1.0, -0.05),
           (0.62, -0.75 * BOT), (0.16, -BOT)]
    ring_xz = [(x, z) for x, z in SEC] + [(-x, z) for x, z in reversed(SEC)]
    # segment k joins point k to k+1 (right half first, then left mirrored)
    seg_mat = [R_IN, R_OUT, GIRD, GIRD, BELLY, BELLY, BELLY, BELLY, BELLY, GIRD, GIRD, L_OUT, L_IN, CREST]

    def ring(bm, r, hw, scale=1.0, zoff=0.0, xyscale=1.0):
        return verts(bm, [G.P(AX + x * hw * xyscale, r, (z * hw * scale) * PX * 1.0 + zoff) for x, z in ring_xz])

    bm = bmesh.new()
    # body: tip to the groove
    tip = verts(bm, [G.P(AX, 1.55, 0.0)])
    rows = [2.0, 2.6, 3.4, 4.4, 5.6, 7.0, 8.6, 10.2, 11.8, 13.2, 14.3, 15.0, 18.4, 18.75]
    rings = [tip]
    for r in rows:
        hw = hw_body(r)
        rings.append(ring(bm, r, hw))
    # chamfer down into the groove
    rings.append(ring(bm, 18.95, 6.0, scale=0.92))
    loft(bm, rings, lambda k: seg_mat[k], smooth=False, cap1=False)
    # groove ring (row 19) recessed
    g0 = ring(bm, 18.95, 6.0, scale=0.92)
    g1 = ring(bm, 19.05, 5.45, scale=0.86)
    g2 = ring(bm, 19.95, 5.45, scale=0.86)
    g3 = ring(bm, 20.05, 6.0, scale=0.92)
    loft(bm, [g0, g1, g2, g3], GROOVE, smooth=False, cap0=False, cap1=False)
    # tail pavilion: rows 20-25, faceted, closing to a point
    tail_mat = [T_R, T_R, GIRD, GIRD, BELLY, BELLY, BELLY, BELLY, BELLY, GIRD, GIRD, T_L, T_L, T_C]
    trows = [(20.05, 6.0, 0.92), (20.35, 6.55, 1.0), (21.9, 6.55, 1.0), (22.6, 5.9, 0.98), (23.3, 4.4, 0.95),
             (24.0, 2.7, 0.9), (24.55, 1.25, 0.85)]
    trings = [ring(bm, r, hw, scale=s) for r, hw, s in trows]
    trings.append(verts(bm, [G.P(AX, 24.95, 0.0)]))
    loft(bm, trings, lambda k: tail_mat[k], smooth=False, cap0=False)
    obj = finish("newshv-10", bm, M, coll, flat=True)
    return obj, M


# --------------------------------------------------------------------------------------------------
# newshv-159: the hooded gunship (flies down the screen: nose at the bottom of the sprite)
# --------------------------------------------------------------------------------------------------

STEEL = dict(metallic=0.35, roughness=0.42, spec=0.65)
GLOW = dict(metallic=1.0, roughness=0.9)


def build_159(coll):
    M = Mats("newshv-159")
    G = Grid(24, 28)
    AX = 12.0
    HOOD = M(59, **STEEL)
    HOOD_RIM = M(57, **STEEL)
    BODY = M(57, **STEEL)
    PLATE = M(59, **STEEL)
    CLAW = M(59, **STEEL)
    CLAW_TOP = M(60, **STEEL)
    GROOVE = M(52, 0.3, 0.6)
    DARK = M(50, 0.3, 0.65)
    BEZEL = M(55, **STEEL)
    BELLY = M(55, 0.3, 0.55)
    RED = M(115, emit=0.8, **GLOW)
    ORANGE = M(123, emit=0.85, **GLOW)
    GEM = M(150, metallic=0.2, roughness=0.18, emit=0.5, spec=1.0)
    bm = bmesh.new()

    # ---- hood: a domed shell, rows 3-17 ------------------------------------------------------------
    HW = Pchip([(2.85, 3.0), (3.5, 4.1), (4.5, 6.0), (5.5, 6.95), (6.5, 7.15), (7.5, 7.95), (9.95, 8.25), (10.3, 8.95),
                (14.0, 9.0), (15.6, 8.9), (16.5, 8.0), (17.1, 6.6)])
    HT = Pchip([(2.85, 1.6), (3.5, 2.6), (5, 3.5), (8, 4.1), (11.5, 4.3), (14, 4.1), (16, 3.4), (17.1, 2.4)])  # crown px
    HB = 1.2  # rim below the sprite plane, px
    HP = 2.3

    def hood_top(c, r):
        hw, ht = HW(r), HT(r)
        t = abs(c - AX) / hw
        if t >= 1:
            return None
        return (-HB + (ht + HB) * (1 - t ** HP) ** (1 / HP)) * PX

    hb = bmesh.new()  # the hood shell, built alone so the notch can be cut from it
    hood_rows = [2.85, 3.0, 3.3, 3.7, 4.2, 5.0, 6.0, 7.2, 8.5, 10.0, 11.5, 13.0, 14.5, 15.6, 16.3, 16.8, 17.1]
    NS = 32
    rings = []
    for i, r in enumerate(hood_rows):
        hw, ht = HW(r), HT(r)
        # end rings shrink (rounded rear/front lips)
        pts = []
        for k in range(NS):
            a = 2 * math.pi * k / NS
            ca, sa = math.cos(a), math.sin(a)
            x = spow(ca, 2 / HP) * hw
            if sa >= 0:
                z = -HB + (ht + HB) * abs(sa) ** (2 / HP)
            else:
                z = -HB - 1.6 * abs(sa) ** (2 / 2.0)  # shallow closed belly
            pts.append(G.P(AX + x, r, z * PX))
        rings.append(verts(hb, pts))
    # round off the ends with tips
    rings.insert(0, verts(hb, [G.P(AX, 2.75, -0.2 * PX)]))
    rings.append(verts(hb, [G.P(AX, 17.25, -0.5 * PX)]))
    hood_mat = lambda k: HOOD if (k < NS // 2) else BELLY  # noqa: E731
    loft(hb, rings, hood_mat, smooth=True)
    # the rear notch (row 3, cols 11-12 open in the sprite): cut into the hood's rear lip
    notch = [(11.0, 1.5), (11.0, 3.75), (11.3, 4.05), (12.7, 4.05), (13.0, 3.75), (13.0, 1.5)]
    cut_into(hb, G, notch, -6 * PX, 8 * PX, HOOD, len(M.list))
    bm.from_mesh(hb_mesh(hb))

    # rim bead round the hood's lower edge (a machined lip): thin tube along the outline at z = -HB
    def tube(path, rad_w, rad_h, mat, n=8):
        rr = []
        for i, (c, r, z) in enumerate(path):
            p = G.P(c, r, z)
            a = G.P(*path[min(i + 1, len(path) - 1)])
            b = G.P(*path[max(i - 1, 0)])
            t = a - b
            t.z = 0
            t.normalize()
            s = t.cross(Vector((0, 0, 1)))
            pts = []
            for k in range(n):
                ang = 2 * math.pi * k / n
                pts.append(p + s * (math.cos(ang) * rad_w * PX) + Vector((0, 0, math.sin(ang) * rad_h * PX)))
            rr.append(verts(bm, pts))
        return loft(bm, rr, mat, smooth=True)

    rim = [(AX - HW(r) + 0.35, r, -HB * PX * 0.6) for r in (4.0, 5.0, 6.4, 8.0, 9.6, 11, 12.5, 14.0, 15.6, 16.4)]
    tube(rim, 0.38, 0.5, HOOD_RIM)
    tube([(2 * AX - c, r, z) for c, r, z in rim], 0.38, 0.5, HOOD_RIM)

    # ---- chevron trim on the hood (raised strip, conforms to the hood) ---------------------------
    arm = [(12.0, 4.4), (11.5, 5.4), (10.5, 6.5), (9.6, 7.6), (9.1, 8.6), (8.5, 9.6), (7.8, 10.6), (7.55, 11.6),
           (7.5, 12.6), (7.4, 13.6), (6.6, 14.6), (5.6, 15.6), (4.7, 16.4)]

    def strip(path, half_w, lift, depth, mat, n_side=1):
        """A flat-topped raised strip over the hood along path (c, r), half width px, top `lift` px
        above the hood, sunk `depth` px into it."""
        rr = []
        for i, (c, r) in enumerate(path):
            a = path[min(i + 1, len(path) - 1)]
            b = path[max(i - 1, 0)]
            tx, ty = a[0] - b[0], a[1] - b[1]
            ln = math.hypot(tx, ty)
            sx, sy = -ty / ln, tx / ln  # side direction in (c, r)
            pts = []
            prof = [(-half_w, -depth), (half_w, -depth), (half_w, lift * 0.6), (half_w * 0.7, lift),
                    (-half_w * 0.7, lift), (-half_w, lift * 0.6)]
            for o, dz in prof:
                cc, rq = c + sx * o, r + sy * o
                zt = hood_top(cc, rq)
                if zt is None:
                    zt = -HB * PX
                pts.append(G.P(cc, rq, 0) + Vector((0, 0, zt + dz * PX)))
            rr.append(verts(bm, pts))
        return loft(bm, rr, mat, smooth=False)

    for side in (1, -1):
        pth = [(AX + side * (c - AX), r) for c, r in arm]
        if side < 0:
            pth = [(AX + (AX - c), r) for c, r in arm]
        strip(pth, 1.45, 0.35, 0.5, RED)  # red edged band
        strip(pth, 0.55, 0.55, 0.3, ORANGE)  # glowing orange core

    strip([(AX, 13.4), (AX, 14.6), (AX, 15.8), (AX, 16.7)], 0.7, 0.45, 0.4, M(60, **STEEL))  # centre spine

    # ---- blue gem in a bezel under the chevron's apex: a ~3 x 3.5 px cabochon at (col 12, row 11), its
    # dark bezel ~4 px wide (cols 10-13; the sprite's gem is 2 px on rows 9, 10, 12 and 4 px on row 11) -
    GC = 11.0  # gem centre row edge
    gz = hood_top(AX, GC)
    ring_pts = []
    bz = []
    nb = 20
    for k in range(nb):
        a = 2 * math.pi * k / nb
        bz.append((math.cos(a), math.sin(a)))
    # bezel: a short ring collar
    def ringv(rad, z, cr=GC):
        return verts(bm, [G.P(AX + rad * x, cr - GE * rad * y, z) for x, y in bz])
    GR = 1.42  # cabochon half width px (cols 11-12, fringing 10 / 13 as on the sprite's row 11)
    GE = 1.22  # a slightly tall oval: the sprite's gem spans rows 9-12
    b0 = ringv(2.0, gz - 0.6 * PX)
    b1 = ringv(2.0, gz + 0.25 * PX)
    b2 = ringv(1.75, gz + 0.4 * PX)
    b3 = ringv(GR, gz + 0.25 * PX)
    loft(bm, [b0, b1, b2, b3], BEZEL, smooth=False, cap0=True, cap1=False)
    # cabochon dome
    dome = [b3]
    for t in (0.25, 0.5, 0.7, 0.86, 0.96):
        rad = GR * math.cos(t * math.pi / 2)
        dome.append(ringv(rad, gz + 0.25 * PX + 0.8 * PX * math.sin(t * math.pi / 2)))
    dome.append(verts(bm, [G.P(AX, GC, gz + 1.05 * PX)]))
    loft(bm, dome, GEM, smooth=True, cap0=False)


    # ---- nose body (rows 16.5-28): lower than the hood -----------------------------------------
    BW = Pchip([(16.3, 6.8), (17.6, 7.2), (18.2, 7.95), (23.6, 7.95), (24.2, 7.3), (24.9, 6.4), (25.9, 5.4), (26.9, 4.5),
                (27.6, 4.0), (28.0, 2.6)])
    BT = Pchip([(16.3, 2.2), (18, 2.4), (23, 2.2), (26, 1.7), (27.6, 1.0), (28.0, 0.5)])
    brows = [16.3, 17.0, 18.0, 19.5, 21.0, 22.5, 23.6, 24.3, 25.0, 25.8, 26.6, 27.3, 27.75, 28.0]
    rings = []
    BP = 2.8
    for r in brows:
        hw, ht = BW(r), BT(r)
        pts = []
        for k in range(NS):
            a = 2 * math.pi * k / NS
            ca, sa = math.cos(a), math.sin(a)
            x = spow(ca, 2 / BP) * hw
            z = (-0.6 + (ht + 0.6) * abs(sa) ** (2 / BP)) if sa >= 0 else (-0.6 - 1.8 * abs(sa))
            pts.append(G.P(AX + x, r, z * PX))
        rings.append(verts(bm, pts))
    rings.append(verts(bm, [G.P(AX, 28.15, -0.4 * PX)]))
    loft(bm, rings, lambda k: BODY if k < NS // 2 else BELLY, smooth=True)

    def body_top(c, r):
        hw, ht = BW(r), BT(r)
        t = abs(c - AX) / hw
        if t >= 1:
            return -0.6 * PX
        return (-0.6 + (ht + 0.6) * (1 - t ** BP) ** (1 / BP)) * PX

    # gabled hatch: apex row 17.9, full width (cols 8.6-15.4) from row 20.9, front face at row 25.7
    PW = Pchip([(17.9, 0.0), (18.6, 1.0), (20.9, 3.4), (25.7, 3.6)])

    def hatch(grow, lift, mat, r0, r1, ridge=True):
        rows = [r0 + (r1 - r0) * t for t in (0, 0.04, 0.12, 0.25, 0.38, 0.5, 0.65, 0.8, 0.92, 1.0)]
        rr = []
        for r in rows:
            hw = PW(r) + grow
            prof = [(-1.0, -0.8), (-1.0, 0.55), (-0.5, 0.92), (0.0, 1.0 if ridge else 0.92), (0.5, 0.92), (1.0, 0.55), (1.0, -0.8)]
            pts = []
            for x, z in prof:
                c = AX + x * max(hw, 0.05)
                zz = body_top(c, r) + (z * lift if z > 0 else z) * PX
                pts.append(G.P(c, r, zz))
            rr.append(verts(bm, pts))
        rr.insert(0, verts(bm, [G.P(AX, r0 - 0.15, body_top(AX, r0) - 0.6 * PX)]))
        return loft(bm, rr, mat, smooth=False, cap0=False, cap1=True)

    hatch(0.5, 0.45, GROOVE, 17.3, 26.0, ridge=False)  # dark cut groove round the hatch
    hatch(0.0, 1.7, PLATE, 17.9, 25.7)
    # launch slot at the front lip (row 26, cols 8-15): a dark recess
    sz = body_top(AX, 26.2)
    sl = [verts(bm, [G.P(AX + x, r, sz + dz * PX) for x, dz in ((-3.6, -0.5), (3.6, -0.5), (3.6, 0.55), (-3.6, 0.55))])
          for r in (25.75, 26.75)]
    loft(bm, sl, DARK, smooth=False)
    # bolts / vents on the hatch (the sprite's 50 dots at (9,21), (14,21), (8,24), (15,24))
    for c, r in ((9.6, 21.6), (14.4, 21.6), (9.3, 24.5), (14.7, 24.5)):
        z = body_top(c, r) + 1.45 * PX
        n = 8
        b = verts(bm, [G.P(c + 0.3 * math.cos(2 * math.pi * k / n), r + 0.3 * math.sin(2 * math.pi * k / n), z - 0.2 * PX)
                       for k in range(n)])
        t = verts(bm, [G.P(c + 0.3 * math.cos(2 * math.pi * k / n), r + 0.3 * math.sin(2 * math.pi * k / n), z + 0.15 * PX)
                       for k in range(n)])
        loft(bm, [b, t], DARK, smooth=False)

    # ---- claw prongs (cols 0-4 / 19-23, rows 17-27), split from the body by a groove (col 4) ------
    OCT = [(1.0, 0.15), (0.5, 1.0), (-0.5, 1.0), (-1.0, 0.15), (-0.85, -0.6), (-0.3, -1.0), (0.3, -1.0), (0.85, -0.6)]
    CX = Pchip([(17.0, 3.6), (18.5, 3.0), (20.5, 2.45), (22.5, 2.0), (24.0, 2.1), (25.5, 2.9), (27.1, 3.6)])
    CW = Pchip([(17.0, 0.3), (17.8, 0.85), (19.0, 0.95), (19.8, 1.05), (20.3, 1.6), (21.6, 2.02), (24.5, 2.02), (25.6, 1.95),
                (26.4, 1.5), (27.0, 0.7), (27.25, 0.3)])
    CL = [(r, CX(r), CW(r)) for r in (17.2, 17.6, 18.1, 18.7, 19.4, 20.1, 20.8, 21.5, 22.3, 23.1, 23.9, 24.6, 25.2,
                                       25.8, 26.3, 26.7, 27.0, 27.2)]
    for side in (-1, 1):
        rr = []
        for r, cx, hw in CL:
            c0 = cx if side < 0 else 2 * AX - cx
            ht = 0.7 + 1.1 * min(1.0, hw / 2.0)
            pts = [G.P(c0 + x * hw, r, (z * (ht if z > 0 else 1.3) + 0.4) * PX) for x, z in OCT]
            rr.append(verts(bm, pts))
        rr.insert(0, verts(bm, [G.P((3.6 if side < 0 else 2 * AX - 3.6), 16.9, 0.3 * PX)]))
        rr.append(verts(bm, [G.P((3.6 if side < 0 else 2 * AX - 3.6), 27.3, 0.4 * PX)]))
        loft(bm, rr, lambda k: (CLAW_TOP if k == 1 else CLAW) if k < 3 else (CLAW if k in (3, 7) else BELLY), smooth=True)
        # the groove web joining claw and body (col 4, rows 18-23): low dark fillet
        cg = 4.5 if side < 0 else 2 * AX - 4.5
        web = [verts(bm, [G.P(cg + x, r, dz * PX) for x, dz in ((-0.9, -1.2), (0.9, -1.2), (0.9, 0.2), (-0.9, 0.2))])
               for r in (17.9, 24.0)]
        loft(bm, web, GROOVE, smooth=False)
    obj = finish("newshv-159", bm, M, coll, sharp_deg=38)
    return obj, M


# --------------------------------------------------------------------------------------------------
# newshv-171: the dropped capsule
# --------------------------------------------------------------------------------------------------

def build_171(coll):
    M = Mats("newshv-171")
    G = Grid(12, 14)
    BODYM = M(59, **STEEL)
    GROOVE = M(56, **STEEL)  # cols 3 / 8: the sprite sits 1-2 indices under the neighbours (median 56)
    BAND = M(60, metallic=0.4, roughness=0.32, spec=0.8)
    ENDM = M(57, **STEEL)
    DISC = M(55, 0.3, 0.5)
    R0 = 2.95  # radius px (rows 3-8: axis at row edge 6)
    bm = bmesh.new()
    N = 24

    def ring(c, rad):
        pts = []
        for k in range(N):
            a = 2 * math.pi * k / N
            pts.append(G.P(c, 6.0 - rad * math.cos(a), rad * math.sin(a) * PX))
        return verts(bm, pts)

    # stations along the axis (col edge, radius, material of the segment that follows)
    # Shallow V grooves (0.18 px) at cols 3 and 8: the sprite dips only 1-2 indices there, so the
    # capsule keeps its soft bright-centre gradient; softly rounded end chamfers.
    GR = R0 - 0.18
    st = [(1.0, 2.6, ENDM), (1.08, 2.82, ENDM), (1.3, 2.95, ENDM), (1.75, R0, BODYM), (2.9, R0, GROOVE),
          (3.5, GR, GROOVE), (4.1, R0, BODYM), (4.85, R0, BAND), (4.95, 3.05, BAND),
          (7.05, 3.05, BODYM), (7.15, R0, BODYM), (7.9, R0, GROOVE), (8.5, GR, GROOVE),
          (9.1, R0, BODYM), (10.25, R0, ENDM), (10.7, 2.95, ENDM), (10.92, 2.82, ENDM), (11.0, 2.6, ENDM)]
    rings = [ring(c, rad) for c, rad, _ in st]
    for i in range(len(rings) - 1):
        loft(bm, [rings[i], rings[i + 1]], st[i][2], smooth=True, cap0=False, cap1=False)
    # shallow recessed end discs
    for c0, c1 in ((1.0, 1.18), (11.0, 10.82)):
        a = ring(c0, 2.6)
        b = ring(c0 + (c1 - c0) * 0.4, 2.2)
        cc = ring(c1, 2.2)
        loft(bm, [a, b], ENDM, smooth=False, cap0=False, cap1=False)
        loft(bm, [b, cc], DISC, smooth=False, cap0=False, cap1=True)
    obj = finish("newshv-171", bm, M, coll, sharp_deg=40)
    return obj, M


# --------------------------------------------------------------------------------------------------
# Review renders
# --------------------------------------------------------------------------------------------------

def review(obj, shell, w, h, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    shell.hide_render = True
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    eng = None
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            eng = e
            break
        except TypeError:
            pass
    if "sun" not in bpy.data.objects:
        sd = bpy.data.lights.new("sun", "SUN")
        sd.energy = 3.0
        sun = bpy.data.objects.new("sun", sd)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(15))
        scene.world.use_nodes = True
        bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
        bgn.inputs[0].default_value = (0.06, 0.065, 0.075, 1)
        bgn.inputs[1].default_value = 3.0
    sh = scene.display.shading

    def cam(loc, look, ortho=None, lens=50, rx=600, ry=600, rot=None):
        d = bpy.data.cameras.new("cam")
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new("cam", d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot if rot else (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry

    def shot(path, flat=False, transparent=False):
        if not flat and eng:
            scene.render.engine = eng
        else:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh.light = "FLAT"
            sh.color_type = "MATERIAL"
            sh.show_cavity = False
            sh.show_object_outline = False
            sh.show_specular_highlight = False
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    k = 20
    big = max(w, h) / 12
    cam((0, 0, 40), (0, 0, 0), ortho=max(w, h) / 12, rx=w * k, ry=h * k, rot=(0, 0, 0))
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_lit.png", transparent=True)
    for nm, loc in (("side", (60, 0, 0)), ("front", (0, -60, 0)), ("rear", (0, 60, 0))):
        cam(loc, (0, 0, 0), ortho=big * 1.02, rx=500, ry=300)
        shot(out / f"{nm}.png")
    d = big * 2.1
    for nm, az, el in (("q_high", -35, 45), ("q_low", 140, 22)):
        a, e = math.radians(az), math.radians(el)
        cam(Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), (0, 0, 0),
            rx=600, ry=500)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam(Vector((0, -d * math.sin(t), d * math.cos(t))), (0, 0, 0), rx=600, ry=500)
    shot(out / "game.png")
    cam(Vector((0, -d * 3 * math.sin(t), d * 3 * math.cos(t))), (0, 0, 0), rx=200, ry=170)
    shot(out / "game_small.png")
    cam((0, 0, -40), (0, 0, 0), ortho=big * 1.05, rx=300, ry=300, rot=(math.pi, 0, 0))
    shot(out / "under.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else ["10", "159", "171"]
    rv = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    builders = {"10": (build_10, 24, 28), "159": (build_159, 24, 28), "171": (build_171, 12, 14)}
    stats = {}
    for key in only:
        fn, w, h = builders[key]
        name = f"newshv-{key}"
        coll = common.reset_collection(name)
        obj, M = fn(coll)
        sealed = obj.copy()  # D90/D118: outline shell from a sealed pre-cull copy
        sealed.data = obj.data.copy()
        coll.objects.link(sealed)
        bpy.context.view_layer.update()
        shell = common.outline_shell(sealed, coll, voxel=0.01 if key != "171" else 0.006, faces=2000, inside=0.004)
        shell.name = shell.data.name = f"{name}_outline"
        bpy.data.objects.remove(sealed, do_unlink=True)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        stats[name] = {"tris": tris, "pal": sorted({k[0] for k in M.slots})}
        print(name, "tris", tris)
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{name}", common.load_sprite(ROOT, name)["sprites"])
        if rv:
            review(obj, shell, w, h, rv / name)
    if rv:
        (rv / "stats.json").write_text(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
