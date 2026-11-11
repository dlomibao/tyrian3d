"""newshd-267: the pink power housing with the glowing slit (newshd.shp 267-273, 24 x 28 px,
a full tile with its stone floor). A FIXED GROUND STRUCTURE: spawned only by ground-layer events
with no movement, carried with the asteroid's terrain, a 20-step glow cycle. It stands on the
ground: the floor plate (painted per pixel from the sprite's stone) is built for the review only and
not exported (D129), since the game draws the tile's ground in HD and the plate showed as grey pixel
cells on it. Underside: the housing and its flange are closed solids.

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"):
- Stone floor (greys) fills the tile round the machine.
- The housing (pink metal, 71): a rounded oblong, cols 3-17 x rows 0-25 (rows 0 / 25 one px
  narrower, the rounded ends), its top end on the tile's top edge. Rows 0-1 lit and rows 23-25
  dark are the light on its rounded ends (lighting, not paint). Side armour plates (71) widen it to
  cols 2-18 over rows 3-20.
- Side clamps (rows 6-17): an outer rail (cols 0 / 20, 72) standing off each plate across a dark
  groove (cols 1 / 19, 66), two brass bolt heads (23) in the groove at rows 7 and 16.
- Vents (cols 3-5 / 15-17, rows 7-16): dark pockets with grey louvres (median 3) between the
  plate and the inner frame.
- Inner frame (72): a raised rectangular rim, cols 6-14 x rows 2-21, bevelled into the slit (rows
  3-4 / 19-20 dark: the inner slopes). Its side bars step down over rows 9-14 (68: lower, shaded):
  a raised boss above and below, a lower jaw between.
- The slit (cols 8-12, rows 5-18, 112): a deep glow chamber. In it, slightly left of centre
  (col 9, widening into col 10 over rows 10-15), the core: a spindle along the slit with a
  filament ridge down its lit side. 267: cold pink metal (68 / 71); 269 dull red (116 / 118),
  271 orange (120 / 122), 273 white-hot (123 / 126). The chamber lining glows with it on 271 / 273
  (113-118), so it is a frame-animated palette material on the static model; the core is two
  parts (cold metal on 267, emissive on 269-273, frame_part).

Material language as the D121 fortress flagship (assembly-newshd-245): painted metal 0.45 / 0.42,
steel 0.75 / 0.32, stone floor 0.05 / 0.85. No texture bake (no textures/newshd-267/ folder; the
siblings are plain). Outline shell (D51) from a closed proxy of the machine.

Units while building: sprite px, x = column edge, y = row edge (down the screen), z up from the
floor plate's foot; finish() maps X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshd-267.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshd-267"
PX = 1 / 12
FL = 0.36      # floor top (lib_b073 FLOOR = 0.03 units)
CX = 10.5      # housing centre line (column edge)
COLD, HOT = [267], [269, 271, 273]


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, frames=None, metallic=0.45, roughness=0.42, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"nshd267_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


def finish(part, mats, coll, smooth=True):
    """usp_talon.finish for the 24 x 28 tile: X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    if smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def apply_mods(obj):
    """Bake the modifier stack into the mesh (no operators, no context)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    obj.modifiers.clear()
    old = obj.data
    obj.data = me
    bpy.data.meshes.remove(old)


def cut(obj, cutter):
    """Boolean difference (exact), the cut faces taking the cutter's materials."""
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.material_mode = "TRANSFER"
    apply_mods(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()


def join(objs, name):
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in objs[0].data.materials:
        me.materials.append(mat)
    out = bpy.data.objects.new(name, me)
    objs[0].users_collection[0].objects.link(out)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return out


# --- generic shapes -----------------------------------------------------------------------------
def box(P, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def rrect(x0, x1, y0, y1, r, nc=5):
    """Rounded rectangle (plan), counter-clockwise in (x, y), 4 * nc points."""
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, 0.5 * math.pi), (x0 + r, y0 + r, math.pi),
                       (x1 - r, y0 + r, 1.5 * math.pi)):
        for k in range(nc):
            a = a0 + 0.5 * math.pi * k / (nc - 1)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(P, outline, z0, z1, mat, ch=0.2):
    """Flat-topped slab over a convex plan outline, its top edge chamfered (hull)."""
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    inner = []
    for x, y in outline:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        inner.append((x - dx / d * ch, y - dy / d * ch))
    pts = [(x, y, z0) for x, y in outline] + [(x, y, z1 - ch) for x, y in outline] + [(x, y, z1) for x, y in inner]
    T.hull(P, pts, mat)


