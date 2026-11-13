"""newshc-191, a grey gun-tower craft (newshc.shp frames 191/193/195), episode 3.

What it is (brief + behaviour): it drifts up the screen on the sky layer in 3.5 BONUS and on the top
layer in 3.11 New Deli and fires aimed shots (tur 76): a flying gun platform. Its sprite is the
vertical mirror of batch 1's newshc-155 gun pod (assembly-newshc-165): the same blue hull, green
light panels, pink cannon and grey pods, so the families match (pal 56 hull, 37 panels, lamp 38
brightening 43/202, barrel 89, bore 82).

Read from the sprite (24x28, mirror symmetric about the column-12 edge, sprite up = forward):
- Grey TOWER (cols 8-15, rows 4-12, pal 1-10 ramp, median 5-6): a raised armoured housing with a
  rounded nose; two dark VENT slots on its roof (cols 9-10 and 13-14, rows 7-11, pal 1) either side
  of a centre ridge. Its bright and dark sides are sheen and shading (rubric).
- Two round PODS (cols 1/2-7 and 16-22, rows 10-17, 101-110, median 105) each with a round dark
  glass CANOPY on its forward top (cols 3-6, rows 11-13, 98-100 -> 99), ringed by grey.
- Pink CANNON (cols 9-14, rows 13-22, 82-95, median 89): read as a barrel elevated about 48 deg
  toward the front, muzzle just behind the tower: the dark ellipse (82/83, rows 15-17) is the bore
  seen from above (the deeper, rear part of the muzzle disc reads darkest), the pale crest down the
  middle of rows 17-22 is the barrel's sheen. It sits between two grey CHEEKS (cols 8 and 15, rows
  13-17) that carry its trunnions.
- Blue HULL (rows 14-24, 49-60, median 56 without the darkest steps) with the rear-centre notch
  (cols 11-12, row 24), chamfered rear corners; its outer rear corners are GREEN sloped panels
  (33-44, median 37) whose inner edge is a lit crease (the 59 diagonal, cols 5-8 rows 20-24).
- A LAMP strip in each green panel (cols 2-3, rows 21-23): 38 on 191, 42-44 on 193, 201-204 on 195;
  its surround 38/39 -> 40-41 -> 41-42. Frames change only these colours: one mesh, animated
  palette materials (D17).

Materials: pal_<index>; satin metal; glows metallic 1 / rough (D126/D173); F0 via Specular IOR Level
(D176). No textures folder exists for this model: no bake. Outline shell D51/D90 from a sealed copy,
one shell per loose island (common.outline_shell keeps only the largest).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshc-191.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshc-191"
U = 1 / 12
D2R = math.pi / 180


def P(c, r, h):
    """Sprite column edge c (east), row edge r (south), height h (px) -> Blender."""
    return Vector(((c - 12) * U, (14 - r) * U, h * U))


def crh(v):
    return v.x / U + 12, 14 - v.y / U, v.z / U


def lerp(a, b, t):
    return a + (b - a) * t


def interp(pts, x):
    """Piecewise linear through sorted (x, y)."""
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0) if x1 > x0 else 0
            return y0 + (y1 - y0) * t
    return pts[-1][1]


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------------------------------
# Materials

def pm(sprite, idx, tag, metallic=0.3, roughness=0.5, glow=0.0, frames=None, spec=None):
    m = common.palette_material(sprite, idx, f"{NAME}-{tag}", metallic=metallic, roughness=roughness,
                                emission_strength=glow, frames=frames)
    if spec is not None:  # D176
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = spec
                break
    return m


def materials(s):
    return {
        "tower": pm(s, 6, "tower", metallic=0.6, roughness=0.34, spec=0.7),
        "slot": pm(s, 1, "slot", metallic=0.3, roughness=0.8),
        "slat": pm(s, 3, "slat", metallic=0.5, roughness=0.5),
        "pod": pm(s, 105, "pod", metallic=0.4, roughness=0.32, spec=0.7),
        "glass": pm(s, 99, "glass", metallic=0.1, roughness=0.12, spec=0.9),
        "rim": pm(s, 102, "rim", metallic=0.55, roughness=0.4),
        "cheek": pm(s, 103, "cheek", metallic=0.55, roughness=0.36),
        "hull": pm(s, 56, "hull", metallic=0.45, roughness=0.38, spec=0.6),
        "crease": pm(s, 59, "crease", metallic=0.5, roughness=0.3, spec=0.7),
        "groove": pm(s, 52, "groove", metallic=0.4, roughness=0.55),
        "green": pm(s, 37, "green", metallic=0.4, roughness=0.42),
        "bezel": pm(s, 39, "bezel", metallic=0.45, roughness=0.45, glow=0.3, frames={193: 41, 195: 42}),
        "lamp": pm(s, 38, "lamp", metallic=1.0, roughness=0.75, glow=1.0, frames={193: 43, 195: 202}),
        "barrel": pm(s, 89, "barrel", metallic=0.3, roughness=0.34, spec=0.7),
        "band": pm(s, 86, "band", metallic=0.45, roughness=0.4),
        "bore": pm(s, 82, "bore", metallic=0.3, roughness=0.7),
        "pin": pm(s, 7, "pin", metallic=0.7, roughness=0.28),
        "nozzle": pm(s, 53, "nozzle", metallic=0.5, roughness=0.4),
        "nozzle_in": pm(s, 50, "nozzlein", metallic=0.3, roughness=0.7),
    }


# --------------------------------------------------------------------------------------------------
# Geometry accumulator (copied pattern from batch 1's scripts; not a shared helper)

class Geo:
    def __init__(self):
        self.v = []
        self.f = []  # (ids, key, smooth)

    def add_v(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def grid(self, rings, mat, closed=True, cap0=None, cap1=None, smooth=True, fan=True):
        """rings: lists of Vectors, same length. mat: key, or fn(centre_crh, i, j) -> key."""
        ids = [[self.add_v(p) for p in ring] for ring in rings]
        n = len(rings[0])
        for i in range(len(rings) - 1):
            for j in range(n if closed else n - 1):
                j2 = (j + 1) % n
                q = [ids[i][j], ids[i][j2], ids[i + 1][j2], ids[i + 1][j]]
                if callable(mat):
                    c = sum((self.v[k] for k in q), Vector()) / 4
                    m = mat(crh(c), i, j)
                else:
                    m = mat
                self.f.append((q, m, smooth))
        for ring_ids, cap, rev in ((ids[0], cap0, True), (ids[-1], cap1, False)):
            if cap is None:
                continue
            if fan:
                c = sum((self.v[k] for k in ring_ids), Vector()) / len(ring_ids)
                ci = self.add_v(c)
                for j in range(n):
                    tri = [ring_ids[j], ring_ids[(j + 1) % n], ci]
                    self.f.append((tri[::-1] if rev else tri, cap, False))
            else:
                self.f.append((ring_ids[::-1] if rev else list(ring_ids), cap, False))
        return ids

    def to_bm(self, keys):
        bm = bmesh.new()
        vs = [bm.verts.new(p) for p in self.v]
        for ids, m, sm in self.f:
            try:
                f = bm.faces.new([vs[i] for i in ids])
            except ValueError:
                continue
            f.material_index = keys.index(m)
            f.smooth = sm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        # drop degenerate faces left by collapsed rings
        bad = [f for f in bm.faces if f.calc_area() < 1e-10]
        if bad:
            bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm


def ring_about(centre, axis, radius, n=24, ref=Vector((1, 0, 0)), squash=1.0):
    """A circle of `radius` px around `axis` at `centre` (Blender units / directions)."""
    axis = axis.normalized()
    e1 = (ref - axis * ref.dot(axis)).normalized()
    e2 = axis.cross(e1)
    return [centre + e1 * (radius * U * math.cos(2 * math.pi * k / n)) +
            e2 * (radius * U * squash * math.sin(2 * math.pi * k / n)) for k in range(n)]


# --------------------------------------------------------------------------------------------------
# Hull: a loft down the rows; each section is a closed ring across the full width

def c_out(r):
    return interp([(12.6, 2.1), (13.4, 1.4), (14.2, 1.05), (21.9, 1.0), (22.5, 1.12), (23.0, 1.45), (23.5, 2.0), (24.0, 2.75),
                   (24.5, 3.6), (24.85, 4.4), (25.0, 4.9)], r)


def c_crease(r):
    return interp([(18.2, 1.0), (19.5, 3.0), (20.5, 4.1), (21.5, 5.0), (22.5, 5.25), (23.5, 6.05),
                   (24.5, 7.05), (25.0, 7.6)], r)


DECK = 2.25      # deck height at the crease (px)
CROWN = 2.5      # deck height on the axis
LIP = 0.35       # fender's outer lip height
SEAM_R = 18.75   # transverse panel line across the deck


def deck_h(c, r):
    x = abs(c - 12)
    return CROWN - (CROWN - DECK) * (x / 11) ** 2


def hull_half(r, drop=0.0, inset=0.0):
    """Left half of the section, from bottom centre round the outside to top centre: (c, h)."""
    co = c_out(r) + inset
    cc = max(c_crease(r), co + 0.35)
    groove = 0.25 if abs(r - SEAM_R) < 0.06 else 0.0
    top = lambda c: deck_h(c, r) - drop - groove  # noqa: E731
    pts = [(12.0, -1.0 + 0.0), (co + 1.0, -1.0), (co + 0.25, -0.75), (co, -0.2), (co, LIP - drop * 0.5)]
    for t in (0.33, 0.66):
        c = lerp(co, cc - 0.2, t)
        pts.append((c, lerp(LIP, DECK - 0.35, t ** 0.9) - drop * 0.7))
    pts += [(cc - 0.2, DECK - 0.3 - drop * 0.7), (cc, top(cc) - 0.05), (cc + 0.7, top(cc + 0.7))]
    for c in (lerp(cc + 0.7, 12, 0.35), lerp(cc + 0.7, 12, 0.7), 12.0):
        pts.append((c, top(c)))
    return pts


def hull_ring(r, **kw):
    half = hull_half(r, **kw)
    right = [(24 - c, h) for c, h in reversed(half[1:-1])]
    return [P(c, r, h) for c, h in half + right]


def fender_h(c, r):
    """Top height of the hull at (c, r) (for parts laid on it)."""
    co, cc = c_out(r), max(c_crease(r), c_out(r) + 0.35)
    if c >= cc:
        return deck_h(c, r)
    t = max(0.0, min(1.0, (c - co) / max(cc - 0.2 - co, 1e-3)))
    return lerp(LIP, DECK - 0.35, t ** 0.9)


def hull_mat(p, i, j):
    c, r, h = p
    x = c if c <= 12 else 24 - c
    if h < 0.0:
        return "hull"
    cc = c_crease(r)
    if abs(r - SEAM_R) < 0.07 and x > cc + 0.1:
        return "groove"
    if r > 18.0 and x < cc - 0.05:
        return "green"
    if r > 19.2 and x < cc + 0.8:
        return "crease"
    return "hull"


def build_hull(g):
    rs = [12.9, 13.4, 14.2, 14.6, 15.5, 16.5, 17.5, 18.2, SEAM_R - 0.18, SEAM_R - 0.05, SEAM_R + 0.05, SEAM_R + 0.18,
          19.5, 20.5, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.4, 24.7]
    rings = [hull_ring(12.6, drop=0.5, inset=0.3)] + [hull_ring(r) for r in rs]
    rings += [hull_ring(24.9, drop=0.25), hull_ring(25.0, drop=0.6, inset=0.15)]
    g.grid(rings, hull_mat, cap0="hull", cap1="hull", fan=True)


HULL_SLOT = 0


def notch_cut(obj):
    """Cut the rear-centre notch (cols 11-12, row 24) with an exact boolean."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        c = 11.05 if v.co.x < 0 else 12.95
        r = 24.15 if v.co.y > 0 else 25.8
        h = -3.0 if v.co.z < 0 else 4.0
        v.co = P(c, r, h)
    # round the notch's inner end a little: bevel its two inner vertical edges
    for f in bm.faces:
        f.material_index = HULL_SLOT
    me = bpy.data.meshes.new("notch_cutter")
    bm.to_mesh(me)
    for m in obj.data.materials:
        me.materials.append(m)
    bm.free()
    cut = bpy.data.objects.new("notch_cutter", me)
    bpy.context.scene.collection.objects.link(cut)
    mod = obj.modifiers.new("notch", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cut
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cut, do_unlink=True)


