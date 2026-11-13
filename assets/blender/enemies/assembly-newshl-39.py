"""assembly-newshl-39, design A: the upper 48 x 56 px of TIME WAR's (4.17) grey thruster capsule, newshl-1 | 3 over
newshl-39 | 41. Its lower 48 x 28 is assembly-newshl-77 (newshl 77 + 79, batch e4-enemies-1), rigid on the same link.

What it is (behaviour dump): types 653-656, armour 255, on the sky layer, two of them spawned at t110 at x=64 and
x=136, swooping in (0,+2), hovering, then drifting (0,+1). A hovering craft, not grounded: the sprite is the top
view of a capsule lying along the screen, its exhaust (newshl-77/79's red bar) at the down-screen end.

Read from the sprite, down the screen (rows of the 48 x 56 assembly, cols of the 48 px width, axis col 24):
- a mushroom cap (rows 4-14, 27 px wide), a domed lens with a blunt front, a small dark nose stub (row 4), and two
  louvred intake grilles in its front half (cols 19-23 and 25-29, rows 5-9: dark walls and two lit slats each),
  either side of a spine strip (col 24) that runs down the whole machine;
- a narrow neck drum (rows 14-17, its dark row 17 the lip's shadow);
- the body (rows 18-55): a forward lip ring (row 18, the groove of row 19 behind it); a tall round core column
  (cols 20-28) carrying the spine and, mid-way, a raised rounded-square housing with a dark dish (the "dark disc",
  rows 33-47); either side of the core a recessed channel with a glowing red tube (cols 16-18 / 30-32, rows 23-55)
  held by dark clamp bands (rows 32-33, 36, 42, 46), fed at its top by a short grey pipe (cols 15-16 / 32-33, rows
  20-23); outboard of each channel a side pod (rows 20-27 upper, a deep notch at rows 27-28, rows 29-55 lower, a
  groove at row 51).
The sprite's right side draws the gaps between core, tube, pipe and pod see-through (col 29 rows 22-55, col 31 rows
22-24, col 34 rows 20-23, col 33 rows 25-28, row 19 cols 31-33, row 24 cols 31-34): those are cut through the hull
(the outline rule); the same gaps on the left are drawn dark and are channel floor (pal 3).

Colours (median palette index per region, darkest / brightest 15% left out as lighting): cap 6, neck 4, lip 5, core
6, pods 4, pipes 6, tube glow 115 (hot bands 118), clamp bands 112, channel floor 3, housing rim 7, dish 3. Satin
steel as assembly-newshl-77 (metallic 0.7, roughness 0.25, Specular IOR Level 0.5); glows metallic 1 / rough 0.9.

Units: c, r = sprite px EDGES of the 48 x 56 assembly (col 3 spans c 3..4); X = (c - 24) / 12, Y = (28 - r) / 12,
z in px / 12. The capsule axis is c = 24.5, z = 0 (top and bottom symmetric in height, as newshl-77; the underside
is a plain closed shape).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshl-39.py
Exports enemies/newshl-1, -3, -39, -41 (glb + spriteModels JSON). Review renders only behind
-- --review <dir> (and --with77 <glb> to show the base beside it).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()
WT = next(c for c in HERE.parents if (c / "assets" / "blender" / "common.py").exists())
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import sprite_data  # noqa: E402

NAME = "assembly-newshl-39"
PIECES = ["newshl-1", "newshl-3", "newshl-39", "newshl-41"]
ROOT = common.repo_root(__file__)
PX = 1 / 12
AX = 24.5
W, H = 48, 56

STEEL = dict(metallic=0.7, roughness=0.25, spec=0.5)  # assembly-newshl-77's HULL (metallic 0.7, roughness 0.24)
BODY = dict(metallic=0.1, roughness=0.45, spec=0.5)  # the body's greys: mostly dielectric satin, so the core spine
#                                                    reads light grey in game (not the env's dark reflection)
GLOW = dict(metallic=1.0, roughness=0.9)


def load_sprite(name):
    """The catalogue doesn't list these four pieces (no reference/models/newshl-1 etc.), so each one's
    frame is read from the game data (tools/sprite_data.py)."""
    return sprite_data.load(ROOT, name, "newshl.shp", [int(name.split("-")[1])])


# Piece centres relative to the 48 x 56 block's centre, in px (the spawn offsets: dx 0/24, dy -28/0).
LAYOUT = [("newshl-1", -12, -14), ("newshl-3", 12, -14), ("newshl-39", -12, 14), ("newshl-41", 12, 14)]


# --------------------------------------------------------------------------------------------------
# Materials (as assembly-newshl-77: palette index per region, satin steel, glows D126/D173, F0 D176)
# --------------------------------------------------------------------------------------------------

class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.82, roughness=0.42, emit=0.0, spec=0.5):
        key = (index, metallic, roughness, emit, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nshl39A{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if spec is not None and "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


# --------------------------------------------------------------------------------------------------
# Geometry helpers (copied from assembly-newshl-77 design: pchip, loft, chamfer box, boolean cut)
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

    def __init__(self, xs, ys):
        self.x, self.y = list(xs), list(ys)
        self.m = _slopes(self.x, self.y) if len(xs) > 1 else [0.0]

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
    return Vector(((c - 24) * PX, (28 - r) * PX, z * PX))


def verts(bm, pts):
    return [bm.verts.new(p) for p in pts]


def loft(bm, rings, mat, smooth=True, cap0=True, cap1=True, cap_mat=None, closed=True):
    mf = mat if callable(mat) else (lambda i, k: mat)
    n = len(rings[0])
    out = []
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        for k in range(n if closed else n - 1):
            j = (k + 1) % n
            try:
                f = bm.faces.new((a[k], b[k], b[j], a[j]))
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


def chbox(bm, c0, c1, r0, r1, z0, z1, ch, mat, chz=None):
    chz = ch if chz is None else chz
    pts = []
    for c, sc in ((c0, 1), (c1, -1)):
        for r, sr in ((r0, 1), (r1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(c + sc * ch, r, z + sz * chz), (c, r + sr * ch, z + sz * chz), (c + sc * ch, r + sr * ch, z)]
    hull_pts(bm, [P(*p) for p in pts], mat)


def cut_into(bm, prism, wall_mat, nmat):
    """Boolean-subtract the closed cutter(s) built by `prism(cb)` from the shell in bm (exact solver)."""
    me = bpy.data.meshes.new("_shell")
    cm = bpy.data.meshes.new("_cut")
    slots = [bpy.data.materials.new("_slot") for _ in range(nmat)]
    for m in (me, cm):
        for sl in slots:
            m.materials.append(sl)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    shell = bpy.data.objects.new("_shell", me)
    cb = bmesh.new()
    prism(cb)
    for f in cb.faces:
        f.material_index = wall_mat
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


def box_prisms(boxes):
    """Cutter of several axis-aligned boxes (c0, c1, r0, r1, z0, z1)."""
    def make(cb):
        for c0, c1, r0, r1, z0, z1 in boxes:
            lo = verts(cb, [P(c, r, z0) for c, r in ((c0, r0), (c1, r0), (c1, r1), (c0, r1))])
            hi = verts(cb, [P(c, r, z1) for c, r in ((c0, r0), (c1, r0), (c1, r1), (c0, r1))])
            loft(cb, [lo, hi], 0, smooth=False)
    return make


def ellipsoid(bm, centre, radii, mat, segments=16, rings=10):
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * radii[0], cy + v.co.y * radii[1], cz + v.co.z * radii[2]))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


def tube_y(bm, c, z, stations, mat_of, sides=16, cap0=True, cap1=True):
    """A round tube along the screen at (c, z): stations (r, radius); mat_of(i) per span."""
    rings = []
    for r, rad in stations:
        rings.append(verts(bm, [P(c + rad * math.cos(2 * math.pi * k / sides), r,
                                  z + rad * math.sin(2 * math.pi * k / sides)) for k in range(sides)]))
    return loft(bm, rings, lambda i, k: mat_of(i), smooth=True, cap0=cap0, cap1=cap1)


def merge(bm, other):
    me = bpy.data.meshes.new("_merge")
    other.to_mesh(me)
    other.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


# --------------------------------------------------------------------------------------------------
# The hull: one closed loft down the screen, one section function for cap, neck, lip and body
# --------------------------------------------------------------------------------------------------

CORE_W = 4.5     # core column half width (cols 20-28)
# Stations: r -> (wl, wr, h, core_h, trough, pod_in_l, pod_in_r, floor, spine). wl / wr: plan half widths
# (D74 inner mask, row centres); h: the outer (pod / cap) half height; core_h: the core column's crest;
# trough 0..1: how far the channels between core and pods are sunk (to `floor`); pod_in: where the pods'
# inner walls stand (px from the axis); spine: the spine strip's height over the crest.
K = ["wl", "wr", "h", "core", "tr", "pil", "pir", "floor", "spine"]
ST = [
    # cap: blunt rounded nose, domed lens, overhanging the neck (mushroom)
    (4.85, 6.4, 6.4, 1.0, 0.0, 0, 10, 10, 2, 0.0),
    (5.05, 8.2, 8.2, 2.2, 0.0, 0, 10, 10, 2, 0.15),
    (5.5, 9.6, 9.0, 3.3, 0.0, 0, 10, 10, 2, 0.35),
    (6.5, 11.5, 9.4, 4.7, 0.0, 0, 10, 10, 2, 0.35),
    (7.5, 12.8, 11.9, 5.6, 0.0, 0, 10, 10, 2, 0.35),
    (8.5, 13.4, 13.3, 6.1, 0.0, 0, 10, 10, 2, 0.35),
    (10.5, 13.5, 13.4, 6.35, 0.0, 0, 10, 10, 2, 0.35),
    (12.5, 13.4, 13.3, 6.2, 0.0, 0, 10, 10, 2, 0.35),
    (13.5, 12.4, 12.4, 5.5, 0.0, 0, 10, 10, 2, 0.35),
    (14.5, 11.5, 11.5, 4.5, 0.0, 0, 10, 10, 2, 0.35),
    # neck drum
    (14.9, 9.6, 9.5, 4.0, 0.0, 0, 10, 10, 2, 0.35),
    (16.6, 9.4, 9.4, 4.0, 0.0, 0, 10, 10, 2, 0.35),
    (16.95, 9.3, 9.3, 4.0, 0.0, 0, 10, 10, 2, 0.35),
    # row 17, the lip's shadow: the drum steps in under the lip (ink at col 15 / col 31)
    (17.15, 8.5, 6.5, 3.9, 0.0, 0, 10, 10, 2, 0.35),
    (17.85, 8.6, 6.6, 4.0, 4.2, 0, 10, 10, 2, 0.35),
    # lip ring (row 18) and its groove (row 19)
    (18.1, 11.4, 8.8, 5.5, 5.9, 0, 10, 10, 2, 0.35),
    (19.0, 12.2, 10.8, 5.6, 6.0, 0, 10, 10, 2, 0.35),
    (19.35, 12.4, 11.4, 5.4, 5.8, 0, 10, 10, 2, 0.35),
    (19.6, 12.4, 11.2, 4.7, 5.4, 0.0, 10.5, 10.5, 2.0, 0.35),
    # upper body: pods (cols 11-13 / 35-36) outboard of a wide channel holding the feed pipes; row 20 is
    # one px narrower both sides (ink at col 11 / col 36), rows 21-25 full width, row 26 in on the left
    (19.85, 12.4, 11.6, 4.9, 6.4, 1.0, 10.4, 10.4, 2.0, 0.35),
    (20.4, 12.45, 11.65, 5.0, 6.7, 1.0, 10.5, 10.5, 2.0, 0.35),
    (20.95, 13.45, 12.45, 5.0, 6.7, 1.0, 10.5, 10.5, 2.0, 0.35),
    (25.9, 13.45, 12.45, 5.0, 6.7, 1.0, 10.5, 10.5, 2.0, 0.35),
    (26.1, 12.5, 12.45, 5.0, 6.7, 1.0, 10.5, 10.5, 2.0, 0.35),
    (26.9, 12.5, 12.45, 5.0, 6.7, 1.0, 10.5, 10.5, 2.0, 0.35),
    # the groove between upper and lower pods (rows 27-28): a dip in height; the plan stays full (the sprite
    # fills cols 13-35 on both rows, ink at cols 12 / 36), so the seam has no gap
    (27.15, 11.5, 11.5, 3.6, 6.7, 1.0, 9.5, 9.5, 2.0, 0.35),
    (27.55, 11.5, 11.5, 3.0, 6.7, 1.0, 8.5, 8.5, 2.0, 0.35),
    (28.7, 11.5, 11.5, 3.0, 6.7, 1.0, 8.5, 8.5, 2.0, 0.35),
    (29.05, 11.5, 11.5, 4.4, 6.7, 1.0, 8.5, 8.5, 2.0, 0.35),
    (29.5, 11.5, 11.5, 4.9, 6.7, 1.0, 8.5, 8.5, 2.0, 0.35),
    (30.9, 11.5, 11.5, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    # lower body: the core column, the glowing channels, the lower pods (cols 12-15 / 33-36)
    (31.15, 12.5, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    (32.4, 12.5, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    # groove across the core in front of the housing (rows 32-33)
    (32.7, 12.5, 11.6, 5.0, 6.0, 1.0, 8.5, 8.5, 1.8, 0.0),
    (33.7, 12.5, 11.6, 5.0, 6.0, 1.0, 8.5, 8.5, 1.8, 0.0),
    (34.0, 12.5, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.0),
    (47.6, 12.5, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.0),
    (48.05, 11.6, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    (50.8, 11.6, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    # groove across the pods (row 51)
    (51.05, 11.4, 11.4, 4.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    (51.75, 11.4, 11.4, 4.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    (52.0, 11.6, 11.6, 5.0, 6.7, 1.0, 8.5, 8.5, 1.8, 0.35),
    # rear end: the face over newshl-77's neck (the seam at row 56)
    (55.4, 11.6, 11.6, 4.9, 6.6, 1.0, 8.5, 8.5, 1.8, 0.35),
    (55.8, 11.2, 11.2, 4.4, 6.0, 1.0, 8.5, 8.5, 1.8, 0.35),
    (56.0, 10.8, 10.8, 4.0, 5.6, 1.0, 8.5, 8.5, 1.8, 0.35),
]

N_EXP = 2.4         # outer superellipse exponent (rounded box section)
BOTTOM = 0.92       # underside half height as a share of h (plain closed shape)


def station_fn():
    rs = [s[0] for s in ST]
    fns = {}
    for i, k in enumerate(K):
        ys = [s[i + 1] for s in ST]
        fns[k] = Pchip(rs, ys)
    return lambda r: {k: f(r) for k, f in fns.items()}


def densify(step=0.5):
    rs = [s[0] for s in ST]
    out = []
    for i, (a, b) in enumerate(zip(rs, rs[1:])):
        n = max(1, int(math.ceil((b - a) / step - 1e-6)))
        if ST[i][1:] == ST[i + 1][1:]:
            n = max(1, int(math.ceil((b - a) / 4.0)))  # a straight run: few rings
        out += [a + (b - a) * k / n for k in range(n)]
    out.append(rs[-1])
    return out


def outer_z(dx, w, h):
    u = min(abs(dx) / w, 1.0)
    return h * (1 - u ** N_EXP) ** (1 / N_EXP)


def core_z(dx, core):
    u = abs(dx) / CORE_W
    if u >= 1 or core <= 0:
        return -1e9
    return core * (1 - u ** 2.2) ** (1 / 2.2)


def top_z(dx, s):
    """The section's top at dx (px from the axis) for station values s."""
    w = s["wl"] if dx < 0 else s["wr"]
    pin = min(s["pil"] if dx < 0 else s["pir"], w - 1.0)
    z = outer_z(dx, w, s["h"])
    a = abs(dx)
    t = s["tr"]
    if t > 0 and 3.0 < a < pin:
        # channel: sunk to the floor between the core and the pod wall (0.3 px chamfer at the wall top)
        m = 1.0 if a < pin - 0.3 else (pin - a) / 0.3
        if a < 3.4:
            m *= (a - 3.0) / 0.4
        z = z + (s["floor"] - z) * t * m
    z = max(z, core_z(dx, s["core"]))
    if a < 0.8 and s["spine"] > 0:
        crest = max(core_z(0.0, s["core"]), outer_z(0.0, w, s["h"]))
        z = max(z, crest + s["spine"] * min(1.0, (0.8 - a) / 0.3))
    return z