def revolve(P, a, u, stations, mat, n=16, cap0=True, cap1=True):
    """Surface of revolution about axis u through a: stations [(t, r)]."""
    a, u = Vector(a), Vector(u).normalized()
    ref = Vector((0, 0, 1)) if abs(u.z) < 0.9 else Vector((1, 0, 0))
    e1 = ref.cross(u).normalized()
    e2 = u.cross(e1).normalized()
    angs = [2 * math.pi * (k + 0.5) / n for k in range(n)]
    rings = []
    for t, r in stations:
        c = a + u * t
        rings.append([P.v(tuple(c + e1 * (r * math.cos(q)) + e2 * (r * math.sin(q)))) if r > 1e-6 else None
                      for q in angs])
        if r <= 1e-6:
            tip = P.v(tuple(c))
            rings[-1] = [tip] * n
    for i in range(len(stations) - 1):
        (t0, r0), (t1, r1) = stations[i], stations[i + 1]
        dt, dr = t1 - t0, r1 - r0
        L = math.hypot(dt, dr) or 1.0
        nt, nr = -dr / L, dt / L
        for k in range(n):
            j = (k + 1) % n
            qm = (angs[k] + angs[j] + (2 * math.pi if j == 0 else 0)) / 2
            out = u * nt + (e1 * math.cos(qm) + e2 * math.sin(qm)) * nr
            vs = [rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]]
            uniq = []
            for v in vs:
                if v not in uniq:
                    uniq.append(v)
            P.f(uniq, mat, out=tuple(out))
    if cap0 and stations[0][1] > 1e-6:
        P.f(rings[0], mat, out=tuple(-u))
    if cap1 and stations[-1][1] > 1e-6:
        P.f(rings[-1], mat, out=tuple(u))


# --- the housing shell: a loft of superelliptic sections along y --------------------------------
HW = T.pchip([0.0, 0.3, 0.7, 1.2, 1.8, 2.6, 23.6, 24.4, 25.0, 25.4, 25.75, 26.0],
             [5.4, 6.2, 6.85, 7.25, 7.45, 7.5, 7.5, 7.45, 7.2, 6.8, 6.2, 5.4])
HH = T.pchip([0.0, 0.3, 0.8, 1.5, 2.5, 4.0, 22.0, 23.5, 24.5, 25.2, 25.7, 26.0],
             [1.7, 2.6, 3.3, 3.75, 4.0, 4.1, 4.1, 4.0, 3.75, 3.3, 2.6, 1.7])
HP, HQ = 2.8, 0.42
Z0 = 1.05     # top of the base flange (the shell starts there)


def shell_section(w, h, n=28):
    """(x, z) ring, x from the centre line: right foot, over the crown, left foot, flat bottom."""
    pts = []
    for k in range(n + 1):
        t = math.pi * k / n          # 0 = right, pi = left
        c = math.cos(t)
        x = w * math.copysign(abs(c) ** 0.85, c)
        r = min(1.0, abs(x) / w)
        z = Z0 + h * max(0.0, 1 - r ** HP) ** HQ
        pts.append((x, z))
    return pts