def build_nozzles(g):
    """Two thruster nozzles let into the hull's rear face (seen by the tilted camera)."""
    ax = Vector((0, -1, 0))  # pointing back (south)
    for c in (7.9, 16.1):
        rings = [ring_about(P(c, 24.4, 0.75), ax, 0.95, 12),
                 ring_about(P(c, 25.08, 0.75), ax, 0.95, 12),
                 ring_about(P(c, 25.08, 0.75), ax, 0.62, 12),
                 ring_about(P(c, 24.75, 0.75), ax, 0.62, 12)]
        g.grid(rings, lambda p, i, j: "nozzle" if i < 2 else "nozzle_in", cap0="nozzle", cap1="nozzle_in",
               smooth=True)


def build_lamps(g):
    """Lamp strip with a bezel in each green panel (pixels (21,2) (22,2) (23,3) and mirror)."""
    path = [(2.3, 20.7), (2.45, 21.5), (2.6, 22.4), (3.1, 23.2), (3.8, 23.85)]
    for mirror in (False, True):
        for key, hw, hh, lift, ext in (("bezel", 0.95, 0.16, 0.06, 0.45), ("lamp", 0.5, 0.22, 0.2, 0.0)):
            pts = list(path)
            if ext:  # extend the bezel a little past both ends of the lamp
                (c0, r0), (c1, r1) = pts[0], pts[1]
                d = math.hypot(c1 - c0, r1 - r0)
                pts.insert(0, (c0 - (c1 - c0) / d * ext, r0 - (r1 - r0) / d * ext))
                (c0, r0), (c1, r1) = pts[-2], pts[-1]
                d = math.hypot(c1 - c0, r1 - r0)
                pts.append((c1 + (c1 - c0) / d * ext, r1 + (r1 - r0) / d * ext))
            rings = []
            n = len(pts)
            for k, (c, r) in enumerate(pts):
                (ca, ra), (cb, rb) = pts[max(0, k - 1)], pts[min(n - 1, k + 1)]
                t = Vector((cb - ca, rb - ra, 0)).normalized()  # along, in (c, r)
                side = Vector((-t.y, t.x, 0))  # across, in (c, r)
                e = 0.05
                dh_c = (fender_h(c + e, r) - fender_h(c - e, r)) / (2 * e)
                dh_r = (fender_h(c, r + e) - fender_h(c, r - e)) / (2 * e)
                nrm = Vector((-dh_c, -dh_r, 1)).normalized()  # surface normal in (c, r, h)
                taper = 0.35 if k in (0, n - 1) else 1.0
                base = Vector((c, r, fender_h(c, r) + lift))
                ring = []
                sides = 8
                for s in range(sides):
                    a = 2 * math.pi * s / sides
                    q = base + side * (hw * taper * math.copysign(abs(math.cos(a)) ** 0.6, math.cos(a))) + \
                        nrm * (hh * taper * math.sin(a))
                    cc = 24 - q.x if mirror else q.x
                    ring.append(P(cc, q.y, q.z))
                if mirror:
                    ring.reverse()
                rings.append(ring)
            g.grid(rings, key, cap0=key, cap1=key)