def section_dxs(s):
    """Fixed-count dx samples, left edge to right edge, dense where the profile turns."""
    def side(sign, w, pin):
        pts = []
        pin = min(pin, w - 1.0)
        # outer roundel: edge to the pod's inner wall top (quadratic spacing, dense at the edge)
        L = w - (pin + 0.3)
        for k in range(8):
            pts.append(sign * (w - L * (k / 8) ** 1.6))
        pts += [sign * (pin + 0.3), sign * (pin + 0.05), sign * (pin - 0.05), sign * (pin - 0.3)]
        # channel floor to the core flank
        for k in range(1, 5):
            pts.append(sign * ((pin - 0.3) + (CORE_W + 0.15 - (pin - 0.3)) * k / 5))
        pts += [sign * (CORE_W + 0.15), sign * 4.35, sign * 4.1, sign * 3.7, sign * 3.2, sign * 2.6, sign * 2.0,
                sign * 1.4, sign * 1.0, sign * 0.8, sign * 0.5]
        return pts
    left = side(-1, s["wl"], s["pil"])
    right = side(1, s["wr"], s["pir"])
    return left + [0.0] + list(reversed(right))


def ring_points(r, s):
    dxs = section_dxs(s)
    top = [(AX + dx, r, top_z(dx, s)) for dx in dxs]
    # underside: plain superellipse back from right to left (same dx samples, skipping the two edge points)
    bot = []
    for dx in reversed(dxs[1:-1]):
        w = s["wl"] if dx < 0 else s["wr"]
        bot.append((AX + dx, r, -outer_z(dx, w, s["h"] * BOTTOM) - 0.0))
    return top, bot