def housing_shell(P, mat, grow=0.0):
    ys = [0.0, 0.1, 0.3, 0.5, 0.7, 1.0, 1.4, 1.8, 2.3, 2.8] + T.frange(3.5, 22.5, 1.0) + \
         [23.2, 23.7, 24.2, 24.6, 25.0, 25.3, 25.55, 25.75, 25.9, 26.0]
    ys = sorted(set(round(y, 3) for y in ys))
    rings = []
    for y in ys:
        w = HW(y) + grow
        h = HH(y) - Z0 + FL + grow
        rings.append([P.v((CX + x, y, z)) for x, z in shell_section(w, h)])
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for i in range(n - 1):
            q = [a[i], a[i + 1], b[i + 1], b[i]]
            c = sum((v.co for v in q), Vector()) / 4
            P.f(q, mat, away=(CX, c.y, Z0 - 2.0))
        P.f([a[-1], a[0], b[0], b[-1]], mat, out=(0, 0, -1))
    P.f(rings[0], mat, out=(0, -1, 0))
    P.f(rings[-1], mat, out=(0, 1, 0))


def flange(P, mat, grow=0.0):
    """Base flange the housing stands on: its plan is the shell's foot, chamfered on top."""
    pts = []
    ys = [0.0, 0.3, 0.7, 1.2, 1.8, 2.6, 23.6, 24.4, 25.0, 25.4, 25.75, 26.0]
    for y in ys:
        pts.append((CX + HW(y) + grow, y))
    for y in reversed(ys):
        pts.append((CX - HW(y) - grow, y))
    slab(P, pts, FL - 0.02, Z0 + 0.05 + grow, mat, ch=0.3)


# --- details ------------------------------------------------------------------------------------
FRAME_TOP = 5.5      # frame bosses
JAW_TOP = 4.85       # the lowered middle of the frame's side bars
SLIT = (8.0, 13.0, 5.0, 19.0)
CH_FLOOR = 1.45      # chamber floor


def bar(P, x0, x1, y0, y1, z0, z1, mat, inner, ch=0.3, bev=0.75):
    """A frame bar: chamfered block whose edge on the `inner` side ('l', 'r', 't', 'b' = toward
    smaller x, larger x, smaller y, larger y) is bevelled deeper (the slope into the slit)."""
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            ex = bev if (inner == "l" and sx == 1) or (inner == "r" and sx == -1) else ch
            ey = bev if (inner == "t" and sy == 1) or (inner == "b" and sy == -1) else ch
            ez = bev * 0.8 if ex == bev or ey == bev else ch
            pts += [(x + sx * ex, y + sy * ey, z1), (x, y + sy * ch, z1 - ez), (x + sx * ch, y, z1 - ez),
                    (x + sx * ch, y + sy * ch, z0), (x, y, z0 + 0.01)]
    T.hull(P, pts, mat)


def frame_ring(P, M, grow=0.0):
    """The inner frame's solid: one rounded-rectangle slab (cols 6-14, rows 2-21), its top edge
    chamfered; the slit and the jaws are cut from it (frame_cutters)."""
    g = grow
    out = rrect(6.0 - g, 15.0 + g, 2.0 - g, 22.0 + g, 1.7, nc=6)
    slab(P, out, 3.4, FRAME_TOP + g, M["frame"], ch=0.45)


def frame_cutters(M, coll):
    """Bevelled slit opening through the frame and the lowered jaws of its side bars (rows 9-14)."""
    cs = []
    P = T.Part(f"{NAME}_framecut", smooth_angle=10)
    x0, x1, y0, y1 = SLIT
    b = 0.75
    pts = [(x, y, 2.0) for x in (x0, x1) for y in (y0, y1)]
    pts += [(x, y, FRAME_TOP - b) for x in (x0, x1) for y in (y0, y1)]
    pts += [(x, y, FRAME_TOP + 0.01) for x in (x0 - b, x1 + b) for y in (y0 - b, y1 + b)]
    pts += [(x, y, 9.0) for x in (x0 - b, x1 + b) for y in (y0 - b, y1 + b)]
    T.hull(P, pts, M["frame"])
    cs.append(finish(P, [], coll, smooth=False))
    for xa, xb in ((5.5, 8.6), (12.4, 15.5)):
        P = T.Part(f"{NAME}_jawcut{xa}", smooth_angle=10)
        pts = []
        for x in (xa, xb):
            pts += [(x, 9.0, JAW_TOP + 0.6), (x, 15.0, JAW_TOP + 0.6), (x, 9.5, JAW_TOP), (x, 14.5, JAW_TOP),
                    (x, 9.0, 9.0), (x, 15.0, 9.0)]
        T.hull(P, pts, M["jaw"])
        cs.append(finish(P, [], coll, smooth=False))
    return cs