# --------------------------------------------------------------------------------------------------
# Tower

T_ROOF = 7.4
T_FRONT, T_BACK = 3.9, 12.9


def t_w(r):
    """Tower half width (px) at row edge r: a rounded nose, straight sides."""
    if r >= 5.9:
        return 4.0
    t = (5.9 - r) / (5.9 - T_FRONT + 0.02)
    return 4.0 * max(0.0, 1 - t ** 2.4) ** (1 / 2.4)


def t_h(r):
    if r >= 6.0:
        h = T_ROOF
    else:
        t = (6.0 - r) / (6.0 - T_FRONT + 0.05)
        h = 3.2 + (T_ROOF - 3.2) * math.sqrt(max(0.0, 1 - t * t))
    if abs(r - 6.6) < 0.06:  # panel line across the roof, ahead of the vents
        h -= 0.22
    return h


def slot_d(r):
    """Vent depth: a ramped intake starting at row 7, a steep back wall at row 11.6."""
    if r < 7.0 or r > 11.6:
        return 0.0
    return 1.9 * smoothstep(7.0, 8.4, r) * (1 - smoothstep(11.35, 11.6, r))


def tower_half(r):
    w, H, d = t_w(r), t_h(r), slot_d(r)
    k = w / 4.0
    return [(0.0, -1.0), (3.7 * k, -1.0), (4.0 * k, -0.4), (4.0 * k, 2.2), (3.84 * k, 2.32), (3.84 * k, 2.68),
            (4.0 * k, 2.8), (4.0 * k, H - 2.2), (3.9 * k, H - 1.0),
            (3.55 * k, H - 0.32), (3.1 * k, H - 0.04), (2.95 * k, H), (2.85 * k, H - d), (1.15 * k, H - d),
            (1.05 * k, H), (0.0, H)]