def region_of(r):
    if r < 14.6:
        return "cap"
    if r < 17.6:
        return "neck"
    if r < 19.7:
        return "lip"
    return "body"


def build(coll, sprite):
    M = Mats(sprite)
    mat = {
        "cap": M(6, **STEEL), "neck": M(4, **STEEL), "lip": M(5, **STEEL), "core": M(6, **BODY),
        # pods and channel floors a less mirror-like satin (as newshl-77's floor / shadow slots), so the dark
        # greys don't go charcoal under the game's environment light
        "pod": M(4, **BODY), "floor": M(3, metallic=0.3, roughness=0.6), "under": M(4, **STEEL),
    }
    pipe = M(6, **STEEL)
    tube = M(115, emit=1.0, **GLOW)
    hot = M(118, emit=1.0, **GLOW)
    band = M(112, metallic=0.8, roughness=0.45)
    rim = M(7, **STEEL)
    dish = M(3, metallic=0.85, roughness=0.3)
    vent = M(3, metallic=0.4, roughness=0.6)
    slat = M(6, **STEEL)
    nose = M(2, metallic=0.7, roughness=0.5)
    gap = M(2, metallic=0.6, roughness=0.6)
    endcap = M(5, **STEEL)

    sf = station_fn()
    bm = bmesh.new()
    rings, info = [], []
    for r in densify(0.6):
        s = sf(r)
        top, bot = ring_points(r, s)
        rings.append(verts(bm, [P(*p) for p in top + bot]))
        info.append((r, s, len(top)))

    def hull_mat(i, k):
        r0, s, ntop = info[i]
        r1 = info[i + 1][0]
        reg = region_of(0.5 * (r0 + r1))
        if k >= ntop - 1:
            return mat["under"] if reg == "body" else mat[reg]
        if reg != "body":
            return mat[reg]
        dxs = section_dxs(s)
        dx = 0.5 * (dxs[k] + dxs[k + 1])
        a = abs(dx)
        pin = s["pil"] if dx < 0 else s["pir"]
        if a >= pin - 0.05:
            return mat["pod"]
        if a > CORE_W + 0.1:
            return mat["floor"]
        z = top_z(dx, s)
        return mat["core"] if z > s["floor"] + 0.6 else mat["floor"]

    loft(bm, rings, hull_mat, smooth=True, cap_mat=endcap)
    nmat = len(M.list) + 12

    # Intake grilles in the cap's front half (cols 19-23 / 25-29, rows 5-9): pockets open to the blunt nose,
    # floor sloping up from 1.6 px at the nose to 5.0 px at row 10.
    def grille_cut(cb):
        for c0, c1 in ((19.15, 23.85), (25.15, 29.85)):
            pts = []
            for c in (c0, c1):
                for r, zf in ((4.0, 1.6), (10.0, 5.0)):
                    pts += [(c, r, zf), (c, r, 9.0)]
            # box with a sloped floor: 8 corners
            lo = verts(cb, [P(c0, 4.0, 1.6), P(c1, 4.0, 1.6), P(c1, 10.0, 5.0), P(c0, 10.0, 5.0)])
            hi = verts(cb, [P(c0, 4.0, 9.0), P(c1, 4.0, 9.0), P(c1, 10.0, 9.0), P(c0, 10.0, 9.0)])
            loft(cb, [lo, hi], 0, smooth=False)
    cut_into(bm, grille_cut, vent, nmat)

    # The see-through gaps of the sprite (outline rule), cut through the hull, and the ink pixels beside them
    # (ink 4-adjacent to a see-through pixel is the border, so it stays under half covered). Mostly the right
    # side; on the left only the drain hole at (45, 19) beside the housing's rear corner.
    T = -20.0, 20.0
    for bx in ([
        (29.0, 30.7, 22.0, 36.95, *T),    # cols 29-30, rows 22-36: between the core and the right tube (col 30 ink)
        (29.0, 30.3, 36.95, 37.9, *T),    # row 37: col 29 (col 30 is lit tube, inner)
        (29.0, 30.0, 37.9, 38.95, *T),    # col 29 only, row 38: rows 38-41 are a bridge from the core to the tube
        (29.0, 30.0, 40.95, 42.1, *T),    # col 29 only, row 41
        (29.0, 30.7, 42.1, 46.95, *T),    # cols 29-30, rows 42-46
        (29.0, 30.3, 46.95, 48.0, *T),    # row 47: col 29 (col 30 is the lit hot band)
        (29.0, 30.7, 48.0, 56.5, *T),     # cols 29-30, rows 48-55
        (28.0, 29.05, 21.95, 24.0, *T),   # col 28, rows 22-23: the core's ink edge beside the gap's top
        (28.0, 29.05, 29.95, 34.0, *T),   # col 28, rows 30-33: the core's ink edge before the housing
        (27.35, 29.05, 44.95, 46.0, *T),  # row 45, cols 27-28: the hole behind the housing's right rear corner
        (28.0, 29.05, 45.9, 48.0, *T),    # col 28, rows 46-47 (ink beside it)
        (33.0, 34.65, 50.95, 52.0, *T),   # cols 33-34, row 51: the pod's inner notch and its ink
        (33.0, 33.6, 52.95, 54.0, *T),    # col 33, row 53 (ink)
        (33.0, 34.65, 53.95, 56.5, *T),   # cols 33-34, rows 54-55
        (31.0, 32.0, 21.9, 25.0, *T),     # col 31, rows 22-24: beside the tube's top
        (30.0, 34.65, 18.9, 20.0, *T),    # row 19, cols 30-34: in front of the feed pipe (cols 30 / 34 ink)
        (31.0, 32.0, 19.9, 21.0, *T),     # col 31, row 20 (ink)
        (29.0, 32.0, 20.95, 22.05, *T),   # row 21, cols 29-31 (ink): the gap's top
        (34.0, 35.0, 19.9, 24.1, *T),     # col 34, rows 20-23: between the pipe and the upper pod
        (31.5, 35.0, 24.0, 25.0, *T),     # row 24, cols 31-34: behind the pipe's end
        (33.0, 34.65, 24.9, 29.0, *T),    # cols 33-34, rows 25-28: between the tube and the pod (col 34 ink); the
                                          # pod's outer strip (cols 35-36) runs on unbroken over the groove
        (29.0, 31.0, 3.0, 5.6, *T),       # row 5, cols 29-30 (ink): the notch at the right grille's mouth
        (18.4, 20.6, 44.95, 46.0, *T),    # left drain hole (45, 19) and its ink (45, 18) / (45, 20)
        (19.0, 20.0, 45.9, 46.6, *T),     # ... and (46, 19)
    ]):
        cut_into(bm, box_prisms([bx]), gap, nmat)  # one box per cut: overlapping cutters upset the solver
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)

    # Louvre slats across each grille (rows 6 and 8), under the cap's surface so the pockets read dark.
    for c0, c1 in ((19.15, 23.85), (25.15, 29.85)):
        for r0, r1, zt in ((5.95, 6.95, 4.0), (7.95, 8.95, 5.3)):
            chbox(bm, c0 - 0.05, c1 + 0.05, r0, r1, zt - 0.9, zt, 0.15, slat)
    # Nose stub (row 4, cols 22-24, ink): a small dark button on the cap's blunt front, mostly behind row 4.
    ellipsoid(bm, P(23.5, 5.2, 0.7), (1.4 * PX, 0.55 * PX, 1.0 * PX), nose, segments=12, rings=6)

    # Feed pipes (cols 15-16 / 32-33, rows 20-23): grey pipes out of the lip's back, curving down into the
    # channel floor at the top of the glowing tube.
    for c in (AX - 8.5, AX + 8.5):
        tube_y(bm, c, 3.0, [(19.95, 1.0), (22.6, 1.0), (23.4, 0.92), (23.9, 0.7), (24.05, 0.35)], lambda i: pipe,
               sides=14, cap1=True)
        # flange collar where it leaves the lip
        tube_y(bm, c, 3.0, [(20.0, 1.25), (20.5, 1.25)], lambda i: rim, sides=14)

    # Glowing tubes (cols 16-18 / 30-32, rows 23-55): half sunk in the channel floor so they read as glowing
    # slots, not pipes standing proud; 2.4 px wide on the sprite's columns (the right one clear of the ink at
    # col 30, the left one of the ink at (45, 18)); hot bands below the clamps at rows 37 / 47; flush dark clamp
    # bands at rows 32-33, 36, 42, 46.
    TZ, TR, HR, BR = 2.2, 1.2, 1.32, 1.27
    def tube_mat(i, st):
        r = 0.5 * (st[i][0] + st[i + 1][0])
        return hot if (37.0 < r < 38.0 or 47.0 < r < 48.0 or 25.6 < r < 26.4) else tube
    for c in (17.2, 31.85):
        st = [(24.45, 0.05), (24.55, 0.5), (24.85, 0.88), (25.25, 1.1), (25.6, TR), (36.95, TR), (37.0, HR),
              (38.0, HR), (38.05, TR), (46.95, TR), (47.0, HR), (48.0, HR), (48.05, TR), (56.0, TR)]
        tube_y(bm, c, TZ, st, lambda i, st=st: tube_mat(i, st), sides=16)
        for r0, r1 in ((32.1, 33.9), (36.1, 36.9), (42.1, 42.9), (46.1, 46.9)):
            tube_y(bm, c, TZ, [(r0, BR), (r1, BR)], lambda i: band, sides=16)

    # The housing on the core (rows 33.8-45, cols 20-28): a raised rounded-square boss, a lit rim and a dark
    # dish (the sprite's "dark disc"); a short rear lip (rows 46-47).
    def rrect(c0, r0, c1, r1, rad, seg=5):
        pts = []
        for cc, rr, a0 in ((c1 - rad, r0 + rad, -90), (c1 - rad, r1 - rad, 0), (c0 + rad, r1 - rad, 90),
                           (c0 + rad, r0 + rad, 180)):
            for k in range(seg + 1):
                a = math.radians(a0 + 90 * k / seg)
                pts.append((cc + rad * math.cos(a), rr + rad * math.sin(a)))
        return pts
    base_z = 1.9
    outer = rrect(20.15, 33.8, 28.85, 45.0, 1.6)
    upper = rrect(20.45, 34.1, 28.55, 44.7, 1.35)
    zr = 7.7  # the dish floor (zr - 0.8) stays over the core's crest (6.7)
    hb = bmesh.new()
    rows_ = [verts(hb, [P(c, r, base_z) for c, r in outer]),
             verts(hb, [P(c, r, zr - 0.3) for c, r in outer]),
             verts(hb, [P(c, r, zr) for c, r in upper])]
    loft(hb, rows_, lambda i, k: rim, smooth=False, cap0=True, cap1=True, cap_mat=rim)
    # the dark disc: a round recessed dish, 7.2 px across (rows 35-44, cols 21-27), sloped walls and a
    # shallow bowl floor, in the square-cornered housing
    DC, DR = (AX, 39.4), 3.6
    def dish_cut(cb):
        prof = [(DR + 0.3, zr + 1.0), (DR, zr), (DR - 0.35, zr - 0.3), (DR - 1.0, zr - 0.6), (DR - 2.2, zr - 0.75),
                (0.6, zr - 0.8)]
        rings = [verts(cb, [P(DC[0] + rr * math.cos(2 * math.pi * k / 32), DC[1] + rr * math.sin(2 * math.pi * k / 32),
                              zz) for k in range(32)]) for rr, zz in prof]
        loft(cb, list(reversed(rings)), 0, smooth=True)
    cut_into(hb, dish_cut, dish, len(M.list) + 12)
    merge(bm, hb)
    # rear lip of the housing (rows 46-47)
    chbox(bm, 20.6, 28.4, 45.9, 47.7, 2.0, 6.95, 0.3, rim)

    me = bpy.data.meshes.new(NAME)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in M.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj, M


