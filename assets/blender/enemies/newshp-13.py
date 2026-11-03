"""Brown ground turret (newshp.shp frames 13-93 and newsh2.shp 39-131): a hard-surface small tank that
is its sprite in 3D (D50-D53).

Seen in episode 1 (levels 1, 1.3, 1.6) and 3. The sprite (24 x 28 px, eight aim directions) is
authoritative for the plan outline, the dome / lamp / muzzle positions and the palette indices
(region medians with the darkest shading and brightest sheen left out); the concept
(assets/blender/features/concepts/newshp-13.jpg) only guides the side, front and rear design.

What it is: a tracked hull on four track units, so the running gear runs the full length of each
side: a long rear belt under each armoured pod (toothed track round road wheels, a sprocket and an
idler) and a short front bogie inboard under each fender prong (the prongs are narrower than the
pods). Each pod has two raised lid plates with a panel gap, an access hatch with a hinge, louvres
and a seam groove in the outer wall and an exhaust port at the back; each prong is one armoured
piece, a fender over its bogie whose louvred glacis slopes down the front to a short nose.
Between the prongs a gun channel, behind the turret an engine deck with a grille and, in the rear
notch, the red lamp (116, glowing) in a dark housing. On it the turret: a dark bearing ring (16), a
cast bronze dome (22, a rounded square in plan, as the sprite's 5 x 4 px block) with raised seam
welts, a mantlet, the grey barrel (7) with a recoil sleeve, clamp and recuperator rod, and the
muzzle as the sprite draws it: a slim dark ported shroud (2) about 3 px wide, a closed collar at
the back and a crown ring with the bore at the tip, open on top between them, where the 1 px
bronze crown shows (24 in front, 22 behind). The underside is a closed tub, no detail.

The turret turns to aim in eight directions, each its own model with the frames that show it
(newsh2.shp repeats newshp.shp's eight directions):

    newshp-13 up-left, -f2 up, -f3 up-right, -f4 left, -f5 right, -f6 down-left, -f7 down,
    -f8 down-right.

Hull and turret are built once (sprite px, gun along +Y, the dome's centre on the origin), joined
into a base mesh (UV'd and baked once), then each direction copies it, moves / scales the hull under
the dome, warps its plan to that frame's outline, stretches the gun to the frame's length, turns the
lot to the aim angle and places the dome over the sprite's dome. The per-direction pivots, offsets,
scales, gun lengths, small aim and muzzle-size tweaks and plan warps were fitted to each frame's
mask (rendering the real mesh's top view in a closed loop) and stored in
assets/blender/textures/newshp-13/fit.json. The hull's outlines carry extra points along their long
edges so the warp can bend a wall, not only move its corners; the warped hull keeps the normals of
its unwarped self, so the sub-pixel nudges don't shade as blotches. The lamp is dark in the frames
that face it away.

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50).
Cycles bakes a colour multiplier (ambient occlusion, edge lift) and a roughness/metalness map to
assets/blender/textures/newshp-13/bake/; Base Color = map x palette colour, so pal_<index>, fades
and the hit flash still apply. The lamp and bores keep their flat palette colour. Each model carries
an outline shell (common.outline_shell, D51) as a child. No engines, so no engine glows.

Run: blender --background --factory-startup --python assets/blender/enemies/newshp-13.py
     [-- --preview out.png] [--no-bake]
(--preview previews every direction: <out>.png and newshp-13-f<n>.png beside it.)
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b067 as lib  # noqa: E402  (frame_image, subset)
import usp_talon as T  # noqa: E402  (cull_hidden, join)

ROOT = common.repo_root(__file__)
NAME = "newshp-13"
TAG = "newshp-13"
PX = 1 / 12
TEX = ROOT / "assets" / "blender" / "textures" / NAME

# (model, aim angle (deg from +X), dome centre in sprite pixel-edge coords (col, row), frames,
#  hull offset in px along the turret's (right, forward) axes, hull yaw (deg), lamp shift (px, +right),
#  lamp lit). Pivots / offsets / yaws fitted to each frame's mask and dome (fit_A.py); the lamp sits
# where each frame draws it, dark where the frame shows none (the rear faces away there).
DIRECTIONS = [
    (NAME, 135, (13.47, 12.54), {("newshp.shp", 13)}, (-1.2, -0.4), -12, 0.0, True),
    (f"{NAME}-f2", 90, (11.5, 13.0), {("newshp.shp", 15), ("newsh2.shp", 45)}, (0.0, 0.0), 0, 0.5, True),
    (f"{NAME}-f3", 45, (11.25, 13.75), {("newshp.shp", 17), ("newsh2.shp", 93)}, (1.0, 0.25), 0, 0.0, True),
    (f"{NAME}-f4", 180, (15.0, 12.0), {("newshp.shp", 51), ("newsh2.shp", 39)}, (0.0, 0.0), 0, 0.5, True),
    (f"{NAME}-f5", 0, (9.5, 11.5), {("newshp.shp", 55), ("newsh2.shp", 43)}, (0.5, 0.5), 0, 0.5, True),
    (f"{NAME}-f6", -135, (13.75, 11.5), {("newshp.shp", 89), ("newsh2.shp", 129)}, (-1.0, 1.5), 0, 0.0, False),
    (f"{NAME}-f7", -90, (11.5, 11.75), {("newshp.shp", 91), ("newsh2.shp", 41)}, (0.5, 1.5), 0, 0.0, False),
    (f"{NAME}-f8", -45, (10.5, 11.25), {("newshp.shp", 93), ("newsh2.shp", 131)}, (0.5, 2.25), 0, 0.0, False),
]
FIT = TEX / "fit.json"
# Per direction: hull scale (across, along) and gun extension (px), as each frame draws them (the
# diagonal and side frames draw the hull a little smaller and the gun longer than the up frame).
SHAPE = {m: ((1.0, 1.0), 0.0) for m, *_ in DIRECTIONS}
if FIT.exists():  # fitted values (fit_A.py) override the starting guesses above
    _fit = json.loads(FIT.read_text())
    DIRECTIONS = [(m, a, tuple(_fit[m]["pivot"]), fr, tuple(_fit[m]["hull"]), _fit[m]["yaw"], lx, lit)
                  if m in _fit else (m, a, p, fr, h, y, lx, lit)
                  for m, a, p, fr, h, y, lx, lit in DIRECTIONS]
    SHAPE.update({m: (tuple(v.get("scale", (1.0, 1.0))), v.get("gun", 0.0)) for m, v in _fit.items()})
WARP = {m: v.get("warp", []) for m, v in _fit.items()} if FIT.exists() else {}
LAMP = {m: tuple(v["lamp"]) for m, v in _fit.items() if "lamp" in v} if FIT.exists() else {}
# Per direction: a small turn of the turret about the dome (deg), where the frame draws the gun a
# little off its nominal angle.
AIM = {m: v.get("aim", 0.0) for m, v in _fit.items()} if FIT.exists() else {}
# Per direction: the muzzle shroud's (length, width) scale, as each frame draws its 3 px muzzle blob a
# little longer or shorter (the hull's per-direction scale, for the muzzle).
MUZ = {m: tuple(v.get("muzzle", (1.0, 1.0))) for m, v in _fit.items()} if FIT.exists() else {}


def warp(stages, c, r):
    """The per-direction plan warp of the hull (warp_A.py): Gaussian RBF stages in sprite px."""
    for st in stages:
        s2 = 2 * st["sigma"] ** 2
        dc = dr = 0.0
        for (cc, cr), (wc, wr) in zip(st["c"], st["w"]):
            k = math.exp(-((c - cc) ** 2 + (r - cr) ** 2) / s2)
            dc += k * wc
            dr += k * wr
        c, r = c + dc, r + dr
    return c, r


GUN_SPLIT = (2.9, 6.8)  # turret px: the barrel between these stretches, the neck and muzzle beyond move


# --- materials -------------------------------------------------------------------------------------
# Slot: (palette index, metallic, roughness, emission). Indices are the sprite's medians per region
# (pods 7 lit / 5 shaded -> 6, deck 4, barrel 7, dome 22, muzzle 24, ring 16, lamp 116).
SLOTS = {
    "armour": (6, 0.28, 0.5, 0),    # side pods, front fenders
    "dark": (4, 0.25, 0.55, 0),     # deck, tub, mantlet, hubs
    "mid": (5, 0.3, 0.5, 0),        # road wheels, recoil sleeve, clamps
    "track": (3, 0.2, 0.7, 0),      # track links
    "deep": (2, 0.1, 0.8, 0),       # recesses, gun channel, housing, neck
    "black": (1, 0.0, 0.9, 0),      # bores, exhaust ports
    "barrel": (7, 0.4, 0.4, 0),
    "ring": (16, 0.3, 0.55, 0),
    "dome": (22, 0.42, 0.38, 0),
    "muzzle": (24, 0.42, 0.4, 0),
    "lamp": (116, 0.0, 0.3, 3.0),
}
ORDER = list(SLOTS)
S = {k: i for i, k in enumerate(ORDER)}
BAKED = [k for k in ORDER if k not in ("lamp", "black")]


def make_materials(sprite):
    mats = []
    for k in ORDER:
        idx, met, rough, em = SLOTS[k]
        mats.append(common.palette_material(sprite, idx, f"{TAG}_{k}", metallic=met, roughness=rough,
                                            emission_strength=em))
    return mats


# --- geometry helpers (sprite px) ------------------------------------------------------------------

def inset(outline, d):
    """CCW outline with every edge moved d inward."""
    n = len(outline)
    if d == 0:
        return list(outline)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / ln, (x1 - x0) / ln
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def dense(outline, step=0.75):
    """The outline with points added along its long edges (every `step` px or less), so the
    per-direction plan warp can bend a flat wall smoothly instead of only moving its corners."""
    out = []
    n = len(outline)
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        k = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k) for j in range(k)]
    return out


def mirror(o):
    return [(-x, y) for x, y in reversed(o)]


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rrect(hw, hh, r, cx=0.0, cy=0.0, seg=4):
    pts = []
    for ax, ay, a0 in ((hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180), (hw - r, -hh + r, 270)):
        for k in range(seg):
            a = math.radians(a0 + 90 * k / (seg - 1))
            pts.append((cx + ax + r * math.cos(a), cy + ay + r * math.sin(a)))
    return pts


class Part:
    def __init__(self):
        self.bm = bmesh.new()

    def loft(self, rings, mat, cap0=True, cap1=True):
        bm = self.bm
        vs = [[bm.verts.new(p) for p in r] for r in rings]
        for a, b in zip(vs, vs[1:]):
            n = max(len(a), len(b))
            for i in range(n):
                j = (i + 1) % n
                if len(a) == 1:
                    f = bm.faces.new((a[0], b[j], b[i]))
                elif len(b) == 1:
                    f = bm.faces.new((a[i], a[j], b[0]))
                else:
                    f = bm.faces.new((a[i], a[j], b[j], b[i]))
                f.material_index = mat
        if cap0 and len(vs[0]) > 2:
            bm.faces.new(list(reversed(vs[0]))).material_index = mat
        if cap1 and len(vs[-1]) > 2:
            bm.faces.new(vs[-1]).material_index = mat
        return vs

    def stack(self, outline, stations, mat, lid=None, top=None):
        """Armour block: rings of `outline` inset by d at height z for each (d, z) station (z may be
        a function of (x, y), a sloped top). Capped both ends; the top cap takes `lid`."""
        rings = []
        for d, z in stations:
            o = inset(outline, d)
            rings.append([(x, y, z(x, y) if callable(z) else z) for x, y in o])
        n = len(self.bm.faces)
        vs = self.loft(rings, mat)
        if lid is not None:
            self.bm.faces.ensure_lookup_table()
            self.bm.faces[-1].material_index = lid
        return vs

    def tube(self, p0, p1, r0, r1=None, sides=12, mat=0, caps=True, phase=0.5, rings=None):
        """A round (or `sides`-gon) bar between two points; `rings` = [(t, r)] for a profile."""
        a, b = Vector(p0), Vector(p1)
        w = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(w.z) < 0.9 else Vector((1, 0, 0))
        u = w.cross(ref).normalized()
        v = w.cross(u).normalized()
        prof = rings or [(0.0, r0), (1.0, r0 if r1 is None else r1)]
        rr = []
        for t, r in prof:
            c = a.lerp(b, t)
            rr.append([tuple(c + r * (math.cos(2 * math.pi * (i + phase) / sides) * u
                                      + math.sin(2 * math.pi * (i + phase) / sides) * v)) for i in range(sides)])
        return self.loft(rr, mat, caps, caps)

    def obj(self, name, mats, coll):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


def cut(target, cutter_part, mats, coll):
    """Boolean difference: recesses take the cutter's material (its walls and floor)."""
    c = cutter_part.obj(target.name + "_cut", mats, coll)
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = c
    try:
        mod.material_mode = "TRANSFER"
    except Exception:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    old = target.data
    target.modifiers.remove(mod)
    target.data = me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(c, do_unlink=True)
    return target