def tower_ring(r):
    half = tower_half(r)
    left = [(12 - x, h) for x, h in half]
    right = [(12 + x, h) for x, h in reversed(half[1:-1])]
    return [P(c, r, h) for c, h in left + right]


def tower_mat(p, i, j):
    c, r, h = p
    x = abs(c - 12)
    H = t_h(r)
    if 6.8 < r < 11.7 and 0.95 < x < 3.05 and 3.0 < h < T_ROOF - 0.12:
        return "slot"
    if abs(r - 6.6) < 0.1 and h > H - 0.05 and x < 3.2:
        return "slat"
    if 2.25 < h < 2.75 and x > 3.6 * t_w(r) / 4.0:  # belt groove round the tower
        return "slat"
    return "tower"


def build_tower(g):
    rs = [T_FRONT + 0.03, 4.0, 4.2, 4.5, 4.9, 5.4, 5.9, 6.3, 6.54, 6.66, 6.9, 7.0, 7.3, 7.7, 8.1, 8.4, 9.5, 10.5,
          11.2, 11.35, 11.5, 11.6, 11.7, 12.5, T_BACK]
    rings = [tower_ring(r) for r in rs]
    # rear edge chamfer
    last = [P(*(lambda q: (12 + (q[0] - 12) * 0.96, T_BACK + 0.1, q[2] - 0.25 if q[2] > 1 else q[2]))(crh(v)))
            for v in rings[-1]]
    rings.append(last)
    g.grid(rings, tower_mat, cap0="tower", cap1="tower")
    # louvre slats across each vent
    for side in (-1, 1):
        for r in (9.1, 10.3):
            x0, x1 = 1.1, 2.9
            h1 = T_ROOF - 0.45
            rings = []
            for rr in (r - 0.17, r + 0.17):
                rings.append([P(12 + side * x0, rr, h1 - 1.4), P(12 + side * x1, rr, h1 - 1.4),
                              P(12 + side * x1, rr, h1), P(12 + side * x0, rr, h1)])
            g.grid(rings, "slat", cap0="slat", cap1="slat", smooth=False, fan=False)