# --------------------------------------------------------------------------------------------------
# Review renders (only with --review <dir>)
# --------------------------------------------------------------------------------------------------

def review(pieces, shells, out, extra=()):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.world.color = (0.035, 0.04, 0.05)
    scene.render.resolution_percentage = 100
    for s in shells:
        s.hide_render = True
    for e in extra:
        e.hide_render = True
    k = 8

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        direction = Vector(look) - Vector(loc)
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    def shot(path, flat=False, transparent=False, cavity=True):
        sh.light = "FLAT" if flat else "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = cavity and not flat
        sh.cavity_type = "BOTH"
        sh.show_object_outline = False
        sh.show_specular_highlight = not flat
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=H / 12, rx=W * k, ry=H * k)
    c.rotation_euler = (0, 0, 0)
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_flat.png", flat=True)
    shot(out / "top_lit.png")
    # per piece top masks (24 x 28 grid each) for the rule IoU
    for p in pieces:
        loc = p.location
        others = [q for q in pieces if q is not p]
        for q in others:
            q.hide_render = True
        cp = cam(f"top_{p.name}", (loc.x, loc.y, 20), (loc.x, loc.y, 0), ortho=28 / 12, rx=24 * k, ry=28 * k)
        cp.rotation_euler = (0, 0, 0)
        shot(out / f"mask_{p.name}.png", flat=True, transparent=True)
        for q in others:
            q.hide_render = False
    cy = 0.0
    ext = 4.9
    views = {
        "south": ((0, -40, 0.0), (0, cy, 0.0)),
        "north": ((0, 40, 0.0), (0, cy, 0.0)),
        "east": ((40, cy, 0.0), (0, cy, 0.0)),
        "west": ((-40, cy, 0.0), (0, cy, 0.0)),
    }
    for nm, (loc, look) in views.items():
        cam(nm, loc, look, ortho=ext, rx=900, ry=420)
        shot(out / f"{nm}.png")
    d = 13
    for nm, el, az in (("q_high", 35, 30), ("q_rear", 30, 215), ("q_low", 12, 150), ("q_front", 30, 160)):
        e, a = math.radians(el), math.radians(az)
        cam(nm, (d * math.cos(e) * math.sin(a), cy - d * math.cos(e) * math.cos(a), d * math.sin(e)), (0, cy, 0),
            lens=60, rx=800, ry=600)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam("game", (0, cy - d * math.sin(t), d * math.cos(t)), (0, cy, 0), lens=55, rx=700, ry=800)
    shot(out / "game.png")
    cam("under", (0, 0, -20), (0, 0, 0), ortho=H / 12, rx=W * 6, ry=H * 6)
    shot(out / "under.png")
    for s in shells:
        s.hide_render = False
    cam("game_ink", (0, cy - d * math.sin(t), d * math.cos(t)), (0, cy, 0), lens=55, rx=700, ry=800)
    shot(out / "game_shell.png")
    if extra:
        for e in extra:
            e.hide_render = False
        for s in shells:
            s.hide_render = True
        cyw = -0.6
        cam("whole_game", (0, cyw - 16 * math.sin(t), 16 * math.cos(t)), (0, cyw, 0), lens=55, rx=700, ry=900)
        shot(out / "whole_game.png")
        cam("whole_q", (11 * math.sin(math.radians(35)), cyw - 11 * math.cos(math.radians(35)), 8), (0, cyw, 0),
            lens=45, rx=800, ry=800)
        shot(out / "whole_q.png")
        cam("whole_east", (40, cyw, 0), (0, cyw, 0), ortho=7.6, rx=900, ry=360)
        shot(out / "whole_east.png")