def stadium_loop(y0, y1, z0, z1, step=0.5, tooth=0.0):
    """A track run's side profile (y, z), CCW seen from +X, sampled every `step` along its length;
    with `tooth` every other pair of points stands out (the grousers)."""
    r = (z1 - z0) / 2
    zc = z0 + r
    ya, yb = y0 + r, y1 - r
    segs = []  # parametric pieces: bottom straight (ya->yb), front arc, top straight (yb->ya), rear arc
    L1 = yb - ya
    L2 = math.pi * r
    total = 2 * L1 + 2 * L2
    n = max(8, int(round(total / step)))
    n += n % 4  # whole teeth
    pts = []
    for i in range(n):
        s = total * i / n
        if s < L1:
            p, nrm = (ya + s, z0), (0, -1)
        elif s < L1 + L2:
            a = -math.pi / 2 + (s - L1) / r
            p, nrm = (yb + r * math.cos(a), zc + r * math.sin(a)), (math.cos(a), math.sin(a))
        elif s < 2 * L1 + L2:
            p, nrm = (yb - (s - L1 - L2), z1), (0, 1)
        else:
            a = math.pi / 2 + (s - 2 * L1 - L2) / r
            p, nrm = (ya + r * math.cos(a), zc + r * math.sin(a)), (math.cos(a), math.sin(a))
        k = tooth if (i // 2) % 2 == 0 else 0.0
        pts.append((p[0] + nrm[0] * k, p[1] + nrm[1] * k))
    return pts


# --- dimensions (sprite px; blueprint coords: x right, y forward, origin = f2 pivot) ----------------
GUN_Z = 3.95
BARREL_R = 0.8  # the barrel's radius at the breech
MUZ_HW = 1.45  # the muzzle shroud's half width
MUZ_Y0, MUZ_LEN, MUZ_TAPER = 7.0, 3.95, 0.18  # its back, length and end chamfer
MUZ_COLLAR, MUZ_RING = 1.05, 0.85  # the closed rear collar and front crown ring
POD_STATIONS = [(0.35, 1.25), (0.0, 2.25), (0.0, 3.4), (0.5, 3.92)]
POD = [(1.55, -6.5), (4.5, -6.5), (6.5, -4.1), (6.5, 1.15), (5.4, 2.5), (2.6, 2.5), (2.6, -4.6), (1.55, -4.6)]
SEAM_Y = -1.6  # the transverse gap between the pod's front and rear armour


def prong_top(x, y):
    """The fender's top: flat over the bogie, then the glacis sloping down to the nose."""
    return 3.7 if y < 4.4 else max(1.75, 3.7 - (y - 4.4) * 0.62)


def prong_bottom(x, y):
    """The fender's underside: clear of the bogie's wheels, then down to the nose under the glacis."""
    return 2.35 if y < 5.6 else max(0.95, 2.35 - (y - 5.6) * 1.6)


def build_hull(mats, coll):
    parts = []
    # Lower tub: the closed belly (no underside detail).
    p = Part()
    p.stack(dense([(-4.3, -5.6), (4.3, -5.6), (4.3, 2.3), (2.55, 2.55), (2.55, 6.9), (-2.55, 6.9), (-2.55, 2.55),
                   (-4.3, 2.3)], 1.0),
            [(0.35, 0.45), (0.0, 0.85), (0.0, 2.1)], S["dark"])
    parts.append(p.obj("tub", mats, coll))

    for s in (1, -1):
        side = (lambda o: o) if s > 0 else mirror
        # Track: a toothed belt loop (outer grousers) round road wheels, sprocket and idler.
        p = Part()
        outer = stadium_loop(-5.6, 2.05, 0.0, 2.15, tooth=0.14)
        # inner loop resampled to the outer's count so the walls can loft
        m = len(outer)
        inner = stadium_loop(-5.25, 1.7, 0.35, 1.8, step=(2 * (6.95 - 1.45) + 2 * math.pi * 0.725) / m)
        while len(inner) != m:
            inner = inner[:m] if len(inner) > m else inner + [inner[-1]]
        xo, xi = s * 6.25, s * 4.15
        ring_o0 = [(xi, y, z) for y, z in outer]
        ring_o1 = [(xo, y, z) for y, z in outer]
        ring_i1 = [(xo, y, z) for y, z in inner]
        ring_i0 = [(xi, y, z) for y, z in inner]
        p.loft([ring_o0, ring_o1, ring_i1, ring_i0, ring_o0], S["track"], cap0=False, cap1=False)
        # Road wheels, a rear drive sprocket and a front idler inside the belt.
        for wy, r, zc in ((-4.55, 0.78, 1.08), (-3.05, 0.62, 0.82), (-1.75, 0.62, 0.82), (-0.45, 0.62, 0.82),
                          (0.95, 0.72, 1.05)):
            p.tube((s * 4.3, wy, zc), (s * 6.0, wy, zc), 0, sides=8, mat=S["mid"],
                   rings=[(0.0, r * 0.8), (0.1, r), (1.0, r)])
            p.tube((s * 5.95, wy, zc), (s * 6.12, wy, zc), r * 0.42, sides=6, mat=S["dark"])
        # Front bogie: a shorter belt under the fender, inboard (the fender is narrower than the pod),
        # so the running gear runs the full length of the hull side.
        outer = stadium_loop(2.6, 6.0, 0.0, 2.15, tooth=0.14)
        m = len(outer)
        inner = stadium_loop(2.95, 5.65, 0.35, 1.8, step=(2 * (2.7 - 1.45) + 2 * math.pi * 0.725) / m)
        while len(inner) != m:
            inner = inner[:m] if len(inner) > m else inner + [inner[-1]]
        xo, xi = s * 4.42, s * 2.65
        p.loft([[(xi, y, z) for y, z in outer], [(xo, y, z) for y, z in outer], [(xo, y, z) for y, z in inner],
                [(xi, y, z) for y, z in inner], [(xi, y, z) for y, z in outer]], S["track"], cap0=False, cap1=False)
        for wy, r, zc in ((3.55, 0.72, 1.05), (5.0, 0.7, 1.05)):
            p.tube((s * 2.8, wy, zc), (s * 4.25, wy, zc), 0, sides=8, mat=S["mid"],
                   rings=[(0.0, r * 0.8), (0.1, r), (1.0, r)])
            p.tube((s * 4.2, wy, zc), (s * 4.32, wy, zc), r * 0.42, sides=6, mat=S["dark"])
        parts.append(p.obj(f"track_{s}", mats, coll))

        # Pod armour: one chamfered block; on its lid two raised plates (front and rear) with a
        # panel gap between them; a seam groove down the outer wall below that gap, louvres low in
        # the outer wall, an exhaust port in the rear face.
        p = Part()
        p.stack(side(dense(POD)), POD_STATIONS, S["armour"])
        pod = p.obj(f"pod_{s}", mats, coll)
        c = Part()
        for k in range(3):
            y = -3.55 + k * 0.55
            c.stack(side(box(6.15, y, 7.2, y + 0.28)), [(0.0, 1.9), (0.0, 3.05)], S["deep"])
        c.stack(side(box(6.38, SEAM_Y - 0.06, 7.2, SEAM_Y + 0.06)), [(0.0, 1.0), (0.0, 3.55)], S["deep"])
        c.tube((s * 3.55, -7.2, 2.55), (s * 3.55, -5.95, 2.55), 0.42, sides=12, mat=S["black"])
        cut(pod, c, mats, coll)
        parts.append(pod)
        lid = inset(POD, 0.5)
        front = [(2.6 + 0.42, SEAM_Y + 0.1)] + [(min(x, 6.0 - 0.0), y) for x, y in
                                                [(6.0, SEAM_Y + 0.1), (6.0, 0.95), (5.2, 2.0), (3.02, 2.0)]]
        rear = [(2.0, -6.0), (4.25, -6.0), (6.0, -4.0), (6.0, SEAM_Y - 0.1), (3.02, SEAM_Y - 0.1),
                (3.02, -4.15), (2.0, -4.15)]
        for nm, o in (("f", front), ("r", rear)):
            p = Part()
            p.stack(side(inset(o, 0.12)), [(0.0, 3.85), (0.0, 4.02), (0.1, 4.12)], S["armour"])
            parts.append(p.obj(f"plate{nm}_{s}", mats, coll))
        # Access hatch on the rear plate with a hinge bar.
        p2 = Part()
        hx = s * 4.3
        p2.stack(rrect(0.72, 0.68, 0.25, hx, -3.55), [(0.0, 4.0), (0.0, 4.22), (0.08, 4.3)], S["armour"])
        p2.tube((hx - 0.5, -2.82, 4.2), (hx + 0.5, -2.82, 4.2), 0.11, sides=8, mat=S["mid"])
        parts.append(p2.obj(f"hatch_{s}", mats, coll))

        # Front fender prong: one armoured piece, a fender over the bogie whose sloped glacis runs
        # down the front to a short nose (the old separate bumper block), louvres cut across the
        # glacis' inner half.
        p = Part()
        pr = dense([(1.55, 2.3), (4.5, 2.3), (4.5, 4.4), (4.5, 6.1), (3.5, 7.5), (1.55, 7.5), (1.55, 6.1),
                    (1.55, 4.4)])
        vs = p.stack(side(pr), [(0.0, prong_bottom), (0.0, lambda x, y: prong_top(x, y) - 0.4),
                                (0.4, prong_top)], S["armour"])
        # split the top at the glacis' knee so the flat deck and the slope stay planar faces
        knee = [v for v in vs[-1] if abs(v.co.y - 4.4) < 1e-3]
        if len(knee) == 2:
            bmesh.ops.connect_verts(p.bm, verts=knee)
        prong = p.obj(f"prong_{s}", mats, coll)
        c = Part()
        for y in (2.95, 3.75, 4.55, 5.35):
            c.stack(side(box(1.95, y, 3.45, y + 0.34)), [(0.0, prong_top(0, y + 0.3) - 0.3), (0.0, 5.0)], S["deep"])
        cut(prong, c, mats, coll)
        parts.append(prong)

    # Gun cradle channel between the prongs.
    p = Part()
    p.stack(dense(box(-1.6, 2.2, 1.6, 7.45)), [(0.0, 0.8), (0.0, 1.9), (0.15, 2.05)], S["deep"])
    parts.append(p.obj("channel", mats, coll))
    # Engine deck, with a transverse grille behind the turret ring.
    p = Part()
    p.stack(dense(box(-2.65, -5.5, 2.65, 2.4)), [(0.0, 1.0), (0.0, 2.45), (0.3, 2.75)], S["dark"])
    deck = p.obj("deck", mats, coll)
    c = Part()
    for y in (-2.95, -2.45):
        c.stack(box(-2.1, y, 2.1, y + 0.26), [(0.0, 2.45), (0.0, 3.5)], S["deep"])
    cut(deck, c, mats, coll)
    parts.append(deck)
    # Lamp housing in the rear notch and the red lamp (a separate island: moved per direction).
    p = Part()
    p.stack(dense(box(-1.45, -5.45, 1.45, -3.1)), [(0.0, 1.2), (0.0, 2.75), (0.25, 3.0)], S["dark"])
    parts.append(p.obj("housing", mats, coll))
    p = Part()
    p.stack(box(-1.0, -4.5, 1.0, -3.5), [(0.0, 2.8), (0.0, 3.1), (0.12, 3.22)], S["lamp"])
    parts.append(p.obj("lamp", mats, coll))
    hull = T.join(parts, "hull")
    for m_ in list(hull.modifiers):
        hull.modifiers.remove(m_)
    # Hull frame -> turret frame: the dome's centre (blueprint y 0.5) on the origin.
    hull.data.transform(Matrix.Translation((0, -0.5, 0)))
    return hull


def build_turret(mats, coll):
    parts = []
    # Bearing ring (16): a dark collar under the dome with a flared lip.
    p = Part()
    p.stack(rrect(2.85, 2.5, 1.9, 0, -0.35, 5), [(0.0, 2.45), (0.0, 2.95), (0.22, 3.3)], S["ring"])
    parts.append(p.obj("ring", mats, coll))
    # Dome (22): a cast turret, a rounded square in plan (as the sprite's 5 x 4 px block), steep
    # sided and flat crowned; seams as raised welts.
    D = dict(rx=2.5, ry=2.0, cy=0.0, z0=3.15, z1=6.2)
    p = Part()
    rings = []
    N = 6
    for k in range(N):
        # superellipse profile (exponent 2.9): steep cast sides, a flattish crown
        th = (k / N) * (math.pi / 2)
        c = math.cos(th) ** (2 / 2.9)
        z = D["z0"] + (D["z1"] - D["z0"]) * math.sin(th) ** (2 / 2.9)
        rings.append([(x, y, z) for x, y in rrect(D["rx"] * c, D["ry"] * c, min(D["rx"], D["ry"]) * c * 0.62, 0,
                                                  D["cy"], 4)])
    rings.append([(0.0, D["cy"], D["z1"])])
    p.loft([[(x, y, 2.9) for x, y, _ in rings[0]]] + rings, S["dome"], cap0=True, cap1=False)
    from mathutils.bvhtree import BVHTree
    bmesh.ops.recalc_face_normals(p.bm, faces=p.bm.faces)
    tree = BVHTree.FromBMesh(p.bm)
    dome = p.obj("dome", mats, coll)
    parts.append(dome)

    def surf(u, v):
        hit = tree.ray_cast(Vector((u * D["rx"], D["cy"] + v * D["ry"], 20.0)), Vector((0, 0, -1)))
        return hit[0], hit[1]

    def welt(uv, w=0.2, h=0.07):
        """A raised seam strap following the dome's surface through the (u, v) points."""
        pts = [surf(u, v) for u, v in uv]
        pts = [(a, n) for a, n in pts if a is not None and a.z > D["z0"] + 0.25]
        q = Part()
        rr = []
        for i, (pnt, n) in enumerate(pts):
            a = pts[max(0, i - 1)][0]
            b = pts[min(len(pts) - 1, i + 1)][0]
            t = (b - a).normalized()
            bn = n.cross(t).normalized()
            rr.append([tuple(pnt - bn * (w / 2) - n * 0.06), tuple(pnt + bn * (w / 2) - n * 0.06),
                       tuple(pnt + bn * (w / 2) * 0.6 + n * h), tuple(pnt - bn * (w / 2) * 0.6 + n * h)])
        q.loft(rr, S["dome"])
        return q.obj("welt", mats, coll)

    for u in (-0.36, 0.36):
        parts.append(welt([(u, -0.95 + 1.85 * i / 8) for i in range(9)]))
    parts.append(welt([(-0.95 + 1.9 * i / 8, 0.42) for i in range(9)]))

    # Mantlet: an armoured block on the dome's front holding the gun.
    p = Part()
    p.stack([(-1.0, 1.0), (1.0, 1.0), (1.0, 2.3), (0.7, 2.75), (-0.7, 2.75), (-1.0, 2.3)],
            [(0.0, 2.95), (0.0, 4.55), (0.25, 4.85)], S["dark"])
    parts.append(p.obj("mantlet", mats, coll))
    # Gun: grey barrel with a recoil sleeve and a clamp, a recuperator rod beside it.
    p = Part()
    br = BARREL_R
    p.tube((0, 2.5, GUN_Z), (0, 8.2, GUN_Z), br, br * 0.9, sides=12, mat=S["barrel"])
    p.tube((0, 2.6, GUN_Z), (0, 3.9, GUN_Z), 0, sides=12, mat=S["mid"],
           rings=[(0.0, br + 0.25), (0.85, br + 0.25), (1.0, br + 0.1)])
    p.tube((0, 5.0, GUN_Z), (0, 5.3, GUN_Z), br + 0.07, sides=12, mat=S["mid"])
    rx = -(br + 0.27)
    p.tube((rx, 2.75, GUN_Z - 0.18), (rx, 6.4, GUN_Z - 0.18), 0.19, sides=8, mat=S["dark"])
    p.tube((rx, 5.05, GUN_Z - 0.18), (-0.1, 5.05, GUN_Z - 0.18), 0.12, sides=6, mat=S["mid"])
    parts.append(p.obj("gun", mats, coll))
    # Muzzle: a slim dark ported shroud (2), about three times the barrel's width, as the sprite's
    # 3 px dark-outlined muzzle: about as long as it is wide, tapered at both ends (an octagon in plan,
    # as the sprite draws it in every direction). A closed tapered collar at the back, a tapered crown
    # ring at the tip with the bore, and between them two side cheeks over a floor, open on top.
    # Through that window the bronze crown shows (1 px wide, as the sprite's tip: 24 in front, 22
    # behind it).
    p = Part()
    hw, hh, zb, tw = MUZ_HW, 0.95, GUN_Z - 0.1, MUZ_TAPER
    y0, y3 = MUZ_Y0, MUZ_Y0 + MUZ_LEN
    y1, y2 = y0 + MUZ_COLLAR, y3 - MUZ_RING
    sec = lambda w, h: rrect(w, h, min(0.32, h - 0.05), seg=3)  # noqa: E731
    for ys in (((y0, hw - tw, hh - tw * 0.5), (y0 + tw, hw, hh), (y1 + 0.1, hw, hh)),
               ((y2 - 0.1, hw, hh), (y3 - tw, hw, hh), (y3, hw - tw, hh - tw * 0.5))):
        p.loft([[(x, y, zb + z) for x, z in sec(w, h)] for y, w, h in ys], S["deep"])
    for sx in (1, -1):
        o = box(0.52, y1, hw, y2) if sx > 0 else mirror(box(0.52, y1, hw, y2))
        p.stack(o, [(0.0, zb - hh + 0.1), (0.0, zb + hh - 0.15), (0.1, zb + hh - 0.05)], S["deep"])
    p.stack(box(-hw + 0.1, y1, hw - 0.1, y2), [(0.0, zb - hh + 0.05), (0.0, zb - 0.3)], S["deep"])
    p.tube((0, y3 - 0.06, zb), (0, y3 + 0.02, zb), 0.32, sides=8, mat=S["black"])
    parts.append(p.obj("shroud", mats, coll))
    p = Part()
    ym = (y1 + y2) / 2 - 0.1
    p.tube((0, y1, GUN_Z), (0, ym, GUN_Z), 0.5, 0.55, sides=10, mat=S["dome"])
    p.tube((0, ym, GUN_Z), (0, y2 + 0.05, GUN_Z), 0, sides=10, mat=S["muzzle"],
           rings=[(0.0, 0.55), (0.75, 0.6), (1.0, 0.66)])
    parts.append(p.obj("crown", mats, coll))
    tur = T.join(parts, "turret")
    for m_ in list(tur.modifiers):
        tur.modifiers.remove(m_)
    return tur


def finish(obj, hard=None):
    """Smooth shading with sharp edges past 35 degrees; on the faces in `hard` (the hull: flat armour
    facets, no curved castings) already past 22 degrees, so a glacis or a chamfer stays a crisp facet
    instead of a smeared bulge."""
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    if hard:
        bm = bmesh.new()
        bm.from_mesh(me)
        for e in bm.edges:
            if len(e.link_faces) == 2 and all(f.index in hard for f in e.link_faces) \
                    and e.calc_face_angle(0) > math.radians(22):
                e.smooth = False
        bm.to_mesh(me)
        bm.free()
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50


def cull(obj):
    """T.cull_hidden, but the recess faces (deep / black: the floors and walls of bores, ports, slots,
    louvres and grooves) are always kept. Its sampled rays can't get out of a deep narrow recess, so
    it would drop the floor and leave a hole that shows the far wall's back face."""
    keep = {S["deep"], S["black"]}
    before = obj.data.copy()
    T.cull_hidden(obj)
    left = {tuple(round(c, 5) for c in p.center) for p in obj.data.polygons if p.material_index in keep}
    bm = bmesh.new()
    bm.from_mesh(before)
    gone = [f for f in bm.faces if f.material_index not in keep
            or tuple(round(c, 5) for c in f.calc_center_median()) in left]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    n = len(bm.faces)
    bm.to_mesh(before)
    bm.free()
    if n:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.from_mesh(before)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bm.to_mesh(obj.data)
        bm.free()
    bpy.data.meshes.remove(before)
    print(f"{NAME}: {obj.name} kept {n} recess faces the cull would drop")


def build_base(mats, coll):
    """Hull and turret, culled separately (their relative offset changes per direction), joined in
    that order (hull faces first) and scaled to Blender units; the face attribute `turret` says
    which piece each face belongs to."""
    hull = build_hull(mats, coll)
    tur = build_turret(mats, coll)
    for o in (hull, tur):
        o.data.transform(Matrix.Scale(PX, 4))
        cull(o)
    nh = len(hull.data.polygons)
    base = T.join([hull, tur], "base")
    for m_ in list(base.modifiers):
        base.modifiers.remove(m_)
    attr = base.data.attributes.new("turret", "BOOLEAN", "FACE")
    for i, p in enumerate(base.data.polygons):
        attr.data[i].value = i >= nh
    return base


def direction_matrices(angle, pc, pr, hx, hy, yaw):
    g = lambda c, r: Vector(((c - 12) * PX, (14 - r) * PX, 0))  # noqa: E731
    place = Matrix.Translation(g(pc, pr)) @ Matrix.Rotation(math.radians(angle - 90), 4, "Z")
    mh = place @ Matrix.Translation((hx * PX, hy * PX, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    return place, mh


def make_direction(base, model, angle, pc, pr, hx, hy, yaw, lamp_dx, lit, coll, mats):
    me = base.data.copy()
    me.name = model
    obj = bpy.data.objects.new(model, me)
    coll.objects.link(obj)
    mt, mh = direction_matrices(angle, pc, pr, hx, hy, yaw)
    mt = mt @ Matrix.Rotation(math.radians(AIM.get(model, 0.0)), 4, "Z")
    tur = me.attributes["turret"].data
    lamp = S["lamp"]
    vt, vl = set(), set()
    for p in me.polygons:
        if tur[p.index].value:
            vt.update(p.vertices)
        if p.material_index == lamp:
            vl.update(p.vertices)
    (sx, sy), gl = SHAPE[model]
    a, b = GUN_SPLIT[0] * PX, GUN_SPLIT[1] * PX
    ml, mw = MUZ.get(model, (1.0, 1.0))
    m0 = (MUZ_Y0 - 0.05) * PX
    rigid = {}
    for v in me.vertices:
        co = v.co.copy()
        if v.index in vt:
            if co.y >= m0:
                co.x *= mw
                co.y = m0 + (co.y - m0) * ml
            if co.y >= b:
                co.y += gl * PX
            elif co.y > a:
                co.y = a + (co.y - a) * (1 + gl * PX / (b - a))
            v.co = mt @ co
        else:
            w = mh @ Vector((co.x * sx, co.y * sy, co.z))
            rigid[v.index] = w.copy()
            c, r = warp(WARP.get(model, []), w.x * 12 + 12, 14 - w.y * 12)
            if v.index in vl:
                c += LAMP.get(model, (0, 0))[0]
                r += LAMP.get(model, (0, 0))[1]
            v.co = Vector(((c - 12) * PX, (14 - r) * PX, w.z))
    if not lit:
        dark = S["deep"]
        for p in me.polygons:
            if p.material_index == lamp:
                p.material_index = dark
    hard = {p.index for p in me.polygons if not tur[p.index].value}
    me.attributes.remove(me.attributes["turret"])
    finish(obj, hard)
    rigid_normals(obj, rigid)
    return obj


def rigid_normals(obj, rigid):
    """Shade the warped hull as its unwarped (rigidly placed) self: the plan warp nudges the walls by
    fractions of a pixel to follow the frame's outline, and smooth shading would turn those nudges
    into blotches. The normals (smooth, sharp edges, weighted) are computed with the hull in its
    rigid place and kept as custom normals once the warp is back."""
    me = obj.data
    warped = {i: me.vertices[i].co.copy() for i in rigid}
    for i, co in rigid.items():
        me.vertices[i].co = co
    me.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    em = ev.to_mesh()
    normals = [tuple(n.vector) for n in em.corner_normals]
    ev.to_mesh_clear()
    for m_ in list(obj.modifiers):
        obj.modifiers.remove(m_)
    for i, co in warped.items():
        me.vertices[i].co = co
    me.update()
    me.normals_split_custom_set(normals)


# --- bake: occlusion + edge lift colour multiplier and roughness (as ship-u-ship.py) --------------

def bake_maps(obj, out_dir, size=512, samples=64):
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
    except Exception as err:
        print("newshp-13: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("newshp-13_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("newshp-13_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode, tint):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
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
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.025
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.1
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, tint[k]), comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    bronze = {S["dome"], S["muzzle"], S["ring"]}
    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode, (0.8, 0.88, 1.0) if i in bronze else (1.0, 0.97, 0.93))
                for i, m in enumerate(mats)}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
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
    for k in BAKED:
        m = mats[S[k]]
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


# --- main ------------------------------------------------------------------------------------------

def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        if o.type == "MESH":
            o.hide_render = True
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(TAG)
    mats = make_materials(sprite)
    base = build_base(mats, coll)
    print(f"{NAME}: base {tris(base)} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:  # bake before any shell exists, so it can't occlude the model
        bake_dir = TEX / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(base, bake_dir)
        fmt = "WEBP"
    models = []
    for model, angle, (pc, pr), frames, (hx, hy), yaw, lamp_dx, lit in DIRECTIONS:
        obj = make_direction(base, model, angle, pc, pr, hx, hy, yaw, lamp_dx, lit, coll, mats)
        shell = common.outline_shell(obj, coll, faces=650)
        shell.parent = obj
        sprites = lib.subset(sprite, frames)
        print(f"{NAME}: {model} {tris(obj)} triangles, shell {len(shell.data.polygons)} faces")
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{model}", sprites, image_format=fmt)
        models.append((model, obj, sprites))
    base.hide_render = True
    base.hide_set(True)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        size = sprite["frames"][0]["size"]
        for i, (model, obj, sprites) in enumerate(models):
            path = out if i == 0 else out.parent / f"{model}.png"
            common.render_preview([obj], str(path), lib.frame_image(ROOT, NAME, sprite, sprites), size=size)


if __name__ == "__main__":
    main()