# --------------------------------------------------------------------------------------------------
# Pods

POD_C, POD_R, POD_H = 4.82, 13.95, 3.85
POD_RX, POD_RY, POD_RZ = 3.27, 3.95, 3.0
POD_UNDER = 0.72      # underside flattening
CAN_TILT = 25 * D2R   # canopy axis tilt forward from vertical
CAN_HALF = 31 * D2R   # canopy half angle


def pod_point(side, th, ph, bulge=1.0):
    a = Vector((0, -math.sin(CAN_TILT), math.cos(CAN_TILT)))  # (c, r, h) unit-sphere space
    e1 = Vector((1, 0, 0))
    e2 = a.cross(e1)
    u = a * math.cos(th) + (e1 * math.cos(ph) + e2 * math.sin(ph)) * math.sin(th)
    z = u.z * (POD_UNDER if u.z < 0 else 1.0)
    c = POD_C + u.x * POD_RX * bulge
    if side > 0:
        c = 24 - c
    return P(c, POD_R + u.y * POD_RY * bulge, POD_H + z * POD_RZ * bulge)


def build_pods(g):
    ths = [0.0, 10, 20, CAN_HALF / D2R, 32.3, 33.5, 34.8, 36.2, 48, 62, 76, 90, 99.2, 100, 101.6, 102.4,
           116, 132, 150, 168]
    bul = {100: 0.975, 101.6: 0.975, 0.0: 1.035, 10: 1.033, 20: 1.022, CAN_HALF / D2R: 1.008, 32.3: 0.985, 33.5: 0.985, 34.8: 1.0}
    n = 24
    for side in (-1, 1):
        rings = []
        for t in ths:
            ring = [pod_point(side, max(t, 0.5) * D2R, 2 * math.pi * k / n, bul.get(t, 1.0)) for k in range(n)]
            if side > 0:
                ring.reverse()
            rings.append(ring)

        def mat(p, i, j):
            if i < 3:
                return "glass"
            if i < 6:
                return "rim"
            if i in (12, 13, 14):
                return "rim"
            return "pod"
        g.grid(rings, mat, cap0="glass", cap1="pod")
        # pylon from the pod's inner flank into the cheek
        c0, c1 = POD_C + 2.4, 8.6
        if side > 0:
            c0, c1 = 24 - c0, 24 - c1
        ax = Vector((1, 0, 0))
        rings = [ring_about(P(c, 14.4, 3.7), ax, rr, 16, ref=Vector((0, 0, 1)))
                 for c, rr in ((c0, 1.05), (lerp(c0, c1, 0.5), 1.05), (lerp(c0, c1, 0.55), 1.25),
                               (lerp(c0, c1, 0.75), 1.25), (lerp(c0, c1, 0.8), 1.05), (c1, 1.05))]
        if side > 0:
            rings = [list(reversed(rg)) for rg in rings]
        g.grid(rings, lambda p, i, j: "rim" if i in (2, 3) else "cheek", cap0="cheek", cap1="cheek")
        # shoulder fairing: the pod's mounting arm, from its inner top into the tower flank
        rings = []
        for r, c0, top in ((9.35, 7.15, 3.9), (9.7, 6.6, 4.5), (10.2, 6.05, 4.8), (11.0, 5.9, 4.9),
                           (12.2, 5.9, 4.7), (12.8, 6.2, 4.0)):
            sec = [(8.6, 1.0), (c0 + 0.4, 1.0), (c0, top - 0.8), (c0 + 0.35, top - 0.15), (c0 + 0.9, top),
                   (8.6, top + 0.2)]
            ring = [P(24 - c if side > 0 else c, r, h) for c, h in sec]
            if side > 0:
                ring.reverse()
            rings.append(ring)
        g.grid(rings, "cheek", cap0="cheek", cap1="cheek", smooth=True, fan=False)