def sink_shell(shell, model, margin, reach):
    """newshk-281.py's sink_shell (copied via assembly-newshl-77): drop every outline-shell vertex to `margin`
    under the lowest top surface within `reach` (seen from above), so the ink stays on the silhouette."""
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
        for kk in range(12):
            a = 2 * math.pi * kk / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                hh = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if hh[0] is not None:
                    zt = min(zt, hh[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprites = {n: load_sprite(n) for n in PIECES}
    merged = dict(sprites[PIECES[0]])
    merged["colors"] = {}
    for s in sprites.values():
        merged["colors"].update(s["colors"])
    merged["name"] = NAME
    coll = common.reset_collection(NAME)
    obj, M = build(coll, merged)
    layout = LAYOUT
    pieces = common.split_assembly(obj, layout)
    bpy.data.objects.remove(obj, do_unlink=True)
    shells, shells_by, out_objs = [], {}, []
    total = 0
    for name, cx, cy in layout:
        p = pieces[name]
        for poly in p.data.polygons:
            poly.use_smooth = True
        p.data.set_sharp_from_angle(angle=math.radians(35))
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: {len(p.data.polygons)} faces, {tris} tris")
        src = bpy.data.objects.new(f"{name}_sealed", p.data.copy())
        coll.objects.link(src)
        bpy.context.view_layer.update()
        shl = common.outline_shell(src, coll, voxel=0.012, faces=2500, inside=0.004, islands="outer")
        sink_shell(shl, src, 0.5 * PX, 1.2 * PX)
        bpy.data.objects.remove(src, do_unlink=True)
        shl.name = shl.data.name = f"{name}_outline"
        assert len(shl.data.polygons) > 0, f"empty outline shell for {name}"
        shells.append(shl)
        shells_by[name] = shl
        out_objs += [p, shl]
    print(f"total tris {total}")
    for name in PIECES:
        common.export_sprite_model(ROOT, [pieces[name], shells_by[name]], f"enemies/{name}", sprites[name]["sprites"])
    # Export at the origin: the piece centre is the node origin (common.split_assembly); the game adds the
    # assembly offset itself. Only review renders lay the pieces out.
    if "--review" in argv:
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
            shells_by[name].location = pieces[name].location
    extra = []
    if "--with77" in argv:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=argv[argv.index("--with77") + 1])
        for o in set(bpy.data.objects) - before:
            if o.parent is None:
                o.location.y -= 42 / 12
            if "outline" in o.name:
                o.hide_render = True
            elif o.type == "MESH":
                extra.append(o)
    if "--review" in argv:
        review([pieces[n] for n in PIECES], shells, Path(argv[argv.index("--review") + 1]), extra)


if __name__ == "__main__":
    main()