def inner_frame(P, M, grow=0.0, detail=True):
    """Clamp pads on the lowered jaws, facing the slit."""
    if not detail:
        return
    for x0, x1 in ((7.15, 7.95), (13.05, 13.85)):
        box(P, x0, x1, 10.2, 13.8, JAW_TOP - 0.3, JAW_TOP + 0.22, M["jaw"], ch=0.12)


def chamber_cutter(M, coll):
    """The slit and its chamber: cut out of the housing (walls / floor keep these materials)."""
    P = T.Part(f"{NAME}_slitcut", smooth_angle=10)
    x0, x1, y0, y1 = SLIT
    v = [P.v((x, y, z)) for z in (CH_FLOOR, 12.0) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    c = (CX, (y0 + y1) / 2, 6.0)
    P.f([v[0], v[1], v[2], v[3]], M["floor"], out=(0, 0, -1))
    P.f([v[4], v[5], v[6], v[7]], M["wall"], out=(0, 0, 1))
    for i in range(4):
        j = (i + 1) % 4
        P.f([v[i], v[j], v[j + 4], v[i + 4]], M["wall"], away=c)
    return finish(P, [], coll, smooth=False)


def vent_cutter(M, coll, x0, x1):
    P = T.Part(f"{NAME}_ventcut{x0}", smooth_angle=10)
    box(P, x0, x1, 7.0, 17.0, 1.7, 12.0, M["pocket"], ch=0.01)
    return finish(P, [], coll, smooth=False)


def vents(P, M):
    """Louvres in the vent pockets: slats across the pocket, leaning toward the core."""
    for xa, xb in ((2.95, 6.05), (14.95, 18.05)):
        for k in range(6):
            yc = 7.85 + k * 1.66
            pts = []
            for x in (xa, xb):
                pts += [(x, yc - 0.55, 2.0), (x, yc + 0.15, 2.0), (x, yc - 0.2, 3.65), (x, yc + 0.5, 3.65)]
            T.hull(P, pts, M["louvre"])
        # a support rib down the middle of the louvre bank
        xm = (xa + xb) / 2
        box(P, xm - 0.18, xm + 0.18, 7.1, 16.9, 1.7, 2.6, M["pocket"], ch=0.05)


def side_plates(P, M, grow=0.0, detail=True):
    g = grow
    for x0, x1 in ((2.0 - g, 3.6), (17.4, 19.0 + g)):
        pts = [(x0, 3.0 - g + 0.6), (x0 + 0.6, 3.0 - g), (x1, 3.0 - g), (x1, 21.0 + g), (x0 + 0.6, 21.0 + g),
               (x0, 20.4 + g)]
        slab(P, pts, FL, 3.5 + g, M["plate"], ch=0.35)
    if not detail:
        return
    # panel seams across the plates (the vent pocket's ends)
    for x0, x1 in ((2.0, 3.6), (17.4, 19.0)):
        for y in (6.75, 17.25):
            box(P, x0 - 0.04, x1 + 0.04, y - 0.12, y + 0.12, 3.05, 3.5, M["seam"], ch=0.03)


def clamps(P, M, grow=0.0, detail=True):
    g = grow
    for rx0, rx1, gx0, gx1, bx in ((0.05 - g, 1.05, 1.0, 2.1, 1.5), (19.95, 20.95 + g, 18.9, 20.0, 19.5)):
        # outer rail (rows 6-17), its ends chamfered down
        pts = []
        for x in (rx0, rx1):
            pts += [(x, 6.0 - g, FL), (x, 18.0 + g, FL), (x, 6.7 - g, 2.55 + g), (x, 17.3 + g, 2.55 + g),
                    (x, 6.0 - g, 1.6), (x, 18.0 + g, 1.6)]
        T.hull(P, pts, M["rail"])
        # groove floor joining the rail to the plate
        box(P, gx0, gx1, 6.6 - g, 17.4 + g, FL, 1.25 + g, M["groove"], ch=0.1)
        if not detail:
            continue
        # brass bolts through the clamp (rows 7 and 16): hex-ish heads on the groove floor
        for by in (7.5, 16.5):
            revolve(P, (bx, by, 1.2), (0, 0, 1), [(0.0, 0.5), (0.35, 0.5), (0.5, 0.36), (0.5, 0.0)], M["bolt"], n=6,
                    cap0=False)
            revolve(P, (bx, by, 1.7), (0, 0, 1), [(-0.05, 0.22), (0.2, 0.22), (0.3, 0.0)], M["bolt"], n=8,
                    cap0=False)


def chamber_fittings(P, M):
    """Electrode posts holding the core at each end of the slit (dark, under the glow)."""
    for y0, y1 in ((5.05, 6.9), (17.9, 18.95)):
        box(P, 9.2, 10.7, y0, y1, CH_FLOOR - 0.05, 2.75, M["post"], ch=0.15)
    # floor ribs either side of the core (heat sinks), in the lining's colour
    for x in (8.45, 12.25):
        box(P, x - 0.25, x + 0.25, 6.0, 18.0, CH_FLOOR - 0.05, CH_FLOOR + 0.55, M["wall"], ch=0.08)


CORE_X, CORE_Z = 9.95, 2.95
CORE_R = [(6.75, 0.0), (6.9, 0.28), (7.4, 0.46), (8.6, 0.52), (9.5, 0.72), (10.3, 0.95), (12.5, 1.06),
          (15.6, 0.95), (16.4, 0.72), (17.2, 0.48), (17.9, 0.3), (18.05, 0.0)]


def core(P, body_mat, fil_mat):
    revolve(P, (CORE_X, 0.0, CORE_Z), (0, 1, 0), CORE_R, body_mat, n=16, cap0=False, cap1=False)
    # filament ridge on the lit (left, upper) side: col 9
    revolve(P, (9.45, 0.0, CORE_Z + 0.55), (0, 1, 0),
            [(7.3, 0.0), (7.45, 0.26), (8.0, 0.34), (16.6, 0.34), (17.25, 0.26), (17.4, 0.0)], fil_mat, n=10,
            cap0=False, cap1=False)


# --- floor and outline proxy ---------------------------------------------------------------------
def floor(pix, Mt):
    tones = ((1, 3), (4, 6), (7, 9), (10, 15))
    colors = Mt.sprite["colors"]
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        mid = (lo + hi) / 2
        slots.append(Mt(min(have, key=lambda i: abs(i - mid)), f"stone{lo}", metallic=0.05, roughness=0.85))

    def slot_of(i):
        for (lo, hi), s in zip(tones, slots):
            if lo <= i <= hi:
                return s
        return slots[1]

    P = T.Part(f"{NAME}_floor", smooth_angle=5)
    T.hull(P, [(x, y, z) for x in (0.0, 24.0) for y in (0.0, 28.0) for z in (0.0, FL - 0.01)], slot_of(4))
    for r in range(28):
        c = 0
        while c < 24:
            s = slot_of(pix[r][c])
            e = c + 1
            while e < 24 and slot_of(pix[r][e]) == s:
                e += 1
            vs = [P.v((xx, yy, FL)) for xx, yy in ((c, r), (e, r), (e, r + 1), (c, r + 1))]
            P.f(vs, s, out=(0, 0, 1))
            c = e
    return P


def build_proxy(M, coll):
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    g = 0.12
    housing_shell(P, M["body"], grow=g)
    flange(P, M["body"], grow=g)
    frame_ring(P, M, grow=g)
    side_plates(P, M, grow=g, detail=False)
    clamps(P, M, grow=g, detail=False)
    return finish(P, [], coll)


# --- build --------------------------------------------------------------------------------------
def build():
    sp = common.load_sprite(WT, NAME)
    sprite = {"name": NAME, "colors": sp["colors"]}
    pix = sp["frames"][0]["pixels"]
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    Mt = Mats(sprite)
    paint = dict(metallic=0.45, roughness=0.42)
    steel = dict(metallic=0.75, roughness=0.32)
    M = {
        "body": Mt(71, "body", **paint),
        "base": Mt(69, "base", **paint),
        "plate": Mt(71, "plate", **paint),
        "seam": Mt(66, "seam", **paint),
        "rail": Mt(72, "rail", **paint),
        "groove": Mt(66, "groove", **paint),
        "bolt": Mt(23, "bolt", metallic=0.7, roughness=0.35),
        "frame": Mt(72, "frame", **paint),
        "jaw": Mt(68, "jaw", **paint),
        "pocket": Mt(2, "pocket", metallic=0.6, roughness=0.5),
        "louvre": Mt(4, "louvre", **steel),
        "post": Mt(112, "post", metallic=0.6, roughness=0.45),
        # the chamber lining heats with the core (271 / 273); emissive so the glow lights it
        "floor": Mt(112, "chfloor", frames={271: 114, 273: 118}, metallic=0.2, roughness=0.5, emission=1.0),
        "wall": Mt(112, "chwall", frames={271: 113, 273: 116}, metallic=0.2, roughness=0.5, emission=1.0),
        "core_c": Mt(68, "core_cold", **steel),
        "fil_c": Mt(71, "fil_cold", **steel),
        "core_h": Mt(116, "core_hot", frames={271: 120, 273: 123}, metallic=0.0, roughness=0.3, emission=3.0),
        "fil_h": Mt(118, "fil_hot", frames={271: 122, 273: 126}, metallic=0.0, roughness=0.3, emission=4.0),
    }
    floor_part = floor(pix, Mt)   # all materials exist before any object is finished

    # housing shell, slit and vents cut out of it
    PS = T.Part(f"{NAME}_shell", smooth_angle=40)
    housing_shell(PS, M["body"])
    shell_obj = finish(PS, Mt.list, coll)
    for cutter in (chamber_cutter(M, coll), vent_cutter(M, coll, 2.6, 6.0), vent_cutter(M, coll, 15.0, 18.4)):
        for mat in Mt.list:
            cutter.data.materials.append(mat)
        cut(shell_obj, cutter)

    PF = T.Part(f"{NAME}_frame", smooth_angle=40)
    frame_ring(PF, M)
    frame_obj = finish(PF, Mt.list, coll)
    for cutter in frame_cutters(M, coll):
        for mat in Mt.list:
            cutter.data.materials.append(mat)
        cut(frame_obj, cutter)

    P = T.Part(f"{NAME}_parts", smooth_angle=34)
    flange(P, M["base"])
    inner_frame(P, M)
    side_plates(P, M)
    clamps(P, M)
    vents(P, M)
    chamber_fittings(P, M)
    parts_obj = finish(P, Mt.list, coll)
    obj = join([shell_obj, frame_obj, parts_obj], NAME)
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(36))

    cores = []
    for frames, bm_, fm in ((COLD, M["core_c"], M["fil_c"]), (HOT, M["core_h"], M["fil_h"])):
        CP = T.Part(f"{NAME}_core_{'cold' if frames == COLD else 'hot'}", smooth_angle=60)
        core(CP, bm_, fm)
        o = finish(CP, Mt.list, coll)
        common.frame_part(o, frames)
        cores.append(o)

    fl = finish(floor_part, Mt.list, coll)
    fl.data.shade_flat()
    fl["tyrian_ground"] = True
    proxy = build_proxy(M, coll)
    shell = common.outline_shell(proxy, coll, faces=3000)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    return obj, cores, fl, shell


if __name__ == "__main__":
    obj, cores, fl, shell = build()
    objs = [obj] + cores + [shell]  # not the floor plate (D129)
    sp = common.load_sprite(WT, NAME)
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sp["sprites"])