# --------------------------------------------------------------------------------------------------
# Cannon and its cheeks

ELEV = 48 * D2R
MUZZLE = (12.0, 15.2, 7.8)
B_AXIS = Vector((0, -math.cos(ELEV), math.sin(ELEV)))  # (c, r, h): toward the front and up


def b_pt(s):
    """Point on the barrel axis s px back from the muzzle, as (c, r, h)."""
    m = Vector(MUZZLE)
    return m - B_AXIS * s


def build_cannon(g):
    axis_bl = (P(*b_pt(-1)) - P(*b_pt(0))).normalized()  # Blender direction of +axis
    st = [(8.5, 0.9, "barrel"), (8.2, 2.05, "barrel"), (7.85, 2.6, "barrel"), (7.6, 2.75, "barrel"),
          (4.6, 2.75, "barrel"), (4.45, 2.6, "band"), (4.25, 2.6, "band"), (4.1, 2.75, "barrel"),
          (2.75, 2.75, "barrel"), (2.65, 2.97, "band"), (1.9, 2.97, "band"), (1.8, 2.75, "barrel"),
          (1.55, 2.75, "barrel"), (1.45, 3.05, "barrel"), (0.0, 3.05, "barrel"), (0.0, 2.15, "barrel"),
          (1.9, 2.15, "bore")]
    n = 22
    rings = [ring_about(P(*b_pt(s)), axis_bl, rad, n) for s, rad, _ in st]
    keys = [k for _, _, k in st]

    def mat(p, i, j):
        k = keys[i + 1] if keys[i + 1] in ("band",) and keys[i] == "band" else keys[i]
        if i == len(st) - 2:
            return "bore"
        if keys[i] == "band" and keys[i + 1] == "band":
            return "band"
        return "barrel"
    g.grid(rings, mat, cap0="barrel", cap1="bore")
    # trunnion pins through the cheeks
    piv = b_pt(2.3)
    for side in (-1, 1):
        c0, c1 = 12 + side * 2.6, 12 + side * 4.35
        rings = [ring_about(P(c, piv.y, piv.z), Vector((1, 0, 0)), rr, 10, ref=Vector((0, 0, 1)))
                 for c, rr in ((c0, 0.9), (c1, 0.9), (c1 + side * 0.25, 0.65))]
        if side < 0:
            rings = [list(reversed(rg)) for rg in rings]
        g.grid(rings, "pin", cap0="pin", cap1="pin")


def cheek_top(r):
    return interp([(12.4, 7.1), (16.6, 7.1), (17.3, 6.7), (17.9, 5.7), (18.3, 4.3), (18.5, 2.6)], r)


def build_cheeks(g):
    rs = [12.4, 13.5, 15.0, 16.6, 17.0, 17.3, 17.6, 17.9, 18.15, 18.35, 18.5]
    for side in (-1, 1):
        c_in, c_out_ = (9.0, 8.0) if side < 0 else (15.0, 16.0)
        rings = []
        for r in rs:
            t = cheek_top(r)
            sec = [(c_out_, -0.9), (c_in, -0.9), (c_in, t - 0.25), (lerp(c_in, c_out_, 0.2), t),
                   (lerp(c_in, c_out_, 0.8), t), (c_out_, t - 0.25)]
            ring = [P(c, r, h) for c, h in sec]
            if side > 0:
                ring.reverse()
            rings.append(ring)
        g.grid(rings, "cheek", cap0="cheek", cap1="cheek", smooth=False, fan=False)


# --------------------------------------------------------------------------------------------------

def build(coll, sprite):
    mats = materials(sprite)
    keys = list(mats)
    # hull first (it takes the boolean), then everything else
    gh = Geo()
    build_hull(gh)
    bm = gh.to_bm(keys)
    me = bpy.data.meshes.new("hull_tmp")
    bm.to_mesh(me)
    bm.free()
    hull = bpy.data.objects.new("hull_tmp", me)
    coll.objects.link(hull)
    for k in keys:
        me.materials.append(mats[k])
    global HULL_SLOT
    HULL_SLOT = keys.index("hull")
    notch_cut(hull)

    g = Geo()
    build_tower(g)
    build_pods(g)
    build_cheeks(g)
    build_cannon(g)
    build_lamps(g)
    build_nozzles(g)
    bm = g.to_bm(keys)
    bm.from_mesh(hull.data)  # append the cut hull (same material slot order)
    bpy.data.objects.remove(hull, do_unlink=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for k in keys:
        mesh.materials.append(mats[k])
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    # drop unused slots
    used = sorted({p.material_index for p in mesh.polygons})
    remap = {u: i for i, u in enumerate(used)}
    orig = [p.material_index for p in mesh.polygons]
    for i in reversed(range(len(mesh.materials))):
        if i not in used:
            mesh.materials.pop(index=i)
    for p, mi in zip(mesh.polygons, orig):
        p.material_index = remap[mi]
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    except Exception:
        pass
    obj.select_set(False)
    return obj, [mesh.materials[i] for i in range(len(mesh.materials))]


def outline_shells(obj, coll, voxel=0.016, faces=1600, smooth=6, inside=0.004, min_share=0.04):
    """common.outline_shell, keeping EVERY outer island (not only the largest): one sealed, smoothed,
    decimated shell per loose part (copy of the shared helper's steps; it should grow this option)."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{NAME}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    _apply(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def box(isl):
        xs = [v.co.x for v in isl]
        ys = [v.co.y for v in isl]
        zs = [v.co.z for v in isl]
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

    def area(b):
        return (b[1] - b[0]) * (b[3] - b[2])
    boxes = [box(i) for i in islands]
    big = max(area(b) for b in boxes)
    keep = []
    for isl, b in zip(islands, boxes):
        if area(b) < min_share * big:
            continue
        # an island inside another island's box is an inner wall: drop it
        inner = any(o is not b and o[0] <= b[0] and o[1] >= b[1] and o[2] <= b[2] and o[3] >= b[3]
                    and o[4] <= b[4] and o[5] >= b[5] and area(o) > area(b) for o in boxes)
        if not inner:
            keep.append(isl)
    keep_ids = {v.index for isl in keep for v in isl}
    print(f"outline: {len(islands)} islands, keeping {len(keep)}")
    for b in boxes:
        print("  island px c %.1f-%.1f r %.1f-%.1f h %.1f-%.1f" % (b[0] / U + 12, b[1] / U + 12, 14 - b[3] / U,
                                                                 14 - b[2] / U, b[4] / U, b[5] / U))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep_ids], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    _apply(shell)
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -inside
        _apply(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def _apply(o):
    for x in bpy.context.view_layer.objects:
        x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    for mod in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj, mats = build(coll, sprite)
    obj.data.calc_loop_triangles()
    print(f"{NAME}: {len(obj.data.polygons)} faces, {len(obj.data.loop_triangles)} triangles")
    shell = outline_shells(obj, coll)
    shell.name = shell.data.name = f"{NAME}_outline"
    print(f"outline: {len(shell.data.polygons)} faces")
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])



if __name__ == "__main__":
    main()
